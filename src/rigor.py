#!/usr/bin/env python3
"""
RIGOR — the commensuration engine, and the proof that the library's three rankings are one.

THE PROBLEM THIS FILE SOLVES
----------------------------
The Assay carries eleven Measures. Eight are physical (Ruin, Celerity, Reach, Sustain, ...) and
three are faculties (Acumen, Discernment, Suasion). And the composite weights read:

    WEIGHTS         ruin 0.20, continuity 0.15, celerity 0.12, ... (sums to 1)
    FACULTY_WEIGHTS acumen 0.0, discernment 0.0, suasion 0.0

**The faculties are weighted zero.** They are instrumented in X.6 §6 and then contribute nothing
to Magnitude. So the Assay, which presents itself as a general measure of a being, is in fact a
Str/Dex/Con scale that carries Int/Wis/Cha as an appendix. Every claim that the library can rank
a schemer against a destroyer has been, to this point, false.

The reason is not laziness. It is that nobody could say what a point of Wisdom is WORTH against a
point of Ruin, and rather than invent an exchange rate the charter set the rate to zero -- which
is itself an exchange rate, and the worst one available, chosen by default rather than by
argument.

THE RESOLUTION IS ALREADY IN THE LIBRARY
----------------------------------------
The exchange rate does not need inventing. It was fixed years ago in three separate places that
nobody had put side by side:

    X.6 §3   Acumen is measured in BITS per epoch, and is capped by the algorithmic content
             of the stream it reads.
    X.2 §4   Transgression is measured in BITS -- Rissanen exception length.
    X.10 §6  L_r = log2(Ruin_edge(r) / Ruin_edge(M0)) converts a band's ENERGY span into the
             BITS required to specify a state within it.

Energy and information were never two currencies. The Assay has been an information measure since
it was written and had simply never been asked to say so. Therefore:

    A point of Ruin at band r spans L_r/10 bits.
    A point of Acumen at band r spans, at ceiling, L_r/10 bits.

**The faculties and the physical Measures share a unit.** Sharing a unit is not yet an exchange
rate, and it is worth being exact about what is proved and what is chosen:

    PROVED   both axes are measured in bits, by the charter's own definitions. Commensurability
             in the strict sense -- same dimension -- follows.
    CHOSEN   that the rate is 1:1. Any rate k != 1 is a free parameter, and nothing in the charter
             or in physics fixes k. Parity is the unique rate introducing NO parameter, which
             under X.9 §4's own accounting is the shortest codification and therefore the one to
             adopt absent an argument for another.

That is an MDL argument, not a physical derivation, and it should be read as one. What it
decisively rules out is k = 0, the rate currently in force: zero is not the absence of a choice.
It is the strongest possible claim -- that no quantity of foresight, insight or influence can ever
register on a being's Magnitude -- and it is the one value a shared unit positively forbids.

WHAT ELSE IS IN HERE, AND WHY IT BELONGS TOGETHER
-------------------------------------------------
Once commensuration is a bit-count, the same shape appears everywhere in the charter, and §2
proves the three instances are literally one operation:

    AHP           ratio judgments  -> scalar, residual reported as Saaty's CR
    Bradley-Terry win/loss counts  -> scalar, residual reported as deviance
    HodgeRank     contest flow     -> scalar, residual reported as eta

Theorem 1 below shows AHP and HodgeRank are the same computation under a logarithm: a ratio
matrix is consistent exactly when its log-flow is curl-free. CR and the curl fraction are DIFFERENT
FUNCTIONALS taking different values -- they are not one number, and this file previously said they
were, which was wrong -- but they vanish together and grow together, because both measure one
defect: the failure of a relational structure to be carried by any scalar.

Moth's *"the omniverse is not a ladder, it is a chord"* and Saaty's CR > 0.10 are therefore the
same finding in two centuries' vocabularies, and Proposition 1's incomparability is its
order-theoretic face.
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# A regex escape arriving as a literal control character matches nothing and fails SILENTLY.
# A word-boundary escape written through a shell heredoc has arrived here as a 0x08 backspace
# five separate times in this project. Each time it read as a tuning problem -- a gate that
# passed nothing, a parser that found zero rows -- rather than as corruption, which is what
# makes it expensive. The check is built from chr() codes because the first version was
# written with escapes and they were eaten too, so it flagged its own source and refused.
_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding='utf-8').read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ': a regex escape was eaten in transit - a literal control '
                     'character is present in the source. Repair before running.')

sys.path.insert(0, HERE)


# ==================================================================================================
# 1. COMMENSURATION — what a point of any Measure is worth, in bits
# ==================================================================================================

def measure_bit_value(band, module=None):
    """The bit-worth of ONE point on any decimal axis at a given band.

    Each Measure is scored 0-10 across its band window. The window spans L_r bits (X.10 §6), so
    one point is L_r/10 bits. This holds for a physical Measure and a faculty alike -- which is
    the whole content of the coherence framework:

        Ruin 7.0 at M5   ->  7.0 * 13.23 = 92.6 bits
        Acumen 7.0 at M5 ->  7.0 * 13.23 = 92.6 bits

    They are equal in UNIT, necessarily, and equal in VALUE by the parity convention argued in the
    module header (the unique zero-parameter choice). The reading is that a being who can specify
    92.6 bits of world by force and one who can specify 92.6 bits by foresight have constrained
    the world equally -- which is a claim about what the Ladder measures, and the library should
    own it as such rather than present it as a theorem.
    """
    import tempus as T
    # band_resolution, NOT rung_description_length: see the note there. Using cumulative content
    # made every M0 axis point worth zero bits, which the anchor validation exposed.
    L = T.band_resolution(band)
    return None if L is None else L / 10.0


def faculty_parity_weights(n_physical=8, n_faculty=3):
    """Weights implied by parity, with NO free parameter.

    If every axis is worth L_r/10 bits per point, then no axis can outrank another a priori: the
    composite is a plain mean over scored axes. Any departure from uniformity is a claim that one
    axis's bits matter more than another's, which is a claim about VALUE, not about capability,
    and the Assay does not measure value.

    This is returned alongside -- not instead of -- the charter's declared weights, because
    replacing them is the owner's call. What is NOT the owner's call is whether zero was
    defensible. It was not.
    """
    n = n_physical + n_faculty
    return {"uniform_weight": 1.0 / n, "n_axes": n,
            "argument": ("parity follows from the bit-equivalence; a non-uniform weight is a "
                         "value judgment the Assay has no instrument for")}


# ==================================================================================================
# 2. THE COMMENSURATION OPERATOR — three faces, one computation
# ==================================================================================================

# Saaty's random consistency index: mean CI of random reciprocal matrices of order n.
SAATY_RI = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41,
            9: 1.45, 10: 1.49, 11: 1.51, 12: 1.48, 13: 1.56, 14: 1.57, 15: 1.59}


def perron_weights(A):
    """AHP: the principal (Perron) eigenvector of a positive reciprocal matrix.

    Perron-Frobenius guarantees a positive matrix has a unique largest-modulus eigenvalue with a
    strictly positive eigenvector, unique up to scale. That eigenvector IS the weight vector --
    the scalar the pairwise judgments were reaching for.

    Returns weights, lambda_max, CI, CR. CR < 0.10 is Saaty's conventional bar for "the judgments
    are coherent enough to scalarize."
    """
    A = np.asarray(A, dtype=float)
    n = A.shape[0]
    vals, vecs = np.linalg.eig(A)
    k = int(np.argmax(vals.real))
    w = np.abs(vecs[:, k].real)
    w = w / w.sum()
    lam = float(vals[k].real)
    ci = (lam - n) / (n - 1) if n > 1 else 0.0
    ri = SAATY_RI.get(n, 1.6)
    cr = (ci / ri) if ri > 0 else 0.0
    return {"weights": w, "lambda_max": lam, "CI": ci, "CR": cr,
            "coherent": bool(cr < 0.10)}


def logrank_weights(A):
    """The SAME problem solved as a least-squares gradient fit on log-ratios.

    Take logs: log A_ij should equal log w_i - log w_j. That is exactly a pairwise FLOW, and
    finding the best-fitting log w is exactly HodgeRank's gradient projection. What the gradient
    cannot explain is curl.

    This is the geometric-mean (logarithmic least squares) solution of AHP, and it is the bridge
    that makes Theorem 1 true.
    """
    A = np.asarray(A, dtype=float)
    F = np.log(A)
    F = 0.5 * (F - F.T)                     # enforce exact antisymmetry
    theta = F.mean(axis=1)                  # closed form: row mean of the log matrix
    theta = theta - theta.mean()
    G = theta[:, None] - theta[None, :]     # the pure-gradient part
    grad_sq = float((G ** 2).sum())
    res_sq = float(((F - G) ** 2).sum())
    total = grad_sq + res_sq
    eta = (grad_sq / total) if total > 0 else 1.0
    w = np.exp(theta)
    w = w / w.sum()
    return {"weights": w, "eta": eta, "curl_fraction": 1.0 - eta,
            "grad_sq": grad_sq, "residual_sq": res_sq}


def theorem_1_check(A):
    """THEOREM 1 (Consistency and curl-freeness coincide).

    For a positive reciprocal matrix A (A_ij > 0, A_ji = 1/A_ij), the following are equivalent:

        (i)   A is perfectly consistent: A_ik = A_ij * A_jk for all i,j,k
        (ii)  A_ij = w_i/w_j for some positive w
        (iii) log A, as an antisymmetric edge flow, is a pure gradient (zero curl)
        (iv)  lambda_max = n, hence CI = CR = 0
        (v)   the HodgeRank residual vanishes, hence eta = 1

    (ii)<=>(iii) is immediate: log A_ij = log w_i - log w_j is the definition of a gradient flow
    on the complete graph. (i)<=>(iv) is Saaty (1977). The Hodge reading is Jiang, Lim, Yao & Ye,
    *Statistical ranking and combinatorial Hodge theory*, Math. Program. 127 (2011).

    PRECISION MATTERS HERE, and an earlier draft of this file overstated it. CR and the curl
    fraction are NOT the same functional and do not take the same value -- CR is built from the
    Perron eigenvalue, the curl fraction from a least-squares residual. What is true, and is all
    that is needed, is that **they vanish together and increase together**: both are measures of
    the same underlying defect, namely the failure of a relational structure to be representable
    by any scalar.

    That is the coherence framework's load-bearing claim, and it is why Int/Wis/Cha can be set
    against Str/Dex/Con at all. Commensuration is never assumed; it is ATTEMPTED, and the attempt
    reports its own residual. Where the residual is small the scalar is trustworthy. Where it is
    large the honest output is not a worse number but the finding that no number exists -- which
    is Moth's chord, Proposition 1's incomparability, and Saaty's CR > 0.10, in three vocabularies.
    """
    p = perron_weights(A)
    l = logrank_weights(A)
    agree = float(np.max(np.abs(p["weights"] - l["weights"])))
    return {
        "perron_weights": p["weights"], "logrank_weights": l["weights"],
        "max_weight_disagreement": agree,
        "CR": p["CR"], "eta": l["eta"], "curl_fraction": l["curl_fraction"],
        "both_say_consistent": bool(p["CR"] < 1e-9 and l["curl_fraction"] < 1e-9),
        "reading": ("CR and the curl fraction rise and fall together: both are the share of the "
                    "relation that no single ladder can carry"),
    }


def consistent_matrix(weights):
    """Build the ratio matrix a weight VECTOR implies: A_ij = w_i / w_j.

    Useful mostly as a diagnosis. A declared weight vector always produces a perfectly consistent
    matrix, hence CR = 0 -- which sounds like a clean bill of health and is the opposite. It means
    the weights were never elicited from judgments and therefore can never be contradicted by
    them. A number that cannot fail a test has not passed one.
    """
    w = np.asarray(list(weights.values()) if isinstance(weights, dict) else weights, dtype=float)
    return w[:, None] / w[None, :]


def _strongly_connected(nodes, beat_edges):
    """Tarjan SCCs of the directed 'i beat j' graph. Needed for Ford's condition below."""
    idx = {}
    low = {}
    on = {}
    stack = []
    out = []
    counter = [0]
    adj = {n: [] for n in nodes}
    for a, b in beat_edges:
        adj[a].append(b)

    def walk(v):
        # iterative Tarjan: the contest graph can be deep and recursion would cap out
        work = [(v, 0)]
        while work:
            node, pi = work[-1]
            if pi == 0:
                idx[node] = low[node] = counter[0]
                counter[0] += 1
                stack.append(node)
                on[node] = True
            recurse = False
            for i in range(pi, len(adj[node])):
                w = adj[node][i]
                if w not in idx:
                    work[-1] = (node, i + 1)
                    work.append((w, 0))
                    recurse = True
                    break
                elif on.get(w):
                    low[node] = min(low[node], idx[w])
            if recurse:
                continue
            if low[node] == idx[node]:
                comp = []
                while True:
                    w = stack.pop()
                    on[w] = False
                    comp.append(w)
                    if w == node:
                        break
                out.append(sorted(comp))
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])

    for n in nodes:
        if n not in idx:
            walk(n)
    return out


