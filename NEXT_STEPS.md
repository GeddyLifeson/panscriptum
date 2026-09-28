# NEXT STEPS — written by run #66 (2026-09-27 daily, evening)

*Overwritten every run. The queue in `state/workorders.json` is the authority; this file is the
reading order, and the short list of things a fresh run would otherwise spend its first hour
rediscovering.*

---

## 1. THE MUTATION PASS DID NOT RUN ON 09-27

mutate refused twice (`state/mutate_20260927_refused.log`, `..._20260927b_refused.log`):
verify_math cannot finish in 1200s in the sandbox while prose holds the one GPU slot, because §20k
makes unpinned 300s token-flow probes. Order `36eca6457ed9` has the measurement; the ruling is
`79d51aef8b71` (OWNER). **Launch it again anyway**
(`python src/mutate.py --target all --file-orders --detach --log state/mutate_<date>.log`, after
the battery and never beside another verify_math). If prose is idle it will run; if it refuses
again, record that and do not widen the timeout. If the owner has ruled for a hermetic battery,
pin `standards._TOKENFLOW` in 20k, batch1 and b3 the way 19ai does, first.

* If a pass does run, it will be the first since M129. The drill should no longer drift on the secondopinion probe
  or on a net that declines to measure. **If the drill drifts anyway, the reason line names the
  probe and class. That would be a new class, so read it rather than assuming M129 regressed.**
* If detect-secrets is ever reported `UNPARSEABLE OUTPUT: '...'`, the quoted text is what it
  printed. That is the evidence M129 could not get, so copy it into the handoff.
* Known equivalents on record (`mutate.py --list-ruled`): assay 826 and 909; escalation 495, 567,
  695, 1006, 1183 and 1274.

## 2. DAEMONS LEFT ON OLDER CODE

`foreman` was mid-patch at 22:37 (local model, binding_health, 1 of 7); `pipeline` started 09-25;
`overnight` was awaiting the crawl lap; `overwatch` had not polled for about 35 hours. Run
`python src/codewatch.py` first. If foreman has still not polled since run #66, look at
`state/foreman.log` before bouncing it: a kill mid-patch skips local_agent's revert.

## 3. THE QUEUE

* BOTS `058fa19d4e65`: close once `data/CHAIN.json` carries `unmatched` (pipeline phase 4).
* OWNER: 55 orders. New tonight: `36eca6457ed9` (mutation pass blocked by the GPU) and `253d116215ab` (sweep66's 11 questions; item 1, the
  closed-gate net, matters most). `670c907af5e3` (BLOCKING "prose stopped") is stale by
  measurement (34 chapters in 4 hours on 09-27), but it is the owner's to close.
* `573ab7b04b6f` (publish daemon, gh.exe in the Claude app's virtualised AppData): close it after
  the first daemon cycle with no PUSH HELD.
* The canary (`binding_health --run`) is the daily run's job. Last run: 2026-09-27 ~22:05, 134
  hosts, 0 failed.

## 4. THINGS A FRESH RUN WOULD OTHERWISE REDISCOVER

* **Never run two verify_math processes at once**, and that includes allsweep (it runs one) and a
  mutation baseline. Run #66 ran verify_math, drill and allsweep strictly one after another, then
  launched mutate.
* **A drill net that cannot measure uses `_DECLARED_ESCAPES`, never `silence.note`** (M129), and
  carries a `_ = "silence-exempt: ..."` marker so the silence audit stays at 316. The net "a net
  that cannot measure DECLARES it" will go red on the old shape.
* **A source-shape net that plants its own control must not contain the control's pattern
  contiguously in drill.py's source**, or it scans itself. Split the word.
* **Never pass prose through a shell heredoc.** Write it with the Write tool and insert it with a
  small script. HANDOFF.md is LF and BUGS.md is CRLF, so match each.
* In a Bash call, assign variables on their own lines before any backgrounded `&` group.
* The crawl's log goes quiet for tens of minutes by design; check its network I/O first.

## 5. THE BATTERY AT CLOSE OF RUN #66

* `drill.py` **645 attacked, 645 held, 0 BREACHED**
* `verify_math` **1318 passed, 0 FAILED** · pyflakes clean
* `liveness` 46 · `silence` 316 · `secondopinion` all three RAN, 0 secrets ·
  `axis_correlation` 45 entities
* `health --preflight` 1 problem (dandwiki) · `allsweep` 1 bad (dandwiki preflight)
* `corpus_db --rebuild` (start of shift) 216 sources, 282,822 entries
