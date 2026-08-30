# OVERWATCH

round 180  ·  last run 2026-08-29 22:41

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 276,686 inspected (deep scan as of round 175)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**5 open** (2 high). Newest first.

- **assay.py** `interval` — [HIGH] the interval is the square root of the sum of half_spread squared and floor squared, which represents the combined variance of prior divergence and evidence-quality noise
  - says: the interval is prior divergence, not ignorance
- **assay.py** `_interval` — [HIGH] The code calculates variance but misses the covariance term which is the larger half of the error bar calculation.
  - says: Half-width of the honest error bar, in BAND units, by variance propagation.
- **autostart.py** `subprocess.Popen` — [MEDIUM] return a Popen object without properly closing file handles
  - says: start a new process
- **assay.py** `denom` — [MEDIUM] sums WEIGHTS over applicable axes but adds 1.0 as a fallback when the sum is zero
  - says: sums WEIGHTS over applicable axes
- **assay.py** `_rho` — [MEDIUM] Returns 0.0 when no documentation is available, but the code delegates to axis_correlation.rho which is supposed to handle the correlation calculation.
  - says: Measured correlation between two Measures. -> float in [-1, 1].

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
