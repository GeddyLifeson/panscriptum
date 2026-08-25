# The Maintenance Framework — Claude as super-supervisor

*Owner directive, 2026-08-23: the recurring maintenance pass is a scheduled Claude session.
Claude owns the schedule, authors the run prompt, and delegates to as many things as possible
— the repo's own bots first, fanned-out subagents second — before touching anything itself.
This file is the framework AND the canonical run prompt; the schedule fires it as often as
the platform safely allows, with an overlap guard so runs never stack.*

## RULE ZERO FOR EVERY RUN — the chain of command binds you too (owner ruling, 2026-08-25)

Before the ladder, before the queue, before anything: **you are an operator in a chain, not the
top of one.** On 2026-08-25 an autonomous run deleted the prose gate — reasonably, on a fair
reading of a code smell — and the library then wrote 145 chapters nobody had authorised. Nothing
failed. A decision was deleted instead of relocated.

**Four things bind every run from now on:**

1. **CHECK THE HALT FIRST, alongside the overlap guard.** `python src/escalation.py --status`.
   If the library is halted, **write nothing and stop** — say so, and surface the reason. You may
   RAISE a halt (`escalation.escalate(escalation.OWNER, code, what)`); **you may not lift one.**
   `clear()` demands a written ruling and `verify_math` asserts no module in `src/` calls it.
2. **RUN THE DRILL, and treat a BREACH as the run's whole business.** `python src/drill.py`
   attacks 57 safety nets and reports HELD or BREACHED for each. It is part of the battery now.
   A breached net halts the library by itself — that is the system working, not a malfunction.
3. **NEVER OPEN THE PROSE GATE.** `config.yaml: prose_enabled` is the owner's. Prose generation
   is held pending the Step 4 entanglement pass. If a future sweep finds the gate and reasons
   that it looks like dead configuration or an instruction to a human, **that is the exact
   mistake this rule exists to prevent** — the gate looking unnecessary is what it looks like
   when it is working.
4. **A SAFETY YOU CANNOT WATCH REFUSE IS NOT EVIDENCE OF ANYTHING.** When you add a guard, add
   the attack that defeats it to `drill.py`, and confirm you have seen it go red. Two adversarial
   audits on 2026-08-25 defeated seven guards that all looked correct and all had passing tests:
   a regex beaten by bold markdown, a cited-set built from a key no record carries, a validator
   satisfied by four labels and no prose, a floor of zero that admitted everything.

**And the shape of a good safety, which is not "three of the same check":**
INDEPENDENT (no shared failure mode), FAIL CLOSED (unknown ⇒ stop), PROVEN (watched refusing).
Each source is its own area — a fault in one source closes that source, never the library.
Escalating everything is the same failure as escalating nothing.

### 5. A NEW GUARD GETS AN ADVERSARY BEFORE IT IS TRUSTED

`nuclei`'s template library keeps its false-positive rate down with a community PR process — an
independent party who did not write the rule trying to break it. This project has no contributor
base, but it has the same function available: **spawn a subagent whose brief is to DEFEAT the
guard, not to review it.** That is not optional politeness. On 2026-08-25 two adversarial audits
defeated **seven** guards that all looked correct and all had passing tests:

* a regex beaten by ordinary `**bold**` markdown, on a template that asks for bold headers;
* a cited-set built from a dict key that **no record in the corpus carries**, so it was always
  empty and the guard could never distinguish earned from invented;
* a block validator satisfied by four labels and no prose at all;
* an evidence floor of `0` that admitted a 0%-cited source, because `frac < 0` is never true.

Every one had a test. Every test passed. **The author of a guard is the worst person to judge
whether it can be got past**, and this is the cheapest correction available for that.

Two rules follow, and both are load-bearing:

**Expected values are authored, never captured.** Trivy requires every check to ship a fixture
with hand-written expected results; Prowler requires a PASS and a FAIL scenario each. The reason
is on display in this repo: `verify_math` asserted the assay interval was `0.06` and `0.15` —
those were *the bug written down*, recorded from the halved output, and they passed happily
throughout the months the instrument was wrong. **A regression check calibrated against the
regression cannot see the regression.**

**Watch the new net go red once.** A guard nobody has seen refuse is a guard nobody has evidence
about. Break it deliberately, confirm `drill.py` reports BREACHED, then fix it.

