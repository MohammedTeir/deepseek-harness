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

/** Real installer-owned Node and child execution; no fixture or remote runtime substitute. */
@RunWith(AndroidJUnit4::class)
class ExecutableProbeTest {
    @Test fun packagedNodeRunsApisAndChild() {
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
        assertTrue(context.bindService(Intent(context, ExecutableProbeService::class.java), connection, Context.BIND_AUTO_CREATE))
        try {
            // 45s execution deadline + up to 5s cleanup + binder/startup overhead.
            assertTrue("Executable probe timed out", completed.await(70, TimeUnit.SECONDS))
            val value = result.get() ?: throw AssertionError("Executable disconnected without evidence")
            assertTrue("Executable failed: $value", value.startsWith("{"))
            val evidence = JSONObject(value)
            assertEquals("v24.22.1", evidence.getString("node"))
            assertEquals("android", evidence.getString("platform"))
            assertEquals("arm64", evidence.getString("arch"))
            assertEquals("packaged-executable", evidence.getString("executionStrategy"))
            assertEquals("passed", evidence.getString("childNodeLaunch"))
            assertFalse(evidence.getBoolean("installedExecutableWritable"))
            assertEquals(Build.VERSION.SDK_INT, evidence.getJSONObject("device").getInt("api"))
            assertEquals(Build.MODEL, evidence.getJSONObject("device").getString("model"))
            assertTrue(evidence.getString("execPath").endsWith("/libnode_executable.so"))
            val identity = evidence.getJSONObject("kernelIdentity")
            assertEquals(evidence.getInt("pid"), identity.getInt("pid"))
            assertEquals(evidence.getInt("supervisorPid"), identity.getInt("parentPid"))
            assertNotEquals(identity.getInt("pid"), evidence.getInt("supervisorPid"))
            assertEquals(android.os.Process.myUid(), identity.getInt("uid"))
            assertNotEquals(0, identity.getInt("uid"))
            val child = evidence.getJSONObject("childNode")
            assertEquals(identity.getInt("pid"), child.getInt("parentPid"))
            assertNotEquals(identity.getInt("pid"), child.getInt("pid"))
            assertEquals(identity.getInt("uid"), child.getInt("uid"))
            assertEquals(0, evidence.getJSONObject("childResult").getInt("exitCode"))
            for (api in listOf("sqlite", "worker", "esm", "nativeLock")) assertTrue(api, evidence.getBoolean(api))
            assertEquals("ba9c736f19e7f60b7f6764adb0b7908c0a2b394e09b6c09863528c7f2bc86095", evidence.getString("crypto"))
            assertEquals("upstream-system-entry", evidence.getString("nativeLockProvider"))
            val network = evidence.getJSONObject("network")
            assertTrue("DNS failed: $network", network.getBoolean("dns"))
            assertTrue("TLS failed: $network", network.getBoolean("tls"))
            assertFalse(evidence.getBoolean("harnessStarted"))
        } finally { context.unbindService(connection) }
    }
}