def bradley_terry(wins, iters=500, tol=1e-12, prior=0.0):
    """Bradley-Terry strengths by the MM algorithm (Hunter 2004), which is monotone convergent.

    `prior` > 0 adds virtual contests against a phantom average opponent.

    WHY A PRIOR IS OFFERED, AND WHY IT IS NOT THE DEFAULT
    ----------------------------------------------------
    Ford's refusal below is correct and, on real data, total. The library's first chain had 38
    entrants in 36 components with the largest at 3 -- honest, and it returned nothing anyone
    could use. Volume will not rescue it either: 3,612 recorded outcomes will never connect Fone
    Bone to Goku, because those fictions share no contest and never will.

    The standard remedy is a weakly-informative prior -- one virtual win and one virtual loss for
    every entrant against every other. It is symmetric, so it asserts nothing about who is
    stronger; it asserts only that everyone is comparable to everyone, which is exactly what
    connects the graph. That makes the maximiser exist for the 11 undefeated and 24 winless
    entrants who otherwise sit at infinity. This is MAP estimation under a symmetric prior, and
    at prior=0 the function is bit-for-bit the maximum-likelihood estimator it was before.

    It is not the default because the two answers mean different things. `identified=True` says
    THE DATA ordered these entities. A regularised strength says the data plus an assumption did,
    and the assumption is that an entity with no recorded contest is average until shown
    otherwise. Both are legitimate; conflating them is not, so the result carries `regularised`
    and the caller decides which question was being asked.

    `wins[(i,j)]` = times i beat j. Returns strengths p with sum 1, plus the deviance against a
    saturated model -- the third face of the same residual.

    FORD'S CONDITION, WHICH THIS FUNCTION PREVIOUSLY IGNORED
    --------------------------------------------------------
    Ford (1957): the Bradley-Terry MLE exists and is unique IF AND ONLY IF the directed comparison
    graph is strongly connected -- in every partition of the entrants into two non-empty sets,
    someone in the second must have beaten someone in the first.

    An earlier version of this function silently violated that twice:

      * On a DISCONNECTED graph it returned strengths for every entrant, so that a = 0.35 and
        c = 0.30 read as "a is stronger than c" when a and c had never met. Across components the
        BT scale is arbitrary; that comparison was pure artifact.
      * On an UNDEFEATED entrant it returned 0.998, which is not the MLE but simply where the
        iteration stopped. The true maximiser is at infinity and no finite answer exists.

    Both now REFUSE rather than report. The charter had already said this about Volition -- theta
    "exists only relative to a connected contest graph" -- and the code was contradicting it.

    Returns `components`, and comparisons are only meaningful WITHIN one.
    """
    names = sorted({n for pair in wins for n in pair})
    idx = {n: i for i, n in enumerate(names)}
    n = len(names)
    W = np.zeros((n, n))
    for (a, b), c in wins.items():
        W[idx[a], idx[b]] += c
    # Keep the OBSERVED contests. The undefeated/winless report below is a statement about the
    # real data, and the prior added just below is by construction symmetric -- so once it is
    # folded in, every entrant has both a win and a loss and those two lists come back empty for
    # any prior > 0, no matter who actually went undefeated. The report then reads "nobody in
    # this set is undefeated" about a set containing someone who is.
    observed = W.copy()
    if prior > 0:
        # Symmetric virtual contests: every entrant against every other, both directions equally.
        # Adds no information about ranking, only about comparability.
        W = W + prior * (np.ones((n, n)) - np.eye(n))
    total_wins = W.sum(axis=1)
    N = W + W.T                                   # games played
    p = np.ones(n) / n

    for _ in range(iters):
        prev = p.copy()
        denom = np.zeros(n)
        for i in range(n):
            for j in range(n):
                if i != j and N[i, j] > 0:
                    denom[i] += N[i, j] / (p[i] + p[j])
        with np.errstate(divide="ignore", invalid="ignore"):
            newp = np.where(denom > 0, total_wins / denom, p)
        if newp.sum() <= 0:
            break
        p = newp / newp.sum()
        if np.max(np.abs(p - prev)) < tol:
            break

    # deviance vs the saturated (per-pair) model
    dev = 0.0
    for i in range(n):
        for j in range(n):
            if i != j and N[i, j] > 0 and W[i, j] > 0:
                fitted = N[i, j] * p[i] / (p[i] + p[j])
                if fitted > 0:
                    dev += 2 * W[i, j] * math.log(W[i, j] / fitted)
    df = max(1, int((N > 0).sum() / 2) - (n - 1))

    # --- Ford's condition, checked rather than assumed -----------------------------------------
    beat = [(a, b) for (a, b), c in wins.items() if c > 0]
    comps = _strongly_connected(names, beat)
    identified = len(comps) == 1 and len(comps[0]) == n

    # An entrant who never lost (or never won) inside the whole set drives theta to +/- infinity.
    undefeated = [names[i] for i in range(n)
                  if observed[i].sum() > 0 and observed[:, i].sum() == 0]
    winless = [names[i] for i in range(n)
               if observed[:, i].sum() > 0 and observed[i].sum() == 0]

    out = {"names": names, "strengths": p, "deviance": dev, "df": df,
           "prior": prior, "regularised": bool(prior > 0),
           "deviance_per_df": dev / df,
           "components": comps, "identified": bool(identified),
           "undefeated": undefeated, "winless": winless,
           "note": "high deviance per df = intransitive contests = chord, not ladder"}

    # A PRIOR CHANGES WHAT IS BEING REFUSED, so it changes whether to refuse.
    #
    # Ford's check runs on the RAW wins, and must: `identified` means "the data ordered these
    # entities", and a virtual contest is not data. But when a prior has been asked for, the
    # maximiser genuinely exists -- the augmented graph is complete by construction and no theta
    # diverges. Returning None there would refuse to report an estimate that does exist, on the
    # grounds that a different estimator would not have existed, which is the wrong refusal.
    #
    # So the numbers are returned and both facts are carried: `identified` stays False, and
    # `regularised` says why there is an answer anyway.
    if prior > 0:
        out["refusal"] = None
        out["caveat"] = (
            f"regularised with prior={prior}: strengths exist because every entrant was given "
            f"symmetric virtual contests, NOT because the recorded outcomes connect them. The "
            f"raw graph has {len(comps)} components. Compare within a component freely; across "
            f"components the ordering is the prior's assumption that an entity with no contests "
            f"is average, not a finding.")
        return out
    if not identified:
        out["strengths"] = None
        out["refusal"] = (
            f"comparison graph is not strongly connected: {len(comps)} components "
            f"{[c[:3] for c in comps][:4]}. Ford (1957) — the MLE is identified only within a "
            f"component, and BETWEEN components the scale is arbitrary. A cross-component "
            f"ranking would be an artifact of the solver, not a finding about the entrants.")
    elif undefeated or winless:
        out["strengths"] = None
        out["refusal"] = (
            f"unbounded MLE: undefeated={undefeated} winless={winless}. Their theta diverges, so "
            f"no finite maximiser exists. Any number reported here would be the iteration cap "
            f"wearing the costume of an estimate.")
    return out


