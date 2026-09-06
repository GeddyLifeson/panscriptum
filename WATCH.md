# OVERWATCH

round 394  ·  last run 2026-09-06 11:22

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 297,340 inspected (deep scan as of round 391)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**44 open** (9 high). Newest first.

- **foreman.py** `kill_stalled_job` — [HIGH] Kills stalled jobs, but the code comments indicate it should only kill jobs that are not in the standing set and not restartable, which is a contradiction.
  - says: A job that is UP and writing nothing is worse than a job that is down.
- **workorders.py** `resolve_code` — [HIGH] resolve_code is called with a code and a resolution message, but the code is not checked against any condition; it always returns True
  - says: resolve_code is called with a code and a resolution message, and it is expected to file a work order if the resolution is not met
- **verify_math.py** `check` — [HIGH] the success floor sits above the standard's 50% ok bar
  - says: the success floor sits below the standard's 50% ok bar
- **verify_math.py** `check` — [HIGH] the check is using a hardcoded payload to test the predicate instead of calling the actual function
  - says: the token-flow probe counts tokens, not prose
- **verify_math.py** `max(BG.HAMLET_FLOOR, int(_bs[0][` — [HIGH] max(int, int) which is an int
  - says: max(BG.HAMLET_FLOOR, int(...))
- **verify_math.py** `check` — [HIGH] check that a condition is false
  - says: check that a condition is true
- **verify_math.py** `A.assay` — [HIGH] assay a single axis's scores and attestation
  - says: assay an anchor's scores and attestation
- **rosetta.py** `stand_rows` — [HIGH] does not parse Stand parameters as described, but instead appears to be a placeholder or incomplete implementation
  - says: (name, mean Stand-parameter grade) pairs read from labelled parameter blocks. -> {}
- **overnight.py** `run` — [HIGH] does not order anything and cannot run after the reader
  - says: Runs after the reader so it sees the evidence the reader just produced
- **foreman.py** `refresh_coverage` — [MEDIUM] Returns a boolean indicating if the coverage script ran successfully, without capturing or reporting any output or error details.
  - says: Re-measure cited/settled. Stale figures understate the library and mislead every other standard that reads them.
- **generate.py** `failures.pop` — [MEDIUM] removes a failure from the failures list even if the chapter was not actually failed
  - says: A DEAD REFUSAL MUST NOT READ LIKE A LIVE ONE
- **workorders.py** `resolve_code` — [MEDIUM] checking if the resolve is in the loaded data
  - says: reading the exit code, was told the resolution never applied when in fact it was a transient failure that should be RETRIED.
- **verify_math.py** `A.axis_score` — [MEDIUM] the guards were present, live, and never once asked to refuse anything
  - says: quantity FIRST. Getting that wrong here raised a TypeError rather than quietly asserting nothing, which is the behaviour a check should have when its author is confused; a check that swallows its own misuse is worse than no check.
- **verify_math.py** `tol=1e-9` — [MEDIUM] tol=1e-9 is discarded because the comparison is exact
  - says: tol=1e-9
- **sweep_plan.py** `clean` — [MEDIUM] not dropped and not [m["module"] for m in modules() if m["module"] not in everything]
  - says: not dropped and not [m["module"] for m in modules() if m["module"] not in everything]
- **sweep_plan.py** `silence.write_json` — [MEDIUM] write_json is called but the code does not handle exceptions that may occur during the write operation
  - says: write_json is used to write the coverage data to the JSON file
- **sweep_plan.py** `silence.replace_retry` — [MEDIUM] replace_retry is called but the code does not handle the case where the replacement fails, leading to potential data loss
  - says: replace_retry is called to replace the temporary file with the final name
- **reference.py** `shelfmark` — [MEDIUM] generates a shelfmark based on the tier_key and lower_rungs, but the code may mislabel rungs if the lengths of upper and lower do not match the expected 3 and 4 elements respectively
  - says: The charter's canonical Shelfmark
- **read.py** `_chunk_put` — [MEDIUM] is the router: Cascade first, across a dozen separately-metered providers, with the local GPU only when all of them decline
  - says: is the router: Cascade first, across a dozen separately-metered providers, with the local GPU only when all of them decline
- **read.py** `_chunk_get` — [MEDIUM] is the router: Cascade first, across a dozen separately-metered providers, with the local GPU only when all of them decline
  - says: is the router: Cascade first, across a dozen separately-metered providers, with the local GPU only when all of them decline
- **read.py** `CLOUD_CHUNK` — [MEDIUM] The value of CLOUD_CHUNK is hardcoded to CHUNK, which is 10000. The code around it suggests it should be derived based on the model's context size and token length, but it's set as a fixed value.
  - says: The CLOUD_UNIT — MEASURED, AND THE MEASUREMENT SAID NO. The reasoning was sound: pool models carry contexts an order of magnitude larger than the local one, free tiers meter REQUESTS rather than tokens, and reading a page in four big pieces instead of fourteen small ones is the same text for a quarter of the calls. 47,757 chunks across the corpus would have become 13,265.
