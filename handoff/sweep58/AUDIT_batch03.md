# Sweep 58 — batch 03 audit

Modules read in full this batch:

| module | lines |
|---|---|
| `src/pipeline.py` | 3640 |
| `src/estate.py` | 723 |
| `src/withdraw_chapters.py` | 602 |
| `src/scope.py` | 473 |
| `src/cosmography.py` | 375 |
| `src/catalogue_aurora.py` | 324 |
| `src/scale_theories.py` | 215 |
| `src/module_index.py` | 192 |

Open-queue check run first (`workorders.open_orders()`); matches against this batch's modules
are marked KNOWN below with a currency verdict. Findings are VERIFIED against the source quoted;
none is asserted from summary text.

## src/pipeline.py

**KNOWN 26667ecd6543 (STATE_LOST_UPDATE) — FIXED, verified.** This shift's `save_state`
(pipeline.py:399-471) now takes `silence.digest_of(STATE)` before the read, re-reads and
three-way merges (`_merge_state`) against `_STATE_BASE`'s last-seen copy on a digest mismatch,
lands through `silence.replace_if_unchanged`, and re-merges on refusal up to
`_STATE_CAS_ATTEMPTS` times. `_merge_state`'s list branch (`done.entrypass` etc.) correctly
preserves an external remover's deletion (e.g. `health.reopen_stranded`) — traced by hand: for
`base={a,b}`, `ours={a,b,c}` (this runner appended c, never touched b), `disk={a}` (another
writer removed b), the output is `{a,c}` — b stays dropped without needing an explicit
"removed-by-other" test, because it is absent from `disk` and not in `added` (`ours - base`).
`_fold_state` mutates `st` in place (`cur[:] = v` for lists, recursion for dicts) so aliases held
across a phase (`done_keys = st["done"]["entrypass"]`) see the merged result. Docstring's claim
that a scalar both sides changed is "this runner's" is upheld by the generic fallback
(`return ours` when neither `ours==base` nor `disk==base` nor `ours==disk`). No new defect found
in this mechanism.

**KNOWN a803028ab794 (ONOMASTICON_TWO_WRITERS_NO_CAS) — FIXED, verified.** `phase_weave`
(pipeline.py:3325-3349) now calls `onomast.land_onomasticon(resolved)` — the single
compare-and-swapped writer `onomast.main()` also uses (confirmed by reading onomast.py:702-746:
digest taken before `name_worlds()` re-reads the prior, lands via
`silence.replace_if_unchanged`, re-runs `name_worlds` against the winner's copy on a digest
mismatch). `phase_weave` correctly branches on `O.OnomasticonUnreadable` (refuses, appends
`False` to `landed`) and reports `onom_landed`/`onom_why` when the CAS itself was refused. Two
writers, one writer function, verified.

**DEFECT MAJOR — withdraw_chapters.py's new CAS on `catalog.json` does not cover its actual
co-writer, `generate.py`.** See the withdraw_chapters.py section below; recorded here too because
diagnosing it required reading `phase_write` (pipeline.py:3116-3256), which is what launches
`generate.py` against `output/index/manifest.json`, and because it directly concerns whether this
shift's fix actually closes order d5492a646306.

**QUESTION — `_STATE_CAS_ATTEMPTS = 5` (pipeline.py:316) vs. `save_state` being called once per
unit inside tight per-entry loops (`phase_entrypass`, up to ~2,600 batches).** Under sustained
contention (e.g. `health.py --reopen` running on a timer beside a live pipeline), 5 attempts with
no backoff between the digest check and the re-read (only `time.sleep` on the OSError branch, not
on a plain digest-mismatch retry) could in principle starve on a fast-writing neighbour. Not
demonstrated as live — no evidence in state/pipeline.log was reviewed for repeated
`STATE WRITE DENIED` lines — so filed as a question rather than a defect. Possibly deliberate:
the docstring's own reasoning is that a denied save just costs the run one retry.

Rest of the module (phases 1, 2, 4-8, `main()`, the two-writer record contract for
`data/records/*.json`, the meta-language ban at the foot of the file) was read in full; no new
defect found. `write_record` / `write_record_catalogue`'s per-entry, per-top-key merge and
duplicate-name pairing logic (order b418b8b3be54/b67dc1990af6 lineage) was traced against its own
extensive docstrings and is internally consistent with the behaviour claimed.

## src/withdraw_chapters.py

