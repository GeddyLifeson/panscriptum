# OVERWATCH

round 410  ·  last run 2026-09-07 02:06

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 298,265 inspected (deep scan as of round 409)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**12 open** (5 high). Newest first.

- **derivation.py** `scan_constants_with_reason` — [HIGH] The function is not defined in the provided code slice.
  - says: Module-level UPPERCASE assignments -- the only place a new constant can hide.
- **corpus_db.py** `deletion_check` — [HIGH] report unavailable when missing key
  - says: report deletions
- **corpus_db.py** `newer` — [HIGH] count of records that cannot be stat'ed
  - says: count of records written since index built
- **cleanup.py** `low_pref` — [HIGH] returns a single match as 'prefix' but the comment says it should be 'prefix-ambiguous'
  - says: finds a proper prefix with one match
- **chain.py** `main` — [HIGH] Does not handle the case where 'fit' returns an error and the edges are not written to the result file
  - says: Handles command line arguments and processes data accordingly.
- **dashboard.py** `panelWatch` — [MEDIUM] displays swallowed failures but not all open findings
  - says: Overwatch — the standing sweep
- **dashboard.py** `hist` — [MEDIUM] is validated to be a list of dicts with numeric 'at' keys
  - says: THE GUARD HAS TO COVER THE FIELDS THE ARITHMETIC BELOW ACTUALLY USES
- **dashboard.py** `hist` — [MEDIUM] is reset to an empty list on any exception during loading
  - says: A CORRUPT HISTORY FILE MUST HEAL, NOT WEDGE.
- **dashboard.py** `movement` — [MEDIUM] Computes deltas against the oldest sample inside the window, but the comment suggests it should report changes over time, not just deltas.
  - says: What has CHANGED, not what the level is.
- **chain.py** `fit` — [MEDIUM] Returns the result of RG.bradley_terry, which may not include Ford's condition check
  - says: Bradley-Terry over the recorded outcomes, with Ford's condition reported either way.
- **binding_health.py** `F.fetch` — [MEDIUM] fetch host and list of titles
  - says: fetch host and title
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
