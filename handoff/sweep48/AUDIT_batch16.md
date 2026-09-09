# AUDIT — Panscriptum run #48, batch 16

**Modules assigned:** src/local_agent.py, src/binding_health.py, src/rosetta.py, src/weave.py,
src/prose_gate.py, src/sweep.py, src/coverage.py, src/tempus.py

**Lines read per module (full files, no sampling):**

| module | lines | read |
|---|---|---|
| src/local_agent.py | 1578 | 1–1578 (full) |
| src/binding_health.py | 1518 | 1–1518 (full) |
| src/rosetta.py | 793 | 1–793 (full) |
| src/weave.py | 698 | 1–698 (full) |
| src/prose_gate.py | 538 | 1–538 (full) |
| src/sweep.py | 374 | 1–374 (full) |
| src/coverage.py | 337 | 1–337 (full) |
| src/tempus.py | 297 | 1–297 (full) |

READ-ONLY throughout. No edits, no runs of `mutate.py` / `drill.py` / `verify_math.py`, no
`local_agent.py --patch`. Coverage recorded via `sweep_plan.record` (see below).

---

## FINDING 1 — MAJOR — binding_health.py: the absent-probe cannot tell "throttled" from
"genuinely absent," reproducing the module's own headline failure mode

**Where:** `src/binding_health.py`
- `_fetch_chars()` (lines 483–523), specifically line 504 (`got = F.fetch(host, [title])`) and
  line 514 (`return 0, None` on an empty `got`)
- `_probe_absent()` (lines 695–760), specifically line 733
  (`got = F.fetch(host, [ABSENT_PROBE])`) and lines 748–749
  (`if not got: return True, "correctly absent -- nothing came back for a title that cannot
  exist"`)
- `canary()` (lines 969–988), specifically lines 985–987, which call `_probe_absent` and set
  `ok_r` unconditionally right after `_probe_present`, with no interaction between them
- `verdict()` (lines 931–966), specifically line 957 (`if ok_present and ok_absent: return
  True, None`)

