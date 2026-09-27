# sweep65 batch11 — audit

Scope, every module read in full with the Read tool, start to finish, sequentially, no sampling
and no grep-only passes:

| module | lines |
|---|---:|
| src/overnight.py       | 2026 |
| src/chain.py           | 1274 |
| src/scout.py           |  835 |
| src/thread_integrity.py|  721 |
| src/tiers.py           |  555 |
| src/citecheck.py       |  458 |
| src/cosmography.py     |  375 |
| src/entity_match.py    |  319 |

Total 6,563 lines, matching `wc -l` over the eight files exactly (verified before reading:
`wc -l` on all eight summed to 6563, and the sum of the chunks actually read below matches it).
Read-only throughout: nothing under `src/`, `data/`, `state/`, `output/`, `prompts/`, `reference/`
or the repo root was edited, created or deleted, except this file and the one permitted
`sweep_plan.record` call. Did not run drill.py, verify_math.py, generate.py, the pipeline,
publish, overnight, chain, mutate, foreman, overwatch or any other job. Did not spawn subagents.

## Method

`CLAUDE.md` read first for doctrine (Hard Rule -1 escalation/halt chain, Hard Rule 0 no-caps,
fail-closed doctrine, "a check that cannot fail looks exactly like a check that passed").

Every prior sweep report naming any of these eight files was located and read before forming a
new opinion:

- `handoff/sweep64/AUDIT_batch11.md` — same batch pairing for `overnight.py`/`chain.py` under a
  different eight-file grouping (with onomast.py, custodes.py, policy.py, axis_correlation.py,
  descending_ladder.py, cachekey.py, repass_bands.py, none of which are in this batch). It filed
  **one SUSPECTED finding**: in `chain.py`'s `harvest()`, a recipe-invalidation reset (order
  `058fa19d4e65`'s `_RECIPE_KEY` mechanism) discarded a HELD corpus root's cached rows on the same
  pass that root went unlistable, while the pass's own stderr message claimed those rows were
  preserved. **RE-VERIFIED AGAINST THE CURRENT SOURCE AND FOUND FIXED.** `chain.py:409-420` (the
  `if _RECIPE_KEY in updates:` branch inside the per-root loop) now detects exactly this
  intersection and prints a distinct, honest message ("its cached rows were discarded with the
  rest of the index... contributes NO contests this pass") instead of the old preserved-rows
  claim. The fix is attributed in-line to "sweep64 batch11, run #64" and matches the finding's own
  suggested remedy. Not re-filed; see Cleared below.
- `handoff/sweep64/AUDIT_batch12.md` — covered `scout.py` and `thread_integrity.py` in full (under
  a different pairing with magnitude.py, generate.py, anchors.py, pick_model.py,
  catalogue_models.py, roll.py). Zero findings against either file; `scout.py`'s CAS
  `_mutate`/`_stamp`/`_unstamp` rotation discipline and `thread_integrity.py`'s DANGLING/asymmetric
  classification were specifically re-verified there and held.
- `handoff/sweep64/AUDIT_batch14.md` — covered `tiers.py`, `cosmography.py` and `entity_match.py`
  in full (with hostcheck.py, health.py, liveness.py, weave.py, coverage.py). Zero findings
  against any of the three; `tiers.py`'s containment scan, `cosmography.py`'s two-ceiling
  `validate()`, and `entity_match.py`'s `qualifier_compatible()`/`candidates()` shapes were
  specifically re-traced and held.
- `citecheck.py` has no prior sweep report on file under any grep of `handoff/sweep6*` — this
  appears to be its first full-module audit pass in the retained handoff history.

`state/workorders.json` (56 entries) was searched for all eight module names before writing any
finding. Hits for `overnight.py`, `chain.py`, `thread_integrity.py` and `cosmography.py` are all
either the standing OWNER-routed "hand-run tools without a halt interlock" policy question
(orders `1e6f99e54b25`/`21c075e5e2d6`/`3099138a82bd`, which names `chain.py main()` explicitly) or
other already-routed/owner-decided items (`d1709d8e757d`, `5bb12b398783`, `a66423722e45`,
`8454be695dc7`, `7099a092abd3`, `a724ec57e0d5` — the last of these, thread_integrity's DANGLING
escalation, is confirmed landed in the current source at line 678's
`_ESC.escalate(_ESC.SUPERVISOR, "THREAD_UNRESOLVABLE", ...)`). None of these six order IDs concern
a code defect this batch could newly confirm or contradict, and none was re-filed. No open
workorder names `scout.py`, `tiers.py`, `citecheck.py` or `entity_match.py` at all.

Each file was then read fresh, start to finish, checking specifically for: wrong logic,
off-by-one errors, inverted conditions, exceptions swallowed where the code claims to fail
closed, a guard that cannot fail, races on shared files, Hard-Rule-0 caps/truncations on any
roster or list, comments asserting behaviour the code no longer has, dead branches, wrong units,
and Windows-specific breakage (WMIC/`py`-launcher/console-window issues).

## Findings

**0 CONFIRMED. 0 SUSPECTED.**

This is, as sweep64's own batch11/12/14 reports also concluded, one of the most heavily
self-audited stretches of this codebase — nearly every non-trivial branch carries an inline
paragraph naming the exact defect it closed, the order id, and often a reproduced
before/after measurement. Reading all eight modules start to finish surfaced no new instance of
any of the priority classes named in the brief, and no regression in anything sweep64 had
verified fixed.

Load-bearing logic specifically hand-traced against the current source rather than taken on the
file's own word:

- **overnight.py**: `_prose_enabled()`'s delegation to `prose_gate.gate_open()` (fail-closed on
  any exception); the three-arm prose-start gate at the cycle's stage-6 block (`drill_rc == 0`
  starts, `== 1` logs a halt-caused refusal, anything else including `None` refuses and logs
  "whether a net is breached is unknown" — verified this is still `==`, not `!=`, so an
  unrecognised/`None` drill result cannot open the gate); `_manager_stopped`'s both-spellings
  ledger check; `_guarded_popen`'s lock-serialised check-then-spawn and its `_PROBE_BLIND`
  sentinel distinct from "already running"; `running()`/`_cmd_is_running()`/`_in_this_tree()`'s
  quote-aware tokenising and `-m`/`-c` refusal; `BUSY_STATUSES`'s inclusion of `rc=17` alongside
  `already-running`/`manager-stopped`/`probe-blind`; the idle-halt branch's fail-closed
  `except Exception: _halted = True` around `escalation.status()`; `preflight()`'s
  identity-by-name lookup of the control-character check label (not identity-by-position); and
  `coverage_snapshot()`'s dual rc-and-mtime staleness check. All hold as documented.
