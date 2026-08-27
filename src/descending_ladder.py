#!/usr/bin/env python3
"""
THE DESCENDING LADDER — the rungs below Planet, and the Quantum Fold.

THE GAP THIS FILLS
------------------
The Ladder of Being (Charter, Part Two) has seventeen rungs and its first is **Planet**. There is
nothing below it. So the library has no address for a being standing on a molecule, no notation
for a realm reached by shrinking, and no way to say where Ant-Man *is* when he goes subatomic --
which is not a marginal case: the Microverse, the Quantum Realm, Horton's speck, the marble at
the end of Men in Black, Palpagos' islands seen from orbit, and every "world within a world" in
the corpus live below rung 1 and are currently unaddressable.

Worse, the omission is silently load-bearing. X.2's Reach axis is measured in metres and its band
edges are "rung-characteristic lengths" -- but there are no rung-characteristic lengths below
1e7 m, so every sub-planetary Reach is scored against a floor that does not exist.

THE FIX, IN ONE SENTENCE
------------------------
The Ladder is extended downward by fifteen rungs to the Planck length, using the same principle
that built it upward: **a rung is a scale at which a coherent thing is bound.** Rung 1 was never
special; it was just where the Custodes started counting because that is where they lived.

THE QUANTUM FOLD
----------------
Below the Planck length the description itself fails -- not "we lack instruments" but "length
ceases to be a meaningful coordinate", which is a statement about 𝔇 (the local law) rather than
about apparatus. X.2 Axiom M1 says every system carries its own 𝔇; the Fold is where one 𝔇 ends
and another may begin. That is why a sufficiently deep descent arrives somewhere that behaves
like a universe rather than like a very small room, and why the notation for it is a *fold*
rather than another rung: you do not keep going down, you come out somewhere else.

This is the honest formalisation of the trope. It does not claim the Quantum Realm is real; it
claims that IF a source attests a universe reached by descent, the address system can now write
it down, and the energetics below say what such a descent costs.
"""
import math

# ---------------------------------------------------------------- real constants (SI, cited)
PLANCK_LENGTH = 1.616255e-35   # m   (CODATA)
PLANCK_TIME = 5.391247e-44     # s
PLANCK_MASS = 2.176434e-8      # kg
PLANCK_ENERGY = 1.956e9        # J   (= Planck mass x c^2)
C_LIGHT = 2.99792458e8         # m/s
HBAR = 1.054571817e-34         # J*s
G_NEWTON = 6.67430e-11         # m^3 kg^-1 s^-2  (CODATA). Named here, not inlined (order
                               # 57acf43b339a) -- it was the one constant in this block missing,
                               # spelled out instead 95 lines down in schwarzschild_radius().
                               # scale_theories.py names the same value as G_NEWTON.
BOLTZMANN = 1.380649e-23       # J/K

# ------------------------------------------------------------------- THE DESCENDING RUNGS
#
# Numbered NEGATIVE, so the existing seventeen are untouched and the whole Ladder is one integer
# axis. Rung +1 (Planet) remains the pivot exactly as published; nothing above it moves.
#
# Each rung is a scale at which matter is BOUND into a coherent object -- the same criterion the
# ascending rungs use (a planet, a system, a galaxy are all binding scales). The characteristic
# length is the rung edge for Reach; the binding energy is the rung edge for Ruin.
DESCENDING = [
    # rung, glyph, name,             length (m),  characteristic binding energy (J)
    (0,   "Cn", "Continental",        1.0e6,      1.0e26),   # continent-scale crust
    (-1,  "Rg", "Regional",           1.0e5,      1.0e22),
    (-2,  "Ct", "Civic",              1.0e4,      1.0e17),   # a city
    (-3,  "St", "Structural",         1.0e2,      1.0e10),   # a building
    (-4,  "So", "Somatic",            1.0e0,      1.0e8),    # a body; ~human scale
    (-5,  "Og", "Organic",            1.0e-2,     1.0e5),    # an organ
    (-6,  "Cl", "Cellular",           1.0e-5,     1.0e-11),  # a cell
    (-7,  "Or", "Organellar",         1.0e-7,     1.0e-14),
    (-8,  "Mc", "Macromolecular",     1.0e-8,     1.0e-17),  # a virus, a protein
    (-9,  "Ml", "Molecular",          1.0e-9,     8.0e-19),  # covalent bond ~5 eV
    (-10, "At", "Atomic",             1.0e-10,    2.2e-18),  # 13.6 eV, hydrogen ionisation
    (-11, "Nu", "Nuclear",            1.0e-14,    1.3e-12),  # ~8 MeV per nucleon
    (-12, "Nc", "Nucleonic",          1.0e-15,    1.5e-10),  # ~938 MeV, proton rest energy
    (-13, "Qk", "Quark-confinement",  1.0e-18,    1.6e-10),  # ~1 GeV confinement scale
    (-14, "Pk", "Planck",             PLANCK_LENGTH, PLANCK_ENERGY),
]

