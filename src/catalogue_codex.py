#!/usr/bin/env python3
"""
Catalogues the owner's own homebrew sources from THE_PRIME_OMNIVERSE_CODEX.md.

The wiki cataloguer (src/catalogue_web.py) cannot touch these, and correctly refuses to try:
"Dr. Firestorm's Engineering Corps", "Draconic Cult Relics", "Native Combat Traditions" and
their kin exist nowhere on the internet because the owner wrote them. Guessing a wiki for them
is how "Curse of Strahd" ended up pointed at the Roblox CURSE Wiki.

Their real source is the owner's own codex at
    C:/Users/imarl/Documents/5e Character Builder/custom/THE_PRIME_OMNIVERSE_CODEX.md
whose Part Two (The Grand Compendium) gives each source a written description AND a structured
manifest:

    ### Dr. Firestorm's Engineering Corps
    <narrative paragraph>
    Full Contents:
      Class (2): Engineer; Esper Variant
      Archetype (7): Alchemist; Battletech; ...
      Magic Item (41): Appendage Retractable Machine (A.R.M.); ...

Element names come from that manifest. Per-element descriptions are joined from
LOCAL_REGISTER.json where the same element was transcribed off the owner's shelf, so most
entries carry real text rather than a restatement of the section blurb.

Attestation is **Transcribed**: this is the owner's own material, read from the owner's own
files. No model generated any of it.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence                                                          # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLL = os.path.join(HERE, "data/SWEEP_ROLL.json")
RECORDS = os.path.join(HERE, "data/records")
CODEX = r"C:\Users\imarl\Documents\5e Character Builder\custom\THE_PRIME_OMNIVERSE_CODEX.md"
REGISTER = os.path.join(HERE, "reference/keystone_volumes/LOCAL_REGISTER.json")

PERSONS = "Persons (named individual characters, real or fictional)"
PLACES = "Places & Locations (worlds, regions, cities, planes, ships-as-places)"
THINGS = "Vessels & Things (items, vehicles, weapons, artifacts, notable objects)"
FACTIONS = "Factions & Organizations (groups, nations, guilds, companies, orders)"
POWERS = "Powers, Abilities & Systems (magic systems, power systems, tech systems, disciplines)"
EVENTS = "Events (major storyline events, wars, historical turning points within the fiction)"
MEDIA = "Media (in-fiction media: books, songs, broadcasts, works that exist within the story itself)"

# Element type -> canonical catalogue category. A Race is a people, so it files under
# Factions & Organizations rather than Persons, which is reserved for named individuals.
TYPE_CATEGORY = {
    "magic item": THINGS, "item": THINGS, "weapon": THINGS, "armor": THINGS,
    "equipment": THINGS, "vehicle": THINGS, "gadget": THINGS,
    "race": FACTIONS, "sub race": FACTIONS, "subrace": FACTIONS, "faction": FACTIONS,
    "deity": PERSONS, "companion": PERSONS, "character": PERSONS, "npc": PERSONS,
    "location": PLACES, "place": PLACES, "plane": PLACES,
    "class": POWERS, "archetype": POWERS, "feat": POWERS, "spell": POWERS,
    "background": POWERS, "class feature": POWERS, "archetype feature": POWERS,
    "racial trait": POWERS, "proficiency": POWERS, "language": POWERS,
    "feat feature": POWERS, "companion trait": POWERS, "background feature": POWERS,
    "dragonmark": POWERS, "magic school": POWERS, "rule": POWERS, "option": POWERS,
    "grants": POWERS, "support": POWERS, "condition": POWERS, "level": POWERS,
    "ability score improvement": POWERS, "information": MEDIA, "source": MEDIA,
}


def norm(s):
    return "".join(c for c in (s or "").lower() if c.isalnum())


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def parse_codex():
    """-> {section_title: {"blurb": str, "contents": [(type, name), ...]}}"""
    with open(CODEX, encoding="utf-8") as f:
        text = f.read()
    part2 = text[text.index("## PART TWO"):]
    blocks = re.split(r"^###+\s*#*\s*", part2, flags=re.M)[1:]
    out = {}
    for b in blocks:
        lines = b.splitlines()
        if not lines:
            continue
        title = lines[0].strip()
        body = "\n".join(lines[1:])
        blurb = body.split("Full Contents:")[0].strip()
        blurb = re.sub(r"\s+", " ", blurb)
        contents = []
        for m in re.finditer(r"^\s{2,}(.+?)\s*\((\d+)\):\s*(.+?)$", body, re.M):
            etype = m.group(1).strip()
            for name in m.group(3).split(";"):
                name = name.strip()
                if name:
                    contents.append((etype, name))
        out[title] = {"blurb": blurb, "contents": contents}
    return out


def load_register_index():
    with open(REGISTER, encoding="utf-8") as f:
        reg = json.load(f)
    idx = {}
    for item in reg:
        key = norm(item.get("name"))
        if key and key not in idx:
            idx[key] = item
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sections = parse_codex()
    register = load_register_index()
    with open(ROLL, encoding="utf-8") as f:
        roll = json.load(f)

    sec_by_norm = {norm(t): t for t in sections}
    written = []
    for r in roll:
        if r.get("entry_count", 0) > 0:
            continue
        n = norm(r["name"])
        title = None
        for k, t in sec_by_norm.items():
            if n and (n in k or k in n):
                title = t
                break
        if not title:
            continue

        sec = sections[title]
        entries = []
        seen = set()
        for etype, name in sec["contents"]:
            key = norm(name)
            if not key or key in seen:
                continue
            seen.add(key)
            hit = register.get(key)
            # Prefer the register's transcribed text; fall back to naming the type and the
            # source honestly rather than inventing a description.
            desc = (hit or {}).get("desc") or ""
            if not desc:
                desc = (f"{etype} from {title}. No transcribed description on file in the "
                        f"Local Register; see the source material for full text.")
            entries.append({
                "name": name,
                "type": etype,
                "description": desc,
                "scale_note": "",
                "category": TYPE_CATEGORY.get(etype.lower(), THINGS),
                "codex_section": title,
            })

        if not entries:
            continue

        record = {
            "source": r["name"],
            "category": r.get("category"),
            "mode": "folder-mechanical",
            "entries": entries,
            "synthesis": None,
            "status": "catalogued",
            "attestation": "Transcribed",
            "section_blurb": sec["blurb"],
            "provenance": (
                f"Transcribed from THE_PRIME_OMNIVERSE_CODEX.md, Part Two (The Grand "
                f"Compendium), section '{title}' -- the owner's own authored document. "
                f"Element names come from that section's 'Full Contents' manifest; "
                f"descriptions are joined from LOCAL_REGISTER.json where the same element was "
                f"transcribed off the owner's shelf. No model generated any of this content. "
                f"scale_note and synthesis left empty: Assay values need Part Three's "
                f"worksheet method."
            ),
        }
        written.append((r, record))

    verb = "Would write" if args.dry_run else "Wrote"
    print(f"{verb} {len(written)} records from the codex:\n")
    for r, rec in sorted(written, key=lambda x: -len(x[1]["entries"])):
        joined = sum(1 for e in rec["entries"] if not e["description"].startswith(e["type"]))
        print(f"  {len(rec['entries']):5d} entries ({joined} with register text)  {r['name']}")
        if not args.dry_run:
            import pipeline as _P
            # GATE ON THE WRITE -- same fix, same reason as catalogue_aurora.py and
            # catalogue_web.py: a roll row marked `catalogued` for a write that never landed is
            # never revisited, because the default work selection is `entry_count == 0`.
            # (run #25)
            if not _P.write_record_catalogue(
                    os.path.join(RECORDS, slug(r["name"]) + ".json"), rec):
                print(f"      -> WRITE DENIED {r['name']}; roll left untouched", flush=True)
                continue
            r["entry_count"] = len(rec["entries"])
            r["status"] = "catalogued"

    if not args.dry_run and written:
        # ATOMIC: `catalogue_web.save_roll()` already wrote this file atomically with a comment
        # warning an interrupted write here "kills the next run of either script outright";
        # this sibling did not. Four scripts write this roll. Fixed 2026-08-25.
        silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)
    if args.dry_run:
        print("\n(dry run -- nothing written)")


if __name__ == "__main__":
    main()
