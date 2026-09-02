"""SNAPSHOT — take a copy before doing something that cannot be undone, and prove it restores.

WHY. On 2026-08-25 this session withdrew 145 generated chapters on the owner's ruling. It moved
them rather than deleting them, which was the right instinct -- but the instinct was the only
thing protecting them. Nothing in the kit takes a copy before a destructive step, and the two
places that do keep backups (`local_agent`'s per-patch revert, `foreman`'s patch lane) each
protect one narrow operation.

The gap the Eli Felse Base project fills with nightly backups and named saves is the same gap
here, and the reason it matters is the reason everything else in this layer matters: the export
repo is a fine backup for anything that was COMMITTED, and no backup at all for the window
between an irreversible act and the next commit.

THREE INDEPENDENT SYSTEMS, per the standing doctrine:

  1. TAKE ONE FIRST. `before("withdraw-chapters", paths)` copies the targets under
     `state/snapshots/<label>-<n>/` and records a manifest of what it took.
  2. PROVE IT RESTORES. `verify(sid)` restores into a TEMPORARY directory and compares bytes.
     An untested backup is a belief, not a backup -- and it is the specific kind of belief that
     is only discovered to be false at the worst possible moment.
  3. NEVER SILENTLY. A snapshot that fails to take is an OPERATOR-level refusal, not a warning
     printed above the destructive step that then proceeds anyway.

Deliberately dumb: file copies and a JSON manifest, no compression, no dedup, no rotation
cleverness. A restore path with logic in it is a restore path that can be wrong.
"""
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence  # noqa: E402

ROOT = os.path.join(HERE, "state", "snapshots")


class SnapshotFailed(RuntimeError):
    """The copy did not happen. The destructive step must not proceed."""


def _rel(p):
    """An absolute path -> its path relative to the repository root. REFUSES anything outside it.

    THE CONTAINMENT CHECK IS THE POINT, and it was missing. This was a bare `os.path.relpath(p,
    HERE)`, which cheerfully answers `../some/other/file.txt` for a path outside the repository
    -- and every consumer of that answer JOINS it onto a directory:

      * `before()` joins it onto `state/snapshots/<sid>/`, so the copy lands OUTSIDE the
        snapshot's own folder. Two snapshots of the same out-of-tree path then collide at one
        shared location under `state/snapshots/`, each overwriting the other's copy.
      * `restore(sid, into=tmp)` joins it onto the temp directory and writes OUTSIDE it, so
        `verify()`'s `finally: shutil.rmtree(tmp)` does not remove what it wrote.
      * `restore(sid)` with its default `into=HERE` writes outside the repository altogether.
      * and `verify()` then compares the two escaped copies to each other and returns True, so
        the escape is certified rather than caught.

    Demonstrated end to end (order ca3452eb9d49) with a file under %TEMP%. Latent today --
    the one live caller passes the in-tree relative `output/index/catalog.json` -- but `before()`
    documents and implements absolute-path support, and this is the module that gates
    irreversible acts, so the latent case is the whole exposure.

    REFUSED RATHER THAN REWRITTEN. Silently re-rooting an out-of-tree path under the snapshot
    directory would take the copy and then restore it to the wrong place, which is a worse
    failure than not taking it: the caller would be told it had a backup of a file it cannot get
    back. An absolute path that IS under `HERE` is still accepted, exactly as documented.
    """
    p = os.path.abspath(p)
    try:
        rel = os.path.relpath(p, HERE)
    except ValueError as e:
        # Windows: `relpath` raises outright across drive letters. Same verdict, said plainly.
        raise SnapshotFailed(
            "%s is not on the same drive as the repository root %s, so it has no path relative "
            "to it and cannot be snapshotted here (%s)" % (p, HERE, e)) from e
    if rel == os.pardir or rel.startswith(os.pardir + os.sep) or os.path.isabs(rel):
        raise SnapshotFailed(
            "%s resolves OUTSIDE the repository root %s. A snapshot of it would be written "
            "outside state/snapshots/<id>/ and restored outside the directory it was restored "
            "into, and verify() would compare the two escaped copies and pass. Snapshot only "
            "paths under the tree." % (p, HERE))
    return rel.replace(os.sep, "/")


