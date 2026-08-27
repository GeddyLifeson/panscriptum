# sweep35 batch 11 — audit

Modules read in full: src/overnight.py, src/binding_health.py, src/handbuilt.py,
src/endpoint.py, src/runguard.py, src/anchors.py, src/suppressions.py, src/cachekey.py
(3,575 lines).

Audit only — no src/ edits made. 6 findings filed.

## Filed

1. **98831f6e6f6d** (MAJOR) — `binding_health.py:93` and `suppressions.py:81` still write
   through a FIXED `path + ".tmp"` name, the identical collision `runguard._land` was replaced
   for today (`_land_claim`, pid+thread in tmp name). Two concurrent writers (e.g. a `--host`
   probe racing a scheduled whole-estate `--run`) can collide on the shared tmp file.

2. **23d84e6f8e81** (MAJOR) — `binding_health.run()`'s new merge (574-598), landed this shift to
   stop a partial `--host` run shrinking the whole-estate report, is a read-modify-write of
   `BINDING_HEALTH.json` with no compare-and-swap. A concurrent whole-estate `--run` finishing
   between this pass's read and write gets clobbered by the stale snapshot — the exact
   partial-over-complete shape the merge exists to prevent, reintroduced through the fix itself.
   `drill._partial_canary_merges` only tests the merge single-threaded.

3. **30854f11f322** (MAJOR) — `binding_verdict()`'s rapidfuzz `token_set_ratio` scores 100
   whenever one side's word-set is a subset of the other's, regardless of unrelated content —
   verified: `fuzz.token_set_ratio("prime","prime world equipment") == 100.0`. A host with a
   short/generic sitename that happens to be a token-subset of its bound source's name would be
   wrongly CONFIRMED, and `workorders.py:523-535` files that as unfixable ("NOTHING IS BROKEN").
   The drill's margin net only checks the 5 hosts on file, none of which is a subset pair.

4. **84b584da5935** (MINOR) — `runguard._land` (72-85) is dead code; `claim`/`beat`/`release`
   all moved onto `_land_claim` this shift and nothing calls the old `_land` any more.

5. **596551e4e37c** (MAJOR) — `overnight.py`'s keeper thread and the main cycle's per-cycle
   STANDING starts both do running()-then-start() with no lock between them; `_PROCS_LOCK` only
   guards the process-table cache, not the decision. A genuinely-down STANDING job can be
   double-started if a keeper tick lands beside a cycle top. Distinct from existing order
   5d14e90b5043 (pipeline redundancy/ordering), which doesn't address this race.

6. **6dc3b3682fc8** (MINOR) — `endpoint.register()` is an unprotected read-modify-write of
   `SOURCE_PAGES.json`; concurrent registrations for different sources can lose an update
   (last writer wins), even though the write itself is now atomic.

## Read and cleared (no new finding)

- `anchors.py`, `handbuilt.py`, `cachekey.py` — no new concurrency/heuristic/cap defects found
  beyond what's already documented/fixed in-file. `cachekey.write_path()` has a narrow TOCTOU
  but the module's own measured collision rate (5 slots / 96,666 entities) and the fact that a
  collision is self-correcting on next read make it low value against this shift's higher-value
  finds.
- `runguard.py`'s CAS design (claim/beat/release via `_land_claim` + `silence.replace_if_unchanged`)
  checked against `silence.py`'s digest/replace-if-unchanged implementation and against
  `verify_math.py`'s existing race test (~line 6850) — correct as built, aside from the dead
  `_land` above.
