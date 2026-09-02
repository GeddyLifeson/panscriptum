"""Withdraw generated chapters from the library, preserving them for the record.

OWNER RULING 2026-08-25: the 145 chapters written while the prose gate was inverted are
withdrawn. They were produced for sources running 0.0%-9.0% cited, 71% of their entries lost the
Threads section the template requires, and some carry Instrument axis scores with no assay behind
them (see BUGS M25/M26/M27).

MOVES, DOES NOT UNLINK. Regenerating them costs real model time, and `generate.py` is resumable
and content-hashed -- once a source's citations improve, its jobs re-run as stale anyway. So the
withdrawn set goes to `output/withdrawn_<date>/` where it is out of the library but still on
disk. Purging it is a separate, deliberate act.

SELECTION IS EXPLICIT AND THE CATALOG IS EDITED, NOT ERASED (order cda7b9e2b4e1). This tool had
no way to withdraw a SUBSET: it processed every entry in the catalog and then replaced the whole
file with `{}`. The 2026-08-25 run was safe only by coincidence -- the entire catalog at that
moment WAS the 145 bad chapters -- and the coincidence is not repeatable. Two consequences of
the old shape, both live:

  * a later `--go` for one bad source would have withdrawn the whole library with it;
  * `{}` also erased entries whose files did NOT move -- the `move failed` branch prints and
    continues, so a chapter still sitting in `output/raw` lost its catalog record anyway, which
    is a file the library no longer knows it has.

So `--source` and `--addr` select, the default is still the whole catalog (the documented
invocation is unchanged), and what is written back is the catalog MINUS exactly the entries whose
files actually left. Anything that failed to move keeps its record.

Usage:  python src/withdraw_chapters.py --go [--label 2026-08-25]
        python src/withdraw_chapters.py --source "Song of Syx" --source "Deep Rock Galactic"
        python src/withdraw_chapters.py --addr "II.J.4/Frontmatter" --go
"""
import argparse
import datetime
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(HERE, "output", "index", "catalog.json")


def _abs(p):
    """Catalog paths are stored Windows-style and relative to the kit root."""
    if not p:
        return None
    p = p.replace("\\", os.sep).replace("/", os.sep)
    return p if os.path.isabs(p) else os.path.join(HERE, p)


def _file_state(p):
    """Classify a catalogued chapter file: 'live', 'gone' or 'unavailable'.

    `publish._live_file_state`'s question, asked about a chapter (order 22394233dbad). The
    `missing` branch below turned on a single `os.path.exists`, and `genericpath.exists`
    catches `(OSError, ValueError)` and answers False -- so a lock, a denial, an over-long path
    or a name the filesystem will not parse was spelled exactly like "this chapter is already
    gone". Measured: `os.path.exists` returns False with no exception for both an over-long
    path and a path with an embedded NUL. That mattered here more than almost anywhere, because
    a path this loop cannot stat was counted as `missing`, was NOT added to `stuck`, and so had
    its catalog record deleted -- the precise harm the module docstring names, "a chapter still
    sitting in output/raw lost its catalog record anyway".

    So it asks twice. A file that stats is 'live'. A file that does not stat AND whose name is
    ABSENT from a successfully enumerated parent directory is 'gone' -- positive evidence, the
    directory answered. Anything else is 'unavailable', and the caller keeps the record.
    """
    try:
        os.stat(p)
        return "live"
    except FileNotFoundError:
        pass
    except (OSError, ValueError):
        # The two families `os.path.exists` swallows: a denial or a lock (OSError) and a name
        # the platform will not accept at all (ValueError). Neither is evidence of absence.
        return "unavailable"
    try:
        present = os.path.basename(p) in os.listdir(os.path.dirname(p) or ".")
    except (OSError, ValueError):
        return "unavailable"
    return "unavailable" if present else "gone"


