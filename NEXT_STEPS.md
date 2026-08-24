# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #8 wrote this on 2026-08-24 ~12:00 local.*

**Read this first.** Four things shape what is worth doing next run:

1. **fandom is still blocked at the socket.** Down across runs #5–#8. Nothing fandom-facing can
   progress until it answers, and it is not a code fault. The `health --preflight` FAIL *is* the
   outage, not a bug to fix. Same for the dandwiki cache FAIL (that one is M1, a decision).
2. **The scheduler fires faster than a run takes.** Run #8 started 2 minutes after run #7 closed
   its guard. Landing on a LIVE predecessor and exiting immediately is the correct outcome, not a
   failure. When you do get a legitimate run this close behind another, **the code diff will be
   nil and the value is in the queue below**, not in reading a diff.
3. **Run #8 found its two real bugs by listing processes and by running one command twice.**
   Neither came from reading code. Cheap, mechanical, repeatable moves — see item 4 and the
   rotation note.
4. **Nothing on the open list is a live data-loss risk right now.** Every remaining item is an
   outage, a decision, or a watched state. That is a change from run #7 and worth protecting.

## 1. Verify first

1. **[finish the m31 story — ONE command]** Run #7 fixed `ask_pool_first`; run #8 confirmed the
   fix FIRES in production (`state/pipeline_auto.log` 11:33:11, *"pool answered entrypass with an
   unusable shape; falling back to local"*), which also confirms run #7's diagnosis was right.
   What is still unmeasured is the CONSEQUENCE, because no batch had posted a result line yet:
   ```
   grep -oE "returned [0-9]+/[0-9]+" state/pipeline_auto.log | sort | uniq -c
   ```
   * Any non-zero numerator = **m31 is closed, end to end.** Say so and stop carrying it.
   * Still `0/20` *while* "unusable shape" lines exist = the pool path was NOT the only cause and
     something else eats batches. Top severity; do not assume the diagnosis a third time.
   * No `returned` lines at all = the pipeline still has not finished a batch; check it is alive
     (`pipeline.py` in the process list) before concluding anything.
   **Note `state/pipeline_auto.log` is truncated on every restart (m23)** — transcribe before
   bouncing anything.
2. **[m40 — did the merge hold?]** `data/OVERWATCH.json` should only ever grow. Check:
   ```
   python -c "import json;d=json.load(open('data/OVERWATCH.json',encoding='utf-8'));print(d['rounds'],len(d['findings']))"
   ```
   Run #8 left it at **rounds 68, 64 findings**. **A LOWER number either way means the merge is
   not holding and that is top severity** — it would mean a stale writer still wins. Also
   worth one line: `python -m pyflakes src/overwatch.py` and a look for the stderr string
   *"merged rather than replaced"* in job logs, which is the merge announcing it did its job.
3. **[m40 follow-on — look for orphans, it is one command]** This is the check that found the
   bug, and nothing in the kit does it automatically:
   ```
   powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'panscriptum' } | ForEach-Object { '{0} | {1}' -f $_.ProcessId, $_.CreationDate }"
   ```
   Anything hours old that is **not** one of the standing jobs (dashboard, publish, foreman,
   overwatch, pipeline, read.py, feats.py --roll, overnight, autostart) is a leftover from a dead
   session. Cross-check CPU time: a process with seconds of CPU over hours is blocked, not
   working. Run #8 killed one such orphan that was about to wipe the ledger.
4. **[m41 — are the nav names still stable?]** They are now supposed to be a fixed point:
   ```
   python src/navtree.py --write   # twice, then confirm the file is byte-identical
   ```
   Run #8 settled them once (146 of 734 names changed, structure untouched) and a second
   `--write` is a genuine no-op. **If names move again, the tie-break regressed** — verify_math
   §19n should catch it first.
5. **[M4 — money] Confirm the lane is still shut.** Unchanged for three runs at **598/500**:
   ```
   python -c "import sys;sys.path.insert(0,'src');import json,cascade_bridge as c;pb=json.load(open('state/PAID_BURST.json'));print(pb['used'],c.paid_lane_open(pb))"
   ```
   → must print `598 False`. **A counter that has grown past 598 means the fix is not holding
   and that is top severity.**
6. **The 149 struck entries** were last verified all `catalogued: True` in run #7 and were NOT
   re-checked in run #8. They will not un-flip themselves, but **read m29 before running
   `cleanup.py --apply`**, which is what would re-strike them, and which is still an open owner
   question.

## 2. Human decisions needed (owner)

7. **[M4] The burst lane** — 598/500, closed by the cap rather than by intent. Raise `cap`, set
   `enabled: false` (which genuinely works now), delete the file (now safe), or retire the lane.
8. **[m37 — now CONFIRMED, and the shape of the question has changed] Nothing reads
   `data/CHAIN.json`.** Verified repo-wide in run #8, not just `src/`: the only non-documentation
   occurrences are `chain.py:53` (the writer) and its own docstring. Every cycle persists the
   Bradley-Terry strengths and the Ford's-condition verdict, and the cross-check the module calls
   its entire purpose never runs against the Assay. **Either wire a consumer that performs the
   cross-check, or stop calling it a check and describe it as an archival record.** Not
   self-authorized in run #8 because inventing a consumer invents a contract.
9. **[NEW] Should `data/GENRES.json` and `data/NAVTREE.json` have automated writers?** Both are
   hand-run (`genre.py --write`, `navtree.py --write`) and both are the only bridge from their
   module into the running system. `NAVTREE.json` is the sharper case: it feeds
   `build_terminal.py`, `reference.py` and `sweep.py`, and `output/registry_terminal.html` is
   rebuilt continuously *from it* — so whatever it holds is served to readers on a loop whether
   or not anyone has regenerated it. `grounding`'s equivalent is called by `pipeline.py:1274`
   every phase and needs nobody. Either these join the phases, or the hand-run step is deliberate
   curatorial control and should be written down as such. **Run #8 regenerated NAVTREE.json but
   wired no job, because that changes a cadence.**
   *(Note: run #8 established that `profile.build_all` needs no such decision — it reads
   GENRES.json at runtime and persists nothing, so it is always current.)*
10. **[m29] `cleanup.py`'s `_EMPTY_MECHANIC` predicate** strikes on *empty description + name
    ending in* `variant|feature|trait|slot|...`. An empty description has repeatedly proved an
    unreliable signal here, and Loki *Variants* are real entities. Exclusions are permanent since
    run #6, so a wrong strike now sticks. Decide before `--apply` runs again.
11. **[m26] The completeness audit cannot see 46 of 210 sources** (`todo` filters on a
    fandom-only `subdomain(h)`). Measure the Wikipedia- and other-hosted sources, or rename the
    measure to say what it actually covers?
12. **[m25 / m16 / dashboard `findings` cap of 12] — ONE decision, three sites: does Hard Rule 0
    bind diagnostics and run logs, or only reader-facing listings?** Carried since run #5 and
    still the highest-leverage single ruling available. Run #7's data point stands: `FOR_OWNER.md`
    was capped at 3 URLs per blocked source and that was obviously wrong *because the listing fed
    a human decision*. **"Does anything downstream act on the truncated list?" is the workable
    test** — and run #8 is a case for the strict reading: `chain`'s `[:120]` dedup key looked like
    a harmless internal detail and was in fact deciding which contests existed.
13. **[m38] `foreman._function_source` resolves symbols by bare name, no uniqueness check** — it
    can hand the model lane the wrong same-named function and, with `--patch` live, overwrite it.
    Refuse an ambiguous symbol, or honour the class qualifier `overwatch` already emits?
14. **[m39] `scout.sweep(limit=4)`** can starve lower-ranked hostless sources forever — the
    ranking is deterministic and recomputed each round. Uncapping changes per-round load.
15. **[m24] `cascade_bridge.dead_forever`** buries buckets on `no such model` / `needs billing` /
    `bad key`, which its docstring's "permanent codes only" rule does not cover. **Still live:**
    run #8 saw `pipeline_auto.log` carrying `REMOVED local-gemma3-12b` and `REMOVED
    local-qwen25-14b`, both HTTP 404 for LOCAL ollama models that are simply **not pulled right
    now**. `ollama pull` restores them; nothing about that is permanent. Removals are in-memory
    per process and do not persist to `POOL_PROOF.json`.
16. **[m12] `thread_integrity.py`'s asymmetric/dangling detection is structurally unreachable.**
    Is it meant to compare implied threads against a separately-recorded DIRECTED thread graph it
    is not currently given? Not a one-line fix either way.
17. **[m13] `phase_synthesis`'s 14-entity ceiling sample** can clamp a whole source to a lesser
    band if the true strongest entity is not sampled. Raise, re-rank, or accept.
18. **[M1] dandwiki.com** — browser-UA HTML reader vs. owner-supplied text. Politeness/ToS call,
    open since run #1. The `health --preflight` cache FAIL is this decision, not a fault.
19. **[m23] job logs truncated on every restart** — bit runs #4 and #7. Fix is small (`"a"` plus a
    session separator, or rotate to `<job>.N.log`) but changes an operational convention and the
    dashboard's `_tail_match` readers assume one current file.
20. **[m30 follow-on] `custodes.convene` could report something real.** `covers_every_reading` is
    true by construction; the informative quantity — whether the **1.96·sd band alone** covered
    every reading — is invisible. A contract addition, not a repair.
21. **Permanently hostless roll entries** (Clockwork Angels, Twilight Imperium, HAWX, …) — stay on
    the roll as owner-supplied-text candidates, or come off? **Catalogued sources with no host is
    20** and *on the roll but never catalogued* is **6** (allsweep, run #8). Also the **91 DECIDED
    spine codes** from the interactive session are **still not written to
    `CHARTER_SPINE_CODES.json`**, which has no writer in `src/` — rulings must land in the charter
    appendix first or they are erased on the next re-derive.

## 3. Small implementable items (no decision needed)

22. **Grep for other hash-order tie-breaks.** m41 was `max(set(xs), key=xs.count)` — a tie
    resolved by *set iteration order*, which is randomized per process for strings. Run #8 fixed
    the two in `navtree.py` and **did not sweep the rest of the kit**. Start with
    `max(set(` / `min(set(` / `sorted(set(` and `next(iter(`, and treat any tie-break over a set
    of strings as suspect. A cheap way to test a whole module: run it twice with
    `PYTHONHASHSEED=0` and twice without, and compare a digest of the output.
23. **The three run #5 audit findings still un-actioned**, all deserving a second opinion:
    `hostcheck`'s `judgeable` flag is computed and respected by `standards.py` but **ignored by
    hostcheck's own two consumers**; `onomast.coin_well_formed`'s fallback **skips both its
    quality and uniqueness checks** (relevant to m41 — that is the same naming path);
    `feats._unwrap_templates` **miscounts brace nesting on `{{{`**.
24. **`src/deprecated/catalogue_local.py:244` — f-string with no placeholders.** The single
    pyflakes warning in the tree. Cosmetic, in a deprecated file; fix or delete the file.
25. **12 silent exception handlers remain** (`python src/silence.py`): silence.py ×5, health.py
    ×2, coverage.py, local_agent.py:339, pipeline.py:1531, publish.py:161, standards.py:797.
    Run #8 closed one (its own, caught by the audit before shipping). These are pre-existing; each
    can turn a failure into a plausible negative result.

## 4. Surface rotation for the next audit fan-out

**Run #8 spawned no subagents** — the queue held enough verified concrete work that a fan-out
would have been invented work. So the rotation list is untouched and is the right place to spend
a run that arrives with a real diff.

Covered, do **not** re-read unless the diff touched them: the round-1 full-codebase audit and
evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces; run #3's two; run #5's three
(assay/magnitude/identity; hostcheck/scout/tuning/compress_store; read/feats/estate/worldseed/
onomast); run #6's four (health/overwatch/silence; catalogue_web/backfill/cleanup;
custodes/tiers/sevenfold/grounding; cascade_bridge's widen/paid path); run #7's five
(address/completeness/foreman; chain/module_index/local_agent/pick_model).

**Not yet audited line-by-line** — pick from here: `address_space.py`, `profile.py`, `burgs.py`,
`tells.py`, `style_audit.py`, `audit.py`, `descending_ladder.py`, `cosmography.py`, `genre.py`,
`reference.py`, `resync_roll.py`, `retry_synthesis.py`, `build_terminal.py`, `sweep.py`, and
**`pipeline.py`'s `ask`/`ask_pool_first`/`phase_entrypass` as they now stand after run #7**, plus
`runguard.py`. Note **`navtree.py` and `onomast.py` are now interesting together** — m41 was in
the first and item 23's fallback finding is in the second, on the same naming path.

## 5. Lessons worth keeping

- **Diff it twice before you believe a diff.** Run #8 nearly recorded 168 changed nav names as
  "run #7's genre fix reaching production". It was a coherent story with real evidence behind it.
  Running the identical command a second time showed 75 *more* names changing with identical
  inputs, which meant the names were random, not stale. **A single diff cannot distinguish
  "changed because of my fix" from "changes every time."**
- **A comment asserting determinism is not evidence of determinism.** Two separate docstrings on
  the m41 path promised stable, reproducible names. Both were sincere; both were false. Prefer
  running the thing twice over reading what it says about itself.
- **The dangerous writer is the one that has been away.** m40's orphan and m41's tie-break are
  the same shape: acting on a stale or arbitrary picture and writing the whole thing back. When a
  save is a whole-file replace, ask what else could have written that file since it was read.
- **"Only one module writes this file" does not mean one writer** — it means one code path, and a
  code path can be live in several processes at once.
- **Check for orphaned processes from previous sessions.** Nothing in the kit does. Every
  maintenance run that leaves a long foreground call behind creates one, so this is a habit rather
  than an accident, and it costs one command to check (item 3).
- **An audit subagent can be right about everything.** Standing advice says to expect them right
  about WHERE more often than WHY. Run #8 verified all four of m37's claims against source and
  **all four were correct, WHERE and WHY.** Verify every finding — but record the score honestly
  in both directions, or the advice slowly becomes a reason to dismiss good work.
- **Run the linter and the silence audit even on your own fix.** The silence audit caught a silent
  `except` introduced *by the m40 merge, in this run*, before it shipped.