**What is wrong.** The module's own docstring (lines 1–37) names three ways a binding can look
dead when it is not, and lists "the host is throttling us -> every fetch returns 429, which
reads as 'empty'" as one of exactly three problems this file exists to solve, citing "74
throttled probes came back as 0%" as precedent. `feats.fetch()` and `feats.api()` were given a
dedicated `outcome` out-channel specifically for this (their own docstrings cite "orders
ef4ca9edd61f, 64e4db060ad6" and a measurement that "34,676 records (12.6%) carry
`pages_read=[]` with `pages_refused={}`... concentrated on exactly the host that was being
throttled"). On a throttle, `feats.api()` retries and then returns `None` with **no exception
raised**; `feats.fetch()` folds that into a plain `{}` return, also with no exception.

Neither `_fetch_chars()` nor `_probe_absent()` passes an `outcome=` dict to `F.fetch()`, so
neither can see *why* nothing came back — they only see the same falsy `{}` a genuine miss
would produce. `_probe_absent()`'s exception handler correctly returns `None` ("could not ask")
for a raised exception, but a throttle that `feats.fetch()` swallows internally never raises, so
it never reaches that branch. It falls straight into `if not got: return True, "correctly
absent..."` — the exact opposite of "unknown."

**Concrete failure mode verified by tracing `canary()`:** the present probe and the absent probe
run back-to-back with no shared state. If the present probe succeeds (`ok_p=True`, e.g. it
landed before a rate limiter kicked in) and the very next request — the single absent-probe
fetch — gets silently throttled, `_probe_absent` returns `(True, "correctly absent...")`.
Because `ok_p` is `True`, `canary()` never calls `_probe_reachable()` to catch this (line
987: `_probe_reachable` is only invoked `else` on `not ok_p`), so nothing else in the function
can catch it either. `verdict(True, True, True, ...)` hits `if ok_present and ok_absent: return
True, None` at line 957 and the host is reported `healthy: True` — a clean bill of health that
in fact never verified the absent-probe's premise at all. This is the mirror image of the
false-quarantine hazard `_probe_absent`'s own docstring argues about at length ("IT MATTERS MORE
HERE THAN ANYWHERE... this is the single probe outcome that can quarantine a demonstrably live
wiki with no second opinion") — the docstring anticipates the false-NEGATIVE direction and
missed the false-POSITIVE one, which is just as damaging to a module whose entire job is
proving a binding's citations can be trusted.

**How verified.** Read `feats.api()` (src/feats.py:785–907) end to end: on `e.code in (429,
503)`, after `retries` attempts it calls `_stamp(False, "throttled")` and `return None` — no
exception. Read `feats.fetch()` (src/feats.py:1465–1527): `d = api(...)`; on `d is None`, the
loop body's `for p in (d or {}).get("query", {}).get("pages", [])` simply iterates nothing, so
`fetch()` returns `{}` with no exception either. Confirmed by grep that neither call site in
binding_health.py (`grep -n "F.fetch" src/binding_health.py` → lines 504, 733) passes `outcome=`.

**Proposed remedy.** Thread an `outcome={}` dict through both `F.fetch()` calls in
`_fetch_chars()` and `_probe_absent()`, exactly as `rosetta.scales_for()` and `feats.fetch()`'s
own callers elsewhere already do for the analogous problem. When `outcome.get("why")` is
anything other than `"ok"` (or `"raw-transport"`, which is an honest unknown for RAW-mode
hosts), both functions should return `None` ("could not ask") rather than `True`/`(0, None)`, in
the same three-valued shape `_probe_absent` already uses for a raised exception.

---

## FINDING 2 — MAJOR — coverage.py: the "UNREACHABLE" state is documented but structurally
dead code

**Where:** `src/coverage.py`
- Module docstring, lines 10–22, which lists six entry states including:
  `UNREACHABLE  a host exists but the fetch failed -- the only state that is purely a defect`
  (line 21)
- `state_of()` (lines 110–144) and `_state_of_file()` (lines 147–183), which only ever compute
  or return `"CITED"`, `"READ"`, `"NO PAGE"`, or `"NOT ATTEMPTED"` (plus `"NO HOST"` at line 113)
- `report()` (lines 240–303), which prints CITED / READ / NO PAGE / NOT TRIED / NO HOST but has
  no UNREACHABLE line

**What is wrong.** The module's own contract promises six mutually exclusive states, and singles
out UNREACHABLE as special: "the only state that is purely a defect" — i.e. the one state an
operator should be able to search for to find genuine transport failures, as opposed to a
"NO PAGE" (a wiki correctly saying no) or "NOT ATTEMPTED" (nothing tried). But no code anywhere
in this file ever assigns or returns the string `"UNREACHABLE"`. `_state_of_file()`'s only
three-way branch is `st = "CITED" if feats else ("READ" if pages else "NO PAGE")` (line 179) —
a file that exists but represents a failed fetch (empty `pages_read`, empty `feats`, no evidence
of a genuine "asked and got nothing" transport success) reads identically to a genuine "asked;
no article" and is filed as `NO PAGE`, exactly as already flagged for lines 177–179. What is
additionally true, and not yet filed, is that there is no path to the documented UNREACHABLE
state at all, under any circumstance — not merely that the boundary between NO PAGE and
UNREACHABLE is misdrawn (the already-known finding), but that the UNREACHABLE branch simply does
not exist in the code.

This is a textbook "check that cannot fail": a state an operator would filter on to find real
defects will always report zero, forever, regardless of how many hosts are actually
unreachable, and nothing about that silence looks different from the state genuinely being
empty.

**How verified.**
- `grep -n "UNREACHABLE" src/coverage.py` → exactly one hit, the docstring line 21. No
  assignment, comparison, or return of that string exists anywhere else in the file.
- `report()` (read in full, lines 240–303) has print statements for every other state in the
  docstring's list except this one.
- Checked whether the battery exercises it regardless: `grep -n "state_of\b" src/*.py` finds no
  caller outside coverage.py itself; `drill.py`'s only reference to `coverage.state_of()` (line
  2442, read in context) tests the M23 ownership distinction between two names, not the
  UNREACHABLE/NO-PAGE boundary. Nothing in the tree currently exercises or could exercise this
  state.
