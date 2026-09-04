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
settlement pattern look like across thousands of worlds nobody has rendered? Running the map
generator once per world -- and the roll carries ~6,000 of them (measured 6,006 on 2026-08-29,
and it grows) -- to count hamlets is not a plan. So the rank-size rule stands in, and the figures
below are estimates of what Azgaar WOULD produce rather than claims about what it did.

Those two figures used to read "a thousand worlds" and "1,521 times", both stale by about four
times, in a file whose own body already said 5,986 at :301 -- so the header and the body of one
file disagreed by a factor of four and the header was the one stated in the present tense as the
reason this module exists. It is phrased not to need maintaining, because the count moved by one
between the order being filed and being worked. The 5,986 at :301 is correct as written: it is a
DATED measurement inside a historical note about order 65ae84ee4bd7, not a present-tense claim.
(Order d5a06f9c6dee.)

That distinction is load-bearing and belongs in any volume that quotes these numbers. It would
also be worth calibrating: render a sample of worlds, count the burgs Azgaar actually generates,
and check the exponent against q = 1. Until that is done these are modelled, not measured.
"""
import argparse
import collections
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import silence          # noqa: E402  -- after the sys.path line above, as every module here does

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

# Which of Watabou's two generators a settlement belongs in, spelled out for a human reader.
# The burg RECORD carries the terse key ("city"/"village") and not these strings, deliberately:
# that key is CLASSES' own fourth column and verify_math §17 pins it --
#     check("small settlements route to the village generator", BG.classify(60)[1], "village")
# -- so widening what `classify()` returns would break a published check for a cosmetic gain.
# This dict is therefore the DISPLAY spelling, used where a person reads the output rather than
# a program; six audit sweeps in a row read it as dead code because nothing consumed it, so it
# is now wired into the sample table below, which is the only place the long form belongs.
# Azgaar performs the hand-off itself and remains the authority on which generator opens.
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


def rank_population(p1, k):
    """The modelled population of the rank-k settlement. ONE expression, three callers.

    `burgs_for` materialises a roll, `class_histogram` counts one without materialising it, and
    `_rank_at_or_above` inverts it. Three copies of the rank-size expression could disagree, and
    two conflicting answers to one question is the fault X.10 §4 prices as beta -- so all three
    read this.
    """
    return max(HAMLET_FLOOR, int(p1 / (k ** ZIPF_Q)))


def coastal_bias(climate, landform):
    """How likely any one settlement is to sit on water -- an archipelago is nearly all coast.

    Hoisted out of `burgs_for` UNCHANGED so that the parameter dump can report the same number
    the roll was actually built from, rather than a second copy of the rule that could drift
    from it. Deliberately NOT rounded anywhere: the coast test compares a hundredth against this
    float directly, and 0.55 against 0.5500000000000000444 decides differently for one burg in a
    hundred.
    """
    bias = {"archipelago": 0.92, "isles": 0.85, "shattered": 0.5,
            "continents": 0.35, "pangaea": 0.25, "highland": 0.2}.get(landform, 0.4)
    if climate in ("oceanic",):
        bias = min(0.95, bias + 0.2)
    if climate in ("arid", "frozen"):
        bias = max(0.05, bias - 0.15)
    return bias


def world_parameters(world_seed, features):
    """Everything one world's ENTIRE settlement roll is derived from. -> dict.

    This is what "storage: 0 bytes" means concretely. Given these numbers and the seed,
    `burgs_for` reproduces every burg, its population, its class, its coast/port/river flags and
    its Azgaar link -- so the parameters ARE the roll, in the only form that fits on a disk.
    `main()` accumulates and dumps these instead of 91 million materialised burg dicts (order
    47e4e1ace8f1).
    """
    era = features.get("tech", "medieval")
    cond = features.get("condition", "settled")
    climate = features.get("climate", "temperate")
    landform = features.get("landform", "continents")
    p1 = largest_city(world_seed, era, cond)
    return {"world_seed": world_seed, "era": era, "condition": cond, "climate": climate,
            "landform": landform, "p1": p1,
            "burgs": burg_count(world_seed, era, cond, p1),
            "coastal_bias": coastal_bias(climate, landform),
            "zipf_q": ZIPF_Q, "hamlet_floor": HAMLET_FLOOR}


def _rank_at_or_above(p1, n, lo):
    """How many of the first `n` ranks still hold at least `lo` people.

    Closed form first -- populations fall as p1/k^q, so the last rank at or above `lo` is
    (p1/lo)^(1/q) -- then CORRECTED against `rank_population` itself, because the closed form is
    float arithmetic and the roll is `int()` of a float division, and the two can differ by one
    at a boundary. The correction is at most a step or two, so this stays O(1) in practice while
    being exact by construction: whatever the closed form says, the answer is checked with the
    same expression `burgs_for` uses to build the burg.
    """
    if n <= 0:
        return 0
    if lo <= HAMLET_FLOOR:
        return n            # every population is floored at HAMLET_FLOOR, so all n qualify
    k = min(n, int((p1 / lo) ** (1.0 / ZIPF_Q)))
    while k < n and rank_population(p1, k + 1) >= lo:
        k += 1
    while k > 0 and rank_population(p1, k) < lo:
        k -= 1
    return k


def class_histogram(p1, n):
    """{class name: how many of this world's `n` burgs are that class}, WITHOUT building them.

    A world's roll is monotone in rank, so each class occupies a contiguous block of ranks and
    counting it is a division rather than a loop over settlements. That is the difference
    between reading the whole omniverse's settlement pattern in a second and materialising
    91 million dicts to count them (order 47e4e1ace8f1). The boundaries come from CLASSES, so
    there is no second table to keep in step.
    """
    counts = {name: 0 for name, _lo, _hi, _gen in CLASSES}
    above = 0                               # ranks already claimed by a larger class
    for name, lo, _hi, _gen in reversed(CLASSES):
        within = _rank_at_or_above(p1, n, lo)
        counts[name] = max(0, within - above)
        above = max(above, within)
    return counts


def burgs_for(world_seed, features, limit=None):
    """The full settlement roll for one world, by the rank-size rule."""
    prm = world_parameters(world_seed, features)
    climate, p1, n, bias = prm["climate"], prm["p1"], prm["burgs"], prm["coastal_bias"]

    out = []
    # A LIMIT MAY ONLY EVER NARROW (order 1bc825e806a9, sweep39-batch16). This was
    # `range(1, (limit or n) + 1)`, which was wrong in two independent directions:
    #
    #   * `limit=0` was FALSY, so it fell through to `n` and returned the whole roll. "Give me
    #     none" answered with "here is everything" -- the same falsy-zero slip as
    #     `binding_health`'s `if limit:`. Measured: `limit=0` returned 483 rows, now returns 0.
    #   * `limit` LARGER than `n` ran the loop PAST the number of settlements the rank-size rule
    #     says this world has, FABRICATING them: `rank_population` keeps returning
    #     HAMLET_FLOOR-floored values for every rank beyond the end, so the extra rows are
    #     indistinguishable from real ones. `n` for a medieval/settled world falls between
    #     roughly 300 and 700, so `--limit 1000` was enough to invent settlements. That is Hard
    #     Rule 0's shape running the other way -- not a smaller universe, an INVENTED one -- and
    #     it is worse than a truncation, because a reader can at least suspect a cut.
    #
    # `min(int(limit), n)` makes the flag a narrowing view of a world that already exists, and
    # `max(0, ...)` keeps a negative from wrapping the range.
    stop = n if limit is None else max(0, min(int(limit), n))
    for k in range(1, stop + 1):
        pop = rank_population(p1, k)
        name, gen = classify(pop)
        s = _stream(world_seed, f"burg{k}")
        coast = (s % 100) / 100.0 < bias      # the VALUE from world_parameters, not the function
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

    # COUNTERS AND PARAMETERS, NOT ROSTERS (order 47e4e1ace8f1). This loop used to call
    # `burgs_for` for every world and hold the result: 91,560,055 burg dicts on the current
    # roll, measured at ~2.15 s and 45.6 MB of heap per 130,603-burg world, so ~25 minutes and
    # ~32 GB before `--write` was even consulted -- and the module simply could not run on this
    # machine. Nothing downstream reads a burg roster (navtree.py:56 takes the scalar
    # `burg_count` and nothing else), and the roll is derivable from its world's seed by
    # definition, which is what the "storage: 0 bytes" line below has always claimed. So the
    # pass accumulates the per-world PARAMETERS and a class histogram computed from them, and
    # the same figures come out in 0.02 s with no roster anywhere.
    #
    # AND THE KEY IS A LIST, BECAUSE `designation` IS NOT UNIQUE (order 65ae84ee4bd7).
    # `per_world[w["designation"]] = ...` silently overwrote: 5,986 worlds carry 5,939 distinct
    # designations, so 47 worlds were dropped, and 26 of the 44 colliding designations name
    # worlds with genuinely DIFFERENT features ('Adventure Time::Ice Kingdom' is continents and
    # highland; 'Adventurers League::Phlan' appears three times). Keying on the seed instead
    # would not have helped -- the seed is derived from the designation, so the duplicates share
    # that too. The count printed on the write line was taken from the post-loss dict, so the
    # completeness claim could not contradict itself however many worlds went missing; it now
    # counts worlds, not keys. Nothing is lost and nothing is merged: a designation holds every
    # world that bears it.
    total = 0
    per_world = {}
    cls = collections.Counter()
    for w in worlds:
        prm = world_parameters(AS.map_seed(w["seed"]), w["features"])
        per_world.setdefault(w["designation"], []).append(prm)
        total += prm["burgs"]
        cls.update(class_histogram(prm["p1"], prm["burgs"]))
    print(f"\nworlds        : {len(worlds):,}   ({len(per_world):,} distinct designations; "
          f"{len(worlds) - len(per_world):,} share one with another world)")
    print(f"burgs         : {total:,}   ({total/max(1,len(worlds)):.0f} per world)")
    print("storage       : 0 bytes — every one is derived from its world's seed")

    # The numerator and the denominator now come from the SAME pass. They did not: the histogram
    # counted the burgs of the worlds that survived the dict while `total` counted the burgs of
    # every world built, so the printed percentages could not sum to 100%.
    print("\nsettlement classes (the rank-size rule doing the work):")
    for k, _, _, _ in CLASSES:
        print(f"   {k:<10}{cls.get(k, 0):>7,}  {cls.get(k,0)/max(1,total):6.1%}")

    if not worlds:
        print("\n  no worlds encoded -- nothing to sample")
    else:
        w0 = worlds[0]
        print("\n" + "-" * 100)
        # NOT `[:60]`. The designation is the world's IDENTITY -- and not even a unique one, see
        # the collision note at :300 -- so cutting it is cutting the one field that says WHICH
        # world the table below describes, on a header line where nothing needs aligning.
        # `suppressions.main()` made the same ruling about its own path column: "A column that
        # stretches is a worse-looking table and a truthful one." (order 0a87f4dcd5a7)
        print(f"SAMPLE — {w0['designation']}")
        print(f"   {w0['features']}")
        print("-" * 100)
        print(f"{'rank':>5}{'population':>12}{'class':>10}   {'flags':<22}generator")
        # MATERIALISED HERE AND NOWHERE ELSE -- one world, on demand, for the reader's table.
        # `--limit` is passed into `burgs_for` rather than slicing a roll that was already built,
        # which is the same rows off the same expression without the roll.
        _rows = burgs_for(AS.map_seed(w0["seed"]), w0["features"], limit=args.limit)
        for b in _rows:
            flags = ",".join(f for f in ("coast", "port", "river") if b[f]) or "inland"
            gen = GENERATORS.get(b["generator"], b["generator"])   # long form for the reader only
            print(f"{b['rank']:>5}{b['population']:>12,}{b['class']:>10}   {flags:<22}{gen}")
        # AND THE TABLE SAYS WHAT IT IS A SAMPLE OF (order 1bc825e806a9). The world's own burg
        # count was never printed, so a reader seeing twenty rows could not tell whether that was
        # all of them or twenty of several hundred -- the Hard Rule 0 shape exactly: nothing
        # fails, the table is well-formed, and it describes a smaller world. The cut itself is
        # legitimate (this is a sample block for a human, and the full roll is what `--write`
        # lands uncapped); what was missing was the marker, in the discipline
        # `suppressions._preview` settled.
        _total = world_parameters(AS.map_seed(w0["seed"]), w0["features"])["burgs"]
        if len(_rows) < _total:
            print(f"   ... and {_total - len(_rows):,} more of this world's {_total:,} burgs "
                  f"(showing {len(_rows):,}; --limit controls this, and can only narrow)")
        else:
            print(f"   all {_total:,} of this world's burgs are shown")
        print()
        print("   largest, via Azgaar's own burg link (it makes the Watabou hand-off itself):")
        print(f"   {burg_link(AS.map_seed(w0['seed']), 1)}")

    if args.write:
        # THE MESSAGE USED TO CONTRADICT THE WRITE ABOVE IT. An earlier design truncated this
        # artifact at fifty worlds; the Hard Rule 0 fix removed the truncation from the code
        # (`worlds = WS.build_all()`, and no slicing anywhere between there and the dump) but
        # left the console line saying "sample of 50 worlds; the rest regenerate on demand".
        # Six audit sweeps running (22, 23, 26, 27, 28, 33) re-filed that line as a defect,
        # because an operator reading only the printed output would believe the file was a
        # fifty-world excerpt and might re-run for coverage it already has. The count is now
        # taken from the dict that was actually written, so the message cannot drift again.
        # The FILENAME still says SAMPLE and is left alone on purpose: renaming an on-disk
        # artifact is a curatorial call, not a maintenance one.
        #
        # THE WRITE ITSELF WAS A TRUNCATE-THEN-FILL. A bare `open(p, "w")` empties the artifact
        # before a single world is serialised, so a reader arriving in that gap sees a partial
        # or zero-byte file and a crash in the gap leaves it that way permanently. This is the
        # twelve-call-site defect `silence.write_json` was written for; route through it and the
        # file is built under a pid+thread-stamped temp name and renamed into place.
        #
        # AND THE MESSAGE IS GATED ON THE VERDICT. `write_json` returns False on a denied
        # rename (Windows, a reader holding the target) rather than raising, so printing
        # "wrote {p}" unconditionally would report an artifact that is not there -- the same
        # shape as the drifted count this branch already carries a comment about.
        #
        # AND WHAT IT WRITES IS NOW THE PARAMETERS, NOT THE ROSTERS (order 47e4e1ace8f1). The
        # dumped rolls came to ~16 GB of JSON for 91.5 million burgs, printed one line under
        # "storage: 0 bytes — every one is derived from its world's seed". Both statements
        # cannot be true, and it is the write that was wrong: P_1, the burg count, the Zipf
        # exponent, the hamlet floor and the coastal bias are everything `burgs_for` consumes,
        # so this file now holds the derivation rather than its output, at a few MB. Every
        # burg is still recoverable, exactly, by handing a row back to `burgs_for`. No
        # downstream reader is affected -- nothing in the tree reads this artifact at all.
        p = os.path.join(HERE, "data", "BURGS_SAMPLE.json")
        n_written = sum(len(v) for v in per_world.values())
        if silence.write_json(p, per_world, indent=2,   # every world; Hard Rule 0
                              ensure_ascii=False):
            print(f"\nwrote {p} ({n_written:,} worlds under {len(per_world):,} designations "
                  f"— every one, Hard Rule 0; the SAMPLE in the filename is historical). "
                  f"Each row is the PARAMETERS its whole roll derives from, not the roll.")
        else:
            print(f"\nDID NOT WRITE {p}: the rename was refused (most likely a reader holding "
                  f"it open). Nothing was changed on disk — re-run to write it.", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
