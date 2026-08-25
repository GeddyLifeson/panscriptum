# BATCH 11 AUDIT — run26

Modules (read in full, line by line): `src/overnight.py` (767 lines), `src/zfighters.py` (486
lines), `src/health.py` (404 lines), `src/entity_match.py` (279 lines), `src/anchors.py` (233
lines), `src/audit.py` (178 lines), `src/compress_store.py` (66 lines). Total ~2,413 lines.

Two findings below (zfighters.py --full crash, anchors.py invariant failure) were **confirmed
by actually running the scripts**, not inferred from reading. Numbers cited under health.py's
special focus were cross-checked against the live `state/failures.json`.

---

## MAJOR

### M1. `zfighters.py:474` — `--full` crashes with `KeyError: 'provenance'` on Son Goku

Confirmed live:

```
$ python src/zfighters.py --full
...
Son Goku   𝔄 M7.53 ± 0.06   (Mastered Ultra Instinct, Tournament of Power)
Traceback (most recent call last):
  File "...\zfighters.py", line 485, in <module>
    sys.exit(main())
  File "...\zfighters.py", line 474, in main
    % (ax, d["score"], d["provenance"], d["cited"][:60]))
KeyError: 'provenance'
```

`main()` (lines 434-441) merges `data/REFERENCE_ASSAYS_PRESENCE.json`'s `"Son Goku"` record
into `out` so the roster ranks whole. Every hand-authored `ROSTER` entry's `axes` dict has a
3-tuple `(score, evidence, provenance)`, and `compute()` (line 412) turns that into
`{"score":…, "cited":…, "provenance":…}`. But Son Goku's axes in
`REFERENCE_ASSAYS_PRESENCE.json` only carry `{"score":…, "cited":…}` — no `provenance` key
(verified directly against the JSON file). The default (non-`--full`) path never touches that
field and runs clean; `--full`'s per-axis print loop (line 471-474) unconditionally indexes
`d["provenance"]` and crashes on the one entity that was merged in from outside `ROSTER`.

### M2. `zfighters.py:24-29` — the module's own headline claim is false against its own computed output

The docstring states, as the one result worth stating before anyone reads the table:

> "ANDROID 17 ANCHORS AT M7, above Vegeta and every Earth-raised fighter except Goku."

Running the script (default mode) produces:

```
Vegito       M7.63
Android 17   M7.60
Gogeta       M7.60
Vegeta       M7.53
Son Goku     M7.53
```

Goku ties Vegeta at the *bottom* of the M7 band, strictly below Android 17 — the opposite of
"except Goku" (which implies Goku is the one fighter who *does* rank above Android 17). Either
the axis scores drifted since this paragraph was written, or the paragraph was never checked
against a live run. This is the "comments/docstrings contradicting their code" lens item,
applied to the file's own thesis statement rather than an inline comment.

### M3. `anchors.py` — the file's one invariant currently reads False, and nothing surfaces that

Confirmed live:

```
$ python src/anchors.py
...
  monotone floor -> ceiling : False
     The Skate Guy                  0.22
     A Sword                        0.10
     Yggdrasil                      6.18
     Goku                           5.42
     The Seat of the Creator       10.99
```

