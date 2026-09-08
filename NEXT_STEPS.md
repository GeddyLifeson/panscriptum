# Next Steps — the priority queue for the next maintenance run

*Overwritten each run. The permanent record is `HANDOFF.md`; the live queue is
`state/workorders.json` via `python src/workorders.py --sweep`.*

Written by run #46b, 2026-09-08 (continued). **Queue at close: 45 open** (OWNER 19 · RUN 12 ·
BOTS 11 · SESSION 3 · LOCAL 1), down from **182** at open. Twenty-two owner rulings were executed
across 137 orders by eight agents on disjoint module sets.

**Gates GREEN on a settled tree:** `verify_math` **1272 passed / 0 FAILED**, `drill` **457 nets /
457 held / 0 BREACHED**, `pyflakes` clean, no probe litter (ledger baselined before the fan-out
and diffed after; the only new class is the legitimate record of halt #3, and the six that grew
are the live `read.py`/`feats.py` daemons mining).

**TWO HALTS WERE RAISED AND LIFTED**, both by this shift, both on the same defect class, and both
reported to the owner in the same turn. See §1 — the class is now closed by a standing check, but
the two blind spots it does *not* cover are filed.

**THE LIBRARY WAS DOWN FROM ~12:35 TO 18:02, AND THE CHAIN WAS RIGHT.** `overnight.py` calls
`assert_clear()` before cycle 1, so with a halt standing the supervisor refused to start — hourly,
all day — and `autostart --watch` correctly declined to respawn past its budget, saying each hour
that this *"is deeper than a crash and needs a person"*. `dashboard`, `pipeline` and `publish` were
down for the same reason. Lifting the halt was the cure; the supervisor came back on the first
attempt and is on cycle 1 as of 18:02:58. **If you find the library down, check `state/HALT.json`
before you check anything else.**

---

## 0. THE FIVE THINGS ONLY THE OWNER CAN DECIDE

These are blocked on a judgment call, not on work. Each is one question.

1. **`c9666b0bd8d9` — two hosts mined the wrong universe into the catalogue, and it is still on
   disk.** `starrealms.fandom.com` serves *The Brain World Wikia*: 68 cached feats files, 56
   carrying text, **52,443 characters** filed under Star Realms. `prime.fandom.com` serves the
   **Prime Hydration drink** wiki; its one text-bearing file is `Logan_Paul_Person_.json`. Both are
   now **quarantined**, which stops further mining and touches nothing already cached. In both
   cases the catalogued entry *names* are genuine and only the host is wrong. **Purge, mark
   contaminated in place, or leave the quarantine as the only guard?** Rebinding does not help
   either one — the correct Prime host holds no article for any catalogued item, and Star Realms
   appears to have no fandom wiki at all.
2. **`50e8d8be9a9b` — what range may a Hand's reading take?** Nothing in the charter is quoted
   anywhere in this tree as fixing `[0, 11)`. Deciding it inside the engine would be decreeing a
   charter rule, so it was left alone: `400.0` still publishes, and **both the battery and the
   drill assert that it does**, so whatever you rule arrives as a red row rather than as silence.
3. **`c39a2c0e1bef` — the T3 shelf concordance mapping.** Phase 4.3 measured that 0 of 31 shelf
   names in the Chronicle's Concordance table resolve to catalogued sources, and only 3 of 11
   named candidates resolve to catalogued entities. The rich leg of the Chronicle join needs an
   owner-authored mapping; it cannot be inferred without becoming resemblance-matching, which
   §6 forbids.
4. **`f7d7769075c0` — should a designed restart raise an owner-visible order?** Three were open at
   once this shift, all recording one restart in the hour, all well inside budget, all of them the
   safety working. CLAUDE.md's own words are that an alarm which always sounds is furniture. But
   raising the bar on what a safety reports **is a change to a safety**, and the shift that finds
   an alarm inconvenient is the worst possible author of the rule that quiets it — so it is filed,
   not adjusted.
5. **`88982cef258d` — two free-tier API keys need re-issuing.** The cloud lane cannot be exercised
   until then, and `58a00e909217` is blocked behind it.

---

## 1. THE DEFECT CLASS THAT RAISED BOTH HALTS — CLOSED, WITH TWO KNOWN BLIND SPOTS

A drill net proves things by replacing a real function with a stub. The stub pins a signature.
When the real function grows a parameter, the stub does not, and **the net breaches on the fix**.
That is worse than failing: it punishes correct work and teaches whoever hits it that the net is
noise.

`verify_math` **§20ae** now measures every stand-in in `drill.py` on **arity** — 94 sites, 0
unresolvable, 0 mismatches — with two controls. **It does not cover two things**, both filed as
`e727ab804c5b`:

* **The inverse fault.** A stub *wider* than its subject accepts a call the real function would
  reject, so the net passes while testing a call that can never happen. Nothing ever fires.
* **Stubs not installed as a direct attribute assignment** on an imported module alias — via
  `setattr`, a context manager, or a dict of patches. All 94 sites today are written the plain
  way, but invisible is exactly what this project's worst findings have looked like.

**`b9044b16c8e9` is the other one to take seriously:** `os.kill(pid, 0)` reported two live,
actively-working processes as gone on this machine. It nearly closed an order on the finding that
two jobs were dead while they were advancing. Every liveness probe in `src/` needs auditing for
this, and the extent is unknown because it was found by being wrong rather than by looking.

