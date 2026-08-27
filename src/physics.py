#!/usr/bin/env python3
"""
PHYSICS — the real-world quantities the Assay converts fiction into, and where they come from.

WHY THIS FILE EXISTS AT ALL
---------------------------
It was found missing. On 2026-08-22 the first full-project audit ran `--help` against all
sixty-seven modules — the cheapest total exercise there is, since it runs every import and every
load-time constant without doing any work — and four of them could not even start:

    verify_math   AttributeError: module 'feats' has no attribute 'kinetic'
    anchors       AttributeError: module 'feats' has no attribute 'kinetic'
    ledger        ImportError: cannot import name 'MATERIAL' from 'feats'
    address_space ValueError: xenoverse=11 does not fit in 3 bits

`verify_math` is the module whose whole job is independently verifying every number this project
computes. It had not run in some time and nothing noticed, because nothing invoked it — which
means every number it checks had been unverified for exactly as long. That is this project's
defect one level up again: a check nobody runs and a check that passes are indistinguishable
from the outside.

The cause was ordinary. These constants lived in `feats.py` when `feats.py` was a feat
CALCULATOR. It was later rewritten into a wiki miner, and the physics went out with the rewrite
while three modules kept importing it. Putting energy constants in the module that makes HTTP
requests was the original mistake; this is their proper home.

WHAT IS IN HERE, AND WHY THESE NUMBERS
--------------------------------------
Every figure is a real physical quantity, which is the entire point of the Assay: joules mean the
same thing in every fiction, so they are the one currency in which a punch in one world and a
punch in another can be compared without anybody's opinion entering.

The material figures are SPECIFIC ENERGIES — joules to do a stated thing to one cubic metre —
and they are the standard destructive-capacity values, given here in J/m^3:

    fragmentation          the piece breaks into chunks
    violent fragmentation  the chunks are thrown
    pulverisation          reduced to dust
    vaporisation           phase change to gas, which is orders of magnitude dearer

Pulverisation of rock, 2.14e8 J/m^3, is the figure the Ledger Standard is denominated in, so a
currency unit and a combat feat are priced in the same joules. That reuse is deliberate and is
asserted by `verify_math`; if this number moves, the currency moves with it.
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

C = 2.99792458e8            # m/s, exact by definition of the metre
RELATIVISTIC_ABOVE = 0.1    # fraction of c at which the Newtonian form stops being honest

# Specific energies in JOULES PER CUBIC METRE. Rock's pulverisation figure is the anchor the
# Ledger Standard reuses; the rest are the conventional destructive-capacity values for their
# materials, and each is a property of the material rather than of any fiction.
MATERIAL = {
    "rock":     {"frag": 8.0e6,  "vfrag": 6.9e7,  "pulv": 2.14e8, "vapor": 2.57e10},
    "concrete": {"frag": 6.0e6,  "vfrag": 4.0e7,  "pulv": 1.70e8, "vapor": 2.50e10},
    "steel":    {"frag": 2.08e8, "vfrag": 6.86e8, "pulv": 1.51e9, "vapor": 4.74e10},
    "ice":      {"frag": 2.0e6,  "vfrag": 5.0e6,  "pulv": 1.35e7, "vapor": 2.85e9},
    "wood":     {"frag": 2.0e6,  "vfrag": 5.0e6,  "pulv": 1.20e7, "vapor": 1.20e10},
    "flesh":    {"frag": 1.5e6,  "vfrag": 5.0e6,  "pulv": 1.20e7, "vapor": 2.66e9},
}

MODES = ("frag", "vfrag", "pulv", "vapor")


def kinetic(mass_kg, speed_ms):
    """Kinetic energy in joules, Newtonian below 0.1c and relativistic above it.

    The switch is not fussiness. At 0.5c the Newtonian formula understates the energy by about a
    third, and this library routinely assays beings described as moving at appreciable fractions
    of light speed — an understated feat lands in a lower Magnitude band, which is a wrong answer
    arrived at by arithmetic rather than by judgement, and therefore the hardest kind to notice.
    """
    v = abs(float(speed_ms))
    m = float(mass_kg)
    if not m > 0.0:
        # The same defect `sphere_volume()` and `binding_energy()` below already refuse: a
        # negative mass squares (or here, multiplies through) into a negative energy that wears
        # the shape of a real one, and nothing downstream has reason to look at it twice.
        raise ValueError(f"kinetic(): mass must be positive, got {mass_kg!r}; "
                         f"a non-positive mass is an unestimable body, not a small one")
    if v >= C:
        # Nothing with mass reaches c. A source that says otherwise is describing something the
        # Assay must handle as UNESTIMABLE on this axis, not as a very large number.
        raise ValueError("kinetic(): a massive body cannot travel at or above c; "
                         "this feat is unestimable in joules, not merely large")
    if v < RELATIVISTIC_ABOVE * C:
        return 0.5 * m * v * v
    gamma = 1.0 / math.sqrt(1.0 - (v / C) ** 2)
    return (gamma - 1.0) * m * C * C


def joules_for(volume_m3, material="rock", mode="pulv"):
    """Energy to do `mode` to `volume_m3` of `material`.

    Raises on an unknown material or mode rather than defaulting to rock. A silent default here
    would be a wrong energy wearing the shape of a right one, and it would propagate into a band,
    a shelfmark, and eventually a volume of prose.
    """
    if material not in MATERIAL:
        raise KeyError(f"joules_for(): no specific energy on record for {material!r}; "
                       f"known: {', '.join(sorted(MATERIAL))}")
    if mode not in MODES:
        raise KeyError(f"joules_for(): unknown mode {mode!r}; known: {', '.join(MODES)}")
    v = float(volume_m3)
    if not v > 0.0:
        # Same defect as `kinetic()`'s mass and `sphere_volume()`'s radius: a negative volume
        # returns a negative joule figure without raising anything, and it is indistinguishable
        # downstream from a small positive one until it lands in a band and a shelfmark.
        raise ValueError(f"joules_for(): volume must be positive, got {volume_m3!r}; "
                         f"a non-positive volume is an unestimable body, not a small one")
    return v * MATERIAL[material][mode]


def sphere_volume(radius_m):
    """Volume of a sphere of radius `radius_m`, in cubic metres.

    Rejects a non-positive radius rather than computing one, for the same reason `joules_for()`
    two functions above refuses to default to rock: a wrong number wearing the shape of a right
    one is the hardest kind to catch. The cube preserves sign, so a negative radius returns a
    NEGATIVE volume without raising anything, and that volume goes on to `joules_for()`, to a
    band edge, to a shelfmark, and eventually into prose, with nothing anywhere in that chain
    ever having reason to look at it twice. A radius of zero is not a smaller body, it is the
    absence of one, and the Assay has nothing to say about it.
    """
    r = float(radius_m)
    if not r > 0.0:
        raise ValueError(f"sphere_volume(): radius must be positive, got {radius_m!r}; "
                         f"a non-positive radius is an unestimable body, not a small one")
    return 4.0 / 3.0 * math.pi * r ** 3


def binding_energy(mass_kg, radius_m):
    """Gravitational binding energy of a uniform sphere, U = 3GM^2/5R.

    Uniform is a simplification and a poor one for a star, whose mass is centrally condensed and
    which therefore binds harder than this returns. `assay.BAND_EDGES` deliberately carries the
    LITERATURE value for the Sun (6.9e41 J) rather than what this function gives, and
    `verify_math` asserts that the two differ in the expected direction. Use this for rocky
    bodies and for order-of-magnitude work, never to set a band.

    A non-positive radius is refused for the same reason `sphere_volume()` refuses it, and with
    one extra edge of its own: R sits in the DENOMINATOR here, so R = 0 used to leave the module
    by way of a bare `ZeroDivisionError` — a traceback that names arithmetic rather than the
    domain error that caused it, and that a caller two modules away would read as a bug in the
    physics instead of as a body it had no business asking about.
    """
    G = 6.67430e-11
    r = float(radius_m)
    if not r > 0.0:
        raise ValueError(f"binding_energy(): radius must be positive, got {radius_m!r}; "
                         f"U = 3GM^2/5R has no value for a body of no extent")
    return 3.0 * G * float(mass_kg) ** 2 / (5.0 * r)


def main():
    ap = argparse.ArgumentParser(description="the real-world quantities the Assay converts into")
    ap.add_argument("--table", action="store_true",
                     help="print only the specific-energy table (suppress the worked examples "
                          "printed after it by default)")
    a = ap.parse_args()
    print("PHYSICS — specific energies in J/m^3\n")
    print(f"  {'material':<12}" + "".join(f"{m:>14}" for m in MODES))
    for name in sorted(MATERIAL):
        row = MATERIAL[name]
        print(f"  {name:<12}" + "".join(f"{row[m]:>14.3g}" for m in MODES))
    print(f"\n  1 Standard (the Ledger unit) = pulverise 1 m^3 of rock = "
          f"{MATERIAL['rock']['pulv']:.3g} J")
    print(f"  Newtonian below {RELATIVISTIC_ABOVE:.0%} c, relativistic above it")
    if a.table:
        return 0
    print(f"\n  a 75 kg body at 10 m/s          {kinetic(75, 10):>12.4g} J")
    print(f"  the same body at 0.5 c          {kinetic(75, 0.5 * C):>12.4g} J")
    print(f"  pulverise 1000 m^3 of concrete  {joules_for(1000, 'concrete', 'pulv'):>12.4g} J")
    return 0


if __name__ == "__main__":
    sys.exit(main())