- **chain.py**: the `_RECIPE_KEY` mechanism traced end to end again post-fix (digest computation,
  the now-corrected held-root-vs-recipe-reset interaction at lines 409-420, exclusion from the
  prune loop at 468 and from `refresh_continuity`'s patch loop at 563); `_land_harvest`'s
  compare-and-swap re-read/re-apply on a lost race; `extract()`'s malformed-model-output guards
  (non-dict outcome, bad/out-of-range index, both arms of `_ask`'s cloud/local fallback);
  `adjudicate_mutuals`'s three-way UNPROBED/self-split/dated disposition and its
  every-provenance-sentence (not just the first) epoch check; `write_result`'s unconditional
  `edges`/`unmatched`/`unanswered` persistence on every fit-refusal path; the `SINGLETON_LOCK`
  claim/release pair's own-pid-only release rule. All correct.
- **scout.py**: `_mutate`'s fail-closed unreadable/wrong-shape refusal (never silently `{}`) and
  its thread-and-pid-qualified temp names; `verify()`'s `min(MIN_NAME_HITS, probeable)` floor and
  its separate `probeable == 0` "unverifiable" branch (checked that `_names_in`'s own >3-character
  filter is exactly what makes `probeable` structurally zero in that branch, so the two guards
  cover the two distinct unsatisfiable-check shapes without overlapping incorrectly); `sweep()`'s
  last-attempted-first rotation, its stamp-before-work / unstamp-only-if-still-ours logic (the
  `seen_now.get(src) != now: continue` ownership check), and its archive-before-trim roll-off.
  Sound throughout.
- **thread_integrity.py**: `_charter_codes()`'s three-way absent/corrupt/wrong-shape handling;
  `load_thread_graph()`'s fail-closed `ThreadGraphUnreadable` (never a silently-empty graph) and
  its address-resolution loop (`_charter_codes() | set(code_to_sources)`); `classify()`'s
  `(b, a) in seen` dedup (confirmed the `(a, b) in seen` half really is dead — `pairs` is built by
  `implied_threads` as its only producer and each key is visited once — matching the order that
  already removed it) and the DANGLING/PARTIALLY-DANGLING/IMPLIED-UNRECORDED/RECIPROCAL/
  ASYMMETRIC-LAWFUL/ASYMMETRIC-SUSPECT partition, including the `fwd`/`back` both-directions test
  order `7bffb5634d7a` fixed; `_floor_verdict`'s six-state regression-floor ladder (baseline /
  UNRECORDABLE / held / ratcheted / held-unrecorded / REGRESSED / UNREADABLE) and its refusal to
  claim a ratchet that did not land; `main()`'s `return 1 if failed else 0` actually reaching the
  exit code.
- **tiers.py**: the `CUTS` invariant checks raised (not `assert`ed) at import; the
  multiverse-complete-linkage / metaverse-and-xenoverse-single-linkage containment scan (re-traced
  why a peer with `hi is None` can never appear beside a real value for the multiverse->metaverse
  or metaverse->xenoverse pairs, since a looser threshold's edge set is a strict superset of a
  tighter one's, so complete-linkage or single-linkage membership at the tighter cut always
  survives at the looser one); `xenoverse_grounding()`'s per-xenoverse (not per-source) pooled
  vote with contested-not-averaged dissent; `_load_groundings()`'s read-verdict-travels-with-data
  pattern and `main()`'s refusal to publish `TIERS.json` on an unreadable-groundings or a
  containment violation.
- **citecheck.py**: `_classify()`'s `UNRESOLVED`/`PAST_EOF`/`BLANK_LINE`/`BARE_BRACKET`/`None`
  five-way return and its 1-based/0-impossible line handling; `_mention_kind()`'s quoted-tag and
  symbol-disclaimer exemptions (confirmed the disclaimer exemption is start-position-gated, not
  whole-line, so a genuine citation before the disclaimer phrase on the same line is still
  checked); `_in_tree_lead()`'s `src/`-vs-`other/src/` boundary check; `_lines()`'s
  unreadable-is-not-missing distinction feeding `_classify` a `None` that is read as "not provably
  broken" rather than clean (both the design tradeoff and its correct implementation).
- **cosmography.py**: `validate()`'s two independent ceiling classes (the in-census Kardashev
  ratio ceilings, which scale with the census and can only catch a proportions error, versus
  `SIZE_CLASS_MAX_GALAXIES`'s absolute per-class ceiling, which is the only check that can catch a
  categorically-impossible POCKET/MINOR census — re-confirmed against the corrected
  `SIZE_CLASSES` multipliers, which are now derived from `GALAXIES_DEFAULT`/
  `STARS_PER_GALAXY_MEAN` rather than hand-typed, per orders `adaeaa7ad639`/`cdfeccbfbab0`);
  `kardashev_to_magnitude()`'s `reached = None` initialisation and ascending-ladder scan (checked
  `assay.LADDER` is in fact ascending M0→M10, which is what makes the "keep raising `reached`"
  loop correct rather than order-dependent).
