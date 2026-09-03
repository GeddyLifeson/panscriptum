# NEXT STEPS — written by the scheduled maintenance run of 2026-09-02 for the run that follows it

Overwritten every run, on purpose. The queue in `state/workorders.json` is the memory; this file
is only the ordering.

---

## 0. READ THIS FIRST

**A halt was raised and lifted during the 2026-09-02 shift. It was self-caused and it is closed.**
`DRILL_BREACH`, from deliberately reverting `local_agent.py` to watch a new net go red. Cause
fixed, drill 386/386 and battery 1130/0 proven before lifting, ruling written into
`state/HALT.json`. **Nothing to chase.** Full account at the top of `HANDOFF.md`.

**FIRST ACTION OF YOUR SHIFT: read `state/mutate_2026-09-02.log` and report the survivor count.**
The mutation pass was launched **four times** and produced **0 of 146 mutations**, refusing
correctly each time. Three of those refusals were environmental; one was my own net misfiring in
the sandbox, which is fixed. If the final post-shift launch also refused, say so plainly — a
pass that did not run is not a pass with zero survivors.

**Do not re-diagnose these three. They are measured, filed, and are not bugs to chase:**
- The cloud pool is **out of free-tier quota** (`groq:qwen/qwen3.6-27b` at 198,972/200,000 tokens
  per day; four other providers rate-limited). `allsweep`'s `cascade live call` row is red for
  this reason. Remedy is money or waiting; the standing answer to money is no.
- The **`LOCAL` rung is starved** — Ollama answers `maximum pending requests exceeded` while the
  model sits resident, because the library's own daemons saturate the single GPU lane. A trivial
  `local_agent` task ran >15 min and wrote nothing. **128 open orders are addressed to LOCAL and
  are effectively parked.**
- **`verify_math` §20z is flaky** and its flakiness is what keeps cancelling the mutation pass.
  Several of its probes make live cascade calls; a throttled provider turns the row red. Measured
  green → red → green on an unchanged tree.

---

## 1. THE HIGHEST-VALUE THING YOU CAN DO (order M66 / `VERIFY_MATH_S20Z_DEPENDS_ON_LIVE_NETWORK`)

**Make §20z independent of the network, and the mandated mutation pass starts working again.**
This one fix unblocks the single largest piece of standing work the schedule asks for. Either
exclude the live-call probes from the 20z scan by construction, or attribute the ledger write to
the probe rather than to `cascade_bridge` — so a genuine fault is still caught while a provider
throttle is not counted as one. It touches the battery's own semantics, which is why this shift
filed it rather than changing it at the end of a long run.

## 2. THEN GIVE BEHAVIOURAL NETS A SCRATCH TREE (order M68)

Adding a guard currently obliges you to halt the library to prove it works, because only
source-shape nets have `_SRC_OVERRIDE`. A throwaway harness that does this properly was written
ad hoc during this shift and proved the new net in three worlds; make it a permanent part of
`drill.py`. **Standing lesson meanwhile: exercise every new net inside `mutate`'s sandbox as well
as on the live tree** — `data/` is junctioned outward there, so a different gate refuses first,
and a net red in the baseline is *disabled as a detector for the whole mutation run*.

## 3. THE ONE-LIMB FIX INSIDE THE LOCAL-RUNG PROBLEM (order M67)

The scheduling question is the owner's, but this half is not: **`local_agent` should refuse
loudly and immediately when Ollama reports a saturated queue**, instead of burning fifteen
minutes and exiting 0. A handler that cannot handle should not report success.

## 4. WORK THE QUEUE — 373 open (LOCAL 128 · BOTS 23 · RUN 47 · SESSION 60 · OWNER 115)

Sweep 42 filed 48 new orders, every one carrying its file, line and reasoning. **40 were closed
this shift.** The RUN rung is where your leverage is; LOCAL is parked until item 3 or the GPU
frees up. Two standing cautions, both learned the hard way this shift:

- **Verify every finding against source before acting. Audits are wrong in both directions.**
  Two of the closures would have caused damage if applied literally: gating `health --reopen` on
  its return value would have **failed every clean run** (`[]` meant three different things), and
  uncapping `backfill`'s `sample` would have **taken the battery red**, because `verify_math`
  asserts against it as a *post-ranking head*.
- **Write ledger edits through a script that asserts what must stay true.** Hand-editing `BUGS.md`
  this shift produced a duplicate bug number and a RESOLVED entry in the Open section; only the
  script's assertions caught either.

## 5. STANDING, UNCHANGED FROM RUN #41

- **GitHub push is DEFERRED by the owner** ("ignore github for now"). The export commits locally;
  the push reads HELD. Not a fault to chase, not yours to fix autonomously.
- **Do not widen `state/ledger_chain_acknowledged.json`.** A second record needs a person, an
  order id and a reason.
- `c614f7c145fc` (the 2026-08-26 automated halt-lift) still wants an owner ruling.

## 6. QUESTIONS WAITING ON A PERSON, NOT ON A RUN

- `cascade_bridge` re-dispatches to a bucket that just said *"retry in 499s"* and then gives up
  instead of failing over. The non-benching is **documented as deliberate**, so it is a ruling.
  Three options are set out in the order; nothing was changed. Note that the case observed was a
  **per-day quota exhaustion**, which `named_transient()` treats as a momentary throttle.
- `scale_theories.py`'s five dead constants: verified dead, **deliberately not deleted** —
  deletions need a review cycle, the module is itself never reached, and `descending_ladder.py:49`
  cross-references them. Re-rated LOCAL → OWNER.
- `assay.py`'s `ATTESTATION_FLOOR` has no monotonicity or ceiling guard while its sibling table is
  protected at import. These tables sit inside every published ± in the library.
