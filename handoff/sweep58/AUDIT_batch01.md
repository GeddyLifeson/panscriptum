# Sweep 58 -- AUDIT batch 01

Modules, read in full:

| module | lines | read |
|---|---|---|
| `src/drill.py` | 20,380 when paged (mtime 23:03); 20,514 at the end of the audit (mtime 23:11:55) | all 20,380 lines top to bottom, plus both regions the concurrent editor inserted afterwards (the ~70-line `an_unreadable_pages_registry_does_not_select_the_wiki_path` in `drill_fetch`, and the ~63-line `an_unreadable_annex_join_refuses_and_a_stale_key_is_reported` in `drill_threads`). Area offsets were re-grepped against the new file to confirm those two regions are the only length changes. |

The open queue (103 orders) was read first. The full text of 19 orders touching drill.py was pulled.

Supporting measurements. All were scratch scripts. None imported drill.py, and none ran the battery.
- **Audit events.** CPython 3.13.9 on this machine raises these events:
  - write-mode `open` → `("open", path, "w", 33665)`; a read → flags 32896. `_WRITE_FLAGS` does not overlap `O_BINARY`/`O_NOINHERIT`.
  - `os.open(O_CREAT|O_EXCL|O_WRONLY)` → `("open", path, None, 1409)`.
  - `os.replace` and `shutil.move` → `os.rename`.
  - `os.makedirs` → `os.mkdir`.
  - `subprocess.Popen` → `(exe, args, cwd, env)`.
  - **`shutil.copy2` → `_winapi.CopyFile2` only.**
  - `shutil.copy` / `shutil.copyfile` → `shutil.copyfile` + `open`.
- **Line citations.** Every `file.py:NNN` citation in drill.py was dumped with the line it lands on (37 citations).

---

## src/drill.py

### New findings

**DEFECT MINOR -- `_live_audit`: the audit hook cannot see a `shutil.copy2`, the most common copy on this platform**

The hook's block comment says it watches "a write-mode open, a rename/replace, a remove, a mkdir, **a copy**, a subprocess". The copy branch is:

```python
elif event in ("os.rename", "shutil.copyfile"):
    hits = [a_ for a_ in args[:2] if _is_live(a_)]
```

Measured on this interpreter, `shutil.copy2(src, dst)` raises exactly one audit event, `_winapi.CopyFile2`. It raises no `shutil.copyfile` and no `open`. `shutil.copytree` copies every file the same way. Only `shutil.copy` and `shutil.copyfile` raise `shutil.copyfile`.

- **Failure scenario.** A probe inside `_esc_sandbox` (or library code it drives) calls `shutil.copy2(fixture, os.path.join(HERE, "state", "workorders.json"))`. The same happens when `snapshot`'s copytree lands files in an already-existing live `state/snapshots/<id>`. The live file is overwritten, and nothing is appended to `_LIVE_ESCAPES`. `restore()` does not raise. Part 3 of `_no_sandboxed_probe_reaches_live_state` stays green.
- **Remedy.** Add `"_winapi.CopyFile2"` to the rename/copy branch (`args[:2]`). Give the witness's CONTROL a `shutil.copy2` onto a live path beside the write-mode open, so a blind copy branch goes red.

**DEFECT MINOR -- `_live_watch` is narrower than the live files the new sandboxed probes depend on; `_absent_tray_is_started_not_waited_for` claims otherwise**

The docstring of `_absent_tray_is_started_not_waited_for` says:

> "All of it is restored in `finally`, inside `_esc_probe` so a stray live write fails this net."

`_live_watch()` watches 11 files, 6 directories and one prefix:
- files: `workorders.json`, `workorders_closed.jsonl`, `workorders_selftest.jsonl`, `HALT.json`, `escalation.log`, `STOPPED.json`, `CODEWATCH.json`, `HOST_QUARANTINE.json`, `BINDING_HEALTH.json`, `SWEEP_ROLL.json`, `catalog.json`
- directories: `escalations`, `codewatch_poll`, `snapshots`, `data/records`, `output/raw`, `output/compressed`
- prefix: `output/withdrawn_`

`state/OLLAMA_RESTARTS.json` (`foreman.RESTART_STAMP`) is not on the list.

