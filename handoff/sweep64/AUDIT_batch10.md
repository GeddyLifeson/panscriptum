# sweep64 batch10 — audit

Auditor for maintenance run #64, batch 10. Read-only on `src/`, `data/`, `state/`, `output/`
throughout except this report and the one `sweep_plan.record()` call at the end. Nothing was run:
no `drill.py`, `verify_math.py`, `generate.py`, `pipeline`, `publish` (deliberately STOPPED, per
brief, never run), `catalogue_web`, `mutate`, or any job. Nothing under
`C:\Users\imarl\panscriptum-export` was touched or run. No subagents were spawned.

## Scope (every line read, start to finish, in chunks; no sampling)

- `src/publish.py`        2207 lines
- `src/dashboard.py`      1248 lines
- `src/catalogue_web.py`   821 lines
- `src/build_terminal.py`  668 lines
- `src/worldseed.py`       536 lines
- `src/suppressions.py`    425 lines
- `src/wh40k.py`           351 lines
- `src/propagation.py`     254 lines
- `src/catalog.py`         167 lines

Total 6,677 lines across nine modules, all read in full.

## Prior-audit cross-check

Read `handoff/sweep63/AUDIT_batch02.md`, `04`, `08`, `09`, `10`, `11`, `15` before starting —
these are the sweep63 reports that touch this batch's nine files (grepped by filename across
`handoff/sweep63/`). All nine modules have been through at least one full prior read (several
through two or three, across sweep59/60/61/63) with a strong, consistent pattern: extensive,
order-numbered self-documentation of past defects and their fixes, and very few surviving
findings. Two items from that history are directly relevant here:

1. **`publish.py:git()` (~line 746), SUSPECTED, first filed sweep61/batch10, re-verified
   unchanged in sweep63/batch10.** If `LOCALAPPDATA` is empty in the standing daemon's inherited
   environment, `gh_dir` resolves to the relative path `gh-cli\bin`, `os.path.isdir()` evaluates
   it against the process's actual cwd, returns False, and the PATH-widening `if` body is
   skipped silently. Re-checked against the current source (lines 745-748): unchanged, still
   standing, still unconfirmed without reading the live daemon's environment (out of scope for a
   read-only audit). **Not re-filed as new — carried forward by reference only.**

