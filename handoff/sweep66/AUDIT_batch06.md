# sweep66 batch06 audit

Auditor for maintenance run #66 (2026-09-27), batch 06. Read-only throughout: nothing under
`src/`, `data/`, `state/`, `output/`, `prompts/`, `reference/` or the repo root was edited,
created or deleted this session, other than this file and the single permitted
`sweep_plan.record(...)` call. No pipeline, generate, publish, crawl, overwatch, foreman, mutate,
drill or verify_math invocation was run, and nothing that clears a halt or touches
`prose_enabled`/`step4_enabled` was called. No subagents were spawned. One standalone,
read-only repro was run against the live `local_agent` module (import + pure function calls only,
no writes, no state touched) to verify Finding 1 below; it is reproduced in full under that
finding.

## Scope — every line read, start to finish, in chunks, no sampling

- `src/workorders.py` — 2,511 lines (chunks: 1-500, 500-999, 1000-1499, 1500-1999, 2000-2511)
- `src/rigor.py` — 1,132 lines (chunks: 1-400, 400-799, 800-1132)
- `src/identity.py` — 752 lines (chunks: 1-400, 400-751, tail re-verified at 748-752)
- `src/endpoint.py` — 654 lines (chunks: 1-400, 400-653, tail re-verified at 653-654)
- `src/backfill.py` — 494 lines (one read)
- `src/recover_folder_records.py` — 380 lines (one read)
- `src/wh40k.py` — 353 lines (one read)
- `src/halo.py` — 219 lines (one read)
- `src/chord_field.py` — 210 lines (one read)

Total: 6,705 lines across 9 modules, all read in full this session.

## Method and prior-audit cross-check

`CLAUDE.md` read first (Hard Rule -1 escalation/halt, Hard Rule 0 no caps ever, fail-closed
doctrine, "a check that cannot fail looks exactly like a check that passed"). `handoff/sweep65/`
was grepped for all nine module names before reading source, and every audit that named one of
them was read in full before drawing any conclusion:

- `handoff/sweep65/AUDIT_batch06.md` — the identical five-module core of this batch
  (`workorders.py`, `rigor.py`, `identity.py`, `endpoint.py`, `backfill.py`), paired last sweep
  with four modules not in this batch. It reported **zero new findings** and one item carried
  forward from sweep64: `workorders.py`'s `HOST_QUARANTINED`/`BINDING_SUSPECT` still filing at
  BOTS with nothing able to close them. Re-verified against current source below — still true,
  unchanged line numbers (`workorders.py:1529`, `:1644-1652`).
- `handoff/sweep65/AUDIT_batch03.md` — covers `recover_folder_records.py` and `wh40k.py` (among
  five modules not in this batch). It filed one fresh finding against each: a
  `write_record_catalogue` merge-slicing defect in `pipeline.py` (not in this batch, not
  re-checked), and a **stale present-tense comment inside `wh40k.py`'s `main()`** claiming the
  ROSTER still needed a 55-axis provenance reading that order `82fc93f056d4` had already done.
  Re-verified against current source: **FIXED**. `wh40k.py`'s `compute()` docstring now reads,
  verbatim, "(Order 82fc93f056d4 has since tagged all 55 `wiki` or `canon`; see compute()'s
  docstring. Stale present tense corrected by sweep65 batch03.)" at line 318. Closed, not
  re-filed.
- `handoff/sweep65/AUDIT_batch09.md` — covers `chord_field.py` (among eight modules not in this
  batch). Zero findings; cleared `landauer_floor`, `recoil_momentum`, `recoil_velocity`,
  `critical_power_self_focus` as standard-physics formulas checked by hand. Re-verified: still
  correct, unchanged.
- `handoff/sweep65/AUDIT_batch16.md` — covers `halo.py` (among eight modules not in this batch).
  Zero findings; cleared the per-axis provenance tagging and the gated atomic write. Re-verified:
  unchanged, still correct.

I also searched `state/workorders.json` (a read-only copy, since the live file is
permission-locked to this process) for every module name, for the specific codes involved in the
sweep65 carried-forward finding (`HOST_QUARANTINED`, `BINDING_SUSPECT`,
`ORDER_ADDRESSED_TO_A_RUNG_THAT_CANNOT_REACH_IT`), and for the terms involved in Finding 1 below
(`DENYLIST_PATHS`, `DENYLIST_PREFIXES`, `misrouted-local`, `_denied_target`, `config.yaml`) before
writing anything down. Only one hit came back for the latter group (order `d2f103634cf1`, a
different, already-known SUSPECTED item about hard links bypassing `_protected_identities()` in
`local_agent.py` itself — not this finding, and not re-filed here).

