# Next Steps — the priority queue for the next maintenance run

*Overwritten each run. The permanent record is `HANDOFF.md`; the live queue is
`state/workorders.json` via `python src/workorders.py --sweep`.*

Written by run #48, 2026-09-08 (daily). **Queue at close: 65 open** (RUN 30 · OWNER 19 · BOTS 9 ·
LOCAL 5 · SESSION 2), up from **47** at open. 17 filed, 5 closed. **The queue grew because 117
modules were read in full and that is what reading them produced** — the smaller number would have
been bought by not looking.

**Gates GREEN, measured before the mutation pass took its baseline and unchanged since (no `src/`
edit after it):** `verify_math` **1278 passed / 0 FAILED**, `drill` **464 nets / 464 held / 0
BREACHED**, `pyflakes` clean over `src/`, `health --preflight` all pass, `secondopinion` all three
tools installed and **0 secrets** from two independent scanners, `escalation --status` clear.
`axis_correlation` 45 entities / mean r +0.3193 — identical to the stored matrix, **no `--write`
owed**.

---

## 0. DO THESE THREE THINGS FIRST, IN THIS ORDER

**1. READ `state/mutate_20260908.log`.** The pass was launched 22:57 on all three targets and was
still running at close. **There is no survivor count and this run does not have one.** A pass that
was killed halfway is not a pass with fewer survivors — if it died, say so and relaunch; if it
finished, the survivors are the most valuable thing on this page.

**2. WORK THE RUN RUNG BEFORE LAUNCHING ANYTHING LONG.** This is the sequencing lesson of run #48 and
it cost the whole shift's RUN work — see §1.

