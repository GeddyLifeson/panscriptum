#!/usr/bin/env python3
"""
DE TEMPORE — time across the omniverse, and what "now" can possibly mean.

THE PROBLEM
-----------
VIII.1 gives the One Calendar (AS, After the Sundering) and a concordance to local reckonings.
The Chronicle's canon-position table then asserts a shared "now" across thirty shelves at 1,204
AS: Fallout at c. 2296 local, Dragon Ball post-Tournament, Warhammer in Era Indomitus, all at
once.

**But simultaneity across universes is not a physical fact, and the charter never says what makes
it one.** In relativity, simultaneity is already frame-dependent within a single spacetime -- two
events "at the same time" for one observer are not for another. Between universes with no shared
spacetime there is no frame at all, so "simultaneous" has no physical referent whatsoever. The
Chronicle has been asserting something it has no mechanism for.

THE RESOLUTION
--------------
Simultaneity in the Panscriptum is **institutional, not physical**, and this is not a dodge -- it
is forced, and it is the same move the charter already made for objectivity.

  Two events are omniversally simultaneous iff they were ACCESSIONED TOGETHER: iff they carry the
  same position in the Chain of Record at a common registry.

Part Four already reached this conclusion about truth -- *"Objectivity, at rung 17, is not a
vision. It is a treaty"* -- because omniscient beings with different priors can agree on every
fact and still disagree on account. Time is the same case. There is no vantage from which the
omniverse's "now" is visible; there is only what the Communion has countersigned as contemporary.

Three consequences fall out, and each explains something the charter states without grounding:

  1. **The Canon of the Now runs perpetually behind** -- not from bureaucratic slowness but
     because "now" is DEFINED by the record, and the record is the slowest thing in it.
  2. **Ascension marks are timestamps.** An event at [^9] is not merely unratified; it is not yet
     omniversally *present*. It is local news.
  3. **Distant shelves are literally in each other's past.** X.7's propagation metric now has a
     relativistic reading: a shelf 1,126 years away is seen as it was, exactly as a distant star
     is. The Concordance Now is a lightcone, not a moment.
"""
import math

SECONDS_PER_YEAR = 3.15576e7
C_LIGHT = 2.99792458e8


# =========================================================== 1. LOCAL TEMPO AND ITS CONVERSION

# NO PER-SHELF TEMPO PARAMETER. This is deliberate and it is a correction.
#
# A first draft of this module declared a clock-rate ratio for every shelf -- a free parameter per
# universe, tuned by hand. That was wrong on the library's own terms, twice over:
#
#   1. It is a SECOND MECHANISM for an observation X.7 already explains. A shelf that appears to
#      be behind is behind because its news is in transit: arrival lag = 1000 * d, measured from
#      the shared-stage graph. Positing that it ALSO runs slow explains the same evidence a
#      second time.
#   2. Which is precisely the sin X.9 §4 prices. beta is a minimum DESCRIPTION LENGTH; a
#      codification carrying two mechanisms where one suffices is longer, and therefore scores
#      HIGHER on Transgression. Adding tempo ratios would have made the omniverse formally more
#      lawless in exchange for nothing.
#
# So apparent time differences between shelves are propagation, full stop. Use
# propagation.arrival_years(). What remains here are the DEGENERATE cases, which are not rates at
# all -- they are shelves where the concept of a rate fails, and each is already named in the
# charter rather than invented here.
DEGENERATE_TIME = {
    "the Basement Loop": ("CLOSED", "returns to its own start; no net reference time elapses, "
                                    "however much is locally experienced (II.N.3)"),
    "the Rot City": ("CLOSED", "resets to its first morning (II.N.3)"),
    "the Betweens (deep/Warp)": ("NON-MONOTONIC", "transit times are not additive and arrival "
                                                  "can precede departure; marked '?' per Working "
                                                  "Rule 2 rather than guessed (W.1)"),
    "the Pale": ("UNDEFINED", "erodes the record by which elapsed time would be measured. Not "
                              "slow — unmeasurable (II.N.4)"),
}


