# BATCH 06 audit — run #25

Files read END TO END, no sampling: `src/magnitude.py` (1026 lines), `src/silence.py` (426
lines), `src/address_space.py` (346 lines), `src/tuning.py` (263 lines), `src/propagation.py`
(214 lines), `src/retry_synthesis.py` (152 lines). Total 2,427 lines.

Cross-referenced against `NEXT_STEPS.md` §3 (run #24's unworked findings) before writing this up.

---

## silence.py — audited as infrastructure (the atomic-write primitive the whole project depends on)

### CLEAN as infrastructure
`write_json` (silence.py:250-287) is correctly built: it writes to a **pid+thread-qualified** tmp
name (`"%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())`, line 276) — so `write_json`
itself does **not** have the cross-process tmp-collision defect `magnitude.py:967` has (see
below). The target path is only ever touched via `os.replace`, so a crash mid-`json.dump` can
corrupt the *tmp* file but never the real target. On a persistent `PermissionError` (Windows
denies rename while a reader holds the target open) it retries 5x with backoff and returns
`False` rather than raising — matches its own docstring. It **can** raise if the `json.dump` call
itself fails (e.g. a non-serializable object) — that is not a contract violation (the docstring
only promises "never raises on a denied replace"), but see finding S1 below for what it means in
practice.

`replace_retry` (silence.py:223-240) is a correct implementation of the documented behaviour:
retries only `PermissionError`, records via `note()` on exhaustion, returns `False`/`True`. `note()`
(silence.py:290-322) and `append_line` (silence.py:187-220) are both `except Exception: pass`
at the outermost layer by explicit design (the recorder must never be the thing that breaks a
run) — that is the correct shape for a *recorder*, not a silent-failure finding.

### S1 — [KNOWN generalised to the FULL list, VERIFIED] every caller of `write_json` in the whole
tree ignores its return value.

Task instructions asked for the tree-wide grep beyond the three examples NEXT_STEPS named
(`navtree.py:263`, `catalogue_codex.py:203`, `scope.py:119`). Full list, all 32 call sites, **every
one a bare statement, none checked**:

```
address_space.py:337   allsweep.py:436        cascade_bridge.py:499   catalogue_aurora.py:150
catalogue_codex.py:203 catalogue_models.py:157 cosmology_graph.py:141 coverage.py:185
feats.py:827           generate.py:58          genre.py:241            grounding.py:239
halo.py:171            ingest_doc.py:112       navtree.py:263          onomast.py:399
pantheon.py:261        recover_folder_records.py:149  recover_folder_records.py:156
reference.py:333       resync_roll.py:68       scope.py:119            sevenfold.py:267
sweep_plan.py:107      tiers.py:341            weave.py:472            weave.py:474
weave.py:475           weave_index.py:268      weave_index.py:270      zfighters.py:478
```
(`verify_math.py:3532` is the one exception — it's a test that DOES check the return.)

VERIFIED: this is a straight grep + manual inspection of each call site's surrounding lines —
every one is a naked `silence.write_json(...)` statement (or, for `weave.py`/`weave_index.py`,
several in a row) with no `if not ...:` guard anywhere. On a persistent Windows lock (5 retries
exhausted, ~3s of backoff), every one of these 30 modules will print "wrote X" / return success
while the file never landed — the exact failure shape the docstring at silence.py:251-268 warns
about, now shown to be universal rather than three isolated misses.

### S2 — [NEW, same shape, smaller blast radius] `replace_retry`'s return value is *also* ignored
at most of its call sites.

Of the ~36 `replace_retry(...)` call sites in the tree, the following are bare (unchecked) calls:
`catalogue_web.py:79`, `coverage.py:76`, `feats.py:298`, `feats.py:807`, `gpu_lane.py:256`,
`gpu_lane.py:310`, `hostcheck.py:79`, `identity.py:222`, `ingest_doc.py:259`, `magnitude.py:817`,
`read.py:600`, `read.py:759`, `read.py:879`, `scout.py:65`. (Others — `chain.py:118/199`,
`completeness.py:401`, `dashboard.py:346`, `foreman.py` x6, `pick_model.py:129`, `pipeline.py:476`,
`runguard.py:80`, `standards.py:907` — correctly gate on the return.) Same failure mode as S1: a
denied rename is recorded via `note()` internally but the caller proceeds as if the file landed.
VERIFIED by grep + inspection.

---

## magnitude.py — the assay engine

### M1 — [KNOWN, VERIFIED deeper] `magnitude.py:911-996` `run_batch()`: cross-process lost-update
on `data/ASSAYS.json`, plus a **non-PID-qualified tmp name** that can crash the batch.

- Each `run_batch()` invocation loads `done = json.load(OUT)` **once** at start (line 936-942)
  into an in-process dict, then on every completed entity re-serializes the **entire** `done`
  dict and writes it back (lines 967-969). Two concurrent invocations (e.g. one `--host X` and
  one `--host Y` batch, both plausible operator commands) each hold their own stale snapshot;
  whichever finishes last silently overwrites the other's newly-scored entities. Classic
  read-once/write-whole lost update.
- The tmp name is `tmp = OUT + ".tmp"` (line 967) — **not** pid-qualified, unlike `silence.write_json`'s
  own tmp naming. Two concurrent processes share this exact path.
- The retry loop (lines 975-983) catches **only** `PermissionError`. VERIFIED live:
  ```
  >>> os.replace('nonexistent_tmp_file_xyz.tmp', 'target_xyz.json')
  FileNotFoundError: [WinError 2] The system cannot find the file specified: ... -> ...
  ```
  If process B's `open(tmp,"w")` truncates/rewrites the same tmp path after process A has already
  consumed it via `os.replace`, B's own subsequent `os.replace(tmp, OUT)` call finds `tmp` gone and
  raises `FileNotFoundError` — uncaught by the `except PermissionError` clause — which propagates
  out of `work()`, out of `ex.map`, and crashes the whole `run_batch()` (the `with ThreadPoolExecutor`
  block re-raises the first worker exception on `list(ex.map(...))`). This confirms the
  "raise an uncaught FileNotFoundError, crashing the batch" claim exactly.
- Additionally: this write bypasses `silence.write_json` entirely and hand-rolls an inferior
  duplicate of the same logic (no pid qualifier, only catches one exception type) inside a module
  that otherwise imports and uses `silence` for everything else. VERIFIED by reading lines 967-983
  against `silence.write_json`/`replace_retry`.

### M2 — [NEW, minor, same shape] `magnitude.py:814-817` `calibrate()`'s write of
`data/CHARTER_REGRESSION.json` also uses a non-PID-qualified tmp name (`_cr + ".tmp"`), though it
does call `silence.replace_retry` (so at least `PermissionError` is handled). A second concurrent
`--calibrate` run would hit the same `FileNotFoundError` race as M1. Low likelihood in practice —
`--calibrate` is not typically run concurrently with itself — flagged for completeness.
UNVERIFIED beyond static reading (didn't spin up two processes).

### M3 — [NEW, cosmetic] `magnitude.py:235` tags its `silence.note()` call `"magnitude.py:151"` —
a stale line number (the actual line is 235, inside `quantity_scores`). This is the same
"stale `silence.note()` line tags" class NEXT_STEPS already names for `foreman.py`, `feats.py`,
`scout.py`; adding this file to that list. Cosmetic but undermines the grep-by-site workflow
`silence.py`'s own docstring promises for `health.py --failures`.

### Observation, not a bug: `compose()`'s budget path is dead code
`compose(entity, cand, epoch, budget, head_note=None)` (magnitude.py:505-530) implements a
round-robin evidence-budget trimmer, but its **only call site** (line 591) always passes
`budget=None` — confirmed via `grep -n "compose("`, one caller in the whole tree. Not a defect
(the module is explicit that `evidence_dropped_to_fit` is always 0 today, kept only so a future
budget can't be silent, line 730) — just noting the branch is currently unexercised.

### Rest of the file — CLEAN
Guards 1-5 (`verify()`, `AXIS_RE`, `_HANDOFF`, `saturated()`, `quantity_scores()`), the
pool-then-local-then-split transport ladder in `assay_entity()`, `_split_assay()`'s
slice-until-exhausted loop (never drops a row, verified by reading the `while i < len(rows)` loop
at lines 456-462), and `candidates()` (line 396-411, `cap=None` by default and the one real call
site at line 576 never passes a cap) all correctly honour Hard Rule 0 as documented — oversized
entities are DEFERRED or SPLIT, never trimmed. `settled()` (line 885-908) correctly treats
`DEFERRED` as unfinished. No other correctness bugs found on a full read.

---

## address_space.py

### A1 — [KNOWN, re-verified LIVE] header/docstring bit-count is stale.
Header (lines 3, 26-27) claims **74 bits / 10 bytes**, 5 fields
`[hyperverse|universe|galaxy|star|planet]`. Live run:
```
WIDTHS {'hyperverse': 3, 'xenoverse': 3, 'metaverse': 3, 'multiverse': 8,
        'universe': 6, 'galaxy': 38, 'star': 27, 'planet': 1}
TOTAL_BITS 89   bytes 12
```
8 fields, 89 bits, 12 bytes — confirmed by direct execution, not inference.

### A2 — [KNOWN, re-verified LIVE] `shelfmark()`'s docstring contradicts its own code.
Docstring (lines 172-176): *"H and X print as '?' because they are uncharted."* Code two lines
later (182-183): `f"Ω › H{f['hyperverse']} › X{f['xenoverse']} › ..."` — prints real integers.
Live proof, an entity whose source has **no** entry in `TIERS.json`:
```
>>> A.assign('TestSource::TestWorld', {})   # tiers={} — genuinely unknown
>>> A.shelfmark(that address)
'Ω › H0 › X0 › Mt.0 › Mv.0 › U-15 › G.bbc37aa8 › P.0'
```
An address for a completely uncharted world prints `H0`/`X0`, indistinguishable from a real,
charted hyperverse-0/xenoverse-0 world. Root cause: `fit()` inside `assign()` (lines 251-252)
maps `None` → `0` before packing, with nothing downstream marking the value as unknown.

### A3 — [NEW] Comment directly contradicts the code eleven lines below it.
Lines 127-129: *"hyperverse and xenoverse are NOT fields. They are not unknown values awaiting a
survey... reserving bits for them would invite filling them in."* The very next statement,
`FIELDS = [...]` (lines 130-139), makes `hyperverse` and `xenoverse` the **first two** entries —
real bit-widths, packed, unpacked, and printed exactly like every other field. This comment block
is a leftover from before the file's own "CHARTED 2026-08-20" rewrite (lines 97-105, which
explicitly describes computing real H/X values via `tiers.py`) and was never removed when the
code changed underneath it. Distinct from A2 (A2 is about the *printed value*, A3 is about a flat
contradiction between a comment and the very next lines of code). VERIFIED by reading.

### A4 — [KNOWN] `"universe": 1 << 6` (line 135) is a hardcoded literal 64, not derived from
`_continuities()` (lines 66-72, which reads the real continuity-group count from
`CONTINUITY_GROUPS.json`, e.g. 168) — despite the module's own banner "THE WIDTHS ARE DERIVED, NOT
CHOSEN" and its own table (line 35: "24 continuities per hyperverse, from the 168 the catalogue
resolved"). `_continuities()` is called exactly once in the whole file, only inside `main()`'s
print statement for a ratio — never to size a field. VERIFIED by reading + grep confirming
`_continuities()`'s only other reference.

### Minor
`UNADDRESSED = None` (line 120) is documented but referenced nowhere else in the tree (`grep -rn
"UNADDRESSED" src/*.py` → one hit, its own definition) — dead constant.

### Otherwise CLEAN
`pack()`/`unpack()` round-trip correctly (module's own `assert` in `main()` passes, and my live
run of `assign()` produced a consistent, decodable address). `seed_from_card()`'s
identity-vs-measurement split is coherent with its stated rationale.

---

## tuning.py — CLEAN, full re-read, no new findings

Matches run #24's clean verdict. `workers(0)` correctly returns `0` (the previously-fixed
floor-vs-ceiling inversion the docstring at lines 226-244 describes is verified fixed by reading
the actual `min(requested, n) if requested is not None else n` logic). `regime()`'s
answering-buckets-AND-measured-success-rate gating, the `RECHECK_SECONDS` cache, and
`_ollama_host()` reading the same `config.yaml` key every other module reads are all internally
consistent. No caps, no unguarded shared writes (this module writes nothing to disk).

---

## propagation.py — CLEAN as a standalone module, one cross-module risk flagged

Dijkstra (`shortest()`, lines 85-112) is a standard correct implementation. `ascension_years()` /
`arrival_years()` / `observed_mark()` correctly implement the two-independent-clocks model the
module's own commentary (lines 139-158) describes fixing from an earlier bug — traced the logic
by hand, no bug found. No caps, no writes (read-only against `SHARED_STAGE_GRAPH.json`). Matches
run #24's clean verdict for the module's own code.

### P1 — [NEW, UNVERIFIED against live data] third consumer of the same capped/superseded graph
NEXT_STEPS §1.F already flags that `cosmology_graph.py:86-87` caps `pair_shared` at 8 and that
`weave.py` computes a better, uncapped graph but writes it to a **different** file
(`SHARED_STAGE_GRAPH_IDF.json`) that `resonance.py` doesn't read. `propagation.py:46` reads
`data/SHARED_STAGE_GRAPH.json` — the same `cosmology_graph.py`-produced file, **not** the IDF one
— making it a *third* consumer of the stale/superseded graph, not just `resonance.py` as
previously noted. Checked whether this specific cap (`pair_shared`, an 8-item *sample* list for
display) actually corrupts what `propagation.py` uses: it does not — `propagation.py` only reads
`p["weight"]` (cosmology_graph.py:141-146), and the weight accumulator `pair_w` is itself
uncapped. However, `cosmology_graph.py:143` (`if w >= 1.0`) drops any pair below weight 1.0 from
the graph file entirely before it's ever written — by the module's own weighting formula
(`w = 1/math.log(n+1.5)`, per shared entity), a single entity shared by exactly two sources
contributes only ≈0.8, i.e. **below the cutoff**, so two sources sharing exactly one thinly-shared
entity would never appear as an edge at all. `propagation.py` would then report such a pair as
fully `DISCONNECTED (no shared furniture at any remove)` — indistinguishable from genuinely
sharing nothing — when a real (if weak) link exists. This is arithmetic inference from reading
`cosmology_graph.py`, not a live-data proof; flagged UNVERIFIED for a future run to confirm with
`python src/propagation.py --from <thin-pair-a> --to <thin-pair-b>` against real data.

---

## retry_synthesis.py

### R1 — [KNOWN, VERIFIED against current pipeline.py source] docstring's "byte-identical" claim
is false, and remains false against the current `phase_synthesis`.
Line 56-58's docstring: *"Byte-identical prompt construction to phase_synthesis, so a retried
source is not scored by a different method than its neighbours."* Read `pipeline.py:655-742`
(current `phase_synthesis`) directly to check: it ranks entries by whether they carry a **mined
feat** (`with_feats`, sorted by feat length), paginates **every** feat-bearing entry into 14-item
chunks (`chunks = [with_feats[i:i+14] for i in range(0, len(with_feats), 14)]`, line 706), asks
once per chunk, and keeps the best-banded answer across all chunks — fully uncapped for
feat-bearing sources, falling back to a single ranked-by-description chunk only when there are
literally no feats at all. `retry_synthesis.synthesise()` (line 60) instead does:
```python
sample = sorted(rec["entries"], key=lambda e: -len(e.get("description", "")))[:14]
```
— sorted by raw **description length**, ignoring feats entirely, and takes exactly one 14-entry
slice, permanently discarding the rest. A retried source with 15+ feat-bearing entries gets a
materially worse ceiling nomination than the main phase would give it, and the result is folded
in permanently via `--merge` with nothing in the record marking it as retry-quality. Matches and
confirms NEXT_STEPS's finding at this exact line.

### R2 — [KNOWN] direct unguarded writes to shared files, bypassing the Two-Writer Contract.
`save_side()` (lines 43-47) and `do_merge()`'s per-record write (lines 109-112) both hand-roll
`open(tmp,"w")` + `json.dump` + `os.replace` directly — no `silence.write_json`/`replace_retry`,
no pid-qualified tmp name, no retry on `PermissionError`. `save_side` writes
`data/SYNTHESIS_RETRY.json`, the file this script's entire resumability depends on; `do_merge`
writes directly into `data/records/*.json` — the exact file the module's own docstring (lines
10-19) says a second writer must never race. **There is no runtime guard anywhere in this file
checking the pipeline is actually stopped before `--merge` runs** — only an operator-facing print
statement (line 147: `"merge with: ... (pipeline must be stopped)"`) asks nicely. Matches
NEXT_STEPS's finding at these lines.

### Otherwise CLEAN
`failed_sources()`, `load_side()`, and `main()`'s `todo` filtering (excludes anything already in
the side file or already carrying a `synthesis` block) are simple and correctly scoped. No other
correctness bugs found on a full read.

---

## Summary of modules read end to end and their verdict

| module | lines | verdict |
|---|---|---|
| silence.py | 426 | infrastructure CLEAN; every caller of its two return-value contracts is the finding |
| magnitude.py | 1026 | 1 known+deepened (M1), 2 new minor (M2, M3) |
| address_space.py | 346 | 2 known re-verified live (A1, A2), 2 new (A3, A4) |
| tuning.py | 263 | CLEAN |
| propagation.py | 214 | CLEAN (own code); 1 new cross-module risk flagged (P1, unverified) |
| retry_synthesis.py | 152 | 2 known, both confirmed against current pipeline.py source |
