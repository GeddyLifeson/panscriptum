# Sweep 59 -- AUDIT batch 13

Modules read in full: | module | lines | read (top to bottom? mtime) |
| --- | --- | --- |
| src/assay.py | 1914 | yes, full (2026-09-08 17:30) |
| src/dashboard.py | 1249 | yes, full (2026-09-08 16:31) |
| src/threads.py | 1013 | yes, full (2026-09-13 23:22) |
| src/manifest_builder.py | 672 | yes, full (2026-09-14 00:01) |
| src/zfighters.py | 537 | yes, full (2026-09-01 00:01) |
| src/hosts.py | 425 | yes, full (2026-09-13 21:34) |
| src/style_audit.py | 343 | yes, full (2026-09-14 22:14) |
| src/tuning.py | 287 | yes, full (2026-09-06 22:44) |
| src/lognames.py | 53 | yes, full (2026-08-29 22:18) |

## src/assay.py

### New findings

**DEFECT MAJOR -- `assay()`'s `hand_readings` parameter has no Layer-1 gate, and silently
publishes `± nan` or raises a raw TypeError -- the exact bug already fixed for its twin door**

where: src/assay.py `_interval()` lines 1245-1249 (mtime 17:30), reached from `assay()`'s call
at lines 1354-1355; `assay()` signature line 1255-1256.

evidence:
```
1245	    hand_var = 0.0
1246	    if hand_readings and len(hand_readings) > 1:
1247	        m = sum(hand_readings) / len(hand_readings)
1248	        hand_var = sum((x - m) ** 2 for x in hand_readings) / (len(hand_readings) - 1)
1249	        parts["_between_hands"] = round(hand_var, 6)
```
`assay(anchor, scores, ..., hand_readings=None, weights=None, sigma=None)` passes
`hand_readings` straight to `_interval` with no validation anywhere -- unlike `scores`
(`_check_scores`), `weights` (`_check_weights`), and `interval_from_hands`'s own `readings`
argument, which this same file hardened with `_check_readings` for precisely this reason
(order 50e8d8be9a9b, whose docstring is quoted below).

failure: reproduced live against the running module:
```
A.assay("M3", dict(A.CHARTER_KENSHIRO), attestation="Witnessed", worksheet="w",
        hand_readings=[float('nan'), 3.0])
  -> {"interval": nan, "moth_number": "𝔄 M3.52 ± nan", ...}
A.assay("M3", dict(A.CHARTER_KENSHIRO), attestation="Witnessed", worksheet="w",
        hand_readings=["seven", 3.0])
  -> TypeError: unsupported operand type(s) for +: 'int' and 'str'
     (raised from _interval() line 1247, not from a Layer-1 door)
```
This is precisely what `_check_readings`'s own docstring (lines 707-746) says the third door
was built to stop: "An interval of nan is not a plus-or-minus... it is not wide, it is absent,
and it prints as a bar," and a raw TypeError "reports a LINE, not a fault, so the caller is
told the instrument broke rather than that their reading was not a number." That fix was
applied only to `interval_from_hands`'s `readings` dict -- `assay()`'s own `hand_readings` list
parameter, which feeds the identical arithmetic (`m = sum(...)/len(...)`, `sum((x-m)**2...)`),
was never given the same gate.

remedy: validate `hand_readings` at the top of `assay()` (or inside `_interval`, before the
`hand_var` block) the same way `_check_readings` validates `interval_from_hands`'s `readings`:
every element finite and numeric, or refuse with `AssayIntegrityError`.

Currently latent: `grep -rn hand_readings src/*.py` shows the only callers are
`verify_math.py`'s battery (clean numeric lists), so no production path is exposed today --
the same "no production caller yet" state this file already tolerates for `interval_from_hands`
itself, `band_for_quantity` and `null_instrument` (see Known below), each kept and hardened
anyway because it is "where the PUBLISHED +/- comes from the day a Custodial Assay pass is
commissioned." This is that same apparatus with the gate missing on one of its two doors.

### Known (already open orders)

