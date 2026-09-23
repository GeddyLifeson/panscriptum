# Continuity log: the annals of Rodos, Ages I–V

Continuity pass over annals/age_I.json … age_V.json, checked against BRIEF.md, PLACE_FACTS.txt and canon_by_age.json.

**97 events changed, 109 individual edits.** No canon event was changed (title, body, place and canon_date all match canon_by_age.json). All ids, their order, every `kind` and every `between` window are the same as before; no window had to move. No new facts were added about the owner's characters. All five files still parse as JSON and keep their original formatting (indent 1, UTF-8).

## Renames

Each rename applies **only in the age given**. The same old name stays correct wherever else it appears (for example, Ailean Mòr is still the first Stone King in Age I). renames.json holds the same mapping. Each key is `"old name [Age N]"`, so a correction script has to strip the bracket and limit the replacement to book/age_N.md.

| Old name (scope) | New name | Kept by the earlier or greater bearer |
|---|---|---|
| Ailean mac Ìomhair [Age II] | Goraidh mac Ìomhair | (patronymic of the rìgh; goes with the byname below) |
| Ailean Mòr [Age II] | Goraidh Mòr | Ailean Mòr, first Stone King (I-0081) |
| Mòrag nic Ailein [Age II] | Mòrag nic Ghoraidh | Mòrag nic Ailein, queen (III-0213); she is now the only one |
| Fearchar Òg [Age III] | Fearchar Donn | Fearchar Òg, rìgh of Dùn dhearg (II-0118) |
| Catrìona Mhòr [Age III] | Catrìona Bhuadhach | Catrìona Mhòr, twelfth Stone King (I-0243) |
| Beathag Ruadh [Age III] | Beathag Fhionn | Beathag Ruadh of the Red Hill (I-0083) |
| Iain Dubh [Age III] | Iain Ciar | Iain Dubh, sixth Stone King (I-0104) |
| Clann Dhòmhnaill [Age III] | Clann Mhuirich | (house restored: Sliochd Mhuirich of II-0020/II-0046) |
| Clann Lachlainn [Age III, walls of Dùn dhearg only] | Clann Ìomhair | (Dùn dhearg is the seat of the house of Ìomhar; Clann Lachlainn stays one of the seven houses) |
| Ailean Clachair [Age IV] | Torcall Clachair | Ailean Clachair, first bridge-mason (II-0033) |
| Beathag Ruadh [Age IV] | Beathag Dhubh | Beathag Ruadh of the Red Hill (I-0083) |
| Coinneach Bàn [Age IV] | Coinneach Glas | Coinneach Bàn, ruler at Cathair dhearg (II-0213) |
| Sìleas nic Choinnich [Age IV] | Ùna nic Choinnich | Sìleas nic Coinnich, founder of the stag's school (II-0022) |
| Eilidh nic Iain [Age IV] | Eilidh nic Ruairidh | Eilidh nic Iain, Eilidh Dhubh of Doire chiar (III-0094) |
| Tormod mac Iain [Age IV] | Tormod mac Pheadair | Tormod mac Iain, Tormod Scrìobhaiche (II-0109) |
| Tormod mac Ailein [Age V] | Tormod mac Sheumais | Tormod mac Ailein, high custodian (IV-0005) |
| Tormod mac Coinnich [Age V] | Tormod mac Dhonnchaidh | Tormod mac Coinnich, reeve of Àth shean (III-0019) |

Bare-name follow-ons were handled too: "Ailean claims nothing" became "Goraidh claims nothing" (II-0077), and "Ailean's cairns" became "Torcall's cairns" (IV-0027).

## Changes, event by event


### Age I

