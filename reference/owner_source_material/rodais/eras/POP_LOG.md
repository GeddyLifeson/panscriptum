# The island's numbers cut to Northern Ireland's (2026-09-25)

The owner's decision: Dia-thìr, some 5,340 square miles since the rescale (eras/RESCALE_LOG.md), should hold about as many people as Northern Ireland, some 1.8 million in the present day (DE 27), and every figure everywhere must match. The script is `eras/pop_sweep.py`; its docstring gives the rules.

## Headline figures

| | before (1,000 people to the unit) | after (50 to the unit) |
|---|---|---|
| people on the land | 35,424,408 | 1,771,220 |
| people within the shires (the head-due's count) | 35,415,000 | 1,770,800 |
| in towns (one in seven) | 4,954,633 | 247,732 |
| Dia-thìrich: in towns / in the country | 4,411,000 / 27,224,000 | 220,600 / 1,361,200 |
| Tuathaich: in towns / in the country within the shires | 543,000 / 3,237,000 | 27,200 / 161,800 |
| the windy coast (the Moot's tally) | near nine thousand | near four hundred and fifty (447) |
| to the square mile, within the shires | ~6,750 | ~337 (~130 to the km²) |
| the largest town, Seann Skell of the west | 74,120 | 3,706 |
| the capital, Cathair dhearg | 10,274 | 514 |
| the Old Faith / Old Spirits / Church, in their towns | 3,177,500 / 1,233,920 / 543,200 | 158,875 / 61,696 / 27,160 |
| the regiments (foot, horse, riflemen, guns) | 5,577, 2,322, 3,022, 79: 11,000 | 1,673, 696, 905, 23: 3,297 |
| the head-due | 18 purses on every 100,000 heads: 6,375 purses | 18 purses on every 5,000 heads: 6,375 purses |
| the Treasury's roll | 9,568 purses | 9,568 purses (unchanged, as the map's treasury) |

### The regiments

| regiment | before | after |
|---|---|---|
| 1 | 826 foot, 581 horse, 398 riflemen and 13 guns (1818) | 248 foot, 174 horse, 119 riflemen and 4 guns (545) |
| 2 | 862 foot, 234 horse, 487 riflemen and 11 guns (1594) | 259 foot, 70 horse, 146 riflemen and 3 guns (478) |
| 3 | 732 foot, 302 horse, 314 riflemen and 7 guns (1355) | 220 foot, 91 horse, 94 riflemen and 2 guns (407) |
| 4 | 684 foot, 266 horse, 364 riflemen and 7 guns (1321) | 205 foot, 80 horse, 109 riflemen and 2 guns (396) |
| 5 | 614 foot, 360 horse, 319 riflemen and 14 guns (1307) | 184 foot, 108 horse, 96 riflemen and 4 guns (392) |
| 6 | 497 foot, 194 horse, 308 riflemen and 8 guns (1007) | 149 foot, 58 horse, 92 riflemen and 2 guns (301) |
| 7 | 437 foot, 224 horse, 230 riflemen and 5 guns (896) | 131 foot, 67 horse, 69 riflemen and 2 guns (269) |
| 8 | 474 foot, 93 horse, 281 riflemen and 4 guns (852) | 142 foot, 28 horse, 84 riflemen and 1 gun (255) |
| 9 | 451 foot, 68 horse, 321 riflemen and 10 guns (850) | 135 foot, 20 horse, 96 riflemen and 3 guns (254) |

### The ages

The era drafts drew each age as a share of the present. The shares are redrawn so every age lies between the Age of Ailean (drawn from the tellings, unchanged) and the present. The people on the island at the close of each age, as the era maps hold them (their towns, with the country scaled as the towns are):

| age | shares of the present, before -> after | people, before -> after |
|---|---|---|
| I | tellings -> tellings | ~18,000 -> ~18,000 |
| II | tellings -> tellings | ~111,000 -> ~111,000 |
| III | 0.035 -> 0.2 | ~1,050,000 -> ~300,000 |
| IV | 0.12 -> 0.35 | ~3,900,000 -> ~569,000 |
| V | 0.45 -> 0.6 | ~15,000,000 -> ~1,023,000 |
| VI | 0.85 -> 0.85 | ~30,100,000 -> ~1,507,000 |
| VII | 1 -> 1 | ~35,424,000 -> ~1,771,000 |

Towns the era drafts give a size to (eras/specs_draft/tools), scaled with their age's share and never above the town's present size:

- age_III.py:234, burg 19 (Cathair dhearg): 3,000 -> 514
- age_III.py:235, burg 315 (Dùn ìseal): 1,200 -> 600
- age_III.py:236, burg 422 (Dùn dhearg): 1,500 -> 500
- age_III.py:237, burg 26 (Cathair dhomhain): 2,500 -> 710
- age_III.py:238, burg 23 (Cathair mhòr): 2,200 -> 630
- age_III.py:239, burg 94 (Seann Vell): 1,800 -> 327
- age_III.py:240, burg 17 (Inis mhòr): 1,500 -> 430
- age_III.py:241, burg 489 (Seann Skell): 2,200 -> 630
- age_III.py:242, burg 419 (Muileann chiar): 600 -> 89
- age_III.py:243, burg 1 (Caol leathan): 1,500 -> 430
- age_III.py:244, burg 166 (Inis thais): 1,200 -> 340
- age_III.py:245, burg 273 (Baile Mòr dhomhain): 1,000 -> 290
- age_III.py:246, burg 18 (Seann Dunn): 900 -> 260
- age_III.py:247, burg 34 (Seann Tarr): 700 -> 190
- age_III.py:248, burg 343 (Cnoc bhàn): 500 -> 140
- age_III.py:249, burg 246 (Muileann chaol): 300 -> 85
- age_III.py:250, burg 77 (Dùn thais): 900 -> 260
- age_III.py:251, burg 22 (Ceann leathan): 900 -> 260
- age_III.py:252, burg 276 (Tobar dhìreach): 250 -> 150
- age_III.py:253, burg 432 (Cnoc dhìreach): 120 -> 35
- age_III.py:254, burg 229 (Muileann ruadh): 250 -> 70
- age_III.py:255, burg 151 (Muileann òg): 400 -> 83
- age_III.py:256, burg 365 (Baile Mòr mhòr): 1,300 -> 480
- age_III.py:257, burg 37 (Seann Toll): 700 -> 200
- age_III.py:258, burg 241 (Baile ruadh): 300 -> 85
- age_III.py:259, burg 119 (Cuan ruadh): 500 -> 180
- age_III.py:260, burg 95 (Caol mhòr): 600 -> 200
- age_IV.py:161, burg 19 (Cathair dhearg): 6,000 -> 514
- age_IV.py:162, burg 23 (Cathair mhòr): 12,000 -> 1,700
- age_IV.py:163, burg 491 (Muileann dhearg): 3,000 -> 440
- age_IV.py:164, burg 489 (Seann Skell): 8,500 -> 1,200
- age_IV.py:165, burg 315 (Dùn ìseal): 2,700 -> 600
- age_IV.py:166, burg 422 (Dùn dhearg): 3,500 -> 510
- age_IV.py:167, burg 273 (Baile Mòr dhomhain): 2,500 -> 360
- age_IV.py:168, burg 76 (Ros fhionn): 1,500 -> 141
- age_IV.py:169, burg 166 (Inis thais): 3,500 -> 510
- age_IV.py:170, burg 20 (Cnoc bheag): 3,500 -> 510
- age_IV.py:171, burg 132 (Seann Skell): 2,700 -> 390
- age_IV.py:172, burg 64 (Seann Warr): 2,400 -> 350
- age_IV.py:173, burg 17 (Inis mhòr): 3,000 -> 440
- age_IV.py:174, burg 297 (Cathair fhada): 2,500 -> 360
- age_IV.py:175, burg 246 (Muileann chaol): 800 -> 120
- age_IV.py:176, burg 443 (Caol gharbh): 900 -> 130
- age_IV.py:177, burg 77 (Dùn thais): 2,000 -> 290
- age_IV.py:178, burg 119 (Cuan ruadh): 1,200 -> 180
- age_IV.py:179, burg 249 (Seann Tarr): 900 -> 130
- age_IV.py:180, burg 305 (Baile chrom): 300 -> 45
- age_IV.py:181, burg 143 (Ceann mhòr): 250 -> 35
- age_IV.py:183, new burg: 300 -> 45
- age_IV.py:184, burg 288 (Muileann gheal): 400 -> 60
- age_IV.py:185, burg 324 (Doire shean): 1,600 -> 230
- age_IV.py:186, burg 30 (Ceann mhin): 2,600 -> 380
- age_IV.py:187, burg 34 (Seann Tarr): 700 -> 190
- age_V.py:189, burg 19 (Cathair dhearg): 4,500 -> 514
- age_V.py:190, burg 27 (Ros dhomhain): 20,000 -> 1,300
- age_V.py:191, burg 354 (Muileann chrom): 12,000 -> 800
- age_V.py:192, burg 44 (Baile thais): 6,000 -> 400
- age_V.py:193, burg 419 (Muileann chiar): 3,000 -> 89
- age_V.py:194, burg 135 (Achadh dhomhain): 6,000 -> 400
- age_V.py:195, burg 224 (Baile dhomhain): 1,500 -> 83
- age_V.py:196, burg 383 (Àth ìseal): 900 -> 60
- age_V.py:197, burg 476 (Cathair gheal): 4,000 -> 270
- age_V.py:198, burg 54 (Muileann àrsaidh): 700 -> 45
- age_V.py:199, burg 160 (Muileann fhionn): 700 -> 45
- age_V.py:200, burg 63 (Ros bheag): 6,000 -> 400
- age_V.py:201, burg 282 (Cuan shean): 9,000 -> 600
- age_V.py:202, burg 304 (Àth àrsaidh): 4,000 -> 270
- age_V.py:203, burg 303 (Baile Mòr ruadh): 2,500 -> 170
- age_V.py:204, burg 313 (Seann Toll): 2,000 -> 130
- age_V.py:205, burg 255 (Dùn chrom): 6,000 -> 400
- age_V.py:206, burg 105 (Baile dhìreach): 800 -> 55
- age_V.py:207, burg 142 (Cnoc ghorm): 5,000 -> 330
- age_V.py:208, burg 143 (Ceann mhòr): 5,000 -> 330
- age_V.py:209, burg 305 (Baile chrom): 3,000 -> 200
- age_V.py:210, burg 246 (Muileann chaol): 2,500 -> 170
- age_V.py:211, burg 152 (Ros dhìreach): 2,500 -> 170
- age_V.py:212, burg 351 (Ceann fhada): 3,000 -> 200
- age_V.py:213, burg 397 (Ceann chaol): 2,400 -> 400
- age_V.py:214, burg 26 (Cathair dhomhain): 12,000 -> 800
- age_V.py:215, burg 77 (Dùn thais): 12,000 -> 800
- age_V.py:216, burg 132 (Seann Skell): 9,000 -> 600
- age_V.py:217, burg 489 (Seann Skell): 30,000 -> 2,000
- age_V.py:276, new burg: 800 -> 55
- age_VII.py:86, new burg: 120 -> 35

Also by hand: `eras/specs_draft/tools/common.py` (the master's scale read from the map, `POP_FACTOR`, `POP_CLAMP`, `KIND_SCALE`, the drafts' `population_scale`), `eras/engine/convert_draft.py` (divides by the master's scale; groups and town works read at the kinds' scale), `legendarium/map_reconcile.py` (world.json's populations at the map's scale), and the population rule in `eras/WRITERS_GUIDE.md`.

The map: `legendarium/reconcile/place.json` sets `units.population.scale` (1,000 -> 50) and the nine regiments' units and totals (record 14), after the military layer's. `legendarium/town_previews.json` is rebuilt from the map at the new scale (Watabou's population, size, width and density tags).

## The changes

Each rule, and where its new text now stands (file:line of the first occurrence in each file).

### The kingdom's heads and the Treasury

- **before:** eighteen purses on every hundred thousand heads
  **after:** eighteen purses on every five thousand heads
  **in:** legendarium/appendices/G_trade.md:162, legendarium/appendices/H_shires.md:53, legendarium/annals/age_VI.json:366, legendarium/annals/age_VII.json:1653, legendarium/reconcile/state.json:999, eras/WRITERS_GUIDE.md:337, eras/age_VI/annals/age_VI_master.json:366, eras/age_VII/annals/age_VII_master.json:1653

- **before:** eighteen purses per hundred thousand heads
  **after:** eighteen purses per five thousand heads
  **in:** legendarium/reconcile/INTEGRATION.md:76

- **before:** The kingdom counted 35,415,000 heads for the head-due
  **after:** The kingdom counted 1,770,800 heads for the head-due
  **in:** legendarium/appendices/H_shires.md:57

- **before:** Together the two peoples number some 35,415,000 within the shires, one in seven of them in a town.
  **after:** Together the two peoples number some 1,770,800 within the shires, one in seven of them in a town.
  **in:** legendarium/appendices/H_shires.md:79

- **before:** | 4,411,000 | 27,224,000 |
  **after:** | 220,600 | 1,361,200 |
  **in:** legendarium/appendices/H_shires.md:75

- **before:** | 543,000 | 3,237,000 within the shires;
  **after:** | 27,200 | 161,800 within the shires;
  **in:** legendarium/appendices/H_shires.md:76

- **before:** some 543,000 people in them.
  **after:** some 27,200 people in them.
  **in:** legendarium/appendices/F_tongues_peoples.md:212, legendarium/reconcile/state.json:1076

- **before:** The Moot's tallies put them near nine thousand, a figure the royal clerks do not accept.
  **after:** The Moot's tallies put them near four hundred and fifty, a figure the royal clerks do not accept.
  **in:** legendarium/appendices/H_shires.md:65

- **before:** The windy coast keeps, by the Moot's tally, about nine thousand people,
  **after:** The windy coast keeps, by the Moot's tally, about four hundred and fifty people,
  **in:** legendarium/appendices/I_land.md:19

- **before:** Sealers, fowlers and herders, near nine thousand by the Moot's tally;
  **after:** Sealers, fowlers and herders, near four hundred and fifty by the Moot's tally;
  **in:** eras/specs_draft/tools/age_VII.py:153

### The faiths, the capital, the cities

- **before:** Counted by the people in their towns, the Old Faith comes first by far, at nearly three million two hundred thousand. The Old Spirits come next, at a little over one million two hundred thousand, and the Church holds some five hundred and forty thousand. Among the orders Macha's is the largest in people, at nearly one million two hundred thousand, close behind the Old Spirits,
  **after:** Counted by the people in their towns, the Old Faith comes first by far, at nearly a hundred and sixty thousand. The Old Spirits come next, at a little over sixty thousand, and the Church holds some twenty-seven thousand. Among the orders Macha's is the largest in people, at nearly sixty thousand, close behind the Old Spirits,
  **in:** legendarium/appendices/B_faiths.md:30

- **before:** Cathair dhearg is counted at 10,274;
  **after:** Cathair dhearg is counted at 514;
  **in:** legendarium/appendices/F_tongues_peoples.md:130

- **before:** The capital and every city of more than twenty thousand people, largest first.
  **after:** The capital and every city of more than a thousand people, largest first.
  **in:** legendarium/appendices/J_arms.md:180

### The regiments

- **before:** The regimental rolls of the present year count 5,577 foot, 3,022 riflemen and 2,322 horse in the nine regiments, with seventy-nine guns. The first regiment is the largest, at 1,818 men, and the eighth and ninth are the smallest, at about 850 each.
  **after:** The regimental rolls of the present year count 1,673 foot, 905 riflemen and 696 horse in the nine regiments, with twenty-three guns. The first regiment is the largest, at 545 men, and the eighth and ninth are the smallest, at about 255 each.
  **in:** legendarium/appendices/C_hosts_wars.md:161, legendarium/reconcile/military.json:614

- **before:** In DE 27 it musters 826 foot, 581 horse, 398 riflemen and 13 guns.
  **after:** In DE 27 it musters 248 foot, 174 horse, 119 riflemen and 4 guns.
  **in:** legendarium/reconcile/prose.json:376

- **before:** In DE 27 it musters 862 foot, 234 horse, 487 riflemen and 11 guns.
  **after:** In DE 27 it musters 259 foot, 70 horse, 146 riflemen and 3 guns.
  **in:** legendarium/reconcile/prose.json:382

- **before:** In DE 27 it musters 732 foot, 302 horse, 314 riflemen and 7 guns.
  **after:** In DE 27 it musters 220 foot, 91 horse, 94 riflemen and 2 guns.
  **in:** legendarium/reconcile/prose.json:388

- **before:** In DE 27 it musters 684 foot, 266 horse, 364 riflemen and 7 guns.
  **after:** In DE 27 it musters 205 foot, 80 horse, 109 riflemen and 2 guns.
  **in:** legendarium/reconcile/prose.json:394

- **before:** In DE 27 it musters 614 foot, 360 horse, 319 riflemen and 14 guns.
  **after:** In DE 27 it musters 184 foot, 108 horse, 96 riflemen and 4 guns.
  **in:** legendarium/reconcile/prose.json:400

- **before:** In DE 27 it musters 497 foot, 194 horse, 308 riflemen and 8 guns.
  **after:** In DE 27 it musters 149 foot, 58 horse, 92 riflemen and 2 guns.
  **in:** legendarium/reconcile/prose.json:406

- **before:** In DE 27 it musters 437 foot, 224 horse, 230 riflemen and 5 guns.
  **after:** In DE 27 it musters 131 foot, 67 horse, 69 riflemen and 2 guns.
  **in:** legendarium/reconcile/prose.json:412

- **before:** In DE 27 it musters 474 foot, 93 horse, 281 riflemen and 4 guns.
  **after:** In DE 27 it musters 142 foot, 28 horse, 84 riflemen and 1 gun.
  **in:** legendarium/reconcile/prose.json:418

- **before:** In DE 27 it musters 451 foot, 68 horse, 321 riflemen and 10 guns.
  **after:** In DE 27 it musters 135 foot, 20 horse, 96 riflemen and 3 guns.
  **in:** legendarium/reconcile/prose.json:424

### The towns, at their new sizes

- **before:** | An Creideamh Sean (Òrd Mhanannain) | 74,120 |
  **after:** | An Creideamh Sean (Òrd Mhanannain) | 3,706 |
  **in:** legendarium/appendices/F_tongues_peoples.md:121

- **before:** | An Creideamh Sean (Òrd Bhrìde) | 57,907 |
  **after:** | An Creideamh Sean (Òrd Bhrìde) | 2,895 |
  **in:** legendarium/appendices/F_tongues_peoples.md:122

- **before:** | Ros dhomhain | An Creideamh Sean (Òrd Mhacha) | 51,589 |
  **after:** | Ros dhomhain | An Creideamh Sean (Òrd Mhacha) | 2,579 |
  **in:** legendarium/appendices/F_tongues_peoples.md:123

- **before:** | Na Seann Spioradan | 49,681 |
  **after:** | Na Seann Spioradan | 2,484 |
  **in:** legendarium/appendices/F_tongues_peoples.md:124

- **before:** | An Creideamh Sean (Òrd an t-Seabhaig) | 49,661 |
  **after:** | An Creideamh Sean (Òrd an t-Seabhaig) | 2,483 |
  **in:** legendarium/appendices/F_tongues_peoples.md:125

- **before:** | Cathair mhòr | An Creideamh Sean (Òrd Mhacha) | 49,298 |
  **after:** | Cathair mhòr | An Creideamh Sean (Òrd Mhacha) | 2,465 |
  **in:** legendarium/appendices/F_tongues_peoples.md:126

- **before:** | An Creideamh Sean (Scoiltean nan Draoidhean) | 42,649 |
  **after:** | An Creideamh Sean (Scoiltean nan Draoidhean) | 2,132 |
  **in:** legendarium/appendices/F_tongues_peoples.md:127

- **before:** | Na Seann Spioradan | 42,136 |
  **after:** | Na Seann Spioradan | 2,107 |
  **in:** legendarium/appendices/F_tongues_peoples.md:128

- **before:** | An Eaglais | 42,002 |
  **after:** | An Eaglais | 2,100 |
  **in:** legendarium/appendices/F_tongues_peoples.md:216

- **before:** | An Eaglais (Eaglais nan Tuathach) | 40,740 |
  **after:** | An Eaglais (Eaglais nan Tuathach) | 2,037 |
  **in:** legendarium/appendices/F_tongues_peoples.md:217

- **before:** | An Eaglais | 32,420 |
  **after:** | An Eaglais | 1,621 |
  **in:** legendarium/appendices/F_tongues_peoples.md:218

- **before:** | An Eaglais (the vigil of the Grey Night) | 27,319 |
  **after:** | An Eaglais (the vigil of the Grey Night) | 1,366 |
  **in:** legendarium/appendices/F_tongues_peoples.md:219

- **before:** | An Eaglais | 25,112 |
  **after:** | An Eaglais | 1,256 |
  **in:** legendarium/appendices/F_tongues_peoples.md:220

- **before:** {{place:burg:19}} | … | 10,300 |
  **after:** {{place:burg:19}} | … | 510 |
  **in:** legendarium/appendices/J_arms.md:184

- **before:** {{place:burg:489}} | … | 74,100 |
  **after:** {{place:burg:489}} | … | 3,710 |
  **in:** legendarium/appendices/J_arms.md:185

- **before:** {{place:burg:27}} | … | 51,600 |
  **after:** {{place:burg:27}} | … | 2,580 |
  **in:** legendarium/appendices/J_arms.md:186

- **before:** {{place:burg:23}} | … | 49,300 |
  **after:** {{place:burg:23}} | … | 2,460 |
  **in:** legendarium/appendices/J_arms.md:187

- **before:** {{place:burg:365}} | … | 35,900 |
  **after:** {{place:burg:365}} | … | 1,790 |
  **in:** legendarium/appendices/J_arms.md:188

- **before:** {{place:burg:166}} | … | 34,900 |
  **after:** {{place:burg:166}} | … | 1,750 |
  **in:** legendarium/appendices/J_arms.md:189

- **before:** {{place:burg:77}} | … | 34,200 |
  **after:** {{place:burg:77}} | … | 1,710 |
  **in:** legendarium/appendices/J_arms.md:190

- **before:** {{place:burg:30}} | … | 32,300 |
  **after:** {{place:burg:30}} | … | 1,620 |
  **in:** legendarium/appendices/J_arms.md:191

- **before:** {{place:burg:26}} | … | 29,400 |
  **after:** {{place:burg:26}} | … | 1,470 |
  **in:** legendarium/appendices/J_arms.md:192

- **before:** {{place:burg:422}} | … | 25,700 |
  **after:** {{place:burg:422}} | … | 1,280 |
  **in:** legendarium/appendices/J_arms.md:193

- **before:** {{place:burg:17}} | … | 24,000 |
  **after:** {{place:burg:17}} | … | 1,200 |
  **in:** legendarium/appendices/J_arms.md:194

- **before:** {{place:burg:63}} | … | 23,800 |
  **after:** {{place:burg:63}} | … | 1,190 |
  **in:** legendarium/appendices/J_arms.md:195

- **before:** {{place:burg:315}} | … | 22,600 |
  **after:** {{place:burg:315}} | … | 1,130 |
  **in:** legendarium/appendices/J_arms.md:196

- **before:** {{place:burg:132}} | … | 22,100 |
  **after:** {{place:burg:132}} | … | 1,110 |
  **in:** legendarium/appendices/J_arms.md:197

- **before:** {{place:burg:255}} | … | 21,100 |
  **after:** {{place:burg:255}} | … | 1,050 |
  **in:** legendarium/appendices/J_arms.md:198

- **before:** {{place:burg:297}} | … | 20,900 |
  **after:** {{place:burg:297}} | … | 1,050 |
  **in:** legendarium/appendices/J_arms.md:199

- **before:** which has never numbered more than a thousand or so,
  **after:** which has never numbered more than fifty or so,
  **in:** legendarium/gazetteer/out_2.json:93

- **before:** though it holds only a few thousand people,
  **after:** though it holds only a hundred or so people,
  **in:** legendarium/gazetteer/out_2.json:147

- **before:** a walled port town of nearly twenty thousand
  **after:** a walled port town of nearly a thousand
  **in:** legendarium/gazetteer/out_2.json:158, legendarium/burg_features.json:364

- **before:** a town of nearly forty thousand on the Abhainn ìseal
  **after:** a town of nearly two thousand on the Abhainn ìseal
  **in:** legendarium/gazetteer/out_2.json:219

- **before:** a port of nearly forty thousand
  **after:** a port of nearly two thousand
  **in:** legendarium/burg_features.json:372

- **before:** It has never grown past seven hundred people.
  **after:** It has never grown past thirty-five people.
  **in:** legendarium/gazetteer/out_2.json:303, legendarium/reconcile/heraldry.json:156

- **before:** a village of twenty-five thousand
  **after:** a village of some twelve hundred
  **in:** legendarium/gazetteer/out_2.json:455

- **before:** Fewer than seven hundred people live there now, among the spoil heaps.
  **after:** Fewer than forty people live there now, among the spoil heaps.
  **in:** legendarium/gazetteer/out_2.json:524

- **before:** a hundred people among the spoil heaps
  **after:** some thirty people among the spoil heaps
  **in:** legendarium/burg_features.json:416

- **before:** It is a large village now, of nearly ten thousand.
  **after:** It is a large village now, of nearly five hundred.
  **in:** legendarium/gazetteer/out_2.json:530

- **before:** It is a large town of twenty thousand.
  **after:** It is a large town of a thousand.
  **in:** legendarium/gazetteer/out_2.json:559

- **before:** a city of more than twenty-five thousand.
  **after:** a city of more than twelve hundred.
  **in:** legendarium/gazetteer/out_2.json:576

- **before:** It is a town of more than twenty thousand, with grain-halls
  **after:** It is a town of more than a thousand, with grain-halls
  **in:** legendarium/gazetteer/out_2.json:592

- **before:** a town of nearly sixty thousand whose harbour
  **after:** a town of nearly three thousand whose harbour
  **in:** legendarium/gazetteer/out_2.json:634

- **before:** the seat of its province, a town of twelve thousand.
  **after:** the seat of its province, a town of six hundred.
  **in:** legendarium/gazetteer/out_2.json:676

- **before:** It is a port town of nearly nine thousand and the older of the two
  **after:** It is a port town of some four hundred and thirty and the older of the two
  **in:** legendarium/gazetteer/out_2.json:700

- **before:** with fourteen thousand people.
  **after:** with seven hundred people.
  **in:** legendarium/gazetteer/out_2.json:712

- **before:** a town of twenty-seven thousand in fact
  **after:** a town of some thirteen hundred in fact
  **in:** legendarium/gazetteer/out_2.json:723

- **before:** It is small, fewer than a thousand people, and its inn
  **after:** It is small, fewer than fifty people, and its inn
  **in:** legendarium/gazetteer/out_2.json:751

- **before:** A farming village of six thousand just south
  **after:** A farming village of three hundred just south
  **in:** legendarium/gazetteer/out_2.json:796

- **before:** It is small, fewer than eight hundred people.
  **after:** It is small, fewer than forty people.
  **in:** legendarium/gazetteer/out_2.json:807

- **before:** It is a small place of fewer than two thousand.
  **after:** It is a small place of fewer than a hundred.
  **in:** legendarium/gazetteer/out_2.json:813

- **before:** It is a large town of nearly seventeen thousand,
  **after:** It is a large town of more than eight hundred,
  **in:** legendarium/gazetteer/out_2.json:819

- **before:** It is a town of five thousand.
  **after:** It is a town of some two hundred and sixty.
  **in:** legendarium/gazetteer/out_2.json:851

- **before:** a temple village of Macha of twenty-four thousand
  **after:** a temple village of Macha of some twelve hundred
  **in:** legendarium/gazetteer/out_2.json:857

- **before:** a church village of twenty-four thousand
  **after:** a church village of some twelve hundred
  **in:** legendarium/burg_features.json:462

- **before:** the eastern mining district, a town of nearly nineteen thousand.
  **after:** the eastern mining district, a town of nearly a thousand.
  **in:** legendarium/gazetteer/out_2.json:867

- **before:** It is a town of eleven thousand.
  **after:** It is a town of some five hundred and seventy.
  **in:** legendarium/gazetteer/out_2.json:879

- **before:** It is a fishing village of three thousand.
  **after:** It is a fishing village of a hundred and fifty.
  **in:** legendarium/gazetteer/out_2.json:885

- **before:** is a town of twenty thousand built around
  **after:** is a town of a thousand built around
  **in:** legendarium/gazetteer/out_2.json:891

- **before:** Fewer than a thousand people live there now.
  **after:** Fewer than fifty people live there now.
  **in:** legendarium/gazetteer/out_2.json:897

- **before:** though it holds under three thousand people.
  **after:** though it holds under a hundred and fifty people.
  **in:** legendarium/gazetteer/out_2.json:925

- **before:** It is a town of nearly nine thousand and the market
  **after:** It is a town of some four hundred and fifty and the market
  **in:** legendarium/gazetteer/out_2.json:931

- **before:** a river port of more than forty thousand
  **after:** a river port of more than two thousand
  **in:** legendarium/gazetteer/out_2.json:953

- **before:** harbour town of forty thousand crowned
  **after:** harbour town of two thousand crowned
  **in:** legendarium/burg_features.json:476

- **before:** a mill town of fourteen thousand
  **after:** a mill town of some seven hundred
  **in:** legendarium/gazetteer/out_2.json:969

- **before:** It has fewer than a thousand people.
  **after:** It has fewer than fifty people.
  **in:** legendarium/gazetteer/out_2.json:979

- **before:** It is a town of nearly ten thousand.
  **after:** It is a town of nearly five hundred.
  **in:** legendarium/gazetteer/out_2.json:1021

- **before:** It is a small village of fewer than two thousand.
  **after:** It is a small village of fewer than a hundred.
  **in:** legendarium/gazetteer/out_2.json:1039

- **before:** a city of seventy-four thousand and the largest place
  **after:** a city of some three thousand seven hundred and the largest place
  **in:** legendarium/gazetteer/out_2.json:1045

- **before:** a town of twenty thousand at a ford
  **after:** a town of a thousand at a ford
  **in:** legendarium/gazetteer/out_2.json:1068, legendarium/reconcile/heraldry.json:191

- **before:** It is small, fewer than seven hundred people.
  **after:** It is small, fewer than forty people.
  **in:** legendarium/gazetteer/out_2.json:807

- **before:** a white town of nine thousand
  **after:** a white town of some four hundred and seventy
  **in:** legendarium/gazetteer/out_2.json:1090

- **before:** It is a town of three thousand in the eastern mining district.
  **after:** It is a town of a hundred and fifty in the eastern mining district.
  **in:** legendarium/gazetteer/out_2.json:1100

- **before:** It is a port town of four thousand.
  **after:** It is a port town of two hundred.
  **in:** legendarium/gazetteer/out_2.json:1106

- **before:** a town of ten thousand that grew
  **after:** a town of five hundred that grew
  **in:** legendarium/gazetteer/out_2.json:1124

- **before:** a town of nearly five thousand, of quarrymen
  **after:** a town of some two hundred and thirty, of quarrymen
  **in:** legendarium/gazetteer/out_2.json:1130

- **before:** a town of thirty-four thousand with a citadel
  **after:** a town of some seventeen hundred with a citadel
  **in:** legendarium/gazetteer/out_2.json:1140

- **before:** It has fewer than seven hundred people and lives on the garrison.
  **after:** It has fewer than forty people and lives on the garrison.
  **in:** legendarium/gazetteer/out_2.json:1150

- **before:** its twelve thousand people guard
  **after:** its six hundred people guard
  **in:** legendarium/gazetteer/out_2.json:1161

- **before:** population 74,120 is the largest of all 505 burgs
  **after:** population 3,706 is the largest of all 505 burgs
  **in:** legendarium/reconcile/heraldry.json:185

### Deaths counted in one town

- **before:** kills some two hundred before it burns out
  **after:** kills some thirty before it burns out
  **in:** legendarium/annals/age_IV.json:670, eras/age_IV/annals/age_IV_master.json:670

- **before:** A coughing sickness killed some two hundred at
  **after:** A coughing sickness killed some thirty at
  **in:** legendarium/appendices/C_hosts_wars.md:181

- **before:** A spotted fever kills some three hundred at Inis chrom
  **after:** A spotted fever kills some forty at Inis chrom
  **in:** legendarium/annals/age_IV.json:1474, eras/age_IV/annals/age_IV_master.json:1474

- **before:** a spotted fever some three hundred at {{place:burg:92}}
  **after:** a spotted fever some forty at {{place:burg:92}}
  **in:** legendarium/appendices/C_hosts_wars.md:181

- **before:** a spotted fever killed some three hundred at Inis chrom
  **after:** a spotted fever killed some forty at Inis chrom
  **in:** legendarium/book/age_IV.md:196

- **before:** The Mission counts four hundred and six dead.
  **after:** The Mission counts twenty-seven dead.
  **in:** legendarium/annals/age_V.json:867, eras/age_V/annals/age_V_master.json:867

- **before:** The Mission counted four hundred and six dead.
  **after:** The Mission counted twenty-seven dead.
  **in:** legendarium/book/age_V.md:119

- **before:** the Mission counts four hundred and six dead
  **after:** the Mission counts twenty-seven dead
  **in:** legendarium/appendices/F_tongues_peoples.md:176

- **before:** killed four hundred and six by the Mission's count
  **after:** killed twenty-seven by the Mission's count
  **in:** legendarium/appendices/C_hosts_wars.md:181

- **before:** | 406 by the Mission;
  **after:** | 27 by the Mission;
  **in:** legendarium/appendices/C_hosts_wars.md:197

- **before:** the pox killed 406.
  **after:** the pox killed 27.
  **in:** legendarium/burg_features.json:28

- **before:** kept the dead below two hundred
  **after:** kept the dead below fifteen
  **in:** legendarium/annals/age_V.json:1210, eras/age_V/annals/age_V_master.json:1210

- **before:** keeping the dead under two hundred
  **after:** keeping the dead under fifteen
  **in:** legendarium/book/age_V.md:147

- **before:** Two hundred and sixty die.
  **after:** Seventeen die.
  **in:** legendarium/annals/age_V.json:2028, eras/age_V/annals/age_V_master.json:2028

- **before:** and two hundred and sixty died there.
  **after:** and seventeen died there.
  **in:** legendarium/book/age_V.md:261

- **before:** killed two hundred and sixty at Baile Mòr ruadh
  **after:** killed seventeen at Baile Mòr ruadh
  **in:** legendarium/appendices/C_hosts_wars.md:173

- **before:** | 260 of drought-fever at Baile Mòr ruadh |
  **after:** | 17 of drought-fever at Baile Mòr ruadh |
  **in:** legendarium/appendices/C_hosts_wars.md:200

- **before:** puts the dead at Doire ghlas above two hundred
  **after:** puts the dead at Doire ghlas above ten
  **in:** legendarium/appendices/C_hosts_wars.md:183, legendarium/annals/age_VI.json:31, eras/age_VI/annals/age_VI_master.json:31

- **before:** more than two hundred were buried that winter
  **after:** more than ten were buried that winter
  **in:** legendarium/book/age_VI.md:20

- **before:** | above 200 (Tuathaich memory) |
  **after:** | above 10 (Tuathaich memory) |
  **in:** legendarium/appendices/C_hosts_wars.md:203

- **before:** a little over nine hundred
  **after:** a little over forty
  **in:** legendarium/book/age_VI.md:61, legendarium/appendices/C_hosts_wars.md:177, legendarium/annals/age_VI.json:187, legendarium/reconcile/military.json:601, eras/specs_draft/tools/age_VI.py:288, eras/age_VI/annals/age_VI_master.json:187

- **before:** Twenty-three townsfolk die.
  **after:** Three townsfolk die.
  **in:** legendarium/annals/age_V.json:3132, eras/age_V/annals/age_V_master.json:3132

- **before:** and burned the town behind it, killing twenty-three
  **after:** and burned the town behind it, killing three
  **in:** legendarium/appendices/C_hosts_wars.md:83

- **before:** | Twenty-three townsfolk dead |
  **after:** | Three townsfolk dead |
  **in:** legendarium/appendices/C_hosts_wars.md:127

- **before:** and twenty-three townsfolk died.
  **after:** and three townsfolk died.
  **in:** legendarium/book/age_V.md:437

- **before:** the fishing town behind it set burning; twenty-three dead
  **after:** the fishing town behind it set burning; three dead
  **in:** eras/specs_draft/tools/age_V.py:205

- **before:** | a little over 900 |
  **after:** | a little over 40 |
  **in:** legendarium/appendices/C_hosts_wars.md:204

### The notes on the eras' populations

- **before:** - **Ages III–VI** default to the master population × 0.035, 0.12, 0.45 or 0.85, clamped per age, with overrides   for towns the annals give a size to.
  **after:** - **Ages III–VI** default to the master population × 0.2, 0.35, 0.6 or 0.85, clamped per age, with overrides   for towns the annals give a size to (never above the town's present size). The master counts 50 people to   its population unit, some 1.8 million on the island (see `../POP_LOG.md`); the shares keep every age between   the Age of Ailean, whose figures come from the tellings, and the present. Each age's kinds are read from its   populations as they were when the shares were first set (`KIND_SCALE` in `tools/common.py`).
  **in:** eras/specs_draft/README.md:61

- **before:** - Populations are in Azgaar's units: a burg's `population` is in thousands (8.6 = 8,600).
  **after:** - Populations are in Azgaar's units: a burg's `population` times the master's `units.population.scale`   (50 people to the unit since the owner's decision of 2026-09-25) is its people (8.6 = 430). The drafts give   people; `convert_draft.py` divides by the master's scale.
  **in:** eras/engine/SPEC.md:71

- **before:** distance scale 0.14 mi/px;
  **after:** distance scale 0.14 mi/px; population scale 50 people to the unit (some 1.8 million);
  **in:** eras/maps/README.md:22

## Reviewed and kept

- the tellings' counts of the Ancient Age and the Age of Ailean (four hundred with their beasts in the cistern fort, three thousand spears, some four hundred of Ailean's blood in the river, nine hundred knots on the cord, three thousand strokes on the counting wall): the figures of the tellings; none came from the map, and the era drafts keep Age II as the tellings give it (some 110,000 on the island).
- the census of hands, eleven thousand four hundred households holding the right and some two thousand refused (II-0143, book III): fits the Holy Age redrawn at a fifth of the present, some 300,000 people.
- some three hundred dead at the ford of Àth shean (III-0106, B, C, book IV): a battle of the whole realm, some 570,000 people in the Age of Sundering; not a town's count.
- some four thousand people on the salt flats of Ros fhionn in a single day (Age IV): the great fair drew from the whole island (some 570,000).
- the strangers' fever: ninety-one Dia-thìrich and eleven humans (IV-0034): spread down the whole west coast; small beside it.
- eleven, fourteen, seven and thirty-one dead in the galleries, eighteen and twenty-three drowned by Am Fuath Mòr and the storm at Baile ghorm, five killed in the first bloodshed: counts of a gallery, a boat or a street, small beside their towns.
- the human families left on the island, a few thousand in all, behind the walls of Ros bheag and marched north (IV-0363, V truce; era Age V refugee camp of 3,000): the humans were counted apart from the map's peoples; their descendants are the Tuathaich, now some 189,000 with the northern towns that took them in.
- a barracks for two hundred at Dùn chrom (IV id), the guild's sick-roll of four hundred men (V id), a column of holdouts some hundreds strong and their dead in the hundreds (VI ids): beside regiments of some 3,300 men and an island of 1.5 to 1.8 million, as they stand.
- the Administration's census rounded to the hundred, and to the thousand in the hill districts (IV-0246): district counts of an island of about a million.
- a village of forty houses become a town of four hundred at Ceann chaol (IV-0212): the town has 476 people today; the Age V draft now gives it 400, as the annal does.
- the four fleets, six hulls, about a hundred men to a hull: the fleets are not cut.
- INTEGRATION.md and reconcile/state.json, land.json: the recount of 2026-09 (36,225,000 -> 35,412,000 heads, the frozen coast's 397,430 people, the Moot's tally of seven or nine thousand): the record of how the map was reconciled, in the map's units of that day (1,000 people to the unit); the numbers as they stand now are here.
- reconcile/military.json: the notes "— infantry: 826 ..." of its regiment edits: set aside by the prose layer (its "skip"); never on the map.
- the Treasury's roll, 9,568 purses: 6,375 from the head-due and 3,193 from the market-due; the market-courts' 8,058 dealings and the sales in purses (appendix G): the map's treasury and trade are unchanged; the head-due's rate is written per five thousand heads so that the roll still adds up.

## Oddities for the owner

- The generator's towns are many and small: 505 of them hold one person in seven, and at 1.8 million the largest (Seann Skell of the west) has 3,706 people and the capital, Cathair dhearg, 514. The relative sizes are kept as asked; a real capital would need the urbanization rate raised, and even then no town could be large without breaking the shares every table gives.
- The Tuathaich number some 189,000 today; the humans left on the island at the Severance were "a few thousand", about a hundred years before. The northern towns that were Dia-thìreach before the Severance account for part of it.
