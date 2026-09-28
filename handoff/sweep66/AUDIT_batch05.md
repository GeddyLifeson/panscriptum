# sweep66 batch05 audit

Scope, read in full, start to finish, no sampling, no grep-only skimming:

- `src/feats.py` — 2817 lines (read in 4 chunks: 1-700, 701-1400, 1401-2100, 2101-2817/end)
- `src/ledger_guard.py` — 1111 lines (read in 2 chunks: 1-600, 601-1111/end)
- `src/estate.py` — 723 lines (read whole)
- `src/autostart.py` — 613 lines (read whole)
- `src/pick_model.py` — 465 lines (read whole)
- `src/snapshot.py` — 376 lines (read whole)
- `src/context_budget.py` — 319 lines (read whole)
- `src/scale_theories.py` — 215 lines (read whole)

Total 6,639 lines across 8 modules, matching `state/sweep_plan/run66.json`'s batch-5 assignment.
Read-only throughout: nothing under `src/`, `data/`, `state/`, `output/`, `prompts/`, `reference/`
or the repo root was edited. No network calls were made and no daemons or long jobs were started.
Nothing was executed at all this run (no standalone repro was needed — no candidate defect
surfaced that required one) except the final `sweep_plan.record` call.

## Prior-audit cross-check

This batch's exact module list and ordering matches `handoff/sweep65/AUDIT_batch05.md` (also
batch 5, same eight files, same line counts). That audit found zero new defects and cleared every
module by name. This run re-read every file end to end against the live source rather than taking
that clearance on trust, and nothing has regressed:

- `feats.py`: `_brace_end`/`_unwrap_templates`'s stack-based brace-width tracking (fixed
  sweep64-batch05, confirmed sweep65-batch05 by execution) is unchanged and still correct on
  inspection of the current source (lines 1602-1630). `_throttle`/`note_throttled`/`note_ok` and
  the registrable-domain `_HOST_LOCKS` keying, `resolve_hosts()`'s override/cache/probe
  for/else logic, `_api_list_all`'s continuation-following and `_CAP_BOUND` accounting, `mine()`'s
  exponent capture, `roll()`'s counter bookkeeping and exit-code propagation, and
  `evidence_for()`'s four `mined_under_*` staleness predicates were all re-traced line by line;
  all still do what their (extensive) comments say they do.
- `pick_model.py`: the VRAM-unit fix (`_mib_to_gb`, fixed sweep64-batch12, confirmed
  sweep65-batch05) is unchanged; `total_vram_gb()`/`free_vram_gb()` both still route through it.
  `family_tier()` ordering, `resident()` vs `fit_note()`'s two distinct budget questions, and the
  tri-state `vram_measured`/`vram_gb` handling in `main()` are all still correct.
- `ledger_guard.py`, `estate.py`, `autostart.py`, `snapshot.py`, `context_budget.py`,
  `scale_theories.py`: every mechanism sweep65-batch05 examined and cleared (structure/floor/chain
  checks, TOCTOU-guarded `inspect()`, tri-state `supervisor_alive()` propagation, path-containment
  refusals in `_rel()`/`_safe_join()`, the two-ratio context arithmetic, and the intentional
  dead-but-authored status of `scale_theories.THEORIES`) was independently re-verified this run
  and found unchanged and correct.

`state/workorders.json` was searched for each of this batch's eight filenames. The hits are the
same shape sweep65-batch05 already characterized, and none of them is a fresh code defect this
batch's files would otherwise need filing:

- `3fb312a72435` — `hosts.py` has no caller; names `feats.py` only as the intended wiring point
  (it reads `WIKI_HOSTS.json` directly instead of `hosts.hosts_for(source)`). The fault, if any,
  is in `hosts.py`/the missing wiring, not in `feats.py`'s current, working behavior.
  `scale_theories.py`'s own docstring (lines 26-30) independently confirms this order is still
  open and correctly describes the same gap — consistent, not new.
