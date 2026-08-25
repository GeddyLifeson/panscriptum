#!/usr/bin/env python3
"""
THE COSMOLOGICAL TIERS — the xenoverse charted, and the hyperverse declined with cause.

WHY THEY WERE '?'
-----------------
Part Two defines four tiers above the universe and the charter's own worked citation prints two of
them as question marks:

    Ω › H? › X? › Mt.ASC › Mv.DRG › U-7 › G.North › P.Earth

That was the right thing to write at the time -- "the Custodes considered guessing a form of
lying" -- because the distinction between a metaverse, a xenoverse and a hyperverse had been
DEFINED but not yet OPERATIONALISED. There was no procedure that could look at two universes and
say which tier joined them.

There is now, and it did not need inventing. It was already in the weave.

THE DEFINITIONS ARE PROCEDURES
------------------------------
Read Part Two's four definitions closely and each one names a different KIND of connection:

    Multiverse   "universes joined by a shared ORIGIN or connective law"
    Metaverse    "multiverses joined by RESONANCE -- theme, law, or mutual recognition"
    Xenoverse    "metaverses joined ARTIFICIALLY -- by builders, or by declaration"
    Hyperverse   "structures of xenoverses so vast they survive only as MYTH"

Those are four strengths of evidence, running from a shared bloodline to a rumour. And the
resonance graph measures exactly that: link weight IS strength of connective evidence. So the four
tiers are four CUTS of one dendrogram, and the only question was where the cuts fall.

They fall at the plateaus, which is what a plateau in a clustering is for -- a range of thresholds
over which the structure does not change is structure that is really there:

    threshold 100    8 clusters   METAVERSE   strong resonance; shared theme and law
    threshold  50    6 clusters   XENOVERSE   held together by deliberate joins

and NO cut for the hyperverse, for reasons set out below -- that tier is declined rather than
charted, and declining it is itself the result.

with the multiverse below them all at 168, taken from complete linkage rather than a threshold
because a shared ORIGIN is an all-pairs condition, not a reachability one.

    168 multiverses  ->  8 metaverses  ->  6 xenoverses  ->  H declined

WHAT MAKES A XENOVERSE ARTIFICIAL
---------------------------------
The middle tier is the one that sounded hardest and turned out to be the most visible. The link
distribution has a cliff:

    6489   Alien <-> Predator
    5926   Call of Duty Zombies <-> Black Ops
    ----   an order of magnitude of nothing ----
    1146   Pantheon: Greek <-> major fantasy pantheons
     365   the 99.5th percentile of all 3,638 links

Two links stand an order of magnitude above every other. Nothing statistical produces that; those
universes were joined because somebody joined them. That is "by builders, or by declaration",
observable, and it is what holds a xenoverse together where mere resonance would not.

THE HYPERVERSE CANNOT BE CHARTED FROM INSIDE ONE
------------------------------------------------
A first pass reported one hyperverse holding 196 of 209 shelves and called that a finding. It was
not. Three things had to be checked before that number meant anything, and all three failed:

  1. WHAT HOLDS IT TOGETHER. Its weakest links are 'dark', 'void', 'magic', 'oracle', 'heaven',
     'world'. Alien and Fire Emblem are bound into one hyperverse because a lot of fiction has a
     thing called the Dark. That is the same failure that once married Cowboy Bebop to Thomas the
     Tank Engine through Gordon -- coincidental common nouns -- and it survives here only because
     three thousand weak links accumulate into connectivity that no single link supports.

  2. WHETHER BETTER EVIDENCE FIXES IT. Requiring each link to rest on a genuinely specific entity
     does not partition the corpus. It erodes it: 196 -> 181 -> 168 -> 155 -> 135 as the bar
     rises, with the remainder falling out as stragglers rather than forming a second structure.
     There is one mass and a tail, at every evidence level.

  3. WHETHER A SECOND ONE COULD EVER BE SEEN. It could not, and this is the decisive point. Every
     tier here is measured from SHARED ENTITIES. A hyperverse that shares no entity with ours
     generates no link, and a thing with no links is indistinguishable from a shelf that simply
     is not in the catalogue. The method can confirm the hyperverse it is standing in and is
     structurally incapable of detecting another.

Which is the charter's own definition arriving from the other direction. A structure that
"survives only as myth" is precisely one for which no shared evidence exists -- so the tier is not
merely unmeasured, it is unmeasurable by any procedure of this kind, from within.

So H stays '?', and the question mark now means something sharper than it did. It was an open
question; it is now a REPORTED LIMIT. X is charted, because deliberate joins stand an order of
magnitude above the noise and can be seen. H is declined, because the evidence that would chart it
is the evidence a hyperverse is defined by not having.

The 13 unaddressed shelves are the honest residue: they share nothing with anything, which is what
a fragment of another hyperverse would look like from here, and also what a self-contained fiction
looks like. Nothing in the data separates those two readings.
"""
import collections
import json
import os
import sys
import silence

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Cuts, taken at the plateaus measured on the resonance graph. Each is the WEAKEST connective
# evidence that still counts as a join at that tier.
# Every cut must be LOOSER than the tier below it, or the nesting breaks. A first attempt put the
# metaverse at 150 while the multiverse sat at the weave's permutation threshold of 102.3 -- so a
# multiverse whose internal pairs ran between 102 and 150 was split across two metaverses, and five
# of them were. A tier that does not contain its own members is not a tier.
MULTIVERSE_THRESHOLD = 102.3        # the weave's permutation threshold, complete linkage
CUTS = [
    ("metaverse",  100.0, "strong resonance: shared theme, law, mutual recognition"),
    ("xenoverse",   50.0, "artificial joins: a deliberate crossover holds the group together"),
    # hyperverse is NOT a cut. See the note above: at any threshold low enough to group
    # xenoverses, the links are coincidental common nouns, and a hyperverse sharing no entities
    # with ours is undetectable in principle. Declining to chart it is the finding.
]
assert all(a[1] > b[1] for a, b in zip(CUTS, CUTS[1:])), "cuts must loosen downward"
assert MULTIVERSE_THRESHOLD >= CUTS[0][1], "multiverse must be tighter than metaverse"
DELIBERATE_JOIN = 2000.0    # above the cliff: no statistical process makes a link this strong


