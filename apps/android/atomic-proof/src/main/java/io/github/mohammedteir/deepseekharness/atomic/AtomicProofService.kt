package io.github.mohammedteir.deepseekharness.atomic

import android.app.Service
import android.content.Intent
import android.os.*
import android.util.Log
import java.io.File
import java.security.MessageDigest
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import org.json.JSONObject

/** Fixed native filesystem tests in a fresh private directory; never opens Harness session data. */
class AtomicProofService : Service() {
    private val executor = Executors.newSingleThreadExecutor()
    private val started = AtomicBoolean(false)
    private val lock = Any()
    private var child: java.lang.Process? = null
    private var cancelled = false
    private fun sha256(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256").digest(bytes)
        .joinToString("") { "%02x".format(it) }
    private fun bounded(file: File): String {
        check(file.isFile && file.length() <= 131072) { "Missing or excessive native evidence: ${file.name}" }
        return file.readText()
    }
    private fun runProof(): String {
        val evidence = File(filesDir, "atomic-probe").apply { check(isDirectory || mkdir()) }.canonicalFile
        // An interrupted prior run is retained; every invocation owns a newly created directory.
        val work = java.nio.file.Files.createTempDirectory(evidence.toPath(), "run-").toFile().canonicalFile
        check(work.setReadable(false, false) && work.setWritable(false, false) && work.setExecutable(false, false))
        check(work.setReadable(true, true) && work.setWritable(true, true) && work.setExecutable(true, true))
        val executable = File(applicationInfo.nativeLibraryDir, "libatomic_poc.so").canonicalFile
        check(executable.isFile && !executable.canWrite()) { "Native proof must execute from installer-owned storage" }
        val stdout = File(work, "stdout.json")
        val stderr = File(work, "stderr.txt")
        val builder = ProcessBuilder(executable.absolutePath, work.absolutePath).directory(work)
            .redirectOutput(stdout).redirectError(stderr)
        builder.environment().clear()
        builder.environment()["PATH"] = "/system/bin"
        val process = synchronized(lock) {
            check(!cancelled) { "Proof cancelled before launch" }
            builder.start().also { child = it }
        }
        try {
            process.outputStream.close()
            check(process.waitFor(85, TimeUnit.SECONDS)) { "Native proof exceeded its deadline" }
            val result = JSONObject(bounded(stdout))
            result.put("nativeExitCode", process.exitValue())
            result.put("nativeStderr", bounded(stderr))
            File(evidence, "stderr.txt").writeText(result.getString("nativeStderr"))
            result.put("device", JSONObject().put("model", Build.MODEL).put("manufacturer", Build.MANUFACTURER)
                .put("androidRelease", Build.VERSION.RELEASE).put("api", Build.VERSION.SDK_INT)
                .put("abis", Build.SUPPORTED_ABIS.joinToString(",")).put("hardware", Build.HARDWARE)
                .put("fingerprint", Build.FINGERPRINT))
            result.put("supervisorUid", android.os.Process.myUid())
            result.put("supervisorPid", android.os.Process.myPid())
            result.put("apkSha256", sha256(File(applicationInfo.sourceDir).readBytes()))
            result.put("nativeSha256", sha256(executable.readBytes()))
            result.put("installedExecutableWritable", executable.canWrite())
            result.put("evidenceDirectory", work.name)
            if (result.optString("status") == "PASS") {
                check(process.exitValue() == 0) { "PASS contradicts native exit code" }
                check(result.getInt("uid") == android.os.Process.myUid() && result.getInt("uid") != 0) { "Wrong native UID" }
                check(result.getInt("parentPid") == android.os.Process.myPid()) { "Wrong native parent" }
                check(result.getString("architecture") == "aarch64") { "Not native ARM64 execution" }
                val tests = result.getJSONArray("tests")
                check(tests.length() == 5 && (0 until tests.length()).all { tests.getJSONObject(it).getString("status") == "PASS" }) { "Incomplete native suite" }
                for (i in 0 until tests.length()) {
                    val item = tests.getJSONObject(i)
                    if (item.getString("name") == "B-existing-destination") {
                        val data = item.getJSONObject("evidence")
                        data.put("beforeSha256", sha256(data.getString("beforeContent").toByteArray(Charsets.UTF_8)))
                        data.put("afterSha256", sha256(data.getString("afterContent").toByteArray(Charsets.UTF_8)))
                    }
                }
            }
            val text = result.toString()
            File(work, "result.json").writeText(text)
            // This convenience copy is diagnostic output, never a durable-session claim.
            File(evidence, "result.json").writeText(text)
            return text
        } finally {
            reap(process)
            synchronized(lock) { child = null }
        }
    }
    private fun reap(process: java.lang.Process) {
        var interrupted = Thread.interrupted()
        try {
            if (process.isAlive) process.destroy()
            val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5)
            while (process.isAlive && System.nanoTime() < deadline) {
                try { process.waitFor(100, TimeUnit.MILLISECONDS) }
                catch (_: InterruptedException) { interrupted = true }
            }
            if (process.isAlive) {
                process.destroyForcibly()
                val killDeadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(3)
                while (process.isAlive && System.nanoTime() < killDeadline) {
                    try { process.waitFor(100, TimeUnit.MILLISECONDS) }
                    catch (_: InterruptedException) { interrupted = true }
                }
                check(!process.isAlive) { "Native proof did not exit after KILL" }
            }
            process.inputStream.close()
            process.errorStream.close()
            process.outputStream.close()
        } finally { if (interrupted) Thread.currentThread().interrupt() }
    }
    private val messenger = Messenger(Handler(Looper.getMainLooper()) { message ->
        if (message.what == 1 && message.replyTo != null && started.compareAndSet(false, true)) {
            val reply = message.replyTo
            executor.execute {
                val text = try { runProof() }
                catch (error: Exception) {
                    val failure = JSONObject().put("schemaVersion", 1).put("status", "BLOCKED")
                        .put("error", "${error.javaClass.simpleName}: ${error.message}").put("gate2Passed", false).toString()
                    try { File(filesDir, "atomic-probe/result.json").writeText(failure) }
                    catch (writeError: Exception) { Log.e("HarnessAtomicProof", "Cannot retain failure", writeError) }
                    failure
                }
                try { reply.send(Message.obtain(null, 1).apply { data = Bundle().apply { putString("result", text) } }) }
                catch (_: RemoteException) { /* Consumer left; private evidence remains. */ }
            }
        }
        true
    })
    override fun onBind(intent: Intent): IBinder = messenger.binder
    override fun onDestroy() {
        synchronized(lock) { cancelled = true; child?.destroy() }
        executor.shutdownNow()
        super.onDestroy()
        // The worker owns child reaping. Its native descendants have parent-death signals.
    }
}
