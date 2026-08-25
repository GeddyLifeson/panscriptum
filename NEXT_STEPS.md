# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #32 wrote this on 2026-08-25 ~13:5x local.*

## 0. BEFORE ANYTHING

`python src/escalation.py --status` **alongside** the overlap guard. Run #32 ended with the
library **CLEAR** — the owner lifted run #31's false-alarm `DRILL_BREACH` at 13:15 and the drill
has run green since (116/116). **If you find a halt, that is the run's whole business.** You may
raise one; you may never lift one.

**THE OWNER RULINGS OF 2026-08-25 STILL SHAPE THE RUN.**

1. **EVERYTHING AMISS IS INVESTIGATED THE MOMENT IT IS SPOTTED** — worked on sight, never filed.
   What survives into this file is what needs an **OWNER RULING**, plus §2's verified tail, which
   is REAL WORK, not a backlog of excuses.
2. **THEN, IMMEDIATELY: THE FULL COMPREHENSIVE SWEEP — every line of every module, every run.**
   `python src/sweep_plan.py --batches 16`, one sonnet agent per batch, all launched together;
   each writes its full report to `handoff/sweep<N>/AUDIT_batchNN.md` and returns **only a compact
   summary**. Then `sweep_plan.missing("run<N>")` **proves** coverage.
   **Run #32's pass: 17 batches, 104 modules, 45,734+ lines, 0 uncovered, 17 reports (~300 KB).**
   **Launch the agents FIRST and work the immediate queue while they run** — runs #28–#32 all did,
   and every time the two converged on the same defect from opposite directions. Run #32's case:
   batch 02 read the discarded `land_json` verdict in source while I traced the same defect from
   `runguard._land:PermissionError` ×99 on the live page, inside the same ten minutes.
   **TELL EACH AGENT TO CALL `record()` ITSELF** — run #32 did and all 17 landed. Verify the
   report exists on disk before believing any coverage claim.
   **[NEW, RUN #32] RE-CHECK `missing()` AFTER the batches finish, not only before.** A module
   created mid-run is invisible to the partition and counted by the proof — that is how
   `binding_health.py` surfaced. Dispatch a closing agent for any straggler.
3. **AN UNRECOGNISED FAILURE IS A BUG, NOT WEATHER.** Still true. `mistral:free` and `github:free`
   are still unrecognised on the page.
4. **THE SAFETY LAYER BINDS YOU.** CLAUDE.md **Hard Rule -1**, MAINTENANCE.md **Rule Zero**.
   `drill.py` is part of the battery (**116 nets now**, must end `0 BREACHED`). **Never open
   `prose_enabled` or `step4_enabled`.** When you add a guard, add the attack that defeats it and
   **watch it go red once**.

## 1. NEEDS AN OWNER RULING — nothing below this line is a bug a run may decide

**A. [NEW, RUN #32 — ANSWER THIS ONE FIRST] WHO IS WRITING MODULES INTO `src/`?**
`binding_health.py` (256 lines, brand new, well-written, with a full docstring citing `maigret`
and `sherlock`) appeared at **13:35** on 2026-08-25. `cascade_bridge.py` was rewritten at
**13:37**. Both landed *during* run #32, after its own edits, and **nothing in `src/` imports
`binding_health` at all**. If this was you at the keyboard, say so here and it becomes routine. If
it was **not**, then something — the foreman's model-patch lane, `local_agent`, or a process
nobody is watching — is authoring whole modules into the tree unattended, and M42 (an unvetted
patch sitting in the live import path for ~900 s) is the mechanism to look at first.

**B. [M35, MEASURED AGAIN AND WORSE] The pool is at 21%, and it is one cause, not four.**
Live at 13:12: **38 calls / 15 min, 8 ok**. Only `nvidia:free` returned anything. **`groq` 0 of 8
and `gemini` 0 of 9 are NEW** and were not on M35's dead-four list (`zai`, `cohere`, `cloudflare`,
`hyperbolic`). Meanwhile the local `ask` metric reads **p50 835 s, p95 1356 s** — fourteen-minute
median latency on one 12288-context model at 98% GPU utilisation, with callers whose deadlines are
far shorter retrying into the same queue. **Three of the dead providers need an account action
only you can take.** The code-side halves stay routing-policy: Z.AI answers an empty account with
**HTTP 429** so the engine (in `C:\Users\imarl\cascade`, **a different repo**) files it as a
throttle; and `cascade_bridge`'s dead-provider bench is a **per-process dict** (batch 05 confirmed:
no cross-process persistence, though the plumbing to fix it — the `bucket_state` table in the
shared `SCRATCH_DB` — already exists unused *in the same file*), so ~15 processes each re-learn
the same dead providers.

