# sweep66 batch07 audit

Auditor for batch 7 of sweep66 (maintenance run #66, 2026-09-27). Read-only throughout: nothing
under `src/`, `data/`, `state/`, `output/`, `prompts/` or `reference/` was edited, created or
deleted this session, other than this report and the single permitted `sweep_plan.record(...)`
call. No pipeline, generate, publish, crawl, overwatch, foreman, mutate, drill or verify_math
invocation was run, no network call was made, and no halt/`prose_enabled`/`step4_enabled` was
touched. No subagents were spawned.

## Scope, read in full, start to finish, sequentially, no sampling

- `src/standards.py` — 2,487 lines (five chunks: 1-500, 500-1000, 1000-1500, 1500-2000, 2000-2487)
- `src/overwatch.py` — 1,146 lines (three chunks: 1-400, 400-800, 800-1146)
- `src/wiki_source.py` — 808 lines (two chunks: 1-420, 420-808)
- `src/withdraw_chapters.py` — 614 lines (two chunks: 1-320, 320-614)
- `src/scope.py` — 473 lines (one read, whole file)
- `src/genre.py` — 385 lines (one read, whole file)
- `src/profile.py` — 354 lines (one read, whole file)
- `src/physics.py` — 312 lines (one read, whole file)

Total: 6,579 lines across 8 modules, all read in full. `wc -l` on the eight files confirms this
total exactly (2487+1146+808+614+473+385+354+312 = 6579).

## Method

`CLAUDE.md` was read first (already resident from a prior turn this session) for doctrine — Hard
Rule -1 (escalation chain, the halt, INDEPENDENT/FAIL CLOSED/PROVEN), Hard Rule 0 (no caps, ever).
Every module was then read top to bottom before drawing any conclusion.

Checked mtimes against the last full audit before reading, since a module unchanged since it was
last read in full is a different risk than one that moved:

    standards.py           2026-09-16  (unchanged since sweep65 batch07 read it)
    overwatch.py           2026-09-26  (unchanged since sweep65 batch07 read it -- that audit's
                                        "changed TODAY" refers to 2026-09-26, which is now
                                        yesterday and the file has not moved since)
    wiki_source.py         2026-09-14  (unchanged since sweep65)
    withdraw_chapters.py   2026-09-14  (unchanged since sweep65)
    scope.py               2026-09-09  (unchanged since sweep65)
    genre.py               2026-09-14  (unchanged since sweep65)
    profile.py             2026-09-16  (unchanged since sweep65)
    physics.py             2026-09-06  (unchanged since sweep65 batch03, which covered it in this
                                        batch's stead there)

All eight files are byte-for-byte unchanged since their last full read one day ago. That does not
excuse a shallower pass — the rules require reading every line regardless — but it does mean any
finding would have to be something two independent full reads both missed, not a regression.

`handoff/sweep65/AUDIT_batch07.md` was read in full: it covered `standards.py`, `overwatch.py`,
`wiki_source.py`, `withdraw_chapters.py`, `scope.py`, `genre.py`, `profile.py` and `tells.py`
(this batch has `physics.py` in place of `tells.py`) and reported **zero** findings, verifying
sweep64's account for the four unchanged modules and giving first coverage to the other four.
`handoff/sweep65/AUDIT_batch03.md` was also read (grep for `physics.py` across sweep65) — it gave
`physics.py` a full read that shift and likewise reported no gap: all four public functions
(`kinetic`, `joules_for`, `sphere_volume`, `binding_energy`) refuse non-positive, non-finite and
NaN inputs and additionally check their own result for non-finiteness (order 371088645964).

Every citation from both prior audits was re-verified against today's source rather than trusted,
and independently re-derived for all eight modules this shift (source-code review, not a re-run
of any script — see the rules on standalone reproductions).

`state/workorders.json` was grepped for all eight module names before writing anything. Matches:

- `withdraw_chapters.py` — order `1e6f99e54b25` (`CORPUS_WRITERS_WITHOUT_A_HALT_INTERLOCK`,
  handler OWNER, re-routed run→owner). Read in full: it cites `withdraw_chapters.py` as
  **precedent** for a halt interlock done right ("wired to the halt for exactly this reason ...
  each is now on verify_math's `_INTERLOCKED` roster"), not as an open defect in this module. The
  open question is whether four *other* tools (`generate.py`, `retry_synthesis.py --merge`,
  `repass_bands.py --apply`, `resync_roll.py`) should refuse under a standing halt the same way.
  Confirmed against source this shift: `withdraw_chapters.py:main()` still calls
  `escalation.assert_clear(os.path.basename(__file__))` before the argparse block and before the
  catalog read, so this module's own interlock is intact. Not a finding against this batch.
- `scope.py` / `genre.py` — order `5bb12b398783` (`SWEEP54_QUESTIONS_FOR_A_RULING`, handler
  OWNER). Item 2 is `scope.py:51-60`'s `TIERS` table (no M0/M5/M9/M10 entry); item covering
  `genre.py` is the sibling order below. Both are carried-forward open questions, not re-filed —
  see Questions below.
- `standards.py` — orders `d03706b5eaf0` (`SWEEP59_OWNER_QUESTIONS_ITEMS_1_AND_5`, item 2: should
  a managed job that has never produced a log read as unmeasurable?) and `d9328fe1ee38`
  (`STALL_STANDARD_WATCHES_THE_LOG_NOT_THE_WORK`, the dangerous half already fixed in
  `foreman.py`, the remaining half a policy ruling about what `standards.py` should *report* for
  a deliberately-unkillable slow job). Both owner-held, both already known from prior sweeps.
- `genre.py` — order `f646c1c5f1d0` (`GENRE_DEAD_DISJUNCTS_AFTER_UNCAPPING`). Mechanical half
  fixed and verified present in source (no `not ranked` disjunct at `genre.py:216` area, no dead
  `or 1`); the owner-held remainder is whether `genres_scored` (invariant at `len(GENRES) == 11`)
  should be dropped or repurposed now that `genres_with_signal` supplies the real per-record
  count. Confirmed still open, still marked in the code's own comment. Not re-filed.

No workorder matches were found for `overwatch.py`, `wiki_source.py`, `profile.py` or
`physics.py` beyond the general standards.py-related orders above.

Priority hunt applied to every module: (1) fail-open branches; (2) tautological/unfalsifiable
checks; (3) caps/truncations of a ranked listing (Hard Rule 0); (4) real logic bugs (wrong
variable, off-by-one, races, inverted conditions, leaks); (5) comment/docstring-vs-code
mismatches; (6) silent exception swallowing manufacturing a negative; (7) dead code claimed live;
(8) regex/escape corruption.

## Findings

**None. Zero VERIFIED, zero SUSPECTED findings across all eight modules.**

Areas given specific hand-tracing this shift, independent of the prior audits' own citations:

- **standards.py**: the `check()` function's ~30 `try/except -> _dropped.append(...)` blocks were
  spot-checked in both directions — that a genuine failure (missing file, bad JSON, a raised
  exception) is caught and routed to `_dropped` rather than silently vanishing the standard, and
  that a genuine success still reaches `out.append`. The "every declared floor is measured"
  self-check (`_re.findall(wordb + _re.escape(d) + wordb, code_all)`, requiring a *second*
  appearance beyond the declaration) was hand-run against `MIN_CATALOGUE_COVERAGE`,
  `CHARTER_REGRESSION_MAX_AGE_H` and `MAX_PROVIDER_MODELS_AGE_H` — all resolve correctly, each
  used at least once beyond its own declaration line. `read_progress_verdict`'s four-state
  contract (`done<=0` cold start, `total<=0` unmeasurable, `done>=total` complete, else
  advancing-or-stalled via `job_stamp`) was traced against all combinations by hand; matches its
  docstring exactly.
- **overwatch.py**: `_merge_ledgers`'s per-key union (findings by `_progress` rank, `seen` by
  later `at`, `rounds` by max, `last_run` by max-as-string) was traced against `_STATE_RANK` and
  `_finished_at`'s numeric/string-timestamp normalisation — a record whose `retired_at`/
  `closed_at` is stored as an epoch float, an epoch-as-string, or a `"%Y-%m-%d %H:%M[:%S]"`
  string all resolve to a comparable float, with an unparseable stamp sorting oldest (never
  displacing a good record). `verify_open`'s and `review`'s "only a completed answer gets
  stamped" discipline (a `None` from `_ask` — the GPU-busy yield — leaves `last_verified`/`seen`
  untouched rather than advancing them) was re-traced end to end.
- **wiki_source.py**: `resolve_wiki`'s three-way branch on `WIKI_HOSTS.json` (a known fandom host,
  a known *non*-fandom host, no host at all) was re-traced against `_api`'s hardcoded
  `fandom.com` — confirmed a known non-fandom host still returns `(None, None)` rather than
  spending guesses against a banned edge. `all_categories`/`category_members`/`extracts`/
  `rank_by_size` were re-confirmed to raise (never return a partial list) on a mid-walk failure,
  and the `(subdomain, min_pages, hard_stop)` cache key was checked against every call site in
  this file — none passes a non-`None` `hard_stop`, so the dormant cache-key gap order
  `83bf7498d135` names is still dormant, not live.
