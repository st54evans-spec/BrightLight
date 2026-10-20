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
- `src/mentra-app.ts` — the glasses-specific seam (MentraOS). The **only** part
  tied to a device SDK.

## Why MentraOS as the default

MentraOS (open-source, MIT, `@mentra/sdk`) runs on Mentra Live and other glasses,
owns its own wake behavior, and keeps Meta AI entirely out of the loop — the
closest match to "just call them up without opening an app." If you're on
Ray-Ban/Oakley Meta instead, keep `brain/router/copilot` as-is and replace
`mentra-app.ts` with a Meta **Wearables Device Access Toolkit** adapter (note:
Meta owns the "Hey Meta" wake word and requires one-time registration in the Meta
AI app; your trigger becomes a tap / action button).

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
