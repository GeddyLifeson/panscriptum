# OVERWATCH

round 452  ·  last run 2026-09-09 03:02

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 301,397 inspected (deep scan as of round 451)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**30 open** (18 high). Newest first.

- **pick_model.py** `vram_gb` — [HIGH] is None
  - says: is not None
- **overnight.py** `_cmd_is_running` — [HIGH] Checks if the fragment is a substring, not if the command line indicates the fragment is being executed.
  - says: Does this command line show `fragment` BEING RUN, rather than merely mentioned?
- **overnight.py** `_cmd_tokens` — [HIGH] Returns split tokens of a command line, not checking if the script is in the current checkout.
  - says: Is the script on this command line THIS checkout's copy? -> bool.
- **onomast.py** `coin_well_formed` — [HIGH] Returns the first well-formed name from a function that may return a malformed name, and does not ensure uniqueness across the register
  - says: First well-formed, unused name for this seed. Deterministic: same input, same output.
- **mutate.py** `_lock_release` — [HIGH] Removes the lock file unconditionally, but the function is named and documented as releasing the lock.
  - says: Drop the lock, but only if it is still OURS.
- **mutate.py** `_lock_acquire` — [HIGH] Acquires the lock and writes a token to it, but the function is named and documented as releasing the lock.
  - says: Drop the lock, but only if it is still OURS.
- **manifest_builder.py** `pack_feats` — [HIGH] is used without being defined in the current scope
  - says: DERIVED, NOT DECLARED (m46). `FEATS_BLOCK_CHARS` had no arithmetic relationship to `num_ctx`
- **local_agent.py** `out` — [HIGH] Shrink whichever field is carrying the bulk, largest first, until the envelope fits (no issue)
  - says: Shrink whichever field is carrying the bulk, largest first, until the envelope fits.
- **local_agent.py** `dumped` — [HIGH] return json.dumps(d) (no issue)
  - says: return json.dumps(d)
- **local_agent.py** `num_ctx` — [HIGH] hardcoded to 8192
  - says: num_ctx from config.yaml
- **local_agent.py** `timeout` — [HIGH] hardcoded to 1800.0
  - says: timeout from config.yaml
- **local_agent.py** `rel_written` — [HIGH] Used to compare the resolved path against the written path to detect hard links, but the comment says it's for checking protected regions.
  - says: Is this project-relative path inside a protected REGION? -> bool (prefix rule only).
- **hostcheck.py** `rate` — [HIGH] rate is set to 0.0 if None
  - says: A CONTROL THAT DID NOT MEASURE IS `None`, NOT ZERO
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [HIGH] the code returns 1 if the return value is None, else 0, which is the opposite of what was intended
  - says: THE VERDICT IS THE EXIT CODE (sweep42-batch10). This discarded `reopen_stranded()`'s return value and returned 0 unconditionally, so a repair that could not read or write PIPELINE_STATE.json reported success to whatever ran it -- the check-that-cannot-fail shape, on a repair. It is invoked from scripts, which have nothing else to read.
- **health.py** `summary` — [HIGH] The failure ledger as it stands. -> {class: count} (but the function is empty and does nothing).
  - says: The failure ledger as it stands. -> {class: count}.
- **grounding.py** `silence.write_json` — [HIGH] writes JSON to the file and returns a boolean indicating success
  - says: uses to mean "this run did not do what it was asked"
- **generate.py** `pipeline` — [HIGH] not imported or used in the code
  - says: enforces meta-language bans
- **generate.py** `generate_job` — [HIGH] does not handle meta-language bans or import errors
  - says: generates a job's content
- **overnight.py** `blocking` — [MEDIUM] is set to True if the output contains the string 'FAIL  ' + _control_label
  - says: is set to True if the output contains the blocking check's failure message
- **mutate.py** `judged_since` — [MEDIUM] list of mutants judged under current baseline
  - says: record of verdicts cast doubt over
- **mutate.py** `killed` — [MEDIUM] count of mutants that were killed
  - says: count of mutants that were killed
- **mutate.py** `indeterminate` — [MEDIUM] a list of mutants that were judged as indeterminate
  - says: the permanent record of the diff
- **mutate.py** `hang_confirms_a_kill` — [MEDIUM] The function checks if the mutant's timeout is evidence of a hang, but the code's logic is flawed in how it interprets the baseline and fresh times, potentially leading to incorrect conclusions about the mutation.
  - says: A mutant timed out on `gname`. Was that the MUTATION hanging, or the machine? -> (bool, why).
- **manifest_builder.py** `silence.replace_retry` — [MEDIUM] The function is used to replace the temporary report file with the final one, but the comment suggests it's meant to handle the report writing process with retries and error handling, which is not fully implemented.
  - says: Land it through a pid+thread temp and silence.replace_retry, and report the verdict on the same footing as the manifest write instead of assuming it.
- **local_agent.py** `modname` — [MEDIUM] module name with the wrong syntax
  - says: module name
- **local_agent.py** `hits` — [MEDIUM] list of matches with line numbers
  - says: list of matches
- **ledger_guard.py** `check_since_snapshot` — [MEDIUM] checks since the last seal, but the comment says it's the since-last-seal loop
  - says: THE SINCE-LAST-SEAL LOOP IS ONE MECHANISM...
- **ledger.py** `to_standards` — [MEDIUM] Converts a local sum into Standards, but returns None when the currency is not convertible, which is the same behavior as the docstring claims, but the function does not use the `currency_status` function as the docstring suggests.
  - says: Convert a local sum into Standards. None where the currency is not convertible -- for UNLISTED vs. deliberately non-convertible, see `currency_status`.
- **hostcheck.py** `adopt` — [MEDIUM] Find a host for every catalogued source that has none, but the function's logic may have issues with how it processes candidates and scores hosts.
  - says: Find a host for every catalogued source that has none.
- **health.py** `reopen_stranded` — [MEDIUM] Reopens batches that contain entries not yet settled (i.e., not catalogued or excluded), but the code's comment indicates that the old test (checking only for uncatalogued entries) was incorrect and that the current test using `entry_settled` is the correct one. However, the code's logic may still be re-opening batches that should not be re-opened due to the change in the test condition.
  - says: Re-open entry batches marked done that still contain uncatalogued entries.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