| id | what | why |
|---|---|---|
| I-0243 | "the last whose name the oral list gives for this age" -> "the last name the oral list gives" | The Stone Kings' list must end before the Binding at Dùn ìseal: Age II has no Stone Kings and the canon Binding comes 'before anything like a king'. |
| I-0244 | "He is the last name in the Red Hill's oral list for this age; the list goes on after him, but in the next age it is written down and no longer only spoken." -> "He is the last name in the Red Hill's oral list; the list stops with him, and in the next age what the reciters kept of it is written down and no longer only spoken." | Age II has no Red Hill rulers (Cathair dhearg is a fishing town there, and the written king-list starts with the Dùn dhearg rìgh), so the list cannot run on. |
| I-0247 | "The keepers number twelve" -> "The keepers number nine" | Hand-off of the keepers: Age I ends with the keepers of the slab by lot, Age II opens with nine hearths keeping the flame. Twelve changed to nine so the keepers' districts become the nine hearths. |
| I-0247 | "twelve at a time, one drawn by lot for each of twelve districts" -> "nine at a time, one drawn by lot for each of nine districts" | Hand-off of the keepers: Age I ends with the keepers of the slab by lot, Age II opens with nine hearths keeping the flame. Twelve changed to nine so the keepers' districts become the nine hearths. |
| I-0255 | "The twelve keepers of the slab" -> "The nine keepers of the slab" | Hand-off of the keepers: Age I ends with the keepers of the slab by lot, Age II opens with nine hearths keeping the flame. Twelve changed to nine so the keepers' districts become the nine hearths. |
| I-0256 | "the keepers are twelve" -> "the keepers are nine" | Hand-off of the keepers: Age I ends with the keepers of the slab by lot, Age II opens with nine hearths keeping the flame. Twelve changed to nine so the keepers' districts become the nine hearths. |

### Age II

| id | what | why |
|---|---|---|
| II-0002 | "the households who swore the Binding choose" -> "the keepers of the slab and the households who swore the Binding choose" | Hand-off: the Age I keepers of the slab (I-0151 to I-0256) take part in the Binding instead of vanishing. |
| II-0003 | "Nine households round the mountain's foot take" -> "Nine households round the mountain's foot, one for each district of the old keepers of the slab, take" | Hand-off of the keepers: Age I ends with the keepers of the slab by lot, Age II opens with nine hearths keeping the flame. Twelve changed to nine so the keepers' districts become the nine hearths. |
| II-0026 | "has a cup cut from grey stone that holds exactly" -> "has the old keepers' stone cup re-cut in grey stone to hold exactly" | The stone cup is invented by Oighrig nic Dhòmhnaill in Age I (I-0153); Fionnlagh Dall's is now a re-cutting. |
| II-0052 | "The first fire at Baile chrom" -> "The fire at Baile chrom relit" | The Baile chrom beacon is first lit in Age I (I-0041). |
| II-0052 | "build a beacon on the point after the loss" -> "relight the old beacon on the point after the loss" | The Baile chrom beacon is first lit in Age I (I-0041). |
| II-0052 | "It is the ancestor of Taigh-solais Baile chrom and the first sea-light in the north-west." -> "It is the ancestor of Taigh-solais Baile chrom." | Age I already has sea-lights, this one among them. |
| II-0076 | "A small fishing town grows at the western bridge-foot" -> "The Red Hill's old settlement, shrunk to a small fishing town, grows again at the western bridge-foot" | The site of Cathair dhearg is the Red Hill, settled and ruled in Age I (I-0083, I-0172); it cannot be founded fresh here. |
| II-0077 | rename "Ailean mac Ìomhair" -> "Goraidh mac Ìomhair" | Same name as the first Stone King (I-0081) for a different person; renamed the later rìgh of Dùn dhearg. |
| II-0077 | rename "Ailean claims" -> "Goraidh claims" | Same name as the first Stone King (I-0081) for a different person; renamed the later rìgh of Dùn dhearg. |
| II-0078 | rename "Ailean mac Ìomhair" -> "Goraidh mac Ìomhair" | Same name as the first Stone King (I-0081) for a different person; renamed the later rìgh of Dùn dhearg. |
| II-0079 | rename "Ailean mac Ìomhair" -> "Goraidh mac Ìomhair" | Same name as the first Stone King (I-0081) for a different person; renamed the later rìgh of Dùn dhearg. |
| II-0079 | rename "Ailean Mòr" -> "Goraidh Mòr" | Same name as the first Stone King (I-0081) for a different person; renamed the later rìgh of Dùn dhearg. |
| II-0080 | rename "Ailean Mòr" -> "Goraidh Mòr" | Same name as the first Stone King (I-0081) for a different person; renamed the later rìgh of Dùn dhearg. |
| II-0081 | rename "Ailean Mòr" -> "Goraidh Mòr" | Same name as the first Stone King (I-0081) for a different person; renamed the later rìgh of Dùn dhearg. |
| II-0081 | rename "Mòrag nic Ailein" -> "Mòrag nic Ghoraidh" | Patronymic follows her father's rename; also removes the clash with Mòrag nic Ailein, queen in Age III (III-0213). |
| II-0112 | rename "Ailean Mòr" -> "Goraidh Mòr" | Same name as the first Stone King (I-0081) for a different person; renamed the later rìgh of Dùn dhearg. |
| II-0129 | "The meeting outlives its purpose and becomes the contest later called Còmhrag Ceann leathan." -> "The meeting outlives its purpose; the field it used is the one where Còmhrag Ceann leathan is later fought." | The canon event V-0096 establishes the Còmhrag in Age V; this can't be its origin. |
| II-0145 | "A beacon is built on the eastern point at Baile ìseal, kept" -> "The old beacon on the eastern point at Baile ìseal is rebuilt, kept" | The Baile ìseal beacon is first kept in Age I (I-0161). |
| II-0146 | "A beacon is built on the northern headland at Muileann bheag, the ancestor" -> "The old beacon on the northern headland at Muileann bheag is rebuilt, the ancestor" | The Muileann bheag beacon is first kept in Age I (I-0162). |
| II-0147 | "A beacon is built on the north-eastern cape at Àth dhearg by Sliochd Raghnaill" -> "The old beacon on the north-eastern cape at Àth dhearg is rebuilt by Sliochd Raghnaill" | The Àth dhearg beacon is first kept in Age I (I-0163). |
| II-0183 | rename "Ailean Mòr" -> "Goraidh Mòr" | Same name as the first Stone King (I-0081) for a different person; renamed the later rìgh of Dùn dhearg. |
| II-0248 | rename "Ailean Mòr" -> "Goraidh Mòr" | Same name as the first Stone King (I-0081) for a different person; renamed the later rìgh of Dùn dhearg. |

