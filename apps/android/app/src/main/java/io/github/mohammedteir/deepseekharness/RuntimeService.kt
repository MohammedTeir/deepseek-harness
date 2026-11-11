package io.github.mohammedteir.deepseekharness

import android.app.Service
import android.content.Intent
import android.os.*
import java.io.File
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/** One-shot embedded API probe; its result never implies Harness startup. */
class RuntimeService : Service() {
    private external fun probeNode(): String
    private external fun runNode(script: String, output: String): Int
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
                    val output = File(directory, "result.json")
                    if (output.exists() && !output.delete()) throw IllegalStateException("Stale result could not be removed")
                    val exit = runNode(script.absolutePath, output.absolutePath)
                    when {
                        exit < 0 -> probeNode()
                        exit != 0 -> "BLOCKED: embedded Node API probe exited with code $exit"
                        !output.isFile -> "BLOCKED: embedded Node returned without API evidence"
                        else -> output.readText().take(4096)
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
