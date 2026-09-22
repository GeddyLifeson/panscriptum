# Ròdais — the Gaelic of Rodos

The owner's constructed language for the island of Rodos: a Gaelic dialect with Scottish Gaelic
grammar and vocabulary, spelled with Irish consonants (*sc* for Scottish *sg*) and Scottish vowels
(grave accents, never acute). It began as a naming layer for an Azgaar map. This folder now holds
the whole language and the finished map.

## Files

| File | What it is |
|---|---|
| `NAMING_LAYER.md` | The original reference sheet: lenition, broad/slender agreement, place-name generics, the peoples. Errata at the end. |
| `GRAMMAR.md` | The full grammar: spelling, mutations, articles, nouns, adjectives, pronouns, prepositional pronouns, verbs (regular, the ten irregulars, *bi*), the copula, particles, word order, numbers, time. |
| `rodais_engine.py` | The rules as code: `normalize`, `lenite`, `check_agreement`, `attach_suffix`, `article`, `possessive`, `Verb` / `IRREGULAR` / `BI`, `verb_phrase`, `clause`, `copula`, `prep_pronoun`, `object_particle`, `number`, `place_name`, `substrate_name`. `python rodais_engine.py` runs its 108-check self-test. |
| `LEXICON.json` | 5,005 entries keyed by English, graded A1 to C2: headword, part of speech, gender and plural for nouns, root for verbs, a literal gloss for idioms. |
| `LEXICON.md` | The same lexicon as a readable Ròdais–English dictionary. |
| `TEXTS.json`, `TEXTS.md` | Four everyday conversations and six tales with line-by-line English. Three tales are real Gaelic traditions moved to Rodos (the selkie wife, the each-uisge, Fionn and the salmon); three are Rodos legends (the Seann-Dhaoine leaving, coal coming into the blood, the Tuathaich going north). None of the story's named characters appear. |
| `Rodos_renamed.map` | The map as the first pass left it (the input). |
| `finish_map.py` | Finishes the renaming, deterministically, through the engine. |
| `Rodos_finished.map` | The finished map. Open it in Azgaar's Fantasy Map Generator. |
| `MAP_CHANGES.md` | Every name `finish_map.py` changed, before and after (425 changes). |
| `check_rodais.py` | Runs every check in the folder: the engine self-test, lexicon completeness and spelling, the texts, and the map. |

## What the map pass fixed

The first pass renamed the burgs, rivers and provinces in the map data. It left:

- **The labels drawn on the map.** The 52 burg labels saved in the SVG still read *Luteley,
  Salington, Whitford…*, and the state label read *City-State Rodos*. Azgaar shows the saved
  labels on load, so the map opened with the old English names. They now match the data.
- **Seann Shkell and Seann Dhunn.** See the errata in `NAMING_LAYER.md`: *Seann Skell, Seann
  Dunn, Seann Tarr, Seann Toll*, carried into the provinces named after them.
- **Everything else in English:** the ocean, the main island (now *Ròdos*), 12 small islands and
  the lake; the 10 religion entries and 9 deities; the war (*An Cogadh Fada*); 13 regiments and fleets; 48 markers; 236 named routes;
  5 zones; the quest journey. The English notes now name places that exist on the map.

Descriptive notes, biome names, trade goods and unit types stay in English, the same line the
first pass drew: names are Ròdais, UI text is not.

## Running it

```
python rodais_engine.py      # 108 checks
python finish_map.py         # Rodos_renamed.map -> Rodos_finished.map + MAP_CHANGES.md
python check_rodais.py       # everything; exits non-zero on any failure
```

Nothing here is under `src/`, so none of the library's daemons, audits or linters pick it up.

## Limits, stated plainly

- **The Gaelic is AI-written.** The grammar follows standard Scottish Gaelic grammars and the
  engine's forms are checked against known forms, but the lexicon and texts have not been
  reviewed by a Gaelic speaker. Each of the ten lexicon batches flagged up to 15 entries it was
  unsure of, mostly modern or technical words that are coinages or paraphrases rather than
  established terms. Treat C1/C2 technical vocabulary as a draft.
- **465 headwords are shared by more than one English entry** (*uisce* for both "water" and
  "rain", *iasc* for fish as food and as animal). That is how Gaelic works; the lexicon does not
  invent distinctions it doesn't have.
- **The map was checked structurally, not in Azgaar.** Every rewritten section parses, every
  label matches its burg, and no old name survives, but the file has not been opened in the
  generator from here (the session had no network access to it).
- **No recordings.** No speech engine reachable from here speaks Scottish Gaelic.
