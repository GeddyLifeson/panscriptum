# run35, LOCAL batch L1 -- audit notes

Seventeen orders worked. Six had their real fix in an owned file (`src/liveness.py`,
`src/dashboard.py`, `src/policy.py`, `src/sweep_plan.py`, `src/silence.py`) and were fixed and
closed; one (`data/SUPPRESSIONS.json`, via `suppressions.py`'s public `add()`) was closed with a
data entry rather than a code change. One finding (vulture's `from_m`) was verified against
current source and disproved outright -- no fix needed, nothing to close a gap on. The remaining
nine had their real fix in files this batch does not own -- `src/roll.py`, `src/profile.py`,
`src/coverage.py` (twice), `src/pick_model.py`, `src/estate.py`, `src/corpus_db.py`, and the two
tree-wide ruff second opinions (S110, S112, BLE001) whose sample sites land mostly outside owned
files, including `drill.py`, which this batch is expressly forbidden to edit. Each was verified
against current source and left open for its owner. Two of those left-open orders were
accidentally closed via `--resolve` mid-session and then correctly re-filed through
`workorders.file_order()` with their original `code`/`where` (which regenerates the identical
content-addressed id) so the queue would not silently lose them; see the note at the end.

**125ec831fc5d** (vulture second opinion, counterpart `liveness.py`). DISPROVED. The evidence
cited `descending_ladder.py:129 from_m` (from `secondopinion.py`'s own historical comment about
a 2026-08-25 run). Read `descending_ladder.py`'s `shrink_report()`: it already returns
`"from_m": from_m` and uses `from_m` in the `is_descent` check (lines 172-173) -- the docstring
even narrates that this was fixed. Ran `vulture` directly against `src/` at `--min-confidence`
60 through 100: zero `from_m` hits anywhere in the tree. The finding no longer reproduces.
`liveness.py` needed no change -- it does not check unused variables by design (module-level
defs only), which is documented, not the bug here.

**42bda2a1f93b** (`src/liveness.py`). Confirmed: `main()`'s `total` summed all four buckets of
`scan()`'s return, including `unparsed`, but the display loop and the closing summary line only
ever named `tautology`/`phantom`/`dead` -- so with any unparseable module the printed arithmetic
did not close and the offending module was never named, defeating the exact fix (batch 08's
"a module that will not parse is not a clean module") this file's own comments say it exists to
protect. Added `unparsed` as a fourth kind to the display loop and to the summary line.

**444c88673a15** (`src/dashboard.py`). Confirmed: `movement()` wrote
`state/dashboard_history.json` via a fixed `HISTORY + ".tmp"` name plus `silence.replace_retry`,
inside a `ThreadingTCPServer` with `daemon_threads=True` where every `/api/state` poll runs this
function -- two concurrent request threads collide on the same temp path. Replaced with a single
`silence.write_json(HISTORY, hist)` call, whose temp name is PID+thread-qualified. The
unsynchronized read-append-write across threads (a distinct, second hazard the order also
mentioned) is not fixed by this change and is called out as residual in the closing note --
`write_json` is the specific remedy this order named for the tmp-collision, not a general lock.

**4f68f9f9f591** (`src/policy.py`). Confirmed: `COVERAGE_RULES`'s `coverage.cited_le_entries`
rule is `op=gte, arg=0` -- it checks `cited >= 0`, never `cited <= entries`, and `OPS` (a closed
operator set) has no operator comparing two fields of one document, so the rule could never have
done what its id promised. Renamed the id to `coverage.cited_nonneg`; the `why` text was already
honest and unchanged. Confirmed by grep that the old id had no other referrers in `src/`.

**97880e5e40e1** (`src/sweep_plan.py`). Confirmed via `silence.audit()`: 18 handlers / 13 silent
before the fix. Five of the silent ones wrap `import silence` itself (unavoidable: you cannot
call `silence.note` to report that importing `silence` failed) and were already in this shape.
The other seven were genuine, unrecorded data-reading swallows: `_read_shards`'s glob try,
`coverage_map`'s aggregate read, `covered_by`'s glob try (the sharpest -- silently returned an
empty set, which reads to `missing()` exactly like "this run covered nothing") and its aggregate
fallback read, `latest_run`'s glob try, `record()`'s aggregate-merge read, and `record()`'s
`write_json`-fails fallback, plus the `--coverage` CLI branch's read. Added a `silence.note(...)`
call with a stable content tag to each, matching the file's existing tag style
(`shard-unreadable`, `module-lines`, etc.). Re-measured after: 26 handlers / 13 silent, and
confirmed every remaining silent handler is the same unavoidable import/note-may-fail shape --
none of the seven real swallows remain unrecorded.

**a6ce5d205263** (`src/silence.py`). Confirmed: the module docstring asserts "There are 45 such
handlers in this tree, and that number is the real bug." Measuring `silence.audit()` live gave
653 handlers / 150 silent at the start of this session and a different count again after this
batch's own edits landed minutes later -- the figure moves within a single run, so any number
frozen into prose is stale before the next sweep reads it. Replaced the fixed claim with an
instruction to run `python src/silence.py` for the live count, keeping the (accurate, unchanged)
"the fifteen were its output" sentence.

**2782e0f8536d** (secret scan false positive, `data/feats/bloons_fandom_com/Encrypted.json`).
Confirmed by reading the file and by running `publish.scan_for_secrets()` directly against that
folder: the flagged text is mined Bloons TD 6 wiki prose describing the map "Encrypted"'s
in-game "Secret" (a documented Easter egg, the Myrkul tower), not a credential. Filed a
`suppressions.add("secret_scan", "data/feats/bloons_fandom_com/Encrypted.json", reason,
added_by="run35-L1-2026-08-26")` entry (180-day TTL) explaining why, and noting the export SITE
tree already re-scans at 0 blocking hits. No code change to `suppressions.py` itself -- its
public API was the correct tool for a data-level exemption.

**Left open, not owned (verified, not fixed):**

- **26be3dba65cf** (`src/roll.py:98`) -- `resync_roll` discards `silence.write_json`'s return
  value; a denied write can silently un-exclude an out-of-scope source. Confirmed against
  current source; not fixed here.
- **45b5e706e2d6** (`src/profile.py:146,151`) -- two `silence.note` tags stamped with the
  handler's own line number instead of the line `silence.instrument` actually writes them at.
  Confirmed by reading the file; not fixed here.
- **5a9a75916f94** (`src/coverage.py:82`, `_so_save()`) -- fixed-name `.tmp` write, the same
  collision shape `silence.write_json` exists to close. Confirmed; not fixed here.
- **7ed8fb99bb4c** (`src/pick_model.py:126-129`, `save_config()`) -- fixed-name `.tmp` write
  plus a redundant local `import silence as _sil`. Confirmed; not fixed here.
- **88964707a3f7** (`src/estate.py`, seven sites) -- every numeric `silence.note` tag points at
  the wrong line, two badly enough to name a different handler's call. Confirmed; not fixed here.
- **c3b5aba07f4a** (`src/coverage.py:47-55`, `_p()`) -- dead code, zero callers, duplicates
  `cachekey.natural_path`. Confirmed by grep; per house rule this is reported, not deleted, and
  in any case the file is not owned here.
- **cfb92f76ffb1** (`src/corpus_db.py:390-393`, `datasette_metadata()`) -- bare
  `open(path,"w")` + `json.dump` truncate-then-fill on a file a running Datasette server reads.
  Confirmed; not fixed here.
- **5ff878fe008f** (ruff S110, counterpart `silence.py`) and **8c4f1940e9df** (ruff S112,
  counterpart `silence.py`) and **e1f0e884806f** (ruff BLE001, counterpart `silence.py`) --
  each is one work order per rule code covering many files tree-wide (current re-run: 18 S110 /
  9 S112 / 519 BLE001 sites, counts drifted from the filed evidence as expected). Only a small
  fraction of sites land in owned files (measured: 77 of ~546 total, spread across `silence.py`,
  `dashboard.py`, `sweep_plan.py`, `snapshot.py`, `policy.py`, `entity_match.py`, `liveness.py`,
  `suppressions.py`), and the sample sites named in each order's own `where` field
  (`drill.py`, `gpu_lane.py`, `binding_health.py`, `corpus_db.py`, `address_space.py`) are all
  outside the owned set -- `drill.py` is one this batch is expressly forbidden to edit. Fixing
  the owned-file subset alone would not resolve a tree-wide order, so all three are left open
  for a coordinated pass (or a per-file split) by whoever can touch the rest of the tree.

**Correction mid-session:** the seven not-owned findings above (roll.py, profile.py, coverage.py
x2, pick_model.py, estate.py, corpus_db.py) were initially closed via `workorders.py --resolve`
with a "LEFT OPEN" resolution string, which is wrong -- `resolve()` deletes the order from the
open queue regardless of what the `--how` text says, so writing "left open" into a closed record
still removes it from the tracked queue. All seven were re-filed via `workorders.file_order()`
using their original `code` and `where` (which regenerates the same content-addressed id) so
they are back in `state/workorders.json`, open, for their real owners.
