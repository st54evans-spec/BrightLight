/**
 * brain.ts — platform-independent.
 *
 * Takes what you said (and optionally one camera frame) and asks YOUR Claude or
 * Grok account. No Meta AI, no SDK lock-in — just the providers' HTTP APIs, so
 * this file runs anywhere Node 18+ (global fetch) does and is easy to test.
 */

export type Bot = "claude" | "grok";

export interface AskOptions {
  /** JPEG frame as base64 (no data: prefix). Send only for visual questions. */
  imageBase64?: string;
  /** Prior turns for follow-up questions, oldest first. */
  history?: Turn[];
  signal?: AbortSignal;
}

export interface Turn {
  role: "user" | "assistant";
  text: string;
}

export interface BrainConfig {
  anthropicApiKey: string;
  xaiApiKey: string;
  claudeModel?: string;
  grokModel?: string;
  maxTokens?: number;
}

const ANTHROPIC_URL = "https://api.anthropic.com/v1/messages";
const XAI_URL = "https://api.x.ai/v1/chat/completions";

export function createBrain(config: BrainConfig) {
  const claudeModel = config.claudeModel ?? "claude-sonnet-4-5";
  const grokModel = config.grokModel ?? "grok-4";
  const maxTokens = config.maxTokens ?? 400;

  async function ask(bot: Bot, text: string, opts: AskOptions = {}): Promise<string> {
    return bot === "claude"
      ? askClaude(text, opts)
      : askGrok(text, opts);
  }

  async function askClaude(text: string, opts: AskOptions): Promise<string> {
    const userContent: unknown[] = [{ type: "text", text }];
    if (opts.imageBase64) {
      userContent.push({
        type: "image",
        source: { type: "base64", media_type: "image/jpeg", data: opts.imageBase64 },
      });
    }
    const messages = [
      ...(opts.history ?? []).map((t) => ({ role: t.role, content: t.text })),
      { role: "user", content: userContent },
    ];

    const res = await fetch(ANTHROPIC_URL, {
      method: "POST",
      signal: opts.signal,
      headers: {
        "content-type": "application/json",
        "x-api-key": config.anthropicApiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({ model: claudeModel, max_tokens: maxTokens, messages }),
    });
    if (!res.ok) throw new Error(`Claude ${res.status}: ${await res.text()}`);
    const data = (await res.json()) as { content: Array<{ type: string; text?: string }> };
    return data.content
      .filter((b) => b.type === "text")
      .map((b) => b.text ?? "")
      .join("")
      .trim();
  }

  async function askGrok(text: string, opts: AskOptions): Promise<string> {
    const userContent: unknown[] = [{ type: "text", text }];
    if (opts.imageBase64) {
      userContent.push({
        type: "image_url",
        image_url: { url: `data:image/jpeg;base64,${opts.imageBase64}` },
      });
    }
    const messages = [
      ...(opts.history ?? []).map((t) => ({
        role: t.role,
        content: t.text,
      })),
      { role: "user", content: userContent },
    ];

    const res = await fetch(XAI_URL, {
      method: "POST",
      signal: opts.signal,
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${config.xaiApiKey}`,
      },
      body: JSON.stringify({ model: grokModel, max_tokens: maxTokens, messages }),
    });
    if (!res.ok) throw new Error(`Grok ${res.status}: ${await res.text()}`);
    const data = (await res.json()) as {
      choices: Array<{ message: { content: string | null } }>;
    };
    return (data.choices[0]?.message.content ?? "").trim();
  }

  return { ask };
}

export type Brain = ReturnType<typeof createBrain>;
