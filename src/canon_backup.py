"""CANON BACKUP -- a second copy of the files that cannot be rebuilt from anything else.

WHY THIS EXISTS, AND THE .gitignore LINE THAT IS THE REASON IT DID NOT.

`data/` is excluded from version control, and the comment in `.gitignore` that excludes it says
it is "derived data". For most of `data/` that is true and the exclusion is right -- ASSAYS,
COVERAGE, ENTITY_INDEX and the rest are rebuilt from the records by running the pipeline again.
But it is NOT true of everything under that rule, and the false half of that sentence is the
entire reason no backup was ever made:

    data/records/*.json          THE CORPUS. 217 sources, ~206 MB. Every other file in data/ is
                                 derived FROM these. They are derived from nothing.
    data/WIKI_HOSTS.json         host bindings, hand-corrected over many runs
    data/CHARTER_SPINE_CODES.json   owner-authored charter codes
    data/SWEEP_ROLL.json         derivable from the records, but destroyed TWICE on 2026-08-26
                                 and recovered only because two dated owner rulings happened to
                                 record the eight out-of-scope sources. Cheap; included.

Order ec67de571754 filed this after the expensive lesson: an agent verifying a fix passed test
rows through a `rows=` parameter specifically to avoid touching the live roll, the write path
ignored `rows=`, and the real 216-source roll was overwritten twice in one shift.

WHAT THIS IS NOT. It is not an archive, not a version history and not a disaster-recovery plan
-- it is a second copy on the same disk, which protects against the failure that has actually
happened here (a process overwriting a file it should not have touched) and not against the one
that has not (the disk dying). Saying so plainly matters: a backup whose limits are unstated
gets trusted for things it cannot do. Off-machine copies remain an owner decision.

EVERY SNAPSHOT IS VERIFIED BY READING IT BACK. A backup that was never read is a belief, not a
backup -- the same "a check that cannot fail looks exactly like a check that passed" defect this
project keeps finding elsewhere. `snapshot()` reopens the archive it just wrote, re-hashes every
member, and refuses to record success unless every digest matches the source it came from.
"""
import argparse
import hashlib
import json
import os
import sys
import threading
import time
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SRC)
import silence  # noqa: E402

ROOT = os.path.join(HERE, "state", "backups", "canon")
KEEP = 7                      # daily snapshots retained; ~8 days of history at this cadence

# The non-derivable set. A directory entry means every .json directly inside it.
CANON_FILES = (
    "data/WIKI_HOSTS.json",
    "data/CHARTER_SPINE_CODES.json",
    "data/SWEEP_ROLL.json",
)
CANON_DIRS = (
    "data/records",
)


def digest(path):
    """sha256 of a file, read in chunks. -> hex, or None when unreadable.

    None rather than an exception because a canonical file that cannot be READ is exactly the
    state a backup run must report rather than die on -- and it must be distinguishable from a
    file that hashed to something, which is why the caller checks for None explicitly.
    """
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(block)
    except OSError:
        silence.note("canon_backup.py:unreadable:" + os.path.basename(path))
        return None
    return h.hexdigest()