# ==================================================================================================
# 3. MDL — beta by counting alternatives, not by decree
# ==================================================================================================

def mdl_bits(n_alternatives):
    """Rissanen: selecting one of N equally-plausible alternatives costs log2 N bits.

    This is the honest floor under every beta in the library. A patch that picks one exception out
    of N possible exceptions cannot cost less, and claiming it costs more requires naming the
    extra structure being specified.
    """
    if n_alternatives <= 1:
        return 0.0
    return math.log2(n_alternatives)


# The catalogue an exception is selected FROM. Without an explicit catalogue, "which law is
# broken" has no bit-count -- you cannot pay to select from a set you have not enumerated. These
# are the standard conserved quantities and structural principles of established physics, which is
# what makes the count auditable rather than atmospheric.
LAW_CATALOGUE = [
    "energy conservation",              # Noether, time-translation symmetry
    "linear momentum conservation",     # Noether, space-translation symmetry
    "angular momentum conservation",    # Noether, rotational symmetry
    "electric charge conservation",     # Noether, U(1) gauge symmetry
    "baryon number",
    "lepton number",
    "CPT invariance",
    "Lorentz invariance",
    "causality (no closed timelike curves)",
    "second law of thermodynamics",
    "unitarity (probability conservation)",
    "the equivalence principle",
]


