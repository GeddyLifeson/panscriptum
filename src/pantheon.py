#!/usr/bin/env python3
"""PANTHEON -- the divine tier of Universes 6 and 7, hand-built under the presence thesis.

WHY THESE SIT ABOVE THE Z FIGHTERS AND WHY TWO OF THEM LEAVE THE BAND ENTIRELY
-----------------------------------------------------------------------------
The Z Fighters top out at M7 because a universe is the largest thing any of them is a factor in.
Three entities here are not bounded that way, and the record says so in a single line found on
Vados's own page:

    "the losing Universes in the Tournament of Power will be obliterated and
     ONLY THE ANGELS WILL BE PRESERVED"

An angel's existence is not contingent on any universe. Whis and Vados persist through the
erasure of the universes they are attached to, which means they are not present AT universal
scale -- they are present at the scale that CONTAINS universes. The charter's band table calls
that M8, "whole multiverses". Zeno joins them from the other direction: he has erased thirteen
universes and his counterpart twenty-five, and the twelve that remain are the twelve he allowed
to remain.

This is the single call in the set most worth arguing with. The counter-case is that Whis's beat
is one universe, that he is Universe 7's angel and travels elsewhere as a visitor, and that
survival of an erasure is a property rather than an extent. I have gone the other way because
presence asks what reality a thing occupies rather than what job it holds, and a being that
outlives the deletion of its universe is occupying something larger than that universe.

BEERUS IS THE CLEAREST M7 IN THE LIBRARY
----------------------------------------
Not for his output, though that is stated at universal ceiling. For pervasion. His own page
records that Universe 7's mortal level is low BECAUSE OF HIM -- "Beerus never gives civilizations
and societies a chance to properly grow". The developmental state of every civilisation in a
universe is a fact about Beerus. Nothing in the Z Fighter roster pervades its universe that way;
they act in theirs, he is a property of his.
"""
import argparse
import json
import os
import sys
import textwrap

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assay as A                                                       # noqa: E402
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

OUT = os.path.join(HERE, "data", "PANTHEON.json")