def _archive_name_free(dst):
    """Is `dst` positively known to be an unused name in the archive? -> bool.

    THE ARCHIVE IS THE ONLY COPY (order 8d14f0adda1b). `shutil.move` given a full destination
    PATH -- not a directory -- does not raise on a name already taken: its "Destination path
    already exists" check only fires when `dst` is a directory. Otherwise `os.rename` raises
    FileExistsError on Windows, `move` falls through to `copy2` + `unlink`, and the file already
    in the archive is OVERWRITTEN with no error and no record. Measured on this machine: moving
    onto an occupied name left the mover's bytes and destroyed the occupant's. Two withdrawals
    sharing one `--label` archive is the whole scenario, and the today's-date default makes it
    unlikely rather than impossible -- a re-run on the same day, or an explicit `--label`, walks
    straight into it.

    Refuses on anything but a clear answer, for the same reason `_file_state` does: a bare
    `os.path.exists` here answers False for a name it merely could not read, which would read as
    "free" and hand the overwrite to `copy2`. Only FileNotFoundError -- the directory answering
    that the name is not there -- counts as free. This is still a check-then-act, so it narrows
    the window rather than closing it; the move itself remains the last word.
    """
    try:
        os.stat(dst)
    except FileNotFoundError:
        return True
    except (OSError, ValueError):
        return False
    return False


def select(cat, sources=None, addrs=None):
    """The entries this run will withdraw. -> {addr: rec}.

    PURE, so the selection can be attacked by the drill without moving a file. No filter selects
    the whole catalog, which is what the tool has always done and what the owner ruling of
    2026-08-25 wanted; a filter selects exactly what it names. Matching on `source_name` is
    exact rather than fuzzy on purpose -- this is the destructive step, and a tool that guesses
    which chapters the operator meant is worse than one that withdraws nothing and says so.
    """
    if not sources and not addrs:
        return dict(cat)
    want_src, want_addr = set(sources or ()), set(addrs or ())
    return {a: r for a, r in cat.items()
            if a in want_addr or (r or {}).get("source_name") in want_src}


