# Proper nouns in Dia-thìris

The readable table of `eras/NAMES.json`, the single source of truth for the Dia-thìris form of every proper noun of the legendarium that stands in English. Human personal names are not in it and stay as written.

- **Dia-thìris** is the form to write. Every form is unchanged by `rodais_engine.normalize()` and passes `check_agreement()` word by word.
- **Gloss** is the English given once, on first mention in a chapter, section or annals entry. The build prints it after the name (`legendarium/glosses.py`: a footnote in the PDF, a hover gloss in the Atlas), so the gloss never repeats the Dia-thìris.
- **First** is the first-attested annals event id.
- **Status**: *existing* means the legendarium, the dictionary, TEXTS or the map already gives the form; *coined* means it was made for this registry from the dictionary's words and the grammar (article and genitive, lenition in names, kennings of old roots).
- The glosses are matched case-sensitively, so write the form exactly as given, article and all.
- Additions go through the lead.

**334 names** (171 existing, 163 coined) and **49 ambiguous cases** for the lead.

## Ages (7)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Ancient Age <br>*also:* Ancient Age; Age I; the First Age | **An Aois Àrsaidh** | the Ancient Age | I-0001 | existing |
| the Age of Ailean <br>*also:* Age of Ailean; Age II | **An Aois Ailein** | the Age of Ailean | I-0080b | existing |
| the Holy Age <br>*also:* Holy Age; Age III | **An Aois Naomh** | the Holy Age | I-0098a | existing |
| the Age of Sundering <br>*also:* Age of Sundering; Age IV | **An Aois Scaraidh** | the Age of Sundering | III-0001 | existing |
| the Age of Strangers <br>*also:* Age of Strangers; Age V | **An Aois Choigreach** | the Age of Strangers | IV-0001 | existing |
| the Age of the Kingdom <br>*also:* Age of the Kingdom; Age VI | **An Aois Rìoghachd** | the Age of the Kingdom | V-0001 | existing |
| the Age of Dubhan <br>*also:* Age of Dubhan; Age VII | **An Aois Dhubhain** | the Age of Dubhan | VI-0001 | existing |

## Eras and periods (10)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Vein Era <br>*also:* Vein Era; VE | **Linn na Fèithe** | the Vein Era (VE); lit. 'the era of the vein' | I-0001 | existing |
| the Grove Era <br>*also:* Grove Era; GE | **Linn na Doire** | the Grove Era (GE); lit. 'the era of the grove' | I-0080b | existing |
| the Flame Era <br>*also:* Flame Era; FE; the year of the Flame | **Linn an Teine** | the Flame Era (FE); lit. 'the era of the fire' | I-0098a | existing |
| the Landfall Era <br>*also:* Landfall Era; LE | **Linn na Tìre** | the Landfall Era (LE); lit. 'the era of the land' | III-0001 | existing |
| the Anchor Era <br>*also:* Anchor Era; AE | **Linn an Acair** | the Anchor Era (AE); lit. 'the era of the anchor' | IV-0001 | existing |
| the Severance Era <br>*also:* Severance Era; SE | **Linn an Dealachaidh** | the Severance Era (SE); lit. 'the era of the parting' | V-0001 | existing |
| the Dubhan Era <br>*also:* Dubhan Era; DE | **Linn an Dubhain** | the Dubhan Era (DE); lit. 'the era of Dubhan' <br>*note:* The map calendar field reads "Dubhan Era" and check_rodais.py requires that exact English string there. | VI-0049a | existing |
| the long years <br>*also:* the Long Years | **na Bliadhnachan Fada** | the long years of Ailean's kin | I-0084 | existing |
| the Reverent Centuries <br>*also:* the reverent centuries | **Na Linntean Urramach** | the Reverent Centuries of the Holy Age; lit. 'the reverent centuries' | II-0058 | coined |
| the Years of Fair Exchange | **Bliadhnachan na Malairt Cothromaich** | the years of fair exchange after the Crossing <br>*note:* promoted | — | coined |

## Wars (8)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Strife of the Heirs <br>*also:* the strife of the heirs; the feuds of the heirs | **Aimhreit nan Oighrean** | the Strife of the Heirs | I-0098a | existing |
| the War of the Two Oaths <br>*also:* War of the Two Oaths | **Cogadh an Dà Mhionn** | the War of the Two Oaths | II-0064b | existing |
| the War of the Roads <br>*also:* War of the Roads | **Cogadh nan Rathad** | the War of the Roads | II-0091 | coined |
| the Silver Feud <br>*also:* Silver Feud; the closing of the silver | **Falachd an Airgid** | the Silver Feud; lit. 'the feud of the silver' | II-0150 | coined |
| the War of the Three Claimants <br>*also:* War of the Three Claimants; the Three Claimants; Three Claimants | **Cogadh nan Trì Tagraichean** | the War of the Three Claimants | III-0104 | coined |
| the Brothers' War <br>*also:* Brothers' War; the war of the brothers | **Cogadh nam Bràithrean** | the Brothers' War | III-0177 | existing |
| the War of the Hills <br>*also:* War of the Hills; the Severance war | **Cogadh nam Beann** | the War of the Hills, called also the Severance war | IV-0324 | coined |
| the Long War <br>*also:* Long War | **An Cogadh Fada** | the Long War | VI-0075 | existing |

## Battles and fights (11)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Battle of the Ford of Blood <br>*also:* the battle at the Ford of Blood; the king's last war; the Last Battle | **Blàr Àth na Fala** | the Battle of the Ford of Blood | I-0098a | existing |
| the burning of Achadh mhòr <br>*also:* Burning of Achadh mhòr | **Loscadh Achadh mhòr** | the burning of Achadh mhòr | II-0064b | coined |
| the fight at Àth fhiadhaich <br>*also:* Fight at Àth fhiadhaich | **Blàr Àth fhiadhaich** | the fight at the ford of Àth fhiadhaich | II-0095 | coined |
| the ford at Àth shean <br>*also:* Ford at Àth shean | **Blàr Àth shean** | the battle of the ford at Àth shean | III-0106 | coined |
| the battle of Muileann chrom <br>*also:* Battle of Muileann chrom | **Blàr Muileann chrom** | the battle of Muileann chrom | III-0110 | coined |
| the battle of Cnoc naomh <br>*also:* Battle of Cnoc naomh | **Blàr Cnoc naomh** | the battle of Cnoc naomh | III-0177 | coined |
| the battle of Muileann ghlas <br>*also:* Battle of Muileann ghlas; the Battle of Muileann | **Blàr Muileann ghlas** | the battle of Muileann ghlas (Brothers' War and Long War) <br>*note:* two battles share the name: III-0179 (Brothers' War) and VI-0115 (Long War) | III-0179 | coined |
| the fight at the ford of Àth chiar <br>*also:* Ford of Àth chiar | **Blàr Àth chiar** | the fight at the ford of Àth chiar | IV-0335 | coined |
| the shelling of Seann Toll <br>*also:* Shelling of Seann Toll | **Loscadh Seann Toll** | the shelling of Seann Toll <br>*note:* loscadh "firing" (of guns), as in the dictionary | IV-0342 | coined |
| the fight at Cnoc ghorm <br>*also:* Fight at Cnoc ghorm | **Blàr Cnoc ghorm** | the fight at Cnoc ghorm | IV-0359 | coined |
| the Battle of Àth leathan <br>*also:* Battle of Àth leathan | **Blàr Àth leathan** | the Battle of Àth leathan | VI-0081 | coined |

## Sieges (4)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the siege of Caol leathan <br>*also:* Siege of Caol leathan | **Sèist Caol leathan** | the siege of Caol leathan | II-0098 | coined |
| the siege of Cathair dhomhain <br>*also:* Siege of Cathair dhomhain | **Sèist Cathair dhomhain** | the siege of Cathair dhomhain | III-0108 | coined |
| the siege of the store at Baile thais <br>*also:* Siege of the store at Baile thais | **Sèist Baile thais** | the siege of the store at Baile thais | IV-0327 | coined |
| the siege of Muileann àrsaidh <br>*also:* Siege of Muileann àrsaidh | **Sèist Muileann àrsaidh** | the siege of Muileann àrsaidh | VI-0091 | coined |

