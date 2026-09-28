# NEXT STEPS — written by the owner-directed session of 2026-09-28 (afternoon)

*Overwritten every run. The queue in `state/workorders.json` is the authority; this file is the
reading order.*

---

## 0. WHAT CHANGED TODAY, IN ONE PARAGRAPH

The owner ruled "fix everything" on 2026-09-28 at about 15:40. The queue went from 64 open orders
(55 OWNER) to 2, both BOTS long jobs. Read the 2026-09-28 entry at the top of HANDOFF.md before
anything else: it lists the git-credential change, the new scheduled task, the withdrawn chapters
and the new pause state.

## 1. CONFIRM THE THINGS ONLY A LATER CYCLE CAN SHOW

* **The publish daemon pushed.** `state/publish.log` should show `pushed` on a daemon cycle after
  this session released the guard. If it shows PUSH HELD, reopen `573ab7b04b6f` with the exact
  error. The fix was removing gh.exe from `~/.gitconfig` so Git Credential Manager serves the
  stored GitHub login.
* **Prose is writing again.** overnight restarts generate.py on its next cycle (after its drill),
  on the rebuilt manifest. Look for new catalogued chapters and for "meta rewrite" lines in
  `state/prose_auto.log`. If Arcanum (II.L.7.4) blocks are still refused for meta-language after
  the rewrite, read `output/index/failures.json` for which terms survive.
* **verify_math still reads 0 FAILED.** Five comment-only citation fixes landed after the last
  full run (one inside a verify_math fixture string).
* **The watchdog keeper task ran.** `schtasks /query /tn "Panscriptum\WatchdogKeeper"` should show
  a recent last-run time and result 0.

## 2. READ THE MUTATION PASS

`state/mutate_20260928.log`, launched about 16:45 on fingerprint `8556f50776d07846`. Baseline:
verify_math 1343/0 in 119s and drill 710/710/0 in 143s. It is the first pass since the battery
went hermetic, so it should not be refused while prose runs. Put the survivor count in the
handoff, and read every BASELINE DRIFTED block before trusting a kill.

## 3. THE QUEUE

* BOTS `f27c121c6cb7`: the Warhammer Fantasy re-catalogue was running at 16:57
  (`state/recatalogue_whfantasy_20260928.log`). Verify it with
  `handoff/owner0928/recatalogue_targets.py` (read-only) and close the order.
* BOTS `058fa19d4e65`: close once `data/CHAIN.json` carries `unmatched` (pipeline phase 4).

## 4. THINGS A FRESH RUN WOULD OTHERWISE REDISCOVER

* **There is now a pause:** `escalation.py --pause REASON [--hours N]` / `--unpause`. The watchdog
  that was live during the session (pid 29656) runs pre-pause code until its next restart. The
  maintenance task and allsweep's GPU checks do not consult `escalation.paused()` yet.
* **Records whose topic was reworded now stay on disk stamped `stale_since`**, and nothing yet
  filters them out of chapter jobs, so an entity can be written twice until a curator prunes it.
* The crawl (`feats.py --roll`) is EXEMPT from codewatch restarts. If `data/feats/starrealms_fandom_com`
  or `data/feats/prime_fandom_com` reappear before its next lap, archive them next to
  `handoff/_archive/owner0928/feats_contaminated/`.
* Never run two verify_math processes at once, and that includes a mutation baseline and allsweep.
* Never pass prose or backslashes through a shell heredoc; use the Write/Edit tools.
