# Integrating the seven layer proposals

Seven passes each read one layer of the generated map against the history and wrote a proposal here
(`religions`, `economy`, `state`, `military`, `land`, `markers_routes`, `heraldry`), four of them with a new
appendix (G trade, H shires, I land, J arms). This note records how they were put together and every point
where two of them, or a proposal and the rest of the record, disagreed.

## How it is applied

- **The map.** `../map_reconcile.py` applies every proposal's `map_edits` and then `integration.json` (the
  integrator's own edits, and the proposal edits it sets aside). Order: state, heraldry, religions, economy,
  military, markers_routes, land, integration. `../../finish_map.py` calls it after
  `burg_features.finish_records`, so a moved town's faith is set on its new cell. It checks every record it
  rewrites round-trips, that only the intended records change (1, 3, 5, 11, 13, 14, 15, 16, 19, 21, 26, 29, 30,
  31, 35, 36, 37, 39, 40, 41, 49) and that a second run changes nothing. `finish_map.py` from `Rodos_renamed.map`
  reproduces `Rodos_finished.map` byte for byte, and `MAP_CHANGES.md` is unchanged.
- **Derived on the map, not written in any proposal:** the 16 routes regrouped as roads have their saved
  `<path id="routeN">` moved from `<g id="trails">` into `<g id="roads">` (record 5), in route order; the
  cultures' rural totals (record 13) follow the cell culture and population arrays.
- **world.json** is regenerated from the map by `map_reconcile.world_digest()` (same keys and order as
  before). Marker notes are now kept whole instead of cut at 200 characters, since the notes are now history.
- **The history** (annals, gazetteer, books, appendices) was edited once, by exact old text. All 37 annals
  edits, 141 gazetteer edits and 48 text edits matched their old text uniquely; nothing had to be merged by hand
  because of a stale old string.

## What was applied, per layer

| Layer | Map edits | Annals added | Annals edited | Gazetteer | Book/appendix edits | New file |
|---|---|---|---|---|---|---|
| state | 153 (2 set aside, see below) | 7 | 0 | 8 | 6 | H_shires |
| heraldry | 4 (2 set aside) | 4 | 0 | 11 | 0 | J_arms |
| religions | 10 | 3 | 2 | 3 | 20 | |
| economy | 22 | 24 | 0 | 58 | 0 | G_trade |
| military | 29 | 10 | 4 | 6 | 12 | |
| markers_routes | 56 (1 replaced) | 19 (1 merged away) | 7 | 26 | 2 | |
| land | 56 | 5 | 24 | 29 | 8 | I_land |
| integration | 7 | | | | | |

71 annals events were added (1,515 → 1,586).

## Conflicts and decisions

1. **Provinces 122 and 123.** Heraldry fixed only the doubled full names (*Siorrachd Siorrachd fhionn*);
   state renamed the two one-cell island shires for their islands. State's values were taken (*Eilean
   dhìreach*, *Siorrachd Eilean dhìreach*; *Eilean ìseal*, *Siorrachd Eilean ìseal*); heraldry's two fullName
   edits are skipped. J's sentence on heater shields named *Siorrachd fhionn*; it now names Eilean dhìreach and
   counts the twelve heater shields the same way H counts the Tuathaich shires (eleven, the island shire among
   them, plus Inis mhin).
2. **Distance scale and latitude.** Both applied: record 1 `units.distance.scale` 4 → 0.2 mi per unit
   (markers_routes) and `geography.mapSize` 33 → 1.13, `latitude` 20.5 → 14.33 with the recomputed
   coordinates, 62.5–64.5 N (land). FMG's scale bar reads 30 mi after load; the quest journey is 156 mi.
