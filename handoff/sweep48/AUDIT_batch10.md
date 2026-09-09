# Panscriptum comprehensive sweep #48 — batch 10 audit

**Modules and lines read (full, no sampling):**

| module | lines read |
|---|---|
| src/publish.py | 1979 (all) |
| src/sweep_plan.py | 1117 (all) |
| src/derivation.py | 811 (all) |
| src/gpu_lane.py | 684 (all) |
| src/withdraw_chapters.py | 519 (all) |
| src/genre.py | 381 (all) |
| src/descending_ladder.py | 357 (all) |
| src/cosmology_graph.py | 260 (all) |

Every finding below was verified against the source with `grep -n`/`sed -n` at the time of
writing (2026-09-08), not inferred from memory of the file.

---

## Findings

### MINOR — cosmology_graph.py:131-132 — two stale line citations, one badly drifted

```python
131:                # WHOLE list, no cap -- Hard Rule 0, ruled 2026-08-24. `weave.py:519` and
132:                # `pipeline.py:2401` write this same `shared_sample` key and were both brought in
```

Verified against the actual sites:

* `weave.py` writes `"shared_sample": shared[(a, b)]}` at **line 671**, not 519 (drift +152).
* `pipeline.py` writes the identical line at **line 3133**, not 2401 (drift +732).

Both are real, current writers of `shared_sample` (confirmed by `grep -n shared_sample
src/weave.py src/pipeline.py src/resonance.py`), so the claim itself is still true — only the
line numbers a reader would jump to are wrong, and badly enough (732 lines) that jumping to
`pipeline.py:2401` lands nowhere near the relevant code. `resonance.py:290` and `resonance.py:295`,
cited elsewhere in this same file (lines 65-66 and 135-136), both check out exactly.

**Remedy:** update the two citations to `weave.py:671` and `pipeline.py:3133`, or drop the line
numbers and cite by function/key name only (as the `resonance.py:295` neighbour effectively
does by naming the key) so a future refactor can't re-drift it.

---

### MINOR — descending_ladder.py:63 — stale citation, `pipeline.py:1538` should be `pipeline.py:2471`

```
59	So READ THE FIRST SECTION OF THIS DOCSTRING AS STILL TRUE, ... the problem is that a finished
60	stage nothing dispatches to is indistinguishable from a stage that was never written
61	(`pipeline.py:1538` says it in those words).
```

The quoted sentence — "A finished stage that nothing dispatches to is indistinguishable from a
stage that was never written" — actually lives at **pipeline.py:2471**, inside the phase-4
docstring. `pipeline.py:1538` is unrelated code (the feats block-batching logic). Drift of 933
lines.

**Remedy:** same as above — repoint the citation to line 2471.

---

### MINOR — withdraw_chapters.py:511 — stale self-citation, `:184` should be `:209`

```
511	    # that matched nothing already raised SystemExit at :184 and never reaches here.
512	    # Order b422c125e93e.
```

This is a self-referential citation (same file). The `raise SystemExit("part of that selection
matches nothing in the catalog...")` it refers to is at **line 209**, not 184 — the file grew by
~25 lines above that point since the comment was written, and the citation was never updated.

**Remedy:** repoint to `:209`, or say "the selector-mismatch refusal above" instead of a line
number, since it's in the same function.

---

### MINOR — derivation.py:628-630 and :790-792 — stale docstring describes `SCAN_MODULES` as still using the bug it was fixed for

Two places in this file's own comments describe `SCAN_MODULES`/`_scan_modules()` as built from
`os.listdir(HERE)` — flat, top-level only, still missing `src/deprecated/`:

```
628	    The mislabel was total rather than occasional: `SCAN_MODULES` is built from `os.listdir(HERE)`
629	    over the same directory this function then reads (order ca1ed2be8c51 notes this listing is
630	    still flat and misses `src/deprecated/`, left open this shift -- see the comment above
631	    `SCAN_MODULES`), so the file-not-found branch is unreachable outside a race -- ...
```

and again in `main()`:

```
790	            # Print WHICH failure it was. `(absent)` for everything was actively wrong here:
791	            # SCAN_MODULES is built from os.listdir of this same directory, so "absent" is a
792	            # race and "will not parse" is the only thing a reader realistically sees.
```

But `_scan_modules()` itself, immediately above (derivation.py:584-596), already uses
`os.walk(HERE)` recursively, and the large comment block directly above `_scan_modules()`
(lines 555-579) explicitly says this was fixed under the **same order id** (`ca1ed2be8c51`) and
marks it **"NO LONGER FLAT ... closed 2026-09-06."** So the file contradicts itself: one comment
block says the flat-listing bug under order ca1ed2be8c51 is closed, and two other comment blocks
in the same file, citing the same order, still describe it as open and still claim the
file-not-found branch is "unreachable outside a race" for a reason (flat top-level-only listing)
that the code no longer has.