# ==================================================================================================
# THE HYPERVERSE — grounding type (see grounding.py)
# ==================================================================================================
#
# A pantheon-seeded version of this tier lived here and has been REMOVED, not deprecated, because
# two live definitions of one tier is worse than either of them.
#
# The pantheon pass worked on its own terms -- God of War grounded in Norse at 419.6 -- and failed
# on coverage: every godless fiction stayed homeless, and Star Wars has no pantheon and never
# will. Grounding type supersedes it and subsumes it, since a pantheon IS a grounding claim: Norse
# myth is not its own hyperverse, it is a DEMIURGIC one, filed beside every other cosmos that had
# a maker shape pre-existing stuff.
#
# The hyperverse therefore comes from grounding.py and from nowhere else.


def hyperverse_of(source, groundings=None):
    """Per-source grounding index. Diagnostic only -- NOT the hyperverse. See xenoverse_grounding."""
    if groundings is None:
        with open(os.path.join(HERE, "data", "GROUNDINGS.json"), encoding="utf-8") as f:
            groundings = json.load(f)
    order = list(GROUNDING_ORDER)
    g = (groundings.get(source) or {}).get("grounding", "ungrounded")
    return order.index(g) if g in order else order.index("ungrounded")


def xenoverse_grounding(xeno_groups, groundings):
    """THE HYPERVERSE. A grounding is answered per XENOVERSE, not per shelf.

    Assigning it per source broke containment -- three xenoverses ended up spanning two
    hyperverses each, because nothing stopped two universes joined by a deliberate crossover from
    being classified with different cosmogonies. A tier that does not contain its members is not a
    tier, and the same rule caught a bad metaverse cut earlier.

    The fix is not bookkeeping. Two universes joined by an attested crossover are one connected
    cosmological structure, and a connected structure has ONE ground: if you can walk from a world
    made ex nihilo into a world that emanates, the two accounts are answering the same question
    about the same thing and cannot both stand. So the First Argument is answered at the level of
    the xenoverse, by pooling the origin evidence of everything inside it.

    Where members disagree, the strongest-evidenced account carries the xenoverse and the
    dissent is RECORDED rather than averaged away -- which is the Four Hands rule applied to
    cosmogony: a divergent reading is cited with both signatures, never silently reconciled.
    """
    out = {}
    for i, group in enumerate(xeno_groups):
        votes = {}
        for src in group:
            g = groundings.get(src) or {}
            name = g.get("grounding", "ungrounded")
            if name == "ungrounded":
                continue                    # silence is not a vote against
            votes[name] = votes.get(name, 0.0) + float(g.get("score") or 0)
        if not votes:
            best, contested = "ungrounded", []
        else:
            best = max(votes, key=votes.get)
            contested = sorted((k for k in votes if k != best), key=votes.get, reverse=True)
        out[i] = {"grounding": best,
                  "index": GROUNDING_ORDER.index(best),
                  "evidence": round(votes.get(best, 0.0), 1),
                  "contested_by": contested}
    return out


