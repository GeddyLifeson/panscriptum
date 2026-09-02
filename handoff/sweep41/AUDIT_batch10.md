# Sweep41 — Batch 10 audit

Modules assigned: `src/publish.py` (1604), `src/health.py` (955), `src/ledger_guard.py` (641),
`src/zfighters.py` (537), `src/axis_correlation.py` (416), `src/genre.py` (339), `src/physics.py`
(305), `src/cosmology_graph.py` (261). Total 5,058 lines. All eight read in full, start to end,
no sampling.

Coverage recorded via `sweep_plan.record('run41', [...8 files...], batch=10)`.

## Findings filed

### MAJOR — order `5bbbb65e7787` — HEALTH_FAILURES_LEDGER_POLLUTED_BY_DRILL_SELFTEST

`state/failures.json` — the ledger `health.py` owns and a person reads to find real faults — is
silently polluted by `drill.py`'s own self-test escalations, every battery/drill run, forever.
`drill.py`'s park and rung-4 nets call the REAL `escalation.escalate()` /
`stop_subsystem()` / `resume_subsystem()` against synthetic subjects (`__drill_area__` via
`DRILL_AREA`, `__drill_rung4__`, `__drill_rung4b__`, `__drill_litter_probe__`) rather than a
mock, and `escalation.escalate()` unconditionally calls `health.record(...)` at
`escalation.py:248` with no awareness of the `__drill*__` synthetic-subject convention.
`workorders.py` already hit this *exact* shape on its own paper trail — its header records "eight
ids were 49.0% of the trail... 62.6% one day later" — and was fixed with a `SELFTEST_SUBJECT`
regex filter plus a separate `workorders_selftest.jsonl` log. `health.record()` /
`escalation.escalate()` never got the equivalent treatment.

Verified live, not merely reasoned about: I read `state/failures.json` and counted 7 of 67 keys
and 42 of 4,054 total events as drill rehearsal noise today, e.g.
`escalation:SUPERVISOR:DRILL_AREA:drill: one area closing`: 6,
`escalation:MANAGER:SUBSYSTEM_STOPPED:__drill_rung4__ stopped: ...`: 6, and four siblings — each
incrementing by exactly 1 per drill/battery run, unbounded, with nothing distinguishing a
rehearsal count from a real MANAGER-rung subsystem stop or SUPERVISOR-rung area closure short of
recognising the `__drill__` name by eye.

This matches the batch brief precisely: a rehearsal writing into the ledger a person reads to
find real faults. Fix belongs at the `escalate()`/`health.record()` boundary (health.py itself
cannot filter what escalation.py chooses to hand it) — mirror the `SELFTEST_SUBJECT` convention
workorders.py already proved: skip `health.record` (or route to a `*_selftest` ledger) for any
subject/name matching drill.py's reserved `__drill[A-Za-z0-9_]*__` pattern. Filed MAJOR/RUN.

### MAJOR — order `f7b611d107cb` — LEDGER_GUARD_SEAL_APPEND_NOT_CONCURRENCY_SAFE

`ledger_guard.seal()` still lands each new hash-chain link with a bare
`open(CHAIN, "a", encoding="utf-8")` + `f.write(...)` (`src/ledger_guard.py:257-259`) — exactly
the unsafe append pattern this project measured losing data under concurrency **today**, in this
same file's own docstring (`_read_chain_lines`, ~line 439): "eight concurrent writers against an
O_APPEND ledger lost 704 of 3,200 rows and tore 3 more... because the append is a seek-then-write
rather than an atomic one" on Windows.

`silence.append_line(path, text)` was built and landed this same day specifically to fix this
exact class of loss — OS-level exclusive locking via `msvcrt.locking` (Windows) / `fcntl.flock`
(POSIX) held for the write, plus `O_BINARY` so the CRT cannot silently expand LF to CRLF — and it
is a drop-in replacement for `seal()`'s chain write. Confirmed by grep: `ledger_guard.py` has no
reference to `append_line`, `msvcrt`, `fcntl`, or any lock — the read side
(`_read_chain_lines`) was hardened this session to detect a *torn* line (per-line JSON-parse
failure → reported as `unparseable`, fails the chain), but the write side that actually produces
the corruption was not touched.

This is not hypothetical for this specific file: `publish.push()` calls
`ledger_guard.assert_intact()` → `seal()` before every push, and `publish.py`'s own module
docstring documents that TWO writers are *deliberately* permitted to publish concurrently — the
standing `--loop` daemon and a hand-run one-shot `--push` — which is precisely the concurrent-
append scenario measured to lose data. Traced the failure mode through: a *torn* line is caught
(unparseable → fails). A *cleanly lost whole line* (the majority of the measured loss — 704 of
707) is a different shape: if two concurrent `seal()` calls both compute their link against the
same prior `prev` digest (both read `read_chain()` before either wrote) and one write is
destroyed outright by the other's non-atomic seek-then-write, the surviving link's stored `prev`
still matches the true predecessor in the file — `verify_chain()`'s BROKEN LINK and SHRANK checks
have no way to see the vanished seal at all, and "ok, N link(s) verify" prints truthfully over a
chain missing a checkpoint. That is a check-that-cannot-fail on the exact loss mode this module's
own docstring says was measured on this machine today, on the tamper-evident chain that gates
every push to the public repo. Filed MAJOR/RUN; fix is mechanical (route the CHAIN write through
`silence.append_line()`).

