# sweep46 — batch 03 audit

`src/pipeline.py` · `src/threads.py` · `src/withdraw_chapters.py` · `src/burgs.py` ·
`src/scope.py` · `src/tuning.py` · `src/catalog.py` — ~5,590 lines.

**Read in full, every line of all seven files.** No sampling, no skimming, no partial read.
Line counts confirmed against the files: pipeline 3,178 · threads 671 · withdraw_chapters 519 ·
burgs 432 · scope 337 · tuning 286 · catalog 167.

Read-and-report only. **No source file in `src/` was edited.** No banned tool (`drill.py`,
`mutate.py`, `allsweep.py`, `publish.py`) was run, and no live crawl or fetch was made.

---

## The two named changes

**`pipeline.write_record_catalogue`'s `(name, type, description)` pairing key (order
b418b8b3be54).** Read the whole function end to end (`pipeline.py:742-926`) plus its helper
`_entry_pair_key` (:693-722). The triple-key pairing, the ambiguous-group fallback that carries
surplus disk rows forward whole rather than mis-attributing a judgment, the per-field
`CATALOGUE_CURATED_FIELDS` gate, and the non-`entries`-key preservation are all consistent with
the docstrings' own measured claims (905 duplicated-name groups; 880 fully separated, 2 partial,
23 refused). `_entry_pair_key` forces every field to a hashable primitive before using it as a
dict key, which closes the exposure the old name-only key shared. No caller of this function in
the batch (`pipeline.py` itself is the only module in the batch that calls it) does anything
with its `True`/`False` return other than what the surrounding docstrings already describe as
gated correctly (`_landed`).

**`scope.ProbeUnread` (order 6e2dab4c3981).** Read `scope.py` in full. `scope_for` raises it for
any `feats.api` outcome that isn't `ok` or the one clean negative (`http-404`), and again when a
search returned titles but `feats.fetch` came back empty. `build()` catches it explicitly and
leaves the host unscored (not cached as an empty verdict) rather than falling into the generic
`except Exception` branch below it. `main()`'s `--probe` and `--host` paths both catch it too and
print `NOT READ: ...` rather than `null`. `ceiling_for()` — the one function in this module other
code actually calls for a value — reads the on-disk cache only and never calls `scope_for`
itself, so it cannot raise `ProbeUnread`; nothing in this batch needs to catch it. Grepped the
whole `src/` tree for callers of `scope_for` / `scope.build` outside `scope.py` itself: only
`magnitude.py` (already fixed per the brief) and `drill.py`'s own fixture-driven nets. None of
the seven files in this batch call `scope_for` directly.

---

## What this batch found

**Nothing new.** All seven modules are exceptionally hardened — each carries the scar tissue of
several previous sweeps (order numbers, measured-not-theorised comments, drill nets) and every
mechanism I traced (the two-writer record contract, the T1/T2 thread derivation, the withdrawal
tool's file-state/collision guards, the rank-size settlement math, the regime/worker tuning, the
catalog CLI's rc handling) already answers "could not measure" with a refusal or a logged
open-unit rather than a fabricated value. I looked specifically for the four failure classes in
the brief (fabricated verdicts, silent data loss, unmarked caps, checks that cannot fail) across
every line and did not find a live one in this batch.

**One pre-existing question, confirmed still open and correctly filed — not re-filed here.**
`pipeline.synthesis_blocks` (:1409-1461) builds phase-1 nomination blocks as
`blocks = ([with_feats[i:i+14] ...] or [rest[i:i+14] ...])`. This is a Python `or`-fallback: if
`with_feats` (entries with a mined feat) is non-empty, `rest` (entries with no mined feat) is
never nominated at all, however large it is — the moment a source has even one feat-bearing
entry, every feat-less entry is dropped from ceiling nomination entirely. The docstring's own
"the cap goes ... the tail is now REACHED rather than discarded" claim only holds for the
all-feat-less case; the mixed case (which is the common one) still drops the tail, silently, with
no marker. This reads exactly like a Hard-Rule-0 shaped finding — until `drill.py:1861-1868`
(`the_feat_bearing_path_really_is_untouched`'s docstring), which names the identical short-circuit
by name, in the same words, and rules explicitly that it is **an owner question, not a finding**:
the 2026-08-25 ruling was scoped to the feat-less fallback only, says nothing about the mixed
case, and "it is not a drill's place to decide it." It is tracked as order `a5de2dcb9447`
(`state/workorders.json`, handler RUN, severity MINOR, open since sweep39-batch02) — confirmed
present and still open. I did not re-file it: nothing about the code changed since that order was
written, and refreshing an unstale, correctly-scoped order would only reset its `last_seen` for
no reason. Flagging it here per the brief's instruction to treat an ambiguous-design case as a
question rather than manufacture a finding out of it.

No other `[:N]` slice, cache, or short-circuit in the batch showed the same shape.

---

## Coverage

Recorded via `sweep_plan.record('run46', [...], batch=3)` for all seven modules — every one was
read end to end, in full, this session.
