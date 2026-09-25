# Era map spec

`build_era_map.py` turns the master map (`Rodos_finished.map`) into one era's map. A spec is a JSON file that
says how the island stood at that moment.

```
python3 eras/engine/build_era_map.py eras/specs/age_3.json eras/age_3/Diathir_3.map --verify --shots /tmp/shots
```

## How the engine works

1. `serve.py` serves the RODAIS folder on 127.0.0.1. It uses the Atlas server's settings: a large request
   queue and keep-alive.
2. `driver.js` (Node + Playwright + Chromium) opens `Diathir_Atlas/fmg/index.html?maplink=<master>`, the
   generator itself. It waits for Azgaar's "Map is successfully loaded".
3. It injects `era_engine.js` and calls `EraEngine.apply(spec)`. The engine edits Azgaar's own live data
   (`pack.*`, `options.map.lore`). It recalculates everything that follows with Azgaar's functions:
   - **Statistics:** `States.collectStatistics`, `States.findNeighbors`, `States.getPoles`, `Provinces.getPoles`.
   - **Burgs:** `Burgs.remove`, `defineGroup`, `defineFeatures`, `defineEmblem`, `definePopulation`,
     `getType`, `getCloseToEdgePoint`.
   - **States, emblems, faiths:** `States.getFullName`, `States.defineTaxRates`, `Emblems.generate`,
     `Emblems.getShield`, `Religions.checkCenters`.
   - **Routes:** `Routes.remove`, `getPoints`, `getWaterPoints`, `getLandPathCost`, `getWaterPathCost`,
     `createWaterExitCheck`, `sync`.
   - **Everything else:** `Markers.getMarkerCoordinates`, `AddedLabels.add`, `Military.generate`, `getName`,
     `getEmblem`, `Markets.relocateMarket`, `removeMarket`, `addMarket`, `expandTerritories`,
     `Production.regenerateEconomy`, `Goods.sync`.

   Culture and faith statistics use the same rule as `collectStatistics`.
4. `Layers.drawAll()` redraws every active layer from the data: states, borders, provinces, cultures, religions,
   burg icons, labels (state labels are placed anew from the pole), routes, markers, zones, emblems, military.
5. Azgaar's own `Save.prepareMapData()` builds the .map text. It is imported from `fmg/save-*.js`, and it builds
   the text without a download. The driver writes that text to disk.

