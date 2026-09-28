# sweep66 batch11 — audit

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

Total 6,563 lines, matching `wc -l` over the eight files exactly. Read-only throughout: nothing
under `src/`, `data/`, `state/`, `output/`, `prompts/`, `reference/` or the repo root was edited,
created or deleted, except this file and the one permitted `sweep_plan.record` call. Did not run
drill.py, verify_math.py, generate.py, the pipeline, publish, overnight, chain, mutate, foreman,
overwatch or any other job. Did not spawn subagents. No network calls were made.

## Method

Every prior sweep report naming any of these eight files was located and read before forming a
new opinion.

`handoff/sweep65/AUDIT_batch11.md` covers the IDENTICAL eight-file batch (same pairing, same
module set) and reported **0 CONFIRMED, 0 SUSPECTED** findings, with each module's load-bearing
logic hand-traced there in detail (the `_RECIPE_KEY` mechanism in chain.py, the fail-closed gates
and idle-halt arithmetic in overnight.py, scout.py's CAS rotation discipline, thread_integrity's
classify()/load_thread_graph() chain, tiers.py's containment scan, citecheck.py's five-way
classifier, cosmography.py's two ceiling classes, entity_match.py's qualifier gate). This run
re-read all eight modules fresh against that report rather than assuming it still holds, and
confirms it does: no code changed in any of the eight files in a way that reopens anything sweep65
cleared, and no new defect class from the brief (wrong results, silent swallowing, caps/
truncation, a bypassable guard, races on shared state, stale comments, dead code) was found in
this pass either.

`handoff/sweep64/AUDIT_batch11.md`, `AUDIT_batch12.md` and `AUDIT_batch14.md` were the sweep before
that, covering the same eight modules split across different batch pairings; sweep65's own
cross-check already re-verified all of sweep64's findings against source (the chain.py `harvest()`
recipe-reset/held-root fix at chain.py:409-420, now present unchanged and re-verified again here)
and found them fixed and stable. Also grepped: `handoff/sweep65/AUDIT_batch02.md` (cites
`entity_match.py:199` and `tiers.py:165` only as *examples* of the "raise, don't assert" pattern —
not findings against those files), `AUDIT_batch05.md` (notes citecheck.py was "covered separately",
i.e. in batch11), `AUDIT_batch06.md` (mentions overnight.py only in the context of drill.py's
rehearsal scope, not a finding), `AUDIT_batch14.md` (mentions overnight.py only as an out-of-scope
neighbor). None of these carry a finding against this batch's modules.

`state/workorders.json` (55 entries) was searched for all eight module names. Every hit is
already-open and already routed, and none is a code defect this batch could newly confirm or
contradict:

- `058fa19d4e65` (chain.py) — already open: the durable code fix (the `_RECIPE_KEY` /
  `_harvest_recipe_digest()` mechanism) is confirmed landed and live-verified in this pass at
  chain.py:201-229 and 379-386 (re-read start to finish); the order's own text records the fix as
  done as of run #64/#65 and reroutes the remaining ask (a stale `data/CHAIN.json` needing a re-fit
  through the running pipeline) to BOTS as an operational task, not a code defect. Not re-filed.
- `1e6f99e54b25`, `21c075e5e2d6`, `3099138a82bd` (overnight.py, chain.py, thread_integrity.py) —
  already open: the standing OWNER-routed policy question of whether a hand-run tool should refuse
  while the library is halted. A design question, not a defect; not re-argued here.
- `5bb12b398783`, `8454be695dc7`, `a66423722e45`, `d1709d8e757d` (overnight.py) — already open,
  owner-routed questions/operational items unrelated to a code defect in this batch's modules.
- `7099a092abd3` (cosmography.py) — already open: the standing "thirteen functions with no
  production caller" owner question. Not re-argued here.
