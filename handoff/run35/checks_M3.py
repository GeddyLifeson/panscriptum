# run35, wave 2, batch M3 -- proposed verify_math/drill checks for the orders worked this batch.
# Runnable Python. Each block is commented with the order id and its target file. These are
# PROPOSALS for verify_math.py / drill.py to adopt -- this agent does not own those files and
# did not add them there.

import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)


# order 26be3dba65cf -- src/roll.py
# exclude() must not report a change as landed when the write to SWEEP_ROLL.json was denied,
# and the caller-supplied-rows path must never touch the real ROLL file at all.
def check_roll_exclude_reports_write_verdict():
    import json
    import tempfile
    import roll
    orig = roll.ROLL
    tmpd = tempfile.mkdtemp()
    tmp_roll = os.path.join(tmpd, "SWEEP_ROLL.json")
    roll.ROLL = tmp_roll
    try:
        rows = [{"name": "CheckFoo", "status": "catalogued"}]
        with open(tmp_roll, "w", encoding="utf-8") as f:
            json.dump(rows, f)
        assert roll.exclude("CheckFoo", "m3 check") is True, \
            "roll.exclude() did not report True for a write that actually landed"
        on_disk = json.load(open(tmp_roll, encoding="utf-8"))
        assert on_disk[0]["status"] == roll.OUT_OF_SCOPE, \
            "roll.exclude() reported success but the row on disk was not updated"
        assert roll.exclude("CheckFoo", "m3 check") is False, \
            "roll.exclude() must return False (no-op) when nothing actually changed"
        rows2 = [{"name": "CheckBar", "status": "catalogued"}]
        assert roll.exclude("CheckBar", "m3 check", rows=rows2) is True
        on_disk2 = json.load(open(tmp_roll, encoding="utf-8"))
        assert all(r["name"] != "CheckBar" for r in on_disk2), \
            "roll.exclude(rows=...) must never write the real ROLL path"
    finally:
        roll.ROLL = orig


# order 40b61d3a8c68 -- src/resonance.py
# hodge_decompose must never divide by zero on empty input, and "no evidence" must not read as
# "perfectly consistent" (eta must not silently become 1.0 when there is no signal to measure).
def check_resonance_hodge_decompose_no_evidence():
    import resonance as RES
    empty = RES.hodge_decompose({})
    assert empty["eta"] is None and empty.get("no_evidence") is True, \
        "hodge_decompose({}) must report no_evidence, not a numeric eta"
    zero_flow = RES.hodge_decompose({("a", "b"): 0.0})
    assert zero_flow["eta"] is None and zero_flow.get("no_evidence") is True, \
        "an all-zero-flow graph must not report eta=1.0 ('perfectly consistent')"
    real = RES.hodge_decompose({("a", "b"): 1.0, ("b", "c"): 1.0, ("a", "c"): -2.0})
    assert real["eta"] is not None and real.get("no_evidence") is False, \
        "a graph with real signal must still report a numeric eta"


# order 9a18068421c3 -- src/suppressions.py
# An unreadable SUPPRESSIONS.json must surface as a fault in problems(), not as zero problems.
def check_suppressions_unreadable_is_a_problem():
    import tempfile
    import suppressions as S
    orig = S.FILE
    tmpd = tempfile.mkdtemp()
    corrupt = os.path.join(tmpd, "SUPPRESSIONS.json")
    with open(corrupt, "w", encoding="utf-8") as f:
        f.write("{not valid json")
    S.FILE = corrupt
    try:
        probs = S.problems()
        assert probs, "a corrupt SUPPRESSIONS.json must report at least one problem"
        assert any("UNREADABLE" in p for p in probs), \
            "the corrupt-file problem must be labelled UNREADABLE, not folded into DANGLING/EXPIRED"
        try:
            S.add("secret_scan", "x/*", "a real reason for this check")
            raise AssertionError("add() must refuse to write on top of an unreadable file")
        except IOError:
            pass
        os.remove(corrupt)
        assert S.problems() == [], \
            "a genuinely MISSING SUPPRESSIONS.json is an honest zero, not a fault"
    finally:
        S.FILE = orig


