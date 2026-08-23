#!/usr/bin/env python3
"""
Rebuilds SWEEP_ROLL.json's entry_count/status from the record files on disk.

The record files are the authority; the roll is an index over them. They can drift apart:
every cataloguer (catalogue_web.py, catalogue_aurora.py, catalogue_codex.py,
recover_folder_records.py) rewrites the whole roll after each source, so two of them running
concurrently will have one clobber the other's counters with a stale copy read minutes
earlier. That happened once here -- the Aurora run wrote 425 entries for Dr. Firestorm's
Engineering Corps and 681 for The Elements Beyond, then the wiki run's final save reset both
to 0 while leaving the record files untouched.

Running this after any cataloguing session makes the roll agree with reality again. It is
safe to run at any time and changes nothing else about the roll.
"""
import json
import os
import sys
import silence

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLL = os.path.join(HERE, "data/SWEEP_ROLL.json")
RECORDS = os.path.join(HERE, "data/records")


def norm(s):
    return "".join(c for c in (s or "").lower() if c.isalnum())


def main():
    dry = "--dry-run" in sys.argv

    with open(ROLL, encoding="utf-8") as f:
        roll = json.load(f)

    # index every record file by its declared `source`, which is more reliable than the
    # filename slug (slugging rules differ between the cataloguers)
    by_source = {}
    for fn in os.listdir(RECORDS):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(RECORDS, fn), encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            silence.note("resync_roll.py:45")
            continue
        src = rec.get("source")
        if src:
            by_source[norm(src)] = (rec, fn)

    changed = []
    for r in roll:
        hit = by_source.get(norm(r["name"]))
        if not hit:
            continue
        rec, fn = hit
        n = len(rec.get("entries", []))
        if r.get("entry_count", 0) != n:
            changed.append((r["name"], r.get("entry_count", 0), n, fn))
            if not dry:
                r["entry_count"] = n
                r["status"] = "catalogued" if n else r.get("status", "catalogued")

    if changed and not dry:
        with open(ROLL, "w", encoding="utf-8") as f:
            json.dump(roll, f, indent=2, ensure_ascii=False)

    verb = "Would fix" if dry else "Fixed"
    print(f"{verb} {len(changed)} roll entries out of sync with their record files:\n")
    for name, was, now, fn in sorted(changed, key=lambda x: -(x[2] - x[1])):
        print(f"  {name[:44]:46s} {was:6d} -> {now:6d}   {fn}")

    have = sum(1 for r in roll if r.get("entry_count", 0) > 0)
    total = sum(r.get("entry_count", 0) for r in roll)
    print(f"\nroll now: {have}/{len(roll)} sources catalogued, {total:,} entries")


if __name__ == "__main__":
    main()
