# OVERWATCH

round 498  ·  last run 2026-09-14 00:43

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 303,320 inspected (deep scan as of round 493)  — state\gpu_lane\slot.0.json — cannot stat: GONE (absent on a second look, one rename later)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**14 open** (5 high). Newest first.

- **codewatch.py** `_maintenance_run_live` — [HIGH] Returns whether a maintenance shift is holding the run guard, but the function's description says it should describe, not decide, and the code's comment says it should not decide the rung (rank).
  - says: Is a maintenance shift holding the run guard right now? -> (bool, description).
- **catalogue_web.py** `record_path` — [HIGH] the function is used but not defined in this file or its imports
  - says: the raw join would look for the un-truncated name, miss the record this module itself wrote under the cap, and write a SECOND one beside it -- the roll counting one source and the corpus holding two halves of it.
- **build_terminal.py** `esc` — [HIGH] not used for some strings that are inserted into innerHTML
  - says: every catalogue-derived string goes through this before it reaches innerHTML
- **chain.py** `fit` — [HIGH] Returns an error when there are fewer than 3 edges, but the comment says it should return the fit result even when there are fewer than 3 edges.
  - says: Bradley-Terry over the recorded outcomes, with Ford's condition reported either way.
- **chain.py** `side_epoch` — [HIGH] returns the earliest epoch of the side's sentences, and whether anything probed, but does not track the side's own sentences' disagreement (conflicts between epochs)
  - says: -> (epoch, its own sentences' disagreement, whether anything probed) for one side.
- **cleanup.py** `low_pref` — [MEDIUM] returns a single prefix match, but the comment says it's for proper prefixes
  - says: returns a single prefix match
- **catalogue_web.py** `type` — [MEDIUM] fallback to 'Deity' if no category is found
  - says: THE CATEGORY THIS TITLE ACTUALLY CAME FROM
- **citecheck.py** `_classify` — [MEDIUM] returns None when the citation is not provably broken, but also returns a reason constant when it is
  - says: -> a reason constant, or None when the citation is not provably broken.
- **allsweep.py** `bad` — [MEDIUM] counts the report write failure as a bad subsystem only when the report was not landed
  - says: sum of all bad subsystems including the report write failure
- **allsweep.py** `reconcile` — [MEDIUM] the function is called but its output is not used in the reconciliation logic
  - says: where the subsystems disagree
- **allsweep.py** `examples` — [MEDIUM] collects over-banded entries but is never used
  - says: collects over-banded entries
- **allsweep.py** `over` — [MEDIUM] counts over-banded entries but is never used
  - says: counts over-banded entries
- **binding_health.py** `len(tried)` — [MEDIUM] the number of titles that were actually tried
  - says: the reader can see how many were asked
- **sweep.py** `sweep` — [MEDIUM] the comparison eight lines down (`sc["n"] > idx[k][3]`) is what implements the finer-grained-scale-wins rule
  - says: the comparison eight lines down (`sc["n"] > idx[k][3]`) is what implements the finer-grained-scale-wins rule

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