3. **Olives on a subarctic island.** Record 41 good 14 *Olives* → *Flax* (unit bale, hemp icon). The good
   *Oil*, whose recipes are this good or whales, is left as Oil: it is now linseed or whale oil. History: G's
   olive-yard became the flax-fields of Seann Warr pressed for linseed oil (text, raw-goods table, market table,
   Ceann leathan and Baile Mòr fhionn paragraphs), the Seann Warr gazetteer line from the economy proposal likewise,
   III-0073 and book III (An Leòmhann Buidhe's "fried olives" → oatcakes fried in linseed oil), and the inn's
   marker note (marker 7). No other olive was left in the history.
4. **The panthers' crossing (marker 40).** It stands on low ground by Baile dhomhain and the southern Cnoc
   àrsaidh, with no cell above hill height anywhere near; but the annals also tie the crossing to those two towns,
   the southern road and the south-west (I-0179, II-0055, III-0072, V-0210), and H's shire 78 note already has
   "the panther watch". Moving it to a mountain pass would break those, so the marker stays and its note is
   rewritten: the roads cross the mountains by the high passes and come down here over the southern road to the
   south-west fens.
5. **The transports list.** Military's 16-entry list (Dirigible, Helicopter, Modern Airplane, Teleport
   removed; ids kept) was applied and tested in the real FMG 1.153.1: the map loads with no errors, the Transport
   Types editor lists 16 types, the Journeys overview and the journey editor open and compute the Leaden Hawk
   journey. FMG looks transports up by name, so the shortened list is kept.
6. **Dubhan has no good.** The history sells dubhan at the works' depots and pumps (VI-0029, VI-0040, VI-0048,
   VI-0087), not in markets, so there is nothing for a market good to represent. G now says so in its account of
   what the roll leaves out: dubhan is not sold in the sixteen markets but at the works' own depots and pumps and
   at inns that keep a pump, with the wartime tithe taken at the pump.
7. **The Crown's dues were described twice.** Economy had a "sale-tithe" fixed in 2023 out of the dubhan war
   tithe and a "head-tax" of eighteen in the hundred of a reckoned wage (V-0036a, VI-0131a, G § V); state had a
   head-due and a market-due set in 1933 (V-0015a), eighteen purses per hundred thousand heads, with the dubhan
   tithe on its own line (H § IV, VI-0154a). State's frame was kept because it is what the map's pollTax/salesTax
   arithmetic gives and it keeps the dubhan tithe apart. Economy's two events now fit inside it: V-0036a is the
   head-due first collected on the 1936 census, VI-0131a is the Treasury fixing the market-due at seventeen in the
   hundred after the war and setting a clerk in each market town. G § V was rewritten to match, the unit is the
   purse of the realm-coin throughout, and G's "Treasury holds 9,568 ... the whole reserve" became the year's roll.
