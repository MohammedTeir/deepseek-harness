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

/** Real Android socket negative tests, not a substitute for human UI acceptance. */
@RunWith(AndroidJUnit4::class)
class CommandBrokerTest {
    @Test fun rejectsUnauthenticatedMalformedAndApprovalActions() {
        val root = File(InstrumentationRegistry.getInstrumentation().targetContext.filesDir, "broker-test-${UUID.randomUUID()}").canonicalFile
        assertTrue(root.mkdir())
        try {
            CommandBroker(root) { throw AssertionError("Negative test must not ask for approval") }.use { broker ->
                val env = broker.launchEnvironment()
                fun request(text: String): JSONObject = LocalSocket().use { socket ->
                    socket.connect(LocalSocketAddress(env.getValue("HARNESS_COMMAND_SOCKET"), LocalSocketAddress.Namespace.ABSTRACT))
                    socket.soTimeout = 10000
                    socket.outputStream.write((text + "\n").toByteArray())
                    JSONObject(socket.inputStream.bufferedReader().readLine())
                }
                fun message(action: String) = JSONObject().put("version", 1).put("token", env.getValue("HARNESS_COMMAND_SECRET")).put("action", action)
                assertEquals("UNAUTHENTICATED", request(message("describe").put("token", "wrong").toString()).getString("code"))
                assertEquals("UNSUPPORTED_ACTION", request(message("approve").toString()).getString("code"))
                assertEquals("MALFORMED_OR_DISCONNECTED", request("{}").getString("code"))
                val malformed = message("describe").toString().dropLast(1) + ",\"version\":1}"
                assertEquals("MALFORMED_OR_DISCONNECTED", request(malformed).getString("code"))
                val description = request(message("describe").toString())
                assertTrue(description.getBoolean("ok"))
                assertEquals(android.os.Process.myUid(), description.getInt("uid"))
                assertEquals(0, broker.evidence().getInt("processLaunches"))
            }
        } finally { assertTrue(root.delete()) }
    }
}