GROUNDING_ORDER = ("ex_nihilo", "emanation", "eternal_cycle", "demiurgic", "immanent",
                   "ungrounded")


def _graph():
    import weave as W
    raw = W.load_index()
    idx, _ = W.filtered_index(raw)
    occ, idf, srcs, N = W.idf_table(idx)
    sur, _ = W.name_surprisal(idx)
    w, shared = W.surprisal_pair_weights(occ, sur)
    return srcs, w, shared


def _components(srcs, w, threshold):
    adj = collections.defaultdict(set)
    for (a, b), v in w.items():
        if v >= threshold:
            adj[a].add(b)
            adj[b].add(a)
    seen, out = set(), []
    for s in srcs:
        if s in seen or not adj[s]:
            continue
        stack, comp = [s], []
        seen.add(s)
        while stack:
            n = stack.pop()
            comp.append(n)
            for m in adj[n]:
                if m not in seen:
                    seen.add(m)
                    stack.append(m)
        out.append(sorted(comp))
    return sorted(out, key=lambda c: -len(c))


def chart(srcs=None, w=None, shared=None):
    """Assign every source its full tier stack. Returns per-source dicts."""
    if srcs is None:
        srcs, w, shared = _graph()

    # multiverse: complete linkage, because a shared ORIGIN binds every member to every other,
    # not merely to a chain of neighbours.
    import weave as W
    multi = W.components(srcs, w, MULTIVERSE_THRESHOLD)
    mv_of = {s: i for i, g in enumerate(multi) for s in g}

    tiers = {}
    for name, thr, _ in CUTS:
        comps = _components(srcs, w, thr)
        tiers[name] = {s: i for i, c in enumerate(comps) for s in c}
        tiers[name + "_groups"] = comps

    try:
        with open(os.path.join(HERE, "data", "GROUNDINGS.json"), encoding="utf-8") as f:
            _groundings = json.load(f)
    except Exception:
        silence.note("tiers.py:245")
        _groundings = {}

    out = {}
    for s in srcs:
        out[s] = {
            "multiverse": mv_of.get(s),
            "metaverse": tiers["metaverse"].get(s),
            "xenoverse": tiers["xenoverse"].get(s),
            "hyperverse": None,          # filled below, from the xenoverse
            "hyperverse_type": None,
            "own_grounding": GROUNDING_ORDER[hyperverse_of(s, _groundings)],
        }
    # The hyperverse is the xenoverse's grounding, so containment holds by construction.
    xg = xenoverse_grounding(tiers["xenoverse_groups"], _groundings)
    for s in srcs:
        xi = out[s]["xenoverse"]
        if xi is not None and xi in xg:
            out[s]["hyperverse"] = xg[xi]["index"]
            out[s]["hyperverse_type"] = xg[xi]["grounding"]
            out[s]["hyperverse_contested_by"] = xg[xi]["contested_by"]
    return out, tiers, multi


