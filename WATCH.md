# OVERWATCH

round 453  ·  last run 2026-09-09 09:32

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 301,397 inspected (deep scan as of round 451)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**34 open** (15 high). Newest first.

- **publish.py** `sync_tree` — [HIGH] Copies files and directories, including whole-tree copies when directories are present
  - says: Refresh the export copy from the live project. Named files only, never a whole-tree copy.
- **publish.py** `held` — [HIGH] the set of COPY_DIRS roots that were removed from COPY_DIRS
  - says: the set of COPY_DIRS roots sync_tree could not enumerate in the live project
- **publish.py** `_is_agent_scratch` — [HIGH] Checks if a file is in a CODE_FREE_DIRS directory and has an extension in _CODE_EXT, but the logic is inverted. It should return True for files that are not in CODE_FREE_DIRS or do not have the extensions in _CODE_EXT.
  - says: True for a file `sync_tree` must never publish because of WHERE it is rather than what it is called: source code under a `CODE_FREE_DIRS` root.
- **pipeline.py** `synthesis_blocks` — [HIGH] The function returns a list of blocks with either mined feats or description-based entries, but the key defect is the use of `+` which combines two lists, leading to a situation where the `or` operator was previously used, which caused some entries to be excluded. The function's actual behavior is to include all entries, but the original intention was to have a ranked truncation, which is not the case here.
  - says: The nomination blocks for one source, and the mined feat text behind them.
- **pipeline.py** `write_record` — [HIGH] Writes the pipeline's in-memory copy over the disk file when there's no drift, silently overwriting any changes made by other writers
  - says: Write a record back WITHOUT clobbering a concurrent writer's work.
- **overnight.py** `_cmd_is_running` — [HIGH] Checks if the fragment is a substring, not if the command line indicates the fragment is being executed.
  - says: Does this command line show `fragment` BEING RUN, rather than merely mentioned?
- **overnight.py** `_cmd_tokens` — [HIGH] Returns split tokens of a command line, not checking if the script is in the current checkout.
  - says: Is the script on this command line THIS checkout's copy? -> bool.
- **mutate.py** `_lock_release` — [HIGH] Removes the lock file unconditionally, but the function is named and documented as releasing the lock.
  - says: Drop the lock, but only if it is still OURS.
- **mutate.py** `_lock_acquire` — [HIGH] Acquires the lock and writes a token to it, but the function is named and documented as releasing the lock.
  - says: Drop the lock, but only if it is still OURS.
- **manifest_builder.py** `pack_feats` — [HIGH] is used without being defined in the current scope
  - says: DERIVED, NOT DECLARED (m46). `FEATS_BLOCK_CHARS` had no arithmetic relationship to `num_ctx`
- **local_agent.py** `num_ctx` — [HIGH] hardcoded to 8192
  - says: num_ctx from config.yaml
- **local_agent.py** `rel_written` — [HIGH] Used to compare the resolved path against the written path to detect hard links, but the comment says it's for checking protected regions.
  - says: Is this project-relative path inside a protected REGION? -> bool (prefix rule only).
- **hostcheck.py** `rate` — [HIGH] rate is set to 0.0 if None
  - says: A CONTROL THAT DID NOT MEASURE IS `None`, NOT ZERO
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [HIGH] the code returns 1 if the return value is None, else 0, which is the opposite of what was intended
  - says: THE VERDICT IS THE EXIT CODE (sweep42-batch10). This discarded `reopen_stranded()`'s return value and returned 0 unconditionally, so a repair that could not read or write PIPELINE_STATE.json reported success to whatever ran it -- the check-that-cannot-fail shape, on a repair. It is invoked from scripts, which have nothing else to read.
- **grounding.py** `silence.write_json` — [HIGH] writes JSON to the file and returns a boolean indicating success
  - says: uses to mean "this run did not do what it was asked"
- **publish.py** `silence.write_json` — [MEDIUM] Writes to a fixed temp file name
  - says: Names the temp file after the writer
- **publish.py** `render_views` — [MEDIUM] Returns 0 on failure, but the docstring says it returns the landed count.
  - says: Redraw the five DRAWN cosmology tiers into output/views/. -> landed count.
- **publish.py** `_is_compiled` — [MEDIUM] Returns True for `.pyc`/`.pyo` files, but also for paths containing `__pycache__` even when the file is not a `.pyc`/`.pyo`
  - says: True for compiled bytecode: any `__pycache__` path component, or a `.pyc`/`.pyo` file.
- **publish.py** `scrub_text` — [MEDIUM] Scrubbing multi-line strings by line, but the code checks for the FIXTURE_MARKER in the entire string, not per line, allowing a single marker to blank the scrub for every line that value carried, including a line with a live credential and no marker of its own.
  - says: Both locks, applied to one string. Named and public so the DRILL can attack it.
- **pipeline.py** `phases` — [MEDIUM] phases is assigned a list of phases based on args.phase or st['phase'], but the code later checks if phases is empty and handles it with specific logging and exit codes. However, the claim is about the runner needing to identify an empty work list, which is addressed in the code. The actual behavior aligns with the claim, so no defect of fact is found here.
  - says: A RUNNER WITH AN EMPTY WORK LIST MUST SAY WHICH KIND OF EMPTY IT IS.
- **pipeline.py** `T.chart` — [MEDIUM] chart() returns a tuple; the first element is the per-source tier stack
  - says: chart() returns a tuple; the first element is the per-source tier stack
- **pipeline.py** `ask_pool_first` — [MEDIUM] Cloud pool first, local second -- for the PHASES' own judgment calls. However, the function does not actually enforce the cloud-first logic as described. It checks if the pool answering is >= _min_buckets, but the actual routing decision is made based on the pool proof's age and caption, which is not directly related to the cloud-first logic. The function's actual behavior is more about handling the cloud answer's usability and falling back to local if needed, rather than strictly enforcing the cloud-first approach as the comment suggests.
  - says: Cloud pool first, local second -- for the PHASES' own judgment calls.
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
