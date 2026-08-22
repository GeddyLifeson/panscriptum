#!/usr/bin/env python3
"""
THE SCALE-CHANGE THEORIES — what would have to be true, and what it would cost.

THE PROBLEM
-----------
"Ant-Man shrinks" is not one claim; it is a family of mutually exclusive claims that happen to
look the same from outside. Until the library says WHICH, his Assay is undefined -- because the
theories disagree about his mass, his momentum, his available energy, and therefore his Ruin.
You cannot ask how he fares against a Saiyan until you have said what he is exempt from.

X.2 §4 gives the discipline: Transgression is beta, the minimum description length of the PATCH
to local law 𝔇 required to admit the attested trajectories -- and beta is "defined relative to a
codification of 𝔇 (Axiom M3: the codification is declared)." So the honest move is to declare
each candidate codification, price it, and see which the attested feats actually require.

Each theory below is stated as physics, priced in exception bits, and -- the part that matters --
made FALSIFIABLE: each predicts something different about growth, momentum, and what happens
when the shrinker punches something.
"""
import math

C_LIGHT = 2.99792458e8
G_NEWTON = 6.67430e-11
HBAR = 1.054571817e-34
NUCLEAR_DENSITY = 2.3e17
PLANCK_LENGTH = 1.616255e-35


# ============================================================================ THE CANDIDATES

THEORIES = {

    "T1_NAIVE_COMPRESSION": {
        "statement": "Mass is conserved in 3-space; the body simply occupies less volume.",
        "physics": "Density rises as 1/r^3. Past nuclear saturation (2.3e17 kg/m^3) degeneracy "
                   "pressure fails and the object collapses; past the Schwarzschild radius it is "
                   "inside its own horizon.",
        "patch": "Suspend degeneracy, and beyond nucleonic scale suspend general relativity.",
        "predicts": [
            "the shrunk body weighs exactly what it did (a coin-sized Ant-Man still 70 kg)",
            "he cannot be carried, thrown, or ride an insect",
            "he sinks through any floor rated below 70 kg on a 1 mm^2 footprint",
        ],
        "falsified_by": "He rides a flying ant. Attested repeatedly. T1 is DEAD on the evidence.",
        "beta_scale": "very high, and rising as 3*log2(1/r)",
    },

    "T2_MASS_SHED": {
        "statement": "Mass is not conserved; matter is destroyed or radiated on shrink and "
                     "recreated on growth.",
        "physics": "Shedding 70 kg liberates m*c^2 = 6.3e18 J -- fifteen hundred megatons, per "
                   "shrink. Growth requires the same in reverse.",
        "patch": "Suspend conservation of mass-energy.",
        "predicts": [
            "every shrink is a multi-gigaton detonation",
            "every growth demands gigatons from nowhere",
        ],
        "falsified_by": "He shrinks indoors without levelling the building. T2 is DEAD.",
        "beta_scale": "catastrophic; conservation is the most expensive law in the codebook",
    },

    "T3_BULK_EXPORT": {
        "statement": "Mass is conserved in a HIGHER-DIMENSIONAL manifold. Shrinking exports mass "
                     "into the bulk; growing imports it back. 3-space conservation is only the "
                     "shadow of a conservation law that holds in full.",
        "physics": "Braneworld and Kaluza-Klein constructions already permit matter and gravity "
                   "to have bulk degrees of freedom (Randall-Sundrum; ADD large extra "
                   "dimensions). Nothing here suspends conservation -- it enlarges the domain "
                   "over which conservation is stated.",
        "patch": "Declare a bulk and a channel to it. One structural addition to 𝔇, not a "
                 "suspension of anything already in it.",
        "predicts": [
            "shrunk mass is LOW -- he can ride an ant, be carried, be thrown",
            "GROWTH IS THE WEAPON: imported mass arrives with momentum, so a growing strike "
            "delivers energy the wielder never carried",
            "the channel is a Vector asset -- if mass can traverse the bulk, so can he",
            "the Quantum Realm is the bulk seen from inside, not a small room",
        ],
        "falsified_by": "Nothing attested. This is the surviving theory.",
        "beta_scale": "moderate and CONSTANT -- the patch is the bulk's existence, paid once, "
                      "not per metre of shrink",
    },

    "T4_CONFORMAL_RESCALE": {
        "statement": "Local rescaling of the metric; the body is unchanged and the ruler alters.",
        "physics": "Exact conformal symmetry would make size meaningless -- but mass terms break "
                   "conformal invariance explicitly, and the Standard Model is not conformal. A "
                   "local rescale must therefore also rescale every particle mass.",
        "patch": "Suspend the mass terms that break conformal symmetry -- i.e. rewrite the "
                 "Higgs sector locally.",
        "predicts": [
            "his chemistry changes with size; his neurons should not fire the same",
            "shrunk, he ought to perceive time differently by the same factor",
        ],
        "falsified_by": "He converses normally at any size. Strains T4 badly.",
        "beta_scale": "high; rewriting the mass-generation mechanism is a deep patch",
    },
}


# ==================================================== THE SURVIVOR, PRICED AND CASHED OUT

def bulk_export_beta(mass_kg, resident_mass_kg=1e-3):
    """Exception bits for T3.

    The patch is structural and paid ONCE: 'a bulk exists, and there is a channel through which
    rest mass may be moved into it.' That is a fixed addition to the codification, so beta does
    not climb with depth the way T1's does -- which is exactly why T3 survives contact with the
    evidence while T1 does not.

    Declared decomposition (Axiom M3):
      64 bits -- the existence of a bulk and its channel (a structural axiom)
      log2 of the mass ratio -- the aperture: how much rest mass the channel can pass
    """
    if resident_mass_kg <= 0 or mass_kg <= resident_mass_kg:
        return 64.0
    return round(64.0 + math.log2(mass_kg / resident_mass_kg), 2)


def growth_strike(final_mass_kg, growth_time_s, final_size_m):
    """T3's signature prediction: the energy of a GROWING strike.

    Mass arrives from the bulk and must be accelerated to the body's expanding surface velocity.
    v ~ final_size / growth_time, so KE = 1/2 m v^2. This is the honest reason a size-changer is
    dangerous -- not the punch, the *arrival*.
    """
    v = final_size_m / max(growth_time_s, 1e-6)
    ke = 0.5 * final_mass_kg * v * v
    return {"imported_mass_kg": final_mass_kg, "surface_velocity_ms": v,
            "kinetic_energy_J": ke, "tnt_kg_equivalent": ke / 4.184e6}


def penetration_pressure(mass_kg, velocity_ms, contact_area_m2, contact_time_s=1e-3):
    """Why a SMALL striker penetrates: force over a vanishing area.

    Ruin is peak deliverable structured WORK (X.2 §4) and does not change much with size -- the
    energy is what it is. Pressure does. This is a Transgression-flavoured effect wearing Ruin's
    clothes, and the axes separate them correctly.
    """
    force = (mass_kg * velocity_ms) / contact_time_s
    return {"force_N": force, "pressure_Pa": force / max(contact_area_m2, 1e-30)}


def surviving_theory():
    """Which candidate survives the attested evidence?"""
    return {name: t for name, t in THEORIES.items()
            if t["falsified_by"].startswith("Nothing attested")}
