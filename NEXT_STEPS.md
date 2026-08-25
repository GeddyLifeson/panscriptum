# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #17 wrote this on 2026-08-24 ~20:50 local.*

**Read this first.** Four things shape what is worth doing next run:

1. **THE SCHEDULE IS EVERY 15 MINUTES (`11,26,41,56 * * * *`), so you will routinely land on a
   live predecessor and that is the designed steady state.** The guard exits in seconds. It does
   **NOT** see interactive sessions — before writing anything, check
   `git -C C:\Users\imarl\panscriptum-export log --oneline -5` and `ls -lt src/*.py | head`.
2. **RUN #17 FIXED THE PUBLISHER, AND THE ROOM IT WAS FIXED IN IS STILL DIRTY.** The standing
   loop had been publishing the public page into a dead Claude session's temp directory (M13,
   now resolved). The **stray 26 MB repo is still on disk** and the **`PANSCRIPTUM_EXPORT`
   variable in the running supervisor's environment still points at it** — the fix works by
   refusing that path, not by cleaning it up. §2 A is the decision. **Do not "fix" this by
   editing the variable in a shell: the supervisor tree has carried its environment since
   2026-08-23 and only a supervisor restart would adopt a new one.**
3. **THE PAGE IS TRUSTWORTHY AGAIN, BUT ITS JOBS PANEL IS NOT.** The `generated` stamp now
   moves on the ten-minute loop (verified: `pushed` at 20:43, commit `012dcb2`). The corpus-read
   panel, however, is a verbatim pass-through of the last matching line in `read_auto.log` and
   **keeps rendering a dead reader's numbers with no staleness marker** — see M14. Read the
   `machine` group and the process list before believing the `jobs` array.
4. **RUN #17 CHANGED `publish.py`'s EXPORT RESOLUTION AND ADDED A DESTINATION TO ITS LOG LINE.**
   If anything about publishing looks odd next run, `state/publish.log` now names the target
   directory on every cycle — read it before theorising.

## 1. Verify first

1. **[M13 — did the publisher stay on the right tree? One line.]**
   ```
   tail -3 state/publish.log
   ```
   Expect `synced N files, wrote docs/state.json  ->  C:\Users\imarl\panscriptum-export` and
   `pushed` (or `no change to push`). **A `->` naming anything under `Temp` or `scratchpad`
   means the guard was bypassed or reverted.** You should ALSO expect a `publish: REFUSING
   PANSCRIPTUM_EXPORT=...` line on every start while the supervisor's poisoned environment
   survives — **that line is the fix working, not a new fault.** It disappears only when the
   supervisor is restarted from a clean shell (§2 A).
2. **[M14 — IS THE READER ACTUALLY RUNNING? This is the one to check first, every run.]**
   Run #17 ended with `read.py` **down** (exited `rc=15` at 20:35:58 after 41 minutes with no
   progress output) and the supervisor had not yet restarted it. `allsweep` is what caught it —
   look for the `NOT RUNNING` line in its RECONCILE block, and confirm against the process list.
   **Then check the log is moving, not just the process:** `read_auto.log`'s last write was
   **forty minutes older than the process's own death**. A live PID is not evidence of work.
