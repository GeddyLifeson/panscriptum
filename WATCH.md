# OVERWATCH

round 407  ·  last run 2026-09-07 00:11

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 298,036 inspected (deep scan as of round 403)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**16 open** (5 high). Newest first.

- **axis_correlation.py** `rho` — [HIGH] returns 0.0 when doc is missing, which contradicts the claim that the default is the measured mean
  - says: THE DEFAULT IS THE MEASURED MEAN, NOT ZERO
- **autostart.py** `threading` — [HIGH] not defined in this slice
  - says: used for thread identification
- **autostart.py** `contextlib` — [HIGH] not defined in this slice
  - says: used for suppressing exceptions
- **autostart.py** `silence` — [HIGH] not defined in this slice
  - says: used for handling errors and logging
- **autostart.py** `installed_state` — [HIGH] not defined in this slice
  - says: returns the state of the launcher
- **binding_health.py** `F.page_looks_real` — [MEDIUM] judge page as real document
  - says: judge page as real article
- **binding_health.py** `F.fetch` — [MEDIUM] fetch host and list of titles
  - says: fetch host and title
- **axis_correlation.py** `measure` — [MEDIUM] used but never defined in this file or its imports
  - says: generate data for axis correlation
- **axis_correlation.py** `rho` — [MEDIUM] used but never defined in this file or its imports
  - says: compute correlation between two axes
- **autostart.py** `ON.running` — [MEDIUM] ON.running(job) is used to check if a job is running, but the comment indicates that `ON.ALL_JOBS` is the correct roster to use and that `ON.running` may not be the correct function to check job status. The comment also mentions that `ON.running()` returns None when it could not read the process table, and that the code should test `is None` explicitly rather than relying on truthiness.
  - says: THE SINGLE ROSTER, NOT A HAND-KEPT SUBSET OF IT. This used to be a six-item tuple typed out here, and it had already drifted from `ON.STANDING`: it named "feats.py" where the roster's own entry is "feats.py --roll" (a real fragment-with-argument, per `_cmd_is_running`'s own docstring, not a mention), and it had no entry at all for `pipeline`, which joined STANDING after this tuple was written -- so `--status` could print every job on ITS list green while pipeline.py was down. `ON.ALL_JOBS` is the roster its own comment in overnight.py says exists so nothing keeps a partial copy; `autostart.py`/`overnight.py` are skipped here because this report already named them above, as the launcher and supervisor lines.
- **assay.py** `scores` — [MEDIUM] the key is present even when no axes were scored
  - says: A ROW WITHOUT THIS KEY IS "NOT RECORDED", NEVER ZERO
- **assay.py** `moth_number` — [MEDIUM] the decimal is clamped to 0.0 or 0.99, but the dict does not always indicate which end it hit
  - says: printed decimal is inside [0, 1) or the dict says which end it hit and why
- **assay.py** `denom` — [MEDIUM] sum(W[k] for k in applicable) or 1.0 is used as a denominator, but the comment states it is a structural backstop and not a live path, yet it is still present in the code
  - says: sum(W[k] for k in applicable) or 1.0
- **assay.py** `_rho_doc` — [MEDIUM] The function does not actually guard against the matrix being missing; it only sets a fallback reason and does not prevent the use of the fallback value in subsequent computations.
  - says: ON THE FALLBACK, AND WHAT ACTUALLY GUARDS IT (corrected 2026-08-26, order c00cab9d0412). If the matrix is missing this degrades to rho = 0 -- the independence assumption -- which is the WRONG answer, deliberately chosen: it is the only value that reproduces the library's historical numbers exactly, so a missing file degrades to "as it was before" rather than to some third behaviour nobody has seen.
- **assay.py** `_rho_doc` — [MEDIUM] The function returns a dict, but it does not actually load the matrix; it only caches the result of a previous load and sets a fallback reason if the matrix is missing.
  - says: The measured matrix, loaded once per process. -> dict, EMPTY when it is unavailable.
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
