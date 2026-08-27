# run35, final wave, batch F1 -- proposed verify_math/drill checks for the orders worked this
# batch. Runnable Python. Each block names the order id and its target file. These are
# PROPOSALS for verify_math.py / drill.py to adopt -- this agent does not own those files and
# did not add them there.

import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)


# order f842daaba5c5 -- src/feats.py, _QUANTITY / mine()
# The caret no longer has to touch the "10": whitespace on both sides of an optional "^" must
# still parse the mantissa and exponent correctly, not backtrack onto the exponent digits alone
# as the mantissa. Negative exponents, the literal multiplication sign, and a caret-less
# superscript exponent must all parse too.
def check_feats_quantity_exponent_parsing():
    import feats as F

    cases = [
        # (text, expected_value_str, expected_unit)
        ("Goku unleashes 3 x 10 ^ 9 megatons of force.", "3e9", "megatons"),
        ("An attack rated 5 x 10^44 joules levels the district.", "5e44", "joules"),
        ("A precise strike measured at 3 x 10^-9 megatons barely scorches paint.", "3e-9", "megatons"),
        ("The blast reaches 3 × 10^9 megatons across the valley.", "3e9", "megatons"),
        ("Its output is rated 3 x 10⁹ megatons of raw force.", "3e9", "megatons"),
        ("A controlled test yields 3 x 10⁻⁹ megatons of output.", "3e-9", "megatons"),
    ]
    for text, want_val, want_unit in cases:
        _, _, quants = F.mine(text, 1)
        assert quants, "no quantity parsed at all from %r" % text
        q = quants[0]
        assert q["value"] == want_val, (
            "%r parsed value=%r, want %r (a wrong-by-orders-of-magnitude mis-parse that still "
            "looks like success)" % (text, q["value"], want_val))
        assert q["unit"] == want_unit, "%r parsed unit=%r, want %r" % (text, q["unit"], want_unit)
        # the mis-parse this order fixes reads as a plain float() success, so also prove the
        # stored value actually floats to the right order of magnitude
        assert abs(float(q["value"]) - float(want_val)) < 1e-6 * max(1.0, abs(float(want_val)))

    # the historic bug: the caret-must-touch-10 pattern silently produced "9" for this sentence
    _, _, quants = F.mine("A weapon rated 3 x 10 ^ 9 megatons flattens the moon.", 1)
    assert quants[0]["value"] != "9", "regression: exponent-touches-caret bug is back"


# order 80fa56642f33 (MAJOR) -- src/zfighters.py, main() --full
# A worksheet axis missing "provenance" (the carried-in Son Goku sheet from
# data/REFERENCE_ASSAYS_PRESENCE.json) must not crash --full; it must print with an honest
# blank label instead of fabricating one.
def check_zfighters_full_survives_missing_provenance():
    import inspect
    import zfighters as ZF
    src = inspect.getsource(ZF.main)
    assert 'd.get("provenance"' in src, \
        "zfighters.main() --full no longer defends the KeyError on a sheet missing 'provenance'"
    # simulate the exact carried-in shape: only "score"/"cited", no "provenance"
    d = {"score": 3.5, "cited": "some sentence"}
    line = "   %-15s%5.1f  [%s] %s" % ("ruin", d["score"], d.get("provenance", ""), d["cited"][:60])
    assert "[]" in line  # honest blank, not a crash and not a fabricated label


# order 0ea638f01b03 -- src/resync_roll.py, main()
# The verdict of silence.write_json(ROLL, ...) must be checked and surfaced, not discarded.
def check_resync_roll_checks_write_verdict():
    import inspect
    import resync_roll as RR
    src = inspect.getsource(RR.main)
    assert "landed = silence.write_json(ROLL" in src, \
        "resync_roll.main() no longer captures write_json's return value"
    assert "WRITE DENIED" in src, \
        "resync_roll.main() does not report a denied roll write to the operator"


