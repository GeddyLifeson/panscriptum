#!/usr/bin/env python3
"""
THE PLANETARY CENSUS — a calculable template from universe-size down to a single world.

Proposed extension to Vol. I.3 (The Universal Register). Given a universe's size class, this
derives its exoplanet count, its life-bearing count, and the distribution of its civilizations
across the Kardashev scale -- and bridges Kardashev to the Magnitude ladder, so a civilization's
energy budget and a person's Assay are read on the same ruler.

WHY THIS IS ADMISSIBLE AS A CHARTER EXTENSION
---------------------------------------------
The Vade Mecum (IV.3) admits an extension only if it is Declared, Derivable, and Reversible.

  DECLARED   -- every convention below is published with its value and its source before use
                (Axiom M3). Measured constants are cited to the paper. Fictional conventions are
                labelled FICTIONAL and given a reason.
  DERIVABLE  -- the Moth test: a stranger with this file recomputes every number. No step is
                hand-waved; census(...) shows its working.
  REVERSIBLE -- every convention is a named module-level constant with an erratum note. Change
                one, re-run, and every downstream figure moves with it.

WHAT IS REAL AND WHAT IS DECLARED
----------------------------------
The astrophysics is real and cited. The biology is not -- nobody knows f_life, and pretending
otherwise would be the exact fabrication Hard Rule 3 forbids. So the biological terms are
declared as Panscriptum conventions, chosen to reproduce a *known* fact about this omniverse:
it is demonstrably crowded. That is honest calibration to an in-fiction observable, and it is
labelled as such on every line.

THE KARDASHEV-MAGNITUDE BRIDGE
-------------------------------
Kardashev measures a civilization's power budget in watts; the Assay's Ruin axis measures an
agent's deliverable work in joules. They convert through time: a civilization commanding P watts
commands P x 3.156e7 joules per year, and that lands in a Magnitude band by the same log rule
every other axis uses. This is why "a Type II civilization" and "an M4 entity" are finally
commensurable statements -- the founding demand, applied to polities.
"""
import math

# ============================================================ MEASURED CONSTANTS (real, cited)

SECONDS_PER_YEAR = 3.15576e7

# Galaxies in the observable universe. Two published figures, both kept, because the disagreement
# is real and the library's own doctrine is to file both readings rather than silently average.
GALAXIES_CONSELICE_2016 = 2.0e12   # Conselice et al. 2016, deep-field extrapolation
GALAXIES_LAUER_2021 = 2.0e11       # Lauer et al. 2021, New Horizons cosmic optical background
GALAXIES_DEFAULT = GALAXIES_LAUER_2021   # declared choice: the newer, more direct measurement

# Stars. The Milky Way is a large spiral and NOT typical -- most galaxies are dwarfs, which is
# why the mean is far below it.
STARS_MILKY_WAY = 2.0e11           # 100-400 billion; midpoint
STARS_PER_GALAXY_MEAN = 1.0e8      # dwarf-dominated mean; order-of-magnitude

# Planets per star. Microlensing says bound planets are the rule, not the exception.
PLANETS_PER_STAR = 1.6             # Cassan et al. 2012, Nature -- "planets around stars are the
                                   # rule rather than the exception"

# eta-Earth: rocky planets in the conservative habitable zone, per star, averaged over spectral
# types. Bryson et al. 2021 (Kepler final catalogue) gives 0.37-0.60 for conservative HZ around
# G/K dwarfs; G/K are a minority of stars, and M-dwarf habitability is contested (flares, tidal
# locking), so the all-star average is taken an order lower.
ETA_EARTH = 0.10                   # declared; Bryson et al. 2021 is the upper anchor

# Kardashev, Sagan's continuous formulation: K = (log10(P) - 6) / 10, P in watts.
KARDASHEV_TYPE_I = 1.0e16          # Sagan's Type I
KARDASHEV_TYPE_II = 4.0e26         # ~ solar luminosity, 3.828e26 W
KARDASHEV_TYPE_III = 4.0e37        # ~ galactic luminosity
EARTH_POWER_2020 = 2.0e13          # world primary energy consumption, ~18 TW


# ======================================================= PANSCRIPTUM CONVENTIONS (FICTIONAL)
#
# These are NOT measurements. Nobody knows them for the real universe. They are declared per
# Axiom M3 and calibrated to an in-fiction observable: the Universal Register carries 13,847
# inhabited worlds on its ACTIVE ROLLS at Delivery (I.9 Part Two) -- and those rolls are the
# charted subset, not the total ("the true count is the Grand Manifest's problem").
#
# The omniverse is demonstrably crowded: every one of 215 catalogued sources has inhabited
# worlds. So these run far above real-world pessimism, deliberately and visibly.

F_LIFE = 0.30          # FICTIONAL: habitable-zone rocky worlds that actually bear life.
                       # Reason: the Chord is a live substrate everywhere (I.7), so abiogenesis
                       # is not the rare accident the real-world Rare Earth position assumes.
