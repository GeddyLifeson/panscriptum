# Next Steps — written by run #40 for the run that follows it

*Overwritten every run. The queue in `state/workorders.json` is the authority on what is open;
this file is the reading of it — what to do first, and why.*

---

## 0. NOTHING IS HALTED. DO NOT RE-DERIVE THE LIBRARY.

`escalation.py --status` reads **clear**. A halt WAS raised during run #40 and lifted by run #40:
it was **self-caused** — a change I made to `pipeline.phase_write` contradicted a netted design
decision, `drill._write_phase_stays_open_when_everything_refuses` went red, the change was
reverted, both gates were re-run green, and the lift is signed
`maintenance-2026-08-31 (automated run #40)` rather than the `owner-cli` default. The full story is
at the top of `HANDOFF.md`. **You are not inheriting a halt.**

Open the shift the way the card says — status, guard, `--sweep`, `corpus_db --rebuild` — and work
the queue.

## 1. CHECK THE GPU FIRST. IT COST RUN #40 THE WHOLE LOCAL RUNG.

**Order `LOCAL_RUNG_UNWORKABLE_GPU_CONTENDED` (OWNER).** `Overwatch.exe` held ~9.7 GB of the card's
10.2 GB for the whole of run #40. Ollama was resident but **starved**: a one-word `/api/chat` did
not answer in 300 s; the same at `num_ctx=2048`/`num_predict=16` did not answer in 90 s; a real
`local_agent` task burned **75 minutes** and returned `transport: TimeoutError timed out`.
**115 LOCAL orders were unworkable.**

**Spend sixty seconds on this before anything else:**

```
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

Then a 60-second one-word probe at `127.0.0.1:11434`. If the card is free and it answers, **work
the LOCAL rung first** — it is the cheapest rung and 115 orders deep, and most of them are
mechanical. If it does not answer, say so in the handoff and move on; do not spend an hour
rediscovering it, which is the hour run #40 spent.

This is **not** order `f6c52ef7657f` (semsearch, 804 sockets on 11434). Re-measured during run #40:
**3** sockets on that port, two ollama's own and one this project's `pipeline.py`. Two different
foreign processes, two different mechanisms. Check which one you have.

## 2. THE MUTATION PASS IS UNFINISHED

Run #40 launched it early, and it correctly reported that **the shift was editing its own gates**
(`drill.py` and `verify_math.py`). It was stopped rather than allowed to produce a survivor list
that would have to be thrown away, then **relaunched as the last act of the shift on a quiet tree**.

**Read `state/mutate_2026-09-01.log` before concluding anything.** A pass killed halfway is not a
pass with fewer survivors.

**The arithmetic deserves a ruling.** 154 mutants each pay a full `verify_math`, and `verify_math`
currently takes **15–20 minutes** instead of its usual ~32 s because `standards.check()` probes the
starved daemon — >30 hours. Either the GPU gets freed, or FAST_GATES needs a `verify_math` variant
that skips live probes. **The second is a design question, not a maintenance decision**: the probes
are part of what makes the gate meaningful.

## 3. THE QUEUE

Run #40 closed **~190** orders; the whole-tree sweep filed **39** new ones, so the number moved less
than the work did. **540 → 423.**

| rung | open | what it is |
|---|---|---|
| LOCAL | 115 | mechanical; **blocked only by the GPU** — unblock it and this drains fast |
| RUN | 116 | verified fixes and new machinery. Your real work. |
| OWNER | 102 | account actions, charter judgements, curatorial calls. **Not yours.** |
| SESSION | 54 | needs an interactive session |
| BOTS | 36 | foreman/overwatch/keeper remedies |

**The 79 `MUTANT_SURVIVED_*` orders are gone** — 73 killed by two new behavioural drill areas, 6
closed as proven-equivalent with the proof recorded. That cluster will not come back in that form.

**The stale-citation cluster is largely gone** (66 orders across 39 files). Finish the remainder the
way run #40's agents finished theirs: **replace the line number with a SYMBOLIC reference** — the
function name, or the quoted sentence — rather than baking a fresh number that will rot again. A
line number in a comment is a claim nothing can keep honest, and this project has now re-found that
fact in six consecutive sweeps.

## 4. START HERE, IN THIS ORDER

1. **`Q_PHASE8_EMPTY_RECORD_CLOSES_SILENTLY` (OWNER)** — read this one first, because run #40 tried
   to answer it and the library refused. `build_jobs_for_source` returns `[]` with no exception for
   a record with no entries, so if every ready source is like that, phase 8 marks itself done having
   built nothing. The fix went in and `drill._write_phase_stays_open_when_everything_refuses` went
   red: its second half *requires* that case to close. Both readings are defensible and only a
   ruling settles it — **and if the sweep's reading wins, the NET has to change first.**
2. **`07258ace3a09` (RUN, MAJOR)** — `address.spine_code_for()` invents a real spine code for an
   unrelated crossover title when it merely opens or closes with a catalogued franchise name.
   Live-reproduced: `spine_code_for("Alien Predator Doom Crossover")` → `"II.N"`. This is BUGS.md's
   long-standing **M44**, finally an order. Hard Rule 2 with a curatorial edge — decide
   deliberately, do not just tighten the regex.
3. **`2cb8756deb0a`** — but **raise it to OWNER first**. It asks what restarts `read.py`,
   `feats.py`, `autostart.py` and `overnight.py`; that is an operations ruling, not code. Run #40
   deliberately did not re-address someone else's order.
4. **`1e45fae97848` and `64ffa3ba30df`** — `catalogue_web.main()` has no `return` and `__main__`
   calls it bare, so a totally failed catalogue pass logs as "ok" through `overnight.join()`; and
   `resync_roll` prints post-fix figures under a "(pre-fix figures)" label on the branch whose whole
   purpose is to say the write did NOT land. **These are the same family run #40 fixed four times
   over** — `feats --roll`, `magnitude --calibrate`, `generate`'s floor, `derivation`'s verdict: *a
   verdict that never reaches the one number a supervisor reads.* Grep for more of it; it is this
   project's most repeated defect shape.
5. **`2d6c9343cd32`** — `allsweep` grades the `cascade live call` verifier bad. Almost certainly
   item 1 arriving at the battery; confirm before treating it as a code fault.
6. **The rest of the sweep's findings** — `handoff/sweep40/AUDIT_batch01..16.md`, with quoted
   evidence and remedies.

## 5. TWO THINGS THAT BIT RUN #40

**Never write regexes, backslashes or backticks through a shell `-c` string or heredoc.** It
happened **three separate times** in one shift — twice to subagents, whose work-order text arrived
corrupted and had to be refiled, and once to the run itself. Write a `.py` file and execute it.

**A literal cannot tell code from prose about code.** A structural check searched the source for a
removed literal and went **red against the new comment quoting it while explaining why it went.**
Ask the AST.

## 6. WHAT IS GREEN

`drill` **364/364, 0 breached** · `verify_math` **1,064 passed, 0 FAILED** · `codewatch` ok ·
`silence` ok · `liveness` 48, under ratchet · `health --preflight` all pass · `axis_correlation` 45
entities, matrix unchanged so no `--write` · `secondopinion` all three tools RAN,
**detect-secrets 0** · `pyflakes src/` **0** · all 116 modules compile · `ledger_guard` **5 ledgers
intact** (`handoff/HANDOFF.md` joined this shift and has its first snapshot).

**Not green:** `allsweep` 1 subsystem bad — see item 5.
