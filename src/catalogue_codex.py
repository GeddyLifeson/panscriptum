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
    # `race variant` and `background variant` are real element types in the codex's Full
    # Contents manifests (28 and 7 occurrences). Unmapped, they fell through to the THINGS
    # default and a lineage was filed beside the magic items. Each takes its sibling's
    # category: a variant of a people is still a people, a variant of a background is still
    # the thing a background grants.
    "race": FACTIONS, "sub race": FACTIONS, "subrace": FACTIONS, "faction": FACTIONS,
    "race variant": FACTIONS, "background variant": POWERS,
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


# DEFERRED IMPORT, NOT A FOURTH COPY. catalogue_aurora imports THIS module at its own top level
# (`from catalogue_codex import TYPE_CATEGORY, THINGS`), so a module-level import of it here is a
# genuine circular import: importing catalogue_codex first would re-enter this file's body before
# TYPE_CATEGORY exists and raise ImportError. Importing inside the function is not a workaround
# for that -- by call time both modules are fully initialised -- and it keeps the count of slug
# implementations in this tree at ONE, which is the whole point. (The `import pipeline as _P`
# inside main() below is the same idiom.)
#
# What was here: `re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]`. The trailing `[:60]`
# breaks Hard Rule 0 on the record's IDENTITY -- 'Who Framed Roger Rabbit (incl. all content from
# its associated crossover-toon IPs)' slugs to 79 characters, the file on disk is 60, and a
# 304-entry record and its roll row are left with no path between them. Filed as order
# 683c59f43829 against catalogue_aurora.py; that record's `mode` is "web", so catalogue_web.py is
# the writer that produced it, and this module carried the identical cap.
def slug(s):
    """NOTHING IN THIS TREE CALLS THIS (order c158b93e2e07). Kept as a public helper;
    `record_path()` below is the entry point `main()` actually uses (see its own comment at
    :326-329ish). Say that first so a future sweep does not re-derive it: `grep -rn 'slug'
    src/catalogue_codex.py` finds this def and three comment mentions and no caller, and an
    AST walk of every `.py` file under `src/` for `X.slug(...)`, bare `slug(...)`, and
    `from catalogue_codex import slug` finds none either -- verified 2026-09-01, not assumed.

    The record's identity, derived from the source name. UNCAPPED -- see above."""
    from catalogue_aurora import slug as _slug
    return _slug(s)


