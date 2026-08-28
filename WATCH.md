# OVERWATCH

round 115  ·  last run 2026-08-28 13:37

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **1** of 268,382 inspected  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**6 open** (2 high). Newest first.

- **descending_ladder.py** `rung_for_length` — [HIGH] Returns (rung, name) for sizes within the descending ladder, but returns (FOLD_RUNG, "Below the Fold") for sizes below the Planck length and (None, None) for sizes above the descen
  - says: Which descending rung does a given size belong to? Returns (rung, name).
- **dashboard.py** `movement` — [HIGH] calls a function named movement that may not exist
  - says: returns a section element with movement data
- **endpoint.py** `silence.replace_if_unchanged` — [MEDIUM] the function is used to handle staleness, but the call site was missed in the code
  - says: this call site was simply missed
- **drill.py** `_landing_nothing_is_not_success` — [MEDIUM] a run that was refused five times running was indistinguishable, to the caller closing the order, from work actually done
  - says: a run that proposed patches and landed NONE cannot report success
- **dashboard.py** `movement` — [MEDIUM] The code calculates deltas without considering that some counters may reset to zero, leading to negative deltas that are incorrectly reported as movement rather than resets.
  - says: A COUNTER THAT FELL IS NOT A COUNTER THAT MOVED.
- **dashboard.py** `movement` — [MEDIUM] Returns a list of metrics with their current values and deltas, but the delta calculation does not account for potential resets due to counter discontinuities, which can incorrectl
  - says: What has CHANGED, not what the level is.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