F_COMPLEX = 0.10       # FICTIONAL: life-bearing worlds reaching complex multicellular life.
F_CIVILIZATION = 0.05  # FICTIONAL: complex-life worlds reaching a technological civilization.
F_SURVIVES = 0.40      # FICTIONAL: civilizations extant at any given epoch rather than fallen.
                       # Reason: the One War is ongoing and the Silence takes worlds (VIII.8).

# Kardashev distribution among extant civilizations. FICTIONAL, and shaped like a power law
# because climbing costs energy and most never do.
# CORRECTED 2026-08-20. The first draft set Type III at 0.001, which produced 1.2e12 galactic
# civilizations in a universe holding 2.0e11 galaxies -- six galaxy-spanning empires per galaxy.
# A Type III commands a galaxy BY DEFINITION, so that is not a large number, it is an incoherent
# one. Caught by validate() below, which now runs on every census and refuses to return a
# physically impossible one. The occupancy targets are declared:
#   Type III  -> ~5% of galaxies host one
#   Type II   -> vanishingly small share of stars, but many per galaxy
KARDASHEV_MIX = {
    "K < 1 (pre-planetary)": 0.90000,
    "Type I (planetary)":    0.08500,
    "Type II (stellar)":     0.01499,
    "Type III (galactic)":   0.00001,
}

# ---------------------------------------------------------------- THE STANDARD UNIVERSE RULE
#
# OWNER RULING, 2026-08-20: **a universe is one observable-universe-equivalent.** Not "roughly",
# not "varies by setting" -- the same size as this reality's observable universe, by definition,
# and that is the Register's default basis for every U-code.
#
# This is a genuine simplification with real consequences, all of them good:
#
#   * It makes the census a CONSTANT, not a per-universe estimate. Every STANDARD universe has
#     the same star count, the same exoplanet count, the same life-bearing count. A Register row
#     no longer needs a size field at all -- only a flag when a universe is NOT standard.
#   * It settles cross-universe comparison at the population level the same way rung-relative
#     units settled it at the individual level (X.2 §8). Two universes are the same *situation*,
#     so their inhabitants' rungs mean the same thing. The Ladder was already the shared ruler;
#     this makes the shared ruler the same LENGTH everywhere.
#   * It removes an inflation vector. Without it, every source's partisans would argue their
#     universe is bigger, and "bigger universe" would silently become a power argument.
#
# Exceptions are declared, not assumed, and the charter already names the class: II.N.3, "the
# small universes that re-run themselves" -- the Basement Loop, the Rot City of ANEURISM IV.
# A universe departs from STANDARD only where its own text forbids the standard reading, per the
# Continuity Rule's proviso ("unless its physics forbid it").
SIZE_CLASSES = {
    "POCKET":   1e-9,   # DECLARED EXCEPTION: a closed loop, a demiplane, one stage and no sky
    "MINOR":    1e-6,   # DECLARED EXCEPTION: a single galaxy's worth, walled
    "STANDARD": 1.0,    # THE DEFAULT AND THE RULE: one observable universe
}
DEFAULT_SIZE_CLASS = "STANDARD"


# ================================================================================ the census

def kardashev_K(watts):
    """Sagan's continuous Kardashev value. Earth today is ~0.73."""
    if watts <= 0:
        return None
    return round((math.log10(watts) - 6.0) / 10.0, 3)


def kardashev_to_magnitude(watts, band_edges=None, ladder=None):
    """Which Magnitude band does a civilization's ANNUAL energy budget reach?

    The bridge the founding demand asked for: a punch, a bullet, and a stellar civilization on
    one ruler. A polity commanding P watts delivers P x 3.156e7 J/year; that figure is read
    against the Ruin band edges exactly as an individual's feat would be.

    Note what this does NOT claim. Commanding the energy is not the same as delivering it as
    structured work against a resistant target -- Ruin is "peak deliverable structured work"
    (X.2 §4), and a civilization's power grid is not a weapon. This returns the band its budget
    REACHES, which is an upper bound on its Ruin, never its Anchor. The Anchor stays a scale
    of presence.
    """
    if band_edges is None or ladder is None:
        from assay import BAND_EDGES, LADDER          # local import: keeps this module standalone
        band_edges, ladder = BAND_EDGES, LADDER
    annual_joules = watts * SECONDS_PER_YEAR
    reached = ladder[0]
    for b in ladder:
        if annual_joules >= band_edges[b]["ruin"]:
            reached = b
    return reached, annual_joules


