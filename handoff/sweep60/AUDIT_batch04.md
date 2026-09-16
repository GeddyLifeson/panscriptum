# sweep60 batch04 audit

Modules read in full, uncapped: `src/mutate.py` (3206 lines), `src/allsweep.py` (1025),
`src/address_space.py` (674), `src/worldseed.py` (536), `src/pantheon.py` (432), `src/wh40k.py`
(350), `src/cosmology_graph.py` (261), `src/whoruns.py` (159). Total 6,643 lines, all read
top-to-bottom, no sampling.

## Overall impression

This batch is unusually clean. All eight modules are part of this project's "self-aware"
documentation style — nearly every non-obvious decision, past bug, and near-miss is narrated
in-line with dates and order IDs. Most of the classic failure shapes this audit was asked to
hunt for (tautological checks, fail-open guards, silent caps) have already been found and fixed
by earlier sweeps, and the fix is usually accompanied by a paragraph explaining exactly why the
old version was wrong. I read every line rather than trusting those paragraphs, and did not find
a live instance of priority-1 or priority-2 defects (a check that cannot fail, or a guard that
fails open) in any of the eight files.

Two real findings below, both minor. Everything else I looked at hardest — mutate.py's lock/
sandbox/reaper machinery, allsweep.py's tier grading, worldseed.py's `limit=0` guard, the
address-space bit-packing arithmetic — checked out under direct reading.

## Findings

### 1. `address_space.py:346` — `citation_card()` never passes `uncharted` to `shelfmark()`, so a revived caller would silently fabricate charted-looking tiers

VERIFIED by reading `shelfmark()`, `charted_gaps()`, `assign()`, and `assign_and_mark()` in full.

```python
def citation_card(name, addr, band="unassayed", decimal=None, interval=None,
                  epoch=None, attestation="Transcribed", worksheet=None, endonym=None,
                  threads=()):
    ...
    return {
        "identity": {
            "name": name,
            "endonym": endonym,
            "shelfmark": shelfmark(addr),   # <-- line 346, no `uncharted=` argument
        },
```

The module goes to considerable lengths elsewhere to make sure an *uncharted* tier (one
`TIERS.json` never measured for a given source) prints as `?` rather than as the integer `0`
that `assign()`'s `fit()` packs for it — see `charted_gaps()`, and `assign_and_mark()`'s own
docstring: "THE PAIR EXISTS SO A CALLER CANNOT TAKE ONE WITHOUT THE OTHER... `assign()` alone
hands back an integer in which an uncharted tier is indistinguishable from a charted zero, and
every caller that then printed `shelfmark(addr)` published the zero as a survey result." That is
exactly what `citation_card()` still does: it calls `shelfmark(addr)` with no `uncharted` set, so
`shelfmark()`'s default `uncharted=()` applies and every field prints as if it had been measured.
14 of 1,016 designations in `data/SHELFMARKS.json` currently carry at least one uncharted tier
(per `worldseed.py`/`address_space.py`'s own count), so a real card built from one of those rows
would misreport a `?` as a charted `0` — precisely the "guessing is a form of lying" failure Part
Two and Hard Rule 4 are about.

**Currently dormant, not live**: `citation_card()` has zero callers anywhere in `src/`, `handoff/`,
or `reference/` (checked by grep). It is already flagged as confirmed-dead in
`handoff/run35/checks_L4.py:214-223`, which notes it "carries an unfixed decimal-clamp bug
(sweep33 #7)" as the reason it hasn't been deleted. That comment names a different, already-known
defect (the `f".{round(decimal*100):02d}"` formatting, which produces 3 digits instead of 2 when
`decimal` rounds to 100) — it does not mention the `uncharted` omission I found. So this appears
to be a second, previously unrecorded defect in the same dead function, worth folding into
whatever owner decision eventually resolves `citation_card()`'s fate.

Severity: low (dead code, no live consumer), but a real defect if the function is ever revived
without this fix.

### 2. `wh40k.py:311-313` — a comment misquotes `compute()`'s own docstring

VERIFIED by reading `compute()`'s full docstring (lines 210-252) and grepping the whole file, plus
the two modules the comment says the pattern was "mirrored from" (`zfighters.py`, `halo.py`) for
the quoted sentence.

```python
                # THE PROVENANCE MARK IS SHOWN, NOT ONLY COMPUTED (order 901e441aae1d).
                # `compute()` derives a mark for every axis and --full printed the axis, the
                # score and the citation and nothing else, so the one view a curator would use
                # was the one view that hid the gap. `compute()`'s own docstring says the entire
                # purpose of the 'unattributed' default is that it "leaves the gap VISIBLE for
                # the curatorial pass, instead of hiding it behind a tag that reads as if the
                # work had been done" -- and every axis entry in this ROSTER is a 2-tuple, so all
```

The quoted sentence — `"leaves the gap VISIBLE for the curatorial pass, instead of hiding it
behind a tag that reads as if the work had been done"` — does not appear in `compute()`'s
docstring, nor in `_provenance()`'s docstring (the function that actually owns the
`unattributed` default), nor anywhere else in `wh40k.py`. I also grepped `zfighters.py` and
`halo.py` (the two modules this file elsewhere says it mirrors) and neither contains it either.
`compute()`'s docstring does make the same underlying point in different words ("Defaults to
`unattributed` rather than to `wiki`, which is the whole point: the old default asserted
something nobody had checked, and this one asserts only what is on record" — that sentence is
actually in `_provenance()`, not `compute()`), but the specific quoted sentence attributed to
"`compute()`'s own docstring" is fabricated or was deleted from the docstring after this comment
was written and never updated.

