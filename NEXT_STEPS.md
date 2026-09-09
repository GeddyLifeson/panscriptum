# Next Steps — the priority queue for the next maintenance run

*Overwritten each run. The permanent record is `HANDOFF.md`; the live queue is
`state/workorders.json` via `python src/workorders.py --sweep`.*

Written by run #49 (owner-directed), 2026-09-09. **Queue at close: 51 open** (RUN 22 · OWNER 20 ·
LOCAL 6 · SESSION 2 · BOTS 1), down from **65**. Eight RUN orders closed by hand, nine more closed
by the sweep as throttled hosts recovered, two filed.

**Gates GREEN:** `verify_math` **1282 passed / 0 FAILED**, `drill` **467 nets / 467 held / 0
BREACHED**, `pyflakes` clean over `src/`, `secondopinion` all three tools RAN with **0 secrets**
agreed by two independent scanners, `escalation --status` clear. `health --preflight` shows one
FAIL — `dandwiki.com` not answering its API, the standing BOTS order `2da53c3e192f`, an external
host.

---

## 0. THREE THINGS BEFORE ANYTHING ELSE

**1. A CORRECTION YOU MAY HAVE INHERITED.** If you read anywhere that *"`escalation.py` has never
received a mutation result"* — including in run #48's own correction entry — **it is false.** There
are **176 closed `MUTANT_*` orders, 99 naming `escalation.py`**, and the **2026-09-04 pass
completed all three targets** (309 mutants, 72,310s, 13 orders filed). That pass also reports
`escalation.py:409 False -> True SURVIVED`, which is the verdict order `58a00e909217` is waiting
on — read it before re-deriving anything.

**2. DO NOT RELAUNCH THE MUTATION PASS BLINDLY.** See §1. It is not a broken instrument; it is a
twenty-hour job spawned as a child of a one-hour shift.

**3. THE PHASE 4.3 SHELF MAPPING IS WAITING ON THE OWNER, NOT ON WORK.**
`handoff/phase43/SHELF_MAPPING_PROPOSAL.md`, 31 rows, unsigned. Do not write any of it to the
spine. See §5.

---

## 1. THE MUTATION PASS — `d2d4ff880570`, AND WHAT IS STILL UNKNOWN

**Diagnosed:** `mutate.py` is in neither `overnight.STANDING` nor `ALL_JOBS`, does not detach (no
`DETACHED_PROCESS`/`CREATE_NEW_PROCESS_GROUP`), and a completed pass takes ~20h against a shift
that lives ~1h. Run #48's pass died inside target 1 with **no traceback**, and the exit 4 it
reported **cannot have come from mutate** — the only `return 4` fires before a banner that IS in
the log, and its message is absent. A twenty-hour job left 1,369 bytes of evidence.

**Remedy, in order:** (a) a `--detach` flag re-spawning itself detached, using `autostart.py`'s
spawn as the working precedent; (b) put it on a roster or record in `codewatch.EXEMPT` why not —
today it is neither covered nor exempted, and `coverage()` cannot report a job absent from
`ALL_JOBS`; (c) capture its output **unbuffered**, because the most expensive thing about the
09-08 failure is that the evidence did not survive the kill.

**STILL UNKNOWN, and do not close the order believing otherwise:** the 09-05b and 09-07 passes died
differently — `FileNotFoundError` on their own sandbox path, mid-run. **The reaper was investigated
and cleared**: `reap_orphans` exempts a live owner pid at any age, and `_pid_alive` uses
`psutil.pid_exists` with a ctypes `OpenProcess` fallback, **not** the `os.kill(pid,0)` idiom of
order `b9044b16c8e9`. That cause needs reproducing, not guessing.

**AND THE SEQUENCING RULE STANDS UNTIL (a) LANDS:** editing `src/` voids a pass's baseline, so
launch it as the **last** act of a shift, never an early one.

---

## 2. THE RUN RUNG — 22 LEFT, THE VERIFIED ONES FIRST

These four were filed by run #48's sweep with the verification already done and are unblocked now
that the 404 definition is correct:

1. **`86b8dd723f90`** — `binding_health` never passes `outcome=` to `feats.fetch`, so a throttled
   fetch and a genuinely absent page both return `(0, None)` — in the module whose verdicts
   quarantine hosts. **Now unblocked**: `feats.CLEAN_NEGATIVES` and `failed_dirty` exist, so a
   third "could not tell" answer can be built on a correct definition.
2. **`1d55458779fd`** — `coverage.py` documents `UNREACHABLE`, *"the only state that is purely a
   defect"*, and the string appears exactly once in the file: in that docstring. Also unblocked by
   the same fix; land it **after** checking `86b8dd723f90`'s shape so the two agree.
3. **`5448a236b884`** — an unparseable model reply is the one pool failure that neither benches the
   bucket nor reaches the unrecognised ledger, and on the hot path `served` is not even passed.
