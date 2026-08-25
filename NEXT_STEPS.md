# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #16 wrote this on 2026-08-24 ~19:35 local.*

**Read this first.** Four things shape what is worth doing next run:

1. **THE SCHEDULE IS EVERY 15 MINUTES (`11,26,41,56 * * * *`), so you will routinely land on a
   live predecessor and that is the designed steady state.** The guard exits in seconds. It does
   **NOT** see interactive sessions — before writing anything, check
   `git -C C:\Users\imarl\panscriptum-export log --oneline -5` and `ls -lt src/*.py | head`.
2. **THE BIGGEST OPEN ITEM IS NOT A BUG, IT IS AN UNREALISED ASSET. [M12]** The live manifest
   holds **zero feats chapters** while the feats join is healthy — **100 of 210 sources, 1,215
   entity blocks, 55,372 mined feats** — because the manifest was built at 10:41, before the
   reader produced them. Nothing reports a fault: `generate.py` is running and correct, writing
   books from a manifest in which that chapter does not exist. **§2 A is the decision.**
3. **THE PAGE'S `machine` GROUP CAN REPORT A FAULT THAT NO LONGER EXISTS.** Run #16 opened on
   `publish.py x2` and a 35-minute-silent `pipeline_auto`; both had already been restarted by
   the supervisor, and the snapshot was **11.5 minutes stale** when read. The page is still the
   right opening diagnostic — **but confirm a machine breach against the live process list
   before acting on it.** The pool, read, and library groups do not have this property.
4. **RUN #16 CHANGED `gpu_lane._BEAT_SECONDS` FROM 300s TO 100s.** Every held lease is now
   refreshed three times as often. The write is tiny and the correctness argument is in
   BUGS.md [M11], but it is a real change in file-write frequency under contention: if
   `state/lane/` shows anything odd next run, start there.

## 1. Verify first

1. **[M11 — did the foreground fix take? The cheap live check.]** `generate.py` is the only
   `priority=True` caller. While it is running:
   ```
   python -c "import sys,json;sys.path.insert(0,'src');import gpu_lane as G;print(json.dumps(G.status(),indent=1))"
   ```
   Expect a `foreground` row whose `age_s` stays **under ~100** and never climbs past 300 while
   its holder is `alive: true`. **An `age_s` past 300 on a live holder means the beat thread is
   not running** — the same symptom m54 was diagnosed by, now on the claim rather than the slot.
   Note this only proves itself on a call longer than the beat; short calls rewrite the claim at
   entry anyway, which is exactly why the defect survived so long.
2. **[m75 — is the page telling the truth about the pool now?]** The `calls that succeed` line
   should read either `UNMEASURED -- N call(s) ...` or `NN% ok of N`. **It must never again
   print a bare `100% ok`.** If it reads UNMEASURED, that is not the bug returning — it means
   the pool is being asked fewer than 20 times per 15-minute window, and `model calls per hour`
   is the line to work.
3. **[THE POOL IS THE STANDING RED AND NOBODY HAS WORKED IT YET.]** Run #16 fixed how it is
   *reported*, not the pool itself. At read time: **20 calls/hour against a floor of 900**, with
   **18 buckets holding headroom, 38% dry, none pinned at rpm 1** — three of the four sub-standards
   HOLD. Per the standard's own order text, that combination means **the reader is not asking**,
   not that the pool is refusing. `cascade:coding` shows `ok_pct: 5` over n=1912. **This is the
   highest-value unexplored diagnosis in the tree.** Start at: does `read.py` resolve its
   transport to Cascade, and does its worker count match the bucket count?
4. **[the regime is on a knife edge]** `regime()` reads `cloud` — "4 answering; **35% ok over 40
   calls**". `CLOUD_MIN_SUCCESS` is **0.35**. It is sitting exactly ON the threshold, not above
   it. Expect flapping; if it flaps, that is the finding, and the knobs are named in §2 I.