# The Fold: below Planck, length is not a coordinate and the descent exits into another 𝔇.
FOLD_GLYPH = "⧉"
FOLD_RUNG = -15


def rung_table():
    return {r[0]: {"glyph": r[1], "name": r[2], "length_m": r[3], "binding_J": r[4]}
            for r in DESCENDING}


def rung_for_length(metres):
    """Which descending rung does a given size belong to? Returns (rung, name).

    THE DOMAIN IS BOUNDED AT BOTH ENDS, and out-of-domain is answered `(None, None)` at both.
    Below the Planck length there is no rung but there is an answer -- the Fold -- and that is
    returned. ABOVE `DESCENDING[0]`'s edge (1e6 m, continental crust) there is no answer here at
    all: that is the ASCENDING Ladder's territory, whose first rung is Planet at ~1e7 m.

    This used to leave `best` at its initialiser and report "Continental" for anything larger, so
    5e6 m, a gas giant and a galaxy all came back labelled rung 0 -- a silent mislabel of the one
    kind this project keeps paying for, since a caller cannot tell a real continental-scale
    answer from a value that fell off the top of the table. The function already answered `metres
    <= 0` with `(None, None)`; the top of the range now uses the same convention, so a number
    outside this ladder is refused rather than rounded into it.
    """
    if metres <= 0:
        return None, None
    if metres < PLANCK_LENGTH:
        return FOLD_RUNG, "Below the Fold"
    if metres > DESCENDING[0][3]:
        return None, None
    best = DESCENDING[0]
    for r in DESCENDING:
        if metres <= r[3]:
            best = r
    return best[0], best[2]


# --------------------------------------------------------------------- transit energetics

def compton_confinement_energy(size_m, mass_kg):
    """Energy required to CONFINE a mass to a given size, from the uncertainty principle.

    Delta_x * Delta_p >= hbar/2, so squeezing an object of mass m into radius r forces momentum
    spread p ~ hbar/(2r) and kinetic energy E ~ p^2/(2m).

    This is the honest physical objection to shrinking while conserving mass, and it is savage:
    it scales as 1/r^2, so every factor of ten smaller costs a hundred times more. It is also the
    reason a shrink that PRESERVES mass is a Transgression (it patches the uncertainty relation)
    while a shrink that SHEDS mass is merely engineering.
    """
    if size_m <= 0 or mass_kg <= 0:
        return None
    p = HBAR / (2.0 * size_m)
    return (p * p) / (2.0 * mass_kg)


def density_at_scale(mass_kg, size_m):
    """kg/m^3 if mass is conserved through the shrink. Compare: water 1e3, neutron star 1e17."""
    if size_m <= 0:
        return None
    return mass_kg / ((4.0 / 3.0) * math.pi * size_m ** 3)


def schwarzschild_radius(mass_kg):
    """r_s = 2GM/c^2. If a shrink takes an object below this, it is not small -- it is a hole."""
    return (2.0 * G_NEWTON * mass_kg) / (C_LIGHT ** 2)