**7099a092abd3** (`assay.band_for_quantity` / `null_instrument` / `interval_from_hands` have no
production caller) -- NO LONGER OPEN / STALE AS WRITTEN. The order asked for an owner ruling on
whether to delete or keep these three. The code now carries, at each of the three sites
(lines 354-361, 1630-1636, 1768-1779), "REPORTED DEAD, NOT DELETED -- and RETAINED BY OWNER
RULING... Closes order 7099a092abd3." The ruling has been made (keep, mark, don't delete); this
order should be closed in state/workorders.json rather than re-filed. (Not a finding against
assay.py -- flagging only because the brief asks to say when an order is stale.)

### Checked and clean

- `_check_constants()` (import-time gate): every cross-table invariant it asserts (sigma
  monotonicity, the old vs new SIGMA_MAX ceiling, BAND_EDGES completeness/monotonicity/symmetry
  with LADDER, ATTESTATION_FLOOR ordering, INSTRUMENT_WINDOWS/LADDER agreement, FACULTY_READS
  targets, the BAND_EDGES/NON_ENERGETIC_AXES/WEIGHTS partition) verified against the live values
  in this file; all hold.
- `axis_score()`'s ordering of checks (band -> axis existence -> quantity) and its M10
  top-rung branch match the docstring's worked examples exactly.
- `_check_scores` / `_check_weights` correctly precede all arithmetic in `assay()` and
  `instrument()`, closing the `𝔄 M3.-90` / `ZeroDivisionError` / Instrument-out-of-1-30 holes
  their own comments describe as historical bugs.
- `calibration_report()`'s sweep no longer mutates the shared `SIGMA_BY_ATTESTATION` table
  (uses the per-call `sigma=` argument) -- verified no global rebind exists in the loop.
- ceiling/floor clamps in `assay()` (`_dec >= 0.995` / `_dec < 0.0`) are symmetric and use the
  same threshold the display rounding needs (0.995, matching `round(_dec*100)`'s own boundary).

## src/dashboard.py

### New findings

**DEFECT MAJOR -- the Standards panel's severity sort silently treats "high" as the LOWEST
priority because of JS's `0 || default` gotcha, so HIGH-severity work orders sort to the
bottom instead of the top**

where: src/dashboard.py, `panelStandards`, line 898 (mtime 16:31).

evidence:
```
898:    bad.sort((a,b)=>({high:0,medium:1,low:2}[a.severity]||3)-({high:0,medium:1,low:2}[b.severity]||3));
```
`{high:0,...}["high"]` evaluates to `0`, and `0 || 3` evaluates to `3` in JavaScript because `0`
is falsy -- so every "high"-severity work order is scored rank 3, identical to an unrecognised
severity, while "medium" (1) and "low" (2) score correctly. Sorting ascending by that rank
therefore orders the list medium, low, high -- HIGH-severity findings display LAST, after low.

The Python-side twin of this exact rank table, `standards.work_orders()` and
`standards.report()` (`src/standards.py:2385` and `:2416`), uses `rank.get(v["severity"], 3)` --
`dict.get` correctly returns the stored `0` for "high" -- and `standards.py:2416`'s own comment
even says "the dashboard's panel already uses it," i.e. the two were meant to agree and one of
them silently does not.

failure: `src/standards.py` positional-argument severities confirm "high" is a real, live value
(e.g. lines 459, 829-858, 1114, 1154, 1259 etc., all `_s(..., "high", ...)`). Any run with an
open HIGH-severity standard (the WORK ORDERS block exists specifically to surface those first)
renders that entry at the bottom of the list on the one page whose job is showing the worst
finding first ("This is the Standards panel — the one instrument that says where things stand
against spec"; MAX_HIGH_FINDINGS gates a whole standard on this count).

remedy: `({high:0,medium:1,low:2}[a.severity] ?? 3)` (nullish coalescing, which only falls
through on `undefined`/`null`, not on `0`), or use `Object.prototype.hasOwnProperty` /
`in` rather than `||`.

### Checked and clean

- `quotas()`'s `worst` seeding/None handling, `_tail_match`'s hint-based format-mismatch
  detection, `movement()`'s corrupt-history healing and reset-detection (`delta < 0`), and
  `safety()`'s FileNotFoundError-vs-unreadable distinctions across halt/gate/drill/escalation
  all match their extensive inline documentation and reproduce correctly by inspection.
- `_ttl()` memoization keys are distinct per panel and do not collide.
- `metrics()`'s tail-read (`f.seek(-tail_bytes, 2)`, dropping the first partial line) is correct.

## src/threads.py

### New findings

**DEFECT MINOR -- `main()`'s printed T4 edge count can overstate live T4 coverage for any
magnitude-asserting entry whose source has no resolvable spine code**

where: src/threads.py `main()` lines 951-957 (mtime 23:22).

evidence:
```
951	    try:
952	        import weave_index as _WI
953	        _t4 = sum(1 for _r in _WI.load_records()
954	                  for _e in ((_r or {}).get("entries") or []) if asserts_a_magnitude(_e))
955	        print("   T4 edges (Law citation) : %s   on the entries that assert a Magnitude band; "
956	              "the rest make no claim a Law governs" % format(_t4, ","))
```
`_t4` is computed by walking every entry in every record and testing `asserts_a_magnitude`
alone -- it does not check whether that entry's SOURCE resolves to a live spine code. But
`threads_for()` (lines 706-715) raises `ThreadRefused` for any source with no record in the
graph, and `build()` never adds an entry for an `UNADDRESSED` source's edges at all -- so a
magnitude-asserting entry belonging to an unaddressed source would be counted in `_t4` while
never actually producing a T4 edge (its source's entries get no Threads section at all,
T4 included).

failure: currently latent -- verified against the live corpus (`threads.build()` +
`weave_index.load_records()`): 0 unaddressed sources today, and of 486 magnitude-asserting
entries, 0 sit in an unaddressed source, so `_t4` and the true count agree right now. But
per CLAUDE.md Hard Rule 2, a populated source with no spine code yet is "the ORDINARY case,"
and this module's own `threads_for` docstring names exactly this shape as "LATENT WHEN IT WAS
WRITTEN, NOT HARMLESS" for the identical reason (an unaddressed source is the ordinary case
that would go live silently). The day an unaddressed source asserts a Magnitude, this printed
line overstates T4 coverage with nothing saying so.

remedy: filter `_t4`'s generator on `ADDR.spine_code_for(_r.get("source")) != UNADDRESSED` (or
equivalently exclude sources present in `graph["unaddressed"]`), so the printed count matches
what `threads_for` can actually emit.

