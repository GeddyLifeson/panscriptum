#!/usr/bin/env python3
"""
PHASE 3 — THE WEAVE. Cross-source entity resolution, with homonymy as the default.

THE MISTAKE THIS MODULE EXISTS TO AVOID
---------------------------------------
The candidate file holds 2,775 names appearing in more than one source, and the temptation is to
call each of them one entity with several attestations. The top of that list is:

    earth   34 sources        mars   21        moon   20        void   15        oracle  11

Adventure Time's Earth and Alien's Earth are not one planet. They are two planets with one name,
in two universes, and the charter settled this before this module existed: shelves are separate
universes at measured propagation distances (I.9, X.7). Fusing them would collapse the omniverse
into a single smeared continuity and every downstream volume would inherit the error.

So the rule is:

    **A SHARED NAME IS NOT AN IDENTITY. Identity requires shared CONTINUITY.**

Within one continuity a repeated name is one entity with several attestations. Across continuities
it is a homonym, and the library keeps both, disambiguated.

Note this cuts against a tempting exception. Zeus appears in Pantheon: Greek and in several D&D
sourcebooks, and it is tempting to fuse them because they descend from one real-world mythology.
That descent is a META fact -- a fact about authors, not about the omniverse -- and the charter
bans meta reasoning in the record. In-universe they are separate beings who share a name, exactly
like the Earths.

HOW CONTINUITY IS DETECTED WITHOUT CIRCULARITY
---------------------------------------------
The existing SHARED_STAGE_GRAPH counted shared names raw, which is why it linked Greek and Roman
myth through "Tartarus (LV-797)" -- a Weyland-Yutani planetary designation -- and tied two D&D
supplements together through "Dexterity" and "Channel Divinity". Raw counts treat a stat name and
a protagonist as equal evidence.

They are not, and information theory says exactly how unequal. An entity appearing in many sources
carries little evidence that any two of them are related; one appearing in few carries a great
deal. That is inverse document frequency:

    idf(e) = log( N_sources / n_sources_containing(e) )

Earth, in 34 of 211 sources, scores 1.82. Ellen Ripley, in 2, scores 4.66. No stoplist is needed
and none is maintained: the weighting is derived from the corpus and updates itself as the
catalogue grows.

A pair's continuity evidence is then the summed idf of everything they share.

THE THRESHOLD IS MEASURED, NOT DECLARED
---------------------------------------
Rather than pick a cutoff by eye, the null is simulated: entity-to-source assignments are shuffled
while preserving how many sources each entity appears in, and the resulting pair weights are the
weights that ARISE BY CHANCE. The cutoff is a high percentile of that null. A pair beats it or it
does not, and the answer is a p-value rather than a preference.
"""
import argparse
import collections
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# A regex escape arriving as a literal control character matches nothing and fails SILENTLY.
# A word-boundary escape written through a shell heredoc has arrived here as a 0x08 backspace
# five separate times in this project. Each time it read as a tuning problem -- a gate that
# passed nothing, a parser that found zero rows -- rather than as corruption, which is what
# makes it expensive. The check is built from chr() codes because the first version was
# written with escapes and they were eaten too, so it flagged its own source and refused.
_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding='utf-8').read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ': a regex escape was eaten in transit - a literal control '
                     'character is present in the source. Repair before running.')


INDEX = os.path.join(HERE, "data", "ENTITY_INDEX.json")
OUT_GROUPS = os.path.join(HERE, "data", "CONTINUITY_GROUPS.json")
OUT_RESOLVED = os.path.join(HERE, "data", "RESOLVED_ENTITIES.json")
OUT_GRAPH = os.path.join(HERE, "data", "SHARED_STAGE_GRAPH_IDF.json")


def load_index():
    with open(INDEX, encoding="utf-8") as f:
        return json.load(f)


def idf_table(index):
    """idf per entity key, plus the source set it occurs in."""
    occ = {k: sorted({h["source"] for h in hits}) for k, hits in index.items()}
    sources = sorted({s for v in occ.values() for s in v})
    N = len(sources)
    idf = {k: math.log(N / len(v)) for k, v in occ.items() if v}
    return occ, idf, sources, N