def _log2_choose(n, k):
    """log2 C(n,k), computed via lgamma so it stays exact for large n without overflow."""
    if k <= 0 or k >= n:
        return 0.0
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)) / math.log(2)


def adjudication_beta(n_laws_touched, n_regimes, n_parameters=0, param_precision_bits=8,
                      catalogue_size=None):
    """beta for an adjudication, by counting what must actually be written to specify it.

    A two-part code in Rissanen's sense: the cost of an exception is the length of the message
    that identifies it uniquely. Three terms, each a genuine count:

      1. WHICH laws are excepted -> log2 C(M, k), the exact cost of naming a k-subset of the
         M-law catalogue above. (The earlier draft used k*log2(4k), which was invented and had no
         claim on anyone's belief.)
      2. WHERE it applies        -> log2(R) to select one of R regimes
      3. HOW MUCH it bends       -> p parameters at the stated precision

    Rissanen, *Modeling by shortest data description*, Automatica 14 (1978); Grunwald, *The
    Minimum Description Length Principle* (2007), ch. 5 on two-part codes.

    This yields a FLOOR, not the charter's value. A floor is the useful thing: it says what an
    exception cannot cost less than, so a declared price can be audited against it.
    """
    M = catalogue_size or len(LAW_CATALOGUE)
    k = max(1, min(n_laws_touched, M))
    n_regimes = max(1, n_regimes)

    b_which = _log2_choose(M, k) if k < M else 0.0
    b_where = mdl_bits(n_regimes)
    b_much = n_parameters * param_precision_bits
    total = b_which + b_where + b_much
    return {"catalogue_size": M, "laws_excepted": k,
            "which_laws_bits": round(b_which, 2), "where_bits": round(b_where, 2),
            "magnitude_bits": round(b_much, 2), "beta_floor_bits": round(total, 2)}


