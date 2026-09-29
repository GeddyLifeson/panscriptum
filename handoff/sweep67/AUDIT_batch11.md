# sweep67 (run67) batch 11 - audit

## Scope

Every line read with the Read tool, sequentially, in chunks. Line counts match `wc -l` (6,783 total):

| module | lines |
|---|---:|
| src/overnight.py  | 2150 |
| src/chain.py      | 1305 |
| src/autostart.py  |  874 |
| src/gpu_lane.py   |  739 |
| src/prose_gate.py |  564 |
| src/burgs.py      |  472 |
| src/navtree.py    |  367 |
| src/physics.py    |  312 |

Read-only for the project. Scratch scripts (t1.py, t2.py, t3.py) live under the session scratchpad in
%TEMP%; `overnight.HERE` and `gpu_lane.LANE` were pointed at temp dirs before any write path ran. No job,
phase, drill, verify_math, generate, publish or mutate was run. No subagents.

## Prior-audit cross-check

`handoff/sweep66/AUDIT_batch07.md` (physics), `_batch10.md` (navtree), `_batch11.md` (overnight, chain),
`_batch05.md` (autostart), `_batch15.md` (prose_gate, burgs), `_batch16.md` (gpu_lane) all reported 0 findings
for these modules. Each earlier statement re-checked against current source:

- overnight `drill_rc == 0` prose gate, `_prose_enabled` delegation, `_guarded_popen` / `_PROBE_BLIND`,
  `BUSY_STATUSES` with rc=17 and paused, idle-halt fail-closed `except`: all still hold. Not re-argued.
- chain `_RECIPE_KEY` / held-root fix (now chain.py:372-424): still present and correct.
- burgs: sweep66 batch15 noted `main()` had no halt check (order 21c075e5e2d6). That is now FIXED:
  `_assert_not_halted` at burgs.py:303-337, only on `--write`. navtree.py:236-271 and chain.py:1129-1171
  carry the same guard. That earlier question is closed.
- prose_gate `unearned_instrument` parenthetical fallback (39a0542b03f3): fallback is gone
  (prose_gate.py:551-563, exact-name match). `instrument_shortfall` bare-marker rule (d03706b5eaf0) is now
  as its own comment says (prose_gate.py:489-506). Both earlier owner questions are closed in code.
- physics: still the four guarded functions, zero logic defects (one docstring number wrong, F6 below).
- gpu_lane: `_slot_count`, `_alive`, heartbeat covering the fg claim while queued (new since sweep66,
  gpu_lane.py:623-635) all hold.
- autostart.py has grown 613 -> 874 lines (scheduled-task keeper, `_ensure_decision`); new code read in full,
  no logic defect found.

## Findings

### F1. `write_status` renders a FAILED coverage snapshot as a row of zeros (overnight.py:1490-1518, 2032-2048) - MODERATE

`coverage_snapshot()` returns `{"error": ...}` on failure and `main()` appends that dict to `history`
(2035). The log line is fixed (2042-2044), and the comment at 2036-2041 says the zero-row problem was a
"reporting fix", but `write_status()` still does `cur = history[-1]` and `cur.get(k, 0)`. Reproduced
(t1.py, HERE redirected to a temp dir), history = one good cycle then one error cycle:

    | entries cited | 0 | 1,000 | -1,000 |
    | cited % | 0 | 10.0 | -10.0 |
    ...
    | 2 | 01:00 | 0 | 0 | 0 |

STATUS.md is copied verbatim into the public repo by publish.py, so a transient coverage.py failure
publishes "cited 0, change -1,000" as a measurement. If the FIRST cycle of a run is the failed one,
`first` is the error dict and every later "change" column is inflated by the whole corpus.
Fix: choose `cur` / `first` from rows that carry no `"error"` key, and render error rows in the cycles
table as "not measured" instead of 0.

### F2. navtree lists 1,569 of 14,592 worlds and its audit cannot see it (navtree.py:44-57, 106-116, 217-233) - MODERATE (Hard Rule 0 shape)

`build()` takes its world set from `data/SEVENFOLD.json` (`tree["worlds"]`) and only uses `WS.build_all()`
for seed metadata. Measured (t3.py):

