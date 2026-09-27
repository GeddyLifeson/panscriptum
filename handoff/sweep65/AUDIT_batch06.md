# sweep65 batch06 audit

Auditor for maintenance run #65 (2026-09-26), batch 06. Read-only throughout: nothing under
`src/`, `data/`, `state/`, `output/`, `prompts/`, `reference/` or the repo root was edited,
created or deleted this session, other than this file and the single permitted
`sweep_plan.record(...)` call. No pipeline, generate, publish, crawl, overwatch, foreman, mutate,
drill or verify_math invocation was run, and nothing that clears a halt or touches
`prose_enabled`/`step4_enabled` was called. No subagents were spawned.

## Scope — every line read, start to finish, in chunks, no sampling

- `src/workorders.py` — 2,511 lines (chunks: 1-400, 400-799, 800-1199, 1200-1599, 1600-1719,
  1720-2019, 2019-2318, 2319-2511)
- `src/rigor.py` — 1,132 lines (chunks: 1-400, 400-799, 800-1132; tail re-verified at 1128-1132)
- `src/identity.py` — 752 lines (chunks: 1-400, 400-752; tail re-verified at 748-752)
- `src/endpoint.py` — 654 lines (chunks: 1-330, 330-654; tail re-verified at 653-654)
- `src/backfill.py` — 494 lines (one read)
- `src/retry_synthesis.py` — 379 lines (one read)
- `src/events.py` — 350 lines (one read)
- `src/audit.py` — 275 lines (one read)
- `src/compress_store.py` — 149 lines (one read)

Total: 6,696 lines across 9 modules, all read in full this session.

## Method and prior-audit cross-check

`CLAUDE.md` read first (Hard Rule -1 escalation/halt, Hard Rule 0 no caps ever, fail-closed
doctrine, "a check that cannot fail looks exactly like a check that passed"). `handoff/sweep64/`
was grepped for all nine module names before reading source, and every audit that named one of
them was read in full:

- `AUDIT_batch06.md` (sweep64) — the identical five-module core (`workorders.py`, `rigor.py`,
  `identity.py`, `endpoint.py`, `events.py`) plus four modules not in this batch. It reported one
  VERIFIED finding — see Carried-forward finding 1 below — and no others; everything else in
  those five modules was traced and cleared. Re-verified against current source; the finding is
  unchanged and the clearances still hold.
- `AUDIT_batch07.md` (sweep64) — covers `backfill.py` and `retry_synthesis.py` (among six modules
  not in this batch). Zero findings, one QUESTION about `retry_synthesis.py`'s exit code — see
  Carried-forward finding 2 below. Re-verified: still true, line numbers essentially unchanged.
- `AUDIT_batch16.md` (sweep64) — covers `audit.py` and `compress_store.py` (among seven modules
  not in this batch). Zero findings against either. Re-verified.

I also checked `state/workorders.json` for every module name and for the specific codes involved
in the carried-forward finding (`HOST_QUARANTINED`, `BINDING_SUSPECT`, `ORDER_ADDRESSED_TO_A_RUNG_
THAT_CANNOT_REACH_IT`) before writing anything down, so nothing below duplicates an order already
on file. `HOST_QUARANTINED`/`BINDING_SUSPECT` do have open per-host orders on file (that is their
documented, intended shape — one order per host), but no order anywhere addresses the meta-fault
itself (BOTS is not a staffed rung for these two codes); that gap was reported as a finding in
sweep64, not filed as a work order there (read-only batch), and is reported the same way here.

Beyond re-checking the above, I read every module myself, end to end, hunting in priority order
for: fail-open branches, tautological/unfalsifiable checks, caps-then-truncation of a ranked
roster (Hard Rule 0), wrong-variable/off-by-one/inverted-condition bugs, races on shared files,
comment/code mismatches, silently swallowed exceptions manufacturing a false negative, dead code
a comment claims is live, and regex/escape corruption. No new instance of any of these was found
in any of the nine modules.

## Findings

