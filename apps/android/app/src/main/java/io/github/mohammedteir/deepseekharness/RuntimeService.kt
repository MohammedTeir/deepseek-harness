package io.github.mohammedteir.deepseekharness

import android.app.Service
import android.content.Intent
import android.os.*
import java.io.File
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean
import org.json.JSONObject

/** One-shot embedded API probe; its result never implies Harness startup. */
class RuntimeService : Service() {
    private fun readDiagnostic(file: File, limit: Int): String = file.reader().use { reader ->
        val buffer = CharArray(limit)
        var used = 0
        while (used < limit) {
            val count = reader.read(buffer, used, limit - used)
            if (count < 0) break
            used += count
        }
        String(buffer, 0, used)
    }
    private external fun probeNode(): String
    private external fun runNode(script: String, output: String, diagnostic: String): Int
    private val executor = Executors.newSingleThreadExecutor { task ->
        Thread(null, task, "HarnessNode", 8L * 1024 * 1024)
    }
    private val started = AtomicBoolean(false)
    private val messenger = Messenger(Handler(Looper.getMainLooper()) { message ->
        if (message.what == 1 && message.replyTo != null && started.compareAndSet(false, true)) {
            val reply = message.replyTo
            executor.execute {
                val result = try {
                    System.loadLibrary("harness_probe")
                    val directory = File(filesDir, "runtime-probe").apply { mkdirs() }
                    val script = File(directory, "smoke.mjs")
                    assets.open("runtime/smoke.mjs").use { input -> script.outputStream().use(input::copyTo) }
                    assets.open("runtime/harness-flock.mjs").use { input ->
                        File(directory, "harness-flock.mjs").outputStream().use(input::copyTo)
                    }
                    val output = File(directory, "result.json")
                    if (output.exists() && !output.delete()) throw IllegalStateException("Stale result could not be removed")
                    val diagnostic = File(directory, "stderr.txt")
                    if (diagnostic.exists() && !diagnostic.delete()) throw IllegalStateException("Stale diagnostics could not be removed")
                    val exit = runNode(script.absolutePath, output.absolutePath, diagnostic.absolutePath)
                    when {
                        exit == -1 || exit == -2 -> probeNode()
                        exit == -4 -> "BLOCKED: cannot capture Node stderr"
                        exit == -5 -> "BLOCKED: cannot restore Node stderr"
                        exit < 0 -> "BLOCKED: JNI could not prepare Node arguments (code $exit)"
                        exit != 0 -> buildString {
                            append("BLOCKED: embedded Node API probe exited with code $exit\n")
                            if (output.isFile) append(readDiagnostic(output, 4096))
                            append("\nNode stderr:\n")
                            append(if (diagnostic.isFile) readDiagnostic(diagnostic, 8192) else "No diagnostics file")
                        }
                        !output.isFile -> "BLOCKED: embedded Node returned without API evidence"
                        else -> {
                            val evidence = JSONObject(readDiagnostic(output, 4096))
                            check(evidence.getInt("pid") == android.os.Process.myPid()) { "Node PID does not match runtime process" }
                            evidence.put("androidUid", android.os.Process.myUid())
                            evidence.put("androidPid", android.os.Process.myPid())
                            evidence.put("identitySource", "android.os.Process")
                            val pending = File(directory, "result.host.pending")
                            pending.writeText(evidence.toString())
                            check(pending.renameTo(output)) { "Host identity evidence could not be persisted" }
                            evidence.toString()
                        }
                    }
                } catch (_: UnsatisfiedLinkError) { "BLOCKED: native probe library could not load" }
                catch (error: Exception) { "BLOCKED: ${error.javaClass.simpleName} during runtime probe" }
                try { reply.send(Message.obtain(null, 1).apply { data = Bundle().apply { putString("result", result) } }) }
                catch (_: RemoteException) { /* Activity left; no result consumer remains. */ }
            }
        }
        true
    })
    override fun onBind(intent: Intent): IBinder = messenger.binder
    override fun onDestroy() {
        executor.shutdownNow()
        super.onDestroy()
        // Manifest keeps this service in :runtime; terminate V8's process-global state.
        android.os.Process.killProcess(android.os.Process.myPid())
    }
}
