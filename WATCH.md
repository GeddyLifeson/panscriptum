# OVERWATCH

round 205  ·  last run 2026-08-30 12:55

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 281,220 inspected  — state\gpu_lane\slot.2.json — cannot stat
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**12 open** (2 high). Newest first.

- **silence.py** `_handler_is_observed` — [HIGH] Checks for the presence of the substring 'raise' in the AST dump of the handler's statements, which cannot detect re-raises due to case sensitivity
  - says: Does this `except` body leave a trace of the exception it caught? -> bool.
- **sevenfold.py** `write_json` — [HIGH] discards the verdict and printed "wrote {p}" regardless
  - says: returns whether the rename LANDED
- **scout.py** `sweep` — [MEDIUM] orders its work-list by last-attempted first, entry count only breaking ties among equally stale sources, and takes `order[:limit]`
  - says: HARD RULE 0, AND THE SHAPE THAT LOOKED LIKE COMPLIANCE. This ordered its work-list by entry count and then took `order[:limit]`, with `foreman.scout_hostless()` calling it as `sweep(limit=4)` on a 30-second loop. Ranking is allowed and truncating is not, and the reason is visible here rather than theoretical: a source LEAVES `hostless()` only when a scout SUCCEEDS. A source that keeps failing therefore stays hostless, stays among the four largest, and is re-scouted every thirty seconds for ever -- while everything ranked fifth and below is never attempted once. The window could not rotate, because the only thing that moved a source out of it was the very success that was not happening. Measured at the time this was fixed: 15 hostless sources, of which 4 could ever be reached.
- **rigor.py** `lognormal_product` — [MEDIUM] calculates a product of log-normal distributions for a list of factors
  - says: the census as a product of uncertain factors
- **rigor.py** `measure_bit_value` — [MEDIUM] The function uses the corrected value (L / 10.0), but the docstring still references the pre-fixed incorrect example (7.0 * 13.23 = 92.6).
  - says: THE NUMBERS ABOVE WERE WRONG UNTIL 2026-08-25 (run #21) AND THE WRONG ONES ARE INSTRUCTIVE.
- **rigor.py** `measure_bit_value` — [MEDIUM] Returns L / 10.0, where L is the band resolution, but the docstring claims it's the bit-worth of one point on a decimal axis.
  - says: The bit-worth of ONE point on any decimal axis at a given band.
- **rigor.py** `prob_at_least_one` — [MEDIUM] calculates the probability of at least one event occurring in a log-normal distribution
  - says: the census as a product of uncertain factors
- **rigor.py** `lognormal_product` — [MEDIUM] calculates a product of log-normal distributions for a list of uncertain factors
  - says: the census as a product of uncertain factors
- **retry_synthesis.py** `save_side` — [MEDIUM] The function save_side is called but its implementation is not provided in the given code slice, leading to a potential runtime error or undefined behavior.
  - says: Take the MERGED mapping back, so this run's own tally counts what is actually on disk rather than only what this process rescued -- see `save_side`. The second half of that return says whether it reached disk at all; a rescue that did not land must not print like one that did, because nothing re-runs the model call behind it.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops
- **foreman.py** `kill_stalled` — [MEDIUM] kill stalled jobs that can be restarted, and escalate those that cannot
  - says: kill stalled jobs
- **drill.py** `silence.write_json` — [MEDIUM] writes to a file that can be read by other processes, but the code around it suggests that the file should be written in a way that ensures readers see the complete data
  - says: this project's stated one correct way to land a shared file

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
