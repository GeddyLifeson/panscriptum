# Batch 03 — run36

Modules: pipeline.py, sweep_plan.py, runguard.py, coverage.py, thread_integrity.py, resonance.py
(3,711 lines total). All six read in full, start to end.

## pipeline.py (2,342 lines)

Read in full. This is the orchestrator; also home to the "two-writer contract"
(`write_record` / `write_record_catalogue`) called out in this batch's guidance. Extremely
heavily self-documented with prior incident writeups — most of the obvious defect shapes
(tautological gates, discarded write verdicts, fixed `.tmp` names, silent caps) have already
been found and fixed here across earlier sweeps, and the fixes read as real on inspection
(`_tmp_for` carries pid+thread, `_landed`/`gate_done` gate every phase's done-key on the actual
rename verdict, `phases_never_closed`/`stalled` correctly distinguish "finished" from "stalled
past the end").

**MAJOR — `write_record` (pipeline.py, `write_record` function, "DRIFT IS A DIGEST OF THE ENTRY
NAMES" docstring) merges entry-level drift correctly but never protects non-`entries` top-level
keys, in either of its two paths, unlike its sibling `write_record_catalogue`.**

Anchor text: `for key, val in rec.items():` / `    if key != "entries":` / `        disk[key] =
val` (the drift-branch key merge), and, above it, `merged = rec` (the initial value, never
reassigned when `drift` is falsy).

Two distinct problems in one function:

1. **No-drift fast path merges nothing at all.** `merged = rec` is set before the file is even
   read, and if `drift` comes back `None` (same entry count, same `_entry_digest`), the function
   never touches `merged` again — it writes the stale in-memory `rec` whole. The drift test is
   entries-only, so a concurrent writer that changed a *different* top-level field (e.g.
   `write_record_catalogue`'s `purged_roster`, or a `synthesis` block written by a different
   process) while entry names stayed identical produces `drift = None`, and this function
   silently reverts that field to whatever `rec` held when the pipeline loaded the record —
   potentially hours earlier. The docstring calls this "the common case," which is exactly what
   makes it costly.
2. **The drift-branch merge has no None-guard.** When drift *is* detected, the loop
   `for key, val in rec.items(): if key != "entries": disk[key] = val` copies **every**
   non-entries key from the stale in-memory `rec` onto `disk` unconditionally — including a
   `None` or a stale value. This is the exact class of bug `write_record_catalogue`'s docstring
   describes fixing in the opposite direction (the 2026-08-25 incident where `catalogue()`'s
   `"synthesis": None` nulled 31 of 216 records) — `write_record_catalogue` was fixed with an
   explicit "absent or None in `rec` → keep the disk value" rule; `write_record`'s twin overwrite
   has no equivalent guard.

Both paths violate the function's own docstring, which says the pipeline "only ever changes
per-entry judgment fields and the source-level synthesis block" — the code does not restrict
itself to `synthesis`, it moves *every* key `rec` happens to carry.

This is a live hazard, not a hypothetical: `write_record` is called by `phase_synthesis` and
`phase_entrypass`, both of which hold `rec` in memory for the duration of a multi-hour phase
while `write_record_catalogue`'s callers (`catalogue_web`, `ingest_doc`) are documented
elsewhere in this same file as writing the *same* record files concurrently — the identical
pipeline-vs-catalogue race the two-writer contract exists to police, just entered from the other
side.

Cross-reference: `handoff/sweep36/AUDIT_batch05.md` independently traced the identical unguarded
loop (line-numbered there as 677-678) via `retry_synthesis.do_merge()`, and filed it as
**QUESTION, not new** — but batch05's reasoning is scoped to `do_merge()`, whose own docstring
requires the pipeline to be stopped before it runs. That carve-out does not cover
`phase_synthesis`/`phase_entrypass`'s own calls to `write_record`, which run *during* a live
pipeline pass, concurrently with the catalogue side, by design. Reporting as MAJOR on that basis
— the hazard batch05 traced through one (guarded) caller is unguarded through pipeline.py's own
two main callers.

### Other things checked and found clean

- `_tmp_for`, `_landed`, `land_json`, `gate_done`, `mark_done`, `phases_never_closed`: read in
  full, consistent with their docstrings, correctly gate done-keys on the actual rename verdict.
- `ask_pool_first` / `_pool_answer_usable`: shape check + optional accept predicate is real, not
  a tautology; `_judged_something` in `phase_entrypass` is a genuine "did this answer address any
  of the indices we asked about" check.
- `valid_scale_note` and its supporting regexes (`_ACT`, `_OBJECT`, `_PATIENT`, `_REPUTATION`,
  `_STATBLOCK`): read the conjunction logic end to end; it is a real AND of act-upon-object +
  not-patient + not-bare-reputation, not a disjunction wearing a conjunction's clothes.
  `_SCALE_PATTERNS`/`_SCALE_EVIDENCE` just above it are explicitly marked UNUSED in a comment,
  and grep confirms only their own definitions — correctly left as documented dead code showing
  the rejected approach, not silently wired back in anywhere.
- `main()`'s phase loop: `stalled` tracking correctly keeps the resume pointer at the first
  phase that did not report `True`, while still letting later phases attempt progress from
  disk artifacts — matches the docstring's stated intent, verified by reading the loop body.
- Grepped all `[:N]` slices in the file: the remaining ones are per-line text truncations for
  prompts/logs (description samples fed to the model, log-line field widths), not roster/entry
  truncations — the two prior "this was a cap" fixes documented in-file (`synthesis_blocks`'
  removed 14-entity cap, `refused[:5]` → uncapped) both check out as actually fixed in current
  source, not just described as fixed.
- `_entry_digest`/`stamp_record`/`verify_record_provenance`: internally consistent, no
  tautology (digest changes when names change, count changes when entries change, both are
  checked independently as the docstring claims).

## sweep_plan.py (372 lines)

Read in full — this is the module proving this very sweep's completeness, per the batch
guidance, and the module explicitly warns (in its own comments) that three consecutive prior
runs each found a new bug in it via self-audit.

**Checked the specific claim that per-batch shards avoid the read-modify-write collision: holds.**
`_shard_path(run, batch)` names each shard `<sanitized run.batch>.<pid>.json`. Since real
concurrent writers (sixteen subagents, one `python -c "sweep_plan.record(...)"` process each)
have distinct PIDs, no two concurrent writers can ever target the same shard path — each writes
its own file and there is no read-modify-write on that path at all, only a fresh create. The one
acknowledged residual (same run/batch retried *within one process*) is sequential, not
concurrent, so it is a harmless overwrite of the same data rather than a race. The genuine RMW
that remains — the fold into the aggregate `SWEEP_COVERAGE.json` at the bottom of `record()`,
protected only by a `threading.Lock` that is useless across the separate processes the docstring
itself names — is explicitly disclosed as a "CONVENIENCE VIEW... nothing draws a conclusion from
it that the shards do not support," and `missing()`/`covered_by()` do in fact read shards first
and only *union in* the aggregate as a fallback for pre-shard history, never let it override a
shard. Traced this claim by reading `covered_by()` and `missing()` end to end: verified true —
an unreliable aggregate write cannot make `missing()` report a false gap, since a false negative
there would require the shard itself to be missing, and shards are per-writer and never pruned.

No new finding. `modules()`'s own error-handling (unreadable file → recorded as `unreadable:
True` rather than silently sorting to the bottom as a phantom 0-line file) and `latest_run()`'s
"don't hardcode a run id" fix both check out as real fixes against their described incidents.

## runguard.py (303 lines)

Read in full. Implements the single-instance overlap guard for maintenance runs, rewritten this
run (referenced in its own comments as edited "run35"/"run36, batch 08"). The core invariant —
"a run may only ever refresh or close a record that carries its own name" — is enforced
identically in `beat()` and `release()`, both gate on `rec.get("agent") == agent` before writing.

Digest-before-read ordering in `claim()`/`beat()`/`release()` is correct and consistent: each
takes `silence.digest_of(path)` before `read(path)`, and the comment's stated reasoning (a
digest taken *after* the read could be newer than the content just reasoned about, letting a
stale write through) is sound. `_land_claim` routes all three operations through
`silence.replace_if_unchanged`, a real compare-and-swap against that digest — verified by
reading `silence.replace_if_unchanged` itself (re-checks the destination's live digest against
the expected one immediately before the rename, and returns `(False, reason)` rather than
`(False, "landed")` on a denied rename, which its own comment says was a previously-fixed
bug — reason and verdict do agree in the current source).

**QUESTION, not a finding**: `replace_if_unchanged`'s CAS still has an unavoidable
check-then-act window between reading the destination's digest and the `os.replace` call a few
lines later — true atomic compare-and-swap across processes isn't available from plain
filesystem rename primitives without a separate lock file, which this codebase has deliberately
avoided elsewhere (see batch05's note on `retry_synthesis.py`'s "explicit no-lock-file
rationale"). The window is narrow and this halves-or-better the actual race probability
(`claim()` racing with `claim()`) relative to the plain write it replaced, but it is not a
mathematical impossibility of collision, only a large reduction. Flagging as a question because
it may already be an accepted trade-off rather than an oversight — no evidence either way was
found in-file.

`main()`'s CLI dispatch and `holder_is_live` staleness threshold: read, nothing found.

## coverage.py (272 lines)

Read in full. `state_of()`'s CITED > READ > NO PAGE > NOT ATTEMPTED precedence, and the
`cachekey.owns()` ownership check inside `_state_of_file` guarding against two differently-cased
entity names sharing a cache path: both read correctly against their docstrings' stated
incidents.

**MINOR/QUESTION — `main()`'s `--show-best` defaults to a silent cap of 10 rows on the BEST
COVERED table**, unlike `--show` (WORST COVERED), whose default is `None` (unlimited).

Anchor text: `ap.add_argument("--show-best", type=int, default=10, ...)`, and in `report()`:
`blimit = show_best if show_best is not None else len(best_all)` — so a bare `python
coverage.py` with no flags prints only the best 10 of however many sources qualify, while the
worst-covered table prints all of them by default. The truncation *is* announced inline
("showing 10 of N; N-10 more not shown, --show-best to raise") rather than silent in the sense
of going unmentioned, but it is a default cap on a ranked report table, which the audit
catalogue names explicitly ("any... `top N` that truncates... or report"). Given `--show`'s
default was evidently deliberately set to unlimited for the worst-covered table (the more
operationally important one), this reads like an intentional asymmetry — the "good news" table
gets a convenience default — rather than an oversight, but it is a literal default cap on a
report and is flagged per the letter of Hard Rule 0. Low severity: console-only, does not feed
any downstream data file (`COVERAGE.json` itself, written separately via `silence.write_json`,
is the full uncapped per-source table).

`main()`'s write-verdict handling (`silence.write_json` return value checked, non-zero exit on
denial): correct, not a discarded verdict.

## thread_integrity.py (229 lines)

Read in full, current source (this file is noted as recently edited). The previously-filed
`bdc23fd24dc8` [MAJOR, sweep35-batch10] finding — `[:8]`/`[:8]`/`[:6]` caps on the three ranked
detail lists — is **confirmed fixed** in current source: all three `for` loops over
`sorted(detail[...], ...)` now iterate the full list, with an explicit "UNCAPPED, per Hard Rule
0" comment explaining the fix.

**MINOR/QUESTION — the DANGLING class is computed with full per-pair detail but `main()` never
prints it, unlike its two siblings.**

`classify()` appends full `(a, b, len(gone), len(shared))` tuples to `detail["DANGLING"]` (same
shape as `detail["PARTIALLY-DANGLING"]`, which *is* printed). `main()` prints itemized rows for
`PARTIALLY-DANGLING`, `RECIPROCAL` and `ASYMMETRIC-SUSPECT` only — `DANGLING` (and
`IMPLIED-UNRECORDED`, `ASYMMETRIC-LAWFUL`) get a count line but no rows. DANGLING is defined as
"points at nothing that exists" — by the module's own class ordering this is the most severe of
the four measurable classes (worse than PARTIALLY-DANGLING, which at least still holds live
shared entities), yet it's the one whose detail is silently dropped on the floor rather than
printed. Given `main()` is this module's *only* reporting surface (no JSON output, per the
already-filed finding on the now-fixed caps), a DANGLING pair is currently invisible to anyone
reading the module's output beyond its raw count. Not filing as MAJOR since it's plausibly
intentional (a DANGLING pair means the shared entity vanished from *both* sides via weave drift,
which may be a symptom of the catalogue still settling rather than an editorial gap requiring
review the way ASYMMETRIC-SUSPECT does) — flagging because the asymmetry with its sibling
PARTIALLY-DANGLING (which does get printed) isn't explained anywhere in-file, and the omission
appears new (not covered by the already-fixed `bdc23fd24dc8`).

`load_entities()`'s `WI.norm()` key-space fix and `implied_threads()`'s symmetric-pair
construction (verified: for a shared entity across sources, both `(a,b)` and `(b,a)` get the
same `shared` key set added by construction, so `classify()`'s `seen`-based dedup of the reverse
direction is safe and does not silently drop or double-count a direction): read, correct.

## resonance.py (193 lines)

Read in full. Per the batch guidance, treating the "no production caller" issue as a known
question rather than a new finding — confirmed still accurate and still open: grepped
`hodge_decompose`, `incomparability_rate`, `resonance_strength`, `dominates(` across `src/*.py`;
the only call sites outside this file are three `verify_math.py` unit-test invocations of
`incomparability_rate`. `custodes.convene()`'s `eta` parameter (the Threnody curl-veto) and its
docstring claim ("`eta` (from `resonance.hodge_decompose`) lets Threnody exercise her veto") are
real and functional *as code* — the veto branch (`if eta is not None and (1.0 - eta) >=
CURL_VETO_THRESHOLD`) is live and correctly gated — but `anchors.py:190`, the sole production
caller of `convene()`, never passes `eta`, so the veto can never fire in practice. This exactly
matches the already-filed `f467f662be4b` [MAJOR, sweep35-batch16, still open in
`handoff/queue/RUN.md`]. No new angle found beyond what's already on file.

One additional, minor, and likely-inconsequential-because-dead observation while reading
`incomparability_rate`: `examples` is capped (`if len(examples) < 5: examples.append((a, b))`)
while the `rate`/`inc`/`total` counts it returns alongside are fully accurate and uncapped — a
silent-cap shape in the letter of Hard Rule 0, but scoped to an illustrative sample field inside
a function with zero production callers (see above), so not filing separately; noting for the
record in case the function is ever wired up, since the cap should probably go at the same time.

`hodge_decompose`'s Jacobi-vs-Gauss-Seidel naming fix and its `no_evidence` empty/all-zero
distinction: read the iteration and the two early-return branches, both check out as described.
`resonance_strength()`'s linear scan over `g["pairs"]`: uncapped, correct.

---

## Findings summary (see individual sections above for full text/anchors)

1. MAJOR — `pipeline.py` `write_record`: no-drift fast path skips merging non-`entries`
   top-level keys entirely (writes stale in-memory `rec` whole); drift-branch merge overwrites
   every non-`entries` key from stale `rec` with no None-guard, unlike `write_record_catalogue`'s
   fixed twin. Anchor: `merged = rec` / `for key, val in rec.items(): if key != "entries": disk[key] = val`.
2. MINOR/QUESTION — `coverage.py` `main()`: `--show-best` defaults to a cap of 10 on the BEST
   COVERED report table (announced, adjustable), asymmetric with `--show`'s unlimited default.
3. MINOR/QUESTION — `thread_integrity.py` `main()`: DANGLING class detail computed but never
   printed (count only), unlike its PARTIALLY-DANGLING/RECIPROCAL/ASYMMETRIC-SUSPECT siblings.
4. QUESTION — `runguard.py` `replace_if_unchanged`: CAS has an inherent (narrow) check-then-act
   window between digest check and rename; likely an accepted trade-off, not confirmed either way.
5. QUESTION (already filed, confirmed still open, not new) — `resonance.py`
   `hodge_decompose`/`resonance_strength` and `custodes.convene`'s `eta` veto: zero production
   wiring, matches `f467f662be4b`.

No module in this batch could not be read; all six were read start to end.
