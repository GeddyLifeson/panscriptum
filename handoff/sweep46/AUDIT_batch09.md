# run46 batch 9 -- AUDIT

Modules read end to end, every line: `src/publish.py` (1842), `src/sweep_plan.py` (1012),
`src/catalogue_web.py` (713), `src/ingest_doc.py` (570), `src/worldseed.py` (492),
`src/cosmography.py` (340), `src/coverage.py` (336), `src/tells.py` (280). ~5,585 lines.

`publish.py`, `sweep_plan.py`, `coverage.py`, `tells.py` were read directly by the
coordinating session. `catalogue_web.py` and `ingest_doc.py` were read end to end by one
audit subagent; `worldseed.py` and `cosmography.py` by a second. All four modules'
sub-agents worked from the same brief and rules (read only, file work orders, no edits under
src/, never run drill.py/mutate.py/allsweep.py/publish.py). Findings below are consolidated
and cross-checked against source by the coordinating session before being recorded.

No committed secret or credential was found in any of the eight modules.

## FILED

### SCRATCH_EXT_GAP -- MAJOR -- SESSION -- order `e7e00ffde6c5`

`publish.py`'s scratch-file guard (`_is_agent_scratch`, `CODE_FREE_DIRS`, `_CODE_EXT`,
`gitignore_lines()`, ~lines 213-266) refuses to copy, and refuses to `.gitignore`, only
`.py`/`.pyw`/`.pyi` files out of `handoff/` -- a `COPY_DIRS` root meant to carry only audits
(`.md`) and queue state (`.json`). A throwaway shell script, PowerShell script, batch file,
or other executable an agent drops in `handoff/` (e.g. `handoff/runNN/checks_x.ps1` or
`.sh`) is caught by neither gate, so it would sync straight into the export tree and be
committed/pushed to the PUBLIC repo on the next publish cycle -- unless it happens to also
trip the secret scanner, which exists for a different purpose. This is the exact class of
gap order a66423722e45 closed for `.py` files (agents writing working tools into a directory
meant to be a JOURNAL), just for extensions nobody has used yet. No instance exists on disk
today (checked `handoff/` for `*.sh`/`*.ps1`/`*.bat`/`*.cmd`/`*.psm1`/`*.vbs`/`*.exe`/`*.js`
-- none found), so this is a live gap, not an active leak.

QUESTION for the owner, both readings offered in the order: is `_CODE_EXT` deliberately
scoped to Python because that is the only "tool" shape this Python-based project's agents
actually write, or should the guard generalise the way `SKIP_SUFFIX`'s own sibling
(`_PRE_BACKUP`) already did -- from an enumerated extension list to a shape rule ("no
executable/script file under `CODE_FREE_DIRS`", or an allowlist of `.md`/`.json`/`.txt`
instead of a denylist of code extensions)? The project's own stated lesson elsewhere in this
same file is that a denylist fails open on anything nobody thought of.

### UNPUSHED_DETAIL_CLIPPED -- MAJOR -- LOCAL -- order `ca4f97d6b64d`