- **withdraw_chapters.py**: `_file_state`'s three-way stat/listdir classification (`live`/`gone`/
  `unavailable`) and `_archive_name_free`'s identical shape were re-traced against every call
  site; both correctly treat a lock/denial/unparseable-path as `unavailable` (record kept) rather
  than as absence. `_land_merged`'s compare-and-swap (digest taken before the read, refusal on a
  changed digest, an absent file routed to `state="absent"` vs. a corrupt one to
  `state="unparseable"`) was traced for both the withdrawal manifest and `catalog.json` call
  sites in `main()`.
- **scope.py**: `ProbeUnread` vs. a genuine empty result was traced through `scope_for` end to
  end — every `F.api` call checks `oc.get("ok")` before treating an empty response as evidence,
  and the one documented clean negative (`http-404`) is the only `why` that does not raise.
  `mutate()`'s compare-and-swap (digest before read, refusal on a changed digest, an unreadable
  file refusing rather than being overwritten) matches the pattern the file's own docstring
  attributes to `roll.mutate`.
- **genre.py**: `classify_text`'s Counter-based scoring was confirmed to create a key for every
  genre in `GENRES` regardless of match (so `ranked` can never be empty, making the removed
  `not ranked` disjunct genuinely dead rather than merely rare), and `classify_source`'s
  `cap is not None` refusal (a loud `SystemExit`, not a silent truncation) was checked against
  its only description in the docstring.
