# OVERWATCH

round 441  ·  last run 2026-09-08 08:17

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 300,109 inspected (deep scan as of round 439)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**30 open** (11 high). Newest first.

- **binding_health.py** `return True, "correctly absent -- nothing came back for a title that cannot exist"` — [HIGH] Returns True, indicating the host is 'correctly absent', but according to the docstring, this should indicate the host is not answering (could not ask) or the host is answering yes to everything.
  - says: Does this host correctly say NO to a title nobody holds? -> (ok, detail).
- **assay.py** `axis_correlation.rho` — [HIGH] is used in the covariance calculation
  - says: had no callers, because its only caller had been rewritten from scratch here
- **verify_math.py** `_flowsecs19ab` — [HIGH] the check passes when the fast path is used, which is the opposite of what is claimed
  - says: and the verdict came from the PROBE, not from the ledger shortcut
- **verify_math.py** `_flowok19ab` — [HIGH] the check passes when the predicate returns False, which is the opposite of what is claimed
  - says: a reasoning model's truncated generation reads as FLOW, not a wedge
- **verify_math.py** `_gl_direct` — [HIGH] the local leg exceeds the card's slot count (regime says 'cloud')
  - says: the local leg never exceeds the card's slot count (regime says 'cloud')
- **thread_integrity.py** `main` — [HIGH] returns 1 if failed else 0
  - says: THE VERDICT REACHES THE EXIT CODE, WHICH IS THE ONLY THING WATCHING (order aa075aa80f5c). `main()` had no `return` on any path and was invoked bare, so the process always exited 0 -- and `allsweep` reads the rc and nothing else. A run in which EVERY implied thread was DANGLING was byte-identical, to its only automated consumer, to a run in which none was. The comment two hundred lines up states the premise ("main() is the ONLY reporting surface this module has") and stopped one step short of the consequence. Same defect `allsweep` records as just fixed for rosetta.py: "main() returned 0 whatever the rhos said".
- **silence.py** `replace_retry` — [HIGH] Raises on other OSError
  - says: Never raises on a denied replace
- **silence.py** `audit` — [HIGH] audit() returns rows of handlers, but the function's name and docstring imply it should audit for silent handlers, not return all catch sites
  - says: audit(root=None)
- **secondopinion.py** `mine_says` — [HIGH] mine_says is not defined in the provided code, and the code uses a different approach to get the secrets count
  - says: mine_says(paths) is called to get the secrets count
- **onomast.py** `load_onomasticon` — [HIGH] Returns an empty dict on FileNotFoundError and on unreadable files, overwriting existing data instead of refusing to overwrite.
  - says: Load the onomasticon from a file, returning the content or an empty dict on error.
- **onomast.py** `well_formed` — [HIGH] Implements seven constraints, but the docstring claims the function was meant to have four constraints and incorrectly attributes three of the four to the wrong constraints
  - says: Is this a name a Custos could say aloud and write down twice the same way?
- **binding_health.py** `_land` — [MEDIUM] land is not defined in this file or its imports
  - says: land
- **binding_health.py** `_land_cas` — [MEDIUM] land_cas is not defined in this file or its imports
  - says: land_cas
- **binding_health.py** `filtered` — [MEDIUM] filtered is a boolean that is True if only is truthy or limit is not None, but the code uses it as a flag for whether filtering was applied, which is not the same as the actual filtering logic.
  - says: WAS THIS PASS FILTERED AT ALL? Asked once, here, and used for every downstream decision, because the three sites below each asked it again as `only or limit` and a falsy-but-given `--limit 0` answered "no" to all of them (orders cd7492eec3bc and f1901d2178ba).
- **assay.py** `interval_from_hands` — [MEDIUM] Derive the published +/- from the Hands' divergence, but the code does not fully implement the two hard constraints from the charter
  - says: Derive the published +/- from the Hands' divergence. Vol. 0.5 §2, Theorem 4.
- **assay.py** `scores` — [MEDIUM] A ROW WITHOUT THIS KEY IS "NOT RECORDED", NEVER ZERO
  - says: A ROW WITHOUT THIS KEY IS "NOT RECORDED", NEVER ZERO
- **address.py** `promote` — [MEDIUM] promote is called with 'set' and 12, but the function's purpose is unclear and may not be intended for this use case
  - says: promote('set', 12)
- **verify_math.py** `_b4_axis_correlation_checks` — [MEDIUM] Uses AC.rho and A._rho which may not be the intended methods for testing the fallback value
  - says: Checks that axis_correlation.rho() and assay._rho() agree on the missing-matrix fallback
- **verify_math.py** `_b4_secondopinion_checks` — [MEDIUM] Modifies SO.RUFF_RULES and uses SO._ruff and SO._vulture, which may not be the intended methods for testing tool resolution
  - says: Checks that secondopinion's tool resolution behaves as expected
- **verify_math.py** `max` — [MEDIUM] compares two integers exactly, but the code is written to use a tolerance which is not applied
  - says: Auerbach 1913 / Zipf 1949; q = 1 is the classical rule. Integer populations, compared exactly -- no tolerance, because a tolerance on two ints is discarded
- **thread_integrity.py** `out` — [MEDIUM] increments the count for implied-unrecorded pairs when it should be for partially dangling
  - says: counts implied-unrecorded pairs
- **thread_integrity.py** `out` — [MEDIUM] increments the count for partially dangling pairs when it should be for implied-unrecorded
  - says: counts partially dangling pairs
- **overwatch.py** `codewatch.exit_if_stale` — [MEDIUM] Exits with rc=17 if the process is stale
  - says: Exits with rc=17 on purpose
- **mutate.py** `run` — [MEDIUM] execute a target and return results
  - says: run a target
- **mutate.py** `could_not_judge` — [MEDIUM] returns True if the signature starts with 'TIMEOUT' or 'ERROR:'
  - says: -> True if this signature means the gate never reached a verdict, on clean code OR on a mutant.
- **local_agent.py** `out` — [MEDIUM] overwritten by the loop's final return
  - says: the final output of the loop
- **local_agent.py** `t_find_symbol` — [MEDIUM] Returns a list of hits with file, line, and kind, but does not provide uniqueness verdict or enclosing class information as claimed.
  - says: Every definition of `name`, with its enclosing class and a uniqueness verdict.
- **ingest_doc.py** `bad_category` — [MEDIUM] bad_category is a counter for invalid categories, not a mechanism for substitution
  - says: bad_category is what makes the substitution visible instead of silent
- **ingest_doc.py** `write_record_catalogue` — [MEDIUM] write_record_catalogue is used for writing to the catalogue, not for merging records
  - says: write_record's disk-wins merge DISCARDED the first 14 entities this module ever found
- **descending_ladder.py** `rung_for_length` — [MEDIUM] Returns (rung, name) for sizes within the DESCENDING range, but returns (None, None) for sizes above the range, and a Fold name for sizes below the Planck length. However, the function's docstring states that the domain is bounded at both ends and out-of-domain is answered with (None, None) at both ends, but the function returns a Fold name for sizes below the Planck length, which is not explicitly mentioned in the docstring.
  - says: Which descending rung does a given size belong to? Returns (rung, name).

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
