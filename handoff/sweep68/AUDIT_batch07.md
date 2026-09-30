# sweep68 (run68) AUDIT batch 07

## Scope

Eight modules, every line read with the Read tool in sequential chunks. Nothing under src/, data/,
state/, output/, prompts/, config.yaml was edited; no subagents; no `main()`, drill, verify_math,
pipeline, generate, publish or mutate was run. Reproductions live in `%TEMP%/aud68_07`
(`wo1.py`, `rg1.py`, `ev1.py`, `ev2.py`, `on1.py`, `ax1.py`, `ax2.py`); the workorders probe repointed
`HERE`/`OPEN_FILE`/`CLOSED_LOG`/`SELFTEST_LOG` at a temp tree and stubbed the modules `sweep_detectors`
imports; the runguard probe passed an explicit temp `path`; events/onomast/axis_correlation probes only
read the live corpus (onomast redirected `OUT` to temp); `silence.note` was no-op'd in every probe.

| module | lines (read) | sweep67 lines |
|---|---|---|
| workorders.py | 2583 | 2581 |
| ledger_guard.py | 1158 | 1157 |
| onomast.py | 854 | 844 |
| runguard.py | 660 | 660 |
| axis_correlation.py | 538 | 538 |
| hosts.py | 424 | 424 |
| events.py | 354 | 350 |
| deprecated/catalogue_local.py | 333 | 333 |

## Prior-audit cross-check (handoff/sweep67 b06, b08, b09, b14, b03)

- b06 finding 8, workorders.py "127 drill nets": GONE (docstring no longer carries the count). b06 finding 9
  (LOCAL door `except` records nothing): FIXED (`silence.note("workorders.py:file-order-door")`, :566).
- b06 finding 2 (HOST_QUARANTINED / BINDING_SUSPECT filed at BOTS, no bot closes them): STILL STANDS,
  workorders.py:1560 and :1712. (BINDING_HEALTH_STALE was moved BOTS -> RUN at :1621 for the same reason;
  the two host codes were not.) Owner-routing question, not re-filed.
- b06 Q1 (`_refuse_cap_hit` raising `BadOrder` for a `what` of exactly 600 chars, and
  escalation.py:367-371 wraps `file_order` in `except Exception: silence.note`): STILL STANDS in code as read;
  not re-run this pass.
- b08 F9 (ledger_guard.py:722 message named the unflattened path; :805-809 docstring said `seal()` appends
  with plain `open`): FIXED, both now correct. b08 Q1 (floor is add-only, no CLI to rebuild it) and Q2
  (deleting `state/ledger_snapshot/` silently re-baselines both checks): STILL STAND, code unchanged.
- b08 Q3 (runguard `beat`/`release` check only the agent name) and Q4 (torn-guard CLI text, future
  heartbeat): STILL STAND; Q4 is now reproduced (F3).
- b08 F6 (events.py bold span >80 chars dropped silently): "FIXED" by widening the regex, but the fix
  introduced F4 below.
- b08 note that hosts.py has a caller (feats.py:2514) and three files still say it has none: onomast.py:454
  still says so (F6).
