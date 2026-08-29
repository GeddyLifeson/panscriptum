# OVERWATCH

round 156  ·  last run 2026-08-29 11:23

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 273,179 inspected (deep scan as of round 151)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**3 open** (1 high). Newest first.

- **chain.py** `adjudicate_mutuals` — [HIGH] Splits mutual pairs by epoch, but does not actually split them in time as described in the docstring. The function's logic is flawed in how it handles the dating and re-keying of n
  - says: Split mutual pairs in time before fitting anything to them.
- **chain.py** `write_result` — [MEDIUM] called twice with the same parameters
  - says: write the result to the output file
- **assay.py** `used` — [MEDIUM] A subset of scored axes that are numeric
  - says: A subset of scored axes

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
