# sweep45 — batch 09

**Files:** `src/publish.py` (1814) · `src/allsweep.py` (973) · `src/wiki_source.py` (689) ·
`src/ingest_doc.py` (542) · `src/burgs.py` (432) · `src/feats_index.py` (369) ·
`src/entity_match.py` (296) · `src/chord_field.py` (210) · `src/module_index.py` (137).

**5,462 lines, all read end to end. No sampling, no file partially read. No source file edited.**

## First, the two things the brief asked to be told about immediately

**No committed secrets were found.** Nothing credential-shaped on any code, comment or docstring
line in the nine files. The only literal that looks like one is `_PLACEHOLDER_CREDS` at
`publish.py:384-386`, which carries the same-line `SECRET-FIXTURE` marker by design.

**The mutation interlock and the secret scanner are intact.** Verified rather than assumed:

* `push()` calls `scan_for_secrets(SITE)` with no `only=` (`publish.py:1457`), and so does every
  other caller in the tree — `workorders.py:1201`, `secondopinion.py:438`. The only `only=` call
  anywhere is a drill net (`drill.py:3972`), which is not a push path.
* The proof named in `scan_for_secrets`' own docstring exists under the name it gives:
  `_the_scanner_reads_files_over_two_megabytes` at `drill.py:3574`, registered at `:3546`.
* `push()` fails closed on an unimportable `ledger_guard` (:1401-1408) and an unimportable
  `mutate` (:1425-1431), and refuses if **either** the sync-time or the push-time `mutate.active()`
  reading saw a non-sandboxed run (:1447-1455). `_mutation_unsafe` (:1318-1325) treats a lock
  with no `sandboxed` key as unsafe.

One order below is about publish.py, and it is about how a refusal is *printed*, not whether it
fires.

## Filed, worst first

| id | sev / handler | what |
|---|---|---|
| `de0681cb9edc` | MAJOR / RUN | `wiki_source`'s listing walks return a **silently partial roster** on a transport failure. `category_members` (:587-591), `all_categories` (:413-418), `find_categories` (:462-464), `extracts` (:608-610) and `rank_by_size`'s `fetch` (:635-637) all catch `Exception`, note it, and hand back whatever arrived. `catalogue_web.py:257-259` asserts the opposite in a comment defending the composite path — "`catalogue()`'s single-wiki path lets `find_categories`/`category_members` **raise**, so ANY transport failure fails the whole attempt honestly and the source stays retryable" — and neither function can raise. So a mid-pagination API error hands `catalogue()` an *alphabetical prefix* of a 33,614-member category, lands it, and the source records `entry_count > 0`: Hard Rule 0's own named failure arriving through a network hiccup instead of a cap, and not retryable, because it now looks catalogued. It also neuters `catalogue_composite`'s `failed_cats` tracking (:220-229), which can essentially never fill for the case it was written for — and `verify_math.py:8704-8709` certifies that tracking with a **source-text** check (`"failed_cats" in _cw_code`), which passes on the presence of two strings while the guard they name is unreachable. |
| `685da15e27fa` | MAJOR / LOCAL | `publish.main()`'s generic handler prints `str(e)[:180]` (:1799). Every refusal `push()` raises is a plain `RuntimeError` and lands there — including `PUBLISH REFUSED — N credential-shaped value(s) …` followed by **one line per leak**. The header alone is ~72 characters, so 180 leaves room for roughly one leak line. That undoes at the last step the Hard Rule 0 repair the same function documents at :1466-1479 (sweep42-batch10 removed `leaks[:20]`/`leaks[:10]` precisely because "the message they will actually read told them about ten or twenty of them"). Irreversible: the exception is discarded after the print and `silence.note("publish.py:main")` keeps only a label. The file already rules the other way twice — `git()` keeps stderr whole (order f5fdaab825a6) and `PushHeld` is printed whole under the comment "not clipped to 180 characters like a generic failure". The escalation *evidence* list still carries every leak, so the data survives; the operator's console copy does not. |
| `c453e9dad827` | MINOR / LOCAL | `module_index.main()` globs `src/*.py` (:61-62), which does not descend, so `src/deprecated/catalogue_local.py` is absent from `handoff/MODULE_INDEX.md` and the printed count reads 115 of 116, unmarked. Third site of one defect — `allsweep.modules()` (:286-304) carries the fix and names the other two under order f42c55355431. Worse here than a missing lint row: the module's whole purpose is "the map of every module in `src/`", and the page is served from the PUBLIC repo. |
| `b0078097c1a3` | MINOR / LOCAL | `module_index.py` has **no argparse**, so `python src/module_index.py --help` runs `main()` and **writes** `handoff/MODULE_INDEX.md`. `allsweep`'s IMPORT tier runs exactly that on every module every sweep, under a docstring promising `--help` runs "WITHOUT DOING ANY WORK" — so a read-only auditor writes into a published `COPY_DIRS` root on every battery run. Same shape as the cascade_bridge move at `allsweep.py:272-280`. A denied write there also grades the module BROKEN in the IMPORT tier. `feats_index.py` is the read-only sibling: no argparse, and `--help` runs the full `audit()` over `data/readfeats` plus every record. |
| `2461f532f411` | MINOR / LOCAL | `allsweep.py:857` and `:960-961` cut display fields with bare slices (`[:50]`, `[:58]`, `[:44]`) while `:836`, twenty lines up in the same function, uses `_marked` under a comment that settles the rule for exactly these columns. `:960` is the ESTATE FAULTS block — the rows a person reads in order to act — and its detail column is cut hardest in the file. Reversible display cuts; the remedy is the marker, and the helper is already at `:131-150`. |

