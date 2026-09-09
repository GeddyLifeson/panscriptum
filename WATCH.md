# OVERWATCH

round 458  ·  last run 2026-09-09 14:18

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 302,102 inspected (deep scan as of round 457)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**43 open** (18 high). Newest first.

- **verify_math.py** `_STx.MIN_CALLS_TO_JUDGE_RATE` — [HIGH] the value standards.MIN_CALLS_TO_JUDGE_RATE is a hardcoded literal 20
  - says: the value standards.MIN_CALLS_TO_JUDGE_RATE carries is the one tuning.py declares
- **verify_math.py** `_MIN_CALLS_DECLARED_VM` — [HIGH] the threshold standards enforces is a hardcoded literal 20
  - says: the threshold standards enforces is the number tuning.py's own source declares
- **verify_math.py** `_chunk_key` — [HIGH] returns the same key for the same entity and passage across runs
  - says: entity-blind keys served one entity's feats to another, and the chunk counted as answered -- the only path in read.py that loses work permanently
- **verify_math.py** `priority` — [HIGH] returns all rows it was given
  - says: built `have_page` (own > 0) and `no_page` (no own AND chars >= 2000) and returned only those two
- **verify_math.py** `burgs_for` — [HIGH] the floor was RE-SPELT here rather than read
  - says: read `max(30, ...)` while `burgs.HAMLET_FLOOR` is 40
- **verify_math.py** `AS.map_seed` — [HIGH] the map seed is STORED — the decoded address carries no seed field
  - says: the map seed is DERIVED — an independently loaded copy of the module recomputes it
- **standards.py** `fab is not None and fab <= MAX_FABRICATION` — [HIGH] The condition is checking if fab is not None and fab is less than or equal to MAX_FABRICATION, but the comment indicates that UNMEASURED (fab is None) should be treated as a finding. The code is not correctly handling the UNMEASURED case as described in the comment.
  - says: The model is returning text that is not in the source. A rate this high means the passage is being truncated before it arrives -- check the chunk size against the model's context -- or that a weak fallback model is carrying the run. IF THIS READS UNMEASURED, TREAT THAT AS THE FINDING: this standard silently did not exist from the day it was written until run #28, because it read a job-dict key that nothing sets, so an absent reading here is exactly the failure mode that
- **standards.py** `out` — [HIGH] not modified in this code slice
  - says: receives messages to be output
- **standards.py** `fandom_ipv4_reachable` — [HIGH] Attempts to connect to 'community.fandom.com' which resolves to IPv6 addresses, making the probe ineffective for testing IPv4 connectivity
  - says: Can this machine open a TCP connection to fandom's edge OVER IPv4?
- **scope.py** `main` — [HIGH] returns 0 only when ap.print_help() is called
  - says: return 0 on both branches
- **scope.py** `scope_for` — [HIGH] returns a scope with a ceiling when no tier reaches MIN_MENTIONS
  - says: returns None when no tier reaches MIN_MENTIONS
- **runguard.py** `claim` — [HIGH] Proceeds with claim even if the guard could not be read, which is an AUTHORISATION rather than an observation, and does not refuse as the docstring says it should.
  - says: Take the guard for `agent`, or refuse. Returns (ok, reason). On refusal the caller must write nothing and stop -- landing on a live predecessor is the NORMAL outcome of a cadence that fires more often than a run takes, and exiting immediately is the correct result rather than a failure.
- **retry_synthesis.py** `PL.clean_band` — [HIGH] acceptance is forgiving, clamping is strict
  - says: acceptance is strict, clamping is forgiving
- **publish.py** `_is_compiled` — [HIGH] Returns True for `.pyc`/`.pyo` files, but also for any file in a `__pycache__` directory, even if it's not a `.pyc`/`.pyo` file.
  - says: True for compiled bytecode: any `__pycache__` path component, or a `.pyc`/`.pyo` file.
- **publish.py** `scrub_text` — [HIGH] Scrubbing multi-line strings by checking for the FIXTURE_MARKER in the entire string, not per line
  - says: Both locks, applied to one string. Named and public so the DRILL can attack it.
- **read.py** `return done["errored"] == 0` — [HIGH] returns 0 if no errors occurred, but the exit code should reflect whether any errors occurred
  - says: THE EXIT CODE IS THE NUMBER A SCHEDULER ACTUALLY LOOKS AT
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [HIGH] the code returns 1 if the return value is None, else 0, which is the opposite of what was intended
  - says: THE VERDICT IS THE EXIT CODE (sweep42-batch10). This discarded `reopen_stranded()`'s return value and returned 0 unconditionally, so a repair that could not read or write PIPELINE_STATE.json reported success to whatever ran it -- the check-that-cannot-fail shape, on a repair. It is invoked from scripts, which have nothing else to read.
- **grounding.py** `silence.write_json` — [HIGH] writes JSON to the file and returns a boolean indicating success
  - says: uses to mean "this run did not do what it was asked"
- **verify_math.py** `check` — [MEDIUM] is used to check a condition that is already known to be true
  - says: asserts that the code meets a certain condition
