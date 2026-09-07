# OVERWATCH

round 420  ·  last run 2026-09-07 12:48

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 298,873 inspected (deep scan as of round 415)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**18 open** (8 high). Newest first.

- **rosetta.py** `silence.write_json` — [HIGH] overwrites without checking if the new mine is larger
  - says: DO NOT OVERWRITE A BIGGER MINE WITH A SMALLER ONE WITHOUT SAYING SO (order 6447bcc2f18c)
- **rosetta.py** `kept` — [HIGH] kept counts rows before they are filtered by the 4-row floor
  - says: kept MUST ONLY COUNT ROWS THAT SURVIVE INTO `out`
- **roll.py** `apply` — [HIGH] Apply a function to rows, returning the modified rows.
  - says: Apply `{source_name: {field: value, ...}}` to the roll, key-wise.
- **rigor.py** `identified` — [HIGH] the code checks for a single component but the variable is used in a condition that implies the absence of undefeated or winless entrants
  - says: the beat graph is ONE strongly connected component spanning every entrant
- **retry_synthesis.py** `PL.ask_pool_first` — [HIGH] calls a different model than phase_synthesis
  - says: calls the same transport as phase_synthesis
- **render.py** `main` — [HIGH] returns 1 on success
  - says: returns 0 on success
- **read.py** `priority` — [HIGH] Sorted purely by own-page size
  - says: Depth first, because depth is what the model is actually better at.
- **overnight.py** `preflight` — [HIGH] Returns (n_failing_checks, blocking) even when health.py crashes or cannot be launched, which contradicts the claim that it returns only when there are corrupted source blocks.
  - says: Returns (n_failing_checks, blocking). Only corrupted source blocks.
- **scope.py** `best` — [MEDIUM] best is set to None if nothing clears the floor, which is then returned as None, implying no scope established
  - says: Nothing clears the floor means nothing was established, and that is a real answer.
- **rosetta.py** `check` — [MEDIUM] check() is called with rosetta and assays, but the docstring refers to a bare-name lookup that scored 0 overlap on all eight standing scales, which is not directly related to the parameters passed to check()
  - says: check()'s docstring on the bare-name lookup that scored 0 overlap on all eight standing scales.
- **rosetta.py** `kept` — [MEDIUM] kept is incremented before potential filtering by the 4-row floor
  - says: kept + dropped stayed arithmetically equal to the pre-refine total
- **rigor.py** `lognormal_product` — [MEDIUM] used in a context that does not match the comment's claim about adjudication auditing
  - says: A SEVENTH ADJUDICATION CANNOT SILENTLY GO UNAUDITED (order 7368cd63bd2c, the remedy's second half).
- **retry_synthesis.py** `PL.write_record` — [MEDIUM] re-reads the file and MERGES, but the code around it suggests it should be used to derive a value rather than perform an action
  - says: re-reads the file and MERGES, precisely so a stale in-memory copy cannot be published over a fresher disk one
- **retry_synthesis.py** `PL.valid_scale_note` — [MEDIUM] validates a truncated string
  - says: validates the whole string
- **resync_roll.py** `by_source` — [MEDIUM] indexes by the normalized version of the source name
  - says: index every record file by its declared `source`
- **policy.py** `evidence_unreadable_detail` — [MEDIUM] only the file names are included, but the error message is truncated to 40 characters
  - says: every failure, every vacuous pass and every unreadable file is named in full, here and in the report
- **overnight.py** `join` — [MEDIUM] join the roll process with a timeout
  - says: absorb the new feats into ceilings and per-entry judgements
- **overnight.py** `codewatch` — [MEDIUM] imported but not used
  - says: BOUND TO A VALUE, NOT LEFT UNDEFINED

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
