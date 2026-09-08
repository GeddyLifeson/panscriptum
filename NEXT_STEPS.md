# Next Steps — the priority queue for the next maintenance run

*Overwritten each run. The permanent record is `HANDOFF.md`; the live queue is
`state/workorders.json` via `python src/workorders.py --sweep`.*

Written by run #47, 2026-09-07 (daily). **Queue at close: 251 open** (OWNER 140 · SESSION 68 ·
RUN 26 · LOCAL 15 · BOTS 2), down from 295 at open. **100 closed, and the workable rung went
from 95 to 43.** Every "already fixed" claim was re-verified against source before its order was
resolved — several survived that check, and several were corrected by it.

**The battery is GREEN on a settled tree:** `verify_math` 1213 passed / 0 FAILED, `drill` 443
nets / 443 held / 0 BREACHED, `allsweep` 0 subsystems bad, `health --preflight` all pass,
`secondopinion` all three tools RAN with 0 secrets agreed by two scanners, `liveness` 45 findings
with 0 tautology and 0 phantom, `axis_correlation` n=45 unchanged, `pyflakes` clean.
**No halt was raised or lifted; `escalation --status` read clear at open and at close.**

---

## 0. READ THE MUTATION LOG FIRST — IT WAS STILL RUNNING WHEN THIS SHIFT CLOSED

`state/mutate_20260907.log` is the pass run #46 launched. **It is NOT a completed pass.**

| target | result |
|---|---|
| `assay.py` | 143 mutants, 138 killed, **5 SURVIVED**, 0 indeterminate (25,601s) |
| `prose_gate.py` | 62 mutants, **62 killed, 0 SURVIVED**, 0 indeterminate (18,539s) |
| `escalation.py` | **NO RESULT — still running after ~23 hours on this target** |

The process was alive and its sandbox verifiably advancing at close. **This is the same target the
run #45 pass died on** (`f9643582fd29`, OWNER). Find out which happened before anything else. A pass
killed partway is not a pass with fewer survivors. **Do not start a second pass while one is live.**

Four of the five `assay.py` survivors were triaged this shift (one real coverage hole closed with
seven proved rows, two proved equivalent, one already killed by a battery that had been disabled
when it was scored). **One follow-up is owed:** run
`python src/mutate.py --rule-equivalent assay.py:675` when no pass is in flight, or the next pass
re-files an equivalence that has already been proved.

---

## 1. THE WORKABLE QUEUE — 43 IDS, ALL OF THEM, SO YOU START FROM MY POSITION

### RUN (26)

