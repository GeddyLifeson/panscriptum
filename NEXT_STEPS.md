# Next Steps — written by run #37 for the run that follows it

*Overwritten every run. The queue in `state/workorders.json` is the authority on what is open;
this file is the reading of it — what to do first, and why.*

---

## 0. NOTHING IS HALTED. TWO HALTS WERE RAISED AND LIFTED LAST NIGHT — READ THAT, THEN MOVE ON.

`escalation.py --status` reads **clear**. Both halts were raised by run #37's own work and
lifted by run #37 after fixing the cause, under the self-caused clause of the 2026-08-25 owner
ruling. Full rulings are in `state/HALT.json`'s history and at the top of HANDOFF.md.

- **`DRILL_BREACH` (22:44, lifted 23:31)** — `blast_cap_bites` breached because order
  528e5b07fded correctly stopped the local model being billed for edits that never happened, and
  the drill's probe had been demonstrating the cap through exactly that path. **The cap was
  never broken.** The probe was rewritten to drive the real path.
- **`SECRET_IN_EXPORT` (23:53, lifted 00:2x)** — the publish gate refused two credential-shaped
  values staged for the public repo. They were **fabricated fixtures** written by a sweep agent
  asked to prove the scanner works, landing in `handoff/`, which is published. Nothing leaked;
  nothing was pushed. Scratch moved out, audit line redacted, order f0fe623a67c0 filed.

**Do not re-derive the state of the library.** Open the shift the way the card says —
`escalation --status`, the run guard, `workorders --sweep`, `corpus_db --rebuild` — and then
work the queue.

## 1. THE ONE THING A PERSON HAS TO DO, AND NO RUN CAN

