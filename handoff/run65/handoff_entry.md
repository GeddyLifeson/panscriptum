## 2026-09-26 evening — DAILY MAINTENANCE RUN #65: THE PUBLISH DAEMON'S MISSING gh.exe IS THE CLAUDE APP'S VIRTUALISED AppData. THE MUTATION DRIFT FOUND AND GRANTED. SWEEP65 DONE, 3 FIXES.

**FOR THE OWNER, AT THE TOP:**

* **WHY THE PUBLISH DAEMON NEVER PUSHES (order `573ab7b04b6f`, now OWNER; it needs you).** The
  Claude desktop app is an MSIX-packaged app, and Windows virtualises AppData for everything it
  starts. gh.exe and gh's login file (`hosts.yml`) were installed from a Claude session, so they
  really live in `AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\...`. The keeper starts
  from your Startup folder, outside the app, and for it and every daemon it spawns neither file
  exists. A probe started through WMI (outside the app) saw neither file; the same probe from this
  session saw both. That is why every session push works and no daemon push has worked since
  09-14, and why runs #59 and #61 could not reproduce it. **The fix is yours**, from an ordinary
  PowerShell window (not inside Claude): `winget install GitHub.cli`, then `gh auth login`, then
  `gh auth setup-git`. Or delete the gh helper line from `C:\Users\imarl\.gitconfig` so Git
  Credential Manager takes over. Until then only the daily run's push lands. The export was 73
  commits ahead of origin tonight; this run's push carries them. The same applies to anything a
  Claude session installed under AppData (uv, pip, ms-playwright, Python Entry Points and more):
  the keeper's daemons cannot see it.
* **THE 09-26 MUTATION PASS FINISHED, AND IT IS NOT A WHOLE PASS.** Read from
  `state/mutate_20260926.log` (66,833s): assay 154 mutants, 152 killed, 2 survived (826 and 909,
  both already ruled equivalent); prose_gate 77/77 killed, 0 survived; escalation 148, 141
  killed, 7 survived (all 7 already ruled equivalent). **Survivors not already ruled: 0.** But
  part way through assay, verify_math and drill drifted red on clean code, 37 assay kills are in
  doubt, and the red baseline was carried into prose_gate and escalation, so both were judged with
  drill and verify_math switched off. Their kill counts are not evidence of coverage.
* **THE verify_math HALF OF THAT DRIFT IS FOUND AND FIXED (M126).** `standards.check()` asks
  `tuning.regime()`, which asks Ollama `/api/tags` (6s timeout) when the cloud pool is weak. Under
  the prose and pipeline load that times out, and `silent:tuning.py:ollama_up` was not in the
  battery's named machine-state exemption. Reproduced exactly (Ollama unreachable AND 0 answering
  buckets; either alone is green), and granted by name. **The drill half did not reproduce**, so
  its class is still unknown; `mutate` now records the drill's reason line with each BREACHED
  row, so the next drift names it. **A new pass was launched at 22:30** (pid 28516,
  `state/mutate_20260926b.log`) on a whole baseline: verify_math 1318/0, drill 641/641/0. It runs
  about 18 hours. **Its survivor count is for run #66 to read.**
* **Order `670c907af5e3` (BLOCKING, OWNER) looks out of date.** It says prose is stopped at the
  MANAGER rung. It is not: `escalation.subsystem_stopped('prose')` is False, generate.py has run
  since 09-25 23:36, and 207 entry chapters are on the shelf, the newest at 22:39. The fixed tail
  (Contradictions / Instrument / Threads) is on every entry of the one I read. Please close it,
  or say what it still waits on.