- `79d51aef8b71` — `verify_math`'s live GPU dependency; names `feats.py --roll` only as one of
  several concurrent GPU consumers measured during that investigation, not as a fault in
  `feats.py` itself.
  `d9328fe1ee38`/`4c2101d54c10`/`573ab7b04b6f` — `standards.py`/`foreman.py`'s stall-detection
  gap and the `autostart.py --watch` watchdog-death incident (2026-09-10) and its restoration
  (`_twin_watchdog` guard). Both are already fully reflected in `autostart.py`'s own current
  comments (`watch()`'s "STAMPED, AND THE STALENESS IS SAID OUT LOUD" block, lines 426-453) —
  the design question of "nothing watches the watchdog" is open, already recorded here and in
  the code, and this audit does not re-raise it as new.
- `8454be695dc7` — `NO_FIRST_CLASS_PAUSE_STATE`, an owner-handler design question about a
  first-class pause marker that `autostart.py`/`overnight.py`/the maintenance task would all
  need to respect. Explicitly marked "A QUESTION, NOT A DEFECT" in the order itself; not a fault
  in `autostart.py`'s current code.
- `a5faab7f3ede` — the already-open, already-argued-both-ways `ledger_guard.seal()` floor-advance
  question (line-count vs. full retention). See below.

## Findings

None. No new CONFIRMED or SUSPECTED defect in any of this batch's eight modules.

## Questions (possible deliberate design — owner decides these)

- `ledger_guard.py`'s `check_since_floor()`/`seal()` floor-advance rule (the floor is replaced
  with the live text only when substantive-line COUNT is non-decreasing, not when every existing
  line is retained) is already tracked as open order `a5faab7f3ede` and the code's own comment at
  `ledger_guard.py:472-510` already lays out the tradeoff (freezing the floor on any edit vs.
  letting a sequence of small losses compound) without resolving it. Not re-raised as a new
  question; noted here only so a reader of this batch's file knows it was seen and is not a gap
  in this audit.
- `autostart.py`'s watchdog has no external liveness check on itself (`watch()`'s own comment,
  lines 426-453: `codewatch.stale()` reports staleness but the loop deliberately does not
  `exit_if_stale()`, "because nothing restarts the Startup .vbs"). This is the same open design
  question as order `4c2101d54c10`/the sibling filed under `d9328fe1ee38`'s shift — three shapes
  of remedy are already named in the code (a liveness check raised by something else alive; a
  Scheduled Task re-running the Startup command on an interval; the daily maintenance run
  asserting it) and the choice between them is called an operations ruling in the comment itself.
  Not re-raised as new; the code already says it is open and undecided.

## Cleared (examined closely, found correct)

- `feats.py` — every mechanism named in the "Prior-audit cross-check" section above, re-verified
  against the current source rather than assumed. Additionally checked this run and found sound:
  `page_looks_real()`'s three-tier refusal-marker gating (sufficient vs. ambiguous markers,
  `parsed=True` skip for MODE_API); `_units()`'s length-gate tallying (`_UNIT_DROPS`); `by_axis()`
  and `_axis_independent_gates()`'s single shared definition (no drift between `axis_evidence`,
  the dead-but-retained wrapper, and the live `by_axis` path); `discover()`'s ranked, uncapped
  page-title walk and its `extra`-parameter refusal under Hard Rule 0; `resolve_title()`'s
  exact-match / disambiguator-ranking logic; `fetch()`'s outcome-channel stamping and per-batch
  `failed_dirty` counting; `_source_pages_text()`'s per-key locking for `pages:` hosts;
  `main()`'s escalation-chain check at the top (fail-closed `ImportError` handling) and its three
  named nonzero-exit conditions for `--roll`.
- `ledger_guard.py` — `check_structure()`'s heading-vs-substring section detection (both the
  `## Open`/`## Resolved` presence test and the bug-id-in-both-sections check, both keyed on
  `^` anchored headings, not substrings); `_handoff_journal_problems()`'s dated-heading and
  ordering checks, including the undated-`#`-heading case; `seal()`'s per-writer-unique temp
  names, snapshot writes, and floor-ratchet; `_lost_fraction()`'s multiset-based line-loss
  measurement; `read_chain()`/`_read_chain_lines()`'s fail-closed handling of unparseable lines
  (reported, not silently dropped); `verify_chain()`'s unit-reconciliation across the
  bytes/chars schema boundary and its acknowledgement mechanism (`_load_acknowledgements()`'s
  fail-closed shape validation); `assert_intact()`'s ordering (structure, chain, since-snapshot,
  since-floor, then seal) and its own nonzero-verdict propagation.
