# sweep64 batch07 audit

Auditor for batch 7 of sweep64 (maintenance run #64, 2026-09-26). Read-only throughout: nothing
under `src/`, `data/`, `state/` or `output/` was edited, created or deleted this session, other
than this report and the single permitted `sweep_plan.record(...)` call. No job, drill, sweep,
publish, mutate, or `withdraw_chapters` invocation was run.

## Scope, read in full, start to finish, sequentially, no sampling

- `src/standards.py` — 2,487 lines (read in five chunks: 1-650, 650-1300, 1300-1950, 1950-2487)
- `src/overwatch.py` — 1,136 lines (two chunks: 1-600, 600-1136)
- `src/wiki_source.py` — 808 lines (two chunks: 1-450, 451-808)
- `src/withdraw_chapters.py` — 614 lines (two chunks: 1-400, 400-614)
- `src/backfill.py` — 494 lines (one chunk)
- `src/retry_synthesis.py` — 379 lines (one chunk)
- `src/catalogue_aurora.py` — 328 lines (one chunk)
- `src/physics.py` — 312 lines (one chunk)

Total: 6,558 lines across 8 modules, all read in full.

## Method

`CLAUDE.md` read first for doctrine (Hard Rule -1 escalation/halt, Hard Rule 0 no caps ever,
fail-closed, "a check that cannot fail looks exactly like a check that passed"). Every module in
this batch was then read top to bottom before any conclusion was drawn, per the
`read-fully-before-reviewing` discipline — no grep-only sampling.

`handoff/sweep63/` was grepped for all eight module names before reading, and every audit that
named one of them was read in full:

- `AUDIT_batch07.md` (sweep63) — covered `standards.py`, `overwatch.py`, `wiki_source.py`,
  `withdraw_chapters.py` (among five other modules not in this batch). Reported two VERIFIED
  findings, both from **sweep61**, and confirmed both already fixed in the code that batch read:
  (1) `standards.py`'s "cached records that were fully read" check no longer reads a 700-byte
  head of each `data/readfeats/*.json` record, it `json.load`s the whole record; (2)
  `overwatch.py`'s digest-retirement loop now retires a finding whose module file was deleted
  (checks `os.path.exists` before the digest comparison). No new findings in any of the four
  modules this batch shares with it.
- `AUDIT_batch03.md` (sweep63) — covered `backfill.py`, `retry_synthesis.py`,
  `catalogue_aurora.py` (among five other modules not in this batch, including `repass_bands.py`
  which is a different module from this batch's four). No findings against any of the three, one
  QUESTION filed against `retry_synthesis.py` (below).
- `AUDIT_batch13.md` (sweep63) — covered `physics.py` in full (among seven other modules not in
  this batch). No findings.

I verified each of those prior claims against the CURRENT source (not merely trusted the citation)
before treating anything as already resolved, per this sweep's standing instruction that audits
here have been wrong in both directions. Both sweep61 fixes cited above are still present and
correct in the code read this session.

I specifically hunted, in priority order, for: (1) fail-open branches (unknown/unreadable state
authorising work); (2) tautological or unfalsifiable checks; (3) caps/truncations of a ranked
listing (Hard Rule 0 — ranking is fine, ranking-then-truncating is forbidden); (4) real logic bugs
(wrong variable, off-by-one, races, inverted conditions, resource leaks); (5) comments/docstrings
asserting behaviour the code does not have; (6) silent exception swallowing that turns a failure
into a plausible negative; (7) dead code a comment claims is live; (8) regex/escape corruption. Per
the brief, `wiki_source.py`'s fandom request rate was checked specifically: `MIN_GAP = 0.15` (line
162) and `WORKERS = 48` (line 163) are the current values, matching the post-incident, post-ban
setting the brief describes (the module's own comment history shows 0.35s serial → 0.08s/16-worker
benchmark → the 0.01s/48-worker ladder that got this machine IP-banned → the current 0.15s
floor). The throttle in `_get()` (lines 166-204) holds a single process-wide lock across all
worker threads and sleeps *inside* that lock when the gap since the last request start is under
`MIN_GAP`, which serialises every request's *start* time by at least 0.15s regardless of
`WORKERS` — i.e. the wall-clock request-start rate is capped at ~6.7 req/s no matter how many of
the 48 workers are in flight waiting on responses; only the network wait overlaps. This matches
the module's own stated intent and is not a regression. `_get()`'s retry loop re-enters the
throttle+lock gate on every retry (the gate sits inside the `for attempt in range(...)` loop), so
a 429/503 backoff does not bypass the global pacing.

## Findings

**None new.** Zero VERIFIED, zero SUSPECTED findings across all eight modules. Everything sweep63
found in these modules was either already fixed (and re-verified fixed here) or was not in this
batch's actual scope.

Areas specifically traced by hand, beyond re-checking sweep63's citations, because they are the
densest/highest-risk logic in each file:

- **standards.py**: `job_stamp`/`read_progress_verdict`'s cold-start vs. stalled vs. unmeasurable
  tri-state logic (lines 442-531) traced against all four `(done, total)` shapes it documents;
  correct. `context_verdict`/`resident_context`/`model_matches` (identity-based resident-runner
  matching, order dddf4d96bb3e) traced; correct, no position-based fallback survives. The
  self-check that finds "every declared floor is measured" (lines 2339-2372) was traced against
  its own regex: `CHARTER_REGRESSION_MAX_AGE_H` and `MIN_CALLS_TO_JUDGE_RATE` (both declared via
  a derived/aliased name rather than a literal) both resolve correctly to "measured" because each
  is referenced a second time by name outside its own declaration line. The eighteen-plus
  `try/except -> _dropped.append(...)` blocks in `check()` were spot-checked and each one's
  exception path both notes to `silence` and appends the same name to `_dropped`, so the
  "every standard could read its own input" aggregate at the bottom genuinely cannot be defeated
  by a silently-vanished row.
- **overwatch.py**: `_merge_ledgers`/`_progress`/`_finished_at` (the two-writer ledger merge and
  its rank-then-timestamp tie-break, order 72e33d06d4eb) traced against mixed epoch/string
  timestamp inputs; correct, and matches the fix already recorded. `verify_open`'s "only a
  finding the model actually answered for is stamped" discipline (order c6f64c1424fa) and
  `review`'s matching `complete` flag (order a3ee0d1d2d4c) are both correctly wired: a `None`
  from `_ask` never stamps `seen` or `last_verified`. `_LOCAL_BUSY` is reset at the top of every
  `round_once` call, so the GPU-busy cloud-fallback budget is per round as documented, not a
  lifetime counter.
- **wiki_source.py**: `resolve_wiki` correctly refuses to spend a fandom-facing guess against a
  source `WIKI_HOSTS.json` already knows is non-fandom (lines 299-313). `all_categories`,
  `category_members`, `extracts` and `rank_by_size` all raise on a mid-walk transport failure
  rather than returning a truncated prefix (order de0681cb9edc) — verified each of the four
  individually. `page_texts`'s `zip(..., strict=True)` over `pool.map` output is order-preserving.
- **withdraw_chapters.py**: `_file_state`/`_archive_name_free` correctly distinguish "positively
  absent" (a directory listing that does not contain the name) from "could not be determined" (a
  lock, a denial, an unparseable path) — never treating the latter as the former. `_land_merged`'s
  compare-and-swap is used consistently for both the withdrawal manifest and `catalog.json`, and
  the final `bad` computation (line 608) folds in every refusal class (`stuck`, `unreadable`,
  `collided`, `stray_stuck`, `not catalog_landed`, `not record_landed`) rather than only the ones
  printed to the console.
