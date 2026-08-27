# Run35 batch 3 audit (agent scope: src/coverage.py, src/standards.py, src/tuning.py,
src/rosetta.py, src/lognames.py, src/sweep.py, src/allsweep.py)

## 1230a343d75f -- coverage.report() ranked, then silently truncated, the two lists it calls
"the outstanding work"

Confirmed exactly: `coverage.py:213` sliced the "SOURCES WITH NO WIKI HOST" list to `[:12]`
under a header that literally says "nothing can ever be cited here", and line 218 sliced
"WORST COVERED WITH A HOST" to `[:show]` with `show` defaulting to 26 both in `report()`'s
signature and on the `--show` CLI flag, so the supervisor's default invocation printed 26 no
matter how many sources were actually behind. Fixed: the hostless list now always prints in
full, headed by its real count ("(N, all shown)"). The worst-covered list's default changed to
`show=None`, which prints everything; an explicit `--show N` still works but now announces how
many rows it held back ("showing N of M; M-N more not shown, --show to raise") instead of
truncating silently -- an announced, caller-requested cap is not the Hard Rule 0 violation, a
silent one is. Left the "BEST COVERED" top-10 list untouched: it is a best-of highlight, not a
list of outstanding work, and wasn't named in this order's evidence. Verified pyflakes+import
clean, and confirmed live (with a real dashboard's `measure()` output as well as synthetic rows
in `handoff/run35/checks_batch3.py`) that both fixed sections now print every row and the
`--show` path announces its cut.

## 9d4d0c4e6c6a -- standards.py's two remaining caps on the exact fields the order text told a
reader to grep for

