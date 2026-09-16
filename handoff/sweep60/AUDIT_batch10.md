# sweep60 batch10 audit

Modules read in full, uncapped: src/publish.py (2163), src/generate.py (1172),
src/catalogue_web.py (821), src/ingest_doc.py (702), src/canon_backup.py (549),
src/burgs.py (442), src/descending_ladder.py (362), src/resonance.py (298). Total 6509
lines, all read start to end, no sampling.

## Summary

This batch is unusually clean. All eight modules carry extensive, dated, order-numbered
docstrings documenting a long history of prior sweeps finding and fixing exactly the
failure classes this audit was asked to hunt for (tautological checks, fail-open guards,
silent truncation, dead code, stale comments). I read every line rather than trusting
those self-reports, and did not find a live instance of priorities 1, 2, 5 or 6 (a check
that cannot fail, a fails-open guard, an uncapped-should-be-capped or capped-should-be-
uncapped list, an ordinary logic bug) anywhere in the material I read. I did find one
verified instance of priority 3/4 (dead code with a docstring that now contradicts the
code beside it), detailed below. Everything else noted is either already self-disclosed
in-file as tracked/held (not a new finding) or a judgment call I want to surface as
low-confidence.

## Findings

### 1. `generate.py:121-149` — `save_json()` is dead code whose docstring describes call
sites that no longer exist. VERIFIED.

```python
def save_json(path, obj):
    """-> True if the file actually landed.
    ...
    GATED, run #37's discarded-write-verdict pass. `silence.write_json` returns False rather
    than raising when the atomic replace is denied -- and a reader holding `output/index/
    catalog.json` open is enough, which on this machine includes estate.py, catalog.py and
    Norton's scan of the just-written tree. Every one of the six call sites below dropped that
    answer, so the two files this program exists to maintain could both silently stop moving:
      * catalog.json is the RESUME LEDGER ...
      * failures.json is where every REFUSAL lands ...
    """
    full = os.path.join(HERE, path)
    landed = silence.write_json(full, obj, indent=2)
    ...
```

`save_json` has **zero callers anywhere in generate.py**, and zero callers anywhere else
in `src/` (`grep -rn "\.save_json(" src/*.py` outside generate.py itself returns
nothing; `grep -n "save_json(" src/generate.py` returns only the `def` line). The
docstring's own claim — "every one of the six call sites below" writes catalog.json or
failures.json through this function — is no longer true of the code beside it: both
files are now written exclusively through `_land_catalog()` and `_land_failures()`
(compare-and-swap merge writers introduced later, per their own docstrings, to fix a
lost-update race that whole-dict `save_json` writes caused). `main()` calls
`_land_catalog`/`_land_failures` at every save point (incremental, per-refusal, and the
two final writes); I traced every `catalog[...]=`/`failures[...]=` write site in
`main()` and confirmed each is paired with `_land_catalog`/`_land_failures`, never
`save_json`.

This is exactly the "finished stage nothing dispatches to is indistinguishable from a
stage that was never written" shape this project's own docstrings elsewhere warn about
(quoting `pipeline.py:phase_chain()`, cited in `descending_ladder.py`): a reader who
greps for `save_json` and finds a detailed, dated docstring explaining why it matters
will reasonably conclude it is load-bearing for catalog.json/failures.json durability.
It is not — it is unreachable, and its docstring is now a description of a defect this
same file fixed by routing around it rather than by removing it. There is drill.py
coverage (`generate_catalog_save_does_not_resurrect_a_withdrawal`,
`generate_failures_save_keeps_a_concurrent_runs_rows`) that *asserts* generate.py's AST
contains no `save_json`/`write_json` call taking a `catalog`/`failures` argument — so the
absence of those two particular call sites is proven and intentional — but neither net
asserts anything about whether `save_json` itself still exists or is called for
something else, so the function's own continued presence, fully documented as though
live, was not caught by either net.

