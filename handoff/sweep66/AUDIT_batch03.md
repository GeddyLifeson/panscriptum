# sweep66 batch03 audit

Auditor for batch 3 of maintenance run #66 (2026-09-27). Read-only throughout: nothing under
`src/`, `data/`, `state/`, `output/`, `prompts/`, `reference/` or the repo root was edited,
created or deleted this session, other than this file and the one permitted
`sweep_plan.record(...)` call. No job, drill, sweep, publish, mutate, generate, crawl, overwatch,
foreman, verify_math or pipeline invocation was run. No subagents were spawned.

## Scope, read in full, start to finish, no sampling

- `src/pipeline.py` — 3,686 lines (read in eight chunks: 1-500, 500-1000, 1000-1500, 1500-2000,
  2000-2500, 2500-3000, 3000-3500, 3500-3686 — full coverage 1-3686)
- `src/weave_index.py` — 731 lines (one pass)
- `src/feats_index.py` — 633 lines (one pass)
- `src/reference.py` — 497 lines (one pass)
- `src/retry_synthesis.py` — 379 lines (one pass)
- `src/events.py` — 350 lines (one pass)
- `src/ledger.py` — 220 lines (one pass)
- `src/repass_bands.py` — 214 lines (one pass)

Total: 6,710 lines across 8 modules, all read in full this session.

## Method

`CLAUDE.md` read first for doctrine (Hard Rule -1 escalation/halt, Hard Rule 0 no caps ever,
fail-closed, "a check that cannot fail looks exactly like a check that passed"). Every module
read top to bottom before any conclusion was drawn.

## Prior-audit cross-check

This exact eight-module roster splits across five sweep65 batches. Each was read in full before
writing anything here:

- **`handoff/sweep65/AUDIT_batch03.md`** covered `pipeline.py`, `weave_index.py`,
  `feats_index.py`, `reference.py` (plus `recover_folder_records.py`, `wh40k.py`, `physics.py`,
  not in this batch). It filed one CONFIRMED-by-execution finding: `pipeline.write_record_
  catalogue`'s `unpaired[:max(len(dgroup)-len(fgroup),0)]` slice could keep a collision/duplicate
  row over a disk-only row with zero ambiguity, silently dropping the unambiguous entity.
  **RE-VERIFIED AGAINST CURRENT SOURCE AND FOUND FIXED.** `pipeline.py:1089-1098` now splits
  `unpaired` into `lone` (disk rows the fresh cast does not carry under that key at all) and
  `clashing` (rows colliding against a real fresh cast) *before* building `unpaired = lone +
  clashing`, so a lone, zero-ambiguity row is now ordered first in the slice and is the last kind
  of row to be dropped. The comment at `pipeline.py:1080-1088` attributes the fix in-line to
  "sweep65 batch03". Confirmed by reading the surrounding code, not by trusting the comment: the
  `lone`/`clashing` split and the `[:max(len(dgroup)-len(fgroup),0)]` slice are both present and
  match the fix the prior audit's own "Proposed fix" section asked for. Not re-filed.
  It also filed one CONFIRMED stale-comment finding in `wh40k.py` (out of this batch — not
  re-checked here) and carried forward the `physiology` field finding (see below) and one
  QUESTION about `ENTRY_SCHEMA`'s bare `category: {"type": "integer"}` (also carried forward
  below, unchanged).
- **`handoff/sweep65/AUDIT_batch06.md`** covered `retry_synthesis.py`, `events.py` (plus seven
  modules not in this batch). Zero new findings; carried forward two items, both re-verified
  below as still true and both restated as QUESTIONS, not re-filed.
- **`handoff/sweep65/AUDIT_batch09.md`** covered `ledger.py` (plus eight modules not in this
  batch). Zero new findings; cleared `to_standards`/`from_standards`/`cross_rate`/`work_value`
  round-trip arithmetic and `assay_to_standards`'s M10 top-band extrapolation. Re-verified below;
  holds.
- **`handoff/sweep65/AUDIT_batch16.md`** covered `repass_bands.py` (plus eight modules not in
  this batch). Zero findings — cleared the write-then-gate-on-`write_record()` pattern, the
  preserve-not-destroy `scale_note_rejected` handling, and uncapped SURVIVORS/DEMOTED rosters.
  Re-verified below; holds.

`state/workorders.json` (56 entries) was searched for every module name and for each finding
candidate before writing anything down, per the brief. Two carried-forward items below already
have open orders on file and are cited by id rather than re-argued:

- **`physiology`** (pipeline.py ENTRY_SCHEMA required-but-never-merged field) — **already open:
  order `0aceab8473e1`**, OWNER rung. Re-verified against current source: `grep -n physiology
  src/pipeline.py` still returns exactly the prompt text (`:1975-1980`), the schema comment
  (`:2065-2071`), the schema property (`:2071`) and the `required` list (`:2078`); the
  result-processing loop in `phase_entrypass` (`:2361-2454`, read in full this session) still
  never reads `res.get("physiology")`; `MERGED_ENTRY_FIELDS` (`:841-849`) still omits it. Unfixed,
  already on file, cited only.
