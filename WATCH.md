# OVERWATCH

round 499  ·  last run 2026-09-14 01:09

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,019 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**7 open** (2 high). Newest first.

- **codewatch.py** `_maintenance_run_live` — [HIGH] Returns whether a maintenance shift is holding the run guard, but the function's description says it should describe, not decide, and the code's comment says it should not decide the rung (rank).
  - says: Is a maintenance shift holding the run guard right now? -> (bool, description).
- **chain.py** `fit` — [HIGH] Returns an error when there are fewer than 3 edges, but the comment says it should return the fit result even when there are fewer than 3 edges.
  - says: Bradley-Terry over the recorded outcomes, with Ford's condition reported either way.
- **cleanup.py** `low_pref` — [MEDIUM] returns a single prefix match, but the comment says it's for proper prefixes
  - says: returns a single prefix match
- **catalogue_web.py** `type` — [MEDIUM] fallback to 'Deity' if no category is found
  - says: THE CATEGORY THIS TITLE ACTUALLY CAME FROM
- **citecheck.py** `_classify` — [MEDIUM] returns None when the citation is not provably broken, but also returns a reason constant when it is
  - says: -> a reason constant, or None when the citation is not provably broken.
- **binding_health.py** `len(tried)` — [MEDIUM] the number of titles that were actually tried
  - says: the reader can see how many were asked
- **sweep.py** `sweep` — [MEDIUM] the comparison eight lines down (`sc["n"] > idx[k][3]`) is what implements the finer-grained-scale-wins rule
  - says: the comparison eight lines down (`sc["n"] > idx[k][3]`) is what implements the finer-grained-scale-wins rule

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
