#!/usr/bin/env python3
"""
ANCHOR VALIDATION — the whole instrument, exercised at floor, standard and ceiling.

WHY ANCHORS AND NOT MORE UNIT TESTS
-----------------------------------
verify_math.py checks that each formula computes what it claims. That is necessary and it is not
sufficient: a set of individually correct formulas can still compose into an instrument that reads
absurdly at the extremes, and nothing in a per-formula test would notice. Instruments are validated
by anchoring -- you measure known references at the bottom, the middle and the top of the range and
check the whole chain end to end.

Five references, chosen to span every axis of variation the library has:

    THE SKATE GUY      an ordinary person. The floor. Everything about him is small and nothing
                       about him is missing -- he has all eleven axes, several at nil.
    GOKU               the standard. The best-attested contestant in the omniverse, and therefore
                       the ONE case where Volition (theta) is genuinely identified.
    THE SEAT OF THE    the ceiling. M10, where every scale saturates and the instrument must
    CREATOR            cap rather than overflow.
    A SWORD            an object. Inert, persistent, wielded rather than acting.
    YGGDRASIL          living but unconscious. The case that broke the contest model.

The point is to find breakage, not to display success. Anything that reads absurdly here is a
defect in the instrument, however clean its unit tests were.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import physics as PH       # noqa: E402
import assay as A          # noqa: E402


# ==================================================================================================
# The six axes with no entry in BAND_EDGES are not unscalable -- they are on OTHER existing scales,
# which was true all along and written down nowhere. axis_score() silently returns None for them,
# leaving an assessor no guidance, so the scales are named here.
# ==================================================================================================
NON_ENERGETIC_AXES = {
    "transgression": "bits of exception length (X.2 §4, Rissanen). Use transgression_bits().",
    "volition":      "theta, the Bradley-Terry latent strength (Part Three). Identified only on a "
                     "strongly connected contest graph (Ford 1957).",
    "acumen":        "bits per epoch of prediction-planning advantage (X.6 §3).",
    "discernment":   "bits per epoch of veridical perception (X.6 §3).",
    "suasion":       "bits per epoch of credible influence (X.6 §3).",
    "vector":        "RUNGS TRAVERSABLE of the 17-rung Ladder (I.9: 'cross-rung travel Goku "
                     "cannot follow'). Scored by attestation footprint.",
}
LADDER_RUNGS = 17


def vector_score(rungs_traversable):
    """Vector on the 0-10 decimal scale, derived from the Ladder's own height. No new quantity."""
    r = max(0, min(LADDER_RUNGS, rungs_traversable))
    return round(10.0 * r / LADDER_RUNGS, 2)


# ==================================================================================================
# THE ANCHORS
# ==================================================================================================
#
# Each `scores` dict uses the four statuses deliberately. Where a value is a number it is derived
# in the comment; where it is NONE / UNESTIMABLE / INAPPLICABLE the reason is given, because those
# are claims and must be defensible.
ANCHORS = {}

# -------------------------------------------------------------------------------- THE SKATE GUY
_kick = PH.kinetic(75, 10)              # a person and a board at ~10 m/s: ~3.75e3 J
ANCHORS["The Skate Guy"] = dict(
    kind="person", anchor="M0",
    note=("the floor. An ordinary human, and the test is that NOTHING about him is missing: he "
          "carries all eleven axes, several genuinely at nil. If the instrument cannot read an "
          "ordinary person it cannot read anything."),
    scores=dict(
        ruin=A.axis_score(_kick, "M0", "ruin"),          # ~3.75e3 J of delivered kinetic energy
        celerity=A.axis_score(2.5, "M0", "celerity"),    # ~2.5 deliberate actions per second
        reach=A.axis_score(2.0, "M0", "reach"),          # arm plus board, ~2 m
        sustain=A.axis_score(3.6e3, "M0", "sustain"),    # an hour at the park
        continuity=A.axis_score(1e2, "M0", "continuity"),  # removed once, stays removed
        transgression=A.NONE,        # breaks no law of physics whatsoever. A finding, not a gap.
        vector=A.NONE,               # cannot leave his own rung at all
        volition=A.UNESTIMABLE,      # no attested contests; theta is not identified for him
        acumen=1.0, discernment=1.5, suasion=2.0,        # unremarkable, but PRESENT
    ),
    attestation="Witnessed",
)

