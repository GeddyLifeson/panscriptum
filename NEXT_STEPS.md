# NEXT STEPS — written by run #65 (2026-09-26 daily, evening)

*Overwritten every run. The queue in `state/workorders.json` is the authority; this file is the
reading order, and the short list of things a fresh run would otherwise spend its first hour
rediscovering.*

---

## 1. READ THE MUTATION PASS

`state/mutate_20260926b.log`, pid 28516, launched 22:30 on fingerprint `7375ddee8cdb1abf`,
baseline verify_math **1318/0** and drill **641/641/0**. It runs about 18 hours. **Put the
survivor count in the handoff**, and read every `BASELINE DRIFTED` block before trusting a kill.

* Drill BREACHED rows in a drift now carry the drill's reason line (M126). If the ledger nets
  drift again ("no probe anywhere in this drill writes into the live failure ledger" / "...by a
  route the in-process spy cannot see"), the reason names the probe site and the class. That is
  the class run #65 could not reproduce. Grant it by name only if it is machine state, the same
  way `silent:tuning.py:ollama_up` was granted in verify_math.
* "WAS RED AT THE BASELINE" for a later target now says when the red was carried in from an
  earlier target's drift. If it says so, that target's kills were judged without that gate.
* Known equivalents on record (`mutate.py --list-ruled`): assay 826 and 909; escalation 495, 567,
  695, 1006, 1183, 1239 and 1274.
* `src/` moved after launch (verify_math, publish, pipeline, drill, wh40k), none of them a target.
  The log will say "src/ MOVED"; the verdicts are about the launch tree.

## 2. THE PUBLISH DAEMON (order `573ab7b04b6f`, OWNER)

The cause is found: gh.exe and gh's `hosts.yml` exist only in the Claude app's virtualised AppData
(`AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache`), which the Startup-folder keeper cannot
see. The fix is the owner's (install gh from an ordinary terminal and log in, or let Git
Credential Manager take over). Until then **the daily run's push is the only one that lands.**
Every PUSH HELD line now ends with a `package store:` fact. Close the order after the first
daemon cycle with no PUSH HELD.

To see what a Startup-folder process sees, launch a probe through WMI
(`Invoke-CimMethod Win32_Process Create`, pythonw); a Bash or PowerShell child of the app sees
the virtualised view.

## 3. THE QUEUE

* BOTS `058fa19d4e65`: close once `data/CHAIN.json` carries `unmatched` (pipeline phase 4).
* BOTS fandom throttle quarantines (marvel, forgottenrealms) close when they lapse.
* OWNER: 53 orders. New tonight: `cb31bf2707ad` (Digimon "What's needed:" banners in 202
  descriptions, reaching prose), `beb7db270826` (sweep65 questions). `670c907af5e3` (BLOCKING,
  "prose stopped") looks stale: prose is running and writing complete chapters. Ask, do not close.
* The canary (`binding_health --run`) is the daily run's job. It last ran 2026-09-26 00:2x;
  BINDING_HEALTH_STALE files at RUN after 7 days.

## 4. THINGS A FRESH RUN WOULD OTHERWISE REDISCOVER

* **Never run two verify_math processes at once.** They share the cascade scratch DB and the
  restart ledger and redden each other (4 FAILED together, 0 alone, run #65).
* **Never pass prose through a shell heredoc.** Run #65's handoff draft broke bash on an
  apostrophe; write with the Write tool and insert with a small script.
* The crawl's log goes quiet for tens of minutes by design; check its network I/O first.
* overwatch rounds take hours on the shared GPU.
* Prose runs about one chapter every 8 minutes. Read a produced chapter, not the progress bar.
* The battery pins `qwen3:8b`; with the library running that is its normal state.

## 5. THE BATTERY AT CLOSE OF RUN #65

* `drill.py` **641 attacked, 641 held, 0 BREACHED**
* `verify_math` **1318 passed, 0 FAILED** · pyflakes clean
* `liveness` 46 · `silence` 316 · `secondopinion` all three RAN, 0 secrets ·
  `axis_correlation` 45 entities
* `health --preflight` 1 problem (dandwiki) · `allsweep` 2 bad (dandwiki preflight, cascade live
  call rate-limited)
* `corpus_db --rebuild` (start of shift) 216 sources, 282,822 entries
