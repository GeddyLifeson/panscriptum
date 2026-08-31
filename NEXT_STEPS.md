# Next Steps — written by run #39 for the run that follows it

*Overwritten every run. The queue in `state/workorders.json` is the authority on what is open;
this file is the reading of it — what to do first, and why.*

---

## 0. NOTHING IS HALTED, AND NOTHING WAS HALTED THIS SHIFT

`escalation.py --status` reads **clear**. No halt was raised by run #39 and none was standing
when it opened. The `DRILL_BREACH` recorded in `state/HALT.json` is run #38's, already lifted by
run #38 under the self-caused clause. **Do not re-derive the state of the library** — open the
shift the way the card says and work the queue.

**Run #38 left no HANDOFF entry.** Its guard was still `done:false` with a 14-hour-stale
heartbeat when run #39 opened, so it did not close its shift. Its work is real and is in the
closed-order paper trail; it is simply not narrated anywhere. If you need to know what #38 did,
read `state/workorders_closed.jsonl` for that window, not `HANDOFF.md`.

## 1. THE ONE THING A PERSON HAS TO DO, AND NO RUN CAN — STILL STANDING

**Order f6c52ef7657f (OWNER).** PID varies; the process is `pythonw -m semsearch.cli watch`,
**not part of this project**. Re-measured live on 2026-08-30 with `netstat -ano`:

| | |
|---|---|
| host TCP sockets in total | 900 |
| sockets touching `127.0.0.1:11434` | 804 (89%) |
| held by `semsearch.cli watch` | **396 ESTABLISHED** |
| held by `ollama.exe`, the other end of those | 398 |

It is still doing it, and it is still the cause of the symptoms the last three runs have chased.
Run #39 hit it directly: two `local_agent` dispatches died with
`WinError 10055 — the system lacked sufficient buffer space`, which is socket exhaustion and
nothing to do with this library. The five throttled-host orders on the BOTS rung
(`marvel`, `onepiece`, `mtg`, `naruto`, `dragonball`) and the stalled `roll_auto` are the same
cause; so was the transient `PREFLIGHT_PROBLEM` that filed and self-closed during the shift
(`aneurism.fandom.com` unreachable at 22:0x, answering 200 by 23:1x).

**One `Stop-Process` reopens the local rung, the crawl and the cloud pool.** Terminating another
project's daemon is an owner call, so runs #37, #38 and #39 have all declined to do it.

## 2. THE MUTATION PASS IS ALMOST CERTAINLY STILL RUNNING. CHECK BEFORE YOU RELAUNCH.

Launched 2026-08-30 with `--target all --file-orders`, **and this time with `python -u`**, so
`state/mutate_20260830.log` is readable while it runs rather than empty until it exits. Check for
a live `mutate.py` process first.

**Its baseline is fully green for the first time** — `verify_math rc=0 (1063 passed, 0 FAILED)`
*and* `drill rc=0 (279 nets, 279 held, 0 BREACHED)`. Every previous run mutated against a sandbox
with part of the battery switched off; see §3.

Order **af40a3c2e7e3** is the standing fix: make `mutate.main()` line-buffer its own stdout so no
future launcher can produce an empty log by forgetting `-u`. Four zero-byte mutate logs are on
disk from earlier runs.

## 3. WHAT CHANGED UNDER THE MUTATION TESTER, AND WHY THE NEXT RUN SHOULD RE-READ ITS RESULTS

The sandbox was not a copy of the library, and had never been one. Two omissions, both fixed:

- `state/` was copied **one level deep**, so `state/sweep_shards/` (155 files, 30 KB) never
  arrived and two sweep-coverage rows in `verify_math` were red in every baseline ever taken.
- the six logs `dashboard` reads were swept up in the blanket `.log` exclusion, so the
  fabrication guard read UNMEASURED and three more rows went red.

Baseline went **1055 passed / 5 FAILED → 1063 passed / 0 FAILED**. Then `drill` in the sandbox
went red for six *different* nets, because run #39 also stopped `drill.denied()` accepting
`"no such file"` as a gate refusal — and inside a sandbox every path under the four junctioned
trees resolves outside it. Fixed by asking `local_agent._safe()` directly. Sandbox drill:
**6 BREACHED → 0**.