**Order f6c52ef7657f (OWNER).** PID 25716, `pythonw -m semsearch.cli watch` — **not part of this
project** — cyclically floods `127.0.0.1:11434` and consumes this machine's entire ephemeral
port range. Measured at 32,467 of 32,651 host sockets. While it floods, every outbound
`connect()` fails with WinError 10055/10048, and **every one of these is a symptom of it, not a
fault in this library**: the local rung dead, the read pass at a ~3,958-hour ETA (this *is* order
a8464e348c5e's "1.7 years"), "0 of 36 buckets answer", "fandom answers this machine: connect
fails", `roll_auto` stalled, and the two ollama standards dropping out of the battery.

**One `Stop-Process -Id 25716` reopens the local rung, the crawl, the cloud pool and two
standards.** Run #37 did not do it: terminating another project's daemon is an owner call.

## 2. THE MUTATION PASS IS PROBABLY STILL RUNNING. CHECK BEFORE YOU RELAUNCH.

Launched 2026-08-28 23:33, `--target all --file-orders`. It was unfinished at the close and
`state/mutate_20260828.log` is **empty because it was launched without `python -u`** — that is a
launch defect, not a mutate.py defect. Check for a live `mutate.py` process first; if it has
exited, read the log and put the survivor count in your handoff.

**Do not trust a survivor count until two things are fixed** (both filed):
- **9a694b3ae227** — the generator skips **55 of 93 comparison-operator sites (59%)**; `in`,
  `not in`, `is`, `is not` and chained compares produce no mutant. `escalation.py` is worst at 13
  of 20 sites never attempted.
- **91c1a581453d** — `run()`'s public entry defaults `base=None`, scoring **every mutant
  KILLED**. Fixed on the CLI path only.

## 3. WORK THESE FIRST

`handoff/sweep37/REMAINING_QUEUE.md` is the full ranked snapshot. The short list, in order:

1. **0b75182d495c** — 1,496 of 4,559 `done.entrypass` keys name spans **unsettled on disk**. The
   writer was fixed last night (9ef51c36acea); the corpus was not, and `phase_entrypass` skips
   anything in its done-keys, so **no amount of running the pipeline repairs this**. Clearing the
   affected keys costs real model time, so confirm on a sample first and do not clear keys for
   spans that *are* settled.
2. **776507b529c5** — the run-36 red-check that shipped the above defect **could not see it**:
   its fixture uses entries carrying no judgment fields. A fixture simpler than the data is a
   check that cannot fail in the one direction the code can break.
3. **fc8e20f90ee9** — 45 open orders still hold a `what` truncated at exactly 600 characters.
   The cap is gone, but the damage stands: **28 tails are recoverable verbatim from `handoff/`;
   17 have lost their remedy permanently.** Recover the 28.
4. **d770b1896635** — `health._flush_ledger`/`_flush_samples` read-modify-write
   `state/failures.json` atomically but **without compare-and-swap**; a competitor's 7 recorded
   failures were watched being clobbered. `silence.replace_if_unchanged` exists for this and has
   no call site in `health.py`.
5. **1f172f5acc6f** — standing jobs that never check their own source. **Read the six-point note
   inside the order before touching it**: the roster should come from `overnight.ALL_JOBS`, not
   `STANDING`; `hostcheck`/`magnitude` are one-shot tools and correctly uncovered; `pipeline` and
   `overnight` are missing from the order and *are* in STANDING; the net's shape must change too
   or it will breach against correctly-wired code; and **`autostart.py` must not simply exit
   rc=17 — nothing relaunches it but the logon shortcut.**
6. **14bd09740627** — allsweep's VERIFY tier is graded by nothing (`rc` is never read). A blanket
   `rc != 0` is the wrong fix: `silence` and `audit` exit 1 by contract.
7. **6e0127c4f3ed is FIXED, but its second layer is still missing** — `verify_math` asserts that
   `prose_enabled` is a *bool* and never *which* bool, and asserts nothing at all about
   `step4_enabled`. Any future path onto `config.yaml` still clears the whole battery.

## 4. TWO NETS ARE OWED. BOTH ARE FIXES THIS PROJECT HAS NOT YET WATCHED REFUSE.

- **The prose gate's invented-entry refusal** (212e3096edfc, fixed). No drill net asserts the
  gate *refuses* in this direction — only that a message exists. The exact check to add is
  written into the order's closure text.
- **The stranded-synthesis detector** (1f39177464cf, fixed). `drill.py` was owned by an agent for
  the whole of run #37, so the net could not be added concurrently.

Per the standing rule: add the attack, and **watch it go red once**.

## 5. WHEN YOU DISPATCH THE SWEEP, DO NOT TRANSCRIBE THE BATCH LIST BY HAND

Run #37 did, and silently dropped two modules from two briefs. Both agents reported "all modules
read in full" and were telling the truth about their briefs. **Only `sweep_plan.missing()` caught
it** (order 34cf5b961af1). Hand each agent its list *from* `batches()` programmatically, or diff
the briefs against `batches()` before dispatch.

## 6. HOUSEKEEPING

- `state/failures.json` holds **test residue** from run #37's deliberate denial injection —
  `corpus_db.py:datasette-metadata-denied`, `feats.py:remine-write-denied`,
  `generate.py:save-denied`, sweep-agent probes at 23:37–23:40, and an injected
  `sweep_plan RuntimeError('boom')` at 23:01. **Not real faults.** One coordinated reset when the
  machine is quiet.
- `data/records/getter-robo.json.precatfix` — a non-`.json` leftover in the records directory.
- **Bounce foreman and overwatch early.** Both ran the whole of run #37 on pre-shift code. The
  cause (838be29f9e58, `codewatch.stale`'s settle window being one poll interval rather than
  wall time) **was fixed last night**, so once they restart once they should keep themselves
  current.

## 7. OWNER DECISIONS STANDING (do not decide these in a run)

- **b57e23204f66** — what `axis_correlation.rho()` returns when the matrix is unreadable. The
  header promises the measured mean, the code returns 0.0. The fallback is now loud; only the
  value is open. The reasoning against both alternatives is recorded in the order.
- **bd673ceaaf31** — Lumen and Threnody cannot contribute what they exist to measure; no ANCHORS
  entry carries a vantage, and defaulting one would invent the measurement.
- **707fefc17465** — `render.py` is reachable by hand and by nothing else. Wire it in or retire
  it deliberately.
- **585fcd3774b8** — `bone-jeff-smith.json` holds 86 entries and no roll row reaches it.
- **30854f11f322** — `binding_verdict`'s false CONFIRMED. Left open **deliberately**: the
  prescribed fix is provably infeasible (every rapidfuzz metric ranks the false positive above a
  real confirmed binding, reproduced twice independently). The separating evidence is the wiki's
  content, not the two strings. Do not force a threshold; the evidence is now published beside
  the score.
