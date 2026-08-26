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

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_entities():
    """Every catalogued entity, by source, with its normalised key.

    THE KEY SPACE IS THE WHOLE POINT (BUGS d8719255faab, 2026-08-26). These keys are compared
    against `WEAVE_CANDIDATES.json`, whose keys are produced by `weave_index.norm`. This
    function used to fold by hand -- lowercase, drop parentheticals, strip non-alphanumerics --
    which is NOT that fold, and so the comparison was between two different key spaces. Every
    name the two folds disagreed on read as an entity that had vanished from its source, and
    got reported as a broken obligation when nothing was broken:

      * no accent folding      "Amelie" vs "amlie" -- `norm` does NFKD first
      * no title stripping     "The Ordning", "St Patrick's Day" keep their article/honorific
      * no @continuity suffix  0 such keys today, but 100% wrong the first time one appears

    Measured against live data before the fix: 24 of 2,775 candidate keys could not be produced
    by the hand fold at all, and 418 of 592 DANGLING pairs were pure artifacts of it.

    The correct fix was rejected once on cost -- `norm` was 13.0 ms/call, so ~43 min over this
    corpus. That was the `_records_sig` defect (BUGS 31715d371415), now fixed; `norm` is
    0.012 ms/call and the designation set is hoisted here exactly once for the whole pass.
    """
    import weave_index as WI
    ents = collections.defaultdict(set)
    names = {}
    known = WI.designations()
    for rec in WI.load_records():
        for e in rec.get("entries", []):
            k = WI.norm(e.get("name"), known)
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


def classify(pairs, distance_fn=None, event_age_years=300.0, recorded=None, ents=None):
    """Sort threads into the classes -- honestly about which are measurable TODAY.

    THE 2026-08-24 CORRECTION (BUGS m12, owner: FIX IT ALL). `implied_threads` builds its
    pair map SYMMETRICALLY by construction -- both (a,b) and (b,a) exist for every shared
    entity -- so comparing it against itself made every pair RECIPROCAL and left the
    ASYMMETRIC classes structurally unreachable: the module was measuring its own input's
    shape and calling it the omniverse's. Asymmetry is real only against a DIRECTED record
    of which entries actually carry a Thread -- and per Hard Rule 5 that graph does not
    exist until the owner's Step 4 entanglement pass. So:

      recorded=None (today)   implied pairs classify as IMPLIED-UNRECORDED -- obligations
                              awaiting the entanglement pass, counted and listed, never
                              dressed as reciprocity nobody verified. DANGLING and
                              PARTIALLY-DANGLING are computed for real, against the live
                              records: a candidate key whose source no longer holds that
                              entity (weave drift), for all of a pair's shared keys or
                              only some of them.
      recorded={(a,b),...}    the future directed graph. The original four-way
                              classification runs, asymmetry classes and all.
    """
    out = collections.Counter()
    detail = collections.defaultdict(list)
    seen = set()
    for (a, b), shared in pairs.items():
        if (b, a) in seen or (a, b) in seen:
            continue
        seen.add((a, b))
        if ents is not None:
            gone = [k for k in shared if k not in ents.get(a, ()) or k not in ents.get(b, ())]
            if gone and len(gone) == len(shared):
                out["DANGLING"] += 1
                detail["DANGLING"].append((a, b, len(gone), len(shared)))
                continue
            if gone:
                # BUGS 2b4e0f497aac. Drift was only reported when EVERY shared key had gone,
                # so a pair sharing 100 entities of which 99 had drifted printed as a clean
                # obligation -- 99 broken threads invisible behind one survivor. Partial drift
                # gets its own class rather than being folded into DANGLING: the pair DOES
                # still hold live shared entities, so it is a real obligation, and calling it
                # wholly dangling would be the opposite error. Exclusive, like DANGLING, so
                # the classes still partition the pairs and the percentages still sum.
                out["PARTIALLY-DANGLING"] += 1
                detail["PARTIALLY-DANGLING"].append((a, b, len(gone), len(shared)))
                continue
        if recorded is None:
            out["IMPLIED-UNRECORDED"] += 1
            detail["IMPLIED-UNRECORDED"].append((a, b, len(shared)))
            continue
        back = (b, a) in recorded
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

    counts, detail = classify(pairs, dist, args.age, ents=ents)
    total = sum(counts.values())
    print("THREAD INTEGRITY")
    print("(no directed thread graph exists yet -- Hard Rule 5; asymmetry classes activate "
          "with the Step 4 entanglement pass)")
    for k in ("IMPLIED-UNRECORDED", "RECIPROCAL", "ASYMMETRIC-LAWFUL", "ASYMMETRIC-SUSPECT",
              "PARTIALLY-DANGLING", "DANGLING"):
        if counts.get(k):
            print(f"  {k:20s} {counts[k]:6,}  ({counts[k]/total:5.1%})")
    print()
    if detail["PARTIALLY-DANGLING"]:
        print("  partial weave drift (obligation still real, some shared entities gone):")
        for a, b, n, tot in sorted(detail["PARTIALLY-DANGLING"], key=lambda x: -x[2])[:8]:
            print(f"     {n:4d}/{tot:<5d} drifted  {a[:24]:26s} <-> {b[:24]}")
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
