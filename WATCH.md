# OVERWATCH

round 423  ·  last run 2026-09-07 15:00

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 299,182 inspected (deep scan as of round 421)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**12 open** (5 high). Newest first.

- **verify_math.py** `path` — [HIGH] is read from the entire module, not the function's scope
  - says: is scoped to the function
- **verify_math.py** `call_idxs` — [HIGH] was deleted due to a conditional check that no longer exists
  - says: finds the call site of verify_restore
- **verify_math.py** `A._interval` — [HIGH] the code inverts the guard, which turns the one safe case into the crash case and vice versa
  - says: Between-hand dispersion is only defined for MORE THAN ONE reading
- **verify_math.py** `_chunk_key` — [HIGH] produces the same key for entities reading the same passage
  - says: two entities reading the SAME passage get different cache keys
- **verify_math.py** `check` — [HIGH] ignores tolerance when the want is an integer
  - says: compares values with tolerance
- **weave.py** `pair_weights` — [MEDIUM] Summed idf of everything each source-pair shares, but with no cap on the contribution of each entity, which can lead to overcounting.
  - says: Summed idf of everything each source-pair shares.
- **verify_math.py** `_ALL_SRC` — [MEDIUM] list of all .py files in the current directory (not necessarily the src directory)
  - says: list of all .py files in the src directory
- **verify_math.py** `_pool19ai` — [MEDIUM] Returns a mock object when the standard is absent, but the code around it expects it to return a real standard or raise an error
  - says: Run the real standards.check() over a synthetic throughput window.
- **verify_math.py** `BG.HAMLET_FLOOR` — [MEDIUM] the value is re-spelt here instead of read from the module
  - says: the floor was RE-SPELT here rather than read, which is the "one spelling in one place" rule broken
- **verify_math.py** `max` — [MEDIUM] the comparison falls through to exact equality, and the tolerance is silently discarded
  - says: Auerbach 1913 / Zipf 1949; q = 1 is the classical rule. Integer populations, compared exactly -- no tolerance, because a tolerance on two ints is discarded
- **tuning.py** `cloud_success_rate` — [MEDIUM] The function returns (None, 0) when there's an exception, which is not treated as a fault, but the docstring says it's never treated as a fault. However, the function's path is hardcoded, which may not be the intended location.
  - says: The pool's MEASURED success rate over the recent past: (rate, calls).
- **tiers.py** `deliberate_joins` — [MEDIUM] the names are cut with nothing marking it
  - says: THE TWO SOURCE NAMES SAY WHEN THEY ARE CUT (orders 1d1ac500342d, fe99e57e1993). These were `a[:26]` and `b[:26]`, bare slices, on the panel titled "why a xenoverse is 'artificial'" -- the panel `deliberate_joins()`'s own docstring calls THE EVIDENCE. An earlier repair (order 9861c18b8485) uncapped the row count and the shared-evidence list on this very block and left the names themselves cut with nothing marking it.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
