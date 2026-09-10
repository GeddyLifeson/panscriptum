# SWEEP run54 — batch 08 audit

Modules: `src/workorders.py`, `src/liveness.py`, `src/derivation.py`, `src/gpu_lane.py`,
`src/worldseed.py`, `src/runguard.py`, `src/suppressions.py`, `src/context_budget.py`

Every module was read in full, top to bottom (not sampled), using `Read`/`Bash cat -n`. Two
modules (`derivation.py`, `liveness.py`) were also exercised live against the current tree —
`derivation.check_graph()` and `liveness.scan()` were actually run, not just read — because both
make falsifiable claims about the current state of `src/` that a static read cannot confirm.

---

## src/workorders.py (2097 lines)

Read in full (five passes of ~400 lines). This is the newest and most heavily cross-checked
module in the batch — nearly every function's docstring narrates a past incident, the fix, and
how it was verified, and I re-derived several of those fixes against the current code rather than
trusting the narration (e.g. re-traced `_fire`'s polarity at all eleven call sites in
`sweep_detectors()`, re-traced the CAS ordering in `_mutate`/`runguard`-style claims, re-traced
`resolve()`'s "did it land, then did it exist" ordering). All of that checks out as currently
correct — the historical bugs described are, in fact, fixed in the code as it stands today.

### MINOR — `WHERE_TARGET` silently drops the end of a cited line range
**Where:** src/workorders.py:808 (`WHERE_TARGET`), consumed by `where_targets()` (816-827) and
`twins()` (830-873)
**What:** `WHERE_TARGET = re.compile(r"\b((?:[A-Za-z0-9_.-]+/)*[A-Za-z_][A-Za-z0-9_]*\.py)(?::(\d+))?")`.
The docstring at 804-808 claims this is "widened by an optional `:line`... so
`src/workorders.py:405-419`, `workorders.py:resolve,main` and `deprecated/catalogue_local.py:12`
all parse."
**Why it is wrong:** the line-number group is `(\d+)`, digits only, so for a range like
`405-419` it captures only the start, `"405"`, and silently drops `-419`. Verified directly:
```
>>> WHERE_TARGET.findall("src/workorders.py:405-419")
[('src/workorders.py', '405')]
```
The three examples in the docstring do all produce *a* match (the claim is technically true at
that level), but the docstring's own first example is precisely a range, and the range's end is
lost with no marker. The practical effect is on `twins()`'s `by_file_line`/`file_line_clusters`
grouping (the tool this project reads to find one fault held by several open orders): an order
citing `foo.py:405-419` and a second order citing a specific line inside that range, e.g.
`foo.py:410`, will group under different keys (`foo.py:405` vs `foo.py:410`) and will NOT surface
as a same-line twin candidate — they only meet at the coarser `by_file`/`file_clusters` level.
**Confidence:** high — read the regex, then ran it directly against the exact three strings the
module's own docstring cites as "all parse."

### Everything else in this module: clean, with what I checked
- Re-verified `sweep_detectors()`'s `_fire(ok, ...)` polarity at all eleven call sites (LEDGER_
  STRUCTURE, LEDGER_CHAIN, LIVENESS_RATCHET, SECRET_STAGED, all four BATTERY_CODES,
  STRANDED_SYNTHESIS, AGENT_SCRATCH_IN_PUBLISHED_TREE, LEGACY_CAP_BOUNDARY_IN_OPEN_QUEUE,
  CLOSED_ORDER_BACK_IN_THE_OPEN_QUEUE, ORDER_ADDRESSED_TO_A_RUNG_THAT_CANNOT_REACH_IT) — every one
  currently passes the *healthy* predicate as `ok`, so `_fire` resolves on health and files on
  fault, matching the module's own account of the run-#33 polarity bug it says it fixed.
- Traced `_mutate`'s compare-and-swap (digest-before-read, retry against a fresh `_load()`,
  pid+thread+attempt temp names) and `resolve()`'s "landed, then existed" ordering — both
  internally consistent with the incidents they cite.
- Traced `_supersede_binding_suspect` against `BINDING_DECIDED_CODE` — closes the sibling verdict
  correctly, leaves the undecided (`BINDING_SUSPECT`) case alone.
- Traced `ghost_orders()`/`closed_at()` — the "time separates a recurrence from a restored
  snapshot" argument holds given `resolve()`'s delete-then-append ordering.
- `order_id`/`where` identity contract, `where_split_by_code`, `cap_boundary_scan`,
  `LEGACY_CAP_BOUNDARY` — read for off-by-one/inverted logic; none found.

---

## src/liveness.py (1054 lines)

Read in full. Ran `liveness.scan()` live against the current tree and inspected `dead_class`
specifically, because the module's own worked example for why the dead-class pass exists cites a
finding that is falsifiable today.