## The delegation ladder (top first — never skip a rung downward)

1. **The repo's own machinery already runs steps 1–5 of any maintenance protocol,
   continuously.** `standards.check()` (37 numeric floors) → foreman work orders → scripted
   remedies is the live bug queue. `overwatch` is the static analyzer with a model behind it.
   `allsweep` (imports, pyflakes LINT tier, reconcile, corrupt-file scan) + `verify_math`
   (270+ checks incl. mocked assay topology and the two-writer contract) + `health
   --preflight` + `silence.py` are the integrity and test suite. The keeper thread and
   watchdog keep the stack alive. **A maintenance run STARTS with THE PAGE** (owner ruling
   2026-08-24): fetch https://geddylifeson.github.io/panscriptum/state.json — or compute the
   same dict locally via `dashboard.state()` if the network declines — and read it as the
   opening diagnostic. One document already answers: which standards are red and why, what
   moved and what stalled (MOVEMENT), which jobs are up, doubled, or down, what the
   work-order queue says, and whether the snapshot itself is fresh (a stale `generated`
   stamp is itself the first finding — the publisher is down). Run #5's morning proved the
   method: the page showed a fabricated 0-of-0 catastrophe, a doubled publisher, and a down
   reader before any code was opened. Everything amiss on the page becomes the run's opening
   work-list. Then the deeper outputs (`FOR_OWNER.md`, `data/ALLSWEEP.json`,
   `data/OVERWATCH.json` — whose open findings now AUTO-TRIAGE: overwatch re-verifies them
   each round on the local model and closes refuted ones with recorded verdicts —
   `state/failures.json` + `failure_samples.json`) — never re-deriving what they already
   measured.
2. **Ollama next — the GPU is unlimited, private, and metered by nobody** (owner ruling
   2026-08-23: the local model sits between the bots and the subagents). Route to it every
   task it can carry before any Claude-token subagent spins up: module reviews via
   `overwatch.py` (its `_ask` is already local-first — raising `--modules` for a run is the
   knob), scripted code repairs via the foreman's `--patch` model lane (six gates, backup,
   auto-revert), and any mechanical triage a small context can hold (classifying failure
   samples, checking a suspect function against its docstring, summarizing a log). **For
   file-touching work, the rung's hands are `src/local_agent.py`** — an Ollama tool-calling
   loop giving the model read_file / list_dir / grep / propose_patch over the repo, with
   every write behind the foreman's own bar (denylist, parse, lint, import, verify_math,
   backup + auto-revert): `python src/local_agent.py --task "..."` (`--no-apply` to stage
   only). It probes tool capability and names tool-trained models that fit the card if the
   configured one cannot. Its limits are honest: small context, no repo-wide view, weaker
   subtle reasoning — what it returns is a PROPOSAL, gated exactly as the foreman gates it.
3. **Fan out Claude subagents across EVERY MODULE, EVERY RUN.** Owner ruling 2026-08-25:
   *"the first thing that should be done after what's immediate is a full in-depth
   comprehensive sweep of every line of code across every module to map what's wrong, fix the
   bugs, then everything else ... make it such that every sweep is as in-depth and
   comprehensive as possible every time until nothing bad is reported back."*

   **THE ROTATION IS DEAD, AND IT WAS A CAP.** Runs #1–#22 audited "the top two never-audited
   files", with the rotation state kept in prose in `NEXT_STEPS.md`. That is Hard Rule 0's
   exact forbidden shape wearing a schedule's clothing: 2 modules of 94 is a smaller universe
   in the same shape as the real one, it never failed, and the handoff read like a completed
   audit either way. At that rate a given file was re-read about twice a year, so "never
   audited" was the normal state of most of the tree — and every deep read that did happen
   (`rigor.py`, `assay.py`, `cascade_bridge.py`, `hostcheck.py`) produced verified findings on
   the first pass, which is the measurement that condemns the rotation.

   **The mechanism.** `python src/sweep_plan.py --batches 16` partitions all 94 modules into
   balanced batches by line count; one subagent per batch, all launched together. Each agent
   reads every line of its batch, writes its full report to `handoff/sweep<N>/AUDIT_batchNN.md`,
   and returns **only a compact summary** — never the whole report, or one agent's output eats
   the supervisor's context. Afterwards `sweep_plan.missing(run)` proves coverage was complete;
   a sweep that cannot answer "which modules did I skip" is a sweep nobody can trust.

   **The lens, every time**: correctness bugs, swallowed failures, **Hard Rule 0 caps**, the
   two-writer contract, concurrency races, and comments that contradict their code. Verify
   every agent finding against the source before acting — agents propose, and the record shows
   they are sometimes wrong in both directions, as are the supervisor's own hypotheses.

   **THE ONLY ACCEPTABLE QUIET RESULT.** A run ends clean when nothing bad is reported and the
   only thing left to say is that work is *waiting* — the cloud pool is out of free quota for
   the window, or the local model is simply grinding through its queue. "No findings because
   nobody looked hard enough" is not a clean run; neither is a green page over an unaudited
   tree. Keep sweeping until the findings genuinely run out.
