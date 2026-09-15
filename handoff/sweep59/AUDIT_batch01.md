# Sweep 59 -- AUDIT batch 01

Modules read in full: | module | lines | read (top to bottom? mtime) |
| src/drill.py | 22,035 | yes, top to bottom, in full; mtime 2026-09-14 22:21 throughout (unchanged across the whole read -- verified before and after) |

## src/drill.py

### New findings

None. Read the whole file end to end and found no new defect of the kinds in the brief's
priority list (fail-open gates, tautological checks, Hard Rule 0 caps, lost updates outside CAS,
off-by-one/inverted logic, console-window-popping subprocess calls, stale false claims in
comments). This module is unusually self-documenting: nearly every net's docstring cites the
exact order it was written against, quotes the mutation it refuses, and records how it was
watched go red before landing. The three areas the brief flagged as being edited tonight by
another agent are already fixed in the file as it stands (mtime 22:21, unchanged for the whole
read):

- **prove stderr output** (order 9f1cce19c85c): `main()`'s `--prove` branch (lines 21667-21674)
  now prints `r["stderr"]` whenever `held is None or r.get("rc")`, exactly the remedy the order
  asks for. The docstring at `prove_net` (lines 846-858) and the comment at the print site both
  cite this order by id.
- **index-spine net passes with no corpus.db** (order e3fcbbe262e2): `index_spine_agrees_with_
  the_resolver` (lines 20237-20275) now calls `_spine_fixture_index()` (lines 17143-17198), which
  builds a real 3-source index via `corpus_db.rebuild()` in a temp dir and checks it unconditionally
  before ever looking at the live `state/corpus.db`; the live index is checked too when present,
  but "no live index" is no longer a vacuous pass in a sandbox/`--prove` tree, only a live one.
- **guard roster net near `weave_index_refuses_an_eaten_escape`** (order fadd4338a7b0): the net
  itself (lines 16917-16948), the roster function `_eaten_escape_roster`/`_every_re_importer_
  carries_the_eaten_escape_guard` (lines 17026-17078), and its control
  `_the_eaten_escape_roster_scan_reads_both_answers` (lines 17081-17115) are all present and
  internally consistent -- the roster asks the AST for a module-level `_BAD_CHARS` guard and
  refuses on an empty importer set, matching the fix description.

### Known (already open orders)
- `9f1cce19c85c` -- PROVE_NET_HIDES_A_CRASHED_CHILDS_TRACEBACK. **No longer accurate.** The
  remedy is already landed (see above); this order should be closed.
- `e3fcbbe262e2` -- INDEX_SPINE_NET_PASSES_WITH_NO_CORPUS_DB. **No longer accurate.** The remedy
  is already landed (see above); this order should be closed.
- `1d45a56ae1d8` -- STALE_CITATIONS_SWEEP57_NOT_IN_EXISTING_ORDERS, `where` includes
  `src/drill.py:8`. Still accurate as filed: line 8 today is the `import time` line (the module
  docstring/imports have not moved enough to fix the drift), and the order is explicitly about
  citation drift, which citecheck cannot detect and this sweep is told not to re-file singly.
- `2f314697d52b` -- DRILL_LIVE_AUDIT_OPEN_QUESTIONS_SWEEP58 (INFO, two open questions about
  `_live_audit`'s `cwd=` handling and whether THE LIVE-STATE WITNESS should drive every sandboxed
  probe). Still accurate as recorded -- these are open questions for a ruling, not defects, and
  nothing in tonight's read answered either one.

### Checked and clean (notable things verified as correct)
- The house eaten-escape guard (`_BAD_CHARS` check at the top of the file, lines 34-36) is placed
  before `HERE`/`sys.path` setup and reads the file via `os.path.abspath(__file__)`, which is
  correct regardless of cwd; no issue from tonight's insertion pass.
- `workorders.where_targets`/`file_order` backslash-normalisation (order 5b00f9d39b94) is exercised
  correctly by `twins_do_not_merge_same_named_files_under_different_roots` and
  `twins_see_a_range_and_the_line_inside_it`; both pass their own stated properties on inspection.
- `main()`'s area list still has `drill_ledger_witness` last, with the comment explaining why
  position is coverage (order 895a99602bf0) -- unchanged and correct.
- The re-read-before-halting logic (`_reread_the_breaches`, `_wait_for_a_settled_tree`) and the
  breach-keeping (`state/drill_breach_<ts>.json`) logic at the end of `main()` are internally
  consistent with the docstrings describing them (orders 71ae3fa7e55e, 2cf4993b3a3f).
- Every `subprocess.run`/`Popen` call site in the file passes `creationflags=getattr(subprocess,
  "CREATE_NO_WINDOW", 0)` (checked across all ~15 call sites) -- no window-popping regression.
- No new tautological check, fail-open swallow, or Hard Rule 0 cap was found in the ~450
  `net(...)` call sites read.

QUESTIONS: 0
record(): ok
