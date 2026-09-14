# AUDIT — sweep run57, batch 06

Modules read in full, top to bottom, this shift: `src/standards.py` (2467 lines),
`src/codewatch.py` (1028 lines), `src/estate.py` (723 lines), `src/anchors.py` (576 lines),
`src/backfill.py` (474 lines), `src/snapshot.py` (376 lines), `src/catalogue_aurora.py`
(324 lines), `src/tuning.py` (286 lines).

## Known-work check performed first

Ran the open-queue dump (`workorders.open_orders()`) and read the two prior full audits named
in the brief in full: `handoff/sweep56/AUDIT_batch06.md` (standards.py, codewatch.py, estate.py
+ six others) and `handoff/sweep56/AUDIT_batch07.md` (anchors.py, backfill.py,
catalogue_aurora.py, tuning.py + four others). `snapshot.py` was not in either sweep56 batch;
located and read its coverage in `handoff/sweep56/AUDIT_batch03.md` instead ("Nothing found.
Read in full."). Every finding below was re-verified directly against the CURRENT source before
being written down — a prior sweep saying a site was clean is not, by itself, evidence that nothing
has drifted since.

---

## DEFECT — stale same-file citation, `standards.py:725-726` — KNOWN(89503c58409f)

```
725:            # refused" -- and the function's docstring at :576
726:            # promises "NOTHING IS CAPPED -- every unverified provider is named". A [:40] slice cut
```

The comment (inside `provider_pool_denominator`, which starts at line 674) points at `:576` for
the phrase `"NOTHING IS CAPPED -- every unverified provider is named"`. That phrase is actually
at **line 695**, inside the SAME function's own docstring. Line 576 today falls inside an
unrelated function (`cfg_num_ctx`'s docstring region).

Verified this is not a fresh drift but the *identical site*, caught and reported before, drifting
again as the file has grown: `handoff/sweep48/AUDIT_batch06.md` already found this exact
citation pointing at `:576` when the real target was `:617` (dated 2026-09-08-era). It has since
drifted a further 78 lines to `:695` while the citation text was never updated. This is squarely
the class tracked by open orders `89503c58409f` (LINE_CITATIONS_IN_SRC_COMMENTS_HAVE_ROTTED_AT_SCALE)
and `386c0d66e31e` (STALE_LINE_CITATIONS_SWEEP54), whose own evidence explicitly predicts exactly
this: "Repairing sites one sweep at a time has been tried three times and the class keeps coming
back, because every edit above a cited line moves it and nothing anywhere checks." Filed as
**KNOWN(89503c58409f)** rather than a new order — the general defect (no mechanical check for
citations past EOF / on blank lines / re-drifted) is already open and this is one more instance
of it, not a new class.

---

## DEFECT — stale same-file citation, `standards.py:1473` — KNOWN(sweep56 batch06)

```
1473:            # restated by hand from CHARTER_REGRESSION_MAX_AGE_H (:525) the way every other
```

`CHARTER_REGRESSION_MAX_AGE_H` is declared at line **635**, not 525. This is the exact finding
already recorded in `handoff/sweep56/AUDIT_batch06.md` ("`CHARTER_REGRESSION_MAX_AGE_H` is
declared at line 635 ... not line 525"), at the identical line number, unchanged since that
sweep. Confirmed still live and unfixed. No new order filed — recorded here as KNOWN so this
sweep's coverage entry doesn't imply it was missed, and so a future batch doesn't re-derive it a
third time. Also falls under the same `89503c58409f`/`386c0d66e31e` umbrella as the finding
above.

---

## QUESTION — `standards.py:1188`, a standard hard-coded to always hold — KNOWN(sweep56 batch06)

```
1188:            "probe failures (reported, not judged)", True, f"{probe:,}", "no floor",
```

Literal `True` passed as `holds`, so this row can never appear as a work order. Already raised
as a QUESTION in `handoff/sweep56/AUDIT_batch06.md`, which also notes it is explicitly
self-labelled "(reported, not judged)" and the surrounding comment says this is deliberate
(probe-class failures are the method, not damage). Re-verified: still the only row in `check()`
where `holds` is a literal constant. No change since sweep56; not re-raised as new, recorded as
KNOWN for continuity of the open question.

---

## Nothing found (verified directly against current source, not merely re-asserted from sweep56)

- **`src/codewatch.py`** — read in full, with particular attention to the sweep brief's own
  named risks: "a daemon keeping stale code running after `src/` changes" and "reading a
  deliberate rc=17 exit as a crash." Traced the whole chain: `fingerprint()`/`quiet_seconds()`
  both refuse (return `None`) rather than answer on any unreadable file, `stale()`'s two-clock
  design (`seen` vs `differing_since`/`quiet`) correctly takes the max of poll-based and
  mtime-based settle time, `_claim_restart_slot` does one locked check-and-take (closing the
  run #36 twin race), `_take_locked` fails CLOSED on a denied ledger write (order f06ba4c82363:
  a claim that cannot be recorded is refused, not granted unmetered), and `exit_if_stale` prints
  "This is NOT a crash" and escalates at JANITOR (not a fault severity) on every rc=17 exit, with
  `overnight.name_rc` (verified in `src/overnight.py`) taught to read rc=17 by name. Cross-checked
  `EXEMPT`/`COVERED_ELSEWHERE` against the live rosters: `overnight.ALL_JOBS` = `["autostart.py",
  "overnight.py"] + STANDING basenames + ["feats.py --roll"]`, and every one of those names
  resolves correctly to EXEMPT, COVERED_ELSEWHERE, or a STANDING member — no UNACCOUNTED job.
  Verified by inspection that `hostcheck.py` and `magnitude.py` (both claimed EXEMPT as
  "NOT A DAEMON EITHER, no loop in main") indeed have no loop in their `main()` bodies. `read.py`
  was promoted into `overnight.STANDING` on 2026-09-08 with a `--loop 5` argument specifically so
  it has a place to call `exit_if_stale`, per the extensive comment at `overnight.py:996-1044`
  (three drill/verify_math nets were updated in the same commit per that comment) — consistent
  with codewatch's own contract. No fail-open path found that isn't already an explicit, argued
  exception (`twins()`/`claim_singleton` failing open with no `psutil` is documented and reasoned,
  not silent). No caps, no dead code beyond what the module already flags as intentional
  (`_budget_left` as the drill-only read path).
- **`src/estate.py`** — read in full again. `inspect()`'s per-extension handling (the `.jsonl`
  torn-line case, the retry-then-classify stat race, the TRANSIENT_EXT exemption), `artifacts()`'s
  root discovery (walks every top-level entry `SKIP_DIRS` doesn't exclude, not a hand-kept list),
  `charter()`'s four behavioural erratum tests (each reads the charter's own tables rather than
  testing string presence), `written()`'s and `terminal()`'s vanishing-row-safe `note()` calls,
  and `external()`'s four-condition Ollama/Cascade/disk checks all re-verified against current
  code. No caps, no silent failures, no lost-update risk (this module only reads).
- **`src/anchors.py`** — read in full. All five graded verdicts in `run()`
  (`the declared ladder grades every anchor`, `every anchor produced a decimal`, the monotone
  ordering, the five per-anchor `CLAIMS`, and the four college/bit-value invariants) are real,
  falsifiable tests over live data, not tautologies — confirmed each can fail (e.g. the finite-
  interval check would fail on a non-numeric or non-positive `interval`; the bit-value check
  would fail on a band whose edges collapse). The three deliberately-NOT-graded properties
  (`prior_divergence_share + attestation_floor_share == 1`, `covers_every_reading`, bit-value
  monotonicity) are correctly excluded as tautological-by-construction, with the reasoning
  documented in-line and verified against `custodes.py`'s own docstrings. No new "check that
  cannot fail" found beyond what sweep56 already confirmed clean.
- **`src/backfill.py`** — read in full. `roster()` is genuinely uncapped by default (`limit=None`
  on the only production call site), ranks by article size rather than alphabetically before any
  `--cap` is applied, and `--cap` itself is opt-in/off-by-default and documented as bounding only
  what is queued this pass, not the roster. `backfill_source`'s write-gating
  (`P.write_record_catalogue` verdict checked before reporting `added`) and the `--all` path's
  now-complete outcome accounting (`denied`, `probe_failed`, `errors`, `not_fetched`,
  `dropped_as_stub` all separately counted) are both intact. The `audit()` print loop's
  `x['source']` is printed uncut, with an in-line comment citing its own prior fix under order
  `fe99e57e1993` — checked against that order's text and confirmed this file's portion of that
  compound order is already landed (KNOWN(fe99e57e1993), no residual defect here).
- **`src/snapshot.py`** — read in full (already "nothing found" in sweep56 batch03; re-verified
  independently rather than trusted). `_rel()`'s containment refusal, `before()`'s
  nanosecond+pid unique id and partial-snapshot refusal (`allow_missing` is explicit opt-in),
  `_dir_matches()`'s whole-directory byte comparison, `verify()`'s restore-to-temp-and-compare,
  `_safe_join()`'s second containment check on restore, and `restore()`'s missing-file refusal
  are all present and behave as documented. No caps, no silent failures, no lost-update risk
  (each snapshot gets its own directory by construction).
- **`src/catalogue_aurora.py`** — read in full. `slug()` is genuinely uncapped;
  `record_path()`'s exact-then-legacy-then-new resolution correctly avoids splitting an
  existing record in half. `parse_folder()`'s dedup key now includes the description text (not
  just type+name), so distinct same-named elements from different subclasses are kept, and
  `dropped` is reported rather than silently discarded. Every write in `main()` (`record`,
  `SWEEP_ROLL.json` via `roll.update_rows`) is gated on its landed verdict and the process exits
  1 on any refusal, with every refusal named in the final message. The `catalogue_aurora.py:151`
  citation of `:74` is (as sweep56 already found) explicitly describing a past state as the
  reason the label was converted to a content tag — re-verified correct, not stale.
- **`src/tuning.py`** — read in full. `_ollama_host()` reads `config.yaml` rather than
  hardcoding, `_answering_buckets()` and `cloud_success_rate()` both degrade to "no evidence"
  (never a false pass) on any read/parse failure, `regime()` requires BOTH bucket count and
  measured success rate before calling a pool "cloud" (closing the reachability-vs-capacity
  conflation the module's own docstring names as the project's most-repeated defect), and
  `workers()`'s ceiling-not-floor contract correctly treats a requested `0` as a real request
  rather than falling through to the profile default. No caps, no silent failures, nothing dead.
  Matches sweep56 batch07's "clean read, nothing to add."

---

## Coverage

Recorded via `sweep_plan.record('run57', ['standards.py','codewatch.py','estate.py',
'anchors.py','backfill.py','snapshot.py','catalogue_aurora.py','tuning.py'], batch=6)` — see
tool output in the session; all eight listed modules were read in full, top to bottom, as
required by Hard Rule 0.

## Summary

| Module | NEW DEFECTs | QUESTIONs | KNOWN |
|---|---|---|---|
| standards.py | 0 | 0 | 3 (2 stale citations, 1 always-holds row) |
| codewatch.py | 0 | 0 | 0 |
| estate.py | 0 | 0 | 0 |
| anchors.py | 0 | 0 | 0 |
| backfill.py | 0 | 0 | 1 (fe99e57e1993, already landed) |
| snapshot.py | 0 | 0 | 0 |
| catalogue_aurora.py | 0 | 0 | 0 |
| tuning.py | 0 | 0 | 0 |
| **Total** | **0** | **0** | **4** |
