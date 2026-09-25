# sweep61 batch 08 — audit report

Scope (every line read, start to finish, in this run):

- src/cascade_bridge.py    2333 lines
- src/sweep_plan.py        1150 lines
- src/rosetta.py            815 lines
- src/runguard.py           660 lines
- src/catalogue_codex.py    515 lines
- src/hosts.py              424 lines
- src/resync_roll.py        332 lines
- src/audit.py              275 lines
- src/compress_store.py     149 lines

Total 6,653 lines, all 9 modules read in full (no sampling).

## Summary

No VERIFIED defects found in this batch. All nine modules are already heavily hardened by
many prior sweeps (comments cite sweep42/43/59/60 batches and dozens of named orders), and
every mechanism I checked closely — compare-and-swap writers, fail-open/fail-closed guards,
Hard Rule 0 compliance (uncapped listings), classifier word-boundary regexes, thread-local
attribution, and the runguard ownership invariant — already has a written rationale and, in
most cases, a documented incident that motivated it. I looked for cases where a documented
fix was incomplete or where a "deliberate design" comment didn't match the code beside it,
and did not find one.

Findings by kind:
- Tautologies / checks that cannot fail: 0 new (one pre-existing, already self-documented as
  intentionally-unreachable-by-design: `hosts.py:discover()`'s `if not res: continue` — `work()`
  always returns a 3-tuple, which is always truthy; the file's own comment says this is kept
  loud on purpose rather than deleted).
- Fail-open guards: 0 new (runguard.py's corrupt-guard fail-open is deliberate, owner-ruled
  2026-09-08, and is announced via escalation + stderr, not silent).
- Caps/truncations (Hard Rule 0): 0 found. Every listing I checked in this batch (audit.py's
  BACKSCAN report, rosetta.py's --probe/--refine/--mine reports, resync_roll.py's changed/
  relabelled/unreadable/unmatched lists, sweep_plan.py's --missing/--check-briefs output,
  cascade_bridge.py's selftest() provider list) is explicitly uncapped, several with comments
  citing the specific order that removed a prior cap.
- Real bugs (wrong branch, off-by-one, unhandled crash, race): 0 found.
- False comments/docstrings beside the code: 0 found.
- Dead code: 0 new. `catalogue_codex.py`'s `slug()` is already flagged dead-but-kept in its own
  docstring (order c158b93e2e07); `sweep_plan.py`'s `coverage_map()` is already flagged dead-but-
  kept (order d411f780d347). Not re-reported as new findings.

## Verification method

Read every module top to bottom via the Read tool (no grep-sampling). For the handful of
places that looked initially suspicious I traced callers/definitions to confirm intended
behavior rather than assuming from a local read:
- `runguard.py` main()'s `--claim/--beat/--release` mutual-exclusivity (only one action fires
  if several flags are passed) — matches the documented CLI contract, not a defect.
- `sweep_plan.py` main()'s `if a.batches: ... elif a.check_briefs:` — `--batches` takes priority
  over `--check-briefs` if both are passed; this is ordinary argparse-without-mutex-group
  behavior consistent with the rest of the file's CLI, not a data-loss bug.
- `cascade_bridge.py` `_ask_call`'s widen-fallback claim loop (`for _ in range(4 if pin is None
  else 0)`) and the `if pinned:` guards after the single non-None exit point — confirmed via the
  file's own "INVARIANT, STATED ONCE" comment (order 8b0338b019ce) that these are documentation
  of which branches touch `pinned`, not live reachability conditions.
- `rosetta.py` `numeric_rows()`'s median-based outlier filter — confirmed this is a data-
  cleaning step for the Spearman rank-correlation input, not a report a person reads, so it is
  not a Hard-Rule-0 violation (that rule targets listings a human reads, not a statistical
  input filter) — and it is already commented as deliberate.

No code was modified, restarted, or executed except read-only `python -c` introspection was
not needed; all verification was by reading source and tracing call graphs.
