package com.brightlight.glasses

import android.util.Log

/**
 * The hands-free loop, independent of the glasses SDK:
 *   spoken text -> bridge -> greeting / need_image / answer -> speak.
 * On a visual question the bridge replies need_image; we capture one frame and
 * send it back as the chosen crew member.
 */
class CopilotController(
    private val glasses: Glasses,
    private val bridge: BridgeClient,
) {
    suspend fun handleUtterance(spoken: String) {
        if (spoken.isBlank()) return
        when (val r = bridge.ask(spoken)) {
            is BridgeClient.AskResult.Greeting -> glasses.speak(r.greeting)

            is BridgeClient.AskResult.Answer -> glasses.speak(r.answer)

            is BridgeClient.AskResult.NeedImage -> {
                val frame = try {
                    glasses.capturePhotoBase64()
                } catch (e: Exception) {
                    glasses.speak("I couldn't use the camera just now.")
                    return
                }
                when (val follow = bridge.ask(r.prompt, memberId = r.memberId, imageBase64 = frame)) {
                    is BridgeClient.AskResult.Answer -> glasses.speak(follow.answer)
                    is BridgeClient.AskResult.Failure -> speakError(follow.message)
                    else -> glasses.speak("I got a confusing response. Try again.")
                }
            }

            is BridgeClient.AskResult.Failure -> speakError(r.message)
        }
    }

    private suspend fun speakError(message: String) {
        Log.w("Copilot", "bridge failure: $message")
        glasses.speak("Sorry, I couldn't reach the crew.")
    }
}