# Mechanics are not entities. Same reasoning as the scale_note gate in pipeline.py: a resolution
# procedure is not an in-universe thing, so it must not appear in the entity index at all, let
# alone serve as evidence that two universes share a continuity.
import re as _re
import silence
_MECHANIC = _re.compile(
    r"^(oath ?spells?|channel ?divinity|saving ?throws?|hit ?points?|armou?r ?class|"
    r"challenge ?rating|proficiency|initiative|advantage|disadvantage|spell ?slots?|"
    r"cantrips?|ability ?scores?|strength|dexterity|constitution|intelligence|wisdom|"
    r"charisma|action|bonus ?action|reaction|feats?|skills?|classes?|races?|backgrounds?|"
    r"characters?|weapons?|armou?r|equipment|spells?|monsters?|items?)$", _re.I)


# Second-person instructional voice. Rules text addresses a reader and tells them what they may
# do; an in-universe description never does. This catches class features whose text is too terse
# to trip the stat-block detector -- "Ability Score Improvement", "Extra Attack" -- without anyone
# maintaining a list of them.
_RULES_VOICE = _re.compile(
    r"(you (?:can|may|gain|choose|learn|know|have|regain|add|increase|become)"
    r"|when you (?:reach|use|take|hit|cast)"
    r"|at (?:\d+(?:st|nd|rd|th) level|higher levels)"
    r"|starting at \d+(?:st|nd|rd|th) level"
    r"|as (?:an|a) (?:action|bonus action|reaction))", _re.I)


def name_surprisal(index):
    """How unlikely is it that two universes coincidentally share this NAME?

    Source-level idf cannot answer that. "Gordon" is rare AS AN ENTITY (few sources list one) and
    utterly common AS A WORD, so idf scores it as strong evidence and Cowboy Bebop gets welded to
    Thomas the Tank Engine through Gordon, Edward, Annie and Lucy. The same defect married Alien to
    professional wrestling through Australia, Mexico and Iran.

    The right question is the surprisal of the NAME ITSELF, which is a property of its tokens:

        surprisal(name) = sum over tokens of log2( N_entities / df(token) )

    A single common given name scores low, because its token is everywhere. "Weyland-Yutani
    Corporation" scores high, because none of its tokens are. Multi-token distinctive names --
    exactly the ones that indicate a genuinely shared world -- dominate, and no stoplist of
    forenames, countries or weapon nouns has to be written or maintained.
    """
    df = collections.Counter()
    names = {}
    for k, hits in index.items():
        nm = hits[0].get("name") or k
        names[k] = nm
        for tok in set(_re.findall(r"[a-z0-9]+", nm.lower())):
            df[tok] += 1
    Nk = max(1, len(index))
    sur = {}
    for k, nm in names.items():
        toks = set(_re.findall(r"[a-z0-9]+", nm.lower()))
        sur[k] = sum(math.log2(Nk / df[t]) for t in toks if df[t] > 0)
    return sur, names


def pair_weights(occ, idf, min_sources=2):
    """Summed idf of everything each source-pair shares."""
    w = collections.defaultdict(float)
    shared = collections.defaultdict(list)
    for k, srcs in occ.items():
        if len(srcs) < min_sources or len(srcs) > 60:
            # An entity in >60 of 211 sources is a common noun by any reasonable reading and
            # contributes essentially nothing; skipping it also keeps the pair loop tractable.
            continue
        s = idf.get(k, 0.0)
        for i in range(len(srcs)):
            for j in range(i + 1, len(srcs)):
                p = (srcs[i], srcs[j])
                w[p] += s
                # NO CAP -- the idf twin of the same truncation removed in
                # `surprisal_pair_weights` below; see the note there. 2026-08-25.
                shared[p].append(k)
    return w, shared


