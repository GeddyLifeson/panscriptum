#!/usr/bin/env python3
"""
THE CHORD AS A FIELD — the adjudication that lets ki and shrinking share one physics.

THE RIGHT QUESTION
------------------
Not "what is Ant-Man exempt from" -- that is local, and answering it one power at a time gives
you 215 incompatible exemptions and no omniverse. The question is:

    WHICH LAWS, THEORIES AND EXPERIMENTS MUST BE ADJUDICATED SO THAT A KI BEAM AND A
    MASS-CONSERVING SHRINK ARE BOTH LAWFUL UNDER ONE 𝔇?

Charter I.7 asserts the answer poetically -- all power is one Chord, "ki is the Chord as
amplitude discipline", and "one substrate is why one measurement applies to everyone." This file
is that assertion made adjudicable: the shared structure both phenomena require, the conservation
bookkeeping that structure forces, and the experiments that would discriminate it from its rivals.

THE UNIFYING OBSERVATION
------------------------
Run the two phenomena's requirements side by side and they are the same requirement, mirrored:

    SHRINKING (T3, the surviving theory)   rest mass leaves 3-space -> reservoir
    KI EMISSION                            energy enters 3-space   <- reservoir

Both need a RESERVOIR that holds mass-energy, and a CHANNEL with a controllable aperture. Neither
needs conservation suspended -- both need the domain over which conservation is stated to be
larger than 3-space. That is one structural addition to 𝔇 serving every power system in the
corpus, which is precisely what a substrate is supposed to do.

This is why the charter can claim one Assay measures everyone. It is not that the systems are
similar. It is that they are drawing on and discharging into the same account.
"""
import math

C_LIGHT = 2.99792458e8
G_NEWTON = 6.67430e-11
HBAR = 1.054571817e-34
K_BOLTZMANN = 1.380649e-23


# ===================================================================== THE ADJUDICATION LIST
#
# Each entry: the law at issue, what each phenomenon demands of it, what real physics already
# permits, what must be DECLARED as an extension, and the experiment that discriminates.

