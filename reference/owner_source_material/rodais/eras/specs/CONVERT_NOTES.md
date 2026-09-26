# Converting the era drafts to engine specs

Written by `eras/engine/convert_draft.py` from `eras/specs_draft/age_<K>.json` (era-spec-draft/1) into `eras/specs/age_<K>.json`. Each age lists what the engine could not draw as the draft asks, and how it was drawn instead. Rerun the converter after changing a draft; the part below the marker at the end is kept.

## Rules for every age

- **Names.** The draft's Dia-thìris `name`; else the NAMES.json form of the English name; else the master's name for an element the master already names; else the English gloss, with NAMES.json forms written as their Dia-thìris (`dt`) form. Polities with no name take a NAMES.json name found in their English description, else their capital's name.
- **Notes** hold no English prose: order or church body (Dia-thìris), annals event, date, `inferred`, citations. `--prose-notes` adds the drafts' English popup prose (with NAMES.json forms).
- **Land.** The engine does not turn land into water or back. Drowned ground is a Flood zone (and a label where NAMES.json names it); biome, river and coast changes are logged and not drawn.
- **Place ids.** New burgs take 1000×K+n from their draft key `<Age>-N<n>`.
- **Provinces.** The era's provinces are the admin list that partitions the most shires (merged where a unit spans shires); other non-overlapping holdings are added; unbounded or overlapping ones are logged.
- **Economy.** `prune`: markets move to the largest burg left or close; no `add_markets` (it clears every deal).
- **Settings.** Distance scale, geography and coordinates are the master's (the spec overrides none); rebuild every age after the master changes.

## Age I

Counts: diplomacy: "kin (a kindred of the hill-folk)" -> Friendly 1; diplomacy: "kin (inferred)" -> Friendly 1; diplomacy: "none recorded" -> Neutral 1; diplomacy: "shared waters (seal grounds)" -> Friendly 1; diplomacy: "unknown; separate peoples in contact" -> Unknown 1; name from the English gloss 35.

**arms**

- Na Seann-Dhaoine: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)
- Clann na Ceiste: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)
- Clann nan Dè: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)
- Teaghlaichean an Ear: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)
- Sealgairean a' Chladaich: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)
- Muinntir a' Chnuic Dheirg: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)

**cultures**

- Na Seann-Dhaoine: master culture 0 is the wildland slot, so the people are added as a culture of their own
- shires with no people in the draft (culture 0, unpeopled): [6, 12, 18, 20, 26, 28, 29, 33, 37, 40, 42, 44, 46, 47, 57, 67, 71, 73, 75, 79, 81, 84, 85, 93, 94, 97, 98, 106, 107, 117]
- master culture 1 (Tuathaich) is not on this map (removed)

**faiths**

- Aithris a' Chruthachaidh: type "Kindred lore" is not one of Azgaar's (Folk, Organized, Cult, Heresy); drawn as Folk
- the rites of Seann-Dhaoine (unknown): type "unknown" is not one of Azgaar's (Folk, Organized, Cult, Heresy); drawn as Folk
- shires with no faith in the draft (religion 0): [6, 12, 18, 20, 26, 28, 29, 33, 37, 40, 42, 44, 46, 47, 57, 67, 71, 73, 75, 79, 81, 84, 85, 93, 94, 97, 98, 106, 107, 117]
- master faith 3 (An Eaglais) is not on this map (removed)

**labels**

- label "the vigil of the seven fires": no Dia-thìris text; not drawn

**land**

