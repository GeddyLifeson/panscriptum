# Age VI volume plan: An Aois Rìoghachd, the Age of the Kingdom (SE 1 – 71)

Architect's plan for the era legendarium of Age VI. Writers read this whole file, then WRITERS_GUIDE.md, TELLS_FOR_WRITERS.md,
the master Book `legendarium/book/age_VI.md` (our spine: every scene it already tells must be kept in substance), and
the master annals `eras/age_VI/annals/age_VI_master.json` (use THIS file's bodies, not legendarium/annals_dated.json:
the rescale changed V-0004 "above ten", V-0018 "a little over forty", V-0036a "on every five thousand heads").

## 1. The volume

**Title.** *Scrìobhte a-nis*, "Now Written".

**Epigraph** (for `front.json`, lead):

> *Cha shocraich an Leabharlann dad. Cha dèan i ach gleidheadh.*
> The Library settles nothing. It only keeps.
>
> — Ailean Leabhar, first keeper of Leabharlann Muileann chaol, {{date:V-0072}}

**Premise.** When the crossing closed and the humans left on Dia-thìr were marched north, the council that had won the
island made itself a kingdom, crowned a king by Macha's rite and set about living in the house the strangers had built:
their survey lines became its shires, their tariff its dues, their pits its wealth, their night shift its law. In the
north the children of the humans, the Tuathaich, met in a wet room at Caol mhòr and opened a minute-book that nobody
south would read. For seventy years the kingdom counted what suited it and filed the rest: the Moot's petitions, the
northern dead, a surveyor's warning that the vein was thinning. The novel follows the clerks, justices, keepers and
surveyors who wrote things down, and those who refused to, until the census is read aloud at Caol mhòr and the Moot
writes two words: *Now written*.

**The question the volume answers.** How did the kingdom that took the island back from the strangers come to work
the vein by the strangers' ways for seventy years, not looking at what it was doing to the north or to the mountain,
and what did it cost the few who wrote the truth down before anyone would read it?

## 2. Point of view and voice

The high recollection voice of the master Books, framed as the Library at Muileann chaol's own telling at the close
of the age, with scenes lived close to one person at the turns (BOOK_STYLE_BRIEF: roughly half recollection, half
POV). This age is quicker, drier and more wry than the old ages, and it is an age of paper: minute-books, ledgers,
receipts, tallies, registers. Let documents speak (a four-line minute, a receipt, a struck-through note) and let
people speak plainly. Tuathaich speech is the humans' tongue, rendered in plain English; Dia-thìris lines are rare
and always followed by their English. Each chapter has one central figure; a chapter may open or close with a short
recollection section in the Library's voice to carry master events its central figure cannot see.

**Principal characters** (a relay; each carries the age through part of its length):

| Person | People | Carries | Chapters (central) |
|---|---|---|---|
| Ailean mac Iain, later **Ailean Leabhar** | Dia-thìreach council clerk, then first keeper of the Library (AE 126 – SE 40) | the settling, the Great Wave's tally, the Library | 1, 3, 5, 6, 16, 24 |
| **Walter Hale** | Tuathaich, once a harbour clerk of Ros bheag; first speaker of the Moot (AE 107 – SE 33) | the north's first generation | 2, 4, 7, 25 |
| **Eilidh nic Leòid** | Dia-thìreach, first circuit justice (AE 106 – SE 16) | the law made exact and made for one people | 9, 15 |
| **Gormshuil nic Dhùghaill** | Dia-thìreach council clerk, first royal chronicler (AE 132 – SE 48) | the royal record: what it says and what it leaves out | 11, 17, 20, 23 |
| **Iain mac Ruairidh, Iain Mapa** | Dia-thìreach Board surveyor (AE 144 – SE 57) | the vein and the warning filed | 12, 22, 27, 28 |
| **Daniel Frayne** | Tuathaich, pupil of Agnes Pike, Moot clerk, bookbinder, speaker from SE 55 (SE 5 –) | the north's second generation | 14 (as a child), 29, 35, 37 |
| **Catrìona nic Neacail** | Dia-thìreach Board surveyor, surveyor-general (SE 18 –) | the Depletion laid bare | 32, 34 |

Guest centres for single chapters: Dòmhnall mac Thormoid (8), Hannah Crane (10), Harry Marlow (13), Agnes Pike (14),
Nell Barrow (18), Oighrig nic Mhathain (19), Mary Coyle (21), Raonaid nic Iain (26), Murchadh mac Coinnich (30),
Seonaid nic Ghill-Eathain (31), Ciorstaidh nic Artair (33), Tormod Pinn (36), Beathag nic Fhionnlaigh (38). The
principals turn up in each other's chapters (Hale at Eilidh's court, Iain Mapa at Catrìona's table, Frayne at
Seonaid's wood), so the relay reads as one story.

### Hard rules for this age

