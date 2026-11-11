package io.github.mohammedteir.deepseekharness.packaging

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.os.Bundle
import android.widget.*
import java.io.File
import java.util.concurrent.TimeUnit

/** Real Bionic/loader checks only; no Node or Harness implementation. */
object PackagingNative {
    init { System.loadLibrary("packaging_probe") }
    external fun sharedInfo(): String
}

data class ExecutionEvidence(val path: String, val stdout: String, val exitCode: Int, val writable: Boolean)

/** Execute only the installed, fixed fixture, with no caller-supplied path or arguments. */
fun runInstalledFixture(context: Context): ExecutionEvidence {
    val file = File(context.applicationInfo.nativeLibraryDir, "libexecution_probe.so")
    check(!file.canWrite()) { "Installer-owned executable is unexpectedly writable" }
    val process = ProcessBuilder(file.absolutePath).redirectErrorStream(true).start()
    try {
        process.outputStream.close()
        check(process.waitFor(30, TimeUnit.SECONDS)) { "Native packaging fixture timed out" }
        return ExecutionEvidence(file.absolutePath, process.inputStream.bufferedReader().readText().take(4096), process.exitValue(), file.canWrite())
    } finally {
        process.destroyForcibly()
        process.inputStream.close()
        process.errorStream.close()
    }
}

class PackagingProofActivity : Activity() {
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val result = TextView(this).apply { text = "OS packaging checks only. Node and Harness are not included." }
        layout.addView(result)
        layout.addView(Button(this).apply {
            text = "Check installed native packaging"
            setOnClickListener {
                val path = File(applicationInfo.nativeLibraryDir, "libexecution_probe.so")
                AlertDialog.Builder(this@PackagingProofActivity).setTitle("Allow fixed packaging fixture?")
                    .setMessage("App UID only. No arguments. Reads UID, PID and page size.\n$path")
                    .setNegativeButton("Deny", null)
                    .setPositiveButton("Allow once") { _, _ ->
                        Thread {
                            val evidence = try { "JNI: ${PackagingNative.sharedInfo()}\nExecutable: ${runInstalledFixture(this@PackagingProofActivity)}" }
                            catch (error: Exception) { "BLOCKED: ${error.javaClass.simpleName}: ${error.message}" }
                            catch (error: UnsatisfiedLinkError) { "BLOCKED: ${error.message}" }
                            runOnUiThread { if (!isDestroyed) result.text = evidence }
                        }.start()
                    }.show()
            }
        })
        setContentView(layout)
    }
}
