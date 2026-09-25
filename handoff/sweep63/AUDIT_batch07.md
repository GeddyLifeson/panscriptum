# sweep63 batch07 audit

Auditor for batch 7 of sweep63 (maintenance run #63, 2026-09-24). Read-only on `src/`, `data/`,
`state/` throughout (no file under those trees was edited). Did not run the pipeline, drill,
verify_math, mutate, publish, or anything else that writes state, other than the single
`sweep_plan.record(...)` call this report ends with.

## Scope (all under `src/`), read in full, start to finish, no sampling

- `standards.py` — 2,487 lines (read in ~900-line chunks, all four)
- `overwatch.py` — 1,136 lines
- `wiki_source.py` — 808 lines
- `withdraw_chapters.py` — 614 lines
- `scope.py` — 473 lines
- `recover_folder_records.py` — 380 lines
- `style_audit.py` — 342 lines
- `ledger.py` — 220 lines
- `chord_field.py` — 210 lines

Total: 6,670 lines across 9 modules, all read.

## Context / prior audits consulted

`CLAUDE.md` (Hard Rule -1 escalation/halt, Hard Rule 0 no caps, fail-closed, "a check that
cannot fail looks exactly like a check that passed") read first. Grepped `handoff/sweep61/` for
these nine module names and read every prior audit that named one:

- `AUDIT_batch07.md` (sweep61) covered `standards.py`, `wiki_source.py`, `withdraw_chapters.py`,
  `ledger.py` among others, and reported one VERIFIED finding: `standards.py`'s "cached records
  that were fully read" standard read only the first 700 bytes of each `data/readfeats/*.json`
  record, so a complete record (`chunks_unanswered: 0`) with a long `pages` list could
  misreport as unanswered.
- `AUDIT_batch03.md` (sweep61) covered `recover_folder_records.py` among others: no findings in
  that module.
- `AUDIT_batch06.md` (sweep61) covered `overwatch.py` and `scope.py` among others, and reported
  one VERIFIED finding: `overwatch.py`'s digest-retirement loop never retires a finding whose
  module file was deleted (`_digest()` returns `""` on `FileNotFoundError`, which is falsy and
  so never satisfies `d and d != f.get("digest")`). Also noted `scope.py`'s `ceiling_for()` as
  already self-reported dead code (order `de43fe54feb7`) — not re-reported.
- `AUDIT_batch12.md` (sweep61) covered `style_audit.py` and `chord_field.py` among others: no
  findings in either module.

**Both VERIFIED findings from sweep61 have since been fixed in the code read this batch:**

1. `standards.py`'s "cached records that were fully read" check (around line 1234-1269) no
   longer reads a 700-byte head. It now `json.load`s the whole record and checks
   `rec.get("chunks_unanswered") != 0`, with an inline comment citing "sweep61 batch07" and the
   measured false-positive count (40 of 3,463) as the reason for the change.
2. `overwatch.py`'s retire loop (around line 948-966) now checks `os.path.exists(_mp)` first and
   retires the finding immediately if the module file is gone, before falling through to the
   digest comparison — with an inline comment citing "sweep61 batch06" verbatim.

Per the brief, this codebase is unusually self-documented: nearly every non-obvious line carries
a comment naming a prior order ID, the incident that motivated it, and how the fix was verified.
I read every one of those against the code beside it and did not re-report anything the code
already names and handles. I specifically hunted, in priority order, for: (1) checks that cannot
fail; (2) fail-open guards; (3) caps/truncations/top-N/sampling (Hard Rule 0); (4) real logic
bugs (wrong variable, off-by-one, unit mix, races on shared files not routed through
`silence.replace_retry`/compare-and-swap, resource leaks, exception paths that corrupt state);
(5) anything that could open `prose_enabled`/`step4_enabled` or lift a halt; (6) regex/escape
corruption.

## Findings

**None.** No new VERIFIED and no new SUSPECTED findings in any of the nine modules, beyond the
two sweep61 findings confirmed fixed above.

Things specifically checked and ruled out, by module:

- **standards.py**: every `MIN_`/`MAX_` floor is genuinely wired into `check()` (the file's own
  "every declared floor is measured" self-check, itself verified by reading its regex against
  the whole file rather than trusting the self-check to have caught its own drift). All ~30
  `try/except` blocks around individual standards correctly route a failed measurement to
  `_dropped` (never a silent green) — spot-checked several against the "every standard could
  read its own input" aggregate at the bottom. `job_stamp`, `read_progress_verdict`,
  `context_verdict`, `charter_regression_verdict`, `provider_pool_denominator` are all pure
  functions with explicit tri-state (`True`/`False`/`None`-as-unmeasured) contracts, and every
  caller respects the contract (no place reads `None` as agreement).
- **overwatch.py**: the ledger merge (`_merge_ledgers`, `_progress`, `_finished_at`) is monotone
  and idempotent as its docstring claims; a corrupted non-dict `seen` entry inherited from disk
  is protected by the `not isinstance(old, dict)` short-circuit before any `.get()` is called on
  it. `_ask`'s local/cloud budget (`_LOCAL_BUSY`, `CLOUD_BUDGET`) is correctly reset once per
  round in `round_once`, matching its own comment about the bug that motivated the reset.
  `verify_open` only stamps `last_verified` on findings the model actually answered for (not on
  yielded ones), matching `review`'s identical `complete` discipline for the `seen` stamp.
- **wiki_source.py**: `resolve_wiki` consults `WIKI_HOSTS.json` before guessing, refuses to
  spend fandom-facing guesses against a source already known to be non-fandom, and every
  category/member/rank-by-size walk now raises on a mid-walk transport failure rather than
  silently returning a truncated prefix (verified each of `all_categories`,
  `category_members`, `extracts`, `rank_by_size` individually, matching each function's own
  "order de0681cb9edc" comment). `page_texts`'s `zip(..., strict=True)` over `pool.map` output
  is order-preserving and correctly paired with its input titles.
- **withdraw_chapters.py**: `_file_state`/`_archive_name_free` correctly distinguish "positively
  absent" from "could not be determined" (never treating a stat failure as an on-disk absence);
  `_land_merged` and `mutate`-style compare-and-swap patterns are used for both the withdrawal
  manifest and `catalog.json`, both gated on their landed verdict, and the final return code
  (`bad = ...`) folds in every refusal class (stuck, unreadable, collided, stray_stuck, denied
  writes) rather than only the ones printed.
- **scope.py**: `ProbeUnread` correctly distinguishes a genuine empty search (cached) from a
  probe that never got an answer (never cached, always retried); `mutate()`'s compare-and-swap
  is applied consistently by `build()` (`probed`, key-wise) and by `--host` (single key), so a
  concurrent `--build` crawl and a hand `--host` re-probe cannot clobber each other.
- **recover_folder_records.py**: the `mapped is None` vs. `mapped == []` distinction (empty
  FOLDER_SOURCE_MAP entry vs. absent one) is handled correctly and routes to the right bucket;
  the declared-vs-yielded shortfall accounting is recorded even when a source turns out already
  populated (harmless — it is diagnostic output, not a decision that changes behavior).
- **style_audit.py**: `TURN_ENDING`'s `\Z`-anchored, `re.M`-free regex genuinely does not match
  mid-record paragraph breaks (traced by hand against the self-test's GAMMA/DELTA fixtures); the
  `--self-test` fixtures assert by name and exact count in both directions (over-collapse and
  over-fire), and do exercise `turn_endings`/`em_per_entry`, matching the file's own comment
  that an earlier self-test never touched either detector.
- **ledger.py** / **chord_field.py**: both are self-consistent, small, and carry no caller
  outside `verify_math.py`'s battery (by ruling, not by omission — see `ledger.py`'s own "HELD
  FOR A FUTURE PHASE" doctrine, order `3fb9fc6b9999`). `assay_to_standards`'s M10 top-band
  handling (no edge above the ceiling) is argued and anchored correctly against
  `tempus.band_resolution`'s precedent, without the exact bug that precedent was fixed for
  (`hi == lo`, verified it does not recur here). No live math errors found in either module's
  pure functions.

## Questions

None met the bar for reporting. Nothing in this batch presented a design ambiguity worth
flagging to a human that the code's own comments had not already settled.

## Coverage

Recorded via `sweep_plan.record('run63', [...], batch=7)` for all nine modules listed above,
each of which was read in full this session (none substituted or skipped).
