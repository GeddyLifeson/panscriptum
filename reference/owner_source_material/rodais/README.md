# Dia-thìris and the Dia-thìr Atlas

The owner's constructed language for the island of Dia-thìr and the island's map and history. There are
two things here:

1. **The language: `DIATHIRIS.html`.** Open it in any browser. **Book** has the sounds, the grammar in
   brief, word forms, sentences, the naming sheet, and texts with English beside them. **Dictionary**
   has 21,285 entries covering 19,518 English words, searchable from either language. Every word among
   the 18,500 most frequent in English is in it, unless it is a name, an abbreviation or not English. Dia-thìris is a Gaelic dialect with
   Scottish Gaelic grammar and vocabulary, spelled with Irish consonants (*sc* for Scottish *sg*) and
   Scottish vowels (grave accents, never acute), and it takes the older word wherever Gaelic has two.
2. **The map, timeline and history: `Diathir_Atlas/`.** Double-click `Diathir Atlas.bat` (or run
   `python atlas.py`). It opens in your browser with three tabs: **Annals** (all 1,515 dated events,
   filter by age, search), **Map** (Azgaar's Fantasy Map Generator itself, running the Dia-thìr map) and
   **Book** (the legendarium: six prose ages, appendices, a gazetteer of all 505 towns). An event's
   map button flies to where it happened; clicking a town shows its history; every place named in the
   book opens the map. Needs only Python 3.7+.

Everything else in this folder is the source for one of those two.

## The language: sources

| File | What it is |
|---|---|
| `DIATHIRIS.html` | The language book (built by `build_language.py` from the files below and `language_template.html`; needs `pip install markdown`). |
| `PHONOLOGY.md` | The sound system in full: consonant and vowel inventories with IPA (broad/slender, fortis/lenis, pre-aspiration, tense/lax sonorants), allophony, syllable structure, the helping vowel, stress and intonation, the sounds of the mutations, every spelling-to-sound rule, a key for English speakers. Where dialects differ Dia-thìris takes the older sound. |
| `GRAMMAR.md` | The grammar in brief: spelling, mutations, articles, nouns, adjectives, pronouns, verbs, the copula, word order, numbers, time, and how Dia-thìris names new things (§13). |
| `GRAMMAR_MORPHOLOGY.md` | Word forms in full: mutations, the article, noun declensions with full paradigms, adjectives, pronouns and prepositional pronouns, every verb form of the regular and irregular verbs, the copula, numerals, derivation, kennings. |
| `GRAMMAR_SYNTAX.md` | Sentences in full: clause types, aspect, particles, questions and commands, the passive, possession and modality, relative and subordinate clauses, reported speech, the noun phrase, discourse, sample texts; 312 glossed examples. |
| `NAMING_LAYER.md` | The original reference sheet: lenition, broad/slender agreement, place-name generics, the peoples. |
| `TEXTS.json`, `TEXTS.md` | Four everyday conversations and seven tales with line-by-line English. |
| `LEXICON.json` | The dictionary data: 21,285 entries. Each has the headword, part of speech, gender, genitive and plural for nouns, root and verbal noun for verbs, the pronunciation in IPA, and a level: A1–C2 for the original teaching vocabulary, F1–F16 for the frequency band of the English word (F1 = the thousand most common). 1,634 are kennings, old-root compounds for new things (*inntinn-iarainn*, "iron-mind", for computer), each with its literal sense and the Scottish Gaelic word it replaces. |
| `LEXICON.md`, `LEXICON_EN.md` | The dictionary as text, Dia-thìris–English and English–Dia-thìris. |
| `lexicon_batches/` | How the dictionary was extended past the original 5,005 entries: the frequency-ranked word lists (`in_NN.json`), the translated batches (`out_NN.json`), the translators' brief, the batch checker, the consistency audit (`audit.py`, `audit_patch.json`) and `merge_lexicon.py`, which rebuilds `LEXICON.json`, `LEXICON.md` and `LEXICON_EN.md` from `LEXICON_5005.json` and the batches. |
| `rodais_engine.py` | The rules as code: `normalize`, `lenite`, `check_agreement`, `article`, `possessive`, `Verb` / `IRREGULAR` / `BI` (every tense, the impersonal, the imperative in all persons), `verb_phrase`, `clause`, `copula`, `prep_pronoun`, `number`, `place_name`, `pronounce` (spelling to IPA). `python rodais_engine.py` runs its 261-check self-test. |

## The Atlas: sources

| File | What it is |
|---|---|
| `Diathir_Atlas/` | The program (see above). Built by `build_atlas.py`. |
| `legendarium/` | The history: the dated annals, the six prose books, the appendices A–J (among them G goods and markets, H shires, I land and waters, J arms), the gazetteer, the reckoning of years from album release dates (`reckoning.py`, `albums.json`, `albums_src/`), and the map's layers reconciled with the history (`reconcile/`, applied by `map_reconcile.py`). `LEGENDARIUM.md` is the whole record as plain text. See `legendarium/README.md`. |
| `Rodos_finished.map` | The finished map. Open it in Azgaar's Fantasy Map Generator 1.153.1. |
| `Rodos_renamed.map`, `finish_map.py`, `MAP_CHANGES.md` | The map as the first renaming pass left it, the script that finishes the renaming through the engine (and then applies the town features, the harbour moves and the layer reconciliation from `legendarium/`), and every name it changed (425). |
| `build_atlas.py`, `atlas.py`, `atlas_template.html`, `atlas_style.css` | Rebuild `Diathir_Atlas/` from an Azgaar build, the map and the legendarium (instructions at the top of `build_atlas.py`). |

| Both | |
|---|---|
| `check_rodais.py` | Runs every check in the folder: the engine self-test, the dictionary's completeness and spelling, the texts, the map, and the legendarium (every event dated and in order, every reference resolving). |

## What the map pass fixed

The first pass renamed the burgs, rivers and provinces in the map data. It left:

- **The labels drawn on the map.** The 52 burg labels saved in the SVG still read *Luteley,
  Salington, Whitford…*, and the state label read *City-State Dia-thìr*. Azgaar shows the saved
  labels on load, so the map opened with the old English names. They now match the data.
- **Seann Shkell and Seann Dhunn.** See the errata in `NAMING_LAYER.md`: *Seann Skell, Seann
  Dunn, Seann Tarr, Seann Toll*, carried into the provinces named after them.
- **Everything else in English:** the ocean, the main island (now *Dia-thìr*), 12 small islands and
  the lake; the 10 religion entries and 9 deities; the war (*An Cogadh Fada*); 13 regiments and fleets; 48 markers; 236 named routes;
  5 zones; the quest journey. The English notes now name places that exist on the map.

Descriptive notes, biome names, trade goods and unit types stay in English, the same line the
first pass drew: names are Dia-thìris, UI text is not.

## Running it

```
python rodais_engine.py      # 261 checks
python lexicon_batches/merge_lexicon.py   # rebuild the dictionary from the batches
python build_language.py     # -> DIATHIRIS.html
python finish_map.py         # Rodos_renamed.map -> Rodos_finished.map + MAP_CHANGES.md
python check_rodais.py       # everything; exits non-zero on any failure
```

Nothing here is under `src/`, so none of the library's daemons, audits or linters pick it up.

## Limits, stated plainly

- **The Gaelic is AI-written.** The grammar follows standard Scottish Gaelic grammars and the
  engine's forms are checked against known forms, but the lexicon and texts have not been
  reviewed by a Gaelic speaker.
- **New things: loans from about 1800, kennings for coinages.** Things known before about 1800
  take old native words; later things may be plain loans (*bus, rèidio*); where Scottish Gaelic
  coined a word, Dia-thìris has its own kenning from old roots (GRAMMAR.md §13). A Scottish Gaelic
  speaker would not know the kennings, which is the point.
- **465 headwords are shared by more than one English entry** (*uisce* for both "water" and
  "rain", *iasc* for fish as food and as animal). That is how Gaelic works; the lexicon does not
  invent distinctions it doesn't have.
- **The map is checked in Azgaar itself.** `Rodos_finished.map` loads in Fantasy Map Generator
  1.153.1 (the version that saved it) with no data errors. Keep `.gitattributes` in this folder:
  a `.map` file is CRLF-separated records around an SVG with LF newlines, and any line-ending
  conversion breaks it.
- **No recordings.** No speech engine reachable from here speaks Scottish Gaelic.