def apparent_lag_years(shelf_a, shelf_b):
    """How far behind does A see B? Derived entirely from X.7's propagation metric.

    No new quantity. This is arrival_years() under a different name, and the name matters: a
    distant shelf is not merely uninformed, it is being observed as it WAS. The Concordance Now
    is a lightcone, not a moment.
    """
    import propagation as P
    adj = P.load_graph()
    d, path = P.shortest(adj, shelf_a, shelf_b)
    if not path:
        return {"lag_years": None, "note": "no shared furniture; relation is mediated or absent"}
    return {"distance": round(d, 4), "lag_years": P.arrival_years(d), "path": path,
            "note": "A sees B as B stood this many years ago"}


# ========================================================= 2. INSTITUTIONAL SIMULTANEITY

def contemporaneous(mark_a, mark_b, tolerance=0):
    """Are two events omniversally contemporary? Institutional test, not physical.

    Events are contemporary iff their ascension marks match: they have climbed the Chain of Record
    to the same rung and are therefore "present" at the same registries.
    """
    return abs(mark_a - mark_b) <= tolerance


def is_present_at(event_mark, observer_rung):
    """Is this event part of the observer's NOW?

    An event ratified to rung n is present to every registry at or below n, and has simply not
    happened yet, so far as any higher registry is concerned. This is why a [^9] event is "true
    locally but not yet omniversal history" -- the charter's own phrasing, now with a mechanism.
    """
    return event_mark >= observer_rung


def concordance_now(observer_rung=17):
    """What 'now' means for an observer at a given rung. The Chronicle's table, explained."""
    return {
        "observer_rung": observer_rung,
        "definition": "the set of events ratified to at least this rung",
        "consequence": ("lower-rung observers have a LARGER now -- more events count as present, "
                        "because less ratification is required. The apex has the smallest and "
                        "oldest now in the omniverse, which is why the Canon of the Now ends "
                        "mid-sentence"),
    }


# ================================================================= 3. LOOPS AND CLOSED TIME

def loop_report(local_years_experienced, iterations=None):
    """A closed timelike shelf: the Basement, the Rot City.

    Net reference time elapsed is ZERO however much is locally experienced -- which is the honest
    statement of what a loop is, and it has a hard consequence the charter should carry: a looped
    shelf can never ACCESSION anything. The Chain of Record requires an event to ascend, and
    ascension takes reference time. A universe that returns to its own start has no reference time
    to spend, so its history cannot climb.
    """
    return {
        "local_years_experienced": local_years_experienced,
        "reference_years_elapsed": 0.0,
        "iterations": iterations,
        "max_ascension_mark": 0,
        "finding": ("a closed loop cannot accession. Its events are true, locally and "
                    "repeatedly, and can never become omniversal history -- the Custodes' "
                    "dispute over whether the Basement is a universe, a purgatory, or a prayer "
                    "is, mechanically, a dispute about whether an unaccessionable history is a "
                    "history"),
        "cross_ref": "II.N.3, the Closed Loops; XI.2, Disputed Cosmologies",
    }


# ============================================================ 4. FORESIGHT, PRICED

def rung_description_length(band):
    """L_r -- the bits needed to specify a rung-r macrostate. DERIVED, not declared.

    X.6 §4 requires reference edges for Acumen and names the quantity: "a rung description length
    L_r: the effective number of bits required to specify a rung-r macrostate under the declared
    codebook." It never supplies a value.

    A first draft of this module invented one (2^(rung-1)) with no derivation, which is exactly
    the free parameter the discipline forbids. The derivation was available the whole time: the
    Ruin band edges already fix, for every rung, the energy range that rung spans. The bits to
    specify a state within that range is the log of the range -- so L_r falls out of BAND_EDGES
    with no new quantity at all.

        L_r = log2( ruin_edge(r) / ruin_edge(M0) )

    This is not a new scale. It is the SAME scale the whole Assay runs on, read as information
    rather than as energy -- which is the reading X.2 §4 already uses for Transgression (exception
    bits) and X.6 §3 for all three faculty axes. Energy and information were never two currencies
    here.
    """
    from assay import BAND_EDGES, LADDER
    if band not in BAND_EDGES:
        return None
    floor = BAND_EDGES[LADDER[0]]["ruin"]
    return round(math.log2(BAND_EDGES[band]["ruin"] / floor), 2)


