# sweep68 (run68) AUDIT batch 10

## Scope

Read-only. Every line of each module read sequentially with the Read tool, in chunks. No subagents; no
pipeline phase, generate, publish `main()`, mutate, verify_math or drill was run. Scratch scripts only under
`%TEMP%/aud68_10` (`r1.py`..`r4.py`): `silence.note` / `silence.write_json` stubbed, `gpu_lane.LANE` pointed at a
temp dir, `autostart._log` and `Popen` stubbed, `dashboard.DATA/STATE` pointed at a temp dir. Nothing under
`state/` or `data/` was touched (the only live reads were `data/WEAVE_CANDIDATES.json` by
`cosmology_graph.build_graph()` and the tree's own read-only status modules).

| module | lines |
|---|---|
| src/publish.py | 2253 |
| src/dashboard.py | 1264 |
| src/autostart.py | 874 |
| src/gpu_lane.py | 755 |
| src/anchors.py | 576 |
| src/sevenfold.py | 485 |
| src/cosmography.py | 381 |
| src/cosmology_graph.py | 261 |
| src/catalog.py | 167 |

## Prior-audit cross-check (handoff/sweep67)

- b10 F2 (dashboard CSS: `.value.ok/.warn/.bad` had no rule): FIXED. dashboard.py:814 now defines all three.
  CLOSED. `publish.render_page()` reuses `dashboard.PAGE`, so the published page has it too.
- b10 F7 stale comment `publish.py:1566 "(publish.py:1214-ish)"`: FIXED (now "cited by symbol"). CLOSED.
- b10 Q6 (`standards_unavailable` written to state.json, read by nothing): STILL STANDS. Only publish.py:724 names
  it; `panelStandards` still shows "Standards not readable." only for an empty list. Carried as Question 1.
- b11 F5 (gpu_lane reclaim deletes a live slot): FIXED. `_take_slot` re-reads and removes only `if _read(path) ==
  rec` (gpu_lane.py:468). CLOSED (window narrowed, not zero; documented in the code).
- b11 F6 (gpu_lane non-numeric heartbeat raises out of `lane()`): FIXED in `_expired` (264-267). CLOSED for
  `_expired`; the same shape survives in `status()` and `foreground()` (my F6).
- b11 Q5 (`--ensure` starts the watchdog without asking halt/pause; breakaway fallback): design unchanged
  (watchdog asks both). Still a question, not re-filed. See F4 for a separate `--ensure` fault.
- b15 F10 (anchors.py stale relative reference): FIXED (comment now cites the symbol). CLOSED.
- b15 Q3 (sevenfold "exactly 7" root not a promise for any input): CLOSED by code. The root arm at
  sevenfold.py:209-222 cuts the nearest weak seam when a window is empty. Reproduced: strong-chain weighted
  blocks of n = 8..60 always give exactly 7 top branches (`r4.py`, 0 exceptions of 53).
- b08/b04/b14 (catalog.py, cosmography.py, cosmology_graph.py): no earlier finding. Re-traced, still hold.

## Findings

### F1. dashboard.py:349-364 (`_watch`) -- an unreadable or absent OVERWATCH.json reads as "0 open, 0 high", and standards.py:1232 grades that as HOLDING. MEDIUM (reproduced)

Quote: `d = json.load(open(os.path.join(DATA, "OVERWATCH.json")...` inside `try: ... except Exception: silence.note(...)`.

`out` is seeded `{"open": 0, "high": 0, "rounds": 0, "findings": [], ...}` and the except branch changes nothing,
so a torn file, a PermissionError while `overwatch.save` is mid-`os.replace` (the documented Windows case), or a
file that is simply absent, is indistinguishable from a sweep that ran and found nothing. The sibling `broken` list
directly below was repaired for exactly this in run #67 ("An unreadable ALLSWEEP.json is NOT zero broken modules
... fails closed"); `open`/`high` were not. `standards.py:1232` then evaluates `w.get("high", 0) <= MAX_HIGH_FINDINGS`
on the seeded 0, so "no high-severity findings open" HOLDS, and `panelWatch` prints "Nothing open -- every finding was
fixed or retired when its file changed" and "after 0 round(s)".

Failure scenario: dashboard poll (30 s TTL) lands inside overwatch's atomic replace of a ledger with HIGH findings ->
PermissionError -> `high=0` -> the standard reports green, the work order for the HIGH finding disappears from
the page, and `publish.snapshot()` (which calls `D.state()`) can publish that reading to the public page. Repro
(`r1.py`): torn file -> `open=0 high=0 rounds=0`; absent file -> identical; a real ledger with one HIGH ->
`open=1 high=1`.
Suggested fix: on any exception or a missing file set `out["unreadable"] = True` (and `high`/`open` to None), have
`standards` fail the row on None, and render "sweep ledger UNREADABLE" in `panelWatch`.

### F2. dashboard.py:646-665 with the JS at 998-1013 -- a failed halt read renders "running -- no halt standing" in the OK colour. LOW (reproduced the data half; the render half by reading the JS)

`safety()` seeds `out["halted"] = None` and the `except` only notes. `panelSafety` does `const h=sf.halted||{}` and
takes the else branch when `h.halted` is falsy: `'value ok','running -- no halt standing'`. The prose gate row
three lines below has an explicit `g.open===undefined?'unknown'`; the halt row, the one the file calls "THE HEADLINE",
has no unknown state. Repro (`r1.py`, `escalation.status` patched to raise): `safety()["halted"] is None`.
Reach is narrow because `escalation.status()` fails closed on an unreadable HALT.json and only raises on a defect,
and the panel is display-only. Suggested fix: `if(sf.halted===null||sf.halted===undefined)` -> a `value bad`
"halt state UNREADABLE" row.

### F3. cosmology_graph.py:206-243 -- `--write` has no halt interlock and no shrink guard, unlike its neighbours. LOW

Quote: `landed = silence.write_json(OUT, {"pairs": ...` (no `assert_clear`; module is absent from
`verify_math._INTERLOCKED`, which lists sevenfold, weave, weave_index, threads, etc.).
sevenfold.py:341-374 was interlocked under the 2026-09-28 ruling ("every hand-run tool that writes the corpus or the
library's output refuses while HALTED"). `data/SHARED_STAGE_GRAPH.json` is the same class of derived artifact, and it
is read live by `propagation.py` and `resonance.py`. The roster check only enumerates modules that already call
`assert_clear`, so an unlisted writer is invisible to it. Separately, the module rebuilds from
`WEAVE_CANDIDATES.json` and lands over the prior graph with no comparison, so a short candidates file (sweep67 b07
described the partial-load path in weave_index) lands a short graph over a complete one. Failure: a halted library,
a hand-run `cosmology_graph.py --write` proceeds and rewrites the artifact resonance reads. Suggested fix: the
same `_assert_not_halted` used in sevenfold on the `--write` path, and refuse when `len(ranked) < prior * floor`.

### F4. autostart.py:640-652 (`ensure`) and 619-637 (`start_watchdog`) -- the keeper one-shot can die with no trace. LOW (reproduced)

Quote: `p = start_watchdog()` -- not wrapped. `start_watchdog` catches only the first `OSError` (job breakaway) and the
fallback `Popen` is unguarded. The task runs `pythonw.exe`, so a raised exception has no console and there is no
`_log` line and no `silence.note`. Repro (`r3.py`, `Popen` raising): `ensure()` raises `FileNotFoundError` and
`autostart.log` gets zero lines. This is the one layer the file's own header says survives everything else dying, and
its own failure is the one it cannot report. `ensure()` already logs the "not started because unknown" case; the
"tried and could not" case is the one missing. Suggested fix: wrap `start_watchdog()` in `ensure()`, `_log` the
type and message, `silence.note`, and return an action word other than "start".

### F5. autostart.py:783-789 -- `--uninstall` removes only the Startup launcher; the scheduled keeper stays and restarts the watchdog (and through it the supervisor) every 10 minutes. LOW (by reading; `r3.py` confirms the uninstall branch never calls `uninstall_task()`)

`--install` installs both the .vbs and the task (801) but `--uninstall` and its help text ("remove it") remove one. An
operator who runs `--uninstall` to stop the automation sees the watchdog return within 10 minutes. The sanctioned way
to stop the machine is the pause marker, so this may be intended; the asymmetry is unstated. Suggested fix: either
call `uninstall_task()` from `--uninstall` or print "the watchdog keeper task still stands; run --uninstall-task".

### F6. gpu_lane.py -- three fail-open / accuracy gaps of the same family as the run #67 fixes. LOW (a, b, c reproduced in `r2.py`)

- a. gpu_lane.py:333, 349 `int(rec.get("depth") or 0)` in `foreground()`: a claim file for our own PID with a
  non-integer depth raises `ValueError` out of `with lane(priority=True)` (repro R3b), against the header "FAIL OPEN,
  ALWAYS". Same class as sweep67 b11 F6, fixed only in `_expired`.
- b. gpu_lane.py:742 `status()` does `float(rec.get("heartbeat") or 0)` inside the whole-listing `try`. One slot file
  with `heartbeat: "abc"` aborts the loop: the rows after it are dropped and `partial: True` is set (repro R3a: slots
  a, b(bad), c -> rows `['a']`). The flag is honest, but one bad file hides every later holder from the only view
  of who holds the card.
- c. gpu_lane.py:333 with `_claim_path()` named for the PID: `foreground()` reads and increments whatever depth is
  on disk without checking the record belongs to this incarnation. A claim left by a crashed process whose PID we now
  hold makes the depth 2, and the exit rewrites depth 1 instead of removing the file (repro R3c: one `fg.<pid>.json`
  remains after the lane exits, `foreground_active()` True for others until CLAIM_LEASE_SECONDS). Background jobs
  then yield up to 240 s to a claim nobody holds. Fix: ignore an on-disk claim whose heartbeat is older than the
  lease, or key on a process start time.
- d (observation). The 900 s slot deadline (662-664) and 240 s yield ceiling (655-657) both end in "go anyway" with
  no `silence.note`, so a round that ran unmetered because it timed out looks the same afterwards as one that
  waited its turn. The permission-denied and claim-write-denied exits do note. Same "degraded round must be
  distinguishable" argument the module makes at `_write_claim`.

### F7. publish.py:186-190 (`_is_skipped`) versus the `.gitignore` glob -- the copier's skip is narrower than the commit's. LOW (reproduced)

`_is_skipped("x.py.pre-sweep")`, `"x.py.pre_edit"`, `"x.pre.old"` are False (the regex `\.pre[a-z0-9]*$` needs the
suffix to be alnum to the end), as are `x.BAK` and `x.PYC` (`SKIP_SUFFIX` is case-sensitive). All of them are copied
into the export tree. `git add -A` does not commit them (`*.pre*`, `*.bak`; Windows git ignores case), so nothing
reaches the public repo, but `scan_for_secrets(SITE)` walks the filesystem (not the index) and will read them: a
backup carrying a fixture-less credential halts the library with SECRET_IN_EXPORT (an OWNER escalation) for a file that
was never going to be published. The docstring says the family is matched "by shape"; the shape it implements
is narrower than the sentence. Suggested fix: `_PRE_BACKUP = r"\.pre[^./\\]*$"` and lower-case the name before the suffix test.

### F8. dashboard.py:1207-1210 and 1235 -- stale comment about what the process writes. LOW (cosmetic)

"This process writes `state/failures.json` ... and `state/CODEWATCH.json` and nothing else anywhere." It also
writes `state/dashboard_history.json` on every `/api/state` request (`movement`, 520) and, through `ST.check`,
`state/read_progress.json` (standards.py:1123, 1889). The ruling's criterion ("writes outside output/ and state/")
still holds, so the exemption is right; the sentence a future reader will use to check it is wrong.

## Questions (owner's call; not filed as defects)

1. publish.py:722-728 / dashboard.py `panelStandards`: `standards_unavailable` is still written and read by nothing
   (carried from sweep67 b10 Q6). Wire it into the standards panel, or drop the key?
2. dashboard.py:242-266 `_read_row` / `_roll_row`: `_tail_match` returns the most recent matching line whatever its
   age, so a reader that died last week still renders a "corpus read" row with its old chunks and eta. The movement
   panel and the read-progress standard catch the stall, but the row itself carries no age. Want the log mtime shown?
3. sevenfold.py:376-393, 481: with `--write`, worlds from sources absent from the resonance graph (UNSHELVED) are
   printed on stderr and omitted from SEVENFOLD.json, and the exit code is still 0. Intended, or should a nonzero
   UNSHELVED fail the write (compare the drop the file's own comment describes)?
4. anchors.py:369 the monotone check is non-strict (`vals[n] < vals[prev]`), so two anchors that assay to the same
   value pass. With the current five readings that cannot happen; is "non-decreasing" the intended claim?
5. autostart.py:474-512 and 372-410: an unreadable halt (`halted is None`) still starts a supervisor and spends the
   hourly start budget (three refused starts exhaust it). Documented as one refused start; note that with a persistently
   failing halt read the budget empties inside the hour, which is the same "budget burned on refusals" the file's docstring
   says cost run #57 an hour. Accepted?

## Cleared (read in full, found correct; what I checked)

- **publish.py**: `_scrub` collision suffixing, per-line `scrub_text`, `_scan_units` block/carry/line_cap arithmetic
  (traced for lines spanning blocks and for over-cap lines), `scan_for_secrets` fail-closed UNSCANNABLE arm and
  suppressed-but-reported arm, `_unpushed` tuple precedence and the unborn-branch true zero, `_live_root_state` /
  `_live_file_state` gone-vs-unavailable, `prune_export` refusal-returns-None and dot-directory rule,
  `sync_tree` walk_errors hold, marker written before prune, root-file sweep, `push()` ordering (ledger guard, both
  mutation readings, scan, add, stranded-commit retry, rebase abort, push confirmation by `_unpushed`), `PushHeld`
  handling, `maintenance_shift_live` fail-open (documented), `_one_shot_push_verdict` three cases, `main()` halt re-ask
  per cycle and `break` with rc=1. Only F7 (and Q1).
- **dashboard.py**: `quotas` `worst=None` for no readable window, `throughput` read-only URI and absent-vs-unreadable,
  `_tail_match` hint ledger, `movement` (`hist[:-1]` baseline, reset-on-negative, numeric `at` guard, both display bounds),
  `safety` drill and escalation-log absent-vs-unreadable, `_watch` broken-modules fail-closed, server bound to
  127.0.0.1, codewatch loop, read-only start under a halt. Only F1, F2, F8.
- **autostart.py**: `_start_decision` ordering (unknown, running, halted, paused, budget, start), tri-state sensors and
  the `--status` precedence expressions, twin-check retry, VBS body quoting (traced the Chr(34) concatenation) and
  `installed_state` CRLF round trip, `task_state` content comparison, atomic install with temp cleanup. F4, F5, Q5.
- **gpu_lane.py**: `_slot_count`, `_alive` Windows path, the three-answer `_take_slot`, mtime fallback for unreadable
  slot files, `_touch` never resurrects, beat interval derived from the shortest lease, `lane()` ordering on release.
  F6 only.
- **anchors.py**: ran `run()` in-process, all 12 verdicts HELD, exit path carries `ok`; the printed-not-graded
  INSTRUMENT_WINDOWS question is still accurate. Q4 only.
- **sevenfold.py**: 400 random shelvings (depths 1, 2, 3, 5; weighted and unweighted, 1..120 members): every member
  placed once, children per parent <= 7 at every tier, 0 violations. Root-7 repro above. Q3 only.
- **cosmography.py**: chain arithmetic, `validate` ceilings, POCKET/MINOR now derive to 1.0e-8 and 1 galaxies (both admit),
  `kardashev_to_magnitude(1e-30)` returns `(None, 3.156e-23)`, RETAINED-no-caller markers still accurate. Nothing found.
- **cosmology_graph.py**: weight formula, uncapped `shared_sample`, complete pair list, gated write with rc 1, `_cut`
  markers; live build 5,782 pairs over 199 sources. F3 only.
- **catalog.py**: missing-catalog note, uncapped missing-source list, rc=1 on a miss. Nothing found.
