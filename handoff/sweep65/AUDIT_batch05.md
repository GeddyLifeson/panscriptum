# sweep65 batch05 audit

Scope, read in full, start to finish, no sampling, no grep-only skimming:

- `src/feats.py` — 2817 lines (read in 4 chunks: 1-700, 701-1400, 1401-2100, 2101-2817/end)
- `src/ledger_guard.py` — 1111 lines (read in 2 chunks: 1-600, 601-1111/end)
- `src/estate.py` — 723 lines (read whole)
- `src/autostart.py` — 613 lines (read whole)
- `src/pick_model.py` — 465 lines (read whole)
- `src/snapshot.py` — 376 lines (read whole)
- `src/context_budget.py` — 319 lines (read whole)
- `src/scale_theories.py` — 215 lines (read whole)

Total 6,639 lines across 8 modules. Read-only throughout: nothing under `src/`, `data/`,
`state/`, `output/`, `prompts/`, `reference/` or the repo root was edited. Nothing was run except
a standalone reproduction of `feats._brace_end`/`_unwrap_templates`'s exact source (copied
verbatim into a scratch file under `%TEMP%`, no project imports, no network, no writes to the
repo) to verify a prior fix by execution, and the final `sweep_plan.record` call.

## Prior-audit cross-check

This batch's module list differs from `handoff/sweep64/AUDIT_batch05.md` in one file:
`citecheck.py` is out and `pick_model.py` is in. `citecheck.py` was covered separately in
`sweep63/AUDIT_batch13.md` (not re-read this run, out of scope for batch05 this time).

**Two findings carried forward from prior sweeps are now CONFIRMED FIXED, verified directly
against the live source rather than taken on the comment's word:**

1. `handoff/sweep64/AUDIT_batch05.md` filed a VERIFIED defect in `feats._unwrap_templates`: a
   `{{{param|default}}}` nested inside a `{{template|...}}` call corrupted the extracted text
   (dropped trailing characters, leaked a stray `}`). The live source at `feats.py:1602-1630`
   now carries a stack-based `_brace_end(c, j, n, first)` (comment: "sweep64 batch05, run #64")
   that tracks each opener's brace-width (2 or 3) on a stack and closes with the matching width.
   Re-ran the exact three repro cases from that audit plus three new stress cases (nested
   double-brace template inside a triple-brace default; two adjacent triple-brace params; a
   triple-brace nested two levels inside two double-brace templates) through the verbatim
   function body in an isolated scratch script: all six now round-trip correctly (e.g.
   `{{Infobox|power={{{1|Unknown}}}}}` -> `"  Unknown  "`, no dropped letter, no stray brace).
   Fixed; not re-filed.
2. `handoff/sweep64/AUDIT_batch12.md` filed a VERIFIED unit-mismatch defect in `pick_model.py`:
   `total_vram_gb()`/`free_vram_gb()` read `nvidia-smi` MiB and divided by 1024 (binary GiB)
   while `weight_gb()`/`KNOWN_WEIGHT_GB` are decimal SI GB, a ~7% understatement of usable VRAM
   in the residency gate. The live source now has `_mib_to_gb(mib)` (`mib * 1048576 / 1e9`,
   comment: "sweep64 batch12, run #64"), used by both `total_vram_gb()` and `free_vram_gb()`.
   Confirmed correct by inspection (1048576/1e9 is exactly the MiB->decimal-GB conversion) and
   by the fact both readers now share one conversion function rather than two independent
   `/1024` expressions. Fixed; not re-filed.

Every other module/finding sweep64-batch05 cleared (`ledger_guard.py`'s structure/floor/chain
checks, `estate.py`'s TOCTOU-guarded `inspect()`, `autostart.py`'s tri-state propagation,
`snapshot.py`'s containment refusals, `context_budget.py`'s two-ratio arithmetic,
`scale_theories.py`'s intentional dead-but-authored status) was re-examined directly against the
current source this run rather than assumed still true, and nothing has regressed.

`state/workorders.json` was searched for each of this batch's eight filenames. Six hits, none of
them a defect inside this batch's code that this audit would otherwise file fresh:
`3fb312a72435`/`79d51aef8b71`/`d9328fe1ee38` name `feats.py`/`autostart.py` only as
context/consumers of faults that live in other modules (`hosts.py`, `verify_math.py`,
`standards.py`/`foreman.py`); `4c2101d54c10`/`573ab7b04b6f`/`8454be695dc7` are about
`autostart.py`'s watchdog and `publish.py`'s credential context, already resolved or under a
separate open order, not new code defects found here; `a5faab7f3ede` is the already-documented,
already-open design question about `ledger_guard.seal()`'s floor-advance rule (line-count vs.
retention) — the code's own comment at `ledger_guard.py:679-708` already argues both sides of
this and says it is unresolved, so this audit treats it as a QUESTION already on record, not a
fresh finding.

## Findings

None. No new CONFIRMED or SUSPECTED defect in any of this batch's eight modules.

## Questions (possible deliberate design)

- `ledger_guard.py`'s `check_since_floor()`/`seal()` floor-advance rule (advance on
  non-decreasing substantive-line COUNT, not on full retention) is already tracked as open order
  `a5faab7f3ede` and already argued both ways in the code's own comments
  (`ledger_guard.py:679-708`). Not re-raised as a new question; noted here only so a reader of
  this batch's file knows it was seen and is not a gap in this audit.

## Cleared (examined closely, found correct)

