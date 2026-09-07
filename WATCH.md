# OVERWATCH

round 409  ·  last run 2026-09-07 01:24

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 298,265 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**8 open** (2 high). Newest first.

- **cleanup.py** `low_pref` — [HIGH] returns a single match as 'prefix' but the comment says it should be 'prefix-ambiguous'
  - says: finds a proper prefix with one match
- **chain.py** `main` — [HIGH] Does not handle the case where 'fit' returns an error and the edges are not written to the result file
  - says: Handles command line arguments and processes data accordingly.
- **chain.py** `fit` — [MEDIUM] Returns the result of RG.bradley_terry, which may not include Ford's condition check
  - says: Bradley-Terry over the recorded outcomes, with Ford's condition reported either way.
- **catalogue_models.py** `sweep` — [MEDIUM] reports truncated stale model references
  - says: reports stale model references
- **catalog.py** `cmd_address` — [MEDIUM] returns 0 on hit, 1 on miss
  - says: -> rc. A MISS IS rc=1 (order 3f4d2d058fdc). See main().
- **binding_health.py** `F.page_looks_real` — [MEDIUM] judge page as real document
  - says: judge page as real article
- **binding_health.py** `F.fetch` — [MEDIUM] fetch host and list of titles
  - says: fetch host and title
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
