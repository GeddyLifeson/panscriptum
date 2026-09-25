# sweep63 batch 02 — AUDIT

Scope: `src/verify_math.py` (13,368 lines). Read sequentially start to finish, in ~700-1000 line
chunks via the Read tool, no sampling. Every line was read; this is a full re-audit, not a diff
against sweep61.

Read-only throughout. No file under `src/`, `data/`, or `state/` was edited (the single
`sweep_plan.record()` call at the end, as instructed, is the only write). Nothing was run except
that one `python -c` invocation — no `verify_math.py`, `drill.py`, `mutate.py`, or `publish.py`
execution.

## Prior audit check

`handoff/sweep61/AUDIT_batch02.md` covered this exact module (same 13,358-line scope, off by 10
lines from today's 13,368 — the file has grown slightly since). Its verdict: "No VERIFIED new
findings. This file is, by a wide margin, the most heavily self-audited module in the
repository." I re-read the whole file from scratch rather than diffing against that conclusion,
per the brief's instruction not to trust a prior audit's self-report without verifying directly.

## Summary

**0 VERIFIED, 0 SUSPECTED findings.** My own full read reaches the same conclusion sweep61
batch02 reached: this module is unusually — almost oppressively — self-documented. A very large
fraction of its 13,368 lines is prose recording the exact history of a defect found in *this*
file: an order id, the date, the mutation or fixture that exposed it, and the corrected check,
plus (for nearly every negative scan) a positive-and-negative control pair proving the detector
itself can still fail. Sections 20i, 20j, 20p, 20q, 20t, 20u, 20y, 20z, and 20ae are themselves
meta-batteries whose entire purpose is finding exactly the shapes this brief's priority list asks
about (tautologies, `f(x)==f(x)` comparisons, `or True` disarms, fail-open guards on
`escalation.py`, narrow/wide drill stand-ins, discarded `tol=`, prose-backed assertions,
uncontrolled negative scans) — each carrying its own canary/control row. I checked each of these
documented fixes against the current code rather than re-reporting them, per the brief.

I specifically hunted the priority list against this read:

1. **Checks that cannot fail.** None found unrepaired. Every place I initially suspected a
   tautology (e.g. `covers_all_signatures`-style guarantee fields, the `_iv`/`_stamp` provenance
   assertions, the `_axis_refusal` blanket-refusal risk) turns out to carry the file's own
   "guarantee vs. datum" split (a declared field plus an independently re-derived assertion) or a
   `[control]` row proving the check is not vacuous. The `f(x) == f(x)` class (map_seed,
   `SF.build()`, `AS.assign()`, cache keys, burg seeds) is repaired everywhere via fresh
   `importlib`-loaded module copies and frozen cross-process pins — I did not find an unrepaired
   instance.

2. **Fail-open guards.** The `escalation.py` interlock scan (§20p, `_interlock20p`), the
   `escalation.clear()` no-caller scan (§20t), and the console-window/subprocess scan (§20e) are
   all AST-based, resolve import aliases, and carry their own canaries. No fail-open shape found
   outside what the file already names and has fixed.

3. **Caps/truncations (Hard Rule 0).** `_slices_of` (the `did[:N]` AST scanner used at §1, §22)
   and the various `--cap`/`extra=`/`show=` rows all assert refusal-by-default with a `[control]`
   proving the scanner isn't blind. No new truncation found.

4. **Real logic bugs.** Nothing found: no wrong-variable, off-by-one, unit-mix, or silent
   exception-swallow that isn't already named, dated, and pinned with a regression row (the
   `tol=` discard class at §1/§17/§20z, the `epoch or "unstamped"` vs `epoch and "unstamped"`
   mutant at §10, the M10 top-rung `9.9`-before-validation bug at §34, etc. are all closed with
   both a positive and negative control).

5. **prose_enabled / step4_enabled / halt-lifting.** Both flags are pinned to exact values with
   an explicit owner-ruling citation (2026-09-16 Phase 4.5 for `prose_enabled`, 2026-08-31 for
   `step4_enabled`); `escalation.clear()` is proven to have no caller in `src/` by AST, not grep;
   the nine/thirteen-module interlock roster is derived from the tree rather than hand-kept. No
   path found that could open either flag or lift a halt silently.

6. **Regex/escape corruption.** The file's own `_BAD_CHARS` self-check at line 17 guards against
   an eaten regex escape corrupting the file in transit; I found no corrupted escape or
   mis-scoped regex in the checks I read (the regex/AST scans throughout are the file's dominant
   idiom and are exercised by canaries as noted above).

Nothing here contradicts sweep61 batch02's conclusion. The ~10-line growth since that audit
(13,358 → 13,368) did not introduce anything new within this module that I could find.

## Findings

None (VERIFIED or SUSPECTED).

## Questions

None new. For the record, three items the file itself already flags as open and unresolved by
design (not defects, not re-reportable per the brief, but noted here since they are unresolved
design questions rather than closed findings):

- **M18** (§12, `assay.axis_score`): an in-range M10 quantity saturates at 9.9 rather than
  scaling continuously. Explicitly pinned as "open M18, untouched" — a `[control]` row exists
  specifically so a future fix to it fails loudly here rather than drifting silently.
- **Instrument resolution above M4** (§12): the Int/Wis/Cha window is fixed at `(30,30)` for
  M5+, so no faculty score differentiates a dullard from a genius above that band. Marked
  "KNOWN DEFECT, charter-owned; needs owner sign-off."
- **order 9736a5a73b02** (§16.batch6): `YEARS_PER_UNIT_DISTANCE`'s calibration against the
  propagation graph's true diameter is printed as an INFO line every run, explicitly "LEFT FOR
  OWNER... not an auto-fail."

None of these are new; all three are already tracked in the code with the owner named as the
decision-maker.

## Coverage note

Module read in full: `src/verify_math.py` only (per this batch's assignment — no other module
was read this session).
