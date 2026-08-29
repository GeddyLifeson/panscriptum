# OVERWATCH

round 163  ·  last run 2026-08-29 15:11

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **0** of 274,390 inspected
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**1 open** (1 high). Newest first.

- **axis_correlation.py** `rho` — [HIGH] Returns 0.0 when the matrix is missing, which contradicts the claim that it returns the measured mean for unmeasured pairs
  - says: Correlation between two axes. -> float.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
