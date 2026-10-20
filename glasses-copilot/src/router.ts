/**
 * router.ts — turns a raw voice transcript into a routing decision:
 *   - which assistant to use (you can just say "ask Grok..." / "Claude, ...")
 *   - whether the question is about what you're looking at, so we should grab
 *     one camera frame before asking.
 *
 * Pure, deterministic, no network — this is the part that is unit-tested.
 */

import type { Bot } from "./brain.js";

export interface RouteResult {
  bot: Bot;
  /** Transcript with any leading "ask grok"/"hey claude" address stripped. */
  prompt: string;
  /** True when the question refers to the wearer's surroundings. */
  wantsVision: boolean;
}

const BOT_ADDRESS = [
  { bot: "grok" as Bot, re: /^\s*(?:hey\s+|ok\s+|ask\s+|yo\s+)?grok[\s,:-]+/i },
  { bot: "claude" as Bot, re: /^\s*(?:hey\s+|ok\s+|ask\s+|yo\s+)?claude[\s,:-]+/i },
];

// Phrases that mean "use my eyes," i.e. look through the camera.
const VISION_HINTS = [
  /\bwhat('?s| is| are| am i)\b.*\b(this|that|these|those|looking at|in front)\b/i,
  /\b(look at|see this|see that|check this out|read this|describe)\b/i,
  /\bwhat do you see\b/i,
  /\bwhat kind of\b.*\b(this|that)\b/i,
  /\b(identify|what plant|what animal|what building|what landmark)\b/i,
  /\bany idea what (this|that|it) is\b/i,
];

export function route(transcript: string, defaultBot: Bot): RouteResult {
  let bot = defaultBot;
  let prompt = transcript.trim();

  for (const { bot: b, re } of BOT_ADDRESS) {
    if (re.test(prompt)) {
      bot = b;
      prompt = prompt.replace(re, "").trim();
      break;
    }
  }

  const wantsVision = VISION_HINTS.some((re) => re.test(prompt));
  return { bot, prompt, wantsVision };
}
