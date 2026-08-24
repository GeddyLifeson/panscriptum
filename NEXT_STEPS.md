# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #12 wrote this on 2026-08-24 ~15:15 local.*

**Read this first.** Four things shape what is worth doing next run:

1. **THE SCHEDULE IS HOURLY (`11 * * * *`).** You should expect to be alone. If the overlap guard
   says a maintenance predecessor is live, that means a run hung — check the heartbeat age.
   **But the guard does NOT see interactive sessions.** Run #12 started one minute after an
   owner-directed session committed at 14:23, and that session was still probing the GPU at
   14:31. **Before you write anything, check `git -C C:\\Users\\imarl\\panscriptum-export log
   --oneline -5` and `ls -lt src/*.py | head` — if either shows activity in the last few minutes,
   you are not alone, and bouncing jobs or editing source is off the table.**
2. **THE BIG ONE IS M6: chapter generation refuses 100% of its calls.** 17,370 of 17,370, every
   job affected, *including a call with an empty user prompt* — the scaffolding alone is 8,086
   tokens against a 6,144 window. It is LATENT (generation waits on the omniverse history) and it
   is a BETTER failure than the silent truncation it replaced. **Do not treat it as closed
   because m46 is: the 14:23 session closed "m46/m52" as one item and only the feats half was
   fixed.**
3. **NOTHING RUNNING USES `gpu_lane` (m56), AND IT MUST NOT BE BOUNCED INTO SERVICE UNTIL m54 AND
   m55 ARE FIXED.** All nine standing jobs predate the code. Two latent defects in the lane would
   activate on the first restart, under exactly the load it exists to serve.
4. **The local rung was UNUSABLE during run #12** — a 5-arm `num_ctx` probe returned nothing in
   120 s on every arm, including the three at the resident size, with the card at 99%. Measure it
   again before routing work to it; the shape of the failure may have changed.

## 1. Verify first

1. **[m56 — is the new code live yet? One command, and it answers the whole question.]**
   Compare process start times against file mtimes:
   ```
   powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | Where-Object { $_.CommandLine -like '*panscriptum*' } | Select-Object ProcessId,CreationDate,CommandLine | Format-Table -AutoSize -Wrap"
   ```
   Anything started before **2026-08-24 14:20** is running pre-`gpu_lane` code. Corroborate the
   same way run #12 did rather than trusting the timestamps alone — if `gpu_lane.status()` reports
   0 slots while `nvidia-smi` reports high utilisation, the lane is arbitrating nothing:
   ```
   python -c "import sys;sys.path.insert(0,'src');import gpu_lane;print(gpu_lane.status())"
   nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv
   ```
2. **[M6 — has anything generated?]** Must stay near 6 while M6 is open:
   ```
   python -c "import json;d=json.load(open('output/index/catalog.json',encoding='utf-8'));print(len(d))"
   ```
   If it has moved, check `state/failures.json` for `ContextOverflow` entries — under M6 a
   generation attempt produces recorded failures, not prose, and that is the system working.
3. **[the local rung — two cheap facts, in this order.]** A trivial call at the resident size, and
   only then the split probe. **If the control fails, stop: you cannot measure the variable.**
   ```
   curl.exe -s --max-time 20 http://127.0.0.1:11434/api/ps
   nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv
   ```
   Then one `say ok` at the resident `num_ctx`. Only if that returns is a 4096-vs-8192 comparison
   meaningful. Note the pin is now explained: `OLLAMA_KEEP_ALIVE = -1` and
   `OLLAMA_MAX_LOADED_MODELS = 1` are user environment variables, so **the infinite expiry
   returns on every load no matter who issues it** — do not re-file that as a bug.
4. **[m59 — the cloud storm]** Is it still ~26 calls/minute at ~3%?
   ```
   python -c "import json,time,collections;now=time.time();c=collections.Counter();[c.update([(d.get('tag'),bool(d.get('ok')))]) for d in (json.loads(l) for l in open('state/model_metrics.jsonl',encoding='utf-8')) if isinstance(d.get('at'),(int,float)) and now-d['at']<=3600];print(c)"
   ```
