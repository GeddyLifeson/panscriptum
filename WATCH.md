# OVERWATCH

round 242  ·  last run 2026-08-31 11:26

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 285,721 inspected (deep scan as of round 241)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**14 open** (3 high). Newest first.

- **thread_integrity.py** `out["IMPLIED-UNRECORDED"]` — [HIGH] used in two places where the code is supposed to count pairs where neither end records the thread, but the code is commented to indicate that this was a bug where the branch was unreachable
  - says: counts pairs where neither end records the thread
- **thread_integrity.py** `out["PARTIALLY-DANGLING"]` — [HIGH] increments the count for partially dangling pairs but the code is commented to indicate that this was a bug where drift was only reported when all shared keys had gone
  - says: counts the number of pairs that are partially dangling
- **standards.py** `now` — [HIGH] variable `now` is referenced but not defined anywhere in this file or its imports, causing a NameError.
  - says: records the current time for the token‑flow update.
- **tiers.py** `main` — [MEDIUM] returns 0 if the write was successful, else 1
  - says: returns 0 if the rename landed, else 1
- **standards.py** `unans_files` — [MEDIUM] count of records that have 'chunks_unanswered' but not 0
  - says: count of unanswered records
- **standards.py** `len(w.get("broken") or []) <= MAX_BROKEN_MODULES` — [MEDIUM] counts broken modules
  - says: every module imports
- **standards.py** `int(cfg.get("num_ctx", 6144))` — [MEDIUM] uses a hard‑coded literal default of 6144 when the config key is missing.
  - says: num_ctx FROM CONFIG, never a literal -- see the docstring.
- **standards.py** `fab` — [MEDIUM] fabrication rate only if parsed successfully, else None
  - says: fabrication rate
- **standards.py** `unans_files` — [MEDIUM] count of records that do not have 'chunks_unanswered' or have it set to 0
  - says: count of unanswered records
- **standards.py** `silence` — [MEDIUM] not defined in this file or its imports
  - says: used to log exceptions
- **standards.py** `HERE` — [MEDIUM] not defined in this file or its imports
  - says: used to locate config and metrics files
- **silence.py** `_handler_is_observed` — [MEDIUM] The function is used to determine if a handler is observed, but the code in the module suggests that the function's logic may not correctly identify re-raised exceptions, leading to potential misclassification of handlers as silent.
  - says: A handler that re-raises, logs, or carries the exception into its own return value is observed.
- **profile.py** `encode` — [MEDIUM] the code does something else
  - says: the code says it does
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
