# Sweep 59 -- AUDIT batch 09

Modules read in full:

| module | lines | read (top to bottom? mtime) |
|---|---|---|
| src/foreman.py | 2208 | yes (mtime 2026-09-13 23:48, unchanged through review) |
| src/rigor.py | 1132 | yes (mtime 2026-09-08 08:16, unchanged through review) |
| src/derivation.py | 812 | yes (mtime 2026-09-13 23:42, unchanged through review) |
| src/address_space.py | 674 | yes (mtime 2026-09-13 23:36, unchanged through review) |
| src/address.py | 543 | yes (mtime 2026-09-14 22:14, unchanged through review) |
| src/pantheon.py | 432 | yes (mtime 2026-09-08 16:24, unchanged through review) |
| src/events.py | 342 | yes (mtime 2026-09-13 23:24, unchanged through review) |
| src/tells.py | 303 | yes (mtime 2026-09-13 22:15, unchanged through review) |

All eight mtimes were re-checked at the end of the review and matched what was read; nothing in
this batch changed under me.

## src/events.py

### New findings

**DEFECT MINOR -- the console listing joins candidates with ", ", but a candidate can itself
contain ", "**

where: src/events.py `main()` (line 325, at mtime 23:24)

evidence:
```
325:            print("        names: %s" % ", ".join(e["named"]))
```
`ev["named"]` (built in `parse()`, lines 230-265) can hold both a whole bolded span AND the
fragments `_fragments()` split out of it (lines 246-263: the whole span is always appended via
`named.append(s)`, then each surviving fragment from `_fragments(s)` is appended separately). A
span like `**Soul Edge, wearing Siegfried**` therefore lands in `named` as four entries:
`"Soul Edge, wearing Siegfried"`, `"Soul Edge"`, `"Siegfried"` (plus, from a different span,
`"Zeno Accords"`).