**So every survivor on record from an earlier run was measured with part of the battery
disabled.** `state/MUTANTS_SURVIVED.jsonl` carries `assay.py x27, escalation.py x8,
prose_gate.py x24`. Those counts are not trustworthy and should be re-derived from the current
run, not carried forward.

## 4. THE SWEEP HAS A COVERAGE HAZARD THAT LEAVES NO TRACE — CHECK SHARDS AGAINST AUDITS

`sweep_plan.batches(n)` packs greedily by **live line counts**, so a shift editing `src/`
re-shuffles which modules a batch number owns. An agent that derives its list at spawn and calls
`record()` at the end can stamp coverage on modules it never opened. Two batches hit it in run
#39; one caught itself and rewrote its shard with a `corrected` field.

`missing()` does **not** catch this — the modules look covered. Run #39 therefore cross-checked
every shard against the audit its own agent wrote (a module counts only if the audit names it)
and got 63 for 63 corroborated, 0 suspect. **Do the same before calling a sweep complete.** The
checker is small enough to re-write; better, make it part of `sweep_plan`.

Filed as **SWEEP_BATCHES_UNSTABLE_UNDER_LIVE_EDITS** (MAJOR, SESSION). The real fix is for
`batches()` to pack against a frozen manifest for the life of a run rather than against live line
counts.

## 5. WHAT RUN #39 DID NOT GET TO

**The queue is at 458 and that is not neglect.** 170 were open at shift start, 25 were closed with
written resolutions, run #39 filed 6, and **the sixteen sweep agents filed 293 in the last hour**.
A queue that grows after a comprehensive sweep is the sweep working. The 293 are fresh, uncapped
and each carries its own remedy.

By rung: RUN 135, LOCAL 122, OWNER 97, SESSION 58, BOTS 46. `state/workorders.json` is the
authority; `workorders.py --sweep` prints it grouped.

**Work the LOCAL rung first, and this time it will actually work.** Three separate faults kept it
from doing anything at all, all fixed this shift (`82adb37c6cfc`, `7dd2672546b1`, `1d54acf05414`).
122 orders sit there and a large share are citation drift and unmarked truncations — exactly what
the free model can carry. Give it several attempts per order and check its work; do not escalate
to yourself on the first miss. **But it will keep failing with `WinError 10055` until §1 above is
dealt with**, so try one order first and read the error before queueing twenty.

**The MAJORs worth doing before anything cosmetic** are listed at the top of run #39's HANDOFF
entry with their ids — the phase-1 ceiling stranding (44 sources, 6,629 entries), the drill probe
that can lift a live halt, `standards.ollama_runner_up`'s three-valued contract, `derivation`'s
infinite walk, `gpu_lane`'s unreclaimable corrupt slot, and `read.py`'s name filter discarding
feats for 4,939 entities.

## 6. TWO THINGS THIS RUN CHANGED THAT YOU SHOULD KNOW BEFORE YOU TRUST A NUMBER

- **`workorders_closed.jsonl` is now history only.** Battery rehearsals go to
  `state/workorders_selftest.jsonl`. The 1,852 rehearsal rows already in the trail were NOT
  rewritten — append-only history is not tidied — so any percentage computed over the whole file
  still carries them. Count from the end, not the start.
- **The secret gate no longer discharges its own blocking orders when it could not scan.** If the
  export tree is absent, `SECRET_STAGED` and `SECRET_IN_EXPORT` simply stand. That is deliberate:
  "could not scan" is not "clean", and this is the one gate where next run is not a recovery.

## 7. OWNER DECISIONS STANDING (do not decide these in a run)

Unchanged from run #37's list — `b57e23204f66`, `bd673ceaaf31`, `707fefc17465`, `585fcd3774b8`,
`30854f11f322` (left open deliberately; the prescribed fix is provably infeasible and the
reasoning is in the order). Added by run #39:

- **`ca0a93856e2a`** — 56 of the 108 entries in BUGS.md's `## Open` say RESOLVED in their own
  label and were never moved. Moving them is curatorial: six carry PARTIALLY CLOSED notes and must
  NOT move, so a regex would silently close live faults. A dated marker now sits at the top of
  that section carrying the measurement.
- **`b86d79c574e3` / `44c420f80448` / `4d44a6363245` / `0c1670811107`** — the `batches()`
  instability in §4, filed four times from four independent sightings.
