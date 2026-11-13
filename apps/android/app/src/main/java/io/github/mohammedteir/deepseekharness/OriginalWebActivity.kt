package io.github.mohammedteir.deepseekharness

import android.app.Activity
import android.net.Uri
import android.os.Bundle
import android.webkit.MimeTypeMap
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.LinearLayout
import android.widget.TextView
import androidx.webkit.WebViewAssetLoader
import java.io.ByteArrayInputStream
import java.io.IOException

/** Offline inspection of the original build; Harness boot and transport are not connected. */
class OriginalWebActivity : Activity() {
    private lateinit var view: WebView
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val loader = WebViewAssetLoader.Builder().addPathHandler("/", WebViewAssetLoader.PathHandler { path ->
            val components = path.split('/')
            if (components.any { it == "." || it == ".." || it.contains('\\') } || path.startsWith("api/")) return@PathHandler denied(404)
            val asset = if (path.isEmpty()) "index.html" else path
            try {
                val ext = asset.substringAfterLast('.', "").lowercase()
                val mime = when (ext) {
                    "js", "mjs" -> "text/javascript"
                    "svg" -> "image/svg+xml"
                    "woff2" -> "font/woff2"
                    "webmanifest" -> "application/manifest+json"
                    else -> MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext) ?: "application/octet-stream"
                }
                WebResourceResponse(mime, if (mime.startsWith("text/") || mime.contains("javascript")) "UTF-8" else null,
                    200, "OK", mapOf("Content-Security-Policy" to "connect-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'",
                        "X-Content-Type-Options" to "nosniff"), assets.open("web/$asset"))
            } catch (_: IOException) { denied(404) }
        }).build()
        view = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.allowFileAccessFromFileURLs = false
            settings.allowUniversalAccessFromFileURLs = false
            settings.allowFileAccess = false
            settings.allowContentAccess = false
            settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean = !allowed(request.url)
                override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse =
                    if (request.method == "GET" && allowed(request.url)) loader.shouldInterceptRequest(request.url) ?: denied(404) else denied(403)
            }
        }
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(TextView(this@OriginalWebActivity).apply { text = "Original web assets: local runtime connection not yet available." })
            addView(view, LinearLayout.LayoutParams(-1, 0, 1f))
        }
        setContentView(layout)
        view.loadUrl("https://appassets.androidplatform.net/index.html")
    }
    private fun allowed(uri: Uri): Boolean = uri.scheme == "https" && uri.host == "appassets.androidplatform.net" && uri.port == -1 && uri.userInfo == null
    private fun denied(code: Int) = WebResourceResponse("text/plain", "UTF-8", code, if (code == 404) "Not Found" else "Forbidden",
        mapOf("Cache-Control" to "no-store"), ByteArrayInputStream(ByteArray(0)))
    override fun onDestroy() { view.destroy(); super.onDestroy() }
}
