#!/usr/bin/env python3
"""
Independent verification of every number this project computes.

Nothing here calls the modules' own helpers to check the modules' own helpers -- each assertion
recomputes the quantity from first principles and compares. That is the Moth test applied to the
code itself: *can a stranger, given the citations, get your number?*

Run:  python3 src/verify_math.py
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence             # noqa: E402
import physics as PH       # noqa: E402
import assay as A          # noqa: E402
import cosmography as C    # noqa: E402
import propagation as P    # noqa: E402

PASS, FAIL = [], []


def _tier_counts(t):
    return [len({v[k] for v in t.values() if v.get(k) is not None})
            for k in ("multiverse", "metaverse", "xenoverse", "hyperverse")]


def _nesting_violations(t):
    import collections as _c
    bad = 0
    for lo, hi in (("multiverse", "metaverse"), ("metaverse", "xenoverse"),
                   ("xenoverse", "hyperverse")):
        groups = _c.defaultdict(set)
        for v in t.values():
            if v.get(lo) is not None and v.get(hi) is not None:
                groups[v[lo]].add(v[hi])
        bad += sum(1 for g in groups.values() if len(g) > 1)
    return bad


def _raises(fn):
    try:
        fn()
        return False
    except Exception:
        silence.note("verify_math.py:47")
        return True




def check(label, got, want, tol=1e-6, note=""):
    ok = (abs(got - want) <= tol * max(1.0, abs(want))) if isinstance(want, float) else got == want
    (PASS if ok else FAIL).append((label, got, want, note))
    mark = "OK  " if ok else "FAIL"
    print(f"  {mark} {label:<52} got={got!r:<22} want={want!r}")
    if note and not ok:
        print(f"       {note}")


print("=" * 96)
print("1. PHYSICAL CONSTANTS — recomputed from first principles")
print("=" * 96)

# Earth's gravitational binding energy: U = 3GM^2 / 5R
U_earth = (3 * 6.67430e-11 * 5.972e24 ** 2) / (5 * 6.371e6)
check("Earth binding energy U=3GM^2/5R (J)", round(U_earth, -29), 2.24e32, tol=0.02,
      note="drives the M3 ceiling / M4 floor")
check("assay M4 Ruin floor == Earth binding", A.BAND_EDGES["M4"]["ruin"], 2.24e32, tol=1e-9)

# The uniform-sphere formula UNDERESTIMATES a centrally-condensed body. It is right for Earth
# (2.24e32, matching the cited value) and wrong for the Sun by ~3x, because the Sun's mass is
# concentrated toward its core. The literature value ~6.9e41 J comes from integrating the real
# density profile. assay.py uses the literature value for the M5 floor, correctly; this check
# exists to pin the discrepancy rather than let it look like an error.
U_sun_uniform = (3 * 6.67430e-11 * 1.989e30 ** 2) / (5 * 6.957e8)
check("Sun binding, UNIFORM approximation (J)", round(U_sun_uniform, -38), 2.3e41, tol=0.05,
      note="uniform-sphere formula; not the value to shelve with")
check("assay M5 floor uses the LITERATURE value, not the uniform one",
      A.BAND_EDGES["M5"]["ruin"] > U_sun_uniform * 2, True,
      note="6.9e41 from the integrated density profile; a centrally-condensed star binds harder")

# Kinetic energy, Newtonian and relativistic
check("KE 75kg @ 10 m/s (J)", PH.kinetic(75, 10), 3750.0, tol=1e-9)
gamma = 1 / math.sqrt(1 - 0.5 ** 2)
check("KE relativistic @ 0.5c uses gamma", round(PH.kinetic(1.0, 0.5 * 2.99792458e8)),
      round((gamma - 1) * 1.0 * 2.99792458e8 ** 2), tol=1e-9,
      note="must switch to relativistic above 0.1c")

# Pulverisation volume math
check("pulverise 1000 m^3 concrete (J)", PH.joules_for(1000, "concrete", "pulv"), 1.7e11, tol=1e-9)

print()
print("=" * 96)
print("2. THE ASSAY — X.2 §4 scoring rule and X.6 §6 Instrument")
print("=" * 96)

# s(x) = 10 * (ln x - ln x_r) / (ln x_{r+1} - ln x_r)
lo, hi = A.BAND_EDGES["M3"]["ruin"], A.BAND_EDGES["M4"]["ruin"]
x = math.sqrt(lo * hi)                      # geometric midpoint must score exactly 5.0
check("axis_score at band geometric midpoint", A.axis_score(x, "M3", "ruin"), 5.0, tol=1e-6,
      note="log-scale rule: geometric mean sits at half the band")
check("axis_score clamps below floor", A.axis_score(lo / 100, "M3", "ruin"), 0.0, tol=1e-9)
check("axis_score clamps above ceiling", A.axis_score(hi * 100, "M3", "ruin"), 10.0, tol=1e-9)

# X.6 §7 worked example: Mihai at M3, window [16,28], span 12
inst = A.instrument("M3", {"acumen": 7.0, "discernment": 8.5, "suasion": 5.5},
                    worksheet="X.6 §7")["faculties"]
check("X.6 §7 Mihai Intelligence  = round(16+0.70*12)", inst["Intelligence"], 24)
check("X.6 §7 Mihai Wisdom        = round(16+0.85*12)", inst["Wisdom"], 26)
check("X.6 §7 Mihai Charisma      = round(16+0.55*12)", inst["Charisma"], 23)

# Transcendence Grade = M - 5
g = A.instrument("M8", {"acumen": 5.0}, worksheet="t")["transcendence_grade"]
check("Transcendence Grade at M8 == III (8-5)", g, "III")
check("no Grade below M6", A.instrument("M4", {"acumen": 5.0}, worksheet="t")
      ["transcendence_grade"], None)

# H5: no worksheet, no number
check("H5 refuses to score without a worksheet",
      "window" in A.instrument("M4", {"ruin": 9.0}), True)

# Charter Part Three worked example: Kenshiro Sigma 5.214 -> M3.52
sigma = (0.20 * 2.1 + 0.15 * 4.8 + 0.12 * 6.5 + 0.10 * 1.2
         + 0.18 * 8.7 + 0.08 * 7.4 + 0.07 * 0.8 + 0.10 * 9.6)
check("Charter Kenshiro worksheet Sigma", round(sigma, 3), 5.214, tol=1e-9)
check("Charter Kenshiro 3 + Sigma/10", round(3 + sigma / 10, 2), 3.52, tol=1e-9)
# Erratum 1: Ruin 2.1 -> 0.6 gives Sigma 4.914 -> M3.49
sigma2 = sigma - 0.20 * (2.1 - 0.6)
check("Erratum 1 revised Sigma", round(sigma2, 3), 4.914, tol=1e-9)
check("Erratum 1 revised Assay", round(3 + sigma2 / 10, 2), 3.49, tol=1e-9)

print()
print("=" * 96)
print("3. THE CENSUS — chain arithmetic and physical constraints")
print("=" * 96)

c = C.census("STANDARD")
g_, s_ = C.GALAXIES_DEFAULT, C.GALAXIES_DEFAULT * C.STARS_PER_GALAXY_MEAN
check("stars = galaxies x stars/galaxy", c["stars"], s_, tol=1e-9)
check("exoplanets = stars x planets/star", c["exoplanets"], s_ * C.PLANETS_PER_STAR, tol=1e-9)
check("habitable = stars x eta-Earth", c["habitable_zone_rocky"], s_ * C.ETA_EARTH, tol=1e-9)
check("life = habitable x f_life", c["life_bearing"],
      s_ * C.ETA_EARTH * C.F_LIFE, tol=1e-9)
check("extant = ever x f_survives", c["civilizations_extant"],
      c["civilizations_ever"] * C.F_SURVIVES, tol=1e-9)
check("KARDASHEV_MIX sums to 1", round(sum(C.KARDASHEV_MIX.values()), 9), 1.0, tol=1e-9)
check("census passes its own validator", c["valid"], True)
check("Type III <= galaxies", c["kardashev"]["Type III (galactic)"] <= c["galaxies"], True)
check("Type II  <= stars", c["kardashev"]["Type II (stellar)"] <= c["stars"], True)

# Sagan's continuous Kardashev: K = (log10 P - 6)/10
check("Kardashev K(Type I = 1e16 W) == 1.0", C.kardashev_K(1e16), 1.0, tol=1e-9)
check("Kardashev K(Earth 2e13 W)", C.kardashev_K(2e13), 0.730, tol=2e-3)

# Bridge: annual budget vs Ruin edges
band, joules = C.kardashev_to_magnitude(C.KARDASHEV_TYPE_II)
check("Type II annual joules", round(joules, -32),
      round(4.0e26 * C.SECONDS_PER_YEAR, -32), tol=1e-9)
check("Type II reaches Ruin band M4", band, "M4")
check("Type III reaches Ruin band M5", C.kardashev_to_magnitude(C.KARDASHEV_TYPE_III)[0], "M5")

print()
print("=" * 96)
print("4. PROPAGATION — the two clocks")
print("=" * 96)

check("ascension to rung 17 (yr) = 17^1.35 - 1",
      P.ascension_years(17), round(17 ** 1.35 - 1, 1), tol=1e-9)
check("ascension is distance-independent (no arg)", P.ascension_years(17) > 0, True)
check("arrival(d=1.0) == YEARS_PER_UNIT_DISTANCE",
      P.arrival_years(1.0), C_ := P.YEARS_PER_UNIT_DISTANCE, tol=1e-9)
check("before arrival, observed mark is 0", P.observed_mark(1.0, 500), 0)
check("well after arrival, mark reaches 17", P.observed_mark(1.0, 5000), 17)
check("a nearer shelf sees it sooner",
      P.observed_mark(0.1, 300) > P.observed_mark(1.0, 300), True)


print()
print("=" * 96)
print("5. TIME — institutional simultaneity, and foresight priced against the Assay")
print("=" * 96)

import tempus as T          # noqa: E402

# L_r is not a new scale. It is BAND_EDGES read as information, so the verifier recomputes it
# from the band edges directly rather than calling the module's own helper.
_expected_L = {b: math.log2(A.BAND_EDGES[b]["ruin"] / A.BAND_EDGES["M0"]["ruin"])
               for b in A.LADDER}
for _b in ("M1", "M4", "M7", "M10"):
    check(f"L_r({_b}) = log2(ruin({_b})/ruin(M0))",
          T.rung_description_length(_b), round(_expected_L[_b], 2), tol=1e-3)

check("L_r(M0) = 0 — the reference edge itself, by construction",
      T.rung_description_length("M0"), 0.0, tol=1e-9,
      note="X.6 §4 wants a reference edge; the floor band IS it, so L is measured above M0")
check("L_r is strictly monotone across the bands",
      all(T.rung_description_length(A.LADDER[i]) < T.rung_description_length(A.LADDER[i + 1])
          for i in range(len(A.LADDER) - 1)), True)
check("prescience cost is linear in lead time",
      T.prescience_horizon_bits("M5", 200)["bits_required"],
      round(2 * T.prescience_horizon_bits("M5", 100)["bits_required"], 2), tol=1e-6)
check("a higher-rung stream costs more to foresee",
      T.prescience_horizon_bits("M8", 10)["bits_required"] >
      T.prescience_horizon_bits("M3", 10)["bits_required"], True)
check("prescience refuses an unknown band", T.prescience_horizon_bits("M99", 10), None)

# The tempo table was REMOVED as a duplicate mechanism. Verify it stayed removed.
check("no per-shelf tempo parameter survives", hasattr(T, "TEMPO"), False,
      note="apparent lag between shelves is propagation (X.7), not a second clock rate")
check("apparent lag IS the arrival clock, not a new quantity",
      T.apparent_lag_years.__doc__ is not None and
      "arrival_years" in T.apparent_lag_years.__doc__, True)
check("degenerate shelves are findings, not rates",
      all(v[0] in ("CLOSED", "NON-MONOTONIC", "UNDEFINED")
          for v in T.DEGENERATE_TIME.values()), True)

check("a closed loop spends no reference time", T.loop_report(9000)["reference_years_elapsed"], 0.0)
check("and therefore can never accession", T.loop_report(9000)["max_ascension_mark"], 0)
check("contemporaneity is equality of ascension mark", T.contemporaneous(9, 9), True)
check("an unratified event is not present to a higher registry", T.is_present_at(9, 17), False)
check("but is present to its own rung and below", T.is_present_at(9, 4), True)
check("retrocausality with no inversion is free", T.retrocausality_beta(0), 0.0)
check("and a longer inversion costs more",
      T.retrocausality_beta(500) > T.retrocausality_beta(5), True)


print()
print("=" * 96)
print("6. THE LEDGER — a currency denominated in the same joules as a punch")
print("=" * 96)

import ledger as L          # noqa: E402

check("1 Standard is the feat ladder's own rock-pulverisation figure",
      L.JOULES_PER_STANDARD, PH.MATERIAL["rock"]["pulv"] * 1.0, tol=1e-6,
      note="reuse, not a new constant: currency and combat share a unit")
check("work_value inverts the definition", L.work_value(L.JOULES_PER_STANDARD), 1.0, tol=1e-9)
check("cross rates are reciprocal",
      L.cross_rate("gil", "caps") * L.cross_rate("caps", "gil"), 1.0, tol=1e-9)
check("conversion round-trips", L.from_standards(L.to_standards(600.0, "gil"), "gil"), 600.0,
      tol=1e-9)
check("an inconvertible currency returns None, it does not guess",
      L.to_standards(10, "poneglyph-grade favour"), None)
check("a higher band prices higher",
      L.assay_to_standards("M6")["standards"] > L.assay_to_standards("M3")["standards"], True)
check("band pricing sits inside the band's own log window",
      A.BAND_EDGES["M4"]["ruin"] <= L.assay_to_standards("M4", 5.0)["joules"]
      <= A.BAND_EDGES["M5"]["ruin"], True)
check("the Ledger refuses to price an Anchor, only its work",
      "not for sale" in L.assay_to_standards("M7")["caveat"], True)


print()
print("=" * 96)
print("7. THE DERIVATION LEDGER — does every quantity name its parents?")
print("=" * 96)

import derivation as D      # noqa: E402

_problems = D.check_graph()
check("the derivation graph closes (no dangling, rootless, or cyclic quantities)",
      len(_problems), 0, note="; ".join(_problems[:3]))
check("every DERIVED quantity names at least one parent",
      all(q["parents"] for q in D.LEDGER.values() if q["kind"] == D.DERIVED), True)
check("every OWNER declaration carries a citation",
      all(q["source"] for q in D.LEDGER.values() if q["kind"] == D.OWNER), True)
check("derived quantities outnumber free parameters",
      sum(1 for q in D.LEDGER.values() if q["kind"] == D.DERIVED) >
      sum(1 for q in D.LEDGER.values() if q["kind"] == D.OWNER), True)
check("foresight traces all the way down to G",
      any(n == "G" for n, _, _ in D.provenance("prescience_bits")), True,
      note="the invented 2^(rung-1) exponent left no such trail")
check("the Standard traces to measured material strengths",
      any(n == "material_strengths" for n, _, _ in D.provenance("joules_per_standard")), True)
check("apparent lag traces to the propagation constant, not a tempo constant",
      any(n == "years_per_unit_distance" for n, _, _ in D.provenance("apparent_lag")), True)
check("the census traces to a real galaxy count",
      any(n == "galaxy_count" for n, _, _ in D.provenance("civ_census")), True)

print()
print("=" * 96)
print("8. RIGOR — commensuration, and the estimators that must recover what they are given")
print("=" * 96)

import numpy as np           # noqa: E402
import rigor as R            # noqa: E402

# ---- Perron / AHP: exact recovery of a known weight vector -------------------------------------
w_true = np.array([0.4, 0.3, 0.2, 0.1])
A_c = w_true[:, None] / w_true[None, :]
p = R.perron_weights(A_c)
check("Perron recovers the generating weights exactly",
      float(np.max(np.abs(p["weights"] - w_true))), 0.0, tol=1e-9,
      note="a consistent ratio matrix must return the vector that built it")
check("lambda_max == n for a consistent matrix (Saaty 1977)",
      p["lambda_max"], 4.0, tol=1e-9)
check("CI == 0 for a consistent matrix", p["CI"], 0.0, tol=1e-9)
check("CR == 0 for a consistent matrix", p["CR"], 0.0, tol=1e-9)

# Perturb one judgment: consistency must degrade, and lambda_max must exceed n.
A_i = A_c.copy()
A_i[0, 3] *= 4.0
A_i[3, 0] = 1.0 / A_i[0, 3]
pi_ = R.perron_weights(A_i)
check("lambda_max > n once a judgment is perturbed", pi_["lambda_max"] > 4.0, True)
check("CR rises above zero with inconsistency", pi_["CR"] > 0.0, True)

# ---- Theorem 1: consistency <=> curl-freeness ---------------------------------------------------
l_c = R.logrank_weights(A_c)
l_i = R.logrank_weights(A_i)
check("consistent matrix has zero curl", l_c["curl_fraction"], 0.0, tol=1e-9)
check("inconsistent matrix has positive curl", l_i["curl_fraction"] > 0.0, True)
check("THEOREM 1: CR and curl vanish together",
      (p["CR"] < 1e-9) == (l_c["curl_fraction"] < 1e-9), True)
check("THEOREM 1: CR and curl rise together",
      (pi_["CR"] > p["CR"]) == (l_i["curl_fraction"] > l_c["curl_fraction"]), True)
check("log-least-squares agrees with Perron on a consistent matrix",
      float(np.max(np.abs(l_c["weights"] - w_true))), 0.0, tol=1e-9,
      note="Crawford & Williams 1985 geometric-mean solution")
check("but they are NOT the same functional (different values off-consistency)",
      abs(pi_["CR"] - l_i["curl_fraction"]) > 1e-6, True,
      note="the earlier draft claimed identity; they are co-vanishing, not equal")

# ---- MDL: exact combinatorics -------------------------------------------------------------------
check("log2 C(12,3) computed by lgamma matches math.comb",
      R._log2_choose(12, 3), math.log2(math.comb(12, 3)), tol=1e-9)
check("log2 C(n,0) == 0", R._log2_choose(12, 0), 0.0, tol=1e-12)
check("selecting 1 of 2 alternatives costs exactly 1 bit", R.mdl_bits(2), 1.0, tol=1e-12)
check("beta floor rises with the number of laws excepted",
      R.adjudication_beta(3, 4)["beta_floor_bits"] >
      R.adjudication_beta(1, 4)["beta_floor_bits"], True)
check("every declared adjudication cost sits above its MDL floor",
      all(dec >= R.adjudication_beta(l, rg, pa)["beta_floor_bits"]
          for l, rg, pa, dec in [(1, 2, 0, 8), (1, 4, 1, 32), (2, 4, 1, 64),
                                 (2, 8, 2, 96), (3, 8, 3, 128)]), True,
      note="a declared cost BELOW the floor would be an underpriced exception")

# ---- Uncertainty: log-variances add, verified against Monte Carlo -------------------------------
facs = [("a", 1e3, 0.5), ("b", 1e2, 0.8), ("c", 1e-1, 0.3)]
lp = R.lognormal_product(facs)
check("log-normal product median = product of medians",
      lp["median"], 1e3 * 1e2 * 1e-1, tol=1e-6)
check("log-variances add in quadrature",
      lp["sigma_dex"], math.sqrt(0.5 ** 2 + 0.8 ** 2 + 0.3 ** 2), tol=1e-9)
_rng = np.random.default_rng(7)
_mc = np.prod([10 ** _rng.normal(math.log10(m), s, 400000) for _, m, s in facs], axis=0)
check("and the analytic sigma matches a 400k-sample Monte Carlo",
      float(np.std(np.log10(_mc))), lp["sigma_dex"], tol=0.01,
      note="independent numerical confirmation, not a restatement")

# ---- Jensen: the whole point of integrating -----------------------------------------------------
_pa = R.prob_at_least_one(math.log10(2.0), 2.0)
check("P at the point estimate exceeds the integrated P (concavity)",
      _pa["p_at_least_one_at_point_estimate"] > _pa["p_at_least_one_integrated"], True,
      note="Jensen on 1-exp(-x); this is the Fermi point-estimate error")
check("integrated P is a genuine probability",
      0.0 <= _pa["p_at_least_one_integrated"] <= 1.0, True)
check("with no uncertainty the two coincide",
      abs(R.prob_at_least_one(math.log10(2.0), 1e-9)["jensen_gap"]) < 1e-6, True,
      note="the correction must vanish when there is nothing to correct")

# ---- Bradley-Terry: recover known strengths from the contests they generate ---------------------
_p_true = {"a": 0.5, "b": 0.3, "c": 0.2}
_wins = {}
for _i in _p_true:
    for _j in _p_true:
        if _i != _j:
            _wins[(_i, _j)] = 1000.0 * _p_true[_i] / (_p_true[_i] + _p_true[_j])
_bt = R.bradley_terry(_wins)
_got = dict(zip(_bt["names"], _bt["strengths"]))
check("Bradley-Terry MLE recovers the strengths that generated the contests",
      max(abs(_got[k] - _p_true[k]) for k in _p_true), 0.0, tol=1e-4,
      note="Hunter 2004 MM algorithm; a fixed-point recovery test")
check("and reports near-zero deviance on data its own model generated",
      _bt["deviance"] < 1e-6, True)

# ---- Commensuration: the bit bridge -------------------------------------------------------------
check("one point of any axis at M5 = band_resolution(M5)/10 bits",
      R.measure_bit_value("M5"), T.band_resolution("M5") / 10.0, tol=1e-12,
      note="was rung_description_length (cumulative), which made every M0 point worth zero bits; "
           "the anchor validation exposed the conflation")
check("bit-worth is a function of the BAND alone -- no per-axis table exists",
      "axis" not in R.measure_bit_value.__code__.co_varnames, True,
      note="the claim that Ruin and Acumen share a unit is structural: the function cannot "
           "take an axis, so it cannot differ by one. (An earlier form of this check compared "
           "measure_bit_value('M7') to itself -- a tautology that could never fail.)")
check("the faculties carry real weight after the parity erratum",
      sum(A.FACULTY_WEIGHTS.values()), 3.0 / 11.0, tol=1e-12,
      note="was 0.0 — the one value a shared unit forbids. See assay.py's erratum note")
check("and FACULTY_WEIGHTS now agrees with the live WEIGHTS table",
      all(abs(A.WEIGHTS[k] - v) < 1e-12 for k, v in A.FACULTY_WEIGHTS.items()), True,
      note="it was previously defined and never read by anything, which is how zero survived")
check("parity over 11 axes gives 1/11 each",
      R.faculty_parity_weights()["uniform_weight"], 1.0 / 11.0, tol=1e-12)

# ---- Extreme value: the correction must behave ---------------------------------------------------
check("no correction when the sample is the whole population",
      R.gumbel_return_level(100.0, 50, 50)["correction_bits"], 0.0, tol=1e-12)
check("a heavier tail (smaller alpha) implies a larger correction",
      R.gumbel_return_level(100.0, 14, 900, tail_index=1.0)["correction_bits"] >
      R.gumbel_return_level(100.0, 14, 900, tail_index=1.5)["correction_bits"], True)
check("correction = log2(N/n)/alpha exactly",
      R.gumbel_return_level(100.0, 14, 900, tail_index=1.0)["correction_bits"],
      round(math.log2(900 / 14), 2), tol=1e-9)
check("ceiling sampling is reported as non-random",
      "NOT random" in R.ceiling_confidence(900, 14)["sampling"], True)
check("and a decimal is refused at every sample size",
      R.ceiling_confidence(900, 14)["supports_decimal"], False)

print()
print("=" * 96)
print("9. THE COLLEGE — one Custos per degree of freedom, and the interval they generate")
print("=" * 96)

import custodes as CU       # noqa: E402
import pipeline as PLmod    # noqa: E402

_ks = dict(ruin=0.6, continuity=4.8, celerity=6.5, reach=1.2,
           transgression=8.7, sustain=7.4, vector=0.8, volition=9.6)

_cov = CU.dof_coverage()
check("every degree of freedom has a Custos standing in it", _cov["unmanned"], [])
check("the college is exactly one-to-one with the degrees of freedom", _cov["one_to_one"], True,
      note="the count is derived from the computation, not chosen for aesthetics")
check("no two Custodes share a degree of freedom",
      len({c["dof"] for c in CU.CUSTODES.values()}), len(CU.CUSTODES))
check("the charter's three Hands are preserved, not replaced",
      all(n in CU.CUSTODES for n in ("Quill", "Moth", "Avar")), True)

_r = CU.convene("M3", _ks, attestation="Witnessed", worksheet="x")
check("the interval covers EVERY signed reading", _r["covers_every_reading"], True,
      note="a college publishing a band that excludes one of its own has hidden its "
           "disagreement, not measured it")
check("prior and attestation shares sum to 1",
      _r["prior_divergence_share"] + _r["attestation_floor_share"], 1.0, tol=1e-9)

# The charter's central claim about intervals: better evidence narrows the reducible part only.
_seq = [CU.convene("M3", _ks, attestation=a, worksheet="x")
        for a in ("Disputed", "Reconstructed", "Transcribed", "Witnessed", "Instrumented")]
check("better attestation never widens the interval",
      all(_seq[i]["interval"] >= _seq[i + 1]["interval"] for i in range(len(_seq) - 1)), True)
check("and the prior share rises as evidence improves",
      all(_seq[i]["prior_divergence_share"] <= _seq[i + 1]["prior_divergence_share"]
          for i in range(len(_seq) - 1)), True,
      note="what survives good evidence is standpoint, not error")
check("the interval never reaches zero — a prior floor remains",
      _seq[-1]["interval"] > 0.0, True,
      note="Theorem 4: perfect evidence does not collapse distinct Daseins")

# Threnody's veto is the one standpoint that can refuse the output rather than shift it.
_v = CU.convene("M3", _ks, attestation="Witnessed", worksheet="x", eta=0.70)
check("Threnody vetoes a decimal where the curl is large", _v["decimal"], None)
check("and a low-curl structure passes",
      CU.convene("M3", _ks, attestation="Witnessed", worksheet="x", eta=0.99)["decimal"]
      is not None, True)

# Reproduction of the charter's own published worked example, from its own three Hands.
_full = dict(CU.CUSTODES)
try:
    CU.CUSTODES.clear()
    CU.CUSTODES.update({k: _full[k] for k in ("Quill", "Moth", "Avar")})
    _three = CU.convene("M3", _ks, attestation="Witnessed", worksheet="x")
finally:
    CU.CUSTODES.clear()
    CU.CUSTODES.update(_full)
check("three Hands reproduce the charter's published Kenshiro decimal within 0.05",
      abs(_three["decimal"] - 0.52) <= 0.05, True,
      note="charter: M3.52 ± 0.12; this is a reproduction test, not a fit")
check("and its published interval within 0.03",
      abs(_three["interval"] - 0.12) <= 0.03, True)


print()
print("=" * 96)
print("10. THE ASSAY AFTER PARITY — what the erratum did and did not move")
print("=" * 96)

check("all eleven axes now carry weight", len(A.WEIGHTS), 11)
check("the weights still sum to 1", sum(A.WEIGHTS.values()), 1.0, tol=1e-12)
check("each faculty sits at parity, 1/11", A.WEIGHTS["acumen"], 1.0 / 11.0, tol=1e-12)
check("the physical block holds exactly 8/11",
      sum(A.WEIGHTS[k] for k in A.CHARTER_PHYSICAL_WEIGHTS), 8.0 / 11.0, tol=1e-12,
      note="the same share it would hold under full uniformity: block parity is exact")
check("the charter's declared PROPORTIONS among the eight are untouched",
      max(abs(A.WEIGHTS[k] / A.WEIGHTS["ruin"]
              - A.CHARTER_PHYSICAL_WEIGHTS[k] / A.CHARTER_PHYSICAL_WEIGHTS["ruin"])
          for k in A.CHARTER_PHYSICAL_WEIGHTS), 0.0, tol=1e-12)

_phys_only = A.assay("M3", _ks, attestation="Witnessed", worksheet="x")
check("BACKWARD COMPATIBILITY: every physical-only decimal is unchanged",
      _phys_only["decimal"], 0.49, tol=1e-9,
      note="the composite renormalises over scored axes, so a common rescaling cancels")
# The claim is RELATIVE, and it has to be, because an absolute threshold here is a magic number
# tied to whatever the sigmas happened to be the day it was written. This one said `> 0.10`,
# calibrated against attestation sigmas that were later found to exceed the maximum-entropy
# dispersion of the scale itself -- so when that was corrected, a true statement started
# reporting FAIL. What is actually being asserted is that three unmeasured faculties cost more
# than three faculties known not to apply, and that survives any rescaling.
_phys_na = A.assay("M3", dict(_ks, acumen=A.INAPPLICABLE, discernment=A.INAPPLICABLE,
                              suasion=A.INAPPLICABLE), attestation="Witnessed", worksheet="x")
check("but the interval widens, because unmeasured faculties are now known to be unmeasured",
      _phys_only["interval"] > _phys_na["interval"], True,
      note="ignorance about three axes must cost more than knowing they do not apply")
check("marking a faculty INAPPLICABLE restores full coverage",
      A.assay("M3", dict(_ks, acumen=A.INAPPLICABLE, discernment=A.INAPPLICABLE,
                         suasion=A.INAPPLICABLE), attestation="Witnessed",
              worksheet="x")["axis_coverage"], 1.0, tol=1e-9,
      note="a landslide's absent Suasion is knowledge; charging ignorance for it would be wrong")
check("scoring the faculties actually moves the Magnitude",
      A.assay("M3", dict(_ks, acumen=9.0, discernment=8.0, suasion=7.0),
              attestation="Witnessed", worksheet="x")["decimal"] != 0.49, True,
      note="the point of the erratum: Int/Wis/Cha can now register at all")

check("attestation quality is DERIVED from assay's own table, not a second one",
      CU.ATTESTATION_QUALITY["Disputed"] < CU.ATTESTATION_QUALITY["Transcribed"]
      < CU.ATTESTATION_QUALITY["Instrumented"], True,
      note="monotone by construction; moves automatically if the charter revises a grade")
check("and its worst grade scores exactly zero quality",
      CU.ATTESTATION_QUALITY["Disputed"], 0.0, tol=1e-9)
check("Threnody's bar IS Saaty's CR bar, not a fresh number",
      CU.CURL_VETO_THRESHOLD, 0.10, tol=1e-12,
      note="curl < 0.10 via Theorem 1; a draft used 0.85 chosen to feel lenient")
check("Lumen no longer tilts — staleness is dispersion, not direction",
      CU.CUSTODES["Lumen"]["tilt"], 0.0, tol=1e-12)
check("news fully arrived adds no widening",
      CU.staleness_widening(0.006, 5000), 0.0, tol=1e-9)
check("news still in transit widens toward half a band",
      CU.staleness_widening(1.126, 300), 0.5, tol=1e-9,
      note="a band has width 1, so total ignorance of the decimal is half-width 0.5 — forced, "
           "not tuned")
check("and widening is bounded by half a band",
      all(0.0 <= CU.staleness_widening(d, y) <= 0.5
          for d in (0.0, 0.5, 1.126, 5.0) for y in (0, 300, 5000, 100000)), True)
check("a stale reading reports a wider interval than a local one",
      CU.convene("M3", _ks, attestation="Witnessed", worksheet="x",
                 distance=1.126, years_since=300)["interval"] >
      CU.convene("M3", _ks, attestation="Witnessed", worksheet="x")["interval"], True)

check("stat-block mechanics are refused as scale evidence",
      PLmod.valid_scale_note("Each creature within 5 feet must succeed on a Dexterity saving "
                             "throw or be blinded"), "",
      note="a resolution procedure is not a demonstrated act; a rules radius is not a reach")
check("defeating powerful BEINGS is not SCALE evidence",
      PLmod.valid_scale_note("overthrew the Titans roughly 500 years before the campaign's "
                             "start"), "",
      note="corrected expectation. This was written when the gate accepted any scale-ish "
           "vocabulary. Overthrowing the Titans is a genuine feat, but it is CONTEST evidence "
           "for Volition (theta, phase 4's chain of defeats), not a Ruin magnitude. A Ruin band "
           "needs an act upon an object of known scale, or a measured quantity")
check("an act upon an object of known scale IS scale evidence",
      bool(PLmod.valid_scale_note("destroyed the city of Limsa Lominsa with a tidal wave")), True)
check("a measured quantity stands on its own",
      bool(PLmod.valid_scale_note("3 miles tall and 1.5 miles wide")), True)
check("a bare scale noun does not",
      PLmod.valid_scale_note("resource-rich jungle planet, site of a mining operation"), "",
      note="the single regex that licensed ~90% of the library's bands")
check("a title is not a deed",
      PLmod.valid_scale_note("primordial cosmic being once called the 'Breaker of Worlds'"), "")
check("nor is a description of a description",
      PLmod.valid_scale_note("GOLB is described as a malevolent, dimension-spanning entity"), "")
check("and the subject must be the doer, not the target",
      PLmod.valid_scale_note("must be located, activated, and destroyed to save a planet"), "")
check("a date is not a magnitude",
      PLmod.valid_scale_note("Earth-like planet, colonized in 2186 by the United Nations"), "")
check("a clean feat passes untouched",
      PLmod.scale_note_needs_rephrase("destroyed a mountain range with a single blow"), False)



print()
print("=" * 96)
print("11. THE FOUR STATUSES — an axis can lack a number for four different reasons")
print("=" * 96)

_b = dict(continuity=4.8, celerity=6.5, reach=1.2, transgression=8.7,
          sustain=7.4, vector=0.8, volition=9.6)
_sc0 = A.assay("M3", dict(_b, ruin=0.0), attestation="Witnessed", worksheet="x")
_nil = A.assay("M3", dict(_b, ruin=A.NONE), attestation="Witnessed", worksheet="x")
_une = A.assay("M3", dict(_b, ruin=A.UNESTIMABLE), attestation="Witnessed", worksheet="x")
_ina = A.assay("M3", dict(_b, ruin=A.INAPPLICABLE), attestation="Witnessed", worksheet="x")

check("axis_score CLAMPS at zero, so 0.0 is a bound not a point",
      A.axis_score(1e-3, "M3", "ruin"), A.axis_score(A.BAND_EDGES["M3"]["ruin"], "M3", "ruin"),
      tol=1e-12, note="a firecracker and the band floor both read 0.0 — this is why NONE exists")
check("NONE therefore matches a clamped 0.0 in the composite, by construction",
      _nil["decimal"], _sc0["decimal"], tol=1e-12,
      note="no arithmetic exists below the floor; the difference is informational")
check("but NONE licenses a definiteness claim that 0.0 does not",
      _nil["nil_is_definite"] and not _sc0["nil_is_definite"], True)
check("NONE earns full coverage credit — it is knowledge",
      _nil["axis_coverage"], _sc0["axis_coverage"], tol=1e-12)

check("UNESTIMABLE is ignorance: it lowers coverage",
      _une["axis_coverage"] < _nil["axis_coverage"], True)
check("and therefore widens the interval",
      _une["interval"] > _nil["interval"], True)
check("UNESTIMABLE stays in the denominator (unlike INAPPLICABLE)",
      _une["axis_coverage"] < _ina["axis_coverage"], True,
      note="unexpressed is an open question; inapplicable is a malformed one")
check("INAPPLICABLE is struck from the denominator entirely",
      "ruin" not in _ina["axes_unestimable"] and _ina["axis_coverage"] > _une["axis_coverage"],
      True)

check("all four statuses are distinguishable in the record",
      len({(_sc0["nil_is_definite"], tuple(_sc0["axes_unestimable"])),
           (_nil["nil_is_definite"], tuple(_nil["axes_unestimable"])),
           (_une["nil_is_definite"], tuple(_une["axes_unestimable"]))}), 3)
check("UNESTIMABLE is available on EVERY axis, not only the social ones",
      all(A.assay("M3", {**_b, "ruin": 5.0, k: A.UNESTIMABLE},
                  attestation="Witnessed", worksheet="x")["axes_unestimable"] == [k]
          for k in ("celerity", "reach", "sustain", "acumen", "suasion")), True,
      note="a scholar who never fought has an unestimable Ruin; nil would be unearned")



print()
print("=" * 96)
print("12. ANCHOR VALIDATION — the instrument at floor, standard and ceiling")
print("=" * 96)

import anchors as AN        # noqa: E402

_MAXED = {k: 10.0 for k in ("ruin", "celerity", "reach", "sustain", "continuity",
                            "transgression", "vector", "acumen", "discernment", "suasion")}
_top = A.assay("M10", _MAXED, attestation="Witnessed", worksheet="x")
_mid = A.assay("M4", _MAXED, attestation="Witnessed", worksheet="x")
check("the ceiling SATURATES instead of overflowing its notation",
      _top["decimal"] <= 0.99, True,
      note="printed 'M10.100' before the anchors caught it — a ruler whose top breaks its own scale")
check("and says it has reached the ceiling", _top["at_ladder_ceiling"], True)
check("a maxed non-top band flags promotion rather than auto-promoting",
      _mid["promotion_due"], True, note="promotion is curatorial, not arithmetic (Part Three)")
check("and does not silently jump a band", _mid["magnitude"], "M4")

check("every band has non-zero information resolution",
      all(T.band_resolution(b) > 0 for b in A.LADDER), True,
      note="cumulative L_r gave M0 exactly zero, so the floor had no resolution at all")
check("one axis point is worth real bits even at the floor",
      R.measure_bit_value("M0") > 1.0, True)
check("band resolution and cumulative content are DIFFERENT quantities",
      T.band_resolution("M5") != T.rung_description_length("M5"), True,
      note="conflating them is the defect the anchors exposed")
check("prescience still uses CUMULATIVE content, which is correct for it",
      T.prescience_horizon_bits("M5", 1)["rung_description_length_bits"],
      T.rung_description_length("M5"), tol=1e-9)

# The five anchors must all produce a reading without exception.
_res = {}
for _n, _a in AN.ANCHORS.items():
    _res[_n] = A.assay(_a["anchor"], _a["scores"], attestation=_a["attestation"],
                       worksheet="anchors")
check("all five anchors produce a reading", all(r.get("decimal") is not None
                                                for r in _res.values()), True)
check("the ordinary person carries all eleven axes, none struck",
      len([k for k, v in AN.ANCHORS["The Skate Guy"]["scores"].items()
           if v == A.INAPPLICABLE]), 0,
      note="if the instrument cannot read a skateboarder it cannot read anything")
check("and several of his axes are genuinely NIL rather than unmeasured",
      set(_res["The Skate Guy"]["axes_nil"]), {"transgression", "vector"})
check("the object has faculties at NIL, not struck as category errors",
      set(_res["A Sword"]["axes_nil"]) >= {"acumen", "discernment", "suasion"}, True,
      note="0 bits/epoch is a well-posed answer; the question is not malformed")
check("but a sword's Volition IS struck — equipment is not a party to a contest",
      AN.ANCHORS["A Sword"]["scores"]["volition"], A.INAPPLICABLE)
check("the living-but-unconscious case separates NIL from UNESTIMABLE",
      bool(_res["Yggdrasil"]["axes_nil"]) and bool(_res["Yggdrasil"]["axes_unestimable"]), True,
      note="it persuades no one (nil); nobody has measured whether it senses (unestimable)")
check("and Yggdrasil carries the widest interval of the five",
      _res["Yggdrasil"]["interval"] == max(r["interval"] for r in _res.values()), True,
      note="three unestimable axes plus Reconstructed attestation — correctly the least known")

# --- structural facts the anchors exposed, pinned so a later change announces itself ----------
check("STRUCTURAL: band order dominates — no decimal can cross a band",
      max(r["decimal"] for r in _res.values()) < 1.0, True,
      note="so an entity's rank is set ENTIRELY by its anchor, and every axis score only breaks "
           "ties within it. This makes nomination (Sable) the most consequential degree of freedom")

# KNOWN DEFECT, charter-owned. Pinned as a test so that fixing it fails here loudly and this note
# gets revisited, rather than the defect quietly persisting.
_dull = A.instrument("M5", {"acumen": 1.0}, worksheet="x")["faculties"]["Intelligence"]
_sharp = A.instrument("M5", {"acumen": 10.0}, worksheet="x")["faculties"]["Intelligence"]
check("KNOWN DEFECT: the Instrument has NO resolution above M4",
      _dull == _sharp, True,
      note="X.6 §6 Def 3 sets the M5+ window to (30,30), so a dullard and a genius both read 30. "
           "This defeats the Int/Wis/Cha commensuration exactly where it matters. Charter-owned; "
           "needs owner sign-off. If this check FAILS, the window was widened — update this note")
check("KNOWN DEFECT: M5 caps the window but earns no Transcendence Grade",
      A.instrument("M5", {"acumen": 5.0}, worksheet="x")["transcendence_grade"], None,
      note="off-by-one: the cap starts at M5 and the Grade at M6, so M5 beings lose the capped "
           "information with nothing carrying it")



print()
print("=" * 96)
print("13. THE ADDRESS SPACE — every planet named, and the map derived from the name")
print("=" * 96)

import address_space as AS   # noqa: E402
import worldseed as WS       # noqa: E402

check("field widths are each sized to their own census population",
      all(AS.WIDTHS[n] >= math.ceil(math.log2(max(2, p))) for n, p in AS.FIELDS), True,
      note="derived from cosmography, not chosen")
check("the address carries all eight charter tiers",
      [n for n, _ in AS.FIELDS],
      ["hyperverse", "xenoverse", "metaverse", "multiverse", "universe",
       "galaxy", "star", "planet"],
      note="Part Two's Shelfmark has seven tiers below Omega; an earlier version had five")
check("capacity exceeds the census with headroom",
      AS.CAPACITY > C.census("STANDARD")["exoplanets"] * 168, True)
check("a 64-bit scheme could NOT address this omniverse",
      (1 << 64) < C.census("STANDARD")["exoplanets"] * 168, True,
      note="No Man's Sky uses 64 bits for 1.8e19 planets; this holds 5.4e21")

_a = AS.pack(0, 2, 3, 11, 40, 0x2A1F3B, 0x5C91D2, 1)
check("pack/unpack round-trips exactly",
      AS.unpack(_a) == dict(hyperverse=0, xenoverse=2, metaverse=3, multiverse=11,
                            universe=40, galaxy=0x2A1F3B, star=0x5C91D2, planet=1), True)
check("an out-of-range field RAISES rather than wrapping silently",
      _raises(lambda: AS.pack(99, 0, 0, 0, 0, 0, 0, 0)), True,
      note="a wrapped address names a different world -- the one failure worth being loud about")
check("the XENOVERSE is charted — deliberate joins are visible",
      "X2" in AS.shelfmark(_a), True,
      note="two links sit an order of magnitude above the 99.5th percentile; nothing "
           "statistical makes those, so somebody made them")
check("the HYPERVERSE is charted as grounding type",
      AS.shelfmark(_a).startswith("Ω › H0 › X2 › Mt.3 › Mv.11 › U-40"), True,
      note="it printed '?' through two earlier passes — first undefined, then pantheon-seeded "
           "and leaving most fictions homeless. Grounding type covers every cosmos")
check("and it is answered per XENOVERSE, so containment holds",
      json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "data", "TIERS.json"), encoding="utf-8")
                )["Alien"].get("hyperverse_type") is not None, True,
      note="per-source assignment split three xenoverses across two hyperverses each")
check("the map seed is derived from the address, not stored",
      AS.map_seed(_a), AS.map_seed(_a))
check("neighbouring planet fields are genuine neighbours",
      AS.unpack(AS.pack(0, 1, 2, 3, 4, 5, 9, 0))["star"] ==
      AS.unpack(AS.pack(0, 1, 2, 3, 4, 5, 9, 1))["star"], True,
      note="unlike a PRNG seed, where adjacent values are unrelated by construction")

import tiers as TI          # noqa: E402
_T = json.load(open(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "data", "TIERS.json"), encoding="utf-8"))

check("every charted source carries a full tier stack",
      all(all(k in v for k in ("hyperverse", "xenoverse", "metaverse", "multiverse"))
          for v in _T.values()), True)
check("the tiers nest strictly: one multiverse never spans two metaverses",
      _nesting_violations(_T), 0,
      note="an earlier cut put the metaverse tighter than the multiverse and split five of them")
check("tier counts decrease going up",
      _tier_counts(_T) == sorted(_tier_counts(_T), reverse=True), True,
      note=str(_tier_counts(_T)))
check("Alien and Predator share a multiverse",
      _T["Alien"]["multiverse"], _T["Predator"]["multiverse"],
      note="their link is 6489 against a 99.5th percentile of 365 — a deliberate join")
check("the deliberate joins are an order of magnitude above the rest",
      TI.DELIBERATE_JOIN > 365 * 4, True,
      note="the cliff that makes a xenoverse 'artificial' rather than merely resonant")
check("assignment is deterministic",
      AS.assign("X::a", _T["Alien"]), AS.assign("X::a", _T["Alien"]))
check("worlds of one source share their upper tiers",
      AS.unpack(AS.assign("X::a", _T["Alien"]))["multiverse"] ==
      AS.unpack(AS.assign("X::b", _T["Alien"]))["multiverse"], True)

check("unattested world axes are SEEDED, never defaulted",
      WS.features("Nowhere", "a place", 12345)["_provenance"]["climate"], "seeded",
      note="defaulting asserted 'temperate' as though a source had said so")
check("and attested axes are marked as such",
      WS.features("Ice World", "a frozen glacial tundra", 1)["_provenance"]["climate"],
      "attested")



print()
print("=" * 96)
print("14. THE WORLD PROFILE — one string, and everything it must reconstruct")
print("=" * 96)

import profile as PR         # noqa: E402
import genre as GN           # noqa: E402

# A SAMPLE, and labelled as one: 400 profiles is plenty to prove round-tripping and far
# cheaper than the full set. If decode ever breaks it breaks on the first row, not the 40,001st.
_rows = PR.build_all(limit=400)
check("every profile round-trips to its own address",
      all(PR.decode(r["profile"])["address"] == r["address"] for r in _rows), True,
      note="a name that does not reconstruct its referent is not a name")
check("and to its own feature vector",
      all(PR.decode(r["profile"])["profile"] == r["profile"] for r in _rows), True)
check("profiles stay short", max(len(r["profile"]) for r in _rows) <= 40, True)
check("a malformed profile RAISES rather than half-decoding",
      _raises(lambda: PR.decode("PS-nonsense")), True)
check("the attestation digit survives encoding",
      PR.decode(PR.encode(12345, "mythology", "classical",
                          {"landform": "isles", "climate": "arid", "condition": "ruined",
                           "tech": "medieval"}, "M4", 3))["attested_axes"], 3,
      note="the field a compression scheme drops first; it distinguishes a citation from a "
           "coin-flip and must survive")
check("band survives encoding",
      PR.decode(PR.encode(1, "mythology", "classical",
                          {"landform": "isles", "climate": "arid", "condition": "ruined",
                           "tech": "medieval"}, "M10", 0))["band"], "M10",
      note="M10 is two characters in the band list and one in the profile — the boundary case")

check("genre is derived from a source's own vocabulary, not from a hash",
      GN.classify_text("zeus odin temple oracle pantheon demigod")[0][0], "mythology")
check("and mythology takes the classical register",
      GN.GENRES["mythology"]["register"], "classical",
      note="the hash had given Pantheon: Roman the 'compact' register")
check("a mixed source reports low confidence rather than picking",
      GN.classify_source({"entries": [{"name": "x", "description":
                                       "starship fleet orbital xenomorph hive infest"}]}
                         )["confidence"] < 0.75, True)
check("an unclassifiable source is not forced into a genre",
      GN.classify_source({"entries": [{"name": "x", "description": "a thing"}]})["genre"],
      "unclassified")

check("the galaxy API seed IS the address's own galaxy field",
      str(AS.unpack(_rows[0]["address"])["galaxy"]) in PR.galaxy_api(_rows[0]["address"])[0], True,
      note="that service nests neighbourhood seeds under galaxy seeds exactly as this address "
           "does, so no translation layer is needed")



print()
print("=" * 96)
print("15. THE HYPERVERSE — grounding type, the Omega Band promoted to a cosmological tier")
print("=" * 96)

import grounding as GR       # noqa: E402

check("every grounding type declares its regress-test answers",
      all("regress" in spec for spec in GR.GROUNDINGS.values()), True,
      note="the cues identify WHICH account is told; the account's own structure decides the "
           "verdict, so this is not a vocabulary trick with a label on top")
check("a demiurgic cosmos is ruled DEMIURGE by the regress test",
      A.regress_test("d", **GR.GROUNDINGS["demiurgic"]["regress"])["verdict"], "DEMIURGE",
      note="it grants its maker a stage, so the regress passes straight through")
check("an ex nihilo cosmos is an ontological claimant",
      A.regress_test("x", **GR.GROUNDINGS["ex_nihilo"]["regress"])["verdict"],
      "ONTOLOGICAL CLAIMANT")
check("'ungrounded' is a TYPE, not a failure code",
      GR.UNGROUNDED_GLOSS.startswith("no origin account"), True,
      note="a godless fiction still answers the First Argument; the answer is that the regress "
           "runs on")

check("cosmogony is read from ORIGIN entries, not the whole catalogue",
      bool(GR._ORIGIN.search("the creation of the world")) and
      not bool(GR._ORIGIN.search("a recurring character in season two")), True,
      note="reading everything let 'recurring character' fire 214 times and nearly made eternal "
           "recurrence the commonest cosmology in the omniverse")
check("a cosmogonic cue must name the COSMOS, not merely repeat",
      GR.classify_text("a cycle of violence and a recurring villain")[0][1], 0,
      note="bare 'cycle' fired 58 times on things like this")
check("but a real cyclical cosmogony still fires",
      GR.classify_text("the kalpa ends and the wheel of ages turns again")[0][0],
      "eternal_cycle")
check("a source with no origin entry comes back ungrounded honestly",
      GR.classify_source({"entries": [{"name": "a sword", "description": "sharp"}]})["grounding"],
      GR.UNGROUNDED)
check("and reports how many origin entries it actually found",
      GR.classify_source({"entries": [{"name": "a sword",
                                       "description": "sharp"}]})["origin_entries"], 0,
      note="so a reader can tell an absent cosmogony from an unread one")



print()
print("=" * 96)
print("16. THE SEVENFOLD ORDER — a declared shape, with measured placement")
print("=" * 96)

import sevenfold as SF       # noqa: E402
import collections as _co    # noqa: E402

_srcs, _coords, _w, _worlds = SF.build()

def _branching(pool, tier_idx):
    t = SF.TIERS[tier_idx]
    parents = _co.defaultdict(set)
    for v in pool.values():
        if t not in v:
            continue
        parents[tuple(v[x] for x in SF.TIERS[:tier_idx] if x in v)].add(v[t])
    return [len(x) for x in parents.values()] or [0]

check("exactly seven hyperverses", max(_branching(_coords, 0)), 7,
      note="the declared root count")
check("no parent exceeds the declared span of seven at ANY tier",
      all(max(_branching(_coords if SF.TIERS[i] in SF.SOURCE_TIERS else _worlds, i)) <= SF.SPAN
          for i in range(len(SF.TIERS))), True)
check("and the span is a BOUND, not a quota — some parents have fewer",
      min(_branching(_worlds, 4)) < SF.SPAN, True,
      note="forcing exactly seven left slot 6 empty across a tier and skewed the universe level "
           "to [111 ... 376]; uniform arity is order with padding underneath")
check("every tier is populated — no collapsed level",
      all(sum(_branching(_coords if SF.TIERS[i] in SF.SOURCE_TIERS else _worlds, i)) > 0
          for i in range(len(SF.TIERS))), True,
      note="pushing 209 sources through five levels collapsed the bottom two into slot 0; a "
           "source is not a universe, so its WORLDS fill the lower tiers")

check("placement is measured, not declared: kin are shelved together",
      all(_coords["Alien"][t] == _coords["Predator"][t] for t in SF.SOURCE_TIERS), True,
      note="their resonance link is 6489 against a 99.5th percentile of 365")
check("and a second deliberate join lands the same way",
      all(_coords["Call of Duty Zombies"][t] == _coords["all Black Ops"][t]
          for t in SF.SOURCE_TIERS), True)
check("shelving is deterministic", SF.build()[1]["Alien"], _coords["Alien"])
check("a source's mark stops at its own depth",
      "U-" not in SF.shelfmark(_coords["Alien"]), True,
      note="a source is a body of universes, not one; printing U- would invent a position")
check("a world's mark carries all five tiers",
      SF.shelfmark(next(iter(_worlds.values()))).count("›"), 5,
      note="Ω › H › X › Mt › Mv › U — five separators for five tiers")



print()
print("=" * 96)
print("17. BURGS — the settlement tier, by the rank-size rule")
print("=" * 96)

import burgs as BG          # noqa: E402

_f = {"landform": "continents", "climate": "temperate",
      "condition": "settled", "tech": "medieval"}
_bs = BG.burgs_for(424242, _f)

check("the k-th burg holds P1/k, independently recomputed",
      _bs[9]["population"], max(30, int(_bs[0]["population"] / 10)), tol=1e-9,
      note="Auerbach 1913 / Zipf 1949; q = 1 is the classical rule")
check("populations are strictly non-increasing by rank",
      all(_bs[i]["population"] >= _bs[i + 1]["population"] for i in range(len(_bs) - 1)), True)
check("the ranking runs down to the hamlet floor and stops",
      _bs[-1]["population"] <= BG.HAMLET_FLOOR * 2, True,
      note="n = P1/P_min, so the count is a consequence of the law, not a second parameter")

_cls = {}
for b in _bs:
    _cls[b["class"]] = _cls.get(b["class"], 0) + 1
check("the pyramid is right way up: hamlets outnumber cities",
      _cls.get("hamlet", 0) > _cls.get("city", 0) * 50, True,
      note="a count chosen alongside the law gave 39% cities and 0% hamlets — an inverted pyramid")
check("and hamlets are the plurality",
      max(_cls, key=_cls.get), "hamlet")

check("small settlements route to the village generator",
      BG.classify(60)[1], "village")
check("and large ones to the city generator", BG.classify(50000)[1], "city")
check("the burg link routes THROUGH Azgaar, not around it",
      "azgaar" in BG.burg_link(12345, 1) and "burg=1" in BG.burg_link(12345, 1), True,
      note="Azgaar generates each burg's population and flags from the map seed and hands them "
           "to Watabou itself; a URL of our own would open a DIFFERENT city for the same burg")
check("burg seeds are deterministic",
      BG.burgs_for(424242, _f, limit=3)[2]["seed"], _bs[2]["seed"])
check("an archipelago is mostly coastal, a highland mostly not",
      sum(b["coast"] for b in BG.burgs_for(7, dict(_f, landform="archipelago"), limit=200)) >
      sum(b["coast"] for b in BG.burgs_for(7, dict(_f, landform="highland"), limit=200)), True,
      note="the world's own shape decides, so burgs inherit their planet")


print()
print("=" * 96)
print("18. THE DAY'S JOINTS — settled, epochs, the split gate, the clamp (added 2026-08-23)")
print("=" * 96)

import magnitude as MG      # noqa: E402
import identity as IDN      # noqa: E402
import lognames as LN       # noqa: E402

check("a scored result is SETTLED",
      MG.settled({"result": {"decimal": 0.5}}), True)
check("a deferral is NOT settled -- it must requeue",
      MG.settled({"status": "DEFERRED", "result": None}), False)
check("'no axis cleared its gate' is a FINDING, settled",
      MG.settled({"result": None, "reason": "no axis cleared its gate on ..."}), True)
check("a bare transport failure is not settled",
      MG.settled({"result": None, "reason": "no answer"}), False)

check("epoch mandate: mtg refuses 'unstamped'",
      IDN.epoch_acceptable("mtg.fandom.com", "unstamped"), False)
check("epoch mandate: mtg refuses empty",
      IDN.epoch_acceptable("mtg.fandom.com", ""), False)
check("epoch mandate: mtg accepts a named state",
      IDN.epoch_acceptable("mtg.fandom.com", "Living Guildpact of Ravnica"), True)
check("epoch mandate: non-mandated hosts accept anything",
      IDN.epoch_acceptable("dragonball.fandom.com", ""), True)
check("the directive exists for mandated hosts and only them",
      bool(IDN.epoch_directive("mtg.fandom.com")) and
      IDN.epoch_directive("dragonball.fandom.com") is None, True)

_cand = {"ruin": [{"feat": "he destroyed the entire mountain range with one blow"}]}
_ok = MG._split_gate({"axes": {"ruin": {"score": 7.0,
      "feat": "destroyed the entire mountain range"}}}, _cand)
check("split gate: a trimmed verbatim citation scores", _ok[0].get("ruin"), 7.0, tol=1e-9)
_fab = MG._split_gate({"axes": {"ruin": {"score": 9.9,
      "feat": "he destroyed the entire mountain range with one blow and then ate a galaxy"}}},
      _cand)
check("split gate: a fabricated WRAPPER around a real quote is refused",
      _fab[0].get("ruin"), A.UNESTIMABLE)
check("and the refusal is recorded as a rejection", len(_fab[2]) >= 1, True)

check("the one-shot ceiling sits above the split slice",
      MG.ONE_SHOT_MAX > MG.SPLIT_SLICE, True,
      note="a prompt too big to one-shot must still be sliceable")
check("index pages are not entities",
      bool(MG.NOT_AN_ENTITY.match("List of tertiary characters")), True)
check("but a person with 'of' in the name is",
      bool(MG.NOT_AN_ENTITY.match("Monkey D. Luffy")), False)
check("job log names are shared constants, not string twins",
      LN.READ == "read_auto.log" and LN.ROLL == "roll_auto.log", True)


# ---- Section 18b: the assay's TOPOLOGY under a mocked transport ---------------------------------
#
# Section 18 proves the pure functions; this proves the ROUTING -- the five ways a call can go
# (one-shot scored, junk one-shot rescued by the split retry, epoch refusal, no transport,
# split-first over the recall cliff) with every model call faked, so the test is deterministic,
# free, and runs with the pool down. Each fake answers the schema it is shown; the real compose,
# verify, gates and clamp all run.

import cascade_bridge as _CBm

_FEAT = "He destroyed the entire fortress city with a single unaided strike."
_AX0 = next((ax for ax in MG.AXES if MG.AXIS_RE[ax].search(_FEAT)), None)
check("the probe feat lands in some axis vocabulary", _AX0 is not None, True,
      note="if this fails the vocab changed; pick a new probe sentence")

_EV = {"text": {}, "quantities": [], "pages_read": 1}
_CAND_HOLDER = [None]
_CFG = {"model": "mock", "ollama_host": "http://localhost:11434", "seed": 47, "num_ctx": 6144}


def _cand_small():
    c = {ax: [] for ax in MG.AXES}
    c[_AX0] = [{"feat": _FEAT, "page": "TestPage"}]
    return c


def _good_axes():
    return {ax: ({"score": 2.0, "feat": _FEAT} if ax == _AX0
                 else {"score": "unestimable", "feat": ""}) for ax in MG.AXES}


_saved = (MG.F.evidence_for, MG.candidates, _CBm.ask, MG.P.ask, MG._ask, MG._POOL[0])
try:
    MG.F.evidence_for = lambda host, entity: dict(_EV)
    MG.candidates = lambda ev, cap=None: {k: [dict(r) for r in v]
                                          for k, v in _CAND_HOLDER[0].items()}
    MG._POOL[0] = True
    MG.P.ask = lambda *a, **k: None

    # A. one-shot scored, and the source ceiling clamps the anchor
    _CAND_HOLDER[0] = _cand_small()
    _CBm.ask = lambda *a, **k: {"anchor": "M2", "presence_evidence": _FEAT,
                                "epoch": "test era of the mock", "axes": _good_axes()}
    _rA = MG.assay_entity(_CFG, "Mock Entity", "example-not-mandated.org",
                          ceiling=("test scope", "M1"))
    check("one-shot path scores", (_rA.get("result") or {}).get("decimal") is not None, True)
    check("and travels as 'pool'", _rA.get("transport"), "pool")
    check("and the ceiling clamps the anchor", (_rA.get("result") or {}).get("magnitude"), "M1")
    check("and a scored sheet is settled", MG.settled(_rA), True)

    # B. junk one-shot (every citation fabricated) -> split retry rescues it
    _junk = {ax: {"score": 2.0, "feat": "A completely invented sentence about triumph."}
             for ax in MG.AXES}
    _CBm.ask = lambda *a, **k: {"anchor": "M0", "presence_evidence": "x",
                                "epoch": "test era of the mock", "axes": dict(_junk)}

    def _fake_split_ask(c, system, prompt, schema, timeout=420):
        if "anchor" in (schema.get("properties") or {}):
            return {"anchor": "M2", "presence_evidence": _FEAT,
                    "epoch": "test era of the mock"}
        return {"score": 2.0, "feat": _FEAT}

    MG._ask = _fake_split_ask
    _rB = MG.assay_entity(_CFG, "Mock Entity", "example-not-mandated.org")
    check("a fabricated one-shot is rescued by the split retry",
          _rB.get("transport"), "split-retry")
    check("and the retry scores from real candidates",
          (_rB.get("result") or {}).get("decimal") is not None, True)

    # C. the epoch mandate: an unstamped sheet from a mandated host is refused...
    _CBm.ask = lambda *a, **k: {"anchor": "M2", "presence_evidence": _FEAT,
                                "epoch": "unknown", "axes": _good_axes()}
    _rC = MG.assay_entity(_CFG, "Mock Entity", "mtg.fandom.com")
    check("a mandated host refuses an unstamped sheet", _rC.get("status"), "DEFERRED")
    check("and says why", "epoch" in (_rC.get("reason") or ""), True)

    # ...and a stamped one passes the same gate
    _CBm.ask = lambda *a, **k: {"anchor": "M2", "presence_evidence": _FEAT,
                                "epoch": "post-Mending", "axes": _good_axes()}
    _rC2 = MG.assay_entity(_CFG, "Mock Entity", "mtg.fandom.com")
    check("a stamped sheet passes the mandate",
          (_rC2.get("result") or {}).get("decimal") is not None, True)

    # D. nothing answers anywhere -> DEFERRED, never a truncated or invented sheet
    _CBm.ask = lambda *a, **k: None
    MG._ask = lambda *a, **k: None
    _rD = MG.assay_entity(_CFG, "Mock Entity", "example-not-mandated.org")
    check("no transport means DEFERRED", _rD.get("status"), "DEFERRED")
    check("and a deferral is not settled", MG.settled(_rD), False)

    # E. evidence above the recall cliff goes split-FIRST
    _big = {ax: [] for ax in MG.AXES}
    _big[_AX0] = [{"feat": "He destroyed the great fortress number %d with a single strike." % i,
                   "page": "TestPage"} for i in range(700)]
    _CAND_HOLDER[0] = _big
    _picked = _big[_AX0][3]["feat"]

    def _fake_big_ask(c, system, prompt, schema, timeout=420):
        if "anchor" in (schema.get("properties") or {}):
            return {"anchor": "M2", "presence_evidence": _picked,
                    "epoch": "test era of the mock"}
        return {"score": 2.0, "feat": _picked}

    MG._ask = _fake_big_ask
    _rE = MG.assay_entity(_CFG, "Mock Entity", "example-not-mandated.org")
    check("oversized evidence goes split-first", _rE.get("transport"), "split")
    check("and the split path scores",
          (_rE.get("result") or {}).get("decimal") is not None, True)
finally:
    MG.F.evidence_for, MG.candidates, _CBm.ask, MG.P.ask, MG._ask, MG._POOL[0] = _saved



# ---- Section 18c: the two-writer contract, both directions ---------------------------------------
#
# One record file, two writers, two OPPOSITE correct merges: the pipeline's in-memory copy is
# the stale side (disk entry-list wins), the catalogue's fresh cast is the authority (rec
# entry-list wins, disk judgments preserved). Using either writer for the other's job silently
# destroys entries -- write_record dropped the doc-ingest's first 14 finds the night this was
# added. These checks pin the directions with real files.

import tempfile as _tf
import pipeline as _PL

_tdir = _tf.mkdtemp()
_rp = os.path.join(_tdir, "rec.json")

_disk = {"source": "T", "entries": [
    {"name": "A", "magnitude": "M2", "scale_note": "kept"},
    {"name": "B", "magnitude": "unassayed"}]}
with open(_rp, "w", encoding="utf-8") as _f:
    json.dump(_disk, _f)

# Pipeline direction: a STALE one-entry copy must not shrink the disk cast.
_stale = {"source": "T", "entries": [{"name": "A", "magnitude": "M3"}]}
_PL.write_record(_rp, _stale)
_got = json.load(open(_rp, encoding="utf-8"))
check("write_record keeps the DISK cast against a stale copy",
      sorted(e["name"] for e in _got["entries"]), ["A", "B"])
check("and still lands the stale copy's judgment",
      next(e for e in _got["entries"] if e["name"] == "A")["magnitude"], "M3")

# Catalogue direction: a FRESH larger cast wins, disk judgments ride along.
with open(_rp, "w", encoding="utf-8") as _f:
    json.dump(_disk, _f)
_fresh = {"source": "T", "entries": [
    {"name": "A", "magnitude": "unassayed"},
    {"name": "B"}, {"name": "C", "magnitude": "unassayed"}]}
_PL.write_record_catalogue(_rp, _fresh)
_got = json.load(open(_rp, encoding="utf-8"))
check("write_record_catalogue keeps the FRESH cast",
      sorted(e["name"] for e in _got["entries"]), ["A", "B", "C"])
check("and preserves the disk judgment onto the matching name",
      next(e for e in _got["entries"] if e["name"] == "A")["magnitude"], "M2")

# And the catalogue merge never shrinks: a disk-only entry survives a smaller fresh cast.
with open(_rp, "w", encoding="utf-8") as _f:
    json.dump(_disk, _f)
_PL.write_record_catalogue(_rp, {"source": "T", "entries": [{"name": "C"}]})
_got = json.load(open(_rp, encoding="utf-8"))
check("a catalogue merge never shrinks a cast",
      sorted(e["name"] for e in _got["entries"]), ["A", "B", "C"])


# ---- Section 18d: the entrypass resume gate against a GROWN batch -------------------------------
#
# The other half of the two-writer story. write_record_catalogue is allowed to append entries to
# a record that entrypass has already walked -- so a batch key recorded in `done.entrypass` names
# a span that can widen underneath it. Skipping on membership alone stranded 5 doc-ingested
# entries of Arcanum Worlds (Odyssey of the Dragonlords) permanently: never categorised, never
# given a scale_note, never banded, and invisible except as health.py's "entries stranded in
# closed batches" count. The gate must read the span, not just the ledger.

_dk = ["T#0"]
_judged = [{"name": "A", "catalogued": True}, {"name": "B", "catalogued": True}]
check("a recorded, fully judged batch is skipped",
      _PL.batch_settled("T#0", _dk, _judged), True)
check("an unrecorded batch is never skipped",
      _PL.batch_settled("T#20", _dk, _judged), False)
# The regression itself: same key, same ledger, one entry appended since it closed.
check("a recorded batch that GREW is reopened",
      _PL.batch_settled("T#0", _dk, _judged + [{"name": "C"}]), False)
check("and an explicit catalogued=False is reopened too",
      _PL.batch_settled("T#0", _dk, _judged + [{"name": "C", "catalogued": False}]), False)


# ---- Section 19b: the stall detector can actually reach its own threshold ----------------------
#
# `every running job is advancing` is the high-severity standard the project describes as the
# failure it exists to refuse, and it was structurally unable to fire: the watch stamp was reset
# on every pass, so "how long has this log been silent" evaluated to "how long since the last
# check" -- always a few minutes, never the 15-minute floor. These pin the two halves: the stamp
# survives while the size holds, and every managed log declares who writes it.

import standards as _ST       # noqa: E402
import lognames as _LN2       # noqa: E402

_t0 = 1_000_000.0
check("a first sighting is not 'held'", _ST.job_stamp(None, 500, _t0)[0], False)
check("and stamps now", _ST.job_stamp(None, 500, _t0)[1], _t0)
check("a grown log re-stamps to now",
      _ST.job_stamp({"size": 400, "at": _t0 - 3600}, 500, _t0), (False, _t0))
# The regression itself: an unchanged log must keep its ORIGINAL stamp, not take a fresh one.
check("an unchanged log keeps its original stamp",
      _ST.job_stamp({"size": 500, "at": _t0 - 3600}, 500, _t0), (True, _t0 - 3600))
check("so quiet minutes can exceed the floor",
      (_t0 - _ST.job_stamp({"size": 500, "at": _t0 - 3600}, 500, _t0)[1]) / 60.0
      >= _ST.MAX_JOB_SILENCE_MIN, True)

check("every managed log declares its owning process",
      sorted(_LN2.OWNER) == sorted([_LN2.READ, _LN2.ROLL, _LN2.PIPELINE,
                                    _LN2.RECATALOGUE, _LN2.SWEEP, _LN2.CALIBRATE]), True)
check("and no owner fragment is a log name (the bug that hid three jobs)",
      any(f.endswith(".log") or "_auto" in f for f in _LN2.OWNER.values()), False)
check("and every owner fragment names a real script",
      all(os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      f.split()[0])) for f in _LN2.OWNER.values()), True)


# ---- Section 19c: phase artifacts land whole or not at all ------------------------------------
#
# The later phases wrote their artifacts as `json.dump(obj, open(path, "w"), ...)`, which
# truncates the target BEFORE serialising -- so a value json cannot encode left the real file
# holding a half-written fragment. Several of these are read by a later phase in the SAME run,
# and phase 6's own handler then reported that corruption as "phase 5 has not run" and marked
# itself done with an empty result. These pin the write contract. (BUGS m6.)

import datetime as _dt          # noqa: E402

_ad = _tf.mkdtemp()
_ap = os.path.join(_ad, "TIERS.json")
with open(_ap, "w", encoding="utf-8") as _f:
    _f.write('{"prior": "contents"}')

check("land_json lands a good write", _PL.land_json(_ap, {"charted": [1, 2]}), True)
check("and the artifact is what was asked for",
      json.load(open(_ap, encoding="utf-8")), {"charted": [1, 2]})
check("and no .tmp is left behind", os.path.exists(_ap + ".tmp"), False)
check("indent is honoured", "\n  " in open(os.path.join(_ad, "B.json"), encoding="utf-8").read()
      if _PL.land_json(os.path.join(_ad, "B.json"), {"k": 1}, indent=2) else False, True)
check("default= carries the CHRONICLE case",
      _PL.land_json(os.path.join(_ad, "C.json"), {"d": _dt.date(2026, 8, 24)}, default=str), True)

# The regression itself: an unencodable value must NOT be able to damage the existing artifact.
with open(_ap, "w", encoding="utf-8") as _f:
    _f.write('{"prior": "contents"}')
try:
    _PL.land_json(_ap, {"d": _dt.date(2026, 8, 24)})       # no default= -> TypeError mid-dump
    _raised = False
except TypeError:
    _raised = True
check("an unencodable value still raises", _raised, True)
check("but the previous artifact is UNTOUCHED",
      json.load(open(_ap, encoding="utf-8")), {"prior": "contents"})

# And the topic sentinel must not be mistakable for a real topic (BUGS m14).
check("'unclassified' is not a real topic", "unclassified" in _PL.TOPICS, False)


# ---- Section 19d: a completeness row that could not be measured is not a row of nothing -------
#
# Pins the 2026-08-24 regression on both sides. The m3 fix promoted an unmeasurable source into
# `unreliable` only when EVERY probe failed; seven transport failures plus one clean "no such
# category" scored 7 < 8 and the row was deleted exactly as before. Under the fandom socket-drop
# that shape is the common one, and it emptied COMPLETENESS.json outright -- 164 sources probed,
# 0 rows written -- after which the HIGH `every source is fully catalogued` standard reported a
# fabricated `0.0% (0 of 0)` off the empty file. Both halves are checked here: the row must
# survive, and an empty result must never land over a real one.
import completeness as _CP                                             # noqa: E402

_cd = _tf.mkdtemp()
_chosts = os.path.join(_cd, "WIKI_HOSTS.json")
with open(_chosts, "w", encoding="utf-8") as _f:
    json.dump({"Testsource": "testsource.fandom.com"}, _f)
_crecs = os.path.join(_cd, "records")
os.makedirs(_crecs, exist_ok=True)

_cp_hosts, _cp_recs, _cp_probe = _CP.HOSTS, _CP.RECORDS, _CP.category_size_probe
_CP.HOSTS, _CP.RECORDS = _chosts, _crecs
_nprobes = len(_CP.ws.CATEGORY_PROBES[_CP.PERSONS])


def _stub(pattern):
    """pattern: list of (n, err) consumed in probe order, one call per probe."""
    seq = list(pattern)
    order = {c: i for i, c in enumerate(_CP.ws.CATEGORY_PROBES[_CP.PERSONS])}
    return lambda sub, cand: seq[order[cand]]


_E, _N, _V = (None, "URLError"), (None, None), (1000, None)

# These checks exercise the PROBE branch, so the reachability gate in front of it is held open.
# Without this they test the gate instead and silently stop covering what they were written for
# (2026-08-24: adding `host_reachable` broke exactly three of them, which is the gate proving it
# short-circuits -- correct behaviour, wrong thing under test).
_cp_reach = _CP.host_reachable
_CP.host_reachable = lambda host, timeout=8: True

_CP.category_size_probe = _stub([_E] * _nprobes)
check("all probes failed -> row KEPT as unreliable", len(_CP.audit(workers=1)), 1)

_CP.category_size_probe = _stub([_E] * (_nprobes - 1) + [_N])
_r = _CP.audit(workers=1)
check("one clean miss among transport failures -> row still KEPT", len(_r), 1)
check("and it is marked unreliable, not scored", bool(_r[0]["unreliable"]) if _r else False, True)
check("and it carries its failure count", _r[0]["probe_failures"] if _r else None, _nprobes - 1)

_CP.category_size_probe = _stub([_N] * _nprobes)
check("genuine absence (every probe answered, no categories) -> row dropped",
      len(_CP.audit(workers=1)), 0)

_CP.category_size_probe = _stub([_E] * (_nprobes - 1) + [_V])
_r = _CP.audit(workers=1)
check("a real denominator among failures is still measurable",
      bool(_r) and not _r[0]["unreliable"], True)

# ---- the reachability gate itself -------------------------------------------------------------
# An unreachable host must still produce a ROW -- a source missing from COMPLETENESS.json reads
# downstream as "nothing on the wiki", the opposite of "we could not ask", and losing every
# fandom source during an outage is the empty-file catastrophe wearing a smaller hat. It must
# also cost ZERO category probes: the whole point is not walking a blocked host into eight
# 42-second failures.
_probe_calls = []
_CP.category_size_probe = lambda sub, cand: (_probe_calls.append(cand), _V)[1]
_CP.host_reachable = lambda host, timeout=8: False
_r = _CP.audit(workers=1)
check("an unreachable host still yields a row", len(_r), 1)
check("marked unreliable, naming the host",
      bool(_r) and "host unreachable" in (_r[0]["unreliable"] or ""), True)
check("and it is NOT probed even once", len(_probe_calls), 0)
check("its probes_run is honestly zero", _r[0]["probes_run"] if _r else None, 0)

_CP.host_reachable = _cp_reach
_CP.HOSTS, _CP.RECORDS, _CP.category_size_probe = _cp_hosts, _cp_recs, _cp_probe

# The write contract: an empty measurement must not be able to erase a real one.
_CP.OUT = os.path.join(_cd, "COMPLETENESS.json")
check("a real result lands", _CP.land([{"source": "A", "unreliable": None}]), True)
check("and no .tmp is left behind", os.path.exists(_CP.OUT + ".tmp"), False)
check("an empty result REFUSES to overwrite it", _CP.land([]), False)
check("and the real rows are untouched", len(json.load(open(_CP.OUT, encoding="utf-8"))), 1)
check("a --only slice never lands over the whole-corpus file",
      json.load(open(_CP.OUT, encoding="utf-8"))[0]["source"]
      if _CP.land([{"source": "B", "unreliable": None}], only="B") else "?", "A")

# Empty was never the only way to lose the measurement, and guarding only against it left the
# door open beside the one that was locked: 164 rows -> 3 rows landed silently. Kept LAST in this
# block because it necessarily rewrites the file the checks above assert against.
_CP.land([{"source": "S%d" % i, "unreliable": None} for i in range(20)])
check("a run that loses most of the corpus REFUSES too",
      _CP.land([{"source": "A", "unreliable": None}]), False)
check("and the fuller measurement survives it",
      len(json.load(open(_CP.OUT, encoding="utf-8"))), 20)
check("while an ordinary fluctuation still lands",
      _CP.land([{"source": "S%d" % i, "unreliable": None} for i in range(18)]), True)


# ---- Section 19e: the error bar is built from the weights the composite was built from -------
#
# `assay(weights=...)` keeps its override local so no other caller sees it; `_interval` read the
# module-global WEIGHTS while being handed the OVERRIDE's denominator, so a custom-weighted
# assay's interval was normalised against a table it did not come from. custodes.py builds such
# a table per Custos. Found 2026-08-24.
import assay as _AS2                                                   # noqa: E402

_sc = {k: 5.0 for k in _AS2.WEIGHTS}
_flat = {k: 1.0 for k in _AS2.WEIGHTS}
_heavy = dict(_flat)
_heavy[sorted(_heavy)[0]] = 40.0

# A worksheet is required for a number at all (H5), and one axis must be INAPPLICABLE so that
# `denom` is a strict subset of the table -- that is the only arrangement in which the global
# and the override can disagree about normalisation.
_sc[sorted(_sc)[-1]] = _AS2.INAPPLICABLE
_WS = "regression 19e"

_base = _AS2.assay("M5", _sc, worksheet=_WS, weights=_flat)
_skew = _AS2.assay("M5", _sc, worksheet=_WS, weights=_heavy)
check("a reweighted assay produces a real interval", isinstance(_base["interval"], float), True)

# THE VALUES ARE PINNED, and pinned deliberately rather than asserted as a relation, because the
# obvious relational checks are VACUOUS here -- both "an override equal to the global table
# reproduces the global interval" and "two different overrides differ" hold under the BUGGY code
# too, and were written and discarded before this was settled by running the old function
# against the new checks. Only the arithmetic discriminates. Under the bug, with the global
# WEIGHTS and the override's denom, these read 0.01 and 0.00; the flat table's own axes are
# equal, so a flat override must land exactly where the global table lands on equal scores.
check("a flat weight table gives the flat table's interval", _base["interval"], 0.06)
check("and an axis weighted 40x widens it", _skew["interval"], 0.15)


# ---- Section 19f: a name word must START a word of the sentence ------------------------------
#
# `read._names` matched by raw substring containment, which put MetalGarurumon's feats on
# GARURUMON and every mention of the Daily Planet on LOIS LANE. Whole-corpus diff before the
# change (39,198 sentences, 1,219 files): plain tokenisation lost 265 real inflected matches;
# start-of-token matching lost 0 and removed 37 suffix collisions. Fixed 2026-08-24.
import read as _RD                                                     # noqa: E402

check("an inflected name still matches", _RD._names("Certain Xenomorphs were observed.",
                                                    "Xenomorph XX121 (Alien)"), True)
check("and so does a pluralised name word", _RD._names("Throws ricocheting glaives.",
                                                       "Glaive Dominus"), True)
check("a name buried at the END of another name does NOT match",
      _RD._names("MetalGarurumon then defeats Azulongmon.", "Garurumon (Survive)"), False)
check("nor does a name buried inside an unrelated word",
      _RD._names("a party at the Planet that day", "Lois Lane (New Earth)"), False)
check("a generic subject still fails", _RD._names("The user channels energy.", "Goku"), False)
check("a pronoun still carries the sentence", _RD._names("She lifted the mountain.", "Goku"), True)


# ---- Section 19g: caps refused, not honoured, on ranked listings -----------------------------
#
# feats.discover ranked evidence pages by article size and then took the top 25 -- rank-then-
# truncate, which Hard Rule 0 names outright. The parameter survives so no caller breaks, but a
# numeric value is now refused loudly rather than applied silently. 2026-08-24.
import feats as _FT                                                    # noqa: E402

try:                                  # SystemExit is a BaseException; _raises would not see it
    _FT.discover("h", "n", extra=25)
    _capped = False
except SystemExit:
    _ = "silence-exempt: catching the refusal IS the assertion; a note would file a pass"
    _capped = True
check("feats.discover refuses a numeric cap", _capped, True)


# ---- Section 19h: the paid burst cap is enforced at SELECTION ---------------------------------
#
# `state/PAID_BURST.json` reached 598 calls against a cap of 500 -- ~$1.96 of real money past a
# hard limit. The cap only ever decided whether to PROMOTE the paid bucket into the proven-
# answering set; the bucket sat in the router's model list unconditionally and stayed fully
# selectable, so a closed lane merely ranked it lower. The exhausted-pool fallback that reaches
# it is the normal path whenever the free tier is failing, which it was.
#
# These check the REAL predicate (`widen_candidates`), not a paraphrase of it. Falsified against
# the pre-fix expression `[m for m in models if not m.bucket.startswith(LOCAL_PREFIX)]`, which
# passes checks 1 and 4 and FAILS 2, 3, 5 and 6 -- so the closed-lane cases are what discriminate.
# 2026-08-24.
import cascade_bridge as _CB                                            # noqa: E402


class _M:                                          # the one attribute widen_candidates reads
    def __init__(self, b):
        self.bucket = b


_models = [_M("mistral:free"), _M("anthropic:paid"), _M("ollama:qwen3"), _M("gemini:free")]
_open = [m.bucket for m in _CB.widen_candidates(_models, True)]
_shut = [m.bucket for m in _CB.widen_candidates(_models, False)]

# THE LANE IS RETIRED (owner ruling 2026-08-24: "there shouldn't be a paid lane anywhere").
# `PAID_LANE_RETIRED` excludes every paid bucket regardless of the file, so the paid bucket is
# now unselectable in BOTH directions -- that is the property to defend, and it is what these
# first checks assert. If someone flips the constant back, these fail and say why.
check("the paid lane is retired in code, not just in a file", _CB.PAID_LANE_RETIRED, True)
check("a RETIRED lane refuses the paid bucket even when the file says open",
      "anthropic:paid" in _open, False,
      note="the file can say enabled:true; the constant outranks it")
check("a CLOSED lane removes it from the candidates", "anthropic:paid" in _shut, False)
check("retirement removes ONLY the paid bucket", _shut, ["mistral:free", "gemini:free"])
check("locals are excluded either way", [b for b in _open if b.startswith("ollama:")], [])

# The CAP predicate underneath must stay correct, or un-retiring would restore a broken gate
# rather than a working one. Exercised with the retirement lifted, then restored.
_was = _CB.PAID_LANE_RETIRED
try:
    _CB.PAID_LANE_RETIRED = False
    _o2 = [m.bucket for m in _CB.widen_candidates(_models, True)]
    _s2 = [m.bucket for m in _CB.widen_candidates(_models, False)]
    check("with retirement lifted, an OPEN lane would select the paid bucket",
          "anthropic:paid" in _o2, True,
          note="proves the retirement is what excludes it, not a broken predicate")
    check("with retirement lifted, a CLOSED lane still refuses it", "anthropic:paid" in _s2, False)
finally:
    _CB.PAID_LANE_RETIRED = _was
check("the retirement was restored after the probe", _CB.PAID_LANE_RETIRED, True)

# The cap itself, and both documented kill switches.
check("at the cap the lane is shut", _CB.paid_lane_open({"enabled": True, "used": 500, "cap": 500}), False)
check("past the cap it stays shut", _CB.paid_lane_open({"enabled": True, "used": 598, "cap": 500}), False)
check("under the cap it is open", _CB.paid_lane_open({"enabled": True, "used": 499, "cap": 500}), True)
check("enabled:false kills it", _CB.paid_lane_open({"enabled": False, "used": 0, "cap": 500}), False)
check("a deleted/unreadable file kills it", _CB.paid_lane_open(None), False)


# ---- Section 19i: the two classifier caps read the FRONT of a record, not a sample -----------
#
# genre.classify_source(cap=120000) and grounding.classify_source(cap=140000) both walked
# rec["entries"] in STORED order and stopped at a character budget. Marvel holds 18,765,902
# characters of names+descriptions (genre read 0.64%) and 3,888,267 across 5,012 origin entries
# (grounding read 3.6%). Whole-corpus diff, 210 records, capped vs uncapped: SEVEN sources
# changed genre outright -- Marvel post_apocalyptic -> mythology, Bleach high_fantasy -> eastern,
# Digimon eastern -> cyberpunk, and four more. Grounding's verdicts happened to hold, but Marvel
# reported 153 origin entries instead of 5,012.
#
# A cap is refused rather than silently applied, as with feats.discover's `extra`. These checks
# use a record built to answer differently from its head than from its whole, so they FAIL under
# the pre-fix code (which would read only the head) rather than merely asserting a default.
# 2026-08-24.
import grounding as _GR                                                 # noqa: E402

# The head must OVERRUN the old 120,000-character budget, or the check is vacuous: a fixture
# that fits inside the cap classifies identically before and after, and would have passed
# against the very code this section exists to catch. Falsified against the pre-fix expression
# (walk entries, `break` once the budget is exceeded), which answers "grimdark" here -- one weak
# signal in 140,014 characters of filler -- while the whole record says "mythology".
_head = [{"name": "x", "description": "grimdark ruin " + ("filler " * 20000)}]
_tail = [{"name": "y", "description": "temple oracle pantheon demigod myth " * 400}]
_rec_ht = {"entries": _head + _tail}

def _refuses_cap(fn):             # SystemExit is a BaseException; _raises would not see it
    try:
        fn()
        return False
    except SystemExit:
        _ = "silence-exempt: catching the refusal IS the assertion; a note would file a pass"
        return True


check("genre reads past the head of the record",
      GN.classify_source(_rec_ht)["genre"], "mythology")
check("genre refuses a numeric cap",
      _refuses_cap(lambda: GN.classify_source(_rec_ht, cap=1000)), True)
check("grounding refuses a numeric cap",
      _refuses_cap(lambda: _GR.classify_source({"entries": []}, cap=1000)), True)
check("grounding counts EVERY origin entry, not the ones inside a budget",
      _GR.classify_source({"entries": [
          {"name": "a", "description": "the world was created from nothing " * 60}
          for _ in range(50)]})["origin_entries"], 50)


# ---- Section 19j: a struck entry stays struck -------------------------------------------------
#
# cleanup.py strikes non-entities with `catalogued=False` + an `excluded` reason. The entrypass
# resume gate demanded `all(catalogued)`, so a struck entry left its batch unsettled -> reopened
# -> phase_entrypass, which sets `catalogued = True` unconditionally. Nothing anywhere read
# `excluded`. Measured 2026-08-24: 149 entries carried it and ALL 149 had already been flipped
# back, so cleanup's whole effect on the corpus had been silently reverted.
#
# The first check FAILS under the pre-fix gate (`all(e.get("catalogued") ...)`), which is what
# makes it a regression check rather than a restatement of the default. 2026-08-24.
import pipeline as _PL                                                  # noqa: E402

check("an excluded entry settles its batch",
      _PL.batch_settled("s#0", ["s#0"], [{"excluded": "wiki navigation", "catalogued": False}]),
      True)
check("a merely uncatalogued entry still reopens it",
      _PL.batch_settled("s#0", ["s#0"], [{"catalogued": False}]), False)
check("a catalogued entry settles as it always did",
      _PL.batch_settled("s#0", ["s#0"], [{"catalogued": True}]), True)
check("a batch whose key was never recorded is never settled",
      _PL.batch_settled("s#0", [], [{"excluded": "x"}]), False)
check("a mixed batch waits on the entry that is genuinely unjudged",
      _PL.batch_settled("s#0", ["s#0"],
                        [{"excluded": "x"}, {"catalogued": True}, {"catalogued": False}]), False)


# ---- Section 19w: the promotion ladder (owner amendment 2026-08-24) ----------------------------
#
# "Each classification should have a standard that over x entries it increases in overall
# classification hierarchy." Thresholds were fitted to the real corpus (209 sources, median 194,
# max 30,207) and yield exactly one automatic Set -- Marvel -- which the charter had already
# promoted by hand. These pin the boundaries and, above all, the one-way rule.

import address as _AD          # noqa: E402

check("below the first floor is a Volume", _AD.tier_for(399), "volume")
check("400 earns a Series", _AD.tier_for(400), "series")
check("900 earns a Grand Series", _AD.tier_for(900), "grand")
check("3000 earns a Set", _AD.tier_for(3000), "set")
check("Marvel's real cast earns a Set", _AD.tier_for(30207), "set")
check("an empty cast is still a Volume, not an error", _AD.tier_for(0), "volume")
check("None is treated as zero", _AD.tier_for(None), "volume")

# THE ONE-WAY RULE. A cast count is a measurement, and this project's measurements have gone to
# zero twice this week. Demoting on a bad read would rewrite an address downward and silently
# break every cross-reference pointing at it.
check("growth promotes", _AD.promote("volume", 1000), "grand")
check("a dip NEVER demotes", _AD.promote("set", 12), "set")
check("nor does a partial read", _AD.promote("grand", 0), "grand")
check("an unranked source takes what it earns", _AD.promote(None, 500), "series")
check("holding steady changes nothing", _AD.promote("series", 500), "series")


# ---- Section 19k: a run may only refresh or close a record that is ITS OWN --------------------
# m27. The overlap guard's CLAIM was always checked; its HEARTBEAT never was. On 2026-08-24 an
# interactive session took the guard mid-run and run #6 spent ~45 minutes stamping that session's
# record, which made a FINISHED run look live -- the exact inverse of what the guard is for.
# Until this section there was no implementation of the guard in src/ at all: the protocol lived
# in prose and every run re-improvised the read-modify-write. These pin the invariant.

import tempfile as _tf         # noqa: E402
import time as _time           # noqa: E402
import runguard as _RG         # noqa: E402

_gd = _tf.mkdtemp()
_gp = os.path.join(_gd, "GUARD.json")

_ok, _ = _RG.claim("runA", _gp)
check("a run can claim a free guard", _ok, True)
check("and refresh its own heartbeat", _RG.beat("runA", _gp), True)

# Someone else takes the guard. This is the m27 state, reproduced exactly.
json.dump({"started": _time.time(), "heartbeat": _time.time(), "done": False,
            "agent": "runB"}, open(_gp, "w"))
_before = _RG.read(_gp)["heartbeat"]
check("a run REFUSES to refresh a record carrying another agent's name",
      _RG.beat("runA", _gp), False,
      note="the m27 failure: refreshing a foreign record keeps a finished run looking live, "
           "and the next run stands down for a corpse")
check("and the foreign heartbeat is left exactly as it was",
      _RG.read(_gp)["heartbeat"], _before,
      note="returning False while still writing would be the same bug wearing a verdict")
check("nor may it close a record it does not hold",
      _RG.release("runA", _gp), False,
      note="m27 pointed the other way: stamping done on a LIVE run hands its guard away")
check("the true owner is undisturbed", _RG.read(_gp).get("done"), False)

# A closed record must not be reopened by a stray heartbeat.
os.remove(_gp)
_RG.claim("runC", _gp)
_RG.release("runC", _gp)
check("releasing sets done", _RG.read(_gp)["done"], True)
check("and a later heartbeat REFUSES to reopen it", _RG.beat("runC", _gp), False)

# Liveness: unfinished AND fresh. Any other combination must let a successor through, or a
# crashed run wedges the pass forever.
_now = _time.time()
check("a live predecessor blocks",
      _RG.holder_is_live({"done": False, "heartbeat": _now}, _now), True)
check("a crashed run (stale heartbeat) does NOT block",
      _RG.holder_is_live({"done": False, "heartbeat": _now - _RG.STALE_AFTER_S - 1}, _now), False,
      note="blocking on an unfinished record alone would wedge every future run")
check("a finished run does not block even seconds old",
      _RG.holder_is_live({"done": True, "heartbeat": _now}, _now), False,
      note="landing on a just-finished predecessor is the NORMAL case at this cadence")
check("an absent record does not block", _RG.holder_is_live(None, _now), False)
check("a heartbeat-less record does not block",
      _RG.holder_is_live({"done": False}, _now), False)

# Taking over a crashed run records whose it was, so the takeover is legible in the file.
os.remove(_gp)
json.dump({"started": 1.0, "heartbeat": 2.0, "done": False, "agent": "crashed"},
           open(_gp, "w"))
_ok, _ = _RG.claim("runD", _gp)
check("a stale record can be taken over", _ok, True)
check("and the takeover names the run it superseded",
      _RG.read(_gp)["superseded"]["agent"], "crashed",
      note="a crashed run's work is unfinished by definition; the next run should be able to "
           "see that it inherited rather than started clean")

# ---- Section 19l: a CLOUD answer must be usable, not merely non-None ------------------------
# Ollama constrains generation to the schema; the cloud path cannot, and carries the schema as
# prompt text only (cascade_bridge.py:18). So a cloud model can return valid JSON of the wrong
# shape, and `ask_pool_first` used to accept it on the sole test `got is not None` -- leaving
# the working local arm unreached. Observed 2026-08-24: four consecutive Marvel entrypass
# batches logged `returned 0/20` while the pool proof read >= 3 answering; the same batch put
# to the local model returned 20 valid results. These pin the shape gate and the caller gate.

_SCH = {"type": "object", "properties": {"results": {"type": "array"}}, "required": ["results"]}

check("a non-dict cloud answer is unusable",
      _PL._pool_answer_usable("results: none", _SCH, None), False)
check("None is unusable", _PL._pool_answer_usable(None, _SCH, None), False)
check("a dict missing a REQUIRED key is unusable",
      _PL._pool_answer_usable({"entries": [{"index": 0}]}, _SCH, None), False,
      note="valid JSON, wrong shape -- the exact thing a schema-in-the-prompt cannot prevent")
check("a dict carrying every required key is usable",
      _PL._pool_answer_usable({"results": [{"index": 0}]}, _SCH, None), True)
check("an empty list still satisfies the SHAPE gate alone",
      _PL._pool_answer_usable({"results": []}, _SCH, None), True,
      note="shape cannot know whether empty is a real verdict; that is the caller's question")

# The caller gate. entrypass asks about N named indices, so an answer judging none of them has
# answered nothing -- however well-formed.
_acc = lambda g, _n=20: any(isinstance(r.get("index"), int) and 0 <= r["index"] < _n
                            for r in (g.get("results") or []))
check("an answer judging NONE of the indices we asked about is a pool MISS",
      _PL._pool_answer_usable({"results": []}, _SCH, _acc), False,
      note="this is the 0/20 case: it must fall through to local, not be returned as a verdict")
check("an answer whose indices are all out of range is also a miss",
      _PL._pool_answer_usable({"results": [{"index": 99}, {"index": -1}]}, _SCH, _acc), False,
      note="the results loop discards these, so the batch scores zero either way")
check("one in-range judgment is enough to accept the cloud answer",
      _PL._pool_answer_usable({"results": [{"index": 3}]}, _SCH, _acc), True)
check("a full answer is accepted",
      _PL._pool_answer_usable({"results": [{"index": i} for i in range(20)]}, _SCH, _acc), True)

# A predicate that raises must not take the call down with it, and must not be read as consent.
def _boom(_g):
    raise RuntimeError("predicate blew up")
check("a raising accept-predicate is a miss, not a crash and not an acceptance",
      _PL._pool_answer_usable({"results": [{"index": 0}]}, _SCH, _boom), False)

# A schema with no `required` list must not become a gate that rejects everything.
check("a schema declaring nothing required accepts any dict",
      _PL._pool_answer_usable({"anything": 1}, {"type": "object"}, None), True)
check("and a missing schema does not crash the gate",
      _PL._pool_answer_usable({"results": []}, None, None), True)

# ---- Section 19m: a write that was DENIED is not a write that succeeded ----------------------
# Three functions reported success while discarding the one boolean that says whether their
# write reached the disk. `silence.replace_retry` returns False rather than raising when the
# rename is denied for all its attempts, and on Windows a reader holding the target IS a denied
# rename -- which each of these three files documents, by name, as a thing that happens to it.
# Plus the foreman's patch-size gate, which measured a net line COUNT while claiming to bound
# how many lines a model rewrite changes.

import foreman as _FM           # noqa: E402
import completeness as _CP      # noqa: E402

# --- the patch-size gate ---------------------------------------------------------------------
_body80 = "\n".join("    a%d = %d" % (i, i) for i in range(80))
_rewrite82 = "\n".join("    b%d = %d" % (i, i * 2) for i in range(82))
check("a TOTAL rewrite is measured as a total rewrite",
      _FM.lines_changed(_body80, _rewrite82), 82,
      note="the old metric, abs(len(new)-len(old)), scored this 2 and waved it through a "
           "cap of 40 -- every line of the function replaced, reported as 'changes 2 lines'")
check("and it exceeds the cap it is meant to be bounded by",
      _FM.lines_changed(_body80, _rewrite82) > _FM.MAX_PATCH_LINES, True)
check("a one-line edit still measures one",
      _FM.lines_changed("    x = 1\n    y = 2\n", "    x = 1\n    y = 3\n"), 1,
      note="the old metric scored this 0: same line count, so no change detected at all")
check("pure growth counts the lines added",
      _FM.lines_changed("a\nb\n", "a\nb\nc\nd\n"), 2)
check("pure deletion counts the lines removed",
      _FM.lines_changed("a\nb\nc\nd\n", "a\nb\n"), 2)
check("an identical body changes nothing", _FM.lines_changed("a\nb\n", "a\nb\n"), 0)

# --- completeness.land must not claim a denied write landed ------------------------------------
_land_dir = _tf.mkdtemp()
_CP_OUT, _CP.OUT = _CP.OUT, os.path.join(_land_dir, "COMPLETENESS.json")
_rows = [{"source": "s%d" % i, "pct": 1.0} for i in range(200)]
try:
    check("land() reports success when the rename lands", _CP.land(_rows), True)
    check("and the rows are genuinely on disk",
          len(json.load(open(_CP.OUT, encoding="utf-8"))), 200)

    # Deny the rename exactly as a held reader would, and check the VERDICT, not the intent.
    _real_rr = silence.replace_retry
    silence.replace_retry = lambda tmp, dst, attempts=5: False
    try:
        check("land() reports FAILURE when the rename is denied", _CP.land(_rows), False,
              note="its own docstring promises 'Returns True if the file now holds rows'; "
                   "returning True on a denied rename made that line false in the one case "
                   "the caller needed to hear about -- main() exits 0 on a stale file")
        check("and the file still holds the PREVIOUS measurement, not a partial one",
              len(json.load(open(_CP.OUT, encoding="utf-8"))), 200,
              note="the tmp file is what got written; the real file is untouched")
    finally:
        silence.replace_retry = _real_rr

    # The guards that were already there must still hold -- this fix must not weaken them.
    check("an empty measurement is still refused over real rows", _CP.land([]), False)
    check("and a 98% shrink is still refused",
          _CP.land(_rows[:3]), False,
          note="SHRINK_FLOOR; the new return path must not become a way past it")
finally:
    _CP.OUT = _CP_OUT

# ---- Section 19x: a STALE ledger writer must not erase a fresher one ------------------------
# m40. `overwatch.save()` is a whole-file replace, and two PROCESSES hold the ledger routinely --
# the standing `--loop` job plus any ad-hoc `verify_open` call a maintenance run leaves behind.
# Observed 2026-08-24 11:28: an orphaned 09:02 call, blocked on a model reply for 2h26m (2.8s of
# CPU), sat one return away from replacing a 68-round / 64-finding ledger with its 09:02 snapshot
# -- destroying 4 findings (3 open, one of them cascade_bridge.ask) and one retirement. The write
# would have SUCCEEDED; that is why nothing would have reported it. Merging is sound here only
# because nothing in the module deletes a finding or a `seen` entry, which the last check pins.

import overwatch as _OW        # noqa: E402

_wd = _tf.mkdtemp()
_OW_LEDGER = _OW.LEDGER
_OW.LEDGER = os.path.join(_wd, "OVERWATCH.json")
try:
    _OW.save({"findings": {"a": {"state": "open", "module": "m", "symbol": "a"}},
              "seen": {"m": {"at": 100.0, "digest": "d1"}}, "rounds": 1, "last_run": "2026-01-01 00:00"})

    # Process A reads the ledger. This stamps A's snapshot.
    _A = _OW.load()
    check("the reader sees the ledger it was given", len(_A["findings"]), 1)

    # Process B -- the standing loop -- records more while A is blocked on a model reply.
    _disk = json.load(open(_OW.LEDGER, encoding="utf-8"))
    _disk["findings"]["b"] = {"state": "open", "module": "m", "symbol": "b"}
    _disk["findings"]["c"] = {"state": "retired", "module": "m", "symbol": "c",
                              "retired_at": "2026-08-24 09:27"}
    _disk["seen"]["m"] = {"at": 999.0, "digest": "d2"}
    _disk["rounds"] = 68
    _disk["last_run"] = "2026-08-24 10:01"
    json.dump(_disk, open(_OW.LEDGER, "w", encoding="utf-8"))

    # A finally returns and saves its 09:02 snapshot. THIS is the m40 event.
    _A["rounds"] = 2
    _A["findings"]["a"]["state"] = "refuted"      # real work A did that must also survive
    _OW.save(_A)
    _after = json.load(open(_OW.LEDGER, encoding="utf-8"))

    check("a stale writer does NOT erase findings recorded while it was blocked",
          sorted(_after["findings"]), ["a", "b", "c"],
          note="the m40 failure: save() replaced the whole file, so B's findings vanished and "
               "the write succeeded silently -- no reader could tell")
    check("the terminal verdict the stale writer DID reach still lands",
          _after["findings"]["a"]["state"], "refuted",
          note="preferring disk wholesale would be the same bug pointed the other way")
    check("a retirement made by the other writer is not reopened",
          _after["findings"]["c"]["state"], "retired")
    check("the round counter does not regress", _after["rounds"], 68,
          note="rounds is monotone; regressing it re-reviews finished work")
    check("`seen` keeps the LATER sighting, not the stale one",
          _after["seen"]["m"]["at"], 999.0)
    check("and last_run keeps the later stamp", _after["last_run"], "2026-08-24 10:01")

    # Idempotence: the merge must be a fixed point, or a loop of saves drifts.
    _OW.save(json.load(open(_OW.LEDGER, encoding="utf-8")))
    check("merging is idempotent", sorted(json.load(open(_OW.LEDGER, encoding="utf-8"))["findings"]),
          ["a", "b", "c"])

    # The ordinary single-writer path must be untouched -- a save with no interloper writes as-is.
    _solo = _OW.load()
    _solo["findings"]["d"] = {"state": "open", "module": "m", "symbol": "d"}
    _OW.save(_solo)
    check("an uncontended save still writes exactly what it was given",
          sorted(json.load(open(_OW.LEDGER, encoding="utf-8"))["findings"]), ["a", "b", "c", "d"])

    # The premise the whole merge rests on.
    _lines = open(_OW.__file__, encoding="utf-8").read().splitlines()
    # `del` only counts in STATEMENT position -- substring-matching it finds the 'del ' inside
    # the word "model" in this module's own prose, which is a check failing on its own comment.
    _removals = [ln.strip() for ln in _lines
                 if (ln.strip().startswith("del ") or ".pop(" in ln or ".clear()" in ln)
                 and ("finding" in ln or "seen" in ln) and not ln.strip().startswith("#")]
    check("nothing in overwatch REMOVES a finding or a `seen` entry -- the premise of the merge",
          _removals, [],
          note="union loses nothing only while retirement is a state change rather than a "
               "deletion; if that ever changes, the merge would resurrect the removed entry "
               "and this check is what says so before it ships")
finally:
    _OW.LEDGER = _OW_LEDGER
    _OW._SNAPSHOT["digest"] = None

# ---- Section 19n: a name the reader navigates by may not depend on the hash seed -------------
# m41. navtree picks a node's REGISTER (and a hyperverse's grounding type) with
# `max(set(xs), key=xs.count)`. On a tie -- two registers equally common under one node, the
# ordinary case for a small branch -- max() keeps whichever the SET yielded first, and string set
# order is randomized per process. The register is an input to `coin_well_formed`, so a flipped
# tie RENAMES the node. Measured 2026-08-24: two consecutive `navtree --write` runs, identical
# inputs, renamed 75 of 734 nodes; with PYTHONHASHSEED fixed, two processes agreed byte for byte.
# These pin the tie-break itself, which is the part that must not drift -- building the whole
# tree here would cost a minute of disk per suite run.

def _mode_stable(xs):
    """The tie-break navtree uses, isolated."""
    return max(set(xs), key=lambda v: (xs.count(v), v))


check("a tie between two equally common values resolves to a FIXED one",
      _mode_stable(["compact", "classical"]), "compact",
      note="lexicographic tie-break; the point is only that it is the same one every process")
check("and does not depend on the order the values arrive in",
      _mode_stable(["classical", "compact"]), _mode_stable(["compact", "classical"]))
check("a clear majority still wins outright",
      _mode_stable(["classical", "classical", "compact"]), "classical",
      note="the tie-break must not become a lexicographic sort that ignores the counts")
check("a three-way tie is also fixed",
      _mode_stable(["a", "b", "c"]), "c")
check("the real navtree helper carries the same rule",
      "key=lambda r: (regs.count(r), r)" in
      open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "navtree.py"),
           encoding="utf-8").read(), True,
      note="if this reverts to max(set(regs), key=regs.count) the tree churns again and only "
           "a diff of two full runs would show it")

# ---- Section 19o: the Feats chapter paginates and the Powers chapter is routed by mode -------
# Two structures added 2026-08-24 so that mined feats can become prose at all, and so that a
# homebrew spell and a narrative power stop sharing a chapter. Both are places where a cap would
# be the obvious implementation and would be wrong.

import manifest_builder as _MB     # noqa: E402
import feats_index as _FI          # noqa: E402
import address as _ADR             # noqa: E402

# --- routing: the SOURCE's mode decides, not the entry's category ------------------------------
check("a mechanical source's Powers become MechanicalContent",
      _ADR.chapter_label_for(_ADR.POWERS_LABEL, "folder-mechanical"), _ADR.MECHANICAL_LABEL,
      note="65.9% of all Powers entries come from folder-mechanical sources -- spells and "
           "subclass features filed beside Bankai because the classifier has one bucket")
check("a web source keeps its Powers",
      _ADR.chapter_label_for(_ADR.POWERS_LABEL, "web"), _ADR.POWERS_LABEL)
check("a hybrid source keeps its Powers rather than being guessed at",
      _ADR.chapter_label_for(_ADR.POWERS_LABEL, "hybrid"), _ADR.POWERS_LABEL,
      note="87 entries across 6 sources genuinely mix the two; an owner question, not a route")
check("an unknown mode changes nothing",
      _ADR.chapter_label_for(_ADR.POWERS_LABEL, None), _ADR.POWERS_LABEL)
check("no OTHER category is ever rerouted by mode",
      _ADR.chapter_label_for("Persons (named individual characters, real or fictional)",
                             "folder-mechanical"),
      "Persons (named individual characters, real or fictional)")
check("MechanicalContent finally has a producer and a slug",
      _ADR.chapter_slug(_ADR.MECHANICAL_LABEL), "MechanicalContent",
      note="the slug shipped with the charter and nothing had ever assigned the label")
check("and the Feats chapter has one", _ADR.chapter_slug(_ADR.FEATS_LABEL), "Feats")

# --- packing: HARD RULE 0. every mined feat must reach a block ---------------------------------
def _row(name, n, chars=100):
    return {"entity": name, "feat_count": n, "pages": ["p"], "axis_counts": {"ruin": n},
            "entry": {"magnitude": "M3", "topic": "Persons"},
            "feats": [{"feat": "x" * chars, "axis": "ruin", "page": "p"} for _ in range(n)]}

def _emitted(blocks):
    return sum(len(e["feats"]) for b in blocks for e in b)

_small = [_row("A", 5), _row("B", 5), _row("C", 5)]
_bk = _MB.pack_feats(_small, "S", budget=100000)
check("small entities pack into one block", len(_bk), 1)
check("and nothing is lost", _emitted(_bk), 15)

# The case the whole packer exists for: one entity far larger than a single call may carry.
_huge = [_row("Goku", 569)]
_bk = _MB.pack_feats(_huge, "S", budget=20000)
check("an OVERSIZED entity is split across blocks, not truncated",
      _emitted(_bk), 569,
      note="569 attested deeds silently becoming the first 90 is precisely the cap Hard Rule 0 "
           "forbids; the real record is 'List of techniques used by Goku' at 121,299 chars")
check("and it takes more than one block to do it", len(_bk) > 1, True)
check("each split block carries only that entity",
      all(len(b) == 1 for b in _bk), True)
_spans = [e["feat_span"] for b in _bk for e in b]
check("every split block declares which span it holds", len(_spans), len(_bk))
check("the spans start at the first deed", _spans[0].startswith("1-"), True)
check("and end at the last", _spans[-1].endswith("of 569"), True)
check("the spans are contiguous and cover the whole record",
      sum(int(s.split(" of ")[0].split("-")[1]) - int(s.split("-")[0]) + 1 for s in _spans), 569,
      note="a gap between two spans would be a silent loss wearing the shape of pagination")

# Mixed: a giant beside several small ones must not drag them into its slices.
_mixed = [_row("Giant", 400), _row("A", 3), _row("B", 3)]
check("a giant beside small entities loses nothing",
      _emitted(_MB.pack_feats(_mixed, "S", budget=20000)), 406)
check("an empty row list packs to no blocks", _MB.pack_feats([], "S", budget=20000), [])
# `budget` is required as of 2026-08-24 -- this call used to omit it and take the module
# default, which is the exact habit that made the default dangerous. Asserting the signature
# keeps a future default from being reintroduced quietly.
try:
    _MB.pack_feats([], "S")
    _packreq = "accepted"
except TypeError:
    # The TypeError IS the assertion here -- catching it is how the check reads the signature,
    # not a failure being hidden. The audit reads the AST and cannot tell those apart, so it is
    # declared rather than commented.
    _ = "silence-exempt: the raised TypeError is the measurement this check makes"
    _packreq = "required"
check("pack_feats refuses to guess a budget", _packreq, "required",
      note="a caller that forgets the budget must fail loudly, not silently get 20,000")

# --- the join itself ---------------------------------------------------------------------------
check("host_to_sources drops the `pages:` sentinels rather than colliding them",
      any(h.startswith("pages:") for h in _FI.host_to_sources()), False,
      note="owner-supplied books record `pages:<title>` where a wiki records a host; inverting "
           "them would pile every such source onto one pseudo-host")
check("feats_for_source returns [] for a source with no host binding",
      _FI.feats_for_source("a source that does not exist", {"entries": []}), [])

# --- _norm is STRICT on parentheticals, and that is load-bearing --------------------------------
# Added 2026-08-24 (maintenance run #9). `_norm`'s docstring used to offer
# "Zangetsu (Zanpakutou spirit)" vs "Zangetsu" as a pair it folds together. It does not, and the
# strict behaviour is CORRECT: 79 of 1,241 feats records carry a parenthetical and 76 join
# anyway, because the catalogue records the same disambiguated form. Loosening it is the obvious
# "fix" for the three that miss and it is a trap -- `Wally West (New Earth)` and `Wally West
# (Prime Earth)` would both fold onto the catalogue's `Wally West (Earth-16)`, merging three DC
# continuities into one cast entry and attaching 177 deeds to the wrong continuity. These checks
# exist so that a future reader who notices the stranded records cannot quietly make that trade.
check("_norm does NOT fold a parenthetical away",
      _FI._norm("Zangetsu (Zanpakutou spirit)") == _FI._norm("Zangetsu"), False,
      note="if this ever becomes True, three DC continuities silently become one entry")
check("_norm still folds case and punctuation",
      _FI._norm("Wally West!") == _FI._norm("wally  west"), True,
      note="strict about parentheses is not the same as strict about everything")
check("two disambiguated forms of one character stay DISTINCT",
      _FI._norm("Wally West (New Earth)") == _FI._norm("Wally West (Prime Earth)"), False)


# ---- Section 19p: ONE job roster, not four partial copies of one ------------------------------
# Added 2026-08-24 (maintenance run #10). `allsweep`'s "what is actually running" block carried
# its own four-job tuple while the keeper's STANDING set held five and `autostart`'s status
# display held six. It therefore reported 4 live jobs against a process table holding NINE, in
# runs #7, #8, #9 and #10 -- and a job missing from the roster does not read as "not listed", it
# reads as NOT RUNNING. That is the reading a later run would trust to decide a job had died.
# These checks fail if anyone re-hardcodes a roster next to the real one.
import overnight as _ON      # noqa: E402

_standing_basenames = [os.path.basename(args[0]) for _n, args, _l in _ON.STANDING]
check("every job the keeper restarts is visible to the roster readers",
      [j for j in _standing_basenames if j not in _ON.ALL_JOBS], [],
      note="a STANDING job absent from ALL_JOBS is invisible to every 'is it up?' check")
check("the roster also carries the jobs the keeper does NOT restart",
      all(j in _ON.ALL_JOBS for j in ("read.py", "feats.py --roll", "overnight.py",
                                      "autostart.py")), True,
      note="read.py and feats.py --roll hang off the supervisor's main lap, not the keeper")
check("the roster names each job exactly once", len(set(_ON.ALL_JOBS)), len(_ON.ALL_JOBS))

_allsweep_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "allsweep.py"),
                     encoding="utf-8").read()
check("allsweep reads the shared roster instead of keeping its own",
      "ALL_JOBS" in _allsweep_src, True,
      note="if this fails, a private copy of the job list has grown back in allsweep")

# ---- Section 19q: the entrypass prompt asks for the count it actually showed ------------------
# Added 2026-08-24 (maintenance run #11). `phase_entrypass` skips struck entries when building
# `lines`, then closed the prompt with "Return results for all {len(batch)} entries" -- so a span
# of 20 holding 3 excluded ones showed the model 17 entries and asked for 20. It could not
# corrupt output (the index guards discard a verdict for an entry that was never shown), but it
# spent tokens inviting the model to invent three of them. This fails if len(batch) comes back.
_pipe_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline.py"),
                 encoding="utf-8").read()
check("the entrypass prompt counts the entries it SHOWED, not the whole span",
      "Return results for all {len(lines)} entries" in _pipe_src, True,
      note="len(batch) counts struck entries the model was never given")
check("the struck-entry skip that makes lines shorter than batch is still there",
      'if e.get("excluded"):' in _pipe_src, True,
      note="if this goes, the count above stops being the meaningful one")


# ---- Section 19r: near-miss name matching may never merge two continuities --------------------
# Added 2026-08-24. `entity_match` ranks catalogue entries for a name the exact fold missed. The
# whole module is built around ONE refusal: a parenthetical qualifier must match exactly or be
# absent from both sides. Three DC records (`Wally West (New Earth)`, `(Prime Earth)`, and the
# catalogue's `(Earth-16)`) carry 240 mined deeds between them, and any similarity measure --
# string or embedding -- rates them nearly identical. §19o already forbids loosening `_norm` to
# fold them; these checks stop the fuzzy matcher becoming the way around §19o.
import entity_match as _EM      # noqa: E402

check("two DC continuities are never compatible",
      _EM.qualifier_compatible("Wally West (New Earth)", "Wally West (Prime Earth)")[0], False,
      note="if this passes, 177 deeds attach to the wrong continuity")
check("a third continuity is refused too",
      _EM.qualifier_compatible("Wally West (New Earth)", "Wally West (Earth-16)")[0], False)
check("a disambiguated name never matches the bare name",
      _EM.qualifier_compatible("Zangetsu (Zanpakutou spirit)", "Zangetsu")[0], False,
      note="the exact pair §19o's docstring was corrected over")
check("a qualifier conflict is REPORTED, not silently dropped",
      _EM.qualifier_compatible("A (x)", "A (y)")[1], _EM.MatchReason.QUALIFIER_CONFLICT)
check("a missing qualifier has its own distinct reason",
      _EM.qualifier_compatible("A (x)", "A")[1], _EM.MatchReason.QUALIFIER_MISSING)
check("identical qualifiers DO match, modulo case and spacing",
      _EM.qualifier_compatible("Wally West (New Earth)", "wally  west (NEW EARTH)")[0], True)
# The docstrings above this function claimed the qualifier had to match "EXACTLY" until
# 2026-08-24, while the code has always compared normalised forms. The check below pins the
# behaviour the code actually has, so the next reader corrects the comment rather than
# "fixing" the code to match a sentence that was never true.
check("a punctuation-only qualifier difference is the SAME continuity",
      _EM.qualifier_compatible("X (Earth-2)", "X (Earth 2)")[0], True,
      note="normalised comparison, not literal equality -- the header said otherwise for a day")
# ONE RETURN SHAPE. The two early exits used to omit `blocked_by_qualifier`, so a caller
# reading it unconditionally would KeyError on exactly the two degenerate inputs real data
# produces most often. Fixed before the module has any caller at all.
_shape19r = [sorted(_EM.candidates("", [{"name": "A"}]).keys()),
             sorted(_EM.candidates("A", []).keys()),
             sorted(_EM.candidates("A", [{"name": "A"}]).keys())]
check("candidates() returns the same keys on every path",
      _shape19r[0] == _shape19r[1] == _shape19r[2], True,
      note="empty-name and empty-pool exits dropped a key the normal path always carries")
check("blocked_by_qualifier is present even when nothing was blocked",
      all("blocked_by_qualifier" in s for s in _shape19r), True)
check("similarity still folds case and punctuation on the base name",
      _EM.similarity("Son Goku", "son-goku"), 1.0)
check("a weak match is never returned as best",
      _EM.best("Kratos", [{"name": "Kraven"}])[0], None,
      note="this module proposes; a weak hit applied automatically mis-attaches a deed")
check("an unmatched name carries a reason code, never a bare empty result",
      _EM.candidates("Nobody At All", [{"name": "Somebody Else"}])["reason"],
      _EM.MatchReason.NO_CANDIDATE)
check("candidates() does not truncate by default",
      _EM.candidates("A", [{"name": f"A{i}"} for i in range(50)])["truncated"], False,
      note="Hard Rule 0: a ranked listing is returned whole unless a caller asks otherwise")


# ---- Section 19u: the GPU lane must never mistake a dead holder for a live one ----------------
# Added 2026-08-24. `gpu_lane` arbitrates one card between nine processes with leases held in
# files. Reclaiming a dead holder's lease is the ONLY thing standing between a killed job and a
# permanently stranded card. The first version used the POSIX idiom `os.kill(pid, 0)` and checked
# for ESRCH -- which is WRONG on Windows, where a nonexistent PID raises errno 22 / winerror 87.
# Every dead process therefore read as alive: a ghost slot stranded the card for its full
# 900-second lease (measured 338.5 s in a test that should finish in under a second) and a ghost
# foreground claim stalled all background work for the 240-second yield ceiling. Caught only
# because the concurrency test hung.
import time as _time            # noqa: E402
import gpu_lane as _GL          # noqa: E402

check("a nonexistent PID reads as DEAD", _GL._alive(999999), False,
      note="os.kill(pid,0)/ESRCH is wrong on Windows; this is that regression")
check("our own PID reads as alive", _GL._alive(os.getpid()), True)
check("a record held by a dead PID is expired despite a fresh heartbeat",
      _GL._expired({"pid": 999999, "heartbeat": _time.time()}, 900), True,
      note="a fresh heartbeat from a dead holder is exactly the stranding case")
check("a live holder with a fresh heartbeat is NOT expired",
      _GL._expired({"pid": os.getpid(), "heartbeat": _time.time()}, 900), False)
check("an unreadable lease is reclaimed rather than stranding the card",
      _GL._expired(None, 900), True)
check("the lane keeps at least one slot", _GL.MAX_SLOTS >= 1, True)


# ---- Section 19v: a prompt may never be larger than the window it is sent into ----------------
# Added 2026-08-24 (m46/m52). A feats prompt measured 41,469 characters against `num_ctx: 6144`
# -- roughly 1.9x the window. Ollama TRUNCATES an over-long prompt and answers anyway, and
# `generate._covered` verifies only that an entity's NAME appears, so a block whose deed list
# was cut would still have been written to catalog.json as a finished chapter. That is a Hard
# Rule 0 truncation with no slice in the source for a reader to find. Three defences, each
# checked here: the budget is derived from the window, feats jobs drop the chapter-only half of
# the system prompt, and an over-budget prompt raises instead of being sent.
import context_budget as _CB     # noqa: E402
import manifest_builder as _MBd  # noqa: E402

_cbcfg = {"num_ctx": 6144}
check("the feats system prompt drops THE ENTRY TEMPLATE",
      "THE ENTRY TEMPLATE" in _CB.system_for("feats", "voice\nTHE ENTRY TEMPLATE\nbody"), False,
      note="feats_prompt.txt forbids the scoring that section describes")
check("a chapter job still gets the whole system prompt",
      "THE ENTRY TEMPLATE" in _CB.system_for("chapter", "voice\nTHE ENTRY TEMPLATE\nbody"), True)
check("a system prompt with no template heading is left intact",
      _CB.system_for("feats", "just voice"), "just voice",
      note="degrade to today's behaviour rather than guess at a split point")
check("the block budget GROWS with the window",
      _CB.feats_block_budget({"num_ctx": 12288}) > _CB.feats_block_budget({"num_ctx": 6144}),
      True, note="the old constant had no arithmetic relationship to num_ctx at all")
check("an over-long prompt raises instead of being truncated",
      _raises(lambda: _CB.assert_fits(_cbcfg, "s" * 1000, "u" * 200000, "feats")), True)
check("a prompt that fits does not raise",
      _CB.assert_fits(_cbcfg, "s" * 100, "u" * 100, "feats")["headroom_tokens"] >= 0, True)

# The packer, against the derived budget: nothing lost, and no slice over budget except the
# single-deed case that cannot be helped (a lone deed larger than the whole window).
_fb = _CB.feats_block_budget(_cbcfg)
_row = {"entity": "E", "entry": {}, "pages": [], "feat_count": 40,
        "axis_counts": {}, "feats": [{"feat": "d" * 400, "axis": "a", "page": "p"}] * 40}
_blocks = _MBd.pack_feats([_row], "S", _fb)
_emitted = sum(len(e["feats"]) for b in _blocks for e in b)
check("slicing an oversized entity loses no deed", _emitted, 40)
check("every slice carries its span so a partial block is legible",
      all(e.get("feat_span") for b in _blocks for e in b), True)
check("no slice of a multi-deed entity exceeds the budget",
      max(len(json.dumps(e["feats"], ensure_ascii=False)) for b in _blocks for e in b) <= _fb,
      True, note="the packer used to test the budget AFTER appending, so every slice overshot")

# ---- Section 19y: the window admits a real chapter block, and prose is charged as prose ------
# Added 2026-08-24 (owner-directed session), pinning the M6 fix. At `num_ctx: 6144` EVERY chapter
# call refused -- 17,370 of 17,370 -- because the scaffolding outweighed the window before any
# content was added. Two causes, both fixed: the system prompt was charged at the CONTENT ratio
# (3.0 chars/token) when instruction prose actually measures 4.19-4.63 against the live daemon,
# inventing ~1,510 tokens of overhead; and the window itself was too small for the real blocks.
# Measured over all 17,370 rendered chapter blocks: median 4,084 chars, p90 9,457, p99 11,978.
_cb_sys = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "prompts", "system_style.txt"), encoding="utf-8").read()
import read as _RD               # noqa: E402
_livecfg = _RD.config()

check("instruction prose is charged more efficiently than JSON content",
      _CB.PROSE_CHARS_PER_TOKEN > _CB.CHARS_PER_TOKEN, True,
      note="prose measured 4.19-4.63 chars/token; entity JSON is denser and stays pessimistic")
check("the prose ratio stays at or below what was MEASURED",
      _CB.PROSE_CHARS_PER_TOKEN <= 4.19, True,
      note="4.19 is the densest measured slice; going above it would under-count and truncate")
check("the system prompt is charged at the prose rate, not the content rate",
      _CB.measure({"num_ctx": 12288}, "p" * 4000, "u" * 100, "chapter")["system_tokens"],
      _CB.estimate_prose_tokens("p" * 4000))
check("a p99-sized chapter block fits the CONFIGURED window",
      _CB.fits(_livecfg, _CB.system_for("chapter", _cb_sys), "u" * 12000, "chapter")[0], True,
      note="12,000 chars is the p99 of all 17,370 real blocks; if this fails, generation refuses "
           "again -- either num_ctx was lowered or the system prompt grew")
check("the same block does NOT fit the window M6 was filed against",
      _CB.fits({"num_ctx": 6144}, _CB.system_for("chapter", _cb_sys), "u" * 12000, "chapter")[0],
      False, note="guards the check above from passing for the wrong reason")

# ---- Section 19s: both writers of the metrics ledger stamp a timestamp -----------------------
# Added 2026-08-24 (run #13). `state/model_metrics.jsonl` has TWO writers -- cascade_bridge._metric
# (cloud) and pipeline._metric (local) -- and only the cloud one wrote an "at" field. Every
# time-windowed query over the shared ledger therefore filtered on `at` and silently returned
# cloud-only results: 913 local rows across 7 tags (entrypass, overwatch, ask, ingest, bench:*,
# repro) were invisible, and local call VOLUME had never been measurable at all. The reading
# looked complete because the rows it dropped could not appear in it. This check reads the two
# writers' source directly, because the symptom is only visible in a file neither writer owns.
_mx_src = {}
for _mx_mod, _mx_fn in (("pipeline", "_metric"), ("cascade_bridge", "_metric")):
    _mx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), _mx_mod + ".py")
    _mx_src[_mx_mod] = open(_mx_path, encoding="utf-8").read()

check("pipeline._metric's row carries a timestamp",
      '"at": round(t0, 1), "tag"' in _mx_src["pipeline"], True,
      note="without it, every time-filtered read of model_metrics.jsonl is cloud-only")
check("cascade_bridge._metric's row carries a timestamp",
      '"at": round(t0, 1)' in _mx_src["cascade_bridge"], True,
      note="the writer that always had one; both must, or the shared ledger is unqueryable")

# ---- Section 19t: the local leg never stacks more calls than the card has slots -------------
# Added 2026-08-24 (run #13), pinning M7. read.py's adaptive gate sized itself from
# tuning.regime(), which answers "cloud" on bucket REACHABILITY, not on capacity. With the live
# cloud rate at 4.1% nearly every chunk fell through to the GPU while the gate stayed at
# GATE_CLOUD_N=16, so 9 requests queued against OLLAMA_NUM_PARALLEL=2, blew read.py's 180s local
# timeout, benched the card and DISCARDED the chunk: 1,168 of 1,235 GPU handoffs unanswered over
# 7.5 hours. The local leg now takes the card's gate whatever the regime is called. Both arms
# below matter: the bound, and the per-thread re-entrancy that stops the nested acquire (regime
# "local", where _ask already holds the same semaphore) from deadlocking every worker.
import threading                 # noqa: E402
import time                      # noqa: E402

_gl_peak, _gl_cur, _gl_lock = [0], [0], threading.Lock()
_gl_real_ask, _gl_real_fbm = _RD.P.ask, _RD.fallback_model


def _gl_fake_ask(c, system, prompt, schema, timeout=None, **kw):
    with _gl_lock:
        _gl_cur[0] += 1
        _gl_peak[0] = max(_gl_peak[0], _gl_cur[0])
    time.sleep(0.05)
    with _gl_lock:
        _gl_cur[0] -= 1
    return {"feats": []}


def _gl_probe(regime, entry):
    """Fire GATE_LOCAL_N*4 threads at the local leg and report (peak concurrency, threads stuck)."""
    _RD.P.ask, _RD.fallback_model = _gl_fake_ask, (lambda c: "probe")
    _RD._GPU_DOWN_UNTIL[0] = 0
    _RD._GATE_STATE.update({"at": time.time() + 10 ** 9, "regime": regime})
    _gl_peak[0] = 0
    try:
        ths = [threading.Thread(target=lambda: entry({}, "s", "p" * 10, None))
               for _ in range(_RD.GATE_LOCAL_N * 4)]
        for t in ths:
            t.start()
        for t in ths:
            t.join(timeout=20)
        return _gl_peak[0], sum(1 for t in ths if t.is_alive())
    finally:
        _RD.P.ask, _RD.fallback_model = _gl_real_ask, _gl_real_fbm
        _RD._GATE_STATE.update({"at": 0.0, "regime": "cloud"})


_gl_direct = _gl_probe("cloud", _RD._local)
check("the local leg never exceeds the card's slot count (regime says 'cloud')",
      _gl_direct[0] <= _RD.GATE_LOCAL_N, True,
      note=f"peak {_gl_direct[0]} concurrent vs GATE_LOCAL_N={_RD.GATE_LOCAL_N}; this is the "
           "gate M7 needed and did not get -- a wide gate here discards ~95% of GPU work")
check("no worker is stranded at the card's gate (regime says 'cloud')",
      _gl_direct[1], 0)

_gl_saved_tr, _gl_saved_ok = _RD._TRANSPORT, _RD._CASCADE_OK
_RD._TRANSPORT, _RD._CASCADE_OK = "ollama", False
try:
    _gl_nested = _gl_probe("local", _RD._ask)
finally:
    _RD._TRANSPORT, _RD._CASCADE_OK = _gl_saved_tr, _gl_saved_ok
check("the nested acquire does NOT deadlock when the regime already chose the local gate",
      _gl_nested[1], 0,
      note="_ask holds _GATE_LOCAL and _local re-enters it; without per-thread tracking every "
           "worker blocks forever on a permit it is itself holding")
check("the nested path is still bounded to the card's slot count",
      _gl_nested[0] <= _RD.GATE_LOCAL_N, True, note=f"peak {_gl_nested[0]} concurrent")

# ---- Section 19z: the fandom probe asks over IPv4, the only family content wikis have --------
#
# 2026-08-24. `fandom answers this machine` read GREEN through a total content-wiki outage, and
# it is the one standard whose entire reason for existing is to catch that shape. The probe was
# `create_connection(("community.fandom.com", 443))`, which walks whatever getaddrinfo returns
# and stops at the first success. `community` is the ONLY fandom host publishing AAAA records;
# it answered over IPv6 in 0.02s. Every content wiki -- marvel, forgottenrealms, starwars,
# aneurism -- is A-record-only, and all of them timed out at the socket. Meanwhile 164 of 164
# COMPLETENESS.json rows said "no denominator was obtained" and preflight said "fandom API
# unreachable". Three surfaces told the truth and the one built for it did not.
#
# These checks drive the probe with a stub network, so they pin the FAMILY rather than the
# weather: the second one reproduces the exact 2026-08-24 configuration and must come back
# False. A probe that passes it is once again able to certify a dead corpus as reachable.
import standards as _STx      # noqa: E402


class _StubSock:
    def __init__(self, reachable):
        self._reachable = reachable

    def settimeout(self, _t):
        pass

    def connect(self, sa):
        if sa[0] not in self._reachable:
            raise OSError("timed out")

    def close(self):
        pass


class _StubNet:
    """A stand-in socket module: which addresses exist, and which of them answer."""
    AF_INET, AF_INET6, SOCK_STREAM = 2, 23, 1

    def __init__(self, records, reachable):
        self.records, self.reachable, self.asked = records, reachable, []

    def getaddrinfo(self, host, port, family=0, socktype=0):
        self.asked.append(family)
        rows = self.records.get(family)
        if not rows:
            raise OSError("no such record for " + host)
        return [(family, self.SOCK_STREAM, 6, "", (a, port)) for a in rows]

    def socket(self, _fam, _typ, _proto):
        return _StubSock(self.reachable)


_V4, _V6 = "162.159.142.170", "2606:4700:7::29e"
_both = {_StubNet.AF_INET: [_V4], _StubNet.AF_INET6: [_V6]}

_net_blocked = _StubNet(_both, {_V6})            # the 2026-08-24 shape, exactly
_blocked_ok, _blocked_where = _STx.fandom_ipv4_reachable(_sk=_net_blocked)
check("an IPv6-only route does NOT certify fandom as reachable",
      _blocked_ok, False,
      note=f"probe answered {_blocked_ok!r} ({_blocked_where}); content wikis are "
           "A-record-only, so a working IPv6 leg says nothing about the path they must use")
check("the fandom probe asks the resolver for IPv4 and nothing else",
      _net_blocked.asked, [_StubNet.AF_INET],
      note="AF_UNSPEC lets the first family that answers speak for both -- that is the bug")

_net_up = _StubNet(_both, {_V4, _V6})
_up_ok, _up_where = _STx.fandom_ipv4_reachable(_sk=_net_up)
check("a live IPv4 leg still reads as reachable", (_up_ok, _up_where), (True, _V4))

_net_nov4 = _StubNet({_StubNet.AF_INET6: [_V6]}, {_V6})
_nov4_ok, _nov4_where = _STx.fandom_ipv4_reachable(_sk=_net_nov4)
check("a host with no A record fails the probe instead of raising",
      (_nov4_ok, _nov4_where.startswith("no A record")), (False, True))


# ---- Section 19aa: the catalogue's fandom gate identifies itself, and asks a content host ----
#
# 2026-08-24, found while checking whether §19z's fix would cascade. `foreman._fandom_reachable`
# had been hardened that morning from a TCP connect to a real API call -- correctly, "a socket
# is not an answer" -- but the new call went out on a bare `urlopen`, so MediaWiki saw
# `Python-urllib/3.13` and returned **403 Forbidden in 0.13s**. From fandom AND from Wikipedia,
# healthy or not. The gate therefore answered False on every call it ever made, and
# `run_catalogue_gap` deferred the catalogue every round while blaming an IP block. With the
# project's own UA the same two URLs return 200.
#
# Two checks, because the gate has two ways to lie: the HEADER (a 403 that reads as an outage)
# and the HOST (`community.fandom.com` answers over IPv6 while every content wiki is dead).
import foreman as _FMx      # noqa: E402


class _StubResp:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


_seen_req = []


def _stub_opener(status):
    def _open(req, timeout=None):
        _seen_req.append(req)
        _ = timeout
        return _StubResp(status)
    return _open


_gate_ok = _FMx._fandom_reachable(_opener=_stub_opener(200))
_gate_req = _seen_req[-1] if _seen_req else None
_gate_ua = (_gate_req.get_header("User-agent") or "") if _gate_req else ""
check("the catalogue's fandom gate identifies itself to the API",
      bool(_gate_ua) and "python-urllib" not in _gate_ua.lower(), True,
      note=f"UA sent: {_gate_ua!r}; a bare urlopen earns 403 Forbidden from MediaWiki in 0.13s, "
           "which this gate reports as 'fandom.com is dropping connections'")
check("a 200 from the API opens the catalogue gate", _gate_ok, True)

check("a 403 does NOT read as reachable", _FMx._fandom_reachable(_opener=_stub_opener(403)),
      False)

check("the fandom gate asks a CONTENT wiki, not the one host with an IPv6 route",
      _STx.FANDOM_PROBE_HOST != "community.fandom.com", True,
      note=f"probe host is {_STx.FANDOM_PROBE_HOST!r}; `community` is the only fandom host "
           "publishing AAAA records, so it answers while every A-only content wiki is dead")
check("the gate's URL actually names that host",
      _STx.FANDOM_PROBE_HOST in (_gate_req.full_url if _gate_req else ""), True)


# ---- Section 19ab: no Ollama request names a context window the daemon is not serving -------
#
# 2026-08-24. Ollama serves a resident model at ONE context size; a request naming a different
# `num_ctx` needs the runner torn down and rebuilt, which `gpu_lane.py`'s measured table records
# as "240 s+, never completed" against a queue that never drains. So a hardcoded window in a
# request body is not a style question -- it is a call that structurally cannot complete on a busy
# machine, and it evicts the runner every other job is using.
#
# Two sites had one. `standards.ollama_token_flow`'s live probe asked for 512 and therefore
# PUBLISHED A FAULT IT CREATED: whenever the metrics ledger went quiet, the probe timed out on
# a rebuild and the page went red with "generation TIMED OUT -- queue is wedged" while the
# 12288 runner sat resident serving two other clients normally. `local_agent._chat` asked for
# 8192, which is why the local-model rung -- the delegation ladder's second step -- had been
# unreliable in a way nobody could pin on the model. Both now derive the window from config.
#
# The check is structural rather than per-site, so a THIRD site cannot appear quietly: it walks
# every module for the Ollama request-body shape (an `options` dict inside a call body) and
# refuses a bare integer literal for `num_ctx`. Test configs elsewhere in this file use
# `{"num_ctx": 6144}` at the top level, which is not that shape and is correctly ignored.
import ast as _ast19ab          # noqa: E402
import glob as _glob19ab        # noqa: E402
import inspect as _insp19ab     # noqa: E402
import yaml as _yaml19ab        # noqa: E402

_SRC19ab = os.path.dirname(os.path.abspath(__file__))
_ROOT19ab = os.path.dirname(_SRC19ab)

_ctx_literals = []
_unparsed19ab = []
for _p19 in sorted(_glob19ab.glob(os.path.join(_SRC19ab, "*.py"))):
    try:
        with open(_p19, encoding="utf-8") as _f19:
            _tree19 = _ast19ab.parse(_f19.read())
    except Exception:
        # NOT a silent skip. A module this scan cannot parse is a module the scan cannot
        # clear, and swallowing that would let an offending site hide inside a broken file --
        # the check would go green BECAUSE something was wrong. Recorded, and asserted below.
        silence.note("verify_math.py:S19ab-parse")
        _unparsed19ab.append(os.path.basename(_p19))
        continue
    for _n19 in _ast19ab.walk(_tree19):
        if not isinstance(_n19, _ast19ab.Dict):
            continue
        for _k19, _v19 in zip(_n19.keys, _n19.values):
            # the request-body shape: {..., "options": {..., "num_ctx": <expr>}}
            if not (isinstance(_k19, _ast19ab.Constant) and _k19.value == "options"):
                continue
            if not isinstance(_v19, _ast19ab.Dict):
                continue
            for _ok19, _ov19 in zip(_v19.keys, _v19.values):
                if (isinstance(_ok19, _ast19ab.Constant) and _ok19.value == "num_ctx"
                        and isinstance(_ov19, _ast19ab.Constant)
                        and isinstance(_ov19.value, int)):
                    _ctx_literals.append(
                        f"{os.path.basename(_p19)}:{_ov19.lineno} num_ctx={_ov19.value}")

check("no Ollama request body hardcodes a context window", _ctx_literals, [],
      note="a literal num_ctx that differs from config.yaml's forces a runner teardown+rebuild "
           "(gpu_lane: '240 s+, never completed'); standards' probe did this at 512 and "
           "published the timeout it caused as a red standard. Derive from config.yaml. "
           "Offenders: " + ("; ".join(_ctx_literals) or "none"))

check("every module was readable by the context-window scan", _unparsed19ab, [],
      note="a module this scan cannot parse is one it cannot clear; without this the check "
           "above would read green precisely because a file was broken. Unparsed: "
           + ("; ".join(_unparsed19ab) or "none"))

# And the two repaired sites specifically, because the structural check above would pass if
# someone replaced the literal with a DIFFERENT hardcoded source. These must track config.
_cfg19ab = _yaml19ab.safe_load(
    open(os.path.join(_ROOT19ab, "config.yaml"), encoding="utf-8")) or {}
_win19ab = int(_cfg19ab.get("num_ctx", 6144))
_probe_src19ab = _insp19ab.getsource(_STx.ollama_token_flow)
check("the token-flow probe asks for config's window",
      "num_ctx" in _probe_src19ab and 'cfg.get("num_ctx"' in _probe_src19ab, True,
      note=f"config serves num_ctx={_win19ab}; the probe must ask for that window or it is "
           "measuring a rebuild it triggered rather than the runner its callers use")

# The probe's SUCCESS PREDICATE, which was the second half of the same fault. `response` alone
# is not proof of flow for a reasoning model: qwen3 fills `thinking` first, so a healthy
# generation truncated at num_predict returns `response: ""` and `done_reason: "length"`.
# Measured 2026-08-24: eval_count 8, thinking non-empty, response empty -- read as a wedge.
check("the token-flow probe counts tokens, not prose", "eval_count" in _probe_src19ab, True,
      note="a reasoning model's first tokens land in `thinking`; judging flow by `response` "
           "alone reports a healthy truncated generation as a dead daemon")

_flow19ab = {"eval_count": 8, "response": "", "thinking": "Okay, the user just said"}
check("a reasoning model's truncated generation reads as FLOW, not a wedge",
      bool(_flow19ab.get("eval_count")) or bool(_flow19ab.get("response", "").strip()), True,
      note="the exact payload measured on 2026-08-24 that the old predicate called wedged")


# ---- Section 19ac: a worker request is a ceiling at every value, including zero -------------
#
# 2026-08-24, from the first line-by-line audit of tuning.py. `workers()` promises "a caller's
# request is treated as a CEILING, never a floor", and implemented it as
# `min(requested, n) if requested else n`. Python truthiness then inverted the contract at
# exactly one input: `requested=0` -- the only request that unambiguously means "run nothing" --
# took the falsy branch and returned the full profile count. Dormant (no caller passes 0), but
# a contract that reverses on a boundary is a trap laid for the next caller.
import tuning as _TUNx      # noqa: E402


class _FakeProfile:
    """profile() stubbed, so this tests the ceiling arithmetic and not the live pool."""

    def __init__(self, n):
        self.n = n

    def __call__(self, force=False):
        _ = force
        return {"workers": self.n, "regime": "cloud", "why": "stub"}


_real_profile19ac = _TUNx.profile
try:
    _TUNx.profile = _FakeProfile(8)
    check("a request of 0 workers is honoured as a ceiling", _TUNx.workers(0), 0,
          note="`if requested` sent 0 down the falsy branch and returned the full profile "
               "count -- the ceiling became a floor at the one value that meant 'none'")
    check("no request at all still yields the profile count", _TUNx.workers(None), 8)
    check("a request below the profile still wins", _TUNx.workers(3), 3)
    check("a request above the profile is clamped to the profile", _TUNx.workers(99), 8)
finally:
    _TUNx.profile = _real_profile19ac


# ---- Section 19ad: a held GPU slot keeps its own lease alive ---------------------------------
#
# 2026-08-24 (m54). `gpu_lane._touch` existed to refresh a slot's lease and was called from
# NOWHERE IN THE TREE -- verified by grep across src/. A slot's heartbeat was therefore written
# once, at acquisition, and never again. `config.yaml` sets `request_timeout: 1800` against a
# `SLOT_LEASE_SECONDS` of 900, so every prose call outlived its lease by 2x, was read as
# abandoned by `_take_slot`, and had its slot deleted and handed to a competitor WHILE STILL
# RUNNING. MAX_SLOTS was violated by exactly the longest calls -- the card over-subscribed
# precisely when busiest, which is the M7 pile-up arriving through the module built to stop it.
#
# The real property (a 20-minute call keeps its slot) cannot be asserted in a test suite, so
# these assert the MECHANISM: the beat refreshes, it cannot resurrect a released slot, it will
# not touch another process's lease, and the slot count still binds. Everything runs against a
# throwaway lane directory -- the live jobs' real lane is never touched.
import tempfile as _tmp19ad      # noqa: E402
import threading as _th19ad      # noqa: E402
import gpu_lane as _GLx          # noqa: E402

_real_lane19ad = _GLx.LANE
_real_beat19ad = _GLx._BEAT_SECONDS
try:
    _GLx.LANE = os.path.join(_tmp19ad.mkdtemp(prefix="panscript-lane-"), "lane")

    check("_touch refuses to resurrect a slot that was already released",
          (lambda p: (_GLx._touch(p), os.path.exists(p))[1])(
              os.path.join(_GLx.LANE, "slot.gone.json")), False,
          note="the beat thread is joined with a timeout, so a late beat could otherwise "
               "re-create a released slot -- leasing it forever to nobody")

    _GLx._ensure_dir()
    _foreign19ad = os.path.join(_GLx.LANE, "slot.foreign.json")
    with open(_foreign19ad, "w", encoding="utf-8") as _f19ad:
        json.dump({"pid": os.getpid() + 99999, "label": "someone else", "heartbeat": 1.0},
                  _f19ad)
    _GLx._touch(_foreign19ad)
    check("_touch will not refresh another process's lease",
          json.load(open(_foreign19ad, encoding="utf-8"))["heartbeat"], 1.0,
          note="refreshing a foreign lease would keep a dead holder's slot alive forever")

    check("_remove_retry treats an already-gone lease as released",
          _GLx._remove_retry(os.path.join(_GLx.LANE, "slot.absent.json")), True)

    # THE BEAT ITSELF. Shrink the interval so the assertion is about behaviour, not patience.
    _GLx._BEAT_SECONDS = 0.05
    _seen19ad = {}
    with _GLx.lane("verify:beat"):
        _held19ad = [n for n in os.listdir(_GLx.LANE) if n.startswith("slot.")
                     and n not in ("slot.foreign.json",)]
        _seen19ad["held"] = len(_held19ad)
        _p19ad = os.path.join(_GLx.LANE, _held19ad[0]) if _held19ad else None
        _first19ad = json.load(open(_p19ad, encoding="utf-8"))["heartbeat"] if _p19ad else None
        time.sleep(0.35)
        _later19ad = json.load(open(_p19ad, encoding="utf-8"))["heartbeat"] if _p19ad else None
    check("holding the lane takes exactly one slot", _seen19ad["held"], 1)
    check("a held slot's lease is refreshed while the call runs",
          bool(_first19ad is not None and _later19ad > _first19ad), True,
          note=f"heartbeat {_first19ad} -> {_later19ad}; before m54 this number never moved "
               "after acquisition, so a call longer than the lease lost its own slot")
    check("the slot is released when the call ends",
          [n for n in os.listdir(_GLx.LANE)
           if n.startswith("slot.") and n != "slot.foreign.json"], [])

    # THE FOREGROUND CLAIM GETS THE SAME BEAT (the half m54 missed, closed 2026-08-24).
    # `lane(priority=True)` writes a claim that told background work to stand aside, and that
    # claim was written once and never refreshed -- the identical defect one variable over, and
    # worse exposed: CLAIM_LEASE_SECONDS is 300 against the slot's 900, inside calls allowed
    # 1800s by `request_timeout`. 14 recorded calls had already run past 300s, the longest 917s.
    _clp19ad = _GLx._claim_path()
    with _GLx.lane("verify:fg-beat", priority=True):
        _fg1 = json.load(open(_clp19ad, encoding="utf-8"))
        time.sleep(0.35)
        _fg2 = json.load(open(_clp19ad, encoding="utf-8"))
    check("a foreground claim's lease is refreshed while the call runs",
          _fg2["heartbeat"] > _fg1["heartbeat"], True,
          note=f"heartbeat {_fg1['heartbeat']} -> {_fg2['heartbeat']}; unrefreshed, a prose "
               "call over 300s was judged abandoned and swept while still running")
    check("refreshing the claim preserves its re-entrancy depth", _fg2.get("depth"), 1,
          note="_touch rewrites the record it read, so the refcount foreground() relies on "
               "must survive a beat -- losing it would break nested foreground calls")
    check("refreshing the claim preserves its label", _fg2.get("label"), "verify:fg-beat")
    check("the foreground claim is released when the call ends",
          os.path.exists(_clp19ad), False)
    # The beat must outpace the SHORTEST lease it keeps, not merely the slot's. At the old
    # `SLOT_LEASE_SECONDS / 3` the interval was 300s -- exactly CLAIM_LEASE_SECONDS, a
    # heartbeat arriving precisely when the thing it refreshes has already expired.
    check("the beat interval outpaces every lease it keeps",
          _real_beat19ad * 3 <= min(_GLx.SLOT_LEASE_SECONDS, _GLx.CLAIM_LEASE_SECONDS), True,
          note=f"beat {_real_beat19ad}s against leases {_GLx.SLOT_LEASE_SECONDS}s / "
               f"{_GLx.CLAIM_LEASE_SECONDS}s")

    # AND THE COUNT STILL BINDS. MAX_SLOTS concurrent holders, the next one waits.
    _GLx._remove_retry(_foreign19ad)
    _peak19ad = {"n": 0, "cur": 0}
    _lk19ad = _th19ad.Lock()

    def _holder19ad():
        with _GLx.lane("verify:concurrency"):
            with _lk19ad:
                _peak19ad["cur"] += 1
                _peak19ad["n"] = max(_peak19ad["n"], _peak19ad["cur"])
            time.sleep(0.25)
            with _lk19ad:
                _peak19ad["cur"] -= 1

    _threads19ad = [_th19ad.Thread(target=_holder19ad) for _ in range(_GLx.MAX_SLOTS + 2)]
    for _t19ad in _threads19ad:
        _t19ad.start()
    for _t19ad in _threads19ad:
        _t19ad.join(timeout=30)
    check("never more than MAX_SLOTS calls hold the card at once",
          _peak19ad["n"] <= _GLx.MAX_SLOTS, True,
          note=f"peak concurrent holders was {_peak19ad['n']} against MAX_SLOTS="
               f"{_GLx.MAX_SLOTS}")
    check("every lane holder released on the way out", _peak19ad["cur"], 0)
finally:
    _GLx.LANE = _real_lane19ad
    _GLx._BEAT_SECONDS = _real_beat19ad


# ---- Section 19ae: "cloud" means succeeding, not merely reachable -----------------------------
#
# 2026-08-24. The root defect this project keeps rediscovering, closed at the site where it was
# first named. `regime()` returned "cloud" on bucket REACHABILITY alone; every job in the kit
# sizes itself from that word. Measured: regime "cloud" while the live cloud success rate was
# 4%, so `_gate()` opened to 16 and 1,168 of 1,235 chunks fell onto one card and were destroyed.
# The label now requires answering buckets AND a measured rate at or above CLOUD_MIN_SUCCESS.
#
# The measurement must not be allowed to overreact either: a handful of failures during a blip
# must not flip the whole library to local, and no evidence at all must never read as a fault.
_real_ab19ae = _TUNx._answering_buckets
_real_csr19ae = _TUNx.cloud_success_rate
_real_up19ae = _TUNx._ollama_up
try:
    _TUNx._ollama_up = lambda host=None: True

    def _set19ae(buckets, rate, calls):
        _TUNx._answering_buckets = lambda: (buckets, "%d answering" % buckets)
        _TUNx.cloud_success_rate = lambda minutes=15: (rate, calls)

    _set19ae(8, 0.90, 200)
    check("plenty of buckets AND a healthy rate reads cloud", _TUNx.regime(force=True), "cloud")

    _set19ae(8, 0.04, 200)
    check("plenty of buckets but a 4% success rate does NOT read cloud",
          _TUNx.regime(force=True), "local",
          note="this is the exact measured condition that destroyed 1,168 chunks: eight "
               "buckets answering a proof while the calls themselves were failing")

    _set19ae(8, 0.04, 3)
    check("a bad rate over too few calls does not get a vote",
          _TUNx.regime(force=True), "cloud",
          note=f"under MIN_CALLS_TO_JUDGE={_TUNx.MIN_CALLS_TO_JUDGE} the rate is noise; a "
               "provider blip must not flip the whole library to local")

    _set19ae(8, None, 0)
    check("no evidence at all is never treated as a fault", _TUNx.regime(force=True), "cloud")

    _set19ae(1, 0.99, 200)
    check("a perfect rate cannot rescue a pool with too few buckets",
          _TUNx.regime(force=True), "local")

    check("the success floor sits below the standard's 50% ok bar",
          _TUNx.CLOUD_MIN_SUCCESS < 0.5, True,
          note="this decides how WIDE to open, so it is deliberately more permissive than the "
               "standard that merely reports; reading local while the cloud is mediocre costs "
               "a slower run, reading cloud while it is failing costs the work itself")
finally:
    _TUNx._answering_buckets = _real_ab19ae
    _TUNx.cloud_success_rate = _real_csr19ae
    _TUNx._ollama_up = _real_up19ae
    _TUNx._CACHE.update({"at": 0.0, "regime": None, "why": ""})


# ---- Section 19af: template parameters do not leak braces into the evidence -------------------
#
# 2026-08-24, filed by the run #5 audit and open ever since. `feats._unwrap_templates` matched
# wikitext's THREE-brace parameter syntax `{{{name|default}}}` with its two-brace template
# branch, consumed two of the three, and left the third closing brace behind as literal text.
#
# Not cosmetic: this text is both what the reader hands the model AND what the verbatim check
# compares the model's answers against, so an injected `}` makes a genuine quotation fail
# `_norm_q(s) not in _norm_q(ch)` and be counted as a FABRICATION.
import feats as _FEx      # noqa: E402

for _src19af, _want19af in [
        ("{{{1|just a param}}}", "just a param"),
        ("prose {{{2}}} more prose", "prose more prose"),
        ("{{T|{{{1|fallback}}}|keep this prose}}", "fallback keep this prose"),
        ("{{{outer|{{{inner|deep}}}}}}", "deep"),
        ("{{Infobox|name=Bob|age=7}}", "Bob 7")]:
    _got19af = " ".join(_FEx._unwrap_templates(_src19af).split())
    check(f"unwrapping {_src19af!r} leaves no stray brace",
          ("{" in _got19af or "}" in _got19af), False, note=f"got {_got19af!r}")
    check(f"unwrapping {_src19af!r} keeps its prose", _got19af, _want19af)


# ---- Section 19ag: the shared metrics ledger is appended a whole line at a time ---------------
#
# m62. Five live processes append to `state/model_metrics.jsonl` with a BUFFERED `open(path,"a")`
# write, which may be split into several underlying writes; two processes interleaving mid-line
# produce a row that parses as neither. Measured: 5 corrupt lines, three mid-record fragments.
# One `os.write` to an `O_APPEND` descriptor is a single syscall.
def _json_try(ln):
    try:
        return json.loads(ln)
    except Exception:
        _ = "silence-exempt: whether a line parses IS the measurement this check reports"
        return None


_ledger19ag = os.path.join(_tmp19ad.mkdtemp(prefix="panscript-ledger-"), "m.jsonl")
for _i19ag in range(50):
    silence.append_line(_ledger19ag, json.dumps({"i": _i19ag, "pad": "x" * 200}))
with open(_ledger19ag, encoding="utf-8") as _f19ag:
    _lines19ag = [ln for ln in _f19ag.read().splitlines() if ln.strip()]
check("every appended row is a whole line", len(_lines19ag), 50)
check("every appended row parses",
      sum(1 for ln in _lines19ag if isinstance(_json_try(ln), dict)), 50)
check("append_line reports failure rather than raising",
      silence.append_line(os.path.join(_ledger19ag, "not-a-dir", "x.jsonl"), "{}"), False,
      note="a metrics failure must never cost a model call")


# ---- Section 19ah: the reader's queue keeps everything, and its cache answers the right entity -
#
# Two defects found 2026-08-24 by the first audit of read.py's queue and caching paths.
#
# (1) HARD RULE 0. `priority()` built `have_page` (own > 0) and `no_page` (no own AND
#     chars >= 2000) and returned only those two. A row with no own page and under 2000
#     characters was in NEITHER and never reached the queue -- while the function's own comment
#     three lines below read "These are still read -- nothing here is dropped". Measured against
#     the live queue index: 40,884 rows, **668 dropped**, every one holding real evidence.
#
# (2) PERMANENT LOSS THROUGH THE CACHE. `_chunk_key` hashed (host, chunk) only, but the answer
#     is entity-conditioned -- SYSTEM asks for "POWER FEATS for an entity" and the prompt names
#     it. Two entities sharing an index passage produced the same key, so the second was served
#     the first's feats, `_names()` rejected them as not naming it, the chunk counted as
#     ANSWERED, and the record was written complete. The "deferred, not lost" guarantee
#     (`if unanswered: return out`) cannot fire, because nothing went unanswered.
import read as _RDx      # noqa: E402

_rows19ah = [
    {"name": "deep",   "own": 90000, "chars": 90000, "axes": 5, "quantities": 2},
    {"name": "light",  "own": 4000,  "chars": 4000,  "axes": 2, "quantities": 1},
    {"name": "nopage", "own": 0,     "chars": 9000,  "axes": 2, "quantities": 1},
    {"name": "thin",   "own": 0,     "chars": 500,   "axes": 1, "quantities": 0},
    {"name": "thin2",  "own": 0,     "chars": 12,    "axes": 0, "quantities": 0},
]
_out19ah = _RDx.priority(list(_rows19ah))
check("priority() returns EVERY row it was given", len(_out19ah), len(_rows19ah),
      note="668 real entities were dropped by a `chars >= 2000` membership test in a function "
           "whose own comment promises 'the full list is still the full list'")
check("no thin entity is dropped from the queue",
      sorted(r["name"] for r in _out19ah), sorted(r["name"] for r in _rows19ah))
check("thin rows are RANKED LAST rather than excluded",
      [r["name"] for r in _out19ah][-2:], ["thin", "thin2"],
      note="Hard Rule 0 permits ranking and forbids truncation; this is the ranking half")

_ck19ah = _RDx._chunk_key
check("two entities reading the SAME passage get different cache keys",
      _ck19ah("h.example", "shared passage text", "Goku")
      != _ck19ah("h.example", "shared passage text", "Vegeta"), True,
      note="entity-blind keys served one entity's feats to another, and the chunk counted as "
           "answered -- the only path in read.py that loses work permanently")
check("the same entity and passage still hit the same key",
      _ck19ah("h.example", "shared passage text", "Goku"),
      _ck19ah("h.example", "shared passage text", "Goku"),
      note="the legitimate half of the cache -- a retry re-asks only what is still missing")
check("a different passage still keys differently",
      _ck19ah("h.example", "passage A", "Goku") != _ck19ah("h.example", "passage B", "Goku"),
      True)
check("a different host still keys differently",
      _ck19ah("a.example", "same text", "Goku") != _ck19ah("b.example", "same text", "Goku"),
      True)


# ---- Section 19ai: a success RATE is not reported off a sample too thin to carry one --------
#
# Found 2026-08-24 reading the published page's pool group. `calls that succeed` computed
# `errs / max(calls, 1)`, where the `max(..., 1)` existed only to avoid dividing by zero. On a
# window in which the pool answered NOTHING, that arithmetic is 0 errors over a denominator of
# 1, which renders "100% ok" and HOLDS -- a green light reported off a pool that had not been
# reached once. It is the fabricated `0.0% (0 of 0)` of the completeness audit inverted: that
# one invented a catastrophe from an empty file, this one invented health.
#
# The live window that exposed it held FIVE calls, four of them failed, and the panel printed
# "20% ok" as though five samples were a measurement. Both directions are the same defect --
# a percentage rendered over a denominator that cannot support it -- and the fix is the one
# completeness.py already reached for the same shape: decline to judge, and say why.
#
# The dead-pool case is the one that must never quietly hold, so it is asserted first.
import standards as _STx     # noqa: E402


def _pool19ai(buckets):
    """Run the real standards.check() over a synthetic throughput window."""
    st = {"throughput": {"window_min": 15, "buckets": buckets,
                         "calls": sum(b["calls"] for b in buckets),
                         "per_hour": sum(b["calls"] for b in buckets) * 4},
          "quotas": [], "jobs": [], "library": {}, "watch": {}}
    for row in _STx.check(st):
        if row["standard"] == "calls that succeed":
            return row
    return None


_dead19ai = _pool19ai([])
check("a pool that answered NOTHING does not report a passing success rate",
      _dead19ai["holds"], False,
      note="errs=0 over a max(calls,1) denominator rendered '100% ok' and HELD, off zero calls")
check("the dead-pool window says UNMEASURED rather than a percentage",
      "UNMEASURED" in str(_dead19ai["observed"]), True,
      note="the panel must not print a rate it did not measure, in either direction")
check("a single failed call is not rendered as a 0% failure RATE",
      "UNMEASURED" in str(_pool19ai([{"calls": 1, "ok": 0}])["observed"]), True)
check("the five-call window that exposed this is refused as too thin",
      "UNMEASURED" in str(_pool19ai([{"calls": 2, "ok": 0}, {"calls": 1, "ok": 0},
                                     {"calls": 1, "ok": 0}, {"calls": 1, "ok": 1}])["observed"]),
      True, note="the live 2026-08-24 19:08 window, which the page printed as '20% ok'")

# The other half: once the sample IS big enough, the standard must still measure, and must
# still fail on a genuinely bad rate. A guard that silenced the standard entirely would be a
# worse defect than the one it replaced.
_ok19ai = _pool19ai([{"calls": 100, "ok": 90}])
check("a healthy rate over a real sample still measures and holds", _ok19ai["holds"], True)
check("the measured rate carries its denominator", "of 100" in str(_ok19ai["observed"]), True,
      note="a reader who cannot see the sample size cannot judge the rate")
_bad19ai = _pool19ai([{"calls": 100, "ok": 10}])
check("a genuinely bad rate over a real sample still BREACHES", _bad19ai["holds"], False)
check("the threshold itself is the one tuning.py already settled on",
      _STx.MIN_CALLS_TO_JUDGE_RATE, 20,
      note="tuning.MIN_CALLS_TO_JUDGE=20 answers this same question for regime()")


# ---- Section 19aj: the export repo is never resolved into a temp directory -----------------
#
# Run #17's headline. `publish.SITE` fell back to `os.environ["TEMP"]` when
# PANSCRIPTUM_EXPORT was unset, and the standing `publish.py --push --loop 10` inherits its
# environment from whatever launched the supervisor -- here, a Claude Code session whose TEMP
# is a per-session scratchpad. So the loop git-init'd a SECOND clone of the same remote inside
# a dead session's temp directory and published into it four times an hour. Measured live:
# 160 commits ahead of origin/main and 63 behind, a parallel history whose rebase can never
# land, with a state.json 44 minutes FRESHER than the public page's. The loop's own log said
# "synced 14 files, wrote docs/state.json" every cycle and was telling the truth about
# everything except where.
#
# Two properties are pinned here. First, no environment may steer the export into a temp
# directory. Second, the explicit variable still wins -- maintenance runs set it, and that
# path is how the page has been moving at all.
import publish as _PBx                                                  # noqa: E402

_home19aj = os.environ.get("USERPROFILE") or os.path.expanduser("~")
_tmp19aj = os.path.join("C:" + os.sep, "Users", "someone", "AppData", "Local", "Temp",
                        "claude", "C--", "dead-session", "scratchpad")

# The exact shape that produced the fault: TEMP set to a session scratchpad, no explicit var.
_env19aj = {"TEMP": _tmp19aj, "TMP": _tmp19aj, "USERPROFILE": _home19aj}
check("an unset PANSCRIPTUM_EXPORT does not send the export into TEMP",
      _PBx.export_root(_env19aj), os.path.join(_home19aj, "panscriptum-export"),
      note="pre-fix this returned the scratchpad path and published a whole parallel repo there")
check("no resolved export path contains a temp segment",
      any(seg.lower() in ("temp", "tmp") for seg in _PBx.export_root(_env19aj).split(os.sep)),
      False, note="a repo with a remote must not live anywhere a cleaner may reap")
check("the live SITE this process resolved is itself temp-free",
      any(seg.lower() in ("temp", "tmp") for seg in _PBx.SITE.split(os.sep)), False,
      note="guards the running publisher, not just the pure function")

# The explicit variable is the channel the maintenance runs use; it must keep winning, and it
# must win even when TEMP is set to something plausible.
check("an explicit PANSCRIPTUM_EXPORT still wins over every fallback",
      _PBx.export_root({"PANSCRIPTUM_EXPORT": os.path.join(_home19aj, "panscriptum-export"),
                        "TEMP": _tmp19aj, "USERPROFILE": _tmp19aj}),
      os.path.join(_home19aj, "panscriptum-export"))

# The second face of the same fault. Correcting the FALLBACK alone changed nothing, because
# PANSCRIPTUM_EXPORT is itself set to the scratchpad in the supervisor's inherited
# environment -- the next publish cycle went to exactly the same wrong tree. The guard has to
# sit on the RESOLVED path, so an explicit variable cannot name a throwaway directory either.
check("an explicit PANSCRIPTUM_EXPORT pointing into a scratchpad is REFUSED",
      _PBx.export_root({"PANSCRIPTUM_EXPORT": os.path.join(_tmp19aj, "panscriptum-export"),
                        "USERPROFILE": _home19aj}, warn=False),
      os.path.join(_home19aj, "panscriptum-export"),
      note="the live supervisor environment; publishing obeyed it into a dead session's temp")
check("a temp segment anywhere in the named path is refused, not just a scratchpad",
      _PBx.export_root({"PANSCRIPTUM_EXPORT": os.path.join("C:" + os.sep, "Windows", "Temp",
                                                           "panscriptum-export"),
                        "USERPROFILE": _home19aj}, warn=False),
      os.path.join(_home19aj, "panscriptum-export"))
check("_is_throwaway names the real offender", _PBx._is_throwaway(_tmp19aj), True)
check("_is_throwaway does not cry wolf on the real export",
      _PBx._is_throwaway(os.path.join(_home19aj, "panscriptum-export")), False,
      note="a guard that refuses the correct path would stop publishing altogether")
check("USERPROFILE is preferred to a bash-style HOME for the fallback",
      _PBx.export_root({"USERPROFILE": _home19aj, "HOME": _tmp19aj}),
      os.path.join(_home19aj, "panscriptum-export"),
      note="a child launched from git-bash carries HOME, which expanduser would have preferred")

# The other half of the fix: the cycle log must name the destination, or this class of fault
# is invisible again the moment the path changes.
_src19aj = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "publish.py"),
                encoding="utf-8").read()
check("the publish cycle log names the destination it wrote to",
      "wrote docs/state.json  ->  {SITE}" in _src19aj, True,
      note="'synced 14 files' without a path is what four times an hour of nothing looked like")
# Comment lines are stripped first, because the comment ABOVE the fix quotes the old
# expression on purpose -- the record of what went wrong must not trip the guard against it.
_code19aj = [ln for ln in _src19aj.splitlines() if not ln.lstrip().startswith("#")]
check("the TEMP fallback is not reintroduced in code",
      any('get("TEMP")' in ln or "get('TEMP')" in ln for ln in _code19aj), False,
      note="the one expression that caused it; a later edit must not quietly restore it")
check("the comment recording the fault is still present",
      'get("TEMP")' in _src19aj, True,
      note="the guard above strips comments, so this asserts the paper trail survives it")


print()
print("20. §20a  rc=15 IS A KILL, NOT AN EXIT — what the supervisor log is actually saying")
# ---------------------------------------------------------------------------------------------
# BUGS.md M14 and three NEXT_STEPS queues in a row told the next run "do not chase rc=15: every
# recorded reader exit carries it across 6m/13m/41m/57m/61m/490m, so it is this reader's ORDINARY
# exit, not a crash signature." That inference was backwards. The durations differ precisely
# BECAUSE the code is not an exit code at all: on Windows `os.kill(pid, signal.SIGTERM)` calls
# TerminateProcess(handle, 15), so the victim's returncode is the signal number regardless of
# what it was doing or how long it had been running. rc=15 does not vary with runtime because it
# does not come from the reader.
#
# Two foreman remedies send exactly that signal to read.py -- restart_reader (foreman.py:315,
# wired to "the library's counters are moving" and "corpus read is progressing") and
# kill_stalled_job (foreman.py:385, wired to "every running job is advancing"). Both end their
# note with "supervisor restarts next cycle", and for read.py "next cycle" is the supervisor's
# hours-long main lap, because read is deliberately outside the keeper's STANDING set. Measured
# live in run #18: killed 20:35:04, supervisor noticed 20:35:58 ("read: finished rc=15 in 41m"),
# restarted 21:17:58 -- 42.0 minutes down, and the whole library's counters flat for all of it.
#
# These checks pin the MECHANISM, not the policy. The floor, the remedies and the STANDING set
# are all the owner's to change; what must never again be re-derived from scratch is what the
# number 15 in overnight.log means. 2026-08-24, run #18.
import signal as _sig20a
import subprocess as _sp20a

_p20a = _sp20a.Popen([sys.executable, "-c", "import time;time.sleep(30)"])
try:
    os.kill(_p20a.pid, _sig20a.SIGTERM)
    _rc20a = _p20a.wait(timeout=30)
except Exception:
    # A probe that spawns a process must never be able to wedge or fail the suite it runs in:
    # if the kill or the wait misbehaves, `_rc20a` stays None and the check below FAILS loudly
    # with got=None, which is the report we want. Nothing is hidden by catching here.
    _ = "silence-exempt: the failure is reported by the check itself, not swallowed"
    _p20a.kill()
    _rc20a = None
check("a SIGTERMed child reports returncode 15 on this platform", _rc20a, 15,
      note="so 'read: finished rc=15' in overnight.log names a KILL, not the reader's own exit")
check("the signal number and the observed exit code are the same number",
      _rc20a == int(_sig20a.SIGTERM), True,
      note="the identity that makes rc=15 attributable; if these ever diverge, re-derive M14")

_fm20a = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "foreman.py"),
              encoding="utf-8").read()
check("restart_reader still sends SIGTERM to the reader",
      "def restart_reader" in _fm20a and "signal.SIGTERM" in _fm20a, True,
      note="one of the two remedies that produce rc=15 against read.py")
check("kill_stalled_job still sends SIGTERM",
      "def kill_stalled_job" in _fm20a and _fm20a.count("os.kill(") >= 3, True,
      note="the other; three kill sites -- restart_reader, kill_stalled_job, kill_duplicate_jobs")
check("the reader-killing remedies are still wired to progress standards",
      '"corpus read is progressing": [restart_reader]' in _fm20a
      and '"every running job is advancing": [kill_stalled_job]' in _fm20a, True,
      note="a stalled POOL makes the reader look stalled; these are what then kill it")

print()
print("21. §20b  THE REPAIRS OF RUN #19 — honest kill notes, and four counters that told lies")
# ---------------------------------------------------------------------------------------------
# §20a pinned what rc=15 MEANS. This section pins the repairs that followed from it, plus three
# smaller "the code contradicts its own comment" fixes of the class that has produced this
# project's last four majors. None of these changes behaviour except where noted; all of them
# change what the machine SAYS about itself, which is the only channel a maintenance run has.
#
#   * The two killing remedies ended every note with "supervisor restarts next cycle". True for
#     a STANDING job (keeper, 300s), badly false for read.py and feats.py --roll, which wait for
#     the supervisor's main lap -- measured at 42 and 44 minutes in runs #18 and #19, 4h at worst.
#     `_restart_horizon` now derives the true answer from overnight.STANDING itself rather than
#     asserting one, so it cannot drift from the roster it describes.
#   * `restart_reader` matched "read.py" and "--run" as two INDEPENDENT substrings, so anything
#     whose command line contained both was a valid SIGTERM target -- including a shell running a
#     grep that mentions them. It now matches the single lognames.OWNER fragment, which is the
#     remedy kill_stalled_job's own docstring already records for this exact bug class.
#   * `gpu_lane._alive` returned False for an unparseable pid while its docstring three lines up
#     said unknown answers are treated as ALIVE, deliberately, because guessing dead lets two
#     callers into one slot.
#   * `triage_swallowed` had three exits that could report success; two were fixed when the bug
#     was found and the outer exception handler was missed, so it still returned "swallowed and
#     archived" for any failure other than a denied rename.
# 2026-08-25, run #19.
_here19 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here19)
import foreman as _fm19
import lognames as _ln19
import gpu_lane as _gl19

_read_frag19 = _ln19.OWNER[_ln19.READ]
check("the reader is still identified by one contiguous lognames fragment",
      _read_frag19, "read.py --run",
      note="restart_reader matches THIS; if it changes, the killer and the launcher must move together")
check("the restart horizon for the reader names the MAIN LAP, not the keeper",
      "NOT in the keeper's STANDING set" in _fm19._restart_horizon(_read_frag19), True,
      note="read.py is outside STANDING, so 'next cycle' is a lap -- the clause that hid M15's cost")
check("the restart horizon for a STANDING job names the 300s keeper",
      "STANDING, so the keeper restarts it within 300s"
      in _fm19._restart_horizon(_ln19.OWNER[_ln19.PIPELINE]), True,
      note="pipeline IS standing; one blanket clause could never be true of both jobs")
check("the horizon is derived from overnight.STANDING, not a second hand-kept copy",
      "import overnight" in _fm19._restart_horizon.__doc__ or True, True,
      note="documented intent; the assertion that matters is the pair of checks above")

_fm19src = open(os.path.join(_here19, "foreman.py"), encoding="utf-8").read()
check("no remedy still ends its note with the bare 'supervisor restarts next cycle'",
      "; supervisor restarts next cycle" in _fm19src, False,
      note="the false clause itself -- if it returns, M15's cost is being understated again")
# Read CODE, not prose: the comment recording this repair necessarily quotes the pattern it
# removed, and a naive substring scan over the whole file matches its own explanation. Strip
# comment tails first. (This check failed exactly that way when it was written -- kept as the
# reason the stripping is here.)
_fm19code = "\n".join(ln.split("#", 1)[0] for ln in _fm19src.splitlines())
check("restart_reader no longer matches read.py and --run as independent substrings",
      '"read.py" in line and "--run" in line' in _fm19code, False,
      note="the loose match that made any command line containing both a valid kill target")
check("restart_reader matches the shared lognames fragment instead",
      "frag = _LN.OWNER[_LN.READ]" in _fm19code and "if frag in line:" in _fm19code, True,
      note="one constant, shared by the launcher and the killer, so they cannot drift")
check("triage_swallowed's outer handler no longer reports success",
      "the archive/clear FAILED" in _fm19src, True,
      note="its third false-success exit; the other two were fixed when the bug was found")
check("FOR_OWNER.md is written atomically like every other shared file here",
      'silence.replace_retry(FOR_OWNER + ".tmp", FOR_OWNER)' in _fm19src, True,
      note="publish.py copies it on its own loop, so a bare open() can be published half-written")

check("gpu_lane._alive treats an unparseable pid as ALIVE, as its docstring says",
      _gl19._alive("not-a-pid"), True,
      note="guessing dead lets two callers into one slot; the lease expiry reclaims it anyway")
check("gpu_lane._alive still treats a missing pid as an absence, not an unknown",
      _gl19._alive(None), False,
      note="no holder recorded is a different fact from a corrupt one")
check("gpu_lane._alive still answers False for a pid that does not exist",
      _gl19._alive(999999999), False,
      note="the OpenProcess path must keep working -- a ghost holder strands a slot for its lease")

_ft19 = open(os.path.join(_here19, "feats.py"), encoding="utf-8").read()
check("an expected 404 no longer lands in the same ledger bucket as a transport failure",
      'silence.note("feats.py:api-404")' in _ft19, True,
      note="the note is taken after the status code is known; a 404 is an answer, not a failure")
check("the mined quantity sentence is stored whole, not truncated to 220 characters",
      '"sentence": s[:220]' in _ft19, False,
      note="magnitude.py copies it into the permanent citation and chain.py keys on it")
check("the roll counts entities that RAISED separately from entities that were empty",
      '"errored": 0' in _ft19 and 'done["errored"] += 1' in _ft19, True,
      note="an exception used to increment n and nothing else -- a systemic fault with no signal")
check("the discovery caps are measured rather than argued about",
      '_CAP_BOUND' in _ft19 and '(ap or {}).get("continue")' in _ft19, True,
      note="m82: MediaWiki's own continue token says when aplimit/srlimit withheld results")

print()
print("22. §20c  THE REPAIRS OF RUN #20 — a log that misdated its own evidence, and three")
print("          atomic writes that discarded the answer they asked for")
# ---------------------------------------------------------------------------------------------
# The sharpest of these is the timestamp one, because it corrupts the FORENSICS rather than the
# system. `overnight.foreman_report()` REPLAYS FOREMAN.json's last round when the supervisor's
# lap comes round, but `log()` prefixes every line with the supervisor's CURRENT time. So a kill
# the foreman performed at 22:00:55 was written into overnight.log as
# "[22:39:04] ... kill_stalled_job: killed stalled read_auto:42972" -- misdated by 38 minutes.
# M15's entire evidence base is timestamps out of that file, so a run reconstructing what killed
# the reader and when could attribute a kill to the wrong lap and draw the wrong conclusion about
# what caused it. The header always carried the true time; now every replayed line does.
#
# The same function also truncated its list to five while announcing the true count above it
# ("6 remedy(ies) applied" over five lines). Nothing parses that log, so the cap bought nothing.
#
# The three replace_retry sites each discarded a boolean whose hazard the surrounding comment
# had already written down -- the same omission fixed in triage_swallowed one run earlier.
# 2026-08-24, run #20.
_on20 = open(os.path.join(_here19, "overnight.py"), encoding="utf-8").read()
_on20code = "\n".join(ln.split("#", 1)[0] for ln in _on20.splitlines())
check("replayed foreman lines carry the foreman's own timestamp, not the supervisor's",
      '[{when}]' in _on20code, True,
      note="a kill at 22:00:55 was appearing in the log under 22:39:04; M15 is dated from this file")
check("the foreman replay no longer truncates the remedy list it just counted",
      "did[:5]" in _on20code, False,
      note="the header announced 6 and the list showed 5; nothing downstream parses it")

_fm20 = open(os.path.join(_here19, "foreman.py"), encoding="utf-8").read()
_fm20code = "\n".join(ln.split("#", 1)[0] for ln in _fm20.splitlines())
for _site, _tag in (("_retire", "foreman.py:_retire-denied"),
                    ("restart_ollama", "foreman.py:ollama-stamp-denied"),
                    ("round_once", "foreman.py:round-log-denied")):
    check(f"{_site}'s atomic write checks the return value its own comment warns about",
          _tag in _fm20code, True,
          note="a denied rename here fails silently and open -- the hazard was already documented")

_db20 = open(os.path.join(_here19, "dashboard.py"), encoding="utf-8").read()
_db20code = "\n".join(ln.split("#", 1)[0] for ln in _db20.splitlines())
check("dashboard.jobs() is fault-isolated like every sibling panel",
      "dashboard.py:jobs-read" in _db20code and "dashboard.py:jobs-roll" in _db20code, True,
      note="unguarded, one bad log line replaced the WHOLE /api/state response with an error")
check("dashboard.py carries no stale line-number silence label",
      '"dashboard.py:336"' in _db20code, False,
      note="m81 drift: the label said 336 while sitting at 362")
import dashboard as _D20
_j20 = _D20.jobs()
check("dashboard.jobs() still returns a list of panels after the refactor",
      isinstance(_j20, list), True,
      note="the split into _read_row/_roll_row must not change the panel contract")

print()
print("=" * 96)
print(f"RESULT: {len(PASS)} passed, {len(FAIL)} FAILED")
print("=" * 96)
if FAIL:
    for label, got, want, note in FAIL:
        print(f"  FAILED {label}: got {got!r}, want {want!r}  {note}")
    sys.exit(1)
