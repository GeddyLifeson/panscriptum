# Sweep 59 -- AUDIT batch 12

Modules read in full: | module | lines | read (top to bottom? mtime) |
| --- | --- | --- |
| src/module_index.py | 192 | yes (mtime 2026-09-07 23:20:37) |
| src/propagation.py | 254 | yes (mtime 2026-09-06 22:33:43) |
| src/grounding.py | 361 | yes (mtime 2026-09-08 16:27:31) |
| src/suppressions.py | 425 | yes (mtime 2026-09-13 23:23:57) |
| src/handbuilt.py | 518 | yes (mtime 2026-09-14 00:07:29, stable through review) |
| src/build_terminal.py | 668 | yes (mtime 2026-09-14 00:14:20) |
| src/allsweep.py | 1025 | yes (mtime 2026-09-14 00:06:07) |
| src/magnitude.py | 1989 | yes (mtime 2026-09-13 23:59:15) |
| src/generate.py | 1172-1173 | yes (mtime moved 22:18:33 -> 22:23:38 during review; anchor lines re-grepped after, all unchanged where cited -- see note under generate.py) |

## src/generate.py
### New findings
None. This file was mid-edit tonight (per brief: "a failures.json merge"). At the version read,
`_land_failures()` (defined `generate.py:234`) already implements the exact remedy order
`ec8b8b35e521` asked for: a compare-and-swap own-rows merge of `failures.json`, mirroring
`_land_catalog`'s existing pattern for `catalog.json`, with a sentinel `_FAILURE_CLEARED` (line
231) so a resolved address is removed rather than round-tripped as a fake row. `main()` calls it
per-failure (e.g. lines 972, 1038, 1059, 1081, 1116) and once unconditionally at the end (line
1133), then reads the landed total back from disk rather than trusting the in-memory dict (lines
1146-1151) -- the same discipline `_land_catalog`/`catalog_landed` already has. I re-grepped the
three anchor points I depended on (`Verifier`-style: `_land_failures` def, the `order ec8b8b35e521`
citations at lines 819/1127, and `main()`/`generate_job` boundaries) after the file's mtime moved
again mid-review (22:18:33 -> 22:23:38, +54 bytes, -1 line) and all were unchanged at those line
numbers; the file's function boundaries (`grep -n "^def "`) are identical before and after. I did
not find a new defect in this module.
### Known (already open orders)
- `ec8b8b35e521` (GENERATE_FAILURES_JSON_LOAD_ONCE_WRITE_WHOLE) -- **appears resolved** at the
  version read tonight. The remedy it asks for (land failures.json through the same own-rows
  merge pattern catalog.json already uses) is now implemented in full via `_land_failures`. Not
  closing it myself since I only read a snapshot mid-edit; flagging for whoever owns the order so
  it isn't left open against code that no longer has the defect.
- `1d45a56ae1d8` (STALE_CITATIONS_SWEEP57...) names `generate.py:166` in its own text (quoted
  again at `generate.py:951-956` as the reason the site now cites the failing function
  symbolically instead of by line) -- the module already carries the fix this order asked for;
  no action needed from this batch.

## src/handbuilt.py
### New findings
None.
### Known (already open orders)
- `1d45a56ae1d8` names `handbuilt.py:455-464,502` citing stale line numbers into silence.py,
  standards.py and catalogue_models.py. At the version read (mtime 00:07:29, unchanged through
  review), those citations are gone -- the surrounding comment (now ~446-464) discusses the same
  history in prose without numbered cross-file citations. Looks resolved for the handbuilt.py half
  of that order; the mutate.py/read.py/verify_math.py/drill.py rows it also names are outside my
  modules.
- `21c075e5e2d6` (MORE_WRITERS_WITHOUT_A_HALT_INTERLOCK_SWEEP58) lists handbuilt.py as writing
  `data/HANDBUILT_ASSAYS.json` with no `escalation.assert_clear()` call, and says it is "NOT
  trivially regenerable." Still accurate: `main()` (lines 440-471) writes `OUT` via
  `silence.write_json` unconditionally, no halt check anywhere in the module. This is an open
  OWNER ruling question per the order, not something a maintenance batch resolves.
