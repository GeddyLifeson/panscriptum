# run46 batch 8 -- AUDIT

Modules read end to end, every line: `src/magnitude.py` (1937), `src/allsweep.py` (985),
`src/estate.py` (692), `src/weave_index.py` (530), `src/reference.py` (485),
`src/grounding.py` (344), `src/navtree.py` (335), `src/tempus.py` (274). ~5,582 lines.
Also read `src/scope.py` (337, not in the batch but required context for the assigned
question) and consulted `src/workorders.py`'s `file_order` signature, `src/local_agent.py`'s
`DENYLIST`, and several prior handoffs (`handoff/nets_20260906/longtail.py`,
`handoff/sweep39/AUDIT_batch08.md`, `handoff/sweep33/AUDIT_batch09.md`) for standing context
on the one finding below. `allsweep.py` was read but never executed, per instructions.

## FILED

### PROBEUNREAD_SWALLOWED_AS_NO_CEILING -- MAJOR -- RUN -- order `3eeedaafce1e`

**This is the assigned question, and the answer is yes: `host_ceiling` fabricates "no
ceiling" from a refusal, one layer below where `scope.py` was fixed to stop exactly that.**

`magnitude.host_ceiling()` (src/magnitude.py:1721-1747) tries `data/SCOPE.json` on disk
first; if that row is absent or carries no ceiling, it falls back to a *live*
`SCOPE.scope_for(host)` call, wrapped in:

```
try:
    row = SCOPE.scope_for(host)
    if row and row.get("ceiling"):
        cl = (row.get("scope"), row["ceiling"])
except Exception:
    silence.note("magnitude.py:host_ceiling-live")
_SCOPE_CACHE[host] = cl
return cl
```

`scope.ProbeUnread` (added to `scope.py` 2026-09-06, this same shift) is a subclass of
`Exception`. When the live probe cannot be READ -- throttled, unreachable, a non-JSON
response, a fetch that came back empty after a real search -- `scope_for` now raises
`ProbeUnread` instead of the old silent `None`. `host_ceiling`'s bare `except Exception`
catches it exactly as it would catch any other failure, `cl` stays `None` (the value that
also means "read, and genuinely has no scope"), and that `None` is written into
`_SCOPE_CACHE[host]` -- a module-level dict with no expiry for the life of the process.

`run_batch()` calls `assay_entity(c, n, h, ceiling=host_ceiling(h))` for every entity in the
queue, threaded across up to 8 workers. The first time a host's live probe is attempted and
throttled, every entity from that host for the rest of the run -- scored by any worker,
because the cache is shared -- gets `ceiling=None`, i.e. no clamp at all. That is the precise
failure `host_ceiling`'s own docstring names as the reason the clamp exists: *"Jace Beleren
came back at M10.77 against the charter's published 𝔄 M2.88."* A refusal to answer has been
turned back into an unbounded anchor, silently, mid-batch.

Contrast with the sibling call site 200 lines above, in the `BENCHMARKS` loop
(magnitude.py:~1600), which this same shift fixed correctly: it catches `SCOPE.ProbeUnread`
specifically, records the entity as `SCOPE_UNMEASURED` with `consistent: None`, and moves on
without scoring it against a fabricated ceiling. `host_ceiling` needed the identical shape
and did not get it.

**A prior shift already looked at this exact call site and reasoned past it.**
`handoff/nets_20260906/longtail.py:91` says: *"magnitude.py:1718 (host_ceiling's live probe)
already catches Exception and is unaffected."* That is true only of "does not crash" --
`host_ceiling` does not propagate the refusal, so nothing stops running -- but "unaffected"
is the wrong word for a function whose entire job is deciding whether an anchor gets clamped,
and which now silently decides "no clamp" on a refusal it cannot tell apart from a genuine
empty scope. This reads as the same trap the batch brief names: a comment recording what a
line used to mean (or, here, what a sibling analysis concluded about a *different* question --
whether the loop crashes) standing in for what the line does now.

It was also raised once before as an open **question**, not a finding:
`handoff/sweep39/AUDIT_batch08.md` Q2 discusses `host_ceiling` caching a `None` result for
the whole run and calls it "a defensible fail-open," because at that time the only way into
the `except Exception` arm was a genuine disk-read failure or an ordinary transport error --
rare, and not a documented refusal. `ProbeUnread` changes the shape of that question: the
same arm now catches a *specifically-raised, specifically-documented* "the host was not
read" signal, on a path (SCOPE.json probing under an active batch, against real wikis) where
throttling is the common case rather than the rare one. What was a judgment call against a
rare accident is now a routine mistranslation of a named refusal.