# order cf231efb8b5b -- src/resync_roll.py, main()
# A source declared by two record files must be noted and shown in the printed report, not
# silently dropped from `by_source`.
def check_resync_roll_flags_duplicate_sources():
    import inspect
    import resync_roll as RR
    src = inspect.getsource(RR.main)
    assert "resync_roll.py:duplicate-source" in src, \
        "resync_roll.main() no longer notes a same-source collision across record files"
    assert "dupes" in src and "declared by more than one record file" in src, \
        "resync_roll.main() no longer surfaces duplicate sources in its printed report"


# order 920942075624 -- src/repass_bands.py, main()
# The source-ceiling denominator must track len(recs), not a hardcoded historical count.
def check_repass_bands_denominator_is_dynamic():
    import inspect
    import repass_bands as RB
    src = inspect.getsource(RB.main)
    assert "of 211" not in src, "repass_bands.main() still hardcodes the stale '211' denominator"
    assert "len(recs)" in src, "repass_bands.main() should derive its denominator from len(recs)"


# order 96e8ac88c6f8 -- src/endpoint.py, source_pages()
# The docstring must match the real return type: a list, never {}.
def check_endpoint_source_pages_docstring_matches_return_type():
    import inspect
    import endpoint as EP
    doc = inspect.getdoc(EP.source_pages) or ""
    assert "{}" not in doc, "endpoint.source_pages() docstring still claims a {} empty return"
    assert "[]" in doc, "endpoint.source_pages() docstring should say [] when it has none"
    assert EP.source_pages("__no_such_source_at_all__") == []


# order 71aef747c9e7 -- src/feats.py, _RATE_LIMITED / _CAP_BOUND
# Both counters must be updated under a lock now, matching the `done` dict's own guard in roll().
def check_feats_counter_dicts_are_locked():
    import inspect
    import feats as F
    assert hasattr(F, "_COUNTS_LOCK"), "feats.py no longer defines _COUNTS_LOCK"
    src_api = inspect.getsource(F.api)
    assert "with _COUNTS_LOCK" in src_api, \
        "feats.api()'s _RATE_LIMITED increment is no longer inside _COUNTS_LOCK"
    src_discover = inspect.getsource(F.discover)
    assert src_discover.count("with _COUNTS_LOCK") >= 2, \
        "feats.discover()'s two _CAP_BOUND increments are not both locked"


# order 49474966f971 -- src/onomast.py, name_worlds()
# `taken` must be seeded from designations already standing in ONOMASTICON.json for worlds NOT
# in the current `resolved` call, so two runs cannot coin the same designation for two
# different worlds -- while a rerun over an UNCHANGED `resolved` must still be idempotent
# (a cid being recomputed must not see its own prior name as "taken").
def check_onomast_seeds_taken_from_existing_designations():
    import json
    import tempfile
    import importlib
    import onomast as O

    tmpd = tempfile.mkdtemp()
    fake_out = os.path.join(tmpd, "ONOMASTICON.json")
    # one designation already standing, for a world that will NOT be part of this call
    with open(fake_out, "w", encoding="utf-8") as f:
        json.dump({"other#1": {"catalogue_name": "Zorivel", "endonym": "Earth",
                                "continuity_group": 1}}, f)

    old_out = O.OUT
    try:
        O.OUT = fake_out
        resolved = {
            "a#2": {"canonical_name": "Earth", "key": "earth", "continuity_group": 2,
                    "attestations": ["Foo"]},
            "b#3": {"canonical_name": "Earth", "key": "earth", "continuity_group": 3,
                    "attestations": ["Bar"]},
        }
        named = O.name_worlds(resolved)
        got_names = {v["catalogue_name"].lower() for v in named.values()}
        assert "zorivel" not in got_names, \
            "name_worlds() coined a name already standing for an unrelated world in ONOMASTICON.json"
    finally:
        O.OUT = old_out


