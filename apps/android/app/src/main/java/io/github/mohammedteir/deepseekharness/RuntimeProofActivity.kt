package io.github.mohammedteir.deepseekharness

import android.app.Activity
import android.content.*
import android.os.*
import android.widget.*

/** Native API diagnostics only; no replacement Harness frontend or agent. */
class RuntimeProofActivity : Activity() {
    private lateinit var output: TextView
    private var connection: ServiceConnection? = null
    private val handler = Handler(Looper.getMainLooper())
    private var generation = 0
    private val timeout = Runnable { output.text = "BLOCKED: runtime probe timed out"; release() }

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        output = TextView(this).apply { text = "Runtime proof only. Harness profile, sessions and tools are not initialized." }
        layout.addView(Button(this).apply { text = "Run embedded Node API probe"; setOnClickListener { runProbe() } })
        layout.addView(output)
        setContentView(layout)
    }

    private fun runProbe() {
        release()
        val current = generation
        output.text = "Starting embedded API probe…"
        val replies = Messenger(Handler(Looper.getMainLooper()) { message ->
            if (generation == current) {
                output.text = message.data.getString("result") ?: "BLOCKED: missing probe result"
                release()
            }
            true
        })
        val service = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName, binder: IBinder) {
                if (generation != current) return
                try { Messenger(binder).send(Message.obtain(null, 1).apply { replyTo = replies }) }
                catch (_error: RemoteException) { output.text = "BLOCKED: runtime disconnected"; release() }
            }
            override fun onServiceDisconnected(name: ComponentName) {
                if (generation == current) { output.text = "BLOCKED: runtime process exited"; release() }
            }
        }
        if (bindService(Intent(this, RuntimeService::class.java), service, Context.BIND_AUTO_CREATE)) {
            connection = service
            handler.postDelayed(timeout, 30000)
        } else output.text = "BLOCKED: cannot bind runtime"
    }

    private fun release() {
        generation++
        handler.removeCallbacks(timeout)
        connection?.let { unbindService(it) }
        connection = null
    }
    override fun onDestroy() { release(); super.onDestroy() }
}
