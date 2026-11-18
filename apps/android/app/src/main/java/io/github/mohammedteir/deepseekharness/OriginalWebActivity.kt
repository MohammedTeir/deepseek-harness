package io.github.mohammedteir.deepseekharness

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.os.Bundle
import android.os.IBinder
import android.os.Message
import android.os.Messenger
import android.os.RemoteException
import android.view.View
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast

/** Loads the original web profile from the app-private loopback server. */
class OriginalWebActivity : Activity() {
    private lateinit var webView: WebView
    private lateinit var status: TextView
    private lateinit var statusPanel: LinearLayout
    private lateinit var copyButton: Button
    private var bound = false

    private fun showFailure(message: String) {
        status.text = "Original web runtime unavailable\n\n$message"
        statusPanel.visibility = View.VISIBLE
        copyButton.visibility = View.VISIBLE
    }

    private val reply = Messenger(android.os.Handler(android.os.Looper.getMainLooper()) { message ->
        val value = message.data.getString("url") ?: "BLOCKED: web runtime returned no URL"
        if (value.startsWith("BLOCKED:")) {
            showFailure(value)
        } else {
            statusPanel.visibility = View.GONE
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
                showFailure(error.message ?: error.javaClass.simpleName)
            }
        }

        override fun onServiceDisconnected(name: ComponentName) {
            bound = false
            showFailure("Original web runtime disconnected")
        }
    }

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        status = TextView(this).apply {
            text = "Starting original web runtime…"
            textSize = 16f
            setPadding(32, 32, 32, 32)
            setTextIsSelectable(true)
        }
        copyButton = Button(this).apply {
            text = "Copy complete error"
            visibility = View.GONE
            setOnClickListener {
                val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                clipboard.setPrimaryClip(ClipData.newPlainText("Harness Original Web error", status.text))
                Toast.makeText(this@OriginalWebActivity, "Error copied", Toast.LENGTH_SHORT).show()
            }
        }
        statusPanel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(ScrollView(this@OriginalWebActivity).apply {
                isFillViewport = true
                addView(status)
            }, LinearLayout.LayoutParams(-1, 0, 1f))
            addView(copyButton, LinearLayout.LayoutParams(-1, -2))
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
            addView(statusPanel, FrameLayout.LayoutParams(-1, -1))
        })
        bindService(Intent(this, OriginalWebRuntimeService::class.java), connection, BIND_AUTO_CREATE)
    }

    override fun onDestroy() {
        if (bound) unbindService(connection)
        webView.destroy()
        super.onDestroy()
    }
}
