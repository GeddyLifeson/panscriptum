# Mutation survivors in `src/escalation.py` — adjudication

Source of survivors: `state/mutate_20260910.log`, 22 rows for `src/escalation.py`.
Adjudicated against the CURRENT `src/escalation.py` (1445 lines) on 2026-09-10.
Interpreter checked: `C:/Users/imarl/miniconda3/python.exe` = **CPython 3.13.9** (matters for
line 272 — `int.is_integer()` exists from 3.12, so an int level does not raise there).

## Citation drift: NONE

The log warns that `src/` moved under the run (fingerprint `f9d8e89e7044ebf8` -> `53fe3a432306b066`).
Every one of the 21 distinct cited line numbers was checked against the current file by printing
that exact line. **All 21 hold the cited code verbatim.** No corrected line numbers are needed.

One citation was *ambiguous* rather than drifted:

- **`escalation.py:1183  or -> and`** — the line has TWO `or` tokens. The log carries one row.
  The survivor must be the **first** `or`, because the second `or` is covered: `drill.py:2782`
  runs `_refuses(lambda: ESC.clear("ok"), ValueError)`, and mutating the second `or` turns the
  condition into `A or (B and C)`, which for `ruling="ok"` evaluates False and lets the lift
  proceed — that mutant would have died on that net. Adjudicated as the first `or`.

## Tally

**9 EQUIVALENT, 13 GAP.**

| # | line | mutation | ruling |
|---|------|----------|--------|
| 1 | 272 | `and -> or` | GAP |
| 2 | 272 | drop `not` | GAP |
| 3 | 303 | drop `not` | GAP |
| 4 | 416 | `False -> True` | GAP |
| 5 | 419 | `True -> False` | GAP |
| 6 | 421 | `True -> False` | GAP |
| 7 | 428 | `> -> <=` | GAP |
| 8 | 438 | drop `not` | GAP |
| 9 | 444 | `False -> True` | EQUIVALENT (by accident — see caveat) |
| 10 | 447 | `True -> False` | EQUIVALENT (by accident — see caveat) |
| 11 | 495 | `False -> True` | EQUIVALENT (dead store) |
| 12 | 567 | `False -> True` | EQUIVALENT (dead store) |
| 13 | 695 | `False -> True` | EQUIVALENT (dead store) |
| 14 | 923 | `False -> True` | GAP |
| 15 | 993 | drop `not` | GAP |
| 16 | 1006 | `False -> True` | EQUIVALENT (dead store) |
| 17 | 1183 | `or -> and` (first) | EQUIVALENT (for every `str` ruling) |
| 18 | 1239 | `False -> True` | EQUIVALENT (dead store) |
| 19 | 1274 | `False -> True` | EQUIVALENT (whole statement is dead) |
| 20 | 1297 | `False -> True` | GAP (narrow) |
| 21 | 1324 | `False -> True` | GAP (narrow) |
| 22 | 1379 | `or -> and` | GAP |

---

# GAPs, in priority order

Severity is judged on the module's job: this is the HALT mechanism, a Hard Rule -1 safety. A
mutation that lets a stop or halt be lifted when it should stand outranks one that defeats a
race guard, which outranks one that garbles a ledger field, which outranks one that garbles
a message.

---

## G1 (HIGHEST) — line 993, drop `not`: an autonomous run can resume a rung-4 stop

Current source (`resume_subsystem_verdict`, def at 961):

```
 975:     if not (ruling or "").strip() or len(str(ruling).strip()) < 20:
 976:         raise ValueError("resuming a stopped subsystem needs a written ruling, not a shrug")
 ...
 993:     if not _a_probe_release(name) and not _by_a_person_at_the_cli():
 994:         raise PermissionError(
 995:             "a stopped subsystem may not be re-opened programmatically. ...")
```

Contract (docstring 926-958 and the comment at 977-999, owner ruling 2026-09-08 "Who may lift a
halt or a subsystem stop", order ddb5eadd8934): *an autonomous run may STOP a subsystem; only a
person may resume one.* The guard refuses unless the caller is either drill's narrow structural
exemption (`_a_probe_release`) **or** a person at this file's own CLI.

Mutant: `if _a_probe_release(name) and not _by_a_person_at_the_cli():`

**Observable change.** For the case the guard exists for — a real subsystem name, a programmatic
caller — `_a_probe_release(name)` is False, so the mutated condition is False and **no
`PermissionError` is raised**. The resume proceeds: `doc.pop(name)`, `_write_stopped`, and a
`JANITOR SUBSYSTEM_RESUMED` escalation. The exact hole order ddb5eadd8934 closed is re-opened,
and the docstring at 927-932 becomes false again.

**Why the battery missed it.** All three of drill's resume calls (`drill.py:9454`, `9483`,
`9593`) sit in the `finally` of a probe wrapped in `try: ... except Exception: silence.note(...)`,
so the mutant's *other* direction — a reserved probe name now raising `PermissionError` — is
swallowed. The one net that asserts a refusal, `resuming_demands_a_written_ruling`
(`drill.py:9464`), calls `E.resume_subsystem(name, "ok")` and requires `ValueError`; the
20-character ruling check at line 975 runs first and still fires, so that net passes either way.
`grep PermissionError src/drill.py src/verify_math.py` shows **no net anywhere asserts that
`resume_subsystem` refuses a programmatic caller.** `_no_runtime_clear` (`drill.py:4251`) covers
`clear()` only.

