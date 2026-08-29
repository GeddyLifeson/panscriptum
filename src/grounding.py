#!/usr/bin/env python3
"""
THE HYPERVERSE — grounding type, or: which answer to the First Argument does this cosmos live under.

WHY THIS TIER AND NOT THE OTHER CANDIDATES
------------------------------------------
Part Two's hyperverse is "structures of xenoverses so vast they survive only as myth", and three
readings were tried before this one.

  UNSUPERVISED CLUSTERING found only coincidental common nouns -- Alien and Fire Emblem bound
  together because a lot of fiction has a thing called the Dark.

  PANTHEON SEEDS worked, and worked well: God of War grounds in Norse at 419.6. But it leaves
  every godless fiction homeless. Star Wars has no pantheon and never will.

  MEDIUM would have covered everything and is a META fact -- how a story was told in our world,
  not a property of the omniverse -- which the charter bans in the record.

The reading that survives is the charter's own. The Omega Band already asks what grounds a cosmos;
the regress test already sorts claimants by whether their account grants them a BEFORE, a STAGE, or
a STATE SPACE; the First Argument is called the library's oldest open case. Promote that from
claimants to cosmoi and the hyperverse is:

    THE KIND OF ANSWER A COSMOS GIVES TO THE FIRST ARGUMENT.

That fits the definition exactly rather than approximately. A grounding is only ever attested in
myth -- there is no other way to attest one, since nobody witnessed it and no instrument reaches
it -- so "survives only as myth" is not a limitation on the tier, it is a description of what
grounds ARE.

AND IT SUBSUMES THE PANTHEON WORK
---------------------------------
A pantheon IS a grounding claim, so nothing from that pass is discarded: Greek myth and the Elder
Scrolls both answer the First Argument, and here they sort by the TYPE of answer rather than by
which gods give it. The godless fictions get an answer too, because "no ground, the regress runs
forever" is itself a type -- and, as it turns out, a populous one.

THE TYPES
---------
Six, derived by running the regress test's three questions to their combinations rather than
invented freehand. Each is a distinct way for the regress to halt, or to fail to.
"""
import argparse
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import assay as A          # noqa: E402

# A regex escape arriving as a literal control character matches nothing and fails SILENTLY.
# A word-boundary escape written through a shell heredoc has arrived here as a 0x08 backspace
# five separate times in this project. Each time it read as a tuning problem -- a gate that
# passed nothing, a parser that found zero rows -- rather than as corruption, which is what
# makes it expensive. The check is built from chr() codes because the first version was
# written with escapes and they were eaten too, so it flagged its own source and refused.
# This module carries sixteen word-boundary escapes across `_ORIGIN` and the `GROUNDINGS`
# cues, and until run #33 was the one file of its shape in the kit without the guard.
_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding='utf-8').read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ': a regex escape was eaten in transit - a literal control '
                     'character is present in the source. Repair before running.')

# What counts as an entry that speaks to origins at all. Everything else is a fact about the
# world, not about how it came to be one.
_ORIGIN = re.compile(
    r"\b(creat|origin|genesis|beginning|primordial|first (?:age|men|ones|gods?)|"
    r"cosmog|cosmolog|birth of|founded the|before (?:time|the world)|the dawn of|"
    r"myth of|legend of the|sundering|emanat|demiurge|world[- ]?tree|cosmic egg|"
    r"void before|ex nihilo|uncreated)\w*", re.I)