### Checked and clean
- `compute()`/`main()` handle Zalama's mixed numeric/`"unestimable"` axis scores correctly
  (`_is_score` gating at the `--full` print, line ~497) -- confirmed no `TypeError` path remains
  for the sentinel-only rows the module's own comments (lines 492-496) say were once a crash site.
- The write-before-print ordering (lines 446-471) correctly avoids the encoding-crash-before-write
  failure the comment there documents.

## src/magnitude.py
### New findings
None found with a concrete reproducing quote after full top-to-bottom reading of all five guards
(verbatim, relevance, subject, saturation, quantity), `_split_assay`/`_split_gate`, `calibrate()`,
`run_batch()` and `main()`. This module is unusually heavily self-audited already (dozens of named
orders each fixing a specific fail-open shape); I could not find a live gap of the same kind.
### Known (already open orders)
- `89503c58409f` roster names `magnitude.py:924` citing `:1172` and `sweep.py:190` (actual
  `magnitude.py:1207`/`sweep.py:199`). At the version read (mtime 2026-09-13 23:59:15) that
  citation text no longer exists in the file (grepped for `sweep.py` and for `1172`/`190`
  fragments, zero hits) -- looks resolved, at least for this one row of that order's roster.
- `34ec8a90c42f` item 8 concerns `suppressions.add`, not this module; not re-filed.
### Checked and clean
- `saturated()`'s six-axis floor (line 936) and its docstring agree with each other and with the
  live code (`len(nums) >= 6 and min(nums) >= 9.0`).
- `_resolve_citation`'s numbered vs. `numbered=False` (split-path) containment direction matches
  its own docstring claim ("one way only" for split, both ways for one-shot) -- verified at lines
  758-763.
- `subject_refusal`'s four cases (passive-with-agent, passive-without, handoff, rival-leads) each
  read the entity's own name via `entity_forms`/`_is_entity`, closing the gap order `1dbec361641b`
  documents was previously open.
