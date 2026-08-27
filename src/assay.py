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
import difflib
import math
import os
import sys

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
# The dispersion of a uniform prior over the band. KEPT AND NAMED, because it is a real and
# useful quantity -- it is the scatter of a single unknown READING -- but it is no longer the
# ceiling on an ATTESTATION sigma, which measures something else entirely. See the derivation
# below `_RAW_SIGMA`, where SIGMA_MAX is rebound to the charter's own widest named grade.
SIGMA_UNIFORM_PRIOR = 9.9 / (12 ** 0.5)
SIGMA_MAX = SIGMA_UNIFORM_PRIOR

# The axis scale, named rather than spelled `9.9` in eight places. An axis score outside it is a
# DATA ERROR, and until 2026-08-25 it was absorbed in silence -- `ruin = 99.0` produced a decimal
# and an interval that looked exactly like a real reading. See `_check_scores`.
AXIS_MIN = 0.0
# 10.0, NOT 9.9, and the difference is real rather than a rounding preference. `axis_score()`
# SATURATES at 9.9 (that saturation is its own open bug, M18), but the composite range the engine
# is built on is [0, 10] -- `assay()`'s own ceiling comment says so, and verify_math tests the
# ceiling by scoring every axis at exactly 10.0. Setting this to 9.9 refused that legitimate
# reading and broke the battery, which is a useful demonstration of the rule this whole layer
# keeps arriving at: a guard tightened past what the system actually does is not a stricter
# guard, it is a broken one. The values worth refusing -- 99.0, -5.0, "lots" -- are refused
# either way.
AXIS_MAX = 10.0

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
# THE SCALE IS ANCHORED ON THE CHARTER'S CALIBRATION POINT, NOT ON THE WIDEST GRADE.
# (Owner ruling 2026-08-25: "fix the bug so it honours the charter's +/-0.12, because of what it
# MEANS -- not that it should always be +/-0.12 if it isn't called for in a given situation.")
#
# THE BUG. This used to read `_SCALE = SIGMA_MAX / max(_RAW_SIGMA.values())`, pinning the WIDEST
# grade (Disputed, 8.50) to the ceiling and dividing everything else by the same factor. That
# choice was made to fix a real incoherence -- raw Witnessed at 4.08 exceeded SIGMA_MAX, so an
# axis nobody could read published a NARROWER bar than one that was witnessed -- but it fixed it
# by compressing the whole table to 0.336x, and the charter's own worked example fell with it:
# Kenshiro is published at +/- 0.12 and the code printed +/- 0.06. Every attestation on every
# entry in the library inherited the same halving. An interval is a claim about how much the
# library does not know; halving it silently is the most consequential kind of quiet error here.
#
# THE FIX, and the measurement that makes it possible. Solve for the Witnessed sigma that
# reproduces the charter's published interval on the charter's own worksheet, under the CURRENT
# two-component `_interval` (not the one-component version these raw figures were fitted to):
#
#     Witnessed sigma needed for Kenshiro -> +/- 0.12   :  2.7436
#     SIGMA_MAX, the uniform-prior hard bound           :  2.8579
#
# IT FITS. The charter's calibration was never actually incompatible with the ceiling -- only
# with anchoring the scale at the wrong end. So Witnessed is placed exactly where the charter
# puts it, and the grades WIDER than Witnessed are mapped into the remaining headroom between it
# and the ceiling instead of being scaled from zero.
#
# Both invariants now hold at once, which is what the previous fix could not manage:
#   * the charter's calibration is exact, and it EMERGES from the method -- a different worksheet,
#     a different attestation or a contested reading gives a different interval, as it must;
#   * monotonicity is preserved -- Instrumented < Witnessed < Transcribed < Reconstructed <
#     Disputed <= SIGMA_UNKNOWN -- so more ignorance can never buy a narrower bar.
_ANCHOR_GRADE = "Witnessed"          # the charter's calibration point, named in Part Three
_ANCHOR_RAW = _RAW_SIGMA[_ANCHOR_GRADE]

