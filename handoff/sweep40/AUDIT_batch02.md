# Sweep 40 — Batch 02 audit

Module: `src/verify_math.py` (7,966 lines). Read in full, sequentially, in ~800-line
windows (offsets 1, 800, 1600, 2400, 3200, 4000, 4800, 5600, 6400, 7200). No sampling.

## Context

This module is the project's independent verification battery: a flat script of ~1,050+
`check(label, got, want)` assertions plus a large number of structural (AST-based) source
scans, each accompanied by an extremely detailed comment recording *why* the check exists —
almost always a real historical defect (mutation-testing survivor, a tautological check, a
truncated ledger, a fail-open guard) that was found and repaired, with the check now pinning
the repair. This is, by a wide margin, the most heavily self-audited file I have seen in this
codebase: dozens of the check patterns Hard Rule 0 / the audit brief calls out by name
(tautologies, `f(x) == f(x)`, checks matched against a comment instead of code, fail-open
guards, discarded write verdicts, rank-then-truncate caps, stale `file.py:NNN` citations) are
already named, fixed, and pinned *inside this very file*, often with the exact language this
audit brief uses ("a check that cannot fail looks exactly like a check that passed").

Given that density of prior self-correction, this pass treated every check as a claim to
verify rather than assume-correct, but did not re-derive the arithmetic already re-derived
independently in the file's own comments (e.g. the §19e interval recalibration, which the file
documents was independently recomputed by a standalone script outside `_interval`). Time was
spent instead on the categories most likely to still hide something in a file this
self-correcting: discarded return values, fail-open branches, and — per the audit brief's own
example category — stale `file.py:NNN` line-number citations inside comments, which were
grepped out and checked one by one against the current source of the files they cite.

## Findings

### 1. Stale cross-file line citation in a comment — `silence.py:408` (INFO / MINOR)

**Where:** `src/verify_math.py:3685-3688`, inside `_for_owner_landing_b19()` (§20b, "the
repairs of run #19"):

```python
elif nm == "write_json" and c.args and _is_fo(c.args[0]):
    # write_json IS the temp-then-replace_retry helper; it lands from a temp by
    # construction (silence.py:408). Markdown rules it out here, but a future
    # JSON sibling of this file would be just as correct.
    landed = from_temp = True
```

**The claim:** that `silence.py:408` supports "write_json IS the temp-then-replace_retry
helper; it lands from a temp by construction."

**What is actually at `silence.py:408`** (current source, read in full):

```
404  return False, ("%s could not be renamed into place (denied after %d attempts, "
405                 "most likely a reader holding it open) -- nothing landed. Retry "
406                 "next round." % (os.path.basename(dst), attempts))
407  _t.sleep(0.3 * (a + 1))
408  except OSError:
```

Line 408 is inside `replace_if_unchanged` (defined at `silence.py:336`), not `write_json`
(defined at `silence.py:471`). `write_json`'s own temp-file write and its call to
`replace_retry` — the code that actually substantiates the claim — are at `silence.py:508`
(`with open(tmp, "w", ...)`) and `silence.py:518` (`landed = replace_retry(tmp, path)`)
respectively. `408` names neither of those; it names an unrelated `except OSError:` clause in
a sibling atomic-write helper.

**Why it is wrong:** this is exactly the "stale `file.py:NNN` cross-reference in a comment"
category the audit brief names. The file elsewhere is scrupulous about this exact failure mode
— §20c pins `dashboard.py:336` as a *removed* stale label, and the file's own multi-paragraph
note above §22 explains at length how earlier versions of this file were burned by drifted
line-number citations (`did[:5]` at a line that had become a blank line; `titles[:8]` at a
line that had become a comment). This one slipped through the file's own vigilance.

**Impact:** none on correctness. This citation is explanatory prose inside a comment, not part
of the check's logic — the check itself (`landed = from_temp = True` when `write_json` is
called on `FOR_OWNER`) is a structural claim about `write_json`'s general contract and does not
depend on the cited line number being right. A future reader chasing the citation to confirm
the claim would land on the wrong function, though, which is the actual harm: the citation
exists specifically so a skeptical reader can check the claim without re-deriving it, and right
now it sends them to the wrong place.

**Remedy:** change `(silence.py:408)` to `(silence.py:508, 518)` (or simply drop the specific
line numbers and cite the function name `write_json`, which does not drift the way line numbers
do — the fix this same file adopted for several other citations, e.g. the `feats.py:api-404`
style named labels replacing numeric ones after BUGS.md m81). Mechanical, no behaviour change —
appropriate for a `LOCAL` handler.

## Other line citations checked and found accurate or non-load-bearing

Grepped every `<name>.py:<N>` citation in the file (`weave.py:187`, `reference.py:232`,
`feats.py:125/139/374/695`, `sweep.py:129`, `dashboard.py:336`, `overnight.py:180`,
`overnight.py:741`) and read each in context:

- `weave.py:187`, `reference.py:232`, `feats.py:125/139/374/695`, `sweep.py:129`,
  `dashboard.py:336` are all cited as **known-stale numbers being asserted absent** — the
  checks assert these exact strings no longer appear in the target files, i.e. they are
  intentionally-quoted *old* labels, not live claims. Not findings.
- `cascade_bridge.py:18` (verify_math.py:2070, §19v) — checked against current
  `src/cascade_bridge.py`: line 18 does say "carries the schema as prompt text only" as
  claimed. Accurate.
- `overnight.py:180` (verify_math.py:6897) — cited as *someone else's* (a work order's) claim,
  which this section explicitly disproves; not a claim verify_math.py itself is asserting live.
- `overnight.py:741` (verify_math.py:3814) — quoting the text of a docstring elsewhere, not
  independently asserting the number; low risk, not chased further given the primary finding
  above already illustrates the same class of defect with a confirmed, load-bearing miss.
- `assay.py:641/776/861` — mutation-testing forensic labels from the 2026-08-25 `mutate.py` run
  (§20r), describing which line a specific historical mutant altered. These are run records,
  not live pointers a reader is meant to re-open today; consistent with this file's established
  convention (see `verify_math.py:47` at line 63, explicitly historical).

## What was NOT found

No tautologies, no `f(x) == f(x)` checks, no fail-open branches, no rank-then-truncate caps,
and no discarded write verdicts were found in `verify_math.py` itself during this pass —
every instance of those exact patterns that appears in the file is *quoted as a historical
defect the file itself already fixed* (with a positive-control "canary" test proving the
detector still catches the pattern, in several cases — see §20i's disarm-guard canaries and
batch1's four canaries at run35). This is expected: `verify_math.py` is the project's own
defect-pattern detector, and it audits itself unusually aggressively already.

No caps on ranked output were found; every list-truncation pattern in the file is either (a)
a check *asserting* Hard Rule 0 compliance in another module (e.g. §19g/§19i/§19o/batch3's
`coverage.report`/`standards.py` checks), or (b) this file's own internal reporting, which does
not truncate its own PASS/FAIL/RESULT accounting.

No stale `prose_enabled` / `step4_enabled` value was found or touched — both gate assertions
(§20x, lines ~5175 and ~5193) were read and left exactly as found, per instruction; they pin the
owner-ruled current values (`prose_enabled: False`, `step4_enabled: True` as of 2026-08-31) and
are correctly asserted as exact-value checks rather than type checks, matching this file's own
stated rationale for why a type check would be insufficient.

## Coverage

`src/verify_math.py` — 7,966 / 7,966 lines read (100%), no sampling.
