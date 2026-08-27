#!/usr/bin/env python3
"""
THE SEVENFOLD ORDER — seven hyperverses, and a span of one to seven at every tier beneath.

AN AUTHORIAL DECLARATION, AND WHY THAT IS THE RIGHT KIND OF ANSWER HERE
----------------------------------------------------------------------
Four passes tried to DISCOVER the upper tiers from the corpus and each failed differently:

    unsupervised clustering   found coincidental common nouns -- 'dark', 'void', 'magic'
    pantheon seeds            left every godless fiction homeless
    medium                    covered everything and was a META fact, which the charter bans
    grounding type            was meaningful per source and would not NEST; pooled per xenoverse
                              it nested and went degenerate, because one xenoverse held 70% of
                              the corpus and its grounding became a four-way coin flip

The common failure is not in any of those metrics. It is that similarity is LUMPY. Real corpora
cluster into one giant mass and a long tail, at every threshold and by every measure, and no
amount of better measurement turns a lumpy thing into a balanced one. A shelving system built on
similarity inherits the lumps.

So the owner's ruling: stop discovering, and declare. Seven hyperverses, and a span of ONE TO
SEVEN at every tier beneath. Axiom M3 used for what it is for -- a convention, chosen, published,
frozen: "promises, not truths."

A RANGE, NOT A FIXED ARITY, AND THE DIFFERENCE IS THE WHOLE DESIGN
------------------------------------------------------------------
A first build read the ruling as exactly seven everywhere and it came out wrong in a way worth
recording: forcing seven children onto every parent left slot 6 empty across a whole tier and made
the universe level lopsided at [111 ... 376], because it was cutting where there was nothing to
cut. Uniform arity does not produce order; it produces the appearance of order with padding
underneath.

The range does. SEVEN is a bound, not a quota:

    hyperverse   exactly 7      the declared root
    xenoverse    1-7 per hyperverse
    metaverse    1-7 per xenoverse
    multiverse   1-7 per metaverse
    universe     1-7 per multiverse

So a hyperverse with one xenoverse in it is not a defective hyperverse, and a metaverse holding a
single multiverse is not an error. The shape is declared and the COUNT is read from the material.

WHAT IS DECLARED AND WHAT IS STILL MEASURED
-------------------------------------------
DECLARED  the root count, and the bound of seven.
MEASURED  how many children a parent actually has, and which child a thing goes in. Cuts fall at
          the weakest seams of the affinity ordering, so sources that resonate stay together --
          Alien and Predator share all three source tiers, as do Call of Duty Zombies and Black
          Ops. Throwing that away to honour a convention would be discarding a measurement for a
          promise.

Order imposed on chaos, with the chaos choosing where the joins fall. Which is the point.

ON THE SIX-DEGREE PROPERTY
--------------------------
A seven-ary tree five deep puts two leaves up to ten steps apart, which is not the diameter-5 the
resonance graph measures. Both are true and they are not in competition: this tree is how things
are FILED, and the resonance graph is how news TRAVELS. A library's shelf order was never its
citation graph. Vol. X.7's propagation still runs on the resonance graph, untouched.
"""
import argparse
import collections
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence                                                          # noqa: E402

SPAN = 7
TIERS = ("hyperverse", "xenoverse", "metaverse", "multiverse", "universe")
CAPACITY = SPAN ** len(TIERS)


def affinity_order(members, weights):
    """Order members so that strongly-linked ones sit adjacent.

    A greedy nearest-neighbour walk over the resonance weights. Not optimal -- optimal linear
    arrangement is NP-hard and the gain would not show on a shelf -- but it keeps kin together,
    which is the whole reason placement is measured rather than declared alongside the shape.
    """
    if not members:
        return []
    remaining = set(members)
    start = max(members, key=lambda m: sum(weights.get((m, o), weights.get((o, m), 0.0))
                                           for o in members))
    order = [start]
    remaining.discard(start)
    while remaining:
        last = order[-1]
        nxt = max(remaining,
                  key=lambda m: (weights.get((last, m), weights.get((m, last), 0.0)), m))
        order.append(nxt)
        remaining.discard(nxt)
    return order