def members(strict=True):
    """Every canonical file, as (repo-relative path, absolute path). -> [(rel, abs)].

    NO CAP AND NO SAMPLE. The whole point is that the set is complete; a backup that quietly
    covered the first N records would restore a smaller library than the one that was lost, and
    would look exactly like a backup that worked.

    AND IT REFUSES RATHER THAN SHRINKS, which the first version of this got wrong on the day it
    was written. It skipped a missing `CANON_FILES` entry and skipped a missing `CANON_DIRS`
    directory, guarding only the all-empty case -- so if `data/records/` were absent or briefly
    unreadable, this returned the two or three small side files, and `snapshot()` would archive
    them, verify every one of their digests perfectly, and record a SUCCESSFUL BACKUP of almost
    nothing. Found by the run #36 whole-tree sweep hours after the module landed.

    That is the module's own stated hazard arriving through its front door: a snapshot of a
    subset verifies flawlessly, because verification only ever compares what was collected
    against where it came from, and never asks whether the collection was complete. The empty
    case was guarded precisely because it was easy to imagine; the 3-of-219 case is the same
    failure and was not.

    So a declared canonical path that is missing is an ERROR, named. `strict=False` exists for
    callers that want the inventory without the refusal (`main()`'s bare status line), and it is
    never used by `snapshot()`.
    """
    out, absent = [], []
    for rel in CANON_FILES:
        p = os.path.join(HERE, rel.replace("/", os.sep))
        if os.path.isfile(p):
            out.append((rel, p))
        else:
            absent.append(rel)
    for rel in CANON_DIRS:
        d = os.path.join(HERE, rel.replace("/", os.sep))
        if not os.path.isdir(d):
            absent.append(rel + "/ (the whole directory)")
            continue
        names = [n for n in sorted(os.listdir(d)) if n.endswith(".json")]
        if not names:
            absent.append(rel + "/ (present but holds no .json)")
        for name in names:
            out.append((rel + "/" + name, os.path.join(d, name)))
    if absent and strict:
        raise RuntimeError(
            "refusing to build a snapshot: %d declared canonical path(s) are missing -- %s. A "
            "backup of what happens to be present would verify perfectly and restore a smaller "
            "library than the one that was lost."
            % (len(absent), ", ".join(absent)))
    return out


