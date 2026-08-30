# OVERWATCH

round 172  ·  last run 2026-08-29 19:12

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 275,602 inspected (deep scan as of round 169)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**4 open** (2 high). Newest first.

- **mutate.py** `_lock_acquire` — [HIGH] does not acquire a lock, has no callers
  - says: acquire a lock
- **manifest_builder.py** `feats_index` — [HIGH] is used to fetch feats for a source, but the code handles exceptions by silently noting the failure and proceeding with an empty list
  - says: joins feats to this source's cast by name
- **magnitude.py** `_cite_number` — [MEDIUM] Matches a line number at the start of a citation, not just the one at the end
  - says: A citation that is NOTHING BUT one of our line numbers
- **liveness.py** `phantom` — [MEDIUM] a list of names used in conditions that are not defined in the module or builtins
  - says: a list of names used in conditions that are not defined

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