def shelve(members, weights, span=SPAN, depth=len(TIERS)):
    """Place members into a span-ary tree of the given depth, balanced and affinity-ordered.

    Balance is by construction: the ordered list is cut into `span` contiguous blocks at each
    level, so no branch can swell into the giant component that wrecked every discovered scheme.
    """
    order = affinity_order(members, weights) if weights else sorted(members)
    coords = {m: [] for m in order}

    def seams(block):
        """Where the affinity ordering is weakest -- the natural places to cut.

        The declaration bounds the branching at seven; it does not FIX it there. Forcing exactly
        seven children everywhere produced empty slots on small blocks and a lopsided universe
        tier, because it was cutting where there was nothing to cut.

        So the count is read from the material and clamped by the rule: order the block by
        affinity, measure each adjacent seam, and cut at the weakest ones -- at most six cuts,
        giving at most seven children, and fewer wherever the block does not want dividing. Order
        imposed on chaos, with the chaos choosing where the joins fall.
        """
        if len(block) < 2:
            return []
        gaps = []
        for i in range(len(block) - 1):
            a, b = block[i], block[i + 1]
            gaps.append((weights.get((a, b), weights.get((b, a), 0.0)), i))
        # As many children as the block can support, never more than the declared span.
        k = max(1, min(span, len(block)))
        # NO SIGNAL TO READ. Every `build()` call for a source's WORLDS passes `weights={}`
        # (worldseed computes no pairwise affinity within a source), so every gap above defaults
        # to the same 0.0 and `gaps.sort()` -- stable -- leaves them in original-index order.
        # Slicing the first k-1 of THAT is not "the weakest seams", it is "the first six
        # positions", and it produced exactly the giant component this function's own docstring
        # says can't happen: shelve([100 members], {}, depth=2) gave one child everything past
        # the sixth member. When nothing distinguishes the seams there is nothing to prefer, so
        # divide the block into `k` evenly sized pieces instead of clustering every cut at one
        # end of it.
        if len({g for g, _ in gaps}) <= 1:
            step = len(block) / k
            cuts = {min(max(round(step * j), 1), len(block) - 1) - 1 for j in range(1, k)}
            return sorted(cuts)
        gaps.sort()
        return sorted(i for _, i in gaps[:k - 1])

    def split(block, level):
        if level >= depth or not block:
            return
        cuts = seams(block)
        bounds = [0] + [c + 1 for c in cuts] + [len(block)]
        child = 0
        for lo, hi in zip(bounds, bounds[1:]):
            chunk = block[lo:hi]
            if not chunk:
                continue
            for m in chunk:
                coords[m].append(child)
            split(chunk, level + 1)
            child += 1

    split(order, 0)
    for m in coords:                          # pad shallow branches with slot 0
        while len(coords[m]) < depth:
            coords[m].append(0)
    return {m: dict(zip(TIERS, c)) for m, c in coords.items()}


def shelfmark(coord, galaxy=None, planet=None):
    """Render whatever tiers this coordinate carries.

    A SOURCE occupies the top three; only a WORLD reaches Mv and U. Printing a source as though
    it had a universe number would invent a position, so the mark simply stops where the
    coordinate does.
    """
    label = {"hyperverse": "H", "xenoverse": "X", "metaverse": "Mt.",
             "multiverse": "Mv.", "universe": "U-"}
    parts = [f"{label[t]}{coord[t]}" for t in TIERS if t in coord]
    if galaxy is not None:
        parts.append(f"G.{galaxy:x}")
    if planet is not None:
        parts.append(f"P.{planet}")
    return "Ω › " + " › ".join(parts)


SOURCE_TIERS = ("hyperverse", "xenoverse", "metaverse")     # 7^3 = 343 slots for 209 sources
WORLD_TIERS = ("multiverse", "universe")                    # filled from within each source


