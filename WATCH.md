# OVERWATCH

round 104  ·  last run 2026-08-27 13:04

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **0** of 264,734 inspected
- catalogued sources with no host: **9** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major
- NOT RUNNING: **0** feats.py --roll

## What the model found in the code

**32 open** (12 high). Newest first.

- **ledger_guard.py** `read_chain` — [HIGH] swallows all exceptions except FileNotFoundError and returns an empty list
  - says: Read the chain, or raise -- "no chain yet" and "could not be read" are not the same claim.
- **dashboard.py** `quotas` — [HIGH] Appends a failure message to the output when quota read fails, but does not report actual usage data as claimed
  - says: Calls actually made in the recent past, per bucket. The quota panel says what is LEFT; this says what is being SPENT, and the two together are the whole picture
- **hostcheck.py** `cachekey.host_dir` — [HIGH] a hand-spelled copy here keeps the OLD answer and this purge silently deletes nothing from the actual cache directories
  - says: the exact "four independent copies of one convention" cachekey.py's own docstring says drift
- **drill.py** `silence.write_json` — [HIGH] writes to a file that may be read by multiple processes simultaneously without proper synchronization
  - says: this project's stated one correct way to land a shared file
- **drill.py** `gate_claim_matches_reality` — [HIGH] the code checks that the catalog and the shelf agree in both directions
  - says: two nets up counts the same directory but only demands it be EMPTY while the gate is shut; this one holds once the gate is open again, which is when it starts t
- **dashboard.py** `movement` — [HIGH] movement(d)
  - says: movement(s)
- **generate.py** `generate_job` — [HIGH] generate_job is not defined in the provided code slice and is used without being imported or defined
  - says: generate_job is supposed to generate text based on the job, templates, and configuration
- **foreman.py** `kill_stalled_job` — [HIGH] kills stalled jobs that cannot be restarted
  - says: A job that is UP and writing nothing is worse than a job that is down.
- **completeness.py** `no_denominator` — [HIGH] A ROW THAT COULD NOT BE MEASURED IS A ROW WITH NOTHING IN IT. The code returns a row with the no_denominator message instead of None, which is read downstream as "this source has n
  - says: A ROW THAT COULD NOT BE MEASURED IS NOT A ROW WITH NOTHING IN IT. Returning None here for an all-errors source deleted it from COMPLETENESS.json, and an absent 
- **chain.py** `work` — [HIGH] increments `unmatched` directly without locking, risking race conditions
  - says: TALLIED LOCALLY, MERGED UNDER THE LOCK, for the same reason `local` exists.
- **binding_health.py** `verdict` — [HIGH] The verdict function is not properly handling the absent probe's three possible outcomes (None, False, True), leading to incorrect classification of host faults.
  - says: The three probe outcomes -> (healthy, reason).
- **genre.py** `classify_source` — [HIGH] Truncates the entry list in stored order, changing the answer for 7 of 210 sources
  - says: Classify one source from its own catalogued entries.
- **dashboard.py** `movement` — [MEDIUM] Calculates deltas between the current reading and the oldest sample within the MOVED_WINDOW_MIN window, but the code's comment and docstring suggest it should compare against the o
  - says: What has CHANGED, not what the level is.
- **drill.py** `resuming_demands_a_written_ruling` — [MEDIUM] the resume call is not checked for success
  - says: a shrug re-opened it. Breach.
- **drill.py** `coverage_totals_never_exceed_their_entry_count` — [MEDIUM] the code checks that the sum of states does not exceed the entry count
  - says: No source's states may sum PAST its own entry count. One direction, and only one.
- **drill.py** `catalog_matches_disk` — [MEDIUM] Only checks that chapters in the catalog exist on disk (catalog -> disk), not the reverse (disk -> catalog).
  - says: Every chapter the catalog claims exists on disk, AND VICE VERSA — both directions.
- **drill.py** `PL.update_handoff` — [MEDIUM] update_handoff is overwritten to do nothing
  - says: update_handoff is a stand-in
- **drill.py** `PL.save_state` — [MEDIUM] save_state is overwritten to do nothing
  - says: save_state is a stand-in
- **drill.py** `PL.load_state` — [MEDIUM] load_state is overwritten to return a fixed state
  - says: load_state is a stand-in
- **drill.py** `denied` — [MEDIUM] Checks for error messages containing 'denylist', 'protected region', 'writable surface', or 'no such file' to determine if a path is denied, but these error messages are not necess
  - says: Was the path refused BY A GATE, as opposed to failing for an unrelated reason?
- **dashboard.py** `movement` — [MEDIUM] Computes deltas between the current reading and the oldest sample within the MOVED_WINDOW_MIN window, but the code actually uses the oldest sample within the window as the base for
  - says: What has CHANGED, not what the level is.
- **foreman.py** `codewatch.exit_if_stale` — [MEDIUM] Exits with rc=17 on purpose if the code is stale
  - says: Fails open: if the process table cannot be read this starts anyway
- **endpoint.py** `found` — [MEDIUM] the mode and path for the host, but initialized to an empty dictionary before the loop
  - says: the mode and path for the host
- **feats.py** `mine` — [MEDIUM] Only sentences that clear the evidence gate are kept; physical quantities are not tagged with the page they came from.
  - says: Sentences that clear the evidence gate, plus any physical quantities, each tagged with the page it came from. Rejections are kept — see the module docstring.
- **descending_ladder.py** `shrink_report` — [MEDIUM] The function does not enforce that `to_m` is less than `from_m` (i.e., it does not ensure it's a descent), but instead reports `is_descent` as a boolean based on the input values.
  - says: Full accounting of a mass-conserving descent. Returns the physics, and the verdict.
- **catalogue_web.py** `catalogue` — [MEDIUM] catalogue a source's pages but the function is named 'catalogue' and the code is correct
  - says: catalogue a source's pages
- **corpus_db.py** `age_seconds` — [MEDIUM] Returns the time since the index was built, but does not handle cases where the index is locked or corrupt, which can result in None being returned incorrectly
  - says: How old the index is in seconds, or None. -> float|None.
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