---

## 2. THE MUTATION PASS — RELAUNCHABLE NOW, FOR THE FIRST TIME

Two **independent** causes killed the earlier passes, and both are fixed:

* A live sandbox **ages into reapability while in use** — both passes reached target 3 at ~12.3h
  against `ORPHAN_AGE_SECONDS` of 6h, because writing into `root/src/` does not refresh `root`'s
  mtime.
* **`mutate.sandbox()` junctioned all of `data/` as one unit**, so gates inside a sandbox read the
  live, continuously-rewritten corpus — the mechanism behind seven baseline drifts and the one
  confirmed false kill at `escalation.py:409`. Now hardlinks top-level files, with the freeze
  proven against the project's own atomic writer rather than assumed.

Fixing either alone would have left the passes dying. `escalation.py` has still never received a
mutation result; that is what the next pass is for. **`58a00e909217` stays open** until a real run
confirms `escalation.py:409` reports SURVIVED under a non-drifting sandbox — it was not closed on
reasoning, because reasoning is what put a false kill there in the first place.

---

## 3. CROSS-FILE DEBTS, READY TO APPLY

Each was refused on purpose by an agent that owned only one side of it. All are specified.

1. **`drill.py`** — a net asserting `category` and `topic` stay independently derived (no path
   collapses topic to match category). Owner ruling 10(a), cited at `pipeline.py:144-152`, flagged
   there as NOT yet written and confirmed absent by grep.
2. **`anchors.py:41`** — one line: `NON_ENERGETIC_AXES = A.NON_ENERGETIC_AXES`. Until it lands,
   `verify_math` holds the two dicts equal and reds if either moves; **delete that row when this
   lands**, or it becomes a check that cannot fail.
3. **`feats.py`** (~line 50) — reads `WIKI_HOSTS.json` directly for one primary host instead of
   calling `hosts.hosts_for(source)`. This is what would make `hosts.py` actually wired, and what
   the corrected comments in `descending_ladder.py` and `scale_theories.py` now point at.
   Behavioural: one host becomes potentially several.
4. **`coverage.py:177-179`** — needs its fourth state, and **the fault changed shape**: a wholly
   blocked entity now reads **NO PAGE** ("the wiki has no article under this name") instead of
   READ. That is a positive false claim about the wiki, which is worse than the silent version it
   replaced.
5. **`src/workorders.py`** — enforce a symbol convention at filing time. The queue's own line-number
   citations have drifted **again** since they were corrected on 2026-08-30 (`SCAN_MODULES`
   543→596, `scan_constants` 617→678); of the 9 citations strict enough to resolve, **9 are stale
   and 0 resolve**. Note the loose-symbol version cannot become a battery row — it would be
   weather, reddening whenever another run files an order.
6. **`handoff/run35/checks_L4.py`** (`b3da16ddfe64`) — reads `roll.py`'s whole source **with no
   comment stripping**, so a refactor could keep it green by leaving the literal in a comment. That
   is the forbidden act and it is now named in `roll.py` so it is not taken. Blocks the real
   `roll.exclude()` lost-update door in `c9146abf92df`.
7. **`allsweep.py:329,720`** — suppress the child's tail for RC_FINDINGS rows, so a DANGLING-positive
   run prints one line and the uncapped listing never reaches the sweep's own output.
8. **Ten functions** in `tempus.py`, `ledger.py` and `cosmography.py` still carry zero retention
   markers under owner ruling 1 (`7099a092abd3`, honestly INCOMPLETE).

---

## 4. STILL OPEN ON PURPOSE — DO NOT "FIX" THESE

* **`f646c1c5f1d0`** — `genre.py:253` cites this order id **by name** as where the open
  `genres_scored` question is recorded. Closing it orphans the citation.
* **`30854f11f322`** — the proposed net already exists as `drill_binding_identity` and is stricter.
  Any threshold change flips three legitimately CONFIRMED hosts to false negatives.
* **`a724ec57e0d5`** — declined by three shifts running, each with a dated note. Nothing has changed
  its premises. Do not decide it unilaterally on the fourth.
* **`d1709d8e757d`** — the index was rebuilt by hand this shift (**234.9h → 0.0h**, 216 records,
  8,322 weave candidates). The order says it is never rebuilt **automatically**, and one manual run
  does not make that untrue. It closes when the rebuild is wired into the standing set.
* **`a66423722e45`** — `publish._is_agent_scratch` already refuses all 28 named files. There is no
  `publish.py` defect; the remaining remedy is relocating scratch files, which is not a publish fix.

---

## 5. HOUSEKEEPING VERIFIED AT CLOSE

`escalation --status` clear. Supervisor running (cycle 1, 18:02:58). `foreman`, `overwatch`,
`read.py --run`, `feats.py --roll` all alive and advancing — 30 files written under `data/` in the
25 minutes before close. `read.py --run` is now **in `overnight.STANDING`**, which required giving
it a `codewatch.stamp` and `exit_if_stale` first, because `drill_codewatch` derives its population
from `STANDING` and promoting an unstamped job would have breached that net silently — a
prerequisite neither order named.

**One caution for whoever runs next:** `autostart.py --watch` is running **old code** and says so
in its own log every 30 minutes. Nothing restarts the Startup `.vbs`, so every change to
`autostart.py` takes effect at the next logon. To apply one now, kill that process and re-run
`pythonw.exe src/autostart.py --watch`.
