#!/usr/bin/env python3
"""
NAVTREE — the terminal's navigation data, with every branch reachable.

THREE BUGS THIS FILE EXISTS TO NOT REPEAT
-----------------------------------------
The first build of this data was assembled inline and had three faults, all of which made the
terminal show fewer things than the library holds:

  1. AN ENTIRE HYPERVERSE WAS UNREACHABLE. The tree was built from WORLDS, and a world only exists
     for a source with catalogued Places entries. H3's sources have none yet -- phase 2 is a third
     of the way through the alphabet -- so H3 had no worlds, and with no worlds it had no node, and
     with no node it could not be clicked. A branch of the omniverse simply was not there.

  2. WORLD LISTS WERE TRUNCATED AT FORTY. One universe claimed 157 worlds and listed 40. The count
     in the panel was right and the bubbles were a subset, which is the worst combination: it looks
     complete and is not.

  3. SOURCES WERE INVISIBLE. A source occupies the top three tiers and its worlds fill the lower
     two, so a source with no catalogued worlds contributed nothing at all -- even though it is a
     real, addressed body of universes sitting on the shelf.

The rule this file follows: EVERY ADDRESSED THING GETS A NODE. A branch that holds a source but no
worlds is still a branch, and it says so rather than disappearing.
"""
import argparse
import json
import os
import sys
import silence

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TIERS = ("hyperverse", "xenoverse", "metaverse", "multiverse", "universe")
OUT = os.path.join(HERE, "data", "NAVTREE.json")


