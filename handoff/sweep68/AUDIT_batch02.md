# sweep68 batch 02 -- AUDIT

## Scope

| module | lines | read |
|---|---|---|
| `src/verify_math.py` | 13,764 | all of it, lines 1-13,764, in 16 consecutive Read chunks |

Read-only for the project. `verify_math.py`, `drill.py`, `generate.py`, `publish.py`, `mutate.py` and every
pipeline phase were NOT run. No subagents. Scratch scripts live in `%TEMP%\aud68_02\` and only `ast.parse`
the source and `exec` the file's own pure scan functions (extracted by name, no `src/` module imported),
plus one 10-line standalone atexit demo. Scans run:

- `check()` rows whose `got` and `want` are the same expression, a self-comparison, or a constant pair:
  none except the deliberate always-FAILED rows at :12133/:12136 and the `tol` probe at :6649.
- float `want` rows where `tol` swamps a small `want`: none (80 `tol=` rows; `_discarded_tol20z` still
  returns `[]`).
- the file's own whole-tree scans against the live tree: prose-backed scan (exactly the two named
  exceptions; 44 needles examined; unresolved/declined lists match their pins), section tags (70, no
  duplicate), `tol=` rows (80, none discarded), the six `_RUN35_PINNED36` sha256 pins (all six match
  the bytes under `handoff/run35/` today), stale probe files (`state/_VM_*` absent).
- every `open(..., "w"/"a")` in the file: each path is under a `_mkdtemp_vm`/`mkdtemp` scratch, a
  redirected module constant, or (the two known probes) `state/`.

## Prior-audit cross-check (handoff/sweep67/AUDIT_batch02.md)

- **F1 (INFO, §18c temp-site count SEVEN vs nine): FIXED.** The paragraph now says NINE and names
  `_lane_root_vm` and `_synthetic_dir_b2`. I recounted the direct `mkdtemp/mktemp/TemporaryDirectory`
  sites outside `_mkdtemp_vm` (408, 4241, 5548, 8190, 9781, 9870, 9893, 10451, 11775): nine, each
  removed in a `finally`, an atexit hook or a `with`. Count is right.
- **F2 (INFO, "nine fixtures" note on the §20ad control): FIXED.** The note no longer carries a number.
- **F3 (INFO, eaten `__file__` in the batch5 header): FIXED** ("so `__file__` IS a file in src/").
- **Q1 (unguarded subscripts of a subject's output): STANDS, unchanged.** `_iv[...]`, `_wide[...]`,
  `_skew[...]`, `_iv_bad[...]`, `_iv_nog[...]` (:8778-8878), `_ev19ft[...]` (:5567), `_r[...]` (:1397),
  `_seq[i][...]`, `_v["decimal"]` still subscript a returned dict directly. A regressed subject that
  returns `None` raises at module level; the atexit net still prints RESULT and the run is red, but
  every later row is lost.
- **Q2 (spawn scan blind to `getoutput`/`getstatusoutput`/`os.spawn*`/`os.exec*`): STANDS, and now
  REPRODUCED** (finding 1 below).
- **Q3 (onomast doctrine-count rows use raw substring digits): STANDS, code unchanged** (:11178-11187).
- **Q4 (deliberately red "a sweep is owed" row beside the mutation baseline): STANDS, unchanged.**
- **Sweep66 Q3 (probe files written into live `state/`): STANDS.** `_VM_UNRECOGNISED_TEST.json`
  (:3060) and `_VM_ATOMIC_PROBE.json` (:6453) are still created in the live `state/`. Both are removed in
  a `finally`, which does not run on a SIGTERM, and §20a documents SIGTERM of jobs as routine. None is
  stranded now, and no other module reads either name (grep of `src/`).
- The file grew by 14 lines since sweep67. The change is the `PLmod.LOG` redirect at :1362 (run #68), which
  is correct: the fixed `%TEMP%\panscriptum_battery_pipeline.log` is shared with `drill.py:54` and is
  1,622 bytes today, so it does not grow without bound.

## Findings

### 1 -- MEDIUM -- the console-window scan accepts `creationflags=0`, `creationflags=None`, `startupinfo=None`

`verify_math.py:6114`: `if "creationflags" in _kw20e or "startupinfo" in _kw20e:` -> counted as guarded.
The scan reads the keyword's NAME and never its value, so the only enforcement of the owner's "no command
window may ever pop" directive (CLAUDE.md memory rule; §20e banner) passes a spawn that suppresses
nothing. Reproduction (ran the real `_spawn_scan20e` on fixtures):

    subprocess.run(['a'], creationflags=0)       -> guarded 1, unguarded []
    subprocess.run(['a'], creationflags=None)    -> guarded 1, unguarded []
    subprocess.getoutput('dir')                  -> guarded 0, unguarded [], osspawn []   (invisible)
    os.spawnl(os.P_NOWAIT, 'x', 'x')             -> invisible
    subprocess.run(['a'], **kw)                  -> unguarded ['f.py:2']   (fails closed, fine)

Scenario: a maintainer adds `subprocess.run(cmd, creationflags=0)` (or a flag variable that is 0 off the
`os.name == "nt"` branch, the exact shape of `autostart.py:288-294`, `:621-637`, `mutate.py:2909`), the
row stays green, and a console window opens several times an hour. Live tree today: I read every
`creationflags=` in `src/` (grep, 55 sites); all pass `_NO_WIN`, `getattr(subprocess, "CREATE_NO_WINDOW",
0)` or a flag built from it, so nothing is broken now. The fixture at :6833 (`creationflags=0x08000000`)
is a control for the flag being read but there is no control for a zero value. Fix: require the keyword's
value not to be the literal `0`/`None`, and add `getoutput`, `getstatusoutput`, `os.spawn*`, `os.exec*`
to the two sets.

### 2 -- LOW -- the crash net's "still exits non-zero" claim is false for `SystemExit(0)` / `sys.exit()`

`verify_math.py:121-122`: "the process still exits non-zero, because Python's own exit code for an
uncaught exception is 1". True for exceptions that reach `sys.excepthook`; not for `SystemExit` with code
0 or None, which does not call the hook and exits 0. The atexit hook (:149-159) then files the FAILED row
and prints `RESULT: N passed, 1 FAILED`, but the exit code stays 0. Reproduction (`repro2.py`, same
atexit shape, `sys.exit(0)` before the last line): prints `RESULT: 0 passed, 1 FAILED`, `rc=0`.
`allsweep` grades "the numbers" (`allsweep.py:255`) by return code, so that run reads green. Scenario: a
subject `main()` driven by a row (`reference.main`, `onomast.main`, `rosetta.main`, `worldseed.main`,
`publish.main`) later grows a `sys.exit()` path, or an argparse `--help`, and the battery ends rc=0 with
a FAILED tally. Not reachable today (I read each driven `main()` call site: each sets `sys.argv` and gets
a return code). The ended-early row is also not `mutate`-safe only because mutate compares the whole
`rc|RESULT` signature. Fix: have the atexit hook `os._exit(1)` when it files the row, or set the code via
`sys.exit` handling in the hook.

### 3 -- LOW -- two safety scans are blind to spellings a real edit could use

Both reproduced against the real functions (`repro1.py`).

- `_writes_the_config20p` (:8008-8057, "the drill never opens the owner's config for writing") only sees
  `open(path, "<mode>")` with a positional mode. `open(p, mode='w')`, `Path(...).write_text(...)`,
  `silence.write_json(<config path>, ...)` and `os.replace(tmp, <config path>)` all return `[]`. The past
  incident this guards (`drill._gates_agree` leaving `prose_enabled` open on disk) would not be caught if
  rewritten in any of those. Mitigation: `drill.py` carries its own `_write_targets` scan that does cover
  `write_text`/`shutil.copy`/`os.replace` (`drill.py:1704-1736`), so this is a thinner second layer, not
  the only one.
- `_clear_callers20t` (:8380-8419, "escalation.clear() has no caller anywhere in src/") resolves the module
  only from `import escalation [as X]`. `E = __import__("escalation"); E.clear()`,
  `importlib.import_module("escalation").clear()` and `sys.modules["escalation"].clear()` all return
  `[]`; this file itself uses the `__import__("escalation")` spelling at :8171. Mitigation: `clear()` also
  refuses at run time unless `__main__` is `escalation.py` and the caller is its `main()`
  (`escalation.py:1297-1348`), so CLAUDE.md's guarantee holds; the static half is weaker than its
  comment implies.

### 4 -- LOW -- three "real population" floors carry 14-20 rows of headroom, and one comment about it is stale

Measured today against the pins: section tags 70 vs floor `>= 55` (:12592); `tol=` rows 80 vs `>= 60`
(:12832); prose-backed needles examined 44 vs `>= 30` (:13042). The tag row's note says the floor "is
deliberately seven below" the count of 62 recorded on 2026-08-29; the count is now 70, so the floor is
fifteen below, and 15 section headers could go unseen while the uniqueness check still reads clean. This
is the class the file already retired at two sibling sites (§20e `>= 20`, standards `>= 40`) in favour of
reconciling against a declared set. Same for `len(_seen20ae) >= 50`. Fix: reconcile against an independent
count (or pin the exact number and let a legitimate change move it on purpose).

### 5 -- LOW -- one raw-source row counts occurrences and is outside the prose-backed scan

`verify_math.py:5099`: `_fm20a.count("os.kill(") >= 3` reads raw `foreman.py`. The prose-backed scan
(§20z) examines only `"needle" in <raw>` membership tests, so a comment or docstring mentioning
`os.kill(` three times would satisfy it after the real calls were removed. Today `foreman.py` has exactly
three, all code (`foreman.py:676`, `:854`, `:953`) and none in prose, so it is not wrong now.

### 6 -- LOW -- the PASS/FAIL swap in the `check()` self-probe is not exception-safe

`verify_math.py:6644-6656`: the probe copies `PASS`/`FAIL`, calls `.clear()` on both, runs
`check("probe...", None, 1.0)` inside `try/except TypeError`, then restores. Any other exception from
`check()` propagates out with both lists already cleared, so the earlier FAILED rows are dropped from the
RESULT dump that the atexit net prints. The run is still red (the crash row is filed), so this loses
evidence, not the verdict. A `finally` would close it. Not reachable today (`check()` is total for a
`None` got).

### 7 -- INFO -- §19t leaves `read` module state at hard-coded values instead of the saved ones

`verify_math.py:3909` sets `_RD._GPU_DOWN_UNTIL[0] = 0` and never restores it; `:3922` resets
`_RD._GATE_STATE` to `{"at": 0.0, "regime": "cloud"}` rather than to whatever it held. Both equal the
import-time defaults (`read.py:339`), and the next section that touches `_GPU_DOWN_UNTIL` (§b5, :11091)
saves and restores it itself, so nothing downstream can observe it. Noted because every other override in
this file restores from a saved value.

## Questions (possibly deliberate)

- **Q1 (carried, sweep66/67):** is the unguarded-subscript rule meant to cover every subscript of a
  subject's output? If so it is a class-wide sweep (the sites listed under the prior-audit cross-check).
- **Q2:** `PR.build_all(limit=400)` (:1854) and `BG.burgs_for(..., limit=200)` (:2157) sample a roster in
  test code. They are labelled samples and do not touch a library output, so I read them as outside Hard
  Rule 0 -- confirm that a labelled test sample of a ranked listing is acceptable.
- **Q3 (carried):** the two `state/_VM_*` probes. Moving them under a scratch directory (both paths are
  module attributes the probe already redirects, `_CB.UNRECOGNISED` and the `write_json` argument) would
  remove the last live-state writes from the battery; is the point that they exercise the real directory?

## Cleared (looked at closely, found correct)

- The hermetic transport (:244-450): class-level `socket.socket.connect`/`connect_ex` tripwire, canned
  `/api/tags` and `/api/ps`, the far-future token-flow pin and its restore, and the closing control that
  proves the stand-ins are still installed. `_gpu_port_of_vm` handles IPv6 4-tuples.
- Every other module-level override is restored from a `finally` with a restore-verifying row:
  completeness (`HOSTS`, `RECORDS`, `category_size_probe`, `host_reachable`, `OUT`), `gpu_lane.LANE` and
  `_BEAT_SECONDS`, `tuning`, `standards` (`MIN_CALLS_TO_JUDGE_RATE`, `_TOKENFLOW`, `check`, `HERE`),
  `assay.BAND_EDGES`/`SIGMA_BY_ATTESTATION`/`INSTRUMENT_WINDOWS`/`_RHO_CACHE`/`assay.assay`, `publish`
  stubs (seven names) and `escalation.HALT_FILE`, `overnight.STANDING`/`_proc_lines`, `feats`
  (`CACHE`, `discover`, `fetch`, `api`), `magnitude` (six names), `read`/`onomast`/`pipeline`/`reference`
  attributes, `builtins.open` at §b3 and §b5, `silence.note`/`replace_retry`, `sys.argv`.
- §20p `_publish_rc20p`: `escalation.HALT_FILE` is redirected before `main()` runs and `assert_clear`
  reads only that file (`escalation.py:1278-1294`), so the halt-independence claim holds; every stubbed
  publish step is restored.
- §20ab: `phase_cosmology` and `phase_write` build every output path from `HERE` at call time, so the
  `_PLab.HERE` redirect covers `GROUNDINGS/TIERS/CENSUS/SHELFMARKS/manifest.json`; `T.chart` only READS
  the live `GROUNDINGS.json`. Nothing is written outside the scratch tree.
- §20ac: `onomast.main()` writes only `OUT` (redirected) and reads `RESOLVED` (redirected).
- `check()` itself: non-numeric `got` against a float `want` is a failed row; NaN and inf `got` fail
  closed; the relative tolerance uses `max(1.0, abs(want))`, so no float `want` in the file has a `tol`
  wider than its own value (scanned).
- The `_admit36` name-and-digest gate refuses tampered, gone and unpinned files; the six digests match.

## Coverage note

Read in full, and only: `src/verify_math.py`, lines 1-13,764.
