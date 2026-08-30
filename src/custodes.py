#!/usr/bin/env python3
"""
THE CUSTODES — one standpoint per degree of freedom, and the interval as their disagreement.

WHY THERE MUST BE MORE THAN THREE
---------------------------------
Vol. 0.5 Theorem 4 already makes the ± a real object rather than a decoration: the interval IS the
spread of the Hands' readings, and the charter's own table shows it working --

    Kenshiro, post-Raoh    AVAR 3.52 · QUILL 3.58 · MOTH 3.49   ->   A M3.53 ± 0.11

with the decomposition that makes it useful: Goku's interval is 89% PRIOR DIVERGENCE and will
never narrow, because the disagreement is not about feats; Kenshiro's is 83% ATTESTATION FLOOR and
would narrow with fieldwork. Two intervals of similar width, two entirely different objects.

But three Hands can only span a three-dimensional disagreement, and the Assay has more ways to move
than that. Every input that can be varied ALONE and change the answer is a direction the reading
can be wrong in, and a direction with no Custos standing in it is a direction nobody is checking.

So the number of Custodes is not a stylistic choice. It is a count, and this module derives it:

    **one Custos per independent degree of freedom in the assay computation.**

A degree of freedom qualifies when varying it alone moves the output AND it cannot be written as a
function of the others. Ten survive that test. Three are the charter's existing Hands, mapped onto
the scheme rather than replaced; seven are the directions that had no one standing in them.

ON DASEIN, AND WHY THESE ARE NOT OPINIONS
-----------------------------------------
The owner's framing is exact and worth preserving: the arguments for and against a god's existence
have different Daseins natively. The cosmological argument reasons from causation, the ontological
from concept, the teleological from design, the moral from value, the experiential from encounter.
These do not disagree about a shared body of evidence. They disagree about what EVIDENCE IS,
because the world shows up differently to each -- as a causal chain, as a concept, as a design, as
a claim on conduct, as a meeting.

A Custos is that, not a bias. Each has a native mode in which the world discloses itself, and that
mode determines what counts as a feat before any weighing begins. Quill does not distrust the
Chain of Record; she was THERE, and presence is what showing-up means for her. Avar is not
indifferent to what Quill saw; unratified sight is not yet world for him.

This is why the divergence is irreducible in principle and not merely in practice. No quantity of
further evidence collapses two Daseins into one, because the further evidence must itself arrive
through one of them. That is precisely what Theorem 4 measures, and precisely why the charter can
say Goku's ± will never narrow while Kenshiro's will.

WHAT THIS BUYS
--------------
The interval stops being a lookup table. Before this module, assay() computed ± from a hardcoded
dict of attestation grades plus a coverage penalty -- a declared constant wearing a formula's
clothes. After it, the ± is a MEASURED DISPERSION of ten independent readings, and its split into
reducible and irreducible parts is computed rather than asserted.
"""
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import assay as A          # noqa: E402


# ==================================================================================================
# 1. THE DEGREES OF FREEDOM — derived from the computation, not chosen
# ==================================================================================================
#
# Each entry: the lever in the code, and why it is irreducible to the others.
DEGREES_OF_FREEDOM = {
    "nomination":     "WHICH feat is the ceiling. Set by sampling (14 of N), so a thin sample "
                      "reads low. Independent of trust: you can perfectly trust an account of "
                      "the wrong feat.",
    "reduction":      "HOW a described act becomes joules. Independent of which act: two "
                      "assessors can agree on the deed and differ on its energy.",
    "attestation":    "HOW FAR the account can be trusted. Independent of the reduction: a "
                      "well-specified conversion of a rumour is still a rumour.",
    "applicability":  "WHICH axes apply to this kind of being. Independent of every score: it "
                      "governs the denominator, not the numerator.",
    "commensuration": "The exchange rate k between axes. Independent: it reweights fixed scores.",
    "comparability":  "WHETHER a scalar exists at all (curl / incomparability). Independent, and "
                      "uniquely a veto: it can deny the output rather than move it.",
    "transgression":  "WHAT the law-breaking costs, in exception bits. Independent of magnitude: "
                      "a small feat can be maximally anomalous.",
    "currency":       "WHETHER the reading is current. Propagation lag; independent of quality, "
                      "since a perfect observation can be centuries stale.",
    "ratification":   "The record's own standing in the Chain. Independent of witness: a sight "
                      "can be unimpeachable and uncountersigned.",
    "scope":          "The aperture the being is judged at, local to omniversal. Independent: it "
                      "changes the comparison class without touching the being.",
}


