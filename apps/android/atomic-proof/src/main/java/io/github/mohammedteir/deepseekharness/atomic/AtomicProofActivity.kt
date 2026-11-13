package io.github.mohammedteir.deepseekharness.atomic

import android.app.Activity
import android.app.AlertDialog
import android.content.*
import android.os.*
import android.widget.*

/** Standalone diagnostic screen, separate from the original Harness frontend and sessions. */
class AtomicProofActivity : Activity() {
    private lateinit var output: TextView
    private lateinit var run: Button
    private var connection: ServiceConnection? = null
    private val handler = Handler(Looper.getMainLooper())
    private var generation = 0
    private val timeout = Runnable { output.text = "BLOCKED: native test timed out; retain private evidence with ADB"; release() }
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        output = TextView(this).apply {
            text = "APK #1: isolated atomic persistence tests. Does not change Harness sessions. Physical-device verification is pending."
            setTextIsSelectable(true)
        }
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        run = Button(this).apply {
            text = "Run native atomic persistence tests"
            setOnClickListener {
                AlertDialog.Builder(this@AtomicProofActivity).setTitle("Run fixed filesystem tests?")
                    .setMessage("Uses this app's private test directory and ordinary UID. Runs 128 competing publisher processes and kills 10 test children at controlled checkpoints. Keeps evidence; no Harness session files are touched.")
                    .setNegativeButton("Cancel", null).setPositiveButton("Run once") { _, _ -> startProof() }.show()
            }
        }
        layout.addView(run)
        layout.addView(Button(this).apply {
            text = "Copy complete result"
            setOnClickListener {
                (getSystemService(CLIPBOARD_SERVICE) as ClipboardManager).setPrimaryClip(ClipData.newPlainText("Atomic proof result", output.text))
                Toast.makeText(this@AtomicProofActivity, "Result copied", Toast.LENGTH_SHORT).show()
            }
        })
        layout.addView(ScrollView(this).apply { addView(output) }, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(layout)
    }
    private fun startProof() {
        release(); val current = generation
        output.text = "Running native filesystem tests…"; run.isEnabled = false
        val replies = Messenger(Handler(Looper.getMainLooper()) { message ->
            if (generation == current) { output.text = message.data.getString("result") ?: "BLOCKED: missing result"; release() }
            true
        })
        val service = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName, binder: IBinder) {
                if (generation != current) return
                try { Messenger(binder).send(Message.obtain(null, 1).apply { replyTo = replies }) }
                catch (_: RemoteException) { output.text = "BLOCKED: native supervisor disconnected"; release() }
            }
            override fun onServiceDisconnected(name: ComponentName) {
                if (generation == current) { output.text = "BLOCKED: native supervisor exited"; release() }
            }
        }
        if (bindService(Intent(this, AtomicProofService::class.java), service, BIND_AUTO_CREATE)) {
            connection = service; handler.postDelayed(timeout, 100000)
        } else { output.text = "BLOCKED: cannot bind native proof"; run.isEnabled = true }
    }
    private fun release() {
        generation++; handler.removeCallbacks(timeout)
        connection?.let { unbindService(it) }; connection = null
        if (::run.isInitialized) run.isEnabled = true
    }
    override fun onDestroy() { release(); super.onDestroy() }
}
