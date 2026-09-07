# OVERWATCH

round 403  ·  last run 2026-09-06 20:49

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 298,036 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**5 open** (1 high). Newest first.

- **withdraw_chapters.py** `select` — [HIGH] the function `select` is called with `a.source` and `a.addr` but the code does not check if either selector matches anything in the catalog. The code only checks if the entire selection is empty, which is not the same as checking each selector independently. The comment suggests that each selector should be checked independently, but the code does not do that. The code only checks if the entire selection is empty, which is not the same as checking each selector independently. The comment suggests that each selector should be checked independently, but the code does not do that.
  - says: PER SELECTOR, NOT PER RUN (order c8ac7dbab3c5). This fired only when the WHOLE selection came back empty, so a mistyped `--addr` alongside any selector that DID match was silently ignored: the run withdrew the ones it understood, said nothing about the one it did not, and the operator read a clean report as confirmation that everything named had gone. Worse, the `unknown` list was built from `a.source` alone, so even on the empty branch -- the branch whose whole job is naming the typo -- an `--addr` typo was never named. Both selectors are now checked against the catalog independently, and ANY selector that matches nothing refuses the run. Matching is exact by design (see `select`), so an unmatched selector is a spelling; on the tool whose next step is irreversible, a spelling is a stop.
- **hostcheck.py** `sweep` — [MEDIUM] searches for replacements for hosts that failed to hold their fiction but uses a flawed logic for selecting replacements
  - says: searches for replacements for hosts that failed to hold their fiction
- **health.py** `reopen_stranded` — [MEDIUM] return value is used to determine exit code, but the code does not handle the case where it returns None
  - says: THE VERDICT IS THE EXIT CODE (sweep42-batch10). This discarded `reopen_stranded()`'s return value and returned 0 unconditionally, so a repair that could not read or write PIPELINE_STATE.json reported success to whatever ran it -- the check-that-cannot-fail shape, on a repair.
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
