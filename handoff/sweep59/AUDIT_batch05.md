# Sweep 59 -- AUDIT batch 05

Modules read in full: | module | lines | read (top to bottom? mtime) |
| feats.py | 2798 | yes, top to bottom (mtime 2026-09-14 22:14) |
| chain.py | 1067 | yes, top to bottom (mtime 2026-09-14 22:18 -- being edited tonight by another agent; unchanged between my read and this write) |
| estate.py | 723 | yes, top to bottom (mtime 2026-09-08 16:20) |
| withdraw_chapters.py | 613 | yes, top to bottom (mtime 2026-09-14 00:00) |
| coverage.py | 456 | yes, top to bottom (mtime 2026-09-14 00:11) |
| cosmography.py | 375 | yes, top to bottom (mtime 2026-09-08 16:25) |
| context_budget.py | 319 | yes, top to bottom (mtime 2026-09-13 23:21) |
| scale_theories.py | 215 | yes, top to bottom (mtime 2026-09-13 23:44) |

## chain.py

### New findings

**DEFECT CRITICAL -- chain.py's own entry point never checks the plant-wide halt (Hard Rule -1)**

where: src/chain.py `main()` (lines 943-1067 at mtime 22:18), whole file

evidence: `escalation.assert_clear`'s own docstring (src/escalation.py:1122-1127) says "EVERY
entry point calls this before doing anything. The plant-wide interlock." `chain.py` has a full
standalone CLI (`argparse`, `--harvest-only`, `--refresh-continuity`, `--limit`, `--workers`,
`--prior`) and its own `if __name__ == "__main__": sys.exit(main())` at line 1066. `main()` goes
straight from `ap.parse_args()` into `refresh_continuity()` / `harvest()` / `extract()` /
`adjudicate_mutuals()` / `fit()` / `write_result()` with no halt check anywhere. A whole-file
grep confirms it: `grep -n "escalation\|assert_clear\|_ESC" src/chain.py` returns zero lines.
Compare `src/withdraw_chapters.py:224-230` and `src/feats.py:2664-2683`, both in this same
batch, which import `escalation`, fail closed on `ImportError`, and call
`_ESC.assert_clear(os.path.basename(__file__))` as the first executable statement of `main()`,
above even the argparse block -- withdraw_chapters.py's own comment there says this exact
history: "Fourteen modules in src/ did [call it]. This one ... did not" (that was its own past
defect, order bd107a18b13e, since fixed). `chain.py` is the sibling that was never fixed the
same way and was never even flagged: `src/verify_math.py:7389-7426`'s `_INTERLOCKED` roster
check only verifies that a module which **already calls** `assert_clear` is on the roster (and
vice versa) -- a module that never calls it at all is invisible to that check by construction,
so chain.py sails through it silently. `grep -l "assert_clear" src/*.py` lists 17 files; chain.py
is not one of them.

failure: an owner-issued halt (Hard Rule -1, e.g. after a bad ruling on the Assay or a corrupted
harvest index) stops every one of the 13 interlocked modules, but `python src/chain.py`,
`python src/chain.py --refresh-continuity`, or `python src/chain.py --harvest-only` all still run
to completion: `harvest()` re-scans and rewrites `state/chain_harvest_idx.json`,
`refresh_continuity()` patches it directly, `extract()` spends real cloud/local model-call budget
across 8 threads, and `write_result()` replaces the published `data/CHAIN.json` -- the file this
module's own comments describe as read by other consumers of the Chain-of-Defeats accuracy leg --
all while the library believes itself halted. This is precisely the shape Hard Rule -1 was
written to close ("nobody with authority to stop things was told... the gate that should have
prevented it had been DELETED"), except here the gate was simply never installed on this
particular entry point, and the roster built to catch that class of gap cannot see an omission,
only a regression.

remedy: add, as the first statement of `main()` (above `ap = argparse.ArgumentParser()`), the
same fail-closed pattern `withdraw_chapters.py`/`feats.py` use:
```python
try:
    import escalation as _ESC
except ImportError as _esc_gone:
    raise SystemExit(
        "REFUSING TO START: the escalation chain (src/escalation.py) could not be "
        "imported (%s), so the halt cannot be read. Hard Rule -1." % _esc_gone
    ) from _esc_gone
_ESC.assert_clear(os.path.basename(__file__))
```
and add `"chain.py"` to `verify_math._INTERLOCKED` (src/verify_math.py:7389-7391) so the roster's
own completeness check keeps this wiring from being quietly removed again.

### Known (already open orders)

- `058fa19d4e65` (CHAIN_HARVEST_INDEX_HIDES_A_WIDENED_OUTCOME_PATTERN) -- **the code-level fix is
  now present.** `_RECIPE_KEY` / `_harvest_recipe_digest()` (chain.py:198-227) fingerprint
  `OUTCOME.pattern`/`OUTCOME.flags`; `harvest()` (line 378) discards the whole cached index
  whenever the stored digest doesn't match the live one, forcing every feats file to be re-opened
  once under the current recipe -- this is exactly the "durable fix" the order's remedy proposed
  as an alternative to a one-off rebuild. This is the change the brief names as being made
  tonight by another agent on this same file (mtime 22:18); I did not re-derive or re-file it.
  The order's *operational* half ("re-run the chain so CHAIN.json carries the current shape")
  still needs a live run to actually pick up the previously-missed rows -- that is a run, not a
  code defect.

### Checked and clean

- `write_result`'s unconditional `edges`/`fit_error`/`unanswered` fields, `landed()`'s
  json-round-trip comparison, and the `_land_harvest`/`refresh_continuity` compare-and-swap
  writers all match their extensive doc comments on re-reading against the source; no
  discrepancy found between what they claim and what they do.
- `adjudicate_mutuals`'s epoch re-keying (only the winner of each direction gets an
  epoch-suffixed node) does correctly dissolve the mutual-pair contradiction rather than merely
  relocating it -- traced through the Goku/Mercenary Tao worked example by hand.