- `a724ec57e0d5` (thread_integrity.py) — already open, marked as a question (two defensible
  readings, owner's call), not a defect.

No open workorder names `scout.py`, `tiers.py`, `citecheck.py` or `entity_match.py` at all.

Each file was then read fresh, start to finish, checking specifically for: wrong logic,
off-by-one errors, inverted conditions, exceptions swallowed where the code claims to fail
closed, a guard that cannot fail, races on shared files, Hard-Rule-0 caps/truncations on any
roster or list, comments asserting behaviour the code no longer has, dead branches, wrong units,
and Windows-specific breakage.

## Findings

**0 CONFIRMED. 0 SUSPECTED.**

Load-bearing logic specifically hand-traced against the current source rather than taken on the
file's own word, this pass:

- **overnight.py**: the stage-6 prose gate's `drill_rc == 0` / `== 1` / anything-else three-way
  branch (still `==`, not `!=`, so an unrecognised or `None` drill result cannot open the prose
  gate); `_prose_enabled()`'s delegation to `prose_gate.gate_open()`, fail-closed on any exception;
  `_guarded_popen`'s lock-serialised check-then-spawn and the `_PROBE_BLIND` sentinel kept distinct
  from "already running"; `running()`/`_cmd_is_running()`/`_in_this_tree()`'s quote-aware
  tokenising and `-m`/`-c` refusal; `BUSY_STATUSES`'s inclusion of `rc=17`; the idle-halt branch's
  fail-closed `except Exception: _halted = True` around `escalation.status()`; `preflight()`'s
  identity-by-name lookup of the control-character check label; `coverage_snapshot()`'s dual
  rc-and-mtime staleness check; `write_status()`'s atomic build-then-replace with a denied-write
  report rather than a silent stale page.
- **chain.py**: the `_RECIPE_KEY` mechanism end to end (digest computation, the held-root-vs-
  recipe-reset interaction at 409-420, exclusion from the prune loop at 468 and from
  `refresh_continuity`'s patch loop at 563); `_land_harvest`'s compare-and-swap re-read/re-apply on
  a lost race; `extract()`'s malformed-model-output guards (non-dict outcome, bad/out-of-range
  index, the `unanswered` vs "answered with nothing" distinction); `adjudicate_mutuals`'s
  three-way UNPROBED/self-split/dated disposition and its every-provenance-sentence epoch check;
  `write_result`'s unconditional edges/unmatched/unanswered persistence on every fit-refusal path;
  the `SINGLETON_LOCK` claim/release pair's own-pid-only release rule.
- **scout.py**: `_mutate`'s fail-closed unreadable/wrong-shape refusal; `verify()`'s
  `min(MIN_NAME_HITS, probeable)` floor and the separate `probeable == 0` "unverifiable" branch;
  `sweep()`'s last-attempted-first rotation, stamp-before-work / unstamp-only-if-still-ours logic,
  and archive-before-trim roll-off.
- **thread_integrity.py**: `_charter_codes()`'s absent-vs-corrupt distinction; `load_thread_graph`'s
  fail-closed `ThreadGraphUnreadable`; `classify()`'s dead `(a,b) in seen` half confirmed still
  genuinely dead (pairs is built once per key by `implied_threads`) and the DANGLING/PARTIALLY-
  DANGLING/IMPLIED-UNRECORDED/RECIPROCAL/ASYMMETRIC-LAWFUL/ASYMMETRIC-SUSPECT partition;
  `_floor_verdict`'s six-state regression ladder; `main()`'s `return 1 if failed else 0` actually
  reaching the exit code.
- **tiers.py**: the `CUTS` invariant checks raised (not asserted) at import; the multiverse/
  metaverse/xenoverse containment scan; `xenoverse_grounding()`'s per-xenoverse pooled vote;
  `_load_groundings()`'s read-verdict-travels-with-data pattern and `main()`'s refusal to publish
  `TIERS.json` on an unreadable-groundings or containment violation.
- **citecheck.py**: `_classify()`'s UNRESOLVED/PAST_EOF/BLANK_LINE/BARE_BRACKET/None five-way
  return; `_mention_kind()`'s start-position-gated disclaimer exemption (a genuine citation before
  the disclaimer phrase on the same line is still checked); `_in_tree_lead()`'s `src/`-vs-other
  boundary check; `_lines()`'s unreadable-is-not-missing distinction.
- **cosmography.py**: `validate()`'s two independent ceiling classes (in-census Kardashev ratios
  vs `SIZE_CLASS_MAX_GALAXIES`'s absolute per-class ceiling); `kardashev_to_magnitude()`'s
  `reached = None` initialisation and ascending-ladder scan.
- **entity_match.py**: `qualifier_compatible()`'s absolute normalised-equality gate; `candidates()`'s
  two early-exit paths both returning the same dict-shaped `blocked_by_qualifier: {}`; the
  `STRONG`/`WEAK` ordering raised (not asserted) at import; `similarity()`'s max-of-Dice/
  SequenceMatcher and its documented, measured refusal to swap in `rapidfuzz`.

No tautology, no fail-open guard reachable from live code, no new Hard-Rule-0 cap/truncation, no
off-by-one/unit-mix/race, and no regex/escape corruption was found in any of the eight modules
beyond what each module's own in-line order history already records as found-and-fixed.

## Questions

None met the bar this batch (a real ambiguity between two defensible readings, not already on
record). The standing OWNER-routed items already on file — the hand-run-tools-vs-halt-interlock
policy question (`1e6f99e54b25`/`21c075e5e2d6`/`3099138a82bd`) and cosmography.py's
thirteen-functions-no-production-caller question (`7099a092abd3`) — are pre-existing, not new
territory this batch surfaced, and are not re-argued here.

## Cleared / re-confirmed still fixed

- `chain.py`'s `harvest()` recipe-reset/held-root interaction (sweep64 batch11 Finding 1) —
  re-verified again at `chain.py:409-420`, unchanged since sweep65, still fixed.
- `overnight.py`, `scout.py`, `thread_integrity.py`, `tiers.py`, `citecheck.py`, `cosmography.py`,
  `entity_match.py` — every load-bearing check named above re-traced against current source and
  held.

## Coverage

Recorded via `sweep_plan.record('run66', ['overnight.py', 'chain.py', 'scout.py',
'thread_integrity.py', 'tiers.py', 'citecheck.py', 'cosmography.py', 'entity_match.py'],
batch=11)`.