### Known (already open orders)

- **325ccb493c45** (should an Annex join key that resolves to no record BLOCK the build or only
  be REPORTED) -- still open and still accurately describes the code: `build()` reports
  `annex_join_unmatched` (lines 637-647) and does not refuse. No change since the order was
  filed.
- **b186bc4dad8f** (topic is not category; three axes, not two) -- historical incident, already
  restored per the order's own text (5,293 of 5,418 rows recovered). `category_path()`
  (lines 441-502) already implements the current three-axis doctrine correctly (subroom first,
  `FINER`-gated topic fallback, category always the coarse room) -- no outstanding defect in the
  code as it stands; the order remains useful as the historical record of why the code is shaped
  this way.

### Checked and clean

- `edge()`'s two refusals (class not in DERIVABLE; address does not resolve) are both reachable
  and both fire correctly against fixtures walked by hand.
- `annex_join()`'s ABSENT-vs-UNREADABLE distinction, and its per-row malformation checks
  (added sweep58-batch15), correctly raise `AnnexJoinUnreadable` rather than degrading to `{}`.
- `counts()`'s T1/T2/T3 arithmetic matches what `threads_for()` actually expands to, verified by
  the same reasoning the comments give (T1 per entry, T2 per (category, sibling), T3 per entry
  per source-level Canon).
- `verify()`'s post-round-trip checks are reachable (unlike the pre-repair tautologies its own
  docstring records) and correctly scoped to T1/T2/T3 only, leaving T4 (not stored) and the
  "quiet one" (structurally unreachable, per its own note) out.

## src/manifest_builder.py

### New findings

None found beyond what is already recorded in this file's own extensive inline history.

### Checked and clean

- `load_record()`'s slug-matching (exact match first, then length-floored, closeness-ranked
  inexact containment) correctly resolves all 215 sources by the reasoning its comments give.
