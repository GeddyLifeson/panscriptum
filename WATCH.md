# OVERWATCH

round 527  ·  last run 2026-09-14 20:08

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,777 inspected (deep scan as of round 523)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**13 open** (3 high). Newest first.

- **allsweep.py** `reconcile` — [HIGH] not defined in the slice
  - says: where the subsystems disagree
- **binding_health.py** `filtered` — [HIGH] filtered is a boolean that is True if only is truthy or limit is not None, but it is not used in any downstream decision
  - says: WAS THIS PASS FILTERED AT ALL? Asked once, here, and used for every downstream decision
- **binding_health.py** `return False, ("%d known-present title(s) %s all returned nothing or too little to be a page (tried: %s)" % (len(tried), _of, ` — [HIGH] it does instead
  - says: the code says it does
- **citecheck.py** `_classify` — [MEDIUM] returns None when the citation is not provably broken, but also returns PAST_EOF for line 0 even though the citation is invalid
  - says: -> a reason constant, or None when the citation is not provably broken.
- **chain.py** `write_result` — [MEDIUM] is called twice with the same `edges`, `res`, and `unmatched` but only the first call's result is checked for landing
  - says: persist `names` and `strengths` whole
- **chain.py** `refresh_continuity` — [MEDIUM] Recomputes `continuity` for rows with `contin,uity: None` using the current inventory, but the function's name and description suggest it should patch rows that were previously unresolved due to an outdated inventory, not recompute continuity from stored fields.
  - says: Patch harvest-index rows still stamped `continuity: None` that a CURRENT designator inventory can now resolve.
- **catalogue_codex.py** `roll_landed` — [MEDIUM] the records were written to disk but the roll does not yet say so
  - says: the records land
- **binding_health.py** `_land` — [MEDIUM] the canary results are still returned but the code does not explicitly state this
  - says: the canary results are still returned -- the run happened
- **binding_health.py** `_land_cas` — [MEDIUM] discards the failure and returns a default value
  - says: deliberately RE-RAISES whatever stopped the temp copy being written
- **backfill.py** `main` — [MEDIUM] returns 1 if failed else 0
  - says: returns 1 if denied else 0
- **backfill.py** `backfill_source` — [MEDIUM] not used in this context
  - says: careful to distinguish used to die here
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0
- **feats.py** `main` — [MEDIUM] returns 0 or 1 based on the roll's success, but the comment claims it should follow the same pattern as `--hosts` and `resolve_hosts` which return 1 if _HOSTS_DENIED else 0 and exit nonzero on failure
  - says: the sibling branches in this same file already do it: `--hosts` twenty lines up returns `1 if _HOSTS_DENIED else 0`, and `resolve_hosts`'s own docstring promises "main() exits nonzero on it". `--roll` was the one place the pattern was never applied, even though `roll()` has always returned exactly the counters needed.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
