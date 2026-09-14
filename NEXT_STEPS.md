# Next Steps — the priority queue for the next maintenance run

*Overwritten each run. The permanent record is `HANDOFF.md`; the live queue is
`state/workorders.json` via `python src/workorders.py --sweep`.*

Written by run #56 (daily), 2026-09-12.

---

## READ THIS FIRST: A HALT IS STANDING, AND IT IS NOT YOURS TO LIFT EITHER

`python src/escalation.py --status` will say **HALTED**, `SUBSYSTEM_STOP_UNRECORDABLE`, raised
2026-09-10 22:57:32 by `drill.py`.

**Do not spend your shift re-diagnosing it. It is fully understood and its cause is repaired.**
A machine crash (Windows event 41 / 6008, unclean reboot at 22:57:01) cost `state/STOPPED.json`
its data blocks; it came back 2 bytes long and all NUL. Every safety in the chain then refused
correctly and halted the library. Run #56 restored the file to `{}` — proven, not guessed, three
ways — and the drill went from 1 BREACHED to 0 on the exact nets involved. The full account is in
`HANDOFF.md` under run #56.

**Run #56 FOUND that fault, so it left the halt standing, and so must you.** CLAUDE.md's ruling of
2026-08-25 reserves lifting to a run that CAUSED the fault in its own session. Only a person can
lift this one.

**What the halt is currently costing, so the owner can weigh it:**

* the **entire daemon fleet is down** and has been since the crash — `dashboard`, `foreman`,
  `overnight`, `overwatch`, `pipeline`, `publish`, `read`. Nothing crawls, synthesises or
  publishes. Only `autostart.py --watch` is alive.
* **`mutate.py` refuses**, so there has been no mutation pass for two shifts and no survivor count.
* **`publish.py --push` refuses**, so run #56's source changes are NOT in the public repo. The
  export repo's last commit is `787b49f` (2026-09-10 22:19), from before the crash.

**Lifting the halt is what restarts all of that.** If the owner lifts it, the first thing worth
doing is checking that the fleet actually came back (`python src/codewatch.py` — every job should
stop saying "LONG") and then pushing run #56's work.

---

## THE BATTERY IS GREEN, AND ONE ROW WENT GREEN BECAUSE THE SWEEP FINISHED

    drill              511 nets / 511 held / 0 BREACHED   (was 502; +9 new nets this shift)
    verify_math        1289 passed / 0 FAILED             (was 1288 / 1 FAILED)
    allsweep           1 subsystem bad, down from 4       (preflight only; see below)
    pyflakes           clean over src/
    secondopinion      all three tools RAN, 0 secrets by two independent scanners
    liveness           48 findings, 0 tautology, 0 phantom
    axis_correlation   45 entities — unchanged, no --write owed
    sweep run56        16 batches, all 119 modules, `missing()` = []
    escalation         HALTED (standing; see above)
    queue at close     78 open — RUN 40 · OWNER 26 · LOCAL 9 · SESSION 2 · BOTS 1

The `verify_math` FAILED row was *"the newest FINISHED sweep proves its own completeness"*, held to
`run55` with 43 modules no batch ever read — **because the crash killed run #55 mid-sweep.**
Completing sweep56 retired it. That is the mechanism to remember: a sweep that does not finish
leaves a red battery row behind it for the next run.

---

## THE THREE THINGS WORTH DOING FIRST

**1. Fix the citation detector, not the citations.** Sweep56's single dominant finding was stale
`file.py:NNN` citations — roughly **sixty across thirty modules**. Do not work them one by one;
three orders already cover that class and it will regrow. Order **`9daa719e4819`** is the reason
they accumulate: `citecheck._PATH_LEAD` treats any citation written `src/foo.py:NNN` as pointing
at another tree and **skips it uncounted**, and this codebase writes both forms. Live-verified:
`secondopinion.py:438` cites `src/liveness.py:197` (real target 348) and citecheck never catches
it. It also scans `src/` non-recursively, so `deprecated/` is invisible to it. Fix the detector,
re-run it, and expect the reported total to jump — this project's own recorded lesson is that
contamination-detection regexes always undercount.

**2. `16bf1ff4df09` — the battery has a hole in the interlock row.** `verify_math._INTERLOCKED` is
a **hand-kept tuple of 10 modules**; an AST scan finds **three more** that consult the halt
(`ingest_doc.py`, `threads.py`, and **`local_agent.py`**, the rung that writes source unattended).
Measured: replacing either fail-closed `raise SystemExit` in those with `pass` **leaves the whole
battery green**. Derive the roster instead of typing it, the way `sweep_plan.modules()` already
does for the sweep. This is a count in doctrine wearing a tuple's clothing, and CLAUDE.md records
the correction of that exact shape elsewhere.

