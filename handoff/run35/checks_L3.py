# run35, LOCAL batch L3 -- proposed verify_math/drill checks for the orders worked this batch.
# Runnable Python. Each block is commented with the order id and its target file. These are
# PROPOSALS for verify_math.py / drill.py to adopt -- this agent owns assay.py, rigor.py,
# physics.py, anchors.py, handbuilt.py, profile.py, custodes.py, magnitude.py, and NOT
# verify_math.py or drill.py, and did not add them there. verify_math.py/drill.py were also
# off-limits to even RUN this batch (order c349a51ee2c5, mutation run in flight against
# assay.py), so every check below was exercised by hand against the fixed source instead.

import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HERE, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


# order 0a77fa43d821 -- src/assay.py, _check_scores()
# NONE must be recognised by EQUALITY like its two sibling sentinels, not by IDENTITY -- a NONE
# that arrives via json.loads (the ordinary path for every score read off disk) is a distinct
# string object from the module's own A.NONE literal and CPython does not intern it.
def check_assay_none_sentinel_by_equality():
    import assay as A
    v = json.loads('"none"')          # a fresh, non-interned "none" -- what disk data looks like
    assert v is not A.NONE, "test invalid: json.loads('\"none\"') is now interned to A.NONE"
    # Must NOT raise. Before the fix this raised AssayIntegrityError because `v is NONE` failed
    # and the value fell through to the not-a-number branch.
    A._check_scores({"ruin": 2.1, "reach": v})


# order d5b264f8a196 -- src/assay.py, _check_scores()
# Off-scale and unknown-axis refusals must list EVERY offender (Hard Rule 0: rank, never
# truncate). Both lists in this function were sliced with [:6].
def check_assay_check_scores_no_truncation():
    import assay as A
    axes = list(A.WEIGHTS)
    assert len(axes) > 6, "test invalid: fewer than 7 axes in WEIGHTS, cannot exercise the cap"
    off_scale = {k: 99.0 for k in axes}          # every real axis, all off-scale
    try:
        A._check_scores(off_scale)
        raise AssertionError("expected AssayIntegrityError for off-scale scores")
    except A.AssayIntegrityError as e:
        for k in axes:
            assert k in str(e), f"off-scale message dropped axis {k!r} past a truncation"
    unknown = {f"notanaxis{i}": 1.0 for i in range(8)}
    try:
        A._check_scores(unknown)
        raise AssertionError("expected AssayIntegrityError for unknown axes")
    except A.AssayIntegrityError as e:
        for k in unknown:
            assert k in str(e), f"unknown-axis message dropped {k!r} past a truncation"


# order b5e63bb91ca2 -- src/assay.py -- DISPROVEN, not a fix. Guards against the finding
# resurfacing: band_for_quantity/interval_from_hands/null_instrument are NOT dead code -- they
# are exactly the three functions verify_math.py section 34 exercises directly (A.<name>(...)).
# A future dead-code sweep must grep verify_math.py, not just src/, before calling something dead.
def check_assay_three_functions_are_not_dead():
    vm = open(os.path.join(SRC, "verify_math.py"), encoding="utf-8").read()
    for fn in ("band_for_quantity", "interval_from_hands", "null_instrument"):
        assert f"A.{fn}(" in vm, (
            f"assay.{fn} no longer called from verify_math.py -- if this is deliberate, the "
            f"dead-code finding (order b5e63bb91ca2) should be re-opened, not re-disproven blind")


# order 3cf9bafb03ed -- src/profile.py module docstring
# The advertised address width must track address_space.TOTAL_BITS, not a literal that can go
# stale the way address_space.py's own table already did once.
def check_profile_docstring_bit_width_matches_address_space():
    import address_space as AS
    doc = open(os.path.join(SRC, "profile.py"), encoding="utf-8").read()
    needle = f"the {AS.TOTAL_BITS}-bit shelfmark in base32"
    assert needle in doc, (
        f"profile.py's module docstring does not say '{needle}' -- it has drifted from "
        f"address_space.TOTAL_BITS ({AS.TOTAL_BITS}) again")


# order 6d0ecf0fdc3c -- src/profile.py, main()'s ROUND TRIP check
# decode() must not be verified against itself. Re-encoding what decode() extracts and comparing
# to the original profile string is the only way genre/register/features/band/attested_axes are
# actually exercised.
def check_profile_round_trip_is_not_tautological():
    import profile as P
    src = open(os.path.join(SRC, "profile.py"), encoding="utf-8").read()
    assert 'd["profile"] != r["profile"]' not in src, (
        "profile.py's ROUND TRIP check compares decode()'s echoed argument to itself again")
    features = {axis: tbl[0][0] for axis, tbl in P.AXES}
    p = P.encode(4242, "unclassified", "classical", features, "unassayed", 0)
    d = P.decode(p)
    re_encoded = P.encode(d["address"], d["genre"], d["register"], d["features"],
                          d["band"], d["attested_axes"])
    assert re_encoded == p, "profile encode/decode is not a true round trip"
    # A genuinely wrong decode of a non-address field must be catchable: corrupt the genre code
    # in the string directly (not through decode(), which is what we are testing) and confirm
    # re-encoding the ORIGINAL fields would not match the corrupted string -- i.e. the comparison
    # has teeth, not that it always passes.
    corrupted = p[:3] + "xx" + p[5:]              # mangle the genre/register field in place
    try:
        d2 = P.decode(corrupted)
        re2 = P.encode(d2["address"], d2["genre"], d2["register"], d2["features"],
                       d2["band"], d2["attested_axes"])
        assert re2 != p or corrupted == p, (
            "round-trip check would not have caught a corrupted profile string")
    except ValueError:
        pass       # decode() refusing an invalid pattern is also an acceptable teeth-check


