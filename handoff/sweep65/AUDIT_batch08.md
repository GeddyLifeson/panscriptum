# sweep65 batch 08 — audit report

Auditor for maintenance run #65 (2026-09-26), batch 08. Read-only throughout: nothing under
`src/`, `data/`, `state/`, `output/`, `prompts/`, `reference/` or the repo root was edited,
created or deleted except this report and the mandated `sweep_plan.record()` call. No drill,
verify_math, generate, pipeline, publish, the crawl, overwatch, foreman, mutate, or
verify_math-adjacent command was run. No subagents were spawned. No halt/`prose_enabled`/
`step4_enabled` state was touched.

## Scope (every line read, start to finish, via the Read tool, no grep-sampling)

- `src/cascade_bridge.py`    2340 lines (read in six chunks: 1-400, 401-800, 801-1200, 1201-1600,
  1601-2032, 2032-2340)
- `src/sweep_plan.py`        1150 lines (four chunks: 1-400, 401-800, 801-1150 plus a targeted
  re-read of 800-1150)
- `src/catalogue_web.py`      821 lines (two chunks: 1-450, 450-821)
- `src/manifest_builder.py`   677 lines (one chunk, whole file)
- `src/catalogue_codex.py`    515 lines (one chunk, whole file)
- `src/sevenfold.py`          441 lines (one chunk, whole file)
- `src/catalogue_aurora.py`   328 lines (one chunk, whole file)
- `src/cosmology_graph.py`    261 lines (one chunk, whole file)
- `src/whoruns.py`            159 lines (one chunk, whole file)

Total 6,692 lines across nine modules, all read completely this session.

## Method and prior-audit cross-check

`CLAUDE.md` read first (Hard Rule -1 escalation/halt chain, Hard Rule 0 no caps ever, fail-closed
doctrine, "a check that cannot fail looks exactly like a check that passed"). `handoff/sweep64/`
was then grepped for all nine module names and every matching report read in full before source:

- `AUDIT_batch08.md` (sweep64) — the closest predecessor, covering `cascade_bridge.py`,
  `sweep_plan.py`, `catalogue_codex.py`, `sevenfold.py` among others. Filed one VERIFIED finding:
  `cascade_bridge.py`'s `ask()` metric line mislabelled a successful non-dict reply (a bare
  fenced list/bool/number) with the FAILURE-attribution `"tried:"` string, because
  `isinstance(got, dict)` was used as a proxy for "did the call fail" when a non-dict `got` can
  also mean "answered, but not with an object."
- `AUDIT_batch09.md` (sweep64) — covers `manifest_builder.py`. Filed one VERIFIED finding: the
  `--include-unassigned` report (`unassigned_sources.md`) printed a recomputed
  `provisional_spine(r)` for each source instead of the disambiguated `volume_code[r["name"]]`
  the build actually used, so two unassigned sources sharing a `category` would be built under
  `.1`/`.2` codes but both reported as the bare, colliding `UNSORTED.<Category>.PROVISIONAL`
  string.
- `AUDIT_batch10.md` (sweep64) — covers `catalogue_web.py`. Zero findings; the batch specifically
  traced the two-writer hazard against `pipeline.write_record_catalogue` and `roll.update_rows`
  and found both correctly used.
- `AUDIT_batch07.md` (sweep64) — covers `catalogue_aurora.py`. Zero findings.
- `AUDIT_batch06.md` (sweep64) — covers `cosmology_graph.py` and `whoruns.py`. Zero findings in
  either.

Both sweep64 VERIFIED findings were traced against the CURRENT source rather than trusted, per
this sweep's standing instruction that prior audits can be wrong in either direction. **Both are
now fixed**, with the fixing commentary present in the code itself (see Cleared, below).

