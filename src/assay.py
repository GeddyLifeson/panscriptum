#!/usr/bin/env python3
"""
The Custodial Assay — the calculation engine.

Implements Charter Part Three and Vol. X.2 (*Mensura Fundamenta*) as executable maths, so that
entities from unconnected fictions can be placed on one ruler.

WHY CROSS-FRANCHISE COMPARISON IS POSSIBLE AT ALL
-------------------------------------------------
Luffy and Goku never fight. The Bradley-Terry model of X.2 §5 therefore says nothing about
them: its identifiability proposition holds only *within connected components* of the contest
graph. If contests were the only bridge, they would be incomparable permanently.

They are not the only bridge. X.2 §8 stacks three invariance strategies:

  1. RUNG-RELATIVE UNITS. Band edges are rung-threat scales -- binding energies, characteristic
     lengths, characteristic tempos. Every inhabited system has a binding hierarchy: planets
     cost ~10^32 J to disrupt in One Piece, in Dragon Ball, and in reality, because that is a
     property of planets and not of the fiction. "The Ladder is the shared ruler because it is
     the shared *situation*."
  2. LAW-RELATIVE AXES. Transgression is defined against the LOCAL law by construction, so it
     never needed translating: it measures how many bits the local rulebook must be patched
     by, whatever that rulebook says.
  3. BRIDGE CALIBRATION. Residual scale freedom between systems is fixed empirically by
     crossover contests -- the Chain of Defeats. This REFINES the first two; it does not
     enable them.

So the engine below is dimensional first and social second. Feats convert to SI; SI converts
to band-relative scores; scores compose into an Assay.

WHAT IT REFUSES TO DO
---------------------
Per the honesty theorems of X.2 §9 and Hard Rule 3: no worksheet, no number. Every quantity
must trace to a cited feat. An entity with no quantified feats gets a band window, never a
decimal. Theorem 1 also guarantees no scalar represents the capability preorder losslessly --
the Assay is explicitly a projection, and Theorem 2 bounds its error below by the curl fraction
of the contest flow. This module reports that loss rather than hiding it.
"""
import math
import os

# A regex escape arriving as a literal control character matches nothing and fails SILENTLY.
# A word-boundary escape written through a shell heredoc has arrived here as a 0x08 backspace
# five separate times in this project. Each time it read as a tuning problem -- a gate that
# passed nothing, a parser that found zero rows -- rather than as corruption, which is what
# makes it expensive. The check is built from chr() codes because the first version was
# written with escapes and they were eaten too, so it flagged its own source and refused.
_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding='utf-8').read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ': a regex escape was eaten in transit - a literal control '
                     'character is present in the source. Repair before running.')


# ---------------------------------------------------------------- the ladder's reference edges
#
# Band floors for each axis quantity, per X.2 §4. These are PHYSICAL, drawn from the binding
# hierarchy every inhabited universe shares -- which is precisely what makes them portable
# across fictions with different magic.
#
# Energy figures are real: TNT ~4.2e9 J/kt; Hiroshima ~6.3e13 J; Earth's gravitational binding
# energy 2.24e32 J; the Sun's 6.9e41 J; a Type II supernova ~1e44 J; the Milky Way's binding
# energy ~1e59 J. Values above M7 are extrapolations of the same ladder and are flagged as
# such, because "universal" has no agreed binding energy.
# CORRECTED 2026-08-20 against X.2 §4. An earlier version of this table was invented and sat
# TWO BANDS LOW: it placed M3's Ruin floor at 1e15 J, when X.2 §4 states plainly that "the M3
# band spans crust-disruption to planetary gravitational binding, ~10^24-10^32 J". Every score
# it produced was wrong. The charter's published edges govern; where the charter is silent
# (M6+, and the non-Ruin axes) the values below extend the same rung-threat logic and are
# flagged as the conventions they are (Axiom M3: chosen, published, frozen -- "promises, not
# truths", X.6 §4).
BAND_EDGES = {
    #        Ruin (J)    Reach (m)   Celerity      Sustain    Continuity
    #                                (actions/s)   (s)        (J*removals)
    "M0":  dict(ruin=1e2,   reach=1e0,   celerity=1e0,   sustain=1e0,   continuity=1e2),
    "M1":  dict(ruin=1e7,   reach=1e2,   celerity=5e0,   sustain=1e1,   continuity=1e7),
    "M2":  dict(ruin=1e12,  reach=1e3,   celerity=2e1,   sustain=1e2,   continuity=1e12),
    # M3 floor = crust disruption; M3 ceiling (= M4 floor) = Earth's gravitational binding
    # energy, 2.24e32 J. Both figures are the charter's own.
    "M3":  dict(ruin=1e24,  reach=1e5,   celerity=1e2,   sustain=1e3,   continuity=1e24),
    "M4":  dict(ruin=2.24e32, reach=6e6, celerity=1e3,   sustain=1e4,   continuity=2.24e32),
    "M5":  dict(ruin=6.9e41, reach=1e9,  celerity=1e5,   sustain=1e5,   continuity=6.9e41),
    "M6":  dict(ruin=1e51,  reach=1e17,  celerity=1e7,   sustain=1e7,   continuity=1e51),
    "M7":  dict(ruin=1e59,  reach=1e21,  celerity=1e9,   sustain=1e9,   continuity=1e59),
    "M8":  dict(ruin=1e70,  reach=1e27,  celerity=1e12,  sustain=1e11,  continuity=1e70),
    "M9":  dict(ruin=1e85,  reach=1e30,  celerity=1e15,  sustain=1e13,  continuity=1e85),
    "M10": dict(ruin=1e99,  reach=1e33,  celerity=1e18,  sustain=1e15,  continuity=1e99),
}