# order 52f1a4d278ea -- src/anchors.py, __main__ comment
# The comment must not assert a stale exit status. Run the module's own check and confirm the
# comment's CURRENT claim (exits 0, ladder holds) matches what actually happens.
def check_anchors_comment_matches_current_exit():
    import subprocess
    src = open(os.path.join(SRC, "anchors.py"), encoding="utf-8").read()
    assert "It exits 1 TODAY" not in src, (
        "anchors.py __main__ comment still claims a stale exit-1 state")
    r = subprocess.run([sys.executable, os.path.join(SRC, "anchors.py")],
                       capture_output=True, text=True, timeout=120,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, (
        f"anchors.py exited {r.returncode}; comment says the ladder holds and it should be 0 "
        f"-- if this legitimately flips again, the __main__ comment needs the same treatment "
        f"order 52f1a4d278ea gave it, not a silent re-drift")


# order 61ca2388367c -- src/rigor.py, main()'s MDL section
# The unconditional "every declared cost sits above its MDL floor" print must be reachable only
# when nothing in the loop was actually below floor.
def check_rigor_mdl_finding_is_guarded():
    src = open(os.path.join(SRC, "rigor.py"), encoding="utf-8").read()
    i = src.index('FINDING: every declared cost sits above its MDL floor')
    # walk backwards from the print to the nearest 'if'/'else' guarding it
    window = src[max(0, i - 400):i]
    assert "_underpriced" in window, (
        "rigor.py's MDL FINDING is no longer guarded on the loop's own below-floor result")


# order 71dfbc345f2a -- src/handbuilt.py, main()'s --full sheet loop
# --full must not raise on a sheet whose axis scores are the string sentinels
# (INAPPLICABLE/UNESTIMABLE), never just real numbers. Zalama is the load-bearing case.
def check_handbuilt_full_handles_string_scores():
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(SRC, "handbuilt.py"), "--full"],
                       capture_output=True, text=True, timeout=180,
                       encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert r.returncode == 0, f"handbuilt.py --full exited {r.returncode}: {r.stderr[-2000:]}"
    assert "Zalama" in r.stdout, "handbuilt.py --full output did not reach the Zalama sheet"
    assert "unestimable" in r.stdout, (
        "handbuilt.py --full did not print any 'unestimable' axis score -- Zalama's "
        "string-sentinel axes are the case this check exists for")


# order b124bcb46f86 -- src/handbuilt.py, The Sentry's why_missed
# The stated roster size in prose must track len(ROSTER), not a stale literal.
def check_handbuilt_sentry_roster_count_matches():
    import handbuilt as H
    n = len(H.ROSTER)
    assert f"one of these {_num2word(n)}" in H.ROSTER["The Sentry"]["why_missed"].lower() or \
           str(n) in H.ROSTER["The Sentry"]["why_missed"], (
        f"The Sentry's why_missed names a roster size that does not match len(ROSTER) == {n}")


def _num2word(n):
    return {4: "four", 9: "nine"}.get(n, str(n))


# order 80ca00f00cbe -- src/physics.py, --table help text
# The --table help text must describe what the flag actually does (suppress the worked examples
# printed by default), not restate the unconditional default behaviour as though it were gated.
def check_physics_table_help_matches_behavior():
    import subprocess
    bare = subprocess.run([sys.executable, os.path.join(SRC, "physics.py")],
                          capture_output=True, text=True, timeout=60,
                          encoding="utf-8", errors="replace").stdout
    tabled = subprocess.run([sys.executable, os.path.join(SRC, "physics.py"), "--table"],
                            capture_output=True, text=True, timeout=60,
                            encoding="utf-8", errors="replace").stdout
    assert tabled in bare or bare.startswith(tabled), (
        "physics.py --table no longer strictly suppresses the worked examples -- re-check the "
        "help text still matches")
    assert len(tabled) < len(bare), "physics.py --table produced no less output than the default"


# order c70075814337 -- src/physics.py, kinetic()/joules_for() sign checks
# A negative mass or negative volume must raise, matching the sibling refusals in
# sphere_volume()/binding_energy() two functions below.
def check_physics_negative_inputs_refused():
    import physics as P
    for bad_call in (lambda: P.kinetic(-5.0, 10.0), lambda: P.joules_for(-10.0, "rock", "pulv")):
        try:
            bad_call()
            raise AssertionError(f"{bad_call} did not raise on a negative magnitude input")
        except ValueError:
            pass
    # and the ordinary path is undisturbed
    assert P.kinetic(75.0, 10.0) == 3750.0
    assert P.joules_for(1000.0, "concrete", "pulv") > 0


# order 85a1d426681d -- src/magnitude.py, main()'s --calibrate exit code
# --calibrate must exit 0 only when EVERY charter benchmark reproduced its band, not on any
# nonzero count.
def check_magnitude_calibrate_exit_requires_full_reproduction():
    src = open(os.path.join(SRC, "magnitude.py"), encoding="utf-8").read()
    assert "return 0 if calibrate() else 1" not in src, (
        "magnitude.py main() reverted to treating calibrate()'s band_hits count as a bool")
    assert "calibrate() == len(BENCHMARKS)" in src, (
        "magnitude.py main() no longer requires full charter reproduction to exit 0")


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("check_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except Exception as e:
                fails += 1
                print(f"FAIL  {name}: {e}")
    sys.exit(1 if fails else 0)
