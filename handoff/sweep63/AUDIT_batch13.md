# sweep63 batch 13 — audit

Auditor scope, read in full, start to finish, in chunks (line counts from `wc -l` at time of
reading):

- `src/assay.py` (1949 lines) — SAFETY-CRITICAL (Hard Rule 3, the Assay scoring)
- `src/silence.py` (1313 lines)
- `src/onomast.py` (844 lines)
- `src/thread_integrity.py` (721 lines)
- `src/anchors.py` (576 lines)
- `src/citecheck.py` (455 lines)
- `src/cosmography.py` (375 lines)
- `src/physics.py` (312 lines)

Total 6,545 lines across 8 modules, all read in full, no sampling. Read-only: nothing under
src/, data/ or state/ was edited, and nothing was run except the final `sweep_plan.record` call.

## Prior-audit cross-check (per instructions, so resolved items are not re-filed)

CLAUDE.md read first (doctrine skim). `handoff/sweep61/` grepped for each of this batch's eight
module names before reading; overlapping prior audits read in full:

- `AUDIT_batch13.md` (sweep61) — same batch number, different module set (assay.py, silence.py,
  scout.py, custodes.py, policy.py, render.py, grounding.py, resonance.py). assay.py and
  silence.py were both already read in full there with no module-specific findings filed against
  either (the one finding that run was in scout.py, out of this batch's scope). Its "Questions"
  section flagged one item relevant here (see below).
- `AUDIT_batch11.md` (sweep61) — covered onomast.py and anchors.py in full; no findings against
  either beyond documented/handled shapes.
- `AUDIT_batch14.md` (sweep61) — covered thread_integrity.py, citecheck.py and cosmography.py in
  full; findings were in hostcheck.py/liveness.py (out of this batch's scope), and this batch's
  three modules were explicitly listed as checked-and-sound (`classify()`'s dedup, the
  DANGLING/PARTIALLY-DANGLING split, `_floor_verdict`'s ratchet-only-down logic for
  thread_integrity.py; `_classify`, `_mention_kind`, `_in_tree_lead` for citecheck.py;
  `GALAXIES_CONSELICE_2016`/`STARS_MILKY_WAY` dead-reference claims and `validate()`'s Kardashev
  ceilings verified for cosmography.py).
- `AUDIT_batch10.md` (sweep61) — covered physics.py in full; no findings against it.

**One open question from sweep61 batch15 is resolved by this read, not merely re-confirmed.**
That audit flagged, as a QUESTION rather than a finding (it had not read assay.py): whether
`tempus.band_resolution()`'s `LADDER.index(band)` call — guarded by `band not in BAND_EDGES` but
not explicitly by `band not in LADDER` — could raise uncaught if `BAND_EDGES` and `LADDER` ever
had different keysets. Having now read `assay.py` in full: `_check_constants()` (assay.py:849-859)
asserts, at import time, that `BAND_EDGES` and `LADDER` carry exactly the same rungs (`_off_ladder`
and `_no_edges` checks, both `AssayIntegrityError` on mismatch), and this function runs
unconditionally at module load (assay.py:1949, the last line of the file). So the two tables are
guaranteed to share a keyset by construction for any process that has successfully imported
`assay`, and `tempus.py`'s guard is sound. Not a live gap.

## General finding

This is, again, the most heavily self-audited part of this codebase — consistent with every prior
sweep of these or adjacent modules. Nearly every constant table, validation gate, interval
formula and edge case carries its own paragraph naming the exact defect it fixes, the order id,
and how it was measured (frequently against reproduced before/after numbers). `assay.py` in
particular — the safety-critical scoring engine — has four independent, documented safety nets
(Layer 1 input validation across all three public entry points, `_check_constants()` at import,
`calibration_report()`'s re-derivation against the charter's own published Kenshiro number, and
drill.py's attacks), and reading it end to end did not surface a live gap in any of them.

No checks-that-cannot-fail, no fail-open guards, and no live Hard-Rule-0 caps/truncations of a
roster, chunk list or entry list were found in any of the eight modules. One low-severity,
cosmetic SUSPECTED finding is filed below because it matches this project's own established
"unmarked truncation" bug shape, even though its practical exposure is minimal.

## Findings

### 1. SUSPECTED, low severity — `citecheck.py:397`, `report()`'s printed citing-line text is
silently truncated at 160 characters with no "+N chars" marker

```python
out.append("  :%-5d  %-12s -> %s:%d" % (f["line"], f["reason"], f["cites"], f["cited_line"]))
out.append("           %s" % f["text"][:160])
```

This is the exact shape this codebase has repeatedly treated as a real Hard Rule 0 defect
elsewhere (e.g. `onomast.py`'s "PAD, DO NOT CUT" fix for the attestation column, order
478dea657aaf; `silence.py`'s removal of `str(detail)[:60]` in `swallow.__init__`, order
e1c3aebfedd4; sweep61 batch16's QUESTION about `local_agent.py`'s `[:200]` audit-trail
truncation): a display field cut with no marker that anything was cut.

**Mitigating factors, which is why this is filed as low severity rather than a priority
finding.** `stale_citations()`/`citations_in_text()` (the actual data the audit computes) return
the full, untruncated `text` field in every finding dict; `main()`'s `--json` path emits that
list verbatim with no truncation at all. The `[:160]` only affects the human-readable console
`report()` rendering, and 160 characters is well past the length of an ordinary Python source
line, so in practice a citing line long enough to be cut here would already be a style outlier.
No data is lost from the record this module publishes — only from one of its two presentation
paths.

**Suggested fix**, consistent with the project's own established remedy for this shape: either
drop the slice (the JSON path already prints it whole, so nothing structural stops the text path
from doing the same) or keep a cap but print `text[:160] + (" …+%d chars" % (len(text) - 160) if
len(text) > 160 else "")`, matching the "+N more" convention used throughout `citecheck.main()`'s
own sibling summary lines and the rest of this codebase.

## Questions (not findings — flagged for a human, not filed as work)

None new. The one live open question touching this batch (tempus.py vs `assay.BAND_EDGES`/
`LADDER`) is resolved above, not merely re-recorded.

## Summary of findings by kind

- Checks that cannot fail: 0
- Fail-open guards: 0
- Caps/truncations hiding roster/entry-list data (Hard Rule 0): 0 live; 1 SUSPECTED cosmetic
  display truncation with no data-loss consequence (citecheck.py, above)
- Real logic bugs (wrong variable, off-by-one, unit mix, unguarded races, resource leaks,
  exception paths that corrupt state): 0
- Anything that could open `prose_enabled`/`step4_enabled` or lift a halt: 0 — none of these eight
  modules touch either gate or `escalation.clear()`
- Regex/escape corruption: 0 (all eight modules carry and pass their own `_BAD_CHARS` guard)

## Coverage

Recorded via `sweep_plan.record('run63', ['assay.py', 'silence.py', 'onomast.py',
'thread_integrity.py', 'anchors.py', 'citecheck.py', 'cosmography.py', 'physics.py'], batch=13)`.