- **Failure scenario.** A later edit drops `F.RESTART_STAMP = os.path.join(t, stamp_name)` in `_case`. `restart_ollama()` then runs `silence.write_json(RESTART_STAMP, st)` (foreman.py, `restart_ollama`) against the LIVE stamp. That stamp rate-limits the real foreman's remedy for 30 minutes, and on its next round the remedy answers "started the absent Ollama tray N min ago ... owner attention needed". The hook records nothing. The net goes red only later, and only incidentally, when its own read of `absent.json` fails.
- **The same gap covers the subject files of other probes W2a moved into `_esc_probe` this shift:**
  - `state/PIPELINE_STATE.json` (`_pipeline_state_keeps_a_concurrent_reopen`). If its `PL.STATE_DIR, PL.STATE = d2, path` line is lost, `PL.load_state()` reads the live state. `save_state` then lands the fixture done-keys `B#20`, `C#0` and `C#20` in it, which is permanent loss for those units.
  - `data/ONOMASTICON.json` (`_onomasticon_writers_keep_each_others_designations`)
  - `state/chain_harvest_idx.json` (`_harvest_keeps_a_patch_landed_mid_scan`)
  - `state/MAINTENANCE_RUN.json` (`_a_one_shot_push_proves_it_is_the_shift`)
  - `data/PROVIDER_MODELS.json` (`catalogue_models_shape_and_orphans`)
  - `data/WIKI_HOSTS.json` (`completeness_filename_alias_is_case_folded`)
- **Remedy.** The hook sees only this process's operations, so it can watch whole trees while a sandbox is open without catching standing daemons. Watch every write under `HERE/state`, `HERE/data`, `HERE/output` and `HERE/config.yaml` rather than a hand-kept list. This follows the block's own argument that a witness reading the same constants shares the sandbox's failure mode. Failing that, remove the "a stray live write fails this net" sentence.

**DEFECT MINOR -- two docstrings contradict `_esc_sandbox` after the consolidation**

1. `drill_escalation_behaviour.a_stop_that_was_never_recorded_closes_only_a_FALSE_order` still says:
   > "`workorders.resolve_code` is stood in for and its calls collected. It is not one of the two side effects `_esc_sandbox` already stops (`file_order` and `health.record`), so without the stand-in this probe would reach the real queue"

   `_esc_sandbox` now does `_WO.resolve_code = lambda *args, **kw: resolved.append((args, kw))`. It also redirects `workorders.OPEN_FILE`, `CLOSED_LOG` and `SELFTEST_LOG`. Neither half of the sentence is true any more.
2. `_esc_sandbox`'s own docstring still says "every probe below wants the same four redirections plus the recorder". `_SANDBOX_REDIRECTS` now holds sixteen redirections and three stubs.

- **Consequence.** A reader deciding whether a new probe needs its own `resolve_code` stand-in is told the sandbox does not provide one. That is the belief that produced order 247586e57b61, which is still open.
- **Remedy.** Rewrite both sentences. The local stand-in in the net is now redundant but harmless.

**DEFECT MINOR -- stale citation in `_withdrawal_takes_a_snapshot`**

The docstring says the word "snapshot" appears "at `withdraw_chapters.py:216-219` inside the paragraph that sits directly above the code -- 'A COPY BEFORE THE IRREVERSIBLE STEP ...'". Line 216 of withdraw_chapters.py is now `except ImportError as _esc_gone:`. The paragraph is at :280, directly above `SNAP.before("withdraw-chapters", ...)` at :285. No open citation order lists this site (89503c58409f, 386c0d66e31e, 1d45a56ae1d8 and d7efd67caa6f were checked).

- **Remedy.** Cite the symbol instead: "the `A COPY BEFORE THE IRREVERSIBLE STEP` comment above `SNAP.before(...)` in `withdraw_chapters.main`".

**QUESTION -- `_live_audit` counts a child with an inherited cwd as a live write, so a sandboxed probe's verdict depends on where the drill was launched**

```python
here_cwd = os.path.normcase(os.path.abspath(os.fsdecode(cwd) if cwd else os.getcwd()))
if here_cwd == root or here_cwd.startswith(root + os.sep):
    hits.append("cwd=" + here_cwd)
```

- Launched from the repo root or `src/`, a sandboxed probe that spawns a child without `cwd=` breaches, and `restore()` raises.
- Launched from anywhere else, the same probe holds.