# ==================================================================================================
# 2. THE CUSTODES
# ==================================================================================================
#
# `tilt`  systematic shift in decimal points this standpoint applies, on its own terms. This is
#         the PRIOR component: it does not shrink with better evidence, because it is not an error.
# `axis_emphasis`  multiplicative reweighting of the axes this Dasein finds disclosive.
# `evidence_sensitivity`  how strongly this Custos's reading responds to attestation quality. High
#         sensitivity means their disagreement IS reducible by fieldwork.
CUSTODES = {
    "Quill": dict(
        dof="attestation", charter="existing Hand",
        dasein="The world shows up as ENCOUNTER. What is real is what was met; she goes there and "
               "bleeds on the page. An account she did not stand inside is a report about the "
               "world, not the world.",
        tilt=+0.06, evidence_sensitivity=0.90,
        axis_emphasis={"ruin": 1.15, "celerity": 1.10, "volition": 1.10},
        refuses="to discount what she saw because a registry has not yet blessed it",
        would_change_her_mind="being present at a contrary event; nothing else",
    ),
    "Moth": dict(
        dof="reduction", charter="existing Hand",
        dasein="The world shows up as RECOMPUTABLE QUANTITY. His test is whether a stranger, given "
               "the citations, can get your number. What cannot be re-derived has not been "
               "measured, however vividly it was seen.",
        tilt=-0.05, evidence_sensitivity=0.35,
        axis_emphasis={"ruin": 1.20, "reach": 1.10, "sustain": 1.05},
        refuses="to enter a figure no one else could reproduce",
        would_change_her_mind="a worksheet that closes; he is moved by arithmetic, not by testimony",
    ),
    "Avar": dict(
        dof="ratification", charter="existing Hand",
        dasein="The world shows up as RECORD. Being is standing in the Chain: an event that has "
               "not ascended has not yet happened omniversally, whoever watched it.",
        tilt=-0.02, evidence_sensitivity=0.55,
        axis_emphasis={"continuity": 1.20, "volition": 1.10},
        refuses="to grant a magnitude on the strength of an uncountersigned sight",
        would_change_her_mind="ratification at a higher rung",
    ),
    # ---- the seven directions nobody was standing in -------------------------------------------
    "Sable": dict(
        dof="nomination", charter="new",
        dasein="The world shows up as EXTENT -- a catalogue always larger than the part surveyed. "
               "She reads every ceiling as a sample maximum and therefore as a floor.",
        tilt=+0.09, evidence_sensitivity=0.75,
        axis_emphasis={"ruin": 1.10, "reach": 1.15},
        refuses="to call the largest thing seen the largest thing there is",
        would_change_her_mind="an exhaustive survey, or a census that closes",
    ),
    "Cassia": dict(
        dof="applicability", charter="new",
        dasein="The world shows up as KINDS. Before any measuring, the question is what sort of "
               "thing this is and which questions it can be asked. A landslide has no Suasion, "
               "and saying so is knowledge, not omission.",
        tilt=-0.01, evidence_sensitivity=0.30,
        axis_emphasis={},
        refuses="category error; she will strike an axis before she will score it badly",
        rules={"endurance_not_volition": (
            "Volition is theta, a position in a contest graph (Part Three), and Ford (1957) makes "
            "it identifiable only on a strongly connected one. An entity whose mode of being is "
            "ENDURANCE rather than victory is therefore a winless node: all in-edges, no out-"
            "edges, theta divergent to minus infinity. Yggdrasil is gnawed by Nidhoggr and "
            "browsed by the four stags and defeats nobody, so the contest model reads a world-"
            "tree as the weakest thing in Norse myth. That is an instrument error, not a finding. "
            "RULE: where an entity's characteristic feat is persistence -- worlds, institutions, "
            "curses, prisons, laws -- Volition is INAPPLICABLE and the feat belongs on Continuity, "
            "which measures exactly what endurance is. Note this is NOT a claim about interiority: "
            "theta needs none. A plague has a theta. The test is whether the thing contests, not "
            "whether it seems to.")},
        would_change_her_mind="a demonstration that the axis applies after all",
    ),
    "Ordo": dict(
        dof="commensuration", charter="new",
        dasein="The world shows up as EXCHANGE. Every quantity is a rate against every other, and "
               "his suspicion is reserved for parity -- the claim that two things trade one for "
               "one is the strongest claim available, not the humblest.",
        tilt=+0.03, evidence_sensitivity=0.25,
        axis_emphasis={"acumen": 1.30, "discernment": 1.30, "suasion": 1.30},
        refuses="a composite whose exchange rates are undeclared",
        would_change_her_mind="an argument fixing k from something other than convenience",
    ),
    "Threnody": dict(
        dof="comparability", charter="new",
        dasein="The world shows up as TENSION HELD -- a chord, not a ladder. Where others see an "
               "unresolved ranking she sees a resolved finding: that no ordering exists. Hers is "
               "the only standpoint that can refuse the output rather than shift it.",
        # HER SENSITIVITY IS 0.0 AND IS NOW WRITTEN AS SUCH (order 39f19f7e646c). It read 0.10,
        # and the evidential term is `tilt * evidence_sensitivity * (1 - q)` -- so with tilt 0.0
        # her response to attestation quality was exactly 0.0 on every reading ever taken. A
        # declared property with no mechanism behind it is the same fault as the dispersive flag
        # filed alongside this order, and the honest resolution is the one the table already
        # implies: her `would_change_her_mind` is "a curl that falls to zero; nothing less", and
        # a curl is not fieldwork. Attestation quality is not her lever, because her instrument
        # is the VETO -- the one standpoint that refuses the output rather than shifting it, and
        # a refusal has no magnitude for evidence to shrink. Zero here is a statement, not a gap.
        # Nothing numeric moves: 0.0 * 0.10 and 0.0 * 0.0 were always the same reading.
        # NOTE the coupling itself survives: any future Custos with tilt 0.0 and a non-zero
        # sensitivity would be inert in the same silent way. Nothing in the tree refuses that
        # pairing; see the order for the check that would.
        tilt=0.0, evidence_sensitivity=0.0,
        axis_emphasis={},
        refuses="to force a scalar through an incomparable pair",
        would_change_her_mind="a curl that falls to zero; nothing less",
        veto=True,
    ),
    "Ferrum": dict(
        dof="transgression", charter="new",
        dasein="The world shows up as LAW AND EXCEPTION. He reads a being by what it costs the "
               "codification to permit -- and a small deed that breaks causality prices higher "
               "than a large one that does not.",
        tilt=+0.04, evidence_sensitivity=0.40,
        axis_emphasis={"transgression": 1.45},
        refuses="to let an anomaly pass at the price of an ordinary feat",
        would_change_her_mind="a shorter codification that covers the same deed",
    ),
    "Lumen": dict(
        dof="currency", charter="new",
        dasein="The world shows up as LIGHTCONE. Every reading is of a past, and distance is age. "
               "What reaches her is never the being but the being as it stood.",
        # ERRATUM: Lumen carried a -0.04 tilt, which asserted that distant beings read WEAKER.
        # Nothing justifies that. Distance does not diminish a being; it diminishes what we know
        # of one. Staleness is IGNORANCE, and ignorance is dispersion, not direction -- so his
        # tilt is zero and his contribution enters the interval instead, derived in convene()
        # from propagation.observed_mark with no constant of its own.
        tilt=0.0, evidence_sensitivity=0.0, dispersive=True,
        axis_emphasis={"celerity": 1.15, "continuity": 1.10},
        refuses="to report a distant magnitude as though it were present tense",
        would_change_her_mind="a nearer vantage, or news that has finished arriving",
    ),
    "Vault": dict(
        dof="scope", charter="new",
        dasein="The world shows up as NESTED SCALES. The same being is a terror in a valley and a "
               "rounding error in a galaxy, and neither reading is the mistaken one; the aperture "
               "must be named before the number means anything.",
        tilt=-0.03, evidence_sensitivity=0.20,
        axis_emphasis={"reach": 1.25, "sustain": 1.10},
        refuses="an unaperture'd magnitude",
        would_change_her_mind="a stated aperture; then she agrees with everyone",
    ),
}

