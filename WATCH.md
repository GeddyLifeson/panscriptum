# OVERWATCH

round 524  ·  last run 2026-09-14 17:19

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,777 inspected (deep scan as of round 523)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**5 open** (1 high). Newest first.

- **rigor.py** `measure_bit_value` — [HIGH] Returns L / 10.0 where L is the band resolution, but the docstring claims it should return the bit-worth of a single point which is L_r / 10 bits. However, the example in the docstring uses 7.0 * 13.23 = 92.6 which is using a different value (13.23) instead of the current value (which is L / 10.0). The docstring also mentions that the numbers were wrong until 2026-08-25 and the example was not corrected, leading to a discrepancy between the code and the docstring.
  - says: The bit-worth of ONE point on any decimal axis at a given band.
- **rigor.py** `prob_at_least_one` — [MEDIUM] the function may not be correctly calculating the probability due to potential issues in the implementation
  - says: calculates the probability of at least one occurrence
- **rigor.py** `lognormal_product` — [MEDIUM] used in a context where it's expected to compute a product of uncertain factors but the code may not be handling the lognormal distribution correctly
  - says: computes the product of uncertain factors
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0
- **feats.py** `main` — [MEDIUM] returns 0 or 1 based on the roll's success, but the comment claims it should follow the same pattern as `--hosts` and `resolve_hosts` which return 1 if _HOSTS_DENIED else 0 and exit nonzero on failure
  - says: the sibling branches in this same file already do it: `--hosts` twenty lines up returns `1 if _HOSTS_DENIED else 0`, and `resolve_hosts`'s own docstring promises "main() exits nonzero on it". `--roll` was the one place the pattern was never applied, even though `roll()` has always returned exactly the counters needed.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
