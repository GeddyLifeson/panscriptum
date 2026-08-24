#!/usr/bin/env python3
"""
THE DERIVATION LEDGER — every quantity in the omniverse, and what it stands on.

WHY THIS FILE EXISTS
--------------------
The library's mathematics grew module by module, and each module was internally honest: it cited
its sources in prose. But prose citation does not COMPOSE. Nothing checked whether a constant
introduced in one module was already fixed by another, whether a new formula silently re-explained
something an older one covered, or whether a number had any parentage at all.

That is the failure mode with teeth. A free parameter is not merely undocumented -- under the
charter's own accounting it is EXPENSIVE. X.9 §4 prices a codification by its minimum description
length: every quantity that must be stated rather than derived is length that beta pays for. So an
undeclared constant does not just look sloppy, it raises the omniverse's Transgression score while
buying nothing. Two such parameters (a per-shelf tempo table, an invented prescience exponent)
survived review purely because nothing was checking.

WHAT A QUANTITY MAY STAND ON
----------------------------
Exactly four things, and the taxonomy is the point:

  MEASURED   a real-world value with a real citation (CODATA, a named paper). Free to use --
             reality already paid for it.
  CHARTER    fixed by owner-written charter text that predates this code. Not ours to move.
  OWNER      declared fiction under Axiom M3. LEGITIMATE but COSTED: each one is a bit of
             description length, is signed, and must state what it is anchored to, so that
             changing the anchor moves the value rather than requiring a new decree.
  DERIVED    computed from parents named here. Free -- derivation is what we are paying for.

Anything else is a violation. The checker below enforces it two ways: the declared graph must
close (no dangling parents, no rootless derivations, no cycles), and the modules' own source is
scanned for module-level constants, so a reviewer can see exactly where numbers live and catch a
new undeclared one the day it is written rather than three volumes later.
"""
import ast
import os
import sys
import silence

HERE = os.path.dirname(os.path.abspath(__file__))

MEASURED, CHARTER, OWNER, DERIVED = "MEASURED", "CHARTER", "OWNER", "DERIVED"


def Q(kind, source, parents=(), note=""):
    return {"kind": kind, "source": source, "parents": list(parents), "note": note}


