"""
Proposed checks for run35 batch 3 (agent working coverage.py / standards.py / tuning.py /
rosetta.py / lognames.py / sweep.py / allsweep.py).

These are NOT run standalone. They assume the surrounding verify_math.py namespace (`os`,
`json`, `ast`, `re`, `check(label, got, want, note=...)`) already exists by the time this block
executes. Per this run's rule (order c349a51ee2c5), verify_math.py and drill.py were not run by
this agent; every check below WAS exercised standalone against the live, already-fixed source
(coverage.py, standards.py, tuning.py, rosetta.py, allsweep.py, overnight.py) to confirm it
behaves as claimed before being written here.

Local names are suffixed _b3 to avoid colliding with verify_math.py's own locals.
"""

import ast as _ast_b3
import re as _re_b3


# ==================================================================================================
# order 1230a343d75f -- belongs in verify_math.py. coverage.report()'s two "outstanding work"
# lists ("SOURCES WITH NO WIKI HOST", "WORST COVERED WITH A HOST") used to rank-then-truncate
# ([:12] and [:show], show defaulting to 26 both in the signature and on the CLI). Fixed: the
# hostless list is now always printed in full; the worst-covered list defaults to full and only
# truncates when --show is passed explicitly, always announcing the count left out. This is a
# positive control that the fix actually surfaces every row, not just a smaller cap.
# ==================================================================================================

print()
print("[batch3] order 1230a343d75f -- coverage.report() no longer caps its two 'outstanding "
      "work' lists")

import coverage as _COVx  # noqa: E402

_fake_rows_b3_1230 = (
    [{"source": f"hostless-{i}", "host": "", "entries": 100 - i, "cited": 0, "read": 0,
      "no_page": 0, "no_host": 100 - i, "not_attempted": 0, "feats": 0,
      "coverage": 0.0, "settled": 0.0} for i in range(20)]  # 20 > the old [:12] cap
    + [{"source": f"hosted-{i}", "host": "somewiki.fandom.com", "entries": 100,
        "cited": i, "read": 0, "no_page": 0, "no_host": 0, "not_attempted": 100 - i,
        "feats": 0, "coverage": i / 100.0, "settled": i / 100.0}
       for i in range(30)]  # 30 > the old default show=26 cap
)

import io as _io_b3_1230
import contextlib as _ctx_b3_1230

_buf_b3_1230 = _io_b3_1230.StringIO()
with _ctx_b3_1230.redirect_stdout(_buf_b3_1230):
    _COVx.report(_fake_rows_b3_1230)
_printed_b3_1230 = _buf_b3_1230.getvalue()

check("[1230a343d75f] every hostless source is printed, not just 12 of 20",
      sum(1 for i in range(20) if f"hostless-{i}" in _printed_b3_1230), 20,
      note="the old code sliced this list to [:12] under a header calling it 'nothing can ever "
           "be cited here'; a source past the cutoff read as if it did not exist")

check("[1230a343d75f] the default run prints all 30 worst-covered-with-a-host sources, not "
      "capped at 26",
      sum(1 for i in range(30) if f"hosted-{i}" in _printed_b3_1230), 30,
      note="report(rows) with no --show now defaults to showing everything; the supervisor's "
           "default invocation used to silently cap at 26")

_buf2_b3_1230 = _io_b3_1230.StringIO()
with _ctx_b3_1230.redirect_stdout(_buf2_b3_1230):
    _COVx.report(_fake_rows_b3_1230, show=5)
_printed2_b3_1230 = _buf2_b3_1230.getvalue()
# Scoped to the WORST COVERED section only -- BEST COVERED is a separate, unrelated top-10
# list over the same fake rows and would otherwise inflate this count.
_worst_section_b3_1230 = _printed2_b3_1230.split("WORST COVERED WITH A HOST", 1)[1].split(
    "\nBEST COVERED", 1)[0]
check("[1230a343d75f] --show=5 prints exactly 5 worst-covered rows AND announces 25 were held "
      "back",
      (sum(1 for i in range(30) if f"hosted-{i}" in _worst_section_b3_1230),
       "25 more not shown" in _printed2_b3_1230),
      (5, True),
      note="a cap the caller asked for is not the bug Hard Rule 0 forbids -- a SILENT one is; "
           "this confirms the announced-cap path still exists and still announces")


# ==================================================================================================
# order 9d4d0c4e6c6a -- belongs in verify_math.py. Two more caps in standards.check() on the
# exact fields the order text told a reader to grep for: `worst = sorted(good, ...)[:3]` (the
# completeness standard's "worst:" detail) and `", ".join(_pending)[:120]` (the spine-code-
# amendment-pending standard). Both now print everything.
# ==================================================================================================