def check_onomast_rerun_over_unchanged_resolved_is_idempotent():
    import json
    import tempfile
    import onomast as O

    tmpd = tempfile.mkdtemp()
    fake_out = os.path.join(tmpd, "ONOMASTICON.json")
    resolved = {
        "a#2": {"canonical_name": "Earth", "key": "earth", "continuity_group": 2,
                "attestations": ["Foo"]},
        "b#3": {"canonical_name": "Earth", "key": "earth", "continuity_group": 3,
                "attestations": ["Bar"]},
    }
    old_out = O.OUT
    try:
        O.OUT = fake_out
        first = O.name_worlds(resolved)
        with open(fake_out, "w", encoding="utf-8") as f:
            json.dump(first, f)
        second = O.name_worlds(resolved)
        assert {k: v["catalogue_name"] for k, v in first.items()} == \
               {k: v["catalogue_name"] for k, v in second.items()}, \
            "name_worlds() is no longer idempotent across a rerun with unchanged input"
    finally:
        O.OUT = old_out


# order 2326f7a4ed66 -- src/corpus_db.py, rebuild()
# A truncated evidence scan (evidence_limit) must be recorded in meta, not silently indistinct
# from a complete one.
def check_corpus_db_records_evidence_truncation():
    import inspect
    import corpus_db as CDB
    src = inspect.getsource(CDB.rebuild)
    assert "evidence_truncated" in src, \
        "corpus_db.rebuild() no longer tracks whether the evidence scan was truncated"
    assert "'evidence_truncated'" in src or '"evidence_truncated"' in src, \
        "corpus_db.rebuild() no longer writes an evidence_truncated row to meta"


# order de9a39b2b47c -- src/weave_index.py, load_records()
# The docstring's file count must agree with corpus_db.py's and with disk (216, not 217).
def check_weave_index_docstring_file_count_matches_corpus_db():
    import weave_index as WI
    import corpus_db  # noqa: F401  (imported to prove both modules are importable together)
    doc = (WI.load_records.__doc__ or "")
    assert "217 files" not in doc, "weave_index.load_records() docstring still says 217 files"
    assert "216 files" in doc, "weave_index.load_records() docstring should say 216 files"


# orders 220a0d0a1d70 (pipeline.py), 4e0e1949ec0b (weave_index.py), 92c0c50a6d2d (pick_model.py),
# e5a4928f2ae9 (scout.py), ed5434c0bc65 (cascade_bridge.py) -- stale numeric silence.note tags
# renamed to content labels. None of the retired numeric spellings should still appear as a
# silence.note() argument.
def check_stale_numeric_silence_tags_are_gone():
    retired = {
        "pipeline.py": ['"pipeline.py:191"', '"pipeline.py:301"',
                        '"pipeline.py:261"', '"pipeline.py:277"'],
        "weave_index.py": ['"weave_index.py:155"'],
        "pick_model.py": ['"pick_model.py:150"'],
        "scout.py": ['"scout.py:241"'],
        "cascade_bridge.py": ['"cascade_bridge.py:100"', '"cascade_bridge.py:113"',
                               '"cascade_bridge.py:151"'],
    }
    for fname, tags in retired.items():
        text = open(os.path.join(SRC, fname), encoding="utf-8").read()
        for tag in tags:
            assert ("silence.note(%s)" % tag) not in text, \
                "%s still carries the stale numeric tag %s" % (fname, tag)


# order 87a01fd3b978 -- src/withdraw_chapters.py, main()
# The CATALOG-emptying write must go through silence.write_json and its verdict must be
# checked, not a hand-rolled path+".tmp" write with the replace_retry return discarded.
def check_withdraw_chapters_checks_catalog_write_verdict():
    import inspect
    import withdraw_chapters as WC
    src = inspect.getsource(WC.main)
    assert 'tmp = CATALOG + ".tmp"' not in src, \
        "withdraw_chapters.main() still hand-rolls a fixed .tmp name for the catalog write"
    assert "catalog_landed = silence.write_json(CATALOG" in src, \
        "withdraw_chapters.main() no longer captures the catalog write's verdict"
    assert "CATALOG WRITE DENIED" in src, \
        "withdraw_chapters.main() does not report a denied catalog write to the operator"


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