# X.6 §6 Definition 3 -- the Instrument's per-band windows, a declared Custodial convention.
INSTRUMENT_WINDOWS = {
    "M0": (1, 18), "M1": (8, 22), "M2": (12, 26), "M3": (16, 28), "M4": (18, 30),
    "M5": (30, 30), "M6": (30, 30), "M7": (30, 30), "M8": (30, 30), "M9": (30, 30),
    "M10": (30, 30),
}

# X.6 §6 Definition 2 -- which band-relative axis score each faculty reads.
FACULTY_READS = {
    "Strength": "ruin",          # at somatic delivery; armaments excluded by convention
    "Dexterity": "celerity",     # contest tempo, not travel speed
    "Constitution": None,        # mean(continuity, sustain) -- handled in code
    "Intelligence": "acumen",    # NOT volition; Prop. 1 demotes θ to supporting evidence
    "Wisdom": "discernment",     # includes resistance to compulsion
    "Charisma": "suasion",       # force-credibility and compulsion both excluded
}
LADDER = ["M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10"]

# X.2 §4 weights (the combat battery), extended by X.6's three faculty axes. Weights are
# meant to be FITTED from contest data, not decreed -- these are the charter's published
# starting values and should be refit once the Chain of Defeats has enough edges.
# Charter Part Three's declared relative weighting of the eight PHYSICAL Measures. Owner-written,
# published, and used in the charter's own worked example -- not ours to move, and not moved.
CHARTER_PHYSICAL_WEIGHTS = {
    "ruin": 0.20, "continuity": 0.15, "celerity": 0.12, "reach": 0.10,
    "transgression": 0.18, "sustain": 0.08, "vector": 0.07, "volition": 0.10,
}
FACULTY_AXES = ("acumen", "discernment", "suasion")

# ERRATUM (X.11): the faculties were weighted ZERO, and worse -- FACULTY_WEIGHTS was defined and
# never read by anything, while assay() filtered on `k in WEIGHTS`, which excluded them outright.
# The Assay therefore presented itself as a general measure of a being while being a Str/Dex/Con
# scale carrying Int/Wis/Cha as an appendix.
#
# That is not a weighting preference. X.6 §3 measures Acumen in BITS, X.2 §4 measures Transgression
# in BITS, and X.10 §6's L_r converts a band's joules into BITS -- so the faculties and the physical
# Measures were always in one unit. Given a shared unit, an exchange rate of zero is the single
# value the unit forbids: it asserts that no quantity of foresight, insight or influence can ever
# register on a being's standing.
#
# The rate adopted is parity, k = 1, because any k != 1 is a free parameter and parity is the
# unique choice introducing none (X.9 §4's own accounting). Each faculty therefore takes 1/11.
#
# The eight physical weights keep their charter-declared PROPORTIONS exactly and collectively hold
# 8/11 -- which is the same share they would hold under full uniformity, so block-level parity is
# exact while the owner's internal structure is untouched. Because the composite renormalises over
# scored axes, this leaves every existing physical-only decimal bit-for-bit unchanged. It is the
# smallest change that is still correct.
_N_ALL = len(CHARTER_PHYSICAL_WEIGHTS) + len(FACULTY_AXES)          # 11
_FACULTY_W = 1.0 / _N_ALL                                            # 1/11, the parity rate
_PHYS_SCALE = (len(CHARTER_PHYSICAL_WEIGHTS) / _N_ALL) / sum(CHARTER_PHYSICAL_WEIGHTS.values())

