# AUDIT batch01 — sweep40 — src/drill.py

Module read in full: `src/drill.py` (9,275 lines). This is the whole-tree drill harness
(37 `drill_*` areas, all wired into `main()`'s battery loop — verified no defined `drill_*`
function is missing from the `for fn in (...)` tuple and no name in that tuple is undefined).
The file is extraordinarily self-auditing: nearly every net's docstring already documents a
prior defeat found by an earlier sweep (run #31 through #40) and the fix that closed it. Most
candidate "findings" turned out, on verification against the current source, to be already-
handled cases the file discusses at length. Two verified findings survive that scrutiny.

## Finding 1 (MINOR) — the "ordinary multi-line file" fixture in
`_the_scanner_reads_files_over_two_megabytes` is not actually multi-line, and does not test
the case its docstring claims

**File**: `src/drill.py`, function `_the_scanner_reads_files_over_two_megabytes`, lines
2709–2745 (net registered at line 2681, inside `drill_publish`).

**Quoted docstring claim** (lines 2721–2727):
```
    So the fixture is the fix here: three files that actually cross the threshold, in the
    three shapes the streaming reader has to handle.

      * an ordinary multi-line file over 2 MB, with the secret at the very end;
      * a SINGLE-LINE file over 2 MB -- a 3 MB one-line JSON register IS one line, and the
        naive repair (read line by line) still loads the whole thing;
      * a secret STRADDLING THE SEGMENT SEAM, ...
```

**Quoted code** (lines 2733–2743):
```python
    filler = "the custodian recorded the specimen in the usual manner. "
    try:
        def only(name, body):
            ...
        long_line = filler * 55_000                     # ~3.1 MB, no newline anywhere
        if not only("big.md", filler * 40_000 + _AWS_EXAMPLE + "\n"):
            return False
        if not only("register.json", _AWS_EXAMPLE + long_line):
            return False
```

`filler` is a single sentence with **no `\n` inside it**. `filler * 40_000` (the body of
`big.md`, the fixture claimed to represent "an ordinary multi-line file") therefore contains
**exactly one** `\n` in the whole ~2.36 MB body — the one appended at the very end after the
secret. That is structurally identical to `long_line = filler * 55_000`, which the very next
line's own comment calls "no newline anywhere" and which is the base of `register.json`, the
fixture explicitly claimed to be the *single-line* case.

Verified against `src/publish.py`'s actual reader (`_scan_units`, lines 350–392): it reads in
fixed `_SCAN_BLOCK` (262,144-byte) chunks and only takes the "ordinary per-line `yield`" path
when a block contains a `\n`; a logical line longer than `line_cap` falls into the
"OVERLAPPING SEGMENTS" branch (`while len(buf) > line_cap: ...`). Because `big.md`'s body is
one ~2.36 MB logical line (over the 2,000,000-byte `line_cap` used by this net's `seam`), it
takes the exact same segmentation branch as `register.json` and `minified.js`. The three
fixtures this net's docstring describes as testing "the three shapes the streaming reader has
to handle" are actually only two distinct shapes: two copies of "single long line, segmented"
plus the seam-straddling variant. The genuinely different third shape — an ordinary file made
of many short lines (each well under `line_cap`) that only exceeds `max_bytes` in aggregate,
which is what the incident's own named examples ("a 3.36 MB register," "a 2.97 MB citations
file," "a 2.68 MB terminal page," "a 2.47 MB data script") most plausibly look like for a prose
or data file rather than a one-line JSON blob — is never exercised by any fixture in this net.
The net still catches the actual regression it was written for (the bare `continue` that
skipped any file over `max_bytes` entirely, which all three fixtures being over 2 MB still
triggers), so this is not a "cannot fail" defect — but the coverage claim in the docstring is
false, and the ordinary-per-line code path through `_scan_units` (the `yield lineno, carry +
buf` / `for mid in parts[1:-1]` branches) is left completely unexercised by this net.

**Why it is wrong**: a safety net's docstring is what a person trusts when deciding the net has
already proven a property; here it asserts three-way coverage that the fixture construction
does not deliver, and the actual majority code path of the reader (ordinary short lines) has no
regression test in this file at all.

**Remedy**: give `big.md` real line breaks, e.g. build it as
`("\n".join([filler] * 40_000)) + _AWS_EXAMPLE + "\n"` (or insert `\n` inside `filler` itself),
so it genuinely exercises the per-line `yield` path with a file whose total size crosses
`max_bytes` while no individual line does. This is a one-line change to the fixture and needs
no change to `publish.py`.

## Finding 2 (INFO/MINOR) — stale `file.py:NNN` cross-references in narrative comments have
drifted from the lines they cite

**File**: `src/drill.py`, multiple locations (spot-checked; not exhaustive).

Several long docstrings cite an exact line number in another module as evidence for a claim
made in the surrounding prose. Checked against the current source:

- Line 4667: `` `feats.py:148`, `min(BACKOFF_MAX, _BACKOFF.get(host, 1.0) * BACKOFF_GROWTH)` ``
  — the clamp is now at `src/feats.py:159`, not 148 (verified: `grep -n BACKOFF_MAX
  src/feats.py` shows the constant at 112 and the clamp expression at 159).
- Similar drift was found spot-checking `pipeline.py:822`, `coverage.py:53`,
  `feats.py:918-923`, `withdraw_chapters.py:50`, `pipeline.py:2122`, `cascade_bridge.py:1060`,
  `cascade_bridge.py:1118-1120`, `cascade_bridge.py:282`, `cascade_bridge.py:1192` — each is off
  by anywhere from a few to several dozen lines against the current file.
- By contrast, `local_agent.py:849` / `:868` (cited at `drill.py`'s
  `_failed_revert_is_escalated` docstring) were verified **exact** — so drift is not universal,
  it accumulates unevenly as the cited files are edited.

**Why this is lower severity than it looks**: none of the actual `net()` checks *use* these
line numbers — every check that needs to survive a refactor is written against the AST (by
symbol/call/branch, as the file's own extensive commentary about "CITED BY SYMBOL, NOT BY LINE
(order a09a0e003c31, run #37)" in `verify_math.py` explains was deliberately done elsewhere in
this project for exactly this reason). The line numbers here are pure narrative decoration for
a human reader trying to go verify a historical claim, and a drifted one sends that reader to
the wrong line rather than breaking any check.

**Remedy**: either drop hard line numbers from narrative comments in favor of function/variable
names (as `verify_math.py` already does per its own comment), or add a cheap periodic
LOCAL/BOTS-tier job that greps `drill.py` (and similarly-styled files) for
`\b[a-z_]+\.py:\d+\b` citations and checks each still points at a line containing the token the
surrounding sentence quotes.

## Areas checked and found sound (no finding filed)

- `coverage_totals_never_exceed_their_entry_count` (drill.py ~5340) sums only `cited`, `read`,
  `no_page`, `no_host` and omits `not_attempted` from the overflow check. Verified against
  `src/coverage.py:110-182`: `state_of()` returns exactly one of five mutually exclusive states
  per entry and `measure()` tallies via a single `Counter`, so `not_attempted` is definitionally
  `entries - (the other four)` and can never itself be the source of an overflow that the other
  four don't already show. Omitting it from the sum is correct, not a gap.
- All 37 `drill_*` area functions are both defined and present in `main()`'s battery tuple
  (checked programmatically) — no orphaned "check that never runs" at the top structural level.
- `two_long_names_sharing_a_prefix_get_two_files` (drill.py ~5814) asserts
  `len(one) > ESC._NAME_MAX` but not `len(two)`. This is an asymmetric assertion, not a
  tautology or a defect — the property under test (`one != two`) is symmetric and fully
  covered; flagged here only as something a future editor might tighten, filed as INFO, not
  worth a work order on its own.
