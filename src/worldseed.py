#!/usr/bin/env python3
"""
WORLDSEED — a compact address that regenerates an inhabited world, derived from its catalogue entry.

THE PROBLEM
-----------
The catalogue is on course for roughly 5,200 inhabited worlds. Hand-authoring a map for each is
not work anybody is going to do, and storing 5,200 map files is storing gigabytes of something
that was generated deterministically in the first place.

WHY "STEER THE BITS OF THE SEED" CANNOT WORK
--------------------------------------------
The obvious idea is to store only the seed and learn which bits mean what -- nudge bit 7 for more
ocean, bit 12 for mountains. It cannot work, and the reason is not a limitation to engineer around:

    A PRNG SEED IS NOT A LATENT SPACE. It is an index.

Pseudo-random generators are specifically constructed so that seeds close together produce streams
that are statistically independent -- the avalanche property. Flipping one bit of the seed does not
perturb the world, it replaces it. Seeds 1000 and 1001 are as unrelated as 1000 and 8,675,309.
There is no gradient to follow and no dialect to learn, by design and on purpose.

WHAT DOES WORK
--------------
A generated map is not a function of the seed alone. It is

    map = f(seed, options)

and the OPTIONS are semantic in exactly the way the seed is not. Heightmap template, climate,
states, cultures, size -- each is a named parameter with a meaning, monotone in its effect, and
therefore genuinely steerable. So:

    the SEED    chooses WHICH instance      -- chaotic, uninterpretable, and that is fine
    the OPTIONS choose WHAT KIND of world   -- derived from the entry's own description

Both are packed into one short address. About twenty bytes per world; roughly 100 KB for the whole
library, against gigabytes of saved maps, and every world reproducible from its own catalogue row.

THIS REUSES WHAT THE LIBRARY ALREADY DERIVED
--------------------------------------------
The encoder does not invent a new taxonomy. It reads quantities that already exist:

    ONOMASTICON REGISTER  worlds in one continuity share a naming register (classical, guttural,
                          liquid ...), so they should share a culture set. Worlds of one universe
                          ought to look related; worlds of unrelated shelves ought not.
    CONTINUITY GROUP      seeds the shared climate band, for the same reason.
    MAGNITUDE BAND        a world whose ceiling is M5 is not a quiet one: band drives state count
                          and conflict.
    DESCRIPTION           the actual text supplies landform, climate and condition.

ON THE ADAPTER
--------------
`to_options()` emits a canonical, tool-independent struct. `to_fmg_query()` renders it for
Azgaar's Fantasy Map Generator. The canonical struct is the part with intellectual content and is
stable; the adapter is a thin mapping whose exact parameter NAMES should be checked against the
version of the generator actually in use, since they are that project's business and not ours.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.parse
import silence

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ==================================================================================================
# 1. FEATURES — read out of the entry's own description
# ==================================================================================================
LANDFORM = [
    ("archipelago", r"\b(archipelago|island chain|scattered isles|atolls?)\b"),
    ("isles",       r"\b(island|isle|isles)\b"),
    ("shattered",   r"\b(shattered|broken|sundered|fractured|floating (?:islands?|rocks?))\b"),
    ("pangaea",     r"\b(single (?:super)?continent|one landmass|pangaea|supercontinent)\b"),
    ("highland",    r"\b(mountain|peaks?|highland|alpine|crag)\w*\b"),
    ("continents",  r"\b(continent|landmass|realm|kingdom|empire|nation)\w*\b"),
]
CLIMATE = [
    ("frozen",    r"\b(frozen|ice|icy|glacial|tundra|arctic|permafrost|snowbound)\w*\b"),
    ("arid",      r"\b(desert|arid|wasteland|dune|parched|scorched|barren|dust)\w*\b"),
    ("tropical",  r"\b(jungle|tropical|rainforest|humid|swamp|monsoon)\w*\b"),
    ("oceanic",   r"\b(ocean|sea|maritime|coastal|tidal|water[- ]?world)\w*\b"),
    ("volcanic",  r"\b(volcan|lava|magma|ash|cinder|molten)\w*\b"),
    ("temperate", r"\b(forest|plain|meadow|grassland|temperate|river|valley)\w*\b"),
]
CONDITION = [
    ("ruined",   r"\b(ruin|ruined|derelict|abandoned|dead|post[- ]?apocalyp|wreck|desolate)\w*\b"),
    ("wartorn",  r"\b(war|battle|siege|invasion|conflict|occupied|embattled|front)\w*\b"),
    ("thriving", r"\b(prosper|thriv|flourish|bustling|capital|jewel|golden)\w*\b"),
]
TECH = [
    ("spacefaring", r"\b(starship|space|orbital|colon(?:y|ised|ized)|interstellar|warp|fleet)\w*\b"),
    ("industrial",  r"\b(factor(?:y|ies)|industrial|steam|machine|foundr|railway|engine)\w*\b"),
    ("magical",     r"\b(magic|arcane|spell|wizard|sorcer|enchant|rune)\w*\b"),
    ("medieval",    r"\b(castle|knight|kingdom|feudal|village|keep|lord)\w*\b"),
]


def _first(table, text, seed, axis):
    """Attested value if the text says so; otherwise a SEEDED one, never a default.

    Measured on the catalogue: 86% of worlds defaulted on landform, 87% on tech, and 200 of 1,068
    worlds ended up sharing one identical option vector. The cause is not the matcher -- it is that
    the median description is 167 characters, and a one-line gloss does not state a climate.

    Defaulting is the wrong answer to silence, twice over. It makes 900 worlds look alike, and it
    quietly asserts "temperate" as though the source had said so. Falling back to the seed instead
    gives variety that is reproducible, and the choice is TAGGED so a reader can tell an attested
    feature from a filled one -- the same distinction the Assay draws between a measured axis and
    an unestimable one.
    """
    for name, pat in table:
        if re.search(pat, text, re.I):
            return name, "attested"
    pick = int(hashlib.sha256(f"{seed}:{axis}".encode()).hexdigest()[:6], 16) % len(table)
    return table[pick][0], "seeded"


def features(name, description, seed=0):
    t = f"{name or ''} {description or ''}"
    out, prov = {}, {}
    for axis, table in (("landform", LANDFORM), ("climate", CLIMATE),
                        ("condition", CONDITION), ("tech", TECH)):
        v, p = _first(table, t, seed, axis)
        out[axis] = v
        prov[axis] = p
    out["_provenance"] = prov
    out["_attested_axes"] = sum(1 for p in prov.values() if p == "attested")
    return out


# ==================================================================================================
# 2. THE CANONICAL OPTION STRUCT
# ==================================================================================================
TEMPLATE = {
    "archipelago": "archipelago", "isles": "lowIsland", "shattered": "shattered",
    "pangaea": "pangea", "highland": "volcano", "continents": "continents",
}
# (temperature at the equator in C, temperature at the pole, precipitation 0-10)
CLIMATE_BAND = {
    "frozen": (8, -40, 3), "arid": (34, -12, 1), "tropical": (30, -6, 9),
    "oceanic": (24, -18, 7), "volcanic": (32, -20, 2), "temperate": (25, -25, 5),
}
CULTURE_SET = {
    "classical": "antique", "guttural": "darkfantasy", "liquid": "highfantasy",
    "sibilant": "highfantasy", "compact": "european", "long": "oriental",
}


def seed_for(designation):
    """32-bit seed. Deterministic, so a world regenerates identically for anyone who has its row."""
    return int(hashlib.sha256(designation.encode("utf-8")).hexdigest()[:8], 16)


def to_options(designation, name, description, band="unassayed", register="classical",
               continuity=0):
    sd = seed_for(designation)
    f = features(name, description, sd)
    eq, pole, precip = CLIMATE_BAND[f["climate"]]

    # A world whose ceiling sits high on the Ladder is not a quiet one. Band drives how contested
    # it is -- more states, more borders, more war -- which is the map reading of a magnitude.
    tier = 0 if band in ("unassayed", None) else max(0, int(re.sub(r"\D", "", band) or 0))
    states = min(40, 6 + tier * 3 + (4 if f["condition"] == "wartorn" else 0))
    if f["condition"] == "ruined":
        states = max(2, states // 3)          # ruin means fewer standing polities, not none

    return {
        "designation": designation,
        "seed": sd,
        "template": TEMPLATE[f["landform"]],
        "temperature_equator": eq,
        "temperature_pole": pole,
        "precipitation": precip,
        "states": states,
        "cultures": max(3, min(24, states // 2 + 3)),
        "culture_set": CULTURE_SET.get(register, "european"),
        "religions": max(2, states // 3),
        "size": {"spacefaring": 90, "industrial": 70, "magical": 55,
                 "medieval": 45, "primitive": 35}.get(f["tech"], 50),
        "era": f["tech"],
        "features": {k: v for k, v in f.items() if not k.startswith("_")},
        "provenance": f["_provenance"],
        "attested_axes": f["_attested_axes"],
        "band": band,
        "continuity_group": continuity,
    }


def address(opt):
    """The whole world in one short string. This is what gets stored, not a map file."""
    return "|".join(str(x) for x in [
        opt["seed"], opt["template"], opt["temperature_equator"], opt["temperature_pole"],
        opt["precipitation"], opt["states"], opt["cultures"], opt["culture_set"],
        opt["religions"], opt["size"],
    ])


# Empirically tested against Azgaar v1.146.0 on 2026-08-20, because the wiki documents only
# seed/options/width/height/scale/x/y/burg/cell and this module was emitting ten parameters.
#
#     seed        APPLIED    documented
#     template    APPLIED    undocumented but functional -- landform genuinely reaches the map
#     width/height APPLIED   and REQUIRED: without them the same seed lays out differently
#                            per device, which silently broke reproducibility
#     culturesSet IGNORED    asked for 'oriental', got Orkish/Dwarven/Goblin -- the fantasy set
#     statesNumber IGNORED   asked 4, got 16
#     culturesNumber IGNORED asked 3, got 7
#     religionsNumber IGNORED asked 2, got 14
#     temperature*, precipitation  IGNORED
#
# So eight of the ten parameters this function used to emit did nothing, and the URL LOOKED like
# it encoded the derived profile while four fifths of it was decoration. Emitting a parameter that
# is silently discarded is worse than omitting it: it invites the reader to believe the climate
# they see was the climate we derived.
URL_SETTABLE = ("seed", "template", "width", "height")

def to_fmg_query(opt, base="https://azgaar.github.io/Fantasy-Map-Generator/",
                 width=1920, height=1080):
    """Render for Azgaar, emitting ONLY what that generator actually honours.

    The rest of the canonical struct still stands -- it is the library's description of the world
    and is what the entry cites. It simply cannot be pushed through a query string. Reaching the
    climate and culture settings needs FMG's `maplink` parameter and a generated .map file, which
    is a real option and a much larger build.
    """
    q = {"seed": opt["seed"], "template": opt["template"],
         "width": width, "height": height, "options": "default"}
    return base + "?" + urllib.parse.urlencode(q)


def unreachable_by_url(opt):
    """What the profile derives that a query string cannot deliver. Named, not hidden."""
    return {k: v for k, v in opt.items()
            if k in ("temperature_equator", "temperature_pole", "precipitation",
                     "states", "cultures", "culture_set", "religions", "size")}


# ==================================================================================================
def build_all(limit=None):
    import pipeline as PL
    try:
        with open(os.path.join(HERE, "data", "ONOMASTICON.json"), encoding="utf-8") as f:
            ono = json.load(f)
    except Exception:
        silence.note("worldseed.py:248")
        ono = {}
    reg_by_group = {v["continuity_group"]: v["register"] for v in ono.values()}
    try:
        with open(os.path.join(HERE, "data", "CONTINUITY_GROUPS.json"), encoding="utf-8") as f:
            groups = json.load(f)["groups"]
        gid = {s: i for i, g in enumerate(groups) for s in g}
    except Exception:
        silence.note("worldseed.py:255")
        gid = {}

    WORLD = re.compile(r"\b(planet|world|moon|homeworld|colony|continent|realm|kingdom|empire|"
                       r"nation|island|city|region|land)\b", re.I)
    out = []
    for _, rec in PL.records():
        src = rec["source"]
        g = gid.get(src, 0)
        reg = reg_by_group.get(g, "classical")
        for e in rec["entries"]:
            if not e.get("catalogued") or e.get("topic") != "Places":
                continue
            nm, d = e.get("name") or "", e.get("description") or ""
            # The whole description, not its first 200 characters. This is a plain in-memory
            # regex over text already loaded -- there is no token budget here to justify a
            # window -- and the median description is 167 characters, so a meaningful tail of
            # them run past the cutoff. A Place whose defining "world"/"planet"/"moon" word
            # fell past character 200 was silently excluded from ever receiving a worldseed
            # address, with nothing counting what was skipped. Fixed 2026-08-24.
            if not (WORLD.search(d) or WORLD.search(nm)):
                continue
            desig = f"{src}::{nm}"
            out.append(to_options(desig, nm, d, e.get("magnitude") or "unassayed", reg, g))
            if limit and len(out) >= limit:
                return out
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    worlds = build_all(args.limit)
    print("=" * 100)
    print("WORLDSEED — one short address per inhabited world")
    print("=" * 100)
    print(f"\nworlds encoded: {len(worlds):,}")
    addrs = [address(w) for w in worlds]
    print(f"mean address length: {sum(len(a) for a in addrs)/max(1,len(addrs)):.0f} chars")
    print(f"whole library at this rate: {sum(len(a) for a in addrs)/1024:.1f} KB "
          f"(a saved map is megabytes EACH)")

    import collections
    for k in ("template", "culture_set", "era"):
        print(f"\n  {k} distribution: {dict(collections.Counter(w[k] for w in worlds).most_common(6))}")

    print("\n" + "-" * 100)
    print("SAMPLE — description in, world out")
    print("-" * 100)
    for w in worlds[:6]:
        print(f"\n  {w['designation'][:60]}")
        print(f"     features {w['features']}  band={w['band']}")
        print(f"     address  {address(w)}")
    if worlds:
        print("\n  example query:")
        print("     " + to_fmg_query(worlds[0])[:150])

    if args.write:
        # ATOMIC. This was a bare `open(path, "w")` + `json.dump`, which is not a write but a
        # TRUNCATE-THEN-FILL: a reader arriving in the gap sees an empty or half-written file,
        # and a kill in the gap leaves it that way permanently. The 2026-08-25 sweep found
        # twelve such sites across ten modules and moved them onto `silence.write_json`, whose
        # temp name carries pid and thread so two writers of one path cannot collide on the
        # temp file itself; every sibling cross-cycle artifact (data/CHAIN.json,
        # data/DESIGNATORS.json, data/SWEEP_ROLL.json, data/records/*.json) already goes that
        # way and WORLDSEEDS.json was simply missed. The verdict is REPORTED rather than
        # discarded: `write_json` returns False on a denied replace instead of raising, so a
        # caller that ignores it prints "wrote" for a file that never landed -- which is the
        # same class of silent failure one level up.
        path = os.path.join(HERE, "data", "WORLDSEEDS.json")
        payload = {w["designation"]: {"address": address(w), **w} for w in worlds}
        if silence.write_json(path, payload, indent=2, ensure_ascii=False):
            print(f"\nwrote {path}")
        else:
            print(f"\nWRITE DENIED {path} — replace refused; it lands on the next run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
