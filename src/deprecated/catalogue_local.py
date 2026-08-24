#!/usr/bin/env python3
"""
Catalogues the roll's remaining sources using the local Ollama model.

READ THIS BEFORE TRUSTING ANYTHING IT PRODUCES
----------------------------------------------
The cloud session catalogued its sources with real research -- it could reach the web and
check itself. This script cannot. It runs against a local model with no network access, so
every entry it writes comes from the model's own memory. For a widely-documented franchise
that is often broadly right; it is also, reliably, partly wrong, and nothing on this machine
can tell the difference.

That is why every record this writes is stamped:

    "attestation": "Reconstructed"
    "provenance" : "Local model recall, no external verification..."

*Reconstructed* is the charter's own Attestation grade for **guessed** (Vade Mecum §II.4,
the ladder Witnessed -> Instrumented -> Transcribed -> Reconstructed -> Disputed). It sits
below *Transcribed*. The library already has the vocabulary for material of this confidence,
so the honest move is to use it rather than let model recall masquerade as research.

Practical consequence: these records are a scaffold so the entanglement/grand-history pass has
a complete omniverse to work against. They are NOT equivalent to the cloud session's 129
researched sources, and they should be re-swept and promoted when real research is available.
`generate.py` keys its cache on a content hash of the source data, so re-sweeping a source
later correctly invalidates anything built from the placeholder version.

Usage:
    python3 src/catalogue_local.py --dry-run          # show the plan, call nothing
    python3 src/catalogue_local.py --limit 3          # catalogue 3 sources then stop
    python3 src/catalogue_local.py                    # catalogue every remaining source
    python3 src/catalogue_local.py --only "Bleach"
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))

import yaml  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLL = os.path.join(HERE, "data/SWEEP_ROLL.json")
RECORDS = os.path.join(HERE, "data/records")

# The exact labels the cloud session used. Chapter labels in the manifest are derived straight
# from these strings, so drifting from them would fragment chapters across the library.
CATEGORIES = [
    "Persons (named individual characters, real or fictional)",
    "Places & Locations (worlds, regions, cities, planes, ships-as-places)",
    "Vessels & Things (items, vehicles, weapons, artifacts, notable objects)",
    "Factions & Organizations (groups, nations, guilds, companies, orders)",
    "Powers, Abilities & Systems (magic systems, power systems, tech systems, disciplines)",
    "Events (major storyline events, wars, historical turning points within the fiction)",
    "Media (in-fiction media: books, songs, broadcasts, works that exist within the story itself)",
]

ENTRY_SCHEMA = {
    "type": "object",
    "properties": {
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "description": {"type": "string"},
                    "scale_note": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["name", "type", "description", "confidence"],
            },
        }
    },
    "required": ["entries"],
}

SYSTEM = """You are cataloguing a fictional source for an encyclopedia. You produce structured
factual records, not prose.

ABSOLUTE RULES:
1. Only list entities you actually recognise from this specific source. An empty list is a
   correct answer. A short accurate list is far more valuable than a long invented one.
2. Never pad toward a target count. If you know six characters from this work, return six.
3. Mark `confidence` honestly per entry: "high" if you are certain this entity belongs to this
   source, "medium" if fairly sure, "low" if you are reaching. Do not mark everything high.
4. Do not merge in entities from other franchises that merely feel similar.
5. `description` is one or two factual sentences. No rhetoric, no speculation about
   significance, no "arguably" or "perhaps".
6. `scale_note` records demonstrated power/scale ONLY where the source actually shows it
   (feats, destruction, reach). Leave it empty otherwise. Never estimate a power level.
7. `type` is a short noun phrase describing what the entity is, e.g. "Character (Shinobi,
   Protagonist)", "City", "Magic Item", "Military Order".
8. STAY IN THE REQUESTED CATEGORY. The commonest failure is filing an ability as an object.
   A named technique, transformation, release state or process (e.g. a power-up form, a
   "-ification" process, a combat art) is a POWER/SYSTEM, never a Vessel or Thing. Vessels &
   Things means physical objects you could drop: a sword, a ship, a badge, an amulet.
9. NO NEAR-DUPLICATES. Do not list the same entity twice under two spellings or with a
   parenthetical alias appended ("Soul Reaper Badge" and "Soul Reaper Badge (Shinigami
   Badge)" are one entry, not two). Pick the name the source most commonly uses.
10. If you are unsure of an entity's real name, LEAVE IT OUT. A confidently wrong name is the
   worst possible output here, because nothing downstream can detect it -- writing "Chad
   (Seraura Urahara)" when the character is Yasutora Sado poisons every entry that follows.
   Omission is recoverable; fabrication is not.
"""

USER = """SOURCE: {source}
CATEGORY: {category}

List the entities from this source that belong in this category.

{guidance}

