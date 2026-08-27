"""AXIS CORRELATION — the Measures are not independent, and here is by how much.

THE QUESTION, AND WHY IT WAS WORTH ASKING. `assay._interval` computed the error bar as

    Var(C) = SUM over axes of  (w_i * sigma_i)^2

which is the correct propagation formula **for independent quantities** and silently wrong for
anything else. The omitted term is the whole of the covariance:

    Var(C) = SUM (w_i sigma_i)^2  +  2 * SUM over i<j of  w_i w_j rho_ij sigma_i sigma_j

Nobody had ever asked whether the eight physical Measures actually are independent. The
suspicion is easy to state -- a character who can level a city (Ruin) probably also operates at
a scale that reaches a long way (Reach) -- and if it is right, then every published interval in
the library is too NARROW, which is the direction this project least wants to be wrong. An
overstated confidence is a claim the evidence does not support.

WHAT THE MEASUREMENT SAID, 2026-08-25. Measured over every entity in the library carrying two or
more NUMERIC axis scores -- 45 of them, from the hand-built and reference assays -- giving 55
measurable pairs at n = 42 to 45 each:

    reach x ruin              r = +0.816   n = 44      <- the suspected pair, confirmed
    continuity x sustain      r = +0.773   n = 42
    continuity x reach        r = +0.756   n = 44
    reach x sustain           r = +0.694   n = 43
    acumen x discernment      r = +0.653   n = 44
    ...
    mean r = +0.319           EVERY sizeable pair positive, none meaningfully negative

The Measures are strongly and consistently positively correlated, and the direction is not in
doubt even if the exact figures move as the sample grows. On the charter's own Kenshiro
worksheet -- eight physical axes, Witnessed -- the covariance term is +3.125 against an
independent variance of 1.440, so the honest interval is **1.78x wider** than the one the
library was publishing.

WHAT THIS DOES NOT CLAIM. n is 45, not 4,500. These are hand-built and reference assays, which
are the library's most carefully scored entities and also its most extreme ones, so the sample
is not a random draw from the corpus. A correlation measured on titans may not hold among
ordinary people. That is a reason to keep measuring and to re-run this as the numbers grow --
it is NOT a reason to keep publishing rho = 0, which is the one value the data rules out.

AND THE GAP THIS EXPOSED, WHICH MATTERS MORE THAN THE NUMBER. Only 45 entities in the entire
library have recoverable numeric axis scores. `ASSAYS.json` holds 507 automated assays and
persists `axes_scored` (which axes) and `variance_by_axis` (their weighted variance) but NOT the
scores themselves -- so 217 assays with at least one scored axis contribute nothing here. The
automated pass has been discarding its own primary measurement. Filed as a work order; until it
is fixed this matrix cannot improve no matter how long the crawl runs.
"""
import argparse
import itertools
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence  # noqa: E402

OUT = os.path.join(HERE, "data", "AXIS_CORRELATION.json")

# Where numeric per-axis scores actually live. Named explicitly rather than globbed loosely: a
# file that merely CONTAINS the word "score" is not a file of assays, and quietly hoovering up
# the wrong shape would produce a correlation matrix nobody could trace to a source.
SOURCES = ("data/HANDBUILT_ASSAYS.json", "data/HERO_ASSAYS.json", "data/PANTHEON.json",
           "data/HALO_ASSAYS.json", "data/WH40K_ASSAYS.json", "data/Z_FIGHTERS.json",
           "data/REFERENCE_ASSAYS_PRESENCE.json",
           # THE AUTOMATED PASS, ADDED RUN #34 — and it is the reason this matrix could not grow.
           # `ASSAYS.json` holds 507 automated assays, 217 of which scored at least one axis and
           # 153 two or more, and NONE of them reached this function: the assay persisted WHICH
           # axes it scored and their weighted variance, but never the numeric score of each axis,
           # so the matrix every published interval leans on was built from 45 hand-made entities
           # while the crawl ran for weeks. `assay.py` now writes `result["scores"]`, and this is
           # the other half of that repair — without it the new key is written and never read.
           #
           # IT CHANGES NOTHING TODAY, deliberately: no existing row carries `scores`, so the
           # population is still 45 until fresh assays land, and the stored matrix only moves when
           # somebody runs `--write`. Backfilling the 507 means re-assaying them, which is an
           # owner's call and is filed, not taken here.
           "data/ASSAYS.json")

MIN_N = 4          # below this a Pearson r is noise wearing a decimal point


def _scores_of(v):
    """PURE. One stored entity -> {axis: numeric score}. Handles both shapes on disk.

    THE HAND-BUILT SHAPE nests a dict per axis carrying a `score` among other fields; THE
    AUTOMATED SHAPE (`ASSAYS.json`, written by `assay.py`) nests the assay under `result` and
    carries a flat `{axis: number}` in `scores`. Separated out and made pure so the drill can put
    both shapes to it without a data file, and so that adding a third shape later is a change in
    one place rather than a second `for` loop that drifts from this one — which is precisely how
    the automated pass came to be invisible here for weeks.

    A row with no scores yields {} and is dropped by the caller's `>= 2` test, so a pre-#34 assay
    written before `scores` existed is skipped rather than counted as zeros. Absent is not zero.
    """
    ax = v.get("axes")
    if isinstance(ax, dict):
        return {k: x["score"] for k, x in ax.items()
                if isinstance(x, dict) and isinstance(x.get("score"), (int, float))}
    res = v.get("result")
    sc = res.get("scores") if isinstance(res, dict) else None
    if isinstance(sc, dict):
        return {k: x for k, x in sc.items() if isinstance(x, (int, float))}
    return {}


