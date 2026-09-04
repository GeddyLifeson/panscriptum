# Sweep43 Batch 11 Audit

Files read completely: `src/overnight.py`, `src/silence.py`, `src/gpu_lane.py`, `src/weave.py`,
`src/backfill.py`, `src/retry_synthesis.py`, `src/runguard.py`, `src/suppressions.py`.

Method note: these eight modules already carry an unusually dense record of past defects found
and fixed, each with a docstring or comment explaining the incident. Most candidate findings I
considered while reading turned out to be that history — already closed, and reasoned about
correctly in the code as it stands today. Where I could, I verified a candidate directly (ran
`silence._handlers()` against all eight files to cross-check for un-recorded swallows; grepped
the tree for callers of suspect functions; spawned a real child process to test `gpu_lane._alive()`
against live/dead/nonexistent PIDs; read `escalation.py`'s `status()`/`_read_halt_raw()` to check
whether a swallow in `overnight.py` is actually reachable). Several plausible-looking issues did
not survive that check and are not reported. Below are the ones that did.

---

## src/overnight.py

### MINOR — `_ESC.status()` failure defaults to "not halted," in the exact code written to stop that shape of outage
`src/overnight.py:1531-1536`

```python
try:
    import escalation as _ESC
    _halted, _rec = _ESC.status()
except Exception:
    _halted, _rec = False, None
```

This sits inside the `idle >= IDLE_LIMIT` branch whose own comment, three lines above, explains
the 2026-08-25 incident: the escalation halt makes every job exit immediately, which from the
supervisor's vantage looks identical to every job crashing on startup, so the supervisor once
concluded the library was broken and exited — "the safety mechanism caused the outage it exists
to prevent." The fix was to check `escalation.status()` first and wait rather than give up when
the library is genuinely halted.