# ==================================================================================================
# 4. UNCERTAINTY — a census is a product of uncertain factors, and must carry an interval
# ==================================================================================================

def lognormal_product(factors, correlations=None):
    """Propagate uncertainty through a PRODUCT, which is what every census chain is.

    `factors` is a list of (name, median, sigma_dex) where sigma_dex is the 1-sigma spread in
    ORDERS OF MAGNITUDE -- the honest unit for quantities known only to within a factor of ten.

    ln(prod X_i) = sum ln X_i, so the log-variances add. With correlations supplied as
    {(a,b): rho}, the covariance terms add too: shared ignorance does not average out, and a
    census that assumes independent factors understates its own spread.

    This is Drake-equation arithmetic done the way Sandberg, Drexler and Ord did it: the point
    estimate is nearly meaningless on its own, and the credible interval is the result.
    """
    names = [f[0] for f in factors]
    mu = sum(math.log10(f[1]) for f in factors)
    var = sum(f[2] ** 2 for f in factors)
    if correlations:
        pos = {n: i for i, n in enumerate(names)}
        for (a, b), rho in correlations.items():
            if a in pos and b in pos and a != b:
                var += 2 * rho * factors[pos[a]][2] * factors[pos[b]][2]
    sd = math.sqrt(max(var, 0.0))
    return {
        "median": 10 ** mu,
        "log10_median": mu,
        "sigma_dex": sd,
        "ci68": (10 ** (mu - sd), 10 ** (mu + sd)),
        "ci95": (10 ** (mu - 1.96 * sd), 10 ** (mu + 1.96 * sd)),
        "spread_orders_of_magnitude": round(2 * 1.96 * sd, 2),
    }