This is purely a documentation-accuracy issue — it does not affect behavior — but it is exactly
the "citation that no longer points at what it claims to" class of defect the audit asks for, and
in a codebase whose whole discipline rests on trusting inline citations, a false one is worth
flagging.

Severity: trivial (no behavioral effect; a stale/incorrect self-citation).

## Areas checked hard and found clean

- `mutate.py`'s lock/token lifecycle (`_lock_acquire`/`_lock_release`/`_hold_lock`), the
  `sandbox()`/`reap_orphans()`/`_owner_pid()` ownership machinery, and `_gate_result`/
  `could_not_judge`/`hang_confirms_a_kill`'s differential-judging logic — all read consistently
  with their own extensive docstrings; no tautological comparison or fail-open guard found.
- `allsweep.py`'s tier grading (`run_verifier`, `estate_faults`, `_row_is_fault`, the final `bad`
  sum) — every tier's contribution to the exit code and to `ALLSWEEP.json` was traced and is
  wired correctly; no computed-and-dropped tier remains (this file's own history is full of that
  exact class of bug, all now fixed and cross-referenced).
- `worldseed.py`'s `limit is not None and len(out) >= limit` guard in `build_all()` — confirmed
  the check now runs before the append, so `limit=0` correctly yields zero entries (the docstring
  describes a prior version that let one entry through; current code does not have that bug).
- `address_space.py`'s bit-packing (`_bits`, `FIELDS`/`WIDTHS`/`TOTAL_BITS`, `pack`/`unpack`,
  `_hash_offsets`/`HASH_BYTES`) — arithmetic traced by hand against the stated invariants
  (round-trip exactness, no overlap between hashed-field slices, `HASH_BYTES` ceiling check);
  consistent.
- `pantheon.py` and `wh40k.py`'s data tables and `main()` write/merge/exit-code paths — the
  gated-write and merge-failure bookkeeping (`write_ok`, `merge_failed`, the `--full` view) all
  correctly propagate to the return code; no dead branches or unreachable exception types found.
- `cosmology_graph.py`'s weighting formula and the `--write` path — the IDF-style weight formula
  matches its docstring exactly, and the full pair list is written unfiltered as claimed.
- `whoruns.py`'s process-matching (`script_of`, `running`) — the `-m`/`-c` exclusion, the
  `_FLAGS_WITH_A_VALUE` skip, and the tri-state `None`-vs-`[]` handling are all correct on
  inspection.

## Coverage

Recorded via `sweep_plan.record`, see below.
