# run35, LOCAL batch L5 -- audit

Owned files this batch: src/pipeline.py, src/sweep.py, src/allsweep.py, src/rosetta.py,
src/coverage.py, src/standards.py, src/tuning.py, src/lognames.py, src/scope.py. Did not run
verify_math.py, drill.py or mutate.py (mutation run in flight); did not start pipeline/sweep
jobs. Every fix below was verified with `pyflakes` plus a bare `import`, and where practical
with a standalone probe reproducing the logic under test (shown inline in each order's --how).

## 273e6cb65d57 -- pipeline.py, `_SCALE_PATTERNS`/`_SCALE_EVIDENCE` dead code (FIXED)

Verified: grep across src/ finds no reader of either name beyond their own definitions at
pipeline.py:1157-1158, and `valid_scale_note()` demonstrably uses the conjunction (`_MAGNITUDE`
OR (`_act_upon_object` AND NOT `_PATIENT` AND NOT unexplained `_REPUTATION`)) that the 15-line
comment two lines above this block explicitly says replaced an OR-of-everything gate. The
defect is real: an unused OR-of-three-patterns sitting right next to the explanation of why OR
was rejected reads as a live alternative implementation, not as inert code. Per this project's
"dead code is not automatically deletable" rule it was not removed. Instead the comment above it
now states plainly that nothing reads it and that it is the shape of the REJECTED approach, so a
future reader (or a local model) cannot mistake "kept for reference" for "safe to wire back in."

## 2b4d552df6f0 -- sweep.py, `report()` ZeroDivisionError on empty rows (FIXED)

Verified: `n = len(rows)` at sweep.py:177, and three unguarded `f[k]/n` (`.../n`) divisions on
what were lines 196/199/201, on the same lines whose bar computation two tokens earlier already
guards with `max(n, 1)`. `report([])` raised `ZeroDivisionError` before the fix; confirmed with
a standalone call. Changed all three sites to divide by `max(n, 1)`, matching the guard already
present in the same function. `report([])` now prints an all-zero funnel and returns a dict of
zeros, exercised in `checks_L5.py`.

## 322cc5ab6f31 -- overwatch.py, stale `silence.note` line tags (LEFT -- not my file)

Verified the finding is accurate: `structure()`'s import/reconcile handler tags
`silence.note("overwatch.py:193")` at (current) line 331, and the estate handler tags
`silence.note("overwatch.py:202")` at line 341 -- both stale numeric tags pointing at unrelated
code (`os.makedirs` in `save()`, `silence.replace_retry` respectively) rather than themselves.
overwatch.py is not in this agent's owned-file list (pipeline.py, sweep.py, allsweep.py,
rosetta.py, coverage.py, standards.py, tuning.py, lognames.py, scope.py) and is not among the
files I'm permitted to edit. Left open for whichever agent owns overwatch.py.

## 4e93de4ab854 -- allsweep.py, `NEVER_RUN` dead constant (FIXED)

Verified: `grep -rn NEVER_RUN src/` returns only its own definition (allsweep.py, now ~line 74);
the actual invocation restriction is structural -- `check_import()` only ever runs a module with
`--help`, and `run_verifier()` only ever iterates the separate, explicit `VERIFIERS` list. The
30-name set is read by nothing, and its comment ("Naming them here beats guessing from a flag")
reads as if the set itself were the guard. Not deleted, per the no-delete-dead-code rule.
Rewrote the comment to say outright that nothing reads `NEVER_RUN` and to name the two real
gates, so it can't be mistaken for live enforcement.

## 5faa6da447e1 -- cleanup.py, eaten-escape guard misses `_MARKUP` / carries dead `_SETTING_META` entry (LEFT -- not my file)

Verified the finding: the guard tuple at cleanup.py:89-92 iterates `(("_NAV", _NAV),
("_EMPTY_MECHANIC", _EMPTY_MECHANIC), ("_SETTING_META", None))`; the `None` entry is inert
because of `if _p is not None`, and `_SETTING_META` is not defined anywhere in cleanup.py (it
lives in pipeline.py:1094, a different module's namespace entirely, so referencing it here would
be a `NameError` if the guard tuple's `None` placeholder were ever replaced with the real
object without importing it). Separately, `_MARKUP`'s first pattern (`_NAV`'s neighbor list,
cleanup.py:63-73) is not covered by the guard at all, despite its first entry being exactly the
word-boundary-escape shape (`r"\s*\bWP\b(?=\s*[\(,]|\s*$)"`) the guard exists to catch. cleanup.py
is not in this agent's owned-file list. Left open.

## 60f13f1d4f77 -- rosetta.py, `scales_for()` srlimit=5 truncates native-scale search (FIXED)

Verified: rosetta.py:194 called the MediaWiki `list=search` API with `srlimit=5` -- below the
API's own default of 10, and far below this same project's own audited-safe value for the
identical kind of call: `feats.py`'s `discover()` uses `srlimit=50` and is on record (m82 audit,
feats.py:1156) as not truncating at that value. Raised rosetta.py's `srlimit` to `"50"` to match
that precedent, with a comment tying it to the m82 audit and to the One Piece Bounty/List loss
already documented a few lines above in the same file. This is a relevance-ranked API result
list widened, not a truncation reintroduced -- Hard Rule 0 is about not re-truncating a ranked
list, and 50 is the value this codebase has already established as safe for this exact call
shape; it is not a new cap.

