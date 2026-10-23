/**
 * server-main.ts — runnable entry for the brain bridge your Ray-Ban Meta app calls.
 *   npm run serve
 */

import { createBrain, type Bot } from "./brain.js";
import { createAskServer } from "./server.js";

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

const port = Number(process.env.PORT ?? 3200);
const defaultBot = env("DEFAULT_BOT", "claude") as Bot;

createAskServer(brain, { defaultBot }).listen(port, () => {
  console.log(`glasses-copilot brain bridge listening on http://localhost:${port}`);
  console.log(`POST /ask  { "text": "any idea what this is", "imageBase64": "..." }`);
});