**Zero NEW findings.** Two items are carried forward from sweep64 because they remain true in the
current source and neither has been fixed or filed as a work order; both are restated briefly
rather than re-derived at length, per this sweep's own instruction not to re-file what a prior
audit already reported.

### Carried forward 1 — `workorders.py`: `HOST_QUARANTINED` and `BINDING_SUSPECT` still file at
BOTS with no bot able to close them

Still true at `workorders.py:1529` (`HOST_QUARANTINED`, handler `"BOTS"`) and `workorders.py:1644-
1652` (`BINDING_SUSPECT`, handler `"BOTS"`). Both close only via `binding_health.py`'s `canary()`
(`release()`/re-probe) or `hostcheck.py --repair`, and both of those are hand-run CLI actions —
traced again this session: no caller of `BH.release`/`canary(...repair)` exists in `foreman.py`,
`overwatch.py`, `overnight.py` or `autostart.py` outside `drill.py`'s synthetic rehearsals. Run #64
fixed the sibling code `BINDING_HEALTH_STALE` from `BOTS` to `RUN` in this same function
(`workorders.py:1587-1592`, comment: "nothing schedules `binding_health --run` ... The daily run is
the operator") but did not extend the same fix to these two. The `ORDER_ADDRESSED_TO_A_RUNG_THAT_
CANNOT_REACH_IT` detector (`workorders.py:2036-2073`) only checks the LOCAL rung against
`local_agent.DENYLIST`; it has no equivalent for BOTS, so this gap is invisible to the queue's own
self-check. CONFIRMED (traced through current source; unchanged from sweep64's finding). Not filed
as a work order here, consistent with the read-only rule and with sweep64's own choice — rerouting
is a judgment call (RUN vs. staffing an actual bot) left to the owner/next fix.

### Carried forward 2 — `retry_synthesis.py`: `main()`'s exit code tracks only the last save, not
whether every named source was rescued

Still true at `retry_synthesis.py:375` (`return 0 if landed else 1`). A run in which several
sources print "STILL FAILING" (the model returned nothing usable for them) but every
`SYNTHESIS_RETRY.json` save lands still exits 0. Each such source is printed to the console, so
nothing is silent, and this may be intentional (matching how `phase_synthesis` treats a per-source
model failure as routine and pickable-up next run) — flagged again only because it is unresolved,
not because it is new. QUESTION, not a finding (possible deliberate design); see below.

## Questions (possible deliberate design)

1. **`retry_synthesis.py:375`** (restated from carried-forward finding 2 above). Reading A: the
   exit code should reflect the run's OWN write health only — "did what I tried to save land" —
   and per-source model failure is expected and handled by simply retrying next run, so folding it
   into the exit code would make an ordinary, self-healing outcome look like a failure. Reading B:
   an automated caller that gates on this exit code cannot currently tell "fully rescued" from
   "half the sources are still stranded, but the half that returned something saved cleanly" without
   parsing stdout, which is exactly the class of silent partial success this project's doctrine
   otherwise refuses.
2. **`workorders.py` HOST_QUARANTINED/BINDING_SUSPECT at BOTS** (restated from carried-forward
   finding 1). Reading A: BOTS is aspirational — the right long-term home once `binding_health -
   -run`/`hostcheck.py --repair` are put on a schedule, and the order sitting open is itself the
   evidence that scheduling is owed. Reading B: until that scheduling exists, RUN is the honest
   rung (as run #64 already ruled for the sibling `BINDING_HEALTH_STALE`), and leaving these two at
   BOTS lets them read as "cheap work already being handled" when nothing is handling them.

## Cleared — examined closely this session, found correct (beyond re-confirming sweep64's clearances)

- **workorders.py**: `_mutate`'s compare-and-swap (pid+thread+attempt temp names, digest-before-
  read); `file_order`/`resolve`/`reroute`'s `_refuse_cap_hit` boundary refusals against the live
  `LEGACY_CAP_BOUNDARY` table; `resolve()`'s "did it land, then did it exist" ordering;
  `_supersede_binding_suspect`'s both-directions supersession (undecided→decided and decided→
  opposite-decided); `ghost_orders()`'s time-based (not disjointness-based) ghost test, re-verified
  against its own worked "5 recurrences, 0 ghosts" measurement; `_fire`'s polarity (healthy
  resolves, unhealthy files) at every one of its ~14 call sites; `cap_boundary_scan`'s open/closed
  split (ratchet vs. append-only measurement).
- **rigor.py**: `_validate_reciprocal_matrix`'s four independent refusals (shape, finite, positive,
  reciprocal); `perron_weights`/`logrank_weights`/`theorem_1_check`'s two-sided, None-aware
  CR/curl-fraction tests; `bradley_terry`'s Ford's-condition check evaluated as two independent
  faults (not an unreachable elif) and its `prior`-vs-raw-graph distinction; `adjudication_beta`'s
  MDL counting; `mathematical_resonance`'s uncapped `load_bearing` ranking and `main()`'s
  tie-respecting display cut (extends through ties at the cut boundary, never splits one).
- **identity.py**: `_is_continuity`'s three structural tests including the `n==1` branching
  special case; `load()`'s three-way absent/unreadable/stale handling and its refusal to persist
  an empty mine over a populated cache; `epoch_of`'s `strict=True` UNPROBED-vs-unmarked
  distinction and its overlong-answer refusal; `_inv_keys`'s multi-spelling fallback order.
- **endpoint.py**: `_save()`/`register()`'s merge-not-overwrite compare-and-swap, each re-reading
  and re-applying only its own dirty keys against the winner's copy; `fetch_raw_verdict`'s
  not_found/refused/errored tally including the 200-with-HTML-body case; `detect()`'s DEAD_TTL
  re-probe asymmetry (dead expires, live does not); `source_pages`/`register`'s absent-vs-
  unreadable distinction, both ways.
- **backfill.py**: `roster()`'s uncapped category walk (top level + one level of subcategory,
  always walked, not gated on a thin top level); the `missing = sorted(..., key=lambda t: (t in
  sizes, -sizes.get(t, 0)))` ranking key, hand-traced against sizes={A:100,C:5}, B unmeasured ->
  [B, A, C]; `lead()`'s walk-forward-to-real-prose logic and its marked mid-word cut.
- **retry_synthesis.py**: `synthesise()`'s block/prompt/transport/acceptance-gate/evidence-cut
  parity with `pipeline.phase_synthesis` (five separate places this function takes code from
  `pipeline` rather than restating it, each with its own history of having drifted before);
  `stranded_sources()`'s condition-based (not cause-based) selection; `save_side`'s re-read-merge
  narrowing the lost-update window and its honest verdict propagation; `do_merge()`'s unmerged/
  denied accounting and nonzero exit on either.
- **events.py**: `_looks_like_a_sentence`'s two mechanical refusal rules (terminal punctuation,
  word count) and the deliberately-absent third (grammar-guessing refused on principle, not
  missing by accident — confirmed against the comment recording its own removal); `_fragments`'s
  joiner-based split, re-checked against both sides surviving the same shape rule; `parse()`'s
  heading and no-heading event dedup by `seen`, and the age lookup via `reversed(heads[:idx+1])`.
- **audit.py**: `_JUNK`'s per-alternative anchoring (`\b` vs `$`) matches its own comment's stated
  intent; the source-population vs. entry-population denominator split (`sources_with_synthesis`
  vs. `entries_catalogued`); `_field`'s wrap-never-slice sample printing.
- **compress_store.py**: `load()`'s content-hash verification against `_address_in(path)`, gated
  correctly on the path actually looking like a content address; `store()`'s atomic temp+
  `replace_retry` write with pid/thread-qualified temp name, and the cleanup-before-raise ordering
  that does not let a failed unlink mask the original write failure.

## Coverage

`sweep_plan.record('run65', ['workorders.py', 'rigor.py', 'identity.py', 'endpoint.py',
'backfill.py', 'retry_synthesis.py', 'events.py', 'audit.py', 'compress_store.py'], batch=6)` run
via a scratch script with the miniconda python; see reply for whether it landed.
