# AUDIT — run46, batch 10

Modules read end to end: `src/foreman.py`, `src/overwatch.py`, `src/wiki_source.py`,
`src/liveness.py`, `src/cleanup.py`, `src/snapshot.py`, `src/physics.py`, `src/profile.py`.
(~5,583 lines per the batch spec; actual `wc -l` sum for these eight files is 6,586 — foreman.py
alone is 1,810 lines, larger than the batch note implied. Read whole regardless.)

## Summary

This batch is unusually well self-audited already — most of the eight modules carry extensive
inline records of prior findings and fixes (order IDs, measured before/after counts against the
live corpus). The three areas flagged in the task brief were checked against the CURRENT source
and hold:

1. **wiki_source.py raise-on-transport-failure.** `category_members`, `all_categories` and
   `extracts` all raise (no `break`-with-partial-list survives). Traced every caller:
   - `category_members` is called from `catalogue_composite` (catalogue_web.py:250, wrapped in
     its own `try/except`, failure recorded in `failed_cats` and the source keeps going) and from
     `catalogue()`'s single-wiki path (catalogue_web.py:420, deliberately unwrapped — the
     exception is meant to fail that whole attempt). `catalogue()` itself is called from exactly
     one place, `main()`'s `_one()` closure (catalogue_web.py:637-644), which wraps it in
     `try/except Exception` and records `record, note = None, "error: ..."` — an honest skip, not
     a partial roster recorded as complete. Confirmed via `grep`, not just docstring-reading.
   - `all_categories` is reached only through `find_categories` → `discover_categories`, called
     from `catalogue()`'s planning loop (catalogue_web.py:397), same unwrapped-on-purpose /
     caught-by-`_one` chain as above.
   - `extracts` has **no caller anywhere in src/** today (confirmed by grep), matching its own
     docstring's claim.
   No caller was found that would let a raised transport failure land as a silently-partial
   roster. This part of the brief is clean.

2. **cleanup.py `clean_description` idempotency.** Read every rule in `_MARKUP` (9 patterns) by
   hand for self-idempotency and for cross-rule interaction within one call. Then verified
   empirically, read-only, against the **entire live corpus**: `clean_description(clean_description(d))
   == clean_description(d)` for all **282,749** non-empty descriptions across all 216
   `data/records/*.json` files — **0 non-idempotent cases**. `pipeline._is_cleaned_twin`'s
   contract (`clean_description(sv) == dv`) is sound on the code as it stands today.

3. **foreman.py `owner_queue()` returning `(path, landed)`.** Confirmed: `round_once()` (the only
   caller) unpacks `p, _landed = owner_queue(owner_items)` and prints an honest "could NOT be
   landed" sentence when `_landed` is False, rather than claiming the file was freshly written.
   The only other reference to `owner_queue` in the tree is a `drill.py` net exercising exactly
   this behaviour. Clean.

4. **liveness.py, read as a detector that can itself have blind spots.** Ran it (read-only, per
   the batch instructions) — 35 dead, 1 dead_class, 9 dead_module, 0 tautology, 0 phantom, 0
   unparsed on the current tree. Manually traced the DEAD/DEAD_CLASS/PHANTOM/TAUTOLOGY logic for
   scoping correctness (bare-name-per-module, attribute-global, self/cls-scoped-by-MRO) — sound
   for the cases exercised. Two structural soft spots noted but **not** filed as separate work
   orders (low confidence / no demonstrated live instance):
   - `EXEMPT_PREFIXES` (`t_`, `test_`, `cmd_`, `phase_`, `check_`, `drill_`) exempts DEAD-pass
     coverage for 72 functions tree-wide with one blanket reason for the whole tuple, unlike
     `EXEMPT`'s per-name reasons — checked a sample (`catalog.py`'s `cmd_*`) and found them
     already reachable via ordinary same-module bare-name calls anyway, so the prefix exemption
     was not actually load-bearing there. Did not have time to check all 72.
   - TAUTOLOGY only inspects `ast.Compare` nodes with exactly one comparator, so a chained
     comparison (`a < b < a`) is structurally invisible to it. No live instance found.

## Genuine finding filed

**Work order `5b79deaaace9`** (code `OVERWATCH_RECONCILE_FILTER_DROPS_FAILURES`, handler RUN,
severity MAJOR) — **not one of the three flagged areas; found independently while reading
overwatch.py.**

`overwatch.structure()` (overwatch.py:404-407) filters `allsweep.reconcile()`'s findings before
they reach WATCH.md:

```python
out["reconcile"] = [r for r in A.reconcile()
                    if r["finding"].isupper() or "no host" in r["finding"]
                    or "never catalogued" in r["finding"]
                    or "MORE THAN ONE" in r["finding"]]
```

Checked every `note(kind, ...)` call in `allsweep.reconcile()` (allsweep.py:427-650) against this
filter. It silently drops, among others:

- **all seven `"<x> reconciliation failed"` / `"process check failed"` rows** — the exception
  handler at the bottom of each of the seven reconcile sub-blocks (source, coverage, cache,
  purge, phase, band, process). A reconcile check that could not even RUN leaves no trace in
  WATCH.md. This is the exact "a check that crashed is not a check that passed" failure
  `write_report()` already guards against for the import/estate scans two tiers up in the very
  same file — left unguarded one tier down, in the same function.
- `"hosts for sources with no catalogue record"` (orphan hosts) — dropped, while its mirror
  `"catalogued sources with no host"` (opposite direction of the same set comparison) passes the
  filter. No stated reason for the asymmetry.
- `"COVERAGE.json is stale"` — fails `.isupper()` only because `.json` is lowercase.
- `"cache directories no source points to"` and `"purged sources that still carry entries"`
  (ghosts) — both dropped.

Live-verified against the actual `WATCH.md` on disk (round 406, 2026-09-06): the Structure
section shows only the three finding kinds the filter happens to let through (no-host,
never-catalogued, NOT RUNNING) — none of the excluded kinds appear, and there is no way from
WATCH.md alone to tell "these checks found nothing" from "these checks' rows don't match a
regex". WATCH.md is, by this file's own repeated language, "the ONLY thing a person reads to
learn what this job found." Filed as a QUESTION with both readings (intended narrow scope vs.
collateral damage from an unexplained filter) since the line carries no comment — unusual for
this otherwise heavily-annotated file.

## Other things checked and found sound (no order filed)

- **foreman.py**: `_catalogue_batch`'s rate/rotation logic is a genuine RATE (nothing is
  discarded, deferred sources are named and re-prioritised by wait time), not a Hard-Rule-0 cap.
  `_checks_pass`, `attempt_patch`'s MAX_PATCH_LINES/`lines_changed`/`regex_touched` gates,
  `kill_stalled_job`'s restartability check, and the AUTO/MODEL/OWNER routing in `round_once` all
  read correctly against their docstrings on the executable line.
- **snapshot.py**: `_rel`/`_safe_join` containment checks, `before()`'s partial/empty refusal,
  `verify()`'s directory-aware byte compare (`_dir_matches`), and `restore()`'s missing-path
  refusal are all sound. One theoretical gap noted (`verify()`'s per-path loop silently skips the
  comparison if the snapshot's own copy `a` is neither file nor directory) but it is not
  reachable in the current call sequence — `restore()` (called immediately before the loop, same
  thread, no gap) already raises `SnapshotFailed` if `a` doesn't exist, so the loop always sees an
  `a` that does exist. Not filed.
- **physics.py**: every function's positive/finite/NaN/overflow guards were re-derived by hand
  against `kinetic`, `joules_for`, `sphere_volume`, `binding_energy` — all four correctly refuse
  non-positive, non-finite, and non-finite-result cases; the NaN-via-`not x > 0.0` coincidence is
  intentional and documented, and speed's `v >= 0.0` NaN case is the one deliberately-inverted
  test, also documented and correct.
- **profile.py**: `encode`/`decode` round-trip logic re-derived by hand (B32 alphabet, band
  index↔BANDS mapping, feature axis index↔table mapping, regex group widths) — internally
  consistent. The `main()` round-trip check genuinely exercises `encode(decode(x))`, not a
  tautology (confirmed the fix from order b9ff8dbf2c77/the `d["profile"]` note is present in the
  current code).

## Coverage recorded

Ran (read-only):
```
python -c "import sys;sys.path.insert(0,'src');import sweep_plan;sweep_plan.record('run46',['foreman.py','overwatch.py','wiki_source.py','liveness.py','cleanup.py','snapshot.py','physics.py','profile.py'],batch=10)"
```
