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
    private var commandActive = false
    private var terminalActive = false
    private var processActive = false
    private var commandService: Messenger? = null
    private var approvalDialog: AlertDialog? = null
    private val timeout = Runnable { output.text = "BLOCKED: runtime probe timed out"; release() }

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        output = TextView(this).apply {
            text = "Select a diagnostic. Original tool approval and fixed process/PTY capability tests are separate. Model requests remain untested."
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
            text = "Run original tool + native approval proof"
            setOnClickListener {
                AlertDialog.Builder(this@RuntimeProofActivity).setTitle("Original Harness command qualification")
                    .setMessage("Two native prompts follow: DENY the first, APPROVE the second. Only /system/bin/pwd with no arguments may run. Keep the app visible; leaving cancels the proof. Existing sessions are preserved.")
                    .setNegativeButton("Cancel", null).setPositiveButton("Start test") { _, _ -> runProbe(command = true) }.show()
            }
        })
        layout.addView(Button(this).apply {
            text = "Run fixed process + PTY capability tests"
            setOnClickListener {
                val executable = File(applicationInfo.nativeLibraryDir, "libharness_process_probe.so").canonicalPath
                AlertDialog.Builder(this@RuntimeProofActivity).setTitle("Authorize fixed OS tests once?")
                    .setMessage("Ordinary app UID ${android.os.Process.myUid()}. Runs fixed stdout/stderr, stdin, missing-executable, TERM/KILL, cooperative child-group and PTY input/resize tests. Invokes /system/bin/sh only with the bundled fixed printf/pwd/exit script. Checks /system/bin command availability. No caller-selected command or root.\n\nExecutable: $executable\nWorkspace: app-private process-probe/run-*\n\nLeaving the Activity cancels this test. This does not enable the original terminal or general shell tools.")
                    .setNegativeButton("Deny", null)
                    .setPositiveButton("Run fixed suite once") { _, _ -> runProbe(process = true) }.show()
            }
        })
        layout.addView(Button(this).apply {
            text = "Run original node-pty proof"
            setOnClickListener {
                AlertDialog.Builder(this@RuntimeProofActivity).setTitle("Authorize original node-pty fixed tests?")
                    .setMessage("Runs bundled original node-pty against fixed benign native fixtures under app UID ${android.os.Process.myUid()}. Tests TTY input/resize, exit 7, Ctrl-C, TERM and timeout/KILL. No shell, caller-selected command, Root or Termux. Leaving cancels the qualification. This is not the original Harness terminal backend.")
                    .setNegativeButton("Deny", null).setPositiveButton("Run fixed suite once") { _, _ -> runProbe(nodePty = true) }.show()
            }
        })
        layout.addView(Button(this).apply {
            text = "Run original terminal + native approval"
            setOnClickListener {
                AlertDialog.Builder(this@RuntimeProofActivity).setTitle("Original terminal qualification")
                    .setMessage("DENY the first native prompt, APPROVE the second. Runs only the installed benign TTY fixture, fixed input and resize through the original Harness registry. No shell, Root or Termux. Keep the app visible; leaving cancels this test. Existing sessions are preserved.")
                    .setNegativeButton("Cancel", null).setPositiveButton("Start test") { _, _ -> runProbe(terminal = true) }.show()
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

    private fun runProbe(packaged: Boolean = false, profile: Boolean = false, command: Boolean = false, process: Boolean = false, nodePty: Boolean = false, terminal: Boolean = false) {
        release()
        commandActive = command || terminal
        terminalActive = terminal
        processActive = process || nodePty
        val current = generation
        output.text = if (terminal) "Starting original terminal qualification…" else if (nodePty) "Running original node-pty fixed tests…" else if (process) "Running authorized fixed OS tests…" else "Starting embedded API probe…"
        val replies = Messenger(Handler(Looper.getMainLooper()) { message ->
            if (generation == current && (command || terminal) && message.what == 2) {
                val request = org.json.JSONObject(message.data.getString("result") ?: "{}")
                val decide: (Boolean) -> Unit = { allow ->
                    try { commandService?.send(Message.obtain(null, 2).apply { data = Bundle().apply {
                        putString("callId", request.getString("callId")); putString("terminalId", request.optString("terminalId")); putBoolean("allow", allow)
                    } }) } catch (_: RemoteException) { output.text = "BLOCKED: approval connection lost"; release() }
                }
                approvalDialog?.dismiss()
                val terminalDetails = if (request.has("terminalId")) "\nTerminal: ${request.getString("terminalId")}\nOwner: ${request.getString("ownerId")}\nBackend: ${request.getString("backend")}\nInitial geometry: ${request.getInt("columns")} x ${request.getInt("rows")}" else ""
                approvalDialog = AlertDialog.Builder(this).setTitle(if (terminal) "Native terminal allocation" else "Native command approval")
                    .setMessage("Test action: ${request.getString("expectedTestAction")}\n\nCommand: ${request.getString("executable")}\nArguments: ${request.getJSONArray("arguments")}\nDirectory: ${request.getString("cwd")}\nSession: ${request.getString("sessionId")}\nTool call: ${request.getString("callId")}\nExecution UID: ${request.getInt("uid")} (ordinary app UID)${terminalDetails}\nAction: ${request.getString("action")}")
                    .setNegativeButton("Deny") { _, _ -> decide(false) }
                    .setPositiveButton("Approve once") { _, _ -> decide(true) }
                    .setOnCancelListener { decide(false) }.create().also { it.show() }
            } else if (generation == current) {
                output.text = message.data.getString("result") ?: "BLOCKED: missing probe result"
                release()
            }
            true
        })
        val service = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName, binder: IBinder) {
                if (generation != current) return
                try { if (command || terminal) commandService = Messenger(binder); Messenger(binder).send(Message.obtain(null, 1).apply { replyTo = replies }) }
                catch (_error: RemoteException) { output.text = "BLOCKED: runtime disconnected"; release() }
            }
            override fun onServiceDisconnected(name: ComponentName) {
                if (generation == current) { output.text = "BLOCKED: runtime process exited"; release() }
            }
        }
        val target = if (terminal) TerminalProbeService::class.java else if (nodePty) NodePtyProbeService::class.java else if (process) ProcessCapabilityService::class.java else if (command) CommandProbeService::class.java else if (profile) ProfileProbeService::class.java else if (packaged) ExecutableProbeService::class.java else RuntimeService::class.java
        if (bindService(Intent(this, target), service, Context.BIND_AUTO_CREATE)) {
            connection = service
            handler.postDelayed(timeout, if (terminal) 280000 else if (process || nodePty) 60000 else if (command) 240000 else if (profile) 120000 else if (packaged) 60000 else 30000)
        } else output.text = "BLOCKED: cannot bind runtime"
    }

    private fun release() {
        commandActive = false
        terminalActive = false
        processActive = false
        commandService = null
        approvalDialog?.dismiss(); approvalDialog = null
        generation++
        handler.removeCallbacks(timeout)
        connection?.let { unbindService(it) }
        connection = null
    }
    override fun onStop() { if (commandActive || processActive) { output.text = if (terminalActive) "BLOCKED: original terminal proof cancelled while leaving the Activity" else if (processActive) "BLOCKED: process qualification cancelled while leaving the Activity" else "BLOCKED: command proof cancelled while leaving the Activity"; release() }; super.onStop() }
    override fun onDestroy() { release(); super.onDestroy() }
}
