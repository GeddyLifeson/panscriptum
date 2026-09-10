# SWEEP run54 — batch 12 audit

Auditor read every line of all eight assigned modules (magnitude.py 1960 lines, rigor.py 1133,
threads.py 894, build_terminal.py 668, handbuilt.py 517, pantheon.py 433, catalogue_aurora.py 325,
tuning.py 287 — 6,217 lines total).

## src/magnitude.py

Read in full (two passes: lines 1-982, then 983-1960). This module is Charter Part Three's
Custodial Assay pipeline, heavily fortified with historical-defect commentary. Traced the five
named guards (verbatim, relevance, subject, saturation, quantity) through `verify()`,
`_split_gate()`, `subject_refusal()`, `_resolve_citation()`, `quantity_scores()`, and the
transport ladder in `assay_entity()` (pool -> local -> split -> defer). Checked each guard's
current code against its own docstring's claims. Checked `_is_score()`'s bool-exclusion, the
`settled()`/`run_batch()` requeue logic, `host_ceiling()`'s ProbeUnread propagation, and
`calibrate()`'s checkpoint/resume logic. No MAJOR or MINOR findings — the guards described in the
module docstring are actually wired into every path that reaches publication (one-shot, local,
split, split-retry), matching their stated claims. All `except Exception` blocks are paired with
`silence.note(...)`.

### INFO — heavily self-documented history, nothing outstanding found
**Where:** src/magnitude.py (whole file)
**What:** The module's own docstrings and inline comments catalogue a long series of past defects
(the empty-citation bug, the stale-num_ctx fight, the missing subject-check on the split path, the
missing subject-check inside `quantity_scores`, the host-missing-on-two-returns bug, etc.) and each
one traces to a specific `order <hash>` and states the current, corrected behaviour.
**Why it is wrong:** N/A — checked each cited fix against the code that currently stands and found
the fix in place in every case I traced. Filed as INFO rather than silence, per the brief's
instruction that "nothing found" needs an account of what was checked.
**Confidence:** Traced call sites for guards 1-5, `_is_score`, `_status_score`, `settled()`,
`saturated()`, `host_ceiling()`'s exception handling, and the one-shot/local/split/retry branches
in `assay_entity()`.

## src/rigor.py

Read in full (single pass, 1133 lines). Verified the AHP/HodgeRank consistency claims
(`_validate_reciprocal_matrix`, `perron_weights`, `logrank_weights`, `theorem_1_check`), the
two-sided CR/curl-fraction checks (order dc501e776a2b), Ford's condition in `bradley_terry`
(strong-connectivity via Tarjan SCC, the un-chained undefeated/winless checks), the MDL floor
functions, the Jensen-gap `prob_at_least_one`, `ceiling_confidence`/`gumbel_return_level`'s
three-way reason branching, and `main()`'s derived (not hardcoded) faculty-weight and audit-row
reporting. No findings — every "the model used to say X, now derives Y" claim in the file checked
out against the code beneath it (e.g. `_muted` is genuinely computed from `A.FACULTY_WEIGHTS`
rather than asserted; `_AUDIT_ROWS`' declared column is read from `chord_field.ADJUDICATIONS`
rather than copied; the `load_bearing` display cut in `main()` extends through ties and states the
remainder count).

### INFO — clean, checked for stale worked examples and tautological checks
**Where:** src/rigor.py (whole file)
**What:** The file's own header flags several past "one fact, two copies" defects (the muted-
faculty print, the worked example using the wrong bit-length function, the hardcoded "8" weight
count).
**Why it is wrong:** N/A — checked each against the current source; all now read from live tables
(`assay.FACULTY_WEIGHTS`, `assay.CHARTER_PHYSICAL_WEIGHTS`, `len(A.WEIGHTS)`) rather than repeating
a literal.
**Confidence:** Read the full file; traced `measure_bit_value`, `faculty_parity_weights`, and the
`main()` printout logic line by line.

## src/threads.py

Read in full (894 lines). Traced `edge()`'s two refusals, `_resolves()`, `annex_codes()` /
`law_codes()`'s fail-closed short-count checks, `cohort_family()`'s bare-Set inclusion,
`category_path()`'s subroom-then-topic fallback, `threads_for()`'s per-entry T4 derivation and its
refusal-on-missing-source behaviour, and `verify()`'s round-tripped-graph checks.