### MINOR — stale worked example: `escalation.Refused` is no longer dead, and the docstring doesn't say so
**Where:** src/liveness.py:296-304 (`_classdefs` docstring)
**What:** The docstring says, citing order 209391b4f990: "measured over this tree,
`escalation.py`'s `class Refused` — ... — is never raised, caught, imported or named anywhere in
src/, while its sibling `SystemHalted` is raised and caught in two modules."
**Why it is wrong:** this was true when that order landed, but a later, unrelated order
(`da15f582b2ea`, 2026-09-08, visible in `src/escalation.py`'s own `refuse_unit`/`refuse_source`
docstrings) added `raise Refused(...)` at `src/escalation.py:1103` and `:1119`. Confirmed two ways:
```
grep -n "Refused(" src/escalation.py   # lines 1103, 1119 — both `raise Refused(...)`
```
```
>>> import liveness; liveness.scan()["dead_class"]
[]   # empty — Refused is no longer reported dead, and correctly so
```
The detector itself is *not* wrong — `scan()` correctly reflects the current, fixed state — but
the docstring's illustrative example is now inaccurate as a description of today's `src/`, and a
future reader trying to reproduce "measured over this tree" as a sanity check on the dead-class
pass will not find what the citation describes. This is exactly the "claim in a comment that the
code no longer honours" shape the sweep brief asks for, just with the twist that the *code*
(escalation.py) changed out from under an unrelated module's (liveness.py's) citation of it,
rather than liveness.py itself drifting.
**Confidence:** high — grepped `src/escalation.py` for `Refused(`, read the surrounding
`refuse_unit`/`refuse_source` functions and their own dated order number, and ran
`liveness.scan()` against the live tree to confirm `dead_class` is empty.

### Everything else in this module: clean, with what I checked
- Re-derived the DFS cycle-safety notes are moot here (no cycles in the ledger this module
  concerns itself with — this is a code-scanner, not the ledger).
- Confirmed the "seen always holds at least key itself" dead-`else` fix (order 114a34e9a97a) is
  actually gone from the current `scoped[key] = set().union(*[...])` line (551) — no conditional
  remains.
- Read `_credit_attrs`/`_scope_aliases`/`scoped` (the receiver-aware DEAD pass, order 6c479972e838)
  for the specific false-positive shape its own docstring worries about (`import X as R` aliased
  differently in two functions of the same module) — the per-scope alias layering handles it
  correctly by inspection.
- Read the TAUTOLOGY, PHANTOM (including the `match`/`case` and short-circuit-statement widening),
  and `reachability()` (subprocess-coverage) passes end to end; no inverted conditions or dead
  branches found beyond the one above.

---

## src/derivation.py (811 lines)

Read in full. Ran `derivation.check_graph()` and `derivation.main()` live, because the module's
own comments cite specific counts (112 quantities, 71 with a derivation chain, an 89-bit address
space) that are checkable facts about the current ledger, not just prose.

**Checked and confirmed:**
- `check_graph()` returns zero problems against the live `LEDGER` (112 entries) — no dangling
  parents, no rootless DERIVED entries, no unsigned OWNER entries, no cycles.
- The "71 of the 112 quantities have a chain" claim in `main()`'s comment (line ~761) matches a
  live count (`len([q for q in LEDGER if depth(q) > 0]) == 71`).
- The cross-module claim in the `SCAN_MODULES` comment block (473-583) — that `verify_math.py`
  independently reconstructs the same recursive `os.walk` rather than importing
  `derivation.SCAN_MODULES` — was verified by reading `src/verify_math.py:10868-10892`: it does
  reconstruct independently, with matching `__pycache__` exclusion, so the two walks cannot
  silently drift back out of step without a test noticing.
- `scan_constants_with_reason`'s three-shape parsing claim (tuple unpack, `AnnAssign`, chained
  `A = B = value`) was checked against `_target_names` and the `ast.Assign`/`ast.AnnAssign`
  handling — correctly implemented.
- The early-return-on-cycle fix in `main()` (order 90516d53d696) is present: `problems` non-empty
  returns 1 before the deepest-chain walk, which is what stops the previously-cited infinite
  oscillation.

No findings. Clean.

---

## src/gpu_lane.py (684 lines)

Read in full. This module's entire design is "every failure path proceeds"; I specifically
checked that none of the fail-open paths have been inverted into fail-closed ones, since that
would be a severe, silent regression class for this file.

**Checked:**
- `_alive()`'s Windows `OpenProcess`/`GetExitCodeProcess` path against the documented POSIX-idiom
  bug it replaced — correctly distinguishes `ERROR_INVALID_PARAMETER` (dead) from
  `ERROR_ACCESS_DENIED`/unknown (alive), with alive as the fail-open default.
- `_take_slot()`'s three-way return (path / `False` busy / `None` unarbitrable) is consumed
  correctly at both call sites in `lane()` — the `None` branch breaks out of the wait loop
  immediately rather than polling to the 900s ceiling.
- `_write_claim`'s verdict is actually read by `foreground()` (order e7b6dcc8d630) rather than
  discarded.