Beyond re-checking the above, I read every module myself, end to end, hunting in priority order
for: fail-open branches, tautological/unfalsifiable checks, caps-then-truncation of a ranked
roster (Hard Rule 0), wrong-variable/off-by-one/inverted-condition bugs, races on shared files,
comment/code mismatches, silently swallowed exceptions manufacturing a false negative, dead code a
comment claims is live, and regex/escape corruption.

## Findings

### 1. CONFIRMED (reproduced by execution) — `workorders.py`'s own LOCAL-denial guard and its
`misrouted-local` detector both use a narrower predicate than `local_agent._denied_target`, and
are blind to anything denied only via `DENYLIST_PATHS`, `DENYLIST_PREFIXES`, or a non-`.py`
target

Two places in `workorders.py` exist specifically to stop an order sitting, undeliverable, on the
LOCAL rung:

- `file_order`'s own door check (`workorders.py:550-564`), filed under order `9b54659bc403`,
  which is supposed to catch a LOCAL order at the moment it is filed and re-route it to RUN if
  its `where` names a target the local model may never write:

  ```python
  if handler == "LOCAL":
      try:
          import local_agent as _LA
          targets = sorted(set(m[0] for m in WHERE_TARGET.findall(
              str(where or "").replace(chr(92), "/"))))           # order 5b00f9d39b94
          if targets and all(_LA._denied_target(t) for t in targets):
              found_by = ... "filed at RUN, not LOCAL" ...
              handler = "RUN"
      except Exception:
          pass
  ```

- `sweep_detectors`'s `misrouted-local` detector (`workorders.py:2036-2073`), filed under order
  `f19f4a2b00f4`, which is supposed to catch it after the fact, on any open order, however it got
  there:

  ```python
  _rx_mod = __import__("re").compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.py\b")
  ...
  _mods = set(_rx_mod.findall(str(_rec.get("where") or "")))
  if not _mods:
      continue
  _denied = sorted(m for m in _mods if m in _LA.DENYLIST)
  if _denied and not [m for m in _mods if m not in _LA.DENYLIST]:
      _stuck.append(...)
  ```

Both extract candidate targets from `where` with a regex that **requires a literal `.py`
suffix** — `WHERE_TARGET` (module-level, shared with `twins()`/`where_targets()`) and the
detector's own private `_rx_mod`. Neither regex can ever match `config.yaml` (the sole member of
`local_agent.DENYLIST_PATHS`) or any file under a `DENYLIST_PREFIXES` region that is not itself a
`.py` file — e.g. anything under `reference/keystone_volumes/`, `state/`, or `data/records/`
that carries a `.md` or `.json` extension. And even when a `.py` target under a protected
*region* IS extracted (because it happens to end in `.py`), the detector's own check —
`m in _LA.DENYLIST` — asks only "is this bare module name on the fixed name list", never
`local_agent._denied_target(t)`, the fuller predicate `file_order`'s own door check already
correctly uses one function up. `DENYLIST_PREFIXES` membership is invisible to that narrower
test.

**Reproduced by execution**, importing `local_agent` directly and comparing its live
`_denied_target` against both of `workorders.py`'s extraction/check paths, with nothing written
anywhere:

```
>>> WHERE_TARGET.findall('config.yaml')                                    -> []
>>> _rx_mod.findall('config.yaml')                                         -> []
>>> local_agent._denied_target('config.yaml')                              -> True

>>> WHERE_TARGET.findall('reference/keystone_volumes/00_MASTER_CHARTER.md') -> []
>>> _rx_mod.findall('reference/keystone_volumes/00_MASTER_CHARTER.md')     -> []
>>> local_agent._denied_target('reference/keystone_volumes/00_MASTER_CHARTER.md') -> True

>>> WHERE_TARGET.findall('reference/keystone_volumes/some_script.py')
    [('reference/keystone_volumes/some_script.py', '', '')]
>>> _rx_mod.findall('reference/keystone_volumes/some_script.py')          -> ['some_script']
>>> 'some_script' in local_agent.DENYLIST                                  -> False
>>> local_agent._denied_target('reference/keystone_volumes/some_script.py') -> True
```

So for a `where` naming only `config.yaml`, or only a non-`.py` file under a protected prefix,
`file_order`'s door check computes `targets = []`, the `if targets and all(...)` guard
short-circuits on the empty list, and the order is filed and stays at LOCAL with no re-route —
silently. The `misrouted-local` detector fares no better: `_mods` comes back empty, `if not
_mods: continue` skips the order outright, so it is not reported as "stuck" either. And for a
`.py` file that IS extracted but is denied only through `DENYLIST_PREFIXES` (a protected
*region*, not a named module), the detector's `m in _LA.DENYLIST` test also misses it, even
though `_denied_target` — sitting one function away and already imported into this exact
detector — would say `True` immediately.

