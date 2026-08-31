# OVERWATCH

round 237  ·  last run 2026-08-31 07:47

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 284,847 inspected (deep scan as of round 235)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**12 open** (1 high). Newest first.

- **read.py** `priority` — [HIGH] Sorts by own-page size and yield_per_chunk, not depth first
  - says: Depth first, because depth is what the model is actually better at.
- **scout.py** `prev.append` — [MEDIUM] Appends to the in‑memory list but never writes the log to disk, so the log write is not gated nor persisted.
  - says: GATED, exactly as the `_mutate` call twenty lines above already is.
- **scout.py** `EP.register` — [MEDIUM] has a handler that logs the error and continues, so the whole cycle does not take down
  - says: This call had no handler, and neither does `sweep()`'s loop, so one raise took down the WHOLE CYCLE rather than one source
- **scout.py** `EP.register` — [MEDIUM] raises an exception which is caught and logged, but the source is still marked as hostless and will be re-scouted
  - says: NOT reported as a success: the URLs passed verification and the registry does not have them, so the source stays hostless and will be re-scouted, which is the correct self-healing outcome as long as the log says why.
- **rosetta.py** `silence.write_json` — [MEDIUM] writes JSON to a file but the code around it suggests it should be used to overwrite existing files, but the function's behavior is not clearly defined in the code
  - says: writes JSON to a file
- **resync_roll.py** `main` — [MEDIUM] the exit code is the number the scheduler actually looks at
  - says: the exit code is the number the scheduler actually looks at
- **repass_bands.py** `if PL.write_record(path, rec):` — [MEDIUM] The code checks the return value of `write_record`; it only appends to `touched` when the write succeeds, contrary to the comment
  - says: `write_record` return value is ignored and `touched` is always appended, causing the run to count rewritten records even when the write failed
- **read.py** `_card_gate` — [MEDIUM] It only checks/acquires _GATE_LOCAL, but the docstring and logic imply it should handle the gate returned by _gate(), which could be _GATE_CLOUD.
  - says: Hold one of the card's GATE_LOCAL_N permits -- unless this thread already holds one.
- **profile.py** `encode` — [MEDIUM] the code does something else
  - says: the code says it does
- **pipeline.py** `write_record` — [MEDIUM] write_record is called without checking if the write actually reached the disk
  - says: A batch is done only when every entry in it carries a result AND the write that carries those results actually reached the disk
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops
- **foreman.py** `kill_stalled` — [MEDIUM] kill stalled jobs that can be restarted, and escalate those that cannot
  - says: kill stalled jobs

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
