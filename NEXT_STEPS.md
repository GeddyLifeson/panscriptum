# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #10 wrote this on 2026-08-24 ~12:55 local.*

**Read this first.** Four things shape what is worth doing next run:

1. **The local-model rung is starved by a process that is NOT OURS, and that is now the single
   highest-value thing on this list (BUGS M5).** `semsearch.cli watch` (PID 25188, parent dead
   since yesterday) was holding **13,942 of 13,945** established connections to the Ollama
   daemon. **Check whether it is still there before anything else** — item 1 below. If the owner
   has stopped it, the free rung comes back and half this queue becomes cheap.
2. **Do not re-diagnose the saturation. Diagnose who is causing it.** Runs #9 and #10 both
   measured the same numbers (~50 ms of compute taking 0.05 s or 35 s). Run #9 attributed it to
   our own jobs contending over one model and told the next runs not to look; that attribution
   was wrong. The measurement is not the diagnosis.
3. **A Hard Rule 0 truncation is loaded and has not fired (m46).** The Feats prompt is ~1.9x its
   context window. Nothing is corrupted because no feats chapter has ever been generated. **If a
   feats generation run is about to happen, m46 blocks it.**
4. **fandom is still blocked at the socket**, runs #5–#10. Both `health --preflight` FAILs are the
   known outages (M3 fandom, M1 dandwiki). The FAILs *are* the outage; neither is a bug to fix.

## 1. Verify first

1. **[M5 — IS THE OLLAMA CHOKE STILL THERE? Run this before anything else.]** One command,
   and it reframed three open bugs last run:
   ```
   powershell -NoProfile -Command "Get-NetTCPConnection -RemotePort 11434 -ErrorAction SilentlyContinue | Group-Object OwningProcess | Sort-Object Count -Descending | Select-Object -First 5 Name,Count"
   ```
   Healthy looks like a handful of connections spread across our own jobs. Run #10 saw **13,942
   on one foreign PID**. If a PID dominates, identify it — `Get-CimInstance Win32_Process -Filter
   'ProcessId=<pid>'` — and **check whether it is ours before forming any opinion.** If the owner
   has cleared it, say so plainly and re-measure the rung: three consecutive trivial `/api/chat`
   calls should return in well under a second each, not 28–35 s.
   **Do not kill a foreign process yourself.** M5 is filed as an owner call for that reason.
2. **[m49 — did the roster fix hold?]** `python src/allsweep.py` must report **nine** `running`
   lines (autostart, overnight, dashboard, publish, foreman, overwatch, pipeline, read,
   feats --roll), not four. verify_math §19p should catch a regression first. A `NOT RUNNING`
   line is informational — the keeper restores a standing job within five minutes — but **two
   consecutive runs showing the same job NOT RUNNING is a real outage**, not roster noise.
3. **[m46 — has anything generated feats yet?]** This must stay at zero until m46 is settled:
   ```
   python -c "import json;d=json.load(open('output/index/catalog.json',encoding='utf-8'));print(sum(1 for k in d if 'Feats' in str(k)))"
   ```
   Non-zero means a feats generation run happened against a prompt ~1.9x its context window, and
   the chapters need checking for silently missing deeds — **the coverage check will not have
   caught it**, because it only verifies the entity NAME appears.
4. **[m40 — the merge]** `data/OVERWATCH.json` should only ever grow:
   ```
   python -c "import json;d=json.load(open('data/OVERWATCH.json',encoding='utf-8'));print(d['rounds'],len(d['findings']))"
   ```
   Runs #8, #9 and #10 all read **68 / 64**. A LOWER number either way is top severity. It has not
   grown because overwatch completes no rounds (M5), **not** because the merge is faulty — run #10
   settled that by reading `state/overwatch.log`. If M5 is cleared and this still does not grow,
   it becomes a real bug for the first time.
5. **[m31 — the pipeline]** Same instrument, same caveat:
   ```
   grep -oE "returned [0-9]+/[0-9]+" state/pipeline_auto.log | sort | uniq -c
   ```
   No `returned` lines means no batch has completed. Run #10 verified `pipeline.py` holds an
   ESTABLISHED socket to 11434 — queued, not wedged. **`state/pipeline_auto.log` is truncated on
   every restart (m23) — transcribe before bouncing anything.**
