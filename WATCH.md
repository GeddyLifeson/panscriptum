# OVERWATCH

round 235  ·  last run 2026-08-31 06:02

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 284,847 inspected
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**16 open** (5 high). Newest first.

- **recover_folder_records.py** `roll_by_name` — [HIGH] roll_by_name is used to access entries that are supposed to be derived from the record folder, but it's actually being used as a source of truth for the record entries
  - says: THE ROLL IS A SNAPSHOT; THE RECORD FOLDER IS THE TRUTH.
- **read.py** `a.one` — [HIGH] the code prints only the first 12 feats, then truncates the rest
  - says: the interactive inspection path
- **read.py** `a.one` — [HIGH] the code prints only the first 12 feats
  - says: the interactive inspection path
- **read.py** `priority` — [HIGH] Sorts by own-page size and yield_per_chunk, not depth first
  - says: Depth first, because depth is what the model is actually better at.
- **pipeline.py** `merged` — [HIGH] initially set to `rec` and only becomes the disk-merged version if the read succeeds
  - says: carries the caller's fresh per-entry judgments
- **repass_bands.py** `if PL.write_record(path, rec):` — [MEDIUM] The code checks the return value of `write_record`; it only appends to `touched` when the write succeeds, contrary to the comment
  - says: `write_record` return value is ignored and `touched` is always appended, causing the run to count rewritten records even when the write failed
- **read.py** `_card_gate` — [MEDIUM] It only checks/acquires _GATE_LOCAL, but the docstring and logic imply it should handle the gate returned by _gate(), which could be _GATE_CLOUD.
  - says: Hold one of the card's GATE_LOCAL_N permits -- unless this thread already holds one.
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
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops
- **foreman.py** `kill_stalled` — [MEDIUM] kill stalled jobs that can be restarted, and escalate those that cannot
  - says: kill stalled jobs

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
