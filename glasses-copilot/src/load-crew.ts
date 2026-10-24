/**
 * load-crew.ts — read the crew roster from JSON.
 * Order: $CREW_CONFIG, then ./config/crew.json, then ./config/crew.example.json.
 */

import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { validateCrew, type Crew } from "./crew.js";

const here = dirname(fileURLToPath(import.meta.url));

export function loadCrew(): Crew {
  const candidates = [
    process.env.CREW_CONFIG,
    resolve(here, "../config/crew.json"),
    resolve(here, "../config/crew.example.json"),
  ].filter((p): p is string => Boolean(p));

  for (const path of candidates) {
    if (existsSync(path)) {
      const crew = validateCrew(JSON.parse(readFileSync(path, "utf8")));
      console.log(`crew: loaded ${crew.members.length} members from ${path}`);
      return crew;
    }
  }
  throw new Error("No crew config found. Copy config/crew.example.json to config/crew.json.");
}
