# SWEEP 38 — AUDIT, BATCH 07

**Agent:** sweep38-batch07 · **Run:** run38 · **Modules:** 9 · **Lines:** 4,491
**Method:** every module read in full, top to bottom. Cross-references and behavioural claims
verified against the current tree by running code in
`…/scratchpad/sweep38/batch07/` (probe scripts: `probe_band.py`, `probe_names.py`,
`probe_remedies.py`, `probe_foreman.py`, `file_orders.py`). Nothing under `src/` was edited.
`pyflakes` is clean across all nine.

**Orders filed:** 10 (2 MAJOR, 8 MINOR; 8 LOCAL, 2 OWNER).

---

## foreman.py — 1,715 lines — READ IN FULL — 5 findings

The three lanes, all sixteen AUTO remedies, the MODEL lane's gate stack, `round_once` and
`main()` were read line by line.

**Verified sound, and worth recording because each is the kind of thing an audit usually
assumes:**

* **Every remedy is wired to a real standard.** AST-walked `standards.py` for every
  `_s(name, …)` call → 46 standard names; diffed against `foreman.REMEDIES` → all 21 keys plus
  `no high-severity findings open` match a live standard. No orphaned remedy, no dead lane.
  25 standards have no remedy and correctly fall to the OWNER lane.
* **`_restartable` / `_restart_horizon` agree**, as the shared `_standing_cmds()` was written to
  guarantee. Measured against the live roster: `pipeline.py --run` is the only one of the six
  `lognames.OWNER` fragments that is STANDING; the other five correctly report the main-lap
  horizon.
* **`_checks_pass`** reads the exit code from `allsweep --quick`, and the claim that `--quick`
  runs only IMPORT and LINT is true (the two `if not a.quick:` gates skip VERIFY and ESTATE).
  The `RESULT: N passed, M FAILED` regex reads the count, not a substring.
* **`lines_changed`** really does measure changed lines (`max(i2-i1, j2-j1)` per non-equal
  opcode), and `attempt_patch` tests `> MAX_PATCH_LINES`, exactly as the module docstring's
  self-correction says.
* **`reprove_pool`** calls `CB.prove()` at its default `pool="coding"`, which covers 36 of the
  router's 38 buckets; the two omitted are local ollama vision/gemma buckets. `POOL_PROOF.json`
  holds 36 rows, matching. The docstring's "thirty-six buckets" is current.
* Every atomic-write site routes through `silence.write_json` / `replace_retry` **and checks the
  return**, including the three that previously did not. `owner_queue`'s inline
  pid/thread-qualified temp is correct and sweeps itself on a denial.

### F1 — MAJOR — `triage_swallowed` names 3 failure classes and then wipes the ledger
`842025c83c3c` · LOCAL · foreman.py:258-331

`top = sorted(d.items(), key=lambda kv: -kv[1])[:3]`, and the very next block archives and
**clears** `state/failures.json`. Everything past the third class is erased from the live ledger
having never been named in the log a person reads, with no "and N more" — Hard Rule 0's shape
aimed at the operational log. Measured live 2026-08-29: 58 distinct classes / 2,827 events, so
55 names would have gone unspoken; the archive's last three snapshots hold 21, 24 and 56
classes, so >3 is normal. Among today's unnamed:
`silent:compress_store.py:address-mismatch ×10` — that is `compress_store.load()` refusing a
blob whose content hash does not match its filename, i.e. corpus corruption — and
`silent:silence.py:stale-write-refused ×21`.