failure: running `python src/events.py` against the live Chronicle (reproduced this session,
no --write) prints, verbatim:
```
  E-1112-BRACKET   The War of the Broken Bracket (1,112 AS — E-1112-BRACKET ...
        names: Soul Edge, wearing Siegfried, Soul Edge, Siegfried, Zeno Accords
```
A reader cannot recover the four-item list from that line -- it reads as five or six
comma-separated tokens, and there is no way to tell from the console output alone where one
candidate ends and the next begins. This is the exact console a person is expected to run to
audit the parse (the module's own closing line says "A name here is a CANDIDATE... decided by
the join"), and the module's stated goal throughout is that "the evidence stays auditable"
(line ~253) -- which this print defeats for any span containing a comma, i.e. exactly the shape
`_fragments()` exists to handle. `data/EVENTS.json` itself is unaffected: `ev["named"]` is stored
as a proper JSON list and `threads.py` would consume it programmatically, not through this
string. So this is a console-display defect only, not a data-correctness one.

remedy: join with a delimiter that cannot appear inside an item (e.g. `" | "`), or print one
name per line/column the way `--refused` already does (line 331, one row per candidate).

### Known (already open orders)
None of the four open orders whose `where` touches these eight modules are new to me; all are
`foreman.py`-scoped and already carry the shift-by-shift history in state/workorders.json:

- `d1709d8e757d` (OWNER, ENTITY_INDEX_NEVER_REBUILT...) -- still accurate: `src/foreman.py`
  remedies still do not schedule a `weave_index.py` rebuild; nothing in `foreman.py` changed
  that this shift.
- `d9328fe1ee38` (OWNER, STALL_STANDARD_WATCHES_THE_LOG_NOT_THE_WORK) -- the `foreman.py` half
  (`kill_stalled_job` / `_io_moving`) is fixed per the order's own note and I verified the fix is
  in place and consistent (lines 600-770): a kill now requires both a quiet log AND no I/O
  movement across a 20s window, and an unrestartable job is escalated rather than killed. The
  remaining half (a job's declared output tree) lives in `standards.py`, not in my batch.
- `e45618de083f` (LOCAL, CODEWATCH_RESTART, INFO) -- routine rc=17 restart log entry, not an
  actionable finding.
- `ff77e242b830` (OWNER, OWNER_QUESTIONS_FROM_SWEEP48_BUNDLE) -- item 2 concerns
  `foreman.py restart_ollama`/`_ollama_answers`; I re-read both (lines 1277-1394) and the
  behaviour matches the order's description exactly (success = `/api/tags` answers, not a
  completed generation). Still an open ruling, not a new defect.

## src/foreman.py, src/rigor.py, src/derivation.py, src/address_space.py, src/address.py, src/pantheon.py, src/tells.py

### Checked and clean (notable things verified, not merely read)
- `foreman.py` DENYLIST/NEVER_DEDUPED, the `_BAD_CHARS` guard placement, `_catalogue_batch()`'s
  rotation/rate math, `kill_stalled_job`'s job-name-to-fragment resolution via `lognames.OWNER`,
  and `round_once`'s `.always`-remedy handling were all read end to end; each matches its own
  docstring and no new false-success or fail-open path was found beyond the ones the file's own
  comments already record as fixed.
- `derivation.py`: ran `python src/derivation.py` (read-only; no writes) -- `check_graph()`
  reports zero problems and the module prints `VERDICT: LEDGER CLOSES`. `_target_names`,
  `scan_constants_with_reason` and the recursive `_scan_modules()` walk were traced by hand and
  are consistent with their docstrings.
- `rigor.py`: ran `python src/rigor.py` (read-only) -- all six sections execute without error and
  print internally consistent numbers (CR/curl-fraction agreement, MDL floors all "above floor",
  Jensen-gap arithmetic). `_validate_reciprocal_matrix`, `perron_weights`/`logrank_weights`'s
  two-sided CR/eta checks, and `bradley_terry`'s Ford's-condition refusal logic were checked by
  hand against the docstring's worked claims.
- `address_space.py`: imported it in a side-effect-free scratch check (module-level code only
  reads `data/TIERS.json` and `data/CONTINUITY_GROUPS.json`, never writes) and confirmed
  `WIDTHS`/`TOTAL_BITS`/`CAPACITY` compute to 88 bits / 3.095e26 capacity against the live
  census, and that the docstring's "FOR SCALE" figure (addressable = 5.4e21) matches the live
  `exoplanets * continuities` computation (5.376e21) exactly -- this claim has NOT drifted.
  `pack`/`unpack`/`_hash_offsets`/`_LEGACY_HASH_OFFSETS` were traced by hand; the round-trip in
  `main()` (not run, since `main()` writes `data/SHELFMARKS.json`) is keyword-only as its comment
  claims.
- `address.py`: the spine-code matcher (`_normalize`, `_token_set`, `_index_name_is_placed_like_a_title`,
  the most-specific-wins loop, the token-overlap fallback) was traced by hand against its own
  worked examples; `tier_for`/`tier_rank`/`promote`'s promotion-only ladder logic is correct
  (verified TIER_FLOORS is checked in ascending order so the loop lands on the highest tier
  reached). `pyflakes` and `ruff` were run against all eight modules in this batch: pyflakes is
  clean; ruff's hits on `address.py`/`address_space.py` are all style-only (percent-formatting,
  import sort, blind-except, `dict()`-as-literal) and were already declined project-wide per
  `src/secondopinion.py`'s stated policy, not correctness defects.
- `pantheon.py`: the GODS table's `compute()`/`value()`/merge-with-Z_FIGHTERS logic was traced by
  hand; `value()` assumes `rec["assay"]["decimal"]` is never `None` (which `assay.assay()` can
  return when a worksheet or scored axis is absent), but every GODS entry supplies a full
  worksheet and every currently-live `data/Z_FIGHTERS.json` entry (checked all 15) carries a
  non-null decimal, so this is not a live defect against current data -- flagged only as a
  fragility, not filed as a finding, per the "concrete input or state" bar.
- `tells.py`: `_anchor`/`_SENTENCE_START` splicing was traced against every DISCOURSE/STRUCTURAL
  pattern that starts with `^\s*`; the escape-mangling self-guard (lines 178-182) and
  `prompt_in_sync()`'s CRLF-folding comparison were checked by hand and are correct.

## QUESTIONS: 0

No new open questions raised in this batch (one long-standing open design question already
recorded in `address.py`'s own comments -- the `_FILLER` single-character-token question -- is
pre-existing prose, not a new finding, and is left as-is per the module's own "left for a ruling"
note).
