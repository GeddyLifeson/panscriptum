#!/usr/bin/env python3
"""HALO — the top of the setting, assayed under the presence thesis.

THE PRECURSORS AND THE FLOOD ARE THE SAME ENTITY, AND THAT IS THE FINDING
------------------------------------------------------------------------
The Gravemind's own page says it outright: it used "knowledge of the Precursors TO WHICH IT WAS
BORN FROM AND HAD BECOME". The Primordial introduces itself to the Ur-Didact as "the last of
those that gave you breath and shape and form, millions of years ago. I am the last of those
your kind rose up against and ruthlessly destroyed. I am the last Precursor. And our answer is
at hand."

So the strongest thing in Halo is not a being that survived an extinction. It is a being FOR
WHICH EXTINCTION WAS A TRANSFORMATION. The Forerunners "rose to seize the Mantle by killing
almost every Precursor", and what the survivors turned into is the thing that forced the
Forerunners to fire the Halo Array and annihilate all sentient life in the Milky Way rather than
lose to it. Genocide against them produced the Flood. That is a continuity score at the ceiling
and it is not rhetoric; it is what the pages say happened.

WHY THIS TOPS OUT AT M6 AND NOT M7
----------------------------------
The Precursors are "Extragalactic" and Tier-0 "Transsentient", with "the ability to travel among
galaxies and accelerate the evolution of intelligent life". Among galaxies -- plural, which is
M6, "a galaxy, group, or cluster". Nothing in the record claims a universe. Halo's ceiling is
genuinely lower than Warhammer's or Dragon Ball's, and saying so is the instrument working: a
setting does not get promoted for being well written.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assay as A                                                       # noqa: E402
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

OUT = os.path.join(HERE, "data", "HALO_ASSAYS.json")
HOST = "halo.fandom.com"

ROSTER = {
 "The Precursors": dict(
  anchor="M6", epoch="pre-Forerunner, through the Primordial",
  presence="Galaxies, plural, and the shape of everything living in them. 'Extragalactic... "
           "Transsentient beings, having the ability to TRAVEL AMONG GALAXIES AND ACCELERATE THE "
           "EVOLUTION OF INTELLIGENT LIFE', rated Tier-0 on the Forerunners' own technological "
           "scale -- the top of it, with the Forerunners far below. They made the Forerunners "
           "and they made humanity: 'I am the last of those that gave you breath and shape and "
           "form, millions of years ago.'",
  axes=dict(
   ruin=(7.5, "Their revenge, not their war: the thing they became forced the extinction of all "
              "sentient life in the galaxy as the ONLY available counter"),
   continuity=(9.9, "CEILING, AND THE CLEANEST CASE IN THE LIBRARY. The Forerunners 'rose to "
                    "seize the Mantle BY KILLING ALMOST EVERY PRECURSOR' -- and the survivors "
                    "came back as the Flood. Their extinction was a metamorphosis. There is no "
                    "state you can put them in that counts as dead"),
   celerity=(4.0, "They move on evolutionary timescales and never on a battlefield's"),
   reach=(9.0, "'Extragalactic'. Their footprint is measured in galaxies and their seeding "
               "reaches every intelligent species in this one"),
   transgression=(9.5, "'Able to change physical forms at will', Tier-0 Transsentience, and the "
                       "power to 'accelerate the evolution of intelligent life' -- they edit "
                       "what a species IS, over millions of years, as a matter of policy"),
   sustain=(9.5, "Millions of years, an extermination, and a second existence afterwards"),
   vector=(9.5, "Intergalactic passage as their defining attribute, plus the Star Roads their "
                "successor form still uses"),
   volition=(9.0, "They planned the Mantle's inheritance across millions of years, were "
                  "massacred for it, and executed the answer anyway. 'And our answer is at hand'"),
   acumen=(8.5, "'The Precursors had intended that the humans take on the role of inheriting the "
                "Mantle instead of the Forerunners' -- a succession plan the Forerunners only "
                "discovered by accident"),
   discernment=(8.0, "They judged the Forerunners unworthy and were correct"),
   suasion=(9.0, "THE MANTLE. A philosophy they handed down that governed an entire galactic "
                 "civilisation's law, religion and military doctrine for millions of years after "
                 "they were dead -- 'the Mantle and religious beliefs of individual Forerunners "
                 "ENTIRELY DICTATED THE GOVERNANCE OF THE FORERUNNER ECUMENE'. Persuasion that "
                 "outlives the persuader by an age"))),

 "The Gravemind": dict(
  anchor="M6", epoch="the Forerunner-Flood war, and again in M3 (Halo 2-3)",
  presence="A galaxy, eaten. It is a compound mind assembled from everything it has consumed, "
           "and what it consumed was most of the life in the Milky Way. The Forerunners' answer "
           "to it was not a weapon but a suicide: 'the Halos fired, ANNIHILATING ALL SENTIENT "
           "LIFE IN THE MILKY WAY GALAXY and containing the Flood.' Nothing else in this library "
           "has caused a galaxy to be sterilised on purpose by the people living in it.",
  axes=dict(
   ruin=(9.5, "'The Forerunners developed the Halo Array as a desperate countermeasure... which "
              "would destroy all sentient life in the Galaxy, thus denying the Flood food for "
              "growth.' Its ruin figure IS the galaxy, delivered by its victims"),
   continuity=(9.5, "Distributed across every organism it holds. Killing its bodies is feeding "
                    "it, and it survived the Array"),
   celerity=(3.5, "Immobile, patient, and always already there"),
   reach=(9.0, "'The Gravemind used the STAR ROADS of the Precursors to attack the Forerunners, "
               "hampering their Slipspace capacity' -- it took the galaxy's transit network away "
               "from the people who owned it"),
   transgression=(9.0, "It converts biomass into itself and keeps the minds. Death stops being "
                       "an exit"),
   sustain=(9.0, "Fed by everything alive; starved only by there being nothing alive"),
   vector=(8.0, "Star Roads and infested fleets; it travels by owning what travels"),
   volition=(9.0, "Three hundred years of war without once considering terms"),
   acumen=(9.0, "Negotiates, deceives and waits. It talks its enemies into positions rather than "
                "overrunning them"),
   discernment=(9.5, "It knows everything its victims knew, which is most of what anyone knew"),
   suasion=(6.5, "It persuades no one. It absorbs, which is the opposite -- and the axis is "
                 "scored on choices set by voice, so this is genuinely low"))),

 "The Ur-Didact": dict(
  anchor="M4", epoch="post-Composer, Requiem",
  presence="A fleet, a shield world and a grudge. The Forerunners' greatest commander, and the "
           "measure of the gap: he is the being the Primordial addresses AS A CHILD -- 'we meet "
           "again, young one' -- and he speaks for a civilisation that held the Mantle 'for all "
           "things' and lost it to something it had already exterminated once.",
  axes=dict(
   ruin=(7.0, "The Composer converts populations into data wholesale -- a planet's worth at a "
              "time"),
   continuity=(8.0, "Interred for millennia in a Cryptum and woke unchanged; survived his own "
                    "civilisation's end"),
   celerity=(6.0, "Slipspace-capable command, not personal speed"),
   reach=(6.5, "Fleet-scale, bounded by the Ecumene's own territory"),
   transgression=(8.0, "Composition: he ends people as bodies and continues them as data, which "
                       "is a rewrite of what a person is"),
   sustain=(7.0, "Millennia of dormancy at no cost"),
   vector=(6.5, "Slipspace, and the Domain"),
   volition=(9.0, "'The Mantle of Responsibility, for all things, belongs to Forerunners alone!' "
                  "-- he never once yields the claim, including after losing it"),
   acumen=(8.0, "The Ecumene's foremost strategist across a three-hundred-year war"),
   discernment=(7.0, "Understood the Flood's nature earlier than the Council would accept"),
   suasion=(7.5, "Commands absolute loyalty from Prometheans and is defied by his own wife"))),
}


def compute():
    out = {}
    for name, rec in ROSTER.items():
        scores = {ax: v[0] for ax, v in rec["axes"].items()}
        sheet = {ax: "[wiki] " + v[1] for ax, v in rec["axes"].items()}
        res = A.assay(rec["anchor"], scores, attestation="Transcribed",
                      epoch=rec["epoch"], worksheet=sheet)
        out[name] = {"assay": res, "anchor": rec["anchor"], "host": HOST,
                     "epoch": rec["epoch"], "presence": rec["presence"],
                     "axes": {k: {"score": v[0], "cited": v[1]} for k, v in rec["axes"].items()}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    a = ap.parse_args()
    out = compute()
    rank = sorted(out.items(),
                  key=lambda kv: -(A.LADDER.index(kv[1]["assay"]["magnitude"])
                                   + kv[1]["assay"]["decimal"]))
    print("=" * 74)
    print("HALO -- BY MAGNITUDE (presence thesis)")
    print("=" * 74)
    for n, rec in rank:
        print("  %-20s %-16s %s" % (n, rec["assay"]["moth_number"], rec["anchor"]))
    if a.full:
        for n, rec in rank:
            print("")
            print("=" * 74)
            print("%s   %s" % (n, rec["assay"]["moth_number"]))
            print("=" * 74)
            print("  " + rec["presence"])
            print("")
            for ax in A.WEIGHTS:
                d = rec["axes"][ax]
                print("   %-15s%5.1f  %s" % (ax, d["score"], d["cited"][:54]))
    # ATOMIC -- the m100 tail, 2026-08-25.
    silence.write_json(OUT, out, indent=1, ensure_ascii=False)
    print("")
    print("-> " + OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
