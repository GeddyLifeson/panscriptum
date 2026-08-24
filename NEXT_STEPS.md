# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #9 wrote this on 2026-08-24 ~12:30 local.*

**Read this first.** Four things shape what is worth doing next run:

1. **Bouncing a job makes an orphan.** Run #9's main find (m42) was created by run #8's own fix:
   the keeper restarted the foreman, and the foreman's in-flight child outlived the process that
   was supposed to kill it. **If you bounce anything this run, check for its orphaned children
   before you close out.** Item 2 below is one command and it has now found a real problem twice.
2. **The local model rung is up but SATURATED — do not diagnose it as broken.** Run #9 measured
   it: one model (`qwen3:8b`) serves every job, a trivial call in the kit's shape got no answer in
   240s, and a bare `/api/chat` took 32.6s wall for **28ms of compute**. The foreman's *"GPU busy
   and no spare pool capacity"* is **accurate reporting, not a swallowed error.** Do not "fix" it.
   The lever, if you want one, is item 9 — more installed models, or less contention.
3. **fandom is still blocked at the socket,** runs #5–#9. Both `health --preflight` FAILs are the
   known outages (M3 fandom, M1 dandwiki). The FAILs *are* the outage; neither is a bug to fix.
4. **Nothing on the open list is a live data-loss risk right now.** m42's instance is closed and
   the ledger was verified untouched. Everything remaining is an outage, a decision, or a guard.

## 1. Verify first

1. **[m42 — the orphan check, ONE command, run it EARLY]** This found the run's main bug and
   nothing in the kit does it automatically:
   ```
   powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'panscriptum' } | ForEach-Object { '{0} | parent={1} | {2}' -f $_.ProcessId, $_.ParentProcessId, $_.CreationDate }"
   ```
   **The parent PID is the part that matters** — run #9 added it for this reason. A `panscriptum`
   python process whose **parent no longer exists** is an orphan by construction: nothing will
   ever kill it, its timeout can never fire, and its output goes to a pipe with no reader. Confirm
   a suspect parent is really gone before killing anything. Cross-check CPU: seconds of CPU over
   hours means blocked, not working — but **network-bound work also looks like that**, so check
   for live sockets before concluding (run #9 nearly mis-called a healthy process this way; a
   `SynSent` connection to Cloudflare proved it was working, just doomed by M3).
   Standing jobs, for comparison: dashboard, publish, foreman, overwatch, pipeline, read.py,
   feats.py --roll, overnight, autostart. A `hostcheck --adopt` whose parent is the LIVE foreman
   is legitimate; one whose parent is dead is not.
2. **[m42 — did the guard get built, and did anything land?]** If a later run patches `_land`,
   confirm `WIKI_HOSTS.json` still holds **202 bindings, 191 non-empty** (md5 `451703b8…` as of
   12:20 today, unchanged since 08:55). A DROP in either number means a stale writer won.