def observations():
    """-> [{axis: score}], one dict per entity carrying two or more numeric axis scores."""
    rows = []
    for rel in SOURCES:
        p = os.path.join(HERE, rel)
        if not os.path.exists(p):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            silence.note("axis_correlation.py:load")
            continue
        for v in (d.values() if isinstance(d, dict) else d):
            if not isinstance(v, dict):
                continue
            s = _scores_of(v)
            if len(s) >= 2:
                rows.append(s)
    return rows


def _pearson(xs, ys):
    n = len(xs)
    if n < MIN_N:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None            # a constant column has no correlation, it has no variance
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def measure(rows=None):
    """-> {'pairs': {'a|b': {'r':..,'n':..}}, 'mean_r':.., 'n_entities':.., 'axes':[..]}."""
    rows = observations() if rows is None else rows
    axes = sorted({k for r in rows for k in r})
    pairs, vals = {}, []
    for a, b in itertools.combinations(axes, 2):
        xs = [r[a] for r in rows if a in r and b in r]
        ys = [r[b] for r in rows if a in r and b in r]
        r_ = _pearson(xs, ys)
        if r_ is None:
            continue
        pairs["%s|%s" % (a, b)] = {"r": round(r_, 4), "n": len(xs)}
        vals.append(r_)
    return {"pairs": pairs, "axes": axes, "n_entities": len(rows),
            "mean_r": round(sum(vals) / len(vals), 4) if vals else None,
            "measured_pairs": len(pairs)}


def write(doc=None):
    doc = doc or measure()
    doc["note"] = ("MEASURED, not decreed. Rebuild with `python src/axis_correlation.py "
                   "--write` whenever the number of entities with numeric axis scores grows. "
                   "rho = 0 is the one value this data rules out.")
    silence.write_json(OUT, doc, indent=2, sort_keys=True)
    return OUT


def load():
    """-> the stored matrix, or None. Callers must handle None; see `assay._rho`."""
    try:
        with open(OUT, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) and d.get("pairs") else None
    except Exception:
        silence.note("axis_correlation.py:load-matrix")
        return None


def rho(a, b, doc=None, default=None):
    """Correlation between two axes. -> float.

    THE DEFAULT IS THE MEASURED MEAN, NOT ZERO, and that is the entire point of this function --
    for an UNMEASURED PAIR inside an otherwise-present matrix. That is the case below where
    `doc["pairs"]` has no entry for `(a, b)`: we have 55 other measurements and no reason to
    think this pair is the one exception, so it inherits the mean rather than the independence
    assumption the data as a whole rules out.

    A WHOLLY MISSING OR UNREADABLE MATRIX (the `if not doc` branch immediately below) is a
    different claim -- we do not have "weaker evidence for this one pair", we have NO matrix at
    all, corrupt or not yet built -- and `load()` does not distinguish those two causes from each
    other, so this function cannot either. Order c00cab9d0412 already ruled on what a caller
    should do about that: `assay._rho_doc` returns 0.0 for exactly this case ON PURPOSE, because
    0.0 reproduces the library's pre-correlation numbers exactly rather than some third,
    never-seen behaviour, and it is never silent about it -- stamped into `RHO_FALLBACK_REASON`,
    printed to stderr, and carried on every affected assay's `correlation_source`. This function's
    own bare `default`-or-`0.0` below is what a direct caller with no wrapper (`drill.py`'s
    `drill_correlation` net) gets instead, and that net is what actually stands guard here: it
    fails BREACHED the moment `widening()` stops measurably widening a bar, missing matrix or
    corrupt one alike. See order 1b29e38dbb17 for the analysis; changing the fallback VALUE would
    be re-opening c00cab9d0412's ruling, not fixing a bug, so it stays as `assay.py` chose it.
    """
    doc = doc or load()
    if not doc:
        return 0.0 if default is None else default
    lo, hi = sorted((a, b))
    hit = doc["pairs"].get("%s|%s" % (lo, hi))
    if hit:
        return float(hit["r"])
    if default is not None:
        return default
    return float(doc.get("mean_r") or 0.0)


def widening(weights, sigma, axes, doc=None):
    """How much wider the honest bar is than the independent one. -> (factor, indep, cov).

    Returns a FACTOR rather than a corrected interval so callers cannot accidentally apply it
    twice, and so the two components stay separately inspectable in the report.
    """
    doc = doc or load()
    denom = sum(weights[k] for k in axes)
    if not denom:
        return 1.0, 0.0, 0.0
    w = {k: weights[k] / denom for k in axes}
    indep = sum((w[k] * sigma) ** 2 for k in axes)
    cov = 0.0
    for a, b in itertools.combinations(axes, 2):
        cov += 2 * w[a] * w[b] * rho(a, b, doc) * sigma * sigma
    total = max(indep + cov, 1e-12)
    return math.sqrt(total / indep) if indep else 1.0, indep, cov


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="rebuild data/AXIS_CORRELATION.json")
    ap.add_argument("--top", type=int, default=15)
    a = ap.parse_args()
    doc = measure()
    print("AXIS CORRELATION — measured over %d entities carrying >=2 numeric axis scores"
          % doc["n_entities"])
    print("=" * 78)
    ranked = sorted(doc["pairs"].items(), key=lambda kv: -abs(kv[1]["r"]))
    for key, v in ranked[:a.top]:
        x, y = key.split("|")
        print("   r=%+.3f  n=%2d   %s x %s" % (v["r"], v["n"], x, y))
    print("-" * 78)
    print("   %d pair(s) measured, mean r = %+.4f" % (doc["measured_pairs"], doc["mean_r"]))
    if doc["mean_r"] and doc["mean_r"] > 0.1:
        print("   The Measures are NOT independent. rho = 0 is ruled out by this data.")
    if a.write:
        print("\nwrote " + write(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