5. **[m40 — CLOSED, do not re-open on a flat reading.]** Went **69/66 -> 70/66** during run #12.
   Only a number that goes DOWN is a bug.
   ```
   python -c "import json;d=json.load(open('data/OVERWATCH.json',encoding='utf-8'));print(d['rounds'],len(d['findings']))"
   ```
6. **[M4 — money]** Must print `598 False False True` (used, enabled, open, RETIRED):
   ```
   python -c "import sys;sys.path.insert(0,'src');import json,cascade_bridge as c;pb=json.load(open('state/PAID_BURST.json'));print(pb['used'],pb.get('enabled'),c.paid_lane_open(pb),c.PAID_LANE_RETIRED)"
   ```
7. **[m42 — hosts]** `WIKI_HOSTS.json` should still hold **202 bindings, 191 non-empty**, md5
   `451703b8…`. A DROP means a stale writer won.
8. **[m49 — the roster]** `allsweep` must report **nine** `running` lines. Held run #12. The same
   job NOT RUNNING on two consecutive runs is a real outage.
9. **[preflight's third FAIL is a thermometer, not a bug.]** "entries stranded in closed batches"
   is `batch_settled` waiting on model calls that time out. It was 4 (all in `Arcanum Worlds
   (Odyssey of the Dragonlords)#340`, which a 17-hour `ingest_doc` is still appending to). **If it
   is climbing, the saturation is getting worse; if it is 0, the rung recovered.**
10. **[run #11's unbounced entrypass fix]** Still not live — `pipeline.py` has not restarted since
    11:17. Same class as m56. verify_math §19q pins the source either way.

## 2. Human decisions needed (owner)

A. **[M6] Which remedy for the 100% chapter refusal?** The arithmetic is tight and only three
   levers exist: raise `num_ctx` to ~11,000-12,000 (median call needs 10,088 tokens, max 16,943 —
   a VRAM question on a 10 GB card, and **no longer blocked by M5**); trim the chapter system
   prompt from 18,112 chars to **~6,282**; or restructure what a chapter call carries. **Lowering
   `WRITE_CHUNK` does not work** — an empty user prompt refuses too. **Do not lower the reserve or
   raise `CHARS_PER_TOKEN` to make it pass** without measuring the real tokenizer ratio first;
   that reintroduces silent truncation wearing a safety margin's shape.
B. **[m54 + m55, and they are one decision] Fix the two `gpu_lane` defects, then bounce — in that
   order.** m54: call `_touch` from inside `lane()`'s hold, or shorten the leases to match real
   call durations. m55: route the six `os.remove` sites through a retry-with-backoff (the
   `replace_retry` pattern, adapted — that helper wraps `os.replace`, not `os.remove`). Then the
   restart order, cheapest first: **`overwatch` and `pipeline`** (keeper restores both within 5
   min — observed doing so at 11:17/11:22/11:37 today); **`foreman` LAST and carefully**, because
   m42 says bouncing it while it holds an `--adopt` child orphans a process that then writes
   `WIKI_HOSTS.json` from a stale snapshot; **`read.py` and `feats.py --roll` are NOT keeper-
   restored** and cost hours of downtime, so let them arrive on the supervisor's own lap; and
   **`ingest_doc` (Dragonlords) has no restarter at all** — it has been up 17 hours and is one of
   the three actual GPU holders.
C. **[the `OLLAMA_*` environment variables]** `OLLAMA_KEEP_ALIVE = -1` plus
   `OLLAMA_MAX_LOADED_MODELS = 1` is the pair behind "a call at a non-resident `num_ctx` never
   completes". Left untouched — they are machine-level and yours. Also: `OLLAMA_NUM_PARALLEL = 2`
   is the real source of truth for `gpu_lane`'s hardcoded `MAX_SLOTS = 2`; should the lane read it?
D. **[m59] Should a bucket that fails N consecutive LIVE calls stand down until the next proof,
   and should the proof measure a rate rather than a single answer?** 1,571 calls/hour at 2.8% is
   the free tier being hammered. Mind m24's paper trail on how easily a bucket gets buried.
E. **[m58] Is `folder-mechanical` routing provisional?** Races and Backgrounds are filed under
   "Places & Locations" across 42 sources. The shelfmark says `[UNCHARTED -- Ladder-of-Being pass
   not yet done]`, which suggests yes — in which case this is not a bug, and the answer belongs in
   the ledger so nobody files it again.
F. **[m57] The singulariser fix needs a corpus diff.** `catalogue_web.py:212` — 425 mangled types.
   Mechanical, but entry `type` feeds matching, so it needs a before/after diff of the whole
   corpus, which is a quiet-repo job.
G. **[the 240-char description truncation, run #11's item D]** `pipeline.py:992` truncates every
   entry description to 240 chars before the model judges it; 50.6% of ~82,000 entries are longer.
   Still a QUESTION, still unanswered, and **it is the same shape as M6 and m13** — an input cap a
   downstream verdict treats as authoritative.
H. **[m25 / m16 / dashboard `findings` cap of 12] — ONE ruling, four sites: does Hard Rule 0 bind
   diagnostics and run logs, or only reader-facing listings?** Carried since run #5. **"Does
   anything downstream act on the truncated list?" is the workable test.**
I. **[m51]** Should `check_context_budget` cover the generate path, or be renamed to say what it
   covers? **M6 makes this sharper: it prints `ok context budget` while 100% of chapter calls
   refuse.**
J. **[M4] The burst lane** — 598/500, retired structurally. Raise, delete, or leave as evidence.
K. **[m48] 70 sources collide under `_norm`**; **[m47]** what should a failed feats join look
   like; **[H]** the 17 stranded feats records (3 of them, 240 deeds, on hosts already bound —
   `entity_match` now names them with typed reasons and recovers zero, which is the correct
   answer); **[I]** the 87 hybrid Powers entries; **[J]** should feats be their own VOLUME.
L. **[m37]** Nothing reads `data/CHAIN.json`. **[M]** `GENRES.json` / `NAVTREE.json` have no
   automated writers. **[m29]** `cleanup.py`'s `_EMPTY_MECHANIC` predicate — exclusions are
   permanent, and note `batch_settled` now correctly treats an excluded entry as settled.
M. **[m26]** the completeness audit cannot see 46 of 210 sources. **[m39]** `scout.sweep(limit=4)`
   can starve lower-ranked hostless sources. **[m38]** `foreman._function_source` resolves symbols
   by bare name — `local_agent.find_symbol` is now the cheap half of this, and reports `main` has
   **74** definitions in `src/`. **[m12]**, **[m13]**, **[m30]**, **[M1]**, **[m43]** unchanged.
N. **Permanently hostless roll entries** — catalogued with no host **20**; on the roll but never
   catalogued **6**. The **91 DECIDED spine codes** from the 12:05 session are **still not written
   to `CHARTER_SPINE_CODES.json`**, which has no writer in `src/`. Rulings that never land in the
   charter appendix are erased on the next re-derive.
O. **`site/state.json` is two days stale (2026-08-22 15:23) and nothing in `src/` references
   `site/`** — the live artifact is `docs/state.json`, written by `publish.py`. Dead directory, or
   something's input? **No deletion without a ruling.**

## 3. Small implementable items (no decision needed)

1. **15 silent exception handlers** (`python src/silence.py`), up from 12 — the three new ones are
   `entity_match.py:255`, `overnight.py:491` (**inside the keep-warm loop, so a keep-warm that
   never works would be invisible**) and `local_agent.py:463`. Still open from before:
   `pipeline.py:321` records to `state/failures.json` but writes **nothing to
   `state/pipeline.log`**, the file an operator actually watches.
2. **`pipeline.py`'s 9 shared cross-phase JSON writes** still use raw `open+json.dump` rather than
   `_landed`/`replace_retry`. Medium surgery, 9 call sites, open since run #2.
3. **The three run #5 audit findings, still un-actioned**: `hostcheck`'s `judgeable` flag is
   ignored by its own two consumers; `onomast.coin_well_formed`'s fallback skips both its quality
   and uniqueness checks; `feats._unwrap_templates` miscounts brace nesting on `{{{`.
4. **`FEATS_BLOCK_CHARS = 20000` still exists as `pack_feats`'s default third argument.** The
   manifest path correctly derives the budget, so this only bites a caller that forgets to pass
   one — which is exactly the mistake both an audit subagent and run #12 made when *calling* it.
   Worth making the parameter required.
5. **`JOB_OVERHEAD_CHARS`'s comment does not reproduce.** It cites "min 314, median 1,193, max
   1,536 across 331 blocks"; a re-measure across 3,386 real blocks gives min 115 / median 142 /
   max 368. The constant (2,000) errs conservative so nothing is at risk — the comment is wrong,
   not the code.
6. **DONE, do not redo:** the 52,101-char manifest anomaly (run #12 — honest, three ~11.6 KB
   homebrew descriptions); the pyflakes warning (run #11, tree lints clean); m23's log truncation
   (fixed 14:23, verified at source run #12); the entrypass count mismatch (§19q); the `allsweep`
   roster (§19p).

## 4. Surface rotation for the next audit fan-out

**Run #12 spawned two sonnet subagents** on the two brand-new modules, and both surfaces are now
**covered**: `gpu_lane.py` with its three call sites (produced m54 + m55, and a clean bill on
dead-PID detection, handle management, atomic slot creation, `finally`-based release and call-site
consistency) and `context_budget.py` + `generate`/`manifest_builder`'s use of it (produced the
chapter-scope gap that became M6, plus a clean bill on Hard Rule 0 — **no deed, entry or block is
dropped or clipped anywhere on the feats path, verified against real data**).
**Both agents were partly wrong and both were caught by re-measuring** — see HANDOFF for which.

Covered, do **not** re-read unless the diff touched them: the round-1 full-codebase audit and
evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces; run #3's two; run #5's three; run
#6's four; run #7's five; run #9's `feats_index.py` and `hostcheck`; run #10's
`manifest_builder.pack_feats` + `generate.py`'s feats branch; run #11's `system_style.txt` and
`pipeline.py`'s `ask`/`ask_pool_first`/`phase_entrypass`; run #12's two above.

**Not yet audited line-by-line** — pick from here: `entity_match.py` (**new, and the only one of
the three new modules nobody has audited**), `address_space.py`, `profile.py`, `burgs.py`,
`tells.py`, `style_audit.py`, `audit.py`, `descending_ladder.py`, `cosmography.py`, `genre.py`,
`reference.py`, `resync_roll.py`, `retry_synthesis.py`, `build_terminal.py`, `sweep.py`,
`runguard.py`, and `compress_store.py`.
**Highest-yield:** **`read.py`'s `_ask` transport ladder** (`read.py:293-362`) — it is the caller
behind m59's 1,571 calls/hour at 2.8%, it owns `_GPU_DOWN_UNTIL` and the cascade/local fallback,
and **nobody has ever audited it** despite it being the busiest model consumer in the kit.

## 5. Lessons worth keeping

- **A fix in the source is not a fix in the system.** A Python process does not re-read its own
  file. Three separate "shipped" fixes were executing nowhere, and the test that catches it costs
  one command: **a process start time against a file mtime.** When a ledger says a fix landed, ask
  what is EXECUTING it.
- **A control that fails tells you nothing about the variable.** The `num_ctx` split could not be
  re-measured because all five probe arms failed, including the three that were supposed to
  succeed. That is not evidence the split is gone; it is the absence of evidence either way, and
  it must be written down as such rather than as "could not reproduce".
- **A surprising all-clear deserves the same suspicion as a surprising alarm.** `if not
  CB.fits(...)` reported 0 overflows out of 17,370 because `fits` returns a `(ok, measurement)`
  tuple and a non-empty tuple is always truthy. The correct answer was 100%. The clean result
  looked like good news and was a bug in the measurement.
- **Read the signature before calling the helper.** Two independent parties — an audit subagent
  and this run — made the identical error of passing `pack_feats`'s budget into its `source_name`
  parameter, and both got plausible-looking numbers back. A wrong argument rarely raises; it just
  quietly uses the default.
- **A check that certifies reachability is not a check on capacity.** The pool proof says 4 of 36
  buckets answer and it is true; the live rate is 2.8%. Same family as m51's `ok context budget`.
- **Closing two bugs as one item loses the half that is not fixed.** "m46/m52" were closed
  together; the feats half was genuinely done and the chapter half went from a silent truncation
  to a 100% refusal without anyone measuring it.