def main():
    # THE PLANT-WIDE INTERLOCK, AND THIS TOOL WAS NOT WIRED TO IT (order bd107a18b13e).
    #
    # `escalation.assert_clear`'s own docstring opens "EVERY entry point calls this before doing
    # anything." Fourteen modules in src/ did. This one -- which `shutil.move`s every catalogued
    # chapter out of the library, moves every unclaimed stray in output/raw, and then rewrites
    # output/index/catalog.json, the file generate.py and publish.py both read -- did not. A halt
    # is raised precisely when a library-wide invariant has been violated and nothing may start
    # until a person rules on it (Hard Rule -1), and moving the chapters out and rewriting the
    # index of them is the last thing that should proceed on uncertain ground. Every action here
    # is a MOVE, so the archive is the only copy afterwards.
    #
    # IT SITS ABOVE THE ARGPARSE BLOCK AND ABOVE THE CATALOG READ, so there is no path into this
    # job that skips it -- including `--go` typed in a hurry while the library is stopped.
    #
    # FAIL CLOSED ON THE IMPORT, copied from publish.py:1385-1398 and NOT wrapped in a bare
    # except: `except ImportError: pass` is how a deleted or unparseable escalation.py silently
    # switched the halt off in nine jobs at once (run #31). A job that cannot ask whether the
    # library is halted has no business starting.
    try:
        import escalation as _ESC
    except ImportError as _esc_gone:
        raise SystemExit(
            "REFUSING TO START: the escalation chain (src/escalation.py) could not be "
            "imported (%s), so the halt cannot be read. Hard Rule -1." % _esc_gone) from _esc_gone
    _ESC.assert_clear(os.path.basename(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true", help="actually move; otherwise dry-run")
    ap.add_argument("--source", action="append", metavar="NAME",
                    help="withdraw only chapters whose source_name is exactly this "
                         "(repeatable); default is the whole catalog")
    ap.add_argument("--addr", action="append", metavar="ADDR",
                    help="withdraw only these catalog addresses, e.g. 'II.J.4/Frontmatter' "
                         "(repeatable)")
    # NOT A FIXED DATE (found run35, batch 6). This defaulted to "2026-08-25" -- the day of the
    # withdrawal that motivated writing this script -- so a second, unrelated `--go` with no
    # `--label` would move its files into that SAME `output/withdrawn_2026-08-25/` archive,
    # which already held 148 files and, because this script MOVES rather than copies, is the
    # only copy of them. Two withdrawals sharing one archive directory is exactly the collision
    # the `shutil.move` sweep further down had no guard against -- it recorded a move it could
    # not make (order ead79ecf5278), but a name it COULD overwrite it did. The default is now
    # today's date, computed when the tool runs rather than baked in when written, AND the
    # sweep itself now refuses an occupied archive name outright (order 8d14f0adda1b) -- the
    # date only made the collision unlikely, and "unlikely" is not a guard when the loser is
    # the only copy of a withdrawn chapter.
    ap.add_argument("--label", default=datetime.date.today().isoformat())
    a = ap.parse_args()

    arch = os.path.join(HERE, "output", "withdrawn_" + a.label)
    with open(CATALOG, encoding="utf-8") as f:
        cat = json.load(f)
    filtered = bool(a.source or a.addr)
    sel = select(cat, a.source, a.addr)
    print("catalog entries: %d" % len(cat))
    print("selected       : %d%s" % (len(sel), "" if not filtered else
                                     "  (--source/--addr; the rest of the catalog stays)"))
    # NAMING SOMETHING AND WITHDRAWING NOTHING IS A TYPO, NOT A RESULT. Falling through would
    # move no file, write the catalog back unchanged, and print a clean report -- an operator
    # would read that as "already withdrawn".
    #
    # PER SELECTOR, NOT PER RUN (order c8ac7dbab3c5). This fired only when the WHOLE selection
    # came back empty, so a mistyped `--addr` alongside any selector that DID match was silently
    # ignored: the run withdrew the ones it understood, said nothing about the one it did not,
    # and the operator read a clean report as confirmation that everything named had gone. Worse,
    # the `unknown` list was built from `a.source` alone, so even on the empty branch -- the
    # branch whose whole job is naming the typo -- an `--addr` typo was never named. Both
    # selectors are now checked against the catalog independently, and ANY selector that matches
    # nothing refuses the run. Matching is exact by design (see `select`), so an unmatched
    # selector is a spelling; on the tool whose next step is irreversible, a spelling is a stop.
    have_src = {(r or {}).get("source_name") for r in cat.values()}
    unknown_src = sorted(set(a.source or ()) - have_src)
    unknown_addr = sorted(set(a.addr or ()) - set(cat))
    if filtered and (not sel or unknown_src or unknown_addr):
        parts = []
        if unknown_src:
            parts.append("no such source_name: %s" % ", ".join(repr(u) for u in unknown_src))
        if unknown_addr:
            parts.append("no such address: %s" % ", ".join(repr(u) for u in unknown_addr))
        raise SystemExit("part of that selection matches nothing in the catalog%s. Refusing to "
                         "continue: matching is exact, so this is a spelling, not an empty "
                         "result. %d entr(ies) WOULD have been withdrawn by the selectors that "
                         "did match; fix the name and re-run so the whole selection is deliberate."
                         % ("" if not parts else " (%s)" % "; ".join(parts), len(sel)))

    if a.go:
        # A COPY BEFORE THE IRREVERSIBLE STEP. This script moves rather than unlinks, which was
        # the right instinct when it was written -- but the instinct was the ONLY thing standing
        # behind 145 chapters. A snapshot that fails RAISES, so the withdrawal cannot proceed
        # believing it has a copy behind it when it does not.
        import snapshot as SNAP
        sid = SNAP.before("withdraw-chapters", ["output/index/catalog.json"],
                          note="catalog (%d entries) before withdrawing %d chapters"
                               % (len(cat), len(sel)))
        ok, why = SNAP.verify(sid)
        if not ok:
            raise SNAP.SnapshotFailed(
                "the snapshot taken before this withdrawal does not restore (%s). Refusing to "
                "continue: an untested backup is a belief, not a backup." % why)
        print("snapshot %s taken and verified (%s)" % (sid, why))
        os.makedirs(os.path.join(arch, "raw"), exist_ok=True)
        os.makedirs(os.path.join(arch, "compressed"), exist_ok=True)

    moved = {"raw": 0, "compressed": 0}
    missing = 0
    stuck = set()
    unreadable = []   # (addr, path) -- could not be statted, so absence was never established
    collided = []     # (addr, path) -- the archive already holds this name; NOT overwritten
    amended = []      # (addr, key, new_path) -- half the entry left, so its record was rewritten
    for _addr, rec in sel.items():
        # WHICH HALF OF THE ENTRY LEFT (order 1687ff8084b9). `raw_path` and `compressed_path`
        # move independently, and `stuck.add(_addr); continue` kept the WHOLE record when the
        # second failed -- including a `raw_path` pointing at a file that had already moved to
        # the archive. "A failed move keeps its record" is right per FILE and wrong per ENTRY
        # when only half the entry moved, so the two halves are tracked separately here and the
        # surviving record is amended below.
        entry_left = []   # [(key, dst)] -- files of this entry that actually reached the archive
        for key, sub in (("raw_path", "raw"), ("compressed_path", "compressed")):
            src = _abs(rec.get(key))
            if not src:
                missing += 1
                continue
            state = _file_state(src)
            if state == "unavailable":
                # STAT REFUSED TO ANSWER, WHICH IS NOT ABSENCE. Counting this as `missing` and
                # falling through dropped the record of a file that may still be in the library
                # -- the one outcome this module exists to prevent. It is a kept record and a
                # printed line, exactly like a failed move.
                print("  could not stat: %s (record kept, absence not established)" % src)
                unreadable.append((_addr, src))
                stuck.add(_addr)
                continue
            if state == "gone":
                missing += 1
                continue
            if a.go:
                dst = os.path.join(arch, sub, os.path.basename(src))
                if not _archive_name_free(dst):
                    # A NAME ALREADY IN THE ARCHIVE IS A REFUSAL, NOT A MOVE. `shutil.move` would
                    # overwrite it (see `_archive_name_free`), and the archive is the only copy of
                    # whatever is sitting there. Leaving the chapter where it is costs one line in
                    # the report; taking it costs the other withdrawal, permanently.
                    print("  archive name taken, NOT moved: %s -> %s" % (src, dst))
                    collided.append((_addr, dst))
                    stuck.add(_addr)
                    continue
                try:
                    shutil.move(src, dst)
                except Exception as e:
                    print("  move failed: %s (%s)" % (src, e))
                    # A FAILED MOVE KEEPS ITS RECORD. The file is still in the library; dropping
                    # its catalog entry anyway (which the old wholesale `{}` did) leaves a
                    # chapter on disk that nothing knows about, which is an unrecorded loss in
                    # the tool whose one job is preserving the record of what was withdrawn.
                    stuck.add(_addr)
                    continue
                entry_left.append((key, dst))
            moved[sub] += 1
        if a.go and _addr in stuck and entry_left:
            # THE RECORD IS KEPT AND MADE TRUE. This entry stays in the catalog because part of
            # it is still in the library, but the part that DID leave is not where the record
            # says any more. Rewriting the path to the archive is chosen over moving the file
            # back: the move already succeeded, and undoing it is a second irreversible act on
            # the strength of the first one's failure. `rec` is the same object `remaining`
            # carries, so the amendment lands in catalog.json with the rest of the write.
            for key, dst in entry_left:
                rec[key] = os.path.relpath(dst, HERE)
                amended.append((_addr, key, rec[key]))

    # Anything left in output/raw that the catalog never claimed -- the pilot's strays.
    # ONLY ON A WHOLE-CATALOG WITHDRAWAL. An unclaimed file belongs to no source and no address,
    # so no `--source`/`--addr` selection can name it; sweeping it up anyway would make a
    # targeted withdrawal quietly take files it was never pointed at.
    #
    # GUARDED, LIKE THE CATALOGUED MOVES ABOVE (order ead79ecf5278). This called `shutil.move`
    # bare, so one denied or colliding stray -- a reader holding a file open, a name already in
    # the archive -- raised out of `main()` at the WORST possible moment: after every catalogued
    # chapter above had already been moved and before the catalog write below. The filesystem
    # had changed and the record of it had not, leaving the catalog pointing at paths nothing
    # occupies and nothing on disk saying which of the two was right. A stray that will not move
    # is a line in the report, not a reason to abandon the record of the ones that did.
    extra = 0
    stray_stuck = []
    rawdir = os.path.join(HERE, "output", "raw")
    if not filtered and os.path.isdir(rawdir):
        for f in sorted(os.listdir(rawdir)):
            src = os.path.join(rawdir, f)
            if not os.path.isfile(src):
                continue
            if a.go:
                dst = os.path.join(arch, "raw", f)
                # SAME COLLISION GUARD AS THE CATALOGUED MOVES (order 8d14f0adda1b). A stray
                # sharing a name with something already archived would overwrite it just as
                # silently, and a stray is by definition the copy nothing has a record of.
                if not _archive_name_free(dst):
                    print("  stray NOT moved, archive name taken: %s -> %s" % (src, dst))
                    stray_stuck.append(f)
                    continue
                try:
                    shutil.move(src, dst)
                except Exception as e:
                    print("  stray move failed: %s (%s)" % (src, e))
                    stray_stuck.append(f)
                    continue
            extra += 1

    withdrawn = {k: v for k, v in sel.items() if k not in stuck}
    remaining = {k: v for k, v in cat.items() if k not in withdrawn}

    catalog_landed = True
    record_landed = True
    record_path = os.path.join(arch, "catalog.withdrawn.json")
    if a.go:
        # The withdrawn catalog is the record of WHAT was withdrawn; keep it beside the files.
        # It is the SELECTION, not the whole catalog: with a filter the two differ, and a record
        # that overstates what left the library is the wrong record to leave behind.
        #
        # AND ITS VERDICT IS KEPT, exactly like the operational write below (order 5d2d456145d0).
        # These two calls sit together and only one used to be checked, which read as a decision
        # that this one could not fail. `silence.write_json` returns False rather than raising on
        # a denied replace, so a lost record here is silent -- and this is the file that says
        # which chapters the archive directory holds. Losing it turns `output/withdrawn_<date>/`
        # into a heap of files with no manifest, in the tool whose one job is preserving the
        # record of what was withdrawn. It cannot be undone by retrying either: the files have
        # already moved, so a second run finds nothing to withdraw and writes an EMPTY record
        # over the gap. That is why it is reported rather than merely returned.
        # MERGE WITH AN EXISTING MANIFEST RATHER THAN REPLACE IT (order 959ac19ac3f7). The
        # file-collision guard above (`_archive_name_free`) only protects the CHAPTER FILES --
        # two `--go` runs sharing a `--label` (the default is just today's date) put both sets
        # of files safely side by side in the same archive directory, because their basenames
        # differ. This manifest has no such disambiguator: it is one fixed name inside that
        # directory, so the second run's unconditional replace erased the first run's record
        # even though the first run's files are still sitting right there, un-overwritten. The
        # archive would then hold chapters from two withdrawals under a manifest listing only
        # one -- "a heap of files with no manifest" for whichever run lost the race, in the tool
        # whose one job is preserving the record of what was withdrawn. Both withdrawals really
        # are in that directory, so the union, keyed by address, is the true manifest; a repeated
        # address (the same entry withdrawn twice under one label) keeps the later record, same
        # rule `_UNPRESERVED`-style merges elsewhere in this project use for "whichever writer
        # has more to say wins the key."
        existing_manifest = {}
        try:
            with open(record_path, encoding="utf-8") as f:
                existing_manifest = json.load(f)
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as e:
            print("  existing manifest at %s could not be read (%s) -- not merging; the new "
                  "manifest will hold only this run's withdrawals." % (record_path, e))
        merged_manifest = dict(existing_manifest)
        merged_manifest.update(withdrawn)
        if existing_manifest:
            new_from_existing = len(existing_manifest) - sum(
                1 for k in existing_manifest if k in withdrawn)
            print("  manifest at %s already existed (%d entr(ies)) -- merged with this run's "
                  "%d, %d kept from the earlier withdrawal, %d entr(ies) total"
                  % (record_path, len(existing_manifest), len(withdrawn),
                     new_from_existing, len(merged_manifest)))
        record_landed = silence.write_json(record_path, merged_manifest, indent=2)
        # ATOMIC, AND THE VERDICT KEPT. This ran AFTER every chapter file above has already
        # been moved, on the one file generate.py and publish.py both read -- same collision
        # hazard as scout._land, on a shared file. The hand-rolled `CATALOG + ".tmp"` plus a
        # dropped `silence.replace_retry` return meant a denied replace (a reader holding
        # catalog.json open, this module's normal situation) left the catalog claiming every
        # withdrawn chapter still lives where the files just moved away from, with nothing
        # raising to say so.
        #
        # THE CATALOG IS EDITED, NOT ERASED. This wrote `{}` unconditionally, which was right for
        # exactly one run and wrong in general: with a `--source`/`--addr` selection it would
        # throw away every chapter the operator did not name, and even without one it discarded
        # the records of chapters whose move had just FAILED. What lands is the catalog minus the
        # entries whose files actually left. With no filter and no failure that is still `{}` --
        # the 2026-08-25 behaviour, arrived at by measurement instead of by assumption.
        catalog_landed = silence.write_json(CATALOG, remaining, indent=2)

    # PATHS AND ENTRIES ARE DIFFERENT UNITS and these lines used to hide it: `moved` and
    # `missing` count PATHS (two per entry) while `stuck` counts ENTRIES, and every line read
    # like an entry count (order 1687ff8084b9). The unit is now written into each label.
    print("raw paths moved       : %d  (+%d unclaimed by the catalog)" % (moved["raw"], extra))
    print("compressed paths moved: %d" % moved["compressed"])
    print("paths already gone    : %d" % missing)
    if stuck:
        # UNCAPPED. This is the list a person reads to go and look at the files, so a ranked
        # first-six would hide exactly the entries that need hands on them.
        print("MOVE FAILED, RECORD KEPT: %d entr(ies) stay in the catalog because their files "
              "are still in the library -- %s" % (len(stuck), ", ".join(sorted(stuck))))
    if unreadable:
        print("COULD NOT STAT, RECORD KEPT: %d path(s) neither moved nor proven absent -- a lock "
              "or a denial reads the same as a deletion, so the record stays: %s"
              % (len(unreadable), ", ".join("%s (%s)" % (ad, p) for ad, p in unreadable)))
    if collided:
        print("ARCHIVE NAME ALREADY TAKEN: %d path(s) were NOT moved because %s already holds "
              "the name and moving would have overwritten the only copy. Re-run those with a "
              "different --label: %s"
              % (len(collided), arch, ", ".join("%s -> %s" % (ad, p) for ad, p in collided)))
    if amended:
        print("PARTIAL WITHDRAWAL, RECORD AMENDED: %d path(s) left while the rest of their entry "
              "stayed, so the kept record now points at the archive copy: %s"
              % (len(amended), ", ".join("%s %s=%s" % t for t in amended)))
    if stray_stuck:
        # Unclaimed by the catalog, so no entry needs amending -- but a file the sweep meant to
        # take and did not is still a difference between what this run reports and what is on
        # disk, and it is only a difference anybody can see if it is printed.
        print("STRAY MOVE FAILED: %d unclaimed file(s) are still in output/raw -- %s"
              % (len(stray_stuck), ", ".join(stray_stuck)))
    if a.go:
        if not record_landed:
            # The archive's own manifest. Named separately from the catalog line below because
            # the remedy is different: retrying the run cannot rebuild this one (the files have
            # already moved), so the %d addresses are printed here to be copied down by hand.
            print("ARCHIVE RECORD NOT WRITTEN: %s -- replace refused, so %d withdrawn entr(ies) "
                  "are in %s with NO manifest beside them. Write it by hand from this run's "
                  "output; a re-run will not reproduce it. Addresses: %s"
                  % (record_path, len(withdrawn), arch, ", ".join(sorted(withdrawn))))
        if not catalog_landed:
            print("CATALOG WRITE DENIED: %s still lists the paths just moved away -- "
                  "replace refused, retry this run" % CATALOG)
        with open(CATALOG, encoding="utf-8") as f:
            print("catalog now       : %d entries" % len(json.load(f)))
        print("archive           : %s" % arch)
    else:
        print("DRY RUN -- pass --go to move")

    # EVERY REFUSAL ABOVE WAS PRINTED AND THEN DISCARDED. `main()` had no `return` on any path
    # and the entry point was a bare `main()`, so this tool exited 0 unconditionally -- including
    # when the catalog write was DENIED, which is the state the module docstring calls "a file
    # the library no longer knows it has", inverted: the files have moved and the catalog has
    # not. The same for a missing archive manifest (a re-run cannot reproduce it), and for
    # chapters that are still in the library or whose absence was never established.
    #
    # THE SIBLING IN THIS SAME TREE ALREADY ARGUED IT OUT. `address_space.py:467-480` hits the
    # identical condition -- a denied `silence.write_json` on a file other modules read -- and
    # returns 1: "Nothing here can retry the rename, so the honest act is to say so and exit
    # nonzero ... a shelfmark read as fresh while it is stale is not recoverable by anything
    # downstream." It applies with more force here, because this tool has already MOVED files by
    # the time the write is refused.
    #
    # Console output is not the machine-readable channel: this is a `--go` tool an operator or a
    # wrapper script runs, and rc 0 is the only thing a shell `&&`, a scheduled job or a keeper
    # restart looks at. Every printed line above is unchanged -- the rc is additive, and the
    # per-condition wording is still what a person reads. The dry-run path returns 0; a selector
    # that matched nothing already raised SystemExit at :184 and never reaches here.
    # Order b422c125e93e.
    bad = ((not catalog_landed) or (not record_landed)
           or bool(stuck or unreadable or collided or stray_stuck))
    return 1 if (a.go and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
