# sweep66 batch09 audit (maintenance run #66, 2026-09-27)

Read-only auditor for batch 9. Nothing under `src/`, `data/`, `state/`, `output/`, `prompts/`,
`reference/` or the repo root was edited, created or deleted except this file and the mandated
`sweep_plan.record()` call. No `drill.py`, `verify_math.py`, `generate.py`, `pipeline`,
`publish`, the crawl, `overwatch`, `foreman`, `mutate` or any job was run. No subagents were
spawned. The only execution was a direct, read-only call to `derivation.check_graph()` against
the live ledger (see Findings) — no file was touched by it.

## Scope (every line read via the Read tool, in chunks, start to finish)

- `src/foreman.py`         2319 lines (chunks 1-600, 601-1200, 1201-1800, 1801-2319)
- `src/codewatch.py`       1180 lines (chunks 1-600, 601-1180)
- `src/derivation.py`       816 lines (chunks 1-420, 421-816)
- `src/build_terminal.py`   668 lines (chunks 1-400, 401-668)
- `src/handbuilt.py`        518 lines (one chunk)
- `src/render.py`           441 lines (one chunk)
- `src/resync_roll.py`      332 lines (one chunk)
- `src/propagation.py`      254 lines (one chunk)
- `src/catalog.py`          167 lines (one chunk)

Total 6,695 lines across nine modules, all read completely, no sampling or grep-only skimming.

## Prior-audit cross-check

This exact nine-module roster has not been audited together as one batch before, but every
module in it was fully read within the last day by sweep65, split across three batches, and
none of the nine files' `mtime` is newer than that read:

- `handoff/sweep65/AUDIT_batch09.md` (run #65) — covers `foreman.py`, `codewatch.py`,
  `build_terminal.py`, `handbuilt.py`, `render.py`, `resync_roll.py` directly (plus `rosetta.py`,
  `ledger.py`, `chord_field.py`, outside this batch). Reported **0 new findings**, and recorded
  one status change now fully confirmed still standing: `foreman.py`'s `_retire_stall_order()`
  (lines 696-715) closes the `STALLED_UNRESTARTABLE` escalation order once no unrestartable job
  is stalled — re-read this pass, unchanged, still called from both sites in `kill_stalled_job`
  that need it (the early "every running job is advancing" holds again return, and the `else`
  branch when no unrestartable job is stalled this round).
- `handoff/sweep65/AUDIT_batch10.md` (run #65) — covers `derivation.py` directly. Reported 0
  findings against it; `check_graph()`'s four rules and cycle detector, `depth()`'s memo-free
  recursion, and `main()`'s early-return-on-failure (order 90516d53d696) all traced and confirmed
  unchanged this pass.
- `handoff/sweep65/AUDIT_batch13.md` (run #65) — covers `propagation.py` and `catalog.py`
  directly. Reported 0 findings against either; `propagation.observed_mark`'s two-clock model,
  `shortest()`'s Dijkstra, `catalog.py`'s `cmd_address`/`cmd_read`/`main()` return-code discipline
  all re-read and confirmed unchanged.

**File modification times** (`stat`, checked before reading) show every one of the nine files
last touched on or before 2026-09-26, i.e. no later than the day sweep65 read them, and the line
counts match sweep65's own recorded counts exactly for eight of the nine files. The ninth,
`handbuilt.py`, is recorded by sweep65 batch09 as 519 lines; this run's `wc -l` and the Read
tool both report 518. Read the file in full and found nothing resembling a one-line content
change — the file ends cleanly at `sys.exit(main())` with a single trailing newline, and every
sheet, comment and the `compute()`/`main()` bodies read identically to sweep65's own quoted
excerpts. Most likely a counting-convention difference (a trailing blank line present or absent
at the time each tool counted), not a code change; noted rather than treated as a defect, since
nothing in the content disagrees with the prior clean bill.

Given unchanged mtimes and matching content, this pass is confirmatory rather than a fresh
read of edited code — and it was still read in full, per the brief, rather than assumed clean
from the timestamps alone.

**`state/workorders.json`** was grepped for all nine `*.py` filenames before writing anything.
Hits naming this batch's modules, all pre-existing and already open, none re-filed:

- `1e6f99e54b25` (`CORPUS_WRITERS_WITHOUT_A_HALT_INTERLOCK`, MAJOR, OWNER) and `21c075e5e2d6`
  (`MORE_WRITERS_WITHOUT_A_HALT_INTERLOCK_SWEEP58`, MINOR, OWNER) name `resync_roll.py` (both) and
  `handbuilt.py` (the second) as writers of corpus/output state with no
  `escalation.assert_clear()` call before writing. Confirmed still true by this read: neither
  module imports or calls `escalation` anywhere (`grep -n escalation src/resync_roll.py
  src/handbuilt.py` — zero hits), and both write live state (`data/SWEEP_ROLL.json` via
  `roll.mutate`; `data/HANDBUILT_ASSAYS.json` via `silence.write_json`) unconditionally. Already
  an open OWNER question about a whole class of writer; not re-filed as a new finding.
- `5bb12b398783` (`SWEEP54_QUESTIONS_FOR_A_RULING`, MINOR, OWNER) names `render.py` among five
  design questions from sweep54. Not re-filed.
- `6b59a5d4302a` (`SWEEP63_QUESTIONS`, MINOR, OWNER) names `resync_roll.py`. Not re-filed.
- `d1709d8e757d` (`ENTITY_INDEX_NEVER_REBUILT_STALENESS_ANNOUNCED_BUT_UNACTED`, MAJOR, OWNER) and
  `d9328fe1ee38` (`STALL_STANDARD_WATCHES_THE_LOG_NOT_THE_WORK`, MAJOR, OWNER) name `foreman.py`.
  Confirmed still consistent with current source: `foreman.REMEDIES` has no entry for an
  "entity index" standard (falls to the OWNER lane by `round_once`'s own default, as designed),
  and `kill_stalled_job`'s `_io_moving` second-witness check (the fix `d9328fe1ee38` asked for)
  is present and unchanged. Not re-filed.
- `f7d7769075c0` (`CODEWATCH_RESTART_FILES_AN_ORDER_PER_DESIGNED_RESTART`, MINOR, OWNER) names
  `codewatch.py`/`foreman.py`. `exit_if_stale`'s JANITOR-rank `CODEWATCH_RESTART` escalation on
  every granted restart is present and unchanged (codewatch.py:1066-1074). Not re-filed.
- `ff77e242b830` (`OWNER_QUESTIONS_FROM_SWEEP48_BUNDLE`, MINOR, OWNER) names `foreman.py`. Not
  re-filed.

No other order in the queue names a function or line inside this batch's nine files as a live
code defect distinct from the above.

## Findings

**0 new CONFIRMED or SUSPECTED defects.**

Independently re-verified rather than taken on the prior audits' word:

- Ran `derivation.check_graph()` directly against the live `LEDGER` (112+ quantities): **0
  problems** — the graph still closes (no `UNKNOWN` kind, no `DANGLING` parent, no `ROOTLESS`
  derivation, no `UNSIGNED` owner declaration, no `CYCLE`). Confirms sweep65 batch10's own
  reproduction is still true today.
- Re-read `foreman.py`'s `_retire_stall_order`/`kill_stalled_job` pair line-by-line against the
  sweep64→sweep65 fix history recorded in their own docstrings/comments; the escalation-order
  math (`_WO.order_id("STALLED_UNRESTARTABLE", "")` matching the `where=""` `escalate()` call
  files under) and the two call sites are exactly as sweep65 described.
- Re-read `codewatch.py`'s `_ledger_lock`/`_take_locked`/`_claim_restart_slot` check-and-take and
  `stale()`'s two-clock (`seen` vs `quiet`, corroborated against `_START["at"]`) settle logic;
  both match their own documentation and sweep65's trace.
- Re-read `build_terminal.py`'s `esc()` discipline at all cited sinks (`panel()`,
  `selectSource()`, `selectWorld()`, `shelfmark()`, the four `f.*` rows), the `<` →
  `<` neutralisation before splicing JSON into the inline `<script>` block, and the
  atomic `replace_retry` write with the denial reaching `main()`'s exit code — all present,
  unchanged.
- Re-read `render.py`'s `children_of()` whole-coordinate guard (raises on a partial coord, per
  orders 3270e0172391/3b422bc17939) and `containment_svg`'s child-count-vs-geometry-divisor
  split (`n = max(1, len(children))` for layout only, `_kids = len(children)` for the caption) —
  both present, unchanged, and consistent with the live tree's `universe` node genuinely having
  no charted children.
- Re-read `resync_roll.py`'s status-relabelling rule (runs unconditionally per matched row, not
  only inside the `entry_count changed` branch — order 2ab24aeb63f7), the `_roll.OUT_OF_SCOPE`
  bare-`!=` guard in both the main loop and the CAS `_apply` closure (kept as a bare compare
  deliberately, for the drill net's AST-based check), and `sys.exit(main())` carrying the write
  verdict (order 8605c2ed6061) — all present, unchanged.
- Re-read `catalog.py`'s `cmd_address`/`cmd_read` miss-is-rc=1 discipline and `load_catalog`'s
  missing-vs-empty distinction (order 3f4d2d058fdc) — present, unchanged.
- Re-read `propagation.py`'s `observed_mark` two-clock model and the "trailing `return 0` is
  unreachable because rung 1's `ascension_years` is exactly 0.0" claim — hand-traced the loop
  again (`range(LADDER_HEIGHT, 0, -1)`, rung 1 last) and confirmed the claim holds.
- Re-read `handbuilt.py`'s write-before-print ordering (so a console `UnicodeEncodeError` on the
  Fraktur `moth_number` glyph cannot cost the `HANDBUILT_ASSAYS.json` write) and the `score_str`
  sentinel-vs-number branch for Zalama's `unestimable` axes — present, unchanged.

## Questions

None new. Carried forward, per the brief, without re-filing (all already OWNER questions on
record, all re-checked against live source this pass and all still standing exactly as
described):

1. **`resync_roll.py`'s closing "roll now: X/Y sources catalogued" line** (`main()`, around line
   319-321) sums over the local in-process `roll` list, already mutated in place with the same
   `repairs` handed to `_roll.mutate()`, rather than re-reading the post-CAS disk state
   `_roll.mutate()` actually wrote. They can only disagree if another writer changed the same
   rows on disk between this process's read and its `_roll.mutate()` call. First raised
   `handoff/sweep63/AUDIT_batch09.md` Question 1, restated unchanged in
   `handoff/sweep64/AUDIT_batch08.md` and `handoff/sweep65/AUDIT_batch09.md`. Not re-filed.
2. **`resync_roll.py` and `handbuilt.py` write live state with no halt check**, per open orders
   `1e6f99e54b25`/`21c075e5e2d6` above — re-verified this pass by grepping both files for
   `escalation` (zero hits in either). Not re-filed; the class-wide ruling is the owner's.

## Coverage

Recording via `sweep_plan.record('run66', ['foreman.py', 'codewatch.py', 'derivation.py',
'build_terminal.py', 'handbuilt.py', 'render.py', 'resync_roll.py', 'propagation.py',
'catalog.py'], batch=9)` — all nine modules read in full this session.