**Filed to RUN rather than LOCAL**, because the fix is not mechanical substitution: it has
to add a `except SCOPE.ProbeUnread` arm that does NOT populate `_SCOPE_CACHE` with a ceiling
for that host (so the next call retries rather than serving the refusal forever, matching
`scope.build()`'s own rule for its cache), and it has to leave the plain `except Exception`
arm's existing behavior alone for every other failure shape -- getting the ordering and the
non-caching right needs the same judgment `scope.py`'s own fix exercised, not a keyword swap.
`magnitude.py` is not on `local_agent.DENYLIST`, but the nature of the change argues for a
session that can verify it against the batch's live behavior rather than the mechanical
rung.

## READ, NO FINDING

- **`src/magnitude.py`** -- full read, 1937 lines. Everything downstream of the one issue
  above is exceptionally well-guarded: five explicit verification guards (verbatim citation,
  axis relevance, subject/doer check, saturation, quantity-vs-guard-3 ordering), all cross-
  referenced against their own prior defects in comments that are honest about what changed
  and why. The `BENCHMARKS` calibration loop's own `ProbeUnread` handler (the one this task
  flagged as already fixed) is correct: it records `SCOPE_UNMEASURED`, sets `consistent:
  None`, and calls `_land(rows, False)` so the pass is never marked complete on an
  unmeasured entity. `--one`'s CLI path now correctly passes `ceiling=host_ceiling(...)`
  (an earlier sweep, sweep38-batch08, found this missing; it is present now). No caps on
  reasons/citations/rejections found; every truncation site is either ranked-with-disclosure
  (`[:N]` with an "and N more" line, e.g. the top-18 weave backbone list) or has been
  explicitly removed with a comment explaining why (`candidates()`'s former `cap` param,
  `compose()`'s round-robin budget spender).
- **`src/allsweep.py`** -- full read, 985 lines. Never executed, per instructions. All
  console-display cuts are disclosed via `_marked`/`_head` helpers that name how much was cut
  and point at the full record in `ALLSWEEP.json`. The VERIFY/LINT/ESTATE/RECONCILE tiers'
  grading logic (which rc means broken vs. findings, which rows count toward `bad`) is
  internally consistent with the comments explaining each historical fix. No unmarked caps,
  no checks that cannot fail.
- **`src/estate.py`** -- full read, 692 lines. The file-inspection logic (`inspect()`) has
  careful, currently-correct handling of transient/racy files (a stat failure gets one retry
  before being graded, `TRANSIENT_EXT` files are exempted from the zero-bytes check) that
  matches its own doc comments about prior false-positive incidents. Every `note()` call site
  states `bad=` explicitly per the module's own "row that will not say is a fault" rule.
- **`src/weave_index.py`** -- full read, 530 lines. `_records_sig()`'s `None`-signature path
  (an unstattable file mid-enumeration) correctly refuses to poison the cache while still
  returning every file that WAS readable, matching the comment's claim. `build()`'s excluded-
  entry accounting (`excluded` Counter) and `main()`'s uncapped candidate reporting both check
  out against the printed report.
- **`src/reference.py`** -- full read, 485 lines. Three hand-built calibration worksheets
  (Goku, Naruto, Luffy) plus comparison/citation machinery. `main()`'s exit code now correctly
  gates on both "did the write land" and "did the calibration hold" (order d049dbbfed6e, prior
  fix, verified present). No caps on diagnostic output.
- **`src/grounding.py`** -- full read, 344 lines. `classify_text`/`classify_source` both
  score the full grounding field (no truncated denominator) per the HARD RULE 0 fixes
  documented in their own docstrings, verified against the current code rather than the
  comment alone.
- **`src/navtree.py`** -- full read, 335 lines. `build()` correctly makes every addressed
  source and world reachable (no 40-world truncation found in current code); `main()`'s exit
  code correctly returns 1 when the audit write is denied OR when problems exist, even on a
  read-only run (order 3726ed72236c, verified present).
- **`src/tempus.py`** -- full read, 274 lines. Pure-function physics/doctrine module, no
  I/O, no caps, nothing to find; `prescience_horizon_bits` and `retrocausality_beta` both
  guard their numeric domains (positive lead time, non-positive backwards-causation span)
  correctly.

## QUESTIONS

None beyond the one filed above, which was asked outright by the batch brief and is
answered there rather than left open.

## COVERAGE

Recorded via `sweep_plan.record('run46', [...], batch=8)` for all eight assigned modules
(magnitude.py, allsweep.py, estate.py, weave_index.py, reference.py, grounding.py,
navtree.py, tempus.py) -- each read end to end. `scope.py` was also read in full but is not
included in the coverage call since it was not part of this batch's assignment.