print()
print("[batch3] order 9d4d0c4e6c6a -- standards.py's two remaining caps on fields the order "
      "text tells a reader to act on")

_standards_path_b3 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "standards.py")
with open(_standards_path_b3, encoding="utf-8") as _f_b3_std:
    _standards_src_b3 = _f_b3_std.read()

check("[9d4d0c4e6c6a] the completeness 'worst' list is no longer sliced to the top 3",
      bool(_re_b3.search(
          r'worst\s*=\s*sorted\(good,\s*key=lambda c:\s*c\.get\("coverage",\s*0\)\)\s*\n',
          _standards_src_b3)), True,
      note="regression guard: fails if a future edit reintroduces a bare [:N] on this line "
           "without also updating this check")
check("[9d4d0c4e6c6a] the completeness 'worst' list has no numeric slice at all",
      bool(_re_b3.search(
          r'worst\s*=\s*sorted\(good,[^\n]*\)\[:\d+\]', _standards_src_b3)), False,
      note="direct negative scan for the exact old shape ([:3])")
check("[9d4d0c4e6c6a] the spine-code-amendment-pending join is no longer character-truncated",
      bool(_re_b3.search(r'", "\.join\(_pending\)\[:\d+\]', _standards_src_b3)), False,
      note="direct negative scan for the exact old shape ([:120]), which used to cut a source "
           "name mid-word")


# ==================================================================================================
# order 5b85ab54b176 -- belongs in verify_math.py. standards.report()'s "N/N standards met" used
# to divide by len(rows), where ~20 standards had their only out.append() inside a try whose
# except just called silence.note() -- so a missing/unreadable input silently DELETED the
# standard and shrank N with it, reading as MORE consistent. Fixed with a `_dropped` list fed by
# each of those ~20 except-handlers plus one new aggregate standard at the end of check().
# ==================================================================================================

print()
print("[batch3] order 5b85ab54b176 -- a standard that fails to read its input now MISSES "
      "instead of vanishing")

# Static check: every silence.note("standards.py:<name>") call this fix identified as sitting
# behind the ONLY out.append() for its standard is now paired with a _dropped.append of the
# same name, so the pairing can't silently rot apart from the note calls in a future edit.
_VANISHING_NAMES_B3 = [
    "reader-gate", "roster-audit", "shelfmarks", "reference-assays", "charter-regression",
    "counters-moving", "allsweep", "catalogue-coverage", "sweep-freshness", "job-advance",
    "unrecognised-pool", "fandom-reachable", "disk", "shelf-ranks", "ollama-runner-standard",
    "token-flow-standard", "jobs-alive", "publish-age", "provider-models", "self-check",
]
_unpaired_b3 = []
for _name_b3 in _VANISHING_NAMES_B3:
    _pat_b3 = (r'silence\.note\("standards\.py:' + _re_b3.escape(_name_b3) + r'"\)\s*\n\s*'
               r'_dropped\.append\("' + _re_b3.escape(_name_b3) + r'"\)')
    if not _re_b3.search(_pat_b3, _standards_src_b3):
        _unpaired_b3.append(_name_b3)
check("[5b85ab54b176] every vanishing-standard except-handler still pairs silence.note() with "
      "_dropped.append() of the same name",
      _unpaired_b3, [],
      note="a name here means a future edit separated the note from the drop-tracking, which "
           "would silently reopen the green-by-absence hole this order closed")

# Functional check: force ONE real input read to fail (COMPLETENESS.json, behind the
# "every source is fully catalogued" standard) and confirm (a) that standard is absent from
# `rows`, (b) the new aggregate standard reports it by name and MISSES, (c) the printed
# "N/N standards met" line's denominator now includes the aggregate row rather than silently
# shrinking with no trace.
import standards as _STx_b3
import dashboard as _Dx_b3

_state_b3 = _Dx_b3.state()
_real_open_b3 = open


def _breaking_open_b3(path, *a, **kw):
    if os.path.basename(str(path)) == "COMPLETENESS.json":
        raise OSError("simulated read failure for 5b85ab54b176's verify_math check")
    return _real_open_b3(path, *a, **kw)


import builtins as _bi_b3

# Clean run FIRST (before anything is patched), so the comparison below isn't sensitive to
# whatever this run's live, network- or clock-dependent standards happen to say.
_clean_rows_b3 = _STx_b3.check(_state_b3)
_clean_names_b3 = {r["standard"] for r in _clean_rows_b3}

_bi_b3.open = _breaking_open_b3
try:
    _rows_b3 = _STx_b3.check(_state_b3)
finally:
    _bi_b3.open = _real_open_b3

_names_b3 = {r["standard"] for r in _rows_b3}
_agg_b3 = next((r for r in _rows_b3 if r["standard"] == "every standard could read its own "
                                                          "input"), None)
