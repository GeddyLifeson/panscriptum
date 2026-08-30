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

WHAT IS ACTUALLY WIRED, AS OF 2026-08-28 — READ THIS BEFORE TRUSTING ANY OF THE ABOVE
-------------------------------------------------------------------------------------
This module has NO PRODUCTION CALLER. Not a reduced one; none. Order f467f662be4b established
it and nothing here disputes it:

    hodge_decompose      zero callers anywhere in `src/`.
    resonance_strength   zero callers anywhere in `src/`.
    incomparability_rate called only by `verify_math.py`, which unit-tests its unmeasured/tied/
                         incomparable split. Exercised, never consulted.
    dominates            called only by `incomparability_rate`, above.

The consequence is specific and it is not academic. `custodes.convene()` gives Threnody -- the
one standpoint that can REFUSE the output rather than shift it -- a veto that fires when the
curl fraction clears Saaty's bar, and the eta that veto reads comes from `hodge_decompose`.
Since nothing calls `hodge_decompose`, nothing computes that eta, and `anchors.py:190`, the sole
real caller of `convene()`, passes none. So eta 1.0 is never asserted and the veto is never
declined; it is simply never asked. Every scalar the library has published was published without
anyone having measured whether a scalar was faithful to it.
// This is the fourth property from HARD RULE -1: a safety that exists in a file is not a safety
// that is running. It has been unreachable from anything the library actually prints for weeks.
//
// AND THIS PARAGRAPH USED TO SAY "the arithmetic below is correct and has been correct for
// weeks", WHICH WAS FALSE (order 6e1c72cddfeb). The sweep in `hodge_decompose` was plain Jacobi
// on the graph Laplacian, which does not converge on a BIPARTITE component -- so an exact,
// zero-residual ladder as ordinary as "one entity beats three others" measured eta 0.0: 100%
// irreducibly chord, theorem_2_error_floor 1.0, with `no_evidence` False, i.e. shaped exactly
// like a confident measurement. It is Gauss-Seidel now, with a convergence test, and it must
// stay that way; the reasoning and the measured before/after are in that function's docstring.
// The one mercy in the timing is that nothing consumed the wrong number.