Not a security or correctness bug (nothing reads a stale or missing write from this
function, because nothing calls it), but it is a genuine instance of priority 3 (dead
code) compounded with priority 4 (docstring contradicting the code it's attached to) —
worth removing or re-marked "REPORTED DEAD, NOT DELETED" the way this same file marks
other intentionally-retained-but-unused symbols (e.g. `descending_ladder.py`'s
`rung_table()`, `catalogue_web.py`'s `MAX_PER_CATEGORY`/`CATEGORY_SCAN_DEPTH`), rather
than left presenting itself as active machinery.

## Checked and clean (no new findings)

- **publish.py** (2163 lines): the secret-scanning locks (`_SECRET`, `_SECRET_ASSIGN`,
  entropy gate, `_is_real_secret`, `scan_for_secrets`, `_scrub`), the export-root
  resolution (`export_root`/`home_export`/`_is_throwaway`), the prune/sync logic
  (`prune_export`, `sync_tree`, `_live_root_state`, `_live_file_state`), and the push
  sequence (`push()`, `PushHeld`, `_unpushed()`, the ledger/mutation interlocks in
  `main()`) were all read and traced end to end. Every fail-open/fail-closed choice is
  explicit and argued for in its own docstring (e.g. `maintenance_shift_live()` fails
  open deliberately and says why; the three `except ImportError` guards around
  `escalation`/`ledger_guard`/`mutate` all fail closed). I did not find a bypassable
  refusal path or a check that cannot fail. The `.gitignore` glob `*.pre*` (built by
  `gitignore_lines()`) is deliberately wider than the `_PRE_BACKUP` regex the copier
  uses, which could in principle gitignore-out a legitimately-copied file whose name
  contains a literal `.pre` substring outside the backup-suffix family (e.g. a
  hypothetical `notes.prewar.md`) — but this is the documented, deliberate direction
  ("wider is the correct direction for the half of the pair that guards a PUBLIC repo"),
  so I'm not filing it as a bug, just flagging it as a low-probability, intentional
  edge case worth knowing about if a real filename ever collides with it.

- **generate.py** (1172 lines, aside from finding 1): `strip_think()`, the
  `_covered`/`_deed_traced`/`_deed_shortfall` coverage checks, `_land_catalog`/
  `_land_failures` CAS merge logic, `save_raw`, and the whole `main()` job loop
  (evidence floor, prose gate, meta-language ban with fail-closed ImportError handling,
  per-job failure filing) were traced. No tautological check found.

- **catalogue_web.py** (821 lines): `_singular()` verified against every example in its
  own docstring (Goddesses→Goddess, Bosses→Boss, Classes→Class, Boxes→Box,
  Witches→Witch, Princess/Colossus unchanged) — the logic is correct and idempotent.
  `MAX_PER_SOURCE`/`MAX_PER_CATEGORY` tripwires, the dedup/provenance bookkeeping in
  `catalogue()`/`catalogue_composite()`, and `main()`'s exit-code logic were all read;
  no issues found.

- **ingest_doc.py** (702 lines): chunking (including the oversized-single-page
  re-split), the resume-cursor state validation, `record_path()`'s ambiguity refusal,
  and `main()`'s `--pdf`/`--mine` branching were traced. The `all(...)` at line 362
  checks over a fixed 2-element tuple `("next","found")`, not a possibly-empty
  collection, so it isn't the "all() over empty list" smell.

- **canon_backup.py** (549 lines): `members()`'s strict-refusal-on-missing-path,
  `snapshot()`'s read-back verification, `verify()`'s manifest-absent fail-closed path
  and archive-vs-manifest member comparison, and `restore()`'s open-before-truncate
  fix were all traced and are internally consistent.

- **burgs.py** (442 lines): the rank-size/Zipf math, `class_histogram`'s
  `_rank_at_or_above` boundary arithmetic (verified against CLASSES by hand), and the
  `--limit` narrowing-only guard were checked; correct.

- **descending_ladder.py** and **resonance.py**: both modules disclose their own
  dead-code status in their own docstrings (`hodge_decompose`/`resonance_strength` in
  resonance.py; the entire descending_ladder.py module, held per owner ruling) — I
  verified those disclosure claims by grepping for callers myself rather than trusting
  the docstrings, and confirmed zero callers in both cases, matching what's stated.
  These are not new findings since the modules already report their own status
  accurately. `hodge_decompose`'s Gauss-Seidel convergence logic and
  `descending_ladder.py`'s rung table/`transgression_bits`/`shrink_report` input
  guards were also traced and are correct as documented.

## Coverage note

No file under audit was edited. This report is the only file written by this run.