- **`ledger.py`'s four dead functions** (`cross_rate`, `to_standards`, `from_standards`,
  `assay_to_standards` — zero production callers, only the battery) — **already open: order
  `7099a092abd3`**, OWNER rung, as one line item of a thirteen-function list spanning `assay.py`,
  `tempus.py`, `ledger.py` and `cosmography.py`. Re-verified: still true of current source, and
  `ledger.py`'s own in-line comments (`:74-81`, `:108-112`, `:129-134`) already record this
  explicitly as "REPORTED DEAD, NOT DELETED" per the same owner ruling the order cites. Not
  re-filed.

## Findings

**Zero new findings this batch.** No fail-open branch, no tautological/unfalsifiable check, no
Hard-Rule-0 cap or silent truncation, no wrong-variable/off-by-one/inverted-condition bug, no race
on a shared state file newly discovered, no comment/code mismatch, no silently swallowed exception
manufacturing a false negative, and no dead code a comment wrongly claims is live, was found in
any of the eight modules beyond what is already on file above. One prior finding (the
`write_record_catalogue` unpaired-row drop) is now CONFIRMED FIXED, reported under "Prior-audit
cross-check" rather than repeated here since it is not a currently-standing finding.

## Questions (possible deliberate design — not findings; owner decides)

Both restated briefly per the brief's instruction not to re-derive what a prior audit already
argued at length; neither is new.

1. **`retry_synthesis.py:375`**, `return 0 if landed else 1`. The exit code tracks only whether
   the *last* save to `data/SYNTHESIS_RETRY.json` landed, not whether every named source was
   actually rescued — a run in which several sources print `STILL FAILING` but every save lands
   still exits 0. Reading A: correct by design, since a per-source model miss is ordinary and
   self-healing (retried next run), and folding it into the exit code would make a routine
   partial outcome look like a failure. Reading B: an automated caller gating on this exit code
   cannot currently distinguish "fully rescued" from "half the sources are still stranded" without
   parsing stdout. (Carried forward verbatim from sweep65 batch06's Question 1; re-verified line
   number and behaviour against current source, unchanged.)
2. **`pipeline.py` `ENTRY_SCHEMA`'s bare `category: {"type": "integer"}`**, with no `enum`/
   `minimum`/`maximum`, unlike `topic` and `subroom`'s constrained enums. The `category_rejected`
   mechanism (`pipeline.py:2371-2383`) exists precisely because the schema cannot constrain the
   range, so an out-of-range value is the expected, handled path rather than a rare edge case.
   Whether the schema should additionally carry `"minimum": 1, "maximum": len(CATEGORIES)` to
   tighten the local-model arm (the cloud arm's exposure is unaffected either way, since cloud
   models do not honour JSON-schema constraints per `_pool_answer_usable`'s own docstring) is a
   design choice for the owner, not a defect. (Carried forward from sweep64/sweep65 batch03,
   re-verified unchanged.)

## Everything else checked, no new findings

- **`pipeline.py`** (full read, 1-3686): the two-writer contract (`write_record` /
  `write_record_catalogue`) including the now-fixed `lone`/`clashing` split; the compare-and-swap
  state merge (`_merge_state`/`_fold_state`/`save_state`); `ask_pool_first`/`_pool_answer_usable`'s
  cloud-then-local routing and shape/accept gating; `valid_scale_note`'s four-gate scale-evidence
  test (magnitude/act-upon-object/patient/reputation); `synthesis_blocks`'s feats-first-then-rest
  uncapped block construction (the `or`→`+` fix and the removed 14-entry cap, both still correct);
  `batch_settled`/`entry_settled`'s resume discipline; every phase function's absent-vs-corrupt
  handling (phases 5, 6, 7, 8 each individually traced: `FileNotFoundError` and generic `Exception`
  are consistently distinguished, and a corrupt phase input always leaves the phase open rather
  than closing over an empty/wrong result); `main()`'s exit-code discipline (`sys.exit(main())`,
  explicit 0/1/3 on every path, `--phase` range validation, the pointer-past-end-with-open-phases
  guard). No new defect.
- **`weave_index.py`** (full read): `_records_sig`'s per-file-vs-directory-level fail-open split
  and its `unstattable` bookkeeping; `designations()`'s cache-on-success-only discipline and its
  refusal to cache a read failure; `norm`/`continuity_of`'s designation-as-suffix fold; the
  `stale`/`behind` staleness split (order `9e884802918e`) with its worked truth table still
  matching current source; the uncapped candidate/bucket reporting and the disclosed
  top-18-of-N ranking in `main()`. No new findings; matches sweep65 batch03's account exactly.
