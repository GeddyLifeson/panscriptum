# Sweep66 batch08 — AUDIT (maintenance run #66, 2026-09-27)

READ-ONLY audit. Nothing under `src/`, `data/`, `state/`, `output/`, `prompts/`, `reference/` or
the repo root was edited. No subagents were spawned. No network calls were made.

## Scope (every line read, start to finish, via the Read tool, no grep-sampling)

- `src/cascade_bridge.py`   2340 lines (two chunks: 1-943, 944-2341)
- `src/sweep_plan.py`       1150 lines (one chunk, whole file)
- `src/catalogue_web.py`     821 lines (one chunk, whole file)
- `src/manifest_builder.py`  677 lines (one chunk, whole file)
- `src/catalogue_codex.py`   515 lines (one chunk, whole file)
- `src/sevenfold.py`         441 lines (one chunk, whole file)
- `src/catalogue_aurora.py`  328 lines (one chunk, whole file)
- `src/tuning.py`            286 lines (one chunk, whole file)
- `src/lognames.py`           52 lines (one chunk, whole file)

Total 6,610 lines across nine modules, all read completely this session, matching the frozen
plan's own line counts in `state/sweep_plan/run66.json` exactly (2340/1150/821/677/515/441/
328/286/52).

## Method and prior-audit cross-check

