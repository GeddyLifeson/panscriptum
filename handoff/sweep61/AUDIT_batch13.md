# sweep61 batch 13 — audit

Scope: read every line, start to finish, of the following (line counts from `wc -l` at time of
reading):

- `src/assay.py` (1946 lines)
- `src/silence.py` (1313 lines)
- `src/scout.py` (833 lines)
- `src/custodes.py` (714 lines)
- `src/policy.py` (611 lines)
- `src/render.py` (441 lines)
- `src/grounding.py` (361 lines)
- `src/resonance.py` (298 lines)

All eight read in full, no sampling.

## Note on render.py's empty-library guard (order 9f75ae0b8d96)

Checked as asked. `main()` (render.py:307-319) calls `WS.build_all(limit=1)` and reads
`tree.get("worlds") or {}` and, before any indexing (`built[0]`, `next(iter(worlds.values()))`),
tests `if not built or not worlds:` and prints which of the two was empty and returns 1. This is
correctly a guard-before-index, verified by reading the code (no need to run it, since the library
is halted tonight). No defect found here.

## General finding

These eight modules are the most heavily self-audited part of this codebase: nearly every
constant table, validation gate and interval calculation carries its own paragraph naming a past
defect, the order that fixed it, and how it was measured. Reading them end to end surfaced one
concrete bug; everything else is either already-documented-and-fixed, or a deliberately-flagged
open question (Threnody's veto never firing in production, `resonance.py` having no production
caller, etc. — these are already named in the code as open, not new findings).

## Findings

### 1. VERIFIED — `scout.py: sweep()`, `--limit 0` is treated as "no limit", not "scout zero"

`scout.py:613-615`:
```python
if limit:
    deferred = order[limit:]
    order = order[:limit]
```
`limit` here is `sweep`'s own parameter (`sweep(limit=None, register=True)`), populated from
`main()`'s `--limit` argparse option (`type=int, default=None`, no minimum enforced). `if limit:`
is a truthiness test, so `limit=0` (an explicit `--limit 0`) is indistinguishable from
`limit=None`: the slicing is skipped entirely and the *whole* hostless queue is scouted that
cycle instead of none of it. Every other `--limit` consumer in this same batch checks the
sentinel correctly — `policy.py`'s `--limit` handling three files over uses
`all_records if a.limit is None else all_records[:a.limit]`, which is `is None`, not truthiness,
and behaves correctly at `--limit 0`. `scout.py` is the one that diverges. Low-severity (an
operator asking for zero work per cycle is an unusual thing to do, and nothing in the codebase
currently calls `sweep(limit=0)`), but it is a real wrong-branch bug reachable from the documented
CLI surface, not a hypothetical.

Verified by reading the source and argparse definition (`scout.py:807-812`); not executed, per
the halt.

## Questions (not findings — plausibly deliberate, already flagged by the code itself)

- `resonance.py`: `hodge_decompose`/`resonance_strength` have zero production callers, and
  Threnody's curl veto in `custodes.convene()` has never fired on a real being because nothing
  computes `eta` in production. The module's own docstring already states this as an open,
  known gap (order f467f662be4b), not something this sweep is newly reporting.
- `policy.py`'s `is_type`/`ARG_REQUIRED` validation happens inside `check_rule()` at each rule
  evaluation, not literally "at load" as several comments phrase it (there is no separate
  module-load-time validation pass over the rule tables) — functionally equivalent since any
  evaluation of a malformed rule still raises before publishing a false verdict, so this is a
  wording nuance rather than a defect worth a separate finding.

## Summary of findings by kind

- Tautology / check that cannot fail: 0
- Fail-open guard: 0
- Cap/truncation hiding data (Hard Rule 0): 0 (all such defects in these 8 modules are already
  fixed and documented as such)
- Real bug (wrong branch / off-by-one / crash / race): 1 (scout.py `sweep()` `--limit 0`, above)
- False comment/docstring beside the code: 0
- Dead code: 0 new (the three `REPORTED DEAD, NOT DELETED` functions in assay.py —
  `band_for_quantity`, `null_instrument`, `interval_from_hands` — are already labelled dead by
  owner ruling in their own comments, not a new finding)
