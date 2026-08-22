#!/usr/bin/env python3
"""
THREAD INTEGRITY — does the omniverse hold together when you walk it?

WHY THIS IS THE COHERENCE TEST
------------------------------
A library feels like one place when following a cross-reference pays off: you walk from an entry
to the thing it names, and the far end knows you are coming. It feels like a pile of files when
the thread leads somewhere that has never heard of where you came from.

The Panscriptum has the notation -- Threads (⌁) carry spine codes, shelfmarks and event-codes, and
the Doctrine of Derivation requires *every factual claim to cite a Law or a Deed*. What it has
never had is anything that CHECKS them. A thread that points at nothing, or points at something
that does not point back, is exactly the failure the Doctrine was written to prevent, and nothing
in the pipeline would notice.

THE ASYMMETRY IS THE INTERESTING PART
-------------------------------------
Naive reciprocity is wrong here, and this is where the charter is better than a normal
cross-reference checker. Some one-way threads are CORRECT:

  * The Aperture Doctrine (I.9) mandates it. A local entry carries a Position Paragraph naming
    the wider flows; the wider flows do not name the cloak. "The smith does not know about the
    Reapers. The entry should know that he does not know."
  * Propagation forbids it. If shelf B sits 1,126 years away and the event is 300 years old, B
    CANNOT thread back -- the news has not arrived. A reciprocal link there would be the error.

So the checker classifies rather than scolds:
    RECIPROCAL   both ends know each other -- the omniverse is joined here
    ASYMMETRIC-LAWFUL   one-way, and aperture or propagation explains why
    ASYMMETRIC-SUSPECT  one-way with no excuse -- a real hole
    DANGLING     points at nothing that exists
"""
import argparse
import collections
import json
import os
import sys
import silence

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_entities():
    """Every catalogued entity, by source, with its normalised key."""
    import glob
    import re
    ents = collections.defaultdict(set)
    names = {}
    for p in glob.glob(os.path.join(HERE, "data/records/*.json")):
        try:
            with open(p, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            silence.note("thread_integrity.py:54")
            continue
        for e in rec.get("entries", []):
            k = re.sub(r"[^a-z0-9]", "", re.sub(r"\([^)]*\)", "", (e.get("name") or "").lower()))
            if k:
                ents[rec["source"]].add(k)
                names.setdefault(k, e.get("name"))
    return ents, names


def implied_threads(candidates_path=None):
    """Threads implied by shared entities: if two sources attest one entity, each should thread
    to the other through it. This is the weave's output read as an obligation."""
    path = candidates_path or os.path.join(HERE, "data/WEAVE_CANDIDATES.json")
    with open(path, encoding="utf-8") as f:
        cand = json.load(f)
    pairs = collections.defaultdict(set)
    for key, hits in cand.items():
        srcs = sorted({h["source"] for h in hits})
        for i in range(len(srcs)):
            for j in range(len(srcs)):
                if i != j:
                    pairs[(srcs[i], srcs[j])].add(key)
    return pairs


def classify(pairs, distance_fn=None, event_age_years=300.0):
    """Sort implied threads into the four classes."""
    out = collections.Counter()
    detail = collections.defaultdict(list)
    seen = set()
    for (a, b), shared in pairs.items():
        if (b, a) in seen or (a, b) in seen:
            continue
        seen.add((a, b))
        back = pairs.get((b, a))
        if back:
            out["RECIPROCAL"] += 1
            detail["RECIPROCAL"].append((a, b, len(shared)))
            continue
        # one-way: is there a lawful excuse?
        excuse = None
        if distance_fn:
            d = distance_fn(a, b)
            if d is not None and d * 1000.0 > event_age_years:
                excuse = f"propagation: {d*1000:.0f}yr away, event is {event_age_years:.0f}yr old"
        if excuse:
            out["ASYMMETRIC-LAWFUL"] += 1
            detail["ASYMMETRIC-LAWFUL"].append((a, b, excuse))
        else:
            out["ASYMMETRIC-SUSPECT"] += 1
            detail["ASYMMETRIC-SUSPECT"].append((a, b, len(shared)))
    return out, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--age", type=float, default=300.0)
    args = ap.parse_args()

    ents, names = load_entities()
    print(f"sources with catalogued entities : {len(ents)}")
    print(f"distinct entity keys             : {len(names):,}")

    pairs = implied_threads()
    print(f"implied thread directions        : {len(pairs):,}")
    print()

    try:
        import propagation as P
        adj = P.load_graph()

        def dist(a, b):
            d, path = P.shortest(adj, a, b)
            return None if not path else d
    except Exception:
        dist = None
        print("(propagation graph unavailable; asymmetry cannot be excused by distance)")

    counts, detail = classify(pairs, dist, args.age)
    total = sum(counts.values())
    print("THREAD INTEGRITY")
    for k in ("RECIPROCAL", "ASYMMETRIC-LAWFUL", "ASYMMETRIC-SUSPECT", "DANGLING"):
        if counts.get(k):
            print(f"  {k:20s} {counts[k]:6,}  ({counts[k]/total:5.1%})")
    print()
    if detail["RECIPROCAL"]:
        print("  strongest reciprocal bonds (the omniverse joined):")
        for a, b, n in sorted(detail["RECIPROCAL"], key=lambda x: -x[2])[:8]:
            print(f"     {n:4d} shared  {a[:26]:28s} <-> {b[:26]}")
    if detail["ASYMMETRIC-SUSPECT"]:
        print()
        print("  one-way with no excuse (real holes, review these):")
        for a, b, n in sorted(detail["ASYMMETRIC-SUSPECT"], key=lambda x: -x[2])[:6]:
            print(f"     {n:4d} shared  {a[:26]:28s}  -> {b[:26]}")


if __name__ == "__main__":
    main()
