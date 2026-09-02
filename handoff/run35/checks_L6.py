# run35, LOCAL batch L6 -- proposed verify_math/drill checks for the orders worked this batch.
# Runnable Python. Each block is commented with the order id and its target file. These are
# PROPOSALS for verify_math.py / drill.py to adopt -- this agent owns recover_folder_records.py,
# ingest_doc.py, catalogue_aurora.py, catalogue_codex.py, overwatch.py, mutate.py,
# secondopinion.py, publish.py, weave.py, reference.py, sevenfold.py, codewatch.py, ledger.py,
# ledger_guard.py, axis_correlation.py, chain.py, feats_index.py, estate.py, and NOT
# verify_math.py or drill.py, and did not add them there. Running verify_math.py, drill.py or
# mutate.py was off-limits this batch (a mutation run in flight, order c349a51ee2c5), so every
# check below was exercised by hand against the fixed source instead -- see AUDIT_L6.md for what
# was actually run and observed. None of these import or invoke mutate.py.

import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HERE, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


# --------------------------------------------------------------------------------------------
# A REHEARSAL MUST NOT LAND IN THE LEDGER A PERSON READS TO FIND REAL FAULTS.
#
# Three checks in this file deliberately drive a guard into recording a failure, and
# `silence.note` calls `health.record`, which writes `state/failures.json` -- the operational
# ledger `standards` grades from, the dashboard polls, and `foreman.triage_swallowed` names
# classes out of. Per order 842025c83c3c that ledger is deliberately never cleared, so anything
# a probe puts in it is permanent.
#
# Measured 2026-09-01 by instrumenting `health.record` over a whole battery run: these three
# added one entry each, every run. The live counts agreed -- `mutate.py:reap-incomplete` 31,
# `mutate.py:reap-skipped-live-owner` 35, `reference.py:shelfmark-shape` 30, against roughly
# thirty runs. Not one was a fault. A real misreaped sandbox would have arrived
# indistinguishable from thirty copies of this rehearsal.
#
# Same shape and same two rules as `drill._deliberately_failing` and verify_math's
# `_no_ledger_vm`: scope it to the single call that is SUPPOSED to fail, so an unrelated fault
# raised during the same check is still recorded, and go on asserting the RETURN VALUE rather
# than the absence of a ledger entry. Nothing under test is suppressed here -- only its echo.
# verify_math.py's §20z watches `health.record` for the whole run and will name any probe that
# starts leaking again.
import contextlib as _ctx_L6      # noqa: E402
import health as _H_L6            # noqa: E402


@_ctx_L6.contextmanager
def _no_ledger_L6():
    """Suppress the ledger echo of a deliberately-provoked guard, and nothing else."""
    _saved = _H_L6.record
    _H_L6.record = lambda *_a, **_k: None
    try:
        yield
    finally:
        _H_L6.record = _saved


# order 0b15581132d0 -- src/secondopinion.py, NOT_FILED
# Every code named as a waiver must actually be selectable by RUFF_RULES, or the waiver can
# never match a finding and the count of "deliberate divergences" is fiction.
def check_secondopinion_not_filed_codes_are_selected():
    import secondopinion as S
    selected_prefixes = tuple(p for p in S.RUFF_RULES.split(",") if p)
    for code in S.NOT_FILED:
        assert code.startswith(selected_prefixes), (
            "%s is waived in NOT_FILED but RUFF_RULES=%r cannot ever select it"
            % (code, S.RUFF_RULES))


# order 3593a47f0f31 -- src/secondopinion.py, report()
# The per-code summary line must disclose when it has truncated the ranked list, the same way
# file_orders() already does with "(+N more)".
def check_secondopinion_report_discloses_truncation():
    import secondopinion as S
    got = {
        "ruff": {"status": "RAN", "findings": [
            {"code": "C%02d" % i, "file": "x.py", "line": 1, "message": "m", "tool": "ruff"}
            for i in range(9)  # 9 distinct codes, one hit each -- past the top-6 print window
        ]},
        "vulture": {"status": "RAN", "findings": []},
        "detect-secrets": {"status": "RAN", "findings": []},
    }
    import io
    import contextlib
    buf = io.StringIO()

    def fake_mine_says(paths=None):
        return {"liveness": 0, "silence": 0, "secrets": 0}

    def fake_run(paths=None):
        return got

    orig_run, orig_mine = S.run, S.mine_says
    S.run, S.mine_says = fake_run, fake_mine_says
    try:
        with contextlib.redirect_stdout(buf):
            S.report()
    finally:
        S.run, S.mine_says = orig_run, orig_mine
    assert "more code" in buf.getvalue(), "9 codes printed with no disclosure of the other 3"


