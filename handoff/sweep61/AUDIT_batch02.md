# sweep61 batch 02 — AUDIT

Scope: `src/verify_math.py` (13,358 lines). Read sequentially start to finish in ~900-1000 line
chunks, all of it, no sampling. This is the project's arithmetic/invariant regression battery.

## Summary

No VERIFIED new findings. This file is, by a wide margin, the most heavily self-audited module
in the repository: it carries its own multi-year history of tautology repairs (order
96c4be60fb92 and many others), fail-open-guard repairs, and Hard-Rule-0 truncation repairs,
each documented in-line with the incident that found it, the date, and a regression check that
pins the fix. Roughly 40% of the file's bulk is prose recording *why* a given check is shaped
the way it is, specifically to stop the next reader (or the next maintenance sweep) from
"fixing" it back into a vacuous form. Sections 20i, 20j, 20p, 20q, 20t, 20u, 20y, 20z, and 20ae
are themselves meta-batteries whose entire purpose is finding rows in this same file that
"cannot fail" (tautologies, f(x)==f(x) comparisons, comparisons against a hand-copied literal
instead of the real source of truth, discarded `tol=`, prose-backed assertions, disarmed
`or True` rows, narrow/wide drill stand-ins, etc.) — and each carries positive AND negative
controls proving the detector itself still works.

I specifically hunted for the classes named in the brief:

1. **Tautologies / f(x)==f(x) / literal `check(label, True, True)` rows.** Grepped the whole
   file for the literal shape `check("...", True, True` — the only two hits are inside fixture
   strings / historical-comment text (lines 6496 and ~11180), not live rows. AST-swept for
   `check(label, X, X)` self-comparisons (identical expression in both `got` and `want`
   positions) — zero hits. The file itself documents at least four instances of this class
   already found and fixed (orders 3f86c571da58, fbdb7fe3bd4c, cc500a6cbf4b, 96c4be60fb92) —
   none of the fixed instances have regressed.

2. **Discarded `tol=`** (want silently not a float, so `check()` falls through to exact
   equality despite the caller believing a tolerance applies). The file's own §20z scan
   (`_discarded_tol20z`) only proves `want` isn't int-valued; I additionally AST-swept for
   `check(..., tol=...)` calls whose `want` is a tuple/list/dict (a case that scan does not
   cover and that would exhibit the identical silent-tol-discard bug). Zero such calls exist in
   the file today (verified: 80 total `tol=` rows, 0 non-float-shaped).

3. **Fail-open guards.** All `except ImportError: pass` / bare-`except: pass` shapes I found are
   either (a) already covered by the §20p `_interlock20p` AST scan (which demands a `raise`
   inside every escalation-import guard's handler), or (b) explicitly labelled
   `silence-exempt:` with a named reason and a `silence.note(...)` site, per the file's own
   swallow-exemption doctrine. No bare, undocumented `except: pass` found.

4. **Hard Rule 0 (rank-then-truncate).** The file's own tests for OTHER modules' Hard-Rule-0
   violations (backfill.py, coverage.py, standards.py, scope.py, entity_match.py, feats.py) are
   thorough and, on inspection, correctly assert against a fixture engineered to overrun the old
   cap. The one `[:N]` inside this file itself (`PR.build_all(limit=400)` at §14) is explicitly
   labelled "A SAMPLE, and labelled as one" for test speed, not a production listing — not a
   Hard Rule 0 violation.

5. **Comments/docstrings stating something false about adjacent code.** None found. Every
   "KNOWN DEFECT" comment (e.g. "the Instrument has NO resolution above M4" at §12, "M5 caps the
   window but earns no Transcendence Grade") is pinned as a *reproduction* of a real, named,
   charter-owned open question, not a false claim.

6. **Dead code.** None observed introduced by this file (it is a script, not a library); the
   file's own §20r/owner-ruling passages document three MARK-AND-KEEP retained-dead functions in
   `assay.py` (not this file) per an explicit owner ruling — out of scope for this batch.

## Notes on rigor observed, not findings

- The file's `check()` harness itself is unusually defended: it survives a row raising mid-run
  (atexit verdict printer), survives a non-numeric `got` against a float `want` without taking
  the whole suite down, and its own disarm-detector (`or True` suffixes) is driven by both
  positive and negative controls at §20i.
- Every negative AST/regex scan in the file (the ones asserting `== []`) is paired with a
  "the scan is looking at a real population, not nothing" row and/or a `[control]` row proving
  the detector can still catch a planted violation — this is the exact ratchet the brief's
  priority list is checking for, and it is already built in at scale (order 873330d2e98d and
  its many descendants).

## Verdict

Findings by kind: **0 VERIFIED, 0 SUSPECTED.** No tautologies, fail-open guards, hidden
truncations, real bugs, false comments, or newly-introduced dead code were found on a full,
sequential, unsampled read of all 13,358 lines. The module's own extensive internal audit
apparatus (which duplicates much of this sweep's stated purpose) appears to be functioning and
current as of the last reconciliation pass referenced in-file (2026-09-13, order 16bf1ff4df09).
