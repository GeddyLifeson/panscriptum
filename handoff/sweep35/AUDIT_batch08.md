# sweep35 batch08 audit

Modules read completely: src/feats.py (1311), src/derivation.py (590), src/catalogue_web.py (441),
src/autostart.py (347), src/genre.py (289), src/render.py (252), src/snapshot.py (210),
src/withdraw_chapters.py (128). 3,568 lines total.

## Findings filed (4, all MAJOR, found_by=sweep35-batch08)

- `dc27521160c1` -- feats.py:534-556 -- `discover()`'s allpages/search calls are still capped
  at aplimit=500 / srlimit=50 with no continuation loop; the `continue` token is only counted
  into `_CAP_BOUND` as a measurement, never followed. An entity with more evidence pages than
  the cap is still discovered in part -- Hard Rule 0 shape, now with an honest counter instead
  of a fix.
- `ea2f5e924fb2` -- catalogue_web.py:117-121,278-282 -- both `catalogue()` and
  `catalogue_composite()` drop a title when `ws.page_texts()` returns a falsy `""`, with zero
  counting. `wiki_source.page_text()` returns the same `""` whether all three section fetches
  failed on the network or the page genuinely has no lead prose -- the project's signature
  ambiguity, unaddressed here even though `catalogue_composite`'s own `failed_cats` tracking
  one function over states the doctrine ("A FAILED SUB-CATEGORY IS NOT AN ABSENT ONE") that
  page-level failures violate identically.
- `cda7b9e2b4e1` -- withdraw_chapters.py:74-86,111 -- no `--source`/`--only` selector exists;
  `--go` unconditionally moves every entry in the current `output/index/catalog.json` and then
  overwrites the catalog with `{}`. Safe on 2026-08-25 only because the whole catalog was the
  bad set that day. The tool's own comment anticipates a future unrelated `--go` run (that's why
  `--label` was made dynamic) but nothing was added to let that run target a subset -- so a
  future withdrawal against a repopulated, mostly-healthy catalog would purge the entire
  library. Currently inert only because catalog.json holds 0 entries right now (verified).
- `026a498d47d2` -- render.py (whole module) -- `view()` and every tier-view function have no
  caller anywhere in src/ outside the module's own `main()`; nothing reads `output/views/`
  (where `--write` saves the drawn-tier SVGs). The module's docstring claims to close the gap
  where the top five cosmology tiers "had addresses and no way to look at them," but that
  closure is only reachable via a manual CLI run -- never wired into catalog.py, publish.py, or
  the registry terminal.

## Notable non-findings (already fixed, verified against current source)

- `e3a69ceb5857` (ADDRESS_BIT_WIDTH_DRIFT) is now stale for its derivation.py half:
  `derivation.py:46-65` reads `address_space.TOTAL_BITS` live via `_address_total_bits()`
  (fail-closed to a string on import failure) rather than restating a literal. Still open for
  `src/profile.py:20`, which this batch did not audit.
- `8c354f6c9780` (AUTOSTART_TWIN_WATCHDOG_FAILS_OPEN_SILENTLY) is now stale: `_twin_watchdog()`
  (autostart.py:173-233) retries `TWIN_TRIES=4` times and logs "FAILED OPEN" explicitly before
  conceding -- the exact "safe middle" the order asked for is implemented.
- genre.py's `classify_text`/`classify_source` Hard Rule 0 fixes (raise on non-None `top`/`cap`)
  are intact and correctly denominate over the full field; only the *stored* `data/GENRES.json`
  is stale (already tracked by `b317ba3a4f36`).
- catalogue_web.py's `MAX_PER_SOURCE`/`MAX_PER_CATEGORY`/`CATEGORY_SCAN_DEPTH` removal is intact
  and defended by a `raise SystemExit` guard; no cap survives in the live code path.
- snapshot.py is sound: `before()` raises on a wholly-empty capture, `verify()` restores to a
  temp dir and compares directories file-by-file (not just existence), `_dir_matches` walks the
  snapshot side.

Coverage recorded via `sweep_plan.record('run35', [8 modules], batch=8)`.