# ================================================================================= THE LEDGER
LEDGER = {

    # ---------------------------------------------------------------------- measured reality
    "c":                  Q(MEASURED, "CODATA exact, 2.99792458e8 m/s"),
    "G":                  Q(MEASURED, "CODATA 6.67430e-11"),
    "hbar":               Q(MEASURED, "CODATA 1.054571817e-34"),
    "k_B":                Q(MEASURED, "CODATA exact, 1.380649e-23"),
    "planck_length":      Q(MEASURED, "CODATA 1.616255e-35 m"),
    "planck_time":        Q(MEASURED, "CODATA 5.391247e-44 s"),
    "planck_mass":        Q(MEASURED, "CODATA 2.176434e-8 kg"),
    "earth_mass":         Q(MEASURED, "IAU 5.972e24 kg"),
    "earth_radius":       Q(MEASURED, "IAU mean 6.371e6 m"),
    "sun_mass":           Q(MEASURED, "IAU 1.989e30 kg"),
    "sun_radius":         Q(MEASURED, "IAU 6.957e8 m"),
    "tnt_yield":          Q(MEASURED, "4.184e6 J/kg, definitional"),
    "nuclear_density":    Q(MEASURED, "saturation density 2.3e17 kg/m^3"),
    "seconds_per_year":   Q(MEASURED, "Julian year 3.15576e7 s"),
    "material_strengths": Q(MEASURED, "engineering fracture and vaporisation enthalpies"),
    "galaxy_count":       Q(MEASURED, "Lauer et al. 2021, New Horizons LORRI"),
    "planets_per_star":   Q(MEASURED, "Cassan et al. 2012, Nature"),
    "eta_earth":          Q(MEASURED, "Bryson et al. 2021 as upper anchor"),
    "solar_luminosity":   Q(MEASURED, "3.828e26 W"),
    "sun_binding":        Q(MEASURED, "6.9e41 J, literature value for a centrally condensed star",
                            note="deliberately MEASURED, not derived: the uniform-sphere formula "
                                 "underestimates the Sun by about 3x, and a verifier that "
                                 "'corrected' this would be wrong, not the value"),

    # ---------------------------------------------------------------------- derived physics
    "planck_energy":      Q(DERIVED, "E = m_P c^2", ["planck_mass", "c"]),
    "binding_energy":     Q(DERIVED, "U = 3GM^2/5R, uniform sphere", ["G"]),
    "schwarzschild":      Q(DERIVED, "r_s = 2GM/c^2", ["G", "c"]),
    "compton_energy":     Q(DERIVED, "E = hbar c / L", ["hbar", "c"]),
    "landauer":           Q(DERIVED, "E = k_B T ln2 per bit erased", ["k_B"]),
    "kardashev_edges":    Q(DERIVED, "Sagan continuous K = (log10 P - 6)/10",
                            ["solar_luminosity"]),

    # ---------------------------------------------------------------------- charter-fixed
    "ladder_height":      Q(CHARTER, "Part Two: 17 rungs"),
    "bands_M0_M10":       Q(CHARTER, "Part Three: eleven magnitude bands"),
    "nine_measures":      Q(CHARTER, "Part Three: the Measures"),
    "attestation_grades": Q(CHARTER, "Part Seven: Transcribed / Corroborated / Attested / Sealed"),
    "four_hands":         Q(CHARTER, "Part Seven: Quill, Moth, Avar, and the Fourth"),
    "log_scoring_rule":   Q(CHARTER, "X.2 §4: clamped decimal position in a band log window"),
    "aperture_doctrine":  Q(CHARTER, "I.9: local entries name wider flows; the reverse need not"),
    "chain_of_record":    Q(CHARTER, "Part Four: ascension marks, ratification by rung"),
    "acumen_ceiling":     Q(CHARTER, "X.6 §3: no agent extracts more prediction than the stream "
                                     "contains"),

    # ---------------------------------------------------------------------- owner declarations
    "band_edges_ruin":    Q(OWNER, "X.2 §4 band edges",
                            ["binding_energy", "sun_binding", "earth_mass", "material_strengths"],
                            note="each edge is pinned to a physical event -- crust disruption, "
                                 "Earth binding, solar binding. The ASSIGNMENT of event to band "
                                 "is the owner's; the ENERGIES are not"),
    "years_per_unit_distance": Q(OWNER, "X.7: 1000 yr per unit shared-stage distance",
                                 note="one declared conversion, and the omniverse's only clock"),
    "rung_cost_exponent": Q(OWNER, "X.7: ascension cost exponent 1.35",
                            ["chain_of_record"],
                            note="superlinear because each rung needs more signatories than the "
                                 "last -- the exponent is declared, the superlinearity is not"),
    "f_life":             Q(OWNER, "X.7 census: habitable worlds that bear life"),
    "f_complex":          Q(OWNER, "X.7 census: life-bearing worlds reaching complex life"),
    "f_civilization":     Q(OWNER, "X.7 census: complex-life worlds reaching civilization"),
    "f_survives":         Q(OWNER, "X.7 census: civilizations extant rather than fallen"),
    "beta_constants":     Q(OWNER, "X.9: the six adjudication costs, 8 to 128 bits",
                            note="ordinal spacing is argued in X.9 §3 from how much of the record "
                                 "each patched law touches; the absolute scale is declared"),
    "currency_rates":     Q(OWNER, "X.12: local mints, each with a purchasing-power anchor",
                            ["joules_per_standard"],
                            note="rates are fiction, ANCHORS are the honest part -- move an "
                                 "anchor and the rate moves with it"),

    # ------------------------------------------------------------------ derived charter math
    "joules_per_standard": Q(DERIVED, "1 Standard = energy to pulverise 1 m^3 of rock",
                             ["material_strengths"],
                             note="NOT a new constant: reuses the feat ladder's own figure, so a "
                                  "currency unit and a combat feat are denominated identically"),
    "eta_consistency":    Q(DERIVED, "HodgeRank gradient share of pairwise flow",
                            ["log_scoring_rule"]),
    "curl_fraction":      Q(DERIVED, "1 - eta", ["eta_consistency"]),
    "theorem_2_floor":    Q(DERIVED, "scalarization error floor equals the curl fraction",
                            ["curl_fraction"]),
    "hand_interval":      Q(DERIVED, "the +/- band is the spread of the Hands' priors",
                            ["four_hands", "attestation_grades"],
                            note="Vol 0.5 Thm 4: Quill/Moth/Avar divergence IS the interval"),
    "ascension_years":    Q(DERIVED, "r^1.35 - 1", ["rung_cost_exponent", "ladder_height"]),
    "arrival_years":      Q(DERIVED, "1000 * d", ["years_per_unit_distance"]),
    "apparent_lag":       Q(DERIVED, "identical to arrival_years -- NOT a second mechanism",
                            ["arrival_years"],
                            note="the tempo-ratio table this replaced was a second explanation "
                                 "for an observation propagation already covered"),
    "observed_mark":      Q(DERIVED, "ascension clock gated by the arrival clock",
                            ["ascension_years", "arrival_years"]),
    "civ_census":         Q(DERIVED, "galaxies x stars x planets x eta x the f-chain",
                            ["galaxy_count", "planets_per_star", "eta_earth", "f_life",
                             "f_complex", "f_civilization", "f_survives"]),
    "transgression_beta": Q(DERIVED, "MDL exception bits: degeneracy plus horizon violation",
                            ["beta_constants", "schwarzschild", "nuclear_density"]),
    "rung_description_length": Q(DERIVED, "L_r = log2(ruin_edge(r) / ruin_edge(M0))",
                                 ["band_edges_ruin"],
                                 note="the fix for an invented 2^(rung-1): reads the SAME band "
                                      "edges as information rather than as energy"),
    "prescience_bits":    Q(DERIVED, "L_r * lead_years, capped by attested Acumen",
                            ["rung_description_length", "acumen_ceiling"]),
    "retrocausality_beta": Q(DERIVED, "structural constant + log2(1 + span)", ["beta_constants"]),
    "institutional_simultaneity": Q(DERIVED, "contemporaneity is equal position in the Chain",
                                    ["chain_of_record"]),
    "loop_unaccessionable": Q(DERIVED, "ascension needs reference time; a closed loop spends none",
                              ["institutional_simultaneity", "ascension_years"]),
    "assay_to_standards": Q(DERIVED, "band log-window position, priced in Standards",
                            ["band_edges_ruin", "joules_per_standard", "log_scoring_rule"]),
    # ------------------------------------------------------- commensuration (rigor.py, X.11)
    "saaty_RI":           Q(MEASURED, "Saaty's random consistency index, tabulated from "
                                      "simulations of random reciprocal matrices"),
    "law_catalogue":      Q(MEASURED, "the enumerated conserved quantities and structural "
                                      "principles of established physics (Noether + CPT, "
                                      "Lorentz, causality, 2nd law, unitarity, equivalence)"),
    "pareto_tail_index":  Q(OWNER, "alpha = 1 (Zipf) as the neutral default for magnitude tails",
                            note="exposed as a parameter, not buried; Gutenberg-Richter and "
                                 "Richardson's war statistics put real-world alpha near 1-1.7, "
                                 "and a larger alpha gives a SMALLER correction, so the default "
                                 "is the conservative end"),
    "commensuration_unit": Q(DERIVED, "every Measure is scored in bits: L_r/10 per axis point",
                             ["rung_description_length", "acumen_ceiling"],
                             note="Ruin's joules and Acumen's bits were always one unit; this "
                                  "is what lets Int/Wis/Cha be set against Str/Dex/Con"),
    "parity_rate":        Q(DERIVED, "exchange rate k = 1 between axes, by minimum description "
                                     "length", ["commensuration_unit", "beta_constants"],
                            note="k != 1 is a free parameter; k = 1 is the unique zero-parameter "
                                 "choice. Rules out the k = 0 currently in force"),
    # WEIGHTS COME FROM THE GEOMETRIC MEAN, NOT THE EIGENVECTOR.
    #
    # Saaty's principal eigenvector was the ledger's primary estimator and should not have been.
    # Crawford & Williams (1985) show the row geometric mean is the MAXIMUM-LIKELIHOOD estimator
    # under multiplicative judgment error, which is the error model a reciprocal ratio matrix
    # actually has, and unlike the eigenvector it cannot rank-reverse.
    #
    # Measured here over 200 simulated eleven-axis matrices, the two are identical on consistent
    # judgments and separate as inconsistency grows -- logrank beats Perron by 0.7% of L1 error
    # at CR=0.011, by 3.2% at CR=0.057, and by 8.9% at CR=0.202. They provably coincide at n=3,
    # which is why a small worked example never shows the difference.
    #
    # Perron keeps the job it is genuinely best at: lambda_max is what Saaty's consistency ratio
    # is defined from, and CR remains the published coherence bar.
    "logrank_weights":    Q(DERIVED, "row geometric mean of a reciprocal ratio matrix; the ML "
                                     "estimator under multiplicative error (Crawford & Williams "
                                     "1985), and rank-reversal-free",
                            ["saaty_RI"],
                            note="PRIMARY estimator for axis weights"),
    "perron_weights":     Q(DERIVED, "principal eigenvector of a reciprocal ratio matrix",
                            ["saaty_RI"],
                            note="retained for lambda_max, from which CR is defined; no longer "
                                 "the primary weight estimator"),
    "consistency_ratio":  Q(DERIVED, "CR = ((lambda_max - n)/(n-1)) / RI", ["perron_weights",
                                                                            "saaty_RI"]),
    "theorem_1":          Q(DERIVED, "ratio-matrix consistency <=> curl-freeness of its log-flow",
                            ["consistency_ratio", "curl_fraction"],
                            note="CR and the curl fraction co-vanish and co-increase; they are "
                                 "NOT equal. Saaty 1977; Crawford & Williams 1985; Jiang, Lim, "
                                 "Yao & Ye 2011"),
    "bradley_terry":      Q(DERIVED, "MM-algorithm MLE for pairwise contest strengths",
                            ["log_scoring_rule"],
                            note="the third face of the same operation; Hunter 2004"),
    "mdl_floor":          Q(DERIVED, "log2 C(M,k) + log2 R + p*precision",
                            ["law_catalogue", "beta_constants"],
                            note="gives every declared beta an auditable lower bound; all five "
                                 "charter costs sit above their floor at a ratio near 3"),
    "census_interval":    Q(DERIVED, "log-normal propagation; log-variances add in quadrature",
                            ["civ_census"],
                            note="a product of log-uncertain factors has no meaningful point "
                                 "estimate, only a credible interval"),
    "jensen_correction":  Q(DERIVED, "E[1-exp(-N)] integrated over the uncertainty, not "
                                     "evaluated at E[N]", ["census_interval"],
                            note="Sandberg, Drexler & Ord 2018; the concavity gap is where the "
                                 "Fermi paradox was manufactured"),
    "evt_ceiling":        Q(DERIVED, "sample max is biased low; correction log2(N/n)/alpha",
                            ["pareto_tail_index"],
                            note="why phase 1 emits a band and refuses a decimal"),
    "math_resonance":     Q(DERIVED, "density, orphan rate and depth of this very ledger",
                            ["theorem_1", "commensuration_unit"],
                            note="the mathematics scored by the measure it applies to everything "
                                 "else -- Vol 0.5's ontology turned on its own instrument"),

    # ------------------------------------------------- the college of Custodes (custodes.py)
    "assay_dof":          Q(DERIVED, "the independent levers in the assay computation: ten "
                                     "survive the test that varying one alone moves the output "
                                     "and is not a function of the others",
                            ["log_scoring_rule", "attestation_grades", "aperture_doctrine",
                             "arrival_years", "chain_of_record", "parity_rate",
                             "curl_fraction", "transgression_beta", "evt_ceiling"]),
    "college_size":       Q(DERIVED, "one Custos per degree of freedom", ["assay_dof"],
                            note="the count is derived, not chosen: a direction with nobody "
                                 "standing in it is a direction nobody checks"),
    "custos_dasein":      Q(DERIVED, "each standpoint's native mode of disclosure fixes what "
                                     "counts as evidence before any weighing",
                            ["college_size", "four_hands"],
                            note="the STRUCTURE is derived -- which standpoints must exist, and "
                                 "why exactly ten. Their magnitudes are not; see custos_tilts"),
    "custos_tilts":       Q(OWNER, "each Custos's tilt, evidence-sensitivity and axis emphasis "
                                   "(about thirty declared numbers, custodes.py CUSTODES)",
                            ["custos_dasein"],
                            note="THE LARGEST BLOCK OF FREE PARAMETERS IN THE LIBRARY, and it is "
                                 "filed honestly rather than dressed as derivation. What is "
                                 "derived is that ten standpoints must exist and which degrees "
                                 "of freedom they occupy; how far each leans is a "
                                 "characterisation of a person, which is fiction under Axiom M3. "
                                 "The anchor that keeps it from being arbitrary: the three "
                                 "charter Hands' tilts are calibrated to reproduce the charter's "
                                 "own published Kenshiro reading (M3.52 ± 0.12) to within 0.05 "
                                 "and 0.03, which is a target they did not get to choose. The "
                                 "seven new tilts have no such anchor and should be treated as "
                                 "the softest numbers here. Lumen's was REMOVED entirely -- see "
                                 "staleness_widening -- so the block is one smaller than it was"),
    "attestation_quality": Q(DERIVED, "quality(g) = 1 - base(g)/max(base), from assay()'s own "
                                      "attestation table", ["attestation_grades"],
                             note="was a second hand-written table; a duplicate mechanism for a "
                                  "quantity the charter had already fixed, and it would have "
                                  "drifted the moment either copy was edited"),
    "curl_veto_threshold": Q(DERIVED, "curl < 0.10, being Saaty's CR bar carried across by "
                                      "Theorem 1", ["theorem_1", "saaty_RI"],
                             note="a draft used 0.85, chosen to feel lenient; the established "
                                  "convention was available and costs nothing"),
    "staleness_widening": Q(DERIVED, "unobserved share of the Chain x half a band",
                            ["observed_mark", "ladder_height"],
                            note="replaces Lumen's -0.04 tilt, which asserted distant beings are "
                                 "WEAKER. Distance diminishes what is known of a being, not the "
                                 "being. Ignorance is dispersion, not direction. The 0.5 is "
                                 "forced by a band having width 1, so it is not a tunable"),
    "interval_as_spread": Q(DERIVED, "the ± is the measured dispersion of the college's readings",
                            ["custos_tilts", "hand_interval"],
                            note="replaces a hardcoded attestation lookup table; Vol 0.5 Thm 4"),
    "prior_vs_floor":     Q(DERIVED, "variance surviving perfect evidence / variance removable "
                                     "by fieldwork", ["interval_as_spread"],
                            note="why Goku's ± will never narrow and Kenshiro's will"),
    "threnody_veto":      Q(DERIVED, "refusal of a scalar where the curl fraction is large",
                            ["curl_fraction", "college_size"],
                            note="the one standpoint that can deny the output rather than move it"),
    "faculty_parity":     Q(DERIVED, "each faculty at 1/11; physical block at 8/11 with charter "
                                     "proportions intact",
                            ["parity_rate", "nine_measures"],
                            note="ERRATUM: was 0.0. Leaves every physical-only decimal unchanged "
                                 "because the composite renormalises over scored axes"),
    "applicability_mark": Q(DERIVED, "INAPPLICABLE excluded from the coverage denominator",
                            ["faculty_parity", "attestation_grades"],
                            note="an absent axis is knowledge; only an unscored one is ignorance"),

    # ---------------------------------------------------- the weave and the onomasticon
    "name_surprisal":     Q(DERIVED, "token-level improbability of a name, in bits",
                            ["log_scoring_rule"],
                            note="source-idf welded Cowboy Bebop to Thomas the Tank Engine "
                                 "through Gordon and Edward; surprisal separates genuine sharing "
                                 "from coincidence at 38:1"),
    "continuity_group":   Q(DERIVED, "complete-linkage clusters over surprisal-weighted pairs",
                            ["name_surprisal"],
                            note="connected components CHAINED, fusing 95 sources into one "
                                 "continuity and resolving Earth across 24 universes"),
    "resonance_graph":    Q(DERIVED, "permissive shelf-relatedness; distinct from identity",
                            ["name_surprisal"],
                            note="the graph X.7 propagation must read from. Diameter 5, mean "
                                 "path 2.04 hops"),
    "six_degrees":        Q(DERIVED, "measured diameter of the resonance graph",
                            ["resonance_graph"],
                            note="holds at 5, and the omniverse is 93.8% connected"),
    "hyperverse_bound":   Q(DERIVED, "max top-level divisions keeping diameter <= 6",
                            ["six_degrees"],
                            note="MEASURED, not declared: at 6 divisions the diameter is 6; at 8 "
                                 "it is 8. Seven is the ceiling, which is what the owner "
                                 "reasoned from the path topology before it was computed"),
    "carried_names":      Q(DERIVED, "an endonym of descent, not a designation of identity",
                            ["continuity_group"],
                            note="thirty peoples with no contact call their world Earth because "
                                 "their founding tradition says they came from it -- New "
                                 "Amsterdam, not a coincidence and not an identity"),
    "world_designation":  Q(DERIVED, "deterministic name from catalogue position + register",
                            ["carried_names"],
                            note="reproducible by construction, so the Moth test applies to "
                                 "naming as much as to arithmetic"),

    # -------------------------------------------------- the address space (address_space.py)
    "address_widths":     Q(DERIVED, "bits per field, each sized to its own census population",
                            ["hyperverse_bound", "galaxy_count", "planets_per_star",
                             "continuity_group"],
                            note="74 bits total. Change the census and the widths follow; nothing "
                                 "here is a round number chosen because it looked tidy"),
    "shelfmark":          Q(DERIVED, "the charter's Omega-address, with the question marks filled",
                            ["address_widths"],
                            note="Part Two's Shelfmark has emitted a placeholder since the "
                                 "beginning because the classification research did not exist; "
                                 "this is that research done as arithmetic"),
    "map_seed":           Q(DERIVED, "32-bit generator seed hashed FROM the address",
                            ["shelfmark"],
                            note="the join between an interpretable position and an "
                                 "uninterpretable terrain: give a Custos the address and the map "
                                 "regenerates identically, with nothing stored"),
    "world_features":     Q(DERIVED, "landform, climate, condition and era read from the entry, "
                                     "with unattested axes seeded and TAGGED",
                            ["map_seed"],
                            note="only 29.9% of map axes are attested by the source text; "
                                 "defaulting the rest made 200 worlds share one option vector "
                                 "and asserted 'temperate' as though a source had said it"),
    "attested_coverage":  Q(DERIVED, "worlds written down / worlds the census says exist",
                            ["civ_census", "address_widths"],
                            note="5.15e-17. One world named per 1.9e16 that exist -- the same "
                                 "finding as the Canon of the Now, in a different currency"),

    "source_genre":       Q(DERIVED, "weighted vocabulary profile over a source's own entries",
                            ["name_surprisal"],
                            note="replaces a HASH of the continuity id, which had given Alien and "
                                 "Doom the flowing elvish register and denied Greek myth the "
                                 "classical one"),
    "genre_priors":       Q(DERIVED, "the urn an unattested world axis draws from",
                            ["source_genre", "world_features"],
                            note="a post-apocalyptic source should not seed a thriving world"),
    "world_profile":      Q(DERIVED, "address + genre + features + band + attestation, one string",
                            ["shelfmark", "source_genre", "world_features", "attested_coverage"],
                            note="29 characters. Traveller's UWP proved the pattern in 1977: a "
                                 "name with structure can be handed over, sorted and checked, and "
                                 "a paragraph cannot. The attestation digit is the field a "
                                 "compression scheme drops first and the one that must survive"),

    "regress_test_axes":  Q(CHARTER, "Omega Band: does the claimant's own account grant it a "
                                     "before, a stage, or a state space?"),
    "grounding_type":     Q(DERIVED, "which answer a cosmos gives to the First Argument",
                            ["regress_test_axes"],
                            note="THE HYPERVERSE. The Omega Band's regress test promoted from "
                                 "claimants to cosmoi: ex nihilo, emanation, eternal cycle, "
                                 "demiurgic, immanent, or ungrounded. Subsumes the pantheon pass "
                                 "-- a pantheon IS a grounding claim -- and covers the godless "
                                 "fictions, because 'the regress runs on' is itself a type"),

    "sevenfold_span":     Q(OWNER, "seven hyperverses; one to seven children at every tier below",
                            note="AUTHORIAL DECLARATION under Axiom M3, after four attempts to "
                                 "DISCOVER the upper tiers failed on the same rock: similarity is "
                                 "lumpy. Every measure produced one giant mass and a tail, and a "
                                 "shelving system built on similarity inherits the lumps. Seven "
                                 "is a BOUND, not a quota -- a hyperverse holding one xenoverse "
                                 "is not defective"),
    "shelf_placement":    Q(DERIVED, "cuts fall at the weakest seams of the affinity ordering",
                            ["sevenfold_span", "name_surprisal"],
                            note="the shape is declared and the placement is measured; Alien and "
                                 "Predator share all three source tiers because the resonance "
                                 "says so, not because anyone put them there"),

    "rank_size_rule":     Q(MEASURED, "Auerbach 1913, Zipf 1949: the k-th largest settlement "
                                      "holds P1/k^q, with q near 1 across an enormous range of "
                                      "real regions and periods"),
    "burg_population":    Q(DERIVED, "P_k = P_1 / k^q", ["rank_size_rule", "world_features"],
                            note="the settlement-scale instance of the heavy-tail family the "
                                 "Assay already carries -- Gutenberg-Richter, Richardson"),
    "burg_count":         Q(DERIVED, "n = P_1 / P_min: the ranking runs until a settlement stops "
                                     "being a burg", ["burg_population"],
                            note="derived FROM the law rather than chosen alongside it. Picking a "
                                 "count near forty gave 39% cities and no hamlets -- an inverted "
                                 "pyramid, because the ranking stopped before it reached the "
                                 "small settlements"),
    "burg_seed":          Q(DERIVED, "hashed from the world seed and the burg's rank",
                            ["burg_count", "map_seed"],
                            note="the bottom of the hierarchy: galaxy -> planet -> burg, each "
                                 "seeded from the level above and nothing stored"),

    "thread_class":       Q(DERIVED, "reciprocal / lawful-asymmetric / suspect",
                            ["aperture_doctrine", "arrival_years"],
                            note="both excuses for one-way threads are themselves ledger entries, "
                                 "which is why a 'hole' is a finding and not an opinion"),
}


