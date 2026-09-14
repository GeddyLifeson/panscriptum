# Sweep 58 — Batch 13 Audit

Read in full, top to bottom (offset-paged where needed):

| module | lines read |
|---|---|
| src/assay.py | 1914 |
| src/dashboard.py | 1249 |
| src/completeness.py | 871 |
| src/custodes.py | 715 |
| src/canon_backup.py | 550 |
| src/axis_correlation.py | 444 |
| src/grounding.py | 362 |
| src/propagation.py | 255 |
| src/catalog.py | 168 |

Open-queue check performed first (`workorders.open_orders()`, scratch script per brief). Findings
below are cross-referenced against it; matches are tagged `KNOWN <id>`.

Per the brief's shift note, three fixes were verified directly against source rather than taken on
faith:

- **canon_backup.verify()** — confirmed FIXED. `verify()` (~L446-454) now returns `False` with
  a `"NOT OK: ..."` note when `gone` (canonical files the manifest records that the live tree no
  longer has) is non-empty. This is order **2f85e46c2c3c** (`CANON_BACKUP_VERIFY_OK_WITH_CANONICAL_FILES_GONE`),
  and the fix is live and correctly wired to the top-level verdict (`return False, notes`), not just
  to a printed note.
- **completeness.audit()** — confirmed FIXED. The `byslug` alias table (~L401-408) now lower-cases
  *both* keys it stores — `byslug[str(src).lower()] = v` and
  `byslug[v["file"][:-5].lower().replace("-", " ")] = v` — matching how `_rec()` (~L457-458) looks
  both up. This closes the alias half of sweep57 question bundle `bf1340bc3b3f`.
- **custodes.py docstrings** — confirmed FIXED. `_abstained()`'s docstring (~L364-372) and
  `convene()`'s docstring (~L438-462) now correctly state that `anchors.py`'s `run()` supplies
  `distance`/`years_since` for the five calibration anchors (owner ruling `bd673ceaaf31`), so Lumen
  no longer abstains on that production path — only `verify_math`'s and `main()`'s demonstration
  calls still omit the vantage and trigger the abstention. Threnody (comparability) is correctly
  still documented as abstaining on every real call. This is order **360c6b8c68e5**
  (`CUSTODES_DOCSTRING_CONTRADICTS_ITS_CALLER`).

## src/catalog.py (168 lines)

Nothing found. Checked: no caps on `cmd_stats`'s missing-sources list or `cmd_search`'s hits;
`load_catalog` names a missing index rather than reading it as empty; every CLI path returns an
`rc` and `main()` is invoked via `sys.exit(main())`, so a miss and a hit are distinguishable exit
codes.

## src/propagation.py (255 lines)

Nothing found. `observed_mark()`'s loop-direction/termination reasoning checks out: the loop counts
down `LADDER_HEIGHT..1`, `ascension_years(1) == 0.0`, and the `lag < 0` guard above it means the
loop is guaranteed to match by its last iteration, so the trailing `return 0` is genuinely dead as
claimed. `main()`'s two paths (`--from/--to` and the default survey) both return non-zero on a
disconnected/absent pair. No caps on the diameter survey's output.

## src/grounding.py (362 lines)

Nothing found. `classify_text`'s `top` defaults to the whole field (Hard Rule 0 compliant);
`classify_source`'s `cap` parameter raises loudly rather than truncating; the write path is gated
on `silence.write_json`'s verdict. The `_ORIGIN`-filter / synthesis-blob exemption is documented
consistently with what the code does (`parts.append` for `syn` is unconditional, outside the
`_ORIGIN.search` guard that gates entry text).

## src/axis_correlation.py (444 lines)

Nothing found beyond queue matches.

- **QUESTION — already filed.** `write()` has no floor guard against a rebuild that reads every
  `SOURCES` file but nets fewer scoreable entities than the standing `data/AXIS_CORRELATION.json`
  (only the source-level `degraded` stamp exists, not a row-count guard). This is **KNOWN 34ec8a90c42f**
  Item 1, triaged by agent Q2 as a DESIGN/RULING question (not a defect), awaiting an owner decision
  on which count and which floor. Verified the description against current source: `write()`
  (~L245-281) indeed compares nothing against the prior file before writing.

