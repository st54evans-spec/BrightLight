import test from "node:test";
import assert from "node:assert/strict";
import { route } from "../dist/router.js";

test("defaults to the configured bot when none is named", () => {
  const r = route("what's the weather like", "claude");
  assert.equal(r.bot, "claude");
  assert.equal(r.wantsVision, false);
  assert.equal(r.prompt, "what's the weather like");
});

test("routes to Grok when addressed and strips the address", () => {
  const r = route("hey Grok, summarize this email", "claude");
  assert.equal(r.bot, "grok");
  assert.equal(r.prompt, "summarize this email");
});

test("routes to Claude when addressed", () => {
  const r = route("Claude: how do I say hello in Japanese", "grok");
  assert.equal(r.bot, "claude");
  assert.equal(r.prompt, "how do I say hello in Japanese");
});

test("detects a visual question so a frame is captured", () => {
  for (const q of [
    "any idea what this is?",
    "what am I looking at",
    "what do you see",
    "read this for me",
    "describe that building",
  ]) {
    assert.equal(route(q, "claude").wantsVision, true, q);
  }
});

test("non-visual questions do not trigger the camera", () => {
  for (const q of [
    "what time is it",
    "remind me to call mom",
    "what's 20 percent of 85",
  ]) {
    assert.equal(route(q, "claude").wantsVision, false, q);
  }
});

test("bot address and vision detection combine", () => {
  const r = route("ask grok any idea what that is", "claude");
  assert.equal(r.bot, "grok");
  assert.equal(r.wantsVision, true);
  assert.equal(r.prompt, "any idea what that is");
});
