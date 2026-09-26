# eras/: the seven era legendaria

Each of the seven ages of Dia-thìr has its own volume, a novel of 600-odd pages in the house design of the master
`legendarium/The_Diathir_Legendarium.pdf`, covering that age alone. The master record in `legendarium/` stays the
single source of every master event and its date; the era volumes add to it and never contradict it. Writers work
from `WRITERS_GUIDE.md`; this file is for whoever builds, checks or maintains the set.

| Key | Volume | Era | PDF |
|---|---|---|---|
| I | The Ancient Age | VE | `age_I/The_Diathir_Legendarium_Ancient_Age.pdf` |
| II | The Age of Ailean | GE | `age_II/The_Diathir_Legendarium_Age_of_Ailean.pdf` |
| III | The Holy Age | FE | `age_III/The_Diathir_Legendarium_Holy_Age.pdf` |
| IV | The Age of Sundering | LE | `age_IV/The_Diathir_Legendarium_Age_of_Sundering.pdf` |
| V | The Age of Strangers | AE | `age_V/The_Diathir_Legendarium_Age_of_Strangers.pdf` |
| VI | The Age of the Kingdom | SE | `age_VI/The_Diathir_Legendarium_Age_of_the_Kingdom.pdf` |
| VII | The Age of Dubhan | DE | `age_VII/The_Diathir_Legendarium_Age_of_Dubhan.pdf` |

## Layout

```
eras/
  README.md            this file
  WRITERS_GUIDE.md     the writers' contract: files, dates, links, names, tokens, size, geography
  build_era.py         builds one age (or all): dated annals, atlas.json, LEGENDARIUM.md, the PDF
  check_era.py         validates one age (or all); --final also holds the size targets
  NAMES.json / .md     every proper noun's Dia-thìris form (the single source; NAMES.md is the readable table)
  PEOPLE.json          every person of the annals and of the ages' plans: id, name, first/last attestation, kin
  THREADS.json         the Atlas's storylines; every "threads" id in any annals or events file is listed here
  RULERS.json          every ruler's birth, accession, death and ages, and the curve of the long years
  master_links.json    written by the build: the master events with the era events that link to them
  POP_LOG.md, RESCALE_LOG.md   the owner's population and map-scale decisions and what changed with them
  maps/, engine/, specs/, specs_draft/   the per-age Atlas maps and the engine that makes them
  quality/             the checks and conversion tools (below), their allow-lists and logs
  age_<K>/
    PLAN.md, PLAN_names.json, PLAN_people.json   the lead's plan of the volume: chapters, new names, people
    annals/age_<K>_master.json   the age's master events, copied from legendarium/annals/age_<K>.json (--seed)
    annals/age_<K>_NN.json       the era annals: {"writer": N, "span": [FROM, TO], "events": [...]}  SOURCE
    book/*.md                    the Books (the novel), in file-name order                              SOURCE
    gazetteer/*.json             the towns as they stood in the age                                     SOURCE
    appendices/*.md              the volume's appendices                                                SOURCE
    places.json, front.json      (some ages) places not on the master map; the epigraph                 SOURCE
    events/NN.json               the chapter writers' event sidecars: DRAFTS, not read by the build
    annals_dated.json, atlas.json, LEGENDARIUM.md, *.pdf     written by build_era.py; never edit by hand
```

### The annals are the source; events/*.json are drafts

Each chapter writer handed in, beside the chapter, a sidecar `events/NN.json` (title, summary, era_year, people,
places, threads, master_links). Each age's lead compiled those into the annals files with a one-off script of their
own (seven scripts, one per age, kept outside the repository), then ran `quality/names_convert.py` over the result
and fixed by hand. Those scripts are not kept here and cannot be folded into one: they carry per-age patch tables
(renamed or dropped events, forced placements, same-day runs, people maps, extra events written by the lead) and
every age was edited after compiling (names put in Dia-thìris, dates and links corrected, events moved between
gaps). A recompile would undo all of that. So:

- **`annals/age_<K>_NN.json` is the source of truth** for the era annals. Edit it directly. The build never reads
  `events/`.
- **`events/*.json` are drafts**, kept for the record of what each chapter writer proposed. They do not match the
  annals entry for entry: I 539 sidecar events against 739 annals entries, II 602/620, III 512/553, IV 557/557,
  V 589/522, VI 561/561, VII 720/646. They have been put through `names_convert.py` too (title and summary), so
  they carry the same Dia-thìris forms as the annals, but nothing checks them and no tool compiles them.
