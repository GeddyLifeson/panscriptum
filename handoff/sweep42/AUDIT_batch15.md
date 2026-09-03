# run42 (sweep42) batch 15 — audit

Modules (read in full, all 8): `src/assay.py` (1374 ln), `src/dashboard.py` (1101 ln),
`src/gpu_lane.py` (685 ln), `src/endpoint.py` (563 ln), `src/tiers.py` (458 ln), `src/genre.py`
(338 ln), `src/coverage.py` (300 ln), `src/roll.py` (270 ln). Total ~5,089 lines, all read start
to finish, no sampling. `CLAUDE.md` read first.

## Special-instruction item: order 6d132aa1e8aa (assay.py "two parallel five-grade attestation
tables")

**Checked directly, and it is accurate — the order is CONFIRMED, still open, not fixed as of this
read.**

`assay.py` really does carry two independently-maintained five-grade attestation tables, both
keyed on the same five grade names (`Instrumented, Witnessed, Transcribed, Reconstructed,
Disputed`), both encoding "worse evidence -> wider published interval", used by two different
formulas on two different call paths:

* `SIGMA_BY_ATTESTATION` (derived from `_RAW_SIGMA`, assay.py:329-335, rescaled at :393-396) — a
  per-AXIS-SCORE sigma (0-9.9 scale), consumed by `_interval()`/`assay()`'s single-worksheet path
  (the routine that produces a Moth Number's published `±` for one entity's own axis scores).
  **Guarded**: `_check_constants()` (assay.py:570-602), run at import, refuses to load unless the
  five sigmas are strictly increasing and none exceeds the ceiling (`SIGMA_MAX`).
* `ATTESTATION_FLOOR` (assay.py:1296-1297) — a flat floor added in quadrature to Hand-disagreement
  spread, consumed by `interval_from_hands()` (assay.py:1307-1366), the routine that derives a
  published `±` from multiple Custodes' (Hands') divergent readings of the same entity, and
  re-exported verbatim as `custodes._ATT_BASE` (custodes.py:247-248) to build
  `custodes.ATTESTATION_QUALITY`.

I independently verified the claimed gap: I read `_check_constants()` in full (assay.py:570-602)
and it examines only `SIGMA_BY_ATTESTATION`/`SIGMA_UNKNOWN`/`SIGMA_MAX` — there is no assertion
anywhere touching `ATTESTATION_FLOOR`'s five values. I grepped every reference to
`ATTESTATION_FLOOR` in `src/` (8 hits, all in `assay.py`, plus the `custodes.py` re-export and two
`drill.py` lines at 8002/8004 that each check ONE endpoint — `Instrumented`'s value and the
unrecognised-grade substitution — never the ordering across all five). No monotonicity or
ceiling check over `ATTESTATION_FLOOR` exists anywhere in the tree today.

Consequence, as the order states: a mid-table edit to `ATTESTATION_FLOOR` that preserves both
tested endpoints (e.g. swapping `Transcribed=0.20` and `Reconstructed=0.40`) would pass every
existing check silently and publish a **narrower** interval for a **worse**-attested Hand-reading
on that pair of grades — the exact "less knowledge, narrower bar" defect this same file's own
`_check_constants()` docstring says it exists to catch on the sigma side, with no equivalent on
the floor side.

**Filed as CONFIRMED** (corroborating the existing order 6d132aa1e8aa /
`ASSAY_ATTESTATION_FLOOR_NO_MONOTONICITY_GUARD`, not a new id). Remedy stays what the order already
names: fold `ATTESTATION_FLOOR` into `_check_constants()` (or a sibling import-time check)
asserting strict monotonicity `Instrumented < Witnessed < Transcribed < Reconstructed < Disputed`,
mirroring the check immediately above it in the source.

## Confirmed findings (new)

**1. `roll.py:264`** — `print(" %s" % why[:150])`

```python
print("  %-46s %6d entries" % ((name or "?")[:45], n))
print("      %s" % why[:150])
```

`why` here is the exclusion note returned by `out_of_scope()` — the human-written reason a person
gave for taking a source out of scope. This is a straight content truncation (not a fixed-width
column pad; there is no `%Ns` width spec on it) of exactly the field this module's own docstring
insists must never be dropped: `out_of_scope()`'s docstring says "RETURNS THE REASON, NOT JUST THE
NAME. An exclusion with no reason attached is how a real source gets quietly dropped and nobody can
reconstruct why," and `exclude()` refuses to even accept an empty note for the same reason. Cutting
the printed reason at 150 characters with no ellipsis, no count of characters dropped, and no
"more" indicator directly contradicts that stated design goal for any note longer than 150 chars —
the report can silently show a truncated justification for excluding a whole source and give no
sign that anything is missing. Per Hard Rule 0 (truncation vs. ranking) and per the module's own
words, this is a defect, not a display convenience. **Confidence: high** — the pattern is exactly
what CLAUDE.md's Hard Rule 0 names, and it sits in the one module whose entire purpose section is
about never losing the reason for an exclusion.

**2. `dashboard.py:1031`** — `str(e)[:120]` on the `/api/state` top-level error response

```python
def do_GET(self):
    if self.path.startswith("/api/state"):
        try:
            self._send(json.dumps(state()), "application/json; charset=utf-8")
        except Exception as e:
            silence.note("dashboard.py:state")
            self._send(json.dumps({"error": f"{type(e).__name__}: {str(e)[:120]}"}),
                       "application/json; charset=utf-8")
        return
```