3. **[THE POOL'S RED NOW HAS A NAMED CAUSE, AND IT IS NOT THE READER.]** Run #16 fixed how the
   pool is *reported*; run #17 measured *why* it is red, and the standard's own guidance is
   wrong about it. `model calls per hour` reads 32 against a floor of 900, three of four
   sub-standards hold, and the order text concludes **"the reader is not asking"** — which sent
   run #16's queue to check the reader's transport. **The transport is fine**
   (`read_auto.log` line 1: `transport: Cascade (cloud buckets, local Ollama as the last
   bucket)`; line 2: `8 workers`). Measured from `state/cascade_scratch.db` instead:
   **116 calls in the last hour (46 ok); 820 calls over 3 hours of which 636 — 78% — were
   `rate_limited`.** `zai:free`: **20 calls, 0 ok, all rate_limited.**
   **No standard in the tree can see a 429 storm** — `buckets with headroom` counts quota
   headroom, which a rate-limiting bucket still has. This is the highest-value item. §2 C is
   the design question; the measurement above is done and need not be redone, only refreshed:
   ```
   python -c "import sqlite3,time;c=sqlite3.connect('state/cascade_scratch.db');t=time.time()-10800;print(list(c.execute('select outcome,count(*) from usage where ts>? group by outcome order by 2 desc',(t,))))"
   ```
4. **[m79 — the ETA is still `0.0h` and the page still prints it.]**
   ```
   grep -o "eta [0-9.]*h" state/read_auto.log | sort | uniq -c
   ```
   Run #17 got **`122 eta 0.0h`** — every line in the file. If a restarted reader now produces
   a spread of ETAs, the rolling window recovered once real (non-cached) chunks entered, which
   is itself the evidence needed for the §2 D ruling. **A fresh log full of `0.0h` again is the
   confirmation that the eviction guard is the mechanism.**
5. **[preflight — 2 FAILs is the baseline; a THIRD IS THE FINDING.]** This pre-registration paid
   immediately in run #17: preflight printed three, the third was `state consistency: entries
   stranded in closed batches: 19`, and it was cleared in four minutes with
   `health.py --reopen --go`. The two expected are `API paths per host family` (**M8**) and
   `caches empty ... feats/www_dandwiki_com` (**M1**). **If `state consistency` returns, note
   whether it names the same batch** — a recurrence on
   `Arcanum Worlds (Odyssey of the Dragonlords)#480` while its ~23-hour `ingest_doc --mine`
   is still running would mean the strand is being re-created, not left over.
6. **[M8 — is fandom back? Four seconds, TCP only.]**
   ```
   python -c "import sys;sys.path.insert(0,'src');import standards as ST;print(ST.fandom_ipv4_reachable())"
   ```
   **Read the latency, not just the boolean**: a slow False is a block; a fast False (<1s) is a
   third answer meaning something new is wrong. The edge IP rotates; that is not itself news.
7. **[m65 — bounce the foreman ONLY when §1.6 says fandom is back, and check the child first.]**
   ```
   powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*adopt*' } | ForEach-Object { '{0} parent={1}' -f $_.ProcessId, $_.ParentProcessId }"
   ```
   A child under the foreman's PID means **DO NOT BOUNCE**. Run #17 saw a live
   `hostcheck.py --adopt --go` at 20:36. The foreman is still the one job running pre-run-#15
   code (started 11:22).
8. **[M11 / M9 / M4 — confirmed closed, one line each, keep them cheap.]** `gpu_lane.status()`
   shows a `foreground` row whose `age_s` stays under ~100 on a live holder;
   `40,884 rows -> 40,884 queued` (must be EQUAL); `598 False False True`.
9. **[ANSWERED — stop re-investigating these.]** **The reader's transport**: it IS Cascade with
   8 workers; the pool red is refusal, not silence (§1.3). **§2 H / m56**: the lane IS
   arbitrating. **The `every source is fully catalogued` UNMEASURED HIGH**: 100% downstream of
   M8, correct behaviour. **The keeper**: healthy, and in run #17 it correctly caught the
   publisher down mid-cycle and restarted it.

## 2. Human decisions needed (owner)

A. **[NEW, run #17 — THE DIRTY ROOM BEHIND M13. Two questions, both cheap, neither safe to
   guess at.]**
   (i) **The stray export repo** at
   `C:\Users\imarl\AppData\Local\Temp\claude\C--\660495b7-...\scratchpad\panscriptum-export`
   is **26 MB, 160 commits ahead of `origin/main` and 63 behind**, pointed at the real remote.
   It is a genuine parallel history of page snapshots. **Delete it, archive it, or leave it?**
   Not deleted by run #17 — deletions need a review cycle, and Windows may reap it on its own,
   which is itself an argument for deciding deliberately.
   (ii) **The supervisor's environment still carries `PANSCRIPTUM_EXPORT` pointing at that
   path.** Nothing in `src/` sets it; the process tree has held it since 2026-08-23. The fix
   refuses it, so nothing is broken — but every publish start now prints a REFUSING line.
   **Restart the supervisor from a clean shell to clear it, or leave the warning as a standing
   reminder?** A supervisor restart bounces every job, so this is the owner's call.
B. **[NEW, run #17 — M14: how should a jobs panel say "this reader is dead"?]** The dashboard's
   pass-through design is deliberate and correct in principle ("the dashboard can never disagree
   with the system it is reporting on"). Its cost is that a stopped reader renders as a working
   one. Two candidate remedies, both design changes: **age the panel off `read_auto.log`'s
   mtime** (cheap, no reader change, matches how `coverage figures are current` already works),
   or **have the reader stamp a heartbeat** the panel reads (truer, more moving parts).
   **Also open, and the bigger half: should `read.py` join the keeper's `STANDING` set?**
   `overnight.py:344-347` deliberately excludes it — the reader "hangs off this supervisor's
   hours-long main lap" — so an early exit is unattended until that lap comes round. Measured
   gaps: **1 min, 8 min, 32 min, 37 min, and once 4 hours.** The exclusion may well be
   deliberate (a reader is not idempotent the way a dashboard is, and a keeper that restarts it
   every five minutes could thrash a job that legitimately takes hours), **which is exactly why
   this is a question and not a patch.** If the answer is no, the alternative is a staleness
   alarm rather than a restart. **Do not chase `rc=15`:** all six recorded exits carry it, over
   6m/13m/41m/57m/61m/490m, so it is the ordinary exit, not a fault signature.
C. **[NEW, run #17 — should the standards tree be able to see a 429 storm?]** Per §1.3 the pool
   is refusing 78% of calls and no standard reports it; worse, `model calls per hour`'s order
   text actively concludes the opposite ("the reader is not asking") and has already misdirected
   one run. Candidates: a fifth pool standard measuring the refusal share, or widening the
   window `calls that succeed` judges over (the usage DB holds 820 calls over 3h where the
   15-minute window holds 8–15, which is why that standard so often reads UNMEASURED — the data
   exists, the window declines to look at it). **The floor is an opinion and the window width is
   deliberate (`window_min: 15`), so neither is a repair to make unasked.** Run #17 deliberately
   left the order text alone rather than editing guidance under time pressure.
D. **[NEW, run #17 — m79's fix needs a ruling on both branches.]** The rolling window's eviction
   guard never trims below two samples, so a stall plus two cache-hit completions gives a
   millisecond `dt`. But the **fallback** branch, `crate = done["chunks"] / max(el, 1e-9)`, is
   the from-t0 average the rolling window was introduced to replace — so "just use the fallback"
   reinstates the older wrong number. **Which rate should the page show while the queue is still
   working through cached entities?** Related and still open from run #15b's audit:
   `chunks_reused` is computed and thrown away, so the rate mixes instant cache hits with real
   model calls no matter which branch wins.
E. **[M12 — STILL THE BIGGEST UNREALISED ITEM. Rebuild the manifest?]** Zero feats chapters in
   an 88 MB manifest feeding a live `generate.py`; the join is healthy and would now produce
   **1,215 entity blocks across 100 sources**; **55,372 mined feats reach no volume.** Rebuilding
   underneath a running prose job is a decision, not a repair. `manifest_builder`'s
   `content_hash` means a rebuild correctly marks changed jobs stale rather than redoing
   everything. **Say whether to rebuild, and whether to stop `generate` first.** Unchanged from
   run #16 — no run has touched it.
F. **[M8 — the only one blocking real work] Is the fandom IPv4 outage a block we earned, or a
   network fault between here and Cloudflare?** All fandom content hosts share two Cloudflare
   IPv4 addresses and both time out; the same edge answers instantly over IPv6; other IPv4
   destinations are fine. **Forcing IPv6 to get around it is a decision only you can make**, and
   runs #14–#17 have all deliberately declined to take it.
G. **[carried, run #16] `FEATS_BLOCK_CHARS` is now referenced by nothing but its own comment.**
   Delete it, or keep it as the measurement of record? Kept for now — deletions need a review.
H. **[carried, run #16] A diagnostic that reports 8 failures from 0 attempts.** In
   `completeness.py`'s host-unreachable short-circuit, the row carries `probe_failures: 8`
   alongside `probes_run: 0`. Diagnostic-only and decodable, but it is a number people reason
   from. Rename, zero it, or leave it?
I. **[m54's cost — confirm the trade.]** `_BEAT_SECONDS` 300s → **100s** means every held lease
   is rewritten 3× as often under contention. Run #17 saw nothing odd in `state/lane/`.
J. **[carried — the `read.py` audit's five questions, unchanged and still open.]** Chunking has
   **no overlap** so a feat sentence straddling a boundary is unrecoverable; **two different
   "own page" tests** disagree on curly apostrophes; **`chunks_skipped` is arithmetically wrong
   for multi-page entities**; a **stale comment describes a `cap_chunks` safety net that is
   inert**; **`chunks_reused` is computed and thrown away** (now also §2 D).
K. **[M10's cost — still worth confirming.]** Entity-scoping the chunk cache orphaned **8,194**
   cached answers (not deleted — just no longer found). Run #15b judged a smaller-but-wrong
   library the worse outcome. **Say if you disagree.**
L. **[carried] The cloud worker floor, the compounding cache TTLs, the 240-char description
   truncation, the last 22 oversized chapter blocks, `check_context_budget`'s scope, and the
   burst lane's 598/500.** All unchanged from run #16's §2 H/I/J/K — none touched this run.
M. **[m25 / m16 / dashboard `findings` cap of 12 / `health.reopen_stranded`'s `reopen[:20]`
   print] — ONE ruling, now FIVE sites: does Hard Rule 0 bind diagnostics and run logs, or only
   reader-facing listings?** Carried since run #5. Run #17 added the fifth site, spotted while
   using the tool. **"Does anything downstream act on the truncated list?" is the workable test.**
N. **[carried, run #16] `entity_match.py` is a complete module with zero production callers.**
   Wire it in, or retire it? Per the project's own lesson, a function that exists and is never
   called is worse than one that is missing.
O. **[carried] The stale local buckets.** The reader still logs `REMOVED local-<model>: HTTP 404`
   across pruned models on every start — run #17 counted `gemma3:12b`, `qwen2.5:14b`,
   `llama3.1:latest`, `qwen3:30b-a3b-...`, and the unsloth Q3 GGUF, several of them 3–4 times per
   start. Self-healing per process; the roster lives outside `src/`. Confirm the prune was
   intentional — this is the single noisiest thing in `read_auto.log` and it obscures the log's
   real content.
P. **[carried] Permanently hostless roll entries** — catalogued with no host **20**; on the roll
   but never catalogued **6**; **1** host for a source with no catalogue record (Lost Mines of
   Phandelver). The **91 DECIDED spine codes** are **still not written to
   `CHARTER_SPINE_CODES.json`**, which has no writer in `src/`. Also **34 catalogued sources have
   no charter spine code**, and three charter errata are open.
Q. **`site/state.json` is stale and nothing in `src/` references `site/`** — the live artifact is
   `docs/state.json`. Dead directory, or something's input? Also **2 cache directories no source
   points to** (`feats/jojo_fandom_com`, `feats/www_dandwiki_com`). **No deletion without a
   ruling.** Note this question now has a sharper edge: run #17 proved the project can carry a
   whole second copy of an artifact that nobody is reading.
R. **[m58, m57, m48, m47, m37, m29, m26, m39, m38, m12, m13, m30, M1, m43]** unchanged from
   run #16's §2 N — none touched this run.

## 3. Small implementable items (no decision needed)

1. **`pipeline.py`'s 9 shared cross-phase JSON writes** still use raw `open+json.dump` rather
   than `_landed`/`replace_retry`. Open since run #2 and now **the last member of its family**.
   `health.reopen_stranded` was fixed to use `replace_retry` and run #17 exercised that path
   live against a running pipeline — it worked, which is a working model to copy.
2. **`gpu_lane._write_claim` and `_touch` use a bare `os.replace`, not `silence.replace_retry`.**
   Verified twice now: `_remove_retry` in that same file cites the Windows rename-denied race
   (m55) as its own justification, so the module already knows the hazard and two of its writers
   do not use the remedy. **A new foreground claim's FIRST write has no beat margin to absorb a
   miss.**
3. **35 silent exception handlers** (`python src/silence.py`). **Run #17 added net zero.** The
   audit reads the AST, so a `#` comment does NOT satisfy it; the idiom is a string
   (`_ = "silence-exempt: ..."`). Concentration: **`gpu_lane.py` 13** and **`context_budget.py`
   4** (fallback-to-empty-string when a prompt file cannot be read — which would generate against
   an EMPTY system prompt rather than fail). Also open: `standards.py` ×2, `entity_match.py:272`,
   `overnight.py:500` (**inside the keep-warm loop**), `publish.py:185`, `coverage.py:92`,
   `pipeline.py:1570`, `foreman.py` ×2, `health.py` ×2, `local_agent.py` ×2.
4. **`gpu_lane._alive` contradicts its own documented policy.** Its docstring says unknown
   answers are treated as ALIVE deliberately; an unparseable `pid` returns `False`. **Verified.**
   Only reachable via external corruption, but it is a direct comment-versus-code mismatch of
   the class that has produced this project's last four majors.
5. **`JOB_OVERHEAD_CHARS`'s comment does not reproduce and still cannot be re-measured** — the
   live manifest contains no feats jobs at all (M12), so there is nothing to measure. The
   constant (2,000) errs conservative either way. **Fix the comment only after M12 is resolved.**
6. **`_HAS_ACTION`'s verb list may have recall gaps** (audit, **still unverified**):
   "vaporiz-", "annihilat-", "incinerat-", "smash", "explod-", "shred", "stun", "wound" are
   absent. Honestly accounted in `chunks_skipped`, so not hidden — but nobody has measured the
   false-negative rate, and run #17 saw `dropped 5,311` against `chunks 4,557`, i.e. **more
   chunks skipped than read**. That ratio makes this worth an actual measurement.
7. **`entity_match.candidates()` recomputes `split_qualifier(name)` inside its pool loop.**
   Performance only. Low priority while the module has no callers (§2 N).
8. **DONE, do not redo:** M13, m78 and §19aj (run #17); M11, m75, m76, m77, §3.3 (run #16);
   M9, M10, m54, m55, m62, m70–m74, the regime rate-gate (run #15b); m66–m69 (run #15);
   m63, m65 (run #14); m64; M8's *standard* (the outage itself is open); m61; the M7 gate fix.
   **Also settled and not to be re-derived:** a timed-out chunk is **deferred, not lost**;
   `hostcheck`'s `judgeable` flag **is** consumed at `standards.py:571`; the lane **is**
   arbitrating; the completeness UNMEASURED HIGH is **downstream of M8, not a bug**; the
   reader's transport **is** Cascade with 8 workers.

## 4. Surface rotation for the next audit fan-out

**Run #17 ran one subagent, on `read.py`'s progress/ETA reporting, and it paid — but read its
report critically.** It correctly traced both code paths, correctly refuted my opening
hypothesis (that "chunks/s" was secretly elapsed seconds — it is a real `dc/dt`), and correctly
established that `dashboard.py` computes nothing of its own. It then **could not account for the
page's `0.01 chunks/s / 2286.3h` reading against a log containing `122 eta 0.0h`, and said so
plainly rather than inventing a mechanism.** That honesty is the useful part and the discrepancy
is still unexplained — **it is a live thread, not a closed one.** Whoever picks it up: the page
snapshot was taken at 19:43 and the reader was restarted at 19:55, so the two readings may
simply belong to different sessions of a log whose history is confusing; prove it rather than
assume it.

Covered, do **not** re-read unless the diff touched them: the round-1 full-codebase audit and
evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces; run #3's two; run #5's three;
run #6's four; run #7's five; run #9's `feats_index.py` and `hostcheck`; run #10's
`manifest_builder.pack_feats` + `generate.py`'s feats branch; run #11's `system_style.txt` and
`pipeline.py`'s `ask`/`ask_pool_first`/`phase_entrypass`; run #12's `gpu_lane.py` and
`context_budget.py`; run #13's `read.py` transport ladder; run #15's `tuning.py`; run #15b's
`read.py` chunking/caching/queue paths; run #16's `entity_match.py` and `gpu_lane.py` re-read;
**run #17's `read.py` progress/ETA reporting**.

**Not yet audited line-by-line** — pick from here: **`feats.py`** (still the highest-yield item —
the single largest source of swallowed failures in the tree, **1,007 `URLError` at
`feats.py:139`** and climbing, and nobody has read it), `address_space.py`, `profile.py`,
`burgs.py`, `tells.py`, `style_audit.py`, `audit.py`, `descending_ladder.py`, `cosmography.py`,
`genre.py`, `reference.py`, `resync_roll.py`, `retry_synthesis.py`, `build_terminal.py`,
`sweep.py`, `runguard.py`, `compress_store.py`. **`overnight.py` is now worth a first read** on
the run #16 principle inverted: it is the process that owns every job's lifecycle, it decides
what gets restarted and what does not, and run #17 found it letting the corpus read stay down
while the keeper noticed the publisher. **`standards.py` is still worth a RE-read** — it changed
in run #16, the whole opening diagnostic is computed from it, and §2 C is a question about its
arithmetic.

**Two overwatch HIGHs were refuted at source by run #14** — `cosmography._fmt` and
`descending_ladder.compton_confinement_energy`. **Do not spend on them again.**

## 5. Lessons worth keeping

- **Make the log name its DESTINATION, not just its action.** M13's code fix was correct,
  tested, and would have left the fault entirely in place. What found it was the one-line change
  beside it: `"synced 14 files, wrote docs/state.json"` was made to say **where**, and the next
  cycle confessed. **A report that names the action but not the object cannot expose a fault in
  the object.** This is the same family as m75 and the completeness catastrophe, seen from a new
  angle: not a measurement that cannot see, but a measurement that never says what it looked at.
- **Fix the class, then check whether the fix actually bound.** The TEMP fallback was the
  obvious cause and it was a real defect — and correcting it changed nothing, because the
  explicit variable was the live carrier. **Re-observe after fixing; do not infer from the diff.**
- **A pre-registered count turns a routine line into a finding.** "Exactly 2 preflight FAILs; a
  third is the finding" cost one sentence to write in run #16 and found 19 stranded entries in
  run #17.
- **The page's own staleness is a finding, and it is the first one.** A 37-minute-old
  `generated` stamp on a machine where the publisher is demonstrably alive is not a contradiction
  to explain away — both facts were true about two different repositories.
- **A live PID is not evidence of work.** The reader's log stopped 40 minutes before the reader
  did; `allsweep`'s `NOT RUNNING` line caught the death, but nothing caught the silence.
- **Verify the subagent, including when it says "I cannot determine this".** Run #17's agent
  refuted the hypothesis it was handed, which is worth more than confirming it, and then declined
  to explain a discrepancy it could not source. Both were correct behaviours; the unexplained
  discrepancy is still open.
- **Kill by PID, not by pattern.** A filter matching `*publish.py*` once matched the shell whose
  command line contained that text.
