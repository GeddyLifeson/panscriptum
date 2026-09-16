# OVERWATCH

round 565  ·  last run 2026-09-16 06:33

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 305,767 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**11 open** (3 high). Newest first.

- **catalogue_web.py** `save_roll` — [HIGH] does not limit the merge to those sources' rows; instead, it merges all rows of the caller's copy
  - says: -> True if the write landed. `names` limits the merge to those sources' rows.
- **cascade_bridge.py** `prove` — [HIGH] Send one tiny call to a single bucket (the pinned one) and record which actually answer.
  - says: Send one tiny call to EVERY bucket and record which actually answer.
- **assay.py** `assay` — [HIGH] Computes a Moth Number but the formula is incorrect due to missing covariance terms and incorrect variance calculation
  - says: Compute a Moth Number: 𝔄 = M_a + (sum w_i * s_i) / 10
- **completeness.py** `probe_failures` — [MEDIUM] is not passed here and is hardcoded to len(probes)
  - says: is passed to track probe failures
- **codewatch.py** `main` — [MEDIUM] the main function is called via raise SystemExit(main())
  - says: the main function
- **catalogue_web.py** `catalogue_composite` — [MEDIUM] Catalogues a cross-media source by merging named categories from several wikis, but the function does not actually merge categories; it processes each sub-wiki's categories separately and aggregates the results without merging them into a single unified list.
  - says: Catalogue a cross-media source by merging named categories from several wikis.
- **cascade_bridge.py** `ask` — [MEDIUM] ask is called with max_attempts=1 but the code does not ensure only one candidate is tested as the function may still process multiple candidates if they are available
  - says: ask is called with max_attempts=1 to ensure only one candidate is tested
- **cascade_bridge.py** `record_unrecognised` — [MEDIUM] record_unrecognised is called with a key and a message, but the key is a bucket name that may not be resolved, leading to incorrect categorization of unparseable replies
  - says: record_unrecognised is called with a key and a message
- **catalogue_codex.py** `roll_landed` — [MEDIUM] roll_landed is used to determine if a write was denied
  - says: the code says it does not matter if the roll is updated
- **catalogue_aurora.py** `update_rows` — [MEDIUM] the function is called but its return value is not used
  - says: COMPARE-AND-SWAP, BECAUSE ATOMIC WAS NEVER THE PROPERTY THIS NEEDED
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
