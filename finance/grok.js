// xAI Grok client (OpenAI-compatible chat completions) with a tool-calling loop.
// Env: XAI_API_KEY (required), XAI_MODEL (default grok-4), XAI_LIVE_SEARCH (default on),
// XAI_BASE_URL (default https://api.x.ai/v1).
const tools = require("./tools");
const { systemPrompt, BOT_NAME } = require("./persona");

const BASE = process.env.XAI_BASE_URL || "https://api.x.ai/v1";
const MODEL = process.env.XAI_MODEL || "grok-4";
const MAX_ROUNDS = 6;

function configured() {
  return !!process.env.XAI_API_KEY;
}

async function completion(body) {
  const res = await fetch(BASE + "/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + process.env.XAI_API_KEY },
    body: JSON.stringify(body),
  });
  const json = await res.json();
  if (!res.ok) throw new Error((json.error && (json.error.message || json.error)) || "xAI error " + res.status);
  return json;
}

/**
 * Run one user turn. history = prior [{role, content}] messages.
 * Returns { reply, toolCalls: [{name, args, result}], citations }.
 */
async function chat({ history = [], message, ctx, notes }) {
  const toolCalls = [];
  if (!configured()) {
    return {
      reply: `${BOT_NAME} here. My brain (xAI Grok) is not connected: set XAI_API_KEY on the server. The calculators, calendar, and reports still work from the dashboard and the REST API.`,
      toolCalls,
      offline: true,
    };
  }
  const messages = [{ role: "system", content: systemPrompt({ notes }) }, ...history.slice(-30), { role: "user", content: message }];
  const liveSearch = (process.env.XAI_LIVE_SEARCH || "on") !== "off";

  for (let round = 0; round < MAX_ROUNDS; round++) {
    const body = { model: MODEL, messages, tools: tools.openAiToolDefs(), tool_choice: "auto", temperature: 0.3 };
    if (liveSearch) body.search_parameters = { mode: "auto", return_citations: true };
    const json = await completion(body);
    const choice = json.choices && json.choices[0];
    if (!choice) throw new Error("Empty response from xAI");
    const msg = choice.message;
    messages.push(msg);
    if (msg.tool_calls && msg.tool_calls.length) {
      for (const tc of msg.tool_calls) {
        let args = {};
        try {
          args = JSON.parse(tc.function.arguments || "{}");
        } catch (e) {
          args = {};
        }
        let result;
        try {
          result = await tools.run(tc.function.name, args, ctx);
        } catch (e) {
          result = { error: e.message };
        }
        toolCalls.push({ name: tc.function.name, args, result });
        messages.push({ role: "tool", tool_call_id: tc.id, content: JSON.stringify(result) });
      }
      continue;
    }
    return { reply: msg.content || "", toolCalls, citations: json.citations || [] };
  }
  return { reply: "I ran out of tool rounds. Ask again with a narrower question.", toolCalls };
}

module.exports = { chat, configured, MODEL };
