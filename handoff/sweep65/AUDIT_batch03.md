# sweep65 batch03 audit

Auditor for batch 3 of sweep65 (maintenance run #65, 2026-09-26). Read-only throughout: nothing
under `src/`, `data/`, `state/`, `output/`, `prompts/`, `reference/` or the repo root was edited,
created or deleted this session, other than this report and the one permitted
`sweep_plan.record(...)` call. No job, drill, sweep, publish, mutate, generate, crawl, overwatch,
foreman, verify_math, or pipeline invocation was run. No subagents were spawned.

## Scope, read in full, start to finish, no sampling

- `src/pipeline.py` — 3,674 lines (read in five chunks: 1-500, 500-1000, 1000-1500, 1500-2000,
  2000-2500, 2500-3000, 3000-3400, 3400-3674 — full coverage 1-3674)
- `src/weave_index.py` — 731 lines (one pass)
- `src/feats_index.py` — 633 lines (one pass)
- `src/reference.py` — 497 lines (one pass)
- `src/recover_folder_records.py` — 380 lines (one pass)
- `src/wh40k.py` — 351 lines (one pass)
- `src/physics.py` — 312 lines (one pass)

Total: 6,578 lines across 7 modules, all read in full.

## Method

`CLAUDE.md` read first for doctrine (Hard Rule -1 escalation/halt, Hard Rule 0 no caps ever,
fail-closed, "a check that cannot fail looks exactly like a check that passed"). Every module read
top to bottom before any conclusion was drawn.

Prior-audit cross-check before writing anything: grepped `handoff/sweep64/` and `handoff/sweep63/`
for each of the seven module names.

- `handoff/sweep64/AUDIT_batch03.md` covered `pipeline.py`, `weave_index.py`, `feats_index.py`,
  `reference.py`, `recover_folder_records.py` (plus `deprecated/catalogue_local.py` and
  `resonance.py`, not in this batch). Filed one VERIFIED-still-open finding (the `physiology`
  field, discarded on every entrypass call) and confirmed the M120 `category_rejected` fix and the
  `feats_index.py` `doc:`-binding fix as landed. Both re-checked against current source below.
- `handoff/sweep64/AUDIT_batch10.md` covered `wh40k.py` (among eight other modules not in this
  batch): "all 55 axes (11 axes x 5 entries) carry a genuine 3-tuple with a `wiki`/`canon`
  provenance tag ... `_provenance`'s default to `unattributed` ... both match their docstrings."
  No finding filed against the file's own internal consistency between `compute()`'s docstring and
  `main()`'s comment — see Finding 2 below, which this read caught and that one did not.
- `handoff/sweep64/AUDIT_batch07.md` covered `physics.py`: all four functions' guard orderings
  traced, no gap found. Re-verified below; still holds.

I also searched `state/workorders.json` for each finding candidate before writing it down, per the
brief, so nothing here duplicates an order already open.

## Findings

### 1. CONFIRMED (reproduced by execution) — `pipeline.write_record_catalogue`'s ambiguous-name
merge can silently drop a disk-only entity that has NO fresh counterpart at all, even though the
function's own docstring and in-line commentary both promise "a merge never shrinks a cast."

`pipeline.py:1080-1091`:

```python
unpaired = []
for key, dsub in disk_by_key.items():
    fsub = fresh_by_key.get(key) or []
    if len(dsub) == 1 and len(fsub) == 1:
        paired[id(dsub[0])] = fsub[0]
    else:
        unpaired.extend(dsub)
if unpaired:
    ambiguous.append(nm)
    # Never shrink the cast. `surplus` is provably <= len(unpaired), because the
    # paired count for this group cannot exceed len(fgroup).
    carry.update(id(de) for de in unpaired[:max(len(dgroup) - len(fgroup), 0)])
```

`unpaired` conflates two genuinely different populations of disk rows under one name group:

  * disk rows that collide ambiguously with the fresh cast (several disk rows and several fresh
    rows share an `_entry_pair_key`, so no 1-1 pairing can be made) — for these, which specific
    fresh row a given disk row's judgments belong to is genuinely unknowable, and dropping the
    surplus is defensible;
  * disk rows whose `(name, type, description)` triple does **not exist at all** in the fresh
    cast (`fsub` is empty) — for these there is **no ambiguity whatsoever**: the row is not
    competing with anything, and the only correct action is to keep it, whole, unconditionally.

Both classes are appended to the same `unpaired` list, and only `max(len(dgroup) - len(fgroup), 0)`
of them survive via a plain list slice. The size arithmetic the docstring cites (`surplus <=
len(unpaired)`, "the merged size is max(m, k)") is correct — the merged row *count* for the name
group does come out to `max(m, k)` — but the comment's actual claim, "never shrink the cast," is
about which **entities** survive, not merely how many rows do. When true collisions and true
"disk-only, unambiguous" rows appear together in one name group and the collisions come first in
iteration order, the slice keeps redundant/collision rows and discards the unambiguous disk-only
one — an entity with genuinely unique content vanishes from the merged record with nothing logged
about it (the log line at `pipeline.py:1118-1123` reports only that the name was "ambiguous" and
that "the surplus disk rows were carried forward whole so the cast did not shrink," which is false
for the specific row that was dropped).

**Failure scenario, concrete.** A source's disk copy holds three "Widget" entries: two share one
description (`D1`, `D2`, an ordinary in-corpus duplicate) and a third (`D3`) has a *unique*
description the current re-catalogue no longer mentions at all (the wiki page changed, or the
crawl regressed). The fresh cast for this re-catalogue holds one "Widget" entry matching `D1`/
`D2`'s description. `write_record_catalogue` computes `unpaired = [D1, D2, D3]` (none pair 1-1: the
`same_desc` key has 2 disk/1 fresh, the `unique_desc` key has 1 disk/0 fresh), `max(3-1,0) = 2`, and
keeps `unpaired[:2] = [D1, D2]` — silently dropping `D3`, the one row with no ambiguity, in favour
of carrying an extra copy of content that already exists via the fresh row.

