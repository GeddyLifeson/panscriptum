# OVERWATCH

round 96  ·  last run 2026-08-27 02:30

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 230,350 inspected
- catalogued sources with no host: **9** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major
- NOT RUNNING: **0** feats.py --roll

## What the model found in the code

**9 open** (2 high). Newest first.

- **binding_health.py** `verdict` — [HIGH] The verdict function is not properly handling the absent probe's three possible outcomes (None, False, True), leading to incorrect classification of host faults.
  - says: The three probe outcomes -> (healthy, reason).
- **genre.py** `classify_source` — [HIGH] Truncates the entry list in stored order, changing the answer for 7 of 210 sources
  - says: Classify one source from its own catalogued entries.
- **build_terminal.py** `descend` — [MEDIUM] descend(key) is called with key as a parameter, but the function is designed to handle the key as a parameter, so there is no discrepancy
  - says: descend(key) is called with key as a parameter
- **backfill.py** `F.api` — [MEDIUM] returns None on timeout or nothing found
  - says: used to fold that into an empty page list here too
- **backfill.py** `lead` — [MEDIUM] extract a lead sentence from a block of text
  - says: take the lead from there
- **axis_correlation.py** `_pearson` — [MEDIUM] Computes Pearson correlation coefficient using population standard deviation (divided by n) without the (n-1) correction
  - says: Computes Pearson correlation coefficient using sample standard deviation (divided by n-1)
- **autostart.py** `subprocess.Popen` — [MEDIUM] returns a subprocess.Popen object immediately without waiting for it to complete
  - says: launches a subprocess
- **assay.py** `sigma` — [MEDIUM] clamp the sigma value to SIGMA_MAX but the code does not handle the case where sigma is None
  - says: clamp the sigma value to SIGMA_MAX
- **address_space.py** `C.GALAXIES_DEFAULT` — [MEDIUM] the default number of galaxies per universe as defined in the cosmography module
  - says: the number of galaxies per universe

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
