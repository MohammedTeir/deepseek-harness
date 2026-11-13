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

/** Original node-pty feasibility; fixed fixture roles, not an agent execution provider. */
class NodePtyProbeService : Service() {
    private val executor = Executors.newSingleThreadExecutor()
    private val started = AtomicBoolean(false)
    private val owner = OwnedProcess(10)
    private fun hash(file: File): String {
        val digest = java.security.MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input -> val bytes = ByteArray(65536); while (true) { val n = input.read(bytes); if (n < 0) break; digest.update(bytes, 0, n) } }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
    private fun copyAssets(source: String, destination: File) {
        check(destination.mkdirs() || destination.isDirectory)
        for (name in assets.list(source) ?: error("Missing fixed asset directory")) {
            check(name.isNotEmpty() && !name.contains('/') && name != ".." && name != ".")
            val next = "$source/$name"; val file = File(destination, name)
            if ((assets.list(next) ?: emptyArray()).isNotEmpty()) copyAssets(next, file)
            else assets.open(next).use { input -> file.outputStream().use { input.copyTo(it) } }
        }
    }
    private fun bounded(file: File): String { check(file.length() <= 196608); return if (file.isFile) file.readText() else "" }
    private fun runProof(): String {
        val base = File(filesDir, "node-pty-probe").canonicalFile.apply { check(mkdirs() || isDirectory) }
        val work = Files.createTempDirectory(base.toPath(), "run-").toFile().canonicalFile
        android.system.Os.chmod(work.path, 448)
        val payload = File(work, "payload"); copyAssets("node-pty", payload)
        fun installed(name: String, executable: Boolean = true): File = File(applicationInfo.nativeLibraryDir, name).canonicalFile.apply { check(isFile && canRead() && !canWrite() && (!executable || canExecute())) }
        val node = installed("libnode_executable.so"); val addon = installed("libharness_node_pty.so", false); val fixture = installed("libharness_pty_fixture.so")
        val build = JSONObject(File(payload, "build.json").readText())
        check(hash(addon) == build.getString("binarySha256") && hash(fixture) == build.getString("fixtureSha256"))
        val files = build.getJSONObject("packageFilesSha256")
        for (name in files.keys()) {
            val file = File(payload, "package/$name").canonicalFile
            check(file.path.startsWith(File(payload, "package").canonicalPath + File.separator))
            check(hash(file) == files.getString(name))
        }
        val resultFile = File(work, "result.json"); val stderr = File(work, "stderr.txt"); val stdout = File(work, "stdout.txt")
        val builder = ProcessBuilder(node.path, File(payload, "smoke.mjs").path, resultFile.path).directory(work).redirectError(stderr).redirectOutput(stdout)
        builder.environment().clear()
        builder.environment().putAll(mapOf("PATH" to "/system/bin", "HARNESS_NODE_PTY_PACKAGE" to File(payload, "package").path,
            "HARNESS_NODE_PTY_ADDON" to addon.path, "HARNESS_NODE_PTY_FIXTURE" to fixture.path))
        try {
            val child = owner.start(builder); child.outputStream.close()
            check(child.waitFor(45, TimeUnit.SECONDS)) { "Original node-pty qualification exceeded deadline" }
            val result = try { JSONObject(bounded(resultFile)) } catch (error: Exception) { throw IllegalStateException("Node exit ${child.exitValue()}: ${bounded(stderr)}", error) }
            result.put("nativeExitCode", child.exitValue()).put("nativeStderr", bounded(stderr)).put("nativeStdout", bounded(stdout))
                .put("apkSha256", hash(File(applicationInfo.sourceDir))).put("nodePtyAddonSha256", hash(addon)).put("fixtureSha256", hash(fixture)).put("nodeSha256", hash(node))
                .put("installedCodeWritable", addon.canWrite() || node.canWrite() || fixture.canWrite()).put("supervisorUid", android.os.Process.myUid()).put("supervisorPid", android.os.Process.myPid())
                .put("expectedWorkspace", work.path).put("testTimeMillis", System.currentTimeMillis()).put("evidenceDirectory", work.name)
                .put("device", JSONObject().put("model", Build.MODEL).put("api", Build.VERSION.SDK_INT).put("androidRelease", Build.VERSION.RELEASE).put("abi", Build.SUPPORTED_ABIS.joinToString(",")))
            if (child.exitValue() == 0) {
                check(result.getJSONObject("kernelIdentity").getInt("uid") == android.os.Process.myUid())
                check(result.getJSONObject("kernelIdentity").getInt("parentPid") == android.os.Process.myPid())
                check(!result.getBoolean("gate3Passed"))
                check(result.getString("cwd") == work.path && result.getString("fixtureExecutable") == fixture.path)
            }
            File(work, "complete-result.json").writeText(result.toString())
            return if (child.exitValue() == 0) result.toString() else "BLOCKED: original node-pty exit ${child.exitValue()}\n$result"
        } finally { owner.close() }
    }
    private val messenger = Messenger(Handler(Looper.getMainLooper()) { message ->
        if (message.sendingUid == android.os.Process.myUid() && message.what == 1 && message.replyTo != null && started.compareAndSet(false, true)) {
            val reply = message.replyTo
            executor.execute {
                val result = try { runProof() } catch (error: Exception) { "BLOCKED: original node-pty ${error.javaClass.simpleName}: ${error.message}" }
                try { reply.send(Message.obtain(null, 1).apply { data = Bundle().apply { putString("result", result) } }) } catch (_: RemoteException) { }
            }
        }
        true
    })
    override fun onBind(intent: Intent): IBinder = messenger.binder
    override fun onDestroy() {
        executor.shutdownNow()
        Thread {
            try { owner.close(); check(executor.awaitTermination(15, TimeUnit.SECONDS)) }
            catch (error: Exception) { Log.e("HarnessNodePty", "Qualification cleanup failed", error) }
            finally { android.os.Process.killProcess(android.os.Process.myPid()) }
        }.start()
        super.onDestroy()
    }
}