# order 88964707a3f7 -- src/estate.py
# Every silence.note() call in inspect() must use a stable symbolic tag, not a numeric line
# reference that rots the next time the file is edited.
def check_estate_note_tags_are_symbolic():
    text = open(os.path.join(SRC, "estate.py"), encoding="utf-8").read()
    import re
    for m in re.finditer(r'silence\.note\("estate\.py:([^"]+)"\)', text):
        tag = m.group(1)
        assert not tag.isdigit(), \
            "estate.py has a numeric silence.note tag again: estate.py:%s" % tag


# order 45b5e706e2d6 -- src/profile.py
def check_profile_note_tags_are_symbolic():
    text = open(os.path.join(SRC, "profile.py"), encoding="utf-8").read()
    import re
    for m in re.finditer(r'silence\.note\("profile\.py:([^"]+)"\)', text):
        tag = m.group(1)
        assert not tag.isdigit(), \
            "profile.py has a numeric silence.note tag again: profile.py:%s" % tag


# order 92a07b4ba203 -- src/identity.py
# load()'s cache write must go through silence.write_json (pid/thread-unique tmp name), not a
# hand-rolled fixed ".tmp" path.
def check_identity_load_uses_write_json():
    text = open(os.path.join(SRC, "identity.py"), encoding="utf-8").read()
    fn = text.split("def load(")[1].split("\ndef ")[0]
    assert "silence.write_json(CACHE, inv" in fn, \
        "identity.py load() no longer writes CACHE through silence.write_json"
    assert 'CACHE + ".tmp"' not in fn, \
        "identity.py load(): the fixed-name '.tmp' collision reappeared"


# order 3c86a8d541b2 -- src/identity.py
# EPOCH_REQUIRED / epoch_directive / epoch_acceptable must be defined before the
# `if __name__ == "__main__"` guard, so they exist in a process that runs this module directly.
def check_identity_epoch_block_before_main_guard():
    text = open(os.path.join(SRC, "identity.py"), encoding="utf-8").read()
    guard = 'if __name__ == "__main__":\n    sys.exit(main())'
    assert text.count(guard) == 1, \
        "identity.py: expected exactly one literal '__main__: sys.exit(main())' guard"
    guard_at = text.index(guard)
    epoch_at = text.index("EPOCH_REQUIRED = {")
    assert epoch_at < guard_at, \
        "identity.py: EPOCH_REQUIRED must be defined before the __main__ guard"


# order 53dcfb2bd48b -- src/policy.py
def check_policy_report_uses_write_json():
    text = open(os.path.join(SRC, "policy.py"), encoding="utf-8").read()
    fn = text.split("def report(")[1].split("\ndef ")[0]
    assert "silence.write_json(REPORT" in fn, \
        "policy.py report() no longer writes REPORT through silence.write_json"
    assert 'tmp = REPORT + ".tmp"' not in fn, \
        "policy.py report(): the fixed-name '.tmp' collision reappeared"


# order 57acf43b339a -- src/descending_ladder.py
# Newton's G must be a named constant in the real-constants block, and schwarzschild_radius
# must use it rather than an inlined literal.
def check_descending_ladder_g_newton_named():
    import descending_ladder as D
    assert hasattr(D, "G_NEWTON") and abs(D.G_NEWTON - 6.67430e-11) < 1e-16
    text = open(os.path.join(SRC, "descending_ladder.py"), encoding="utf-8").read()
    fn = text.split("def schwarzschild_radius(")[1].split("\ndef ")[0]
    assert "6.67430e-11" not in fn, \
        "descending_ladder.py schwarzschild_radius() still inlines G rather than using G_NEWTON"
    assert "G_NEWTON" in fn


if __name__ == "__main__":
    import inspect as _inspect
    fails = []
    mod = sys.modules[__name__]
    for name, fn in sorted(_inspect.getmembers(mod, _inspect.isfunction)):
        if not name.startswith("check_"):
            continue
        try:
            fn()
            print("  OK  ", name)
        except Exception as e:
            fails.append((name, e))
            print("  FAIL", name, "--", e)
    print("\n%d checks, %d failed" % (
        len(_inspect.getmembers(mod, _inspect.isfunction)), len(fails)))