def filtered_index(index):
    """Drop mechanics before anything else looks at the corpus.

    A name regex alone was too narrow -- it caught "Channel Divinity" and missed "Ability Score
    Improvement" and "Extra Attack", which then ranked among the strongest cross-source fusions.
    Maintaining a list of every class feature ever printed is not a plan.

    So the second gate reuses pipeline._STATBLOCK on the DESCRIPTION, which is the same test the
    scale_note gate already applies: text written in resolution procedure describes a rule, not a
    thing in a world. One detector, two callers, and it does not need updating per supplement.
    """
    try:
        from pipeline import _STATBLOCK
    except Exception:
        # Content label, not a line number: this was tagged "weave.py:187", which is the `try:`
        # three lines above the call it was meant to mark, not the import that actually failed.
        # A stale number costs a grep every time someone diagnoses it (see wiki_source.py's own
        # converted sites for the same fix).
        silence.note("weave.py:statblock-import")
        _STATBLOCK = None
    out, dropped = {}, 0
    for k, hits in index.items():
        nm = (hits[0].get("name") or "").strip()
        desc = hits[0].get("description") or ""
        if (_MECHANIC.match(nm)
                or (_STATBLOCK is not None and _STATBLOCK.search(desc[:400]))
                or _RULES_VOICE.search(desc[:300])):
            dropped += 1
            continue
        out[k] = hits
    return out, dropped


def surprisal_pair_weights(occ, sur, min_sources=2, max_sources=60):
    """Pair evidence weighted by NAME surprisal rather than source-idf."""
    w = collections.defaultdict(float)
    shared = collections.defaultdict(list)
    for k, srcs in occ.items():
        if not (min_sources <= len(srcs) <= max_sources):
            continue
        s = sur.get(k, 0.0)
        for i in range(len(srcs)):
            for j in range(i + 1, len(srcs)):
                p = (srcs[i], srcs[j])
                w[p] += s
                # NO CAP. `if len(shared[p]) < 8` was the last cap standing in the weave, and it
                # was invisible because it sat in the BUILDER while both consumers -- this
                # module's own writer and `pipeline.py:1761`, the production path that writes
                # `data/RESONANCE_GRAPH.json` -- carried the comment "WHOLE list -- Hard Rule 0,
                # ruled 2026-08-24" directly above it. The comment described the ruling; the data
                # had been truncated eight entries earlier. A cap LABELLED AS COMPLIANCE is the
                # worst shape a cap can take, because the label is what stops anyone looking.
                # Found by the whole-tree sweep, 2026-08-25.
                shared[p].append(k)
    return w, shared


