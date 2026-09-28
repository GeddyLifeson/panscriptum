# sweep66 batch12 audit

Auditor for batch 12 of sweep66 (maintenance run #66, 2026-09-27). READ-ONLY throughout: nothing
under `src/`, `data/`, `state/`, `output/`, `prompts/`, `reference/` or the repo root was edited,
created or deleted this session, other than this report and the single permitted
`sweep_plan.record(...)` call at the end. No subagent was spawned. No pipeline, generate, publish,
crawl, overwatch, foreman, mutate, drill or verify_math invocation was run, and no
halt/`prose_enabled`/`step4_enabled` was touched.

## Scope, read in full, start to finish, sequentially, no sampling

| module | lines | chunks |
|---|---:|---|
| src/magnitude.py | 1989 | 1-1000, 1000-1500, 1500-1989 |
| src/generate.py | 1305 | 1-700, 700-1305 |
| src/onomast.py | 844 | one read |
| src/custodes.py | 714 | one read |
| src/policy.py | 611 | one read |
| src/axis_correlation.py | 443 | one read |
| src/descending_ladder.py | 362 | one read |
| src/tells.py | 303 | one read |

Total 6,571 lines, matching `wc -l` over the eight files exactly. Every line of every module was
read; nothing was grep-only skimmed.

## Prior-audit cross-check

This exact eight-file grouping was audited in `handoff/sweep65/AUDIT_batch12.md` (2026-09-26,
same pairing except `resonance.py` in place of `tells.py`), which reported 0 findings after
re-deriving the sweep64 verdict independently. `tells.py` was separately covered in
`handoff/sweep65/AUDIT_batch07.md` (also 0 findings, one low-confidence question about
`_anchor()`'s `pat[4:]` slice).

Each prior report's specific claims were re-checked against the CURRENT source rather than taken
on their word:

- **magnitude.py**: guards 1-5 (`_resolve_citation`, `AXIS_RE`, `subject_refusal`, `saturated`,
  `quantity_scores`) re-traced against the current code. Confirmed `saturated()`'s six-axis floor
  is still applied only to `_is_score`-filtered values (bool excluded via `_is_score`'s explicit
  `not isinstance(x, bool)`); confirmed guard 3 (`subject_refusal`) is still invoked on both the
  one-shot (`verify`) and split (`_split_gate`) paths, and on the instrument path
  (`quantity_scores`), closing the three historical holes named in the module's own order
  history (66696f8ee28f, e22f29b8e4df, 41e8ffc2e490). Confirmed the saturation check in
  `assay_entity` still runs AFTER the instrument overwrite, so a quantity reading can still push
  a sheet into saturation and be correctly caught.
- **generate.py**: `strip_think`, `_covered`, `_deed_traced`/`_deed_shortfall`,
  `complete_fixed_tail`, `block_problems`, `generate_job`'s corrective retry, the
  `_land_catalog`/`_land_failures` CAS merges, `save_raw`'s atomic replace, and `main()`'s
  evidence-floor / manifest / meta-ban-import-failure fail-closed paths were each re-read end to
  end. All still do what their comments claim. `complete_fixed_tail`'s Threads-reinsertion
  (`list(_THREADS_FIELD.finditer(body))[-1]`, picking the LAST match) was re-checked: still only
  matters if an entry body contains the `Threads:` pattern more than once, which remains an
  unreached edge case per sweep65's own grep, not a live defect.
- **onomast.py**: `is_carried`, `well_formed`'s seven constraints, `coin_well_formed_stamped`'s
  ordinary/exhausted/digest-tail fallback ladder, `name_worlds`'s append-only carry-forward and
  standing-vs-retired split (order e5001f0b0153), `land_onomasticon`'s CAS retry — all re-traced,
  all sound.
- **custodes.py**: `_custos_reading`'s private per-call weight table (never mutates the shared
  `A.WEIGHTS` global), `convene()`'s abstention wiring for Lumen/Threnody (order f467f662be4b
  still open by design — nothing in production computes `eta`), `_transit_widening`'s
  dispersive-vs-unmechanised split, `half`'s cover-every-reading floor, `table_faults()` — all
  re-verified against current source.
- **policy.py**: `OPS`/`TYPES`/`ARG_REQUIRED` remain closed sets refused at load
  (`check_rule` raises `BadRule` before the value-side `except Exception` can misfile a malformed
  rule as a document failure), `evaluate()`'s vacuous-pass detector and its `absent`-op exemption,
  `main()`'s uncapped default corpus sweep and the two-tier (1/2) exit code — all re-verified.
