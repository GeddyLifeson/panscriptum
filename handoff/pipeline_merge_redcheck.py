"""Prove the write_record top-key fix, and watch the OLD behaviour lose the data.

Found by the run #36 whole-tree sweep (batch 3): `pipeline.write_record` carried the unguarded
version of the exact defect that produced the standing BLOCKING order 3c7c8a6e9102, in BOTH of
its paths -- the drift branch overwrote every non-`entries` key from the stale in-memory copy
with no None-guard, and the no-drift fast path wrote that copy WHOLE and never merged at all.
The sibling writer `write_record_catalogue` was fixed for this on 2026-08-25; this one was not.

Six arms, and the ones after the second are what make this evidence rather than assertion:

  1. NO DRIFT, disk holds a key the caller left None      -> the disk value must survive
  2. DRIFT,    disk holds a key the caller left None      -> the disk value must survive
  3. an EXPLICIT empty value ("" / {} / []) still CLEARS  -> the escape hatch must still work
  4. a caller's real value still WINS                     -> the fix must not freeze the record
  5. NO DRIFT, the caller's per-entry JUDGMENTS reach disk -> the fold runs on the fast path
  6. DRIFT,    the caller's per-entry JUDGMENTS reach disk -> and on the merge path too

Plus two controls, one per direction the writer can break:

  A. the old unguarded top-key merge restored   -> arms 1 and 2 must FAIL
  B. the per-entry fold back inside `if drift:` -> arm 5 must FAIL, arm 6 must NOT

ARM 5 AND CONTROL B ARE ORDER f3536eed6ce0, AND THE ORDER IS ABOUT THIS FILE'S OWN BLIND SPOT.
Every arm above used ENTRIES = [{"name": "Alpha"}, {"name": "Beta"}] on BOTH sides of the round
trip -- entries carrying no per-entry judgment field at all. So when the run-36 top-key repair
introduced a second defect (the no-drift fast path wrote the caller's copy whole and folded no
judgments onto the disk cast), not one arm here could observe it: there was no judgment in the
fixture to lose. Measured live afterwards at 20 entries judged, 0 of 20 settled on disk, and
1,496 recorded `done.entrypass` spans unsettled. A proof that is structurally unable to fail in
the direction a change broke is a check that cannot fail, which is this project's oldest lesson
wearing a red-check's clothes.

The judgment defect is FIXED in `pipeline.write_record` as of run #37 -- the fold is hoisted
above the `if drift:` -- so arm 5 goes GREEN against current code, as it should. Control B is
what keeps it honest: it restores the pre-hoist shape and requires arm 5 to go red against it.
An arm nothing can make fail proves nothing whichever colour it prints.
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

# The per-entry fields `write_record` is contracted to fold from the caller's copy onto the disk
# cast. Named here rather than spelled out in arm 5 so the arm tests the contract rather than one
# hand-picked field.
#
# AND THE LIST IS NOW THE WRITER'S OWN, not a copy of it (order 776507b529c5). This was five
# literal keys and the writer folds six -- `scale_note_rejected` was missing, so the one judgment
# field that records a REJECTED reading, and therefore the one whose loss looks most like a clean
# record, was outside the fixture. Reading `P.MERGED_ENTRY_FIELDS` means a field added to the
# writer is covered here the day it is added rather than the day someone remembers this file:
# a check whose fixture is simpler than the data is a check that cannot fail in exactly the
# direction the code can break, which is the finding this whole arm exists for. Unknown fields
# get a generic authored value, because what is being proved is that the fold RUNS, not what any
# particular field means.
_JUDGMENT_VALUES = {
    "category": "person",
    "scale_note": "settled by the entrypass",
    "scale_note_rejected": "M9 -- rejected: no cited feat supports it",
    "magnitude": "M4",
    "topic": "the worked example",
    "catalogued": True,
}
JUDGMENTS = {f: _JUDGMENT_VALUES.get(f, "authored by the caller for %s" % f)
             for f in P.MERGED_ENTRY_FIELDS}


def arm(label, disk_doc, rec, check, writer=None):
    """One round trip through `writer` (default: the real `pipeline.write_record`).

    `writer` exists so a control can run the SAME arms through a reconstruction of the older
    shape; nothing in the arms themselves knows which writer they are proving.
    """
    d, p = scratch(disk_doc)
    try:
        (writer or P.write_record)(p, json.loads(json.dumps(rec)))
        got = read(p)
        ok = check(got)
        print("  %-58s %s" % (label, "PASS" if ok else "FAIL"))
        return ok
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _writer_before_the_hoist(path, rec):
    """`pipeline.write_record` as it stood BETWEEN the run-36 top-key repair and the run-37 fold
    hoist: identical in every respect except that the per-entry judgment fold sits back inside
    `if drift:`, which is where it was when 1,496 entrypass spans failed to settle.

    Reconstructed here rather than monkeypatched, because the fold is inline in the real function
    and there is no seam to replace -- the same technique as `unguarded` below, which restores the
    old `_merge_top_keys` by substitution. The atomic temp-and-rename is not reproduced: this
    writes straight to the scratch path, because what the control has to reproduce is the MERGE,
    and how the bytes land is a different property with its own checks.
    """
    merged = rec
    try:
        with open(path, encoding="utf-8") as fh:
            disk = json.load(fh)
        n_disk, n_mem = len(disk.get("entries") or []), len(rec.get("entries") or [])
        drift = ("count" if n_disk != n_mem else
                 "content" if P._entry_digest(disk) != P._entry_digest(rec) else None)
        if drift:                                    # <-- THE DEFECT: the fold was gated on this
            by_name = {e.get("name"): e for e in rec.get("entries") or []}
            for de in disk.get("entries") or []:
                se = by_name.get(de.get("name"))
                if not se:
                    continue
                # The writer's own field list, for the reason given at JUDGMENTS: a control that
                # folds a different set from the real writer is not reproducing the old shape,
                # it is inventing a third one.
                for fld in P.MERGED_ENTRY_FIELDS:
                    if fld in se:
                        de[fld] = se[fld]
        P._merge_top_keys(disk, rec, os.path.basename(path))
        merged = disk
    except FileNotFoundError:
        pass
    except Exception:
        return False
    P.stamp_record(merged, "pipeline.write_record")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=2, ensure_ascii=False)
    return True


def _judged(got):
    """Did every judgment the caller authored reach the disk copy of the entry it belongs to?"""
    by_name = {e.get("name"): e for e in got.get("entries") or []}
    alpha = by_name.get("Alpha") or {}
    return all(alpha.get(k) == v for k, v in JUDGMENTS.items())


def run_all(writer=None):
    results = []

    # 1 -- no drift (same entry names), caller leaves synthesis unauthored.
    results.append(arm(
        "1  no drift: disk synthesis survives a None from the caller",
        {"entries": ENTRIES, "synthesis": {"ceiling_entity": "Superman"}, "mode": "web"},
        {"entries": ENTRIES, "synthesis": None},
        lambda g: (g.get("synthesis") or {}).get("ceiling_entity") == "Superman"
        and g.get("mode") == "web", writer))

    # 2 -- drift (disk has an extra entry), same question.
    results.append(arm(
        "2  drift: disk synthesis survives a None from the caller",
        {"entries": ENTRIES + [{"name": "Gamma"}],
         "synthesis": {"ceiling_entity": "Superman"}},
        {"entries": ENTRIES, "synthesis": None},
        lambda g: (g.get("synthesis") or {}).get("ceiling_entity") == "Superman"
        and len(g.get("entries") or []) == 3, writer))

    # 3 -- an explicit empty value must still CLEAR. The escape hatch matters: without it the
    #      guard would make a key impossible to remove, which is its own defect.
    results.append(arm(
        "3  an explicit empty value still clears the disk value",
        {"entries": ENTRIES, "synthesis": {"ceiling_entity": "Superman"}},
        {"entries": ENTRIES, "synthesis": {}},
        lambda g: g.get("synthesis") == {}, writer))

    # 4 -- a real authored value must still win, or the record freezes.
    results.append(arm(
        "4  a caller's real value still overwrites the disk value",
        {"entries": ENTRIES, "synthesis": {"ceiling_entity": "Superman"}},
        {"entries": ENTRIES, "synthesis": {"ceiling_entity": "Doomsday"}},
        lambda g: g["synthesis"]["ceiling_entity"] == "Doomsday", writer))

    # 5 -- NO DRIFT, and the caller has judged an entry. Same entry NAMES on both sides, which is
    #      what `_entry_digest` decides drift on and what phase 2 produces every single time:
    #      `phase_entrypass` fills in bands and notes and never renames anybody. So this is the
    #      ORDINARY path, not a corner, and the judgments must be on disk afterwards.
    results.append(arm(
        "5  no drift: the caller's per-entry judgments reach disk",
        {"entries": [{"name": "Alpha"}, {"name": "Beta"}],
         "synthesis": {"ceiling_entity": "Superman"}},
        {"entries": [dict({"name": "Alpha"}, **JUDGMENTS), {"name": "Beta"}],
         "synthesis": None},
        _judged, writer))

    # 6 -- DRIFT, and the caller has judged an entry. Order 776507b529c5 asks for both paths to
    #      be asserted, and only arm 5 was: the fold sat inside `if drift:` for a whole run, so
    #      "it works on the drift path" was an assumption inherited from the shape of the bug
    #      rather than a measurement. It is also the arm that would catch the OPPOSITE mistake --
    #      a future repair that hoists the fold out of `if drift:` and, in doing so, drops it
    #      from the drift path. Disk has an entry the caller does not, which is what
    #      `_entry_digest` calls count drift; Alpha's judgments must still be on disk after.
    results.append(arm(
        "6  drift:    the caller's per-entry judgments reach disk",
        {"entries": [{"name": "Alpha"}, {"name": "Beta"}, {"name": "Gamma"}],
         "synthesis": {"ceiling_entity": "Superman"}},
        {"entries": [dict({"name": "Alpha"}, **JUDGMENTS), {"name": "Beta"}],
         "synthesis": None},
        lambda g: _judged(g) and len(g.get("entries") or []) == 3, writer))

    return results


def main():
    print("WITH THE FIX")
    ok = all(run_all())

    print("\nCONTROL A -- the old unguarded merge restored (arms 1 and 2 must go RED)")
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
    print("\n  control A arms 1-2 went red:", red)

    # CONTROL B -- the fold back inside `if drift:`. Arm 5 is the only arm this can move, and it
    # must move: an arm that stays green against the very shape that produced the defect is not
    # evidence about the fold, it is evidence that the fixture has no judgment in it. That was
    # the whole finding of order f3536eed6ce0.
    print("\nCONTROL B -- the per-entry fold back inside `if drift:` (arm 5 must go RED)")
    control_b = run_all(writer=_writer_before_the_hoist)
    # ARM 5 RED, ARM 6 GREEN, and BOTH are required. Arm 6 staying green under the old shape is
    # not a weakness in the control, it is the control's precision: the pre-hoist writer folded
    # correctly whenever there WAS drift, and a control that reddened both arms would be
    # reproducing something other than the defect that lost 1,496 spans.
    red5 = control_b[4] is False and control_b[5] is True
    print("\n  control B arm 5 went red and arm 6 stayed green:", red5)

    good = ok and red and red5
    print("\nVERDICT:", "the top-key guard and the per-entry fold both hold and are load-bearing"
          if good else "NOT PROVEN -- do not rely on this fix")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