GODS = {
 "Zeno": dict(
  anchor="M8", epoch="Tournament of Power, both Omni-Kings present",
  presence="The multiverse is the shape he has left it. 'At some point in time, Zeno destroyed 6 "
           "of the then-existing 18 universes'; 'as of the Tournament of Power, Zeno has now "
           "wiped out 13 total Universes, while Future Zeno has wiped out 25'. The twelve "
           "universes that exist are the twelve he has not erased, which makes their continued "
           "existence a standing fact about him rather than about them.",
  axes=dict(
   ruin=(9.5, "Thirteen universes erased, and six of the original eighteen 'after a bout of "
              "anger'", "wiki"),
   continuity=(9.5, "Nothing in the record threatens him; the Core Area Warriors' entire plot is "
                    "built around the problem that he cannot be reached", "wiki"),
   celerity=(7.5, "Erasure is instantaneous, but he is never depicted contesting tempo with "
                  "anything", "canon"),
   reach=(9.5, "'His ability to be able to destroy entire universes on a whim' -- and he erases "
               "Universe 9 entire, 'with the exception of Mohito'", "wiki"),
   transgression=(9.5, "Erasure is not destruction: no technique, no expenditure, no mechanism "
                       "the rulebook can name. He declares a universe out of existence", "wiki"),
   sustain=(9.5, "No state to hold and no cost to holding it", "canon"),
   vector=(6.5, "Goes where he wishes, but is carried and attended everywhere he goes", "wiki"),
   volition=(8.5, "Absolute and never opposed -- and moved by Goku's friendship, which is the "
                  "one lever the record shows working on him", "wiki"),
   acumen=(1.5, "'Incapable of understanding the horrible action of erasing trillions of lives, "
                "since he and his future counterpart wonder why everyone in the Tournament of "
                "Power stops fighting after witnessing an entire universe erased'. The lowest "
                "acumen against the highest power in the library", "wiki"),
   discernment=(3.0, "Watches everything and comprehends almost none of it", "wiki"),
   suasion=(9.0, "Twelve universes reorganise their entire mortal development around what he "
                 "might think. The Grand Minister exists to attend him", "wiki"))),

 "Vados": dict(
  anchor="M8", epoch="Tournament of Power, angel of Universe 6",
  presence="An angel, and therefore not contained by the universe she serves. 'After the Grand "
           "Minister announces that the losing Universes in the Tournament of Power will be "
           "obliterated and that only the Angels will be preserved, Vados simply closes her eyes "
           "and silently smiles.' She watched Universe 6 face deletion knowing it did not apply "
           "to her.",
  axes=dict(
   ruin=(7.0, "Destroys a planet on Champa's order without ceremony", "wiki"),
   continuity=(9.5, "'Only the Angels will be preserved' -- she survives the erasure of her own "
                    "universe as a matter of standing rule", "wiki"),
   celerity=(8.5, "Steps between two Gods of Destruction mid-clash and stops both", "wiki"),
   reach=(8.0, "Creates an arena, stands, food, portraits and a breathable atmosphere on a "
               "barren world -- 'which would require manipulation' at planetary scale", "wiki"),
   transgression=(8.5, "Matter manipulation as an ordinary courtesy: she makes an atmosphere "
                       "because the guests need one", "wiki"),
   sustain=(9.0, "No transformation, no exertion, no clock", "canon"),
   vector=(8.5, "Angel travel between universes under her own power, carrying passengers",
           "canon"),
   volition=(6.0, "Bound by angel law to indifference, and she keeps to it", "wiki"),
   acumen=(8.0, "'She pointed out that Zeno was already going to erase all of them with their "
                "universes completely, but Goku's closeness with Zeno was able to convince the "
                "Omni-King to give the underdeveloped universes a chance' -- she reads the "
                "political structure correctly when the Gods of Destruction do not", "wiki"),
   discernment=(8.5, "Sees the tournament for the reprieve it is while everyone else sees a "
                     "death sentence", "wiki"),
   suasion=(6.5, "'The only Angel of the other universes who has any respect for Goku', and her "
                 "read is the one that proves correct", "wiki"))),

 "Whis": dict(
  anchor="M8", epoch="Universe 7's angel, Battle of Gods onward",
  presence="The strongest being in Universe 7 by the explicit statement of the being who was "
           "previously the strongest -- and, as an angel, not bounded by that universe at all. "
           "'Only the Angels will be preserved.' He is Beerus's attendant, teacher and "
           "restraint, the Grand Minister's son, and the reason two Gods of Destruction have "
           "never finished a fight.",
  axes=dict(
   ruin=(7.5, "Never fights to destroy; his one recorded application of force is a neck chop "
              "that ends a fight between two Gods of Destruction", "wiki"),
   continuity=(9.5, "Angels are preserved when their universes are obliterated -- his existence "
                    "does not depend on the universe he serves", "wiki"),
   celerity=(9.0, "Intercepts Beerus and Champa mid-exchange, an exchange whose stray energy is "
                  "consuming two universes", "wiki"),
   reach=(8.0, "'Politely told the Z Fighters that the entire Solar System will be destroyed in "
               "an instant in honorific register while calmly eating a cake'", "wiki"),
   transgression=(9.0, "Temporal Do-Over rewinds three minutes of the universe outright -- he "
                       "un-happens events, which is the axis at its purest", "canon"),
   sustain=(9.0, "No state to hold; the record shows no exertion from him at any point", "canon"),
   vector=(8.5, "Carries Beerus and passengers between universes under his own power", "canon"),
   volition=(6.5, "Angel law requires indifference, and he mostly keeps it -- 'Whis felt ashamed "
                  "about the chaos and destruction Moro was causing across Universe 7... despite "
                  "having to be indifferent according to angel laws'", "wiki"),
   acumen=(8.5, "Teaches both Saiyans, manages a God of Destruction's temper as a standing duty, "
                "and is never once surprised", "canon"),
   discernment=(9.0, "Describes Beerus's ceiling accurately, reads Moro's spread across the "
                     "universe, and knows what Goku will do before Goku does", "wiki"),
   suasion=(7.5, "Manages Beerus by cake and by tone -- the only being who redirects a God of "
                 "Destruction without force", "canon"))),

 "Beerus": dict(
  anchor="M7", epoch="God of Destruction of Universe 7, Super onward",
  presence="THE MOST PERVASIVE ENTITY IN THE ROSTER. Not for output -- for what his existence "
           "does to a universe passively. 'This is one reason why his Universe has such a low "
           "mortal level as Beerus never gives civilizations and societies a chance to properly "
           "grow.' The developmental state of every civilisation in Universe 7 is a fact about "
           "Beerus. The Z Fighters act in their universe; he is a property of his.",
  axes=dict(
   ruin=(9.0, "'Strong enough to destroy entire solar systems with ease'; 'enough power to "
              "destroy the entire universe if he was provoked enough'; 'could destroy the "
              "Supreme Kai's realm, which is 1/10th the size of Universe 7'", "wiki"),
   continuity=(4.5, "A documented kill-switch: his life is bound to the Supreme Kai's, and the "
                    "lowest continuity of any god here by a wide margin", "canon"),
   celerity=(8.5, "Trades with Champa across a universe; mortals cannot perceive the exchange",
             "wiki"),
   reach=(8.5, "'Their destructive energy begins to destroy both the Sixth and Seventh Universe, "
               "requiring Whis and Vados to step in' -- his stray output reaches across two "
               "universes", "wiki"),
   transgression=(9.0, "Hakai erases rather than destroys; and 'Toei went on to state Beerus "
                       "killing Zamasu split the main timeline in half'", "wiki"),
   sustain=(6.5, "Fights well below his ceiling and tires at it; sleeps for decades between "
                 "engagements", "canon"),
   vector=(5.0, "Travels between universes only as Whis's passenger -- no independent passage",
           "canon"),
   volition=(7.0, "Capricious and absolute within his remit, but visibly restrained now 'because "
                  "of Zeno'", "wiki"),
   acumen=(6.5, "'Beerus told Frieza to destroy Planet Vegeta, as he felt that destroying it "
                "himself was too much of a bother' -- and it worked", "wiki"),
   discernment=(7.5, "Senses across his universe from sleep; identifies the Super Saiyan God "
                     "prophecy from a dream", "canon"),
   suasion=(8.5, "'Beerus himself was partially responsible' for the destruction of Planet "
                 "Vegeta by a word to Frieza. Gods, Kais and tyrants alike arrange themselves "
                 "around his mood", "wiki"))),

 "Champa": dict(
  anchor="M7", epoch="God of Destruction of Universe 6, Tournament of Power",
  presence="Universe 6 entire, and a share of Universe 7 whenever he loses his temper in it. "
           "'The two continue to fight throughout the universe in a rampage, destroying multiple "
           "planets'; 'Champa and Beerus are eventually stopped by their attendants for nearly "
           "destroying a universe.' He is his universe's destruction principle, and a worse one "
           "than his brother.",
  axes=dict(
   ruin=(8.5, "'Dodges a kick from Champa which destroys the planet, instantly killing its "
              "bird-like inhabitants' -- a planet destroyed by a missed kick", "wiki"),
   continuity=(4.0, "Bound to his own Supreme Kai as Beerus is, and erased outright with "
                    "Universe 6: 'Champa comes to terms with his fate and calls out to Beerus, "
                    "playfully making one final rude face at his brother before being wiped from "
                    "existence'", "wiki"),
   celerity=(8.0, "Trades with Beerus across a universe, and is consistently the slower of the "
                  "two", "wiki"),
   reach=(8.0, "'Their destructive energy begins to destroy both the Sixth and Seventh "
               "Universe'", "wiki"),
   transgression=(8.5, "Hakai, the same erasure his brother wields", "canon"),
   sustain=(5.5, "Tires faster than Beerus and is out of condition by the record's own "
                 "description", "canon"),
   vector=(5.0, "Vados carries him", "wiki"),
   volition=(5.5, "Rules by tantrum -- 'Champa angrily prepares to wipe out his team for their "
                  "failure and disobedience' and is stopped by a warning about Zeno", "wiki"),
   acumen=(4.0, "Loses the wager, the tournament and his temper in sequence; needs Vados to "
                "explain his own situation to him", "wiki"),
   discernment=(5.5, "'Left shocked and confused when Frieza knocks Frost out' -- he does not "
                     "read his own fighters correctly", "wiki"),
   suasion=(5.0, "Obeyed by fear inside Universe 6 and by nobody outside it", "wiki"))),

 "Grand Minister": dict(
  anchor="M8", epoch="Tournament of Power, Zeno's attendant",
  presence="The administrator of the multiverse. He announces the terms on which universes live "
           "or are obliterated, he is the father of the angels, and he stands at the Omni-King's "
           "shoulder. 'When Android 17 wished for all the erased universes to be restored, the "
           "Grand Minister was not only unsurprised but even showed satisfaction' -- he had "
           "arranged for exactly that outcome to be reachable.",
  axes=dict(
   ruin=(8.0, "Never fights on record; his rank among angels implies the ceiling and the record "
              "never tests it", "canon"),
   continuity=(9.5, "An angel, and the first of them -- preserved by the same rule that spares "
                    "his children", "canon"),
   celerity=(9.0, "Attends Zeno instantly wherever Zeno is", "canon"),
   reach=(9.0, "Announces the tournament's terms to all twelve universes at once", "wiki"),
   transgression=(8.5, "Sets the rules the tournament runs on, including which beings may be "
                       "erased and which preserved", "wiki"),
   sustain=(9.5, "No state, no cost", "canon"),
   vector=(9.0, "Moves between universes and to Zeno's palace at will", "canon"),
   volition=(7.0, "Serves absolutely and appears to want nothing for himself", "canon"),
   acumen=(9.5, "'Not only unsurprised but even showed satisfaction' at the restoration wish -- "
                "he engineered a tournament whose prize could undo its own cost, and the "
                "manga states 'both of them intended the tournament prize' from the start. The "
                "highest acumen in the library", "wiki"),
   discernment=(9.0, "Reads Zeno, the angels and twelve universes' worth of politics correctly "
                     "and continuously", "wiki"),
   suasion=(8.5, "Speaks and twelve universes rearrange themselves; the Gods of Destruction "
                 "listen to him in silence", "wiki"))),
}