def build():
    """Two-stage shelving, because a population must be able to FILL the tree it is put in.

    A first attempt pushed all 209 sources through five levels and the bottom two collapsed --
    every source landed in Mv.0 and U-0, because by the fourth split each chunk held one member
    and there was nothing left to divide. Seven-ary depth five wants 16,807 leaves; 209 sources
    cannot supply them.

    They do not have to. A source is not a universe -- it is a body of them, and the worlds inside
    it fill the lower tiers. So sources are shelved across the top three (343 slots, comfortably
    more than 209) and each source's own worlds across the bottom two. Every tier then has a
    population that can actually occupy it.
    """
    import tiers as TI
    import worldseed as WS
    srcs, w, shared = TI._graph()

    top = shelve(srcs, w, depth=len(SOURCE_TIERS))
    coords = {s: {t: top[s][t] for t in SOURCE_TIERS} for s in srcs}

    by_source = {}
    for world in WS.build_all():
        by_source.setdefault(world["designation"].split("::")[0], []).append(world)

    worlds = {}
    for src, ws in by_source.items():
        base = coords.get(src)
        if base is None:
            continue
        names = [x["designation"] for x in ws]
        inner = shelve(names, {}, depth=len(WORLD_TIERS))
        for d in names:
            worlds[d] = dict(base)
            worlds[d]["multiverse"] = inner[d]["hyperverse"]
            worlds[d]["universe"] = inner[d]["xenoverse"]
    return srcs, coords, w, worlds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    srcs, coords, w, worlds = build()
    print("=" * 96)
    print("THE SEVENFOLD ORDER — seven at every tier, declared")
    print("=" * 96)
    print(f"\nsources shelved : {len(coords)}")
    print(f"capacity        : {CAPACITY:,} universe slots ({SPAN}^{len(TIERS)})")
    print(f"occupancy       : {len(coords)/CAPACITY:.2%}  — sparse by design")

    print("\nbalance at each tier (the property every discovered scheme failed):")
    print(f"worlds shelved  : {len(worlds):,}")
    print()
    print(f"{'tier':<12}{'children per parent':<24}{'occupancy'}")
    for i, t in enumerate(TIERS):
        pool = coords if t in SOURCE_TIERS else worlds
        parents = collections.defaultdict(set)
        for v in pool.values():
            if t not in v:
                continue
            key = tuple(v[x] for x in TIERS[:i] if x in v)
            parents[key].add(v[t])
        if not parents:
            continue
        counts = sorted(len(x) for x in parents.values())
        lo, hi = counts[0], counts[-1]
        # m30, same shape as custodes' covers_every_reading: `seams()` already clamps every child
        # count to SPAN, so "OVER SPAN" cannot print for any input. This displays a GUARANTEE, not
        # a discovery. Kept because it states the bound where a reader looks for it; it becomes a
        # real check only if seams() ever stops clamping.
        ok = "OK" if hi <= SPAN else "OVER SPAN"
        print(f"{t:<12}{f'{lo}-{hi}':<24}{len(parents)} parents   {ok}")

    print("\naffinity preserved — strongly linked sources shelved together:")
    for a, b in (("Alien", "Predator"), ("Call of Duty Zombies", "all Black Ops"),
                 ("Pantheon: Greek", "Pantheon: Roman")):
        if a in coords and b in coords:
            ca, cb = coords[a], coords[b]
            same = [t for t in SOURCE_TIERS if ca[t] == cb[t]]
            print(f"   {a[:24]:<26}{b[:24]:<26}share {len(same)}/{len(SOURCE_TIERS)}: {same}")

    print("\nsample shelfmarks:")
    for s in sorted(coords)[:8]:
        print(f"   {s[:34]:<36}{shelfmark(coords[s])}")

    print("\nsample WORLD shelfmarks — the leaves the tier system exists for:")
    for d in sorted(worlds)[:8]:
        print(f"   {d[:42]:<44}{shelfmark(worlds[d])}")

    if args.write:
        p = os.path.join(HERE, "data", "SEVENFOLD.json")
        # ATOMIC -- the m100 tail, 2026-08-25.
        # GATED: `write_json` returns whether the rename LANDED, and this discarded the verdict
        # and printed "wrote {p}" regardless -- the one line in this module that argues writes
        # must be gated (see catalogue_aurora.py, scope.py, same run #33 sweep) and then did not
        # gate its own.
        landed = silence.write_json(p, {"span": SPAN, "sources": coords, "worlds": worlds},
                                    indent=2, ensure_ascii=False)
        print(f"\nwrote {p}" if landed else f"\nWRITE DENIED: {p} did not land; rerun to retry")
    return 0


if __name__ == "__main__":
    sys.exit(main())
