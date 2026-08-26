#!/usr/bin/env python3
"""
Rebuilds the missing folder-mode records from data the cloud session already gathered.

Why this exists
---------------
100 of the 215 sources on the Acquisitions Roll show `entry_count: 0` -- a cloud session hit
a limit mid-sweep and those records were never written (77 have no record file at all; 23 have
a file containing an empty `entries` list). Every one of them is nonetheless flagged
`status: "catalogued"` on the roll, which is why the gap is easy to miss.

For a subset of them the research is NOT actually missing. It is sitting in the kit in a
different shape:

  * reference/keystone_volumes/LOCAL_REGISTER.json  -- 14,576 items transcribed off the
    owner's own shelf, each tagged with the real source book it came from.
  * reference/pipeline_tooling/FOLDER_SOURCE_MAP.json -- the cloud session's OWN mapping from
    roll source name -> the register `source` strings that belong to it, with counts. This is
    curatorial work it already did; we follow it rather than re-deriving it with fuzzy name
    matching, which produces false hits like "Doom" -> "Deep Magic: Blood & Doom".

So this script is a transcription, not a generation step. It moves real, already-researched
entries into the record schema `manifest_builder.py` expects. Nothing here invents content,
and no model is involved.

What it deliberately does NOT do
--------------------------------
The remaining sources -- the web-mode ones like Bleach, Baki, Crash Bandicoot -- have no local
data in any form. They cannot be recovered here, by this script or by a local model, because
the facts simply are not on this machine. Generating them from a model's own memory would
breach Hard Rule 1 and is the one failure mode this whole pipeline exists to prevent.

Usage:
    python3 src/recover_folder_records.py --dry-run   # report what would be written
    python3 src/recover_folder_records.py             # write records + update SWEEP_ROLL.json
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

import silence                                                          # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REGISTER = os.path.join(HERE, "reference/keystone_volumes/LOCAL_REGISTER.json")
SOURCE_MAP = os.path.join(HERE, "reference/pipeline_tooling/FOLDER_SOURCE_MAP.json")
ROLL = os.path.join(HERE, "data/SWEEP_ROLL.json")
RECORDS = os.path.join(HERE, "data/records")

# Matches ingest.py's slug(), so recovered files land where the cloud session would have put
# them. load_record() in manifest_builder.py matches on alphanumerics-only containment, so the
# exact punctuation does not matter -- but consistency does, for anyone reading the folder.
def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower())
    return s.strip("-")[:60]


# Register `source` strings that must never be transcribed, however the map points at them.
#
# "ME" is the cloud session's unresolved bucket, not a book. FOLDER_SOURCE_MAP.json points
# SEVEN unrelated roll sources at it -- Walrock Homebrew, The Elements Beyond, Mordenkainen's
# Tome of Foes, Prime World Equipment, Rime of the Frostmaiden, swordmeow's Atavist, and
# Unearthed Arcana -- and its 7 items are all "Trickster" archetype features belonging to none
# of them. Following that mapping would file the same 7 wrong entries under several different
# books and attest them as researched. Every other mapping in the file has real name
# correspondence and is followed as written.
EXCLUDED_REGISTER_SOURCES = {"ME"}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    register = load(REGISTER)
    source_map = load(SOURCE_MAP)
    roll = load(ROLL)

    # index the register by its own `source` string
    by_source = {}
    for item in register:
        by_source.setdefault(item.get("source"), []).append(item)

    roll_by_name = {r["name"]: r for r in roll}
    empty = [r["name"] for r in roll if r.get("entry_count", 0) == 0]

    written, skipped_no_map, skipped_no_items, skipped_populated = [], [], [], []

    for name in empty:
        mapped = source_map.get(name)
        if not mapped:
            skipped_no_map.append(name)
            continue

        entries = []
        for register_source, _declared_count in mapped:
            if register_source in EXCLUDED_REGISTER_SOURCES:
                continue
            for item in by_source.get(register_source, []):
                entries.append({
                    "name": item.get("name"),
                    "type": item.get("type", ""),
                    # Verbatim from the register. These descriptions are truncated at ~120
                    # chars with a trailing ellipsis in every copy of the register held in
                    # this kit -- that is the source's own limit, not a bug here. Left exactly
                    # as-is: Ground Rule 2 of prompts/system_style.txt already tells the prose
                    # model that thin data earns a short entry rather than invented padding.
                    "description": item.get("desc", ""),
                    "scale_note": "",
                    "category": "Mechanical/Named Content",
                    "register_source": register_source,
                })

        if not entries:
            skipped_no_items.append(name)
            continue

        path = os.path.join(RECORDS, slug(name) + ".json")

        # THE ROLL IS A SNAPSHOT; THE RECORD FOLDER IS THE TRUTH. `empty` was selected from
        # SWEEP_ROLL.json as it stood when this process started, and the roll is written by
        # four different scripts (see `silence.write_json`'s own account of it). If another
        # writer -- the cloud session, `ingest.py`, `resync_roll.py`, or a concurrent run of
        # this very tool -- landed real researched entries in that record since the snapshot,
        # writing here would replace research with a truncated folder-mechanical transcription
        # and mark the roll `catalogued` over it, with nothing in the output saying so.
        # An unreadable file counts as populated: not knowing what is there is not evidence
        # that nothing is, and this direction is the recoverable one.
        already = False
        if os.path.exists(path):
            try:
                already = bool(load(path).get("entries"))
            except Exception:
                already = True
        if already:
            skipped_populated.append(name)
            continue

        roll_entry = roll_by_name[name]
        record = {
            "source": name,
            "category": roll_entry.get("category"),
            "mode": "folder-mechanical",
            "entries": entries,
            # No synthesis: ceiling_entity and provisional_magnitude are assay judgements the
            # cloud session made from researched feats. There are none for these sources, and
            # inventing them would put a fabricated power ceiling into the volume frontmatter.
            "synthesis": None,
            "status": "catalogued",
            "provenance": ("Recovered locally from LOCAL_REGISTER.json via the cloud session's "
                           "FOLDER_SOURCE_MAP.json. Transcribed, not researched -- register "
                           "descriptions are truncated at source."),
        }

        if not args.dry_run:
            # ATOMIC. NOTE FOR REVIEW: the two-writer contract says a RECORD should be written
            # through `pipeline.write_record_catalogue`, not straight to disk at all. Making the
            # write atomic is the safe half of that repair; routing this recovery tool through
            # the catalogue writer changes its merge semantics and is flagged in NEXT_STEPS.
            # GATE ON THE WRITE. `silence.write_json` returns False on a persistent lock and
            # this ignored it, then marked the roll row `catalogued` with a real `entry_count`
            # anyway -- so a write that never landed left the roll actively LYING about a record
            # that is not on disk, and since work selection is `entry_count == 0` the source was
            # never revisited. Staying honestly zero is recoverable; claiming a phantom record
            # is not. (run #25)
            if not silence.write_json(path, record, indent=2, ensure_ascii=False):
                print(f"  WRITE DENIED {name}; roll left untouched", flush=True)
                continue
            roll_entry["entry_count"] = len(entries)
            roll_entry["status"] = "catalogued"
        written.append((name, len(entries), os.path.basename(path)))

    if not args.dry_run and written:
        # ATOMIC: `resync_roll.py`'s docstring names THIS script as a roll-clobber source.
        # GATE ON THIS WRITE TOO, for the same reason the per-record writes above are gated:
        # a denied replace here leaves every recovered source still reading `entry_count: 0`
        # while its record sits on disk, and work selection is `entry_count == 0` -- so the
        # next run would transcribe them all again over records that are now good.
        if not silence.write_json(ROLL, roll, indent=2, ensure_ascii=False):
            print("  ROLL WRITE DENIED; the records landed but SWEEP_ROLL.json still reads "
                  "entry_count: 0 for them -- re-run to update the roll", flush=True)

    verb = "Would write" if args.dry_run else "Wrote"
    print(f"{verb} {len(written)} records, {sum(n for _, n, _ in written):,} entries:\n")
    for name, n, fn in sorted(written, key=lambda x: -x[1]):
        print(f"  {n:5d}  {name[:48]:50s} -> {fn}")

    print(f"\nStill empty and NOT recoverable here: {len(skipped_no_map) + len(skipped_no_items)}")
    print(f"  {len(skipped_no_map):3d} not in FOLDER_SOURCE_MAP (web-mode sources -- need real "
          f"research, no local data exists)")
    print(f"  {len(skipped_no_items):3d} mapped, but the register holds no items for them")

    if skipped_populated:
        print(f"\nLeft alone: {len(skipped_populated)} record(s) already hold entries on disk. "
              f"The roll's entry_count is what is stale, not the record:")
        for name in sorted(skipped_populated):
            print(f"  {name}")
    if args.dry_run:
        print("\n(dry run -- nothing written)")


if __name__ == "__main__":
    main()
