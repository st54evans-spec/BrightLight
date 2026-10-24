package com.brightlight.glasses

import android.content.Context

/**
 * A [Glasses] stand-in that uses the phone itself: phone mic/speaker for voice and
 * the phone camera for vision. Lets you test the whole crew loop (summon →
 * greeting, question → answer, "any idea what this is" → photo → answer) before
 * the Meta SDK is wired up or when the glasses aren't on your face.
 */
class PhoneGlasses(
    context: Context,
    private val capture: suspend () -> String,
    private val onSpoken: (String) -> Unit = {},
) : Glasses {
    private val tts = TtsSpeaker(context)

    override suspend fun register() {}

    override fun onVoiceInvocation(handler: (spoken: String, done: () -> Unit) -> Unit) {}

    override suspend fun capturePhotoBase64(): String = capture()

    override suspend fun speak(text: String) {
        onSpoken(text)
        tts.speak(text)
    }

    fun shutdown() = tts.shutdown()
}
