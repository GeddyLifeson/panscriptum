# Era dashboard

Written by `eras/quality/era_policy.py` on 2026-09-26 01:43. Targets from `check_era.py`: entries 800-1500, pages 500-, words annals 30,000-45,000, books 170,000-200,000, gazetteer 10,000-15,000, appendices 10,000-20,000.

| Age | check_era | files | entries | pages | annals | books | gazetteer | appendices | tells /10k | English names | misspelt |
|---|---|---|---|---|---|---|---|---|---|---|---|
| III | HOLDS | 59 | 815 ok | 609 ok | 53,134 HIGH | 185,360 ok | 10,405 ok | 11,743 ok | 1.6 (38 in 236,184 words) | 0 | 0 |

## Coverage of era events

| Age | era events | links | threads | people | category | told_in | master events with a category |
|---|---|---|---|---|---|---|---|
| III | 553 | 534/553 (97%) | 385/553 (70%) | 97/553 (18%) | 553/553 (100%) | 553/553 (100%) | 0/262 (0%) |

## check_era failures and notes

**Age III, The Holy Age**
- note annals_dated.json is older than the sources: run build_era.py III
- note 262 master events have no category yet (the master pass gives them one)
- note proper noun in English: the Binding (write An Ceangal) in appendices/B_flame_and_companies.md
- note proper noun in English: the Binding (write An Ceangal) in book/03_of_the_binding_of_the_first_flame.md
- note proper noun in English: the Binding (write An Ceangal) in book/08_of_beathag_bhan.md
- note proper noun in English: the Binding of the First Flame (write Ceangal na Ciad Lasrach) in book/03_of_the_binding_of_the_first_flame.md
- note proper noun in English: the Choosing (write An Roghnachadh) in book/37_of_the_shut_hall_and_the_choosing_of_gilleasbuig.md
- note proper noun in English: the First Flame (write A' Chiad Lasair) in book/03_of_the_binding_of_the_first_flame.md
- ... 34 more notes (python check_era.py III)