# ------------------------------------------------------------------------------------------ GOKU
ANCHORS["Goku"] = dict(
    kind="person", anchor="M5",
    note=("the standard, and the single case where Volition is genuinely identified: he has more "
          "attested contests than anything else in the omniverse, and they are densely "
          "interconnected. If theta is estimable anywhere, here."),
    scores=dict(
        ruin=A.axis_score(2e42, "M5", "ruin"),           # star-order output
        celerity=A.axis_score(3e5, "M5", "celerity"),    # combat tempo
        reach=A.axis_score(5e9, "M5", "reach"),          # planetary-to-system engagements
        sustain=A.axis_score(4e5, "M5", "sustain"),      # days-long engagements
        continuity=A.axis_score(3e42, "M5", "continuity"),  # dies and returns, repeatedly
        transgression=7.5,           # ki is not conserved; a real and expensive exception
        vector=vector_score(6),      # instantaneous transmission, afterlife, some planes
        volition=9.4,                # SCORED: dense, strongly connected contest graph
        acumen=4.0,                  # not a planner, and the charter should not pretend otherwise
        discernment=8.0,             # ki-sense is high-bandwidth veridical perception
        suasion=7.5,                 # reliably turns enemies into allies
    ),
    attestation="Witnessed",
)

# ------------------------------------------------------------- THE SEAT OF THE CREATOR (ceiling)
ANCHORS["The Seat of the Creator"] = dict(
    kind="office", anchor="M10",
    note=("the ceiling. Everything must SATURATE rather than overflow: the Instrument's M10 window "
          "is (30, 30), so every faculty pins at 30 regardless of score, and the Transcendence "
          "Grade must read V. A ceiling that keeps climbing is a broken ruler."),
    scores=dict(
        ruin=10.0, celerity=10.0, reach=10.0, sustain=10.0, continuity=10.0,
        transgression=10.0,          # authors the law rather than excepting it
        vector=vector_score(17),     # every rung, by definition of the seat
        volition=A.UNESTIMABLE,      # contests nothing; there is nothing to contest with
        acumen=10.0, discernment=10.0, suasion=10.0,
    ),
    attestation="Transcribed",       # nobody has witnessed it; the honest grade is low
)

# ------------------------------------------------------------------------------ A SWORD (object)
ANCHORS["A Sword"] = dict(
    kind="object", anchor="M0",
    note=("an object. Inert, persistent, WIELDED rather than acting. The test is whether the four "
          "statuses can express 'a thing that does nothing by itself but lasts forever' without "
          "either flattering it or filing it as a category error."),
    scores=dict(
        ruin=A.axis_score(1.5e3, "M0", "ruin"),          # a cut delivered by an arm
        celerity=A.NONE,             # initiates nothing; its tempo is the wielder's
        reach=A.axis_score(1.0, "M0", "reach"),
        sustain=A.axis_score(1e9, "M0", "sustain"),      # centuries in a scabbard: genuinely high
        continuity=A.NONE,           # broken, it stays broken
        transgression=A.NONE,        # steel breaks no law
        vector=A.NONE,               # goes where it is carried
        volition=A.INAPPLICABLE,     # not a contestant. Equipment is not a party to a contest.
        acumen=A.NONE,               # 0 bits/epoch. The question is well posed; the answer is nil.
        discernment=A.NONE,
        suasion=A.NONE,
    ),
    attestation="Instrumented",
)

# ------------------------------------------------------ YGGDRASIL (living, unconscious)
ANCHORS["Yggdrasil"] = dict(
    kind="living, unconscious", anchor="M6",
    note=("living but unconscious, and the case that broke the contest model. Its whole magnitude "
          "lives in CONTINUITY and REACH -- it spans nine worlds and endures Nidhoggr eternally. "
          "Volition is unestimable rather than nil: winless nodes have divergent theta (Ford), "
          "which is not the same as being weak."),
    scores=dict(
        ruin=A.NONE,                 # destroys nothing. Not weak -- simply not a destroyer.
        celerity=A.NONE,             # acts on no perceptible tempo
        reach=A.axis_score(1e18, "M6", "reach"),         # spans nine worlds
        sustain=A.axis_score(1e8, "M6", "sustain"),
        continuity=A.axis_score(5e51, "M6", "continuity"),  # survives Ragnarok itself
        transgression=6.0,           # a tree that holds nine worlds is an expensive exception
        vector=A.NONE,               # it does not travel; it is the thing travelled upon
        volition=A.UNESTIMABLE,      # winless node: theta divergent, not identified
        acumen=A.UNESTIMABLE,        # plants do process information; nobody has measured this one
        discernment=A.UNESTIMABLE,
        suasion=A.NONE,              # persuades no one
    ),
    attestation="Reconstructed",
)


