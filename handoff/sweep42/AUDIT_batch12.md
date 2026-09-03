# sweep42 batch 12 — audit

Modules read in full: `src/workorders.py`, `src/silence.py`, `src/scout.py`, `src/sweep_plan.py`,
`src/anchors.py`, `src/render.py`, `src/runguard.py`, `src/propagation.py`.

Special attention per assignment: `workorders.py` (the queue) and `silence.py` (the atomic-write
primitives), specifically for any path where an order could be lost, double-filed, or closed
without a paper trail, and any write path that is not atomic.

---

## CONFIRMED DEFECTS

### 1. `workorders.py:536-539` (inside `resolve()`) — the paper trail itself is appended with a
non-atomic, unlocked text-mode write, exactly the hazard `silence.py` was written to fix

```python
trail = SELFTEST_LOG if (synthetic or is_selftest(rec)) else CLOSED_LOG
try:
    os.makedirs(os.path.dirname(trail), exist_ok=True)
    with open(trail, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
except Exception as exc:
```

This is the write that lands every closed order into `state/workorders_closed.jsonl` (and
`workorders_selftest.jsonl`) — the append-only ledger the whole module's docstring calls "the
paper trail, never a growing backlog" and the one artifact `_mutate`'s extensive CAS work exists
to keep trustworthy on the *open*-queue side. But the close-side write to the append-only ledger
is a bare `open(path, "a")` + `f.write(...)`, not `silence.append_line()`.

`silence.py`'s own docstring for `append_line` (lines 305-360) documents, with measurements taken
on this exact machine on 2026-09-01, that this precise pattern is broken on Windows:

> "the Windows CRT implements `_O_APPEND` as a SEEK-TO-END FOLLOWED BY A WRITE, two operations
> with a gap in the middle. Two processes that both seek to the same end offset both write there,
> and the second does not append after the first — it lands ON it. MEASURED... eight processes
> appending 400 sub-page JSON rows each to one ledger. Expected 3,200 rows. 2,496 arrived, 704
> were destroyed outright, and 3 more were torn into rows that parse as neither writer's. A 22%
> loss rate, silent."