def census(size_class="STANDARD", galaxies=None, verbose=False):
    """Derive a universe's full planetary census from its size class.

    Returns every intermediate so the chain is auditable end to end -- the Moth test applied to
    a population rather than a person.
    """
    if size_class not in SIZE_CLASSES:
        raise ValueError(f"size_class must be one of {sorted(SIZE_CLASSES)}")
    mult = SIZE_CLASSES[size_class]
    n_galaxies = (galaxies if galaxies is not None else GALAXIES_DEFAULT) * mult

    stars = n_galaxies * STARS_PER_GALAXY_MEAN
    planets = stars * PLANETS_PER_STAR
    habitable = stars * ETA_EARTH
    life = habitable * F_LIFE
    complex_life = life * F_COMPLEX
    civs_ever = complex_life * F_CIVILIZATION
    civs_now = civs_ever * F_SURVIVES

    kardashev = {k: civs_now * v for k, v in KARDASHEV_MIX.items()}

    out = {
        "size_class": size_class,
        "galaxies": n_galaxies,
        "stars": stars,
        "exoplanets": planets,
        "habitable_zone_rocky": habitable,
        "life_bearing": life,
        "complex_life": complex_life,
        "civilizations_ever": civs_ever,
        "civilizations_extant": civs_now,
        "kardashev": kardashev,
        "conventions": {
            "eta_earth": ETA_EARTH, "f_life": F_LIFE, "f_complex": F_COMPLEX,
            "f_civilization": F_CIVILIZATION, "f_survives": F_SURVIVES,
        },
    }
    validate(out)
    if not out["valid"]:
        raise ValueError("census is physically impossible:\n  - "
                         + "\n  - ".join(out["problems"]))
    if verbose:
        print(_render(out))
    return out


def validate(c):
    """Refuse a census that violates the physical meaning of its own categories.

    A Kardashev type is defined by the SCALE IT COMMANDS, so each type has a hard ceiling set by
    how many of that thing exist. These are not style preferences; a census that breaks them is
    describing an impossible universe, and publishing it would put a fabricated number into the
    Register exactly as a naked Assay would.
    """
    problems = []
    k = c["kardashev"]
    t3 = k.get("Type III (galactic)", 0.0)
    t2 = k.get("Type II (stellar)", 0.0)
    t1 = k.get("Type I (planetary)", 0.0)

    if t3 > c["galaxies"]:
        problems.append(
            f"Type III ({t3:.3e}) exceeds galaxies ({c['galaxies']:.3e}): a galactic "
            f"civilization commands a galaxy; there cannot be more of them than galaxies")
    if t2 > c["stars"]:
        problems.append(
            f"Type II ({t2:.3e}) exceeds stars ({c['stars']:.3e}): a stellar civilization "
            f"commands a star")
    if t1 > c["habitable_zone_rocky"]:
        problems.append(
            f"Type I ({t1:.3e}) exceeds habitable worlds ({c['habitable_zone_rocky']:.3e})")
    if c["civilizations_extant"] > c["life_bearing"]:
        problems.append("more extant civilizations than life-bearing worlds")
    if abs(sum(KARDASHEV_MIX.values()) - 1.0) > 1e-6:
        problems.append(f"KARDASHEV_MIX sums to {sum(KARDASHEV_MIX.values())}, not 1.0")

    c["occupancy"] = {
        "galaxies hosting a Type III": (t3 / c["galaxies"]) if c["galaxies"] else None,
        "stars hosting a Type II": (t2 / c["stars"]) if c["stars"] else None,
        "habitable worlds hosting a Type I": (t1 / c["habitable_zone_rocky"])
        if c["habitable_zone_rocky"] else None,
    }
    c["valid"] = not problems
    c["problems"] = problems
    return c


def _fmt(x):
    if x >= 1e6:
        return f"{x:.3e}"
    if x >= 1:
        return f"{x:,.0f}"
    return f"{x:.4f}"


def _render(c):
    L = [f"UNIVERSE CENSUS — size class {c['size_class']}", ""]
    chain = [
        ("galaxies", "galaxies", ""),
        ("stars", "stars", f"x {_fmt(STARS_PER_GALAXY_MEAN)} stars/galaxy"),
        ("exoplanets", "exoplanets", f"x {PLANETS_PER_STAR} planets/star (Cassan 2012)"),
        ("habitable_zone_rocky", "in the habitable zone", f"x eta-Earth {ETA_EARTH}"),
        ("life_bearing", "BEARING LIFE", f"x f_life {F_LIFE} (declared)"),
        ("complex_life", "complex life", f"x f_complex {F_COMPLEX} (declared)"),
        ("civilizations_ever", "civilizations ever", f"x f_civ {F_CIVILIZATION} (declared)"),
        ("civilizations_extant", "EXTANT NOW", f"x f_survives {F_SURVIVES} (declared)"),
    ]
    for key, label, note in chain:
        L.append(f"  {_fmt(c[key]):>12}  {label:<24} {note}")
    L.append("")
    L.append("  Kardashev distribution of the extant:")
    for k, v in c["kardashev"].items():
        L.append(f"    {_fmt(v):>12}  {k}")
    return "\n".join(L)