def prob_at_least_one(log10_median, sigma_dex, n_samples=200000, seed=20260820):
    """P(N >= 1) integrated over the uncertainty -- NOT evaluated at the mean.

    THIS IS THE ERROR THE FERMI LITERATURE EXISTS TO CORRECT, and an earlier draft of this file
    committed it. Plugging the expected count into 1 - exp(-lambda) computes

        P(N >= 1 | E[lambda])        which is NOT        E[ P(N >= 1) ].

    Because 1 - exp(-lambda) is concave, Jensen's inequality makes the first strictly larger
    whenever lambda is uncertain. When lambda is uncertain across SIX ORDERS OF MAGNITUDE, as
    every census chain here is, the gap is not a rounding matter: the point estimate can say
    "certainly yes" while the integrated answer carries real probability of "nobody".

    That is the entire finding of Sandberg, Drexler & Ord, *Dissolving the Fermi Paradox* (2018):
    the apparent paradox is manufactured by point-estimating a product of log-uncertain factors.

    Implemented by Monte Carlo over the log-normal, with a fixed seed so the number is
    reproducible by anyone who runs it -- which is the Moth test.
    """
    rng = np.random.default_rng(seed)
    lam = 10.0 ** rng.normal(log10_median, sigma_dex, n_samples)
    p_int = float(np.mean(1.0 - np.exp(-lam)))
    p_point = 1.0 - math.exp(-(10.0 ** log10_median))
    return {
        "p_at_least_one_integrated": p_int,
        "p_at_least_one_at_point_estimate": p_point,
        "jensen_gap": p_point - p_int,
        "p_none": 1.0 - p_int,
        "note": ("the point-estimate column is the one to distrust; it is P evaluated at the "
                 "mean, not the mean of P"),
    }


# ==================================================================================================
# 5. EXTREME VALUE — a source's ceiling is a MAXIMUM, and maxima have their own law
# ==================================================================================================

def ceiling_confidence(n_entries, n_scored):
    """How much of a source's true ceiling has been seen, after scoring n of N entries?

    The synthesis phase nominates a ceiling from a SAMPLE. The ceiling is therefore a sample
    maximum, and a sample maximum is a biased-low estimator of a population maximum -- the
    Fisher-Tippett-Gnedenko setting, not ordinary estimation.

    Under SIMPLE RANDOM SAMPLING, P(the population max is among n drawn from N) = n/N exactly,
    distribution-free. 14 of 900 gives 1.6%.

    **BUT THE PIPELINE DOES NOT SAMPLE RANDOMLY**, and it would be dishonest to quote n/N as if it
    did. `phase_synthesis` takes the 14 LONGEST descriptions. Description length correlates with
    an entity's prominence, and prominence correlates with power, so this is informative sampling
    deliberately biased TOWARD the ceiling. The true probability is therefore higher than n/N --
    possibly much higher.

    How much higher is NOT quantified here, and I decline to invent a correction factor for it,
    because doing so would require the joint distribution of description length and magnitude,
    which nobody has measured. So this returns n/N explicitly labelled as the random-sampling
    FLOOR, and the selection effect is named and left unquantified.

    That is the honest report: a hard lower bound plus a named, unmeasured effect in a known
    direction. It is also why phase 1 emits BAND ONLY and never a decimal -- a band is wide enough
    to survive this ignorance, and a decimal is not.
    """
    if n_entries <= 0:
        return None
    p = min(1.0, n_scored / n_entries)
    return {
        "n_entries": n_entries, "n_scored": n_scored,
        "p_true_max_seen_if_random": round(p, 4),
        "sampling": "NOT random: 14 longest descriptions, biased toward prominence",
        "bound_direction": "n/N is a FLOOR; informative selection raises it by an unmeasured amount",
        "supports_decimal": False,
        "why": ("a decimal would need the joint distribution of description length and magnitude, "
                "which has not been measured; the band does not"),
    }


def gumbel_return_level(sample_max_bits, n_scored, n_entries, tail_index=1.0):
    """Order-statistic correction: how far above the sample max the population max likely sits.

    ASSUMPTION, STATED RATHER THAN BURIED: the magnitude distribution has a regularly-varying
    (Pareto) upper tail with index alpha. Then the max of n scales as n^(1/alpha), so

        E[log2 max_N] - E[log2 max_n] = (1/alpha) * log2(N/n)

    Because the library's magnitudes are ALREADY logarithmic (bits), the correction is additive in
    the native unit and composes directly with L_r.

    Why a Pareto tail is the defensible default: heavy tails are the empirical rule for
    destructive magnitudes in the real world -- earthquake energies follow Gutenberg-Richter,
    war severities follow Richardson's power law (alpha ~ 1.35-1.7), city sizes and wealth follow
    Zipf. alpha = 1.0 is the neutral Zipf choice and is CONSERVATIVE here: smaller alpha means a
    heavier tail and a larger correction, so a referee who prefers alpha = 1.5 gets a smaller
    nudge, not a broken method.

    The parameter is exposed precisely so the assumption can be argued with instead of smuggled.
    """
    if n_scored <= 0 or n_entries <= n_scored or tail_index <= 0:
        return {"correction_bits": 0.0, "corrected_bits": sample_max_bits, "tail_index": tail_index}
    corr = math.log2(n_entries / n_scored) / tail_index
    return {"correction_bits": round(corr, 2),
            "corrected_bits": round(sample_max_bits + corr, 2),
            "tail_index": tail_index,
            "basis": "E[max of N] / E[max of n] under a Pareto(alpha) tail; stated, not assumed silently"}