- `WS.build_all()`: 14,592 worlds, 14,512 distinct designations
- SEVENFOLD.json `worlds`: 1,569 (file dated 2026-08-20; NAVTREE.json 2026-08-24)
- built but absent from SEVENFOLD: 13,025 designations get no node; SEVENFOLD entries not built: 82
- NAVTREE.json lists 1,569 worlds; `state/NAVTREE_AUDIT.json` says 0 problems

The header promises "EVERY ADDRESSED THING GETS A NODE", but `audit()` only checks the tree against itself, so
a stale SEVENFOLD produces a smaller universe of the same shape with a clean audit. Nothing in the supervisor
lap refreshes sevenfold.py (grep: only navtree/publish/render/sevenfold name SEVENFOLD.json). Also `seeds` is
keyed by `designation` (navtree.py:54), the exact non-unique key burgs.py:357-366 documents as dropping worlds:
80 worlds collapse (14,592 vs 14,512), the last one wins its seed/features.
Fix: in `build()` compare `set(seeds)` with `set(tree["worlds"])`, add both differences (and the duplicate
count) to `problems` so `--write` refuses, and key `seeds` on a list per designation as burgs.py now does.
Separately (operational, not code): SEVENFOLD.json / NAVTREE.json need regenerating.

### F3. `chain.py --limit N` truncates the ranked-by-path corpus and writes CHAIN.json unmarked (chain.py:672, 1206) - LOW-MODERATE

`extract()` does `rows = rows[:limit]` on rows sorted by feats-file path (harvest, 484), i.e. an alphabetical
head - the Goku-is-past-the-window shape Hard Rule 0 describes. `_run` then fits and calls `write_result`,
which lands `data/CHAIN.json`. The document records `unanswered.sentences` (= the truncated count) but never
the harvested total or that a limit was applied, so a limited debug run is indistinguishable on disk from a
full pass (pipeline.phase_chain never passes a limit, so only a hand-run reaches it).
Fix: refuse `--limit` together with a write (or skip `write_result` / write to a scratch path), or record
`{"limit": N, "harvested": len(rows)}` in the document.

### F4. Stale line-number comment in overnight.py:1601-1602 - LOW

"`supervisor_alive()` (called at autostart.py:435) ... `start_supervisor()` (called at autostart.py:463)".
Current call sites are autostart.py:478 and :539 (autostart grew by 261 lines). The file's own comments
elsewhere insist on content labels over line numbers (overnight.py:957-963). Replace with names.

### F5. gpu_lane slot reclaim can delete a live slot (gpu_lane.py:421-454) - LOW

`_take_slot` reads a record, judges it expired, then `_remove_retry(path)` unconditionally. If another process
completes its own reclaim + O_EXCL create between this read and this remove, the remove deletes the NEW
holder's fresh slot and this caller then creates one too. Reproduced deterministically by interleaving the
steps (t2.py, MAX_SLOTS=1): both A and B end up holding slot.0. Window is microseconds and needs two callers
noticing the same expired slot at once, which is plausible when a holder dies with several processes polling
every 0.4 s. Effect is one extra concurrent model call (the module fails open by design), so LOW.
Fix: re-read immediately before removing and remove only if the record still equals the expired one, or
rename-to-tombstone first.

### F6. gpu_lane fail-open gap: a parseable slot file with a non-numeric heartbeat raises out of `lane()` (gpu_lane.py:260, 449-453) - LOW

`_expired()` does `float(rec.get("heartbeat") or 0)` with no guard, and `_take_slot` is not wrapped by `lane()`.
`{"pid": <live pid>, "heartbeat": "abc"}` in slot.0.json makes `with lane("x")` raise ValueError to the caller
instead of proceeding (reproduced, t2.py). The header says "a corrupt claim file ... all of them end in go
ahead anyway". Unparseable JSON is handled (`_read` -> None); only wrong-typed-but-valid JSON escapes. Only this
module writes those files, so LOW. Fix: `try/except (TypeError, ValueError): return True` in `_expired`.

### F7. physics.py:86-88 docstring number is wrong - LOW (documentation)

"At 0.5c the Newtonian formula understates the energy by about a third." Measured: Newtonian is 0.808 of the
relativistic value, i.e. it understates by 19%. The qualitative point stands; the figure is wrong in a docstring
whose stated purpose is that this arithmetic be right.

## Questions

