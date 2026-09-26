# sweep64 batch03 audit

Auditor for batch 03 of sweep64 (maintenance run #64, 2026-09-26). Read-only on `src/`, `data/`,
`state/`, `output/` throughout — nothing under those trees was edited. Did not run pipeline.py,
drill.py, verify_math.py, generate.py, publish, mutate, or any job. No subagents were spawned.

## Scope, read in full, start to finish, no sampling

- `src/pipeline.py` — 3,674 lines (read in ~300-500 line chunks, full coverage 1-3674)
- `src/weave_index.py` — 730 lines (one pass)
- `src/feats_index.py` — 633 lines (one pass)
- `src/reference.py` — 497 lines (one pass)
- `src/recover_folder_records.py` — 380 lines (one pass)
- `src/deprecated/catalogue_local.py` — 333 lines (one pass, including the dead code after the
  self-refusal `raise SystemExit`, which is deliberate per the module's own header)
- `src/resonance.py` — 298 lines (one pass)

Total: 6,545 lines across 7 modules, all read.

## Method

CLAUDE.md read first for doctrine (Hard Rule -1 escalation/halt, Hard Rule 0 no caps, fail-closed,
"a check that cannot fail looks exactly like a check that passed"). Grepped `handoff/sweep63/` for
these seven module names and read every prior audit that named one in full before reading source:

- `handoff/sweep63/AUDIT_batch03.md` — covered `pipeline.py` and `weave_index.py`. Filed one
  VERIFIED finding: `phase_entrypass`'s out-of-range `category` answer was silently discarded with
  no rejection marker (`category` had no `category_rejected` companion the way `topic`/`subroom`
  do), and a carried-over open item restating sweep61's `physiology` field finding (requested,
  schema-required, never assigned to `batch[i]`, never merged to disk).
- `handoff/sweep63/AUDIT_batch06.md` — covered `feats_index.py`, `reference.py`,
  `deprecated/catalogue_local.py`, `resonance.py`. Filed one VERIFIED finding:
  `feats_index.feats_for_source()` hardcoded `binding["kind"] = "bound"` on the only branch that
  ever ran for a `doc:`-bound source, instead of naming it `"doc"` as `source_binding()` does for
  the identical source.
- `handoff/sweep63/AUDIT_batch07.md` — covered `recover_folder_records.py`. No findings.

Per the task brief, the specific ask was to give fresh eyes to the 2026-09-24 M120 change in
`pipeline.py` (the out-of-range `category` fix) end to end, and to re-verify or re-derive
everything else rather than assume sweep63's account still holds. Both prior VERIFIED findings
above were re-traced against the CURRENT source (not assumed fixed from the mere existence of a
comment claiming so).

## Findings

### 1. VERIFIED-FIXED — the M120 `category_rejected` change (pipeline.py) is correctly wired end
to end, across both writers. Not a defect; reported because the brief specifically asked for this
to be checked rather than assumed.

Traced the full path:

- **Schema** (`ENTRY_SCHEMA`, pipeline.py:2033-2071): `category` is still a bare
  `{"type": "integer"}`, deliberately unconstrained (see Q1 below) — this is unchanged from
  sweep63's read and is not itself a new defect since the code downstream now handles an
  out-of-range value explicitly.
- **Results loop** (pipeline.py:2359-2371):
  ```python
  ci = res.get("category")
  if isinstance(ci, int) and 1 <= ci <= len(CATEGORIES):
      batch[i]["category"] = CATEGORIES[ci - 1]
      batch[i].pop("category_rejected", None)
  elif ci is not None and ci != "":
      batch[i]["category_rejected"] = _stored_cut(str(ci), 120)
  ```
  A valid `ci` corrects `category` and clears any stale rejection; an invalid one leaves
  `category` untouched (matching `topic`/`subroom`'s established pattern) and records the refused
  value instead of discarding it. `catalogued = True` is still set unconditionally afterward
  (line 2442) — this is consistent with how `topic_rejected`/`subroom_rejected` already work, not
  a new gap.
- **`MERGED_ENTRY_FIELDS`** (pipeline.py:841-849) now includes `"category_rejected"`, cited
  "sweep63 batch03" in its own comment.
- **`ENTRY_REJECTION_COMPANIONS`** (pipeline.py:877-880) now maps `"category": "category_rejected"`.
- **`write_record`'s per-entry fold** (pipeline.py:1438-1446): `category_rejected` is folded via
  the `MERGED_ENTRY_FIELDS` loop when present in the in-memory entry, and the companion-clear loop
  correctly pops a stale `category_rejected` from disk exactly when `category` is present in the
  caller's entry and `category_rejected` is not (i.e. a fresh correction superseded an old
  rejection) — the same guarded shape already used for `topic`/`subroom`.
- **`write_record_catalogue`'s per-entry fold** (pipeline.py:1092-1112): iterates
  `MERGED_ENTRY_FIELDS` including `category_rejected`; since no cast-builder ever writes
  `category_rejected`, the fresh cast's value for that field is always falsy, so the
  `if not sv or sv == "unassayed": se[fld] = dv` branch correctly carries a disk-held rejection
  note forward onto the merged/re-catalogued row regardless of `_entry_was_judged`. `category`
  itself continues to go through the `CATALOGUE_CURATED_FIELDS` path exactly as before the M120
  change (unaffected by it).
- **`_PIPELINE_JUDGMENT_MARKS`** (pipeline.py:926-928) does not list `category_rejected`
  explicitly, but this is not a gap: `category_rejected` is only ever set in the same iteration
  that also sets `catalogued = True` (excluded entries `continue` before reaching either), and
  `catalogued` is already in the marks list, so `_entry_was_judged()` correctly returns `True` for
  any entry carrying a `category_rejected` mark.

No inconsistency, no dropped clear, no asymmetry between the two writers found in this path. This
closes out sweep63-batch03's finding #1 as fixed.

### 2. VERIFIED (carried over, still unfixed) — pipeline.py: the `physiology` field is asked for,
schema-required, and never captured anywhere.

- `ENTRY_SYSTEM` (pipeline.py:1963-1968) instructs the model at length on what `physiology` should
  contain for a Peoples & Species entry.
- `ENTRY_SCHEMA` (pipeline.py:2059, 2065-2066) declares `"physiology": {"type": "string"}` and
  lists it in `"required"`.
- The results-processing loop (pipeline.py:2349-2442), which reads every other field of `res`
  (`category`, `scale_note`, `magnitude`, `topic`, `subroom`), never once reads
  `res.get("physiology")`.
- `MERGED_ENTRY_FIELDS` (pipeline.py:841-849) does not list `"physiology"`, so even a hypothetical
  future in-memory assignment could not reach disk through `write_record`'s fold.

Concrete failure scenario: every entrypass call the model answers correctly and in full — for a
category-8 (Peoples & Species) entry it returns e.g.
`"physiology": "silicon-based; does not eat, breathe or age; killed only by structural shattering"`
exactly as instructed — and this value is discarded on every single call, permanently, because
nothing downstream reads or stores it. The field was added specifically to close the gap named in
its own schema comment ("order 6c7495ee66be... what it is MADE OF"), and that gap is still open:
zero entries in the corpus can carry a physiology value through this path. This is the identical
finding sweep61-batch03 filed in full and sweep63-batch03 re-confirmed as a carried-over open item
(not re-derived there at length, "this one is simply not yet resolved"); re-verified here against
the current source (2026-09-26) by the same method (reading the schema, the prompt, the full
results loop, and `MERGED_ENTRY_FIELDS`) and it remains unfixed. Flagging again because the task
explicitly asks for VERIFIED findings still present, not only new ones.

### 3. VERIFIED-FIXED — feats_index.py: `feats_for_source()`'s `doc:`-binding mislabel (sweep63
batch06 finding #1) has been fixed.

```python
if binding is not None:
    binding.clear()
    # A `doc:` pseudo-host survives `host_to_sources` (only `pages:` is stripped), so a
    # document-bound source arrives here, not in the branch above. Name it the way
    # `source_binding` names the same source (sweep63 batch06), not "bound".
    binding.update({"kind": ("doc" if all(str(h).startswith("doc:") for h in hosts)
                             else "bound"),
                    "hosts": sorted(hosts)})
```
(feats_index.py:373-380). This now agrees with `source_binding()`'s classification of the same
source for the single-host case sweep63 measured (`Arcanum Worlds (Odyssey of the Dragonlords)`
→ `"doc"`). Not re-filed; confirmed fixed by reading the branch and tracing the same scenario
sweep63 used.

## Everything else checked, no new findings

- **`weave_index.py`**: re-verified `_records_sig`'s per-file vs. directory-level fail-open
  distinction, `designations()`'s cache-on-success-only discipline, the stale-vs-behind staleness
  split, and the uncapped candidate/bucket reporting in `main()`. All intact, matches sweep63's
  account. No tautologies, fail-open guards, or new caps found. `norm()`'s continuity-suffix
  (`@keep`) interacting with `_STOPNAMES`/`MIN_MATCH_KEY` (a short or generic name attached to a
  rare continuity designator could bypass both filters) was checked but not filed — see Q2.
- **`reference.py`**: re-verified the calibration-gates-the-exit-code fix (`calibrated = not
  outside`, folded into `main()`'s return value) and the atomic/gated writes to
  `REFERENCE_ASSAYS.json`. Intact.
- **`recover_folder_records.py`**: re-verified the `mapped is None` vs. `mapped == []` distinction,
  the declared-vs-yielded shortfall accounting (`short_sources`), and the gated writes (both the
  per-record write and the roll compare-and-swap) correctly propagate `denied` to the exit code.
  Matches sweep63's account; no findings.
- **`deprecated/catalogue_local.py`**: unchanged self-refusing module (`raise SystemExit(_REFUSAL)`
  at import except for `--help`). The code after the raise is genuine dead code, but the module's
  own header explicitly says it is kept unrepaired on purpose as a record of the failure mode, so
  this is not "a comment claiming code is live that isn't" — the comment says the opposite.
- **`resonance.py`**: re-verified the Gauss-Seidel convergence fix (STAR/BIPARTITE/PATH4 all
  converge; `converged: False` returns `eta: None` rather than a number nobody can trust), the
  `no_evidence` vs. `eta: None` separation for both the empty-edge-set and zero-flow cases, and
  `incomparability_rate`'s unmeasured/tied/incomparable three-way split. Still zero production
  callers, as its own docstring states. No findings.
- No fail-open guards, no lifted/openable `prose_enabled`/`step4_enabled` gates, and no
  regex/escape corruption were found in any of the seven modules (all carry the `_BAD_CHARS`
  transit self-check where applicable, and every regex compiled cleanly against its stated
  intent — checked `_MAGNITUDE`/`_ACT`/`_OBJECT`/`_PATIENT`/`_REPUTATION`/`_STATBLOCK`/
  `_SETTING_META`/`_META_TERMS` in pipeline.py by hand against their documented purpose).
- No new caps/truncations (Hard Rule 0) found. All the ranked-then-uncapped reporting sections in
  `pipeline.py` (phase 7/8 refusal and empty-source rosters) and `weave_index.py` (candidate
  buckets, cross-attested roster) that sweep63 already verified uncapped remain uncapped.

## Questions (not findings)

1. **pipeline.py, `ENTRY_SCHEMA`**: `category` remains a bare `{"type": "integer"}` with no
   `enum`/`minimum`/`maximum`, unlike `topic` (enum-constrained) and `subroom` (enum-constrained).
   Local Ollama's schema-constrained decoding cannot enforce a range on a bare integer type, and
   the cloud pool arm (`_pool_answer_usable`) only checks that required keys are present, never
   that their values are in range — so an out-of-range `category` reaching the M120 fix's
   `category_rejected` branch is the *expected* path, not a rare edge case. The M120 fix makes
   this visible and auditable rather than silent, which resolves the original defect; whether the
   schema itself should also carry `"minimum": 1, "maximum": len(CATEGORIES)` (which JSON Schema
   supports and Ollama's constrained decoding can likely honor, tightening the local arm without
   touching the cloud arm's exposure) is a design choice for the owner, not a defect in the current
   code.
2. **weave_index.py, `norm()`/`_STOPNAMES`/`MIN_MATCH_KEY`**: a name whose parenthetical is a
   corpus-learned continuity designation (e.g. a hypothetical short or generic name paired with a
   `(Bayverse)`-style tag) folds to `key@designation`, which is neither an exact `_STOPNAMES`
   member nor necessarily shorter than `MIN_MATCH_KEY` even when the bare name would have been
   filtered. This was checked and not traced to any live occurrence in the corpus (no example
   found), so it is not filed as SUSPECTED; noted only because the two matching filters are
   documented as applying to "generic"/"too short" names and a continuity suffix changes both
   tests' outcomes without anyone having ruled on whether that is intended.

## Coverage
