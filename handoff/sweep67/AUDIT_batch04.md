# Sweep 67 (run67) - AUDIT batch 04

## Scope

Read in full, sequentially, with the Read tool, nothing skimmed. Read-only; no daemon, phase, drill,
verify_math, publish, generate or mutate run was started. No subagent. Scratch scripts only under
%TEMP% (`aud67_b4.py`; it imports `suppressions` with `FILE` pointed at a temp file and touches nothing
in the kit).

| module | lines |
|---|---|
| src/mutate.py | 3314 |
| src/threads.py | 1063 |
| src/estate.py | 723 |
| src/handbuilt.py | 550 |
| src/suppressions.py | 448 |
| src/cosmography.py | 381 |
| src/tuning.py | 286 |
| src/lognames.py | 74 |

## Prior-audit cross-check (handoff/sweep66/AUDIT_batch*.md)

- **mutate.py, sweep66 B04 Question 1 (`--list` refused under a halt while `--list-ruled` /
  `--rule-equivalent` / `--unrule` are exempt):** still stands, unchanged. `main()` runs the three registry
  commands before `escalation.status()` (mutate.py:2804-2846), and `--list` (mutate.py:2856) after the halt
  check (2849). Carried as Question 1, not re-filed.
- **mutate.py, sweep66 B04 (canon_backup `--keep 0`)**: not in this batch.
- **estate.py (sweep66 B05):** no finding or question on file. Re-read: `_effective_ext`, `inspect()`'s stat
  retry, the per-extension read strategy, `charter()`'s table-driven errata and the vanishing-row repairs are
  all as described. On this interpreter (3.13.9) `ast.parse` raises `SyntaxError` for a NUL byte
  (verified), so `inspect()`'s `except SyntaxError` is sufficient; on 3.11 or older it would be `ValueError`
  and escape the thread pool. Nothing to file.
- **handbuilt.py (sweep66 B09 Question 2, "no halt check"):** RESOLVED. `_assert_not_halted()`
  (handbuilt.py:440-464) now exists and `main()` calls it before the write (handbuilt.py:476), fail closed
  on `ImportError`. The question is closed by the 2026-09-28 ruling. (Question 1 of that audit is
  `resync_roll.py`, not this batch.)
- **cosmography.py (sweep66 B11, `7099a092abd3`, "thirteen functions with no production caller"):**
  RESOLVED for this file. Both functions here (`kardashev_K`, `kardashev_to_magnitude`) now carry the
  "RETAINED WITH NO PRODUCTION CALLER, BY OWNER RULING" comment (cosmography.py:205-217). Re-verified by
  grep: their only callers are `verify_math.py:1080-1088`. `GALAXIES_CONSELICE_2016`, `STARS_MILKY_WAY` are
  read by nothing, as the comments say (they say so themselves; not a finding).
- **threads.py (sweep66 B16, `325ccb493c45`, `annex_join_unmatched` only reported):** RESOLVED. `build()` now
  raises `AnnexJoinUnmatched` on a whole-corpus build (threads.py:669-688), and order `28f335ecefd3` item 3
  is fixed (`siblings` is built from `source_codes`, threads.py:597-601). Both confirmed by reading the code.
- **suppressions.py (sweep66 B10):** cleared then; `MAX_TTL_DAYS`/`_valid_ttl` (order 34ec8a90c42f item 8) are
  new since and read correctly (bool, non-finite, zero, negative and over-365 are all refused).
- **tuning.py, lognames.py (sweep66 B08):** zero findings then. `lognames.PRODUCT` (order d9328fe1ee38) is new
  since; every path it names exists on disk (checked) and every key is also a key of `OWNER`.

## Findings

All are LOW. None reaches the pipeline output, the halt chain or any published number.