def build():
    import address_space as AS
    import burgs as BG
    import worldseed as WS

    with open(os.path.join(HERE, "data", "SEVENFOLD.json"), encoding="utf-8") as f:
        tree = json.load(f)
    sources, worlds = tree["sources"], tree["worlds"]

    seeds = {}
    for w in WS.build_all():
        era = w["features"].get("tech", "medieval")
        cond = w["features"].get("condition", "settled")
        s = AS.map_seed(w["seed"])
        p1 = BG.largest_city(s, era, cond)
        seeds[w["designation"]] = {
            "s": s, "f": w["features"], "a": w.get("attested_axes", 0),
            "b": p1, "nb": BG.burg_count(s, era, cond, p1),
        }

    # THE TWO NAMING LAYERS. The catalogue designation is what the Library files a world under;
    # the endonym is what its people call it. Both go in the record, neither stands in for the
    # other. Worlds outside the onomasticon keep their source name as their designation -- they
    # were never renamed because nothing collided.
    try:
        with open(os.path.join(HERE, "data", "ONOMASTICON.json"), encoding="utf-8") as f:
            ono = json.load(f)
    except Exception:
        silence.note("navtree.py:65")
        ono = {}
    by_endonym = {}
    for v in ono.values():
        for src in v.get("attestations", []):
            by_endonym[(src, v["endonym"].lower())] = v["catalogue_name"]
    for desig, meta in seeds.items():
        src, _, nm = desig.partition("::")
        cat = by_endonym.get((src, nm.strip().lower()))
        meta["cat"] = cat or nm.strip()
        meta["endo"] = nm.strip()
        meta["carried"] = bool(cat)

    nodes = {}

    def touch(path):
        k = ".".join(map(str, path))
        nodes.setdefault(k, {"t": TIERS[len(path) - 1], "n": 0, "src": 0,
                             "k": set(), "w": [], "s": []})
        return nodes[k]

    # 1. SOURCES first, so a branch exists even where nothing has been catalogued yet.
    for name, c in sources.items():
        path = []
        for t in ("hyperverse", "xenoverse", "metaverse"):
            path.append(c[t])
            nd = touch(path)
            nd["src"] += 1
            if len(path) > 1:
                touch(path[:-1])["k"].add(".".join(map(str, path)))
        touch(path)["s"].append(name)

    # 2. WORLDS, which reach two tiers deeper. No cap: a universe lists every world it holds.
    for desig, c in worlds.items():
        path = []
        for t in TIERS:
            path.append(c[t])
            nd = touch(path)
            nd["n"] += 1
            if len(path) > 1:
                touch(path[:-1])["k"].add(".".join(map(str, path)))
        meta = seeds.get(desig, {})
        touch(path)["w"].append({"d": desig, **meta})

    # ---- NAMES FOR EVERY TIER NODE ------------------------------------------------------
    # Numbers are an index, not a name. A hyperverse takes the name of its grounding type; every
    # tier below is coined from the onomasticon's syllabary, seeded on the node's own key so the
    # name is stable, and drawn in the register its contents imply so a metaverse sounds like the
    # multiverses inside it.
    import onomast as O
    try:
        with open(os.path.join(HERE, "data", "GROUNDINGS.json"), encoding="utf-8") as f:
            grounds = json.load(f)
    except Exception:
        silence.note("navtree.py:118")
        grounds = {}
    try:
        with open(os.path.join(HERE, "data", "GENRES.json"), encoding="utf-8") as f:
            genres = json.load(f)
    except Exception:
        silence.note("navtree.py:123")
        genres = {}

    # Seven hyperverses drawn from six grounding types means some type names get used twice.
    # An ordinal suffix ("The Outflow the Second") says nothing about the place and doubles the
    # length of a label that has to fit on the rim of the map, so each type carries a set of
    # names for the same cosmological ground instead. A second emanation hyperverse is The
    # Effusion: the same claim about how it came to be, said another way.
    HYPER_NAME = {
        "ex_nihilo":     ["The Spoken", "The Uttered", "The Fiat", "The Summons"],
        "emanation":     ["The Outflow", "The Effusion", "The Welling", "The Overspill"],
        "eternal_cycle": ["The Wheel", "The Return", "The Turning", "The Recurrence"],
        "demiurgic":     ["The Shaped", "The Wrought", "The Fashioned", "The Handiwork"],
        "immanent":      ["The Indwelling", "The Inhering", "The Suffused", "The Pervasion"],
        "ungrounded":    ["The Unfounded", "The Unmoored", "The Baseless", "The Adrift"],
    }

    def sources_under(key):
        out = []
        for name, c in sources.items():
            path = ".".join(str(c[t]) for t in ("hyperverse", "xenoverse", "metaverse"))
            # The `+ "."` on BOTH arms, not just the first. Without it `key.startswith(path)`
            # matched on a digit prefix, so a source shelved at "0.1.2" was counted as sitting
            # above node "0.1.20" -- an unrelated sibling branch -- and its genre register voted
            # in that node's naming ballot. The exact-equality case is already the first arm,
            # so both startswith arms want the strict-descendant form. (BUGS m11, 2026-08-23.)
            if path == key or path.startswith(key + ".") or key.startswith(path + "."):
                out.append(name)
        return out

    def register_for(key):
        regs = [genres.get(s, {}).get("register") for s in sources_under(key)]
        regs = [r for r in regs if r in O.REGISTERS]
        if not regs:
            return "classical"
        # m41. `max(set(regs), key=regs.count)` is NOT deterministic. On a tie -- two registers
        # equally common under this node, the ordinary case for a small branch -- max() keeps
        # whichever the SET yielded first, and set order for strings is hash-randomized per
        # process. The register is an input to coin_well_formed below, so a flipped tie renames
        # the node. Measured: two consecutive `navtree --write` runs renamed 75 of 734 nodes.
        # The name as secondary key makes the tie-break explicit and repeatable.
        return max(set(regs), key=lambda r: (regs.count(r), r))

    taken = set()
    names = {}
    for k in sorted(nodes, key=lambda x: (len(x.split(".")), x)):
        depth = len(k.split("."))
        if depth == 1:
            srcs_here = sources_under(k)
            gs = [grounds.get(s, {}).get("grounding") for s in srcs_here]
            gs = [g for g in gs if g and g != "ungrounded"]
            # Same hash-order tie-break as register_for above (m41): this one picks the
            # hyperverse's grounding type, and so its name straight out of HYPER_NAME.
            top = max(set(gs), key=lambda g: (gs.count(g), g)) if gs else "ungrounded"
            pool = HYPER_NAME.get(top, HYPER_NAME["ungrounded"])
            nm = next((x for x in pool if x.lower() not in taken), None)
            if nm is None:
                # Four names per type against a ceiling of seven hyperverses; this branch is
                # reachable only if the grounding pass collapses five or more onto one type.
                nm, i = pool[0], 1
                while nm.lower() in taken:
                    i += 1
                    nm = f"{pool[0]} {i}"
            names[k] = nm
        else:
            nm = O.coin_well_formed(f"tier|{k}", register_for(k), taken)
            names[k] = nm
        taken.add(names[k].lower())

    out = {}
    for k, v in nodes.items():
        e = {"t": v["t"], "n": v["n"], "src": v["src"], "k": sorted(v["k"]),
             "name": names.get(k, k)}
        if v["w"]:
            e["w"] = sorted(v["w"], key=lambda x: x["d"])
        if v["s"]:
            e["s"] = sorted(v["s"])
        out[k] = e

    roots = sorted((k for k in out if "." not in k), key=int)
    return {"roots": roots, "nodes": out}


