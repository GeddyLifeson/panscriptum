# Lexicon batches — translators' brief

Ròdais is getting a dictionary of the 16,000 most common English words (ranked by the `wordfreq`
frequency list, lemmatized). 2,749 of them are already in `../LEXICON.json`; the other ~15,600 are
split into `in_01.json` … `in_22.json`: `[{"rank": 57, "en": "people"}, ...]` (rank 1 = most common).
You translate one batch into `out_NN.json` and check it with `python validate_batch.py out_NN.json`.

## Read first

- `../README.md`, `../GRAMMAR.md` (all of it, and §13 on naming new things), `../NAMING_LAYER.md`.
- `../LEXICON.json`: the existing 5,005 entries. **Reuse its choices**: if a word you are translating
  (or its root) already has a Ròdais form there, use the same one so the dictionary agrees with
  itself (`grep -i '"en": "word' ../LEXICON.json`, or search by the Ròdais form).
- `../rodais_engine.py`: `normalize()`, `check_agreement()`, `lenite()`.

## What Ròdais is

Scottish Gaelic grammar and vocabulary, in Ròdais spelling: **grave accents only** (never acute),
**sc for Scottish sg** (*uisce*, *scoil*, *loisc*). Write the standard Scottish Gaelic word, then
put it through `normalize()`. Where Scottish Gaelic has a well-established native word, use it.

**New things: loans from 1800 on are fine, coinages are Ròdais's own (owner's rule).** The humans
arrived around 1780, so a word Gaelic *borrowed* from English/Scots for a thing that came in from
~1800 on is a real Ròdais loan: keep it, in Ròdais spelling (plain loans like *bus*, *tacsaidh*,
*rèidio* stay; *bàta-smùide* "steam-boat" is a coinage, so it is replaced). But where Scottish Gaelic uses a *coinage* (a compound
or calque made up for the new thing), Ròdais makes its own compound instead, built from the
**oldest known synonym** of each part (skyscraper → *suathaiche-nèimh* "heaven-grazer"; computer →
*inntinn-iarainn* "iron-mind"; jet lag → "travel-drowsiness"). Such an entry has `"kenning": true`,
`"lit"` (the literal English of the compound) and `"scots"` (the Scottish Gaelic word it replaces).
Look at the 609 existing kennings (`"kenning": true`) and match their style.

## It must feel OLD (the owner's rule)

Ròdais should feel like old Irish / Scottish Gaelic, not modern broadcast Gaelic. When choosing a
word:

- For things that existed before 1800, prefer the **old native Gaelic word** over a borrowing from
  English or Scots (old loans like *eaglais*, *leabhar* are fine). Loans for things that came in from
  1800 on are allowed (see above).
- Where Scottish Gaelic has both an everyday modern word and an older or literary one shared with
  Irish (the Classical Gaelic of the bards, c. 1200–1650), prefer the older one if it is still a
  real, recognisable word: e.g. *àrd-rìgh*, *filidh*, *cath* (battle), *laoch*, *dàn*, *slòigh*,
  *tìr*, *cèill*.
- Build kennings from the oldest known synonym of each part, as a medieval poet would have named the thing.
- Keep Scottish Gaelic grammar and the Ròdais spelling (grave accents, sc). Do not write Old Irish
  spelling; the old feel comes from word choice and kennings.
- Keep agreement with existing LEXICON.json choices.

## One entry per sense that matters

```json
{"id": "f-bank-n1", "en": "bank", "rank": 1234, "sense": "river bank", "pos": "n",
 "rod": "bruach", "g": "f", "pl": "bruachan", "gen": "bruaiche"}
{"id": "f-bank-n2", "en": "bank", "rank": 1234, "sense": "money institution", "pos": "n",
 "rod": "taigh-stòrais", "g": "m", "pl": "taighean-stòrais", "kenning": true,
 "lit": "store-house", "scots": "banca"}
{"id": "f-run-v", "en": "run", "rank": 300, "sense": "move fast on foot", "pos": "v",
 "rod": "ruith", "root": "ruith", "vn": "ruith"}
```

- `id`: `f-<english>-<pos><n>`, unique. `rank`: copy from the input. `sense`: a short English gloss.
- `pos`: n, v, adj, adv, prep, conj, pron, num, interj, det, part, phrase.
- Nouns: `g` (m/f), `pl` (plural, omit only for mass/abstract nouns), `gen` (genitive singular).
- Verbs: `rod` = the root (imperative 2sg), `root` = same, `vn` = verbal noun.
- Adjectives: `rod` = the plain form. Add `"comp"` (comparative, e.g. *nas motha* → give *motha*) where irregular.
- Give each word its main senses (1–3 entries); don't split hairs.
- Function words (the, of, would, that...) translate by their Ròdais equivalents, with a `sense`
  explaining the construction (e.g. "of" → *de* / genitive construction; "would" → conditional
  ending, `pos: "part"`, `rod: "-adh"`, sense "conditional mood of the verb").
- **Skip** what is not a common English word: personal names, place names, brand names,
  abbreviations, letters, non-English words, internet junk: `{"en": "harlan", "rank": 18002,
  "skip": "personal name"}`. A word that is also a common noun (e.g. "bill", "jack") is not skipped.
  Every input word must appear once in the output, either with entries or with a skip.

## Checks

`python validate_batch.py out_NN.json` must print 0 errors (warnings are for you to look at: fix a
caol-le-caol warning unless the word is genuinely irregular in Gaelic). The JSON must be one list.
Work in chunks of ~100 words, appending to the output, so nothing is lost if you are interrupted.
