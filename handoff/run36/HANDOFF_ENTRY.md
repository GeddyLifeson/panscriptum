## 2026-08-27 — Run #36, the daily shift that found M46

**FOR THE OWNER — READ THESE FIRST.**

**1. NOTHING IS HALTED, AND THIS RUN NEITHER RAISED NOR LIFTED A HALT.** `escalation.py
--status` read `clear` at the open and at the close. No halt was found, so none was cleared —
the standing rule that a halt you merely FOUND stays standing was never tested this shift.

**2. THE CANONICAL CORPUS HAD NO BACKUP AND NOW HAS ONE.** Order `ec67de571754`, closed. The
exposure was worse than filed and is worth stating plainly: **`data/` is gitignored, `git
ls-files data/` returns ZERO**, and the `.gitignore` comment justifying the exclusion calls it
"derived data" — which is false for `data/records/*.json`, the canonical 217-source corpus every
other file in `data/` is derived FROM. **219 canonical files, 214.7 MB, existed in exactly one
place on one disk.** New `src/canon_backup.py` snapshots the non-derivable set, then reopens the
archive and re-hashes every member against its source before it will record success, refusing
and self-deleting if any digest differs. First snapshot: 214.7 MB → 50.9 MB, verified, 6.6 s,
7-snapshot rotation. **Restore proven end to end** — a restored `WIKI_HOSTS.json` was byte-
identical to the live file. Its drill net was watched go red on both arms before staging.

**What is still yours:** this is a second copy **on the same disk**. It covers the failure that
has actually happened here — a process overwriting a file it should not have touched, twice in
one shift on 2026-08-26 — and it does not cover the disk dying. An off-machine copy is your
call and is filed separately.

**3. THE LOCAL RUNG IS STILL CLOSED, AND THE RECORDED REASON FOR IT IS WRONG.** New order
`4e37d5e59b09`. Orders `a8464e348c5e` and `505177847f43` both attribute the stall to a `num_ctx`
mismatch — config asks 12288, the resident runner serves 4096 — forcing a 6 GB model reload per
request. **Measured directly and refuted.** The same trivial prompt sent at num_ctx
None / 4096 / 12288 / 4096 gave three 90-second timeouts and one instant server-side rejection,
`"server busy, please try again. maximum pending requests exceeded"`, and **the resident
`context_length` stayed 4096 through all four, including the 12288 request.** Ollama never
reloaded. No num_ctx value works, so matching them fixes nothing — and lowering `num_ctx` to
4096, which the recorded diagnosis invites, would have shrunk the chapter content budget for no
benefit at all.

The process previously blamed — `pythonw` pid 11468, `semsearch.cli watch`, 9,599 connections —
**has exited.** Established connections to 11434 are down to 20, ten of them `ollama.exe`'s own.
What actually holds it: **`llama-server` pid 29452, up since 2026-08-26 17:28, which has burned
87,270 seconds of CPU — 24.2 hours — in 29 hours of wall clock**, 7.2 GB resident, GPU at 96%,
pinned by `keep_alive` `expires_at: 2318` so nothing will ever unload it. A real `local_agent`
order timed out at 300 s with zero output.

**The remedy is one action and it is yours: restart the Ollama runner.** That releases the pin
and drains the queue. Nothing was killed — it is a shared daemon and other things on this
machine use it. The 52-order LOCAL rung was escalated to Claude agents deliberately, once, on
that measurement, rather than being discovered order by order.

**4. dandwiki IS NOT DOWN — IT IS A LOGIN WALL.** New order `dea5b511b74b`. Two orders described
it as an unreachable host whose API "is not answering". It answered: **HTTP 403, "To reduce
server load, we had to restrict this action to logged in users only."** A transport fault is
something a retry eventually clears; a login wall is one no retry can ever satisfy, and the BOTS
rung has been probing it every 24 hours against a condition that cannot change. Three options,
all yours: hold credentials for an account, drop the source from the roll, or accept it as
permanently partial and stop probing.

---

### M46 — SOLVED, AFTER THREE WRONG DIAGNOSES, AND THE MUTATION MANDATE IS UNBLOCKED

