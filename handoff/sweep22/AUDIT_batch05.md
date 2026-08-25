# Batch 05 audit — read.py, custodes.py, address.py, tempus.py, catalogue_codex.py, module_index.py

Full line-by-line pass. No sampling. Two seeded questions (m79 rate-window contamination in
read.py; the custodes.py:229-230 "derived" claim) were run down at source; both write-ups below
answer them explicitly, not just tag them.

Every dynamic claim below (duplicate-entity counts, codex parse mismatches, ambiguous section
matches, module counts, `floor` table cross-reference) was actually executed against the live
repo/data, not inferred from reading alone. Commands used `C:/Users/imarl/miniconda3/python.exe`
and touched no files outside this repo; nothing was written to panscriptum-export.

---

## HIGH

### 1. read.py — m79 CONFIRMED: the chunk-rate counter mixes cache hits, historical totals, and real model calls

**VERIFIED.**

`run()`'s `work()` closure feeds the progress line and ETA from one counter:

```python
# read.py:990
done["chunks"] += out["chunks_read"]
```

`out["chunks_read"]` is set in `read_entity()` as:

```python
# read.py:734-736
out = {"entity": name, "host": host, "pages": sorted(text),
       "chunks_read": len(chunks) - unanswered, "chunks_unanswered": unanswered,
       "chunks_reused": reused,
```

`chunks_read` counts every chunk that got *an answer from any source* — including chunks served
from the per-chunk disk cache (`_chunk_get`, read.py:573-583, near-instant, no model call) mixed
indistinguishably with chunks that required a real Cascade/local-GPU call
(read.py:685-701). There is no separate "chunks answered by a real model call this pass" counter
— `chunks_reused` is computed (read.py:684, 693-696) but **never read anywhere in `run()`**; it
is written into the per-entity JSON and then dropped on the floor by the aggregator.

Worse: an entity that is *already fully cached* short-circuits at the very top of `read_entity`
and returns the **stored historical record** without touching a single chunk this pass:

```python
# read.py:608-614
if os.path.exists(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
```

That returned record's `chunks_read` is whatever it was when the entity was *originally* read
(could be dozens), and `work()` adds that whole historical number to `done["chunks"]` for zero
real work done in this pass.

