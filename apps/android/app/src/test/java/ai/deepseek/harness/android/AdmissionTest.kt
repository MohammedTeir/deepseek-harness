package ai.deepseek.harness.android

import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.TimeUnit

class AdmissionTest {
    @Test fun rejectsForeignOrigins() {
        listOf("http://appassets.androidplatform.net/", "https://evil.test/", "file:///etc/passwd",
            "https://appassets.androidplatform.net.evil.test/", "https://user@appassets.androidplatform.net/",
            "https://appassets.androidplatform.net:8443/", "javascript:alert(1)", "not a URL")
            .forEach { assertFalse(it, LocalOrigin.allows(it)) }
        assertTrue(LocalOrigin.allows(LocalOrigin.URL))
        assertTrue(LocalOrigin.allows("${LocalOrigin.URL}assets/app.js"))
    }
    @Test fun approvalIsRequiredBoundedAndSingleUse() {
        var now = 0L
        val auth = DiagnosticAuthorization { now }
        assertFalse(auth.consume("invented"))
        val token = auth.approve()
        assertFalse(auth.consume("wrong"))
        assertTrue(auth.consume(token))
        assertFalse(auth.consume(token))
        val expired = auth.approve()
        now += TimeUnit.SECONDS.toNanos(30)
        assertFalse(auth.consume(expired))
        val revoked = auth.approve()
        auth.revoke()
        assertFalse(auth.consume(revoked))
        val replaced = auth.approve()
        val current = auth.approve()
        assertFalse(auth.consume(replaced))
        assertTrue(auth.consume(current))
    }
}