It is latent today: none of the 17 modules the sandboxed probes drive calls `subprocess.*` (grep). A cwd is not a write, and a harmless `tasklist` spawned by library code inside a sandbox would halt the library at OWNER rung from one directory and not another. **Question:** should the rule fire only on an absolute path argument inside the tree, or stay deliberately strict?

**QUESTION -- part 2 of THE LIVE-STATE WITNESS drives only the seven `_LIVE_STATE_PROBES`**

The comment above `_LIVE_STATE_PROBES` says driving them "is what makes the witness able to go red on a probe taken back OUT of the sandbox, which no after-the-fact reading of the escape list can see." About 40 probes were moved into `_esc_probe` this shift, several whose subject is a live file (the seven listed in the second DEFECT above). They are covered only by part 3, which records nothing for a probe outside every sandbox. If one of them loses its `_esc_probe` wrapper, the witness cannot see it. **Question:** should probes whose subject is a live file join the list, or is "found writing live state" the intended membership rule?

### KNOWN (matched to open orders; accuracy re-checked against the text as read)

- **KNOWN 70a74f7a0628.** Accurate, and slightly understated. The following still run against live state:
  - `drill_rung_four`: `a_stop_is_written_down_and_readable`, `resuming_demands_a_written_ruling`, `a_probe_leaves_no_order_behind` (live `STOPPED.json`, cleanups via `_sweep_probe_litter`)
  - `drill_park.area_fault_does_not_close_the_park` (`WO.resolve_code` on the live queue)
  - `blast_cap_bites` (live `resolve_code`)
  - `cannot_edit_shared_run_state` (live `state/__drill_state_probe__.json`)
  - `_run_the_runner` (real `codewatch.exit_if_stale`)

  The order names only the resolve_code cleanups. The `ESC.escalate` / `stop_subsystem` calls in `area_fault_does_not_close_the_park` and the rung-4 probes also append to the live `state/escalation.log` and `state/escalations/__drill__.log`, and file the order through the live `file_order`.
- **KNOWN 0954a44e057d.** Still accurate, all five:
  - `_unparseable_reply_is_benched_and_ledgered`: its `fail()` re-implements the rule.
  - `_coverage_reaches_unreachable`: its "report prints it" half is `"UNREACHABLE" in CV.report.__doc__ / inspect.getsource`.
  - `_rows_in`: returns 0 on `OSError`.
  - `_policy_corpus_clean`: passes on an empty glob.
  - `index_spine_agrees_with_the_resolver`: `return True` when the DB is absent.
- **KNOWN 156c2e28f823 item 1.** Still accurate: `_sandbox_without_its_target_refuses`'s `not any(os.path.isdir(r) for r in roots)` runs after the `finally` has already rmtree'd `roots`.
- **KNOWN 7a487cfab844.** Still accurate:
  - `run_actually_holds_the_lock`: its `mkdtemp` is never removed.
  - `tempfile.mktemp` in `history_heals_nonnumeric_at` / `movement_survives_nonnumeric_metric`.
  - `prove_net`: swallows a failed junction `rmdir`.
  - Fixed-name artefacts under `HERE`, `handoff/` and `state/`.
  - `the_document_ingester_asks_about_the_halt`: says "the record writer is stubbed", but only `ID.HOSTS` is redirected.
  - The `drill_snapshot` nets still write live `state/` and `state/snapshots`.
- **KNOWN 400d5c76e6f8.** Still accurate. Abstention and cleanup `silence.note` sites remain unwrapped, e.g.:
  - the junction probes' `drill.py:junction-probe-unstageable` / `surface-probe-*`
  - `paid_access_stays_switched_off`
  - `_twins_ignores_a_foreign_tree`
  - `datasette_config_is_generated_not_copied`
- **KNOWN e727ab804c5b.** Still accurate, and the population grew this shift. New stand-ins wider than their subjects include:
  - `_Rec.run(self, args, **kw)` and `_Rec.Popen(self, args, **kw)` in `_absent_tray_is_started_not_waited_for`
  - `_ur.urlopen = lambda *a_, **k_: True`
  - `PB.maintenance_shift_live = lambda *a_, **k_: ...` and `PB._mutation_observation = lambda *a_, **k_: None`

  All accept calls the real functions would reject.
