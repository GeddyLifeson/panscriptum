#!/usr/bin/env python3
"""
BURGS — the settlement tier, and the bottom of the seed hierarchy.

WHERE THIS SITS
---------------
The stack now runs the whole way down, each level seeded from the one above and nothing stored:

    galaxy / neighbourhood   a hierarchical galaxy service, seeded from the address's galaxy field
    planet surface           Azgaar's Fantasy Map Generator, seeded from the citation card
    BURG                     this module -- every town, village and hamlet on that surface

Azgaar's generator already anticipates the hand-off. Its documented URL parameters include `burg`
(focus on a settlement, requires scale > 1) and it passes `size`, `coast`, `port` and `river` out
to Watabou's Medieval Fantasy City Generator, with size = population/1000. So the seam exists on
their side; what was missing was ours -- a rule for how many burgs a world has and how big each
one is.

POPULATIONS ARE DERIVED, NOT INVENTED
-------------------------------------
The obvious approach is to pick a number of settlements and roll sizes. There is no need, because
settlement sizes are one of the most robust empirical regularities there is: the RANK-SIZE RULE
(Auerbach 1913, Zipf 1949). Rank a region's settlements by population and the k-th holds roughly

    P_k = P_1 / k^q

with q near 1 across an enormous range of real regions and historical periods. It is the same
heavy-tail family the Assay already leans on for magnitudes -- Gutenberg-Richter for earthquakes,
Richardson for wars -- so this is not a new assumption, it is the settlement-scale instance of one
the library already carries.

That fixes the whole distribution from two numbers: the largest city, and how many burgs there
are. Both follow from the world's own profile rather than from a die roll.

WHAT THIS MODULE IS, AND IS NOT
------------------------------
It is NOT the authority on any particular world's burgs. Azgaar's generator is: give it the seed
and it produces the settlements, their populations, their coast and port and river flags, and the
link that opens each one in Watabou's city or village generator. That integration already exists
on their side and this module does not duplicate it -- `burg_link` routes through it.

What this module IS is an ESTIMATOR, for the question Azgaar cannot answer cheaply: what does the
settlement pattern look like across a thousand worlds nobody has rendered? Running the map
generator 1,521 times to count hamlets is not a plan. So the rank-size rule stands in, and the
figures below are estimates of what Azgaar WOULD produce rather than claims about what it did.

That distinction is load-bearing and belongs in any volume that quotes these numbers. It would
also be worth calibrating: render a sample of worlds, count the burgs Azgaar actually generates,
and check the exponent against q = 1. Until that is done these are modelled, not measured.
"""
import argparse
import hashlib
import json
import math
import os
import sys
import urllib.parse

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Zipf exponent. q = 1 is the classical rank-size rule and the neutral choice; real regions
# scatter around it, and exposing it means a Custos can argue with it rather than discover it
# buried. Same treatment as the Pareto tail index in the extreme-value work.
ZIPF_Q = 1.0

# Settlement classes by population. The town/city boundary is where Watabou's two generators
# genuinely part company: below it a settlement is a cluster of dwellings, above it it has streets.
CLASSES = [
    ("hamlet",  0,     100,   "village"),
    ("village", 100,   1000,  "village"),
    ("town",    1000,  10000, "city"),
    ("city",    10000, 10 ** 9, "city"),
]

# Which of Watabou's two generators a settlement belongs in. Recorded for reference only --
# Azgaar performs the hand-off itself and is the authority on which one opens.
GENERATORS = {"city": "Watabou city generator", "village": "Watabou village generator"}


def _stream(seed, salt=""):
    return int(hashlib.sha256(f"{seed}:{salt}".encode("utf-8")).hexdigest()[:12], 16)


# The smallest thing the record still calls a burg. Below this it is a farmstead and the
# catalogue has nothing to say about it.
HAMLET_FLOOR = 40


def burg_count(world_seed, era, condition, p1=None):
    """How many named settlements a world carries.

    DERIVED FROM THE RANK-SIZE RULE ITSELF, not chosen alongside it. A first version picked a
    count near forty and produced a world of 39% cities and no hamlets at all -- an inverted
    pyramid, because the ranking simply stopped before it reached the small settlements. Real
    regions are overwhelmingly hamlets and villages with a scattering of cities on top.

    The rule already knows where to stop: it runs until a settlement falls below the floor at
    which it stops being a burg. So

        n = P_1 / P_min

    and the shape of the pyramid is a consequence of the law rather than a second parameter that
    could disagree with it.
    """
    if p1 is None:
        p1 = largest_city(world_seed, era, condition)
    n = int((p1 / HAMLET_FLOOR) ** (1.0 / ZIPF_Q))
    # A ruined world keeps its ruins on the map but loses the living tail.
    factor = {"ruined": 0.3, "wartorn": 0.8, "settled": 1.0, "thriving": 1.15}.get(condition, 1.0)
    return max(3, int(n * factor))


