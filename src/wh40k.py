#!/usr/bin/env python3
"""WARHAMMER 40,000 — the top of the setting, assayed under the presence thesis.

WHY THE CHAOS GODS OUTRANK THE EMPEROR, AND IT IS NOT CLOSE
-----------------------------------------------------------
Under a threat doctrine this would be an argument. Under presence it is arithmetic.

The Emperor's extent is the Imperium: a million worlds, trillions of worshippers, and the
Astronomican, whose "reach is said to be around 70,000 light years, which by default becomes the
maximum radius of Astronomican-assisted Warp-navigable space". That is enormous and it is
GALACTIC -- a radius, with an outside.

The Chaos Gods have no outside. They are not beings in the Warp; they are what the Warp is made
of, and the Warp underlies every point in realspace. Khorne's own page states the mechanism
plainly: "CONSCIOUSLY OR NOT, ALL WARRIOR CULTURES PAY KHORNE HOMAGE with their acts of murder
and destruction, from the headhunting tribes of backwater Feral Worlds to the planet-conquering
Chaos Space Marine." Every act of violence anywhere in the universe, by anyone, including people
who have never heard of him, is a contribution to him. That is not reach. It is constitution.

So the four anchor at M7 -- "a universe AND ITS FUNDAMENTAL LAWS", which is exactly what an
emotion-substrate is in that setting -- and the Emperor at M6.

WHY THE FOUR ARE NOT SIMPLY TIED
--------------------------------
They share an anchor, which is correct: they are the same kind of thing at the same scale. The
decimals separate them on what the record actually attributes to each, and the separations are
real rather than decorative. Slaanesh has the largest single ACHIEVED act in the setting. Nurgle
has the largest CLAIM. Khorne has the broadest passive pervasion. Tzeentch has the deepest
transgression and the worst discipline.
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

OUT = os.path.join(HERE, "data", "WH40K_ASSAYS.json")
HOST = "warhammer40k.fandom.com"

ROSTER = {
 "Nurgle": dict(
  anchor="M7", epoch="M41, the Plague Wars",
  presence="Entropy with a face. His page frames him at a scale nothing else in the setting "
           "claims: 'if a being had the luxury of observing the rise and fall of empires, of "
           "seeing the birth of suns and their eventual collapse into swirling masses of cosmic "
           "destruction' -- that observer is Nurgle, and the timescale is the universe's own. "
           "His stated purpose is 'the Great Corruption and ultimate reshaping of the universe', "
           "and 'there will come a time when they collapse entirely and the universe will begin "
           "a massive transformation'. He is not trying to conquer the universe. He is waiting "
           "for it, because he is what it turns into.",
  axes=dict(
   ruin=(8.0, "Plague as a method: 'a choking plague to wipe out an Ork infestation on Hurax, a "
              "planet that Nurgle coveted' -- a world cleared as a favour to a lieutenant"),
   continuity=(9.9, "CEILING. Despair and decay cannot be killed because they are not events. "
                    "Of the four he is the one whose substrate is guaranteed by physics"),
   celerity=(2.0, "The slowest thing in the setting, deliberately. He does not need to arrive"),
   reach=(9.0, "'He returns to his cauldron and empties its contents into a bottomless drain, "
               "the noxious liquid falling as rain upon one of the mortal worlds' -- he waters "
               "planets from his kitchen"),
   transgression=(9.0, "The 'ultimate reshaping of the universe' is a rewrite of what matter "
                       "does, not a war against who holds it"),
   sustain=(9.9, "CEILING. He is fed by the one process that never stops anywhere"),
   vector=(8.0, "His realm touches every mortal world that rots, which is all of them"),
   volition=(8.5, "Patient, affectionate and utterly fixed. He has never once changed his aim"),
   acumen=(7.0, "Grants realms to lieutenants as acknowledgement of good work -- he administers "
                "rather than schemes, and it works"),
   discernment=(8.0, "Sees the whole arc of empires as a single motion"),
   suasion=(9.0, "The only Chaos God who offers LOVE, and it converts the desperate at a rate "
                 "the others cannot match with fear or ambition"))),

 "Khorne": dict(
  anchor="M7", epoch="M41",
  presence="The broadest passive presence in this library. 'CONSCIOUSLY OR NOT, ALL WARRIOR "
           "CULTURES PAY KHORNE HOMAGE with their acts of murder and destruction, from the "
           "headhunting tribes of backwater Feral Worlds to the planet-conquering Chaos Space "
           "Marine.' Every violent act by every being anywhere -- including everyone who has "
           "never heard of him and would refuse him if they had -- is a contribution to him. He "
           "does not need worshippers. He needs there to be conflict, and there is.",
  axes=dict(
   ruin=(9.5, "'It is Khorne's sole desire to drown the galaxy in a tide of slaughter, to "
              "conquer and kill every living thing until there is nothing left but spilt blood "
              "and shattered bone.' The highest ruin in the setting, and the least conditional"),
   continuity=(9.5, "'When Khorne does obliterate the invading armies of its brother gods, they "
                    "do not exact retribution directly' -- the other three do not fight him "
                    "head-on"),
   celerity=(7.5, "Immediate and unsubtle; his are the fastest interventions of the four"),
   reach=(9.5, "Every battlefield in the universe at once, without needing to be told"),
   transgression=(7.0, "The least rule-breaking of the four. He kills, which is legal everywhere"),
   sustain=(9.5, "Sustained by conflict, and conflict is the setting's only constant"),
   vector=(7.5, "'Each piece of the realm of battle constantly fights to obliterate the others' "
                "-- his own domain is in motion"),
   volition=(9.5, "Absolute and unsplittable. He wants ONE thing and has never wanted anything "
                  "else"),
   acumen=(2.0, "The lowest acumen at the top of this setting. He does not plan, and 'a follower "
                "who displeases Khorne by failing to provide sufficient blood sacrifices will "
                "likely find themselves as the next offering' -- he eats his own staff"),
   discernment=(4.0, "Sees violence and nothing else. Blind to everything Tzeentch trades in"),
   suasion=(8.0, "No persuasion required: he is paid homage by people who are not trying to"))),

 "Tzeentch": dict(
  anchor="M7", epoch="M41",
  presence="Change itself, and therefore present wherever anything is not yet settled. His "
           "constituency is the setting's most dangerous class: 'the individuals most likely to "
           "be tempted into the service of Tzeentch are PSYKERS, WHO ALREADY POSSESS THE SECRET "
           "AND FEARED ABILITY TO TAP THE LIMITLESS POWER OF THE WARP TO RESHAPE REALITY.' He "
           "does not recruit soldiers; he recruits the people who can edit the world.",
  axes=dict(
   ruin=(6.5, "Ruin is beneath him and he says so. He unmakes by arrangement, not by force"),
   continuity=(9.5, "Every defeat is a move he intended. The setting cannot distinguish his "
                    "losses from his plans, which is a form of invulnerability"),
   celerity=(8.0, "Acts before the situation exists"),
   reach=(9.0, "Through psykers, into any mind capable of touching the Warp -- which is the only "
               "route by which realspace is edited at all"),
   transgression=(9.9, "CEILING, AND THE CLEAREST CASE IN THE SETTING. 'The limitless power of "
                       "the Warp to reshape reality' is his instrument, wielded by proxies, "
                       "against the rules of what is"),
   sustain=(9.0, "Hope and ambition renew faster than they are spent"),
   vector=(9.0, "Moves through the Warp and through causality alike"),
   volition=(6.0, "Wants everything, therefore commits to nothing. His will is the most divided "
                  "of the four and the record makes that his defect"),
   acumen=(9.9, "CEILING. The schemer of a setting made of schemes"),
   discernment=(9.5, "Sees every branch, which is why he cannot choose one"),
   suasion=(8.5, "Buys the ambitious with the one thing they want, which is more"))),

 "Slaanesh": dict(
  anchor="M7", epoch="M41, post-Fall",
  presence="The only one of the four with a dated, catastrophic ACHIEVED act on the record. "
           "Its birth alone: 'the blast killed BILLIONS OF AELDARI IN A SINGLE INSTANT and "
           "devoured a great section of the galaxy in the process. Across the galaxy, that "
           "ancient species was almost wiped out.' A god whose mere coming-into-existence ended "
           "the setting's dominant civilisation and left a hole in the galaxy.",
  axes=dict(
   ruin=(9.5, "'Killed billions of Aeldari in a single instant and devoured a great section of "
              "the galaxy' -- and that was an accident of its birth, not an attack"),
   continuity=(8.5, "Youngest of the four and the only one with a birthday, which is a real "
                    "vulnerability the others do not have"),
   celerity=(8.5, "Instantaneous where desire is present, which is everywhere"),
   reach=(8.5, "'On many worlds, the Fall of the Aeldari is REENACTED IN MICROCOSM as society "
               "collapses and the howling winds of Chaos ravage the world through the minds of "
               "its psykers' -- it repeats its own birth on a planetary scale, repeatedly"),
   transgression=(8.5, "Rewrites what a person wants, which is upstream of what they do"),
   sustain=(8.5, "Excess renews itself, but burns its hosts out faster than the other three"),
   vector=(8.0, "Reaches wherever sensation is, and takes the Aeldari dead wherever they go"),
   volition=(7.5, "Wants without limit and without direction"),
   acumen=(7.5, "'A widespread and technologically advanced conflict is particularly vulnerable "
                "to Slaanesh's influence as A SINGLE WELL-PLACED CONVERT can have the means to "
                "wreck a fleet or destroy an entire city' -- it understands leverage exactly"),
   discernment=(8.5, "Knows what everyone wants, including what they will not admit"),
   suasion=(9.5, "Converts by giving people precisely what they asked for"))),

 "The Emperor of Mankind": dict(
  anchor="M6", epoch="M41, ten millennia on the Golden Throne",
  presence="A galaxy, and no further -- which is the whole finding. The Astronomican, powered by "
           "His mind, has a 'reach said to be around 70,000 LIGHT YEARS, WHICH BY DEFAULT BECOMES "
           "THE MAXIMUM RADIUS OF ASTRONOMICAN-ASSISTED WARP-NAVIGABLE SPACE.' Every Imperial "
           "voyage in the setting happens inside a sphere His mind defines. That is a "
           "staggering presence and it has an EDGE, stated in light years. The Chaos Gods' "
           "presence has no edge because it is not a radius.",
  axes=dict(
   ruin=(7.0, "'Ordering the Ultramarines to destroy the Khurian city of Monarchia where the "
              "Emperor was worshipped as a god' -- a city erased to make a rhetorical point"),
   continuity=(9.0, "Ten thousand years dead and not dead, sustained on a failing machine. "
                    "Neither alive nor gone, and unkillable in either state"),
   celerity=(3.0, "Immobile for ten millennia. Whatever He was, He is now a fixed point"),
   reach=(8.5, "A 70,000 light-year psychic beacon -- the largest single stated radius in the "
               "setting"),
   transgression=(8.0, "'The Emperor planned to use the Golden Throne to enter and reshape the "
                       "labyrinthine dimension of the Aeldari Webway to serve as a direct and "
                       "instantaneous transport network' -- He set out to re-engineer a "
                       "dimension"),
   sustain=(6.0, "Failing, and known to be failing. The Throne degrades and the Imperium counts "
                 "the years"),
   vector=(4.0, "He goes nowhere. The Astronomican goes everywhere, and it is not Him moving"),
   volition=(9.0, "Ten thousand years of holding one position by will alone, with no body left "
                  "to hold it with"),
   acumen=(8.5, "'His advanced scientific knowledge which displayed an understanding of the "
                "universe on a primal level'; and He alone was entrusted with 'the Primordial "
                "Truth' by the Chaos Gods themselves"),
   discernment=(9.0, "He knew what the Chaos Gods were when nobody else in the species did"),
   suasion=(9.9, "CEILING. A trillion-fold state religion built on a man who explicitly forbade "
                 "it -- He destroyed a city to stop being worshipped and is worshipped by more "
                 "beings than any other entity in this library"))),
}


def compute():
    """PROVENANCE IS PER AXIS, AND WHERE IT IS UNKNOWN THIS SAYS SO RATHER THAN GUESSING.

    This stamped `"[wiki] " + v[1]` onto every worksheet line unconditionally (order
    1770c2b84786, the sibling of the defect fixed in `halo.py`). Several of these citations
    quote no page at all -- they are the assayer's reading, soundly argued and not transcribed --
    and labelling those wiki-verbatim beside the ones that really do quote the cache makes the
    tag decoration instead of evidence. A provenance mark applied to everything distinguishes
    nothing, and the reader who most needs it is the one asking whether a high score rests on a
    citation or on judgment.

    WHY THIS IS NOT THE WHOLE `halo.py` FIX. `halo.py` carries a per-axis `wiki`/`canon` tag in
    the ROSTER itself, and reaching that state here means deciding, for each axis of each entry,
    whether the sentence is quotation or paraphrase. That is a curatorial reading of the sources,
    not a mechanical edit, and inventing the answer would replace one false provenance claim with
    another -- a worse outcome, because the second would look deliberate.

    So both shapes are accepted. A 3-tuple carries its own mark, exactly as `halo.py` and
    `zfighters.py` do. A 2-tuple -- every entry here, today -- is marked `unattributed`, which is
    the true statement: nobody has recorded where this line came from. That removes the false
    claim now and leaves the gap VISIBLE for the curatorial pass, instead of hiding it behind a
    tag that reads as if the work had been done.
    """
    out = {}
    for name, rec in ROSTER.items():
        scores = {ax: v[0] for ax, v in rec["axes"].items()}
        sheet = {ax: "[" + _provenance(v) + "] " + v[1] for ax, v in rec["axes"].items()}
        res = A.assay(rec["anchor"], scores, attestation="Transcribed",
                      epoch=rec["epoch"], worksheet=sheet)
        out[name] = {"assay": res, "anchor": rec["anchor"], "host": HOST,
                     "epoch": rec["epoch"], "presence": rec["presence"],
                     "axes": {k: {"score": v[0], "cited": v[1], "provenance": _provenance(v)}
                              for k, v in rec["axes"].items()}}
    return out


def _provenance(axis_value):
    """The provenance tag for one axis entry. -> 'wiki' | 'canon' | 'unattributed'.

    Defaults to `unattributed` rather than to `wiki`, which is the whole point: the old default
    asserted something nobody had checked, and this one asserts only what is on record.
    """
    if len(axis_value) >= 3 and axis_value[2]:
        return str(axis_value[2])
    return "unattributed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    a = ap.parse_args()
    out = compute()
    rank = sorted(out.items(),
                  key=lambda kv: -(A.LADDER.index(kv[1]["assay"]["magnitude"])
                                   + kv[1]["assay"]["decimal"]))
    print("=" * 78)
    print("WARHAMMER 40,000 -- BY MAGNITUDE (presence thesis)")
    print("=" * 78)
    for n, rec in rank:
        print("  %-24s %-16s %s" % (n, rec["assay"]["moth_number"], rec["anchor"]))
    if a.full:
        for n, rec in rank:
            print("")
            print("=" * 78)
            print("%s   %s" % (n, rec["assay"]["moth_number"]))
            print("=" * 78)
            print("  " + rec["presence"])
            print("")
            for ax in A.WEIGHTS:
                d = rec["axes"][ax]
                print("   %-15s%5.1f  %s" % (ax, d["score"], d["cited"][:56]))
    # ATOMIC, for the same reason and by the same hand as `zfighters.py:478`. That file is this
    # one's twin -- same shape, same job, same `main()` ending in a hand-built assay dump -- and
    # it was made atomic as "the m100 tail" on 2026-08-25 while this line was left standing. The
    # sibling one module over is the shape lesson 14 exists for: the ruling was made, applied
    # where someone was already looking, and the identical construction next door was never
    # opened. `data/WH40K_ASSAYS.json` is consumed like its twin, so a crash mid-write hands a
    # reader a truncated file. (run #27)
    silence.write_json(OUT, out, indent=1, ensure_ascii=False)
    print("")
    print("-> " + OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
