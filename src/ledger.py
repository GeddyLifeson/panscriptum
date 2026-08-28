#!/usr/bin/env python3
"""
DE PRETIO — the Ledger Standard, formalised.

I.9 asserts an omniversal economy: *"value across worlds is denominated against the Assay (Moth's
system moonlights as the omniverse's monetary standard -- gil, zenny, credits, caps, and bolts all
convert through it, to his documented horror)."*

Asserted, and never built. There is no conversion table anywhere in the library, which means the
one institution that would make the omniverse feel INHABITED rather than merely mapped -- a shared
price for a shared thing -- exists only as a sentence.

WHY THE ASSAY CAN CARRY A CURRENCY
----------------------------------
Because the Assay is already an energy-anchored log scale. X.2 §4 scores Ruin against
rung-characteristic binding energies in joules, and joules are the same everywhere by the same
argument that lets the Ladder be a shared ruler at all (X.2 §8: "the Ladder is the shared ruler
because it is the shared *situation*").

So the Standard's unit is defined against work, not against any world's mint:

    1 STANDARD (§) = the energy to pulverise one cubic metre of rock = 2.14e8 J

That figure is not arbitrary. It is the same quantity the feat ladder already uses to price
demolition, so a currency unit and a combat feat are denominated in the same thing -- which is the
founding demand ("the force of a punch and the force of a bullet use the same terms") applied to
money.

WHAT THIS BUYS THE LIBRARY
--------------------------
The Aperture Doctrine mandates that every LOCAL entry close with a Position Paragraph naming the
wider flows -- *"what it would fetch at the Freeport."* Without a conversion table that clause
cannot be written. With one, every mundane object in the catalogue acquires a thread to the
omniverse, and a cloak in a village becomes a thing with a price in a market it has never heard of.
"""
import math

# The unit, anchored to work. IMPORTED, not restated: if the feat ladder ever revises what it
# costs to pulverise a cubic metre of rock, the currency revises with it automatically. A literal
# copied by hand here would be a second, silently-drifting source of truth for one quantity --
# which is the exact failure the derivation ledger exists to catch.
from physics import MATERIAL       # noqa: E402

JOULES_PER_STANDARD = MATERIAL["rock"]["pulv"]     # 2.14e8 J -- the same figure the feat ladder prices
STANDARD_GLYPH = "§"


# ---------------------------------------------------------------- local currencies
#
# Each rate is anchored by a PURCHASING-POWER ANCHOR: one good whose value is attested in that
# world's own terms, converted to Standards through what that good can do. Rates are FICTIONAL and
# declared per Axiom M3, but the ANCHORS are the honest part -- change an anchor and the rate moves
# with it, which is what makes the table reversible rather than decreed.
CURRENCIES = {
    #  code        per Standard   anchor
    "gil":        (120.0,  "a night's inn lodging in a crystal-world capital"),
    "zenny":      (95.0,   "a mid-grade capsule; the Corridor's most-traded consumer good"),
    "credits":    (75.0,   "standard Federation replicator ration allocation"),
    "caps":       (12.0,   "a wasteland day's clean water -- scarcity-anchored, hence the low "
                           "rate: caps buy little because the Ashen Earths have little"),
    "bolts":      (300.0,  "a machined replacement part in a spacefaring economy"),
    "denarii":    (40.0,   "a legionary's daily stipend, Terra antiquity"),
    "gold pieces": (25.0,  "the Great Wheel's standard adventuring coin"),
    "poneglyph-grade favour": (None, "NOT CONVERTIBLE: the Grand Line's true currency is "
                                      "information the World Government has erased. A market "
                                      "cannot price what one party has criminalised knowing"),
}

# Condensates -- the material Chord (W.7). These are what the wars are actually fought over, and
# the Standard exists mostly to price them.
CONDENSATES = {
    "senzu bean":     (4.2e5,  "restores a combatant to peak from near-death: prices the "
                               "Continuity axis directly, which is why the Corridor is the "
                               "smallest tonnage and highest strategic weight in the Trade Web"),
    "spice (melange)": (9.0e5, "deep-sight; prices Vector, not Ruin -- monopoly-inflated well "
                               "above its work-equivalent, per the Arrakis Concession"),
    "energon (refined)": (1.2e4, "a Cybertronian's daily sustenance; collateralised to the frame "
                                  "since the Energon Panic of 934 AS"),
    "Element 115":    (7.5e5,  "Dark Aether coupling; priced with a hazard premium the Communion "
                               "regards as insufficient"),
    "eezo":           (3.1e4,  "mass-effect field generation; industrial rather than exotic"),
    "materia":        (2.6e4,  "crystallised technique; the only condensate that teaches"),
    "stimpak":        (85.0,   "field trauma repair; the Ashen Earths' whole medical economy"),
}


