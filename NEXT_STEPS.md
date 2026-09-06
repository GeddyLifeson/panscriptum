# Next Steps — the priority queue for the next maintenance run

*Overwritten each run. The permanent record is `HANDOFF.md`; the live queue is
`state/workorders.json` via `python src/workorders.py --sweep`.*

Written by run #45, 2026-09-05. **Queue at close: 404 open** (LOCAL 136 · RUN 58 · OWNER 133 ·
SESSION 63 · BOTS 14), down from 456 at open.

---

## 0. READ THE MUTATION LOG FIRST — IT IS THE FIRST CLEAN ONE IN SEVERAL SHIFTS

`state/mutate_20260905b.log`. It was launched on a **fully green three-gate baseline**:
`import rc=0`, `verify_math 1144 passed 0 FAILED`, `drill 404 attacked / 404 held / 0 BREACHED`.
Every previous pass this week ran with at least one gate red, which **disables that gate as a
detector for the whole run** and makes survivors mostly noise — that is measured, not feared: the
2026-09-02 pass was roughly two-thirds artefact for exactly this reason.

So this log's survivor list is worth trusting in a way the last three were not. **Read it before
doing anything else**, and put the survivor count in your handoff. Three things to know:

- It takes ~20 hours and was launched near the end of run #45, so it will still be running.
  A pass killed halfway is **not** a pass with fewer survivors — say so plainly if it did not finish.
- A survivor is **not** automatically a bug. Which it is has to be decided by reading. `escalation.py`
  now has a **registry of ruled-equivalent mutants** (`state/MUTANTS_RULED_EQUIVALENT.json`,
  seeded with 9) so a verdict already reached is not re-derived a fourth time. Suppressions are
  journaled and countable; `python src/mutate.py --list-ruled` shows them; `--unrule <file>:<line>`
  puts one back in one command.
- `mutate` now scores **KILLED-BY-HANG**: a mutant that times out a gate the pristine code
  completes well inside its limit is killed, not unjudged. Check the margin it prints.

**Before you launch the next one**, confirm no agent is still editing `src/`. The harness now
refuses a red baseline taken from a tree under edit, and it exercised that refusal for real on
2026-09-05 — but a *green* baseline on a tree being edited is still let through with a warning,
and "reproducible over seconds is not stable over the hours this run takes".

## 1. FOR THE OWNER — the digest is the shortest path

`handoff/OWNER_DIGEST_20260905.md`. All 186 OWNER+SESSION orders read and grouped into **15
questions**, so one answer closes several. Highest value, in order:

1. **`342ccfafa4a4`** — the configured model `qwen3:8b` is a **thinking** variant, and
   `config.yaml`'s own comment block *requires* a non-thinking one because `generate.py` strips no
   think-tags. Harmless only while `prose_enabled` is shut. Three options in the order.
2. **`959b98f38a63`** + **`5be28f56946c`** — the fandom throttling. Hosts answer a single request
   in 0.27s; we run 12 workers; and **`binding_health.is_quarantined` is never consulted on the
   fetch path**, so the 3-strike hand-off brakes nothing. Closes seven recurring BOTS orders.
   Do **not** pick a worker count from my probe — measure the real per-host rate first.
3. **`71ae3fa7e55e`** — should a breach read from a tree under active edit halt the library?
   Raised because run #45 halted itself that way. The proposal (re-read only the breached net
   before halting) makes the drill *stronger*, not quieter, and explicitly does **not** let the
   maintenance guard suppress a halt.
4. **The 31 over-escalated orders** the digest lists as belonging on RUN, not OWNER. I did not
   re-address them — moving an order off the owner rung is still a decision about who decides.
   Approving that list would take ~24% off the OWNER rung in one stroke.
5. **`9b54659bc403`** — both remedies are written out as exact code; pick one.

## 2. THE UNFINISHED HALF OF THE SHELL-SAFETY FIX — `1c99df1f69c1`

`workorders.py` now has `--how-file` and stdin, and text round-trips byte for byte. Work-order text
passed on argv is **executed**, not merely mangled.

**THERE IS NOTHING LEFT TO PATCH IN THIS REPO — do not go looking.** A `--how` / `--resolve` search
across the tracked tree was run twice on 2026-09-05 and verified independently by the coordinator:
the unsafe form appears **only** in past-tense audit prose under `handoff/`, in `workorders.py`
itself, and in `state/foreman_backups/` copies of it. `MAINTENANCE.md`, `CLAUDE.md` and `prompts/`
carry **no** instruction to shell `--how`. (An earlier note in this shift's own reporting said the
docs did; that was wrong, and correcting it here is the point of this paragraph — the next run
should not spend a search on a file that does not exist.)

**The whole remaining remedy is the wording of the session brief a coordinator writes when it
spawns agents**, which is not a repo file and cannot be fixed by editing one. Whoever writes that
brief next should use:

```
write the resolution with the Write tool to <scratchpad>/how_<id>.txt, then
  python src/workorders.py --resolve <id> --how-file "<scratchpad>/how_<id>.txt"
```