**Net that kills it.** Sibling of `_no_runtime_clear`, pointed at the resume instead of the lift.
Inside `_esc_sandbox()` the sandbox arm of `_a_probe_release` (line 916, `STOPPED != _REAL_STOPPED`)
would answer True for every name, so this must be driven **against the real ledger with nothing
stopped**, exactly as `the_person_check_is_not_defeated_by_choosing_a_name` (`drill.py:9493`)
already does:

```
def a_resume_is_refused_to_a_program():
    import escalation as E
    if E.STOPPED != E._REAL_STOPPED:
        return False          # sandboxed: the name arm is answering. Not a pass.
    r = "a ruling long enough to pass the twenty character bar"
    # a REAL subsystem name, called from drill.py, must be refused before anything is written
    if not _refuses(lambda: E.resume_subsystem_verdict("catalogue_web", r), PermissionError):
        return False
    if not _refuses(lambda: E.resume_subsystem("catalogue_web", r), PermissionError):
        return False
    # and the exemption still works, or drill's own cleanup breaks
    for good in H.SELFTEST_RESUME_SUBJECTS:
        if _refuses(lambda: E.resume_subsystem_verdict(good, r), PermissionError):
            return False
    return True
```

Both directions are required: a one-sided net that only demands the refusal would pass a fix that
refuses everything and would break drill's own probe cleanup. Note the second limb (the exempt
names) returns `(False, "<name> was not stopped; nothing to resume")` rather than raising, which
is the correct "reached the write path" evidence without writing anything.

---

## G2 (HIGH) — line 923, `False -> True`: the exemption fails OPEN when its evidence goes missing

Current source (`_a_probe_release`, def at 878):

```
 916:     if STOPPED != _REAL_STOPPED:
 917:         return True
 918:     try:
 919:         import health as _H
 920:         return bool(_H.is_resume_probe(name))
 921:     except Exception:
 922:         silence.note("escalation.py:probe-release-marker")
 923:         return False
```

Contract, spelled in capitals in the docstring at 912-914: *"FAILS CLOSED. If `health` cannot be
imported the answer is False — not a probe — so the person check applies in full. An exemption
that survives its own evidence going missing is not an exemption, it is a hole."*

Mutant: `return True`.

**Observable change.** Whenever `import health` fails or `is_resume_probe` raises,
`_a_probe_release` answers **True for every name**. Line 993 then short-circuits
(`not True` is False) and the person check is skipped entirely — same end state as G1, reached
through the error path instead of the name path. The docstring's promise inverts word for word.

**Why the battery missed it.** `health` imports fine under the battery, so line 923 is never
executed. `the_person_check_is_not_defeated_by_choosing_a_name` (`drill.py:9493`) exercises only
the name arm at 920.

**Net that kills it.** Drive the `except` arm directly — the predicate takes no lock and writes
nothing, so this is cheap:

```
def the_probe_exemption_fails_closed_without_its_evidence():
    import escalation as E, sys
    if E.STOPPED != E._REAL_STOPPED:
        return False
    import health as _H
    saved = sys.modules.pop("health")
    sys.modules["health"] = None          # forces ImportError on the late `import health`
    try:
        return E._a_probe_release("__drill_rung4__") is False
    finally:
        sys.modules["health"] = saved
```

Assert `is False`, not falsy — the whole point is which of the two literals is returned. A second
row can stub `_H.is_resume_probe` to raise and assert the same.

---

## G3 (HIGH) — line 428, `> -> <=`: the staleness test inverts and live locks are stolen

Current source (`_halt_lock`, contextmanager, def at 390):

```
 423:         except FileExistsError:
 424:             # STALENESS STEAL. A lock whose file has not been touched inside the window is a
 425:             # lock nobody is holding ... Steal it and try again rather than wait out a corpse.
 426:             try:
 428:                 if time.time() - os.path.getmtime(lock) > HALT_LOCK_STALE_SECONDS:
 429:                     os.remove(lock)
 430:                     continue
 431:             except OSError:
 432:                 pass
 433:             time.sleep(HALT_LOCK_WAIT)
```

`HALT_LOCK_STALE_SECONDS = 60.0` (line 381), `HALT_LOCK_ATTEMPTS = 40`, `HALT_LOCK_WAIT = 0.05`.

Mutant: `if time.time() - os.path.getmtime(lock) <= HALT_LOCK_STALE_SECONDS:`

**Observable change.** Exactly inverted, and inverted in the unsafe direction:

- A **fresh** lock — the file a writer is actively holding, age <= 60s — is immediately
  `os.remove`d and taken. Mutual exclusion over `state/HALT.json` is gone: two processes are
  inside the read-merge-rename section at once, which is precisely the lost-fault race the lock
  was added to close (order 97cc0dc43ca7, comment at 489-494). The loser's `finally` at 448-450
  then removes a lock file that by now belongs to the thief.
- A **genuinely stale** lock — a corpse older than 60s — is never stolen; the loop spins 40 x
  0.05s and fails open with the "HALT LOCK NOT TAKEN" warning. A dead process's lock file now
  degrades every subsequent halt write for as long as it sits there.