# DERIVED from assay()'s own attestation table rather than restated. A second hand-written table
# of evidence quality would be a duplicate mechanism for a quantity the charter has already fixed
# -- the same error as the withdrawn tempo table (X.10 §4), and it would drift the moment either
# copy was edited. Quality is the complement of the interval that grade already earns:
#
#     quality(g) = 1 - base(g) / max(base)
#
# Monotone by construction, and it moves automatically if the charter revises a grade.
#
# THIS WAS THE FORBIDDEN SECOND COPY UNTIL order 6475cb78e185: the comment above already claimed
# "derived", but the dict here was a hand-typed literal matching `interval_from_hands`'s floor by
# coincidence of two people copying the same number, not by import -- it could not have been
# imported before, because that floor lived only inside the function's body. It is now hoisted to
# `assay.ATTESTATION_FLOOR`, and this reads it rather than restating it.
_ATT_BASE = A.ATTESTATION_FLOOR
_ATT_WORST = max(_ATT_BASE.values())
CURL_VETO_THRESHOLD = 0.10   # = Saaty's CR bar, via Theorem 1

ATTESTATION_QUALITY = {g: round(1.0 - b / _ATT_WORST, 4) for g, b in _ATT_BASE.items()}

# What a grade outside the charter's five reads as. It is a SUBSTITUTION, not a measurement, and
# it used to be an unnamed literal `0.4` inside `_custos_reading` -- so "TOTAL NONSENSE" produced
# a number one hundredth away from "Transcribed" and nothing in the result said the grade had not
# been recognised (order 0aefdac4a26d). A lowercase "witnessed", a grade renamed in the charter
# and a caller's typo all land here. The value is kept where it was rather than retuned: this
# order is about the SILENCE, and moving the number as well would change every published interval
# for a class of input while claiming to be a reporting fix.
ATTESTATION_UNRECOGNISED_QUALITY = 0.4


