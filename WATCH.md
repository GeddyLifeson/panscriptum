# OVERWATCH

round 98  ·  last run 2026-08-27 04:31

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 252,077 inspected
- catalogued sources with no host: **9** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major
- NOT RUNNING: **0** feats.py --roll

## What the model found in the code

**13 open** (5 high). Newest first.

- **completeness.py** `no_denominator` — [HIGH] A ROW THAT COULD NOT BE MEASURED IS A ROW WITH NOTHING IN IT. The code returns a row with the no_denominator message instead of None, which is read downstream as "this source has n
  - says: A ROW THAT COULD NOT BE MEASURED IS NOT A ROW WITH NOTHING IN IT. Returning None here for an all-errors source deleted it from COMPLETENESS.json, and an absent 
- **catalogue_web.py** `roll` — [HIGH] the variable 'roll' is never defined in this file, causing a NameError when called
  - says: save_roll(roll) saves the updated roll after setting its status
- **chain.py** `work` — [HIGH] increments `unmatched` directly without locking, risking race conditions
  - says: TALLIED LOCALLY, MERGED UNDER THE LOCK, for the same reason `local` exists.
- **binding_health.py** `verdict` — [HIGH] The verdict function is not properly handling the absent probe's three possible outcomes (None, False, True), leading to incorrect classification of host faults.
  - says: The three probe outcomes -> (healthy, reason).
- **genre.py** `classify_source` — [HIGH] Truncates the entry list in stored order, changing the answer for 7 of 210 sources
  - says: Classify one source from its own catalogued entries.
- **corpus_db.py** `age_seconds` — [MEDIUM] Returns the time since the index was built, but does not handle cases where the index is locked or corrupt, which can result in None being returned incorrectly
  - says: How old the index is in seconds, or None. -> float|None.
- **cleanup.py** `changed` — [MEDIUM] set in three branches but not used in the fourth, leading to potential missed updates
  - says: tracking whether any changes were made to a record
- **chain.py** `work` — [MEDIUM] uses `chunk[min(i, len(chunk) - 1)]` to attribute outcomes to sentences, which may still be incorrect
  - says: Every outcome after the first skipped sentence was therefore attributed to the wrong sentence, and inherited the wrong page and the wrong CONTINUITY.
- **build_terminal.py** `descend` — [MEDIUM] descend(key) is called with key as a parameter, but the function is designed to handle the key as a parameter, so there is no discrepancy
  - says: descend(key) is called with key as a parameter
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
