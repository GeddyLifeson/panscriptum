#!/usr/bin/env python3
"""
Phase 4, first half — the shared-stage graph. Pure Python, no model.

HOW TERRA MOSAICA EXPANDS INTO AN OMNIVERSE
-------------------------------------------
Terra Mosaica is not a special case; it is the Continuity Rule worked at rung 1. The charter
gives two rules and they do all the lifting at every rung:

  IDENTITY  -- "two sources describing the same thing are the same thing witnessed twice, and
                the disagreements go to the Contradictions register as scholarship, not to
                separate shelves as canon."
  CONTINUITY -- "worlds that share a stage share a history. Every 'modern Earth' is presumed to
                be *the same Earth* unless its physics forbid it."

Applied upward, they generate the whole ladder:

    shared stage        -> same PLANET   (rung 1)   Kamurocho and Shinjuku, one Tokyo
    one spacetime       -> same UNIVERSE (rung 12)  U-TERRA
    shared ORIGIN       -> MULTIVERSE    (rung 13)  the Shattered Futures: Fallout, Hokuto,
                                                    Mad Max, Metro as sibling futures of one past
    resonance           -> METAVERSE     (rung 14)  the Sets of Collection II
    artificial joining  -> XENOVERSE     (rung 15)  the Architects' door-networks
    myth-scale          -> HYPERVERSE    (rung 16)  one Custos each (owner ruling 2026-08-19)
    the total           -> OMNIVERSE     (rung 17)  no outside

So the omniverse is not assembled by decree. It is what you get when you stop pretending that
sources are separate realities and start asking which of them share furniture.

WHAT THIS SCRIPT MEASURES
-------------------------
The shared-stage evidence, empirically: which sources co-attest which entities. Two sources that
both attest Tokyo, the Moon, and the same three factions are sharing a stage, whatever their
publishers thought. That co-attestation graph is the raw material Phase 4 clusters into rungs --
bottom-up from evidence, never top-down from a vision, per the owner's ruling.

Weighting matters and is the whole craft here. A shared "Earth" is weak evidence (34 sources
attest it, so it separates nothing); a shared "Zhentarim" is strong (11 sources, all D&D, and it
correctly binds exactly the Forgotten Realms corpus). So each shared entity contributes
1/log(sources attesting it) -- rare shared entities bind, ubiquitous ones barely count. This is
inverse document frequency, and it is the standard fix for exactly this failure.

Usage:
    python3 src/cosmology_graph.py            # report
    python3 src/cosmology_graph.py --write    # emit data/SHARED_STAGE_GRAPH.json
"""
import argparse
import collections
import json
import math
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAND = os.path.join(HERE, "data/WEAVE_CANDIDATES.json")
OUT = os.path.join(HERE, "data/SHARED_STAGE_GRAPH.json")

# Entities so widely attested they carry no grouping information. Kept explicit rather than
# purely threshold-based so the reasoning is auditable.
UBIQUITOUS_CUTOFF = 12   # attested in more sources than this -> contributes ~nothing


def build_graph():
    with open(CAND, encoding="utf-8") as f:
        cand = json.load(f)

    pair_w = collections.defaultdict(float)
    pair_shared = collections.defaultdict(list)
    src_entities = collections.defaultdict(int)

    for key, hits in cand.items():
        sources = sorted({h["source"] for h in hits})
        n = len(sources)
        if n < 2:
            continue
        for s in sources:
            src_entities[s] += 1
        # inverse-frequency weight: rare co-attestations bind, ubiquitous ones do not
        w = 1.0 / math.log(n + 1.5)
        if n > UBIQUITOUS_CUTOFF:
            w *= 0.15
        name = hits[0]["name"]
        for i in range(n):
            for j in range(i + 1, n):
                p = (sources[i], sources[j])
                pair_w[p] += w
                if len(pair_shared[p]) < 8:
                    pair_shared[p].append(name)
    return pair_w, pair_shared, src_entities


def components(pair_w, threshold):
    """Connected components of the graph above a weight threshold -- candidate rung clusters."""
    adj = collections.defaultdict(set)
    for (a, b), w in pair_w.items():
        if w >= threshold:
            adj[a].add(b)
            adj[b].add(a)
    seen, comps = set(), []
    for node in adj:
        if node in seen:
            continue
        stack, comp = [node], []
        seen.add(node)
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nb in adj[cur]:
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        comps.append(sorted(comp))
    return sorted(comps, key=len, reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--threshold", type=float, default=3.0)
    args = ap.parse_args()

    pair_w, pair_shared, src_entities = build_graph()
    print(f"source pairs sharing >=1 entity : {len(pair_w):,}")
    print()

    top = sorted(pair_w.items(), key=lambda kv: -kv[1])[:16]
    print("STRONGEST SHARED STAGES (inverse-frequency weighted):")
    for (a, b), w in top:
        shared = ", ".join(pair_shared[(a, b)][:4])
        print(f"  {w:6.1f}  {a[:24]:26s} <-> {b[:24]:26s}  {shared[:52]}")
    print()

    comps = components(pair_w, args.threshold)
    print(f"CANDIDATE CLUSTERS at weight >= {args.threshold} : {len(comps)}")
    for c in comps[:8]:
        print(f"  [{len(c):3d}] {', '.join(s[:20] for s in c[:6])}{' …' if len(c) > 6 else ''}")

    if args.write:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump({
                "pairs": [{"a": a, "b": b, "weight": round(w, 3),
                           "shared_sample": pair_shared[(a, b)]}
                          for (a, b), w in sorted(pair_w.items(), key=lambda kv: -kv[1])
                          if w >= 1.0],
                "clusters": comps,
                "threshold": args.threshold,
            }, f, indent=2, ensure_ascii=False)
        print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