- `pack_feats()`'s flush-before-exceeding slicing is verified correct by hand-tracing the loop;
  every oversized entity's feats are paginated in full, never truncated.
- `series_members` / `volume_code` numbering is computed over `numbering_pool` (the full roll)
  and applied to `build_pool` (the filtered set), so `--only`/`--pilot` cannot change another
  source's address, per order 372168774ee7.
- The unassigned-sources report is rewritten unconditionally every run (not gated on
  `unassigned` being non-empty), avoiding the staleness bug its own comment describes.
- Both the manifest write and the report write check `silence.write_json`/`replace_retry`'s
  landed verdict and report failure rather than assuming success.

## src/zfighters.py

### New findings

None found. Hand-authored data module; `compute()`, `value()`, and `main()`'s ranking/banding
logic are internally consistent and match `assay.py`'s `LADDER`/`moth_number` contract.

### Checked and clean

- `main()`'s Son Goku fallback correctly marks `_incomplete` rather than silently omitting him
  from the ranking loop (which skips keys starting with `_`).
- The final write goes through `silence.write_json` and checks the landed verdict before
  printing success.

## src/hosts.py

### New findings

None found beyond the already-open order below.

### Known (already open orders)

**3fb312a72435** (hosts.py has no caller anywhere in the pipeline) -- STILL ACCURATE. Re-verified
live: `grep -rn "import hosts" src/*.py` returns only `descending_ladder.py`/`scale_theories.py`
(comments quoting the finding) and `drill.py` (test-harness fixtures importing it as `H`, and
one drill fixture literally named `"claimer.py": "import render\nimport hosts\n"` as a mutation
target -- not a production call). `grep -rn "hosts_for(\|SOURCE_HOSTS" src/*.py` outside
`hosts.py` itself returns only comments in `descending_ladder.py`/`onomast.py`/`scale_theories.py`
naming the same gap. `feats.py` still mines only from `WIKI_HOSTS.json`. No change since the
order was filed.

### Checked and clean

- `add()`'s compare-and-swap retry loop (5 attempts, digest-before-read, pid+thread-unique temp)
  correctly distinguishes True/False/None as documented.
- `discover()`'s three-way `keep is _PROBE_FAILED` / `keep is None` / normal-list handling
  correctly separates "raised", "roster too thin to score" and "probed, held nothing."
- `_load()`'s ABSENT-vs-CORRUPT distinction is correctly applied by both `primary_host` (via
  `.get()`, not tripped since `_load` only raises on a real parse/type fault) and `hosts_for`.

## src/style_audit.py

### New findings

None found. This module's self-test (`--self-test`) already exercises both over-collapse and
over-fire directions for the shape detector, the banned-tell scanner, `TURN_ENDING`, and
em-dash counting, with a positive and a negative fixture; traced the fixtures by hand against
`entries()`, `record_of()`, `opener_shape()`, and `TURN_ENDING` and they produce exactly the
counts the self-test asserts.

### Checked and clean

- `TURN_ENDING`'s `\Z` anchor (not `$` under `re.M`) is correctly non-line-oriented, matching
  its own docstring's account of the bug it replaced.
- `_cut()` is applied correctly to all four rankings in `report()`; none is capped before the
  remainder is computed (Hard Rule 0), including the two-stage cut in EXACT OPENERS (window +
  `c>1` filter, both counted against the right denominator).

## src/tuning.py

### New findings

None found.

### Checked and clean

- `regime()`'s cloud/local/starved decision matches its own worked comments; `judged` correctly
  gates the success-rate veto on `MIN_CALLS_TO_JUDGE`.
- `profile()`'s cloud worker count is read from the SAME `_CACHE["buckets"]` that produced the
  cached verdict (no re-read-uncached mismatch).
- `workers()`'s ceiling-not-floor contract, including the `requested=0` boundary case the
  docstring calls out, behaves as documented (`min(0, n) == 0`).

## src/lognames.py

### New findings

None. Five-line constant map plus an `OWNER` dict of process fragments; verified every fragment
in `OWNER` is specific enough to distinguish the job it names from a different invocation of the
same script, per the module's own stated rule, by inspection against the comment's own
reasoning (no external files to cross-check within this batch's scope).

QUESTIONS: 0

record(): ok
