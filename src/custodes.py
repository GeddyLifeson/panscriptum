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
        tilt=0.0, evidence_sensitivity=0.10,
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

    q = ATTESTATION_QUALITY.get(attestation, 0.4)
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
    """
    import propagation as P
    if distance is None or years_since is None:
        return 0.0
    mark = P.observed_mark(distance, years_since)
    unobserved = 1.0 - (mark / P.LADDER_HEIGHT)
    return max(0.0, min(1.0, unobserved)) * 0.5


def convene(anchor, scores, attestation="Transcribed", worksheet="convened", eta=None,
            distance=None, years_since=None):
    """Convene the full college. The interval is the DISPERSION of their readings.

    Returns the consensus decimal, the ± as measured spread, and -- the part that makes the number
    useful -- the split between what fieldwork could fix and what it could not.

    `eta` (from resonance.hodge_decompose) lets Threnody exercise her veto: where the contest
    structure is substantially curl, no scalar is faithful and the college says so rather than
    averaging harder.
    """
    readings = [r for r in (_custos_reading(n, anchor, scores, attestation, worksheet)
                            for n in CUSTODES) if r]
    if len(readings) < 2:
        return {"decimal": None, "reason": "insufficient readings; band-only"}

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
    half = max(1.96 * total_sd, max(abs(v - consensus) for v in vals))
    # Lumen's contribution: dispersive, not directional.
    stale = staleness_widening(distance, years_since)
    half += stale

    out = {
        "anchor": anchor,
        "n_custodes": len(readings),
        "consensus": round(consensus, 3),
        "decimal": round(consensus - A.LADDER.index(anchor), 2),
        "interval": round(half, 2),
        "staleness_widening": round(stale, 3),
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


def main():
    print("=" * 96)
    print("THE COLLEGE OF CUSTODES — one standpoint per degree of freedom")
    print("=" * 96)
    cov = dof_coverage()
    print(f"\ndegrees of freedom in the assay : {cov['degrees_of_freedom']}")
    print(f"Custodes                        : {cov['custodes']}   "
          f"one-to-one: {cov['one_to_one']}")
    print(f"unmanned directions             : {cov['unmanned'] or 'none'}")

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
    print(f"\n   consensus  A M3.{int(round(r['decimal'] * 100)):02d} ± {r['interval']:.2f}"
          f"   (charter: M3.52 ± 0.12, three Hands)")
    print(f"   prior divergence {r['prior_divergence_share']:.0%} / "
          f"attestation floor {r['attestation_floor_share']:.0%}")
    print(f"   interval covers every signed reading: {r['covers_every_reading']}")

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
