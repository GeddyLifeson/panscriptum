# Next Steps — the priority queue for the next maintenance run

*Overwritten each run. The permanent record is `HANDOFF.md`; the live queue is
`state/workorders.json` via `python src/workorders.py --sweep`.*

Written by run #59 (daily), 2026-09-14. **This run raised one halt and lifted it** (self-caused: tonight's chain.py recipe-digest change left a drill fixture stale; the fixture was fixed and proven RED/HOLD, then drill 596/596/0 and verify_math 1307/0 before the lift). The library is running.

    drill              608 nets / 608 held / 0 BREACHED   (was 590; +18 nets, each proven HELD and RED)
    verify_math        1307 passed / 0 FAILED
    allsweep           3 bad at the final run:
                         preflight      dandwiki, owner order 8b3f2911fa0c
                         cascade live call  provider quota plus a stale Groq model id (`qwen/qwen3.6-27b` returns HTTP 404) in Cascade's own config outside this kit; the row flaps (OK at 22:48)
                         BUGS.md estate  3 eaten escapes, self-inflicted and repaired before the push; re-check that allsweep's estate tier reads 0 unreadable
    pyflakes           clean over src/
    secondopinion      all three tools RAN, 0 secrets by two independent scanners
    liveness           47 findings, 0 tautology, 0 phantom
    silence            303 SILENT (was 300; all three new sites read and deliberate)
    axis_correlation   45 entities -- unchanged, no --write owed
    sweep run59        16 batches, all 119 modules, `missing()` = []
    escalation         clear
    queue at close     50 open -- OWNER 44 / RUN 4 / LOCAL 1 / BOTS 1   (was 58 at open)

---

## READ FIRST: FIVE THINGS TO CHECK BEFORE ANYTHING ELSE

**1. Did the publish daemon's push start working?** Every daemon push failed from the 18:00 reboot on 2026-09-14 until run #59 released the guard ("gh.exe: No such file or directory" from git's credential sh, gh.exe present). Run #59 could not reproduce it and landed two things in `publish.git()`: `stdin=subprocess.DEVNULL` (the one spawn difference sweep59-batch11 found) and `_credential_probe` (display only). Read `state/publish.log`. If pushes land, record that stdin was the likely cause. If it still fails, the probe's bracketed line says whether Python itself could exec gh.exe (it then points at the OS/AV) or only git's sh could not.

**2. The mutation pass launched by run #59.** It was launched at 22:53:43 on 2026-09-14, detached as pid 28764, targets all (assay.py, prose_gate.py, escalation.py), log `state/mutate_20260914.log`, sandbox `panscriptum_mutate_1d96qw29`. The baseline was GREEN (import rc=0; verify_math 1307/0 in 155s; drill 596/596/0 in 128s), with one caveat in its own log: src/ was written 4s before the sandbox copy. Expect about 30h. It judges from its launch-time copy of src/, so the drill grew from 596 to 604+ nets on the live tree afterwards without moving its verdicts. It carries tonight's fixes in its snapshot. Check that it is still alive (`state/MUTATION_ACTIVE.json`, pid). The deletion watcher writes the scratchpad log named in the handoff; stop it by creating `state/STOP_SANDBOX_WATCH`. If the pass died on a FileNotFoundError, the watcher log names what deleted the sandbox: that closes `9ea4d3545524`. When escalation.py finishes, read its verdict for the old escalation.py:409 mutant (now near `held = False` ~:416) for `58a00e909217`. This is the first pass over escalation.py with a green drill baseline. **Do not edit assay.py, prose_gate.py or escalation.py while it runs.**

**3. `data/CHAIN.json` and order `058fa19d4e65`.** The code fix and its net landed, and the live harvest index was rebuilt under the new recipe digest. The full `chain.py` run that should rewrite CHAIN.json (pid 18496, orphaned from the agent that started it, no log after 22:26) was still in its model pass at close. If CHAIN.json's mtime is still 2026-08-22, re-run `python -u src/chain.py` with a log. The harvest is now cached, so it goes straight to extraction. When CHAIN.json carries `fit_error` / `unmatched` / `unanswered`, close the order.

**4. Daemons on stale code.** At close, overnight and pipeline had not polled codewatch since the 18:00 reboot, and tonight changed many modules. Run `python src/codewatch.py`; restart any that has not bounced at a safe point, and say so.

**4b. BOTS order `0a7cc18747e5` (BINDING_HEALTH_STALE) is really a HAND job.** The canary `data/BINDING_HEALTH.json` was written 2026-09-07 23:00 and crossed its 7-day ceiling on 2026-09-14. The comment above `BINDING_HEALTH_MAX_AGE` in workorders.py says so: nothing schedules `binding_health --run`, which is a ~200-page job against hosts that rate-limited this machine once, so an operator runs it by hand. Run #59 deliberately did not start a crawl against fandom hosts from a maintenance shift. Run it at a quiet hour, watching for the ban shape (fandom HTTP 000 or timeouts while Wikipedia answers). The detector then closes the order.

