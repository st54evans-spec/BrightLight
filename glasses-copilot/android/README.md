# glasses-copilot — Android app (Ray-Ban Meta Gen 2 & Gen 3)

Native Android app that uses your Ray-Ban Meta glasses for mic, camera, and
speaker, and calls the TypeScript **brain bridge** for the answer. Your crew's
greetings and personas come from the bridge, so "Scout, any idea what this is"
greets you in Scout's voice, then Scout answers.

## How the pieces fit

```
"Hey Meta, start Copilot, Scout any idea what this is"
        │ Meta cold-launches the app + hands it the text
        ▼
  MainActivity ─▶ CopilotController ─▶ BridgeClient ─▶ POST /ask
        │                                                 │
        │                    need_image ◀─────────────────┘
        │  MetaGlasses.capturePhotoBase64()  (one frame)
        └──────────── POST /ask {memberId, prompt, image} ─▶ answer
                               │
                      MetaGlasses.speak(answer)  (TTS → A2DP)
```

- `BridgeClient.kt` — HTTP to the bridge (`/ask`, `/crew`). **Complete.**
- `CopilotController.kt` — the greeting / need-image / answer loop. **Complete.**
- `Glasses.kt` — the device interface the loop depends on. **Complete.**
- `MetaGlasses.kt` — the **DAT seam**: register, voice invocation, photo capture,
  TTS. The marked blocks are where the installed SDK's calls go.
- `MainActivity.kt` — permissions + wiring; buttons to the two screens below.
- `SettingsActivity.kt` + `Settings.kt` — bridge URL, saved on the phone, with a
  **Test connection** button that lists your crew and their greetings. API keys are
  not here on purpose: they stay in the bridge's `.env`.
- `PushToTalkActivity.kt` + `PhoneGlasses.kt` + `SpeechInput.kt` — **phone test
  bench.** Runs the same `CopilotController`, but with the phone's mic (Android
  `SpeechRecognizer`), speaker (TTS) and camera standing in for the glasses, so you
  can test the whole loop today without the DAT SDK wired. **Complete.**

## Test on the phone first

1. Start the bridge: in `glasses-copilot/`, `npm run serve`.
2. Install the app, open **Settings**, enter `http://<computer-LAN-ip>:3200`, tap
   **Test connection** — you should see Claude, Scout, Cato Ledger and their lines.
3. Open **Test on phone**. Tap and say (or type):
   - "Hey Scout" → Scout's greeting
   - "Cato, what's the margin on a $40 item that costs $25" → Cato Ledger (Grok)
   - "Claude, any idea what this is?" → phone camera opens, snap, Claude answers
   Everything is spoken back and logged on screen.

## Compile

The Android SDK is a separate install from the Kotlin source. Android Studio
includes it. On a machine that only has Java 17+, `scripts/install-sdk.sh`
installs the command-line SDK (platform 35 and build-tools) under
`/opt/android-sdk`.

```bash
export ANDROID_HOME=/opt/android-sdk   # or wherever the SDK landed
cd glasses-copilot/android
printf 'sdk.dir=%s\n' "$ANDROID_HOME" > local.properties   # not committed
./gradlew assembleDebug
```

The debug APK is `app/build/outputs/apk/debug/app-debug.apk`. `local.properties`
is gitignored because the SDK path differs per machine.

## Build for the glasses

1. Start the bridge on your computer: in `glasses-copilot/`, `npm run serve`.
   Note your LAN IP (e.g. `192.168.1.20`).
2. Set the bridge URL in the app's **Settings** screen (or the `BRIDGE_URL` default
   in `app/build.gradle.kts`):
   - Emulator → `http://10.0.2.2:3200` (already the default)
   - Real phone → `http://<your-computer-LAN-ip>:3200`
3. Add the DAT SDK: uncomment the `com.meta.wearables.dat:*` deps in
   `app/build.gradle.kts` (add Meta's Maven repo in `settings.gradle.kts` if
   required), and fill the marked blocks in `MetaGlasses.kt` from the SDK:
   https://wearables.developer.meta.com/docs/develop/dat/build-integration-android/
4. Register your app's package (`com.brightlight.glasses`) in the Wearables
   Developers Center, and the voice-invocation phrase so "Hey Meta, start Copilot"
   launches it.
5. Requirements: Android 10+, Kotlin 2.2+, DAT 1.0.1+, glasses firmware V128,
   Meta AI app V292. Start with the Mock Device Kit before using hardware.

## Honest status

The bridge-facing half (HTTP, the loop, crew/greetings, personas) is complete and
covered by tests in the parent project. `./gradlew assembleDebug` compiles the
phone app (settings screen and push-to-talk bench included). The `MetaGlasses.kt` SDK calls are stubbed
and clearly marked — they're the one part to wire against the DAT version you
install, because Meta's symbol names shift between releases. The structure (lifecycle
order, single-photo-to-protect-HFP, answer-once voice invocations, A2DP TTS) follows
the current docs.

## Not possible on Ray-Ban Meta (any app)

Custom wake words, disabling "Hey Meta", touching the recording LED or privacy
settings, Meta AI APIs, raw mic streams. For full control use open hardware
(MentraOS / Mentra Live) — see the parent README.
