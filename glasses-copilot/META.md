# Running on Ray-Ban Meta (Wayfarer Gen 2 & Gen 3)

This is the native half for Ray-Ban Meta. The glasses' SDK (Meta Wearables Device
Access Toolkit) is native-only, so the app that touches the glasses is a small
Swift (iOS) or Kotlin (Android) app. It uses the glasses for mic/camera/speaker
and calls the TypeScript **brain bridge** (`npm run serve`) for the Claude/Grok
answer. Keeps your API keys off the glasses and reuses the tested routing logic.

```
"Hey Meta, start Copilot, any idea what this is"
        │ (voice invocation cold-launches your app + hands it the text)
        ▼
  native app ── HFP mic ──▶ your STT ──▶ POST /ask {text}
        │                                   │
        │               need_image? ◀───────┘
        │ capture ONE photo (camera)
        └────────── POST /ask {bot, text, imageBase64} ──▶ { answer }
                              │
                       your TTS ──▶ A2DP speaker
```

## What's confirmed (Oct 2026)

- **Both your glasses work.** DAT 1.0 supports Ray-Ban Meta Gen 2 and Gen 3.
  Requires **SDK 1.0.1+**, glasses firmware **V128**, Meta AI app **V292**.
  Gen 3 may report as `DeviceType.rayBanMetaOptics` — accept both it and
  `.rayBanMeta`.
- **Hands-free launch:** register a voice-invocation phrase so
  **"Hey Meta, start Copilot …"** cold-launches your app and delivers the rest of
  the sentence. This is the only hands-free entry Meta exposes (no custom wake
  words, "Hey Meta" can't be replaced).
- **Mic:** Bluetooth HFP, bidirectional mono, tuned to the wearer's voice. Works
  during TTS playback, so you can interrupt with a VAD.
- **Camera:** grab a single photo for visual questions. (A full stream shares the
  BT link with HFP and drops frame rate; in-stream audio is beta and not
  publishable — so single-photo-on-demand is the right pattern here.)

## Hard limits (no workarounds)

- No control over the recording **LED**, privacy settings, or "Hey Meta."
- No Meta AI API, no raw per-mic audio. Beamforming still picks up people within
  ~6 ft, so filter/VAD on your side.
- One session per device; the user can pause/stop by tapping, folding, or removing
  the glasses. A capability can be denied at runtime (`CAPABILITY_DENIED`) — treat
  as expected, not a crash.

## Setup

- iOS 17.2+, Xcode 26.4+. Android 10+, Kotlin 2.2+.
- Create your app in the Wearables Developers Center; add the SDK
  (`facebook/meta-wearables-dat-ios` / `-android`).
- Start against the **Mock Device Kit** before using hardware.
- Point the app at the brain bridge: run `npm run serve` and use its URL.

## iOS (Swift) — the key calls

```swift
import MWDATCore
import MWDATCamera

// 1) One-time registration (deeplinks to the Meta AI app, returns to you)
try await Wearables.shared.register()

// 2) Voice invocation: "Hey Meta, start Copilot ..." cold-launches the app
Wearables.shared.voiceInvocations.listen { invocation in
    let spoken = invocation.text            // the words after your app name
    Task {
        let answer = await handleUtterance(spoken)
        invocation.respond(.success)        // answer exactly once
        await speak(answer)                 // your TTS -> A2DP
    }
}

// 3) Capture ONE frame only when the bridge says it needs vision
func capturePhotoBase64(_ session: DeviceSession) async throws -> String {
    let camera = try session.addCamera()
    let photo = try await camera.capturePhoto()    // single frame
    return photo.jpegData.base64EncodedString()
}
```

HFP mic: configure `AVAudioSession` with `.playAndRecord` + `.allowBluetoothHFP`,
run your streaming STT on the input, then POST the transcript to `/ask`.

## Android (Kotlin) — the key calls

```kotlin
import com.meta.wearables.dat.core.*
import com.meta.wearables.dat.camera.*

// 1) Registration (deeplinks to Meta AI app)
Wearables.register(context)

// 2) Voice invocation stream
Wearables.voiceInvocations().collect { invocation ->
    val spoken = invocation.text
    val answer = handleUtterance(spoken)
    invocation.respond(Response.success())
    speak(answer)                                   // your TTS -> A2DP
}

// 3) Single photo for visual questions
suspend fun capturePhotoBase64(session: DeviceSession): String {
    val camera = session.addCamera()
    val photo = camera.capturePhoto()               // single frame
    return Base64.encodeToString(photo.jpegBytes, Base64.NO_WRAP)
}
```

Mic: use the glasses as a standard HFP input and run your STT on it.

## handleUtterance (both platforms, same shape)

```
POST {bridge}/ask { "text": spoken }
  -> { status: "answer", answer }         : speak(answer)
  -> { status: "need_image", bot, prompt }: photo = capturePhotoBase64()
                                            POST /ask { bot, text: prompt, imageBase64: photo }
                                            -> speak(answer)
```

> The exact SDK symbol names above track DAT 1.0.1 and may shift between SDK
> releases; verify against the version you install. The bridge contract (`/ask`)
> is stable and covered by tests.