- `_corpus_root_state`/`_held_root` prune-hold logic for an unlistable `data/readfeats` or
  `data/feats` root: verified the held root's keys really are excluded from the prune loop
  (line 455) and that `_RECIPE_KEY` is excluded from both the prune and the held-root check.

## feats.py

### Checked and clean

Read in full; this module is unusually heavily audited already (every major function's
docstring cites the specific measured incident that shaped it). I did not find a new defect in
the categories the brief asks about first:
- Every module-level shared-state dict written from worker threads (`_RATE_LIMITED`,
  `_CAP_BOUND`, `_UNIT_DROPS`, `_UNIT_LONGEST`, `_STALE_GATE`, `_UNCACHED`) is correctly
  guarded by `_COUNTS_LOCK` at its read-modify-write site; `_BACKOFF`/`_STRIKE` are guarded by
  the per-domain `_HOST_LOCKS`.
- `_units()`'s length gate boundaries (`n<=20` short, `n>=400` long, yield only `20<n<400`)
  are consistent with the "same `20 < len(s) < 400` gate" the comments claim -- no off-by-one.
- `resolve_hosts`'s override/cache/corpus-evidence/guess-and-verify cascade: traced the
  for/else at lines ~1172-1185 by hand; a clean negative (404) is the only path that can write
  `known[src] = None`, an undetermined probe or an empty candidate list is routed to `unprobed`
  and left OUT of the map (never silently cached as absence), matching the extensive comments.
- `mine()`/`by_axis()`'s length-filter and gate-rejection counters are each tallied once per
  call site (not double-counted across the two functions), matching the "gate is not once, per
  gate" comment.
- The 2026-09-14 insertion of the module-level eaten-escape guard (lines 46-48) duplicates the
  pre-existing guard already in this file at lines 819-829 (predating tonight's run). Purely
  redundant, not a defect, and covered by the brief's "do not report the guard insertion"
  instruction -- noted here only so it isn't independently re-filed.

## estate.py, withdraw_chapters.py, coverage.py, cosmography.py, context_budget.py,
## scale_theories.py

### Checked and clean

No new defects found after a full top-to-bottom read of each. All six are fail-closed on every
read/parse/stat failure I traced (unreadable config, corrupt cache, vanished file mid-scan,
denied atomic replace), and every cap/truncation I checked prints its own remainder or refuses
outright rather than silently shortening a roster, consistent with Hard Rule 0. Specific checks:
- `estate.py`: `_effective_ext`'s backup-marker peel, the TOCTOU-guarded `getsize` retries, and
  `charter()`'s table-driven erratum checks (Supercluster/Filament-Void/Hyperverse/M0-M2) all
  read the charter's live tables rather than testing for a bare substring, matching the "each row
  is the test its own text describes" comment.
- `withdraw_chapters.py`: the `moved[sub] += 1` / `extra += 1` counters sit outside their
  `if a.go:` blocks in both the catalogued-move and stray-move loops, so a dry run reports
  "would move" counts under a label that says "moved" -- this is documented, deliberate preview
  behaviour (see the item-(a) comment on the stray-sweep block) and not a new defect; the
  bottom-line "DRY RUN -- pass --go to move" disambiguates it.
- `coverage.py`: `state_of()`'s STRICT PRECEDENCE (CITED > READ > NO PAGE > UNREACHABLE > NOT
  ATTEMPTED) traced by hand across multiple orderings of candidate files; never downgrades a
  stronger already-found state.
- `cosmography.py`: `SIZE_CLASSES`/`SIZE_CLASS_MAX_GALAXIES` ceilings hold even accounting for
  floating-point rounding (`2e11 * (1/2e11)` == `0.9999999999999999`, still `<= 1.0`) -- MINOR's
  ceiling does not spuriously trip.
- `context_budget.py`: `content_budget_chars`/`feats_block_budget` arithmetic (prose ratio for
  scaffolding, content ratio for JSON, `JOB_OVERHEAD_CHARS` subtracted before the
  `METADATA_INFLATION` division) checked term-by-term against the header's worked numbers.
- `scale_theories.py`: unwired and unread by anything else in `src/` (confirmed by grep, matching
  its own docstring); `surviving_theory()`'s arity assertion and `bulk_export_beta`'s floor at
  `resident_mass_kg <= mass_kg` both hold.

QUESTIONS: 0
record(): ok