- **backfill.py**: the `missing = sorted(missing, key=lambda t: (t in sizes, -sizes.get(t, 0)))`
  ranking key (order d673aa4d609a, fixed from an inverted `not in`) was hand-traced against the
  module's own worked example (`sizes={A:100, C:5}`, B unmeasured) and produces `[B, A, C]` as
  documented — an unmeasured title ranks with the deepest articles, never with the smallest known
  one, so `--cap` cannot systematically drop failed size-lookups.
- **retry_synthesis.py**: `synthesise()`'s best-band-across-chunks selection (`rank = int(band[1:])
  if band != "unassayed" else -1`) correctly lets any real band beat an unassayed one. The
  acceptance gate uses `PL.clean_band`/`PL.valid_scale_note`/`PL._stored_cut` from `pipeline`
  directly rather than restating them, so the five previously-documented parity drifts between
  this rescue path and `phase_synthesis` cannot recur silently.
- **catalogue_aurora.py**: `record_path`'s legacy-slug fallback (prefix-anchored, order
  683c59f43829/5fcb628db94c) and `parse_folder`'s duplicate-key-now-includes-description dedup
  (order run#36) both trace correctly against their own documented before/after examples.
- **physics.py**: every public function (`kinetic`, `joules_for`, `sphere_volume`,
  `binding_energy`) refuses non-positive, non-finite, and NaN inputs on every parameter, and
  additionally checks its own *result* for non-finiteness (order 371088645964) to catch overflow
  that finite, individually-accepted inputs can still produce. Traced all four functions' guard
  orderings; none has a gap the sibling functions' equivalent guard closes.

## Questions (not findings)

1. **Carried forward from sweep63 batch03, still true, not re-derived at length.**
   `retry_synthesis.py`, `main()`: the run path's exit code (`return 0 if landed else 1`, line
   375) tracks only whether the *last save* to `SYNTHESIS_RETRY.json` landed, not whether every
   named source was actually rescued — a run in which several sources print "STILL FAILING" (the
   model genuinely returned nothing usable) but every save lands still exits 0. This may be
   intentional, matching `phase_synthesis`'s own treatment of a per-source model failure as
   routine and non-fatal to be picked up next run, and the "STILL FAILING" line is printed for
   each such source so nothing is silent on the console. Still true as of this read (line numbers
   unchanged); flagged again only because it is unresolved, not because it is newly found.

## Summary of findings by kind

- Fail-open guards: 0
- Tautological/unfalsifiable checks: 0
- Caps/truncations hiding a ranked listing (Hard Rule 0): 0
- Real logic bugs (wrong variable, off-by-one, races, inverted conditions, leaks): 0
- Docstring/comment vs. code mismatches: 0
- Silent exception swallowing that manufactures a negative: 0
- Dead code claimed live: 0
- Regex/escape corruption: 0 (all eight modules carry and pass their own `_BAD_CHARS` guard at
  import time)
- `wiki_source.py` MIN_GAP/rate-limiting: correct at 0.15s, verified against the module's own
  incident history; not a regression toward the 0.01s setting that caused the fandom.com IP ban

## Coverage

Recorded via `sweep_plan.record('run64', ['standards.py', 'overwatch.py', 'wiki_source.py',
'withdraw_chapters.py', 'backfill.py', 'retry_synthesis.py', 'catalogue_aurora.py', 'physics.py'],
batch=7)` for all eight modules listed above, each read in full this session.
