# OVERWATCH

round 448  ·  last run 2026-09-08 22:18

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 301,105 inspected (deep scan as of round 445)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py
- NOT RUNNING: **0** foreman.py

## What the model found in the code

**19 open** (2 high). Newest first.

- **generate.py** `pipeline` — [HIGH] not imported or used in the code
  - says: enforces meta-language bans
- **generate.py** `generate_job` — [HIGH] does not handle meta-language bans or import errors
  - says: generates a job's content
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
- **drill.py** `PL.mark_done(st, "weave")` — [MEDIUM] the marker itself, and the gate that calls it are both unguarded
  - says: the marker itself, and the gate that calls it
- **drill.py** `st.get("phase") == 4` — [MEDIUM] the resume point advances past the open work
  - says: the resume point stays behind the open work
- **drill.py** `the_gate_and_the_public_door_are_denied` — [MEDIUM] The function's logic is based on checking denied and still_open, but the comment suggests it's supposed to check if the gate and public door are denied, which may not align with the actual return value.
  - says: NOT A STRING BYPASS -- the first six attacks in this area were all 'a name the filesystem resolves differently'.
- **drill.py** `the_gate_and_the_public_door_are_denied` — [MEDIUM] The function checks if both 'src/prose_gate.py' and 'src/publish.py' are denied, but the logic is inverted in the return statement (returns denied and still_open instead of denied and not still_open).
  - says: The local model may not write the prose gate, nor the module that pushes to the public.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