**Why the battery missed it.** `grep` over `src/drill.py` and `src/verify_math.py` for
`HALT_LOCK`, `halt-lock` and `.lock` finds **only** `codewatch`'s `LEDGER_LOCK` rows. There is no
net anywhere that exercises `escalation._halt_lock`. The whole cluster G3-G6, G8, G9 and the two
EQUIVALENT-by-accident rulings at 444/447 all rest on that single absence.

**Net that kills it.** Two rows inside `_esc_sandbox()` — `lock` is computed as
`HALT_FILE + ".lock"` **at call time** (line 415), which the docstring at 412-413 says is
deliberate, so the sandbox redirection carries the lock into scratch:

```
def a_fresh_lock_is_not_stolen():
    d, filed, restore = _esc_sandbox()
    try:
        lock = ESC.HALT_FILE + ".lock"
        os.makedirs(os.path.dirname(lock), exist_ok=True)
        open(lock, "w").close()                     # fresh mtime: a live holder
        ESC.HALT_LOCK_ATTEMPTS = 3                  # keep the wait to ~0.15s
        with ESC._halt_lock() as got:
            if got is not False:                    # must refuse, not steal
                return False
        return os.path.exists(lock)                 # and the holder's lock must survive
    finally:
        restore()

def a_stale_lock_is_stolen():
    ... same setup, then: os.utime(lock, (time.time() - 600, time.time() - 600))
    with ESC._halt_lock() as got:
        if got is not True: return False
    return not os.path.exists(lock)                 # released on the way out
```

These two rows also kill G4, G5, G6, G8 and G9, and they are the rows that make 444/447 stop
being equivalent (see the caveat under E1/E2). Restore `HALT_LOCK_ATTEMPTS` in the `finally`.

---

## G4 (HIGH) — line 438, drop `not`: the lock verdict inverts

```
 438:     if not held:
 439:         silence.note("escalation.py:halt-lock-not-taken")
 440:         sys.stderr.write("HALT LOCK NOT TAKEN (%s) — raising the halt UNLOCKED ...")
 444:         yield False
 445:         return
 446:     try:
 447:         yield True
 448:     finally:
 449:         with contextlib.suppress(OSError):
 450:             os.remove(lock)
```

Mutant: `if held:`.

**Observable change.** Fully inverted.
- Lock **taken** (`held` True): warns "HALT LOCK NOT TAKEN", yields False, and `return`s at 445 —
  so the `finally` never runs and **the lock file is leaked**, blocking every other halt writer
  until the 60s staleness steal.
- Lock **not taken** (`held` False, i.e. 40 contended attempts or a non-contention `OSError`
  break at 437): falls into the `try`, yields True, and the `finally` `os.remove(lock)`s a file
  this process never created — deleting the actual holder's lock. Two writers inside the section.

Same net as G3 kills it: the contended row expects `False` + lock survives (mutant yields True
and deletes it); the uncontended row expects `True` + lock removed after (mutant yields False and
leaks it).

---

## G5 (HIGH) — line 416, `False -> True`: a lock that was never taken reports as held

```
 415:     lock = HALT_FILE + ".lock"
 416:     held = False
 417:     for _ in range(HALT_LOCK_ATTEMPTS):
 ...
 421:             held = True
 422:             break
 ...
 434:         except OSError:
 437:             break
```

Mutant: `held = True`.

**Observable change.** This is *not* a dead store, unlike the `landed, why = False, ...` cluster.
`held` is only assigned inside the `try` on the success path (421). The two paths that leave the
loop **without** assigning it — all `HALT_LOCK_ATTEMPTS` exhausted under contention, and the
non-contention `except OSError: break` at 434-437 (read-only or missing `state/`, an AV object
lock) — carry the initializer straight to line 438. So under the mutant those paths report a lock
that was never created: no fail-open warning, `yield True`, and a `finally` that `os.remove`s
another process's lock file.

That is the fail-open design at 403-410 being quietly converted into a fail-*silent* one: the
lock's own comment says it "can never add a refusal", but it also must never claim an exclusion it
does not have.

Killed by the contended row of the G3 net.

---

## G6 (MEDIUM-HIGH) — line 272, drop `not`: the non-integral-float guard inverts

```
 268:     # `is_integer()` IS HONOURED, so `escalate(3.0, ...)` still means SAFETY. 3.0 names a rung
 269:     # exactly; 2.7 does not name one at all, and the difference is not a matter of taste.
 272:     if isinstance(level, float) and not level.is_integer():
 273:         _bad_level, level = repr(level), MANAGER
 274:     try:
 275:         level = int(level)
```

By line 272 a `str` level has already been resolved to an int by the `BY_NAME` block at 253-258,
so this line only ever sees non-strings.

Mutant: `if isinstance(level, float) and level.is_integer():`

**Observable change.** Exactly inverted, and both halves are wrong in the way order
762256b4b844 exists to prevent:

- `escalate(3.0, "C", "W")` — documented at 268 as still meaning SAFETY — is now recorded at
  **MANAGER** with `evidence["unrecognised_level"] == "3.0"`.
- `escalate(2.7, "C", "W")` — the incident shape — sails past the guard to `int(2.7) == 2` and
  becomes a **QUIET `escalate(OPERATOR, ...)`**: a rung of a six-rung chain chosen by a
  truncation nobody was told about. That is verbatim the defect the block was written to refuse.

