# Sweep 59 -- AUDIT batch 06

Modules read in full: | module | lines | read (top to bottom? mtime) |
| --- | --- | --- |
| src/workorders.py | 2507 | yes, top to bottom, offset/limit pages; mtime 2026-09-14 22:18 |
| src/ledger_guard.py | 1083 | yes, top to bottom; mtime 2026-09-14 22:14 |
| src/wiki_source.py | 808 | yes, top to bottom; mtime 2026-09-14 22:14 |
| src/autostart.py | 613 | yes, top to bottom; mtime 2026-09-13 21:37 |
| src/scope.py | 473 | yes, top to bottom; mtime 2026-09-09 23:10 |
| src/retry_synthesis.py | 379 | yes, top to bottom; mtime 2026-09-09 23:04 |
| src/resync_roll.py | 332 | yes, top to bottom; mtime 2026-09-06 22:30 |
| src/halo.py | 219 | yes, top to bottom; mtime 2026-08-29 23:32 |
| src/catalog.py | 167 | yes, top to bottom; mtime 2026-09-06 22:43 |

All nine compile clean (`py_compile`) and are clean under `pyflakes`, checked directly this batch.

## Run #59's concurrent insertion (the `_BAD_CHARS` eaten-escape guard)

Verified present and correctly placed in all three modules the brief's Known section named for
this batch: `workorders.py` (lines 48-50, before `HERE`/`sys.path`/`import silence`),
`ledger_guard.py` (lines 36-38, same position), `wiki_source.py` (lines 34-36, after this
module's own imports). Each guard is self-contained (uses only `os`, already imported, plus
`chr()`) so placement relative to `sys.path`/`silence` does not matter for correctness, and all
three still compile and pass pyflakes. `scope.py` and `autostart.py` already carried this guard
from earlier work (not part of tonight's 24-module batch) and are unaffected. `retry_synthesis.py`,
`resync_roll.py`, `catalog.py` import no `re` and correctly carry no guard. No breakage found.

Also verified: the backslash-normalisation fix (order 5b00f9d39b94) is applied symmetrically at
both of `workorders.py`'s call sites -- `file_order`'s LOCAL-denylist check (line 554) and
`where_targets` (line 965) both do `str(where or "").replace(chr(92), "/")` before matching
`WHERE_TARGET`. Consistent, no drift between the two.

## src/workorders.py
### New findings
None found. This module is exceptionally heavily hardened by prior sweeps (order ids visible
throughout: 5d3794de8b81, c5431186cc05, fb5ac415e249, 9b54659bc403, 1ba189fabcaa, e6385a07a3fd,
8dc37c208839, 263f3ae18375/2ea46665a2ea, 386c0d66e31e, and more) and every fault class the brief
asks to prioritise -- fail-open gates, tautological checks, caps/truncations, lost updates,
inverted conditions -- already has a comment recording when it was found and fixed. Traced
`_mutate`'s compare-and-swap, `file_order`/`resolve`/`reroute`'s `_change` closures, `_fire`'s
healthy/unhealthy polarity, `battery_faults`, `ghost_orders`, `twins`/`where_targets`'s overlap
math, and `cap_boundary_scan` end to end against source; found no new defect.

### Known (already open orders)
- **a5faab7f3ede** (`LEDGER_GUARD_FLOOR_RATCHETS_ON_LINE_COUNT`, filed against `ledger_guard.py`,
  not `workorders.py`, but this queue is where it is filed and tracked) -- still open, OWNER
  rung, awaiting a ruling on the floor-advance rule. Not re-filed.

### Checked and clean
- `_mutate`'s digest-before-read compare-and-swap, and every writer (`file_order`, `resolve`,
  `reroute`) is a pure function of the dict handed to it, re-applicable on a stale-write retry.
- `_fire`'s polarity (`ok` resolves, not-`ok` files) matches its own extensive comment and every
  one of its ~15 call sites in `sweep_detectors`.