# ========================================================================= GRAPH INTEGRITY
def check_graph():
    problems = []
    for name, q in LEDGER.items():
        for p in q["parents"]:
            if p not in LEDGER:
                problems.append(f"DANGLING  {name} -> {p} (parent not on the ledger)")
        if q["kind"] == DERIVED and not q["parents"]:
            problems.append(f"ROOTLESS  {name} is DERIVED but names no parents")
        if q["kind"] == OWNER and not q["source"]:
            problems.append(f"UNSIGNED  {name} is an owner declaration with no citation")

    state = {}

    def visit(n, stack):
        if state.get(n) == "done":
            return
        if state.get(n) == "open":
            problems.append(f"CYCLE     {' -> '.join(stack + [n])}")
            return
        state[n] = "open"
        for p in LEDGER[n]["parents"]:
            if p in LEDGER:
                visit(p, stack + [n])
        state[n] = "done"

    for n in list(LEDGER):
        visit(n, [])
    return problems


def depth(name, seen=None):
    """How far a quantity sits from bare reality. Deep is GOOD -- it means derived, not decreed."""
    seen = seen or set()
    if name in seen or name not in LEDGER:
        return 0
    seen = seen | {name}
    ps = [p for p in LEDGER[name]["parents"] if p in LEDGER]
    return 0 if not ps else 1 + max(depth(p, seen) for p in ps)