`state/workorders.json` was searched for every module name in this batch plus the two prior
findings' distinguishing text (`isinstance(got`, `non-dict`, `model_metrics`, `_via`,
`provisional_spine`, `STALLED_UNRESTARTABLE`) before writing anything down. No open order names
either fixed finding. Order `21c075e5e2d6` (OWNER rung, "MORE_WRITERS_WITHOUT_A_HALT_INTERLOCK_
SWEEP58") does name `sevenfold.py` as one of several derived-artifact writers that do not call
`escalation.assert_clear()` under a halt — this is an open, already-filed OWNER-rung policy
question spanning modules well outside this batch, not re-derived or re-filed here.

## Findings

**Zero new VERIFIED or SUSPECTED findings.** Both defects carried forward from sweep64 in this
batch's modules are confirmed fixed against the current source:

1. **CLOSED — `cascade_bridge.py:1470-1477`, `ask()`'s metric line.** Now three-way:
   `got.get("_via")` when `got` is a dict; `"tried:" + ",".join(_tried())` only when `got is
   None`; and a new `"unstamped:" + ",".join(_tried())` branch for a non-None, non-dict `got`
   (a bare fenced list/bool/number). The comment at the site explicitly cites "sweep64 batch08,
   run #64." Traced `selftest()`'s parallel `if got` / `got.get("_via")` guard at line 2096 too
   (the sibling site the sweep64 report flagged as carrying the identical class of bug one path
   further down) — it already guards with `isinstance(got, dict)` and is unaffected by this
   class of defect.

2. **CLOSED — `manifest_builder.py:654`, the unassigned-sources report.** Now reads
   `volume_code.get(r['name'], provisional_spine(r))` — the code the build actually assigned,
   falling back to a fresh `provisional_spine(r)` only if the source is missing from
   `volume_code` entirely (which cannot happen for anything in `unassigned` when
   `--include-unassigned` is set, since `numbering_pool` is a superset of every unassigned
   source). The comment at the site names "sweep64 batch09, run #64" and restates the exact
   collision scenario the prior finding described. Also re-checked `provisional_spine()` itself
   and the `series_members`/`volume_code` disambiguation loop (lines 533-546) that produces the
   `.1`/`.2` suffixes — unchanged and correct.

## Cleared — examined closely this session, found correct

- **`cascade_bridge.py`**: the entire failure-classification chain traced end to end —
  `_extract_json`'s raw_decode scan (no brace-counting regression), `local_transport` /
  `client_rejection` / `permanent_refusal` ordering (local-transport wins, then WAF rejection,
  then account-fault vocabulary), `_size_refusal_permanent`'s Limit/Requested arithmetic guard
  ahead of `named_transient`'s word/code scan, `retry_after_seconds`'s ordered pattern list
  (composite `Xm Ys` tried before bare seconds, so "6m51.264s" cannot be misread as 51s),
  `dead_forever`'s mtime+TTL memo and `local_transport`/`client_rejection` exemptions before the
  401/402/404/410 code+word test, `record_unrecognised`'s digest-before-read compare-and-swap and
  jittered 12-attempt backoff, `_ask_call`'s reservation lifecycle (reserve happens before the
  `try`, `finally` always releases exactly the one bucket named `pinned`, local buckets are
  refused on both the pin path and the claim-loop path), the widen-fallback's proof-file ranking
  plus round-robin rotation surviving the stable re-sort, `prove()`/`try_disabled()`'s
  `max_attempts=1` isolation and served-bucket cross-check, and the `__main__` guard's `--help`
  short-circuit ahead of any live call. No fail-open branch, no wrong-variable/off-by-one, no
  regex escape corruption, no dead-code-claimed-live found anywhere in the file.
- **`sweep_plan.py`**: `normalise_module`'s exact-then-basename-if-unambiguous resolution (never
  guesses on a basename collision); `record()`'s per-shard-file-then-aggregate-fallback write
  path and the unknown/accepted split; `_read_shards`/`covered_by`/`missing`'s per-run shard scan
  (not `coverage_map()`, which is deliberately newest-wins and wrong for this question);
  `roster_of`'s `None`-vs-empty-set distinction and `missing_detail`'s refusal to infer
  `added_since` from mtimes; `freeze_plan`'s three-way `frozen_plan()` reason handling (only
  `"absent"` may license a fresh freeze) and its create-if-absent compare-and-swap against a
  second first-caller; `check_briefs`'s frozen-plan-vs-live-tree selection and its
  `tree_changed_since_freeze` flag. All match their docstrings' claims exactly.