`CLAUDE.md` read first (Hard Rule -1 escalation/halt chain, Hard Rule 0 no caps ever, the three
safety properties — INDEPENDENT / FAIL CLOSED / PROVEN — and "a check that cannot fail looks
exactly like a check that passed"). `handoff/sweep65/` was then grepped for all nine module
names and every matching report read in full before source:

- **`handoff/sweep65/AUDIT_batch08.md`** — the closest predecessor by far: an almost identical
  nine-module batch (`cascade_bridge.py`, `sweep_plan.py`, `catalogue_web.py`,
  `manifest_builder.py`, `catalogue_codex.py`, `sevenfold.py`, `catalogue_aurora.py`, plus
  `cosmology_graph.py` and `whoruns.py` in place of this run's `tuning.py`/`lognames.py`).
  Sweep65 reported **zero new findings** and traced two sweep64 defects as CLOSED
  (`cascade_bridge.py`'s `ask()` metric mislabelling a non-dict success as a failure; the
  `manifest_builder.py` unassigned-sources report recomputing `provisional_spine` instead of
  reading the actual assigned `volume_code`). It also carried a long "Cleared" list detailing
  exactly what was hand-traced in each of the seven shared modules (the whole
  `cascade_bridge.py` failure-classification chain; `sweep_plan.py`'s freeze/compare-and-swap
  machinery; `catalogue_web.py`'s `_singular`/dedup/`save_roll` compare-and-swap;
  `manifest_builder.py`'s `load_record` resolution and `pack_feats` pagination;
  `catalogue_codex.py`'s manifest cross-check and collision reporting;
  `sevenfold.py`'s `_even_cuts`/`seams()` balance logic; `catalogue_aurora.py`'s slug/dedup
  key).
- **`handoff/sweep65/AUDIT_batch04.md`** — covers this run's other two modules,
  `tuning.py` and `lognames.py`, alongside five others. Zero new findings for either;
  `tuning.py`'s cleared list named `regime()`/`profile()`'s `_CACHE["buckets"]` coupling, the
  `workers()` "zero is a request" fix, and `cloud_success_rate`'s `MIN_CALLS_TO_JUDGE` floor;
  `lognames.py` was noted as a small, static constants module with no logic to fault.

This sweep's read was not a re-trust of sweep65's verdict: every one of the nine files was read
line-by-line against the *current* source (this project's own standing instruction is that a
prior audit can be wrong in either direction), with the specific claims above hand-checked
against the live text. **All of it still holds.** The order numbers, measured figures and fix
descriptions cited in sweep65's report (`c810cf64d278`, `2239a87c57f5`, `af47010df391`,
`9508f9322b4c`, `f307490add1e`, `097b8706b5df`/`497b8706b5df`, `6eb20e8d3565`,
`0a5019b2527e`, `2a48315d26e6`, `683c59f43829`/`5fcb628db94c`, etc.) match the comments and
code currently in place verbatim in every case checked. No drift was found in any of the nine
modules since sweep65.

`state/workorders.json` (1108 lines) was read in full and grepped for all nine module names.
Hits, all already-known and none newly derived here:

- `CASCADE_BRIDGE_HAS_NO_REACHABLE_MODEL` (line ~527) — an infrastructure/config finding about
  Cascade's local-model roster pointing at uninstalled Ollama models, not a code defect in this
  tree; the remedy is a change to `<CASCADE_HOME>/config.json`, outside this repo, and is
  already so documented in `cascade_bridge.py`'s own header comment.
- The Groq qwen `finish_reason`/`max_tokens` re-route (line ~747/753) — an open OWNER-rung
  question about `cascade_bridge.py`'s size-refusal handling needing an upstream Cascade engine
  change (surfacing `finish_reason`, accepting per-call `max_tokens`); explicitly re-routed to
  OWNER by run #61 with no code change expected from this tree until that's decided. Verified
  the size-refusal guard this order concerns (`_size_refusal_permanent`, `_SIZE_REFUSAL`) is
  unchanged and still does exactly the narrow thing its own comment says it does.
  `21c075e5e2d6`/`1e6f99e54b25` (line ~93) — the standing OWNER-rung question of which
  manually-invoked writers should refuse under a halt, naming `sevenfold.py` among many other
  modules across the tree; unchanged, not re-derived here, and not a defect — it is explicitly
  an open policy question the project's own doctrine says a run must not resolve unilaterally.
- `CATALOGUE_WEB_STORED_TYPES_NEED_RECATALOGUE` (line ~995) — a curatorial/cost decision about
  whether to spend multi-day pool time re-cataloguing already-fixed sources; not a code defect,
  already filed for the owner.
- No hit names `sweep_plan.py`, `manifest_builder.py`, `catalogue_aurora.py`, `tuning.py` or
  `lognames.py` as carrying any open defect-shaped order.

## Findings

**Zero VERIFIED defects. Zero SUSPECTED defects.** All nine modules match sweep65's clean
verdict against the live source read in full this session. Nothing in the diff between what
sweep65 saw and what is on disk now changes any conclusion — the files are, line for line,
either byte-identical to what sweep65's own quoted excerpts describe or carry only the fixes
sweep65 already logged as closed.

Specific defect classes actively checked and found absent in every module (not merely assumed
clean because a prior audit said so):

- **Caps/truncation (Hard Rule 0).** `MAX_PER_SOURCE = None` with an import-time tripwire in
  `catalogue_web.py`; `slug()`/`record_path()` uncapped in `catalogue_aurora.py` with legacy-cap
  fallback so old records aren't orphaned; `pack_feats()` in `manifest_builder.py` paginates
  oversized entities rather than truncating them; every collision/mismatch report in
  `catalogue_codex.py` (`norm_clashes`, `ambiguous`, `reg_ambiguous`, `dupe_elements`,
  `unmapped_types`) is printed uncapped; `sevenfold.py`'s per-branch tables and shelfmark
  samples are honestly headed as samples with the real totals printed alongside; `sweep_plan.py`
  has explicitly "NO exclusions, deliberately" in `modules()`.
- **Silent swallowing.** Every `except Exception` site checked in this batch either calls
  `silence.note(...)` with a distinct tag or is a deliberately total, documented fail-safe
  (e.g. `_bucket_of`, `provider_error` in `cascade_bridge.py`) whose docstring states why a
  diagnostic lookup must never take down the call it explains.
- **Guards that can be bypassed.** `MAX_PER_SOURCE`'s import-time `raise SystemExit` fires
  before any network work, closing the historical "cap re-introduced after the expensive part
  already ran" hole. `sweep_plan.freeze_plan()` refuses to recompute on anything but a
  genuinely-absent plan file (`"absent"` only), reporting `frozen: False` with a named reason
  otherwise. `cascade_bridge.OWNER_EXCLUDED` cannot be cleared by any code path — only by an
  owner editing the source.
- **Races on shared state files.** `sweep_plan.record()`'s per-shard-then-aggregate-fallback
  design, `catalogue_web.save_roll()`/`catalogue_codex.py`/`catalogue_aurora.py`'s
  `roll.update_rows` compare-and-swap (never a whole-document land), and
  `cascade_bridge.record_unrecognised()`'s twelve-attempt jittered compare-and-swap with
  read-back verification were all re-traced against the current code and are unchanged from
  sweep65's description.
- **Stale comments that now lie about the code.** None found. Every comment referencing an
  order number, a measured figure, or a "this used to be X" claim was checked against the
  code immediately below it in this pass; all agree.
- **Dead code.** `sweep_plan.coverage_map()` is still explicitly marked dead-but-kept (zero
  callers, documented as "the one written statement of what the authoritative view is").
  `MAX_PER_CATEGORY`/`CATEGORY_SCAN_DEPTH` in `catalogue_web.py` are still marked dead-but-kept
  as documentation of removed caps. `sweep_plan.py`'s `latest_run()` removal note is present and
  accurate (no `def latest_run` exists in the file; grep confirms). `lognames.py` has no logic
  to be dead.

No new defect was found in any of the nine modules.

## Questions (not findings)

None new. All three carried-forward items are OWNER-rung policy questions already on file, not
re-derived here and not defects:

1. **The `21c075e5e2d6`/`1e6f99e54b25` writers-under-a-halt question**, which names
   `sevenfold.py` among many modules across the tree. A ruling either way ("derived, regenerable
   artifacts may run under a halt" vs. "refuse") would change behaviour, but absence of a halt
   interlock in `sevenfold.py` today is deliberate pending that ruling, not a bug — per this
   sweep's own brief, an owner-held gate looking unnecessary is what it looks like when working.
2. **The Groq qwen `finish_reason`/`max_tokens` question** (order `af47010df391`'s open half,
   re-routed to OWNER by run #61) — needs a decision about the separate Cascade engine project,
   outside this repo's remit.
3. **`CATALOGUE_WEB_STORED_TYPES_NEED_RECATALOGUE`** — a curatorial cost/benefit decision about
   spending multi-day pool time re-cataloguing 156 sources whose stored `type` field predates
   the `first_cat`-provenance fix; explicitly filed as belonging to the owner, not something to
   fix unilaterally.

## Coverage recorded

Recorded via `sweep_plan.record('run66', ['cascade_bridge.py', 'sweep_plan.py',
'catalogue_web.py', 'manifest_builder.py', 'catalogue_codex.py', 'sevenfold.py',
'catalogue_aurora.py', 'tuning.py', 'lognames.py'], batch=8)` for all nine modules above, each
read in full this session, none substituted or skipped.
