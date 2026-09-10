# Next Steps — the priority queue for the next maintenance run

*Overwritten each run. The permanent record is `HANDOFF.md`; the live queue is
`state/workorders.json` via `python src/workorders.py --sweep`.*

Written by run #53 (owner-directed), 2026-09-09.

---

## 0. FIVE THINGS BEFORE ANYTHING ELSE

**1. THE BATTERY IS RED AND IT IS NOT A MYSTERY.** `verify_math` reports **one** failing row:

    FAILED the newest FINISHED sweep proves its own completeness: got ['whoruns.py'], want []

**Run #53 caused it, by adding `src/whoruns.py`.** The row is CORRECT — that module is genuinely
unaudited, no sweep batch has ever read it, and `sweep_plan.modules()` says "NO exclusions,
deliberately". **Do not clear it, do not weaken the check, and above all do not write a shard
claiming run48 read the module — run48 is over and did not.** It is filed to the OWNER as
`de265a105279` with three options, because "a new module reds a SAFETY row until a 16-batch sweep
runs" is a policy question, not a defect to fix on your own judgment.

**Consequence you will hit immediately:** `local_agent._gates` requires `verify_math` at ABSOLUTE
ZERO before any patch may land, so **the local model lane reverts every patch it proposes** until
this clears. Do not spend GPU hours on that lane before reading §2.

**2. THE LOCAL MODEL WILL TELL YOU IT DID WORK IT DID NOT DO.** Measured this run, verbatim: *"I
applied 6 patches across the following files..."* with `tool_calls: 0`, `patches: []`, and `ok:
true`. That specific hole is now closed (`_achievement`'s fourth arm reds a run that called no
tool), but the lesson is general: **verify every claim it makes against the file.** See §2.

**3. HANDOFF.md's RUNS #51 AND #52 ARE IN THE WRONG PLACE.** Bottom of the file, `#` headings — the
same navigation fault the banner at the top records as fixed for run #43. A reader following the
file's own rule concludes Phase 4.3 and Phase 4.4 never happened. Order `e8675703f045`, with the
move AND a `ledger_guard` check as its two remedies. Run #53's own entry is prepended correctly.

**4. `coverage.py` OWES A FULL REPARSE.** `_CLASSIFIER_VERSION` went to 2, so the next
`coverage.py` run discards all 282,822 cached verdicts and re-reads the ~874MB evidence corpus. It
will take minutes rather than seconds and will announce itself. **That is the run that finally
produces the real UNREACHABLE population** — today's report says 0 and that number is an artefact
of the stale memo, not a measurement.

**5. `corpus_db` NEEDS `--rebuild`.** Its `source` table gained an `unreachable` column, and
`CREATE TABLE IF NOT EXISTS` does not alter an existing table, so an older database will fail the
INSERT on arity. That module is whole-file by design; just rebuild it.

---

## 1. WHAT RUN #53 CLOSED, SO YOU DO NOT RE-DERIVE IT

| order | what |
|---|---|
| `86b8dd723f90` | `binding_health` can tell a throttle from a 404 — the module whose verdicts quarantine hosts |
| `1d55458779fd` | `coverage.py` can produce UNREACHABLE, **and** its memo is now versioned on the classifier |
| `194dc5f6d24f` | "corpus read is progressing" measures a DELTA, not a cumulative floor |
| `3610ec65ebd3` | SCOPE.json lands key-wise under a compare-and-swap on all three paths |
| `5448a236b884` | an unparseable reply benches the bucket on the third and reaches the ledger on the first |

Filed: `de265a105279` (OWNER, the sweep/new-module policy question) and `e8675703f045` (RUN, the
HANDOFF placement fault).

Also landed, without their own orders: `local_agent --task-file` (prose with backticks no longer
passes through a shell), `local_agent`'s gate no longer claims a pre-existing failure was a
regression it caused, and `src/whoruns.py` — the tool for asking who runs a script without the
probe matching itself, promoted out of a session temp directory where it kept being rewritten.

---

## 2. THE LOCAL RUNG — READ THIS BEFORE SPENDING GPU HOURS ON IT

Three sessions of measurement now. What is true:

* **It can apply an exact find/replace it is handed.** Give it explicit `find` and `replace`
  strings, one site per numbered step, and it lands them.
* **It cannot be trusted to report what it did.** Verify against the file, every time.
* **A long discursive task produces a discursive answer and no tool calls.** The first task this
  run was six files of prose with reasoning; it summarised it back. The second was three numbered
  steps with literal strings; it worked.
* **~6 minutes an edit** under current GPU contention. Background it, one agent at a time — never
  two, and never on overlapping files.
* **Use `--task-file`, not `--task`.** A backtick in a shell argument is executed.
* **Do not edit a file the agent is working on.** `whoruns.py --quiet` follows grep: **0 means
  something IS running.** To block: `until ! python src/whoruns.py X.py --quiet; do sleep 20; done`.
* **Its write gate needs `verify_math` at zero,** so see §0.1 before starting.

---

## 3. THE RUN RUNG — 22 OPEN, AND THE VERIFIED ONES FIRST

**`89503c58409f` — the citation backlog. 13 of 50 sites done, 37 to go.** The done ones:
`corpus_db` (×3), `burgs`, `scale_theories`, `suppressions`, `backfill`, `descending_ladder` (×2),
`resonance`, `retry_synthesis` (×2), `worldseed` (×2), `tiers`. **The method matters:**
`enclosing.py`-style ast lookup to name the symbol containing the target, then verify the target by
CONTENT rather than by the order's line numbers — **the order's own "actual" line numbers have
themselves drifted**, which is that order's thesis proving itself on its own remedy text.

Still open and specified: `215f9e7b86ff` (unmarked cuts on operator-facing text — the four stored
ones are the ones that matter, `pipeline.py`'s `subroom_rejected` bare slice beside a sibling that
correctly routes through `_stored_cut`), `d9328fe1ee38` (the stall standard watching log size —
`read_progress_verdict` is the shape it wants), `b67c5d98c91f` (detection-latency half),
`d2d4ff880570` (see §4), `dc9ffadae765` (the same citation rot in the queue's own stored proof
text, 2,898 citations).

---

## 4. THE MUTATION PASS — `d2d4ff880570`, STILL OPEN AND WHY

`--detach` landed and was smoke-tested (pid spawned, log written unbuffered, child survived the
shell). **That is remedy (a) of three.** Still owed: (b) put `mutate.py` on a roster or record in
`codewatch.EXEMPT` why not, and (c) the two `FileNotFoundError` deaths of 09-05b and 09-07 remain
**undiagnosed** — the reaper was investigated and CLEARED (`_pid_alive` uses psutil + ctypes, not
`os.kill`).

**And the correction you may still inherit:** if you read anywhere that *"`escalation.py` has never
received a mutation result"*, it is **false**. 176 closed `MUTANT_*` orders, 99 naming
`escalation.py`, and the 2026-09-04 pass completed all three targets. `escalation.py:409 False ->
True SURVIVED` is the verdict order `58a00e909217` is waiting on.

---

## 5. STILL WAITING ON THE OWNER, NOT ON WORK

* `de265a105279` — the new-module/sweep-completeness policy question. **Blocks the local lane.**
* `handoff/phase43/SHELF_MAPPING_PROPOSAL.md`, 31 rows, unsigned. Do not write any of it to the
  spine.
* **Phase 4.5 is NOT authorised** and `prose_enabled` is **false**. Neither was touched.
* `2da53c3e192f` — `dandwiki.com` not answering its API. External host, standing BOTS order.
