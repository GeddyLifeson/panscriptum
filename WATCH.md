# OVERWATCH

round 559  ·  last run 2026-09-16 02:34

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 305,734 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**26 open** (6 high). Newest first.

- **foreman.py** `overwatch.save` — [HIGH] discards the failure silently
  - says: prints the denial itself and returns the same verdict `silence.write_json` gave
- **foreman.py** `kill_duplicate_jobs` — [HIGH] Returns False when duplicates are found but no process matched, and sometimes returns False when no duplicates were ended despite having found some.
  - says: Keep the OLDEST instance of each job and end the rest.
- **autostart.py** `silence` — [HIGH] is never defined in this slice
  - says: handles errors with retries and logging
- **autostart.py** `installed_state` — [HIGH] is never defined in this slice
  - says: returns the state of the launcher
- **drill.py** `CB.verify` — [HIGH] does not verify the archive against the live tree
  - says: is what anybody asks months later
- **drill.py** `CB.snapshot` — [HIGH] writes a snapshot and does not re-open it for verification
  - says: reopens the archive it wrote and re-hashes every member before recording success
- **catalogue_models.py** `sweep` — [MEDIUM] write a payload and return it, not actually interacting with providers
  - says: ask each provider what it actually serves
- **ledger_guard.py** `seal` — [MEDIUM] returns None on failure but does not raise an exception
  - says: seals the ledger hash chain
- **ledger_guard.py** `check_since_floor` — [MEDIUM] only checks against the all-time floor, not the current snapshot
  - says: checks for loss that compounds across pushes
- **ledger_guard.py** `check_since_snapshot` — [MEDIUM] only checks against the current snapshot, not the all-time floor
  - says: checks for loss that compounds across pushes
- **ledger_guard.py** `verify_chain` — [MEDIUM] only verifies hash, but does not check structure or floors
  - says: verifies hash chain integrity
- **ledger_guard.py** `check_all` — [MEDIUM] only checks structure and floors, but does not verify hash chain integrity
  - says: reports all ledger structure and floor issues
- **ledger_guard.py** `silence.append_line` — [MEDIUM] still uses the old shape
  - says: NOT A BARE `open(CHAIN, "a")`
- **hostcheck.py** `base` — [MEDIUM] The `base` variable is assigned the result of `null_rate(host, by=by, exclude=source) if by else None`, which may not correctly represent the baseline rate due to potential issues with the `null_rate` function's handling of the `exclude` parameter and the conditional logic.
  - says: The `null_rate` function is called with `by=by` to get the baseline rate for the host.
- **hostcheck.py** `score` — [MEDIUM] Calculates a score based on probe data and baseline comparisons, but the function's name and docstring suggest a more direct measurement of host performance against a baseline, not a comprehensive judgment of the host's overall quality or relevance.
  - says: One host, fully judged: how much of this roster it holds, ABOVE ITS OWN BASELINE.
- **hostcheck.py** `foreign` — [MEDIUM] is initialized as an empty list and then extended with names from the 'by' parameter, but the actual control sample is derived from the 'foreign' list after deduplication and sampling
  - says: builds a list of foreign names for the control sample
- **hostcheck.py** `candidates` — [MEDIUM] Returns the same flat `grounded + spec` list it has always returned.
  - says: Other hosts worth probing for this source, best first: grounded, then speculation.
- **foreman.py** `silence.write_json` — [MEDIUM] The code attempts to write the log but does not handle the case where writing is denied, leading to potential data loss.
  - says: A denied rename here loses this whole round from the operational record, and overnight.foreman_report() would then replay the PREVIOUS round as if it were this one -- i.e. report stale repairs as current.
- **foreman.py** `kill_stalled` — [MEDIUM] killed stalled or spared based on restartability and I/O activity
  - says: killed stalled
- **foreman.py** `CB._PROVEN[0]` — [MEDIUM] invalidates the cached proof by setting to None
  - says: force the next _alive() to re-read
- **chain.py** `singleton_release` — [MEDIUM] unconditionally releases a record that names itself
  - says: releases a record that names itself
- **chain.py** `live` — [MEDIUM] initialized to 0, then set to 1 if _RECIPE_KEY is in updates
  - says: Seeded at 1, not 0, when the recipe itself just changed above: that write belongs in this cycle's land even on an empty corpus (no file loop iteration would otherwise set `changed`)
- **drill.py** `_LIVE_HOOK` — [MEDIUM] the audit hook is not checked for failures
  - says: the audit hook failed
- **drill.py** `GL._take_slot` — [MEDIUM] return a slot
  - says: arbitrate a slot
- **drill.py** `GL.lane` — [MEDIUM] create a context manager for a lane
  - says: arbitrate a lane
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
