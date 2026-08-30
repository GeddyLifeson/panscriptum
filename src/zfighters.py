#!/usr/bin/env python3
"""Z FIGHTERS -- hand-built assays under the presence thesis.

WHY BY HAND
-----------
The mined evidence for these fifteen is epoch-skewed to the point of uselessness. Krillin's only
surfaced feat is "a power level of 5,000 according to the Movie 3 Pamphlet"; Tien's is 180;
Gohan's best is "rose to over 1,370 and seriously hurt his uncle". Scored as they stand, the Z
Fighters come out at M1 -- which is a correct reading of the sentences the miner happened to
surface, and a wrong measurement of the beings they describe. reference.py already named this
failure: "An assay without a fixed epoch is not a loose assay, it is a measurement of an
unspecified subject."

So each sheet below fixes an epoch, and cites the record at that epoch. Provenance is marked
per axis: [wiki] where the sentence is in the mined cache verbatim, [canon] where the event is
on-panel at the locus given and the miner did not surface it.

THE ANCHOR RULE APPLIED HERE
----------------------------
Presence, per the charter's band table: M3 is a planet, M4 a planetary or stellar system, M7 a
universe. The operative question for each is the largest scale at which the entity is a FACTOR --
where reality at that scale would run differently without them. Not what they could destroy.

That rule produces one result worth stating plainly before anyone reads the table: ANDROID 17
ANCHORS AT M7, above Vegeta and every Earth-raised fighter except Goku. He won the Tournament of
Power, and the Super Dragon Balls wish that restored the erased universes was his. Reality at
universal scale is measurably different because of him, which is the whole of what the anchor
asks. Under the old threat doctrine he would sit well below Gohan. Under presence he does not,
and the difference is not a scoring artefact -- it is the thesis working as intended.

The mirror of that result is Krillin, Tien and Yamcha. All three fought in the Tournament of
Power; none of them anchors there. Being present AT an event whose stakes are universal is not
the same as being present at universal scale, and the distinction is the one the anchor exists to
draw. They are planetary, and they are excellent at it.
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

OUT = os.path.join(HERE, "data", "Z_FIGHTERS.json")

# (score, evidence, provenance)
ROSTER = {
 "Vegeta": dict(
  anchor="M7", epoch="Tournament of Power, Super Saiyan Blue Evolved",
  presence="A factor in universal-scale events by his own action, not by attendance. He fights a "
           "God of Destruction and survives it, is trained personally by an angel, contests the "
           "Tournament of Power to its closing minutes, and puts down Toppo AFTER Toppo assumes "
           "the power of a God of Destruction. Gods of other universes know his name.",
  axes=dict(
   ruin=(3.5, "Final Flash destroyed a large portion of the area against Cell; Galick Gun is "
              "'capable of destroying large planets if enough power is put into it'", "wiki"),
   continuity=(5.0, "Killed by Frieza, by Buu at his own hand, and by Beerus's strike, and "
                    "restored each time -- but never by his own property", "canon"),
   celerity=(7.5, "Trades at Blue Evolved tempo with Toppo in his God of Destruction state",
             "canon"),
   reach=(3.0, "'Huge enough to be seen in space, with potency to destroy planets'", "wiki"),
   transgression=(5.5, "Attempted the destruction of the Universe Tree, a structure feeding on "
                       "universal energy", "wiki"),
   sustain=(4.0, "Blue Evolved holds far longer than a Kaio-ken burst but still lapses inside "
                 "one engagement", "canon"),
   vector=(5.0, "Travels to other universes and to the World of Void; no independent "
                "cross-rung passage of his own", "canon"),
   volition=(9.5, "The defining axis. He surpasses his own ceiling by refusal at Toppo, and the "
                  "Saiyan pride that was his flaw becomes the mechanism of every ascent he "
                  "makes", "canon"),
   acumen=(6.5, "The strategist of the pair: he reads Cell's sloppiness, engineers the Buu "
                "absorption gambit, and Piccolo credits his loss to fighting style rather than "
                "power", "wiki"),
   discernment=(6.0, "Ki-sensing at planetary range; reads reserve and intent mid-exchange",
                "canon"),
   suasion=(4.0, "Commands by rank and by record rather than by warmth; Cabba takes him as a "
                 "master on his word", "wiki"))),

 "Android 17": dict(
  anchor="M7", epoch="Tournament of Power, final survivor",
  presence="THE HIGHEST-EXTENT ACT ANY Z FIGHTER HAS ON RECORD. He wins the Tournament of Power, "
           "and the Super Dragon Balls wish he is granted RESTORES THE ERASED UNIVERSES. Whole "
           "universes exist again because of a choice he made. Nothing else in this roster -- "
           "Goku included -- has a single act of that extent attached to its own name.",
  axes=dict(
   ruin=(2.5, "Never the destructive ceiling of his own team; his barriers and blasts are "
              "arena-scale", "canon"),
   continuity=(8.5, "Infinite energy by construction -- he does not tire, and he self-destructs "
                    "at full output and survives to fight on", "canon"),
   celerity=(7.0, "Keeps pace in the final three alongside Goku and Frieza", "canon"),
   reach=(8.5, "The restoration wish reaches every erased universe at once -- extent that "
               "nothing else on this roster touches", "canon"),
   transgression=(6.0, "Barrier techniques that hold against Jiren's output, and an energy "
                       "source that declines the exhaustion every other fighter obeys", "canon"),
   sustain=(9.5, "The one axis where he outclasses every Saiyan absolutely: limitless energy, "
                 "no transformation to hold, no clock", "canon"),
   vector=(3.0, "Carried to the World of Void; no passage of his own", "canon"),
   volition=(7.5, "Chooses self-destruction to buy his team the match, having entered for prize "
                  "money and a ranger's wage", "canon"),
   acumen=(6.0, "Fights the attrition war the Saiyans cannot: conserves, screens for others, and "
                "is standing when they are not", "canon"),
   discernment=(5.5, "Reads the arena and the eliminations rather than ki alone", "canon"),
   suasion=(4.5, "A park ranger with no following, whose one act of persuasion is asking for "
                 "the universes back", "canon"))),

 "Gogeta": dict(
  anchor="M7", epoch="Super Saiyan Blue, Broly / Hearts",
  presence="A being whose clashes shatter reality as a side effect. Both Gogetas' Ultimate "
           "Kamehamehas 'briefly shatter reality'; the plot he ends is one aimed at the gods who "
           "'can destroy reality on a whim'. He exists for minutes at a time and those minutes "
           "are universal in extent.",
  axes=dict(
   ruin=(6.5, "Shatters Hearts' gem and bursts his aura through him; the clash 'briefly "
              "shattering reality'", "wiki"),
   continuity=(4.0, "Never defeated, but the fusion itself is the fragility -- a single failure "
                    "ends the being", "canon"),
   celerity=(8.5, "Outpaces Broly in Full Power and dodges Hearts mid-monologue", "wiki"),
   reach=(6.0, "Reality-shattering output at arena range; no universal-range act of his own",
          "wiki"),
   transgression=(8.0, "Punches Broly through dimensions into another realm entirely", "canon"),
   sustain=(1.0, "Thirty minutes at the outside, and far less at Blue. The lowest sustain on "
                 "this roster by construction", "canon"),
   vector=(7.0, "Moves between dimensions in the course of a fight rather than by technique",
           "canon"),
   volition=(7.0, "A merged will, and the merge is voluntary on both sides", "canon"),
   acumen=(6.5, "Fights with Vegeta's read and Goku's instinct at once, which is the stated "
                "point of the fusion", "canon"),
   discernment=(7.0, "Locates Broly's rage state and plays to it deliberately", "canon"),
   suasion=(3.0, "Exists too briefly to move anyone; Hearts monologues AT him", "wiki"))),

 "Vegito": dict(
  anchor="M7", epoch="Super Saiyan Blue, Merged Zamasu",
  presence="His anger alone is a universal hazard: 'his anger at this causes him to start "
           "breaking through dimensions, which, if left unchecked, could destroy the universe.' "
           "A being whose emotional state is scored at universal extent is present at that "
           "scale whatever else he does.",
  axes=dict(
   ruin=(6.0, "Cuts Merged Zamasu apart repeatedly; the halves reform, which is Zamasu's "
              "property and not a limit on the cut", "canon"),
   continuity=(4.5, "Undefeated in every appearance, and defused by his own time limit twice",
               "canon"),
   celerity=(8.5, "Toys with Super Buu at a tempo Buu cannot follow", "canon"),
   reach=(7.5, "'Breaking through dimensions, which, if left unchecked, could destroy the "
               "universe'", "wiki"),
   transgression=(8.0, "Breaks dimensions by temper; the Potara fusion itself is a Kai-tier "
                       "operation on identity", "wiki"),
   sustain=(1.0, "The famous defect: the fusion lapses at the decisive moment, twice, and the "
                 "record turns on it both times", "canon"),
   vector=(7.0, "Dimensional passage as an involuntary by-product of rage", "wiki"),
   volition=(8.0, "Fights Buu from inside Buu after choosing to be absorbed", "canon"),
   acumen=(7.5, "The absorption gambit is planned in advance and executed against a being that "
                "reads minds", "canon"),
   discernment=(7.0, "Sees through Zamasu's immortality to the structure sustaining it", "canon"),
   suasion=(3.5, "Taunts rather than persuades; no follower has ever been won by Vegito",
            "canon"))),

 "Gohan": dict(
  anchor="M4", epoch="Ultimate / Mystic Gohan, Tournament of Power",
  presence="A stellar system. Cell's Solar Kamehameha would have taken the solar system with it, "
           "and Gohan is the one who decided that contest; he later leads Team Universe 7 into "
           "the Tournament of Power without being its decisive fighter. His extent is his own "
           "system, and his registration above it is as a participant rather than a factor.",
  axes=dict(
   ruin=(6.0, "'Disintegrating an entire mountain with a single blast'; the one-armed "
              "Kamehameha that ends Cell", "wiki"),
   continuity=(5.5, "Survives Cell's full output at eleven and Buu's beating at his peak; dies "
                    "twice and returns by wish, never by property", "canon"),
   celerity=(7.0, "Holds Dyspo and Anilaza in the Tournament of Power", "canon"),
   reach=(5.5, "'Destroy entire mountains with random blows' and 'lift the extremely heavy Z "
                "Sword'", "wiki"),
   transgression=(4.0, "No law-breaking technique of his own; his ascents are potential "
                       "unlocked, not rules rewritten", "canon"),
   sustain=(7.5, "Ultimate Gohan is a PERMANENT state, not a transformation on a clock -- the "
                 "highest sustain of any Saiyan on this roster", "canon"),
   vector=(3.0, "Carried between worlds by others; Instant Transmission is not his", "canon"),
   volition=(6.0, "Ascends by rage rather than by choice, and the record notes his reluctance as "
                  "the recurring cost", "canon"),
   acumen=(8.5, "The scholar of the roster -- a doctorate, and the tactical read that puts him "
                "in charge of Team Universe 7 over stronger fighters", "canon"),
   discernment=(6.5, "Ki-sensing at planetary range; reads Cell's arrogance and plays it", "canon"),
   suasion=(6.5, "Chosen as team leader by fighters who outrank him in power, which is the axis "
                 "in its purest form", "canon"))),

 "Piccolo": dict(
  anchor="M3", epoch="Fused with Kami and Nail, Cell Saga onward",
  presence="A planet, and structurally so: while he lives the Dragon Balls exist, and when he "
           "dies they do not. No other fighter on this roster is load-bearing for a planetary "
           "institution in that way -- Earth's capacity to undo its own deaths runs through his "
           "continued existence.",
  axes=dict(
   ruin=(6.0, "'Immense physical strength, allowing him to easily destroy entire mountains with "
              "random blows'", "wiki"),
   continuity=(6.0, "Dies for Gohan twice and returns by wish; regenerates from injury that "
                    "would end a human", "canon"),
   celerity=(6.0, "Keeps pace through the Cell Saga; falls behind by the Buu Saga and the record "
                  "says so", "canon"),
   reach=(6.5, "'Piccolo used this technique to hide the moon in which it appears destroyed'",
          "wiki"),
   transgression=(7.5, "Illusion that makes a destroyed target still exist, and a moon that "
                       "appears destroyed while remaining -- he edits what is the case, which is "
                       "the axis exactly", "wiki"),
   sustain=(7.0, "No transformation to hold and no clock; he simply persists", "canon"),
   vector=(3.5, "Interplanetary travel by ship and by others; none of his own", "canon"),
   volition=(7.0, "Fuses with Nail and then Kami, each an irreversible surrender of a separate "
                  "self, chosen twice", "canon"),
   acumen=(9.0, "The tactician of the series: the Cell Games strategy, Gohan's training, and the "
                "Fusion Dance instruction all originate with him. Highest acumen on the roster",
           "canon"),
   discernment=(7.5, "Sensing at planetary range without ki, and the read that identifies Cell's "
                     "plan before Cell states it", "canon"),
   suasion=(6.0, "Raises Gohan and is obeyed by fighters who could kill him", "canon"))),

 "Future Trunks": dict(
  anchor="M3", epoch="Super Saiyan Rage, Future timeline",
  presence="One planet, in a timeline he personally decided. He kills Frieza and King Cold on "
           "arrival, ends Future Cell, and is the last defender of an Earth with nobody else "
           "left. 'Bringing peace to his timeline' is a planetary result and the record calls it "
           "one.",
  axes=dict(
   ruin=(5.5, "Ends Future Cell outright; Burning Attack is 'capable of destroying large planets "
              "if enough power is put into it'", "wiki"),
   continuity=(4.5, "Killed by Cell and restored by wish; killed by Black in his own timeline "
                    "with no wish available", "canon"),
   celerity=(6.5, "Bisects Frieza before Frieza registers the movement", "canon"),
   reach=(4.5, "Planet-scale output at close range; no extended reach", "wiki"),
   transgression=(6.0, "Time travel as a practice rather than an accident, and the Sword of Hope "
                       "cutting Merged Zamasu, an immortal", "canon"),
   sustain=(5.0, "Super Saiyan Rage holds through an engagement but costs him", "canon"),
   vector=(8.0, "A working time machine he arrives in and leaves by -- cross-timeline passage "
                "under his own control, which almost nothing else here has", "canon"),
   volition=(8.5, "Rage state driven purely by refusal to lose another world; he fights Black "
                  "and Zamasu knowing he cannot win", "canon"),
   acumen=(6.5, "Arrives with a plan, a heart-medicine, and a timeline of events, and executes "
                "all three", "canon"),
   discernment=(5.5, "Ki-sensing at battlefield range", "canon"),
   suasion=(5.0, "Trusted instantly by strangers on evidence he brings with him", "canon"))),

 "Android 18": dict(
  anchor="M3", epoch="Cell Saga through Tournament of Power",
  presence="A planet. In the future timeline she and 17 are the reason Earth has no defenders "
           "left; in the present she is one of its defenders and a Tournament of Power entrant. "
           "Her extent begins and ends with the world she is on.",
  axes=dict(
   ruin=(4.0, "Breaks Vegeta's arm and outclasses every Z Fighter present at her introduction",
          "canon"),
   continuity=(8.0, "Infinite energy, no fatigue, and no ageing -- the same construction as 17",
               "canon"),
   celerity=(6.0, "Matches Super Saiyan tempo at introduction; outpaced by the Buu era", "canon"),
   reach=(3.5, "Close-quarters output only", "canon"),
   transgression=(5.0, "An energy source that declines exhaustion, which is a standing exception "
                       "to the rule every organic fighter obeys", "canon"),
   sustain=(9.0, "Limitless. She does not tire, and the record makes that her defining "
                 "advantage over Saiyans", "canon"),
   vector=(2.5, "No travel of her own", "canon"),
   volition=(6.0, "Chooses her team's interest over her own repeatedly in the Tournament of "
                  "Power", "canon"),
   acumen=(6.0, "Fights economically and reads matchups; declines fights she cannot win", "canon"),
   discernment=(4.0, "No ki sense at all -- a real and cited blindness", "canon"),
   suasion=(4.5, "A family and a marriage, and no following beyond it", "canon"))),

 "Gotenks": dict(
  anchor="M3", epoch="Super Saiyan 3, Buu Saga",
  presence="A planet, briefly. He fights Super Buu inside the Hyperbolic Time Chamber and on "
           "Earth, and the world's survival turns on him for the length of a fusion. Nothing "
           "above Earth registers him at all.",
  axes=dict(
   ruin=(5.5, "Super Ghost Kamikaze Attack dismembers Super Buu; Super Saiyan 3 at a child's "
              "hands", "canon"),
   continuity=(3.5, "Absorbed by Buu; the fusion is undone by damage and by time alike", "canon"),
   celerity=(7.0, "Outpaces Super Buu until the fusion lapses", "canon"),
   reach=(4.0, "Planet-surface range", "canon"),
   transgression=(6.5, "The Fusion Dance itself, and ghosts that act with independent volition",
                  "canon"),
   sustain=(0.5, "Thirty minutes, less at Super Saiyan 3, and it lapses at the worst possible "
                 "moment every single time. The lowest sustain in the library", "canon"),
   vector=(3.0, "Flight only", "canon"),
   volition=(5.0, "Enormous confidence, no discipline; the record makes the arrogance the cause "
                  "of the loss", "canon"),
   acumen=(2.0, "Two children. Every plan is improvised and most are bad", "canon"),
   discernment=(4.5, "Ki-sensing at planetary range", "canon"),
   suasion=(2.5, "Insufferable to allies and enemies equally", "canon"))),

 "Krillin": dict(
  anchor="M3", epoch="Tournament of Power, unlocked potential",
  presence="A planet, and no further. He fights in a tournament whose stakes are twelve "
           "universes, and that is attendance rather than extent -- the distinction the anchor "
           "exists to draw. On Earth he is a defender, a police officer and a constant; off it "
           "he is a name on a roster.",
  axes=dict(
   ruin=(2.5, "Destructo Disc cuts anything it reaches, which is a Transgression property rather "
              "than an output; his raw ceiling is the lowest here", "canon"),
   continuity=(2.0, "The most-killed character in the series, restored every time by others' "
                    "wishes and never by anything of his own", "canon"),
   celerity=(5.0, "Fastest of the humans; outclassed by every Saiyan present", "canon"),
   reach=(3.0, "'A power level of 5,000 according to the Movie 3 Pamphlet'", "wiki"),
   transgression=(6.5, "The Destructo Disc ignores durability entirely -- a cutting plane that "
                       "threatens Frieza and Nappa alike regardless of the gap", "canon"),
   sustain=(5.5, "No transformation to hold; fights to exhaustion on his own reserves", "canon"),
   vector=(2.5, "Flight and others' ships", "canon"),
   volition=(7.5, "Enters the Tournament of Power knowing exactly what he is against, and his "
                  "death is twice the hinge the strongest fighter in the series turns on",
             "canon"),
   acumen=(7.0, "Reads fights he cannot win and acts anyway; the Solar Flare and Disc "
                "combination is his own", "canon"),
   discernment=(6.5, "Ki-sensing at planetary range, and the first to notice most arrivals",
                "canon"),
   suasion=(5.5, "Goku's oldest friend, and the reason several of Goku's decisions go the way "
                 "they do", "canon"))),

 "Tien Shinhan": dict(
  anchor="M3", epoch="Tournament of Power, Neo Tri-Beam",
  presence="A planet. A Tournament of Power entrant and one of Earth's standing defenders; his "
           "dojo and his students are the whole of his footprint outside a fight.",
  axes=dict(
   ruin=(3.5, "Neo Tri-Beam scales with what he is willing to spend of himself, and he spends it",
          "canon"),
   continuity=(2.0, "'Killed along with Tien when Kid Buu blows up the Earth using the Planet "
                    "Burst and is later wished back to life'", "wiki"),
   celerity=(5.0, "Multiform and after-image; outpaced by Saiyans from the Saiyan Saga onward",
             "canon"),
   reach=(3.0, "'His power level is 180 during the 22nd World Martial Arts Tournament'", "wiki"),
   transgression=(5.5, "Tri-Beam trades his own life force for output directly -- a rule most "
                       "fighters cannot invoke at all", "canon"),
   sustain=(3.0, "Tri-Beam is self-consuming by design; the technique's cost IS the fighter",
            "canon"),
   vector=(2.5, "Flight; carried otherwise", "canon"),
   volition=(8.0, "Holds Semi-Perfect Cell in place with Tri-Beam until he collapses, buying "
                  "time he knows will cost him everything", "canon"),
   acumen=(6.5, "A disciplined technician who trains others and fights to a plan", "canon"),
   discernment=(6.0, "The third eye, and ki-sensing at battlefield range", "canon"),
   suasion=(4.5, "Turns from the Crane School on his own judgement and takes students of his "
                 "own", "canon"))),

 "Goten": dict(
  anchor="M3", epoch="Super Saiyan, Buu Saga",
  presence="A planet, at seven years old. He reaches Super Saiyan younger than anyone on record "
           "and his half of Gotenks is load-bearing for Earth's survival in the Buu Saga.",
  axes=dict(
   ruin=(4.0, "Super Saiyan output as a child, casually reached", "canon"),
   continuity=(3.0, "Killed with Earth by Kid Buu and restored by wish", "canon"),
   celerity=(5.5, "Super Saiyan tempo at seven", "canon"),
   reach=(3.5, "Close range", "canon"),
   transgression=(4.0, "The Fusion Dance, learned and performed", "canon"),
   sustain=(6.0, "No clock on his base or Super Saiyan states", "canon"),
   vector=(3.0, "Flight", "canon"),
   volition=(4.5, "Reaches Super Saiyan without the grief every prior Saiyan needed, which the "
                  "record treats as remarkable and unearned alike", "canon"),
   acumen=(2.0, "Seven years old", "canon"),
   discernment=(4.5, "Ki-sensing", "canon"),
   suasion=(3.5, "Charming and entirely without followers", "canon"))),

 "Yamcha": dict(
  anchor="M3", epoch="Post-King Kai training, Cell Saga",
  presence="A planet, and the low end of it. One of Earth's defenders through the Saiyan and Cell "
           "sagas, and a professional baseball player afterwards, which is a real footprint on "
           "one world and nothing at all beyond it.",
  axes=dict(
   ruin=(3.0, "'He defeats Recoome, an opponent whose power level is at least 40,000 and had "
              "easily taken out Vegeta'", "wiki"),
   continuity=(1.5, "Killed by a Saibaman -- the single most-cited death in the series -- and "
                    "restored by others", "canon"),
   celerity=(4.5, "Wolf Fang Fist tempo; outclassed from the Saiyan Saga onward", "canon"),
   reach=(3.0, "Close range and Spirit Ball at short distance", "canon"),
   transgression=(3.0, "The Spirit Ball steers after release, and nothing else of his bends a "
                       "rule", "canon"),
   sustain=(5.0, "No transformation and no clock", "canon"),
   vector=(2.5, "Flight", "canon"),
   volition=(5.0, "Returns to the field repeatedly after being outclassed, and stops when he "
                  "judges he should", "canon"),
   acumen=(5.5, "A bandit's read on a fight, and the self-knowledge to retire from it", "canon"),
   discernment=(5.0, "Ki-sensing at battlefield range", "canon"),
   suasion=(4.0, "A public career and a following that has nothing to do with fighting", "canon"))),

 "Chiaotzu": dict(
  anchor="M2", epoch="Saiyan Saga, self-destruction against Nappa",
  presence="A continent at the outside. The smallest extent on this roster: he is a factor at "
           "the scale of the battlefield he is standing on, and the record's own summary of him "
           "is that he was 'killed along with Tien when Kid Buu blows up the Earth' -- present "
           "for the planetary event, not a party to it.",
  axes=dict(
   ruin=(4.5, "Detonates himself against Nappa at full output -- his entire being spent as the "
              "attack", "canon"),
   continuity=(1.0, "Dies twice and is restored by others; the second time the Dragon Balls "
                    "cannot take him", "wiki"),
   celerity=(3.5, "Slowest of the surviving Z Fighters", "canon"),
   reach=(4.0, "Telekinesis at line of sight, which exceeds his physical reach considerably",
          "canon"),
   transgression=(7.0, "Telekinesis and paralysis operate on the opponent directly, bypassing "
                       "durability -- the highest transgression-to-power ratio on the roster",
                  "canon"),
   sustain=(3.0, "Psychic work exhausts him quickly", "canon"),
   vector=(2.0, "Flight", "canon"),
   volition=(9.0, "Chooses his own detonation with full knowledge that the Dragon Balls have "
                  "already been used on him once. Near-ceiling, and the highest thing about him",
             "canon"),
   acumen=(4.5, "A capable second who follows Tien's plan rather than making one", "canon"),
   discernment=(6.0, "Reads minds and locates ki without seeing it", "canon"),
   suasion=(3.0, "One bond, held absolutely, and no reach past it", "canon"))),
}


def compute():
    out = {}
    for name, rec in ROSTER.items():
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
    ap = argparse.ArgumentParser(description="hand-built Z Fighter assays")
    ap.add_argument("--full", action="store_true", help="print every worksheet line")
    a = ap.parse_args()

    out = compute()

    # Goku's sheet lives in the presence-thesis rebuild; carry it in so the roster ranks whole.
    try:
        p = os.path.join(HERE, "data", "REFERENCE_ASSAYS_PRESENCE.json")
        with open(p, encoding="utf-8") as f:
            out["Son Goku"] = json.load(f)["Son Goku"]
    except Exception:
        # SAID OUT LOUD, AND CARRIED INTO THE FILE. The note stays -- this must not raise, the
        # local roster is still worth printing -- but a silence-ledger row is not something the
        # person reading the table will ever see, and the table prints under a banner claiming
        # to be THE Z FIGHTERS BY MAGNITUDE while missing the fighter the module's own header
        # ranks everyone else against. `data/Z_FIGHTERS.json` was then written without him and
        # `pantheon.py` merged that partial roster with no way to tell it from a whole one.
        silence.note("zfighters.py:goku")
        print("INCOMPLETE ROSTER: Son Goku's sheet could not be read from "
              "data/REFERENCE_ASSAYS_PRESENCE.json, so the ranking below and the file written "
              "at the end are missing him. Every placement relative to Goku is unstated.")
        out["_incomplete"] = ["Son Goku"]

    # `_incomplete` is a marker, not a fighter. Keys opening with an underscore are skipped by
    # everything that ranks, here and in `pantheon.py`'s merge, so the fact can ride in the JSON
    # without becoming a row in it.
    rank = sorted(((n, r) for n, r in out.items() if not n.startswith("_")),
                  key=lambda kv: -value(kv[1]))
    print("=" * 86)
    print("THE Z FIGHTERS, BY MAGNITUDE  (presence thesis; epoch fixed per fighter)")
    print("=" * 86)
    print("  %-16s %-16s %-9s %s" % ("FIGHTER", "ASSAY", "ANCHOR", "EPOCH"))
    print("  " + "-" * 82)
    band = None
    for n, rec in rank:
        b = rec["assay"]["magnitude"]
        if b != band:
            band = b
            print("  --- %s %s" % (b, "-" * 70))
        # Goku's sheet is carried in from the presence rebuild and does not repeat the anchor
        # and epoch at the top level -- both are inside the assay result there.
        anchor = rec.get("anchor") or rec["assay"].get("magnitude", "?")
        epoch = rec.get("epoch") or rec["assay"].get("epoch", "")
        # `epoch[:38]` cut the LAST column of the table for no gain -- nothing after it needs
        # aligning, so a long epoch costs line length and nothing else, while a cut one costs the
        # thing the header spends two paragraphs on: a fixed epoch is what makes each row a
        # measurement of a SPECIFIED subject. Five of the fourteen were cut (Vegeta 46 chars,
        # Gohan 44, Chiaotzu 43, Piccolo 42, Krillin 39). Same ruling as pantheon.py:294-297,
        # order 9d24c8a5febf, on the identical last-column cut in this table's sibling.
        print("  %-16s %-16s %-9s %s"
              % (n, rec["assay"]["moth_number"], anchor, epoch))

    if a.full:
        for n, rec in rank:
            print("")
            print("=" * 86)
            print("%s   %s   (%s)"
                  % (n, rec["assay"]["moth_number"],
                     rec.get("epoch") or rec["assay"].get("epoch", "")))
            print("=" * 86)
            print("  " + rec["presence"])
            print("")
            for ax in A.WEIGHTS:
                d = rec["axes"][ax]
                # NOT EVERY SHEET CARRIES `provenance`. The local roster's axes always get it
                # synthesised above (rec["axes"] -> {"score", "cited", "provenance"}), but the
                # Son Goku sheet is carried in whole from data/REFERENCE_ASSAYS_PRESENCE.json,
                # where every axis has only ["cited", "score"] -- verified against the file on
                # disk. `d["provenance"]` crashed `--full` outright on that sheet, which also
                # meant Z_FIGHTERS.json (below, read by pantheon.py) never got refreshed,
                # because the crash lands before that write. A missing label prints as an
                # honest blank rather than fabricating a "canon"/"wiki" this sheet never claimed.
                # WRAPPED, NOT CUT. `--full`'s help text is "print every worksheet line" and
                # `d["cited"][:60]` truncated every one of them, with no ellipsis and nothing
                # saying the sentence continued. Measured against the live roster: 100 of the 154
                # worksheet citations run past 60 characters and the worst three lose 97
                # characters each, so --full showed 39% of the evidence in the shape of all of
                # it. The cited sentence IS the worksheet -- this module's header stakes the
                # provenance mark on the sentence being in the mined cache VERBATIM. Same repair
                # in the twins wh40k.py and halo.py, which cut at 56 and 54.
                prov = d.get("provenance", "")
                body = textwrap.wrap(d["cited"], 60) or [""]
                print("   %-15s%5.1f  [%s] %s" % (ax, d["score"], prov, body[0]))
                for cont in body[1:]:
                    print("   %-15s%5s  %s %s" % ("", "", " " * (len(prov) + 2), cont))

    # ATOMIC. `data/Z_FIGHTERS.json` is read by `pantheon.py`, so a crash mid-write corrupts a
    # file another module consumes. The m100 tail, 2026-08-25.
    #
    # GATED: the comment above is about a CRASH mid-write; this is the quieter half of the same
    # risk. `write_json` returns whether the rename LANDED, this discarded it, and the run then
    # printed "-> {OUT}" and returned 0 -- so `pantheon.py` reading a stale Z_FIGHTERS.json looked
    # exactly like `pantheon.py` reading a fresh one. Note the paragraph above already records a
    # day when this file "never got refreshed" and nothing said so. Run #36 sweep.
    if not silence.write_json(OUT, out, indent=1, ensure_ascii=False):
        silence.note("zfighters.py:main-write-denied")
        print("")
        print("WRITE DENIED -> %s: replace refused; the assays above did NOT land and the file "
              "pantheon.py reads is the previous run's. Rerun to retry." % OUT)
        return 1
    print("")
    print("-> " + OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
