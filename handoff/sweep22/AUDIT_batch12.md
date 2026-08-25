# Batch 12 audit — overnight.py, zfighters.py, silence.py, cosmography.py, wh40k.py, descending_ladder.py, sweep_plan.py

Every line of every file in this batch was read top to bottom. Findings below are grouped by
severity, then by file. Every claim marked VERIFIED was confirmed by direct code reading and, where
useful, by actually running the code (`C:/Users/imarl/miniconda3/python.exe`) against this tree.
Nothing in this batch was edited.

---

## SCOPE NOTE FOR M15 (read this first)

The brief asked for a close audit of overnight.py's stall-detection and kill path, and "exactly
what evidence it uses to decide a job is stalled."

**overnight.py contains no stall-detection logic at all.** Its only two kill paths are pure
wall-clock timeouts:

- `run()` / `join()`: `subprocess.Popen(...).wait(timeout=timeout_h*3600)` → on
  `TimeoutExpired`, `p.kill()`. Caps used this cycle: `run(read, ...)` = `a.read_hours`
  (default **3.0h**), `join(roll, ...)` = **4h**, `run(pipeline, ...)` = **2h**, default for an
  unspecified `run()` call = **6h**.

There is no heartbeat check, no output-freshness check, no progress counter anywhere in this
file — a "stalled" job and a "legitimately slow" job are indistinguishable to overnight.py, and
it never tries to distinguish them. It only enforces a hard ceiling on total wall-clock time.

The `kill_stalled_job` remedy quoted in the docstring at `overnight.py:295` — `"[22:39:04]
... kill_stalled_job: killed stalled read_auto:42972"` — is **not overnight.py's own action**. It
is a line replayed *verbatim* from `data/FOREMAN.json` by `foreman_report()`
(`overnight.py:272-310`); the decision to call something "stalled" and the kill itself both
happen inside **foreman.py**, which is outside this batch.

Corroborating evidence that the reported downtimes (1, 8, 19.9, 32, 37, 37.6, 42, 44 min, and
once 4h) are not overnight.py's own timeouts: none of the short downtimes match any constant in
this file (3h/4h/2h/6h), and read.py's own cap (`a.read_hours`, default 180 min) doesn't match
any of them either. The "once 4 hours" figure is suspiciously close to `join(roll, timeout_h=4)`
(`overnight.py:660`) — worth checking whether that one incident was actually the *roll* stage's
own timeout misattributed to the reader, rather than a foreman stall-kill of read.py. UNVERIFIED —
flagging for the investigator, not asserting it.

**Recommendation:** point the M15 investigation at `foreman.py` (not in this batch) for the actual
stall heuristic and kill call.

---

## HIGH — correctness / swallowed-failure / concurrency

### 1. `silence.py:346-348` — `instrument()`'s keyword list doesn't recognize this project's own exemption idiom, and has already caused a documented incident

```python
346:            if any(t in ast.dump(node) for t in ("health", "record", "log", "print",
347:                                                 "raise", "swallow", "note", "LEDGER")):
348:                continue
```

Compare with `_handlers()` (used by `audit()`), a few dozen lines earlier:

```python
128:        records = any(t in body for t in ("health", "record", "log", "print", "raise",
129:                                          "swallow", "silence", "LEDGER"))
```

`_handlers()`'s list includes `"silence"`; `instrument()`'s list does not (it has `"note"`
instead). Across this codebase there is a deliberate, widely-used idiom for marking a handler as
reviewed-and-intentionally-unrecorded:

```python
except Exception:
    _ = "silence-exempt: no cache yet is the normal first state"
```

(seen verbatim in `chain.py:139`, `completeness.py:76`, `coverage.py:62`, `feats.py:746`,
`gpu_lane.py:375/378`, `handbuilt.py:464`, `local_agent.py:286`, `sweep.py:85`,
`weave_index.py:176`, `standards.py:194`, and inside `overnight.py:140`/`read.py:620` — all in
this tree). `_handlers()` correctly treats these as "observed" (the `"silence"` keyword matches
the string). **`instrument()` does not** — its site-selection list has no `"silence"` entry, so
it does not recognize `"silence-exempt: ..."` as anything other than a plain assignment, and will
happily insert a `silence.note(...)` call into a handler a human deliberately marked exempt.

This is not hypothetical. `overnight.py:135-137` documents exactly this happening, twice:

> "Noting it filed 35,806 ledger entries in two hours and buried every real failure class under
> a probe artefact -- TWICE, because `silence.py --instrument` re-added the note the evening
> sweep removed."

**This is the single clearest instance in this batch of "silence.py suppresses (here: pollutes
and buries) the very faults it exists to expose."**

VERIFIED (cross-referenced against overnight.py's own account of the incident and confirmed the
keyword-list mismatch directly).

**Suggested repair:** add `"silence"` to `instrument()`'s skip-keyword list at line 346-347 so it
matches `_handlers()`'s list exactly (or better: factor both lists into one shared constant so
they can never drift apart again).

---

### 2. `silence.py:133` — `uses_exc` is a broken substring check; it currently provides zero real protection for named exception handlers

```python
133:        uses_exc = bool(node.name) and node.name in body
```

`body` here is `ast.dump(node)` for the **whole** `ExceptHandler` node, whose own dump text
already contains `name='<the name>'` as a structural field — plus the words `Exception`, `Name`,
`Load`, `Store`, etc. For any short/common exception-binding name (this codebase's overwhelming
convention: `except ... as e:`), the letter is essentially guaranteed to appear somewhere in the
dump **regardless of whether the exception variable is ever referenced in the handler body**.

Direct repro:

```python
>>> ast.dump(ExceptHandler for "except Exception as e: pass")
"ExceptHandler(type=Name(id='Exception', ctx=Load()), name='e', body=[Pass()])"
>>> "e" in that string
True
```

So `except Exception as e: pass` — the textbook silent swallow this file's own docstring opens
by naming as the project's core defect — is classified `silent: False` (i.e. "observed") purely
because the letter "e" is a substring of "Exception". `records` is also `False` here (no
logging keyword present), so the *only* thing saving this handler from being flagged is the
coincidental letter match, not any real inspection of whether `e` is used.

This codebase has 86 handlers using the `as e:` pattern (`grep -c "except.* as e:"`). None of
them currently exploit this hole — I checked every one programmatically (walking each handler's
*actual* body for a genuine `Name` reference to the bound exception, or a genuine logging/raise
call) and found zero cases where the real answer disagrees with the tool's answer today. But that
is because every existing handler *also* independently logs, records, re-raises, or carries the
"silence-exempt" string — not because `uses_exc` is doing any work. The check is a coincidental
tautology, not a safety net. Given `foreman.py --patch` (per `overnight.py:617-621`) autonomously
patches source files unattended, a future auto-generated `except Exception as e: pass` (or any
handler using a short exception name with no other observation) would sail through `audit()`
undetected, exactly the class of fault this file exists to catch.

VERIFIED (repro'd the substring collision directly; swept the whole `src/` tree to confirm no
*currently existing* case is silently mis-scored by this specific mechanism, distinguishing it
from the `"records"` false positives below, which are all the intentional exemption idiom).

**Suggested repair:** don't test name-as-substring-of-dump; walk `node.body` for a genuine
`ast.Name` reference to `node.name`, the way a real "is the exception used" check should.

---

### 3. `overnight.py` — `pipeline.py` is simultaneously a STANDING (always-on) service and a bounded per-cycle job; once the keeper has claimed it, the deliberately-ordered "run after the reader" invocation silently becomes a no-op

`pipeline.py` is in `STANDING` (`overnight.py:379`), which the keeper thread reasserts every 5
minutes forever, restarting it whenever it's found down (`overnight.py:509-522`). It is *also*
started at the top of every cycle via `start()` (`overnight.py:636`, non-blocking, no timeout),
and *also* run again — blocking, with `timeout_h=2` — right after the reader finishes, explicitly
because "it sees the evidence the reader just produced" (`overnight.py:662-665`):

```python
636:        start("pipeline", [os.path.join(SRC, "pipeline.py")], "pipeline_auto.log")
...
664:        statuses.append(run("pipeline", [os.path.join(SRC, "pipeline.py")],
665:                            "pipeline_auto.log", timeout_h=2))
```

`run()`'s very first action is the singleton guard:

```python
167:    if running(os.path.basename(args[0])):
168:        log(f"  {name}: already running, left alone")
169:        return "already-running"
```