- **`feats_index.py`** (full read): `host_to_sources` raising (never caching an empty map) on an
  unreadable `WIKI_HOSTS.json`; `load_index`'s unreadable/collided fault tracking, counted rather
  than silently subtracted from the denominator; `source_binding`'s bound/pages/doc/unbound/
  unknown classification; `feats_for_source`'s within-source entry-name-collision tracking
  (`_ENTRY_COLLISIONS`) and its last-writer-wins-but-recorded discipline; `audit()`'s
  `files_seen`-denominated join rate. No new findings.
- **`reference.py`** (full read): `compute`/`card`/`citation`'s worksheet-to-Assay pipeline;
  `shelfmark`'s could-not-read-vs-genuinely-unknown-rung distinction (`nav_unreadable` marker) and
  its length-clamp guard against a future non-3/4-length `tier_key`/`lower_rungs`; `main()`'s
  calibration-gates-the-exit-code fix (`calibrated = not outside`, folded into the return value
  alongside the write-landed verdict); the `--compare` path's `(host, entity)`-keyed lookup into
  `ASSAYS.json` and its pre/post-`b03f2ab9951a` "not recorded" vs. fabricated-zero handling. No
  new findings.
- **`retry_synthesis.py`** (full read): `save_side`'s re-read-merge-then-write discipline and its
  returned (merged, landed) pair, both consumed correctly by `main()`'s loop; `stranded_sources()`'s
  condition-based (no-synthesis-with-entries) rather than cause-based (failed-set-only) selection;
  `synthesise()`'s five points of deliberate parity with `pipeline.phase_synthesis` (block
  construction, transport, acceptance gate, evidence-validity gate, evidence storage cut), all
  taken from `pipeline` rather than restated; `do_merge()`'s `merged`/`skipped`/`denied`/`unmerged`
  four-way accounting and its `1 if (denied or unmerged) else 0` exit code. No new findings.
- **`events.py`** (full read): `_looks_like_a_sentence`'s two mechanical, deliberately-incomplete
  refusal rules (terminal punctuation, word count) with the stale third-rule comment already
  removed per its own in-line history; `_fragments`'s joiner-based split requiring both sides to
  independently pass the same shape rule; `parse()`'s heading and no-heading event dedup via
  `seen`, and the nearest-preceding-level-2-heading age lookup; `shelf_positions`'s header-match
  fix (the decoy `.replace("Now ", "")` removal). No new findings. (Note: the open OWNER question
  about `unearned_instrument()`'s trailing-parenthetical strip that a raw grep for "events.py"
  surfaces in `state/workorders.json` is filed against `src/prose_gate.py`, confirmed by reading
  the order's own `where` field — it is not a finding against this module and is not carried
  forward here.)
- **`ledger.py`** (full read): `to_standards`/`from_standards`/`cross_rate`/`work_value` round-trip
  arithmetic, hand-checked; `assay_to_standards`'s M10 top-band extrapolation
  (`hi = lo * (lo/prev)`, confirmed `hi > lo` since `prev < lo` for every populated band, so
  `ruin_score` still moves the top-band answer rather than collapsing to a zero-width range);
  `currency_status`'s unlisted-vs-deliberately-non-convertible distinction. No new findings;
  matches sweep65 batch09's account.
- **`repass_bands.py`** (full read): the write-then-gate-on-`write_record()` pattern (`touched`/
  `denied` both counted, `denied` folded into the exit code and into the closing message);
  the preserve-not-destroy `scale_note` demotion (`scale_note_rejected` set via `_stored_cut`
  before `scale_note` is cleared, keeping `pipeline.ENTRY_REJECTION_COMPANIONS`'s contract intact
  rather than handing `write_record` a false "rejection no longer stands" signal); the SURVIVORS
  and DEMOTED rosters and the source-ceiling demotion roster all genuinely uncapped. No new
  findings; matches sweep65 batch16's account.
- No regex/escape corruption in any of the eight modules — each of the six that carry the
  `_BAD_CHARS` self-check (`pipeline.py`, `weave_index.py`, `feats_index.py`, `reference.py`,
  `events.py`) passes it at import time, verified by reading the check itself rather than trusting
  its presence; `retry_synthesis.py` and `ledger.py` carry no such check and none of their regex
  literals showed signs of escape corruption on inspection (`ledger.py` in fact contains no
  regexes at all).

## Coverage

Recorded via `sweep_plan.record('run66', ['pipeline.py', 'weave_index.py', 'feats_index.py',
'reference.py', 'retry_synthesis.py', 'events.py', 'ledger.py', 'repass_bands.py'], batch=3)` for
all eight modules above, each read in full this session — see reply for whether it landed.
