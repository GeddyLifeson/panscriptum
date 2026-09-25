# Era specs (draft, Phase 1b)

One JSON per age, `age_I.json` … `age_VII.json`: the island **at the close of each age**, in a neutral form
for the era-map engine to read. Schema tag: `"schema": "era-spec-draft/1"`. All ids refer to the master map
`Rodos_finished.map` (burgs record 15, provinces 30, markers 35, routes 37, zones 38, cultures 13, religions 29);
all annals ids to `legendarium/annals_dated.json`.

| Age | Snapshot | Burgs | New burgs | Polities | Markers (master + new) | Routes (master + new) |
|---|---|---|---|---|---|---|
| I   | 8 an Lùnastal, VE 5,324   | 37  | 6 | 6 | 17 + 17 | 1 + 6 |
| II  | 30 an Lùnastal, GE 4,603  | 76  | 4 | 4 | 26 + 19 | 26 + 4 |
| III | 5 am Faoilleach, FE 2,960 | 291 | 3 | 3 | 40 + 24 | 191 + 6 |
| IV  | 4 am Faoilleach, LE 1,820 | 474 | 2 | 1 | 42 + 18 | 411 + 2 |
| V   | 1 am Faoilleach, AE 151   | 495 | 3 | 4 | 44 + 15 | 435 + 6 |
| VI  | 18 an t-Ògmhios, SE 71    | 505 | 0 | 2 | 47 + 15 | 450 + 5 |
| VII | 21 an Dùbhlachd, DE 27    | 505 | 1 | 2 | 49 + 12 | 450 + 5 |

## Conventions used everywhere

- **`cites`**: a list. Each entry is an annals id (`III-0138a`), `App.X …` (an appendix and section),
  `gazetteer B<id>`, `book <N> …`, `map …` (the master map itself), `NAMING_LAYER …` or `AGES7_BRIEF …`.
  Validation checks the format and that every annals id exists.
- **`inferred: true`**: the record is silent and the choice is ours (extent, population, a name, a date).
  Absent or false means the choice is stated in a cited source. Every default population is inferred.
- **`name` / `name_en`**: `name` is Dia-thìris (or `null` where no native name is attested and none was coined),
  `name_en` is the English gloss. Every `name` was checked with `rodais_engine.normalize()` (unchanged) and
  `check_agreement()` (clean). Seann-Dhaoine roots (Bral, Skell, …) are checked for normalization only.
- **Places** are referred to as `{"burg": id}`, `{"marker": id}`, `{"cell": id}`, `{"province": id}` or
  `{"new_burg": "<key>"}`. A marker or battle may sit at a burg that doesn't exist yet in that age. The spec
  still uses the burg's position; the validation block lists these as warnings.
- **Keys** for things that are not on the master map are `<Age>-N##` (new burgs), `<Age>-K##` (new markers),
  `<Age>-R##` (new routes) and `<Age>-Z##` (zones).

## Top-level fields

