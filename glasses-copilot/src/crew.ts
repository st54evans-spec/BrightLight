/**
 * crew.ts — your "crew" of named assistants, modeled on finance/persona.js:
 * each member has a name you call out, its own spoken greeting, its own persona
 * (system prompt), and a backend (Claude or one of your Grok bots).
 *
 * "Scout, any idea what this is" -> Scout greets in its voice, then answers.
 */

import { detectVision } from "./router.js";
import type { Bot } from "./brain.js";

export type Provider = Bot; // "claude" | "grok"

export interface CrewMember {
  /** Stable key used by the app when sending a follow-up. */
  id: string;
  /** Spoken name you summon it with. */
  name: string;
  /** Alternate spoken forms ("Cato", "Cato Ledger"). */
  aliases?: string[];
  provider: Provider;
  /** Spoken when you summon this member. */
  greeting: string;
  /** Persona + instructions (its "voice"). */
  systemPrompt?: string;
}

export interface Crew {
  members: CrewMember[];
  /** Member used when you don't call anyone by name. */
  defaultMemberId: string;
}

export interface CrewRoute {
  member: CrewMember;
  /** Transcript with the member's name stripped from the front. */
  prompt: string;
  wantsVision: boolean;
  /** A crew member was named explicitly. */
  summoned: boolean;
  /** There is an actual task after the name (vs. a bare "Hey Scout"). */
  hasPrompt: boolean;
}

export function findMember(crew: Crew, id: string): CrewMember {
  const m = crew.members.find((x) => x.id === id);
  if (!m) throw new Error(`Unknown crew member: ${id}`);
  return m;
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function routeToCrew(text: string, crew: Crew): CrewRoute {
  const trimmed = text.trim();

  for (const member of crew.members) {
    for (const name of [member.name, ...(member.aliases ?? [])]) {
      const re = new RegExp(
        `^\\s*(?:hey\\s+|ok\\s+|ask\\s+|yo\\s+)?${escapeRegex(name)}\\b[\\s,:.\\-]*`,
        "i"
      );
      if (re.test(trimmed)) {
        const prompt = trimmed.replace(re, "").trim();
        return {
          member,
          prompt,
          wantsVision: detectVision(prompt),
          summoned: true,
          hasPrompt: prompt.length > 0,
        };
      }
    }
  }

  const member = findMember(crew, crew.defaultMemberId);
  return {
    member,
    prompt: trimmed,
    wantsVision: detectVision(trimmed),
    summoned: false,
    hasPrompt: trimmed.length > 0,
  };
}

/** Validate a parsed crew config (from JSON). Throws on problems. */
export function validateCrew(data: unknown): Crew {
  if (!data || typeof data !== "object") throw new Error("crew config must be an object");
  const c = data as Partial<Crew>;
  if (!Array.isArray(c.members) || c.members.length === 0) {
    throw new Error("crew config needs a non-empty members array");
  }
  for (const m of c.members) {
    if (!m.id || !m.name || !m.greeting) {
      throw new Error("each crew member needs id, name, and greeting");
    }
    if (m.provider !== "claude" && m.provider !== "grok") {
      throw new Error(`member ${m.id}: provider must be "claude" or "grok"`);
    }
  }
  if (!c.defaultMemberId || !c.members.some((m) => m.id === c.defaultMemberId)) {
    throw new Error("defaultMemberId must match a member id");
  }
  return c as Crew;
}