- `_touch()`'s "never resurrects" guard (`rec.get("pid") != os.getpid(): return`) is intact.
- `_heartbeat` refreshes every path it's given (slot and, for a foreground call, the claim path
  too) — `_keep` in `lane()` includes both when `fg is not None`.
- `_slot_count()`'s handling of `OLLAMA_NUM_PARALLEL=0`/`"auto"` falls through to the next source
  rather than clamping to 1, matching its own stated fix.

No findings. Clean.

---

## src/worldseed.py (532 lines)

Read in full.

**Checked:**
- `build_all(limit=0)` — the `is not None` guard is placed before the append it guards, so
  `limit=0` returns an empty list rather than letting one entry through (order 82adeee9b7ee is
  correctly implemented as described).
- `to_options()`'s band-parsing three-way (`ok`/`unparsed`/`out_of_range`, with `band_provenance`
  distinguishing an unparsed band from a genuinely unassayed one) — correctly implemented; the
  `unparsed` arm is reached only when `band not in ("unassayed", None)` and the regex fails, tier
  stays 0 but is now tagged rather than reading as ordinary unassayed.
- `main()`'s write path (`args.write`) returns 1 on a denied write and falls through to `return 0`
  otherwise — no missing return.
- The `"primitive"` size-table entry and `URL_SETTABLE`/`unreachable_by_url` dead code are all
  explicitly owner-ruled "mark and keep, delete nothing" (orders 40e98eed6870, e68664e621bf,
  c0384991bfc5) — saw the markings, not filed as findings.
- `TEMPLATE`, `CLIMATE_BAND`, `CULTURE_SET` dicts all have complete coverage of the vocabulary the
  matcher tables (`LANDFORM`, `CLIMATE`) can produce — no `KeyError` surface.

No findings. Clean.

---

## src/runguard.py (382 lines)

Read in full.

**Checked:**
- The digest-before-read ordering in `claim()`, `beat()`, `release()` — traced the actual race it
  closes (a competitor's write landing between digest and read still causes the eventual CAS to
  refuse, because the expected digest is always older than or equal to what was actually read,
  never newer) — correct in both directions analysed.
- `holder_is_live()`'s fail-open-on-missing-heartbeat behaviour, and that `read_verdict()` now
  distinguishes absent (`None, None`) from torn (`None, "<reason>"`) from present-but-unprovable
  (rec, "<reason>") — `claim()` escalates at SAFETY on the fault case without blocking the claim,
  matching the cited owner ruling (order 70f66fbd98aa).
- `beat()`/`release()`'s ownership checks (`owner != agent`) both correctly refuse before touching
  the record.

No findings. Clean.

---

## src/suppressions.py (353 lines)

Read in full.

**Checked:**
- `_load()`'s three-state return (absent / wrong-shape / unreadable) all route through
  distinguishable paths, and `add()`/`remove()` both refuse to write over an unreadable file
  rather than landing an empty list on top of it.
- `suppressed()`/`problems()` use `fnmatch.fnmatchcase` (not `fnmatch.fnmatch`) — confirmed both
  call sites, so a suppression pattern cannot silently widen through Windows case-folding.
- `_repo_listing()` is built once and lazily (only when a wildcard row is actually present) rather
  than once per row.
- `main()`'s `--check`/`--list` mutual exclusion, and the `_preview()` truncation-with-marker on
  the *display* side only (never on the stored `reason`, which was the actual historical bug it
  narrates having fixed).

No findings. Clean.

---

## src/context_budget.py (296 lines)

Read in full, including verifying one of its own cross-file claims.

**Checked:**
- The claim that `generate.py` sets `num_predict: -1` (the output-side ceiling this module's
  input-side budget is meant to complement) — confirmed via `grep -n "num_predict" src/generate.py`
  (line 294, `"num_predict": -1`).
- `estimate_tokens`/`estimate_prose_tokens` direction of pessimism: `CHARS_PER_TOKEN = 3.0` (low,
  so token estimates run high) for content, `PROSE_CHARS_PER_TOKEN = 4.0` (measured 4.19/4.63,
  kept below both) for scaffolding — both push the budget in the safe (smaller) direction as
  claimed.
- `feats_block_budget()`'s two corrections (`JOB_OVERHEAD_CHARS` subtracted before the metadata
  division, `METADATA_INFLATION` dividing rather than multiplying the room) both narrow the
  returned budget, which is the correct direction for a function whose failure mode is an
  over-large block that gets silently truncated by Ollama.
- `assert_fits()` raises with the actual numbers rather than returning a boolean silently.

No findings. Clean.

---

## Summary

- MAJOR: none.
- MINOR: 2 — `src/workorders.py:808` (WHERE_TARGET drops line-range ends), `src/liveness.py:296-304`
  (stale `Refused` worked example, now falsified by an unrelated later fix in `escalation.py`).
- INFO: none filed (nothing found that was worth recording as a note without being one of the
  above).
- Clean modules (read in full, checks noted above): `derivation.py`, `gpu_lane.py`, `worldseed.py`,
  `runguard.py`, `suppressions.py`, `context_budget.py`.
