"""Prove the write_record top-key fix, and watch the OLD behaviour lose the data.

Found by the run #36 whole-tree sweep (batch 3): `pipeline.write_record` carried the unguarded
version of the exact defect that produced the standing BLOCKING order 3c7c8a6e9102, in BOTH of
its paths -- the drift branch overwrote every non-`entries` key from the stale in-memory copy
with no None-guard, and the no-drift fast path wrote that copy WHOLE and never merged at all.
The sibling writer `write_record_catalogue` was fixed for this on 2026-08-25; this one was not.

Four arms, and the last two are the ones that make it evidence rather than assertion:

  1. NO DRIFT, disk holds a key the caller left None      -> the disk value must survive
  2. DRIFT,    disk holds a key the caller left None      -> the disk value must survive
  3. an EXPLICIT empty value ("" / {} / []) still CLEARS  -> the escape hatch must still work
  4. a caller's real value still WINS                     -> the fix must not freeze the record

Plus the control: with the old unguarded merge restored, arm 1 and arm 2 must FAIL.
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import pipeline as P  # noqa: E402


def scratch(disk_doc):
    d = tempfile.mkdtemp(prefix="pipemerge_")
    p = os.path.join(d, "source.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(disk_doc, fh)
    return d, p


def read(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


ENTRIES = [{"name": "Alpha"}, {"name": "Beta"}]


def arm(label, disk_doc, rec, check):
    d, p = scratch(disk_doc)
    try:
        P.write_record(p, json.loads(json.dumps(rec)))
        got = read(p)
        ok = check(got)
        print("  %-58s %s" % (label, "PASS" if ok else "FAIL"))
        return ok
    finally:
        shutil.rmtree(d, ignore_errors=True)


def run_all():
    results = []

    # 1 -- no drift (same entry names), caller leaves synthesis unauthored.
    results.append(arm(
        "1  no drift: disk synthesis survives a None from the caller",
        {"entries": ENTRIES, "synthesis": {"ceiling_entity": "Superman"}, "mode": "web"},
        {"entries": ENTRIES, "synthesis": None},
        lambda g: (g.get("synthesis") or {}).get("ceiling_entity") == "Superman"
        and g.get("mode") == "web"))

    # 2 -- drift (disk has an extra entry), same question.
    results.append(arm(
        "2  drift: disk synthesis survives a None from the caller",
        {"entries": ENTRIES + [{"name": "Gamma"}],
         "synthesis": {"ceiling_entity": "Superman"}},
        {"entries": ENTRIES, "synthesis": None},
        lambda g: (g.get("synthesis") or {}).get("ceiling_entity") == "Superman"
        and len(g.get("entries") or []) == 3))

    # 3 -- an explicit empty value must still CLEAR. The escape hatch matters: without it the
    #      guard would make a key impossible to remove, which is its own defect.
    results.append(arm(
        "3  an explicit empty value still clears the disk value",
        {"entries": ENTRIES, "synthesis": {"ceiling_entity": "Superman"}},
        {"entries": ENTRIES, "synthesis": {}},
        lambda g: g.get("synthesis") == {}))

    # 4 -- a real authored value must still win, or the record freezes.
    results.append(arm(
        "4  a caller's real value still overwrites the disk value",
        {"entries": ENTRIES, "synthesis": {"ceiling_entity": "Superman"}},
        {"entries": ENTRIES, "synthesis": {"ceiling_entity": "Doomsday"}},
        lambda g: g["synthesis"]["ceiling_entity"] == "Doomsday"))

    return results


def main():
    print("WITH THE FIX")
    ok = all(run_all())

    print("\nCONTROL -- the old unguarded merge restored (arms 1 and 2 must go RED)")
    real = P._merge_top_keys

    def unguarded(disk, rec, label):
        for key, val in rec.items():
            if key != "entries":
                disk[key] = val
        return []

    P._merge_top_keys = unguarded
    control = run_all()
    P._merge_top_keys = real
    red = (control[0] is False) and (control[1] is False)
    print("\n  control arms 1-2 went red:", red)

    good = ok and red
    print("\nVERDICT:", "the top-key guard holds and is load-bearing" if good
          else "NOT PROVEN -- do not rely on this fix")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
