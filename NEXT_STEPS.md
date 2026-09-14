# Next Steps — the priority queue for the next maintenance run

*Overwritten each run. The permanent record is `HANDOFF.md`; the live queue is
`state/workorders.json` via `python src/workorders.py --sweep`.*

Written by run #57 (owner-triggered), 2026-09-13. **The halt is lifted, on the owner's ruling. The library is running and the battery is green.**

    drill              523 nets / 523 held / 0 BREACHED   (was 511; +12 new nets this shift)
    verify_math        1294 passed / 0 FAILED            (was 1289; +5 rows this shift)
    allsweep           2 subsystem(s) bad -- FAILED cascade live call 77.3s rc=1 (broken); FAILED preflight 35.3s rc=1 (broken)
    pyflakes           clean over src/
    secondopinion      all three tools RAN, 0 secrets by two independent scanners
    liveness           48 findings, 0 tautology, 0 phantom
    axis_correlation   45 entities -- unchanged, no --write owed
    sweep run57        16 batches, all 119 modules, `missing()` = []
    escalation         clear (lifted 2026-09-13 on the owner's written ruling)
    queue at close     95 open -- RUN 56 / OWNER 26 / LOCAL 11 / SESSION 2

---

## READ FIRST: FOUR THINGS TO CHECK BEFORE ANYTHING ELSE

**1. The local model.** It was down all day and was started by hand by run #57 at 21:55 (tray pid 44656). `foreman.restart_ollama()` can only kill-and-wait for a tray, so if the tray is absent again nothing in the library will start it -- order `b750409c76be`. Check `curl http://127.0.0.1:11434/api/tags` first thing.

**2. Watch the publish daemon's first push.** From 2026-09-10 01:12 to 2026-09-13, every push by the
daemon failed with `could not read Username for 'https://github.com'`, and the export fell 124 commits
behind. Run #57 pushed by hand, so the repo is current. But the daemon's failure did not reproduce,
and its cause is still unknown.

**PUSHED -- the outage is over.** `publish.py --push`, run by run #57 at 22:02 with credential prompts disabled, synced 72 files and printed `pushed`. `origin/main` moved from `b7b4387` (2026-09-10 01:12) to `6065172` ("sync 2026-09-13 22:02 — code: allsweep, autostart, citecheck, drill, foreman, hosts +14; 53 data/site file(s)"), and the export is now 0 commits ahead of `origin/main`. So the 124 stranded commits and all of this shift's code are public. This entry and the other ledgers went up in a second push immediately after.

**WHY THE DAEMON'S OWN PUSHES FAILED IS STILL NOT KNOWN, and this is not recorded as a fix.** `publish.git()` already strips `GITHUB_TOKEN` and `GH_TOKEN` (the token is a persistent User variable, length 93, so every daemon inherits it, but git never sees it). Run #57 reproduced the daemon's process context: detached, windowless, launched from pythonw, running `git push --dry-run`. It tried both today's environment and one adding `GCM_INTERACTIVE=never` and `GIT_TERMINAL_PROMPT=0`. **Both succeeded**, so the failure did not reproduce. That leaves two readings. Either the cached Git Credential Manager credential was refreshed at some point after the failures began, or the logon-launched daemon's environment differs in a way that could not be recreated. **Watch `state/publish.log` on the daemon's first push after this shift releases the guard.** If it logs `could not read Username` again, the cause is in the daemon's context, and the variables above are the first thing to try.

**3. A mutation pass is running.** It was launched detached at ~21:15 (pid 39980,
`state/mutate_20260913.log`). **Read the log before trusting any survivor.** Its sandbox predates run
#57's edits, so it judges mutants with the pre-run-57 drill and verify_math, which lack this shift's
twelve new nets. A survivor may already be caught by the current battery; check each against it
before filing. Survivors are auto-filed as MUTANT_SURVIVED orders.

**4. Three decisions belong to the owner. Do not spend a shift deriving them again:**

* `8b3f2911fa0c` — dandwiki's API returns 403 by site policy. The preflight row stays red until
  someone rules on it.
* `a5faab7f3ede` — how `ledger_guard`'s loss floor should advance. By line count, as now, a lossy
  push can hide inside new growth; by strict retention, the floor freezes on any typo fix. A "union"
  middle rule is proposed on the order.
* `1e6f99e54b25` — whether `generate.py`, `retry_synthesis.py --merge`, `repass_bands.py --apply`
  and `resync_roll.py` should refuse to run while the library is halted. Precedent here says yes.

---

## THE THREE THINGS WORTH A SHIFT, IN ORDER

**1. One widened drill sandbox, closing four orders at once.** `4be1a84f19c6`, `5d686329771b`,
`1c7c2c2c8b00` and `247586e57b61` are the same fault: drill probes that touch LIVE state and whose
only protection is the guard under test. One of them has already quarantined fixture hosts in the
live `HOST_QUARANTINE.json`. Route every such probe through one sandbox (temp queue, temp host map,
temp records root, temp poll dir). Then add a LEDGER WITNESS-style net asserting no probe opens a
live path. Run #56 and run #57 both declined this as the second structural edit of a shift that
had already changed `drill.py`; the next shift should make it the FIRST.

**2. verify_math's own holes.**

* `491bd68b18e9` comes first. Section 20u `exec()`s every `handoff/run35/checks_L*.py` it finds,
  and `handoff/` is where agents write. Restrict it to the six pinned files, by name and digest.
* Then `3c72359c53aa`. The two §20j rows are tautological, and fixing them properly means lifting
  §20e's inline scan into a function a fixture control can drive.
* Then `19eb3626d39c`, two blanket ledger suppressions.

**3. Supervision faults with the watchdog's shape.**

* `633832bdae90`: the supervisor counts deliberate rc=17 restarts toward its idle limit, so a burst
  of source edits on short cycles can halt it.
* `972932ab89b0`: `chain.harvest()` overwrites a compare-and-swapped continuity patch.

Both are small once read.

---

## HOUSEKEEPING

* **Claim with `runguard.claim()` and keep beating on a timer.** The pid-based stale-but-alive arm
  protects only a long-lived holder; a session-driven run is protected by its heartbeat and nothing
  else. Run #57 ran `runguard.beat()` every four minutes from a background loop.
* **Watch the order queue's `KNOWN` discipline.** Sweep57's batches checked the open queue before
  reporting and labelled matches KNOWN, which kept this shift's filings to real news. Keep that
  instruction in every sweep prompt.
* **Citecheck cannot find most stale citations**, and that is by design: it proves only past-EOF,
  blank-line and bare-bracket. Do not expect a detector to shrink `89503c58409f`. Citing by symbol
  (order `0c7592915a48`) is the durable remedy.
* **The watchdog was restarted by hand this shift** (pid 39080) to put its fix in effect.
  `autostart.py` never picks up source changes on its own; any future fix to it needs the same
  restart.
