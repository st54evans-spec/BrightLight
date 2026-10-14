// xAI Grok client. Chat uses the Responses API so custom finance tools and
// server-side Agent Tools can run in the same turn.
// Env: XAI_API_KEY (required), XAI_MODEL (default grok-4),
// XAI_AGENT_TOOLS (default on; XAI_LIVE_SEARCH is the legacy alias),
// XAI_BASE_URL (default https://api.x.ai/v1).
// Lender-rate lookups use server-side web_search and x_search. The retired
// Live Search field search_parameters is not sent.
const tools = require("./tools");
const { systemPrompt, BOT_NAME } = require("./persona");

const BASE = process.env.XAI_BASE_URL || "https://api.x.ai/v1";
const MODEL = process.env.XAI_MODEL || "grok-4";
const MAX_ROUNDS = 6;

function configured() {
  return !!process.env.XAI_API_KEY;
}

/** Server-side web_search / x_search for current lender rates. Default on. */
function agentToolsOn() {
  const flag = process.env.XAI_AGENT_TOOLS != null ? process.env.XAI_AGENT_TOOLS : process.env.XAI_LIVE_SEARCH;
  return (flag == null ? "on" : flag) !== "off";
}

function requestTools() {
  const defs = tools.responsesToolDefs();
  if (agentToolsOn()) defs.push({ type: "web_search" }, { type: "x_search" });
  return defs;
}

async function responses(body) {
  const res = await fetch(BASE + "/responses", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + process.env.XAI_API_KEY },
    body: JSON.stringify(body),
  });
  const json = await res.json();
  if (!res.ok) throw new Error((json.error && (json.error.message || json.error)) || "xAI error " + res.status);
  return json;
}

function replyText(json) {
  const parts = [];
  for (const item of json.output || []) {
    if (item.type !== "message" || !Array.isArray(item.content)) continue;
    for (const c of item.content) {
      if (c && typeof c.text === "string" && c.text) parts.push(c.text);
    }
  }
  return parts.join("\n").trim();
}

function citationsFrom(json) {
  const urls = [];
  if (Array.isArray(json.citations)) {
    for (const c of json.citations) urls.push(typeof c === "string" ? c : c && c.url);
  }
  for (const item of json.output || []) {
    for (const c of item.content || []) {
      for (const a of (c && c.annotations) || []) if (a && a.url) urls.push(a.url);
    }
  }
  return [...new Set(urls.filter(Boolean))];
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
  const toolDefs = requestTools();
  let input = [{ role: "system", content: systemPrompt({ notes }) }, ...history.slice(-30), { role: "user", content: message }];
  let previousResponseId = null;
  const citations = [];

  for (let round = 0; round < MAX_ROUNDS; round++) {
    const body = { model: MODEL, input, tools: toolDefs, tool_choice: "auto", temperature: 0.3, store: true };
    if (previousResponseId) body.previous_response_id = previousResponseId;
    const json = await responses(body);
    previousResponseId = json.id || previousResponseId;
    for (const url of citationsFrom(json)) if (!citations.includes(url)) citations.push(url);

    const calls = [];
    for (const item of json.output || []) {
      if (item.type === "web_search_call" || item.type === "x_search_call") {
        const name = item.type === "x_search_call" ? "x_search" : "web_search";
        toolCalls.push({ name, args: item.action || {}, result: { serverSide: true, status: item.status || "completed" } });
      } else if (item.type === "function_call") {
        calls.push(item);
      }
    }
    if (!calls.length) return { reply: replyText(json), toolCalls, citations };

    input = [];
    for (const tc of calls) {
      let args = {};
      try {
        args = typeof tc.arguments === "string" ? JSON.parse(tc.arguments || "{}") : tc.arguments || {};
      } catch (e) {
        args = {};
      }
      let result;
      try {
        result = await tools.run(tc.name, args, ctx);
      } catch (e) {
        result = { error: e.message };
      }
      toolCalls.push({ name: tc.name, args, result });
      input.push({ type: "function_call_output", call_id: tc.call_id || tc.id, output: JSON.stringify(result) });
    }
  }
  return { reply: "I ran out of tool rounds. Ask again with a narrower question.", toolCalls, citations };
}

module.exports = { chat, configured, MODEL, agentToolsOn };