# SOLVED, not guessed: the Witnessed sigma that reproduces the charter's published Kenshiro
# interval under the CURRENT two-component `_interval`, on the charter's own EIGHT-axis battery
# with the three faculty axes marked INAPPLICABLE (they postdate Part Three -- see below).
# The published interval is given to two decimals, so a RANGE of sigmas reproduces it. The
# MIDPOINT is taken rather than the first root: sitting on the edge of a rounding bucket is how
# a constant comes to depend on the last bit of a float, and an earlier bisection landed one
# ten-thousandth below the boundary and printed 0.11.
#
# RE-SOLVED 2026-08-25 WHEN THE COVARIANCE TERM WAS ADDED, and the charter's number is what
# stayed fixed. Owner ruling: the charter publishes +/- 0.12 and the charter is the ground
# truth, so the intermediate constant moves and the published bar does not. Swept again at
# 0.0005 resolution under the three-component `_interval`: sigma 1.7225 .. 1.8720 all yield
# +/- 0.12 on Kenshiro. Previously 3.2003, against a formula that omitted the larger half of
# the variance.
#
# AND THE RESULT IS COHERENT FOR THE FIRST TIME, which is the strongest evidence the covariance
# term belongs here. The long comment below records that the old ceiling had to be abandoned
# because the charter's own calibration point could not be represented under it -- raw Witnessed
# fitted to 4.08 on a scale whose maximum-entropy dispersion is 2.86, i.e. the charter's best
# grade of testimony came out MORE uncertain than knowing nothing at all. That was never a
# defect in the charter. It was the missing covariance being absorbed into the per-axis sigma,
# which is the only place the old formula had to put it. With the term present, Witnessed sits
# at 1.80 -- comfortably inside the uniform-prior bound, in the order one would expect.
_ANCHOR_SIGMA = 1.7973
_SCALE = _ANCHOR_SIGMA / _ANCHOR_RAW

# Straight proportion, so every ratio and the whole ORDER the charter gives is preserved.
SIGMA_BY_ATTESTATION = {k: round(v * _SCALE, 4) for k, v in _RAW_SIGMA.items()}

# WHY THE OLD CEILING WAS THE WRONG BOUND, since removing a stated hard bound needs an argument.
#
# `SIGMA_MAX = 9.9/sqrt(12)` is the standard deviation of a UNIFORM PRIOR over the 0-9.9 band --
# a correct bound for the dispersion of a single axis READING about which nothing is known. But
# the attestation sigmas are not per-axis reading noise. The comment above says so itself: they
# "were fitted to reproduce the charter's published intervals", which means they carry the
# SYSTEMATIC uncertainty of a whole grade of testimony, not the scatter of one measurement. Two
# different quantities were being compared, and the smaller one was used to cap the larger.
#
# The consequence was measured: the charter's calibration point could not be represented at all.
# Every sigma at or above the old ceiling produced +/- 0.11 on the charter's own worked example,
# where the charter publishes +/- 0.12 -- so the instrument could not reproduce the number the
# charter defines it by, at any setting.
#
# The bound that IS answerable to the charter is the widest grade the charter itself names.
# "Disputed" is the charter's own statement of maximum uncertainty, so it becomes the ceiling,
# and ignorance sits AT it -- an unread axis is exactly as uncertain as the worst testimony the
# charter recognises, and never narrower than any of them.
SIGMA_MAX = SIGMA_BY_ATTESTATION["Disputed"]

# Ignorance sits AT the ceiling, so it is by construction at least as wide as any measurement.
SIGMA_UNKNOWN = SIGMA_MAX
# NONE is a finding, not a gap, so it is nearly certain -- but "absent" is still asserted from
# evidence and inherits a little of the reading's own dispersion.
SIGMA_NIL_FACTOR = 0.5


# ============================================================================================
# THE ASSAY'S OWN SAFETY NETS (owner ruling 2026-08-25)
# ============================================================================================
# WHY THIS SUBSYSTEM GETS ITS OWN NETS, AND WHY THEY ESCALATE HIGHER THAN MOST.
#
# A wrong number here does not damage one entry. Every printed Magnitude in the library carries
# an interval from this file, so a calibration that drifts is a library-wide falsehood, and it is
# the QUIET kind: `M3.52 +/- 0.06` is exactly as convincing as `M3.52 +/- 0.12`. That is why the
# halved interval survived for months without anybody noticing -- nothing about it looked wrong.
#
# The three properties CLAUDE.md's Hard Rule -1 requires, applied here:
#   INDEPENDENT  four different mechanisms -- input validation at the call, a constants check at
#                import, a calibration re-derivation against the charter, and drill attacks --
#                and no two of them fail the same way.
#   FAIL CLOSED  a score outside the axis scale RAISES rather than being absorbed; a broken
#                constants table refuses to import at all.
#   PROVEN       `calibration_report()` re-derives the charter's own published number instead of
#                asserting a constant, and `drill.py` attacks each net.