**3. Check `state/HALT.json` before anything else if the library looks down.** (Standing advice from
run #46b; still the right first move.)

---

## 1. THE SEQUENCING CONFLICT — A ONE-LINE OWNER RULING WOULD SETTLE IT

§3b says launch the mutation pass early, *before* §4, because it runs for hours. Editing `src/`
during a pass is the confirmed cause of the baseline drift that killed three previous passes
(`79d51aef8b71`, `f40f701594a4`). **Together those mean that from the moment mutation launches, no
RUN-rung code order can be worked for the rest of the shift.** §2 says drain the queue until empty;
§3b guarantees it cannot be.

Run #48 launched at 22:57 and froze its own main rung for the remainder. **The mistake was mine** —
§2 comes before §3 and §3b in the file's own ordering, and I should have drained RUN first — but the
file's literal words ("as soon as the battery is green and BEFORE you start §4") point the other way,
and a shift that follows them literally will make the same mistake.

**Until a ruling: drain the RUN rung first, launch mutation last.** The pass runs unattended either
way; nothing about it needs the shift to still be awake.

---

## 2. THE RUN RUNG — TWELVE ORDERS, ALL VERIFIED, ALL READY TO EDIT

Every one was re-verified against live source by run #48. **These need editing, not investigating.**
Highest value first, in my reading:

1. **`3f6bc55e526f` — a rung-4 stop can be lifted with no person, by choosing the subsystem's name.**
   `_a_probe_release` decides "is this a drill probe?" with an **unanchored** `re.search` borrowed
   from the failure ledger, so `payments__drill_x__` and `nightly-publish__drilled__` both win the
   exemption and skip `_by_a_person_at_the_cli()`. Not exploited today (no production caller of
   `stop_subsystem`), filed on the shape. Fix by **equality** against the three reserved names.
   **Watch it refuse in both directions** — a fix that refuses everything breaks drill's own cleanup.
2. **`71a9b380cb03` — `feats.py:698`'s http-404 exemption is unreachable.** A 404 sets `ok=False`,
   so `fetch()` increments `failed`, so `bool(tr.get("failed"))` short-circuits True and the
   allowlist naming "http-404" is never evaluated. Every genuinely-absent entity is re-mined for
   ever, against the hosts already at 8x–32x backoff. **LAND THIS ONE FIRST**: `1d55458779fd` and
   `86b8dd723f90` both depend on what counts as a clean negative, and will inherit this boundary if
   it is still wrong. Note the complication in the order: `why` records only the FIRST non-ok reason,
   so a mixed 404+throttled batch needs more than a reordered `or`.
3. **`d8c888dd28c2` and `6e0047258461` — the two remaining process-probe faults.** `-c` false-
   *positives* in `_cmd_is_running` (a daemon then refuses to start — the silent direction), and
   `allsweep`'s probe has no tri-state. Both fixes already exist elsewhere in the tree
   (`codewatch.runs_script`, `overnight._proc_lines`). **Consider making `overnight._cmd_is_running`
   and `codewatch.runs_script` one implementation** — they are provably two copies of one rule that
   disagree, and this is the fourth time that family has drifted.
4. **`87d2ef35a516` — `health.reopen_stranded` blind-writes PIPELINE_STATE.json.** Reads once, lands
   the whole document, no compare-and-swap, while its own docstring says it runs when a pipeline may
   be live. The comment directly above the write is entirely about two concurrent writers: the
   torn-file half was fixed, the lost-update half was not. Same shape as `c9146abf92df`;
   `roll.mutate` is the pattern.
5. **`9e884802918e`, `194dc5f6d24f`, `72e33d06d4eb`** — a dead boolean (`(A or B) and B` ≡ `B`), a
   HIGH standard that latches true after the first chunk, and a tie-break comparing `strftime`
   against `time.time()`. All three are small, all three are verified.
6. **`acea8b00848e`** — `ingest_doc.py` writes both unreconstructible files with **zero** escalation
   references and **zero** drill coverage. The fix is a transcription of what `hostcheck.py` already
   has (order `77950336e3aa`: `_assert_not_halted`, the `_INTERLOCKED` list, a net at
   `drill.py:8531-8595`).
7. **`5448a236b884`, `1d55458779fd`, `86b8dd723f90`** — the unparseable-reply gap, `coverage.py`'s
   documented-but-unproducible UNREACHABLE state, and `binding_health`'s throttle/absence conflation.

**Then the gathered ones:** `89503c58409f` (50 rotted citations across 33 modules — mechanical, but a
symbol must be chosen per site) and `215f9e7b86ff` (unmarked cuts; each site's marking helper already
exists in its own file).

---

## 3. STILL OPEN ON PURPOSE — READ THE SHIFT NOTES BEFORE TOUCHING

* **`a66423722e45` — ITS REMEDY AS WRITTEN WOULD RED THE BATTERY.** It says to move 28 scripts out of
  `handoff/`. **Twelve are load-bearing:** `verify_math` §20u *executes* the six
  `handoff/run35/checks_L*.py` in their own namespaces and asserts all six are still on disk ("a
  vanished file is coverage that silently left"), and six more sit in a checked register under
  `28c1f58f5e8a`. Only the ten under `nets_20260906/` are real scratch, and one of those is the
  staged net `2f07cbd3241d` is owed. Corrected note attached this shift.
* **`c9146abf92df`** — the `roll.exclude()` lost-update door. **Blocker re-verified as current, not
  stale:** `checks_L4.py` pins the literal call text and §20u does execute it. `b3da16ddfe64`
  (restate that assertion as a property) is the genuine prerequisite.
* **`d1709d8e757d`** — text says 235.2h stale / 210 of 216 modified; **measured today: 5.3h, 1 of
  216**. The predecessor rebuilt it. Stays open because *nothing schedules a rebuild* — still true.
  Prerequisite nobody names: promoting a job into `overnight.STANDING` needs a `codewatch.stamp` and
  `exit_if_stale` first, or `drill_codewatch` breaches silently.
* **`f646c1c5f1d0`** — `genre.py:253` cites this id by name; closing it orphans the citation.
* **`30854f11f322`** — any threshold change flips three legitimately CONFIRMED hosts to false
  negatives.
* **`a724ec57e0d5`** — declined by four shifts now, each with a dated note. Do not decide it
  unilaterally on the fifth.
* **`5d0fa30e4b09`** — twelve QUESTIONS from sweep 48, gathered deliberately. Two are load-bearing:
  `codewatch.fingerprint()` does not descend into `src/deprecated/` (nil consequence *today*, but it
  is what every rc=17 decision rests on), and line-based mutation attribution into a docstring-heavy
  file remaps silently after any edit — which bears directly on reading the current pass's results.

---

## 4. FOR THE OWNER — SIX THINGS ONLY A PERSON CAN DECIDE

Unchanged from run #46b unless noted:

1. **`c9666b0bd8d9`** — two hosts mined the wrong universe into the catalogue and it is still on
   disk (`starrealms.fandom.com` serves *The Brain World Wikia*, 52,443 chars; `prime.fandom.com`
   serves the Prime Hydration drink wiki). Both quarantined. **Purge, mark contaminated in place, or
   leave the quarantine as the only guard?**
2. **`50e8d8be9a9b`** — what range may a Hand's reading take? `400.0` still publishes and both the
   battery and the drill assert that it does, so a ruling arrives as a red row rather than silence.
3. **`c39a2c0e1bef`** — the T3 shelf concordance mapping needs an owner-authored table; it cannot be
   inferred without becoming resemblance-matching, which §6 forbids.
4. **`f7d7769075c0`** — should a designed rc=17 restart raise an owner-visible order? Four fired this
   shift, all within budget, all the safety working. **Run #48 closed those four instances** (the
   restarts completed and were verified from the process table) **without touching the policy** — the
   instance is finished, the question is not.
5. **`88982cef258d`** — two free-tier API keys need re-issuing; `58a00e909217` is blocked behind it.
6. **NEW — the sequencing conflict in §1.** One line settles whether mutation launches first or last.

---

## 5. HOUSEKEEPING VERIFIED AT CLOSE

`escalation --status` clear. Supervisor, dashboard, publish, foreman, overwatch, read and the crawl
all alive; `autostart.py` alive since 2026-08-31 **and now correctly reported as such**.

* **`pipeline.py --run` (pid 21384) was still on 18:05 code at close** and was deliberately not
  killed — mid-phase, doing real work, and an rc=17 there costs the phase. It bounces at its next
  phase boundary. What is filed (`b67c5d98c91f`) is that nobody would have known.
* **The crawl is not stalled** whatever `roll_auto` says: 276,911 feats files, one written 1.1 min
  before close. Six hosts are in throttle backoff (marvel 32x, onepiece 13x, four at 8x); those BOTS
  orders resolve themselves as the hosts recover.
* **No probe litter.** `handoff/` holds exactly the same 28 executable-suffix files it held at open —
  the sixteen sweep agents wrote only `.md` audits under `handoff/sweep48/`, everything else to the
  session scratchpad.
* **`state/MAINTENANCE_RUN.json` is deliberately NOT ticked by a background thread.** Run #46b's
  heartbeat froze the moment its agent stopped, and that is exactly what let run #48 detect the death
  correctly instead of waiting on a corpse. Keep it stamped inline.