- `feats.py` `_brace_end`/`_unwrap_templates` — re-verified by direct execution against six cases
  (three from the original defect report, three new stress cases); the stack-based rewrite is
  correct on all of them. See "Prior-audit cross-check" above.
- `feats.py` `_throttle`/`note_throttled`/`note_ok`/`backoff_state` and the `_HOST_LOCKS`
  registrable-domain keying — re-traced; the edge lock and per-host strike ledger still do not
  collide at the point of mutation vs. iteration, and `tuple(_BACKOFF.items())` is still a
  snapshot copy.
- `feats.py` `resolve_hosts()`'s override/cache/probe for/else logic — every branch (override
  hit, cached hit, corpus-derived guess, verified guess, undetermined probe, no-candidate slug)
  still lands in the map or in `unprobed` correctly; nothing silently caches a null on a failed
  probe.
- `feats.py` `_api_list_all`'s continuation-following and `_CAP_BOUND` accounting — the
  repeated-token stop condition and the ran-out-of-answer path both count rather than silently
  truncate; `discover()`'s ranked-not-cut title/page lists are consistent with Hard Rule 0.
  `resolve_title`'s ranking (exact match, then name-opens-title with a size tiebreak) is sound.
- `feats.py` `mine()`'s exponent capture (groups 2/3 of `_QUANTITY`) and the unit-first Mach
  alternative — both fold correctly into one `exponent`/`quants` shape; nothing is dropped.
- `feats.py` `roll()`'s counter bookkeeping (`done`, `deferred`, `_UNCACHED`, `_STALE_GATE`,
  `_CAP_BOUND`, `_RATE_LIMITED`) and the deferred-tail re-run — nothing is double-counted or
  silently dropped; the exit-code logic in `main()`'s `--roll` branch correctly fails the run on
  zero jobs or all-errored.
- `feats.py` `evidence_for()`'s cache-staleness gauntlet (`mined_under_superseded_gate`,
  `mined_without_name_matching`, `mined_under_old_marker_layer`, `mined_under_failed_transport`)
  — the four predicates are mutually exclusive in scope (wiki vs. non-wiki, title-lookup vs.
  name-match) and none can silently authorize a stale record.
- `ledger_guard.py`'s `check_structure`'s heading-vs-substring section detection, `seal()`'s
  floor-ratchet and temp-file cleanup (`except (OSError, NameError)`), `verify_chain()`'s
  bytes-vs-chars unit reconciliation across the legacy/current boundary, and
  `_load_acknowledgements()`'s fail-closed shape validation — all re-checked directly; all still
  correct.
- `estate.py` `inspect()`'s TOCTOU-guarded stat/read paths (retry-then-distinguish
  GONE-from-UNREADABLE) and `_effective_ext`'s backup-marker peeling — both still refuse rather
  than silently authorize, and both correctly distinguish a benign race from a real fault.
  `artifacts()`'s root discovery (walking `os.scandir(HERE)` rather than a hand-kept list) is
  consistent with its own comment about the 60-file gap it closed.
- `autostart.py`'s tri-state (`True`/`False`/`None`) `supervisor_alive()` propagation through
  `_start_decision()`, `watch()`, and `main()`'s two chained ternaries — re-traced; all three
  preserve the three-way distinction end to end, including the halt-before-budget ordering in
  `_start_decision()`.
- `pick_model.py` — full re-read past the fixed VRAM-unit bug: `family_tier()`'s ordering
  (longer/more-specific family strings before their own prefixes), `parse_param_size()`'s
  tag-name fallback regex, `resident()` vs. `fit_note()`'s two distinct budget questions
  (total-minus-reserve vs. free-right-now, each labeled which is which), `save_config()`'s
  gated/atomic write, and `main()`'s `is not None`/`is False` tri-state handling around
  `vram_measured`/`vram_gb` — all correct.
- `snapshot.py`'s `_rel()`/`_safe_join()` path-containment refusals, `before()`'s
  partial-snapshot refusal (`allow_missing`), and `restore()`'s missing-file accounting against
  the manifest — all still refuse rather than under-restore silently.
- `context_budget.py`'s two-ratio arithmetic (`CHARS_PER_TOKEN` vs. `PROSE_CHARS_PER_TOKEN`)
  through `content_budget_chars()`, `feats_block_budget()`'s `JOB_OVERHEAD_CHARS`/
  `METADATA_INFLATION` corrections, and `_read_scaffold()`'s fail-closed absent-vs-unreadable
  split — every conversion is still conservative in the direction the module argues for.
- `scale_theories.py` — confirmed still intentionally unwired dead-but-authored content per owner
  ruling `01695fe3ef26`; `surviving_theory()`'s field-based (not prose-prefix) selection and its
  arity assertion are both still correct.

## Summary of findings by kind

- Checks that cannot fail: 0
- Fail-open guards: 0
- Caps/truncations hiding roster/entry-list data (Hard Rule 0): 0
- Real logic bugs (wrong variable, off-by-one, race, inverted condition, regex/escape
  corruption): 0 new (2 prior findings confirmed fixed by direct execution/inspection — see
  "Prior-audit cross-check")
- Comments/docstrings asserting behavior the code does not have: 0
- Suppressed exceptions turning a failure into a plausible negative: 0

## Coverage recorded

Ran `sweep_plan.record('run65', ['feats.py', 'ledger_guard.py', 'estate.py', 'autostart.py',
'pick_model.py', 'snapshot.py', 'context_budget.py', 'scale_theories.py'], batch=5)` from the kit
directory after this file was written.