# Each type carries the regress-test answers that define it, so the classification is not a
# vocabulary trick with a label on top -- the cues identify the account, and the account's own
# structure decides the verdict via assay.regress_test.
GROUNDINGS = {
    "ex_nihilo": dict(
        regress=dict(has_a_before=False, has_a_stage=False, embedded_in_a_state_space=False,
                     claims_to_be_the_ground=True),
        gloss="creation from nothing; the regress halts at the maker",
        cues={r"\b(created?|made|formed) (?:the|all) (?:world|universe|cosmos|heavens|earth)": 4,
              r"\b(ex nihilo|out of nothing|from nothing|before there was anything|"
              r"in the beginning|spoke .{0,20}into being|first cause|uncreated)": 5,
              r"\b(almighty|omnipotent creator|the creator|prime mover)\w*": 3}),
    "emanation": dict(
        regress=dict(has_a_before=False, has_a_stage=False, embedded_in_a_state_space=False,
                     claims_to_be_the_ground=True),
        gloss="the world flows from a ground that does not act; time emanates with it",
        cues={r"\b(emanat|flowed? (?:from|forth)|proceeds? from|outpouring|the One\b|"
              r"aspects? of the|fragments? of the (?:one|source|divine))\w*": 5,
              r"\b(descend(?:ed|s) from the source|lesser reflections?|hypostas)\w*": 4}),
    "eternal_cycle": dict(
        regress=dict(has_a_before=True, has_a_stage=False, embedded_in_a_state_space=False),
        gloss="no origin; the regress closes into a loop and halts by returning",
        # 'recurr' fired 214 times on "recurring character" and bare 'cycle' 58 times on things
        # like "cycle of violence". A cosmogonic cue must name the COSMOS, not merely repeat.
        cues={r"\b(kalpa|yuga|eternal return|eternal recurrence|ragnarok|cosmic cycle|"
              r"wheel of (?:time|ages|rebirth)|cycle of (?:ages|creation|worlds|destruction)|"
              r"(?:world|universe|cosmos) is (?:reborn|remade)|ages? (?:repeat|turn again)|"
              r"ends? and begins again)\w*": 4,
              r"\b(has always existed|without beginning|beginningless|eternal cosmos|"
              r"no first (?:moment|cause)|time is a circle)": 5}),
    "demiurgic": dict(
        regress=dict(has_a_before=True, has_a_stage=True, embedded_in_a_state_space=False),
        gloss="a maker shaped pre-existing stuff; the regress passes straight through",
        cues={r"\b(shaped|forged|carved|wrought|built) (?:the|this) (?:world|cosmos|land)": 5,
              r"\b(primordial (?:chaos|sea|ocean|waters|void)|from the (?:corpse|body|bones) of|"
              r"titans? before|elder race|those who came before|the first ones)\w*": 4,
              r"\b(world[- ]?tree|world[- ]?serpent|cosmic egg|separation of .{0,18}and)\w*": 3}),
    "immanent": dict(
        regress=dict(has_a_before=False, has_a_stage=False, embedded_in_a_state_space=True,
                     claims_to_be_the_ground=True),
        gloss="the ground is the world itself; no maker stands outside it",
        cues={r"\b(flows? through all|binds? .{0,16}together|present in all (?:things|life)|"
              r"life ?(?:force|energy|stream)|the weave\b|the force\b|anima mundi|"
              r"all things are one)\w*": 5,
              r"\b(pantheis|immanent|the current|the lifestream|natural order)\w*": 3}),
}
UNGROUNDED = "ungrounded"
UNGROUNDED_GLOSS = "no origin account is attested; the regress runs on without halting"


def classify_text(text, top=None):
    """Score every grounding against a body of text. Returns ALL of them, ranked (name, score).

    [HARD RULE 0] `top` defaulted to 3, and that default did two separate kinds of damage
    (corrected 2026-08-25, order e2b3af23cb8a) -- the same defect, in the same shape, as the one
    just fixed in `genre.classify_text` (order bc0b85ea353b):

      1. It truncated a ranked list. Two of the five groundings a source scored against were
         thrown away before anyone saw them, and `classify_source` stored the survivors as
         `runners_up` -- so the classified rows in data/GROUNDINGS.json carry 2 of their 4
         runners-up and the UNGROUNDED rows carry 3 of 5, each of which reads as a complete
         margin and is not one.
      2. Worse, `classify_source` computed `confidence = score / sum(ranked)` with `ranked` the
         TRUNCATED list, so the denominator was the top three scores instead of all five. Every
         published confidence was INFLATED, and that number feeds the contested-cosmogony line
         in `main()` (`confidence < 0.5`), which is what decides whether a cosmos is reported as
         settled or as two accounts running close.

    Ranking is the point and stays; cutting the tail off the ranking is what was wrong, because
    it silently asserted that the other groundings scored nothing. `top` survives so no caller
    breaks, but it now defaults to the whole field. Pass an integer only for a display, never
    for a denominator.

    Whole-corpus measurement, 210 records (59 classified, 151 ungrounded at floor 6),
    top-3 denominator vs full-field denominator:
         14 of the 59 classified sources report a different confidence. The other 45 had
                    nothing outside their top three to add to the denominator -- with only five
                    groundings in the field, most sources score zero on two of them, which is
                    exactly why this stayed invisible for so long.
          0 sources change GROUNDING. The winner is the winner under either denominator, so no
                    published classification, verdict or gloss moves. What moves is the margin.
          4 sources CROSS THE 0.50 CONTESTED-COSMOGONY LINE in `main()`, all of them downward
                    and none upward: the flag was catching 11 sources and catches 15.
                        major fantasy pantheons   ex_nihilo   0.558 -> 0.473
                        Pantheon: Mesoamerican    demiurgic   0.529 -> 0.450
                        Marvel                    emanation   0.553 -> 0.493
                        Bleach                    emanation   0.536 -> 0.484
                    Each was being reported as a settled cosmogony while its own classifier was
                    in fact split across a field it had not been allowed to see.
    The stored margins roughly double: 118 runners-up across the classified rows become 236.

    Note the contrast with `genre`, where 193 of 210 confidences moved and 63 crossed the flag.
    The field there is eleven wide, here it is five; the defect is identical and the blast
    radius is not. A small field hides this bug rather than excusing it.
    """
    scores = collections.Counter()
    for name, spec in GROUNDINGS.items():
        for pat, wt in spec["cues"].items():
            scores[name] += wt * len(re.findall(pat, text, re.I))
    return scores.most_common(top)


