# run35, SECOND OPINION batch -- proposed verify_math/drill checks for the 22 ruff/vulture
# orders worked this batch. Runnable Python. Each block names the order id, the rule, and what
# it guards against regressing. These are PROPOSALS for verify_math.py / drill.py to adopt --
# this agent does not own those files and did not add them there.

import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)


def _read(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return f.read()


# order c0eed39c5201 -- B023, src/catalogue_web.py
# The two progress= lambdas inside the discovery/fetch loops must keep binding `_short` as a
# default argument. This file already documents having shipped the un-bound version once
# (heartbeat lines naming the wrong class); losing the default silently reopens that exact bug.
def check_catalogue_web_progress_lambdas_bind_short():
    text = _read("catalogue_web.py")
    assert text.count("lambda d, t, _short=_short:") == 2, \
        "catalogue_web.py: expected both progress= callbacks to bind _short as a default arg " \
        "(B023 closure-capture guard) -- found a different count"


# order 3bfa520db5a5 -- B008, src/pipeline.py (WAIVED, not fixed -- guard the waiver's premise)
# pipeline.py's _judged_something must keep freezing len(batch) as a default argument. This is
# the B008 site the batch waived BECAUSE it prevents a B023 bug; if a future edit moves the
# len(batch) call into the function body, it reintroduces the closure bug the waiver relied on.
def check_pipeline_judged_something_still_freezes_batch_len():
    text = _read("pipeline.py")
    assert "def _judged_something(g, _n=len(batch)):" in text, \
        "pipeline.py: _judged_something no longer freezes len(batch) via a default argument " \
        "-- this was accepted as SAFE specifically because it avoids a B023 closure bug; " \
        "moving the len(batch) read into the function body would silently reintroduce it"


# order 847b46302956 -- B904, seven files sharing one escalation-chain import guard
# Every 'except ImportError as _esc_gone: raise SystemExit(...)' site added `from _esc_gone`.
# Regressing any one back to a bare raise loses the traceback chain this batch added.
def check_escalation_import_guards_chain_from_esc_gone():
    files = ["dashboard.py", "foreman.py", "overwatch.py", "pipeline.py", "read.py",
             "publish.py", "overnight.py"]
    missing = []
    for name in files:
        text = _read(name)
        if "except ImportError as _esc_gone:" in text and "from _esc_gone" not in text:
            missing.append(name)
    assert not missing, \
        "escalation-chain ImportError guard(s) lost their 'from _esc_gone' chaining: %s" % missing


# order e02f6ce1e851 -- B905, src/sevenfold.py (the one deliberate non-fix)
# zip(TIERS, c) inside shelve() must stay WITHOUT strict=True -- SOURCE_TIERS/WORLD_TIERS are a
# real prefix/suffix split of TIERS, so c is shorter than TIERS whenever depth < len(TIERS), and
# strict=True would raise on every call that is not the unused 5-tier default.
def check_sevenfold_shelve_zip_stays_non_strict():
    text = _read("sevenfold.py")
    fn = text.split("def shelve(")[1].split("\ndef ")[0]
    assert "dict(zip(TIERS, c))" in fn, \
        "sevenfold.py shelve(): zip(TIERS, c) shape changed -- re-check whether strict=True " \
        "was added; SOURCE_TIERS/WORLD_TIERS are prefixes/suffixes of TIERS so lengths differ " \
        "by design whenever depth < len(TIERS)"


# order 5ff878fe008f / 8c4f1940e9df -- S110/S112 waiver premise
# The waiver for both rules rested on silence.py's own audit() already tracking every sampled
# site as 'silent'. If silence.py's silent/observed classification logic changes shape, this
# batch's reasoning (and the NOT_FILED entries citing it) should be re-checked, not assumed.
def check_silence_audit_still_reports_silent_handlers():
    import silence
    rows = silence.audit()
    assert rows, "silence.audit() returned nothing -- S110/S112 waiver relied on this running"
    assert any(r["silent"] for r in rows), \
        "silence.audit() no longer reports any silent handlers -- re-examine the S110/S112 " \
        "NOT_FILED waivers in secondopinion.py, which cited this as corroboration"


# order e1f0e884806f -- BLE001 waiver premise
# The BLE001 waiver in secondopinion.py's NOT_FILED cites a specific measured ratio (521 of 672
# handlers already observed). This does not need to hold exactly forever, but a silence.audit()
# that suddenly reports mostly-silent handlers would mean the waiver's premise had inverted.
def check_silence_audit_majority_observed_not_silent():
    import silence
    rows = silence.audit()
    silent = sum(1 for r in rows if r["silent"])
    assert silent < len(rows) / 2, \
        "silence.audit(): silent handlers are now the majority (%d of %d) -- the BLE001/S110/" \
        "S112 waivers in secondopinion.py's NOT_FILED assumed the opposite; worth re-arguing" \
        % (silent, len(rows))


# order 12bfbb78ca49 -- RUF023, src/silence.py
# swallow.__slots__ must stay sorted -- purely cosmetic, but cheap to keep guarded so it is
# never silently re-broken by an unrelated edit that appends a new slot at the end.
def check_swallow_slots_sorted():
    import silence
    assert list(silence.swallow.__slots__) == sorted(silence.swallow.__slots__), \
        "silence.swallow.__slots__ is no longer sorted"


# orders 7f65cdb7725c (RUF007) and part of e02f6ce1e851 (B905) -- three pairwise conversions
# The zip(x, x[1:]) -> itertools.pairwise(x) conversions must not regress back to zip, which
# would also silently reopen a B905 "add strict=" false-positive against a deliberately
# unequal-length pairing.
def check_pairwise_conversions_stayed_pairwise():
    checks = [
        ("hostcheck.py", "itertools.pairwise(clean)"),
        ("sevenfold.py", "itertools.pairwise(bounds)"),
        ("tiers.py", "itertools.pairwise(CUTS)"),
    ]
    bad = []
    for name, needle in checks:
        if needle not in _read(name):
            bad.append("%s: missing %r" % (name, needle))
    assert not bad, "itertools.pairwise conversion(s) regressed: %s" % bad
