package io.github.mohammedteir.deepseekharness

import android.net.LocalSocket
import android.net.LocalSocketAddress
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/** Real Android sockets with automated native decisions; not human-approval acceptance. */
@RunWith(AndroidJUnit4::class)
class TerminalAllocationBrokerTest {
    private fun runCase(body: (TerminalAllocationBroker, LinkedBlockingQueue<JSONObject>, (String) -> JSONObject) -> Unit) {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val root = File(context.filesDir, "terminal-broker-test-${UUID.randomUUID()}").canonicalFile
        assertTrue(root.mkdir())
        try {
            val prompts = LinkedBlockingQueue<JSONObject>()
            TerminalAllocationBroker(context, root) { prompts.add(it) }.use { broker ->
                val env = broker.launchEnvironment()
                body(broker, prompts) { text -> LocalSocket().use { socket ->
                    socket.connect(LocalSocketAddress(env.getValue("HARNESS_TERMINAL_SOCKET"), LocalSocketAddress.Namespace.ABSTRACT))
                    socket.soTimeout = 70000
                    val frame = if (text.startsWith("RAW:")) text.removePrefix("RAW:") else JSONObject(text)
                        .put("version", 1).put("token", env.getValue("HARNESS_TERMINAL_SECRET")).toString()
                    socket.outputStream.write((frame + "\n").toByteArray())
                    JSONObject(socket.inputStream.bufferedReader().readLine())
                } }
            }
        } finally { assertTrue(root.delete()) }
    }
    private fun fields(description: JSONObject, call: Int, terminal: String): JSONObject {
        val result = JSONObject(description.getJSONObject("configuration").toString())
        for (key in listOf("uid", "identitySource", "action")) result.remove(key)
        return result.put("callId", description.getJSONArray("callIds").getString(call)).put("terminalId", terminal)
    }
    private fun operation(fields: JSONObject, action: String) = JSONObject(fields.toString()).put("action", action).toString()
    @Test fun rejectsUnauthenticatedMalformedAndAgentDecisionFrames() = runCase { broker, prompts, request ->
        assertEquals("MALFORMED_OR_DISCONNECTED", request("RAW:{}").getString("code"))
        assertEquals("UNAUTHENTICATED", request("RAW:{\"version\":1,\"token\":\"bad\",\"action\":\"describe\"}").getString("code"))
        assertEquals("UNSUPPORTED_ACTION", request("{\"action\":\"approve\"}").getString("code"))
        assertEquals("UNSUPPORTED_ACTION", request("{\"action\":\"execute\"}").getString("code"))
        val exact = fields(request("{\"action\":\"describe\"}"), 1, "pty-2")
        assertEquals("APPROVAL_REQUIRED", request(operation(exact, "consume")).getString("code"))
        assertEquals("MALFORMED", request(JSONObject(operation(exact, "prepare")).put("uid", "0").toString()).getString("code"))
        assertEquals("REQUEST_CHANGED", request(JSONObject(operation(exact, "prepare")).put("executable", "/system/bin/sh").toString()).getString("code"))
        assertTrue(prompts.isEmpty()); assertEquals(0, broker.evidence().getInt("allocationsConsumed"))
    }
    @Test fun nativeDecisionBindsTerminalAndConsumptionIsOneShot() = runCase { broker, prompts, request ->
        val pool = Executors.newFixedThreadPool(2)
        try {
            val description = request("{\"action\":\"describe\"}")
            val denied = fields(description, 0, "pty-1")
            val denial = pool.submit<JSONObject> { request(operation(denied, "prepare")) }
            val first = prompts.poll(10, TimeUnit.SECONDS) ?: throw AssertionError("Missing denial prompt")
            assertFalse(broker.decide(first.getString("callId"), "pty-999", true))
            assertTrue(broker.decide(first.getString("callId"), first.getString("terminalId"), false))
            assertEquals("rejected", denial.get(10, TimeUnit.SECONDS).getString("outcome"))
            assertEquals("REJECTED", request(operation(denied, "consume")).getString("code"))
            val exact = fields(description, 1, "pty-2")
            val approval = pool.submit<JSONObject> { request(operation(exact, "prepare")) }
            val second = prompts.poll(10, TimeUnit.SECONDS) ?: throw AssertionError("Missing approval prompt")
            assertEquals(android.os.Process.myUid(), second.getInt("uid"))
            assertTrue(broker.decide(second.getString("callId"), second.getString("terminalId"), true))
            assertEquals("allowed-once", approval.get(10, TimeUnit.SECONDS).getString("outcome"))
            assertEquals("DUPLICATE", request(operation(exact, "prepare")).getString("code"))
            for ((key, value) in mapOf("terminalId" to "pty-3", "ownerId" to "other", "cwd" to "/", "sessionId" to "other", "backend" to "other")) {
                assertEquals("REQUEST_CHANGED", request(JSONObject(operation(exact, "consume")).put(key, value).toString()).getString("code"))
            }
            assertEquals("REQUEST_CHANGED", request(JSONObject(operation(exact, "consume")).put("columns", 81).toString()).getString("code"))
            val attempts = (1..2).map { pool.submit<JSONObject> { request(operation(exact, "consume")) } }.map { it.get(10, TimeUnit.SECONDS) }
            assertEquals(1, attempts.count { it.getBoolean("ok") }); assertEquals(1, attempts.count { it.optString("code") == "USED" })
            assertEquals("USED", request(operation(exact, "consume")).getString("code"))
            assertEquals(1, broker.evidence().getInt("allocationsConsumed")); assertFalse(broker.evidence().getBoolean("processLauncherImplemented"))
        } finally { pool.shutdownNow(); assertTrue(pool.awaitTermination(10, TimeUnit.SECONDS)) }
    }
    @Test fun cancellationRevokesPendingAndLateNativeDecision() = runCase { broker, prompts, request ->
        val pool = Executors.newSingleThreadExecutor()
        try {
            val exact = fields(request("{\"action\":\"describe\"}"), 0, "pty-1")
            val pending = pool.submit<JSONObject> { request(operation(exact, "prepare")) }
            val prompt = prompts.poll(10, TimeUnit.SECONDS) ?: throw AssertionError("Missing prompt")
            assertTrue(request(operation(exact, "cancel")).getBoolean("ok"))
            assertEquals("cancelled", pending.get(10, TimeUnit.SECONDS).getString("outcome"))
            assertFalse(broker.decide(prompt.getString("callId"), prompt.getString("terminalId"), true))
            assertEquals("CLOSED", request(operation(exact, "consume")).getString("code"))
        } finally { pool.shutdownNow(); assertTrue(pool.awaitTermination(10, TimeUnit.SECONDS)) }
    }
    @Test fun cancellationBeforePreparePreventsALateGrant() = runCase { broker, prompts, request ->
        val exact = fields(request("{\"action\":\"describe\"}"), 0, "pty-1")
        assertTrue(request(operation(exact, "cancel")).getBoolean("ok"))
        assertEquals("CLOSED", request(operation(exact, "prepare")).getString("code"))
        assertEquals("CLOSED", request(operation(exact, "consume")).getString("code"))
        assertTrue(prompts.isEmpty()); assertEquals(0, broker.evidence().getInt("allocationsConsumed"))
    }

}