### F1. mutate.py:3247 (with 3160-3209) - work orders are filed from a target whose verdicts were declared void
`_session` sets `rc, stopped_at = 4, i` when `restored_exactly` is false (3160-3167) or
`live_file_untouched` is false (3168-3209) and prints "THIS RUN'S VERDICTS FOR IT ARE VOID". It then falls
into the `if a.file_orders and r["survivors"] and confirm:` block (3247) for the same target, which files
every survivor as a MAJOR `RUN` work order via `file_orders`. The comment at 3268 justifies printing the
findings ("still worth printing"), not filing them. For the live-file case the sandbox copy is by
definition stale, so the filed `was`/`became` text and line number may describe source that no longer
exists, and the order text carries no "void" caveat. Severity LOW (needs `--file-orders` plus a foreign edit
during a multi-hour pass, and the run exits 4 with a partial banner). Fix: guard the filing with
`stopped_at is None or i < stopped_at`, or `and not (rc == 4 and stopped_at == i)`, i.e. do not file for the
target that tripped the check.

### F2. mutate.py:2189 - the "root is the live tree" refusal is case- and separator-sensitive
`_abs == os.path.abspath(HERE)` and `abspath(join(_abs, "src")) == SRC` compare strings. On Windows the same
directory spelled `c:\users\...` does not equal `C:\Users\...`. Reproduced: `abspath(here.lower()) ==
abspath(here)` is False, `normcase` equal is True. So `run(target, root=<lower-cased HERE>)` passes the
guard that the surrounding comment (2169-2196) says exists to stop mutants being written into real `src/`.
No caller does this today (the comment says so); severity LOW. Fix: compare `os.path.normcase(os.path.realpath(...))`
on both sides (realpath also covers a junction pointing at the live tree).

### F3. mutate.py:1185-1189 - stale comment against `OWNERSHIP_CEILING_SECONDS`
`_owner_pid`'s docstring still says the ceiling is "comfortably longer than the longest plausible mutation run
(hours)" and that a recycled pid "can strand a directory for at most one day". The constant directly above
(1166) was raised from 24h to 72h in run #59, and its own comment (1159-1165) says a full pass takes about 30h.
The docstring now understates both the run length and the strand window by 3x. Fix: say 72 hours and "about
30 hours".

### F4. mutate.py:1055-1069 - `_write_rulings` is a bare read-modify-write with a fixed temp name
`rule_equivalent` and `unrule_equivalent` read the registry (`ruled_equivalent`), edit a dict, then
`_write_rulings` writes `path + ".tmp"` and `os.replace`s it. Two concurrent invocations collide on the temp
file, and the second read-modify-write silently drops the first's ruling (lost update); a denied replace
(the ordinary Windows case) raises out of `os.replace` with the `.tmp` left behind. The brief's rule is that
shared state goes through `silence.write_json` / `replace_retry` (handbuilt.py:487-497 records the identical
repair). The comment (1061) says it is only called from the two human CLI flags, so the exposure is small;
LOW. Fix: `silence.write_json(path, {...})` for the write, or reuse `suppressions._mutate`'s
`replace_if_unchanged` pattern.

### F5. mutate.py:250-256 - clearing a stale lock can delete a freshly created one
`_lock_acquire` reads `active()` -> (False, stale rec), then `os.remove(LOCK)`, then `O_EXCL` create. Two
runs starting together with a dead holder's record on disk: A removes the stale file and creates its own; B,
which read the stale record before A's create, then removes A's fresh lock and creates its own. Both believe
they hold it; A's `_lock_release(token)` later sees B's token and leaves it (mutate.py:305-308), so
publish.py's refusal window is shortened. The order a693fe8a33cc repair closed check-then-create for the live
case but not the stale-clear step. Consequence is bounded because mutation is sandboxed (the live tree is
never at risk), so publish.py's block is the only thing affected; LOW. Fix: remove the stale file only if its
contents still equal the stale record just read (or `os.replace` it to a unique name and let `O_EXCL` decide).

