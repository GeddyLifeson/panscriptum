# sweep66 batch15 audit (maintenance run #66, 2026-09-27)

## Scope (every line read, start to finish, via the Read tool, no sampling)

- `src/read.py`         1720 lines — read in 4 chunks (1-450, 451-900, 901-1350, 1351-1720)
- `src/escalation.py`   1445 lines — read in 4 chunks (1-400, 401-800, 801-1200, 1201-1445)
  [SAFETY-CRITICAL]
- `src/corpus_db.py`    1053 lines — read in 3 chunks (1-400, 401-800, 801-1053)
- `src/ingest_doc.py`    702 lines — read in 2 chunks (1-350, 351-702)
- `src/prose_gate.py`    545 lines — read in 2 chunks (1-300, 301-545) [SAFETY-CRITICAL]
- `src/burgs.py`         442 lines — read whole
- `src/grounding.py`     361 lines — read whole
- `src/resonance.py`     298 lines — read whole

Total 6,566 lines across eight modules, all read completely, start to finish. READ-ONLY
throughout: nothing under `src/`, `data/`, `state/`, `output/`, `prompts/`, `reference/` or the
repo root was edited, created or deleted, and no subagents were spawned. No network access, no
daemons started. Nothing was executed except `json.load` reads of `state/workorders.json` /
`state/HALT.json` (read-only) and the mandated `sweep_plan.record()` call at the end.

## Prior-audit cross-check

This exact eight-module set is (module-for-module) sweep65's own batch15, minus `tempus.py`
(which sweep65 swapped in for `resonance.py` that cycle) plus `resonance.py` back in. Both
`handoff/sweep65/AUDIT_batch15.md` and `handoff/sweep65/AUDIT_batch12.md` (which covered
`resonance.py` under a different grouping the same day) were read in full before touching source.

- sweep65 batch15 found **0 CONFIRMED / 0 SUSPECTED** defects in `read.py`, `escalation.py`,
  `corpus_db.py`, `ingest_doc.py`, `prose_gate.py`, `burgs.py`, `grounding.py`, beyond two things
  already fixed by earlier sweeps (`read.py`'s `_names()` curly/ASCII-apostrophe fold, and a
  `pipeline.py` meta-language over-match outside this batch). Both were re-verified against the
  live source this cycle: the `_QMAP`-folded fallback pattern is still present and unchanged at
  `read.py:280-291`, and the fold logic still folds both the character-class construction
  (`t.translate(_QMAP)`) and the sentence being tested (`low.translate(_QMAP)`) — confirmed by
  re-reading the block rather than re-running the fuzz check sweep65 already ran.
- sweep65 batch12 found `resonance.py` clean — `hodge_decompose`'s Gauss-Seidel convergence
  fix and the no-evidence-vs-eta-1.0 distinction, `dominates`/`incomparability_rate`'s
  unmeasured/tied/incomparable split — and re-noted the module's own well-documented
  zero-production-caller status. Re-read in full this cycle: unchanged, still sound, still
  uncalled (see Questions).
- sweep64's cross-check (cited by sweep65) also noted `escalation.py:1274`'s `landed = False`
  as a genuine but harmless dead store (the loop body reassigns `landed` from `_land_clear()` at
  the top of every iteration before it is next read, so the assignment at line 1274 cannot
  affect behaviour). Re-traced this cycle against the current source: the line is unchanged, the
  loop shape is unchanged (`for _attempt in range(STOP_CAS_ATTEMPTS): expected = ...; halted,
  rec = status(); ...; landed, why = _land_clear(rec, expected); if landed and
  _halt_file_cleared(): ...; return True; landed = False`), and the dead-store reading still
  holds. Not filed as a new order — it was never filed as one, only carried as a cross-sweep
  observation, and it changes no behaviour.