- **The owner's characters stay offstage.** Niall, Brìghde, Eòghan and Mairead: crowned, died, succeeded, exactly as
  the annals and Appendix A say, and nothing more (no words, thoughts, scenes, causes; Brìghde's death has no cause
  made public and none may be hinted). Their ages are the owner's rule and are fixed in eras/RULERS.json: Niall born
  AE 128, crowned at 25 (SE 3), dead at 44 (SE 22); Brìghde born SE 1, crowned at 21, dead at 27 (SE 28); Eòghan born
  AE 146, crowned at 32, his reign ending at 62 (SE 58); Mairead born SE 20, crowned at 38. An age may be stated with
  the fact, and nothing more. **Dubhan**: born SE 29 in the north (V-0115), a childhood watching the caste
  that does not age (V-0149), experiments from SE 61 that fail (V-0207); in the last chapter only the master Book's
  own line (he banked his fire and slept beside it). No scene, speech or thought of his. **Seachran, Brean** and the
  Splatter and Dodge generation: born SE 24 among the shunting families (V-0100); nothing more, and not "who grow up to
  be Dubhan's allies". **Aisling, Fionnan, Lorccan, Cian**: no appearance; the age knows the coal-touched only as a
  census line "and nothing more" and as the Rite's doctrine. Keep the master's phrases about the ruling caste ("an
  aristocracy that stood very near the undying") as they stand, and add nothing to them.
- **Nothing past 18 an t-Ògmhios SE 71.** Master bodies that look ahead must be told only as far as the age goes:
  V-0078a (say "six ages as the table then stands"; never "seven" or "the Dubhan Era"), V-0092 ("It was thought one
  later": drop), V-0100 (drop "allies"), V-0125 (the store's first opening at Achadh shean is told in SE 43, not in
  SE 33), V-0128 and V-0143 ("came later to the library": tell only when it happens, or not), V-0139 (the confusion of
  the two Dùn thais begins; Tormod Pinn marks them west and east in SE 48, told then), V-0209 (drop "next
  generation"), V-0211 ("outlasts the crossing by years"), V-0231 (Tom Varley is the accounts-keeper's small son, not
  "the pit captain"). The master Book's "Àth leathan will come into this book again" must not be copied. No Cathal,
  no dubhan fuel, no Long War, no regiments raised, no Age VII names (Martha Greaves, Peter Hale, Ruth Calder).
- **Two of everything.** Seann Skell *in the west* (burg 489: the humans' harbour, Òrd Mhanannain, the counting-house)
  and Seann Skell *on the southern coast* (burg 431: the high custodian). Seann Bhral *in the west* (burg 47: the Leòid
  ruling, the western branch, Manannan's feast, the carrier ruling of SE 59) and Seann Bhral *in the south* (burg 110: the fishing
  port, the pumps). Dùn thais west (8) and east (77). Always say which.
- **Numbers.** The island holds about 1.3 million at SE 1 and 1.5 million at SE 71; the Tuathaich are about one in
  nine. Towns are small (the capital about 500 souls in its walls, Caol mhòr about 1,800, the southern Seann Skell
  about 2,500). Keep the canon's small figures: above ten dead at Doire ghlas, a little over forty in the Great Wave,
  thirty-one at Muileann dhearg. Head-due: 18 purses on every 5,000 heads. Distances (0.14 mi to the unit): Cathair
  dhearg to Caol mhòr 34 miles, to Muileann chaol 59, to the Sloc Mòr 31, to the fair at Muileann òg 14; Caol mhòr to
  Doire ghlas 10; the Sloc Mòr to Muileann chiar 24, to Cathair mhòr 16, to Muileann dhearg 5; Ceann mhòr to Baile
  chrom 3, to Àth leathan 15; Àth leathan to Seann Bhral in the west 13.
- Voice: TELLS_FOR_WRITERS in full. The master Book's scenes (the Moot, Cuan dhearg's boats in the barley, Eilidh at
  Ceann mhòr, the cellar, the receipt, "Now written", Catrìona's week in the files) are the spine; expand them, keep
  their facts and their best lines, and do not copy their sentences wholesale.

## 3. Structure

Six Parts, thirty-eight chapters, about 182,000 words. Each chapter is its own Book file,
`book/NN_<slug>.md` (NN = 01–38, slug from the title), opening `# <chapter title>`, then the date line, an optional
epigraph, and `## I.`, `## II.`… sections (three to six per chapter). A chapter that opens a Part (1, 7, 13, 19, 26,
32) puts the Part title in its date line block as `*Part One: Of the Settling*` above the dates. Words given are targets.

### PART ONE: OF THE SETTLING (SE 1 – 5)

**1. Of the Winter of the Severance** · Ailean mac Iain · 1 am Faoilleach AE 151 (as memory) – SE 1 an t-Ògmhios ·
V-0001, V-0002 · 5,000 w.
Open in recollection on the last page of the Age of Strangers (the beacons' *Cha tàinig long*, the columns north),
then close on Ailean, twenty-five, a hill-born council clerk named for the first king, riding north with the council's
guard as tally-clerk at the heads of the roads. At Caol mhòr on 22 am Màrt the council's word fixing the homeland is
read to a wet crowd; it must be read in the humans' tongue too, and the reader found is Walter Hale, a harbour clerk
of Ros bheag, who reads it flat and then, privately, corrects the word Ailean had used for it: not "settled", "held".
Ailean writes Hale's word in his margin. South again, 3 an t-Ògmhios at Cathair dhearg: the war-companies stood down;
a captain, Fearchar mac Raghnaill, begs that his company's roll not be burned; Ailean carries the rolls into the
council's chests and writes the list of what he carried. Turn: the two words in the margin. Ends on the chests locked
and the list signed.
*New events:* guard posted at the heads of the north roads (SE 1); the count at the heads of the roads, the council's
last tally of the columns (SE 1); the humans' chapel at Ros bheag shut and its bell carted north (SE 1); the captains'
plea that the companies' rolls be kept (SE 1).

**2. Of the Stones on the North Roads** · Walter Hale · SE 1 an t-Ògmhios – SE 2 an Cèitean · V-0003, V-0004 · 5,000 w.
Hale, forty-four, with his wife Ellen and children David and Alice, lodged at Caol mhòr, unloading at the quay. On
31 an t-Iuchar the council's masons set the stones on the north roads; Hale walks out to the one on the Caol mhòr
road, reads its cut Dia-thìris to David, and no wall follows. The harvest is thin; the stores from over the water
never come; the Caol mhòr boats share their catch by households. In an Dùbhlachd Hale carries meal to Doire ghlas
(ten miles) and helps bury: above ten, children among them; the Dia-thìrich make no count, so the Tuathaich make
their own, and Hale begins his day-book as a count. Turn: realising no one south will ever count these dead. Ends in
spring with the names pinned in the church porch at Doire ghlas and the herring back.
*New:* the north's first harvest short (SE 1); the Caol mhòr catch shared by households (SE 1); Hale's day-book begun
(SE 1); names of the hungry year's dead pinned at Doire ghlas (SE 2); seed oats from the Doire mhin mill on credit
(SE 2); the herring return to the Caol mhòr grounds (SE 2).

**3. Of the Counting-Houses and the Broken Locks** · Ailean mac Iain · SE 2 an t-Ògmhios – an t-Iuchar ·
V-0005, V-0006, V-0007 · 5,000 w.
The council's clerks go through the humans' counting-houses at Cathair dhearg, Ros dhomhain and Seann Skell in the
west; the tithe ledgers are charred and in a hand few can read. Ailean, who learned some of it from a Mission reader
as a boy, is told to box them unread, and does. In the Seann Skell house he finds the humans' district surveys, the
only whole surveys of the island, and boxes them apart with a label: the shires will be drawn on them. A recollection
section, told as the north tells it: at Ceann mhòr, Cathair gheal and Inis àrsaidh the fishermen take hammers to the
harbour stores' locks and share out house by house. 27 an t-Iuchar: the state styles itself Rìoghachd Dia-thìr from
the council's steps; Ailean in the crowd notes it is ruled as before. Turn: the labelled box. Ends on the
proclamation.
*New:* the humans' district surveys sent to the council from Seann Skell in the west (SE 2); the tariff tables of Ros
dhomhain copied out (SE 2); the council's seal first cut (SE 2); the proclamation read at the market crosses of the
south (SE 2).

**4. Of the Moot and the Council of Twelve** · Walter Hale (last section Ailean) · SE 2 an Lùnastal – an t-Sultain ·
V-0008, V-0009 · 5,500 w.
The master scene grown to a chapter: the householders of the northern towns in the long low room at Caol mhòr, the
afternoon's argument, the name going round like a bucket along a line, "We've no standing", the book with nothing in
it and the day written. The Moot's first business: grain for the winter, the guard, the dead of Doire ghlas; a shared
granary; a letter south carried by a carter. Last section at Cathair dhearg, 23 an t-Sultain: the council of twelve
seated (custodian families and captains; name four), its minute-books opened; the under-clerks Ailean mac Iain and
Gormshuil nic Dhùghaill sworn; the Moot's letter read aloud; a councillor asks what a Moot is; it is filed. Turn: the
two minute-books opening a month apart. Ends with both books shut for the night.
*New:* the Moot's first letter to the council, filed (SE 2); the Moot's granary at Caol mhòr (SE 2); Gormshuil and
Ailean sworn under-clerks (SE 2); the council's first minute of its twelve and their seats (SE 2).

**5. Of the Grey Water and the Crowning** · Ailean mac Iain · SE 2 an t-Sultain – SE 3 an Dùbhlachd ·
V-0010 – V-0014c · 5,000 w.
Ailean sits with Dùghall mac Iain in the Ros dhomhain sheds while the humans' tariff stays in force for want of
another. On 11 an t-Ògmhios SE 3 he sails as the council's clerk in *An Sireadh* under Aonghas mac Mhurchaidh, out of
Cuan shean, past the north-western capes and north-about: a month of grey water, the mist, no land, no sign of a
passage; the captain turns home. The priests of Manannan at Seann Skell in the west say *A Mhanannain, cùm a' mhuir
dùinte* at the harbour mouth as she comes in. He has missed Niall's crowning (19 an t-Ògmhios, told in recollection)
and comes home to *mar a thàinig Niall* in a tavern ledger. In an Dùbhlachd he draws shire lines on the surveys he
boxed; the lines stop at the great moss; he writes the minute that the windy coast "is not in the survey"; the two
island shires; the Ceann mhòr market right. Turn: the edge of the map. Ends on that minute.
*New:* *An Sireadh*'s log filed with the council (SE 3); the prayer said at the western Seann Skell on her return
(SE 3); the council's shire map drawn on the humans' sheets (SE 3); Dùghall mac Iain's first clause of the tariff in
Dia-thìris (SE 3).

**6. Of the Great Wave** · Ailean mac Iain · SE 4 am Faoilleach – SE 5 an Giblean · V-0015 – V-0022 · 5,500 w.
Maoir set over the shires; the dues (cìs-cinn, cìs-margaidh); Clàr nan Suaicheantas copied from the Residency's book
of arms, lions, parrots and crocodiles on shires that never saw one, the western Seann Skell's scorpion; Coinneach mac
Ailein holding court under the market roof at Baile Mòr mhòr. Then 3 an t-Ògmhios: the Great Wave on the southern
coast. Ailean carries the relief party's tally-book to Cuan dhearg: the smell, the broken piles, the boats in the
barley, one upright in a furrow with her mast stepped. He counts through the summer; on 24 an t-Samhain the dead of
three towns come to a little over forty; Ros gharbh's fleet on the headland. His figures carry the council to its
first relief: Achadh mhin's survivors moved and their seed paid; Cnoc chaol rebuilt on the hill; an Tràigh Bhàthte;
*tonn* heard in the survivors' mouths; Eilean mhin's shepherds do not go back. Turn: a count that made the state act.
Ends with *Tha e san tonn*.
*New:* the first maor's seal cut from the roll (SE 4); the relief party out of Cathair dhearg (SE 4); the Cuan dhearg
dead buried on the hill (SE 4); the boats left standing in the fields till harvest (SE 4); the treasury's first
relief roll (SE 4); Ros gharbh's boats rebuilt (SE 5).

### PART TWO: OF COIN, RITE AND MOUNTAIN (SE 5 – 13)

**7. Of the Coin with the Coal in its Seal** · Walter Hale · SE 5 an Giblean – SE 6 am Màrt · V-0023 – V-0027 · 5,000 w.
The humans' coin cried down; in the north the savings box under every bed becomes metal. A recollection section at
the mint in the old counting-house: Fearchar Bonn grinding coal dust for the seal ink. Hale writes the Moot's petition
for an exchange; Ailean, far south, receives and files it (one line). In an Gearran SE 6 Hale walks to Doire mhin to
Joseph Marlow's forge, where dead coin goes into the pot and comes out as ploughshares sold back for the price of the
charcoal; Marlow's boy Harry is off to a shipwright at Cuan shean. At Inis thais the merchants trade on the house of
the Stone's chits (recollection). Turn: Hale understands "received and filed" will be the answer to everything and
that the north must make its own. Ends with the first furrow cut by a coin-iron share.
*New:* first coins of the Rìoghachd struck (SE 5); the Moot's tally of northern savings voided (SE 5); Harry Marlow
bound apprentice at Cuan shean (SE 6); Joseph Marlow's song first sung at Doire mhin (SE 6).

**8. Of the Order of Worship** · Dòmhnall mac Thormoid · SE 6 an Giblean – SE 7 an Gearran · V-0028 – V-0033 · 5,000 w.
Òrd Bhrìde given doctrine: the leyline and the unbroken line of the coal-touched. Dòmhnall, old, named Àrd-choimheadaiche
and seated at Seann Skell on the southern coast, must write an order of worship where none was ever written; he
writes a doctrine about a line of people he has never met (no coal-touched person appears). The Hawk houses about
Cnoc bheag refuse; Muileann naomh takes the order and hangs the first bell in a hawk-house; the Stone sends a letter
wishing it well; Òrd Mhacha keeps the regalia and refuses him a share. A short section at Caol mhòr: Hale's
schoolhouse petition and "clear, at least". Turn: the first reading of the written order. Ends on one house
disowning, one ignoring with courtesy, one outranking.
*New:* the order first read at the southern Seann Skell (SE 6); the Hawk houses' letter of refusal (SE 6); Muileann
naomh's bell first rung at a measured burning (SE 6); copies of the order sent to every house of the Rite (SE 7).

**9. Of the Justice's Circuit** · Eilidh nic Leòid · SE 7 an t-Ògmhios – SE 8 an t-Sultain · V-0034 – V-0038 · 5,000 w.
The first census: few coal-touched, noted and no more; the census of faiths (*gun chreideamh* on the far north-western
cape and the empty islets); Doire ghlas counted from the road, the Moot's tally a fifth higher. Eilidh of Cathair
dhomhain, unmarried, raised on custody-book law, named first circuit justice: eleven shires of the south-west, most of
a year in the saddle. The head-due first gathered. At Muileann bhàn she hears a quarrel over the waterworks' lead
pipes. At Seann Bhral in the west, 10 an t-Sultain SE 8, the first Tuathaich land suit: she reasons strictly and rules
that land under human title passes to the Crown and the right to work it stays with the holders, and believes it
generous. Turn: the ruling written. Ends with it copied to every maor's court.
*New:* Eilidh's first assize at Cathair dhomhain (SE 7); her circuit at Inis thais and Doire shean (SE 7); the pipes
case at Muileann bhàn (SE 8); the ruling copied to the maoir (SE 8).

**10. Of the Vigil in the Open** · Hannah Crane · SE 8 an Dàmhair – SE 9 an Giblean · V-0039 – V-0044a · 5,000 w.
Opening recollection: the coal line mended to Muileann chrom and a Rail Board of a clerk, two engineers and the
humans' timetable; the capital's bridge hallowed anew, the humans' stone turned to face the river; Tuam Cnoc dhìreach
closed to new graves. Then Baile chrom: the Church kept in the north, the First Canoe fragment kept (never shown; say
nothing of where). Hannah, vigil-keeper of the Grey Night, decides to keep the vigil in the open on the headland for
the first time since the Severance, 14 am Màrt SE 9; the maor's man watches and does nothing; the bishops write
"irregular". The church at Cnoc ghorm built and the Ros bheag bell hung in it; Muileann fhionn's cattle market. Turn:
silence kept where it can be seen. Ends with the geese going north. (Never tell which night the vigil is.)
*New:* the Rail Board's timetable posted at Muileann chrom (SE 8); the bishops' letter on the vigil (SE 9); the Ros
bheag bell hung at Cnoc ghorm (SE 9); the first drove from Muileann fhionn south (SE 9).

**11. Of the Wall that was Not Built** · Gormshuil nic Dhùghaill · SE 10 an Giblean – SE 11 an t-Samhain ·
V-0045 – V-0052 · 5,000 w.
The Cnoc ghorm church school reported to council. Seumas mac Coinnich Ghlais proposes a boundary wall; the debate;
Gormshuil takes the minute that refuses it as needless, four lines, the fourth *They do not come south*; five initial,
seven do not sign against; she copies it into a private book, her first. With her mother, of an Old Spirits house, she
walks to Allt an Àigh; the walkers' hall at Achadh gharbh. The mine back to its old yield; the Sloc Mòr granted to
Uisdean mac Ùisdein on the humans' terms, the Crown's fifth; the Mine Board seated at Cathair dhearg; the night shift
kept; the custodians protest and then bless the shafts. Turn: the fourth line. Ends on the blessing.
*New:* Gormshuil's private copy-book begun (SE 10); the Mine Board seated at Cathair dhearg (SE 11); Uisdean mac
Ùisdein's first contract with the hewers (SE 11); the custodians' protest entered (SE 11).

**12. Of the Sloc Mòr** · Iain mac Ruairidh · SE 12 am Màrt – SE 13 an t-Samhain · V-0053 – V-0060 · 5,000 w.
Iain, nineteen, a hewer's son of the hills, taken on as chainman by Lachlann mac Iain Bhàin, the Board's surveyor:
lamp, chain, the colours in the broken face that the godkin see. Families from the hungry east pour into the
vein-towns; Muileann dhearg doubles and its shut druid hall becomes a hewers' lodging; Baile thais grows inns and a
ropewalk on the coal road; raiders off Cathair gheal (recollection, one paragraph). 3 an Dàmhair SE 12: the first
coal train from the Sloc Mòr to the capital on the humans' rails. The grey spoil-stone cut under the Mac Ùisdein
mark; the Muileann chrom sidings and the yard families counted apart; the western branch with its spur to Àth leathan;
the guild custom restored for Dia-thìrich alone; the Guild of Hewers sworn with hands on a lump of coal. Iain, the
Board's man, is not sworn. Turn: standing outside the oath. Ends on the hewers' saying (*Cha d' fhuair a' bheinn fois
a-riamh*).
*New:* Iain taken on as chainman (SE 12); inns of Baile thais (SE 12); the Rail Board's office built of spoil-stone
(SE 13); Lachlann mac Iain Bhàin's book of the faces begun (SE 13); the spur to Àth leathan opened (SE 13).

### PART THREE: OF GUILDS, LAW AND LIBRARY (SE 14 – 20)

**13. Of the Indentures** · Harry Marlow · SE 14 am Faoilleach – an Dùbhlachd · V-0061 – V-0064 · 4,500 w.
Harry, seventeen, apprentice to Seumas Crùbach at Cuan shean. News of Ros dhomhain binding thirty in a day on the
slipway. 28 am Màrt: the charter rule reaches Cuan shean and Seann Bhral in the west; Seumas tears the indenture and
cannot look at him. Harry stays as day-labour at half the wage, outside the guild. The chandlers of Ceann àrsaidh get
the patrol-boat right; the lamp-makers of Muileann mhin stamp their flame over a hammer. On an old human hull left on
the Cuan shean hard Harry learns the humans' lines by hand. Turn: choosing to stay south, unbound. Ends at the year's
end sending wages north.
*New:* the Tuathaich day-wage set at the Cuan shean yard (SE 14); the lamp-makers' mark first stamped (SE 14); a
Tuathaich boy's plea refused at the Ros dhomhain guild court (SE 14); the Moot's letter on the indentures filed (SE 14).

**14. Of Agnes Pike's School** · Agnes Pike (Daniel Frayne as a child) · SE 15 am Faoilleach – an t-Iuchar ·
V-0065 – V-0067 · 4,500 w.
The weavers of Baile chiar chartered. Agnes, a miller's daughter of the Pikes, opens her school in a byre at Doire
ghlas on 14 am Faoilleach with the Moot's purse (Hale brings it) and no leave: the Bible and the Moot's minutes for
readers. Daniel Frayne, nine, walks in from Muileann leathan and copies letters better than he reads them. The maor
visits, looks, and writes nothing. Alice Hale opens a second school at Caol mhòr. Recollection: the Cill ghlas
district surveyed by Lachlann and Iain and declared safe, new shafts cut back from the old fault. Turn: the maor's
empty report. Ends with Daniel copying the Moot's minute of the school's founding.
*New:* the Moot's school purse voted (SE 15); the maor's visit (SE 15); the school register begun (SE 15); Alice
Hale's school at Caol mhòr (SE 15).

**15. Of the Seventeen Suits** · Eilidh nic Leòid · SE 15 an t-Iuchar – SE 16 an Giblean · V-0068, V-0069 · 6,000 w.
The master scene grown: Ceann mhòr in the heat of an t-Iuchar, windows open, flies, nineteen cases, seventeen
Tuathaich land suits on human titles brown at the folds; she reads each to the end and reads her own ruling aloud.
Hale sits for the suitors with no standing; she lets him speak as a witness. Fifteen for the Crown; two for the
holders, where a custodian's countersign stood on the title. At the inn that night Hale and Eilidh talk: exactness
and the people it was made for. She rides home by Àth leathan and Seann Bhral in the west, and falls ill in the
winter; dies at Cathair dhomhain 2 an Giblean SE 16. Her rulings are bound as Leabhar nam Breith and every justice
carries it. Turn: the conversation; she does not change her rulings and knows what they are. Ends with the book handed
to her successor.
*New:* the two suits found for the holders (SE 15); Hale heard as a witness (SE 15); Uilleam mac Leòid named to the
northern circuit (SE 16).

**16. Of the Cellar at Muileann chaol** · Ailean mac Iain → Ailean Leabhar · SE 16 an Cèitean – SE 17 an Lùnastal ·
V-0070 – V-0075 · 5,500 w.
Bealltainn fires over Muileann chaol; the master cellar scene (rolls soft as bread, three lines by the light of the
stair, lamps, a table, a boy, Coinneach Clàrc). Named first keeper; the council's minute-books and the boxed ledgers
brought east. The long reading; every date turned to the civil calendar; his dislike of the Diosal. On the margin of
the Àth ìseal roll, Cailean mac Eachainn's Line of Aisling: copied fair into Leabhar nan Sloinnidhean after the Line
of the Mason; the long years into Leabhar nan Aithrisean; "Both. The one keeps names. The other keeps what people
said." *A chur san Leabharlann* and "The Library settles nothing." First readers (a Ros dhomhain shipwright asking
for the humans' hull plans); the Guild's bath-house at the warm springs and its sick-roll of four hundred; the five
lights given Dia-thìreach keepers, Baile chrom's keeper bidden to watch the land. Turn: the decision to keep, not to
settle. Ends as the lights are lit.
*New:* the custodians' rolls lifted from the wet cellar (SE 16); Leabhar nan Sloinnidhean and Leabhar nan Aithrisean
opened (SE 16); the Library's civil-calendar table (SE 17).

**17. Of the Table of the Ages** · Gormshuil nic Dhùghaill · SE 17 an Dàmhair – SE 19 an Cèitean · V-0076 – V-0081 ·
5,000 w.
Copyists, binders and paper-makers settle round the Library; its yard is the market; the Tobar dhìreach mill.
Ailean's reckoners, laying Clann na Ceiste's tellings against the king-lists, part the eldest age and count the Age of
Ailean apart. 20 an t-Samhain SE 18: the office of royal chronicler made and the years counted by the ages, "six ages
as the table then stands". Gormshuil named; she will not keep the record at the capital ("a record kept beside the
throne is kept for the throne"); she heads her first year the eighteenth of the Severance Era. The first chronicle
circuit, with young Tormod mac Sheumais among the clerks: forty chests from the south, one from the north; the town
arms copied, five hundred and five; the parish book of Inis bheag copied and not taken. Turn: leaving the capital.
Ends as the northern chest is opened and holds only the maoir's returns.
*New:* the table of the ages drawn, the Age of Ailean counted apart (SE 17); the first Tobar dhìreach paper at the
Library (SE 18); the clerks turned away at Doire ghlas (SE 19).

**18. Of the Raiders' Bay** · Nell Barrow (with Mary Coyle, Walter Hale) · SE 19 an t-Sultain – SE 20 an Lùnastal ·
V-0082 – V-0086 · 5,000 w.
A westerly storm drowns eleven Tuathaich fishermen off Cuan bheag, Thomas Coyle among them; Mary Coyle widowed; the
Moot's lifeboat by subscription, the council pays a third. Fishermen of Achadh àrsaidh tell of the thing off the
north-western cape; Gormshuil writes it down and notes the raiders shelter there. The Eilean dhubh flocks counted by
the islanders. Nell Barrow, skipper's widow at Cathair gheal, sends the town's two requests for help; none comes;
8 an Giblean SE 20 she leads the armed boats that drive the raiders from the bay. The council fines the town; Hale
brings the Moot's purse; the town pays. Far south, the Mac Ùisdein cross at Cathair mhòr. Turn: the fine. Ends with
the fine paid at the maor's door.
*New:* the Moot's lifeboat subscription (SE 19); the Cuan bheag lifeboat launched (SE 20); Cathair gheal's two
requests (SE 20); the fine paid (SE 20).

### PART FOUR: OF FAIR, CROWN AND SURVEY (SE 21 – 34)

**19. Of the Fair at Muileann òg** · Oighrig nic Mhathain · SE 21 an Cèitean – SE 22 an Lùnastal · V-0087 – V-0091 ·
5,000 w.
Opening recollection: the Stone's house at Caol leathan rebuilt with a bell tower that sets the town's hours.
Oighrig, a market clerk of Dùn chrom, made first toll-mistress. The first fair on 16 an Dàmhair SE 21: every province
the state holds. Her rules: stall-fee in coin, a court of the fair, and, on the council's word, Tuathaich goods only
through Dia-thìreach factors; she writes that rule in her own words, then turns away David Hale's wool to a factor.
The fair road metalled past Dùn chrom; the gate-toll builds the fair's wall. Turn: writing the factor rule and
knowing what it does. Ends as the rules are read aloud.
*New:* the court of the fair's first sitting (SE 21); the first factors licensed for northern goods (SE 21); the
Moot's letter against the factor rule filed (SE 22).

**20. Of the Way Niall Came** · Gormshuil nic Dhùghaill · SE 22 an Lùnastal – SE 23 an Lùnastal · V-0092 – V-0098 ·
5,000 w.
Niall dies; Brìghde is crowned without contest (only the facts: the rite, the crowd, the bells; no word of either
ruler). Gormshuil admits one idiom to the chronicle, *mar a thàinig Niall*, and argues it with herself. The ancestors'
hall at Seann Dunn; Cuan ruadh's own harbour light that the Lighthouse Board will not take on; the first Còmhrag at
Ceann leathan, Calum Ruadh the champion, two dead, a year's wages and the right to bear arms; the inns and the
fair-wardens. Turn: the idiom let in. Ends with Calum Ruadh walking home armed.
*New:* the bells for Niall at Cathair dhearg (SE 22); the Seann Dunn list first copied to the Library (SE 23); the
Lighthouse Board's refusal (SE 23); the dead of the first Còmhrag buried (SE 23).

**21. Of the Sea-Feast Turned Away** · Mary Coyle · SE 24 am Màrt – SE 26 an Gearran · V-0099 – V-0104 · 4,500 w.
Recollection: the Ros gheal grain dock and the Hawk's twentieth; births among the shunting families of Muileann chrom
(Seachran and Brean named, nothing more); Seann Bhral in the south, the greatest fishing port; the circus at Seann
Chwen. Mary, speaking for the widows in the Moot, leads the northern crews to Manannan's feast at Seann Bhral in the
west as their forebears learned; the keeper turns them away ("the sea is the same and the house is not"). In an
Gearran SE 26 they keep Fleadh na Mara at Cnoc ghorm, a blessing of the boats. Turn: turned away, they make their own.
Ends with the boats blessed.
*New:* Mary Coyle first speaks in the Moot (SE 24); the Hawk's twentieth first paid (SE 24); the northern crews sail
for Seann Bhral (SE 25).

**22. Of Iain Mapa's Survey** · Iain mac Ruairidh · SE 26 am Màrt – SE 27 an t-Iuchar · V-0105 – V-0109 · 4,500 w.
Iain, thirty-two, months on the faces of the Sloc Mòr with lamp and chain; the vein thinning east and south and not
arguing. He carries the survey rolled and tied to the Board; three men do not unroll it; "It will be considered." "I
should like a receipt." Ruairidh mac Ailein signs one. Filed; Iain sent to the silver works at Muileann chiar. The
Board moves to Cathair mhòr and makes its rule that surveys stay there. Recollection: the scent-makers of Seann Vell;
the Grey Night forbidden at Baile chrom, Hannah fined, the vigil indoors; Cuan dhearg's harbour reopened with a boat
from the fields, *Bàta an Achaidh*, kept as a relic. Turn: the receipt. Ends with Iain at Muileann chiar pinning it
into his book.
*New:* the receipt given (SE 26); Iain sent east (SE 26); Riaghailt a' Bhùird made (SE 27); Hannah Crane's fine paid
by the Moot (SE 27).

**23. Of the Bare Entry** · Gormshuil nic Dhùghaill · SE 28 am Faoilleach – SE 29 an t-Ògmhios · V-0110 – V-0116 ·
3,800 w.
Achadh mhin bears again. Brìghde dies young, no cause made known; Eòghan crowned amid the first dispute; Gormshuil
writes the bare entry and nothing more, and knows the silence will be read. The council's first votes against a
succession: Tormod mac Iain Òig and Sìleas nic Artair do not sit again. The Inis bhàn fire and its loud bell. Dubhan
born in the north (one sentence, the annal's fact). The Moot's letter: eleven schools, three teaching Dia-thìris at the
parents' asking. Turn: the bare entry. Ends with the schools' letter.
*New:* the two councillors' seats filled (SE 28); Inis bhàn's fire-bell bought (SE 29); Agnes Pike's school begins
Dia-thìris (SE 29).

**24. Of Walls under the Ground** · Ailean Leabhar · SE 30 an Giblean – SE 32 an Cèitean · V-0117 – V-0124 · 3,500 w.
The Mac Ùisdein stone house and the Guild's feast in it; licences on the southern fishing grounds kept for
Dia-thìreach boats; Doire shean's harbour on the Stone's money. Ailean at the trenches at Làrach an Dùin: walls older
than any, no writing, "of the Old Ones, purpose unknown"; at Làrach an Teampaill the Old Spirits ask him not to dig,
and he measures and lets it be; the obelisk copied stroke by stroke and fenced. The Baile chrom keeper's report of
the vigil in the lighthouse's shadow, and the council doing nothing. The salt-pans of Àth bheag. Mòrag nic Coinnich
now his deputy. Turn: letting the temple be. Ends on the obelisk copy filed.
*New:* the diggers' camp at Làrach an Dùin (SE 31); its finds laid in the Library (SE 31); the first licence refused
to a Caol mhòr boat (SE 30).

**25. Of Walter Hale's Last Winter** · Walter Hale → Mary Coyle · SE 33 am Faoilleach – SE 34 am Màrt ·
V-0125 – V-0130 · 3,800 w.
The Cathair fhada grain-store built. The second census measures the gap, and the report is kept. Hale, old, at Caol
mhòr: his last sittings, David keeping the books; he dies 28 an Gearran SE 33; the whole north walks to his burial;
the Moot chooses Mary Coyle. Seonag nic Ille-Mhoire asks to see the report and is refused, and writes it down. The
Moot pays for Ruth Ashby and Clara Tulloch to learn medicine from Eachann mac Rath at Àth àrsaidh, who is struck from
his guild. The Abhainn ìseal floods; the line shut; the ports on stored coal. Turn: Hale's last minute. Ends with Mary
Coyle's first.
*New:* Hale's burial (SE 33); David Hale keeps the books under Mary Coyle (SE 33); the ports' coal rationed (SE 34).

### PART FIVE: OF THE FALL AND THE SEARCH (SE 35 – 52)

**26. Of the Hawk's Own Custodian** · Raonaid nic Iain · SE 35 an Cèitean – SE 36 an Dùbhlachd · V-0131 – V-0136 ·
5,000 w.
The Hawk houses seat Raonaid at Inis ìseal; the high custodian at the southern Seann Skell will not own her; she
writes the Hawk's spoken order down, reads it once a year and locks the copy away; the white hawk recut on the shire's
seal among its crescents. Recollection: six dead at the Còmhrag, the custodians' petition, the wardens' refusal; the
circus at Ceann leathan; the coal line to Ceann leathan; the Ros bheag yard and the Ros dhomhain shipwrights' lost
protest. Turn: the locked copy. Ends on the recut seal.
*New:* the high custodian's letter refusing Raonaid (SE 35); the gathering at Inis ìseal (SE 35); the first coal-ship
loaded at Ceann leathan (SE 36).

**27. Of the Silver at Depth** · Iain Mapa · SE 37 am Faoilleach – SE 39 an t-Ògmhios · V-0137 – V-0140 · 4,500 w.
The silver seam richer at depth; the old guild chartered anew; Iain measures the new faces and marries Mòr nic
Dhòmhnaill, a refiner's daughter; the blank-houses of the eastern hills and the gold washed below Baile dhìreach. The
two Dùn thais: a sea court in the west that gives a raider's hulk to the fishermen, a covered market in the east, and
the royal record beginning to confuse them. Siorrachd Doire chaol cut out. Recollection: the shepherd lost above
Doire uaine and the magistrate entering wolves. Turn: the silver thriving where the coal fails, and Iain keeping his
copy. Ends at Doire uaine.
*New:* the first blanks to the mint (SE 37); Iain marries (SE 38); the maor of Baile chiar's petition (SE 38).

**28. Of the Fall at Muileann dhearg** · Iain Mapa · SE 39 an t-Iuchar – SE 40 an t-Samhain · V-0141 – V-0147 · 5,500 w.
1 an t-Iuchar SE 39: a gallery under Muileann dhearg gives way on a line marked sound; thirty-one dead. Iain rides
from Muileann chiar and goes down; it is the Rending's fault. The rules of the shafts made for Dia-thìrich; at Àth
leathan the timber ordered and never delivered (recollection, no "later"). He writes a letter naming the fault and his
old survey, and does not send it. 3 an t-Sultain SE 40: Ailean Leabhar dies; Mòrag keeper, writing beside each item
where it came from. Forty families leave Achadh dhomhain; sixty apprentices bound, none Tuathaich; the fire at the
fair on Samhain eve, the court in a field, Oighrig dead of her burns; the Rail Board refuses the Moot's goods. Turn: the
unsent letter. Ends with the northern wool loading onto carts.
*New:* the dead of the fall buried (SE 39); the Moot's letter on the western pits filed (SE 39); Ailean Leabhar
buried at Muileann chaol (SE 40).

**29. Of the Carters' Road** · Daniel Frayne · SE 41 am Faoilleach – SE 42 an t-Iuchar · V-0148 – V-0152 · 4,500 w.
Frayne, thirty-five, a Moot clerk, rides with the wool carts by Cnoc ghorm, Àth fhada and the old road to Inis àrsaidh,
five days, the villages opening inns; the name the north gives the road. One paragraph of recollection: a boy in the
north watching the caste that does not age (V-0149 only). In an Dùbhlachd SE 41 the Moot's register of the western
pits' dead and maimed, Clàr nan Leòn; Frayne writes the first names on the families' word. At Ros mhòr the turned-out
boatbuilders open a yard; Harry Marlow, grey now, lays its first keel to the humans' lines. Gormshuil lays down the
chronicle; Tormod Pinn. Turn: the first name in the register. Ends with the first Ros mhòr hull afloat.
*New:* the first inn on the Carters' Road at Àth fhada (SE 41); the first Ros mhòr hull launched (SE 42); Gormshuil's
last entry written (SE 42).

**30. Of the Unlit Ships** · Murchadh mac Coinnich · SE 43 an Giblean – SE 45 an Dùbhlachd · V-0153 – V-0160 ·
4,500 w.
Recollection: Tormod copies Gormshuil's list of what the record lacks; the dry years at Achadh shean and the grain up
the coal line from Cathair fhada's store (its first opening), no one dies; twelve wells. Murchadh, young keeper of
Taigh-solais Baile ìseal, watches raiders land and burn the salt-sheds of Àth bheag; the patrol boats two days late;
he starts logging every unlit ship, heading and hour; the fishermen's names for them, *An Ròn Dubh* and *An
Fhaoileag*, pass into the record. At Ceann leathan Ealasaid nic Coinnich of Àth ghlas wins the Còmhrag and does not
fight again. Turn: the first entry. Ends on his first full year's log.
*New:* the salt-sheds rebuilt (SE 44); the patrol boats' report (SE 44); *An Ròn Dubh* sighted off Baile ìseal
(SE 45).

**31. Of the Sacred Wood** · Seonaid nic Ghill-Eathain · SE 46 an Dàmhair – SE 49 an Gearran · V-0161 – V-0171 ·
4,500 w.
Cnoc bheag passes Cathair mhòr. The druid schools of Flidais wake; Seonaid lectures in the sacred wood near Muileann
chiar on the oldest question, why the vein answers some hands; the Baile gharbh houses walk to hear her; wet months at
Caol shean, students copying the census line on the coal-touched and disputing it openly; the Muileann dhearg hall
given back to the school. The Hawk given a place under the Rite. A section with Frayne's copying school at Muileann
leathan. The breakwater at Caol chrom begun; Cidhe Beag ferry; Loch chrom trout. The pillar at Cnoc chiar set beside
the obelisk and the column: signs in common, no meaning; "the Old Ones were here and said so". Turn: the question put
plainly in the open. Ends on that sentence.
*New:* the Muileann dhearg hall returned to the school (SE 47); Tormod Pinn marks the two Dùn thais west and east
(SE 48); the breakwater's first stone (SE 48); Frayne's first bindings sold south without his name (SE 48).

### PART SIX: OF THE ONE SHEET AND THE EMPTY FLOOR (SE 50 – 71)

**32. Of the Forty-One Shafts** · Catrìona nic Neacail · SE 50 am Màrt – SE 52 an Lùnastal · V-0172 – V-0180 · 5,000 w.
Recollection: Inis chrom's lofts rebuilt on piles; Cnoc leathan's six schools. Alasdair mac Ùisdein borrows against
his house's share; the Board lends surveyors, Catrìona, thirty-two, among them. Seonaid's letter that the search asks
the wrong question, filed. Forty-one shafts from the hills above Dùn dhearg to the moors south of Baile ruadh; none
strikes. Mòrag finds a Holy Age list naming the same hills searched and barren. Dùn dhearg's claim; the house pays a
third and sells half its share; the stone house let to the Board. The open shafts at Baile ruadh; sheep, one child;
the shire fences them. Turn: the last dry shaft and Mòrag's list arriving the same week. Ends on the fence.
*New:* Catrìona lent to the search (SE 50); the first shaft above Dùn dhearg (SE 51); the last shaft at Baile ruadh
abandoned (SE 51).

**33. Of the Reef Bell** · Ciorstaidh nic Artair · SE 53 an Giblean – SE 55 an t-Ògmhios · V-0181 – V-0189 · 5,000 w.
Recollection: Muileann dhomhain's mills turn to bark; the rope-makers of Seann Tarr and the shire's chest that sends
only its list; the circus at Inis àrsaidh; Ceann mhin's fish-market; edged tools banned from the Còmhrag. At Tobar
dhearg her father Artair drowns going out to a boat on the reef; she goes out after him and brings the crew in; the
warrant is hers; the iron post and bell on the reef, and no boat aground. Mary Coyle lays down the chair; Daniel
Frayne, first speaker born after the Severance. Turn: going out. Ends with the bell in fog.
*New:* Artair buried at Tobar dhearg (SE 54); the reef bell first rung in fog (SE 55).

**34. Of the One Sheet** · Catrìona nic Neacail · SE 55 an Dùbhlachd – SE 57 an t-Iuchar · V-0190 – V-0197 · 5,500 w.
The fair's northern day; the Doire ghlas grey twill with *An Snàthainn Geal* at the selvedge, copied by Baile chiar.
Catrìona, surveyor-general, draws the last unworked stretches: one sheet. She publishes it; to learn how long, she
spends a week in the Board's files at Cathair mhòr by a smoking lamp and finds a rolled, tied survey thirty years old
in a hand she does not know. She sends the Library a copy with the day the Board received it, rides to Muileann chiar
and sits with Iain Mapa in his last spring; he shows her his receipt. He dies; his copy is found with the receipt
pinned to it. She resigns and goes to teach at Caol shean. Muileann dhearg loses a third; its hall shut, its bell sold
to Caol shean; coal-ships wait half-loaded at Ceann leathan. Turn: the survey in the press. Ends with the Muileann
dhearg bell ringing her first lecture.
*New:* Catrìona named surveyor-general (SE 56); her visit to Muileann chiar (SE 57); Iain Mapa's widow sends his
papers to the Library (SE 57); Catrìona's first lecture at Caol shean (SE 57).

**35. Of the Crown Alone** · Daniel Frayne · SE 58 an t-Sultain – SE 60 an Lùnastal · V-0198 – V-0205 · 3,800 w.
Baile Mòr dhomhain's market outdraws the fair. Mairead crowned (the fact only). The Hewers bind none; Muileann shean
teaches hewers' children to survey. The Doire ghlas mills on Moot money; the Rail Board refuses the cloth; Frayne
brings the suit, and Ruairidh mac Phàdraig at Seann Bhral in the west rules the Board a carrier of the Crown; the
council lets the appeal lapse. The Crown buys the last Mac Ùisdein shafts; copper at Àth fhiadhaich, unblessed. Turn:
the first ruling the Moot wins. Ends with the first bale on the coal line.
*New:* the Moot's suit brought (SE 59); the first bolt from the mills (SE 59); the first northern bale by rail (SE 60).

**36. Of the Pumps and the Panthers** · Tormod Pinn · SE 61 an t-Ògmhios – SE 63 an Lùnastal · V-0206 – V-0215 ·
3,800 w.
The copper-town's street named for the Sloc Mòr. Dubhan's first attempts, the annal's sentence only. The Sloc Mòr's
lowest galleries let flood, "a pause"; the pumps sold to the dry dock at Seann Bhral in the south. The panthers across
the south-west near Baile dhomhain, Baile ghorm's hides; Tormod's longest entry, the old list naming the next year a
hungry one. The lamp-makers' shortage and lending-book; the Muileann chrom yard stops the trains three days, settles,
dismisses eleven. The harvest comes in good and Tormod strikes through his own note. Turn: the strike-through. Ends on
it.
*New:* the last pump drawn out (SE 61); panther-skins first at the fair (SE 62); the eleven leave Muileann chrom (SE 63).

**37. Of Now Written** · Daniel Frayne · SE 64 an Dàmhair – SE 67 an Lùnastal · V-0216 – V-0227 · 4,200 w.
The third census published openly. 6 an t-Samhain SE 64, Caol mhòr: Frayne's hands flat on the table, the clerk's
flat voice, every column at half; the quiet; *Now written.* The line for the coal-touched, a number only, copied by
Tormod; the Stone's own count within a hundred. Tormod dies at his desk; Beathag chronicler; her first foot-note: the
northern figures were the Moot's (Frayne had given them). The Hawk's birth-rolls filed under the Hawk. Mòrag calls in
the shires' chests; Seann Tarr burns its own; Cathair naomh's two carts; Seann Toll's willing chest; the Library
doubles. The Moot will not send its books. Turn: the two words. Ends on the Moot's minute keeping its books in the
north.
*New:* the Moot's figures given to the census clerks (SE 64); Tormod Pinn buried (SE 65); the Moot's minute declining
to send its books (SE 67).

**38. Of the Empty Floor and the Banked Fire** · Beathag nic Fhionnlaigh · SE 68 an t-Ògmhios – 18 an t-Ògmhios SE 71 ·
V-0228 – V-0237 · 4,500 w.
The new wing of Sloc Mòr stone: three floors of chests and the fourth left empty. The branch to Àth leathan shut; the
Tuathaich hewers work on under their own captains and pay the fifth by the Leòid ruling, entered as arrears; at Cnoc
thais Sam Varley keeps the pit accounts and his small son Tom runs errands. An Sligeanach Fad' às sold to drovers; the
herring fail off Seann Dunn and the east boats push north; Inis mhin's boats go to deep water. Mòrag lays down;
Raghnall keeper. Coal doubles at the fair; the ceiling will not hold; watchmen at Cnoc fhiadhaich see nothing. Last
section, the summer of SE 71, dry and dear: Beathag's foot-note of what the record could not learn; the poorer streets
dark; in the north, as the tellers say, one man banked his fire and slept beside it. Ends on that night, the kingdom
asleep. No word of what the morning brought.
*New:* the Àth leathan hewers' first coal carted to Seann Bhral in the west (SE 69); the fair's ceiling broken (SE 70);
the capital's poorer lamps burned short hours (SE 71); Beathag's foot-note for SE 70 (SE 71).

## 4. Continuity

**Opening state** (the master Fifth Book's close, 1 am Faoilleach AE 151): the crossing is closed; the last ship,
Strake's, stood out north from Cuan shean on 5 an Dùbhlachd AE 150; the five beacons relit and their daybooks say *Cha
tàinig long*; the humans still on Dia-thìr walked north under the council's safe-conduct (counted at Àth chrom, a night
at Àth leathan); the council's companies hold the roads; the custodians' rolls and the Residency letter-books lie in
the cellars at Muileann chaol; the tithe ledgers burned green at Muileann chrom; Cian and Lorccan not yet twenty; the
hill is the island's again, and the island knows no way to use it but the strangers' way.

**Closing state** (the master Seventh Book's opening, the night of 18 an t-Ògmhios SE 71): Mairead reigns; the council
of twelve, maoir, circuit justices; the Board works the vein in the Crown's name alone, the Sloc Mòr's lowest galleries
flooded; the Guild of Hewers binds none; coal dear at the fair, sold ever smaller; the poorer streets of the capital
dark; Beathag nic Fhionnlaigh chronicler at Muileann chaol, Raghnall mac Mhuirich keeper, the fourth floor empty; Daniel
Frayne speaker of the Moot at Caol mhòr; Ciorstaidh nic Artair keeper at Tobar dhearg; the high custodian at the
southern Seann Skell; the house of Mac Ùisdein with its share in the spoil and the quarry; the Tuathaich working the
western pits under their own captains; the coin's seal still pressed with coal ink; in the north Dubhan at his work
unwatched.

**Threads** (THREADS.json ids; tag every event that moves one):

| Thread | Advances in chapters |
|---|---|
| the-tuathaich | 1, 2, 4, 6(maoir), 7, 9, 10, 13, 14, 15, 18, 19, 21, 23, 25, 28, 29, 33, 34, 35, 37, 38 |
| the-library | 16, 17, 20, 23, 24, 28, 30, 32, 34, 37, 38 |
| the-orders-of-the-old-faith | 8, 11, 20, 26, 31 |
| the-church-on-the-island | 1, 10, 14, 21, 22 |
| the-coal-blood | 8 (doctrine), 9 (census line), 31 (schools' question), 37 (census line) |
| the-seven-coals (the vein's failing) | 11, 12, 22, 28, 32, 34, 36, 38 |
| the-mist | 5 |
| line-of-the-mason, line-of-aisling | 16 (copied into Leabhar nan Sloinnidhean) |
| the-stone-kings | 17 (the Age of Ailean counted apart) |
| the-company | 1, 3, 11 (its terms kept) |

Proposed new thread for the lead: **the-depletion**, dt *An Traoghadh* (in NAMES.json), gloss "the Depletion", "The
thinning of the vein, from the first quiet note of the survey to the one sheet and after." Chapters 22, 28, 32, 34,
36, 38.

## 5. Cast

`PLAN_people.json` lists every named person the plan uses (master-annals people marked `master`, the owner's
characters marked `owner`, new people marked `new`). Years: AE for births before the Severance Era (AE 1 = the
continuous count's 1780), SE after; `died: null` means living at the close of the age. The lead enters new people in
PEOPLE.json; writers use no named person not in that file without asking. New proper nouns are in `PLAN_names.json`
(all pass normalize() and check_agreement()).

## 6. Writers

Chapters are written one per writer (CHAPTER_BRIEF.md): each writes `book/NN_<slug>.md` and `events/NN.json`. The
foreman compiles the events into annals files by the blocks below: block Wnn's events go into `annals/age_VI_nn.json`
with its span and id range (N = ceil(nn/2); odd nn uses EVI-N000–N499, even nn EVI-N500–N999). The hand-off states
are the joins between blocks; chapter writers also read the synopses on either side of their own.

| W | Chapters (Book title) | Span | Ids | Opening hand-off | Closing hand-off |
|---|---|---|---|---|---|
| W01 | 1–3 *Of the Winter of the Severance, and the Keys* | V-0001 → V-0008 | EVI-1000–1499 | §4 opening state | SE 2 an t-Iuchar: kingdom proclaimed; surveys boxed at the council; north's hungry year over, day-book begun; Hale known as the reader; Ailean an under-clerk in all but oath |
| W02 | 4–6 *Of the Moot, the Crown and the Great Wave* | V-0008 → V-0023 | EVI-1500–1999 | W01's close | SE 5 an Giblean: Moot and council seated; Niall reigns; shires, maoir, dues, roll of arms; Great Wave counted and relieved; *An Sireadh* home empty; human coin still current |
| W03 | 7–9 *Of the Coin, the Rite and the Circuit* | V-0023 → V-0039 | EVI-2000–2499 | W02's close | SE 8 an t-Sultain: realm-coin current, north's savings void; Marlow's song; Rite with doctrine and high custodian, Hawk refusing; census taken; Leòid ruling given, Eilidh alive; Harry apprenticed |
| W04 | 10–12 *Of the Vigil, the Wall and the Sloc Mòr* | V-0039 → V-0061 | EVI-2500–2999 | W03's close | SE 13 an t-Samhain: coal line to the Sloc Mòr and west to Seann Bhral with the Àth leathan spur; Mac Ùisdein's concession, Board at Cathair dhearg, night shift; Guild of Hewers chartered; vigil open; Cnoc ghorm church and school; wall refused; Iain chainman |
| W05 | 13–15 *Of the Indentures, the School and the Seventeen Suits* | V-0061 → V-0070 | EVI-3000–3499 | W04's close | SE 16 an Giblean: guilds closed to Tuathaich, Harry day-labour; Agnes Pike's and Alice Hale's schools; Cill ghlas reopened; Eilidh dead, Leabhar nam Breith carried |
| W06 | 16–18 *Of the Cellar, the Table and the Raiders' Bay* | V-0070 → V-0087 | EVI-3500–3999 | W05's close | SE 20 an Lùnastal: Library and its books; chronicler at Muileann chaol, years by the six ages; forty chests and one; Mary Coyle widowed; Cathair gheal fined; Mac Ùisdein cross |
| W07 | 19–21 *Of the Fair, the Way Niall Came and the Sea-Feast* | V-0087 → V-0105 | EVI-4000–4499 | W06's close | SE 26 an Gearran: the fair and its factor rule; Brìghde reigns; Còmhrag yearly; Fleadh na Mara at Cnoc ghorm; Mary Coyle a voice in the Moot |
| W08 | 22–25 *Of the Survey Filed, the Bare Entry and Hale's Last Winter* | V-0105 → V-0131 | EVI-4500–4999 | W07's close | SE 34 am Màrt: Iain at Muileann chiar with his receipt; Board's rule; Eòghan reigns; Dubhan born; Library digs; Hale dead, Mary Coyle speaker; second census secret; line shut by flood |
| W09 | 26–28 *Of the Hawk's Custodian, the Silver and the Fall* | V-0131 → V-0148 | EVI-5000–5499 | W08's close | SE 40 an t-Samhain: Raonaid at Inis ìseal; line to Ceann leathan; Iain married, unsent letter kept; fall and rules; Ailean Leabhar dead, Mòrag keeper; Oighrig dead; Moot's goods refused by rail |
| W10 | 29–31 *Of the Carters' Road, the Unlit Ships and the Sacred Wood* | V-0148 → V-0172 | EVI-5500–5999 | W09's close | SE 49 an Gearran: Carters' Road; Clàr nan Leòn; Ros mhòr yard; Tormod Pinn chronicler; Murchadh's log; druid schools open, Seonaid lecturing; Frayne's bindery; Hawk given a place |
| W11 | 32–34 *Of the Forty-One Shafts, the Reef Bell and the One Sheet* | V-0172 → V-0198 | EVI-6000–6499 | W10's close | SE 57 an t-Iuchar: search failed, Mac Ùisdein half sold; Ciorstaidh at Tobar dhearg; Frayne speaker; Depletion laid bare; Iain Mapa dead; Catrìona at Caol shean; Muileann dhearg emptying; Eòghan still reigning |
| W12 | 35–38 *Of the Crown Alone, Now Written and the Empty Floor* | V-0198 → end | EVI-6500–6999 | W11's close | §4 closing state |

## 7. Back matter

**Chronicle.** 253 master + about 360 era entries (~30 per writer) ≈ 610 entries, ~35k words. Bodies one to four
sentences in the Tale-of-Years voice; every event with category, links (lineages, the petition and its filing, the
survey and its finding, the ruling and the rulings that cite it), threads, people, `told_in`.

**Gazetteer** (74 towns, ~160 words each, as they stood in this age; master towns keep their master founding):

| W | Burgs |
|---|---|
| W01 | 19 Cathair dhearg, 95 Caol mhòr, 209 Doire ghlas, 27 Ros dhomhain, 330 Inis àrsaidh, 489 Seann Skell (west) |
| W02 | 143 Ceann mhòr, 365 Baile Mòr mhòr, 190 Cuan dhearg, 150 Achadh mhin, 364 Cnoc chaol, 282 Cuan shean |
| W03 | 5 Doire mhin, 166 Inis thais, 431 Seann Skell (south), 20 Cnoc bheag, 326 Muileann naomh, 26 Cathair dhomhain, 47 Seann Bhral (west) |
| W04 | 305 Baile chrom, 142 Cnoc ghorm, 160 Muileann fhionn, 279 Achadh gharbh, 135 Achadh dhomhain, 491 Muileann dhearg, 354 Muileann chrom |
| W05 | 88 Ceann àrsaidh, 137 Muileann mhin, 106 Baile chiar, 234 Muileann leathan, 44 Baile thais, 204 Baile Mòr fhionn |
| W06 | 246 Muileann chaol, 276 Tobar dhìreach, 62 Inis bheag, 38 Cuan bheag, 476 Cathair gheal, 23 Cathair mhòr |
| W07 | 1 Caol leathan, 255 Dùn chrom, 18 Seann Dunn, 119 Cuan ruadh, 22 Ceann leathan, 24 Ros gheal, 110 Seann Bhral (south) |
| W08 | 29 Seann Vell, 371 Inis bhàn, 324 Doire shean, 492 Àth bheag, 297 Cathair fhada, 304 Àth àrsaidh |
| W09 | 25 Inis ìseal, 63 Ros bheag, 8 Dùn thais (west), 77 Dùn thais (east), 346 Àth leathan |
| W10 | 174 Àth fhada, 60 Ros mhòr, 411 Achadh shean, 131 Baile gharbh, 197 Caol shean, 133 Caol chrom |
| W11 | 92 Inis chrom, 167 Cnoc leathan, 422 Dùn dhearg, 241 Baile ruadh, 202 Muileann dhomhain, 34 Seann Tarr, 30 Ceann mhin |
| W12 | 273 Baile Mòr dhomhain, 212 Muileann shean, 12 Àth fhiadhaich, 170 Baile ghorm, 192 Cathair naomh, 37 Seann Toll, 269 Cnoc thais, 9 Inis mhin, 280 Cnoc fhiadhaich |

**Appendices** (five, ~3,000 words each, all as at SE 71):

| File | Writer | Contents |
|---|---|---|
| `A_rulers_offices.md` *The Crown and its Offices* | W12 | the restored line (only what the chronicle says: Niall, Brìghde, Eòghan, Mairead, with {{year:}}s); the council of twelve and the named councillors; keepers of the Library; royal chroniclers; high custodians; circuit justices; surveyors-general; speakers of the Moot; the house of Mac Ùisdein, the Hales and the Pikes in this age |
| `B_faiths_orders.md` *The Faiths and Orders* | W03 | the Rite's doctrine and written order; the Hawk (refusal, Raonaid, the place of SE 47); the Stone; Macha and the regalia; Manannan and the western feasts; the Old Spirits (Allt an Àigh, Seann Dunn, Làrach an Teampaill); the druid schools' revival; the Tuathaich Church, Cnoc ghorm, Fleadh na Mara; the Grey Night; the census of faiths |
| `C_shires_dues_arms.md` *The Shires, the Dues and the Arms* | W02 | the drawing on the humans' lines; the 123 shires grouped by region, with the island shires, Doire chaol and the windy coast outside; maoir; cìs-cinn and cìs-margaidh; Clàr nan Suaicheantas and the town arms; the circuits |
| `D_reckoning_record.md` *The Reckoning and the Record* | W06 | the Diosal given up; the table of the ages, the Age of Ailean counted apart, "six ages"; the civil calendar; the Library's books (lines, tellings, provenance notes); the royal chronicle and its foot-notes; the censuses of SE 7, 33, 64; the Moot's minutes and registers that stayed north |
| `E_vein_boards_trade.md` *The Vein, the Boards and the Trades* | W11 | the Sloc Mòr (concession, fifth, night shift, flooding, sale); the Mine and Rail Boards; the coal line and its branches; the guilds and their marks; the fair and its rules; the coin; silver, copper, salt, scent, cloth; the Depletion's measures (the surveys of SE 26 and SE 56, one sheet, the forty-one shafts) |