def _custos_reading(name, anchor, scores, attestation, worksheet):
    """One Custos's reading of the same evidence, through their own emphasis and tilt."""
    c = CUSTODES[name]
    base = A.assay(anchor, scores, attestation=attestation, worksheet=worksheet)
    if base.get("decimal") is None:
        return None

    emph = c.get("axis_emphasis") or {}
    if emph:
        # A PRIVATE weight table, never the shared global: the old mutate-and-restore was
        # correct single-threaded and silently wrong beside any concurrent assay() call.
        w = {k: v * emph.get(k, 1.0) for k, v in A.WEIGHTS.items()}
        tot = sum(w.values())
        w = {k: v / tot for k, v in w.items()}
        base = A.assay(anchor, scores, attestation=attestation, worksheet=worksheet,
                       weights=w)

    q = ATTESTATION_QUALITY.get(attestation, ATTESTATION_UNRECOGNISED_QUALITY)
    # The tilt has two parts, and separating them is the whole point:
    #   PRIOR      the standpoint's own reading, which survives perfect evidence
    #   EVIDENTIAL the part that shrinks as attestation improves
    prior_part = c["tilt"]
    evidential_part = c["tilt"] * c["evidence_sensitivity"] * (1.0 - q)
    # assay() already returns `decimal` as the fractional offset within the band (0.49 means
    # M3.49), so it is added directly. Tilts are quoted in those same hundredths.
    idx = A.LADDER.index(anchor)
    return {
        "custos": name, "dof": c["dof"],
        "reading": round(idx + base["decimal"] + prior_part + evidential_part, 4),
        "reading_at_perfect_evidence": round(idx + base["decimal"] + prior_part, 4),
        "veto": bool(c.get("veto")),
    }


def staleness_widening(distance, years_since):
    """Interval widening owed to a reading being in transit. DERIVED, no constant of its own.

    propagation.observed_mark() already says how much of the Chain of Record can have reached an
    observer at this distance after this long. The unobserved share is exactly what we do not know
    about the being's present state.

    If NOTHING has arrived, the honest statement is that the being's decimal is unknown across its
    whole band -- half-width 0.5, because a band has width 1. That 0.5 is forced by the band's own
    definition and is not a tunable.

    THE None BRANCH IS NOT A MEASUREMENT OF ZERO STALENESS (order 2af7ca515157). "No vantage was
    supplied" and "the news has fully arrived" are different states of the world and must not
    share an answer -- the same distinction `resonance.hodge_decompose` draws between an empty
    edge set and a perfectly consistent ladder. This function has to return a float, so it
    returns 0.0; what it CANNOT do from in here is tell its caller which of the two it meant. So
    the caller is the one that must ask first, and `convene()` now does: it tests the arguments
    itself, records `staleness_measured: False`, and never routes an unsupplied vantage through
    here as though it were a reading. Keeping this branch means a direct caller still gets a
    number rather than a traceback; it is not the place the distinction is made.
    """
    import propagation as P
    if distance is None or years_since is None:
        return 0.0
    mark = P.observed_mark(distance, years_since)
    unobserved = 1.0 - (mark / P.LADDER_HEIGHT)
    return max(0.0, min(1.0, unobserved)) * 0.5


# Set the first time a Custos is convened with nothing to read in her own degree of freedom, and
# never cleared. Same shape as `assay.RHO_FALLBACK_REASON` because it is the same class of event:
# a standpoint that could not stand, in a college whose whole claim is that every direction is
# manned. `dof_coverage()` answers "is there a Custos for this direction"; these answer the
# harder question underneath it -- "did she have anything to look at".
ABSTENTIONS = {}
_ABSTAIN_ANNOUNCED = set()

_ABSTAIN_NOTE = {
    "currency": ("Lumen (dof=currency) ABSTAINED: convene() was called with no `distance` and/or "
                 "no `years_since`, so propagation.observed_mark was never consulted and the "
                 "interval carries NO widening for the reading being in transit. This is not a "
                 "finding that the reading is current -- it is the absence of the measurement "
                 "whose absence Lumen exists to report. Every published interval from such a "
                 "call is narrower than the evidence supports by however stale the reading is."),
    "comparability": ("Threnody (dof=comparability) ABSTAINED: convene() was called with no "
                      "`eta`, so resonance.hodge_decompose was never run and the curl fraction "
                      "of this being's contest structure is UNMEASURED. The veto below cannot "
                      "fire. A scalar is being published without anyone having checked whether a "
                      "scalar is faithful -- which is the one thing this standpoint is for."),
}