**KNOWN d5492a646306 (WITHDRAW_CHAPTERS_LOST_UPDATE) — PARTIALLY FIXED; one real gap remains.**
`_land_merged` (withdraw_chapters.py:115-168) is a correct compare-and-swap: digest taken before
the read, `merge(current, state)` called fresh on every attempt, lands via
`silence.replace_if_unchanged`, refuses (does not blind-write) on a genuinely unreadable file,
distinguishes "denial" (digest unchanged) from "race" (re-loop). `_catalog_merge` (line 511) and
`_manifest_merge` (line 472) both correctly recompute from the FRESH read rather than the
run-start snapshot (`cat`), so **two concurrent `withdraw_chapters.py --go` invocations** — the
scenario the order names — can no longer revert each other. Verified by tracing `_catalog_merge`:
`out = {k: v for k, v in current.items() if k not in withdrawn}` drops only this run's own
selection from whatever is currently on disk, and re-applies `amended` (partial-withdrawal path
rewrites) onto that same fresh copy.

**DEFECT MAJOR — the fix does not protect against `generate.py`, which is `catalog.json`'s other,
and more routinely concurrent, writer.** `generate.py` (verified, lines 104-149, 643, 905, 939,
945) loads `catalog = load_json(cfg["paths"]["catalog"], {})` **once** at the top of an
"hours-long generation run" (its own docstring, `save_json`'s docstring at generate.py:120), holds
it in memory as jobs complete (`catalog[job["address"]] = {...}`), and periodically lands the
**whole in-memory dict** via `save_json` → `silence.write_json(full, obj, indent=2)` — atomic
(no torn file) but **not compare-and-swapped**: it does not re-read `catalog.json` before landing
and cannot see an edit another writer made since it was loaded. `catalog.py` only reads the file;
`grep` across `src/` confirms `generate.py` and `withdraw_chapters.py` are the only two writers of
`output/index/catalog.json`.

Concrete failure scenario: `generate.py` starts, loads a catalog holding entries A, B, C. An
operator runs `withdraw_chapters.py --source "B's source" --go` while `generate.py` is still
running; the new CAS correctly lands a catalog with B removed and moves B's chapter files into
`output/withdrawn_<date>/`. `generate.py`'s next periodic `save_json(cfg["paths"]["catalog"],
catalog)` (generate.py:939 or the final one at :945) still holds B in its stale in-memory `catalog`
dict and writes it back — B's row reappears in `catalog.json`, pointing at `raw_path`/
`compressed_path` under `output/raw/`/`output/compressed/`, which no longer hold that file (it is
now the archive's only copy). This silently resurrects an entry the CAS fix in the same file was
built specifically to make impossible, by an actor outside this module — this shift's fix closes
the withdraw-vs-withdraw race but leaves the withdraw-vs-generate race exactly as open as
order d5492a646306 found the file.

Remedy: either `generate.py`'s `save_json` calls for `cfg["paths"]["catalog"]` need the same
key-wise compare-and-swap `withdraw_chapters._land_merged` and `roll.mutate`/`roll.update_rows`
already use elsewhere in this tree, or `withdraw_chapters.py --go` needs to refuse to run (or the
two need a shared lock/interlock) while a `generate.py` run is live — the same class of guard
`pipeline.py` uses (`codewatch`) for its own single-instance assumption. Not filed as a workorder
by me (read-only batch); flagging for the coordinator.

Rest of the module (`select`, `_file_state`, `_archive_name_free`, the stray-sweep, exit-code
handling) read in full; no further new defect found.

## src/estate.py

Nothing found. Checked: `inspect()`'s file-type dispatch (`.jsonl` line-at-a-time, `.json` whole,
`TEXT_EXT` + `ast.parse` for `.py`, binaries/logs sized only) matches its own docstring's claims;
the stat-retry-then-classify logic (`live`/`gone`/`unavailable`) in `inspect()` correctly treats an
`OSError`/`ValueError` from `os.stat` as "unavailable" rather than "gone"; `artifacts()`'s root
discovery is genuinely dynamic (`os.scandir(HERE)`), not a re-introduction of the hand-kept-list
defect its own comment describes fixing. `charter()`'s four erratum checks are real tests against
the document's own parsed tables (band_rows/rung_rows), not string-presence tests. All four
`note()` closures (`charter`, `written`, `terminal`, `external`) consistently grade real absences
`bad=True` and known-accepted conditions `bad=False`, matching the module's stated grading
doctrine. This module makes no writes of its own (audit-only), so no CAS/lost-update surface to
check.

## src/scope.py

Nothing found. `scope_for`'s `ProbeUnread` exception correctly distinguishes "not read" from "read
and nothing cleared MIN_MENTIONS" (verified against `_CLEAN_NEGATIVE = ("http-404",)`); `build()`
does not cache a probe failure as a verdict (a raised `ProbeUnread`/generic exception leaves the
host out of `out` entirely rather than writing `None`); `mutate()` (line 297) is the same
digest-before-read / fresh-read-per-attempt / `replace_if_unchanged` CAS shape verified in
`pipeline.save_state` and `withdraw_chapters._land_merged`, applied key-wise
(`cache.update(probed)`) so a concurrent `--host` re-probe cannot be reverted by a `--build` crawl
landing later with its own stale snapshot — this module's version of the exact hazard flagged
above for `withdraw_chapters.py`/`generate.py`, already closed correctly here.

## src/cosmography.py

**KNOWN 7099a092abd3 (BATTERY_IS_THE_ONLY_CALLER_OF_THIRTEEN_PUBLIC_FUNCTIONS) — still accurate.**
Re-verified by grep: `kardashev_K` and `kardashev_to_magnitude` have zero callers in `src/` outside
`verify_math.py` and `cosmography.py` itself (`assay.py:374` only mentions
`kardashev_to_magnitude` in a comment). Matches the order's claim exactly.

No other findings. `validate()`'s two-tier check (ratio ceilings that scale with the census, plus
the absolute `SIZE_CLASS_MAX_GALAXIES` ceiling read off each size class's own declared
description) is internally consistent with its own docstring's account of why the ratio-only
check couldn't have caught the POCKET/MINOR multiplier bug it describes. `kardashev_to_magnitude`'s
`reached = None` initialisation correctly answers "no band" rather than defaulting to
`ladder[0]`, matching its docstring's stated fix.

## src/catalogue_aurora.py

Nothing found. `slug()`/`record_path()`'s uncapped-identity-with-legacy-fallback logic is
consistent and does not risk splitting an existing record (exact name checked first, then the
prefix-anchored legacy truncation). `parse_folder`'s dedup key now includes `desc`, so distinct
same-named elements from different subclasses are kept (matches its own worked example). `main()`
gates every write verdict it produces: `write_record_catalogue`'s landed/denied result gates
whether a source is added to `written`/`roll_changes`, and `roll.update_rows` (not a whole-roll
land) is used for the roll write, with the verdict reaching the process exit code
(`return 1 if refused or not roll_landed`). No un-gated write found.

## src/scale_theories.py

Nothing found; module's own "held, not wired" claim was independently re-verified rather than
taken on faith. `grep -rln scale_theories src/` returns `descending_ladder.py`, `drill.py`,
`entity_match.py`, `liveness.py`, `onomast.py`, `tempus.py`, `tiers.py` — every one of those
references is a comment, not an `import`/call (checked each with a targeted grep of the actual
line). `surviving_theory()`'s single-survivor invariant is asserted by raising rather than by a
silent `{}`/tautology, matching its own docstring's stated fix (order e7dc70db782b).

## src/module_index.py

Nothing found. `_modules()` genuinely walks `src/` recursively (`os.walk`, only `__pycache__`
excluded) rather than a non-recursive glob, matching its docstring's claim about
`src/deprecated/catalogue_local.py` now being reachable. The duplicate-group-name check
(`seen_in`/`dupe_names`) and the stale-group-name check are independent, both computed, both
reported to stderr AND folded into a nonzero return code (not merely printed and swallowed) — the
document write itself is also gated on `silence.replace_retry`'s verdict before either check's
result can turn the exit code nonzero.

## Coverage stamp

`sweep_plan.record("run58", [8 module names above], batch=3)` — see result below.

## Summary of new (non-KNOWN) findings

- DEFECT MAJOR — `src/withdraw_chapters.py` (also noted against `src/pipeline.py`'s `phase_write`
  as the launcher of the other writer): the new compare-and-swap on `catalog.json` closes the
  withdraw-vs-withdraw race named by order d5492a646306 but not the withdraw-vs-`generate.py`
  race, because `generate.py`'s own `catalog.json` writer (`save_json` at generate.py:117-149,
  called from a `catalog` dict loaded once at generate.py:643 and held across an hours-long run)
  is a plain atomic whole-document write with no compare-and-swap and no re-read. A `generate.py`
  cycle in flight when `withdraw_chapters.py --go` runs can silently resurrect the withdrawn
  catalog row on its next periodic save.
- QUESTION — `pipeline.py`'s `_STATE_CAS_ATTEMPTS = 5` retry budget under sustained external
  contention on `PIPELINE_STATE.json`; not demonstrated live, flagged for awareness only.
