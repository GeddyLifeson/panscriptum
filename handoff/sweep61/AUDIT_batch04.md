# sweep61 batch04 — audit report

Scope (read in full, start to finish, no sampling):

- src/mutate.py           3206 lines
- src/allsweep.py         1025 lines
- src/address_space.py     674 lines
- src/worldseed.py         536 lines
- src/sevenfold.py         441 lines
- src/events.py            350 lines
- src/propagation.py       254 lines
- src/catalog.py           167 lines

Total 6653 lines, all read.

## Method

Read every module top to bottom. All eight of these modules are exceptionally
heavily self-documented: nearly every historically-found defect (tautologies,
fail-open guards, truncations, dead code, false comments) is already recorded
in-line with its own "corrected/ order NNNN" comment, a measured before/after,
and in several cases a citation to the exact incident that motivated the fix.
That made this pass mostly a search for what those comments have NOT yet
caught, rather than a first look.

Where a claim was checkable without running any of the forbidden commands, I
verified it with `python -c` snippets that only import a module and call a
pure function (no mutation, no drill, no network, no GPU):

- `sevenfold.shelve()` against a synthetic 20-member, weights={} input:
  confirmed an exactly-even 7-way then per-branch split with no collisions,
  matching the docstring's claim that a wholly-tied block splits evenly.
- `address_space`: imported cleanly off the fallback tier counts (no
  TIERS.json needed), computed `TOTAL_BITS=88`, `WIDTHS`, and the hashed-field
  offsets/`HASH_BYTES`; confirmed no field overlap (universe 0-6, galaxy 8-46,
  star 48-75, planet 78-79) and a byte-exact `pack`/`unpack`/`shelfmark`
  round trip on the module's own worked example.
- `propagation.ascension_years(1) == 0.0` and `observed_mark`'s three
  documented edge cases (lag==0, lag<0, distance beyond arrival) all matched
  the docstring's claimed behaviour exactly.

None of these produced a new finding; they confirm the in-line claims are
currently true.

## Findings

**0 VERIFIED new defects.** No tautological check, no fail-open guard, no new
undisclosed cap/truncation, no crash-on-plausible-input, and no false
comment/docstring was found beyond what these modules' own comments already
record as known and fixed. `catalog.py`, `propagation.py`, and `events.py` in
particular are short, internally consistent, and I found nothing to add.

**1 QUESTION** (not filed as a finding — a design choice, not a defect):

- `src/mutate.py`, `main()`: the halt check (`escalation.status()`) runs
  before the `--list` branch but after the `--list-ruled` / `--rule-equivalent`
  / `--unrule` branches, and the comment above those three explains they run
  first "because none of them mutates anything." `--list` is documented
  identically ("count the mutants, run none of them") and does not touch the
  filesystem either, yet it IS blocked by a standing halt, unlike the other
  three read-only paths. This is fail-closed (the safe direction) rather than
  a fail-open bug, so it costs nothing but convenience — flagging only because
  the exemption rationale as written ("none of them mutates anything") applies
  equally to `--list` and the code doesn't follow it there. Possibly
  deliberate; a person should decide whether `--list` belongs in the same
  pre-halt group.

## Coverage recorded

Recorded via `sweep_plan.record('run61', [...], batch=4)` for the eight
modules above.
