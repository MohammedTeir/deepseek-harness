package io.github.mohammedteir.deepseekharness

import android.app.Service
import android.content.Intent
import android.os.*
import android.util.Log
import java.io.File
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import org.json.JSONObject

/** Original dsh profile/session proof; no shell, model request or substitute engine. */
class ProfileProbeService : Service() {
    private val executor = Executors.newSingleThreadExecutor()
    private val started = AtomicBoolean(false)
    private val owner = OwnedProcess(10)
    private fun read(file: File): String {
        if (!file.isFile) return ""
        check(file.length() <= 65536) { "Profile diagnostic exceeds limit" }
        return file.readText()
    }
    private fun digest(file: File): String {
        val digest = java.security.MessageDigest.getInstance("SHA-256")
        file.inputStream().use { stream ->
            val buffer = ByteArray(65536)
            while (true) {
                val count = stream.read(buffer)
                if (count < 0) break
                digest.update(buffer, 0, count)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
    private fun runProbe(): String {
        val directory = File(filesDir, "profile-probe").canonicalFile.apply { mkdirs() }
        val output = File(directory, "result.json")
        check(!output.exists() || output.delete()) { "Cannot remove stale profile result" }
        val root = ProfileImage.install(assets, filesDir)
        try {
            val executable = File(applicationInfo.nativeLibraryDir, "libnode_executable.so").canonicalFile
            check(executable.isFile && !executable.canWrite()) { "Installed Node missing or writable" }
            val builder = ProcessBuilder(executable.absolutePath,
                File(root, "apps/android/runtime/profile-smoke.mjs").absolutePath, output.absolutePath)
                .directory(directory).redirectError(File(directory, "stderr.txt")).redirectOutput(File(directory, "stdout.txt"))
            builder.environment()["LD_LIBRARY_PATH"] = applicationInfo.nativeLibraryDir
            builder.environment()["TMPDIR"] = cacheDir.absolutePath
            val process = owner.start(builder)
            try {
                process.outputStream.close()
                check(process.waitFor(90, TimeUnit.SECONDS)) { "Original profile exceeded 90-second deadline" }
                if (process.exitValue() != 0) return "BLOCKED: original profile exit ${process.exitValue()}\n${read(output)}\nNode stderr:\n${read(File(directory, "stderr.txt"))}"
                val result = JSONObject(read(output))
                check(result.getBoolean("harnessStarted") && result.getBoolean("sessionRecoveredAcrossRuntimeRestart")) { "Original profile/session evidence incomplete" }
                val identity = result.getJSONObject("kernelIdentity")
                check(identity.getInt("pid") == result.getInt("pid") && identity.getInt("parentPid") == android.os.Process.myPid())
                check(identity.getInt("uid") == android.os.Process.myUid() && identity.getInt("uid") != 0)
                check(result.getString("execPath") == executable.absolutePath)
                check(!result.getBoolean("modelRequestExecuted") && !result.getBoolean("approvedCommandExecuted") && !result.getBoolean("gate2Passed"))
                result.put("device", JSONObject().put("model", Build.MODEL).put("androidRelease", Build.VERSION.RELEASE).put("api", Build.VERSION.SDK_INT))
                val publication = File(applicationInfo.nativeLibraryDir, "libharness_atomic.so").canonicalFile
                check(publication.isFile && !publication.canWrite()) { "Publication binding missing or writable" }
                result.put("apkSha256", digest(File(applicationInfo.sourceDir)))
                result.put("nativePublicationSha256", digest(publication))
                result.put("installedPublicationBindingWritable", publication.canWrite())
                result.put("supervisorPid", android.os.Process.myPid()).put("supervisorUid", android.os.Process.myUid())
                val pending = File(directory, "result.host.pending")
                pending.writeText(result.toString())
                check(pending.renameTo(output))
                return result.toString()
            } finally { owner.close() }
        } finally {
            // Only the temporary interpreted installation is removed; home/sessions persist.
            ProfileImage.remove(root.parentFile!!)
        }
    }
    private val messenger = Messenger(Handler(Looper.getMainLooper()) { message ->
        if (message.what == 1 && message.replyTo != null && started.compareAndSet(false, true)) {
            val reply = message.replyTo
            executor.execute {
                val result = try { runProbe() }
                catch (error: Exception) { "BLOCKED: profile ${error.javaClass.simpleName}: ${error.message}" }
                try { reply.send(Message.obtain(null, 1).apply { data = Bundle().apply { putString("result", result) } }) }
                catch (_: RemoteException) { /* Bound consumer left; process ownership still closes. */ }
            }
        }
        true
    })
    override fun onBind(intent: Intent): IBinder = messenger.binder
    override fun onDestroy() {
        executor.shutdownNow()
        super.onDestroy()
        Thread {
            try {
                owner.close()
                check(executor.awaitTermination(15, TimeUnit.SECONDS)) { "Profile worker did not stop" }
            }
            catch (error: Exception) { Log.e("HarnessProfile", "Profile cleanup failed", error) }
            finally { android.os.Process.killProcess(android.os.Process.myPid()) }
        }.start()
    }
}
