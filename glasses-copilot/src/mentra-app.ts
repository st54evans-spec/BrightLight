/**
 * mentra-app.ts — the glasses-specific seam.
 *
 * This wires the platform-independent copilot loop to MentraOS (open, MIT, runs
 * on Mentra Live and other glasses, owns its own wake behavior, no Meta app).
 *
 * The MentraOS binding below is the ONE place to verify against the current SDK,
 * because method names move between versions. Everything it depends on
 * (copilot/brain/router) is plain, tested TypeScript.
 *
 * Docs: https://docs.mentra.glass  •  SDK: @mentra/sdk  •  console.mentra.glass
 *
 * Install the SDK when you're ready to run on hardware:
 *   npm i @mentra/sdk
 */

import { createBrain, type Bot } from "./brain.js";
import { startCopilot, type GlassesRuntime } from "./copilot.js";

function env(name: string, fallback?: string): string {
  const v = process.env[name] ?? fallback;
  if (v === undefined) throw new Error(`Missing env var ${name}`);
  return v;
}

const brain = createBrain({
  anthropicApiKey: env("ANTHROPIC_API_KEY"),
  xaiApiKey: env("XAI_API_KEY"),
  claudeModel: process.env.CLAUDE_MODEL,
  grokModel: process.env.GROK_MODEL,
});

const defaultBot = (env("DEFAULT_BOT", "claude") as Bot);

/**
 * Adapt a MentraOS session to our GlassesRuntime. Pseudocode against @mentra/sdk
 * is left inline and commented so the file type-checks on its own; replace the
 * bodies with the real calls from the SDK version you install.
 */
function makeMentraRuntime(session: MentraSessionLike): GlassesRuntime {
  return {
    onUtterance(handler) {
      // session.events.onTranscription(d => { if (d.isFinal) handler(d.text); })
      session.onFinalTranscript(handler);
    },
    async captureFrame() {
      // const photo = await session.camera.requestPhoto();
      // return photo.base64; // JPEG, strip any data: prefix
      return session.capturePhotoBase64();
    },
    async speak(text) {
      // await session.audio.speak(text);  // MentraOS TTS
      await session.speak(text);
    },
    showText(text) {
      // session.layouts.showTextWall(text);
      session.showTextWall?.(text);
    },
  };
}

/**
 * Minimal structural type for what we use from a MentraOS session. Keeping it
 * here (instead of importing from @mentra/sdk) lets the project build and test
 * before the SDK is installed; swap to the real import when wiring hardware.
 */
interface MentraSessionLike {
  onFinalTranscript(handler: (text: string) => void): void;
  capturePhotoBase64(): Promise<string>;
  speak(text: string): Promise<void>;
  showTextWall?(text: string): void;
}

/**
 * Entry point. With @mentra/sdk installed, extend its AppServer and call this
 * from onSession(session):
 *
 *   import { AppServer } from "@mentra/sdk";
 *   class App extends AppServer {
 *     protected async onSession(session) { runOnSession(session); }
 *   }
 *   new App({ packageName: ..., apiKey: ..., port: ... }).start();
 */
export function runOnSession(session: MentraSessionLike): void {
  const glasses = makeMentraRuntime(session);
  startCopilot(glasses, brain, { defaultBot });
}

console.log(
  "glasses-copilot core loaded. Install @mentra/sdk and call runOnSession(session) " +
    "from your AppServer.onSession to run on hardware. See README.md."
);
