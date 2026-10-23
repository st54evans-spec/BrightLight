import test from "node:test";
import assert from "node:assert/strict";
import { createAskServer } from "../dist/server.js";

// Fake brain: records calls, returns a canned answer. No network.
function makeFakeBrain() {
  const calls = [];
  return {
    calls,
    ask(bot, text, opts = {}) {
      calls.push({ bot, text, imageBase64: opts.imageBase64 });
      return Promise.resolve(`[${bot}] ${text}${opts.imageBase64 ? " (saw image)" : ""}`);
    },
  };
}

async function withServer(brain, fn) {
  const server = createAskServer(brain, { defaultBot: "claude" });
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

test("non-visual question is answered directly", async () => {
  const brain = makeFakeBrain();
  await withServer(brain, async (base) => {
    const res = await post(base, { text: "what's 20 percent of 85" });
    const data = await res.json();
    assert.equal(data.status, "answer");
    assert.equal(data.bot, "claude");
    assert.equal(brain.calls.length, 1);
    assert.equal(brain.calls[0].imageBase64, undefined);
  });
});

test("visual question without a frame asks for an image first", async () => {
  const brain = makeFakeBrain();
  await withServer(brain, async (base) => {
    const res = await post(base, { text: "ask grok any idea what this is" });
    const data = await res.json();
    assert.equal(data.status, "need_image");
    assert.equal(data.bot, "grok");
    assert.equal(data.prompt, "any idea what this is");
    assert.equal(brain.calls.length, 0, "should not call the model yet");
  });
});

test("follow-up with an image answers using the frame", async () => {
  const brain = makeFakeBrain();
  await withServer(brain, async (base) => {
    const res = await post(base, {
      bot: "grok",
      text: "any idea what this is",
      imageBase64: "ZmFrZQ==",
    });
    const data = await res.json();
    assert.equal(data.status, "answer");
    assert.equal(data.bot, "grok");
    assert.match(data.answer, /saw image/);
    assert.equal(brain.calls[0].imageBase64, "ZmFrZQ==");
  });
});

test("missing text is rejected", async () => {
  await withServer(makeFakeBrain(), async (base) => {
    const res = await post(base, {});
    assert.equal(res.status, 400);
  });
});
