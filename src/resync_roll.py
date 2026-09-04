#!/usr/bin/env python3
"""
Rebuilds SWEEP_ROLL.json's entry_count/status from the record files on disk.

The record files are the authority; the roll is an index over them. They can drift apart:
every cataloguer (catalogue_web.py, catalogue_aurora.py, catalogue_codex.py,
recover_folder_records.py) USED TO rewrite the whole roll after each source, so two of them
running concurrently had one clobber the other's counters with a stale copy read minutes
earlier. That happened once here -- the Aurora run wrote 425 entries for Dr. Firestorm's
Engineering Corps and 681 for The Elements Beyond, then the wiki run's final save reset both
to 0 while leaving the record files untouched.

That class is closed at the source as of order f818a77293fc: every writer of the roll,
including this one, now lands its own rows through `roll.mutate`'s compare-and-swap, which
re-reads and re-applies key-wise by source name rather than landing a whole stale document.
This script remains the repair for the drift that is left -- a record file written or emptied
without the roll being told (hostcheck.purge does exactly that), and any row still carrying a
count from before the fix.

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
    # ARGPARSE, NOT A SUBSTRING TEST ON argv (order eb4a87793c19). This was
    # `dry = "--dry-run" in sys.argv`, with no parser anywhere in the module, so every near miss
    # -- `--dryrun`, `--dry`, `-n`, `--dry_run`, `--dry-run=true` -- left `dry` False and the
    # script went straight on to the real `silence.write_json(ROLL, ...)`. Nothing errored and
    # the printed output gave no way to notice: the only difference between the two modes is the
    # word "Fixed" versus "Would fix" at the head of a table the reader is scanning for source
    # names. The file at stake is data/SWEEP_ROLL.json -- one of canon_backup's four
    # non-derivable canonical files, "destroyed TWICE on 2026-08-26" -- so a flag that means DO
    # NOT TOUCH THIS FILE has to make an unrecognised spelling a hard error, which parse_args
    # does and `in sys.argv` cannot.
    import argparse
    ap = argparse.ArgumentParser(
        description="Rebuild SWEEP_ROLL.json's entry_count/status from the record files.")
    ap.add_argument("--dry-run", action="store_true",
                    help="report every repair without writing data/SWEEP_ROLL.json")
    dry = ap.parse_args().dry_run

    with open(ROLL, encoding="utf-8") as f:
        roll = json.load(f)

    # SNAPSHOT THE ON-DISK FIGURES BEFORE THE REPAIR LOOP CAN TOUCH `roll` (order 590964e48e63).
    # The loop below mutates these SAME dicts in place (`r["entry_count"] = n`,
    # `r["status"] = want`) before any write is attempted, so recomputing "have" from `roll`
    # after the loop -- which the denied-write branch used to do -- reads the REPAIRED figures,
    # not the disk figures, even though that branch exists specifically to report that the
    # write did NOT land. Kept separately so the denied branch has something honest to print.
    have_on_disk = sum(1 for r in roll if r.get("entry_count", 0) > 0)

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
    unreadable = []
    for fn in sorted(os.listdir(RECORDS)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(RECORDS, fn), encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            # COUNTED, NOT ONLY NOTED. A record file that will not parse is a source this run
            # did NOT check, and the closing "roll now: X/Y sources catalogued" was printed over
            # it as though it had. `silence.note` files the fault where a maintenance sweep can
            # find it later; it says nothing to the person reading this run's output now, which
            # is the person who can still do something about it. (order 2ab24aeb63f7)
            silence.note("resync_roll.py:record-unreadable")
            unreadable.append(fn)
            continue
        # PARSES IS NOT THE SAME AS IS-A-RECORD (sweep43-batch15). `json.load` is perfectly
        # happy with `[]`, `"x"`, `null` or `3`, none of which have `.get`, so the next line
        # raised an uncaught AttributeError and took the WHOLE resync down -- past the handler
        # directly above it, which only ever covered the parse. A half-written or hand-edited
        # record is exactly the file most likely to be in that state, and it is the same fault
        # class already fixed in `wiki_source.py`'s read of the hosts file and never carried
        # over here.
        #
        # Folded into `unreadable` rather than given a category of its own, because it means
        # the same thing to the person reading the output: this is a source this run did NOT
        # check, and the closing "roll now: X/Y sources catalogued" must not be printed over it
        # as though it had been.
        if not isinstance(rec, dict):
            silence.note("resync_roll.py:record-not-an-object")
            unreadable.append(fn)
            continue
        src = rec.get("source")
        if src:
            key = norm(src)
            if key in by_source:
                silence.note("resync_roll.py:duplicate-source")
                dupes.setdefault(key, [by_source[key][1]]).append(fn)
            by_source[key] = (rec, fn)

    # `roll.py` is the single authority on what is in scope; imported once, above the loop.
    import roll as _roll

    changed = []
    relabelled = []
    unmatched_rows = []
    unnamed_rows = 0
    # {source name: {field: value}} -- this run's repairs, re-applied to a FRESHLY READ roll by
    # the compare-and-swap below rather than landed as this process's whole copy of the file.
    # (order f818a77293fc)
    repairs = {}
    for r in roll:
        # A NAMELESS ROW USED TO TAKE THE WHOLE RESYNC DOWN. `norm(r["name"])` assumed every row
        # carries a name, so one malformed row raised KeyError before anything was written and
        # every OTHER row's repair was lost with it -- the least useful possible response to one
        # bad row in an index over the record files. No such row exists on disk today (checked:
        # 215 rows, all named), which is exactly when the guard is cheap. (order eb4a87793c19)
        if not r.get("name"):
            silence.note("resync_roll.py:row-without-name")
            unnamed_rows += 1
            continue
        hit = by_source.get(norm(r["name"]))
        if not hit:
            # A ROLL ROW WITH NO RECORD FILE IS UNCHECKED, NOT AGREED. It was skipped with a
            # bare `continue` and never appeared anywhere in the output, so the closing
            # "roll now: X/Y sources catalogued" was printed over rows this run never looked
            # at. Counted and listed below instead. (order 2ab24aeb63f7)
            unmatched_rows.append(r["name"])
            continue
        rec, fn = hit
        n = len(rec.get("entries", []))
        if r.get("entry_count", 0) != n:
            changed.append((r["name"], r.get("entry_count", 0), n, fn))
            if not dry:
                r["entry_count"] = n
                repairs.setdefault(r["name"], {})["entry_count"] = n

        # THE STATUS RULE IS ABOUT THE COUNT, NOT ABOUT THE COUNT HAVING MOVED.
        #
        # This whole block sat INSIDE the `if r.get("entry_count", 0) != n:` branch above, so a
        # row whose count already agreed but whose LABEL did not was never visited and kept the
        # wrong label indefinitely -- and the pair it was added to repair (entry_count == 0 with
        # status "catalogued", left behind by `hostcheck.purge`) is exactly the pair that stops
        # changing once the count has settled at zero. A repair reachable only while the count
        # is still moving cannot fix the state it was written for. It is evaluated for every
        # matched row now, and only WRITES when the label actually differs, so nothing is
        # rewritten for the sake of it. (order 2ab24aeb63f7)
        #
        # AN OWNER EXCLUSION IS NOT A STALE STATUS, and this rule would have reverted one. The
        # rule is `"catalogued" if n else "uncatalogued"`, so any out-of-scope source that still
        # has records on disk -- and the four excluded on 2026-08-25 have 933 entries between
        # them -- would be quietly promoted back to `catalogued` on the next routine resync,
        # with nothing red anywhere. An exclusion a maintenance script can undo without anyone
        # noticing is not an exclusion.
        #
        # A ZERO IS NOT A STALE READING OF A NONZERO STATUS. `hostcheck.py`'s `purge()` empties
        # a record's `entries` list without touching this roll, so a source resynced down to
        # zero used to keep whatever status it already had -- "catalogued" for anything that had
        # been catalogued before the purge -- letting `entry_count: 0` and `status: catalogued`
        # coexist on the same row. `entry_count == 0` is what every real consumer
        # (`manifest_builder`, `catalog.py`, `pipeline.py`) actually gates work-selection on, so
        # the label must agree with the count rather than repeat the count's own history.
        if r.get("status") != _roll.OUT_OF_SCOPE:
            want = "catalogued" if n else "uncatalogued"
            if r.get("status") != want:
                relabelled.append((r["name"], r.get("status"), want, n))
                if not dry:
                    r["status"] = want
                    repairs.setdefault(r["name"], {})["status"] = want

    landed = True
    if (changed or relabelled) and not dry:
        # ATOMIC: this file's own docstring warned about the roll-clobber hazard while the
        # code went on truncate-then-filling it. Fixed 2026-08-25.
        #
        # AND ATOMIC WAS STILL NOT THE PROPERTY (order f818a77293fc). This module exists BECAUSE
        # of a lost update -- the opening docstring records the wiki run's final save resetting
        # two counters to 0 while leaving the record files untouched -- and it then landed its
        # own whole in-memory copy of the roll, which is the same act from the other side. The
        # repair is now key-wise: `roll.mutate` re-reads the file, re-applies only THIS run's
        # rows, and on a refusal re-reads and re-applies rather than retrying the same bytes.
        #
        # THE EXCLUSION GUARD IS RE-CHECKED ON THE FRESH ROW, not just on the snapshot. A source
        # a person marked out-of-scope while this run was walking the record folder must not be
        # promoted back by a repair computed before that ruling existed; that is the trap
        # roll.py's header and the drill net of the same name are both about.
        #
        # THE VERDICT IS NOT OPTIONAL. The writer returns False rather than raising on a
        # denied replace (silence.replace_if_unchanged's PermissionError/OSError branches),
        # and this call used to discard that return --
        # so on the exact Windows reader-holds-target case this module's own docstring
        # describes, data/SWEEP_ROLL.json stayed unchanged while the summary below still
        # printed "Fixed". Reported instead, same idiom as worldseed.py's write.
        def _apply(rows):
            for r in rows:
                fix = repairs.get(r.get("name"))
                if not fix:
                    continue
                if "entry_count" in fix:
                    r["entry_count"] = fix["entry_count"]
                if "status" not in fix:
                    continue
                # A BARE `!=` COMPARE, deliberately, and not folded into the line above as an
                # `and`. The exclusion guard is a property the drill net reads out of this
                # module's parse tree -- every reachable write to a row's status must sit inside
                # an out-of-scope guard -- and a BoolOp is not the shape it can read. Same rule,
                # written so the net can still see it holding.
                if r.get("status") != _roll.OUT_OF_SCOPE:
                    r["status"] = fix["status"]
            return rows

        landed, why = _roll.mutate(_apply, path=ROLL)
        if why:
            print("\nROLL: %s" % why)

    verb = "Would fix" if dry else "Fixed"
    print(f"{verb} {len(changed)} roll entries out of sync with their record files:\n")
    for name, was, now, fn in sorted(changed, key=lambda x: -(x[2] - x[1])):
        print(f"  {name[:44]:46s} {was:6d} -> {now:6d}   {fn}")

    if relabelled:
        # Its own list, because a status repair and a count repair are different findings: the
        # count came from the record file, the label came from a rule about the count.
        print(f"\n{verb.lower()} {len(relabelled)} row(s) whose STATUS disagreed with their "
              f"count (the count itself may not have moved):")
        for name, was, now, n in sorted(relabelled):
            print(f"  {name[:44]:46s} {str(was)[:14]:16s} -> {now:14s} (entry_count {n})")

    # UNCAPPED, both of them, per Hard Rule 0: these are lists a person reads in order to act --
    # one needs the record file repaired, the other needs a record file to exist at all -- and a
    # truncated list of them would quietly decide which sources are worth the reader's attention.
    if unreadable:
        print(f"\n{len(unreadable)} record file(s) could not be read, so their source was NOT "
              f"checked against the roll and is NOT counted in the figures below:")
        for fn in unreadable:
            print(f"  {fn}")

    if unmatched_rows:
        print(f"\n{len(unmatched_rows)} roll row(s) have no record file declaring their source; "
              f"nothing was verified for them either way:")
        for name in unmatched_rows:
            print(f"  {name}")

    if unnamed_rows:
        print(f"\n{unnamed_rows} roll row(s) carry no `name` at all, so nothing could be looked "
              f"up for them; they were skipped and are NOT counted in the figures below")

    if dupes:
        print(f"\n{len(dupes)} source(s) declared by more than one record file "
              f"(winner is the last name alphabetically; the rest are NOT reflected above):")
        for key, files in sorted(dupes.items()):
            print(f"  {' == '.join(files)}")

    # THE CAVEAT TRAVELS WITH THE FIGURE. Both closing lines below are counts over the whole
    # roll, and rows this run could not check are inside them.
    caveat = ""
    if unmatched_rows or unreadable or unnamed_rows:
        caveat = ("   [%d row(s) unchecked: no record file; %d record file(s) unreadable; "
                  "%d row(s) with no name]"
                  % (len(unmatched_rows), len(unreadable), unnamed_rows))

    if not dry and not landed:
        print(f"\nWRITE DENIED {ROLL} -- replace refused; roll is UNCHANGED on disk, "
              f"the fixes above did not land and will retry next run")
        print(f"\nroll unchanged: {have_on_disk}/{len(roll)} sources catalogued (pre-fix figures)"
              + caveat)
        # NONZERO, because this is the branch where the file on disk is NOT what the lines above
        # describe. `main()`'s value only became the process's exit code when the module started
        # calling `sys.exit(main())` below; before that a supervisor or a person reading $? after
        # a cataloguing session was told the roll now agrees with the record files while the roll
        # was untouched. Two independent defects, one signal -- the bare `return` here was the
        # other half. (order 8605c2ed6061)
        return 1

    have = sum(1 for r in roll if r.get("entry_count", 0) > 0)
    total = sum(r.get("entry_count", 0) for r in roll)
    print(f"\nroll now: {have}/{len(roll)} sources catalogued, {total:,} entries" + caveat)
    return 0


if __name__ == "__main__":
    # THE EXIT CODE IS THE NUMBER THE SCHEDULER ACTUALLY LOOKS AT -- generate.py, weave_index.py,
    # sweep.py, feats.py and handbuilt.py all say so at this same line, and this module called
    # `main()` bare, which discards the return value entirely. A denied SWEEP_ROLL.json write
    # exited 0, i.e. the run reported that the roll now agrees with the record files when the
    # file on disk was unchanged. `sys.exit(None)` is 0, so a clean run is unaffected.
    # (order 8605c2ed6061)
    sys.exit(main())
