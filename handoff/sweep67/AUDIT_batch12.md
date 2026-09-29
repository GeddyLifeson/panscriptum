# AUDIT batch 12 -- sweep67 (run67)

## Scope

Read in full, sequentially in chunks, no skimming:

| module | lines |
|---|---|
| src/magnitude.py | 1989 |
| src/silence.py | 1313 |
| src/allsweep.py | 1076 |
| src/secondopinion.py | 712 |
| src/tiers.py | 555 |
| src/coverage.py | 456 |
| src/snapshot.py | 376 |
| src/resonance.py | 298 |

Read-only for the project. Scratch scripts only under %TEMP%\b12 (t1..t4, scan). Nothing under
src/, data/, state/, output/ was written. Repros import modules and call pure functions;
no daemon, phase or mutating CLI was run.

## Prior-audit cross-check (handoff/sweep66)

Every earlier report on these modules (sweep66 batches 05, 11, 12, 13, 14, 15; sweep65 batch04
via 14) reported 0 findings and no new questions. Re-checked against current source:

- 66/12 magnitude guards 1-5 (`_resolve_citation`, `AXIS_RE`, `subject_refusal`, `saturated`,
  `quantity_scores`): still stand as described. The `_is_score` bool exclusion, guard 3 on the
  verify/_split_gate/instrument paths, and saturation-after-instrument ordering are all as
  claimed. What those reports did not examine is what guard 5 *feeds on* (F3, F4 below) and
  numeric non-finite scores (F7).
- 66/13 silence/allsweep: `_handler_is_observed`, CAS/replace discipline, `run_verifier`'s
  `failed` grading, `reconcile` uncapped names, `estate_faults` fail-closed: still stand. The
  DANGLING escalation ruling (a724ec57e0d5) is now partly implemented (`dangling_count`); still
  a question owned elsewhere. The IMPORT tier's `--help` premise was never tested for modules
  without argparse (F1).
- 66/14 secondopinion, coverage: `ran_clean` non-vacuity, `state_of` precedence: still stand.
  The `mine_says()["silence"]` figure was never checked against what `silence.audit` returns (F9).
- 66/15 resonance: no production caller for `hodge_decompose`/`resonance_strength`: still true
  (grep, only custodes/anchors comments and drill/verify_math). Gauss-Seidel fix verified
  again. New: absolute tolerance (F14).
- 66/11 tiers: CUTS invariants and containment gate stand. New: stale citations (F16).
- 66/05 snapshot: `_rel` containment and `_safe_join` stand. New: label handling (F15).

## Findings

