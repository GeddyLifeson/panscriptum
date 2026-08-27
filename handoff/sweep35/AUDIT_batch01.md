# sweep35 batch01 — audit of src/verify_math.py

## What was read

The entire file, start to finish, 6992 lines, in sequential offset reads (no sampling):
lines 1-400, 400-700, 700-1100, 1100-1500, 1500-1900, 1900-2300, 2300-2700, 2700-3100,
3100-3500, 3500-3900, 3900-4300, 4300-4720, 4720-4963 (sections 1 through 33, §20a-§20t),
then sections 34-36 (lines 4963-6992: §20r mutation-survivor checks, the run #35 sweep pinned
checks batch1-batch6, and the run #35 LOCAL-batch loader) with extra care per the brief, since
this is the material added today.

Section markers were enumerated first (`grep -n 'print("[0-9]*\. '`) to locate exactly where
sections 34/35/36 begin, so the "heavily edited today" material could be read in full rather
than sampled.

## What was found

Two work orders filed, both in the newly-added material (section 35's spliced "run35" batch
content, itself dated 2026-08-26):

1. **96c4be60fb92** — `verify_math.py:6728-6735`. Two checks are literal tautologies:
   `check("worldseed.main survives zero worlds (no worlds[0] IndexError)", True, True, ...)`
   and the identical shape for `burgs.main`. The "got" argument is the hardcoded literal
   `True`, not a computed result of calling `worldseed.main` or `burgs.main` — nothing under
   test is invoked. The comment beside each admits the gap ("a stronger version of this check
   should monkeypatch..."), so the placeholder shipped as a passing check anyway. This is the
   file's own standing lesson (a check that cannot fail looks exactly like a check that
   passed) recurring inside the file written to catch it.

2. **ff470a877ac5** — `verify_math.py:6542-6583` (order 0a67628cfa8f). The check for a
   failed size-lookup batch never calls `src/backfill.py`. It patches `F.api = _fake_api` but
   then calls `_fake_api(...)` directly and hand-reimplements the batching/sizes/ranking loop
   from `backfill.backfill_source` (backfill.py:180-203) inline in the test, asserting against
   its own copy of the algorithm. `backfill_source` itself is never imported or called. A
   regression in the real function (e.g. reverting the `if d is None: continue` guard at
   backfill.py:192-194 — exactly the fix this order describes) would leave the check green.
   Verified by reading backfill.py:170-207 directly: the real fix is present and correct there;
   the test simply doesn't reach it.

Both were checked against `state/workorders.json` before filing (no existing order named
either).

## Filing mishap, corrected

The first two `file_order()` calls both used `where='verify_math.py'` (no line range).
`order_id()` hashes on `(code, where)` only, not on the finding text, so the second call
silently overwrote the first order's content under one shared id (`5cb6156889eb`) instead of
creating a second order. Caught immediately by reading the queue back. Re-filed both findings
with distinct `where` values that include the line range, and resolved the stray collided
record (`5cb6156889eb`) with a resolution note explaining the mechanical error and pointing at
the two correct ids. No finding content was lost.

## What was read carefully and NOT filed, with reasons

- Section 34 (§20r, the 24 mutation-survivor checks against `assay.py`, lines 4963-5339): read
  in full. Every check calls real module functions (`A.axis_score`, `A.band_for_quantity`,
  `A.regress_test`, `A.interval_from_hands`, `A._interval`, `A.calibration_report`, etc.) and
  most are explicitly anti-reimplementation (e.g. the promotion_watch comment at
  verify_math.py:5134-5136 states the principle directly and the checks below it obey it, via
  the real `A.assay(...)` rather than a recomputed expression). No tautologies, no silent caps,
  no swallowed failures found here.
- Section 35's "batch1" through "batch4" spliced content (lines 5343-6333): each check was
  traced back to a real function call in the target module (`_writes_the_config20p`,
  `LG.read_chain`, `PUB._is_skipped`, `OW.review`, `SO._ruff`/`SO._vulture`, `AC.rho`,
  `_COVx.report`, `_STx_b3.check`, `_ROSx_b3.main`, `_ONx_b3._cmd_is_running`). Most of these
  batches go out of their way to add "positive control" canaries proving their own pattern-
  matchers can still find the fault they exist to catch (the `order 873330d2e98d` block is
  explicitly this). This is good practice and not a finding.
- Section 35's "batch5" (lines 6364-6710) beyond the one filed defect: `_b5_local_carded_checks`,
  `_b5_cascade_no_fallthrough`, `_b5_onomast_doctrine_counts` (re-measures live data rather than
  hardcoding expected counts — the correct pattern, not a fixture-disagrees-with-module
  instance), `_b5_feats_named_labels`, `_b5_backfill_cap_visible` (signature/source checks only,
  not a behavioural reimplementation), `_b5_wiki_source_nonfandom_shortcircuit`,
  `_b5_hostcheck_uses_host_dir` — all call real functions or inspect real source text. Not filed.
- Section 35's "batch6" (lines 6712-6905) beyond the tautology filed above: `eb014351bc46`
  (burgs, calls `BG.burgs_for`), `b235c9c7c388` (identity, calls `ID._is_continuity`),
  `602bbb05ffae` (resonance, calls `RES.incomparability_rate`), the completeness/health/
  catalogue_web source-text checks, `derivation.SCAN_MODULES` (derived, not hand-listed —
  correct pattern), `tempus` hasattr checks, `withdraw_chapters` argparse check, `runguard`
  (a real concurrency-shaped functional test via `RG.claim`/`RG.release`/`RG._land_claim`),
  `cascade_bridge` docstring check, and the `propagation.py` graph-diameter block (explicitly
  printed as `OWNER RULING NEEDED, not an auto-fail` and does not call `check()` at all — by
  design, not a defect). None filed.
- Section 36 (§20u, lines 6909-6992), the loader that `exec`s `handoff/run35/checks_L*.py` in
  isolated namespaces and folds their PASS/FAIL back through the real `check()`: read in full.
  Verified the six expected files (`checks_L1.py`...`checks_L6.py`) exist on disk. The
  fail-closed handling (missing file, unparseable file, `SystemExit` from a file's own harness,
  a file with neither `check_*` functions nor a `PASS`/`FAIL` pair) all route to a FAILED
  check rather than a skip, matching the stated intent. No defect found in the loader itself;
  the content of `checks_L1.py`-`checks_L6.py` is out of scope for this module-scoped audit.
- Checked for recurrence of previously-fixed patterns across all of §34-36 specifically:
  re-searched for the `" or " + "True, " + "True,"` disarm-guard needle shape (none), for any
  other literal `check(label, True, True` occurrences anywhere in the file (grep found only the
  two filed above), and for reintroduced `[:N]` truncations in the new material (all hits are
  either references to a *removed* cap in commentary/negative-scans, or truncating an error
  message string for a printed label — not a truncation of a described-complete data listing).

## Sections 1-33 (pre-existing material)

Read in full for completeness per Hard Rule 0 (own audit), but not re-analysed for new
findings beyond what earlier sweeps already filed — the open work-order queue already carries
numerous `SWEEP34_FINDING` / `SWEEP33_FINDING` / named entries against this file's earlier
sections (stale line-number `silence.note` tags, the duplicate section-tag orders
`VERIFY_MATH_DUPLICATE_SECTION_TAGS` and `dc14fdc767ce`, stale `foreman.py`/`publish.py` line
citations, etc.). Nothing new was found in that span beyond what is already on the queue; nor
was any of it re-filed.

## Coverage

Recorded via `sweep_plan.record('run35', ['verify_math.py'], batch=1)`.
