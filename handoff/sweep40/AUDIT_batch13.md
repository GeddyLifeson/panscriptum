# Sweep40 batch13 audit

Modules read in full: `src/read.py` (1384 lines), `src/rigor.py` (956 lines),
`src/identity.py` (700 lines), `src/estate.py` (543 lines), `src/address.py` (419 lines),
`src/sweep.py` (344 lines), `src/coverage.py` (300 lines), `src/suppressions.py` (242 lines).

Overall verdict: this is another extremely well-hardened batch. `read.py`, `rigor.py`,
`identity.py`, `estate.py`, `coverage.py` and `suppressions.py` all show the mature pattern seen
in prior sweep30-39 batches -- every silent-truncation, fail-open, and RMW hazard I probed for is
already named, fixed, and explained at length in the module's own comments (Hard Rule 0
compliance is genuine throughout: `read.py`'s chunk-caching, `coverage.py`'s CITED/READ/NO
PAGE/NOT ATTEMPTED precedence, `identity.py`'s staleness-as-floor banner, `suppressions.py`'s
stored-vs-displayed truncation split, `estate.py`'s per-row severity grading). `sweep.py`'s
`nested_run()`/funnel logic and `rigor.py`'s math (Bradley-Terry Ford's-condition refusal,
MDL floors, Jensen-gap integration) were checked by hand and are internally consistent.

Live cross-reference audit: every `file.py:NNN` citation still embedded as a *current* claim
(`read.py:213-215` self-reference, `address.py:234` -> `manifest_builder.py:247`,
`address.py:226` -> `catalogue_web.py:68-95`) was checked against the cited line and is accurate.
Every other `file.py:NNN` string in these eight files is itself *narrating a past stale citation
that was already replaced with a symbol/order-id citation* (`rigor.py`'s `tempus.py:182-186`,
`identity.py`'s `chain.py:381`, `coverage.py`'s `foreman.py:324`) -- those are not live claims and
are not findings.

One real, live, verified defect was found, in `address.py`. It matches an already-known BUGS.md
entry (**M44**, logged "OPEN, VERIFIED run #32") that had not yet been turned into a
`workorders.json` entry, so it is filed here for the first time as a work order.

---

## Finding 1 (MAJOR) -- `address.spine_code_for()` still invents an address for an unrelated
crossover title, via the "opens/closes the title" exception to its own most-specific-match rule

**Where:** `src/address.py:151-169` (function `_index_name_is_placed_like_a_title`, and the
"most specific wins" loop in `spine_code_for`)

```python
150   # return UNASSIGNED, which is the safe answer this fallback exists to give.
151    def _index_name_is_placed_like_a_title(w_name, w_target):
152        """The index entry sits inside the target: is it there as the title, or as vocabulary?"""
153        if len(w_name.split()) > 1:
154            return True
155        return w_target.startswith(w_name.rstrip() + " ") or w_target.endswith(" " + w_name.lstrip())
156
157    w_target = _worded(source_name)
158    if w_target.strip():
159        best_code, best_evidence = None, 0
160        for name, code in codes.items():
161            w_name = _worded(name)
162            if w_name in w_target and not _index_name_is_placed_like_a_title(w_name, w_target):
163                continue
164            if w_target in w_name or w_name in w_target:
165                evidence = min(len(w_target), len(w_name))
166                if evidence > best_evidence:
167                    best_code, best_evidence = code, evidence
168        if best_code is not None:
169            return best_code
```

**Why it is wrong.** The module's own docstring (lines ~52-58) states the contract plainly:
"Falls back to a flagged placeholder (never a guessed real code) if the source isn't in the
appendix yet ... Surface these to the owner for a real assignment rather than silently inventing
one." Hard Rule 2, which the file's own extensive comment history (three prior rounds of fixes
to this exact function, all documented in the surrounding comments) exists specifically to
enforce, forbids exactly this.

`_index_name_is_placed_like_a_title` was added to fix a narrower version of this same bug (a
single-token index entry matching anywhere inside a title). Its fix only checks whether the
index entry's word **opens or closes** the target string -- it does not check whether the
**rest of the target** is actually about that entry, or about something else entirely. So any
title that happens to begin or end with a catalogued single-token franchise name is treated as
"the work's own name with a qualifier attached" (the comment's own example: `'Halo (all games)'`)
even when the remaining words name two or three *other*, unrelated catalogued franchises.

**Live reproduction**, run against the current source and the real `data/CHARTER_SPINE_CODES.json`
(which maps the single token `"Alien"` -> `II.N`):

```
>>> address.spine_code_for('Alien Predator Doom Crossover')
'II.N'
>>> address.spine_code_for('Doom Marines vs Aliens Anthology')
'II.N.2'
>>> address.spine_code_for('Halo Fan Documentary About Nothing')
'II.F.4'
```

None of these three titles is genuinely a work belonging to the franchise it was shelved under
-- each is an invented crossover/anthology/documentary title that merely opens or closes with a
catalogued single-token name. All three should return `UNASSIGNED` (the module's own safe
answer) and be surfaced via `unassigned_sources.md` for owner sign-off, exactly as the
docstring promises. Instead each is silently given a real spine code with no marker, which:

1. Directly violates Hard Rule 2 ("never guess a real [code]"), inside the one function whose
   entire multi-round revision history is fixing exactly this class of bug.
2. Does the "second harm" the file's own comments repeatedly name for the prior three rounds of
   this bug: a source that matches WRONG never reaches `unassigned_sources.md`, so the owner
   review that would have caught it is never triggered.

This is a live defect, not a hypothetical: `BUGS.md` already records it as **M44 — OPEN,
VERIFIED run #32**, with the identical repro (`spine_code_for("Alien Predator Doom Crossover")
-> "II.N"`). I re-verified it against the current tree today (2026-08-31) and it is unchanged.
Checking `workorders.json`'s open orders found no entry for this specific finding -- the BUGS.md
ledger entry had not yet been carried into a work order, so it is filed now (Finding 1 below).

**Remedy.** The "opens/closes the title" exception needs a second condition: it should only
apply when nothing else meaningful survives on that side of the match (i.e. the qualifier is
generic filler like `all`, `edition`, `documentary`, `(all games)`), not merely "the word sits
at a boundary." A cheap version: after stripping the matched index name from one end of
`w_target`, check whether what remains contains any OTHER catalogued index name's token(s) as a
whole word; if so, this is evidence of multiple works being invoked (a crossover/anthology) and
the match must not win outright -- fall through to `UNASSIGNED` or require the token-overlap
fallback's stricter equal-token-set test instead. This preserves the genuine cases the docstring
cites (`'Halo (all games)'`, `'Pantheon: Norse'`) while refusing titles that name two or more
franchises.

---

## Notes (not filed, already covered by existing findings/design)

- `coverage.py:47-55` (`_p()`): confirmed dead (zero callers). This is the codebase's own
  documented, deliberately-preserved fixture for `liveness.py`'s dead-code detector (see
  `liveness.py:10`, `drill.py:5296`, and multiple prior sweep audits back to sweep34). Not a new
  finding.
- `estate.py` has no `main()`/CLI entry point. Confirmed intentional: it is imported as a library
  by `allsweep.py:728` and `overwatch.py:412`, and nothing in the tree expects to run it
  standalone.
- `address.py:390-393` (`tier_rank` returning 0 for an unrecognised tier, same as `'volume'`):
  already filed and open as work order `2c8e55f8f3f7` (sweep39-batch13, MINOR, handler SESSION).
  Independently re-derived the same defect while reading `promote()`/`tier_rank()`; not re-filed.