- `_refuse_cap_hit` reads the same `LEGACY_CAP_BOUNDARY` dict `cap_boundary_scan` grades by; no
  second hand-kept copy to drift.
- The `MAINTENANCE_GUARD_DISAGREES_WITH_THE_PROCESS_TABLE` call site (`_fire(_gf is None, ...)`)
  looked at first glance like "unknown treated as healthy" (a fail-open shape), but
  `runguard.guard_fault`'s own docstring (lines 363-368) explains this is deliberate: "a detector
  that fires on 'I could not tell' is noise, and noise gets switched off" -- a plausible,
  reasoned design choice, not a defect, and not this module's call to change.
- `twins()`'s interval-overlap test (`s2[1] <= s[2] and s[1] <= s2[2]`) is the standard correct
  overlap condition.

## src/ledger_guard.py
### New findings
None found. Traced `_one_insertion` (prefix+suffix covers whole of `old`), `_lost_fraction`'s
multiset diff, the floor-ratchet in `seal()`, `verify_chain`'s mixed bytes/chars unit handling
(lines 875-886) -- confirmed correct in all three cases (both-legacy, both-fixed, boundary
mixed) -- and `_load_acknowledgements`'s fail-closed shape. No new defect.

### Known (already open orders)
- **a5faab7f3ede** `LEDGER_GUARD_FLOOR_RATCHETS_ON_LINE_COUNT` -- re-verified against
  `seal()` lines 483-486: the floor still advances on
  `sum(_substantive_lines(text).values()) >= sum(_substantive_lines(floor_text).values())`,
  i.e. on substantive-line COUNT rather than full retention. Still accurate; still an OWNER
  design question (a "union" rule vs strict retention), not re-filed.

### Checked and clean
- `read_chain`/`_read_chain_lines` fail closed on anything but `FileNotFoundError`.
- `assert_intact()` runs all four mechanisms (`check_all`, `verify_chain`,
  `check_since_snapshot`, `check_since_floor`) in the order needed (both baseline checks run
  before `seal()` moves either baseline), matching `main()`'s CLI which runs the same four.
- Acknowledgement records (`_load_acknowledgements`) fail closed: any malformed entry is dropped
  and the shrink it would have covered still fails.

## src/wiki_source.py
### New findings
None found. `all_categories`'s cache-key/hard_stop interaction, `find_categories`'s stated
floor, `category_members`/`rank_by_size`/`extracts`'s "raise, don't silently truncate" contract,
and `clean_titles`'s O(n) dedup were all re-verified against source. No new defect.

### Known (already open orders)
None of the open orders in `state/workorders.json` name this file specifically beyond the
already-applied `fadd4338a7b0` guard insertion (verified present, see above).

### Checked and clean
- `resolve_wiki`'s host-map-first resolution order, and its fall-through refusal for a known
  non-fandom host (does not burn guesses/verification calls against a machine already IP-banned
  once from fandom.com).
- `page_texts`' `zip(titles, pool.map(...), strict=True)` preserves per-title pairing correctly
  (`ThreadPoolExecutor.map` yields in input order).
- `CATEGORY_MIN_PAGES` floor and its unmeasurable "below floor" report are honestly described,
  not silently reported as zero.

## src/autostart.py
### New findings
None found. `_start_decision`'s priority order (unknown > running > halted > budget > start),
the tri-state `supervisor_alive()` sensor, `_twin_watchdog`'s fail-open-with-retry-and-log shape,
and `installed_state`'s content (not existence) check were all traced against source.

### Known (already open orders)
- **4c2101d54c10** `WATCHDOG_ABSENT` -- still open, OWNER rung: nothing watches the watchdog
  itself (three design options named in the order: a liveness check raised by something else, a
  Scheduled Task re-running at intervals, or a daily assertion). Still accurate as a design
  question; not re-filed. The module's own `watch()` loop (lines 465-525) still has no self-
  liveness path other than the staleness-is-reported-not-acted-on note at lines 426-453, which
  matches the order's description exactly.

