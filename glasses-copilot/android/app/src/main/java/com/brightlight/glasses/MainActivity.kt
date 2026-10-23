package com.brightlight.glasses

import android.Manifest
import android.os.Bundle
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

/**
 * Wires the Meta glasses to the copilot loop. Hands-free entry is the voice
 * invocation ("Hey Meta, start Copilot ..."); there's also a push-to-talk path
 * you can trigger from the phone for testing.
 */
class MainActivity : ComponentActivity() {

    private lateinit var glasses: MetaGlasses
    private lateinit var copilot: CopilotController
    private lateinit var status: TextView

    private val permissions = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { /* proceed regardless; features degrade without mic/BT */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        status = TextView(this).apply { text = "Starting…" }
        setContentView(status)

        permissions.launch(
            arrayOf(
                Manifest.permission.RECORD_AUDIO,
                Manifest.permission.BLUETOOTH_CONNECT,
            )
        )

        // The bridge URL (your `npm run serve`). Put it in BuildConfig or settings.
        val bridge = BridgeClient(BuildConfig.BRIDGE_URL)
        glasses = MetaGlasses(this)
        copilot = CopilotController(glasses, bridge)

        lifecycleScope.launch {
            glasses.register()
            status.text = "Say: \"Hey Meta, start Copilot, any idea what this is\""

            // Hands-free: each invocation is one spoken request.
            glasses.onVoiceInvocation { spoken, done ->
                lifecycleScope.launch {
                    try {
                        copilot.handleUtterance(spoken)
                    } finally {
                        done() // answer the invocation exactly once
                    }
                }
            }

            // Show the crew roster so you know who you can call.
            runCatching { bridge.crew() }.onSuccess { crew ->
                status.text = "Crew: " + crew.joinToString(", ") { it.name }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        glasses.shutdown()
    }
}