ADJUDICATIONS = {

    "A1_ENERGY_CONSERVATION": {
        "law": "Conservation of energy (Noether: time-translation symmetry).",
        "ki_demands": "A fighter emits 1e15-1e30 J from a body whose chemical store is ~1e8 J. "
                      "Energy must arrive from outside the body.",
        "shrink_demands": "Rest mass must go somewhere and come back, without a 1500-megaton "
                          "release (which killed theory T2).",
        "already_permitted": "Energy is NOT globally conserved in general relativity. In a "
                             "non-static spacetime there is no timelike Killing vector, so no "
                             "global conserved energy exists -- expansion redshifts photons and "
                             "the lost energy has no home. Local conservation (div T = 0) holds; "
                             "global does not. Physics already lives with this.",
        "must_declare": "A reservoir with which 3-space exchanges mass-energy, and local "
                        "conservation restated over brane + bulk rather than brane alone.",
        "experiment": "Bookkeeping: measure total mass-energy of a closed lab before and after "
                      "an emission. If the deficit is exact and repeatable, the channel is real "
                      "and its aperture is measurable. If the deficit varies with the emitter's "
                      "intent, see A5.",
        "beta_bits": 64,
    },

    "A2_MOMENTUM_CONSERVATION": {
        "law": "Conservation of momentum (Noether: space-translation symmetry).",
        "ki_demands": "THE HARDEST CONSTRAINT, and the one usually ignored. A beam carrying "
                      "energy E carries momentum >= E/c. Emitting 1e20 J directionally implies "
                      "recoil of ~3e11 kg*m/s. A 70 kg man would depart at relativistic speed. "
                      "Attested emitters do not recoil.",
        "shrink_demands": "Mass crossing the channel must not impart net momentum, or every "
                          "shrink would be a launch.",
        "already_permitted": "Nothing in 3-space. This is the single most expensive line in the "
                             "adjudication.",
        "must_declare": "The channel is momentum-symmetric: it absorbs the reaction. Equivalently "
                        "the reservoir is the recoil partner, and momentum conserves over "
                        "brane + bulk. The emitter braces against the substrate, not the ground.",
        "experiment": "Measure recoil. If a beam of energy E produces recoil << E/c, momentum is "
                      "leaving the brane, and the deficit measures the coupling directly. This "
                      "is the cleanest discriminator in the list.",
        "beta_bits": 96,
    },

    "A3_BEAM_COHERENCE": {
        "law": "Diffraction; the inverse-square law.",
        "ki_demands": "A beam that neither disperses nor falls off as 1/r^2 over kilometres. "
                      "An unguided beam of aperture a and wavelength L spreads by ~L/a radians.",
        "shrink_demands": "Nothing. Irrelevant to shrinking -- which is itself informative: the "
                          "phenomena share a reservoir, not a mechanism.",
        "already_permitted": "Self-focusing is REAL. In a nonlinear medium, intensity-dependent "
                             "refractive index (the Kerr effect) causes a beam to collapse into "
                             "a filament above a critical power. Laser filamentation in air is "
                             "routine laboratory physics.",
        "must_declare": "The substrate is a nonlinear medium with a Kerr-like response. Then a "
                        "beam above critical power self-traps -- no new law, an existing effect "
                        "in a declared medium.",
        "experiment": "Look for a power threshold. Self-focusing has a sharp critical power; "
                      "below it beams disperse normally. If weak ki disperses and strong ki "
                      "filaments, the medium is nonlinear and A3 is settled cheaply.",
        "beta_bits": 8,
    },

    "A4_THE_EQUIVALENCE_PRINCIPLE": {
        "law": "Mass-energy sources gravity (Einstein field equations).",
        "ki_demands": "Energy in transit through the channel should gravitate while present.",
        "shrink_demands": "If 70 kg leaves 3-space, the local gravitational field MUST change. "
                          "There is no way to hide mass from gravity while it is here.",
        "already_permitted": "Braneworld models (Randall-Sundrum) already have gravity leaking "
                             "into the bulk while gauge fields stay on the brane -- gravity is "
                             "the one force that is not brane-confined.",
        "must_declare": "Nothing, if the reservoir is a bulk of the RS type: exported mass "
                        "genuinely stops sourcing brane gravity because it is no longer on the "
                        "brane.",
        "experiment": "Gravimetry. A precise gravimeter beside a shrinking body should register "
                      "the mass leaving. THIS IS THE DECISIVE TEST BETWEEN T3 AND T1: naive "
                      "compression keeps the mass here and the gravimeter reads unchanged; bulk "
                      "export takes it away and the gravimeter drops.",
        "beta_bits": 0,
    },

    "A5_INTENT_COUPLING": {
        "law": "No known field couples to mental state.",
        "ki_demands": "Ki responds to will, training, and emotional state. This is not "
                      "decoration -- it is the attested control mechanism.",
        "shrink_demands": "Aperture control is deliberate; the same coupling problem, smaller.",
        "already_permitted": "Nothing in physics. THIS IS THE IRREDUCIBLE PATCH, and it should "
                             "be stated plainly rather than smuggled in with the geometry.",
        "must_declare": "A coupling between an agent's strategy selection and the channel "
                        "aperture. NOTE: the charter's own ontology already admits this class of "
                        "claim -- X.2 Axiom M2 makes an agent's beliefs and strategy choices "
                        "macrostate variables of S, and X.6 §3's Suasion axis measures influence "
                        "on other agents' choices in bits. Mind-to-macrostate coupling is "
                        "already in the codification; this extends it from other minds to the "
                        "substrate.",
        "experiment": "Double-blind aperture trials: does output correlate with intent under "
                      "conditions where the emitter cannot know the target state? If yes, the "
                      "coupling is real and its channel capacity is measurable in bits -- which "
                      "would make it an Acumen-like axis quantity rather than a mystery.",
        "beta_bits": 128,
    },

    "A6_THERMODYNAMICS": {
        "law": "Second law; entropy of the total system does not decrease.",
        "ki_demands": "Energy arriving as a coherent directed beam is LOW entropy. Extracting "
                      "ordered work from a reservoir looks like a Maxwell's demon.",
        "shrink_demands": "Reassembly on growth must restore structure exactly -- information "
                          "must be preserved across the channel.",
        "already_permitted": "Landauer's principle prices information: erasing one bit costs "
                             "kT*ln2. A demon is lawful provided it PAYS. And the reservoir may "
                             "simply be a low-entropy source, as the early universe was.",
        "must_declare": "The channel is information-preserving, and the reservoir's entropy "
                        "rises to pay for the order delivered. State the exchange rate.",
        "experiment": "Measure waste heat. Landauer sets a floor: an information-preserving "
                      "channel of capacity C has a minimum dissipation. If observed dissipation "
                      "is below the Landauer bound, the second law is genuinely violated and the "
                      "patch is far more expensive than declared.",
        "beta_bits": 32,
    },
}


def total_beta():
    """Total exception bits for the unified codification -- paid ONCE for all systems."""
    return sum(a["beta_bits"] for a in ADJUDICATIONS.values())


def per_system_beta_without_unification(n_systems):
    """What it would cost to patch each power system separately, with no shared substrate.

    This is the argument FOR the Chord stated quantitatively: MDL. A codification with one
    reservoir and one channel, reused by every system, is shorter than 215 bespoke exemptions --
    and beta is defined as a minimum DESCRIPTION LENGTH, so the shorter codification is not
    merely tidier, it is the one that scores lower on the Transgression axis.
    """
    return n_systems * total_beta()


def landauer_floor(bits, temperature_K=300.0):
    """Minimum energy to erase `bits` of information at temperature T. Joules."""
    return bits * K_BOLTZMANN * temperature_K * math.log(2)


def recoil_momentum(energy_J):
    """Momentum a directed beam of this energy MUST carry: p >= E/c."""
    return energy_J / C_LIGHT


def recoil_velocity(energy_J, emitter_mass_kg):
    """Emitter recoil velocity if momentum conserves in 3-space alone. The A2 problem, in m/s."""
    return recoil_momentum(energy_J) / emitter_mass_kg


def critical_power_self_focus(wavelength_m, n0=1.0003, n2=3e-23):
    """Kerr self-focusing critical power: P_cr = 3.77 * L^2 / (8*pi*n0*n2).

    Real laboratory physics -- the threshold above which a beam collapses into a filament instead
    of diffracting. Defaults are air. A substrate with a larger n2 has a lower threshold, which is
    exactly what A3 needs.
    """
    return (3.77 * wavelength_m ** 2) / (8.0 * math.pi * n0 * n2)