**Failure scenario, concrete.** Any future detector or hand-filed order that calls
`file_order(code, what, "LOCAL", where="config.yaml", ...)` (the config that names every
model/host/`num_ctx` in the kit, and the one thing `local_agent.py`'s own comment calls out by
name as denied "because every module in the kit reads it ... and unlike a broken .py it fails
silently rather than at import") — or one naming a non-`.py` file under
`reference/keystone_volumes/` (the charter itself, which Hard Rules 2-4 already reserve to the
owner) — would sit at LOCAL forever. `sweep_detectors`'s `misrouted-local` check, whose own
docstring says exactly this shape is "worse than an open order at RUN because ... it reads as
work waiting to be picked up, and every shift re-reads it and moves on," would never flag it,
because its own extraction regex cannot see the target at all.

**Not currently live**: the queue holds exactly one open LOCAL order right now
(`018727423a09`, `where="dashboard"`), which matches neither pattern, so nothing is silently
stuck on this gap today. This is a genuine code-behaviour gap, verified by direct execution
against the live `local_agent` module, not a currently-firing incident — reported as a finding
rather than a live-queue emergency for that reason.

**Not already filed.** `state/workorders.json` was searched for `DENYLIST_PATHS`,
`DENYLIST_PREFIXES`, `misrouted-local`, `_denied_target` and `config.yaml`; the only hit,
order `d2f103634cf1` item 2, is the unrelated, already-known SUSPECTED finding about hard links
bypassing `_protected_identities()` inside `local_agent.py` itself (a different mechanism: that
one is about identity-based bypass of the identity/prefix checks; this one is about
`workorders.py`'s own two callers never reaching `_denied_target` for anything that isn't a bare
`.py` module name). Filing fresh, as a finding rather than a work order per this sweep's
read-only rule.

**Proposed fix** (not applied — read-only sweep): have both call sites ask `_denied_target`
directly against every `os.path`-shaped token in `where`, rather than filtering to `.py` names
first. `file_order`'s existing `WHERE_TARGET.findall` already captures non-`.py` paths reasonably
well if the trailing `\.py` requirement in the regex is loosened for this one call site (or a
second, permissive extraction is used just for the local-denial door check and the
`misrouted-local` detector), and the detector should call `_LA._denied_target(t)` instead of
`t in _LA.DENYLIST` for the same reason `file_order`'s door check already does.

### 2. Carried forward (already known, still true) — `workorders.py`: `HOST_QUARANTINED` and
`BINDING_SUSPECT` still file at BOTS with no bot able to close them

Restated briefly per this sweep's instruction not to re-derive an unchanged finding at length.
Still true at `workorders.py:1529` (`HOST_QUARANTINED`, handler `"BOTS"`) and `workorders.py:1644-
1652` (`BINDING_SUSPECT`, handler `"BOTS"`). Both close only via `binding_health.py`'s `canary()`
(`release()`/re-probe) or `hostcheck.py --repair`, both hand-run CLI actions with no scheduled
caller. The sibling code `BINDING_HEALTH_STALE` in this exact same function was moved from BOTS to
RUN in run #64 (`workorders.py:1587-1592`, comment citing that exact history) but the fix was not
extended to these two. CONFIRMED (traced through current source; unchanged from sweep65). Not
filed as a work order here, consistent with the read-only rule and with sweep64/65's own choice —
rerouting is a judgment call for the owner, not a mechanical repair.

## Questions (possible deliberate design, not findings)

Nothing new met the bar this batch. One item is already on file and restated only for
completeness, not re-filed: `rigor.py:670`'s `adjudication_beta`, `k = max(1, min(n_laws_touched,
M))`, charges one law even when zero were touched — already recorded as sweep61's question 6
(order `28f335ecefd3`), unchanged in current source, every live caller passes `laws >= 1` today.

## Cleared — examined closely this session, found correct (beyond re-confirming sweep65's
clearances)

- **workorders.py**: `_mutate`'s compare-and-swap (pid+thread+attempt temp names,
  digest-before-read); `_fire`'s healthy-resolves/unhealthy-files polarity at every call site
  (battery, ledgers, bindings, secrets, drill-close, stranded-synthesis, handoff-scratch,
  cap-boundary, ghost-order, misrouted-local, citations); `resolve()`'s "did it land, then did it
  exist" ordering; `reroute()`'s three-way disposition and its `_refuse_cap_hit` handling on
  `found_by` for both the moved and already-there cases; `ghost_orders()`'s time-based (not
  disjointness-based) test; `twins()`'s interval-overlap clustering (`_span`, the overlap
  predicate `s2[1] <= s[2] and s[1] <= s2[2]`); `cap_boundary_scan`'s open/closed split; the
  `LEGACY_CAP_BOUNDARY` table deliberately excluding `resolution` from `_refuse_cap_hit` (that
  field only ever lands in the append-only closed log, which `cap_boundary_scan`'s own docstring
  already treats as "a measurement, not a failure" rather than something to refuse at write time
  — confirmed this is documented reasoning, not an oversight).
- **rigor.py**: `_validate_reciprocal_matrix`'s four independent refusals; `perron_weights`/
  `logrank_weights`/`theorem_1_check`'s two-sided, None-aware CR/curl-fraction tests;
  `bradley_terry`'s Ford's-condition check as two independent faults (verified un-chained, not an
  unreachable `elif`) and its `prior`-vs-raw-graph distinction; `adjudication_beta`'s MDL
  counting; `mathematical_resonance`'s uncapped `load_bearing` ranking and `main()`'s
  tie-respecting display cut (`while _cut < len(_lb) and _lb[_cut][1] == _lb[_cut-1][1]: _cut +=
  1`).
- **identity.py**: `_is_continuity`'s three structural tests, including the `n==1` branching case
  and the general majority formula `shared >= (n // 2) + 1` (only ever reachable at n==2 given
  `MIN_BEARERS=3`, and correct there); `load()`'s three-way absent/unreadable/stale handling and
  its refusal to persist an empty mine over a populated cache; `_inv_keys`'s multi-spelling
  fallback (the sweep63 "falls through on a falsy-but-empty entry" question re-verified: harmless,
  since an empty dict at any key spelling produces the same empty `continuities()` result whether
  or not the fallback triggers — matches the existing "no reachable harm found" verdict, not
  re-filed); `epoch_of`'s `strict=True` UNPROBED-vs-unmarked distinction.