### F1 -- MEDIUM-HIGH: allsweep's IMPORT tier EXECUTES `main()` of every argparse-less module (writes live data files)
`allsweep.py:349` runs `python src/<mod>.py --help` for every module and the docstrings rely on
it ("without doing any work", `:343-347`; `NEVER_RUN` comment `:96-99` says the safety "is
structural: check_import only ever passes --help"). That holds only for modules that parse
argv. Static scan of src/ (`__main__` present, no argparse/sys.argv/optparse/--help anywhere):
`address.py address_space.py anchors.py custodes.py derivation.py feats_index.py onomast.py
profile.py rigor.py roll.py tiers.py` -- 11 modules whose `__main__` is `sys.exit(main())`
with no argv handling, so `--help` runs the real `main()`.
Evidence it really happens (today's sweep): ALLSWEEP.json `at` 22:10:20, `seconds` 220.9, so
started 22:06:39. In that window: `data/SHELFMARKS.json` 22:06:41 (address_space `main()` calls
`silence.write_json`, `address_space.py:630`), `data/ONOMASTICON.json` 22:06:49
(`onomast.main` -> `land_onomasticon`), `data/TIERS.json` 22:07:11 (`tiers.main` ->
`tiers.py:541`). The recorded import rows are `ok: True`, seconds 1.9 / 2.0 / 18.6 -- the graph
build in tiers is exactly the work `--help` is meant to skip.
Consequences: (a) the module docstring's "READ-ONLY AGAINST THE LIBRARY ... safe to run at any
time, including against live jobs" (`:49-54`) is false: TIERS/SHELFMARKS/ONOMASTICON are
rewritten every sweep, racing pipeline phase_cosmology and address_space's import-time read of
TIERS.json; (b) foreman's patch gate runs `allsweep.py --quick` (foreman.py comments), so every
candidate-patch check rewrites them; (c) none of those three mains calls `assert_clear` (grep),
so it also happens under a halt (the sweep only greps the refusal text on non-zero exit);
(d) a legitimate refusal (tiers rc=2 "REFUSING TO CHART", bootstrap state) is graded a BROKEN
import by the "exited without a traceback, saying:" branch (`:383-388`).
Fix: make check_import not depend on the module's CLI: run `python -c "import <mod>"` (with
src on sys.path) for the load/regex/guard check, and keep `--help` only for modules that
declare argparse; or give the 11 modules a `-h/--help` guard before `main()`. Add a drill net:
every module whose `__main__` runs `main()` must answer `--help` without side effects.

### F2 -- LOW-MEDIUM: check_import has no TimeoutExpired/OSError handler; one slow module aborts the whole sweep
`allsweep.py:349-351` (`timeout=120`, no try) is called via `list(ex.map(check_import, mods))`
(`:812`). A TimeoutExpired propagates out of `main()` before ALLSWEEP.json is written, whereas
`run_verifier` handles the same exception (`:463`). Together with F1 (tiers `--help` runs the
whole graph build: 18.6 s on an idle box; its own comment says "takes minutes" under load) the
trigger is real. Same shape at `:909`: `E.artifacts(...)` is not inside the try that wraps the
four report-row tiers (`:935-944`), so an exception there also kills the run with no report.
Fix: catch per-module and return `{"ok": False, "detail": "timed out after 120s"}`; wrap
`E.artifacts` like the sibling tiers.

### F3 -- MEDIUM: quantity-only entity gets an anchor from model memory with an empty evidence prompt
`magnitude.py:1231` lets an entity through when `ev["quantities"]` is non-empty even with zero
candidates; `compose()` then builds a prompt with no evidence (repro `t4.py`: the prompt is the
header plus "Cite only from an axis's own list. An axis with no list takes a status.") and
`CB.ask/P.ask` returns an anchor from the model's recollection, contrary to SYSTEM ("from
nothing else"). That unevidenced anchor is then (a) published as the record's anchor and (b)
the band `quantity_scores` passes to `A.axis_score` (`:1434`), so even the "instrument" number is
computed against an anchor nothing supports. The quantities are never shown to the model.
Fix: for a quantity-only entity either anchor from `A.band_for_quantity` of the reading, or
return the "no axis cleared its gate" finding; do not ask the model to anchor over nothing.

### F4 -- MEDIUM: guard 5 accepts any "N unit" sentence as an instrument reading and overwrites verified scores unconditionally
`feats.mine` records a quantity from ANY 20-400 char sentence on the page (not only feats).
`quantity_scores` (`magnitude.py:493-525`) applies only guard 3 (doer), no relevance test, and
maps "ton(s)/tonne(s)" to TNT joules and any metres/miles figure to Reach. Then `assay_entity`
`:1436-1437` assigns `scores[ax] = q["score"]` for every axis with a reading, replacing a
verified, cited model score whether higher or lower. Repro (`t1.py`, entity Goku):
"Goku stands 2 meters tall." -> reach reading 0.0 (2 meters); "Goku weighs 90 tons in his heavy
training suit." -> ruin reading 0.0 (90 tons), at anchors M3 and M7. Both would replace a real
Ruin/Reach score and be published as `INSTRUMENT` (highest attestation). The `_TO_JOULES`
comment claims only "units with an unambiguous physical meaning"; "ton" (mass vs TNT) and a
height in metres are not. (Possibly deliberate "instrument outranks opinion" -- but a reading
that is not about the axis is not an instrument reading; treated as a finding, not a question,
because guard 2 exists for exactly this and is skipped on this path.)
Fix: require TNT/explosive context for ton units (or drop bare ton/tonne), require the sentence to
pass `AXIS_RE[axis]` plus an act verb, and only let an instrument reading REPLACE a model score
when it is the higher, or record both.

### F5 -- LOW-MEDIUM: calibrate() keeps DEFERRED / SCOPE_UNMEASURED rows as "done" and can stamp a complete pass over them
`magnitude.py:1551-1553` carries forward every prior row with an entity, including
`status: DEFERRED` (transport failure, "retried next run") and `SCOPE_UNMEASURED`; `:1601-1608`
never re-runs a benchmark in `prior`; `:1674` `_land(rows, len(rows) == len(BENCHMARKS))` stamps
`at` when every benchmark merely HAS a row. `standards.charter_regression_verdict`
(`standards.py:748`) then returns `holds = bool(scored) and not bad and fresh`: one consistent
scored row plus five unscored rows holds ("1/1 consistent, 5 unscored"). The docstring
(`:1528-1532`) says the design forbids exactly this ("green by absence", one row early). The
comment at `:1686-1688` acknowledges "not that every benchmark scored" but treats it as fact,
not as a hole.
Fix: only carry forward SCORED and NO_SCORE rows; treat DEFERRED/SCOPE_UNMEASURED as pending;
mark `complete` only when no row is DEFERRED/SCOPE_UNMEASURED (or make the verdict require it).

### F6 -- LOW: host_ceiling caches "no ceiling" after a generic live-probe exception
`magnitude.py:1798-1800`: `except Exception: note("host_ceiling-live")` falls through to
`_SCOPE_CACHE[host] = cl` with `cl = None`, which is what the long comment above it
(`:1777-1795`) says must never happen for ProbeUnread ("cached... skipped the clamp too").
Any non-ProbeUnread exception from `scope_for` (a KeyError on a malformed search row, a
TypeError) is cached as a permanent None for the process. Fix: do not cache on the exception
arm (return None uncached, or re-raise as the ProbeUnread arm does).

### F7 -- LOW: NaN / Infinity model scores become 0.0 / 9.9 on a cited axis
`_is_score` (`magnitude.py:814`) admits non-finite floats (Python `json` accepts `NaN`,
`Infinity`). `verify` `:901` `round(min(9.9, max(0.0, float(raw))), 2)`; repro: NaN with a valid
citation gives score 0.0 (`max(0.0, nan)` is 0.0), no rejection recorded. `_split_gate :1212`
same; `_one_axis :1050` compares NaN. A plausible negative numeric score from an unusable answer.
Fix: `math.isfinite` in `_is_score`.

### F8 -- LOW: `--limit` ranks then truncates with no banner; "already assayed" is `len(done)`
`magnitude.py:1745` `out[:limit]` (queue is richest-first) then `:1866` prints
"queue: %d entities, %d already assayed" where the first figure is the truncated length and the
second is every record in ASSAYS.json including DEFERRED ones (`settled()` false). Nothing says
the queue was cut or that "already assayed" includes unsettled records. `read.py` prints an
honest PARTIAL banner for the same flag. Fix: print total queue vs limit; count `settled()`.

### F9 -- MEDIUM-LOW: secondopinion's "house detectors: silence=N" counts every catch site, not the silent ones
`secondopinion.py:472` `sum(len(silence.audit(r) or []) ...)`; `silence.audit` returns a row for
EVERY handler with a `silent` flag. Measured now: 1308 rows, 312 silent (`t2.py`). The page
prints `silence=1308` beside ruff's BLE001/S110 counts under "vs", so the house detector's
finding count is overstated ~4x and the comparison this module exists to make is wrong. (The
comment at `:570-577` quotes 737/774 for silence on 2026-08-29 when silence.py itself measured
180 silent that day -- consistent with total, not silent.) Fix: count `r["silent"]`.

### F10 -- LOW: outside-tool subprocesses decode with the locale codec
`secondopinion.py:290,322,383` use `text=True` with no `encoding`, so on this machine
(cp1252) any non-ASCII byte undefined in cp1252 (e.g. UTF-8 for U+00CD, 0x8D) raises
UnicodeDecodeError inside `subprocess.run`; `run()` converts that to `ERRORED: UnicodeDecodeError`
and the tool reports as absent. allsweep's own spawns pass `encoding="utf-8", errors="replace"`.
Latent (ruff messages are mostly ASCII today). Fix: same kwargs here.

### F11 -- LOW: coverage.measure() silently drops any record `pipeline.records()` cannot open
`coverage.py:317` iterates `P.records()`, whose `except Exception: note(); continue`
(`pipeline.py:761-764`) skips a record that is unreadable at that instant (Windows denies
open during another writer's replace). measure() has a 4-attempt retry for the host map for
exactly this reason (`:299-308`) but none here, and writes COVERAGE.json with that source
absent, no marker, headline totals shrunk. Fix: compare the number of rows to
`len(glob(records/*.json))` and refuse or retry when they differ.

### F12 -- LOW: append_line docstring contradicts the code on contention
`silence.py:645-647`: "under contention this returns False and notes it rather than blocking a
model call". Code `:662-710`: on lock failure it writes UNLOCKED and returns True, and
`msvcrt.locking(LK_LOCK)` (`:732`) itself blocks ~10 s (10 x 1 s retries) before raising,
so a model call CAN be stalled up to 10 s. The `_lock_exclusive` comment (`:730-731`,
"Once is the bound") is wrong the same way. Fix docstring, or use `LK_NBLCK` for a real bound.

### F13 -- LOW: `silence.swallow` is dead and swallows BaseException
`silence.py:86-135`: zero callers anywhere in src/ (grep `swallow(`; the docstring itself says
"no live callers"). Its `__exit__` returns True for any `exc_type`, so `with swallow(...)` also
eats KeyboardInterrupt/SystemExit/GeneratorExit (repro `t1.py`: "swallow ate KeyboardInterrupt").
Fix: delete it, or `if not issubclass(exc_type, Exception): return False`.

### F14 -- LOW: hodge_decompose's convergence tolerance is absolute, so eta depends on flow scale
`resonance.py:181` `max shift < tol` with `tol=1e-9` against the raw flow. Same exact ladder
(a>b>c>d, all pair margins), scale s: s=1 eta 1.0; 1e-8 1.0; 1e-9 0.9999; 1e-10 0.9753 with
`converged: True, sweeps: 1` (`t3.py`). eta is dimensionless and must be scale-invariant;
the function reports a converged measurement of something unsettled. Inert today (no production
caller) but the module's own doctrine is "a confident measurement of nothing". Fix: relative
tolerance `tol * max(1.0, max|f|)`, or normalise flows by max|f|.

### F15 -- LOW: snapshot label can escape state/snapshots on Windows
`snapshot.py:124` sanitises the label with `replace(os.sep, "_")`, which on Windows replaces only
backslash; a label containing `/` (e.g. `../x`) makes `dest = ROOT/../x-<ns>-<pid>`, outside
ROOT, and `listing()` never sees it. All current callers pass constants, so latent, but this is
the module whose `_rel`/`_safe_join` were written against exactly this escape. Fix: replace both
separators (and `..`) or `re.sub(r"[^A-Za-z0-9._-]", "_", label)`.

### F16 -- LOW: stale citations and frozen counts in comments
- `tiers.py:484-491` cites "DELIBERATE_JOIN = 2000.0 at :122", "the docstring's original
  measurement at :55" and ":50-59"; live lines are 174, 72 and the docstring block near 63-79.
  `tiers.py:123` "The 13 unaddressed shelves" is a present-tense frozen count in a module that
  says (`:38-45`) counts must not be written into prose.
- `magnitude.py:1278` "The local window is 6,144 tokens" contradicts `:187-201` and `:1294-1299`
  in the same function (12,288 since 2026-08-24).
- `magnitude.py:779` `assay.py:174` for the NONE credit: assay.py:174 is now a comment paragraph
  about NONE vs INAPPLICABLE, the credit logic is near `:1338`.
Fix: cite by symbol, as the tree's own doctrine says.

## Questions

1. `magnitude._split_assay._one_axis` (`:1050`) keeps the HIGHEST-scored answering slice for an
   axis while the docstring says "the best-evidenced slice's answer". Max over noisy per-slice
   model scores is an upward-biased estimator. Deliberate?
2. `magnitude.run_batch` rewrites the whole ASSAYS.json from an in-memory `done` on every result
   (`:1921`); two `--batch` processes (the comment at `:1913-1916` says a second one exists) lose
   each other's records with no compare-and-swap. Is a single `--batch` guaranteed elsewhere?
3. `secondopinion.file_orders` (`:509`) lists only the first 4 sites per rule in a work order
   ("+N more", full list a `ruff` away). Disclosed, but Hard Rule 0 says never truncate a
   roster; the queue field elsewhere was made uncapped for that reason. Keep the cap?
4. `silence.instrument` (`:1304-1307`) writes `.presilence` and the source with bare `open("w")`
   (not atomic, on live src/ that codewatch fingerprints), and a second run overwrites the
   pristine `.presilence` with an already-instrumented copy. Intended for a one-shot tool?
5. `coverage._CLASSIFIER_VERSION` covers `_state_of_file`/`_empty_state`, but `_empty_state` also
   depends on `feats.CLEAN_NEGATIVES`; a change to that tuple leaves memoised verdicts stale by
   the same mechanism the header describes. Fold its digest into the version key?
6. `snapshot.verify` returns True for a manifest whose `took` is empty (a snapshot that
   `before()` refused, "captured NOTHING", leaves such a directory) and `--verify all` walks those;
   `restore` also merges directories (`dirs_exist_ok`) rather than mirroring, so files created
   after the snapshot survive a "restore". Both may be intended ("deliberately dumb").
7. Standing class question (already OWNER-routed 1e6f99e54b25 etc.; not re-filed): `tiers.main`,
   `address_space.main`, `onomast.main`, `coverage.main`, `magnitude` writers have no halt
   interlock. F1 makes this reachable without anyone running them by hand.

## Cleared (examined closely, found correct)

- magnitude: `_resolve_citation` number/exact/containment/overlap ladder and the numbered=False
  one-way path; `subject_refusal` a-d ordering; `quantity_scores` guard 3 wiring; `saturated`
  six-axis floor; `_status_score` sentinels; `compose` round-robin budget (budget is None on
  every live call, `dropped` always 0); `_split_gate` guards 1+3; epoch/anchor DEFERRED returns;
  `settled()`; `run_batch` lock + tally; calibrate `_land` atomic checkpoint.
- silence: `_block_reaches_sink`/`_stmts_after` taint walk (unhandled `Match` nodes fail toward
  SILENT, the safe side); `_suppressed_names/_suppress_is_declared`; `write_json` tmp naming,
  fsync, discard-on-refuse; `replace_retry` vs `replace_if_unchanged` re-digest per attempt;
  `_digest_or_unreadable`; `note()` total; `instrument` bottom-up insertion and re-parse check.
- allsweep: `_HALT_REFUSAL` import, `run_verifier` grading, `dangling_count`, `reconcile`
  uncapped `names`, `_row_is_fault` fail-closed, lint BLIND paths, `bad` sum and landed gate.
- secondopinion: `_exe` reason split, exit-code handling per tool (vulture rc 3), torn-tree
  fingerprint and `--file-orders` refusal, three-branch secrets comparison.
- tiers: CUTS/MULTIVERSE invariants raised not asserted; `_components`; `xenoverse_grounding`
  containment-by-construction; `_load_groundings` fail-open/writer fail-closed; `deliberate_joins`
  uncapped; p99.5 nearest-rank arithmetic; write gates and rc.
- coverage: `state_of` precedence and READ max-pages; memo keyed by path+name+classifier version;
  `_so_save` dirty-on-landed; host-map retry/refusal; `report` disclosed floors and caps.
- snapshot: `_rel`, `_safe_join`, all-or-nothing `before`, manifest write verdict, `restore` missing
  refusal, `_dir_matches` byte compare.
- resonance: Gauss-Seidel sweep and gauge fix, no-evidence vs eta 1.0 separation, isolated-node
  raise, `incomparability_rate` unmeasured/tied split with uncapped examples.

## Coverage recorded

`sweep_plan.record('run67', ['magnitude.py', 'silence.py', 'allsweep.py', 'secondopinion.py',
'tiers.py', 'coverage.py', 'snapshot.py', 'resonance.py'], batch=12)` run after this file was written.