### Age III

| id | what | why |
|---|---|---|
| III-0002 | "is repeated in Queen Beathag nic Dhòmhnaill's hall at Cathair dhearg by" -> "is repeated at Cathair dhearg in the hall of Queen Beathag nic Dhòmhnaill, daughter of Mòr nic Coinnich, by" | Royal hand-off: Age II closes with Mòr nic Coinnich crowned (II-0247), and Age III opened with an unconnected queen. |
| III-0006 | "The vein-house above Muileann dhearg reckons" -> "The vein-house above Muileann dhearg, heir to the Keepers' Hall at Dùn ìseal, reckons" | Custodian hand-off: the Age II Keepers sit at Talla na Lasrach, Dùn ìseal; Age III's vein-house appeared from nowhere. |
| III-0034 | "Clann Dhòmhnaill, Clann Fhearchair" -> "Clann Mhuirich, Clann Fhearchair" | Of the Four Houses of custody (II-0046), Sliochd Mhuirich, the main Keeper house, was missing from the seven. Clann Dhòmhnaill appears nowhere else, so it was swapped for Clann Mhuirich. |
| III-0052 | "is first worked into neck-rings for the heads of the seven houses. A smiths' fellowship forms around the seam and keeps its methods within four families." -> "is worked into neck-rings for the heads of the seven houses. The smiths' fellowship of the seam, heir to Sliochd Fhearchair, closes its methods within four families." | Silver is smelted and smithed at Muileann chiar from II-0016, and the silversmiths' house Sliochd Fhearchair is in II-0150. |
| III-0061 | rename "Fearchar Òg" -> "Fearchar Donn" | Fearchar Òg is already the rìgh of Dùn dhearg in Age II (II-0118, II-0126); renamed the Age III king. |
| III-0062 | "At Cnoc bheag the priestess Gormshuil nic Artair teaches" -> "At Cnoc bheag, where the dawn-hawk rite of the Holy Age is still kept, the priestess Gormshuil nic Artair teaches" | The hawk called Mòd and its rite already exist in Age II (II-0158, II-0159, II-0216). Gormshuil now formalises the Hawk faith instead of founding it. |
| III-0062 | "Her followers are the first house of Creideamh an t-Seabhaig." -> "Her followers gather the old rite into the first house of Creideamh an t-Seabhaig." | As above. |
| III-0068 | "by Clann Lachlainn, who hold the land around it" -> "by Clann Ìomhair, who hold the land around it" | Dùn dhearg is the seat and burying-place of the house of Ìomhar (II-0046, II-0135, II-0148). |
| III-0069 | rename "Fearchar Òg" -> "Fearchar Donn" | Fearchar Òg is already the rìgh of Dùn dhearg in Age II (II-0118, II-0126); renamed the Age III king. |
| III-0086 | "Dòmhnall mac Ailein, a net-maker of Inis thais, preaches a single god, Clach," -> "Dòmhnall mac Ailein, a net-maker of Inis thais, where the wolf-sworn's stone stands, gives the one god of the wolf-sworn a name, Clach," | The wolf-sworn, their wolf-stone at Inis thais and their one god are in Age II (II-0100, II-0161, II-0217). This is now a naming, not a founding. |
| III-0087 | "the first building on the island made for a god of one name only" -> "the first temple on the island raised to Clach by name" | The wolf-sworn already built a hall to their one god (II-0217). |
| III-0089 | "takes up the teaching of Uallach" -> "takes up the wood-watchers' teaching of Uallach" | The black horned beast of two natures and the wood-watchers at court come from Age II (II-0114, II-0210, II-0220). |
| III-0099 | "casts the first bronze bell on Rodos for its hawk-house" -> "casts the first bronze bell on Rodos hung in a hawk-house" | The bronze-casters of Muileann dhearg were already casting bells in Age II (II-0154). |
| III-0105 | place burg:95 -> burg:64 | The text is about Seann Warr, which is burg:64 (the western port; burg:95 is Caol mhòr in the Tuathaich north-west). |
| III-0112 | rename "Catrìona Mhòr" -> "Catrìona Bhuadhach" | Catrìona Mhòr is the twelfth Stone King in Age I (I-0243); renamed the Age III queen. |
| III-0113 | rename "Catrìona Mhòr" -> "Catrìona Bhuadhach" | Catrìona Mhòr is the twelfth Stone King in Age I (I-0243); renamed the Age III queen. |
| III-0115 | place burg:95 -> burg:64 | The text is about Seann Warr, which is burg:64 (the western port; burg:95 is Caol mhòr in the Tuathaich north-west). |
| III-0116 | rename "Catrìona Mhòr" -> "Catrìona Bhuadhach" | Catrìona Mhòr is the twelfth Stone King in Age I (I-0243); renamed the Age III queen. |
| III-0120 | "At Seann Skell a preacher named Mànas mac Ruairidh proclaims Cnut, the Yellow Scorpion, as the one god," -> "At Seann Skell, where the sting-creed of the Holy Age first called itself the only true one, a preacher named Mànas mac Ruairidh proclaims its one power as Cnut, the Yellow Scorpion," | The sting-oath becomes a one-god creed at Seann Skell in Age II (II-0086, II-0160, II-0218, II-0219). Mànas now names it instead of founding it. |
| III-0121 | rename "Catrìona Mhòr" -> "Catrìona Bhuadhach" | Catrìona Mhòr is the twelfth Stone King in Age I (I-0243); renamed the Age III queen. |
| III-0130 | "Clann Choinnich builds a bath-house of dressed stone over the hot springs of …" -> "Clann Choinnich rebuilds the old bath-house over the hot springs of … in dressed stone" | The bath-house over the springs is first built in Age II (II-0063). |
| III-0149 | "break into a cave, Toll-dubh, and find a stair" -> "break into Toll-dubh, the shaft of the old tellings, long lost, and find a stair" | The western Toll-dubh is cut and known in Age I (I-0037). |
| III-0160 | rename "Beathag Ruadh" -> "Beathag Fhionn" | Beathag Ruadh is the first holder of the Red Hill in Age I (I-0083); renamed the Age III queen. |
| III-0163 | rename "Beathag Ruadh" -> "Beathag Fhionn" | Beathag Ruadh is the first holder of the Red Hill in Age I (I-0083); renamed the Age III queen. |
| III-0176 | rename "Iain Dubh" -> "Iain Ciar" | Iain Dubh is the sixth Stone King in Age I (I-0104); renamed the Age III king of the Brothers' War. |
| III-0177 | rename "Iain Dubh" -> "Iain Ciar" | Iain Dubh is the sixth Stone King in Age I (I-0104); renamed the Age III king of the Brothers' War. |
| III-0179 | rename "Iain Dubh" -> "Iain Ciar" | Iain Dubh is the sixth Stone King in Age I (I-0104); renamed the Age III king of the Brothers' War. |
| III-0180 | rename "Iain Dubh" -> "Iain Ciar" | Iain Dubh is the sixth Stone King in Age I (I-0104); renamed the Age III king of the Brothers' War. |
| III-0182 | rename "Iain Dubh" -> "Iain Ciar" | Iain Dubh is the sixth Stone King in Age I (I-0104); renamed the Age III king of the Brothers' War. |
| III-0183 | rename "Iain Dubh" -> "Iain Ciar" | Iain Dubh is the sixth Stone King in Age I (I-0104); renamed the Age III king of the Brothers' War. |
| III-0185 | rename "Iain Dubh" -> "Iain Ciar" | Iain Dubh is the sixth Stone King in Age I (I-0104); renamed the Age III king of the Brothers' War. |
| III-0197 | rename "Catrìona Mhòr" -> "Catrìona Bhuadhach" | Catrìona Mhòr is the twelfth Stone King in Age I (I-0243); renamed the Age III queen. |
| III-0199 | "find a second cave also called Toll-dubh, with" -> "find again the eastern Toll-dubh of the old tellings, with" | The eastern Toll-dubh is known in Age I (I-0036), and a youth was let down it (I-0120). |

