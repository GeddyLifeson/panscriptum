# Sweep41 Batch 02 — Audit of `src/verify_math.py`

**Scope**: `src/verify_math.py` (8,441 lines at start of read; grew to 8,593 lines mid-audit —
see note below). Companion file `handoff/run35/checks_L6.py` (329 lines) reviewed as in-scope
context, since it is spliced/executed by verify_math.py's §20u.

**Method**: read the entire file top to bottom in ~700-line chunks (offsets 1, 601, 1301, 2001,
2701, 3400 [detail], 3530, 4230, 4930, 5630, 6330, 7030, 7730, and finally the newly-added tail
at 8420-8593). Cross-checked suspicious patterns with AST-based scans (self-comparison
tautologies, conditionally-executed `check()` calls, `try` blocks wrapping `check()` calls) run
directly against the live file, and verified specific claims against the actual battery run and
against `src/assay.py` source.

## A live edit landed mid-audit

Partway through this read, `src/verify_math.py` grew from 8,441 to 8,593 lines (+152) — someone
(not this agent) added a new section, order **1036c659495d**, "and no row promises a tolerance
that check() will throw away" (new lines ~8508-8585), immediately before the final RESULT block.
This is a well-built addition: it AST-scans every `check(..., tol=...)` call for a `want`
argument that is provably int-valued (bare int literal, `int()`, `len()`, `ord()`,
single-argument `round()`, or int arithmetic over those), which is exactly the case where
`check()`'s own `if isinstance(want, float):` branch silently discards the caller's `tol=` and
falls through to exact equality — a real, previously-undetected instance of the "check whose
scope is narrower than its name" family this sweep is hunting for. It carries both a positive
control (5 fixtures it must catch) and a negative control (4 fixtures it must not flag),
matching this file's own house style. I read this new section in full and it introduces no
defect of its own. Re-ran the battery after it appeared: **1084 passed, 0 FAILED** (up from the
1078 quoted in my task brief, consistent with the new checks landing). I did not edit anything;
this is reported for the record per the task's warning that another agent had just touched this
file.

## Findings

**None filed.** After a full read plus targeted AST scans for the specific failure shapes named
in the brief, I found no new instance of:

- **A check that cannot fail** — searched for `check()` calls whose `got`/`want` arguments are
  textually identical AST source segments (the historical tautology shape this file has caught
  and fixed repeatedly, e.g. orders 3f86c571da58, fbdb7fe3bd4c, cc500a6cbf4b, dbc2937118da,
  96c4be60fb92, 498dd8b268f7). Zero hits.
- **A check whose scope is narrower than its title claims** — the one known instance in this
  file, §19ag's `silence.append_line` tearing check, already carries the note added earlier
  today stating plainly that it only exercises ONE process and that the real concurrency
  guarantee now lives in `drill.py`'s multi-process net. Read in full at lines 3398-3453;
  correctly scoped and honestly labelled now.
- **A stale fixture** — spot-checked several hardcoded-looking constants (the six
  `handoff/run35/checks_L*.py` file count at line ~8204, the `_EXPECT20p` guard counts, the
  `>= 20` / `>= 55` / `>= 60` parse-coverage floors); all are either re-derived live from the
  filesystem/AST each run or carry an explicit, reasoned margin against drift, and none were
  stale against the current tree (verified the file count directly: `ls
  handoff/run35/checks_L*.py` returns exactly 6).
- **A probe writing into a live ledger unwrapped** — verified via the file's own end-of-run
  ratchet (§20z, "no probe anywhere in this battery writes into the live failure ledger"),
  which passed on the actual run I performed (`_escaped20z == []`), and independently confirmed
  `handoff/run35/checks_L6.py`'s three probes (`mutate.py:reap-incomplete`,
  `mutate.py:reap-skipped-live-owner`, `reference.py:shelfmark-shape`) are each wrapped in
  `_no_ledger_L6()` now, matching today's fix described in the task brief.
- **An aspirational assertion requiring editing each run** — the `prose_enabled`/`step4_enabled`
  gate checks (§20x, lines ~5403-5424) look like this shape at first glance but are the opposite:
  they pin an exact *value* precisely so that any future flip requires an explicit, documented
  owner ruling and an edit to this row — the row's whole point is to be edited only alongside a
  recorded ruling, not silently.
- **Hard Rule 0 truncations hiding evidence** — none found; every cap-related check in this file
  (§19g, §19i, §19v, batch3's coverage.report()/standards.py caps) asserts the ABSENCE of a
  silent cap or the presence of an announced one.

## Considered and explicitly NOT filed

- **`if isinstance(_cal, dict): check(...)` at line ~6259-6263** (§20r, the calibration-margin
  guard mutation net). This guards a single check behind a condition on `_cal =
  A.calibration_report()`. I traced `calibration_report()` in `src/assay.py:625-670` and
  confirmed it has exactly one `return` statement and no other exit path — it always returns a
  dict, so the guard is currently unreachable-false and the check inside it always runs. This
  is the same *shape* as the "conditional check that silently skips" anti-pattern §20k and §19d
  exist to refuse, but it is not currently an instance of it, since the guard cannot presently
  evaluate False. Filing a work order over defensive code that is provably harmless today felt
  like exactly the over-claiming the task brief warns against ("audits are wrong in both
  directions"). Flagging it here in prose rather than as an order: if `calibration_report()`
  ever grows an early-return path, this guard would start silently absorbing a check failure,
  and whoever touches that function should know the guard is watching.
- **`_sigma_table_refuses`'s bare `except Exception: return False`** (line ~6089-6090). Considered
  whether a broad except could mask a bug in `A._check_constants()`, but traced the two call
  sites: both assert the return value against `True`, so if `_check_constants()` raised an
  unexpected exception type instead of `AssayIntegrityError`, the helper would return `False` and
  the assertion would correctly go red (just with a less informative reason). Not a masking
  defect — no order filed.

## Coverage

Recorded: `sweep_plan.record('run41', ['verify_math.py'], batch=2)` — confirmed present in
`state/sweep_shards/` for run41.

## Summary for the sweep coordinator

8,441 lines read at start, plus the 152-line addition that landed mid-audit (read in full),
totalling everything currently on disk in `src/verify_math.py` (8,593 lines), plus
`handoff/run35/checks_L6.py` (329 lines) in full. Zero new work orders filed — this module has
been worked hard today (the 19ag scope note, the two LF/CRLF byte checks, the ledger-escape
detector, the checks_L6.py probe wrapping, and now the tol= discard scan all landed within the
audit window) and a thorough read plus AST-level cross-checking turned up no further unverified
defects of the kind this sweep is built to find.
