# OVERWATCH

round 244  ·  last run 2026-08-31 12:20

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 285,721 inspected (deep scan as of round 241)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**10 open** (4 high). Newest first.

- **withdraw_chapters.py** `shutil.move` — [HIGH] THE RECORD IS NOT KEPT (entry_left is not updated).
  - says: THE RECORD IS KEPT AND MADE TRUE.
- **withdraw_chapters.py** `shutil.move` — [HIGH] A FAILED MOVE discards the record (adds to stuck).
  - says: A FAILED MOVE KEEPS ITS RECORD.
- **wiki_source.py** `resolve_wiki` — [HIGH] Does not consult the library's host map and instead relies on guessing subdomains
  - says: Return (subdomain, sitename) for a verified wiki, or (None, None). THE LIBRARY'S OWN HOST MAP IS CONSULTED FIRST.
- **standards.py** `now` — [HIGH] variable `now` is referenced but not defined anywhere in this file or its imports, causing a NameError.
  - says: records the current time for the token‑flow update.
- **withdraw_chapters.py** `bad` — [MEDIUM] The variable 'bad' is computed based on conditions that may not align with the actual exit code logic, potentially leading to incorrect exit codes.
  - says: EVERY REFUSAL ABOVE WAS PRINTED AND THEN DISCARDED. `main()` had no `return` on any path and the entry point was a bare `main()`...
- **tiers.py** `main` — [MEDIUM] returns 0 if the write was successful, else 1
  - says: returns 0 if the rename landed, else 1
- **standards.py** `unans_files` — [MEDIUM] count of records that have 'chunks_unanswered' but not 0
  - says: count of unanswered records
- **standards.py** `len(w.get("broken") or []) <= MAX_BROKEN_MODULES` — [MEDIUM] counts broken modules
  - says: every module imports
- **standards.py** `int(cfg.get("num_ctx", 6144))` — [MEDIUM] uses a hard‑coded literal default of 6144 when the config key is missing.
  - says: num_ctx FROM CONFIG, never a literal -- see the docstring.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
