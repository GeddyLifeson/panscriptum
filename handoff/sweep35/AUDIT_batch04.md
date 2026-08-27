# SWEEP35 batch04 audit

Modules: src/standards.py, src/gpu_lane.py, src/tiers.py, src/sevenfold.py,
src/cosmography.py, src/recover_folder_records.py, src/catalogue_aurora.py (3,587 lines).

Read every module completely (standards.py in three offset reads, 1755 lines total). Checked
existing state/workorders.json first to avoid re-filing; several suspicions in tiers.py and
standards.py (stale silence.note tags, hyperverse print/assign contradiction, TIERS.json vs
address_space.py prose mismatch, cosmography dead constants) were already open orders from
sweep33/34 and were left alone.

## Findings filed (4)

1. **standards.py:1357-1379** -- `except FileNotFoundError:` on the `promotions have their
   spine codes amended` standard bypasses the shared `_dropped`/silence.note mechanism the file
   was edited today to add. When `data/SHELF_RANKS.json` is absent (true on this machine right
   now, verified live), the standard vanishes from `check()`'s output with no `_dropped` entry
   and is invisible even to the new "every standard could read its own input" aggregate that was
   added today specifically to catch this shape. RUN/MAJOR.

2. **catalogue_aurora.py:70-97** -- `parse_folder()`'s dedup key is `(type, normalized-name)`
   only, no description/file. Generic archetype-feature names ("Bonus Proficiencies", "Expanded
   Spell List") repeat across unrelated subclasses in different source XML files, and the
   dedup silently keeps only the first. Measured against the real Aurora XML folders: 442
   elements dropped as "duplicates" across the 10 mapped folders, 293 of which carry a
   genuinely different description (not duplicates at all). unearthed-arcana alone loses 134
   distinct elements. Nothing counts, logs, or prints any of this. RUN/MAJOR.

3. **standards.py:291-364** -- the fandom-reachability probe's new per-process memoisation
   (`_FANDOM_V4_CACHE`, added today) has no TTL, unlike the file's other two memoised probes
   (`_RUNNER` ttl=120s, `_TOKENFLOW` ttl=300s). The standard's two real production callers,
   `dashboard.py` (`serve_forever()`, polled every 5s) and `publish.py --loop`, are both
   long-running single processes, so the fandom probe now fires once per daemon lifetime and
   then reports the same verdict for however many hours the daemon runs -- defeating the
   standard's documented purpose ("notice an outage while it is happening") for exactly the
   deployments it was written for. RUN/MAJOR.

4. **sevenfold.py:213-221** -- `build()` silently drops an entire source's worlds with no
   count when that source isn't present in the weave resonance graph (`coords.get(src) is
   None: continue`). Currently inert (measured: 0 of the 3 sources missing from the weave graph
   have any worldseed-eligible Places entries), but unguarded and unreported -- a live risk
   for the rules-heavy D&D-Folder sources CLAUDE.md flags as likely to be graph-thin. RUN/MINOR.

## Areas checked and cleared (no finding)

- gpu_lane.py: fail-open design is explicit and documented end to end (Windows `_alive` fix,
  heartbeat/lease mechanics, `_remove_retry`). Its many "silent" exception handlers (per
  `silence.audit()`) are the module's declared policy ("FAIL OPEN, ALWAYS"), not an oversight;
  did not re-flag as a style complaint against a documented design. Confirmed `status()` does
  have a caller (`overnight.py:835`, keep-warm busy-check).
- tiers.py: cut/assert logic checked (`CUTS` ordering, `MULTIVERSE_THRESHOLD` assertions) --
  real, non-tautological guards against literal constants. Existing sweep34 order already
  covers the hyperverse "DECLINED" print vs. per-source assignment contradiction.
- cosmography.py: self-contained, no file I/O beyond a local `assay` import; `validate()`'s
  Kardashev ceiling checks are real, not tautological. Existing sweep34 order covers the dead
  constants.
- recover_folder_records.py: write-gating and "already populated" fail-safe logic already fixed
  per in-file history; no new gap found beyond the two open orders (stale slug comment,
  writes-outside-record-writer).
- catalogue_aurora.py FOLDER_SOURCE coverage: the two unmapped custom/ folders (`Panscriptum`,
  `Prime Omniverse Codex`) contain no XML at all (kit reference docs / the discarded old codex)
  -- confirmed not a silent gap.

Coverage recorded via `sweep_plan.record('run35', [...7 modules...], batch=4)`.