5. **[M8 — is fandom back? Four seconds, TCP only.]**
   ```
   python -c "import sys;sys.path.insert(0,'src');import standards as ST;print(ST.fandom_ipv4_reachable())"
   ```
   Run #16 got `(False, '162.159.142.170 TimeoutError')` in **16.0s**. **Read the latency, not
   just the boolean**: a slow False is a block; a fast False (<1s) is a third answer meaning
   something new is wrong. **The edge IP rotates** (172.66.2.166 → 162.159.142.170); the IP
   changing is not itself news.
6. **[m65 — bounce the foreman ONLY when §1.5 says fandom is back, and check the child first.]**
   ```
   powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*adopt*' } | ForEach-Object { '{0} parent={1}' -f $_.ProcessId, $_.ParentProcessId }"
   ```
   A child under the foreman's PID means **DO NOT BOUNCE** — the orphan rewrites `WIKI_HOSTS.json`
   from a stale snapshot. Run #16 saw pid **48832 under 5420** and left it alone. The foreman is
   still the one job running pre-run-#15 code.
7. **[M9 / M4 — both confirmed closed, one line each, keep them cheap.]**
   `40,884 rows -> 40,884 queued` (must be EQUAL) and `598 False False True`.
8. **[preflight — still exactly 2 FAILs]** `API paths per host family` (**M8**) and
   `feats/www_dandwiki_com` (**M1**). **A THIRD FAIL is the finding.**
9. **[ANSWERED — stop re-investigating these.]** **§2 H / m56**: the lane IS arbitrating —
   `status()` shows real leases with live holders, not `slots: []`. **The `every source is fully
   catalogued` UNMEASURED HIGH**: all 164 rows are `*.fandom.com`, every one short-circuits at
   `host_reachable()` with `probes_run: 0`, deliberately. It is 100% downstream of M8 and will
   read UNMEASURED until fandom answers. **That is correct behaviour, not a bug.** **The keeper**:
   healthy, answered three times over.

## 2. Human decisions needed (owner)

A. **[M12 — THE BIGGEST ITEM. Rebuild the manifest?]** Zero feats chapters in an 88 MB manifest
   feeding a live `generate.py`; the join is healthy and would now produce **1,215 entity blocks
   across 100 sources**. Rebuilding underneath a running prose job is a decision, not a repair —
   and note `manifest_builder`'s `content_hash` means a rebuild correctly marks changed jobs
   stale rather than redoing everything. **Say whether to rebuild, and whether to stop `generate`
   first.**
B. **[M8 — the only one blocking real work] Is the fandom IPv4 outage a block we earned, or a
   network fault between here and Cloudflare?** All fandom content hosts share two Cloudflare
   IPv4 addresses and both time out; the same edge answers instantly over IPv6; other IPv4
   destinations are fine. **Forcing IPv6 to get around it is a decision only you can make**, and
   runs #14, #15, #15b and #16 all deliberately declined to take it.
