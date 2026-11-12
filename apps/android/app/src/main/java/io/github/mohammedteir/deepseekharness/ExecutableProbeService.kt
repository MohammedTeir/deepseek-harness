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

/** Fixed, installer-owned Node executable comparison; no arbitrary command interface. */
class ExecutableProbeService : Service() {
    private val executor = Executors.newSingleThreadExecutor()
    private val started = AtomicBoolean(false)
    private val owner = OwnedProcess()
    private fun read(file: File): String {
        if (!file.isFile) return ""
        check(file.length() <= 32768) { "Probe evidence exceeds diagnostic limit" }
        return file.readText()
    }
    private fun runProbe(): String {
        val directory = File(filesDir, "executable-probe").apply { mkdirs() }
        val executable = File(applicationInfo.nativeLibraryDir, "libnode_executable.so").canonicalFile
        check(executable.isFile && !executable.canWrite()) { "Installer-owned Node executable missing or writable" }
        for (name in listOf("smoke.mjs", "executable-smoke.mjs", "child-node.mjs", "proc-identity.mjs")) {
            assets.open("runtime/$name").use { source -> File(directory, name).outputStream().use(source::copyTo) }
        }
        val output = File(directory, "result.json")
        check(!output.exists() || output.delete()) { "Cannot remove stale executable result" }
        val stderr = File(directory, "stderr.txt")
        val stdout = File(directory, "stdout.txt")
        val builder = ProcessBuilder(executable.absolutePath,
            File(directory, "executable-smoke.mjs").absolutePath, output.absolutePath)
            .directory(directory).redirectError(stderr).redirectOutput(stdout)
        // Only the immutable installer directory supplies this binary's shared dependencies.
        builder.environment()["LD_LIBRARY_PATH"] = applicationInfo.nativeLibraryDir
        val process = owner.start(builder)
        try {
            process.outputStream.close()
            check(process.waitFor(45, TimeUnit.SECONDS)) { "Packaged Node exceeded 45-second deadline" }
            val exit = process.exitValue()
            if (exit != 0) return "BLOCKED: packaged Node exit $exit\n${read(output)}\nNode stderr:\n${read(stderr)}"
            check(output.isFile) { "Packaged Node returned without evidence" }
            val result = JSONObject(read(output))
            val identity = result.getJSONObject("kernelIdentity")
            check(identity.getInt("pid") == result.getInt("pid")) { "Kernel/Node PID mismatch" }
            check(identity.getInt("parentPid") == android.os.Process.myPid()) { "Unexpected Node parent" }
            check(identity.getInt("uid") == android.os.Process.myUid() && identity.getInt("uid") != 0) { "Unexpected child UID" }
            check(result.getString("execPath") == executable.absolutePath) { "Node execPath is not the installed executable" }
            check(result.getString("childNodeLaunch") == "passed") { "Child Node launch unverified" }
            result.put("supervisorPid", android.os.Process.myPid())
            result.put("supervisorUid", android.os.Process.myUid())
            result.put("installedExecutableWritable", executable.canWrite())
            result.put("device", JSONObject().put("model", Build.MODEL).put("manufacturer", Build.MANUFACTURER)
                .put("androidRelease", Build.VERSION.RELEASE).put("api", Build.VERSION.SDK_INT))
            val pending = File(directory, "result.host.pending")
            pending.writeText(result.toString())
            check(pending.renameTo(output)) { "Could not persist supervisor evidence" }
            return result.toString()
        } finally { owner.close() }
    }
    private val messenger = Messenger(Handler(Looper.getMainLooper()) { message ->
        if (message.what == 1 && message.replyTo != null && started.compareAndSet(false, true)) {
            val reply = message.replyTo
            executor.execute {
                val result = try { runProbe() }
                catch (error: Exception) { "BLOCKED: packaged probe ${error.javaClass.simpleName}: ${error.message}" }
                try { reply.send(Message.obtain(null, 1).apply { data = Bundle().apply { putString("result", result) } }) }
                catch (_: RemoteException) { /* The bound consumer left. */ }
            }
        }
        true
    })
    override fun onBind(intent: Intent): IBinder = messenger.binder
    override fun onDestroy() {
        executor.shutdownNow()
        super.onDestroy()
        // Cleanup owns startup/exit synchronization; never kill the supervisor before reaping.
        Thread {
            try { owner.close() }
            catch (error: Exception) { Log.e("HarnessExecProbe", "Child cleanup failed", error) }
            finally { android.os.Process.killProcess(android.os.Process.myPid()) }
        }.start()
    }
}
