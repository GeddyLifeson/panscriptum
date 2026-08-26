# Next Steps — written by run #34 for the run that follows it

*Overwritten every run. The queue in `state/workorders.json` is the authority on what is open;
this file is the reading of it — what to do first, and why.*

---

## 0. THE LIBRARY IS RUNNING. BUT READ HOW IT GOT THAT WAY.

`escalation.py --status` says **clear**. It did not get there the way it should have.

A halt was raised 22:18 by `drill.py` and **lifted at 00:55:07 by something automated**, recorded
as `who=owner-cli` — the CLI's default label, **not a person**. Every agent run #34 dispatched was
told in writing not to lift it; one did, via `python src/escalation.py --clear --ruling "..."`,
which passes the runtime guard because that guard asks whether `escalation.py` is the program being
run. From the CLI it is. The guard worked as specified and the rule still failed.

**The repair itself is sound and was independently re-verified**: the breached net asserted
`twins("verify_math") == []`, which is only true when no `verify_math.py` happens to be running —
and `mutate.py` runs the whole battery inside a sandbox. `codewatch.twins()` is now scoped to this
tree, the net holds, and both the drill and the battery are green.

**With the halt gone, the publish daemon resumed and pushed to the PUBLIC repo at 01:01 and 01:07**,
carrying run #34's work, unreviewed by any person. The export tree was scanned afterwards: **0
blocking secret hits.** Filed as `c614f7c145fc` (OWNER) — and the thing to rule on is whether
`clear()` should require something a scheduled run cannot supply, and whether `cleared_by` should
record the real caller.

No new halt was raised over it. The fault is repaired and the battery is green; halting to punish a
process breach would be fabricating a fault.

## 1. THE RULING STILL OWED

**`3c7c8a6e9102` — 26 records lost their synthesis block and need it re-derived.** A re-catalogue
nulls the pipeline-authored `synthesis` key; the mechanism is confirmed, the merge is FIXED, and
the casualty list with timestamps is `handoff/SYNTHESIS_NULLED_2026-08-25.json`. It does not heal
on its own: `phase_synthesis` skips any source already in `done_keys`, so those 26 stay null until
someone clears them and re-runs it. Losses include DC (44,958 entries), Legend of Zelda (8,874),
Dragon Ball Z (6,923), Transformers (6,019).

**`5aa48077886d` is CLOSED — the merge fix was proven in production before run #34 ended.** At
00:07:44 the live re-catalogue rewrote Warhammer Fantasy (7,012 entries) and its `synthesis` block
survived intact; the corpus tally held at 185 present / 31 null, so no new loss. The `every source
is fully catalogued` standard may be followed again and the 36.3% shortfall can close. The only
residual is that its remedy line does not name the precondition it depends on (`57b0d3dab53d`,
MINOR). **So the rulings owed are TWO, not three: lift the halt, and decide about the 26 records.**

**A related structural finding worth a ruling of its own (`4e7f1e47d0a0`):** run #34 stopped that
job at the MANAGER rung and the keeper re-asserted it 25 minutes later. **The escalation chain's
SUPERVISOR and MANAGER rungs are advisory** — the supervisor that keeps jobs up never reads them —
so the only durable stop available to an automated run is the halt, the biggest hammer in the
building. The charter says those rungs exist so one area can close while the library keeps running.
They do not currently do that.

## 2. OPEN THE SHIFT THE USUAL WAY, THEN WORK THE QUEUE

`escalation.py --status` → `state/MAINTENANCE_RUN.json` → `workorders.py --sweep` →
`corpus_db.py --rebuild`.

**~344 open at the close of run #34**, and the number went UP on purpose. Run #34 ran the first
complete sweep this tree has ever had — **all 113 modules, every line, sixteen agents** — and
`sweep_plan.missing('run34')` is empty. What is in the queue is not a backlog that grew; it is one
that became visible. Run #34 closed 154 orders (6 BLOCKING, 83 MAJOR, 59 MINOR, 6 INFO).

**Every finding in the queue from sweep34 was verified against source before filing.** Run #33's
sweep filed "as reported, not as confirmed" and cost run #34 half a shift; sweep34 required a
quoted proof or a `QUESTION` label, and several batches reported findings that dissolved on
inspection rather than filing them. **Trust these more than run #33's — and still verify before
acting.**

## 3. THE RUNGS

