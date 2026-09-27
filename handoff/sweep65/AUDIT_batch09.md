# sweep65 batch09 audit

Auditor for batch 9 of maintenance run #65 (2026-09-26). Read-only throughout: nothing under
`src/`, `data/`, `state/`, `output/`, `prompts/`, `reference/` or the repo root was edited,
created or deleted except this file and the mandated `sweep_plan.record()` call. No drill,
verify_math, generate, pipeline, publish, the crawl, overwatch, foreman, mutate or any job was
run. No subagents were spawned.

## Scope (every line read via the Read tool, in chunks, start to finish)

- `src/foreman.py`         2319 lines (chunks 1-600, 601-1200, 1201-1719, 1801-2319)
- `src/codewatch.py`       1180 lines (chunks 1-600, 601-1180)
- `src/rosetta.py`          815 lines (chunks 1-420, 421-815)
- `src/build_terminal.py`   668 lines (chunks 1-340, 341-667)
- `src/handbuilt.py`        519 lines (one chunk)
- `src/render.py`           441 lines (one chunk)
- `src/resync_roll.py`      332 lines (one chunk)
- `src/ledger.py`           220 lines (one chunk)
- `src/chord_field.py`      210 lines (one chunk)

Total 6,704 lines, all nine modules read completely, no sampling or grep-only skimming.

## Method

Read `CLAUDE.md` first (Hard Rule -1 escalation/halt chain, Hard Rule 0 no-caps, fail-closed
doctrine). Then read every sweep64/sweep63 audit that names one of these nine files before
reading source, since this exact nine-file roster is split across two prior batches:

- `handoff/sweep64/AUDIT_batch09.md` — the direct predecessor batch: covers `foreman.py`,
  `codewatch.py`, `ledger.py`, `chord_field.py` (plus four modules not in this batch). It filed
  one VERIFIED finding on `foreman.kill_stalled_job`'s `STALLED_UNRESTARTABLE` escalation never
  being retired, and one on `manifest_builder.provisional_spine` (out of this batch's roster).
- `handoff/sweep64/AUDIT_batch08.md` — covers `rosetta.py`, `resync_roll.py` (0 new findings on
  either; cleared `numeric_rows`/`stand_rows`/`ordinal_rows`/`assays_by_host`/`check`, and the
  resync_roll status-relabelling/owner-exclusion fix).
- `handoff/sweep64/AUDIT_batch10.md` — covers `build_terminal.py` (cleared: every innerHTML sink
  escaped, atomic write).
- `handoff/sweep64/AUDIT_batch16.md` — covers `handbuilt.py`, `render.py` (cleared both).

Also grepped `state/workorders.json` for every module name and function mentioned above before
writing anything down; the hits are all open QUESTION-type orders already on record (e.g.
`1e6f99e54b25`/`21c075e5e2d6` on manually-invoked writers bypassing the halt, `7099a092abd3` on
dead functions with test-only callers, `d9328fe1ee38`/`ff77e242b830`/`f7d7769075c0` on foreman/
codewatch topics already ruled on) — none of them is the `STALLED_UNRESTARTABLE` finding itself,
which is not a work order but a sweep-report finding.

## Findings

**0 new CONFIRMED or SUSPECTED findings this batch.** One important status change:

### CLOSED (not a new finding) — `foreman.py`'s `STALLED_UNRESTARTABLE` escalation now retires itself

sweep64/AUDIT_batch09.md filed this as VERIFIED: `kill_stalled_job()` escalated SUPERVISOR/
`STALLED_UNRESTARTABLE` through `escalation.escalate()` with no `source=`, so the order filed
under `where=""` and nothing anywhere called `resolve_code`/`resolve` for that code — the order
would stand open forever, still naming a pid that no longer existed.

This is fixed in the current source. `foreman.py:696-715` now defines `_retire_stall_order(why)`,
which computes `_WO.order_id("STALLED_UNRESTARTABLE", "")` (the same `where=""` the escalate call
files under — verified against `workorders.order_id`'s definition, `hashlib.sha1("%s|%s" %
(code, where))`, so the ids match byte-for-byte), checks the order is still open via `_WO._load()`,
and calls `_WO.resolve(oid, why, by="foreman.kill_stalled_job")` — traced `workorders.resolve()`
(`workorders.py:702-` on) and confirmed it returns the closed record (truthy, not `None`) only when
the compare-and-swap actually landed, which is what `_retire_stall_order`'s `is not None` check
requires.

It is called from both places that need it: `kill_stalled_job()`'s early return when the
"every running job is advancing" standard already holds (`foreman.py:744-746`), and the `else`
branch taken when this round finds no unrestartable job stalled (`foreman.py:851-853`). The
docstring at `_retire_stall_order` (lines 696-705) cites this exact history ("sweep64 batch09,
run #64... Measured on 2026-09-26: it still named `roll_auto:47680`..."), so this is a landed,
documented repair of the prior finding rather than a coincidental rewrite. Verified by reading
`workorders.py`'s `order_id`/`file_order`/`resolve` definitions directly, not by trusting the
comment.

## Questions

Nothing new. One item carried forward without re-filing, per the brief (already a QUESTION in
sweep63/sweep64, not a work order, not a defect):

1. **`resync_roll.py`'s closing "roll now: X/Y sources catalogued" line** (`main()`, line
   319-321) sums over the local in-process `roll` list — which this run has already mutated in
   place with the same repairs handed to `_roll.mutate()` — rather than re-reading the post-CAS
   disk state `_roll.mutate()` actually wrote. In the ordinary case the two agree, because the
   local mutations and the CAS `_apply` closure apply the same `repairs` dict under the same
   exclusion guard. They can only disagree if another writer changed the same rows on disk
   between this process's read and its `_roll.mutate()` call — a race already flagged as
   Question 1 in `handoff/sweep63/AUDIT_batch09.md` and restated, unchanged, in
   `handoff/sweep64/AUDIT_batch08.md`. Not re-filed as a new finding.

## Cleared (examined closely this pass, found correct)

- **`foreman.py`**: `_python_processes()`'s psutil-only listing (no wmic anywhere live, fails
  closed with `ProcessTableUnreadable` on an empty or unreadable table); `_restartable`/
  `_restart_horizon`'s shared `_standing_cmds()` derivation; `kill_stalled_job`'s two-witness
  design (`_io_moving` I/O sampling spares a restartable OR unrestartable job whose log is quiet
  but which is still doing I/O); `kill_duplicate_jobs`'s oldest-survives logic and `NEVER_DEDUPED`
  exclusion of the supervision chain; `_catalogue_batch`'s rotation (stamped-before-work, uncapped
  universe, ranked-not-truncated); `attempt_patch`'s patch-safety gates (`regex_touched`,
  `lines_changed`, `_contracts_pass`, `_checks_pass`'s `RESULT:` regex, not a substring test);
  `round_once`'s `.always`-remedy handling past a `did=True` break; `restart_ollama`'s fail-closed
  stamp read and tray-vs-daemon distinction; `main()`'s per-round halt re-check and rc=17
  `codewatch.exit_if_stale` call at the loop's tail.
- **`codewatch.py`**: `runs_script`/`twins`/`claim_singleton`'s documented FAIL OPEN behaviour on
  an unreadable process table (three separate docstrings say so, not a hidden defect);
  `_ledger_lock`/`_take_locked`/`_claim_restart_slot`'s check-and-take-under-one-lock fix for the
  budget race; `stale()`'s dual-clock settle window (`seen` vs. `quiet`, corroborated against the
  startup stamp so a backdated mtime cannot borrow evidence from an older edit); `_report_if_never_settling`'s unconditional MANAGER rank; `last_polled`/`_poll_pid_alive`'s
  three-valued liveness check (a dead or recycled pid never reads as a fresh poll).
- **`rosetta.py`**: `numeric_rows`'s row-vs-window split (verified by direct execution against a
  synthetic multi-column wikitable row: `[[Straw Hat Pirates]] || 3,000,000,000 || [[Roronoa
  Zoro]] || 1,111,000,000` correctly pairs `Roronoa Zoro` with `1,111,000,000` and filters the
  crew name via `_NOT_A_NAME`; a row whose link/number counts disagree is dropped rather than
  mis-paired); `ordinal_rows`'s case-preserving offset fix; `stand_rows`'s label-anchored parameter
  block reading; `assays_by_host`/`check`'s per-host scoping and the `partition("|")` fix;
  `refine`'s per-host, Persons-only matching and the numeric-scale order-of-magnitude floor;
  `main --mine`'s `MINE_FLOOR` refusal-to-shrink guard.
- **`build_terminal.py`**: every catalogue-derived string reaching `innerHTML` (`panel()`,
  `selectSource()`, `selectWorld()`, `shelfmark()`, the four `f.*` rows) goes through `esc()`;
  the `<` → `<` neutralisation before splicing JSON into the inline `<script>` block; the
  atomic `replace_retry` write with denial reaching the exit code; `--help` no longer rebuilds
  the page.
- **`handbuilt.py`**: `compute()`'s per-sheet assay construction; `main()`'s write-before-print
  ordering (so a console UnicodeEncodeError on the Fraktur `moth_number` glyph cannot cost the
  JSON write); the `score_str` sentinel-vs-number branch for Zalama's `unestimable` axes.
- **`render.py`**: `children_of()`'s whole-coordinate-required guard (raises rather than pooling
  every value of an unspecified prefix dimension); `containment_svg`'s child-count-vs-layout-
  divisor separation (`n = max(1, len(children))` for geometry only, `_kids = len(children)` for
  the caption); `write_views()`'s atomic per-file temp+`replace_retry` write with a pid/thread-
  qualified name and a read verdict.
- **`resync_roll.py`**: the status-relabelling rule running unconditionally per matched row
  (not only inside the `entry_count changed` branch), the `_roll.OUT_OF_SCOPE` bare-`!=` guard in
  both the resync loop and the CAS `_apply` closure, and the exit code carrying the write verdict
  (`sys.exit(main())`, not a bare `main()`).
- **`ledger.py`**: `to_standards`/`from_standards`/`cross_rate`/`work_value` round-trip
  arithmetic; `assay_to_standards`'s M10 top-band extrapolation (`hi = lo * (lo/prev)`, confirmed
  `hi > lo` since `prev < lo`, so `ruin_score` still moves the answer at the top band rather than
  collapsing to a zero-width range as the fixed bug describes). No live caller outside
  `verify_math.py`'s battery, per its own "HELD FOR A FUTURE PHASE" doctrine (order `3fb9fc6b9999`).
- **`chord_field.py`**: `landauer_floor`, `recoil_momentum`, `recoil_velocity`,
  `critical_power_self_focus` — all standard-physics formulas, checked by hand against their
  cited results; no dead-constant drift (`C_LIGHT`/`K_BOLTZMANN` are the only two module-level
  constants and both have a live caller in this same file).

## Coverage

Recorded via `sweep_plan.record("run65", [...], batch=9)` for all nine modules above, each read
in full this session.
