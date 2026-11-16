package io.github.mohammedteir.deepseekharness

import android.app.Activity
import android.graphics.Typeface
import android.os.Bundle
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/** Explains why packaged web assets cannot boot before the Harness runtime is connected. */
class OriginalWebActivity : Activity() {
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val density = resources.displayMetrics.density
        fun dp(value: Int) = (value * density).toInt()

        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(24), dp(24), dp(24), dp(24))
            addView(TextView(this@OriginalWebActivity).apply {
                text = "Original web assets"
                textSize = 22f
                setTypeface(typeface, Typeface.BOLD)
            })
            addView(TextView(this@OriginalWebActivity).apply {
                text = "Not available in this build"
                textSize = 14f
                setPadding(0, dp(8), 0, dp(20))
            })
            addView(TextView(this@OriginalWebActivity).apply {
                text = "This APK includes the frontend files, but it does not yet start the on-device Harness web runtime or connect it to the WebView. The frontend needs that runtime to provide its boot data and authenticated local connection. Without them, loading the static page produces a plugin error instead of the app."
                textSize = 16f
                setLineSpacing(dp(4).toFloat(), 1f)
                setTextIsSelectable(true)
            })
        }
        setContentView(ScrollView(this).apply {
            isFillViewport = true
            addView(content)
        })
    }
}
