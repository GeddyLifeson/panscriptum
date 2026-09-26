# sweep64 batch 13 — audit

## Scope

Read in full, start to finish, sequentially with the Read tool, no sampling and no
grep-driven skimming (line counts from `wc -l` at time of reading):

- `src/assay.py`          1949 lines — SAFETY-CRITICAL (the Custodial Assay scoring engine)
- `src/silence.py`        1313 lines
- `src/completeness.py`    905 lines
- `src/secondopinion.py`   708 lines
- `src/canon_backup.py`    549 lines
- `src/cleanup.py`         452 lines
- `src/sweep.py`           374 lines
- `src/tuning.py`          286 lines
- `src/lognames.py`         52 lines

Total 6,588 lines across 9 modules, all read completely. Read-only throughout: nothing
under `src/`, `data/`, `state/` or `output/` was edited, and nothing was run except the
final `sweep_plan.record()` call this batch was instructed to make.

## Method and prior-audit cross-check

`CLAUDE.md` was read first (Hard Rule -1 escalation chain, Hard Rule 0 no-caps/no-truncation,
the "check that cannot fail" doctrine, the `prose_enabled`/`step4_enabled` gate note).

`handoff/sweep63/` was grepped for all nine module names before reading code, and every
overlapping report was read in full:

- `AUDIT_batch13.md` (sweep63) — same batch number, same two heaviest files: `assay.py` and
  `silence.py`, both read in full there with zero findings against either.
- `AUDIT_batch09.md` (sweep63) — covered `tuning.py` and `lognames.py`; zero findings, one
  open QUESTION about `hosts.py`/`hostcheck.py` vocabulary drift (out of this batch's scope).
- `AUDIT_batch14.md` (sweep63) — covered `cleanup.py` and `sweep.py`; zero findings.
- `AUDIT_batch16.md` (sweep63) — covered `completeness.py`, `secondopinion.py` and
  `canon_backup.py`; zero VERIFIED, one SUSPECTED finding but in `pick_model.py` (out of
  this batch's scope — a truthiness-vs-`is not None` VRAM fallback bug, not touched here),
  and two carried-forward QUESTIONs specific to this batch's files (below).

So all nine of this batch's modules already have a full-line sweep63 read on record, with
no live findings against any of them. This read was done independently rather than as a
rubber stamp — every function was traced by hand against the hazards named in the brief
(fail-open branches, tautological checks, Hard-Rule-0 truncations, off-by-ones, silent
exception swallowing, regex/escape corruption, false comments) — and it reaches the same
conclusion: **no new VERIFIED or SUSPECTED defect was found in any of the nine modules.**

## Findings

**0 VERIFIED. 0 SUSPECTED (new).**

This is, again, an extremely heavily self-audited part of the codebase. Every non-obvious
branch in every one of these nine files carries its own paragraph naming the specific defect
it was written to close, the order ID, and (usually) a live measurement proving the fix. I
read every line looking for a defect the code's own comments do not already name and did not
find one. Specific load-bearing logic traced by hand and confirmed correct, not merely
asserted from the comments:

- `assay.py`: `axis_score()`'s five-way refusal ladder (band off-Ladder / axis non-energetic
  / axis unknown / quantity unscorable / degenerate table), including the M10 top-rung branch
  now reached only for a real axis on a real band; `_check_constants()`'s monotonicity,
  ceiling, `BAND_EDGES` half-extension and `FACULTY_READS`/`NON_ENERGETIC_AXES` partition
  checks, all hand-verified against the live tables (11 rungs × 5 axes, complete and strictly
  increasing; 11 Measures partitioned 5 energetic + 6 non-energetic, disjoint and exhaustive);
  `_interval()`'s two-component variance-plus-covariance propagation, traced term by term
  against `CHARTER_KENSHIRO` and confirmed the covariance loop runs over `applicable` (not
  just `used`), which is the fix the file's own comment says a false start got wrong;
  `assay()`'s ceiling/floor clamp on the printed decimal (`_dec >= 0.995` / `_dec < 0.0`,
  matching the 2-decimal rounding boundary rather than the raw band edge); `_check_weights`/
  `_check_scores`/`_check_readings`/`_check_hand_readings`, the four Layer-1 gates, each
  confirmed to raise rather than clamp on an out-of-range or non-finite input, before any
  arithmetic runs.
- `silence.py`: `_handler_is_observed`'s AST-based (not string-matched) re-raise detection,
  the `_OBSERVED_RX` word-boundary matching, and `_block_reaches_sink`'s taint-propagation
  logic (assignment vs. sink distinction, `_stmts_after`'s recursive walk into nested
  If/For/While/With/Try suites) — traced by hand for a case where a Try node sits nested
  inside a handler's enclosing suite; the recursion correctly stitches together "rest of this
  suite + rest of every enclosing suite" as the docstring claims. `write_json`/`replace_retry`/
  `replace_if_unchanged`'s atomic-write and compare-and-swap discipline (temp name carries
  pid+thread, digest re-read immediately before each replace attempt, `PermissionError` vs.
  other `OSError` given different ledger classes) all check out.
- `completeness.py`: `work()`'s three-way split (no_denominator / genuine-absence-now-
  unreliable / existing-but-zero) and the `if n is not None` vs `if n` distinction for a
  category answering `pages: 0`; `land()`'s three-outcome verdict (`True` / `False` /
  `SKIPPED_ONLY`) and its shrink-floor guard — all traced against the described failure
  scenarios and confirmed to behave as documented.