- **read.py** `CHUNK` — [MEDIUM] The value of CHUNK is hardcoded to 10000, which is not derived from any calculation or variable in the code. The code around it suggests it should be derived based on the num_ctx and token length, but it's set as a fixed value.
  - says: THE GPU-SAFE UNIT. Ollama runs at num_ctx 6144, and English wiki prose is about 3.7 characters per token, so 10,000 characters is roughly 2,700 tokens of passage plus the system prompt -- comfortably inside the window. Sending more does not error: Ollama truncates in silence, which is what produced the "51% fabrication rate" that was really a cut-off passage.
- **publish.py** `prune_export` — [MEDIUM] a function that deletes files not in `wanted` but also deletes entire directories that are not in `COPY_DIRS` or `EXPORT_OWN_DIRS`
  - says: a function that deletes files not in `wanted`
- **profile.py** `decode` — [MEDIUM] raises ValueError on invalid profiles but does not validate the decoded components against the B32 alphabet
  - says: decodes a world profile string into its components
- **policy.py** `main` — [MEDIUM] The function returns 0, 1, or 2 based on the presence of failures, unreadable records, and whether the report was landed. The comment suggests that the function should print all failures and vacuous passes, but the code only returns exit codes without printing all the details.
  - says: Every failure and every vacuous pass is named. These printed 12 and stopped, which on a 216-record corpus meant the 13th failure onward existed only in state/policy_report.json -- and the line above it announced a count that looked like the whole list.
- **policy.py** `ev_read` — [MEDIUM] initialized to 0 and then set to the length of feats, which is the number of evidence files that were processed
  - says: counts the number of evidence files that were read
- **policy.py** `ev_total` — [MEDIUM] initialized to 0 and then set to the length of all_feats, which is the total number of evidence files
  - says: counts the total number of evidence files
- **policy.py** `nonempty` — [MEDIUM] Checks if the value has a __len__ attribute and its length is greater than zero, which would include numbers if they are containers (like a list or dict) but not numbers in a name field.
  - says: Spelled as what it means: a non-empty container or string.
- **pipeline.py** `batch_settled` — [MEDIUM] skips when the batch is already in done_keys
  - says: skip when the span as it stands right now is fully judged
- **overwatch.py** `round_once` — [MEDIUM] The function resets the _LOCAL_BUSY counter to 0 at the beginning of each round, but the comment suggests that the budget was previously per process and not per round, implying that the function may not correctly handle the budgeting logic as intended.
  - says: THE BUDGET IS PER ROUND, AND UNTIL NOW IT WAS PER PROCESS. CLOUD_BUDGET's own comment calls it "calls the watcher may take from the shared pool in one round", and the yield it guards is explicitly meant to last "for as long as the busy period lasted" -- but nothing ever reset the counter. In `--loop` mode (the standing sweep, which runs for days) one busy stretch pushed the lifetime total past 20 and every later GPU-busy call returned None forever after, with no cloud fallback. The watcher quietly stopped watching, which this file's own comment names as the thing it exists to prevent. Reset where the round begins.
- **overnight.py** `drill_rc` — [MEDIUM] assigned the value of safety_drill() which is not checked against any condition
  - says: supposed to stop us still able to? Cheap (no model calls, no network) and it is the only check that would notice a safety having been REMOVED rather than having failed.
- **overnight.py** `run` — [MEDIUM] Runs a stage to completion, but does not properly handle the case where the process is already running, leading to potential duplicate runs.
  - says: Run one stage to completion, refusing to start a duplicate.
- **onomast.py** `load_onomasticon` — [MEDIUM] returns {} on FileNotFoundError and catches all exceptions, raising OnomasticonUnreadable only if the file exists and cannot be parsed
  - says: RAISES `OnomasticonUnreadable` if the file is on disk and will not parse, and is allowed to propagate on purpose
- **mutate.py** `dead` — [MEDIUM] dead is assigned the result of unusable_gates(base), which is a list of gates that could not complete on clean code
  - says: dead = unusable_gates(base)
- **mutate.py** `no_verdict` — [MEDIUM] no_verdict is used to represent a verdict, but the comment suggests it should be a candidate for being a survivor
  - says: A SURVIVOR OF THE FAST GATES IS ONLY A CANDIDATE
- **mutate.py** `no_verdict` — [MEDIUM] no_verdict is assigned the value of sig, which is used to indicate a verdict, but the comment suggests it should represent the absence of a verdict
  - says: THE GATE DID NOT REACH A VERDICT. Not a kill: see `could_not_judge`.
- **mutate.py** `missed` — [MEDIUM] list of files that were not copied due to sandbox issues
  - says: list of files that were not copied due to sandbox issues
- **mutate.py** `absent` — [MEDIUM] list of targets that are not files in the sandbox
  - says: list of targets missing from the sandbox
- **mutate.py** `suppressed_on_record` — [MEDIUM] returns entries with 'ruled_equivalent' key, which may not be suppressed
  - says: every survivor a standing ruling kept out of the queue
- **mutate.py** `survivors_on_record` — [MEDIUM] filters out baseline_event and ruled_equivalent entries, but includes entries with 'line' key
  - says: FILTERED TO ACTUAL SURVIVORS
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