class AssayIntegrityError(ValueError):
    """The instrument is not fit to publish a number. Never caught and continued past."""


def _check_scores(scores, weights=None):
    """Every score must be a sentinel or a real number ON the axis scale, on an axis that EXISTS.

    THE SECOND GAP, closed 2026-08-26 (order b8a17bd503d3). A score whose key was not in the
    weight table passed this check and was then dropped by `assay()` without a trace: `used`
    filters on `k in W`, and `nil`, `applicable`, `unestimable` and `unscored` all iterate over
    W rather than over the caller's dict, so the key appeared in NO list, changed no
    denominator, and produced no diagnostic. Measured: `{ruin, ruinn, stamina}` and `{ruin}`
    returned the identical Moth Number, so a typo'd axis name was indistinguishable from never
    having supplied the axis at all -- the assay reported full confidence in a reading it had
    thrown away.

    This is the same shape as the X.11 erratum recorded above, where `k in WEIGHTS` zeroed three
    whole faculties library-wide. That fixed the weights. The FILTER was left silent, so the next
    misspelt or newly-invented axis would vanish exactly as the faculties had. It refuses now.

    The check is against the table actually in force -- a `weights=` override is a smaller
    universe of axes, and a key outside IT is dropped just as silently.

    THE GAP THIS CLOSES, measured 2026-08-25: `ruin = 99.0` on a 0-9.9 axis returned a decimal
    and an interval with no complaint, and so did `ruin = -5.0`. A transcription slip, a
    percentage pasted where a band score belongs, or a model emitting 85 because it was thinking
    in percent -- all silently shifted the composite and published a confident number.

    Raising is correct rather than clamping. A clamp would turn a data error into a plausible
    reading, which is the exact failure this project keeps arriving at from new directions.
    """
    W = weights if weights is not None else WEIGHTS
    bad = []
    unknown = []
    for k, v in (scores or {}).items():
        if k not in W:
            # Refused whatever the VALUE is: `{"ruinn": "n/a"}` is a typo carrying a sentinel,
            # not a finding about a Measure called ruinn.
            unknown.append(k)
            continue
        if v is NONE or v in (INAPPLICABLE, UNESTIMABLE) or v is None:
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            bad.append("%s=%r (not a number)" % (k, v))
        elif not (AXIS_MIN <= float(v) <= AXIS_MAX):
            bad.append("%s=%r (outside %.1f-%.1f)" % (k, v, AXIS_MIN, AXIS_MAX))
    if bad:
        raise AssayIntegrityError(
            "axis scores off the scale: " + "; ".join(sorted(bad)[:6])
            + ". The axis scale is %.1f-%.1f (Charter Part Three). A score outside it is a data "
              "error, not a very strong reading, and it is refused rather than clamped so it "
              "cannot become a plausible number." % (AXIS_MIN, AXIS_MAX))
    if unknown:
        hints = []
        for k in sorted(unknown)[:6]:
            near = difflib.get_close_matches(str(k), sorted(W), n=1, cutoff=0.6)
            hints.append("%r%s" % (k, (" (did you mean %r?)" % near[0]) if near else ""))
        raise AssayIntegrityError(
            "axis scores on axes that do not exist: " + "; ".join(hints)
            + ". The Measures in force are: " + ", ".join(sorted(W))
            + ". A score on an unrecognised axis is refused rather than dropped, because a "
              "dropped one is invisible: it appears in no scored list, no unscored list and no "
              "coverage figure, so a misspelt axis reads as an axis nobody supplied.")