**Reproduced by execution**, in an isolated scratch copy of the module (own `HERE`/`state`/`log`
pointed at `%TEMP%\claude\sweep65_batch03_scratch`, nothing under the real `src/`/`data/`/`state/`
touched):

```
merged entry count: 3
 - Widget | same_desc | (fresh) | None
 - Widget | same_desc | D1 | M3
 - Widget | same_desc | D2 | M2

descriptions present in merged output: ['same_desc']
CONFIRMED: D3 (the entity with a description absent from BOTH the fresh cast AND
any other disk row -- zero ambiguity about whether it should be carried) was DROPPED
from the merged record, even though the docstring claims 'a merge never shrinks a cast'.
```

**Proposed fix.** Separate the two populations before slicing: any disk row whose key has an
empty `fsub` (line 1082, `fsub = fresh_by_key.get(key) or []` was falsy for that key) has no
competitor and should be carried unconditionally, exactly like the `if not fgroup:` early-return a
few lines above already does for a whole absent name. Only rows that collided against a *non-empty*
`fsub` (a real many-to-one or many-to-many ambiguity) belong in the pool the `[:N]` slice trims.

**Not already filed.** Order `b418b8b3be54` (the order this code cites for its own history) is not
referenced anywhere in `state/workorders.json`, and no prior sweep audit (`sweep60` through
`sweep64` batch03, all of which read this exact function) mentions the `unpaired[...]` slice or
this specific interaction. Filing fresh.

### 2. CONFIRMED — `wh40k.py:315-316`, a comment inside `main()` asserts something the code no
longer does: it claims every `ROSTER` axis entry is a 2-tuple and therefore prints as
`'unattributed'`, when the `ROSTER` literal a few dozen lines above it, and `compute()`'s own
docstring, both say the opposite.

```python
# ... `compute()`'s own docstring gives the reason
# the 'unattributed' default exists at all: a 2-tuple axis should say so out loud
# instead of inheriting a neighbour's tag, which keeps a gap in the reading
# visible rather than hidden behind a mark that reads as if the work had been
# done -- and every axis entry in this ROSTER is a 2-tuple, so all
# 55 are 'unattributed' today and --full showed none of it.
```

`compute()`'s docstring (`wh40k.py:210-251`), a few lines above this comment in the same file,
says the opposite happened since order `901e441aae1d` was written: "THE READING HAS NOW BEEN DONE
... (order 82fc93f056d4, owner ruling 20 of 2026-09-08) ... All 55 axes carry a `wiki`/`canon` tag
in the ROSTER itself ... MEASURED 2026-09-08: 13 wiki, 42 canon." Verified directly against the
`ROSTER` literal (`wh40k.py:48-207`): every one of the 55 axis tuples (11 axes x 5 entities) ends
in the literal string `"wiki"` or `"canon"` —

```
$ grep -c '"wiki")\|"canon")' src/wh40k.py
55
```

— confirming all 55 are 3-tuples with real provenance, not 2-tuples defaulting to
`'unattributed'`. `_provenance()` (`wh40k.py:266-274`) returns `axis_value[2]` whenever the tuple
has 3 elements, so at runtime `--full` genuinely does print `wiki`/`canon` for all 55 axes today —
the code is correct and the earlier sweep64 audit confirmed exactly that. What is stale is only
this one comment inside `main()`, which was written to justify the "show the provenance mark, not
only compute it" change (order `901e441aae1d`) against the ROSTER as it stood *at that time*
(before the later order `82fc93f056d4` did the 55-axis reading) and was never updated afterward —
unlike every neighbouring comment in this file, which marks past states with "was"/"once"/"used to"
rather than the present-tense "is"/"are ... today" this one uses.

**Failure scenario.** None functional — the running code behaves correctly (`--full` shows real
`wiki`/`canon` tags). The risk is purely to a future reader/maintainer: this comment, read on its
own, asserts the ROSTER still needs the 55-axis reading commissioned by order `82fc93f056d4`,
which could send someone to re-do work that is already done, or to distrust a correctly-working
`--full` output as covering up an unfilled gap.

