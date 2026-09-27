# sweep65 batch15 — audit

Scope: every module below read in full, start to finish, sequentially, in chunks. No sampling,
no grep-only skimming.

  - src/read.py              1720 lines — read in full (4 chunks: 1-450, 451-900, 901-1350,
                              1351-1720)
  - src/escalation.py        1445 lines — read in full (4 chunks: 1-400, 401-800, 801-1200,
                              1201-1445) [SAFETY-CRITICAL]
  - src/corpus_db.py         1053 lines — read in full (3 chunks: 1-400, 401-800, 801-1053)
  - src/ingest_doc.py         702 lines — read in full (3 chunks: 1-350, 351-700, 700-703)
  - src/prose_gate.py         545 lines — read in full (2 chunks: 1-300, 301-545)
                              [SAFETY-CRITICAL]
  - src/burgs.py              442 lines — read in full (1 chunk)
  - src/grounding.py          361 lines — read in full (1 chunk)
  - src/tempus.py             297 lines — read in full (1 chunk) [NEW TO THIS BATCH]

Total: 6,565 lines across 8 modules, all read.

## Roster change from sweep64

Batch 15 carried `halo.py`/`module_index.py` last sweep; this sweep swaps those out for
`tempus.py`, per this run's assignment. `tempus.py` had no prior sweep64/63 batch15 audit to
cross-check, so it was read cold, and `state/workorders.json` was searched for `tempus.py` before
starting (one hit, `7099a092abd3`, an OWNER-rung question about `tempus.apparent_lag_years` /
`tempus.band_resolution` / `tempus.loop_report` having no production caller besides the battery —
not re-litigated here, already open at OWNER).

## Prior-audit cross-check

`handoff/sweep64/AUDIT_batch15.md` covered seven of these eight modules (all but `tempus.py`) and
found exactly two VERIFIED findings, both since addressed:

1. `read.py`'s `_names()` fallback (M119, curly-vs-ASCII apostrophe folding) — checked live this
   sweep by extracting the exact fallback logic standalone and running it against the same
   `MSM-07N Ram Z'Gok` case sweep64 used. The current code (read.py:282-291) now folds the
   separator class through `_QMAP` on *both* sides (`t.translate(_QMAP)` when building the
   character class, and `low.translate(_QMAP)` when testing the sentence) — confirmed live:
   curly-apostrophe-in-catalogue vs. ASCII-apostrophe-in-prose now matches (`True`), which it did
   not before the fix. Fixed as sweep64 described; not re-filed.
2. The P8 meta-language `stub(s)`/`*wiki*` over-match — filed against `src/pipeline.py`, outside
   this batch's module list both then and now; not re-verified this sweep since it is not one of
   the eight assigned files (still true today: `stub(s)` remains in this batch's grep-visible
   surface only via that same off-batch file, not touched here).

Also cross-checked: sweep64's "Questions" section noted `escalation.py`'s `clear()` dead-store
(`landed = False`, line 1274 in the current file) as an owner question already on record — not
re-filed, matches the current source exactly.

## Method

Full sequential read of every line of every module, chunked through the Read tool. Two specific
mechanisms were verified by execution in a scratch copy outside the repo
(`%TEMP%/verify_names.py`, `debug_names3.py`, `verify_burgs.py` — pure logic extracted from the
modules, no import of the modules themselves, no mutation, no drill, no network):

  * `read.py`'s `_names()` punctuation-fallback regex (the sweep64 fix), fuzz-checked against
    curly-apostrophe / ASCII-apostrophe / dropped-apostrophe / hyphen-vs-space variants of one
    catalogued name.
  * `escalation.py`'s `_by_a_person_at_the_cli()` frame-depth assumption (`sys._getframe(2)`),
    reproduced standalone to confirm `main()`'s documented choice to call
    `resume_subsystem_verdict()` directly rather than through the `resume_subsystem()` wrapper is
    load-bearing and correctly wired — going through the wrapper does put the wrong function name
    at frame 2, exactly as the in-file comment warns, so calling the verdict function directly
    from `main()` is not a stylistic choice, it is required for the person-check to fire correctly.
  * `burgs.py`'s `class_histogram()` / `_rank_at_or_above()` closed-form-plus-correction, fuzzed
    against a brute-force per-rank simulation over 20,000 random `(p1, n)` pairs spanning boundary
    values around each `CLASSES` threshold and around `HAMLET_FLOOR` — zero mismatches.

## Findings

None. No CONFIRMED or SUSPECTED defects were found in any of the eight modules beyond what prior
sweeps already found, fixed, and left as commented history in the source. This batch's module set
is unusually well-picked-over: all seven carried-over files were audited clean by sweep64 (after
two real findings in sweep63 and earlier), and the one new file (`tempus.py`) is short, has no
mutable state, no file I/O of its own, and every arithmetic path traces cleanly to the docstring's
stated derivation (checked by hand: `rung_description_length` gives 0 at M0 by construction as
claimed; `band_resolution`'s M10 saturation branch correctly reuses the M9→M10 width rather than
inventing a ceiling edge; `is_present_at`'s `>=` direction matches the "lower rung sees a larger
now" consequence stated in `concordance_now`'s own docstring, verified by tracing both directions
by hand).

## Questions (not findings)

None new. The two standing questions touching this batch (`escalation.py:1274`'s dead store, and
`tempus.py`'s three battery-only public functions under order `7099a092abd3`) are already on
record at OWNER and are not re-litigated here per the brief's instruction not to re-file anything
with an open work order.

## Cleared

Read in full and found sound: `read.py`'s transport ladder (Cascade-quick / GPU / Cascade-backoff
ordering across `auto`/`cascade`/`ollama` modes), the adaptive concurrency gate and its per-thread
re-entrancy guard, `priority()`'s deep/light interleave (terminates correctly, drains both lists),
`_queue_row`'s memo/ownership logic, and `read_entity`'s cache-only-on-full-read discipline;
`escalation.py`'s full rung ladder, the halt/stop compare-and-swap-plus-lock write paths, the
fail-open halt-lock vs. fail-closed halt-read asymmetry, `_by_a_person_at_the_cli`'s frame check
(verified live, see above), and the OWNER-only `clear()`/`resume_subsystem_verdict()` gating;
`corpus_db.py`'s three-state sentinel handling (`SPINE_LOOKUP_FAILED`/`HOST_LOOKUP_FAILED`/
unreadable), its mtime-plus-deletion freshness check, and the CANNED query set's floor handling
(`worst_cited` vs. `below_floor_cited` correctly split at `entries>=40` with no NULL-sorts-first
trap); `ingest_doc.py`'s resumable chunk cursor, its oversize-page re-splitting (mirrors
`read.py:_local_carded`), and `record_path`'s ambiguous-match refusal; `prose_gate.py`'s layer
1-4c chain including `section_shortfall`'s extra-block double-charge (an over-length block
correctly cannot reach 1.0) and `instrument_shortfall`'s being/non-being branching (traced by
hand against all four `(marked, scored/excused, being)` combinations); `burgs.py`'s rank-size
derivation (fuzz-verified, see above); `grounding.py`'s uncapped full-field confidence
denominator; and `tempus.py`'s institutional-simultaneity and prescience-pricing functions (no
mutable state, all derivations traced to their stated source).

## Coverage recorded

Recorded via `sweep_plan.record('run65', [...], batch=15)` for all eight modules listed above,
all read in full.
