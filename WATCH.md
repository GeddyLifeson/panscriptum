# OVERWATCH

round 171  ·  last run 2026-08-29 18:48

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 275,602 inspected (deep scan as of round 169)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**5 open** (1 high). Newest first.

- **identity.py** `epoch_of` — [HIGH] Returns "" when the epoch probe is unprobed or when the response is not explicit, but the system prompt specifies that "If the sentence carries no marker at, return {"epoch": "", "
  - says: The epoch a single sentence places itself in, or "" when it names none.
- **liveness.py** `phantom` — [MEDIUM] a list of names used in conditions that are not defined in the module or builtins
  - says: a list of names used in conditions that are not defined
- **liveness.py** `taut` — [MEDIUM] a list of comparisons with identical sides that are not constants
  - says: a list of comparisons with identical sides
- **liveness.py** `dead` — [MEDIUM] a list of module-level definitions and methods that are not referenced by the current module's attributes
  - says: a list of module-level definitions and methods that are not referenced
- **liveness.py** `scoped` — [MEDIUM] a dictionary mapping keys to sets of attributes that are reachable via inheritance
  - says: a dictionary mapping keys to sets of attributes

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