**Why the battery missed it.** `grep is_integer|2\.7|escalate(3\.0` over `src/drill.py` and
`src/verify_math.py` returns nothing. The existing rung rows at `drill.py:9869-9889` only ever
pass `str` and `int` levels (`"SAFETY"`, `ESC.SUPERVISOR`, `"MANGER"`), all of which are resolved
or handled before line 272 is reached.

**Net that kills it.** A direct sibling of the existing rows, through `_esc_probe`:

```
lambda: _esc_probe(lambda d, f: (
    ESC.escalate(3.0, "C", "W")["level"] == ESC.SAFETY                      # exact float = rung
    and "unrecognised_level" not in (ESC.escalate(3.0, "C", "W")["evidence"] or {})
    and ESC.escalate(2.7, "C", "W")["level"] == ESC.MANAGER                 # truncation refused
    and (ESC.escalate(2.7, "C", "W")["evidence"] or {})["unrecognised_level"] == "2.7")),
```

The `3.0 -> SAFETY` limb alone kills both line-272 mutants; the `2.7` limbs prove the guard is
still doing its job rather than merely being switched off.

---

## G7 (MEDIUM-HIGH) — line 272, `and -> or`: the guard swallows every integral float, and crashes on a non-number

Mutant: `if isinstance(level, float) or not level.is_integer():`

**Observable change**, two distinct ones:

1. **Any float is unrecognised.** `isinstance(3.0, float)` short-circuits the `or` to True, so
   `escalate(3.0, ...)` lands at MANAGER with `unrecognised_level "3.0"` — the same downgrade as
   G6's first half. Killed by the same `3.0 -> SAFETY` assertion.
2. **A non-number level raises out of the alarm path.** For a level that is neither `str` (handled
   at 253) nor float, the `or` evaluates `level.is_integer()`. On CPython 3.13 `int` and `bool`
   have `is_integer()`, so ordinary calls survive — which is exactly why this mutant lived. But
   `escalate(None, ...)`, `escalate([], ...)`, `escalate(Decimal("3"), ...)` now raise
   **`AttributeError` out of `escalate()`**, uncaught: the `try/except (TypeError, ValueError)`
   that was written to catch this class of input begins at line 274, one line *below*. The
   comment at 231-237 describes precisely this shape as the worst kind of bug report — "a
   mutation run then found a real problem, tried to report it, and the alarm crashed instead of
   sounding, taking the whole run's results with it."

**Second net row**, which the current battery has no equivalent of:

```
lambda: _esc_probe(lambda d, f: all(
    ESC.escalate(bad, "C", "W")["level"] == ESC.MANAGER
    for bad in (None, [], object(), b"OWNER"))),
```

Assert it returns a record at MANAGER rather than raising — the documented contract at 244-251 is
that *every* unrecognisable level lands at MANAGER with the bad value in the evidence.

---

## G8 (MEDIUM) — line 419, `exist_ok=True -> False`: the halt lock is never taken, on any write

```
 417:     for _ in range(HALT_LOCK_ATTEMPTS):
 418:         try:
 419:             os.makedirs(os.path.dirname(lock), exist_ok=True)
 420:             os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
 421:             held = True
```

Mutant: `exist_ok=False`.

**Observable change.** `os.path.dirname(lock)` is `state/`, which exists on any live library. With
`exist_ok=False` the call raises **`FileExistsError` about the directory**, which is caught by the
`except FileExistsError` arm at 423 that was written to mean "another writer holds the lock".
That arm then calls `os.path.getmtime(lock)` on a lock file that does not exist, gets `OSError`,
`pass`es, sleeps 0.05s, and loops. All 40 attempts do this. Result, on **every single halt
write**:

- a ~2 second stall before the halt file is touched;
- `held` stays False, so `silence.note("escalation.py:halt-lock-not-taken")` and the
  "HALT LOCK NOT TAKEN" stderr banner fire every time;
- the lock is never created, so the whole exclusion added by order 97cc0dc43ca7 is permanently off
  and the lost-fault race is fully re-opened.

The fail-open design means no halt is lost, which is why nothing red-lit — but a safety that is
switched off on every invocation while printing that it is switched off, and nothing noticing, is
the gap.

Killed by the uncontended row of the G3 net (`got is True` and the lock file exists inside the
`with`). A cheap extra guard: assert `silence` recorded no `escalation.py:halt-lock-not-taken`
note during an uncontended halt write.

---

## G9 (MEDIUM) — line 421, `True -> False`: the lock is taken, disclaimed, and leaked

Mutant: `held = False` after a successful exclusive create, then `break`.

**Observable change.** The lock file **is** created on disk; the function then reports it was not
taken (warning + `silence.note` + `yield False`) and `return`s at 445, so the `try/finally` at
446-450 is never entered and **the lock file is never removed**. Every subsequent halt writer now
contends with an orphan for a full `HALT_LOCK_STALE_SECONDS` (60s) before the staleness steal at
428 clears it — so under any repeat traffic the lock is permanently in the stolen/re-orphaned
state and exclusion never actually holds.

Killed by the uncontended row of the G3 net: `got is True` fails immediately, and the
"lock removed after the `with` block" assertion fails too.

---

## G10 (MEDIUM-LOW) — line 303, drop `not`: the lost-escalation warning inverts

```
 301:     recorded = _append_log(rec)
 302:     rec["recorded"] = bool(recorded)
 303:     if not recorded:
 304:         sys.stderr.write(
 305:             "ESCALATION NOT RECORDED — %s at %s could not be appended to the janitor's log "
 ...
```

