package ai.deepseek.harness.android

import android.app.Activity
import android.app.AlertDialog
import android.os.Bundle
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import androidx.webkit.WebViewAssetLoader
import java.io.ByteArrayInputStream
import java.util.concurrent.Executors

/** Offline carrier for unmodified upstream assets. Harness runtime integration is explicitly unavailable. */
class MainActivity : Activity() {
    private lateinit var web: WebView
    private val authorization = DiagnosticAuthorization()
    private val worker = Executors.newSingleThreadExecutor()
    private var disposed = false

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; fitsSystemWindows = true }
        layout.addView(TextView(this).apply {
            setText(R.string.runtime_unavailable)
            setPadding(16, 12, 16, 12)
        })
        layout.addView(Button(this).apply {
            setText(R.string.run_diagnostic)
            setOnClickListener { approveDiagnostic() }
        })
        val loader = WebViewAssetLoader.Builder()
            .addPathHandler("/", WebViewAssetLoader.AssetsPathHandler(this).let { handler ->
                WebViewAssetLoader.PathHandler { path -> handler.handle("web/${if (path.isEmpty()) "index.html" else path}") }
            }).build()
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)
        web = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.allowFileAccess = false
            settings.allowContentAccess = false
            settings.javaScriptCanOpenWindowsAutomatically = false
            settings.setSupportMultipleWindows(false)
            settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest) =
                    !LocalOrigin.allows(request.url.toString())
                override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse {
                    if (LocalOrigin.allows(request.url.toString())) {
                        val response = loader.shouldInterceptRequest(request.url)
                        if (response != null) return response
                    }
                    return WebResourceResponse("text/plain", "UTF-8", 403, "Forbidden", emptyMap(), ByteArrayInputStream(byteArrayOf()))
                }
            }
        }
        layout.addView(web, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(layout)
        if (state == null || web.restoreState(state) == null) web.loadUrl(LocalOrigin.URL)
    }

    private fun approveDiagnostic() {
        AlertDialog.Builder(this)
            .setTitle(R.string.approve_title)
            .setMessage(getString(R.string.approve_message, filesDir.toString()))
            .setNegativeButton(R.string.deny) { _, _ -> authorization.revoke() }
            .setPositiveButton(R.string.allow_once) { _, _ ->
                val token = authorization.approve()
                worker.execute {
                    val message = try {
                        val result = DiagnosticExecution(authorization).pwd(token, filesDir)
                        getString(R.string.result_message, result.stdout, result.stderr, result.exitCode.toString(), result.timedOut.toString())
                    } catch (error: Exception) {
                        getString(R.string.diagnostic_failed, error.javaClass.simpleName)
                    }
                    runOnUiThread {
                        if (!disposed) AlertDialog.Builder(this).setTitle(R.string.result_title)
                            .setMessage(message).setPositiveButton(R.string.close, null).show()
                    }
                }
            }.show()
    }

    override fun onSaveInstanceState(state: Bundle) { web.saveState(state); super.onSaveInstanceState(state) }
    @Deprecated("Platform back API retained for API 29")
    override fun onBackPressed() { if (web.canGoBack()) web.goBack() else super.onBackPressed() }
    override fun onDestroy() {
        disposed = true
        authorization.revoke()
        worker.shutdownNow()
        web.stopLoading()
        web.destroy()
        super.onDestroy()
    }
}