def snapshot(stamp=None):
    """Write one verified snapshot. -> (path, manifest dict).

    Raises RuntimeError if verification fails, because a snapshot that cannot be read back is
    worse than no snapshot: it occupies the place where a real one would go.
    """
    os.makedirs(ROOT, exist_ok=True)
    stamp = stamp or time.strftime("%Y%m%d-%H%M%S")
    items = members()
    if not items:
        raise RuntimeError("no canonical files found under %s -- refusing to write an empty "
                           "snapshot, which would read as a successful backup" % HERE)
    sources = {rel: digest(p) for rel, p in items}
    missing = sorted(r for r, d in sources.items() if d is None)
    if missing:
        # UNCAPPED, like `members()` eight lines above, and for its reason. This was
        # `missing[:5]`: an honest count over a truncated list, which is the same shape one
        # level down as the thing `members()` refuses -- "a backup of what happens to be
        # present would verify perfectly and restore a smaller library than the one that was
        # lost". This is the message a person reads when a backup of the whole canonical corpus
        # refuses, the set is bounded by the canonical inventory, and it only prints on a
        # refusal, so there is no volume argument for cutting it. Order d111c05f5368.
        raise RuntimeError("%d canonical file(s) could not be read: %s"
                           % (len(missing), ", ".join(missing)))

    # PID AND THREAD IN THE TEMP NAME, the convention `silence.write_json` set after two
    # writers sharing one fixed temp filename cost this project real data. A second-resolution
    # stamp is not a disambiguator: two snapshots starting in the same second would write the
    # same scratch file, and the loser would be verified against the winner's bytes.
    tmp = os.path.join(ROOT, "_writing-%s-%d-%d.zip"
                       % (stamp, os.getpid(), threading.get_ident()))
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for rel, p in items:
            z.write(p, arcname=rel)

    # READ IT BACK. Not a formality: this is the only step that distinguishes a backup from an
    # assertion that a backup happened.
    bad = []
    with zipfile.ZipFile(tmp) as z:
        got = set(z.namelist())
        for rel, _p in items:
            if rel not in got:
                bad.append(rel + " (absent from the archive)")
                continue
            h = hashlib.sha256()
            with z.open(rel) as fh:
                for block in iter(lambda: fh.read(1 << 20), b""):
                    h.update(block)
            if h.hexdigest() != sources[rel]:
                bad.append(rel + " (digest differs from source)")
    if bad:
        os.remove(tmp)
        # UNCAPPED, and this is the worst of the three `[:5]`s that were here: the archive is
        # deleted on the line above, so this string is the ONLY surviving record of which
        # members failed to verify. Order d111c05f5368.
        raise RuntimeError("snapshot failed verification and was deleted: %s" % "; ".join(bad))

    final = os.path.join(ROOT, "canon-%s.zip" % stamp)
    if silence.replace_retry(tmp, final) is False:
        raise RuntimeError("snapshot could not be renamed into place: %s" % final)

    manifest = {"stamp": stamp, "files": len(items), "bytes": os.path.getsize(final),
                "verified": True, "digests": sources}
    # THE MANIFEST WRITE IS CHECKED TOO. This discarded the verdict while the archive write three
    # lines above correctly raised on a refusal -- the same discarded-write-verdict defect the
    # run #36 sweep found in ten other modules, committed here in the module whose entire job is
    # not to trust a write it has not confirmed. Without the manifest `verify()` has no recorded
    # digests to compare against, so it silently degrades to "the zip still opens".
    # THROUGH `silence.write_json`, WHICH IS THE ONLY WRITER IN THIS PROJECT THAT GETS THE TEMP
    # NAME RIGHT. This went through a hand-rolled `_write_manifest` whose scratch file was
    # `dst + '.writing'` -- a FIXED name, eight lines after the comment above forbidding exactly
    # that for the zip beside it. Two snapshots overlapping would write one scratch manifest and
    # the loser's bytes would land beside the winner's archive, and a crossed manifest is worse
    # than an absent one: `verify()` fails CLOSED with no manifest (:312-320) but a present one
    # parses, `recorded` is non-empty, and it reports "archive intact, N members" having
    # compared this archive against another one's digests. `write_json` carries pid and thread
    # in the temp, discards the temp on a denied replace, and returns the verdict this line
    # already gates on. Order 112bed050c3a.
    #
    # NOT FULLY CLOSED, and deliberately left so: two snapshots starting in the same second
    # share `stamp`, hence share `final` and this destination name. Closing that means putting
    # the pid into `stamp` itself, which changes the archive naming `prune()` and `newest()`
    # read, so it is a separate decision from this one.
    if not silence.write_json(final[:-4] + ".manifest.json", manifest,
                              indent=2, sort_keys=True):
        raise RuntimeError(
            "the snapshot landed at %s but its manifest could not be written, so nothing records "
            "what it contains and verify() cannot check it. Re-run the snapshot." % final)
    return final, manifest


# A snapshot whose zip write dies part-way leaves its scratch file behind -- `_writing-<stamp>-
# <pid>-<tid>.zip`, a full archive's worth of bytes (~215 MB) -- and `prune` only ever looked at
# `canon-*.zip`, so nothing anywhere reaped them (order 4965e049c8fb). Reaped by AGE, not by
# asking whether the pid in the name is still alive: pids are reused, and a wrong answer there
# deletes an archive that is being written right now. Six hours is far longer than any snapshot
# this project has taken and far shorter than the interval between them.
ORPHAN_AGE_S = 6 * 3600