- **profile.py**: `encode()`/`decode()` round trip re-traced by hand for the band field
  specifically — `encode` clamps a parsed decimal-band tier to `10` before indexing `B32[tier]`,
  and `BANDS` has exactly 11 entries (`M0`..`M10`), so `decode`'s `BANDS[B32.index(band)]` cannot
  index out of range for anything `encode` itself produces. The feature-digit range check in
  `decode` (`i >= len(tbl)` raising a readable error naming the profile, axis, character and
  legal digit set) was checked against all four `AXES` tables.
- **physics.py**: full re-read confirms sweep65 batch03's account exactly — `kinetic`,
  `joules_for`, `sphere_volume` and `binding_energy` each refuse non-positive, non-finite and NaN
  arguments (with `binding_energy` correctly allowing `mass_kg == 0`, unlike the other three'
  strict `> 0.0` on their positional argument, since `M=0` is a physically valid unbound body
  rather than an unestimable one) and additionally check their own arithmetic result for
  non-finiteness to catch overflow from individually-finite, individually-accepted inputs.

No regex/escape corruption in any of the eight modules — each carries and passes its own
`_BAD_CHARS` self-check at import time (verified by reading the check itself in each file, not
merely trusting its presence, and confirming none of the eight files contains chr(8)/chr(11)/
chr(12)/chr(7) by inspection while reading).

