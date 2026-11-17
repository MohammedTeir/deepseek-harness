package io.github.mohammedteir.deepseekharness

import android.app.Service
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.Message
import android.os.Messenger
import android.os.RemoteException
import android.util.Log
import java.io.File
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/** Starts the real packaged web profile and publishes its authenticated loopback URL. */
class OriginalWebRuntimeService : Service() {
    private val executor = Executors.newSingleThreadExecutor()
    private val started = AtomicBoolean(false)
    private var server: Process? = null
    private var imageRoot: File? = null
    private var readyUrl: String? = null

    private fun reply(reply: Messenger, value: String) {
        try {
            reply.send(Message.obtain(null, 1).apply {
                data = Bundle().apply { putString("url", value) }
            })
        } catch (_: RemoteException) { }
    }

    private fun startWebProfile(): String {
        val root = ProfileImage.install(assets, filesDir)
        imageRoot = root
        val executable = File(applicationInfo.nativeLibraryDir, "libnode_executable.so").canonicalFile
        check(executable.isFile && !executable.canWrite()) { "Installed Node executable unavailable" }
        val entry = File(root, "apps/cli/lib/bin.js")
        check(entry.isFile) { "Packaged dsh CLI entry unavailable" }
        val home = File(root, "home").apply { mkdirs() }
        val builder = ProcessBuilder(
            executable.absolutePath, entry.absolutePath,
            "--profile", "web", "--host", "127.0.0.1", "--port", "0", "--no-open",
        ).directory(root).redirectErrorStream(true)
        builder.environment()["DSH_HOME"] = home.absolutePath
        builder.environment()["HOME"] = filesDir.absolutePath
        builder.environment()["TMPDIR"] = cacheDir.absolutePath
        builder.environment()["DSH_TELEMETRY_DISABLED"] = "1"
        builder.environment()["LD_LIBRARY_PATH"] = applicationInfo.nativeLibraryDir
        val process = builder.start()
        server = process
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(45)
        val output = StringBuilder()
        process.inputStream.bufferedReader().use { reader ->
            while (System.nanoTime() < deadline) {
                if (!reader.ready()) {
                    if (!process.isAlive) break
                    Thread.sleep(25)
                    continue
                }
                val line = reader.readLine() ?: break
                output.appendLine(line)
                if (line.startsWith("dsh web: ")) return line.removePrefix("dsh web: ").trim()
            }
        }
        val suffix = output.toString().takeLast(8192)
        throw IllegalStateException("Web profile did not publish a URL: $suffix")
    }

    private val messenger = Messenger(Handler(Looper.getMainLooper()) { message ->
        if (message.what == 1 && message.replyTo != null) {
            val reply = message.replyTo
            val published = readyUrl
            if (published != null) {
                reply(reply, published)
            } else if (started.compareAndSet(false, true)) {
                executor.execute {
                    val result = try {
                        startWebProfile()
                    } catch (error: Exception) {
                        stopServer()
                        "BLOCKED: ${error.javaClass.simpleName}: ${error.message}"
                    }
                    if (!result.startsWith("BLOCKED:")) readyUrl = result
                    reply(reply, result)
                }
            }
        }
        true
    })

    private fun stopServer() {
        server?.let { process ->
            process.destroy()
            if (!process.waitFor(3, TimeUnit.SECONDS)) process.destroyForcibly()
        }
        server = null
        imageRoot?.parentFile?.let { ProfileImage.remove(it) }
        imageRoot = null
    }

    override fun onBind(intent: Intent): IBinder = messenger.binder

    override fun onDestroy() {
        executor.shutdownNow()
        stopServer()
        super.onDestroy()
    }
}