Because the keeper (a separate daemon thread) restarts `pipeline.py` the moment it ever exits,
and because `pipeline.py` is a GPU stage that can plausibly still be running from either the
keeper's last restart or the cycle-top `start()` call by the time `read`/`roll` finish, the
blocking call at line 664 routinely finds pipeline "already-running" and **returns immediately
without ever waiting for it, inspecting its return code, or applying the stated 2h cap.** The
comment's stated purpose — run pipeline *after* the reader, bounded, so it processes this
cycle's fresh evidence — can be silently defeated by the supervisor's own keeper mechanism. The
log shows only `"pipeline: already running, left alone"`, which reads as healthy, not as "the
intended ordered run did not happen."

VERIFIED by code reading (the STANDING membership, the keeper's unconditional restart-on-down
behavior, and `run()`'s singleton short-circuit are all directly in this file). Whether
`pipeline.py` is itself idempotent/backlog-processing (which would make the *data* eventually
consistent even though this specific ordering guarantee is lost) is outside this batch — flagging
as a design collision either way, since nothing in `overnight.py` accounts for it.

**Suggested repair:** decide whether `pipeline.py` is a standing service or a bounded per-cycle
job — it cannot correctly be both under the current `run()`/`STANDING` machinery. If it must stay
standing, replace the blocking re-run with a signal/marker the standing instance picks up (e.g. a
"new evidence available" flag) rather than a `run()` call whose entire timeout and rc-checking
logic is silently skipped whenever the singleton guard fires.

---

### 4. `overnight.py:696-701` — the crash-loop HALT safety net is masked by *any* "already-running" status among the cycle's three tracked jobs, even when the others are genuinely failing every cycle

```python
696:        busy = [x for x in statuses if x == "already-running"]
697:        if busy and snap["cycle_seconds"] < MIN_CYCLE_SECONDS:
698:            log(f"  {len(busy)} job(s) already running and working; waiting "
699:                f"{WAIT_SECONDS // 60}m before looking again")
700:            idle = 0
701:            time.sleep(WAIT_SECONDS)
702:    elif snap["cycle_seconds"] < MIN_CYCLE_SECONDS:
703:            idle += 1
...
706:            if idle >= IDLE_LIMIT:
707:                log("  HALT: every job has returned instantly for "
```

`statuses` holds exactly three entries per cycle: `read`, `roll` (via `join`), `pipeline`. The
`busy` check only asks "is *any* of the three `'already-running'`?" — it does not check whether
the *other two* are actually succeeding. Given Finding #3 above makes pipeline chronically
"already-running" once the keeper has taken it over, a scenario where (say) `read.py` is crashing
instantly every cycle (`rc=1`) while pipeline merely *looks* busy would take the `busy`-branch
forever: `idle` is reset to 0 every single cycle (line 700), so `IDLE_LIMIT` (3 fast cycles) can
never be reached and the supervisor never halts — it just logs "N job(s) already running and
working; waiting 10m" on repeat, which reads as healthy operation while up to two of the three
real stages are silently failing on every pass.

VERIFIED by code reading; the interaction with Finding #3 (which makes this scenario likely
rather than contrived) is noted but not independently reproduced end-to-end.

**Suggested repair:** the halt/idle decision should be per-job, or at minimum should require that
*every* status this cycle be either `"ok"` or `"already-running"` before treating the cycle as
healthy-and-busy — one crashing job should not be forgiven because a different job happened to
still be running.

---

### 5. `overnight.py:414-422` — `coverage_snapshot()` never checks the coverage subprocess's return code

```python
416:        subprocess.run([PY, os.path.join(SRC, "coverage.py")], cwd=HERE,
417:                       capture_output=True, text=True, timeout=1800,
418:                       env=dict(os.environ, PYTHONIOENCODING="utf-8"), creationflags=_NO_WIN)
419:        rows = json.load(open(os.path.join(HERE, "data", "COVERAGE.json"), encoding="utf-8"))
```

