package io.github.mohammedteir.deepseekharness

import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit

/** Wait for the original web profile's URL while retaining output and the child exit state. */
internal fun awaitWebProfileUrl(process: Process, timeoutMillis: Long): String {
    require(timeoutMillis > 0) { "Startup timeout must be positive" }

    val output = StringBuilder()
    val readyUrls = LinkedBlockingQueue<String>()
    val reader = Thread({
        try {
            process.inputStream.bufferedReader().use { stream ->
                while (true) {
                    val line = stream.readLine() ?: break
                    appendStartupDiagnostic(output, line)
                    if (line.startsWith(READY_PREFIX)) {
                        readyUrls.offer(line.removePrefix(READY_PREFIX).trim())
                    }
                }
            }
        } catch (error: Exception) {
            appendStartupDiagnostic(output, "Output capture failed: ${error.javaClass.simpleName}: ${error.message}")
        }
    }, "deepseek-web-runtime-output").apply {
        isDaemon = true
        start()
    }

    val deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(timeoutMillis)
    while (true) {
        val remaining = deadline - System.nanoTime()
        if (remaining <= 0) break
        val url = readyUrls.poll(minOf(remaining, POLL_INTERVAL_NANOS), TimeUnit.NANOSECONDS)
        if (url != null) return url
        if (!process.isAlive) {
            process.waitFor()
            reader.join(READER_JOIN_MILLIS)
            readyUrls.poll()?.let { return it }
            throw IllegalStateException(
                "Web profile exited before publishing a URL (exit code ${process.exitValue()}): ${snapshot(output)}",
            )
        }
    }

    val aliveAtDeadline = process.isAlive
    if (aliveAtDeadline) {
        process.destroy()
        if (!process.waitFor(TERMINATE_GRACE_MILLIS, TimeUnit.MILLISECONDS)) {
            process.destroyForcibly()
            process.waitFor(TERMINATE_GRACE_MILLIS, TimeUnit.MILLISECONDS)
        }
    }
    reader.join(READER_JOIN_MILLIS)
    val exitState = if (process.isAlive) "still running" else "exit code ${process.exitValue()}"
    throw IllegalStateException(
        "Web profile startup timed out after ${timeoutMillis} ms (alive at deadline=$aliveAtDeadline; $exitState): ${snapshot(output)}",
    )
}

private fun appendStartupDiagnostic(output: StringBuilder, line: String) {
    synchronized(output) {
        output.appendLine(line)
        if (output.length > MAX_DIAGNOSTIC_CHARS) {
            output.delete(0, output.length - MAX_DIAGNOSTIC_CHARS)
        }
    }
}

private fun snapshot(output: StringBuilder): String = synchronized(output) { output.toString().trimEnd() }

private const val READY_PREFIX = "dsh web: "
private const val MAX_DIAGNOSTIC_CHARS = 64 * 1024
private const val READER_JOIN_MILLIS = 1_000L
private const val TERMINATE_GRACE_MILLIS = 1_000L
private const val POLL_INTERVAL_NANOS = 100_000_000L