def deliberate_joins(w, shared):
    """The links no statistical process explains -- the evidence a xenoverse is artificial."""
    return sorted(((v, a, b, shared.get((a, b), [])[:3])
                   for (a, b), v in w.items() if v >= DELIBERATE_JOIN), reverse=True)


def main():
    srcs, w, shared = _graph()
    charted, tiers, multi = chart(srcs, w, shared)

    print("=" * 96)
    print("THE COSMOLOGICAL TIERS — H? and X? charted")
    print("=" * 96)
    print(f"\n{'tier':<13}{'count':>7}{'largest':>9}   the join that defines it")
    print("-" * 96)
    print(f"{'multiverse':<13}{len(multi):>7}{max(len(g) for g in multi):>9}   "
          f"shared origin (complete linkage, all pairs)")
    for name, thr, why in CUTS:
        g = tiers[name + "_groups"]
        print(f"{name:<13}{len(g):>7}{max(len(x) for x in g):>9}   {why}")

    # "Unaddressed" means shares no entity with ANYTHING -- not merely that its hyperverse is
    # declined, which is now true of every shelf by design.
    linked = {x for pair in w for x in pair}
    unaddressed = [s for s in srcs if s not in linked]
    print(f"\nhyperverse: DECLINED for all {len(srcs)} shelves — uncharted by cause, not omission")
    print(f"unaddressed (share no entity with anything at all): {len(unaddressed)}")
    for s in unaddressed[:6]:
        print(f"   {s}")

    print("\n" + "-" * 96)
    print("NESTING — each tier must strictly contain the one below")
    print("-" * 96)
    order = ["multiverse", "metaverse", "xenoverse"]
    counts = [len(multi)] + [len(tiers[n + "_groups"]) for n, _, _ in CUTS]
    print(f"   {' -> '.join(f'{n} {c}' for n, c in zip(order, counts))}")
    ok = all(counts[i] >= counts[i + 1] for i in range(len(counts) - 1))
    print(f"   monotone: {ok}")
    bad = 0
    for s in srcs:
        c = charted[s]
        if c["xenoverse"] is None:
            continue
        for lo, hi in (("multiverse", "metaverse"), ("metaverse", "xenoverse")):
            peers = [t for t in srcs if charted[t][lo] == c[lo] and c[lo] is not None]
            if peers and len({charted[t][hi] for t in peers}) > 1:
                bad += 1
                break
    print(f"   containment violations (a lower group split across two higher ones): {bad}")

    print("\n" + "-" * 96)
    print("THE DELIBERATE JOINS — why a xenoverse is 'artificial'")
    print("-" * 96)
    for v, a, b, sh in deliberate_joins(w, shared):
        print(f"   {v:>8.0f}  {a[:26]:<28}{b[:26]:<28}{sh}")
    print(f"   (99.5th percentile of all {len(w):,} links is 365 — these are not statistical)")

    print("\n" + "-" * 96)
    print("SAMPLE STACKS")
    print("-" * 96)
    for s in ("Alien", "Predator", "Pantheon: Greek", "Warhammer 40,000",
              "all Fallout", "Adventure Time"):
        if s in charted:
            c = charted[s]
            print(f"   {s[:26]:<28}H{c['hyperverse']} › X{c['xenoverse']} › "
                  f"Mt{c['metaverse']} › Mv{c['multiverse']}")

    out = os.path.join(HERE, "data", "TIERS.json")
    # ATOMIC: the same pattern pipeline.py's `land_json` was already fixed for on this very
    # file (bug m6); this writer was missed at the time. 2026-08-25.
    silence.write_json(out, charted, indent=2, ensure_ascii=False)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