## Corroborated, already open — not refiled

* `7e360eaec3a6` — `chord_field.py` is imported by nothing and none of its functions has a
  caller. Confirmed by repo-wide search: only prose mentions in `drill.py:81` and
  `liveness.py:253`, both listing it *as* a no-caller module.
* `4d78c426afb3` — `find_categories`' docstring promises "every category" while the discovery
  half is floored at `acmin: 40`.
* `83bf7498d135` — `all_categories`' cache key omits `hard_stop`.
* `c8dc624e4e02` — `feats_for_source` returns a bare `[]` for a source with no host binding.
* `9da4543dc586`, `cf861246e83e` — the two open `ingest_doc` orders; both re-verified as still
  live at the lines they name.
* `3d2d9b87cc10` — `sync_tree`'s `COPY_FILES` withdrawal loop, the file analogue of `f2271d9ee843`.
  Confirmed: `prune_export`'s second half reaches directories dropped from `COPY_DIRS`
  (:967-1005) and root **files** are left alone deliberately (:974-976), so a name withdrawn from
  `COPY_FILES` keeps its published copy.

## Looked at and deliberately not filed

* **`entity_match.py` has no production caller** — only `verify_math` imports it (§19o/§19r).
  It reads as priority-1 shape, but the module header states it plainly ("Latent today only
  because nothing calls this module yet"), `STEP4_PLAN.md §6` names it as future work, and it is
  written as a seam with no side effects. Deliberate, disclosed, not a defect.
* **`allsweep` VERIFIERS row `identity.py` = `RC_BROKEN`** while `identity.main()` returns 0 on
  every reachable path (verified: :689 and :707). The row can therefore only fail by crash or
  timeout — but the table's own comment says so in the line above it, so the limitation is
  disclosed rather than hidden.
* **`NEVER_RUN` is read by nothing** (`allsweep.py:101`). Grep confirms it. The constant's own
  comment says so and says why: a roster for a human, not a gate.
* **`scan_for_secrets`' `except Exception: supp = None`** (:576-580) is a bare handler returning
  without a `silence.note`. The direction is fail-safe — losing the suppression table produces
  *more* findings, which is a refusal — so it is not a hole; noted rather than filed.
* **`snapshot()`'s `except Exception`** (:648-668) is a model of the opposite: it forces
  `standards` back to `[]` *and* records the failure on a separate `standards_unavailable` key.
* **`_scan_units`, `_scrub_line`, `_is_real_secret`, `_live_root_state`, `_live_file_state`,
  `_same_dir`, `_unpushed`, `prune_export`'s None-vs-0** — each re-derived against the source and
  each does what its docstring claims. `burgs.py` and `chord_field.py` produced no findings of
  their own beyond the already-open no-caller order.

## Coverage

`sweep_plan.record("sweep45", [...nine files...], batch=9)` — recorded.