### Age IV

| id | what | why |
|---|---|---|
| IV-0005 | "The Council of Custodians at Cathair dhearg, under the high custodian" -> "The Council of Custodians at Cathair dhearg, which has sat in the crown's place since the crown fell vacant at the close of the Sundering age, under the high custodian" | Royal hand-off: Age III ends with a crowned ruler, Age IV has no crown, and Age V speaks of a restored kingdom. The lapse is now stated. |
| IV-0025 | "on a coast without a single light" -> "on a coast lit only by the old driftwood fires" | Five beacons burn from Age I (I-0164) and the Holy Age (II-0029, II-0231). |
| IV-0027 | rename "Ailean Clachair" -> "Torcall Clachair" | Ailean Clachair is the Holy Age founder of the bridge-masons (II-0033); renamed the Age IV beacon mason. |
| IV-0027 | rename "Ailean's cairns" -> "Torcall's cairns" | Follows the Torcall Clachair rename. |
| IV-0027 | "to choose sites for the beacons. They mark five headlands." -> "to choose sites for the new beacons. They mark the five headlands of the old fires." | The five beacon sites are fixed in Age I (I-0164). |
| IV-0028 | rename "Eilidh nic Iain" -> "Eilidh nic Ruairidh" | Eilidh nic Iain is Eilidh Dhubh of Doire chiar in Age III (III-0094); renamed the Age IV net-maker who married Samuel Hale. |
| IV-0046 | rename "Beathag Ruadh" -> "Beathag Dhubh" | Beathag Ruadh already names the Red Hill holder (Age I) and a queen (Age III); renamed the custodian of Doire mhòr. |
| IV-0048 | rename "Ailean Clachair" -> "Torcall Clachair" | Ailean Clachair is the Holy Age founder of the bridge-masons (II-0033); renamed the Age IV beacon mason. |
| IV-0048 | "The first beacon is finished on the southern headland at Tobar dhearg, a round tower of grey stone with" -> "The first of the new beacons is finished on the southern headland at Tobar dhearg, a round tower of grey stone raised over the old fire-tower, with" | Tobar dhearg already had a stone tower from Age II (II-0231). |
| IV-0057 | "Drochaid Cathair dhearg in stone" -> "Drochaid Cathair dhearg rebuilt" | The bridge at Cathair dhearg is of stone from Age II (II-0032, II-0083, II-0190) and is widened in Age III (III-0071). |
| IV-0057 | "replace the timber bridge over Abhainn dhomhain at Cathair dhearg with one of dressed stone," -> "rebuild the old stone bridge over Abhainn dhomhain at Cathair dhearg in dressed stone," | As above. |
| IV-0061 | rename "Coinneach Bàn" -> "Coinneach Glas" | Coinneach Bàn is a ruler at Cathair dhearg in Age II (II-0212/0213); renamed the Age IV high custodian. |
| IV-0068 | rename "Coinneach Bàn" -> "Coinneach Glas" | Coinneach Bàn is a ruler at Cathair dhearg in Age II (II-0212/0213); renamed the Age IV high custodian. |
| IV-0075 | rename "Ailean Clachair" -> "Torcall Clachair" | Ailean Clachair is the Holy Age founder of the bridge-masons (II-0033); renamed the Age IV beacon mason. |
| IV-0078 | rename "Beathag Ruadh" -> "Beathag Dhubh" | Beathag Ruadh already names the Red Hill holder (Age I) and a queen (Age III); renamed the custodian of Doire mhòr. |
| IV-0088 | "An Taigh-seinnse Mòr opens" -> "An Taigh-seinnse Mòr reopens" | The house on this site is built in Age II (II-0037) and named in Age III (III-0098, III-0180). |
| IV-0088 | "A carters' house is built at the halfway stage of the ore road between the capital and the hills, and becomes An Taigh-seinnse Mòr." -> "The old carters' house at the halfway stage of the ore road between the capital and the hills is rebuilt, and keeps the name An Taigh-seinnse Mòr." | As above. |
| IV-0102 | rename "Sìleas nic Choinnich" -> "Ùna nic Choinnich" | Sìleas nic Coinnich founded the stag's school in Age II (II-0022); renamed the silver-guild leader (kept nic Choinnich, which ties her to Clann Choinnich's silver petitions in Age III). |
| IV-0106 | rename "Tormod mac Iain" -> "Tormod mac Pheadair" | Tormod mac Iain already names Tormod Scrìobhaiche (II-0109) and King Tormod Bàn (III-0097); renamed the Àth dhearg beacon keeper. |
| IV-0107 | rename "Tormod mac Iain" -> "Tormod mac Pheadair" | Tormod mac Iain already names Tormod Scrìobhaiche (II-0109) and King Tormod Bàn (III-0097); renamed the Àth dhearg beacon keeper. |
| IV-0123 | "The Company builds a bridge over the river at Ros fhionn" -> "The Company rebuilds the old bridge over the river at Ros fhionn" | Drochaid Ros fhionn stands from Age II (II-0033, II-0191) through Age III (III-0081, III-0162, III-0168). |
| IV-0143 | rename "Sìleas nic Choinnich" -> "Ùna nic Choinnich" | Sìleas nic Coinnich founded the stag's school in Age II (II-0022); renamed the silver-guild leader (kept nic Choinnich, which ties her to Clann Choinnich's silver petitions in Age III). |
| IV-0154 | "The sickness spreads along the ore roads to Muileann chrom, Baile dhomhain, Àth ìseal, Cnoc fhiadhaich and Seann Toll, and from there to the coast." -> "The sickness spreads along the ore roads from the camps at Muileann chrom, Àth ìseal and Cnoc fhiadhaich, and falls hardest on Ros dhìreach, Ceann òg, Inis ìseal, Baile dhomhain, Achadh fhada, Cnoc bheag, Muileann uaine, Cuan àrsaidh and Inis bhàn." | The event is placed at zone:0, whose struck burgs (PLACE_FACTS) are those nine. The old text named other towns as the zone. |
| IV-0170 | "The Administration builds a bath-house at the hot springs" -> "The Administration builds a new bath-house at the hot springs" | A bath-house stands on the springs from Age II (II-0063, III-0130). |
| IV-0175 | rename "Black Unicorn" -> "Dark Unicorn" | Same faith is 'the Dark Unicorn' in the brief and in Ages III and V; one English name for Uallach's faith. |
| IV-0179 | rename "Black Unicorn" -> "Dark Unicorn" | Same faith is 'the Dark Unicorn' in the brief and in Ages III and V; one English name for Uallach's faith. |
| IV-0219 | "from Achadh shean down to Cuan ruadh and west toward Baile chaol." -> "worst at Achadh shean, Àth uaine, Achadh àrsaidh and Muileann chiar, and reaching down to Cuan ruadh and west toward Baile chaol." | The event is placed at zone:2, whose struck burgs (PLACE_FACTS) are Achadh shean, Àth uaine, Achadh àrsaidh and Muileann chiar. They are now named. |
| IV-0231 | rename "Eilidh nic Iain" -> "Eilidh nic Ruairidh" | Eilidh nic Iain is Eilidh Dhubh of Doire chiar in Age III (III-0094); renamed the Age IV net-maker who married Samuel Hale. |
| IV-0248 | "to the town of Muileann chaol for safekeeping" -> "to the town of Muileann chaol, which still kept Beathag nic Thòmais's loft of papers, for safekeeping" | Library hand-off: the Age III collection at Muileann chaol (III-0217, III-0221) is the one the custodians add to. |
| IV-0300 | "opened by Seònaid Bhàn" -> "reopened by Seònaid Bhàn" | Follows IV-0088. |
| IV-0309 | rename "Beathag Ruadh" -> "Beathag Dhubh" | Beathag Ruadh already names the Red Hill holder (Age I) and a queen (Age III); renamed the custodian of Doire mhòr. |
| IV-0315 | rename "Black Unicorn" -> "Dark Unicorn" | Same faith is 'the Dark Unicorn' in the brief and in Ages III and V; one English name for Uallach's faith. |
| IV-0322 | rename "Black Unicorn" -> "Dark Unicorn" | Same faith is 'the Dark Unicorn' in the brief and in Ages III and V; one English name for Uallach's faith. |

