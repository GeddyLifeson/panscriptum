# Age V volume plan: An Aois Choigreach (AE 1 – 151)

Architect's plan for the era legendarium of the Age of Strangers. Instructions to writers, not prose. Read with
`PLAN_people.json` (cast; years are AE era years, a negative number = that many years before AE 1, null = not told)
and `PLAN_names.json` (new proper nouns, all tested with `normalize()` and `check_agreement()`).

## 1. The volume

- **Title:** *Dath a' Ghuail*, the Colour of the Coal: the Book of the Age of Strangers.
- **Epigraph** (for `front.json`): *Carson a chì sinne an dath, is iadsan dall air?* / Why do we see the colour, and
  they blind to it? (Aonghas mac Coinnich's question, Dùn thais, IV-0114.)
- **Premise.** In the winter of AE 1 Manannan's mist lifts on the northern water and three ships come down from the
  north. The Council of Custodians, which has sat in the empty crown's place since the Sundering age closed, gives the
  strangers leave to stay. In a hundred and fifty years the leave turns into a treaty in one tongue, the treaty into a
  Company, the Company's contracts into pits worked by the ton, and the pits into camps, plagues, hungers and a levy.
  The Dia-thìrich petition, strike, sing, copy and at last rise, and in the War of the Hills (AE 149–150) they drive
  the Administration into the north-west; the last Commissioner sails, the crossing closes, and the humans left on
  the island are marched north. In the dust of the deep galleries the Keeper's old promise wakes in four children
  whom the years do not touch.
- **The question the volume answers:** how did a people who gave strangers water on a beach come to lose the hill
  under their feet, and what did they keep, and at what cost, when they took it back? Its running image: the
  strangers never see the colour in the coal; the island never stops seeing it.

## 2. Point of view and voice

- The high recollection voice of master Book V, with scenes, speech and named people followed over years. Each
  chapter is centred on one person (POV named below) in close past tense; each Book opens with a short recollection
  passage and may close with one.
- **Frame:** the copyists of the three households in the cellar at Muileann chaol set the age down from its four
  witnesses (custodians' rolls, the Residency's letter-books, the beacon-keepers' daybooks, the camps' songs) in the
  winter the rolls came down to them (IV-0376). The frame speaks as at the close of AE 150–151 and never after.
- **Humans** speak in plain English-like speech (their tongue); Dia-thìrich in the same English with Dia-thìris names
  and occasional lines of Dia-thìris. The humans cannot see the colour in the coal; every Dia-thìreach can.
- **Principal lineages (the relay across 150 years):**
  1. **The Maoir of Muileann chrom:** Raghnall mac Dhòmhnaill → Dòmhnall → Iain Maor → Mòrag nic Iain (ch 7–36).
  2. **The Hales of Baile dhìreach:** Eilidh nic Ruairidh and Samuel Hale → Iain Hale → Thomas Hale → Eilidh Hale
     (ch 4–5, 15, 28, 40). The two peoples in one house.
  3. **The custodians' women:** Gormshuil nic Fhearchair → Peigi Ghlas → Eilidh nic Raghnaill (ch 2–40).
  4. **The silver guild:** Ùna nic Choinnich → Catrìona nic Eachainn (ch 14–26).
  5. **The keepers of the lights:** Anna nic Dhòmhnaill, Tormod mac Pheadair, Uisdean mac Lachlainn → Lachlann mac
     Uisdein, Raonaid nic Dhòmhnaill (ch 8–40). The daybooks as a structural device ("a keeper has nothing to gain
     from a ship that is not there").
  6. **The witnesses from over the sea:** Samuel Wren → Anne Colby → Matthew Dunne (ch 2–29).
  7. **The copyists:** Muireall nic Fhearchair → Cailean mac Eachainn (ch 2, 30–31, 40; the frame).

### Hard rules for every writer
- **Owner's characters** (Aisling, Fionnan, Lorccan, Cian, Donnchadh mac Thormoid, and Aisling's grandfather Tormod
  and great-grandfather Ruairidh of Doire mhòr): chronicle facts only. No new words, deeds, thoughts, relatives or
  feelings. Aisling is seen only from outside (born; does not age; the camps' names *nighean an rìgh* and
  *Aisling-aois*; her line found). The gallery scene (ch 19) is retold as the camp women tell it, following master
  Book V §VII, adding no words to Donnchadh or the Keeper. Aisling's mother stays unnamed and off the page.
  Ruairidh mac Thormoid of Àth fhionn is **not** of Aisling's line; never link them.
- **Nothing after the age.** Never write: Tuathaich, the Kingdom, Rìoghachd, the Library/Leabharlann (say "the loft of
  Beathag nic Thòmais" and "the cellar at Muileann chaol"), the Moot, Niall, SE/DE dates, "immortal". The thing in
  the children has **no name until ch 30** (IV-0250); before that, "the change", "what the years did not do".
  The book ends on 1 am Faoilleach AE 151. No era events after IV-0377.
- Names: NAMES.json and PLAN_names.json only; human personal names as written. Travel times per WRITERS_GUIDE §13
  (Cuan shean–Cathair dhearg 26 mi; Ros dhomhain–Muileann chrom 35 mi; Muileann chrom–Muileann chiar 23 mi;
  Muileann chrom–Muileann chaol 28 mi; Cathair dhearg–Ros bheag 29 mi). Towns are small (a few hundred people;
  Seann Skell of the west 2,000; Baile dhìreach 55); island about a million; deaths in tens.
- Distinguish same-named towns by id: Baile chrom 305 (north-west beacon) vs 187 (hills); Seann Skell 489 (west) vs
  132 (hawk-shrine) ; Muileann chaol 246 (the cellar) vs 196 (north); Seann Chwen 36 / 14; Seann Warr 64 (salt) /
  128 (farms); Achadh àrsaidh 242 (north-west fishers); Baile Mòr ruadh 303 (north-west) / 387 (drought-fever).
- Tells: TELLS_FOR_WRITERS.md. Run `quality/tells_scan.py V` and `quality/future_check.py V`.

## 3. Structure: 6 Parts, 12 Books, 40 chapters (~186k words)

**Files (one writer per chapter):** each chapter is its own Book file `book/NN_slug.md` (NN = the two-digit chapter
number below; slug from the title, e.g. `book/01_of_the_gauze_on_the_water.md`), opening `# <chapter title>`, the
date line, an optional epigraph, then `## I.`, `## II.`… scene sections. Chapters 1, 8, 14, 21, 28 and 34 open a Part and
carry the Part title and epigraph given below. The "Book NN (Wnn)" groupings below are the old two-writer blocks and
now serve only as id ranges for compiling the annals (§6). Events go in `events/NN.json` per CHAPTER_BRIEF.md.

---

### PART ONE — Of the Opening of the Sea (AE 1–11)

**Book 01 (W01): Of the Gauze on the Water, the Forty Words and the Post at Ros dhomhain** — *AE 1 – 5*.
Epigraph: *A Mhanannain, cùm a' mhuir dùinte.* / Manannan, keep the sea shut.

**Ch 1. Of the Gauze on the Water** — POV Lachlann Odhar, then Oighrig nic Leòid. AE 1 Jan – AE 2 Feb (~5,000 w).
Masters: IV-0001, 0001a, 0002, 0003, 0004, 0005, 0006.
Open with the frame (the cellar, the four witnesses, the winter the rolls came) and the last state of the old age:
priests at Seann Skell praying at every tide, the mist thin. Lachlann's two boats of Achadh àrsaidh (burg 242) off the
north-west cape; the grey wall goes to gauze; three sails come down from the north; hails fail; he steers south a
long day to Cuan shean and the ships follow. Oighrig, custodian of Cuan shean, meets Harrow wading with an empty
cask; gives water and no more; sends a rider to Cathair dhearg; forty days of strangers fed below the dunes
(show them mending nets, trading buttons for fish). Baile fhiadhaich's custodian rides south: better ropes, worse
manners. The council sits the winter; Oighrig, ill, is one of the three absent when Tormod mac Ailein's council
gives leave (11 am Faoilleach AE 2); the roll says unanimous, a margin says three were absent. Turn: old sailors say
the ships came from the quarter the Sundering fleet sailed into; the council forbids the remark. Ends with Lachlann
saying it anyway at the harbour wall, and nobody answering.
New era events: EV-1001 the word brought home to Achadh àrsaidh (AE 1); EV-1002 Harrow's men mend nets on the dunes
(AE 1); EV-1003 the rider from Cuan shean reaches Cathair dhearg (AE 1); EV-1004 Oighrig nic Leòid's letter to the
council from her sickbed (AE 1); EV-1005 Manannan's priests at Seann Skell keep the tide-prayer through the forty days (AE 1).

**Ch 2. Of Forty Words for the Colours of Coal** — POV Gormshuil nic Fhearchair. AE 2 Feb – AE 3 May (~5,000 w).
Masters: IV-0007, 0008, 0009, 0010, 0011.
The land beyond named *an Tìr Thall*; the humans' Church, Crìosd, an Eaglais. The season of words at Cathair dhearg:
Gormshuil across a table from Samuel Wren (thin, courteous, coughing in the damp), pointing at cup and bread; her
niece Muireall copying. The basket of broken coal in the window-light; the forty colours; Wren's one word, the word for
his hearth-fuel; the candle held up. Gormshuil's stillness; she waits for him to ask for her word, and he does not.
Muireall writes the note under the first leaf (one word for the coal of the vein; no Dia-thìris word answers it; they
did not ask). Turn: Gormshuil decides to learn his letters, since he will not learn her colours. Ends with the first
fair trade beginning (IV-0011) and the leaf going into a chest bound for the loft at Muileann chaol.
New: EV-1006 the humans' first prayers said in a sail-loft at Cuan shean (AE 2); EV-1007 the council gives Gormshuil
the keeping of the word-list (AE 2); EV-1008 Muireall copies the first leaf (AE 3); EV-1009 the copy sent to the loft
of Beathag nic Thòmais at Muileann chaol (AE 3); EV-1010 Gormshuil begins the humans' letters with Wren (AE 3).

**Ch 3. Of the Post at Ros dhomhain** — POV alternating Thomas Pike and Gilleasbuig Gobha. AE 3 Jun – AE 5 Apr (~5,000 w).
Masters: IV-0012, 0012a, 0013, 0014, 0015, 0016, 0017, 0018, 0019, 0020.
The years of fair exchange told fairly. The post's counter; Pike's tally-book balancing to the line. Caol leathan pilots
tow the first hull up the Abhainn gheal into Loch chrom. Wool from Cathair naomh; dyes for Baile Mòr mhòr. Gilleasbuig
learns to temper bar-iron in one winter; bronze hoes melted for bells. Harrow sails and returns with four ships,
carpenters, the surgeon Tull, and a letter from a trading house asking what else the island has: Pike reads it aloud
at the counter and the smith hears the question. Inis mhòr's shipwrights measure the hulls with knotted cords. Tull
sets the Cuan shean fisherman's leg; the first debt to a stranger. Salt of Seann Warr; Caol leathan's wool paid only in
iron by weight. Turn and end: Pike, asked by the letter, writes home that the island has "coal of a middling sort, much
of it," and Gilleasbuig, reading nothing, forges him a hinge.
New: EV-1011 Gilleasbuig's first tempered blade (AE 3); EV-1012 the bells of Cathair dhearg cast from the hoes (AE 4);
EV-1013 the trading house's letter read at the post (AE 4); EV-1014 Pike's first two years balanced (AE 5, before IV-0020).

**Book 02 (W02): Of the Council of Six, the Five Headlands and the Treaty in One Tongue** — *AE 5 – 11*.

**Ch 4. Of the Council of Six** — POV Eilidh nic Ruairidh. AE 5 Apr – AE 6 Jan (~3,900 w).
Masters: IV-0021, 0022, 0023, 0024.
Baile dhìreach, a port of some fifty souls on the south-west coast. Human boatbuilders and a cooper come ashore; the
council of six, three and three; the compact written twice; the chair alternating between Iain mac Chaluim and William
Rook; dues halved. Samuel Hale mends her father's barrels; she learns his words for rope and knot. Inis thais is bidden
and declines. Turn: Eilidh's father refuses Samuel, then relents when Rook takes the chair and nothing falls down. Ends
with the first winter of the joint council.
New: EV-1501 the compact written in both tongues (AE 5); EV-1502 the first human house on the shingle (AE 5);
EV-1503 Iain mac Chaluim hands the chair to William Rook (AE 6).

**Ch 5. Of the Five Headlands** — POV Torcall Clachair, with James Fenn. AE 6 Jan – AE 7 May (~3,900 w).
Masters: IV-0025, 0026, 0027, 0027a, 0028.
The supply ship on the western reefs in fog, nine drowned; a chart drawn from memory. The humans ask for beacons; the
builders agree, not seeing what it will bring. Torcall and Fenn walk the coast a season: the five headlands of the old
driftwood fires (Tobar dhearg, Baile ìseal, Muileann bheag, Àth dhearg, Baile chrom); Fenn's line of sights across the
island from the open sea off the north-west; Fenn writes his own names on the chart, Torcall says each headland has one.
Turn: the walk ends at Baile dhìreach for the wedding of Eilidh and Samuel, entered in both books; the custodians at
Cathair dhearg, asked for a ruling, send none. Ends with Torcall's cairns and the double entry set side by side.
New: EV-1504 the nine drowned buried on the western shore (AE 6); EV-1505 Torcall's first cairn on the Tobar dhearg
headland (AE 6); EV-1506 the council asked for a ruling on the marriage (AE 7).

**Ch 6. Of the Treaty in One Tongue** — POV Tormod mac Ailein. AE 7 – AE 9 Oct (~3,900 w).
Masters: IV-0029, 0030, 0031, 0032, 0033.
Tormod's reasons: iron, the surgeon, the ships that could come again. Josiah Pell lands. The reading in the council
hall, rain off the lake, the ford-look before signing; Pell signs for the Administration. The clerk enters the Diosal
year and the moon and leaves the day blank. The Residency built on the rise above Ros dhomhain by masons of the capital;
Harrow and Pike found the Company, whose charter claims "all fuels, ores and minerals the island may yield"; its first
building a stone warehouse at Cathair dhomhain (plant it; it is opened in ch 37). Turn: Gormshuil reads the charter to
Tormod in private and he understands the phrase too late. Ends with the warehouse door being hung.
New: EV-1507 Pell lands at Cuan shean (AE 8); EV-1508 the clerk leaves the day blank (AE 8); EV-1509 Gormshuil reads
the charter to Tormod (AE 9).

**Ch 7. Of the Fever and the Sacks of Coal** — POV Raghnall mac Dhòmhnaill (young). AE 9 Nov – AE 11 Oct (~3,900 w).
Masters: IV-0034, 0035, 0036, 0037, 0038, 0039, 0040.
The strangers' fever at Cuan shean (91 and 11 dead); the town shut to ships; Pell's protest. Baile àrsaidh's custodian
and her sons die; Cnoc àrsaidh blocks its road with carts and is spared. Raghnall, a hewer's son of Muileann chrom,
guides Abel Stone and Hugh Mercer into the hills for a coin; the sacks of broken coal; the seam "further than can be
walked in a day". The custodians demand it back; half returned and laid in the rock with the words, half "carried west".
Contracts. Turn: Raghnall is chosen to lead the thirty of the first pit, paid by the ton in iron and lamp-oil, and is
proud when the first ton is weighed. Ends Part One with a recollection coda: the custodians' cuttings had never been
measured by weight.
New: EV-1510 the fever dead of Cuan shean buried beyond the dunes (AE 10); EV-1511 Raghnall guides the prospectors (AE
10); EV-1512 the returned half laid in the rock with the words (AE 11); EV-1513 the first ton weighed at Muileann chrom (AE 11).

### PART TWO — Of the Hill Sold by the Ton (AE 12–41)

**Book 03 (W03): Of the Door at Doire mhòr, the Mark and the Law That Went Out** — *AE 12 – 24*.

**Ch 8. Of the Door at Doire mhòr** — POV Beathag Dhubh. AE 12 Jul – AE 16 Apr (~5,000 w).
Masters: IV-0041–0050.
Ceann fhada's quay; fishermen paid for their foreshore in nails by weight. Wren's grammar ("keepers of the coal"); the
hawk-priests of Cnoc bheag read it. The chapel and the first iron bell; the custodians ask it not be rung before the
fleet is out. The Company's agent climbs to Doire mhòr; Beathag hears him out at her door and does not ask him in;
Ruairidh stands behind her, silent. Her answer survives only in his report. Cnoc fhiadhaich opened instead; the cart-road
curves round her fields. The first beacon, Tobar dhearg, built by Torcall with Fenn's lens; Anna nic Dhòmhnaill climbs
it twice a night. Raiders strip a brig off the north-west. Turn: Beathag sees the road bend and knows it for a
postponement. Ends: "for now."
New: EV-2001 the bell rung once before the fleet was out (AE 13); EV-2002 Beathag calls Doire mhòr's households to the
hearth (AE 14); EV-2003 the cart-road round Doire mhòr finished (AE 15); EV-2004 Anna nic Dhòmhnaill's tally of lit
nights cut on the stair wall (AE 16).

**Ch 9. Of the Mark and Its Hundred Pence** — POV Samuel Wren, then Gormshuil. AE 17 Feb – AE 20 Dec (~5,000 w).
Masters: IV-0051–0061.
Wren copies the obelisk at Cnoc bheag and sends it over the sea; no answer. The mark and its hundred pence struck at Ros
dhomhain (a ship on one face, nothing of Dia-thìr). Cathair mhòr refuses the mark a year; two books at the capital
market. Wren's winter at Dùn thais: "why is the vein holy?" / "why is your fuel burned?"; the druids' western isle and
his Naomh Breandan. The capital's bridge rebuilt for coal-carts; Pell's carriage over it. The Harbour Articles: two
custodians refuse to sign, Gormshuil one of them. Baile ghlas charged anchorage. The concession grazing at Muileann
àrsaidh; the families build in stone. Tormod mac Ailein dies; Coinneach Glas chosen. Turn: Gormshuil's refusal. Ends at
Tormod's burying, Wren coughing at the back.
New: EV-2005 Wren's letter home on the druids (AE 18); EV-2006 Gormshuil nic Fhearchair refuses the Articles (AE 19);
EV-2007 the first stone houses on the concession (AE 20); EV-2008 Tormod mac Ailein buried at Cathair dhearg (AE 20).

**Ch 10. Of the Law That Went Out** — POV Fionnghal nic Artair. AE 21 Jul – AE 24 Mar (~5,000 w).
Masters: IV-0062–0070.
Harrow's ship does not come home; the Company to Pike. The Small-Burning Law lapses: no repeal, only a ceasing to pay.
Doire mhin keeps the count one season longer. Fionnghal writes from Dùn dhearg the only surviving defence ("the Law was
never for the coal's sake but for the people, who would become whatever the burning made them"), rides to Cathair
dhearg to read it; the council files it. Murchadh Seabhag preaches the Hungry Hawk at Seann Skell; the sermon carried
into the camps and seized. Achadh naomh will not light bought coal. Furnaces burn by the cartload. Maddox arrives with
orders to double the yield; the oaks of Cathair fhada fall for props. Turn: the filing. Ends with Fionnghal home,
burning peat.
New: EV-2009 Fionnghal rides to Cathair dhearg (AE 22); EV-2010 the council files her letter unanswered (AE 22);
EV-2011 the Company's agents seize the hawk sermon in the camps (AE 23); EV-2012 the last oak of Cathair fhada (AE 24).

**Book 04 (W04): Of the Eleven, the Green River and Raghnall Maor** — *AE 25 – 41*.

**Ch 11. Of the Eleven of Cnoc fhiadhaich** — POV Raghnall. AE 25 – AE 29 (~5,000 w).
Masters: IV-0071–0077.
The gallery driven fast without the timbering Raghnall's crews begged for; the fall; eleven dead. The custodians' roll
names all eleven, the Company's report none ("unsound ground"). The dry cough: thirty-eight boys at the pit-mouth; his
son Dòmhnall, six, breaks coal and lives. Cill thais keeps the orphans. The Baile ìseal beacon, Torcall directing from a
chair; its keepers drawn from the fishing families by rule. Ceann òg's traders' boats. The timber camp at Àth ìseal.
Turn: the agent offers Raghnall more pay to keep his crews at the face; he takes it. Ends with the first crews in the
huts at Àth ìseal.
New: EV-2501 the eleven buried at Muileann chrom (AE 25); EV-2502 Dòmhnall mac Raghnaill at the pit-mouth (AE 26);
EV-2503 Torcall Clachair's last cairn (AE 28).

**Ch 12. Of the Green River Run Black** — POV Seònaid Bhàn. AE 30 – AE 35 Jul (~5,000 w).
Masters: IV-0078–0090.
Doire mhòr's stream dammed with no written order; its people carry water two summers (Tormod among them: fact only),
then begin to leave. The short hunger; meal-carts from Doire fhiadhaich by the Holy Age custom. The mountain by the
ton; Dùn chrom's rope-walks to winding-rope; the second charter; barges at Cidhe Beag, the shrine carried uphill; the
Abhainn uaine silts black, the salmon fail; Baile Mòr dhomhain a barge town; Baile dhomhain drawn on a grid. Seònaid
reopens An Taigh-seinnse Mòr at Lùnastal, taking marks and barter both; Rathad na Mèinne metalled; the carters of
Doire chaol band together at her table; Seann Toll made a landing. Gormshuil dies; Muireall carries her papers to the
loft. Turn: Seònaid's rule of two payments. Ends with the carters bargaining in her room.
New: EV-2504 Gormshuil nic Fhearchair dies at Cathair dhearg (AE 31); EV-2505 the first households leave Doire mhòr (AE
32); EV-2506 the last salmon netted at the green river's mouth (AE 33); EV-2507 Seònaid's rule of marks and barter (AE 34).

**Ch 13. Of Raghnall Maor** — POV Raghnall, then Dòmhnall. AE 36 – AE 41 Jul (~5,000 w).
Masters: IV-0090a–0099.
The coal ships' lane to Ceann leathan. Raghnall set over Dia-thìreach crews: the staff, the slate roof, the byname given
him by his own people. Overseers multiply; the roll gives their number, not their names. Seumas Dubh killed by his crew
at Cnoc mhòr; two hanged at Ros dhomhain, the first hanging; Raghnall made to watch. Maddox bars the hawk-priests; the
overseers enforce it. The spotted pox; the Mission counts 27, the custodians more in the margin; Baile chiar cuts its dead
into stones. Baile dhìreach loses its dues; its council shrinks to four. Beathag Dhubh dies. Maddox leaves rich; Lisle
has every agreement copied into one bound book. Turn: the hanging. Ends with Lisle opening the book.
New: EV-2508 Raghnall's slate-roofed house (AE 36); EV-2509 the two hanged named in the custodians' roll (AE 38);
EV-2510 Beathag Dhubh dies at Doire mhòr (AE 41).

### PART THREE — Of Silver, Steam and the Green Death (AE 42–76)

**Book 05 (W05): Of the Ledgers at the Adit, the Daybook and the Question** — *AE 42 – 62*.

**Ch 14. Of the Ledgers at the Adit** — POV Ùna nic Choinnich. AE 42 Mar – AE 45 Jan (~3,900 w).
Masters: IV-0100–0105.
Lisle's customs house at Ros gheal; the hawk-faithful there chase its officers out. The Company claims the silver seam;
Ùna at the adit with the whole guild in leather aprons and two ledgers open: "find the humans' name". Lisle reads the
treaties and finds nothing about silver; the Silver Compact on Là Fhèill Brìde AE 44, the first writing of the age in
the Dia-thìreach side's favour. Silver goes to sea by Seann Bhral; Baile gheal's carters take the salt round the lake.
Turn: the surveyor closes his book. Ends with the compact locked in the guild chest. (Alasdair Liath becomes high
custodian on Coinneach Glas's death.)
New: EV-3001 the hawk-faithful of Ros gheal chase out the customs officers (AE 42); EV-3002 Alasdair Liath high
custodian (AE 44); EV-3003 the compact read in the guild hall (AE 44).

**Ch 15. Of the Keeper's Daybook** — POV Tormod mac Pheadair; interlude Iain Hale. AE 45 Jul – AE 48 Oct (~3,900 w).
Masters: IV-0106–0113.
Àth dhearg lit, built by its own townsmen; Tormod begins the first daybook (entries structure the chapter). Raiders in
low black boats burn a Company coal ship; he sees the glow. The gunboat burns the fishermen's boats at the cove near
Ceann leathan. At Baile dhìreach the joint council breaks over a boundary wall; humans go to Ros bheag and Ros
dhomhain; the Hales go quiet and stay (Iain Hale). The boatyard to Inis chrom. The dry year at Achadh shean; Baile ruadh
borrows seed from the Company store. Turn: Iain Hale's choice to stay. Ends on a daybook line.
New: EV-3004 the first line of the Àth dhearg daybook (AE 45); EV-3005 the Hales keep their house at Baile dhìreach
(AE 47); EV-3006 Baile ruadh's seed debt entered (AE 48).

**Ch 16. Of the Question at Dùn thais** — POV Aonghas mac Coinnich; then Eachann Mòr's household. AE 49 Jun – AE 56 Sep (~3,900 w).
Masters: IV-0114–0129.
The question in the Deer register, and "it is the wrong question"; students carry it to Baile Mòr uaine. Cathair gheal
founded on the concession under a charter naming no custodian; farms and a mill at Cnoc ghorm; human fishers at Ceann
mhòr; tobacco. Eachann Mòr sends Calum over the sea; the ship goes north-about; no letter comes. The Mission school
(overseers' children); Inis bhàn's answering school. The Ros fhionn bridge; eastern coal through Inis bheag and Baile
mhin; Caol gharbh passed by. Things the clerks cannot file: the beast in the north-western sea, a brig lost in the mist,
whale-lances at Àth fhionn, the surveyors lost at Doire uaine and the salt left for the sìth. Turn: Calum's ship. Ends
with Aonghas refusing to answer his own question.
New: EV-3007 Aonghas writes the question in the register (AE 49); EV-3008 Calum's ship sails north-about (AE 51);
EV-3009 the search party returns from Doire uaine empty-handed (AE 56).

**Ch 17. Of the Tithe and the Flux** — POV Anne Colby. AE 57 Feb – AE 62 Mar (~3,900 w).
Masters: IV-0130–0137.
Lisle's schedule: one part in five to one in three, received in a Mission pupil's translation; grain weighed at Dùn
fhiadhaich. Colby lands; the bloody flux on the quays; she makes the chapel a sick-house and keeps the dead under
fifteen, learning the crews by the custodians' names. The flux to Seann Vell by barge; the town shuts. Lisle dies; Crane
from chief agent to Commissioner; the pay office at Ceann mhin, a day's walk each way. Raghnall Maor dies; Dòmhnall
takes the staff (the custodians' hope dies). Turn: Colby writes the dead by name. Ends at Raghnall's burying.
New: EV-3010 Anne Colby lands at Ros dhomhain (AE 58); EV-3011 the crews' first walk to Ceann mhin (AE 61);
EV-3012 Raghnall Maor buried (AE 62).

**Book 06 (W06): Of Lowe's Spade, the Smoke in the Gallery and the Green Death** — *AE 63 – 76*.
Epigraph: *Ithidh Mòd an neach a dh'itheas an cnoc.* / Mòd will eat whoever eats the hill.

**Ch 18. Of Lowe's Spade** — POV Edwin Lowe. AE 63 Feb – AE 68 Jan (~5,000 w).
Masters: IV-0138–0145.
Muileann bheag's beacon burns coal; its flame lays a colour on the water the fishermen see and Lowe does not; they say it
drives the herring. Lowe digs Làrach an Teampaill (cut stone, burnt bone, marks), "not the present race"; the custodians
agree and add nothing; copies of the pillar at Cnoc chiar and column at Cnoc ghorm. Voss's glass-house. Martha Gale
offers the silver guild partnership; Ùna, very old, has it read twice and puts it to hands; refused. The camp at Achadh
dhomhain opened for the deep galleries, houses of spoil; Dùn chiar weaves canvas. Turn: Lowe's blindness at the
coloured flame. Ends with the first house of spoil roofed.
New: EV-3501 Muileann bheag's keepers refuse to change the flame (AE 64); EV-3502 Lowe's labourers stop at the burnt
bone (AE 64); EV-3503 Voss's first pane (AE 66).

**Ch 19. Of the Smoke in the Gallery** — POV Beitris Bhàn (layer-out of the dead). AE 68 – AE 72 Oct (~5,000 w).
Masters: IV-0144 (recalled), 0146, 0146a, 0147, 0148, 0149, 0149a, 0150, 0151.
The first winter of the camp; burials. Beitris hears, years after, what the hewer told his wife and the wife the women:
the smoke in the gallery, the breath, the cough the surgeon gave a year, the birth in a house of spoil on 7 am Màrt AE
69, the cough stopping that night (retold in the women's voice from master Book V; no new words). The Company coach;
the steelyard at Ros dhomhain; Ros dhìreach's first cargo lost; the first steamer. The child is seen and noted, nothing
more; no one yet has a word. Shrines: Cill dhìreach's first piece of coal from each gallery; Cill ghlas at the oldest
cutting. Ùna dies at the silver town. Turn: the women decide to keep the telling among themselves. Ends with Beitris
climbing to Cill ghlas at Lùnastal ("remember it").
New: EV-3504 the first winter's dead of Achadh dhomhain (AE 68); EV-3505 Ùna nic Choinnich dies (AE 70);
EV-3506 Beitris's climb to Cill ghlas (AE 72).

**Ch 20. Of the Green Death** — POV Anne Colby and Beitris Bhàn. AE 73 Jun – AE 76 May (~5,000 w).
Masters: IV-0152–0162.
First cases at Achadh dhomhain (pallor like a candle through bottle-glass; dark dust; weakness); forty in a month; the
green acre. Along the coal roads; twenty-six settlements and the blank line; Baile chrom of the hills kept apart from
the north-west town. Àth ghlas burns its huts and stops it soonest. Cnoc naomh's shrine ground fills. Bright weighs
dust in the lungs of the dead; his notebook breaks off mid-table. Crane dies; Martha Gale holds the seal; Tolley
arrives, never visits; quarantine at Caol mhin. Hawk-feathers nailed over doors; the saying. Turn: Colby and Beitris
wash the dead side by side. Ends with Tolley's letter-book blaming the dust, the hearth and the shrines, in that order.
New: EV-3507 the green acre first dug (AE 73); EV-3508 Bright's notebook breaks off (AE 75); EV-3509 Bright dies at
Muileann chrom (AE 76).

### PART FOUR — Of the Levy, the Hunger and the Drought (AE 77–110)

**Book 07 (W07): Of the Eleven Days, the Blessed Coin and the Levy** — *AE 77 – 91*.

**Ch 21. Of the Eleven Days of Baile thais** — POV Catrìona nic Eachainn. AE 77 Apr – AE 79 Nov (~5,000 w).
Masters: IV-0163–0169.
Colby's sick-houses; Cnoc gharbh's people leave their huts. Catrìona asks the agent Silas Crewe to shut the worst
galleries; "the yield must not fall". The coal-tub; eleven days; she counts loaves in the windows; one store, the
Company's. Twelfth morning, the shelves. (Raghnall Breac, a boy, is among the strikers.) The granary order signed by
Dòmhnall Maor; Ros gharbh's fish smuggled by night. Catrìona turned out and refused everywhere; she walks east to
Muileann chiar; the guild takes her. Turn: the empty shelves. Ends with the guild's answer filed and not kept.
New: EV-4001 Catrìona's request to close the galleries (AE 77); EV-4002 Dòmhnall Maor signs the granary order (AE 78);
EV-4003 Catrìona walks east over the hills (AE 79).

**Ch 22. Of the Priced Silver and the Blessed Coin** — POV Fearghas mac Mhuirich; Catrìona. AE 80 Sep – AE 87 Apr (~5,000 w).
Masters: IV-0170–0180.
The bath-house at the springs, a penny on certain days. The silver town grows; the daughter town west; silver for
marks at the guild's price; silversmiths at Muileann bhàn. Tolley asks Òrd Mhacha to bless the coin: Dubh Sainglenn and
Liath Macha, the dark and the light; Fearghas says the coin is only one of them. Second change of coin; the fleece table
at Baile Mòr fhionn; Caol fhiadhaich sells half its boats. The dissenters go to the sacred forest at Cnoc bheag.
Dòmhnall Maor dies; Iain Maor takes the staff. Camp interlude: the washing-women first say the girl who does not grow
is of the old king's blood (*nighean an rìgh*); nobody believes the thousands of years. High custodian Artair mac Iain
seated. Turn: Fearghas's refusal in the temple. Ends with the dissenters' first fire under the trees.
New: EV-4004 Artair mac Iain high custodian (AE 81); EV-4005 Fearghas refuses the blessing (AE 85); EV-4006 the
dissenters' first rite in the forest (AE 87).

**Ch 23. Of the Levy and the Ring of Beacons** — POV Dùghall Clachair. AE 88 – AE 91 Sep (~5,000 w).
Masters: IV-0181–0193.
The Levy: one in five, two years, paid in marks; read at Caol mhòr in the humans' tongue; hardest round Baile chrom and
the concession, whose human farmers are exempt. Baile ìseal's 41 and 19; Muileann naomh's bribe taken with the tally.
Tolley shuts the Deer hall at Dùn thais; the last disputation at Doire chiar; teaching under the trees of Flidais.
Dùghall's Cnoc thais masons, taken by the Levy from unworked fields, build the Baile chrom tower; he cuts his crew's
names in the stair. The ring finished; Cuan ruadh loses its coasting trade; Baile chrom lit with a coal flame, sailings
double. Turn: the names in the stone. Ends with Uisdean mac Lachlainn lighting the lamp.
New: EV-4007 the Levy read at Cnoc thais (AE 88); EV-4008 Uisdean mac Lachlainn named keeper (AE 90); EV-4009 the names
cut in the stair (AE 91).

**Book 08 (W08): Of the Great Hunger, the Petition, the Songs and the Drought** — *AE 94 – 110*.
Epigraph: *Tha an long ag ithe a' chnuic / gus an cnoc a ghiùlan air falbh.*

**Ch 24. Of Gorta Baile chrom** — POV Uisdean mac Lachlainn; Anne Colby. AE 94 Mar – AE 97 Aug (~3,900 w).
Masters: IV-0194–0201.
Thirty-four settlements; the Levy took the hands. From the tower Uisdean sees the empty fields and his own flame moving
on the sea. The famine country's bounds; Doire ghlas sends its young to the camps; Inis mhin eats its seed; Seann Bhrenn
opens the Holy Age grain-pits. The relief ship lies a month at Ros dhomhain while two offices argue. Colby, back on the
island, runs the kitchen at Baile chrom. The Levy set aside, never repealed. Cnoc mhòr walks south, its village empty.
Turn: Uisdean thinks of putting out the light and does not. Ends with the Levy's ending read at Baile chrom, too late.
New: EV-4501 Colby lands again (AE 95); EV-4502 the relief ship's passing in the Baile chrom daybook (AE 96);
EV-4503 the Levy's end read at Baile chrom (AE 97).

**Ch 25. Of the Petition on the Bench** — POV Peigi Ghlas. AE 98 Oct – AE 99 Dec (~3,900 w).
Masters: IV-0202–0206.
Tolley retires; Haskins orders the council consulted, then sets the tithe first. Customs and a store at Seann Dunn. The
nineteen at Ceann àrsaidh, first as one body; the drafting; Ruairidh mac Thormoid of Àth fhionn, born before the coin,
writes so beside his name. Peigi carries it: the bench, the passage of lamp-soot, the young clerk, the pile. She goes
home. Not answered. Turn: the pile. Ends at Cill ghlas, Peigi trimming Brìde's lamp.
New: EV-4504 the custodians ride to Ceann àrsaidh (AE 99); EV-4505 Peigi Ghlas at the Residency (AE 99).

**Ch 26. Of Fearchar Bàrd's Songs** — POV Fearchar Bàrd. AE 101 Jan – AE 105 Sep (~3,900 w).
Masters: IV-0207–0216.
Grievance written: Leabhar Baile thais, many hands (wages, deaths, the granary, the stream). Fearchar's songs of the Levy
and the famine, forbidden and so written down; sung at An Taigh-òsta Grianach; carters sing them unknowing. The deep
quay for iron steamships; the ship song. Ceann chaol's quay. Baile thais walls its pithead. Catrìona dies at Muileann
chiar; the delegation docked a day's pay; Fearchar makes her lament. The quay fire. Artair mac Iain dies and the council
cannot choose; Haskins finds it easier. Turn: the carters singing. Ends with the empty seat.
New: EV-4506 Fearchar's first song forbidden (AE 102); EV-4507 Catrìona's burying at Muileann chiar (AE 104);
EV-4508 Artair mac Iain dies (AE 105, before IV-0216).

**Ch 27. Of the Long Drought** — POV Iseabail nic Leòid. AE 106 Aug – AE 110 Aug (~3,900 w).
Masters: IV-0217–0228.
Three dry seasons. Achadh shean's wells fail; the cattle column a day long, fewer than half reach water. Ten districts;
Baile chaol slaughters its herds; Doire fhionn's women walk half a day for water. Allt an Àigh never fails; pilgrims of
Na Seann Spioradan at Bealltainn; the watchman who charged is recalled; Inis uaine feeds them. Drought-fever at Baile Mòr
ruadh (387) and Cnoc shean; the Mission names the cause and bores wells that hold. Achadh chaol to the pits. The tally
not lowered; each custodian writes alone. Iseabail drives Àth mhòr's beasts west and counts the dead. Turn: she begins
her forty pages. Ends with the Mission rig striking water.
New: EV-4509 Iseabail drives the cattle west (AE 107); EV-4510 Iseabail at Allt an Àigh (AE 108); EV-4511 Iseabail
begins her petition (AE 110).

### PART FIVE — Of the Word and the Line (AE 111–137)

**Book 09 (W09): Of the Law of One Line, the Night Shift and the Cellar** — *AE 111 – 126*.

**Ch 28. Of the Law of One Line** — POV Thomas Hale. AE 111 Feb – AE 113 Dec (~5,000 w).
Masters: IV-0229–0234.
Iseabail's forty pages and Haskins's one line. Thomas Hale claims a share in a customary cutting through his
grandmother; Dunstan rules that rights descend only through the line the Administration recognises. Within a few years
eleven cuttings pass to the Company; Cnoc dhubh's since the Holy Age. The custodians stop entering such marriages.
Thomas sees his suit made a weapon. The Lamp-Watch begins at Baile thais and Cnoc chaol under the burial club; its first
deed, burying an old breaker who died in the lock-up. Turn: the ruling read. Ends with Thomas at the burial, the one
man there who can read the humans' law.
New: EV-5001 Thomas Hale's suit filed (AE 111); EV-5002 the Baile dhìreach custodians stop entering marriages (AE 112);
EV-5003 the old breaker dies in the lock-up (AE 113).

**Ch 29. Of the Night Shift** — POV Matthew Dunne; Iain Maor. AE 114 Jun – AE 120 Apr (~5,000 w).
Masters: IV-0235–0244.
Haskins recalled; Vane, born at the Residency, speaks Dia-thìris badly. The tram-road to Ros dhìreach. The night-shift
order: the hill given no silence; Cnoc chaol's two shifts by coal-lamp; the strike, replaced in a week; Muileann
dhomhain turns the strikebreakers from every door; the Lamp-Watch purse runs dry. Dunne preaches the ground must rest;
recalled; the sermon copied into the camps. The lung-rot kills the humans of the night crews; few Dia-thìrich who cough
die of it; the old women say *Donnchadh's cough* and no more. Iain Maor's letter filed with his dismissal, reversed. The
coal line opens; Baile ghorm's lamp-bodies. Turn: the sermon. Ends with the first coal train into Ros dhomhain.
New: EV-5004 Vane speaks Dia-thìris at Cathair dhearg (AE 115); EV-5005 the strike purse runs out (AE 117);
EV-5006 Dunne sails (AE 118).

**Ch 30. Of the Cellar at Muileann chaol** — POV Cailean mac Eachainn. AE 121 Feb – AE 126 Feb (~5,000 w).
Masters: IV-0245–0251.
Fionnan born (birth only): the second case. The census, true for humans, rounded for Dia-thìrich; the outer coasts ruled
from Seann Vell on Eilean ruadh. Seònaid nic Dhùghaill dies and the Deer register ends. The custodians of the east send
their rolls to Muileann chaol; the three households copy in the cellar; Cailean is taken on. Some copies go to the other
Muileann chaol (196); Cailean fetches them back. Peigi Ghlas calls the custodians to Cill ghlas: cloaks steaming, Brìde's
lamp in the cutting, pumps in the dark; the plain word *fuil-ghuail*, coal-touched. Turn: the vote. Ends with the word
written in a physician's column.
New: EV-5007 Cailean joins the three households (AE 122); EV-5008 Cailean fetches the mis-sent copies (AE 125);
EV-5009 Peigi calls the custodians to Cill ghlas (AE 126, before IV-0250).

**Book 10 (W10): Of the Line of Aisling, the Grey Goose and the Rending** — *AE 126 – 138*.

**Ch 31. Of the Line of Aisling** — POV Cailean, then Mòrag nic Iain. AE 126 Oct – AE 131 Sep (~5,000 w).
Masters: IV-0251a, 0252–0258.
The Àth ìseal roll; the seven names; the walk to Tobar dhìreach; Ealasaid's recital, which must match master Book V
§XII exactly; "I told you whose son he was". The Residency orders the reporting; the custodians report none. Barter
struck down; the barter houses shut ("complete for the first time"); the fishwives of Inis mhòr refuse coin a week;
marks borrowed at interest; Muileann òg's market closes. Peigi Ghlas dies. Iain Maor dies; Mòrag takes the staff, "a
safe pair of hands". Turn: Ealasaid's words. Ends with Mòrag hanging the staff over her hearth.
New: EV-5501 the custodians' first return to the Residency: none (AE 127); EV-5502 Peigi Ghlas dies (AE 128);
EV-5503 Iain Maor buried (AE 131).

**Ch 32. Of the Grey Goose and the Dockers** — POV Hannah Webb. AE 132 Aug – AE 135 Mar (~5,000 w).
Masters: IV-0259–0266.
Vane dies; Merriman and his constables; the posts at Muileann shean and Tobar ghorm. Hannah, a human labourer near Baile
chrom, learns the night prayer from a Ceann mhòr fisher-wife and keeps the silent vigil under the grey goose; the
Mission calls it irregular; Baile chrom disowns it; Manannan's priests say their prayer went astray. Her brother, a
docker at Ros dhomhain, strikes nine days beside Dia-thìrich; Merriman breaks it and the human dockers are shipped;
Seann Vell's dockers stay out. Lorccan and Cian born (births only). Turn: the ship taking her brother. Ends with two
births written in a custodian's roll.
New: EV-5504 Merriman's constables land (AE 132); EV-5505 Hannah Webb's first vigil (AE 133); EV-5506 the human dockers
shipped (AE 134).

**Ch 33. Of the Rending of Cill ghlas** — POV Mòrag nic Iain Maor; Eilidh nic Raghnaill. AE 136 Jan – AE 138 Jan (~5,000 w).
Masters: IV-0267–0275.
Blasting-powder; the custodians' request marked on Robert Fairley's plan, the charges set below it; powder landed at
Caol ìseal. 9 an t-Ògmhios AE 137: the ground grinds like a quern, the fault tears, dozens die (Raghnall Breac among
them), the shrine goes down; the roll sets the shrine before the dead. The district fenced; the moor-road stone;
Achadh chaol built. The flooded gallery at Muileann chrom: seven after the pumps were stopped; Edgar Holt speaks of the
loss to the working; the first stone; rifle smoke; four and one. The inquiry: Mòrag testifies; struck out; Eilidh gets
the copy for the Lamp-Watch. Turn: the striking-out. Ends Part Five.
New: EV-5507 Fairley marks the request (AE 136); EV-5508 Raghnall Breac among the dead (AE 137); EV-5509 Eilidh
nic Raghnaill joins the Lamp-Watch (AE 137).

### PART SIX — Of the War of the Hills (AE 138–151)

**Book 11 (W11): Of the Warning, the Houses on the Roads and the Breaking of the Staff** — *AE 138 – 149*.

**Ch 34. Of the Warning and the Constables** — POV Eilidh nic Raghnaill. AE 138 Feb – AE 141 Apr (~5,000 w).
Masters: IV-0276–0289.
The grey fever off the ships, young and strong first; Cathair mhòr's market shut; Dùn thais loses its physician. Eilidh
drafts the second petition in the burial club's room; thirty-one settlements; the underlined sentence. Coinneach Ruadh
signs and loses his clerkship. The answer: constables tripled, fortified stores, the empty barracks at Dùn chrom.
Ìomhar Seabhag at Seann Skell; Ros gheal's shrine; hawk and Deer at Inis bhàn. The fever in the north-west; Hannah Webb
nurses in the shared wards at Cathair gheal; Muileann fhionn shut in; Tobar fhiadhaich. Turn: the answer is constables.
Ends with Eilidh reading Ìomhar's sermon to the Lamp-Watch.
New: EV-6001 Eilidh drafts the petition (AE 138); EV-6002 the first constables' company at Baile thais (AE 140).

**Ch 35. Of the Houses on the Roads** — POV Aonghas of An Taigh-seinnse Mòr. AE 141 Sep – AE 146 Nov (~5,000 w).
Masters: IV-0290–0314.
The road-houses make ready: the walled well, the six ostlers, the Grianach's watch, Tormod Buabhall's lists, Doire
shean's landing, the loft at the Reòta, the Sligeanach post-house, the boy runners of Àth fhiadhaich, the ledgers at
Achadh mhòr; Aonghas searched most, found least. 27 am Màrt AE 143: the fire on Cnoc an Rabhaidh (taken for heath fire);
every working stops at once; six days of empty holds; broken by shutting the stores; forty taken, eight shipped and
never heard of; the heather burned. Fewer, older ships; idle Caol leathan and Caol bheag. Leave no longer asked;
Merriman out, Strake in. Turn: the six days. Ends with Strake's commission read without the council's name.
New: EV-6003 Aonghas takes the loft (AE 142); EV-6004 the fire on Cnoc an Rabhaidh (AE 143, same day as IV-0301).

**Ch 36. Of the Breaking of the Staff** — POV Mòrag nic Iain Maor. AE 147 Feb – AE 149 Feb (~5,000 w).
Masters: IV-0315–0324.
The hall locked; the custodians in Macha's temple. The iron bird over the coal country. The edict of seizure; Doire mhòr
emptied by constables; two streets at Baile dhomhain. The order to Mòrag; the staff across her knee on the Company's
step; three overseers resign. The guild buys rifles from the eastern raiders, entered as refining tools. The forest
council at Cnoc bheag chooses Eilidh; Strake's arrest order; Baile thais silent. 20 an Gearran AE 149: war. Turn: the
staff. Ends on the day of war.
New: EV-6005 the iron bird seen over Muileann chrom (AE 147); EV-6006 the forest council's first fire (AE 148);
EV-6007 Eilidh leaves Baile thais by night (AE 149).

**Book 12 (W12): Of the War of the Hills, the Leaden Hawk and the Closing of the Crossing** — *AE 149 – 151*.
Epigraph: *Loisc iad an leabhar, ach cha do loisc iad an cnoc.*

**Ch 37. Of the Rising in the Hills** — POV Mòrag; Seumas Ciar; Uilleam Gobha. AE 149 Feb – Dec (~3,900 w).
Masters: IV-0325–0335.
First light at Muileann chrom: eleven constables yield. Ceann fhada's quay, two barges sunk. Baile thais: eleven days,
water gone, the constables sent to the coast unharmed on Eilidh's order. The moor above Cnoc naomh; the northern pits
rise. Aonghas shuts the coal road. Uilleam Gobha's tin grenades and rail pikes. The capital rises: the hall's locks, the
bridge barricaded with carts; the Cathair dhomhain warehouse opened (ch 6). Muileann mhin argues three days. The
Residency fortified. Àth chiar: Ashdown's column waist-deep, forty lost; nineteen rebels named. Turn: sparing the
constables. Ends with the nineteen names.
New: EV-6501 the constables of Baile thais sent to the coast (AE 149); EV-6502 Uilleam Gobha's first grenades tried
(AE 149); EV-6503 the nineteen of Àth chiar buried (AE 149).

**Ch 38. Of the Leaden Hawk** — POV Coinneach Beag. AE 150 Jan – Jun (~3,900 w).
Masters: IV-0336–0352 (incl. 0342a–e).
Ashdown's retreat and Dùn chrom's shut gates; the silver town rises; Dùn ìseal yields; Dùn dhearg declares, quoting
Fionnghal; Cnoc leathan's riflemen; Ros fhionn floods; Seann Toll shelled. The seven wait nine hours at An Cupa Dàna;
lead hawks cast from cartridges; the route exactly as the masters give it (Seann Toll, Baile thais, Achadh dhomhain,
the Abhainn ìseal, Cnoc bheag, the Hawk coast, Inis mhin, carriage, the grass watch counting forty-one riders, Inis thais
where the Stone shuts its harbour and lends the Fianna's roads). Inis mhòr coaling; the two Seann Chwens' raids;
Cathair gheal and Muileann àrsaidh keep out; the hawk-shrines open; the southern lights put out (Raonaid) and two ships
lost; one ship from over the sea. Turn: the forty-one riders all riding south. Ends at the midsummer lines.
New: EV-6504 the lead hawks cast (AE 150); EV-6505 Raonaid nic Dhòmhnaill's daybook line on the dark night (AE 150).

**Ch 39. Of the Burning of the Ledgers** — POV Dùghall Dubh. AE 150 Jul – Sep 21 (~3,900 w).
Masters: IV-0353–0362.
Grain from Seann Warr (128); the capital shares by household and the custodians take the same. Over the roofs in
stocking feet; the tithe books in the yard; the light struck. Ceann àrsaidh: the ledger the custodians asked to spare,
refused. Muileann chrom's weigh-house burns green; the verse. Cnoc ghorm. The harbour quarter opens its lower gates; the
iron bird's shed burned. Cuan uaine's quays. Strake goes by water; the companies find the Residency stripped but for the
letter-books. Turn: the unspared ledger. Ends with the letter-books on the Commissioner's table.
New: EV-6506 Dùghall's men gather on the roofs (AE 150); EV-6507 the letter-books counted at the Residency (AE 150).

**Ch 40. Of the Truce and the Closing of the Crossing** — POV Eilidh Hale; Lachlann mac Uisdein; Cailean (frame). AE 150 Sep 23 – AE 151 1 Faoilleach (~3,900 w).
Masters: IV-0363–0377.
Ros bheag the last seat; outposts at Ros àrsaidh; hunger, and Strake opens the stores to both peoples. Cuan shean shuts
its harbour. At Baile dhìreach each side asks the children of the old council which people they are; Eilidh Hale does
not answer and stays. The last ship at Samhain with its sealed letter. The truce of Àth àrsaidh; Baile Mòr ruadh (303)
receives the columns; its Dia-thìrich choose. The columns north: the count at Àth chrom, the name written down at Àth
leathan; Hannah Webb among them. The harbour officers of Ceann mhòr, Cathair gheal and Inis àrsaidh board Strake's
ship at Cuan shean with their keys. Lachlann watches her stand out north until the sea has her. The beacons relit; *Cha
tàinig long*. The rolls come down to the cellar; Cailean opens the first chest (frame closes). 1 am Faoilleach AE 151:
the Severance; Cian and Lorccan not yet twenty. End on that day, with what was lost and what was kept, not on what
came after.
New: EV-6508 Eilidh Hale's silence (AE 150); EV-6509 the harbour officers board with their keys (AE 150);
EV-6510 Cailean opens the first chest (AE 150, after IV-0376).

## 4. Continuity

- **Opening state** (end of master Book IV, III-0239a): the crown empty since Gormshuil nic Thormoid; the Small-Burning
  Law kept; Clann Choinnich's silver petition unanswered; eleven keep the empty-harbour rite at Seann Skell; the mist on
  the eastern sea thinner each winter; Manannan's priests praying at every tide; the north-west nearly empty; no ship
  has come for eighteen centuries. The Council of Custodians sits in the crown's place (as IV-0005 finds it).
- **Closing state** (opening of master Book VI): 1 am Faoilleach AE 151, the Severance; the humans (a few thousand)
  marched north under the council's guard into the old concession country; the council at Cathair dhearg with the high
  custodian's seat still empty and Eilidh nic Raghnaill speaking for the forest council; its companies under arms and
  their rolls not yet put away; the counting-houses at Cathair dhearg, Ros dhomhain and Seann Skell not yet emptied;
  the northern harbour officers gone with their keys; the stores from over the sea stopped; the beacons burning with
  nothing to count; Cian and Lorccan children; no king.
- **Threads** (THREADS.json ids; tag every event that moves one):
  `the-mist` ch 1, 5, 16, 35, 40 · `the-company` ch 6–39 · `the-church-on-the-island` ch 2, 8, 9, 17, 18, 29, 32 ·
  `the-coal-blood` ch 19, 22, 29, 30, 31, 32, 40 · `line-of-aisling` ch 12 (Tormod), 19, 31 · `the-keepers-promise`
  ch 19, 31 · `line-of-the-mason` ch 31 (Ealasaid) · `the-seven-coals` ch 2, 18 (the coloured flame), 30 ·
  `the-orders-of-the-old-faith` ch 9, 10, 16, 22, 23, 32, 34, 38 · `the-library` (tag only, never the name) ch 2, 12,
  30, 31, 40 · `the-tuathaich` (tag only, never the name) ch 9, 16, 32, 40.

## 5. Cast

See `PLAN_people.json` (91 entries: owner's characters flagged; master-named people marked; new people marked).

## 6. Writer assignment (12 writers, ~15.5k words each)

Chapter writers write `events/NN.json` only; the foreman compiles `annals/age_V_NN.json` (`"writer": NN`) per block below. Id range: N = ceil(NN/2); odd NN uses EV-N000–N499, even NN
EV-N500–N999. Target 20–25 era events each (the listed ones plus more small ones in the same gaps), total with the
403 masters about 650.

| W | Book file | Ch | Span [FROM, TO] | Ids | Opens with | Closes with |
|---|---|---|---|---|---|---|
| W01 | book/01_of_the_gauze_on_the_water.md | 1–3 | IV-0001, IV-0021 | EV-1000–1499 | mist thinning, empty crown, Law kept | the post trading fairly; Pike's letter home; Tull's debt |
| W02 | book/02_of_the_council_of_six.md | 4–7 | IV-0021, IV-0041 | EV-1500–1999 | fair exchange at its height | first pit at Muileann chrom; Raghnall leads the thirty; Residency and Company stand |
| W03 | book/03_of_the_door_at_doire_mhor.md | 8–10 | IV-0041, IV-0071 | EV-2000–2499 | the first pit working; Wren's grammar near done | Law lapsed; Maddox in; oaks felled; Coinneach Glas high custodian |
| W04 | book/04_of_the_eleven_of_cnoc_fhiadhaich.md | 11–13 | IV-0071, IV-0100 | EV-2500–2999 | Maddox doubling the yield | Raghnall Maor overseer; Beathag and Gormshuil dead; Lisle's bound book |
| W05 | book/05_of_the_ledgers_at_the_adit.md | 14–17 | IV-0100, IV-0138 | EV-3000–3499 | Lisle reading the book | Silver Compact held; Hales stay; Crane Commissioner; Dòmhnall Maor |
| W06 | book/06_of_lowes_spade.md | 18–20 | IV-0138, IV-0163 | EV-3500–3999 | four beacons; tithe at one in three | Aisling born (AE 69); Green Death past; Tolley in; Ùna dead |
| W07 | book/07_of_the_eleven_days.md | 21–23 | IV-0163, IV-0194 | EV-4000–4499 | Tolley's letter-book; camps under the hawk-feather | Catrìona at the guild; Iain Maor; Levy in force; ring of beacons lit |
| W08 | book/08_of_gorta_baile_chrom.md | 24–27 | IV-0194, IV-0229 | EV-4500–4999 | the ring lit, the Levy stripping the fields | high custodian's seat empty; drought over; Iseabail writing |
| W09 | book/09_of_the_law_of_one_line.md | 28–30 | IV-0229, IV-0251a | EV-5000–5499 | Haskins; petitions singly | Lamp-Watch alive; coal line; *fuil-ghuail* agreed; Fionnan born |
| W10 | book/10_of_the_line_of_aisling.md | 31–33 | IV-0251a, IV-0276 | EV-5500–5999 | the word in the column | line found; Mòrag holds the staff; the Rending; first blood; inquiry |
| W11 | book/11_of_the_warning.md | 34–36 | IV-0276, IV-0325 | EV-6000–6499 | the struck testimony copied | staff broken; forest council; war declared |
| W12 | book/12_of_the_war_of_the_hills.md | 37–40 | IV-0325, end | EV-6500–6999 | the day of war | the Severance, 1 am Faoilleach AE 151 |

`told_in` anchors: `book/NN_<slug>.md#<section anchor>` of each chapter file. The Book-file column above is superseded by one file per chapter.

## 7. Back matter

- **Chronicle:** 403 masters + ~250 era events (500–800 total), ids and spans above. Bodies 1–4 sentences, Tale of
  Years voice; every event with category, links (answers, causes, person, legacy to earlier ages where apt), threads,
  people (ids via the lead from PLAN_people), `told_in`.
- **Gazetteer** (`gazetteer/NN_<slug>.json`, one per writer; ~70 towns, ~180 words each; all stand at the close;
  never Doire mhòr 101, Cill ghlas 123, Cnoc mhòr 140):
  W01 282 Cuan shean, 19 Cathair dhearg, 27 Ros dhomhain, 242 Achadh àrsaidh, 17 Inis mhòr, 64 Seann Warr ·
  W02 105 Baile dhìreach, 134 Baile fhiadhaich, 1 Caol leathan, 398 Tobar dhearg, 26 Cathair dhomhain, 433 Cnoc àrsaidh ·
  W03 351 Ceann fhada, 422 Dùn dhearg, 132 Seann Skell, 297 Cathair fhada, 23 Cathair mhòr, 77 Dùn thais ·
  W04 354 Muileann chrom, 280 Cnoc fhiadhaich, 109 Cill thais, 383 Àth ìseal, 313 Seann Toll, 224 Baile dhomhain ·
  W05 419 Muileann chiar, 110 Seann Bhral, 258 Àth dhearg, 476 Cathair gheal, 143 Ceann mhòr, 371 Inis bhàn ·
  W06 327 Muileann bheag, 135 Achadh dhomhain, 461 Cill dhìreach, 393 Àth ghlas, 318 Cnoc naomh, 366 Caol mhin ·
  W07 44 Baile thais, 355 Muileann chiar (west), 502 Muileann bhàn, 20 Cnoc bheag, 269 Cnoc thais, 95 Caol mhòr ·
  W08 305 Baile chrom, 209 Doire ghlas, 88 Ceann àrsaidh, 46 Àth fhionn, 411 Achadh shean, 387 Baile Mòr ruadh ·
  W09 415 Cnoc chaol, 152 Ros dhìreach, 246 Muileann chaol, 202 Muileann dhomhain, 198 Cnoc dhubh, 3 Baile ghorm ·
  W10 276 Tobar dhìreach, 212 Muileann shean, 438 Tobar ghorm, 86 Caol ìseal, 389 Achadh chaol, 29 Seann Vell ·
  W11 255 Dùn chrom, 462 Cnoc dhìreach, 491 Muileann dhearg, 24 Ros gheal, 12 Àth fhiadhaich, 395 Achadh mhòr ·
  W12 163 Àth chiar, 315 Dùn ìseal, 10 Cuan dhearg, 166 Inis thais, 63 Ros bheag, 304 Àth àrsaidh, 412 Àth chrom,
  346 Àth leathan, 303 Baile Mòr ruadh, 489 Seann Skell.
- **Appendices** (as they stood at the close of the age, ~3–4k words each):
  - `appendices/A_rulers.md` (W04) — *The Council, the Commissioners and the Stewards*: high custodians (Tormod mac
    Ailein, Coinneach Glas, Alasdair Liath, Artair mac Iain, the empty seat); the forest council and its speaker;
    Harrow and the ten Commissioners with years; the Stewards of Muileann chrom; heads of the silver guild; the keepers
    of the five lights.
  - `appendices/B_faiths.md` (W06) — *The Faiths under the Strangers*: the Church and the Mission (chapel, bell, school,
    kitchens); the Coal Rite at the pit-mouth shrines (Cill dhìreach, Cill ghlas); the Hawk (Murchadh, Ìomhar, the
    feathered doors); the Deer (the question, the shut hall, the forest); Macha's blessing and the dissenters; the
    Grey Night; the Keeper's gift as the camps tell it.
  - `appendices/C_hosts_wars.md` (W11) — *Strikes, Sicknesses and the War of the Hills*: tables of the sicknesses
    (strangers' fever to grey fever) with dead and places; the strikes and the stoppage; the constables' posts; the
    council's companies, the guild's riflemen, the hawk company, the Leaden Hawk; the fights of AE 149–150.
  - `appendices/D_reckoning.md` (W07) — *Two Dates on Every Page: Reckoning, Coin and Measure*: the Diosal year beside
    the humans' day and week; the mark and its hundred pence and the three changes of coin; the steelyard and the ton;
    the tithe from one in five to one in three; the daybooks as a count of years.
  - `appendices/E_words.md` (W01) — *Words of the Age of Strangers*: the forty colours (as many as the leaf keeps);
    *an Tìr Thall*, *an Eaglais*; the words taken from the humans' tongue and the words coined against them
    (*eun-iarainn*, *fuil-ghuail*, *Aisling-aois*, *nighean an rìgh*, *Maor*); sayings of the camps.
