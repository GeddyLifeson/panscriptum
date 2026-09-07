# OVERWATCH

round 408  ·  last run 2026-09-07 00:54

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 298,036 inspected (deep scan as of round 403)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**19 open** (8 high). Newest first.

- **catalogue_codex.py** `roll_landed` — [HIGH] the write to SWEEP_ROLL.json was denied
  - says: the write to SWEEP_ROLL.json landed
- **catalogue_codex.py** `parse_codex` — [HIGH] -> {title: {blurb: ..., contents: [...]}}
  - says: -> {norm(name): [item, ...]} -- EVERY item under a key, never just the first to arrive.
- **canon_backup.py** `prune` — [HIGH] Deletes all but the newest `keep` snapshots, but the code does not actually delete the snapshots; it only marks them as denied and prints a message.
  - says: Delete all but the newest `keep` snapshots, and reap abandoned scratch files.
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
- **catalogue_models.py** `sweep` — [MEDIUM] reports truncated stale model references
  - says: reports stale model references
- **catalog.py** `cmd_read` — [MEDIUM] returns 0 on hit, 1 on miss
  - says: -> rc. A MISS IS rc=1 (order 3f4d2d058fdc). See main().
- **catalog.py** `cmd_address` — [MEDIUM] returns 0 on hit, 1 on miss
  - says: -> rc. A MISS IS rc=1 (order 3f4d2d058fdc). See main().
- **canon_backup.py** `final` — [MEDIUM] the final name includes the stamp which is unique per snapshot
  - says: THE NAMING CONVENTION STILL SORTS
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
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