### Age V

| id | what | why |
|---|---|---|
| V-0029 | "The first high custodian" -> "The first high custodian of the Rite" | 'High custodian' is already the head of the Council of Custodians in Age IV (IV-0005, IV-0216). |
| V-0040 | "built under the humans" -> "rebuilt under the humans" | The bridge is of stone from Age II; the humans rebuilt it (IV-0057). |
| V-0048 | "begin walking each year to the holy well called Allt an Àigh in the east, whose water the old tales call healing" -> "keep up their yearly walk to the holy well called Allt an Àigh in the east, whose water the old tales say brings fortune" | The canon event II-0011 has a pilgrimage that 'has never fully stopped' to a stream that grants fortune, kept up in III-0175 and IV-0222. |
| V-0051 | "whose house held the overseer's post under the humans" -> "whose house held an overseer's post under the humans" | In Age IV the overseer's staff at Muileann chrom belongs to Raghnall Maor's line, which ends with Mòrag nic Iain Maor (IV-0092 to IV-0319). There were many overseers (IV-0093). |
| V-0053 | "and its hall of Feallsanachd an Fhèidh is enlarged twice in the same span" -> "and its hall of Feallsanachd an Fhèidh, shut since the humans' time, is taken for a hewers' lodging and enlarged twice in the same span" | The Deer school is dormant from IV-0247 until the canon revival V-0162. |
| V-0071 | "He brings with him the council's minute-books … and spends" -> added "takes in the custodians' rolls kept in the town's cellars since the Severance war," | Library hand-off: the rolls the custodians sent to Muileann chaol (IV-0248, IV-0376) pass into the new library. |
| V-0074 | "A bath-house is built over the hot springs" -> "A new bath-house is built over the hot springs" | The springs have had a bath-house since Age II (II-0063, III-0130, IV-0170). |
| V-0075 | "At Taigh-solais Baile chrom, the one beacon on the Tuathaich coast," -> "At Taigh-solais Baile chrom, on the Tuathaich coast," | Muileann bheag (marker:14, burg:327) is also a Tuathaich town, as V-0253 says. |
| V-0103 | "the oldest on the west coast" -> "one of the oldest on the west coast" | The Scorpion creed begins at Seann Skell (II-0218, III-0120). |
| V-0123 | "The lighthouse on the Tuathaich coast" -> "A lighthouse on the Tuathaich coast" | As V-0075. |
| V-0137 | "The town's silversmiths are chartered as a guild." -> "The town's old silver guild takes a charter under the restored custom." | The silver guild of Muileann chiar already exists and holds the seam in Age IV (IV-0102, IV-0337). |
| V-0152 | rename "Tormod mac Ailein" -> "Tormod mac Sheumais" | Tormod mac Ailein is the high custodian who signed the first treaty (IV-0005); renamed the royal chronicler Tormod Pinn. |
| V-0163 | "where the Fèidh had last met before the humans came" -> "where the Fèidh had last met under the humans" | Deer masters taught in this wood during the humans' time (IV-0188). |
| V-0210 | "named in the Holy Age lists and not seen since." -> "named in the Holy Age lists and not seen in living memory." | A great panther crossing is recorded in Age III (III-0225). |
| V-0275 | rename "Tormod mac Coinnich" -> "Tormod mac Dhonnchaidh" | Tormod mac Coinnich is the granary reeve of Àth shean in Age III (III-0019); renamed the last master of the Guild of Hewers. |