This isn't just cosmetic: a reader auditing "is this module's directory walk still missing
`src/deprecated/`" would read lines 628-630 or 790-792 in isolation and conclude the gap is
still open, when it was actually closed in the same file two sections earlier.

**Remedy:** update both stale passages to reflect that `_scan_modules()` now walks recursively
(fixed, order ca1ed2be8c51, closed 2026-09-06) — the "file-not-found is a race, not a real
outcome" reasoning still holds, it just no longer depends on a *flat* listing to be true.

---

### MINOR — publish.py: several unmarked `str(e)[:N]` truncations on diagnostic/finding text

`publish.py` is otherwise unusually disciplined about this exact defect class — nine separate
`order`-tagged comments in the file describe fixing an unmarked truncation on an exception
message elsewhere in the same file (`git()`'s stderr, `_unpushed()`'s two branches, the
escalation evidence list, `PushHeld`'s two messages, `main()`'s catch-all). Four sites were not
covered by that pass and are still silently truncated with no `…`/count-remaining marker
(compare `_marked()`, defined in this same file for exactly this purpose but not used at any of
these four sites):

1. **`scan_for_secrets`, line 664** — the UNSCANNABLE finding text:
   ```python
   _add((rel, 0, "unscannable"),
        (rel, 0, "UNSCANNABLE — could not be read for scanning (%s: %s); "
                 "refusing rather than passing it unexamined"
                 % (type(e).__name__, str(e)[:80])))
   ```
   This is a *finding* in the list `push()` reads before deciding whether to refuse a publish —
   exactly the "diagnostic or finding" class Hard Rule 0 is being read broadly to cover for this
   sweep. If the underlying `OSError`/`UnicodeDecodeError` text runs past 80 characters, the
   operator sees a silently clipped reason for why a file could not be scanned.

2. **`snapshot()`, line 693** — `"detail": str(e)[:200]` inside `standards_unavailable`, which is
   written into the *publicly published* `docs/state.json`. Unmarked.

3. **`_unpushed()`, lines 766 and 794** — `"git rev-list answered %r, which is not a count" %
   n[:40]` / `local[:40]`. Both are on the "git said something unexpected" branch; low
   likelihood of firing, still silently clipped, and the neighbouring comments at 755-761 and
   786-789 argue at length for keeping *other* strings on this same code path whole.