3. **[m31 — STILL OPEN, and run #9 could not close it either]** Unchanged from run #8's queue:
   ```
   grep -oE "returned [0-9]+/[0-9]+" state/pipeline_auto.log | sort | uniq -c
   ```
   As of 12:20 there are **no `returned` lines at all** and the log has not been written since
   **11:52**. `pipeline.py` is alive (PID 3056). So the *consequence* of run #7's `ask_pool_first`
   fix is **neither confirmed nor refuted** — do not record it as either. The fix itself IS
   confirmed firing (two *"unusable shape"* lines). Given item 2 of the preamble, a batch may
   simply not be completing while one model serves every job.
   **`state/pipeline_auto.log` is truncated on every restart (m23)** — transcribe before bouncing.
4. **[m40 — the merge]** `data/OVERWATCH.json` should only ever grow:
   ```
   python -c "import json;d=json.load(open('data/OVERWATCH.json',encoding='utf-8'));print(d['rounds'],len(d['findings']))"
   ```
   Run #8 **and** run #9 both read **68 / 64**. A LOWER number either way is top severity. Note
   it has not GROWN across either run, which is consistent with overwatch being starved by item 2
   of the preamble rather than with a fault — but if it is still 68 next run, read
   `state/overwatch.log` before assuming that.
5. **[m41 — nav names]** Now verified twice. `python src/navtree.py --write` twice, then confirm
   `data/NAVTREE.json` is byte-identical (md5 `1cbb6657…`). Run #9 got three identical digests
   across separate processes. **If names move again, the tie-break regressed** — verify_math
   §19n should catch it first.
6. **[M4 — money]** Must print `598 False`; flat for four runs:
   ```
   python -c "import sys;sys.path.insert(0,'src');import json,cascade_bridge as c;pb=json.load(open('state/PAID_BURST.json'));print(pb['used'],c.paid_lane_open(pb))"
   ```
   *(Note the two dollar figures in the ledgers are both correct and measure different things:
   BUGS.md's ~$1.96 is the ~98 calls spent PAST the cap; FOR_OWNER.md's $11.96 is all 598.)*

## 2. Human decisions needed (owner)

A. **[17 stranded feats records — RE-SCOPED by run #9, read this before acting]** The earlier
   framing said four missing hosts strand 17 records / 462 deeds. Re-measured, it is two problems:
   * **14 records / 222 deeds** — hosts genuinely absent from `data/WIKI_HOSTS.json` (the amazing
     digital circus, date a live, sakamoto days, uncle grandpa). Adding bindings is mechanical;
     **which source each belongs to is the owner call.** This part is as described.
   * **3 records / 240 deeds — the MAJORITY of the stranded evidence — are on hosts already
     bound**: `Wally West (New Earth)` and `Wally West (Prime Earth)` (dc.fandom.com → DC), and
     `Brood` (marvel.fandom.com → Marvel). **No host ruling recovers these.** The catalogue holds
     `Wally West (Earth-16)` — a third continuity — and no plain `Brood` under any spelling. The
     question is curatorial: should a deed mined from one continuity attach to a cast entry for
     another? **Do not answer it by loosening `_norm`** — verify_math §19o now forbids that, and
     the reason is written into `feats_index._norm`'s docstring.
B. **[hybrid Powers — 87 entries, 6 sources]** Which chapter do hybrid sources' abilities belong
   to? `address.chapter_label_for` routes by `mode` (`folder-mechanical` → MechanicalContent,
   `web` → Powers), covering 98.7%. `hybrid` sources genuinely mix both, so no wholesale route is
   honest. Leave under Powers (current), route to Mechanical, or split per-entry — the last needs
   a real per-entry signal, and an empty description is NOT one (see m29).
C. **[cross-source feats encyclopedia]** Should feats exist as their own VOLUME, not only as the
   per-source `<spine>/Feats` chapter that was built? A library-wide encyclopedia organised BY
   AXIS needs its own spine code, which Hard Rule 2 reserves for the owner. The join and packer
   would serve it unchanged; only the addressing is missing.
D. **[m43] Should the kit detect orphaned processes itself?** Two runs, two instances, both found
   by hand. The check is trivial — a `panscriptum` python process whose parent PID is dead — but
   it adds a reported subsystem to `allsweep` or `health --preflight`, and **the two runs that hit
   it disagree on the remedy: kill it, or report it?** Killing is what both runs did by hand;
   automating a kill is a much larger claim than automating a report.
E. **[m42] Which guard?** Either `hostcheck._land` gains m40's digest-compare (write only if the
   file is as it was read; else re-read and merge), or long-running children learn to notice a
   dead parent and exit. The first is local and proven; the second fixes the whole class. **Note
   `_land` is already atomic — atomicity is not the missing property.**
F. **[M4] The burst lane** — 598/500, closed by the cap rather than by intent. Raise `cap`, set
   `enabled: false` (which genuinely works now), delete the file (now safe), or retire the lane.
G. **[m37] Nothing reads `data/CHAIN.json`** — confirmed repo-wide in run #8. Every cycle persists
   the Bradley-Terry strengths and the Ford's-condition verdict, and the cross-check the module
   calls its entire purpose never runs against the Assay. **Wire a consumer, or stop calling it a
   check and describe it as an archival record.** Inventing a consumer invents a contract.
H. **Should `data/GENRES.json` and `data/NAVTREE.json` have automated writers?** Both are hand-run
   and both are the only bridge from their module into the running system. `NAVTREE.json` is the
   sharper case: it feeds `build_terminal.py`, `reference.py` and `sweep.py`, and
   `output/registry_terminal.html` is rebuilt continuously *from it* — so whatever it holds is
   served to readers whether or not anyone regenerated it. Either these join the phases, or the
   hand-run step is deliberate curatorial control and should be written down as such.
I. **[m29] `cleanup.py`'s `_EMPTY_MECHANIC` predicate** strikes on empty description + a name
   ending in `variant|feature|trait|slot|…`. An empty description has repeatedly proved unreliable
   here, and Loki *Variants* are real entities. Exclusions are permanent since run #6, so a wrong
   strike now sticks. **Decide before `cleanup.py --apply` runs again** — the 149 previously
   struck entries have all been flipped back, so re-running is what would re-strike them.
J. **[m26] The completeness audit cannot see 46 of 210 sources** (`todo` filters on a fandom-only
   `subdomain(h)`). Measure the others, or rename the measure to say what it covers?
K. **[m25 / m16 / dashboard `findings` cap of 12] — ONE decision, three sites: does Hard Rule 0
   bind diagnostics and run logs, or only reader-facing listings?** Carried since run #5 and still
   the highest-leverage single ruling available. **"Does anything downstream act on the truncated
   list?" is the workable test.** Run #8's `chain` `[:120]` dedup key is the case for the strict
   reading: it looked like a harmless internal detail and was deciding which contests existed.
   *(New data point, run #9: `hostcheck.null_rate`'s `[:sample]` is the same shape and is
   genuinely inert — see m44. The rule needs to distinguish these two, or it will keep costing a
   measurement every run.)*
L. **[m38] `foreman._function_source` resolves symbols by bare name, no uniqueness check** — it
   can hand the model lane the wrong same-named function and, with `--patch` live, overwrite it.
   Refuse an ambiguous symbol, or honour the class qualifier `overwatch` already emits?
M. **[m39] `scout.sweep(limit=4)`** can starve lower-ranked hostless sources forever — the ranking
   is deterministic and recomputed each round. Uncapping changes per-round load.
N. **[m24] `cascade_bridge.dead_forever`** buries buckets on `no such model` / `needs billing` /
   `bad key`, which its docstring's "permanent codes only" rule does not cover. **Still live and
   now clearly consequential:** run #9 saw `overwatch.log` and `pipeline_auto.log` carrying
   `REMOVED local-gemma3-12b`, `REMOVED local-qwen25-14b`, `REMOVED local-llama31`, `REMOVED
   local-qwen3-30b-q3` — all HTTP 404 for LOCAL ollama models that are **simply not pulled**
   (`ollama list` holds exactly one model). Nothing about that is permanent; `ollama pull` restores
   them. Removals are in-memory per process and do not persist.
O. **[m12] `thread_integrity.py`'s asymmetric/dangling detection is structurally unreachable.** Is
   it meant to compare implied threads against a separately-recorded DIRECTED thread graph it is
   not currently given? Not a one-line fix either way.
P. **[m13] `phase_synthesis`'s 14-entity ceiling sample** can clamp a whole source to a lesser band
   if the true strongest entity is not sampled. Raise, re-rank, or accept.
Q. **[M1] dandwiki.com** — browser-UA HTML reader vs. owner-supplied text. Politeness/ToS call,
   open since run #1. The `health --preflight` cache FAIL is this decision, not a fault.
R. **[m23] job logs truncated on every restart** — bit runs #4 and #7. Fix is small (`"a"` plus a
   session separator, or rotate to `<job>.N.log`) but changes an operational convention and the
   dashboard's `_tail_match` readers assume one current file.