4. **`194dc5f6d24f`** — *"corpus read is progressing"* measures a **cumulative** counter, so after
   the first chunk this HIGH standard can never go red. **Not attempted this run**: the honest fix
   is a delta, using the `job_stamp`/`JOB_WATCH` machinery that `standards.py` already has for its
   sibling standard, and it is more than a line. Note it composes with `d9328fe1ee38`'s remedy
   rather than competing.

Then the gathered ones: **`89503c58409f`** (50 rotted line citations across 33 modules — the
load-bearing row is `verify_math.py:11720-11723`, whose argument that cross-module citations do not
rot is refuted by three of its own six examples) and **`215f9e7b86ff`** (unmarked cuts; each site's
marking helper already exists in its own file).

**Two structural recommendations that came out of this run's fixes and are worth their own orders:**

* **Merge `overnight._cmd_is_running` and `codewatch.runs_script`.** They are two spellings of one
  rule that have now drifted apart **four** times (`codewatch.twins` twice, the allsweep roster,
  and the `-c` gap fixed today). Do it carefully — different signatures, different callers, and a
  shared helper becoming a shared bug is the obvious failure.
* **Cheap structural nets** for two fixes landed today that got none: that `allsweep.reconcile`
  contains no second process enumeration, and that `health.reopen_stranded` re-reads between its
  load and its land. Both are AST-shaped and cost nothing per battery run, unlike behavioural nets
  that would walk the corpus.

---

## 3. STILL OPEN ON PURPOSE — READ THE SHIFT NOTES FIRST

* **`a66423722e45`** — **its remedy as written would red the battery.** `verify_math` §20u
  *executes* the six `handoff/run35/checks_L*.py` and asserts all six are still on disk; six more
  are held in a checked register. Only the ten under `nets_20260906/` are real scratch, one of
  which is the staged net `2f07cbd3241d` is owed.
* **`c9146abf92df`** — the `roll.exclude()` lost-update door. Blocker re-verified as **current**:
  `checks_L4.py` pins the literal call text and §20u does execute it. `b3da16ddfe64` is the real
  prerequisite.
* **`d1709d8e757d`** — nothing schedules an index rebuild. Still true. Its *numbers* are stale;
  the shift note carries the current ones.
* **`58a00e909217`** — see §0.1. Evidence for it exists in the 09-04 log; the order asks for a
  non-drifting sandbox, so read both before ruling.
* **`f646c1c5f1d0`**, **`30854f11f322`**, **`a724ec57e0d5`**, **`5d0fa30e4b09`** — unchanged, each
  with a dated reason.

---

## 4. FOR THE OWNER

1. **`c9666b0bd8d9`** — two hosts mined the wrong universe into the catalogue and it is still on
   disk. Purge, mark contaminated, or leave the quarantine as the only guard?
2. **`50e8d8be9a9b`** — what range may a Hand's reading take? `400.0` still publishes and both the
   battery and the drill assert that it does.
3. **`c39a2c0e1bef`** — Phase 4.3's rich join. **The proposal in §5 is the answer to this one.**
4. **`f7d7769075c0`** — should a designed rc=17 restart raise an owner-visible order?
5. **`88982cef258d`** — two free-tier API keys need re-issuing; `58a00e909217`'s cloud lane is
   blocked behind it.
6. **`2cb442afd901` — NEW.** What fraction of the corpus moving should make the entity index
   "stale"? `behind` and `modified_since` are now recorded on every call, so a few days of readings
   give the real distribution before you pick a number.
7. **The sequencing ruling** from run #48 §1 — drain RUN first and launch mutation last, or keep
   the early launch and accept RUN-rung work is a different shift's job. Remedy (a) in §1 would
   dissolve the question entirely.

---

## 5. PHASE 4.3 — THE MAPPING IS DRAFTED AND UNSIGNED

`handoff/phase43/SHELF_MAPPING_PROPOSAL.md`. **26 DIRECT** rows reaching **81,581 entries**,
against the **3** threads the thin leg yields today. **2 JUDGMENT** (Great Wheel — the D&D shelf is
~40 roll entries and which the row governs is a scoping call; Ludic Spheres — three of four clauses
resolve, *"arenas in service"* fits Rocket League and ARMS equally). **3 REFUSED** (Masked
Multiverses, Rot City, The One War — the evidence names nothing, and for the last, "maps to no
source" is a legitimate ruling).

Every row is licensed by the Chronicle's own `stands_at` sentence naming canon particulars — Moro
and Granolah, the Omenpaths, the Crucible, Era Indomitus — **never by a shelf name resembling a
source**, which §7G forbids. Every proposed source was checked to exist on the roll by exact name.

**Nothing is written to the spine and nothing should be until rows are confirmed.** 4.4 and 4.5
remain UNAUTHORISED; `prose_enabled` is untouched.