Two breaks: A Sword (0.10) scores *below* The Skate Guy (0.22), and Yggdrasil (6.18) scores
*above* Goku (5.42). Per the module's own docstring this is exactly the class of defect
anchoring exists to catch ("Anything that reads absurdly here is a defect in the instrument,
however clean its unit tests were") — a real, actionable finding about `assay.py`/`physics.py`
scoring, worth flagging to the owner on its own merits.

But separately, this is a code bug in *this* file: `run()` computes `ok` and only ever
`print()`s it (line 225); the `__main__` guard is bare `run()` with no `sys.exit(...)`, and
`run()` returns `rows`, not an int. The process always exits 0, whether the invariant holds or
not. Nothing that calls this script automatically (a CI-style checker, `overnight.py`'s
preflight, a human skimming a log tail) can tell "False" apart from "True" without reading the
text — the exact "plausible negative result" shape this whole codebase's `silence.py` campaign
exists to eliminate, reproduced in the one module whose entire job is finding it elsewhere.
Contrast with `audit.py`, which gets this right (`return 1 if fails else 0`, confirmed below).

### M4. `overnight.py:145` — `running()`'s fallback clause reopens the false-positive bug its neighbour was fixed for

```python
if fragment in cmd.replace("\\", "/").split("/")[-1] or fragment in cmd:
    return True
```

`run()`'s own docstring (lines 163-166) explains that matching had to move to the BASENAME
specifically because a plain substring test against the full command line let one job's
command line that merely *mentioned* another stage's filename count as that stage running.
That basename fix is the first clause here, and by itself it is sufficient in every case
checked (a fragment like `"read.py"` always survives inside
`cmd.replace("\\","/").split("/")[-1]`, which captures the script name plus every trailing
CLI argument). The second clause, `or fragment in cmd`, is a plain whole-command-line substring
test with no basename anchoring at all — it reopens precisely the bug class the first clause
exists to close. In the current job set the risk is low (script names are specific and rarely
appear as literal substrings of unrelated argv), but it is live: any future job whose command
line references another stage's filename as data (a log path, a `--target`, a diagnostic
argument) would make `running()` report a false "already running," and `run()`/`start()` would
silently skip launching or restarting a job that should have started. This is the same failure
shape (a guard matching more than the one spelling of the thing it's supposed to detect) called
out in the audit lens as a KEY SHAPE risk.

---

## MINOR

### N1. `overnight.py` — five `silence.note()` calls carry stale line-number labels

| call site (current line) | label | actual owning line |
|---|---|---|
| `coverage_snapshot()` line 468 | `"overnight.py:124"` | 468 |
| `preflight()` line 486 | `"overnight.py:141"` | 486 |
| `foreman_report()` line 283 | `"overnight.py:203"` | 283 |
| `watch_report()` line 325 | `"overnight.py:229"` | 325 |
| `ledger_report()` line 350 | `"overnight.py:253"` | 350 |

These labels were presumably accurate once; the file has since grown/moved around them and
nobody updated the strings. Since `state/failures.json` keys on this exact string
(`silent:overnight.py:124:...` etc.), anyone chasing a ledger entry back to source lands on the
wrong code. Low severity (only affects diagnosability, not behaviour), but it directly
undercuts the one thing these labels exist for.

### N2. `overnight.py:71-74` — lazy `_PROCS_LOCK` init has a real (if low-impact) TOCTOU race

```python
global _PROCS_LOCK
if _PROCS_LOCK is None:
    import threading
    _PROCS_LOCK = threading.Lock()
with _PROCS_LOCK:
    ...
```

Three threads call into `_proc_lines()` concurrently in this process (main loop, the `_keep`
keeper thread, and indirectly anything that calls `running()`). If two of them race this
check before either assignment lands, each creates and locks its own separate `Lock()` object,
briefly defeating the mutual exclusion the lock exists to provide. Consequence today is mild
(worst case, two near-simultaneous PowerShell/WMI process enumerations instead of one — not a
correctness break, just wasted work), but it is a genuine unguarded double-checked-locking
pattern, worth a plain module-level `threading.Lock()` instead of the lazy version.

### N3. `overnight.py` — `pipeline`'s "runs after the reader" ordering isn't actually guaranteed

`pipeline.py` is `start()`ed in the background at the top of every cycle (line 683, alongside
dashboard/publish/foreman/overwatch), then invoked again via blocking `run()` after `read.py`
and the roll finish (line 711), with the comment: "Runs after the reader so it sees the
evidence the reader just produced." But `run()` at line 711 first calls the same
`running(os.path.basename(args[0]))` singleton guard as everywhere else — if the
cycle-start `pipeline.py` instance from line 683 is still alive when the reader finishes
(plausible if `read.py` finishes quickly, or pipeline runs long), `run()` reports
"already-running" and returns without launching a fresh pass, so the pipeline invocation that
actually processed the reader's fresh output is the one that started *before* the reader did.
In practice this likely self-corrects across cycles (pipeline being a single-pass, non-`--loop`
job), but the comment's stated guarantee does not hold within a single cycle whenever the
background instance outlives the reader.

---

## QUESTIONS (health.py special focus — probe/unexpected counting)

Confirmed the task's cited numbers (449 unexpected + 3,935 probe = 4,384) match the live
`state/failures.json` exactly: summing every key containing `endpoint.py:detect`,
`endpoint.py:fetch`, `hostcheck.py:probe`, `hostcheck.py:candidates`, `hostcheck.py:relevance`,
or `scout.py:verify` gives 3,935 (450 + 450 + 2,979 + 56); everything else sums to 449. So
today's arithmetic is right. Two structural concerns, both outside my assigned files but
directly bearing on how to read health.py's ledger:

### Q1. The probe/unexpected split lives entirely in `standards.py`, not in `health.py`, and is a coarse site-name substring match, not an exception-type check

`health.py`'s `LEDGER`/`record()`/`flush()` store every failure with no notion of "probe" vs
"real" — that classification is computed downstream, in `standards.py`
(`any(t in k for t in (...))` against six hardcoded literal strings). Because the match is on
the *site label* (module:function) and not on the *exception type*, any new `except` clause
added later inside `endpoint.detect()`/`endpoint.fetch()`/`hostcheck.probe()` for a genuine
internal defect (not a probing 404/timeout) would be silently swept into "probe" and excluded
from the "unexpected swallowed failures" standard — nothing in `health.py` (or this batch)
would notice the misclassification, since the ledger itself carries no probe/real flag to
check against. Worth a second pair of eyes on `standards.py` specifically for whether every
current key under those six prefixes is genuinely probe-shaped (HTTPError from an intentional
multi-path detection attempt) rather than something else that happens to share the module name.

### Q2. Archiving resets the live ledger every foreman round, which can flatten a genuinely growing fault

`foreman.triage_swallowed()` (not in this batch, but load-bearing for `health.py`'s numbers)
archives `state/failures.json` into `state/failures_archive.json` and then clears the live file
to `{}`. `overnight.py`'s own `STANDING` set runs foreman on a `--loop 30` cadence. Since
`standards.py`'s "unexpected swallowed failures" check reads only the *live* (post-clear)
ledger, a fault with a steady background rate that never exceeds `MAX_SWALLOWED_NEW` within a
single ~30-minute window will never trip the standard, no matter how many windows in a row it
repeats — the total across the full run could be large while every individual check sees a
small number. The full history is preserved in `failures_archive.json`, but nothing in this
batch's files (nor, as far as I can tell without reading `standards.py`/`foreman.py` in full)
reads the archive back for a trend/rate check. Confirmed the *counting itself* (sum, dedup) is
correct within a window; the concern is purely about the reset cadence hiding a slow-growing
class.

### Q3. `health.py:241` `check_caches()` samples the first 200 files by `glob.glob` order, not a random sample

```python
for fp in files[:200]:
    ...
n = min(len(files), 200)
if empty == n:
    out.append((f"{base}/{host}", f"all {n} sampled entries empty"))
```

Explicitly documented as a deliberate size-not-parse performance tradeoff (a full parse of
every cached page across 147 hosts pushed preflight past 5 minutes), and the output string does
say "sampled" rather than implying exhaustiveness, so this doesn't violate Hard Rule 0's
disclosure requirement. But `glob.glob()`'s order is filesystem-dependent, not randomised or
guaranteed sorted — if a host's earliest-written 200 cache files happen to all be empty (e.g.
from an aborted early run) while thousands of later ones are populated, this check would
false-positive "cache empty" for a host that is actually fine, or the mirror case could mask a
genuinely broken host whose first 200 files happen to be non-empty stragglers. Flagging per the
Hard-Rule-0 instruction to report every `[:N]`; my read is this is a **legitimate bound** for a
cheap diagnostic heuristic (not a data-producing cap — nothing about the catalogue itself is
truncated), with the caveat that the "first 200" isn't actually a statistically representative
sample.

---

## Hard Rule 0 sweep (every `[:N]` / `limit` / `top` / `MAX_*` found in these 7 files)

All instances found and classified. **No violations of Hard Rule 0 found** — every cap here
either (a) truncates a human-readable log/console string, not catalogue data, (b) is an
explicitly-disclosed, non-authoritative sample (audit.py's `--sample`, the "and N more" pattern
in its invariant printer, health.py's `check_caches` sample), or (c) is `entity_match.py`'s
`candidates(limit=None)`, which correctly implements Hard Rule 0's own disclosure contract:

- `entity_match.py:174-239` — `candidates(name, pool, limit=None)`. Default is `None` (no cap).
  When a caller does pass a limit, the function sets `truncated=True` in its return so a
  truncated result can never be silently mistaken for the full set. **This is the correct
  pattern** and worth naming as a positive example, since the rest of this report is mostly
  problems.
- `overnight.py` — `watch_report(top=6)` / `ledger_report(top=8)` slice printed summaries of
  `OVERWATCH.json` / `failures.json` for the supervisor's own log; full data persists in those
  source files untouched. `write_status()`'s `history[-12:]` likewise only bounds the STATUS.md
  "recent cycles" table, not the underlying run history. All log/display truncation, not data
  loss. `IDLE_LIMIT`/`MIN_CYCLE_SECONDS`/`WAIT_SECONDS`/timeout_h are operational governors
  (halt/backoff thresholds), not data caps.
- `health.py:81` — `SAMPLES_KEEP = 3` bounds the *example* ring per failure class, explicitly
  separate from the *count* (`LEDGER`, uncapped). `health.py:327` — `reopen[:20]` bounds only
  the console preview of stranded batch keys in `reopen_stranded()`; the actual repair
  (`st["done"]["entrypass"] = [k for k in done if k not in set(reopen)]`) operates on the full,
  unsliced `reopen` list — every stranded batch is genuinely reopened. `health.py:241` —
  covered as Q3 above.
- `audit.py` — `args.sample` (default 14) and the banded-sample draw (`min(10, len(banded))`)
  are explicitly, by the module's own docstring, a *human-reading* pass distinct from the
  exhaustive `audit_invariants()` pass that runs over every entry with no cap. `for x in v[:4]`
  in the invariants printer discloses the remainder ("... and N more") rather than hiding it.
  All string-truncation for terminal display (`[:60]`, `[:150]`, etc.) is display-only.
- `zfighters.py` — `ROSTER` is a fixed, hand-curated set of 15 fighters by explicit design (the
  module's whole reason for existing, per its docstring, is that these 15 need hand-built
  epoch-fixed sheets instead of the mined pipeline); not a truncation of a larger available set.
- `compress_store.py:21` — `hexdigest()[:32]` truncates a SHA-256 digest to 128 bits for use as
  a content-addressed filename. Not a Hard-Rule-0 data cap (it's a hash, not a listing), and at
  this project's realistic scale (tens of thousands of chapters, nowhere near the ~2^64
  birthday-bound collision risk for 128 bits) this is a non-issue in practice — noted only for
  completeness.

---

## SPECIAL FOCUS — overnight.py supervisor mechanics (confirmed against source)

**STANDING set** (lines 372-380), exactly 5 jobs the keeper restarts:
`dashboard.py --port 8777`, `publish.py --push --loop 10`, `foreman.py --go --patch --loop 30`,
`overwatch.py --loop 20 --modules 4`, `pipeline.py` (no `--loop`, single-pass).

**Confirmed excluded from STANDING**: `read.py` and `feats.py --roll` — both present in
`ALL_JOBS` (line 387-389, "the keeper's STANDING set is the subset it can restart on its own")
but absent from `STANDING` itself. This is exactly the M15 mechanism described in the task: a
foreman remedy that SIGTERMs `read.py` mid-cycle leaves it dead until the *next* pass through
the blocking `run("read", ...)` call at line 704, which only happens once per lap.

**Keeper interval**: `_keep()` (line 556-569) does `time.sleep(300)` then checks/restarts each
STANDING job — confirmed 300s = 5 minutes, matching the docstring's own claim ("re-asserts the
standing jobs every five minutes").

**Worst-case downtime for a mid-lap `read.py` kill**: after the SIGTERM, `run("read", ...)`
(line 704) returns immediately with the nonzero rc; control falls through to `join(roll,
timeout_h=4)` (up to 4h if the roll is still running), then `run("pipeline", ..., timeout_h=2)`
(up to 2h), then `foreman_report()`/`watch_report()`/`ledger_report()` (fast), then
`coverage_snapshot()` (subprocess timeout 1800s = 30 min), then a possible idle sleep (up to
`WAIT_SECONDS`=600s), then the *next* cycle's `preflight()` (subprocess timeout 1800s = 30 min)
before `run("read", ...)` is reached again. The empirically-measured 42-minute figure in the
task is consistent with this chain when roll/pipeline finish quickly; the mechanism is
structurally unbounded in the worst case (bounded only by the 4h/2h/30min/30min timeouts
stacked together), not a fixed 42 minutes.

**`name_rc()` (lines 392-436)**: verified the unsigned→signed 32-bit conversion
(`signed = rc - (1 << 32) if rc >= (1 << 31) else rc`) is arithmetically correct for Windows'
unsigned `DWORD` exit codes (e.g. `4294967295` → `-1`, matching the cited real log example).
Checked the four hardcoded NTSTATUS constants against their standard values —
`STATUS_CONTROL_C_EXIT` (0xC000013A), `STATUS_ACCESS_VIOLATION` (0xC0000005),
`STATUS_STACK_BUFFER_OVERRUN` (0xC0000409), `STATUS_STACK_OVERFLOW` (0xC00000FD) — all correct.
`1` (ordinary Python error exit / `Popen.kill()`'s default `TerminateProcess(handle, 1)` on
Windows) and `0` are correct. No mapping errors found in this table.

---

## SPECIAL FOCUS — audit.py: can its checks actually fail?

Yes, confirmed live (`python src/audit.py --sample 3`): the invariants pass currently reports
**334 real violations** across 69,644 catalogued entries — wiki-navigation artefacts
mis-catalogued as entities (177), empty descriptions (66), too-short descriptions (58), and
ceiling entities not present among their own source's entries (33) — and correctly propagates
failure via `return 1 if fails else 0` (line 173). These are not vacuous/tautological checks;
each one is independently falsifiable against real data and several are currently tripping.
Worth flagging as a positive contrast to anchors.py (M3 above), which computes an equivalent
invariant but never surfaces its failure through the exit code.

---

## Files touched by this audit (read only, no edits made)

- `C:\Users\imarl\panscriptum-library-kit\src\overnight.py`
- `C:\Users\imarl\panscriptum-library-kit\src\zfighters.py`
- `C:\Users\imarl\panscriptum-library-kit\src\health.py`
- `C:\Users\imarl\panscriptum-library-kit\src\entity_match.py`
- `C:\Users\imarl\panscriptum-library-kit\src\anchors.py`
- `C:\Users\imarl\panscriptum-library-kit\src\audit.py`
- `C:\Users\imarl\panscriptum-library-kit\src\compress_store.py`

Cross-referenced (not audited in full, consulted only to answer the special-focus questions):
`src/silence.py`, `src/standards.py` (lines ~500-560), `src/foreman.py` (`triage_swallowed`,
lines 214-283), `src/feats.py` (`api()`, lines ~119-172), `data/failures.json`,
`data/REFERENCE_ASSAYS_PRESENCE.json`.