Contract, comment at 297-300: *"SAID ON stderr WHEN IT IS False, because by construction it cannot
be said in the log — the log is the thing that just failed."* At rungs 1-4 the log is the whole
enforcement (comment at 291-296).

Mutant: `if recorded:`.

**Observable change.** Purely on stderr, but inverted both ways: the banner is printed on **every
successful** escalation (so the operator console fills with a false alarm that reads as a lost
alarm, and the real one becomes invisible in the noise), and it is **silent on the one occasion it
exists for** — the append genuinely failing. No state, no return value, and no work order changes.

**Why the battery missed it.** `drill.py:9992-10015`
(`a_lost_escalation_says_so_on_the_record`) covers line 302 thoroughly — three rows asserting
`rec["recorded"]` is True / False / False across both append targets — but asserts nothing about
stderr. Severity is held down by exactly that: `rec["recorded"]` still carries the truth to any
programmatic caller, so only the human channel breaks.

**Net that kills it.** Extend the existing probe rather than adding a new one — it already has
`silence.append_line` stubbed to fail:

```
# inside a_lost_escalation_says_so_on_the_record's probe, around each escalate:
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stderr(buf):
    rec = ESC.escalate(ESC.SUPERVISOR, "C", "W", source="S")
# append succeeded  -> banner must be ABSENT
# append stubbed off -> banner must be PRESENT
return ("ESCALATION NOT RECORDED" in buf.getvalue()) is (rec["recorded"] is False)
```

Both directions are needed; asserting only the failure case would leave the false-alarm half live.

---

## G11 (LOW) — line 1379, `or -> and`: a signed resume is recorded as unsigned

```
1379:             ok, reason = resume_subsystem_verdict(a.resume, a.ruling, by=(a.by or "cli"))
```

`--by` defaults to `None` (line 1350, and the comment at 1345-1349 explains there is deliberately
no default). The comment at 1376-1378 says the `"cli"` fallback *names the CHANNEL, which is a
fact, rather than a person, which would be the false statement the `--by` default was removed for.*

Mutant: `by=(a.by and "cli")`.

**Observable change**, and it goes the wrong way on attribution:

- `--resume X --ruling "..."` with no `--by`: `None and "cli"` is `None`, so `by=None`. That
  reaches `escalate(JANITOR, "SUBSYSTEM_RESUMED", ..., who=by)` at line 1043, and `escalate`'s
  `who or os.path.basename(sys.argv[0] or "?")` fills in **`"escalation.py"`** instead of
  `"cli"`. Minor.
- `--resume X --ruling "..." --by alice`: `"alice" and "cli"` is **`"cli"`**. A person who signed
  the resume by name is recorded in `state/escalation.log` as an anonymous CLI. This is the same
  class of defect as order c614f7c145fc — the ledger carrying a false statement about who
  decided — only erasing a true signature rather than inventing a false one.

No gate changes: `by` is not consulted by any check, only written to the record. That is why this
ranks low despite touching a safety lift's attribution.

**Net that kills it.** Line 1379 lives in `main()`, so it must be driven through `main()`. In
process, with the verdict function stubbed to a recorder:

```
def the_cli_resume_records_who_signed_it():
    import escalation as E, sys
    seen = {}
    real, argv = E.resume_subsystem_verdict, sys.argv
    E.resume_subsystem_verdict = lambda n, r, by="?": (seen.update(by=by) or (True, "ok"))
    sys.argv = ["escalation.py", "--resume", "X",
                "--ruling", "a ruling long enough to pass the bar", "--by", "alice"]
    try:
        E.main()
        if seen.get("by") != "alice":
            return False
        seen.clear()
        sys.argv = ["escalation.py", "--resume", "X",
                    "--ruling", "a ruling long enough to pass the bar"]
        E.main()
        return seen.get("by") == "cli"          # channel named, not a person, and not None
    finally:
        E.resume_subsystem_verdict, sys.argv = real, argv
```

Both limbs are needed: `--by alice -> "alice"` kills the mutant, and the unsigned limb pins the
`"cli"` fallback the comment at 1376-1378 argues for.

---

## G12 (LOW, narrow) — line 1324, `False -> True`: a raising lift claims it landed

```
1300: def _land_clear(rec, expected):
 ...
1314:         landed, why = silence.replace_if_unchanged(tmp, HALT_FILE, expected)
1315:         if not landed:
1318:             _unlink(tmp)
1319:         return landed, why
1320:     except Exception as e:
1321:         silence.note("escalation.py:halt-clear")
1322:         sys.stderr.write("CANNOT WRITE HALT FILE while lifting the halt — %s: %s\n" ...)
1324:         return False, "raised"
```

Mutant: `return True, "raised"`.

**Observable change, and why it is narrow.** The caller is `clear()` at 1265-1274:

```
1265:         landed, why = _land_clear(rec, expected)
1270:         if landed and _halt_file_cleared():
1271:             _append_log({... "code": "HALT_CLEARED" ...})
1273:             return True
1274:         landed = False
```