- **KNOWN 1d45a56ae1d8.** Still stale: `_backoff_stops_at_its_ceiling` cites `feats.py:159`, which now lands on `h = h.split("/")[0]...`.
- **KNOWN 89503c58409f.** Still stale:
  - `a_ladder_rung_with_no_instrument_window_refuses_to_load` cites `anchors.py:427` twice (docstring and expectation).
  - `main()`'s rc comment cites `foreman.py:115`.
- **KNOWN 54db4a3baec8 / 9245eb5f6f76.** These are agent R's areas: the two nets inserted during this audit, `an_unreadable_pages_registry_does_not_select_the_wiki_path` and `an_unreadable_annex_join_refuses_and_a_stale_key_is_reported`. Both were read; nothing is filed against them.
- **KNOWN e114b2d0fe48.** The nets landed this shift, but their orders are still OPEN: befe73801f6f, 17242f0e3f39, aa9522fcec35, 3c85cdc4e5ee, 633832bdae90, b750409c76be, d9328fe1ee38, 12d4e1b00c2f, 247586e57b61, 4be1a84f19c6, 5d686329771b, 093a35335c68. This may simply be the shift not yet closed; recorded so the close step does not miss them.

### Checked hard and found sound (so the next sweep does not re-derive them)

- **THE LIVE-STATE WITNESS** (`_no_sandboxed_probe_reaches_live_state`) can fail. Part 1's control opens a live-path file for writing (`HERE/state/workorders.json/__drill_witness_control__/x.json`). The audit event fires before the open itself fails, and `restore()` must refuse. Every event shape `_live_audit` destructures was confirmed against this interpreter, except the copy gap above.
- **`_esc_sandbox`.**
  - It fails closed on a mis-rooted redirect row.
  - `restore()` is idempotent and unwinds LIFO.
  - `_SANDBOX_REDIRECTS` covers every path constant of `escalation`, `workorders`, `binding_health`, `codewatch`, `withdraw_chapters` and `snapshot` (grepped against each module).
- **The four new `drill_escalation_behaviour` nets**, verified against escalation.py:
  - `an_unrecorded_escalation_says_so_on_stderr_and_only_then`: `recorded = _append_log(rec)` / `if not recorded:` at :301-308.
  - `a_halt_record_without_a_cleared_field_is_still_standing`: `cur.get("cleared", False)` at :1297.
  - `a_lift_whose_write_raised_does_not_report_landed`: the `os.makedirs` under a file reaches the `except` arm of `_land_clear`, `return False, "raised"`.
  - `a_cli_resume_signs_with_the_name_it_was_given`: `by=(a.by or "cli")` at :1379.

  Each kills its named mutant, and every stand-in signature matches its subject (`_append_log(rec)`, `resume_subsystem_verdict(name, ruling, by="?")`).
- **W2a's `drill_park` nets.**
  - `_absent_tray_is_started_not_waited_for` matches foreman's `_ollama_processes` / `_ollama_tray_exe` / `_start_ollama_tray` / `_ollama_answers` (a late `import urllib.request`, module-global `time`/`shutil`).
  - `_a_quiet_log_alone_does_not_license_a_kill` matches `kill_stalled_job` / `_io_moving`, which late-import `standards`, `dashboard` and `psutil`, so the `sys.modules` stand-ins are what they reach.
  - `_a_deliberate_restart_is_not_an_idle_cycle` evaluates `busy = busy_statuses(statuses)` and fails when `"rc=17"` is dropped from `BUSY_STATUSES`.
- **`_a_one_shot_push_proves_it_is_the_shift`** follows `publish.main()`'s one-shot branch (:2008-2027): no singleton claim without `--loop`, and the refusal comes before `sync_tree`.
- **`reroute_refuses_found_by_at_exactly_80`**: its hand-built prefix matches `workorders.reroute`'s `"%s | rerouted %s -> %s by %s: %s"` (:848).
- **`_scrub_recurses_into_tuple_and_set`**: `"ghp_" + "A"*24` matches publish's `ghp_[A-Za-z0-9]{20,}`.
- No new console-window omission: every spawn read passes `CREATE_NO_WINDOW`. No new Hard Rule 0 cut, and no eaten regex escape, was found in drill.py.
