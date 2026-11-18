package io.github.mohammedteir.deepseekharness

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class WebProfileStartupTest {
    @Test fun returnsThePublishedUrlAndLeavesTheServerRunning() {
        val process = ProcessBuilder(
            "sh", "-c",
            "printf 'WARNING: linker warning\\ndsh web: http://127.0.0.1:5678/?token=test\\n'; exec sleep 10",
        ).start()
        try {
            assertEquals("http://127.0.0.1:5678/?token=test", awaitWebProfileUrl(process, 2_000))
            assertTrue(process.isAlive)
        } finally {
            process.destroyForcibly()
            process.waitFor()
        }
    }

    @Test fun reportsChildExitCodeAndDrainsOutputAfterTheProcessExits() {
        val process = ProcessBuilder(
            "sh", "-c", "printf 'WARNING: linker warning\\n'; exit 17",
        ).start()

        val error = try {
            awaitWebProfileUrl(process, 2_000)
            throw AssertionError("Expected a startup failure")
        } catch (failure: IllegalStateException) {
            failure
        }

        assertTrue(error.message.orEmpty().contains("exited before publishing a URL (exit code 17)"))
        assertTrue(error.message.orEmpty().contains("WARNING: linker warning"))
    }

    @Test fun reportsAndStopsAChildThatDoesNotPublishReadiness() {
        val process = ProcessBuilder("sh", "-c", "exec sleep 10").start()

        val error = try {
            awaitWebProfileUrl(process, 100)
            throw AssertionError("Expected a startup timeout")
        } catch (failure: IllegalStateException) {
            failure
        }

        assertTrue(error.message.orEmpty().contains("startup timed out after 100 ms"))
        assertTrue(error.message.orEmpty().contains("alive at deadline=true"))
        assertTrue(!process.isAlive)
    }
}
