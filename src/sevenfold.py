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
import itertools
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


def _even_cuts(n_members, k):
    """The k-1 cut positions of an exactly even split of `n_members`. -> sorted list.

    Positions are gap indices: cutting after block[i]. Clamped into [0, n_members-2] so a cut can
    never produce an empty chunk, and deduplicated for the case where k exceeds what the block
    can actually be divided into.
    """
    step = n_members / k
    return sorted({min(max(int(round(step * j)), 1), n_members - 1) - 1 for j in range(1, k)})


def shelve(members, weights, span=SPAN, depth=len(TIERS)):
    """Place members into a span-ary tree of the given depth, balanced and affinity-ordered.

    BALANCE IS BY CONSTRUCTION, AND THE BOUND IS NOW A REAL ONE. This said "the ordered list is
    cut into `span` contiguous blocks at each level, so no branch can swell into the giant
    component" while `seams()` was free to put every cut at one end of the block -- and on the
    live shelving it did: the largest single address held 38 sources and the top tier's seven
    branches ran from 1 member to 66 (order 2a48315d26e6). What bounds it now is that every cut
    is chosen within half a step of its even-split boundary, so each child holds between roughly
    half and one and a half times its even share, at every level, whatever the weights say.
    Measured after the change on the same 209 sources: top branches 15-45 (was 1-66), 36 sources
    sharing an address (was 106), largest address 2 (was 38). `main()` prints MEMBERS PER BRANCH
    so the property is measured on every run rather than asserted in this docstring.
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
        # A WEAKEST SEAM NEAR EACH EVEN BOUNDARY, WHICH IS THE ONLY FORM OF THIS THAT KEEPS THE
        # BALANCE PROMISE (order 2a48315d26e6). Two earlier shapes of this code and why neither
        # holds:
        #
        # 1. `gaps.sort(); gaps[:k-1]` -- the k-1 GLOBALLY weakest seams, wherever they fall.
        #    Every `build()` call for a source's WORLDS passes `weights={}` (worldseed computes
        #    no pairwise affinity within a source), so every gap is 0.0, the stable sort leaves
        #    them in index order, and the first six positions win: `shelve([100 members], {},
        #    depth=2)` gave one child everything past the sixth member -- the giant component
        #    `shelve`'s own docstring says cannot happen.
        # 2. An even split guarded by `if len({g for g, _ in gaps}) <= 1` -- i.e. only when the
        #    block is WHOLLY tied. One nonzero seam anywhere defeats it and hands the block back
        #    to (1). Measured on the live shelving under that guard: 106 of 209 sources (50.7%)
        #    shared a Shelfmark, 17 addresses held more than one, the largest held 38, and the
        #    seven top-tier branches held 1, 9, 16, 19, 43, 55 and 66 members.
        #
        # Extending the even split to any TIED RUN (the order's own suggested remedy) was tried
        # and MEASURED WORSE, which is why it is not what is here: spreading cuts evenly across
        # the positions of a tied run spreads them over where the ties are, not over the block,
        # so on the live graph all six cuts landed inside one dense band of zero seams and the
        # top branches came out 7, 8, 9, 9, 10, 16 and 150. A tie-run split balances the tie; the
        # claim is about the BLOCK.
        #
        # So: take the even-split boundary for each of the k-1 cuts, and around each one search a
        # window of half a step either side for the weakest seam in it, nearest boundary winning
        # a tie. Balance is then bounded by construction -- every chunk lands within half a step
        # of even, so no branch can swell into a giant component whatever the weights say -- and
        # the material still chooses the exact joint, which is what reading the seams was for.
        # A window is also what makes the affinity signal meaningful rather than global: two
        # sources with no measured affinity at opposite ends of the order are not evidence that
        # the shelf should be cut at both.
        cuts = []
        step = len(block) / k
        for boundary in _even_cuts(len(block), k):
            lo = max(0, int(round(boundary - step / 2)))
            hi = min(len(gaps) - 1, int(round(boundary + step / 2)))
            window = [g for g in gaps[lo:hi + 1] if g[1] not in cuts]
            if not window:
                continue
            # (seam strength, distance from the even boundary) -- the weakest seam in the window,
            # and of equally weak ones the one that divides the block most evenly.
            cuts.append(min(window, key=lambda t: (t[0], abs(t[1] - boundary)))[1])
        return sorted(set(cuts))

    def split(block, level):
        if level >= depth or not block:
            return
        cuts = seams(block)
        bounds = [0] + [c + 1 for c in cuts] + [len(block)]
        child = 0
        for lo, hi in itertools.pairwise(bounds):
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
    # zip(TIERS, c) is deliberately unequal-length whenever depth < len(TIERS) (SOURCE_TIERS and
    # WORLD_TIERS are prefixes/suffixes of TIERS by construction) -- it labels the first `depth`
    # coordinates with the first `depth` tier names, so strict=True would raise on every call
    # that does not use the full 5-tier default.
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
SOURCE_CAPACITY = SPAN ** len(SOURCE_TIERS)                 # 343 -- what sources actually occupy

# {source -> number of its worlds that the last build() could not shelve}. Populated by build();
# empty when every world-bearing source reached the tree. See the note inside build().
UNSHELVED = {}


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

    # TWO POPULATIONS, COUNTED SEPARATELY, AND THE DIFFERENCE SAID OUT LOUD. `coords` covers
    # only the sources that survive weave's resonance graph, while `by_source` is built from
    # worldseed over EVERY record in `pipeline.records()`. The two disagree today: the graph
    # holds 209 sources and `records()` holds 210 -- 'Bone (Jeff Smith)', 'aurora_mods (Way of
    # the Inkmaster)' and 'the Sex Worker background' are in the corpus and not in the graph
    # (measured this run). None of the three currently yields a world past worldseed's filter,
    # so nothing is being lost right now, and `continue` said nothing either way: the next
    # rules-heavy source that filters out of the graph AND has eligible worlds would have its
    # entire world set vanish from every tier count and every shelfmark with no line printed
    # anywhere. A drop with no count is indistinguishable from a source that had nothing.
    UNSHELVED.clear()
    worlds = {}
    for src, ws in by_source.items():
        base = coords.get(src)
        if base is None:
            UNSHELVED[src] = len(ws)
            continue
        names = [x["designation"] for x in ws]
        inner = shelve(names, {}, depth=len(WORLD_TIERS))
        for d in names:
            worlds[d] = dict(base)
            worlds[d]["multiverse"] = inner[d]["hyperverse"]
            worlds[d]["universe"] = inner[d]["xenoverse"]
    if UNSHELVED:
        print("[sevenfold] UNSHELVED: %d source(s) produced worlds but are absent from the "
              "resonance graph, so %d world(s) appear in no tier count and have no shelfmark: %s"
              % (len(UNSHELVED), sum(UNSHELVED.values()),
                 ", ".join("%s (%d)" % (s, n) for s, n in sorted(UNSHELVED.items()))),
              file=sys.stderr, flush=True)
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
    print(f"capacity        : {CAPACITY:,} universe slots ({SPAN}^{len(TIERS)}) — the full tree, "
          f"reached only through a source's own worlds")
    print(f"source capacity : {SOURCE_CAPACITY:,} slots ({SPAN}^{len(SOURCE_TIERS)}) — sources "
          f"occupy only the top {len(SOURCE_TIERS)} tiers, per SOURCE_TIERS above")
    print(f"occupancy       : {len(coords)/SOURCE_CAPACITY:.2%}  — sparse by design")

    print("\nbalance at each tier (the property every discovered scheme failed):")
    print(f"worlds shelved  : {len(worlds):,}")
    # The count that used to be missing. A zero here is a statement; nothing at all was not.
    print(f"worlds UNSHELVED: {sum(UNSHELVED.values()):,}"
          + (f"  ({len(UNSHELVED)} source(s) absent from the resonance graph: "
             + ", ".join(sorted(UNSHELVED)) + ")" if UNSHELVED else "  (every world-bearing "
             "source reached the tree)"))
    print()
    # MEMBERS PER BRANCH IS THE COLUMN THE BALANCE CLAIM IS ABOUT (order 2a48315d26e6). The table
    # printed CHILDREN PER PARENT only -- a quantity `seams()` clamps to <= SPAN by construction,
    # which is why the comment below already says "OVER SPAN" is a display that cannot print. A
    # table of guaranteed numbers cannot report an imbalance: while one address held 38 of the
    # 209 sources and the top branches ran 1 to 66, every row of this table read 1-7 OK. What
    # swells is the POPULATION of a branch, so that is now measured too, with the even share
    # beside it to read the spread against.
    print(f"{'tier':<12}{'children per parent':<22}{'members per branch':<26}{'occupancy'}")
    for i, t in enumerate(TIERS):
        pool = coords if t in SOURCE_TIERS else worlds
        parents = collections.defaultdict(set)
        members = collections.Counter()
        for v in pool.values():
            if t not in v:
                continue
            key = tuple(v[x] for x in TIERS[:i] if x in v)
            parents[key].add(v[t])
            members[key + (v[t],)] += 1
        if not parents:
            continue
        counts = sorted(len(x) for x in parents.values())
        lo, hi = counts[0], counts[-1]
        # m30, same shape as custodes' covers_every_reading: `seams()` already clamps every child
        # count to SPAN, so "OVER SPAN" cannot print for any input. This displays a GUARANTEE, not
        # a discovery. Kept because it states the bound where a reader looks for it; it becomes a
        # real check only if seams() ever stops clamping.
        ok = "OK" if hi <= SPAN else "OVER SPAN"
        msizes = sorted(members.values())
        even = sum(msizes) / len(msizes)
        mcol = f"{msizes[0]}-{msizes[-1]} (even {even:.1f})"
        print(f"{t:<12}{f'{lo}-{hi}':<22}{mcol:<26}{len(parents)} parents   {ok}")

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
        if not landed:
            # AND THE EXIT CODE HAS TO CARRY IT TOO (order 3e65dbed45a6). The verdict was gated
            # into the PRINT and then thrown away at `return 0`, so an automated caller could not
            # tell a denied write from a successful one -- and whatever reads SEVENFOLD.json goes
            # on reading the previous run's shelving, which is the identical situation
            # `zfighters.py:492-497` answers with a 1. A line only a person reads is not a
            # verdict; it is a hope that a person was reading.
            silence.note("sevenfold.py:main-write-denied")
            print(f"\nWRITE DENIED: {p} did not land; the shelving above was NOT written and "
                  f"the file on disk is the previous run's. Rerun to retry.")
            return 1
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
