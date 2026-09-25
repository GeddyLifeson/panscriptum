# sweep61 batch 16 — audit

Scope: read every line, start to finish, of all eight modules in this batch:

- `src/local_agent.py` (1650 lines)
- `src/binding_health.py` (1601 lines)
- `src/completeness.py` (905 lines)
- `src/secondopinion.py` (708 lines)
- `src/canon_backup.py` (549 lines)
- `src/axis_correlation.py` (443 lines)
- `src/descending_ladder.py` (362 lines)
- `src/tells.py` (303 lines)

Read-only pass. No edits made under `src/`, `state/`, `data/`, or `config.yaml`.

## Summary

This batch is unusually mature. Every one of the eight modules carries extensive in-place
documentation of *previously found and already-fixed* defects (tautologies, fail-open guards,
silent truncations, discarded write verdicts, TOCTOU races) — each cited with an order ID and a
"how it was found / how it was verified" note. I read every one of those historical notes against
the code beside it and did not find a live recurrence of any of them. I looked hard for a *new*
instance of the five priority classes (tautologies, fail-open guards, Hard-Rule-0 caps, real bugs,
false comments) and did not find a VERIFIED defect in any of the eight files.

**Findings by kind: 0 VERIFIED bugs, 0 VERIFIED fail-open guards, 0 VERIFIED tautologies, 0
VERIFIED Hard-Rule-0 cap violations, 0 false comments found. 2 QUESTIONs (below), both low
confidence, neither meets the bar for a finding.**

## Verification method

- Traced every regex/format string named in comments (e.g. `tells.py`'s `_BLOCKED_MARK =
  "refusal marker"` against `feats.page_looks_real`'s actual refusal-marker message text in
  `src/feats.py:424-431` — confirmed the substring is present verbatim, so the match is live, not
  a silently-dead check as it first appeared).
- Hand-traced `descending_ladder.rung_for_length`'s boundary loop and `binding_health._spread`'s
  interpolation formula against sample inputs to rule out off-by-one / duplicate-index bugs
  (`_spread`'s `if j not in picked` guard is provably unreachable while `n > want`, confirming the
  docstring's own "Distinct by construction" claim rather than contradicting it).
- Grepped this batch for `[:N]` slices and checked each site: all are either (a) probe/display
  budgets that are announced with a count and "N more" language (e.g.
  `axis_correlation.py --top`, `secondopinion.py`'s `sites[:4]` / `ranked[:6]`, both followed by
  "+N more"), or (b) references *inside comments* narrating a past bug's `[:5]`/`[:33]`/`[:40]`
  cap that has since been removed (verified by reading the surrounding code, not just the
  grep hit) — none is a live, unmarked truncation of a stored roster.
- Checked `secondopinion.ran_clean()`'s `all(...)` is never vacuously true: `run()` always
  populates exactly the three fixed tool keys, so `got` is never empty.
- Confirmed `tells.py` is wired (imported by `standards.py` and `style_audit.py`), not dead code
  as an initial read of its own `prompt_in_sync` docstring might suggest before checking callers.
- Read `axis_correlation.widening()`'s single shared `sigma` against its only caller
  (`drill.py:21131`, a net fixture) and confirmed production code (`assay.py`) calls `rho()`
  pairwise with its own per-axis variance rather than `widening()`, so the shared-sigma shape is
  scoped to that test net and not a production simplification bug.

## Questions (not findings — flagged for a human, not filed)

1. **`src/local_agent.py:892-894`, `t_propose_patch`** — the audit-trail `entry` appended to
   `log` truncates `why`, `find`, and `replace` to `[:200]` characters each, silently, with no
   "+N chars" marker. This is the same *shape* of defect this project has fixed repeatedly
   elsewhere in this exact codebase under "STORED WHOLE" (e.g. `binding_health.quarantine()`'s
   reason field, `binding_health._fetch_chars`'s and `_probe_reachable`'s exception text, both
   explicitly citing Hard Rule 0). SUSPECTED, not VERIFIED: I could not find any downstream
   consumer that reads `patches[].find`/`.replace` programmatically (no other module parses
   `local_agent.run()`'s JSON for these fields; `main()` only re-serializes the whole `out` dict
   to a console line that is itself capped, announced, at 8000 characters). If this log is purely
   a human-readable console/audit trail and never a record another process acts on, the cap is
   probably fine as a display truncation; if `patches` is ever persisted or parsed elsewhere, the
   200-char cut would hide the same information the "STORED WHOLE" fixes exist to preserve.

2. **`src/canon_backup.py:274`, `prune()`** — `for f in snaps[:-keep] if keep > 0 else []:`
   silently prunes *nothing* when `--keep 0` or a negative `--keep` is passed, with no comment
   explaining the choice — notable only because every other non-obvious line in this file (a
   file that documents five separate historical defects in loving detail) carries one. Not
   exploitable (the argparse default is `KEEP=7`), and refusing-to-delete is the safe direction,
   so this is a QUESTION about documentation completeness, not a defect.

No dead code, false comments, or fail-open guards were found beyond what the modules' own
comments already record as known, historical, and handled.