def before(label, paths, note="", allow_missing=False):
    """Copy `paths` (files or directories) aside. -> snapshot id. Raises if it cannot.

    RAISES rather than returning a falsy value, because the caller is about to do something
    irreversible and the one thing that must not happen is for a failed snapshot to read as a
    successful one at a glance.

    A PARTIAL SNAPSHOT REFUSES TOO, and until now only the empty one did (order f4193095edff).
    A missing path was `continue`d over: ask for four paths where one is a typo, a renamed
    directory, or a file not created yet, and this returned an id, `verify()` returned True, and
    the manifest recorded neither what was REQUESTED nor what was SKIPPED -- so the caller went
    ahead with an irreversible step holding part of what it asked for, with nothing anywhere
    naming the part it did not get. This module's own words for the empty case apply to the
    partial one unchanged: "an empty snapshot is not a safe snapshot, it is a missing one
    wearing the same name." An all-or-nothing refusal that only fires when NOTHING was captured
    is a check that fires only in the case nobody hits.

    `allow_missing=True` is for the caller who genuinely means "copy whichever of these exist",
    and it is opt-in because that is a claim only the caller can make. It suppresses the refusal
    and nothing else: `requested` and `skipped` go into the manifest either way, so what was not
    taken is on the record even when it was expected.
    """
    # THE ID HAS TO BE UNIQUE OR TWO SNAPSHOTS ARE ONE (order da72c19bef09). It was
    # `label + "-" + int(time.time())` -- a WHOLE-SECOND clock -- against
    # `os.makedirs(dest, exist_ok=True)`, so two `before()` calls with the same label in the same
    # second shared one directory: the second copytree wrote into the first's tree and the second
    # `_manifest.json` REPLACED the first's. The manifest is the only record of what a snapshot
    # holds (`restore` and `verify` read `m["took"]` and nothing else), so the first snapshot's
    # contents became unrestorable -- present on disk, invisible to the tool -- while `before()`
    # handed an id to both callers as though each had its own copy. `exist_ok=True` made that
    # collision silent BY CONSTRUCTION, in the module whose whole job is that an irreversible act
    # always has a copy behind it.
    #
    # Nanoseconds plus the pid: the clock separates two calls in one process, the pid separates
    # two processes that hit the same nanosecond. And `exist_ok=False`, so if the id ever DOES
    # collide the answer is SnapshotFailed -- already this module's contract for "the copy did
    # not happen" -- rather than a silent merge.
    sid = "%s-%d-%d" % (str(label or "snap").replace(os.sep, "_"),
                        time.time_ns(), os.getpid())
    dest = os.path.join(ROOT, sid)
    took, requested, skipped = [], [], []
    try:
        os.makedirs(ROOT, exist_ok=True)
        os.makedirs(dest, exist_ok=False)
        for p in paths or ():
            src = p if os.path.isabs(p) else os.path.join(HERE, p)
            requested.append(str(p))
            if not os.path.exists(src):
                skipped.append(str(p))
                continue
            rel = _rel(src)
            tgt = os.path.join(dest, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(tgt), exist_ok=True)
            if os.path.isdir(src):
                shutil.copytree(src, tgt, dirs_exist_ok=True)
            else:
                shutil.copy2(src, tgt)
            took.append(rel)
        # `requested` AND `skipped` ARE RECORDED WHETHER OR NOT THEY MATTER HERE. The refusal
        # below can be waived; the record cannot, because the manifest is the only thing a
        # restore six weeks from now has to tell it what this snapshot was supposed to hold.
        manifest = {"id": sid, "at": time.time(), "label": label, "note": note, "took": took,
                    "requested": requested, "skipped": skipped}
        # THROUGH `silence.write_json`, NOT A BARE open(..., "w") (order da72c19bef09). This was
        # the one unhardened write left in the kit. A bare open truncates BEFORE serialising, so
        # an interrupted flush leaves a snapshot whose FILES are all on disk and whose index is
        # 0 bytes: `manifest()` raises, `verify()` returns (False, "manifest unreadable"), and
        # `restore()` raises -- the copy taken before an irreversible step cannot be used, which
        # is precisely the failure this module was written to make impossible. health.py, read.py
        # and pipeline.py were all moved off that formula for the same reason.
        #
        # AND THE VERDICT IS NOT DISCARDED. `write_json` returns False rather than raising on a
        # denied replace, so the `except -> SnapshotFailed` wrapper around this block cannot see
        # it (the discarded-verdict shape health.py :846-876 was fixed for). A snapshot whose
        # manifest did not land is a snapshot that does not exist, so it raises.
        if not silence.write_json(os.path.join(dest, "_manifest.json"), manifest,
                                  indent=1, ensure_ascii=False):
            raise SnapshotFailed(
                "snapshot %r copied %d path(s) but its manifest could not be landed at %s. "
                "The manifest is the only record of what the copy holds -- restore() and "
                "verify() read nothing else -- so a snapshot without one cannot be used and "
                "must not be reported as taken."
                % (label, len(took), os.path.join(dest, "_manifest.json")))
    except SnapshotFailed:
        # Already the right exception with the right sentence -- re-wrapping it in the generic
        # one below would bury the manifest's specific failure inside "could not snapshot".
        raise
    except Exception as e:
        silence.note("snapshot.py:before")
        raise SnapshotFailed(
            "could not snapshot %r before a destructive step (%s: %s). The step must not "
            "proceed: an irreversible act with no copy behind it is the one thing this module "
            "exists to prevent." % (label, type(e).__name__, e)) from e
    if not took:
        raise SnapshotFailed(
            "snapshot %r captured NOTHING -- none of the given paths exist. An empty snapshot "
            "is not a safe snapshot, it is a missing one wearing the same name." % label)
    if skipped and not allow_missing:
        # AFTER the manifest is written, deliberately: the snapshot directory and its record of
        # what went wrong stay on disk for the operator to read, rather than the refusal erasing
        # its own evidence. The caller is stopped, which is the point; nothing is cleaned up
        # behind it, which is how they find out what was missing.
        raise SnapshotFailed(
            "snapshot %r captured %d of %d requested path(s) -- %s do(es) not exist. The "
            "irreversible step must not proceed on a partial copy: pass allow_missing=True if "
            "the absences are expected, or fix the path(s). Manifest: %s"
            % (label, len(took), len(requested), ", ".join(repr(s) for s in skipped),
               os.path.join(ROOT, sid, "_manifest.json")))
    return sid


