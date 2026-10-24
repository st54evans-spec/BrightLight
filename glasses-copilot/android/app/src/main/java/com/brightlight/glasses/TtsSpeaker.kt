package com.brightlight.glasses

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import kotlinx.coroutines.suspendCancellableCoroutine
import java.util.Locale
import kotlin.coroutines.resume

/**
 * Android TextToSpeech wrapped as a suspend call. Routes to whatever audio device
 * is active — the glasses over A2DP when they're connected, the phone otherwise.
 */
class TtsSpeaker(context: Context) {
    private val tts = TextToSpeech(context) { }

    init {
        tts.language = Locale.US
    }

    suspend fun speak(text: String): Unit = suspendCancellableCoroutine { cont ->
        val id = "copilot-${System.nanoTime()}"
        tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {}
            override fun onDone(utteranceId: String?) { if (cont.isActive) cont.resume(Unit) }
            @Deprecated("deprecated in API 21")
            override fun onError(utteranceId: String?) { if (cont.isActive) cont.resume(Unit) }
        })
        tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, id)
    }

    fun shutdown() = tts.shutdown()
}
