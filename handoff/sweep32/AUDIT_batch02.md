# AUDIT — BATCH 02, run32

Modules read in full, every line:

| module | lines |
|---|---|
| src/pipeline.py | 2015 |
| src/sevenfold.py | 274 |
| src/runguard.py | 219 |
| src/halo.py | 178 |
| src/module_index.py | 83 |

---

## KNOWN LEAD 1 — `pipeline.py` `synthesis_blocks`, `rest[:14]`

`src/pipeline.py:713-742` (`synthesis_blocks`), fallback line **741**:

```python
return ([with_feats[i:i + 14] for i in range(0, len(with_feats), 14)] or [rest[:14]],
        feats_for)
```

**Verdict: a Hard Rule 0 cap, not a fully defensible decision — MAJOR, VERIFIED.**

- `with_feats` (entries that have a mined feat) is chunked into **every** block of 14 — no
  entry with a feat is ever dropped. That branch is the actual m13 fix described in the
  surrounding comment ("EVERY feat-bearing entry is nominated... no feat-bearing entry is
  ever excluded from nomination", `pipeline.py:800-806`).
- The fallback only fires when a source has **zero** feat-bearing entries at all. In that
  case `rest` (every remaining entry, ranked by description length) is truncated to the top
  14 and the rest are silently never shown to the model for this source's ceiling
  nomination. That is ranking-then-truncating a candidate list — the exact anti-pattern Rule
  0 names.
- The in-code justification ("a description is a wiki lead paragraph — biography, not a
  deed — sampling more lead paragraphs buys nothing") is a generalization, not a guarantee.
  `feats_for` is populated from the automated feat-miner cache (`_mined_feats`, reading
  `data/readfeats`/`data/feats`); an entry the miner missed can still have a genuine
  demonstrated feat sitting in its raw `description` text (the same regex/model gates that
  built the mined-feats cache are not applied to descriptions here). Entries ranked 15th and
  beyond are excluded from consideration on an assumption, not a per-entry check — the same
  class of reasoning the docstring itself says was already proven wrong once for this exact
  function (the m13 fix, three paragraphs up).
- Net effect: for any source whose feat miner drew a total blank, only the top-14
  longest-description entries can ever nominate the source's ceiling; anything further down
  the list can never be the nominated ceiling entity, however strong its actual (unmined)
  evidence, for as long as the source stays feat-blank.

Recommend: apply the same "chunk everything, keep the best across chunks" treatment used for
`with_feats` to the `rest` fallback, matching the fix already applied to its sibling branch.

---

## KNOWN LEAD 2 — `pipeline.py` `phase_chain`, `len(rows) < 10`

`src/pipeline.py:1437-1445`:

```python
rows = CH.harvest()
log(f"phase 4 chain: {len(rows):,} sentences read like a contest outcome")
if len(rows) < 10:
    log("  too few contests on record to fit anything; leaving the graph empty")
    st["done"].setdefault("chain", []).append("all")
    st["units_done"] += 1
    save_state(st)
    return
```

**Verdict: half-confirmed, half-refuted. VERIFIED on both points below.**

1. **"Discards the harvested rows" — REFUTED as literal data loss.** `CH.harvest()`
   (`src/chain.py:31` on) is an **incremental, disk-cached** harvest keyed by file mtime
   (`state/chain_harvest_idx.json`): every file that yields a contest-outcome sentence has
   its rows persisted in that index independent of `phase_chain`. When `len(rows) < 10`,
   `phase_chain` simply does not call `CH.extract()`/`CH.fit()` this cycle — it does not
   delete or forget anything. The next call to `harvest()` (next run, or a growing corpus)
   returns the same rows again, plus any new ones. So no row is destroyed; the fit is merely
   deferred, honestly, with a stated reason.
2. **"Marks itself permanently done" — REFUTED for `pipeline.py`'s own dispatcher, but the
   state value is dead/misleading — MINOR.** `main()` (`pipeline.py:1953-1954`) calls
   `IMPLEMENTED.get(ph)` and invokes `fn(c, st)` unconditionally for every phase in the
   requested range on every invocation; it never consults `st["done"]["chain"]` to decide
   whether to skip phase 4. So appending `"all"` to `done["chain"]` does **not** block a
   future run — the next full run (or `--phase 4`) re-harvests and re-checks from scratch.
   Confirmed by grep: `"chain"` appears in `pipeline.py` only at the two `append("all")` call
   sites (lines 1441, 1461) and never on a read/lookup path.
   - That said, this makes `done["chain"]` a write-only, ever-growing list of duplicate
     `"all"` entries that nothing in this file ever consults — dead bookkeeping that looks
     load-bearing (mirroring every other phase's `done_keys` idiom) but isn't. Anything
     *outside* `pipeline.py` (e.g. a maintenance dashboard or `foreman.py`, not in this
     batch) that trusts `state/PIPELINE_STATE.json["done"]["chain"]` as "phase 4 finished, no
     work pending" would be misled by a cycle that found `<10` rows and quit early — the
     value says "done" while the graph is still empty. I could not verify from this batch's
     modules whether any consumer actually reads it that way; flagged as SUSPECTED for that
     downstream part only.

---

## OTHER FINDINGS — `pipeline.py`

### BLOCKING — `land_json` return value discarded at every one of its 12 call sites

`src/pipeline.py:486-503` defines `land_json`, which wraps `_landed` (itself wrapping
`silence.replace_retry`) specifically so that **a phase artifact write that did not land is
visible to its caller** — the docstring is explicit: *"Same discipline as the record writers;
`_landed` already explains why the verdict is returned rather than swallowed."* And
`_landed`'s own docstring (`pipeline.py:149-164`) states the whole reason this matters: *"both
record writers are called by phases that then mark their unit DONE, which means there is no
next round. A denied rename plus a recorded done-key is the exact silent permanent loss..."*

That discipline is honored for `write_record`/`write_record_catalogue` (checked at
`pipeline.py:842` and `:1277`), but **every** call to `land_json` ignores the return value:

```
pipeline.py:1489  land_json(.../TIERS.json, charted)
pipeline.py:1516  land_json(.../GROUNDINGS.json, grounds)
pipeline.py:1521  land_json(.../CENSUS.json, cen)
pipeline.py:1536  land_json(.../SHELFMARKS.json, marks)
pipeline.py:1647  land_json(.../CHRONICLE.json, {...})
pipeline.py:1759  land_json(ranks_p, ranks)
pipeline.py:1769  land_json(.../SHELVES.json, {...})
pipeline.py:1840  land_json(out, jobs)                      # output/index/manifest.json
pipeline.py:1878  land_json(.../CONTINUITY_GROUPS.json, ...)
pipeline.py:1880  land_json(.../RESOLVED_ENTITIES.json, resolved)
pipeline.py:1881  land_json(.../RESONANCE_GRAPH.json, ...)
pipeline.py:1893  land_json(.../ONOMASTICON.json, named)
```

In every case (`phase_cosmology`, `phase_history`, `phase_shelve`, `phase_write`,
`phase_weave`) the code proceeds straight to `st["done"].setdefault(<phase>, []).append("all")`
and `save_state(st)` regardless of whether the write landed. If
`silence.replace_retry` hits persistent `PermissionError` (its own documented failure mode —
"a brief backoff outwaits any honest reader; persistent denial is recorded, never raised"),
the phase artifact silently keeps its previous (stale or nonexistent) content while the phase
is recorded as complete for this cycle. This is precisely the "swallowed failure via discarded
return value" class the task brief calls out by name, and it directly contradicts `_landed`'s
own docstring claim that callers gate their done-keys on the verdict — that claim is true only
for the two record writers, not for `land_json`, despite `land_json`'s docstring explicitly
invoking the same discipline. Comment-contradicts-code, and a real swallowed failure, at every
one of 12 sites across 5 phases.

Recommend: gate each `st["done"]... append("all")` on the corresponding `land_json` call(s)
succeeding, same pattern already used at `pipeline.py:842` and `:1277`.

### MAJOR — `save_state` never checks or exposes `silence.replace_retry`'s verdict

`src/pipeline.py:184-189`:

```python
def save_state(st):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=2, ensure_ascii=False)
    silence.replace_retry(tmp, STATE)  # atomic; retried, readers poll this file
```

`save_state` is called ~20 times through the file, after essentially every `done_keys.append`,
every `failed[...] = ...`, and every `units_done += 1`. Its return value (there isn't one —
the function doesn't even `return` the verdict) means no caller anywhere in the file can know
whether a given state snapshot actually reached disk. Concretely lower severity than the
`land_json` finding above because: the in-memory `st` dict keeps accumulating correctly for
the life of the process, so a single dropped `save_state` write is self-healing on the *next*
successful `save_state` call later in the same run; the failure only bites if the process dies
or is killed between a dropped write and the next successful one, in which case the run
resumes from an older-than-expected `PIPELINE_STATE.json` and simply redoes some already-done
units (safe direction, matching the project's own stated philosophy elsewhere in this file).
Still flagged because it is the same discarded-boolean pattern the task brief specifically asks
to hunt for, and `save_state` doesn't even follow its own module's `_landed` convention of
surfacing the verdict for a caller who might want it.

### NOTE — Hard Rule 0 tautology self-flagged, verified correct (sevenfold.py, see below) applies analogously here: none found in pipeline.py beyond the two known leads.

---

## OTHER FINDINGS — `sevenfold.py`

### MAJOR (SUSPECTED) — `build()` silently drops a world's shelfmark when its source isn't shelved

`src/sevenfold.py:199-208` (`build`):

```python
for src, ws in by_source.items():
    base = coords.get(src)
    if base is None:
        continue
    ...
```

If a world's designation prefix (`world["designation"].split("::")[0]`) does not match any
name in `coords` (the top-level source shelving, built from `tiers._graph()`'s `srcs`), that
source's entire batch of worlds is skipped with no `silence.note`, no log line, and no count
of how many worlds were dropped. `main()`'s printed summary (`len(worlds)`) would simply be
smaller with no indication why. I did not read `tiers.py`/`worldseed.py` (outside this batch)
to confirm whether such a mismatch can occur in practice (e.g. a source present in
`worldseed.build_all()`'s designations but absent from `tiers._graph()`'s roster) — flagged
SUSPECTED, not verified, but the silent `continue` with zero diagnostics is itself worth
fixing regardless of how often it fires, since it is indistinguishable from "no worlds lost."

### NOTE — self-documented tautological check, verified correct

`src/sevenfold.py:241-245`, inside `main()`'s per-tier balance table:

```python
# m30, same shape as custodes' covers_every_reading: `seams()` already clamps every child
# count to SPAN, so "OVER SPAN" cannot print for any input. This displays a GUARANTEE, not
# a discovery. ...
ok = "OK" if hi <= SPAN else "OVER SPAN"
```

I traced `seams()` (`sevenfold.py:108-129`) and confirmed the comment is accurate: `k` is
clamped to `min(span, len(block))`, cut indices are unique members of `range(len(block)-1)`,
so `split()` always produces exactly `k` non-empty children. `hi <= SPAN` cannot fail for any
input. This is exactly the "check that cannot fail" shape the lens asks to hunt for, but it is
already self-flagged in-source as intentional display rather than a live check — recording as
NOTE, not a fresh finding.

### MINOR — display-only truncations, correctly exempt from Hard Rule 0

`sevenfold.py:257,258,261,262` (`sorted(coords)[:8]`, `sorted(worlds)[:8]` in `main()`'s
"sample shelfmarks" printout) are pure CLI-summary display truncations; the actual `--write`
path (`sevenfold.py:264-269`) serializes the full `coords`/`worlds` dicts, untruncated. Not a
Rule 0 violation.

---

## OTHER FINDINGS — `runguard.py`

### MINOR (SUSPECTED) — `claim()` has a TOCTOU race between two concurrent claimants

`src/runguard.py:98-121` (`claim`): reads `prior` via `read(path)`, decides `holder_is_live`,
then later writes a fresh record via `_land`. There is no file lock or compare-and-swap
between the read and the write — `_land`/`silence.replace_retry` is a plain
open-write-rename with a `PermissionError` retry, not an atomic claim primitive. Two processes
racing `claim()` at nearly the same instant could both observe "no live predecessor" and both
write their own record; the second `_land` wins and the first caller's `claim()` still returns
`(True, "claimed")` even though it no longer holds the file the way it believes. This is a
narrower window than the m27 bug this module was written to fix (which was about *refreshing*
someone else's record), and the module's own framing elsewhere (`stamp_record`/
`verify_record_provenance` in `pipeline.py`) treats this style of detector as "a DETECTOR,
deliberately, not a lock" — so this may be an accepted, documented-elsewhere risk rather than
an oversight. Flagged SUSPECTED/MINOR since I could not find an explicit acknowledgment of
this specific claim-time race in `runguard.py` itself (only the refresh-time race is discussed
in its module docstring).

### NOTE — `beat()`/`release()`/`read()` are otherwise sound

Ownership checks (`owner != agent`), the `done` guard in `beat()`, and the absent/corrupt
handling in `read()` are all correctly reasoned and match their docstrings. `_land` correctly
propagates `silence.replace_retry`'s verdict (unlike `pipeline.save_state`) — this module is a
positive example of the write-verdict discipline the task brief asks to hunt for violations of.

---

## OTHER FINDINGS — `halo.py`, `module_index.py`

No correctness, swallowed-failure, Hard Rule 0, two-writer-contract, concurrency, or
tautological-check defects found in either module.

- `halo.py` is a static roster + `assay.A.assay()` computation, written via
  `silence.write_json` (two-writer-contract compliant; not a record file, no contract
  violation). The `[:54]` truncation at `halo.py:169` is CLI `--full` display formatting only
  (the underlying `cited` text is written whole to `HALO_ASSAYS.json`) — correctly exempt from
  Hard Rule 0.
- `module_index.py`'s `except Exception` in `first_line()` (`module_index.py:46-48`) falls
  back to `"(unparseable)"` and logs via `silence.note` — an acceptable degrade-and-report
  for a docstring-scraping utility, not a swallowed failure of consequence.

---

## Summary of severities

- BLOCKING: 1 (`land_json` return value unchecked at all 12 call sites across 5 phases)
- MAJOR: 2 (`synthesis_blocks` rest[:14] cap; `sevenfold.build()` silent world-drop, SUSPECTED)
- MINOR: 2 (`save_state` unchecked write; `runguard.claim()` TOCTOU race, SUSPECTED)
- NOTE: 3 (`phase_chain` done-key is dead/unread state; `sevenfold` OK/OVER-SPAN tautology,
  self-flagged; `sevenfold` display-only `[:8]` truncations, correctly exempt)
