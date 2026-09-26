# The rescale and the move into the Atlantic (2026-09-25)

The owner's decisions: Dia-thìr about the size of Northern Ireland (the map's distance scale 0.2 -> 0.14 miles to the unit: lengths x0.7, areas x0.49, travel times x0.7 rounded as a teller would, densities x2.04; town counts and populations unchanged), and the island alone in the Atlantic west of the Outer Hebrides, with the humans' homeland east of it, Manannan's mist on the eastern sea, and the one passage through the mist running north-about (which is why the harbours of the Crossing are on the west coast). The Otherworld stays west.

Headline figures (land 272,668 map units of area; frame 1536 x 702 units):

| | at 0.2 mi/unit | at 0.14 mi/unit |
|---|---|---|
| the land with its islands | ~10,900 sq mi | ~5,340 sq mi (~13,840 km²) |
| the shires | ~10,720 sq mi | ~5,250 sq mi |
| Dia-thìrich / Tuathaich country | ~9,220 / ~1,680 sq mi | ~4,520 / ~825 sq mi |
| the windy coast | ~190 sq mi | ~93 sq mi |
| Loch chrom | ~74 sq mi | ~36 sq mi |
| the island, west to east / north to south (land bounding box) | ~220 x ~103 mi | ~154 x ~72 mi |
| Fenn's line (IV-0027a) | 221 mi, 45 of sea | 155 mi, 30 of sea |
| the Leaden Hawk (IV-0342a..e) | 80 mi on foot in 3+ days; 2 + 2 days by carriage; 8 days in all | 55 mi in 2+ days; 1½ + 1½ days; 6 days |
| the map frame | 307 x 140 mi, 54.2-56.2 N, 8.0-3.6 W | 215 x 98 mi, 56.12-57.54 N, 13.56-7.87 W |
| people within the shires (35,415,000, unchanged) | ~3,300 a sq mi | ~6,750 a sq mi (~2,600 a km²) |
| (since cut to 1,770,800 by the owner's later decision: ~337 a sq mi; see POP_LOG.md) | | |

The map: legendarium/reconcile/place.json (the last layer of map_reconcile.py) sets the scale and the frame and sets aside the earlier layers' scale and frame edits; the climate layer's temperatures are computed for the frame they were set in (recompute_temperature 'frame'), so the weather does not change. The land's middle is near 56.9 N 11.1 W; the eastern cape is some 62 miles west of Barra, the south coast some 100 miles north-west of the Donegal coast, the north-east of the island some 50 miles south-west of St Kilda; the frame holds no real coast. The Leaden Hawk's eves in annals/age_V.json were set to 2, 1, 1, 2 days.

Towns the lore ties to the Crossing, all on the west coast and all left where they are: the meeting off the north-west cape by Achadh àrsaidh (burg 242, marker 45), Ceann mhòr (143), Cuan shean (282), Ros bheag (63), Seann Skell of the west (16), Baile dhìreach (105).

## The changes

Each rule, and where its new text now stands (file:line of the first occurrence in each file).

### Distances, areas and travel times

- **before:** Dia-thìr is a little over two hundred miles from the capes of the far north-west to the eastern cape, and nowhere much more than a hundred miles from the north coast to the south. The main island covers about eleven thousand square miles. Twelve small islands lie off its coasts, and the largest of them is some seventeen square miles.
  **after:** Dia-thìr is a little over a hundred and fifty miles from the capes of the far north-west to the eastern cape, and nowhere much more than seventy miles from the north coast to the south. The main island covers about five thousand three hundred square miles, near fourteen thousand of the square measure the humans call the kilometre. Twelve small islands lie off its coasts, and the largest of them is some eight square miles.
  **in:** legendarium/appendices/I_land.md:7

- **before:** about a hundred and ninety square miles that no shire holds
  **after:** about ninety-three square miles that no shire holds
  **in:** legendarium/appendices/I_land.md:19

- **before:** a single massif about seventy miles from west to east and thirty-five from north to south
  **after:** a single massif about fifty miles from west to east and twenty-five from north to south
  **in:** legendarium/appendices/I_land.md:23

- **before:** the longest river on Dia-thìr, about fifty-three miles.
  **after:** the longest river on Dia-thìr, about thirty-seven miles.
  **in:** legendarium/appendices/I_land.md:39

- **before:** **Abhainn fhionn**, about forty-five miles.
  **after:** **Abhainn fhionn**, about thirty-two miles.
  **in:** legendarium/appendices/I_land.md:41

- **before:** **Abhainn uaine**, about forty miles.
  **after:** **Abhainn uaine**, about twenty-eight miles.
  **in:** legendarium/appendices/I_land.md:43

- **before:** **Abhainn chaol**, about thirty-four miles.
  **after:** **Abhainn chaol**, about twenty-four miles.
  **in:** legendarium/appendices/I_land.md:45

- **before:** **Abhainn gheal**, the northern, about thirty-one miles.
  **after:** **Abhainn gheal**, the northern, about twenty-two miles.
  **in:** legendarium/appendices/I_land.md:47

- **before:** **Abhainn dhomhain**, the capital's river, about thirty miles.
  **after:** **Abhainn dhomhain**, the capital's river, about twenty-one miles.
  **in:** legendarium/appendices/I_land.md:49

- **before:** **Abhainn naomh**, the western, about thirty miles.
  **after:** **Abhainn naomh**, the western, about twenty-one miles.
  **in:** legendarium/appendices/I_land.md:51

- **before:** **Abhainn gheal**, the lake river, about twenty-four miles.
  **after:** **Abhainn gheal**, the lake river, about seventeen miles.
  **in:** legendarium/appendices/I_land.md:53

- **before:** **Abhainn ghorm**, the north-eastern, about twenty-seven miles.
  **after:** **Abhainn ghorm**, the north-eastern, about nineteen miles.
  **in:** legendarium/appendices/I_land.md:55

- **before:** fall south to the south coast in twenty miles or less
  **after:** fall south to the south coast in fourteen miles or less
  **in:** legendarium/appendices/I_land.md:57

- **before:** about seventy-four square miles of fresh water
  **after:** about thirty-six square miles of fresh water
  **in:** legendarium/appendices/I_land.md:63

- **before:** | {{place:feature:8}} | off the west coast | 17 |
  **after:** | {{place:feature:8}} | off the west coast | 8 |
  **in:** legendarium/appendices/I_land.md:73

- **before:** | {{place:feature:13}} | off the south coast | 16 |
  **after:** | {{place:feature:13}} | off the south coast | 8 |
  **in:** legendarium/appendices/I_land.md:74

- **before:** | {{place:feature:15}} | off the south-east coast | 10 |
  **after:** | {{place:feature:15}} | off the south-east coast | 5 |
  **in:** legendarium/appendices/I_land.md:75

- **before:** | {{place:feature:4}} | off the north coast | 7 |
  **after:** | {{place:feature:4}} | off the north coast | 4 |
  **in:** legendarium/appendices/I_land.md:76

- **before:** | {{place:feature:12}} | off the south-east coast | 7 |
  **after:** | {{place:feature:12}} | off the south-east coast | 3 |
  **in:** legendarium/appendices/I_land.md:77

- **before:** | {{place:feature:14}} | off the south coast | 5 |
  **after:** | {{place:feature:14}} | off the south coast | 3 |
  **in:** legendarium/appendices/I_land.md:78

- **before:** | {{place:feature:6}} | off the north coast | 5 |
  **after:** | {{place:feature:6}} | off the north coast | 3 |
  **in:** legendarium/appendices/I_land.md:79

- **before:** | {{place:feature:5}} | off the north-east coast | 4 |
  **after:** | {{place:feature:5}} | off the north-east coast | 2 |
  **in:** legendarium/appendices/I_land.md:80

- **before:** | {{place:feature:3}} | off the north coast | 3 |
  **after:** | {{place:feature:3}} | off the north coast | 1 |
  **in:** legendarium/appendices/I_land.md:81

- **before:** | {{place:feature:10}} | off the east coast | 2 |
  **after:** | {{place:feature:10}} | off the east coast | 1 |
  **in:** legendarium/appendices/I_land.md:82

- **before:** | {{place:feature:7}} | off the Tuathaich coast | 2 |
  **after:** | {{place:feature:7}} | off the Tuathaich coast | 1 |
  **in:** legendarium/appendices/I_land.md:83

- **before:** | {{place:feature:11}} | off the west coast | 2 |
  **after:** | {{place:feature:11}} | off the west coast | 1 |
  **in:** legendarium/appendices/I_land.md:84

- **before:** some 190 square miles, in two pieces
  **after:** some 93 square miles, in two pieces
  **in:** legendarium/appendices/H_shires.md:61

- **before:** some 10,900 square miles, of which the shires hold some 10,720
  **after:** some 5,340 square miles, of which the shires hold some 5,250
  **in:** legendarium/appendices/H_shires.md:71

- **before:** (about 9,220 square miles)
  **after:** (about 4,520 square miles)
  **in:** legendarium/appendices/H_shires.md:75

- **before:** (about 1,680 square miles)
  **after:** (about 825 square miles)
  **in:** legendarium/appendices/H_shires.md:76

- **before:** two hundred and twenty-one miles, some forty-five of them sea at the western end
  **after:** a hundred and fifty-five miles, some thirty of them sea at the western end
  **in:** legendarium/annals/age_V.json:251, legendarium/reconcile/markers_routes.json:497

- **before:** some eighty miles in a little over three days
  **after:** some fifty-five miles in a little over two days
  **in:** legendarium/annals/age_V.json:3153, legendarium/reconcile/markers_routes.json:621

- **before:** Two days by carriage across country
  **after:** A day and a half by carriage across country
  **in:** legendarium/annals/age_V.json:3179, legendarium/reconcile/markers_routes.json:653

- **before:** Two days more by carriage
  **after:** A day and a half more by carriage
  **in:** legendarium/annals/age_V.json:3192, legendarium/reconcile/markers_routes.json:669

- **before:** Two more days by carriage
  **after:** A day and a half more by carriage
  **in:** legendarium/annals/age_V.json:3192, legendarium/reconcile/markers_routes.json:669

- **before:** A day and a half by carriage across country, off every road, bring the
  **after:** A day and a half by carriage across country, off every road, brings the
  **in:** legendarium/annals/age_V.json:3179, legendarium/reconcile/markers_routes.json:653

- **before:** A day and a half more by carriage, still off the roads, bring the
  **after:** A day and a half more by carriage, still off the roads, brings the
  **in:** legendarium/annals/age_V.json:3192, legendarium/reconcile/markers_routes.json:669

- **before:** eight days after it left Cuan dhearg
  **after:** six days after it left Cuan dhearg
  **in:** legendarium/annals/age_V.json:3192

- **before:** Inis thais eight days after they had set out
  **after:** Inis thais six days after they had set out
  **in:** legendarium/book/age_V.md:445, legendarium/reconcile/markers_routes.json:914

- **before:** Inis thais nine days after they had set out
  **after:** Inis thais six days after they had set out
  **in:** legendarium/book/age_V.md:445, legendarium/reconcile/markers_routes.json:914

- **before:** eight days out of Cuan dhearg
  **after:** six days out of Cuan dhearg
  **in:** eras/specs_draft/age_V.json:13208, eras/specs_draft/tools/age_V.py:375

- **before:** by cart, a week on the road
  **after:** by cart, five days on the road
  **in:** legendarium/book/age_VI.md:162, legendarium/annals/age_VI.json:1363

- **before:** Word of the ships reaches Baile fhiadhaich, up the western coast, in three days.
  **after:** Word of the ships reaches Baile fhiadhaich, up the western coast, in two days.
  **in:** legendarium/annals/age_V.json:43

### Where the island is

- **before:** That winter Manannan's mist lifted, which had lain on the western sea since the fleet of the Sundering sailed into it and had hidden the island from every ship beyond.
  **after:** That winter Manannan's mist lifted from the northern water, which had lain on the eastern sea since the fleet of the Sundering sailed into it and had hidden the island from every ship beyond. The humans' land lies east of Dia-thìr, over that sea, and nearer than any Dia-thìreach had guessed; but on the straight way between, the mist has never cleared. The one road through it that the humans ever found ran north-about, out past the north cape and down again on the north-west of the island, and so it was off the north-west that the strangers first raised the land, and every harbour of the Crossing was a harbour of the west coast.
  **in:** legendarium/book/age_V.md:15

- **before:** One sea surrounds all of it, and the Dia-thìrich call it by one name on every coast, north and south: *Muir Mhanannain*, Manannan's sea, for the lord of the sea whose mist lay on it and hid the island from every ship beyond until the humans came out of the west ({{date:IV-0001a}}, {{date:IV-0002}}).
  **after:** One sea surrounds all of it, and the Dia-thìrich call it by one name on every coast, north and south: *Muir Mhanannain*, Manannan's sea, for the lord of the sea whose mist lay on it and hid the island from every ship beyond until the humans came down out of it from the north ({{date:IV-0001a}}, {{date:IV-0002}}). Dia-thìr lies alone in it. The humans' charts put the nearest shore of their own land some sixty miles east of the eastern cape, among a chain of low islands, and a greater coast a hundred miles to the south-east; no one on the island has seen either, even from the summits on the clearest day, for the mist lies on that sea.
  **in:** legendarium/appendices/I_land.md:7

- **before:** Beyond the headlands to the west lay Manannan's own mist. The Dia-thìrich tell that the fleet of the Sundering sailed into it ({{date:III-0023}}), and the order of Manannan teaches that he shut the western sea behind the fleet with it
  **after:** Beyond the northern and eastern headlands lies Manannan's own mist. To the west the open ocean runs on past sight of land, and the tellings put the Otherworld there; the mist lies to the north and east, on the sea between the island and the humans' land, and the straight way east has never been found through it. The one passage the humans knew ran north-about, out past the north cape and down on the north-west, and that is why every harbour of the Crossing was on the west coast. The Dia-thìrich tell that the fleet of the Sundering sailed into the mist by the same road ({{date:III-0023}}), and the order of Manannan teaches that he shut the eastern sea behind the fleet with it
  **in:** legendarium/appendices/I_land.md:98

- **before:** Since the Severance no ship has come from the west, and the priests say the lord of the sea has shut it again
  **after:** Since the Severance no ship has come out of it, and the priests say the lord of the sea has shut it again
  **in:** legendarium/appendices/I_land.md:98

- **before:** For so northerly a place Dia-thìr is a mild island, wet and windy, with cool summers and winters that are seldom hard.
  **after:** For so northerly a place Dia-thìr is a mild island, wet and windy, with cool summers and winters that are seldom hard. It stands alone in the open ocean, and no land breaks the gales before they reach it.
  **in:** legendarium/appendices/I_land.md:90

### The humans' homeland in the east

- **before:** men from over the western sea ruled the island
  **after:** men from over the eastern sea ruled the island
  **in:** legendarium/book/age_V.md:11

- **before:** coming on slowly out of the west with the mist tearing off their bows
  **after:** coming on slowly down from the north with the mist tearing off their bows
  **in:** legendarium/book/age_V.md:19

- **before:** three hulls out of the west riding at anchor off the town
  **after:** three hulls down from the north riding at anchor off the town
  **in:** legendarium/book/age_V.md:25

- **before:** Harrow sailed west with hides and cloth
  **after:** Harrow sailed for home with hides and cloth
  **in:** legendarium/book/age_V.md:59

- **before:** Harrow sails west with hides and dyed cloth
  **after:** Harrow sails for home with hides and dyed cloth
  **in:** legendarium/annals/age_V.json:153

- **before:** Edmund Harrow's ship did not come home from the western crossing
  **after:** Edmund Harrow's ship did not come home from the crossing
  **in:** legendarium/book/age_V.md:103

- **before:** Edmund Harrow's ship does not come back from the western crossing
  **after:** Edmund Harrow's ship does not come back from the crossing
  **in:** legendarium/annals/age_V.json:547

- **before:** sent their son Calum west on a Company ship
  **after:** sent their son Calum over the sea on a Company ship
  **in:** legendarium/book/age_V.md:143

- **before:** The boy, Calum, sailed west on a Company ship
  **after:** The boy, Calum, sailed over the sea on a Company ship
  **in:** legendarium/annals/age_V.json:1061

- **before:** Sailed west on a Company ship
  **after:** Sailed over the sea on a Company ship
  **in:** legendarium/appendices/houses.json:25

- **before:** the human dockers were shipped west
  **after:** the human dockers were shipped over the sea
  **in:** legendarium/book/age_V.md:299

- **before:** the human dockers are shipped west
  **after:** the human dockers are shipped over the sea
  **in:** legendarium/annals/age_V.json:2400

- **before:** When it ends they are not shipped west
  **after:** When it ends they are not shipped over the sea
  **in:** legendarium/annals/age_V.json:2408

- **before:** Their crew-leaders are among those shipped west
  **after:** Their crew-leaders are among those shipped over the sea
  **in:** legendarium/annals/age_V.json:2780

- **before:** Eight were shipped west to an Tìr Thall
  **after:** Eight were shipped over the sea to an Tìr Thall
  **in:** legendarium/book/age_V.md:405

- **before:** eight are shipped west to an Tìr Thall
  **after:** eight are shipped over the sea to an Tìr Thall
  **in:** legendarium/annals/age_V.json:2829

- **before:** the eight who were shipped west
  **after:** the eight who were shipped over the sea
  **in:** legendarium/book/age_V.md:493

- **before:** when the ships went west, and did not go
  **after:** when the ships went out, and did not go
  **in:** legendarium/book/age_V.md:333, legendarium/appendices/A_rulers.md:35

- **before:** With the roads cut and no ships from the west
  **after:** With the roads cut and no ships from over the sea
  **in:** legendarium/book/age_V.md:465

- **before:** The roads cut and no ships coming from the west
  **after:** The roads cut and no ships coming from over the sea
  **in:** legendarium/annals/age_V.json:3381

- **before:** The keeper watched her stand out to the west, smaller and greyer
  **after:** The keeper watched her stand out to the north, smaller and greyer
  **in:** legendarium/book/age_V.md:475

- **before:** whatever road had brought the humans over the western water
  **after:** whatever road had brought the humans over the eastern water
  **in:** legendarium/book/age_VI.md:14

- **before:** a ship was sent out past the western capes to seek the crossing the humans had used. She came home after a month of open water.
  **after:** a ship was sent out past the north-western capes and north-about to seek the crossing the humans had used. She came home after a month of grey water.
  **in:** legendarium/book/age_VI.md:44

- **before:** "title": "The ship sent west"
  **after:** "title": "The ship sent north"
  **in:** legendarium/annals/age_VI.json:87

- **before:** The council sends a ship out past the western capes to seek the crossing the humans used. She returns after a month of open water
  **after:** The council sends a ship out past the north-western capes and north-about to seek the crossing the humans used. She returns after a month of grey water
  **in:** legendarium/annals/age_VI.json:88

- **before:** has shut the western sea again
  **after:** has shut the eastern sea again
  **in:** legendarium/annals/age_VI.json:88, eras/specs_draft/age_VI.json:9583, eras/specs_draft/age_VII.json:10339, eras/specs_draft/tools/age_VI.py:24

- **before:** under the seal of a magistrate who had sailed west
  **after:** under the seal of a magistrate who had sailed home
  **in:** legendarium/book/age_VI.md:83

- **before:** went out past the western capes
  **after:** went out past the north-western capes
  **in:** legendarium/book/age_VII.md:138, eras/specs_draft/age_VII.json:21, eras/specs_draft/tools/age_VII.py:23

- **before:** goes out past the western capes
  **after:** goes out past the north-western capes
  **in:** legendarium/annals/age_VII.json:1665

- **before:** gone out past the western capes
  **after:** gone out past the north-western capes
  **in:** legendarium/book/age_VII.md:142

- **before:** beyond the western capes
  **after:** beyond the north-western capes
  **in:** eras/specs_draft/age_VII.json:9909, eras/specs_draft/tools/age_VII.py:71

- **before:** They say the fleet stood out west into Manannan's sea, toward the Otherworld of the tellings
  **after:** They say the fleet stood out past the north cape into Manannan's sea, toward the Otherworld of the tellings
  **in:** legendarium/book/age_IV.md:74

- **before:** had shut the western sea behind the fleet with his mist
  **after:** had shut the eastern sea behind the fleet with his mist
  **in:** legendarium/book/age_IV.md:202

- **before:** shut the western sea behind the fleet with his mist
  **after:** shut the eastern sea behind the fleet with his mist
  **in:** legendarium/book/age_IV.md:202, legendarium/annals/age_IV.json:1510

- **before:** Manannan shut the western sea behind the fleet of the Sundering
  **after:** Manannan shut the eastern sea behind the fleet of the Sundering
  **in:** legendarium/appendices/B_faiths.md:234

- **before:** the mist on the western sea
  **after:** the mist on the eastern sea
  **in:** legendarium/book/age_IV.md:302, legendarium/annals/age_IV.json:3114

- **before:** the mist that had lain on the western sea since the fleet of the Sundering sailed into it lifts. Two fishing boats
  **after:** the mist that had lain on the eastern sea since the fleet of the Sundering sailed into it lifts from the northern water. Two fishing boats
  **in:** legendarium/annals/age_V.json:15

- **before:** meet three ships coming out of the thin grey from the west, and hail them
  **after:** meet three ships coming down out of the thin grey from the north, and hail them
  **in:** legendarium/annals/age_V.json:15

- **before:** meet three ships out of the west and hail them
  **after:** meet three ships coming down from the north and hail them
  **in:** legendarium/reconcile/markers_routes.json:481

- **before:** met the three ships from the west in the first days of the Crossing
  **after:** met the three ships coming down from the north in the first days of the Crossing
  **in:** legendarium/reconcile/markers_routes.json:131, eras/specs_draft/age_VII.json:14214

- **before:** Three ships out of the west anchor off Cuan shean
  **after:** Three ships down from the north anchor off Cuan shean
  **in:** legendarium/annals/age_V.json:27

- **before:** Three ships out of the west anchored off
  **after:** Three ships down from the north anchored off
  **in:** legendarium/appendices/F_tongues_peoples.md:149

- **before:** A fisher of the west coast, putting out before dawn
  **after:** A fisher of the north-west coast, putting out before dawn
  **in:** legendarium/book/age_IV.md:304

- **before:** on still mornings the fishers of the west coast begin to see
  **after:** on still mornings the fishers of the north-west coast begin to see
  **in:** legendarium/annals/age_IV.json:3114

- **before:** west the mist lies thinner each winter
  **after:** north-west the mist lies thinner each winter
  **in:** eras/specs_draft/age_IV.json:21, eras/specs_draft/tools/age_IV.py:51

- **before:** where ships from the west first raise the land
  **after:** where ships coming down from the north first raise the land
  **in:** legendarium/annals/age_V.json:251, legendarium/reconcile/markers_routes.json:497

- **before:** and there the ships bound for an Tìr Thall leave it and the ships from the west come in
  **after:** and there the ships bound for an Tìr Thall leave it for the passage north-about, and the ships coming down from the north come in
  **in:** legendarium/annals/age_V.json:673, legendarium/reconcile/markers_routes.json:509

- **before:** The willing sail west. 
  **after:** The willing sail out past the north cape. 
  **in:** legendarium/annals/age_IV.json:275

- **before:** the fleet of the willing sailed west into Manannan's mist
  **after:** the fleet of the willing sailed north-about into Manannan's mist
  **in:** eras/specs_draft/age_IV.json:21, eras/specs_draft/tools/age_IV.py:42

- **before:** **The Otherworld.** The Old Faith holds that the Otherworld lies west over the sea, behind Manannan's mist.
  **after:** **The Otherworld.** The Old Faith holds that the Otherworld lies west over the open sea, past the sight of any headland.
  **in:** legendarium/appendices/B_faiths.md:140

- **before:** The fleet of the Sundering sailed west into that mist ({{date:III-0023}}), and the saying
  **after:** The fleet of the Sundering went out north-about into Manannan's mist on the eastern sea ({{date:III-0023}}), not west, but the tellers say it went to find the Otherworld all the same, and the saying
  **in:** legendarium/appendices/B_faiths.md:140

- **before:** When no ship came from the west after the Severance
  **after:** When no ship came from an Tìr Thall after the Severance
  **in:** legendarium/appendices/B_faiths.md:234

- **before:** No ship has come from the west since the last one sailed from Ros bheag
  **after:** No ship has come from an Tìr Thall since the last one sailed from Ros bheag
  **in:** legendarium/appendices/G_trade.md:23

- **before:** sent it west to the scholars of an Tìr Thall
  **after:** sent it over the sea to the scholars of an Tìr Thall
  **in:** legendarium/appendices/F_tongues_peoples.md:421

- **before:** sends it west to the scholars of an Tìr Thall
  **after:** sends it over the sea to the scholars of an Tìr Thall
  **in:** legendarium/annals/age_V.json:446

- **before:** Copied by Samuel Wren and sent west; no answer came
  **after:** Copied by Samuel Wren and sent over the sea; no answer came
  **in:** eras/specs_draft/age_V.json:13069, eras/specs_draft/tools/age_V.py:359

- **before:** "title": "Fewer ships from the west"
  **after:** "title": "Fewer ships from over the sea"
  **in:** legendarium/annals/age_V.json:2848

- **before:** "title": "No relief from the west"
  **after:** "title": "No relief from over the sea"
  **in:** legendarium/annals/age_V.json:3267

- **before:** "title": "Timber from the west"
  **after:** "title": "Timber out of the mist"
  **in:** legendarium/annals/age_IV.json:3060

- **before:** "title": "The last ship from the west"
  **after:** "title": "The last ship from the east"
  **in:** legendarium/annals/age_V.json:3404

- **before:** "title": "The ship that sailed west"
  **after:** "title": "The ship that sailed east"
  **in:** legendarium/annals/age_V.json:3452

- **before:** Lionel Strake, the last Commissioner, sails west from Cuan shean with his officers
  **after:** Lionel Strake, the last Commissioner, sails from Cuan shean for an Tìr Thall with his officers
  **in:** legendarium/annals/age_V.json:3453

- **before:** Strake sailed west in the last ship able to make the crossing
  **after:** Strake sailed for an Tìr Thall in the last ship able to make the crossing
  **in:** legendarium/appendices/C_hosts_wars.md:87

- **before:** The last Commissioner sailed west, and where he came to land is not known
  **after:** The last Commissioner sailed for an Tìr Thall, and where he came to land is not known
  **in:** legendarium/appendices/A_rulers.md:230

- **before:** the last Commissioner; sailed west, and of his landing nothing is known
  **after:** the last Commissioner; sailed for an Tìr Thall, and of his landing nothing is known
  **in:** legendarium/appendices/A_rulers.md:173

- **before:** its last Commissioner sailed west from Cuan shean with his officers
  **after:** its last Commissioner sailed from Cuan shean for an Tìr Thall with his officers
  **in:** eras/specs_draft/age_V.json:21

- **before:** Strake left the Residency (AE 150) and sailed west from Cuan shean
  **after:** Strake left the Residency (AE 150) and sailed from Cuan shean for an Tìr Thall
  **in:** eras/specs_draft/age_V.json:7689, eras/specs_draft/tools/age_V.py:150

- **before:** sailed west; nothing on Dia-thìr tells of his coming anywhere
  **after:** sailed for an Tìr Thall; nothing on Dia-thìr tells of his coming anywhere
  **in:** eras/specs_draft/age_V.json:7694, eras/specs_draft/tools/age_V.py:152

- **before:** He sailed west from Cuan shean and was not heard of again.
  **after:** He sailed from Cuan shean for an Tìr Thall and was not heard of again.
  **in:** eras/specs_draft/age_V.json:14109, eras/specs_draft/tools/age_V.py:482

- **before:** the last ship from the west anchored here
  **after:** the last ship from the east anchored here
  **in:** eras/specs_draft/age_V.json:992, eras/specs_draft/tools/age_V.py:200

- **before:** The mist that lay on the western sea since the Sundering lifted in the winter of the Crossing.
  **after:** The mist that lay on the eastern sea since the Sundering lifted from the northern water in the winter of the Crossing.
  **in:** eras/specs_draft/age_V.json:13744, eras/specs_draft/tools/age_V.py:425

- **before:** sea='the western sea'
  **after:** sea='the eastern sea'
  **in:** eras/specs_draft/tools/age_V.py:425

- **before:** "sea": "the western sea"
  **after:** "sea": "the eastern sea"
  **in:** eras/specs_draft/age_V.json:13742

- **before:** the western sea is open water at the snapshot, but no ship will come again
  **after:** the northern water is open at the snapshot, but no ship will come again
  **in:** eras/specs_draft/age_V.json:42, eras/specs_draft/tools/age_V.py:41

- **before:** Manannan's mist lies on the western sea beyond the headlands
  **after:** Manannan's mist lies on the eastern sea beyond the northern and eastern headlands
  **in:** eras/specs_draft/age_IV.json:39, eras/specs_draft/tools/age_IV.py:56

- **before:** Manannan's mist on the western sea
  **after:** Manannan's mist on the eastern sea
  **in:** legendarium/appendices/B_faiths.md:140, eras/specs_draft/age_IV.json:13293, eras/specs_draft/tools/age_IV.py:348

- **before:** the departed: west, beyond the mist
  **after:** the departed: north-about, beyond the mist
  **in:** eras/specs_draft/age_IV.json:13618, eras/specs_draft/tools/age_IV.py:366

### Also changed by hand

- legendarium/annals/age_V.json: the eves of IV-0342a and IV-0342c (3 -> 2, 2 -> 1), so the Leaden Hawk reaches Inis thais six days after leaving Cuan dhearg.
- eras/NAMES.json (via the names tool): the last ship from the east; the ship that sailed east, *An Long a Sheòl an Ear*; Manannan's mist over the eastern sea.
- eras/WRITERS_GUIDE.md: the rule on geography, distance and compass (section 13), and the example book title.
- legendarium/build_book.py: the gazetteer's opening lines give the size and place of the island.
- check_rodais.py: the frame and the scale are checked; legendarium/README.md and map_reconcile.py describe the place layer.

## Reviewed and kept

- the bearers are eleven days on the road with the body of Fionnlagh Dall (III-0036): a funeral procession of about 20 miles (was 28), stopping at every hearth; the pace was never set by the distance.
- 'a day's walk' (Muileann ghlas from Cathair dhearg, 15 mi; Baile àrsaidh up the coast), 'within a day' of a waypoint house, 'a day's rowing apart', 'a day's sail east', 'half a day's journey', 'a half-day's walk': still true at the smaller scale (a day's walk now covers every one of these with room to spare).
- 'a few miles apart' (Cathair dhomhain and the capital, now 5 mi), 'a few miles from' (Inis thais and Baile dhìreach, 5 mi; the paper-mill and the library): still a few miles.
- 'a little over a mile long' (the shell road at Seann Warr), 'for a mile' (the fires on the east bank), 'passes Caol gharbh by a mile': works and sights smaller than a map cell, not measured from the map.
- the west coast, the western harbours, the western Seann Skell, Cidhe an Iar, the western crossing of the Abhainn dhomhain, the western reefs, the gales off the north-western sea, the rain off the western ocean, 'the drowned, gone west over the sea', the Old Ones sailing 'westward, toward the setting sun', Naomh Breandan sailing west from an Tìr Thall to the Isle of the Blessed: the island's own geography, the Atlantic weather, and the Otherworld in the west: all agree with the new map.
- reconcile/*.json 'why' and 'summary' texts that give the 0.2 scale, the North Channel frame, the journey's 80 + 33 + 43 miles and Fenn's 221 miles; INTEGRATION.md; CONTINUITY_LOG.md; gazetteer/CONSISTENCY_LOG.md: the record of earlier decisions; reconcile/place.json sets the scale and frame aside and says why.