WEIGHTS = {k: v * _PHYS_SCALE for k, v in CHARTER_PHYSICAL_WEIGHTS.items()}
WEIGHTS.update({k: _FACULTY_W for k in FACULTY_AXES})
FACULTY_WEIGHTS = {k: _FACULTY_W for k in FACULTY_AXES}

# A score may be marked INAPPLICABLE rather than left unscored, and the difference is the
# difference between ignorance and knowledge. A landslide has no Suasion -- that is a finding, and
# it must not widen the interval. A person's unmeasured Acumen is ignorance, and it must.
# Marking an axis inapplicable is therefore a CLAIM, and one that has to be defensible: it says the
# axis does not apply to this kind of thing, not that nobody got round to scoring it.
INAPPLICABLE = "n/a"

# FOUR STATUSES, because an axis can fail to carry a number for four different reasons and the
# charter's epistemics treat them differently. Collapsing any two loses a real distinction.
#
#   a number    MEASURED. And 0.0 is a CLAMPED value, not a point: axis_score() floors at zero, so
#               0.0 reads "at or below the band floor" and covers everything from a firecracker to
#               crust disruption. It is a BOUND.
#
#   NONE        NIL, as a POINT finding: the axis applies, evidence was considered, and the
#               quantity is genuinely absent.
#
#               Its composite contribution is identical to a clamped 0.0, and that is correct
#               rather than a defect -- both floor the axis, and no arithmetic below the floor
#               exists. (An earlier comment here claimed they were "twenty-four orders of
#               magnitude apart", which was wrong: it forgot the clamp.) The distinction NONE
#               carries is INFORMATIONAL, and it is exactly the information the clamp destroys:
#               0.0 leaves open how far below the floor a being sits, and NONE closes it.
#
#               That is why the status has to exist. The scoring rule structurally cannot record
#               "this cannot harm anyone at all", and downstream reasoning needs it -- a weapon
#               with NONE Ruin is inert, while one with 0.0 Ruin might merely be unmeasured at
#               this band. It earns full coverage credit, because it IS knowledge.
#
#   UNESTIMABLE APPLIES BUT UNEXPRESSED. The being is the right kind of thing to have this, but
#               has never been observed exercising it, so there is no evidence either way. This is
#               IGNORANCE and widens the interval. Available on EVERY axis, not just the social
#               ones: a scholar who has never fought has an unestimable Ruin, and calling it nil
#               would be a claim nobody has earned.
#
#   INAPPLICABLE CATEGORY ERROR. The axis does not apply to this kind of being, so the question is
#               malformed rather than open. Struck from the denominator entirely.
#
# The conflations to avoid:
#   NONE vs INAPPLICABLE  -- "it has none" asserts a fact about the being; "inapplicable" denies
#                            the question was well posed about its kind.
#   NONE vs UNESTIMABLE   -- "it has none" is a finding; "unexpressed" is an open question.
#   NONE vs 0.0           -- a point versus a clamped bound. Same composite, different knowledge.
NONE = "none"
UNESTIMABLE = "unestimable"

# Reference energies, for converting described feats into joules. Every one is a real physical
# quantity, which is the entire point: they mean the same thing in every fiction.
REFERENCE_JOULES = {
    "punch_human": 1.4e2,
    "rifle_round": 3.0e3,
    "car_crash": 5.0e5,
    "building_demolition": 1.0e10,
    "kiloton_tnt": 4.184e12,
    "hiroshima": 6.3e13,
    "megaton_tnt": 4.184e15,
    "tsar_bomba": 2.1e17,
    "richter_9_quake": 2.0e18,
    "continent_shatter": 1.0e26,
    "earth_binding": 2.24e32,      # gravitational binding energy of Earth
    "sun_binding": 6.9e41,
    "supernova": 1.0e44,
    "galaxy_binding": 1.0e59,
}


