/**
 * server.ts — tiny HTTP bridge so a native Ray-Ban Meta app (Swift/Kotlin, using
 * the Meta Wearables Device Access Toolkit) can reuse the TypeScript brain/router
 * instead of reimplementing them. No framework, no deps — testable in plain Node.
 *
 * Handshake (keeps the mobile app dumb; all routing stays here):
 *   POST /ask { text }                      ->  { status: "answer", ... }         (non-visual)
 *   POST /ask { text }                      ->  { status: "need_image", bot, prompt } (visual)
 *   POST /ask { bot, text, imageBase64 }    ->  { status: "answer", bot, answer }  (visual follow-up)
 *   GET  /health                            ->  { ok: true }
 */

import {
  createServer as createHttpServer,
  type ServerResponse,
  type Server,
} from "node:http";
import { route } from "./router.js";
import type { Bot } from "./brain.js";

export interface AskBrain {
  ask(bot: Bot, text: string, opts?: { imageBase64?: string }): Promise<string>;
}

export interface ServerOptions {
  defaultBot: Bot;
}

interface AskBody {
  bot?: Bot;
  text?: string;
  imageBase64?: string;
}

export function createAskServer(brain: AskBrain, opts: ServerOptions): Server {
  return createHttpServer((req, res) => {
    if (req.method === "GET" && req.url === "/health") {
      return json(res, 200, { ok: true });
    }
    if (req.method === "POST" && req.url === "/ask") {
      let raw = "";
      req.on("data", (chunk) => (raw += chunk));
      req.on("end", () => void handleAsk(raw, brain, opts, res));
      return;
    }
    json(res, 404, { error: "not found" });
  });
}

async function handleAsk(
  raw: string,
  brain: AskBrain,
  opts: ServerOptions,
  res: ServerResponse
): Promise<void> {
  let body: AskBody;
  try {
    body = raw ? (JSON.parse(raw) as AskBody) : {};
  } catch {
    return json(res, 400, { error: "invalid JSON" });
  }
  if (!body.text || typeof body.text !== "string") {
    return json(res, 400, { error: "text is required" });
  }

  try {
    // If the app already captured a frame, just answer with it.
    if (body.imageBase64) {
      const bot = body.bot ?? opts.defaultBot;
      const answer = await brain.ask(bot, body.text, { imageBase64: body.imageBase64 });
      return json(res, 200, { status: "answer", bot, answer });
    }

    const decision = route(body.text, body.bot ?? opts.defaultBot);
    // Visual question but no frame yet: tell the app to capture one and come back.
    if (decision.wantsVision) {
      return json(res, 200, {
        status: "need_image",
        bot: decision.bot,
        prompt: decision.prompt,
      });
    }

    const answer = await brain.ask(decision.bot, decision.prompt);
    return json(res, 200, { status: "answer", bot: decision.bot, answer });
  } catch (err) {
    return json(res, 502, {
      error: err instanceof Error ? err.message : String(err),
    });
  }
}

function json(res: ServerResponse, status: number, obj: unknown): void {
  res.writeHead(status, { "content-type": "application/json" });
  res.end(JSON.stringify(obj));
}