def _check_constants():
    """The sigma table's invariants, verified AT IMPORT so a broken instrument cannot load.

    Two of these are the exact failures this file has already had:
      * monotonicity -- the pre-2026-08-25 table let an UNREAD axis publish a narrower bar than
        a witnessed one, which is the wrong direction for a library to be confident in;
      * the ceiling -- an attestation sigma above SIGMA_MAX is silently clamped by `_interval`,
        so a table can look calibrated in the source and behave differently in the arithmetic.
    """
    order = ["Instrumented", "Witnessed", "Transcribed", "Reconstructed", "Disputed"]
    vals = [SIGMA_BY_ATTESTATION[g] for g in order]
    if vals != sorted(vals) or len(set(vals)) != len(vals):
        raise AssayIntegrityError(
            "attestation sigmas are not strictly increasing: %s. Better testimony must never be "
            "assigned MORE uncertainty than worse testimony." % dict(zip(order, vals)))
    if SIGMA_UNKNOWN < max(vals):
        raise AssayIntegrityError(
            "SIGMA_UNKNOWN (%.4f) is below the widest attestation grade (%.4f) -- an axis nobody "
            "could read would publish a TIGHTER bar than the worst testimony on file."
            % (SIGMA_UNKNOWN, max(vals)))
    if max(vals) > SIGMA_MAX:
        raise AssayIntegrityError(
            "an attestation sigma (%.4f) exceeds SIGMA_MAX (%.4f); `_interval` clamps it, so the "
            "table in the source is not the table in the arithmetic." % (max(vals), SIGMA_MAX))


# The charter's own worked example, kept HERE beside the constants it calibrates rather than
# only in the battery. Part Three's example predates Vol. X.6's three faculty axes, so they are
# INAPPLICABLE -- getting this wrong is what makes the calibration look unreachable, and it cost
# a full re-derivation on 2026-08-25 before the shape was noticed.
CHARTER_KENSHIRO = {"ruin": 2.1, "continuity": 4.8, "celerity": 6.5, "reach": 1.2,
                    "transgression": 8.7, "sustain": 7.4, "vector": 0.8, "volition": 9.6,
                    "acumen": INAPPLICABLE, "discernment": INAPPLICABLE,
                    "suasion": INAPPLICABLE}
CHARTER_KENSHIRO_INTERVAL = 0.12      # Charter Part Three, published
CHARTER_KENSHIRO_DECIMAL = 0.52


def calibration_report():
    """-> dict. Re-DERIVE the charter's published numbers; never assert a stored constant.

    The distinction matters and this file has the scar: the battery's own regression checks for
    the interval were recorded FROM the halved output, so they passed throughout the period the
    instrument was wrong. A check calibrated against the regression cannot see the regression.
    This one computes the charter's example through the live code and compares it to the number
    the CHARTER publishes, which is the only external authority available.

    `margin` is reported because the published interval has two decimals, so a range of sigmas
    reproduces it -- and sitting on the edge of that range is how a constant comes to depend on
    the last bit of a float. The first fix landed 0.0001 below the boundary and printed 0.11.
    """
    got = assay("M3", dict(CHARTER_KENSHIRO), attestation="Witnessed",
                worksheet="charter Part Three")
    lo = hi = None
    saved = SIGMA_BY_ATTESTATION["Witnessed"]
    # THE SWEEP TOUCHES NOTHING SHARED. This loop used to assign each trial sigma into
    # SIGMA_BY_ATTESTATION and put it back in a `finally` -- ~800 iterations during which every
    # other reader of that table (any concurrent `assay()`, and this runs from dashboard.py's
    # render and from drill.py's battery) computed its interval against a scratch value and
    # published it. It is the same fault the `weights=` override was introduced to end one
    # screen below, and it survived on the sigma side because a try/finally looks like the
    # cure. `sigma=` passes the trial value down the call it belongs to and nowhere else.
    s = max(AXIS_MIN + 0.5, saved - 2.0)
    while s <= min(SIGMA_MAX, saved + 2.0):
        if assay("M3", dict(CHARTER_KENSHIRO), attestation="Witnessed",
                 worksheet="w", sigma=s)["interval"] == CHARTER_KENSHIRO_INTERVAL:
            lo = s if lo is None else lo
            hi = s
        s += 0.005
    margin = None
    if lo is not None and hi is not None and hi > lo:
        margin = round(min(saved - lo, hi - saved) / ((hi - lo) / 2.0), 3)
    return {"interval": got.get("interval"), "want_interval": CHARTER_KENSHIRO_INTERVAL,
            "decimal": got.get("decimal"), "want_decimal": CHARTER_KENSHIRO_DECIMAL,
            "holds": (got.get("interval") == CHARTER_KENSHIRO_INTERVAL
                      and got.get("decimal") == CHARTER_KENSHIRO_DECIMAL),
            "sigma": saved, "band_lo": lo, "band_hi": hi, "margin": margin}