def axis_score(x, band, axis):
    """X.2 §4 scoring rule: s(x) = 10 * clamp((ln x - ln x_r) / (ln x_{r+1} - ln x_r)).

    Log-scaled because power quantities span dozens of orders of magnitude; clamped because a
    value below the band floor scores ~0 even for a legitimately anchored agent (the clamp that
    forced Erratum 1, where Kenshiro's attested output sat below the M3 floor and a hand-scored
    Ruin of 2.1 could not be sustained).
    """
    if x is None or x <= 0 or band not in BAND_EDGES:
        return None
    i = LADDER.index(band)
    if i + 1 >= len(LADDER):
        return 9.9
    lo = BAND_EDGES[band].get(axis)
    hi = BAND_EDGES[LADDER[i + 1]].get(axis)
    if not lo or not hi or hi <= lo:
        return None
    frac = (math.log(x) - math.log(lo)) / (math.log(hi) - math.log(lo))
    return round(10.0 * max(0.0, min(1.0, frac)), 2)


def band_for_quantity(x, axis="ruin"):
    """Which rung's floor does this quantity clear? A helper for sanity checks, NOT the Anchor.

    The Anchor is a scale of PRESENCE -- how much of reality a thing occupies, pervades, or
    registers within -- and deliberately not an energy threshold. Kenshiro anchors at M3
    without cracking continents, and Yggdrasil anchors high while menacing nobody at all.
    Presence is absolute rather than relative to an opponent: Goku is no threat to Brahman and
    still arrives at a universe's worth of it. Use this only to ask "what does this feat's
    energy correspond to on the ladder", never to assign a band.
    """
    if x is None or x <= 0:
        return None
    out = "M0"
    for b in LADDER:
        if x >= BAND_EDGES[b].get(axis, math.inf):
            out = b
    return out



# --------------------------------------------------------------------- the interval, derived
#
# The interval used to be `base + 0.5 * (1 - coverage)`, and that 0.5 was a decree. It made the
# published error bar a house convention rather than a measurement, which is the one thing Part
# Three's own preface refuses: "a number, a method that produced the number, and an honest
# statement of how wrong the number might be."
#
# The composite is a weighted sum, so its uncertainty follows from standard propagation:
#
#     Var(C) = SUM over axes of  w_i^2 * sigma_i^2        (weights normalised over applicable)
#
# Two kinds of term go in. A SCORED axis carries the dispersion its attestation grade implies --
# a witnessed reading is tighter than a reconstructed one, which is what the grades were always
# meant to express. An axis with NO score contributes the dispersion of not knowing: if it could
# lie anywhere in 0-9.9 with no reason to prefer any part of that range, its standard deviation
# is the uniform one, (b-a)/sqrt(12).
#
# Two things fall out that the old formula could not express. Missing a HEAVY axis now costs more
# than missing a light one -- an unknown Ruin (w=0.145) widens the bar further than an unknown
# Vector (w=0.051), which is obviously right and was previously invisible. And an assay with
# every axis scored under Witnessed attestation narrows below anything the old floor allowed,
# because there is genuinely less to be wrong about.
# CALIBRATED AGAINST THE CHARTER'S OWN PUBLISHED BARS, not chosen.
#
# Kenshiro is printed at M3.52 +/- 0.12, Witnessed, with the eight physical Measures scored and
# the three faculties absent. Solving the propagation above for the sigma that reproduces 0.12
# gives 4.08 -- on an axis scale running 0.0 to 9.9.
#
# That number is worth reading twice. The charter's own error bar says a Measure is known to
# about +/-4 of its ten-point range: the Assay's second decimal is far finer than the evidence
# under it. Nothing here is wrong -- the interval was always the place that admitted this, and
# printing 3.52 +/- 0.12 says exactly that the 5 is firm and the 2 is not. Deriving the bar
# rather than decreeing it simply makes the admission legible.
# THE CEILING ON IGNORANCE, WHICH IS ALSO THE CEILING ON ERROR.
#
# An axis nobody could estimate is a value known only to lie somewhere in 0.0-9.9. Under a
# uniform prior that is a standard deviation of range/sqrt(12) = 2.86 -- the MAXIMUM-ENTROPY
# dispersion for this scale, and therefore the most uncertain any single axis can honestly be.
#
# This is a hard bound and it was being violated. The attestation sigmas were fitted to reproduce
# the charter's published intervals back when `_interval` had ONE component, so they quietly
# absorbed the between-hand disagreement that now has a term of its own. Witnessed came out at
# 4.08 -- larger than knowing nothing at all -- and the consequence was visible in the arithmetic:
#
#     ruin = 0.0           coverage 0.73   interval 0.12
#     ruin = UNESTIMABLE   coverage 0.58   interval 0.11   <-- LESS knowledge, NARROWER bar
#
# An assay that publishes more confidence for an axis it could not read is not conservative, it
# is wrong in the direction this library least wants to be wrong. `verify_math` asserted the
# opposite for months and could not say so, because `verify_math` itself would not import.
SIGMA_MAX = 9.9 / (12 ** 0.5)

