/**
 * server-main.ts — runnable entry for the brain bridge your Ray-Ban Meta app calls.
 *   npm run serve
 */

import { createBrain } from "./brain.js";
import { createAskServer } from "./server.js";
import { loadCrew } from "./load-crew.js";

function env(name: string): string {
  const v = process.env[name];
  if (v === undefined) throw new Error(`Missing env var ${name}`);
  return v;
}

const brain = createBrain({
  anthropicApiKey: env("ANTHROPIC_API_KEY"),
  xaiApiKey: env("XAI_API_KEY"),
  claudeModel: process.env.CLAUDE_MODEL,
  grokModel: process.env.GROK_MODEL,
});

const crew = loadCrew();
const port = Number(process.env.PORT ?? 3200);

createAskServer(brain, { crew }).listen(port, () => {
  console.log(`glasses-copilot brain bridge listening on http://localhost:${port}`);
  console.log(`GET  /crew   roster + greetings`);
  console.log(`POST /ask    { "text": "scout any idea what this is", "imageBase64": "..." }`);
});
