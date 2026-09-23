# The legendarium of Rodos

The whole record of the island in the spirit of *The Silmarillion*, *The Hobbit*, *The Lord of the Rings* and its
Appendices: a prose book for each of the five ages, dated annals of every event, appendices (rulers and houses,
faiths, hosts and wars, the reckoning of years, words born from history, tongues and peoples, goods and markets,
shires, land and waters, arms), and a gazetteer of every town on the map. Every event has a day, a month and a year.

Read it in the **Rodos Atlas** (`../Rodos_Atlas/`), where the annals, the book and the live map are wired
together, as a printed book in `../The_Rodos_Legendarium.pdf`, or as plain text in `LEGENDARIUM.md`.

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
| `appendices/*.md`, `appendices/houses.json` | The appendices, A–J: rulers, faiths, hosts and wars, the reckoning, words, tongues and peoples, and (from the layer reconciliation) G goods and markets, H shires, I land and waters, J arms. The houses' people are dated by the builder. |
| `gazetteer/out_*.json` | Every burg: founding age, founders, history, what it is known for. `CONSISTENCY_LOG.md` records the checks against the map. |
| `burg_features.json`, `burg_features.py` | Every burg's town features (citadel, walls, plaza, temple, shanty), each with its reason from the gazetteer, annals or appendices, and `"port": 0` for the 72 burgs whose map cell lies inland with no haven (Watabou would otherwise draw a sea on a random side). Azgaar builds each town's plan link to Watabou's generators from these flags. `python burg_features.py` writes them into `../Rodos_finished.map`, `../Rodos_Atlas/Rodos.map` and `world.json`: the burgs record, the saved anchor icons of the cleared ports, and a town plan for the fort group in the settings, and nothing else. `../finish_map.py` applies them too. |
| `burg_moves.json` | The 29 harbour towns whose map cell lay inland, moved to the nearest free shore cell with a haven in their own province and state (24 on the sea, 5 on the freshwater lake by the capital) (old and new cell and position, the port's water, the distance in cells). `burg_features.py` applies it as Azgaar's burg editor relocates a burg: position, cell, the cells' burg record, the port, and the icon, label and anchor in the saved SVG. |
| `route_extensions.json` | The 49 routes that ended where a moved town used to stand, carried on to its new cell: the points before and after, the cell links, and the path Azgaar draws for them. Applied by `burg_features.py`. |
| `reconcile/` | Every layer of the generated map read against the history: one proposal per layer (`religions`, `economy`, `state`, `military`, `land`, `markers_routes`, `heraldry` `.json`), each with what agreed, what conflicted, what was missing, and its `map_edits`, annals, gazetteer and text edits; `integration.json`, the integrator's own map edits and the proposal edits it sets aside; then `faiths.json` (the three faiths), `climate.json` (the latitude of an island between Ireland and Scotland, its mild temperatures, no glacier and no ice), `dubhan.json` (dubhan the traded fuel) `loose_ends.json` (the two routes cut into road and trail pieces) and `tales.json` (the tellings of the Old Faith read against the Gaelic tales: Macha's wood, the wood of the two horses); `INTEGRATION.md`, how the proposals were combined and every conflict decided. |
| `map_reconcile.py` | Applies every proposal's `map_edits` and `integration.json` to the map in a fixed order, byte-safe like `burg_features.py`, and derives what follows (the regrouped roads' saved paths, the cultures' rural totals). `python map_reconcile.py` updates `../Rodos_finished.map`, `../Rodos_Atlas/Rodos.map` and regenerates `world.json`; `../finish_map.py` calls it after the burg moves, so a rebuild from `../Rodos_renamed.map` reproduces the finished map. |
| `town_previews.json` | Every burg's town-plan link (Watabou's City or Village Generator), as the Atlas's own Azgaar builds it from the map. The forts get a citadel town with no walls or square. |
| `build_book.py` | Assembles `LEGENDARIUM.md`; `../build_atlas.py` uses it for the Atlas. |
| `build_pdf.py` | Typesets `LEGENDARIUM.md` as a book, `../The_Rodos_Legendarium.pdf` (WeasyPrint; fonts in `fonts/`, OFL). |

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
python build_pdf.py      # -> ../The_Rodos_Legendarium.pdf (pip install weasyprint markdown)
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