The `CompletedProcess` return value is discarded entirely — `.returncode` is never inspected, and
`capture_output=True` output is captured but never surfaced even on failure. If `coverage.py`
crashes (nonzero exit, no exception raised — `subprocess.run` without `check=True` never raises
for a nonzero exit) but the previous `data/COVERAGE.json` still exists on disk from an earlier
successful run, `json.load(...)` succeeds against the **stale** file and `coverage_snapshot()`
returns numbers that look exactly like a real, fresh measurement. This is precisely the failure
class the file's own comment at lines 674-679 says was already fixed — but that fix only covers
the case where the subprocess call itself raises (e.g. can't launch, hard timeout). A crash that
exits nonzero without raising slips straight through, silently re-reporting last cycle's numbers
as this cycle's in `STATUS.md` and in the `log()` line at 684-685.

VERIFIED by code reading (no `check=True`, no `.returncode` access anywhere in this function).

---

### 6. `overnight.py:433-455` — `preflight()` has the same gap for the same reason

```python
434:        r = subprocess.run([PY, os.path.join(SRC, "health.py"), "--preflight"], cwd=HERE,
435:                           capture_output=True, text=True, timeout=1800,
436:                           env=dict(os.environ, PYTHONIOENCODING="utf-8"), creationflags=_NO_WIN)
437:        out = r.stdout
```

Only `r.stdout` is inspected for `"FAIL"`/`"FAIL  control"` substrings; `r.returncode` is never
read. If `health.py --preflight` crashes early (before printing any `"FAIL"` line — e.g. an
import error at the top of the script) with a traceback on stderr and a nonzero exit, `out` would
contain no `"FAIL"` text, so `n = 0` and `blocking = False`: `preflight()` returns `(0, False)`,
**exactly** the "checked, nothing wrong" false-pass the code's own comment at lines 440-449
explicitly says it fixed for the launch-exception path — but, as with Finding #5, only for that
path, not for "ran, exited nonzero, printed nothing recognizable."

VERIFIED by code reading.

---

### 7. `sweep_plan.py:68-88` — `record()` has an unguarded read-modify-write race on the shared coverage file; this is the exact "multiple parallel batches" usage pattern the file exists to serve

```python
68: def record(run, covered):
70:     try:
71:         with open(COVERAGE, encoding="utf-8") as f:
72:             data = json.load(f)
73:     except Exception:
74:         data = {}
78:     for m in covered:
79:         data[m] = {"run": run, "at": now}
80:     tmp = COVERAGE + ".tmp"
81:     with open(tmp, "w", encoding="utf-8") as f:
82:         json.dump(data, f, indent=1, sort_keys=True)
84:         import silence
85:         silence.replace_retry(tmp, COVERAGE)
```

The final write *is* correctly atomic (`silence.replace_retry`, properly used — this is the one
place in the file that gets the two-writer contract right). But atomicity of the *write* does
nothing to protect the *read-modify-write cycle*: there is no lock, no version stamp, no
compare-and-swap. Two calls to `record()` — say batch 12 and batch 7's audit sessions both
finishing near the same time, each recording their own slice of `covered` — can both read the
same starting snapshot, each add their own modules in memory, and then each write their *own*
merged copy back; whichever write lands second silently discards the first call's additions,
because the second call's in-memory `data` never had them. This is a classic lost-update race,
and it sits directly on top of this file's stated purpose: "`missing()` is the check that proves
nothing was dropped" (line 17) is only true if `record()` can't itself drop a concurrent update.
Given the project's own standing instruction to parallelise sweep work across batches, concurrent
callers are the expected case, not an edge case.

VERIFIED the code path by reading; whether two batches actually call `record()` concurrently in
the current orchestration is a question about the caller (outside this file), not about the race
itself, which is real regardless.

**Suggested repair:** either serialize `record()` through the same retry/lock discipline used for
the final write (e.g. a short-lived lock file, or a merge-on-write scheme where the write itself
computes `data[m] = ...` after re-reading under the lock, not before), or have each batch write to
its own `SWEEP_COVERAGE.<run>.<batch>.json` and have `missing()`/`--coverage` merge across the set
at read time instead of merging in the writer.

---

### 8. `sweep_plan.py` — several of its own exception handlers are exactly the kind of silent swallow this project exists to eliminate, confirmed by `silence.py`'s own audit

Running `silence._handlers("sweep_plan.py")` against this brand-new file returns:

```
{'line': 46,  'type': 'Exception', 'silent': True}   # modules(): file read failure -> n = 0
{'line': 73,  'type': 'Exception', 'silent': True}   # record(): coverage read failure -> {}
{'line': 86,  'type': 'Exception', 'silent': True}   # record(): replace_retry import/fallback
{'line': 97,  'type': 'Exception', 'silent': True}   # missing(): coverage read failure -> {}
{'line': 122, 'type': 'Exception', 'silent': True}   # main(): --coverage read failure -> {}
```

The most consequential is line 46:

```python
42:    for p in sorted(glob.glob(os.path.join(SRC, "*.py"))):
43:        try:
44:            with open(p, encoding="utf-8", errors="replace") as f:
45:                n = sum(1 for _ in f)
46:        except Exception:
47:            n = 0
```

A module that fails to open — permissions, a transient I/O error, a race against a concurrent
editor — is silently reported as a **0-line module** rather than flagged in any way (no
`silence.note()`, no `"silence-exempt"` marker, no print). It still appears in `modules()`'s
output (so it isn't dropped from the roster outright — no Hard Rule 0 violation), but its line
count is fabricated as zero, which quietly corrupts the "roughly-equal-line-count" bin-packing
`batches()` is built around, and gives no signal that a module's audit weight is unknown rather
than genuinely tiny. This file was written "minutes ago in this session" specifically to enforce
full, honest coverage across every module — and its own read-failure path is exactly the
"honest-looking answer that gets believed" pattern `silence.py`'s docstring opens by describing.

VERIFIED by directly running the project's own `silence.audit()`/`_handlers()` against this file.

**Suggested repair:** import `silence` at module scope and call `silence.note("sweep_plan.py:modules")`
in the `except` at line 46 (and apply the project's own `"silence-exempt: ..."` idiom or a real
`note()` call to the other four, matching the convention already used everywhere else in this
tree for a "cache/coverage file not yet built" case).

---

## MEDIUM

### 9. `overnight.py:462` — `write_status()` uses a bare `open(p, "w")` on a cross-process file

```python
462:    with open(p, "w", encoding="utf-8") as f:
```

`STATUS.md` is written non-atomically (open-truncate, then a sequence of `f.write()` calls). The
file's own comments elsewhere describe `publish.py` reading and copying this exact file "verbatim"
on its own 10-minute loop while `overnight.py` may be mid-rewrite. Per the project's two-writer
contract ("shared state files via `silence.replace_retry`"), this should go through a
temp-file-plus-`replace_retry` write like `sweep_plan.record()` does correctly for
`SWEEP_COVERAGE.json`. A reader landing mid-write would see a truncated/partial `STATUS.md`.

VERIFIED (bare `open(..., "w")`, confirmed cross-process readership via the file's own comments
at lines 478-479 and the publish-loop description at lines 606-611).

### 10. `zfighters.py:476` and `wh40k.py:230` — same bare `open(OUT, "w")` pattern on shared data files

```python
zfighters.py:476:    with open(OUT, "w", encoding="utf-8") as f:
wh40k.py:230:        with open(OUT, "w", encoding="utf-8") as f:
```

`data/Z_FIGHTERS.json` and `data/WH40K_ASSAYS.json` are both read elsewhere in the tree
(`pantheon.py`, confirmed by grep). These are manually-invoked, standalone tools rather than
automated STANDING jobs, so the collision window is narrower than for `STATUS.md`, but the same
contract applies to any file another process reads. VERIFIED.

### 11. `cosmography.py:44-48` — the comment's claim that both galaxy-count figures are "kept" is not true of the code

```python
44:# Galaxies in the observable universe. Two published figures, both kept, because the disagreement
45:# is real and the library's own doctrine is to file both readings rather than silently average.
46:GALAXIES_CONSELICE_2016 = 2.0e12   # Conselice et al. 2016, deep-field extrapolation
47:GALAXIES_LAUER_2021 = 2.0e11       # Lauer et al. 2021, New Horizons cosmic optical background
48:GALAXIES_DEFAULT = GALAXIES_LAUER_2021   # declared choice: the newer, more direct measurement
```

`GALAXIES_CONSELICE_2016` is never referenced anywhere else in this file, and `grep -rl` across
all of `src/` turns up nothing else that uses it either — it is dead. Only
`GALAXIES_LAUER_2021` (via `GALAXIES_DEFAULT`) is ever wired into `census()`. The comment's stated
design property ("both kept... rather than silently average") is not delivered: there is no
parameter, no alternate code path, no report field anywhere that exposes the Conselice figure.
Functionally, this file *does* silently pick one and discard the other — the opposite of what the
comment claims. VERIFIED (grep across `src/*.py` confirms zero other references).

### 12. `descending_ladder.py:85-95` — `rung_for_length()` has no upper-bound guard; out-of-range input is silently misclassified as "Continental" rather than rejected or delegated

```python
85: def rung_for_length(metres):
86:     """Which descending rung does a given size belong to? Returns (rung, name)."""
87:     if metres <= 0:
88:         return None, None
89:     if metres < PLANCK_LENGTH:
90:         return FOLD_RUNG, "Below the Fold"
91:     best = DESCENDING[0]
92:     for r in DESCENDING:
93:         if metres <= r[3]:
94:             best = r
95:     return best[0], best[2]
```

The function explicitly guards the *lower* bound (below Planck length → `FOLD_RUNG`) but has no
corresponding guard for the *upper* bound (above the Continental rung's 1e6 m). When `metres`
exceeds every rung's characteristic length, the loop's `if metres <= r[3]` condition never fires
for any entry, so `best` never leaves its initial value, `DESCENDING[0]` ("Continental",
rung 0) — silently, with no signal that the input was outside this table's intended
sub-planetary domain at all. Directly reproduced:

```
>>> rung_for_length(1e10)     # nowhere near continental scale
(0, 'Continental')
>>> rung_for_length(3e16)     # roughly a light-year
(0, 'Continental')
```

Currently **dormant** — `grep` finds no other module in `src/` calling `rung_for_length()` yet
(only listed as a name in `derivation.py`'s `SCAN_MODULES`). But the module's own docstring frames
its purpose as fixing exactly this kind of silent floor/ceiling gap for the Reach axis ("every
sub-planetary Reach is scored against a floor that does not exist"); once wired into that
integration, any caller that doesn't pre-filter to sub-planetary values will get a wrong,
unflagged "Continental" answer for ordinary planetary/stellar/galactic Reach values. VERIFIED by
direct execution.

### 13. `sweep_plan.py:34-49` — `modules()`'s docstring claims an ordering the code does not implement

```python
34: def modules():
35:     """Every module in src/, newest-largest first. NO exclusions, deliberately.
...
49:    return sorted(out, key=lambda m: -m["lines"])
```

The only sort key is line count, descending. There is no `os.path.getmtime` call, no timestamp
field, nothing anywhere in this function or file that reads file modification time — "newest" is
not implemented at all, only "largest." A reader relying on the docstring's claim (e.g. assuming
recently-touched modules get priority within a batch) would be wrong. VERIFIED (grep confirms no
`getmtime`/`st_mtime`/`os.stat` usage anywhere in the file).

---

## LOW

### 14. `overnight.py:71-75` — lazy-singleton lock initialization race

```python
71:    global _PROCS_LOCK
72:    if _PROCS_LOCK is None:
73:        import threading
74:        _PROCS_LOCK = threading.Lock()
75:    with _PROCS_LOCK:
```

Classic check-then-act on a module-global without an outer lock. `_proc_lines()` (via
`running()`) is called from the main thread and from the `_keep()` / `_keep_warm()` daemon
threads started in `main()`; if two callers race the very first call before `_PROCS_LOCK` exists,
each could construct and install its own `Lock()` instance, so early callers on either side of
that race would not actually be mutually excluded. Narrow window (only matters before the first
successful call installs the shared lock), and the worst outcome is a duplicate subprocess probe
rather than data corruption. VERIFIED by code reading.

### 15. `overnight.py:49`, `zfighters.py:47`, `silence.py:74`, `wh40k.py:41` — module self-check opens its own source file without closing the handle

```python
overnight.py:49:  if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
```

Same pattern in all four files (`_BAD_CHARS` self-scan at import time). No `with` block, no
explicit `.close()` — relies on CPython refcounting to close the handle once the generator
expression finishes. Harmless in practice under CPython, but inconsistent with the otherwise
careful resource handling elsewhere in these same files (e.g. `overnight.py`'s `run()`/`join()`
explicitly close/`finally`-close their log handles). Style nit rather than a functional leak.

### 16. `silence.py:245-282` — `note()`'s counters are updated without a lock from a function documented as safe to call from anywhere, including background threads

```python
245: _ATEXIT_ARMED = False
246: _SINCE_FLUSH = 0
...
269:        if not _ATEXIT_ARMED:
270:            import atexit
271:            atexit.register(health.flush)
272:            _ATEXIT_ARMED = True
...
277:        _SINCE_FLUSH += 1
278:        if _SINCE_FLUSH >= FLUSH_EVERY:
```

`overnight.py`'s `_keep()` and `_keep_warm()` daemon threads both call `silence.note(...)` from
inside except blocks (`overnight.py:520`, `overnight.py:556`, `overnight.py:580`), concurrently
with any main-thread caller. The `_ATEXIT_ARMED` check-then-act could register
`atexit.register(health.flush)` more than once (harmless — an extra flush at exit is a no-op on
an already-flushed ledger). `_SINCE_FLUSH += 1` can lose increments under thread interleaving,
which can only *delay* a periodic mid-run flush, not lose the underlying `health.record(...)`
call itself (that part is unconditional, earlier in the same function). Low real-world impact,
included for completeness of the concurrency sweep requested.

### 17. `cosmography.py` — three more constants are defined and never used anywhere in `src/`

`STARS_MILKY_WAY` (line 52), `EARTH_POWER_2020` (line 69), `KARDASHEV_TYPE_I` (line 66) are all
"MEASURED CONSTANTS (real, cited)" per the section header, but none is referenced anywhere in this
file or the rest of the tree (`KARDASHEV_TYPE_II`/`KARDASHEV_TYPE_III` *are* used, by
`verify_math.py:160/164`, so those two are fine). Likely intended as reference/documentation
values or fixtures for a not-yet-written check; not a functional bug, just genuinely dead code
worth a look next time this file is touched.

### 18. `wh40k.py` — no provenance field on axis evidence, unlike the sibling module `zfighters.py`

`zfighters.py`'s `ROSTER` entries are 3-tuples `(score, evidence, provenance)` with per-axis
`"wiki"`/`"canon"` tagging; `wh40k.py`'s are 2-tuples `(score, evidence)`, and `compute()`
hardcodes `"[wiki] "` for every axis of every entity (`wh40k.py:197`) with no way to express
anything else. Not a bug in itself (every WH40K axis description here does appear to quote wiki
text directly), but it's a structural inconsistency between two near-identical modules, and the
2-tuple format gives no way to flag a future non-wiki-sourced axis the way `zfighters.py` can.

---

## CLEAN

- **`cosmography.py`** — the actual astrophysics/Kardashev math is internally consistent:
  `KARDASHEV_MIX` sums to exactly 1.0, `validate()`'s physical-impossibility checks are correctly
  derived and were verified by hand-computing a full `census("STANDARD")` run
  (~1.2e15 extant civilizations, all four Kardashev-tier population checks pass against galaxy/
  star/habitable-world ceilings), `kardashev_K`/`kardashev_to_magnitude` guard their domain
  edges (`watts <= 0`, `size_m <= 0`) correctly, and there is no try/except anywhere in the file
  (nothing for the silence/two-writer rules to apply to). Apart from findings #11 and #17 above
  (unused constants / one overclaiming comment), this module is sound.
- **`zfighters.py`** — all 14 hand-authored roster entries carry exactly the 11 axes
  `assay.WEIGHTS` expects (verified programmatically — zero missing/extra axes across the whole
  roster), `compute()` runs cleanly end to end, the Goku carry-in fallback is correctly wrapped
  and recorded via `silence.note()` on failure. Apart from finding #10 (shared bare-`open`) and
  the self-check style nit, no other issues found.
- **`wh40k.py`** — same automated axis-completeness check passes for all 5 entities, `compute()`
  runs cleanly, the ranking/printing logic is correct. Apart from findings #10 and #18, no other
  issues found.
- **`descending_ladder.py`** — the physics helper functions
  (`compton_confinement_energy`, `density_at_scale`, `schwarzschild_radius`,
  `transgression_bits`) are dimensionally correct, guard their domain edges appropriately, and
  the file's own documented 2026-08-20 correction (uncertainty-relation pricing was wrong,
  degeneracy-pressure pricing is right) checks out against the stated example (a 70 kg man
  compressed to atomic scale). No try/except anywhere in the file. Only finding #12
  (`rung_for_length`'s missing upper bound) stands against it.

---

## Notes on method

- Ran `C:/Users/imarl/miniconda3/python.exe` against live imports of `zfighters`, `wh40k`,
  `cosmography`, `descending_ladder`, `silence`, and `sweep_plan` to verify axis completeness,
  `compute()`/`census()` execution, the `ast.dump()` substring-matching bugs in `silence.py`, and
  the `rung_for_length()` upper-bound gap, rather than relying on static reading alone for the
  claims where a live check was feasible without touching any file.
- Did not audit `foreman.py`, `health.py`, `pipeline.py`, `read.py`, `pantheon.py`,
  `verify_math.py`, `derivation.py`, or `coverage.py` — referenced only as corroborating context
  for findings about this batch's own seven files, per the batch boundary.