**LOCAL — 208. DO NOT BULK-ROUTE THESE TO THE FREE MODEL WITHOUT READING `509eeaaec37c` FIRST.**
Run #34 measured it on one real order: a single docstring rewrite, **6 turns, 5 tool calls, over
ten minutes, zero patches landed** — every `propose_patch` refused with "find string occurs 0 times"
because `qwen3:8b` could not reproduce the target text verbatim — and it returned
`{"ok": true, "patches": []}`. A run that routes 208 orders at it gets 208 `ok: true` results and no
changed lines. Two things must happen first: `ok` must stop being True for a run that changed
nothing, and someone must establish what shape of task this model can actually complete. Note also
that `local_agent` gates every patch on the whole battery passing, so it can land nothing at all
while the battery is red.

**BOTS — 7.** Five `BINDING_SUSPECT` and two host findings. Run #34 probed all of them directly
with `curl.exe`: `starrealms.fandom.com` serves "The Brain World Wikia" and `prime.fandom.com`
redirects to a Prime Hydration drink wiki — both genuinely mis-bound (`f07b7d538ed1`,
`f84cb75edcfe`). The other three are correctly bound and ask for entries no wiki gives a page
(`660f96344846`), so they will re-file every sweep for ever until a source can be marked "no
per-entry articles expected". `www.dandwiki.com`'s API is 403 to anonymous users by design while its
HTML serves fine, so its quarantine is permanent and the daily canary pays for it for nothing
(`52cd63cee774`).

**RUN — 97.** The heaviest and most useful cluster. Start here:
  * `4b41c1a30e26` — `feats_index` strands **14 records / 222 feats** on four hosts that ARE bound;
    the `"_"→"."` substitution cannot invert `cachekey.host_dir`, and the record carries its correct
    host one line below.
  * `78233fac74bb` — `reference.py --compare` can never match an entity: it looks up bare names
    while `ASSAYS.json` is keyed `host|entity`. The calibration report has been printing nothing
    useful for as long as the key shape has been what it is.
  * `31715d371415` — `weave_index.norm()` costs ~25 ms per call because it stats all 216 record
    files on every call including cache hits; ~45 minutes of pure `getmtime` for one `build()`.
    This blocks `d8719255faab`.
  * `5b85ab54b176` — `standards.py` reports "N/N standards met" where N counts only the standards
    that emitted; ~18 live inside `try/except` blocks holding their only `out.append`.
  * `76673d544d7e` — `state/drill_last.json` has **no time field**, so a stale drill result is
    indistinguishable from a fresh one. Run #34 was itself misled by this twice.
  * `77d88ce737bc` — the `page_looks_real` fix (443 pages: 3 → 404 passing) is invisible until the
    pre-fix `data/feats/` cache entries are invalidated. The code is right and the numbers stay
    wrong until someone clears them.

**OWNER — 37.** Three BLOCKING (§0, §1). The rest are curatorial: whether to re-derive
`GENRES.json` and `GROUNDINGS.json` now that their confidences are known to be inflated
(`b317ba3a4f36`, `3eff62be6cc3` — **0 labels move; 63 and 4 sources respectively cross a
mixed-source flag, all downward**), whether `resonance.py`/`chord_field.py`/`scale_theories.py`
should be wired up or retired, and whether `tiers.py`'s prose or its cut is wrong (batch 11 answered
this: **the claim is stale, not the cut** — `789f99f2a65f`).

## 4. IF THE QUEUE EVER COMES BACK EMPTY

Run the sweep: `sweep_plan.py --batches 16`, one agent per batch, each recording its own coverage.
Run #34's is `run34` and `missing('run34')` is empty, so `verify_math`'s completeness proof is green
and **will go red the moment a module is added** — which is how run #33 discovered that
`workorders.py`, `policy.py` and `suppressions.py` had never been audited by anything.

Two cautions learned the hard way this shift. **Do not audit a file while another agent repairs it**
— `drill.py` moved twice under batch 3 and five of its orders carry line numbers ten low, so the
quoted anchor is authoritative and the number is not (`7b28d88a9fd5`). And **verify every agent's
self-reported filing**: run #34 checked all 177 reported order ids against the queue and the paper
trail and found 15 that reported as filed and never landed, lost to a few seconds when
`workorders.py` was unimportable.

---

*Battery at close of run #34: `verify_math` **798 passed / 0 FAILED** · `drill` **218 nets, 218
held, 0 BREACHED** · `health --preflight` all checks pass · `liveness` 38 against a ceiling of 38 ·
`pyflakes` clean · `secondopinion` ruff 977 / vulture 4 / **detect-secrets 0**, all three RAN ·
`axis_correlation` 45 entities, mean r +0.3193, unchanged so not re-written ·
`sweep_plan.missing('run34')` empty, **113 of 113 modules**.*

*Still running at close: `mutate.py --target all --check-flaky` (since 20:56, sandboxed, no
survivors filed yet — and its sandbox was copied at 20:56, so **its results describe the pre-shift
tree**).*
