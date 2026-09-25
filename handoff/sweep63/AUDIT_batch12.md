# sweep63 batch12 audit

Scope, every module read in full, start to finish, no sampling:

  - src/magnitude.py          1989 lines
  - src/chain.py              1262 lines
  - src/threads.py            1022 lines
  - src/manifest_builder.py    671 lines
  - src/handbuilt.py           518 lines
  - src/pantheon.py            432 lines
  - src/events.py              350 lines
  - src/cachekey.py            217 lines
  - src/module_index.py        192 lines

Total 6653 lines. Read-only throughout: nothing under src/, data/, or state/ was edited, and
nothing was run except a grep of handoff/sweep61/ for these module names, a read of the prior
audits that turned up, and the coverage-recording call at the end.

## Method

Skimmed CLAUDE.md's doctrine first (Hard Rule -1 escalation/halt, Hard Rule 0 no caps, fail-closed,
"a check that cannot fail looks exactly like a check that passed"). Then grepped
handoff/sweep61/*.md for each of the nine module names before reading any source, and read every
prior audit that named one: AUDIT_batch03.md (cachekey.py, module_index.py), AUDIT_batch04.md
(events.py), AUDIT_batch09.md (manifest_builder.py, alongside codewatch.py's -X/-W flag bug, which
is not in this batch's files), and AUDIT_batch12.md (magnitude.py, chain.py, threads.py,
handbuilt.py, pantheon.py, paired there with a different four files than this batch pairs them
with). None of those reports left an open, unresolved finding against any of these nine files.
batch09 recorded one QUESTION against `manifest_builder.load_record`'s exact-match early return
(assumes no two record filenames normalise to the same string) and batch12 recorded one QUESTION
against `threads.build()`'s widened `known` set touching `siblings` as well as T1/T2 resolution.
Both are reproduced below only as still-open background, not re-filed as findings.

All nine files continue the pattern the sweep61 reports already describe: essentially every guard,
truncation risk, and tautology candidate in this batch carries an inline comment citing the prior
order/sweep that found and fixed it, with a measured before/after. `magnitude.py`'s five numbered
guards (verbatim, relevance, subject, saturation, quantity) each carry their own failure history;
`chain.py` carries roughly 25 named orders on citation/mutual-pair/harvest-index correctness;
`threads.py` documents its own four "quiet one" refusals and a deliberately-reasoned single `[:2]`
slice; `manifest_builder.py`, `handbuilt.py`, `pantheon.py`, `events.py`, `cachekey.py` and
`module_index.py` each read the same way. Per the brief, defects the code's own comments already
name and show fixed are not re-reported here; the pass looked for what survives that filter.

## Findings

**0 VERIFIED. 0 SUSPECTED.** No new tautology / check-that-cannot-fail, no new fail-open guard, no
new uncommented cap/truncation, no new wrong-variable/off-by-one/unit-mix bug, no new race on a
shared file outside the documented `silence.replace_retry`/CAS paths, no new resource leak, no new
exception path that corrupts state, and nothing that could open `prose_enabled`/`step4_enabled` or
lift a halt was found in this batch beyond what sweep61 already recorded and this pass re-verified
as still resolved.

Specifically checked and found sound (traced by hand, not merely read):
- `magnitude.py`: guard ordering in `assay_entity` (verbatim -> relevance -> subject -> cross-axis
  -> quantity -> saturation, in that sequence on every path that reaches a result); the pool/split/
  local transport fallback ladder for every combination of prompt size and pool availability;
  `pack_feats`-equivalent slice accounting in `_split_assay`/`compose` (`start` is advanced by the
  flushed slice's own length before the slice resets, so span labels stay correct); `_is_score`'s
  bool-exclusion is applied at all six sites that need it.
- `chain.py`: `write_result`'s single writer contract; `_land_harvest`'s compare-and-swap re-read
  and re-apply on a lost race; `adjudicate_mutuals`'s four-way disposition of a mutual pair (both
  dated and differ / one side self-disagrees / only one side dated / neither probed) against every
  branch by hand.
- `manifest_builder.py`: `pack_feats`'s oversized-entity pagination (flush-before-exceeding, span
  arithmetic); the two-writer `unassigned_sources.md` path now atomic and single-source-of-truth
  for the sources list.
- `threads.py`: `edge()`'s two refusals (class, unresolved address) are the only path any T-class
  edge can be built through; `threads_for`'s T4 derivation is per-entry and correctly excluded from
  the normalised (source, category) storage.
- `events.py`: candidate-span shape rules (`_looks_like_a_sentence`, `_fragments`) are mechanical
  refusals only, no resemblance matching anywhere in the parse; heading/no-heading event dedup by
  `seen` is sound.
- `cachekey.py`, `module_index.py`: re-verified against sweep61 batch03's read; unchanged, no new
  candidates found on a fresh line-by-line pass.

## Questions (not findings, carried from prior audits, still open)

- `manifest_builder.load_record`'s exact-normalised-equality early return assumes no two record
  filenames collide once lowercased and stripped of punctuation. Not reproducible against the
  shipped `data/records/` (215/215 resolve today, 214 by exact match), and the function is already
  hardened in three documented rounds against near-miss classes. Unchanged since sweep61 batch09.
- `threads.build()` widens `known` with `annex_codes() | law_codes()` before deriving `siblings`
  (the T2 cohort-family map) as well as `cats_at_code`. Traced again this pass: `cats_at_code` is
  populated only from real per-source codes via `code_of.items()`, so an Annex (`VIII.n`) or Law
  (`X.n`) code cannot manufacture a false T2 sibling unless an actual source is ever shelved under
  one of those addresses, which none is today. Inert, not acted on. Unchanged since sweep61
  batch12.

No other candidate in this batch survived verification. Given the density of prior audit work
already embedded in these nine files -- five of the nine were audited in this exact grouping two
sweeps ago with the same zero-new-findings result -- this batch reads as substantively clean
rather than under-audited.
