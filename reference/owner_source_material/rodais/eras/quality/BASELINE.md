# Quality baseline

Taken 2026-09-25 with the tools in this folder, before any era writer file exists. Re-run them to compare.

```
python tells_scan.py master --hits 0
python names_check.py master --hits 0
python era_policy.py            # writes ERA_DASHBOARD.md
python ask.py --rebuild
```

## Master legendarium (legendarium/)

Tells: 105 in 254,469 words, 4.1 per 10k words. English proper nouns where NAMES.json has a Dia-thìris form: 6714. Dia-thìris forms with wrong case, accents or a doubled article: 80. NAMES.json and THREADS.json dt forms failing `normalize()`: 0.

| file | words | tells /10k | not-X-but-Y | summing-up | record-hedging | modern-word | participle-tail | dash-and | repeated-opener | dashes /1k | over-used | English names | misspelt |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| annals/age_I.json | 4,344 | 0.0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 |  | 87 | 0 |
| annals/age_II.json | 8,018 | 3.7 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0.0 |  | 119 | 0 |
| annals/age_III.json | 13,553 | 2.2 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0.0 |  | 313 | 1 |
| annals/age_IV.json | 10,833 | 0.9 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0.0 |  | 230 | 2 |
| annals/age_V.json | 18,426 | 1.6 | 0 | 0 | 0 | 2 | 0 | 0 | 1 | 0.0 |  | 506 | 0 |
| annals/age_VI.json | 11,447 | 2.6 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0.0 |  | 317 | 26 |
| annals/age_VII.json | 7,086 | 0.0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 |  | 239 | 6 |
| book/age_I.md | 7,445 | 8.1 | 0 | 0 | 1 | 0 | 0 | 0 | 5 | 0.3 | itself 10.7 | 111 | 0 |
| book/age_II.md | 12,487 | 8.0 | 6 | 0 | 0 | 0 | 0 | 0 | 4 | 0.2 |  | 127 | 0 |
| book/age_III.md | 15,932 | 4.4 | 3 | 0 | 0 | 0 | 0 | 0 | 4 | 0.1 |  | 329 | 1 |
| book/age_IV.md | 9,455 | 2.1 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0.2 |  | 183 | 3 |
| book/age_V.md | 15,647 | 3.2 | 1 | 0 | 0 | 1 | 0 | 0 | 3 | 0.1 |  | 338 | 2 |
| book/age_VI.md | 6,830 | 4.4 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0.3 |  | 183 | 11 |
| book/age_VII.md | 4,939 | 0.0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.4 |  | 120 | 1 |
| book/creation.md | 4,590 | 21.8 | 1 | 0 | 0 | 0 | 0 | 0 | 9 | 0.2 |  | 74 | 0 |
| appendices/A_rulers.md | 7,885 | 3.8 | 0 | 0 | 2 | 1 | 0 | 0 | 0 | 0.3 |  | 310 | 2 |
| appendices/B_faiths.md | 12,200 | 6.6 | 1 | 0 | 2 | 2 | 0 | 0 | 3 | 0.1 | itself 11.5 | 427 | 2 |
| appendices/C_hosts_wars.md | 6,896 | 2.9 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0.1 |  | 236 | 0 |
| appendices/D_reckoning.md | 7,594 | 5.3 | 1 | 0 | 2 | 0 | 0 | 0 | 1 | 0.1 |  | 317 | 11 |
| appendices/E_words.md | 6,498 | 3.1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 11.2 |  | 263 | 4 |
| appendices/F_tongues_peoples.md | 7,131 | 9.8 | 1 | 0 | 6 | 0 | 0 | 0 | 0 | 0.1 |  | 166 | 1 |
| appendices/G_trade.md | 5,321 | 7.5 | 1 | 0 | 0 | 0 | 0 | 0 | 3 | 10.1 |  | 74 | 2 |
| appendices/H_shires.md | 4,972 | 2.0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0.2 |  | 245 | 1 |
| appendices/I_land.md | 3,523 | 2.8 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0.3 |  | 51 | 0 |
| appendices/J_arms.md | 4,656 | 0.0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.2 |  | 72 | 0 |
| gazetteer/out_0.json | 13,070 | 4.6 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0.0 | quiet 36.7 | 502 | 3 |
| gazetteer/out_1.json | 11,733 | 3.4 | 0 | 0 | 0 | 1 | 0 | 0 | 3 | 0.0 |  | 440 | 1 |
| gazetteer/out_2.json | 11,958 | 5.9 | 3 | 0 | 0 | 3 | 0 | 0 | 1 | 0.0 |  | 335 | 0 |

Most frequent English names left standing (the master predates NAMES.json, so these are expected until a names pass):

- the Holy Age -> An Aois Naomh: 281
- the Company -> A' Chompanaidh: 192
- the Severance -> An Dealachadh: 181
- the Age of Strangers -> An Aois Choigreach: 145
- the Hall -> Talla na Lasrach: 142
- the Old Faith -> An Creideamh Sean: 139
- the Company's -> A' Chompanaidh: 132
- the Seann-Dhaoine -> Seann-Dhaoine: 128
- the Old Spirits -> Na Seann Spioradan: 125
- the druid schools -> Scoiltean nan Draoidhean: 119

Notes on reading the numbers:

- Most master `repeated-opener` hits are POV runs in the books ("He… He… He…") and are a judgement call, not errors.
- E_words (11.2 dashes per 1k) and G_trade (10.1) are the only files with a heavy dash habit; table rows are not counted.
- `misspelt` is mostly an English "the" before a name that carries its own article ("the Seann Spioradan" for Na Seann Spioradan, "the Diosal"), plus a few case slips ("earrannan mòra").

## Eras (eras/age_I … age_VII)

No writer files yet: every age holds only its master seed, so tells and names are 0 and era-event coverage is 0/0. `check_era.py` holds for all seven ages. Every age is under target (entries 92–403 against 1,200–1,800; about 33–107 pages against 500–600). None of the 1,616 master events has a category yet. See ERA_DASHBOARD.md.

Known quirk in `check_era.section_words()`: with no `book/` files, the books slice starts at "# The Annals of the Age", so the annals are counted twice (books = annals, and the page estimate is too high). The dashboard says so; check_era.py is not changed here.

## Search index

`rodos.sqlite`: 2715 rows (master and era annals, books and appendices by section, houses, gazetteers, NAMES, PEOPLE, THREADS).