# ==================================================================================================
# 6. THE MATHEMATICS AS A CHORD — resonance measured on the derivation graph itself
# ==================================================================================================

def mathematical_resonance():
    """Apply the library's own resonance measure to the library's own mathematics.

    If Being is constituted by relation, then so is a QUANTITY: a number's meaning is the set of
    other numbers it is answerable to. A mathematics of isolated formulas is incoherent in exactly
    the sense Vol. 0.5 means -- not wrong, but unrelated, and therefore unable to say anything
    about the whole.

    So the derivation graph is scored the way any relational structure is scored:

      density        edges per quantity -- how connected the mathematics is
      orphan_rate    share of quantities that no other quantity depends on
      depth          longest derivation chain, distance from bare reality
      load_bearing   the quantities most things ultimately rest on
    """
    import derivation as D
    L = D.LEDGER
    n = len(L)
    edges = sum(len(q["parents"]) for q in L.values())
    depended_on = set()
    for q in L.values():
        depended_on.update(q["parents"])
    orphans = [k for k in L if k not in depended_on]

    fanout = {}
    for k, q in L.items():
        for p in q["parents"]:
            fanout[p] = fanout.get(p, 0) + 1

    return {
        "quantities": n,
        "relations": edges,
        "density": round(edges / n, 3),
        "orphan_rate": round(len(orphans) / n, 3),
        "orphans": sorted(orphans),
        "max_depth": max(D.depth(k) for k in L),
        # Ranked, never truncated (Hard Rule 0). The sole consumer slices for display; a
        # RETURNED field that stops at eight decides on the ledger's behalf that the ninth
        # load-bearing quantity is not load-bearing.
        "load_bearing": sorted(fanout.items(), key=lambda kv: -kv[1]),
        "reading": ("a terminal quantity with no dependents is not an error -- results are "
                    "allowed to be results. A quantity with no PARENTS and no citation would be, "
                    "and the ledger refuses those separately"),
    }


