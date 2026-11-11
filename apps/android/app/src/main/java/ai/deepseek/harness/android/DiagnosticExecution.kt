package ai.deepseek.harness.android

import java.io.File
import java.util.UUID
import java.util.concurrent.TimeUnit

/** Native-only, single-use authorization for the fixed pwd diagnostic. No WebView API exposes it. */
class DiagnosticAuthorization(private val clock: () -> Long = System::nanoTime) {
    private var pending: Pair<String, Long>? = null

    @Synchronized fun approve(): String {
        val token = UUID.randomUUID().toString()
        pending = token to clock()
        return token
    }

    @Synchronized fun consume(token: String): Boolean {
        val grant = pending ?: return false
        if (grant.first != token) return false
        pending = null
        val elapsed = clock() - grant.second
        return elapsed >= 0 && elapsed < TimeUnit.SECONDS.toNanos(30)
    }

    @Synchronized fun revoke() { pending = null }
}

data class DiagnosticResult(val stdout: String, val stderr: String, val exitCode: Int?, val timedOut: Boolean)

/** Executes only a fixed app-scoped command after trusted native consent; no general shell or PTY claim. */
class DiagnosticExecution(private val authorization: DiagnosticAuthorization) {
    fun pwd(token: String, directory: File): DiagnosticResult {
        check(authorization.consume(token)) { "Execution authorization missing, expired, or consumed" }
        val process = ProcessBuilder("/system/bin/sh", "-c", "pwd")
            .directory(directory).apply { environment().clear(); environment()["PATH"] = "/system/bin" }.start()
        try {
            process.outputStream.close()
            val ended = process.waitFor(3, TimeUnit.SECONDS)
            if (!ended) {
                process.destroyForcibly()
                process.waitFor()
            }
            return DiagnosticResult(
                process.inputStream.bufferedReader().readText(),
                process.errorStream.bufferedReader().readText(),
                process.exitValue(), !ended,
            )
        } finally {
            process.inputStream.close()
            process.errorStream.close()
            process.destroy()
        }
    }
}
