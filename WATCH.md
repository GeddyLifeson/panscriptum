# OVERWATCH

round 415  ·  last run 2026-09-07 07:15

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 298,873 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**36 open** (9 high). Newest first.

- **manifest_builder.py** `write_json` — [HIGH] discarded the verdict and printed "Wrote N jobs" regardless
  - says: returns whether the rename LANDED
- **ingest_doc.py** `state_p` — [HIGH] used but never defined in this file or its imports
  - says: path to ingest state file
- **hostcheck.py** `purge-record` — [HIGH] the function silently deletes files without recording the deletion
  - says: the gap it leaves is a recorded finding rather than a silence
- **hostcheck.py** `candidates` — [HIGH] Returns the same flat `grounded + spec` list it has always returned, but the comment says callers must use `candidates_split` to bound the tail.
  - says: Other hosts worth probing for this source, best first: grounded, then speculation.
- **health.py** `excluded_dirs` — [HIGH] A host is excused if any source on it is excluded
  - says: A host is only excused when EVERY source on it is excluded
- **genre.py** `classify_source` — [HIGH] Truncates the entry list in stored order and changes the answer for 7 of 210 sources
  - says: Classify one source from its own catalogued entries.
- **generate.py** `failures.pop` — [HIGH] removes a failure entry from the failures list even if the chapter was successfully catalogued
  - says: A DEAD REFUSAL MUST NOT READ LIKE A LIVE ONE
- **estate.py** `low` — [HIGH] low is a variable that is used but never defined in this file or its imports
  - says: low is a variable that is supposed to represent the combined lowercase text of the bottom three bands' descriptions
- **endpoint.py** `html_text` — [HIGH] Defined in another module, but not imported here
  - says: Extract text from HTML body
- **magnitude.py** `band_hits` — [MEDIUM] counts BAND MATCHES ONLY
  - says: counts BAND MATCHES ONLY
- **local_agent.py** `out` — [MEDIUM] a dictionary that is modified in multiple places, leading to potential confusion about its final state
  - says: the final output dictionary
- **local_agent.py** `timeout` — [MEDIUM] Set to 1800.0 if not provided, but the code also sets timeout to 420 in a comment that is not used
  - says: Set to 1800.0 if not provided
- **local_agent.py** `denied` — [MEDIUM] Matches on the module name if it's in the denylist, otherwise matches on the repo-relative path if it's in the denylist paths
  - says: Match on the module name when there is one, and on the repo-relative path otherwise.
- **ledger_guard.py** `verify_chain` — [MEDIUM] only checks part of the ledgers
  - says: check the relay's ledgers
- **ledger_guard.py** `check_all` — [MEDIUM] only checks part of the ledgers
  - says: check the relay's ledgers
- **hostcheck.py** `relevance` — [MEDIUM] Returns a rate based on a subset of titles, not the full set, and the denominator is not the total number of existing articles.
  - says: Of the articles that DO exist here, how many are about this fiction? -> (rate, n).
- **health.py** `preflight` — [MEDIUM] Writes a stamp file that may or may not be written, and returns the number of problems found
  - says: Run every preflight check. -> the number of problems found.
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
- **dashboard.py** `hist` — [MEDIUM] is validated to be a list of dicts with numeric 'at' keys
  - says: THE GUARD HAS TO COVER THE FIELDS THE ARITHMETIC BELOW ACTUALLY USES
- **binding_health.py** `F.fetch` — [MEDIUM] fetch host and list of titles
  - says: fetch host and title
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