`resolve()` is exactly the kind of write this describes: it is reached concurrently (the whole
point of `_mutate`'s 8-attempt CAS loop a few lines above is that "under twelve agents working the
queue concurrently" is the normal operating condition here), and every one of those concurrent
closers appends its resolution to the *same* `CLOSED_LOG`/`SELFTEST_LOG` file with a plain text
`"a"`-mode write. `silence.append_line` exists specifically to replace this shape with an
OS-level-locked, binary-mode append; `resolve()` was never migrated to it.

Consequence: under concurrent closes (the documented normal case for this queue), rows in
`workorders_closed.jsonl` can be silently destroyed or torn — which is precisely the "closed
without a proper paper trail" failure mode this audit was asked to look for, and it can happen
even when `_mutate`'s CAS on the *open* queue succeeds cleanly.

**Confidence: high.** The defect is a straightforward diff against `silence.append_line`'s own
documented rationale, in the same codebase, describing the identical code shape as broken with
measured numbers.

---

### 2. `workorders.py:734-739` (`_closed_rows()`) — a genuinely unreadable closed log is silently
treated as an EMPTY one, with no `silence.note()`, unlike every sibling read-path in this file

```python
def _closed_rows():
    """Every parseable record in the paper trail, oldest first."""
    try:
        fh = open(CLOSED_LOG, encoding="utf-8")
    except OSError:
        return
    with fh:
        for line in fh:
            ...
```

`except OSError` catches far more than "the file has never been created" (`FileNotFoundError`,
which *is* the honest-empty case) — it also swallows permission errors, a file held open/torn by
a concurrent writer mid-replace, disk errors, etc., and in every one of those cases this generator
silently yields nothing, with no call to `silence.note()` anywhere on this path. Per `silence.py`'s
own audit criteria (`_handler_is_observed`), a bare `except OSError: return` with no recorder call
and no re-raise is exactly the SILENT shape the whole `silence.py` module exists to eliminate.

This is a direct inconsistency with the rest of the same file:
- `_load()` (lines 279-325) explicitly draws the "three states, not two" distinction for the open
  queue: "FileNotFoundError alone means absent, and absent is honestly empty. Any other failure
  means UNREADABLE and raises" — with an extended docstring on why collapsing that distinction
  previously deleted a whole queue.
- `cap_boundary_scan()`'s own read of the *same* `CLOSED_LOG` file (lines 643-665) catches only
  `FileNotFoundError`, letting any other failure propagate.

`_closed_rows()` is the odd one out, and it is not a cosmetic path: it backs `closed_at()`, which
backs `ghost_orders()` — the detector this file added specifically to catch "a closed order came
back open," i.e. exactly the "closed without a paper trail" failure class this audit was pointed
at. If `workorders_closed.jsonl` is transiently unreadable (e.g. torn mid-write by defect #1
above, or held open by a concurrent reader), `ghost_orders()` will report **zero ghosts** — a
clean bill — precisely when the paper trail it is supposed to check is damaged and cannot
actually be read. This is the "a check that cannot fail looks exactly like a check that passed"
shape this project's own `CLAUDE.md`/HARD RULE -1 names as the standing lesson.

**Confidence: high.** The asymmetry with `_load()` and `cap_boundary_scan()` in the very same file
is direct and the consequence (a load-bearing detector going silently blind) is concrete.

---

### 3. `scout.py:161` (`_mutate()`) — the CAS temp-file name omits the thread id, the identical
shape already found and fixed in three sibling modules

```python
tmp = "%s.%d.%d.tmp" % (path, os.getpid(), a)
```

Compare:
- `workorders.py:373` — `"%s.%d.%d.%d.tmp" % (OPEN_FILE, os.getpid(), _th.get_ident(), a)`
- `runguard.py:123` — `"%s.%d.%d.tmp" % (path, os.getpid(), _th.get_ident())`
- `silence.py:691` (`write_json`) — `"%s.%d.%d.tmp" % (path, os.getpid(), _th.get_ident())`

All three carry the thread id specifically because of a defect this project already found and
documented (`workorders.py`'s own comment at the `_mutate` docstring, order c5431186cc05): "two
THREADS of one process on the same attempt opened the same scratch file and interleaved their
writes." `scout.py`'s own hand-rolled `_mutate` — which guards `SCOUT_ATTEMPTS.json`,
`SCOUT_BLOCKED.json`, and (via `feats.HOSTS`) the shared wiki-host adoption map — was written the
same day as `workorders._mutate` and `runguard._land_claim` per its own docstring ("`workorders
._mutate` and `runguard._land_claim` were both given this same treatment the same day, over the
same primitive"), but its temp name was never given the thread-id fix its siblings got.

Under two threads of one process both calling `scout._mutate` for the same target file and landing
on the same retry attempt number `a`, both would open the identical temp path
(`path.<pid>.<a>.tmp`) and could interleave their `json.dump` writes into it — corrupting the
staged copy before `silence.replace_if_unchanged` ever runs, or causing one thread's write to be
silently discarded to disk. `sweep_plan.py:300` (`record()`'s aggregate-fallback tmp) has this
same pid-only shape and is a secondary, lower-confidence instance of the same gap.

**Confidence: medium-high.** The code shape is a verbatim match to an already-fixed defect
elsewhere in this exact project. I could not confirm from these eight files alone whether
`scout._mutate` is ever actually invoked by more than one thread of a single process (its
callers — `foreman.py`'s scheduling loops — are outside this batch), so I cannot certify current
exploitation, only that the guard the rest of the project installed against this exact failure
mode is absent here.

---

## QUESTIONS (may be deliberate; not filed as fixes)

### Q1. Console-display truncation without a "cut here" marker, in three places

- `workorders.py:1436` — `r.get("what", "")[:70]` in `main()`'s open-queue printout.
- `render.py:298` — `v["url"][:64]` in the diagnostic tier table printed by `main()`.
- `propagation.py:226` — `a[:19]` / `b[:19]` in the sample-distance survey printed by `main()`.

Per `CLAUDE.md` HARD RULE 0, "`[:N]` on a printed... string" is named explicitly as a finding
shape, and none of these three carry an ellipsis or an "(+N more)" marker, so a reader cannot tell
from the printed line alone that anything was cut. However, this same codebase's own extensive
commentary elsewhere (e.g. `workorders.py`'s `file_order`/`resolve` docstrings, discussing the
2026-08-28 cap removal) explicitly argues that a cut *at the console-print call site* is the one
place a cap is legitimate, because it is reversible — the full value is preserved in the
underlying JSON/return value in all three cases (the full order is in `state/workorders.json`,
the full URL is what `view()` returned, the full shelf name is the literal probe-list constant).
None of these three feed a decision, a filed record, or a persisted artifact — they are ad hoc
CLI-diagnostic formatting only.

I'm not confident whether this counts as the "console renderer... which is where a cap belongs"
exception the codebase's own doctrine carves out, or as a genuine (if minor) instance of the
"and N more" omission HARD RULE 0 calls out by name. Flagging for a ruling rather than fixing.

### Q2. `sweep_plan.py:199` / `:300` — CAS/fallback temp names without a thread id

Same shape as confirmed defect #3, but lower confidence here because `sweep_plan.py`'s own
docstring for `record()` states the intended topology explicitly: one process per batch, never
multiple threads of one process calling `record()` for the same run/batch. If that topology holds
in practice, the missing thread id is inert. Flagging alongside #3 for consistency, since the
project has twice already been surprised by "this only happens under a topology I didn't expect"
for this exact temp-naming shape.

---

## Coverage

Recorded via `sweep_plan.record('run42', [...], batch=12)` per instructions.