def shrink_report(mass_kg, from_m, to_m):
    """Full accounting of a mass-conserving descent. Returns the physics, and the verdict.

    THE REPORT NAMES ITS OWN DESCENT. `from_m` was accepted and then never mentioned again, and
    the returned dict echoed neither end of the trajectory, so a caller holding the report could
    not say what it was a report OF without keeping its own copy of the arguments -- and a
    physics verdict separated from the trajectory it judges is one filing mistake away from being
    read against the wrong one. `from_m`, `to_m` and whether this is actually a descent are
    reported as data.

    `is_descent` is reported, NOT enforced. An attested trajectory that goes the other way is not
    a violation of physics, it is a caller asking the wrong function, and the objections list is
    reserved for laws that had to be patched -- putting a caller's mistake in it would corrupt
    `mass_conserved_is_lawful`, which downstream reads as a statement about the fiction.
    """
    rho = density_at_scale(mass_kg, to_m)
    conf = compton_confinement_energy(to_m, mass_kg)
    r_s = schwarzschild_radius(mass_kg)
    rung, name = rung_for_length(to_m)
    verdict = []
    if to_m < r_s:
        verdict.append(f"BLACK HOLE: target size {to_m:.2e} m is inside the Schwarzschild "
                       f"radius {r_s:.2e} m for this mass")
    if rho and rho > 1e17:
        verdict.append(f"beyond nuclear density ({rho:.2e} kg/m^3 vs ~1e17 for a neutron star)")
    if conf and conf > PLANCK_ENERGY:
        verdict.append(f"confinement energy {conf:.2e} J exceeds the Planck energy")
    return {
        "from_m": from_m, "to_m": to_m,
        "is_descent": bool(from_m is not None and to_m < from_m),
        "target_rung": rung, "target_rung_name": name,
        "density_kg_m3": rho, "confinement_energy_J": conf,
        "schwarzschild_radius_m": r_s,
        "mass_conserved_is_lawful": not verdict,
        "objections": verdict,
    }


NUCLEAR_DENSITY = 2.3e17          # kg/m^3, saturation density of nuclear matter


def transgression_bits(mass_kg, to_m):
    """Exception bits beta for a mass-conserving shrink, per X.2 §4.

    beta is the minimum description length of the PATCH to local law required to admit the
    attested trajectory. A shrink that SHEDS mass patches nothing (beta = 0) -- it is
    engineering, and the charter would file it as Vector or Praxis, not hax. A shrink that KEEPS
    mass has to suspend a law, and the question is which one.

    CORRECTED 2026-08-20. The first version priced the patch against the uncertainty relation,
    and returned beta = 0 for every case -- including a 70 kg man at atomic scale, which is
    plainly the most transgressive thing in the file. The error: Delta_x Delta_p >= hbar/2 is
    only expensive for SMALL masses. Confining 70 kg to 1e-10 m costs ~1e-51 J, nothing at all.
    Uncertainty is not the law being broken.

    The law being broken is DEGENERACY. Matter compressed past nuclear saturation collapses --
    that is why neutron stars have a maximum mass and why nothing sits at 1e31 kg/m^3 and stays
    a man. So the patch is priced against the density overshoot, and against the Schwarzschild
    condition beyond it, since an object inside its own event horizon is not small but gone.
    """
    rho = density_at_scale(mass_kg, to_m)
    if rho is None:
        return 0.0

    beta = 0.0
    if rho > NUCLEAR_DENSITY:
        # bits to amend "matter above saturation density collapses"
        beta += math.log2(rho / NUCLEAR_DENSITY)
    if to_m < schwarzschild_radius(mass_kg):
        # amending general relativity itself: the object is inside its own horizon and is
        # nonetheless attested walking around and talking. Priced separately and heavily.
        beta += math.log2(schwarzschild_radius(mass_kg) / max(to_m, PLANCK_LENGTH)) + 64.0
    return round(beta, 2)
