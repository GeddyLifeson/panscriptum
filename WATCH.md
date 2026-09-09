# OVERWATCH

round 449  ·  last run 2026-09-09 00:41

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 301,105 inspected (deep scan as of round 445)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**22 open** (6 high). Newest first.

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
- **hostcheck.py** `adopt` — [MEDIUM] Find a host for every catalogued source that has none, but the function's logic may have issues with how it processes candidates and scores hosts.
  - says: Find a host for every catalogued source that has none.
- **hostcheck.py** `score` — [MEDIUM] The function returns a dictionary with a verdict, but the actual calculation of the lift and verdicts may not align with the claim of measuring 'above its own baseline' due to the handling of base and rate values.
  - says: One host, fully judged: how much of this roster it holds, ABOVE ITS OWN BASELINE.
- **health.py** `reopen_stranded` — [MEDIUM] Reopens batches that contain entries not yet settled (i.e., not catalogued or excluded), but the code's comment indicates that the old test (checking only for uncatalogued entries) was incorrect and that the current test using `entry_settled` is the correct one. However, the code's logic may still be re-opening batches that should not be re-opened due to the change in the test condition.
  - says: Re-open entry batches marked done that still contain uncatalogued entries.
- **generate.py** `floor` — [MEDIUM] the evidence floor is set to 0.35
  - says: the evidence floor is misconfigured
- **foreman.py** `kill_stalled_job` — [MEDIUM] kills stalled jobs that can be restarted, but fails to kill those that cannot be restarted
  - says: A job that is UP and writing nothing is worse than a job that is down.
- **foreman.py** `restart_reader` — [MEDIUM] Enumerates processes to find a reader, but the logic is flawed as it uses a loose substring match instead of the exact fragment
  - says: The reader is not progressing. Restarting is safe: every entity is cached only when it was fully read, so nothing is lost and nothing is re-read that was finished.
- **foreman.py** `reprove_pool` — [MEDIUM] returns False when 0 of len(rows) buckets answer, and True otherwise
  - says: This returned True whenever the proof was written -- "0 of 6 buckets answer" and "6 of 6" alike -- and `round_once` BREAKS its remedy list the first time a remedy returns did=True unless the remedy is marked `.always`.
- **drill.py** `drill_outside` — [MEDIUM] an area whose probes the ledger witness cannot watch, which is the shape a net quietly becomes unable to fail in. New areas go ABOVE this line.
  - says: an area whose nets never run, which is the quietest way to lose a net.
- **drill.py** `drill_agent_scratch_gate` — [MEDIUM] an area whose probes the ledger witness cannot watch, which is the shape a net quietly becomes unable to fail in. New areas go ABOVE this line.
  - says: an area whose nets never run, which is the quiet, 
- **drill.py** `drill_weave_plan` — [MEDIUM] an area whose probes the ledger witness cannot watch, which is the shape a net quietly becomes unable to fail in. New areas go ABOVE this line.
  - says: an area whose nets never run, which is the quietest way to lose a net.
- **drill.py** `drill_hostcheck` — [MEDIUM] an area whose probes the ledger witness cannot watch, which is the shape a net quietly becomes unable to fail in. New areas go ABOVE this line.
  - says: an area whose nets never run, which is the quietest way to lose a net.
- **drill.py** `drill_identity_dashboard` — [MEDIUM] an area whose probes the ledger witness cannot watch, which is the shape a net quietly becomes unable to fail in. New areas go ABOVE this line.
  - says: an area whose nets never run, which is the quietest way to lose a net.
- **drill.py** `a_control_too_thin_to_be_one_is_not_a_baseline` — [MEDIUM] An incomplete function that is cut off and does not perform any action.
  - says: A function that describes the behavior of a control that is too thin to be a baseline.
- **drill.py** `zero_readable_bodies_is_the_thinnest_evidence_and_buys_the_least` — [MEDIUM] A function that runs tests by modifying the hostcheck module's functions and restoring them afterward.
  - says: A function that describes the behavior of zero readable bodies and how it affects the host verdict.
- **drill.py** `drill_hostcheck` — [MEDIUM] A function that runs tests and modifies the hostcheck module's behavior for testing purposes.
  - says: The host verdict, and the baseline every lift in the module is computed against.
- **drill.py** `PL.gate_done(st, "write", [True, True])` — [MEDIUM] the marker itself, and the gate that calls it are both unguarded
  - says: the marker itself, and the gate that calls it

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
