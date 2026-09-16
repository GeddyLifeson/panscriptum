# sweep60 batch01 — AUDIT of src/drill.py

Scope: the entire file, 23,258 lines, read sequentially start to finish in ~1000-line
chunks (no sampling). No file under `src/` was edited. This report is the only file
written.

## Context

`drill.py` is itself an adversarial test harness whose whole subject is "a check that
cannot fail looks exactly like a check that passed." It has already been through
dozens of prior sweeps (the file's own comments cite orders and sweep numbers going
back months), and a very large fraction of its ~13,000 lines of docstring prose is a
first-person history of exactly the defect classes this audit was asked to look for —
tautological nets, fail-open guards, dead-code blind spots, stale line citations, caps
— each one found, named, and then netted so it cannot recur silently. That density of
prior self-correction is the reason this batch's findings are thin: most of the
obvious instances of every requested defect class already have a regression test
sitting next to them, with the incident and the fix both spelled out in the
docstring.

I looked for defects in drill.py's own code (not the modules it drills), specifically
new instances of the six priority classes, not restatements of history already fixed.

## Findings

### 1. Unclosed file handle at module import (LOW severity, VERIFIED as written, low practical impact)

`src/drill.py:35`:

```python
_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")
```

The file object returned by `open(...)` is never closed or used as a context manager;
the code calls `.read()` on it directly and lets the temporary go out of scope. On
CPython this closes via refcounting essentially immediately, so I would not expect
this to leak a handle in practice — but it is exactly the "a resource never closed"
shape called out in the task's ordinary-bugs category, and it sits in code that
otherwise (elsewhere in this same file, e.g. `_ast_of`, `_carries_eaten_escape_guard`'s
callers) consistently uses `with open(...) as fh:`. Worth a one-line fix for
consistency; not something I'd call a real hazard on the interpreter this project
actually runs under.

### 2. `all(...)` over a table that is empty today only by convention, not by construction (LOW/UNSURE)

`axis_score_tells_its_five_refusals_apart` (around line 16030, inside
`drill_assay_behaviour`):

```python
wrong_scale = all("NOT on the energy ladder" in why(1e9, "M3", ax)
                  for ax in ASSAY.NON_ENERGETIC_AXES)
...
return (quantity_cases and off_ladder and typo and wrong_scale and partition and scores)
```

`all()` over `ASSAY.NON_ENERGETIC_AXES` is the exact shape the task's priority #1
names — "an `all(...)` over a possibly-empty list." Today `NON_ENERGETIC_AXES` holds
six axes (the net's own docstring says so: "six axes permanently in this state"), so
`wrong_scale` is a real, non-vacuous assertion right now. But nothing in this net
enforces that the set is non-empty before looping over it the way
`_every_re_importer_carries_the_eaten_escape_guard` (a few thousand lines later in the
same file) explicitly does for its own roster ("An importer set that comes back EMPTY
also fails: a matcher that matches nothing would otherwise hold here for ever"). If a
future edit to `assay.py` ever moved every axis onto the energy ladder (emptying
`NON_ENERGETIC_AXES`), `wrong_scale` would silently become `True` by vacuous truth,
and the accompanying `partition` check two lines below
(`sorted(ASSAY.NON_ENERGETIC_AXES) == sorted(set(ASSAY.WEIGHTS) - set(ASSAY.BAND_EDGES["M0"]))`)
would also pass trivially (both sides empty) — so nothing in this net would notice
that its entire "wrong-scale axis" arm had stopped testing anything. This is
low-confidence as a live bug (I did not verify whether such a change to `assay.py` is
plausible or planned) but it is a structurally real instance of the pattern the task
asked me to prioritize, in a net that otherwise takes real care to avoid exactly this
shape everywhere else in the file.

### 3. No other new findings

I read every priority class against the full file and did not find additional
instances I'm confident are live, unaddressed defects:

- **Tautologies / checks that cannot fail**: none found beyond #2 above. Every
  `all()`/`any()` I checked over a fixed, non-empty, hand-written iterable (which is
  the overwhelming majority) is fine; the several dozen that operate over *derived*
  rosters (module lists, importer lists, roster diffs) are explicitly guarded against
  the empty-collection case (`if not importers: raise...`, `if not wrote: return
  False`, `if not built: ...`, etc.) — this file's authors clearly learned this lesson
  the hard way and now check for it by habit.
- **Fail-open guards**: I did not find a new `except: pass` that silently permits
  further action. Every swallow I traced either (a) is inside a probe's own cleanup
  path with an explicit `silence.note(...)` fallback recording the swallow, or (b) is
  one of the documented, deliberate fail-open exceptions (the mutation lock's stale-
  holder path, the halt lock's fail-open-by-owner-ruling path, `_a_probe_release`'s
  documented `health` import failure) — each of which is itself the subject of a net
  proving the fail-open case is bounded correctly (e.g. `dead_holder_does_not_block_
  forever`, `unreadable_lock_counts_as_HELD`).
- **Dead / unreachable code**: I did not find an unreferenced top-level function.
  Every `drill_*` area function I saw defined is present in `main()`'s default area
  tuple (I cross-checked the full list against the tuple at the bottom of the file);
  there is no orphaned area whose nets would silently never run — which would have
  been the single largest possible finding in a file like this, given how much of its
  own prose is devoted to exactly that failure shape ("a value computed, printed, and
  dropped").
- **Stale comments / line citations**: none found. The file has already migrated away
  from line-number citations entirely (order 0c7592915a48, "cited by symbol, not by
  line") after being burned by drift repeatedly, and every citation I checked uses
  the symbol form consistently.
- **Caps / truncation on something that should be uncapped**: none found in drill.py
  itself. Its own `drill_no_caps` area exists to catch this class in *other* modules;
  I did not find a `[:N]` or similar truncation inside drill.py's own logic that
  isn't a legitimate stderr/text-length display cut (and those are explicitly marked
  as display-only, e.g. `prove_net`'s stderr tail, which is labeled "THE CUT SAYS IT
  IS A CUT").
- **Ordinary bugs** (wrong variable, off-by-one, swapped args, wrong exception type):
  none found with any confidence. I traced several of the more intricate AST-walking
  helpers (`_live_stmts`, `_live_walk`, `_arm_leaves`, `_gate_precedes_spawn`,
  `_is_rooted`, `_carries_result_of`) end to end against their own docstrings'
  worked examples and did not find a discrepancy between the described behavior and
  the code.

## Summary

This batch is close to clean. Two low-severity, low-to-moderate-confidence findings
(an unclosed file handle at import time; a defensible-but-unguarded `all()` over a
currently-non-empty derived set), both filed above with line references. Everything
else I traced resolved correctly against its own documentation. Given how much of
this specific file's history is "N sweeps ago, this exact class of bug was found and
fixed here," the low yield is itself consistent with the file being genuinely
well-hardened against sampling-only sweeps — which is also a reason to keep reading
it in full on every pass, since the failure mode this project fears most is
precisely a check that *used* to fail correctly quietly stopping.
