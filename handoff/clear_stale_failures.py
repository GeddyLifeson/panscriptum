"""Remove synthesis-phase failure records for sources that now HAVE a synthesis.

A failure record for something that succeeded is not a cautious record, it is a false one:
`health.py --preflight` counts it as "failures recorded that already succeeded" and reports a
problem, which is correct -- the state file is claiming something untrue.

Two names qualify after the 2026-08-28 restore: `Marvel`, whose synthesis was re-derived and
merged tonight, and `Bone (Jeff Smith)`, whose record already carried one (its failure entry has
been stale for longer). Nothing else is touched -- in particular the 49 `entrypass` entries are
BATCH keys of the form `Source#offset`, not source names, and they are real outstanding failures.

WRITTEN UNDER COMPARE-AND-SWAP. `state/PIPELINE_STATE.json` is the pipeline's own file and the
pipeline is a running daemon. A blind read-modify-write here would be the exact lost-update this
project has been repairing all week, committed while tidying up after it. If the file changes
under this script it refuses and says so, rather than landing a stale copy.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import silence  # noqa: E402

STATE = os.path.join(HERE, "state", "PIPELINE_STATE.json")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    digest = silence.digest_of(STATE)
    with open(STATE, encoding="utf-8") as fh:
        st = json.load(fh)

    failed = (st.get("failed") or {}).get("synthesis") or {}
    drop = []
    for name in sorted(failed):
        p = os.path.join(HERE, "data", "records", slug(name) + ".json")
        if not os.path.isfile(p):
            print("  keep  %-24s (no record file -- not provably stale)" % name)
            continue
        with open(p, encoding="utf-8") as fh:
            rec = json.load(fh)
        if rec.get("synthesis"):
            drop.append(name)
            print("  DROP  %-24s (record now carries a synthesis)" % name)
        else:
            print("  keep  %-24s (still has no synthesis -- a real failure)" % name)

    if not drop:
        print("nothing stale; leaving the state file untouched")
        return 0

    for name in drop:
        failed.pop(name, None)
    st.setdefault("failed", {})["synthesis"] = failed

    tmp = STATE + ".stale.%d.tmp" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=2, ensure_ascii=False)
    ok, why = silence.replace_if_unchanged(tmp, STATE, digest)
    print("write:", "landed" if ok else "REFUSED -- " + str(why))
    if not ok:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return 1
    print("dropped %d stale synthesis failure(s)" % len(drop))
    return 0


if __name__ == "__main__":
    sys.exit(main())
