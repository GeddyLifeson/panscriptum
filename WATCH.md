# OVERWATCH

round 466  ·  last run 2026-09-09 19:37

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 302,144 inspected (deep scan as of round 463)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**38 open** (14 high). Newest first.

- **drill.py** `ESC.escalate` — [HIGH] The escalate call is missing the 'what' argument, which is required to name the specific breached nets in the halt sentence.
  - says: A BREACHED NET IS ITSELF AN OWNER-LEVEL EVENT. THE HALT SENTENCE NAMES EVERY BREACHED NET
- **drill.py** `drill_hostcheck` — [HIGH] A function that returns a boolean indicating if an escalation log is unreadable
  - says: The host verdict, and the baseline every lift in the module is computed against.
- **drill.py** `drill` — [HIGH] A function that returns a boolean indicating if an escalation log is unreadable
  - says: The host verdict, and the baseline every lift in the module is computed against.
- **drill.py** `reap_orphans` — [HIGH] reaping matched a PREFIX AND AN AGE and a PID
  - says: reaping matched a PREFIX AND AN AGE and nothing else
- **overnight.py** `snap` — [HIGH] snap is updated with cycle and at information even when there's an error
  - says: A crashed snapshot carries ONLY an "error" key
- **ingest_doc.py** `mine` — [HIGH] reads the memory
  - says: reads the disk
- **feats.py** `_QUANTITY_UNIT_FIRST` — [HIGH] Matches 'mach' followed by a number, but the comment says it's for unit-first form (e.g., '5 mach') which is actually number-first. The regex is for 'mach' followed by a number, which is number-first, but the comment says it's for unit-first.
  - says: Matches unit-first form (e.g., '5 mach')
- **feats.py** `why not in CLEAN_NEGATIVES` — [HIGH] the code says it does instead
  - says: the code says it does instead
- **escalation.py** `clear` — [HIGH] clear() is called but not defined in this file or its imports
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller
- **escalation.py** `resume_subsystem_verdict` — [HIGH] Enforces a 20-character minimum for the ruling, which is different from `clear`'s 12-character requirement
  - says: Re-open one subsystem. -> (bool, reason). The three-valued sibling of `resume_subsystem`.
- **escalation.py** `subsystem_stopped` — [HIGH] is called but not used in the code path where it's needed to close the order
  - says: re-checks if a subsystem is stopped by reading the file
- **escalation.py** `escalate` — [HIGH] Escalates to a rung that cannot enforce itself, leading to no action taken
  - says: Rung 4, made DURABLE. Stop one subsystem until a person resumes it.
- **read.py** `return done["errored"] == 0` — [HIGH] returns 0 if no errors occurred, but the exit code should reflect whether any errors occurred
  - says: THE EXIT CODE IS THE NUMBER A SCHEDULER ACTUALLY LOOKS AT
- **grounding.py** `silence.write_json` — [HIGH] writes JSON to the file and returns a boolean indicating success
  - says: uses to mean "this run did not do what it was asked"
- **verify_math.py** `phase_cosmology` — [MEDIUM] phase 5 does not refuse, but instead returns (False, False) as per the code
  - says: phase 5 REFUSES an unparseable WORLDSEEDS.json instead of re-addressing from nothing
- **verify_math.py** `verify_restore` — [MEDIUM] the function's call site is checked to ensure it uses the sandbox copy
  - says: protects a sandbox copy, not the three ledgers
- **drill.py** `_an_unreadable_halt_file_confirms_nothing` — [MEDIUM] The function tests that `_halt_file_records` answers False when the file is unreadable, but the code does not correctly simulate an unreadable file. The test does not check if the file is unreadable and returns False in all cases, which may not accurately reflect the actual behavior.
  - says: `_halt_file_records` must answer False when it cannot read the file at all.
- **drill.py** `_a_halt_is_not_raised_on_the_writer_s_word` — [MEDIUM] The function tests that `_raise_halt` verifies the record LANDED, but the test does not correctly simulate a write that claims to have landed. The test uses a lambda that returns (True, 'landed') without writing to the file, which may not accurately reflect the actual behavior.
  - says: `_raise_halt` must verify the record LANDED; a write that merely claims to is not one.
- **drill.py** `_halt_fails_closed` — [MEDIUM] Points the module at a corrupt halt file and confirms it reads as HALTED, but the code does not check if the file is actually unreadable. The test returns True if the file is unreadable, but the actual check for unreadability is missing.
  - says: Point the module at a deliberately corrupt halt file and confirm it reads as HALTED.
