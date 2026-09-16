# OVERWATCH

round 561  ·  last run 2026-09-16 04:05

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 305,734 inspected (deep scan as of round 559)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**19 open** (4 high). Newest first.

- **corpus_db.py** `rebuild` — [HIGH] Rebuilds the index but does not actually process the canonical JSON data as described, instead handling WIKI_HOSTS.json and COVERAGE.json files and attempting to connect to a temporary database without fully implementing the described index rebuilding logic.
  - says: Rebuild the index from the canonical JSON. -> counts.
- **build_terminal.py** `esc` — [HIGH] some catalogue-derived strings bypass it, like shelfmark and the four f.* rows in selectWorld
  - says: every catalogue-derived string goes through this before it reaches innerHTML
- **foreman.py** `overwatch.save` — [HIGH] discards the failure silently
  - says: prints the denial itself and returns the same verdict `silence.write_json` gave
- **foreman.py** `kill_duplicate_jobs` — [HIGH] Returns False when duplicates are found but no process matched, and sometimes returns False when no duplicates were ended despite having found some.
  - says: Keep the OLDEST instance of each job and end the rest.
- **corpus_db.py** `code` — [MEDIUM] is set to None when code is 'UNASSIGNED'
  - says: NULL means unshelved, and only the resolver may say so
- **compress_store.py** `load` — [MEDIUM] Reads a stored blob back, decompresses it, and checks if the decompressed text's hash matches the filename's hash, raising an error if they don't match.
  - says: Read a stored blob back, VERIFYING it against the address it is filed under.
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
- **hostcheck.py** `candidates` — [MEDIUM] Returns the same flat `grounded + spec` list it has always returned.
  - says: Other hosts worth probing for this source, best first: grounded, then speculation.
- **foreman.py** `silence.write_json` — [MEDIUM] The code attempts to write the log but does not handle the case where writing is denied, leading to potential data loss.
  - says: A denied rename here loses this whole round from the operational record, and overnight.foreman_report() would then replay the PREVIOUS round as if it were this one -- i.e. report stale repairs as current.
- **foreman.py** `kill_stalled` — [MEDIUM] killed stalled or spared based on restartability and I/O activity
  - says: killed stalled
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