def manifest(sid):
    with open(os.path.join(ROOT, sid, "_manifest.json"), encoding="utf-8") as f:
        return json.load(f)


def _dir_matches(a, b):
    """-> (ok, why) for a snapshotted DIRECTORY, compared file by file, bytes and all.

    THE HOLE THIS FILLS, found by the run33 sweep (order e5116f51c82a). `verify()` compared
    bytes only under `os.path.isfile(a)`, so when the snapshotted path was a DIRECTORY -- which
    is what `before()` takes through `shutil.copytree`, and what a caller about to withdraw a
    folder of chapters actually snapshots -- the only check left standing was `os.path.exists(b)`,
    which is true of any directory whatever is or is not inside it. A restore that dropped,
    truncated or corrupted every file beneath it still reported "N path(s) restored and
    byte-identical". That is this module's own stated failure: an untested backup is a belief,
    and a verify that cannot fail is how the belief gets held.

    Walks the SNAPSHOT side, because the snapshot is the thing being proved restorable: every
    file it holds must be present and identical on the restored side. Deliberately dumb like the
    rest of this module -- no `dircmp` heuristics and no shallow compare, since a stat-only
    match is exactly the answer a truncated restore would give.
    """
    import filecmp
    for root, _dirs, files in os.walk(a):
        for name in files:
            fa = os.path.join(root, name)
            sub = os.path.relpath(fa, a).replace(os.sep, "/")
            fb = os.path.join(b, os.path.relpath(fa, a))
            if not os.path.isfile(fb):
                return False, "restore omitted %s" % sub
            if not filecmp.cmp(fa, fb, shallow=False):
                return False, "restored bytes differ for %s" % sub
    return True, ""