- `secondopinion.py`: `ran_clean()` cannot be vacuously true (`run()` always populates all
  three tool keys); the returncode-vs-stdout handling in `_ruff`/`_vulture`/`_detect_secrets`
  matches each tool's actual exit-code contract; the tree-fingerprint-before-and-after guard
  in `report()` correctly refuses `--file-orders` when the tree moved mid-scan.
- `canon_backup.py`: `members()`'s strict-refusal-on-missing-canonical-path (never silently
  shrinks the inventory); `snapshot()`'s read-back verification (re-opens the just-written
  zip, re-hashes every member against the pre-write digest); `verify()`'s archive-vs-manifest-
  vs-live three-way comparison, including the `unreadable`-is-not-`changed` split and the
  archive-vs-manifest membership check (`absent`/`extra`) that closes the "testzip() only
  checks what's physically present" gap. `restore()`'s open-source-before-truncate-destination
  ordering and its checked `replace_retry` verdict are sound.
- `cleanup.py`: confirmed this module performs **no filesystem deletion at all** — see
  Question 1 below, since the task brief's premise ("cleanup.py can delete files") does not
  match what the source does. `_ruby_question_mark`/`_ruby_parenthetical`'s non-ASCII guards
  (idempotent under re-application, and correctly declining on the three real-English
  false-positive cases the file's own comment names) and `clean_ceiling`'s exact/head/
  single-prefix-only resolution ladder (refusing to guess on `prefix-ambiguous`) are sound.
- `sweep.py`: `nested_run()`'s consecutive-subset-chain search, hand-traced against a case
  where a non-nested stage sits between two nested ones — it correctly restarts the run at
  the break rather than assuming nesting continues; the funnel's `drop` value is provably
  non-negative because `chain` only ever contains stages verified nested via `<=`.
- `tuning.py`: `regime()`/`profile()`'s `_CACHE["buckets"]` coupling — confirmed the worker
  count and the regime label always come from the same caching moment, whether that moment
  is a fresh read or a served cache hit. `workers()`'s "zero is a request, not an absence"
  fix, confirmed against its own worked scenario.
- `lognames.py`: a small, static constants module; no logic to fault.

## Questions (not findings — flagged for a human, not filed as work)

1. **The task brief's premise about `cleanup.py` does not match the source.** The brief says
   "cleanup.py can delete files: check every delete path fails closed." Grepped and read in
   full: `src/cleanup.py` contains no `os.remove`, `os.unlink`, `shutil.rmtree`, or any other
   filesystem-delete call. Its most destructive action is flipping an in-memory record's
   `catalogued` flag to `False` and writing an `excluded` reason string back through
   `pipeline.write_record` (a data-level exclusion, not a file deletion) — everything it
   touches stays on disk. The module that actually deletes files in this batch is
   `canon_backup.py` (`prune()`'s `os.remove` on old snapshots and orphaned scratch zips),
   and that path was checked and fails closed: a denied `os.remove` is recorded via
   `silence.note` and counted as NOT removed rather than as removed (see the `gone`/`denied`
   split in `prune()`), and the orphan reaper only removes `_writing-*.zip` scratch files
   older than `ORPHAN_AGE_S` (6h), never a fresh in-progress one. Worth correcting the sweep
   plan's per-batch brief text so a future auditor does not spend the read looking for a
   delete path in the wrong file.
2. **Carried forward, not re-argued** — `canon_backup.py:274`, `prune()`'s
   `for f in snaps[:-keep] if keep > 0 else []` still silently no-ops on `--keep 0` or a
   negative `--keep` (falls to `[]`, deleting nothing, which is the safe direction) rather
   than refusing or warning. Not exploitable under the current default (`KEEP = 7`,
   `argparse` default `7`). Already recorded by sweep61 batch16 and sweep63 batch16; still
   true, still undocumented, still not worth a fix on its own.

## Summary of findings by kind

- Real logic bugs (wrong variable, off-by-one, unit mix, races, resource leaks): 0
- Fail-open branches: 0 — every exception path traced in these nine modules (host-reachability
  probes, digest reads, manifest reads, ruff/vulture/detect-secrets spawns) fails toward
  "unmeasured" / "refuse" / "not removed", never toward "proceed as if it succeeded."
- Tautological / unfalsifiable checks: 0 new (several checks that read as tautologies at a
  glance — `instrument()`'s `grade_n <= 5`, `interval_from_hands`'s `covers_all_signatures` —
  are documented in-line as deliberate bounds guards or published guarantees, not live tests,
  and are correctly labelled as such).
- Hard Rule 0 caps/truncations of a roster or listing: 0 live. The only truncations present
  (`completeness.py`'s `good[:a.top]` print table, `sweep.py`'s `DEEPEST EVIDENCE` `[:top]`)
  are explicit, documented `--top N` display requests over data that is written to disk in
  full beforehand — not a silent shrinking of the underlying measurement.
- Comments/docstrings asserting behaviour the code does not have: 0 new.
- Regex/escape corruption: 0 — all nine modules carry and pass their own `_BAD_CHARS` guard,
  and `cleanup.py`'s additional per-pattern control-character check covers `_NAV`,
  `_EMPTY_MECHANIC`, `PL._SETTING_META` and every entry in `_MARKUP`.
- Silent exception swallowing turning a failure into a plausible negative: 0 new — every
  bare-except/suppress site inspected either records via `silence.note`/`silence.exempt`
  or was already covered by the shared `_handler_is_observed` classifier that `silence.py`
  itself implements.

## Coverage

Recorded via `sweep_plan.record('run64', ['assay.py', 'silence.py', 'completeness.py',
'secondopinion.py', 'canon_backup.py', 'cleanup.py', 'sweep.py', 'tuning.py', 'lognames.py'],
batch=13)`.