## Raids (2)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the salt-flats raid <br>*also:* Salt-flats raid | **Creach an t-Salainn** | the salt-flats raid; lit. 'the raid of the salt' | I-0099 | coined |
| the raid on Eilean dhubh <br>*also:* Raid on Eilean dhubh | **Creach Eilean dhubh** | the raid on Eilean dhubh | III-0133 | coined |

## Companies and hosts (4)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Leaden Hawk <br>*also:* the Leaden Hawk company; Leaden Hawk | **Buidheann an t-Seabhaig Luaidhe** | the Leaden Hawk company; lit. 'the company of the leaden hawk' | IV-0342a | existing |
| the Severance companies <br>*also:* the war-companies; Severance companies | **Buidhnean an Dealachaidh** | the war-companies of the Severance | V-0002 | coined |
| the Circus <br>*also:* the circus | **An Siorcas Siubhail Do-thuigsinn** | the Incomprehensible Travelling Circus | V-0102 | existing |
| the Fianna <br>*also:* the Fianna of the Stone; the wolf-sworn | **an Fhianna** | the Fianna, the sworn guards of the Stone | II-0100 | coined |

## Regiments (9)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the first regiment <br>*also:* The first regiment | **A' chiad rèisimeid** | the first regiment | VI-0088 | existing |
| the second regiment <br>*also:* The second regiment | **An dàrna rèisimeid** | the second regiment | VI-0102 | existing |
| the third regiment <br>*also:* The third regiment | **An treas rèisimeid** | the third regiment | VI-0092 | existing |
| the fourth regiment <br>*also:* The fourth regiment | **An ceathramh rèisimeid** | the fourth regiment | VI-0103 | existing |
| the fifth regiment <br>*also:* The fifth regiment | **An còigeamh rèisimeid** | the fifth regiment | VI-0093 | existing |
| the sixth regiment <br>*also:* The sixth regiment | **An siathamh rèisimeid** | the sixth regiment | VI-0101 | existing |
| the seventh regiment <br>*also:* The seventh regiment | **An seachdamh rèisimeid** | the seventh regiment | VI-0084 | existing |
| the eighth regiment <br>*also:* The eighth regiment | **An t-ochdamh rèisimeid** | the eighth regiment | VI-0106 | existing |
| the ninth regiment <br>*also:* The ninth regiment | **An naoidheamh rèisimeid** | the ninth regiment | VI-0110 | existing |

## Fleets (5)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the first fleet <br>*also:* The first fleet | **A' chiad chabhlach** | the first fleet | VI-0089 | existing |
| the second fleet <br>*also:* The second fleet | **An dàrna cabhlach** | the second fleet | VI-0099 | existing |
| the third fleet <br>*also:* The third fleet | **An treas cabhlach** | the third fleet | VI-0107 | existing |
| the fourth fleet <br>*also:* The fourth fleet | **An ceathramh cabhlach** | the fourth fleet | VI-0090 | existing |
| the fleet of the Sundering <br>*also:* the fleet; the departed fleet | **Cabhlach an Scaraidh** | the fleet of the Sundering | III-0021 | coined |

## Treaties and truces (3)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Peace of the Threshold <br>*also:* Peace of the Threshold; the Peace | **Sìth an Stairsnich** | the Peace of the Threshold | II-0064c | existing |
| the truce of Àth àrsaidh <br>*also:* Truce of Àth àrsaidh | **Fosadh Àth àrsaidh** | the truce of Àth àrsaidh | IV-0369 | coined |
| the first written treaty <br>*also:* the treaty; the Treaty in One Tongue; the first treaty | **Cùmhnant Cathair dhearg** | the first written treaty, signed at Cathair dhearg; the Treaty in One Tongue | IV-0029 | coined |

## Compacts and oaths (4)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Binding of the First Flame <br>*also:* Binding of the First Flame | **Ceangal na Ciad Lasrach** | the Binding of the First Flame | II-0001 | coined |
| the Binding | **An Ceangal** | the Binding (of the First Flame); lit. 'the bond' | II-0001 | coined |
| the oath of the seven <br>*also:* the Oath of the Seven | **Mionnan nan Seachd** | the oath of the seven houses | III-0197 | coined |
| the Silver Compact <br>*also:* Silver Compact | **Cùmhnant an Airgid** | the Silver Compact; lit. 'the covenant of the silver' | IV-0103 | coined |

