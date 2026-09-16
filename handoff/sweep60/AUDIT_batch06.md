# sweep60 batch06 — audit report

Modules read in full, uncapped, line by line (no sampling): `src/workorders.py` (2507),
`src/overwatch.py` (1124), `src/identity.py` (752), `src/endpoint.py` (654), `src/scope.py`
(473), `src/genre.py` (385), `src/resync_roll.py` (332), `src/ledger.py` (220),
`src/chord_field.py` (210). Total 6,657 lines, matches the assignment.

## Summary

These nine modules are exceptionally heavily self-audited already: nearly every risky pattern
(caps/truncation, fail-open exception handling, tautological "healthy" tests, silent
overwrites, lost-update races) carries its own multi-paragraph comment citing an order number,
a prior sweep, and a measurement of the damage before the fix. I read every one of those
comments against the code beside it rather than taking the comment's word for it, and in every
case I checked, the code matched what the comment claims (the `_fire(ok, ...)` polarity in
`workorders.sweep_detectors` was the one place I expected to find the fabled "inverted health
check" the file's own docstring describes finding once before — I checked all eleven call
sites and all eleven now pass the correct predicate).

I did not find a NEW instance of a check-that-cannot-fail, a fail-open guard, or a
contradicted docstring in this batch. I looked specifically for the classes the brief
prioritizes and I am reporting one low-confidence completeness gap (not a "cannot fail" bug)
and noting one cross-module dependency I verified by reading the other file rather than
assuming it holds.

**This batch is substantially clean.** That is itself notable given the file sizes, and I want
to be explicit that "clean" here means "no NEW defect found by manual line-by-line reading
against the stated priorities," not "provably bug-free."

## Findings

### 1. LOW / advisory-tool completeness gap — `workorders.py` `twins()`, lines ~1010–1029

```python
spans = {k: _span(k) for k in by_line}
overlap = {}
for k, s in spans.items():
    ids = set(by_line[k])
    if s is not None:
        for k2, s2 in spans.items():
            if k2 != k and s2 is not None and s2[0] == s[0] and s2[1] <= s[2] and s[1] <= s2[2]:
                ids.update(by_line[k2])
    overlap[k] = ids
```

The pairwise overlap test is not transitively closed. If citation A (`foo.py:100-110`)
overlaps B (`foo.py:105-120`), and B overlaps C (`foo.py:115-130`), but A and C do not
directly overlap each other, then `overlap["foo.py:100-110"]` will contain {A,B} and
`overlap["foo.py:115-130"]` will contain {B,C} — neither cluster shows all three orders as one
chain, even though B links them. A reader who opens A's cluster to find every order touching
that neighbourhood will not see C.

I verified this by tracing the loop directly (no transitive/union-find step follows it) rather
than by running it. Severity is low because `twins()` is explicitly documented as "CANDIDATES,
not a verdict" that a person is meant to read and cross-check against source, and the two
non-transitive views (A's cluster, C's cluster) are both still shown — nothing is hidden
outright, the grouping is just not maximal. I am flagging it because the module's own stated
purpose is exactly to stop a person from having to notice this kind of chained relationship by
hand, and a chain longer than two hops is the case this silently degrades. Not a Hard-Rule-0
truncation and not a tautological check — a genuine but minor algorithmic gap. Labelled unsure
on severity, not on the mechanics (the mechanics I traced and am confident about).

### 2. Verified NOT a bug — `ledger.py` `assay_to_standards`, lines 186–217 (cross-module check)

```python
from assay import BAND_EDGES, LADDER
if magnitude_band not in BAND_EDGES:
    return None
i = LADDER.index(magnitude_band)
```

This guards on membership in `BAND_EDGES` and then indexes into the separately-defined
`LADDER` list — if the two ever disagreed (a band in one but not the other), this would raise
an uncaught `ValueError` past the `None`-returning guard. `assay.py` is not one of my assigned
modules, so I read it anyway to check this specific cross-module assumption rather than leave
it as a guess: `src/assay.py:73-107` defines both, and their key sets are identical
(`M0`..`M10` in both, same order). So this is safe as the codebase stands today; recorded here
only because it is a latent coupling (an edit to one table without the other would reintroduce
exactly the failure class this audit is hunting for), not because it is currently broken.

## Not found (checked specifically, per the brief's priority list)

- **Tautological / cannot-fail checks**: traced every `all(...)` over a possibly-empty
  collection in these files (`workorders.py:555` is guarded by `targets and all(...)`, not
  vacuous); traced the `_fire(ok, ...)` polarity at all 11 `sweep_detectors()` call sites in
  `workorders.py` (this file's own docstring describes having shipped an inverted version of
  exactly this once — the current version is correct); traced `genre.py`'s `ranked[0][1] == 0`
  guard (real, not vacuous — `classify_text("")` always returns len(GENRES) entries, but they
  can genuinely all be zero, and that's the case being tested).
- **Fail-open guards**: every bare `except: pass` / `except Exception: pass` in this batch
  (`workorders.py:457,564,1244`; `overwatch.py:365`) leaves the surrounding operation in a
  fail-closed or no-op state (temp-file cleanup best-effort, "cannot tell, file as addressed but
  a post-hoc detector still catches it", stats default), not a state that grants permission or
  skips a safety check.
- **Caps/truncation on data that should be uncapped**: every `[:N]` slice I found is either (a)
  a display-only cut with an explicit "+N more" remainder shown to the reader, (b) a hash/id
  truncation (sha1/sha256 to N hex chars — a key, not data loss), or (c) explicitly marked dead
  legacy-cap-boundary detection code that exists specifically to catch a *reintroduced* cap.
  I did not find a live, uncommented truncation of substantive data.
- **Stale `file.py:NNN` citations**: none of the doc comments in these nine files cite a line
  number in *another* file that I could check against current content and find wrong (several
  explicitly moved to symbol-based citation for this exact reason, e.g. `identity.py`'s
  `epoch_of` docstring).
- **Dead/unreachable code**: several intentionally-dead symbols exist (`ledger.py`'s
  `STANDARD_GLYPH`, `CONDENSATES`, `currency_status`; `scope.py`'s `ceiling_for`;
  `overwatch.py`'s unreachable `_STATE_RANK` entries "stale"/"confirmed"; `identity.py`'s
  deleted `adjudicate`), but every one is explicitly marked dead-on-purpose with an owner-ruling
  citation ("mark and keep, delete nothing"), not silently orphaned.

## Coverage

Ran after this report was written:

```
cd C:\Users\imarl\panscriptum-library-kit
PYTHONIOENCODING=utf-8 C:/Users/imarl/miniconda3/python.exe -c "import sys; sys.path.insert(0,'src'); import sweep_plan; sweep_plan.record('sweep60', ['workorders.py','overwatch.py','identity.py','endpoint.py','scope.py','genre.py','resync_roll.py','ledger.py','chord_field.py'], batch=6)"
```