4. **`push()`, line 1591** — the mutation-unsafe refusal message:
   ```python
   raise RuntimeError(
       "REFUSING TO PUSH: a mutation run was active %s and had NOT declared itself "
       "sandboxed, so files in src/ may be deliberately corrupt right now (%s)."
       % (_when, json.dumps(_rec, default=str)[:200]))
   ```
   Checked `mutate.py`'s `_lock_acquire` (line ~263-271): the lock record includes a `"targets"`
   key holding the full list of files a mutation run claimed, and `"sandboxed"` is appended
   *after* `targets` in the dict literal. If `targets` is long, `json.dumps(_rec)` can easily
   exceed 200 characters before reaching `"sandboxed"` — so the one refusal message an operator
   reads to understand *why* a push was blocked can silently omit the very field the refusal
   turns on. (The refusal *decision* itself is correct — `_mutation_unsafe` reads
   `rec.get("sandboxed")` directly off the untruncated dict, never off this string — so this is
   a diagnostics-only defect, not a gating bug. The underlying lock file `state/MUTATION_ACTIVE.json`
   persists on disk with the full record, but the message doesn't say so or name the path.)

**Remedy:** route all four through `_marked()` (already defined in this file), or for site 4,
either widen the cap or state the lock file's path in the message so an operator knows where to
look for the untruncated record.

---

### QUESTION (checked, no bug found) — sweep_plan.py `missing()` / self-reported coverage

Per the sweep brief, I specifically checked whether `missing(run)` can ever report full coverage
(`[]`) for a run that did not actually read a module. Traced the whole path:
`missing()` → `covered_by(run)` → shards written only by `record()`, which validates every
name through `normalise_module()` against `known_modules()` before it can land in the
`"modules"` list (unresolvable names are diverted to `"unknown"` and never count as coverage).

I did not find a mechanism that fabricates coverage for a module that was never named by a
`record()` call. The system's completeness proof is fundamentally a **self-report** — nothing
here (or elsewhere in this batch) verifies that a batch which called `record()` with a module
name actually read that module's content, the same trust boundary this very sweep operates
under. That's a property of the design, already implicit in how `record()`'s own docstring
describes it ("`record()` is called by sixteen batch agents at the end of work already done"),
not a new defect — flagging it as a question rather than a finding per the brief's own
guidance, since I could not verify it as a bug rather than an accepted design boundary.

One adjacent, low-severity observation: `covered_by()`'s and `coverage_map()`'s fallback reads
of the legacy aggregate `SWEEP_COVERAGE.json` do not re-run `normalise_module()` on the keys
already sitting in that file (which predates the `order f307490add1e` validation regime). This
is inert rather than exploitable — a legacy mis-spelled key simply matches no current module
label in `modules()`, so it cannot mark a *real* module as falsely covered — but it means a
pre-order legacy entry could in principle sit there forever without ever being checked against
`known_modules()`. Not raised as a finding because I could not construct a case where it
produces a wrong answer, only a possibly-dead one.

---

## What I read and found nothing wrong in

* **src/publish.py** — full file. The three publish-time locks (`_scrub`/`scrub_text` credential
  scrubbing, `scan_for_secrets` LOCK THREE, `ledger_guard`/`mutate` import-or-refuse interlocks),
  `_is_agent_scratch`/`CODE_FREE_DIRS`, `gitignore_lines()`, `prune_export`, `sync_tree`'s
  root-file sweep, `_live_root_state`/`_live_file_state`/`_same_dir`/`_may_delete_in_export`,
  `PushHeld`/`_unpushed()`'s three-outcome push logic, `maintenance_shift_live`, and `main()`'s
  halt re-check per loop cycle. I traced every branch looking specifically for a path that lets
  something unintended reach the public repo (this sweep's #1 priority) and for a gate whose
  exception arm falls through to the guarded action; I did not find one. This file is unusually
  self-auditing — most of its own historical defects are already named, dated and fixed in its
  own comments — and the four unmarked-truncation sites above are the only gaps I could
  substantiate.
* **src/sweep_plan.py** — full file, including the known, already-filed `freeze_plan`
  check-then-write race (order bf316bbb7f89, not re-reported) and `missing()`'s self-report
  design (discussed as a QUESTION above, not a finding). `record()`'s shard-write path,
  `normalise_module()`'s exact-match/ambiguity-refusal logic, `check_briefs()`'s
  frozen-plan-vs-live-tree handling, and `main()`'s CLI all read correctly to me.
* **src/derivation.py** — full file, including the ledger's own kind/parent/cycle validation in
  `check_graph()`, the (now-fixed, and confirmed no external caller re-triggers it) `depth()`
  non-termination-on-cycle history, and `scan_constants_with_reason()`'s AST walk. Only the two
  stale citations above.
* **src/gpu_lane.py** — full file. This is the most heavily hardened module in the batch
  (Windows `_alive()` process-liveness check, slot/claim lease-and-heartbeat logic, the
  three-way `_take_slot()` return contract, `_heartbeat`/`_touch`'s non-resurrection guarantee,
  `_remove_retry`'s Windows-denial retry). I could not find a new race, an unreachable guard, or
  a fail-open path that isn't already deliberate and documented as such. No findings.
* **src/withdraw_chapters.py** — full file, including the plant-wide `escalation.assert_clear`
  wiring, `select()`'s exact-match filter, the per-selector unknown-name refusal, the snapshot-
  before-`--go`-move sequence, `_archive_name_free`'s collision guard, the per-file vs.
  per-entry withdrawal-record bookkeeping, and the manifest merge logic. Only the one stale
  self-citation above.
* **src/genre.py** — full file, including the already-filed open question at line 253
  (`genres_scored` invariant, order f646c1c5f1d0 — not re-reported) and the rest of
  `classify_text`/`classify_source`'s uncapped-ranking logic, `_project_pipeline()`'s
  interpreter-diagnosis, and `_cut()`'s marked truncation. No new findings.
* **src/descending_ladder.py** — full file, including the deliberately-unwired/HELD status this
  module documents about itself (order 66f96febdb3a), the U-shaped Ruin-column warning, and the
  domain-guarded `rung_for_length`/`shrink_report`/`transgression_bits` arithmetic. Only the one
  stale citation above; the `assay.py:74-75`, `anchors.py:43` and `publish.py:1346` citations in
  this same docstring were checked and are all still accurate (assay.py's is off by ~2 lines,
  landing on the header row immediately above the cited table rather than the rows themselves —
  too small a drift to be worth reporting as its own finding).
* **src/cosmology_graph.py** — full file, including the IDF weighting formula, the
  uncapped-pair-list write (`pairs_filtered: False`, no `>= 1.0` filter), `components()`'s
  connected-component walk, and the gated `write_json` verdict in `main()`. Only the two stale
  citations above.
