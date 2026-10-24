package com.brightlight.glasses

import android.content.Context

/**
 * MetaGlasses — Meta Wearables Device Access Toolkit implementation of [Glasses].
 *
 * THIS IS THE SEAM TO VERIFY against the DAT version you install (symbol names
 * track SDK 1.0.1). The marked blocks are where the real SDK calls go; the
 * surrounding structure (lifecycle order, HFP-vs-camera handling, TTS) is correct
 * and matches the docs. Works on Ray-Ban Meta Gen 2 and Gen 3 — accept both
 * DeviceType.rayBanMeta and .rayBanMetaOptics.
 *
 * Requires: DAT 1.0.1+, glasses firmware V128, Meta AI app V292.
 * Docs: https://wearables.developer.meta.com/docs/develop/dat
 */
class MetaGlasses(private val context: Context) : Glasses {

    private val tts = TtsSpeaker(context)
    // private val wearables = Wearables.init(context, BuildConfig.META_PACKAGE_NAME)
    // private var session: DeviceSession? = null

    override suspend fun register() {
        // === DAT seam ===
        // Deeplinks to the Meta AI app for a one-time confirmation, then returns.
        //   wearables.register()
        // Then open a device session once registered:
        //   session = wearables.startDeviceSession()
        //   observe DeviceSessionState; perform live work only while STARTED.
    }

    override fun onVoiceInvocation(handler: (String, () -> Unit) -> Unit) {
        // === DAT seam ===
        // "Hey Meta, start Copilot ..." cold-launches the app and delivers the
        // spoken text as a voice invocation (a Wearables-level stream, not a
        // device-session capability). Answer each one exactly once.
        //
        //   wearables.voiceInvocations().collect { invocation ->
        //       handler(invocation.text) { invocation.respond(Response.success()) }
        //   }
    }

    override suspend fun capturePhotoBase64(): String {
        // === DAT seam ===
        // Single photo keeps the HFP mic alive (a full stream shares the BT link
        // and drops frame rate). Capture one frame and base64-encode the JPEG.
        //
        //   val camera = session!!.addCamera()
        //   val photo = camera.capturePhoto()
        //   return Base64.encodeToString(photo.jpegBytes, Base64.NO_WRAP)
        throw NotImplementedError("Wire camera.capturePhoto() from the installed DAT SDK")
    }

    override suspend fun speak(text: String) {
        // TTS routes to the glasses over A2DP when they're the active output. (If
        // an HFP mic session is open, release it first so the speaker isn't stuck
        // at mono voice quality.)
        tts.speak(text)
    }

    fun shutdown() = tts.shutdown()
}