def band_resolution(band):
    """Bits spanned by a band's OWN window -- what one decimal point on any axis is worth.

    SPLIT OUT AFTER ANCHOR VALIDATION, which caught a conflation. rung_description_length() above
    measures CUMULATIVE content: how many bits separate this band's floor from the bottom of the
    Ladder. That is the right quantity for prescience, because the algorithmic content of a stream
    is everything there is in it to predict.

    It is the WRONG quantity for commensuration, and the anchors made that unmissable: L_r(M0) = 0
    by construction, so at the floor every axis point was worth ZERO bits and the Skate Guy and the
    Sword could not be compared at all. An instrument with no resolution at its own floor is not an
    instrument.

    What one axis POINT is worth is the width of the band it sits in:

        band_resolution(r) = log2( edge(r+1) / edge(r) ) ... and /10 per decimal point

    M10 has no band above it, so it inherits the M9->M10 width; saturation at the ceiling is a
    property of the Ladder, not a licence to invent an edge.
    """
    from assay import BAND_EDGES, LADDER
    if band not in BAND_EDGES:
        return None
    i = LADDER.index(band)
    if i + 1 < len(LADDER):
        lo, hi = BAND_EDGES[band]["ruin"], BAND_EDGES[LADDER[i + 1]]["ruin"]
    else:
        lo, hi = BAND_EDGES[LADDER[i - 1]]["ruin"], BAND_EDGES[band]["ruin"]
    return round(math.log2(hi / lo), 2)


def prescience_horizon_bits(band, lead_time_years):
    """What foresight COSTS, in the currency the Assay already uses.

    X.6 §3 defines Acumen as prediction-planning advantage in bits per epoch, and caps it: "the
    theoretical ceiling of the quantity is set by the algorithmic information content of the rung
    process itself -- no agent extracts more prediction than the stream contains."

    So prescience is not a separate power. It is an extreme Acumen reading, priced against the
    stream it claims to read, using L_r from above.

    CROSS-REFERENCES, all load-bearing:
      X.2 §4   -- band edges supply L_r; bits are the same unit as Transgression's beta
      X.6 §3   -- Acumen's unit (bits/epoch) and its ceiling
      X.6 H5   -- a claim without a worksheet is band-bounded, not scored
      II.F.6   -- Dune's prescience is filed as "limited rung-13 sight", which this prices
    """
    L = rung_description_length(band)
    if L is None:
        return None
    required = L * lead_time_years
    return {
        "band": band,
        "rung_description_length_bits": L,
        "lead_time_years": lead_time_years,
        "bits_required": round(required, 2),
        "ceiling_note": ("compare against the claimant's attested Acumen in bits/epoch (X.6 §3). "
                         "A claim exceeding the stream's own content is not strong foresight — "
                         "it is incoherent, because there is nothing there to extract"),
        "derivation": "L_r = log2(ruin_edge(band) / ruin_edge(M0)); bits = L_r * years",
    }


def retrocausality_beta(effect_precedes_cause_by_years):
    """Exception bits for attested backwards causation, per X.2 §4.

    Patching the causal order is expensive: it is not one law but the arrow that orders all of
    them. Priced at a heavy structural constant plus the span, because a longer inversion touches
    more of the record.
    """
    if effect_precedes_cause_by_years <= 0:
        return 0.0
    return round(128.0 + math.log2(1.0 + effect_precedes_cause_by_years), 2)
