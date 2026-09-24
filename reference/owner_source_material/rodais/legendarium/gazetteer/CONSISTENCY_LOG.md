# Gazetteer consistency log

Pass over `out_0.json`, `out_1.json`, `out_2.json` against `PLACE_FACTS.txt` (markers, disaster zones, regiments and fleets, by burg id).
53 entries changed, 63 edits. Each line: burg id (name), field: before → after, then the reason. Only the changed sentence or phrase is quoted.

Rules applied: a burg may mention a marker, zone or garrison belonging to another burg only as a true neighbour relation (checked against map distance). Only burgs listed in a zone say they were struck. Every zone burg now names its disaster, and every marker, regiment and fleet burg names its thing. Founding fields were not touched.

## Changes

- **12** (Àth fhiadhaich), history: “and the famous tavern An Sligeanach Fad' às stands on the road just outside it.” → “and the famous tavern An Sligeanach Fad' às stands at Ceann bhàn, a short way down the road.” — *inn belongs to burg 203*
- **12** (Àth fhiadhaich), known_for: “river-mouth harbour and An Sligeanach Fad' às” → “river-mouth harbour of the eastern road” — *inn belongs to burg 203*
- **13** (Achadh àrsaidh), history: “No record says who laid them.” → “No record says who laid them. Tiormachd Achadh shean, the Long Drought, struck it in the Age of Strangers and parched its hay-meadows for three dry seasons running.” — *drought zone struck burg 13*
- **14** (Seann Chwen), history: “Its people keep the capital's faith of the Dark Unicorn.” → “Its people keep the capital's faith of the Dark Unicorn, and its green is one of the two grounds where the travelling circus, An Siorcas Siubhail Do-thuigsinn, pitches.” — *circus marker 36 is at burg 14*
- **20** (Cnoc bheag), history: “Since the Severance it has faced” → “A' Phlàigh Uaine, the Green Death, struck the town in the Age of Strangers. Since the Severance it has faced” — *plague zone struck burg 20*
- **25** (Inis ìseal), history: “It is a city by rank and a barracks in practice.” → “The Green Death, A' Phlàigh Uaine, struck its garrison in the Age of Strangers, and it is a city by rank and a barracks in practice.” — *plague zone struck burg 25*
- **50** (Àth gharbh), history: “is a walled town of the south-west whose fame is Am Buabhall Fortanach, the great roadside tavern that stands outside its gate. The tavern fortified” → “is a walled town of the south-west, a short walk from Doire shean and its great roadside tavern, Am Buabhall Fortanach. That tavern fortified” — *inn belongs to burg 324*
- **50** (Àth gharbh), known_for: “Am Buabhall Fortanach and the First Fleet” → “the First Fleet's walled ford town” — *inn belongs to burg 324*
- **58** (Muileann uaine), history: “The Green Death passed through it, and since then the second sense of 'uaine' has clung to its name.” → “It is not the Muileann uaine of the Cnoc bheag country that the Green Death struck, though the two are often confused.” — *plague struck burg 274, not 58*
- **58** (Muileann uaine), known_for: “ore-crushing mill of the Green Death” → “ore-crushing mill of the interior workings” — *plague struck burg 274, not 58*
- **78** (Muileann chiar), history: “It is not the silver town of the same name.” → “Tiormachd Achadh shean, the Long Drought, struck it in the Age of Strangers. It is not the silver town of the same name.” — *drought zone struck burg 78*
- **81** (Doire dhearg), history: “The Green Death took many of its people, and the village that remains keeps the ancestor rite.” → “Many of its people left when the workings moved on, and the village that remains keeps the ancestor rite.” — *burg 81 not in plague zone*
- **87** (Ros dhìreach), history: “It was walled after the Severance,” → “A' Phlàigh Uaine, the Green Death, struck it in the Age of Strangers. It was walled after the Severance,” — *plague zone struck burg 87*
- **99** (Cnoc ruadh), history: “The Long Drought emptied half its folds, and it has never quite regained its old number of flocks.” → (removed). *burg 99 not in drought zone*
- **101** (Doire mhòr), history: “It lies a short way from Cill ghlas, and it buried some of the dead of the Rending.” → (removed). *burg 101 not in Rending zone and not near Cill ghlas*
- **108** (Àth dhearg), history: “It suffered through the Green Death and the Long Drought. It is not the Àth dhearg whose name the northern lighthouse bears.” → “It is neither the Àth dhearg whose name the northern lighthouse bears nor the western ford that the Great Hunger struck.” — *burg 108 in neither plague nor drought zone*
- **124** (Àth uaine), history: “The Green Death hit it hard, and its plague graves lie in the field by the ford,” → “Its camp graves lie in the field by the ford,” — *burg 124 not in plague zone*
- **124** (Àth uaine), known_for: “plague graves of the camp years” → “camp graves by the green ford” — *burg 124 not in plague zone*
- **127** (Seann Vell), history: “The fleet named for Cuan shean lies off its shore.” → “An ceathramh cabhlach is stationed at Cuan shean, a short way up the coast.” — *fleet stationed at burg 282*
- **129** (Cnoc shean), history: “Its common is one of the two grounds where the travelling circus, An Siorcas Siubhail Do-thuigsinn, pitches.” → “Its common holds the market of the farms around it.” — *circus markers are at burgs 55 and 14*
- **129** (Cnoc shean), known_for: “circus ground on the old hill” → “market common on the old hill” — *circus markers are at burgs 55 and 14*
- **143** (Ceann mhòr), history: “It was a Dia-thìrich port of the Holy Age, resettled by the Tuathaich after the Severance.” → “It was a Dia-thìrich port of the Holy Age, struck by Gorta Baile chrom in the Age of Strangers and resettled by the Tuathaich after the Severance.” — *famine zone struck burg 143*
- **162** (Seann Vell), history: “An Taigh-seinnse Mòr stands on the road just east of it.” → “An Taigh-seinnse Mòr stands just east of it, at the quay of Cuan chrom.” — *inn belongs to burg 418*
- **162** (Seann Vell), known_for: “An Taigh-seinnse Mòr on the harbour road” → “walled harbour on the Cuan chrom road” — *inn belongs to burg 418*
- **173** (Tobar ìseal), history: “and the drought of the Age of Strangers proved the builders right.” → “and the dry summers since have proved the builders right.” — *burg 173 not in drought zone*
- **219** (Àth chaol), history: “It keeps the old spirits of the Dia-thìrich and felt the Long Drought of Achadh shean hard, when the ford ran dry for three seasons.” → “It keeps the old spirits of the Dia-thìrich, and its ford runs low in the dry months.” — *burg 219 not in drought zone*
- **219** (Àth chaol), known_for: “the ford that ran dry” → “narrow ford on the Inis mhin road” — *burg 219 not in drought zone*
- **220** (Cnoc bheag), history: “The Long Drought emptied its pastures for a time, and the town has never fully recovered its herds.” → “Its pastures are thin, and the town has always kept fewer herds than its walls could shelter.” — *burg 220 not in drought zone*
- **223** (Cuan àrsaidh), history: “It follows the capital's faith of the Dark Unicorn.” → “The Green Death, A' Phlàigh Uaine, struck the harbour in the Age of Strangers. It follows the capital's faith of the Dark Unicorn.” — *plague zone struck burg 223*
- **229** (Muileann ruadh), history: “It is a place for the sick and the old to bathe, and a Toll-dubh no one has explored lies nearby.” → “It is a place for the sick and the old to bathe.” — *dungeons are at burgs 80 and 505, both far off*
- **241** (Baile ruadh), history: “The Long Drought of Achadh shean hit its fields hard, and it keeps the old spirits and trades grain with Achadh naomh.” → “It keeps the old spirits and trades grain with Achadh naomh.” — *burg 241 not in drought zone*
- **242** (Achadh àrsaidh), history: “It was resettled by the Tuathaich after the Severance and keeps the Yellow Scorpion.” → “Gorta Baile chrom, the Great Hunger, struck it in the Age of Strangers; it was resettled by the Tuathaich after the Severance and keeps the Yellow Scorpion.” — *famine zone struck burg 242*
- **274** (Muileann uaine), history: “It lies near the unclaimed forest of Coille Naomh Cnoc bheag, and its millers will not cut timber from it.” → “A' Phlàigh Uaine, the Green Death, struck it in the Age of Strangers, and since then the second sense of 'uaine' has clung to its name.” — *plague zone struck burg 274; Coille Naomh Cnoc bheag is far away at burg 504*
- **284** (Baile ìseal), history: “A low town in the middle east, close enough to Cill ghlas that the Rending cracked its houses. It was rebuilt within a generation.” → “A low town in the middle east, a short way south of Cill ghlas and the ground the Rending tore open.” — *burg 284 not in Rending zone*
- **284** (Baile ìseal), known_for: “houses rebuilt after the Rending” → “grain town south of Cill ghlas” — *burg 284 not in Rending zone*
- **300** (Cnoc uaine), history: “sends its young to the fleet at Doire shean's harbour.” → “sends its young to the first fleet at Àth gharbh.” — *fleet stationed at burg 50*
- **305** (Baile chrom), history: “Whether the Great Hunger took its name from this Baile chrom or another is not settled in the record.” → “Gorta Baile chrom, the Great Hunger, takes its name from this town, which it struck in the Age of Strangers.” — *famine zone struck burg 305*
- **313** (Seann Toll), history: “and it was badly shaken by the Rending at nearby Cill ghlas.” → “and it stands a short way west of Cill ghlas, where the Rending opened.” — *burg 313 not in Rending zone*
- **317** (Àth chrom), history: “A small ford on a bent stream near Cill ghlas, where the Rending opened. The ford shifted after the collapse and had to be re-cut.” → “A small ford on a bent stream south of Cill ghlas, where the Rending opened.” — *burg 317 not in Rending zone*
- **317** (Àth chrom), known_for: “the ford moved by the Rending” → “bent ford south of Cill ghlas” — *burg 317 not in Rending zone*
- **334** (Baile dhearg), history: “It keeps the old spirits and felt the Long Drought of Achadh shean.” → “It keeps the old spirits.” — *burg 334 not in drought zone*
- **335** (Muileann àrsaidh), history: “It was resettled by the Tuathaich after the Severance and follows the Yellow Scorpion.” → “Gorta Baile chrom, the Great Hunger, struck it in the Age of Strangers, and it was resettled by the Tuathaich after the Severance. It follows the Yellow Scorpion.” — *famine zone struck burg 335*
- **336** (Achadh fhada), history: “Its fields feed the Hawk-faith mill at Muileann uaine.” → “A' Phlàigh Uaine, the Green Death, struck it in the Age of Strangers. Its fields feed the Hawk-faith mill at Muileann uaine.” — *plague zone struck burg 336*
- **344** (Àth uaine), history: “It lives now on toll and on the soldiers who still keep the tower.” → “Tiormachd Achadh shean, the Long Drought, struck it in the Age of Strangers, and it lives now on toll and on the soldiers who still keep the tower.” — *drought zone struck burg 344*
- **355** (Muileann chiar), history: “and suffered badly when Scàineadh Cill ghlas tore the hills open nearby and closed the district for a generation.” → “and lost its trade when Scàineadh Cill ghlas, a short way west, closed the district for a generation.” — *burg 355 not in Rending zone*
- **371** (Inis bhàn), history: “It is one of several harbours” → “The Green Death, A' Phlàigh Uaine, struck it in the Age of Strangers. It is one of several harbours” — *plague zone struck burg 371*
- **389** (Achadh chaol), history: “It suffered in the Green Death and again when the diggings closed after Scàineadh Cill ghlas.” → “Scàineadh Cill ghlas, the Rending, struck it when the fault tore open, and the diggings it fed were closed after.” — *burg 389 in Rending zone, not plague zone*
- **413** (Baile leathan), history: “Baile leathan is the town nearest Leabharlann Muileann chaol,” → “Baile leathan is one of the towns nearest Leabharlann Muileann chaol,” — *burgs 487 and 348 lie nearer the library*
- **420** (Baile àrsaidh), history: “with the fleet at Cuan shean to the west.” → “with the fleet at Cuan shean to the south.” — *Cuan shean (burg 282) lies south*
- **423** (Baile òg), history: “It suffered in the Green Death and again when Scàineadh Cill ghlas closed the district for a generation.” → “It emptied when Scàineadh Cill ghlas closed the district for a generation.” — *burg 423 not in plague zone*
- **430** (Muileann bheag), history: “Muileann bheag is a fort with a citadel astride Imrich nam Pantar, the panther roads, where the island's great cats cross at fixed intervals.” → “Muileann bheag is a fort with a citadel north of Baile dhomhain, whose fields the panthers of Imrich nam Pantar cross.” — *migration marker 40 is at burg 257*
- **430** (Muileann bheag), known_for: “citadel astride the panther roads” → “citadel north of the panther roads” — *migration marker 40 is at burg 257*
- **435** (Tobar fhiadhaich), history: “even in the Long Drought.” → “even in the driest years.” — *burg 435 not in drought zone*
- **445** (Àth dhearg), history: “A red ford on the western coast below the lighthouse of Baile chrom, resettled” → “A red ford on the western coast below the lighthouse of Baile chrom, struck by Gorta Baile chrom in the Age of Strangers and resettled” — *famine zone struck burg 445*
- **450** (Ceann òg), history: “It follows the Hawk,” → “The Green Death, A' Phlàigh Uaine, struck it in the Age of Strangers. It follows the Hawk,” — *plague zone struck burg 450*
- **451** (Àth chrom), history: “It was nearly abandoned in the Long Drought, when its ford ran dry and the carts no longer needed it. It lives on the road again.” → “It lives on the road and has never been more than a crossing.” — *burg 451 not in drought zone*
- **472** (Àth fhionn), history: “below the lighthouse of Baile chrom, resettled” → “below the lighthouse of Baile chrom, struck by Gorta Baile chrom in the Age of Strangers and resettled” — *famine zone struck burg 472*
- **477** (Muileann bheag), history: “not the fort of the panther roads” → “not the fort above the panther roads” — *migration marker 40 is at burg 257*
- **479** (Baile dhomhain), history: “Its trade goes down” → “A' Phlàigh Uaine, the Green Death, struck it in the Age of Strangers. Its trade goes down” — *plague zone struck burg 479*
- **480** (Baile ghlas), history: “It suffered in the Long Drought.” → (removed). *burg 480 not in drought zone*
- **491** (Muileann dhearg), known_for: “red mill scarred by the Scàineadh” → “red mill beside Cill ghlas” — *burg 491 not in Rending zone*
- **499** (Cill thais), history: “lies at anchor below it, and its priests bless” → “is stationed at Cuan shean below, and the village's priests bless” — *fleet stationed at burg 282*
- **505** (Muileann ruadh), history: “It is not the Muileann ruadh of the warm springs to the west.” → “The unexplored hollow called Toll-dubh lies close by, and the townsfolk keep away from it. It is not the Muileann ruadh of the warm springs to the west.” — *dungeon marker 20 is at burg 505*

## Checked and left as they are

- Encounter markers (`Coinneachadh`, burgs 406, 202, 443, 242, 277) and the party marker (`A' Bhuidheann`, burg 11) are game-state markers rather than places, so none were added to the text.
- Neighbour claims were kept where the map distance supports them. Examples: 146 beside Allt an Àigh, 252 and 386 by the silver seam, 395 near An Sligeanach Fad' às, 30 and 290 taking in Great Wave survivors, 415 and 491 idled by the Rending's closure of the district.
- Local markets and wool or drove fairs (46, 181, 400, 438) are left in. They are not Fèill Muileann òg and do not claim to be.
- The three stone inscriptions (20/450, 243/145, 392) come from `chronicle_canon.json` and are left unchanged.
- JSON check: all three files parse, and their key sets match the originals (169 / 169 / 167 entries).
