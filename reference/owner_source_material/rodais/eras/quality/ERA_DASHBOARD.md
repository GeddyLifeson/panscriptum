# Era dashboard

Written by `eras/quality/era_policy.py` on 2026-09-26 00:21. Targets from `check_era.py`: entries 500-800, pages 500-600, words annals 30,000-45,000, books 170,000-200,000, gazetteer 10,000-15,000, appendices 10,000-20,000.

| Age | check_era | files | entries | pages | annals | books | gazetteer | appendices | tells /10k | English names | misspelt |
|---|---|---|---|---|---|---|---|---|---|---|---|
| V | HOLDS | 69 | 523 ok | 592 ok | 30,999 ok | 196,764 ok | 10,249 ok | 10,230 ok | 1.3 (28 in 222,316 words) | 1447 | 7 |

## Coverage of era events

| Age | era events | links | threads | people | category | told_in | master events with a category |
|---|---|---|---|---|---|---|---|
| V | 120 | 114/120 (95%) | 65/120 (54%) | 119/120 (99%) | 120/120 (100%) | 120/120 (100%) | 0/403 (0%) |

## check_era failures and notes

**Age V, The Age of Strangers**
- note EV-4501: its window ([93, 93]) cannot hold between its master neighbours (years 1873..1873); spread evenly instead
- note 403 master events have no category yet (the master pass gives them one)
- note proper noun in English: Dunstan's rule (write Riaghailt Dunstan) in EV-5001
- note proper noun in English: Dunstan's rule (write Riaghailt Dunstan) in book/28_of_the_law_of_one_line.md
- note proper noun in English: Dunstan's rule (write Riaghailt Dunstan) in gazetteer/09_the_cellar_and_the_night_crews.json
- note proper noun in English: Macha's order (write Òrd Mhacha) in appendices/B_faiths.md
- note proper noun in English: Macha's order (write Òrd Mhacha) in book/22_of_the_priced_silver_and_the_blessed_coin.md
- note proper noun in English: Macha's order (write Òrd Mhacha) in book/36_of_the_breaking_of_the_staff.md
- ... 34 more notes (python check_era.py V)