## Checked and left alone

- **Tormod mac Iain in Age II and Age III.** Tormod Scrìobhaiche (II-0109) and King Tormod Bàn (III-0097) share a patronymic. Each is always known by his byname, and the Age III king really is the son of Iain mac Aonghais, so both names stand. Only the Age IV keeper, who had no byname, was renamed.
- **Surnames that recur across ages.** The Hales (Samuel and Thomas Hale in IV; Walter and Peter Hale in V), the Pikes (Thomas in IV, Agnes in V) and the Cranes (Commissioner Walter Crane in IV, Hannah Crane in V) read as families that stayed on. Patronymics shared across different people (mac Ruairidh, nic Coinnich, nic Artair and others) are ordinary Gaelic usage and do not collide on a full name.
- **Tensions inside the canon itself.** These were left because canon cannot change. II-0001 puts the custodianship "centuries before anything like a king", yet Age I has Stone Kings. The non-canon text already says the list was only "later called" Rìghrean na Cloiche, and the Stone Kings' list now ends with Catrìona Mhòr. V-0176 calls the first failed vein search a Holy Age attempt, but canon I-0144 sets it in Age I. V-0177 follows V-0176.
- **Four Muileann chiars.** Place refs were checked: burg:419 is the silver town (marker:2), burg:78 has the sacred forest (marker:23) and zone:2, and burg:355 is the "new town" of IV-0172. Every event is on the right one.
- **Regiments and fleets.** All thirteen stations in Age V match PLACE_FACTS, including the two Seann Skells (seventh regiment at burg:489; ninth regiment and second fleet at burg:431).
- **The five lighthouses.** The arc now runs as follows. Age I lights fires at all five sites. Age II relights and rebuilds them, with the first stone tower at Tobar dhearg (II-0231). Age IV raises new towers on the old sites under the humans (IV-0048 onward; canon IV-0191). Age V converts them (canon V-0251).

