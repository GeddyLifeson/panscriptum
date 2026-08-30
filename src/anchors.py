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
    # THE DECLARED LADDER, floor to ceiling. OWNER RULING 2026-08-25 on the Goku/Yggdrasil pair:
    # *"obviously the tree holds higher."*
    #
    # This resolves M34 in the direction that costs nothing to trust: the INSTRUMENT was right and
    # the DECLARATION was wrong. The assay scored Yggdrasil 6.18 and Goku 5.42 while this list
    # asserted the reverse, and the invariant dutifully reported a violation on every run for
    # weeks. Reading the two entries against the charter's own axes, the assay's answer is the
    # defensible one -- Yggdrasil is a REACH and CONTINUITY object, a structure holding nine
    # realms whose removal is a cosmological event, while Goku's case is built on RUIN and
    # CELERITY. The ladder's rungs are rung-threat scales, not combat records, and a being who
    # can destroy a planet is not thereby above the thing nine worlds hang from.
    #
    # AND THE SWORD/SKATE GUY PAIR, ruled separately the same day: *"the assay is right here for
    # the sword vs skate guy."* So `A Sword` (0.10) sits BELOW `The Skate Guy` (0.22), where the
    # instrument had it all along.
    #
    # BOTH violations resolved the same way, and that is the finding worth keeping. The invariant
    # had been red for weeks and was read as *the assay has drifted from its calibration*. It had
    # not. The DECLARED LADDER was wrong at two of its four steps, and the instrument was right at
    # both -- so the check was reporting a real disagreement while everyone assumed it named the
    # wrong culprit. A failing invariant says two things disagree; it does not say which is lying,
    # and this file's own message ("a reading about the ASSAY") quietly asserted that it did.
    #
    # The scores are defensible on the charter's own axes in both cases. Yggdrasil is a REACH and
    # CONTINUITY object -- a structure nine realms hang from -- against Goku's RUIN and CELERITY;
    # rungs are rung-threat scales, not combat records. And an inert blade has no agency to score
    # on most axes at all, while a person who acts does, however modestly.
    order = ["A Sword", "The Skate Guy", "Goku", "Yggdrasil", "The Seat of the Creator"]
    # AN ASSAY REFUSAL IS NOT A READING AT THE BAND FLOOR (order cdec5a03b731). This was
    # `vals[name] = A.LADDER.index(a["anchor"]) + (res.get("decimal") or 0.0)`, and `assay.assay`
    # has two documented paths that return `decimal: None` with a reason -- no worksheet
    # (assay.py:886, honesty theorem H5) and "no axis scored from cited feats; band-only"
    # (assay.py:897). The first is unreachable here because every call passes
    # `worksheet='anchors.py'`; the SECOND is one edit away in a file whose scores are
    # hand-written constants. `or 0.0` turned that refusal into a ladder value pinned at the band
    # floor and then the monotone invariant graded it as though it were a reading, with the
    # reason printed by `run()` and thrown away -- "A CHECK WHOSE RESULT IS PRINTED AND DISCARDED
    # CANNOT FAIL", which is this file's own __main__ comment. It also collapsed a genuine
    # decimal of 0.0 into the refusal case, so the two could not be told apart at all.
    #
    # `bool` is excluded explicitly because it is a subclass of `int`: a `decimal` of True would
    # otherwise arrive here as the number 1 and grade cleanly.
    scored = {name: a for name, a, _res, _inst, _col in rows}
    vals, refused = {}, []
    for name, a, res, inst, col in rows:
        dec = res.get("decimal")
        if isinstance(dec, bool) or not isinstance(dec, (int, float)):
            refused.append((name, str(res.get("reason") or "no reason recorded")))
            continue
        vals[name] = A.LADDER.index(a["anchor"]) + dec

    # EVERY INVARIANT THIS FILE GRADES, AND EVERY ONE OF THEM CAN FAIL (order 237356c82d06).
    #
    # run() computed an ASSAY, an INSTRUMENT reading, a COLLEGE interval and a bit value for
    # each of the five anchors, printed all four, and gated the exit code on exactly one thing:
    # the monotone ordering. Each anchor's `note` states a testable claim and none was tested.
    # The ceiling's is the plainest -- "every faculty pins at 30 regardless of score, and the
    # Transcendence Grade must read V. A ceiling that keeps climbing is a broken ruler" is an
    # assertion written as a comment, and a comment cannot fail. These are the same claims,
    # graded, so the file this docstring calls the place where "anything that reads absurdly
    # here is a defect in the instrument" can now SAY so rather than print a paragraph.
    verdicts = []

    def verdict(label, passed, detail=""):
        verdicts.append((bool(passed), label, detail))

    # -- 1. the declared ladder must name every anchor, and only anchors (order 1618d9790f0d).
    # The monotone loop below iterates `order`, so an anchor added to ANCHORS and not here was
    # scored, printed and silently excluded from the only check that can fail this file -- the
    # way to add a new reference was also the way to add an ungraded one. The reverse, a name in
    # `order` with no ANCHORS row, raised KeyError on the unguarded `vals[n]` lookup instead of
    # reporting the gap. `order` is NOT derived from ANCHORS: its ordering is the owner's
    # declared ladder and carries the 2026-08-25 ruling recorded above, which is exactly what
    # the instrument is being checked against. Membership is asserted instead, which keeps the
    # declaration and refuses the drift.
    # MEMBERSHIP IS ASKED OF `scored`, NOT OF `vals`. They were the same dict until an assay
    # refusal stopped putting its anchor in `vals`; asking this question of `vals` would report a
    # refused anchor as ABSENT FROM ANCHORS, which is a different fault with a different repair.
    ungraded = sorted(set(scored) - set(order))
    unanchored = [n for n in order if n not in scored]
    verdict("the declared ladder grades every anchor",
            not ungraded and not unanchored,
            ("in ANCHORS but ungraded: %s; " % ", ".join(ungraded) if ungraded else "")
            + ("named in the ladder but absent from ANCHORS: %s"
               % ", ".join(unanchored) if unanchored else ""))

    # -- 1b. and every anchor must have produced a DECIMAL to order by. Graded ahead of the
    # monotone check because it decides whether that check has anything to read (cdec5a03b731).
    verdict("every anchor produced a decimal",
            not refused,
            "; ".join("%s: %s" % (n, why) for n, why in refused))

    # -- 2. the ordering itself. Skipped rather than crashed if a name is missing above, and
    # skipped rather than graded against a floor value if an assay declined to produce one.
    mono_evaluated = False
    if unanchored:
        mono = False
        mono_detail = "not evaluated -- the ladder names an anchor that does not exist"
    elif refused:
        mono = False
        mono_detail = ("not evaluated -- %s produced no decimal, so there is no reading to place "
                       "on the ladder" % ", ".join(n for n, _why in refused))
    else:
        mono_evaluated = True
        mono, prev = True, None
        for n in order:
            if prev is not None and vals[n] < vals[prev]:
                mono = False
            prev = n
        mono_detail = "  ".join("%s %.2f" % (n, vals[n]) for n in order)
    verdict("monotone floor -> ceiling", mono, mono_detail)

    # -- 3. each anchor's OWN stated claim, in the words of its note.
    by_name = {name: (a, res, inst, col) for name, a, res, inst, col in rows}

    def _struck(a):
        return [k for k, v in a["scores"].items() if v == A.INAPPLICABLE]

    # (anchor, the claim in its note's own terms, a test over that anchor's four readings
    # -> (held, what was read)). Driven off a table rather than written out five times so a
    # sixth reference is one line, and so the missing-anchor case is handled once below.
    CLAIMS = [
        ("The Seat of the Creator",
         "the ceiling SATURATES rather than overflows: every faculty pins at 30 and the "
         "Transcendence Grade reads V",
         lambda a, res, inst, col: (
             bool(inst.get("faculties"))
             and all(str(v).startswith("30") for v in (inst.get("faculties") or {}).values())
             and inst.get("transcendence_grade") == "V",
             "faculties=%r grade=%r" % (inst.get("faculties"), inst.get("transcendence_grade")))),
        ("The Skate Guy",
         "the floor is COMPLETE: an ordinary person carries all eleven axes, none struck, "
         "several genuinely at nil",
         lambda a, res, inst, col: (
             len(a["scores"]) == 11 and not _struck(a) and bool(res.get("axes_nil")),
             "axes=%d struck=%s nil=%s"
             % (len(a["scores"]), _struck(a) or "none", res.get("axes_nil")))),
        ("A Sword",
         "the object is neither flattered nor filed as a category error: volition alone is "
         "struck as INAPPLICABLE, and it still assays",
         lambda a, res, inst, col: (
             _struck(a) == ["volition"] and bool(res.get("moth_number")),
             "struck=%s assay=%s" % (_struck(a), res.get("moth_number") or res.get("reason")))),
        ("Goku",
         "the standard is the one case where Volition is IDENTIFIED: theta is a number, "
         "not a status",
         lambda a, res, inst, col: (
             isinstance(a["scores"].get("volition"), (int, float)),
             "volition=%r" % (a["scores"].get("volition"),))),
        ("Yggdrasil",
         "the unconscious case is UNESTIMABLE rather than nil: a winless node has divergent "
         "theta, which is not the same as being weak",
         lambda a, res, inst, col: (
             a["scores"].get("volition") == A.UNESTIMABLE,
             "volition=%r" % (a["scores"].get("volition"),))),
    ]
    for _name, _label, _test in CLAIMS:
        got = by_name.get(_name)
        if got is None:
            # A REFERENCE NAMED HERE AND ABSENT FROM ANCHORS IS A FINDING, NOT A TRACEBACK.
            # The unguarded `by_name[name]` this replaces raised KeyError and took the whole
            # file down before any other claim was graded -- the same unguarded-lookup shape
            # order 1618d9790f0d reported for `vals[n]`, reintroduced one section lower.
            verdict(_label, False,
                    "%r is named by this check and absent from ANCHORS, so the claim could not "
                    "be tested at all" % _name)
            continue
        _held, _detail = _test(*got)
        verdict(_label, _held, _detail)

    ok = all(p for p, _l, _d in verdicts)
    for passed, label, detail in verdicts:
        print(f"  {'HELD    ' if passed else 'VIOLATED'}  {label}")
        if detail:
            print(f"              {detail}")

    # THE MESSAGE NO LONGER NAMES A CULPRIT (order e954295c02e1). The comment ninety lines above
    # records the finding worth keeping from the 2026-08-25 ruling -- "A failing invariant says
    # two things disagree; it does not say which is lying, and this file's own message ('a
    # reading about the ASSAY') quietly asserted that it did" -- and the message was never
    # changed. It said the assay had drifted; the ruling found the DECLARED LADDER wrong at two
    # of its four steps and the instrument right at both, and this project spent weeks reading a
    # red invariant as assay drift on the strength of that sentence. The printed values line is
    # the useful half and is kept.
    #
    # Only printed when the check actually RAN. `mono` is also False when the ordering was
    # skipped, and telling a reader the anchors do not ascend when nothing was compared would be
    # the same fault in the other direction; the skipped case already states itself in
    # `mono_detail` above.
    if mono_evaluated and not mono:
        print("\n  INVARIANT VIOLATED. The anchors do not ascend from floor to ceiling: the "
              "assay and the DECLARED LADDER above disagree. This does not say which is wrong "
              "-- on 2026-08-25 the declared ladder was wrong at two of four steps and the "
              "instrument was right at both. Read the scores against the charter's axes before "
              "assuming the assay drifted.")

    # ------------------------------------------------------- REPORTED, NOT GRADED: an OWNER
    # QUESTION, and it is the thing the missing assertions were hiding.
    #
    # `assay.INSTRUMENT_WINDOWS` is (30, 30) from M5 upward, and the Instrument computes
    # `min(30, round(lo + (s/10) * span))` -- with span 0 that returns 30 for EVERY score from
    # 0.0 to 9.9. So Goku at M5 prints all six faculties at 30, identical to the M10 ceiling,
    # beside his own anchor comment reading `acumen=4.0, # not a planner, and the charter should
    # not pretend otherwise`. The faculties carry no information at all for any entity at M5 or
    # above, which is most of the library's headline entities.
    #
    # It is PRINTED rather than graded because the window table is charter material (X.6 §6) and
    # may be a declared convention -- saturation at the top of the Ladder is arguably the point.
    # Ruling on it is the owner's, not this script's. What this script can do, and now does, is
    # refuse to let it sit unsaid: the sentence below runs on every invocation whether or not
    # anything failed, which is the difference between a known convention and a broken ruler
    # nobody has looked at.
    collapsed = [b for b in A.LADDER if A.INSTRUMENT_WINDOWS[b][0] == A.INSTRUMENT_WINDOWS[b][1]]
    if collapsed:
        print(f"\n  OWNER QUESTION (reported, not graded): assay.INSTRUMENT_WINDOWS is a "
              f"ZERO-WIDTH window at {len(collapsed)} of {len(A.LADDER)} bands "
              f"({', '.join(collapsed)}), so every faculty reads "
              f"{A.INSTRUMENT_WINDOWS[collapsed[0]][1]} there regardless of axis score -- an "
              f"entity at {collapsed[0]} and the M10 ceiling print the same six numbers. Either "
              f"that is charter X.6 §6's declared saturation or the Instrument stops measuring "
              f"most of the library above {collapsed[0]}; this file cannot rule on which.")
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
    # It exited 1 at run #26: `A Sword` (0.10) sat below `The Skate Guy` (0.22) and `Goku` (5.42)
    # below `Yggdrasil` (6.18). The owner ruling of 2026-08-25 (above, at the `order` list) found
    # the DECLARED LADDER wrong rather than the instrument and reordered it to match the scores,
    # so the invariant now holds and this exits 0. That is a reading about the ladder that was
    # fixed, not a claim that this check can no longer fail -- it still exits 1 the moment the
    # assay and the declared order disagree again, which is the entire reason it says so out loud
    # instead of throwing `ok` away.
    _rows, _ok = run()
    sys.exit(0 if _ok else 1)
