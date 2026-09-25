# sweep63 batch16 — audit

Scope: read every line, start to finish (no sampling), of all eight modules in this batch:

- `src/local_agent.py`      1650 lines — read in full (2 chunks) [SAFETY-CRITICAL: write gate]
- `src/binding_health.py`   1601 lines — read in full (2 chunks)
- `src/completeness.py`      905 lines — read in full (1 chunk)
- `src/secondopinion.py`     708 lines — read in full (1 chunk)
- `src/canon_backup.py`      549 lines — read in full (1 chunk)
- `src/pick_model.py`        449 lines — read in full (1 chunk)
- `src/catalogue_models.py`  364 lines — read in full (1 chunk)
- `src/entity_match.py`      319 lines — read in full (1 chunk)

Total: 6,545 lines across 8 modules. Read-only; nothing under `src/`, `data/`, `state/` was
edited, and no pipeline/drill/verify_math/mutate/publish command was run.

## Context and method

CLAUDE.md's Hard Rule -1 (escalation/halt) and Hard Rule 0 (no caps) were skimmed first.
`handoff/sweep61/` was grepped for these eight module names before reading code. Five of the
eight (`local_agent.py`, `binding_health.py`, `completeness.py`, `secondopinion.py`,
`canon_backup.py`) were sweep61 batch16's exact scope and that audit's findings/verification
notes were read in full; the other three were covered piecemeal in sweep61 batch10
(`pick_model.py`), batch14 (`entity_match.py`) and batch15 (`catalogue_models.py`), and those
sections were read too. None of sweep61's prior findings, verified fixes, or documented-and-
handled shapes (the extensive in-code "order" comments) are re-reported here.

This is a heavily audited, mature codebase. Every module carries dense inline documentation of
previously found and fixed defects (tautologies, fail-open guards, caps, discarded write
verdicts, TOCTOU races, truthiness-vs-`is None` bugs), each cited by order ID with its own
verification note. I traced the load-bearing logic by hand against the specific hazards this
project has been bitten by before (Hard Rule 0 caps, fail-open guards, checks that cannot fail,
races on shared state files) and did not find a live recurrence of any previously-fixed shape.

## Findings

**0 VERIFIED. 1 SUSPECTED (new, not in either sweep61 audit). 0 new QUESTIONS beyond two
carried forward from sweep61 for visibility (still open, not re-argued).**

### 1. SUSPECTED — `src/pick_model.py:340-342`, `main()` — a falsy real VRAM reading is
   silently replaced by the 10.0GB fallback while `vram_measured` still claims a real reading

```python
_measured_vram = total_vram_gb()
vram_measured = _measured_vram is not None
budget = (_measured_vram or 10.0) - VRAM_RESERVE_GB
```

`total_vram_gb()` (lines 183-199) returns `None` on any probe failure, or a float (GB) parsed
from `nvidia-smi --query-gpu=memory.total` on success — including, in principle, `0.0` if the
driver ever reports a total of 0 (a wedged/reset GPU, a broken passthrough, a driver that
answers before the card is fully enumerated). `vram_measured` is computed correctly with
`is not None`, so it would report `True` for a genuine `0.0` reading. But `budget` is computed
with `_measured_vram or 10.0` — plain truthiness — so a real `0.0` reading falls through to the
10.0GB assumed fallback exactly as if `total_vram_gb()` had returned `None`, while
`vram_measured` still says the budget was measured. The residency gate (`resident()`, called at
line 360 only `if vram_measured`) would then enforce a fabricated 9.0GB budget against a card
that actually reported having 0GB, and `_budget_note()` (lines 344-346) would print it as
`"9.0GB"` rather than `"assumed 9.0GB (nvidia-smi unavailable)"` — the exact "a guess enforcing
a rule it cannot support" failure this same file's own header comment on `_measured_vram` (order
322e45cf2ea1) was written to prevent, and the exact truthiness-vs-`is not None` shape this same
`main()` was independently fixed for at the `vram_gb` print branch eleven lines later (order
ae7b56cd43d0, "`is not None`, NOT TRUTHINESS, AND 0.0 GETS ITS OWN SENTENCE").

