# OVERWATCH

round 447  ·  last run 2026-09-08 21:16

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 301,105 inspected (deep scan as of round 445)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**7 open** (2 high). Newest first.

- **feats.py** `roll` — [HIGH] the counters are ignored and 0 is returned unconditionally
  - says: THE COUNTERS REACH THE EXIT CODE
- **feats.py** `alive` — [HIGH] Returns the first element of the result of `alive_verdict` being True
  - says: Unchanged contract: True only when the wiki answered. See `alive_verdict` for the third answer, which every caller that CACHES a negative must ask for instead of this.
- **feats_index.py** `index_faults` — [MEDIUM] Builds the index if it has not been built, but the function returns a cached value that may be stale if the index is rebuilt without clearing the cache.
  - says: Builds the index if it has not been built, so the answer is never a stale zero.
- **feats_index.py** `_norm` — [MEDIUM] folds to alphanumeric-only
  - says: THIS DOES NOT STRIP A PARENTHETICAL
- **events.py** `_fragments` — [MEDIUM] The function splits on the joiners but does not check if the split parts are valid participants.
  - says: The separately-named participants inside one bold span, if it names more than one. -> [str].
- **escalation.py** `landed` — [MEDIUM] the file and the log agree
  - says: the file and the log disagree
- **escalation.py** `resume_subsystem_verdict` — [MEDIUM] Returns a bool and reason, but the actual behavior is to return a bool and a reason that indicates whether the resume was successful or not, which is consistent with the claim.
  - says: Re-open one subsystem. -> (bool, reason). The three-valued sibling of `resume_subsystem`.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