- **entity_match.py**: `qualifier_compatible()`'s absolute normalised-equality gate (never
  overruled by a similarity score); `candidates()`'s two early-exit paths, both confirmed to
  return the same `dict`-shaped `blocked_by_qualifier: {}` as the normal path (the historical
  list/dict mismatch from order `21f729df8884` is gone); the `STRONG`/`WEAK` ordering raised (not
  asserted) at import; `similarity()`'s max-of-Dice/SequenceMatcher and its documented refusal to
  swap in `rapidfuzz` (a measured, not assumed, non-drop-in).

No tautology, no fail-open guard reachable from live code, no new Hard-Rule-0 cap/truncation, no
off-by-one/unit-mix/race, and no regex/escape corruption was found in any of the eight modules
beyond what each module's own in-line order history already records as found-and-fixed.

## Questions

None met the bar this batch (a real ambiguity between two defensible readings). The standing
design questions already on record — the hand-run-tools-vs-halt-interlock policy question
(`1e6f99e54b25`/`21c075e5e2d6`/`3099138a82bd`, naming `chain.py main()` and `overnight.py`'s
supervised jobs among others) and cosmography.py's thirteen-functions-no-production-caller
question (`7099a092abd3`) — are pre-existing OWNER-routed items, not new territory this batch
surfaced, and are not re-argued here.

## Cleared

- `chain.py`'s `harvest()` recipe-reset/held-root interaction (sweep64 batch11 Finding 1,
  `058fa19d4e65`-adjacent but never itself filed as a workorder) — verified FIXED at
  `chain.py:409-420`.
- `overnight.py` — every fail-closed gate, singleton guard and idle-halt branch documented above.
- `scout.py` — every CAS write path and rotation-ownership check documented above.
- `thread_integrity.py` — the full classify()/load_thread_graph()/_floor_verdict() chain.
- `tiers.py` — the containment scan, the grounding-derived hyperverse, the publish-time refusals.
- `citecheck.py` — the five-way classifier and its use/mention exemptions.
- `cosmography.py` — both validate() ceiling classes and the Kardashev-Magnitude bridge.
- `entity_match.py` — the qualifier gate and both candidates() early-exit shapes.

## Coverage

Recorded via `sweep_plan.record('run65', ['overnight.py', 'chain.py', 'scout.py',
'thread_integrity.py', 'tiers.py', 'citecheck.py', 'cosmography.py', 'entity_match.py'],
batch=11)` — see the script run alongside this report.