def _abstained(dof):
    """Record, once per process per degree of freedom, that a Custos had nothing to read.

    ORDER 2af7ca515157 AND f467f662be4b, AND THEY ARE ONE FAULT SEEN TWICE. Both Custodes were
    given a real mechanism, a real threshold and a real place in `convene()`'s body, and both
    were then wired to a keyword argument that no production caller supplies -- `anchors.py:190`,
    the single real call site, passes neither `eta` nor `distance`/`years_since`. So `half +=
    stale` added exactly 0.0 on every real reading and the curl veto could not fire on any of
    them, and NOTHING SAID SO: the output dict reported `staleness_widening: 0.0`, which reads as
    a measurement that came back zero, and omitted `threnody_veto` entirely, which reads as a
    veto that was considered and declined.
    // The code was never wrong. It was never reached. Those look identical from the output, and
    // that is precisely what this records.

    It does not substitute a value, because there is no honest value to substitute: the vantage
    and the contest graph are inputs, not defaults, and inventing either would be manufacturing
    the measurement rather than reporting its absence. What it does is make the absence
    IMPOSSIBLE TO READ AS A ZERO -- in the returned dict (`*_measured: False` plus a named
    reason), in the health ledger, on stderr, and on `ABSTENTIONS` afterwards.
    """
    ABSTENTIONS[dof] = _ABSTAIN_NOTE[dof]
    if dof not in _ABSTAIN_ANNOUNCED:
        _ABSTAIN_ANNOUNCED.add(dof)
        import silence
        silence.note("custodes.py:abstained-" + dof)
        print("custodes.py: " + _ABSTAIN_NOTE[dof], file=sys.stderr)


def _transit_widening(distance, years_since):
    """The half-width the DISPERSIVE Custodes add, and which of them had no mechanism to add it.

    THE FLAG IS CONSULTED HERE, WHICH IS THE PART IT WAS MISSING (order 90eba4982972). `convene`
    derived the dispersive list from the table, placed it in the output dict, and then widened
    the interval from `staleness_widening(...)` regardless of it -- so a second dispersive Custos
    would have been NAMED in `dispersive_custodes` beside an interval she moved by exactly
    nothing, which is precisely what the comment there claimed could no longer happen. Proved by
    flipping Lumen's flag in memory with identical inputs: the interval was byte-identical and
    only the name list changed.

    The widening is now accumulated PER dispersive Custos, through the mechanism belonging to her
    own degree of freedom. Exactly one dof has such a mechanism -- `currency`, via
    `propagation.observed_mark` -- and a Custos flagged dispersive in any other direction is
    returned in the fourth slot rather than absorbed, because "she declares a dispersion nobody
    can compute" and "she contributes nothing" must not share an answer. Same rule as the
    abstentions one level up: an absent measurement must not be readable as a zero.

    -> (half-width to add, was the currency measurement taken, why, [flagged but unmechanised])
    """
    stale, measured, source, without = 0.0, False, None, []
    for name in sorted(n for n, c in CUSTODES.items() if c.get("dispersive")):
        if CUSTODES[name]["dof"] != "currency":
            without.append(name)
            continue
        if distance is not None and years_since is not None:
            stale += staleness_widening(distance, years_since)
            measured = True
            source = ("measured: propagation.observed_mark(distance=%r, years_since=%r)"
                      % (distance, years_since))
        else:
            source = _ABSTAIN_NOTE["currency"]
            _abstained("currency")
    if source is None:
        # A THIRD STATE, and it gets its own sentence rather than borrowing one of the other
        # two: nobody in the table stands dispersive in `currency`, so no transit widening was
        # derived and none was expected. Unreachable while Lumen carries the flag; it exists so
        # that removing the flag reads as a change in the college rather than as a measurement.
        source = ("no Custos in the table is marked dispersive in dof=currency, so no transit "
                  "widening was derived and none was expected")
    return stale, measured, source, without