Return JSON: {{"entries": [{{"name", "type", "description", "scale_note", "confidence"}}]}}
Only entities you genuinely recognise from {source}. An empty list is acceptable and correct
if this source has nothing in this category."""

GUIDANCE = {
    "Persons": "Named individual characters. Protagonists, antagonists, supporting cast, "
               "historical figures within the fiction.",
    "Places": "Worlds, regions, cities, buildings, planes of existence, and ships treated as "
              "places.",
    "Vessels": "Items, vehicles, weapons, artifacts and notable objects.",
    "Factions": "Groups, nations, guilds, companies, military orders, criminal organisations.",
    "Powers": "Named magic systems, power systems, technologies and disciplines - the SYSTEM "
              "itself, not individuals who use it.",
    "Events": "Major storyline events, wars, and historical turning points inside the fiction.",
    "Media": "Works that exist INSIDE the story - in-fiction books, songs, broadcasts, films. "
             "Not the source work itself. Most sources have none; return an empty list then.",
}


def load_cfg():
    with open(os.path.join(HERE, "config.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def call(cfg, system, prompt, schema):
    body = json.dumps({
        "model": cfg["model"],
        "system": system,
        "prompt": prompt,
        "stream": False,
        "format": schema,
        "options": {"seed": cfg.get("seed", 47), "temperature": 0.1,
                    "num_ctx": cfg.get("num_ctx", 12288)},
    }).encode()
    req = urllib.request.Request(cfg["ollama_host"].rstrip("/") + "/api/generate",
                                 data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=cfg.get("request_timeout", 1800)) as r:
        return json.loads(json.loads(r.read().decode()).get("response", "{}"))


def catalogue_source(cfg, roll_entry, verbose=True):
    name = roll_entry["name"]
    entries, per_cat = [], {}
    seen = set()
    for cat in CATEGORIES:
        key = cat.split(" ")[0].rstrip("s,")
        guidance = next((v for k, v in GUIDANCE.items() if cat.startswith(k)), "")
        try:
            got = call(cfg, SYSTEM, USER.format(source=name, category=cat, guidance=guidance),
                       ENTRY_SCHEMA)
        except Exception as e:
            if verbose:
                print(f"      {key:9s} FAILED: {str(e)[:70]}")
            per_cat[key] = 0
            continue
        n = 0
        for e in got.get("entries", []):
            nm = (e.get("name") or "").strip()
            if not nm:
                continue
            # Mechanical de-duplication. Rule 9 in the system prompt asks the model not to
            # emit near-duplicates and it does anyway -- an observed pilot returned both
            # "Shinigami Badge" and "Soul Reaper Badge (Shinigami Badge)" in the same call.
            # Collapse on the name with any parenthetical alias stripped and non-alphanumerics
            # removed, so the two forms above resolve to one entry. First spelling wins.
            base = re.sub(r"\([^)]*\)", "", nm)
            key_norm = re.sub(r"[^a-z0-9]", "", base.lower())
            if not key_norm or key_norm in seen:
                continue
            seen.add(key_norm)
            entries.append({
                "name": nm,
                "type": (e.get("type") or "").strip(),
                "description": (e.get("description") or "").strip(),
                "scale_note": (e.get("scale_note") or "").strip(),
                "category": cat,
                "confidence": e.get("confidence", "low"),
            })
            n += 1
        per_cat[key] = n
        if verbose:
            print(f"      {key:9s} {n:4d}")
    return entries, per_cat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--only", type=str, default=None)
    args = ap.parse_args()

    cfg = load_cfg()
    with open(ROLL, encoding="utf-8") as f:
        roll = json.load(f)

    todo = [r for r in roll if r.get("entry_count", 0) == 0]
    if args.only:
        wanted = {n.strip().lower() for n in args.only.split(",")}
        todo = [r for r in todo if r["name"].lower() in wanted]
    if args.limit:
        todo = todo[: args.limit]

    print(f"{len(todo)} sources to catalogue with {cfg['model']}")
    print("Every record written will be stamped Attestation: Reconstructed "
          "(the charter's grade for guessed).\n")
    if args.dry_run:
        for r in todo:
            print(f"  {r['name']}  [{r.get('category')}, mode={r.get('mode')}]")
        print("\n(dry run -- Ollama was not called)")
        return

    roll_by_name = {r["name"]: r for r in roll}
    done = 0
    for i, r in enumerate(todo, 1):
        name = r["name"]
        print(f"[{i}/{len(todo)}] {name}")
        t0 = time.time()
        entries, per_cat = catalogue_source(cfg, r)
        if not entries:
            print("      -> nothing recognised, leaving uncatalogued\n")
            continue

        record = {
            "source": name,
            "category": r.get("category"),
            "mode": r.get("mode", "web"),
            "entries": entries,
            "synthesis": None,
            "status": "catalogued",
            "attestation": "Reconstructed",
            "provenance": (
                "Local model recall, no external verification. Produced by "
                f"src/catalogue_local.py using {cfg['model']} with no network access. "
                "Attestation grade Reconstructed per Vade Mecum II.4 -- this is guessed "
                "material, below Transcribed, and must be re-swept against real research "
                "before it is treated as equivalent to the cloud session's records."
            ),
        }
        with open(os.path.join(RECORDS, slug(name) + ".json"), "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)

        roll_by_name[name]["entry_count"] = len(entries)
        roll_by_name[name]["status"] = "catalogued-reconstructed"
        with open(ROLL, "w", encoding="utf-8") as f:
            json.dump(roll, f, indent=2, ensure_ascii=False)

        done += 1
        hi = sum(1 for e in entries if e["confidence"] == "high")
        print(f"      -> {len(entries)} entries ({hi} high-confidence) in "
              f"{time.time()-t0:.0f}s\n")

    print(f"Catalogued {done}/{len(todo)} sources.")


if __name__ == "__main__":
    main()
