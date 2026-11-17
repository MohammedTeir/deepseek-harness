package io.github.mohammedteir.deepseekharness

import android.app.Activity
import android.content.ComponentName
import android.content.Intent
import android.content.ServiceConnection
import android.os.Bundle
import android.os.IBinder
import android.os.Message
import android.os.Messenger
import android.os.RemoteException
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import android.widget.TextView

/** Loads the original web profile from the app-private loopback server. */
class OriginalWebActivity : Activity() {
    private lateinit var webView: WebView
    private lateinit var status: TextView
    private var bound = false

    private val reply = Messenger(android.os.Handler(android.os.Looper.getMainLooper()) { message ->
        val value = message.data.getString("url") ?: "BLOCKED: web runtime returned no URL"
        if (value.startsWith("BLOCKED:")) {
            status.text = "Original web runtime unavailable\n\n$value"
        } else {
            status.visibility = TextView.GONE
            webView.loadUrl(value)
        }
        true
    })

    private val connection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName, service: IBinder) {
            val request = Messenger(service)
            bound = true
            try {
                request.send(Message.obtain(null, 1).apply { replyTo = reply })
            } catch (error: RemoteException) {
                status.text = "Original web runtime unavailable\n\n${error.message ?: error.javaClass.simpleName}"
            }
        }

        override fun onServiceDisconnected(name: ComponentName) {
            bound = false
            status.text = "Original web runtime disconnected"
        }
    }

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        status = TextView(this).apply {
            text = "Starting original web runtime…"
            textSize = 16f
            setPadding(32, 32, 32, 32)
        }
        webView = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.allowFileAccess = false
            settings.allowContentAccess = false
            settings.allowFileAccessFromFileURLs = false
            settings.allowUniversalAccessFromFileURLs = false
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                    return !request.url.host.orEmpty().let { it == "127.0.0.1" || it == "localhost" }
                }
            }
        }
        setContentView(FrameLayout(this).apply {
            addView(webView, FrameLayout.LayoutParams(-1, -1))
            addView(status, FrameLayout.LayoutParams(-1, -2))
        })
        bindService(Intent(this, OriginalWebRuntimeService::class.java), connection, BIND_AUTO_CREATE)
    }

    override fun onDestroy() {
        if (bound) unbindService(connection)
        webView.destroy()
        super.onDestroy()
    }
}