# order 6d729c0d6ca5 -- src/secondopinion.py, docstring/comment prose
# The three hand-written prose counts for the same measurement must not disagree with each
# other any more (they used to read 449 / 456 / 449 -- two different numbers claiming to be the
# same fact). Static check on the source text.
def check_secondopinion_no_stale_conflicting_counts():
    path = os.path.join(SRC, "secondopinion.py")
    text = open(path, encoding="utf-8").read()
    assert "449" not in text and "456" not in text, (
        "a stale hardcoded blind-except count reappeared in secondopinion.py")


# order 237a61e89859 -- src/mutate.py, main()'s --check-flaky --no-confirm path
# flaky_gates() must be scored against the SAME gate set baseline() was built from, or a
# --no-confirm run compares a gate (e.g. drill) it never ran a baseline for and refuses forever.
def check_mutate_flaky_gates_uses_same_gates_as_baseline():
    path = os.path.join(SRC, "mutate.py")
    text = open(path, encoding="utf-8").read()
    assert "flaky_gates(root, base, gates=gates + confirm)" in text, (
        "main() no longer passes the matching gate set to flaky_gates()")


# order 3320036fb65c -- src/mutate.py, reap_orphans()
# A sandbox shutil.rmtree could not actually delete (the junction case) must NOT be reported as
# removed. ignore_errors=True never raises, so the only honest signal is checking the path
# afterward.
def check_mutate_reap_orphans_does_not_over_report():
    import mutate as M
    import tempfile
    root = tempfile.gettempdir()
    name = M.SANDBOX_PREFIX + "checkL6undeleteable"
    p = os.path.join(root, name)
    os.makedirs(p, exist_ok=True)
    # Hold a file open inside it on the platforms where that blocks deletion; on platforms where
    # it doesn't, this check degrades to confirming reap_orphans agrees with what is on disk
    # either way, which is still the property being tested.
    held_path = os.path.join(p, "locked.txt")
    f = open(held_path, "w")
    try:
        # WRAPPED: the held-open file is the fixture, so reap_orphans is SUPPOSED to fail to
        # delete this sandbox and note `mutate.py:reap-incomplete` -- and on a busy machine it
        # also notes `reap-skipped-live-owner` for whatever real sandbox is in flight. Both were
        # landing in the live ledger once per battery run. The assertion below is on the
        # RETURNED list against what is on disk, which is unchanged.
        with _no_ledger_L6():
            removed = M.reap_orphans(older_than=-1)  # -1s cutoff: everything qualifies by age
        still_there = os.path.isdir(p)
        assert (p in removed) != still_there, (
            "reap_orphans's removed-list disagrees with what is actually on disk for %s" % p)
    finally:
        f.close()
        import shutil
        shutil.rmtree(p, ignore_errors=True)


# order c9f8d161a09f -- src/mutate.py, _pid_alive() / _pid_alive_windows()
# On Windows without psutil, a definitely-dead PID must read as dead, not unconditionally alive
# (the old fallback), or an orphaned lock from a hard-killed run can never be marked stale.
def check_mutate_pid_alive_windows_detects_dead_pid():
    import mutate as M
    if os.name != "nt":
        return  # the fallback this check targets is Windows-only; nothing to test elsewhere
    assert M._pid_alive_windows(os.getpid()) is True
    assert M._pid_alive_windows(999_999_999) is False, (
        "a PID nothing holds must read as dead, not err toward ALIVE unconditionally")