## Also examined, not filed (verified clean / already covered)

- **`publish.py`** (1604 lines, full read): extremely heavily hardened already by today's work
  (three atomic marker writes, `assert_clear` re-asked every loop cycle, `maintenance_shift_live`,
  the mutation interlock checked on both sides of the tree copy, `PushHeld` as its own exception
  class, `_unpushed()` reading the remote-tracking ref rather than trusting a clean worktree,
  `scan_for_secrets` streaming every file with no size skip). No new defect found. One thing
  noted but not filed: `snapshot()`'s own comment ("Whether `dashboard.PAGE` ever surfaces this
  key is its own question") flags an open design question about whether
  `standards_unavailable` is ever rendered — but `dashboard.py` is outside this batch and the
  comment already marks it as unresolved/out of scope rather than a silent defect, so I did not
  chase it into another batch's module.
- **`zfighters.py`** (537 lines): hand-typed roster plus mechanics; atomic gated write, provenance
  defaults handled for the Son Goku sheet carried in from a different file, `--full` wraps rather
  than truncates citations. No defect found.
- **`axis_correlation.py`** (416 lines): today's fix (single `load()` per `widening()` call
  instead of 55) verified in place; `_no_matrix` fires once per site, not once per pair; `widening()`
  floors `total` at `1e-12` before `sqrt`, so no domain error is reachable. No infinite/NaN escape
  found.
- **`genre.py`** (339 lines): Hard Rule 0 fixes verified (`top` defaults to the whole ranked list,
  `cap` raises rather than truncating silently, `Counter` construction guarantees every genre is
  scored so `most_common(None)` is never partial). No defect found.
- **`physics.py`** (305 lines): every entry point (`kinetic`, `joules_for`, `sphere_volume`,
  `binding_energy`) checks its inputs AND its result for `math.isfinite`, refuses NaN/negative/
  infinite arguments with a named `ValueError` rather than propagating `inf`/`nan` into a band
  edge. This is exactly the "infinite escaping as a real result" shape the batch brief called out
  for this file, and it is already closed on every path I traced. No defect found.
- **`cosmology_graph.py`** (261 lines): Hard Rule 0 fixes verified (`shared_sample` uncapped,
  `pairs_filtered: False` stated in the artifact, atomic gated write). Weight formula
  `1/log(n+1.5)` cannot divide by zero or log a non-positive number since `n >= 2` by
  construction. No defect found.
- **`ledger_guard.py`**: beyond the filed finding, re-checked every other mechanism for a sibling
  of today's netted `_read_snapshot`/`_snapshot_path` bug — `check_append_only`'s
  `_one_insertion` (LCP+LCS covering `old` fully), `check_structure`'s order-independent section
  bounding, and `verify_chain`'s unit-mixing guard (`chars` vs `bytes` across the pre/post
  order-016fcf397818 boundary) all read correctly against their own worked examples. No further
  "check that cannot fail" found.
- **`health.py`**: beyond the filed finding, `flush()`/`_flush_ledger()`/`_flush_samples()`'s
  compare-and-swap re-read-and-re-merge logic, the corrupt-ledger preserve-as-`.corrupt` paths,
  and `preflight()`'s stamp-denial reporting were all read against their own documented incidents
  and check out. `reopen_stranded()` and `check_state()` both route through the single
  `pipeline.entry_settled` predicate as their docstrings claim (verified by reading
  `pipeline.py`'s `entry_settled`/`batch_settled` is out of this batch's scope, but the call sites
  here are consistent). No defect found beyond the filed one.

## Decided NOT to file, and why

- The `snapshot()` open question about `standards_unavailable` surfacing in `dashboard.PAGE`
  (publish.py) — the module's own comment already marks it as an open question rather than a
  claimed guarantee, and confirming it needs `dashboard.py`, which is outside this batch.
  Flagging here for whichever batch covers `dashboard.py` rather than filing a cross-batch order
  on unverified ground.
- Did not re-file any of the pre-existing open orders already covering this batch's files
  (checked `state/workorders.json` for `LEDGER_GUARD_*`, `HEALTH*`/`FAILURES*`, `PUBLISH_*`,
  `AXIS_CORRELATION_*`, `GENRE*`, `COSMOLOGY_GRAPH_*`, `PHYSICS_*` — none overlap the two new
  findings above).

## Battery / drill

Not run against the live tree per the batch's hard constraint. Relied on the context-supplied
"drill 378 nets / 0 BREACHED, pyflakes clean" baseline and on reading `state/failures.json`
directly for the health.py finding's live evidence.