def convene(anchor, scores, attestation="Transcribed", worksheet="convened", eta=None,
            distance=None, years_since=None):
    """Convene the full college. The interval is the DISPERSION of their readings.

    Returns the consensus decimal, the ± as measured spread, and -- the part that makes the number
    useful -- the split between what fieldwork could fix and what it could not.

    TWO OF THE TEN CUSTODES CANNOT WORK ON A DEFAULT CALL, AND THAT IS THE STATE OF THE TREE
    TODAY (orders 2af7ca515157, f467f662be4b, both left OPEN for the wiring):

      `eta`, from `resonance.hodge_decompose`, is what lets Threnody exercise her veto: where the
      contest structure is substantially curl, no scalar is faithful and the college should say
      so rather than average harder. NOTHING IN PRODUCTION COMPUTES IT. `resonance.py` has no
      production caller at all, `hodge_decompose` has no caller anywhere, and the only calls that
      pass `eta` are this module's own `main()` demo (a literal 0.70) and `verify_math`. The
      veto's arithmetic is exercised; the veto itself has never fired on a real being.

      `distance`/`years_since` are what Lumen reads, via `propagation.observed_mark`. No caller
      supplies them either, so `staleness_widening` contributes exactly 0.0 to every real
      interval.

    Both are therefore reported as ABSTENTIONS rather than absorbed: `staleness_measured` and
    `comparability_measured` ride on every result, false on a default call, with the reason
    named in `currency_source` / `comparability_source`. A reader of one published +/- can tell
    from the number itself that two of its ten standpoints did not get to speak.

    WIRING THEM IS A CHANGE IN `anchors.py`, NOT HERE, and it is a curatorial one rather than a
    mechanical one: `ANCHORS` carries no vantage for any of its five entries, so somebody has to
    rule what distance and how many years each is being read across, and there is no contest
    graph for the college to decompose. Defaulting either from in here would be inventing the
    measurement, which is the failure this file exists to refuse.
    """
    # THE ATTENDANCE IS A FACT ABOUT THE ARGUMENTS, so it is settled before the readings are
    # counted (order ded8418c75a6). These flags used to be computed halfway down the body, past
    # the `len(readings) < 2` early return, so a band-only result carried {decimal, reason} and
    # nothing else -- silent about which standpoints spoke, which is the exact silence they were
    # added to end, surviving on the one path where the college could not reach a number at all.
    # Whether Lumen and Threnody had anything to read depends on `distance`/`years_since`/`eta`,
    # never on how many readings came back, so both returns can and now do carry it.
    dispersive = sorted(n for n, c in CUSTODES.items() if c.get("dispersive"))
    (stale, stale_measured, currency_source,
     dispersive_unmechanised) = _transit_widening(distance, years_since)
    if eta is None:
        comparability_source = _ABSTAIN_NOTE["comparability"]
        _abstained("comparability")
    else:
        comparability_source = ("measured: eta=%.4f from resonance.hodge_decompose "
                                "(curl fraction %.4f, bar %.2f)"
                                % (eta, 1.0 - eta, CURL_VETO_THRESHOLD))
    # AN UNRECOGNISED GRADE IS NOT A MID-QUALITY GRADE (order 0aefdac4a26d). `_custos_reading`
    # substitutes ATTESTATION_UNRECOGNISED_QUALITY for anything outside the charter's five and a
    # number is published either way; until this flag there was nothing in the result that could
    # tell a reader the grade had never been recognised, so "TOTAL NONSENSE" was indistinguishable
    # from "Transcribed" apart from a hundredth on the decimal. The substituted value rides along
    # exactly the way the abstention reasons do.
    attestation_recognised = attestation in ATTESTATION_QUALITY
    attendance = {
        "staleness_measured": stale_measured,
        "currency_source": currency_source,
        "comparability_measured": eta is not None,
        "comparability_source": comparability_source,
        "attestation_recognised": attestation_recognised,
        "attestation_source": (
            "grade %r is one of the charter's %d" % (attestation, len(ATTESTATION_QUALITY))
            if attestation_recognised else
            "UNRECOGNISED grade %r: not one of %s. Every Custos read it at the substituted "
            "quality %.2f, so any decimal and interval here are a reading of a grade the "
            "charter does not define -- not a measurement of mid-quality evidence."
            % (attestation, sorted(ATTESTATION_QUALITY), ATTESTATION_UNRECOGNISED_QUALITY)),
    }
    if not attestation_recognised:
        attendance["attestation_substituted_quality"] = ATTESTATION_UNRECOGNISED_QUALITY

    readings = [r for r in (_custos_reading(n, anchor, scores, attestation, worksheet)
                            for n in CUSTODES) if r]
    if len(readings) < 2:
        return dict(attendance, decimal=None, reason="insufficient readings; band-only")

    vals = [r["reading"] for r in readings]
    perfect = [r["reading_at_perfect_evidence"] for r in readings]

    consensus = statistics.fmean(vals)
    total_sd = statistics.pstdev(vals)
    prior_sd = statistics.pstdev(perfect)          # survives perfect evidence: irreducible

    total_var = total_sd ** 2
    prior_var = prior_sd ** 2
    prior_share = (prior_var / total_var) if total_var > 0 else 1.0
    prior_share = max(0.0, min(1.0, prior_share))

    # The interval must COVER every signed reading -- a college that publishes a band excluding one
    # of its own members has not measured its disagreement, it has hidden it.
    half = max(1.96 * total_sd, *(abs(v - consensus) for v in vals))
    # Lumen's contribution: dispersive, not directional. `_transit_widening` above derived it
    # from the table's own `dispersive=True`, one flagged Custos at a time -- see its docstring
    # for why a list that only reached the output dict was not the same as a flag being read.
    half += stale

    out = {
        "anchor": anchor,
        "n_custodes": len(readings),
        "consensus": round(consensus, 3),
        "decimal": round(consensus - A.LADDER.index(anchor), 2),
        "interval": round(half, 2),
        "staleness_widening": round(stale, 3),
        # THE FLAG IS THE POINT, not the number beside it. `staleness_widening: 0.0` alone is
        # ambiguous between "the news has fully arrived" and "nobody told us where this being
        # is", and in production it has only ever meant the second. The whole attendance --
        # `staleness_measured`, `currency_source`, `comparability_measured`,
        # `comparability_source`, `attestation_recognised` -- is spread in from the block at the
        # top of this function, so the band-only return above carries exactly the same flags.
        **attendance,
        "dispersive_custodes": dispersive,
        # NAMED AND UNABLE TO ACT is its own state and gets its own key: a Custos the table
        # marks dispersive whose degree of freedom has no derived widening. Empty while Lumen is
        # the only one flagged; it is what stops the next flagged Custos being reported as a
        # contributor to a number she cannot reach.
        "dispersive_without_mechanism": dispersive_unmechanised,
        "prior_divergence_share": round(prior_share, 3),
        "attestation_floor_share": round(1.0 - prior_share, 3),
        "reading_spread": {r["custos"]: round(r["reading"], 3) for r in readings},
        # m30: this is a GUARANTEE being published, not a check being run. `half` is defined
        # above as max(1.96*sd, max|v - consensus|) and only ever widened after, so this is true
        # by construction for every possible input and cannot fail. It is left in place because
        # it states the invariant at the point a reader would look for it -- but it must not be
        # mistaken for verification, and it becomes a live check the moment `half` stops being
        # defined to cover. What it does NOT report, and what would be genuine information, is
        # whether the 1.96*sd band ALONE covered every reading, i.e. whether the widening had to
        # fire. See NEXT_STEPS: that is an addition to the contract, not a repair, so it is
        # raised as a question rather than shipped here.
        "covers_every_reading": all(abs(v - consensus) <= half + 1e-12 for v in vals),
        "interpretation": ("a high prior share means further fieldwork will NOT narrow this; the "
                           "disagreement is between standpoints, not about facts"),
    }
    # Threnody's bar is NOT a new number. Saaty's conventional limit for "these judgments are
    # coherent enough to scalarize" is CR < 0.10; Theorem 1 puts CR and the curl fraction on the
    # same footing, so the analogous bar is curl < 0.10, i.e. eta > 0.90. Taking 0.85 would have
    # been a fresh parameter chosen to feel lenient.
    #
    # AND WHEN `eta` IS None THE VETO IS NOT DECLINED, IT IS UNMEASURED (order f467f662be4b).
    # `threnody_veto` is deliberately NOT set to False on that path: a False would state that the
    # curl was looked at and found small, which nothing in production has ever done. What is
    # published instead is `comparability_measured: False` and the reason, so the absence reads
    # as an absence. Both keys are set in the attendance block at the top of this function now,
    # so the band-only return carries them too (order ded8418c75a6); only the veto itself, which
    # needs the readings, stays down here.
    if eta is not None and (1.0 - eta) >= CURL_VETO_THRESHOLD:
        out["threnody_veto"] = True
        out["decimal"] = None
        out["reason"] = (f"curl fraction {1-eta:.2f}: the contest structure is substantially "
                         f"non-transitive, so no scalar represents it faithfully. Band-only.")
    return out


