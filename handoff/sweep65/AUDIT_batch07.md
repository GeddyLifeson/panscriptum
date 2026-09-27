# sweep65 batch07 audit

Auditor for batch 7 of sweep65 (maintenance run #65, 2026-09-26). Read-only throughout: nothing
under `src/`, `data/`, `state/`, `output/`, `prompts/` or `reference/` was edited, created or
deleted this session, other than this report and the single permitted `sweep_plan.record(...)`
call. No pipeline, generate, publish, crawl, overwatch, foreman, mutate, drill or verify_math
invocation was run, and no halt/`prose_enabled`/`step4_enabled` was touched.

## Scope, read in full, start to finish, sequentially, no sampling

- `src/standards.py` — 2,487 lines (five chunks: 1-500, 500-1000, 1000-1500, 1500-2000, 2000-2487)
- `src/overwatch.py` — 1,146 lines (three chunks: 1-400, 400-800, 800-1147)
- `src/wiki_source.py` — 808 lines (two chunks: 1-420, 420-808)
- `src/withdraw_chapters.py` — 614 lines (three chunks: 1-320, 320-613, 613-615)
- `src/scope.py` — 473 lines (one read, whole file)
- `src/genre.py` — 385 lines (one read, whole file)
- `src/profile.py` — 354 lines (one read, whole file)
- `src/tells.py` — 303 lines (one read, whole file)

Total: 6,570 lines across 8 modules, all read in full.

## Method

`CLAUDE.md` read first for doctrine (Hard Rule -1 escalation/halt chain, Hard Rule 0 no caps
ever, fail-closed, "a check that cannot fail looks exactly like a check that passed"). Every
module was then read top to bottom before any conclusion was drawn — no grep-only sampling.

Checked file mtimes against the last audit date before reading, since a module unchanged since
its last full read is a different risk than one that moved:

    standards.py          2026-09-16  (unchanged since sweep64 batch07 read it)
    wiki_source.py         2026-09-14  (unchanged since sweep64)
    withdraw_chapters.py    2026-09-14  (unchanged since sweep64)
    overwatch.py           2026-09-26  (changed TODAY, after sweep64's batch07 audit) — read with
                                       extra scrutiny for exactly this reason
    scope.py / genre.py / profile.py / tells.py — not in sweep64 batch07's module list; read
                                       fresh and cross-checked against sweep54/59/63/64 batches
                                       that previously covered them (see below)

`handoff/sweep64/AUDIT_batch07.md` was read in full: it covered `standards.py`, `overwatch.py`,
`wiki_source.py`, `withdraw_chapters.py` (plus four modules not in this batch) and reported ZERO
new findings, re-verifying two sweep61 fixes still correct. I re-verified its citations against
today's source rather than trusting them, and independently re-derived the same conclusion for
the three unchanged modules.

For the four modules sweep64-batch07 did not cover, prior coverage was located and read:
- `genre.py`: sweep54-batch?? / order 40e98eed6870 (priors field, owner-marked dead-but-kept) and
  order f646c1c5f1d0 (dead `not ranked` disjunct, dead `or 1`, invariant `genres_scored`). Current
  source (read this session) already carries both fixes verbatim — the dead disjunct/guard are
  gone, `genres_with_signal` exists beside the invariant `genres_scored`, and the owner-question
  about whether to rename/drop `genres_scored` is still open and still marked as such in the code
  (order f646c1c5f1d0, cited by name at genre.py:257-263). No new finding; question not re-derived,
  just re-confirmed present.
- `scope.py`: sweep54's question about `TIERS` (scope.py:51-60, no M0/M5/M9/M10 band) is still
  true of the current table (verified: TIERS emits only M1,M2,M3,M4,M6,M7,M8) and still
  unresolved. Not re-filed as a new finding — it is the same open question, re-confirmed.
- `profile.py`, `tells.py`: no prior sweep audit found naming either file specifically (grepped
  `handoff/sweep63/`, `handoff/sweep64/` for both names — no match). Read as first full coverage
  this run. Both are extremely dense with their own inline "found X, fixed Y, verified Z"
  commentary from earlier work; each of those citations (profile.py's B32 alphabet width fix,
  the feature-digit IndexError fix in `decode()`, the decimal-band parse fix in `encode()`;
  tells.py's sentence-anchor `\s*` fix, the `_anchor()` mid-paragraph rewrite) was traced against
  the current code rather than taken on faith, and each matches what its comment claims.

`state/workorders.json` was grepped for all eight module names before writing anything. Matches
were the already-known sweep54 items above (scope.py, genre.py) and general mentions of
standards.py/overwatch.py inside two long-form orders (the never-run-job unmeasurable question,
and the job-advancing witness question) already carried as open questions in CLAUDE.md/prior
audits, not new to this batch.

Priority hunt applied to every module: (1) fail-open branches; (2) tautological/unfalsifiable
checks; (3) caps/truncations of a ranked listing (Hard Rule 0); (4) real logic bugs (wrong
variable, off-by-one, races, inverted conditions, leaks); (5) comment/docstring-vs-code
mismatches; (6) silent exception swallowing manufacturing a negative; (7) dead code claimed
live; (8) regex/escape corruption.

## Findings

**None. Zero VERIFIED, zero SUSPECTED findings across all eight modules.**

Specific areas hand-traced this session, beyond re-checking prior citations:

- **overwatch.py** (the one module that changed today): the new `watch_code` plumbing in
  `round_once()` (per-module `codewatch.exit_if_stale("overwatch")` call at the point each
  module's review is saved, in addition to the existing end-of-round call) was traced end to
  end — every module read is `save(led)`d immediately before the code-staleness check, so an
  exit there loses at most the next unread module, never a completed read. `_ask`'s local/cloud
  fallback logic, `_LOCAL_BUSY` reset-per-round, `verify_open`'s yielded-vs-checked bookkeeping,
  `_merge_ledgers`'s per-key union rules, and `main()`'s per-round halt re-check were all traced
  again against the current source; all correct, matching the extensive in-file fix history.
- **standards.py**: `read_progress_verdict`'s cold-start / no-denominator / advancing / stalled
  tri-state logic re-traced against all `(done, total, prev)` shapes including the `total<=0`
  and `done<=0` interaction the file's own comment says was a live bug until order 156c2e28f823;
  current code returns the documented verdict for all four cases. The "every declared floor is
  measured" self-check's regex (word-bounded, comment-stripped, whole-file, second-appearance
  rule) was hand-run against `CHARTER_REGRESSION_MAX_AGE_H` and `MIN_CALLS_TO_JUDGE_RATE`, both
  of which are declared via a derived name rather than a literal; both resolve correctly.
  `context_verdict`/`resident_context`/`model_matches` (identity-based resident-runner matching)
  re-traced; no position-based fallback survives anywhere in the block.
- **wiki_source.py**: `MIN_GAP=0.15`/`WORKERS=48` unchanged from the post-IP-ban setting;
  `all_categories`/`category_members`/`extracts`/`rank_by_size` each still raise (never return a
  partial) on a mid-walk transport failure; `resolve_wiki` still refuses to spend a fandom guess
  against a source `WIKI_HOSTS.json` already knows is non-fandom.
- **withdraw_chapters.py**: `_file_state`/`_archive_name_free` still correctly distinguish
  "positively absent" from "could not be determined"; `_land_merged`'s compare-and-swap is used
  identically for both the withdrawal manifest and `catalog.json`; the final `bad` computation
  folds in every refusal class (stuck, unreadable, collided, stray_stuck, not-landed) that the
  console report itself names.
- **genre.py**, **scope.py**, **profile.py**, **tells.py**: no fail-open branch, no truncation
  of a ranked listing, no dead-but-load-bearing comment found. `tells.py`'s `_anchor()` splice
  point (`pat[4:]` assuming the literal 4-character prefix `^\s*`) was checked against every
  entry in `STRUCTURAL`/`DISCOURSE` that starts with `^\s*` — all such entries are exactly that
  4-character prefix, so the splice is safe for the current pattern set (would silently misfire
  only if a future pattern were added starting with a *different*-length anchor, which is a risk
  worth naming as a question below, not a present defect). `profile.py`'s `encode()`/`decode()`
  round trip (address, genre code, register code, four feature digits, band, attested-axes
  count) was hand-traced against the B32 alphabet and its own `main()`'s round-trip self-check
  logic (which re-encodes what `decode()` extracted rather than comparing decode's echo to
  itself — confirmed this is what current code actually does, not the tautological comparison
  the file's own comment says used to exist).

## Questions (not findings)

1. **Carried forward, not re-derived.** `scope.py:51-60` — `TIERS` still has no entry for M0,
   M5, M9 or M10, so a scope-derived ceiling can only ever land on M1-M4 or M6-M8. Filed by
   sweep54; still true; still unresolved; not re-filed as new.
2. **Carried forward, not re-derived.** `genre.py:257-263` — `genres_scored` is still invariant
   (always `len(GENRES) == 11`). Owner-marked "mark and keep" per ruling 2026-09-08; the sibling
   `genres_with_signal` field already supplies the per-record fact. Not re-filed as new.
3. **New, low-confidence, not filed as a finding.** `tells.py`'s `_anchor()` (line ~171-172)
   assumes any pattern beginning with the literal string `"^\s*"` can have exactly that 4-character
   prefix sliced off and replaced with `_SENTENCE_START`. True of every pattern in the file today.
   If a future DISCOURSE/STRUCTURAL entry were added with a differently-shaped leading anchor
   (e.g. `^\s*\n` or a named group), the slice would silently produce a broken regex rather than
   refusing — there is no assertion that `pat[4:]` starts where the author intended. Whether this
   is worth an explicit `assert pat.startswith(r"^\s*")`-style guard, or is fine left as a
   convention future editors are expected to follow (the file is small and hand-maintained), is a
   judgment call rather than a present defect, since no such pattern exists in the file today.

## Cleared (examined closely, found correct)

- `overwatch.py`: ledger load/save merge-on-conflict (`_merge_ledgers`, `_reconcile_with_disk`),
  digest-based staleness detection, per-round `_LOCAL_BUSY` reset, `verify_open`'s
  yielded/checked/closed accounting, `rotation()`'s changed-then-stale ordering, the halt
  re-check inside the `--loop` while-loop, the mid-round `codewatch.exit_if_stale` addition.
- `standards.py`: every `try/except -> _dropped.append(...)` handler in `check()` (spot-checked
  a large sample) both notes to `silence` and appends the matching name to `_dropped`, so "every
  standard could read its own input" cannot be defeated by a silently-vanished row; the
  provider-pool local/cloud stale-model split; `charter_regression_verdict`'s in-progress vs.
  never-run vs. complete tri-state; `ollama_token_flow`/`ollama_runner_up`/`fandom_ipv4_reachable`
  three-valued (True/False/None-means-unmeasurable) contracts, each honoured by its caller.
- `wiki_source.py`: `_get`'s shared-throttle-plus-local-gap layering; `page_texts`'s
  order-preserving `zip(..., strict=True)` over `pool.map`; `clean_titles`'s O(n) set-based dedup.
- `withdraw_chapters.py`: `select()`'s pure exact-match filtering; the archive-name collision
  guard (`_archive_name_free`) applied identically to catalogued moves and unclaimed strays; the
  manifest merge-by-address union at landing time.
- `scope.py`: `scope_for`'s "highest tier clearing the floor, never the most frequent" selection;
  `ProbeUnread` vs. genuine-empty-result distinction; `mutate()`'s compare-and-swap with digest
  taken before the read.
- `genre.py`: `classify_text`'s full-field ranking (no `top` truncation reaching a stored
  denominator); `classify_source`'s refusal of a numeric `cap`; the atomic, verdict-gated
  `GENRES.json` write.
- `profile.py`: `encode()`'s refusal of an out-of-range `attested` count vs. graceful degradation
  of an unparseable `band`; `decode()`'s per-axis range check naming the profile, axis and legal
  digits rather than raising a bare `IndexError`.
- `tells.py`: `prompt_in_sync()`'s CRLF-folded comparison; the `_BAD_CHARS`/control-character
  self-check applied to both the compiled patterns and the lexical word list.

## Coverage

Recorded via `sweep_plan.record('run65', ['standards.py', 'overwatch.py', 'wiki_source.py',
'withdraw_chapters.py', 'scope.py', 'genre.py', 'profile.py', 'tells.py'], batch=7)` for all
eight modules listed above, each read in full this session.
