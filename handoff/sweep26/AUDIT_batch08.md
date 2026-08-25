# AUDIT batch08 — sweep26

Files in scope, all read in full, start to end, no sampling:

- `src/feats.py` — 991 lines
- `src/completeness.py` — 455 lines
- `src/tiers.py` — 347 lines
- `src/navtree.py` — 272 lines
- `src/tells.py` — 215 lines
- `src/cosmology_graph.py` — 153 lines

Total: 2,433 lines across 6 modules.

Cross-referenced against `BUGS.md`, `NEXT_STEPS.md`, `HANDOFF.md`, `src/silence.py`
(`write_json`, `replace_retry`, `note`), `src/endpoint.py` (`api_url`, `detect`, `MODE_RAW`),
`src/weave.py`/`src/pipeline.py` (sibling writers of `SHARED_STAGE_GRAPH*`/`RESONANCE_GRAPH.json`),
`src/sevenfold.py` (navtree's actual tier source), and the prior `handoff/sweep25/AUDIT_batch08.md`
(same file set minus `navtree.py`/`cosmology_graph.py`, plus `feats_index.py`/`sweep_plan.py` which
are out of scope this run). Every carried-forward item below was independently re-read against the
CURRENT source and re-verified, not copied; line numbers are this run's own.

---

## M16 — verified against current source, chain-by-chain

Read `feats.py` end to end and checked every step of the described chain against the live file.
**It holds exactly as described, with only cosmetic line-number drift** (the file grew from the
version the finding was originally written against):

1. **`api()` bare `except Exception`** — now at `feats.py:170-174`. Returns `None` after
   `retries` (default 2) attempts, identical to a clean 404. Confirmed.
2. **`alive()`** — `feats.py:177-178`. `retries=0`: one attempt, no retry budget. Confirmed.
3. **`resolve_hosts()`'s slug loop** — `feats.py:282-288`. On every candidate slug failing
   `alive()` (including from one bad probe), `known[src] = None` is written, and persisted via
   `silence.replace_retry` (the write itself is correctly atomic — only the *decision* to write
   `None` is the bug).
4. **The membership check** — `feats.py:265`: `if src in known: continue`. Confirmed as
   membership, not `known.get(src)` — `True` for a `None` value, so a source that failed one
   network blip is never reconsidered by any future `--hosts` run.
5. **`evidence_for()` writes a cache file on the empty path** — `feats.py:786-808`. The `out`
   dict (`:800-802`) has no `fetch_failed`/`error` flag; a transport-caused empty `pages` dict
   produces a byte-identical evidence record to a genuine absence, and it's written unconditionally
   via `silence.replace_retry` at `:807`, cached forever (short of `--no-cache`).
6. **`roll()` skips the whole source** — `feats.py:841-844`: `if not h: ... continue`. A `None`
   host (falsy) drops the source from the job list entirely, no counter incremented for it.

**Verdict: M16 still holds exactly as described. No drift in mechanism**, only in line numbers.

### Extending M16: the SAME failure shape recurs inside `discover()` and `fetch()`, on every call, not just host resolution

Not previously filed under M16's own text (though covered in spirit by the already-open **m106**,
"the shared root of M16/m93/m94/m107" for `endpoint.py`). Traced independently this run because
the task asked specifically for other places in `feats.py` where a transport failure becomes an
indistinguishable "nothing here":

- **`discover()`** (`feats.py:311-368`) makes two `api()` calls — `allpages` (`:348-349`) and
  `search` (`:358-359`). If either transiently fails, `api()` returns `None`, and both call sites
  immediately do `(ap or {}).get("query", {})...` / `(sr or {}).get(...)` — a `None` collapses to
  `{}` and the loop over it simply adds nothing. `discover()` returns just `[name]` (from the
  unconditional `add(name)` at `:335`), which reads identically to "this wiki genuinely has no
  evidence subpages for this entity" even though the request never completed.
- **`fetch()`** (`feats.py:427-453`) does the same at `:443-446`: a chunk's `api()` call returning
  `None` on transport failure collapses to `(d or {}).get("query", {}).get("pages", [])` = `[]`,
  so those titles are silently absent from `out` — indistinguishable from titles that don't exist.