### Checked and clean
- The one `subprocess.Popen` call site (`start_supervisor`) carries `_NO_WIN | DETACHED_PROCESS`.
- `_vbs_body()`'s VBScript quoting (`Chr(34)`) is correct for a path containing both quotes and
  backslashes.
- `main()`'s `--install`/`--uninstall`/`--status` verdict-to-exit-code plumbing matches the
  gated-write pattern the rest of the tree uses.

## src/scope.py
### New findings
None found. `scope_for`'s `ProbeUnread` distinction between "not read" and "read, empty",
`build()`'s per-host stamping and compare-and-swap `mutate()`, and the removed argmax-below-floor
fallback were all re-verified against source and match their own extensive commentary.

### Known (already open orders)
None naming this file specifically.

### Checked and clean
- `mutate()`'s digest-before-read CAS, keyed per host so a `--host` re-probe cannot lose a
  concurrent `--build` crawl's rows or vice versa.
- `ceiling_for()` is genuinely dead code (no callers repo-wide) and is correctly marked as such
  rather than deleted, per house doctrine.

## src/retry_synthesis.py
### New findings
None found. `synthesise()`'s three documented convergence fixes (prompt construction, transport,
acceptance-gate strictness all now taken from `pipeline` rather than restated) were re-verified
against `pipeline.py`'s corresponding functions by name (not re-read in full -- out of this
batch's module list). `save_side`'s read-merge-write-with-verdict and `do_merge`'s unmerged-source
accounting were traced end to end.

### Known (already open orders)
- **1e6f99e54b25** `CORPUS_WRITERS_WITHOUT_A_HALT_INTERLOCK` -- re-verified: `do_merge()` (the
  `--merge` path this order names) still calls no `escalation.assert_clear()` or equivalent;
  confirmed via `grep -n escalation src/retry_synthesis.py` returning nothing. Still accurate;
  OWNER ruling pending on whether a hand-run repair tool should refuse under a halt. Not re-filed.

### Checked and clean
- `synthesise()`'s per-chunk best-band selection matches `phase_synthesis`'s documented method.
- The exit-code plumbing in `main()`/`do_merge()` correctly nets denied writes and unmerged
  sources into a nonzero return.

## src/resync_roll.py
### New findings
None found. The `--dry-run` argparse fix, the sorted-record-file dedup for duplicate `source`
declarations, the snapshot-before-repair-loop ordering, and the status-repair guard against
`OUT_OF_SCOPE` rows were all re-verified against source.

### Known (already open orders)
- **1e6f99e54b25** `CORPUS_WRITERS_WITHOUT_A_HALT_INTERLOCK` -- re-verified: this module calls no
  `escalation` function anywhere (`grep -n escalation src/resync_roll.py` empty). Still accurate;
  same OWNER question as `retry_synthesis.py --merge`. Not re-filed.

### Checked and clean
- The compare-and-swap through `roll.mutate(_apply, path=ROLL)`, with the exclusion-guard
  re-checked against the fresh row inside `_apply` rather than the snapshot taken before the walk.
- `unreadable`/`unmatched_rows`/`unnamed_rows` are each counted and excluded from the closing
  "roll now: X/Y" figure, with the caveat travelling with it.

## src/halo.py
### New findings
None found. Small, single-purpose, already carries the per-axis provenance fix and the gated
atomic write with printed WRITE DENIED verdict.

### Known (already open orders)
None naming this file.

### Checked and clean
- `main()`'s `--full` output wraps evidence text (via `textwrap.wrap`) rather than truncating it.
- `silence.write_json`'s landed/denied verdict reaches the return code.

## src/catalog.py
### New findings
None found. Small CLI; already carries the missing-vs-empty catalog distinction, the uncapped
"populated sources with no books" listing, and the every-path-returns-an-rc fix.

### Known (already open orders)
None naming this file.

### Checked and clean
- `cmd_stats`'s "missing" roster is printed in full, uncapped.
- Every `main()` branch returns an explicit rc; `sys.exit(main())` at the bottom actually uses it.

QUESTIONS: 0
