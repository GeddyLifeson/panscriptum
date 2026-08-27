#!/usr/bin/env python3
"""
INFORMATION PROPAGATION — how long it takes the omniverse to learn a thing.

Owner's problem, 2026-08-20: if something is added to the library later, how did the omniverse
not already know about it? And how can a new world slot into the existing organisation instead
of forcing a new arm "from shoulder to nail"?

The charter already supplies the mechanism and is missing only the metric.

  THE MECHANISM (Charter, Part Four -- the Chain of Record):
    "History arrives old: full ascension takes years to centuries, the Canon of the Now runs
     perpetually behind." An event is logged by a scribe with a provisional code and ascends
     rung by rung -- town, world, system, cluster -- gathering a countersign pedigree, until it
     is accessioned at the apex. The ascension mark says how far it got: E-0902-VEILS [^17] is
     settled omniversal history; an event at [^9] is "stuck at a cluster archive, still true
     locally but not yet omniversal history."

  THE MISSING METRIC (this module):
    How FAR is one shelf from another? The charter never says, so "Black Ops has not heard of
    Shrek" has no principled length. This computes it from evidence already in hand: the
    shared-stage graph. Two sources that co-attest entities share furniture and therefore share
    couriers; two sources sharing nothing are far apart, and the graph distance between them is
    the number of intermediaries any news must cross.

WHY THIS IS THE HONEST ANSWER RATHER THAN A DODGE
--------------------------------------------------
"Nobody had heard of it yet" is an excuse when it is asserted and a finding when it is measured.
Under this module the claim becomes falsifiable: a new source's distance to every existing shelf
is computed, its expected ascension height follows, and if the number says Black Ops SHOULD have
heard of a thing, the entry must explain why it did not. That is the Contradictions register
doing its job instead of a hand-wave doing it.

It also matches the charter's own physics. The Registry Communion propagates along the Roads
(Age IV); the Roads follow the Betweens; and W.1 holds the Betweens are one sea at different
depths. Distance in the co-attestation graph is a proxy for distance along that sea.
"""
import argparse
import collections
import heapq
import json
import math
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH = os.path.join(HERE, "data/SHARED_STAGE_GRAPH.json")

# Ascension rungs, per the Ladder. An event's mark [^n] is the rung it has been ratified to.
LADDER_HEIGHT = 17

# Declared conventions (Axiom M3), all FICTIONAL and all reversible.
#
# BASE_YEARS_PER_HOP: how long news takes to cross one intermediary shelf. Anchored to the
# charter's own timings -- the Registry Communion spread "town by town, world by world" across
# the stitched centuries (400-900 AS), i.e. roughly five centuries to cover the charted Roads.
# CORRECTED 2026-08-20: the first draft counted HOPS, which made everything 2-3 apart and
# flattened exactly the structure this module exists to expose. Every shelf reaches every other
# in <=3 hops because they all attest Earth -- but the WEIGHT of those links varies by 200x.
# Distance is now the summed inverse of shared evidence, so a tenuous link is long even when it
# is a single hop.
#
# Anchored so that distance 1.0 -- the far end of the measured range, Left 4 Dead to Dragon Ball
# Z -- is a millennium of lateral travel. Same-universe pairs (Alien/Predator at 0.006) then
# come out at ~6 years, which is the right order for "news travels within a universe".
YEARS_PER_UNIT_DISTANCE = 1000.0
# Ascension is slower the higher it climbs: a town scribe countersigns in a season, a cluster
# archive in a generation. Cost grows with rung.
RUNG_COST_EXPONENT = 1.35


def load_graph():
    with open(GRAPH, encoding="utf-8") as f:
        g = json.load(f)
    adj = collections.defaultdict(dict)
    for p in g["pairs"]:
        # Distance is INVERSE to shared evidence: heavily co-attesting shelves are near.
        d = 1.0 / max(p["weight"], 1e-6)
        a, b = p["a"], p["b"]
        if b not in adj[a] or d < adj[a][b]:
            adj[a][b] = d
            adj[b][a] = d
    return adj


def shortest(adj, src, dst):
    """Dijkstra. Returns (distance, path) or (inf, []) if disconnected."""
    if src not in adj or dst not in adj:
        return math.inf, []
    dist = {src: 0.0}
    prev = {}
    pq = [(0.0, src)]
    seen = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in seen:
            continue
        seen.add(u)
        if u == dst:
            break
        for v, w in adj[u].items():
            nd = d + w
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    if dst not in dist:
        return math.inf, []
    path, cur = [dst], dst
    while cur != src:
        cur = prev[cur]
        path.append(cur)
    return dist[dst], list(reversed(path))


