# Era dashboard

Written by `eras/quality/era_policy.py` on 2026-09-25 18:02. Targets from `check_era.py`: entries 1200-1800, pages 500-600, words annals 90,000-130,000, books 100,000-130,000, gazetteer 40,000-60,000, appendices 30,000-50,000.

| Age | check_era | files | entries | pages | annals | books | gazetteer | appendices | tells /10k | English names | misspelt |
|---|---|---|---|---|---|---|---|---|---|---|---|
| I | HOLDS | 0 | 92 low | 19 low | 5,371 low | 0 low | 0 low | 0 low | 0.0 (0 in 0 words) | 0 | 0 |
| II | HOLDS | 0 | 186 low | 28 low | 10,028 low | 0 low | 0 low | 0 low | 0.0 (0 in 0 words) | 0 | 0 |
| III | HOLDS | 0 | 262 low | 40 low | 16,316 low | 0 low | 0 low | 0 low | 0.0 (0 in 0 words) | 0 | 0 |
| IV | HOLDS | 0 | 254 low | 35 low | 13,531 low | 0 low | 0 low | 0 low | 0.0 (0 in 0 words) | 0 | 0 |
| V | HOLDS | 0 | 403 low | 51 low | 22,571 low | 0 low | 0 low | 0 low | 0.0 (0 in 0 words) | 0 | 0 |
| VI | HOLDS | 0 | 253 low | 36 low | 14,121 low | 0 low | 0 low | 0 low | 0.0 (0 in 0 words) | 0 | 0 |
| VII | HOLDS | 0 | 166 low | 26 low | 8,814 low | 0 low | 0 low | 0 low | 0.0 (0 in 0 words) | 0 | 0 |

Ages with no `book/` files yet (I, II, III, IV, V, VI, VII): `check_era.section_words()` then counts the annals a second time as books (its books slice opens at the first "# The " heading, which is "# The Annals of the Age"), so their books and pages figures are too high until a Book exists.

## Coverage of era events

| Age | era events | links | threads | people | category | told_in | master events with a category |
|---|---|---|---|---|---|---|---|
| I | 0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/92 (0%) |
| II | 0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/186 (0%) |
| III | 0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/262 (0%) |
| IV | 0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/254 (0%) |
| V | 0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/403 (0%) |
| VI | 0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/253 (0%) |
| VII | 0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/166 (0%) |

## check_era failures and notes

**Age I, The Ancient Age**
- note 92 master events have no category yet (the master pass gives them one)

**Age II, The Age of Ailean**
- note 186 master events have no category yet (the master pass gives them one)

**Age III, The Holy Age**
- note 262 master events have no category yet (the master pass gives them one)

**Age IV, The Age of Sundering**
- note 254 master events have no category yet (the master pass gives them one)

**Age V, The Age of Strangers**
- note 403 master events have no category yet (the master pass gives them one)

**Age VI, The Age of the Kingdom**
- note 253 master events have no category yet (the master pass gives them one)

**Age VII, The Age of Dubhan**
- note 166 master events have no category yet (the master pass gives them one)

