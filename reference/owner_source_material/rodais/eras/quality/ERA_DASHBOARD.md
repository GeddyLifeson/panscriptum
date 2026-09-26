# Era dashboard

Written by `eras/quality/era_policy.py` on 2026-09-26 01:47. Targets from `check_era.py`: entries 800-1500, pages 500-, words annals 30,000-45,000, books 170,000-200,000, gazetteer 10,000-15,000, appendices 10,000-20,000.

| Age | check_era | files | entries | pages | annals | books | gazetteer | appendices | tells /10k | English names | misspelt |
|---|---|---|---|---|---|---|---|---|---|---|---|
| I | HOLDS | 61 | 831 ok | 569 ok | 50,367 HIGH | 172,186 ok | 10,593 ok | 10,569 ok | 2.2 (50 in 229,936 words) | 385 | 0 |
| II | HOLDS | 71 | 806 ok | 569 ok | 50,531 HIGH | 172,527 ok | 10,478 ok | 10,350 ok | 1.2 (27 in 225,932 words) | 173 | 0 |
| III | HOLDS | 59 | 815 ok | 609 ok | 53,134 HIGH | 185,360 ok | 10,405 ok | 11,743 ok | 1.6 (38 in 236,184 words) | 0 | 0 |
| IV | HOLDS | 63 | 811 ok | 566 ok | 48,828 HIGH | 170,379 ok | 11,280 ok | 11,956 ok | 1.2 (26 in 220,882 words) | 1 | 0 |
| V | HOLDS | 70 | 925 ok | 658 ok | 59,511 HIGH | 197,122 ok | 16,326 HIGH | 11,231 ok | 1.2 (30 in 253,274 words) | 0 | 0 |
| VI | HOLDS | 59 | 814 ok | 581 ok | 51,435 HIGH | 171,379 ok | 12,929 ok | 14,449 ok | 1.7 (38 in 228,632 words) | 411 | 15 |
| VII | HOLDS | 71 | 812 ok | 619 ok | 48,605 HIGH | 193,072 ok | 10,577 ok | 11,407 ok | 1.7 (42 in 246,220 words) | 662 | 0 |

## Coverage of era events

| Age | era events | links | threads | people | category | told_in | master events with a category |
|---|---|---|---|---|---|---|---|
| I | 739 | 679/739 (92%) | 455/739 (62%) | 391/739 (53%) | 739/739 (100%) | 739/739 (100%) | 0/92 (0%) |
| II | 620 | 620/620 (100%) | 404/620 (65%) | 456/620 (74%) | 620/620 (100%) | 620/620 (100%) | 0/186 (0%) |
| III | 553 | 534/553 (97%) | 385/553 (70%) | 79/553 (14%) | 553/553 (100%) | 553/553 (100%) | 0/262 (0%) |
| IV | 557 | 529/557 (95%) | 331/557 (59%) | 444/557 (80%) | 557/557 (100%) | 557/557 (100%) | 0/254 (0%) |
| V | 522 | 515/522 (99%) | 294/522 (56%) | 451/522 (86%) | 522/522 (100%) | 522/522 (100%) | 0/403 (0%) |
| VI | 561 | 561/561 (100%) | 380/561 (68%) | 51/561 (9%) | 561/561 (100%) | 561/561 (100%) | 0/253 (0%) |
| VII | 646 | 646/646 (100%) | 626/646 (97%) | 457/646 (71%) | 646/646 (100%) | 646/646 (100%) | 0/166 (0%) |

## check_era failures and notes

**Age I, The Ancient Age**
- note 92 master events have no category yet (the master pass gives them one)
- note proper noun in English: the Keeper (write Coimhdeach na Fine) in book/08_of_the_keeper_in_the_grove.md
- note proper noun in English: the Keeper (write Coimhdeach na Fine) in book/28_of_the_warm_springs_and_the_walled_gate.md
- note proper noun in English: the Keeper (write Coimhdeach na Fine) in book/30_of_eoghann_at_the_river.md
- note proper noun in English: the Mason (write An Clachair) in book/01_of_the_mason_and_the_lightning.md
- note proper noun in English: the Old Ones (write Seann-Dhaoine) in appendices/B_the_telling_the_riddle_and_the_lightings.md
- note proper noun in English: the Old Ones (write Seann-Dhaoine) in appendices/D_the_peoples_of_the_shore_and_the_hills.md
- note proper noun in English: the Stone (write Lia Fàil) in EI-3040
- ... 33 more notes (python check_era.py I)