# Attestation grades, rescaled so the worst of them just reaches the ceiling and the ORDER the
# charter gives is preserved exactly. The between-hand term now carries what the old inflation
# was standing in for, which is where that variance always belonged: two custodians disagreeing
# is not one custodian being imprecise.
_RAW_SIGMA = {
    "Instrumented": 2.70,       # an instrument reading beats a witness
    "Witnessed": 4.08,          # the charter's calibration point
    "Transcribed": 5.30,        # told rather than seen
    "Reconstructed": 7.00,      # inferred
    "Disputed": 8.50,           # the widest grade the charter names
}
_SCALE = SIGMA_MAX / max(_RAW_SIGMA.values())
SIGMA_BY_ATTESTATION = {k: round(v * _SCALE, 4) for k, v in _RAW_SIGMA.items()}

# Ignorance sits AT the ceiling, so it is by construction at least as wide as any measurement.
SIGMA_UNKNOWN = SIGMA_MAX
# NONE is a finding, not a gap, so it is nearly certain -- but "absent" is still asserted from
# evidence and inherits a little of the reading's own dispersion.
SIGMA_NIL_FACTOR = 0.5


def _interval(scores, used, nil, applicable, attestation, denom, hand_readings=None,
              weights=None):
    """Half-width of the honest error bar, in BAND units, by variance propagation.

    TWO components, because one cannot reproduce the charter's own numbers. Goku is published at
    +/- 0.41 under the SAME Witnessed grade that gives Kenshiro +/- 0.12, and no per-axis sigma
    explains that -- it would have to exceed the 9.9 range itself. The charter names the reason
    in Goku's own citation: "readings divergent, both filed." Avar and Quill disagree, and that
    disagreement is a second source of variance entirely.

        Var(total) = Var(measurement)  +  Var(between hands)

    which is the standard variance-components decomposition. A single-hand assay carries only
    the first term; a contested one carries both, and the interval widens because the library
    genuinely does not know which reading is right rather than because any hand was sloppy.
    """
    # min() rather than a bare lookup: an unknown attestation grade must not be able to claim
    # more certainty than the ceiling, and a future edit to the table must not either.
    sigma = min(SIGMA_MAX, SIGMA_BY_ATTESTATION.get(attestation, SIGMA_MAX))
    # THE SAME WEIGHT TABLE THE COMPOSITE WAS BUILT FROM. `assay()` takes a `weights=` override
    # and deliberately keeps it local (`W`) so a per-call reweighting stays invisible to every
    # other caller -- but this function read the module-global WEIGHTS while being handed the
    # OVERRIDE's `denom`, so a custom-weighted assay got its composite from one table and its
    # error bar from another, normalised against a denominator belonging to neither. custodes.py
    # builds exactly such a table per Custos (`axis_emphasis`); it happens to read only
    # `decimal` today, which is why nothing had caught this. Found 2026-08-24.
    W = weights if weights is not None else WEIGHTS
    var = 0.0
    parts = {}
    for k in applicable:
        w = W[k] / denom                  # normalised so the weights sum to 1 over applicable
        if k in used:
            s_i = sigma
        elif k in nil:
            s_i = sigma * SIGMA_NIL_FACTOR
        else:
            s_i = SIGMA_UNKNOWN           # unscored or unestimable: the dispersion of ignorance
        term = (w * s_i) ** 2
        var += term
        parts[k] = round(term, 6)
    # Between-hand dispersion, when more than one reading is on file. Sample sd of the filed
    # decimals, already in band units, so it is added in quadrature without rescaling.
    hand_var = 0.0
    if hand_readings and len(hand_readings) > 1:
        m = sum(hand_readings) / len(hand_readings)
        hand_var = sum((x - m) ** 2 for x in hand_readings) / (len(hand_readings) - 1)
        parts["_between_hands"] = round(hand_var, 6)
    # Axis scores run 0-9.9 and the decimal runs 0-1, so the measurement sd divides by ten.
    total = (var ** 0.5 / 10.0) ** 2 + hand_var
    return round(total ** 0.5, 2), parts