So `done["chunks"]` — the numerator of `crate` at read.py:1014-1024 — is a blend of three
completely different costs: (a) free, instant full-entity cache hits contributing large stale
numbers, (b) near-free per-chunk cache hits, and (c) real model calls costing seconds (cloud) to
minutes (GPU-benched). `RATE_WINDOW=300` (read.py:222) makes this a *rolling* rather than
from-`t0` average — a real partial mitigation the code's own comments document (read.py:1010-1013)
— but the window still blends whatever mix of (a)/(b)/(c) fell inside the last 300 seconds. Right
at a "to GPU" transition — the queue exhausts its cheap/cached prefix and starts handing real
chunks to a benched or saturated card — the window is still full of the fast entries that just
finished, so the reported chunks/s and ETA are inflated for up to 5 minutes before decaying to
something honest. This is exactly the shape m79 describes and exactly the failure mode the file's
own comment at read.py:1010-1013 already diagnosed once (the from-`t0` version: "1,595 chunks per
second and an ETA of 0.0 hours for eight hours of work") — the rolling window narrowed the blast
radius but did not remove the underlying conflation, because the counter itself still does not
distinguish a cache hit from a model call.

**Repair sketch:** track `done["chunks_new"]` (chunks that actually invoked `_ask`, i.e.
`chunks_read - reused` when the entity was processed this pass, and 0 when the entity returned
from the top-level full-record cache) separately, and drive `crate`/ETA off *that*, not off
`chunks_read`.

---

### 2. read.py — entity-record write uses a non-per-writer temp filename; the same race the file already fixed once, live in the data

**VERIFIED**, including empirically confirming the trigger condition exists in the current corpus.

```python
# read.py:756-759
os.makedirs(os.path.dirname(path), exist_ok=True)
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
silence.replace_retry(tmp, path)
```

`tmp` is derived only from `path` — no pid, no thread id. Compare `_chunk_put`, in the same file,
which was *already patched* for exactly this defect:

```python
# read.py:592-597 (comment) / 596-598 (fix)
# A PER-WRITER TEMP NAME. This was `p + ".tmp"`, derived only from the cache key, so two
# workers answering the same passage at once opened and truncated ONE file -- each
# writing over the other mid-dump, then both renaming it. `replace_retry` makes the
# rename safe; nothing made the WRITE safe. ...
tmp = "%s.%d.%d.tmp" % (p, os.getpid(), threading.get_ident())
```

The `read_entity` write at line 756 never received the equivalent fix. `queue()` builds `todo`
from every `(host, entity)` row with no dedup (read.py:884-965), and `ThreadPoolExecutor.map`
(read.py:1095-1096) can schedule two rows for the same `(host, name)` onto two different worker
threads concurrently — each computing the identical `cache_path(host, name)` and therefore the
identical `tmp = path + ".tmp"`. Two threads opening the same tmp path in `"w"` mode race exactly
as `_chunk_put`'s own comment describes: each truncates and writes over the other mid-dump before
either renames.

I ran this against the live corpus rather than treating it as theoretical:

```
total (host, name) pairs in the current queue-eligible corpus: 83,139
duplicate (host, name) pairs:                                   1,371
e.g. 3x ('forgottenrealms.fandom.com', 'Jim Darkmagic')
     2x ('en.wikipedia.org', 'Red Star of the Solar Federation')
```

1,371 pairs is not a corner case — with `workers` in the 8-16 range (read.py:1079,
`--workers auto`), any run of reasonable width has a real chance of two of those duplicates
landing on concurrent threads. A corrupted `readfeats/*.json` from an interleaved write either
crashes the next reader that tries to parse it (caught by the self-healing block at
read.py:608-621, which deletes and re-earns it — so it degrades to "silently loses one entity's
cached record and re-pays for it," not a hard crash) or, worse, produces a file that happens to
parse but contains a spliced mix of both writers' JSON fragments, which is a data-integrity
failure with no self-healing catch at all.

**Repair sketch:** give the write at line 756 the same `"%s.%d.%d.tmp" % (path, os.getpid(),
threading.get_ident())` treatment `_chunk_put` already uses, or dedupe `todo` in `queue()`/`run()`
so the same `(host, name)` is never scheduled twice in one pass.

---

### 3. custodes.py:229-230 — the "derived" claim is false; the table is a third hand-typed copy, not a reference

**VERIFIED**, cross-checked against assay.py at source.

```python
# custodes.py:221-224 (comment, preceding the table)
# DERIVED from assay()'s own attestation table rather than restated. A second hand-written table
# of evidence quality would be a duplicate mechanism for a quantity the charter has already fixed
# -- the same error as the withdrawn tempo table (X.10 §4), and it would drift the moment either
# copy was edited. Quality is the complement of the interval that grade already earns:
```

```python
# custodes.py:229-230
_ATT_BASE = {"Witnessed": 0.10, "Instrumented": 0.08, "Transcribed": 0.20,
             "Reconstructed": 0.40, "Disputed": 0.55}
```

This is not derived from anything — it is a bare dict literal in custodes.py, with no import from
and no reference to `assay`. The values are byte-for-byte identical to a dict that already exists,
independently hand-typed, inside `assay.py`:

```python
# assay.py:630-631, inside interval_from_hands()
floor = {"Witnessed": 0.10, "Instrumented": 0.08, "Transcribed": 0.20,
         "Reconstructed": 0.40, "Disputed": 0.55}.get(attestation, 0.30)
```

So there are now (at least) two independent hardcoded copies of "attestation grade → base
uncertainty" in this codebase — `assay.py`'s `floor` dict and `custodes.py`'s `_ATT_BASE` — plus
a third, differently-scaled table in `assay.py` itself (`_RAW_SIGMA`/`SIGMA_BY_ATTESTATION`,
assay.py:304-316, same five grade names, different numeric scale). The comment at custodes.py:221
explicitly names the failure mode this constitutes ("it would drift the moment either copy was
edited") and claims the code avoids it. It does not: nothing in custodes.py imports
`assay.floor`, `assay.SIGMA_BY_ATTESTATION`, or any shared source of truth. If `assay.py:630-631`
is ever edited (e.g. a grade's base value is tuned), `custodes.py`'s `ATTESTATION_QUALITY` table
(custodes.py:234, built from `_ATT_BASE`) silently goes stale and every Custos's
`evidence_sensitivity` weighting (custodes.py:254-259) is computed against the wrong quality
figure — precisely the outcome the comment says is impossible.

**Repair sketch:** either import `assay`'s `floor`/`SIGMA_BY_ATTESTATION` table directly and derive
`_ATT_BASE` from it, or move the one true table into `assay.py` and have both `interval_from_hands`
and `custodes.py` read the same name.

---

### 4. catalogue_codex.py:196-197 — bare `open(ROLL, "w")` on the shared roll state file

**VERIFIED**, cross-checked against the sibling script that writes the same file correctly.

```python
# catalogue_codex.py:195-197
if not args.dry_run and written:
    with open(ROLL, "w", encoding="utf-8") as f:
        json.dump(roll, f, indent=2, ensure_ascii=False)
```

`ROLL` is `data/SWEEP_ROLL.json` (catalogue_codex.py:35) — the shared roll manifest read by
several other scripts (`allsweep.py:170`, `pipeline.py:1205`, `manifest_builder.py`,
`resync_roll.py`, `catalogue_web.py`'s `load_roll`). This is a direct, non-atomic, truncate-on-open
write to that file, with no temp file and no `silence.replace_retry`.

Contrast the established, already-correct pattern for the exact same file, in `catalogue_web.py`:

```python
# catalogue_web.py:69-76
def save_roll(roll):
    # Atomic for the same reason the record write beside it is: SWEEP_ROLL.json is written from
    # three worker threads here and read elsewhere by `load_roll` and `resync_roll.py`, BOTH of
    # which do an unguarded `json.load`. A truncating write interrupted mid-dump therefore does
    # not degrade anything gracefully -- it kills the next run of either script outright.
    import silence as _sil
    tmp = ROLL + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(roll, f, indent=2, ensure_ascii=False)
    _sil.replace_retry(tmp, ROLL)
```

The codebase already knows, in writing, exactly why this file needs atomic replacement
("kills the next run of either script outright"), and `catalogue_codex.py` does not do it. If
`catalogue_codex.py --dry-run` is omitted and the process is interrupted (Ctrl-C, OOM, crash)
between `open(ROLL, "w")` and the `json.dump` completing, `SWEEP_ROLL.json` is left truncated and
every other script's unguarded `json.load(ROLL)` breaks on its next run.

Note in passing, out of this batch's scope but directly adjacent: `catalogue_web.py`'s own
`save_roll` (quoted above) uses a *fixed* `tmp = ROLL + ".tmp"` rather than a per-writer name, even
though its own comment says it's called "from three worker threads" — that looks like the same
race class as read.py finding #2 above, just in a file outside this batch. Flagging for a separate
pass, not claiming it here.

**Repair sketch:** route this write through `catalogue_web.save_roll(roll)` (or copy its
tmp+`silence.replace_retry` pattern locally) instead of a bare `open(...,"w")`.

---

## MEDIUM

### 5. read.py — GPU benching is bypassed for the oversized-prompt (re-split) path

`_local_carded` has two branches:

```python
# read.py:503-523
def _local_carded(c, system, prompt, schema):
    c = dict(c, model=fallback_model(c))
    if len(prompt) <= CHUNK + 2000:
        got = P.ask(c, system, prompt, schema, timeout=360)
        if got is None:
            _GPU_DOWN_UNTIL[0] = time.time() + GPU_BENCH
        return got
    head, _, body = prompt.partition(chr(10) + chr(10))
    merged = {"feats": []}
    for i in range(0, len(body), CHUNK):
        got = P.ask(c, system, head + chr(10) + chr(10) + body[i:i + CHUNK],
                    schema, timeout=180)
        merged["feats"].extend((got or {}).get("feats", []))
    return merged
```

Only the first branch (prompt fits in one local call) sets `_GPU_DOWN_UNTIL` on a `None` result.
The second branch — used whenever a cloud-sized (`CLOUD_CHUNK`) prompt falls back to the local GPU
and has to be re-split — calls `P.ask` in a loop with a 180s timeout per piece and never benches
the card no matter how many of those sub-calls come back `None`. Given the extensive documentation
elsewhere in this same file about exactly this failure mode (read.py:474-496, the "1,168 of them
UNANSWERED" postmortem), leaving one of the two local code paths outside the benching mechanism
looks like an oversight rather than a deliberate choice — a saturated card can eat N separate
180s timeouts in this branch, each with zero benefit, before the caller ever backs off. Undetermined
whether this path is hit often in practice (it only fires when `_CASCADE_OK` was true when the
chunk was read but the local fallback is reached anyway with a `CLOUD_CHUNK`-sized prompt), so
flagging as MEDIUM rather than HIGH.

### 6. module_index.py — the classification table has not kept pace with the codebase; "grouped by stage" no longer describes what the page shows

`GROUPS` (module_index.py:23-37) names 50 unique modules across six stages. `src/` currently holds
95 `.py` files. I ran the actual classification:

```
46 of 95 modules fall through to "Everything else" (module_index.py:68-74), including:
  custodes, tempus, propagation, derivation, resonance, scale_theories, sweep_plan,
  cosmology_graph, entity_match, grounding, ledger, ... (46 total)
```

Nothing crashes and nothing is silently dropped — the `set(mods) - placed` fallback
(module_index.py:68) correctly catches everything not named in `GROUPS`, so this is not a Hard
Rule 0 violation. But the module's own stated purpose is "collects them ... grouped by the stage
of the machine they serve, so onboarding is a read of one page instead of eighty-seven headers"
(module_index.py:4-6) — with essentially half the codebase (including two files audited in this
very batch, `custodes.py` and `tempus.py`) landing in an unstaged catch-all, that promise is no
longer true for a new reader. `GROUPS` needs the ~46 missing names sorted into (or a new stage
added for) before the generated page delivers what its docstring claims.

Also, separately: `GROUPS` still lists `"wikipedia_source"` (module_index.py:26), which is not a
file in `src/` anymore — harmless (filtered by `if n in mods` at line 59) but a stale name worth
removing.

---

## LOW

### 7. read.py — `cap_chunks` truncation folds into `skipped` indistinguishably from genuine filtering

```python
# read.py:661-668
chunks.sort()
chunks = [(t, c) for _, _, t, c in chunks]
if cap_chunks:
    chunks = chunks[:cap_chunks]
skipped = sum(len(b) for b in text.values()) // size - len(chunks)
```

`cap_chunks` defaults to `None` (uncapped, matching Hard Rule 0) and is only ever non-`None` via
the explicit `--chunks` CLI flag (read.py:1107-1108, documented "omit to read every chunk of every
page") — this is a judgment call (an opt-in test/measurement knob), not a live default violation.
But if it *is* set, `skipped` is computed after the cap is applied, so chunks dropped purely by the
cap are counted in the same `chunks_skipped` field (read.py:737) as chunks genuinely filtered out
by the mention/action-verb tests. A record produced under `--chunks N` cannot be told apart, from
its own JSON, from one produced uncapped where the same chunks were filtered for content reasons.
Worth a distinct field (`chunks_capped`) if `--chunks` is ever used against real (non-test) runs.

### 8. read.py — two benign, unlocked check-then-act reads (no data corruption, just imprecision)

- `_gate()` (read.py:291-300): `_GATE_STATE["at"]`/`["regime"]` read and refreshed with no lock;
  concurrent threads can both pass the staleness check and both re-fetch `tuning.regime()`
  redundantly. Self-correcting, at most wastes one extra call every ~120s.
- `fallback_model()` (read.py:433-470): `_FALLBACK_MODEL[0]` is a lazy, unlocked singleton; two
  threads racing the first call both hit the Ollama `/api/tags` endpoint and compute the same
  (idempotent) answer. Wasteful, not wrong.

### 9. read.py — `--one` debug print caps displayed feats to 12; the saved record is not affected

```python
# read.py:1120-1121
for f in out["feats"][:12]:
    print("   %-14s %s" % (f["axis"], f["feat"][:104]))
```

This is a console-display truncation on the single-entity debug path only. `out["feats"]` itself —
and whatever `read_entity` already wrote to disk — is the full, uncapped list. Not a Hard Rule 0
violation; noted for completeness since the audit brief calls out every `[:N]` slice.

### 10. custodes.py — `dispersive=True` on Lumen is dead data

```python
# custodes.py:204
tilt=0.0, evidence_sensitivity=0.0, dispersive=True,
```

`dispersive` is set once and never read anywhere else in the file (confirmed by search — the only
other occurrence is a comment, custodes.py:321). The actual widening mechanism,
`staleness_widening()` called from `convene()` at custodes.py:322, is a standalone function of
`distance`/`years_since` alone; it has no reference to the `CUSTODES` dict or to Lumen specifically.
The adjacent comment ("Lumen's contribution: dispersive, not directional") reads as if the code
below it draws on Lumen's entry, but structurally it does not — the widening fires identically
whether or not "Lumen" exists in `CUSTODES` at all. Cosmetic/documentation drift, not a
computational error (Lumen's `tilt=0`/`evidence_sensitivity=0` already correctly make him
contribute nothing directional to `_custos_reading`).

### 11. tempus.py — `apparent_lag_years` returns different key sets on the two branches

```python
# read.py N/A — tempus.py:88-92
d, path = P.shortest(adj, shelf_a, shelf_b)
if not path:
    return {"lag_years": None, "note": "no shared furniture; relation is mediated or absent"}
return {"distance": round(d, 4), "lag_years": P.arrival_years(d), "path": path,
        "note": "A sees B as B stood this many years ago"}
```

The no-path branch omits `distance` and `path` keys entirely rather than setting them to `None`.
A caller doing `result["distance"]` unconditionally would `KeyError` on the no-path case. Checked
the one caller in this batch's reach, `pipeline.py:1489-1500` — pipeline.py is out of this
batch's scope so I did not do a full audit of it, but a quick look shows it accesses
`lag.get(...)`-style rather than direct indexing in the surrounding block, so this may not bite
today. Flagging the shape mismatch as a latent API footgun rather than a confirmed live crash.

### 12. catalogue_codex.py — `parse_codex()`'s Full-Contents regex assumes single-line entries; verified currently true, not enforced

```python
# catalogue_codex.py:90
for m in re.finditer(r"^\s{2,}(.+?)\s*\((\d+)\):\s*(.+?)$", body, re.M):
```

No `re.S`/`DOTALL`, so a "Full Contents" line that word-wrapped across two physical lines in the
owner's markdown would silently lose every item after the wrap, and the declared count
(`m.group(2)`) is parsed but never checked against `len(names)` to catch exactly that. I ran this
against the real file (`THE_PRIME_OMNIVERSE_CODEX.md`, 64 sections) and confirmed 0 count/parsed
mismatches today — not a live bug — but nothing in the code would notice if a future edit
introduced one. Cheap fix: assert `len(names) == declared` and route the mismatch through
`silence.note` rather than silently accepting whatever the regex captured.

### 13. catalogue_codex.py — codex-section matching uses unguarded substring containment

```python
# catalogue_codex.py:126-131
for k, t in sec_by_norm.items():
    if n and (n in k or k in n):
        title = t
        break
```

Same idiom (`x in y or y in x` on normalized/stripped strings, no word-boundary check) that
`address.py`'s own docstring (address.py:64-84) documents as having produced real false positives
elsewhere in this codebase ("dc" inside "swor-**d-c**-oast", mis-shelving a D&D sourcebook under DC
Comics). Ran it against the live roll: only 2 zero-entry-count sources currently reach this branch
and both match correctly with no ambiguity. Not a live bug today, but it is the same fragile
pattern the project has already been burned by once, applied here without the hardening address.py
had to add.

### 14. module_index.py — stale hardcoded module count in the header docstring

```python
# module_index.py:2
"""MODULE_INDEX — the map of the 87 modules, generated from their own first lines.
```

`src/` currently holds 95 `.py` files; the generated output itself is correct (it prints
`len(mods)` dynamically, module_index.py:77), only the prose header inside the docstring is
stale. Cosmetic.

---

## CLEAN

- **address.py** — no correctness, concurrency, or Hard Rule 0 issues found. `spine_code_for`'s
  four-tier matching (exact key, normalized-equality, word-padded substring, token-overlap) is
  careful and its own history of prior false-positive fixes is documented and still holds up
  against the live data (spot-checked, no regressions found). `tier_for`/`tier_rank`/`promote`
  (the promotion ladder) are correct pure functions, and `promote` genuinely never demotes as
  documented. The only note is a benign unlocked lazy-singleton read in `_load_spine_codes()`
  (harmless, idempotent) — not worth listing as a finding on its own.
- **tempus.py** — the physics/derivation logic (`rung_description_length`, `band_resolution`,
  `prescience_horizon_bits`, `retrocausality_beta`) is internally consistent and matches
  `verify_math.py`'s own live checks; the `/10 per decimal point` language in `band_resolution`'s
  docstring initially looked like a code/comment mismatch but is correctly the *caller's*
  responsibility (confirmed both `rigor.py:128` and `verify_math.py:382-384` apply the `/10.0`
  externally, exactly as documented). Only the minor API-shape note above (#11).
- **custodes.py** — aside from finding #3 (the false "derived" claim) and #10 (dead `dispersive`
  field), the college mechanism itself is sound: `convene()`'s interval genuinely covers every
  signed reading by construction (custodes.py:320, `covers_every_reading` check at 344 is honestly
  labeled as a tautology in its own comment rather than a real verification — that self-awareness
  is a good sign, not a bug), `prior_share`/`attestation_floor_share` split is guarded against
  division by zero (custodes.py:315-316), and Threnody's veto threshold is derived from Theorem 1
  rather than a fresh number, as claimed.

---

## Summary table

| module | HIGH | MEDIUM | LOW |
|---|---|---|---|
| read.py | 2 | 1 | 3 |
| custodes.py | 1 | 0 | 1 |
| address.py | 0 | 0 | 0 |
| tempus.py | 0 | 0 | 1 |
| catalogue_codex.py | 1 | 0 | 2 |
| module_index.py | 0 | 1 | 1 |