## b32a24da9987 -- allsweep.py, stale `silence.note("allsweep.py:140")` (FIXED)

Verified: `run_verifier()`'s `TimeoutExpired` handler (now line 173) carried the stale numeric
tag `"allsweep.py:140"`, while the sibling generic-`Exception` handler four lines below already
uses the durable content form `"allsweep.py:run_verifier"`. Retagged the timeout handler to
`"allsweep.py:run_verifier-timeout"` -- distinct from its sibling so triage can still tell a
30-minute timeout from an actual crash, and immune to line drift like the sibling.

## ba4f12234033 -- standards.py, self-check blind to `CHARTER_REGRESSION_MAX_AGE_H` (FIXED)

Verified both halves of the finding directly: (1) the declared-floor regex
`^(M(?:IN|AX)_[A-Z_]+)\s*=` anchors `M(IN|AX)_` to the START of the name, so
`CHARTER_REGRESSION_MAX_AGE_H` (standards.py:368) was never captured as "declared" at all; (2)
even a fixed name would have fallen outside the search, because `body =
src[src.index("def check("):]` assumed every floor's only real use is textually inside
`check()`, and this floor's only use (standards.py:402, inside `charter_regression_verdict()`)
sits ABOVE `def check(` -- deliberately pulled out on 2026-08-25 for its own testability, per
that function's own docstring. `check()` calls it by name at line 980 and never repeats the
constant, so the old body-slice could not see it under any name-matching fix.

Fixed both: the declared-name regex now allows any number of leading `CAPS_` segments before
`M(IN|AX)_`; the used-check now scans the WHOLE comment-stripped file for a SECOND occurrence of
each declared name (the first being assumed to be its own declaration line, which every truly
dead constant also has and must not get credit for). Verified with a standalone probe
reproducing the exact logic against the live file: `CHARTER_REGRESSION_MAX_AGE_H` is now in
`declared` and NOT in `dead`, and the previously-empty `dead` list (27 floors, all already
measured) stays empty -- no floor lost coverage as a side effect of widening the search.

## d1e6c5916a18 -- scope.py, `build(records, hosts)` never reads `records` (FIXED)

Verified by reading: `build()` (scope.py:117) computes `todo` solely from `hosts.items()` and
never references its `records` parameter anywhere in its body; `main()`'s `--build` path called
`build(P.records(), hosts)`, which walks the entire 216-file `data/records/` tree only to throw
the result away at the callee's first line. Removed the dead parameter (`build(hosts)`), updated
the one call site, and removed the now-unused `import pipeline as P` (its only use in this
file). Confirmed via grep that no other module calls `scope.build()` (magnitude.py imports
`scope` only for its other functions, e.g. `ceiling_for`).

## e3a52d3f20b5 -- tempus.py, `apparent_lag_years()` inconsistent return shape (LEFT -- not my file)

Verified: the no-path branch returns `{"lag_years", "note"}` while the success branch returns
`{"distance", "lag_years", "path", "note"}` (tempus.py:83-96); `pipeline.py:1731` calls this in a
loop over every source, so a caller reading `r["path"]` or `r["distance"]` unconditionally will
`KeyError` on exactly the branch (no shared furniture) that real data is likely to hit often.
tempus.py is not in this agent's owned-file list. Left open -- note for whoever owns tempus.py:
the fix pattern already exists in this same codebase (`entity_match.candidates`, "ONE RETURN
SHAPE, ALWAYS"), so this is a known, previously-solved shape of defect.

## e755ab46df7f -- coverage.py, stale `silence.note("coverage.py:60")` (FIXED)

Verified: `_state_of_file()`'s file-load `except` (coverage.py:151) carried the stale tag
`"coverage.py:60"`; line 60 in the current file is inside a comment block about `_SO_CACHE_P`,
unrelated to this handler, whose actual effect on failure is to report the entity as NOT
ATTEMPTED. The sibling handler eleven lines earlier already uses a durable symbolic form,
`"coverage.py:so-save"`. Retagged to `"coverage.py:state_of_file-read"`, matching that
convention and naming the function and the operation that actually failed.

## fef23be535cf -- dashboard.py, rank-then-truncate on the swallowed-failures table (LEFT -- explicitly off-limits)

Verified: dashboard.py:316 (`sorted(f.items(), key=lambda kv: -kv[1])[:6]`) truncates the
swallowed-failure identity table to 6 rows, five lines after a comment on the same function
recording that an identical cap on `findings` was ruled a truncation on 2026-08-24;
`state/failures.json` currently holds 25 distinct tags, 19 of which would not be shown.
`swallowed_total` preserves the magnitude but not the identities past rank 6. dashboard.py is
explicitly listed as off-limits this batch (another agent owns it right now). Left open, not
resolved, per the standing instruction not to touch this file.

## Files touched this batch

- src/pipeline.py (273e6cb65d57)
- src/sweep.py (2b4d552df6f0)
- src/allsweep.py (4e93de4ab854, b32a24da9987)
- src/rosetta.py (60f13f1d4f77)
- src/standards.py (ba4f12234033)
- src/scope.py (d1e6c5916a18)
- src/coverage.py (e755ab46df7f)

No edits made to any file outside the owned list. `python -m pyflakes` and a bare `import` were
run against every touched file after every edit; all clean.
