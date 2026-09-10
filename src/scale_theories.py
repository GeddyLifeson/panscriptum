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

HELD FOR A FUTURE PHASE, MARKED, AND NOT WIRED
----------------------------------------------
Order `01695fe3ef26`; owner ruling 2026-09-08, "whole modules built and never wired in":
**wire what closes a measured gap; hold the rest, marked.** `render.py` was wired under that
ruling (`publish.py:1346`, `import render as R`). `hosts.py` WAS NOT, and this sentence used to
say it was -- measured 2026-09-08 during run #46: `import hosts`, `from hosts import`,
`hosts_for(` and `SOURCE_HOSTS` all return zero hits anywhere in src/ outside `hosts.py` itself.
Order `3fb312a72435` is still open for it and the wiring point is `feats.py`, which reads
WIKI_HOSTS.json directly for one primary host instead of asking `hosts.hosts_for(source)`.
Corrected rather than left standing, because a comment asserting a completed action that never
happened is worse than no comment: the next reader takes it as settled and stops looking. THE FOUR PRICED CODIFICATIONS IN `THEORIES` ARE HELD, and the reason is
recorded here so the next sweep re-finds a decision rather than an open question.

Nothing in `src/` imports this module. Its only mention anywhere is its own name inside
`derivation.SCAN_MODULES`, and `liveness.py` lists it as NEVER REACHED: `bulk_export_beta`,
`growth_strike`, `penetration_pressure` and `surviving_theory` all have zero callers.

Held rather than retired because `THEORIES` is AUTHORED CONTENT -- four candidate codifications
of 𝔇, each priced in exception bits and each carrying its own falsifier -- and deleting the
module would lose the authorship, not just the code. Held rather than wired because wiring it
means deciding what prices Transgression for a size-changer, which moves a published axis; that
is a phase of its own with a snapshot and a before/after table, not a maintenance edit. Nothing
is deleted.

THE FIVE PHYSICAL CONSTANTS BELOW STAY DECLARED HERE (order `a78d5cd748b2`, same ruling). They
are read by nothing -- not by the four functions, not outside this file -- and the audit that
found them proposed importing them from a canonical home instead. THERE IS NO CANONICAL HOME AND
THAT IS DELIBERATE: `chord_field.py` and `descending_ladder.py` each declare their own copies,
and `chord_field.py`'s own comment records the house precedent as the OPPOSITE of centralising
-- each file keeps only the constants it uses, because a second source of truth is the drift
hazard, not the cure for it. The owner ruled these onto that precedent. So they are not
centralised, and they are not deleted either: `descending_ladder.py` carries a comment
cross-referencing "scale_theories.py names the same value as G_NEWTON", and removing them would
silently make an existing comment false -- that cross-reference is part of how the duplication
was meant to stay VISIBLE rather than being tidied out of sight. They are reference values for
this module's own physics, marked as unread, and they wait on the same phase the functions do.
"""
import math

# REFERENCE-ONLY, HELD, NOT CENTRALISED (order a78d5cd748b2, owner ruling 2026-09-08 -- the
# chord_field precedent; see the module docstring above for why this is not a duplication to be
# fixed by importing). Each of the five occurs exactly once in this file, which is its own
# declaration, and nothing in src/ reads any of them.
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
        # `falsified` is THE SWITCH; `falsified_by` is the ARGUMENT. See surviving_theory.
        "falsified": True,
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
        "falsified": True,
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
        "falsified": False,
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
        "falsified": True,
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
    """Which candidate survives the attested evidence? -> {name: theory}, exactly one.

    SELECTED ON A FIELD, NOT ON A PROSE PREFIX (order e7dc70db782b). This read
    `t["falsified_by"].startswith("Nothing attested")`, so the module's entire output turned on
    the first two words of an English sentence written to be READ. Reword T3's argument at all --
    "No attested feat falsifies this", "Nothing on the record" -- and the function returns `{}`,
    which says "no theory survives the evidence", silently, with nothing anywhere asserting that
    exactly one should. A check that answers "no survivor" to a copy-edit is a check that cannot
    fail in the useful direction, and this module's whole product is which theory stands.

    So the switch and the argument are separate fields: `falsified` decides, `falsified_by` says
    why and is free to be edited as prose. The arity is asserted rather than assumed -- an edit
    that leaves two survivors or none RAISES instead of returning a plausible dict. Raised, not
    `assert`ed, because `python -O` strips assertions and this is the guarantee the callers of
    this module (once it has any -- see the open SWEEP34_FINDING order) will be relying on.
    """
    survivors = {name: t for name, t in THEORIES.items() if not t["falsified"]}
    if len(survivors) != 1:
        raise ValueError(
            "scale_theories: exactly one theory must survive the evidence, and %d do (%s). "
            "The candidate set was edited without re-deciding which one stands; fix the "
            "`falsified` flags in THEORIES rather than letting this return a plausible answer."
            % (len(survivors), ", ".join(sorted(survivors)) or "none"))
    return survivors