- **endpoint.py**: `_save()`'s merge-not-overwrite compare-and-swap; `detect()`'s DEAD_TTL
  re-probe asymmetry; `fetch_raw_verdict`'s not_found/refused/errored tally including the
  200-with-HTML-body case; `source_pages`/`register`'s absent-vs-unreadable distinction, both
  directions, including the fixed `register()` merge-and-retry-before-raising path.
- **backfill.py**: `roster()`'s uncapped category walk (top level + one level of subcategory,
  always walked); the `missing = sorted(..., key=lambda t: (t in sizes, -sizes.get(t, 0)))`
  ranking key, hand-traced against `sizes={A:100,C:5}`, B unmeasured -> `[B, A, C]`; `lead()`'s
  walk-forward-to-real-prose logic and its marked mid-word cut; `main()`'s `--all` exit code
  (`return 1 if denied else 0`, not counting per-source `errors` — this is the already-open OWNER
  question, order `0384c99d5454`, re-verified unchanged at `backfill.py:463`, not re-filed).
- **recover_folder_records.py**: the `mapped is None` vs. `mapped == []` distinction;
  `short_sources`'s declared-vs-yielded accounting; the `EXCLUDED_REGISTER_SOURCES` guard; the
  gated per-record write and the compare-and-swap `roll.update_rows` call, both propagating
  `denied` into the exit code.
- **wh40k.py**: `compute()`'s per-axis (not blanket) provenance tagging via `_provenance()`,
  defaulting to `unattributed` rather than `wiki`; the gated atomic `WH40K_ASSAYS.json` write; the
  `--full` wrapped (not cut) citation printing. The sweep65 stale-comment finding is fixed (see
  above). No new defect.
- **halo.py**: per-axis provenance tagging (here a direct `v[2]` index rather than a helper —
  every ROSTER entry is a 3-tuple, so this fails loudly with `IndexError` rather than silently
  defaulting if a future axis omits the tag, which is at least as safe as `wh40k.py`'s explicit
  fallback); the gated atomic write and its rc propagation; the uncapped, wrapped `--full`
  citation display.
- **chord_field.py**: `landauer_floor`, `recoil_momentum`, `recoil_velocity`,
  `critical_power_self_focus` — standard-physics formulas, re-checked by hand; `total_beta()`/
  `per_system_beta_without_unification()` arithmetic; no dead constants (`C_LIGHT`,
  `K_BOLTZMANN` both have live callers in this same file, per the module's own comment recording
  the removal of the two that did not).

## Coverage

`sweep_plan.record('run66', ['workorders.py', 'rigor.py', 'identity.py', 'endpoint.py',
'backfill.py', 'recover_folder_records.py', 'wh40k.py', 'halo.py', 'chord_field.py'], batch=6)`
run via a scratch script with the miniconda python; see reply for whether it landed.