- **drill.py** `custodes_table_faults_is_empty` — [MEDIUM] Checks for any table faults, including those not related to tilt and evidence_sensitivity
  - says: No CUSTODES entry may carry tilt == 0.0 together with a non-zero evidence_sensitivity.
- **drill.py** `PL.synthesis_blocks` — [MEDIUM] now a + operator that combines both halves
  - says: was [with_feats chunks] or [rest chunks]
- **drill.py** `PL._mined_feats` — [MEDIUM] overridden during a test to simulate a specific mining behavior
  - says: used to decide which arm is taken
- **overnight.py** `write_status` — [MEDIUM] Attempts to write a temporary file and replaces it with the new content, but the function's return value is not directly tied to the success of the file write operation as the function's name suggests.
  - says: Land STATUS.md. -> True if it landed, False if the replace was denied.
- **overnight.py** `CB.snapshot()` — [MEDIUM] raises exceptions which are caught and logged
  - says: NEVER RAISES
- **overnight.py** `CB.newest()` — [MEDIUM] uses the timestamp of the newest snapshot to determine if a backup is needed
  - says: RATE-LIMITED BY THE NEWEST SNAPSHOT'S OWN TIMESTAMP
- **overnight.py** `_cmd_is_running` — [MEDIUM] Checks if a command line fragment is being run by splitting and matching parts.
  - says: PURE. Does this command line show `fragment` BEING RUN, rather than merely mentioned?
- **overnight.py** `_cmd_tokens` — [MEDIUM] Returns split tokens of a command line, used to determine if a script is running.
  - says: Is the script on this command line THIS checkout's copy? -> bool.
- **ingest_doc.py** `mine` — [MEDIUM] mine() is called in a try block, and if not ok, returns 1. However, the comment says that mine() returns True only when every chunk was processed, and False on early stops. The code treats False as an error, but the comment implies that False is a valid outcome (resumable).
  - says: DON'T DISCARD THE VERDICT (order afd7aa05efb4). mine() returns True only when every chunk was processed, and False on both of its early stops -- 60 consecutive transport misses (~5h of napping) and a denied record write. Those are exactly the outcomes an operator or a scheduler needs to tell apart, and `mine(a.source); return 0` gave a run that mined 3 of 262 chunks the same exit code as one that finished the book. The --pdf half of this function has been disciplined about this since order e7b6dcc8d630; this half was not.
- **health.py** `a.preflight` — [MEDIUM] used as a condition to trigger preflight checks
  - says: used to work only by coincidence of being the fall-through default
- **health.py** `silence.write_json` — [MEDIUM] write_json is called in a context where a return value of False indicates a denied write, but the code proceeds to return None when the write is denied
  - says: write_json returns False when the atomic replace is denied
- **health.py** `dump_kw.setdefault` — [MEDIUM] overriding the default for sort_keys
  - says: set default for sort_keys
- **feats.py** `known` — [MEDIUM] A CLEAN NEGATIVE IS CACHED, BUT A NULL IS ALSO CACHED (for a source that was never probed)
  - says: AND ONLY A CLEAN NEGATIVE MAY BE CACHED
- **feats.py** `known` — [MEDIUM] A NULL IS A CACHED FAILURE, BUT A NULL IS ALSO A CACHED ANSWER (for a source that was never probed)
  - says: A NULL IS A CACHED FAILURE, NOT AN ANSWER
- **feats.py** `alive` — [MEDIUM] Returns the first element of `alive_verdict` which is True if the wiki answered, but the function is not called anywhere, making it effectively unused.
  - says: Unchanged contract: True only when the wiki answered. See `alive_verdict` for the third answer, which every caller that CACHES a negative must ask for instead of this.
- **escalation.py** `clear` — [MEDIUM] does not properly handle the case where the halt file is not cleared, leading to incorrect return values
  - says: clears a halt by writing a ruling to the halt file
- **escalation.py** `clear` — [MEDIUM] Lifts the halt if the caller is not a person, but the code checks for a person before allowing the lift
  - says: Lift the halt. A PERSON ONLY, and refused at run time if the caller is not one.
- **escalation.py** `WO.file_order` — [MEDIUM] only escalations with level >= JANITOR are converted to work orders
  - says: EVERY ESCALATION BECOMES A WORK ORDER
- **allsweep.py** `bad` — [MEDIUM] counts LINT, RECONCILE, ESTATE, VERIFY, and adds 1 for report failure, but the comment says it should count only LINT, ESTATE, VERIFY, and report failure
  - says: sum of bad subsystems including LINT, RECONCILE, ESTATE, VERIFY, and report write failure

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
