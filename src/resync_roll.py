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
    # SORTED, because two record files can declare the SAME source -- that is exactly why this
    # matches on the declared `source` field rather than the filename slug, and the comment
    # above says so. `os.listdir` promises no order, so whichever of the two happened to be
    # visited last silently won the dict slot and its entry count became the roll's new truth;
    # which one won could differ between machines or between runs. Sorted, the winner is at
    # least the same one every time and the fix is reproducible.
    #
    # Reproducible is not the same as visible: sorting only fixes WHICH file wins, it does
    # nothing about the LOSER's entries vanishing from this resync with no trace anywhere. A
    # dict slot has no memory of what it overwrote, so a genuine split-file source (the same
    # thing catalogued twice under different filenames) used to lose one file's entries off
    # the roll silently. Flagged here with a silence.note and folded into the printed diff
    # below instead, so the loss is at least on the record even though picking a winner stays
    # a data-authority call this script does not make.
    by_source = {}
    dupes = {}
    for fn in sorted(os.listdir(RECORDS)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(RECORDS, fn), encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            silence.note("resync_roll.py:record-unreadable")
            continue
        src = rec.get("source")
        if src:
            key = norm(src)
            if key in by_source:
                silence.note("resync_roll.py:duplicate-source")
                dupes.setdefault(key, [by_source[key][1]]).append(fn)
            by_source[key] = (rec, fn)

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
                # AN OWNER EXCLUSION IS NOT A STALE STATUS, and this line would have reverted
                # one. The rule below is `"catalogued" if n else keep`, so any out-of-scope
                # source that still has records on disk -- and the four excluded on 2026-08-25
                # have 933 entries between them -- would be quietly promoted back to
                # `catalogued` on the next routine resync, with nothing red anywhere. An
                # exclusion a maintenance script can undo without anyone noticing is not an
                # exclusion. `roll.py` is the single authority on what is in scope.
                import roll as _roll
                if r.get("status") == _roll.OUT_OF_SCOPE:
                    pass
                elif n:
                    r["status"] = "catalogued"
                else:
                    # A ZERO IS NOT A STALE READING OF A NONZERO STATUS. `hostcheck.py`'s
                    # `purge()` empties a record's `entries` list without touching this roll, so
                    # a source resynced down to zero used to keep whatever status it already
                    # had -- "catalogued" for anything that had been catalogued before the purge
                    # -- letting `entry_count: 0` and `status: catalogued` coexist on the same
                    # row. `entry_count == 0` is what every real consumer (`manifest_builder`,
                    # `catalog.py`, `pipeline.py`) actually gates work-selection on, so the label
                    # must agree with the count rather than repeat the count's own history.
                    r["status"] = "uncatalogued"

    landed = True
    if changed and not dry:
        # ATOMIC: this file's own docstring warned about the roll-clobber hazard while the
        # code went on truncate-then-filling it. Fixed 2026-08-25.
        #
        # THE VERDICT IS NOT OPTIONAL. write_json returns False rather than raising on a
        # denied replace (silence.py:366-367), and this call used to discard that return --
        # so on the exact Windows reader-holds-target case this module's own docstring
        # describes, data/SWEEP_ROLL.json stayed unchanged while the summary below still
        # printed "Fixed". Reported instead, same idiom as worldseed.py's write.
        landed = silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)

    verb = "Would fix" if dry else "Fixed"
    print(f"{verb} {len(changed)} roll entries out of sync with their record files:\n")
    for name, was, now, fn in sorted(changed, key=lambda x: -(x[2] - x[1])):
        print(f"  {name[:44]:46s} {was:6d} -> {now:6d}   {fn}")

    if dupes:
        print(f"\n{len(dupes)} source(s) declared by more than one record file "
              f"(winner is the last name alphabetically; the rest are NOT reflected above):")
        for key, files in sorted(dupes.items()):
            print(f"  {' == '.join(files)}")

    if not dry and not landed:
        print(f"\nWRITE DENIED {ROLL} -- replace refused; roll is UNCHANGED on disk, "
              f"the fixes above did not land and will retry next run")
        have = sum(1 for r in roll if r.get("entry_count", 0) > 0)
        print(f"\nroll unchanged: {have}/{len(roll)} sources catalogued (pre-fix figures)")
        return

    have = sum(1 for r in roll if r.get("entry_count", 0) > 0)
    total = sum(r.get("entry_count", 0) for r in roll)
    print(f"\nroll now: {have}/{len(roll)} sources catalogued, {total:,} entries")


if __name__ == "__main__":
    main()