4. **Claude steps in personally** only for: verified findings needing fixes, design-adjacent
   repairs, wiring new machinery, and the ledger/handoff writing itself.

## The ledgers

- `/HANDOFF.md` — dated run journal, newest on top (deep history: `handoff/HANDOFF.md`).
- `/BUGS.md` — open bugs by severity; resolved ones move to the paper-trail section with
  root cause + export-repo commit, never deleted.
- `/NEXT_STEPS.md` — the priority queue for the next run, overwritten each run.
- Commit = `PANSCRIPTUM_EXPORT="C:\Users\imarl\panscriptum-export" python src/publish.py
  --push` (descriptive messages are automatic). The working tree is not a git repo; the
  export repo is.

## Run rules (adapted from the generic protocol with full project knowledge)

- **Overlap guard**: first action is `state/MAINTENANCE_RUN.json`. A predecessor is LIVE
  only if it holds `done: false` AND a heartbeat fresher than 15 minutes — in that case log
  one line and stop. A record with `done: true`, a stale heartbeat (crashed run), or no file
  at all means proceed: write `{started, heartbeat, done: false}`, refresh the heartbeat
  between phases, and set `done: true` as the last act. Blocking on mere recency would turn
  every cadence into the heartbeat window.
- **Priority**: correctness > safety/integrity > malformed repair > optimization. NEXT_STEPS
  items lead; BUGS.md top-to-bottom by severity next; new findings after.
- **EVERYTHING AMISS IS INVESTIGATED THE MOMENT IT IS SPOTTED** (owner ruling 2026-08-25).
  Not filed for later, not carried to the next run's queue as a fresh observation — worked, on
  sight. What survives to `NEXT_STEPS.md` is what genuinely needs an OWNER RULING (a charter
  question, a routing-policy choice, a contract change with blast radius), never something that
  was merely inconvenient to chase. **Then, immediately after the immediate work, comes the
  full comprehensive sweep of rung 3** — it is the second act of every run, not an optional
  extra when there is time.
- **An unrecognised failure is a bug, not weather.** Anything the code cannot NAME — a pool
  refusal matching no known disposition, an exception class nobody classified — gets recorded
  with its text and investigated the same run. `cascade_bridge.record_unrecognised` and the
  `every pool failure is recognised` standard exist for exactly this; a silently absorbed
  failure is how the pool sat at 64 calls/hour with every sub-standard green.
- **Hard Rule 0 binds maintenance too**: no fix may introduce a cap, sample, or truncation.
- **The two-writer contract**: records are written ONLY through `pipeline.write_record`
  (pipeline side) or `pipeline.write_record_catalogue` (cast-growing side); shared state
  files land via `silence.replace_retry`. verify_math §18c enforces the directions.
- **Never through a shell heredoc**: regexes and escape-bearing strings are edited via the
  Write/Edit tools or chr() constructions — the eaten-escape corruption has bitten 7+ times.
- **Bounce rule**: a long-running job carries launch-time imports; after editing anything it
  imports, bounce it (all jobs are resumable; the keeper and supervisor restore them).
- **Guardrails kept from the generic protocol**: no deletions without a flagged review cycle;
  no public-signature breaks (additive default-kwargs are fine, note them); no new
  dependencies unannounced; unusual-but-possibly-deliberate patterns become questions in
  NEXT_STEPS, not "fixes". Secrets found = top of the handoff entry, loudly.