def verify(sid):
    """-> (ok, detail). Restore into a TEMP directory and compare bytes against the snapshot.

    Restoring somewhere harmless is the whole point. A `verify` that checked the live tree would
    pass whenever the destructive step had not run yet, which is exactly when it is called.
    """
    import filecmp
    import tempfile
    try:
        m = manifest(sid)
    except Exception as e:
        return False, "manifest unreadable: %s" % type(e).__name__
    tmp = tempfile.mkdtemp(prefix="snapverify_")
    try:
        n = restore(sid, into=tmp)
        for rel in m.get("took", []):
            a = os.path.join(ROOT, sid, rel.replace("/", os.sep))
            b = os.path.join(tmp, rel.replace("/", os.sep))
            if not os.path.exists(b):
                return False, "restore omitted %s" % rel
            if os.path.isfile(a) and not filecmp.cmp(a, b, shallow=False):
                return False, "restored bytes differ for %s" % rel
            # A directory's existence says nothing about its contents; `_dir_matches` reads them.
            if os.path.isdir(a):
                dir_ok, why = _dir_matches(a, b)
                if not dir_ok:
                    return False, "inside %s: %s" % (rel, why)
        return True, "%d path(s) restored and byte-identical" % n
    except Exception as e:
        return False, "restore raised %s: %s" % (type(e).__name__, e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _safe_join(base, rel):
    """`os.path.join(base, rel)`, refusing any `rel` that climbs out of `base`.

    THE SECOND HALF OF `_rel`'s CONTAINMENT CHECK (order ca3452eb9d49). Guarding `before()` stops
    an escaping path being TAKEN; this stops one already recorded from being WRITTEN, and there
    are two ways for one to exist: a manifest written before `_rel` refused, and a manifest
    edited by hand. `restore()`'s default `into` is the live repository root, so an unguarded
    `..` in `took` is an arbitrary write outside the tree performed by the module whose job is
    to make destructive steps reversible.
    """
    tgt = os.path.abspath(os.path.join(base, rel.replace("/", os.sep)))
    root = os.path.abspath(base)
    if tgt != root and not tgt.startswith(root + os.sep):
        raise SnapshotFailed(
            "manifest entry %r resolves to %s, which is outside %s. Refusing to restore it: a "
            "restore that writes outside the directory it was given is not a restore."
            % (rel, tgt, root))
    return tgt


def restore(sid, into=None):
    """Copy a snapshot back. `into` defaults to the live tree -- pass a temp dir to test it.
    -> the number of paths restored. RAISES SnapshotFailed if any of the manifest's `took`
    entries could not be copied back -- it does not silently return fewer than it promised.

    A SNAPSHOT PARTLY LOST BETWEEN CAPTURE AND RESTORE (files deleted, moved, or never fully
    copied) used to be a `continue` here: the loop just skipped whatever `os.path.exists(src)`
    said no to, and the only signal was the returned count being smaller than `len(m['took'])`
    -- which nothing compared. `verify()` catches this because it independently walks
    `m['took']` itself and checks every path exists in the restored copy, but `verify()` restores
    into a TEMP directory; `restore(sid)` with its default `into=HERE` is the actual recovery
    after an irreversible step, and until now that path had no such check at all. Same shape
    `before()` was hardened against under order f4193095edff, arriving from the restore end
    instead of the capture end (order 9681220bad8f). `SnapshotFailed` is already this module's
    word for "the copy did not happen" -- a restore that silently returns part of a snapshot
    deserves the same refusal `before()` gives a capture that silently takes part of one.
    """
    base = into or HERE
    m = manifest(sid)
    n = 0
    missing = []
    for rel in m.get("took", []):
        src = _safe_join(os.path.join(ROOT, sid), rel)
        tgt = _safe_join(base, rel)
        if not os.path.exists(src):
            missing.append(rel)
            continue
        os.makedirs(os.path.dirname(tgt), exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, tgt, dirs_exist_ok=True)
        else:
            shutil.copy2(src, tgt)
        n += 1
    if missing:
        raise SnapshotFailed(
            "restore(%r) is missing %d of %d manifest path(s) that its own record says it took: "
            "%s. The snapshot on disk no longer matches its manifest; restoring the rest and "
            "saying nothing would read as a whole recovery when it is a partial one."
            % (sid, len(missing), len(m.get("took", [])), ", ".join(missing)))
    return n


def listing():
    out = []
    if not os.path.isdir(ROOT):
        return out
    for sid in sorted(os.listdir(ROOT)):
        try:
            out.append(manifest(sid))
        except Exception:
            out.append({"id": sid, "broken": True})
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--verify", help="snapshot id, or 'all'")
    a = ap.parse_args()
    if a.verify:
        ids = [m["id"] for m in listing()] if a.verify == "all" else [a.verify]
        bad = 0
        for sid in ids:
            ok, why = verify(sid)
            print("  %-40s %s  %s" % (sid, "OK " if ok else "FAILED", why))
            bad += 0 if ok else 1
        print("\n%d snapshot(s), %d failed to restore" % (len(ids), bad))
        return 1 if bad else 0
    for m in listing():
        print("  %-40s %s  %s" % (m.get("id"), len(m.get("took") or []), m.get("label", "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
