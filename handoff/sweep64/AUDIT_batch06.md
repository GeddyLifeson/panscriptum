# sweep64 batch 06 audit

Auditor for maintenance run #64 (2026-09-26), batch 06. Read-only on `src/`, `data/`, `state/`
throughout — nothing under those trees was edited, created or deleted except this report and the
`sweep_plan.record` call at the end. Did not run drill.py, verify_math.py, generate.py, the
pipeline, publish, mutate, or `workorders.py --sweep/--resolve`. Did not spawn subagents. No
backticks, prose, or regexes were passed through a shell command; this file was written directly
with the Write tool.

## Scope (every line read, start to finish, in chunks; no sampling)

- `src/workorders.py` — 2511 lines (read 1-400, 400-799, 800-1199, 1200-1599, 1600-1999,
  2000-2299, 2300-2511)
- `src/rigor.py` — 1132 lines (1-400, 400-799, 800-1132)
- `src/identity.py` — 752 lines (1-400, 400-752)
- `src/endpoint.py` — 654 lines (1-330, 330-654)
- `src/scope.py` — 473 lines (whole file)
- `src/genre.py` — 385 lines (whole file)
- `src/events.py` — 350 lines (whole file)
- `src/cosmology_graph.py` — 261 lines (whole file)
- `src/whoruns.py` — 159 lines (whole file)

Total: 6,677 lines across 9 modules, all read in full.

## Method and prior-audit cross-check