_RHO_CACHE = [None]

# Set the moment the correlation matrix turns out to be unavailable, and never cleared: a run
# that once computed a bar under the independence assumption computed it under the independence
# assumption, whatever the file does later.
RHO_FALLBACK_REASON = None

# The measured mean over 55 pairs, quoted in the message below so the loss has a SIZE attached.
# Naming the number is the difference between "a file is missing" and "every interval this
# process prints is roughly a factor narrower than the evidence supports".
_RHO_FALLBACK_NOTE = ("data/AXIS_CORRELATION.json unavailable, so `_rho` returned 0.0 and every "
                      "interval computed in this process ASSERTS THE MEASURES ARE INDEPENDENT. "
                      "They are not: the matrix measures a mean r of about +0.32 and every "
                      "sizeable pair positive, which makes these bars TOO NARROW. Rebuild with "
                      "`python src/axis_correlation.py --write` before publishing anything.")


def _rho_doc():
    """The measured matrix, loaded once per process. -> dict, EMPTY when it is unavailable.

    Cached because `_interval` runs per entity and the matrix is a small static file; read once
    per process, and a matrix edited mid-run does not take effect until the next one, which is
    the behaviour a calibration constant should have.

    ON THE FALLBACK, AND WHAT ACTUALLY GUARDS IT (corrected 2026-08-26, order c00cab9d0412).
    If the matrix is missing this degrades to rho = 0 -- the independence assumption -- which is
    the WRONG answer, deliberately chosen: it is the only value that reproduces the library's
    historical numbers exactly, so a missing file degrades to "as it was before" rather than to
    some third behaviour nobody has seen.

    The docstring here used to justify that by saying `_check_constants` "refuses at import time
    if the matrix is absent when it should be present". IT DOES NOT AND NEVER DID: that function
    checks the sigma table's monotonicity and ceiling and does not mention the matrix, and no
    import-time guard over it exists anywhere in this file. The fallback was covered by ONE
    thing, `drill.py:drill_correlation`, which fails a drill round when the matrix is missing --
    real cover, but it runs when somebody runs the drill, not when an assay is computed, so a
    batch could publish a full run of too-narrow bars between two green rounds.
    // A guard cited in a comment and absent from the code is worse than no guard, because the
    // next reader stops looking. That is the specific failure being repaired here.

    THE ADDED GUARD IS NOT AN IMPORT-TIME REFUSAL, and deliberately not. Refusing to import
    would take down every consumer of this file -- the whole library's ability to print any
    number -- over a derived cache that `axis_correlation.py --write` regenerates from data
    already on disk, and it would do it on a fresh clone before that file has ever been built.
    So the fallback ANNOUNCES instead: once to stderr, permanently on `RHO_FALLBACK_REASON`, and
    on the face of every assay it touches via `correlation_source`. It cannot fire unnoticed.
    """
    global RHO_FALLBACK_REASON
    if _RHO_CACHE[0] is None:
        doc, why = None, None
        try:
            import axis_correlation
            doc = axis_correlation.load()
            if not doc:
                why = "load() returned nothing (file missing, unreadable, or carrying no `pairs`)"
        except Exception as exc:
            why = "axis_correlation would not import: %r" % (exc,)
        _RHO_CACHE[0] = doc or {}
        if why:
            RHO_FALLBACK_REASON = why
            print("assay.py: " + _RHO_FALLBACK_NOTE + " Cause: " + why, file=sys.stderr)
    return _RHO_CACHE[0]