## Questions (not findings — owner-held, carried forward, not re-derived)

1. **`scope.py:51-60`** — `TIERS` still has no entry for M0, M5, M9 or M10 (the ordered list
   jumps nation→continent→planet→star system→galaxy→universe→multiverse, mapping to
   M1,M2,M3,M4,M6,M7,M8 only), so a scope-derived ceiling can never land on those four bands.
   Filed by sweep54 (order `5bb12b398783`); still true of the current table; still unresolved;
   not re-filed.
2. **`genre.py:257-267`** — `genres_scored` is still invariant at `len(GENRES) == 11` for every
   record, carrying no per-record information (the sibling `genres_with_signal` field already
   supplies the real per-record count). Owner-marked "mark and keep" per order `f646c1c5f1d0` and
   the 2026-09-08 ruling; not re-filed.
3. **`standards.py`** — the two open items under `d03706b5eaf0` (should `standards.py`'s "jobs
   that are ADVANCING" read a job that has *never* produced a log as unmeasurable rather than
   stalled?) and `d9328fe1ee38` (should the stall standard report a deliberately-unkillable slow
   job, e.g. one throttled 32x by a host backoff, differently from a genuinely wedged one?) are
   both still open in `state/workorders.json`, both owner-held policy questions rather than
   defects, and both confirmed unchanged against current source. Not re-filed.

No new questions were found this shift beyond re-confirming these three carried-forward ones.

## Cleared (examined closely this shift, found correct)

- `standards.py`: the ~30-strong `_dropped`/`silence.note` green-by-absence defence in `check()`;
  `charter_regression_verdict`'s never-run/mid-pass/complete tri-state; `context_verdict`/
  `resident_context`/`model_matches`'s identity-based (not position-based) resident-runner match;
  `provider_pool_denominator`'s verified/unverified split; the self-check regex over
  `MIN_/MAX_`-prefixed constants.
- `overwatch.py`: `_merge_ledgers`/`_reconcile_with_disk`'s per-key union rules; `_finished_at`'s
  numeric/string timestamp normalisation; `verify_open`'s only-stamp-on-a-real-answer discipline;
  `rotation()`'s changed-then-longest-unread ordering; the mid-round `codewatch.exit_if_stale`
  call added 2026-09-26.
- `wiki_source.py`: `resolve_wiki`'s known-fandom/known-non-fandom/unknown three-way branch;
  `all_categories`/`category_members`/`extracts`/`rank_by_size`'s raise-never-partial contract;
  `page_texts`'s order-preserving `zip(..., strict=True)`; `clean_titles`'s O(n) dedup.
- `withdraw_chapters.py`: `_file_state`/`_archive_name_free`'s stat-then-listdir positive-absence
  test; `_land_merged`'s compare-and-swap for both the manifest and the catalog; the per-entry
  `entry_left`/`amended` bookkeeping for a half-succeeded move.
- `scope.py`: `ProbeUnread` vs. genuine-empty distinction in `scope_for`; the "highest tier
  clearing the floor, never the most frequent" selection; `mutate()`'s compare-and-swap.
- `genre.py`: `classify_text`'s full-field, uncapped ranking; `classify_source`'s loud refusal of
  a numeric `cap`; the atomic, verdict-gated `GENRES.json` write with its correct return code.
- `profile.py`: `encode()`'s refusal of a non-int or out-of-range `attested`; `decode()`'s
  per-axis range check naming the profile, axis and legal digits; the band clamp/index pairing.
- `physics.py`: all four public functions' guard ordering (positive → finite → NaN-safe →
  result-finite) and the OverflowError-to-ValueError re-raise in `sphere_volume`/`binding_energy`
  that renames an arithmetic exception as the domain error that actually caused it.

## Coverage

Recorded via `sweep_plan.record('run66', ['standards.py', 'overwatch.py', 'wiki_source.py',
'withdraw_chapters.py', 'scope.py', 'genre.py', 'profile.py', 'physics.py'], batch=7)` for all
eight modules listed above, each read in full this session.