def hops(path):
    return max(0, len(path) - 1)


def ascension_years(to_rung=LADDER_HEIGHT):
    """Years for an event to climb ITS OWN Chain of Record to a given rung.

    Purely vertical, and deliberately independent of distance: a town scribe logging a deed in
    his own town does not wait on couriers from another shelf. The charter's accession law is
    local-first -- "a scribe witnesses a deed and logs it with a provisional local code" -- and
    only then does it ascend.
    """
    return round(float(to_rung) ** RUNG_COST_EXPONENT - 1.0, 1)


def arrival_years(distance):
    """Years before a shelf at this distance hears of the event AT ALL."""
    return round(distance * YEARS_PER_UNIT_DISTANCE, 1)


def observed_mark(distance, years_since):
    """The ascension mark a DISTANT shelf should currently see. The field an entry must print
    when it claims a neighbour has not heard.

    CORRECTED 2026-08-20. The first version summed lateral and vertical cost into one number,
    which made even rung 1 unreachable for any distant shelf -- so every pair read [^0] and the
    model said nothing. That was wrong in kind: it treated a far-away observer as if it slowed
    down the event's OWN ratification. It does not. Two independent clocks:

        the event ascends its own chain     -> ascension_years(rung), no distance
        a distant shelf hears, delayed      -> arrival_years(distance)

    So a distant observer at time t sees the event as it stood at time (t - arrival). Before
    arrival it sees nothing, which is the honest [^0] and the whole point: Left 4 Dead has not
    heard of Dragon Ball Z's tournaments because the news is still in transit, not because
    nobody countersigned it. THE HONEST [^0] COMES SOLELY FROM THE `lag < 0` GUARD BELOW --
    once lag is non-negative, `ascension_years(1) == 0.0` (order ad730acf0b18), so the loop's
    first iteration always matches and always returns; the trailing `return 0` after the loop
    is unreached and is not a second [^0] path.
    """
    lag = years_since - arrival_years(distance)
    if lag < 0:
        return 0
    for rung in range(LADDER_HEIGHT, 0, -1):
        if lag >= ascension_years(rung):
            return rung
    return 0  # unreachable: see the docstring note above


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", default=None)
    ap.add_argument("--to", dest="dst", default=None)
    ap.add_argument("--years", type=float, default=300.0,
                    help="years since the event, for the ascension-mark calculation")
    args = ap.parse_args()

    adj = load_graph()
    print(f"shelves in the graph : {len(adj)}")
    print(f"edges                : {sum(len(v) for v in adj.values()) // 2}")
    print()

    if args.src and args.dst:
        d, path = shortest(adj, args.src, args.dst)
        if not path:
            print(f"{args.src} -> {args.dst}: DISCONNECTED (no shared furniture at any remove)")
            return
        print(f"{args.src}  ->  {args.dst}")
        print(f"  hops     : {hops(path)}")
        print(f"  distance : {d:.4f}")
        print(f"  path     : {' -> '.join(path)}")
        print(f"  arrival  : {arrival_years(d):,.0f} years before it is heard of at all")
        print(f"  own [^17]: {ascension_years():,.0f} years to ratify at home")
        print(f"  after {args.years:,.0f} yr, this shelf sees [^{observed_mark(d, args.years)}]")
        return

    # Default: the diameter survey -- who is far from whom
    print("SAMPLE DISTANCES — arrival delay and what each shelf currently sees:")
    probes = [
        ("all Black Ops", "all Pixar films"),
        ("all Black Ops", "Dragon Ball Z"),
        ("Dragon Ball Z", "all Pixar films"),
        ("Left 4 Dead", "Dragon Ball Z"),
        ("Pantheon: Greek", "Marvel"),
        ("Minecraft", "Warhammer 40,000"),
    ]
    for a, b in probes:
        if a in adj and b in adj:
            d, p = shortest(adj, a, b)
            if p:
                marks = " ".join(f"{y}yr:[^{observed_mark(d, y)}]"
                                 for y in (100, 500, 1500))
                print(f"  d={d:6.3f}  arrives+{arrival_years(d):>6,.0f}yr  "
                      f"{a[:19]:21s} -> {b[:19]:21s}  {marks}")
            else:
                print(f"   -- DISCONNECTED  {a} -> {b}")
        else:
            missing = a if a not in adj else b
            print(f"   ?? not in graph: {missing}")


if __name__ == "__main__":
    main()
