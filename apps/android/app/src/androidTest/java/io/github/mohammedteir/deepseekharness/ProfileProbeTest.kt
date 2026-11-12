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

/** Real original profile and restart recovery; no model or approved-command substitute. */
@RunWith(AndroidJUnit4::class)
class ProfileProbeTest {
    @Test fun originalProfileRecoversSession() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val done = CountDownLatch(1)
        val result = AtomicReference<String>()
        val reply = Messenger(Handler(Looper.getMainLooper()) { message ->
            result.set(message.data.getString("result")); done.countDown(); true
        })
        val connection = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName, binder: IBinder) {
                try { Messenger(binder).send(Message.obtain(null, 1).apply { replyTo = reply }) }
                catch (error: RemoteException) { result.set(error.javaClass.simpleName); done.countDown() }
            }
            override fun onServiceDisconnected(name: ComponentName) { done.countDown() }
        }
        assertTrue(context.bindService(Intent(context, ProfileProbeService::class.java), connection, Context.BIND_AUTO_CREATE))
        try {
            assertTrue("Original profile did not return", done.await(115, TimeUnit.SECONDS))
            val value = result.get() ?: throw AssertionError("Profile disconnected without result")
            assertTrue("Original profile failed: $value", value.startsWith("{"))
            val json = JSONObject(value)
            assertEquals("napi-v9", json.getJSONObject("nativeInternalLoader").getString("abi"))
            assertEquals("require-builtin", json.getJSONObject("nativeInternalLoader").getString("product"))
            val storage = json.getJSONObject("persistenceDiagnostics").getJSONObject("storage")
            for (field in listOf("directorySync", "fileSync", "exclusiveHardlinkPublish", "existingPathRejected")) assertTrue(field, storage.getBoolean(field))
            assertEquals(2, json.getJSONObject("persistenceDiagnostics").getInt("shutdownAcknowledgements"))
            assertTrue(json.getBoolean("harnessStarted"))
            assertTrue(json.getBoolean("sessionRecoveredAcrossRuntimeRestart"))
            assertTrue(json.getBoolean("recoveredNondefaultDirectory"))
            assertTrue(json.getJSONObject("persistedJsonlSha256").length() > 0)
            assertEquals("deepseek-harness-sdk-runtime", json.getJSONObject("serverInfo").getString("name"))
            assertEquals("android", json.getString("platform"))
            assertEquals("arm64", json.getString("arch"))
            assertEquals("v24.22.1", json.getString("node"))
            assertEquals(android.os.Process.myUid(), json.getInt("supervisorUid"))
            assertNotEquals(0, json.getInt("supervisorUid"))
            assertFalse(json.getBoolean("approvedCommandExecuted"))
            assertFalse(json.getBoolean("modelRequestExecuted"))
            assertFalse(json.getBoolean("gate2Passed"))
        } finally { context.unbindService(connection) }
    }
}
