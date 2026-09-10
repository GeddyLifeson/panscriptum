# Next Steps — the priority queue for the next maintenance run

*Overwritten each run. The permanent record is `HANDOFF.md`; the live queue is
`state/workorders.json` via `python src/workorders.py --sweep`.*

Written by run #54 (daily), 2026-09-10. **Every gate a run can be responsible for is at absolute
zero, the sweep is COMPLETE, and the queue is bigger than it was — because the sweep did its job.**

    drill              479 nets / 479 held / 0 BREACHED
    verify_math        1283 passed / 0 FAILED
    pyflakes           clean over src/
    secondopinion      all three tools RAN, 0 secrets by two independent scanners
    liveness           49 findings, 0 tautology, 0 phantom
    axis_correlation   45 entities, matches the stored n_entities, no --write owed
    escalation         clear
    sweep run54        16 batches, all 118 modules, `missing()` = []
    queue at close     59 open — RUN 27 · OWNER 22 · LOCAL 7 · SESSION 2 · BOTS 1

**TWO ALLSWEEP VERIFIERS ARE RED AND NEITHER IS CODE.** Do not spend a shift on them:

* `preflight` — **dandwiki.com is not answering its API**. Standing BOTS order `2da53c3e192f`,
  an external host, red for days.
* `cascade live call` — **every cloud failover rate limited** (Gemini 3.1 Flash-Lite, DeepSeek V3
  (SambaNova), GLM 4.7 Flash (Z.AI)). 42 models configured, 30 provider-ready, free tiers spent.
  **This was GREEN earlier in the same shift**, so it is a quota condition, not a regression — the
  crawl runs continuously and `local_agent` spent ~90 minutes on the pool. Belongs to
  `9fb8a6b10c1f` and `88982cef258d`; **re-measure before concluding anything from it.**

---

## 0. FIVE THINGS BEFORE ANYTHING ELSE

**1. DO NOT RE-DIAGNOSE THE 2026-09-09 HALT.** It was raised at 23:23:46 and **lifted by run #53
at 23:42:01**, as the shift that caused it, with a full ruling in `state/HALT.json`. Cause:
run #53's own net `_scope_lands_key_wise` drove `scope.mutate`'s two `silence.note` refusals into
the live failure ledger. Run #54 spent real budget re-deriving that from the other end because the
evidence had been deleted; the fix for that is landed (`2cf4993b3a3f`) and the next breach will
name its own site. **Read `HALT.json`'s `ruling` field before forming any theory about it.**

**2. TWO MAINTENANCE RUNS WERE LIVE IN ONE TREE ON 2026-09-09, AND THE GUARD SAID NOBODY WAS.**
Order `99d752c5632f`. `state/MAINTENANCE_RUN.json` records `started` and `heartbeat` once,
together, and never again — so a shift that works for two hours becomes invisible after fifteen
minutes, and the *longer* it works the more certainly the next run walks in on it. Nothing was
lost this time. **If you are about to start a long shift, refresh that heartbeat as you go**, and
read the order's remedy (record the PID, the way `mutate`'s lock already does) before trusting the
file.

**3. CHECK `codewatch`'S NEW POLL COLUMN FIRST — IT IS A LIVE MEASUREMENT AS OF TODAY.**
`python src/codewatch.py` now prints "last polled Ns ago" beside each covered job. Every job read
**"last poll NOT KNOWN"** at run #54's close, which was honest: all seven daemons predate the
code. **A job still reading NOT KNOWN is a job that has not reached `exit_if_stale` in a day** —
which is the fault order `b67c5d98c91f` was filed about, now visible instead of inferred. This is
the cheapest real reading available to you and it takes one command.

**4. PUBLISH BEFORE YOU LAUNCH THE MUTATION PASS — THE INSTRUCTIONS AS WRITTEN CANNOT BOTH BE
FOLLOWED.** `publish.py` refuses while `mutate.active()` is True, correctly and with a drill net
enforcing it, so a pass launched per §3b blocks this shift's own §5 push **for the next twenty
hours**. Run #54 walked into this: launched the pass, realised it had blocked its own push,
stopped the 90-second-old pass, published, and relaunched it. Filed as `e4caaebcbe18` — and note
the lock is now over-blocking on its own terms, because a sandboxed pass never corrupts the live
tree and `active()` does not look at the `sandboxed: true` its own record carries.