def null_threshold_surprisal(occ, sur, sources, trials=20, pct=99.9, seed=20260820):
    """Permutation null on the surprisal weights: what pair evidence arises by chance alone?"""
    rng = random.Random(seed)
    out = []
    keys = [(k, len(v)) for k, v in occ.items() if 2 <= len(v) <= 60]
    for _ in range(trials):
        w = collections.defaultdict(float)
        for k, n in keys:
            srcs = sorted(rng.sample(sources, n))
            sv = sur.get(k, 0.0)
            for i in range(len(srcs)):
                for j in range(i + 1, len(srcs)):
                    w[(srcs[i], srcs[j])] += sv
        if w:
            vals = sorted(w.values())
            out.append(vals[min(len(vals) - 1, int(len(vals) * pct / 100.0))])
    out.sort()
    return out[len(out) // 2] if out else 0.0


def null_threshold(occ, idf, sources, trials=40, pct=99.9, seed=20260820):
    """Permutation null: what pair weight arises purely by chance?

    Each entity keeps the NUMBER of sources it appears in and is reassigned to a random set of
    that size. Everything real about the corpus -- how many entities, how widely each is spread --
    is preserved; only the association between entities and particular sources is destroyed. The
    resulting weights are what coincidence alone produces.
    """
    rng = random.Random(seed)
    maxes = []
    keys = [(k, len(v)) for k, v in occ.items() if 2 <= len(v) <= 60]
    for _ in range(trials):
        w = collections.defaultdict(float)
        for k, n in keys:
            srcs = rng.sample(sources, n)
            srcs.sort()
            s = idf.get(k, 0.0)
            for i in range(len(srcs)):
                for j in range(i + 1, len(srcs)):
                    w[(srcs[i], srcs[j])] += s
        if w:
            vals = sorted(w.values())
            maxes.append(vals[min(len(vals) - 1, int(len(vals) * pct / 100.0))])
    maxes.sort()
    return maxes[len(maxes) // 2] if maxes else 0.0


def components(sources, w, threshold):
    """Continuity groups by COMPLETE-LINKAGE agglomeration, not connected components.

    A first version used connected components of the thresholded graph and produced a single
    "continuity" containing 95 of 211 sources -- Adventure Time, Alien, Warhammer and One Piece all
    fused, and Earth resolved across 24 universes. Exactly the error the module exists to prevent.

    The cause is CHAINING, the classic failure of single-linkage clustering: A links to B, B links
    to C, so A and C land in one cluster though they share nothing. Continuity is not transitive
    in that way. Alien and Predator share a continuity; Predator sharing a weak edge with something
    else does not drag Alien along with it.

    Complete linkage states the requirement directly: a continuity group is one in which EVERY
    pair clears the bar, not merely one where a path exists. That is a clique condition, and it is
    what "these all share a continuity with one another" actually means.
    """
    lookup = {}
    for (a, b), v in w.items():
        lookup[(a, b)] = v
        lookup[(b, a)] = v

    clusters = [[s] for s in sources]

    def min_cross(c1, c2):
        m = float("inf")
        for a in c1:
            for b in c2:
                v = lookup.get((a, b), 0.0)
                if v < m:
                    m = v
                    if m < threshold:
                        return m           # early exit: one bad pair disqualifies the merge
        return m

    merged = True
    while merged:
        merged = False
        best = None
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                m = min_cross(clusters[i], clusters[j])
                if m >= threshold and (best is None or m > best[0]):
                    best = (m, i, j)
        if best:
            _, i, j = best
            clusters[i] = sorted(clusters[i] + clusters[j])
            clusters.pop(j)
            merged = True

    return sorted([sorted(c) for c in clusters], key=lambda g: -len(g))


def resonance_graph(w, sources):
    """THE SECOND GRAPH, and the one this module originally forgot to build.

    Continuity and connectedness are different questions and they need different graphs:

      IDENTITY   strict, complete-linkage. "Is this Earth THAT Earth?" The answer is almost always
                 no, which is why it yields 169 continuities and mostly singletons. Each universe
                 keeps its own Earth, and that is correct.

      RESONANCE  permissive, every shared name counted. "How related are these two shelves?" A
                 shared Earth between Adventure Time and Alien is not an identity, but it is
                 emphatically a RELATION -- which is Vol. 0.5's whole thesis: relation without
                 identity is the normal case, not a failure to resolve.

    Forcing one graph to answer both questions shatters the omniverse into unrelated fragments.
    The owner's test is the right one: everything should be a few hops from everything else. It is
    -- diameter 5, mean path 2.04 -- and that is now measured rather than hoped for.

    This graph, not the identity graph, is what X.7's propagation distances must be read from.
    """
    adj = collections.defaultdict(set)
    for (a, b) in w:
        adj[a].add(b)
        adj[b].add(a)

    def bfs(src):
        d = {src: 0}
        q = collections.deque([src])
        while q:
            n = q.popleft()
            for m in adj[n]:
                if m not in d:
                    d[m] = d[n] + 1
                    q.append(m)
        return d

    ecc, reach = {}, 0
    for s in sources:
        d = bfs(s)
        ecc[s] = max(d.values()) if len(d) > 1 else 0
        reach = max(reach, len(d))
    isolates = sorted(s for s in sources if not adj[s])
    connected = [e for e in ecc.values() if e > 0]
    return {
        "shelves": len(sources),
        "pairs": len(w),
        "largest_component": reach,
        "diameter": max(connected) if connected else 0,
        "isolates": isolates,
        "eccentricity": dict(collections.Counter(ecc.values())),
        "six_degrees_holds": bool(connected and max(connected) <= 6),
        "note": ("isolates share no entity with any other shelf. Some are genuine (a wholly "
                 "self-contained fiction); at least one is an artefact of the mechanics filter, "
                 "which emptied a shelf that consisted entirely of rules text"),
    }


def resolve(index, groups):
    """Canonical entities. Within a continuity group a repeated name is ONE entity; across groups
    it is a homonym and both are kept."""
    gid = {}
    for i, g in enumerate(groups):
        for s in g:
            gid[s] = i
    resolved = {}
    homonyms = 0
    for key, hits in index.items():
        by_group = collections.defaultdict(list)
        for h in hits:
            by_group[gid.get(h["source"], -1)].append(h)
        if len(by_group) > 1:
            homonyms += 1
        for g, hs in by_group.items():
            cid = f"{key}#{g}"
            names = collections.Counter(h["name"] for h in hs)
            bands = [h.get("magnitude") for h in hs
                     if h.get("magnitude") and h["magnitude"] != "unassayed"]
            resolved[cid] = {
                "key": key,
                "continuity_group": g,
                "canonical_name": names.most_common(1)[0][0],
                "attestations": sorted({h["source"] for h in hs}),
                "n_attestations": len({h["source"] for h in hs}),
                "topics": sorted({h.get("topic") for h in hs if h.get("topic")}),
                "bands_attested": sorted(set(bands)),
                "band_conflict": len(set(bands)) > 1,
            }
    return resolved, homonyms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    raw = load_index()
    index, dropped = filtered_index(raw)
    print(f"entity keys {len(raw):,}  ({dropped} mechanics dropped -> {len(index):,})")

    occ, idf, sources, N = idf_table(index)
    sur, names = name_surprisal(index)

    print("\nname surprisal separates genuine sharing from coincidence:")
    for k in ("gordon", "russia", "knife", "ellenripley", "weylandyutanicorporation"):
        if k in sur:
            print(f"   {names[k][:34]:<36} {sur[k]:7.1f} bits")

    w, shared = surprisal_pair_weights(occ, sur)
    thr = null_threshold_surprisal(occ, sur, sources, trials=args.trials)
    print(f"\ncandidate pairs {len(w):,}   permutation threshold {thr:.1f}")
    kept = {p: v for p, v in w.items() if v >= thr}
    print(f"pairs surviving: {len(kept):,} ({len(kept)/max(1,len(w)):.1%})")

    groups = components(sources, w, thr)
    multi = [g for g in groups if len(g) > 1]
    print(f"\ncontinuity groups: {len(groups)}  ({len(multi)} multi-source, "
          f"{len(groups)-len(multi)} singleton universes)")
    for g in multi[:12]:
        print(f"   {len(g):>3}  {[x[:26] for x in g[:4]]}{' ...' if len(g) > 4 else ''}")

    resolved, homonyms = resolve(index, groups)
    fused = sum(1 for v in resolved.values() if v["n_attestations"] > 1)
    print(f"\nresolved entities {len(resolved):,}")
    print(f"  homonym names kept SEPARATE : {homonyms:,}")
    print(f"  genuinely fused             : {fused:,}")
    print(f"  band conflicts to adjudicate: "
          f"{sum(1 for v in resolved.values() if v['band_conflict']):,}")

    print("\n  strongest genuine fusions:")
    for v in sorted(resolved.values(), key=lambda x: -x["n_attestations"])[:8]:
        print(f"     {v['canonical_name'][:30]:<32}{v['n_attestations']:>3}  "
              f"{[x[:18] for x in v['attestations'][:3]]}")

    byk = collections.Counter(v["key"] for v in resolved.values())
    print("\n  most-split homonyms (one name, many universes):")
    for k, n in byk.most_common(6):
        if n > 1:
            print(f"     {names.get(k, k)[:26]:<28} {n} distinct entities")

    if args.write:
        # ATOMIC, and the file handles now actually close. These three were
        # `json.dump(obj, open(path, "w"))` -- truncate-then-fill AND a leaked handle, on files
        # weave_index.py, resonance.py and cosmology_graph.py read live. 2026-08-25.
        silence.write_json(OUT_GROUPS, {"threshold": thr, "groups": groups},
                           indent=2, ensure_ascii=False)
        silence.write_json(OUT_RESOLVED, resolved, indent=2, ensure_ascii=False)
        silence.write_json(OUT_GRAPH,
                           {"threshold": thr, "metric": "name-surprisal, bits",
                            "pairs": [{"a": a, "b": b, "weight": round(v, 2),
                                       "shared_sample": shared[(a, b)]}   # WHOLE list (key name kept: resonance.py reads it) -- Hard Rule 0, ruled 2026-08-24
                                      for (a, b), v in sorted(kept.items(),
                                                              key=lambda kv: -kv[1])]},
                           indent=2, ensure_ascii=False)
        print("\nwrote CONTINUITY_GROUPS / RESOLVED_ENTITIES / SHARED_STAGE_GRAPH_IDF")
    return 0


if __name__ == "__main__":
    sys.exit(main())
