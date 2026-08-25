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
    p = os.path.abspath(p)
    return os.path.relpath(p, HERE).replace(os.sep, "/")


def before(label, paths, note=""):
    """Copy `paths` (files or directories) aside. -> snapshot id. Raises if it cannot.

    RAISES rather than returning a falsy value, because the caller is about to do something
    irreversible and the one thing that must not happen is for a failed snapshot to read as a
    successful one at a glance.
    """
    sid = "%s-%d" % (str(label or "snap").replace(os.sep, "_"), int(time.time()))
    dest = os.path.join(ROOT, sid)
    took = []
    try:
        os.makedirs(dest, exist_ok=True)
        for p in paths or ():
            src = p if os.path.isabs(p) else os.path.join(HERE, p)
            if not os.path.exists(src):
                continue
            rel = _rel(src)
            tgt = os.path.join(dest, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(tgt), exist_ok=True)
            if os.path.isdir(src):
                shutil.copytree(src, tgt, dirs_exist_ok=True)
            else:
                shutil.copy2(src, tgt)
            took.append(rel)
        manifest = {"id": sid, "at": time.time(), "label": label, "note": note, "took": took}
        with open(os.path.join(dest, "_manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=1, ensure_ascii=False)
    except Exception as e:
        silence.note("snapshot.py:before")
        raise SnapshotFailed(
            "could not snapshot %r before a destructive step (%s: %s). The step must not "
            "proceed: an irreversible act with no copy behind it is the one thing this module "
            "exists to prevent." % (label, type(e).__name__, e))
    if not took:
        raise SnapshotFailed(
            "snapshot %r captured NOTHING -- none of the given paths exist. An empty snapshot "
            "is not a safe snapshot, it is a missing one wearing the same name." % label)
    return sid


def manifest(sid):
    with open(os.path.join(ROOT, sid, "_manifest.json"), encoding="utf-8") as f:
        return json.load(f)


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
        return True, "%d path(s) restored and byte-identical" % n
    except Exception as e:
        return False, "restore raised %s: %s" % (type(e).__name__, e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def restore(sid, into=None):
    """Copy a snapshot back. `into` defaults to the live tree -- pass a temp dir to test it."""
    base = into or HERE
    m = manifest(sid)
    n = 0
    for rel in m.get("took", []):
        src = os.path.join(ROOT, sid, rel.replace("/", os.sep))
        tgt = os.path.join(base, rel.replace("/", os.sep))
        if not os.path.exists(src):
            continue
        os.makedirs(os.path.dirname(tgt), exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, tgt, dirs_exist_ok=True)
        else:
            shutil.copy2(src, tgt)
        n += 1
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