**Proposed fix.** Rephrase the clause to past tense ("at the time this fix landed, every axis
entry ... was a 2-tuple ... order 82fc93f056d4 has since filled all 55 with a real provenance
tag") or simply delete the stale clause and point to `compute()`'s docstring for the current
state.

**Not already filed.** `state/workorders.json` has no reference to order `901e441aae1d`,
`82fc93f056d4`, `"2-tuple"` or `"unattributed"` in this context. Filing fresh.

## Carried forward (already open — not re-filed)

- **`pipeline.py`, `physiology`** (order in `state/workorders.json` under
  `"what": "\`physiology\` IS REQUIRED OF THE MODEL ON EVERY ENTRYPASS CALL AND READ BY NOBODY."`).
  Re-verified against current source: `grep -n physiology src/pipeline.py` still returns exactly
  the same four hits as the open order describes — the prompt instruction (`:1963-1968`), a schema
  comment (`:2050`), the schema property (`:2059`) and the `required` list (`:2066`) — and the
  results-processing loop at `phase_entrypass` (`:2349-2442`, read in full this session) still
  never calls `res.get("physiology")`. `MERGED_ENTRY_FIELDS` (`:841-849`) still does not list it.
  Unfixed, already on file; not re-filed, cited only.

## Questions (possible deliberate design, not findings)

1. **`pipeline.py`, `ENTRY_SCHEMA`'s bare `category: {"type": "integer"}`** with no `enum`/
   `minimum`/`maximum`, unlike `topic` and `subroom`. Consistent with sweep64 batch03's Q1 — the
   `category_rejected` mechanism exists precisely because the schema cannot constrain the range,
   so an out-of-range value is the expected path, not a rare edge case. Whether the schema should
   additionally carry `"minimum": 1, "maximum": len(CATEGORIES)` to tighten the local-model arm
   (Ollama's constrained decoding could likely honour it; the cloud arm's exposure is unaffected
   either way) is a design choice for the owner, not a defect in the current code. Carried forward
   from sweep64 rather than re-derived at length; still true.

## Everything else checked, no new findings

- **`pipeline.py`**: full read, 1-3674. The two-writer contract (`write_record` /
  `write_record_catalogue`), the compare-and-swap state merge (`_merge_state`/`_fold_state`/
  `save_state`), `ask_pool_first`/`_pool_answer_usable`'s cloud-then-local routing, `valid_scale_
  note`'s four-gate scale evidence test, `batch_settled`/`entry_settled`'s resume discipline, every
  phase function's absent-vs-corrupt handling (5, 6, 7, 8 each traced individually), and `main()`'s
  exit-code discipline (`sys.exit(main())`, explicit 0/1 on every path) were all read and traced.
  No fail-open guard, no tautological check, no new Hard-Rule-0 cap, no inverted condition beyond
  Finding 1 above.
- **`weave_index.py`**: full read, matches sweep64 batch03's account exactly — `_records_sig`'s
  per-file vs. directory-level fail-open split, `designations()`'s cache-on-success-only
  discipline, the `stale`/`behind` staleness split (order 9e884802918e), and the uncapped
  candidate/bucket reporting in `main()`. No new findings.
- **`feats_index.py`**: full read. `host_to_sources` raising rather than caching an empty map,
  `load_index`'s unreadable/collided fault tracking, the `doc:`-binding classification (confirmed
  fixed, matches sweep64), and `feats_for_source`'s within-source entry-collision tracking all
  traced. No new findings.
- **`reference.py`**: full read. The calibration-gates-the-exit-code fix (`calibrated = not
  outside`, folded into `main()`'s return value), the gated `REFERENCE_ASSAYS.json` write, and
  `shelfmark()`'s could-not-read-vs-genuinely-unknown-rung distinction all traced. No new findings.
- **`recover_folder_records.py`**: full read. The `mapped is None` vs. `mapped == []` distinction,
  `short_sources`' declared-vs-yielded accounting, the `EXCLUDED_REGISTER_SOURCES` guard, and the
  gated per-record and roll writes (both propagate `denied` into the exit code) all traced. No new
  findings.
- **`wh40k.py`**: full read beyond Finding 2. The gated atomic `WH40K_ASSAYS.json` write in
  `main()`, `_provenance`'s default-to-`unattributed` (never `wiki`), and the `--full` wrapped
  (not cut) citation printing all match their behaviour. No functional defect.
- **`physics.py`**: full read. All four public functions (`kinetic`, `joules_for`,
  `sphere_volume`, `binding_energy`) were traced argument-by-argument: each refuses non-positive,
  non-finite and NaN inputs, and additionally checks its own result for non-finiteness to catch
  overflow from finite, individually-accepted inputs (order 371088645964). No gap found; matches
  sweep64 batch07's account.
- No regex/escape corruption in any of the seven modules — each carries and passes its own
  `_BAD_CHARS` self-check at import time (verified by reading the check itself in each file, not
  merely trusting its presence).

## Coverage

Recorded via `sweep_plan.record('run65', [...], batch=3)` for all seven modules above, each read
in full this session. See the scratch verification script and its output:
`%TEMP%\claude\sweep65_batch03_scratch\repro.py` (isolated copy of `pipeline.py` + its direct
dependencies, own `HERE`/`state`/log paths — nothing under the real repo touched).
