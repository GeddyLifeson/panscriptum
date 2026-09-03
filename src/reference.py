#!/usr/bin/env python3
"""
REFERENCE — hand-built Assays for three entities, to calibrate the automated pass against.

The local model, run unguarded, scored all eleven of Goku's axes at 9.9 and filed one of Zeno's
feats under his name. The guards in `magnitude.py` stop that, but guards only prove a sheet is
not fabricated; they cannot say whether a score of 4.5 should have been a 7. For that you need
sheets whose values are already known to be defensible, which is what this file holds.

Three entities, chosen because Charter Part Three publishes a value for each and does NOT print
the worksheet behind it (only Kenshiro's is printed in full). So each of these reconstructs a
worksheet that has to land inside a stated interval it was not fitted to:

    Goku    M7.62 +/- 0.41   Mastered Ultra Instinct, Tournament of Power
    Naruto  M4.31 +/- 0.30   Fourth Shinobi World War, Six Paths
    Luffy   M4.08 +/- 0.55   Gear Five / Awakened Nika

EPOCH IS THE FIRST DISCIPLINE, NOT A LABEL
------------------------------------------
The automated pass anchored Goku at M3 against a published M7.62, and the cause was epoch. The
miner surfaced Super Saiyan 3-era feats, which genuinely are M3-M4 evidence, and scored them
faithfully. Both readings are correct about different beings: the charter's doctrine that every
Assay is time-indexed is the whole reason 'Naruto, Six Paths' and 'Naruto, Hokage' are separate
measurements. An assay without a fixed epoch is not a loose assay, it is a measurement of an
unspecified subject.

WHAT EACH CITATION CARRIES
--------------------------
Every axis line names its evidence and where the evidence lives. Two provenance marks:

    [wiki]   the sentence is in the mined cache under data/feats, verbatim and checkable now.
             `magnitude.verify()` would accept it, and these lines double as ground truth for
             whether the gate is passing what it should.
    [canon]  the event is on-panel in the published work at the locus given. Not in the cache,
             because the miner did not surface that page.

Attestation is Transcribed for all three -- told, not seen, which is what reading a published
work is. Note that this makes my intervals TIGHTER than the charter's on Goku (0.41): the
charter's figure is set by Avar and Quill disagreeing, which is inter-hand dispersion rather
than attestation grade, and is a mechanism this file does not reproduce.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assay as A                                                       # noqa: E402
import silence

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


OUT = os.path.join(HERE, "data", "REFERENCE_ASSAYS.json")

# (score, evidence, locus, provenance)
REFERENCE = {
    "Goku": {
        "source": "Dragon Ball Z", "spine": "II.A.1", "host": "dragonball.fandom.com",
        "tier_key": "1.6.1",
        "lower_rungs": ["DRG", "7", "North", "Earth"],
        "styled": "SON GOKU",
        "aka": "Kakarot, of the Saiyan line of U-7",
        "class": "Person (Ascendant, Gyre-law)",
        "threads": ["II.A.1", "V.4", "VIII.9", "X.3 §G-114"],
        "worksheet_ref": "X.3 §G-114",
        "epoch": "Mastered Ultra Instinct, Tournament of Power",
        "charter": ("M7", 7.62, 0.41),
        "attestation": "Transcribed",
        "anchor": "M7",
        "presence": "He registers at the scale of a universe and is attended to at the scale "
                    "of twelve. Gods of Destruction from every universe watch him by name; the "
                    "Omni-King knows him personally; a tournament whose forfeit is the erasure "
                    "of universes is convened around contests he is in. Nothing here is about "
                    "how dangerous he is to them -- Zeno is in no danger from him whatsoever. "
                    "It is about how much of reality has him in it.",
        "axes": {
            "ruin": (2.5, "Exchanges with Jiren destabilise the World of Void, a space built to "
                          "contain the combat of gods", "DBS ToP, ep. 109-110", "canon"),
            "continuity": (3.5, "Endures Jiren's assault with no resurrection clause; Ultra "
                                "Instinct confers evasion, never durability",
                           "DBS ToP, ep. 110", "canon"),
            "celerity": (9.0, "Ultra Instinct acts without conscious mediation - the body answers "
                              "before thought reaches it", "Whis, DBS ep. 129", "canon"),
            "reach": (2.0, "As Super Saiyan, Goku was noted to have 3,000 kili - power to destroy "
                           "several planets", "Goku/Power and Abilities", "wiki"),
            "transgression": (4.5, "A divine technique the Gods of Destruction have not "
                                   "themselves mastered", "Whis, DBS ep. 110", "canon"),
            "sustain": (1.5, "The state cannot be held; it expends him and lapses within a "
                             "single engagement", "DBS ToP, ep. 110 and 130", "canon"),
            "vector": (6.0, "Instant Transmission locks to a ki signature and crosses "
                            "interstellar distance without transit", "DBZ Namek/Cell arcs",
                       "canon"),
            "volition": (9.0, "Goku then proceeded to single-handedly destroy the entire Red "
                              "Ribbon Army's headquarters and defeat all of its soldiers",
                         "Goku/Power and Abilities", "wiki"),
            "acumen": (2.0, "A combat savant with no planning record; his adaptations are "
                            "in-engagement, which the instrument scores as Volition",
                       "DBS, throughout", "canon"),
            "discernment": (6.5, "Ki-sensing across planetary distance; reads intent and reserve "
                                 "mid-exchange", "DBZ/DBS, throughout", "canon"),
            "suasion": (3.0, "Assembles Team Universe 7 and secures Frieza's cooperation on his "
                             "word alone", "DBS ToP recruitment, ep. 93-96", "canon"),
        },
    },
    "Naruto Uzumaki": {
        "source": "Naruto", "spine": "II.A.4", "host": "naruto.fandom.com",
        "tier_key": "4.2.0",
        "lower_rungs": ["NRT", "1", "?", "?"],
        "styled": "NARUTO UZUMAKI",
        "aka": "Seventh Hokage; jinchuriki of Kurama",
        "class": "Person (Sealed-vessel, Chakra-law)",
        "threads": ["II.A.4", "VII.2", "X.3 §N-041"],
        "worksheet_ref": "X.3 §N-041",
        "epoch": "Fourth Shinobi World War, Six Paths Sage Mode",
        "charter": ("M4", 4.31, 0.30),
        "attestation": "Transcribed",
        "anchor": "M4",
        "presence": "He registers across one world and the dimension folded above it. Every "
                    "hidden village, an allied army of five nations, and the moon-dimension "
                    "Kaguya rules are all inside the extent within which he is a factor; "
                    "outside it, nothing has heard of him.",
        "axes": {
            "ruin": (1.5, "Tailed Beast Bomb output is continental at its ceiling and never "
                          "approaches the band floor", "Naruto ch. 671-690", "canon"),
            "continuity": (5.5, "Kurama's reserves sustain regeneration through wounds that end "
                                "peers; survives the beast's extraction",
                           "Naruto ch. 662-693", "canon"),
            "celerity": (7.5, "In Six Paths Sage Mode he and Sasuke answer Kaguya's dimensional "
                              "displacement in time to act", "Naruto ch. 674-681", "canon"),
            "reach": (5.0, "Distributes Six Paths chakra to the entire Allied Shinobi Force "
                           "across a battlefield", "Naruto ch. 649", "canon"),
            "transgression": (7.0, "Truth-Seeking Orbs erase matter outright and ignore ninjutsu; "
                                   "the sealing of a progenitor deity is a Transgression-class "
                                   "act, not a Ruin one", "Naruto ch. 690", "canon"),
            "sustain": (6.0, "Kurama's reserves are vast but Six Paths chakra is lent and lapses "
                             "on a clock", "Naruto ch. 692-693", "canon"),
            "vector": (3.5, "Flight in Six Paths mode and Flying Thunder God by another's mark; "
                            "no independent cross-rung travel", "Naruto ch. 674", "canon"),
            "volition": (7.0, "Improvisational to a fault, with shadow-clone training compressing "
                              "years of practice into days", "Naruto ch. 511-518", "canon"),
            "acumen": (3.5, "Academically the worst of his cohort; his advantage is tactical "
                            "improvisation, which the instrument scores as Volition",
                       "Naruto, throughout", "canon"),
            "discernment": (7.0, "Sage Mode sensing plus Kurama's reading of negative emotion, "
                                 "at battlefield range", "Naruto ch. 566", "canon"),
            "suasion": (9.5, "He converts his enemies by speech and standing alone - Nagato, "
                             "Obito, Gaara - which is precisely the axis's definition: choices "
                             "set by voice, with compulsion excluded",
                        "Naruto ch. 446-449, 636-638", "canon"),
        },
    },
    "Monkey D. Luffy": {
        "source": "One Piece", "spine": "II.A.3", "host": "onepiece.fandom.com",
        "tier_key": "1.2.5",
        "lower_rungs": ["OPC", "1", "?", "?"],
        "styled": "MONKEY D. LUFFY",
        "aka": "Straw Hat; bearer of the Hito Hito no Mi, Model: Nika",
        "class": "Person (Awakened-fruit, Toon-law)",
        "threads": ["II.A.3", "VII.5", "X.3 §L-088"],
        "worksheet_ref": "X.3 §L-088",
        "epoch": "Gear Five / Awakened Nika",
        "charter": ("M4", 4.08, 0.55),
        "attestation": "Transcribed",
        "anchor": "M4",
        "presence": "He registers across one world's seas and its government. A bounty read "
                    "in every port, a nation's liberation turning on him, and an order that "
                    "names him its enemy are all measures of extent, not of threat -- the same "
                    "world, more thoroughly occupied, is what separates him from a rookie.",
        "axes": {
            "ruin": (0.5, "Bajrang Gun is island-scale at its ceiling, orders below the band "
                          "floor", "One Piece ch. 1044-1049", "canon"),
            "continuity": (7.0, "Gear Five renders injury cartoonish rather than survivable, and "
                                "the awakening itself followed a death",
                           "One Piece ch. 1044", "canon"),
            "celerity": (6.5, "Trades at Kaidou's tempo and answers attacks timed to lightning",
                         "One Piece ch. 1045-1049", "canon"),
            "reach": (4.0, "On Fish-Man Island, the Sea Kings believed he would have completely "
                           "destroyed the gigantic ship Noah before it would have landed",
                      "Monkey D. Luffy/Abilities and Powers", "wiki"),
            "transgression": (8.5, "Gear Five imposes cartoon logic on the environment - ground "
                                   "turned rubber, attacks reflected, causality declined. The "
                                   "charter names toon-force under this axis explicitly",
                              "One Piece ch. 1044-1046", "canon"),
            "sustain": (1.0, "The form shortens his life and drops him to helplessness on lapse",
                        "One Piece ch. 1046", "canon"),
            "vector": (1.5, "Self-propulsion only; no travel above the planetary rung",
                       "One Piece, throughout", "canon"),
            "volition": (7.5, "Advanced Conqueror's Haki and an improvisational style that "
                              "invents its own techniques mid-fight",
                         "One Piece ch. 1010-1049", "canon"),
            "acumen": (0.5, "No planning record whatever; explicitly the least analytical member "
                            "of his own crew", "One Piece, throughout", "canon"),
            "discernment": (7.0, "Future Sight Observation Haki resolves seconds ahead of the "
                                 "present", "One Piece ch. 1010-1015", "canon"),
            "suasion": (7.0, "Binds a crew and moves whole populations by example. Conqueror's "
                             "Haki is deliberately NOT counted here - imposed will is "
                             "compulsion, which the charter files under Transgression",
                        "One Piece, Alabasta through Wano", "canon"),
        },
    },
}


def compute(name, rec):
    scores = {ax: v[0] for ax, v in rec["axes"].items()}
    sheet = {ax: f"{v[1]}  <{v[2]}>  [{v[3]}]" for ax, v in rec["axes"].items()}
    return A.assay(rec["anchor"], scores, attestation=rec["attestation"],
                   epoch=rec["epoch"], worksheet=sheet)


# The charter's canonical Shelfmark is EIGHT rungs:
#     Omega > H > X > Mt. > Mv. > U- > G. > P.
# The navtree shelves SOURCES, which reaches only as far as the metaverse; the four rungs below
# that are per-ENTITY facts and have to come from the fiction. Where the fiction does not name a
# rung it stays `?`, per the charter's own rule that unknown rungs are marked and never guessed.
# Naruto's world has no named galaxy and One Piece's planet has no name in the text, so those
# rungs are honestly blank rather than invented -- which is the rule doing its job, not a gap.
RUNGS = ("H.", "X.", "Mt.", "Mv.", "U-", "G.", "P.")


def shelfmark(rec):
    try:
        nav = json.load(open(os.path.join(HERE, "data", "NAVTREE.json"), encoding="utf-8"))
        parts = rec["tier_key"].split(".")
        upper = []
        for i in range(len(parts)):
            k = ".".join(parts[:i + 1])
            upper.append(nav["nodes"].get(k, {}).get("name", k))
    except Exception:
        # Content label, not a line number: this was tagged "reference.py:232", which is
        # `def shelfmark(rec):` itself, not the NAVTREE lookup that actually failed. A stale
        # number costs a grep every time someone diagnoses it (see wiki_source.py's own
        # converted sites for the same fix).
        silence.note("reference.py:shelfmark-navtree")
        upper = ["?", "?", "?"]
    lower = list(rec.get("lower_rungs", ["?", "?", "?", "?"]))
    # RUNGS names exactly 7 cosmological rungs (H, X, Mt, Mv, U-, G, P). This assumed upper is
    # always 3 long and lower always 4 -- true for the three hardcoded entries below, but a
    # future entry whose tier_key or lower_rungs comes out a different length would either
    # mislabel a rung (the hardcoded "3" here) or raise an uncaught IndexError past the end of
    # RUNGS. Clamp to what RUNGS can actually hold and say so, rather than crash a citation
    # render on unfamiliar data.
    if len(upper) + len(lower) > len(RUNGS):
        silence.note("reference.py:shelfmark-shape")
        lower = lower[:max(0, len(RUNGS) - len(upper))]
        upper = upper[:len(RUNGS)]
    marks = [f"{RUNGS[i]}{v}" for i, v in enumerate(upper)]
    marks += [f"{RUNGS[len(upper) + i]}{v}" for i, v in enumerate(lower)]
    return "Ω › " + " › ".join(marks)


def citation(name, rec, res):
    """The charter's canonical formal-citation block (Part Three, The Two Registers).

    Part Three's obligations here are absolute, the way units and error bars are absolute in
    physics: an Assay never appears without its confidence interval, its epoch tag and a
    worksheet pointer, because "a value with no derivation reference is, formally, not a
    measurement but a rumour." All three print below, or the card is malformed.
    """
    L = []
    L.append("⟦FORMAL CITATION⟧")
    L.append(f"{rec['styled']}  ({rec['aka']})")
    L.append(f"Shelfmark:   {shelfmark(rec)}")
    L.append(f"Assay:       𝔄 = {res['magnitude']} + {res['decimal']:.2f} "
             f"⟨w-composite; worksheet {rec['worksheet_ref']}⟩ ; "
             f"CI ± {res['interval']:.2f}")
    L.append(f"Epoch:       {rec['epoch']}")
    L.append(f"Attestation: {rec['attestation']}; single-hand, unsigned "
             f"(reference reconstruction, not a filed reading)")
    L.append(f"Class:       {rec['class']}   •   Threads: "
             + " · ".join(rec["threads"]))
    L.append(f"Vernacular:  “{_vernacular(res)}”")
    return chr(10).join(L)


def _vernacular(res):
    """Part Three's shelf-talk. Decimals are never spoken: a band divides into thirds."""
    d = res["decimal"]
    third = "shallow" if d <= 0.32 else ("solid" if d <= 0.66 else "deep")
    word = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
            6: "six", 7: "seven", 8: "eight", 9: "nine",
            10: "ten"}[A.LADDER.index(res["magnitude"])]
    tail = " — and argued" if res["interval"] >= 0.40 else ""
    edge = ", at the ceiling and on watch" if res.get("promotion_watch") else ""
    return f"a {third} {word}{edge}{tail}"