`CLAUDE.md` (Hard Rule -1 escalation/halt, Hard Rule 0 no caps, fail-closed, "a check that cannot
fail looks exactly like a check that passed") read first. `handoff/sweep63/` was grepped for all
nine module names before reading source; the audits that turned up were read in full:

- `AUDIT_batch06.md` (sweep63) — this exact grouping of files, read by a prior instance of this
  batch: findings were `workorders.py`'s `_fire` polarity bug (already fixed, comment cites it) and
  a `pipeline.py`/`category`-field gap (pipeline.py is not in this batch). `rigor.py` carried one
  still-open QUESTION (`adjudication_beta`'s `k=max(1,...)` clamp, dormant, no caller) — re-checked
  this pass, unchanged, not re-filed.
- `AUDIT_batch03.md` (sweep63) — covers `endpoint.py`: no findings, one non-finding observation
  (register()'s bare `raise` vs. source_pages()'s wrapped exception on an unreadable registry) —
  re-checked, still true, still not a defect.
- `AUDIT_batch07.md` (sweep63) — covers `scope.py`: no findings.
- `AUDIT_batch11.md` (sweep63) — covers `cosmology_graph.py` and `whoruns.py`: no findings in
  either (the batch's one finding was in `dashboard.py`, outside this scope).
- `AUDIT_batch12.md` (sweep63) — covers `events.py`: no findings.

`identity.py` and `genre.py` were not named in any sweep63 audit surfaced by the grep; read fresh.

Per the brief: today's run #64 changed `BINDING_HEALTH_STALE`'s handler from `BOTS` to `RUN`
(workorders.py, in the section commented "run #64, 2026-09-26" below), on the grounds that nothing
schedules `binding_health --run`. This prompted a specific check across every other detector in
`workorders.py`: does its addressed rung actually have a bot (or a scheduled run) able to close it.
That check is Finding 1.

## Findings

### 1. VERIFIED — `workorders.py`: two detectors file at handler `BOTS` whose only closing
mechanism is a manual, unscheduled CLI invocation — the same shape run #64 just fixed for
`BINDING_HEALTH_STALE`, left unfixed here

**HOST_QUARANTINED** (workorders.py:1524-1530):

```python
# 3. quarantined wiki hosts -- one order per host, so each closes on its own recovery
try:
    import binding_health as BH
    q = BH.quarantined()
    for host, rec in sorted(q.items()):
        filed.append(file_order("HOST_QUARANTINED", "%s: %s" % (host, rec.get("reason", "")),
                                "BOTS", "MINOR", where=host, found_by="binding_health"))
```

**BINDING_SUSPECT** (workorders.py:1546-1652, filing at 1644-1652), with the section's own stated
reason for the rung:

```python
    # 3b. HOSTS THAT ARE UP BUT WHOSE TITLES DO NOT RESOLVE. Not a quarantine -- the host is
    #     serving -- so nothing above would ever file it, and until run #33 nothing did: the
    #     canary had no verdict for "the binding is wrong" and reported it as a dead host.
    #     Filed at BOTS because `hostcheck.py --repair` is the tool that re-probes a binding.
    ...
            else:
                # UNCLASSIFIED, UNKNOWN, or a canary record written before identity probing
                # existed. Kept at the old code and the old rung, because "I could not tell"
                # must not be filed as either answer.
                filed.append(file_order(
                    "BINDING_SUSPECT",
                    "%s answers its API but none of its catalogued titles resolve, and "
                    ...
                    "BOTS", "MINOR", where=host, evidence=h.get("reason"),
                    found_by="binding_health.canary"))
```

Both codes are only closed by a host's identity being re-probed and coming back healthy — that
verdict is produced solely by `binding_health.py`'s `canary()` (called for `HOST_QUARANTINED`'s
release via `binding_health.release()`, and for `BINDING_SUSPECT` via the identity probe the
section's own comment names, `hostcheck.py --repair`, i.e. `hostcheck.sweep(repair=True)`).

Traced every caller of both:
- `grep -rn "\.canary(" src/*.py` (excluding `binding_health.py` itself): the only call sites are
  inside `binding_health.py`'s own `run()` (dispatched by `binding_health.py --run`, a human
  command) and `drill.py`'s synthetic halt-rehearsal tests, which monkey-patch `BH.canary` to a
  fake lambda rather than exercising the real probe (`drill.py:9245`, `drill.py:10040`).
- `grep -rn "repair=True" src/*.py`: the only call sites are `hostcheck.py:1730`
  (`sweep(only=a.only, repair=a.repair, ...)`, i.e. the CLI's own argparse dispatch — a human
  typing `--repair`) and `drill.py:14693`/`14700` (the halt drill's own synthetic rehearsal).
- `grep -n "hostcheck" src/foreman.py src/overwatch.py src/overnight.py src/autostart.py`: the
  only automated caller of `hostcheck.py` anywhere is `foreman.py:273`,
  `["hostcheck.py", "--adopt", "--go", "--workers", "3"]` — `--adopt`, never `--repair`, and
  `hostcheck.py` itself never touches quarantine or binding identity from the `--adopt` path
  (`grep -n "quarantine\|binding_health" src/hostcheck.py` returns only comments citing the other
  module, no import or call).
- `grep -rn "binding_health\.quarantine\|binding_health\.release\|import binding_health" src/*.py`
  (excluding `binding_health.py`/`workorders.py`): `feats.py` imports it and calls
  `BH.quarantine(host, ...)` (to SET a quarantine, during ordinary mining throttling) and
  `BH.is_quarantined`/`BH.quarantined` (to read it) — it never calls `release()`. No caller of
  `release()` exists anywhere outside `binding_health.py`'s own `canary()`.
- "the keeper" (the standing-daemon restarter `codewatch.py`/`overnight.STANDING` describe) only
  restarts a daemon that has exited; it does not invoke one-off maintenance scripts like
  `binding_health.py --run` or `hostcheck.py --repair` on any cadence.

So both orders are addressed to "the repo's own machinery: foreman remedies, overwatch, the
keeper" (workorders.py's own definition of BOTS at the top of the file), but no such machinery
ever runs the one action (`binding_health.py --run`/`--repair`) that could close either of them.
This is the exact shape the run #64 fix for `BINDING_HEALTH_STALE` (workorders.py:1583-1592,
handler changed BOTS -> RUN with the comment "nothing schedules `binding_health --run`, an
operator runs it by hand ... The daily run is the operator") already names and fixes for a third
code in the same section — but the fix was not extended to the two sibling codes filed by the same
`binding_health` canary a few lines away in the same function.

**Concrete failure scenario.** A host throttles repeatedly during ordinary mining; `feats.py`
quarantines it and `workorders.sweep` files `HOST_QUARANTINED` at BOTS. The host's own problem
(a rate limit, a transient block) clears within hours in reality, but nothing schedules
`binding_health.py --run` (or a targeted `--host` re-probe) to notice — per the same
`BINDING_HEALTH_MAX_AGE` comment (workorders.py:160-167) that says it plainly: "unlike the
battery's two artifacts, nothing schedules `binding_health --run` on a cadence ... an operator
runs it by hand." The order sits open at BOTS indefinitely — not because the host is still bad,
but because the rung it is addressed to has no staffed process able to re-probe it — until a
person happens to run the ~200-page canary by hand. The same applies to a `BINDING_SUSPECT` host:
its "unclassified" identity can only be resolved by the identity probe inside `canary()`/
`--repair`, which likewise waits on a human. Meanwhile `for_ladder()`'s BOTS section of the printed
queue accumulates orders that read as "cheap work already being handled by the machinery" when in
fact nothing is working them at all — the same "undeliverable order at a cheap-looking rung" harm
`ORDER_ADDRESSED_TO_A_RUNG_THAT_CANNOT_REACH_IT` (workorders.py:2018-2073) exists to catch for
LOCAL, but there is no equivalent detector for BOTS.

**Not filed as a fix**: read-only batch. The mechanical remedy is the same one run #64 already
applied one code over — reroute both to RUN (or otherwise wire an actual scheduled invocation of
`binding_health.py --run`) — but which is correct is a judgment call about whether these should be
scheduled or reassigned, which this batch leaves to the owner/next fix, consistent with the brief's
instruction to report rather than edit.

## Everything else — no further findings

The remaining eight files were read in full and, beyond Finding 1 above, no new fail-open branch,
tautological/unfalsifiable check, cap-then-truncation (Hard Rule 0), wrong-variable/off-by-one bug,
race, comment/code mismatch, regex/escape corruption, or silent-exception-as-negative was found.
Specific things traced by hand and ruled sound:

- **workorders.py**: `_mutate`'s compare-and-swap (digest-before-read, pid+thread+attempt temp
  names); `file_order`/`resolve`/`reroute`'s cap-boundary refusals (`_refuse_cap_hit` reads the
  same `LEGACY_CAP_BOUNDARY` `cap_boundary_scan` grades); `resolve()`'s "did it land, then did it
  exist" ordering; `is_selftest`/`SELFTEST_SUBJECT` and the `LOCAL_AGENT_BLAST_CAP` closer-marked
  exception; `ghost_orders()`'s time-based (not disjointness-based) ghost test; `_fire`'s polarity
  (healthy resolves, unhealthy files — the sweep63 fix is intact); every other handler assignment
  in the file (`LEDGER_STRUCTURE`/`LEDGER_CHAIN` at RUN/SESSION, `LIVENESS_RATCHET`/`STALE_CITATION`
  at LOCAL, `BINDING_RIGHT_ENTRY_NAMES_ARE_NOT_TITLES`/`BINDING_HOST_SERVES_ANOTHER_WIKI` at OWNER,
  `SECRET_STAGED` at SESSION, the battery codes at RUN, `AGENT_SCRATCH_IN_PUBLISHED_TREE`/
  `CAP_BOUNDARY`/`CLOSED_ORDER_BACK_IN_THE_OPEN_QUEUE`/`ORDER_ADDRESSED_TO_A_RUNG_THAT_CANNOT_
  REACH_IT` at RUN) checked against what actually runs them and found staffed or legitimately
  self-closing, unlike the two named above.
- **rigor.py**: `_validate_reciprocal_matrix`'s refuse-rather-than-clamp preconditions;
  `theorem_1_check`'s two-sided, None-aware CR/curl-fraction test; `bradley_terry`'s Ford's-
  condition check (evaluated independently per the sweep61 un-chaining, not as an unreachable
  elif); `gumbel_return_level`'s three-way named-reason branch; `mathematical_resonance`'s uncapped
  `load_bearing` ranking and `main()`'s tie-respecting display cut. No restated numeric literal
  found drifting from its live table (the module's own stated failure mode).
- **identity.py**: `_is_continuity`'s three structural tests (orthography/branching/population),
  including the n==1 special case (verified algebraically identical to the general
  `shared >= (n//2)+1` formula at n=1, so not a live divergence, just an explicit case for
  clarity); `load()`'s three-way absent/unreadable/stale handling and its "never persist an empty
  mine over a populated cache" guard; `epoch_of`'s `strict=True` UNPROBED-vs-unmarked distinction.
- **endpoint.py**: `_save()`/`register()`'s merge-not-overwrite compare-and-swap (both re-read,
  re-apply their own dirty/changed keys against the winner's copy rather than a blind overwrite);
  `fetch_raw_verdict`'s not_found/refused/errored tally, including the 200-with-HTML-body case;
  `detect()`'s DEAD_TTL re-probe logic. The one known non-finding (bare `raise` in `register()`'s
  unreadable branch vs. `source_pages()`'s wrapped exception) re-verified unchanged and still not
  a correctness issue.
- **scope.py**: `scope_for`'s `ProbeUnread` distinguishing "not read" from "read, nothing cleared
  MIN_MENTIONS"; the highest-tier-clearing-the-floor selection (not argmax, not frequency);
  `build()`'s per-host stamp-vs-contract selection (not membership-based) and its exclude-on-
  transport-failure-without-caching logic; `mutate()`'s compare-and-swap. `ceiling_for()` remains
  correctly self-reported dead code (order de43fe54feb7); not re-filed.
- **genre.py**: `classify_text`/`classify_source`'s uncapped, unranked-away scoring and honest
  full-field confidence denominator; the `ranked[0][1]==0` guard (verified `most_common(None)`
  always returns every GENRES key, so the removed `not ranked` disjunct really was unreachable, not
  a live safety net removed).
- **events.py**: `_looks_like_a_sentence`'s two mechanical (non-grammar-guessing) refusal rules;
  `_fragments`' joiner-based, shape-checked split; `parse()`'s heading/no-heading event dedup by
  `seen`, and the age-lookup (`reversed(heads[:idx+1])`) correctly including the event's own
  heading when it is itself level-2.
- **cosmology_graph.py**: the inverse-frequency weight formula matches its docstring exactly
  (`1/log(n+1.5)`, `x0.15` above `UBIQUITOUS_CUTOFF`); `--write` emits every pair and cluster
  uncapped, with `threshold_applies_to: "clusters"` stated so the artifact cannot misdescribe
  itself the way order 9861c18b8485 recorded it once doing.
- **whoruns.py**: `script_of`'s `-m`/`-c` short-circuit and `_FLAGS_WITH_A_VALUE` two-token skip;
  `running()`'s tri-state (None = unmeasurable, correctly distinct from an empty list) and its use
  of `ON._in_this_tree` to avoid a mutation-sandbox false positive.

## Questions (not findings)

None met the bar for reporting beyond what prior sweeps already raised and left open in modules
outside this batch (e.g. `rigor.py`'s dormant `adjudication_beta` clamp, restated above as
unchanged, not re-argued here).

## Coverage

Recorded via `sweep_plan.record('run64', [...], batch=6)` for all nine modules listed above, each
read in full this session, none substituted or skipped.