def dof_coverage():
    """Is every degree of freedom actually manned? A direction with no Custos is unwatched."""
    manned = {c["dof"] for c in CUSTODES.values()}
    missing = sorted(set(DEGREES_OF_FREEDOM) - manned)
    return {"degrees_of_freedom": len(DEGREES_OF_FREEDOM), "custodes": len(CUSTODES),
            "manned": len(manned), "unmanned": missing,
            "one_to_one": len(missing) == 0 and len(CUSTODES) == len(DEGREES_OF_FREEDOM)}


def table_faults():
    """Properties the CUSTODES table ASSERTS that its own arithmetic makes inert. -> [str].

    ZERO TILT WITH A NON-ZERO SENSITIVITY IS THE ONE THIS EXISTS FOR (order d27e95a57233).
    `_custos_reading` computes `evidential_part = tilt * evidence_sensitivity * (1 - q)`, so a
    Custos entered with `tilt=0.0` is frozen against attestation quality no matter what her
    `evidence_sensitivity` declares -- while the column's own header two hundred lines above says
    "High sensitivity means their disagreement IS reducible by fieldwork". Threnody sat exactly
    there: she declared 0.10 and her evidential part was 0.0 on every reading ever taken, found
    by audit rather than by anything in the tree, and closed as an INSTANCE (order 39f19f7e646c).
    Both zero-tilt Custodes declare 0.0 today, so the table is consistent as it stands; what was
    unrefused was the COUPLING, which is why this module keeps producing the same class of
    finding one entry at a time (see also the dispersive flag, 90eba4982972, and the arguments
    no caller passes, 2af7ca515157 / f467f662be4b).

    Returns a list of sentences, empty when the table is clean, in the shape `dof_coverage()`
    above uses: a property of the table, computed rather than asserted, so a caller can print it
    or fail on it. THE BATTERY HOOK IS DELIBERATELY NOT WIRED HERE -- `src/verify_math.py` and
    `src/drill.py` were owned by another agent for the 2026-08-29 shift, which is the same reason
    the order was filed rather than fixed. One line there against this function turns the next
    occurrence into a red battery instead of an audit finding three sweeps later.
    """
    faults = []
    for name, c in sorted(CUSTODES.items()):
        if c.get("tilt") == 0.0 and c.get("evidence_sensitivity"):
            faults.append(
                "%s declares evidence_sensitivity=%s with tilt=0.0, so her evidential part is "
                "0.0 on every reading -- the sensitivity is a property asserted in the table and "
                "enforced nowhere. Either give her a tilt or declare the sensitivity 0.0 with a "
                "written reason, as Threnody's and Lumen's entries do."
                % (name, c.get("evidence_sensitivity")))
    return faults


