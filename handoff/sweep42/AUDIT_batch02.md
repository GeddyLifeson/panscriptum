# sweep42 batch 2 — audit of src/verify_math.py

Read in full: all 9,281 lines of `src/verify_math.py`, in ~900-line passes, plus the repo
`CLAUDE.md` for house rules. No other file was edited.

## Summary

`verify_math.py` is not an ordinary module — it is the project's own regression battery, and it
is already extraordinarily self-audited: the file is full of first-person accounts of its own
past defects (tautological checks, swallowed exceptions, `[:N]` truncations, guards that never
ran) each followed by a fix, a regression check, and — for every negative scan — a positive
"canary" control proving the detector can still catch the thing it exists to catch. Sections
§18c, §19h-bis, §20i, §20p, §20t, §20y, §20z and the final three checks at end-of-file are
explicitly the file auditing *itself* for exactly the defect classes this sweep is asked to look
for (unfailable checks, tautologies, truncated diagnostics, disarmed assertions, stale line
citations, duplicate labels/section tags).

After a full read I found **no confirmed Hard-Rule-0 / swallowed-exception / unfailable-check
defect that the file's own self-audit has not already caught and fixed**. I checked specifically
for: bare `except:`, undocumented `except Exception` swallows (all 26 occurrences are either
test-fixture behavior being asserted, or wrapped with `_no_ledger_vm()`/`silence.note(...)` per
the file's own documented convention), oversized `tol=` values that would make a numeric check
unfalsifiable (largest is `tol=1.0` against a ~4.6e16 quantity, explicitly justified in a
comment), tautological `got`/`want` pairs, and stale self-referential line-number citations
(the two I found, `:337` and `:346`-ish, are historical prose describing a past fix, not live
pointers anything depends on).

## Confirmed defects

None found in this module.

## Questions (not defects — flagging for owner judgment per the "might be deliberate" rule)

### Q1 — Diagnostic FAIL-note strings are truncated with fixed `[:N]` slices

Examples: `verify_math.py:5390` (`str(r["observed"])[:60]`), `:8478` and `:8490`
(`str(_e36)[:200]` / `str(_row36)[:200]`), `:6217` region (`type(_e_sig).__name__` — not sliced,
fine), `:8091` region, and several more scattered through §20aa/§35–36.

CLAUDE.md's Hard Rule 0 states outright: "any place output is truncated (`[:N]` on a printed/
written string, a list sliced before printing...) is a FINDING." Read at the letter, these sites
qualify — they cap an exception message or an `observed` value to a fixed character count before
it goes into a `note=` field that only prints when the check FAILS, so a diagnostic longer than
the cap loses its tail exactly when a reader needs it most.

That said, this is almost certainly a different thing from what Hard Rule 0 is aimed at: the
rule's own worked examples (`roster(limit=600)`, `cap=250` on a missing-cast repair, `cap_chunks
=12`) are all about a **ranked list of real-world entities losing members**, not a
freeform exception string being previewed for terminal readability. This file is scrupulously
careful about the roster/entity-list version of this rule (§19g/§19i/§19o/§b3-1230/§b5 all pin
exactly that class), and the diagnostic-string truncation pattern is used consistently and
knowingly across dozens of sites by the same author, including inside the file's *own*
Hard-Rule-0 self-checks (`_disarmed_rows20i`, `_dup_labels20z`, etc.), which suggests it is a
deliberate, accepted convention rather than an oversight. Flagging as a question rather than a
fix per the instructions: is diagnostic-message elision in a `note=` field understood to be
exempt from Hard Rule 0, or should these also print the full text?

Confidence: low that this is an actual defect; noted because it is the one place the file's own
practice appears to brush against the literal wording of its strictest rule.

### Q2 — Many `open(path, encoding=...).read()` calls have no `with` block

Dozens of sites (e.g. `verify_math.py:1041-1044`, `:4739-4740`, and throughout every section that
reads a sibling module's source for a text/AST scan) open a file inline without a context manager
or explicit `.close()`. In a long-lived process this would be a real handle leak; in this
particular script (a flat, single-process, exits-when-done battery) it is very unlikely to matter
in practice, and it is completely consistent throughout the file — never mixed with `with` for
the same kind of read — which reads as a deliberate style choice for a script this dense with
one-liner source-scans, not a defect. Flagging only because it stands out against the file's
otherwise very disciplined resource hygiene elsewhere (the `_mkdtemp_vm`/`atexit` sweep at §18c,
the careful `finally:`-based restores throughout).

Confidence: very low; almost certainly intentional/harmless for this use case.

## Coverage note

`sweep_plan.record('run42', ['verify_math.py'], batch=2)` was run after this file was written (see
parent turn) to record coverage.