The same file already refuses this cap elsewhere for the identical reason: `owner_queue`
("EVERY url, not the first three … A cap here is Hard Rule 0's exact shape aimed at a human
decision") and `_catalogue_batch`, which prints every deferred source by name.

### F2 — MAJOR — QUESTION — `restart_reader` kills a job nothing restarts
`d2e44a766769` · OWNER · foreman.py:448-490

`restart_reader()` SIGTERMs `read.py --run` with **no `_restartable()` gate**. Measured:
`_restartable('read.py --run')` is `False`, and `_restart_horizon` — which this function itself
calls and prints — returns *"NOT in the keeper's STANDING set … 42-44 min typically and 4h at
worst"*. The sibling remedy `kill_stalled_job` was changed for exactly this case
(foreman.py:555-573, "NEVER KILL WHAT YOU CANNOT RESTART (owner finding, 2026-08-25)"), records
the measured outage — *read.py killed at 10:59, stayed dead, every counter flat* — and names the
precise state `restart_reader` is now in: *"this function's own log line SAID SO while killing it
anyway."* `restart_reader` is the remedy for both `the library's counters are moving` and
`corpus read is progressing`, i.e. the automatic response to the standard that incident breached.

Filed as a question because the 2026-08-23 docstring gives a real counter-argument (a wedged
reader is worth nothing, so the trade is different) and because gating it would make the remedy a
permanent no-op — the honest alternative being to move `read.py` into `overnight.STANDING`, which
is a supervisor-topology decision. `_restart_horizon` already points at NEXT_STEPS §2 B as
holding three candidate fixes awaiting the same ruling.

### F3 — MINOR — an absent stall row reads as "no job is stalled now"
`b28082b9f65a` · LOCAL · foreman.py:515-517

`if not row or row.get("holds"): return True, "no job is stalled now"` conflates *the standard
says nothing is stalled* with *the standard is not in the report*. Reproduced: `rows=[]` yields
`(True, 'no job is stalled now')`, indistinguishable from the healthy case, and `did=True` also
breaks `round_once` out of the remedy list. Latent today (all 21 remedy keys match a live
standard — see above); fires on a rename or a standard that fails to produce its row. Same
fail-open shape the rest of the file is built against.

### F4 — MINOR — `restart_ollama` reports a 40s wait it does not perform
`01d39a5dc76d` · LOCAL · foreman.py:1031-1053

`sleep(12)` + `6 × (urlopen timeout 8 / sleep 5)` = **42s floor, 90s ceiling**; the message says
"did not respawn it within 40s". This is the module that fixed "supervisor restarts next cycle"
so a remedy would stop understating its own price. Best fix is to time it rather than restate a
constant, so the number cannot drift again.

### F5 — MINOR — five drifted cross-references
`6a361af0fa76` · LOCAL

| cited | actual |
|---|---|
| `allsweep.py:479, :498` (the `--quick` tiers) | 602, 627 (argparse at 548) — *claim correct* |
| `verify_math.py:5504` ("not safe to run") | 5815, and again 6026 — *claim correct* |
| `silence.py:408` (pid/thread temp), ×2 | 453 |
| `overnight.py:619` (how read.py is launched) | 1254 — *claim correct* |

`health.py:198-210` is **accurate** (the passage sits at 195-211) and should be left alone.

### Read and judged NOT a fault
* **`FOREMAN.json` kept at `prev[-200:]`** — log rotation, ~4 days at the 30-minute loop, and
  `overnight.foreman_report()` reads the newest entry. Not a roster.
* **`scout_hostless` passing `SC.sweep(limit=4)`** — checked `scout.sweep`: `limit` is now a
  *rate*, the ordering is last-attempted-first, and the deferred sources are printed by name
  inside `sweep()` itself. The rotation the `_catalogue_batch` docstring credits is real.
* **`_catalogue_batch`'s `rate`** — a per-round dispatch volume with every deferred, off-roll and
  unnameable source printed by name. That is rotation, not truncation.
* **`attempt_patch`'s TOCTOU** — `_function_source` reads the file, then the splice re-reads it
  and uses the earlier `start:end`. Two concurrent foremen could in principle splice with stale
  offsets. Not filed: `main()` calls `codewatch.claim_singleton("foreman")` in loop mode, and the
  backup is taken immediately before the write so a revert still restores the other writer's
  state. Recorded here so a later sweep does not have to re-derive it.
* **`regex_touched` passing an unparseable patch** when the original had no metacharacter
  literals — the module docstring already states this openly ("The standalone parse gate this
  line promises does not exist"), and the import check catches it.

---

## wiki_source.py — 687 lines — READ IN FULL — 1 question + 1 xref

Every cap this module once had is genuinely gone: `all_categories`' `hard_stop` defaults to
`None` and is memoised **only** on a complete walk, `find_categories`' `limit` and
`rank_by_size`' `top` default to `None`, and `category_members(limit=None)` pages to exhaustion.
`_get` cannot fall off its retry loop (every path returns, continues or raises). `page_text`
correctly `continue`s across all three sections before answering `""`. `clean_titles`' `seen`
set is present and the dedup is first-wins as documented. `MIN_GAP = 0.15` / `WORKERS = 48` are
consistent — the global gap is the throughput floor regardless of pool width.

### F6 — MINOR — QUESTION — the 40-page category floor is undeclared where it matters
`4d78c426afb3` · OWNER · wiki_source.py:375-446

`find_categories` promises *"Every category on this wiki that holds subjects of the given
canonical class"*, but its discovery half reaches the API as `acmin: 40`, so categories under 40
pages are excluded server-side, unmatched and uncounted. `all_categories`' own docstring is
honest about the floor; `find_categories`' — the one `catalogue_web` calls — is not. Two
readings: a sensible noise filter with a loose docstring, or Hard Rule 0 one level down in the
same file that already deleted `hard_stop=6000` and `limit=6` for this reason. The order names a
cheap measurement that would settle it, with the caveat that this machine has been IP-blocked by
fandom.com over exactly this kind of extra traffic.

### xref
`wiki_source.py:671` cites `catalogue_web.py:150`; the call is at `catalogue_web.py:206`. Folded
into `bf22c557852e`.

---

## sweep_plan.py — 566 lines — READ IN FULL — 1 finding

The shard topology is sound and the reasoning in `record`, `covered_by` and `latest_run` matches
the code: `covered_by` is a membership question answered by membership (not via the newest-wins
`coverage_map`), `latest_run` returns `None` rather than a guess, `missing()` is
`modules()` − `covered_by(run)`, and `_src_py_files` genuinely walks subdirectories so
`deprecated/catalogue_local.py` is now visible to `modules()`. `check_briefs`' `clean` flag looks
like it ignores `undispatched`, but an undispatched batch's modules necessarily land in
`uncovered`, so it does not.

### F7 — MINOR — the shard temp leaks on a denied replace
`75cd9babe439` · LOCAL · sweep_plan.py:186-222

The shard write is the one landing in this module that does not sweep its own scratch file. The
COVERAGE fallback thirty lines below removes its temp *and* notes the failure to do so;
`silence.write_json` does the same via `_discard_tmp`; `foreman.owner_queue` does it inline.
**No correctness impact** — every reader globs `*.json` and a `<shard>.json.tmp` never matches —
but `_shard_path` embeds run+batch+pid, so each denial leaves a uniquely-named file that
accumulates.

### Already filed — not re-filed
`coverage_map()` has no callers anywhere in `src/`, and `main()`'s `--coverage` reads
`SWEEP_COVERAGE.json` directly instead of going through it. Confirmed still true; this is open
order **`d411f780d347`** (MINOR, in `handoff/sweep37/REMAINING_QUEUE.md:278`). Left alone.

---

## worldseed.py — 440 lines — READ IN FULL — 1 finding

`_first`'s seeded fallback, the provenance tagging, `LAST_BUILD`'s "inputs not fully read"
banner, the designation-collision report and the uncapped `most_common()` distributions are all
correct and all do what their comments say. `build_all`'s `WORLD` regex runs over the whole
description. `to_fmg_query` emits only the four parameters Azgaar honours, and
`unreachable_by_url` names the rest.

### F8 — MINOR — the Magnitude band is parsed by digit-concatenation
`d2be0d5e0cc9` · LOCAL · worldseed.py:167-182

`int(re.sub(r"\D", "", band) or 0)` is right only for a bare `M<int>`. Reproduced in-process:
`'M3.52'` → tier **352**, `'𝔄 M3.52 ± 0.12'` → tier **352012**; `states = min(40, 6 + tier*3)`
then pins at the 40 ceiling with `cultures=23`, `religions=13`, silently. **Latent, not live** —
measured across all 216 `data/records/*.json`, catalogued Places carry only `unassayed` (12,411),
`M3` (16), `M2` (6), `M1` (2). But the decimal form is the charter's published Assay notation and
CLAUDE.md Hard Rule 3 calls band-only a deliberate interim, so the first real Assay pass turns
every assayed world into a saturated one. Remedy in the order: match `M\s*(\d+)`, clamp to the
declared M0–M10 scale, and `silence.note` anything out of range rather than clamping quietly.

### Already filed — not re-filed
The unreachable `"primitive"` entry in the `size` table is open at OWNER
(`handoff/queue/OWNER.md:755`), and the module now carries both the owner question and the
evidence block gathered for it (order `ad681057369a`). Left alone.

### xref
`worldseed.py:264-265` claims `build_all` has "seven importers … address_space …".
`address_space.py` does not import `worldseed` at all; there are **six** callers (burgs:276,
navtree:49, profile:155, render:222, sevenfold:289, verify_math:7286). The argument survives at
six. Folded into `bf22c557852e`.

---

## pick_model.py — 359 lines — READ IN FULL — 1 finding

`save_config` correctly gates on both `re.subn`'s match count and `replace_retry`'s boolean, and
says which of the two failed. `FAMILY_TIERS` ordering puts `qwen3` above the bare `qwen`
catch-all, as its comment requires. `resident()` sizes against total-minus-reserve; `fit_note`
against free — deliberate and documented in both docstrings.

### F9 — MINOR — a residency refusal is reported as "only embedding/vision models found"
`7b4ac0fde9ef` · LOCAL · pick_model.py:298-332

`scored` drops non-text models *and* residency-refused models into one bucket, and two
operator-facing lines then attribute the emptiness to the wrong cause. Line 311 calls refused
models "not usable for text generation"; lines 329-332 print *"Nothing usable installed (only
embedding/vision models found?). Pull a text model"* and exit 1 — telling somebody to pull models
they already have, and teaching them nothing about the 9.0 GB budget that actually refused them.
The REFUSED block above it contradicts the diagnosis. Remedy: count the two exclusions
separately and branch the message.

### Observation, not filed
`fit_note`'s "see MOE_MARKERS above, which is now STILL DISQUALIFYING" is a shade stronger than
the code: `MOE_MARKERS`/`is_moe` only choose the word "MoE" vs "dense" in a warning string;
nothing disqualifies on family, only on size. It is true *in effect* today (every marked family
exceeds the 9.0 GB budget). This sits inside the lines of an order already filed and since
partly repaired — `handoff/queue/LOCAL.md:408`, whose quoted "the cost is modest" wording is gone
from the current `fit_note` — so it is recorded here rather than re-queued.

### xref
`pick_model.py:127-128` cites `silence.py:370-373`; the construction is at `silence.py:453`.
Folded into `bf22c557852e`.

---

## coverage.py — 294 lines — READ IN FULL — nothing new beyond xrefs

The five-state model is honestly implemented. `state_of`'s strict precedence
CITED > READ > NO PAGE > NOT ATTEMPTED is reachable at every rung — the bug its comment describes
(NO PAGE unreachable) is fixed, and the `elif` guard is correct. `_state_of_file` keys the memo by
path **and** name, so the M23 collision cannot be re-introduced through the cache, and the
`cachekey.owns()` check is the only route to believing a file. `_so_save` advances `dirty` only on
a landed write. `main()` returns 1 and says so on a denied `COVERAGE.json` replace.

`report()`'s `--show` defaults to None (all shown) and `--show-best` defaults to 10 but announces
the remainder and accepts `0` for all — an announced, reversible display cap with an affordance
for the whole list, which is what the Hard Rule permits.

**`_p()` has no callers — deliberately.** It is the founding fixture for `liveness.py`
(liveness.py:10, :113, :179, :252) and is asserted by two `drill.py` nets (drill.py:57, :4484,
:4498). **Do not "clean it up."** Recorded here so a future sweep does not file it.

### xrefs (folded into `bf22c557852e`)
* `coverage.py:82` cites `foreman.py:324`; `refresh_coverage` is foreman.py:353-357 (`timeout=600`
  at :356).
* `coverage.py:216-217` says the `max(n, 1)` guards are at "lines 185-186 **below**". They are at
  coverage.py:202-203, and `measure()` is **above** `report()`. Wrong in three ways.

---

## propagation.py — 235 lines — READ IN FULL — nothing found

Read in full; **nothing found**, and its measured claims reproduce exactly today, which is worth
recording because the docstring at lines 66-82 explicitly warns that graph-derived figures go
stale:

```
python src/propagation.py            -> shelves 197, edges 3753
python src/propagation.py --from "Left 4 Dead" --to "Dragon Ball Z"
                                     -> distance 1.1258, hops 2, arrival 1,126 yr
```

against the comment's "Measured 2026-08-27 over 197 shelves / 3,753 edges: Left 4 Dead → Dragon
Ball Z is 1.126". Dijkstra is correct including the `src == dst` and disconnected cases.
`observed_mark`'s claim that its trailing `return 0` is unreachable is **true**:
`ascension_years(1) == round(1.0**1.35 - 1.0, 1) == 0.0`, so once `lag >= 0` the loop's last
iteration always matches.

Checked and found *not* to be a fault: the sampled probe output shows only `[^0]` and `[^17]`,
which looks like a 17-rung scale collapsing to two values. It is not — full ratification takes
`17**1.35 - 1 ≈ 45` years, so intermediate rungs need `0 ≤ lag < 45`, a real if narrow window
(`--years 200` on Pantheon: Greek → Marvel, arrival 175, lands at `[^11]`). The default probe
years 100/500/1500 simply straddle it. The wide mismatch between the 45-year vertical clock and
the millennium-per-unit lateral clock is a declared, reversible Axiom M3 convention that the
comment already flags as the owner's to re-scale, so it is not filed.

Minor, not filed: passing `--from` without `--to` silently falls through to the sample survey.

---

## compress_store.py — 143 lines — READ IN FULL — nothing found beyond xrefs

Read in full; **nothing found**. `store()` lands through a pid/thread-qualified temp, sweeps the
temp on a denial, and **raises** rather than returning a success dict for a blob that never
landed — so `generate.py` cannot write a poisoned `compressed_path` into the catalogue.
`_address_in()` correctly declines to invent a failure for a path that is not a 32-hex content
address, and `load()` verifies the hash and refuses loudly on a mismatch. That refusal is live:
`silent:compress_store.py:address-mismatch` was at ×10 in `state/failures.json` when I read it —
i.e. this check is currently catching real damaged blobs, which is also part of the argument for
F1 above, since that count is exactly the kind of thing `triage_swallowed`'s `[:3]` never names.

### xrefs (folded into `bf22c557852e`)
`generate.py:554` → the `compress_store.store(text, …)` call is at generate.py:629;
`generate.py:468` → the `"compressed_path"` write is at generate.py:648.
`catalog.py:97` is **correct** (`cmd_read` is at line 97 and does call `compress_store.load`).

---

## lognames.py — 52 lines — READ IN FULL — nothing found

Read in full; **nothing found**. Verified the `OWNER` fragments against the live tree rather than
against the comment: `pipeline.py --run` matches `overnight.STANDING`'s invocation exactly (so
the `--run` disambiguation order 08c1fd3932a4 is in effect on both sides); `read.py --run` matches
`overnight.py:1254`; every `<log>.log[:-4]` stem lines up with the job names
`foreman.kill_stalled_job` parses out of the stall report. The bare `sweep.py` exception is
correctly reasoned — every invocation of `sweep.py` runs the rebuild.

---

## COVERAGE

```
sweep_plan.record('run38',
  ['foreman.py', 'wiki_source.py', 'sweep_plan.py', 'worldseed.py', 'pick_model.py',
   'coverage.py', 'propagation.py', 'compress_store.py', 'lognames.py'],
  batch=7)
```
All nine read in full. No module in the brief was skipped or sampled.