`state/workorders.json` was searched for all eight module names before writing anything (see
"Method" below for what was found and why none of it is re-filed). `state/HALT.json` was also
read for context: the library is not currently halted (`"cleared": true`, cleared by
maintenance run #63 under owner ruling on order `f25d3d5be9b1`); this has no bearing on any
finding below, it is recorded only because `escalation.py` and `prose_gate.py` are both
safety-critical modules in this batch and their current runtime state is relevant context for a
reader of this audit.

## Method (what state/workorders.json already holds against these eight modules)

Every hit is a pre-existing OWNER-level item, still open, none re-filed here:

- `1e6f99e54b25` / `21c075e5e2d6` (OWNER, MINOR) — the class-wide question of whether
  manually-invoked writers should refuse under a library HALT. `ingest_doc.py` is cited in
  `1e6f99e54b25` as already correctly wired (`_assert_not_halted` gates both `register()` and
  `mine()`, re-asked every chunk inside `mine()`'s loop — confirmed present and unchanged at
  `ingest_doc.py:40-76, 191, 319, 466`). `burgs.py` is cited in `21c075e5e2d6` as one of the
  writers of a "documented-regenerable, unread-downstream" artifact (`data/BURGS_SAMPLE.json`)
  that does NOT currently ask the halt — confirmed still true (`burgs.py`'s `main()` has no
  `escalation` import or `assert_clear` call). This is the class-wide ruling both orders are
  waiting on, not a new instance; not re-filed.
- `39a0542b03f3` (OWNER, MAJOR) — `prose_gate.py`'s `unearned_instrument()` trailing-parenthetical
  base-name fallback (`base = re.sub(r"\s*\(.*", "", name).strip()` at `prose_gate.py:542`).
  Confirmed present and unchanged; still an open question about whether the fallback should
  require the exact catalogued name given continuity-critical variants like "Wally West (New
  Earth)" vs. "Wally West (Prime Earth)". Not re-filed.
- `d03706b5eaf0` (OWNER, part of a two-item bundle) — `prose_gate.py`'s `instrument_shortfall()`
  bare-marker question: should a Place/Faction/Thing entry that carries only the "▣"/"Instrument"
  marker with no "Not applicable" sentence count as present? Confirmed the code is unchanged
  (`prose_gate.py:483-496`) and the question stands exactly as filed. Not re-filed.
- `670c907af5e3` (OWNER, BLOCKING) — the prose subsystem stop (`generate.py` dropping the
  Threads/Contradictions/Instrument tail on multi-entry blocks). Named against `generate.py` and
  `prompts/system_style.txt`, neither of which is in this batch; mentioned here only because
  `state/escalations/prose.log` exists and `escalation.resume_subsystem` is the sanctioned lift
  path this order's own resume line names. Nothing in this batch's eight files bears on it
  directly; not re-litigated.

No other order in the queue names a function or line inside this batch's eight files.

## Findings

**0 CONFIRMED. 0 SUSPECTED (new).**

Every non-obvious branch in all eight files carries its own paragraph naming the specific defect
it was written to close, usually with an order ID and a live measurement proving the fix. Each
such claim was hand-traced against the live source rather than trusted from the comment.
Load-bearing logic re-verified this cycle:

- **`read.py`**: the transport ladder (two quick pool attempts, then the local GPU, then the
  5-attempt cloud backoff ladder, cascade-mode's hard refusal to fall through to the GPU); the
  adaptive gate's thread-local re-entrancy guard (`_card_gate`) and its double-checked-locking
  regime recheck (`_gate()`/`_GATE_LOCK`) — confirmed the lock is genuinely held across the
  `tuning.regime()` call, so the comment describing what would happen WITHOUT the lock is a
  justification for the lock's existence, not a description of a live race; `_local_carded`'s
  oversized-prompt re-split and per-piece 360s timeout, matching the ordinary-chunk path;
  `_chunk_key`'s entity-in-key fix and the per-writer temp-name fix in `_chunk_put`; `_names()`'s
  full fallback chain (token-start match, empty-`parts` phrase-bound fallback with `_QMAP`-folded
  punctuation gaps, final pronoun check) traced by hand against the documented MetalGarurumon/
  Planet/Ash/Ram-Z'Gok cases; `priority()`'s three-bucket split (have_page/no_page/thin) and the
  deep/light interleave loop, confirmed it terminates and drains both lists on every iteration
  count parity; `queue()`'s fail-closed empty/unreadable host-map refusal with retry; `run()`'s
  chunk-based ETA, `--limit`'s honest PARTIAL banner, and the propagated exit code
  (`done["errored"] == 0`).
- **`escalation.py`**: the full rung ladder (JANITOR through OWNER) and `_FIELDS` whitelist;
  `escalate()`'s level-coercion (string name, non-integral float, out-of-range int all fail
  closed to MANAGER rather than OWNER, with the bad value preserved in evidence) and the
  `halt_landed`/`recorded` verdict propagation; `_halt_lock()`'s deliberate fail-OPEN staleness-
  steal design (contrasted correctly against every other layer's fail-closed default, per the
  module's own stated design); `_raise_halt`/`_land_halt`'s compare-and-swap plus read-back
  verification (`_halt_file_records`) rather than trusting `landed` alone; `_read_halt_raw`'s
  three-way None/dict/unreadable-stand-in return, confirmed `null` and non-dict JSON both map to
  the fail-closed stand-in rather than "no halt"; `stop_subsystem`/`resume_subsystem_verdict`'s
  matching CAS-retry-plus-readback discipline, the false-order cleanup on an unlanded stop
  (`resolve_code` only fires after a positive re-check via `subsystem_stopped`, never
  unconditionally), and the `_a_probe_release` exemption's two independently-sufficient
  conditions (redirected ledger, or exact membership in the borrowed `health.SELFTEST_RESUME_
  SUBJECTS` set — confirmed by-equality, not the wider `is_selftest` regex sweep65 also verified);
  `clear()`'s ruling-then-caller refusal ordering, the `_halt_identity`-based raced-halt detection
  that refuses to silently re-merge a lift onto a halt record that grew a new fault mid-write, and
  the dead `landed = False` store noted above.
- **`corpus_db.py`**: `rebuild()`'s three-way sentinel handling (`SPINE_LOOKUP_FAILED`/
  `HOST_LOOKUP_FAILED`/genuine NULL) and its per-file named-not-silently-dropped unreadable-record
  and unreadable-evidence lists; the pid+thread-unique tmp name preventing concurrent-rebuild
  self-destruction; `freshness()`'s MTIME-plus-`record_files`-deletion-check double coverage
  (confirmed a deleted record is correctly distinguished from an edited one, and an index built
  before the deletion check exists reports `"unavailable"` rather than a false all-clear);
  `_freshness_banner()`'s layered caveats (evidence-not-scanned, lookup-file-unreadable,
  predates-the-check, stale-with-deletions-is-an-overcount) all confirmed to print in the stated
  priority and never silently suppress one another; `_cell()`'s ellipsis marker on a truncated
  display value; the CANNED query set's uncapped listings and the `worst_cited`/`below_floor_
  cited` NULL-sorts-first-on-ASC split at the `entries>=40` boundary.
- **`ingest_doc.py`**: `_assert_not_halted`'s narrow write-path-only gating, re-asked every chunk
  inside `mine()`'s loop; `record_path()`'s three-way exact/bounded-containment/ambiguous-refusal
  resolution with `_slug_words_contain`'s hyphen-boundary padding; `mine()`'s resume-cursor
  absent-vs-unreadable-vs-wrong-shape three-way handling (a torn or hand-damaged cursor refuses
  rather than silently restarting from chunk 0); the oversized-page re-split mirroring
  `read.py:_local_carded`, confirmed splitting only adds chunk boundaries and cannot move an
  existing chunk's start forward; the advance-on-the-write-not-the-intent discipline in both the
  record-catalogue write (rewinding `known` on a denied write, without advancing the cursor) and
  the resume-cursor write itself; `main()`'s propagated `mine()` verdict (True only when every
  chunk was processed) rather than a blanket `return 0`.
- **`prose_gate.py`**: the four/five-layer independence (config-read gate, tool-level refusal,
  evidence-floor-with-its-own-floor-on-the-floor, block validator, Instrument-section validator);
  `floor_ok()`'s refusal of a floor at or below zero (closing the exact `floor=0`-admits-everything
  hole its own docstring describes); `section_shortfall()`'s ghost-entry and extra-entry
  denominator inflation (traced by hand: an over-length block cannot reach `frac == 1.0` because
  each unrequested block is charged into `required` on top of being scored in `present`, exactly
  as the 2026-08-28 fix describes); `assert_block_complete`'s undeclared-truncation-safe "N more"
  disclosure; `instrument_shortfall()`'s being/non-being/marked/scored/excused five-way branching,
  traced against all four `(marked, scored-or-excused, being)` combinations by hand; `unearned_
  instrument()`'s decoration-stripping name match (the sweep61 fix tolerating `### Name`/`_Name_`
  headers) and its still-open trailing-parenthetical fallback (see Method above).