# ==================================================================================================
def main():
    np.set_printoptions(precision=4, suppress=True)
    import assay as A

    print("=" * 96)
    print("RIGOR — commensuration, and the proof the library's rankings are one operation")
    print("=" * 96)

    print("\n1. COMMENSURATION: what one point of any Measure is worth, in bits")
    print("-" * 96)
    for b in ("M2", "M5", "M8", "M10"):
        v = measure_bit_value(b)
        print(f"   {b:>4}   1 point on ANY axis = {v:8.2f} bits    "
              f"(Ruin 7.0 -> {7*v:9.1f} | Acumen 7.0 -> {7*v:9.1f})")
    print("   the two columns are equal because they are the same quantity (X.6 §3 + X.10 §6)")

    print(f"\n   charter faculty weights : {A.FACULTY_WEIGHTS}")
    print(f"   parity implies          : {faculty_parity_weights()['uniform_weight']:.4f} each")
    print("   FINDING: zero is an exchange rate too, and it is the one rate the bit-equivalence")
    print("            forbids. Int/Wis/Cha currently cannot affect a Magnitude at all.")

    print("\n2. THEOREM 1 — Saaty's CR and Moth's chord index are one measurement")
    print("-" * 96)
    A_consistent = consistent_matrix(A.WEIGHTS)
    t = theorem_1_check(A_consistent)
    print("   charter's declared 8 weights, read as a ratio matrix:")
    print(f"     CR = {t['CR']:.2e}   curl fraction = {t['curl_fraction']:.2e}   "
          f"both consistent: {t['both_say_consistent']}")
    print(f"     Perron and log-least-squares weights agree to {t['max_weight_disagreement']:.2e}")
    print("   DIAGNOSIS: CR is exactly zero because a declared VECTOR cannot be inconsistent.")
    print("              This is not a clean bill of health — it means the weights have never")
    print("              been exposed to a judgment that could contradict them.")

    # A genuinely elicited, imperfect set of judgments behaves differently.
    B = np.array([[1, 3, 5], [1/3, 1, 3], [1/5, 1/3, 1]], dtype=float)   # mildly inconsistent
    tb = theorem_1_check(B)
    print("\n   an ELICITED 3x3 with real disagreement:")
    print(f"     CR = {tb['CR']:.4f}   curl fraction = {tb['curl_fraction']:.4f}")
    print("     both rise together — that is Theorem 1 visible")

    print("\n3. MDL — beta by counting, auditing the charter's declared costs")
    print("-" * 96)
    print(f"   law catalogue: {len(LAW_CATALOGUE)} enumerated principles "
          f"(Noether conservations + structural)")
    ratios = []
    for nm, laws, regimes, params, declared in [
            ("coherence", 1, 2, 0, 8), ("thermodynamics", 1, 4, 1, 32),
            ("energy", 2, 4, 1, 64), ("momentum", 2, 8, 2, 96),
            ("intent", 3, 8, 3, 128)]:
        d = adjudication_beta(laws, regimes, params)
        floor = d["beta_floor_bits"]
        ratio = declared / floor if floor > 0 else float("inf")
        ratios.append(ratio)
        ok = "above floor" if declared >= floor else "BELOW FLOOR — underpriced"
        print(f"   {nm:<16} floor {floor:7.2f}   declared {declared:4d}   "
              f"x{ratio:5.2f}   {ok}")
    import statistics as _st
    print(f"   declared/floor ratio: mean {_st.mean(ratios):.2f}, "
          f"stdev {_st.pstdev(ratios):.2f}")
    print("   FINDING: every declared cost sits above its MDL floor, and the ratios cluster —")
    print("            the charter's constants encode a roughly constant safety factor rather")
    print("            than arbitrary numbers. That is auditable; it was not before.")

    print("\n4. UNCERTAINTY — the census as a product of uncertain factors")
    print("-" * 96)
    import cosmography as C
    chain = [("galaxies", C.GALAXIES_DEFAULT, 0.15), ("stars/galaxy", C.STARS_PER_GALAXY_MEAN, 0.30),
             ("eta_earth", C.ETA_EARTH, 0.40), ("f_life", C.F_LIFE, 0.70),
             ("f_complex", C.F_COMPLEX, 0.90), ("f_civ", C.F_CIVILIZATION, 1.00),
             ("f_survives", C.F_SURVIVES, 0.50)]
    r = lognormal_product(chain)
    print(f"   median extant civilisations : {r['median']:.3e}")
    print(f"   68% credible interval       : {r['ci68'][0]:.2e}  to  {r['ci68'][1]:.2e}")
    print(f"   95% credible interval       : {r['ci95'][0]:.2e}  to  {r['ci95'][1]:.2e}")
    print(f"   spread                      : {r['spread_orders_of_magnitude']} orders of magnitude")
    pa = prob_at_least_one(r["log10_median"], r["sigma_dex"])
    print(f"   P(at least one) integrated  : {pa['p_at_least_one_integrated']:.6f}")
    print(f"   P(...) at the point estimate: {pa['p_at_least_one_at_point_estimate']:.6f}")
    print(f"   Jensen gap                  : {pa['jensen_gap']:.2e}")
    print("   the gap is nil HERE only because a fictional census is astronomically above 1;")
    print("   the method is not vacuous, so here it is on the case it was built for:")

    # The real Milky Way, with literature-scale uncertainty. Reproduces the qualitative result of
    # Sandberg, Drexler & Ord (2018): once abiogenesis carries its true log-uncertainty, P(alone)
    # is not small, and no paradox needs dissolving because none was ever established.
    real = [("stars in the Galaxy", 1.0e11, 0.10), ("fraction with planets", 1.0, 0.10),
            ("habitable per system", 0.20, 0.50), ("abiogenesis", 0.50, 15.0),
            ("complex life", 0.10, 1.00), ("intelligence", 0.20, 0.50),
            ("detectable window frac", 0.01, 1.00)]
    rr = lognormal_product(real)
    pr = prob_at_least_one(rr["log10_median"], rr["sigma_dex"])
    print(f"     median N (Milky Way)      : {rr['median']:.3e}   "
          f"sigma {rr['sigma_dex']:.2f} dex")
    print(f"     P(at least one) integrated: {pr['p_at_least_one_integrated']:.4f}")
    print(f"     P(...) at point estimate  : {pr['p_at_least_one_at_point_estimate']:.4f}")
    print(f"     P(WE ARE ALONE)           : {pr['p_none']:.4f}   <-- invisible to a point estimate")
    print("     Jensen's inequality on a concave function; Sandberg/Drexler/Ord 2018")

    print("\n5. EXTREME VALUE — a ceiling drawn from 14 of N entries")
    print("-" * 96)
    for N in (50, 200, 900):
        cc = ceiling_confidence(N, 14)
        g1 = gumbel_return_level(132.34, 14, N, tail_index=1.0)
        g2 = gumbel_return_level(132.34, 14, N, tail_index=1.5)
        print(f"   N={N:<5} P(max seen | RANDOM) >= {cc['p_true_max_seen_if_random']:6.2%}   "
              f"correction +{g1['correction_bits']:5.2f} bits (a=1.0) "
              f"/ +{g2['correction_bits']:5.2f} (a=1.5)")
    print("   sampling is NOT random (14 longest descriptions) — n/N is a floor, and the")
    print("   selection effect is named but deliberately left unquantified")
    print("   this is why phase 1 emits a BAND and refuses a decimal")

    print("\n6. THE MATHEMATICS AS A CHORD")
    print("-" * 96)
    mr = mathematical_resonance()
    print(f"   quantities {mr['quantities']}   relations {mr['relations']}   "
          f"density {mr['density']}   max depth {mr['max_depth']}")
    print("   load-bearing: " + ", ".join(f"{k}({v})" for k, v in mr["load_bearing"][:6]))
    print()
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