- **axis_correlation.py**: `_scores_of`'s bool-exclusion on both stored shapes, `observations()`'s
  read/missing accounting, `widening()`'s single-`_no_matrix`-call-per-run fix (sentinel `doc`
  built once rather than `rho()` re-calling `load()` 55 times) — all re-verified.
- **descending_ladder.py**: `rung_for_length`'s domain guards at both ends (metres<=0 and
  metres>DESCENDING[0][3] both refuse with `(None, None)`, sub-Planck routes to the Fold), the
  U-shaped binding column documented as deliberate, `shrink_report`'s and `transgression_bits`'s
  non-positive-input refusals — re-verified; module remains HELD/unwired by design (order
  `66f96febdb3a`), no caller anywhere in `src/`.
- **tells.py**: `prompt_in_sync()`'s CRLF-folded comparison, the `_BAD_CHARS`/control-character
  self-check applied to both compiled patterns and the lexical word list, `_anchor()`'s splice
  point re-checked against every current `STRUCTURAL`/`DISCOURSE` entry starting `^\s*` — still
  safe for the current pattern set (see Questions).

`state/workorders.json` (55 entries) was searched for all eight module names before writing
anything. Hits, all already OWNER-routed and none re-filed:

- `1e6f99e54b25` / `21c075e5e2d6` / `3099138a82bd` — the standing "hand-run tools without a halt
  interlock" question, naming `generate.py`, `axis_correlation.py` among many other writers.
- `28f335ecefd3` — SWEEP61_QUESTION_BUNDLE, includes a `generate.py:_covered()` question about an
  empty/missing `name` always counting as covered (item 2). Re-checked against current
  `_covered()`: still true, still just a question (no unnamed entry has ever reached it).
- `34ec8a90c42f` — includes item 1, `axis_correlation.write()` has no floor guard against a
  rebuild that reads fewer sources than the standing file. Re-verified still true of the current
  `write()`/`measure()`; DESIGN/RULING per the order, not re-filed.
- `5bb12b398783` — SWEEP54_QUESTIONS, item 1 concerns `overnight.py` (not in this batch); listed
  because it also touches `custodes.py`'s neighbourhood in the same bundle — no new content for
  this batch.
- `670c907af5e3` — PROSE_TEMPLATE_TAIL_DROPPED, BLOCKING, the order that produced
  `complete_fixed_tail` and the one corrective retry now in `generate_job` (2026-09-25). Still
  open awaiting the owner's read of whether option (a) alone resolved the incident; nothing in
  this read changes that status.
- `8454be695dc7` — NO_FIRST_CLASS_PAUSE_STATE, mentions `generate.py` in passing (killing it
  between catalog saves). Not new to this batch.
- `a66423722e45` — AGENT_SCRATCH_IN_PUBLISHED_TREE, mentions `policy.py` only as one file among
  many `publish.COPY_DIRS` already refuses. Not relevant to a `policy.py` code defect.
- `beb7db270826` — SWEEP_QUESTIONS from sweep65, item 1 is about
  `pipeline.write_record_catalogue`'s merge bound; `tells.py` is not actually its subject (the
  name match is incidental to the order's text). No content for this batch.
- `d2f103634cf1` — SWEEP64_QUESTIONS, item 1 concerns `pipeline._META_TERMS` used from
  `generate.py`'s meta-ban call, not a `generate.py` defect itself. Not re-filed.

None of these is a code defect this batch could newly confirm or contradict, and none names a
symbol in these eight files that this read found freshly broken.

## Findings

**0 CONFIRMED. 0 SUSPECTED.** No new defect was found in any of the eight modules: no wrong
logic, off-by-one, inverted condition, silently swallowed exception where the code claims to fail
closed, guard that cannot fail, race on a shared file, uncapped-then-capped roster, stale comment
lying about current behaviour, or dead branch claimed live.

This is, as every recent sweep of this stretch has also found, one of the most heavily
self-audited parts of the codebase: nearly every non-trivial branch carries an inline paragraph
naming the exact defect it closed, the order id, and often a reproduced before/after measurement.
Reading all eight modules start to finish surfaced no regression in anything sweep64/65 had
verified fixed, and no new instance of any of the priority classes in the brief.

## Questions (design ambiguity, not defects — owner's call, not re-filed as new)