def provenance(name):
    """The full citation chain for one quantity -- what a Hand would need to recompute it."""
    if name not in LEDGER:
        return None
    out, stack, seen = [], [name], set()
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        q = LEDGER[n]
        out.append((n, q["kind"], q["source"]))
        stack.extend(p for p in q["parents"] if p in LEDGER)
    return out


# ============================================== MODULE-LEVEL CONSTANT SCAN (where numbers live)
SCAN_MODULES = ["assay", "feats", "cosmography", "propagation", "descending_ladder",
                "scale_theories", "chord_field", "resonance", "tempus", "ledger", "rigor", "custodes", "weave", "onomast", "worldseed", "address_space", "genre", "profile", "tiers", "grounding", "sevenfold", "burgs"]


def scan_constants(mod):
    """Module-level UPPERCASE assignments -- the only place a new constant can hide."""
    path = os.path.join(HERE, mod + ".py")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        src = f.read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        silence.note("derivation.py:scan_constants-parse")
        return None
    names = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            nm = getattr(node.targets[0], "id", None)
            if nm and nm.isupper():
                lits = sum(1 for s in ast.walk(node.value)
                           if isinstance(s, ast.Constant) and isinstance(s.value, (int, float)))
                names.append((nm, lits))
    return names


def main():
    print("=" * 96)
    print("THE DERIVATION LEDGER — does the omniverse's mathematics close?")
    print("=" * 96)
    print()

    kinds = {}
    for q in LEDGER.values():
        kinds[q["kind"]] = kinds.get(q["kind"], 0) + 1
    total = len(LEDGER)
    print(f"quantities on the ledger : {total}")
    for k in (MEASURED, CHARTER, OWNER, DERIVED):
        n = kinds.get(k, 0)
        print(f"    {k:9s} {n:3d}   ({n/total:5.1%})")
    print()
    print(f"  DERIVED SHARE   {kinds.get(DERIVED,0)/total:6.1%}   "
          f"the share of the mathematics that costs no description length")
    print(f"  FREE PARAMETERS {kinds.get(OWNER,0):6d}   "
          f"owner declarations, each signed and anchored")
    print()

    problems = check_graph()
    if problems:
        print("GRAPH FAILURES")
        for p in problems:
            print("   " + p)
    else:
        print("  graph closes — no dangling parents, no rootless derivations, no cycles")
    print()

    print("deepest derivation chains (distance from bare reality):")
    for n in sorted(LEDGER, key=lambda x: -depth(x))[:6]:
        chain, cur = [], n
        while [p for p in LEDGER[cur]["parents"] if p in LEDGER]:
            chain.append(cur)
            cur = max((p for p in LEDGER[cur]["parents"] if p in LEDGER), key=depth)
        chain.append(cur)
        print(f"   {depth(n)}  {' <- '.join(chain)}")
    print()

    print("where constants live (a reviewer's map, not a verdict):")
    for m in SCAN_MODULES:
        cs = scan_constants(m)
        if cs is None:
            print(f"   {m:20s} (absent)")
        elif cs:
            print(f"   {m:20s} {len(cs):2d} constants, {sum(c[1] for c in cs):4d} literals")
    print()
    print("=" * 96)
    print("VERDICT: " + ("LEDGER CLOSES" if not problems else f"{len(problems)} FAILURES"))
    print("=" * 96)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
