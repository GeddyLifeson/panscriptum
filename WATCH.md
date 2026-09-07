# OVERWATCH

round 412  ·  last run 2026-09-07 04:55

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 298,265 inspected (deep scan as of round 409)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**33 open** (8 high). Newest first.

- **genre.py** `classify_source` — [HIGH] Truncates the entry list in stored order and changes the answer for 7 of 210 sources
  - says: Classify one source from its own catalogued entries.
- **generate.py** `failures.pop` — [HIGH] removes a failure entry from the failures list even if the chapter was successfully catalogued
  - says: A DEAD REFUSAL MUST NOT READ LIKE A LIVE ONE
- **estate.py** `low` — [HIGH] low is a variable that is used but never defined in this file or its imports
  - says: low is a variable that is supposed to represent the combined lowercase text of the bottom three bands' descriptions
- **endpoint.py** `html_text` — [HIGH] Defined in another module, but not imported here
  - says: Extract text from HTML body
- **drill.py** `a_pure_ladder_is_all_ladder` — [HIGH] The function returns a result where 'eta' is 1.0, but the comment suggests it should return 0.0 for a shape with no ladder in it. The actual result contradicts the claim.
  - says: A STAR is EXACTLY representable: theta_a = 0.75, the three losers -0.25 each, reproducing every edge. eta must be 1.0 and the curl fraction 0.0. Under Jacobi this was 0.0 -- the answer for a shape with NO ladder in it at all, returned for a shape that is nothing but ladder.
- **drill.py** `S.replace_if_unchanged` — [HIGH] The function unconditionally returns "landed" for denied operations, which is incorrect.
  - says: The function should return the correct reason for a denied operation.
- **drill.py** `S.replace_if_unchanged` — [HIGH] The function returns (False, "landed") unconditionally, leading to incorrect logging of denied operations as successful.
  - says: A denied rename must not come back describing itself as a landing.
- **drill.py** `net` — [HIGH] The code calls net with a function that attempts to create a junction, which is unrelated to the scenario described in the first net call
  - says: The first net call claims to test a scenario where the local model may not write the prose gate or the module that pushes to the public
- **generate.py** `failures` — [MEDIUM] is used to store failure details but does not prevent the run from continuing
  - says: REFUSES THE CHAPTER, DOES NOT ABORT THE RUN
- **generate.py** `failures` — [MEDIUM] updates with getattr(e, "lists", {}) which may not include all failure details
  - says: THE COMPLETE OFFENDER LISTS, WHERE A LATER READER CAN REACH THEM
- **generate.py** `floor` — [MEDIUM] The code checks if the floor is ok, but the actual floor value is not used in any further checks.
  - says: the evidence floor is misconfigured
- **generate.py** `floor` — [MEDIUM] It is set to 0.35 and then converted to a float, but the code does not actually apply the floor check to the evidence.
  - says: It gets the treatment the sibling condition twenty lines down already gets.
- **foreman.py** `restart_ollama` — [MEDIUM] This function does not handle the case where the service is already running, which could lead to errors or failed restarts
  - says: This function is supposed to restart Ollama
- **foreman.py** `restart_ollama` — [MEDIUM] This function attempts to restart Ollama but does not actually check if the service is running before attempting to restart it, which could lead to unnecessary restarts
  - says: This function is supposed to restart Ollama
- **foreman.py** `kill_stalled` — [MEDIUM] killed stalled but not the ones that cannot be restarted
  - says: killed stalled
- **foreman.py** `restart_reader` — [MEDIUM] The function restart_reader() returns False when it cannot enumerate processes, but the code does not handle this case properly. It returns False, but the comment says that restarting is safe and that the function should return True if the reader is not progressing.
  - says: The reader is not progressing. Restarting is safe: every entity is cached only when it was fully read, so nothing is lost and nothing is re-read that was finished.
- **foreman.py** `triage_swallowed` — [MEDIUM] Archives failures and sorts them, but the comment suggests it should name the top classes
  - says: A spike in swallowed failures means something upstream is failing and being tolerated.
- **foreman.py** `rerun_roll` — [MEDIUM] Checks if the roll is running and returns a message, but the comment suggests it should report on the roll's status
  - says: The page roll has not finished its pass. It is network-bound, so a stall is a host problem rather than a quota one -- and the supervisor restarts it next cycle anyway. This reports rather than acts, because two rolls at once is the failure the supervisor exists to prevent.
- **foreman.py** `scout_hostless` — [MEDIUM] Counts sources that are both kept and registered, but the comment suggests it should verify URLs
  - says: Ask the model where the sources with no host publish, and verify every answer.
- **foreman.py** `adopt_hosts` — [MEDIUM] Attempts to adopt hosts by running a script and checks for adoption count
  - says: Find a wiki for sources that have none. Entries with no host are uncitable forever.
- **feats_index.py** `_norm` — [MEDIUM] Folds a name to its comparable core, but does not strip parentheticals, contradicting a previous docstring claim that it did.
  - says: Fold a name to its comparable core. Case and punctuation differ freely between a wiki page title and the catalogue's entry name, and both are written by different passes. Alphanumerics only.
- **escalation.py** `clear` — [MEDIUM] The code catches ValueError and PermissionError, but the comment suggests they are the same event, which may not be accurate.
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller, and the two refusals are the same event to a reader: the lift did not happen and here is why.
- **escalation.py** `assert_clear` — [MEDIUM] raises an exception if the system is not halted, but the docstring says it's the interlock that makes the chain real and prevents the library from working while halted
  - says: EVERY entry point calls this before doing anything. The plant-wide interlock.
- **escalation.py** `escalate` — [MEDIUM] Rung 4, made DURABLE. Stop one subsystem until a person resumes it. -> the record.
  - says: Rung 4, made DURABLE. Stop one subsystem until a person resumes it.
- **drill.py** `CW._budget_left` — [MEDIUM] returns the budget and used counts, but the docstring says it's about spending and requiring it to run out
  - says: Spend the budget against a scratch ledger and require it to RUN OUT, then refill.
- **drill.py** `only_the_owner_rung_writes_a_halt` — [MEDIUM] the code checks for the existence of the halt file before escalating to OWNER, which may not have been created yet
  - says: a halt file appears at OWNER and at no rung below it
- **drill.py** `os.replace` — [MEDIUM] a stand-in that raises a PermissionError on the first attempt but allows subsequent calls
  - says: the function that performs a file rename
- **drill.py** `the_cap_resets_per_run` — [MEDIUM] ``blast_reset()` only clears the `patches` counter, not the `files` set, and the test is designed to check this
  - says: ``blast_reset()` clears the WHOLE budget, both halves of it.
- **drill.py** `LA._safe` — [MEDIUM] LA._safe is used to check a path that is supposed to be reachable, but the code indicates that the path is not reachable and the check is meant to verify that the path is accessible.
  - says: An ordinary in-surface path must still be reachable: a gate that refuses everything passes every refusal test ever written.
- **dashboard.py** `panelWatch` — [MEDIUM] displays swallowed failures but not all open findings
  - says: Overwatch — the standing sweep
- **dashboard.py** `hist` — [MEDIUM] is validated to be a list of dicts with numeric 'at' keys
  - says: THE GUARD HAS TO COVER THE FIELDS THE ARITHMETIC BELOW ACTUALLY USES
- **binding_health.py** `F.fetch` — [MEDIUM] fetch host and list of titles
  - says: fetch host and title
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