- `estate.py` — `_effective_ext()`'s backup-marker peeling (re-deriving the extension rather than
  enumerating markers); `inspect()`'s TOCTOU-guarded stat/read retry (GONE vs. UNREADABLE vs.
  transient-and-benign, each reported distinctly) and its per-extension read strategy (`.jsonl`
  line-by-line, `.json` whole, `TEXT_EXT` plus `ast.parse` for `.py`, binaries/logs sized only);
  `artifacts()`'s root discovery via `os.scandir(HERE)` rather than a hand-kept list; `charter()`'s
  table-driven erratum tests (reading the charter's own Magnitude/Ladder tables rather than a
  string-presence test) and its `bad=True`/`bad=False` severity split; `written()`'s and
  `external()`'s per-condition row emission (no vanishing rows on an exception or an empty dict).
- `autostart.py` — `installed_state()`'s content-comparison (not existence-only) verdict;
  `install()`'s temp-plus-replace-retry idiom with readback verification; `supervisor_alive()`'s
  tri-state passthrough from `overnight.running()`; `_twin_watchdog()`'s tree-scoped (not
  bare-filename) twin detection via `codewatch.twins()`, its retry-then-fail-open behavior, and
  its `--watch`-only filtering; `_start_decision()`'s halt-before-budget ordering (pure function,
  independently testable); `watch()`'s rate-limited logging for each of the four conditions
  (unknown/halted/budget/start) and its non-exiting response to stale-self-code.
- `pick_model.py` — every mechanism named in the "Prior-audit cross-check" section above, plus
  `score_model()`'s tier/instruct/log-size composite scoring, `resident()`'s budget-vs-total
  question vs. `fit_note()`'s budget-vs-free question (explicitly two different questions, not a
  contradiction when they disagree), and `main()`'s `excluded`/`refused`/`scored` three-way split
  driving the correct diagnosis message in each branch.
- `snapshot.py` — `_rel()`'s containment refusal (drive-crossing and `..`-escape both refused,
  not silently re-rooted); `before()`'s partial-snapshot refusal (`allow_missing`) and its
  nanosecond+pid unique snapshot ids (`exist_ok=False`, never a silent merge); `_dir_matches()`'s
  file-by-file, byte-for-byte directory verification (not existence-only); `_safe_join()`'s
  second containment check on restore; `restore()`'s missing-manifest-entry refusal (not a
  silent partial restore).
- `context_budget.py` — `_read_scaffold()`'s fail-closed absent-vs-unreadable split (no empty
  string substituted, which would silently widen the budget); the `CHARS_PER_TOKEN` (content) vs
  `PROSE_CHARS_PER_TOKEN` (scaffolding) split, both applied in the correct direction in
  `content_budget_chars()` and `measure()`; `split_system_prompt()`'s heading-anchored (not
  line-number) split and its no-op fallback when the heading is absent; `feats_block_budget()`'s
  `JOB_OVERHEAD_CHARS`/`METADATA_INFLATION` corrections charged in the correct ratio.
- `scale_theories.py` — confirmed still intentionally unwired dead-but-authored content per owner
  ruling `01695fe3ef26`, and the docstring's claim about `hosts.py` not being wired is itself
  still accurate (cross-checked against `3fb312a72435` above); `surviving_theory()`'s
  field-based (not prose-prefix) selection and its raised (not asserted) arity check are both
  still correct; the five reference-only physical constants are still each declared exactly once
  and read by nothing, matching the module's own claim.

## Summary of findings by kind

- Checks that cannot fail: 0
- Fail-open guards: 0
- Caps/truncations hiding roster/entry-list data (Hard Rule 0): 0
- Real logic bugs (wrong variable, off-by-one, race, inverted condition, regex/escape
  corruption): 0
- Comments/docstrings asserting behavior the code does not have: 0
- Suppressed exceptions turning a failure into a plausible negative: 0

## Coverage recorded

Ran `sweep_plan.record('run66', ['feats.py', 'ledger_guard.py', 'estate.py', 'autostart.py',
'pick_model.py', 'snapshot.py', 'context_budget.py', 'scale_theories.py'], batch=5)` from the kit
directory after this file was written.
