# run46 batch 5 audit

Modules read end to end (every line): `src/standards.py` (2247), `src/generate.py` (834),
`src/gpu_lane.py` (684), `src/address_space.py` (525), `src/feats_index.py` (437),
`src/style_audit.py` (338), `src/recover_folder_records.py` (288), `src/ledger.py` (172),
`src/compress_store.py` (149). ~5,674 lines total, matching the batch assignment.

Method: read the executable line, not the comment above it; every candidate finding was
checked against source before being written up here. No file was sampled or capped.

## Overall impression

This is an unusually hard-audited batch. All nine modules carry dense, dated commentary
recording prior findings and their fixes (green-by-absence, `_dropped`/UNMEASURED handling,
atomic-write verdict gating, Windows PID-liveness idiom, caps removed under Hard Rule 0,
etc.). The great majority of the patterns this sweep is instructed to hunt for --
fabricated measurements, silent data loss, caps-then-truncation, checks that cannot fail --
are already named, fixed, and cross-referenced by order id in these files. I verified a
sample of those historical fixes against the live code rather than trusting the comments
(per the run's own warning about comments recording past, not present, behaviour) and found
them correctly reflected in the executable lines.

`compress_store.load()` (priority 2 in the brief) does refuse a blob whose content hash
disagrees with its filename -- verified at compress_store.py:139-148, a real corruption
check, not decorative.

## Findings filed

1. **GENERATE_COVERAGE_CHECKS_FALSE_POSITIVE_ON_THINKING_TEXT** (order `5bbd4b3376fe`,
   OWNER, MAJOR). `_covered()` (generate.py:246-259) and `_deed_traced`/`_deed_shortfall`
   (262-293) decide whether an entry/deed was actually written by testing for its name or a
   distinctive word IN THE FULL RESPONSE TEXT, which carries no think-tag stripping (per the
   task's own context and order 342ccfafa4a4). A thinking model narrating its plan before
   writing ("now for Entity X...") will very plausibly satisfy both checks by mentioning
   every entity/deed in its reasoning preamble, even if the real Entry-Template prose for
   that entity was never emitted -- collapsing Hard Rule -1's three-layer defence
   (`_covered` -> retry -> `prose_gate.assert_block_complete`) to one layer (Layer 4 alone)
   for exactly the failure class Layer 3 exists to catch. This is additive to the existing
   order `3859043e365e` (which reasons about context-budget squeeze and names only
   `_covered`, not the feats-side `_deed_traced`); the new order explains the FALSE-POSITIVE
   mechanism and names the second guard. Not a live defect -- `prose_enabled` is shut.

2. **FEATS_INDEX_EXCEPTION_TEXT_CUT_WITH_NO_MARKER** (order `70f5e5150f8b`, LOCAL, MINOR).
   `feats_index.host_to_sources()` builds its RuntimeError with `str(e)[:110]`
   (feats_index.py:164) -- an unmarked hard cut on the underlying exception text, the same
   shape already fixed elsewhere in this tree (standards.py:174-181, and the `[:40]` reason
   cut in catalogue_models.py cited at standards.py:612-622), both repaired by collapsing
   whitespace instead of slicing. Low blast radius (only fires when
   `data/WIKI_HOSTS.json` itself cannot be read), one-line fix.

## Questions / observations not filed as findings

- `feats_index.feats_for_source`'s `entries_by_norm` dict is keyed on a normalised name
  (non-unique identity) -- but this is explicitly the documented, deliberate behaviour
  (collision is counted, named, and reported via `_ENTRY_COLLISIONS`/`audit()`, and the
  module's own comment states "last-writer-wins is NOT changed here... a curatorial call").
  Not a finding.
- `recover_folder_records.py`'s `roll_by_name = {r["name"]: r for r in roll}` assumes roll
  source names are unique. This is the same identity every other pipeline stage (WIKI_HOSTS,
  spine addressing) already depends on being unique; no evidence found of an actual
  collision, so not filed.
- `standards.py`, `gpu_lane.py`, and `address_space.py` show no unfixed instance of the
  three priority patterns (fabricated measurement standing in for "could not measure",
  silent data loss, unmarked truncation). Every `[:N]` slice remaining in these files is
  either a deliberate short-summary-plus-uncapped-full-list pattern (e.g.
  `ChapterRefused.lists`, `_unearned[:5]`/`missing[:8]` beside their uncapped keys) or a
  console preview genuinely marked as a preview (`generate.py --dry-run`'s `pending[:3]`).

Coverage recorded via `sweep_plan.record('run46', [...], batch=5)`.