Confirmed both, at the current (shifted-by-earlier-edits) line numbers: `worst = sorted(good,
key=lambda c: c.get("coverage", 0))[:3]` in the "every source is fully catalogued" standard's
detail string, and `", ".join(_pending)[:120]` in the "promotions have their spine codes
amended" standard, which could and did cut a source name mid-word. Both are the second
occurrence of the exact shape this file already fixed once (the "unrecognised pool" block a few
hundred lines below, whose own comment calls this "lesson 14: fix a shape, then grep the tree
for it" -- the grep was never done). Fixed both to print every entry, no cap, matching that
same block's already-established pattern in this file. Verified pyflakes+import clean; ran
`standards.report()` live against real dashboard state and confirmed the "worst" detail now
lists every uncovered source (50+, not 3) and the spine-code-pending line is no longer
character-truncated.

## 5b85ab54b176 -- standards.report()'s "N/N standards met" only counted standards that managed
to emit

Confirmed by reading `check()` end to end (via AST, to be sure of the count): roughly twenty
standards have their only `out.append()` inside a `try:` whose `except Exception:` does nothing
but `silence.note(...)` -- so a missing or unreadable input file (COMPLETENESS.json,
dashboard_history.json, SHELF_RANKS.json, the provider-models snapshot, etc.) doesn't fail that
standard, it deletes it, and `report()`'s `len(rows) - len(bad)) / len(rows)` line then divides
by the smaller total and reads as *more* consistent for having lost evidence -- exactly the
"green by absence" failure CLAUDE.md's Hard Rule -1 names. Fixed by adding a `_dropped` list
inside `check()`, populated by each of those ~20 except-handlers alongside their existing
`silence.note(...)` call, plus one new standard appended at the end of `check()` ("every
standard could read its own input") that MISSES, at HIGH severity, and names every standard
that vanished this run. A dropped standard now costs a MISS instead of shrinking the
denominator it would have counted against. Verified pyflakes+import clean; ran
`standards.report()` live against real dashboard state (currently 31/43, nothing dropped, new
row prints "ok none"), and in `handoff/run35/checks_batch3.py` forced a real input read
(COMPLETENESS.json) to fail via a monkeypatched `open()` and confirmed by set comparison that
exactly the one broken standard disappears, the aggregate standard is present in both the clean
and the broken run, and it correctly MISSES and names the broken standard on the broken run.

## 495390283745 -- a check that cannot fail at the thing it names

Confirmed: `standards.MIN_CALLS_TO_JUDGE_RATE = 20` was an independent hand-copied literal, and
`verify_math.py`'s check ("the threshold itself is the one tuning.py already settled on")
compares that constant against the literal `20`, never against `tuning.MIN_CALLS_TO_JUDGE`
itself -- so raising `tuning.MIN_CALLS_TO_JUDGE` would leave the check green while the two
policies silently diverged, which is precisely the failure the check's own note says it exists
to catch. `verify_math.py` is out of this agent's ownership, so the fix goes at the source
instead: `standards.py` now imports `tuning` at module level and sets
`MIN_CALLS_TO_JUDGE_RATE = tuning.MIN_CALLS_TO_JUDGE` directly (no circular import risk --
`tuning.py` imports nothing from `standards.py`), so the two names are the same number by
construction and cannot drift apart regardless of what any downstream check compares against.
Verified pyflakes+import clean; confirmed live that `standards.MIN_CALLS_TO_JUDGE_RATE == 20 ==
tuning.MIN_CALLS_TO_JUDGE`. Proposed, in `handoff/run35/checks_batch3.py`, a replacement for
`verify_math.py`'s check that compares against `tuning.MIN_CALLS_TO_JUDGE` directly (which can
no longer be fooled by a coincidence) plus a source-regex regression guard against the literal
being re-inlined.

## 6e3e3e553fd5 -- rosetta.check(), the module's stated purpose, had no automated caller

Confirmed: `rosetta.py`'s `main()` `--check` branch always `return 0` after printing the rhos,
regardless of any `DISAGREES` flags, and `allsweep.py`'s `VERIFIERS` list -- the thing that
actually runs things every sweep -- had no rosetta entry (`rosetta` sits only in the dead
`NEVER_RUN` set, which nothing in `allsweep.py` reads, so its presence there was never load-
bearing either way). Fixed: `rosetta.py --check` now returns 1 if any scale disagrees with the
Assay (rho < 0.3), matching `silence.py`/`audit.py`'s existing 0-clean/1-findings contract so a
caller can gate on it, and added `("franchise rank agreement", ["rosetta.py", "--check"])` to
`allsweep.VERIFIERS`, so it now runs automatically every sweep. Verified pyflakes+import clean
on both files. Ran `rosetta.py --check` live: currently 0 rows (the mine has no names
overlapping the 217 scored Assays yet, so nothing to disagree with -- correctly wired, no false
positive). In `handoff/run35/checks_batch3.py`, built a synthetic scale whose native order is
the exact inverse of the Assay's and confirmed, through `main()`'s real code path with temp
files, that the process now exits 1 instead of the old unconditional 0.

## dcdd1fa96864 -- DISPROVED: the substring collision does not reproduce against current source

The order's evidence quotes `overnight.py:180` as `if fragment in cmd.replace("\\","
/").split("/")[-1] or fragment in cmd: return True` -- a plain substring test under which
`lognames.OWNER[SWEEP] = "sweep.py"` would indeed match a running `allsweep.py`. That is not
the code currently on that line. `overnight.running()` at line 179 calls `_cmd_is_running(
fragment, cmd)`, a function whose own docstring explains it replaced exactly that substring test
(citing the identical `codewatch.twins()` bug from run #34) with an exact
`os.path.basename(script) == os.path.basename(want)` comparison. Measured directly against the
live function: `_cmd_is_running("sweep.py", "python .../src/allsweep.py")` returns `False`;
`_cmd_is_running("sweep.py", "python .../src/sweep.py")` returns `True`. `foreman.py:818`'s
`ON.running("sweep.py")` call goes through this same fixed matcher. So none of the order's three
alleged live consequences (foreman's guard, overnight's start-guard, kill_stalled_job) actually
fire on this collision today. No file was touched -- `overnight.py` is outside this agent's
ownership regardless, and `lognames.py` needed no change since the fragment it defines does not
collide under the matcher actually in effect. Per METHOD step 1, resolved as disproved rather
than "fixed," and a regression guard (asserting the two `_cmd_is_running` results above) was
added to `handoff/run35/checks_batch3.py` so a future regression back to substring matching
would be caught.