- Confirmed the raw material to build it already exists on disk and is read by other modules:
  `feats.py` evidence records carry `pages_refused` alongside `pages_read` (feats.py:2183, and
  feats.py's own fetch()/measurement comments at ~1475), which is exactly the signal that would
  distinguish "asked, host refused/failed" from "asked, wiki said no such page." coverage.py's
  `_state_of_file()` reads only `pages_read`/`pages` and `feats` (line 177–178) and never looks
  at `pages_refused`.

**Proposed remedy.** Read `pages_refused` (or an equivalent fetch-outcome marker, ideally
threaded from the same `feats.fetch(..., outcome=...)` channel Finding 1 discusses) inside
`_state_of_file()`, and emit `"UNREACHABLE"` when an evidence file shows a failed/refused fetch
with no successful page read — distinct from the true `"NO PAGE"` case where the wiki was asked
and cleanly answered "no such article." Add the corresponding `report()` line so the promised
state is actually observable.

---

## FINDING 3 — MINOR/INFO — prose_gate.py: five stale `file.py:NNN` citations in
`cited_names_for`'s docstring

**Where:** `src/prose_gate.py`, lines 363–364, inside `cited_names_for()`'s docstring:

> "This was the only `cachekey.load` call site in the tree that did not pass `on_corrupt` --
> feats.py:1454, hostcheck.py:1374, pipeline.py:1399, read.py:804 and sweep.py:184 all do."

**What is wrong.** All five line numbers have drifted from the actual `cachekey.load(` call
sites in those files:

| citation | cited line | actual `cachekey.load(` call |
|---|---|---|
| feats.py | 1454 | 2008 |
| hostcheck.py | 1374 | 1436 |
| pipeline.py | 1399 | 1461 |
| read.py | 804 | 819 (804 is a comment discussing `cachekey.load`, not the call itself) |
| sweep.py | 184 | 192 |

**How verified.** `grep -n "cachekey.load" src/feats.py src/hostcheck.py src/pipeline.py
src/read.py src/sweep.py` and cross-checked each against `sed -n` on the cited line number to
confirm the cited line does not contain the call (see command output in this session). This is
squarely the "stale citations" defect class this codebase already has standing conventions
against (`local_agent.py`'s own comment on `foreman.py:324` drifting is a documented instance of
the identical fault, order bf22c557852e, cited in coverage.py's own header).

**Note:** this does not affect the gate's behavior — the underlying claim (that these five sites
*do* pass `on_corrupt`) is still true by inspection; only the line numbers are wrong. Low
severity, but exactly the kind of thing that costs the next reader a grep, and prose_gate.py is
a mutation-testing target where every comment is read closely.

**Proposed remedy.** Replace the hardcoded line numbers with function/site names only (as the
rest of this docstring already does for `verify_math §20x`), or re-derive and correct them.

---

## What I read and found nothing wrong in

- **src/local_agent.py**, in full. This module is unusually well-fortified: eight documented
  historical bypasses of its write-surface gates (case-folding, name-prefix, NTFS ADS,
  case-sensitive extension test, unlisted directory, junction redirection, hard-link identity,
  empty-find-string), each with its own regression comment and each verified by inspection to
  still be closed as described (`_safe()`, `_denied_target()`, `_protected_identities()`,
  `t_propose_patch()`). Traced the full gate chain in `_gates()` (parse → pyflakes → import →
  whole-suite verify_math) and the backup/revert path in `t_propose_patch()`, including the
  failed-revert ALARM/escalation path — all fail closed, and a failed revert is surfaced through
  both the audit trail and a SAFETY escalation rather than silently claimed as success. The
  blast-radius cap (`_blast_ok`), the retry/backoff in `_chat()`, and `_tool_message()`'s
  envelope-vs-payload truncation logic were all traced and found internally consistent with
  their own docstrings. No new defect found.
- **src/rosetta.py**, in full. The three scale parsers (`numeric_rows`, `ordinal_rows`,
  `stand_rows`), `spearman()`, `assays_by_host()`, `check()` and `refine()` were traced for
  off-by-one and precedence errors; none found. The host-scoped matching fix (order
  0bba50a6d76b) and the `MINE_FLOOR` non-destructive-overwrite guard in `main()` were verified
  against their own stated rationale and found correctly implemented.
- **src/weave.py**, in full. `components()`'s complete-linkage agglomeration was checked for the
  chaining/transitivity failure the module's docstring says it replaced a connected-components
  approach to avoid; the merge criterion (`min_cross(c1,c2) >= threshold`) does correctly
  preserve the "every pair in a cluster clears the bar" invariant across merges. The
  `NullThresholdUnmeasured` fail-closed paths in both `null_threshold_surprisal()` and the
  reported-dead `null_threshold()` were verified to raise rather than return a spendable 0.0.
- **src/prose_gate.py**, in full, beyond Finding 3. All four/five layers (`gate_open`,
  `step4_gate_open`, `evidence_ok`/`floor_ok`, `section_shortfall`/`assert_block_complete`,
  `instrument_shortfall`/`assert_instrument_present`, `unearned_instrument`) were traced for the
  "check that cannot fail" pattern the brief calls out. `cited_names_for`'s fail-closed empty-set
  return on any read failure is deliberate and documented (not re-reported, per instructions).
  Did not find a second instance of a swallowed failure being indistinguishable from a
  legitimate negative result inside this file.
- **src/sweep.py**, in full. `nested_run()`'s subset-chain detection and `report()`'s funnel/
  loose-population split (the fix for order 2420550a2b8e) were verified against the data they
  claim to test rather than assumed correct.
- **src/tempus.py**, in full. This module is charter mathematics/world-building rather than
  pipeline plumbing; `rung_description_length`, `band_resolution`, `prescience_horizon_bits` and
  `retrocausality_beta` were checked for sign errors and off-by-one edge cases (M0 boundary, M10
  ceiling) and none were found.
- **src/binding_health.py**, in full, beyond Findings 1–2. `_spread()`'s even-sampling math was
  checked for index collisions (none possible given `n > want` implies step `> 1`); the
  compare-and-swap paths in `quarantine()`/`release()`/`_land_cas()` and the three-valued
  `binding_verdict()` scoring were traced and, apart from the already-filed containment/subset
  defect (order 30854f11f322, not re-reported), found consistent with their documentation.
- **src/coverage.py**, in full, beyond Finding 2 and the already-filed lines 177–179 NO-PAGE
  false-positive (not re-reported). `measure()`'s fail-closed host-map read and `report()`'s
  division-by-zero guards were verified.

No caps or unmarked truncations were found in any list this batch's modules print or store —
every listing print in these eight files that truncates (e.g. `_shown`/`_rest` in prose_gate.py,
the `[:top]` in sweep.py's DEEPEST EVIDENCE table) already states the omission count.
