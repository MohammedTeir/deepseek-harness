package io.github.mohammedteir.deepseekharness

import android.content.*
import android.os.*
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

/** Requires the real packaged runtime; missing libraries fail instead of skipping. */
@RunWith(AndroidJUnit4::class)
class RuntimeProbeTest {
    @Test fun embeddedNodeExecutesApis() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val completed = CountDownLatch(1)
        val result = AtomicReference<String>()
        val reply = Messenger(Handler(Looper.getMainLooper()) { message ->
            result.set(message.data.getString("result")); completed.countDown(); true
        })
        val connection = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName, binder: IBinder) {
                try { Messenger(binder).send(Message.obtain(null, 1).apply { replyTo = reply }) }
                catch (error: RemoteException) { result.set(error.javaClass.simpleName); completed.countDown() }
            }
            override fun onServiceDisconnected(name: ComponentName) { completed.countDown() }
        }
        assertTrue(context.bindService(Intent(context, RuntimeService::class.java), connection, Context.BIND_AUTO_CREATE))
        try {
            assertTrue("Runtime did not return within 45 seconds", completed.await(45, TimeUnit.SECONDS))
            val value = result.get() ?: throw AssertionError("Runtime disconnected without evidence")
            assertTrue("Runtime failed: $value", value.startsWith("{"))
            val evidence = JSONObject(value)
            assertEquals("v24.22.1", evidence.getString("node"))
            assertEquals("android", evidence.getString("platform"))
            assertEquals("arm64", evidence.getString("arch"))
            assertNotEquals("Runtime must have its own process", android.os.Process.myPid(), evidence.getInt("pid"))
            assertEquals("Node PID matches runtime host", evidence.getInt("pid"), evidence.getInt("androidPid"))
            assertEquals("android.os.Process", evidence.getString("identitySource"))
            assertEquals("Runtime shares application UID", android.os.Process.myUid(), evidence.getInt("androidUid"))
            assertNotEquals("Runtime must not be root", 0, evidence.getInt("androidUid"))
            if (evidence.getBoolean("uidApiAvailable")) {
                assertEquals(evidence.getInt("androidUid"), evidence.getInt("uid"))
            } else {
                assertTrue("Unavailable Node getuid must remain null", evidence.isNull("uid"))
            }
            for (api in listOf("sqlite", "worker", "esm")) assertTrue(api, evidence.getBoolean(api))
            assertEquals("ba9c736f19e7f60b7f6764adb0b7908c0a2b394e09b6c09863528c7f2bc86095", evidence.getString("crypto"))
            assertTrue("Native lock acquisition/contention/release", evidence.getBoolean("nativeLock"))
            assertEquals("upstream-system-entry", evidence.getString("nativeLockProvider"))
            val network = evidence.getJSONObject("network")
            assertTrue("DNS failed: $network", network.getBoolean("dns"))
            assertTrue("TLS failed: $network", network.getBoolean("tls"))
            assertFalse("API probe must not claim Harness execution", evidence.getBoolean("harnessStarted"))
        } finally { context.unbindService(connection) }
    }
}