# order 31e504c0df88 -- src/catalogue_aurora.py, module docstring
# The docstring's headline element count must not exceed what parse_folder() actually returns
# for the two named folders, by more than a small, explained margin.
def check_catalogue_aurora_docstring_count_not_inflated():
    import catalogue_aurora as CA
    a = CA.parse_folder("drfirestorm")
    b = CA.parse_folder("the-elements-beyond")
    measured = len(a) + len(b)
    # The docstring should quote a number no larger than what this run actually measured, not a
    # larger figure asserted once and never re-checked.
    doc = CA.__doc__ or ""
    import re as _re
    m = _re.search(r"yield ([\d,]+)\s+elements", doc)
    assert m, "docstring no longer states a headline element count to check"
    claimed = int(m.group(1).replace(",", ""))
    assert claimed <= measured + 5, (
        "docstring claims %d elements; parse_folder measures %d today" % (claimed, measured))


# order f1bbfe251913 -- src/sevenfold.py, main()'s occupancy line
# Occupancy must be computed against SOURCE_CAPACITY (the 3 tiers sources actually occupy), not
# the full 5-tier CAPACITY -- dividing by the wrong denominator understated occupancy 49x.
def check_sevenfold_occupancy_uses_source_capacity():
    import sevenfold as SF
    assert SF.SOURCE_CAPACITY == SF.SPAN ** len(SF.SOURCE_TIERS)
    assert SF.SOURCE_CAPACITY < SF.CAPACITY, "source capacity should be the smaller, real figure"
    path = os.path.join(SRC, "sevenfold.py")
    text = open(path, encoding="utf-8").read()
    assert "len(coords)/SOURCE_CAPACITY" in text, (
        "occupancy line no longer divides by SOURCE_CAPACITY")


# order 4c9a939daeea -- src/reference.py, shelfmark()
# A tier_key/lower_rungs shape wider than RUNGS (7 entries) must degrade to a clamped mark, not
# raise IndexError, and a narrower/wider upper() must not silently mislabel with a hardcoded "3".
def check_reference_shelfmark_handles_oversized_shape():
    import reference as R
    rec = {"tier_key": "a.b.c.d.e", "lower_rungs": ["1", "2", "3", "4", "5"]}
    # WRAPPED: the oversized shape IS the fixture, so `reference.shelfmark` is supposed to
    # notice it and note `reference.py:shelfmark-shape`. That class stood at 30 in the live
    # ledger, one per battery run, describing this rehearsal and nothing else.
    with _no_ledger_L6():
        mark = R.shelfmark(rec)   # must not raise IndexError
    assert mark.startswith("Ω"), "shelfmark should still render the Omega-prefixed address"


# order b729b23ebc8e -- src/overwatch.py, review() / _anchored()
# Neither function should carry a parameter its body never reads.
def check_overwatch_no_dead_parameters():
    import inspect
    import overwatch as O
    assert "ledger" not in inspect.signature(O.review).parameters, (
        "review() still carries an unread ledger parameter")
    assert "module" not in inspect.signature(O._anchored).parameters, (
        "_anchored() still carries an unread module parameter")


# order 9c1e9ba00cc2 -- src/ledger_guard.py, assert_intact() / seal()
# A seal() that fails to write must not be silently ignored by assert_intact() -- it must raise,
# the same way every other integrity failure in this module does.
def check_ledger_guard_assert_intact_raises_on_failed_seal():
    import ledger_guard as LG
    orig_seal = LG.seal
    orig_verify = LG.verify_chain
    orig_check = LG.check_all
    LG.check_all = lambda: {}
    # Mirrors the real signature since 2026-09-02: `verify_chain(with_acknowledged=False)`
    # returns a 2-tuple, or a 3-tuple with the acknowledged list when asked. `assert_intact`
    # asks for the 3-tuple, so a stub that cannot answer it breaks the probe, not the subject.
    LG.verify_chain = (lambda with_acknowledged=False:
                       (True, [], []) if with_acknowledged else (True, []))
    LG.seal = lambda: None   # simulate the on-disk write failing
    try:
        try:
            LG.assert_intact()
            raised = False
        except LG.LedgerViolation:
            raised = True
        assert raised, "assert_intact() must raise when seal() reports failure (returns None)"
    finally:
        LG.seal, LG.verify_chain, LG.check_all = orig_seal, orig_verify, orig_check