## Laws and rulings (11)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Small-Burning Law <br>*also:* the Law; Small-Burning Law; the first law | **Lagh an Loscaidh Bhig** | the Small-Burning Law; lit. 'the law of the small burning' | II-0027 | existing |
| the shared-meal law <br>*also:* the first shared meal law; the shared meal law; the Shared Meal | **Lagh a' Bhìdh Roinnte** | the shared-meal law; lit. 'the law of the shared food' | I-0146 | coined |
| the road-peace <br>*also:* the Road-Peace | **Sìth an Rathaid** | the road-peace; lit. 'the peace of the road' | II-0038 | coined |
| the division of keeping <br>*also:* the Division of Keeping | **Roinn a' Ghleidhidh** | the division of keeping between rìgh and Keeper | II-0078 | coined |
| the ruling of the hearth <br>*also:* the Ruling of the Hearth | **Riaghailt an Teallaich** | the ruling of the hearth; lit. 'the rule of the hearth' | III-0113 | coined |
| the Levy <br>*also:* Levy | **An Togail** | the Levy of one in five for the pits; lit. 'the raising' | IV-0181 | coined |
| Dunstan's rule | **Riaghailt Dunstan** | Dunstan's rule (a human's name kept as written) | IV-0232 | coined |
| the Law of One Line | **Lagh na h-Aon Loidhne** | the Law of One Line <br>*note:* the book's chapter title for the humans' inheritance rule; confirm it is meant as a name | IV-0230 | coined |
| the Leòid ruling <br>*also:* Leòid ruling | **Breith Leòid** | the Leòid ruling | V-0038 | coined |
| the Seann Bhral ruling | **Breith Seann Bhral** | the Seann Bhral ruling | V-0203 | coined |
| the wartime tithe | **Deachamh a' Chogaidh** | the wartime tithe | VI-0086 | coined |

## Charters and concessions (3)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Company's charter <br>*also:* the Company charter | **Cairt na Companaidh** | the Company's charter | IV-0032 | coined |
| the Sloc Mòr concession | **Cead an t-Sluic Mhòir** | the Sloc Mòr concession | V-0051 | coined |
| the market charter of Cathair fhada | **Cairt Mhargaidh Cathair fhada** | the market charter of Cathair fhada <br>*note:* one of several market charters (Caol ruadh, VI-0120a); the pattern Cairt Margaidh + town serves for all | III-0070a | coined |

## Articles (1)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Harbour Articles <br>*also:* Harbour Articles | **Puingean a' Chalaidh** | the Harbour Articles; lit. 'the points of the harbour' | IV-0058 | coined |

## Edicts (1)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the edict of seizure <br>*also:* the confiscation edict; the Edict of Seizure | **Àithne a' Ghlacaidh** | the edict of seizure (the confiscation edict) | IV-0316 | coined |

## Petitions (5)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the first petition <br>*also:* the First Petition | **A' Chiad Athchuinge** | the first petition of the Dia-thìrich to the Administration | IV-0204 | coined |
| the second petition <br>*also:* the Second Petition | **An Dàrna Athchuinge** | the second petition to the Administration | IV-0279 | coined |
| the Fed Hawk's petition | **Athchuinge an t-Seabhaig Bhiadhte** | the Fed Hawk's petition | III-0143 | coined |
| the silver petitions <br>*also:* the second silver petition; the silver petition | **Athchuingean an Airgid** | the silver petitions of Clann Choinnich | III-0208 | coined |
| the Moot's last petition <br>*also:* the Moot's petition | **Athchuinge Dheireannach an Tionail** | the Moot's last petition | VI-0077 | coined |

## Institutions (24)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Hall <br>*also:* the Hall of the Flame; the Hall at Dùn ìseal; the Hall of the Holy Age | **Talla na Lasrach** | the Hall of the Flame | II-0004 | existing |
| the nine hearths <br>*also:* the Nine Hearths | **Na Naoi Teallaichean** | the nine hearths that chose the Keeper | II-0003 | coined |
| the Four Houses <br>*also:* the four houses | **Na Ceithir Taighean** | the Four Houses of custody of the Holy Age | II-0046 | coined |
| the red hall <br>*also:* the Red Hall | **An Talla Dearg** | the red hall, the rìgh's hall at Cathair dhearg | II-0137 | coined |
| the seven houses of custody <br>*also:* the seven houses; the Seven Houses; the houses of custody | **Na Seachd Taighean** | the seven houses of custody <br>*note:* the houses themselves have Dia-thìris names (Clann Mhuirich, Clann Fhearchair...); the collective name is coined | III-0034 | coined |
| the vein-house <br>*also:* the Vein-House | **Taigh na Fèithe** | the vein-house above Muileann dhearg | III-0006 | coined |
| the house of disputation | **Taigh na Deasbaid** | the house of disputation at Dùn thais | III-0074 | coined |
| the Council of Custodians <br>*also:* Council of Custodians; the council of custodians | **Comhairle a' Chùraim** | the Council of Custodians; lit. 'the council of the custody' <br>*note:* "the council" is also the royal council of the Age of the Kingdom; choose by age | IV-0005 | coined |
| the Company <br>*also:* Company; the Company's; Clerk of the Company | **A' Chompanaidh** | the Company <br>*note:* existing in TEXTS (the Tuathaich tale: "a' Chompanaidh", "daoine na Companaidh"); a kenning Comann nan Coigreach was the alternative | IV-0032 | existing |
| the Administration <br>*also:* Administration; the humans' Administration | **Riaghaltas nan Coigreach** | the Administration; lit. 'the government of the strangers' | IV-0031 | coined |
| the Residency <br>*also:* Residency; the Residency at Ros | **Taigh an Àrd-mhaoir** | the Residency above Ros dhomhain; lit. 'the house of the high steward' | IV-0031 | coined |
| the Mission <br>*also:* Mission; the Mission at Cathair | **Teachdaireachd na h-Eaglaise** | the Mission; lit. 'the errand of the Church' | IV-0042 | coined |
| the Lamp-Watch <br>*also:* Lamp-Watch | **Faire nan Lòchran** | the Lamp-Watch; lit. 'the watch of the lamps' | IV-0234 | coined |
| the forest council <br>*also:* the council in the forest | **Comhairle na Coille** | the council of the mining regions, met in the sacred forest | IV-0322 | coined |
| the Kingdom of Dia-thìr <br>*also:* the Kingdom; the kingdom of Dia-thìr | **Rìoghachd Dia-thìr** | the Kingdom of Dia-thìr | V-0007 | existing |
| the Crown <br>*also:* Crown | **An Crùn** | the Crown <br>*note:* also the plain crown of the earlier ages; lower-case "the crown" there stays a common noun | V-0015 | coined |
| the council of the kingdom <br>*also:* the royal council; the council of twelve | **Comhairle na Rìoghachd** | the royal council of twelve | V-0009 | coined |
| the Moot <br>*also:* Moot; the Moot at Caol mhòr; the Moot at Caol | **Tional nan Tuathach** | the Moot; lit. 'the gathering of the northerners' <br>*note:* not Am Mòd: Mòd is the Hawk of Acaill's name in the Hawk order | V-0008 | coined |
| the Treasury <br>*also:* Treasury | **An t-Ionmhas** | the Treasury | V-0015a | coined |
| the Library <br>*also:* Library | **an Leabharlann** | the Library at Muileann chaol | V-0070 | existing |
| the Library at Muileann chaol <br>*also:* Leabharlann Muileann chaol; the Library of Muileann chaol | **Leabharlann Muileann chaol** | the Library at Muileann chaol | V-0070 | existing |
| the Mine Board <br>*also:* the Board; Mine Board | **Comhairle nam Mèinnean** | the Mine Board; lit. 'the board of the mines' | V-0107 | coined |
| the Rail Board <br>*also:* Rail Board | **Comhairle na Slighe-iarainn** | the Rail Board; lit. 'the board of the iron way' | V-0039 | coined |
| the Lighthouse Board | **Comhairle nan Taighean-solais** | the Lighthouse Board | V-0095 | coined |

## Guilds and fellowships (4)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the shipwrights' fellowship <br>*also:* the Shipwrights; the Sundering fellowship | **Comann nan Saor-luinge** | the shipwrights' fellowship | III-0010 | existing |
| the silver guild <br>*also:* the Silver Guild | **Comann an Airgid** | the silver guild of Muileann chiar | IV-0102 | coined |
| the Guild of Hewers <br>*also:* the Hewers; Guild of Hewers | **Comann nan Gualadairean** | the Guild of Hewers; lit. 'the fellowship of the colliers' | V-0060 | coined |
| the Fuel-Fitters <br>*also:* the Guild of Fuel-Fitters; Fuel-Fitters; the Guild of Fuel-Fitters at Seann Skell | **Comann nan Goibhnean-ceangail** | the Guild of Fuel-Fitters; lit. 'the fellowship of the fitters' | VI-0045 | coined |

## Offices (9)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Keeper of the Hall <br>*also:* the Keeper Raonaid Dhubh; the Keeper Calum Liath | **Coimheadaiche na Lasrach** | the Keeper of the Hall; lit. 'the watcher of the flame' <br>*note:* English "the Keeper" also means Coimhdeach na Fine; E_words says the two share a name only in translation. Writers must choose by sense: the spirit is Coimhdeach na Fine, the Hall's office is Coimheadaiche na Lasrach. | II-0002 | coined |
| the Keepers <br>*also:* the Keepers of the Flame; the Keepers of the Holy Age; the First Keepers | **Coimheadaichean na Lasrach** | the Keepers of the Hall; lit. 'the watchers of the flame' | II-0002 | coined |
| the high custodian of the Council <br>*also:* the high custodian; the council's high custodian | **Ceann a' Chùraim** | the high custodian of the Council of Custodians; lit. 'head of the custody' <br>*note:* not the Àrd-choimheadaiche of the Rite (E_words: the two share a name only in translation) | IV-0005 | coined |
| the Commissioner <br>*also:* Commissioner | **An t-Àrd-mhaor** | the Commissioner; lit. 'the high steward' | IV-0057a | coined |
| the Commissioners <br>*also:* the Commissioners of the Administration | **Na h-Àrd-mhaoir** | the Commissioners; lit. 'the high stewards' | IV-0069 | coined |
| the circuit justices <br>*also:* the circuit justice | **Britheamhan na Cuairte** | the circuit justices | V-0036 | coined |
| the high custodian of the Rite | **Àrd-choimheadaiche** | the high custodian of the Rite; lit. 'high watcher' | V-0029 | existing |
| the keeper of the Library <br>*also:* the Library's keeper | **Neach-gleidhidh an Leabharlainn** | the keeper of the Library | V-0071 | coined |
| the royal chronicler | **Seanchaidh na Rìoghachd** | the royal chronicler | V-0078 | coined |

## Titles used as names (2)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Mason <br>*also:* Mason | **An Clachair** | the Mason, Neachdan, who broke the vein | I-0001 | coined |
| king of the godkin <br>*also:* King of the godkin | **Rìgh Chlann nan Dè** | king of the godkin, the first king's style | I-0080b | existing |

## Peoples (4)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Old Ones <br>*also:* Old Ones; Old One; the Seann-Dhaoine | **Seann-Dhaoine** | the Old Ones, the people before the Dia-thìrich | I-0010 | existing |
| the godfolk | **an Dia-shluagh** | the godfolk; lit. 'the god-host' | — | existing |
| the godkin | **Clann nan Dè** | the godkin; lit. 'the children of the gods' | I-0080b | existing |
| the fuil-ghuail <br>*also:* the coal-blooded; the coal-touched; coal-touched | **fuil-ghuail** | the coal-blooded; lit. 'coal-blood' | IV-0250 | existing |

## Houses and lines (10)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Mason's children <br>*also:* the Mason's line; the Mason's kin | **Clann a' Chlachair** | the Mason's children, the Mason's line | I-0001 | existing |
| the Children of the Question <br>*also:* Children of the Question | **Clann na Ceiste** | the Children of the Question | I-0068a | existing |
| the Inquisitors of the Mystic Coal | **Luchd-ceasnachaidh a' Ghuail Dhìomhair** | the Inquisitors of the Mystic Coal | I-0073a | existing |
| the Stone Kings <br>*also:* Stone Kings; Stone King; the list of the Stone Kings | **Rìghrean na Cloiche** | the Stone Kings; lit. 'the kings of the stone' | I-0081 | existing |
| the Red Hill <br>*also:* Red Hill; the Red Hill list | **An Cnoc Ruadh** | the Red Hill where Cathair dhearg now stands, and its line <br>*note:* ruadh chosen to keep the name clear of any "Cnoc dhearg"; the town names use the lenited lower-case qualifier | I-0083 | coined |
| the house of Muireach <br>*also:* the house of Muireach | **Sliochd Mhuirich** | the house of Muireach | II-0020 | existing |
| the house of Tormod <br>*also:* the House of Tormod | **Sliochd Thormoid** | the house of Tormod | II-0047 | existing |
| the house of Raghnall | **Sliochd Raghnaill** | the house of Raghnall | II-0048 | existing |
| the house of Ìomhar | **Sliochd Ìomhair** | the house of Ìomhar | II-0046 | existing |
| the house of Mac Ùisdein | **Taigh Mhic Ùisdein** | the house of Mac Ùisdein | V-0117 | coined |

## Faiths (9)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Rite <br>*also:* the Coal Rite; Coal Rite; the houses of the Rite | **Deas-ghnàth a' Ghuail** | the Coal Rite; lit. 'the rite of the coal' | V-0028 | coined |
| the Old Faith <br>*also:* Old Faith | **An Creideamh Sean** | the Old Faith | II-0221 | existing |
| the Old Spirits <br>*also:* Old Spirits; the Old Spirits of the Dia-thìrich | **Na Seann Spioradan** | the Old Spirits | II-0005 | existing |
| the Old Spirits of the Dia-thìrich | **Seann Spioradan nan Dia-thìreach** | the Old Spirits of the Dia-thìrich (the full name) | II-0005 | existing |
| the Church <br>*also:* Church | **An Eaglais** | the Church | IV-0001 | existing |
| the Tuathaich Church <br>*also:* the old congregations of the north coast | **Eaglais nan Tuathach** | the Tuathaich Church; the old congregations of the north coast | V-0042 | existing |
| without a faith | **gun chreideamh** | without a faith | V-0034a | existing |
| the Old Reverence <br>*also:* the old reverence; the Old Reverence and Its Parting | **An Seann Urram** | the old reverence of the hearths, before the orders parted <br>*note:* promoted | II-0221 | coined |
| the Mystery of the Grey Night | **Rùn-dìomhair na h-Oidhche Glaise** | the Mystery of the Grey Night | V-0043 | existing |

## Orders and schools (9)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the order of Brìde <br>*also:* the order of Brìde's flame | **Òrd Bhrìde** | the order of Brìde's flame | V-0028 | existing |
| the Hawk order <br>*also:* the Hawk; the Hawk houses; the Hawk-order; the hawk-houses | **Òrd an t-Seabhaig** | the Hawk order | II-0158 | existing |
| the Hungry Hawk <br>*also:* Hungry Hawk | **An Seabhag Acrach** | the Hungry Hawk | III-0062 | coined |
| the Fed Hawk <br>*also:* Fed Hawk | **An Seabhag Biadhte** | the Fed Hawk | III-0142 | coined |
| the druid schools <br>*also:* the druid school; the Two Schools; the stag's people | **Scoiltean nan Draoidhean** | the druid schools | II-0021 | existing |
| the Philosophy of the Deer <br>*also:* the Deer; the Philosophy of the Stag | **Feallsanachd an Fhèidh** | the Philosophy of the Deer, the druid schools' own name | II-0021 | existing |
| Macha's order <br>*also:* the order of Macha; the wood-watchers | **Òrd Mhacha** | the order of Macha | III-0089 | existing |
| the order of the Stone <br>*also:* the Stone's order; the houses of the Stone | **Òrd na Cloiche** | the order of the Stone | III-0086 | existing |
| Manannan's order <br>*also:* the order of Manannan; the sting-sworn | **Òrd Mhanannain** | the order of Manannan | III-0120 | existing |

## Rites (3)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Mourning Custom <br>*also:* the White Sorrow; the white sorrow; the Mourning Custom of the Sundering | **an Tùrsa Geal** | the Mourning Custom; lit. 'the white sorrow' | III-0031 | existing |
| the rite of the empty harbour <br>*also:* the empty-harbour rite; the Empty Harbour | **Deas-ghnàth a' Chalaidh Fhalaimh** | the rite of the empty harbour | III-0036 | coined |
| the Grey Night <br>*also:* Grey Night; the grey night; the vigil of the Grey Night | **Oidhche Glaise** | the Grey Night | IV-0262 | existing |

## Feasts, fairs and days (8)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the day of the empty-harbour rite | **Là an Diosail** | the day of the empty-harbour rite; lit. 'the day of the sunwise turn' | III-0127 | existing |
| the night of lamps <br>*also:* the Night of Lamps; the lamps at Seann Skell | **Oidhche nan Lòchran** | the night of lamps at Seann Skell | III-0022 | coined |
| the fair at Muileann òg <br>*also:* the Fair; the great fair | **Fèill Muileann òg** | the fair at Muileann òg | V-0088 | existing |
| the melee <br>*also:* the Còmhrag | **Còmhrag Ceann leathan** | the yearly melee at Ceann leathan; lit. 'the combat of Ceann leathan' | V-0096 | existing |
| Christmas <br>*also:* Christmas Day | **an Nollaig** | Christmas | VI-0071 | existing |
| the four feasts <br>*also:* the Four Feasts; the quarter-days; the Quarter-Days | **Na Ceithir Fèilltean** | the four quarter-feasts <br>*note:* the feasts themselves (Là Fhèill Brìde, Bealltainn, Lùnastal, Samhain) are already Dia-thìris | — | coined |
| the drowned-feast | **Fleadh a' Bhàthaidh** | the drowned-feast; lit. 'the feast of the drowning' | II-0242 | coined |
| the northern feast of the sea <br>*also:* the northern sea-feast | **Fleadh na Mara** | the northern feast of the sea at Cnoc ghorm | V-0104 | coined |

## Gods and holy powers (9)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Hawk of Acaill <br>*also:* Hawk of Acaill | **Seabhag Acaill** | the Hawk of Acaill, whom the Hawk order calls Mòd <br>*note:* seabhag is feminine in the dictionary but masculine in the canon names (Òrd an t-Seabhaig); the hawk names here follow the canon | III-0062 | coined |
| the Peaceful Goose <br>*also:* Peaceful Goose | **an Gèadh Sìtheil** | the Peaceful Goose (Sìne) | V-0043 | existing |
| the wild goose of the Spirit <br>*also:* the wild goose of the Holy Spirit | **an Gèadh Fiadhaich** | the wild goose of the Holy Spirit | IV-0262 | existing |
| the Holy Spirit <br>*also:* the Spirit | **an Spiorad Naomh** | the Holy Spirit | IV-0262 | coined |
| the Lord <br>*also:* the Lord's day | **an Tighearna** | the Lord | — | existing |
| Christ | **Crìosd** | Christ | — | existing |
| the Young God <br>*also:* Young God | **an Dia Òg** | the Young God, Caoran | I-0011a | existing |
| the Good God | **an Dagda** | the Good God, father of the gods | — | existing |
| the Monster of the Gates | **Uilebheist nan Geataichean** | the Monster of the Gates, Crom Cruaich | — | existing |

## Spirits (1)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Keeper <br>*also:* the Keeper of the Kin; the Keeper of the kin; Keeper of the Kin; the kin's keeper | **Coimhdeach na Fine** | the Keeper of the Kin; lit. 'the guardian of the kindred' | I-0011a | existing |

## Creatures of the tellings (5)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Sea-Watcher <br>*also:* the Watcher; Sea-Watcher | **Uilebheist na Mara** | the Sea-Watcher; lit. 'the monster of the sea' | I-0040 | existing |
| the Hollow Man <br>*also:* the Hollow Man of Doire uaine; Hollow Man | **Marbh-bheò** | the Hollow Man of Doire uaine; lit. 'dead-alive' | I-0045 | existing |
| the Seal Wife <br>*also:* The Seal Wife | **Bean an Ròin** | the Seal Wife | — | existing |
| the Water Horse <br>*also:* The Water Horse | **An t-Each-Uisce** | the Water Horse | — | existing |
| the Salmon of Knowledge | **Bradan an Eòlais** | the Salmon of Knowledge | — | existing |

## Coals, relics and holy things (12)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Stone | **Lia Fàil** | the Stone that cries out under the rightful king <br>*note:* "the Stone" is also short for the order (Òrd na Cloiche); choose by sense | II-0217 | existing |
| the Cup of Truth <br>*also:* Cup of Truth; Manannan's Cup; the Cup | **Cupa na Fìrinne** | Manannan's Cup of Truth | II-0086 | coined |
| the Seven Coals <br>*also:* Seven Coals; the seven coals | **na Seachd Guail** | the Seven Coals | I-0017a | existing |
| the coloured coal | **an gual dathach** | the coloured coal | I-0001 | existing |
| the black coal | **gual dubh** | the black coal, of earth | I-0038a | existing |
| the fire coal | **gual teine** | the fire coal, of fire | I-0073a | existing |
| the snowflake coal | **gual sneachda** | the snowflake coal, of air | I-0027a | existing |
| the gold coal <br>*also:* the gold-sheen coal | **gual òir** | the gold-sheen coal, of sea water | I-0017a | existing |
| the silver coal <br>*also:* the silver-sheen coal | **gual airgid** | the silver-sheen coal, of river water | I-0062a | existing |
| the mahogany coal | **gual donn-ruadh** | the mahogany coal, of life | I-0052a | existing |
| the rainbow coal | **gual bogha-froise** | the rainbow coal, of spirit | I-0080a | existing |
| the First Flame <br>*also:* First Flame | **A' Chiad Lasair** | the First Flame, Brìde's flame bound at Dùn ìseal | II-0001 | coined |

## Events used as names (18)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the First Blood among the heirs <br>*also:* the First Blood; First blood at Dùn thais; First blood among the heirs | **A' Chiad Fhuil** | the First Blood among the heirs at Dùn thais; lit. 'the first blood' <br>*note:* the Fifth Book also heads a chapter "the First Blood" for the first bloodshed between the peoples (IV-0270) | II-0001c | coined |
| the Division <br>*also:* the Roinn; the Parting of the Kingdom; the parting of the kingdom; the Division of the kin | **Roinn na Rìoghachd** | the Division; lit. 'the parting of the kingdom' | II-0001b | existing |
| the Gathering of the Heirs <br>*also:* Gathering of the Heirs | **Cruinneachadh nan Oighrean** | the Gathering of the Heirs | II-0001a | existing |
| the census of hands <br>*also:* the Census of Hands; the count of hands | **Cunntas nan Làmh** | the census of hands | II-0142 | coined |
| the measuring of the vein <br>*also:* the Measuring of the Vein | **Tomhas na Fèithe** | the measuring of the vein | II-0120 | coined |
| the Choosing <br>*also:* Choosing | **An Roghnachadh** | the Choosing; lit. 'the choosing' | III-0003 | coined |
| the Setting-Out <br>*also:* Setting-Out | **Am Falbh** | the Setting-Out; lit. 'the departure' | III-0023 | coined |
| the Sundering <br>*also:* Sundering | **a' Scaradh** | the Sundering; lit. 'the parting' | III-0023 | existing |
| the sunwise turn <br>*also:* the Sunwise Turn; the Diosal; the count of the Diosal | **An Diosal** | the sunwise turn of the departing fleet | III-0024 | existing |
| the Crossing <br>*also:* Crossing; the crossing | **An t-Aiseag** | the Crossing; lit. 'the ferrying' <br>*note:* also the sea passage itself: "the closing of the crossing" (IV-0377) | IV-0001 | coined |
| the first strike <br>*also:* the Eleven Days of Baile thais; the strike at Baile thais | **Stad-oibre Baile thais** | the first strike, at Baile thais; the Eleven Days of Baile thais | IV-0165 | coined |
| the day the pits stopped <br>*also:* the Day the Pits Stopped; the first stoppage together | **Là Stad nan Sloc** | the day the pits stopped | IV-0306 | coined |
| the Severance <br>*also:* Severance | **An Dealachadh** | the Severance; lit. 'the parting' <br>*note:* existing through Linn an Dealachaidh and the dictionary (dealachadh "severance"); E_words notes a' Scaradh is also said of it | IV-0377 | existing |
| the Depletion <br>*also:* Depletion | **An Traoghadh** | the Depletion of the vein; lit. 'the draining' | V-0105 | coined |
| the Keeper's gift | **Tìodhlac a' Choimhdich** | the Keeper's gift | IV-0144 | existing |
| the mason's fire <br>*also:* the first fire | **Teine a' Chlachair** | the mason's fire, the first fire | I-0001 | coined |
| the Forgotten Coal | **An Gual Dìochuimhnichte** | the forgotten coal of the godfolk <br>*note:* promoted | — | coined |
| the panther roads <br>*also:* the panther road; the crossing days | **Imrich nam Pantar** | the panthers' crossing | I-0078 | existing |

## Calamities (5)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Green Death <br>*also:* Green Death | **A' Phlàigh Uaine** | the Green Death; lit. 'the green plague' | IV-0152 | existing |
| the Great Hunger <br>*also:* Great Hunger | **Gorta Baile chrom** | the Great Hunger; lit. 'the famine of Baile chrom' | IV-0194 | existing |
| the Long Drought <br>*also:* Long Drought | **Tiormachd Achadh shean** | the Long Drought; lit. 'the drought of Achadh shean' | IV-0217 | existing |
| the Rending <br>*also:* the Rending of Cill ghlas | **Scàineadh Cill ghlas** | the Rending; lit. 'the splitting of Cill ghlas' | IV-0269 | existing |
| the Great Wave <br>*also:* Great Wave | **Tonn Mhòr Cnoc chaol** | the Great Wave; lit. 'the great wave of Cnoc chaol' | V-0017 | existing |

## Storms (3)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Black Wind <br>*also:* Black Wind | **A' Ghaoth Dhubh** | the Black Wind | I-0159 | existing |
| the great hate | **Am Fuath Mòr** | the great hate, the storm that drowned Seann Toll's boats | III-0066 | existing |
| the Black Laugh | **An Gàire Dubh** | the Black Laugh | III-0100 | existing |

## Seas and sea-lanes (5)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| Manannan's sea <br>*also:* the sea of Manannan | **Muir Mhanannain** | Manannan's sea, round Dia-thìr | — | existing |
| Manannan's mist <br>*also:* the mist | **Ceò Mhanannain** | Manannan's mist over the western sea | III-0239a | coined |
| the Hawk bay | **Bàgh an t-Seabhaig** | the Hawk bay | I-0116a | coined |
| the ancient sea-way | **Slighe-mhara àrsaidh** | the ancient sea-way | I-0064a | existing |
| the southern lane | **Slighe-mhara Caol fhiadhaich** | the southern sea-lane | III-0189a | existing |

## Regions and countries (11)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the land beyond <br>*also:* the Land Beyond | **an Tìr Thall** | the land beyond, the humans' homeland | IV-0007 | existing |
| the Tuathaich homeland | **Tìr-dhùthchais nan Tuathach** | the Tuathaich homeland in the north | V-0001 | coined |
| the Isle of the Blessed | **Inis nam Beannaichte** | the Isle of the Blessed | V-0042 | coined |
| the Otherworld | **An Saoghal Thall** | the Otherworld; lit. 'the world beyond' <br>*note:* Tìr nan Òg and Magh Meall are its two existing names | III-0023 | coined |
| the land of the young | **Tìr nan Òg** | the land of the young | — | existing |
| the plain of delight | **Magh Meall** | the plain of delight | — | existing |
| the windy coast <br>*also:* the Windy Coast | **an Oirthir Ghaothach** | the windy coast | V-0014a | existing |
| the Hawk coast <br>*also:* the Hawk country | **Oirthir an t-Seabhaig** | the Hawk coast | IV-0342b | coined |
| the salt shore <br>*also:* the Salt Shore | **Tràigh an t-Salainn** | the salt shore | I-0104b | coined |
| the great shares <br>*also:* the nine great shares; great shares | **na h-Earrannan Mòra** | the nine great shares of the Division | II-0001b | existing |
| the Red Share <br>*also:* Red Share | **an Earrann Dhearg** | the Red Share of Ìomhar Dearg at Dùn dhearg | II-0001b | existing |

## Landmarks (42)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Ford of Blood <br>*also:* Ford of Blood | **Àth na Fala** | the Ford of Blood, below Dùn dhearg | I-0098a | existing |
| the ford of the forty | **Àth an Dà Fhichead** | the ford of the forty, the carriers' name for Àth fhiadhaich | II-0095 | coined |
| the quay of the sunwise turn | **Cidhe an Diosail** | the quay of the sunwise turn at Seann Skell | III-0041 | existing |
| the meeting of the ships | **Coinneachadh nan Long** | the meeting of the ships | IV-0001a | existing |
| the green acre | **An Acair Uaine** | the green acre, the plague-field at Achadh dhomhain <br>*note:* acair is both "acre" and "anchor" in the dictionary; ambiguous | IV-0153 | coined |
| the ring of beacons <br>*also:* the Ring of Beacons; the five beacons | **Fàinne nan Teintean-rabhaidh** | the ring of beacons | IV-0191 | coined |
| the coal line <br>*also:* coal line | **Slighe a' Ghuail** | the coal line (the railway); lit. 'the way of the coal' | IV-0243a | coined |
| the mine road <br>*also:* the coal road | **Rathad na Mèinne** | the mine road | IV-0088a | existing |
| the drowned strand | **an Tràigh Bhàthte** | the drowned strand at old Cnoc chaol | V-0020 | existing |
| the Carters' Road | **Rathad nan Cairtearan** | the Carters' Road, the north's wool road | V-0148 | coined |
| the Tuathaich cairn | **Càrn nan Tuathach** | the Tuathaich cairn on the field of Àth leathan | VI-0130 | coined |
| the stone at Cathair mhòr <br>*also:* the stone of the regiments' dead | **Clach nan Rèisimeidean** | the stone of the regiments' dead at Cathair mhòr; lit. 'the stone of the regiments' | VI-0126 | coined |
| the house of Donn | **Taigh Dhuinn** | the house of Donn, where the dead go | — | existing |
| the Mason's Point <br>*also:* the Point | **Binnean a' Chlachair** | the Mason's Point, the island's highest summit | I-0027a | existing |
| the temple ruin | **Làrach an Teampaill** | the temple ruin | I-0035 | existing |
| the fortress | **Làrach an Dùin** | the fortress ruin | I-0033 | existing |
| the outpost | **Làrach an Dùin-fhaire** | the watch-fort ruin | I-0032 | existing |
| the column | **Calbh Cnoc ghorm** | the column at Cnoc ghorm | I-0073 | existing |
| the sacred forest at Cnoc bheag <br>*also:* the sacred forest | **Coille Naomh Cnoc bheag** | the sacred forest at Cnoc bheag | I-0051 | existing |
| the stag's grove <br>*also:* Flidais's wood; the holy wood | **Coille Naomh Muileann chiar** | the holy wood of Muileann chiar, Flidais's wood | I-0048 | existing |
| the healing water | **Allt an Àigh** | the stream of the healing water | II-0011 | existing |
| the warm springs <br>*also:* the hot springs | **Fuarain Theth Muileann ruadh** | the warm springs below Muileann ruadh | I-0057 | existing |
| the great pit <br>*also:* the Sloc Mòr; the Sloc | **An Sloc Mòr** | the great pit at the mountain | V-0051 | existing |
| the sunny house | **An Taigh-òsta Grianach** | the sunny house, a waypoint inn | II-0072 | existing |
| the golden house | **An Taigh-seinnse Òir** | the golden house, a waypoint inn | II-0082 | existing |
| the Yellow Lion | **An Leòmhann Buidhe** | the Yellow Lion, a waypoint inn | III-0073 | existing |
| the far-off house | **An Sligeanach Fad' às** | the far-off house, a waypoint inn | II-0195 | existing |
| the mausoleum at Cnoc dhìreach <br>*also:* the mausoleum; the necropolis at Cnoc dhìreach | **Tuam Cnoc dhìreach** | the mausoleum at Cnoc dhìreach | I-0075 | existing |
| the obelisk at Cnoc bheag <br>*also:* the obelisk | **Carragh Cnoc bheag** | the obelisk at Cnoc bheag | I-0069 | existing |
| the pillar at Cnoc chiar <br>*also:* the pillar | **Colbh Cnoc chiar** | the pillar at Cnoc chiar | I-0071 | existing |
| the bridge at Cathair dhearg | **Drochaid Cathair dhearg** | the bridge at Cathair dhearg | III-0071 | existing |
| the field of Muileann ghlas <br>*also:* the Muileann ghlas field | **Àraich Muileann ghlas** | the battlefield of Muileann ghlas | VI-0116 | existing |
| the field of Àth leathan | **Àraich Àth leathan** | the battlefield of Àth leathan | VI-0085 | existing |
| the meeting of the cups | **Coinneachadh nan Cupan** | the meeting of the cups | I-0154a | existing |
| the meeting on the moor road | **Coinneachadh a' Mhonaidh** | the meeting on the moor road | IV-0272a | existing |
| the crews meet on the moor | **Coinneachadh an Fhearainn** | the meeting of the crews on the moor | IV-0327a | existing |
| the meeting at the neck <br>*also:* the stone on the neck | **Coinneachadh na h-Amhaich** | the meeting at the neck | III-0167a | existing |
| the beacon at Baile ìseal <br>*also:* the light at Baile ìseal | **Taigh-solais Baile ìseal** | the lighthouse at Baile ìseal | I-0161 | existing |
| the beacon at Muileann bheag <br>*also:* the light at Muileann bheag | **Taigh-solais Muileann bheag** | the lighthouse at Muileann bheag | I-0162 | existing |
| the beacon at Àth dhearg <br>*also:* the light at Àth dhearg | **Taigh-solais Àth dhearg** | the lighthouse at Àth dhearg | I-0163 | existing |
| the beacon at Tobar dhearg <br>*also:* the light at Tobar dhearg | **Taigh-solais Tobar dhearg** | the lighthouse at Tobar dhearg | I-0164 | existing |
| the beacon on the Baile chrom headland <br>*also:* the last beacon | **Taigh-solais Baile chrom** | the lighthouse at Baile chrom | I-0041 | existing |

## Ships (1)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the three ships <br>*also:* the Three Ships; three ships | **Na Trì Longan** | the three ships of the Crossing | IV-0002 | coined |

## Documents and records (14)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the table of the ages <br>*also:* the Table of the Ages; the seven ages | **Clàr nan Aoisean** | the table of the ages | V-0078a | existing |
| the Keepers' roll <br>*also:* the Hall's roll; the Hall's list; the Keepers' count | **Clàr an Talla** | the Keepers' roll of the Hall; lit. 'the roll of the Hall' | II-0113 | coined |
| the roll of the willing | **Rolla nan Deònach** | the roll of the willing | III-0004 | coined |
| the custody-book <br>*also:* the custody book | **Leabhar a' Chùraim** | the custody-book of the vein-house | III-0006 | coined |
| the Line of Aisling <br>*also:* Line of Aisling | **Sloinneadh Aisling** | the Line of Aisling | IV-0251a | coined |
| the Moot's minutes | **Cuimhne-coinneimh an Tionail** | the Moot's minutes; lit. 'the meeting-memory of the gathering' | V-0008 | coined |
| the Library's sealed archive <br>*also:* the sealed archive | **Ciste-chuimhne Dhùinte** | the Library's sealed war archive | VI-0128 | coined |
| the royal chronicle <br>*also:* the chronicle | **Eachdraidh na Rìoghachd** | the royal chronicle of the restored kingdom | V-0078 | coined |
| the Line of the Mason <br>*also:* Line of the Mason; The Line of the Mason | **Sloinneadh a' Chlachair** | the Line of the Mason; lit. 'the pedigree of the Mason' | I-0011a | coined |
| the Keeper's riddle <br>*also:* the riddle | **Tòimhseachan a' Choimhdich** | the Keeper's riddle | I-0011a | existing |
| the king-list <br>*also:* the king-lists; the first written king-list; the written king-list | **Clàr nan Rìghrean** | the king-list; lit. 'the roll of the kings' | II-0111 | coined |
| the two lists <br>*also:* the Two Lists | **An Dà Chlàr** | the two oral king-lists, of the Stone Kings and the Red Hill | I-0245 | coined |
| Words Born from History <br>*also:* the Words Born from History | **Briathran na h-Eachdraidh** | the chronicle's list of Words Born from History; lit. 'the words of history' | — | coined |
| The Arms of the Kingdom <br>*also:* the roll of arms | **Clàr nan Suaicheantas** | the roll of arms; lit. 'the table of the badges' | V-0015b | existing |

## Books (6)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the Book of the Three Claimants <br>*also:* Book of the Three Claimants | **Leabhar nan Trì Tagraichean** | the Book of the Three Claimants | III-0117 | coined |
| the Book of the Hawk | **Leabhar an t-Seabhaig** | the Book of the Hawk | III-0065 | existing |
| the Bible <br>*also:* Bible | **am Bìoball** | the Bible | IV-0055 | existing |
| the First Canoe <br>*also:* First Canoe | **A' Chiad Churach** | the First Canoe, the voyage of Naomh Breandan | V-0042 | coined |
| the Telling of the Making <br>*also:* Telling of the Making; the Telling | **Aithris a' Chruthachaidh** | the Telling of the Making | — | existing |
| the book of Baile thais | **Leabhar Baile thais** | the book of Baile thais, the book of grievances | IV-0208 | existing |

## Titles of the books, the Atlas and the PDFs (32)

| English | Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| The Legendarium of Dia-thìr <br>*also:* The Diathir Legendarium; the Legendarium | **Leabhar nan Aoisean** | The Legendarium of Dia-thìr; lit. 'the book of the ages' | — | existing |
| The Seven Books <br>*also:* the Seven Books | **Na Seachd Leabhraichean** | The Seven Books | — | coined |
| The Tale of the Seven Ages | **Sceul nan Seachd Aoisean** | The Tale of the Seven Ages | — | coined |
| The Prologue | **An Ro-ràdh** | The Prologue | — | coined |
| The First Book <br>*also:* the First Book | **A' Chiad Leabhar** | The First Book | — | coined |
| The Second Book <br>*also:* the Second Book | **An Dàrna Leabhar** | The Second Book | — | coined |
| The Third Book <br>*also:* the Third Book | **An Treas Leabhar** | The Third Book | — | coined |
| The Fourth Book <br>*also:* the Fourth Book | **An Ceathramh Leabhar** | The Fourth Book | — | coined |
| The Fifth Book <br>*also:* the Fifth Book | **An Còigeamh Leabhar** | The Fifth Book | — | coined |
| The Sixth Book <br>*also:* the Sixth Book | **An Siathamh Leabhar** | The Sixth Book | — | coined |
| The Seventh Book <br>*also:* the Seventh Book | **An Seachdamh Leabhar** | The Seventh Book | — | coined |
| The Annals of Dia-thìr <br>*also:* the Annals; the annals | **Annalan Dia-thìr** | The Annals of Dia-thìr | — | coined |
| The Appendices | **Na Leasachaidhean** | The Appendices | — | coined |
| A Gazetteer of Dia-thìr <br>*also:* the Gazetteer | **Clàr nam Bailtean** | A Gazetteer of Dia-thìr; lit. 'the roll of the towns' | — | coined |
| The Houses of Dia-thìr | **Taighean Dia-thìr** | The Houses of Dia-thìr | — | coined |
| The Books of the Age | **Leabhraichean na h-Aoise** | The Books of the Age (an era legendarium) | — | coined |
| The Annals of the Age | **Annalan na h-Aoise** | The Annals of the Age (an era legendarium) | — | coined |
| A Gazetteer of the Age | **Bailtean na h-Aoise** | A Gazetteer of the Age (an era legendarium); lit. 'the towns of the age' | — | coined |
| Dia-thìr Atlas <br>*also:* the Atlas | **Leabhar-cruinne Dia-thìr** | the Dia-thìr Atlas; lit. 'the world-book of Dia-thìr' | — | coined |
| The Rulers and Houses of Dia-thìr <br>*also:* Appendix A | **Rìghrean agus Taighean Dia-thìr** | The Rulers and Houses of Dia-thìr (Appendix A) | — | coined |
| The Faiths of Dia-thìr <br>*also:* Appendix B | **Creideamhan Dia-thìr** | The Faiths of Dia-thìr (Appendix B) | — | coined |
| Hosts, Wars and Calamities <br>*also:* Appendix C | **Slòigh, Cogaidhean agus Doscainnean** | Hosts, Wars and Calamities (Appendix C) | — | coined |
| The Reckoning of Years <br>*also:* Appendix D | **Cunntas nam Bliadhnachan** | The Reckoning of Years (Appendix D) | — | coined |
| The Tongues and Peoples of Dia-thìr <br>*also:* Appendix F | **Cànanan agus Cinnidhean Dia-thìr** | The Tongues and Peoples of Dia-thìr (Appendix F) | — | coined |
| The Goods and Markets of Dia-thìr <br>*also:* Appendix G | **Bathar agus Margaidhean Dia-thìr** | The Goods and Markets of Dia-thìr (Appendix G) | — | coined |
| The Shires of Dia-thìr <br>*also:* Appendix H | **Siorrachdan Dia-thìr** | The Shires of Dia-thìr (Appendix H) | — | coined |
| The Land and Waters of Dia-thìr <br>*also:* Appendix I | **Tìr agus Uisceachan Dia-thìr** | The Land and Waters of Dia-thìr (Appendix I) | — | coined |
| The Arms of Dia-thìr <br>*also:* Appendix J | **Suaicheantais Dia-thìr** | The Arms of Dia-thìr (Appendix J) | — | coined |
| Fionn and the Salmon of Knowledge | **Fionn agus Bradan an Eòlais** | Fionn and the Salmon of Knowledge (a tale) | — | existing |
| How the Old Ones Left | **Mar a Dh'fhalbh na Seann-Dhaoine** | How the Old Ones Left (a tale) | — | existing |
| How Coal Came into the Blood | **Mar a Thàinig an Gual dhan Fhuil** | How Coal Came into the Blood (a tale) | — | existing |
| Why the Tuathaich Went North | **Carson a Chaidh na Tuathaich gu Tuath** | Why the Tuathaich Went North (a tale) | — | existing |

## Ambiguous cases for the lead (49)

These may be common nouns rather than names. Each has a proposed form; the build ignores them until the lead moves them into `names`.

| English | Proposed Dia-thìris | Gloss | First | Status |
|---|---|---|---|---|
| the thousandth year <br>*also:* the Thousandth Year | **Bliadhna a' Mhìle** | the thousandth year of the Landfall Era <br>*note:* ambiguous: a date, not certainly a name | III-0156 | coined |
| the sea-thieves of the north-west <br>*also:* Sea-thieves | **Spùinneadairean-mara an Iar-thuath** | the sea-thieves of the north-west <br>*note:* ambiguous: a description as much as a name; the map already has Spùinneadairean-mara markers | III-0131 | coined |
| the night-shift order <br>*also:* the Night-Shift Order | **Òrdugh na Faire-oidhche** | the night-shift order <br>*note:* ambiguous: may be a common noun | IV-0237 | coined |
| the stone cup <br>*also:* the Stone Cup | **An Cupa Cloiche** | the stone cup of the Hall <br>*note:* ambiguous: mostly lower case, an object rather than a name | I-0153 | coined |
| the waypoint houses <br>*also:* the waypoint-keepers; the roadside houses; the Houses on the Roads | **Taighean an Rathaid** | the waypoint houses of the carriers' roads <br>*note:* ambiguous: usually a common noun | II-0085 | coined |
| the road-guards | **Freiceadan nan Rathad** | the road-guards of Dùn dhearg <br>*note:* ambiguous: usually a common noun | II-0129 | coined |
| the custodians <br>*also:* the custodian houses; the custodian families | **Luchd a' Chùraim** | the custodians of the vein; lit. 'the people of the custody' <br>*note:* ambiguous: written lower case in the books | III-0006 | coined |
| the crown's riders | **Marcaichean a' Chrùin** | the crown's riders <br>*note:* ambiguous | III-0145a | coined |
| the leave to stay <br>*also:* the Leave to Stay | **Cead nan Coigreach** | the leave to stay given to the humans <br>*note:* ambiguous | IV-0005 | coined |
| the humans <br>*also:* the strangers | **na Coigrich** | the strangers, the humans <br>*note:* ambiguous: "the humans" is a common noun in the books; kept English unless the lead rules otherwise | IV-0001 | existing |
| the Mission school | **Scoil na Teachdaireachd** | the Mission school <br>*note:* ambiguous | IV-0121 | coined |
| the trading post | **Ionad-malairt Ros dhomhain** | the trading post at Ros dhomhain <br>*note:* ambiguous | IV-0012 | coined |
| the overseers <br>*also:* the Maoir; the Maoir of Muileann chrom | **na Maoir** | the overseers; lit. 'the stewards' <br>*note:* ambiguous: maor is a common noun | IV-0091 | existing |
| the constabulary <br>*also:* the constables | **Na Constabalan** | the constabulary; Merriman's constables <br>*note:* ambiguous; constabal is a dictionary loan | IV-0259 | coined |
| the grey fever | **Am Fiabhras Glas** | the grey fever <br>*note:* ambiguous: lower case in the books | IV-0276 | coined |
| the strangers' fever | **Fiabhras nan Coigreach** | the strangers' fever <br>*note:* ambiguous | IV-0034 | coined |
| the last ship from the west <br>*also:* the last ship | **An Long Mu Dheireadh** | the last ship from an Tìr Thall <br>*note:* ambiguous | IV-0368 | coined |
| the ship that sailed west | **An Long a Sheòl an Iar** | the ship that sailed west with Strake <br>*note:* ambiguous | IV-0374 | coined |
| the boundary stones | **Clachan-crìche** | the boundary stones <br>*note:* ambiguous; clachan-crìche is attested for the Roinn's stones | V-0003 | existing |
| the mint | **Taigh a' Bhuinn** | the mint at Cathair dhearg <br>*note:* ambiguous | V-0024 | coined |
| the hewers | **na Gualadairean** | the hewers, the coal-cutters of the pits <br>*note:* ambiguous: common noun | V-0060 | coined |
| the search for a second vein <br>*also:* the Search | **Sireadh na Dàrna Fèithe** | the search for a second vein <br>*note:* ambiguous | V-0176 | coined |
| the enforcers <br>*also:* the Board's enforcers | **Luchd-èigneachaidh a' Bhùird** | the Board's enforcers <br>*note:* ambiguous | VI-0065 | coined |
| the holdouts <br>*also:* the Holdouts of the Western Hills | **Na Daoine Daingeann** | the holdouts of the western towns <br>*note:* ambiguous: the Seventh Book heads a chapter with it | VI-0055 | coined |
| the plain seal | **An Seula Lom** | the plain seal of the kingdom <br>*note:* ambiguous | VI-0050 | coined |
| the hill-folk <br>*also:* the Hill-Folk | **Muinntir a' Chnuic** | the hill-folk of the vein <br>*note:* ambiguous | I-0065 | coined |
| the undying generation | **Na Daoine gun Aois** | the undying generation of the coal-blooded <br>*note:* ambiguous | IV-0146 | coined |
| the sting-oath | **Mionnan a' Ghatha** | the sting-oath of the western merchants <br>*note:* ambiguous | II-0160 | coined |
| the dawn-hawk rite <br>*also:* the dawn-hawk | **Deas-ghnàth Seabhag na Camhanaich** | the dawn-hawk rite of the north coast <br>*note:* ambiguous | II-0159 | coined |
| the ancestor rite | **Deas-ghnàth nan Sinnsearan** | the ancestor rite of the Old Spirits <br>*note:* ambiguous | II-0005 | coined |
| God | **Dia** | God, in the Church's faith <br>*note:* ambiguous: English "God" is left as is in quotations | IV-0001 | existing |
| the Bible in Dia-thìris | **Am Bìoball ann an Dia-thìris** | the Bible in Dia-thìris <br>*note:* ambiguous | — | coined |
| the shared meal <br>*also:* the shared-meal custom | **Am Biadh Roinnte** | the shared-meal custom <br>*note:* ambiguous | II-0179 | coined |
| the white stag <br>*also:* the White Stag | **An Damh Geal** | the white stag of Flidais's wood <br>*note:* ambiguous | I-0050 | coined |
| the seven lightings <br>*also:* the Seven Lightings | **Na Seachd Lasaidhean** | the seven lightings of the coals <br>*note:* ambiguous | — | coined |
| the misstrike <br>*also:* Cormac of the Misstrike | **An Droch Bhuille** | the misstrike that lit the mahogany coal <br>*note:* ambiguous | I-0052a | coined |
| the slab | **An Leac** | the slab over the burnt vein <br>*note:* ambiguous | I-0003 | coined |
| the vein <br>*also:* the Vein | **An Fhèith** | the vein of coloured coal <br>*note:* ambiguous: a common noun in most places; Linn na Fèithe is built on it | I-0001 | coined |
| the famine country | **Dùthaich na Gorta** | the famine country <br>*note:* ambiguous | IV-0195a | coined |
| the dry country | **An Dùthaich Thioram** | the drought country <br>*note:* ambiguous | IV-0219 | coined |
| the vein country | **Dùthaich na Fèithe** | the vein country <br>*note:* ambiguous | — | coined |
| the country of the Stone | **Dùthaich na Cloiche** | the country of the Stone in the south-west <br>*note:* ambiguous | — | coined |
| the stair under the hill <br>*also:* the Stair | **Staidhre Toll-dubh** | the stair at Toll-dubh <br>*note:* ambiguous | III-0149 | coined |
| the letter-books | **Leabhraichean-litreach an Riaghaltais** | the Administration's letter-books <br>*note:* ambiguous | IV-0376 | coined |
| the Administration's register | **Clàr an Riaghaltais** | the Administration's register <br>*note:* ambiguous | IV-0252 | coined |
| the great gathering at the ford <br>*also:* the Great Gathering; the ford gathering | **An Tional Mòr** | the great gathering at the ford <br>*note:* ambiguous | I-0208a | coined |
| the northern concession <br>*also:* the concession towns | **Ceadachd a' Chinn a Tuath** | the humans' northern concession <br>*note:* ambiguous | IV-0060 | coined |
| the eastern pirates <br>*also:* the pirates | **Spùinneadairean-mara an Ear** | the eastern pirates <br>*note:* ambiguous: spùinneadair-mara is a common noun; the map's markers are named Spùinneadairean-mara | IV-0108 | existing |
| the first war | **A' Chiad Chogadh** | the first war (the War of the Roads) <br>*note:* ambiguous | II-0093 | coined |