**The mechanism has bitten at least four times across two separate sweeps, months apart** — which
is the order's own argument that this is structural rather than an agent being careless. The fourth
predates the three the order names: `handoff/run35/AUDIT_batch2.md:107-109` records that
`b68ca666da79`'s resolution "got truncated mid-sentence by an unescaped backtick in the shell
command (bash read `` `continue` `` as command substitution)" and ends abruptly at `"...and "`. It
joins `525dd7bbffed` and `7209d442c73e` as unrepairable — the closed log is append-only.

Also note `shell_active()` under-reports: it misses `;` `|` `&` `>` `<` newline `!` and the single
quote (order `ebdd80dc9e68`).

## 3. WORK THESE FIRST ON THE RUN RUNG — the sweep's sharpest, all verified against source

- **`b418b8b3be54`** — the name-keyed fold fixed in `write_record` **is still standing in
  `write_record_catalogue`**, one function over. Measured: 935 rows a name-keyed dict collapses.
  The twin's group-order remedy does *not* transfer; read the order.
- **`de0681cb9edc`** — `wiki_source`'s listing walks return a **partial roster** on a transport
  failure while `catalogue_web` asserts they raise. Lands `entry_count > 0`, not retryable.
- **`ef4ca9edd61f`** — **34,676 of 275,029 cache files (12.6%)** cannot distinguish a fetch
  failure from a genuinely page-less entity. marvel 25.6%.
- **`6e2dab4c3981`** — `scope.py` caches an API failure as an honest empty verdict. SCOPE.json is
  155 hosts all at stamp 0, so the *next* `--build` is the run that stamps them.
- **`f4af474dfc49`** — `mutate._session` KeyError-aborts the first time a mid-run baseline refresh
  cannot complete. Relevant to item 0.
- **`12aca83cab86`** — `weave.components()` fuses every shelf into one continuity when the null
  threshold returns its "could not measure" 0.0.
- **`91cbbd5e4d24`** — `cleanup.clean_description` is not idempotent (1 case in 282,749) and that
  breaks `pipeline._is_cleaned_twin` on a second `--apply`.
- **`9508f9322b4c`** — a hole in run #45's own `freeze_plan` fix: three conditions collapse to one
  bare `None`, so a frozen plan can be silently recomputed and overwritten.

## 4. VERIFY BEFORE WORKING — several orders look already-fixed

The sweep flagged these as repaired in source but still open. **Confirm each on a CODE line, not a
comment**: this codebase records in comments what a line used to be, and that trap produced false
positives for three separate agents on 2026-09-05.

`7604e95da60d` · `980ccacdcead` · `9f9f19d77791` · `2f8ebf12e5f2` · `e41c9c2e4839` ·
`64ffa3ba30df` · `52a73082c56b` · `c6ca8a8f8e55` · `b1612dc92424` · `18187cb13de7` ·
`e9ff72c7eb48` · `4da7238657a3` · `357e24fa2fa1` (8 of 9 sites gone)

**`b1f561587b19` is the exception — do not close it on a report.** Two agents reached opposite
conclusions about whether `prose_gate.section_shortfall` already charges extras into `required`.
That is the owner-held gate whose deletion once cost 145 unauthorised chapters. Read it yourself.

## 5. PROCEDURE — the thing run #45 got wrong

**Do not run the battery while sweep agents are still writing to `src/`.** That is what halted the
library on 2026-09-05: an AST net read `publish.py` during the few seconds it was not valid Python.
Sequence it — agents report, then `codewatch.quiet_seconds()` reaches `STABLE_SECONDS`, *then* the
battery. The read-only sweep batches can overlap with the battery safely; the editing ones cannot.

Corollary worth keeping: **the sweep is read-only by design now.** Sixteen batches audited 97,104
lines and edited nothing, which is what let the tree settle while they worked.

## 6. THE LOCAL RUNG SHOULD NOW WORK — verify that it does

The transport timeout that made it return empty-handed is fixed (`local_agent._chat` reads
`request_timeout` from config instead of a hardcoded 420s). **Nobody has yet seen it complete an
order**, because the shift routed the work to Claude agents once the failure was measured. Give it
a few orders early and check its diffs. If it is still slow, the likely cause is item 1.1 above —
a reasoning model spends its budget thinking before it emits a tool call. `--no-apply` stages
without writing.

136 orders sit on LOCAL. That rung is the owner's standing instruction and it has been inert for
days for a reason nobody had measured.

## 7. STANDING

- `data/BINDING_HEALTH.json` is **9 days stale** — the probe is not running on any schedule.
- `data/CHAIN.json` was fitted 2026-08-22 over ~8,000 of the **21,993** contest rows now held.
- `tiers.DELIBERATE_JOIN = 2000.0` is argued from a 99.5th percentile of 365 that is now **1,222**.
- BUGS.md's Open section still holds ~56 entries labelled RESOLVED that were never moved
  (`ca0a93856e2a`). Move them **one at a time, each verified** — several are partially closed and a
  bulk regex would silently close live faults.
