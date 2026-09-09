# OVERWATCH

round 455  ·  last run 2026-09-09 12:36

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 301,397 inspected (deep scan as of round 451)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**29 open** (13 high). Newest first.

- **retry_synthesis.py** `PL.clean_band` — [HIGH] acceptance is forgiving, clamping is strict
  - says: acceptance is strict, clamping is forgiving
- **publish.py** `_is_compiled` — [HIGH] Returns True for `.pyc`/`.pyo` files, but also for any file in a `__pycache__` directory, even if it's not a `.pyc`/`.pyo` file.
  - says: True for compiled bytecode: any `__pycache__` path component, or a `.pyc`/`.pyo` file.
- **publish.py** `scrub_text` — [HIGH] Scrubbing multi-line strings by checking for the FIXTURE_MARKER in the entire string, not per line
  - says: Both locks, applied to one string. Named and public so the DRILL can attack it.
- **read.py** `return done["errored"] == 0` — [HIGH] returns 0 if no errors occurred, but the exit code should reflect whether any errors occurred
  - says: THE EXIT CODE IS THE NUMBER A SCHEDULER ACTUALLY LOOKS AT
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
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [HIGH] the code returns 1 if the return value is None, else 0, which is the opposite of what was intended
  - says: THE VERDICT IS THE EXIT CODE (sweep42-batch10). This discarded `reopen_stranded()`'s return value and returned 0 unconditionally, so a repair that could not read or write PIPELINE_STATE.json reported success to whatever ran it -- the check-that-cannot-fail shape, on a repair. It is invoked from scripts, which have nothing else to read.
- **grounding.py** `silence.write_json` — [HIGH] writes JSON to the file and returns a boolean indicating success
  - says: uses to mean "this run did not do what it was asked"
- **roll.py** `apply` — [MEDIUM] Apply changes to rows by updating fields, but does not handle the case where a source name is not present in the roll (i.e., unmatched names)
  - says: Apply `{source_name: {field: value, ...}}` to the roll, key-wise.
- **rigor.py** `mathematical_resonance` — [MEDIUM] used without definition in code
  - says: returns a dictionary with mathematical quantities and relations
- **rigor.py** `ceiling_confidence` — [MEDIUM] used without definition in code
  - says: computes confidence in a ceiling
- **rigor.py** `gumbel_return_level` — [MEDIUM] used without definition in code
  - says: calculates the return level for Gumbel distribution
- **rigor.py** `prob_at_least_one` — [MEDIUM] used without definition in the code
  - says: calculates the probability of at least one occurrence
- **rigor.py** `lognormal_product` — [MEDIUM] used without definition in the code
  - says: computes the product of log-normal distributions
- **rigor.py** `load_bearing` — [MEDIUM] sorted(fanout.items(), key=lambda kv: -kv[1])
  - says: Ranked, never truncated (Hard Rule 0). The sole consumer slices for display; a RETURNED field that stops at eight decides on the ledger's behalf that the ninth load-bearing quantity is not load-bearing.
- **retry_synthesis.py** `do_merge` — [MEDIUM] Returns 0 or 1 based on merge status, but the docstring says it should run only when the pipeline is stopped
  - says: Fold the side file into the records. Run ONLY when the pipeline is stopped.
- **publish.py** `push` — [MEDIUM] raises PushHeld and other exceptions that are caught and handled elsewhere
  - says: has only two RETURN values, and both are honest ones: it landed, or there was nothing to land.
- **publish.py** `_is_agent_scratch` — [MEDIUM] The function does not check if the root is a directory, which could lead to false positives if the root is a directory but not a file.
  - says: The root itself is never a file, so a bare `handoff` cannot match.
- **publish.py** `_is_agent_scratch` — [MEDIUM] Returns True if the file is in a CODE_FREE_DIRS directory and has an extension in _CODE_EXT, but does not check if the file is actually a file (i.e., not a directory).
  - says: True for a file `sync_tree` must never publish because of WHERE it is rather than what it is called: source code under a `CODE_FREE_DIRS` root.
- **recover_folder_records.py** `shortfalls` — [MEDIUM] It is appended to the provenance string only if there are shortfalls.
  - says: The shortfall is written into the provenance.
- **recover_folder_records.py** `shortfalls` — [MEDIUM] It is a cross-check that could not be made, which is its own answer -- the same distinction this file draws between a denied write and a write that landed.
  - says: A mapping that declares nothing usable is not a mapping that agrees.
- **read.py** `qcache` — [MEDIUM] filtering entries with _QK in key but not in value
  - says: filtering entries with _QK in key
- **pipeline.py** `ask_pool_first` — [MEDIUM] Cloud pool first, local second -- for the PHASES' own judgment calls. However, the function does not actually enforce the cloud-first logic as described. It checks if the pool answering is >= _min_buckets, but the actual routing decision is made based on the pool proof's age and caption, which is not directly related to the cloud-first logic. The function's actual behavior is more about handling the cloud answer's usability and falling back to local if needed, rather than strictly enforcing the cloud-first approach as the comment suggests.
  - says: Cloud pool first, local second -- for the PHASES' own judgment calls.
- **overnight.py** `blocking` — [MEDIUM] is set to True if the output contains the string 'FAIL  ' + _control_label
  - says: is set to True if the output contains the blocking check's failure message

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