**Age II, The Age of Ailean**
- note annals_dated.json is older than the sources: run build_era.py II
- note 186 master events have no category yet (the master pass gives them one)
- note proper noun in English: the Black Wind (write A' Ghaoth Dhubh) in book/26_black_wind_and_five_fires.md
- note proper noun in English: the Hollow Man (write Marbh-bheò) in book/29_of_the_panther_road_and_the_edge_of_the_woods.md
- note proper noun in English: the Keeper (write Coimhdeach na Fine) in book/01_the_seven_nights.md
- note proper noun in English: the Keeper (write Coimhdeach na Fine) in front.json
- note proper noun in English: the Line of the Mason (write Sloinneadh a' Chlachair) in appendices/A_rulers.md
- note proper noun in English: the Mason (write An Clachair) in appendices/A_rulers.md
- ... 34 more notes (python check_era.py II)

**Age III, The Holy Age**
- note 262 master events have no category yet (the master pass gives them one)
- note proper noun in English: the Binding (write An Ceangal) in appendices/B_flame_and_companies.md
- note proper noun in English: the Binding (write An Ceangal) in book/03_of_the_binding_of_the_first_flame.md
- note proper noun in English: the Binding (write An Ceangal) in book/08_of_beathag_bhan.md
- note proper noun in English: the Binding of the First Flame (write Ceangal na Ciad Lasrach) in book/03_of_the_binding_of_the_first_flame.md
- note proper noun in English: the Choosing (write An Roghnachadh) in book/37_of_the_shut_hall_and_the_choosing_of_gilleasbuig.md
- note proper noun in English: the First Flame (write A' Chiad Lasair) in book/03_of_the_binding_of_the_first_flame.md
- note proper noun in English: the Four Houses (write Na Ceithir Taighean) in book/17_of_eilidh_nic_iomhair_and_the_four_houses.md
- ... 33 more notes (python check_era.py III)

**Age IV, The Age of Sundering**
- note 254 master events have no category yet (the master pass gives them one)
- note proper noun in English: the Book of the Three Claimants (write Leabhar nan Trì Tagraichean) in book/25_of_the_book_of_the_three_claimants.md
- note proper noun in English: the Choosing (write An Roghnachadh) in book/01_of_the_three_crews.md
- note proper noun in English: the Crown (write An Crùn) in book/29_of_the_crown_joined_to_the_vein.md
- note proper noun in English: the Hall (write Talla na Lasrach) in book/01_of_the_three_crews.md
- note proper noun in English: the Hall (write Talla na Lasrach) in book/03_of_the_queens_word_and_the_queens_sister.md
- note proper noun in English: the Hall (write Talla na Lasrach) in book/25_of_the_book_of_the_three_claimants.md
- note proper noun in English: the Hall (write Talla na Lasrach) in book/27_of_the_bargain_of_the_counts.md
- ... 33 more notes (python check_era.py IV)

**Age V, The Age of Strangers**
- note EV-4501: its window ([93, 93]) cannot hold between its master neighbours (years 1873..1873); spread evenly instead
- note 403 master events have no category yet (the master pass gives them one)
- note proper noun in English: Dunstan's rule (write Riaghailt Dunstan) in appendices/E_words.md
- note proper noun in English: the Administration (write Riaghaltas nan Coigreach) in appendices/E_words.md
- note proper noun in English: the Anchor Era (write Linn an Acair) in appendices/E_words.md
- note proper noun in English: the Bible (write am Bìoball) in appendices/E_words.md
- note proper noun in English: the Commissioner (write An t-Àrd-mhaor) in appendices/E_words.md
- note proper noun in English: the Company (write A' Chompanaidh) in appendices/E_words.md
- ... 34 more notes (python check_era.py V)

**Age VI, The Age of the Kingdom**
- note annals_dated.json is older than the sources: run build_era.py VI
- note 253 master events have no category yet (the master pass gives them one)
- note proper noun in English: the Administration (write Riaghaltas nan Coigreach) in EVI-5018
- note proper noun in English: the Administration (write Riaghaltas nan Coigreach) in book/27_of_the_silver_at_depth.md
- note proper noun in English: the Carters' Road (write Rathad nan Cairtearan) in book/29_of_the_carters_road.md
- note proper noun in English: the Church (write An Eaglais) in appendices/B_faiths_orders.md
- note proper noun in English: the Company (write A' Chompanaidh) in book/09_of_the_justices_circuit.md
- note proper noun in English: the Company (write A' Chompanaidh) in book/12_of_the_sloc_mor.md
- ... 34 more notes (python check_era.py VI)

**Age VII, The Age of Dubhan**
- note 166 master events have no category yet (the master pass gives them one)
- note proper noun in English: Christmas (write an Nollaig) in book/20_of_ruth_calders_letter.md
- note proper noun in English: the Age of Dubhan (write An Aois Dhubhain) in appendices/D_faiths.md
- note proper noun in English: the Company (write A' Chompanaidh) in book/18_of_the_leoid_ruling.md
- note proper noun in English: the Crossing (write An t-Aiseag) in EVII-5527
- note proper noun in English: the Crossing (write An t-Aiseag) in book/22_of_the_old_names_read_aloud.md
- note proper noun in English: the Dubhan Era (write Linn an Dubhain) in appendices/E_words.md
- note proper noun in English: the Grey Night (write Oidhche Glaise) in appendices/D_faiths.md
- ... 33 more notes (python check_era.py VII)

