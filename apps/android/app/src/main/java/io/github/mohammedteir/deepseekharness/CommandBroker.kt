package io.github.mohammedteir.deepseekharness

import android.net.LocalServerSocket
import android.net.LocalSocket
import android.os.Process
import android.util.JsonReader
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.StringReader
import java.security.MessageDigest
import java.util.UUID
import java.util.concurrent.CompletableFuture
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/** Per-run AF_UNIX broker. Same-UID reviewed code only; not a hostile-plugin sandbox. */
class CommandBroker(private val workspace: File, private val showApproval: (JSONObject) -> Unit) : AutoCloseable {
    val sessionId = "android-command-${UUID.randomUUID()}"
    val callIds = listOf("deny-${UUID.randomUUID()}", "allow-${UUID.randomUUID()}")
    private val uid = Process.myUid()
    private val secret = UUID.randomUUID().toString() + UUID.randomUUID().toString()
    private val name = "harness-command-${UUID.randomUUID()}"
    private val server: LocalServerSocket
    private val closed = AtomicBoolean(false)
    private val workers = Executors.newFixedThreadPool(2)
    private val sockets = ConcurrentHashMap.newKeySet<LocalSocket>()
    private val grants = ConcurrentHashMap<String, CommandGrant>()
    private val owners = ConcurrentHashMap<String, FixedPwdExecution>()
    private val decisions = ConcurrentHashMap<String, CompletableFuture<String>>()
    private val audit = java.util.Collections.synchronizedList(mutableListOf<JSONObject>())
    private val acceptThread = Thread {
        while (!closed.get()) {
            val socket = try { server.accept() } catch (_: Exception) { break }
            if (sockets.size >= 4) { socket.close(); continue }
            sockets.add(socket)
            workers.execute { try { socket.use { handle(it) } } finally { sockets.remove(socket) } }
        }
    }
    init {
        check(uid > 0 && workspace.isDirectory && workspace == workspace.canonicalFile)
        check(android.system.Os.stat(workspace.path).st_uid == uid) { "Workspace owner mismatch" }
        val mode = android.system.Os.stat("/system/bin/pwd").st_mode
        check(mode and (android.system.OsConstants.S_ISUID or android.system.OsConstants.S_ISGID) == 0) { "Set-ID executable is forbidden" }
        server = LocalServerSocket(name)
        acceptThread.start()
    }
    fun launchEnvironment(): Map<String, String> = mapOf(
        "HARNESS_COMMAND_SOCKET" to name, "HARNESS_COMMAND_SECRET" to secret,
        "HARNESS_COMMAND_SESSION" to sessionId, "HARNESS_COMMAND_CALLS" to JSONArray(callIds).toString())
    private fun identity(callId: String) = CommandGrant.Request(sessionId, callId, "/system/bin/pwd", emptyList(), workspace.path, uid)
    private fun snapshot(callId: String) = JSONObject().put("sessionId", sessionId).put("callId", callId)
        .put("executable", "/system/bin/pwd").put("arguments", JSONArray()).put("cwd", workspace.path)
        .put("uid", uid).put("identitySource", "android.os.Process").put("action", "Run fixed pwd once")
    private fun record(action: String, code: String, peer: Int) {
        audit.add(JSONObject().put("action", action).put("code", code).put("peerPid", peer).put("uid", uid).put("timeMillis", System.currentTimeMillis()))
    }
    private fun error(code: String) = JSONObject().put("ok", false).put("code", code)
    private fun success() = JSONObject().put("ok", true)
    private fun parse(line: String): JSONObject {
        val result = JSONObject()
        JsonReader(StringReader(line)).use { reader ->
            reader.isLenient = false
            reader.beginObject()
            while (reader.hasNext()) {
                val key = reader.nextName()
                check(!result.has(key)) { "Duplicate field" }
                when (key) {
                    "version" -> { check(reader.peek() == android.util.JsonToken.NUMBER); result.put(key, reader.nextInt()) }
                    "arguments" -> { val args = JSONArray(); reader.beginArray(); while (reader.hasNext()) args.put(reader.nextString()); reader.endArray(); result.put(key, args) }
                    else -> result.put(key, reader.nextString())
                }
            }
            reader.endObject()
            check(reader.peek() == android.util.JsonToken.END_DOCUMENT)
        }
        return result
    }
    private fun handle(socket: LocalSocket) {
        var reply = error("MALFORMED")
        try {
            socket.soTimeout = 10000
            val peer = socket.peerCredentials
            if (peer.uid != uid || peer.pid <= 0) { reply = error("UNEXPECTED_PEER"); return }
            val bytes = java.io.ByteArrayOutputStream()
            while (true) {
                val value = socket.inputStream.read()
                check(value >= 0 && bytes.size() < 8192) { "Incomplete or oversized request" }
                if (value == 10) break
                bytes.write(value)
            }
            val line = Charsets.UTF_8.newDecoder().decode(java.nio.ByteBuffer.wrap(bytes.toByteArray())).toString()
            val request = parse(line)
            val keys = request.keys().asSequence().toSet()
            val base = setOf("version", "token", "action")
            check(request.getInt("version") == 1)
            if (!MessageDigest.isEqual(secret.toByteArray(), request.getString("token").toByteArray())) { reply = error("UNAUTHENTICATED"); return }
            val action = request.getString("action")
            if (action == "describe") {
                check(keys == base)
                reply = success().put("fixedExecutableAvailable", File("/system/bin/pwd").canExecute()).put("cwd", workspace.path).put("uid", uid).put("sessionId", sessionId).put("callIds", JSONArray(callIds))
                return
            }
            if (action !in setOf("prepare", "execute", "cancel")) { reply = error("UNSUPPORTED_ACTION"); return }
            val expected = base + setOf("sessionId", "callId", "executable", "arguments", "cwd")
            if (keys != expected) { reply = error("MALFORMED"); return }
            val call = request.getString("callId")
            if (request.getString("sessionId") != sessionId || call !in callIds ||
                request.getString("executable") != "/system/bin/pwd" || request.getJSONArray("arguments").length() != 0 ||
                request.getString("cwd") != workspace.path || workspace.canonicalFile != workspace) {
                reply = error("REQUEST_CHANGED"); record(action, "REQUEST_CHANGED", peer.pid); return
            }
            if (closed.get()) { reply = error("CLOSED"); return }
            when (action) {
                "prepare" -> {
                    val grant = CommandGrant(identity(call), System::nanoTime, 90_000_000_000L)
                    if (grants.putIfAbsent(call, grant) != null) { grant.close(); reply = error("DUPLICATE"); return }
                    val answer = CompletableFuture<String>()
                    decisions[call] = answer
                    showApproval(snapshot(call).put("expectedTestAction", if (call == callIds[0]) "Deny" else "Approve"))
                    val outcome = try { answer.get(60, TimeUnit.SECONDS) } catch (_: Exception) { grant.close(); "cancelled" }
                    decisions.remove(call, answer)
                    record(action, outcome, peer.pid)
                    reply = success().put("outcome", outcome)
                }
                "cancel" -> { grants[call]?.close(); owners[call]?.close(); decisions[call]?.complete("cancelled"); reply = success() }
                "execute" -> {
                    val grant = grants[call]
                    if (grant == null) { reply = error("APPROVAL_REQUIRED"); record(action, "APPROVAL_REQUIRED", peer.pid); return }
                    val execution = FixedPwdExecution.android(sessionId, call, workspace, uid, grant)
                    // One owner per call; grant still independently rejects duplicate consumption.
                    if (owners.putIfAbsent(call, execution) != null) { reply = error("USED"); record(action, "USED", peer.pid); return }
                    try {
                        val value = execution.execute()
                        record(action, "EXECUTED", peer.pid)
                        reply = success().put("result", JSONObject().put("stdout", value.stdout).put("stderr", value.stderr)
                            .put("exitCode", value.exitCode).put("cwd", workspace.path))
                    } catch (failure: Exception) {
                        record(action, "EXECUTION_FAILED", peer.pid)
                        reply = error((if (failure is java.net.SocketTimeoutException) "TIMEOUT" else if (failure is java.io.InterruptedIOException) "CANCELLED" else "EXECUTION_FAILED")).put("failure", failure.message)
                    } finally { execution.close() }
                }
            }
        } catch (_: Exception) { reply = error("MALFORMED_OR_DISCONNECTED") }
        finally {
            try { socket.outputStream.write((reply.toString() + "\n").toByteArray()); socket.outputStream.flush() } catch (_: Exception) { /* Fail closed. */ }
        }
    }
    /** Only the private bound Activity handler invokes this; no socket approval action exists. */
    fun decide(callId: String, allow: Boolean) {
        val grant = grants[callId] ?: return
        val answer = decisions[callId] ?: return
        if (grant.decide(allow)) answer.complete(if (allow) "allowed-once" else "rejected")
        else answer.complete("cancelled")
    }
    fun evidence() = JSONObject().put("uid", uid).put("sessionId", sessionId).put("audit", JSONArray(audit.toList()))
        .put("cwd", workspace.path).put("callIds", JSONArray(callIds)).put("requests", JSONArray(callIds.map { snapshot(it) }))
        .put("transport", "AF_UNIX abstract; SO_PEERCRED UID plus per-run secret")
        .put("processLaunches", owners.values.sumOf { it.processLaunches() })
    override fun close() {
        if (!closed.compareAndSet(false, true)) return
        grants.values.forEach { it.close() }
        decisions.values.forEach { it.complete("cancelled") }
        var interrupted = Thread.interrupted()
        val failures = mutableListOf<Exception>()
        fun attempt(action: () -> Unit) { try { action() } catch (error: Exception) { failures.add(error) } }
        try {
            owners.values.forEach { attempt { it.close() } }
            attempt { server.close() }
            sockets.forEach { attempt { it.close() } }
            workers.shutdownNow()
            try { acceptThread.join(2000) } catch (_: InterruptedException) { interrupted = true }
            val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(8)
            while (!workers.isTerminated && System.nanoTime() < deadline) {
                try { workers.awaitTermination(100, TimeUnit.MILLISECONDS) }
                catch (_: InterruptedException) { interrupted = true }
            }
            if (!workers.isTerminated) failures.add(java.io.IOException("Broker workers did not stop"))
        } finally { if (interrupted) Thread.currentThread().interrupt() }
        if (failures.isNotEmpty()) throw java.io.IOException("Broker cleanup failed").apply { failures.forEach { addSuppressed(it) } }
    }
}
