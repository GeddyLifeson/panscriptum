# Sweep run27 — Batch 09 Audit

Modules read in full (every line, no sampling):
- `src/hostcheck.py` — 955 lines
- `src/manifest_builder.py` — 478 lines
- `src/pick_model.py` — 357 lines
- `src/sevenfold.py` — 274 lines
- `src/catalogue_codex.py` — 215 lines
- `src/retry_synthesis.py` — 164 lines

Total: 2,443 lines. Also cross-read (not batch modules, needed to verify claims made by batch
modules): `src/pipeline.py` (phase_synthesis, ask/ask_pool_first — lines 337-390, 655-730),
`src/context_budget.py` (feats_block_budget and friends — lines 100-260). Also ran two small
verification scripts against live repo data (LOCAL_REGISTER.json duplicate-name check,
SWEEP_ROLL.json codex-title collision check) and one isolated reproduction of `sevenfold.shelve()`
with empty weights.

---

## hostcheck.py

### 1. [HIGH][CONFIRMED] `null_rate()` folds a failed baseline probe to 0.0 and caches it process-wide
`hostcheck.py:394-423`, specifically 419-420:
```python
rate = r.get("rate")
rate = 0.0 if rate is None else rate
```
`probe()` returns `rate=None` specifically to mean "the request failed, not zero hits" (see the
module's own docstring at lines 150-155 about this exact conflation). `null_rate()` immediately
discards that distinction and treats a failed baseline probe as a genuine 0% baseline, then caches
it forever for the rest of the process in `_NULL_CACHE` (module-level dict, line 390). Since
`null_rate()` is called from `score()` (line 460) for EVERY source that later gets scored against
that same host, a single transient network hiccup on the FIRST call to a shared "universal" host
(e.g. `en.wikipedia.org`, which is probed against dozens/hundreds of sources per run) permanently
zeroes that host's baseline for the rest of the sweep. Since `lift = rate - base` (line 463), an
artificially-low baseline inflates lift for every subsequent Wikipedia hit that run, which can
push otherwise-borderline hosts over `GOOD_LIFT` into a false "holds" verdict. Confirmed by direct
code trace; the scale of real-world impact (how often the first probe actually fails) is
SUSPECTED, not measured.
This is a **known-open** item; still true as read.

### 2. [HIGH][CONFIRMED] `judged_any` treats any reachable candidate as proof the search was adequate
`hostcheck.py:524-562`, specifically 534, 538, 546-562. In the `--repair` loop, for each failing
source `r`:
```python
judged_any = judged_any or not p["verdict"].startswith("UNREACHABLE")
...
if best[1] and best[1] != r["host"] and best[0] > DEAD:
    fixed[src] = best[1]                      # repoint
elif not judged_any:
    ... keeping r["host"] for now             # safe path
elif r["verdict"] == "partial":
    ... keeping r["host"]                     # safe path
else:
    fixed[src] = None                         # UNASSIGN
```
`judged_any` only needs ONE candidate (of potentially a dozen+) to come back non-UNREACHABLE —
it does not care whether that candidate was the actually-correct host. If the source's true
correct host times out/errors (UNREACHABLE) but some other, wrong candidate answers normally
(scoring WRONG FICTION), `judged_any` is True, `best` stays empty, and — unless the ORIGINAL
verdict was "partial" — the source falls into the final `else` branch and is **unassigned**
(`fixed[src] = None`, line 562), even though the one host that might actually hold the fiction
was never successfully tested. Confirmed via trace; matches the known-open description exactly.

### 3. [HIGH][CONFIRMED] `--repair` has no `--go` gate, unlike `--purge`/`--adopt`
`hostcheck.py:913-951` (main). `--purge` and `--adopt` both gate live writes behind
`dry=not a.go` (lines 933, 939). `--repair` has no such gate:
```python
sweep(only=a.only, repair=a.repair, workers=a.workers)
```
`sweep()`'s signature (`def sweep(only=None, repair=False, workers=8):`, line 486) doesn't even
accept a `dry` parameter. Inside `sweep()`, `if repair and wrong:` (line 524) leads straight to
`_land(F.HOSTS, hosts)` and `_land(UNFIT, unfit)` (lines 590-591) — live writes to
`data/WIKI_HOSTS.json` and `data/HOST_UNFIT.json` the moment `--repair` is passed, with no preview
option at all. **Known-open; still true as read.**

### 4. [MEDIUM][CONFIRMED] `--purge` help text contradicts the function's own docstring
`hostcheck.py:918-919`:
```python
ap.add_argument("--purge", action="store_true",
                help="remove rosters the audit rejected AND whose host was independently rejected")
```
`purge()`'s own docstring (lines 642-645) explicitly says: *"An earlier docstring claimed the code
also required the host to have been independently rejected; it never did (the check was loaded
and unused)... nothing is purged except sources a person explicitly listed with --source."* The
docstring was corrected; the `argparse` help string one function away, in the same file, still
carries the exact retracted claim. Anyone running `--help` is told the tool has a safety check
that the function's own comment says never existed.

### 5. [MEDIUM][CONFIRMED] `sweep()`/`adopt()` do a stale full-dict read-modify-write on WIKI_HOSTS.json across a long window
`hostcheck.py:489` (read) → `590` (write) in `sweep()`, and `862` (read) → `908` (write) in
`adopt()`. Both load the entire host map once at the top, then spend potentially many minutes
probing (network-bound, explicitly paced/throttled per `_get()`'s own docstring at lines 98-109),
then write the ENTIRE in-memory dict back at the end with no re-read, no merge, and no lock. The
module's own comment at lines 582-589 states plainly that `WIKI_HOSTS.json` has three writers
(`sweep()`, `adopt()`, and `scout.py`) and five readers. If `scout.py` registers a new host, or the
other of `sweep()`/`adopt()` finishes and writes, during this window, that write is silently
clobbered when this function's stale copy lands via `_land()`. This is the same class of bug
`_land()`'s own docstring (lines 66-79) exists to fix for the *file-replace* half of the problem
(`silence.replace_retry` outwaits a reader) — it does nothing for the *stale-data* half.

### 6. [MEDIUM][SUSPECTED] `probe()`'s name sample is capped and unranked — plausible contributor to the RED "reachable wiki" metric
`hostcheck.py:128`: `names = [n for n in names if n and len(n) > 1][:PROBE]` (PROBE=40, API mode);
`hostcheck.py:135`: `got = EP.fetch_raw(host, names[:12])` (raw mode, only 12). Names come from
`entities_by_source()` in whatever order `CHARACTER_SWEEP.json` rows happen to be in (line 383-386)
— not ranked by distinctiveness or likelihood of being on the wiki. For a source with a large
roster, the actually-identifying names could fall past position 40 (or 12, for raw-mode hosts) and
never get tested, producing a spuriously low hit rate that could tip a genuinely-correct host into
"WRONG FICTION"/low-lift territory. The 40-vs-12 split also means raw-mode hosts are judged on
roughly a third of the evidence API-mode hosts get, for no stated reason connected to API limits
(raw mode has no batched query at all, so the 40-name MediaWiki-batch justification in the
docstring at line 83 doesn't apply to it). Given the batch's extra focus on the 93%-reachable-host
metric, this truncation-of-untriaged-evidence is a plausible (not traced-to-a-specific-source)
contributor. Could be deliberate performance tradeoff — flagging as a question, not a certain bug.

### 7. [LOW][SUSPECTED] Aboutness check stacks a second truncation on top of #6
`hostcheck.py:199` (`titles = [t for t in titles if t][:sample]`, sample=12 default),
`hostcheck.py:218` and `787` (`sorted(rest, key=len, reverse=True)[:3]`, top-3 tokens only). Even
when a host has up to 40 hits, only the first 12 titles get their bodies read for the aboutness
veto, and only the top-3 longest distinctive tokens are searched for. Likely a deliberate
cost/latency tradeoff (fetching full wikitext per title is expensive) but compounds with #6's
evidence thinning. Not independently confirmed to have flipped a real verdict.

---

## catalogue_codex.py

### 8. [MEDIUM][CONFIRMED] Register dedup silently drops ~900 duplicate-named entries and can attach the wrong description
`catalogue_codex.py:104-112`:
```python
def load_register_index():
    ...
    for item in reg:
        key = norm(item.get("name"))
        if key and key not in idx:
            idx[key] = item
    return idx
```
Only the FIRST occurrence of each normalized name survives; every later duplicate is dropped with
no log, no warning. Verified directly against the live file: `LOCAL_REGISTER.json` holds 14,576
items but only 13,602 unique normalized names — **885 normalized keys have 2+ entries**, e.g.
`"Acid"` (x3), `"Ability Score Improvement"` (x2), `"Absorb Elements"` (x2). Any homebrew element
catalogued from the codex whose name collides with an unrelated register entry from a different
section/source gets whichever description happened to load first — not necessarily the right one
— with the collision itself never surfaced anywhere.

### 9. [MEDIUM][SUSPECTED] Codex-section matching is unranked bidirectional substring containment, first-match-wins
`catalogue_codex.py:130-137`:
```python
for k, t in sec_by_norm.items():
    if n and (n in k or k in n):
        title = t
        break
```
Matches the first codex section (in `sec_by_norm` dict/document order) whose normalized title
contains, or is contained by, the roll row's normalized name — no preference for exact or longest
match, no check for a second ambiguous candidate. I ran this against the live
`data/SWEEP_ROLL.json` + the actual codex file: currently only 6 roll rows have `entry_count == 0`
(the only rows this function considers), 2 of them match a codex section, and **no ambiguous
multi-match was observed** in this pass — so there is no live misfire right now. The mechanism
itself is still fragile (no uniqueness guard) and this project has a documented history of exactly
this kind of accidental substring collision (see `manifest_builder.py`'s own DC/Sword-Coast note,
finding #16 below). Flagging as a design question rather than a confirmed bug given current data
shows no collision.

### 10. [LOW][CONFIRMED] Silent, uncounted skips for non-matching or empty-content sections
`catalogue_codex.py:136-137` (`if not title: continue`) and `163-164` (`if not entries: continue`)
— rows that find no codex section, or whose section has zero contents after dedup, are dropped
with no counter, no log line, nothing distinguishing them from rows that were never attempted.
Given the "every source is fully catalogued" metric is RED, this path offers zero visibility into
why a given hostless/wiki-less source stayed uncatalogued via the codex route. (Scale check: with
only 6 eligible rows currently, this module's own contribution to the 17.2% figure looks small —
the bulk of that RED number is almost certainly driven by `catalogue_web.py`, which is outside
this batch.)

---

## retry_synthesis.py

### 11. [HIGH][CONFIRMED] Docstring's "byte-identical" claim is false — the sibling fix in pipeline.py was never applied here
`retry_synthesis.py:56-60`:
```python
def synthesise(c, rec):
    """Byte-identical prompt construction to phase_synthesis, so a retried source is not
    scored by a different method than its neighbours."""
    src = rec["source"]
    sample = sorted(rec["entries"], key=lambda e: -len(e.get("description", "")))[:14]
```
Compare `pipeline.py:phase_synthesis` (lines 655-730, esp. 693-707): it calls `_mined_feats(rec)`,
sorts feat-BEARING entries first, chunks them into groups of 14 with **every** feat-bearing entity
nominated across as many chunks as needed (best band across chunks wins), and only falls back to
a single `rest[:14]` chunk of description-only entries when a source has no feats at all. Its own
comment explicitly names this the fix for "BUGS m13, Hard-Rule-0-shaped, ruled by the owner
2026-08-24: FIX IT ALL" — the exact bug of a fixed sample-of-14 silently clamping the ceiling
nomination to whichever entity happened to rank in the top 14 by description length.
`retry_synthesis.py`'s `synthesise()` still has precisely that old, ruled-out construction: no
`_mined_feats` call at all, one flat `sorted(...)[:14]` by description length, hard Hard-Rule-0 cap
(line 60). A retried source with more than 14 feat-bearing entities — or any feat-bearing entities
ranked below the top 14 by raw description length — gets judged by a materially different, weaker
method than the main phase would have used, contradicting the docstring's stated purpose (parity
with neighbours). **Known-open; confirmed by direct comparison against pipeline.py.**

### 12. [MEDIUM][CONFIRMED] `save_side()` bypasses the two-writer contract: fixed-name temp, no retry, no `silence`
`retry_synthesis.py:43-47`:
```python
def save_side(d):
    tmp = SIDE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    os.replace(tmp, SIDE)
```
The module never imports `silence` (its import block, lines 21-31, has no such import). This is a
shared file (`data/SYNTHESIS_RETRY.json`, read by `load_side()` and by `--merge`) written with a
fixed temp-file name and a bare `os.replace()` — no `silence.replace_retry` backoff for the
Windows "destination held open by a reader" case that every other shared-file writer in this batch
handles (`hostcheck._land`, `catalogue_codex` via `silence.write_json`, `sevenfold` via
`silence.write_json`). Two concrete risks: (a) if `--merge` is reading `SIDE` via `load_side()` at
the exact moment a non-merge run calls `os.replace()`, Windows can deny the rename with no retry to
outwait it; (b) the fixed temp name means two concurrent non-merge invocations of this script would
race on the same `.tmp` path. **Known-open; confirmed by direct reading — no `silence` import
anywhere in the file.** (Note: `do_merge()` itself, lines 94-127, *does* correctly go through
`pipeline.write_record` for the actual catalogue records, per its own comment describing an
earlier, now-fixed bug — that part is fine. It's specifically `save_side`'s own file that's
unprotected.)

---

## sevenfold.py

### 13. [HIGH][CONFIRMED] World-level shelving reproduces the exact "giant component" bug its sibling (source-level) path was fixed to avoid
`sevenfold.py:204`, inside `build()`:
```python
inner = shelve(names, {}, depth=len(WORLD_TIERS))
```
An **empty** weights dict is passed for every source's per-world shelving, unconditionally. Trace
through `shelve()`/`seams()` (lines 99-150):
- `affinity_order(members, weights) if weights else sorted(members)` (line 105) — empty dict is
  falsy, so `order = sorted(members)` (plain alphabetical, no affinity used at all).
- `seams()` (lines 108-129): every gap defaults to `weights.get(..., weights.get(..., 0.0))` = 0.0
  since the dict is empty. `gaps.sort()` on all-equal-weight tuples `(0.0, i)` sorts purely by
  index `i` (stable sort, ties broken by original position) — so `gaps[:k-1]` always picks the
  first `k-1` **indices**, not the actual weakest seams.
- This makes `bounds = [0, 1, 2, ..., k-1, len(block)]`: `k-1` singleton blocks followed by **one**
  block holding everything else — at every recursive level.

I reproduced this directly (`shelve(members, {}, depth=2)` on synthetic member lists):
```
10 members -> top-level block sizes: [4, 1, 1, 1, 1, 1, 1]
20 members -> top-level block sizes: [14, 1, 1, 1, 1, 1, 1]
50 members -> top-level block sizes: [44, 1, 1, 1, 1, 1, 1]
```
This is exactly the failure the module's own docstring (lines 27-31) and `shelve()`'s own
docstring (lines 100-104, "Balance is by construction... so no branch can swell into the giant
component that wrecked every discovered scheme") describe fixing for the SOURCE tier, where real
weights come from `TI._graph()` (line 189, `top = shelve(srcs, w, ...)`). The WORLD tier
(multiverse/universe — the two tiers this project's own comments call "the leaves the tier system
exists for," line 260) never got any weights threaded through and silently reproduces the
"everyone lands in slot 0/1" collapse the docstring says was already fixed. Every source with more
than a handful of worlds will have almost all of them piled into a single multiverse/universe
coordinate while a few outliers get their own slot. This directly contradicts the "balanced by
construction" claim as applied to worlds specifically. Could conceivably be intentional (worlds
don't "need" affinity, alphabetical filing is fine) — but the empirically-reproduced imbalance is
the precise failure mode the design explicitly set out to prevent, so I'm calling it CONFIRMED
rather than a style question.

No other findings in this file — `affinity_order()`'s greedy walk, the padding loop (lines 147-149,
appears to be dead/defensive code — every recursive path already appends a coordinate at every
level; I could not construct a case that needs it), and the self-documented "OVER SPAN cannot
print" display invariant (lines 241-245, explicitly acknowledged in-code as "a GUARANTEE, not a
discovery... kept because it states the bound") all check out as described.

---

## pick_model.py

Read in full; no new bugs found. Specifically verified two things the file's own comments claim
were fixed, since this project has a history of "fixed" comments that weren't:
- `family_tier()` ordering (lines 55-62, comment at 40-54 claims "longer, more specific family
  strings MUST come before their own prefixes"): traced `qwen3:8b`, `qwen2:7b` (hypothetical),
  `llama3.1:8b`, `llama3:8b` through the tier-5-down-to-tier-1 outer loop — all resolve to the
  intended tier; the tier-1 bare `"qwen"` catch-all is never reached by anything that should have
  matched a more specific tier-5/4 entry first. Confirmed correct as currently written.
- `save_config()` (lines 104-134, docstring at 105-114 describes two historical false-success
  bugs): current code checks `re.subn`'s match count (`n == 0` → returns False, line 120-123) and
  checks `_sil.replace_retry`'s return value (line 129) before reporting success. Confirmed correct.

The only thing worth flagging as a note rather than a bug: `resident()`/the REFUSED gate (line 301)
sizes against **total** VRAM minus a reserve (line 295), while the informational `fit_note()` shown
per model (line 324) sizes against **free** VRAM (line 308) — two different numbers used for two
different purposes. This is explicitly documented as intentional in both functions' docstrings
(lines 174-176, 196-201), so not flagging as a defect.

---

## manifest_builder.py

### 14. [HIGH][CONFIRMED] The context_budget "" empty-string default this batch was told to look for
`manifest_builder.py:329-331`:
```python
import context_budget as _CBUD
budget = cfg.get("feats_block_chars")
budget = int(budget) if budget else _CBUD.feats_block_budget(cfg)
```
This is the live, unguarded caller of `context_budget.feats_block_budget(cfg)` — called with only
`cfg`, so it reads the prompt files itself. In `context_budget.py:233-253`:
```python
if system_text is None:
    try:
        with open(os.path.join(PROMPTS, "system_style.txt"), encoding="utf-8") as f:
            system_text = f.read()
    except Exception:
        system_text = ""
if template_text is None:
    try:
        with open(os.path.join(PROMPTS, "feats_prompt.txt"), encoding="utf-8") as f:
            template_text = f.read()
    except Exception:
        template_text = ""
```
If either prompt file is missing, moved, or unreadable at call time, the exception is swallowed and
the real prompt text is replaced with `""`. That understates `scaffold_chars(sys_used,
template_text)`, which **overstates** the resulting `content_budget_chars()` / `feats_block_budget()`
— the computed budget comes back bigger than what the real (non-empty) system+template prompt
actually leaves room for. `manifest_builder.py` then packs feats blocks up to that inflated budget
(line 338, `pack_feats(feat_rows, source_name, budget)`), and the REAL prompt assembled later at
generation time (with the real, non-empty system/template text) can exceed `num_ctx` and get
silently truncated by Ollama — which is the exact `ContextOverflow` scenario `context_budget.py`'s
own module docstring and `assert_fits()` (lines 191-201) exist to prevent. The failure mode is a
default that "hides an error in the dangerous direction" (lens #2) feeding directly into a Hard
Rule 0 concern (an oversized block silently truncated by Ollama). **Known-open; confirmed by
reading context_budget.py directly and tracing the call site.**

### 15. [MEDIUM][CONFIRMED] Manifest write is a raw truncating write, not the atomic pattern used by sibling modules in this batch
`manifest_builder.py:436-437`:
```python
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"jobs": all_jobs}, f, indent=2)
```
`out_path` is `output/index/manifest.json` (or `manifest.pilot.json`), which per `CLAUDE.md` is
read by `generate.py` (`python3 src/generate.py --manifest output/index/manifest.json`) — a
long-running, resumable process. This write goes straight to the real path with no temp file and
no `silence.write_json`/`replace_retry`, unlike `sevenfold.py` (line 267,
`silence.write_json(p, ...)`) and `catalogue_codex.py` (line 209, `silence.write_json(ROLL, ...)`)
in this same batch. A rebuild that races a live `generate.py` read, or is interrupted mid-write
(Ctrl-C, crash), can hand `generate.py` a truncated/invalid JSON manifest. The same raw-write
pattern is used for `output/index/unassigned_sources.md` (lines 455, 463) — lower stakes since
that's a human-read report file, not a pipeline input consumed by another running process.

### 16. [LOW][SUSPECTED] `load_record()`'s tie-break among equally-close candidates depends on `os.listdir()` order
`manifest_builder.py:90-100`. When two or more record filenames satisfy the containment test
(line 97) with the identical `abs(len(norm_fname) - len(norm_target))` score, the first one
encountered in `os.listdir(records_dir)` iteration order wins (`if best_score is None or score <
best_score`, strict `<`, so ties keep the first found). `os.listdir()` order isn't guaranteed
sorted/deterministic across filesystems. I did not find a live tied pair in the current
`data/records/` directory, so no confirmed misfire — flagging because this module's own comments
(lines 72-89) describe fixing exactly this family of file-matching bug twice already (the
Roger-Rabbit truncation and the DC/Sword-Coast-Adventurer's-Guide collision), and a silent,
filesystem-order-dependent tie-break is the same shape of fragility one step further out.

---

## Summary of what could produce a wrongly-unreachable host or a stalled catalogue (per the batch's extra focus)

- **hostcheck.py**: #1 (baseline folded to 0.0, cached process-wide) and #2 (judged_any evicting a
  host on a transient failure of the *right* candidate) are the two mechanisms most directly able to
  turn a real, reachable wiki into a permanently-unassigned source. #6/#7 (unranked, capped
  evidence sample) are secondary contributors that could produce noisy/low scores without an
  outright network failure.
- **catalogue_codex.py**: its contribution to the 17.2% "fully catalogued" figure looks small in
  absolute terms right now (only 6 zero-entry rows currently eligible, 2 matched) — the bulk of
  that RED number is very likely driven by `catalogue_web.py`, which is outside this batch and
  should be checked by whichever batch owns it. Within this module, #8 (silent register-dedup
  collisions) is the most concrete correctness risk, and #10 (silent skip counts) is the biggest
  visibility gap.