1. **Carried forward, not re-derived.** `tells.py:_anchor()` (line 171-172) assumes any pattern
   beginning with the literal string `"^\s*"` can have exactly that 4-character prefix sliced off
   and replaced with `_SENTENCE_START`. True of every pattern in the file today (verified against
   every current `STRUCTURAL`/`DISCOURSE` entry). If a future entry were added with a
   differently-shaped leading anchor, the slice would silently produce a broken regex rather than
   refusing. Already on record from sweep65 batch07; not re-filed.
2. **Low-confidence, new observation, not filed.** `descending_ladder.py:shrink_report()`
   (line 309): `"is_descent": bool(from_m is not None and to_m < from_m)`. When a caller passes
   `from_m=None` (a legitimate way to say "starting point unknown," since `from_m` has no
   default and is only ever echoed, never validated), the field comes back `False` — the same
   value as a genuine ascent — rather than `None`/"unknown". `mass_conserved_is_lawful` and the
   objections list are unaffected either way (they depend only on `to_m`/`mass_kg`), and the
   module has zero callers anywhere in `src/` (HELD by owner ruling, order `66f96febdb3a`), so
   nothing downstream currently reads `is_descent` at all. Noted here rather than filed because
   it is inert and may be exactly the intended reading ("no known starting point" and "not a
   descent" being treated the same by design is defensible); worth a one-line docstring comment
   if this module is ever wired, not a fix today.

## Cleared (examined closely, found correct)

- `magnitude.py`: the five citation/relevance/subject/saturation/quantity guards; `_split_assay`/
  `_split_gate`/`slice_census` per-axis split-path parity with the one-shot path; `assay_entity`'s
  pool-then-split-then-local-then-defer ladder, epoch mandate, ceiling clamp, and the
  `settled()`/DEFERRED distinction; `calibrate()`'s resume/checkpoint discipline and its use of
  `standards.charter_regression_verdict` rather than a re-derived band-match count.
- `generate.py`: the think-tag stripping boundary; the CAS merge helpers for catalog.json and
  failures.json; `save_raw`'s atomic write; the four-layer prose gate (`prose_gate.assert_gate_
  open`, `evidence_ok`/`floor_ok`, `assert_block_complete`, `assert_instrument_present`,
  `unearned_instrument`); `main()`'s missing-manifest / corrupt-COVERAGE.json / misconfigured-
  floor fail-closed exits; the exit-code plumbing through `sys.exit(main())`.
- `onomast.py`: `coin_well_formed_stamped`'s provably-unique digest-tail last resort;
  `load_onomasticon`'s missing-vs-unreadable distinction; `name_worlds`'s `naming`/`taken`
  seeding and the standing-vs-retired flag split; `land_onomasticon`'s pre-read digest CAS.
- `custodes.py`: the ten-degrees-of-freedom table and `dof_coverage()`; `_custos_reading`'s
  private weight normalisation; `convene()`'s attendance flags settled before the
  `len(readings) < 2` early return; `table_faults()`'s zero-tilt/nonzero-sensitivity check.
- `policy.py`: `resolve()`'s found-vs-null distinction; `check_rule`'s BadRule-before-evaluation
  ordering for `is_type` and the other arg-taking ops; `evaluate()`'s `absent`-op exemption from
  the vacuous-pass report; `report()`'s CAS-gated write and `main()`'s three-tier exit code.
- `axis_correlation.py`: `_scores_of`'s two-shape bool-safe extraction; `observations()`'s
  absent/unreadable-both-ledgered sources accounting; `rho()`/`widening()`'s documented fallback
  (order c00cab9d0412, unchanged by this pass) and the single-lookup sentinel-doc fix.
- `descending_ladder.py`: `rung_for_length`'s finest-rung-still-covering walk (re-hand-traced at
  metres=5e3, correctly settles on Civic); `transgression_bits`'s refuse-don't-price-at-zero
  guard for non-physical inputs.
- `tells.py`: `scan()`'s counted (not boolean) hits; `prompt_in_sync()`'s CRLF fold; the
  control-character self-check over both `_COMPILED` and `_LEX`.

## Coverage

Recorded via `sweep_plan.record('run66', ['magnitude.py', 'generate.py', 'onomast.py',
'custodes.py', 'policy.py', 'axis_correlation.py', 'descending_ladder.py', 'tells.py'],
batch=12)` — see the one scratch `.py` file used for that call, written under `%TEMP%` and
removed after running.