def card(name, rec, res):
    band, val, ci = rec["charter"]
    delta = abs(res["decimal"] + A.LADDER.index(res["magnitude"]) - val)
    inside = delta <= ci
    L = ["=" * 92, citation(name, rec, res), "=" * 92,
         f"  Anchor  {rec['anchor']} — presence: {rec['presence']}", "",
         f"  {'MEASURE':<15}{'SCORE':>6}{'w':>8}{'w.s':>8}   WORKSHEET LINE",
         "  " + "-" * 88]
    tot = 0.0
    for ax in A.WEIGHTS:
        sc, ev, locus, prov = rec["axes"][ax]
        w = A.WEIGHTS[ax]
        tot += w * sc
        L.append(f"  {ax:<15}{sc:>6.1f}{w:>8.4f}{w * sc:>8.3f}   [{prov}] {ev}")
        L.append(f"  {'':<37}   ⟨{locus}⟩")
    L.append("  " + "-" * 88)
    L.append(f"  {'':<29}{'sum':>8}{tot:>8.3f}     ->  {res['magnitude']} + {tot:.3f}/10 "
             f"= {res['moth_number']}")
    L.append("")
    L.append(f"  coverage {res['axis_coverage']}   axes scored {len(res['axes_scored'])}/11"
             f"   promotion watch: {res['promotion_watch']}")
    L.append(f"  CHARTER  {band}.{round((val % 1) * 100):02d} ± {ci:.2f}"
             f"   delta {delta:.2f}   "
             f"{'INSIDE the published interval' if inside else 'OUTSIDE - investigate'}")
    return chr(10).join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", action="store_true",
                    help="diff these against whatever the automated pass produced")
    a = ap.parse_args()

    # `outside` carries the SAME per-entity delta `card()` already prints, kept so the verdict
    # below can name which reconstruction drifted instead of only counting it (order
    # d049dbbfed6e).
    out, inside, outside = {}, 0, []
    for name, rec in REFERENCE.items():
        res = compute(name, rec)
        out[name] = {"reference": res, "charter": rec["charter"], "epoch": rec["epoch"],
                     "anchor": rec["anchor"], "spine": rec["spine"],
                     "shelfmark": shelfmark(rec),
                     "worksheet": {ax: {"score": v[0], "evidence": v[1], "locus": v[2],
                                        "provenance": v[3]} for ax, v in rec["axes"].items()}}
        val = res["decimal"] + A.LADDER.index(res["magnitude"])
        delta = abs(val - rec["charter"][1])
        if delta <= rec["charter"][2]:
            inside += 1
        else:
            outside.append((name, delta, rec["charter"][2]))
        print(card(name, rec, res))
        print()

    # ATOMIC: standards.py and zfighters.py both read REFERENCE_ASSAYS.json. 2026-08-25.
    #
    # GATED, the same way `zfighters.main` is for the file it hands `pantheon.py`. This file is
    # the hand-computed BENCHMARK the automated assay is judged against, so a stale copy is not
    # a slower answer, it is a wrong ruler: `standards.py` and `zfighters.py` read it, and
    # `--compare` below differences the automated pass against `out` in memory while those two
    # go on reading whatever survived on disk. `write_json` returns whether the rename LANDED
    # and this dropped it, so a denied replace still printed "-> OUT" under a file that had not
    # changed. Reported, and the exit status carries it, because the one thing that must not
    # happen is a benchmark refresh that reports success and did not occur.
    import silence
    landed = silence.write_json(OUT, out, indent=1, ensure_ascii=False)
    if landed:
        print(f"{inside}/{len(REFERENCE)} reconstructions land inside the charter's published "
              f"interval  ->  {OUT}")
    else:
        silence.note("reference.py:main-write-denied")
        print(f"{inside}/{len(REFERENCE)} reconstructions land inside the charter's published "
              f"interval")
        print(f"WRITE DENIED -> {OUT}: replace refused; the reconstructions above did NOT land "
              f"and the file standards.py and zfighters.py read is the previous run's. Rerun "
              f"to retry.", file=sys.stderr)

    # THE CALIBRATION IS PART OF THE VERDICT NOW (order d049dbbfed6e). Both returns below used
    # to be `0 if landed else 1`, i.e. the exit code answered "did the OUTPUT FILE get written",
    # and never "did the calibration this module exists to perform actually hold". `inside` was
    # computed, printed, and dropped. That mattered because rc is the only channel out:
    # `allsweep.py`'s "calibration assays" row runs this file specifically to catch a drifted
    # benchmark, and a drifted benchmark exited 0. Reproduced 2026-08-29 by moving one charter
    # value: '2/3 reconstructions land inside', delta 5.44, rc 0. A check that cannot fail looks
    # exactly like a check that passed.
    #
    # THE TWO FAULTS STAY DISTINGUISHABLE, in the printout and in the words, because they have
    # different remedies: WRITE DENIED is a locked or held file and the answer is to rerun;
    # CALIBRATION OUTSIDE is the hand-built worksheets no longer reproducing the charter's
    # published interval and the answer is to re-derive, never to rerun. They share ONE exit
    # code deliberately -- both are RC_BROKEN-class faults for allsweep, not findings -- so no
    # second VERIFIERS row is warranted; see the note beside that row in allsweep.py.
    calibrated = not outside
    if not calibrated:
        for _name, _delta, _ci in outside:
            print(f"CALIBRATION OUTSIDE -> {_name}: delta {_delta:.2f} against the charter's "
                  f"published +/- {_ci:.2f}. The reconstruction no longer lands inside an "
                  f"interval it was not fitted to, which is the one thing this module exists "
                  f"to demonstrate.", file=sys.stderr)
        print(f"CALIBRATION OUTSIDE: {len(outside)} of {len(REFERENCE)} reconstructions miss "
              f"the charter's published interval.", file=sys.stderr)

    if a.compare:
        path = os.path.join(HERE, "data", "ASSAYS.json")
        if not os.path.exists(path):
            print("\nno ASSAYS.json yet - run the automated pass, then compare")
            return 0 if (landed and calibrated) else 1
        auto = json.load(open(path, encoding="utf-8"))
        # ASSAYS.json is keyed `host|entity` -- 'dragonball.fandom.com|Goku', never a bare
        # 'Goku'. This looked entities up by bare name, so every row fell into the fallback
        # branch and this report has printed nothing but 'band only' for as long as the key has
        # had that shape. Each row also STATES its own host and entity, so index on those rather
        # than re-spelling the separator here; the key split is only a fallback for a row that
        # somehow carries neither field.
        by_pair = {}
        for k, row in (auto or {}).items():
            if not isinstance(row, dict):
                continue
            host, _, ent = str(k).partition("|")
            by_pair[(row.get("host") or host, row.get("entity") or ent or k)] = row

        print(f"\n{'entity':<20}{'reference':>12}{'automated':>12}{'delta':>8}"
              "  axes scored by the automated pass")
        for name, rec in REFERENCE.items():
            row = by_pair.get((rec["host"], name))
            if row is None:
                print(f"{name:<20}{'--':>12}{'no row':>12}"
                      f"{'':>8}  not in ASSAYS.json under {rec['host']}")
                continue
            got = row.get("result")
            if not got or got.get("decimal") is None:
                status = row.get("status") or "no result"
                print(f"{name:<20}{'--':>12}{status.lower():>12}"
                      # UNCUT (Hard Rule 0, sweep42-batch03). This is the diagnostic explaining
                      # why a reference row has no result; cut at 44 characters it stopped
                      # roughly where the actual cause begins. estate.py's _brief() helper
                      # exists in this codebase for precisely this shape.
                      f"{'':>8}  {str(row.get('reason') or '')}")
                continue
            r = out[name]["reference"]
            rv = r["decimal"] + A.LADDER.index(r["magnitude"])
            gv = got["decimal"] + A.LADDER.index(got["magnitude"])
            scored = got.get("axes_scored") or []
            # band.decimal, as `card()` prints the charter's -- slicing `moth_number` cut it
            # mid-figure and printed 'M7.44 ±'.
            fmt = "%s.%02d"
            print(f"{name:<20}{fmt % (r['magnitude'], round(r['decimal'] * 100)):>12}"
                  f"{fmt % (got['magnitude'], round(got['decimal'] * 100)):>12}"
                  f"{abs(rv - gv):>8.2f}  {len(scored)}/11: "
                  f"{', '.join(scored) if scored else 'none'}")

            # PER-AXIS SCORES, WHERE THE ROW ACTUALLY CARRIES THEM (order b03f2ab9951a,
            # assay.py, added 2026-08-26). A row's `scores` key is ABSENT, not zero, for every
            # automated assay computed before that change -- reading a missing key as "scored
            # zero" would fabricate a finding out of a schema change, so a missing key prints
            # as "not recorded" and nothing is differenced against it.
            auto_scores = got.get("scores")
            if auto_scores is None:
                print(f"{'':<20}  axis scores: not recorded on this row (pre-dates "
                      f"b03f2ab9951a)")
            else:
                ws = out[name]["worksheet"]
                diffs = []
                for ax in scored:
                    if ax not in auto_scores or ax not in ws:
                        continue
                    ref_s = ws[ax]["score"]
                    got_s = auto_scores[ax]
                    if isinstance(ref_s, (int, float)) and isinstance(got_s, (int, float)):
                        diffs.append(f"{ax} {got_s:.1f} vs {ref_s:.1f} "
                                     f"(|{abs(got_s - ref_s):.1f}|)")
                print(f"{'':<20}  axis scores: {'; '.join(diffs) if diffs else 'none comparable'}")

        # `ASSAYS.json` rows now carry a `scores` field alongside `axes_scored` (added
        # 2026-08-26, order b03f2ab9951a) -- the axis diff above uses it directly when it is
        # present. Rows computed before that change simply lack the key and are reported as
        # "not recorded", never as a zero score, so this column's absence on older rows is not
        # this tool's limitation, it is that row's age.
        print("\naxes: 'axis scores' above differences this file's worksheet against the "
              "automated pass's\npersisted per-axis scores (b03f2ab9951a) where both sides "
              "have a numeric reading for the\nsame axis; rows predating that field report "
              "'not recorded' instead of a fabricated zero.")
    return 0 if (landed and calibrated) else 1


if __name__ == "__main__":
    sys.exit(main())