This is the run's main result. `mutate.py --target all` had been dying about four minutes in with
a bare `FileNotFoundError` on `<sandbox>/src/assay.py`, **after its own baseline gates had passed
in that same sandbox** — blocking the whole §3b mutation mandate for three consecutive runs. It
had been blamed on concurrent edits during the copy (run #34), then on the `drill` gate
(run #35), then on `drill.py` generally (this run's first two probes). **All three were wrong.**

What settled it was the control nobody had run: build **two** sandboxes, run `drill.py` in only
**one**, and watch both. **Both died together at six seconds.** A bare sandbox with nothing
whatsoever running against it died as well. Decoy directories under other prefixes survived the
same window untouched. So the reaper matched `SANDBOX_PREFIX` and nothing else.

**The reason it hid for three runs is that reaping was the one destructive operation here that
reported nothing.** `removed` went back to callers that discarded it, and the only `note()`
covered the *failure* case — so an incomplete reap was recorded and a successful one was not.
The louder event was invisible and the quieter one was logged. A reap ledger added this shift
(`state/reap_ledger.jsonl`, recording pid, argv, paths and stack) named the call site on the
first attempt: **`drill.py → M.reap_orphans()`**.

**The defect.** `reap_orphans` deleted by **prefix and age only**. It had no notion of ownership,
so it deleted sandboxes belonging to **other live processes**. The age gate was the only thing
between a reap and somebody else's in-flight run — and an age gate is precisely what a caller
lowers when it wants to watch reaping actually happen. So `abandoned_sandboxes_are_reaped`, *in
the act of being made able to go red*, destroyed every concurrent sandbox on the machine.

That is this project's standing lesson in its sharpest form yet: **the net that could not fail
was harmless, and fixing it so that it could fail is what made it dangerous.**

**The fix.** A sandbox records its owner pid in `_owner.json`, written *before* any module is
copied — the copy is the fragile window where M46 struck. `reap_orphans` now skips any sandbox
whose owner is still alive, at **any** age; the age gate becomes what it should always have
been, a fallback for sandboxes whose owner died without cleaning up. An unknown or unreadable
owner falls back to age-only, so nothing becomes permanently undeletable — that would recreate
the 154 MB leak the reaper exists to prevent.

**Proven in both directions** (`handoff/run36/m46_fix_redcheck.txt`): a live-owned sandbox
survives `older_than=0`; **another live process's** sandbox survives it; a dead-owner sandbox is
still reaped; an unowned old sandbox is still reaped; and with the ownership check disabled, arm
one goes **RED as required**. Arm 1 **failed on the first attempt**, which is worth keeping in
the record: the first cut exempted only *other* processes, so a sandbox owned by the reaping
process itself was still deleted at `older_than=0` — one `reap_orphans()` call inside a live run
away from being M46 again with a shorter stack. The rule is now "any live owner, including
self."

---

### THE QUEUE

**159 open at the sweep → see the closing count below.** RUN went 56 → 18 and LOCAL 52 → 16.
**OWNER stayed at 49 and that is correct** — those are judgment calls a maintenance run may not
make.

Work was partitioned **by target module**, never by count, so that no two agents ever held the
same file. Two agents in the previous shift closed orders they did not own; this shift none did,
and the one agent that only half-finished an order (`98831f6e6f6d`, the second write site being
in a module it did not own) **refused to close it** and wrote the exact replacement into a
cross-module note instead. That is the behaviour the partition was for.

**Orders closed as DISPROVED, not fixed — the audits were wrong:**
* `a32028fe76b7` — `secondopinion.py` was said to swallow 531 ruff BLE001 findings. Measured
  live through the module's own `_ruff()`: **1,004 findings, 400 waived (39.8%), 604 reaching
  the queue including all 532 BLE001.** The independent opinion is intact. The order's anchor
  was stale; the codes had been waived on 2026-08-27 and reverted the same day.
* `c3b5aba07f4a` — `coverage._p()` was called accidental dead code. It is `drill.py`'s own named
  fixture proving `liveness.py` catches its own docstring's worked example. Deleting it would
  have broken a net.
* `02277646a783`, `0d5ab3aab8ff`, `e3a69ceb5857`, `c16499b0a50b`, `e45d838478c1`,
  `5925b90cb6d0` (in part) — each verified against source and found already fixed, reachable, or
  misdescribed.

**All three second-opinion tools are installed and ran:** ruff 0.16.4, vulture 2.16,
detect-secrets 1.5.0. None reported NOT INSTALLED.

---

### A REGRESSION THIS RUN CAUSED, AND FIXED

Adding `src/canon_backup.py` turned `verify_math`'s "the live sweep proves its own completeness"
check **red**, naming the new module as unswept. The check was right and was left alone — a new
module genuinely had not been read by any sweep. It is closed by this shift's whole-tree sweep
rather than by weakening the check.

Separately, a legitimate fix to `feats.py`'s discovery pagination broke a `verify_math` check
that pinned on a **source substring**, `'(ap or {}).get("continue")'`. A check that goes red
because the code got better is measuring the spelling, not the invariant — and it is the same
whole-file-substring shape nine drill nets were rewritten away from this same shift. It now
asks the **parse tree** for a loop that both reads MediaWiki's `continue` token and resubmits it,
so renaming the helper cannot turn it red and a comment cannot turn it green.

---

### THE COMPREHENSIVE SWEEP — 114 OF 114 MODULES, AND IT AUDITED THIS RUN'S OWN WORK

`sweep_plan.missing('run36')` returns **0**. Every module in `src/` was read by exactly one
agent, and each agent recorded its own coverage, because the agent is the only thing that knows
it actually read the file.

**The sweep's single most valuable result is that it caught this shift's own repairs.** Three
separate findings were against code written hours earlier by other agents on this run:

1. **Three of the sixteen freshly-converted drill nets STILL CANNOT FAIL**, each proven with a
   crafted fixture. Earlier in the shift, sixteen nets that verified a guard by whole-file
   substring search were converted to ask the parse tree instead — a real improvement, and each
   conversion was watched refuse a defeat. The audit found the conversion **fixed the medium and
   left the defect: presence is not reachability.**
   * `publish_asks_before_pushing` checks that `import mutate` appears and that "REFUSING TO
     PUSH" appears somewhere in `push()` — and never that `_MUT.active()` is *called*. `push()`
     already contains **three unrelated "REFUSING TO PUSH" strings**, so **deleting the real
     mutation interlock today would leave this net green.** That interlock is what stands between
     a mutation run and a push of corrupted source to a public repo, which happened twice on
     2026-08-25.
   * `_halt_is_not_breakage` walks the whole `If` node including dead code. A fixture that always
     declares the library "broken" and never checks halt status **passed**, because a dead
     `if False:` block carried the required tokens — reproducing the exact outage the net exists
     to prevent.
   * `mutation_never_touches_the_live_tree` passed against a crafted `run()` writing straight to
     the live tree unsandboxed.
   Six more converted nets share the weakness and are unexploitable only because each guard has
   exactly one occurrence in today's source — a property of today's tree, not of the nets.
2. **My own `canon_backup.py` had the hazard I wrote its net about.** `members()` silently
   skipped a missing canonical path, so an absent `data/records/` would have produced a
   "verified" snapshot of three small side files. **A partial backup verifies perfectly** —
   verification compares what was collected against where it came from and never asks whether
   the collection was complete. I guarded the empty case because it was easy to imagine and
   missed the likelier one. Fixed to refuse and name what is missing; its manifest write was
   also discarding its verdict, inside the one module whose whole job is not trusting an
   unconfirmed write.
3. **My own M46 fix had a recycled-PID hole** — see above.

**53 + 31 findings filed** across the two tranches. Recurring shapes worth naming:
* **The discarded write verdict.** Ten modules repaired (13 sites); an AST walk found **46 more
  across 30 files**. It is still being *introduced*: `hostcheck.py` went from 1 site to 5 *during
  this shift* when an agent refactored its writes behind a local helper. A general net is staged
  and **starts red at 46**, deliberately.
* **Fixed `.tmp` names and read-modify-writes.** Repaired in `binding_health`, `suppressions`,
  `health`, `runguard`, `endpoint`; still open in `publish.write()`, `standards`, `hostcheck`,
  `completeness`.
* **A repaired parser beside unrepaired output.** `scope.py` stopped inventing ceilings, but **28
  of 155 hosts still hold invented ones on disk that `build()` can never re-probe** — and
  `magnitude.host_ceiling()` reads them as authoritative clamps on published Magnitudes. Same
  shape as the Aurora records.
* **A cap that broke an identity, not a list.** `who-framed-roger-rabbit-…` (304 entries) has a
  roll row; the record filename is that row's 79-character slug **cut to exactly 60**, so the two
  cannot find each other. Hard Rule 0 arriving through a filename. Separately,
  `bone-jeff-smith` (86 entries) genuinely has no roll row at all.
* **A fail-open in `escalation.py` itself** — `_read_stopped()` returned `{}` for a valid-but-
  non-dict `STOPPED.json`, so every subsystem read as NOT STOPPED, while the handler directly
  above it promises in capitals that unreadable means stopped. Fixed and proven this shift.

Also closed on measurement: the machine's **TCP ephemeral port exhaustion** (BLOCKING, filed
14:51) is gone — 240 of 16,384 in use, because the foreign client that held thousands of
connections has exited. Nothing was fixed and recurrence is not harder; it is closed because the
fault stopped firing, not because it was addressed.

### A HAZARD IN THE HARNESS, NOT IN THE LIBRARY

Three separate agents independently reported that a mid-session system-reminder instructed them
to make file edits through Bash `sed` and heredocs rather than the Edit/Write tools. **All three
refused and said so**, because this repo's hard rule forbids pushing regexes and backslashes
through a shell — the eaten-escape corruption is the oldest bug here, and this project hit it
twice as recently as run #35. Their judgment was correct and no file content passed through a
shell. Recording it because the instruction will recur, and an agent that follows it will
silently corrupt source.
