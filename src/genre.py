#!/usr/bin/env python3
"""
GENRE — classify a source once, and let everything downstream follow from it.

THE OBSERVATION THIS IMPLEMENTS
-------------------------------
There are only so many kinds of story. Measured on the catalogue, the world-feature space is 432
cells (landform x climate x condition x era) and 1,165 catalogued worlds already occupy 382 of
them -- 88.4%. The space is nearly saturated, which means a new source almost never needs bespoke
work. It needs CLASSIFYING, and everything else is lookup.

THE ERROR THIS CORRECTS
-----------------------
The onomasticon's REGISTER decides a world's culture set and the sound of its names, and it was
being assigned by hashing the continuity group id -- an arbitrary number. The results were exactly
as good as that sounds:

    Alien + Doom                 -> liquid     the flowing, vowel-rich register. For xenomorphs.
    Cowboy Bebop + Sailor Moon   -> guttural   the harsh one. For jazz noir and magical girls.
    Pantheon: Greek + Roman      -> compact    the classical world, denied the classical register.

A hash cannot know what a source is about. A genre classifier can, because genre is a real
property of a body of text and is recoverable from it.

WHAT GENRE FIXES DOWNSTREAM
---------------------------
    register        -> culture set and naming (onomast.py, worldseed.py)
    world priors    -> what an UNATTESTED axis should fall back to. A post-apocalyptic source
                       should not seed a "thriving" world, and a mythological one should not seed
                       an "industrial" era. The seed still breaks ties; genre supplies the urn it
                       draws from.

That is the compositional payoff: classify once at the source, and a world's whole default profile
comes with it.
"""
import argparse
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import silence                                                           # noqa: E402