**5. Do not spend a shift re-deriving the owner decisions.** Run #59 added one: `3099138a82bd` (chain.py, weave.py, axis_correlation.py, roll.py join the halt-interlock ruling of `1e6f99e54b25` / `21c075e5e2d6`). The rest are unchanged from run #58's list.

---

## THE RUN WORK LEFT, IN ORDER

**1. `98898e10038e` (MAJOR): read.py `_names()` short-name prefix collisions.** The remedy needs the full-corpus old-vs-new diff before it ships (run-#3 lesson). Land it at a quiet point; read.py is a daemon module.

**2. `5b99ff000325` (MAJOR): a refused RAW-mode hostcheck probe reads as rate 0.0.** `endpoint.fetch_raw` swallows per-title transport failures, so a blocked dandwiki host and an empty one look the same. It needs a verdict form of `fetch_raw` (grep its callers first) and a hostcheck RAW branch that records `rate: None` on total refusal. Harness-evidenced, not observed live.

**2b. Run #59's second and third waves are CLOSED, each netted and proven, with the central drill green after each wave (604/604/0, then 608/608/0):**
* `13ab15a6c8da` chain.py single-instance guard
* `dfac5986e779` silence.py observed test
* `c4d13e8829b5` completeness zero categories
* `98898e10038e` read.py short names
* `2f314697d52b` drill live-audit
* `7bd2ee5f8b3b` foreman WMIC -> psutil
* `5b99ff000325` RAW refusal
* `58cbf2367aeb` sweep59 bundle

If any of these misbehaves, its closed record in `state/workorders_closed.jsonl` carries the fix, the nets and the prove logs.

**3. `58cbf2367aeb`: eight sweep59 questions and latent minors.** Answered by run #59:
* item 2, cascade_bridge unstated-throttle bench: a gap, fixed
* item 3, hostcheck RAW branch: answered, and it led to 5b99ff000325, fixed
* item 4, policy `is_type` bool: fixed
* item 6, profile.encode: unreachable, comment only
* item 7, events.py display: separator " | "
* item 8, threads.py T4 count: fixed and netted

The bundle is closed. **Items 1 and 5 went to the owner as order SWEEP59_OWNER_QUESTIONS_ITEMS_1_AND_5:**
* item 1: prose_gate `instrument_shortfall()` accepts a bare Instrument marker on a non-being entry
* item 5: standards.py reads a never-run managed job as unmeasurable (reproduced in isolation; both readings recorded)

**4. Still open from before:** `9ea4d3545524` (the watcher is running; see READ FIRST 2) and `58a00e909217` (tonight's pass answers it).

**4b. `89503c58409f`, line citations in comments.** Run #59 worked the whole roster:
* 1 FIXED (tiers.py)
* 29 ALREADY FIXED by earlier runs, each verified by grep
* 20 SKIPPED, because other agents or the mutation pass held those files that night: assay.py 4, completeness.py 1, drill.py 2, foreman.py 9, mutate.py 2, prose_gate.py 5, read.py 3, standards.py 3, verify_math.py 3

The per-site status is in `handoff/sweep59/citation_roster_status_89503c58409f.txt`. Convert the skipped sites BY SYMBOL once those files are free. Rules for that work:
* Leave assay.py and prose_gate.py until the mutation pass ends.
* Leave mutate.py's historical coordinates alone; they are the `--rule-equivalent` key format.
* Leave verify_math's citecheck fixtures alone.

**4c. `d7efd67caa6f`, detector citations.** citecheck's last live site is a verify_math fixture, which citecheck deliberately does not exempt. It stays open until someone rules on an exemption. (The withdraw_chapters.py -> publish.py blank-line citation that citecheck found tonight was fixed by symbol.)

---

## LESSONS FROM RUN #59 (keep them)

* **Measure an order's premise before routing it.** `1d45a56ae1d8`'s sites were already fixed; two local-model attempts were spent before a grep showed it.
* **A new invariant makes old fixtures lie.** The recipe digest was correct and proven, and it still breached an older net whose fixture predated the key. When a change adds a "missing reads as invalid" rule, grep drill.py for fixtures of that file before the central drill runs, not after.
* **A sweep finding can be real and still overstated.** Batch11's completeness denominator claim did not survive `best = max(...)`; batch05's CRITICAL was a known owner-class question. Verify the harm, not only the line.
* **An agent that starts a long job must name the pid it owns.** The chain agent's full run ran twice in parallel, and its own report called the surviving run killed.
* **Never set a shell variable inside a backgrounded `&&` chain.** It bit again this run (logs went to `/`). Assign on its own line first.