check("[5b85ab54b176] a standard whose input read failed is genuinely absent from rows (this "
      "is the precondition the bug relied on, not the fix)",
      "every source is fully catalogued" in _names_b3, False)
check("[5b85ab54b176] the aggregate standard exists, MISSES, and names the dropped standard",
      (_agg_b3 is not None, _agg_b3["holds"] if _agg_b3 else None,
       "catalogue-coverage" in str(_agg_b3["observed"]) if _agg_b3 else False),
      (True, False, True),
      note="observed=%r" % (_agg_b3["observed"] if _agg_b3 else "<no row>"))
# Set difference rather than raw length: the aggregate standard is present in BOTH runs (it
# only flips holds True/False), so a clean run and a one-standard-dropped run differ by exactly
# the one standard that failed to read -- never by a shrinking, untraceable total. Set
# comparison (rather than len() arithmetic) also can't be fooled by an unrelated standard
# flapping between the two check() calls for live/network reasons.
check("[5b85ab54b176] exactly the broken standard -- and nothing else -- disappears; the "
      "aggregate standard is present, unaffected, in both runs",
      (_clean_names_b3 - _names_b3, "every standard could read its own input" in _clean_names_b3,
       "every standard could read its own input" in _names_b3),
      ({"every source is fully catalogued"}, True, True),
      note="clean run standards=%d, broken run standards=%d" % (len(_clean_names_b3),
                                                                 len(_names_b3)))


# ==================================================================================================
# order 495390283745 -- belongs in verify_math.py, REPLACING the existing check "the threshold
# itself is the one tuning.py already settled on" (currently `_STx.MIN_CALLS_TO_JUDGE_RATE, 20`),
# which compares against a literal and would stay green if tuning.py and standards.py diverged.
# standards.py now derives the constant directly (`MIN_CALLS_TO_JUDGE_RATE = tuning.MIN_CALLS_
# TO_JUDGE`), so the two cannot diverge -- this checks the SOURCE actually says that, not just
# that today's two numbers happen to match.
# ==================================================================================================

print()
print("[batch3] order 495390283745 -- MIN_CALLS_TO_JUDGE_RATE is derived from tuning.py, not a "
      "hand-copied literal")

import tuning as _TUNx_b3

check("[495390283745] standards.MIN_CALLS_TO_JUDGE_RATE is identically tuning.MIN_CALLS_TO_"
      "JUDGE (same object/value by construction), not a coincidentally-equal literal",
      _STx_b3.MIN_CALLS_TO_JUDGE_RATE, _TUNx_b3.MIN_CALLS_TO_JUDGE)
check("[495390283745] the source assigns the constant FROM tuning, so a future edit that "
      "reverts to a bare literal is caught here even if the two numbers still happen to match "
      "today",
      bool(_re_b3.search(r'MIN_CALLS_TO_JUDGE_RATE\s*=\s*tuning\.MIN_CALLS_TO_JUDGE\s*\n',
                         _standards_src_b3)), True,
      note="if this goes red while the check above is still green, someone re-inlined the "
           "literal and got lucky that tuning.py had not moved yet -- exactly the shape that "
           "let this order's bug happen the first time")
check("[495390283745] verify_math.py's existing '...already settled on' check should compare "
      "against tuning.MIN_CALLS_TO_JUDGE directly, not the literal 20 -- PROPOSED EDIT for the "
      "coordinator (this agent does not own verify_math.py): "
      "check(\"the threshold itself is the one tuning.py already settled on\", "
      "_STx.MIN_CALLS_TO_JUDGE_RATE, _TUNx.MIN_CALLS_TO_JUDGE, note=...)",
      True, True,
      note="documentation-only row; the two lines above already give the coordinator a real, "
           "runnable version of this same intent that cannot be fooled by a coincidence")


# ==================================================================================================
# order 6e3e3e553fd5 -- belongs in verify_math.py. rosetta.check()'s Spearman rank-agreement
# test (the module's stated purpose) had no automated caller: main()'s --check branch always
# `return 0`, and allsweep.VERIFIERS had no rosetta entry. Fixed: --check now returns 1 on any
# real disagreement (rho < 0.3), and allsweep.VERIFIERS gained a
# ("franchise rank agreement", ["rosetta.py", "--check"]) entry.
# ==================================================================================================

print()
print("[batch3] order 6e3e3e553fd5 -- rosetta's rank-agreement check now has a real caller and "
      "a real exit code")

import allsweep as _ALLx_b3

check("[6e3e3e553fd5] allsweep.VERIFIERS now runs rosetta.py --check",
      any(argv == ["rosetta.py", "--check"] for _label, argv in _ALLx_b3.VERIFIERS), True,
      note="before this fix, ROSETTA.json's mined values were consumed by sweep.py but the "
           "correlation check itself ran only under a hand-typed rosetta.py --check")