6. **[M4 — money]** Must print `598 False`; flat for five runs:
   ```
   python -c "import sys;sys.path.insert(0,'src');import json,cascade_bridge as c;pb=json.load(open('state/PAID_BURST.json'));print(pb['used'],c.paid_lane_open(pb))"
   ```
7. **[m42 — hosts]** `WIKI_HOSTS.json` should still hold **202 bindings, 191 non-empty** (md5
   `451703b8…`, unchanged 08:55 → run #10). A DROP in either number means a stale writer won.
8. **[the orphan check — still worth running, now with its known blind spots]**
   ```
   powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'panscriptum' } | ForEach-Object { '{0} | parent={1} | {2}' -f $_.ProcessId, $_.ParentProcessId, $_.CreationDate }"
   ```
   **Two known blind spots, both found in run #10:** `autostart.py --watch` legitimately has a
   dead parent (it is the login launcher) — that is not an orphan; and the filter on
   `panscriptum` **cannot see a foreign orphan**, which is exactly what M5 turned out to be. Use
   item 1 alongside this, not instead of it. Low CPU over a long life means blocked, not dead —
   check for live sockets before concluding.

## 2. Human decisions needed (owner)

A. **[M5] Stop or restart `semsearch.cli watch`?** Not ours, so not touched. Doing so should
   restore the free local rung for the whole kit. Everything below that needs a model is cheaper
   afterwards.
B. **[m46] Which remedy for the Feats prompt overflowing `num_ctx`?** Raise `num_ctx` (larger KV
   cache, fewer layers on GPU — config.yaml's own note covers this), lower `feats_block_chars`
   (no data loss, `pack_feats` paginates correctly, but ~2x the calls on the bottleneck), trim the
   18 KB system prompt for feats jobs, or a mix. **Add a verify_math check asserting the prompt
   fits once a remedy is chosen** — it was deliberately not added in run #10 because it would have
   failed on arrival and turned the battery red. **Settle before the first feats generation run.**
C. **[m48] 70 sources have catalogue entries colliding under `_norm`** (worst: 125). Two causes
   are mixed: exact duplicate entries (a catalogue-quality question) and genuine spelling folds
   (the join working). Not data loss — feats attach to the surviving twin. **Do not "fix" it by
   loosening `_norm`**; §19o forbids that and the reason is in m45's paper trail.
D. **[m47] What should a failed feats join look like?** Today an exception becomes "this source
   has no feats," indistinguishable from a true zero, losing the whole source's chapter. Fail
   loud, or record the skip where the owner actually looks (`output/index/failures.json` is the
   file CLAUDE.md points at, and manifest-build-time skips never reach it). Dormant today —
   verified zero non-dict items across all records and all 1,241 readfeats files.
E. **[m43] Should the kit detect this at all, and detect WHAT?** Run #10 showed the drafted rule
   ("a panscriptum process whose parent is dead") both misses the only orphan that has cost
   anything and false-positives forever on `autostart.py --watch`. The better question may be
   "what is holding the resources we need" — clients on 11434, handles on our state files. Still
   an owner call, and still kill-vs-report.
F. **[17 stranded feats records — RE-SCOPED by run #9, read before acting]** Two problems, not
   one: **14 records / 222 deeds** on hosts genuinely absent from `WIKI_HOSTS.json` (the amazing
   digital circus, date a live, sakamoto days, uncle grandpa) — mechanical to add, but which
   source each belongs to is the owner call. And **3 records / 240 deeds — the MAJORITY of the
   evidence — on hosts already bound** (`Wally West (New Earth)`, `Wally West (Prime Earth)`,
   `Brood`). **No host ruling recovers those**; it is a curatorial question about whether a deed
   mined from one continuity attaches to a cast entry for another.
G. **[hybrid Powers — 87 entries, 6 sources]** Which chapter do hybrid sources' abilities belong
   to? `address.chapter_label_for` routes by `mode`, covering 98.7%. `hybrid` genuinely mixes
   both. Leave under Powers (current), route to Mechanical, or split per-entry — the last needs a
   real per-entry signal, and an empty description is NOT one (see m29).
H. **[cross-source feats encyclopedia]** Should feats be their own VOLUME, not only the per-source
   `<spine>/Feats` chapter? Needs its own spine code, which Hard Rule 2 reserves for the owner.
   The join and packer would serve it unchanged; only the addressing is missing.
I. **[M4] The burst lane** — 598/500, closed by the cap rather than by intent. Raise `cap`, set
   `enabled: false` (which genuinely works now), delete the file (now safe), or retire the lane.
J. **[m37] Nothing reads `data/CHAIN.json`** — confirmed repo-wide in run #8. Wire a consumer, or
   stop calling it a check and describe it as an archival record.
K. **Should `data/GENRES.json` and `data/NAVTREE.json` have automated writers?** Both are hand-run
   and both are the only bridge from their module into the running system. `NAVTREE.json` feeds
   `build_terminal.py`, `reference.py` and `sweep.py`, and `output/registry_terminal.html` is
   rebuilt continuously *from it* — so whatever it holds is served to readers whether or not
   anyone regenerated it.
L. **[m29] `cleanup.py`'s `_EMPTY_MECHANIC` predicate** strikes on empty description + a name
   ending in `variant|feature|trait|slot|…`. Exclusions are permanent since run #6, so a wrong
   strike now sticks, and Loki *Variants* are real entities. **Decide before `cleanup.py --apply`
   runs again** — the 149 previously struck entries have all been flipped back.
M. **[m26] The completeness audit cannot see 46 of 210 sources** (`todo` filters on a fandom-only
   `subdomain(h)`). Measure the others, or rename the measure to say what it covers?
N. **[m25 / m16 / dashboard `findings` cap of 12] — ONE decision, three sites: does Hard Rule 0
   bind diagnostics and run logs, or only reader-facing listings?** Carried since run #5 and still
   the highest-leverage single ruling available. **"Does anything downstream act on the truncated
   list?" is the workable test** — run #8's `chain` `[:120]` dedup key looked like a harmless
   internal detail and was deciding which contests existed, while `hostcheck.null_rate`'s
   `[:sample]` (m44) is the same shape and genuinely inert.
O. **[m38] `foreman._function_source` resolves symbols by bare name, no uniqueness check** — with
   `--patch` live it can overwrite the wrong same-named function. Refuse an ambiguous symbol, or
   honour the class qualifier `overwatch` already emits?
P. **[m24] `cascade_bridge.dead_forever`** buries buckets on `no such model` / `needs billing` /
   `bad key`, which its docstring's "permanent codes only" rule does not cover. The local-model
   404s it acts on are simply models that are not pulled (`ollama list` holds one); `ollama pull`
   restores them, so nothing about it is permanent. Removals are in-memory and do not persist.
Q. **[m12] `thread_integrity.py`'s asymmetric/dangling detection is structurally unreachable.**
   Is it meant to compare implied threads against a directed thread graph it is not given?
R. **[m13] `phase_synthesis`'s 14-entity ceiling sample** can clamp a whole source to a lesser
   band if the true strongest entity is not sampled. Raise, re-rank, or accept.
S. **[M1] dandwiki.com** — browser-UA HTML reader vs. owner-supplied text. Politeness/ToS call,
   open since run #1. The `health --preflight` cache FAIL is this decision, not a fault.
T. **[m23] job logs truncated on every restart** — bit runs #4 and #7. Fix is small (`"a"` plus a
   session separator, or rotate to `<job>.N.log`) but changes an operational convention and the
   dashboard's `_tail_match` readers assume one current file.
U. **[m39] `scout.sweep(limit=4)`** can starve lower-ranked hostless sources forever — the ranking
   is deterministic and recomputed each round. Uncapping changes per-round load.
V. **[m30 follow-on] `custodes.convene` could report something real.** `covers_every_reading` is
   true by construction; the informative quantity — whether the 1.96·sd band alone covered every
   reading — is invisible. A contract addition, not a repair.
W. **Permanently hostless roll entries** (Clockwork Angels, Twilight Imperium, HAWX, …) — stay on
   the roll as owner-supplied-text candidates, or come off? **Catalogued sources with no host is
   20**; **on the roll but never catalogued is 6** (allsweep, run #10 — unchanged since #8).
   Also the **91 DECIDED spine codes** from the 12:05 session are **still not written to
   `CHARTER_SPINE_CODES.json`**, which has no writer in `src/` — rulings must land in the charter
   appendix first or they are erased on the next re-derive.

## 3. Small implementable items (no decision needed)

1. **`src/deprecated/catalogue_local.py:244` — f-string with no placeholders.** The single
   pyflakes warning in the tree. Cosmetic, in a deprecated file; fix or delete the file.
2. **The three run #5 audit findings, still un-actioned**, all deserving a second opinion:
   `hostcheck`'s `judgeable` flag is computed and respected by `standards.py` but **ignored by
   hostcheck's own two consumers**; `onomast.coin_well_formed`'s fallback **skips both its quality
   and uniqueness checks**; `feats._unwrap_templates` **miscounts brace nesting on `{{{`**.
3. **12 silent exception handlers remain** (`python src/silence.py`): silence.py ×5, health.py ×2,
   coverage.py, local_agent.py:339, pipeline.py:1531, publish.py:161, standards.py:797. Each can
   turn a failure into a plausible negative result — m47 is exactly that shape, one layer up.
4. **`pipeline.py`'s 9 shared cross-phase JSON writes** still use raw `open+json.dump` rather than
   `_landed`/`replace_retry` (from run #2's audit). Medium surgery, 9 call sites, still open.
5. **DONE, do not redo:** the hash-order tie-break sweep (run #9) and the `allsweep` roster
   (run #10, m49 — now one list in `overnight.ALL_JOBS`, pinned by §19p).

## 4. Surface rotation for the next audit fan-out

**Run #10 spawned two sonnet subagents** against the surface run #9 named as highest-yield —
`manifest_builder.pack_feats` and `generate.py`'s feats branch. Both are now **covered**: the
packer was verified correct (7,354 feats in, 7,354 out, genuine pagination, deterministic order),
and the audits produced m46, m47, m48 and m50.

Covered, do **not** re-read unless the diff touched them: the round-1 full-codebase audit and
evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces; run #3's two; run #5's three;
run #6's four; run #7's five (address/completeness/foreman; chain/module_index/local_agent/
pick_model); run #9's `feats_index.py` and `hostcheck`'s `null_rate`/`adopt`/`_land`; run #10's
`manifest_builder.pack_feats` + feats-chapter block and `generate.py`'s feats branch.

**Not yet audited line-by-line** — pick from here: `address_space.py`, `profile.py`, `burgs.py`,
`tells.py`, `style_audit.py`, `audit.py`, `descending_ladder.py`, `cosmography.py`, `genre.py`,
`reference.py`, `resync_roll.py`, `retry_synthesis.py`, `build_terminal.py`, `sweep.py`,
`runguard.py`, and **`pipeline.py`'s `ask`/`ask_pool_first`/`phase_entrypass`**.
**Newly interesting:** `compress_store.py` and `prompts/system_style.txt` — the 18 KB system
prompt is sent on *every* call and is half of m46's overflow, and nobody has read it against the
context budget it is charged to.

## 5. Lessons worth keeping

- **Measuring a symptom precisely is not the same as diagnosing it.** Run #9 measured the local
  rung's saturation to the millisecond and attributed it to our own jobs. Both numbers survived
  re-measurement; the attribution did not. **An accurate measurement attached to a wrong cause is
  more dangerous than no measurement, because it tells the next runs to stop looking.**
- **Ask who else is using the shared thing.** The whole of M5 came from one question the logs
  could never have answered: *who else is on this port?* Our processes, our logs and our checks
  were all working correctly and all pointed inward.
- **A symptom described identically four times is a symptom nobody re-derived.** Runs #7–#10 each
  recorded "allsweep says 4, the process table says 9" and each repeated the same suggested
  starting point. The cause was a hardcoded list two lines from where everyone was told to look.
  **When a finding is inherited verbatim, re-derive it once before trusting its framing.**
- **Three copies of a list are three chances to be wrong, and the copy that is wrong is silent.**
  A job missing from a roster does not read as "not listed", it reads as NOT RUNNING.
- **A subagent that says "I found no live data for this" may simply not have looked at the data.**
  m48's collisions were reported as UNCERTAIN with none found; a one-minute scan found 70 sources
  and 125 in the worst. **Verify a negative finding as carefully as a positive one.**
- **A comment asserting a property is not evidence of that property** — three false claims in
  two runs, all in code less than a day old, all written by careful authors. Twice now the
  comment's own worked example already refuted its headline number.
- **Not fixing is a legitimate outcome, if it is measured and written down.** m44 and m46 are both
  filed with their measurements and deliberately unfixed — one because fixing it would perturb
  live verdicts for no gain, the other because every remedy is a trade only the owner can make.
