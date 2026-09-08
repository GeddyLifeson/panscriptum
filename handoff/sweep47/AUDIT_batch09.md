# Sweep 47, Batch 09 — Audit

Scope: `src/magnitude.py`, `src/corpus_db.py`, `src/thread_integrity.py`, `src/autostart.py`,
`src/axis_correlation.py`, `src/sweep.py`, `src/wh40k.py`, `src/tuning.py` — every line of each,
read in full, no sampling. Plus `src/workorders.py` (2,020 lines, read in full), per the
orchestrator's explicit instruction to give the day's fresh `reroute()`/filing-time-reroute code
closest attention even though it is not in this batch's module list.

Coverage: **all 9 files above read in full, start to end, with no skipped ranges.** Nothing else
was opened except brief cross-references noted below (grep-only, not full reads): `local_agent.py`
(to check `_denied_target`'s basename handling and the DENYLIST contents), `cascade_bridge.py`
(grep only, to locate `POOL_PROOF.json`'s writer — not read in full, out of batch scope).

## Already-open work orders against this batch's modules — status

All of the following were re-examined against the CURRENT source. None was re-filed; none was
found closed. Two things worth flagging explicitly:

- **`8c354f6c9780` (AUTOSTART_TWIN_WATCHDOG_FAILS_OPEN_SILENTLY)** — the order's own restored text
  already records that sweep35 and sweep37 found this **stale in its "SILENTLY" half**:
  `_twin_watchdog()` (autostart.py) now retries `TWIN_TRIES=4` times and writes an explicit
  `"FAILED OPEN: ..."` line to `autostart.log` on both failure branches (psutil/codewatch import
  failure, and a process-table read failure after retries) before conceding. Independently
  confirmed by reading the current code: the fail-open path is no longer silent. What remains
  genuinely open is the *design* question the order's title undersells — fail-open vs fail-closed
  at boot — which is explicitly left to the owner in the code's own comments. Not re-filed;
  flagging here per the brief's "if you find one is already fixed, say so" instruction, since the
  order is partially stale.
- **`b57e23204f66` (AXIS_CORRELATION_FALLBACK_VALUE)** — same pattern: the *loudness* half is
  fixed (`_no_matrix()` now stamps `MATRIX_FALLBACK_REASON`, notes to the ledger, and prints to
  stderr once per process), confirmed present in current `axis_correlation.py`. The *value*
  question (0.0 vs the measured mean) is explicitly left standing as an owner ruling in the
  code's own docstring (`rho()`), consistent with the order still being open for that half only.
- All other listed orders (`de43fe54feb7`, `2cb8756deb0a`, `a724ec57e0d5`, `9038da917a70`,
  `0058f581b42b`, `4e7f1e47d0a0`, `f90795d5c6bd`, `0922effae314`, `88a5f9192e1b`, `5c962f306e58`,
  `2b695c192470`, `5a0c4196142f`, `82fc93f056d4`, `b813fc5a37e2`) were checked against current
  source (several by reading their full stored `what` text) and all describe conditions still
  verifiably true in the code today. None is stale. `2cb8756deb0a`
  (CODEWATCH_UNCOVERED_JOBS_OUTSIDE_THE_KEEPER) is confirmed still true for `magnitude.py`
  specifically: `grep -n codewatch src/magnitude.py` returns nothing — `run_batch()`/`calibrate()`
  are long-lived jobs with no `codewatch.stamp`/`exit_if_stale` call site.

## New findings filed

### 1. `CORPUS_DB_SQL_CRASHES_ON_MISSING_INDEX` (id `7e81ccefa1c6`, LOCAL, MINOR)

`corpus_db.main()`'s `--sql`/`--canned` branch calls `query(sql)` with **no guard** for whether
`state/corpus.db` exists or is openable — unlike its sibling branch three lines above (the
`if not sql:` case), which already asks `freshness()` and prints a clean `"corpus.db NOT USABLE
-- ..."` message. `query()` opens the DB via `connect(readonly=True)` →
`sqlite3.connect("file:...?mode=ro", uri=True)`, which raises `sqlite3.OperationalError: unable
to open database file` when the target is absent — uncaught, all the way out of `main()`.

**Verified by direct execution** (not inferred): with `corpus_db.DB` pointed at a nonexistent
path, both a bare `corpus_db.query(corpus_db.CANNED["coverage"])` call and a full
`corpus_db.main()` invocation under `sys.argv=["corpus_db.py","--canned","coverage"]` raise the
uncaught `OperationalError`. This is very likely the **first command** a fresh checkout's user
runs (before ever running `--rebuild`), and it is the one call site in an otherwise fastidiously
self-documenting module (every other failure path — `rebuild()`, `drift()`,
`datasette_metadata()`, `age_seconds()`, `freshness()` — fails with a named, actionable message)
that lacks the guard its own neighbouring branch already applies three lines earlier.

Fault shape: a check that exists right next to the crash site and is simply not reached on this
path — closest to "a guard that fails open" in effect (crashes instead of degrading to the
established informative-failure convention), though the underlying mechanism is a missing
try/except rather than an inverted one.

### 2. `WORKORDERS_REROUTE_NOOP_REPORTS_AS_SUCCESS` (id `1ba189fabcaa`, LOCAL, MINOR)

Closest scrutiny was given to today's new `reroute()` function and the filing-time
denylist-reroute check in `file_order()`, per the orchestrator's explicit instruction. Findings
on the three specific questions asked:

- **Does `reroute()` preserve id/first_seen/seen/evidence?** Yes, verified by reading `_change`:
  it mutates only `rec["handler"]` and appends to `rec["found_by"]`; every other key is untouched,
  and the docstring's claim is accurate.
- **Can the silent re-address at filing time (`file_order`'s `handler == "LOCAL"` block) hide a
  genuine routing fault?** No defect found. `_denied_target()` bases its check on the path's own
  basename, so `WHERE_TARGET`'s raw (possibly directory-prefixed) matches are handled correctly
  regardless of whether `where` spells a bare filename or a `src/...` path. The override is
  transparent — it is written into `found_by` verbatim, including the reason — so it does not
  hide anything from a reader of the order; it is belt-and-suspenders with the independent
  post-hoc detector `ORDER_ADDRESSED_TO_A_RUNG_THAT_CANNOT_REACH_IT` in `sweep_detectors()`, which
  would still catch a case where this filing-time check could not run (e.g. `local_agent`
  unimportable).
- **Can the new CLI's error paths leave the queue half-written?** No. `_mutate()`'s
  temp-file-plus-compare-and-swap discipline is used uniformly by `reroute()` exactly as by
  `resolve()`/`file_order()`, and `main()`'s `--reroute` branch mirrors `--resolve`'s careful
  three-way disposition (landed-and-changed / lost-write-still-open / genuinely-absent) using the
  same `still_open = a.reroute in (_load() or {})` re-check pattern, including the same
  `QueueUnreadable` handling. No half-written-state path was found.

**What WAS found**, verified by reading `reroute()`'s `_change` closure and `main()`'s
`--reroute` handler: when `--to RUNG` names the rung an order is **already** on, `_change` takes
the `if old == handler: return rec` branch — no `found_by` note, no state change — and `main()`
prints `"rerouted <id> -> <RUNG>"` regardless, exactly as it would for a genuine move. Nothing in
the return value, on stdout, or in the order's own audit trail distinguishes "this just moved"
from "this was already there and nothing happened." This is the same class of ambiguity
`resolve()`'s own docstring explicitly reasons about avoiding for its own two cases
("a caller cannot tell 'already closed' from 'your close was lost' if both come back the same
way") — the analogous distinction for `reroute()` was not given the same treatment. Filed as
MINOR/LOCAL: it does not corrupt the queue or lose data, but it makes a redundant reroute call
(e.g. from a remediation pass whose own analysis is stale, or two lanes independently deciding an
order is misrouted) indistinguishable from a real one, both on the terminal and in the paper
trail.

## Notable things that are NOT findings (checked and cleared)

- `axis_correlation.py`: cross-checked the docstring's factual claims against the live data files
  — confirmed 0 of 507 `data/ASSAYS.json` rows currently carry `result.scores` with ≥2 entries
  (matching the docstring's "still 45 [entities]" claim exactly), and confirmed exactly one
  entity-name collision (`Son Goku`) across the eight `SOURCES` files, which is not remotely
  enough to be worth filing as a correlation-measurement concern.
- `sweep.py`: confirmed `sweep.load` and `sweep.cache_path` are genuinely callerless as their
  docstrings claim (`grep -rn` across `src/`), and `--top`'s single capped table is the
  documented, explicit-request exception to Hard Rule 0 (not a silent truncation).
- `wh40k.py`: the provenance-tagging mechanism `82fc93f056d4` describes as needing a curatorial
  pass is implemented correctly as described (2-tuples → `unattributed`, 3-tuples → their own
  tag); the remaining gap is exactly the curatorial pass itself, which the order already names.
- `thread_integrity.py`: `_charter_codes()`'s three-way absent/corrupt/wrong-shape handling,
  `load_thread_graph()`'s fail-closed `ThreadGraphUnreadable`, and the `_floor_verdict()` ratchet
  were all read closely for a "confident value from could-not-measure" shape and none was found —
  every failure path is already named and escalated rather than defaulted silently.
- `magnitude.py` (1,959 lines, the largest file in the batch): read for the recurring fault
  shapes across all five verification guards, `_split_assay`/`_split_gate`, `calibrate()`'s
  resume/checkpoint logic, and `run_batch()`'s tally/requeue logic. No new defect found — this
  file already carries an unusually high density of prior fixes with detailed incident writeups,
  and the transport-fallback logic (`used` tracking across pool → local → split) was traced
  carefully for a stale-label risk and found consistent: `used` is always reassigned to the
  transport actually attempted before being reported.
- `tuning.py`, `autostart.py`: read in full; no new findings beyond the one status note on
  `8c354f6c9780` above. `tuning.workers()`'s previously-documented zero-vs-None bug is confirmed
  fixed in current code (`min(requested, n) if requested is not None else n` correctly handles
  `requested=0`).

## Coverage record

`sweep_plan.record('run47', [...8 module basenames...], batch=9)` was run for exactly the 8
modules named in the brief. `workorders.py` was audited beyond the brief's scope at the
orchestrator's explicit instruction but is not included in the coverage record, since it is not
one of this batch's assigned modules (recording it here would misrepresent another batch's
assignment).