def assay(anchor, scores, attestation="Transcribed", epoch=None, worksheet=None,
          hand_readings=None, weights=None):
    """Compute a Moth Number: 𝔄 = M_a + (sum w_i * s_i) / 10   (Charter Part Three, step 3).

    Returns a dict, never a bare float -- a value without its interval, epoch and worksheet
    pointer is formally a rumour (Absolute 1 of the Five Absolutes), so the number is not
    handed out unaccompanied.
    """
    if anchor not in LADDER:
        raise ValueError(f"anchor must be one of {LADDER}")
    if not worksheet:
        # H5 of X.6: no worksheet, no number. Thin attestation yields a band window.
        return {"magnitude": anchor, "decimal": None, "interval": None,
                "reason": "no worksheet supplied; band-only per honesty theorem H5"}

    # An optional per-call weight table. custodes' axis-emphasis readings used to mutate
    # the module-global WEIGHTS under a try/finally -- correct alone, silently wrong the
    # moment any other thread called assay() mid-window (round-2 audit, finding 1). A local
    # view makes the reweighting invisible to everyone else by construction.
    W = weights if weights is not None else WEIGHTS
    used = {k: v for k, v in scores.items()
            if k in W and isinstance(v, (int, float))}
    if not used:
        return {"magnitude": anchor, "decimal": None, "interval": None,
                "reason": "no axis scored from cited feats; band-only"}

    # Renormalise over scored axes only, so an unscored axis widens the interval rather than
    # silently dragging the composite toward zero. Note this ratio is invariant to any common
    # rescaling of the weights, which is why bringing the faculties in at parity left every
    # existing physical-only decimal untouched.
    # NONE joins the numerator at nil and the denominator at full weight: knowing an axis is
    # absent is knowing something, and it must pull the composite down rather than be ignored.
    nil = [k for k in W if scores.get(k) == NONE]
    wsum = sum(W[k] for k in used) + sum(W[k] for k in nil)
    composite = sum(W[k] * used[k] for k in used) / wsum
    value = LADDER.index(anchor) + composite / 10.0

    # Interval per step 4: attestation grade sets confidence, and unscored axes add ignorance.
    #
    # The denominator counts only APPLICABLE axes. An axis explicitly marked inapplicable is not
    # missing information -- it is information, and charging ignorance for it would punish an
    # assessor for knowing that a landslide has no Suasion.
    # UNESTIMABLE stays in the denominator: it IS ignorance, unlike INAPPLICABLE.
    applicable = [k for k in W if scores.get(k) != INAPPLICABLE]
    unestimable = sorted(k for k in W if scores.get(k) == UNESTIMABLE)
    unscored = sorted(k for k in W if k not in used and k not in nil
                      and scores.get(k) not in (INAPPLICABLE, UNESTIMABLE))
    denom = sum(W[k] for k in applicable) or 1.0
    coverage = wsum / denom
    interval, var_parts = _interval(scores, used, nil, applicable, attestation, denom,
                                    hand_readings=hand_readings, weights=W)

    # CEILING BEHAVIOUR. composite is in [0,10], so decimal reaches 1.00 when every scored axis
    # maxes -- and 1.00 is not a decimal within the band, it is the FLOOR OF THE NEXT ONE. Left
    # alone this printed "M10.100", which is a broken ruler: an instrument whose top reading
    # overflows its own notation.
    #
    # Promotion is a curatorial act, not an arithmetic one (Part Three flags it via
    # promotion_watch), so this does NOT auto-promote. It clamps the printed decimal and says
    # which case it is.
    _dec = value - LADDER.index(anchor)
    _ceiling = _promote = False
    if _dec >= 1.0:
        if anchor == LADDER[-1]:
            _ceiling = True          # the Ladder has no rung above this; saturation is the answer
        else:
            _promote = True          # every axis maxed: this belongs in the band above, on review
        _dec = 0.99
    return {
        "magnitude": anchor,
        "decimal": round(_dec, 2),
        "at_ladder_ceiling": _ceiling,
        "promotion_due": _promote,
        "moth_number": f"𝔄 {anchor}.{int(round(_dec * 100)):02d} ± {interval:.2f}"
                       + (" [ceiling]" if _ceiling else "")
                       + (" [promotion due]" if _promote else ""),
        "interval": interval,
        "axes_scored": sorted(used),
        "axes_nil": sorted(nil),
        # NONE licenses a claim a clamped 0.0 cannot: that the axis is absent, not merely
        # unresolved below the floor.
        "nil_is_definite": bool(nil),
        "axes_unestimable": unestimable,
        "axes_unscored": unscored,
        "unestimable_note": ("applies to this kind of being but has never been observed being "
                             "exercised; open, not absent" if unestimable else ""),
        "axis_coverage": round(coverage, 2),
        "interval_method": "variance propagation over weighted axes; "
                           "unscored axes carry the uniform dispersion of ignorance",
        "variance_by_axis": var_parts,
        "attestation": attestation,
        "epoch": epoch or "unstamped",
        "worksheet": worksheet,
        "promotion_watch": (value - LADDER.index(anchor)) >= 0.90,
    }


