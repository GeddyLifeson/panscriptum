# OVERWATCH

round 500  ·  last run 2026-09-14 01:42

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,019 inspected (deep scan as of round 499)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**6 open** (1 high). Newest first.

- **codewatch.py** `_maintenance_run_live` — [HIGH] Returns whether a maintenance shift is holding the run guard, but the function's description says it should describe, not decide, and the code's comment says it should not decide the rung (rank).
  - says: Is a maintenance shift holding the run guard right now? -> (bool, description).
- **derivation.py** `main` — [MEDIUM] returns 0 only if the ledger closes and there are no problems; returns 1 if there are problems
  - says: returns 0 if the ledger closes, 1 otherwise
- **cleanup.py** `low_pref` — [MEDIUM] returns a single prefix match, but the comment says it's for proper prefixes
  - says: returns a single prefix match
- **catalogue_web.py** `type` — [MEDIUM] fallback to 'Deity' if no category is found
  - says: THE CATEGORY THIS TITLE ACTUALLY CAME FROM
- **binding_health.py** `len(tried)` — [MEDIUM] the number of titles that were actually tried
  - says: the reader can see how many were asked
- **sweep.py** `sweep` — [MEDIUM] the comparison eight lines down (`sc["n"] > idx[k][3]`) is what implements the finer-grained-scale-wins rule
  - says: the comparison eight lines down (`sc["n"] > idx[k][3]`) is what implements the finer-grained-scale-wins rule

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