The master is only read. Randomness (a generated coat of arms, a new burg's population, generated regiments) is
seeded from the spec's `seed`, else its `name`, so the same spec gives the same map. The one exception is the
save date in the file's header, which Azgaar writes.

`--verify` opens the new map fresh in a new page by maplink and checks these things:
- page errors, error dialogs and Azgaar's `[Data integrity]` messages;
- the engine's own integrity check;
- the counts the spec asks for;
- that every land cell of each state's `shires` is in that state;
- that every layer draws.

It then saves the map again with `prepareMapData` and compares the result with the file (the round trip).
`--shots DIR` saves pictures of the states, cultures, religions, routes and provinces layers. The report is
written to `OUT.map.report.json`. It holds the warnings, the ids given to new elements, the counts and the
verification.

`mapinfo.py [MAP]` lists the ids a spec refers to: shires, burgs, routes, markers and so on.

## Conventions

- **Ids are the master's.** A removed burg keeps its slot with `removed: true`, as Azgaar does. Burg 19 is
  Cathair dhearg on every map, and a merged-away province keeps its id, marked removed. New elements get the
  next free id, and the report lists them.
- **`"@key"` references.** Any new element may carry a `"key"`. Anywhere an id is expected, `"@key"` refers
  to it. For example, `"capital": "@newtown"` or `"state:@east"` in `notes`.
- **Era place ids.** A new town declared in `eras/age_<K>/places.json` has the id 1000×K+n (4001 is Age IV's
  first). Give it in `burgs.add` as `"id": 4001`. Anywhere a burg id is expected, 4001 then means that burg,
  whatever Azgaar id it gets (`capital`, `routes.add.burgs`, regiments, markers, `notes` as `burg:4001`...).
  The burg also carries `"placeId": 4001` in the saved map, and the report's `placeIds` maps 4001 to the
  Azgaar id. Numbers of 1000 or more in a burg reference are always read as place ids; Azgaar ids stay below
  1000.
- **Shires** are the master's provinces (ids 1–123, `mapinfo.py`), read from the master's cells. They are
  the fixed unit for placing things, whatever the era's own provinces are.
- **Only land cells** (height ≥ 20) take a state, province, culture or faith, as on the master.
- A section left out means "as on the master". For lists, `keep` gives the master ids to keep; everything
  else is dropped. `remove` drops the listed ids and keeps the rest.
- Populations are in Azgaar's units: a burg's `population` is in thousands (8.6 = 8,600).
- Units follow `options.map.military.units`: `infantry`, `cavalry`, `riflemen`, `artillery` and `fleet`.

## Top level

| key | |
|---|---|
| `name`, `seed`, `comment` | Name, random seed, free comment. |
| `master` | The master map, relative to the spec (default `Rodos_finished.map`). |
| `lore` | `{name, description, calendar: {year, era, eraShort}}`, which is `options.map.lore`. |
| `units` | Merged into `options.map.units`, e.g. `{"distance": {"scale": 0.14}}` (the scale bar is redrawn from it). |
| `features` | `{rename: {featureId: name}}`: islands, lakes and the ocean. |
| `rivers` | `{rename: {riverId: name or {name, type, ...}}}` |
| `cultures`, `religions`, `burgs`, `states`, `provinces` | See below (applied in the order cultures, religions, burgs, states, provinces). |
| `diplomacy` | `[[a, b, relation, back?], ...]`. The relation is one of Ally, Friendly, Neutral, Suspicion, Enemy, Unknown, Rival, Vassal, Suzerain. `back` is the relation from b to a. It defaults to the same relation, except that Vassal and Suzerain answer each other. |
| `diplomacy_default` | The relation between states not listed (default `Neutral`). |
| `campaigns` | `[{name, start, end?, attacker, defender}]`, added to both states' campaigns. |
| `military` | `{regiments: {stateId: [regiment, ...]}}` (another way to give a state's regiments). |
| `routes`, `markers`, `zones`, `labels`, `economy`, `journeys`, `notes` | See below. |
| `rural_population` | `{scale: 0.4, shires: {"12": 0.8}}` multiplies the cells' rural population. |
| `layers` | `{active: [layer ids]}`: the layers switched on in the saved map (default: as the master). |
| `expect` | `{counts...}`: extra counts for `--verify` to check (e.g. `{"provinces": 40}`). |
| `land` | Not supported; see "Land and water". |

## cultures

```json
"cultures": {
  "edit":   {"1": {"name": "…", "color": "#…", "type": "Naval", "code": "Tu", "note": "…"}},
  "add":    [{"key": "gall", "name": "Gall-Ghàidheil", "base": 43, "color": "#9e6fce", "type": "Naval",
              "shield": "heater", "expansionism": 1, "code": "GG", "origins": [2], "center": 1234}],
  "assign": [{"culture": "@gall", "shires": [58, 60]}, {"culture": 1, "cells": [812, 813]}],
  "remove": {"1": 2}
}
```

- `edit` (alias `rename`: a string is the new name) sets any fields.
- `add` appends a culture. `base` is the name base (index in the namebases).
- `assign` applies in order. Each entry is a cell selector (see "Cell selectors").
- `remove` maps a culture to its replacement. Its cells, burgs, states and faiths move to the replacement,
  and the culture is marked removed.
- When any culture is assigned or removed, every burg takes the culture of its cell, unless the burg's own
  `culture` is given in `burgs`.

## religions

These work like cultures: `edit`/`rename`, `add`, `assign` (with `religion`) and `remove`.

```json
"religions": {
  "edit": {"3": {"name": "Eaglais nan Coigreach", "deity": "Crìosd", "form": "Monotheism"}},
  "add":  [{"key": "old", "name": "…", "type": "Folk|Organized|Cult|Heresy", "form": "Animism", "deity": "…",
            "culture": 2, "expansion": "culture", "expansionism": 1, "color": "#…", "code": "…",
            "origins": [0], "center": 2933}],
  "assign": [{"religion": "@old", "where_culture": 2}, {"religion": 1, "shires": [3, 7]}],
  "remove": {"3": 1}
}
```

A faith's centre is moved into its own cells (`Religions.checkCenters`).

## burgs

```json
"burgs": {
  "keep": [1, 3, 19],
  "remove": [44],
  "population_scale": 0.5,
  "edit": {"19": {"name": "…", "population": 3.2, "group": "town", "culture": 2, "type": "River",
                  "features": {"citadel": 1, "walls": 1, "plaza": 1, "temple": 1, "shanty": 0},
                  "coa": {…}, "note": "…"}},
  "add":  [{"key": "newwest", "id": 4001, "name": "Baile Ùr", "cell": 1085, "population": 6.5, "port": true,
            "group": "town", "features": {…}, "culture": 2, "coa": {…}, "note": "…"}]
}
```

- `keep` lists the master burgs that exist; the rest are removed. New era towns go in `add`, never in
  `keep`.
- `id` on a new burg is its era place id (see "Conventions"). `remove` drops more, or drops burgs
  without a `keep` list.
- `population_scale` multiplies every kept burg's population.
- A new burg needs a `cell` (land, with no burg on it) or `x,y`.
- `port: true` makes a new burg a port on the sea next to its cell, as Azgaar places ports.
- Anything left out is made the way Azgaar makes it: population, features, arms (from its state's arms)
  and group.
- The state of every burg is the state of its cell. Capitals are the states' `capital` burgs.
- A burg whose capital status or population changed has its group defined anew (`Burgs.defineGroup`),
  unless `group` is given. Groups: capital, city, fort, monastery, caravanserai, trading_post, town,
  village, hamlet.

## states

```json
"states": {
  "list": [
    {"key": "west", "name": "…", "form": "Monarchy", "formName": "Kingdom", "fullName": "Rìoghachd an Iar",
     "color": "#fc8d62", "capital": 489, "culture": 2, "type": "River", "expansionism": 1.1,
     "coa": {…} | "generate", "shires": [3, 7, 14], "cells": [55, 56],
     "military": [regiment, …] | "keep" | "generate",
     "campaigns": [{"name": "…", "start": 1190, "end": 1195, "attacker": "@west", "defender": "@east"}],
     "label": {"text": "…", "fontSize": 140, "pathPoints": [[x, y], …]}, "note": "…"},
    {"key": "mid", "base": 1, "capital": 19, "shires": […], "military": "keep"}
  ],
  "cell_state": {"812": "@west"},
  "default_state": "@mid",
  "chronicle": [],
  "neutral_name": "Neutrals"
}
```

- The list replaces all the master's states. State ids are 1, 2, 3… in list order (a given `id` must agree).
  A bare list may be given instead of `{"list": …}`.
- `base: N` starts from master state N (its arms, taxes, treasury, regiments and campaigns), and the fields
  given override it. `keep_label: true` also keeps its label.
- Territory: all land cells of the state's `shires`, then its `cells`, then `cell_state` overrides. Cells no
  state claims are neutral, unless `default_state` is given.
- A state's capital cell is always its own (with a warning if the shires said otherwise).
- `fullName` defaults to Azgaar's `States.getFullName`.
- Arms are generated when not given. Taxes come from `defineTaxRates`.
- A state with no `color` gets a colour its neighbours do not have.
- Neighbours, area, cells, burgs, urban and rural population, the pole (label anchor), the list of
  provinces, and diplomacy are all derived. State labels are placed by Azgaar unless `label` is given.
- Regiment: `{"name": "…", "burg": 19 | "cell": 3048 | "x": …, "y": …, "units": {"infantry": 900}, "naval": false,
  "icon": "⚔️", "note": "…", "bx": …, "by": …}`.
  - Naval regiments stand on the burg's haven.
  - The name and icon default to Azgaar's `Military.getName` and `getEmblem`.
  - `"generate"` runs Azgaar's `Military.generate`. Its notes are in English.
  - Without `base`, a state has no regiments unless they are given.
- `chronicle` is `states[0].diplomacy`, Azgaar's war chronicle (a list of lists of strings).

## provinces

These are the era's own administrative units. They start from the master's shires:

```json
"provinces": {
  "base": "master" | "none",
  "remove": [12],
  "merge":  [{"into": 3, "from": [7], "name": "…", "fullName": "…"}],
  "split":  [{"key": "north6", "from": 6, "cells": […] | "shires": […], "name": "…", "formName": "…",
              "fullName": "…", "burg": 20, "color": "#…", "coa": {…}}],
  "add":    [{"key": "march", "name": "…", "formName": "Crìoch", "fullName": "…", "shires": [110], "cells": […],
              "burg": "@newtown"}],
  "edit":   {"1": {"name": "…", "fullName": "…", "formName": "…", "burg": 19, "color": "#…", "note": "…"}},
  "cell_province": {"812": "@march"},
  "neutral": "clear" | "keep"
}
```

- `base: "none"` starts with no provinces. Build them all with `add`: each takes the cells its selector
  names.
- The steps apply in this order: remove, merge, split and add, edit, cell_province.
- Merged-away and emptied provinces are marked removed; their ids are kept.
- A province's state is the state that holds most of its land. The engine warns when a province spans
  states.
- A seat (`burg`) that is gone is replaced by the largest burg left in the province, or none.
- `fullName` defaults to `"<formName> <name>"`, the map's Gaelic order ("Siorrachd Cathair dhearg").
- Colour and arms are made when not given.
- `neutral: "clear"` (the default) leaves land outside every state without a province, as Azgaar has it.

## Cell selectors

These are used by `assign`, provinces, zones and `split`. The keys combine:
- `shires` (master provinces; `0` is the master's land in no shire, the windy coast);
- `provinces` (era provinces, as they stand at that step);
- `states` (era states: only after the states are set, so for zones);
- `cells`, `burgs` (the burgs' cells), `from_culture`, `from_religion`;
- `where_culture` (this narrows the other keys, or selects on its own).
- `around: {cells: [...], steps: 2}` (those cells and every cell within `steps` neighbours of them);
- `water_box: [x0, y0, x1, y1]` (the water cells inside the box, for a sea zone; the pack keeps only water near
  the coast, so this is a coastal band).

## routes

```json
"routes": {
  "keep": [0, 2, 4],
  "remove": [7],
  "edit": {"12": {"name": "…", "group": "roads", "note": "…"}},
  "add":  [{"key": "kingsroad", "name": "Rathad nan Rìghrean", "group": "roads|trails|searoutes",
            "burgs": [489, 19, 431]}, {"group": "trails", "cells": [100, 101, 102]}]
}
```

- A new route through `burgs` (or `stops`, cells) follows the cheapest path between each pair of stops, by
  Azgaar's own route costs (`getLandPathCost`; for `searoutes`, `getWaterPathCost` from port to port).
- `cells` gives the path outright.
- Points and curves are made by `Routes.getPoints` / `getWaterPoints`. The cells' route links are kept
  consistent, as Azgaar's loader expects.

## markers

```json
"markers": {
  "keep": [0, 1, 2],
  "remove": [5],
  "edit": {"3": {"name": "…", "note": "…"}},
  "add":  [{"key": "stone", "type": "statues", "icon": "🗿", "name": "…", "note": "…",
            "burg": 19 | "cell": 2745 | "x": 330, "y": 200,
            "size": 30, "pin": "bubble", "fill": "#fff", "stroke": "#000", "dx": 50, "dy": 50, "px": 12}]
}
```

A known Azgaar type (`volcanoes`, `inns`, `battlefields`, `statues`, `ruins`…) supplies its icon and offsets.

## zones

```json
"zones": {
  "keep": [0, 1],
  "edit": {"0": {"name": "…", "shires": [10, 11]}},
  "add":  [{"key": "front", "name": "…", "type": "Invasion", "shires": [110], "color": "url(#hatch1)",
            "hidden": false, "note": "…"}]
}
```

- A zone's cells come from any cell selector.
- The colour defaults to Azgaar's hatch for the type: Invasion, Rebels, Proselytism, Crusade, Disease,
  Disaster, Eruption, Avalanche, Fault, Flood or Tsunami.
- Earlier moments within an age (the nine shares of the Roinn, a king's conquests) go here as zones.

## labels

```json
"labels": {
  "keep": [],
  "add":  [{"key": "roinn", "text": "Na Trì Rìoghachdan", "x": 760, "y": 60 | "cell": 1234, "fontSize": 160,
            "group": "added", "pathPoints": [[x, y], …], "letterSpacing": 2, "note": "…"}],
  "state": {"1": {"text": "…", "fontSize": 140, "pathPoints": [[x, y], [x, y]]}}
}
```

## economy (markets and goods)

`"economy": {"mode": "prune" | "regenerate", "relocate_markets": true, "remove_markets": [3],
"add_markets": [19], "edit_goods": {"12": {"name": "…"}}}`

- **prune** (the default) keeps the master's economy, made consistent. A market whose centre burg is gone
  moves to the largest burg of its territory, or closes. Deals with removed burgs or markets are dropped,
  and so are the burgs' production entries for those deals. Market territories are redrawn
  (`expandTerritories`) only when markets changed.
- `add_markets` uses Azgaar's `addMarket`, which clears every deal. Use it with `regenerate`.
- **regenerate** runs Azgaar's `Production.regenerateEconomy()`: territories, deals and burg production all
  made anew for the era's burgs.

## journeys

`"journeys": {"keep": []}` keeps the listed journey ids, or indices where a journey has no id.

## notes

`"notes": {"burg:19": "…", "state:@east": "…", "province:3": "…", "marker:@stone": "…", "regiment:1-0": "…"}`

- This is Azgaar's note (legend) on an element. The types are state, province, burg, marker, river, route,
  feature, zone, journey, market, regiment (`regiment:<state>-<i>`), addedLabel, culture, religion, biome
  and good.
- An empty string removes a note.
- Most `add` and `edit` entries also take `note` directly.

## Land and water

This is not supported, and the build refuses a spec with `land`. Reasons:

- **The pack is rebuilt from the grid.** Land and water are the grid's heights (record 7). On load, Azgaar
  rebuilds the whole pack graph from the grid (`Pack.generate`). It keeps only land and near-coast water
  cells, and adds extra points along every coastline. Turning one cell from water to land, or back, changes
  the number and order of the pack cells.
- **Every per-cell record goes out of step.** The per-cell records are biome, burg, culture, population,
  state, faith, province, routes, goods and markets (records 16–27, 36, 40, 44). Azgaar's loader then
  stops with its "Striping issue" error.
- **Features change too.** The same flip changes features, lakes, rivers, the distance field and
  shorelines.
- **Only one tool re-maps safely, and it is too fragile to drive headless.** The heightmap editor's "risk"
  mode re-maps the data after a height edit, cell by cell. It is an interactive editor, and a small flip
  there can still move rivers and burgs.

An annal that changes the land (the drowned neck of Eilean dhubh) is better shown with a zone (e.g. type
Flood) and a label. The other way is to edit the heightmap by hand in Azgaar, once, and then use that map as
the `master` for the ages concerned.

## Report and ids

`OUT.map.report.json`:
- `placeIds`: `{placeId: Azgaar burg id}`;
- `ids`: `{burg: {key: id}, state: {…}, province: {…}, culture: {…}, religion: {…}, marker: {…}, zone: {…},
  route: {…}, label: {…}}`;
- `counts`;
- `warnings`;
- `integrity`;
- with `--verify`, `verify`: the load log, counts against expectation, `shires`, `draw`, `roundTrip` and
  `shots`.