- **`catalogue_web.py`**: `_singular`'s three-rule Fandom-category singularisation (never
  `.rstrip("s")`); `catalogue`/`catalogue_composite`'s `first_cat` provenance tracking (never the
  stale `cats[0]`); the dedup key including the disambiguator (never stripping the parenthetical
  before hashing); `save_roll`'s compare-and-swap through `roll.update_rows`; the `MAX_PER_SOURCE
  = None` import-time tripwire; `main()`'s `--limit 0` vs `None` distinction and the
  partial-failure exit code (`tally["failed"]` compared against `todo`, not only the all-failed
  case). No new gap beyond what sweep64/batch10 already verified clean.
- **`manifest_builder.py`**: `load_record`'s exact-then-prefix-then-containment record resolution
  with the `MIN_INEXACT_LETTERS` floor; `pack_feats`'s flush-before-exceeding pagination and its
  per-entity oversized-slice handling (never drops a deed); the `numbering_pool` (unfiltered) vs
  `build_pool` (post `--only`/`--pilot`) split that keeps a volume's address stable regardless of
  which sources are actually built; the owner-exclusion filter reported by name before any
  selection; both the manifest and the unassigned-report writes gated on their own landed-verdict
  and folded into a single non-zero return code when either is denied.
- **`catalogue_codex.py`**: the manifest-declared-count cross-check in `parse_codex` (0
  mismatches against the live codex, dormant but wired); the four uncapped, pre-write-summary
  collision reports (`norm_clashes`, `ambiguous`, `reg_ambiguous`, `dupe_elements`,
  `unmapped_types` — five, all present); `load_register_index`'s every-item-under-its-key
  (never first-wins) collision handling; the `(type, name)` pair used as the true element
  identity in the dedup `seen` set, not `name` alone.
- **`sevenfold.py`**: `_even_cuts`'s clamped, deduplicated boundary computation; `seams()`'s
  two-rule cut selection (median-ceiling-eligible seams, windowed around each even boundary) —
  hand-traced against a small synthetic block to confirm the window-plus-weaker-half interaction
  cannot cut a strong seam nor leave a giant component; `build()`'s two-population accounting
  (`coords` from the resonance graph vs. `by_source` from every record) and the `UNSHELVED`
  reporting for sources that produce worlds but are absent from the graph; the `--write` gate on
  `silence.write_json`'s landed verdict.
- **`catalogue_aurora.py`**: `slug`/`record_path`'s uncapped identity with the legacy-60-char
  fallback preferring an existing file; `parse_folder`'s `(type, norm(name), description)` dedup
  key (never silently drops a same-named, differently-described element); the write-then-roll
  compare-and-swap gating (`write_record_catalogue` and `roll.update_rows` both checked, both
  named in the exit code).
- **`cosmology_graph.py`**: the `1/log(n+1.5)` inverse-frequency weight formula with the `x0.15`
  ubiquity penalty, matching the docstring's worked numbers exactly; `--write` emitting every
  pair and cluster uncapped with `threshold_applies_to: "clusters"` stated so the artifact cannot
  misdescribe its own `--threshold` as a pair-list filter.
- **`whoruns.py`**: `script_of`'s `-m`/`-c` short-circuit and the `_FLAGS_WITH_A_VALUE` two-token
  skip (an attached `-Xutf8` still falls through the bare `startswith("-")` arm correctly);
  `running()`'s tri-state (`None` = unmeasurable, distinct from an empty list) and its use of
  `ON._in_this_tree` to avoid a mutation-sandbox false positive; the exit-code documentation
  explicitly warning that 0 means "something is running," matching grep's convention rather than
  the more common shell-negative-means-success (mis-)reading.

## Questions

None new. The one open policy question touching this batch (`sevenfold.py`'s absence from any
halt interlock, order `21c075e5e2d6`/`1e6f99e54b25`, OWNER rung) is already filed and unchanged;
not re-derived here.

## Coverage recorded

Recorded via `sweep_plan.record('run65', ['cascade_bridge.py', 'sweep_plan.py',
'catalogue_web.py', 'manifest_builder.py', 'catalogue_codex.py', 'sevenfold.py',
'catalogue_aurora.py', 'cosmology_graph.py', 'whoruns.py'], batch=8)` for all nine modules above,
each read in full this session, none substituted or skipped.