def audit(data):
    """Every claim the terminal makes must be one the data can honour."""
    nodes, problems = data["nodes"], []
    for k, v in nodes.items():
        if v["k"]:
            # Skips a child that has no node instead of raising KeyError on it. The loop below
            # is written to REPORT that exact condition, and dereferencing every child key
            # first meant audit() would crash rather than name the fault it exists to catch.
            s = sum(nodes[c]["n"] for c in v["k"] if c in nodes)
            if s != v["n"]:
                problems.append(f"{k}: claims {v['n']} worlds, children sum to {s}")
        elif v["n"] != len(v.get("w", [])):
            problems.append(f"{k}: claims {v['n']} worlds, lists {len(v.get('w', []))}")
        for c in v["k"]:
            if c not in nodes:
                problems.append(f"{k}: child {c} has no node")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    data = build()
    nodes = data["nodes"]
    print("=" * 88)
    print("NAVTREE — every addressed thing gets a node")
    print("=" * 88)
    print(f"\nnodes  : {len(nodes):,}")
    print(f"roots  : {data['roots']}")

    import collections
    by_tier = collections.Counter(v["t"] for v in nodes.values())
    print("\nnodes per tier:")
    for t in TIERS:
        print(f"   {t:<12}{by_tier.get(t, 0):>5}")

    worlds = sum(len(v.get("w", [])) for v in nodes.values())
    srcs = sum(len(v.get("s", [])) for v in nodes.values())
    print(f"\nworlds listed : {worlds:,}")
    print(f"sources listed: {srcs:,}")

    empty = [k for k, v in nodes.items() if v["n"] == 0]
    print(f"branches holding sources but no catalogued worlds yet: {len(empty)}")
    print("   (these were invisible before — a branch is a branch)")

    problems = audit(data)
    print(f"\nAUDIT: {len(problems)} problems")
    for p in problems[:6]:
        print("   " + p)

    if args.write and not problems:
        # ATOMIC. This site had no temp-file staging at all -- not even the bare
        # `path + ".tmp"` + `os.replace` that other modules hand-rolled -- while `silence` was
        # already imported here for other purposes. The m100 tail, 2026-08-25.
        silence.write_json(OUT, data, separators=(",", ":"), ensure_ascii=False)
        print(f"\nwrote {OUT}  ({os.path.getsize(OUT)//1024} KB)")
    elif args.write:
        print("\nNOT WRITTEN — audit must be clean first")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
