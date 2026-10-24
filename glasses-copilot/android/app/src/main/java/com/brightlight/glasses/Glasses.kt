package com.brightlight.glasses

/**
 * Glasses — the device seam. CopilotController depends on this interface, so the
 * app logic is independent of the SDK. MetaGlasses implements it against the Meta
 * Wearables Device Access Toolkit (the one part to verify against the SDK version
 * you install; symbol names track DAT 1.0.1).
 */
interface Glasses {
    /** One-time registration; deeplinks to the Meta AI app and returns. */
    suspend fun register()

    /**
     * Fires when the wearer says "Hey Meta, start Copilot ...". The text is the
     * words after your app name. Answer each invocation exactly once via [done].
     */
    fun onVoiceInvocation(handler: (spoken: String, done: () -> Unit) -> Unit)

    /** Capture ONE JPEG frame, base64 (no data: prefix). Used for visual questions. */
    suspend fun capturePhotoBase64(): String

    /** Speak text to the wearer through the glasses speakers (TTS -> A2DP). */
    suspend fun speak(text: String)
}
