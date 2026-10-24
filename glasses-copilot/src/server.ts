/**
 * server.ts — HTTP bridge the native Ray-Ban Meta app calls. Crew-aware: it owns
 * the roster, greetings, and personas so the mobile app stays dumb. No deps.
 *
 * Handshake:
 *   GET  /crew                              -> roster (names + greetings, no keys)
 *   POST /ask { text }                      -> { status: "greeting", ... }   (bare "Hey Scout")
 *   POST /ask { text }                      -> { status: "need_image", ... } (visual question)
 *   POST /ask { text }                      -> { status: "answer", ... }     (spoken answer)
 *   POST /ask { memberId, text, imageBase64 } -> { status: "answer", ... }   (visual follow-up)
 *   GET  /health                            -> { ok: true }
 */

import {
  createServer as createHttpServer,
  type ServerResponse,
  type Server,
} from "node:http";
import { routeToCrew, findMember, type Crew } from "./crew.js";
import type { Bot } from "./brain.js";

export interface AskBrain {
  ask(
    bot: Bot,
    text: string,
    opts?: { imageBase64?: string; systemPrompt?: string }
  ): Promise<string>;
}

export interface ServerOptions {
  crew: Crew;
}

interface AskBody {
  memberId?: string;
  text?: string;
  imageBase64?: string;
}

export function createAskServer(brain: AskBrain, opts: ServerOptions): Server {
  return createHttpServer((req, res) => {
    if (req.method === "GET" && req.url === "/health") {
      return json(res, 200, { ok: true });
    }
    if (req.method === "GET" && req.url === "/crew") {
      return json(res, 200, {
        defaultMemberId: opts.crew.defaultMemberId,
        members: opts.crew.members.map((m) => ({
          id: m.id,
          name: m.name,
          aliases: m.aliases ?? [],
          provider: m.provider,
          greeting: m.greeting,
        })),
      });
    }
    if (req.method === "POST" && req.url === "/ask") {
      let raw = "";
      req.on("data", (chunk) => (raw += chunk));
      req.on("end", () => void handleAsk(raw, brain, opts.crew, res));
      return;
    }
    json(res, 404, { error: "not found" });
  });
}

async function handleAsk(
  raw: string,
  brain: AskBrain,
  crew: Crew,
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
    // Follow-up with a captured frame: answer as the chosen member.
    if (body.imageBase64) {
      const member = body.memberId
        ? findMember(crew, body.memberId)
        : findMember(crew, crew.defaultMemberId);
      const answer = await brain.ask(member.provider, body.text, {
        imageBase64: body.imageBase64,
        systemPrompt: member.systemPrompt,
      });
      return json(res, 200, { status: "answer", member: member.id, name: member.name, answer });
    }

    const r = routeToCrew(body.text, crew);

    // Bare summon ("Hey Scout") -> greet in that member's voice.
    if (r.summoned && !r.hasPrompt) {
      return json(res, 200, {
        status: "greeting",
        member: r.member.id,
        name: r.member.name,
        greeting: r.member.greeting,
      });
    }

    // Visual question without a frame -> ask the app to capture one.
    if (r.wantsVision) {
      return json(res, 200, {
        status: "need_image",
        member: r.member.id,
        name: r.member.name,
        prompt: r.prompt,
      });
    }

    const answer = await brain.ask(r.member.provider, r.prompt, {
      systemPrompt: r.member.systemPrompt,
    });
    return json(res, 200, { status: "answer", member: r.member.id, name: r.member.name, answer });
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