* **NEW OWNER ORDER `cb31bf2707ad`: the Digimon wiki's "What's needed:" maintenance box was mined
  as description text on 202 entries, and prose is writing it as fact** (Hosoda, in
  `II_K_2_Persons_1411_1420.md`). The box runs into the real text with no delimiter, and both
  fixes (strip at mining and re-catalogue, or widen prose_gate's P8 ban) are yours to choose.
  THE UNNAMED HAND is still on every entry, as 670c907af5e3 already noted.
* **NEW OWNER ORDER `beb7db270826`: two small sweep65 questions.** The one with a live cost is the
  catalogue merge's bound (see M128 below).
* **No committed secrets.** detect-secrets 0.

### THE SHIFT

Opened clean: no halt, run #64's guard `done:true`, guard claimed with a token (heartbeat kept by a
bounded background loop). `corpus_db --rebuild`: 216 sources, 282,822 entries, 128s.

**Queue, worked to the floor:** 3 LOCAL notices (overnight and overwatch rc=17 restarts, the
publish-resumed notice) verified against the process table and closed. Two more restart notices
caused by this run's own edits (dashboard, publish) closed the same way; publish restarted at
22:31 on the new code. The one RUN order, `573ab7b04b6f`, was diagnosed (above) and rerouted to
OWNER, because the fix is a tool install and a login. BOTS: `058fa19d4e65` stays until
`data/CHAIN.json` carries `unmatched` (still the August shape); the two fandom throttle
quarantines close themselves when they lapse.

**Fixed by the run:** M126 (the drift grant, the drill reason capture, and a truthful "red at
baseline" line when the red came from an earlier target), and the publish probe that now names
the package-store case (M127, display only).

### SWEEP65

16 Sonnet auditors, one per frozen batch (`state/sweep_plan/run65.json`). Every module was read
in full, and `sweep_plan.missing('run65') == []`. Audits are in `handoff/sweep65/`. 13 batches
found nothing new and confirmed sweep64's fixes in place. Every finding was re-read against
source by the run.

* **M128, fixed with a different remedy from the one proposed.** batch03 reproduced
  `write_record_catalogue` dropping a disk-only entity to keep a duplicate. The proposed fix
  (carry every such row) would grow a record on every re-catalogue that rewords a duplicated
  name, so the run kept the count bound and changed only which rows fill it. The drill net gained
  two cases, and both reverts (old order, naive fix) were watched going RED.
* **Small:** verify_math's one bare `assert` made an explicit raise (batch02); a stale
  present-tense comment in `wh40k.main()` corrected (batch03); the new publish probe's Roaming
  edge fixed (batch10).
* **Checked and not changed:** batch06's "HOST_QUARANTINED / BINDING_SUSPECT sit at BOTS with no
  closer". The first closes when its quarantine lapses (run #64 showed six do), and the second
  closes on the next canary sweep, which the daily run operates. The routing stands.
* **Two concurrent verify_math runs collide** (they share the cascade scratch DB and the restart
  ledger): run together they gave 4 FAILED, alone 0. That was this run's own mistake, not a
  library fault. Run verify_math one at a time.

### THE BATTERY AT CLOSE

drill **641/641/0** (1 new net, 2 new cases in an existing one) · verify_math **1318/0** ·
pyflakes clean · liveness 46 · silence 316 · secondopinion: ruff, vulture, detect-secrets all
RAN, 0 secrets · axis_correlation 45 entities, unchanged (not re-written) · health --preflight 1
problem (dandwiki's login wall, OWNER) · allsweep 2 bad rows, both standing OWNER orders: the
dandwiki preflight, and the cascade live call timing out on rate-limited free tiers
(`9fb8a6b10c1f`). The jszip estate row left with rodais.

### RESTARTS

publish.py, pipeline.py, mutate.py, verify_math.py, drill.py and wh40k.py changed. publish
(pid 25568) and dashboard restarted on the new code. pipeline (pid 44264, since 09-25) takes
rc=17 at its own phase boundary; its change (M128) matters only when a catalogue write runs
inside it. The crawl (`feats.py --roll`) is EXEMPT and runs the old `write_record_catalogue`
until its lap ends, which is the behaviour it had before, not a new risk. mutate.py, verify_math.py
and drill.py are not daemons, and the running mutation pass holds its launch copy by design.

---

