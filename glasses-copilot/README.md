# glasses-copilot

Hands-free voice **+ vision** copilot for smart glasses that talks to **your own
Claude and Grok accounts** — not Meta AI. Tap (or use your wake phrase), speak,
and when you ask about something in front of you it grabs one camera frame so the
assistant can answer "any idea what that is?"

> This folder is self-contained and deliberately touches nothing else in the
> BrightLight repo. It's easy to move into its own repo — just copy the folder.

## What it does

1. You trigger it and speak. The glasses mic → speech-to-text → a transcript.
2. `router.ts` decides which assistant ("ask Grok…", "Claude, …", or your
   default) and whether the question is visual.
3. If visual, it captures **one** camera frame.
4. `brain.ts` sends your text (+ optional frame) to the Anthropic or xAI API.
5. The reply is spoken back through the glasses speakers (and shown, if the
   glasses have a display).

## Architecture

```
your voice ─▶ [glasses SDK] ─▶ onUtterance(text)
                                   │
                              router.ts  ── which bot? visual?
                                   │
                     wantsVision ? captureFrame() : —
                                   │
                              brain.ts  ── Claude / Grok HTTP API (vision)
                                   │
                 glasses.speak(answer)  +  showText(answer)
```

- `src/brain.ts` — provider calls over plain `fetch`. No SDKs, no Meta. **Portable.**
- `src/router.ts` — pure routing logic. **Unit-tested.**
- `src/copilot.ts` — the loop, written against a tiny `GlassesRuntime` interface.
- `src/server.ts` — HTTP `/ask` bridge a native Ray-Ban Meta app calls. **Tested.**
- `src/mentra-app.ts` — the glasses seam for the MentraOS path.

## Your crew (named bots with their own greetings)

Modeled on `finance/persona.js`: each crew member has a name you call out, a
spoken **greeting**, its own persona, and a backend (Claude or one of your Grok
bots). Say "Scout" and Scout greets you in its voice; "Scout, any idea what this
is" and Scout answers about what you're looking at.

Edit `config/crew.example.json` (copy to `config/crew.json`):

```json
{
  "defaultMemberId": "claude",
  "members": [
    { "id": "scout", "name": "Scout", "provider": "grok",
      "greeting": "Scout, eyes on. Point me at it.",
      "systemPrompt": "You are Scout, a fast, street-smart Grok copilot..." }
  ]
}
```

The bridge serves the roster at `GET /crew` and plays the right greeting on
summon, so the phone app stays simple.

## On Ray-Ban Meta (Wayfarer Gen 2 & Gen 3) — see [META.md](./META.md)

The full Android app is in [`android/`](./android/) — it uses the glasses for
mic/camera/speaker and calls this bridge.

Meta's glasses SDK is native-only, so the device half is a small Swift/Kotlin app
that uses the glasses for mic/camera/speaker and calls the TypeScript brain bridge
(`npm run serve`). Confirmed working on Gen 2 **and** Gen 3 (DAT 1.0.1+, firmware
V128, Meta AI app V292).

- Hands-free entry: **"Hey Meta, start Copilot …"** cold-launches your app with the
  spoken text. That's the only hands-free hook Meta allows.
- Grab **one photo** per visual question (keeps the HFP mic working).
- **Not possible on Meta hardware (for anyone):** custom wake words, disabling
  "Hey Meta", changing the recording LED or privacy settings, Meta AI APIs, or raw
  mic streams. The toolkit is a sandboxed session the wearer can pause anytime.

## Two hardware paths

- **Ray-Ban Meta (Gen 2 / Gen 3):** native Swift/Kotlin app + the brain bridge.
  See [META.md](./META.md). This is the path if you own the Wayfarers.
- **MentraOS / Mentra Live:** open-source (`@mentra/sdk`), owns its own wake word,
  no Meta app at all — the only way to get custom wake words and fuller control.
  Use `src/mentra-app.ts`.

## Run

```bash
cd glasses-copilot
cp .env.example .env     # add your ANTHROPIC_API_KEY and XAI_API_KEY
npm install
npm run build
npm test                 # runs the router tests
```

To run on hardware: `npm i @mentra/sdk`, create an app at
https://console.mentra.glass, then extend `AppServer` and call `runOnSession`
(see the comment block in `src/mentra-app.ts`). Docs: https://docs.mentra.glass

## Scope / safety

This is pointed at **you** and people who've agreed to it: your accounts, your
voice, and a frame only when you ask a visual question. It does not disable any
recording indicator, does not identify strangers, and does not capture audio you
aren't part of.
