# OVERWATCH

round 446  ·  last run 2026-09-08 19:56

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 301,105 inspected (deep scan as of round 445)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py
- NOT RUNNING: **0** read.py

## What the model found in the code

**9 open** (4 high). Newest first.

- **escalation.py** `landed` — [HIGH] what it does instead
  - says: what the code says it does
- **drill.py** `resync_cannot_revert_an_exclusion` — [HIGH] The code is incomplete and does not fully implement the logic described in the comment about the trap.
  - says: THE TRAP THIS ALMOST FELL INTO. `resync_roll` rebuilds status from records on disk with the rule `catalogued if n else keep` -- so an excluded source that still HAS records would be silently promoted back. All four of the 2026-08-35 exclusions have records.
- **drill.py** `the_liveness_probe_retries_and_names_what_it_found` — [HIGH] The function does not actually perform the liveness probe as described. Instead, it modifies the `F.api` function to simulate different API outcomes and checks if the `check_api_paths()` function correctly identifies the fault type. The actual behavior is testing the `check_api_paths()` function's ability to distinguish between different fault types, not performing the liveness probe itself.
  - says: This is the preflight's liveness probe. It made ONE attempt per host family (`retries=0` against feats.api's default of 2), so a single DNS hiccup or TLS handshake failure -- documented, live faults on this machine -- became a preflight problem, a stamped row in state/preflight_last.json, a filed MAJOR order and an rc=1 cycle, for a condition that had already cleared. `check_caches` in the same file states the doctrine: "A permanent red is not extra safety; it is how a preflight stops being read." And it did not pass api()'s `outcome` dict, so "fandom API unreachable" was emitted identically for the wrong API path -- the 404 that cost 5,590 entries and is this check's whole stated purpose -- and for a transient network fault. Two faults with opposite remedies, one sentence. api() separates them and its own docstring says that channel exists because collapsing them "is NOT tolerable for a liveness probe".
- **completeness.py** `land` — [HIGH] Returns a third outcome SKIPPED_ONLY, which is truthy but does not indicate the file holds `rows`
  - says: Returns True if the file now holds `rows`
- **escalation.py** `landed` — [MEDIUM] the file and the log agree
  - says: the file and the log disagree
- **escalation.py** `resume_subsystem_verdict` — [MEDIUM] Returns a bool and reason, but the actual behavior is to return a bool and a reason that indicates whether the resume was successful or not, which is consistent with the claim.
  - says: Re-open one subsystem. -> (bool, reason). The three-valued sibling of `resume_subsystem`.
- **drill.py** `silence.write_json` — [MEDIUM] writes to a file but does not handle exceptions or errors that may occur during the write operation
  - says: this project's stated one correct way to land a shared file
- **derivation.py** `main` — [MEDIUM] returns 1 when problems is non-empty, 0 when empty
  - says: RETURNING EARLY RATHER THAN BOUNDING THE WALK, of the order's two remedies.
- **derivation.py** `scan_constants` — [MEDIUM] Delegates to `scan_constants_with_reason` and ignores the reason, which is exactly what this signature can express: a list of (NAME, literal_count), or `None` when the module could not be scanned for either reason.
  - says: Module-level UPPERCASE assignments -- the only place a new constant can hide.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
