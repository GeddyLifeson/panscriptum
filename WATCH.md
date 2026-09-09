# OVERWATCH

round 463  ·  last run 2026-09-09 17:09

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 302,144 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**30 open** (13 high). Newest first.

- **build_terminal.py** `esc` — [HIGH] some catalogue-derived strings bypass it, and some are escaped where they enter the string not at the sinks
  - says: every catalogue-derived string goes through this before it reaches innerHTML
- **axis_correlation.py** `rho` — [HIGH] used without definition
  - says: compute correlation between two axes
- **worldseed.py** `to_fmg_query` — [HIGH] Constructs a query string with parameters that are not all the ones the generator actually honours
  - says: Render for Azgaar, emitting ONLY what that generator actually honours.
- **worldseed.py** `URL_SETTABLE` — [HIGH] A tuple of parameters that the function to_fmg_query does not use, and which are not authoritative or complete
  - says: What the profile derives that a query string cannot deliver. Named, not hidden.
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
- **read.py** `return done["errored"] == 0` — [HIGH] returns 0 if no errors occurred, but the exit code should reflect whether any errors occurred
  - says: THE EXIT CODE IS THE NUMBER A SCHEDULER ACTUALLY LOOKS AT
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [HIGH] the code returns 1 if the return value is None, else 0, which is the opposite of what was intended
  - says: THE VERDICT IS THE EXIT CODE (sweep42-batch10). This discarded `reopen_stranded()`'s return value and returned 0 unconditionally, so a repair that could not read or write PIPELINE_STATE.json reported success to whatever ran it -- the check-that-cannot-fail shape, on a repair. It is invoked from scripts, which have nothing else to read.
- **grounding.py** `silence.write_json` — [HIGH] writes JSON to the file and returns a boolean indicating success
  - says: uses to mean "this run did not do what it was asked"
- **cleanup.py** `low_pref` — [MEDIUM] finds a prefix match with len(ce) >= 6, but the comment says it's for proper prefixes and the docstring says it's for guessing names which is worse
  - says: finds a prefix match
- **catalogue_models.py** `sweep` — [MEDIUM] reports stale model references when providers no longer serve them but truncates the list of available samples to the first 10 entries
  - says: reports stale model references when providers no longer serve them
- **autostart.py** `ON.running` — [MEDIUM] ON.running(job) returns None when the probe could not read the process table, but the code uses truthiness to interpret None as 'not running', which contradicts the docstring's advice to test 'is None' explicitly
  - says: THE SINGLE ROSTER, NOT A HAND-KEPT SUBSET OF IT. This used to be a six-item tuple typed out here, and it had already drifted from `ON.STANDING`: it named "feats.py" where the roster's own entry is "feats.py --roll" (a real fragment-with-argument, per `_cmd_is_running`'s own docstring, not a mention), and it had no entry at all for `pipeline`, which joined STANDING after this tuple was written -- so `--status` could print every job on ITS list green while pipeline.py was down. `ON.ALL_JOBS` is the roster its own comment in overnight.py says exists so nothing keeps a partial copy; `autostart.py`/`overnight.py` are skipped here because this report already named them above, as the launcher and supervisor lines.
- **allsweep.py** `bad` — [MEDIUM] excludes reconcile and estate findings, only counts some of them
  - says: sum of all bad subsystems including reconcile and estate
- **navtree.py** `silence.write_json` — [MEDIUM] write_json is called but the code does not handle the case where the write is denied, leading to incorrect behavior as the code does not properly handle the failure case
  - says: write_json
- **workorders.py** `shell_active` — [MEDIUM] the reroute reason arrived as a SHELL ARGUMENT and contains %d construct(s) a shell acts on, but the code is not using the result of shell_active
  - says: the reroute reason arrived as a SHELL ARGUMENT and contains %d construct(s) a shell acts on
- **workorders.py** `how` — [MEDIUM] the --how argument is read from the command line, and the --how-file argument is used to read from a file or stdin. However, the code uses _side_channel_text to handle both channels, which is supposed to manage the safe channel. The variable 'how' is assigned the result of _side_channel_text, which may not be the same as the command line argument.
  - says: read the --how text from PATH ('-' for stdin) instead of from the command line. THE SAFE CHANNEL: the text never becomes a shell argument, so nothing in it can be substituted, eaten or EXECUTED
- **workorders.py** `scanned` — [MEDIUM] is set to the result of os.path.isdir(P.SITE), which is a boolean
  - says: determines if the export tree exists
- **scope.py** `ceiling_for` — [MEDIUM] The function is called by `magnitude.host_ceiling` (magnitude.py:942) and is used to retrieve the ceiling from the SCOPE.json file.
  - says: The Magnitude ceiling a source's own scope supports, or None. NO CALLERS -- see above.
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
- **tells.py** `prompt_in_sync` — [MEDIUM] compares the block with the text after replacing \r\n with \n, but the code is named 'prompt_in_sync' which implies checking if the prompt is in sync
  - says: returns True if the prompt file contains the generated block, False otherwise

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