1. overnight.py:1811-1824 - a halt seen at the TOP of a lap `break`s and ends the supervisor ("supervisor
   finished"), while the idle branch (2084-2137) argues a halted supervisor must WAIT, because exiting once
   stranded the library after the halt cleared. Reading autostart's `_start_decision`, the watchdog restarts a
   supervisor after the halt lifts, so the exit is probably deliberate. Confirming: is the two-behaviour split
   intended?
2. overnight.py `_guarded_popen` / `run` / `start` match on the script basename only (`running("feats.py")`),
   while ALL_JOBS uses "feats.py --roll". A hand-run `feats.py --mine` therefore blocks the supervisor's roll for
   its duration. Fails in the safe direction; intended?
3. prose_gate.py:486-499 - "Not applicable" / "uninstrumented" / an axis label are searched across the whole
   entry block, not just the Instrument section, so the phrase appearing in ordinary Record prose satisfies the
   check. Is section-scoping wanted, or is presence-anywhere the accepted strength of layer 4c?
4. prose_gate.py:266-267 - the body-length strip removes any line STARTING with the words Shelfmark/Class/
   Magnitude/Threads (no colon), so a prose line beginning "Class..." or "Threads of..." is not counted toward
   the 120-character floor. Over-refusal only; acceptable?
5. autostart.py:640-652 - `--ensure` (scheduled task, every 10 min) starts the watchdog without asking the halt
   or the pause, by stated design (the watchdog asks). Also, if Task Scheduler refuses job breakaway
   (autostart.py:626-637), the fallback child stays inside the task's job object; does it survive the one-shot's
   exit on this Windows build? Could not test without touching Task Scheduler.

## Cleared

- overnight.py: `_proc_lines` three-answer contract and TTL; `running`/`_cmd_is_running`/`_in_this_tree`
  quote-aware tokeniser with `-m`/`-c` refusal; `_guarded_popen` locked double-check; `_manager_stopped` both
  spellings and fail-closed; `run`/`start`/`join` timeouts and handle closing (time ceilings, not content caps);
  `coverage_snapshot` rc+mtime check; `preflight` label-by-identity and DID-NOT-COMPLETE branch;
  `safety_drill` rc handling; `weave_index_decision` (None does not rebuild); `identity_refresh_cycle` /
  `canon_backup_cycle` mtime rate-limits; `name_rc` sign handling; keeper and keep-warm threads (`gpu_lane`
  API names `status()["slots"]`, `foreground_active`, `lane` all exist); idle/`BUSY_STATUSES` arithmetic.
  `write_status` atomic landing is fine apart from F1.
- chain.py: harvest CAS (`_land_harvest`, `refresh_continuity`), recipe key, held roots, dedup key uses the full
  sentence, `extract` model-output guards and unanswered tally, `adjudicate_mutuals` dispositions, singleton
  claim/release, `landed()` (json.loads NaN constants are shared objects, so NaN round-trip compares equal),
  `write_result` uncapped roster.
- autostart.py: `_start_decision` ordering (halt, pause, budget), tri-state sensors, twin check retries,
  VBS/`task_state` content comparison, `--status` tri-state expressions (precedence checked), handle closing.
- gpu_lane.py: `_slot_count`, `_alive` (Windows OpenProcess path), heartbeat over slot and claim, `_touch` never
  resurrects, `lane` unarbitrable/permission-denied ceilings, `status` partial flag.
- prose_gate.py: strict `is not True` gate, `floor_ok` (NaN and bool edge cases fine), `evidence_ok`,
  section/ghost/extra accounting, `_AXIS_RE` decoration tolerance, exact-name `unearned_instrument`.
- burgs.py: `class_histogram` vs brute-force classification over 4,800 (seed, era, condition) worlds: 0
  mismatches (t1.py); `burgs_for` limit-may-only-narrow; parameters-not-rosters write; halt guard on `--write`.
  Only a stale ":301" line reference in the module docstring (the 5,986 figure now sits near line 361) - not
  counted, the passage is explicitly historical.
- navtree.py: name-coining determinism (tie-breaks), `sources_under` dotted-prefix, `audit` self-consistency,
  gated writes and exit codes. (F2 is about what it does not check.)
- physics.py: all guard orderings and result-finiteness checks; `binding_energy` formula.
