# OVERWATCH

round 464  ·  last run 2026-09-09 17:42

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 302,144 inspected (deep scan as of round 463)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**40 open** (19 high). Newest first.

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
- **drill.py** `silence.write_json` — [HIGH] does not include a time field in the written data
  - says: this project's stated one correct way to land a shared file
- **drill.py** `silence.write_json` — [HIGH] writes to a file that can be partially read by other processes due to truncate-then-fill behavior
  - says: this project's stated one correct way to land a shared file
- **drill.py** `TH.threads_for` — [HIGH] hands back a blank
  - says: asking it for a Threads section must REFUSE rather than hand back a blank
- **drill.py** `ESC.escalate` — [HIGH] stringifies every real evidence mapping into "{'a': 1}"
  - says: stringifies every real evidence mapping
- **drill.py** `ESC.escalate` — [HIGH] resolves a typo to MANAGER
  - says: resolves a typo to OWNER
- **drill.py** `the_gate_and_the_public_door_are_denied` — [HIGH] The function uses `_denied_target` to check if the targets are denied, but the logic may allow the local model to write the prose gate or the public module if the control files are still open.
  - says: NOT A STRING BYPASS
- **drill.py** `the_gate_and_the_public_door_are_denied` — [HIGH] The function returns True when both targets are denied and the control files are still open, which may allow the local model to write the prose gate or the public module.
  - says: The local model may not write the prose gate, nor the module that pushes to the public.
- **build_terminal.py** `esc` — [HIGH] some catalogue-derived strings bypass it, and some are escaped where they enter the string not at the sinks
  - says: every catalogue-derived string goes through this before it reaches innerHTML
- **axis_correlation.py** `rho` — [HIGH] used without definition
  - says: compute correlation between two axes
- **worldseed.py** `to_fmg_query` — [HIGH] Constructs a query string with parameters that are not all the ones the generator actually honours
  - says: Render for Azgaar, emitting ONLY what that generator actually honours.
- **worldseed.py** `URL_SETTABLE` — [HIGH] A tuple of parameters that the function to_fmg_query does not use, and which are not authoritative or complete
  - says: What the profile derives that a query string cannot deliver. Named, not hidden.
- **read.py** `return done["errored"] == 0` — [HIGH] returns 0 if no errors occurred, but the exit code should reflect whether any errors occurred
  - says: THE EXIT CODE IS THE NUMBER A SCHEDULER ACTUALLY LOOKS AT
- **grounding.py** `silence.write_json` — [HIGH] writes JSON to the file and returns a boolean indicating success
  - says: uses to mean "this run did not do what it was asked"
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
- **drill.py** `the_ignore_file_names_the_same_class` — [MEDIUM] the function checks for .py and other extensions but relies on the CODE_FREE_DIRS and _CODE_EXT to cover all cases, which may not align with the intended behavior
  - says: THE SAME CLASS MEANS THE WHOLE CLASS, NOT THE .py FAMILY
- **drill.py** `SC.LOG` — [MEDIUM] A temporary file path created in a test environment
  - says: A path to the log file
- **drill.py** `SC.ATTEMPTS` — [MEDIUM] A temporary file path created in a test environment
  - says: A path to the attempts log file
- **drill.py** `SC.hostless` — [MEDIUM] A lambda function that returns a fixed dictionary of synthetic hostless sources
  - says: A function that returns hostless sources
- **drill.py** `SC.scout` — [MEDIUM] A lambda function that returns a fixed dictionary with a 'source' key, but does not perform any actual scouting or logging
  - says: A function that simulates scouting behavior with a source, names, and registration flag
- **drill.py** `F._BACKOFF` — [MEDIUM] tracks backoff multipliers and strike counts
  - says: tracks backoff multipliers
- **drill.py** `F.note_throttled` — [MEDIUM] increments a strike count and increases backoff
  - says: notes that a host is throttled
- **drill.py** `PL.gate_done(st, "write", [True, True])` — [MEDIUM] the marker itself, and the gate that calls it are not both being tested
  - says: the marker itself, and the gate that calls it
- **drill.py** `PL.mark_done(st, "weave")` — [MEDIUM] the marker itself, and the gate that calls it are not both being tested
  - says: the marker itself, and the gate that calls it
- **drill.py** `only` — [MEDIUM] It actually returns False if the file is not only that content
  - says: The code says it checks for a specific file content
- **drill.py** `LA.t_propose_patch` — [MEDIUM] applies the patch when called with apply=True
  - says: proposes a patch without applying it
- **allsweep.py** `bad` — [MEDIUM] counts LINT, RECONCILE, ESTATE, VERIFY, and adds 1 for report failure, but the comment says it should count only LINT, ESTATE, VERIFY, and report failure
  - says: sum of bad subsystems including LINT, RECONCILE, ESTATE, VERIFY, and report write failure
- **cleanup.py** `low_pref` — [MEDIUM] finds a prefix match with len(ce) >= 6, but the comment says it's for proper prefixes and the docstring says it's for guessing names which is worse
  - says: finds a prefix match
- **catalogue_models.py** `sweep` — [MEDIUM] reports stale model references when providers no longer serve them but truncates the list of available samples to the first 10 entries
  - says: reports stale model references when providers no longer serve them
- **workorders.py** `shell_active` — [MEDIUM] the reroute reason arrived as a SHELL ARGUMENT and contains %d construct(s) a shell acts on, but the code is not using the result of shell_active
  - says: the reroute reason arrived as a SHELL ARGUMENT and contains %d construct(s) a shell acts on

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