- land change 1: "The northern lowlands are oak and hazel woodland, not moor: the oak came after the cold years and has not yet " -- not drawn (the engine keeps the master's land, biomes and rivers)
- land change 2: "The north-western horn and the windy coast stay bare heather and bog, as now." -- not drawn (the engine keeps the master's land, biomes and rivers)
- land change 3: "Eilean dhubh is already an island at the snapshot (its neck drowned in VE 506), so the coast is as on the mast" -- not drawn (the engine keeps the master's land, biomes and rivers)
- land change 4: "The lake dwellings of Loch chrom stand on their oak piles in the shallows (burned in GE 1,525)." -- not drawn (the engine keeps the master's land, biomes and rivers)

**map**

- the master's journey (Buidheann an t-Seabhaig Luaidhe) is later than this age; dropped
- rural population scaled by 0.0134, so the island holds some 18,000 people (2,520 of them in its towns)
- the master's markets, goods and deals are pruned to this age's burgs (Azgaar's economy has no era)
- draft popup prose (notes.polities, notes.burgs, roles, reasons) not carried: map notes hold no English prose

**military**

- 2 campaigns: their sides are people, not the map's states; not in the states' campaign lists (battles are markers where the draft gives them)

**names**

- faith old-ones-rite: no Dia-thìris name; English gloss used: "the rites of Seann-Dhaoine (unknown)"
- new burg I-N01: no Dia-thìris name; English gloss used: "the seal-hunters' camp on Eilean mhin"
- new burg I-N02: no Dia-thìris name; English gloss used: "the autumn seal camp on Eilean fhada"
- new burg I-N04: no Dia-thìris name; English gloss used: "the summer camps in the passes"
- new burg I-N05: no Dia-thìris name; English gloss used: "the deer-drive camp of the eastern forest"
- new burg I-N06: no Dia-thìris name; English gloss used: "the hearths of the southern shore"
- province "the hearths of the Doire uaine hills (covered hearths)": no Dia-thìris name; named after its largest burg, "Doire uaine"
- province "the high valleys about the crack": no Dia-thìris name; named after its largest burg, "Dùn ìseal"
- marker I-K01: no Dia-thìris name; English gloss used: "Teine a' Chlachair and the slab over the vein"
- marker I-K02: no Dia-thìris name; English gloss used: "Coimhdeach na Fine in the grove"
- marker I-K03: no Dia-thìris name; English gloss used: "the first lighting: gual òir on the sea"
- marker I-K04: no Dia-thìris name; English gloss used: "the third lighting: gual dubh warm in the ground"
- marker I-K05: no Dia-thìris name; English gloss used: "the fourth lighting: the blood of the misstrike"
- marker I-K06: no Dia-thìris name; English gloss used: "the fifth lighting: gual airgid in the river"
- marker I-K07: no Dia-thìris name; English gloss used: "the sixth lighting: the fire in the fingers"
- marker I-K08: no Dia-thìris name; English gloss used: "the seventh lighting: gual bogha-froise and the vigil"
- marker I-K09: no Dia-thìris name; English gloss used: "hearth-stones on the terraces of the Abhainn uaine"
- marker I-K10: no Dia-thìris name; English gloss used: "the fish-weirs of the Abhainn ìseal"
- marker I-K11: no Dia-thìris name; English gloss used: "the stone boxes of Eilean dhearg"
- marker I-K12: no Dia-thìris name; English gloss used: "the steps of Bral"
- marker I-K13: no Dia-thìris name; English gloss used: "the script in the cliff at Tarr"
- marker I-K14: no Dia-thìris name; English gloss used: "the hut of the nine"
- marker I-K15: no Dia-thìris name; English gloss used: "the geese of Eilean ghorm"
- marker I-K16: no Dia-thìris name; English gloss used: "the drowned hearths of the neck"
- marker I-K17: no Dia-thìris name; English gloss used: "where the eleven were lost"
- … and 12 more

**provinces**

- no subdivision of the island in this age covers it; provinces start from none
- Na Seann-Dhaoine: "the ten Seann places and the islands off them (VE 3,872)" (extent): the whole polity or unbounded; not drawn as a province

**states**

- Clann nan Dè: no capital in the draft; its largest burg 315 (Dùn ìseal) is drawn as the capital
- neutral shires (unclaimed, or of a polity not drawn): [6, 12, 18, 20, 26, 28, 29, 33, 37, 40, 42, 44, 46, 47, 57, 67, 71, 73, 75, 79, 81, 84, 85, 93, 94, 97, 98, 106, 107, 117]

## Age II

Counts: diplomacy: "none recorded; the handful is burned in " -> Neutral 1; diplomacy: "separate charges: the king rules the gra" -> Friendly 1; diplomacy: "suzerain and vassal" -> Suzerain 1; diplomacy: "trade at the ford" -> Friendly 1; diplomacy: "war" -> Enemy 1; name from the English gloss 33.

**arms**

- Rìoghachd Chlann nan Dè: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)
- Muinntir a' Chnuic Dheirg: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)
- Dùn dhearg: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)
- Luchd-faire na Lice: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)

**cultures**

- Na Seann-Dhaoine: holds no land at the snapshot; not on the map
- shires with no people in the draft (culture 0, unpeopled): [122]
- master culture 1 (Tuathaich) is not on this map (removed)

**faiths**

- Aithris a' Chruthachaidh: type "Kindred lore" is not one of Azgaar's (Folk, Organized, Cult, Heresy); drawn as Folk
- shires with no faith in the draft (religion 0): [122]
- master faith 3 (An Eaglais) is not on this map (removed)
- 1 burgs keep a faith other than their shire's; Azgaar gives a burg the faith of its cell, so only the note tells it

**labels**

- label "the kin wait for their shares": no Dia-thìris text; not drawn
- label "the spears of the east": no Dia-thìris text; not drawn

**land**

- land change 1: "The oak has fallen back from the northern lowlands (GE 3,588): heather, birch and bog-moss as on the master ma" -- not drawn (the engine keeps the master's land, biomes and rivers)
- land change 2: "Loch chrom stands a hand higher on the Ros dhomhain tide-rock than at the first cut; no change to the drawn sh" -- not drawn (the engine keeps the master's land, biomes and rivers)
- land change 3: "The lake dwellings of Loch chrom are burned (GE 1,525); the charred piles stand in the shallows." -- not drawn (the engine keeps the master's land, biomes and rivers)
- land change 4: "The crack across the valley at Cill ghlas, banked with stones and marked by a line of white stones." -- not drawn (the engine keeps the master's land, biomes and rivers)

**map**

- the master's journey (Buidheann an t-Seabhaig Luaidhe) is later than this age; dropped
- rural population scaled by 0.0824, so the island holds some 111,000 people (15,560 of them in its towns)
- the master's markets, goods and deals are pruned to this age's burgs (Azgaar's economy has no era)
- draft popup prose (notes.polities, notes.burgs, roles, reasons) not carried: map notes hold no English prose

**military**

- 3 hosts given only in words (no units): not drawn as regiments
- 4 campaigns: their sides are people, not the map's states; not in the states' campaign lists (battles are markers where the draft gives them)

**names**

- new burg II-N01: no Dia-thìris name; English gloss used: "the heirs' camp in the valley under Dùn ìseal"
- new burg II-N02: no Dia-thìris name; English gloss used: "the war-camp of the eastern host"
- new burg II-N03: no Dia-thìris name; English gloss used: "the salt-folk's shelters at the ford gathering"
- new burg II-N04: no Dia-thìris name; English gloss used: "the ring of shelters at Fuarain Theth Muileann ruadh"
- province "the salt shore": no Dia-thìris name; named after its largest burg, "Baile ghorm"
- province "the north": no Dia-thìris name; named after its largest burg, "Baile Mòr mhòr"
- province "the west": no Dia-thìris name; named after its largest burg, "Ros dhomhain"
- province "the south coast (holders the gathering does not name)": no Dia-thìris name; named after its largest burg, "Tobar dhearg"
- marker II-K01: no Dia-thìris name; English gloss used: "the crowning in the grove"
- marker II-K03: no Dia-thìris name; English gloss used: "the boundary stones of Dòmhnall Clachach"
- marker II-K04: no Dia-thìris name; English gloss used: "where An Cnoc Ruadh knelt"
- marker II-K05: no Dia-thìris name; English gloss used: "the shingle of Baile ghorm"
- marker II-K06: no Dia-thìris name; English gloss used: "the keepers' house and the stone cup"
- marker II-K07: no Dia-thìris name; English gloss used: "the hawk lintel of Àth mhòr"
- marker II-K08: no Dia-thìris name; English gloss used: "the wolf graves of Tobar fhiadhaich"
- marker II-K09: no Dia-thìris name; English gloss used: "Gilleasbuig Beag's island"
- marker II-K10: no Dia-thìris name; English gloss used: "the tide-rock of Ros dhomhain"
- marker II-K11: no Dia-thìris name; English gloss used: "the stone of A' Ghaoth Dhubh"
- marker II-K12: no Dia-thìris name; English gloss used: "the white stones of the fault"
- marker II-K13: no Dia-thìris name; English gloss used: "the first trench for another vein"
- marker II-K14: no Dia-thìris name; English gloss used: "the tally wall of Seann Warr"
- marker II-K15: no Dia-thìris name; English gloss used: "the half-cut stone"
- marker II-K16: no Dia-thìris name; English gloss used: "the wind-stones and the eight notches"
- marker II-K17: no Dia-thìris name; English gloss used: "Eilean ìseal, the island of the dead"
- marker II-K18: no Dia-thìris name; English gloss used: "the long-house of Cathair gheal"
- … and 12 more

**provinces**

- no subdivision of the island in this age covers it; provinces start from none
- Muinntir a' Chnuic Dheirg: "the Red Hill's households (Cathair dhomhain, Baile ghlas, Cnoc bheag of the forest, Ceann àrsaidh)" (households counted in the Red Hill list): the whole polity or unbounded; not drawn as a province
- Luchd-faire na Lice: "the nine districts of the hills (one keeper each)" (lot districts, not bounded on any record): the whole polity or unbounded; not drawn as a province

**states**

- neutral shires (unclaimed, or of a polity not drawn): [122]

## Age III

Counts: diplomacy: "the division of keeping" -> Neutral 1; diplomacy: "tributary when the road-guard comes" -> Suzerain 1; name from NAMES.json 5; name from the English gloss 34.

**arms**

- Rìoghachd Cathair dhearg: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)
- Talla na Lasrach: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)
- Caol mhòr: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)

**cultures**

- master culture 1 (Tuathaich) is not on this map (removed)

**diplomacy**

- realm / raiders (hostile (outlaws of the north-western and eastern waters)): not both states on the map; not drawn

**faiths**

- An Creideamh Sean: 7 orders/bodies are not faiths of their own on the map; each burg's order or body is named in its note
- master faith 3 (An Eaglais) is not on this map (removed)

**labels**

- label "Na Linntean Urramach": no Dia-thìris text; not drawn

**land**

- land change 1: "No change to coast, rivers or heights. Talla na Lasrach stands over the flame at Dùn ìseal; stone bridges carr" -- not drawn (the engine keeps the master's land, biomes and rivers)
- land change 2: "The fields of Achadh mhòr were burned to the stubble in FE 556 and have long since been sown again." -- not drawn (the engine keeps the master's land, biomes and rivers)

**map**

- the master's journey (Buidheann an t-Seabhaig Luaidhe) is later than this age; dropped
- rural population scaled by 0.2218, so the island holds some 300,000 people (43,152 of them in its towns)
- the master's markets, goods and deals are pruned to this age's burgs (Azgaar's economy has no era)
- draft popup prose (notes.polities, notes.burgs, roles, reasons) not carried: map notes hold no English prose

**military**

- 5 hosts given only in words (no units): not drawn as regiments
- 6 campaigns: their sides are people, not the map's states; not in the states' campaign lists (battles are markers where the draft gives them)

**names**

- polity north-west: no Dia-thìris name; named after its capital, "Caol mhòr"
- new burg III-N01: no Dia-thìris name; English gloss used: "the masons' lodge by the western crossing"
- new burg III-N02: no Dia-thìris name; English gloss used: "the pilgrims' guest-shelters at Allt an Àigh"
- new burg III-N03: no Dia-thìris name; English gloss used: "the summer shelters on Eilean ruadh"
- province "the ground of the Hall and the galleries": no Dia-thìris name; named after its largest burg, "Dùn ìseal"
- province "the slab at Tobar dhìreach and the schools' hill": no Dia-thìris name; named after its largest burg, "Cnoc bhàn"
- marker III-K03: no Dia-thìris name; English gloss used: "the double stones of Dùn thais (first blood of the heirs)"
- marker III-K04: no Dia-thìris name; English gloss used: "the stone of the two oaths"
- marker III-K05: no Dia-thìris name; English gloss used: "the boundary stones of the woods (east)"
- marker III-K06: no Dia-thìris name; English gloss used: "the boundary stones of the woods (west)"
- marker III-K07: no Dia-thìris name; English gloss used: "the weather-cairns of Cnoc ghlas"
- marker III-K08: no Dia-thìris name; English gloss used: "the ancestor-cairn of Cathair naomh"
- marker III-K10: no Dia-thìris name; English gloss used: "Goraidh Mòr's hall and the kings' graves"
- marker III-K11: no Dia-thìris name; English gloss used: "the white wolf-stone at the gate"
- marker III-K12: no Dia-thìris name; English gloss used: "the shrine of the drowned"
- marker III-K14: no Dia-thìris name; English gloss used: "the toll-house at Àth ghlas"
- marker III-K15: no Dia-thìris name; English gloss used: "the watch-tower of Baile ruadh"
- marker III-K16: no Dia-thìris name; English gloss used: "the bridge below Dùn chrom"
- marker III-K17: no Dia-thìris name; English gloss used: "the bridge at Ceann àrsaidh"
- marker III-K18: no Dia-thìris name; English gloss used: "the bridge at Doire mhin"
- marker III-K19: no Dia-thìris name; English gloss used: "the stone quay of Seann Vell"
- marker III-K20: no Dia-thìris name; English gloss used: "the stag-letters"
- marker III-K21: no Dia-thìris name; English gloss used: "the temple of Sliochd Thormoid"
- marker III-K22: no Dia-thìris name; English gloss used: "the mill-shrine"
- marker III-K23: no Dia-thìris name; English gloss used: "the school of letters at Inis bheag"
- … and 12 more

**provinces**

- 6 units of "the provinces of the rìghrean" span several shires; merged
- shires in no unit of "the provinces of the rìghrean" are not provinces in this age: [7, 14, 28, 35, 36, 75, 86, 105, 107, 114, 120, 122]
- Rìoghachd Cathair dhearg: "the houses of custody and the great lordships" (lordships within the realm): overlaps the era's provinces; not drawn
- Talla na Lasrach: "the nine hearths about the mountain's foot" (households of custody (not bounded)): the whole polity or unbounded; not drawn as a province

**routes**

- III-R04 (the river-boats of the Abhainn uaine): Azgaar draws no "rivers" group; drawn as trails

**states**

- burg 419 (Muileann chiar): polity realm in a shire of hall; its cell goes to realm

**zones**

- III-Z18 (Cuid nam Marbh): no ground in the draft; not drawn

## Age IV

Counts: name from NAMES.json 4; name from the English gloss 25; state arms from the master roll 1.

**cultures**

- master culture 1 (Tuathaich) is not on this map (removed)

**diplomacy**

- realm / the departed (none: no word since the broken tidings of two landfalls): not both states on the map; not drawn
- realm / sea-thieves of the north-west (hostile): not both states on the map; not drawn

**faiths**

- An Creideamh Sean: 6 orders/bodies are not faiths of their own on the map; each burg's order or body is named in its note
- master faith 3 (An Eaglais) is not on this map (removed)

**labels**

- label "the departed: north-about, beyond the mist": no Dia-thìris text; drawn as "Am Falbh" (the Setting-Out, NAMES.json) at the north-westernmost port, Ceann mhòr (the fleet went north-about)
- label "the cold way of the grain barges (laid up LE 1,634)": no Dia-thìris text; not drawn

**land**

- land change 1: "Manannan's mist lies on the eastern sea beyond the northern and eastern headlands (from the Setting-Out, LE 40" -- not drawn (the engine keeps the master's land, biomes and rivers)
- land change 2: "The oak grove that named Doire fhionn is gone, felled for the keels of the fleet (LE 5); the northern Doire sh" -- not drawn (the engine keeps the master's land, biomes and rivers)
- land change 3: "The Abhainn bheag below Ros fhionn is silted by a shifting bar (LE 1,159); the salt barges cannot reach its qu" -- not drawn (the engine keeps the master's land, biomes and rivers)
- land change 4: "The salt pans of Caol gharbh are under the sea (LE 1,734)." -- no land/water flip; a Flood zone instead

**map**

- the master's journey (Buidheann an t-Seabhaig Luaidhe) is later than this age; dropped
- rural population scaled by 0.3878, so the island holds some 570,000 people (120,983 of them in its towns)
- the master's markets, goods and deals are pruned to this age's burgs (Azgaar's economy has no era)
- draft popup prose (notes.polities, notes.burgs, roles, reasons) not carried: map notes hold no English prose

**military**

- 1 hosts given only in words (no units): not drawn as regiments
- 3 campaigns: their sides are people, not the map's states; not in the states' campaign lists (battles are markers where the draft gives them)

**names**

- new burg IV-N01: no Dia-thìris name; English gloss used: "the guest-house at Allt an Àigh"
- new burg IV-N02: no Dia-thìris name; English gloss used: "the ferry landing at Cidhe Beag"
- marker IV-K02: no Dia-thìris name; English gloss used: "Taigh na Fèithe and its lot-stones"
- marker IV-K03: no Dia-thìris name; English gloss used: "the spirit-house and the ancestor-posts"
- marker IV-K04: no Dia-thìris name; English gloss used: "the temple of Lia Fàil"
- marker IV-K05: no Dia-thìris name; English gloss used: "Macha's great house"
- marker IV-K06: no Dia-thìris name; English gloss used: "the house of Òrd an t-Seabhaig and Leabhar an t-Seabhaig"
- marker IV-K07: no Dia-thìris name; English gloss used: "the ford of Àth shean"
- marker IV-K11: no Dia-thìris name; English gloss used: "the stone of the fourteen names"
- marker IV-K12: no Dia-thìris name; English gloss used: "the salt pans of Ros fhionn"
- marker IV-K13: no Dia-thìris name; English gloss used: "the paper mill"
- marker IV-K14: no Dia-thìris name; English gloss used: "the burned sea-thieves' boats"
- marker IV-K15: no Dia-thìris name; English gloss used: "the gates of Seann Warr"
- marker IV-K16: no Dia-thìris name; English gloss used: "the felled grove of Doire fhionn"
- marker IV-K17: no Dia-thìris name; English gloss used: "Taigh na Deasbaid at Dùn thais"
- marker IV-K18: no Dia-thìris name; English gloss used: "the timber from beyond Ceò Mhanannain"
- route IV-R01: no Dia-thìris name; English gloss used: "the cairned drove road of Àth chiar"
- route IV-R02: no Dia-thìris name; English gloss used: "the grain barges down the Abhainn dhomhain"
- zone IV-Z01: no Dia-thìris name; English gloss used: "Ceò Mhanannain on the eastern sea"
- zone IV-Z02: no Dia-thìris name; English gloss used: "Rolla nan Deònach and Am Falbh (LE 2–40)"
- zone IV-Z03: no Dia-thìris name; English gloss used: "the cold hearths of Cogadh nan Trì Tagraichean (LE 558)"
- zone IV-Z04: no Dia-thìris name; English gloss used: "the swallowing cough and the closed coast road (LE 1,079–1,082)"
- zone IV-Z10: no Dia-thìris name; English gloss used: "the coppice shires (LE 109)"
- zone IV-Z11: no Dia-thìris name; English gloss used: "the salt country of Ros fhionn (LE 354–1,179)"
- zone IV-Z12: no Dia-thìris name; English gloss used: "the lordship of Seann Chwen for life (LE 1,276–1,291)"

**provinces**

- 3 units of "the shires (siorrachdan)" span several shires; merged
- Dia-thìr: "the seven houses of custody" (houses answerable to the vein-house for their galleries and their share of the burning): overlaps the era's provinces; not drawn
- Dia-thìr: "chartered towns" (towns with rights of their own): 3 units with no ground of their own (towns, boards, markets); in the burg notes only

**routes**

- IV-R02 (the grain barges down the Abhainn dhomhain): Azgaar draws no "rivers" group; drawn as trails

**zones**

- IV-Z01: its `sea` says west, its name east; the name is followed
- IV-Z01: a sea zone with no cells in the draft; drawn on the coastal water to the north and east (from its name, its sea and the age's mist land changes)

## Age V

Counts: diplomacy: "allies" -> Ally 1; diplomacy: "truce (the truce of Àth àrsaidh)" -> Suspicion 1; name from NAMES.json 7; name from the English gloss 22; name kept from the master 1; province named after its seat 120.

**arms**

- Comhairle nan Coimheadaichean: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)
- Cathair gheal: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)
- Comann an Airgid: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)

**diplomacy**

- council / administration (war, ended): not both states on the map; not drawn
- north / administration (abandoned): not both states on the map; not drawn
- silver-guild / eastern raiders (trade in rifles for bar silver): not both states on the map; not drawn

**faiths**

- An Creideamh Sean: 6 orders/bodies are not faiths of their own on the map; each burg's order or body is named in its note
- An Eaglais: 2 orders/bodies are not faiths of their own on the map; each burg's order or body is named in its note
- 9 burgs keep a faith other than their shire's; Azgaar gives a burg the faith of its cell, so only the note tells it

**labels**

- label "An Dealachadh": no Dia-thìris text; not drawn

**land**

- land change 1: "Manannan's mist lifted in the winter of the Crossing (AE 1); the northern water is open at the snapshot, but n" -- not drawn (the engine keeps the master's land, biomes and rivers)
- land change 2: "The Rending: the earth torn open along a fault about Cill ghlas (AE 137); the district fenced and closed, left" -- not drawn (the engine keeps the master's land, biomes and rivers)
- land change 3: "The Abhainn uaine silted black with the washing of coal (AE 33); its salmon runs failed." -- not drawn (the engine keeps the master's land, biomes and rivers)
- land change 4: "The oak woods about Cathair fhada felled for pit-props (AE 24)." -- not drawn (the engine keeps the master's land, biomes and rivers)
- land change 5: "Spoil-heaps at the camps and deep workings of the Muileann chrom district; the lower galle" -- no land/water flip; a Flood zone instead

**map**

- the master's journey (Buidheann an t-Seabhaig Luaidhe) is later than this age; dropped
- rural population scaled by 0.5978, so the island holds some 1,000,000 people (307,862 of them in its towns)
- the master's markets, goods and deals are pruned to this age's burgs (Azgaar's economy has no era)
- draft popup prose (notes.polities, notes.burgs, roles, reasons) not carried: map notes hold no English prose

**military**

- 9 hosts given only in words (no units): not drawn as regiments
- 3 campaigns: their sides are people, not the map's states; not in the states' campaign lists (battles are markers where the draft gives them)

**names**

- polity north: no Dia-thìris name; named after its capital, "Cathair gheal"
- new burg V-N01: no Dia-thìris name; English gloss used: "the columns' camp at Baile Mòr ruadh"
- new burg V-N02: no Dia-thìris name; English gloss used: "Taigh an Àrd-mhaoir above Ros dhomhain"
- new burg V-N03: no Dia-thìris name; English gloss used: "the camp of Cnoc fhiadhaich workings"
- marker V-K01: no Dia-thìris name; English gloss used: "Teachdaireachd na h-Eaglaise chapel and school"
- marker V-K02: no Dia-thìris name; English gloss used: "A' Chompanaidh deep-water quay and steelyard"
- marker V-K05: no Dia-thìris name; English gloss used: "the store at Baile thais"
- marker V-K09: no Dia-thìris name; English gloss used: "the beacon hill of the stoppage"
- marker V-K11: no Dia-thìris name; English gloss used: "the burned flying-machine shed"
- marker V-K12: no Dia-thìris name; English gloss used: "the ford where the columns were counted"
- marker V-K13: no Dia-thìris name; English gloss used: "the grey-night fields"
- marker V-K14: no Dia-thìris name; English gloss used: "the pit shrine of Cill dhìreach"
- marker V-K15: no Dia-thìris name; English gloss used: "Leabhar Baile thais and Faire nan Lòchran"
- route V-R02: no Dia-thìris name; English gloss used: "the mule tram-road to Ros dhìreach"
- route V-R03: no Dia-thìris name; English gloss used: "the eastern Rathad na Mèinne"
- route V-R04: no Dia-thìris name; English gloss used: "the coal barges of the Abhainn uaine"
- route V-R05: no Dia-thìris name; English gloss used: "A' Chompanaidh cart-road round Doire mhòr"
- route V-R06: no Dia-thìris name; English gloss used: "the road of the columns north"
- zone V-Z05: no Dia-thìris name; English gloss used: "the northern concession (AE 20)"
- zone V-Z06: no Dia-thìris name; English gloss used: "An Togail country (AE 88–97)"
- zone V-Z07: no Dia-thìris name; English gloss used: "the lines at midsummer AE 150"
- zone V-Z08: no Dia-thìris name; English gloss used: "the mining country of the rising (AE 149)"
- zone V-Z09: no Dia-thìris name; English gloss used: "the lifted Ceò Mhanannain (AE 1)"

**provinces**

- the provinces are the units of the Administration of an Tìr Thall and the Company (gone at the snapshot) ("the districts of the Administration (AE 122 to AE 146)"), which is not a state at the snapshot; kept as the era's provinces
- 1 units of "the districts of the Administration (AE 122 to AE 146)" span several shires; merged
- shires in no unit of "the districts of the Administration (AE 122 to AE 146)" are not provinces in this age: [122, 123]
- Comhairle nan Coimheadaichean: "the forest council of the mining country" (war council): overlaps a province already drawn (shires [35, 42, 76, 87, 96, 112]); not drawn
- Comhairle nan Coimheadaichean: "the custodians of the settlements (nineteen at the first petition, thirty-one at the second)" (settlement custodians): no shires given; not drawn

**routes**

- V-R01 (Slighe a' Ghuail (carbad-iarainn)): Azgaar draws no "railways" group; drawn as roads
- V-R02 (the mule tram-road to Ros dhìreach): Azgaar draws no "railways" group; drawn as roads
- V-R04 (the coal barges of the Abhainn uaine): Azgaar draws no "rivers" group; drawn as trails

**states**

- the silver guild of Muileann chiar: holds no shire; drawn as a state of its capital's cell alone
- the Administration of an Tìr Thall and the Company (gone at the snapshot): holds no shire and has no seat at the snapshot; not drawn as a state
- burg 419 (Muileann chiar): polity silver-guild in a shire of council; its cell goes to silver-guild

**zones**

- V-Z07: the front is drawn as the ground of all its sides (123 shires)
- V-Z09: a sea zone with no cells in the draft; drawn on the coastal water to the north and east (from its name, its sea and the age's mist land changes)

## Age VI

Counts: diplomacy: "a homeland held apart without standing i" -> Neutral 1; name from NAMES.json 7; name from the English gloss 17; state arms from the master roll 1.

**arms**

- Tional nan Tuathach: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)

**diplomacy**

- kingdom / raiders off Cathair gheal (hostile; no help sent to the Tuathaich towns): not both states on the map; not drawn
- kingdom / moot: "Neutral" in the diplomacy list, but kingdom is its suzerain; drawn as Suzerain/Vassal

**faiths**

- An Creideamh Sean: 6 orders/bodies are not faiths of their own on the map; each burg's order or body is named in its note
- An Eaglais: 3 orders/bodies are not faiths of their own on the map; each burg's order or body is named in its note
- 32 burgs keep a faith other than their shire's; Azgaar gives a burg the faith of its cell, so only the note tells it

**labels**

- label ""They do not come south."": no Dia-thìris text; not drawn

**land**

- land change 1: "The drowned strand of Cnoc chaol: the old town's site left as the Great Wave left it (SE 4" -- no land/water flip; a Flood zone and the label "an Tràigh Bhàthte" instead
- land change 2: "The dry shafts of the search for a second vein, forty-one of them from the hills above Dùn dhearg to the moors" -- not drawn (the engine keeps the master's land, biomes and rivers)
- land change 3: "The lowest galleries of the Sloc Mòr let flood (SE 61)." -- no land/water flip; a Flood zone and the label "An Sloc Mòr" instead
- land change 4: "The breakwater across the strait between Caol chrom and Caol gharbh, the longest on the island (SE 48–56)." -- not drawn (the engine keeps the master's land, biomes and rivers)

**map**

- the master's journey (Buidheann an t-Seabhaig Luaidhe) is later than this age; dropped
- rural population scaled by 0.8367, so the island holds some 1,500,000 people (531,170 of them in its towns)
- the master's markets, goods and deals are pruned to this age's burgs (Azgaar's economy has no era)
- draft popup prose (notes.polities, notes.burgs, roles, reasons) not carried: map notes hold no English prose

**military**

- 3 hosts given only in words (no units): not drawn as regiments
- 2 campaigns: their sides are people, not the map's states; not in the states' campaign lists (battles are markers where the draft gives them)

**names**

- marker VI-K02: no Dia-thìris name; English gloss used: "the boundary stones on the north roads"
- marker VI-K04: no Dia-thìris name; English gloss used: "the mint"
- marker VI-K05: no Dia-thìris name; English gloss used: "the forty-one dry shafts"
- marker VI-K06: no Dia-thìris name; English gloss used: "the fall at Muileann dhearg"
- marker VI-K07: no Dia-thìris name; English gloss used: "the church at Cnoc ghorm"
- marker VI-K09: no Dia-thìris name; English gloss used: "the market cross of Mac Ùisdein"
- marker VI-K10: no Dia-thìris name; English gloss used: "the ancestors' hall of Seann Dunn"
- marker VI-K12: no Dia-thìris name; English gloss used: "the waterworks of Muileann bhàn"
- marker VI-K13: no Dia-thìris name; English gloss used: "the copper workings of Àth fhiadhaich"
- marker VI-K14: no Dia-thìris name; English gloss used: "Ciorstaidh nic Artair's reef post"
- marker VI-K15: no Dia-thìris name; English gloss used: "the lifeboat of Cuan bheag"
- route VI-R02: no Dia-thìris name; English gloss used: "the western branch of Slighe a' Ghuail"
- route VI-R03: no Dia-thìris name; English gloss used: "Slighe a' Ghuail to Ceann leathan"
- route VI-R05: no Dia-thìris name; English gloss used: "the eastern salt drove road"
- zone VI-Z04: no Dia-thìris name; English gloss used: "An Traoghadh: the vein's last unworked stretches (SE 56)"
- zone VI-Z07: no Dia-thìris name; English gloss used: "the stone's shires (their own count, SE 65)"
- zone VI-Z08: no Dia-thìris name; English gloss used: "the panthers' host (SE 62)"

**provinces**

- Rìoghachd Dia-thìr: "the market towns" (market right): 15 units with no ground of their own (towns, boards, markets); in the burg notes only
- Rìoghachd Dia-thìr: "the Boards" (crown boards): 3 units with no ground of their own (towns, boards, markets); in the burg notes only

**routes**

- VI-R01 (Slighe a' Ghuail): Azgaar draws no "railways" group; drawn as roads
- VI-R02 (the western branch of Slighe a' Ghuail): Azgaar draws no "railways" group; drawn as roads
- VI-R03 (Slighe a' Ghuail to Ceann leathan): Azgaar draws no "railways" group; drawn as roads

## Age VII

Counts: culture: shires keeping the master's cells 123; diplomacy: "defeated and unreconciled: seann-chunnta" -> Suspicion 1; faith: shires keeping the master's cells 123; name from NAMES.json 3; name from the English gloss 18.

**arms**

- Tional nan Tuathach: no arms at the snapshot; Azgaar needs arms, so they are generated (seeded)

**cultures**

- Na Seann-Dhaoine: holds no land at the snapshot; not on the map

**diplomacy**

- kingdom / beyond the north-western capes (the charter of export: dubhan only, loaded at Ros dhomhain; the kingdom does not know who buys): not both states on the map; not drawn
- kingdom / moot: "Suspicion" in the diplomacy list, but kingdom is its suzerain; drawn as Suzerain/Vassal

**faiths**

- An Creideamh Sean: 6 orders/bodies are not faiths of their own on the map; each burg's order or body is named in its note
- An Eaglais: 3 orders/bodies are not faiths of their own on the map; each burg's order or body is named in its note
- 32 burgs keep a faith other than their shire's; Azgaar gives a burg the faith of its cell, so only the note tells it

**land**

- land change 1: "None: this is the master map (Rodos_finished.map) at full era density." -- not drawn (the engine keeps the master's land, biomes and rivers)

**map**

- draft popup prose (notes.polities, notes.burgs, roles, reasons) not carried: map notes hold no English prose

**markers**

- the master's markers keep the master's notes

**military**

- 1 campaigns besides the master's are not in the campaign list

**names**

- new burg VII-N01: no Dia-thìris name; English gloss used: "the Àth leathan post"
- marker VII-K01: no Dia-thìris name; English gloss used: "the dubhan works of Seann Skell"
- marker VII-K02: no Dia-thìris name; English gloss used: "the dubhan depots of the north"
- marker VII-K03: no Dia-thìris name; English gloss used: "Comann nan Gualadairean' Row"
- marker VII-K04: no Dia-thìris name; English gloss used: "Ciste-chuimhne Dhùinte of An Cogadh Fada"
- marker VII-K06: no Dia-thìris name; English gloss used: "the pass posts on the northern road"
- marker VII-K07: no Dia-thìris name; English gloss used: "the capped western seams"
- marker VII-K08: no Dia-thìris name; English gloss used: "the last face of An Sloc Mòr"
- marker VII-K09: no Dia-thìris name; English gloss used: "the charter of export"
- marker VII-K11: no Dia-thìris name; English gloss used: "An còigeamh rèisimeid's barracks"
- marker VII-K12: no Dia-thìris name; English gloss used: "the Leòmhann lamp"
- route VII-R01: no Dia-thìris name; English gloss used: "the line (Slighe a' Ghuail)"
- route VII-R02: no Dia-thìris name; English gloss used: "the western branch"
- route VII-R03: no Dia-thìris name; English gloss used: "the line to Ceann leathan"
- route VII-R05: no Dia-thìris name; English gloss used: "the dubhan tank-hulls up the west coast"
- zone VII-Z06: no Dia-thìris name; English gloss used: "the holdout towns of the western hills"
- zone VII-Z07: no Dia-thìris name; English gloss used: "an Oirthir Ghaothach, of no shire"
- zone VII-Z08: no Dia-thìris name; English gloss used: "Tìr-dhùthchais nan Tuathach and the pass line"

**routes**

- VII-R01 (the line (Slighe a' Ghuail)): Azgaar draws no "railways" group; drawn as roads
- VII-R02 (the western branch): Azgaar draws no "railways" group; drawn as roads
- VII-R03 (the line to Ceann leathan): Azgaar draws no "railways" group; drawn as roads

<!-- manual: everything below this line is kept when convert_draft.py rewrites the file -->

## Age VII against the master map

Age VII is the master (`Diathir_Atlas/Diathir.map`, DE 27) with the draft's additions. Counts, master → Age VII:

| | master | Age VII | why |
|---|---|---|---|
| states | 2 | 2 | the draft gives the Moot (`Tional nan Tuathach`, 11 northern shires, 343 cells) as a vassal of the kingdom; the master now has it too (legendarium/reconcile/history.json), and the spec draws both anew |
| burgs | 505 | 506 | new burg VII-N01, place id 7001 (the Àth leathan post, cell 2136) |
| provinces | 123 | 123 | same shires, names and arms; the 11 northern shires now belong to the Moot |
| cultures / faiths | 2 / 3 | 2 / 3 | same cells; the culture names are the draft's (`Na Dia-thìrich`, `Na Tuathaich`). Shire 120, which the draft gives to no faith (`Gun chreideamh`), loses the master's faiths (35 cells) |
| markers | 49 | 61 | 12 new markers (VII-K01…K12) |
| routes | 450 | 455 | 5 new routes; the coal line and its branches are drawn as `roads` (Azgaar has no railways) |
| zones | 5 | 9 | 4 new zones (the Long War, the holdout towns, the windy coast, the Tuathaich homeland) |
| added labels | 0 | 3 | the draft's three Dia-thìris labels |
| regiments, markets, deals, journeys | 13, 16, 8058, 1 | same | the master state is used as the base (`base: 1`), so arms, treasury, regiments and the campaign are unchanged |

Other differences: 63 burgs change state (those in the Moot's shires); Caol mhòr (burg 95) is the Moot's capital (group `capital`); 328 burgs get a note (their order or church body, `inferred`, citations); the state label is placed anew by Azgaar; `lore.description` names the age and date. Master marker, zone and route notes are kept. Scale and geography are the master's (0.14 mi/px; latN 57.54, latS 56.12, lonW −13.56, lonE −7.87).

## The name check

`python3 eras/quality/names_check.py eras/specs/age_<K>.json` still reports a few hits. They are false positives or citations:
the Dia-thìris form contains the English core (`Na Seann-Dhaoine`, `An Sloc Mòr`, `Roinn na Rìoghachd`, `fuil-ghuail`), or
the hit is inside a citation such as `App.A holders of the Red Hill`, which is kept as written because it names an appendix section.

## Where the humans came from

The humans' homeland lies east. Manannan's mist lies on the northern and eastern seas, and the only passage runs
north-about, round the north cape and down to the north-west coast. The converter draws the mist zones (IV-Z01 and
V-Z09) on the coastal water north and east of the island. It follows each zone's English name and the age's land
changes about the mist. IV-Z01's stale `sea` field says "west", and the converter logs it and does not follow it.
The departed's label in Age IV has no Dia-thìris text. It is drawn as "Am Falbh" (the Setting-Out) at the
north-westernmost port standing in that age. No note in the specs places the humans or the mist in the west. The
drafts' English prose, which `--prose-notes` would carry, is the drafts' own to correct.
