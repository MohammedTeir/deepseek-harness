package io.github.mohammedteir.deepseekharness

import android.app.Service
import android.content.Intent
import android.os.*
import android.util.Log
import org.json.JSONObject
import java.io.File
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/** Original-profile qualification supervisor. Private Binder owns human decisions. */
class CommandProbeService : Service() {
    private val executor = Executors.newSingleThreadExecutor()
    private val started = AtomicBoolean(false)
    private val owner = OwnedProcess(10)
    @Volatile private var broker: CommandBroker? = null
    @Volatile private var reply: Messenger? = null
    private fun send(what: Int, value: String) {
        reply?.send(Message.obtain(null, what).apply { data = Bundle().apply { putString("result", value) } })
    }
    private fun hash(file: File): String {
        val digest = java.security.MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input -> val bytes = ByteArray(65536); while (true) { val n = input.read(bytes); if (n < 0) break; digest.update(bytes, 0, n) } }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
    private fun bounded(file: File): String { check(file.length() <= 196608); return if (file.isFile) file.readText() else "" }
    private fun runProof(): String {
        val directory = File(filesDir, "command-probe").canonicalFile.apply { check(mkdirs() || isDirectory) }
        val workspace = File(directory, "workspace").canonicalFile.apply { check(mkdirs() || isDirectory) }
        val output = File(directory, "result.json")
        check(!output.exists() || output.delete())
        val image = ProfileImage.install(assets, filesDir)
        val native = try { CommandBroker(workspace) { request -> send(2, request.toString()) } }
        catch (error: Exception) { ProfileImage.remove(image.parentFile!!); throw error }
        broker = native
        try {
            val executable = File(applicationInfo.nativeLibraryDir, "libnode_executable.so").canonicalFile
            check(executable.isFile && !executable.canWrite())
            val builder = ProcessBuilder(executable.path, File(image, "apps/android/runtime/command-smoke.mjs").path, output.path)
                .directory(directory).redirectOutput(File(directory, "stdout.txt")).redirectError(File(directory, "stderr.txt"))
            builder.environment().keys.toList().filter { Regex("KEY|TOKEN|SECRET|PASSWORD", RegexOption.IGNORE_CASE).containsMatchIn(it) }.forEach { builder.environment().remove(it) }
            builder.environment().putAll(native.launchEnvironment())
            builder.environment()["LD_LIBRARY_PATH"] = applicationInfo.nativeLibraryDir
            builder.environment()["TMPDIR"] = cacheDir.path
            val process = owner.start(builder)
            process.outputStream.close()
            check(process.waitFor(210, TimeUnit.SECONDS)) { "Command qualification timed out" }
            val payload = bounded(output)
            val result = if (payload.isBlank()) JSONObject().put("schemaVersion", 1).put("failure", "Controller produced no JSON result").put("gate2Passed", false) else JSONObject(payload)
            result.put("nativeBroker", native.evidence()).put("device", JSONObject().put("model", Build.MODEL)
                .put("api", Build.VERSION.SDK_INT).put("androidRelease", Build.VERSION.RELEASE).put("abi", Build.SUPPORTED_ABIS.joinToString(",")))
            result.put("apkSha256", hash(File(applicationInfo.sourceDir)))
                .put("nativeNodeSha256", hash(executable))
                .put("nativePublicationSha256", hash(File(applicationInfo.nativeLibraryDir, "libharness_atomic.so")))
                .put("supervisorUid", android.os.Process.myUid()).put("supervisorPid", android.os.Process.myPid())
                .put("testTimeMillis", System.currentTimeMillis()).put("nativeStderr", bounded(File(directory, "stderr.txt")))
            if (process.exitValue() == 0) {
                val identity = result.getJSONObject("kernelIdentity")
                check(identity.getInt("parentPid") == android.os.Process.myPid() && identity.getInt("uid") == android.os.Process.myUid())
                check(result.getBoolean("originalRegistryAndPipeline") && result.getBoolean("sessionRecoveredAcrossRuntimeRestart"))
                check(native.evidence().getInt("processLaunches") == 1)
                check(result.getBoolean("approvedCommandExecuted") && !result.getBoolean("gate2Passed"))
            }
            output.writeText(result.toString())
            return if (process.exitValue() == 0) result.toString() else "BLOCKED: original command proof exit ${process.exitValue()}\n$result"
        } finally {
            try { native.close() } finally { broker = null; try { owner.close() } finally { ProfileImage.remove(image.parentFile!!) } }
        }
    }
    private val messenger = Messenger(Handler(Looper.getMainLooper()) { message ->
        if (message.sendingUid != android.os.Process.myUid()) return@Handler true
        if (message.what == 2) {
            broker?.decide(message.data.getString("callId") ?: "", message.data.getBoolean("allow", false))
        } else if (message.what == 1 && message.replyTo != null && started.compareAndSet(false, true)) {
            reply = message.replyTo
            executor.execute {
                val result = try { runProof() } catch (error: Exception) { "BLOCKED: ${error.javaClass.simpleName}: ${error.message}" }
                try { send(1, result) } catch (_: RemoteException) { /* Consumer left; no pending grant survives close. */ }
            }
        }
        true
    })
    override fun onBind(intent: Intent): IBinder = messenger.binder
    override fun onDestroy() {
        executor.shutdownNow()
        Thread {
            try { broker?.close(); owner.close(); executor.awaitTermination(18, TimeUnit.SECONDS) }
            catch (error: Exception) { Log.e("HarnessCommand", "Command cleanup failed", error) }
            finally { android.os.Process.killProcess(android.os.Process.myPid()) }
        }.start()
        super.onDestroy()
    }
}