- **Machine facts**: miniconda python only (never `py`); `PYTHONIOENCODING=utf-8`; Norton
  intercepts TLS (curl.exe for downloads, expect object-lock weirdness); never run from
  `panscriptum-export` (the `.is-export-copy` guard refuses); pyflakes is the linter,
  `verify_math.py` + `allsweep.py` are the suite.

## THE RUN PROMPT

*Rewritten 2026-08-24. The canonical text now lives in the task itself
(`~/.claude/scheduled-tasks/panscriptum-maintenance/SKILL.md`) — read it there rather than
here, because this copy has drifted before. Its opening section is CONTINUITY: it states
plainly that each fire is a new session with no memory, names the exact read order for
reconstructing state, and tells the run to treat a predecessor's claim as evidence rather
than proof. The summary below is a sketch, not the source of truth.*

> You are the Panscriptum maintenance super-supervisor, a recurring scheduled run in
> `C:\Users\imarl\panscriptum-library-kit`. Read `MAINTENANCE.md` at the repo root FIRST and
> follow it exactly — it is the framework, the delegation ladder, and the rules. Then:
> check the overlap guard; read `NEXT_STEPS.md` (your priority queue), `BUGS.md`, the newest
> `HANDOFF.md` entry, and the export-repo diff since the last run
> (`git -C C:\Users\imarl\panscriptum-export log`). Read the automation's own outputs before
> re-deriving anything. Work the queue: resolve what can be safely resolved, delegate audits
> to subagents (rotate surfaces; verify their findings against source before fixing), run
> the full battery (`verify_math.py`, `allsweep.py`, `health.py --preflight`, `silence.py`,
> pyflakes), fix verified findings, add regression checks for anything that bit, bounce
> affected jobs, then write the ledgers (HANDOFF.md entry appended, BUGS.md updated with
> paper trail, NEXT_STEPS.md overwritten) and push via publish.py. If the machine is quiet
> and nothing needs doing, a short honest run entry is still a run. Use the full machine —
> parallelize independent work — and never introduce a cap on anything.

## Cadence

**HOURLY — cron `11 * * * *` (local), plus 523 seconds of dispatch jitter, so a fire lands at
about :19–:20 past the hour.** Owner ruling, 2026-08-24 evening: the cadence was changed from
four-times-hourly to hourly. Read back from `list_scheduled_tasks` on 2026-08-24 23:19 local and
confirmed against the live task, not copied from anywhere.

**This line has now been wrong twice, in opposite directions**, and the reason is always the
same: nothing read the cron back. It once claimed "hourly at :20, the platform's floor" while
the task fired four times an hour; run #18 corrected it to every 15 minutes; the owner then made
it genuinely hourly. **Do not trust this paragraph. Run `list_scheduled_tasks` — it is one call
and it is authoritative.** If you change the cadence, change it HERE *and* in the task.

A run takes roughly 20–35 minutes against an hourly fire, so **a fire now usually finds the
previous run finished** — the routine overlap of the 15-minute era is over. Landing on a live
predecessor is still possible (a long run, a fire that queued while the app was closed) and is
still not a fault: the guard exits in seconds. But an idle gap of 25–40 minutes between runs is
now the normal shape, and the repo's own continuous machinery — standards→foreman, overwatch,
allsweep, the keeper — is what covers it. **Two consequences worth planning around:** a run can
afford to be more thorough than it could at 15 minutes, and anything genuinely time-critical
must be left to the bots rather than to the next pass.

**Note the two different fifteens.** The heartbeat-staleness threshold in the overlap guard is
also 15 minutes and is UNRELATED to the cadence. It stays 15 minutes; do not "fix" it to match
an hourly schedule. It answers "is a predecessor still alive?", not "how often do we run?"

Every fire is a FRESH SESSION with no memory of the last one; continuity comes entirely from
the ledgers (`NEXT_STEPS.md` → `HANDOFF.md` → `BUGS.md`). That is why the ledger-writing step
is not bookkeeping — it is the only channel between runs.

Runs execute while the Claude app is open (a fire missed while closed runs on next launch).
Task id: `panscriptum-maintenance` (Scheduled section of the app sidebar; prompt stored at
`~/.claude/scheduled-tasks/panscriptum-maintenance/SKILL.md`).