### MINOR — stale authorization status for T4 baked into a live refusal message
**Where:** src/threads.py:311-337, specifically the string at line 328
**What:** `edge()` raises `ThreadRefused` for any class not in `DERIVABLE`, and the refusal message
reads: `"...T3 (the Chronicle join) was authorised by STEP4_PLAN.md §7G on 2026-09-08; T4 (Law
citations) is Phase 4.4 and remains UNAUTHORISED by §7G's own closing line; T5..."`. But the same
file's own header (lines 27-37) and `DERIVABLE = ("T1", "T2", "T3", "T4")` (line 141) state T4 was
admitted under §7H on 2026-09-09 — i.e., T4 is *not* unauthorised; it is a live, derivable class.
**Why it is wrong:** Since T4 is now in `DERIVABLE`, this specific message can never fire for
`cls="T4"` (calling `edge(..., "T4", ...)` no longer hits this branch), so the immediate risk is
contained — but the string is factually wrong about T4's status and would mislead anyone reading it
(e.g., if it is ever shown for a genuinely-invalid class, or read out of context/logged). It is
exactly the "claim in a comment that the code no longer honours" shape, just living in a runtime
string rather than a docstring.
**Confidence:** Read the whole file including the DERIVABLE tuple and the header's §7H admission
note; confirmed by grep that line 328 is the only place this specific "remains UNAUTHORISED"
sentence appears and that it was not updated when T4 was admitted.

### INFO — remainder of file checked and clean
**Where:** src/threads.py (whole file)
**What:** `verify()`'s docstring documents an earlier state (audit T-3) where every check was a
tautology against the just-built object; the checks are now run against a round-tripped
(serialized/re-parsed) graph in `main()`, which is a live-fireable check.
**Why it is wrong:** N/A — confirmed `main()` calls `verify(json.loads(json.dumps(graph)))`, not
`verify(graph)` directly, matching the fix the docstring claims.
**Confidence:** Read `verify()` and its one call site in `main()`.

## src/build_terminal.py

Read in full (668 lines: Python wrapper + embedded JS template). Checked the `--help`-must-not-
rebuild fix in `main()`, the atomic write via `silence.replace_retry` with proper exit-code
propagation, the `<` -> `<` neutralisation before splicing JSON into the inline `<script>`,
and the `esc()` HTML-escaping discipline claimed for every catalogue-derived string reaching
innerHTML (`shelfmark()`, `panel()`, `selectSource()`, `selectWorld()`). Confirmed `selectWorld()`
now escapes both `cat`-derived strings and the four `f.*` fields (landform/climate/condition/tech)
per the two comments claiming those sinks were fixed (orders 3b37494e20db, c000fbc3c378).

### INFO — nothing found beyond what the file already documents as fixed
**Where:** src/build_terminal.py (whole file)
**What:** N/A.
**Why it is wrong:** N/A — checked `esc()` usage at all string-interpolation sites inside
`selectWorld()`, `selectSource()`, `panel()`, and `shelfmark()`; all catalogue-derived values pass
through `esc()` before reaching a template literal that is assigned to `innerHTML`.
**Confidence:** Read the whole embedded JS and grepped for template-literal interpolations of
`nd.name`, `cat`, `f.landform` etc. to confirm each is wrapped in `esc(...)`.

## src/handbuilt.py

