# OVERWATCH

round 566  ·  last run 2026-09-16 08:19

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 305,767 inspected (deep scan as of round 565)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** feats.py --roll

## What the model found in the code

**6 open** (2 high). Newest first.

- **catalogue_web.py** `save_roll` — [HIGH] does not limit the merge to those sources' rows; instead, it merges all rows of the caller's copy
  - says: -> True if the write landed. `names` limits the merge to those sources' rows.
- **assay.py** `assay` — [HIGH] Computes a Moth Number but the formula is incorrect due to missing covariance terms and incorrect variance calculation
  - says: Compute a Moth Number: 𝔄 = M_a + (sum w_i * s_i) / 10
- **endpoint.py** `source_pages` — [MEDIUM] returns [] when the file is absent and raises `PagesRegistryUnreadable` when the file is unreadable
  - says: RAISES `PagesRegistryUnreadable` WHEN THE REGISTRY CANNOT BE READ, and never answers [] for it
- **codewatch.py** `main` — [MEDIUM] the main function is called via raise SystemExit(main())
  - says: the main function
- **catalogue_web.py** `catalogue_composite` — [MEDIUM] Catalogues a cross-media source by merging named categories from several wikis, but the function does not actually merge categories; it processes each sub-wiki's categories separately and aggregates the results without merging them into a single unified list.
  - says: Catalogue a cross-media source by merging named categories from several wikis.
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