| id | sev | code | where |
|---|---|---|---|
| `07258ace3a09` | MAJOR | ADDRESS_SPINE_CODE_INVENTED_FOR_CROSSOVER_TITLE | src/address.py:151-169 (_index_name_is_placed_like_a |
| `23dbbcd656f3` | MAJOR | ASSAY_MUTATION_SURVIVORS_TRIAGED_MOST_ARE_ARTEFACTS | src/assay.py (10 survivors), src/verify_math.py (con |
| `af47010df391` | MAJOR | CASCADE_SIZE_REFUSAL_READ_AS_THROTTLE | src/cascade_bridge.py:542-550 (_TRANSIENT_WORDS / _T |
| `eb4801a30501` | MAJOR | CODEWATCH_BUDGET | dashboard |
| `2cb8756deb0a` | MAJOR | CODEWATCH_UNCOVERED_JOBS_OUTSIDE_THE_KEEPER | src/read.py, src/feats.py, src/autostart.py, src/ove |
| `75c4171c2e93` | MAJOR | DRILL_EXITS_ZERO_WHEN_ITS_OWN_VERDICT_DID_NOT_LAND | src/drill.py |
| `d1709d8e757d` | MAJOR | ENTITY_INDEX_NEVER_REBUILT_STALENESS_ANNOUNCED_BUT_UNACTED | data/ENTITY_INDEX.json; src/weave_index.py (the buil |
| `b0a931a92419` | MAJOR | HEALTH_LEDGER_WRONG_SHAPE_IS_NOT_CORRUPT_TO_ANY_READER | src/health.py:_flush_ledger, _flush_samples, _read_l |
| `2461a04d8849` | MAJOR | MUTATE_BASELINE_DOES_NOT_NAME_ITS_RED_ROWS | src/mutate.py baseline() / red_gates() / main()'s re |
| `58a00e909217` | MAJOR | MUTATION_LONG_RUN_SCORED_AN_UNKILLABLE_MUTANT_AS_KILLED | src/mutate.py (differential judging over a long run; |
| `8950aa8d3f62` | MAJOR | NO_DETECTOR_MEASURES_GATE_REACHABILITY | src/liveness.py (the detector that does not exist);  |
| `30854f11f322` | MAJOR | SWEEP35_FINDING | binding_health.py:310-355 |
| `ca4f97d6b64d` | MAJOR | UNPUSHED_DETAIL_CLIPPED | src/publish.py:706-750 (_unpushed) |
| `79d51aef8b71` | MAJOR | VERIFY_MATH_HAS_A_LIVE_GPU_DEPENDENCY | src/verify_math.py -- a live Ollama connection held  |
| `a66423722e45` | MINOR | AGENT_SCRATCH_IN_PUBLISHED_TREE | handoff/ as a COPY_DIRS root vs where agents write w |
| `a5de2dcb9447` | MINOR | DRILL_NO_CAPS_NETS_DRIVE_THE_WRONG_BRANCH | src/drill.py:1497 |
| `e114b2d0fe48` | MINOR | FIXED_ORDERS_LEFT_OPEN_AT_SHIFT_END | the resolve step at the end of a maintenance shift;  |
| `e045c3218e85` | MINOR | HEALTH_API_PROBE_CALLS_ONE_ARBITRARY_HOST_THE_FAMILY | src/health.py:check_api_paths (the fams bucket) |
| `406a61029dca` | MINOR | QUESTION_IDEMPOTENCY_NET_SWALLOWS_AN_UNREADABLE_RECORD | src/drill.py |
| `3e65d8657462` | MINOR | QUESTION_TWINS_NET_GRADES_A_PROBE_IT_COULD_NOT_STAGE | src/drill.py |
| `c9146abf92df` | MINOR | ROLL_LOST_UPDATE_REMAINING_WRITERS | src/foreman.py:189 and src/roll.py:127 (exclude) |
| `5ed00985ce04` | MINOR | STALE_CITATION_OVERNIGHT | src/overnight.py: running() docstring (~line 201), i |
| `5d14e90b5043` | MINOR | SWEEP34_FINDING | src/overnight.py:842 |
| `a724ec57e0d5` | MINOR | TI_DANGLING_VERDICT_STOPS_SHORT_OF_THE_LADDER | src/thread_integrity.py:339-345; src/allsweep.py:181 |
| `2f07cbd3241d` | MINOR | WITHDRAW_CHAPTERS_STRAY_SWEEP_NET_STILL_OWED | handoff/nets_20260906/longtail.py NET 3 (staged, not |
| `ad681057369a` | MINOR | WORLDSEED_UNREACHABLE_PRIMITIVE_TIER | src/worldseed.py size lookup |

### LOCAL (15)

Note: the LOCAL rung produced **zero** completed orders this shift — the GPU was saturated
(`OLLAMA_NUM_PARALLEL=1`, `/api/generate` returning "maximum pending requests exceeded" at 96%
utilisation) and `local_agent` yields to the library's own calls by design. Five of these are
self-closing `CODEWATCH_RESTART` records. **Check whether the card is free before dispatching here**,
and carry the work in a Claude lane if it is not.

| id | sev | code | where |
|---|---|---|---|
| `69c7f940635a` | MAJOR | READ_CLOUD_ANSWER_ACCEPTED_WITH_NO_SHAPE_CHECK | src/read.py:_ask_ungated (cascade_bridge.ask call si |
| `c22c8b1f426c` | MINOR | COSMOGRAPHY_CENSUS_RAISES_FOR_TWO_OF_THREE_SCALES | src/cosmography.py:151-160 |
| `70f5e5150f8b` | MINOR | FEATS_INDEX_EXCEPTION_TEXT_CUT_WITH_NO_MARKER | src/feats_index.py:164 (host_to_sources) |
| `4ed4041c3b78` | MINOR | LIMIT_ZERO_READ_AS_NO_LIMIT_THREE_MORE | src/generate.py:589, src/catalogue_web.py:545, src/f |
| `3e576b1a29ad` | MINOR | PROFILE_ENCODE_CRASHES_ON_DECIMAL_BAND | profile.py:encode, profile.py:BANDS, worldseed.py:to |
| `ed58a1a87da0` | MINOR | ROLL_ORDER_CITATION_DRIFTED_C9146 | src/roll.py:267 (exclude), miscited as :127 in order |
| `e866d1520c16` | MINOR | STALE_CITATION_TIERS | src/tiers.py: deliberate_joins() docstring (~line 32 |
| `fe99e57e1993` | MINOR | UNMARKED_NAME_CUTS_SWEEP44 | src/backfill.py:364; src/catalogue_web.py:557,344; s |
| `1ba189fabcaa` | MINOR | WORKORDERS_REROUTE_NOOP_REPORTS_AS_SUCCESS | src/workorders.py:reroute, workorders.py:main (the - |
| `d88f8c7f5734` | INFO | CHARTER_CODES_CORRUPT |  |
| `018727423a09` | INFO | CODEWATCH_RESTART | dashboard |
| `91bb70c85e31` | INFO | CODEWATCH_RESTART | publish |
| `764e283cdf00` | INFO | CODEWATCH_RESTART | overnight |
| `ee382241ff8c` | INFO | CODEWATCH_RESTART | overwatch |
| `e45618de083f` | INFO | CODEWATCH_RESTART | foreman |

### BOTS (2)

| id | sev | code | where |
|---|---|---|---|
| `2da53c3e192f` | MINOR | HOST_QUARANTINED | www.dandwiki.com |
| `3dc2832846bc` | MINOR | STALLED_UNRESTARTABLE |  |

---

## 2. THE FIVE I WOULD DO FIRST, AND WHY

1. **`d1709d8e757d` — `data/ENTITY_INDEX.json` is 9 days stale at 177 MB and NOTHING rebuilds it.**
   210 of 216 record files have been modified under it. `verify_math` announces this twice a run and
   no process acts on it; continuity groups, resolved entities and the resonance graph are all
   computed from it. I did not rebuild it — the cost is unmeasured and the GPU was contended.
   Measure the rebuild on a quiet machine, then put the scheduling question to the owner.
2. **`8950aa8d3f62` — nothing measures which lines a gate can actually reach.** This is the general
   fact underneath the mutation survivors. Run the battery under coverage, report unreached lines in
   the safety modules as a **roster, never a percentage** (Hard Rule 0), and expect a legitimate
   declared residue.
3. **`79d51aef8b71` and `f40f701594a4` — the two baseline-drift mechanisms.** One is fixed and now
   guarded; the other (the junctioned `data/` in the mutation sandbox) is not. **Do not close either
   on one quiet run** — the 09-07 `prose_gate.py` target logged zero drift over 18,539s while
   `assay.py` logged two events in 25,601s.
4. **`406a61029dca` and `3e65d8657462` — two drill QUESTIONS, each with a reading already written.**
   Both were deliberately NOT landed because **both change when the library HALTS.** They want a
   ruling. "A safety that stops work is not a fault that stops work."
5. **`2f07cbd3241d` — the withdraw_chapters net is still owed**, still staged and unlanded at
   `handoff/nets_20260906/longtail.py`. Whoever takes it must watch it go RED against a broken
   `withdraw_chapters` before landing it. **Do not move that file out of the tree first.**

---

## 3. FOR THE OWNER — DECISIONS ONLY A PERSON CAN MAKE

- **`f19f4a2b00f4` (re-routed RUN → OWNER this shift, after four shifts each re-derived it).** The
  technical blocker is gone: `PIPELINE_STATE.json` held still across a 22.4-minute window. 28
  `done.entrypass` keys record real work over 531 entries later purged for being mined off the wrong
  wiki. **Delete them, move them to a `done.entrypass_purged` block, or leave them?** Nothing was
  written. A second question rides along: both purged records still say status `catalogued` while
  `SWEEP_ROLL.json` says `uncatalogued`.
- **The GPU is over-subscribed by two standing instructions that are individually right.** "All three
  mutation targets every shift" and "route everything possible to the free local model" cannot both
  hold on one single-slot card that a multi-hour pass occupies. Recorded on `79d51aef8b71`.
- **`f646c1c5f1d0` (re-routed LOCAL → OWNER).** Its mechanical half is fixed; what remains is whether
  `genres_scored` — a field that is invariant by construction — should be dropped, renamed, or kept
  as a deliberate denominator.

---

## 4. HOUSEKEEPING THAT IS NOT A FAULT

- The **binding-health canary was refreshed** (11.0 days → current): 134 hosts checked, 1 failed and
  quarantined (`www.dandwiki.com`). `health --preflight` independently reports the matching empty
  cache and correctly attributes it to binding_health.
- **`foreman` exiting rc=17 is deliberate** — it is picking up changed source, and the keeper restarts
  it. `codewatch` showed restarts within budget all shift. Do not read it as a crash.
- The **corpus entry count did not move** (282,822 at both rebuilds) and that is expected: entries come
  from catalogue passes, evidence and feats come from reading, and reading rose all shift. The
  remaining uncatalogued sources are blocked on hostless-source questions at the OWNER rung.
- **`silence`'s SILENT count moved 232 → 247** on purpose: the audit now sees `contextlib.suppress`
  blocks, which are the same act as `except: pass` spelled differently and were invisible to it. The
  count rose because the undercount ended, not because anything regressed.
