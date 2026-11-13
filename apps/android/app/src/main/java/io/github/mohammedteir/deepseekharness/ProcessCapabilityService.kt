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

/** Fixed native OS qualification only; no arbitrary-command Binder or original terminal backend. */
class ProcessCapabilityService : Service() {
    private val executor = Executors.newSingleThreadExecutor()
    private val started = AtomicBoolean(false)
    private val owner = OwnedProcess(10)
    private fun hash(file: File): String {
        val digest = java.security.MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input -> val bytes = ByteArray(65536); while (true) { val n = input.read(bytes); if (n < 0) break; digest.update(bytes, 0, n) } }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
    private fun text(file: File): String { check(file.length() <= 196608); return if (file.isFile) file.readText() else "" }
    private fun runProof(): String {
        val parent = File(filesDir, "process-probe").canonicalFile.apply { check(mkdirs() || isDirectory) }
        val work = Files.createTempDirectory(parent.toPath(), "run-").toFile().canonicalFile
        android.system.Os.chmod(work.path, 448) // 0700; existing Harness session trees are never opened.
        val executable = File(applicationInfo.nativeLibraryDir, "libharness_process_probe.so").canonicalFile
        check(executable.isFile && !executable.canWrite() && executable.canExecute())
        val output = File(work, "stdout.json"); val errors = File(work, "stderr.txt")
        val builder = ProcessBuilder(executable.path, "--suite", work.path).directory(work).redirectOutput(output).redirectError(errors)
        builder.environment().clear(); builder.environment()["PATH"] = "/system/bin"
        try {
            val child = owner.start(builder); child.outputStream.close()
            check(child.waitFor(40, TimeUnit.SECONDS)) { "Fixed suite deadline exceeded" }
            val raw = text(output)
            val result = try { JSONObject(raw) } catch (error: Exception) { throw IllegalStateException("Native exit ${child.exitValue()}: $raw; ${text(errors)}", error) }
            result.put("nativeExitCode", child.exitValue()).put("nativeStderr", text(errors))
            result.put("apkSha256", hash(File(applicationInfo.sourceDir))).put("nativeProbeSha256", hash(executable))
                .put("installedProbeWritable", executable.canWrite()).put("supervisorPid", android.os.Process.myPid()).put("supervisorUid", android.os.Process.myUid())
                .put("expectedWorkspace", work.path).put("testTimeMillis", System.currentTimeMillis()).put("evidenceDirectory", work.name)
                .put("device", JSONObject().put("model", Build.MODEL).put("androidRelease", Build.VERSION.RELEASE).put("api", Build.VERSION.SDK_INT).put("abi", Build.SUPPORTED_ABIS.joinToString(",")))
            if (child.exitValue() == 0) {
                check(result.getInt("uid") == android.os.Process.myUid() && result.getInt("uid") > 0)
                check(result.getInt("parentPid") == android.os.Process.myPid() && result.getString("execPath") == executable.path)
                check(!result.getBoolean("gate3Passed"))
            }
            File(work, "result.json").writeText(result.toString())
            return if (child.exitValue() == 0) result.toString() else "BLOCKED: native process suite exit ${child.exitValue()}\n$result"
        } finally { owner.close() }
    }
    private val messenger = Messenger(Handler(Looper.getMainLooper()) { message ->
        if (message.sendingUid == android.os.Process.myUid() && message.what == 1 && message.replyTo != null && started.compareAndSet(false, true)) {
            val reply = message.replyTo
            executor.execute {
                val result = try { runProof() } catch (error: Exception) { "BLOCKED: process qualification ${error.javaClass.simpleName}: ${error.message}" }
                try { reply.send(Message.obtain(null, 1).apply { data = Bundle().apply { putString("result", result) } }) }
                catch (_: RemoteException) { /* Consumer left; owner already closes in runProof. */ }
            }
        }
        true
    })
    override fun onBind(intent: Intent): IBinder = messenger.binder
    override fun onDestroy() {
        executor.shutdownNow()
        Thread {
            try { owner.close(); check(executor.awaitTermination(15, TimeUnit.SECONDS)) }
            catch (error: Exception) { Log.e("HarnessProcessProof", "Probe cleanup failed", error) }
            finally { android.os.Process.killProcess(android.os.Process.myPid()) }
        }.start()
        super.onDestroy()
    }
}