def prune(keep=KEEP):
    """Delete all but the newest `keep` snapshots, and reap abandoned scratch files.

    -> [names of snapshots ACTUALLY removed]. Age-ordered by NAME, which is the timestamp, not
    by mtime -- mtime moves when a file is touched and this must not be able to decide that the
    newest snapshot is the oldest one.

    THE DELETE VERDICT WAS BEING DISCARDED (order 4965e049c8fb). `removed.append(f)` sat outside
    the try/except, so a denied `os.remove` -- the ordinary case on this machine when the
    dashboard or a reader holds a snapshot open -- was recorded as a removal, and `main()` then
    printed "pruned N old snapshot(s): ..." naming files still on disk. In the module whose whole
    subject is not trusting a write it has not confirmed ("a backup that was never read is a
    belief, not a backup"), that is the same defect one level down.

    THE REFUSALS GO TO STDERR RATHER THAN INTO THE RETURN VALUE, and that is deliberate: this
    returns a plain list because `overnight.canon_backup_cycle` consumes it as one, and widening
    it to a tuple would break that caller silently at the point where it reports a backup. The
    machine-readable record is `silence.note`, which is already where a denied write in this
    project goes to be counted.
    """
    if not os.path.isdir(ROOT):
        return []
    snaps = sorted(f for f in os.listdir(ROOT)
                   if f.startswith("canon-") and f.endswith(".zip"))
    removed, denied = [], []
    for f in snaps[:-keep] if keep > 0 else []:
        gone = True
        for p in (os.path.join(ROOT, f),
                  os.path.join(ROOT, f[:-4] + ".manifest.json")):
            try:
                if os.path.isfile(p):
                    os.remove(p)
            except OSError:
                silence.note("canon_backup.py:prune-denied:" + f)
                gone = False
        # A pair half-removed counts as NOT removed. It is the worse state of the two -- an
        # archive with no manifest is what `verify()` cannot check, and a manifest with no
        # archive is a record of a backup that is not there -- so it must not read as a clean
        # prune, and the next pass will try the survivor again.
        (removed if gone else denied).append(f)
    for f in sorted(os.listdir(ROOT)):
        if not (f.startswith("_writing-") and f.endswith(".zip")):
            continue
        p = os.path.join(ROOT, f)
        try:
            if time.time() - os.path.getmtime(p) < ORPHAN_AGE_S:
                continue                     # a snapshot may be writing this one right now
            os.remove(p)
            silence.note("canon_backup.py:orphan-reaped:" + f)
        except OSError:
            silence.note("canon_backup.py:orphan-denied:" + f)
    if denied:
        print("canon_backup: %d old snapshot(s) could NOT be fully deleted and are still on "
              "disk: %s" % (len(denied), ", ".join(denied)), file=sys.stderr)
    return removed


def newest():
    """-> path of the most recent snapshot, or None."""
    if not os.path.isdir(ROOT):
        return None
    snaps = sorted(f for f in os.listdir(ROOT)
                   if f.startswith("canon-") and f.endswith(".zip"))
    return os.path.join(ROOT, snaps[-1]) if snaps else None


