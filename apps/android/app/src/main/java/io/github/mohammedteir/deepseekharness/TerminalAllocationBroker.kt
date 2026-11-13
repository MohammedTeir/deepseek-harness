package io.github.mohammedteir.deepseekharness

import android.content.Context
import android.net.LocalServerSocket
import android.net.LocalSocket
import android.os.Process
import android.system.Os
import android.system.OsConstants
import android.util.JsonReader
import android.util.JsonToken
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.io.StringReader
import java.security.MessageDigest
import java.util.UUID
import java.util.concurrent.CompletableFuture
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger

/** Fixed qualification broker, not activated by an application service. Reviewed same-UID code only. */
class TerminalAllocationBroker(context: Context, private val workspace: File,
                               private val showApproval: (JSONObject) -> Unit) : AutoCloseable {
    val sessionId = "android-terminal-${UUID.randomUUID()}"
    val callIds = listOf("deny-${UUID.randomUUID()}", "allow-${UUID.randomUUID()}")
    private val uid = Process.myUid()
    private val executable = File(context.applicationInfo.nativeLibraryDir, "libharness_pty_fixture.so").canonicalFile
    private val name = "harness-terminal-${UUID.randomUUID()}"
    private val secret = UUID.randomUUID().toString() + UUID.randomUUID().toString()
    private val closed = AtomicBoolean(false)
    private val cleaned = CompletableFuture<Unit>()
    private val lock = Any()
    private val server: LocalServerSocket
    private val workers = Executors.newFixedThreadPool(2)
    private val sockets = ConcurrentHashMap.newKeySet<LocalSocket>()
    private val grants = ConcurrentHashMap<String, TerminalAllocationGrant>()
    private val answers = ConcurrentHashMap<String, CompletableFuture<String>>()
    private val terminalClaims = mutableSetOf<String>()
    private val cancelledCalls = mutableSetOf<String>()
    private val audit = mutableListOf<JSONObject>()
    private val omittedAudit = AtomicInteger()
    private val allocationsConsumed = AtomicInteger()
    @Volatile private var resourceFailure: JSONObject? = null
    private val acceptThread = Thread({
        while (!closed.get()) {
            val socket = try { server.accept() } catch (_: IOException) { break }
            if (closed.get() || sockets.size >= 4) { socket.close(); continue }
            sockets.add(socket)
            try { workers.execute { try { socket.use { handle(it) } } finally { sockets.remove(socket) } } }
            catch (_: java.util.concurrent.RejectedExecutionException) { sockets.remove(socket); socket.close() }
        }
    }, "HarnessTerminalAccept")
    init {
        check(uid > 0 && workspace == workspace.canonicalFile && workspace.isDirectory)
        check(workspace.path.startsWith(context.filesDir.canonicalPath + File.separator)) { "App-private workspace required" }
        check(Os.stat(workspace.path).st_uid == uid) { "Workspace UID mismatch" }
        check(executable.parentFile == File(context.applicationInfo.nativeLibraryDir).canonicalFile)
        check(executable.isFile && executable.canExecute() && !executable.canWrite()) { "Installed fixture unavailable" }
        val mode = Os.stat(executable.path).st_mode
        check(mode and (OsConstants.S_ISUID or OsConstants.S_ISGID) == 0) { "Set-ID fixture forbidden" }
        server = LocalServerSocket(name)
        acceptThread.start()
    }
    /** Pass only to reviewed bundled code; never log or persist the secret. */
    fun launchEnvironment(): Map<String, String> = mapOf(
        "HARNESS_TERMINAL_SOCKET" to name, "HARNESS_TERMINAL_SECRET" to secret,
        "HARNESS_TERMINAL_SESSION" to sessionId, "HARNESS_TERMINAL_CALLS" to JSONArray(callIds).toString())
    private fun success() = JSONObject().put("ok", true)
    private fun error(code: String) = JSONObject().put("ok", false).put("code", code)
    private fun configuration() = JSONObject()
        .put("sessionId", sessionId).put("ownerId", sessionId)
        .put("backend", TerminalAllocationGrant.BACKEND).put("executable", executable.path)
        .put("arguments", JSONArray(listOf(TerminalAllocationGrant.ROLE))).put("cwd", workspace.path)
        .put("columns", TerminalAllocationGrant.COLUMNS).put("rows", TerminalAllocationGrant.ROWS)
        .put("uid", uid).put("identitySource", "android.os.Process")
        .put("qualification", "lifecycle")
        .put("action", "Allocate one fixed benign PTY fixture; test wait timeout and cancellation; no shell")
    private fun snapshot(call: String, terminal: String) = configuration().put("callId", call).put("terminalId", terminal)
    private fun record(action: String, code: String, peer: Int) = synchronized(audit) {
        if (audit.size >= 256) omittedAudit.incrementAndGet()
        else audit.add(JSONObject().put("action", action).put("code", code).put("peerPid", peer)
            .put("uid", uid).put("timeMillis", System.currentTimeMillis()))
        Unit
    }
    private fun parse(line: String): JSONObject {
        val value = JSONObject()
        JsonReader(StringReader(line)).use { reader ->
            reader.isLenient = false; reader.beginObject()
            while (reader.hasNext()) {
                val key = reader.nextName(); check(!value.has(key)) { "Duplicate key" }
                when (key) {
                    "version", "columns", "rows" -> { check(reader.peek() == JsonToken.NUMBER); value.put(key, reader.nextInt()) }
                    "arguments" -> {
                        val items = JSONArray(); reader.beginArray()
                        while (reader.hasNext()) { check(items.length() < 16 && reader.peek() == JsonToken.STRING); items.put(reader.nextString()) }
                        reader.endArray(); value.put(key, items)
                    }
                    else -> { check(reader.peek() == JsonToken.STRING); value.put(key, reader.nextString()) }
                }
            }
            reader.endObject(); check(reader.peek() == JsonToken.END_DOCUMENT)
        }
        return value
    }
    private fun matchesConfiguration(request: JSONObject): Boolean =
        request.getString("sessionId") == sessionId && request.getString("ownerId") == sessionId
            && request.getString("callId") in callIds && request.getString("terminalId").matches(Regex("pty-[1-9][0-9]{0,15}"))
            && request.getString("backend") == TerminalAllocationGrant.BACKEND
            && request.getString("executable") == executable.path && request.getString("cwd") == workspace.path
            && request.getJSONArray("arguments").toString() == JSONArray(listOf(TerminalAllocationGrant.ROLE)).toString()
            && request.getInt("columns") == TerminalAllocationGrant.COLUMNS && request.getInt("rows") == TerminalAllocationGrant.ROWS
    private fun handle(socket: LocalSocket) {
        var reply = error("MALFORMED")
        var callForReply: String? = null
        try {
            socket.soTimeout = 10000
            val peer = socket.peerCredentials
            if (peer.uid != uid || peer.pid <= 0) { reply = error("UNEXPECTED_PEER"); return }
            val bytes = java.io.ByteArrayOutputStream()
            while (true) {
                val byte = socket.inputStream.read(); check(byte >= 0 && bytes.size() < 8192)
                if (byte == 10) break
                bytes.write(byte)
            }
            val request = parse(Charsets.UTF_8.newDecoder().decode(java.nio.ByteBuffer.wrap(bytes.toByteArray())).toString())
            check(request.getInt("version") == 1)
            if (!MessageDigest.isEqual(secret.toByteArray(), request.getString("token").toByteArray())) { reply = error("UNAUTHENTICATED"); return }
            val action = request.getString("action")
            val base = setOf("version", "token", "action")
            val keys = request.keys().asSequence().toSet()
            if (closed.get()) { reply = error("CLOSED"); return }
            if (action == "describe") {
                check(keys == base)
                reply = success().put("sessionId", sessionId).put("callIds", JSONArray(callIds)).put("configuration", configuration())
                return
            }
            if (action !in setOf("prepare", "consume", "cancel")) { reply = error("UNSUPPORTED_ACTION"); return }
            val expected = base + setOf("sessionId", "callId", "ownerId", "terminalId", "backend", "executable", "arguments", "cwd", "columns", "rows")
            if (keys != expected) { reply = error("MALFORMED"); return }
            if (!matchesConfiguration(request)) { reply = error("REQUEST_CHANGED"); record(action, "REQUEST_CHANGED", peer.pid); return }
            val call = request.getString("callId"); val terminal = request.getString("terminalId")
            when (action) {
                "prepare" -> {
                    val answer = CompletableFuture<String>()
                    val grant: TerminalAllocationGrant
                    synchronized(lock) {
                        if (closed.get()) { reply = error("CLOSED"); return }
                        if (call in cancelledCalls) { reply = error("CLOSED"); return }
                        if (grants.containsKey(call)) { reply = error("DUPLICATE"); return }
                        if (answers.isNotEmpty()) { reply = error("BUSY"); return }
                        if (terminal in terminalClaims) { reply = error("TERMINAL_ALREADY_BOUND"); return }
                        try { grant = TerminalAllocationGrant(sessionId, call, sessionId, terminal, workspace, executable, uid, System::nanoTime, 90_000_000_000L) }
                        catch (failure: IOException) {
                            resourceFailure = JSONObject().put("name", failure.javaClass.simpleName).put("message", failure.message?.take(1024))
                            reply = error("RESOURCE_REJECTED").put("failure", resourceFailure); record(action, "RESOURCE_REJECTED", peer.pid); return
                        }
                        grants[call] = grant; answers[call] = answer; terminalClaims.add(terminal)
                    }
                    callForReply = call
                    try {
                        if (!closed.get()) showApproval(snapshot(call, terminal).put("expectedTestAction", if (call == callIds[0]) "Deny" else "Approve"))
                        val outcome = answer.get(60, TimeUnit.SECONDS)
                        reply = success().put("outcome", outcome); record(action, outcome, peer.pid)
                    } catch (_: Exception) { grant.close(); reply = success().put("outcome", "cancelled"); record(action, "cancelled", peer.pid) }
                    finally { answers.remove(call, answer) }
                }
                "consume", "cancel" -> {
                    synchronized(lock) {
                        val grant = grants[call]
                        if (grant != null && grant.request().terminalId != terminal) { reply = error("REQUEST_CHANGED"); return }
                        callForReply = call
                        if (action == "cancel") {
                            // A cancellation arriving before prepare must also prevent a late native prompt/grant.
                            cancelledCalls.add(call); grant?.close(); answers[call]?.complete("cancelled")
                            reply = success(); record(action, "CLOSED", peer.pid)
                        } else {
                            if (closed.get() || call in cancelledCalls) { reply = error("CLOSED"); return }
                            if (grant == null) { reply = error("APPROVAL_REQUIRED"); return }
                            // Every wire field matched native configuration; a caller UID is never accepted.
                            val result = try { grant.consume(grant.request()) } catch (failure: IOException) {
                                resourceFailure = JSONObject().put("name", failure.javaClass.simpleName).put("message", failure.message?.take(1024))
                                reply = error("RESOURCE_REJECTED").put("failure", resourceFailure); record(action, "RESOURCE_REJECTED", peer.pid); return
                            }
                            if (result == CommandGrant.Outcome.CONSUMED) allocationsConsumed.incrementAndGet()
                            reply = if (result == CommandGrant.Outcome.CONSUMED) success().put("allocation", snapshot(call, terminal)) else error(result.name)
                            record(action, result.name, peer.pid)
                        }
                    }
                }
            }
        } catch (_: IOException) { reply = error("RESOURCE_OR_TRANSPORT_FAILURE") }
        catch (_: Exception) { reply = error("MALFORMED_OR_DISCONNECTED") }
        finally {
            try { socket.outputStream.write((reply.toString() + "\n").toByteArray()); socket.outputStream.flush() }
            catch (_: Exception) { callForReply?.let { grants[it]?.close(); answers[it]?.complete("cancelled") } }
        }
    }
    /** Native UI only; no decision action exists on the socket protocol. */
    fun decide(callId: String, terminalId: String, allow: Boolean): Boolean {
        if (closed.get()) return false
        val grant = grants[callId] ?: return false
        val answer = answers[callId] ?: return false
        if (grant.request().terminalId != terminalId) return false
        return try {
            val accepted = grant.decide(allow)
            answer.complete(if (accepted) if (allow) "allowed-once" else "rejected" else "cancelled")
            accepted
        } catch (_: IOException) { grant.close(); answer.complete("cancelled"); false }
    }
    fun evidence(): JSONObject = JSONObject().put("sessionId", sessionId).put("uid", uid)
        .put("audit", synchronized(audit) { JSONArray(audit.toList()) }).put("omittedAuditEntries", omittedAudit.get())
        .put("allocationsConsumed", allocationsConsumed.get())
        .put("transport", "AF_UNIX abstract; SO_PEERCRED UID and per-run secret")
        .put("resourceFailure", resourceFailure ?: JSONObject.NULL)
        .put("processLauncherImplemented", false).put("maliciousSameUidPluginIsolation", false)
    /** Native owner cleanup only; never call from a worker or main UI thread. */
    override fun close() {
        if (!closed.compareAndSet(false, true)) { cleaned.get(12, TimeUnit.SECONDS); return }
        val failures = mutableListOf<Exception>(); var interrupted = Thread.interrupted()
        fun attempt(action: () -> Unit) { try { action() } catch (error: Exception) { failures.add(error) } }
        try {
            synchronized(lock) { grants.values.forEach { it.close() }; answers.values.forEach { it.complete("cancelled") } }
            // shutdown wakes a blocked accept before its descriptor is closed on Android.
            attempt { Os.shutdown(server.fileDescriptor, OsConstants.SHUT_RDWR) }
            attempt { server.close() }; sockets.forEach { attempt { it.close() } }; workers.shutdownNow()
            try { acceptThread.join(2000) } catch (_: InterruptedException) { interrupted = true }
            val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(8)
            while (!workers.isTerminated && System.nanoTime() < deadline) {
                try { workers.awaitTermination(100, TimeUnit.MILLISECONDS) } catch (_: InterruptedException) { interrupted = true }
            }
            if (acceptThread.isAlive || !workers.isTerminated) failures.add(IOException("Terminal broker cleanup incomplete: acceptAlive=${acceptThread.isAlive}, workersTerminated=${workers.isTerminated}, sockets=${sockets.size}"))
            if (failures.isNotEmpty()) throw IOException("Terminal broker cleanup failed").apply { failures.forEach { addSuppressed(it) } }
            cleaned.complete(Unit)
        } catch (error: Exception) { cleaned.completeExceptionally(error); throw error }
        finally { if (interrupted) Thread.currentThread().interrupt() }
    }
}