def main():
    print("=" * 96)
    print("THE COLLEGE OF CUSTODES — one standpoint per degree of freedom")
    print("=" * 96)
    cov = dof_coverage()
    print(f"\ndegrees of freedom in the assay : {cov['degrees_of_freedom']}")
    print(f"Custodes                        : {cov['custodes']}   "
          f"one-to-one: {cov['one_to_one']}")
    print(f"unmanned directions             : {cov['unmanned'] or 'none'}")
    # Printed beside the coverage line because it is the same kind of fact: a property of the
    # table rather than of a reading. Uncapped -- every fault is named, there is never a long
    # list of these, and a table fault is precisely what a person is here to act on.
    _faults = table_faults()
    print(f"table faults                    : {len(_faults) or 'none'}")
    for _f in _faults:
        print(f"   FAULT: {_f}")

    print(f"\n{'Custos':<11}{'degree of freedom':<17}{'origin':<16}refuses")
    print("-" * 96)
    for n, c in CUSTODES.items():
        print(f"{n:<11}{c['dof']:<17}{c['charter']:<16}{c['refuses'][:44]}")

    ks = dict(ruin=0.6, continuity=4.8, celerity=6.5, reach=1.2,
              transgression=8.7, sustain=7.4, vector=0.8, volition=9.6)

    print("\n\nKENSHIRO, post-Raoh — the charter's own worked example, re-convened")
    print("-" * 96)
    r = convene("M3", ks, attestation="Witnessed", worksheet="Charter Part Three")
    for k, v in sorted(r["reading_spread"].items(), key=lambda kv: kv[1]):
        print(f"   {k:<11} {v:.3f}")
    print(f"\n   consensus  A M3.{round(r['decimal'] * 100):02d} ± {r['interval']:.2f}"
          f"   (charter: M3.52 ± 0.12, three Hands)")
    print(f"   prior divergence {r['prior_divergence_share']:.0%} / "
          f"attestation floor {r['attestation_floor_share']:.0%}")
    print(f"   interval covers every signed reading: {r['covers_every_reading']}")
    # THE COLLEGE'S ATTENDANCE, printed where the reading is. `dof_coverage()` says every
    # direction has a Custos assigned to it; this says which of them had anything to read. The
    # charter's worked example is convened with no vantage and no contest graph, so two of the
    # ten abstain — and the demo must not present a ten-standpoint number as though ten
    # standpoints spoke.
    print(f"   staleness measured (Lumen)       : {r['staleness_measured']}")
    print(f"   comparability measured (Threnody): {r['comparability_measured']}")
    for _dof in sorted(ABSTENTIONS):
        print(f"   ABSTAINED [{_dof}] — {ABSTENTIONS[_dof][:76]}...")

    print("\n\nTHE SAME BEING, POORLY ATTESTED — what fieldwork can and cannot fix")
    print("-" * 96)
    for att in ("Instrumented", "Witnessed", "Transcribed", "Reconstructed", "Disputed"):
        rr = convene("M3", ks, attestation=att, worksheet="x")
        print(f"   {att:<14} ± {rr['interval']:.2f}   "
              f"prior {rr['prior_divergence_share']:.0%} / "
              f"attestation {rr['attestation_floor_share']:.0%}")
    print("\n   as attestation improves the interval shrinks toward the prior floor and stops.")
    print("   what remains is the college disagreeing about the world, not about the evidence.")

    print("\n\nTHRENODY'S VETO — where no scalar is faithful")
    print("-" * 96)
    rv = convene("M3", ks, attestation="Witnessed", worksheet="x", eta=0.70)
    print(f"   with curl fraction 0.30: decimal = {rv['decimal']}")
    print(f"   {rv.get('reason','')}")
    print("\n" + "=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