def verify(path=None):
    """Re-verify a snapshot against the LIVE tree. -> (ok, [notes]).

    Divergence is NOT a failure. The live tree moves constantly and a snapshot from this morning
    is supposed to differ from the tree this evening. What this answers is the narrower and more
    useful question: is the archive itself still intact and readable, and which canonical files
    have changed since it was taken.

    NO MANIFEST IS A FAILURE, NOT A PASS (order b6d5f70a7f19). This used to return ok=True with
    `recorded = {}`, so `changed` was empty BY CONSTRUCTION and the notes read "archive intact,
    0 members" / "0 canonical files changed since the snapshot" -- a comparison against nothing,
    reported as a clean verify, with `main()` printing "VERIFY: ok" and returning 0. It is
    precisely the failure `snapshot()`'s own run #36 comment names: "Without the manifest
    verify() has no recorded digests to compare against, so it silently degrades to 'the zip
    still opens'." The WRITE side was corrected to raise; the READ side was not. Reachable
    whenever a manifest is absent -- an older snapshot, one deleted by hand, or a prune that
    removed one of the pair and not the other.
    """
    path = path or newest()
    notes = []
    if not path or not os.path.isfile(path):
        return False, ["no snapshot exists"]
    man = path[:-4] + ".manifest.json"
    recorded = {}
    if os.path.isfile(man):
        try:
            with open(man, encoding="utf-8") as fh:
                recorded = (json.load(fh) or {}).get("digests") or {}
        except (OSError, ValueError) as e:
            # An unparseable manifest is the same state as a missing one, and it used to leave
            # this function by way of a raw traceback out of `main()`. It falls into the refusal
            # below with the reason attached.
            notes.append("manifest unreadable (%s)" % type(e).__name__)
    if not recorded:
        # FAIL CLOSED. "I cannot tell whether this snapshot is what it claims" is not a pass. The
        # archive may well be perfect, and the note says that rather than alleging corruption --
        # what is missing is any means of CHECKING, and that is a much worse thing to find out
        # during a restore than during a verify.
        return False, notes + [
            "NO MANIFEST beside %s: there are no recorded digests to check this archive "
            "against, so nothing about its contents can be verified -- only that the zip "
            "opens. Take a fresh --snapshot, which writes one." % os.path.basename(path)]
    try:
        with zipfile.ZipFile(path) as z:
            broken = z.testzip()
    except (OSError, zipfile.BadZipFile) as e:
        return False, ["archive unreadable: %s" % e]
    if broken:
        return False, ["archive corrupt at member %s" % broken]
    live = {rel: digest(p) for rel, p in members(strict=False)}
    changed = [r for r, d in live.items() if recorded.get(r) and d != recorded[r]]
    added = [r for r in live if r not in recorded]
    gone = [r for r in recorded if r not in live]
    notes.append("archive intact, %d members" % len(recorded))
    notes.append("%d canonical files changed since the snapshot" % len(changed))
    if added:
        notes.append("%d canonical files are new since the snapshot" % len(added))
    if gone:
        # UNCAPPED. A canonical record file that has disappeared from the live tree is the
        # single most actionable thing this module can tell anyone, and `sorted(gone)[:5]` named
        # the alphabetical head and decided the rest had not happened. Order d111c05f5368.
        notes.append("%d canonical files present in the snapshot are GONE from the live tree: %s"
                     % (len(gone), ", ".join(sorted(gone))))
    return True, notes


def restore(rel, path=None, dest=None):
    """Extract ONE canonical file from a snapshot. -> written path.

    One file, never the whole tree, and never over the live file by default: a restore that can
    overwrite `data/` wholesale is a tool for turning a small loss into a large one. `dest`
    defaults beside the snapshot so a person compares before replacing anything.
    """
    path = path or newest()
    if not path:
        raise RuntimeError("no snapshot to restore from")
    dest = dest or os.path.join(ROOT, "restored", os.path.basename(rel))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with zipfile.ZipFile(path) as z, open(dest, "wb") as out:
        with z.open(rel) as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                out.write(block)
    return dest


def main():
    ap = argparse.ArgumentParser(description="back up the non-derivable canonical files")
    ap.add_argument("--snapshot", action="store_true", help="take a verified snapshot")
    ap.add_argument("--verify", action="store_true", help="re-verify the newest snapshot")
    ap.add_argument("--restore", metavar="REL", help="extract one file, e.g. data/WIKI_HOSTS.json")
    ap.add_argument("--keep", type=int, default=KEEP)
    a = ap.parse_args()

    if a.restore:
        print("restored ->", restore(a.restore))
        return 0
    if a.verify:
        ok, notes = verify()
        for n in notes:
            print(" ", n)
        print("VERIFY:", "ok" if ok else "FAILED")
        return 0 if ok else 1
    if a.snapshot:
        t0 = time.time()
        path, man = snapshot()
        removed = prune(a.keep)
        print("snapshot: %d files, %.1f MB, verified, in %.1fs"
              % (man["files"], man["bytes"] / 1e6, time.time() - t0))
        print("  ->", path)
        if removed:
            print("  pruned %d old snapshot(s): %s" % (len(removed), ", ".join(removed)))
        return 0

    items = members(strict=False)
    print("%d canonical files, %.1f MB live"
          % (len(items), sum(os.path.getsize(p) for _r, p in items) / 1e6))
    n = newest()
    print("newest snapshot:", n or "NONE -- the canonical corpus is unbacked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