- **`burgs.py`**: `burg_count`/`largest_city`'s derivation of settlement count directly from the
  rank-size rule rather than a second free parameter; `rank_population`'s single shared expression
  across all three consumers; `_rank_at_or_above`'s closed-form-then-corrected-against-
  `rank_population` boundary handling (re-traced by hand at the `HAMLET_FLOOR` edge and at a
  fractional-rank boundary — the two correction `while` loops move at most one or two steps and
  terminate); `class_histogram`'s monotone-contiguous-block counting without materialising a
  roster; `burgs_for`'s `--limit`-may-only-narrow fix (`min(int(limit), n)` plus `max(0, ...)`,
  confirmed `limit=0` now yields zero rows rather than falling through to the whole roll); `main()`'s
  parameters-not-rosters accumulation and the designation-collision list-keyed dict (confirmed a
  duplicate designation is no longer silently overwritten).
- **`grounding.py`**: `classify_text`'s uncapped full-field ranking (no `top=3` truncation feeding
  the confidence denominator); `classify_source`'s `cap` parameter hard-refusal (`SystemExit` on
  any non-`None` value, matching `feats.discover`/`genre.classify_source`'s house convention);
  the origin-entry filter's stated synthesis-blob exemption and its named consequence (a
  zero-origin-entry source can still classify off its synthesis blob alone); `main()`'s uncapped
  contested-cosmogony list, sorted by actual contest rather than dict order, with uncut names and
  uncut runners-up.
- **`resonance.py`**: `hodge_decompose`'s Gauss-Seidel sweep (re-traced the STAR/BIPARTITE/PATH4
  convergence claims against the documented before/after measurements — the in-place update
  order is what makes it Gauss-Seidel rather than the Jacobi sweep that never converges on a
  bipartite component); the `_isolated` self-check that can never fire under the current
  construction (kept deliberately as a real guard against a future construction change, not a
  guard that has ever refused anything — read and agree with sweep65's characterisation); the
  no-evidence-vs-eta-1.0 distinction on both the empty-`nodes` and `total==0` paths;
  `dominates`/`incomparability_rate`'s unmeasured/tied/incomparable three-way split, and the
  uncapped `examples` list (Hard Rule 0: every incomparable pair is returned, not the first five).

## Questions (possible deliberate design, not filed as new — already on record or self-documented)

None new. Three items touching this batch were re-examined against the current source and are
unchanged from how prior sweeps and the modules' own docstrings already frame them:

1. `prose_gate.py`'s `unearned_instrument()` trailing-parenthetical fallback (order `39a0542b03f3`)
   and `instrument_shortfall()`'s bare-marker question (order `d03706b5eaf0`) — both open at
   OWNER, both re-verified against the current code, neither re-filed.
2. `burgs.py`'s write of `data/BURGS_SAMPLE.json` with no halt check (order `21c075e5e2d6`,
   grouped with `ingest_doc.py`'s already-correctly-wired case under `1e6f99e54b25`) — the
   class-wide "which writers must refuse under a halt" ruling is still pending; not re-filed.
3. `resonance.py`'s continuing zero-production-caller status for `hodge_decompose`/
   `resonance_strength`, and `incomparability_rate`/`dominates` being exercised only by
   `verify_math`'s own unit tests. The module's own docstring names this at length (including the
   consequence that `custodes.convene()`'s Threnody curl-veto never actually fires because nothing
   supplies it an eta) and states wiring it is an `anchors.py`-side change outside this module's
   scope. No corresponding entry was found in `state/workorders.json` under `hodge_decompose` or
   `resonance.py` — this is consistent with sweep65 batch12's same finding (examined, not filed,
   because the module's own docstring already carries the full analysis and the remedy is
   explicitly named as belonging to a different file). Not filed as new here either, for the same
   reason.

## Coverage recorded

Recorded via `sweep_plan.record('run66', ['read.py', 'escalation.py', 'corpus_db.py',
'ingest_doc.py', 'prose_gate.py', 'burgs.py', 'grounding.py', 'resonance.py'], batch=15)`.
