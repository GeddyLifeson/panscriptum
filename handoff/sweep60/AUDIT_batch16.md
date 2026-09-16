# sweep60 batch16 — audit of local_agent.py, binding_health.py, onomast.py, weave.py, anchors.py, cleanup.py, sweep.py, physics.py

All 8 modules read in full, uncapped, end to end (6,518 lines): local_agent.py (1650),
binding_health.py (1601), onomast.py (844), weave.py (709), anchors.py (576), cleanup.py (452),
sweep.py (374), physics.py (312).

## Overall finding

This is a heavily-audited batch. Every one of these eight files carries dozens of dated,
order-numbered comments documenting bugs found and fixed by earlier sweeps (sweep22 through
sweep58, runs #5 through #57), specifically in the categories this audit was asked to look for:
tautological checks, fail-open guards, dead code, stale citations, hidden caps, and ordinary
bugs. I read every line against that history rather than trusting the comments, and I did not
find a new instance of any of the priority-1/2 failure shapes (a check that cannot fail, a guard
that fails open) in live, reachable code. I looked hardest at `local_agent.py`'s write gate
(`_safe`, `_denied_target`, `t_propose_patch`, `_gates`) and at `cleanup.py`'s deletion paths,
per the brief, and traced the gate logic by hand rather than trusting the surrounding prose; I
did not find a hole in either.

I have two low-confidence observations below (not confident enough to call bugs) and one
confirmed-but-already-self-disclosed dead-code note. No file gets a clean bill beyond "I looked
hard and didn't find anything new" — see the honesty note at the end.

## Findings

### 1. UNSURE — physics.py: `kinetic()` rejects mass==0, `binding_energy()` allows it (physics.py:93, physics.py:256)

`kinetic()`'s guard is `if not m > 0.0: raise ValueError(... "a non-positive mass is an
unestimable body, not a small one")` (line 93), which rejects `mass_kg=0`. `binding_energy()`'s
guard is `if not m >= 0.0: raise ValueError(...)` (line 256), which **accepts** `mass_kg=0` and
returns `U=0.0` without error. Both docstrings argue from the same premise ("a wrong number
wearing the shape of a right one"), but the two functions land on opposite verdicts for the
identical input (a body of zero mass). I verified this by reading both guards side by side; I
did not find anywhere in this file explaining why zero mass is "unestimable" for one quantity
and a legitimate zero for the other. It may be intentional (a massless point genuinely has zero
binding energy, whereas `kinetic()`'s docstring treats zero mass as "no body was described" —
different physical questions), so I am flagging this as an inconsistency worth a second look
rather than a confirmed defect.

### 2. Confirmed, but already self-disclosed — onomast.py: `register_for()`'s feature-voting branch is dead in production (onomast.py:443-498, call site onomast.py:627)

The weighted-vote logic (`FEATURE_SHIFT`/`GENRE_WEIGHT`/`FEATURE_WEIGHT`, lines 410-498) is
reachable only when `register_for()` is called with `genre_register` or `features` set, and the
only production caller, `name_worlds()` at line 627, calls it with one positional argument
(`register_for(v["continuity_group"])`), so those parameters are always `None` and the whole
branch never executes against real data. I verified this by reading `name_worlds()`'s call site
directly. This is **not a new finding** — the module's own docstring at lines 450-481 already
names this exact gap ("HELD, MARKED, AND NOT WIRED... `name_worlds()` -- the only production
caller -- still passes `register_for(v["continuity_group"])`, one positional argument") and
records an owner ruling to hold it deliberately. Reporting only so the batch record shows it was
checked and matches the code.

### 3. UNSURE, very low confidence — pervasive unclosed file handles on read-only paths

Several read paths across this batch open a file without a `with` block or explicit `.close()`,
e.g. `sweep.py`'s `rosetta_index()` (line 135: `json.load(open(p, encoding="utf-8"))`) and
`navtree_names()` (line 151, same shape), and `local_agent.py`'s `t_read_file()` (line 643:
`text = open(full, encoding="utf-8", errors="replace").read()`). None of these raised in my
reading — CPython's refcounting closes the handle essentially immediately since no reference is
retained — and this same idiom is used in dozens of places across the wider codebase (not just
my batch), so it reads as a deliberate house style rather than a defect anyone missed. I flag it
only because the task brief explicitly asks about "a resource never closed"; I do not think this
rises to a real bug on CPython and I am not confident it's worth fixing.

## What I checked hardest and found clean

- **local_agent.py's write gate**: `_safe()`, `_protected_identities()`/`_identity_denied()`,
  `_denied_region()`/`_denied_target()`, the WRITABLE_PREFIXES/WRITABLE_FILES allowlist, the
  DENYLIST_PREFIXES region check, the blast-radius cap (`_blast_ok`), and `_gates()`'s
  parse/lint/import/verify_math chain in `t_propose_patch`. Traced the order of checks by hand
  (module denylist -> identity denylist -> allowlist on both written and resolved spellings ->
  protected regions -> empty-find guard -> uniqueness guard -> blast cap -> write -> gates ->
  revert-on-failure). Did not find a gap. The `verify_math` pass/fail extraction uses a regex
  (`RESULT:\s*\d+\s+passed,\s*(\d+)\s+FAILED`) rather than a substring test, which correctly
  avoids the "0 FAILED" substring-of-"10 FAILED" bug this same file's comments say was fixed
  elsewhere in this project.
- **cleanup.py's deletion/exclusion paths**: it never deletes a file or a record; it only flips
  `catalogued: False` / sets `excluded` reasons and writes back through `pipeline.write_record`,
  which is gated (`if not PL.write_record(path, rec): ... unwritten.append(src)`) and reported.
  The `_ruby_question_mark`/`_ruby_parenthetical` regex replacements both decline on plain ASCII
  text (guarding the exact false-positive class documented in their own history), and I checked
  the non-ASCII test by hand against the three ASCII examples the comments cite.
- **binding_health.py's tri-state verdict logic** (`verdict()`): enumerated all reachable
  branches by hand against `(ok_present, ok_absent, ok_reachable) ∈ {True,False} × {True,False,None} × {True,False,None}`;
  every combination reaches a return, none of them defaults to a pass on missing evidence.
- **anchors.py's own self-audit** (`run()`'s `verdicts` list): confirmed none of the graded
  claims are tautological — each reads live data from `assay.assay`, `assay.instrument`,
  `custodes.convene`, or `rigor.measure_bit_value`, and the file's own comments explicitly name
  and exclude the two checks that WOULD be tautological (prior+attestation shares summing to 1,
  and `covers_every_reading`), which is the right call, not an oversight.
- **weave.py's `components()`**: refuses `threshold <= 0` before agglomerating, which is exactly
  the guard needed since an absent pair defaults to weight `0.0` and a non-positive threshold
  would otherwise merge every source into one continuity.
- Grepped all 8 files for stale `file.py:NNN` citations, `TODO`/`FIXME`/`XXX`, and bare
  `except: pass`. One citation found (`binding_health.py:499` → `feats.py:204`); checked it
  against the live `feats.py` and it still matches (the 1,364-throttled-fetches figure is at
  that line). No bare `except: pass` found in any of the 8 files.

## Honesty note

I did not find a confirmed new defect in the top three priority categories (tautological check,
fail-open guard, dead/unreachable code not already self-disclosed) anywhere in this batch. Given
how many prior sweeps have already passed over these exact eight files with that exact mandate,
I consider "no new finding in those categories" to be a real result here, not a sign I stopped
looking early — I read every line of every file, not a sample.
