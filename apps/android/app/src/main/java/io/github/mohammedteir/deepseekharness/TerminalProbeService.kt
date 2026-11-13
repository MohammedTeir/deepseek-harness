package io.github.mohammedteir.deepseekharness

import android.app.Service
import android.content.Intent
import android.os.*
import android.util.Log
import org.json.JSONObject
import java.io.File
import java.nio.file.Files
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/** Visible, bound, fixed original-terminal qualification. No general shell or background promise. */
class TerminalProbeService : Service() {
    private val executor = Executors.newSingleThreadExecutor()
    private val started = AtomicBoolean(false)
    private val owner = OwnedProcess(10)
    @Volatile private var broker: TerminalAllocationBroker? = null
    @Volatile private var reply: Messenger? = null
    @Volatile private var completedResult: File? = null
    private fun failureDetails(error: Throwable, depth: Int = 0): JSONObject = JSONObject()
        .put("name", error.javaClass.simpleName).put("message", error.message?.take(2048))
        .also { value ->
            if (depth < 4) {
                value.put("suppressed", org.json.JSONArray(error.suppressed.take(8).map { failureDetails(it, depth + 1) }))
                error.cause?.let { value.put("cause", failureDetails(it, depth + 1)) }
            }
        }
    private fun send(what: Int, value: String) {
        reply?.send(Message.obtain(null, what).apply { data = Bundle().apply { putString("result", value) } })
    }
    private fun hash(file: File): String {
        val digest = java.security.MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input -> val buffer = ByteArray(65536); while (true) { val n = input.read(buffer); if (n < 0) break; digest.update(buffer, 0, n) } }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
    private fun bounded(file: File): String { check(file.length() <= 262144); return if (file.isFile) file.readText() else "" }
    private fun copyAssets(source: String, destination: File) {
        check(destination.mkdirs() || destination.isDirectory)
        for (name in assets.list(source) ?: error("Missing node-pty assets")) {
            check(name.isNotEmpty() && name !in listOf(".", "..") && !name.contains('/'))
            val next = "$source/$name"; val target = File(destination, name)
            if ((assets.list(next) ?: emptyArray()).isNotEmpty()) copyAssets(next, target)
            else assets.open(next).use { input -> target.outputStream().use { input.copyTo(it) } }
        }
    }
    private fun runProof(): String {
        val base = File(filesDir, "terminal-probe").canonicalFile.apply { check(mkdirs() || isDirectory) }
        val work = Files.createTempDirectory(base.toPath(), "run-").toFile().canonicalFile
        android.system.Os.chmod(work.path, 448)
        val workspace = File(work, "workspace").apply { check(mkdir()) }.canonicalFile
        val image = ProfileImage.install(assets, filesDir)
        try {
            val payload = File(work, "node-pty"); copyAssets("node-pty", payload)
            fun installed(name: String): File = File(applicationInfo.nativeLibraryDir, name).canonicalFile.apply { check(isFile && canRead() && !canWrite()) }
            val node = installed("libnode_executable.so"); val addon = installed("libharness_node_pty.so"); val fixture = installed("libharness_pty_fixture.so")
            val build = JSONObject(File(payload, "build.json").readText())
            check(hash(addon) == build.getString("binarySha256") && hash(fixture) == build.getString("fixtureSha256"))
            val files = build.getJSONObject("packageFilesSha256")
            for (name in files.keys()) {
                val file = File(payload, "package/$name").canonicalFile
                check(file.path.startsWith(File(payload, "package").canonicalPath + File.separator))
                check(hash(file) == files.getString(name))
            }
            val native = TerminalAllocationBroker(this, workspace) { request -> send(2, request.toString()) }
            broker = native
            var primaryFailure: Exception? = null
            try {
                val output = File(work, "result.json")
                val builder = ProcessBuilder(node.path, File(image, "apps/android/runtime/terminal-smoke.mjs").path, output.path)
                    .directory(work).redirectOutput(File(work, "stdout.txt")).redirectError(File(work, "stderr.txt"))
                builder.environment().clear()
                builder.environment().putAll(native.launchEnvironment())
                builder.environment().putAll(mapOf("PATH" to "/system/bin", "HOME" to work.path, "TMPDIR" to cacheDir.path,
                    "LD_LIBRARY_PATH" to applicationInfo.nativeLibraryDir, "HARNESS_NODE_PTY_PACKAGE" to File(payload, "package").path,
                    "HARNESS_NODE_PTY_ADDON" to addon.path, "HARNESS_NODE_PTY_FIXTURE" to fixture.path))
                val child = owner.start(builder); child.outputStream.close()
                check(child.waitFor(240, TimeUnit.SECONDS)) { "Original terminal qualification deadline exceeded" }
                val text = bounded(output)
                val result = if (text.isBlank()) JSONObject().put("failure", "Controller produced no result") else JSONObject(text)
                result.put("nativeExitCode", child.exitValue()).put("nativeBroker", native.evidence())
                    .put("apkSha256", hash(File(applicationInfo.sourceDir))).put("nodeSha256", hash(node))
                    .put("nodePtyAddonSha256", hash(addon)).put("fixtureSha256", hash(fixture))
                    .put("nativePublicationSha256", hash(installed("libharness_atomic.so")))
                    .put("installedCodeWritable", node.canWrite() || addon.canWrite() || fixture.canWrite())
                    .put("supervisorUid", android.os.Process.myUid()).put("supervisorPid", android.os.Process.myPid())
                    .put("testTimeMillis", System.currentTimeMillis()).put("evidenceDirectory", work.name)
                    .put("device", JSONObject().put("model", Build.MODEL).put("api", Build.VERSION.SDK_INT)
                        .put("androidRelease", Build.VERSION.RELEASE).put("abi", Build.SUPPORTED_ABIS.joinToString(",")))
                    .put("nativeStderr", bounded(File(work, "stderr.txt"))).put("gate3Passed", false)
                if (child.exitValue() == 0) {
                    val identity = result.getJSONObject("kernelIdentity")
                    check(identity.getInt("uid") == android.os.Process.myUid() && identity.getInt("parentPid") == android.os.Process.myPid())
                    check(result.getBoolean("harnessStarted") && result.getBoolean("sessionRecoveredAcrossRuntimeRestart"))
                    check(native.evidence().getInt("allocationsConsumed") == 1 && result.getJSONObject("report").getInt("starts") == 1)
                }
                File(work, "complete-result.json").also {
                    it.writeText(result.toString()); completedResult = it
                }
                return if (child.exitValue() == 0) result.toString() else "BLOCKED: original terminal exit ${child.exitValue()}\n$result"
            } catch (primary: Exception) {
                primaryFailure = primary
                throw primary
            } finally {
                val cleanupFailures = mutableListOf<Exception>()
                try { native.close() } catch (cleanup: Exception) { cleanupFailures.add(cleanup) }
                broker = null
                try { owner.close() } catch (cleanup: Exception) { cleanupFailures.add(cleanup) }
                if (cleanupFailures.isNotEmpty()) {
                    val primary = primaryFailure
                    if (primary != null) cleanupFailures.forEach { primary.addSuppressed(it) }
                    else throw java.io.IOException("Terminal owner cleanup failed").apply { cleanupFailures.forEach { addSuppressed(it) } }
                }
            }
        } finally { ProfileImage.remove(image.parentFile!!) }
    }
    private val messenger = Messenger(Handler(Looper.getMainLooper()) { message ->
        if (message.sendingUid != android.os.Process.myUid()) return@Handler true
        if (message.what == 2) {
            broker?.decide(message.data.getString("callId") ?: "", message.data.getString("terminalId") ?: "", message.data.getBoolean("allow", false))
        } else if (message.what == 1 && message.replyTo != null && started.compareAndSet(false, true)) {
            reply = message.replyTo
            executor.execute {
                val result = try { runProof() } catch (error: Exception) {
                    Log.e("HarnessTerminal", "Original terminal qualification failed", error)
                    val failure = JSONObject().put("status", "BLOCKED").put("failure", failureDetails(error)).put("gate3Passed", false)
                    completedResult?.let { file ->
                        try { failure.put("qualificationBeforeCleanup", JSONObject(bounded(file))) }
                        catch (read: Exception) { failure.put("resultReadFailure", failureDetails(read)) }
                    }
                    "BLOCKED: original terminal ${error.javaClass.simpleName}: ${error.message}\n$failure"
                }
                try { send(1, result) } catch (_: RemoteException) { /* The Activity left; owner cleanup revokes approval. */ }
            }
        }
        true
    })
    override fun onBind(intent: Intent): IBinder = messenger.binder
    override fun onDestroy() {
        executor.shutdownNow()
        Thread {
            val failures = mutableListOf<Exception>()
            fun attempt(action: () -> Unit) { try { action() } catch (error: Exception) { failures.add(error) } }
            try {
                attempt { broker?.close() }; attempt { owner.close() }
                attempt { check(executor.awaitTermination(25, TimeUnit.SECONDS)) }
                if (failures.isNotEmpty()) Log.e("HarnessTerminal", "Qualification cleanup failed",
                    java.io.IOException("Native owner cleanup incomplete").apply { failures.forEach { addSuppressed(it) } })
            } finally { android.os.Process.killProcess(android.os.Process.myPid()) }
        }.start()
        super.onDestroy()
    }
}
