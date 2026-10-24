/**
 * copilot.ts — the hands-free loop, written against a tiny GlassesRuntime
 * interface so it is independent of any specific glasses SDK and fully typed.
 *
 * Flow: you speak -> transcript -> route -> (grab a frame only if visual) ->
 * ask your Claude/Grok -> speak + show the answer. No app to open, no Meta AI.
 */

import type { Brain, Bot, Turn } from "./brain.js";
import { route } from "./router.js";

export interface GlassesRuntime {
  /** Fires with final (not partial) transcripts of the wearer's speech. */
  onUtterance(handler: (text: string) => void): void;
  /** Capture one JPEG frame from the camera, base64 (no data: prefix). */
  captureFrame(): Promise<string>;
  /** Play text back through the glasses speakers (TTS). */
  speak(text: string): Promise<void>;
  /** Optional: show text on a display, if the glasses have one. */
  showText?(text: string): void;
}

export interface CopilotOptions {
  defaultBot: Bot;
  /** Keep this many prior turns for follow-ups. */
  historyLimit?: number;
}

export function startCopilot(
  glasses: GlassesRuntime,
  brain: Brain,
  opts: CopilotOptions
): void {
  const historyLimit = opts.historyLimit ?? 6;
  const history: Turn[] = [];
  let busy = false;

  glasses.onUtterance(async (text) => {
    if (!text.trim() || busy) return;
    busy = true;
    try {
      const { bot, prompt, wantsVision } = route(text, opts.defaultBot);
      glasses.showText?.(`${bot}…`);

      const imageBase64 = wantsVision ? await glasses.captureFrame() : undefined;
      const answer = await brain.ask(bot, prompt, { imageBase64, history });

      history.push({ role: "user", text: prompt });
      history.push({ role: "assistant", text: answer });
      while (history.length > historyLimit) history.shift();

      glasses.showText?.(answer);
      await glasses.speak(answer);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      glasses.showText?.(`Error: ${msg}`);
      await glasses.speak("Sorry, I couldn't reach that assistant.");
    } finally {
      busy = false;
    }
  });
}
