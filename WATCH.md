# OVERWATCH

round 526  ·  last run 2026-09-14 18:02

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,777 inspected (deep scan as of round 523)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**11 open** (4 high). Newest first.

- **allsweep.py** `reconcile` — [HIGH] not defined in the slice
  - says: where the subsystems disagree
- **binding_health.py** `filtered` — [HIGH] filtered is a boolean that is True if only is truthy or limit is not None, but it is not used in any downstream decision
  - says: WAS THIS PASS FILTERED AT ALL? Asked once, here, and used for every downstream decision
- **binding_health.py** `return False, ("%d known-present title(s) %s all returned nothing or too little to be a page (tried: %s)" % (len(tried), _of, ` — [HIGH] it does instead
  - says: the code says it does
- **canon_backup.py** `replace_retry` — [HIGH] the function is called but its result is ignored, and the code proceeds to raise an exception regardless of the result
  - says: THE VERDICT IS CHECKED, WHICH IS THE HALF THAT MATTERS. `replace_retry` NEVER RAISES, by contract; it reports False.
- **binding_health.py** `_land` — [MEDIUM] the canary results are still returned but the code does not explicitly state this
  - says: the canary results are still returned -- the run happened
- **binding_health.py** `_land_cas` — [MEDIUM] discards the failure and returns a default value
  - says: deliberately RE-RAISES whatever stopped the temp copy being written
- **backfill.py** `main` — [MEDIUM] returns 1 if failed else 0
  - says: returns 1 if denied else 0
- **backfill.py** `backfill_source` — [MEDIUM] not used in this context
  - says: careful to distinguish used to die here
- **catalogue_models.py** `last` — [MEDIUM] a single-line exception repr with type and message joined by a space
  - says: a single-line exception repr
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0
- **feats.py** `main` — [MEDIUM] returns 0 or 1 based on the roll's success, but the comment claims it should follow the same pattern as `--hosts` and `resolve_hosts` which return 1 if _HOSTS_DENIED else 0 and exit nonzero on failure
  - says: the sibling branches in this same file already do it: `--hosts` twenty lines up returns `1 if _HOSTS_DENIED else 0`, and `resolve_hosts`'s own docstring promises "main() exits nonzero on it". `--roll` was the one place the pattern was never applied, even though `roll()` has always returned exactly the counters needed.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
