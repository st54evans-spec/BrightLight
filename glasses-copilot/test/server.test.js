import test from "node:test";
import assert from "node:assert/strict";
import { createAskServer } from "../dist/server.js";

const CREW = {
  defaultMemberId: "claude",
  members: [
    { id: "claude", name: "Claude", provider: "claude", greeting: "Claude here.", systemPrompt: "be claude" },
    { id: "scout", name: "Scout", provider: "grok", greeting: "Scout, eyes on.", systemPrompt: "be scout" },
  ],
};

function makeFakeBrain() {
  const calls = [];
  return {
    calls,
    ask(bot, text, opts = {}) {
      calls.push({ bot, text, imageBase64: opts.imageBase64, systemPrompt: opts.systemPrompt });
      return Promise.resolve(`[${bot}] ${text}${opts.imageBase64 ? " (saw image)" : ""}`);
    },
  };
}

async function withServer(brain, fn) {
  const server = createAskServer(brain, { crew: CREW });
  await new Promise((r) => server.listen(0, r));
  const { port } = server.address();
  try {
    return await fn(`http://127.0.0.1:${port}`);
  } finally {
    await new Promise((r) => server.close(r));
  }
}

const post = (base, body) =>
  fetch(`${base}/ask`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });

test("health check", async () => {
  await withServer(makeFakeBrain(), async (base) => {
    const res = await fetch(`${base}/health`);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { ok: true });
  });
});

test("crew roster lists members and greetings, no system prompts", async () => {
  await withServer(makeFakeBrain(), async (base) => {
    const res = await fetch(`${base}/crew`);
    const data = await res.json();
    assert.equal(data.defaultMemberId, "claude");
    assert.equal(data.members.length, 2);
    assert.equal(data.members[1].greeting, "Scout, eyes on.");
    assert.equal(data.members[1].systemPrompt, undefined);
  });
});

test("bare summon returns that member's greeting, no model call", async () => {
  const brain = makeFakeBrain();
  await withServer(brain, async (base) => {
    const res = await post(base, { text: "hey Scout" });
    const data = await res.json();
    assert.equal(data.status, "greeting");
    assert.equal(data.member, "scout");
    assert.equal(data.greeting, "Scout, eyes on.");
    assert.equal(brain.calls.length, 0);
  });
});

test("non-visual question routes to the named member with its persona", async () => {
  const brain = makeFakeBrain();
  await withServer(brain, async (base) => {
    const res = await post(base, { text: "Scout what's 20 percent of 85" });
    const data = await res.json();
    assert.equal(data.status, "answer");
    assert.equal(data.member, "scout");
    assert.equal(brain.calls[0].bot, "grok");
    assert.equal(brain.calls[0].systemPrompt, "be scout");
  });
});

test("visual question without a frame asks for an image first", async () => {
  const brain = makeFakeBrain();
  await withServer(brain, async (base) => {
    const res = await post(base, { text: "Scout any idea what this is" });
    const data = await res.json();
    assert.equal(data.status, "need_image");
    assert.equal(data.member, "scout");
    assert.equal(data.prompt, "any idea what this is");
    assert.equal(brain.calls.length, 0);
  });
});

test("follow-up with an image answers as the chosen member", async () => {
  const brain = makeFakeBrain();
  await withServer(brain, async (base) => {
    const res = await post(base, {
      memberId: "scout",
      text: "any idea what this is",
      imageBase64: "ZmFrZQ==",
    });
    const data = await res.json();
    assert.equal(data.status, "answer");
    assert.equal(data.member, "scout");
    assert.match(data.answer, /saw image/);
    assert.equal(brain.calls[0].imageBase64, "ZmFrZQ==");
    assert.equal(brain.calls[0].systemPrompt, "be scout");
  });
});

test("no name falls back to the default member", async () => {
  const brain = makeFakeBrain();
  await withServer(brain, async (base) => {
    const res = await post(base, { text: "what time is it" });
    const data = await res.json();
    assert.equal(data.status, "answer");
    assert.equal(data.member, "claude");
    assert.equal(brain.calls[0].bot, "claude");
  });
});

test("missing text is rejected", async () => {
  await withServer(makeFakeBrain(), async (base) => {
    const res = await post(base, {});
    assert.equal(res.status, 400);
  });
});
