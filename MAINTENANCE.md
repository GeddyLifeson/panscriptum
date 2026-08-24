# The Maintenance Framework — Claude as super-supervisor

*Owner directive, 2026-08-23: the recurring maintenance pass is a scheduled Claude session.
Claude owns the schedule, authors the run prompt, and delegates to as many things as possible
— the repo's own bots first, fanned-out subagents second — before touching anything itself.
This file is the framework AND the canonical run prompt; the schedule fires it as often as
the platform safely allows, with an overlap guard so runs never stack.*

## The delegation ladder (top first — never skip a rung downward)

1. **The repo's own machinery already runs steps 1–5 of any maintenance protocol,
   continuously.** `standards.check()` (37 numeric floors) → foreman work orders → scripted
   remedies is the live bug queue. `overwatch` is the static analyzer with a model behind it.
   `allsweep` (imports, pyflakes LINT tier, reconcile, corrupt-file scan) + `verify_math`
   (270+ checks incl. mocked assay topology and the two-writer contract) + `health
   --preflight` + `silence.py` are the integrity and test suite. The keeper thread and
   watchdog keep the stack alive. **A maintenance run STARTS by reading their outputs**
   (`FOR_OWNER.md`, `data/ALLSWEEP.json`, `data/OVERWATCH.json`, `state/failures.json` +
   `failure_samples.json`, the dashboard state) — never by re-deriving what they already
   measured.
2. **Fan out subagents for what the bots can't do**: line-by-line malformed-code audits and
   optimization audits (rotate the surface — the audit history lives in `handoff/AUDIT_*.md`
   and `HANDOFF.md` run entries; don't re-read what the last run covered unless it changed),
   plus any special focus the diff or BUGS.md suggests. Verify every agent finding against
   the source before acting — agents propose, the transcript record shows they are sometimes
   wrong in both directions.
3. **Claude steps in personally** only for: verified findings needing fixes, design-adjacent
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

## THE RUN PROMPT (canonical — the scheduled task fires exactly this)

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

**Hourly (minute :20 local) — the platform's floor for a recurring scheduled task**, which
is therefore "as often as possible" here; the scheduler rejects sub-hourly minute lists.
Runs execute while the Claude app is open (a fire missed while closed runs on next launch).
The overlap guard makes any frequency harmless — a fire landing on a live predecessor exits
in seconds — and the repo's own continuous machinery covers the minutes between fires. Task
id: `panscriptum-maintenance` (Scheduled section of the app sidebar; prompt stored at
`~/.claude/scheduled-tasks/panscriptum-maintenance/SKILL.md`).