# ------------------------------------------------------------------- the Instrument (X.6 §6)

def instrument(anchor, axis_scores, worksheet=None):
    """Deterministic conversion to the six faculties, 1-30, plus Transcendence Grade.

    X.6 §6 Definition 4:  value = round( c_M + (s/10) * (C_M - c_M) ),  hard cap 30.
    X.6 §6 Definition 5:  for M >= 6, Grade G = M - 5, printed I..V, DERIVED only.

    Two refusals are built in, and both are theorems rather than house style:

    * H5, the thin-data ban. Without a worksheet the subject carries a WINDOW, not a value:
      "a point value printed from a band prior is not a wide measurement but a *fabricated*
      one -- it asserts evidence that does not exist." This is why the bulk catalogue prints
      "uninstrumented" and why building this function creates no licence to run it.
    * Theorem 3(ii), honest nulls. An agent whose strategy set is a singleton (a relic; the
      Sphere of Annihilation is the charter's worked case) returns null on every choice-based
      quantity because the supremum is empty. "Not applicable" is a computed result.
    """
    if anchor not in INSTRUMENT_WINDOWS:
        raise ValueError(f"anchor must be one of {LADDER}")
    if not worksheet:
        lo, hi = INSTRUMENT_WINDOWS[anchor]
        return {"printout": "uninstrumented — no faculties on file",
                "window": [lo, hi],
                "reason": "H5 thin-data ban: band membership alone yields a window, not values"}

    lo, hi = INSTRUMENT_WINDOWS[anchor]
    span = hi - lo
    grade_n = max(0, LADDER.index(anchor) - 5)
    grade = ["", "I", "II", "III", "IV", "V"][grade_n] if grade_n <= 5 else "V"

    out = {}
    for faculty, axis in FACULTY_READS.items():
        if faculty == "Constitution":
            a, b = axis_scores.get("continuity"), axis_scores.get("sustain")
            s = None if a is None or b is None else 0.5 * (a + b)
        else:
            s = axis_scores.get(axis)
        if s is None:
            # An axis unattested at M6+ prints no value AND no Grade: "transcendence is not
            # evidence" (Definition 5).
            out[faculty] = None
            continue
        value = min(30, round(lo + (s / 10.0) * span))
        out[faculty] = f"{value} (Grade {grade})" if grade else value

    return {"faculties": out, "window": [lo, hi],
            "transcendence_grade": grade or None,
            "worksheet": worksheet}


def null_instrument(reason="strategy set is a singleton"):
    """Theorem 3(ii): the computed null for a degenerate agent (a relic, not a being)."""
    return {"printout": "Not applicable — the Instrument measures beings, and this Record's "
                        "mathematics returns the null it promises: no faculties exist to score.",
            "reason": reason, "computed": True}


# ============================================= THE REGRESS TEST (Charter Part Three, Omega Band)

def regress_test(name, has_a_before=None, has_a_stage=None, embedded_in_a_state_space=None,
                 claims_to_be_the_ground=False, notes=""):
    """Is this a ground-of-being claimant, or a demiurge wearing the costume?

    The charter's own instrument: "run the contingency argument against a claimant's own creation
    account. Any claimant whose scripture grants them a stage, substrate, or *before* (an egg, a
    primordial sea, a chaos to shape) is thereby classified a demiurge -- real, mighty, a First
    Office seatholder for their address, but not the ground, because the regress passes through
    them."

    This is NOT a power ranking and must never be used as one. Per H4 the wall between M10 and
    MOmega is type-theoretic: 𝔄 is a functional on agents embedded in a state space, and a
    ground-of-being claimant is by its own claim not such an element. DECLINED is a domain error,
    not a big number. A demiurge that fails this test is not thereby weak -- Galactus fails it and
    shelves at M6-M7 -- it is merely IN the domain, and therefore assayable at all.
    """
    demiurge_markers = []
    if has_a_before:
        demiurge_markers.append(f"has a before ({has_a_before})")
    if has_a_stage:
        demiurge_markers.append(f"was given a stage ({has_a_stage})")
    if embedded_in_a_state_space:
        demiurge_markers.append(f"embedded in a state space ({embedded_in_a_state_space})")

    if demiurge_markers:
        return {
            "name": name,
            "verdict": "DEMIURGE",
            "assayable": True,
            "band_notation": "ordinary M-band; assay normally",
            "reasoning": "the regress passes through this claimant: " + "; ".join(demiurge_markers),
            "omega_eligible": False,
            "notes": notes,
        }
    if claims_to_be_the_ground:
        return {
            "name": name,
            "verdict": "ONTOLOGICAL CLAIMANT",
            "assayable": False,
            "band_notation": "𝔄: DECLINED",
            "reasoning": "halts the regress on its own terms; not an element of any state space, "
                         "so the Assay's domain does not contain it (H4)",
            "omega_eligible": True,
            "omega_note": "the ARGUMENT for this claimant may be scored 𝔄 MΩ.x on the Seven "
                          "Groundings. The claimant itself is never scored. Seat, never Name.",
            "notes": notes,
        }
    return {"name": name, "verdict": "ORDINARY AGENT", "assayable": True,
            "band_notation": "ordinary M-band", "omega_eligible": False, "notes": notes}