Every one of `state()`'s panel builders (`quotas`, `throughput`, `jobs`, `library`, `watch`,
`metrics`, `safety`) wraps its own body in try/except and degrades gracefully, so this outer
handler looks unreachable at first read — but it is not: `movement(now_state)` (dashboard.py:370)
computes its final `out` list (lines ~470-499, the per-metric delta loop) **outside** any
try/except — only the HISTORY file read/repair and the HISTORY write are guarded (lines 419-433
and 434-468). A malformed or type-mismatched value reaching `keys` (e.g. from a corrupted
`dashboard_history.json` row that survives the `isinstance(h, dict)` check with sabotaged field
types) can raise a raw `TypeError` out of `v - was` at line 479, propagating through `movement()`,
through `state()`, and landing exactly on this handler — where it is cut to 120 characters. This is
the identical failure shape this same file names and fixes twice elsewhere in this batch's own
code (`dashboard.py:1031`'s neighbours: the `[:160]`/`[:120]`-style cuts on `watch()`'s findings
and on `safety()`'s quarantine reasons were both found and un-capped — "UNCUT (order
50c9f6130b95)" at line 340-346, "reason uncut, same ruling" at line 611-614) — a diagnostic
"cut so short it cannot diagnose" is exactly what CLAUDE.md calls out, and this file's own
established practice elsewhere is to never do this. **Confidence: medium** — the truncation itself
is unambiguous and matches the house anti-pattern precisely; what is not fully proven is how
likely the specific TypeError path through `movement()` is to fire in production (it requires a
corrupted-but-dict-shaped history row), so the severity is "a diagnostic that would be too short
if it ever needed to fire," not an observed live failure.

## Checked and found NOT a violation / already correctly handled (not filed)

- **`assay.py`** — read start to finish. `_check_scores`, `_check_weights`, the covariance term in
  `_interval`, the floor/ceiling/promotion/demotion clamps in `assay()`, the `_rho` fallback and
  its provenance stamp, `calibration_report()`'s re-derivation discipline, and `instrument()`'s
  Layer-1 validation were all read against their own extensive commentary and found internally
  consistent — every guard the comments claim exists does exist and fires where claimed. No new
  defect found beyond the confirmed `ATTESTATION_FLOOR` gap above.
- **`gpu_lane.py`** — read start to finish. This module carries an unusually dense set of
  already-fixed prior incidents (m54, m55, orders d316c46b67bd, e7b6dcc8d630, 763b56061157,
  b54fbcf84962, 4822b2c5744e) and every guard named in its comments was verified present and
  correctly wired: the Windows `_alive()` PID check, the slot/claim staleness reclaim logic, the
  heartbeat threads for both slot and foreground leases, the fail-open behaviour on every failure
  path, and `status()`'s honest `partial` flag. No new defect found.
- **`endpoint.py`** — read start to finish. The MODE_API/MODE_RAW/MODE_DEAD probe cache's
  compare-and-swap save (`_save()`), the DEAD-verdict TTL, `fetch_raw`'s and `fetch_html`'s
  distinct-ledger-entry-per-failure-class handling (403 vs 404 vs HTML-body-as-block-page), and
  `register()`'s absent-vs-unreadable distinction were all checked against their own commentary
  and found consistent. `main()`'s `--list` and probe-listing paths print every host in every
  mode, uncapped.
- **`tiers.py`** — read start to finish, including the extensive cosmology-tier methodology essay
  at the top. The containment-nesting refusal-to-publish gates (`split_sources`, the groundings-
  readable re-check at write time) were verified to actually gate the write (return 2, do not call
  `write_json`) rather than merely print a warning. `deliberate_joins()` returns the whole `shared`
  evidence list per pair (Hard-Rule-0 fix already landed, verified present). No new defect found.
- **`genre.py`** — read start to finish. `classify_text`'s `top` parameter and `classify_source`'s
  `cap` parameter are both already corrected per Hard Rule 0 (uncapped ranking is the default;
  passing a numeric `cap` now raises `SystemExit` rather than truncating silently). `main()`'s
  low-confidence list is printed whole, ranked worst-first. No new defect found.
- **`coverage.py`** — read start to finish. The CITED/READ/NO-PAGE/NOT-ATTEMPTED/NO-HOST state
  machine's strict precedence, the per-file ownership check (`cachekey.owns`) guarding against
  path-collision cross-contamination, and `report()`'s `--show`/`--show-best` semantics (None/0
  both mean "all of them," capping is announced with a count of what's hidden) were all verified
  against their own commentary. No new defect found.
- **`roll.py`** — read start to finish apart from the finding above. The `mutate()`
  compare-and-swap, `update_rows()`'s unmatched-name reporting, and `exclude()`'s
  caller-supplied-`rows`-means-caller-persists contract (the fix for the 2026-08-26 roll-destruction
  incident) were all checked and found correctly implemented as documented.

## Questions (not filed as defects — plausibly deliberate, flagged for the owner's awareness)

None beyond the standing `ATTESTATION_FLOOR` item above, which is already an open order rather than
a fresh question.

## Coverage

Recorded via:
```
cd C:\Users\imarl\panscriptum-library-kit && PYTHONIOENCODING=utf-8 C:/Users/imarl/miniconda3/python.exe -c "import sys; sys.path.insert(0,'src'); import sweep_plan; sweep_plan.record('run42', ['assay.py','dashboard.py','gpu_lane.py','endpoint.py','tiers.py','genre.py','coverage.py','roll.py'], batch=15)"
```