- Both feed directly into `evidence_for()` (`:784-785`, `titles = discover(...); pages =
  fetch(...)`) on **every single call**, not just the host-resolution path M16 describes. A
  mid-roll transport hiccup on an otherwise-healthy host can produce a thin or empty
  `pages_read` list that then gets permanently cached by the same unconditional write at
  `feats.py:807` M16 already names.
- `_page_exists()` (`:376-381`) has the identical shape (`(d or {}).get("query", {}).get("pages",
  [])` → `False` on both transport failure and genuine absence) but — see below — is dead code, so
  it does not currently contribute live damage.

**Severity: this is arguably the more consequential instance of the M16 pattern**, since it fires
on the routine path of every `roll()` entity, not only during host discovery. Filed here as new
detail on the already-open `m106` family; the fix `m106` already calls for (propagate a
distinguishable failure signal through `api()`'s callers) would need to reach `discover()` and
`fetch()`, not only `alive()`/`resolve_hosts()`.

---

## feats.py — other findings (all re-confirmed against current line numbers; all already tracked)

- **`resolve_title()`/`_page_exists()` dead code — m80, re-confirmed.** `feats.py:376-424`.
  Grepped the whole repo: the only occurrences of `resolve_title(` / `_page_exists(` are their own
  `def` lines. `resolve_title`'s docstring describes fixing a measured 17,148-entry loss (catalogue
  name ≠ wiki title, e.g. "Hulk (Bruce Banner)" vs. wiki's "Hulk"); it is never spliced into
  `discover()`/`fetch()`/`evidence_for()` (`:784`), so that loss is, per the call graph, still
  live and unmitigated. **Unchanged from sweep24/25.**
- **`aplimit=500`/`srlimit=50`, no continuation — m82, re-confirmed, now instrumented.**
  `feats.py:348-361`. `_CAP_BOUND` increments on a MediaWiki `continue` token but nothing follows
  up with an `apcontinue`/`sroffset` loop — the measurement now exists (`:75-85`, printed at
  `roll()`'s end, `:912-917`) but the cap itself is unfixed. Progressed from "unmeasured" to
  "measured, still open" since the last sweep.
- **`_RATE_LIMITED`/`_CAP_BOUND` unlocked across `ThreadPoolExecutor` workers — re-confirmed.**
  `feats.py:73, 85, 162, 351, 361` vs. `done` in `roll()` which IS correctly `lock`-protected
  (`:869/881-899`). Diagnostic-only underccount, no entity data corrupted.
- **Stale `silence.note()` line labels — m81, re-confirmed, cosmetic.** `feats.py:159, 171, 451,
  743, 878` (e.g. `"feats.py:125"` now fires from line 159). Doesn't change behavior; misleads
  anyone jumping from the failure ledger to source.
- **`remine()` is dead code but honestly disclosed** (`feats.py:811-828`) — its own 2026-08-25
  comment says "This function currently has no callers." Not filed as a finding.

---

## completeness.py — re-confirmed findings, no new ones found

- **`category_size_probe()`/`_cs_load()` — unlocked shared-dict race + shared non-unique temp
  filename across `ThreadPoolExecutor` workers.** `completeness.py:66-119`, sharpest at
  `:110-116`: `cache = _cs_load()` returns the same dict object to every thread; `json.dump`
  iterating it while another thread inserts a key can raise `RuntimeError: dictionary changed size
  during iteration` (silently absorbed by the wrapping `except Exception: silence.note(...)`,
  dropping that thread's write); the fixed `tmp = _CS_CACHE_P + ".tmp"` name (not PID/thread
  qualified, unlike `silence.write_json`'s pattern) lets two racing `open(tmp, "w")` calls
  interleave. `_cs_load()`'s blanket `except Exception: pass` (`:76-77`) then treats the resulting
  corruption identically to "no cache yet" and silently resets to `{}}`, forcing a re-probe against
  the exact fandom traffic pattern the module's own docstring says got the machine IP-banned once.
  **Confirmed unchanged.**
- **`host_reachable()` gates on `endpoint.api_url()`, which is API-mode-only, so every RAW-mode
  wiki reports permanently unreachable / 0.0% coverage even when perfectly readable.**
  `completeness.py:194-203` (docstring + the `EP.api_url(host)` call at `:195`), used at `:259`
  and referenced at `:268`. `endpoint.api_url()` (`endpoint.py:176-184`) returns a usable base URL
  only when `detect(host)["mode"] != MODE_RAW`; for a RAW-mode host (dandwiki.com is the
  canonical example — `feats.py`'s own docstring calls it out as "answers every API call with
  403") `api_url` returns falsy, `host_reachable` short-circuits to `False` at `:197-198` before
  ever trying the real transport (`EP._get`/`fetch_raw`) that could actually read the wiki. Already
  filed in `NEXT_STEPS.md` §2.D as part of the `m106` family, "reproduced live against
  www.dandwiki.com." **Re-confirmed unchanged at these exact line numbers.**
- **`land()` is correctly guarded** (`:342-407`) — empty-result refusal, `SHRINK_FLOOR` (0.5)
  partial-loss refusal, and it actually checks and propagates `silence.replace_retry()`'s boolean
  return (`:401-406`), unlike most other writers in this batch. **No finding; worth naming as the
  positive counter-example** to the pattern below.

---

## tiers.py — CLEAN in the last sweep; one real finding this run corrects that classification

Re-read in full. `_components()` (`:203-223`), the nesting/monotonicity assertions (`:119-120`),
the runtime containment check in `main()` (`:307-319`), and `main()`'s `unaddressed[:6]`
(`:298`)/`deliberate_joins()`'s `shared.get((a,b),[])[:3]` (`:273`) are all as previously found:
correct, non-tautological, and the two `[:N]` slices are stdout-only display truncations — the
full `unaddressed` count prints uncapped first, and `TIERS.json` (written via `silence.write_json`
at `:341`) carries every source. **Not a Hard Rule 0 violation; consistent with `feats.py`'s own
`_show()` pattern.**

- **NEW: `main()` ignores `silence.write_json()`'s return value and unconditionally reports
  success.** `tiers.py:338-342`:
  ```python
  out = os.path.join(HERE, "data", "TIERS.json")
  # ATOMIC: ... this writer was missed at the time. 2026-08-25.
  silence.write_json(out, charted, indent=2, ensure_ascii=False)
  print(f"\nwrote {out}")
  ```
  `write_json` returns `False` (never raises) when `replace_retry` exhausts its 5 attempts against
  a denied rename — exactly the shape `completeness.land()` two sections above checks for and
  `cosmology_graph.py`/`navtree.py` (below) are already tracked as NOT checking for. `TIERS.json`
  has real concurrent readers: `address_space.py:108,316`, `profile.py:135`, `verify_math.py:757,
  769,1271`, and — the one that matters most — `pipeline.py`'s own phase 6
  (`pipeline.py:490,1478-1491,1597`), which the file's own comment says reads phase 5's freshly
  written `TIERS.json` **in the same run**. `pipeline.py`'s phase 5 (`phase_cosmology`,
  `:1376-1400`) calls this exact same `tiers.chart()` and lands the result through its own,
  separately-checked `land_json` — so the dual-writer situation is benign (both paths are
  independently atomic and idempotent over the same deterministic computation) — but `tiers.py`'s
  **own** standalone `main()` entry point (`python3 src/tiers.py --write`, i.e. an operator running
  the module directly rather than via the pipeline) can silently report "wrote {out}" while the
  file on disk is stale, if a reader is holding it at that moment. `NEXT_STEPS.md`'s enumerated
  "write_json return ignored" bucket names `cosmology_graph.py`, `navtree.py`, `pantheon.py`,
  `genre.py`, `coverage.py`, `zfighters.py`, `resync_roll.py`, `scope.py` — **`tiers.py:341` is not
  on that list and was marked CLEAN by the last sweep of this batch; it belongs in the same
  bucket.**

---

## navtree.py — re-confirmed findings only, both prior fixes verified live in current source

- **m11 (false digit-prefix match) — VERIFIED FIXED.** `sources_under()` (`navtree.py:144-155`)
  now requires the `+ "."` boundary on both `startswith` arms (`:153`), matching the fix comment
  in place. Re-derived the failure mode by hand (a source shelved at `"0.1.2"` vs. node `"0.1.20"`)
  and confirmed the current code no longer false-matches it.
- **m41 (non-deterministic tie-break renaming nodes) — VERIFIED FIXED.** `register_for()`
  (`:157-168`) and the hyperverse-naming block (`:170-190`) both now use `max(set(x), key=lambda
  v: (x.count(v), v))` — name as an explicit secondary sort key breaks the hash-order tie
  deterministically. Matches the in-place fix comment exactly.
- **`silence.write_json()` return value ignored — already tracked (`NEXT_STEPS.md` bucket),
  re-confirmed at current line.** `navtree.py:259-264`: `if args.write and not problems:
  silence.write_json(OUT, data, ...); print(f"\nwrote {OUT} ...")` — no check of the boolean
  return. Same shape as `tiers.py` above and `cosmology_graph.py` below. `NAVTREE.json` is read
  live by the Registry Terminal build path (`build_terminal.py`, out of this batch's scope) —
  a denied rename here would silently leave a stale nav tree in place while the CLI reports
  success.
- **`audit()` / `build()` logic re-checked, no new findings.** The "empty" branch detection
  (`v["n"] == 0`, `:250`), the child-sum consistency check (`:213-223`), and the
  source-then-worlds two-pass `touch()` construction (`:88-109`) were traced by hand against the
  `TIERS` tuple ordering and are internally consistent — a node's `"n"` is only ever incremented by
  the worlds pass, so `n == 0` correctly and only ever means "sources here, no catalogued worlds,"
  matching the module's own stated purpose. Confirmed navtree draws its tier coordinates from
  `SEVENFOLD.json` (`:44-46`), not `TIERS.json` — `sevenfold.py` **declares** a fixed 7×7×7×7×7
  shape rather than deriving one from clustering, so every source/world tier field is a real
  integer 0–6 by construction; the "could a `None` tier value collapse unrelated nodes onto one
  key" concern this raised on first read does not apply, because `sevenfold.py` never emits `None`
  there. No finding.

---

## cosmology_graph.py — both findings already known and tracked; re-confirmed at current lines with live cross-file verification

- **Hard Rule 0: `pair_shared` truncated to 8 per pair, then persisted under the key
  `"shared_sample"` and consumed downstream as real evidence.** `cosmology_graph.py:86-87`:
  ```python
  if len(pair_shared[p]) < 8:
      pair_shared[p].append(name)
  ```
  written whole (not re-sliced) into `data/SHARED_STAGE_GRAPH.json` at `:143` (the `"shared_sample"`
  field). Already filed in `NEXT_STEPS.md` §2.F's Hard Rule 0 open-caps list. **What this run adds:
  live cross-file confirmation that this is the exact instance sibling modules were already fixed
  for, and it's still live.** `pipeline.py:1795` and `weave.py:478` both build the identical
  `"shared_sample"` field for their own resonance-graph outputs and both carry the same inline
  comment: `# WHOLE list -- Hard Rule 0, ruled 2026-08-24` (`weave.py`'s adds "(key name kept:
  resonance.py reads it)"). **`cosmology_graph.py` is the one file in this family that was not
  brought in line with that 2026-08-24 ruling** — it still truncates the exact field named as
  needing the whole list. Confirmed the file `cosmology_graph.py` writes
  (`OUT = data/SHARED_STAGE_GRAPH.json`, `:55`) is the same file `resonance.py:141` reads
  (`graph_path or os.path.join(HERE, "data/SHARED_STAGE_GRAPH.json")`), and `resonance.py:146`
  consumes `p.get("shared_sample", [])` directly as evidence — so the 8-item cap is not a display
  artifact, it reaches a real downstream consumer, per `NEXT_STEPS.md`'s own note that it found "a
  third consumer, `propagation.py:46`."
- **`silence.write_json()` return ignored.** `cosmology_graph.py:141-149` — already named
  specifically in `NEXT_STEPS.md`'s write_json-ignored-return bucket; re-confirmed unchanged. Same
  shape as `tiers.py`/`navtree.py` above: `silence.write_json(OUT, {...}, ...)` with no captured
  return, followed unconditionally by `print(f"\nwrote {OUT}")` (`:149`). The file's own inline
  comment (`:138-139`) explicitly names `propagation.py` and `resonance.py` as live readers who
  "would silently trust" an empty/stale graph — making the unchecked return here the more
  consequential instance of this pattern in the batch, since the docstring already identifies the
  exact hazard it fails to guard against.
- Everything else in the 153-line file (`_pause_for`-style host/IDF weighting logic doesn't apply
  here — that's `feats.py`; `build_graph()`'s `1.0/math.log(n+1.5)` weighting, `UBIQUITOUS_CUTOFF`
  decay, `components()`'s BFS) reads correctly against the module's own docstring. `src_entities`
  (`:68,76,88`) is computed and returned but never used by `main()` — dead data, not a bug.

---

## tells.py — one re-confirmed regex-precedence bug, already tracked; nothing new found

- **`"not merely X but Y"` alternation precedence — already flagged in `NEXT_STEPS.md`,
  re-verified by execution this run.** `tells.py:70`:
  ```python
  "not merely X but Y": r"\bnot merely\b|\bnot simply\b|\bnot just\b.{0,40}\bbut\b",
  ```
  `|` is the lowest-precedence regex operator, so this is three independent alternatives and only
  the third requires a trailing `but`. Confirmed live:
  ```
  >>> import tells; tells.scan("It was not merely impressive on its own, no further clause.")
  {'not merely X but Y': 1}
  >>> tells.scan("It was not simply impressive by itself, nothing more said.")
  {'not merely X but Y': 1}
  ```
  Both false-positive with zero `but` anywhere in the sentence. Correct form groups the
  alternation: `r"\b(?:not merely|not simply|not just)\b.{0,40}\bbut\b"`.
- Everything else — `_anchor()`'s sentence-boundary rewrite (`:127-134`), the
  `_LEX`/`_COMPILED` control-character guard (`:139-141`), `prompt_section()`'s claim that the
  prompt block and the audit are generated from one shared list (`:158-197`) — checked and true;
  `LEXICAL`/`STRUCTURAL`/`DISCOURSE` feed both `_COMPILED`/`_LEX` and `wrap(sorted(...))`
  identically, so drift between what's banned and what's checked is structurally impossible, as
  claimed. One cosmetic redundancy noted, not a bug: `"tapestry"` (`LEXICAL`, `:47`) and
  `"tapestry of"` (`LEXICAL_FICTION`, `:62`) both match on the same input containing "tapestry of",
  double-counting that occurrence under two different tell names — harmless (rates, not raw
  presence, drive the audit per the module's own docstring) but worth pruning if the two lists are
  ever revisited.

---

## Summary of severities (this batch)

- **MAJOR (re-confirmed, unchanged mechanism):** `feats.py` M16 full chain; `feats.py`
  `resolve_title()`/`_page_exists()` dead code (m80); `completeness.py`
  `category_size_probe()`/`_cs_load()` threading race; `completeness.py` `host_reachable()`
  RAW-mode false-unreachable (m106 family); `cosmology_graph.py` `pair_shared` 8-item cap feeding
  `resonance.py`/`propagation.py` as real evidence.
- **MAJOR (new detail on an open finding):** `discover()`/`fetch()` in `feats.py` share M16's
  exact transport-failure-as-absence shape, and fire on every `roll()` entity, not only host
  resolution.
- **MINOR:** `feats.py` unlocked `_RATE_LIMITED`/`_CAP_BOUND` counters; `feats.py` `aplimit`/
  `srlimit` no-continuation cap (m82, now instrumented, still unfixed); `cosmology_graph.py`
  ignored `write_json` return (already tracked, but its own docstring names the exact live-reader
  hazard it fails to guard against); `navtree.py` ignored `write_json` return (already tracked);
  `tells.py` `"not merely"` regex precedence (already tracked, re-verified live).
- **MINOR — corrects a prior CLEAN classification:** `tiers.py:341` ignores `silence.write_json()`'s
  return value and unconditionally prints success; `TIERS.json` has real same-run readers
  (`pipeline.py` phase 6) and is not on `NEXT_STEPS.md`'s enumerated ignored-return list despite
  matching the pattern exactly. The last sweep of this batch (sweep25) marked `tiers.py` CLEAN;
  this is the one thing it missed.
- **COSMETIC:** `feats.py` stale `silence.note()` line labels (m81).
- **CLEAN, no findings beyond the above:** `navtree.py` core `build()`/`audit()` logic (m11/m41
  both verified fixed in current source); `tells.py` structural/discourse pattern set generally;
  `completeness.py` `land()` (positive counter-example — correctly checks its atomic write).