The readback at 1270 (comment 1266-1269: *"READ BACK, AND DO NOT TRUST `landed` ALONE"*) absorbs
almost all of the damage — if the write threw, the file normally still says `cleared: false`, so
`_halt_file_cleared()` is False and the loop simply retries. The mutation therefore changes
behaviour only when `_land_clear` raises **and** the halt file on disk already says cleared,
i.e. a concurrent lift landed in the same window. In that case the original returns False (and on
the next pass `status()` reports not-halted, so `clear()` returns False at 1243-1244), while the
mutant returns **True and appends a `HALT_CLEARED` ledger row** crediting this caller with a lift
whose write raised. The mutant also causes an extra `_read_halt_raw()` on every raising attempt,
where the original short-circuits.

The direction is fail-open on a halt lift, which is why it is listed as a GAP rather than waved
through — but the readback means it cannot on its own lift a halt that is standing.

**Net that kills it.** Unit-level, no concurrency needed — assert the literal pair the `except`
arm is contracted to return:

```
def a_raising_lift_reports_that_it_did_not_land():
    d, filed, restore = _esc_sandbox()
    try:
        os.makedirs(ESC.HALT_FILE, exist_ok=True)   # HALT_FILE is a DIRECTORY: open() raises
        landed, why = ESC._land_clear({"cleared": True}, None)
        return landed is False and why == "raised"
    finally:
        restore()
```

`landed is False`, not falsy. The sibling row for `_land_halt`'s own `return False, "raised"`
(line 590) is worth writing at the same time; that mutant is not in this survivor list, which
suggests it was killed, but the two arms should be covered symmetrically.

---

## G13 (LOWEST, narrow) — line 1297, `False -> True`: a halt record with no `cleared` key reads as cleared

```
1293: def _halt_file_cleared():
1294:     """Does the halt file on disk actually say `cleared` now? -> bool. The readback that makes
1295:     the lift's verdict evidence rather than an assumption."""
1296:     cur = _read_halt_raw()
1297:     return isinstance(cur, dict) and bool(cur.get("cleared", False))
```

Mutant: `cur.get("cleared", True)`.

**Observable change.** A HALT.json that parses to a dict but carries **no `cleared` key** now
reads as cleared. That is the fail-closed default inverted, and it is the same default `status()`
uses one function away (line 641, `return (not rec.get("cleared", False)), rec`) — the two are
meant to agree.

Reachability is genuinely narrow, and I could not construct a path that makes it matter without a
second writer. `_halt_file_cleared()` is called from exactly one place, line 1270, and only when
`_land_clear` reported `landed` True — meaning our own payload, which always carries
`"cleared": True` (set at 1256), is what is on disk. To read a keyless dict back you need another
process to have replaced HALT.json between our `os.replace` and our readback, **and** that
process's payload to lack the key — which `_land_halt` can produce, because on the append branch
(line 546-548) `payload = cur` is passed through unchanged, so a hand-edited or half-written
HALT.json missing `cleared` survives a corroboration append still missing it.

I am ruling this GAP rather than EQUIVALENT because I cannot prove no path reaches it — but the
honest value of a net here is defence-in-depth on a fail-closed default, not a live bug.

**Net that kills it.** Trivially cheap, and worth taking for the price:

```
def the_lift_readback_fails_closed_on_a_keyless_record():
    d, filed, restore = _esc_sandbox()
    try:
        with open(ESC.HALT_FILE, "w", encoding="utf-8") as f:
            json.dump({"code": "X", "what": "a halt record with no cleared key"}, f)
        if ESC._halt_file_cleared() is not False:
            return False
        with open(ESC.HALT_FILE, "w", encoding="utf-8") as f:
            json.dump({"code": "X", "cleared": True}, f)
        return ESC._halt_file_cleared() is True
    finally:
        restore()
```

---

# EQUIVALENT, with the proof for each

## E1 — line 444, `yield False -> yield True` (equivalent *by accident*)

```
 444:         yield False
 445:         return
```

**Proof.** `_halt_lock` has exactly one call site in the whole tree:

```
$ grep -n "_halt_lock" src/*.py
src/escalation.py:390:def _halt_lock():
src/escalation.py:496:    with _halt_lock():
```

(the other three hits are comments, plus one comment in `verify_math.py:7455`). Line 496 is
`with _halt_lock():` — **no `as` binding**. A `with` statement discards the context manager's
yielded value when there is no `as` target. No other code in `src/` calls `_halt_lock`. Therefore
the value yielded at 444 cannot influence any program behaviour, and the mutation is equivalent.

