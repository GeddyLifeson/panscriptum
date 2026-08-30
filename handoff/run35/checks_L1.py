# run35, LOCAL batch L1 -- proposed verify_math/drill checks for the orders worked this batch.
# Runnable Python. Each block is commented with the order id and its target file. These are
# PROPOSALS for verify_math.py / drill.py to adopt -- this agent does not own those files and
# did not add them there.

import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)


# order 42bda2a1f93b -- src/liveness.py
# main()'s printed breakdown must always sum to the printed total, including the unparsed
# bucket -- the bug was exactly that the total counted a kind the breakdown never named.
def check_liveness_unparsed_is_reported():
    # DRIVEN, NOT GREPPED (2026-08-29 maintenance). The second assert here used to be
    # `"%d unparsed" in text`, a hand-written summary fragment. main() was then rewritten to
    # DERIVE both the itemisation and the summary from one `KINDS` tuple, precisely so that a
    # limb added to scan() can no longer be counted in the total and named nowhere -- the
    # `dead_module` defect, order dded1fc0e664, where "47 finding(s) — 0 + 0 + 36 + 1 + 0" was
    # all a reader ever saw. The literal fragment disappeared because the improvement removed
    # every hand-written fragment; the count is still printed. Pinning the spelling made the
    # fix look like the regression, so drive main() instead: stub scan(), capture stdout, and
    # read the summary line. A future limb that goes uncounted fails this for real.
    import contextlib
    import io as _io
    import liveness
    text = open(os.path.join(SRC, "liveness.py"), encoding="utf-8").read()
    assert '"unparsed"' in text.split("def main")[1].split("\ndef ")[0], \
        "liveness.py main() no longer displays the 'unparsed' bucket"
    fixture = {"dead": [], "dead_class": [], "dead_module": [], "tautology": [],
               "phantom": [], "unparsed": ["fake_a.py: will not parse",
                                           "fake_b.py: will not parse"]}
    real_scan, real_argv = liveness.scan, sys.argv
    buf = _io.StringIO()
    try:
        liveness.scan = lambda *a, **k: dict(fixture)
        sys.argv = ["liveness.py", "--quiet"]
        with contextlib.redirect_stdout(buf):
            liveness.main()
    finally:
        liveness.scan, sys.argv = real_scan, real_argv
    out = buf.getvalue()
    assert "2 unparsed" in out, (
        "liveness.py main()'s summary line no longer names the unparsed count -- two unparsed "
        "files were fed in and the report said: %r" % out.strip()[-200:])
    # ...and the total must count them, or the bucket is named over an arithmetic that hides it.
    assert "2 finding(s)" in out, (
        "liveness.py main()'s total no longer includes the unparsed bucket: %r"
        % out.strip()[-200:])


# order 444c88673a15 -- src/dashboard.py
# movement() must land state/dashboard_history.json through silence.write_json, not a
# hand-rolled fixed ".tmp" name (the exact collision shape this project has been bitten by
# under a threaded server).
def check_dashboard_movement_uses_write_json():
    text = open(os.path.join(SRC, "dashboard.py"), encoding="utf-8").read()
    fn = text.split("def movement")[1].split("\ndef ")[0]
    assert "silence.write_json(HISTORY, hist)" in fn, \
        "dashboard.py movement() no longer writes HISTORY through silence.write_json"
    assert 'HISTORY + ".tmp"' not in fn, \
        "dashboard.py movement(): the fixed-name '.tmp' collision reappeared"


# order 4f68f9f9f591 -- src/policy.py
# The coverage rule that only checks cited>=0 must not carry an id promising cited<=entries --
# OPS has no cross-field comparator, so that name was never something the rule could evaluate.
def check_policy_no_misleading_rule_id():
    text = open(os.path.join(SRC, "policy.py"), encoding="utf-8").read()
    assert '"coverage.cited_le_entries"' not in text, \
        "policy.py: misleading rule id 'coverage.cited_le_entries' reappeared (checks " \
        "cited>=0, not cited<=entries -- OPS has no operator that compares two fields)"
    assert '"coverage.cited_nonneg"' in text, \
        "policy.py: renamed rule id 'coverage.cited_nonneg' is missing"


# order 97880e5e40e1 -- src/sweep_plan.py
# The seven genuine data-reading swallows in sweep_plan.py (glob/read failures in
# _read_shards, coverage_map, covered_by x2, latest_run, record x2, plus the --coverage CLI
# read) must each carry a silence.note call. Uses silence.audit() itself, so a regression is
# caught by the same instrument that would catch a brand new silent handler anywhere else.
def check_sweep_plan_data_reads_are_noted():
    import silence
    rows = [r for r in silence.audit() if r["file"] == "sweep_plan.py"]
    silent = [r for r in rows if r["silent"]]
    # Every remaining silent handler must be the unavoidable shape: it wraps `import silence`
    # itself, so it cannot call silence.note if the import is what failed. Verified by checking
    # each silent handler's enclosing lines mention "import silence".
    text = open(os.path.join(SRC, "sweep_plan.py"), encoding="utf-8").read()
    lines = text.splitlines()
    for r in silent:
        window = "\n".join(lines[max(0, r["line"] - 4):r["line"] + 1])
        assert "import silence" in window or "silence.note(" in window, (
            "sweep_plan.py:%d is silent and is NOT the unavoidable "
            "import/note-itself-may-fail shape -- a genuine data-reading swallow regressed"
            % r["line"])


# order a6ce5d205263 -- src/silence.py
# The module docstring must not assert a fixed, specific handler count as "the real bug" --
# audit()'s own live count must differ from any number frozen in prose within one run, which
# is exactly what made the original "45" claim false the moment it was measured.
def check_silence_docstring_no_frozen_handler_count():
    text = open(os.path.join(SRC, "silence.py"), encoding="utf-8").read()
    head = text.split('"""', 2)[1]
    assert not re.search(r"There are \d+ such handlers in this tree", head), \
        "silence.py docstring: a frozen handler count reappeared in prose"


# order 2782e0f8536d -- data/SUPPRESSIONS.json (via suppressions.py's public API)
# The Bloons wiki false positive must stay suppressed, with a reason attached (never a bare
# skip), and the suppression must actually cover the exact file the scanner flags.
def check_bloons_secret_scan_suppression_has_reason():
    import suppressions
    row = suppressions.suppressed(
        "secret_scan", "data/feats/bloons_fandom_com/Encrypted.json")
    assert row is not None, \
        "the secret_scan suppression for the Bloons Encrypted.json false positive is gone"
    assert len(row.get("reason", "")) >= 12, \
        "the Bloons Encrypted.json suppression lost its written reason"


# order 125ec831fc5d -- src/descending_ladder.py (disproved; guards against regression)
# shrink_report() must keep reporting from_m as data (from_m field + is_descent), which is
# what makes the vulture-reported "unused variable from_m" finding false. If from_m is ever
# accepted and dropped again, this should fail alongside a fresh vulture finding.
def check_descending_ladder_shrink_report_uses_from_m():
    text = open(os.path.join(SRC, "descending_ladder.py"), encoding="utf-8").read()
    fn = text.split("def shrink_report")[1].split("\ndef ")[0]
    assert '"from_m": from_m' in fn, \
        "descending_ladder.shrink_report() no longer reports from_m in its return dict"
    assert "from_m is not None and to_m < from_m" in fn, \
        "descending_ladder.shrink_report() no longer uses from_m in is_descent"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("check_")]
    for fn in fns:
        fn()
        print("OK", fn.__name__)
    print(f"{len(fns)} checks passed")
