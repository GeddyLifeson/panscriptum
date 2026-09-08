# sweep47 batch 15 audit

Modules read in full, every line: `src/read.py` (1554), `src/dashboard.py` (1197),
`src/rosetta.py` (793), `src/onomast.py` (640), `src/canon_backup.py` (504),
`src/catalogue_models.py` (339), `src/navtree.py` (335), `src/tempus.py` (274).
Total 5636 lines, matching the brief exactly. No module and no line range in this batch
was skipped or sampled.

## New verified findings

### 1. `read.py`'s cloud path accepts any non-None answer with no shape check (MAJOR)

`read._ask_ungated` calls `cascade_bridge.ask(system, prompt, schema)` directly, twice in
the "quick pool" loop and again in the `CASCADE_TRIES` backoff ladder, and both call sites
test only `if got is not None: return got`. `cascade_bridge.py`'s own module docstring
(the "STRUCTURED OUTPUT" section) says plainly that the schema is a *request* to a cloud
model, not a constraint the way Ollama's `format=` parameter is for the local arm, and
that "a cloud model can return perfectly well-formed JSON of entirely the wrong shape and
this layer has no way to tell" -- validating that shape is explicitly left to the caller.
The one caller in this codebase that does that validation is `pipeline.ask_pool_first`,
via `pipeline._pool_answer_usable`, which checks every key the schema marks `required`
(here, `"feats"`) is actually present before treating a cloud answer as usable, and falls
back to the local arm otherwise. `read.py`'s cloud calls do not go through
`ask_pool_first` -- they call `cascade_bridge.ask` directly -- and never gained the
equivalent check.

Consequence, traced through `read_entity`: a cloud provider that answers with a
well-formed dict lacking a `"feats"` key (e.g. `{"result": "no feats found"}`, `{"error":
"..."}`, or any other off-schema JSON) is treated as `got is not None`, so:
- `_chunk_put` caches `(got or {}).get("feats", [])` == `[]` for that chunk, permanently,
  under `data/chunkfeats/`, indistinguishable from a passage the model genuinely judged
  and found empty;
- the `for f in (got or {}).get("feats", []):` loop finds nothing and the chunk counts as
  **read**, not unanswered;
- if this happens across every chunk of an entity's evidence, `unanswered == 0`, the
  guard `if unanswered: return out` never fires, and the entity's record is written to
  `data/readfeats/` as complete with zero feats -- the exact "entity filed as having no
  feats in a passage that describes its feats" failure this module's own header names as
  the reason every other guard in the file exists, arriving through the one path nothing
  had checked for it.

Not purely theoretical: `cascade_bridge.py`'s own history log (in the same docstring)
records this exact class of defect being found and fixed at the phase-call sites in
`pipeline.py` after a live incident (four Marvel entrypass batches scoring 0/20 against a
"pool answering" proof, while the same batch put to the local model directly scored
20/20) -- `read.py`'s cloud calls are the one call site that never received the parallel
fix. (Response shapes that are non-dict, e.g. a bare JSON list, are not silent: `(got or
{}).get(...)` raises `AttributeError` on those and the entity is correctly counted
`errored`, not silently zeroed -- the risk is specific to a syntactically-valid dict that
is merely off-schema.)

Remedy is local to `read.py`: reuse `pipeline._pool_answer_usable(got, schema, None)` (or
an equivalent required-key check) as the acceptance test in both `CB.ask` call sites in
`_ask_ungated`, the same way `ask_pool_first` already does, before returning the cloud
answer or incrementing any "answered" counter.

### 2. `read.py --run` always exits 0, even when every entity errored (MAJOR)

