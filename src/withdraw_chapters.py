"""Withdraw generated chapters from the library, preserving them for the record.

OWNER RULING 2026-08-25: the 145 chapters written while the prose gate was inverted are
withdrawn. They were produced for sources running 0.0%-9.0% cited, 71% of their entries lost the
Threads section the template requires, and some carry Instrument axis scores with no assay behind
them (see BUGS M25/M26/M27).

MOVES, DOES NOT UNLINK. Regenerating them costs real model time, and `generate.py` is resumable
and content-hashed -- once a source's citations improve, its jobs re-run as stale anyway. So the
withdrawn set goes to `output/withdrawn_<date>/` where it is out of the library but still on
disk. Purging it is a separate, deliberate act.

Usage:  python src/withdraw_chapters.py --go [--label 2026-08-25]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true", help="actually move; otherwise dry-run")
    # NOT A FIXED DATE (found run35, batch 6). This defaulted to "2026-08-25" -- the day of the
    # withdrawal that motivated writing this script -- so a second, unrelated `--go` with no
    # `--label` would move its files into that SAME `output/withdrawn_2026-08-25/` archive,
    # which already held 148 files and, because this script MOVES rather than copies, is the
    # only copy of them. Two withdrawals sharing one archive directory is exactly the collision
    # the unguarded `shutil.move` sweep further down has no guard against. The default is now
    # today's date, computed when the tool runs rather than baked in when it was written.
    ap.add_argument("--label", default=datetime.date.today().isoformat())
    a = ap.parse_args()

    arch = os.path.join(HERE, "output", "withdrawn_" + a.label)
    with open(CATALOG, encoding="utf-8") as f:
        cat = json.load(f)
    print("catalog entries: %d" % len(cat))

    if a.go:
        # A COPY BEFORE THE IRREVERSIBLE STEP. This script moves rather than unlinks, which was
        # the right instinct when it was written -- but the instinct was the ONLY thing standing
        # behind 145 chapters. A snapshot that fails RAISES, so the withdrawal cannot proceed
        # believing it has a copy behind it when it does not.
        import snapshot as SNAP
        sid = SNAP.before("withdraw-chapters", ["output/index/catalog.json"],
                          note="catalog before withdrawing %d chapters" % len(cat))
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
    for _addr, rec in cat.items():
        for key, sub in (("raw_path", "raw"), ("compressed_path", "compressed")):
            src = _abs(rec.get(key))
            if not src or not os.path.exists(src):
                missing += 1
                continue
            if a.go:
                try:
                    shutil.move(src, os.path.join(arch, sub, os.path.basename(src)))
                except Exception as e:
                    print("  move failed: %s (%s)" % (src, e))
                    continue
            moved[sub] += 1

    # Anything left in output/raw that the catalog never claimed -- the pilot's strays.
    extra = 0
    rawdir = os.path.join(HERE, "output", "raw")
    if os.path.isdir(rawdir):
        for f in sorted(os.listdir(rawdir)):
            src = os.path.join(rawdir, f)
            if not os.path.isfile(src):
                continue
            if a.go:
                shutil.move(src, os.path.join(arch, "raw", f))
            extra += 1

    catalog_landed = True
    if a.go:
        # The withdrawn catalog is the record of WHAT was withdrawn; keep it beside the files.
        shutil.copy(CATALOG, os.path.join(arch, "catalog.withdrawn.json"))
        # ATOMIC, AND THE VERDICT KEPT. This ran AFTER every chapter file above has already
        # been moved, on the one file generate.py and publish.py both read -- same collision
        # hazard as scout._land, on a shared file. The hand-rolled `CATALOG + ".tmp"` plus a
        # dropped `silence.replace_retry` return meant a denied replace (a reader holding
        # catalog.json open, this module's normal situation) left the catalog claiming every
        # withdrawn chapter still lives where the files just moved away from, with nothing
        # raising to say so.
        catalog_landed = silence.write_json(CATALOG, {}, indent=2)

    print("raw moved         : %d  (+%d unclaimed by the catalog)" % (moved["raw"], extra))
    print("compressed moved  : %d" % moved["compressed"])
    print("paths already gone: %d" % missing)
    if a.go:
        if not catalog_landed:
            print("CATALOG WRITE DENIED: %s still lists the paths just moved away -- "
                  "replace refused, retry this run" % CATALOG)
        with open(CATALOG, encoding="utf-8") as f:
            print("catalog now       : %d entries" % len(json.load(f)))
        print("archive           : %s" % arch)
    else:
        print("DRY RUN -- pass --go to move")


if __name__ == "__main__":
    main()
