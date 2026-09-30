# sweep68 batch 01 -- AUDIT

## Scope

| module | lines | read |
|---|---|---|
| `src/drill.py` | 30,315 (`if __name__ == "__main__":` at 30314-30315) | 1 to 30315 in 1,000-line chunks with the Read tool, none skipped |

The file did not change while it was read (mtime 2026-09-29 22:34). Nothing under `src/`, `data/`,
`state/`, `output/`, `prompts/` or `config.yaml` was edited or run. Reproductions ran in copies of the kit
under `%TEMP%\aud68_01\kit*` (each copy's `HERE` is the copy, asserted in the script), never in the live tree.
`drill.py` was imported from those copies (import-time spy and `pipeline.LOG` redirect are scratch); its
`main()` was called only with a one-fake-area tuple inside a copy. `mutate.py`'s `_run_mutation` was driven only
in a copy with a supplied scratch root. Scripts: `roster.py`, `netargs.py`, `repro.py`, `runnet.py`, `wt.py`,
`walkjunction.py`, `mkkits.py`, `mutkits.py`, `mutmut.py`.

Static checks over the whole file (ast, `roster.py` / `netargs.py`): all 50 `drill_*` areas are named in
`main()`'s tuple, `drill_ledger_witness` is last; 820 `net(` call sites, no duplicate net name inside any function
and none globally; no module-level function is unreferenced; the 36 nested defs with no references are all stub-class
methods; no `net(...)` is handed a constant, a non-callable expression or an eager call other than the two
`(lambda v: (lambda: ...))(x)` factories; no area is net-free. `liveness.scan()` sums to 45 against `LIVENESS_CEILING = 52`
(headroom 7, under the ten a whole orphaned module contributes).

## Prior-audit cross-check (handoff/sweep67/AUDIT_batch01.md)

| prior | status |
|---|---|
| F1 probe-cleanup notes reach the ledger witness | **Partly fixed, still stands** for `_remove_scratch_in_live_state` (see F8). The junction, surface, unlisted, empty-find, state-probe, blast, history and litter probes now append to `_DECLARED_ESCAPES` (4573, 4684, 4819, 4902, 5227, 5277, 15409, 24654). The snapshot-area helper (8784-8798) and `prove_net` (916-929) still call `silence.note`. |
| F2 `overnight_prose_needs_a_clean_drill` substring | **Fixed**: `_is_clean_rc` / `_requires_clean_drill` (14131-14140), with three planted bypasses as controls (14179-14190). |
| F3 `_static_truth` all-False `or` | **Fixed** (1160-1163), control at 14192. The optional half (constant `Compare`) still stands, see F9. |
| F4 unreadable roll | **Fixed**: torn scratch file (23750-23759). |
| F5 coverage vacuous pass | **Fixed** (14312-14313), control at 14331. |
| F6 stale docstrings | **Fixed** (`_reread_the_breaches` says 3-tuple; `_catalog_matches_disk` names the right area). |
| Q1 source-shape nets read `HERE/src`, not `_srcdir()` | **Still stands, no ruling**: `generate_lands_catalog_every_chapter` (14046), `overnight_prose_needs_a_clean_drill` (14114), `throttle_iterates_a_snapshot` (14210), `_publish_never_swallows_a_missing_safety` (5886), `_no_programmatic_clear` (5406), `_counts_decided_by_substring` (19997), `_no_new_bare_kill0_probe` (20581), `_a_module_claimed_wired_is_actually_imported` (20658), `_guards_are_wired_where_claimed` (13792), `_withdrawal_takes_a_snapshot` (8934), `every_ollama_call_site_takes_a_lane_turn` (21326). |
| Q2 `every_ollama_call_site_takes_a_lane_turn` skips `src/deprecated/` | **Still stands** (21326 globs `src/*.py`). |
| Q3 `_gate_closed_shelf_holds` writes with plain `write_json`, path not in `_live_watch()` | **Still stands** (13861-13871; watch list 15753-15778). |
| Q4 `_live_watch()` hand-kept | **Still stands**. |

## Findings

### F1. Probe names carry the pid, so a probe left behind by a kill is never cleaned up; an orphaned junction sits inside published `src/`. MEDIUM. Source verified; junction descent reproduced; kill-window not reproduced (UNVERIFIED as an occurrence).
`drill.py:4583-4587` (order 7a487cfab844): `_JUNCTION_PROBE_NAME = "__drill_junction_probe_%d__" % os.getpid()`,
and the same for the surface junction (4587), `handoff/__drill_blast_probe_%d__.md` (4583), the unlisted root
file (4584) and the empty-find file (4585). The junction probes create `src/<name>` with `mutate.make_junction`
pointing at `state/` (4832-4833) or `data/` (4927-4928); `unstage()` (4799, 4891) removes it in a `finally`.
Before the rename the name was fixed: a run killed inside the window left `src/__drill_junction_probe__`, and the next
run's `make_junction` failed on the existing name, took the `except OSError` arm and called `unstage()`, which removed
it. With a per-process name nothing revisits the orphan. A `grep` of `src/` for `__drill_` finds no reaper; `main()` has none.
Failure scenario: `overnight.safety_drill` times out and kills the drill (or the foreman SIGTERMs it, or Norton denies the
`os.rmdir` in `unstage()`, which `_DECLARED_ESCAPES` records and forgives) between `make_junction` and `unstage()`.
`src/__drill_junction_probe_<pid>__` -> `state/` remains. `publish.sync_tree` walks `COPY_DIRS = ("src", ...)`
(`publish.py:151`) with `os.walk(root, onerror=...)` (`publish.py:1283`, default `followlinks=False`).
`walkjunction.py` on this Python (3.13.9): `os.path.islink(junction)` is False, `isjunction` True, and `os.walk` lists
`__drill_junction_probe_1234__\secret.json` beside `a.py`. So the next push cycle stages every non-skipped file under
`state/` (or, for the surface probe, 1 GB of `data/`) into the export tree; `scan_for_secrets` is then the only gate,
and a hit there raises SECRET_IN_EXPORT and stops publishing. The file probes (`handoff/__drill_blast_probe_<pid>__.md`,
`handoff/__drill_empty_find_<pid>__.txt`) leak the same way into the public repo (`_is_agent_scratch` refuses only code
suffixes). Right now none of these exist on disk.
Fix: sweep `src/__drill_*`, `handoff/__drill_*`, `__drill_*` at the root and `data/__drill_*` at drill start (unlink the junction
before anything else), or make `publish.sync_tree` refuse any directory that `os.path.isjunction` names.

### F2. `_esc_sandbox` can fail halfway through its redirect loop and leaves `escalation.HALT_FILE` pointing at scratch, so the DRILL_BREACH halt is written to the wrong file. MEDIUM. REPRODUCED (`repro.py kit1 sandbox_leak`).
`drill.py:15945-15952`: `saved[(mod, attr)] = getattr(mod, attr)` sits outside any `try`. `_SANDBOX_REDIRECTS` (15877-15894) begins
with the four `escalation` attributes. If a later row names an attribute that no longer exists (`snapshot.ROOT`,
`codewatch.LEDGER_LOCK`, `withdraw_chapters.CATALOG`, ... renamed in a refactor), the loop raises after the earlier rows are
already redirected, `_esc_sandbox` never returns `restore`, and `_esc_probe` (16003) calls it before its own `try`.
Repro (copy of the kit, `del snapshot.ROOT`): `_esc_sandbox()` raises `AttributeError: module 'snapshot' has no attribute 'ROOT'`;
`ESC.HALT_FILE` is left at `%TEMP%\drill_escbehav_xxxx\HALT.json`; `ESC.escalate(ESC.OWNER, "DRILL_BREACH", ...)` returns
`halt_landed = True` and `<kit>/state/HALT.json` does not exist. In production the affected net is recorded as breached, `main()`
prints "the library has been HALTED" (30292), and the halt lands in a directory nothing reads. Every later sandbox call repeats
the failure and stacks another redirect on top of the last.
This is the drill's own top rung failing open, in exactly the condition (a code edit that renames a constant) the drill exists to catch.
Fix: build `saved` in a `try` that restores what it already set on any exception, or resolve all `getattr`s before the first `setattr`.

### F3. An area that dies is halted on a single reading; the re-read that protects every other breach cannot re-ask it. MEDIUM. REPRODUCED (`repro.py kit2 area_dies` vs `kit2b area_flaky`).
`drill.py:30004-30011` turns an exception that escapes an area function into a `held: False` row named "AREA DID NOT RUN".
`_reread_the_breaches` (26359-26363) looks the row up in `_ATTACKS`, finds nothing, writes
`"no attack was recorded for this row -- it cannot be re-asked"` and appends it to `reproduced`; `main()` then raises
DRILL_BREACH at OWNER. Order 71ae3fa7e55e's whole argument is that a photograph of a tree under edit must not halt the library.
Many areas start with a local import (`import publish as P` in `drill_publish` at 5480, `import pipeline as PL` in `drill_no_caps`,
`import ledger_guard as LG`, `import assay as A`, ...) or take a real `SNAP.before("drill", ["config.yaml"])` (8966) outside any net,
so the moment an agent has `publish.py` half-written when that line runs, the area dies and the library halts with no settle wait and
no three-way re-read. Repro: an area that raises `SyntaxError` -> `rc = 1`, `state/HALT.json` written, row REPRODUCED "cannot be re-asked";
an area whose net reads False once -> "recovered ... held on all 3 re-reads", no halt.
Possibly deliberate (fail closed on "could not run"); the comment at 29985-30003 argues for recording it, not for skipping the re-read.
Fix: register a re-run for the area itself (`_ATTACKS[(row area, row net)] = lambda: (fn(), <no new held:False rows>)`), or classify an import
failure separately from an assertion failure and settle first.

### F4. Tonight's `_net_run68_generate_holds_shared_address` drives the helper and never asks whether `generate.main()` calls it. MEDIUM. REPRODUCED (`repro.py kit3 net3`).
`drill.py:28598-28609` calls `G.hold_shared_addresses(jobs)` on fixtures and checks the three return values. The protection is
`generate.py:1278`: `jobs, shared_addr, _held = hold_shared_addresses(jobs)`. Delete that line, or keep it and drop the answer, and the
net reads True while `generate.py` writes every shared-address job twice over itself -- the 1,251-duplicate incident the net is named for.
This file's own doctrine (lines 3-9, `_the_loop_asks_the_gate`, `_guards_are_wired_where_claimed`) is that a correct pure function nothing calls is
a comment. Repro: copy of the kit with `generate.py:1278` replaced by `_unused = hold_shared_addresses(jobs); shared_addr, _held = set(), {}`:
the net returns True.
Fix: add the wiring half -- `_bound_from_call(tree, main, "hold_shared_addresses")` bound, and `jobs` reassigned from element 0 -- read through `_srcdir()`.

### F5. Tonight's `a_halt_one_mutant_raised_does_not_judge_the_next` watches one of three scrub sites. LOW. REPRODUCED (`runnet.py kit5 / kit5b`).
`drill.py:23131-23177` drives `_run_mutation(..., limit=2, ...)` with the default `rebaseline_every=None` (`mutate.py:2280`). `_scrub_sandbox_halt(root)`
is called at `mutate.py:2071` (hang confirmation), `2439` (`_refresh_baseline`) and `2540` (before each mutant). The docstring of `_scrub_sandbox_halt`
(1966) names "every baseline refresh" as damaged by a leaked halt, yet only the per-mutant call is exercised. Result on copies of the kit:
unmodified `mutate.py` -> True; per-mutant scrub removed -> False (the net has teeth there); refresh-site scrub removed -> True.
A regression that puts the halted sandbox back into the periodic re-photograph re-creates the twenty-hour disabled-detector outcome with the battery green.
Fix: a second drive with `rebaseline_every=1e-9` (as `a_baseline_that_moves_mid_run_...` at 23049 already does) whose gate writes a halt when the target differs.

### F6. `_net_run68_phase8_volume_codes` cannot see the owner-exclusion arm. LOW. REPRODUCED (`repro.py kit4 net4`).
`drill.py:28558-28595`. The fixture's excluded source ("Gamma Out") is also absent from `MB.volume_codes`, so with
`pipeline.py:3520` (`if src in excluded:`) deleted the source falls to the next arm (`src not in codes` -> "not on the roll") and the landed
job ids are identical. Copy with the exclusion arm removed: net True; copy with the `UNASSIGNED` arm (`pipeline.py:3529`) removed: net False (so the
net does bite on that arm and on the bare-Series-code regression). The two arms differ in what they do to the phase: `refused` with no `jobs` appends
`False` to `landed` and holds phase 8 open (`pipeline.py`, "every ready source refused to build"), `held` does not. The net does not read `st["done"]`
or the log, so the distinction is unwatched. Fix: assert `"write" in st["done"]` for a roll whose only ready source is the excluded one.

### F7. Two nets accept a call whose answer is thrown away. LOW-MEDIUM. REPRODUCED (`repro.py kit1 weak_predicates`).
- `the_watchdog_loop_actually_asks` (`drill.py:8041-8052`): `decides` is any `Call` to the name `_start_decision`; `reads_halt` is any attribute call named `status`
  (`psutil.Process(...).status()` qualifies). A `watch()` that calls `_start_decision(...)` and ignores the result, and calls `p.status()` on a process, returns True.
  The sibling launcher nets use `_gate_precedes_spawn`, which requires the answer bound and the spawn on the far side of an `if` that leaves. This is the loop that spends the restart budget.
- `the_write_needs_the_owners_ratification` (`drill.py:18980-18991`): `_calls_within(tree, main, "prose_gate.step4_gate_open", reachable=True)` is true for a `main()` that binds
  `ok, why = PG.step4_gate_open()` and writes regardless. `threads.py:1050-1060` does refuse on `ok` today; the net cannot tell.
Fix for both: bound answer + guarded `if` that leaves before the write / the start (the `_gate_precedes_spawn` shape).

### F8. Carry-over of sweep67 F1: `_remove_scratch_in_live_state` still notes a failed tidy-up into the spied ledger. LOW (latent). REPRODUCED (`repro.py kit1 cleanup_note`).
`drill.py:8784-8798` calls `_si.note("drill.py:%s" % site)` when `shutil.rmtree` left the directory. Callers (8855, 8857, 8859, 8902, 8904, 8960, 9029, 9044) run
outside any sandbox, so the note reaches `_spy_record` and `no_probe_writes_into_the_live_failure_ledger` (26191) raises; the re-read reproduces it and the library halts.
Repro: hold a handle inside a temp dir, call the helper: `_LEDGER_ESCAPES` gains `drill.py:8798 [...] -> silent:drill.py:snapshot-dir-probe-cleanup`.
`_decline_notes` (24324) cannot catch it: its pattern needs the words in the literal, and the site is formatted from `%s`
(pattern vs `_si.note("drill.py:%s" % site)` -> no match). The comment at 8794 ("Not a verdict") contradicts the effect. `prove_net`'s three notes (916, 925, 929) are `--prove` only.
Fix: route the helper through `_DECLARED_ESCAPES` like its siblings; add `%s` call sites to the scan.

### F9. Carry-over of sweep67 F3, second half: constant comparisons are not folded. LOW. REPRODUCED.
`drill.py:1139-1164` decides `Constant`, `not`, and `and`/`or` chains only. `if 1 == 2: gate()` leaves `gate` reachable
(`repro.py kit1 weak_predicates` (c): `['gate']`), so every `reachable=True` net accepts a gate parked there.

### F10. `_write_targets` misses two write shapes. LOW. REPRODUCED (`wt.py`).
`drill.py:1738` (`if not n.args: continue`) and `1751` (`m = mode.value if isinstance(mode, ast.Constant) else ""`): of
`open(LIVE, MODE)`, `open(file=LIVE, mode='w')`, `open(LIVE, 'w')` only the third is reported. `mutation_never_touches_the_live_tree`
(22286) is built on it. Fail direction is a missed write, not a false halt.

### F11. `a_hard_linked_file_is_refused` grades an unstageable probe as a breach. LOW.
`drill.py:7539-7540` raises `RuntimeError("could not stage a hard link on this filesystem, so nothing was measured")`; `net()` records that as held=False and `main()` halts.
Every neighbour that cannot stage its probe declines through `_DECLARED_ESCAPES` (sweep66 D1 ruling; the hardlink net at 22762-22767 does). A filesystem or scanner that
refuses `os.link` halts the library over a measurement that did not happen.

### F12. Re-reads of nets that depend on area-scoped fixtures cannot recover. LOW.
`drill_snapshot` removes `sid` at the end of the area (9044); `drill_stale_writer` removes its temp dir in the area's `finally` (9499-9505). `_reread_the_breaches` re-calls
`_ATTACKS[(area, net)]` after the area ended, so "a snapshot restores byte-identically" and the stale-writer nets raise on a missing fixture and always read REPRODUCED. Fail-closed, but the three-read rule
cannot help these nets.

## Questions (possibly deliberate; owner decides)

- **Q1.** F3: is halting an area that dies on one reading intended, given the re-read ruling?
- **Q2.** F1: is a per-pid probe name worth losing self-healing? A per-run name plus a start-of-run sweep of `__drill_*` would keep both.
- **Q3.** `workorders.sweep_detectors` does `import drill as _D` (`workorders.py:1545`) to read `LIVENESS_CEILING`. Importing drill replaces `health.record`/`health.flush`
  with the spy and redirects `pipeline.LOG` for that process (`drill.py:54, 143-144`). The importer today is the short-lived `workorders.py --sweep`; a long-lived caller would grow
  `_LEDGER_ESCAPES` on every noted fault and send its real pipeline log lines to `%TEMP%`. Move the constant to a leaf module?
- **Q4.** Sweep67 Q1-Q4 above are unchanged.

## Cleared (read in full, no defect)

Import-time witness and `net()` stack (47-212, 380-419); `_src_mtime_preserved`, `_ledger_redirected`, `_quietly`, `_deliberately_failing`; `prove_net` /
`ledger_dry_run` / `_remove_scratch_tree`; the reachability primitives (1139-1876) apart from F9/F10; the PROSE / STEP4 gate nets and the disk-read gate nets (1880-2730);
the assay, cache and no-caps areas; `drill_park` and every `drill_escalation_behaviour` probe (`_call_clear_from`, `_as_a_person`, `_with_refused_writes`, the lock nets);
the codewatch area including the budget and claim nets; the publish area (scanner size and seam nets, `_publish_never_swallows_a_missing_safety`, guard fail-open nets);
ledger area; the two-writer, done-key and owner0928 areas; the mutation area's reaper nets (all four redirect `tempfile.tempdir`); `_no_sandboxed_probe_reaches_live_state`, `_every_sandboxed_probe_is_driven_by_the_witness`
and `_live_audit` event coverage; `_reread_the_breaches` three-read logic and `main()`'s verdict, stamp, mutation-run and `--to-halt` paths; `_net_run68_battery_pipeline_log_is_not_live`
(`pipeline.log` writes through the module global `LOG` at call time, so the redirect at line 54 is effective); the ~90 `_net_<hex>` nets at 26825-29765, each restoring what it stubs.

## Coverage

Recorded with `sweep_plan.record('run68', ['drill.py'], batch=1)` after the full read.
