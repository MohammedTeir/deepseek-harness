package ai.deepseek.harness.android

import java.net.URI

/** Admission policy shared by navigation and subresource loading. */
object LocalOrigin {
    const val HOST = "appassets.androidplatform.net"
    const val URL = "https://$HOST/"

    fun allows(url: String): Boolean = try {
        val uri = URI(url)
        uri.scheme == "https" && uri.host == HOST && uri.rawUserInfo == null &&
            (uri.port == -1 || uri.port == 443)
    } catch (error: java.net.URISyntaxException) {
        false
    }
}
