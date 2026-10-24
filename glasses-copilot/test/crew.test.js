import test from "node:test";
import assert from "node:assert/strict";
import { routeToCrew, validateCrew } from "../dist/crew.js";

const CREW = {
  defaultMemberId: "claude",
  members: [
    { id: "claude", name: "Claude", provider: "claude", greeting: "Claude here." },
    { id: "scout", name: "Scout", provider: "grok", greeting: "Scout, eyes on." },
    { id: "ledger", name: "Ledger", aliases: ["Cato", "Cato Ledger"], provider: "grok", greeting: "Ledger here." },
  ],
};

test("summoning by name strips the name and keeps the task", () => {
  const r = routeToCrew("Scout, what's the plan", CREW);
  assert.equal(r.member.id, "scout");
  assert.equal(r.prompt, "what's the plan");
  assert.equal(r.summoned, true);
  assert.equal(r.hasPrompt, true);
});

test("bare summon has no prompt (so the app plays the greeting)", () => {
  const r = routeToCrew("hey Scout", CREW);
  assert.equal(r.member.id, "scout");
  assert.equal(r.summoned, true);
  assert.equal(r.hasPrompt, false);
});

test("aliases resolve to the same member", () => {
  assert.equal(routeToCrew("Cato, run the numbers", CREW).member.id, "ledger");
  assert.equal(routeToCrew("Cato Ledger run the numbers", CREW).member.id, "ledger");
});

test("no name falls back to the default member", () => {
  const r = routeToCrew("what time is it", CREW);
  assert.equal(r.member.id, "claude");
  assert.equal(r.summoned, false);
});

test("vision is detected on the stripped prompt", () => {
  const r = routeToCrew("Scout any idea what this is", CREW);
  assert.equal(r.member.id, "scout");
  assert.equal(r.wantsVision, true);
});

test("validateCrew rejects a bad provider", () => {
  assert.throws(() =>
    validateCrew({ defaultMemberId: "x", members: [{ id: "x", name: "X", greeting: "hi", provider: "gemini" }] })
  );
});

test("validateCrew rejects a default that matches no member", () => {
  assert.throws(() =>
    validateCrew({ defaultMemberId: "nope", members: [{ id: "x", name: "X", greeting: "hi", provider: "grok" }] })
  );
});
