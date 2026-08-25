# Next Steps — written by run #33 for the run that follows it

*Overwritten every run. The queue in `state/workorders.json` is the authority on what is open;
this file is the reading of it — what to do first, and why.*

---

## 0. THE LIBRARY IS HALTED. READ THIS BEFORE ANYTHING ELSE.

`escalation.py --status` will say **HALTED — `DRILL_BREACH`**, raised by `drill.py` at the close
of run #33. **A halt is the whole run until a person lifts it.** You may raise one; you may not
lift one. Do not work around it, and do not read jobs exiting on purpose as breakage — that
misreading caused this project's longest outage.

**What broke, and it is small.** The net is *"no NEW dead code or unfailable check has appeared"*.
Liveness went **38 → 39** against a ratchet ceiling of 38. The one new entry is
`secondopinion.py:185 ran_clean()` — no callers — in a module that landed at **15:41 from a
concurrent session**, after run #33's sweep partition and after its drill had already started.
Run #33 verified that **no module it touched contributes any dead entry**.

**Check first whether it has already cleared.** `ran_clean()` is a natural helper for a module
that was minutes old, so its author may well have wired up the caller since. Run
`python src/liveness.py`; if the count is back to 38, re-run `python src/drill.py`, and if it is
green, the halt is ready for a person to lift — **which is still not you.**

**`LIVENESS_CEILING` MUST NOT BE RAISED to clear this.** The drill's own expectation line is the
ruling: *the ceiling is a ratchet — lower it when you clean up, never raise it to go green.*

**Publishing is owed.** Run #33 wrote `HANDOFF.md`, `BUGS.md`, `NEXT_STEPS.md` and 18 sweep
reports to the working tree, then `publish.py --push` **refused because of this halt** — correctly,
it reads the interlock first. Nothing is in the export repo. **Once the halt is lifted, publish
before doing anything else**, or run #33's entire record stays local.

Filed as `HALT_NEEDS_RULING` (OWNER, BLOCKING) and `secondopinion.py:185` (SESSION, MAJOR).

## 1. THEN OPEN THE SHIFT THE USUAL WAY

`escalation.py --status` → `state/MAINTENANCE_RUN.json` → `workorders.py --sweep`. Run #33
opened on a clear library and **closed on a halted one** — raised by the drill, not by me, and
**lifted by nobody**. See §0.

**The queue is worth trusting more than it was yesterday, and still not completely.** Run #33
found that a RED battery filed nothing at all — `drill.py` escalated, and `verify_math`,
`health`, `allsweep` and `liveness` did not. That is fixed (M37) and drilled. But the fix covers
the artifacts those tools *leave behind*; a battery member that is never run leaves a stale
artifact, which now fires `PREFLIGHT_STALE` / `BATTERY_STALE` rather than reading as green. **Run
the battery anyway.** A queue is a record of what the detectors last saw, not a substitute for
looking.

## 2. TWO THINGS FOR A PERSON, NOT FOR A RUN

**`www.dandwiki.com` needs a curatorial ruling.** Its API returns HTTP 403 — *"restricted to
logged in users"* — to every request; all 805 cached entries are empty. No retry recovers it.
The only technical remedy is an account, and **no automated run should create one**. The choice
is the owner's: drop the source, re-bind it to a different wiki, or accept that it contributes no
evidence. It is quarantined with that reason recorded, so it costs nothing while it waits.

**Five hosts are `BINDING_SUSPECT` (BOTS, MINOR).** They answer their API but none of their
catalogued titles resolve — e.g. `eberron.fandom.com` is a live wiki whose bound source is a D&D
sourcebook whose entries are rules features the wiki has no articles for. This is a *binding*
fault, not a host fault, and it is a judgement about where a source should read from.
`hostcheck.py --repair` is the tool; whether a re-bind is right is a curatorial question.

## 3. THE FIRST THING TO ACTUALLY FIX: a HARD RULE 0 violation

`HARD_RULE_0_CAP` (RUN, MAJOR). `foreman.scout_hostless()` calls `scout.sweep(limit=4)`, which
ranks hostless sources by entry count and **truncates to the top 4**. Verified in source:
`order = sorted(...)[:limit]`. A *successful* scout removes a source from `hostless()`, so the
window rotates on success — but a **failing** source stays hostless, stays in the top 4, and
pins the window for ever. Sources ranked 5th and lower never get a turn.

Run #33 filed this rather than fixing it, deliberately: the honest fix is to **rotate** (order by
last-attempted, so every source is reached) rather than to raise the number, and choosing how
often a failed source is retried is a cost decision — one model call and one fetch per source per
cycle — that belongs to whoever is paying for it. Hard Rule 0 is explicit that the answer is
never a smaller universe, so **do not simply raise the 4.**

## 4. THE QUEUE, BY RUNG (121 open at close of run #33)

