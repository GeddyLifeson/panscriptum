# Sweep 47, Batch 16 — Audit

Scope (brief): `src/local_agent.py`, `src/binding_health.py`, `src/scout.py`, `src/threads.py`,
`src/handbuilt.py`, `src/pantheon.py`, `src/descending_ladder.py`, `src/cosmology_graph.py`.

## Coverage

All 8 modules read in full, every line, current on-disk source (not order text): local_agent.py
(1370 lines), binding_health.py (1289 lines), scout.py (826 lines), threads.py (671 lines),
handbuilt.py (516 lines), pantheon.py (405 lines), descending_ladder.py (291 lines),
cosmology_graph.py (260 lines). 5,628 lines total, matching the brief's count. Nothing skipped.

## Status of already-open orders (not re-filed; verified against current source)

**local_agent.py**
- `556c1b8fda9f` LOCAL_AGENT_HARDLINK_BYPASS — **still open, confirmed unfixed**. `_safe()`'s
  junction defence (lines ~458-513) resolves via `os.path.realpath`, which follows symlinks and
  junctions but does **not** resolve hardlinks (a hardlink has no "target" path — it IS the same
  inode under a second name in the writable surface). A file inside `src/` or `handoff/` hardlinked
  to `src/foreman.py` (or any denylisted module) would pass every denylist/allowlist string check
  under its own innocuous name, and `open(full, "w")` would then rewrite the shared inode. No
  `st_ino`/`st_dev` cross-check exists anywhere in `_safe()` or `t_propose_patch`.