- `quantity_scores` now runs guard 3 (`subject_refusal`) before crediting an instrument reading
  (order `41e8ffc2e490`'s fix), confirmed present at lines 506-517.
- `assay_entity`'s DEFERRED-vs-refused distinction (`settled()`, lines 1804-1827) is internally
  consistent with `run_batch`'s three-way tally (scored/refused/deferred).

## src/allsweep.py
### New findings
None.
### Known (already open orders)
- `a724ec57e0d5` (TI_DANGLING_VERDICT...) cites `allsweep.py:181` and `:719-723` for the
  RC_FINDINGS Verifier row and the tail-suppression condition. At the current file those are now
  at line 242 (`Verifier("thread integrity", ["thread_integrity.py"], RC_FINDINGS)`) and line 849
  (`if r.get("failed") or r["crashed"] or r.get("timeout"):`) -- drifted citations, not re-filed
  per the brief (single drifted line numbers are covered by the existing citation-rot orders). The
  substance the order raises is still accurate: an RC_FINDINGS verdict (e.g. a nonzero DANGLING
  count from thread_integrity) sets `failed=False` (confirmed at line 399,
  `failed = bool(crashed or (r.returncode != 0 and rc_means == RC_BROKEN and not refused))`), so
  the tail-print condition at line 849 still suppresses the child's full DANGLING listing for that
  row. This remains an open OWNER ruling per the order's own text, not a new defect.
### Checked and clean
- `verifier_console_lines`'s `earlier`/`lines_total` accounting is internally consistent with
  `run_verifier`'s `tail` construction (full list stored when `failed or crashed`, else last 14).
- The IMPORT tier's halt-refusal handling (`_HALT_REFUSAL in blob`) and VERIFY tier's equivalent
  (`refused = _HALT_REFUSAL in out`) agree in shape and neither counts a refusal as a failure.
- `estate_faults`/`_row_is_fault` fail closed on a row with no `bad` key, per its own docstring.
- The final `bad` count formula (lines 988-997) sums exactly the graded tiers it lists in the
  trailing printed breakdown; no tier is double-counted or omitted from both.

## src/build_terminal.py
### New findings
None.
### Known (already open orders)
- `89503c58409f` roster names `build_terminal.py:647` citing `catalogue_codex.py:315-331` and
  `generate.py:700-706` (actual `catalogue_codex.py:~496-507`; the `generate.py` citation called
  "unrelated code"). Not re-filed (citation-rot class already covered); did not locate that
  specific citation text in the current file (mtime 2026-09-14 00:14:20) to confirm firsthand
  whether it was already repaired or the order's line number has simply drifted past the comment
  it once named -- flagging rather than asserting either way since I did not find the exact text
  to compare against.
### Checked and clean
- `esc()` escaping discipline is applied at every innerHTML sink I traced (`shelfmark`,
  `selectWorld`, `panel`) -- the fixes for orders `3b37494e20db` and `c000fbc3c378` are present and
  match their own code comments.
- `main()`'s `--help` no longer rebuilds the page (argparse added per the documented order); the
  atomic write (`tmp` + `silence.replace_retry`) and denied-write exit code (order `ca499449f966`)
  both behave as documented.
- The uncapped shelved-here roster (`.roster{max-height:190px;overflow-y:auto}`, CSS) and the
  ring-label trimming (`trimmed()`) both match their Hard-Rule-0 justifying comments.

## src/suppressions.py
### New findings
None.
### Known (already open orders)
- `34ec8a90c42f` item 8 (suppressions.add has no upper bound on ttl_days) -- confirmed still
  accurate: `add()`/`DEFAULT_TTL_DAYS` (lines 42, 169-219) apply no bound and no non-finite/
  non-positive check on `ttl_days`. This is an open OWNER design question per the order; not
  re-filed.
### Checked and clean
- `_mutate`'s compare-and-swap retry loop (attempts=8) correctly distinguishes a denial-while-file-
  unchanged (breaks and raises) from a lost race (re-reads and retries).
- `active()` fails closed on an unreadable file (returns `[]`, so a detector applies in full).
- `suppressed()`/`problems()` use `fnmatchcase` (not `fnmatch`) deliberately, matching the
  case-sensitivity argument in both docstrings.
- `_repo_listing()` is built once and lazily (only when a wildcard row exists), matching its
  own performance/correctness comment.

## src/grounding.py
### New findings
None.
### Checked and clean
- `classify_text`'s `top` parameter now defaults to the whole ranked field (Hard Rule 0 fix,
  order `e2b3af23cb8a`) and `classify_source`'s `confidence` denominator is the full field, not a
  top-3 slice.
- `classify_source`'s `cap` parameter is refused with `SystemExit` when non-None, matching the
  sibling `genre.classify_source` pattern.
- The `main()` diagnostic listing (`low`, contested cosmogonies) is uncapped and sorted by
  confidence, matching its own comment; runners-up are printed whole, not `[:6]`.
- `_BAD_CHARS` guard present (this module carries word-boundary regex escapes) and correctly
  placed before the module's own regex compiles.

## src/propagation.py
### New findings
None.
### Checked and clean
- `observed_mark`'s loop direction (counts down from `LADDER_HEIGHT` to 1) and the "rung 1 is the
  last iteration, not the first" correction (order `67a45b2dcaf8`) match the actual `range(17, 0,
  -1)` code -- rung 1 is indeed the final iteration since `ascension_years` is monotonic increasing
  in rung.
- `main()`'s `--from`/`--to` path and the default diameter-survey path both return a verdict via
  exit code (order `d773ad5756ab`) rather than always returning 0.
- Shelf-name printing in the survey loop is unclipped (order `e8f59f0800fd`'s fix present).

## src/module_index.py
### New findings
None.
### Checked and clean
- `_modules()` walks `src/` recursively (`os.walk`, not `glob("*.py")`), so subdirectory modules
  (e.g. `deprecated/catalogue_local.py`) are included -- matches order `f42c55355431`'s fix as
  applied here.
- Stale-group-name and duplicate-group-name checks (lines 106-131, 113-124) both gate the exit
  code (return 1) rather than only printing to stderr.
- The atomic write + `replace_retry` verdict is checked and gates the exit code on a denied
  rename, per the module's own "verdict is CHECKED" comment.
- No `_BAD_CHARS` guard present, correctly -- this module does not import `re`, so it is not a
  member of the `fadd4338a7b0` roster.

QUESTIONS: 0
record(): ok
