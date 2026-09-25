# Era maps M1–M7

Each map shows Dia-thìr at the close of one age. They are built from the master (`Diathir_Atlas/Diathir.map`) by
`eras/engine/build_era_map.py`, using the engine specs `eras/specs/age_<K>.json`. Those specs are made by
`eras/engine/convert_draft.py` from the drafts in `eras/specs_draft/`. Every map loads with no errors or dialogs, and
it saves again identically (round trip). What the engine could not draw is listed in `eras/specs/CONVERT_NOTES.md`.

| Age | Snapshot date | File | States | Burgs | Markers | Notes |
|---|---|---|---|---|---|---|
| I | 8 an Lùnastal, VE 5,324 | `Diathir_Age_I.map` | 6 | 43 | 34 | Old Ones on the coasts and five hill-folk groups; 30 shires unpeopled; new camps 1001–1006; hill-folk capital inferred (Dùn ìseal); the oak woods are not drawn (biomes as on the master) |
| II | 30 an Lùnastal, GE 4,603 | `Diathir_Age_II.map` | 4 | 80 | 45 | Ailean's kingdom, the Red Hill as its vassal, Dùn dhearg at war with it, the keepers of the slab; the holdings are drawn as 5 provinces; new 2001–2004 |
| III | 5 am Faoilleach, FE 2,960 | `Diathir_Age_III.map` | 3 | 294 | 64 | The realm (the rìghrean's provinces, merged into 107), Talla na Lasrach, and the north-west, named after its seat Caol mhòr; new 3001–3003 |
| IV | 4 am Faoilleach, LE 1,820 | `Diathir_Age_IV.map` | 1 | 476 | 60 | One realm, 120 shires; the master's arms; Ceò Mhanannain drawn as a sea zone on the northern and eastern seas; the departed shown as the label "Am Falbh" at Ceann mhòr, the north-west port (they sailed north-about); the drowned salt pans of Caol gharbh as a Flood zone; new 4001–4002 |
| V | 1 am Faoilleach, AE 151 | `Diathir_Age_V.map` | 3 | 498 | 59 | The Council, the humans' north (named after its seat Cathair gheal) and Comann an Airgid (its capital's cell only); the Administration is gone and not drawn; the lifted mist drawn on the northern and eastern seas; new 5001–5003 |
| VI | 18 an t-Ògmhios, SE 71 | `Diathir_Age_VI.map` | 2 | 505 | 62 | The kingdom and Tional nan Tuathach, its vassal; an Tràigh Bhàthte and An Sloc Mòr drawn as Flood zones; no new burgs |
| VII | 21 an Dùbhlachd, DE 27 | `Diathir_Age_VII.map` | 2 | 506 | 61 | The master, plus the Moot as a second state, one new burg (7001) and the draft's new markers, routes and zones; see "Age VII against the master map" in CONVERT_NOTES.md |

`age_<K>.report.json` holds each build's warnings, the ids given to new elements (`placeIds`: era place id → Azgaar
burg id), the counts and the verification. `shots/` holds the states, cultures, religions, routes and provinces
pictures of each map.

Every map carries the master's settings, since the engine edits the master and the specs override none: distance
scale 0.14 mi/px; latitude 18.18, longitude 53; coordinates latN 57.54, latS 56.12, lonW −13.56, lonE −7.87
(latT 1.42, lonT 5.69); mapSize 0.79. After the master changes, rebuild every age.

To rebuild:

```
python3 eras/engine/convert_draft.py
python3 eras/engine/build_era_map.py eras/specs/age_IV.json eras/maps/Diathir_Age_IV.map --verify \
    --report eras/maps/age_IV.report.json --shots eras/maps/shots
```
