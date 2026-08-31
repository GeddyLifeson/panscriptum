# OVERWATCH

round 233  ·  last run 2026-08-31 04:12

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 283,526 inspected (deep scan as of round 229)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**14 open** (2 high). Newest first.

- **pipeline.py** `merged` — [HIGH] initially set to `rec` and only becomes the disk-merged version if the read succeeds
  - says: carries the caller's fresh per-entry judgments
- **pipeline.py** `phase_chain` — [HIGH] This function is not implemented and causes the runner to stop at phase 4 because the function is missing.
  - says: Phase 4 -- the Chain of Defeats. See chain.py for the reasoning.
- **profile.py** `encode` — [MEDIUM] the code does something else
  - says: the code says it does
- **pipeline.py** `write_record` — [MEDIUM] write_record is called without checking if the write actually reached the disk
  - says: A batch is done only when every entry in it carries a result AND the write that carries those results actually reached the disk
- **pipeline.py** `pairs` — [MEDIUM] the list comprehension filters out entries with weight below the threshold (if v >= thr)
  - says: the WHOLE list is included (Hard Rule 0)
- **pipeline.py** `drift` — [MEDIUM] can be 'count', 'content', or None
  - says: indicates a drift by content
- **pipeline.py** `merged` — [MEDIUM] initialised to `rec` and overwritten by `disk` if merge succeeds
  - says: carries the caller's fresh per-entry judgments
- **pick_model.py** `refused` — [MEDIUM] keeps the tuples of (score, model) for models refused for VRAM
  - says: keeps the models refused for VRAM
- **physics.py** `main` — [MEDIUM] returns 0 unconditionally
  - says: the main function
- **magnitude.py** `assay_entity` — [MEDIUM] returns a deferred status when the anchor is not in the ladder
  - says: assays an entity by trying different methods
- **identity.py** `identify` — [MEDIUM] Returns `(base, continuity)` only if `desig` is in `continuities`
  - says: Return `(base, continuity)` for a resolved wiki title.
- **hostcheck.py** `score` — [MEDIUM] score is called with by=by, but the by parameter is already passed as by[src], making the by=by redundant and possibly incorrect
  - says: score(host, by[src], src, by=by)
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops
- **foreman.py** `kill_stalled` — [MEDIUM] kill stalled jobs that can be restarted, and escalate those that cannot
  - says: kill stalled jobs

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