**Caveat, and it matters.** This is equivalence by accident, not by construction. The comment at
492-493 treats the yielded value as load-bearing (*"when it cannot be taken, `_halt_lock` yields
False and every line below runs exactly as it did before"*), and the docstring documents a
two-valued contract. The value is one `as got:` away from being live. The G3 net, which must bind
`as got` to test the lock at all, converts E1 and E2 into killed mutants at zero extra cost —
which is the right outcome: a documented contract that no caller and no test reads is a contract
that will silently rot.

## E2 — line 447, `yield True -> yield False` (equivalent *by accident*)

Same proof as E1: the yielded value is discarded by `with _halt_lock():`. Note additionally that
the mutation does **not** disturb the release — the `try/finally` at 446-450 still runs
`os.remove(lock)` on the way out — so even the disk state is identical. Same caveat and same fix
as E1.

## E3 — line 495, `landed, why = False, "not attempted"` in `_raise_halt`

```
 495:     landed, why = False, "not attempted"
 496:     with _halt_lock():
 497:         for _attempt in range(STOP_CAS_ATTEMPTS):
 498:             expected = silence.digest_of(HALT_FILE)
 499:             landed, why = _land_halt(rec, expected)
 500:             if landed and _halt_file_records(rec):
 501:                 return True
 515:             landed = False
 519:     silence.note("escalation.py:halt-write-denied")
 520:     sys.stderr.write("CANNOT WRITE HALT FILE after %d attempts (%s) — %s: %s\n"
 521:                      % (STOP_CAS_ATTEMPTS, why, rec["code"], rec["what"]))
 522:     return landed
```

**Proof (dead store).** Only `landed` is mutated; `why` keeps its initializer and is read at 520,
unchanged. `_halt_lock` is a generator-based context manager that yields exactly once on both of
its paths (444 and 447), so the `with` body always executes. `STOP_CAS_ATTEMPTS = 5` (line 656) is
a module constant, so `range(...)` is non-empty and line 499 executes at least once, assigning
`landed` **before any read of it**. There is no path from 496 to 522 that skips 499: the only
statements between are the `for` header and 498, and if either 498 or 499 raises, the exception
propagates out of `_raise_halt` entirely (the `finally` in `_halt_lock` only removes the lock; it
does not swallow) and 522 is never reached. Therefore the value at 495 is never read.

Worth noting for contrast: the structurally identical `landed = False` at **line 515 is NOT dead**
— it is what forces `_raise_halt` to return False when `_land_halt` said it landed but
`_halt_file_records` disagreed. That token does not appear in the survivor list, which is the
consistency check: the live one was killed, the dead one survived.

## E4 — line 567, `landed, why = False, "not attempted"` in `_land_halt`

```
 567:     landed, why = False, "not attempted"
 568:     try:
 569:         os.makedirs(os.path.dirname(HALT_FILE), exist_ok=True)
 ...
 578:         landed, why = silence.replace_if_unchanged(tmp, HALT_FILE, expected)
 579:         if not landed:
 583:             _unlink(tmp)
 584:             return False, why
 585:     except Exception:
 590:         return False, "raised"
 591:     return landed, why
```

**Proof (dead store).** Three exits, none of which reads the initializer:

- Anything in 569-578 raises -> 585 -> `return False, "raised"` (both literals).
- 578 completes and `landed` is falsy -> `return False, why` at 584, where `why` came from 578.
- 578 completes and `landed` is truthy -> `return landed, why` at 591, both from 578.

Line 578 is the only statement between 567 and any read, and it assigns both names. A failure
partway through the tuple unpack at 578 (a non-2-tuple return) is an exception and lands in the
`except`. So neither initializer value can reach a reader.

## E5 — line 695, `landed, detail = False, "not attempted"` in `stop_subsystem`

```
 695:     landed, detail = False, "not attempted"
 696:     for _ in range(STOP_CAS_ATTEMPTS):
 700:         expected = silence.digest_of(STOPPED)
 701:         try:
 702:             doc = _read_stopped()
 703:         except Exception:
 705:             landed, detail = False, "state/STOPPED.json could not be read at all"
 706:             break
 707:         if "__unreadable__" in doc:
 713:             landed, detail = False, (...)
 716:             break
 717:         doc[str(name)] = {...}
 719:         try:
 720:             landed, detail = _write_stopped(doc, expected)
 721:         except Exception:
 725:             landed, detail = False, "the temp copy could not be written"
 726:         if landed:
 727:             break
 728:     if not landed:
```

**Proof (dead store).** `range(5)` is non-empty, and **every** way of leaving the first iteration
assigns both names first: the read-failure break (705), the unreadable break (713), and the write
arm (720 or 725), which is reached unconditionally once 707 is false. The only unguarded
statements are 700 (`silence.digest_of`) and 717 (`doc[...] = ...`); if either raises, the
exception propagates out of `stop_subsystem` and neither 728 nor 778 (`rec["stop_recorded"]`) is
reached. So `landed` at 728, `detail` at 733/773, and `landed` at 778 are all fed by an assignment
inside the loop, never by line 695.

## E6 — line 1006, `landed, detail = False, "not attempted"` in `resume_subsystem_verdict`

```
1006:     landed, detail = False, "not attempted"
1007:     for _ in range(STOP_CAS_ATTEMPTS):
1009:         expected = silence.digest_of(STOPPED)
1010:         doc = _read_stopped()
1011:         if "__unreadable__" in doc:
1019:             return False, reason
1020:         if str(name) not in doc:
1024:             return False, "%s was not stopped; nothing to resume" % name
1025:         doc.pop(str(name), None)
1026:         try:
1027:             landed, detail = _write_stopped(doc, expected)
1028:         except Exception:
1030:             landed, detail = False, "the temp copy could not be written"
1031:         if landed:
1032:             break
1033:     if not landed:
```

**Proof (dead store).** This one differs in shape from E5 — it has two early `return`s inside the
loop — but the conclusion holds and for a sharper reason: **both early returns emit literals**
(`return False, reason` at 1019, `return False, "..."` at 1024) and read neither `landed` nor
`detail`. Every path that leaves the loop *without* returning passes through 1027 or 1030, both of
which assign both names. So line 1033's read and line 1040's use of `detail` are always fed from
inside the loop. Line 1006 is dead.

This is the one I most expected to disagree with its siblings, given the early returns; it does
not, because those returns are literal-valued.

## E7 — line 1183, first `or -> and`, in `clear()`

```
1183:     if not ruling or not str(ruling).strip() or len(str(ruling).strip()) < 12:
1184:         raise ValueError("a ruling is required, in words ...")
```

Original is `A or B or C`; mutant is `(A and B) or C` (`and` binds tighter than `or`), where
`A = not ruling`, `B = not str(ruling).strip()`, `C = len(str(ruling).strip()) < 12`.

**Proof for every `str` ruling.** The only falsy `str` is `""`. For `ruling = ""`: `A` True, and
`C` is `len("") < 12` -> True, so both forms are True. For every other `str`, `A` is False, so
original reduces to `B or C` and mutant reduces to `False or C` = `C`; and `B` implies `C`
(if `str(ruling).strip()` is empty then its length is 0 < 12), so `B or C` = `C`. The two forms
agree on every string. `ruling` arrives either from `argparse` (`--ruling`, `default=""`, always a
`str`) or from a programmatic caller passing a ruling, so this covers every reachable input.

**The one theoretical counterexample**, recorded for completeness: an object that is falsy but
whose `str()` strips to 12 or more characters (a custom `__bool__`/`__str__` pair, an empty numpy
array). Original raises on `A`; mutant needs `A and B`, and `B` is False, and `C` is False, so it
would let the lift through to the person check. No such value is reachable from the CLI or from
any caller in `src/`, and I would not spend a net on it.

Note this ruling depends on the survivor being the **first** `or` — see "Citation drift" at the
top. The second `or` is already covered by `drill.py:2782` (`_refuses(lambda: ESC.clear("ok"),
ValueError)`), which is how the ambiguity resolves.

## E8 — line 1239, `landed, why = False, "not attempted"` in `clear()`

```
1238:     first = None
1239:     landed, why = False, "not attempted"
1240:     for _attempt in range(STOP_CAS_ATTEMPTS):
1241:         expected = silence.digest_of(HALT_FILE)
1242:         halted, rec = status()
1243:         if not halted:
1244:             return False
1247:         elif _halt_identity(rec) != first:
1254:             return False
1265:         landed, why = _land_clear(rec, expected)
1270:         if landed and _halt_file_cleared():
1273:             return True
1274:         landed = False
1278:                      % (STOP_CAS_ATTEMPTS, why))
1279:     return False
```

**Proof (dead store).** `why` is not touched by this mutation and is read at 1278. For `landed`:
the two early returns at 1244 and 1254 return the **literal** `False`, reading nothing; the only
read of `landed` is at 1270, and line 1265 assigns it on every path that reaches 1270. And
critically, **`clear()` returns the literal `False` at 1279, not `landed`** — so after the loop
the variable is never read at all. Line 1239's value is unobservable.

## E9 — line 1274, `landed = False` in `clear()`

**Proof.** Mutating to `landed = True`. The statement is the last in the loop body. Two
successors: (a) the next iteration, where the only read of `landed` is at 1270 and line 1265
reassigns it first — and every path from 1241 to 1265 either reaches 1265 or returns a literal
(1244, 1254) or raises; (b) loop exhaustion, after which `landed` is never read, because 1278 uses
only `why` and 1279 returns the literal `False`.

So the whole statement at 1274 is **dead code** — it can be deleted without changing behaviour.

That is worth flagging on its own, because the structurally identical `landed = False` at line
**515 in `_raise_halt` is load-bearing** (`_raise_halt` ends `return landed`, so 515 is what
converts a "landed but the readback disagreed" attempt into a False verdict). The two functions
were written as mirrors — the comment at 1266-1269 explicitly points at `_raise_halt` — and one
of the mirrored lines is live while the other is not. Either delete 1274, or change 1279 to
`return landed` so the mirror is real; the latter is a behaviour change and should be a ruling,
not a tidy-up, since the literal `False` at 1279 is what `main()`'s two-worlds branch at
1415-1430 is written against.

---

# Summary of what to write

Seven nets close eleven of the thirteen GAPs:

1. **`_halt_lock`, contended** (fresh lock present) -> yields `False`, holder's lock survives.
   Kills G3, G4, G5. Converts E1/E2 to killable.
2. **`_halt_lock`, uncontended** -> yields `True`, lock file exists inside the `with` and is gone
   after, and no `halt-lock-not-taken` note was recorded. Kills G4, G8, G9.
3. **`_halt_lock`, stale lock** (mtime backdated past 60s) -> stolen, yields `True`. Kills G3's
   second half.
4. **`resume_subsystem` refuses a program** (real ledger, real subsystem name, both spellings) and
   still exempts the three reserved subjects. Kills G1.
5. **`_a_probe_release` fails closed** with `health` unimportable. Kills G2.
6. **`escalate` float rungs**: `3.0 -> SAFETY` with no `unrecognised_level`; `2.7 -> MANAGER` with
   `unrecognised_level == "2.7"`; `None`/`[]`/`object()` -> MANAGER rather than `AttributeError`.
   Kills G6, G7.
7. **stderr assertion folded into the existing `a_lost_escalation_says_so_on_the_record` probe**.
   Kills G10.

The remaining three (G11 CLI attribution, G12 `_land_clear` raise arm, G13 keyless-record
readback) are each a single cheap row and are described in place.

The dominant finding is structural rather than per-mutant: **`escalation._halt_lock` has no test
coverage of any kind** — seven of the twenty-two survivors sit inside it, and two more
(444/447) are equivalent only because its one caller throws the yielded value away.