**C. [NEW, RUN #32] TWO `llama-server.exe` PROCESSES SERVE THE SAME MODEL BLOB.**
Ports 65098 (pid 30004, started 01:34:17) and 51195 (pid 30988, started 01:37:09) — three minutes
apart, twelve hours ago. **Both answer `/health` OK**; 65098 still reports a loaded model via
`/props`; `ollama /api/ps` knows about **one** resident model (qwen3:8b, 7.95 GB). Card at
**9528 / 10240 MiB, 98% util**. **Run #32 did not kill it**: the arithmetic says the orphan is
probably holding little VRAM (9528 − 7954 ≈ 1.5 GB, and the desktop plausibly accounts for that),
so killing it is not obviously the fix for **B**, and killing a live model server unattended is not
a maintenance run's call. **Your action.**

**D. [M19] The reader throttles the whole pool through the GPU semaphore.** `local, 1 of 16
permits`. **Read B first — run #32's latency measurement suggests B is most of M19's cause rather
than a neighbour of it.** Note batch 05's correction: `gpu_lane`'s own `MAX_SLOTS=2` is deliberate
and local-only; the 1-of-16 belongs to `read.py`.

**E. [M20] The entrypass done-marker is a positional key.** `health --preflight` reports **874
stranded across four sources** — Mario 253, Gundam 227, Thomas 209, SpongeBob 185. **Unchanged
from run #29's 874, so the doubling has stopped**; it is no longer accelerating, but it is not
draining either.

**F. [M18 / batch 11's sharper reading] `axis_score()` returns a flat 9.9 at M10 — and `ledger.py`
is worse.** Batch 11 found `ledger.assay_to_standards` (`:127-134`) has **no** M10 guard at all:
`lo == hi` collapses the interpolation, so `joules` returns the M10 floor (1e99 J) for **every**
`ruin_score` 0–10, silently ignoring its own input. Two modules resolving one edge case two
incompatible ways, and neither matches the other.

**G. [M21] `action=raw` does not follow redirects.** Batch 09 located it exactly: `endpoint.py:186`
`raw_url()` is missing `redirect=yes`. dandwiki's 805 cached entries all hold `redirect SRD:<title>`
and the source has contributed zero evidence — still the standing `health --preflight` failure.
It touches the fetch path of every RAW host, hence a ruling rather than a patch.

**H. [M34] The assay disagrees with its own calibration ladder.** `anchors.py` prints INVARIANT
VIOLATED and `allsweep` now correctly reports it as an import-tier failure. **Batch 10 did the
analysis you need to rule on it:** Goku (5.42) < Yggdrasil (6.18) is almost certainly an **ORDER**
fault — Goku is anchored M5 and Yggdrasil M6 in the same file, so Yggdrasil's total is
mathematically guaranteed higher whatever the axis scoring does. A Sword (0.10) < Skate Guy (0.22)
is more likely a **SCORING** fault — both share anchor M0, and the Sword has 7 of 11 axes zeroed
(`NONE`) rather than excluded (`INAPPLICABLE`), unlike how `volition` was handled. **Two different
repairs meaning opposite things; the charter decides.**

**I. [carried] Is `rest[:14]` in `pipeline.synthesis_blocks` a cap or a decision?** Batch 02
**confirmed it as a real Hard Rule 0 cap** and added the argument that settles it: the sibling
`with_feats` branch **was already fixed for this exact defect (m13)**, so the file is now
inconsistent with itself. Changing it multiplies model calls across every feat-less source, so it
still wants a ruling — but the "it is defensible" reading is weaker than it was.

## 2. THE VERIFIED-BUT-UNREPAIRED TAIL FROM RUN #32'S SWEEP — this is work, not a backlog

**Findings I verified at source myself carry bug numbers (M37–M45, in BUGS.md).** Below are the
agents' credible findings with file and line, **unverified by me**. **Verify before fixing** — the
record shows agents are wrong in both directions, as are the supervisor's own hypotheses.

**Do first — the fail-open safeties, because they are the layer everything else trusts:**
- `ledger_guard.py:224` — `assert_intact()` discards `seal()`'s return and always returns True; and
  `seal()` itself swallows write failure via bare `except Exception: return None`. A failed
  chain-append still lets `publish.py:456` push as "ledgers intact". **Same shape as M29 and M36 —
  do all three together.**
- `drill.py:117-120` — the "COVERAGE.json unreadable" net never makes the file unreadable; both
  disjuncts resolve through the ordinary "source not in rows" path. **A net that cannot fail**,
  and it duplicates the net two lines above it.
- `drill.py:539-545,626-635,756-760,846-848,850,853,933-943` — **seven** nets whose attack is a
  substring check against source text rather than AST or execution. Batch 08 grep-confirmed that
  `"THERE IS NO PAID LANE"` exists **only in a comment** in `cascade_bridge.py:180`, so that net
  cannot detect its own stated regression. `:626-635` is the `escalation.clear()` caller check —
  defeated by any import alias, and note it lives in **drill.py, not verify_math.py**, contrary to
  what `escalation.py:33-34` and CLAUDE.md both claim.
- `hostcheck.py:80` (`_land`) — discards `replace_retry`'s return at **7 confirmed call sites**
  (591, 592, 598, 708, 731, 839, 906) while every caller prints success.
- `ingest_doc.py:293` — `P.write_record()` return discarded; the same file documents and avoids
  this exact bug 60 lines away.

**Hard Rule 0 — caps deciding answers, not displays:**
- `foreman.py:192` — `SC.sweep(limit=4)` ranks hostless sources then truncates to 4; ranks 5+
  starve permanently. Confirmed against `scout.py:237-241`.
- `feats.py:349-362` — `discover()`'s `aplimit=500`/`srlimit=50` never follow MediaWiki's
  `continue` token. **A live cap on evidence**, only counted, never fixed.
- `chain.py:108` — `unmatched.most_common(40)` truncates before writing into `CHAIN.json`.
- `genre.py:135-197` + `grounding.py:112-117,169-179` — both compute `confidence` over only the
  top 3 of 5 grounding types, inflating it (worked example: true 0.294 reported as 0.417) and
  masking genuinely contested cosmogonies from the `confidence < 0.5` flag.
- `scope.py:74,81` — `srlimit="3"` / `titles[:8]` in the **Magnitude-ceiling** path. Batch 14 reads
  these as defensible sampling; batch-level disagreement, so decide at source.
- `catalogue_models.py:158`, `dashboard.py:316`, `dashboard.py:377` — confirmed truncations.

**Dead code that the docstring says is working:**
- `onomast.py:268-334` — **traced definitively by batch 11**: the entire genre/feature-weighted
  register system is dead. `name_worlds()` (`:356`) only ever calls `register_for(continuity_group)`
  and `pipeline.py:1892` passes nothing else, so every world's register is still **pure
  `sha256` hash** — the exact bug the docstring claims was fixed.
- `custodes.py:267,290-357` — Threnody's veto is computed, never read, and its real path is gated
  on an `eta` the sole production caller (`anchors.py:190`) never supplies. *"The only standpoint
  that can refuse the output"* refuses nothing.
- `feats.py:377-425` — `resolve_title()`/`_page_exists()`, the documented fix for 17,148 mistitled
  entities, are **never called**. The defect is still live.
- `resonance.py` — the whole module is unimported by anything.
- `allsweep.py:74-80` — `NEVER_RUN` safety list referenced nowhere; zero actual protection.
- `escalation.py:55-56` — `class Refused` defined but never raised; rungs 1–2 (OPERATOR/SUPERVISOR)
  have no wired enforcement from this module.

**Concurrency:**
- `chain.py:354` — `unmatched[side[:40]] += 1` outside the lock under 8 workers, persisted into
  `CHAIN.json`. **Known, still open.**
- `hosts.py` `discover()`/`add()` — 6 workers doing read-modify-write on shared
  `SOURCE_HOSTS.json` with no lock; lost updates.
- `read.py:627,776-780` — TOCTOU on the cache write path, plus (`:777`) a hand-rolled untagged
  `tmp` in the same function where `_chunk_put` (`:607`) was already fixed this way.
- `identity.py:180-207` — `_is_continuity()`'s single-bearer branch is structurally unreachable
  behind the `n >= 2` gate, contradicting its own worked example.
- `snapshot.py:56-60` — second-granularity `sid` collision; two same-label `before()` calls in one
  second share a directory via `exist_ok=True`.

**Correctness:**
- `snapshot.py:109-116` — `verify()` byte-compares **files** but only `os.path.exists` for
  directories, so it can report "byte-identical" over a corrupted directory restore. **In the
  module whose whole job is proving backups trustworthy.**
- `cleanup.py:73-80` — the corruption guard wires `_SETTING_META` to literal `None`, a permanent
  no-op, while its comment promises three regexes.
- `overnight.py:180` — `running()`'s unanchored substring match: **`"sweep.py"` is a substring of
  `"allsweep.py"`**, so `foreman.run_character_sweep()` silently no-ops whenever allsweep runs.
- `overnight.py:496-510` — `coverage_snapshot()` never checks the subprocess return code.
- `publish.py` — bearer-token charset excludes `+` and `/`; vendor list omits `ghu_`/`ghr_`; and
  `scan_for_secrets` (`:290`) **skips any staged file over 2 MB** — batch 14 found **4 real files
  already over it**, no live secret today, but no warning is printed on skip either.
- `catalogue_web.py:99-103` — per-category fetch exceptions swallowed with `continue`; the source
  still shows `entry_count > 0` and is never retried. Permanent category loss.
- `address_space.py:251-252` — `fit()` modulo-wraps out-of-range tier indices, defeating `pack()`'s
  documented raise-rather-than-rename guarantee.
- `catalogue_aurora.py:140,150-165` — sources appended to `written` before the attempt and never
  removed on WRITE DENIED, so denied writes are summarised as successes.
- `thread_integrity.py:104-134` — DANGLING fires only at 100% drift; partial drift is absorbed.
- `silence.py:223-233` / `:290-327` — `digest_of` returns None for both "absent" and "unreadable"
  (so `expected_digest=None` can be fooled by a transient PermissionError into overwriting live
  data); `write_json` never fsyncs despite its docstring calling it "the one correct way".
- `sweep_plan.py:143-151` — the per-shard write **16 concurrent batches depend on** uses raw
  `os.replace` with no retry, alone among this file's writes.
- 9 stale `silence.note()` line labels (`overnight.py:318,360,385,503,521`, `chain.py:169,276,283,332`).

**The systemic one, still mechanical, still worth one batch with one check:** ~15 modules write
shared state with hand-rolled `path + ".tmp"` + bare `os.replace`. Confirmed this run:
`identity.py:210`, `magnitude.py:848,1050`, `coverage.py:78`, `withdraw_chapters.py:95`,
`publish.py:426-433`, `endpoint.py:83`, `worldseed.py:317`, `build_terminal.py:572`,
`manifest_builder.py:435`, `snapshot.py:74`, `dashboard.py:378`, `catalogue_web.py:75`,
`escalation.py:154`, `standards.py:1059`. **`scout.py:55` is REFUTED** — it does call
`replace_retry`; its issue is only the untagged tmp name. `burgs.py:225` is **worse than reported**:
a bare `open(p,"w")` with no atomicity at all.

## 3. STANDING LESSONS — 35 and 36 are new

26. **A LITERAL CANNOT TELL CODE FROM PROSE ABOUT CODE.** A check matching source text fails on an
    honest reflow and **passes on a comment**. Use the AST or exercise the code. Run #32 applied
    this to every net it added, and batch 08 found seven existing nets that violate it.
27. **A PATH IS A HYPOTHESIS TOO.** Absolute paths for everything; `git -C <dir>` for git.
28. **A SAFETY THAT STOPS WORK MUST BE TOLD APART FROM A FAULT THAT STOPS WORK** — and the fix must
    be carried to **every** file that makes the same inference.
29. **A PROCESS QUERY IS A HYPOTHESIS UNTIL IT MATCHES SOMETHING YOU CAN NAME.** Enumerate
    `python.exe`/`pythonw.exe` and match on the SCRIPT name; several jobs launch with a relative path.
30. **A CHECK THAT CANNOT FAIL LOOKS EXACTLY LIKE A CHECK THAT PASSED.** When you loosen a check
    that cried wolf, add the companion net proving it still refuses the real thing.
31. **VERIFY THE CADENCE WITH `list_scheduled_tasks`, NEVER FROM A FILE, INCLUDING THIS ONE.** The
    15 minutes in the overlap guard is the heartbeat-staleness threshold — a different number
    answering a different question. Do not "fix" it to match the cadence.
32. **AGE EVERY FILE A STANDARD READS — ESPECIALLY WHEN IT READS GREEN.** But a stale row is not
    proof the fault is stale: check the live table.
33. **BOUNCE WHAT YOU CHANGED.** **Run #32 changed `pipeline`, `verify_math`, `drill`.**
    `pipeline.py` (pid 57224 at the time) is the one that matters — it was mid-run on the old
    import. `dashboard`, `publish` and `foreman` import `standards`; nothing running imports
    `verify_math` or `drill` except foreman-dispatched jobs.
34. **THE SWEEP AUDITS THE SWEEP, AND THAT IS WHERE THE BEST FINDING KEEPS BEING.** Five runs
    running. #28: `record()`'s lost update. #29: `missing()` answering the wrong question. #31: the
    completeness check frozen on a hardcoded `"run29"`. #32: the partition is a **snapshot** while
    the proof is **live**, so a module born mid-run belongs to neither. Never exempt the instrument.
35. **[NEW, RUN #32] A CONTRACT STATED IN A DOCSTRING IS NOT A CONTRACT ANYTHING ENFORCES.**
    `_landed` returned its verdict and *said in words* that callers gate their done-keys on it.
    Twelve callers ignored it for as long as the sentence existed, and every one of them read as
    correct code. **When you write "the callers now do X", add the check that proves they do** —
    otherwise the docstring is the only thing that was fixed.
36. **[NEW, RUN #32] BUSY IS NOT WEDGED, AND MEASURING WHICH TAKES ONE NUMBER.** The local model's
    health probes were green and honest all run while `calibrate` failed for 3.6 h. The number that
    settled it was `ask` **p50 = 835 s** — not a wedge, a fourteen-minute queue with impatient
    callers. `standards.ollama_token_flow`'s "any completed call in 15 minutes proves flow" is
    **correct and should not be tightened**; the fault is downstream deadlines, not the probe.
