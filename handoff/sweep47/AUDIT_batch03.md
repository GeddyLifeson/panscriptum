# SWEEP 47 — BATCH 03 AUDIT

Scope per brief: `src/pipeline.py`, `src/gpu_lane.py`, `src/withdraw_chapters.py`,
`src/burgs.py`, `src/scope.py`, `src/recover_folder_records.py`, `src/catalog.py`
(5,633 lines). This is an audit shift — no source file was edited.

## Coverage

Every line of all seven modules was read in full, in order, this shift:

- `src/catalog.py` — 168 lines, whole file, one pass.
- `src/scope.py` — 338 lines, whole file, one pass.
- `src/gpu_lane.py` — 685 lines, whole file, one pass.
- `src/burgs.py` — 433 lines, whole file, one pass.
- `src/withdraw_chapters.py` — 520 lines, whole file, one pass.
- `src/recover_folder_records.py` — 289 lines, whole file, one pass.
- `src/pipeline.py` — 3,207 lines, whole file, read in six sequential chunks
  (1-400, 401-800, 801-1200, 1201-1600, 1601-2000, 2001-2400, 2401-2800,
  2801-3200, 3201-3206) with no gaps between chunk boundaries.

Nothing in the seven modules was skipped or sampled. I did not read any file outside this
batch's list, with two narrow exceptions used only to verify blast radius/precedent for
findings, not audited themselves: `src/overnight.py` (grepped + two short ranges, to confirm
that `run()` actually consumes `pipeline.py`'s subprocess return code) and `src/local_agent.py`
(grepped, to confirm `pipeline` sits in `DENYLIST` and so the `file_order` LOCAL->RUN
auto-redirect would fire if this were filed at LOCAL). Neither was read in full and neither is
claimed as covered.

## Findings

### 1. NEW — filed as work order `1f8e0f1bfb26` PIPELINE_MAIN_NEVER_EXITS_NONZERO (MAJOR, SESSION)

`pipeline.py:3171-3172` is `if __name__ == "__main__": main()`, not `sys.exit(main())`.
`main()` raises `SystemExit` on only four narrow guard conditions (the source-corruption
self-check, the missing-escalation-chain guard, the `--phase` out-of-range guard, and the
pointer-past-end-with-open-phases guard). Every other termination path is a bare `return`
with no exit code:

- a phase raising an uncaught exception (`:3136-3139`, logged as `PHASE CRASHED:` with the
  full traceback, then `save_state(st); return`)
- a `KeyboardInterrupt` (`:3132-3135`, "interrupted -- state saved, safe to resume"; `return`)
- the ladder finishing with a phase LEFT OPEN / stalled (`:3162-3167`, "runner exiting with
  phase N ... STILL OPEN"; `return`)

All three log a clear failure or incompleteness and then return `None`, so the OS process exit
code is 0 in every one of them — the pattern the hunt brief names directly: "an exit code that
always says OK, so a job that accomplished nothing is logged as success."

This is not cosmetic. `overnight.py`'s `run()` (`:602-660`) launches exactly this invocation
(`overnight.py:911,1600,1650-1651`, all `[pipeline.py, "--run"]`) as a subprocess and reads
`p.returncode` directly: `if p.returncode != 0: tail(lf, name)` and
`return "ok" if p.returncode == 0 else f"rc={p.returncode}"`, and that string feeds the cycle's
own health summary via `statuses.append(...)`. A cycle in which `pipeline.py` crashed mid-phase,
or finished with a phase stalled, reports exactly the same `"ok"` as a cycle that did all its
work.

It is also the same fault class this project has already found and fixed five times elsewhere:
open order `e8466cd6ed14` (still targeting `chain.py:main()`) names `onomast.py:569-573`,
`reference.py:363-373`, `genre.py:327-331`, `sevenfold.py:412-415` and `wh40k.py:289-293` as
sites already repaired for "reports success over a write that was never verified." Neither that
sweep nor any other open order visited `pipeline.py`'s own `main()`, and its failure surface is
wider than any of the five (an uncaught crash and a mid-ladder stall, not only a denied write).

Remedy suggested in the filed order: `sys.exit(main())` at the bottom, and explicit `return 1`
on the three silent paths / `return 0` on a clean finish — the same shape the five already-fixed
sites use.

### 2. Two open work orders confirmed FIXED — do not re-file

**`f2b06f8c9476` PIPELINE_SYNTHESIS_PROMPT_FEAT_LIST_CAP** and **`8d8ba5377fb6`
SYNTH_PROMPT_CAPS_MINED_FEATS_AT_THREE** both describe the same old code:
`` ' | '.join(re.sub(...)[:150] for x in fl[:3])[:420] `` — an entity's mined feats cut to the
first three in file order (unranked), then a further per-feat and overall character cut, with
no marker.

That code no longer exists. `synthesis_prompt` (current `pipeline.py:1477-1520`) now sorts the
full feat list richest-first (`sorted(..., key=lambda s: (-len(s), s))`), packs as many as fit a
420-character budget, and — when the budget is exhausted — appends
`"[N of this entity's M mined feats withheld for prompt budget, ranked richest-first]"`. The
docstring directly above it (`:1480-1494`) names this as the fix for order `0e041fe97852`, and a
`grep -n "fl\[:3\]" src/pipeline.py` finds the pattern only inside that docstring's *quotation*
of the old code, nowhere live. Both orders describe a defect that has already been repaired;
recommend closing them rather than carrying them forward.

### 3. Open order `4ed4041c3b78` (LIMIT_ZERO_READ_AS_NO_LIMIT_THREE_MORE) is not actually sited in `burgs.py`

The brief lists this order against `burgs.py`, but reading its `where` field: it names
`src/generate.py:589`, `src/catalogue_web.py:545`, `src/feats.py:1622` — none of which is in
this batch. `burgs.py`'s own instance of the falsy-zero `--limit` bug (the one the order's `what`
text cites as precedent, "fixed ... earlier in burgs.py") is confirmed fixed in the current file:
`burgs_for`'s `stop = n if limit is None else max(0, min(int(limit), n))` (`burgs.py:258`) and
`main()`'s `ap.add_argument("--limit", type=int, default=None)` (`:295`) both use `is None`
throughout, not truthiness. Nothing to file here; noting it so the order's actual three target
files are understood to sit outside this batch rather than resolved by this batch.

### 4. Everything else read: no new verified defect

`catalog.py`, `scope.py`, `gpu_lane.py`, `withdraw_chapters.py` and
`recover_folder_records.py` are heavily self-documented with prior fixes (see each file's own
inline order citations) and I could not find a fault in any of them beyond what the brief's open
orders already name. Specific things checked and ruled out as NOT defects (recorded so a later
sweep does not re-spend time on them):

- `withdraw_chapters.py`: `moved[sub] += 1` and `extra += 1` sit outside their `if a.go:` blocks,
  so a dry run's "raw paths moved" / "unclaimed" counts are populated even without `--go`. This
  looks at first glance like a report of work that didn't happen, but it is deliberate and
  consistent with the module's own documented reasoning at `:317-323` (part (a)) for the
  identical `extra` counter: the dry run's whole job is to preview what `--go` would do, and
  `withdrawn`/`remaining` are likewise computed unconditionally for the same reason. The final
  `"DRY RUN -- pass --go to move"` line disambiguates. Not filed.
- `recover_folder_records.py`: the check-then-write on `already = bool(load(path).get("entries"))`
  followed later by `silence.write_json(path, record, ...)` is a genuine TOCTOU window (another
  writer could land real research in between), but it is exactly the standing two-writer hazard
  already covered by open order `9a44b1535851` (RECORDS_WRITTEN_OUTSIDE_THE_RECORD_WRITER), whose
  evidence explicitly discusses this "re-reads the live record and skips any source already
  holding entries" mitigation. Not a new finding.
- `gpu_lane.py`: no defects found. This module has more prior hardening (m54, m55, orders
  d316c46b67bd, e7b6dcc8d630, 763b56061157, 4822b2c5744e, b54fbcf84962) than any other file in
  the batch and none of the fail-open/lease/heartbeat logic showed a gap on this pass.
- `scope.py`: no defects found beyond the two already-open orders (both about stale cached data
  from before a code fix, not about the current code path).
- `catalog.py`: no defects found; this is the smallest and most straightforwardly correct module
  in the batch.

## Summary of filings this shift

| id | code | severity | handler |
|---|---|---|---|
| `1f8e0f1bfb26` | PIPELINE_MAIN_NEVER_EXITS_NONZERO | MAJOR | SESSION |

No other findings met the bar to file. Two open orders (`f2b06f8c9476`, `8d8ba5377fb6`) are
reported above as fixed rather than being re-filed or silently dropped.
