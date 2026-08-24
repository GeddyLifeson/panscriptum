# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #11 wrote this on 2026-08-24 ~13:20 local.*

**Read this first.** Four things shape what is worth doing next run:

1. **THE SCHEDULE IS NOW HOURLY.** The owner changed it mid-run #11 from every 15 minutes
   (`11,26,41,56 * * * *`) to `11 * * * *`. Run #10 finished 93 seconds before run #11 started,
   so runs were constantly landing on live predecessors. **You should now expect to be alone.**
   If the overlap guard says a predecessor is live under an hourly schedule, that is no longer
   normal — it means a previous run hung. Check the heartbeat age before assuming.
2. **The local rung is not slow, it is SORTING US BY `num_ctx` (M5, mechanism found run #11).**
   A call that asks for the resident runner's 4096 completes in 9-38 s; a call asking 6144 or
   8192 **does not complete at all**. `synthesis` and `entrypass` are the only living lanes.
   **Do not re-derive this** — it is measured, tabulated and in BUGS M5. Re-measure only the two
   cheap facts: is PID 25188 still there, and does a `num_ctx: 6144` probe still time out.
3. **m52 is the biggest open technical finding and it is LATENT — which is the only reason it is
   still cheap.** 94% of the 9,153 chapter jobs overflow `num_ctx`. Nothing is corrupted because
   generation has never run at volume (`catalog.json` = **6 addresses**). **If a generation run
   is about to happen, m52 blocks it, exactly as m46 blocks a feats run.**
4. **fandom is still blocked at the socket**, runs #5–#11. Both `health --preflight` FAILs are
   the known outages (M3 fandom, M1 dandwiki). The FAILs *are* the outage; neither is a bug.

## 1. Verify first

1. **[M5 — two cheap checks, in this order.]**
   ```
   powershell -NoProfile -Command "Get-NetTCPConnection -RemotePort 11434 -ErrorAction SilentlyContinue | Group-Object OwningProcess | Sort-Object Count -Descending | Select-Object -First 5 Name,Count"
   ```
   Run #10 saw 13,942 on PID 25188; run #11 saw **14,244** — it grows. If it is gone, **re-run
   the num_ctx probe before celebrating**, because the pinned 4096 runner may outlive the client
   that pinned it:
   ```
   curl.exe -s --max-time 20 http://127.0.0.1:11434/api/ps
   ```
   Healthy = either no pinned `expires_at: 2318…` entry, or a `num_ctx: 6144` call that returns.
   **Do not kill a foreign process yourself.** M5 is an owner call for that reason.
2. **[m52 — has anything generated at volume yet?]** Must stay near 6 until m52 is settled:
   ```
   python -c "import json;d=json.load(open('output/index/catalog.json',encoding='utf-8'));print(len(d))"
   ```
   A number in the hundreds means a generation run happened against a window that fits 6% of
   chapter jobs, and **`_covered()` will not have caught it** — it only checks the entity NAME
   appears. Spot-check chapters for entries that stop mid-sentence or are missing their tail.
3. **[m46 — feats specifically]** Still zero, checked run #11:
   ```
   python -c "import json;d=json.load(open('output/index/catalog.json',encoding='utf-8'));print(sum(1 for k in d if 'Feats' in str(k)))"
   ```
4. **[m40 — CLOSED, do not re-open on a flat reading.]** `OVERWATCH.json` went **68/64 → 69/66**
   in run #11; the merge is exonerated **by observation**. A round takes 48-152 s per module
   under M5, so two reads 20 minutes apart can legitimately show the same numbers.
   **Only a number that goes DOWN is a bug.**
   ```
   python -c "import json;d=json.load(open('data/OVERWATCH.json',encoding='utf-8'));print(d['rounds'],len(d['findings']))"
   ```
5. **[m31 — the pipeline]** Still no `returned N/M` line, now partly explained: entrypass runs at
   `num_ctx=4096` and IS completing (check `state/model_metrics.jsonl` for recent `entrypass`
   rows with an `s` of 24-38), while the phases that would emit the batch line need lanes M5 has
   killed. **`state/pipeline_auto.log` is truncated on every restart (m23) — transcribe first.**
6. **[M4 — money]** Must print `598 False`; flat for six runs:
   ```
   python -c "import sys;sys.path.insert(0,'src');import json,cascade_bridge as c;pb=json.load(open('state/PAID_BURST.json'));print(pb['used'],c.paid_lane_open(pb))"
   ```
7. **[m42 — hosts]** `WIKI_HOSTS.json` should still hold **202 bindings, 191 non-empty**
   (md5 `451703b8…`, unchanged 08:55 → run #11). A DROP means a stale writer won.
8. **[m49 — the roster]** `allsweep` must report **nine** `running` lines. Held in run #11.
   One `NOT RUNNING` line is informational (the keeper restores within 5 min); **the same job
   NOT RUNNING on two consecutive runs is a real outage.**
9. **[run #11's unbounced fix]** `pipeline.py`'s entrypass prompt was changed to `len(lines)` but
   **the running process still carries the old string** — it was deliberately not bounced,
   because it is the only working lane. Confirm the fix is live after the next natural restart;
   verify_math §19q pins the source either way.

## 2. Human decisions needed (owner)

A. **[M5] Stop or restart `semsearch.cli watch` (PID 25188)?** Not ours, so not touched. This is
   still the cheapest win available and it now has a measured mechanism, not just a cost.
B. **[m52 + m46] Which remedy for the context overflow, given it CANNOT be "raise `num_ctx`"
   while M5 stands?** Raising it currently converts those paths from slow to never-answers
   (measured). The remedies that do not depend on the daemon: lower `WRITE_CHUNK` (`generate.py:37`,
   currently 8 entries per block — no data loss, more calls), trim the **18,112-char** system
   prompt for chapter jobs, or split the prompt per job type (**~69% of it is provably
   chapter-only by the file's own text; The Instrument alone is 5,758 chars and is explicitly
   *forbidden* for feats jobs by `feats_prompt.txt:30-33`**). **Add a verify_math check asserting
   the prompt fits once a remedy is chosen** — deliberately not added in runs #10 or #11 because
   it would fail on arrival and turn the battery red.
C. **[m51] Should `check_context_budget` cover the generate path too, or be renamed to say what
   it covers?** It measures read.py's pass only. Either is defensible; leaving it as-is means
   `ok context budget` keeps meaning less than it reads.
D. **[NEW — m53-shaped, filed as a question because the code says it is deliberate]
   `pipeline.py:992` truncates every entry description to 240 chars before the model judges it.**
   The comment says this is intentional ("classification needs the opening clause"). A subagent
   measured **50.6% of ~82,000 sampled entries are longer than 240 chars** (median 245 — the
   typical entry sits right on the cutoff). Consequence: `valid_scale_note` can only ever see the
   first 240 chars, so an entity whose feat evidence appears later is banded **`unassayed`
   because the evidence was cut out of the prompt**, indistinguishable from genuine absence — and
   those bands "order the entire Persons series" per the code's own comment. **Is the 240 still
   the right trade now that the consequence is measured?** Per the hard rules this is a QUESTION,
   not a fix — do not change it unilaterally.
E. **[m48] 70 sources have catalogue entries colliding under `_norm`** (worst: 125). Exact
   duplicates mixed with genuine spelling folds. Not data loss. **Do not "fix" it by loosening
   `_norm`** — §19o forbids it and m45's paper trail says why.
F. **[m47] What should a failed feats join look like?** Today an exception becomes "this source
   has no feats," indistinguishable from a true zero. Dormant — verified zero non-dict items.
G. **[m43] Should the kit detect resource-holders at all?** Run #10 showed the drafted rule
   ("parent is dead") misses the only orphan that has cost anything and false-positives forever
   on `autostart.py --watch`. Run #11 strengthens the reframe: the useful question is **"who is
   holding the runner, and at what context size."**
H. **[17 stranded feats records]** 14 records / 222 deeds on genuinely unbound hosts (mechanical,
   but which source each belongs to is curatorial); **3 records / 240 deeds — the majority — on
   hosts already bound** (`Wally West` ×2, `Brood`), which **no host ruling recovers.**
I. **[hybrid Powers — 87 entries, 6 sources]** Leave under Powers, route to Mechanical, or split
   per-entry (the last needs a real per-entry signal; an empty description is NOT one, see m29).
J. **[cross-source feats encyclopedia]** Should feats be their own VOLUME? Needs a spine code,
   which Hard Rule 2 reserves for the owner.
K. **[M4] The burst lane** — 598/500, closed by the cap not by intent. Raise, disable, delete, or
   retire.
L. **[m37] Nothing reads `data/CHAIN.json`.** Wire a consumer, or stop calling it a check.
M. **Should `data/GENRES.json` and `data/NAVTREE.json` have automated writers?** Both hand-run,
   both the only bridge from their module into the running system; `registry_terminal.html` is
   rebuilt continuously *from* NAVTREE.
N. **[m29] `cleanup.py`'s `_EMPTY_MECHANIC` predicate** — exclusions are permanent since run #6,
   so a wrong strike sticks, and Loki *Variants* are real. **Decide before `--apply` runs again.**
O. **[m26] The completeness audit cannot see 46 of 210 sources** (`todo` filters on a
   fandom-only `subdomain(h)`). Measure the rest, or rename the measure.
P. **[m25 / m16 / dashboard `findings` cap of 12] — ONE ruling, three sites: does Hard Rule 0
   bind diagnostics and run logs, or only reader-facing listings?** Carried since run #5, still
   the highest-leverage single ruling available. **"Does anything downstream act on the truncated
   list?" is the workable test** — and item D above is a fourth site where the answer is *yes*.
Q. **[m38] `foreman._function_source` resolves symbols by bare name**, no uniqueness check, with
   `--patch` live. Refuse ambiguous symbols, or honour the class qualifier `overwatch` emits?
R. **[m24] `cascade_bridge.dead_forever`** buries buckets on `no such model`. **Live evidence in
   `state/overwatch.log` right now**: four buckets REMOVED for 404s on models that simply are not
   pulled. `ollama pull` restores them, so nothing about it is permanent.
S. **[m12] `thread_integrity.py`'s asymmetric/dangling detection is structurally unreachable.**
T. **[m13] `phase_synthesis`'s 14-entity ceiling sample** can clamp a whole source's band. Note
   this is the same shape as D and P — an input cap a downstream verdict treats as authoritative.
U. **[M1] dandwiki.com** — browser-UA HTML reader vs. owner-supplied text. Politeness/ToS call.
V. **[m23] job logs truncated on every restart** — bit runs #4, #7 and #11 (overwatch.log holds
   only one round block). Fix is small; it changes an operational convention.
W. **[m39] `scout.sweep(limit=4)`** can starve lower-ranked hostless sources forever.
X. **[m30 follow-on] `custodes.convene` could report something real** — the 1.96·sd band's own
   coverage is invisible.
Y. **Permanently hostless roll entries** — **catalogued sources with no host is 20**; **on the
   roll but never catalogued is 6** (unchanged since #8). Also the **91 DECIDED spine codes**
   from the 12:05 session are **still not written to `CHARTER_SPINE_CODES.json`**, which has no
   writer in `src/` — rulings must land in the charter appendix or they are erased on re-derive.

## 3. Small implementable items (no decision needed)

1. **12 silent exception handlers remain** (`python src/silence.py`): silence.py ×5, health.py ×2,
   coverage.py, local_agent.py:339, pipeline.py:1531, publish.py:161, standards.py:797. Two worth
   knowing about, both audited run #11: `pipeline.py:321` (the cloud arm's catch-all) records to
   `state/failures.json` but writes **nothing to `state/pipeline.log`** — the file an operator
   actually watches; and `pipeline.py:250` degrades to local-only permanently if
   `POOL_PROOF.json` is unreadable, silently.
2. **`pipeline.py`'s 9 shared cross-phase JSON writes** still use raw `open+json.dump` rather than
   `_landed`/`replace_retry` (run #2's audit). Medium surgery, 9 call sites, still open.
3. **The three run #5 audit findings, still un-actioned**: `hostcheck`'s `judgeable` flag is
   respected by `standards.py` but **ignored by hostcheck's own two consumers**;
   `onomast.coin_well_formed`'s fallback **skips both its quality and uniqueness checks**;
   `feats._unwrap_templates` **miscounts brace nesting on `{{{`**.
4. **One manifest anomaly nobody has root-caused:** the largest chapter job is **52,101 chars of
   payload, ~7x the 7,406 median**. Worth one look at which source/chapter it is.
5. **DONE, do not redo:** the pyflakes warning (run #11 — **the tree now lints clean, 0
   warnings**); the entrypass count mismatch (run #11, §19q); the hash-order tie-break sweep
   (run #9); the `allsweep` roster (run #10, m49, §19p).

## 4. Surface rotation for the next audit fan-out

**Run #11 spawned two sonnet subagents** on the surfaces run #10 named. Both are now **covered**:
`prompts/system_style.txt` against its context budget (produced m51 + m52) and `pipeline.py`'s
`ask`/`ask_pool_first`/`phase_entrypass` (produced item D, the fixed count mismatch, and a clean
bill on the retry/fallback contract — `ask` returns an honest `None`, and `phase_entrypass`
gates on `catalogued` rather than non-null, which is the correct invariant).

Covered, do **not** re-read unless the diff touched them: the round-1 full-codebase audit and
evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces; run #3's two; run #5's three;
run #6's four; run #7's five; run #9's `feats_index.py` and `hostcheck`'s `null_rate`/`adopt`/
`_land`; run #10's `manifest_builder.pack_feats` + feats-chapter block and `generate.py`'s feats
branch; run #11's two above.

**Not yet audited line-by-line** — pick from here: `address_space.py`, `profile.py`, `burgs.py`,
`tells.py`, `style_audit.py`, `audit.py`, `descending_ladder.py`, `cosmography.py`, `genre.py`,
`reference.py`, `resync_roll.py`, `retry_synthesis.py`, `build_terminal.py`, `sweep.py`,
`runguard.py`, and `compress_store.py`.
**Newly interesting:** **`generate.py`'s chapter branch and `manifest_builder`'s chapter-block
packer** — m52 says the jobs it builds overflow at the median, and `pack_feats` was verified
correct in run #10 but **the chapter packer never has been**. That is the highest-yield surface
on this list.

## 5. Lessons worth keeping

- **A value unchanged across N reads is evidence of a freeze only if the reads are spaced wider
  than the thing's natural period.** Three runs read `OVERWATCH.json` at 68/64 and inferred
  "stuck"; a round simply takes 48-152 s per module and was in flight each time. **Nobody had
  measured the period they were implicitly comparing against.**
- **Measure the mechanism, not just the magnitude.** Runs #9 and #10 both measured the local
  rung's saturation precisely. What changed everything was one controlled probe holding the
  prompt fixed and varying only `num_ctx` — turning "it's slow" into "6144 never returns and
  4096 returns in 9 seconds," which is a different bug with a different remedy list.
- **Control the confound before believing the live data.** The telemetry showing `entrypass`
  working and `overwatch` failing is also perfectly consistent with "small prompts work, big ones
  don't." Only the 6-character probe separates the two. **Live data agreeing with your hypothesis
  is not confirmation if a second hypothesis predicts it equally well.**
- **Both wrong measurements this run erred small.** A subagent reported a 3,331-char median
  chapter block; my own first pass reported 154 by summing only top-level strings and missing the
  nested payload. The true figure is 7,406 — and it is the difference between m52 being marginal
  and being severe. **When a number decides a severity, measure it twice by different means.**
- **A guard's reasoning does not extend itself to the neighbouring case.** `generate.py` forbids
  output truncation and cites Hard Rule 0 by name, on the same call whose input side is
  unguarded. The author knew the principle exactly; it just did not occur to them that the
  window has two ends.
- **A check that passes is only as good as its scope.** `ok context budget` was true and
  irrelevant for six runs.
- **Not fixing is a legitimate outcome, if it is measured and written down.** m44, m46 and m52
  are all filed with their measurements and deliberately unfixed. So is the un-bounced
  `pipeline.py` fix — shipping it would have cost the only working lane.
