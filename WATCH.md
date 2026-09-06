# OVERWATCH

round 400  ·  last run 2026-09-06 18:05

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 297,695 inspected (deep scan as of round 397)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**13 open** (3 high). Newest first.

- **foreman.py** `kill_stalled_job` — [HIGH] Kills stalled jobs, but the code comments indicate it should only kill jobs that are not in the standing set and not restartable, which is a contradiction.
  - says: A job that is UP and writing nothing is worse than a job that is down.
- **verify_math.py** `check` — [HIGH] the success floor sits above the standard's 50% ok bar
  - says: the success floor sits below the standard's 50% ok bar
- **verify_math.py** `check` — [HIGH] the check is using a hardcoded payload to test the predicate instead of calling the actual function
  - says: the token-flow probe counts tokens, not prose
- **roll.py** `main` — [MEDIUM] returns 0
  - says: RETURNS THE REASON, NOT JUST THE NAME
- **manifest_builder.py** `manifest_landed` — [MEDIUM] is the result of write_json
  - says: returns whether the rename LANDED
- **manifest_builder.py** `feats_index.feats_for_source` — [MEDIUM] The code attempts to compute a budget for feats blocks but the actual issue is that the `feats_index.feats_for_source` call is not properly handling the case where the feats lookup fails, leading to an incorrect assumption about the presence of feats in the source.
  - says: DERIVED, NOT DECLARED (m46). `FEATS_BLOCK_CHARS` had no arithmetic relationship to `num_ctx`
- **ledger_guard.py** `check_all` — [MEDIUM] only checks the structure and floors, not the entire ledger integrity
  - says: check the relay's ledgers
- **foreman.py** `refresh_coverage` — [MEDIUM] Returns a boolean indicating if the coverage script ran successfully, without capturing or reporting any output or error details.
  - says: Re-measure cited/settled. Stale figures understate the library and mislead every other standard that reads them.
- **verify_math.py** `A.axis_score` — [MEDIUM] the guards were present, live, and never once asked to refuse anything
  - says: quantity FIRST. Getting that wrong here raised a TypeError rather than quietly asserting nothing, which is the behaviour a check should have when its author is confused; a check that swallows its own misuse is worse than no check.
- **hostcheck.py** `sweep` — [MEDIUM] searches for replacements for hosts that failed to hold their fiction but uses a flawed logic for selecting replacements
  - says: searches for replacements for hosts that failed to hold their fiction
- **health.py** `reopen_stranded` — [MEDIUM] return value is used to determine exit code, but the code does not handle the case where it returns None
  - says: THE VERDICT IS THE EXIT CODE (sweep42-batch10). This discarded `reopen_stranded()`'s return value and returned 0 unconditionally, so a repair that could not read or write PIPELINE_STATE.json reported success to whatever ran it -- the check-that-cannot-fail shape, on a repair.
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