def largest_city(world_seed, era, condition):
    """P_1, the primate city. Everything else follows from the rank-size rule."""
    base = {"primitive": 2500, "medieval": 20000, "magical": 25000,
            "industrial": 400000, "spacefaring": 3000000}.get(era, 20000)
    factor = {"ruined": 0.15, "wartorn": 0.6, "settled": 1.0, "thriving": 1.6}.get(condition, 1.0)
    jitter = 0.6 + (_stream(world_seed, "primate") % 1000) / 1250.0    # 0.6 - 1.4
    return max(200, int(base * factor * jitter))


def classify(pop):
    for name, lo, hi, gen in CLASSES:
        if lo <= pop < hi:
            return name, gen
    return CLASSES[-1][0], CLASSES[-1][3]


def burgs_for(world_seed, features, limit=None):
    """The full settlement roll for one world, by the rank-size rule."""
    era = features.get("tech", "medieval")
    cond = features.get("condition", "settled")
    climate = features.get("climate", "temperate")
    landform = features.get("landform", "continents")

    p1 = largest_city(world_seed, era, cond)
    n = burg_count(world_seed, era, cond, p1)

    # Coastal likelihood follows the world's own shape -- an archipelago is nearly all coast.
    coastal_bias = {"archipelago": 0.92, "isles": 0.85, "shattered": 0.5,
                    "continents": 0.35, "pangaea": 0.25, "highland": 0.2}.get(landform, 0.4)
    if climate in ("oceanic",):
        coastal_bias = min(0.95, coastal_bias + 0.2)
    if climate in ("arid", "frozen"):
        coastal_bias = max(0.05, coastal_bias - 0.15)

    out = []
    for k in range(1, (limit or n) + 1):
        pop = max(30, int(p1 / (k ** ZIPF_Q)))
        name, gen = classify(pop)
        s = _stream(world_seed, f"burg{k}")
        coast = (s % 100) / 100.0 < coastal_bias
        out.append({
            "rank": k,
            "seed": s % (2 ** 32),
            "population": pop,
            "class": name,
            "generator": gen,
            "coast": bool(coast),
            "port": bool(coast and (s >> 8) % 100 < 55),
            "river": bool((s >> 16) % 100 < (30 if climate in ("arid", "frozen") else 62)),
        })
    return out


def burg_link(world_map_seed, rank, scale=8):
    """The route to a settlement's own map: THROUGH Azgaar, not around it.

    An earlier version of this module built Watabou city-generator URLs directly. That was a
    second mechanism for something Azgaar already does -- its generator creates each burg's
    population and its coast/port/river flags from the map seed and hands them to Watabou itself,
    with size = population/1000. Constructing our own URL would have produced a DIFFERENT city
    than Azgaar's own link for the same burg: two conflicting answers to one question, which is
    the exact failure X.10 §4 prices as beta.

    So the link goes through the documented `burg` parameter and lets Azgaar make the hand-off.
    """
    return (f"https://azgaar.github.io/Fantasy-Map-Generator/"
            f"?seed={world_map_seed}&options=default&scale={scale}&burg={rank}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    import worldseed as WS
    import address_space as AS

    worlds = WS.build_all()          # every world; Hard Rule 0
    print("=" * 100)
    print("BURGS — every settlement on every world, by the rank-size rule")
    print("=" * 100)

    total = 0
    per_world = {}
    for w in worlds:
        seed = AS.map_seed(w["seed"])
        bs = burgs_for(seed, w["features"])
        per_world[w["designation"]] = bs
        total += len(bs)
    print(f"\nworlds        : {len(worlds):,}")
    print(f"burgs         : {total:,}   ({total/max(1,len(worlds)):.0f} per world)")
    print(f"storage       : 0 bytes — every one is derived from its world's seed")

    import collections
    cls = collections.Counter(b["class"] for bs in per_world.values() for b in bs)
    print(f"\nsettlement classes (the rank-size rule doing the work):")
    for k, _, _, _ in CLASSES:
        print(f"   {k:<10}{cls.get(k, 0):>7,}  {cls.get(k,0)/max(1,total):6.1%}")

    w0 = worlds[0]
    print("\n" + "-" * 100)
    print(f"SAMPLE — {w0['designation'][:60]}")
    print(f"   {w0['features']}")
    print("-" * 100)
    print(f"{'rank':>5}{'population':>12}{'class':>10}   {'flags':<22}generator")
    for b in per_world[w0["designation"]][:args.limit]:
        flags = ",".join(f for f in ("coast", "port", "river") if b[f]) or "inland"
        print(f"{b['rank']:>5}{b['population']:>12,}{b['class']:>10}   {flags:<22}{b['generator']}")
    print()
    print("   largest, via Azgaar's own burg link (it makes the Watabou hand-off itself):")
    print(f"   {burg_link(AS.map_seed(w0['seed']), 1)}")

    if args.write:
        p = os.path.join(HERE, "data", "BURGS_SAMPLE.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(per_world, f, indent=2,          # every world; Hard Rule 0
                      ensure_ascii=False)
        print(f"\nwrote {p} (sample of 50 worlds; the rest regenerate on demand)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
