# run35, LOCAL batch L5 -- proposed verify_math/drill checks for the orders worked this batch.
# Runnable Python. Each block is commented with the order id and its target file. These are
# PROPOSALS for verify_math.py / drill.py to adopt -- this agent owns pipeline.py, sweep.py,
# allsweep.py, rosetta.py, coverage.py, standards.py, tuning.py, lognames.py, scope.py, and NOT
# verify_math.py or drill.py, and did not add them there. Running verify_math.py/drill.py/
# mutate.py was also off-limits this batch (a mutation run in flight), so every check below was
# exercised by hand against the fixed source instead -- see AUDIT_L5.md for what was actually
# run and observed.

import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HERE, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


# order 2b4d552df6f0 -- src/sweep.py, report()
# report() must not raise on an empty rows list. It must print a funnel of zeros instead --
# ZeroDivisionError from f[k]/n (n=len(rows)==0) was the actual defect; f[k]/max(n,1) is the fix
# already used by the bar computation two lines above it in the same function.
def check_sweep_report_empty_rows_no_crash():
    import io
    import contextlib
    import sweep
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        f = sweep.report([])          # must not raise ZeroDivisionError
    assert isinstance(f, dict)
    assert all(v == 0 for v in f.values()), "empty input should give an all-zero funnel"
    assert "0.0%" in buf.getvalue() or "0%" in buf.getvalue()


# order 60f13f1d4f77 -- src/rosetta.py, scales_for()
# The MediaWiki search call that acquires native power scales must not ask for fewer hits than
# this project's own audited-safe precedent (feats.py discover(), srlimit=50) or the API's own
# default (10). Static check on the source text -- no network call.
def check_rosetta_srlimit_not_truncated():
    src = open(os.path.join(SRC, "rosetta.py"), encoding="utf-8").read()
    import re as _re
    m = _re.search(r'"list":\s*"search",\s*"srlimit":\s*"(\d+)"', src)
    assert m, "scales_for()'s search call not found in the expected shape"
    n = int(m.group(1))
    assert n >= 10, "srlimit=%d is below the MediaWiki search API's own default of 10" % n


# order 4e93de4ab854 -- src/allsweep.py, NEVER_RUN
# NEVER_RUN must stay either genuinely wired into a gate, or explicitly and visibly documented
# as unused -- never silently dead under a comment that reads as a live safety. This checks
# that whichever is true, the source is HONEST about it: if grep still finds no reader beyond
# its own definition, the comment above it must say so in plain words.
def check_allsweep_never_run_honesty():
    src = open(os.path.join(SRC, "allsweep.py"), encoding="utf-8").read()
    import re as _re
    uses = [m.start() for m in _re.finditer(r"\bNEVER_RUN\b", src)]
    assert len(uses) >= 1
    only_definition = len(uses) == 1
    if only_definition:
        near = src[max(0, uses[0] - 400):uses[0]]
        assert "NOTHING READS NEVER_RUN" in near or "nothing reads never_run" in near.lower(), (
            "NEVER_RUN is unread and the comment above it no longer discloses that")


# order b32a24da9987 / e755ab46df7f -- src/allsweep.py run_verifier(), src/coverage.py
# _state_of_file() -- every silence.note() call site should carry a label that is either (a) a
# symbolic/content name (no bare line number), or (b) verified to actually match its own current
# line. This batch retagged two numeric, stale ones; this check guards against a numeric tag
# silently going stale again by flagging any silence.note("<file>.py:<digits>") pattern outright
# (this project's own stated preference: "a stable CONTENT label over a fresh number that will
# rot again").
def check_no_bare_line_number_silence_tags():
    import re as _re
    offenders = []
    for fname in ("allsweep.py", "coverage.py"):
        src = open(os.path.join(SRC, fname), encoding="utf-8").read()
        for m in _re.finditer(r'silence\.note\("([a-zA-Z_]+\.py):(\d+)"\)', src):
            offenders.append("%s -> %s" % (fname, m.group(0)))
    assert not offenders, "bare numeric silence.note tags found: %s" % offenders


# order ba4f12234033 -- src/standards.py, the "every declared floor is measured" self-check
# The self-check must (a) recognise a MIN_/MAX_ floor even when it carries a prefix like
# CHARTER_REGRESSION_, and (b) find a real use of that floor even when the use lives in a helper
# function defined ABOVE check() (the shape charter_regression_verdict() introduced 2026-08-25).
# Reproduces the check's own logic against the live file rather than importing private state.
def check_standards_self_check_finds_prefixed_floor():
    import re as _re
    src = open(os.path.join(SRC, "standards.py"), encoding="utf-8").read()
    declared = set(_re.findall(r"^((?:[A-Z][A-Z0-9]*_)*M(?:IN|AX)_[A-Z_]+)\s*=", src, _re.M))
    assert "CHARTER_REGRESSION_MAX_AGE_H" in declared
    code_all = chr(10).join(ln.split("#")[0] for ln in src.splitlines())
    wordb = chr(92) + "b"
    dead = sorted(d for d in declared
                  if len(_re.findall(wordb + _re.escape(d) + wordb, code_all)) < 2)
    assert "CHARTER_REGRESSION_MAX_AGE_H" not in dead
    assert dead == [], "unexpected dead floors under the new self-check: %s" % dead


# order d1e6c5916a18 -- src/scope.py, build()
# build() must not accept (or require) an unused records argument. AST-checks the live
# signature and confirms the whole-corpus read (pipeline.records()) is no longer reachable from
# scope.py's own --build path.
def check_scope_build_signature_has_no_dead_param():
    import ast
    import inspect
    src = open(os.path.join(SRC, "scope.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "build")
    args = [a.arg for a in fn.args.args]
    # NO DEAD PARAM -- which is what this check is named for and what the order fixed. It used
    # to assert `args == ["hosts"]`, an exact-signature pin, and on 2026-08-29 scope.build()
    # legitimately gained `force=False`: it is read in the todo comprehension
    # (`force or _stamp(out.get(h)) < PROBE_VERSION`) and passed from main() as `force=a.rebuild`,
    # the escape hatch for a host frozen out for ever once it had a key. A live parameter is not
    # drift. Assert the PROPERTY instead -- every declared parameter is actually read in the body
    # -- which still fails the day a dead one is re-added, under any name, and no longer fails
    # the day a used one is added.
    body_names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
    dead = [a for a in args if a not in body_names]
    assert not dead, "scope.build() has dead parameter(s): %r (signature %r)" % (dead, args)
    assert args and args[0] == "hosts", \
        "scope.build() no longer takes hosts as its first parameter: %r" % (args,)
    assert "P.records(" not in src, "scope.py still calls pipeline.records() somewhere"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("check_") and callable(v)]
    ok = 0
    for fn in fns:
        try:
            fn()
            print("PASS", fn.__name__)
            ok += 1
        except Exception as e:
            print("FAIL", fn.__name__, "--", type(e).__name__, str(e)[:200])
    print("%d/%d passed" % (ok, len(fns)))