- **verify_math.py** `check` — [MEDIUM] checks if the status starts with 'RAN' but the expected value is False
  - says: checks if the status starts with 'RAN'
- **verify_math.py** `A.null_instrument` — [MEDIUM] the null Instrument reports itself as computed, but the reason is not provided as expected
  - says: the null Instrument reports itself COMPUTED, not merely absent
- **verify_math.py** `A.LADDER` — [MEDIUM] the ladder is not strictly ordered
  - says: the answer is STRICTLY ordered
- **verify_math.py** `A.band_for_quantity` — [MEDIUM] returns a value that is not strictly ordered
  - says: answers for a real quantity
- **verify_math.py** `A.axis_score` — [MEDIUM] returns None
  - says: returns a confidently INVERTED score
- **verify_math.py** `A.axis_score` — [MEDIUM] refuses on not lo or not hi or hi <= lo
  - says: refuses on not lo or not hi or hi <= lo
- **tiers.py** `with_h` — [MEDIUM] hyperverse (link-graph, this module's own resonance cut): ...
  - says: hyperverse (grounding-derived, per xenoverse): ...
- **tells.py** `prompt_in_sync` — [MEDIUM] compares the block with the text after replacing \r\n with \n, but the code is named 'prompt_in_sync' which implies checking if the prompt is in sync
  - says: returns True if the prompt file contains the generated block, False otherwise
- **sweep_plan.py** `plan_rec` — [MEDIUM] freeze_plan(a.run, a.batches) is called but the result is not used if a.run is False
  - says: freeze_plan(a.run, a.batches)
- **sweep_plan.py** `silence.write_json` — [MEDIUM] write_json is called but the exception is caught and a fallback is used, which may not properly handle the error
  - says: write_json is used to write the data to the COVERAGE file
- **standards.py** `work_orders` — [MEDIUM] returns 1 if bad else 0
  - says: the SAME EXIT CONVENTION ON EVERY PATH
- **standards.py** `_dup` — [MEDIUM] counts duplicates of job names in process lines
  - says: one instance of each job
- **standards.py** `job_stamp` — [MEDIUM] the function is called with p (previous job data), size (current log size), and now (current time), and returns held (whether the job is stalled) and stamp (the last modification time of the log file). However, the comment suggests that the function should calculate the time since the last modification, but the function's actual behavior is to carry forward the last known modification time if the size hasn't changed, which may not accurately reflect the job's actual silence period.
  - says: WHEN DID IT LAST MOVE, not when did this check last run. `at` was re-stamped to `now` on every pass, so `quiet_min` measured the interval between two consecutive standards runs -- a few minutes, always -- and could not reach the 15-minute floor no matter how long a job had actually been silent. The standard this file's own docstring calls "the failure this whole library is built to refuse" was therefore structurally unable to fire, for any job, and had been reporting "all advancing" by construction. Carrying the stamp forward while the size holds is what makes the number mean silence.
- **secondopinion.py** `report` — [MEDIUM] returns got and _torn
  - says: returns got and _torn
- **scope.py** `ceiling_for` — [MEDIUM] Returns the ceiling for a source's scope, but the function is marked as having no callers and is kept for historical reasons.
  - says: The Magnitude ceiling a source's own scope supports, or None. NO CALLERS -- see above.
- **rigor.py** `mathematical_resonance` — [MEDIUM] used without definition in code
  - says: returns a dictionary with mathematical quantities and relations
- **rigor.py** `gumbel_return_level` — [MEDIUM] used without definition in code
  - says: calculates the return level for Gumbel distribution
- **rigor.py** `prob_at_least_one` — [MEDIUM] used without definition in the code
  - says: calculates the probability of at least one occurrence
- **rigor.py** `lognormal_product` — [MEDIUM] used without definition in the code
  - says: computes the product of log-normal distributions
- **rigor.py** `load_bearing` — [MEDIUM] sorted(fanout.items(), key=lambda kv: -kv[1])
  - says: Ranked, never truncated (Hard Rule 0). The sole consumer slices for display; a RETURNED field that stops at eight decides on the ledger's behalf that the ninth load-bearing quantity is not load-bearing.
- **publish.py** `_is_agent_scratch` — [MEDIUM] The function does not check if the root is a directory, which could lead to false positives if the root is a directory but not a file.
  - says: The root itself is never a file, so a bare `handoff` cannot match.
- **publish.py** `_is_agent_scratch` — [MEDIUM] Returns True if the file is in a CODE_FREE_DIRS directory and has an extension in _CODE_EXT, but does not check if the file is actually a file (i.e., not a directory).
  - says: True for a file `sync_tree` must never publish because of WHERE it is rather than what it is called: source code under a `CODE_FREE_DIRS` root.
- **recover_folder_records.py** `shortfalls` — [MEDIUM] It is appended to the provenance string only if there are shortfalls.
  - says: The shortfall is written into the provenance.
- **recover_folder_records.py** `shortfalls` — [MEDIUM] It is a cross-check that could not be made, which is its own answer -- the same distinction this file draws between a denied write and a write that landed.
  - says: A mapping that declares nothing usable is not a mapping that agrees.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