# Each genre: the vocabulary that identifies it, the naming register it implies, and the priors an
# unattested world axis should draw from. Weights let a strong signal ("xenomorph") outrank a weak
# one ("ship").
GENRES = {
    "mythology": dict(
        register="classical", cues={
            r"\b(god|goddess|deity|pantheon|titan|olympus|valhalla|myth|demigod|oracle|"
            r"temple|prophec|underworld|nymph|hero cult)\w*": 3,
            r"\b(zeus|odin|thor|ra|anubis|amaterasu|quetzalcoatl|brahma|shiva)\b": 5},
        priors=dict(landform="highland", climate="temperate", condition="settled",
                    tech="primitive")),
    "high_fantasy": dict(
        register="liquid", cues={
            r"\b(elf|elves|dwarf|dwarves|wizard|sorcer|arcane|spellbook|dragon|realm|"
            r"enchant|rune|druid|paladin|tavern|kingdom)\w*": 3,
            r"\b(magic|mana|artifact|quest|prophecy)\w*": 1},
        priors=dict(landform="continents", climate="temperate", condition="settled",
                    tech="medieval")),
    "grimdark": dict(
        register="guttural", cues={
            r"\b(daemon|heresy|xenos|grimdark|warp|inquisit|chaos god|blood god|"
            r"skull|corpse|damnation|abyss|torment)\w*": 4,
            r"\b(demon|hell|undead|necro|plague|curse|dread)\w*": 2},
        priors=dict(landform="highland", climate="volcanic", condition="wartorn",
                    tech="medieval")),
    "cosmic_horror": dict(
        register="sibilant", cues={
            r"\b(eldritch|elder god|unspeakable|madness|cyclopean|non[- ]euclidean|"
            r"xenomorph|hive|parasite|infest|mutat)\w*": 4,
            r"\b(horror|terror|nightmare|abomination|monstros)\w*": 2},
        priors=dict(landform="shattered", climate="volcanic", condition="ruined",
                    tech="industrial")),
    "space_opera": dict(
        register="sibilant", cues={
            r"\b(starship|hyperspace|warp drive|federation|empire|fleet|orbital|"
            r"interstellar|colony|terraform|cruiser|jump gate)\w*": 3,
            r"\b(space|planet|star system|alien|android|laser)\w*": 1},
        priors=dict(landform="continents", climate="arid", condition="settled",
                    tech="spacefaring")),
    "cyberpunk": dict(
        register="compact", cues={
            r"\b(cyber|netrunner|megacorp|implant|augment|neural|hacker|corpo|"
            r"neon|chrome|black ?ice)\w*": 4,
            r"\b(corporation|dystopi|surveillance|slum)\w*": 2},
        priors=dict(landform="continents", climate="temperate", condition="wartorn",
                    tech="industrial")),
    "post_apocalyptic": dict(
        register="guttural", cues={
            r"\b(wasteland|fallout|apocalyp|survivor|scaveng|irradiat|vault|"
            r"ruins? of|collapse|last of|remnant)\w*": 4,
            r"\b(mutant|raider|shelter|ration|infected)\w*": 2},
        priors=dict(landform="continents", climate="arid", condition="ruined",
                    tech="industrial")),
    "military_modern": dict(
        register="compact", cues={
            r"\b(battalion|platoon|insurgen|deployment|spec ?ops|rifle|artillery|"
            r"helicopter|convoy|briefing|task force)\w*": 3,
            r"\b(soldier|war|army|weapon|mission|combat)\w*": 1},
        priors=dict(landform="continents", climate="temperate", condition="wartorn",
                    tech="industrial")),
    "superhero": dict(
        register="compact", cues={
            r"\b(superhero|supervillain|secret identity|superpower|vigilante|"
            r"caped|nemesis|origin story)\w*": 4,
            r"\b(hero|villain|powers|mask|city)\w*": 1},
        priors=dict(landform="continents", climate="temperate", condition="settled",
                    tech="industrial")),
    "eastern": dict(
        register="long", cues={
            r"\b(shinobi|samurai|katana|sensei|yokai|kami|jutsu|shogun|dojo|"
            r"onmyoji|oni|senpai|chakra|ki blast)\w*": 4,
            r"\b(ninja|sword saint|clan|honor|spirit)\w*": 1},
        priors=dict(landform="isles", climate="temperate", condition="settled",
                    tech="medieval")),
    "whimsy": dict(
        register="liquid", cues={
            r"\b(candy|whimsic|silly|cartoon|talking animal|adventure buddy|"
            r"nonsense|goofy|slapstick)\w*": 4,
            r"\b(friend|fun|colorful|sweet|magic land)\w*": 1},
        priors=dict(landform="isles", climate="tropical", condition="thriving",
                    tech="magical")),
}

DEFAULT = dict(register="classical",
               priors=dict(landform="continents", climate="temperate",
                           condition="settled", tech="medieval"))


def classify_text(text, top=3):
    """Score every genre against a body of text. Returns ranked (genre, score)."""
    scores = collections.Counter()
    for g, spec in GENRES.items():
        for pat, w in spec["cues"].items():
            scores[g] += w * len(re.findall(pat, text, re.I))
    return scores.most_common(top)