S. **[m30 follow-on] `custodes.convene` could report something real.** `covers_every_reading` is
   true by construction; the informative quantity — whether the **1.96·sd band alone** covered
   every reading — is invisible. A contract addition, not a repair.
T. **Permanently hostless roll entries** (Clockwork Angels, Twilight Imperium, HAWX, …) — stay on
   the roll as owner-supplied-text candidates, or come off? **Catalogued sources with no host is
   20**; **on the roll but never catalogued is 6** (allsweep, run #9 — both unchanged from #8).
   Also the **91 DECIDED spine codes** from the 12:05 session are **still not written to
   `CHARTER_SPINE_CODES.json`**, which has no writer in `src/` — rulings must land in the charter
   appendix first or they are erased on the next re-derive.

## 3. Small implementable items (no decision needed)

1. **`allsweep`'s `running` detector is now wrong three runs straight** — it reported **4** live
   jobs (read, feats --roll, pipeline, overnight) while the process list showed **10** alive,
   omitting dashboard, publish, foreman, overwatch and autostart. Run #8 saw 1, run #7 saw 4. The
   jobs are demonstrably up, so this is a detection false-negative rather than an outage — **but
   it is the thing a future run would trust to decide a job is down**, which makes it worth an
   hour now. Start by reading how it matches a process; the standing jobs it misses are exactly
   the ones the keeper launches.
2. **The three run #5 audit findings, still un-actioned**, all deserving a second opinion:
   `hostcheck`'s `judgeable` flag is computed and respected by `standards.py` but **ignored by
   hostcheck's own two consumers**; `onomast.coin_well_formed`'s fallback **skips both its quality
   and uniqueness checks**; `feats._unwrap_templates` **miscounts brace nesting on `{{{`**.
3. **`src/deprecated/catalogue_local.py:244` — f-string with no placeholders.** The single
   pyflakes warning in the tree. Cosmetic, in a deprecated file; fix or delete the file.
4. **12 silent exception handlers remain** (`python src/silence.py`): silence.py ×5, health.py ×2,
   coverage.py, local_agent.py:339, pipeline.py:1531, publish.py:161, standards.py:797. Each can
   turn a failure into a plausible negative result — which is exactly what run #9 spent an hour
   ruling out on the foreman's "GPU busy" message before finding it was honest.
5. **The hash-order tie-break sweep (run #8 item 22) is DONE — do not redo it.** Run #9 swept
   `max(set(` / `min(set(` / `sorted(set(` / `next(iter(` across `src/`. navtree's two are fixed
   and carry their tie-break; every `sorted(set(` is deterministic by construction; the two
   `next(iter(` sites read dicts with deterministic insertion order. The only thing it turned up
   was m44, which is filed and inert.

## 4. Surface rotation for the next audit fan-out

**Runs #8 and #9 spawned no subagents.** In #9 the local rung was measured saturated (preamble
item 2) and the queue held enough verified concrete work. The rotation list is therefore still
untouched and is the right place to spend a run that arrives with a real diff.

Covered, do **not** re-read unless the diff touched them: the round-1 full-codebase audit and
evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces; run #3's two; run #5's three
(assay/magnitude/identity; hostcheck/scout/tuning/compress_store; read/feats/estate/worldseed/
onomast); run #6's four (health/overwatch/silence; catalogue_web/backfill/cleanup;
custodes/tiers/sevenfold/grounding; cascade_bridge's widen/paid path); run #7's five
(address/completeness/foreman; chain/module_index/local_agent/pick_model).
**Run #9 read `feats_index.py` closely** (its join, `_norm`, `audit()`) and `hostcheck`'s
`null_rate`/`adopt`/`_land` — treat those as covered.

**Not yet audited line-by-line** — pick from here: `address_space.py`, `profile.py`, `burgs.py`,
`tells.py`, `style_audit.py`, `audit.py`, `descending_ladder.py`, `cosmography.py`, `genre.py`,
`reference.py`, `resync_roll.py`, `retry_synthesis.py`, `build_terminal.py`, `sweep.py`, and
**`pipeline.py`'s `ask`/`ask_pool_first`/`phase_entrypass`**, plus `runguard.py`.
**Newly interesting:** `manifest_builder.pack_feats` and `generate.py`'s `feats` branch shipped
12:05 today and **have never been read by anyone but their author** — run #9 audited the join
beside them and found two false claims in an hour-old docstring, so the rest of that diff is the
highest-yield unaudited surface in the tree.

## 5. Lessons worth keeping

- **A fix is an event, and events make orphans.** Run #8 bounced a job to ship a patch; that bounce
  orphaned the job's in-flight child, which became run #9's main bug. **Any run that restarts
  something should check what that something had running underneath it** before closing out.
- **`subprocess.run(timeout=)` only kills the child while the parent is alive.** A supervised
  child is safe; the same child whose parent was replaced is unkillable and unbounded. The parent
  PID is the diagnostic, and it is cheap.
- **Low CPU over a long life means blocked — but "blocked" is not "dead."** Run #9 nearly called a
  healthy process an orphan on the m40 ratio alone. A live socket (`SynSent` to the host it is
  probing) distinguishes network-bound work from a wedged one. **Check the sockets before the
  ratio decides.**
- **An error message that looks swallowed may be honest.** *"GPU busy and no spare pool capacity"*
  sits directly after a `silence.note`, which makes it look like a masked failure. It was true.
  Measuring the claim (240s for a trivial call; 32.6s wall for 28ms of compute) cost less than the
  wrong fix would have, and the right output was *no code change*.
- **Re-measure a predecessor's headline number even when it reproduces.** The feats audit
  reproduced exactly — 1,241 / 1,224 / 39,400 — and the *explanation* attached to it was still
  wrong for 52% of the affected evidence. **Totals agreeing is not the same as the story agreeing.**
- **A comment asserting a property is not evidence of that property** — and code being an hour old
  is no protection. Two false claims were found in a module written that morning by a careful
  author. Prefer running the thing to reading what it says about itself.
- **When the obvious fix is a trap, pin it with a test.** Loosening `_norm` looks like it recovers
  240 stranded deeds and actually merges three DC continuities. The finding is only durable
  because verify_math §19o now fails if anyone tries it.
- **Not fixing is a legitimate outcome, if it is measured.** m44 was found, measured, shown inert,
  and left alone with the measurement recorded — which costs the next run nothing and stops a
  behaviour change nobody wanted.
