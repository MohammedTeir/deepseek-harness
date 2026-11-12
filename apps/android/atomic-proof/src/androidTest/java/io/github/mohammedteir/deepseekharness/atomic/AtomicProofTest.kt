package io.github.mohammedteir.deepseekharness.atomic

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

/** Executes fixed native tests under the installed ordinary app UID; not session recovery. */
@RunWith(AndroidJUnit4::class)
class AtomicProofTest {
    @Test fun nativeAtomicPublicationSuite() {
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
        assertTrue(context.bindService(Intent(context, AtomicProofService::class.java), connection, Context.BIND_AUTO_CREATE))
        try {
            assertTrue("Native proof did not return", done.await(95, TimeUnit.SECONDS))
            val value = result.get() ?: throw AssertionError("Missing native result")
            val json = JSONObject(value)
            assertEquals(value, "PASS", json.getString("status"))
            assertEquals(0, json.getInt("nativeExitCode"))
            assertEquals(android.os.Process.myUid(), json.getInt("uid"))
            assertNotEquals(0, json.getInt("uid"))
            assertEquals("aarch64", json.getString("architecture"))
            assertEquals(Build.VERSION.SDK_INT, json.getJSONObject("device").getInt("api"))
            assertFalse(json.getBoolean("installedExecutableWritable"))
            assertFalse(json.getBoolean("harnessPersistenceModified"))
            assertFalse(json.getBoolean("gate2Passed"))
            val tests = json.getJSONArray("tests")
            assertEquals(5, tests.length())
            val names = mutableSetOf<String>()
            for (i in 0 until tests.length()) {
                val test = tests.getJSONObject(i)
                assertEquals(test.toString(), "PASS", test.getString("status"))
                names.add(test.getString("name"))
                val data = test.getJSONObject("evidence")
                when (test.getString("name")) {
                    "A-publication" -> for (key in listOf("fileFsync", "directoryFsync", "sameInode", "sourceConsumed", "cleanupSynced")) assertTrue(key, data.getBoolean(key))
                    "B-existing-destination" -> {
                        assertEquals("EEXIST", data.getString("code"))
                        assertEquals(data.getString("beforeSha256"), data.getString("afterSha256"))
                        assertEquals(data.getJSONObject("before").toString(), data.getJSONObject("after").toString())
                        assertTrue(data.getBoolean("destinationSymlinkProtected"))
                    }
                    "C-independent-processes" -> {
                        assertEquals(8, data.getInt("processesPerRound")); assertEquals(16, data.getInt("rounds"))
                        val rounds = data.getJSONArray("roundResults")
                        assertEquals(16, rounds.length())
                        for (r in 0 until rounds.length()) {
                            val round = rounds.getJSONObject(r)
                            assertEquals(1, round.getInt("successes")); assertEquals(7, round.getInt("collisions"))
                            assertEquals(8, round.getInt("completeReadObservations"))
                            val pids = round.getJSONArray("pids")
                            assertEquals(8, (0 until pids.length()).map { pids.getInt(it) }.toSet().size)
                            assertTrue(round.getBoolean("lateCollisionProtected"))
                            assertTrue(round.getInt("independentObserverCompleteReads") > 0)
                            assertFalse((0 until pids.length()).any { pids.getInt(it) == round.getInt("independentObserverPid") })
                        }
                    }
                    "D-interruption" -> {
                        assertEquals(10, data.getJSONArray("cases").length())
                        assertFalse(data.getBoolean("powerLossTested"))
                    }
                    "E-errors-and-boundaries" -> {
                        assertTrue(data.getBoolean("traversalRejected")); assertTrue(data.getBoolean("sourceSymlinkRejected"))
                        assertTrue(data.getBoolean("fsyncFailurePropagated")); assertFalse(data.getBoolean("fallbackUsed"))
                    }
                }
            }
            assertEquals(setOf("A-publication", "B-existing-destination", "C-independent-processes", "D-interruption", "E-errors-and-boundaries"), names)
        } finally { context.unbindService(connection) }
    }
}