**3. The three drill-probe orders — `5d686329771b`, `1c7c2c2c8b00`, `247586e57b61` — are one
fault wearing three faces, and today is the evidence.** Probes reach LIVE state: one grades its own
cleanup of the live `state/codewatch_poll/` and **latches an OWNER halt** if a removal is ever
denied (Windows denies removals routinely — it is what `silence.replace_retry` exists to outwait);
one runs `withdraw_chapters --go` against the **live tree** protected only by the guard it is
testing; and `_esc_sandbox` stops `file_order` and `health.record` but **not**
`workorders.resolve_code`, so two probes rewrite the live queue every battery run. Run #56 opened
its shift on a halt raised by drill probes against damaged live state. Different cause, same
structure. Worth fixing as one piece of work — widen `_esc_sandbox` and move the probes inside it.

**Run #56 deliberately did not touch these**, because it had already edited `drill.py` once
(adding nine nets, watched red then green) and a second structural edit to the probe/sandbox
boundary in the same shift is the change most likely to void the battery it is judged by.

---

## SMALLER, AND READY TO GO

* **`066bfb187bd1` — a `--sweep` silently destroys a re-route and everything attached to it.**
  Measured within one shift: run #56 re-routed `32eaec248adf` RUN → OWNER with ~50 lines of
  measurement, and the next sweep put it back at RUN with the detector's one-line `what` and the
  diagnosis **gone**. So no detector-owned order can ever be re-routed, and the reroute mechanism
  is voided for exactly the orders most likely to need it. The dandwiki ruling request was re-filed
  as **`8b3f2911fa0c`** under a code no detector owns, so it will survive.
* **`e3b2668af9af` (LOCAL)** — `coverage.py:378` drops sources under 40 entries from the WORST
  COVERED ranking with no disclosure. One line beside an existing print; route it to the local
  model.
* **`3d000c4e482f`** — `hosts.add()` is a third site in the lost-update family (with
  `c9146abf92df` and `26667ecd6543`). All three want the same remedy —
  `silence.replace_if_unchanged` with the digest taken **before** the read. Worth doing as one
  pass over the family rather than three separate visits.
* **`b0586860a8ae` got more urgent, not less.** Run #56 added the eighth and ninth copies of the
  same three-token display-cut helper (`magnitude._reason_cell`, `repass_bands._preview`) rather
  than hoisting across files it did not own. Every copy is written in the identical shape with the
  identical marker, so the hoist is still a rename and not a re-argument — but there are nine now.

---

## TWO STANDING REDS THAT ARE NOT CODE — DO NOT SPEND A SHIFT ON THEM

* **`preflight` / `8b3f2911fa0c`** — `www.dandwiki.com` serves its front page (200) and **403s its
  API** to anonymous clients, by site policy. A control host returns 200, so this is neither this
  machine's TLS fault nor an outage. It is picked as its family's stand-in every run, so the row is
  **permanently red and no maintenance action can clear it** — and quarantine cannot fix it either,
  because quarantine here is a temporary `retry_after` backoff, not a policy block list (measured:
  `binding_health.quarantined()` returns `{}` right now while `data/HOST_QUARANTINE.json` holds six
  hosts, every one expired). **Needs an owner ruling**; four options are on the order.
* **`cascade live call`** — cloud free tiers spent (`88982cef258d`). A quota condition, not a
  regression.

---

## HOUSEKEEPING FOR WHOEVER OPENS NEXT

* **Use `runguard.claim()` / `beat()` / `release()`.** Do not hand-write
  `state/MAINTENANCE_RUN.json`. Run #56 did exactly that at the top of its shift — the same
  "every run re-improvises the read-modify-write inline" habit `runguard` was written to end,
  skipping its compare-and-swap — and it had just finished reading that module's docstring.
* The guard now records **`pid` and `pid_started`**, and a stale heartbeat on a **provably alive**
  holder reads as LIVE. So a long quiet shift no longer looks like a corpse to its successor. It
  still cannot protect a run whose interpreter has exited between beats, which is the ordinary
  case here — see `guard_fault`'s docstring for why that arm was measured and removed.
* **`run #55` left no `HANDOFF.md` entry at all** — the crash killed it mid-shift. The gap between
  run #54 and run #56 is not a skipped run.