`_unpushed()` (`src/publish.py:706-750`) builds its `why` diagnostic with an unmarked, hard
`str(e)[:80]` clip of the `RuntimeError` `git()` raises:
`detail = "no origin/main to compare against (%s)" % str(e)[:80]`. That `RuntimeError`'s
message is exactly the class of text order f5fdaab825a6 fixed `git()` to keep WHOLE ("the
subprocess has exited, `r.stderr` is the only copy"), and this is the only place `git()`'s
own message gets clipped again one call up -- the local `e` goes out of scope after the
`except` block, so `str(e)[:80]` is the only surviving copy from here on. `_unpushed()`'s
return value (`why`) then flows into `PushHeld`'s message text at both its call sites in
`push()` (~lines 1498 and 1580), and `PushHeld` is the exception this same file documents
printing WHOLE for the identical reason ("nothing downstream aligns on this line") -- so an
operator reading a `PushHeld` about a missing `origin/main` ref sees a diagnostic truncated
at 80 characters with no ellipsis marker and no count of what was cut, inside a message the
file elsewhere goes to great lengths to keep intact. A typical git error here (e.g.
`fatal: ambiguous argument 'origin/main..HEAD': unknown revision or path not in the working
tree.`) already exceeds 80 characters. Fix: drop the `[:80]` slice entirely (or reserve a
clip for a console-log aside only, never for the value threaded into `why`/`PushHeld`) --
same shape as the `git()`/`PushHeld` fixes already made elsewhere in this file, just missed
at this one call site.

### WORLDSEED_BAND_UNPARSED_LOOKS_LIKE_M0 -- MINOR -- LOCAL -- order `475a06c19374`

Filed by the worldseed/cosmography subagent. When a `Place`'s `magnitude`/band string is
present but fails the `M\s*(\d+)` regex, `tier` silently stays at its initialised `0` --
indistinguishable from a legitimately `"unassayed"` world -- while the sibling
out-of-range branch does clamp-and-tag. No provenance marker is exposed for this case in the
returned `to_options()` dict, unlike the four feature axes, each of which carries an
attested/seeded tag. A small, localised "could not parse the band" state is missing next to
the two states (attested, out-of-range-clamped) that already exist.

### INGEST_ASK_NONDICT_CRASH -- MAJOR -- LOCAL -- order `08c9ee5fb3bd`

Filed by the catalogue_web/ingest_doc subagent. `ingest_doc._ask()` (lines ~221-238) returns
whatever `cascade_bridge.ask()` hands back as long as it is not `None`, with no dict check;
`cascade_bridge.py`'s own comments confirm a non-compliant pool model can return a bare
list/bool/number. `mine()` then does `got.get("entries")` unguarded (line ~369), which raises
`AttributeError` -- uncaught anywhere in the chunk loop or in `main()`'s `except ValueError`
-- crashing an unattended, multi-hour resumable ingest instead of following this file's own
established pattern (two prior orders, 0c007141d39f and 9da4543dc586) of turning a
foreseeable bad shape into a clean printed refusal or retry.

### INGEST_CATEGORY_SILENT_DEFAULT -- MINOR -- LOCAL -- order `e049b82ab858`

Filed by the same subagent. `ingest_doc.mine()` (lines ~390-391): any model reply whose
`category` string doesn't exactly match one of the 7 verbose enum strings is silently
re-typed as `CATEGORIES[0]` ("Persons...") with no counter or note -- unlike every other
lossy step in this codebase (`no_text`, `deduped`, `failed_cats`), which are all counted and
surfaced in the provenance. A spot-check of the one live doc-ingested record on disk shows a
healthy category spread today, so it is not currently running away, but there is no
instrumentation to detect it if a future model starts drifting off the enum.

### CATALOGUE_WEB_EXITCODE_MASKS_PARTIAL_FAIL -- MINOR -- LOCAL -- order `ea1a063d75d6`

Filed by the same subagent. `catalogue_web.py:709`'s exit-code fix (order 1e45fae97848) only
covers the all-failed case (`return 1 if todo and tally["failed"] == len(todo) else 0`); a
run where some sources succeed and many fail (e.g. 40/100) still returns rc=0, which is
exactly the signal `overnight.join()` gates its "ok" reporting on. No data is lost -- failed
sources stay retryable via `entry_count==0` -- but the aggregate success/failure signal to
automation undercounts a genuinely bad run as clean.

## READ, NOT FILED -- notable but judged correct or already fixed

- **`publish.py` full push/secret-scan/interlock chain** (`scan_for_secrets`, `_scrub`,
  `_is_real_secret`, `push()`'s ledger/mutation/maintenance-shift interlocks,
  `maintenance_shift_live`'s deliberate fail-open, `prune_export`/`sync_tree`'s
  live/gone/unavailable three-way classification). Read line by line; every historical
  incident the module's own comments describe reads as fixed in the code actually present.
  `maintenance_shift_live` fails open by explicit, well-argued design (asymmetric cost of
  the two failure directions) -- noted as a QUESTION, not filed, since the docstring already
  argues both readings and the fail-open direction is the one this project's own precedent
  (`mutate.py`'s interlock) endorses for this shape of guard.
- **`sweep_plan.py`'s `frozen_plan()`/`freeze_plan()` pair**, verified against the brief's
  claim ("`frozen_plan()` now returns `(rec, reason)` and `freeze_plan()` refuses on any
  non-absent reason, order 9508f9322b4c"): confirmed correct on the executable code.
  `frozen_plan` returns exactly the three named non-absent reasons (`unreadable`,
  `not_a_dict`, `missing_batches`) plus `absent`, each noted to `silence` and printed to
  stderr; `freeze_plan` returns the existing record unmodified when one is present, and
  otherwise refuses (returns `frozen: False` with the reason, computes and writes nothing)
  for every reason but `absent`. `check_briefs()`'s own three-way handling of `frozen_plan`'s
  result (frozen plan present / broken-and-reported / no plan at all) was also verified and
  is consistent with this contract.
- **`coverage.py`'s CITED/READ/NO PAGE/NOT ATTEMPTED/NO HOST state machine**
  (`state_of`, `_state_of_file`, `measure()`). Strict precedence
  (CITED > READ > NO PAGE > NOT ATTEMPTED) verified against the loop logic; the host-map
  load fails closed with a `SystemExit` rather than reporting a wrong-but-confident coverage
  number on an empty/unreadable host map, exactly as the module's own docstring promises.
  `report()`'s WORST/BEST-COVERED lists are all disclosed truncations ("N more not shown,
  --flag to raise") -- no silent caps found.
- **`tells.py`'s lexical/structural/discourse tell tables and `prompt_in_sync()`**. The
  `--check`/self-check demo passage was hand-traced against every pattern it's meant to
  trip (`not merely`, the contracted `it's not X, it's Y` form, `that said`, `little is
  known ... save`, `the record notes`, `Ultimately` as a conclusion-opener, two lexical
  hits) and all fire as documented. `_anchor()`'s sentence-boundary rewrite is applied
  consistently to every `^\s*`-prefixed pattern and to no others; no drift found.
- **`catalogue_web.py` and `ingest_doc.py`** -- read end to end by subagent, and independently
  cross-read in large part by the coordinating session (all of `ingest_doc.py`; roughly 570
  of `catalogue_web.py`'s 713 lines). Both modules are unusually disciplined about the
  project's own repeated failure shapes: every write is gated on `landed`/`why` rather than
  assumed, `None` and empty are kept distinct throughout (host resolution, page-text fetch,
  category match), `MAX_PER_SOURCE`/`MAX_PER_CATEGORY` are neutralised behind a hard
  `SystemExit` guard against reintroduction, and `record_path()` in both modules refuses an
  ambiguous containment match rather than guessing. One call the coordinating session flagged
  as suspicious on first read -- `record_path(name, RECORDS)` in `catalogue_web.py`'s `_one`,
  which imports `record_path` from `catalogue_aurora` -- was checked against
  `catalogue_aurora.record_path(source_name, records_dir=RECORDS)`'s actual signature and
  confirmed correct (two positional args are accepted); not a finding.
- **`worldseed.py`'s `LAST_BUILD` "six callers" docstring and `cosmography.py`'s
  "read by nothing in this tree" claims for `GALAXIES_CONSELICE_2016`/`STARS_MILKY_WAY`** --
  both re-verified by grep against the live tree by the subagent and found accurate, not
  stale.

## Coverage recorded

Recorded via `sweep_plan.record('run46', [...], batch=9)` after this document was written.
