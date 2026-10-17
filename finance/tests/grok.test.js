const test = require("node:test");
const assert = require("node:assert/strict");

const KEY = "test-not-a-secret";
const grok = require("../grok");

function withEnv(extra, fn) {
  const keys = ["XAI_API_KEY", "XAI_AGENT_TOOLS", "XAI_LIVE_SEARCH"];
  const saved = {};
  for (const k of keys) saved[k] = process.env[k];
  for (const k of keys) delete process.env[k];
  Object.assign(process.env, extra);
  return Promise.resolve()
    .then(fn)
    .finally(() => {
      for (const k of keys) {
        if (saved[k] == null) delete process.env[k];
        else process.env[k] = saved[k];
      }
    });
}

test("lender lookups use web_search and x_search, not search_parameters", async () => {
  const seen = [];
  const original = global.fetch;
  global.fetch = async (url, opts) => {
    seen.push({ url, body: JSON.parse(opts.body) });
    return {
      ok: true,
      json: async () => ({
        id: "resp_1",
        output: [
          {
            type: "web_search_call",
            status: "completed",
            action: { type: "search", query: "SBA 7(a) rate cap" },
          },
          {
            type: "message",
            role: "assistant",
            content: [
              {
                type: "output_text",
                text: "SBA 7(a) cap is prime + 2.75%.",
                annotations: [{ type: "url_citation", url: "https://www.sba.gov/funding-programs/loans/7a-loans" }],
              },
            ],
          },
        ],
        citations: ["https://www.sba.gov/funding-programs/loans/7a-loans"],
      }),
    };
  };
  try {
    await withEnv({ XAI_API_KEY: KEY }, async () => {
      const out = await grok.chat({ message: "What is the current SBA 7(a) rate?", ctx: { userId: 1 }, history: [] });
      assert.equal(seen.length, 1);
      assert.match(String(seen[0].url), /\/responses$/);
      assert.equal(seen[0].body.search_parameters, undefined);
      assert.equal(Object.prototype.hasOwnProperty.call(seen[0].body, "search_parameters"), false);
      assert.ok(seen[0].body.tools.some((tool) => tool.type === "web_search"));
      assert.ok(seen[0].body.tools.some((tool) => tool.type === "x_search"));
      assert.ok(seen[0].body.tools.some((tool) => tool.type === "function" && tool.name === "compare_loans"));
      const system = seen[0].body.input.find((m) => m.role === "system").content;
      assert.match(system, /get_tax_deadlines/);
      assert.match(system, /Never supply a due date from memory/);
      assert.match(system, /April 15 2026/);
      assert.match(system, /January 15 2027/);
      assert.match(system, /April 15 2027/);
      assert.match(system, /web_search/);
      assert.equal(out.reply, "SBA 7(a) cap is prime + 2.75%.");
      assert.deepEqual(out.citations, ["https://www.sba.gov/funding-programs/loans/7a-loans"]);
      assert.equal(out.toolCalls[0].name, "web_search");
    });
  } finally {
    global.fetch = original;
  }
});

test("custom tools round-trip on the responses API without agent search", async () => {
  const seen = [];
  const original = global.fetch;
  let n = 0;
  global.fetch = async (url, opts) => {
    const body = JSON.parse(opts.body);
    seen.push(body);
    n += 1;
    if (n === 1) {
      return {
        ok: true,
        json: async () => ({
          id: "resp_fn",
          output: [{ type: "function_call", name: "list_lenders", call_id: "call_1", arguments: '{"kind":"heloc"}' }],
        }),
      };
    }
    return {
      ok: true,
      json: async () => ({
        id: "resp_done",
        output: [{ type: "message", content: [{ type: "output_text", text: "Catalog loaded." }] }],
      }),
    };
  };
  try {
    await withEnv({ XAI_API_KEY: KEY, XAI_AGENT_TOOLS: "off", XAI_LIVE_SEARCH: "on" }, async () => {
      const out = await grok.chat({ message: "List HELOC lenders", ctx: { userId: 1 }, history: [] });
      assert.equal(seen[0].search_parameters, undefined);
      assert.equal(seen[0].tools.some((tool) => tool.type === "web_search" || tool.type === "x_search"), false);
      assert.ok(seen[0].tools.some((tool) => tool.type === "function" && tool.name === "list_lenders"));
      assert.equal(seen[1].previous_response_id, "resp_fn");
      assert.equal(seen[1].input[0].type, "function_call_output");
      assert.equal(seen[1].input[0].call_id, "call_1");
      assert.ok(JSON.parse(seen[1].input[0].output).lenders.length > 0);
      assert.equal(out.toolCalls[0].name, "list_lenders");
      assert.equal(out.toolCalls[0].args.kind, "heloc");
      assert.equal(out.reply, "Catalog loaded.");
    });
  } finally {
    global.fetch = original;
  }
});