Not VERIFIED because I could not reproduce a live `0.0` total reading (that would need an
actually-wedged GPU, out of scope for a read-only audit) and a real card reporting literally 0
bytes of total VRAM is a very unlikely condition — this is not the "browser and Discord ate the
free memory" case `free_vram_gb()`'s sibling fix (ae7b56cd43d0) targeted, which is common; a
`0` *total* would mean the driver itself is confused. Flagged because it is the identical bug
shape the file has already found and fixed once, left unfixed at the one call site that feeds
the value the fix's sibling branch treats as authoritative. Suggested fix: `budget =
(_measured_vram if vram_measured else 10.0) - VRAM_RESERVE_GB`.

## What was checked and ruled out (not reported as findings)

- `local_agent.py`: `_safe()`'s eight documented bypass classes (case, name prefix, ADS,
  case-sensitive extension, unlisted directory, junction, path-vs-resolved-path denylist
  mismatch, hard link) were each re-traced against the current code and are closed as described.
  `_gates()`'s parse/lint/import/verify_math chain, `t_propose_patch`'s blast-radius accounting
  order, the `_tool_message` envelope-shrink loop (including its `keep<=1` terminal case), and
  `_achievement()`'s four-armed "did this run actually do anything" logic all check out against
  their own docstrings' worked examples.
- `binding_health.py`: `quarantine()`/`release()`'s compare-and-swap (digest-before-read
  ordering), `_spread()`'s "distinct by construction while n > want" claim, the three-valued
  `verdict()` truth table (`ok_absent is None` handled before every other branch), and
  `binding_verdict()`'s tie-break-by-measurement logic were hand-traced against sample inputs
  and hold.
- `completeness.py`: `work()`'s no-denominator / genuine-absence / existing-but-zero three-way
  split (`sizes`/`failed`/`no_denominator`), `land()`'s three write-loss guards (shrink floor,
  denied rename, filtered-run exemption), and the shared-host primary/borrower logic were traced
  and are correct.
- `secondopinion.py`: `ran_clean()` can never be vacuously true (`run()` always populates the
  three fixed tool keys); `_ruff`/`_vulture`/`_detect_secrets`'s returncode-vs-stdout handling
  matches each tool's documented exit-code contract; `NOT_FILED`'s waiver list was spot-checked
  against `RUFF_RULES` and every entry selects a rule the ruleset actually enables.
- `canon_backup.py`: `snapshot()`'s read-back verification (archive re-opened, every member
  re-hashed against the pre-write digest) and `verify()`'s archive-vs-manifest-vs-live three-way
  comparison (including the `unreadable`-is-not-`changed` split) are sound. `prune()`'s `for f in
  snaps[:-keep] if keep > 0 else []` still silently no-ops on `--keep 0`/negative — this is the
  same QUESTION sweep61 batch16 already recorded (not exploitable; argparse default is 7; not
  re-filed here).
- `pick_model.py`: `family_tier()`'s substring-match ordering (longer/more-specific family
  strings before their prefixes) was checked against every FAMILY_TIERS entry and is correctly
  ordered; `save_config()`'s atomic replace-with-denial-check and `resident()`/`fit_note()`'s
  documented total-vs-free budget split are otherwise sound apart from the one finding above.
- `catalogue_models.py`: the `LISTED`/`EMPTY_LIST`/`UNREACHABLE`/`UNCONFIGURED` four-outcome
  model is exhaustively handled at every read site (`live`, `verified`, `unverified`, `stale`),
  matching sweep61 batch15's own conclusion; re-checked against the current code and still holds.
- `entity_match.py`: `qualifier_compatible()`'s absolute (never score-overruled) gate,
  `similarity()`'s difflib-vs-Dice max, and the `STRONG`/`WEAK` raised-at-import ordering check
  were traced; `candidates()`'s two early-exit shapes now both return `dict` (not the historical
  list/dict mismatch sweep61 batch14 already closed) and were confirmed unchanged.

## Questions (carried forward from sweep61, not re-argued, still open)

1. `local_agent.py:892-894` (unchanged line content from sweep61 batch16's citation) — the audit
   log entry still truncates `why`/`find`/`replace` to `[:200]` each with no "+N chars" marker.
   Sweep61 marked this SUSPECTED-not-VERIFIED because nothing parses those fields
   programmatically; still true on this read. Not re-filed.
2. `canon_backup.py:274`, `prune()`'s `--keep 0` no-op (see above) — still undocumented, still
   not exploitable under the current default. Not re-filed.

No tautologies, no new fail-open guards, no Hard Rule 0 cap violations, and no false
comments/docstrings were found in this batch beyond what is already recorded in sweep61.