`main()`'s `--run` branch calls `run(limit=a.limit, workers=w, cap_chunks=a.chunks,
all_entries=not a.persons_only)` and then unconditionally `return 0`. `run()` itself
returns nothing. `done["errored"]` is tracked and printed on the closing line
(`err_note`), but nothing in the count feeds the process exit code -- a pass in which
every single entity's `read_entity` call raised (all of them landing in `done["errored"]`)
still exits 0.

This matters concretely because `overnight.run()` (the supervisor helper that launches
`read.py --run` for the nightly cycle) branches on exactly this: `if p.returncode != 0:
tail(lf, name)` and reports `"rc=%d" % p.returncode` instead of `"ok"`. A totally-failed
reading pass -- one that accomplished nothing -- is therefore indistinguishable, at the
one layer built to notice, from a completely healthy one. This is the fault class named
in this sweep's brief as "an exit code that always says OK". Contrast with `navtree.py`
in this same batch, which was already corrected for precisely this shape (order
3726ed72236c: "the exit code is the number a scheduler actually looks at") and now
returns 1 when its audit found problems or its write was denied -- `read.py --run` has no
equivalent.

Remedy is local and small: `return 1 if done["errored"] else 0` (or similar) from `run()`,
propagated through `main()`'s `--run` branch instead of the unconditional `return 0`.

## Already-open orders verified against current code

Per the brief's instruction, checked every one of the 20 already-open orders against the
code as it stands today rather than re-filing. Findings:

**Confirmed already fixed** (code now matches what the order asked for; no action needed,
left open only for whoever closes orders to mark them):
- `read.py` **05294ca33e1f** (final line omits UNANSWERED) -- `run()`'s closing print now
  includes `unanswered_note` with the exact wording the order asked for.
- `read.py` **a693102e217a** (stale transport/ctx comments) -- both comments (the CHUNK
  arithmetic block and the `CASCADE_TRIES` note) have been rewritten to state the true
  premises and explain why the stale number is harmless; they self-cite this order.
- `read.py` **d9fbd60efd0f** (CLOUD_CHUNK conditional inert) -- both call sites now use
  `size = CHUNK` unconditionally and cite this order in a comment.
- `read.py` **aefd1a2c9343** (--one truncation + dead row fields) -- `--one`'s feat print
  is uncut, and `source`/`category` are no longer written onto queue rows.
- `read.py` **ef26ed6029e7** (--limit silent, no marker) -- `run()` now computes and
  prints `deferred` and a `limit_note` naming the partial run.
- `read.py` **cdf0d2367cba** (four direct subscripts drift risk) -- `work()`'s aggregation
  now uses `.get()` for all five counters.

**Confirmed still open**, matching the code exactly as the order describes (no new
information, not re-filed):
- `read.py` **fc08e056e1ab** (own-page normalization mismatch between `read_entity`'s
  `_norm_q` compare and `_queue_row`'s raw `.strip().lower()` compare) -- both forms are
  still present and still disagree.
- `dashboard.py` **aad11acb1183**, **cefcad5fc513**, **ffdaa9aa7288** -- `main()` still
  calls `_ESC.assert_clear` unconditionally before serving; `step4_gate_open()` is still
  read-only with no enforcing caller; the per-line escalation-log parse at `safety()` still
  swallows a bad line with a bare `continue` and no `silence.note`, and still lets a
  non-dict-but-valid-JSON line raise past the inner guard into the outer "unreadable"
  branch.
- `onomast.py` **ae25c89f0179** (`register_for` genre/feature blend unreachable),
  **2caa35dc6a30** (merge drops unschemaed prior record silently), **371140b9fb9d**
  (`pick`'s never-repeat guarantee has an unratcheted fallback) -- all three match the
  current source exactly.
- `onomast.py` **845dbaec182f** (coin-exhausted returns a rejected name) -- **partially**
  addressed since this order was filed: the exhausted path (`coin_well_formed`) is now
  loud (prints to stderr and tags `silence.note` distinctly for a clean vs. unusable
  fallback), but the function still *returns* the same known-malformed-or-duplicate name
  it just tested and rejected, which is exactly what the order's remedy said not to do.
  Diagnosis is fixed; the underlying return-a-rejected-value defect the order is actually
  about is not. Left open rather than re-filed since the order already covers it.
- `tempus.py` **7099a092abd3**, **0291835411d9**, **1a9c237dda4d** -- all three are live
  OWNER-rung disputes about caller-graph counting method (whether `verify_math.py`
  counts as a "reader") and about dead reference data (`DEGENERATE_TIME`,
  `concordance_now`); `DEGENERATE_TIME` is in fact read at `verify_math.py:722`, which
  is already the crux of the standing disagreement between 7099a092abd3 and
  1a9c237dda4d rather than new information -- not re-litigated here.
- `catalogue_models.py` **47c8def059e3** and **70f5e5150f8b** -- both `where` fields
  point at `cosmology_graph.py` and `feats_index.py` respectively, not at
  `catalogue_models.py`; this module is cited in both only as the precedent whose fix
  (the "not cut" `available_sample`/error-text handling, visible in `ask_provider` and
  `sweep()`) the other two files still lack. `catalogue_models.py`'s own code shows no
  version of either truncation.
- `rosetta.py` **68459d3e739b** -- the code-side fix (`assays_by_host`, `check(...,
  by_host=...)`) is landed and working (verified by reading `check()` and `main()`'s
  `--check` branch); the order is correctly left open as a *data coverage* question
  (7 of 8 standing scales still can't be scored because too few of their named entities
  carry an assay on the same wiki), which is exactly how the order is worded.

Not independently verifiable from this batch's modules alone (their evidence lives in
files outside batch 15, or depends on process/runtime state rather than source):
`read.py` a8464e348c5e, 2cb8756deb0a, d2e44a766769; `dashboard.py` 3e11c452ff67,
728d9e99e9ec, f90795d5c6bd; `onomast.py`'s cross-references are all internal so that one
is fully covered above.

## Modules with no new findings

`canon_backup.py` -- read in full, no open orders against it, none found. The module is
unusually thorough about verifying its own writes (snapshot re-hash-on-read, gated
manifest write, `replace_retry` on the restore path) and about refusing rather than
degrading (missing canonical paths raise instead of producing a smaller "successful"
backup). No silent truncation, no could-not-measure-as-confident-value, no unchecked
write found anywhere in it.

`navtree.py` -- read in full, no open orders against it, none found beyond confirming it
is a good counter-example to finding 2 above (its own exit code already accounts for a
denied audit-record write and for non-empty `problems`).
