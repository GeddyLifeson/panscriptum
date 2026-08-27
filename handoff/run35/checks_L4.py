"""
PROPOSED verify_math / drill checks -- run35, batch L4.

NOT wired into verify_math.py or drill.py (orders forbid editing those two files this run).
Each block below is commented with the work order id it closes/guards and the target file it
exercises, and is written to be runnable standalone: `python handoff/run35/checks_L4.py` from
the repo root with `src` on the path. The coordinator (or whoever owns verify_math.py /
drill.py) can lift each block into the real suite.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "src")
sys.path.insert(0, SRC)

PASS, FAIL = [], []


def check(label, got, want, note=""):
    ok = got == want
    (PASS if ok else FAIL).append((label, got, want, note))
    mark = "OK  " if ok else "FAIL"
    print(f"  {mark} {label:<70} got={got!r:<10} want={want!r}")
    if note and not ok:
        print(f"       {note}")


# ============================================================ order 06ab9dec6fb6 / 3a48ca598e7f
# (tiers.py, navtree.py) -- a module must be loadable by file spec from a CLEAN interpreter,
# not just importable via `python src/<file>.py` (which puts src on sys.path implicitly and
# hides an `import silence` placed before the sys.path.insert that is supposed to resolve it).
import importlib.util


def loads_clean(modname, path):
    spec = importlib.util.spec_from_file_location(modname, path)
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
        return True
    except ModuleNotFoundError:
        return False


for _mod, _rel in (("tiers", "tiers.py"), ("navtree", "navtree.py")):
    check(f"{_rel} loads by file spec from a clean interpreter (sys.path untouched)",
          loads_clean(_mod, os.path.join(SRC, _rel)), True,
          note="import silence must sit AFTER sys.path.insert, not before it")


# ============================================================ order 18649050748c (tiers.py)
# HARD RULE 0: the unaddressed-shelf roster must never be truncated below its own count.
with open(os.path.join(SRC, "tiers.py"), encoding="utf-8") as _f:
    _tiers_src = _f.read()
check("tiers.py main() no longer slices the unaddressed roster with [:N]",
      "unaddressed[:" not in _tiers_src, True)


# ============================================================ order 05e21ca7f404 (navtree.py)
# HARD RULE 0 + "a finding nobody reads is a finding nobody has": the audit's problem list must
# print in full AND be persisted somewhere other than a scrolling console.
with open(os.path.join(SRC, "navtree.py"), encoding="utf-8") as _f:
    _navtree_src = _f.read()
check("navtree.py main() no longer slices the problem list with [:N]",
      "problems[:" not in _navtree_src, True)
check("navtree.py main() writes the audit result to a file every run",
      "NAVTREE_AUDIT" in _navtree_src and "silence.write_json" in _navtree_src, True)

_audit_out = os.path.join(HERE, "..", "..", "state", "NAVTREE_AUDIT.json")
check("state/NAVTREE_AUDIT.json exists (written by a prior `python src/navtree.py` run)",
      os.path.exists(_audit_out), True)


# ============================================================ order 11020c99f0f9 (roll.py)
# exclude() must never silently discard a corrected reason, and must never treat "no such
# source" the same as "already excluded, nothing to do".
#
# CAUTION FOR ANYONE REUSING THIS: exclude()'s `rows=` argument only overrides what is READ and
# matched -- it still calls silence.write_json(ROLL, rows, ...) against the real, hardcoded
# ROLL path whenever `changed` is True. Passing rows= is NOT a safe way to sandbox a test; you
# must also repoint the module's ROLL constant, as done below, or this test will overwrite
# data/SWEEP_ROLL.json with throwaway test rows (this happened once during this batch's own
# work and was recovered from a backup -- see AUDIT_L4.md).
import roll as RL  # noqa: E402

_real_roll_path = RL.ROLL
try:
    with tempfile.TemporaryDirectory() as _rtd:
        RL.ROLL = os.path.join(_rtd, "roll.json")

        _rows = [{"name": "CheckSourceA", "status": "out-of-scope", "note": "old reason"}]
        _changed = RL.exclude("CheckSourceA", "corrected reason", rows=_rows)
        check("exclude() persists a corrected note on an already-excluded source (returns True)",
              _changed, True)
        check("exclude() actually rewrote the note in place",
              _rows[0]["note"], "corrected reason")

        try:
            RL.exclude("NoSuchSourceAtAll", "some reason",
                       rows=[{"name": "Other", "status": "x"}])
            _raised = False
        except ValueError:
            _raised = True
        check("exclude() raises rather than silently no-opping on an unmatched name",
              _raised, True)
finally:
    RL.ROLL = _real_roll_path


# ============================================================ order b3da16ddfe64 (roll.py)
with open(os.path.join(SRC, "roll.py"), encoding="utf-8") as _f:
    _roll_src = _f.read()
check("roll.py's SWEEP_ROLL.json writer passes ensure_ascii=False (matches its siblings)",
      "silence.write_json(ROLL, rows, indent=2, ensure_ascii=False)" in _roll_src, True)


# ============================================================ order b9fe73c30bd2 (address_space.py)
# silence.note() tags must be stable content labels, not line numbers that rot on the next edit.
with open(os.path.join(SRC, "address_space.py"), encoding="utf-8") as _f:
    _as_src = _f.read()
import re as _re
_tags = _re.findall(r'silence\.note\("(address_space\.py:[^"]+)"\)', _as_src)
check("address_space.py has exactly 4 silence.note tags, all distinct",
      (len(_tags), len(set(_tags))), (4, 4), note=str(_tags))
check("none of address_space.py's silence.note tags are bare line numbers",
      any(_re.search(r":\d+$", t) for t in _tags), False, note=str(_tags))


# ============================================================ order 229259ca01f4 (endpoint.py)
import endpoint as EP  # noqa: E402

check("endpoint.exists_raw no longer exists (confirmed dead, zero callers repo-wide)",
      hasattr(EP, "exists_raw"), False)


# ============================================================ order c170b202b0d6 (resync_roll.py)
# A source resynced down to zero entries must not keep a stale "catalogued" status, and an
# owner exclusion must survive the same resync untouched.
import json

import resync_roll as RR  # noqa: E402

with tempfile.TemporaryDirectory() as _td:
    _records_dir = os.path.join(_td, "records")
    os.makedirs(_records_dir)
    _roll_path = os.path.join(_td, "roll.json")
    with open(_roll_path, "w", encoding="utf-8") as _f:
        json.dump([
            {"name": "PurgedCheck", "entry_count": 50, "status": "catalogued"},
            {"name": "ExcludedCheck", "entry_count": 5, "status": "out-of-scope",
             "note": "check"},
        ], _f)
    with open(os.path.join(_records_dir, "purgedcheck.json"), "w", encoding="utf-8") as _f:
        json.dump({"source": "PurgedCheck", "entries": []}, _f)
    with open(os.path.join(_records_dir, "excludedcheck.json"), "w", encoding="utf-8") as _f:
        json.dump({"source": "ExcludedCheck", "entries": [1, 2, 3, 4, 5]}, _f)

    RR.ROLL, RR.RECORDS = _roll_path, _records_dir
    _argv = sys.argv
    sys.argv = ["resync_roll.py"]
    try:
        RR.main()
    finally:
        sys.argv = _argv

    with open(_roll_path, encoding="utf-8") as _f:
        _result = {r["name"]: r for r in json.load(_f)}

check("resync_roll: a source purged to zero loses its stale 'catalogued' status",
      _result["PurgedCheck"]["status"], "uncatalogued")
check("resync_roll: a source purged to zero has entry_count corrected to 0",
      _result["PurgedCheck"]["entry_count"], 0)
check("resync_roll: an out-of-scope source keeps its status even with real records on disk",
      _result["ExcludedCheck"]["status"], "out-of-scope")


# ============================================================ order 596493b0b139 -- REPORT ONLY
# citation_card()/seed_from_card() (address_space.py) were confirmed dead (zero callers in
# src/, handoff/, docs/, reference/) but were NOT deleted -- map_seed() is the documented
# "prefer this" alternative and IS used elsewhere, and citation_card() carries an unfixed
# decimal-clamp bug (sweep33 #7) that would need resolving either way before deletion is a
# clean call. This is a standing owner question, not a check with a pass/fail answer -- left
# here as a reminder to re-grep before ever deleting either function.
with open(os.path.join(SRC, "address_space.py"), encoding="utf-8") as _f:
    _as_src2 = _f.read()
check("citation_card/seed_from_card still present (deliberately left for owner call)",
      "def citation_card(" in _as_src2 and "def seed_from_card(" in _as_src2, True)


# ============================================================ order e3a69ceb5857 -- OUT OF SCOPE
# "74 bits" was stale prose in derivation.py:333 and profile.py:20 -- NEITHER file is owned by
# this batch (L4 owns address_space.py, roll.py, resync_roll.py, tiers.py, hosts.py, navtree.py,
# endpoint.py, address.py, genre.py, grounding.py). address_space.py itself already prints
# TOTAL_BITS rather than a literal (verified: address_space.py lines 290/314). profile.py:20 was
# ALREADY fixed by someone else during this run (now reads "89-bit") between when this order was
# first checked and when this file was written -- confirming this really is a live, concurrently
# -worked queue. derivation.py:333 is the one that still needs its owner to make the same fix.
with open(os.path.join(HERE, "..", "..", "src", "derivation.py"), encoding="utf-8") as _f:
    _deriv_src = _f.read()
with open(os.path.join(HERE, "..", "..", "src", "profile.py"), encoding="utf-8") as _f:
    _profile_src = _f.read()
check("derivation.py no longer restates '74 bits' as a literal (STILL FAILING -- not this batch's file)",
      "74 bits" in _deriv_src, False)
check("profile.py no longer restates '74-bit' as a literal (already fixed elsewhere, reads 89-bit)",
      "74-bit" in _profile_src, False)


print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    sys.exit(1)