2. **`dashboard.py`'s `movement()`/`panelMovement()` `reset` flag, VERIFIED by sweep63/batch11 as
   unread by the one JS consumer that existed** (a counter that fell read identically to "first
   reading"). **This is now fixed.** Current code at `dashboard.py:865` —
   `if(m.reset){txt='FELL in '+m.minutes+' min: a restart, or a real regression';cls='down'}`
   — branches on `m.reset` before the `m.delta===null` check, so a reset now renders distinctly
   from a genuine first reading. Confirmed by reading the full `panelMovement()` function
   (`dashboard.py:856-875`) and the Python side that sets `reset` (`dashboard.py:562-568`).
   **Closed, not re-filed.**

No other prior finding in those seven reports applies to code that has changed in a way that
would revive it.

## Two things the brief asked to be mapped precisely

### 1. How `sync_tree`/`prune_export` decide what to delete (`publish.py`)

Traced end to end against the current source (`publish.py:1189-1389` for `sync_tree`,
`:1054-1186` for `prune_export`):

- `wanted` (the set of relative paths that may exist in the export) is built **only by walking
  the live kit** under each `COPY_DIRS` root (`src`, `prompts`, `reference`, `registry_terminal`,
  `handoff`) plus the named `COPY_FILES` root files. A path is added to `wanted` only if it
  exists in the live kit at that exact relative path, is not `_is_skipped` (`.pyc`/`.bak`/
  `.tmp`/`.orig`/`.pre*`), and is not `_is_agent_scratch` (code-shaped files under `handoff/`).
- `prune_export(wanted, held)` then walks the **export copy** (`SITE`) under each non-`held`
  `COPY_DIRS` root and deletes every file whose export-relative path is **not** in `wanted`
  (`publish.py:1124-1139`), then removes any top-level directory under `SITE` that is neither a
  current `COPY_DIRS` root nor `EXPORT_OWN_DIRS` (`("docs",)`) nor dot-prefixed
  (`publish.py:1158-1186`, whole-subtree `shutil.rmtree`). `sync_tree`'s own root-file sweep
  (`publish.py:1352-1371`) does the equivalent for root files against `COPY_FILES`/
  `EXPORT_OWN_FILES` (`()`).
- **Consequence, traced precisely because the brief asked for it**: any file that exists in the
  export repo but does **not** exist at the identical relative path in the live kit — regardless
  of whether it is a brand-new top-level directory, a new file nested inside an existing
  `COPY_DIRS` root (e.g. under `reference/`), or a new root file — is invisible to `wanted` and
  is deleted on the very next `sync_tree()`/`prune_export()` cycle. A file that exists at the
  **same path** in both trees is not deleted, but IS overwritten: the rsync-style short-circuit
  (`publish.py:1248-1253`, mtime+size match) only skips the copy when kit and export already
  agree bit-for-bit-in-metadata, so a PR edit to an existing kit-mirrored file, merged into
  `origin/main` and pulled into `SITE` by `push()`'s own `git fetch`+`git rebase`
  (`publish.py:1814-1816`), is overwritten by the kit's stale copy on the next cycle unless the
  kit is also updated to match.
- Two escape hatches exist and were checked: a `COPY_DIRS` root that fails to enumerate (`_hold`,
  `publish.py:1211-1216`, `_live_root_state` "unavailable") is *held*, not pruned, for that
  cycle only — it does not protect owner-added content, only content the live read genuinely
  could not see. Nothing else in `sync_tree`/`prune_export` distinguishes "the kit deleted this
  on purpose" from "the export repo added this and the kit never had it" — both look identical
  from the code's point of view (files present in the export, absent from `wanted`), which is
  exactly why the two are indistinguishable without an owner ruling on whether the kit or the
  repo is authoritative for a given path. This matches the docstrings' own stated design (`sync
  tree docstring, publish.py:1189-1203`; `prune_export` docstring, `publish.py:1054-1107`) —
  the mechanism is doing exactly what it says, and the incompatibility with a second writer
  editing the export directly is a property of the design, not a bug in its implementation.
  Traced for a defect in the mechanism itself and found none; classified as **QUESTION** (a
  design/policy fact for the owner's ruling, not a defect) rather than a finding.

### 2. `catalogue_web.py --recatalogue` vs `pipeline.write_record`, the "known two-writer hazard"

Checked whether `catalogue_web.py` has any writer of `data/records/*.json` that bypasses
`pipeline`'s merge discipline. Grepped the file for `json.dump`, direct `open(...RECORDS...)`,
and any hand-rolled temp-file write of a record: **none exist.** The only record write anywhere
in `catalogue_web.py` is at `catalogue_web.py:763` —

```python
if not _P.write_record_catalogue(record_path(name, RECORDS), record):
```

— which calls `pipeline.write_record_catalogue` (`pipeline.py:985` onward), documented there as
*"the CATALOGUE's side of the two-writer contract; `write_record` below is the pipeline's"* —
the fresh cast wins on `entries`, per-entry judgments already on disk are preserved onto matching
names, disk-only entries are kept, and a key `catalogue_web` did not author (`None` in `rec`)
no longer overwrites a disk value (`pipeline.py:1009-1021`). This is the correct, designed-for
writer for exactly this hazard, and `--recatalogue` (`catalogue_web.py:641-647`) only widens
*which* sources are selected for re-cataloguing (every source, not just `entry_count == 0`
ones) — it does not change the write path at all, so there is no separate "whole-file writer"
for `--recatalogue` to bypass the contract with. **Verified clean — not a finding.**

`save_roll()` (`catalogue_web.py:180-234`), the sibling writer for `data/SWEEP_ROLL.json`, was
also checked: it goes through `roll.update_rows()`, a key-wise compare-and-swap merge, not a
whole-document write, for the same reason.

## Findings

**0 VERIFIED, 0 SUSPECTED new findings.** The two items above are QUESTIONS (mapping/design
facts requested by the brief, not defects) and one item is a re-verified-fixed prior finding
(closed, not counted). Specifically checked and ruled out, beyond what is already covered above:

- **`publish.py`**: `_scrub`/`scan_for_secrets`'s three independent secret locks (dict/list/
  tuple/set recursion with collision-suffixing, per-line scanning of arbitrarily long lines via
  `_scan_units`, compiled-bytecode exclusion) traced end to end; all match their docstrings.
  `_live_root_state`/`_live_file_state`'s three-way live/gone/unavailable classification (the
  "absence of evidence is not evidence of absence" fix) traced against every call site; a root
  or file that cannot be read is held, never treated as deleted. `push()`'s four independent
  interlocks (secret scan, ledger guard, mutation interlock read on both sides of the tree copy,
  maintenance-shift guard with token verification) traced; each fails closed on an unrecognised
  state (`_mutation_unsafe`, `maintenance_shift_live`'s own documented fail-OPEN is deliberate
  and argued in its docstring — an unreadable guard file must not wedge the publisher forever).
  `main()`'s halt re-check every loop cycle, `PushHeld`'s three-outcome contract (landed / no-op
  / held-not-a-no-op), and the `--i-hold-the-guard`/token-digest one-shot-push verdict logic
  (`_one_shot_push_verdict`) all match their extensive in-line documentation.
- **`dashboard.py`**: every panel builder (`quotas`, `throughput`, `jobs`, `library`, `watch`,
  `safety`, `metrics`, `movement`) is individually fault-isolated as its docstrings claim; the
  history file's corrupt-must-heal-not-wedge logic (`movement()`, three separate guard layers for
  non-list, non-dict-element, and non-numeric-`at` shapes) traced and confirmed correct; the
  cold-start baseline bug (`hist[0] is row`) is fixed via `hist[:-1]`. No new gap found.
- **`build_terminal.py`**: every catalogue-derived string reaching `innerHTML` (`panel()`,
  `selectSource()`, `selectWorld()`, `shelfmark()`, including the four `f.*` rows and both uses
  of `cat`) goes through `esc()` — confirmed by reading every backtick-template literal in the
  `<script>` block. The `<` -> `\u003c` neutralisation before splicing JSON into the inline
  `<script>` block, and the atomic write with denial-handling in `main()`, both match their
  documentation.
- **`worldseed.py`**: `_first`'s attested-vs-seeded provenance tagging, `to_options`'s
  band-provenance three-way split (`ok`/`unparsed`/`out_of_range`, with `unparsed` no longer
  indistinguishable from a real `tier=0`), `build_all`'s `limit is not None` fix and its
  ONOMASTICON/CONTINUITY_GROUPS unreadable-vs-partial reporting, and the designation-collision
  report in `main()` (`--write`) all traced and match their docstrings.
- **`suppressions.py`**: `_load`'s wrong-shape-is-corruption fix, `_mutate`'s compare-and-swap
  with re-apply-on-lost-race, `add`/`remove`'s fail-closed discipline (refused is not
  added/removed), `suppressed()`'s and `problems()`'s deliberate `fnmatchcase` (never
  case-folding `fnmatch`), and `_repo_listing`'s single-walk-not-per-row optimisation all traced
  and match their documentation.
- **`wh40k.py`**: all 55 axes (11 axes x 5 entries) carry a genuine 3-tuple with a `wiki`/`canon`
  provenance tag: verified by counting `axes=dict(...)` entries per roster row. `_provenance`'s
  default to `unattributed` (never `wiki`) and the gated, atomic `WH40K_ASSAYS.json` write in
  `main()` both match their docstrings.
- **`propagation.py`**: `ascension_years(1) == 0.0` re-confirmed by hand (`round(1**1.35-1.0,1)
  == 0.0`), so `observed_mark`'s loop always terminates on or before its last iteration and the
  trailing `return 0` is genuinely unreachable, matching the docstring's own claim.
- **`catalog.py`**: `load_catalog`'s missing-vs-empty distinction, and `main()`'s rc propagation
  for `address`/`read` misses, both match their documentation.

## Questions

1. **(Mapping requested by the brief, see above.)** `sync_tree`/`prune_export` treat "present in
   the export, absent from the live kit" as the single signal for deletion, with no mechanism to
   distinguish deliberate kit-side removal from owner-added content in the export. This is a
   property of the current one-way-mirror design, not an implementation defect — flagged here
   only because the brief asked for the precise mechanics ahead of the owner's ruling on which
   side (kit or public repo) is authoritative for `reference/owner_source_material/rodais` and
   similar paths.

## Coverage recorded

Recording via `sweep_plan.record('run64', [...], batch=10)` for the nine modules above, all
read in full.
