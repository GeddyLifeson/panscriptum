#!/usr/bin/env python3
"""HAND-BUILT — assays for entities the automated pass cannot reach, and why it cannot.

Each sheet here exists because an entity was ASKED FOR and the library could not answer, and in
every case the reason turned out to be a defect rather than a gap. Recording the defect beside
the assay is the point: the number is worth less than knowing why the machine could not produce
it.

GETTER EMPEROR -- catalogued, mined, and invisible
--------------------------------------------------
It is in the library. `data/records/getter-robo.json` holds it, `feats/getterrobo_fandom_com/`
has its mined page, and its own catalogue entry reads:

    "type":     "Character"
    "category": "Media (in-fiction media: books, songs, broadcasts, works that exist
                 within the story itself)"

The two fields contradict each other in the same record, and it is the ONLY Media entry among
that source's 121 -- a category of one. Its own description says it is "a gigantic being...
Wielding godlike power, it continually absorbs matter on a universal scale". An M7 filed as
though it were a book, and therefore absent from every downstream stage that reads Persons.

Library-wide there are 548 entries typed `Character` and filed elsewhere, 41 of them under
Media. Many are legitimate -- Weyland-Yutani is typed Character and correctly filed under
Factions -- so this is not a blanket repair. It is a class of error worth a pass of its own.

MISTER MXYZPTLK -- mined twice, zero feats, and the gate was right each time
---------------------------------------------------------------------------
He was never catalogued: `data/records/dc.json` holds 377 entries for the whole of DC, and he
is not among them. Mining him directly works immediately -- two pages, 29,676 characters -- and
still yields NOTHING:

    pages 1 (13,651 chars)   feats 0   held-back 2
    pages 1 (16,025 chars)   feats 0   held-back 2

The subject gate is doing exactly what it was built to do. Almost every sentence on his page has
Superman as the actor: Superman tricks him, Superman rewires the typewriter, Superman gets him to
paint his face blue. Mxyzptlk is the PATIENT of his own article, because the character's entire
premise is losing. A gate that requires the entity to be the doer will refuse that page forever,
and it should -- but the entity is not therefore unmeasurable, it is unmeasurable BY THAT GATE.
That is a real limit of the instrument and it is worth writing down next to the sheet.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assay as A                                                       # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

OUT = os.path.join(HERE, "data", "HANDBUILT_ASSAYS.json")

ROSTER = {
 "The Black Winter": dict(
  anchor="M8", host="marvel.fandom.com", epoch="Thor Vol 6, the Herald of Thunder",
  why_missed="never catalogued, and its page title carries a DOUBLE parenthetical -- "
             "'Black Winter (Sixth Cosmos) (Multiverse)'. Every sane guess at the title returns "
             "zero chars, and 'Black Winter' itself is a 492-character disambiguation stub that "
             "mines to nothing. The library had no way to find it by name.",
  presence="It eats universes for a living and it is not the only one of its kind. 'This Black "
           "Winter was one of the ENDERS, A RACE THAT CONSUMES ENTIRE UNIVERSES.' Its own power "
           "listing reads 'Universal Consumption: The Black Winter devours entire universes AND "
           "TIMELINES, reducing them to nothingness.' A being whose diet is universes is not "
           "present at universal scale -- universes are objects to it, and the scale it moves "
           "through is the one that contains them.",
  axes=dict(
   ruin=(9.5, "'Devours entire universes and timelines, reducing them to nothingness' -- and it "
              "'consumed the universe that existed in the Sixth Cosmos before the current "
              "Multiverse, leaving Galan as the sole survivor'", "wiki"),
   continuity=(9.0, "It predates the current multiverse and survived the turn from one cosmos to "
                    "the next. Nothing in the record defeats it; Thor ESCAPES", "wiki"),
   celerity=(4.5, "Never contests tempo with anything. It is inevitability rather than speed",
             "canon"),
   reach=(9.0, "'The Black Winter attacked an alternate universe' -- it reaches across the "
               "multiverse to feed", "wiki"),
   transgression=(8.5, "It consumes TIMELINES, not merely matter: histories are erased rather "
                       "than destroyed. And it wears other beings' futures as a face", "wiki"),
   sustain=(9.5, "Formless and perpetually feeding, across cosmic iterations. 'Life-Force "
                 "Absorption: feeds upon the life forces of universes and cosmic entities it "
                 "consumes, INCLUDING GALACTUS HIMSELF'", "wiki"),
   vector=(8.5, "Moves between universes and between cosmoses under its own power", "wiki"),
   volition=(8.0, "'Assuring him it had no intention of destroying his universe' -- it declines "
                  "a meal by choice, which is the clearest possible evidence of a will", "wiki"),
   acumen=(7.0, "Chose Galan of Taa as its Herald from an entire dead cosmos, and works on Thor "
                "by showing him his own death rather than by fighting him", "wiki"),
   discernment=(7.5, "Perceives across timelines well enough to show a god a true vision of his "
                     "own end", "wiki"),
   suasion=(7.5, "IT MADE GALACTUS. The Devourer of Worlds is its herald and its leavings, and "
                 "'the Silver Surfer compares it to Galactus but on a far larger scale, "
                 "consuming universes instead of planets'", "wiki"))),

 "Getter Emperor": dict(
  anchor="M7", host="getterrobo.fandom.com", epoch="Shin Getter Robo, final evolution",
  why_missed="catalogued as Media, not as a Person -- invisible to every assay stage",
  presence="A universe, and taking more of it continuously. Its own catalogue entry: 'a "
           "gigantic being described as the final evolution of the Getter. Wielding godlike "
           "power, IT CONTINUALLY ABSORBS MATTER ON A UNIVERSAL SCALE.' It is not a being that "
           "acts at universal scale occasionally -- it is one whose ordinary metabolism is "
           "universal, and which grows monotonically toward occupying everything.",
  axes=dict(
   ruin=(8.5, "'Each Getter Machine is armed with a Getter Beam capable of destroying an entire "
              "planet' -- and the Emperor is the final evolution of the whole line", "wiki"),
   continuity=(9.0, "The terminal form of an open-ended evolution. Nothing in the record ends "
                    "it; it is what everything else is on the way to becoming", "wiki"),
   celerity=(5.5, "Enormous and unhurried. Its threat is not tempo and the record never gives "
                  "it one", "canon"),
   reach=(9.0, "'The complete machine's Getter Beam capable of travelling over 400 million "
               "light-years' -- a firing range spanning thousands of galaxies", "wiki"),
   transgression=(8.0, "Getter Rays are the evolutionary principle of that cosmos rather than an "
                       "energy source; the Emperor is that principle wearing a body", "canon"),
   sustain=(9.5, "'Continually absorbs matter' -- it has no clock, no lapse and no upper bound. "
                 "The highest sustain in the library", "wiki"),
   vector=(7.5, "Moves through space at a scale where galaxies are waypoints", "canon"),
   volition=(4.0, "'Depicted as neither a malevolent or benevolent force' -- it wants nothing "
                  "the record can name, which is a low score and not a criticism", "wiki"),
   acumen=(3.0, "No reasoning is ever depicted. It does not plan; it arrives", "canon"),
   discernment=(4.0, "No perception is attributed to it beyond its own advance", "canon"),
   suasion=(6.5, "'A major plot point throughout Shin Getter Robo and the entire Getter Robo "
                 "universe', and 'humanity spread across space and conquered countless worlds' "
                 "under the power it represents. An entire species' future organises around it",
            "wiki"))),

 "Mister Mxyzptlk": dict(
  anchor="M8", host="dc.fandom.com", epoch="Post-Crisis through Prime Earth",
  why_missed="never catalogued (DC's roster is 377 entries); mines to zero feats because he is "
             "the patient of every sentence on his own page",
  presence="A fifth-dimensional being, and the fifth dimension is not inside the multiverse the "
           "way a universe is -- it looks down on it. His own page lists him harangueing "
           "Supermen on Earth-One, Earth-Two, Earth 12, 16, 21, 22, 29, 38, 49, 55, 66, 162, 898 "
           "and 1956. He is a recurring feature OF the multiverse rather than a resident of any "
           "universe in it, and Zrfff is his address.",
  axes=dict(
   ruin=(6.0, "'This changed history so that Earth was destroyed' -- a world lost as the "
              "SIDE EFFECT of him briefly deciding to be a serious student", "wiki"),
   continuity=(9.5, "He cannot be killed, only sent home, and only by being tricked into saying "
                    "his own name backwards. The rules for doing it change every visit, by his "
                    "choice", "wiki"),
   celerity=(4.5, "Never depicted contesting tempo with anything. He does not need to", "canon"),
   reach=(8.5, "Present across fourteen named Earths on his own page, plus counterparts, "
               "offspring and rivals seeded through the multiverse", "wiki"),
   transgression=(9.5, "'A reality-manipulating imp from the 5th Dimension.' He brings a giant "
                       "typewriter into existence out of a billboard advertisement because the "
                       "scene needs one. Near-ceiling, and the axis's clearest case", "wiki"),
   sustain=(9.0, "No state to hold and no cost; the ninety-day exile is imposed from outside "
                 "and is the only limit on record", "wiki"),
   vector=(8.5, "Moves between the fifth dimension and any universe he pleases, at will", "wiki"),
   volition=(7.0, "Does exactly as he likes and nothing compels him -- except a naming rule he "
                  "invented and agreed to himself", "wiki"),
   acumen=(6.5, "Chooses 'Mxyzptlk' deliberately 'as he figures it will be nearly impossible for "
                "Superman to accomplish'. He games the rules he writes", "wiki"),
   discernment=(4.0, "THE DEFECT AT THE HEART OF HIM. A near-omnipotent being who loses, every "
                     "single time, to a newspaperman with a trick -- a rewired typewriter, a "
                     "dare, a bucket of blue paint. Reality obeys him and he cannot read a room",
                "wiki"),
   suasion=(6.0, "Poses as Ben Deroy and 'convinces Lois Lane to marry him'", "wiki"))),
}


def compute():
    out = {}
    for name, rec in ROSTER.items():
        scores = {ax: v[0] for ax, v in rec["axes"].items()}
        sheet = {ax: "[" + v[2] + "] " + v[1] for ax, v in rec["axes"].items()}
        res = A.assay(rec["anchor"], scores, attestation="Transcribed",
                      epoch=rec["epoch"], worksheet=sheet)
        out[name] = {"assay": res, "anchor": rec["anchor"], "host": rec["host"],
                     "epoch": rec["epoch"], "presence": rec["presence"],
                     "why_the_machine_missed_it": rec["why_missed"],
                     "axes": {k: {"score": v[0], "cited": v[1], "provenance": v[2]}
                              for k, v in rec["axes"].items()}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    a = ap.parse_args()
    out = compute()
    for n, rec in sorted(out.items(),
                         key=lambda kv: -(A.LADDER.index(kv[1]["assay"]["magnitude"])
                                          + kv[1]["assay"]["decimal"])):
        print("=" * 88)
        print("%-24s %s   (%s)" % (n, rec["assay"]["moth_number"], rec["epoch"]))
        print("=" * 88)
        print("  ANCHOR %s -- %s" % (rec["anchor"], rec["presence"]))
        print("")
        print("  MISSED BECAUSE: " + rec["why_the_machine_missed_it"])
        if a.full:
            print("")
            for ax in A.WEIGHTS:
                d = rec["axes"][ax]
                print("   %-15s%5.1f  [%s] %s"
                      % (ax, d["score"], d["provenance"], d["cited"][:58]))
        print("")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("-> " + OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