- `e8622cf0d047` LOCAL_AGENT_WHY_NONE_REVERTS_A_GOOD_PATCH — **still open, confirmed unfixed**.
  `t_propose_patch`'s success return (`return _settle({"applied": True, "why": why[:200]})`,
  inside the `try:` around the write+gates) does `why[:200]` unguarded. If the model sends
  `"why": null` (valid JSON, satisfies the tool schema's `required` list without a real value),
  `why` is `None` and `None[:200]` raises `TypeError`, which the enclosing `except Exception`
  catches and reverts — so a patch that **passed every gate** is thrown away and reported as a
  revert, purely because of this formatting bug.
- `cca253138a62` LOCAL_AGENT_TOOL_TRACE_UNMARKED_CUT — **still open, confirmed unfixed**. The
  per-call console trace at the bottom of `run()` (`print("  [%s] %s -> %s" % (fn,
  json.dumps(args)[:90], json.dumps(res)[:110])`) still cuts both fields with no marker.
- `eb681053b234` LOCAL_AGENT_PYFLAKES_GATE_NO_ENCODING — **appears FIXED**. `_gates()`'s pyflakes
  subprocess call now passes `env=dict(os.environ, PYTHONIOENCODING="utf-8")` (line ~680), and the
  surrounding comment narrates exactly this fix having landed.
- `bffc372a96d2` LOCAL_RUNG_STARVED_BY_THE_LIBRARYS_OWN_DAEMON — not independently verifiable from
  this module alone (depends on `gpu_lane.py`, outside this batch); `_chat()` does route every
  Ollama call through `gpu_lane.lane("local_agent")`, consistent with a partial mitigation.
- `171ade4c7d27` LOCAL_AGENT_SATURATION_DIAGNOSIS_CORRECTED — matches the `_chat()` docstring's
  narrated fix (num_ctx/timeout now read from `config.yaml` rather than bare literals); appears
  addressed as described.

**binding_health.py** — every specifically-named open order's title matches a fix already narrated
and present in the current source:
- `30854f11f322` SWEEP35_FINDING (containment-only CONFIRMED scores) — **fixed**: `binding_verdict`
  now returns `containment`/`tight`/`tied_with` fields recording exactly this.
- `ecc355769a41` BINDING_HEALTH_STORED_ERROR_TRUNCATION — **fixed**: `quarantine()` stores
  `"reason": str(reason)` whole (no `[:300]`); the docstring narrates the fix.
- `61c763a60779` BINDING_HEALTH_QUARANTINE_VERDICT_DISCARDED — **fixed**: `quarantine()`'s `rec`
  now carries `"landed": landed` and escalates `HOST_QUARANTINE_NOT_RECORDED` when the write
  doesn't land; `run()` captures `release()`'s return value through `_report_not_released`.
- `4ed4041c3b78` LIMIT_ZERO_READ_AS_NO_LIMIT (+3 more) — **fixed in this file**: `run()` uses
  `if limit is not None:` (not `if limit:`). Grepped the whole file for other truthy-limit
  patterns; found none — the "three more" instances referenced by the order title are elsewhere.
- `14a73de63099` BINDING_HEALTH_CANDIDATE_BOUND_READS_AS_TOTAL — **fixed**: `_probe_present`'s
  "candidate %d of %d tried" now uses `len(candidates)` (the real bound), not `len(tried)` twice.
- `959b98f38a63` FANDOM_THROTTLING_IS_OUR_CONCURRENCY_NOT_A_B... — owner-level, not resolvable by
  reading this module alone (concerns `feats.py`/concurrency policy); left open.

**scout.py**
- `ef26ed6029e7` READ_LIMIT_NEVER_ADVANCES_AND_SAYS_NOTHING — **still open, confirmed unfixed**.
  `sweep()` (line ~606) does `if limit:` rather than `if limit is not None:` — the exact falsy-zero
  shape already fixed in `binding_health.run()`. `--limit 0` is read as "no limit" and scouts the
  entire hostless roll instead of nothing, silently.

**threads.py, pantheon.py, descending_ladder.py, cosmology_graph.py** — the remaining named orders
(`b186bc4dad8f`, `9fcbe25a473b`, `66f96febdb3a`, `38c51153243c`, `47c8def059e3`, `e866d1520c16`)
were all re-checked against current source and remain open/unfixed as described, with no
contradicting evidence found:
- `9fcbe25a473b` PANTHEON_INCOMPLETE_MARKER_PRINTS_BUT_DOES_NOT_[affect the exit code] — confirmed:
  `main()`'s `_incomplete` branch (line ~279-283) only prints a note; it never appends to
  `merge_failed`, so a roster known-incomplete via `Z_FIGHTERS.json`'s own `_incomplete` marker
  still returns `0` (success) as long as the write landed.
- `38c51153243c` DESCENDING_LADDER_BINDING_ENERGY_NOT_MONOTONIC — confirmed by direct inspection of
  the `DESCENDING` table: binding energy rises from 8.0e-19 J (rung -9, Molecular) to 2.2e-18 J
  (rung -10, Atomic) and again at rungs -11/-12/-13, breaking monotonic decrease with length. This
  is real physics (ionisation energy > a single covalent bond in Joules) but breaks the stated
  "characteristic binding energy" ordering; correctly flagged OWNER-level, not re-filed.

## New finding filed this batch

**BINDING_HEALTH_NONSTRICT_QUARANTINE_STATUS_IN_REPORT** (new, verified) — `binding_health.run()`
uses the non-strict `is_quarantined(h)` (which silently returns `False` when
`HOST_QUARANTINE.json` is unreadable — by its own docstring, justified only for the two callers
that use it to *gate a write*) to populate the **report field** `"quarantined": held` for a host
with no catalogued title to probe (line ~1077). This is a third call site the function's own
docstring doesn't account for ("Both callers ask this only to decide whether to WRITE"), and it is
read-for-display, not read-to-decide-a-write. If `HOST_QUARANTINE.json` happens to be unreadable at
that moment AND this host is actually quarantined, the emitted report row confidently states
`quarantined: false` and omits the "-- and this host is QUARANTINED..." reason clause — exactly
the "could-not-measure recorded as a confident negative" shape this module's own header names as
the whole problem it exists to prevent, now reproduced in one of its own report fields. Filed as
`BINDING_HEALTH_QUARANTINE_STATUS_UNKNOWN_READS_AS_FALSE`, handler LOCAL (the fix is narrow: use
`quarantined(strict=True)` here and catch `QuarantineUnreadable` to report the state as unknown
rather than `False`), severity MINOR.

## Modules/lines NOT read

None. All 8 files read in full, both directly (Read tool, in two passes each for local_agent.py
and binding_health.py due to file length) and cross-checked with targeted greps for known
truthy/falsy-limit and staleness patterns.