def run():
    import custodes as CU
    import rigor as R
    rows = []
    print("=" * 100)
    print("ANCHOR VALIDATION — the instrument at floor, standard and ceiling")
    print("=" * 100)

    for name, a in ANCHORS.items():
        res = A.assay(a["anchor"], a["scores"], attestation=a["attestation"],
                      worksheet="anchors.py")
        inst = A.instrument(a["anchor"],
                            {k: v for k, v in a["scores"].items()
                             if isinstance(v, (int, float))},
                            worksheet="anchors.py")
        col = CU.convene(a["anchor"], a["scores"], attestation=a["attestation"],
                         worksheet="anchors.py")
        rows.append((name, a, res, inst, col))

        print(f"\n{'-' * 100}")
        print(f"{name}   [{a['kind']}]   anchor {a['anchor']}")
        print(f"  {a['note']}")
        print(f"  ASSAY      {res.get('moth_number') or res.get('reason')}")
        print(f"  coverage   {res.get('axis_coverage')}   "
              f"nil={res.get('axes_nil')}   unestimable={res.get('axes_unestimable')}")
        print(f"  inapplicable struck: "
              f"{[k for k, v in a['scores'].items() if v == A.INAPPLICABLE] or 'none'}")
        fac = inst.get("faculties")
        if fac:
            print(f"  INSTRUMENT {fac}   Grade {inst.get('transcendence_grade')}")
        print(f"  COLLEGE    ± {col.get('interval')}   "
              f"prior {col.get('prior_divergence_share')} / "
              f"attestation {col.get('attestation_floor_share')}")
        bit = R.measure_bit_value(a["anchor"])
        print(f"  one axis point at {a['anchor']} = {bit:.2f} bits")

    # ---------------------------------------------------------------- invariants across anchors
    print(f"\n{'=' * 100}")
    print("INVARIANTS")
    print("=" * 100)
    order = ["The Skate Guy", "A Sword", "Yggdrasil", "Goku", "The Seat of the Creator"]
    vals = {}
    for name, a, res, inst, col in rows:
        vals[name] = A.LADDER.index(a["anchor"]) + (res.get("decimal") or 0.0)
    prev = None
    ok = True
    for n in order:
        if prev is not None and vals[n] < vals[prev]:
            ok = False
        prev = n
    print(f"  monotone floor -> ceiling : {ok}")
    for n in order:
        print(f"     {n:<28} {vals[n]:6.2f}")
    if not ok:
        print("\n  INVARIANT VIOLATED. The anchors do not ascend from floor to ceiling, which "
              "means the instrument disagrees with the ordering it was calibrated against. "
              "This is a reading about the ASSAY, not about this script.")
    return rows, ok


if __name__ == "__main__":
    # A CHECK WHOSE RESULT IS PRINTED AND DISCARDED CANNOT FAIL, AND `allsweep` RUNS THIS FILE.
    #
    # Until run #26 `run()` computed `ok`, printed it, threw it away and returned `rows`, so the
    # process exited 0 whether the instrument's floor-to-ceiling ordering held or not. `allsweep`
    # lists this module under "the instrument" and judges it by exit code, so a violated invariant
    # read to every automated caller as a clean instrument -- the project's lesson 9 exactly, in
    # the one script whose entire job is to fail when the assay drifts. `audit.py` gets this right
    # one file over and is the pattern copied here.
    #
    # It exits 1 TODAY: measured run #26, `A Sword` (0.10) sits below `The Skate Guy` (0.22) and
    # `Goku` (5.42) below `Yggdrasil` (6.18). Whether that ordering or the scores are wrong is an
    # instrument question for the owner (NEXT_STEPS), not something this script may paper over --
    # but it must now say so out loud instead of exiting 0.
    _rows, _ok = run()
    sys.exit(0 if _ok else 1)