## src/canon_backup.py (550 lines)

- **KNOWN 2f85e46c2c3c — confirmed FIXED**, see summary above.

No other findings. `members(strict=True)` refuses rather than silently shrinking when a declared
canonical path is absent; `snapshot()` reads its own archive back and verifies every digest before
recording success; `prune()` treats a half-removed archive/manifest pair as "not removed"; `restore()`
opens the source member before creating any destination file and lands via `replace_retry` with the
verdict checked.

## src/custodes.py (715 lines)

- **KNOWN 360c6b8c68e5 — confirmed FIXED**, see summary above.
- **QUESTION — already filed.** `_transit_widening()` (~L388-428) sums `staleness_widening(...)`
  once per dispersive Custos whose `dof == "currency"`; today only Lumen qualifies so the sum is a
  single term, but a second such Custos would double-count one physical fact (transit staleness) as
  two independent widenings, and the `source` string would also only record the last such Custos'
  provenance rather than all contributors. This is **KNOWN 34ec8a90c42f** Item 4, already triaged
  as a DESIGN/RULING question, not a defect — no consequence today since the table has exactly one
  currency-dof dispersive Custos. Verified against current source; the code matches the order's
  description exactly.

No other findings. `convene()`'s attendance flags (`staleness_measured`, `comparability_measured`,
etc.) are set before the `len(readings) < 2` early return, so a band-only result still carries them,
as documented. `table_faults()` correctly reports zero faults for both zero-tilt Custodes (Threnody,
Lumen), matching their written `tilt=0.0` / `evidence_sensitivity=0.0` declarations.

## src/completeness.py (871 lines)

- **KNOWN — confirmed FIXED**, byslug lower-casing, see summary above.
- **KNOWN f5b8e4afb558** (`PRIMARY_HOST_ONLY_EVER_FANDOM`) — remedy (a) is landed and verified
  live: the `elif shared[host] > 1 ...` branch (~L668-679) now says "no primary can be identified
  for a non-fandom host at all ... the question was never asked" when `subdomain(host) is None`,
  distinct from the fandom-host "is not the primary" wording. Remedy (b) — what should decide the
  primary for a shared non-fandom host — is unresolved and correctly left open per the order; no
  aggregate or row changed, as intended.

No other findings. `land()`'s three-valued verdict (`True`/`False`/`SKIPPED_ONLY`) is correctly
distinguished by `main()` (`if verdict is True: ... else: ...`), and the shrink-floor / write-denial
/ `--only` guards all match their documented behaviour.

## src/dashboard.py (1249 lines)

Nothing found. This module is not in this shift's "rewrote code in" list and none of its many
documented past fixes (fault isolation per panel, corrupt-history healing, absent-vs-unreadable
distinctions, uncapped findings/quarantine/breached-nets lists) show signs of regression on
inspection. `main()`'s halt-handling for a read-only instrument (prints and continues rather than
refusing to start) matches the criterion stated in its own comment (writes only inside `state/`).

## src/assay.py (1914 lines, live mutation target — read only, not run)

Nothing found beyond queue matches.

- **KNOWN 7099a092abd3** — `band_for_quantity`, `null_instrument`, and `interval_from_hands` (plus
  siblings in `tempus.py`, `ledger.py`, `cosmography.py`) have no production caller, only battery
  callers. Owner ruling 1 of 2026-09-08 already decided "mark and keep, delete nothing," and the
  in-file comments at each function correctly reflect that ruling. Not re-litigated here.

No new findings. Spot-checked the load-bearing arithmetic: `_interval()`'s covariance term matches
`axis_correlation.widening()`'s formula in structure (both `2*w_a*w_b*rho*sigma_a*sigma_b`, summed
over `i<j`); `_check_constants()`'s cross-table assertions (BAND_EDGES vs LADDER vs NON_ENERGETIC_AXES
vs WEIGHTS partition) hold under the current tables; `axis_score()`'s five-way branch ordering
(structural refusals before the quantity is even inspected) is consistent with its own docstring's
account of the top-rung history it fixed.

## Coverage stamp

`sweep_plan.record("run58", [...], batch=13)` called for exactly the nine modules listed above,
all read in full this session.