### F6. mutate.py:1699-1706 and 2249-2252 - two quiet gaps in sandbox setup
(a) The `state/` copy loop swallows `OSError` with a bare `pass` (1705-1706), the only copy in `sandbox()`
that leaves no `silence.note` (its siblings note at 1613, 1662, 1735, 1864, 1876). A `.json`/`.jsonl` the
gates read that fails to copy then shows up only as a red baseline row, with nothing saying it was a sandbox
copy failure rather than a library fault - the exact confusion the surrounding comments (1663-1693) were
written to prevent. (b) `_run_mutation` builds the sandbox at 2249 and reads `live_before` at 2252, both
before the `try:` at 2254, so a `FileNotFoundError` on the live target (file being replaced) leaks the whole
sandbox until `reap_orphans` ages it out (72h if the owner pid is recycled). Both LOW. Fix: `silence.note` in
(a); move 2251-2252 inside the `try`, or compute `live_before` before `sandbox()`.

### F7. suppressions.py:103-106, 307, 329, 387-392 - a wrong element type in the list raises instead of failing closed
`_load` checks that the top level is a list but not that its elements are objects with numeric `expires_at`
and string `path`. Reproduced against a temp file: `["oops"]` makes `active()`, `suppressed()` and
`problems()` all raise `AttributeError: 'str' object has no attribute 'get'`; `expires_at: "soon"` raises
`TypeError` in all three; `path: null` raises `TypeError` in `suppressed()` and `problems()`. `active()`'s
docstring (301-304) promises "an unreadable file returns no active suppressions -- FAILS CLOSED", and the
`_load` comment (94-102) argues that a wrong shape is corruption to be reported as `ok=False`. The
element-level shape is the same class of half-finished hand edit and is not covered. Effect in practice is
loud, not silent: `publish.py:630` wraps the call in `except Exception: supp = None`, so the scanner runs
unsuppressed (correct direction), but `problems()` raises rather than reporting `UNREADABLE`, and
`drill.py:5422-5428` would crash rather than report. LOW. Fix: in `_load`, return `([], False)` unless every
row is a dict with a str `detector`, str `path` and numeric `expires_at`.

### F8. threads.py:261 and 285 - `annex_codes()` / `law_codes()` crash on a wrong-shaped file, contrary to their docstrings
Both promise "EMPTY set if unreadable" and fail closed. The `try` covers only `open` and `json.load`; the
`doc.get("canons")` / `doc.get("laws")` and `c.get("code")` calls sit outside it. A file whose top level is a
list (or whose canon rows are strings) raises `AttributeError` out of `build()` (not a `ThreadRefused`, so
`main()` prints a traceback instead of "REFUSING TO DERIVE"), and out of `verify()` and `threads_for` for a
reader of THREADS.json. Still nothing is written, so this is fail-closed in effect but not in the documented
manner. LOW. Fix: `if not isinstance(doc, dict): note; return set()`, and `isinstance(c, dict)` in the
comprehension.

### F9. threads.py:118-119, 938, 969 - stale text about T4
The comment above `DERIVABLE` (118-119) says "T4 is a later phase; T5 is owner-authored only and is not in
this tuple"; T4 is in the tuple (141) and the next 20 lines say it was admitted under section 7H. The CLI's
argparse description ("derive the T1/T2 thread graph", 938) and banner ("Phases 4.1 and 4.3 (T1 home + T2
cohort + T3 Chronicle join)", 969) omit T3-and-T4 status inconsistently (the banner names T3 and prints a T4
line six lines later, the argparse text names neither). Comment/text rot only; LOW. Fix: reword the three
strings.

### F10. handbuilt.py:377-378 (and 111-112, 270-272) - superlatives in the shipped data that the data contradicts
Getter Emperor's `sustain` rationale ends "The highest sustain in the library". Measured by running
`handbuilt.compute()`: sustain 9.5 is a three-way tie (Getter Emperor, The Black Winter, The Internal Revenue
Service). Rune King Thor's volition rationale says "The highest volition in the library, and it is not close"
(9.5 against 9.0 for The Undertaker). Undertaker's suasion says "THE HIGHEST-EARNED SCORE IN THIS LIBRARY" for
9.9, which equals his own continuity 9.9. These strings are written verbatim into
`data/HANDBUILT_ASSAYS.json` as `cited` text (handbuilt.py:435-436), i.e. into the record, not just a
comment. No score is affected. LOW. Fix: drop the comparatives, or say "tied for" and name the tie.