# Functional control: feed rosetta.check() (via main()'s own code path) a native scale and an
# Assay ordering that DIRECTLY CONTRADICT each other, and confirm the process would now exit 1.
import rosetta as _ROSx_b3

_contradicting_rosetta_b3 = {
    "test-wiki": {
        "Test Power Scale": {
            "kind": "numeric",
            "values": {"Alpha": 1, "Bravo": 2, "Charlie": 3, "Delta": 4, "Echo": 5, "Foxtrot": 6},
        }
    }
}
# Our Assay ranks them in the EXACT OPPOSITE order the native scale publishes.
_contradicting_assays_b3 = {
    "Alpha": 6.0, "Bravo": 5.0, "Charlie": 4.0, "Delta": 3.0, "Echo": 2.0, "Foxtrot": 1.0,
}
_rows_b3_rosetta = _ROSx_b3.check(_contradicting_rosetta_b3, _contradicting_assays_b3)
check("[6e3e3e553fd5] the canary scale (exact rank inversion) is measured as a real "
      "disagreement (rho <= -0.9)",
      bool(_rows_b3_rosetta) and _rows_b3_rosetta[0]["rho"] <= -0.9, True,
      note="observed rows=%r" % _rows_b3_rosetta)

# Same scenario, through main()'s actual --check code path (the part that used to always
# `return 0`), using temp files so the fixed exit code is exercised for real.
import json as _json_b3
import tempfile as _tmp_b3

with _tmp_b3.TemporaryDirectory() as _td_b3:
    os.makedirs(os.path.join(_td_b3, "data"), exist_ok=True)
    _rosetta_path_b3 = os.path.join(_td_b3, "ROSETTA.json")
    # main()'s --check reads ASSAYS.json as os.path.join(HERE, "data", "ASSAYS.json") --
    # it must sit under data/, not flat beside ROSETTA.json.
    _assays_path_b3 = os.path.join(_td_b3, "data", "ASSAYS.json")
    with open(_rosetta_path_b3, "w", encoding="utf-8") as _f:
        _json_b3.dump(_contradicting_rosetta_b3, _f)
    with open(_assays_path_b3, "w", encoding="utf-8") as _f:
        _json_b3.dump({k: {"result": {"decimal": v}}
                       for k, v in _contradicting_assays_b3.items()}, _f)
    _orig_out_b3, _orig_here_b3 = _ROSx_b3.OUT, _ROSx_b3.HERE
    _ROSx_b3.OUT = _rosetta_path_b3
    _ROSx_b3.HERE = _td_b3
    _orig_argv_b3 = sys.argv
    sys.argv = ["rosetta.py", "--check"]
    try:
        _rc_b3 = _ROSx_b3.main()
    finally:
        _ROSx_b3.OUT, _ROSx_b3.HERE = _orig_out_b3, _orig_here_b3
        sys.argv = _orig_argv_b3

check("[6e3e3e553fd5] rosetta.py --check now exits 1 (not always 0) when a scale genuinely "
      "disagrees with the Assay -- the exact defect this order named",
      _rc_b3, 1,
      note="before the fix this was `return 0` unconditionally regardless of the printed rhos")


# ==================================================================================================
# order dcdd1fa96864 -- DISPROVED, not fixed. The order's evidence quotes overnight.py:180 as a
# plain substring test (`fragment in cmd... or fragment in cmd`) under which
# lognames.OWNER[SWEEP]='sweep.py' would collide with allsweep.py. Measured against the live
# source: overnight.running() now calls _cmd_is_running(), which does an EXACT
# os.path.basename(script) == os.path.basename(want) comparison (fixed for the unrelated
# codewatch.twins()-shaped bug in run #34) -- the substring code the order quotes no longer
# exists on this path. This is a regression guard so the disproof stays true.
# ==================================================================================================

print()
print("[batch3] order dcdd1fa96864 -- DISPROVED; guard against the substring-match bug "
      "reappearing")

import overnight as _ONx_b3

check("[dcdd1fa96864] lognames.OWNER[SWEEP]='sweep.py' does NOT match a running allsweep.py "
      "(the collision the order alleged)",
      _ONx_b3._cmd_is_running("sweep.py",
                              "python C:/Users/imarl/panscriptum-library-kit/src/allsweep.py"),
      False,
      note="if this goes red, _cmd_is_running regressed to substring matching and the order's "
           "finding, previously disproved, would become real")
check("[dcdd1fa96864] ...and DOES still match a running sweep.py itself (the matcher isn't "
      "just refusing everything)",
      _ONx_b3._cmd_is_running("sweep.py",
                              "python C:/Users/imarl/panscriptum-library-kit/src/sweep.py"),
      True)
