package io.github.mohammedteir.deepseekharness

import android.app.Activity
import android.app.AlertDialog
import android.content.*
import android.os.*
import android.widget.*
import java.io.File

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
        output = TextView(this).apply {
            text = "Select a diagnostic. The profile test starts original Harness and checks session recovery; commands and model requests remain untested."
            setTextIsSelectable(true)
        }
        layout.addView(Button(this).apply { text = "Run embedded Node API probe"; setOnClickListener { runProbe() } })
        layout.addView(Button(this).apply {
            text = "Run packaged Node + child probe"
            setOnClickListener {
                val command = listOf(File(applicationInfo.nativeLibraryDir, "libnode_executable.so").absolutePath,
                    File(filesDir, "executable-probe/executable-smoke.mjs").absolutePath,
                    File(filesDir, "executable-probe/result.json").absolutePath)
                AlertDialog.Builder(this@RuntimeProofActivity).setTitle("Run fixed Node comparison?")
                    .setMessage("App UID only. Runs the APK's API tests and one fixed child Node program. No Harness tool approval is proved.\n\n${command.joinToString("\n")}")
                    .setNegativeButton("Cancel", null)
                    .setPositiveButton("Run once") { _, _ -> runProbe(true) }.show()
            }
        })
        layout.addView(Button(this).apply {
            text = "Run original Harness profile + session recovery"
            setOnClickListener {
                AlertDialog.Builder(this@RuntimeProofActivity).setTitle("Run original Harness profile?")
                    .setMessage("Starts and restarts the original sdk-minimal profile with execution providers disabled. Creates persistent app-private session files. No model request or approved command is tested.")
                    .setNegativeButton("Cancel", null)
                    .setPositiveButton("Run once") { _, _ -> runProbe(profile = true) }.show()
            }
        })
        layout.addView(Button(this).apply {
            text = "Copy complete result"
            setOnClickListener {
                (getSystemService(CLIPBOARD_SERVICE) as ClipboardManager).setPrimaryClip(ClipData.newPlainText("Harness runtime proof", output.text))
                Toast.makeText(this@RuntimeProofActivity, "Result copied", Toast.LENGTH_SHORT).show()
            }
        })
        layout.addView(ScrollView(this).apply { addView(output) }, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(layout)
    }

    private fun runProbe(packaged: Boolean = false, profile: Boolean = false) {
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
        val target = if (profile) ProfileProbeService::class.java else if (packaged) ExecutableProbeService::class.java else RuntimeService::class.java
        if (bindService(Intent(this, target), service, Context.BIND_AUTO_CREATE)) {
            connection = service
            handler.postDelayed(timeout, if (profile) 120000 else if (packaged) 60000 else 30000)
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