| Field | Contents |
|---|---|
| `age`, `age_name`, `era` | age numeral; its name; era `{abbr, name, name_en}` (VE, GE, FE, LE, AE, SE, DE). |
| `snapshot` | `date` (era date), `plan_label` (how it relates to ERA_PLAN's label), absolute `y/m/d`, `last_event_shown`, `next_event`, a one-paragraph `description`, `cites`. |
| `land_changes` | coastline or terrain that differs from the master map (drowned strands, flooded galleries, a breakwater). Each is `{what, cites}`. |
| `burgs` | master burgs that stand at the snapshot. Each is `{id, master_name, era_name?, era_name_en?, name_note?, population, kind, role, culture, faith, order?, church_body?, polity, walls?, port?, features?, cites, inferred?, note?}`. With no `era_name`, the master name applies. |
| `burgs_absent` | every master burg not drawn: `{id, master_name, state, reason, cites}`. `state` is `not yet founded`, `ruin`, `abandoned` or similar; ruins may be drawn as markers. |
| `new_burgs` | settlements lost before the master map (camps, lake dwellings, a regimental post). Each is `{key, name, name_en, cell, province, near, population, kind, role, culture, faith, polity, reason, cites, inferred}`. `cell` is a master pack cell. It is land, it isn't a master burg's cell, and no two new burgs share one. |
| `polities` | `{key, name, name_en, form, capital {burg}, ruler {name, title, note, cites}, culture, color, suzerain?, admin_units[], treasury?, cites, inferred?}`. `admin_units` lists the era's subdivisions (holdings, shares, houses, shires). Each list is `{name, name_en, kind, units[{name, name_en, seat, provinces}]}`. |
| `province_polity` | master province id (as a string) → polity key, or `"unclaimed"`. All 123 provinces are present. `province_polity_notes` explains the edge cases. |
| `diplomacy` | `{a, b, relation, since?, note?, cites}`. |
| `cultures` | `{key, name, name_en, master_culture, provinces[], cites}`. `master_culture` maps back to record 13. |
| `faiths` | `{key, name, name_en, master_religion, type, form, deity, provinces[], orders[], bodies[]?, cites}`. `orders` (Old Faith orders) and `bodies` (church bodies) have `{key, name, name_en, gods?, seat, provinces, note, cites}`. Burgs refer to them through `faith`, `order` and `church_body`. |
| `routes` | `rule` (how presence was decided), `master[]` (`{id, master_name, group, basis, name?, name_en?, inferred?, note?, cites?}`, where `name` overrides the master name), `absent[]` (master route ids not drawn), `new[]` (`{key, name, name_en, group, points[], note, cites, inferred?}`, where `points` is an ordered list of places to join). |
| `markers` | `master[]` (`{id, master_name, era_name?, note?, cites}`), `absent[]` (`{id, reason, cites}`), `new[]` (`{key, name, name_en, burg|marker|cell, icon, event, note, cites, inferred?}`), including myth sites. |
| `zones` | `{key, name, name_en, type, master_zone?, provinces[], note, cites}`. `master_zone` reuses a record-38 zone's cells; otherwise the zone is the union of its provinces (`0` = the windy coast, which has no province). |
| `labels` | free map text: `{text, text_en, at, cites}`. |
| `military` | `hosts[]` (`{name, name_en, kind, polity, station, raised?, strength?, units?, note, cites}`), `campaigns[]` (`{name, name_en, date, sides?, battles[{at, cite}], outcome?, cites}`), plus `hosts_gone` or `totals` where they apply. |
| `arms` | polity arms `{polity, blazon, note, cites}` and, where shires exist (IV–VII), `{shire, shire_name, blazon, shield, master_coa?, note, cites}` taken from App.J. |
| `notes` | `polities{key: text}` and `burgs{id: text}`: 2–4 sentences each for popups. |
| `validation` | `errors` (always empty on a good build), `warnings`, `dia_thiris_names_checked`, `dia_thiris_name_problems`, `canon_personal_names_reported` (canon personal names that fail `check_agreement`, reported without being changed), and `checks` (a sentence saying what was checked). |

## Populations

- **Ages I–II** use explicit small figures. Age II defaults to √(master pop), clamped to 30–220.
- **Ages III–VI** default to the master population × 0.035, 0.12, 0.45 or 0.85, clamped per age, with overrides
  for towns the annals give a size to. The north-west is reduced in IV and V (the dearth country ×0.4, then ×0.5).
- **Age VII** uses the master populations as they are.
- `kind` is derived from population per age (camp, hamlet, village, town, city…), except in VII, where it is the
  master `group`.

## Routes

A master route is present when every town it touches stands. It is also present when both of its end towns
stand and no more than a quarter of the towns between are missing. Named, dated routes (Rathad na Mèinne,
Rathad na Banrighinn, An Rathad Tuath, the sea lanes…) follow their first attested age regardless. Railways and
tracks that don't exist on the master map go in `routes.new`.

## Rebuilding

```
cd eras/specs_draft/tools
python3 build_all.py            # all ages
python3 build_all.py V VI       # some ages
```

`common.py` loads the master map, annals and gazetteer, provides the `Spec` builder, and holds the validation.
The content of each age is in `age_<K>.py`. Nothing outside `eras/specs_draft/` is read-write.