# ================================================ THE HANDS AS PRIORS (Vol. 0.5 §2, Theorem 4)
#
# The four recurring marginalia Hands are not flavour. They are the Order's canonical PRIORS --
# the standing set of granularities from which the same evidence is read. Their disagreement is
# not noise around a true value; per Vol. 0.5 it is structural, permanent where their priors are
# not mutually absolutely continuous, and it is WHAT THE PUBLISHED INTERVAL MEASURES.
#
# This is why X.2 §7 sources the interval from "attestation grade AND SOURCE DISAGREEMENT", why
# the charter files Avar's and Quill's competing Goku readings "both signed", why the Five
# Absolutes forbid silent averaging, and why the Emperor -- read across a sparse graph where the
# Hands' priors barely overlap -- is "the most argued name in the Registry" at +/- 0.85.
HANDS = {
    "AVAR": "institutional prior: the Order's accumulated base rates; conservative, "
            "corrective, weights the ratified record heavily",
    "QUILL": "experiential prior: went there, saw it, bled on the page; weights witnessed "
             "testimony heavily and distrusts the ledger's smoothing",
    "MOTH": "formal prior: the worksheet, the fitted weights, the operational scoring rule; "
            "distrusts anything not recomputable",
    "UNNAMED": "the warning prior: weights tail risk far above the others, and speaks only "
               "where the tail is what matters",
}


def interval_from_hands(readings, attestation="Transcribed"):
    """Derive the published +/- from the Hands' divergence. Vol. 0.5 §2, Theorem 4.

    `readings` maps Hand name -> that Hand's assayed value (e.g. {"AVAR": 7.41, "QUILL": 7.90}).

    Two hard constraints, both from the charter rather than from taste:

      1. THE INTERVAL MUST COVER EVERY SIGNED READING. This is the Vade Mecum's own countersign
         check -- "that the interval covers both signed readings" (III.4). An interval that
         excludes a signatory's value is not a measurement, it is a suppression.
      2. NEVER SILENTLY AVERAGE (Absolute 3). The centre is published WITH the full spread and
         every signature attached; the mean is a convenience for sorting, never the finding.

    The attestation floor is added in quadrature because evidence-quality noise and prior
    divergence are independent sources of variance (X.2 §7 separates them explicitly).
    """
    vals = [v for v in readings.values() if v is not None]
    if not vals:
        return None
    centre = sum(vals) / len(vals)
    half_spread = (max(vals) - min(vals)) / 2.0

    floor = {"Witnessed": 0.10, "Instrumented": 0.08, "Transcribed": 0.20,
             "Reconstructed": 0.40, "Disputed": 0.55}.get(attestation, 0.30)

    interval = round(math.sqrt(half_spread ** 2 + floor ** 2), 2)

    # Constraint 1, enforced rather than hoped for.
    while any(abs(v - centre) > interval for v in vals):
        interval = round(interval + 0.01, 2)

    return {
        "centre": round(centre, 2),
        "interval": interval,
        "signatures": {h: round(v, 2) for h, v in readings.items() if v is not None},
        "spread": round(max(vals) - min(vals), 2),
        "prior_divergence_share": round((half_spread ** 2) / (half_spread ** 2 + floor ** 2), 2),
        "covers_all_signatures": all(abs(v - centre) <= interval for v in vals),
        "note": ("the interval is prior divergence, not ignorance: commissioning more feats "
                 "will NOT narrow the share attributable to the Hands' differing priors "
                 "(Vol. 0.5, Erratum 10)"),
    }
