# OVERWATCH

round 101  ·  last run 2026-08-27 08:19

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 252,077 inspected
- catalogued sources with no host: **9** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**23 open** (9 high). Newest first.

- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [HIGH] The function's code does not perform the check described in the docstring, instead only checking one direction and not ensuring the sum does not exceed the entry count.
  - says: No source's states may sum PAST its own entry count. One direction, and only one.
- **drill.py** `except Exception: continue` — [HIGH] discard failures and count as clean
  - says: handle unreadable records
- **drill.py** `PL.update_handoff` — [HIGH] does nothing
  - says: update the handoff to the real file
- **drill.py** `PL.save_state` — [HIGH] does nothing
  - says: save the state to the real file
- **drill.py** `PL.load_state` — [HIGH] load a hard-coded dictionary
  - says: load the state from the real file
- **completeness.py** `no_denominator` — [HIGH] A ROW THAT COULD NOT BE MEASURED IS A ROW WITH NOTHING IN IT. The code returns a row with the no_denominator message instead of None, which is read downstream as "this source has n
  - says: A ROW THAT COULD NOT BE MEASURED IS NOT A ROW WITH NOTHING IN IT. Returning None here for an all-errors source deleted it from COMPLETENESS.json, and an absent 
- **chain.py** `work` — [HIGH] increments `unmatched` directly without locking, risking race conditions
  - says: TALLIED LOCALLY, MERGED UNDER THE LOCK, for the same reason `local` exists.
- **binding_health.py** `verdict` — [HIGH] The verdict function is not properly handling the absent probe's three possible outcomes (None, False, True), leading to incorrect classification of host faults.
  - says: The three probe outcomes -> (healthy, reason).
- **genre.py** `classify_source` — [HIGH] Truncates the entry list in stored order, changing the answer for 7 of 210 sources
  - says: Classify one source from its own catalogued entries.
- **feats.py** `mine` — [MEDIUM] Only sentences that clear the evidence gate are kept; physical quantities are not tagged with the page they came from.
  - says: Sentences that clear the evidence gate, plus any physical quantities, each tagged with the page it came from. Rejections are kept — see the module docstring.
- **drill.py** `bad, unreadable = 0, 0` — [MEDIUM] count bad records but unreadable is incremented but not used
  - says: count bad records and unreadable ones
- **descending_ladder.py** `shrink_report` — [MEDIUM] The function does not enforce that `to_m` is less than `from_m` (i.e., it does not ensure it's a descent), but instead reports `is_descent` as a boolean based on the input values.
  - says: Full accounting of a mass-conserving descent. Returns the physics, and the verdict.
- **dashboard.py** `movement` — [MEDIUM] Computes deltas between the current sample and the oldest sample within the MOVED_WINDOW_MIN window, but the comment and docstring suggest it should compute changes relative to the
  - says: What has CHANGED, not what the level is.
- **dashboard.py** `quotas` — [MEDIUM] Returns only the status of models in the 'cascade' system, ignoring other potential sources of quota information.
  - says: Every window on every bucket, and which one is actually binding.
- **catalogue_web.py** `catalogue` — [MEDIUM] catalogue a source's pages but the function is named 'catalogue' and the code is correct
  - says: catalogue a source's pages
- **corpus_db.py** `con.execute` — [MEDIUM] INSERT OR REPLACE INTO source VALUES (?,?,?,?,?,?,?,?,?)
  - says: INSERT OR REPLACE INTO source VALUES (?,?,?,?,?,?,?,?,?)
- **corpus_db.py** `age_seconds` — [MEDIUM] Returns the time since the index was built, but does not handle cases where the index is locked or corrupt, which can result in None being returned incorrectly
  - says: How old the index is in seconds, or None. -> float|None.
- **cleanup.py** `changed` — [MEDIUM] set in three branches but not used in the fourth, leading to potential missed updates
  - says: tracking whether any changes were made to a record
- **chain.py** `work` — [MEDIUM] uses `chunk[min(i, len(chunk) - 1)]` to attribute outcomes to sentences, which may still be incorrect
  - says: Every outcome after the first skipped sentence was therefore attributed to the wrong sentence, and inherited the wrong page and the wrong CONTINUITY.
- **backfill.py** `F.api` — [MEDIUM] returns None on timeout or nothing found
  - says: used to fold that into an empty page list here too
- **backfill.py** `lead` — [MEDIUM] extract a lead sentence from a block of text
  - says: take the lead from there
- **autostart.py** `subprocess.Popen` — [MEDIUM] returns a subprocess.Popen object immediately without waiting for it to complete
  - says: launches a subprocess
- **assay.py** `sigma` — [MEDIUM] clamp the sigma value to SIGMA_MAX but the code does not handle the case where sigma is None
  - says: clamp the sigma value to SIGMA_MAX

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
