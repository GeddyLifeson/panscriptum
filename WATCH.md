# OVERWATCH

round 108  ·  last run 2026-08-27 20:54

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 264,734 inspected
- catalogued sources with no host: **9** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major
- NOT RUNNING: **0** feats.py --roll

## What the model found in the code

**29 open** (9 high). Newest first.

- **pipeline.py** `phase_cosmology` — [HIGH] does not run any of the described modules
  - says: chart the tiers, and answer the First Argument per cosmos.
- **pipeline.py** `phase_chain` — [HIGH] A function that does not implement phase 4 logic but instead serves as a placeholder that stops the runner cleanly when phase 4 is reached
  - says: Phase 4 -- the Chain of Defeats. See chain.py for the reasoning.
- **pipeline.py** `gate_done` — [HIGH] Marks a phase done even if some artifacts did not land, because the condition is incorrect
  - says: Mark a phase done ONLY if every artifact it wrote actually landed.
- **mutate.py** `_lock_acquire` — [HIGH] Never called within the module, rendering the lock mechanism ineffective
  - says: Acquire a lock to prevent concurrent mutation runs
- **ledger_guard.py** `read_chain` — [HIGH] swallows all exceptions except FileNotFoundError and returns an empty list
  - says: Read the chain, or raise -- "no chain yet" and "could not be read" are not the same claim.
- **dashboard.py** `quotas` — [HIGH] Appends a failure message to the output when quota read fails, but does not report actual usage data as claimed
  - says: Calls actually made in the recent past, per bucket. The quota panel says what is LEFT; this says what is being SPENT, and the two together are the whole picture
- **drill.py** `gate_claim_matches_reality` — [HIGH] the code checks that the catalog and the shelf agree in both directions
  - says: two nets up counts the same directory but only demands it be EMPTY while the gate is shut; this one holds once the gate is open again, which is when it starts t
- **dashboard.py** `movement` — [HIGH] movement(d)
  - says: movement(s)
- **genre.py** `classify_source` — [HIGH] Truncates the entry list in stored order, changing the answer for 7 of 210 sources
  - says: Classify one source from its own catalogued entries.
- **profile.py** `encode` — [MEDIUM] the code says it does
  - says: the code says it does
- **policy.py** `vacuous` — [MEDIUM] A rule that passed while looking at a field that does not exist, but the rule's operator is 'absent' (which is exempt from being flagged as vacuous). The code includes a check for 
  - says: A rule that PASSED while looking at a field that does not exist. Not a failure -- but not evidence of anything either, and the only place it is ever visible.
- **pipeline.py** `batch_settled` — [MEDIUM] The function batch_settled is called with key, done_keys, and batch, but the code does not actually check if the batch is closed or if entries have been added after the batch was c
  - says: A CLOSED BATCH IS NOT A CLOSED SPAN. The resume key is `source#start`, but the span it names is `entries[start:start+B]` -- and a record's entry list GROWS afte
- **pipeline.py** `write_record_catalogue` — [MEDIUM] write_record_catalogue is the catalogue's side of the two-writer contract
  - says: write_record_catalogue below is the pipeline's.
- **overnight.py** `main` — [MEDIUM] exits with 0
  - says: supervisor finished
- **overnight.py** `_cmd_is_running` — [MEDIUM] Checks if the command line contains the fragment as a script name, but not its arguments, and if the interpreter is Python
  - says: PURE. Does this command line show `fragment` BEING RUN, rather than merely mentioned?
- **onomast.py** `well_formed` — [MEDIUM] Enforces constraints that may not align with the intended purpose of checking pronounceability and uniqueness
  - says: Is this a name a Custos could say aloud and write down twice the same way?
- **dashboard.py** `movement` — [MEDIUM] The code reports a negative delta as a reset rather than a movement, but the comment suggests it should distinguish between a counter that fell (reset) and one that moved, which th
  - says: A COUNTER THAT FELL IS NOT A COUNTER THAT MOVED.
- **dashboard.py** `movement` — [MEDIUM] The code attempts to heal a corrupt history file by resetting it to an empty list, but the comment suggests it should start with an empty list and append the new row without skippi
  - says: A CORRUPT HISTORY FILE MUST HEAL, NOT WEDGE.
- **dashboard.py** `movement` — [MEDIUM] Calculates deltas between the current reading and the oldest sample within the MOVED_WINDOW_MIN window, but the code's comment and docstring suggest it should compare against the o
  - says: What has CHANGED, not what the level is.
- **drill.py** `resuming_demands_a_written_ruling` — [MEDIUM] the resume call is not checked for success
  - says: a shrug re-opened it. Breach.
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [MEDIUM] the code checks that the sum of states does not exceed the entry count
  - says: No source's states may sum PAST its own entry count. One direction, and only one.
- **drill.py** `catalog_matches_disk` — [MEDIUM] Only checks that chapters in the catalog exist on disk (catalog -> disk), not the reverse (disk -> catalog).
  - says: Every chapter the catalog claims exists on disk, AND VICE VERSA — both directions.
- **drill.py** `denied` — [MEDIUM] Checks for error messages containing 'denylist', 'protected region', 'writable surface', or 'no such file' to determine if a path is denied, but these error messages are not necess
  - says: Was the path refused BY A GATE, as opposed to failing for an unrelated reason?
- **dashboard.py** `movement` — [MEDIUM] Computes deltas between the current reading and the oldest sample within the MOVED_WINDOW_MIN window, but the code actually uses the oldest sample within the window as the base for
  - says: What has CHANGED, not what the level is.
- **feats.py** `mine` — [MEDIUM] Only sentences that clear the evidence gate are kept; physical quantities are not tagged with the page they came from.
  - says: Sentences that clear the evidence gate, plus any physical quantities, each tagged with the page it came from. Rejections are kept — see the module docstring.
- **descending_ladder.py** `shrink_report` — [MEDIUM] The function does not enforce that `to_m` is less than `from_m` (i.e., it does not ensure it's a descent), but instead reports `is_descent` as a boolean based on the input values.
  - says: Full accounting of a mass-conserving descent. Returns the physics, and the verdict.
- **catalogue_web.py** `catalogue` — [MEDIUM] catalogue a source's pages but the function is named 'catalogue' and the code is correct
  - says: catalogue a source's pages
- **corpus_db.py** `age_seconds` — [MEDIUM] Returns the time since the index was built, but does not handle cases where the index is locked or corrupt, which can result in None being returned incorrectly
  - says: How old the index is in seconds, or None. -> float|None.
- **backfill.py** `lead` — [MEDIUM] extract a lead sentence from a block of text
  - says: take the lead from there

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
