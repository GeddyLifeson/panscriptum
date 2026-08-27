#!/usr/bin/env python3
"""
RE-PASS — re-apply the corrected evidence gate to everything already catalogued.

The backscan found that ~90% of assigned Magnitude bands rested on no feat at all: a bare mention
of "planet" satisfied the old gate, so "resource-rich jungle planet" and "one of the cities
dedicated to the preservation of humanity" were licensing Magnitudes.

The gate is fixed. This re-applies it to work already done.

NO MODEL CALLS. The evidence was already extracted and is still on disk; what was wrong was the
RULE applied to it. So this is a pure re-evaluation -- fast, deterministic, and repeatable -- and
it demotes to `unassayed` every band whose evidence does not survive the corrected reading.

Demotion is not data loss. The entry keeps its name, description, topic and category; it loses a
claim nobody had earned. `unassayed` is the honest state under X.6 H5: no worksheet, no number.

Run with --apply to write. Without it, reports only.
"""
import argparse
import collections
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pipeline as PL          # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    recs = PL.records()
    demoted_entries = []
    demoted_sources = []
    kept_entries = []
    cleared_notes = 0
    touched = []

    for path, rec in recs:
        changed = False
        src = rec["source"]

        syn = rec.get("synthesis") or {}
        band = syn.get("provisional_magnitude")
        if (band and band != "unassayed"
                and not PL.valid_scale_note(syn.get("evidence") or "")):
            demoted_sources.append((src, band, (syn.get("evidence") or "")[:70]))
            if args.apply:
                syn["provisional_magnitude"] = "unassayed"
                syn["demoted_by"] = ("evidence gate corrected 2026-08-20; the recorded "
                                     "evidence is not a feat")
                changed = True

        for e in rec["entries"]:
            if not e.get("catalogued"):
                continue
            b = e.get("magnitude")
            sn = e.get("scale_note") or ""
            if b and b != "unassayed":
                if PL.valid_scale_note(sn):
                    kept_entries.append((src, e.get("name"), b, sn[:70]))
                else:
                    demoted_entries.append((src, e.get("name"), b, sn[:70]))
                    if args.apply:
                        e["magnitude"] = "unassayed"
                        changed = True
            # A note that no longer evidences scale should not sit in the record claiming to.
            if sn and not PL.valid_scale_note(sn):
                cleared_notes += 1
                if args.apply:
                    e["scale_note"] = ""
                    changed = True

        if changed:
            # GATE ON THE WRITE. `write_record` returns whether the write LANDED; this ignored
            # it and appended to `touched` regardless, so the run's closing "APPLIED. N
            # rewritten" counted sources whose file was never modified. Reproduced by the run
            # #25 sweep against a torn file: the write was refused, the disk copy was untouched,
            # and the script still reported it as rewritten. (run #25)
            if PL.write_record(path, rec):
                touched.append(src)
            else:
                print("  WRITE DENIED %s; left as it was" % src, flush=True)

    total_banded = len(demoted_entries) + len(kept_entries)
    print("=" * 96)
    print("RE-PASS — corrected evidence gate applied to work already done")
    print("=" * 96)
    print("\nENTRY BANDS")
    print(f"  banded before      : {total_banded:,}")
    print(f"  survive the gate   : {len(kept_entries):,}  ({len(kept_entries)/max(1,total_banded):.1%})")
    print(f"  demoted to unassayed: {len(demoted_entries):,}")
    print("\nSOURCE CEILINGS")
    print(f"  demoted to unassayed: {len(demoted_sources):,} of {len(recs):,}")
    print(f"\nscale notes cleared (no longer evidence): {cleared_notes:,}")

    print("\n  SURVIVORS — every one of these is an act upon an object, or a measured quantity:")
    for s, n, b, sn in kept_entries[:14]:
        print(f"     [{b}] {str(n)[:30]:<32}{sn}")

    print("\n  DEMOTED — a sample of what was carrying a Magnitude:")
    by_band = collections.Counter(b for _, _, b, _ in demoted_entries)
    print(f"     by band: {dict(sorted(by_band.items()))}")
    for s, n, b, sn in demoted_entries[:8]:
        print(f"     [{b}] {str(n)[:30]:<32}{sn}")

    if args.apply:
        print(f"\nAPPLIED. {len(touched)} record files rewritten.")
    else:
        print("\nDRY RUN. Re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
