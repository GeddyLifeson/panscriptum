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


def members():
    """Every canonical file, as (repo-relative path, absolute path). -> [(rel, abs)].

    NO CAP AND NO SAMPLE. The whole point is that the set is complete; a backup that quietly
    covered the first N records would restore a smaller library than the one that was lost, and
    would look exactly like a backup that worked.
    """
    out = []
    for rel in CANON_FILES:
        p = os.path.join(HERE, rel.replace("/", os.sep))
        if os.path.isfile(p):
            out.append((rel, p))
    for rel in CANON_DIRS:
        d = os.path.join(HERE, rel.replace("/", os.sep))
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name.endswith(".json"):
                out.append((rel + "/" + name, os.path.join(d, name)))
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
        raise RuntimeError("%d canonical file(s) could not be read: %s"
                           % (len(missing), ", ".join(missing[:5])))

    tmp = os.path.join(ROOT, "_writing-%s.zip" % stamp)
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
        raise RuntimeError("snapshot failed verification and was deleted: %s" % "; ".join(bad[:5]))

    final = os.path.join(ROOT, "canon-%s.zip" % stamp)
    if silence.replace_retry(tmp, final) is False:
        raise RuntimeError("snapshot could not be renamed into place: %s" % final)

    manifest = {"stamp": stamp, "files": len(items), "bytes": os.path.getsize(final),
                "verified": True, "digests": sources}
    silence.replace_retry(*_write_manifest(final, manifest))
    return final, manifest


def _write_manifest(final, manifest):
    """-> (tmp, dst) for the manifest beside a snapshot, already written to tmp."""
    dst = final[:-4] + ".manifest.json"
    tmp = dst + ".writing"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    return tmp, dst


def prune(keep=KEEP):
    """Delete all but the newest `keep` snapshots. -> [removed stamps].

    Age-ordered by NAME, which is the timestamp, not by mtime -- mtime moves when a file is
    touched and this must not be able to decide that the newest snapshot is the oldest one.
    """
    if not os.path.isdir(ROOT):
        return []
    snaps = sorted(f for f in os.listdir(ROOT)
                   if f.startswith("canon-") and f.endswith(".zip"))
    removed = []
    for f in snaps[:-keep] if keep > 0 else []:
        for p in (os.path.join(ROOT, f),
                  os.path.join(ROOT, f[:-4] + ".manifest.json")):
            try:
                if os.path.isfile(p):
                    os.remove(p)
            except OSError:
                silence.note("canon_backup.py:prune-denied:" + f)
        removed.append(f)
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
    """
    path = path or newest()
    notes = []
    if not path or not os.path.isfile(path):
        return False, ["no snapshot exists"]
    man = path[:-4] + ".manifest.json"
    recorded = {}
    if os.path.isfile(man):
        with open(man, encoding="utf-8") as fh:
            recorded = (json.load(fh) or {}).get("digests") or {}
    try:
        with zipfile.ZipFile(path) as z:
            broken = z.testzip()
    except (OSError, zipfile.BadZipFile) as e:
        return False, ["archive unreadable: %s" % e]
    if broken:
        return False, ["archive corrupt at member %s" % broken]
    live = {rel: digest(p) for rel, p in members()}
    changed = [r for r, d in live.items() if recorded.get(r) and d != recorded[r]]
    added = [r for r in live if r not in recorded]
    gone = [r for r in recorded if r not in live]
    notes.append("archive intact, %d members" % len(recorded))
    notes.append("%d canonical files changed since the snapshot" % len(changed))
    if added:
        notes.append("%d canonical files are new since the snapshot" % len(added))
    if gone:
        notes.append("%d canonical files present in the snapshot are GONE from the live tree: %s"
                     % (len(gone), ", ".join(sorted(gone)[:5])))
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

    items = members()
    print("%d canonical files, %.1f MB live"
          % (len(items), sum(os.path.getsize(p) for _r, p in items) / 1e6))
    n = newest()
    print("newest snapshot:", n or "NONE -- the canonical corpus is unbacked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
