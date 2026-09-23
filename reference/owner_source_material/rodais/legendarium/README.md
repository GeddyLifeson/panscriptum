# The legendarium of Rodos

The whole record of the island in the spirit of *The Silmarillion*, *The Hobbit*, *The Lord of the Rings* and its
Appendices: a prose book for each of the five ages, dated annals of every event, appendices (rulers and houses,
faiths, hosts and wars, the reckoning of years, words born from history, tongues and peoples), and a gazetteer of
every town on the map. Every event has a day, a month and a year.

Read it in the **Rodos Atlas** (`../Rodos_Atlas/`), where the annals, the book and the live map are wired
together, or as plain text in `LEGENDARIUM.md`.

## Files

| File | What it is |
|---|---|
| `BRIEF.md` | The writers' contract: sources of canon, the owner's characters (chronicle facts only), the ages, places by id, spelling. |
| `chronicle_canon.json`, `canon_by_age.json`, `canon_words_and_faiths.txt` | The owner's chronicle, the canon every other file defers to. |
| `world.json`, `PLACE_FACTS.txt` | The map (`../Rodos_finished.map`) as data: burgs, provinces, rivers, markers, zones, faiths, hosts; which town each marker, zone and host belongs to. |
| `annals/age_I..V.json` | The annals as written: events in order, each with its place on the map. No dates are typed by hand. |
| `CONTINUITY_LOG.md`, `renames.json` | The continuity pass across the five ages and the names it changed. |
| `albums.json` | The pool of release dates the reckoning draws on: 2,234 records by 139 artists (1,769 dated to the day), every one looked up on the web with its source. Built by `albums_src/build_pool.py` from the owner's own list of artists and our top 100 rock and metal artists (`albums_src/top100_rock_metal.json`, aggregated from seven published rankings by `albums_src/aggregate_top100.py`). |
| `kept_dates.json` | Dates the owner kept when the pool was rebuilt: the 18 events of the Stone Kings. |
| `reckoning.py` | Gives every event its day, month and year → `annals_dated.json`. |
| `book/age_I..V.md` | The prose of each age. |
| `appendices/*.md`, `appendices/houses.json` | The appendices; the houses' people are dated by the builder. |
| `gazetteer/out_*.json` | Every burg: founding age, founders, history, what it is known for. `CONSISTENCY_LOG.md` records the checks against the map. |
| `build_book.py` | Assembles `LEGENDARIUM.md`; `../build_atlas.py` uses it for the Atlas. |

## How the dates are made

Writers never choose dates; they choose order, and a window (`"between": [from, to]`) when an event must fall in a
stretch of years. `reckoning.py` then dates every event in the order written:

- The chronicle's own years stay fixed, and its full dates stay whole (11 an Giblean 2020, 10 an Dùbhlachd 2021).
- Events between fixed points are spread evenly, aiming at the middle of any window.
- The **year** is built from three album release years, then the **month** and **day** from other albums:
  `year = first year of the age + (100 × ((yy(A) + yy(C)) mod 100) + yy(B)) mod (length of the age)`, with no year 0.
- Which albums make which date is not recorded.
- `within: [ID, N, M]` holds an event N (and at least M) years after an earlier one, so a person's acts fall within a
  human life and "the following year" means it; `same_day`, `eve` (or `eve: N` days) and `first_of_year` pin days.
  `TIMING_LOG.md` lists every such constraint and the phrase it honours.

In the books and appendices, dates are references, never typed: `{{date:IV-0157}}`, `{{year:IV-0157}}`,
`{{reckon:A:B:KEY}}` for a day the reckoning makes in a window (births and deaths, foundings), and `{{place:burg:19}}`
for a place, which the Atlas links to the map. If the annals are re-dated, the whole record follows.

```
python reckoning.py      # annals/*.json -> annals_dated.json
python build_book.py     # -> LEGENDARIUM.md
python ../check_rodais.py
```

## Limits, stated plainly

- The album release dates come from memory, not a checked discography; no music database was reachable from
  where this was built. They only seed the reckoning, and the reckoning holds whatever they give it to the
  chronicle's fixed years and to the order of events, so a wrong release date changes a day but never the history.
- The prose and appendices are AI-written against the canon. The owner's own characters appear only in what the
  chronicle already says of them.
- Two tensions sit inside the canon itself and are left standing (see `CONTINUITY_LOG.md`): the Stone Kings of the
  Ancient Age against "centuries before anything like a king", and the failed vein search placed in two ages.
