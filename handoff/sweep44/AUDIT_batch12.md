# Audit batch 12 — run44

Modules read in full, top to bottom: `src/workorders.py` (1527 lines), `src/health.py` (973),
`src/custodes.py` (689), `src/codewatch.py` (578), `src/policy.py` (476), `src/genre.py` (338),
`src/style_audit.py` (314), `src/descending_ladder.py` (226). 5,121 lines total.

Overall impression: this is a heavily self-audited slice of the tree. Nearly every historical
defect class this sweep looks for (silent caps, swallowed exceptions, inverted guards, lost
writes) has already been found here at least once and is now documented in-line with an order
number, a measurement, and a fix. The two findings below are genuinely new; everything else I
checked either matched its own documentation or was already filed and is confirmed present.

## Findings

### 1. `src/workorders.py:479-481` — `is_selftest()`'s first branch is dead code; no writer in the
tree ever sets the field it tests for

```python
def is_selftest(rec):
    ...
    if rec.get("synthetic"):
        return True
    return bool(SELFTEST_SUBJECT.match(str(rec.get("where") or "")))
```

The docstring (lines 459-476) says an order counts as a self-test "if it was FILED as one or
CLOSED as one," and cites `rec.get("synthetic")` as the mechanism for the filed case, matching
the drill's blast-cap order (`LOCAL_AGENT_BLAST_CAP`) since that one carries `where=""` and can't
be caught by the `SELFTEST_SUBJECT` regex.

