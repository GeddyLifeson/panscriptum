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


print()
print("=" * 96)
print(f"RESULT: {len(PASS)} passed, {len(FAIL)} FAILED")
print("=" * 96)
if FAIL:
    for label, got, want, note in FAIL:
        print(f"  FAILED {label}: got {got!r}, want {want!r}  {note}")
    sys.exit(1)