def classify_source(rec, cap=None):
    """Classify one source from its own catalogued entries.

    Uses names and descriptions together: a source's vocabulary is what identifies it, and neither
    field alone is enough -- names carry the proper nouns, descriptions carry the idiom.

    [HARD RULE 0] `cap` was 120,000 characters and it was DECIDING ANSWERS. The scan walks
    `rec["entries"]` in stored order -- scrape order, nothing ranked -- so the cap did not sample
    a source's vocabulary, it read the front of it. Marvel holds 18,765,902 characters of names
    and descriptions: the cap read 0.64% of them and stopped.

    Measured over the whole corpus before this changed (210 records, capped vs uncapped):
    SEVEN sources answered differently once the whole text was read --
        Marvel                              post_apocalyptic -> mythology
        KibblesTasty (techno-psionic line)  grimdark         -> high_fantasy
        Bleach                              high_fantasy     -> eastern
        Yorviing's Arcane Grimoire          grimdark         -> high_fantasy
        Dr. Firestorm's Engineering Corps   military_modern  -> high_fantasy
        Crash Bandicoot                     mythology        -> grimdark
        Digimon                             eastern          -> cyberpunk
    These are not near-misses: Marvel scored 240 for post_apocalyptic off the truncated head and
    41,891 for mythology off the whole record. `genre` sets `register` and `priors`, so each of
    those seven was dressing its prose in a voice chosen by scrape order.

    The parameter survives so that no caller breaks, but a numeric value is now refused loudly
    rather than applied silently -- the same treatment `feats.discover`'s `extra` got. Uncapped
    costs ~77s on Marvel and is negligible on everything else; per Hard Rule 0 the answer to slow
    is more time, never a smaller universe. 2026-08-24.
    """
    if cap is not None:
        raise SystemExit(
            "genre.classify_source: `cap` truncates the entry list in STORED order and changed "
            "the answer for 7 of 210 sources (Marvel: post_apocalyptic -> mythology). "
            "Hard Rule 0 -- rank if you must, never truncate. Pass cap=None.")
    parts = []
    for e in rec.get("entries", []):
        parts.append(e.get("name") or "")
        parts.append(e.get("description") or "")
    ranked = classify_text(" ".join(parts))
    if not ranked or ranked[0][1] == 0:
        return {"genre": "unclassified", "score": 0, "confidence": 0.0,
                "register": DEFAULT["register"], "priors": DEFAULT["priors"], "runners_up": []}
    top, score = ranked[0]
    total = sum(s for _, s in ranked) or 1
    return {
        "genre": top,
        "score": score,
        # Margin over the runners-up. A source that scores 40 for grimdark and 38 for horror is
        # NOT confidently either, and the record should say so rather than pick.
        "confidence": round(score / total, 3),
        "register": GENRES[top]["register"],
        "priors": GENRES[top]["priors"],
        "runners_up": ranked[1:],
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
    print("GENRE — classify the source once, and the world defaults follow")
    print("=" * 100)
    dist = collections.Counter(v["genre"] for v in out.values())
    print(f"\nsources classified: {len(out)}")
    for g, n in dist.most_common():
        print(f"   {g:<20}{n:>4}")

    low = [(s, v) for s, v in out.items() if v["confidence"] < 0.45 and v["genre"] != "unclassified"]
    print(f"\nlow-confidence (genre is genuinely mixed, flagged not forced): {len(low)}")
    for s, v in low[:5]:
        ru = ", ".join(f"{g}:{n}" for g, n in v["runners_up"][:2])
        print(f"   {s[:30]:<32}{v['genre']:<18}{v['confidence']:.2f}   vs {ru}")

    print("\n" + "-" * 100)
    print("THE CASES THE HASH GOT WRONG")
    print("-" * 100)
    for s in ("Alien", "Doom", "Cowboy Bebop", "Sailor Moon", "Pantheon: Greek",
              "Pantheon: Roman", "God of War", "Warhammer 40,000", "all Fallout",
              "JoJo's Bizarre Adventure"):
        if s in out:
            v = out[s]
            print(f"   {s[:26]:<28}{v['genre']:<18}-> register {v['register']:<11}"
                  f"(conf {v['confidence']:.2f})")

    if args.write:
        p = os.path.join(HERE, "data", "GENRES.json")
        # ATOMIC. `GENRES.json` is read by `navtree.py` and `profile.py`; a truncate-then-fill
        # leaves it empty for the length of the write, and `profile.py:129-138` turns a failed
        # load into a silent `{}` fallback that produces a fully-populated, blanket-default
        # catalogue indistinguishable downstream from real data. The m100 tail, 2026-08-25.
        silence.write_json(p, out, indent=2, ensure_ascii=False)
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