- Do not write a compiler that regenerates the annals from the sidecars.

## Building

```
cd eras
python3 build_era.py IV              # one age: date the annals, write annals_dated.json, atlas.json, LEGENDARIUM.md, the PDF (~1 min)
python3 build_era.py IV --no-pdf     # the same without the PDF (seconds)
python3 build_era.py all             # every age
python3 build_era.py IV --seed       # re-copy annals/age_IV_master.json after the master record changes
```

The build copies every master event with exactly the date `legendarium/annals_dated.json` gives it. Master events
cut the age into gaps; each era event is dated only inside the gap it stands in (after its `{"after": M}` marker, or
the start of its file's span), so an era event can never move or pass a master event. `build_era.py` asserts that
on every run.

After a change to the master record, rebuild the master first, then the ages, then the Atlas:

```
cd legendarium && python3 reckoning.py && python3 build_book.py && python3 build_pdf.py
cd .. && python3 check_rodais.py                                   # ALL CHECKS HOLD
cd eras && for K in I II III IV V VI VII; do python3 build_era.py $K; python3 check_era.py $K --final; done
cd .. && S=<scratch dir>; rm -rf $S/fmgbuild; cp -r Diathir_Atlas/fmg $S/fmgbuild; python3 build_atlas.py $S/fmgbuild
```

`build_atlas.py` reads every `age_<K>/atlas.json`, so the Atlas carries each age's era events and switches between
the seven era maps.

## Checks

| Command | What it holds |
|---|---|
| `python3 check_era.py K [--final]` | seed and master dates; ids in their writer's block; categories, link types and targets; threads, people and told_in; tokens; places and gazetteer burgs; Dia-thìris spelling; forbidden words; nothing ahead of the age (future_check); rulers' ages (ages_check); size (with `--final`, the lower bounds fail) |
| `python3 quality/names_check.py K` | English left where NAMES.json (or the age's PLAN_names.json) gives a Dia-thìris form, misspelt Dia-thìris names, registry forms that normalize() would change. Must end `TOTAL english 0, misspelt 0` |
| `python3 quality/future_check.py K` | the owner's no-foreshadowing rule, alone (check_era runs it) |
| `python3 quality/ages_check.py K` | the rulers' ages rule, alone (check_era runs it) |
| `python3 quality/dates_check.py K` | every era event against the master events it is tied to: its era_between inside its gap, a `cause` link no later than its target, a `sequel`/`legacy`/`answers`/`fulfils` link no earlier. Counts and outliers |
| `python3 quality/tells_scan.py K` | machine-sounding prose (the tells of TELLS_FOR_WRITERS.md) |
| `python3 quality/era_policy.py` | writes `quality/ERA_DASHBOARD.md`, one table of every age |
| `python3 ../check_rodais.py` | the master record and everything built from it |

`quality/names_convert.py K` is the tool that puts English proper nouns into Dia-thìris across an age's writer files
and its `events/` sidecars (`--dry` first; every run is appended to `quality/names_convert_K.log`). Re-running it over
a finished age changes nothing: the forms a lead kept in English on purpose are listed in its `KEEP_IN`, and forms
that are names in one age only (Age VII's "the Board") in `NAMED_IN`. "The Keeper" is decided by `keeper_sense()`:
the spirit Coimhdeach na Fine in Age I, the Hall's office Coimheadaiche na Lasrach in Age III, and elsewhere
whichever the words of its sentence point to; a sentence that points neither way is left and logged as LEFT for a
reader. Checked against every form the leads wrote by hand (214 in all), it chooses wrongly none and leaves 2.

## The owner's rules (permanent canon)

- **It reads like a novel.** Each volume is one novel in a series, read front to back: connected narrative, people,
  scenes and speech in the high recollection voice of the master Books, not an encyclopedia. Each volume opens where
  the last closed. The Atlas may jump about; the book may not (no forward cross-references, no "see also").
- **No foreshadowing.** A volume speaks only of its own age and what came before it: no later names, eras, dates,
  towns, people or events, no "ages later", "was to become", "would later". An era annals entry looks no further
  than its own day. `future_check.py` enforces it.
- **Page breaks.** Every chapter of an era novel opens on a new page, grouped under its Parts (build_pdf.py's
  `.opener.chap`), with space above and no running head over the chapter title.
- **Names in Dia-thìris.** Every proper noun is in Dia-thìris, taken from NAMES.json: places, institutions, ages and
  eras, wars, peoples, titles used as names, gods, offices, laws, documents, orders, ships, feasts. The one exception is
  the humans' personal names, which stay as the humans wrote them. The build footnotes the English gloss at the first
  mention. Long vowels take the grave accent; sc not sg; caol le caol.
- **Rulers' ages are stated, and ages are ordinary after the Holy Age.** RULERS.json gives every ruler's birth,
  accession, death and ages. Ailean Mòr lived 4,626 years; his kin's long years shrink generation by generation and
  run out in the Holy Age. No one born in FE 1,200 or later, and no one outside the king's kin in any age, lives past
  95; the coal-blooded of the Age of Strangers on are the one exception, and they are not rulers. `ages_check.py`.
- **Geography and scale.** Dia-thìr lies alone in the Atlantic, west of the Outer Hebrides; the humans' homeland is
  east over the sea behind Manannan's mist, the one passage runs north-about, the Otherworld is west. The map is 0.14
  miles to the unit: about 154 miles from the north-western capes to the eastern cape, 72 north to south, some 5,340
  square miles. Travel 15–25 miles a day on foot, 10–15 by laden cart, 25 by carriage on a road, 20–30 by sail along
  the coast. See WRITERS_GUIDE.md §13 and RESCALE_LOG.md.
- **Population.** About 1.8 million in the present day (DE 27), a third in its 505 towns; at the close of each age
  roughly I 18,000, II 110,000, III 300,000, IV 570,000, V a million, VI 1.5 million, VII 1.8 million. A town in an
  older age is that age's share of its present size (III 0.035, IV 0.12, V 0.45, VI 0.85) unless the annals say
  otherwise. Deaths, crowds and musters must fit the place and the age. See POP_LOG.md.

## Shared registries

- **PEOPLE.json.** Every person named in an age's PLAN_people.json is here, and every id in an annals event's
  `people` list. `first` is the earliest attestation in time, the master record searched first (on the same day the
  master event wins): a master or era event that names the person, within their planned lifespan. It must be the
  earliest, not merely the earliest master event: future_check.py reads a person's age from `first`. `last` is the latest
  attestation. One person across several volumes has one id (Ailean Mòr is `ailean-mor` from Age I to Age III); two
  people who share a name get their own ids (`tormod-ruadh` of Age V and `tormod-ruadh-age-iii`). A person the
  annals never name has as `first` the first event of the chapter the plan introduces them in. Add people through
  the lead; merge into the file (re-read, add, never rewrite another age's entries).
- **THREADS.json.** Every thread id used in any `annals/*.json` or `events/*.json` must exist here with its
  Dia-thìris name, gloss, colour and description.

## Allow-lists

The checks let a hit stand only when an allow-list names it, each with its reason. Keep them tight: fix the text
first.

- `quality/names_allow.json` (names_check): per age, the chapter and section headings (their anchors are `told_in`
  targets and names_convert never touches them), a name's core used without its article as a common noun ("a Board
  carrier", "a red hall"), and the English common nouns that share a word with a name: the crossing (a ford, a
  voyage; not An t-Aiseag), the column and the pillar, the fleet, the mist, the chronicle, the slab, the black coal,
  the four houses, the Stone, the Cup, the Hall, the Keeper and the Keepers in the Holy Age, the wolf-sworn before FE
  2,843, and the volume's own appendices and annals. 108 rules: I 14, II 7, III 25, IV 21, V 25, VI 8, VII 8.
- `quality/future_allow.txt` (future_check): 272 lines, each a file, rule, matched text and the snippet that must be
  on the same line, for a name or person that looks later but is not (Ciorstaidh of Age III is not the Age V
  Ciorstaidh; old Griogair mac Aonghais of Age V is not the Age VI surveyor; the grove of Doire ghlas is older than
  the town).
- `quality/names_convert.py`: `COMMON` (English words converted only in the longer forms that pin them),
  `BAD_VARIANTS`, `KEEP_IN` and `NAMED_IN` (above).

## Known open items

- `quality/dates_check.py all` still reports link-order outliers in Ages I, III, IV, VI and VII (an event linked as
  the `cause` of a master event but dated after it, or a `sequel` dated before). Most are link types the chapter
  writers used loosely ("cause" for "caused by"); Ages II and V are clean. Fix them in the annals files, reading
  each, not by a blanket rewrite of the link types.