- b09 F2 (onomast `naming` excluded from `taken`, new world can take an existing world's name): FIXED
  (order c9c29a2305f1; `reserved` set at :620-639). Traced against the docstring cases; holds.
- b14 Q3 (axis_correlation double counting across SOURCES): now MEASURED, see F5.
- b03 (catalogue_local): refuses at import except `--help`; unchanged and still correct.

## Findings

### F1 (MEDIUM) workorders.py:1827-1830 closes DRILL_BREACH on a drill record that is empty, undated, or 40 days old
`if last is not None and not (last.get("breached") or []): resolve_code("DRILL_BREACH", "drill re-runs clean: ...")`.
Only the `breached` key is consulted. Nothing tests `at`, `nets`, `held` or `src`, although drill.py now
stamps `at`/`src` "so a result can be tied to the code it tested" (drill.py:30108-30118) and
`PREFLIGHT_STALE`/`BATTERY_STALE` exist precisely so a stale artifact is not read as green. Repro
(`wo1.py`, temp queue, `DRILL_BREACH` filed at `where=""`, the id `escalate` files it under): with
`drill_last.json` = `{}`, `{"nets":0,"held":0,"breached":[]}`, and `{"at": now-40d, "nets":475,"breached":[]}`
the sweep closes the OWNER/BLOCKING order each time ("drill re-runs clean: None/None nets held"); an absent
file and `breached:["x"]` correctly leave it open. Concrete path: a breach whose verdict write did not land
(drill.py:30153-30160 says the previous run stays standing "as current") leaves an older clean file, and the
next `workorders --sweep` deletes the freshly filed order and records "clean" in the paper trail. The HALT
file itself is unaffected (this closes the order, not the halt). Fix: require a numeric `at` inside a
ceiling, `nets > 0` and `held == nets`, else file/keep a DRILL_STALE-style order instead of closing.

### F2 (LOW) workorders.py:917 and :212 one malformed field takes down a whole read
`open_orders()` sorts on `SEVERITY.index(r.get("severity"))`; `file_order` validates severity but a
hand-edited/other-writer row ("major") makes `open_orders()`, and therefore `for_ladder()`, `twins()`,
`--handler` and the default listing, raise `ValueError: 'major' is not in list` (repro). Likewise
`battery_faults` does `float(preflight.get("at") or 0)` (:212, and `float(at)` :265), so a string
timestamp raises (repro) rather than filing PREFLIGHT_STALE; inside `sweep_detectors` that becomes a loud
DETECTOR_FAILED for the whole battery section instead of the specific STALE order. Loud, not silent, hence
LOW. Fix: `.get(..., "INFO")` guarded by `in SEVERITY`, and treat an unparseable `at` as "no timestamp".

### F3 (LOW) runguard.py:298 a future or Infinity heartbeat reads as live for ever; :641 CLI reports a torn guard as free
`holder_is_live` tests only `(now - hb) < STALE_AFTER_S`. Repro (`rg1.py`, temp guard): heartbeat `Infinity`
-> live, `claim()` refuses "heartbeat -inf min old"; heartbeat now+10 years -> live, refused ("-5256000.0
min old"). `NaN` and a very old value are correctly not live. A clock that jumped forward once and then
back leaves a real heartbeat in the future, and every later claim stands down until the clock catches up;
this is the wedge the module says it fears more than overlap, and the age is printed negative rather than
flagged. Separately `main()` on an unreadable guard prints "no readable record - a run may proceed" and
returns 0 (repro), although `read_verdict` computed the fault; only `claim()` escalates it. Fix: treat
`hb > now + STALE_AFTER_S` as a `read_verdict` fault (not live), and have the CLI print the fault.

### F4 (LOW, latent) events.py:69 widening BOLD to `[^*]{2,}` lets one stray `**` invert the pairing and drop real names unrecorded
The sweep67 fix removed the 80-character ceiling so long spans reach `_looks_like_a_sentence`. But
`_looks_like_a_sentence` has no length rule (only terminal punctuation and >8 words), so the comment at :65-67
("Length is now judged by _looks_like_a_sentence") overstates it, and the bounded regex was also what let
mis-paired markers self-correct. Repro (`ev2.py`): a body with one stray `**`, ninety characters of prose,
then `**Gamma** took part, **Delta** too` gives `named: ['took part,']` and refuses only the prose span; the
old regex named `['Gamma','Delta']`. Gamma and Delta vanish with no `candidates_refused` row, and a
non-name is offered to the join. Live Chronicle: 70 `**` markers, 0 lines/bodies with an odd count, and the
old and new regexes give identical span lists for every event (measured, `ev1.py`), so no live effect
today. Fix: exclude newlines from the span (`[^*\n]`) and/or warn when a body's `**` count is odd.

### F5 (LOW) axis_correlation.py:242-247 Son Goku is counted twice; n_entities and r are off by one entity
`observations()` has no de-duplication across SOURCES. Live: Z_FIGHTERS.json and
REFERENCE_ASSAYS_PRESENCE.json both carry "Son Goku" with an identical score vector (`ax1.py`), so
`n_entities` 45 is 44 distinct entities. Effect (`ax2.py`): mean_r 0.3193 vs 0.3239 deduped; largest single
pair shift 0.041 (acumen|ruin r 0.173 n=44 vs 0.132 n=43). The docstring's "45 entities" and the
SHRINK_FLOOR base both inherit it. Small, but every published interval leans on this matrix. Fix: key rows
by (source-independent) entity name/vector and drop repeats, reporting how many were dropped.

### F6 (LOW) onomast.py:450-456 comment says hosts.py is not wired; it is
"`hosts.py` WAS NOT [wired] ... `import hosts` ... return zero hits anywhere in src/". feats.py:2514 does
`import hosts as HS` and calls `hosts_for(..., include_primary=False)` (:2518). The same stale sentence
still stands in descending_ladder.py:42-43 and scale_theories.py:26-27 (outside this batch). Order
3fb312a72435's premise is gone; the comment now lies to whoever audits wiring.

### F7 (LOW) hosts.py:393-406 `--discover` exits 0 when discovered hosts were lost or sources could not be probed
`discover()` writes "N DISCOVERED HOST(S) WERE NOT RECORDED" and "N SOURCE(S) COULD NOT BE PROBED" to
stderr and `silence.note`s, but returns only `(added, rows)`; `main()` prints "hosts added: N" and returns 0
unconditionally. A scheduled/automated run reading the exit code sees success over a walk that lost its
product to a denied write. (`rows` also lists hosts whose `add()` returned None.) Fix: return the lost and
probe_failed lists and make rc 1 when either is non-empty. Related question Q3.

## Questions

Q1. workorders.py:1560/1712 (carried from b06 finding 2): HOST_QUARANTINED and BINDING_SUSPECT stay at BOTS
though no bot closes them, and BINDING_HEALTH_STALE was moved to RUN for exactly that reason. Same treatment?

Q2. ledger_guard.py: the SHRANK acknowledgement (`_load_acknowledgements`, :880-889) validates the range as
two ints with lo <= hi but not that `hi` is within the existing chain, so an entry `[0, 999999]` for a ledger
also covers every FUTURE shrink of it. The header calls it "a closed link range". Intended (the file is
person-written), or should `hi` be capped at `len(chain)-1` when written? Also carried: Q2 of b08
(deleting `state/ledger_snapshot/` or the chain file resets baselines as "no snapshot yet"/"no chain yet").

Q3. onomast.py `main()` (writes data/ONOMASTICON.json), hosts.py `discover()`/`add()` (data/SOURCE_HOSTS.json)
and events.py `--write` (data/EVENTS.json) have no `_assert_not_halted`, while axis_correlation.py's `--write`
has one (:435-459, :479-481). Does the 2026-09-28 halt-interlock ruling reach derived data/ files? (b09/b12
raised the onomast half already.)

Q4. workorders.py:1569: HOST_QUARANTINED orders are closed for any host absent from `BH.quarantined()`. It is
strict and raises on an unreadable file (binding_health.py:381-402), which this section turns into
DETECTOR_FAILED, so it is safe as read; noting that the whole guarantee lives in the `strict=True` default of
another module.

Q5. hosts.py:275-277 `per_source=24` still trims speculative candidates (disclosed, and `candidates_split`
keeps grounded hosts out of it). Hard Rule 0 says no cap; is a bound on guessed subdomain probes an accepted
exception, or should it be time-boxed rather than count-boxed?

Q6. axis_correlation.py `--top -3`: `ranked[:-3]` prints all but three rows and the "N more not shown" line is
skipped (`limit < len(ranked)` is false for a negative limit). Trivial; reject negatives?

## Cleared (read closely, found correct)

- workorders.py: `_load` three-way and QueueUnreadable propagation; `_mutate` digest-before-read CAS with
  pid+thread+attempt temp names and the not-landed returns; `file_order` refresh semantics (re-route
  ownership of `handler`/`found_by`, cap-boundary refusal only on caller-supplied text, inherited-boundary
  report after landing); `resolve` landed-then-existed ordering and append-after-delete, selftest routing;
  `reroute` three outcomes; `where_targets`/`twins` overlap clustering and `src/` normalisation; `check_closed`
  refusing an unlistable directory; `cap_boundary_scan`; `ghost_orders`/`closed_at` (recurrence vs ghost);
  every `_fire` call site polarity in `sweep_detectors` (ok = healthy resolves, not-ok files); `_detector`
  DETECTOR_FAILED files-and-closes; secrets section gated on `scanned`; 3b `BINDING_HEALTH.json` absent vs
  torn; `--check-citations` rc; `--handler` refusal.
- ledger_guard.py: `_one_insertion` (p+s can only equal n exactly, so prefix and suffix never overlap in
  `new`); `check_since_snapshot`/`check_since_floor` ordering before `seal()`; `_floor_union` multiset union;
  `_lost_fraction` multiset; `verify_chain` unit selection across legacy/new links and SHRANK for an empty
  ledger; heading-anchored BUGS.md spans; `assert_intact` failing closed on an unreadable chain; unparseable
  chain lines reported as problems.
- onomast.py: `well_formed` seven constraints; `coin_well_formed_stamped` fallback provably unique via digest
  tails; `load_onomasticon` missing vs unreadable; `name_worlds` reservation rule (`reserved` minus own prior
  name), standing-vs-retired split, unschema'd prior notes; `land_onomasticon` digest-before-read and re-run
  on a moved file; live data: 0 of 268,128 resolved records lack `attestations`, so `v["attestations"][0]`
  in `main()` cannot raise today (43 collision groups of size >= 2).
- runguard.py: claim/beat/release CAS ordering (digest before read); `read_verdict` three faults; stale-but-
  alive arm only ever answers "live"; `guard_fault` positive-evidence-only; token never written to the record.
- axis_correlation.py: `_scores_of` bool exclusion in both shapes; `_pearson` MIN_N and constant column;
  `_shrink_verdict` fail-closed on unreadable/non-dict/non-int prior; `write()` gated on the landed verdict;
  `widening` sentinel doc; `_assert_not_halted` fails closed on the import and sits on the `--write` path only.
- hosts.py: `_load` absent vs corrupt raising; `add()` CAS loop with the three-state return; `discover()`
  outcome tallies (thin roster, probe failed, lost writes, withheld) all reported and none capped except the
  disclosed speculative bound (Q5).
- events.py: `_fragments` joiners require both halves to pass the shape rules; `shelf_positions`; code
  extraction incl. cited-without-heading events; the `stdout.reconfigure` guard; `build(write=True)` raises on
  a denied write. Live: 0 nested coded headings, so the b08 Q7 double-credit does not occur today.
- deprecated/catalogue_local.py: refuses at import for every argv except `-h/--help` (which prints and exits
  0, so `allsweep.check_import` grades it clean); everything after the `raise` is dead by design and touches
  nothing (`yaml` import, `slug`, roll writes are unreachable).