### F11. tuning.py:193 - a read-only probe creates the database it is probing
`cloud_success_rate()` calls `sqlite3.connect(path, timeout=2.0)`, which creates an empty
`state/cascade_scratch.db` when it is absent, then fails on `select ... from usage` (no table) and returns
`(None, 0)` "no evidence". mutate.py:1746-1751 already documents this behaviour as the cause of a red baseline
("`tuning.cloud_success` connects without `mode=ro`, which CREATES an empty file"), and `cascade_bridge.provider_error`
opens the same file read-only. The side effect is an empty file where cascade's own creation logic may expect
none, written by a function whose docstring calls it a read. LOW (the file exists on this machine today at
22 MB, so it is dormant). Fix: `sqlite3.connect("file:%s?mode=ro" % path, uri=True, timeout=2.0)`, as
mutate.py:1769 already does for its own read.

## Questions

1. **mutate.py `--list` refused under a halt** while the three registry commands are exempt (carried from
   sweep61 / sweep65 / sweep66, unchanged; mutate.py:2849-2856). Counts, mutates nothing, fail-closed. Not
   re-filed.
2. **mutate.py:457 and 2277 - `str.splitlines` versus `ast` line numbers.** `_mutations` and `_run_mutation`
   both index `text.splitlines(keepends=True)` by `node.lineno - 1`. `splitlines` also breaks on `\x0b`,
   `\x0c`, `\x1c-\x1e`, `\x85`, `\u2028` and `\u2029`, which `ast` does not count as newlines, so one such
   character anywhere in a target would shift every later mutant onto the wrong line (a false kill or a
   survivor row naming the wrong line). Checked: none of those characters is present in assay.py,
   prose_gate.py or escalation.py today (assay.py is CRLF, which both handle identically). Latent; is a guard
   (`len(lines) == text.count(...)`-style, or `re.split` on `\r\n|\r|\n`) wanted?
3. **threads.py:831-848 - `verify()` does not pin T2 edges to class T2 or to `from == rec["code"]`.** Every
   edge in `T2` lists is only checked for `class in DERIVABLE` and `to in known`, so a round trip that turned a
   `T2` into a `T1` or `T3` edge would pass. The comment block (873-884) argues carefully against tautological
   checks elsewhere; this one is a check that can fail on less than it could. Deliberate breadth or an
   oversight?
4. **threads.py:773-781 - `threads_for` re-reads and re-parses `LAWS.json` for every magnitude-asserting entry**
   (`_known_for_t4` -> `law_codes()`), and if the file is unreadable it emits one `silence.note
   ("threads.py:t4-refused")` per such entry (447 today). The degradation itself is documented and right; is the
   per-entry note wanted, given that `_touch_root`'s comment in mutate.py explicitly avoids the same litter?
5. **tuning.py:61-66 - a stale POOL_PROOF is counted at full strength.** Already marked open by its own comment
   (m59); noted only so it is not mistaken for new. Unchanged since sweep66.

## Cleared (read start to finish, nothing found beyond the above)