If that check itself raises, this `except` silently assumes **not halted**, and control falls
through to the "HALT: every job has returned instantly... that is not an idle library, it is a
broken one" branch a few lines below, which `break`s the main loop and ends the supervisor
process — reproducing the exact outage this code exists to prevent, one layer down. That is a
fail-**open** default in a function explicitly about a fail-closed guarantee (Hard Rule -1: "An
unreadable config... a corrupt halt file: all refuse. Silence must never authorise anything.").

I checked whether this is actually reachable: `escalation._read_halt_raw()` is written to never
raise — it catches every read/parse failure itself and returns a fail-closed stand-in record
(`_unreadable_halt(...)`), and `status()` just derives `(halted, record)` from that. So under
normal operation this `except Exception` is close to dead code; the only realistic trigger is
`import escalation` itself failing at this specific point deep into an hours-long cycle (e.g. the
module vanishing or breaking under a foreman auto-patch or maintenance run while jobs were
running), which the top-of-cycle `assert_clear()` check earlier in the same iteration would not
have caught because it ran hours earlier. Given that mitigating fact I am rating this MINOR
rather than MAJOR, but the direction is still wrong and worth closing: default to treating an
unreadable halt-status as "assume halted, wait" rather than "assume clear, declare broken,"
matching the fail-closed convention used everywhere else rung 5 is checked in this file (compare
the top-of-cycle interlock a few dozen lines above, which raises `SystemExit` rather than
proceeding when escalation cannot be imported).

**Remedy:** on the exception, treat the situation the same as `_halted=True` (wait and retry)
rather than `False` — or at minimum call `silence.note(...)` so a real occurrence leaves a mark,
since right now it would leave none.

### MINOR — `_in_this_tree`'s two swallow points have no ledger visibility
`src/overnight.py:270-278`

```python
        try:
            import psutil
            script = os.path.join(psutil.Process(pid).cwd(), script)
        except Exception:
            return False              # cannot tell whose copy it is -- see the docstring
    try:
        return os.path.samefile(script, os.path.join(HERE, "src", os.path.basename(script)))
    except OSError:
        return False                  # vanished mid-walk, or unreadable
```

Both branches are deliberate and correctly reasoned (the function's own docstring: "FAILS OPEN BY
SAYING NO... that direction is deliberate and it is the cheaper error here"). I am not disputing
the direction. What is missing is any `silence.note()` call: if `psutil` is ever unimportable, or
`Process(pid).cwd()` consistently raises (e.g. under a permissions regime that denies querying
other users' processes), `_in_this_tree` silently returns `False` for every relative-path
command line it is asked about, every single call, for the life of the process — and this feeds
directly into `running()`, which is the ONE OF EACH invariant the whole module exists to hold.
A systemic failure here degrades the singleton guard (toward allowing a duplicate stage) with
nothing in `state/failures.json` to show it happened. Every other swallow in this file that can
matter this much calls `silence.note(...)`; these two are the exception.

**Remedy:** add `silence.note("overnight.py:in-this-tree-psutil")` / `"...-samefile"` on these two
paths, matching the convention used a few lines above at `_proc_lines`.

### MINOR / INFO — lazily-constructed module locks have a bootstrap race
`src/overnight.py:100-101, 136-140` (`_PROCS_LOCK`) and `354, 357-362` (`_SPAWN_LOCK`)

```python
_PROCS_LOCK = None
...
    global _PROCS_LOCK
    if _PROCS_LOCK is None:
        import threading
        _PROCS_LOCK = threading.Lock()
    with _PROCS_LOCK:
```

Both locks are created lazily, on first use, with a plain `if X is None: X = Lock()` — the
classic unsynchronised double-checked-locking pattern. CPython's GIL is released on a timer, not
only at safe points chosen by the programmer, so two threads can both observe `X is None`,
each construct their own `Lock()`, and each proceed to hold a *different* lock object for a
window before the global settles on one of them. `_guarded_popen`'s own docstring stakes a
specific correctness claim on this: "SERIALISED against every other thread in this process," a
guarantee added specifically because the keeper thread and the cycle body both call it for the
same job names. A momentarily-unsynchronised bootstrap defeats that guarantee for exactly the
race it was added to close.

I checked reachability: in `main()`, `running("overnight.py")` (which uses `_PROCS_LOCK`) runs on
the main thread before either background thread (`_keep`, `_keep_warm`) is started, and the
keeper thread sleeps 300s before its first call into `_guarded_popen` (via `start()`), while the
cycle body's own first standing-job starts happen immediately. So in the code as it stands today,
both locks are already-constructed singletons by the time a second thread could contend for them,
and the race is not currently triggerable. It is real and latent, though, and would reappear
silently if the keeper's first-iteration delay is ever shortened or another thread is added ahead
of it.

**Remedy:** construct both locks at module level (`_PROCS_LOCK = threading.Lock()`,
`_SPAWN_LOCK = threading.Lock()`) instead of lazily — module import is already serialised by
Python's import system, which removes the race for free and costs nothing.

---

## src/weave.py

### MINOR — `null_threshold()` is dead code, unlike its sibling, and is not reported as such
`src/weave.py:276-300`

```python
def null_threshold(occ, idf, sources, trials=40, pct=99.9, seed=20260820):
    """Permutation null: what pair weight arises purely by chance?
    ...
```

I grepped all of `src/` for callers: nothing calls `null_threshold` (the idf-weighted permutation
helper) anywhere, including `weave.py`'s own `main()`, which calls `null_threshold_surprisal`
instead. Its sibling `pair_weights()` — the idf-weighted pair-scoring function this null threshold
was built to accompany — is in the identical position (superseded by `surprisal_pair_weights`,
called from nowhere) and carries an explicit comment saying so: "SUPERSEDED, NOT CALLED ANYWHERE
-- `main()` here, `pipeline.py` and `tiers.py` all call `surprisal_pair_weights()` instead...
Reported, not deleted, per house doctrine that dead code is not automatically deletable: order
25ec11447b4c / sweep33 batch08 finding 8." `null_threshold` is the same shape of leftover
(superseded by the surprisal-weighted version, in the same idf-vs-surprisal split this module's
docstring documents) but has no such comment and was never filed. Per this project's own doctrine
that dead code must be reported rather than silently carried, this is the gap.

**Remedy:** OWNER call on whether to delete `null_threshold` now that `pair_weights` (its only
sensible caller) is itself superseded, or annotate it the same way `pair_weights` is annotated
and leave both for a future cleanup pass together.

---

## Clean

- **src/silence.py** — read completely. The write path (`write_json`/`replace_retry`/
  `replace_if_unchanged`), the append path (`append_line`, Windows byte-range locking), and the
  audit/instrument machinery were all re-verified line by line against their own change-history
  comments; I could not find a place where the current code disagrees with its own docstring. Ran
  `silence._handlers()` against this file's own handlers (5 flagged "silent" by the automated
  audit) and checked each by hand — all are legitimate root-of-the-recording-chain swallows
  (`note()` itself, `swallow.__exit__`, fd/lock cleanup) that must not recurse into the recorder,
  or the documented "absent, not unreadable" `FileNotFoundError` arm. No findings.
- **src/gpu_lane.py** — read completely, including the Windows `_alive()` PID-liveness check,
  which I tested directly against a live, a just-killed, and a never-existent PID (see Method
  note) and confirmed behaves as documented. Checked the slot/claim/heartbeat machinery
  specifically for double-release or double-acquire shapes (per this batch's brief) and found
  none: `O_CREAT|O_EXCL` gives atomic slot acquisition, `_remove_retry` is idempotent on
  `FileNotFoundError`, and the heartbeat thread is stopped before release in `lane()`'s `finally`.
  12 handlers flagged "silent" by the automated audit, all deliberate and already reasoned in the
  module's "FAIL OPEN, ALWAYS" header. No findings.
- **src/backfill.py** — read completely. The ranking/cap machinery (`roster()`, `backfill_source`'s
  size-lookup-failed handling and its `(t in sizes, -sizes.get(t,0))` sort key) matches its own
  extensively-documented fix history when traced by hand. No findings.
- **src/retry_synthesis.py** — read completely. Nomination method genuinely shares code with
  `pipeline.py` as claimed; `save_side`/`do_merge` gate on write verdicts throughout. No findings.
- **src/runguard.py** — read completely, focusing on the lock-lifecycle question this batch
  flagged. `claim`/`beat`/`release` all take the digest before the read (closing the race the
  docstrings describe) and route through the same CAS helper. `release()` does not itself check
  `rec.get("done")` before writing (unlike `beat()`, which does) — I traced this for a
  double-release scenario and it is not exploitable: the ownership check plus the CAS against the
  digest taken at the start of the call together prevent a stale `release()` from doing anything
  but a harmless no-op or a correctly-refused overwrite. See the QUESTION below for a real,
  unresolved tension in this file's fail-direction.
- **src/suppressions.py** — read completely. `active()`/`problems()` fail closed on an unreadable
  or wrong-shaped file as documented; `suppressed()` is genuinely wired into `publish.py`'s secret
  scan and `drill.py`'s own nets (I grepped for this specifically, since an unused suppression
  mechanism would itself be a finding — it is not unused). No findings.

---

## Questions (for the OWNER, not findings)

1. **runguard.py deliberately fails OPEN on a corrupt/unreadable guard record — is that the
   intended exception to Hard Rule -1?** `read()`'s docstring is explicit about the choice: "an
   unreadable guard cannot prove a predecessor is live, and refusing to run on a corrupt guard
   would wedge the pass permanently on a file nothing else repairs." `holder_is_live()` follows
   through on that — a record with a missing or non-numeric `heartbeat` field returns `False`
   (not live), which lets a fresh `claim()` proceed. That is the opposite of Hard Rule -1's
   "FAIL CLOSED... a corrupt halt file: all refuse. Silence must never authorise anything," and
   the module's own header says this file exists specifically to hold the one invariant that
   prevented m27 (two maintenance runs overlapping). The justification given (nothing else
   repairs `MAINTENANCE_RUN.json`, so failing closed wedges the pass forever) is reasonable on
   its face, but it is a real, load-bearing departure from the project's stated doctrine and I
   could not find anywhere it was put to the owner as a ruling the way the prose gate and other
   Hard Rule -1 exceptions were. Worth an explicit decision: is a corrupt guard record acceptable
   to treat as "free to claim," or should it instead escalate (e.g. via `escalation.py`) so a
   person clears it rather than the next `claim()` silently doing so?

---

## Coverage note

All eight files were read top to bottom, not sampled. `overnight.py` (1557 lines) required two
reads due to a tool output cap; both halves were read.
