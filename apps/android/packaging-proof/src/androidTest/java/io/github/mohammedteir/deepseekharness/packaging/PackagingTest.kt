package io.github.mohammedteir.deepseekharness.packaging

import android.os.Process
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Trusted instrumentation exercises real OS operations; no Harness/runtime claim. */
@RunWith(AndroidJUnit4::class)
class PackagingTest {
    @Test fun loadsActualArm64JniLibrary() {
        val evidence = JSONObject(PackagingNative.sharedInfo())
        assertEquals(Process.myUid(), evidence.getInt("uid"))
        assertEquals(Process.myPid(), evidence.getInt("pid"))
        assertTrue(evidence.getInt("pageSize") > 0)
        assertNotEquals(0, evidence.getInt("uid"))
    }
    @Test fun executesInstallerOwnedArm64Program() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val result = runInstalledFixture(context)
        assertEquals(result.stdout, 0, result.exitCode)
        assertFalse(result.writable)
        val evidence = JSONObject(result.stdout)
        assertEquals(Process.myUid(), evidence.getInt("uid"))
        assertNotEquals(Process.myPid(), evidence.getInt("pid"))
        assertTrue(evidence.getInt("pageSize") > 0)
        assertNotEquals(0, evidence.getInt("uid"))
    }
}
