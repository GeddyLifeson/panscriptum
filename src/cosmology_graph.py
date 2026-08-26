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

    w = 1 / log(n + 1.5)          where n = number of sources attesting it
    w = w * 0.15                  additionally, if n > UBIQUITOUS_CUTOFF (12)

-- rare shared entities bind, ubiquitous ones barely count. This is inverse document frequency,
and it is the standard fix for exactly this failure. Two details of the formula, spelled out
because the docstring used to say plain `1/log(n)` and the code has never done that (corrected
2026-08-25, order 353e7210c11c -- the CODE is right, the prose was wrong):

  * the `+1.5` smoothing. n is >= 2 by construction, so plain log(n) never divides by zero, but
    it does hand n=2 a weight of 1.44 -- nearly double n=3's 0.91. That cliff at the smallest,
    noisiest end is exactly where a single spurious co-attestation would do the most damage.
    log(n+1.5) flattens it: 0.80 at n=2, 0.68 at n=3.
  * the x0.15 ubiquity penalty. Smoothing alone still leaves a 34-source "Earth" contributing a
    third of what a 2-source name does, and Earth is attested by nearly everything. Past the
    cutoff the term is knocked down by a further 85% rather than to zero, so ubiquitous shared
    furniture still registers as evidence -- faintly, which is what it is -- instead of being
    deleted from the record.

NOTHING IS FILTERED OUT OF THE WRITTEN GRAPH
--------------------------------------------
Every pair that shares at least one entity is written to data/SHARED_STAGE_GRAPH.json, with its
weight. A consumer that wants only strong pairs applies its own threshold to the `weight` field
it is handed; the stored artifact stays complete and describes itself honestly. (Until
2026-08-25 an undeclared `if w >= 1.0` at the write dropped 2,666 of 3,753 pairs -- 71% -- while
the file recorded `"threshold": 3.0`, a number that had selected nothing. `resonance.py:157`
reads this file to answer "are these two shelves in relation at all", so for 71% of genuinely
co-attesting pairs it returned "no shared furniture". Order 9861c18b8485.)

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

# Entities so widely attested they carry little grouping information. Kept explicit rather than
# purely threshold-based so the reasoning is auditable.
UBIQUITOUS_CUTOFF = 12      # attested in more sources than this -> penalised, not deleted
UBIQUITOUS_PENALTY = 0.15   # ...by this factor. Never 0: faint evidence is still evidence.


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
        # inverse-frequency weight: rare co-attestations bind, ubiquitous ones barely do.
        # Formula and the reasons for both terms are in the module docstring.
        w = 1.0 / math.log(n + 1.5)
        if n > UBIQUITOUS_CUTOFF:
            w *= UBIQUITOUS_PENALTY
        name = hits[0]["name"]
        for i in range(n):
            for j in range(i + 1, n):
                p = (sources[i], sources[j])
                pair_w[p] += w
                # WHOLE list, no cap -- Hard Rule 0, ruled 2026-08-24. `weave.py:478` and
                # `pipeline.py:1795` write this same `shared_sample` key and were both brought in
                # line under that ruling; this file is the one member of the family that was
                # missed, and it kept an `< 8` cap for two more days. The cap was not cosmetic:
                # `resonance.py:146` reads `shared_sample` back as the pair's actual shared
                # evidence, so a ninth shared entity simply did not exist to anything downstream.
                # The key name is kept exactly as the siblings keep it, for resonance's sake.
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
    ap.add_argument("--threshold", type=float, default=3.0,
                    help="weight floor for CLUSTERING only. It has never filtered the pair "
                         "list and now says so in the artifact it writes.")
    ap.add_argument("--show", type=int, default=16,
                    help="how many ranked rows to print on screen (0 = all). Console framing "
                         "only -- --write always emits every pair.")
    args = ap.parse_args()

    pair_w, pair_shared, src_entities = build_graph()
    ranked = sorted(pair_w.items(), key=lambda kv: -kv[1])
    print(f"source pairs sharing >=1 entity : {len(pair_w):,}   (ALL of them are written)")
    print()

    shown = len(ranked) if args.show <= 0 else min(args.show, len(ranked))
    print("STRONGEST SHARED STAGES (inverse-frequency weighted):")
    for (a, b), w in ranked[:shown]:
        names = pair_shared[(a, b)]
        shared = ", ".join(names[:4])
        more = f" (+{len(names) - 4:,} more shared)" if len(names) > 4 else ""
        print(f"  {w:6.1f}  {a[:24]:26s} <-> {b[:24]:26s}  {shared[:52]}{more}")
    if shown < len(ranked):
        print(f"  ... {len(ranked) - shown:,} further pairs not printed here (of "
              f"{len(ranked):,}). Screen framing, not a filter: --show 0 prints them all, "
              f"and --write emits every one.")
    print()

    comps = components(pair_w, args.threshold)
    print(f"CANDIDATE CLUSTERS at weight >= {args.threshold} : {len(comps)}")
    for c in comps[:shown]:
        head = ", ".join(s[:20] for s in c[:6])
        tail = f" (+{len(c) - 6} more)" if len(c) > 6 else ""
        print(f"  [{len(c):3d}] {head}{tail}")
    if shown < len(comps):
        print(f"  ... {len(comps) - shown} further clusters not printed here; all "
              f"{len(comps)} are written to the artifact.")

    if args.write:
        # ATOMIC: propagation.py and resonance.py both read SHARED_STAGE_GRAPH.json live, so a
        # truncate-then-fill here hands them an empty graph they would silently trust.
        #
        # COMPLETE: every pair that shares at least one entity, ranked by weight, none dropped.
        # An undeclared `if w >= 1.0` here used to discard 2,666 of 3,753 pairs (71%) while the
        # file below still announced `"threshold": 3.0` -- so the artifact misdescribed itself
        # AND the number it named had selected nothing. A weight floor is a CONSUMER's decision:
        # every pair carries its `weight`, so anything that wants only strong links filters on
        # that field. Ranking, yes; truncation, never (Hard Rule 0, order 9861c18b8485).
        import silence
        silence.write_json(OUT, {
            "pairs": [{"a": a, "b": b, "weight": round(w, 3),
                       "shared_sample": pair_shared[(a, b)]}
                      for (a, b), w in ranked],
            "pair_count": len(ranked),
            "pairs_filtered": False,
            "clusters": comps,
            "cluster_count": len(comps),
            # `src_entities` was built, returned and unpacked, then read by nothing -- it
            # reached no print and no file, so the per-source count of co-attested entities
            # existed only for the length of one call. Written here, WHOLE and uncapped, so
            # the work the function already does is actually available. Additive: propagation
            # and resonance read `pairs`/`clusters` and are untouched by a new key.
            "source_entities": dict(sorted(src_entities.items())),
            # `threshold` selects CLUSTERS and nothing else. Named twice, unambiguously,
            # because for two days it read as though it had selected the pair list.
            "threshold": args.threshold,
            "threshold_applies_to": "clusters",
            "weight_formula": "1/log(n+1.5), x0.15 when n > 12",
        }, indent=2, ensure_ascii=False)
        print(f"\nwrote {OUT}")
        print(f"  pairs written : {len(ranked):,} of {len(pair_w):,} (all of them, unfiltered)")
        print(f"  clusters      : {len(comps)} at weight >= {args.threshold}")
        print(f"  sources       : {len(src_entities):,}")


if __name__ == "__main__":
    main()