def compute(roster):
    out = {}
    for name, rec in roster.items():
        scores = {ax: v[0] for ax, v in rec["axes"].items()}
        sheet = {ax: "[" + v[2] + "] " + v[1] for ax, v in rec["axes"].items()}
        res = A.assay(rec["anchor"], scores, attestation="Transcribed",
                      epoch=rec["epoch"], worksheet=sheet)
        out[name] = {"assay": res, "anchor": rec["anchor"], "epoch": rec["epoch"],
                     "presence": rec["presence"],
                     "axes": {k: {"score": v[0], "cited": v[1], "provenance": v[2]}
                              for k, v in rec["axes"].items()}}
    return out


def value(rec):
    r = rec["assay"]
    return A.LADDER.index(r["magnitude"]) + r["decimal"]


def main():
    ap = argparse.ArgumentParser(description="the divine tier, and the whole ladder with it")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--gods-only", action="store_true")
    a = ap.parse_args()

    out = compute(GODS)
    # ATOMIC -- the m100 tail, 2026-08-25.
    # GATED, like scope.py's build(): write_json returns whether the rename LANDED, and the
    # unconditional "-> OUT" line below used to discard that verdict -- a denied replace still
    # pointed a reader at a file that, this round, did not actually receive this run's data.
    write_ok = silence.write_json(OUT, out, indent=1, ensure_ascii=False)

    combined = dict(out)
    if not a.gods_only:
        for path in ("Z_FIGHTERS.json",):
            try:
                with open(os.path.join(HERE, "data", path), encoding="utf-8") as f:
                    for k, v in json.load(f).items():
                        combined.setdefault(k, v)
            except Exception:
                silence.note("pantheon.py:merge")

    rank = sorted(combined.items(), key=lambda kv: -value(kv[1]))
    print("=" * 88)
    print("DRAGON BALL, UNIVERSES 6 AND 7 -- BY MAGNITUDE (presence thesis)")
    print("=" * 88)
    band = None
    for n, rec in rank:
        b = rec["assay"]["magnitude"]
        if b != band:
            band = b
            # Charter Part Two's magnitude table (00_MASTER_CHARTER.md), "Can threaten..." column.
            # M2-M4 and M7 are the bands Z_FIGHTERS.json actually populates today, which is why
            # M1/M5/M6 went unnoticed missing here -- add a band there and this must not go blank.
            label = {"M1": "a city or nation", "M2": "a continent", "M3": "a planet",
                     "M4": "a stellar system", "M5": "star clusters", "M6": "a galaxy",
                     "M7": "a universe", "M8": "multiverses"}.get(b, "(no label on file for %s)" % b)
            print("  --- %s  %-16s %s" % (b, label, "-" * 44))
        epoch = rec.get("epoch") or rec["assay"].get("epoch", "")
        # `epoch[:40]` cut the last column of the ranked table for no gain: it is the LAST
        # column, so nothing after it needs aligning and a long epoch costs only line length.
        # Order 9d24c8a5febf, same rule as the citation cap below.
        print("  %-17s %-16s %s" % (n, rec["assay"]["moth_number"], epoch))

    if a.full:
        for n, rec in rank:
            if n not in out:
                continue
            print("")
            print("=" * 88)
            print("%s   %s" % (n, rec["assay"]["moth_number"]))
            print("=" * 88)
            print("  " + rec["presence"])
            print("")
            for ax in A.WEIGHTS:
                d = rec["axes"][ax]
                # UNCAPPED, in the view whose flag is literally named --full. This printed
                # `d["cited"][:58]`, and the cited sentence is the ENTIRE warrant for the score
                # sitting beside it: 54 of the 66 axis citations were being cut, the longest
                # (Vados, acumen) at 294 characters. data/PANTHEON.json held the whole text, so
                # nothing was lost on disk -- what was lost was the reader's ability to check
                # the claim, which is the only reason to print an axis line at all.
                #
                # Same shape as `tiers.deliberate_joins`, whose `shared.get((a, b), [])[:3]` was
                # brought in line in run #27 on the owner's 2026-08-24 ruling, and that
                # docstring's sentence carries over verbatim: a cap on the evidence for a claim
                # is not a display convenience. WRAPPED rather than simply widened, because a
                # citation is prose of no fixed length and one 294-character line is its own
                # kind of unreadable; continuation lines hang under the first so the column
                # structure survives and every character is on screen. Order 9d24c8a5febf.
                head = "   %-15s%5.1f  [%s] " % (ax, d["score"], d["provenance"])
                body = textwrap.wrap(str(d["cited"]), width=max(24, 92 - len(head))) or [""]
                print(head + body[0])
                for cont in body[1:]:
                    print(" " * len(head) + cont)
    print("")
    if write_ok:
        print("-> " + OUT)
    else:
        print("WRITE DENIED: %s did not land this round; rerun to retry" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