8. **H's totals after the land layer lowered the frozen coast's people.** Land cut the rural population of the
   81 unshired cells and the ice edge of shire 120 (1.22 million → about 21 thousand). Recounted from the map:
   heads within the shires 36,225,000 → 35,412,000; head-due 6,521 → 6,374 purses; market-due (the rest of the
   9,568-purse roll) 3,047 → 3,194; Tuathaich in the country within the shires 4,046,000 → 3,234,000; Ròdaich
   unchanged; still one in seven in a burg and two parts in three of the roll from heads. The Moot's tally of the
   frozen coast is seven thousand (land's own text edit). The shire table's burg counts and cultures do not
   depend on population or biome and did not change. Two table notes that land's terrain corrections made wrong
   were fixed: shire 57 (Àth fhiadhaich is a hill ford, not a river-mouth harbour) and shire 71 (Ceann àrsaidh's
   river road runs west to the lake, not to the eastern sea; its gazetteer "known for" line likewise).
9. **Event ids that clashed.** III-0168a (economy's market-court and markers' Seòlaid Ros fhionn): markers'
   became III-0168b. IV-0127a (land's brig in the drift ice, economy's whale-boats): economy's became IV-0127b and
   G's two references follow. V-0014a (state's frozen coast, economy's Ceann mhòr market): economy's became V-0014c
   (state's V-0014b island shires keeps its id) and G's three references follow. V-0015a (state's dues, heraldry's
   roll of arms): heraldry's became V-0015b and J's references follow. Events sharing an anchor are listed in id
   order; chains (IV-0342a..e) follow their parent.
10. **The coal line twice.** Military's IV-0243a (1899) and markers' IV-0236a (1895–1905) were the same railway.
    One event is kept, IV-0243a, with military's date and place and the markers layer's carters of Doire chaol on
    Rathad na Mèinne; IV-0236a is dropped. Its line runs Muileann chrom – Cathair dhearg – Ros dhomhain, which
    agrees with V-0058a and VI-0022.
11. **The southern sea-lane and Baile thais.** Markers sent the lane "up the river to the quays of Baile thais";
    land moved Baile thais up to where the Abhainn uaine leaves the hills, with Cidhe Beag just below it. The lane
    now ends at the landing of Cidhe Beag below Baile thais (III-0189a and the Baile thais gazetteer line).
12. **The Leaden Hawk's road.** FMG, with the new scale, gives the journey 79 + 33 + 43 mi and 7 days 20 hours;
    the proposal said nine days. It now says eight (IV-0342e, book IV), and the five events are pinned with `eve`
    so that they fall within those eight days (17–25 April 1929) instead of being spread over two months. Since
    that is spring, "the first winter of the Severance war" became "the first spring" in the three gazetteer lines,
    the book ("That spring the council had sent its letters") and the party marker's note (the markers edit is set
    aside and the same note, with the season, is an integration edit).
13. **The Tuathach faith's third shire.** Religions called province 122 "the inland shire to the west"; it is
    the one-cell island Eilean dhìreach, so B now says "the island shire ... off the coast to the west of them".
14. **Rathad na Banrighinn.** The history already names Queen Catrìona's road so (III-0114, A), but *Banrighinn*
    breaks caol le caol and the map's names must obey it. *banrigh* (ban- + rìgh) is a real Gaelic exception, so
    *banrigh, banrìgh, banrighinn, banrighrean, banrìghrean* were added to the engine's `AGREEMENT_EXCEPTIONS`
    beside the weekdays and *airson*; the engine's self-test still passes 261/261.
15. **Biome 10.** With 579 settled cells relabelled from Glacier to biome 10, its name *Tundra* was changed to
    *Moor* (record 3), the word the history uses for that country.
16. **Seann Toll's one-cell Deer enclave** (religions' unsure note) is kept: B's counts assume it, and nothing in
    the history names another faith for the town.

## Dates