**LOCAL — 64 orders. Work these first, and work them with `local_agent.py`.** This is the whole
point of the rung: they are mechanical and the free model can carry them without spending a
metered token. The shapes are: a comment or docstring that describes behaviour the code no
longer has; a CLI flag parsed and never read; a bare `os.replace` where `silence.replace_retry`
or `silence.write_json` belongs; `silence.note()` tags carrying line numbers that no longer point
at their own call sites; dead functions. **`--no-apply` stages without writing** — use it to read
a batch before letting it land.

**BOTS — 6.** One real quarantine (dandwiki) and the five binding-suspects above. Neither is
work a run closes; both are waiting on §2.

**RUN — 48, of which 2 BLOCKING.** Take the BLOCKING pair first:

* **`local_agent.py` — a failed auto-revert is invisible.** When `propose_patch`'s auto-revert
  itself fails, the resulting `ALARM` reaches nothing reliable: the console print truncates the
  JSON at 110 chars and cuts the `ALARM` key off, the `patches` audit trail records only patch
  *intent* and never outcome, and neither `run()`'s `ok` flag nor the exit code reflect it. **A
  bad, unreviewed write can persist while the run reports success** — in the one lane that lets a
  model write to `src/`. Fix the channel before routing more work to LOCAL in bulk.
* **`escalation.py` — the "cannot be cleared programmatically" guarantee is enforced by a literal
  substring scan** for two exact spellings (`escalation.clear(`, `ESC.clear(`), at `drill.py:727`.
  A different import alias, a `getattr`, or a dynamic call bypasses it undetected. This is a
  verification gap, not a hole in the halt itself — `clear()` still demands a written ruling, and
  the drill still watches it refuse (`drill.py:570,573`). **Do not make the halt more permissive
  while fixing this.**

  **Correction worth carrying:** `CLAUDE.md` states this is *"asserted by `verify_math` to have
  no caller anywhere in `src/`."* It is not — run #33 grepped `verify_math.py` and the assertion
  is not there; the only enforcement is the drill substring scan above. The guarantee is weaker
  than the charter describes it, in both the mechanism and the file. An AST-based check in
  `verify_math` (resolving aliases, `getattr`, and dynamic dispatch) is the fix that would make
  the sentence in `CLAUDE.md` true.

Then the 46 MAJORs. The heaviest cluster is `pipeline.py`, and run #33 read both of batch 02's
top two against source — they are **not** the same standing:

* **`phase_chain` (pipeline.py:1510) — CONFIRMED.** `CH.write_result(edges, res, unmatched)`
  discards its return value and the very next line appends the done-key unconditionally. It does
  not call `gate_done` at all. This is M36's exact shape surviving in the one phase that routes
  through a different writer, and `chain.write_result` does not return a landed/not-landed
  verdict anyway — so fixing it means giving that writer a verdict first.
* **`phase_write` (pipeline.py:1893) — ARGUABLE, treat as a question.** The claim is that
  `gate_done(st, "write", [])` marks the phase done via `all([]) == True` when every source's
  job-build failed. The vacuous-true branch is **deliberate and documented** — M36 explicitly
  left "a phase that correctly wrote nothing is not held open" alone. The real question is
  narrower and worth asking: should `jobs` empty **while `refused` is non-empty** be treated as
  "nothing to do" or as "everything failed"? Those are different, and only the second is a
  fault. Do not patch this as if it were settled.

**One more that run #33 verified and that deserves priority over its MAJOR label:**
`silence.py:133` — `uses_exc = bool(node.name) and node.name in body`, where
`body = ast.dump(node)`. For `except ValueError as e:` the dump contains `name='e'`, so
`'e' in body` is **always true** and the handler is scored "observes its exception" whether or
not `e` is ever used. Every named handler passes; only bare `except:` can be caught. This is the
`swallowed failures` verifier — a battery member — under-reporting the project's own signature
defect, and `allsweep` currently lists it as `findings`, so whatever it *is* reporting is a
subset of the truth. Fix the detector before trusting any count it produced.

## 5. ON THE 116 SWEEP FINDINGS

`handoff/sweep33/` holds all 18 reports and is the full record; every finding is filed, none
dropped. **Four BLOCKING findings were verified against source before filing and all four were
real** — but the remaining 112 are filed **as reported, not as confirmed**. Verify before acting.
Audits are wrong in both directions, and run #33's own batches produced at least two claims that
dissolved on inspection (the `completeness.py` "measured 0 rows" line is `verify_math`'s
deliberate self-test of the shrink floor, not a live fault; `cleanup.py` deletes nothing from the
filesystem at all).

## 6. IF THE QUEUE COMES BACK EMPTY

Run the sweep. Run #33's is `run33`, 109/109 modules, and `sweep_plan.missing('run33')` is empty
— so the completeness proof in `verify_math` is green and will stay green until a module is
added. **A new module in `src/` fails that check by design**, which is how run #33 learned that
`workorders.py`, `policy.py` and `suppressions.py` had never been audited by anything.

---

*Battery at close of run #33: `verify_math` 795 passed / 0 FAILED · `drill` 162 nets, 162 held,
0 BREACHED · `health --preflight` all checks pass · pyflakes clean · secret scanner 0 actionable
(8 findings, all previously waived).*