But nothing in `src/` ever stores a `"synthetic"` key on an order record. `file_order()`'s
`_change()` closure builds the stored dict explicitly (lines 440-446) and it has no `synthetic`
field, and there is no `file_order(..., synthetic=...)` parameter for a caller to set one. I
grepped the whole tree for any assignment shape that could put it there (`["synthetic"] =`,
`.setdefault("synthetic"`, `"synthetic": True`) and found nothing. The only place `synthetic`
appears as data rather than as a keyword argument is inside `resolve()` itself (line 484's
parameter and line 535's `synthetic or is_selftest(rec)`), and that parameter is never merged
into the record before `is_selftest(rec)` is called on it — `_change()`'s `rec.update(...)` at
line 513 adds `resolved_at`/`resolution`/`resolved_by` only.

So `rec.get("synthetic")` can only ever read `None` in the current codebase, and the branch can
never return `True`. The real work of separating the drill's rehearsal closes from genuine ones
is done entirely by the `synthetic` keyword argument at the `resolve()`/`resolve_code()` call
site (which does work correctly — `drill.py:3090` passes `synthetic=True` and that value is
consulted directly via the `synthetic or is_selftest(rec)` expression, not through the record).
Behavior today is correct because of that `or`; what's broken is the *other* half of the
documented mechanism, and if `is_selftest()` were ever called on its own (as a filter over loaded
records, for instance, the way `cap_boundary_scan()` filters the open queue) rather than always
paired with an explicit `synthetic=` argument, a hand-marked "this is a rehearsal" record would
silently fail to be recognized as one.

This is exactly the shape the project's Hard Rule -1 calls out — "a check that cannot fail looks
exactly like a check that passed" — except here it's a branch that can never pass, sitting next
to one that does the real work, in code whose whole subject is not losing track of which closures
are real.

**Confidence: high** (verified by reading `file_order`, `resolve`, and every reference to
`synthetic` in `src/`). **Severity: low-to-moderate** — no observed present-day misbehavior, since
the only production caller of `resolve()` with an intent to mark self-tests already passes
`synthetic=True` directly; this is latent dead code plus a docstring overstating what the
function actually checks.

### 2. `src/policy.py:323` and `:369` — exception text is truncated at a fixed producer-side cut
with no "+N chars" marker, inconsistent with this file's own fix for the same class of bug

```python
# main(), record-read loop, line 323:
unreadable.append((os.path.basename(p), "%s: %s" % (type(e).__name__, str(e)[:70])))
```

```python
# _sweep_one(), evidence-cache sweep, line 369:
return (subject, "%s: %s" % (type(exc).__name__, str(exc)[:70]))
```

Both cut an exception's `str()` at 70 characters, unconditionally, with no marker if the cut
actually removed anything and no full copy kept anywhere. Neither `unreadable` nor `ev_unreadable`
is ever written to `state/policy_report.json` — both are console-only (the `report()` call at
line 396 only sends `evidence_unreadable: len(ev_unreadable)`, a count, into the stored scope) —
so this is not a Hard-Rule-0 violation against a stored/ordered listing the way the fixed caps
elsewhere in this file were. But it is precisely the exception-truncation-with-no-marker pattern
this same project has filed and fixed multiple times elsewhere (`health.py` order 7d85937fc436,
`workorders.py` order e6385a07a3fd, `health.py` order f767adf965f0 — all specifically about not
cutting the one sentence that explains *why* a read failed), and this file's own `_observed()`
helper forty lines above (lines 105-126) is the fix for that exact class, done correctly: it
declares its bound, and if it has to shorten a value it says so — `"... (+%d chars)"`. The two
spots above don't get that treatment, so an operator reading `UNREAD some_file.json
JSONDecodeError: Expecting value` (say, if the useful part of the message — the byte offset, the
line/column — landed past character 70) has no way to know the message was cut versus that being
the whole exception text.

**Confidence: high** that the cut exists and is inconsistent with `_observed()`'s pattern in the
same file. **Severity: low** — this is diagnostic-only text for a single run's console output, not
a stored artifact, so nothing is silently lost from any file on disk; the harm is a debugging
detour if the truncated 8 characters happened to matter, not a wrong verdict or a lost order.
Worth an easy fix (route both through something like `_observed()`, or at minimum add the
`(+%d chars)` marker) for consistency with the rest of the file's own stated discipline.

## Confirmed present, not re-filed

- `src/health.py:591`, inside `check_caches()`: `if len(files) < 25: continue` — present exactly
  as described, order e296ea51a1d9. I read the whole of `check_caches()` and the rest of
  `health.py`'s CHECKS list looking for the same shape (a directory-count threshold silently
  exempting a host from the emptiness check) recurring elsewhere in this batch's files, and did
  not find it repeated — it appears to be a single instance, not a wider pattern in these eight
  modules.
- `src/codewatch.py` — `runs_script()`, `twins()`, and `claim_singleton()` all fail open exactly as
  their own docstrings describe (missing `cwd` on a relative path; `psutil` absent or the process
  table unwalkable; either failure finds no twins and lets the daemon start). I read the whole
  file looking for *other* fail-open paths beyond these three named ones and didn't find any that
  weren't already reasoned through inline and treated as a deliberate degraded mode rather than an
  "I don't know" being read as "fine" — `_ledger_lock()`'s fallback to proceeding unlocked after
  exhausting its retry budget is the closest candidate, but it's about losing mutual exclusion on
  an advisory lock file, not about answering an unknown fault state with silence, and it's already
  argued for in its own docstring (an occasional missed restart-count is cheaper than a daemon
  stuck forever on old code because a stale lock file never got cleaned up).

## Everything else checked and found clean

`custodes.py`, `genre.py`, `style_audit.py`, and `descending_ladder.py` were read in full with no
new findings. All four are unusually well-instrumented against their own past failures — every
`[:N]` slice, truncating default, or asserted invariant I checked either had an explicit
in-code argument for why it's safe (e.g. `descending_ladder.py`'s domain-boundary checks in
`rung_for_length()`, which correctly return `(None, None)` outside the ladder's range on both
ends rather than silently rounding into the nearest rung) or was a previously-filed-and-fixed Hard
Rule 0 violation with its own order number and measurement still in the comment. In particular:

- `custodes.py`'s `table_faults()` (checking for a zero-tilt Custos with a nonzero
  `evidence_sensitivity`, which would be numerically inert) is itself an example of the "guard
  that cannot fail" class done *correctly* — it computes the fault from the same arithmetic
  `_custos_reading()` uses rather than asserting it, and both zero-tilt Custodes in the table
  today (Threnody, Lumen) correctly declare `evidence_sensitivity=0.0` so the check reports clean.
- `genre.py`'s `classify_text`/`classify_source` both refuse a nonzero `cap`/`top` argument at the
  call site (`raise SystemExit`) rather than silently truncating, which is the load-bearing fix
  for the Marvel post_apocalyptic/mythology misclassification this file documents.
- `style_audit.py`'s `_cut()` helper is used consistently across all four of its rankings
  (opening shapes, exact openers, machine tells, heavy vocabulary) to label a truncated ranking
  honestly; I checked each of the four call sites and none silently drops a remainder any more.
- `workorders.py`'s `_mutate()`/`resolve()`/`file_order()` compare-and-swap and ordering logic
  (write-then-append for closes, `landed` checked before `rec is None` when resolving) all matched
  their own extensive docstrings on a close read; I specifically checked for anything that could
  lose or misroute an order in the queue's shared-state paths per this batch's brief and did not
  find one beyond finding #1 above.