def classify_source(rec, cap=None, floor=6):
    """Which answer to the First Argument does this source's cosmos give?

    `floor` matters. A single stray "created the world" is not a cosmogony, and forcing every
    shelf into a type would manufacture exactly the false confidence the Omega Band's own
    integrity rules forbid. Below the floor the honest answer is UNGROUNDED -- which is a real
    type here, not a failure code.

    [HARD RULE 0] `cap` was 140,000 characters, applied to the origin-bearing entries in STORED
    order. Six sources exceed it; Marvel carries 3,888,267 characters across 5,012 origin
    entries, so the cap read 3.6% of the cosmogony and stopped. Whole-corpus check before this
    changed (210 records): no source's VERDICT flipped -- but that is luck, not safety, and the
    reported evidence was wrong regardless. Marvel's `origin_entries` read 153 instead of 5,012
    and its score 95 instead of 930, so the record understated its own attestation 33-fold on
    the very field a reader would use to judge how well-founded the claim is.

    Sibling `genre.classify_source` had the same shape and there SEVEN sources answered
    differently once uncapped -- which is what the two-verdict difference between these modules
    really shows: the cap is a coin toss whose outcome nobody was checking.

    Parameter kept so no caller breaks; a numeric value is refused loudly, as in
    `feats.discover` and `genre.classify_source`. 2026-08-24.
    """
    if cap is not None:
        raise SystemExit(
            "grounding.classify_source: `cap` truncates the origin-entry list in STORED order "
            "(Marvel: 153 of 5,012 origin entries read). Hard Rule 0 -- rank if you must, never "
            "truncate. Pass cap=None.")
    # A cosmogony is stated in a source's ORIGIN entries, not smeared across its whole catalogue.
    # Reading everything let incidental vocabulary outvote the actual creation account -- which is
    # how "recurring character" nearly made eternal recurrence the commonest cosmology in the
    # omniverse. So the scan is targeted, and a source with no origin-bearing entry comes back
    # UNGROUNDED by the honest route: no origin account is attested because none was written down.
    parts, origin_entries = [], 0
    for e in rec.get("entries", []):
        blob = (e.get("name") or "") + " " + (e.get("description") or "")
        if not _ORIGIN.search(blob):
            continue
        origin_entries += 1
        parts.append(blob)
    syn = rec.get("synthesis") or {}
    parts.append((syn.get("rationale") or "") + " " + (syn.get("evidence") or ""))
    # Unranked-away: every grounding in GROUNDINGS is scored and every score is kept, so the
    # denominator below is the whole field and `runners_up` is the whole field minus the winner.
    # See classify_text's note.
    ranked = classify_text(" ".join(parts))
    if not ranked or ranked[0][1] < floor:
        return {"grounding": UNGROUNDED, "score": ranked[0][1] if ranked else 0,
                "confidence": 0.0, "gloss": UNGROUNDED_GLOSS,
                "verdict": "NO CLAIM", "origin_entries": origin_entries,
                # No winner here, so the whole field is the runners-up -- all of it, not the
                # first three of it.
                "runners_up": ranked, "groundings_scored": len(ranked)}

    top, score = ranked[0]
    total = sum(s for _, s in ranked) or 1
    spec = GROUNDINGS[top]
    # The regress test decides the verdict, not the keyword match. A demiurgic account is a
    # demiurge because its own structure grants it a stage -- the cues only identify WHICH
    # account is being told.
    verdict = A.regress_test(top, **spec["regress"])
    return {
        "grounding": top,
        "score": score,
        # Share of the WHOLE field, not of the top three. A cosmos that scores 40 emanation and
        # 38 demiurgic is not confidently either, and the record should say so rather than pick
        # -- but that only works when the losers are in the denominator too.
        "confidence": round(score / total, 3),
        "gloss": spec["gloss"],
        "verdict": verdict["verdict"],
        "assayable": verdict["assayable"],
        "reasoning": verdict["reasoning"],
        "origin_entries": origin_entries,
        "runners_up": ranked[1:],
        # Stated so a reader can tell at a glance that the margin was taken over the full field.
        "groundings_scored": len(ranked),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    import pipeline as PL

    out = {}
    for _, rec in PL.records():
        out[rec["source"]] = classify_source(rec)

    print("=" * 100)
    print("THE HYPERVERSE — grounding type: which answer to the First Argument")
    print("=" * 100)
    dist = collections.Counter(v["grounding"] for v in out.values())
    print(f"\nsources: {len(out)}   hyperverses: {len(dist)}\n")
    for g, n in dist.most_common():
        gl = GROUNDINGS[g]["gloss"] if g in GROUNDINGS else UNGROUNDED_GLOSS
        print(f"   H:{g:<15}{n:>4}  {gl}")

    print("\nCOVERAGE: every source has a type — 'ungrounded' is an ANSWER, not a gap")
    print(f"   with a positive origin account : {len(out)-dist[UNGROUNDED]:>4}")
    print(f"   regress runs on unhalted       : {dist[UNGROUNDED]:>4}")

    print("\n" + "-" * 100)
    print("VERDICTS — the regress test, applied to cosmoi instead of claimants")
    print("-" * 100)
    for v in collections.Counter(x["verdict"] for x in out.values()).most_common():
        print(f"   {v[0]:<22}{v[1]:>4}")

    print("\n" + "-" * 100)
    print("SAMPLE")
    print("-" * 100)
    for s in ("Pantheon: Abrahamic", "Pantheon: Norse", "Pantheon: Hindu", "all Elder Scrolls",
              "Star Wars", "Warhammer 40,000", "all Final Fantasy", "Dune", "all Fallout",
              "the Lovecraftian mythos", "God of War", "Bleach"):
        if s in out:
            v = out[s]
            print(f"   {s[:26]:<28}{v['grounding']:<15}{v['verdict']:<20}conf {v['confidence']:.2f}")

    low = [(s, v) for s, v in out.items()
           if v["grounding"] != UNGROUNDED and v["confidence"] < 0.5]
    # NOTHING IS CAPPED HERE. This is a diagnostic: the whole point of the contested list is that
    # a person reads it and rules on each entry, and `low[:5]` printed the first five in dict
    # order -- not the five most contested, just the five that happened to be catalogued first --
    # while the count beside it said 15. `feats._show` already refuses to cap a diagnostic for
    # exactly this reason; one ruling, two habits, and this was the second one. The runners-up on
    # each line are uncapped too: the margin is the evidence for the flag, and printing 2 of 4 of
    # it is the same truncation this module was just corrected for. Sorted most-contested first
    # so the ordering carries meaning rather than scrape order. Order e2b3af23cb8a, 2026-08-25.
    print(f"\ncontested cosmogonies (two accounts run close; flagged, not forced): {len(low)}")
    for s, v in sorted(low, key=lambda x: x[1]["confidence"]):
        ru = ", ".join(f"{g}:{n}" for g, n in v["runners_up"])
        print(f"   {s[:28]:<30}{v['grounding']:<15}{v['confidence']:.2f}  vs {ru}")

    if args.write:
        p = os.path.join(HERE, "data", "GROUNDINGS.json")
        # ATOMIC: GROUNDINGS.json is shared. 2026-08-25 whole-tree sweep.
        #
        # GATED (order e7b6dcc8d630). `write_json` returns whether the rename LANDED and never
        # raises when it is denied -- which on Windows is the ordinary outcome while any reader
        # holds the target -- so discarding it printed "wrote {p}" for a file that had not
        # changed. Three modules read this file on their own clocks (`navtree`, `pipeline`,
        # `tiers`), and every one of them would then be reading the PREVIOUS pass's groundings
        # while the operator had been told the new ones were in place: a stale answer wearing
        # the shape of a fresh one. Reported as a non-zero exit, which is what `main()` already
        # uses to mean "this run did not do what it was asked".
        import silence
        if not silence.write_json(p, out, indent=2, ensure_ascii=False):
            silence.note("grounding.py:write-denied")
            print(f"\nWRITE DENIED -> {p}: the replace was refused, so the groundings above "
                  f"did NOT land and navtree/pipeline/tiers still read the previous pass. "
                  f"Rerun to retry.")
            return 1
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