def record_path(source_name, records_dir=RECORDS):
    """Where this source's record lives -- preferring the file that ALREADY EXISTS.

    Exact slug first, then the legacy 60-character prefix of the same slug (prefix-anchored by
    construction, so it cannot match an unrelated record the way free containment can), and only
    then a new uncapped path. Without this, dropping the cap would not have reunited a truncated
    record with its row -- it would have written a SECOND record beside it.
    """
    from catalogue_aurora import record_path as _record_path
    return _record_path(source_name, records_dir)


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
    """-> {norm(name): [item, ...]} -- EVERY item under a key, never just the first to arrive.

    THE SAME RULING AS THE SECTION PATH, APPLIED TO THE REGISTER PATH, WHICH NEVER GOT IT
    (order 096f6efc33d2). This built `{norm(name): item}` under `if key not in idx`, so the
    winner of a normalised collision was decided by FILE ORDER in LOCAL_REGISTER.json -- and the
    winner's `desc` is what the caller attaches to the codex element and writes into the record
    under attestation "Transcribed", beneath a provenance sentence saying the description was
    transcribed off the owner's shelf. Measured 2026-08-29 against
    reference/keystone_volumes/LOCAL_REGISTER.json: 14,576 items, 13,602 distinct norm() keys,
    885 colliding keys, 974 items silently dropped, and 700 of those groups carry DIFFERENT desc
    text. For those 700 element names the attested description was a coin flip.

    Forty lines below, the section path already argues why that is the one case where guessing is
    worse than doing nothing -- so the members come back whole and `main` decides: one desc (or
    several that agree) is used as before, disagreement falls back to the honest "no transcribed
    description on file" string and is reported uncapped for an operator to disambiguate."""
    with open(REGISTER, encoding="utf-8") as f:
        reg = json.load(f)
    idx = {}
    for item in reg:
        key = norm(item.get("name"))
        if key:
            idx.setdefault(key, []).append(item)
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sections = parse_codex()
    register = load_register_index()
    with open(ROLL, encoding="utf-8") as f:
        roll = json.load(f)

    # A NORMALISED TITLE COLLISION IS REPORTED, NOT DROPPED (order 5da00dda2c8e). `norm` keeps
    # only lowercased alphanumerics, so "The Ninth Gate" and "the-ninth-gate" normalise the same
    # and the dict comprehension that used to build this silently kept whichever came last -- one
    # of the owner's own codex sections would then be uncatalogable, and nothing said which.
    sec_by_norm = {}
    norm_clashes = {}
    for t in sections:
        k = norm(t)
        if k in sec_by_norm:
            norm_clashes.setdefault(k, [sec_by_norm[k]]).append(t)
            continue                      # keep the FIRST, so the report names what was refused
        sec_by_norm[k] = t
    if norm_clashes:
        # Uncapped: this is a list somebody reads to go and rename a section in the codex.
        print("  CODEX SECTION TITLES COLLIDE UNDER norm(): the first of each pair is the one "
              "bindable; the rest cannot be reached by any source name -- " +
              "; ".join("%s -> %s" % (k, " / ".join(repr(x) for x in v))
                        for k, v in sorted(norm_clashes.items())), flush=True)

    written = []
    # This run's roll rows, by source name -- the input to the compare-and-swap at the bottom.
    # See roll.mutate: landing the whole in-memory document is what loses another writer's row.
    # (order f818a77293fc)
    roll_changes = {}
    ambiguous = []      # (source_name, [candidate section titles]) -- bound to nothing on purpose
    reg_ambiguous = {}  # norm(element) -> [register spellings] -- desc left untranscribed
    for r in roll:
        if r.get("entry_count", 0) > 0:
            continue
        n = norm(r["name"])
        title = None
        # AN EXACT MATCH WINS OUTRIGHT. The substring scan below is bidirectional, so a short
        # source name can match whichever unrelated section happens to contain it. That is the
        # "Curse of Strahd pointed at the Roblox CURSE Wiki" shape this module's header already
        # names.
        if n and n in sec_by_norm:
            title = sec_by_norm[n]
        if not title and n:
            # AND AN AMBIGUOUS SUBSTRING MATCH BINDS NOTHING (order 5da00dda2c8e). This scan used
            # to `break` on the first hit in codex-FILE order, which is not a ranking of anything
            # -- it is the order the owner happened to write the sections in. The exact-match
            # preference above does nothing for the case the comment describes, because the whole
            # hazard is a source name that matches NO section exactly and two loosely. The chosen
            # title is then used for sections[title], for every entry's `codex_section`, and for
            # the provenance sentence "section '<title>' -- the owner's own authored document",
            # written under attestation "Transcribed". Attesting to a transcription from the
            # wrong section is worse than not cataloguing the source at all, and it is the one
            # case where guessing is worse than doing nothing -- so all candidates are collected
            # and more than one is a refusal that gets reported, not a coin flip that gets
            # attested.
            cands = sorted({t for k, t in sec_by_norm.items() if n in k or k in n})
            if len(cands) == 1:
                title = cands[0]
            elif len(cands) > 1:
                ambiguous.append((r["name"], cands))
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
            hits = register.get(key) or []
            # Prefer the register's transcribed text; fall back to naming the type and the
            # source honestly rather than inventing a description.
            #
            # WHERE THE MEMBERS OF A norm() COLLISION DISAGREE, NOTHING IS ATTESTED. Members that
            # agree collapse harmlessly and stay silent -- the same text arriving twice is not an
            # ambiguity. Members with different desc text are two answers to "what is this
            # element", and picking one would write it into the corpus as transcribed evidence.
            # (order 096f6efc33d2; see load_register_index.)
            descs = sorted({(h.get("desc") or "").strip() for h in hits} - {""})
            desc = descs[0] if len(descs) == 1 else ""
            if len(descs) > 1:
                reg_ambiguous.setdefault(
                    key, sorted({(h.get("name") or "") for h in hits}))
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

    if ambiguous:
        # Uncapped, and printed before the write report so it is not buried under it. A source
        # named here was NOT catalogued; the operator either renames it to match a section
        # exactly or renames the section.
        print("  AMBIGUOUS SECTION BINDING -- %d source(s) matched more than one codex section "
              "by substring and were SKIPPED rather than attested to a guess:" % len(ambiguous))
        for nm, cands in ambiguous:
            print("      %s -> %s" % (nm, " / ".join(repr(c) for c in cands)))
        print("", flush=True)

    if reg_ambiguous:
        # Uncapped, and before the write report for the same reason the section list is: this is
        # a list somebody reads to go and disambiguate LOCAL_REGISTER.json. Every element named
        # here was still catalogued -- only its DESCRIPTION was left untranscribed, because two
        # register rows normalise to one key and say different things.
        print("  AMBIGUOUS REGISTER DESCRIPTION -- %d element key(s) collide under norm() with "
              "DIFFERING desc text, so no description was transcribed for them (the entries are "
              "written; the description falls back to the honest 'none on file' form):"
              % len(reg_ambiguous))
        for k, names in sorted(reg_ambiguous.items()):
            print("      %s -> %s" % (k, " / ".join(repr(x) for x in names)))
        print("", flush=True)

    denied = []
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
            # `record_path`, not a raw join on slug(): with the cap gone, the join would miss a
            # record written under it and write a second one beside the first -- the roll counting
            # one source and the corpus holding two.
            if not _P.write_record_catalogue(record_path(r["name"], RECORDS), rec):
                print(f"      -> WRITE DENIED {r['name']}; roll left untouched", flush=True)
                # AND IT REACHES THE PROCESS BOUNDARY (order 0e8ef2e30f2b). This verdict was
                # honoured in prose and thrown away as a return code, so a supervisor or wrapper
                # checking rc saw a clean run.
                denied.append(r["name"])
                continue
            # NOT `r["entry_count"] = ...` / `r["status"] = ...` any more (order 09f3105df988).
            # `r` is a row of the in-memory `roll` list read once at the top of this function;
            # since the compare-and-swap migration (order f818a77293fc) persistence goes
            # exclusively through `roll_changes` against a FRESHLY-READ roll below, so mutating
            # `r` was a leftover of the whole-document write this function used to do and was
            # never read again -- it made the in-memory roll look like it was still the thing
            # being persisted, which is exactly the misreading that migration was filed to end.
            roll_changes[r["name"]] = {"entry_count": len(rec["entries"]),
                                       "status": "catalogued"}

    roll_landed = True
    if not args.dry_run and written:
        # ATOMIC: `catalogue_web.save_roll()` already wrote this file atomically with a comment
        # warning an interrupted write here "kills the next run of either script outright";
        # this sibling did not. Fixed 2026-08-25. SEVEN scripts write this roll, not four --
        # the count in that older note was already stale when it was written (order
        # f818a77293fc), and atomicity was never the property it needed anyway; see below.
        #
        # GATED, exactly as `catalogue_aurora.py` was: the per-record write eleven lines above
        # already honours its verdict and skips the roll row on denial, and then this -- the
        # write that PERSISTS those roll rows -- threw its own verdict away. So the records
        # really did land, the roll saying so did not, and the next run's `entry_count == 0`
        # selection would re-parse sources already correctly catalogued. Run #36 sweep.
        #
        # AND A COMPARE-AND-SWAP, NOT A WHOLE-DOCUMENT LAND (order f818a77293fc). Atomic closed
        # the torn-file hazard and says nothing about staleness: this function reads the roll
        # once, works through every section of the codex, and used to write its own hours-old
        # copy of every OTHER writer's rows back over them. `roll.update_rows` merges only the
        # rows this run actually catalogued into a freshly-read roll.
        import roll as _roll
        roll_landed, roll_why = _roll.update_rows(roll_changes, path=ROLL)
        if not roll_landed:
            silence.note("catalogue_codex.py:roll-write-denied")
        if roll_why:
            print("  ROLL: %s" % roll_why, flush=True)
    if args.dry_run:
        print("\n(dry run -- nothing written)")
    elif not roll_landed:
        print("\n(WRITE DENIED: SWEEP_ROLL.json did not land; the records above were written "
              "to disk but the roll does not yet say so -- rerun to retry)")

    # THE VERDICTS REACH THE EXIT CODE (order 0e8ef2e30f2b). Both write failures in this script
    # were captured correctly and neither left the process: main() returned None and the guard
    # below called it bare, so a denied SWEEP_ROLL.json write -- the one whose own comment says
    # the records land, the roll saying so does not, and the next run re-parses sources already
    # catalogued -- exited 0 and read as a clean run to anything checking rc. `module_index.py`
    # in the same tree gets this right and is the shape copied here: return 1 on a denied write,
    # `sys.exit(main())` at the bottom. Ambiguous section bindings do NOT set rc: nothing failed
    # to write, the module deliberately declined to guess, and a re-run will decline identically
    # -- that is a curatorial item for the report, not a run failure for a supervisor to retry.
    if denied or not roll_landed:
        sys.stderr.write(
            "catalogue_codex: %d record write(s) denied%s%s\n"
            % (len(denied),
               "" if not denied else " (%s)" % ", ".join(denied),
               "" if roll_landed else "; SWEEP_ROLL.json write also denied"))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