- **mutate.py**: `_mutations` (per-node span location, `_col` byte-to-char conversion, `_between` gap search,
   `_token_pos` boundaries, the `_fallback_next` cursor, dedup keyed on resulting text); `_row_ids`;
  `_gate_result`'s signature/side-channels; `hang_confirms_a_kill`'s two independent pristine readings;
  `unusable_gates`/`red_gates`/`could_not_judge` prefix matching; `_run_mutation`'s live-root refusal (other
  than F2), missing-baseline and ungauged-gate refusals, restore probe, `hang_kills` accounting, per-survivor
  `red_gates_disabled` copies and `_refresh_baseline`'s discard of an unusable refresh; the killed +
  survived + indeterminate == mutants arithmetic; `file_orders`' stale/moved-ruling text; `_journal`
  append-only never-raising; `journal_rows`/`survivors_on_record`/`suppressed_on_record` filters;
  `ruled_equivalent` fail-toward-reporting; `ruling_mismatch`; `reap_orphans`' ownership-beats-age with the
  72h ceiling and the junction-unlink-before-rmtree; `_remove_sandbox`; the BUILDING_PREFIX rename dance; the
  data/ hardlink-per-file design; `tree_is_moving`'s fail-closed answers; `--detach` argv rebuild;
  `_session`'s halt ordering, red-baseline refusal only in combination with a moving tree, rc propagation
  and the `stopped_at` break. The `limit` slice (2272-2275) is a disclosed interactive convenience reported
  as `capped`/`mutants_attemptable`; not a Hard Rule 0 breach.
- **threads.py**: `cohort_family` (two-component codes), `category_path` (subroom-then-topic with parent
  check), `survey`, `build`'s T1/T2/T3 derivation, uncapped cohort lists (the only slice in the file is
  `parts[:2]`, matching the docstring's claim), `counts`, `threads_for`'s refusal for an unaddressed source,
  `edge()`'s two refusals, `annex_join`'s row-shape validation, `recorded_pairs`, and `main()`'s
  halt-then-derive-then-verify-round-trip-then-gate-then-`silence.write_json` order.
- **estate.py**: `_brief` marker, `inspect()` (stat retry, TRANSIENT_EXT, `.jsonl` per-line parse,
  `.corrupt` exemption, control-character scan), `artifacts()` root discovery and per-directory rollup,
  `charter()`'s table-driven errata and its "could not read tables" bad row, `written()`'s and `external()`'s
  one-row-per-condition emission (no vanishing rows), `terminal()`'s husk test.
- **handbuilt.py**: all nine roster sheets parse and score (ran `compute()`: no exception, no promotion or
  demotion flags, no unscored axes); Zalama's interval 0.19 vs 0.15 for the rest matches the comment at
  165-170; write-before-print ordering; the `score_str` sentinel branch; `_assert_not_halted`.
- **suppressions.py**: `_valid_ttl`, `_preview` marker, `_land`'s CAS + temp cleanup, `_mutate`'s
  re-apply-on-lost-race and denial-versus-race distinction, `add`/`remove` fail-closed refusals, the
  case-sensitive `fnmatchcase` matching, `_repo_listing`, `problems()` expired/dangling reporting.
- **cosmography.py**: `kardashev_to_magnitude`'s `reached = None` initialiser and ascending scan, `census`
  chain arithmetic, `validate`'s two ceiling classes and `SIZE_CLASSES` derived from `GALAXIES_DEFAULT` /
  `STARS_PER_GALAXY_MEAN` (POCKET is 1e-8 galaxies, MINOR exactly 1, both within `SIZE_CLASS_MAX_GALAXIES`),
  `KARDASHEV_MIX` sums to 1.0 within the 1e-6 test, `kardashev_K(2e13) = 0.730`.
- **tuning.py**: `regime()`'s AND of answering buckets and measured success, `_CACHE["buckets"]` shared with
  `profile()`, `workers()` treating 0 as a request, `_answering_buckets` verdict counting (POOL_PROOF has 9
  answering rows over 9 distinct buckets today).
- **lognames.py**: constants, `OWNER` fragments and `PRODUCT` paths all consistent and all present on disk;
  `mutate.sandbox()`'s derivation of its log list from this module picks up exactly the six `.log` strings.

## Coverage recorded

`sweep_plan.record('run67', ['mutate.py', 'threads.py', 'estate.py', 'handbuilt.py', 'suppressions.py',
'cosmography.py', 'tuning.py', 'lognames.py'], batch=4)` run from the kit directory via miniconda python after
this file was written; all eight modules were read in full first.