C. **[NEW, run #16] `FEATS_BLOCK_CHARS` is now referenced by nothing but its own comment.**
   With `pack_feats`'s default removed (§3.3, closed), the constant is live only as documentation
   of a real measurement (Warhammer 40,000, 106 blocks, median 20,464, max 21,993). **Delete it,
   or keep it as the measurement of record?** Kept for now — deletions need a review cycle.
D. **[NEW, run #16 — a diagnostic that reports 8 failures from 0 attempts.]** In
   `completeness.py`'s host-unreachable short-circuit, the row carries
   `probe_failures: len(probes)` = **8** alongside `probes_run: 0`. Nothing was attempted, so
   "8 failures" is a count of probes *not run*. `probes_run: 0` makes it decodable and the
   measured path is unaffected, so this is **diagnostic-only** — but it is a number people
   reason from, and it is the same family as §2 E below. Rename, zero it, or leave it?
E. **[m54's cost — confirm the trade.]** `_BEAT_SECONDS` 300s → **100s** means every held lease
   is rewritten 3× as often under contention. Correctness argument in BUGS.md [M11]; the cost is
   small file writes. **Say if you want the beat derived differently** (e.g. per-lease threads at
   per-lease intervals) rather than one thread on the shortest lease.
F. **[carried — the `read.py` audit's five questions, unchanged and still open.]** Chunking has
   **no overlap** so a feat sentence straddling a boundary is unrecoverable and re-runs lose the
   identical sentences forever; **two different "own page" tests** disagree on curly apostrophes;
   **`chunks_skipped` is arithmetically wrong for multi-page entities** (floors one division over
   a concatenated total where the loop is per page); a **stale comment describes a `cap_chunks`
   safety net that is inert** (default `None` everywhere — so there is currently no bound at all
   on one entity's GPU time, which is Hard Rule 0 working as intended, but the comment reads as
   reassurance that is no longer true); **`chunks_reused` is computed and thrown away**, so the
   chunks/s rate and ETA mix instant cache hits with real model calls.
G. **[M10's cost — still worth confirming.]** Entity-scoping the chunk cache orphaned **8,194**
   cached answers (not deleted — just no longer found). Run #15b judged a smaller-but-wrong
   library the worse outcome. **Say if you disagree**, because the re-read cost lands on an
   already-contended card.
H. **[§2 I from run #15 — the cloud worker floor.]** `tuning.py`'s `max(4, min(16, n + 2))` still
   floors at 4, so a *stale* `"cloud"` label can pair with `n = 0` to give 4 workers against a
   dead pool. The rate check makes this much harder to reach; the floor itself is unchanged and
   still documented as deliberate.
I. **[§2 J from run #15 — compounding cache TTLs.]** `tuning.RECHECK_SECONDS=180` and
   `read.GATE_RECHECK_S=120` run on independent clocks, so the gate width can be up to **240s**
   stale rather than the 120s its constant implies. Verified as arithmetic, **not instrumented
   live**. Also `read.py`'s `_GATE_STATE` defaults to `"cloud"` — open-wide before the first refresh.
J. **[m60] Which trade for the last 22 oversized chapter blocks?** Largest **46,840** chars
   against a p99 of 11,978. **[m51]** Should `check_context_budget` cover the generate path?
   **[M4]** The burst lane — 598/500, retired structurally: raise, delete, or leave as evidence?
K. **[the 240-char description truncation]** `pipeline.py` truncates every entry description to
   240 chars before the model judges it; 50.6% of ~82,000 entries are longer. **Same shape as M6,
   m13, M9 — and now as m75**: a measurement a downstream verdict treats as authoritative.
L. **[m25 / m16 / dashboard `findings` cap of 12] — ONE ruling, four sites: does Hard Rule 0 bind
   diagnostics and run logs, or only reader-facing listings?** Carried since run #5. **"Does
   anything downstream act on the truncated list?" is the workable test.**
M. **[NEW, run #16 — `entity_match.py` is a complete module with zero production callers.]**
   Confirmed repo-wide: the only importer is `verify_math.py`, testing it against itself. Its
   header describes recovering the ~240 stranded DC deeds; nothing ever invokes it to do so.
   Run #16 fixed its contract and its docstrings (m76, m77) so it is *correct* dead code.
   **Wire it in, or retire it?** Per the project's own lesson, a function that exists and is
   never called is worse than one that is missing.
N. **[m58] Is `folder-mechanical` routing provisional?** **[m57]** The singulariser fix needs a
   corpus diff (`catalogue_web.py:212`, 425 mangled types). **[m48]** 70 sources collide under
   `_norm`. **[m47]** what a failed feats join should look like; the 17 stranded feats records;
   the 87 hybrid Powers entries. **[m37]** Nothing reads `data/CHAIN.json`. **[m29]**
   `cleanup.py`'s `_EMPTY_MECHANIC`. **[m26]** the completeness audit cannot see 46 of 210
   sources. **[m39]** `scout.sweep(limit=4)` can starve lower-ranked hostless sources. **[m38]**
   `foreman._function_source` resolves symbols by bare name (`main` has 74 definitions).
   **[m12]**, **[m13]**, **[m30]**, **[M1]**, **[m43]** unchanged.
O. **[the stale local buckets]** The reader still logs `REMOVED local-<model>: HTTP 404` across
   the pruned models on every start (`gemma3:12b`, `qwen2.5:14b` seen again this run).
   Self-healing per process; the roster lives outside `src/`. Confirm the prune was intentional.
P. **Permanently hostless roll entries** — catalogued with no host **20**; on the roll but never
   catalogued **6**. The **91 DECIDED spine codes** are **still not written to
   `CHARTER_SPINE_CODES.json`**, which has no writer in `src/`. Also **34 catalogued sources have
   no charter spine code**, and three charter errata are open (Supercluster, Filament, Hyperverse
   are rungs with no Magnitude band).
Q. **`site/state.json` is stale and nothing in `src/` references `site/`** — the live artifact is
   `docs/state.json`. Dead directory, or something's input? **No deletion without a ruling.**
   Also: **2 cache directories no source points to** (`feats/jojo_fandom_com`,
   `feats/www_dandwiki_com`), reported by `allsweep` — same question, same rule.

## 3. Small implementable items (no decision needed)

1. **`pipeline.py`'s 9 shared cross-phase JSON writes** still use raw `open+json.dump` rather
   than `_landed`/`replace_retry`. Open since run #2 and now **the last member of its family** —
   m62, m74 are fixed, and `silence.append_line` plus the per-writer temp-name pattern are both
   in the tree as models.
2. **`gpu_lane._write_claim` and `_touch` use a bare `os.replace`, not `silence.replace_retry`.**
   Raised by the run #16 audit and **verified**: `_remove_retry` in that same file cites the
   Windows rename-denied race (m55) as its own justification, so the module already knows the
   hazard and two of its writers do not use the remedy. Slots have a 3× beat margin that absorbs
   one miss; **a new foreground claim's FIRST write has no such cushion.**
3. **35 silent exception handlers** (`python src/silence.py`). **Run #16 added net zero** — one
   was introduced and converted before landing. **The audit reads the AST, so a `#` comment does
   NOT satisfy it**; the idiom is a string (`_ = "silence-exempt: ..."`). Concentration:
   **`gpu_lane.py` 13** and **`context_budget.py` 4** (246, 252, 265, 270 — fallback-to-empty-string
   when a prompt file cannot be read, which would generate against an EMPTY system prompt rather
   than fail). Also open: `entity_match.py:272`, `overnight.py:500` (**inside the keep-warm
   loop**), `publish.py:161`, `coverage.py:92`, `pipeline.py:1570`, `foreman.py` ×2,
   `health.py` ×2, `local_agent.py` ×2, `standards.py` ×2.
4. **`gpu_lane._alive` contradicts its own documented policy.** Its docstring says "unknown
   answers are treated as ALIVE, deliberately... guessing 'dead' would let two callers into one
   slot"; an unparseable `pid` returns `False`. **Verified.** Only reachable via external/manual
   corruption of a lane file, but it is a direct comment-versus-code mismatch of the class that
   has produced this project's last three majors.
5. **`JOB_OVERHEAD_CHARS`'s comment does not reproduce, AND could not be re-measured this run.**
   It cites "min 314, median 1,193, max 1,536 across 331 blocks"; run #15b's re-measure across
   3,386 blocks gave min 115 / median 142 / max 368. **Run #16 could not independently confirm
   either figure — the live manifest contains no feats jobs at all (see M12), so there was
   nothing to measure.** The constant (2,000) errs conservative either way. **Fix the comment
   only after M12 is resolved**, when real feats jobs exist to measure again.
6. **`_HAS_ACTION`'s verb list may have recall gaps** (audit, **still unverified**): "vaporiz-",
   "annihilat-", "incinerat-", "smash", "explod-", "shred", "stun", "wound" are absent. A chunk
   whose only feat verb is missing is skipped before the model sees it. Honestly accounted in
   `chunks_skipped`, so not hidden — but nobody has measured the false-negative rate.
7. **`entity_match.candidates()` recomputes `split_qualifier(name)` inside its pool loop** rather
   than once before it, against a pool of up to 85,968 names. Performance only, no correctness
   effect. Low priority while the module has no callers (§2 M).
8. **DONE, do not redo:** M11, m75, m76, m77 and §3.3 (run #16); M9, M10, m54, m55, m62, m70–m74
   and the regime rate-gate (run #15b); m66–m69 (run #15); m63, m65 (run #14); m64; M8's
   *standard* (§19z/§19aa — **the outage itself is open**); m61 (§19s); the M7 gate fix (§19t).
   **Also settled and not to be re-derived:** a timed-out chunk is **deferred, not lost**;
   `hostcheck`'s `judgeable` flag **is** consumed at `standards.py:571`; the lane **is**
   arbitrating (§2 H closed); the completeness UNMEASURED HIGH is **downstream of M8, not a bug**.

## 4. Surface rotation for the next audit fan-out

**Run #16's two subagents both paid.** `entity_match.py` returned six findings — two survived as
fixes (m76, m77), one became the design question in §2 M, three were confirmed-but-minor.
`gpu_lane.py`'s **re-read found the run's most serious defect (M11)** in a file audited only
four runs earlier, because it had *changed since*. **That is the transferable result: re-auditing
a recently-modified hot file beat auditing a cold unaudited one.**

Covered, do **not** re-read unless the diff touched them: the round-1 full-codebase audit and
evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces; run #3's two; run #5's three;
run #6's four; run #7's five; run #9's `feats_index.py` and `hostcheck`; run #10's
`manifest_builder.pack_feats` + `generate.py`'s feats branch; run #11's `system_style.txt` and
`pipeline.py`'s `ask`/`ask_pool_first`/`phase_entrypass`; run #12's `gpu_lane.py` and
`context_budget.py`; run #13's `read.py` transport ladder; run #15's `tuning.py`; run #15b's
`read.py` chunking/caching/queue paths; **run #16's `entity_match.py` and `gpu_lane.py` re-read**.

**Not yet audited line-by-line** — pick from here: **`feats.py`** (now the highest-yield item —
it is the single largest source of swallowed failures in the tree, **678 `URLError` at
`feats.py:139`**, and nobody has read it), `address_space.py`, `profile.py`, `burgs.py`,
`tells.py`, `style_audit.py`, `audit.py`, `descending_ladder.py`, `cosmography.py`, `genre.py`,
`reference.py`, `resync_roll.py`, `retry_synthesis.py`, `build_terminal.py`, `sweep.py`,
`runguard.py`, `compress_store.py`. **`standards.py` is worth a RE-read** on the run #16
principle — it changed this run, it is the file the whole opening diagnostic is computed from,
and m75 proves its arithmetic has not been read closely.

**Two overwatch HIGHs were refuted at source by run #14** — `cosmography._fmt` and
`descending_ladder.compton_confinement_energy`. **Do not spend on them again.**

## 5. Lessons worth keeping

- **Fix the class at the site where it was first named — then check the site next door.** m54's
  own docstring reasoned that "every prose call outlives its own lease", fixed the slot, and left
  an identical lease *three times shorter* unrefreshed twelve lines away. The second defect was
  not hidden. **It was described, in the fix for the first one.**
- **A guard against one failure can manufacture the opposite one.** `max(calls, 1)` existed only
  to prevent a division by zero and, by doing so, turned an unanswered pool into a clean "100%
  ok". **Ask what a defensive default REPORTS when it fires, not just what it prevents.**
- **Re-auditing a changed hot file beat auditing a cold one.** `gpu_lane.py` had been audited
  four runs earlier; it had changed since, and it yielded the run's only Major.
- **Both new majors were found by reading code against its own comment** — the third run running
  that this method has produced the headline finding.
- **Verify the test harness before believing the result.** This run twice measured "0 feat rows
  for every source" and twice the harness was wrong (an empty `record`, then a tuple unpacked as
  a path). The third attempt showed a **healthy** join. **A shocking measurement is a reason to
  check the instrument first** — the real finding (M12) was next door and quieter.
- **Liveness is not progress, and neither is a green standard.** `allsweep` reported 0 subsystems
  bad while the manifest quietly contained no feats chapters at all.
- **A fast failure and a slow failure are different findings.** The fandom probe's **16.0s**
  False is what confirms M8 is still a block rather than something new.
- **The page can be stale, and its machine group can report a fault that has already healed.**
  Confirm a machine breach against the live process list before acting on it.
- **Test the test.** Every regression check added this run was confirmed FAILING against the
  pre-fix behaviour first. A check that passes before the fix is decoration.
- **Kill by PID, not by pattern.** A filter matching `*publish.py*` once matched the shell whose
  command line contained that text.