def _rho_source():
    """-> a one-line provenance stamp for the correlations behind an interval.

    Carried on every assay because stderr is not a record: a batch redirects it, a dashboard
    never sees it, and the entry outlives the run. A reader of one published number can tell
    from the number itself whether its bar was computed against measured correlations or
    against the independence assumption.
    """
    if _rho_doc():
        return "measured: data/AXIS_CORRELATION.json"
    return "FALLBACK rho=0, independence ASSERTED not measured -- " + (RHO_FALLBACK_REASON or "")


def _rho(a, b):
    """Measured correlation between two Measures. -> float in [-1, 1]."""
    doc = _rho_doc()
    if not doc:
        return 0.0
    # DELEGATED, not reimplemented. This function first carried its own copy of the lookup --
    # sort the pair, read the table, fall back to the mean -- and the liveness ratchet caught
    # the consequence within the hour: `axis_correlation.rho` had no callers, because its only
    # caller had been rewritten from scratch here. Two implementations of one rule are two
    # answers to it, which is the exact fault this session had just finished fixing in
    # `corpus_db`'s spine column. The fallback to the measured mean rather than to zero lives
    # in that function, where it is documented once.
    import axis_correlation
    return axis_correlation.rho(a, b, doc)


def _interval(scores, used, nil, applicable, attestation, denom, hand_readings=None,
              weights=None, sigma=None):
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
    # more certainty than the ceiling, and a future edit to the table must not either. The
    # clamp applies to a per-call `sigma=` override too, which is the whole point of having it:
    # a caller sweeping sigmas must not be able to buy certainty the table cannot.
    sigma = min(SIGMA_MAX,
                sigma if sigma is not None else SIGMA_BY_ATTESTATION.get(attestation, SIGMA_MAX))
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
    # ------------------------------------------------------------------ COVARIANCE
    #
    # THE TERM THAT WAS MISSING, and it was the larger half. Everything above is the propagation
    # formula for INDEPENDENT quantities. The Measures are not independent, and this is not a
    # supposition -- `axis_correlation.py` measured it over the 45 entities in the library
    # carrying two or more numeric axis scores:
    #
    #     reach x ruin  r = +0.816 (n=44)   continuity x sustain  r = +0.773 (n=42)
    #     acumen x discernment  r = +0.653 (n=44)      mean over 55 pairs  r = +0.319
    #
    # Every sizeable pair is POSITIVE. On the charter's own Kenshiro worksheet the covariance
    # term came to +3.125 against an independent variance of 1.440, so the bar the library was
    # publishing was **1.78x too narrow** -- an overstatement of confidence, which is the one
    # direction Part Three's preface forbids. Owner ruling 2026-08-25.
    #
    # APPLIED OVER EVERY APPLICABLE PAIR, each with its OWN dispersion -- which is the full
    # covariance matrix, `Var = SUM_i SUM_j w_i w_j rho_ij s_i s_j` with rho_ii = 1.
    #
    # The first version of this applied rho only among SCORED axes, on the reasoning that the
    # correlation was measured between VALUES and that ignorance about Ruin is not ignorance
    # about Reach. The battery refused it within the minute, and it was right: dropping the
    # cross terms for unknown axes DILUTED the scored axes' normalised weights without replacing
    # their covariance, so declaring three faculties UNESTIMABLE produced a NARROWER bar than
    # declaring them inapplicable. That is precisely the "less knowledge, narrower bar" defect
    # recorded above, reintroduced in a new place by the fix for a different one.
    #
    # And the statistics agree with the battery. If two Measures genuinely covary, then errors
    # about them covary too: not knowing Ruin and not knowing Reach are not independent
    # ignorances, because they are ignorance about the same correlated pair. Treating them as
    # independent understates the joint uncertainty for exactly the entities the library knows
    # least about.
    cov = 0.0
    _s = {}
    for k in applicable:
        _s[k] = (sigma if k in used
                 else sigma * SIGMA_NIL_FACTOR if k in nil
                 else SIGMA_UNKNOWN)
    _app = list(applicable)
    for _i in range(len(_app)):
        for _j in range(_i + 1, len(_app)):
            _a, _b = _app[_i], _app[_j]
            cov += (2 * (W[_a] / denom) * (W[_b] / denom)
                    * _rho(_a, _b) * _s[_a] * _s[_b])
    if cov:
        parts["_covariance"] = round(cov, 6)
    # A variance is not allowed to be negative however the correlations fall. If a future matrix
    # ever drove this below zero the formula would be returning an imaginary error bar, which
    # would surface as a crash somewhere far away from the cause.
    var = max(var + cov, 0.0)
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
          hand_readings=None, weights=None, sigma=None):
    """Compute a Moth Number: 𝔄 = M_a + (sum w_i * s_i) / 10   (Charter Part Three, step 3).

    Returns a dict, never a bare float -- a value without its interval, epoch and worksheet
    pointer is formally a rumour (Absolute 1 of the Five Absolutes), so the number is not
    handed out unaccompanied.

    `sigma=` is the same device as `weights=` and exists for the same reason. A caller that
    needs to see what the interval would be under a DIFFERENT attestation dispersion --
    `calibration_report` sweeps ~800 of them to find the band of sigmas reproducing the
    charter's published +/- 0.12 -- used to assign into the module-global SIGMA_BY_ATTESTATION
    under a try/finally. That is correct alone and silently wrong the moment anything else
    reads the table mid-sweep: it is the identical pattern this file already removed from
    custodes' axis-emphasis path (see the note above `W` below), left standing on the sigma
    side. A per-call value is invisible to every other caller by construction, and no window
    exists in which a published interval is computed against a sweep's scratch value.
    Run33 order 6797f36117ce.
    """
    if anchor not in LADDER:
        raise ValueError(f"anchor must be one of {LADDER}")
    # LAYER 1: the reading must be ON the scale, and ON an axis that exists, before any
    # arithmetic touches it. `weights=` is passed through because the override IS the table the
    # composite will filter on, so it is the table an unknown key must be judged against.
    _check_scores(scores, weights=weights)
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
                                    hand_readings=hand_readings, weights=W, sigma=sigma)

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
        # THE PRIMARY MEASUREMENT, PERSISTED (added 2026-08-26, order b03f2ab9951a).
        #
        # This dict is what a caller stores, and until today it recorded WHICH axes were scored
        # and the weighted VARIANCE each contributed, but never the score itself. The numbers
        # the whole assay is about were computed, folded into one composite, and dropped.
        #
        # The cost was measured rather than supposed. `data/ASSAYS.json` holds 507 automated
        # assays; 217 scored at least one axis and 153 scored two or more -- and every one of
        # those readings is unrecoverable, so `axis_correlation.py` still builds the rho matrix
        # that widens EVERY published interval in the library from 45 hand-built entities. The
        # crawl could run for another month and that 45 would not move.
        #
        # ADDITIVE, never a replacement: `axes_scored` keeps its exact meaning and its readers
        # (`axis_correlation.py`, `reference.py`) keep parsing. The keys of this dict are
        # `axes_scored` by construction -- the same `used` -- so the two can never disagree.
        #
        # A ROW WITHOUT THIS KEY IS "NOT RECORDED", NEVER ZERO. The 507 rows already on disk
        # predate it and are not rewritten here. Reading a missing `scores` as an absence of
        # capability would invent a library-wide finding out of a schema change, which is the
        # single most damaging way to consume this field.
        "scores": {k: used[k] for k in sorted(used)},
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
        # Provenance for the covariance half of that variance. `_interval` is the larger half of
        # this number's honesty and it depends on a file that can be missing; the stamp says
        # which of the two arithmetics produced the bar printed above.
        "correlation_source": _rho_source(),
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
    # `grade_n <= 5` cannot be false while the Ladder has eleven rungs, and the run33 sweep
    # filed it as a tautology (order e496aef86818). It is a BOUNDS GUARD, not a test: the
    # literal below has six slots, so the day a rung is added above M10 the alternative to this
    # branch is an IndexError raised from inside the Instrument. Definition 5 caps the printed
    # Grade at V regardless, so saturating is the right answer and not a guess. Left standing.
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


# LAYER 2: THE INSTRUMENT CHECKS ITSELF AT IMPORT, and refuses to load if it is unfit.
# Deliberately at import rather than on first use: a broken sigma table must not be able
# to publish even one number while waiting to be noticed, and every consumer of this file
# imports it before it computes anything. This mirrors the `_BAD_CHARS` guard at the top
# of the kit's modules -- corruption stops the program rather than colouring its output.
_check_constants()