WIRING IT IS A CHANGE IN `anchors.py`, NOT HERE, and it needs a real input rather than a call:
`hodge_decompose` consumes a pairwise contest flow, and the library does not currently build one
per being. `convene()` reports the gap as an explicit Threnody abstention in the meantime, so no
published interval can be mistaken for one that cleared the veto. Left as an OPEN order.
"""
import collections
import itertools
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ============================================================ 1. THE CURL AND THE INDEX (η)

SWEEP_BUDGET = 5000
SWEEP_TOL = 1e-9


def hodge_decompose(edges, sweeps=SWEEP_BUDGET, tol=SWEEP_TOL):
    """Least-squares HodgeRank: split a pairwise flow into gradient (ranking) + residual (curl).

    `edges` maps (a, b) -> flow, read as "a beats b by this much" (antisymmetric: F(b,a) = -F(a,b)).

    Solves min over theta of sum (F_ab - (theta_a - theta_b))^2 -- the best-fitting ladder. What
    the ladder cannot explain is the curl, and its share is what Theorem 2 bounds every scalar
    assay's error by.

    GAUSS-SEIDEL, AND THE METHOD IS LOAD-BEARING, NOT A STYLE CHOICE (order 6e1c72cddfeb).
    This was plain JACOBI (every neighbour term read out of the previous sweep's theta) under a
    fixed 600-sweep budget, and Jacobi on the graph Laplacian has iteration matrix D^-1 A, which
    has an eigenvalue of -1 on any BIPARTITE component. Theta there oscillates with period 2 for
    ever; the gauge-fix below subtracts the constant mode, not the alternating one; and the fixed
    budget then sampled whichever phase parity 600 happened to land on. Measured before the fix:

        STAR (a beats b, c and d -- one entity beating three others, the commonest contest
        shape there is)                                    -> eta 0.0, truth 1.0
        BIPARTITE 4x4, every hero beats every villain by 1.0, exactly reproduced by
        theta_h=+0.5 / theta_v=-0.5                        -> eta 0.0, truth 1.0
        4-node PATH a>b>c>d                                -> eta 0.8889, truth 1.0
        theta[h1] over the first eight sweeps of the 4x4   -> 1, 0, 1, 0, 1, 0, 1, 0

    and at sweeps=599 eta came out 0.8, at 600 eta 0.0, at 601 eta 0.8 -- NO budget reaches the
    right answer, because the sequence does not converge. So the run #33 sweep's correction went
    the wrong way: it renamed the method to match the loop when the loop should have been changed
    to match the name. Gauss-Seidel -- each node updated IN PLACE, reading neighbours already
    refreshed this sweep -- converges on a symmetric positive-semidefinite consistent system
    (the divergence of an antisymmetric flow is orthogonal to the constant nullspace, so this one
    is consistent), bipartite or not. Measured after: STAR, BIPARTITE 4x4 and PATH4 all reach
    eta 1.0 in 2, 2 and 18 sweeps; the 3-cycle and the 4-cycle still give eta 0.0 in one sweep,
    which is the right answer for a pure curl.

    AND THE BUDGET IS NO LONGER TRUSTED SILENTLY. The loop stops when the largest per-node shift
    falls below `tol`, and if it exhausts `sweeps` instead, this returns `converged: False` with
    eta and everything derived from it as None. An eta read off an unconverged iteration is the
    exact failure this module is about -- a confident measurement of nothing -- and it was
    especially dangerous here because it erred toward "the omniverse is MAXIMALLY
    non-transitive" while `no_evidence` came back False.
    """
    nodes = sorted({n for e in edges for n in e})
    if not nodes:
        # NO EVIDENCE, NOT A CONSISTENT LADDER (order 40b61d3a8c68). An empty edge set used to
        # divide by zero (`len(new)` below is 0) rather than report anything -- and the fallback
        # for the OTHER zero-signal case (an all-zero flow, `total == 0` below) returned
        # `eta = 1.0`, the same number a genuinely perfectly-consistent ladder produces. "No
        # contest data" and "perfect consistency" must not share an answer: that is this
        # module's own signature failure, applied to itself. `eta` and everything derived from
        # it come back None here, with `no_evidence: True` so a caller can tell the two apart.
        return {"theta": {}, "eta": None, "curl_fraction": None, "ladder_representable": None,
                "irreducibly_chord": None, "theorem_2_error_floor": None, "no_evidence": True,
                "converged": None, "sweeps": 0}
    theta = {n: 0.0 for n in nodes}

    nbrs = collections.defaultdict(list)
    for (a, b), f in edges.items():
        nbrs[a].append((b, f))
        nbrs[b].append((a, -f))

    # ASSERTED ONCE, NOT TESTED EVERY SWEEP AND NEVER TRUE (order 9803b72711b3). The sweep below
    # carried `if not nbrs[n]: new[n] = theta[n]; continue`, a branch that cannot execute:
    # `nodes` is built from the edge keys themselves and the loop above appends to `nbrs[a]` and
    # `nbrs[b]` for every one of them, so every member of `nodes` necessarily has a neighbour.
    # Verified across three edge sets -- no node with an empty neighbour list in any of them.
    # A defence that has never refused anything is the mechanical shape `liveness.py` exists to
    # catch, and it sat in the module whose docstring is about safeties that are not in effect.
    # Kept as a real check rather than deleted: if the construction above ever changes, the
    # alternative to this line is a ZeroDivisionError from inside the sweep with no name on it.
    _isolated = [n for n in nodes if not nbrs[n]]
    if _isolated:
        # Named in full, not sampled: this can only fire on a construction bug, and the names
        # are the whole diagnosis (Hard Rule 0).
        raise ValueError("hodge_decompose: %d node(s) built from the edge set have no neighbour "
                         "(%s) -- the adjacency construction above is broken, and the sweep "
                         "would divide by zero" % (len(_isolated), ", ".join(map(str, _isolated))))

    # theta_a = mean over neighbours of (theta_b + F_ab), UPDATED IN PLACE so the rest of this
    # sweep sees the refreshed value -- that in-place read is the whole difference between
    # Gauss-Seidel and the Jacobi sweep that never converged on a bipartite component.
    converged = False
    used = 0
    for used in range(1, sweeps + 1):
        prev = theta
        theta = dict(theta)
        for n in nodes:
            theta[n] = sum(theta[b] + f for b, f in nbrs[n]) / len(nbrs[n])
        mean = sum(theta.values()) / len(theta)       # gauge-fix: mean zero
        theta = {n: v - mean for n, v in theta.items()}
        # THE LARGEST PER-NODE SHIFT, not the mean of them: a mean shift hides one node still
        # swinging behind a hundred that have settled, and one unsettled node is an unsettled
        # theta. Measured against the gauge-fixed values, so the fix itself cannot register as
        # movement.
        if max(abs(theta[n] - prev[n]) for n in nodes) < tol:
            converged = True
            break
    if not converged:
        # NO ETA AT ALL RATHER THAN AN ETA NOBODY CAN TRUST. This is the fail-closed direction:
        # the caller that reads this is `custodes.convene()`'s Threnody curl-veto, and a wrong
        # eta there is a veto that fires or abstains on arithmetic that never settled.
        return {"theta": {n: round(v, 4) for n, v in theta.items()}, "eta": None,
                "curl_fraction": None, "ladder_representable": None,
                "irreducibly_chord": None, "theorem_2_error_floor": None,
                "no_evidence": False, "converged": False, "sweeps": used,
                "why": "the iteration did not settle within %d sweeps (tol %g) -- there IS "
                       "evidence here, but no measurement of it" % (sweeps, tol)}

    grad_sq = res_sq = 0.0
    for (a, b), f in edges.items():
        g = theta[a] - theta[b]
        grad_sq += g * g
        res_sq += (f - g) ** 2

    total = grad_sq + res_sq
    # `total == 0` means every edge carried zero flow -- no signal to decompose, not a decomposed
    # signal that happens to be perfectly consistent. Same "no evidence != eta 1.0" distinction
    # as the empty-`nodes` case above; see that comment.
    eta = (grad_sq / total) if total > 0 else None
    if eta is None:
        return {"theta": {n: round(v, 4) for n, v in theta.items()}, "eta": None,
                "curl_fraction": None, "ladder_representable": None,
                "irreducibly_chord": None, "theorem_2_error_floor": None, "no_evidence": True,
                "converged": True, "sweeps": used}
    return {
        "theta": {n: round(v, 4) for n, v in theta.items()},
        "eta": round(eta, 4),
        "curl_fraction": round(1.0 - eta, 4),
        "ladder_representable": round(eta * 100, 1),
        "irreducibly_chord": round((1.0 - eta) * 100, 1),
        "theorem_2_error_floor": round(1.0 - eta, 4),
        "no_evidence": False,
        # REPORTED, NOT ASSUMED. Every dict this function returns now carries the same two keys,
        # so "did the arithmetic settle?" is answerable from the result rather than from the
        # budget the caller hopes was enough.
        "converged": True,
        "sweeps": used,
    }


# ==================================================== 2. INCOMPARABILITY (Proposition 1)

def dominates(v1, v2):
    """Does v1 dominate v2 on every scored axis? The capability preorder, componentwise."""
    shared = [k for k in v1 if k in v2 and v1[k] is not None and v2[k] is not None]
    if not shared:
        return False
    return all(v1[k] >= v2[k] for k in shared) and any(v1[k] > v2[k] for k in shared)


def incomparability_rate(vectors):
    """Fraction of DECIDABLE pairs that are INCOMPARABLE -- neither dominates, on shared data.

    Proposition 1 says these exist. This says how common they are, which is the empirical content
    of "the omniverse is not a ladder". An incomparable pair is not an unresolved question; it is
    a resolved finding that no ordering exists between two things -- which is exactly what a pair
    with no shared scored axis is NOT (there is no data to find anything with) and what an
    identical pair is NOT (the ordering is resolved as equal, not absent). `dominates()` answers
    False for both of those for an unrelated reason -- no axis clears its `any(v1[k] > v2[k])`
    strict-inequality test -- so counting "neither dominates" as incomparable folded both into
    the numerator. They are now split out: UNMEASURED (no shared axis) is excluded from the rate
    entirely, and TIED (dominates both ways on equality, i.e. identical on every shared axis) is
    counted as a decided pair but not an incomparable one.

    `examples` IS EVERY INCOMPARABLE PAIR, NOT THE FIRST FIVE (order 89fc2eaf23f1, Hard Rule 0).
    This was `if len(examples) < 5`, capping a list in a RETURN VALUE rather than in a print --
    so 20 vectors with 40 incomparable pairs handed the caller five of them with nothing in the
    dict distinguishing "five examples" from "five incomparable pairs exist". The count was
    recoverable from `incomparable` beside it; the roster was not, and the roster is the evidence.
    A caller that wants a sample can take one, knowing what it is a sample of.
    """
    names = sorted(vectors)
    total = unmeasured = tied = inc = 0
    examples = []
    for a, b in itertools.combinations(names, 2):
        total += 1
        va, vb = vectors[a], vectors[b]
        shared = [k for k in va if k in vb and va[k] is not None and vb[k] is not None]
        if not shared:
            unmeasured += 1
            continue
        if all(va[k] == vb[k] for k in shared):
            tied += 1
            continue
        if not dominates(va, vb) and not dominates(vb, va):
            inc += 1
            examples.append((a, b))
    decidable = total - unmeasured
    return {"pairs": total, "unmeasured": unmeasured, "tied": tied, "incomparable": inc,
            "rate": round(inc / decidable, 4) if decidable else None,
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
