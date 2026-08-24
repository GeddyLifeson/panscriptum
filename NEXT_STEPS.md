# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #4 wrote this on 2026-08-24 ~01:00.*

**State of the ledger: there are no open bugs awaiting only implementation.** Everything left in
BUGS.md's Open section is either a HUMAN CALL (M1, m12, m13, m16) or an operational state being
watched (m1, m2). Runs #3/#3b/#4 closed m3–m11, m14, m15, m17–m22 plus the two matching-logic
bugs and the Ollama wedge. So this run's queue is mostly *verification* and *owner decisions* —
if both are clear, the honest next move is a new audit surface (section 4), not invented work.

*Nothing from run #4 is left hanging: the stranded-batch fix closed end-to-end (preflight now
reads `ok  state consistency`), Ollama is serving with zero 503s in the fresh pipeline log, and
every implementation-ready bug is fixed. Start at section 2 unless something below has drifted.*

## 1. Verify first

1. **Local-model throughput, not liveness.** The runner is up and serving (run #4: 0 × 503 in a
   fresh `pipeline_auto.log`, and a full phase-2 source completed in under a minute). But a 30B
   MoE at 8.5 GB on a 10 GB card offloads heavily to CPU, and an earlier instance sat inside a
   single call for 40+ minutes. If phase 2 stops showing progress, sample `units_done` in
   `PIPELINE_STATE.json` twice a few minutes apart before concluding anything — and treat it as a
   model-choice / offload question for the owner (`pick_model.py` ranks candidates), not a
   correctness bug.
2. **[m23] job logs are truncated on every restart** — this bit run #4 directly (see BUGS). Until
   it is fixed, transcribe anything you are diagnosing out of `state/<job>.log` before the keeper
   bounces the job, or the evidence goes with it.
3. **The new `the local model has a live runner` standard** should read `runner up, N resident`.
   If it ever reads `NO llama-server process`, the remedy is restarting `ollama.exe` by hand
   (the tray app respawns it) — it is in the OWNER lane deliberately and will not self-heal.
4. **The stall detector is still young.** Run #3 made `every running job is advancing` able to
   fire for the first time. Check `state/job_progress.json`: stamps should age on quiet logs and
   reset on growing ones. If it reports a job stalled, verify the job was really wedged before
   trusting it — and if false positives recur, raise `MAX_JOB_SILENCE_MIN` (15) rather than
   re-breaking the timer. Its AUTO remedy SIGTERMs the job.
5. **Two spine assignments now land in UNASSIGNED** (`Sword Coast Adventurer's Guide`, `Who
   Framed Roger Rabbit (…)`) and appear in `output/index/unassigned_sources.md`. They need the
   owner's real Collection/Set assignment — Hard Rule 2 curatorial work, not a code fix.

## 2. Human decisions needed (owner) — unchanged unless noted

6. **`kill_stalled_job` is in the AUTO lane** and now reachable for the first time. Keep it
   automatic, or move it to OWNER?
7. **Should the Ollama-wedge standard get an AUTO remedy?** Run #4 deliberately did not add one.
   A restart is mechanical and reversible, and the wedge cannot clear on its own — but it is a
   service restart, so it is the owner's call whether the foreman may do it unattended.
8. **[m12] `thread_integrity.py`'s asymmetric/dangling detection is structurally unreachable.**
   Is the module meant to compare implied threads against a separately-recorded DIRECTED thread
   graph it currently isn't given? Not a one-line fix either way.
9. **[m13] `phase_synthesis`'s 14-entity ceiling sample** can clamp a whole source to a lesser
   band if the true strongest entity isn't sampled. Raise, re-rank, or accept.
10. **[m16] `weave.py`'s `shared_sample` (8, sliced to 6)** — diagnostic evidence, not
    reader-facing content, but Hard Rule 0's text doesn't carve out diagnostics. **Same ruling
    settles `dashboard.py`'s `/api/state` `findings` cap of 12.** One decision, two sites.
11. **[M1] dandwiki.com** — browser-UA HTML reader vs. owner-supplied. Politeness/ToS call,
    open since run #1. `health --preflight` will keep reporting its cache all-empty until this
    is decided; that FAIL is this decision, not a fault.
12. **Permanently hostless roll entries** (Clockwork Angels, Twilight Imperium, HAWX, …) — stay
    on the roll as owner-supplied-text candidates, or come off?
13. **Paid burst lane** — 500-call cap, counter in `state/PAID_BURST.json`. Raise, keep, retire?

## 3. Carried operational items

14. **[m1] Marvel completeness row** — re-check whether still ~0.4% stale. Note run #3's m3 fix
    changed what `completeness.py` reports for all-probes-failed sources, so re-read the row
    before suspecting the byslug matching.
15. **[m2] 6 roll sources never catalogued, 20 catalogued with no host** — scout/adopt keep
    retrying; overlaps item 12.
16. **Charter regression** — `data/CHARTER_REGRESSION.json` exists. Confirm the `automation
    reproduces the charter` standard takes a real reading from it rather than a vacuous pass.

## 4. Surface rotation for the next audit fan-out

Covered, do **not** re-read unless the diff touched them: the round-1 full-codebase audit and
evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces (derivation/rigor/handbuilt;
sweep/endpoint/wiki_source/coverage; build_terminal/weave/weave_index/navtree/render;
pipeline/ledger/thread_integrity); run #3's two (ingest_doc/manifest_builder/generate/address/
catalog; foreman/standards/publish/overnight/dashboard).

**Not yet audited line-by-line** — pick from here: `assay.py`, `magnitude.py`, `chain.py`,
`identity.py`, `cascade_bridge.py` (only partly covered), `compress_store.py`, `module_index.py`,
`hostcheck.py`, `scout.py`, `tuning.py`, `catalogue_web.py`, `silence.py`, `health.py`,
`overwatch.py`, `local_agent.py`, `read.py`, `feats.py`, `estate.py`, `worldseed.py`, `onomast.py`.

## 5. Two lessons worth keeping

- **Diff the whole corpus before and after any matching-logic change.** Run #3 shipped two
  first-cut fixes that regressed real behaviour — `Soul Calibur` fell out of II.A.7, and source
  `DC` was misrouted to the Sword Coast record — and *both* were caught only by diffing all 215
  roll entries. A fix that looks right on the reported case is not verified until the cases
  nobody reported are checked.
- **Distrust a green liveness check.** The Ollama wedge was reported healthy by every probe in
  the project for 31 minutes because they all asked `/api/tags`. When a job is doing no work,
  read the job's own log before believing any status summary — and prefer a check that asserts a
  contradiction cannot exist (resident model with no runner) over one that asserts a service
  answered.
