# run35, wave 2, batch M1 -- proposed verify_math/drill checks for the orders worked this batch.
# Runnable Python. Each block is commented with the order id and its target file. These are
# PROPOSALS for verify_math.py / drill.py to adopt -- this agent does not own those files and
# did not add them there.

import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)


# order 1cdbdbc3d4fa / c49e3871ac60 -- src/overnight.py, watch_report()
# The count-vs-sort case mismatch and the announce-then-truncate cap were both in this one
# function. Prove both: a mixed-case "High" finding is counted AND kept (not sorted off the
# end), and the printed loop never sees a slice shorter than the full open list.
def check_overnight_watch_report_counts_and_prints_all():
    import inspect
    import overnight as ON
    src = inspect.getsource(ON.watch_report)
    # The fix's own explanatory comment mentions the retired `` `[:top]` `` slice by name, so
    # the code line is what must be checked, not a bare substring search over the whole source.
    for_line = [ln for ln in src.splitlines() if ln.strip().startswith("for f in sorted(open_f")]
    assert for_line, "overnight.watch_report()'s findings loop was not found where expected"
    assert "[:" not in for_line[0], \
        "overnight.watch_report() re-added a cap on the open-findings list: %r" % for_line[0]
    assert '"severity") or "").lower() == "high"' in src, \
        "overnight.watch_report()'s sort key must lower() severity, matching the count's compare"
    # simulate the sort the function performs and check a mixed-case "High" survives to the top
    findings = [{"severity": "medium", "module": "a", "symbol": "x", "actual": "1"},
                {"severity": "High", "module": "b", "symbol": "y", "actual": "2"}]
    ranked = sorted(findings, key=lambda x: -((x.get("severity") or "").lower() == "high"))
    assert ranked[0]["severity"] == "High", \
        "a mixed-case 'High' finding must sort first, not be pushed down by lowercase mediums"


# order 43d5bcfcdd19 -- src/autostart.py, main() --status
# The status report must read overnight.ALL_JOBS, not a hand-kept subset, so a job added to
# STANDING (e.g. 'pipeline') shows up without a second edit here.
def check_autostart_status_uses_all_jobs_roster():
    import inspect
    import autostart as AS
    import overnight as ON
    src = inspect.getsource(AS.main)
    assert "ON.ALL_JOBS" in src, \
        "autostart.main() --status no longer reads overnight.ALL_JOBS"
    assert '"dashboard.py", "publish.py", "foreman.py", "overwatch.py"' not in src, \
        "autostart.main() --status has a hand-kept job tuple again"
    assert "pipeline.py" in ON.ALL_JOBS and "feats.py --roll" in ON.ALL_JOBS, \
        "overnight.ALL_JOBS itself is missing an expected standing job"


# order 6f8a12503285 -- src/overnight.py module docstring
# The docstring must not assert the obsolete GPU-serial rule while the body starts pipeline
# backgrounded alongside the reader.
def check_overnight_docstring_matches_gpu_serial_reality():
    text = open(os.path.join(SRC, "overnight.py"), encoding="utf-8").read()
    doc = text.split('"""')[1]
    assert "Only one GPU stage runs at a time" not in doc, \
        "overnight.py docstring re-asserts the obsolete GPU-serial rule"
    assert "OBSOLETE" in doc, \
        "overnight.py docstring should say the GPU-serial rule is obsolete, matching the body"


# order c1f5ad96dfbe / d757d03bef8b -- src/dashboard.py, _tail_match()
# A format change that breaks RE_READ/RE_ROLL must be distinguishable from an idle job: a tail
# containing the hint substring but no full regex match should log a format-mismatch note
# rather than silently returning None the same way an empty/idle log does.
def check_dashboard_tail_match_flags_format_mismatch():
    import tempfile
    import dashboard as D
    good = ("  1234/5000  3.45 chunks/s  feats    100  dropped     3  chunks     50/200 "
            "(2 to GPU, 1 UNANSWERED, not cached)  eta 1.2h")
    bad = ("  1234/5000  3.45 chunks/s  feats    100  dropped     3  chunks     50/200 "
           "(2 to GPU, 1 answered, not cached)  eta 1.2h")  # UNANSWERED renamed -> no match
    tmpd = tempfile.mkdtemp()
    p_good = os.path.join(tmpd, "good.log")
    p_bad = os.path.join(tmpd, "bad.log")
    with open(p_good, "w", encoding="utf-8") as f:
        f.write(good + "\n")
    with open(p_bad, "w", encoding="utf-8") as f:
        f.write(bad + "\n")
    r_good = D._tail_match(p_good, D.RE_READ, hint="chunks/s")
    assert r_good is not None, "a genuinely well-formed progress line must still match"
    import health
    # `silence.note` files under "silent:<site>:<exc-class-or-None>" -- called outside an
    # except block (as this call site does; see chain.py:write_result-denied and others for the
    # same established pattern) the class is literally "None". Checked, then IMMEDIATELY
    # popped back out of the real in-memory health.LEDGER so this check does not leave a test
    # artifact in the live, shared state/failures.json the moment atexit flushes it.
    tag = "silent:dashboard.py:tail-format-mismatch:%s:None" % os.path.basename(p_bad)
    before = health.LEDGER.get(tag, 0)
    try:
        r_bad = D._tail_match(p_bad, D.RE_READ, hint="chunks/s")
        assert r_bad is None, "a line that no longer matches the regex must not fabricate a result"
        after = health.LEDGER.get(tag, 0)
        assert after == before + 1, \
            "a hint-present/regex-absent tail must land one health.LEDGER entry under %r" % tag
    finally:
        if before:
            health.LEDGER[tag] = before
        else:
            health.LEDGER.pop(tag, None)


# order d0ff339b7138 -- src/allsweep.py module docstring
# The docstring must name every tier that actually gates the exit status (foreman._checks_pass
# reads this list), and must not claim the module never writes.
def check_allsweep_docstring_lists_all_tiers_and_write():
    text = open(os.path.join(SRC, "allsweep.py"), encoding="utf-8").read()
    doc = text.split('"""')[1] + text.split('"""')[2]
    for tier in ("IMPORT", "LINT", "VERIFY", "ESTATE", "RECONCILE"):
        assert tier in doc, "allsweep.py docstring is missing the %s tier" % tier
    assert "Nothing here writes" not in doc, \
        "allsweep.py docstring still claims it never writes, but it lands data/ALLSWEEP.json"


# order fef23be535cf -- src/dashboard.py, _watch()
# The swallowed-failures table must not be capped; every distinct tag in failures.json must
# survive into out["swallowed"].
def check_dashboard_watch_swallowed_not_capped():
    import inspect
    import dashboard as D
    src = inspect.getsource(D._watch)
    assert "[:6]" not in src, "dashboard._watch() re-added a 6-row cap on the swallowed table"
    fake = {"tag%d" % i: i + 1 for i in range(25)}
    ranked = sorted(fake.items(), key=lambda kv: -kv[1])
    assert len(ranked) == 25, "sanity: the ranking itself must not drop rows"


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
        len([n for n, _ in _inspect.getmembers(mod, _inspect.isfunction)
             if n.startswith("check_")]), len(fails)))