def currency_status(currency):
    """-> (listed, reason). Is `currency` a code this table even knows, and why can't it price?

    `to_standards`/`from_standards` both collapse two different situations to a bare `None`: a
    currency this catalogue never heard of (almost always a typo -- "quatloos") and a currency it
    lists BY NAME and marks deliberately non-convertible, with a reasoned doctrinal sentence
    attached ("poneglyph-grade favour": "A market cannot price what one party has criminalised
    knowing"). `CURRENCIES.get(currency, (None, "unlisted"))[0]` throws the reason away at the
    `[0]` subscript before either caller can tell the two apart, so a caller printing an Aperture
    Doctrine Position Paragraph would print "not convertible" for a misspelling the same as for a
    considered doctrinal position. This is additive -- `to_standards`/`from_standards` keep
    returning bare `None` either way, matching the existing "does not guess" contract -- and
    exists for a caller that wants to say WHY. (order e9167885aef6)
    """
    if currency not in CURRENCIES:
        return False, "unlisted"
    return True, CURRENCIES[currency][1]


def to_standards(amount, currency):
    """Convert a local sum into Standards. None where the currency is not convertible -- for
    UNLISTED vs. deliberately non-convertible, see `currency_status`."""
    rate = CURRENCIES.get(currency, (None, "unlisted"))[0]
    if rate is None:
        return None
    return amount / rate


def from_standards(standards, currency):
    """The inverse of `to_standards`. None where the currency is not convertible -- for
    UNLISTED vs. deliberately non-convertible, see `currency_status`."""
    rate = CURRENCIES.get(currency, (None, "unlisted"))[0]
    if rate is None:
        return None
    return standards * rate


def cross_rate(a, b):
    """How many units of b buy one unit of a."""
    ra = CURRENCIES.get(a, (None,))[0]
    rb = CURRENCIES.get(b, (None,))[0]
    if ra is None or rb is None:
        return None
    return rb / ra


def work_value(joules):
    """The Standard's definition, applied: what a quantity of work is worth."""
    return joules / JOULES_PER_STANDARD


def assay_to_standards(magnitude_band, ruin_score=5.0):
    """What a band of destructive capability is 'worth' in Standards.

    This is Moth's documented horror made explicit: because Ruin is energy and the Standard is
    energy, an entity's destructive capacity has a PRICE, and insurers, hiring halls, and siege
    contractors have been computing it since the Standard's founding whether or not he approved.

    Note the honest limit: this prices DELIVERABLE WORK, never the entity. An Anchor is a scale
    of presence (X.2 §3), and presence is not for sale -- which is precisely why the Ledger can
    price a warlord's artillery and not the warlord.
    """
    from assay import BAND_EDGES, LADDER
    if magnitude_band not in BAND_EDGES:
        return None
    i = LADDER.index(magnitude_band)
    lo = BAND_EDGES[magnitude_band]["ruin"]
    # M10 HAS NO BAND ABOVE IT TO SUPPLY A CEILING. `LADDER[min(i+1, len(LADDER)-1)]` clamped
    # the top rung back to ITSELF, so `hi == lo`, the log range collapsed to zero and
    # `ruin_score` stopped moving the answer at exactly the one band where the most extreme
    # entities sit: M10 at ruin_score 0, 5 and 10 all priced identically
    # (4.672897196261646e+90 Standards), while M9 spans fourteen orders of magnitude over the
    # same argument. `tempus.band_resolution` (tempus.py) faces the identical "no edge above the
    # ceiling" problem and answers it by giving M10 the same log-width as the M9->M10 gap rather
    # than a zero-width point -- borrowed here, but anchored at M10's OWN floor (as every other
    # band already is at ruin_score=0) rather than shifted down to M9's floor, which is what
    # copying tempus's exact interval would have done. (order 5082a529e937)
    if i + 1 < len(LADDER):
        hi = BAND_EDGES[LADDER[i + 1]]["ruin"]
    else:
        prev = BAND_EDGES[LADDER[i - 1]]["ruin"]
        hi = lo * (lo / prev)
    joules = math.exp(math.log(lo) + (ruin_score / 10.0) * (math.log(hi) - math.log(lo)))
    return {"joules": joules, "standards": work_value(joules),
            "caveat": "prices deliverable work only; the Anchor is a scale of presence "
                       "and not for sale"}