# order f9041b1208ba -- src/publish.py, scrub_text()
# A FIXTURE_MARKER on one line of a multi-line value must not silence a live secret sitting on
# a DIFFERENT line of that same value.
def check_publish_scrub_text_marker_is_line_scoped():
    import publish as P
    marker_line = P.FIXTURE_MARKER + " (documentation example above)"
    secret_line = "ghp_" + ("a" * 24)
    s = marker_line + "\n" + secret_line
    out = P.scrub_text(s)
    assert "[redacted]" in out, "a secret on a line without the marker must still be redacted"
    assert marker_line in out, "the marker's own line should be left alone"


# order 930550461fba -- src/recover_folder_records.py, module docstring
# The docstring's "Why this exists" numbers must not overstate the gap by an order of magnitude
# relative to what is actually on data/SWEEP_ROLL.json + data/records/ right now.
def check_recover_folder_records_docstring_matches_roll():
    import json as _j
    roll_path = os.path.join(HERE, "data", "SWEEP_ROLL.json")
    roll = _j.load(open(roll_path, encoding="utf-8"))
    zero = [r for r in roll if r.get("entry_count", 0) == 0]
    import recover_folder_records as RF
    doc = RF.__doc__ or ""
    import re as _re
    m = _re.search(r"^(\d+) of the (\d+) sources", doc, _re.M)
    assert m, "docstring no longer states a headline entry_count:0 count to check"
    claimed_gap, claimed_total = int(m.group(1)), int(m.group(2))
    # Not a strict equality: the roll is live and can move between the doc being written and
    # this check running. The point is that a doc claiming ~17x the live gap should fail loudly.
    if len(roll) == claimed_total:
        assert claimed_gap <= max(len(zero) * 3, len(zero) + 5), (
            "docstring claims %d sources with entry_count 0; roll shows %d today"
            % (claimed_gap, len(zero)))


# order c97aaf6b1296 -- src/ingest_doc.py, mine() state-file read
# The silence.note tag here must be a durable content label, not a line number that will drift
# the next time this file is edited (this exact tag was already off by one line when filed).
def check_ingest_doc_no_numeric_note_tags():
    path = os.path.join(SRC, "ingest_doc.py")
    text = open(path, encoding="utf-8").read()
    import re as _re
    for m in _re.finditer(r'silence\.note\("ingest_doc\.py:([^"]+)"\)', text):
        tag = m.group(1)
        assert not tag.isdigit(), (
            "ingest_doc.py has a bare line-number silence.note tag again: %r" % tag)


# order e9986e00bdec -- src/ingest_doc.py, extract()
# pages.json must be written through silence.write_json (atomic), not a bare truncating open()
# + json.dump -- it is the only machine copy of a book the library cannot re-fetch.
def check_ingest_doc_extract_writes_pages_atomically():
    path = os.path.join(SRC, "ingest_doc.py")
    text = open(path, encoding="utf-8").read()
    assert 'silence.write_json(os.path.join(d, "pages.json")' in text, (
        "extract() no longer writes pages.json through silence.write_json")


# order 25ec11447b4c -- src/weave.py, pair_weights() / idf_table() consumption
# Documents (does not delete, per house doctrine) that pair_weights() has no callers anywhere
# in src/ and that idf/N from idf_table() are unused after unpacking in main(). A regression
# here would mean someone wired it back up without removing the "SUPERSEDED" marker comment, or
# vice versa -- either way this check should be revisited by a human, not auto-resolved.
def check_weave_pair_weights_still_marked_superseded():
    path = os.path.join(SRC, "weave.py")
    text = open(path, encoding="utf-8").read()
    assert "SUPERSEDED, NOT CALLED ANYWHERE" in text, (
        "the dead-code marker above pair_weights() is gone -- was it revived or deleted?")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("check_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print("PASS", fn.__name__)
        except Exception as e:
            failed += 1
            print("FAIL", fn.__name__, "--", type(e).__name__, str(e))
    print("\n%d/%d passed" % (len(fns) - failed, len(fns)))
    raise SystemExit(1 if failed else 0)