**5. THE MUTATION PASS WAS LAUNCHED DETACHED as run #54's last act** (`--target all
--file-orders --detach`), the first pass to use run #53's `--detach`. Its log is
`state/mutate_20260910.log`. **Read it before doing anything else expensive**: if it finished, its
survivors are filed as work orders and each has to be READ, not assumed — some mutations are
genuinely equivalent and which it is cannot be guessed. If it died again, say so plainly and put
the evidence in `d2d4ff880570`; four passes in a row have now failed, and the fifth failing
differently is information.

---

## 1. THE RUN RUNG — WHAT IS ACTUALLY CLOSEABLE

Ranked by value per hour, not by severity.

1. **`f5b8e4afb558` — no non-fandom source can ever be the primary for a shared host.**
   `completeness.subdomain()` returns `None` for anything not `*.fandom.com`, so `primary[h]` is
   never assigned and all 32 sources sharing `en.wikipedia.org` (28) or `www.dandwiki.com` (4) are
   permanently marked unreliable. **Latent only because `en.wikipedia.org` is currently recorded
   unreachable.** Remedy (a) — make the message say the discriminator does not apply to a
   non-fandom host, instead of implying a primary exists — is reporting-only, changes no
   aggregate, and should just be done. Remedy (b) is a ruling; leave it.
2. **`156c2e28f823` — four conditions that cannot be false**, and the first is in `drill.py`
   itself: `_sandbox_without_its_target_refuses`'s sandbox-litter clause is unfalsifiable (batch
   01 proved it by deleting `mutate.py`'s cleanup and watching the net stay GREEN). A clause that
   reads as coverage and provides none, in the file whose own doctrine is that a safety nobody has
   watched refuse is not evidence. The other three are small.
3. **`386c0d66e31e` — the stale-citation class, third sweep running.** Do NOT spend the shift
   renumbering: **build the cheap detector** in its remedy (b). Flag any `file.py:NNN` whose target
   file is missing, whose N is past end-of-file, or which lands on a blank line or a bare closing
   bracket. Two of this sweep's confirmed sites would have been caught by that alone, and under
   such a floor the class stops growing between sweeps instead of being re-harvested by each one.
   Read it beside `89503c58409f` and `dc9ffadae765`.
4. **`400d5c76e6f8` — about twenty unwrapped `silence.note` sites in `drill.py`**, now enumerated
   by batch 01. Triggers include *no psutil*, *no `cmd` on the machine*, an absent
   `~/cascade/config.json`, and an AV scanner holding a probe file — any of which halts the
   library at OWNER rung. **This is a ruling as much as a repair**: `_deliberately_failing`
   suppresses, `_not_a_leak` declares and its own docstring restricts it to one probe, and an
   *abstention* note is arguably real information about the machine. Decide the rule first, then
   apply it twenty times.
5. **`3fc19ad4d1c6` — five silent-failure sites**, four of which are one-line and safe
   (`onomast.py`, `coverage.py`, `publish._scrub`, `secondopinion._exe`). The fifth,
   `weave.filtered_index()` failing OPEN on an import error, is the fail-open/fail-closed
   question and should be asked rather than patched.
6. **`d1709d8e757d` — nothing schedules the entity-index rebuild.** Run #54 rebuilt it by hand
   (00:00, 178.0 MB, after `allsweep` reported it 30.1h stale with 37 records newer). **Read
   `2cb442afd901` first** — the trigger threshold is the owner's open question, and picking one
   autonomously would be answering it by writing it into a roster.

**Already carrying a dated reason and deliberately still open:** `a66423722e45` (its remedy as
written would red the battery), `c9146abf92df` (blocked on `b3da16ddfe64`), `58a00e909217`,
`79d51aef8b71`, `30854f11f322`, `e8675703f045`, `e727ab804c5b`, `e114b2d0fe48`, `d9328fe1ee38`,
`5d0fa30e4b09`, `215f9e7b86ff`, `dc9ffadae765`.

---

## 2. THE LOCAL RUNG — AND AN HONEST ACCOUNT OF IT

`abc943bb6464` (two Hard Rule 0 undisclosed cuts: `repass_bands.py`'s three 70-character slices,
and `workorders.WHERE_TARGET` dropping the end of a cited line range) was routed to `local_agent`
**twice, and landed nothing both times.** Recorded as attempted-and-not-landed, which is what the
agent's own verdict says: *"This run changed nothing; do not record it as work done."*

**BOTH FAILURES WERE MINE, NOT THE MODEL'S, AND THE SECOND ONE IS WORTH ONE LINE OF YOUR TIME.**

* **Attempt 1** (task described the sites in prose): five patches proposed, all refused by
  `find string occurs N times; it must occur exactly once`. A task naming a symbol and a line is
  not enough — the gate wants the line quoted.
* **Attempt 2** (task quoted the three substitutions verbatim, and asked for a `_marked()` helper
  to be inserted "immediately above the line that reads `def main():`"): **every single proposal
  was the helper insertion with `find` set to `"    def main():"` — four leading spaces.**
  `repass_bands.py` has `def main():` at column 0. It never reached the three substitutions, and
  burned ~45 minutes of GPU retrying the same indented anchor.

**So: when you hand this to LOCAL, give it the anchor exactly as it appears in the file, column
zero and all — or, better, drop the helper insertion entirely and have it do only the three
one-line substitutions against a helper you have already put in the file yourself.** The three
substitutions were never attempted and are trivially unique strings.

**The LOCAL lane is open again** now the battery is at absolute zero. It was closed for as long as
`whoruns.py` sat unswept, because `local_agent._gates` requires `verify_math` clean before any
patch may land — see `de265a105279`, whose owner half is exactly that trade.

---

## 3. FOR THE OWNER

1. **`55d0be76b99b` — NEW, and the largest.** 133 of 210 sources carry a ceiling entity with no
   band, in a state nothing re-visits: `SYNTH_SYSTEM`'s hard rule 3 says the ceiling and the
   magnitude go empty together, `phase_synthesis` enforces only the magnitude half, `todo` keys on
   the ceiling alone, and the `unassayable` block is guarded by `if not _ceiling` so it has
   recorded nothing for anybody. Three answers offered; run #54's reading is (b), widening `todo`
   so an unbanded source is re-asked as the cast grows — no nomination lost.
2. **`99d752c5632f` — the maintenance guard.** See §0.2.
3. **`de265a105279` — should an `added_since` gap fail a Hard-Rule−1 safety?** The row now SAYS
   which of three things happened (fixed this shift, nothing weakened). What stands is the trade:
   it closes the free LOCAL lane for as long as a new module is unswept.
4. **`5bb12b398783` — five questions from the sweep**, each verified and unchanged: the prose gate
   treating "the drill did not run" as "the drill was clean"; `scope.TIERS` having no marker for
   M0/M5/M9/M10; `custodes`' `prior_share = 1.0` default; whether the `_BAD_CHARS` eaten-escape
   self-check belongs on every regex-heavy module; and whether `navtree.py`/`rosetta.py` should be
   asking `escalation.assert_clear()` before writing into `data/`.
5. **`2cb442afd901`** — what fraction of the corpus moving makes the entity index stale. Blocks
   §1.6.
6. **`c9666b0bd8d9`**, **`f19f4a2b00f4`**, **`88982cef258d`**, **`f7d7769075c0`**,
   **`50e8d8be9a9b`**, **`b186bc4dad8f`**, and the four wiki-binding pairs — unchanged, each with
   a dated reason.
7. **Phase 4.3's shelf mapping is still drafted and unsigned**:
   `handoff/phase43/SHELF_MAPPING_PROPOSAL.md`. Nothing is written to the spine and nothing should
   be. **4.5 remains unauthorised and `prose_enabled` is untouched.**

---

## 4. THE SWEEP'S OWN OUTPUT

`handoff/sweep54/AUDIT_batch01.md` … `AUDIT_batch16.md`, one per batch, each recording what was
checked as well as what was found — including the modules that came back clean and why that is a
reading rather than a shrug. The brief the batches worked to is `handoff/sweep54/BRIEF.md`; it is
reusable and worth reusing.

**Two things the batches flagged that no order carries**, because they are about the sweep rather
than the library: batch 11 disclosed that running `reference.py` to verify its calibration WROTE
`data/REFERENCE_ASSAYS.json` during a nominally read-only audit (deterministic content, but the
next brief should say *do not execute a module that writes into `data/`*), and batch 06 named two
citations it could not check because their targets lay outside its own batch — a real limit of
per-batch verification, and an argument for the detector in §1.3.
