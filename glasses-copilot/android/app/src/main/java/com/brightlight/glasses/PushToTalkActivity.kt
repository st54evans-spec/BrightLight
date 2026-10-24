package com.brightlight.glasses

import android.Manifest
import android.graphics.Bitmap
import android.os.Bundle
import android.util.Base64
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.launch
import java.io.ByteArrayOutputStream
import java.util.concurrent.atomic.AtomicReference

/**
 * Push-to-talk test bench. Runs the exact same CopilotController the glasses use,
 * but with the phone's mic, speaker and camera standing in. Try:
 *   "Hey Scout"                       -> Scout's greeting
 *   "Cato, run the numbers on ..."    -> Cato Ledger answers (Grok)
 *   "Claude, any idea what this is?"  -> opens the phone camera, then answers
 */
class PushToTalkActivity : ComponentActivity() {

    private lateinit var glasses: PhoneGlasses
    private lateinit var copilot: CopilotController
    private lateinit var speech: SpeechInput
    private lateinit var log: TextView
    private lateinit var typed: EditText
    private lateinit var talk: Button

    private val pendingCapture = AtomicReference<CompletableDeferred<String>?>(null)

    private val micPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted -> if (granted) startListening() else append("Microphone permission denied.") }

    private val takePicture = registerForActivityResult(
        ActivityResultContracts.TakePicturePreview(),
    ) { bitmap: Bitmap? ->
        val waiting = pendingCapture.getAndSet(null) ?: return@registerForActivityResult
        if (bitmap == null) {
            waiting.completeExceptionally(IllegalStateException("No photo taken"))
        } else {
            val out = ByteArrayOutputStream()
            bitmap.compress(Bitmap.CompressFormat.JPEG, 85, out)
            waiting.complete(Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP))
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val pad = (16 * resources.displayMetrics.density).toInt()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(pad, pad, pad, pad)
        }

        root.addView(TextView(this).apply {
            text = "Phone test bench — same brain, phone mic/camera/speaker."
            textSize = 14f
        })

        talk = Button(this).apply {
            text = "Tap, then talk"
            setOnClickListener { micPermission.launch(Manifest.permission.RECORD_AUDIO) }
        }
        root.addView(talk)

        val typedRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        typed = EditText(this).apply {
            hint = "…or type what you'd say"
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        }
        typedRow.addView(typed)
        typedRow.addView(Button(this).apply {
            text = "Send"
            setOnClickListener {
                val text = typed.text.toString().trim()
                if (text.isNotEmpty()) { typed.setText(""); handle(text) }
            }
        })
        root.addView(typedRow)

        log = TextView(this).apply { textSize = 14f; setPadding(0, pad, 0, 0) }
        root.addView(log)

        setContentView(ScrollView(this).apply { addView(root) })

        val bridge = BridgeClient(Settings(this).bridgeUrl)
        glasses = PhoneGlasses(this, capture = ::capturePhoto) { spoken -> append("🗣  $spoken") }
        copilot = CopilotController(glasses, bridge)
        speech = SpeechInput(this)

        lifecycleScope.launch {
            runCatching { bridge.crew() }
                .onSuccess { crew -> append("Crew: " + crew.joinToString(", ") { it.name }) }
                .onFailure { append("Bridge unreachable (${it.message}). Check Settings.") }
        }
    }

    private fun startListening() {
        if (!speech.isAvailable) {
            append("No speech recognizer on this phone — use the text box.")
            return
        }
        talk.isEnabled = false
        talk.text = "Listening…"
        speech.listen(
            onResult = { heard -> resetTalk(); handle(heard) },
            onError = { msg -> resetTalk(); append("($msg)") },
        )
    }

    private fun resetTalk() {
        talk.isEnabled = true
        talk.text = "Tap, then talk"
    }

    private fun handle(text: String) {
        append("You: $text")
        lifecycleScope.launch {
            runCatching { copilot.handleUtterance(text) }
                .onFailure { append("Error: ${it.message}") }
        }
    }

    /** Opens the phone camera and suspends until a frame comes back (or is cancelled). */
    private suspend fun capturePhoto(): String {
        append("(opening camera for a look)")
        val deferred = CompletableDeferred<String>()
        pendingCapture.set(deferred)
        takePicture.launch(null)
        return deferred.await()
    }

    private fun append(line: String) {
        log.text = if (log.text.isEmpty()) line else "${log.text}\n\n$line"
    }

    override fun onDestroy() {
        super.onDestroy()
        speech.destroy()
        glasses.shutdown()
    }
}
