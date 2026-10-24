package com.brightlight.glasses

import android.os.Bundle
import android.text.InputType
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

/**
 * Bridge URL + connection test. API keys are deliberately NOT here: they live in
 * the bridge's .env so nothing secret is ever on the phone or the glasses.
 */
class SettingsActivity : ComponentActivity() {

    private lateinit var settings: Settings
    private lateinit var urlField: EditText
    private lateinit var result: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        settings = Settings(this)

        val pad = (16 * resources.displayMetrics.density).toInt()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(pad, pad, pad, pad)
        }

        root.addView(TextView(this).apply { text = "Bridge URL"; textSize = 16f })
        urlField = EditText(this).apply {
            inputType = InputType.TYPE_TEXT_VARIATION_URI
            hint = "http://192.168.1.20:8787"
            setText(settings.bridgeUrl)
        }
        root.addView(urlField)
        root.addView(TextView(this).apply {
            text = "Your phone's path to `npm run serve`. Use your computer's LAN IP, " +
                "not localhost. Anthropic / xAI keys stay in the bridge's .env."
            textSize = 13f
        })

        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row.addView(Button(this).apply {
            text = "Save"
            setOnClickListener {
                settings.bridgeUrl = urlField.text.toString()
                result.text = "Saved."
            }
        })
        row.addView(Button(this).apply {
            text = "Test connection"
            setOnClickListener { testConnection() }
        })
        root.addView(row)

        result = TextView(this).apply { textSize = 14f; setPadding(0, pad, 0, 0) }
        root.addView(result)

        setContentView(ScrollView(this).apply { addView(root) })
    }

    private fun testConnection() {
        val url = urlField.text.toString().trim()
        result.text = "Connecting to $url …"
        lifecycleScope.launch {
            runCatching { BridgeClient(url).crew() }
                .onSuccess { crew ->
                    settings.bridgeUrl = url
                    result.text = buildString {
                        appendLine("Connected. Crew on duty:")
                        for (m in crew) {
                            appendLine()
                            appendLine("${m.name}  (${m.provider})")
                            appendLine("  \"${m.greeting}\"")
                        }
                    }
                }
                .onFailure { e ->
                    result.text = "Couldn't reach the bridge: ${e.message}\n\n" +
                        "Check that `npm run serve` is running, the phone is on the same " +
                        "Wi-Fi, and the URL uses the computer's LAN IP."
                }
        }
    }
}
