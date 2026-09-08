#!/usr/bin/env python3
"""
Rebuilds the missing folder-mode records from data the cloud session already gathered.

Why this exists
---------------
6 of the 215 sources on the Acquisitions Roll show `entry_count: 0` -- a cloud session hit
a limit mid-sweep and those records were never written (0 have no record file at all; all 6
have a file containing an empty `entries` list). Every one of them is nonetheless flagged
`status: "catalogued"` on the roll, which is why the gap is easy to miss. (Measured directly
against data/SWEEP_ROLL.json and data/records/ on 2026-08-26; re-run the same check before
trusting these counts on a later date, since the roll is live and this section is not.)

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
import sys

sys.path.insert(0, os.path.dirname(__file__))

import silence                                                          # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REGISTER = os.path.join(HERE, "reference/keystone_volumes/LOCAL_REGISTER.json")
SOURCE_MAP = os.path.join(HERE, "reference/pipeline_tooling/FOLDER_SOURCE_MAP.json")
ROLL = os.path.join(HERE, "data/SWEEP_ROLL.json")
RECORDS = os.path.join(HERE, "data/records")

# Still matches catalogue_web.py's slug() -- because both are now literally the same function.
#
# The note that stood here said this copy deliberately carried the `[:60]` truncation that
# ingest_doc.py's slug() lacks, and read that difference as the other file's omission. It was the
# reverse: the cap is the defect (Hard Rule 0 -- ranking is encouraged, ranking then truncating is
# forbidden), and it applies to a record's IDENTITY as much as to a roster. `Who Framed Roger
# Rabbit (incl. all content from its associated crossover-toon IPs)` slugs to 79 characters and
# was cut to 60 on disk, which is how a 304-entry record and its roll row lost the path between
# them (order 683c59f43829, fixed in catalogue_aurora.py, symptom written by catalogue_web.py).
#
# IMPORTED rather than re-written, for the reason the bug itself demonstrates: four slug functions
# that must agree is not a design, it is a pending disagreement. `record_path` comes with it and
# prefers the file that ALREADY EXISTS -- exact slug first, then the legacy 60-character prefix --
# so an un-truncated identity cannot strand or duplicate the records written under the cap. No
# cycle: catalogue_aurora imports catalogue_codex and silence, neither of which imports this file.
from catalogue_aurora import record_path, slug as _slug  # noqa: E402

# Re-bound so `recover_folder_records.slug` still exists as a module attribute, and is the SAME
# OBJECT as catalogue_aurora.slug and catalogue_web.slug rather than a third that must agree.
slug = _slug


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
    # ROLL SOURCE -> [(register source, declared, yielded)] for every mapping that yielded fewer
    # items than it declared (order 729c26e0e63c). Reported BY NAME beside the other buckets at
    # the foot of this function, because -- per order aff81a1f1029, established for this very
    # file -- these buckets prescribe DIFFERENT work and a count tells the reader neither which
    # sources nor which remedy.
    short_sources = {}
    # Set by either write gate below; carried out through main()'s return so a denied write is
    # a nonzero exit and not merely a printed line. See the two sites for the argument.
    denied = False
    # This run's roll rows, by source name -- the input to the compare-and-swap at the bottom.
    # The comment at line 168 already says the roll is a SNAPSHOT and the record folder is the
    # truth; landing the whole snapshot back is how that snapshot became everyone else's truth
    # too. (order f818a77293fc)
    roll_changes = {}

    for name in empty:
        mapped = source_map.get(name)
        # `is None`, NOT falsiness. An empty LIST is a source that IS in FOLDER_SOURCE_MAP and
        # maps to nothing, and `if not mapped` filed it under "not in FOLDER_SOURCE_MAP
        # (web-mode sources -- need real research, no local data exists)" -- the one bucket whose
        # remedy is wrong for it. The `skipped_no_items` bucket ("mapped, but the register holds
        # no items for them") exists for exactly this case and could never fire for it, because
        # the empty mapping never reached the loop that fills `entries`. The two buckets
        # prescribe different work -- go and research the source, versus fix the mapping or the
        # register -- so the mislabel sends the reader the wrong way. Measured over the 6 roll
        # sources with entry_count == 0: 'Lost Mines of Phandelver' and 'the Witch Tradition' are
        # present in FOLDER_SOURCE_MAP.json with [], the other 4 are genuinely absent. An empty
        # mapping now falls through and lands in `skipped_no_items` by the ordinary route.
        # (order 37d3d588847a)
        if mapped is None:
            skipped_no_map.append(name)
            continue

        entries = []
        # THE DECLARED COUNT IS SPENT NOW, NOT UNPACKED AND DROPPED (order 729c26e0e63c, owner
        # ruling 5 of 2026-09-08: "rank instead of displace; record every drop and re-ask" --
        # the missing counters land in feats_index/manifest_builder and here).
        #
        # `_declared_count` came out of FOLDER_SOURCE_MAP.json, which this module's own header
        # describes as the cloud session's mapping "WITH COUNTS ... curatorial work it already
        # did", and it was read into a name with a leading underscore and never compared with
        # anything. The number it should be compared against was on the very next line. So a
        # mapping declaring 350 items against a register yielding 3 was transcribed in silence:
        # the record landed, the roll row was stamped `status='catalogued'` with
        # `entry_count: 3`, and because work selection everywhere in this pipeline is
        # `entry_count == 0` the source was never revisited. A truncated catalogue
        # indistinguishable from a complete one, arriving through a cross-check the data had
        # already paid for.
        shortfalls = []
        for register_source, _declared_count in mapped:
            if register_source in EXCLUDED_REGISTER_SOURCES:
                continue
            _got = by_source.get(register_source, [])
            try:
                _want = int(_declared_count)
            except (TypeError, ValueError):
                # A MAPPING THAT DECLARES NOTHING USABLE IS NOT A MAPPING THAT AGREES. It is a
                # cross-check that could not be made, which is its own answer -- the same
                # distinction this file draws between a denied write and a write that landed.
                _want = None
                shortfalls.append((register_source, None, len(_got)))
            if _want is not None and len(_got) < _want:
                shortfalls.append((register_source, _want, len(_got)))
            for item in _got:
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

        # RECORDED BEFORE THE EARLY EXIT BELOW, deliberately: a source that declared 350 and
        # yielded nothing at all is the LOUDEST case of this fault, and putting the accumulator
        # after the `continue` would have made it the one case that never gets reported.
        if shortfalls:
            short_sources[name] = list(shortfalls)

        if not entries:
            skipped_no_items.append(name)
            continue

        # `record_path`, not a raw join on slug(): the existing file wins where there is one, so
        # a record written under the old 60-character cap is FOUND (and therefore correctly seen
        # as already populated by the guard below) instead of being shadowed by a second file
        # under the un-truncated name.
        path = record_path(name, RECORDS)

        # THE ROLL IS A SNAPSHOT; THE RECORD FOLDER IS THE TRUTH. `empty` was selected from
        # SWEEP_ROLL.json as it stood when this process started, and the roll is written by
        # SEVEN different scripts (four, in `silence.write_json`'s older account of it; the
        # count was already stale and the roll writes are compare-and-swapped now, order
        # f818a77293fc -- but this snapshot is still a snapshot). If another
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
            # AND THE SHORTFALL IS WRITTEN INTO THE PROVENANCE (order 729c26e0e63c). This string
            # already exists to say what the transcription is and is NOT; a register that
            # yielded fewer items than the mapping declared is exactly that kind of statement,
            # and it has to travel with the record rather than only across the console, because
            # the record is what a later reader has.
            "provenance": ("Recovered locally from LOCAL_REGISTER.json via the cloud session's "
                           "FOLDER_SOURCE_MAP.json. Transcribed, not researched -- register "
                           "descriptions are truncated at source."
                           + ("" if not shortfalls else
                              " INCOMPLETE AGAINST ITS OWN MAPPING: "
                              + "; ".join(
                                  "%s declared %s, register yielded %d"
                                  % (rs, "an unreadable count" if want is None else want, got)
                                  for rs, want, got in shortfalls)
                              + ". This record is a floor, not the whole of what was mapped.")),
        }

        if not args.dry_run:
            # ATOMIC, AND EXEMPT FROM THE RECORD-WRITER CONTRACT BY RULING -- THIS IS THE NOTE
            # (order 9a44b1535851, owner ruling 10 of 2026-09-08: "leave recover_folder_records
            # outside the catalogue writer with the exemption recorded in the two-writer note").
            #
            # THE CONTRACT. `pipeline.write_record_catalogue` is the project's only sanctioned
            # record writer, and the reason is that it MERGES rather than replaces: the
            # catalogue and the pipeline both write data/records/*.json, they write them WHOLE,
            # and marvel.json once went from 1,051 entries to 30,207 in a single re-catalogue
            # pass -- so landing a stale in-memory copy over that reverts twenty-nine thousand
            # entries and the loss reads as "the re-catalogue never ran".
            #
            # WHY THIS TOOL IS THE EXCEPTION. Merging is the wrong semantics HERE. This is a
            # folder-mechanical transcription of a register: it is not researched, its
            # descriptions are truncated at source, and it carries `synthesis: None` because
            # inventing a ceiling would be a fabricated power band in a volume's frontmatter.
            # Folding it INTO an existing record would silently mix transcription with research
            # under one provenance string, which is the one property this record exists to keep
            # separable. So it does not merge -- it declines to write at all where a record
            # already holds entries (see the `already` guard below), which is the fail-closed
            # form of the same protection and is strictly more conservative than a merge.
            #
            # THE ROUTING GAP IS THEREFORE CLOSED BY RULING, NOT BY CODE, and this comment is
            # where it is recorded. The order's own text noted that its predecessor said the
            # deviation was "flagged in NEXT_STEPS" while NEXT_STEPS.md contained no mention of
            # it -- and NEXT_STEPS.md is overwritten every run, so it was never a place a
            # decision could live. It lives here, beside the write it governs.
            #
            # Making the write atomic was the safe half of the original repair and is unchanged.
            # GATE ON THE WRITE. `silence.write_json` returns False on a persistent lock and
            # this ignored it, then marked the roll row `catalogued` with a real `entry_count`
            # anyway -- so a write that never landed left the roll actively LYING about a record
            # that is not on disk, and since work selection is `entry_count == 0` the source was
            # never revisited. Staying honestly zero is recoverable; claiming a phantom record
            # is not. (run #25)
            if not silence.write_json(path, record, indent=2, ensure_ascii=False):
                print(f"  WRITE DENIED {name}; roll left untouched", flush=True)
                # AND THE VERDICT LEAVES THE PROCESS (order aff81a1f1029). This branch printed
                # and continued, main() fell off its end returning None, and the entry point
                # discarded even that -- so a run in which EVERY write was denied exited 0 and
                # any caller gating on rc learned nothing. The comment above says at length why
                # a silently-dropped verdict here is unrecoverable; this is that same argument
                # one level up.
                denied = True
                continue
            # roll_entry itself is not mutated here: persistence goes exclusively through
            # roll_changes / roll.update_rows below, which re-reads the roll from disk and
            # merges only these changes into it (order 9954fb56d0e3, mirroring the same fix
            # in catalogue_codex.py under order 09f3105df988).
            roll_changes[name] = {"entry_count": len(entries), "status": "catalogued"}
        written.append((name, len(entries), os.path.basename(path)))

    # ATOMIC: `resync_roll.py`'s docstring names THIS script as a roll-clobber source.
    # GATE ON THIS WRITE TOO, for the same reason the per-record writes above are gated:
    # a denied replace here leaves every recovered source still reading `entry_count: 0`
    # while its record sits on disk, and work selection is `entry_count == 0` -- so the
    # next run would transcribe them all again over records that are now good.
    # AND A COMPARE-AND-SWAP RATHER THAN A WHOLE-DOCUMENT LAND (order f818a77293fc). Atomic was
    # never the property this needed: this tool reads the roll at startup, walks the register,
    # and used to write its own startup-time copy of every other writer's rows back over them.
    # `roll.update_rows` merges only the rows recovered here into a freshly-read roll.
    if not args.dry_run and written:
        import roll as _roll
        roll_landed, roll_why = _roll.update_rows(roll_changes, path=ROLL)
        if not roll_landed:
            print("  ROLL WRITE DENIED; the records landed but SWEEP_ROLL.json still reads "
                  "entry_count: 0 for them -- re-run to update the roll", flush=True)
            denied = True
        if roll_why:
            print("  ROLL: %s" % roll_why, flush=True)

    verb = "Would write" if args.dry_run else "Wrote"
    print(f"{verb} {len(written)} records, {sum(n for _, n, _ in written):,} entries:\n")
    for name, n, fn in sorted(written, key=lambda x: -x[1]):
        # UNCUT (Hard Rule 0, sweep42-batch07). `name[:48]` cut the source name with no marker,
        # against this codebase's own display-truncation doctrine (corpus_db._cell(), order
        # 6160ef68b229). The padding stays so short names still line up.
        print(f"  {n:5d}  {name:50s} -> {fn}")

    # NAMED, NOT COUNTED (order aff81a1f1029). `skipped_populated` below has always printed its
    # sources by name; these two printed a bare number. Order 37d3d588847a separated these
    # buckets precisely BECAUSE they prescribe different work -- go and research the source,
    # versus fix the mapping or the register -- and a count tells the reader neither which
    # sources nor which remedy. There are at most a handful, and every one is printed.
    print(f"\nStill empty and NOT recoverable here: {len(skipped_no_map) + len(skipped_no_items)}")
    print(f"  {len(skipped_no_map):3d} not in FOLDER_SOURCE_MAP (web-mode sources -- need real "
          f"research, no local data exists)")
    for name in sorted(skipped_no_map):
        print(f"        {name}")
    print(f"  {len(skipped_no_items):3d} mapped, but the register holds no items for them")
    for name in sorted(skipped_no_items):
        print(f"        {name}")

    # THE CROSS-CHECK THE DATA ALREADY PAID FOR (order 729c26e0e63c). Named, never counted, for
    # the reason the two buckets above are: this bucket prescribes its own third remedy -- fix
    # the mapping, or fix the register -- and it is the one bucket whose members otherwise look
    # like successes. Every source and every mapping is printed; there is no cut here.
    if short_sources:
        _total_lost = sum((want or 0) - got
                          for rows in short_sources.values() for _, want, got in rows
                          if want is not None and want > got)
        print(f"\nSHORT AGAINST THEIR OWN MAPPING: {len(short_sources)} source(s), about "
              f"{_total_lost:,} declared item(s) the register did not yield. These landed as "
              f"records and were stamped 'catalogued', and work selection is entry_count == 0, "
              f"so nothing will revisit them on its own:")
        for name in sorted(short_sources):
            for rs, want, got in short_sources[name]:
                print("  %-42s %-30s declared %s, yielded %d"
                      % (name, rs, "an unreadable count" if want is None else want, got))

    if skipped_populated:
        print(f"\nLeft alone: {len(skipped_populated)} record(s) already hold entries on disk. "
              f"The roll's entry_count is what is stale, not the record:")
        for name in sorted(skipped_populated):
            print(f"  {name}")
    if args.dry_run:
        print("\n(dry run -- nothing written)")
    # 1 means at least one write this run was DENIED -- not "nothing to do" and not a finding
    # about the corpus. Every other module in this family (feats, chain, weave, reference,
    # backfill, module_index) already carries its verdict out this way.
    return 1 if denied else 0


if __name__ == "__main__":
    sys.exit(main())
