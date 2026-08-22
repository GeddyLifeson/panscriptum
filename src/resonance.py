#!/usr/bin/env python3
"""
RESONANCE — the relational ontology, made computable.

THE CORRECTION THIS FILE EXISTS TO MAKE
---------------------------------------
Vol. 0.5's first draft treated Resonantism as an EPISTEMOLOGY: an account of how Custodes know,
cashed out as Bayesian priors. That is true and it is secondary. The philosophy's first line is
an ONTOLOGY -- *Being is constituted by relation* -- a claim about what things ARE, not about how
they are known. Read that way, it is not an addition to the charter's mathematics. It is the
thing that mathematics already discovered and had no name for.

FOUR PLACES THE CHARTER IS ALREADY RELATIONAL
---------------------------------------------
1. POWER IS NEVER A PROPERTY. X.2 Definition 4 defines the capability preorder A ⪰ B iff
   C_B ⊆ C_A -- strength is a relation *between* agents. Nothing anywhere in the charter defines
   an agent's power intrinsically. There is no such quantity to define.

2. INCOMPARABILITY IS STRUCTURAL, NOT MISSING DATA. Proposition 1 establishes agents A, B with
   A ⋡ B and B ⋡ A. Two things, both true, neither greater. That is Coexistent Contradiction
   stated as an order-theoretic fact, and Theorem 1 (no lossless scalarization) follows from it.

3. THE CURL IS THE RESIDUE OF RELATION. X.2 §5 decomposes contest flow as
   F = grad(θ) ⊕ curl ⊕ harmonic. The gradient is the best-fitting ladder; the curl is
   irreducible non-transitivity -- the cycles where A beats B beats C beats A.

4. AND MOTH SAID IT OUTRIGHT. "The omniverse is not a ladder; it is a chord" IS the statement
   η < 1, and η is measurable. A chord is simultaneous distinct tones held in tension without
   resolving to one -- which is Resonantism's thesis, arrived at from paired-comparison
   statistics by a man who thought he was doing bookkeeping.

WHAT THIS MODULE PROVIDES
-------------------------
η, the consistency index, as THE MEASURE OF COEXISTENT CONTRADICTION: the fraction of relational
reality a ranking can represent. 1 - η is the part that is irreducibly chord rather than ladder,
and Theorem 2 says no scalar assay can do better than that bound. It also provides the
incomparability rate on axis vectors, and reads resonance strength off the shared-stage graph --
so that "these two things are in relation" is a number everywhere it is claimed.
"""
import collections
import itertools
import json
import math
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ============================================================ 1. THE CURL AND THE INDEX (η)

def hodge_decompose(edges):
    """Least-squares HodgeRank: split a pairwise flow into gradient (ranking) + residual (curl).

    `edges` maps (a, b) -> flow, read as "a beats b by this much" (antisymmetric: F(b,a) = -F(a,b)).

    Solves min over theta of sum (F_ab - (theta_a - theta_b))^2 -- the best-fitting ladder. What
    the ladder cannot explain is the curl, and its share is what Theorem 2 bounds every scalar
    assay's error by.

    Implemented as plain Gauss-Seidel on the graph Laplacian: no dependencies, and the whole point
    is that a Hand must be able to recompute it.
    """
    nodes = sorted({n for e in edges for n in e})
    idx = {n: i for i, n in enumerate(nodes)}
    theta = {n: 0.0 for n in nodes}

    nbrs = collections.defaultdict(list)
    for (a, b), f in edges.items():
        nbrs[a].append((b, f))
        nbrs[b].append((a, -f))

    # theta_a = mean over neighbours of (theta_b + F_ab)
    for _ in range(600):
        new = {}
        for n in nodes:
            if not nbrs[n]:
                new[n] = theta[n]
                continue
            new[n] = sum(theta[b] + f for b, f in nbrs[n]) / len(nbrs[n])
        shift = sum(new.values()) / len(new)          # gauge-fix: mean zero
        theta = {n: v - shift for n, v in new.items()}

    grad_sq = res_sq = 0.0
    for (a, b), f in edges.items():
        g = theta[a] - theta[b]
        grad_sq += g * g
        res_sq += (f - g) ** 2

    total = grad_sq + res_sq
    eta = (grad_sq / total) if total > 0 else 1.0
    return {
        "theta": {n: round(v, 4) for n, v in theta.items()},
        "eta": round(eta, 4),
        "curl_fraction": round(1.0 - eta, 4),
        "ladder_representable": round(eta * 100, 1),
        "irreducibly_chord": round((1.0 - eta) * 100, 1),
        "theorem_2_error_floor": round(1.0 - eta, 4),
    }


# ==================================================== 2. INCOMPARABILITY (Proposition 1)

def dominates(v1, v2):
    """Does v1 dominate v2 on every scored axis? The capability preorder, componentwise."""
    shared = [k for k in v1 if k in v2 and v1[k] is not None and v2[k] is not None]
    if not shared:
        return False
    return all(v1[k] >= v2[k] for k in shared) and any(v1[k] > v2[k] for k in shared)


def incomparability_rate(vectors):
    """Fraction of pairs that are INCOMPARABLE -- neither dominates.

    Proposition 1 says these exist. This says how common they are, which is the empirical content
    of "the omniverse is not a ladder". An incomparable pair is not an unresolved question; it is
    a resolved finding that no ordering exists between two things.
    """
    names = sorted(vectors)
    total = inc = 0
    examples = []
    for a, b in itertools.combinations(names, 2):
        total += 1
        va, vb = vectors[a], vectors[b]
        if not dominates(va, vb) and not dominates(vb, va):
            inc += 1
            if len(examples) < 5:
                examples.append((a, b))
    return {"pairs": total, "incomparable": inc,
            "rate": round(inc / total, 4) if total else None,
            "examples": examples}


# ============================================ 3. RESONANCE STRENGTH (the shared-stage graph)

def resonance_strength(a, b, graph_path=None):
    """How strongly are two shelves in relation? Reads the co-attestation weight directly.

    This is the ontology's operational form: two things are related to the degree they share
    furniture, and that degree is a number rather than an assertion. Everything downstream --
    propagation delay, cosmological clustering, entity resolution -- is this quantity wearing a
    different hat.
    """
    path = graph_path or os.path.join(HERE, "data/SHARED_STAGE_GRAPH.json")
    with open(path, encoding="utf-8") as f:
        g = json.load(f)
    for p in g["pairs"]:
        if {p["a"], p["b"]} == {a, b}:
            return {"weight": p["weight"], "shared": p.get("shared_sample", []),
                    "in_resonance": True}
    return {"weight": 0.0, "shared": [], "in_resonance": False,
            "note": "no shared furniture at this remove; relation is mediated, not direct"}
