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
        val entry = File(root, "runtime/lib/bin.js")
        check(entry.isFile) { "Packaged production dsh CLI entry unavailable" }
        val home = File(filesDir, "harness-home").canonicalFile.apply { check(mkdirs() || isDirectory) }
        val documents = File(filesDir, "harness-documents").canonicalFile.apply { check(mkdirs() || isDirectory) }
        val workspace = androidDefaultWorkspaceDirectory(documents).apply { check(mkdirs() || isDirectory) }
        val patch = File(filesDir, "android-web-runtime.patch.yml")
        patch.writeText(
            "- id: workspace-controller\n"
                + "  config:\n"
                + "    defaultWorkspacePath: ${yamlPath(workspace)}\n",
        )
        val builder = ProcessBuilder(
            executable.absolutePath, entry.absolutePath,
            "--profile", "web", "--patch", patch.absolutePath,
            "--host", "127.0.0.1", "--port", "0", "--no-open",
        ).directory(workspace).redirectErrorStream(true)
        builder.environment()["DSH_HOME"] = home.absolutePath
        builder.environment()["HOME"] = home.absolutePath
        builder.environment()["TMPDIR"] = cacheDir.absolutePath
        builder.environment()["DSH_TELEMETRY_DISABLED"] = "1"
        builder.environment()["LD_LIBRARY_PATH"] = applicationInfo.nativeLibraryDir
        val process = builder.start()
        server = process
        process.outputStream.close()
        return awaitWebProfileUrl(process, STARTUP_TIMEOUT_SECONDS * 1_000)
    }

    private fun yamlPath(file: File): String = "'" + file.absolutePath.replace("'", "''") + "'"

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
        imageRoot = null
    }

    override fun onBind(intent: Intent): IBinder = messenger.binder

    override fun onDestroy() {
        executor.shutdownNow()
        stopServer()
        super.onDestroy()
    }

    private companion object {
        const val STARTUP_TIMEOUT_SECONDS = 45L
    }
}

/** Android's intentional app-private default path, shared by cwd and the Workspace controller. */
internal fun androidDefaultWorkspaceDirectory(documents: File): File =
    File(documents, "deepseek-harness/default").canonicalFile