Read in full (517 lines: docstring + 9-entity hand-built roster + `compute()`/`main()`). Checked
the write-before-print ordering fix (to survive `UnicodeEncodeError` on cp1252 consoles), the
`silence.write_json` usage in place of a hand-rolled temp file, the sentinel-score guard in
`main()`'s `--full` printer (`score_str` branches on `isinstance(score, (int, float)) and not
isinstance(score, bool)` before formatting with `%5.1f`, avoiding the `TypeError` the comment
describes for Zalama's `"unestimable"` strings), and the unwrapped-citation fix (`textwrap.wrap`
instead of a `[:58]` slice).

### INFO — static data module, no logic defects found
**Where:** src/handbuilt.py (whole file)
**What:** N/A — this module is mostly a literal roster (`ROSTER` dict) of hand-assayed sheets with
narrative justification; `compute()` and `main()` are thin.
**Why it is wrong:** N/A.
**Confidence:** Read the whole file, including every roster entry's axis citations, and traced
`compute()`'s and `main()`'s handling of both numeric and sentinel-string scores.

## src/pantheon.py

Read in full (433 lines). Checked the gated writes (`write_ok` carried through to both the printed
line and the exit code — order a012b799a6c9), the Z_FIGHTERS.json merge's three failure paths
(unreadable file -> `merge_failed` + non-zero exit; `_incomplete` marker -> counted toward
`merge_failed`; `combined.setdefault` never silently overwriting a hand-built god), and the
`--full` view's uncapped citation printing with defensive `.get("provenance", "?")` for the
documented Son-Goku data gap.

### INFO — nothing found beyond what the file already documents as fixed
**Where:** src/pantheon.py (whole file)
**What:** N/A.
**Why it is wrong:** N/A — confirmed `return 0 if write_ok else 1` and the `merge_failed` check both
precede the final `return`, so neither a denied write nor a partial roster merge can return 0.
**Confidence:** Read `main()` end to end, including both `return` statements and the `--full` loop.

## src/catalogue_aurora.py

Read in full (325 lines). Checked the uncapped `slug()` plus `record_path()`'s legacy-cap fallback
(so old records aren't orphaned nor duplicated), `parse_folder()`'s dedup key now including
`desc` (fixing the earlier same-name-different-content collision), and the gated writes:
per-record `_P.write_record_catalogue(...)` result checked before `written.append(...)` and before
mutating the in-memory roll row, plus the compare-and-swap `roll.update_rows(roll_changes, ...)`
replacing what the docstring calls a previously-unsafe whole-document overwrite. The exit code
(`return 1`) is reachable via `refused` (no roll entry / no elements parsed / write denied) and via
`not roll_landed`.

### INFO — nothing found beyond what the file already documents as fixed
**Where:** src/catalogue_aurora.py (whole file)
**What:** N/A.
**Why it is wrong:** N/A.
**Confidence:** Read `main()` end to end including the roll-changes accumulation, the
compare-and-swap call, and the final refusal aggregation/exit code.

## src/tuning.py

Read in full (287 lines). Checked `_ollama_host()` reading `config.yaml` (rather than a hardcoded
localhost), `_answering_buckets()`'s staleness annotation without silent discount,
`cloud_success_rate()`'s path-from-owning-module fix (`CB.SCRATCH_DB` rather than a second literal
path), the `regime()`/`profile()` cache-consistency fix (workers sized from the SAME `_CACHE`
reading that produced the label, not a second live re-probe), and `workers()`'s `requested is not
None` fix for the zero-means-"run nothing" boundary case (the docstring calls this dormant since no
current caller passes 0; confirmed by grep below).

### INFO — dormant-bug claim spot-checked
**Where:** src/tuning.py:249-267 (`workers()`)
**What:** The docstring states "No caller passes 0 today (chain.py, magnitude.py and read.py all
pass a positive int), so this is dormant rather than live."
**Why it is wrong:** N/A — spot-checked; `magnitude.py`'s `run_batch()` calls
`T.workers(workers)` where `workers` defaults to argparse `default=8`, so it is never 0 unless a
caller explicitly passes `--workers 0`. Did not verify chain.py/read.py (out of batch scope), so
this claim is accepted on the strength of the two call sites actually available to check, not
independently re-verified for all three named modules.
**Confidence:** Read `magnitude.py --workers` argparse default and its one call to
`T.workers(...)`; did not read chain.py or read.py (not in this batch).

## Summary of findings

- 0 MAJOR
- 1 MINOR: src/threads.py:328 — stale "T4 ... remains UNAUTHORISED" text inside `edge()`'s refusal
  message, contradicted by the same file's own admission of T4 under §7H and by `DERIVABLE`
  already including T4. Currently unreachable for `cls="T4"` specifically (since T4 passes the
  `cls not in DERIVABLE` test and never reaches this string), but the string itself is wrong and
  would mislead if ever surfaced for another invalid class or read out of context.
- 7 INFO (one per module, recording what was checked; several modules had no residual defects to
  report beyond confirming previously-documented fixes are actually in place)
