# Sweep 58 — Batch 12 Audit

Modules read in full, top to bottom (line counts via `wc -l`):

| module | lines |
|---|---|
| src/magnitude.py | 1989 |
| src/sweep_plan.py | 1150 |
| src/chain.py | 988 |
| src/manifest_builder.py | 670 |
| src/zfighters.py | 536 |
| src/genre.py | 381 |
| src/catalogue_models.py | 364 |
| src/physics.py | 312 |

Open queue checked first via `workorders.open_orders()` (script in scratchpad `sweep58/check_orders.py`, full text dumped to `sweep58/orders_full.txt`). Six open orders touch this batch's modules; all six are addressed below as KNOWN.

---

## src/sweep_plan.py (1150 lines)

**KNOWN bf316bbb7f89 / 762fadb8c4c9** — `SWEEP_PLAN_FREEZE_PLAN_HAS_NO_COMPARE_AND_SWAP` / `SWEEP_PLAN_FREEZE_HAS_NO_CAS_ON_CREATE`. **No longer accurate — fixed this shift, verified sound.** `freeze_plan()` (:258-348) now lands the newly-computed plan through `silence.replace_if_unchanged(tmp, path, None)` (:325), which I traced into `silence.py`: `expected_digest=None` specifically asserts "the file did not exist when read" (`silence.py:639`, confirmed by `_digest_or_unreadable`'s `FileNotFoundError -> None` branch at `silence.py:607-608`). On a lost race (`ok` is False), the code re-reads via `frozen_plan(run)` and returns the winner's plan rather than the caller's own stale computation (:328-332), and only falls back to `frozen: False` if genuinely nothing landed anywhere (:333-338). This is the correct create-if-absent CAS shape described in both orders' remedies (`silence.replace_if_unchanged` / `runguard._land_claim` shape). No residual defect found in this path.

**Nothing else found.** Also read in full: `_src_py_files`, `modules`, `batches`, `_table_digest`, `known_modules`, `normalise_module`, `record` (per-batch shard write + best-effort aggregate fold), `_read_shards`, `coverage_map`, `covered_by`, `unknown_claims`, `missing`, `roster_of`, `missing_detail`, `_assignment`, `check_briefs`, `main`. All write paths (`record`'s shard write, the aggregate `COVERAGE` fold, `freeze_plan`) go through `replace_retry`/`replace_if_unchanged`/`write_json` with denials noted rather than swallowed; no unmarked truncation, no bare `except: pass` on a load-bearing path, no console-window risk (no subprocess calls in this module).

---

## src/chain.py (988 lines)

**KNOWN 972932ab89b0** — `CHAIN_HARVEST_CLOBBERS_THE_CONTINUITY_CAS_PATCH`. **No longer accurate — fixed this shift, verified sound.** `harvest()` now takes `digest = silence.digest_of(HARVEST_IDX)` (:314) immediately before its own content read, and on `changed`, lands through `_land_harvest(idx, digest, updates, removed)` (:396) rather than a plain `silence.write_json`. `_land_harvest` (:231-299) is the same shape as `workorders._mutate`/`runguard._land_claim`: it retries `silence.replace_if_unchanged(tmp, HARVEST_IDX, digest)`, and on a lost race (target digest changed, not merely denied) re-reads the fresh file and re-applies only `updates`/`removed` — this pass's own changes — on top of it (:274-292), so an entry `refresh_continuity()` patched concurrently is not clobbered. A denied-but-unchanged target (digest still matches) is correctly distinguished from a genuine race and is *not* retried as one (:262-273). Verified the companion function `refresh_continuity()` (:418-501) already used this same pattern before this shift.

**DEFECT MAJOR — `write_result` discards the raw contest graph on both refusal paths, directly contradicting the module's own stated fix (order 0ced896514e7).**
`write_result` (:107-159) builds:
```python
"edges": [[a, b, n] for (a, b), n in edges.items()] if res.get("strengths") is not None else None,
```
`res.get("strengths")` is `None` in *both* of `main()`'s refusal branches: (1) `fit()` returns `{"error": "too few edges to fit"}` whenever `len(wins) < 3` (`fit()`, :856-861) — this dict has no `strengths` key at all; (2) `RG.bradley_terry()` succeeds but Ford's condition fails, so `res["strengths"]` is explicitly `None` (the "NO STRENGTHS RETURNED" branch, :944-961). In both cases `out["edges"]` is written as `null` to `CHAIN.json`, even though the actual extracted/adjudicated contest edges (the `edges` argument, a live `Counter` with real entries) were passed into the very same call.

This is exactly the loss the surrounding `main()` comment (:904-933) says was fixed: *"THE HARVEST IS WRITTEN EVEN WHEN THE FIT REFUSES ... throwing away the edges ... on the one path where the fit refuses ... the edges are kept and the graph is the finding."* `write_result` is now *called* on both refusal paths (that part of the order's fix landed correctly), but the document it produces still nulls out the one field the fix was about. Concretely: a run that harvests exactly 2 real contest sentences between two catalogued entities produces `len(wins) < 3` → `fit()` refuses → `write_result(edges, {"error": "too few edges to fit"}, unmatched)` is called with `edges` holding those 2 real edges → `CHAIN.json` is written with `"edges": null`. A reader of `CHAIN.json` (or `pipeline.phase_chain`, the module's other documented caller of the same `write_result`) sees no edges at all on a refusal, indistinguishable from a harvest that found nothing.

Remedy: make `"edges"` unconditional — `[[a, b, n] for (a, b), n in edges.items()]` — the same way `"components"`, `"unmatched"` and `"unanswered"` are already written regardless of whether the fit succeeded.

**DEFECT MINOR — `OUTCOME` regex still misses present-participle verb forms, the same defect class just fixed for `beat` in this file.**
The 2026-09-09 fix noted in the comment at :55-64 corrected `beat(?:en)?` to `beat(?:s|en|ing)?` specifically because a wiki narrates outcomes in multiple tenses and the miner was silently dropping sentences it didn't inflect for. Several sibling verbs in the same alternation were not given the same treatment: `kill(?:ed|s)?` has no `-ing` form, `overpower(?:ed|s)?` has no `-ing` form, `destroy(?:ed|s)?` has no `-ing` form, and `surrender(?:ed)? to` has no `-s`/`-ing` form. Concretely, a mined sentence like *"Frieza is destroying the planet as Goku watches"* or *"...while overpowering his opponent"* fails to match `OUTCOME` at all and is silently excluded from `harvest()`'s candidate rows — with no note, no count, nothing distinguishing it from a sentence that genuinely records no contest (which `harvest()`'s docstring calls "the common and correct" case). This is the identical shape the `beat` fix was written to close, left open on its neighbours.

Remedy: extend the same inflection set (`-ed|-s|-ing`, plus `-es`/`-ing` for `surrender ... to`) to the remaining alternation members, or state explicitly (as a comment) why only `beat` needed it.

**Nothing else found** in `write_result`, `landed`, `_corpus_root_state`, `_held_root`, `refresh_continuity`, `_partials`, `entity_index`, `_ask`, `extract` (the per-thread `local_unmatched` locking and the model-index-vs-sentence-index fix are both correctly in place), `adjudicate_mutuals` (the unprobed/self-split/half-dated/split branches are mutually exclusive and each is counted once), `fit`, `main`'s three write/landed checks.

---

## src/catalogue_models.py (364 lines)

**KNOWN 5d0fa30e4b09 (item 5)** — `catalogue_models.py:118-127, 187-238 ... a malformed provider response can be misclassified as EMPTY_LIST, and a `models` entry naming an unconfigured provider is invisible to every count `sweep()` produces`. **No longer accurate — fixed this shift, verified.**
- Malformed-reply handling: `ask_provider` (:80-158) now distinguishes "a well-formed empty list" (`empty_at`, EMPTY_LIST) from "the body wasn't a list at all" or "a non-empty list with no `id`/`name` on any row" (both set `last = "MalformedModelList: ..."` and `continue` to the next candidate URL rather than being folded into EMPTY_LIST). If every tried URL fails this way, the provider outcome is `UNREACHABLE` with the malformed-body message as `error` (:153-158) — matches the shift description ("a malformed reply is 'unreachable'"). Traced the full per-URL loop (:110-152); confirmed `empty_at` is only ever set from the genuinely-empty-list branch (:140-141), never from the malformed branch.
- Unconfigured-provider counting: `sweep()` (:194-350) now appends a synthetic `UNCONFIGURED` row for every provider named in `cfg["models"]` but absent from `cfg["providers"]` (:211-214, the `_orphan` loop), and this row is included in `rows` before `counts["unconfigured"]` is computed (:330), so it is no longer invisible to the tally. Verified `live`/`by_name`/`unverified` all correctly treat these orphans as unasked (outcome `UNCONFIGURED`, excluded from `live`).

**Nothing else found.** `wanted()`, the `LAST_WRITE_LANDED` tri-state and its documented failure modes, the `stale`/`unverified`/`counts` bookkeeping, and `main()`'s gated return code were all read and are internally consistent; no cap, no swallowed exception without `silence.note`, no console-window risk.

---

## src/genre.py (381 lines)

**KNOWN f646c1c5f1d0** — `GENRE_DEAD_DISJUNCTS_AFTER_UNCAPPING`. **No longer accurate — fixed, verified, and fixed exactly as the order's remedy suggested.** `classify_source` (:181-264): the `not ranked` disjunct is gone (:230 is bare `if ranked[0][1] == 0`), the dead `or 1` on the confidence denominator is gone (:240 is bare `total = sum(s for _, s in ranked)`), and — rather than dropping the now-invariant `genres_scored` field — the order's alternative remedy was taken: a new `genres_with_signal` field (`sum(1 for _, s in ranked if s > 0)`, :263) was added alongside it, with `genres_scored` kept and explicitly documented (:251-259) as a tripwire against a future re-introduced cap rather than a per-record signal. This is a live, owner-level naming/schema question already correctly flagged as such in-code, not a defect.

**Nothing else found.** `classify_text`'s uncapped `most_common(top)`, the `cap` parameter's hard refusal in `classify_source`, `_project_pipeline`'s diagnostic-not-guard framing, and `main`'s atomic/gated `GENRES.json` write were all read; the two `_cut()` calls in `main()` are marked reversible console-only cuts and `GENRES.json` itself stores full names.

---

## src/manifest_builder.py (670 lines)

**KNOWN c8dc624e4e02** — `FEATS_FOR_SOURCE_UNBOUND_HOST_SILENT`. **No longer accurate — fixed, verified against both sides of the call.** `build_jobs_for_source` (:377-397) now passes a `binding={}` out-param into `feats_index.feats_for_source(source_name, record, binding=_binding)` and prints a WARNING when `_binding.get("kind") == "unbound"` (:380-385), distinguishing a genuinely-unbound source from one that simply has no attested feats. Cross-checked the callee: `feats_index.feats_for_source` (`feats_index.py:325-355`) accepts the `binding` kwarg, stamps it via `source_binding(source_name, host_map)`, and this is the exact contract the order's remedy asked for ("have manifest_builder ask a second question ... before treating `[]` as 'no attested feats'").

**Nothing else found.** `load_record`'s fuzzy-match ranking (equality-exempt, length-floored, closeness-ranked), `pack_feats`'s flush-before-exceeding pagination (never truncates an oversized entity), the `numbering_pool`-vs-`build_pool` separation that keeps a source's address stable independent of `--only`/`--pilot`, and the manifest/report atomic-write-with-verdict pair in `main()` were all read in full and are consistent with their own extensive in-line justifications.

---

## src/magnitude.py (1989 lines)

**Nothing found.** This is the most heavily self-hardened module in the batch (five explicit guards against fabricated Custodial Assay evidence, each with its own fix history in-line). Specifically checked and found correct:
- `_resolve_citation`'s single citation form (numbered vs. split, one-way containment on the split path) and its length/token floor.
- `subject_refusal`'s four branches (passive-with-agent, passive-without-agent, handoff, rival-leads-a-verb) — all read the entity's own name, closing the "doer" hole the order 1dbec361641b comment describes.
- `saturated()`'s six-axis floor is applied consistently (`_is_score` correctly excludes `bool` from the numeric-score test, used at all six sites per its own docstring's claim — spot-checked `verify`, `_split_gate`, `saturated`).
- `quantity_scores` and the main `assay_entity` quantity-overwrite loop both now gate on `subject_refusal` before letting an instrument reading overwrite a model score (order 41e8ffc2e490).
- `candidates()` has no `cap` parameter (order 7eee204672ce confirmed removed from the signature).
- `run_batch.work()`'s `host_ceiling(h)` call sits inside the same `try` as `assay_entity`, so `SCOPE.ProbeUnread` (deliberately re-raised by `host_ceiling`) is caught there as documented, not left to escape a worker thread.
- No unmarked truncation on any persisted field (`sheet`, `rejections`, `unmatched`, citations) — all cut points are console-only and explicitly marked.

One general observation, not filed as a defect: `AXIS_LEXICON` (magnitude.py) uses unanchored prefix matching (`destroy`, `obliterat`, `annihilat`, no trailing `\b`) so it does not share chain.py's verb-inflection gap — confirmed by inspection, no action needed here.

---

## src/zfighters.py (536 lines)

**Nothing found.** Hand-authored data table (`ROSTER`) plus `compute()`/`main()`. The Goku-sheet merge failure path (:436-451) fails safe (prints an explicit `INCOMPLETE ROSTER` banner and marks `_incomplete` rather than silently ranking without him), the `--full` worksheet printer wraps rather than truncates citations, and the final `Z_FIGHTERS.json` write is gated on `silence.write_json`'s return with the denial reported rather than assumed. No caps, no bare excepts without `silence.note`.

---

## src/physics.py (312 lines)

**Nothing found.** Pure-function module (`kinetic`, `joules_for`, `sphere_volume`, `binding_energy`) with unusually thorough non-finite/non-positive/overflow guarding on every input AND every result (each traced to a named order in its own comment). No I/O, no state, no caps, no console-window risk. One asymmetry noted but not filed as a defect: `kinetic()` requires strictly positive mass (`not m > 0.0` refuses 0) while `binding_energy()` accepts mass == 0 (`not m >= 0.0`); both are internally consistent with their own physical meaning (a massless body has no kinetic feat to measure but a well-defined, trivial binding energy of 0), so this reads as deliberate rather than an inconsistency.

---

## Coverage stamp

`sweep_plan.record("run58", [...8 modules above...], batch=12)` called; see final message for confirmation.

## Summary counts

- DEFECT: 2 (1 MAJOR — chain.py `write_result` edges nulled on refusal; 1 MINOR — chain.py `OUTCOME` regex inflection gap)
- QUESTION: 0 new (the `genre.py` `genres_scored` field-naming question is pre-existing and already correctly flagged in-code under KNOWN f646c1c5f1d0, not restated as a new QUESTION)
- KNOWN: 6 open-order references (bf316bbb7f89, 762fadb8c4c9, 972932ab89b0, 5d0fa30e4b09 item 5, f646c1c5f1d0, c8dc624e4e02) — all six now FIXED and verified against current source; none still accurate as filed
