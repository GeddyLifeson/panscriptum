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
    if not math.isfinite(m):
        # THE OTHER HALF OF THE SAME ASYMMETRY (order 3598ae9a4aad). `joules_for()` was given an
        # explicit finiteness test for exactly this and mass was not, so `kinetic(inf, 10)`
        # returned inf: this module refused infinity for SPEED and for VOLUME and accepted it
        # for MASS. `not m > 0.0` above catches NaN as a side effect of its shape and lets
        # infinity straight through, which is the cause `joules_for()`'s own comment already
        # diagnoses. An inf joule figure is not a large quantity, it is the absence of one, and
        # it propagates to a band edge, a shelfmark and prose with nothing downstream having
        # reason to look at it twice.
        raise ValueError(f"kinetic(): mass must be finite, got {mass_kg!r}; "
                         f"an unbounded body is unestimable in joules, not merely large")
    if not v >= 0.0:
        # NaN, and it was the one value that got through this whole module (order 7909342fefa4).
        # EVERY comparison against NaN is False, so `v >= C` was False and `v < RELATIVISTIC_ABOVE
        # * C` was False too, and the speed fell to the relativistic branch, where gamma is NaN
        # and the joule figure is NaN -- returned with no exception, into a band, a shelfmark and
        # eventually prose. Mass, volume and radius are all refused by `not x > 0.0`, which
        # happens to catch NaN as a side effect of its shape; speed was the one parameter whose
        # guard was written the other way round, as `v >= C`, and so had no such accident. This
        # is the same test in the shape that refuses it on purpose. (`abs()` above means a
        # negative can never reach here; only NaN can fail this.)
        raise ValueError(f"kinetic(): speed is not a number, got {speed_ms!r}; "
                         f"NaN is the absence of a measurement, not a large one")
    if v >= C:
        # Nothing with mass reaches c. A source that says otherwise is describing something the
        # Assay must handle as UNESTIMABLE on this axis, not as a very large number. Infinity
        # lands here, which is the right verdict for it.
        raise ValueError("kinetic(): a massive body cannot travel at or above c; "
                         "this feat is unestimable in joules, not merely large")
    if v < RELATIVISTIC_ABOVE * C:
        result = 0.5 * m * v * v
    else:
        gamma = 1.0 / math.sqrt(1.0 - (v / C) ** 2)
        result = (gamma - 1.0) * m * C * C
    if not math.isfinite(result):
        # THE RESULT, NOT JUST THE INPUTS (order 371088645964). Every guard above refuses an
        # infinite ARGUMENT; none of them refuses an infinite ANSWER, and `kinetic(1e308, 1e5)`
        # -- two entirely finite, entirely accepted arguments -- overflows inside the arithmetic
        # and returns `inf` anyway. It arrives by a different door from the one order 3598ae9a4aad
        # shut, and it arrives from inputs this function has no grounds to refuse: 1e308 kg is
        # absurd, but refusing it outright would be an arbitrary mass ceiling, a different and
        # worse decision than testing what the arithmetic actually produced. Same wording as the
        # input guards, because it is the same fact from the other side: an inf joule figure is
        # not a large quantity, it is the absence of one, and nothing downstream has reason to
        # look at it twice before it reaches a band edge, a shelfmark and prose.
        raise ValueError(f"kinetic(): mass={mass_kg!r}, speed={speed_ms!r} produced a "
                         f"non-finite result; this feat is unestimable in joules, not merely "
                         f"large")
    return result


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
    if not math.isfinite(v):
        # The other half of order 7909342fefa4. `not v > 0.0` catches NaN by accident and lets
        # INFINITY straight through, so `joules_for(float('inf'))` returned inf -- a joule figure
        # that is not a quantity, wearing the shape of one, on its way to a band edge. An
        # unbounded body is UNESTIMABLE, which is a different answer from an enormous one, and
        # `kinetic()` above already gives infinity that verdict for speed.
        raise ValueError(f"joules_for(): volume must be finite, got {volume_m3!r}; "
                         f"an unbounded body is unestimable in joules, not merely large")
    result = v * MATERIAL[material][mode]
    if not math.isfinite(result):
        # THE RESULT, NOT JUST THE ARGUMENT (order 371088645964). A finite volume can still
        # overflow the multiply for `vapor`, the dearest mode by orders of magnitude; the same
        # `sphere_volume(1e100)` that raises OverflowError below feeds a finite-looking huge
        # volume in here, which then overflows silently. Checked here for the same reason
        # `kinetic()` now checks its result.
        raise ValueError(f"joules_for(): volume={volume_m3!r} of {material!r} ({mode}) "
                         f"produced a non-finite result; this feat is unestimable in joules, "
                         f"not merely large")
    return result


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
    if not math.isfinite(r):
        # `sphere_volume(inf)` returned inf and fed it straight to `joules_for()`, which refuses
        # an infinite VOLUME -- so the refusal fired one function late and named the wrong
        # argument. Refused here, where the unbounded body actually is (order 3598ae9a4aad).
        raise ValueError(f"sphere_volume(): radius must be finite, got {radius_m!r}; "
                         f"an unbounded body is unestimable in joules, not merely large")
    try:
        result = 4.0 / 3.0 * math.pi * r ** 3
    except OverflowError:
        # `r ** 3` OVERFLOWS FOR A LARGE FINITE `r`, AND THE EXCEPTION NAMES ARITHMETIC, NOT
        # A DOMAIN ERROR (order 371088645964) -- exactly the wrong answer `assay.py`'s
        # `_check_weights` docstring already names: "it names a line, not a fault, so the
        # caller is told the instrument broke rather than that their table was not one."
        # Caught and re-raised in this module's own voice, naming the argument that caused it.
        raise ValueError(f"sphere_volume(): radius={radius_m!r} produced a non-finite volume; "
                         f"this feat is unestimable in joules, not merely large") from None
    if not math.isfinite(result):
        raise ValueError(f"sphere_volume(): radius={radius_m!r} produced a non-finite volume; "
                         f"this feat is unestimable in joules, not merely large")
    return result


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
    if not math.isfinite(r):
        # R is the DENOMINATOR, so an infinite radius returned a perfectly finite-looking 0.0 --
        # "this body is not bound at all", published as a measurement of a body of unbounded
        # extent. That is the quietest of the four (order 3598ae9a4aad): the other three
        # returned inf, which at least looks wrong.
        raise ValueError(f"binding_energy(): radius must be finite, got {radius_m!r}; "
                         f"an unbounded body is unestimable in joules, not merely large; "
                         f"U -> 0 here is not a body that is easy to unbind")
    m = float(mass_kg)
    if not m >= 0.0:
        raise ValueError(f"binding_energy(): mass must be non-negative, got {mass_kg!r}; "
                         f"M^2 silently discards the sign of a negative mass, which is not a "
                         f"physical body")
    if not math.isfinite(m):
        # `binding_energy(inf, 1)` returned inf. `not m >= 0.0` carries the NaN and sign cases
        # and nothing else -- infinity passes it, exactly as it passed `kinetic()`'s mass guard
        # (order 3598ae9a4aad). The accidental OverflowError out of `m ** 2` at 1e200 is not a
        # guard: it names arithmetic, not a domain error, and it does not fire for inf at all.
        raise ValueError(f"binding_energy(): mass must be finite, got {mass_kg!r}; "
                         f"an unbounded body is unestimable in joules, not merely large")
    try:
        m2 = m ** 2
    except OverflowError:
        # `binding_energy(1e200, 1) -> OverflowError` out of `m ** 2` (order 371088645964). The
        # exception fires BEFORE any result exists, so there is nothing to test with
        # `math.isfinite` the way `kinetic()` and `sphere_volume()` do -- it has to be caught at
        # the point of overflow instead. It is not a mitigation as-is: it names arithmetic
        # rather than the domain error that caused it (`_check_weights`' exact complaint in
        # assay.py), and unlike `kinetic()`'s inf it does not even reach a value a caller could
        # mistake for real -- it just crashes two modules away from the body that caused it.
        # Re-raised in the module's own voice, naming the mass that overflowed.
        raise ValueError(f"binding_energy(): mass={mass_kg!r} produced a non-finite result "
                         f"(M^2 overflowed); this feat is unestimable in joules, not merely "
                         f"large") from None
    result = 3.0 * G * m2 / (5.0 * r)
    if not math.isfinite(result):
        raise ValueError(f"binding_energy(): mass={mass_kg!r}, radius={radius_m!r} produced a "
                         f"non-finite result; this feat is unestimable in joules, not merely "
                         f"large")
    return result


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