`reckoning.py` dates by list order between anchors, so inserted events shift their neighbours. Of the 1,515
existing events, 392 changed date: 259 changed year (Age I 131, median 14 years, most 44; Age II 100, median
7, most 33; Age III 1; Age IV 18 and Age V 9, one year each) and 133 changed only day or month. No fixed date
moved: all 93 chronicle years are kept (IV-0270's "c. 1915" was already held at 1916 before), both full canon
dates are whole, and the 18 Stone Kings in `kept_dates.json` are unchanged. Sixteen year-only canon events kept
their year but got another day in it. The only dated prose span that sits on moved events (A: "some eighty years
of rule apiece") rests on reigns whose years did not move.

## Checks

`python3 reckoning.py`, `python3 build_book.py` and `python3 ../check_rodais.py` all pass. Three checks were
added to `check_rodais.py`: every reconcile edit is in the map (a fresh `reconcile_records` changes nothing), the
16 roads are drawn in the roads group and nowhere else, and `world.json` is the digest of the map as it stands.

## Left open

- Routes 119 and 233 carried short stretches of the queen's and coal roads as trails; they are now cut into road
  and trail pieces (loose_ends.json, below), and the roads have no gaps.
- The railway cannot be drawn: FMG has no railway route group.
- The states' rural totals now follow the cells as the cultures' do (below). The religions and provinces records
  carry no statistics in this map; FMG counts them whenever an editor opens.
- The saved cultures layer in the SVG is what FMG draws from the cells: redrawn in FMG 1.153.1 on the rebuilt map
  (Layers.hide/show/draw), it serialises byte for byte as saved, so it is not stale.

## The three faiths (faiths.json)

Applied last. Record 29 is set to four entries: 0 *Gun chreideamh*; 1 *An Creideamh Sean* (organised,
polytheist, Ròdaich, deity *an Dagda*, centre Dùn ìseal, cell 3104); 2 *Na Seann Spioradan* (folk, shamanic,
Ròdaich, deity *na Sìthichean*, centre Seann Dunn of the east coast, cell 2933, since the climate pass); 3 *An Eaglais* (organised, monotheist, Tuathaich,
deity *Crìosd*, centre Doire ghlas, cell 480). The list is compacted (ids 0–3), not kept at ten with six marked
removed, so world.json and the Religions editor hold only what exists. The cells (record 26) are renumbered:
the six Ròdaich orders' cells (old 4–8, and old 3 where the cell is Ròdaich) → 1; old 2 → 2; the Tuathaich
cells (old 1, old 9, and old 3 where the cell is Tuathaich) → 3; 0 stays. Burgs: 315 / 126 / 64 (505); land
cells 1,787 / 616 / 385. `map_reconcile.py` has a `replace_religions` edit for this; on a map that already
holds the new list it passes over the earlier record-29 edits and checks each earlier record-26 edit against
its renumbered value, so a second run changes nothing. A layer's `skip` list is now read from every layer file
(faiths.json sets aside integration's note for marker 47 and gives the same note with Inis thais as the temple
city of Òrd na Cloiche). Marker notes 23 and 24 (the sacred forests) name Flidais's grove of the druid schools
and Macha's wood. The religions layer is saved empty in the SVG and FMG draws it from the cells when shown;
in FMG 1.153.1 the layer draws three faiths and the Religions editor opens with the four rows.

## The climate, Manannan's sea, dubhan and the loose ends (climate.json, dubhan.json, loose_ends.json)

The owner: "there should be no ice caps or glaciers, this is an island that sits between Ireland and Scotland";
"change charcoal to dubhan and just change the history to say that as of the current day Dubhan negotiated to be
able to export the stuff". Applied after the faiths, in this order.

- **climate.json.** Record 1: latitude 20.5 → 18.99 and longitude 19.5 → 51.63 with the coordinates Azgaar's
  Coordinates.calculate gives (56.2–54.2 N, 8.0–3.6 W; the island's coasts about 56.0–54.6 N, its middle near
  5.8 W); climate equator 20 → 27 and north pole −34 → −4 C. Record 11 is recomputed by a new edit form,
  `recompute_temperature`, exactly as Azgaar's Temperature.compute() does (checked: with the old settings it
  reproduces the old record for all 10,064 grid cells): sea level 9 C everywhere, land 2–9 C, coldest the
  summits of the massif. Record 16: the 37 Glacier cells become Moor on the unshired windy coast (17) and
  Grassland at the north end of shire 120 (20); none is left. Record 21: their people are the mean of their moor
  neighbours (0.80 → 5.59 thousand in all). Record 39 is `[]` (the 139 icebergs gone) and the SVG's ice group is
  saved empty (`empty_svg_group`). The land layer's latitude, coordinates and its two state rural edits are set
  aside (`skip`); the states' rural totals are now derived from the cells like the cultures' (Neutrals 7.26 →
  8.94, the kingdom 30,457.73 → 30,460.84 thousand; Tuathaich rural 3,240.81 → 3,245.59).
- **The sea.** finish_map.py names the ocean *Muir Mhanannain* (was *An Cuan Siar*), and the generator's
  "Frozen" routes are *fuar*, not *reòta* (*Slighe-mhara fhuar*, *Slighe-uisce fhuar*); MAP_CHANGES.md follows.
  No sea label is drawn on the saved map, so nothing in record 5 changes for it.
- **dubhan.json.** Good 34 (Coal, then the economy layer's Charcoal) is *Dubhan*, by the barrel, made from Stone
  (the spoil) instead of Wood. Markets and deals refer to it by id. The economy layer's rename is set aside.
- **loose_ends.json.** A new edit form, `split_route`, cuts a route into pieces (points, group, name, the cells'
  route links in record 36, and the saved paths Azgaar's Routes.getPath draws). Route 119 → 119 trail (Àth shean
  – Cnoc òg), 446 Rathad na Mèinne (Cnoc òg – Baile ìseal), 447 Rathad na Banrighinn (Baile ìseal – Baile chiar),
  448 trail *Ceum Baile chiar* (Baile chiar – Seann Vell); route 233 → 233 Rathad na Banrighinn (Baile Mòr fhionn –
  Àth fhiadhaich), 449 trail *Slighe Àth fhiadhaich* (on to Inis thais). 19 roads now, all drawn in the roads group.
- **faiths.json.** Na Seann Spioradan's centre is Seann Dunn (burg 18, cell 2933), the seat Appendix B now gives it.
- **The history.** The frozen coast is *an Oirthir Ghaothach*, the windy coast: bare heather moor and blanket bog
  behind the great moss, open to the north-western gales. Rewritten, ids and dates kept: I-0006a (the bare
  north-west), I-0008a (seals on the skerries), III-0173 (the great gale at Inis mhòr), IV-0127a (a brig lost in
  the mist), V-0014a, VI-0098a; edited: III-0120, III-0215, IV-0001a, IV-0246a, V-0011, VI-0154a. Added:
  III-0239a (the mist thins, 1774) and VI-0154b (Dubhan's charter of export, 2026). No other event changed date.
  H and G carry the recount: 35,415,000 heads, head-due 6,375 and market-due 3,193 purses (the roll still
  9,568), Tuathaich in the country 3,237,000 within the shires, the Moot's tally of the windy coast near nine
  thousand. Appendix I's climate is the new temperature record read in the humans' degrees.
- **Checks added to check_rodais.py:** no Glacier cell, no icebergs and the ice layer empty, the island between
  54 and 57 N with no grid cell cold enough for ice, Dubhan a good and Charcoal/Coal not, and no glacier, ice cap,
  iceberg or drift ice anywhere in the history (annals, books, appendices, houses, gazetteer, marker notes).

## The tales (tales.json)

The owner: the island's Gaelic tellings may be older and fuller than the Irish and Scottish tales, but never
contradict them. Applied last. Record 35: marker 24's note (set by faiths.json, now in its `skip`) names Dubh
Sainglenn and Liath Macha as the two horses of one chariot, foaled on one night, not one beast. The history was
edited once by exact old text (annals 7 events, books 11 passages, B 19, J 4, D 1, E 1, one gazetteer line): Macha's
two horses; Fionntan mac Bòchra the oldest of men and the Hawk of Acaill (Mòd) his fellow in memory, not his
shape; Manannan's Cup of Truth broken by three lies and whole at three truths; Crom Cruaich "of the mound" and his
stone on Magh Slèacht; Lia Fàil set up at Teamhair; Taigh Dhuinn a rock in the south-western sea; Lugh's feast
for Tailtiu; Dian Cècht's silver hand for Nuadha. No event, id or date changed.

**Later: the Sixth Age.** When the Age of Dubhan was counted apart from the Age of the Kingdom, the events from the first
working dubhan onward (V-0238 to V-0394) moved to `annals/age_VI.json` as VI-0001 to VI-0157, suffixes kept
(V-0263a became VI-0026a); every reference in this document and in the layer proposals follows the new ids, and no
date moved.
