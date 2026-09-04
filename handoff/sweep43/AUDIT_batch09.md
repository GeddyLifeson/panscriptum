# Sweep 43, Batch 9 — audit

Files read in full: src/foreman.py, src/allsweep.py, src/rosetta.py, src/zfighters.py,
src/sevenfold.py, src/cosmography.py, src/resonance.py, src/audit.py

Method: every candidate below was checked against the exact source lines and, where cheap,
proven against a runnable snippet rather than argued from memory. Two findings below were
confirmed with a live reproduction (foreman.py's SQL pattern, tested against an in-memory
sqlite table).

---

## src/foreman.py

### MAJOR — `clear_learned_caps`'s SQL pattern wipes legitimately-learned rate caps, not just the mis-learned `rpm: 1`

**file:line:** src/foreman.py:159-161

```python
n += c.execute("update bucket_state set learned=NULL "
               "where learned like '%\"rpm\": 1%' or learned like '%\"rpm\":1%'"
               ).rowcount
```

**What actually happens:** SQLite `LIKE '%X%'` matches wherever the literal substring `X`
occurs, with no requirement that a digit boundary follows it. `"rpm": 1` is a literal PREFIX of
`"rpm": 10`, `"rpm": 11`, ... `"rpm": 19`, `"rpm": 100`...`"rpm": 199`, `"rpm": 1000`, etc. So
this UPDATE clears every bucket whose learned rpm happens to start with the digit `1`, not only
the genuinely mis-learned `rpm: 1`.

Verified directly (not just reasoned about) with a throwaway sqlite table:

```
rows tried:  {"rpm": 1}, {"rpm": 10}, {"rpm": 15}, {"rpm": 100}, {"rpm": 2}, {"rpm": 19}, {"rpm": 21}
MATCHED (would be wiped): rpm=1, rpm=10, rpm=15, rpm=100, rpm=19
NOT matched (correctly spared): rpm=2, rpm=21
```

**Why it matters:** the function's own docstring says the buckets it exists to un-pin have
"documented caps of 10, 10 and 15" (Gemini, Gemini Lite, Groq). A bucket that has correctly
LEARNED a real cap of exactly 10 or 15 — the very numbers this docstring names — gets its
learned value wiped by the same query that is supposed to only clear the false `rpm: 1`
pinning. This is called automatically by the `foreman` remedy loop for three different
standards ("no bucket pinned at rpm 1", "calls that succeed", "model calls per hour"), so a
healthy, correctly-learned rate limit is erased on a schedule, which can reintroduce the 429
storms this whole mechanism was written to stop. It is the identical bug class this same file
elsewhere calls out and fixes explicitly — `adopt_hosts`'s "0 adopted" substring match and
`_checks_pass`'s "0 FAILED" vs "10 FAILED" substring match — but this instance was not caught.

**Suggested remedy:** anchor the match on a value boundary, e.g. `learned like '%"rpm": 1,%'`
OR `learned like '%"rpm": 1}%'` (both terminators JSON can produce), or parse `learned` as JSON
and check the actual `rpm` field equals 1 rather than pattern-matching the serialized text.

---

### MINOR — `_catalogue_batch`'s reported "universe_size" undercounts the true short-source universe

**file:line:** src/foreman.py:795-857, specifically the return at :856-857 (`len(gap)`)

**What actually happens:** `gap` starts as every source the completeness audit calls short.
Before `len(gap)` is captured and returned as `universe_size` (called `whole` at the call site),
two subsets have already been popped out of `gap`: `off_roll` (named by the audit but absent
from the roll) and `unnameable` (cannot be given an unambiguous `--only` fragment). Both are
real, populated categories on the live data per this function's own docstring ("Warhammer
40,000", "Gundam (all centuries...)" for unnameable; sources named by the audit that have since
left the roll for off_roll). So `whole` = short sources minus off_roll minus unnameable, not
"every source the audit says is short", even though the docstring insists three separate times
that "the universe is WHOLE (every source the audit says is short by one or more)".

`run_catalogue_gap` then prints:

```python
print("   AUTO   catalogue: %d of %d short source(s) this round, longest-waiting first: "
      % (len(batch), whole) + ...)
```

A reader sees "N of whole short sources" where `whole` is silently smaller than the real count
of short sources whenever off_roll or unnameable is non-empty — which the module's own comments
say is the normal case (54 short, 35 uncatchable by the old filter; several sources have
commas in their names).

**Why it matters:** nothing is actually lost here — off_roll and unnameable are each printed by
full name on their own line — so this is not a Hard Rule 0 truncation. But the headline "N of
whole" number is the one figure a person actually reads for "how much of the library is short",
and it is quietly smaller than the true count in exactly the situation this module was written
to make visible.

**Suggested remedy:** capture `len(gap)` for the "whole" figure before popping off_roll and
unnameable (or report a separate `true_universe = len(gap_before_off_roll_and_unnameable)`), so
the printed denominator matches the module's own stated invariant.

---

## src/rosetta.py

### MINOR — `refine()`'s "rows kept" counter includes rows from scales that are then discarded entirely

**file:line:** src/rosetta.py:426-443

```python
for title, sc in scales.items():
    vals = {n: v for n, v in sc["values"].items() if _norm(n) in known}
    dropped += len(sc["values"]) - len(vals)
    kept += len(vals)
    if len(vals) < 4:                  # below four rows a scale cannot rank anything
        continue
    if sc["kind"] == "numeric":
        lo, hi = min(vals.values()), max(vals.values())
        if lo <= 0 or hi / lo < 100:
            continue
    keep_scales[title] = {"kind": sc["kind"], "n": len(vals), "values": vals}
```

**What actually happens:** `kept += len(vals)` runs before the two `continue`s that drop a
scale outright (fewer than 4 matched rows, or a numeric scale whose span is a progression
ladder rather than a power scale). A scale that matches, say, 3 catalogued names gets those 3
rows counted into `kept`, then the whole scale is discarded and none of those 3 rows appear in
`out` — the dict that is actually written to `data/ROSETTA.json`.

`main()`'s `--refine` path prints this count as ground truth:

```python
print(f"rows kept          : {kept:,}   dropped: {dropped:,}")
print(f"scales surviving   : {sum(len(v) for v in out.values())} across {len(out)} wikis")
```

**Why it matters:** `kept` does not describe what actually survived into the file on disk — it
overcounts by the row totals of every scale that got dropped by the 4-row floor or the
magnitude-span filter. `kept + dropped` is arithmetically self-consistent (it always equals
`before`), which is exactly what makes the discrepancy easy to miss: the two printed numbers
look reconciled while `kept` is not describing `out`.

**Suggested remedy:** only add to `kept` for scales that make it into `keep_scales` (move the
`kept += len(vals)` line after the two `continue`s, or track a separate
`kept_but_scale_dropped` counter and print it alongside).

---

## src/allsweep.py

No findings after a full read. VERIFIERS' rc_means grading, the LINT tier's did-not-complete
detection, `estate_faults`, and RECONCILE's per-check logic (host/record/roll reconciliation,
coverage staleness, cache-directory orphans, purge-ghost detection, phase implementation,
band-ceiling violation, and the live-process census against `overnight.ALL_JOBS`) were all
checked line by line against what they claim to do and match. The "cascade live call" verifier
being red is the known environmental quota condition named in the brief and is not re-filed.

## src/zfighters.py

No findings. The hand-authored ROSTER content is a curatorial artifact, not code, and is out of
scope for a correctness audit. `compute()`, the Goku-sheet fallback, the ranking/printing loop,
and the gated write at the end all do what they say.

## src/sevenfold.py

No findings. `affinity_order`, `_even_cuts`, `seams()` (including the window + weaker-half-only
cut selection), `split()`, and `build()`'s two-population UNSHELVED accounting were checked
against their extensively-documented fix history and match.

## src/cosmography.py

No findings beyond one already self-documented, non-hidden condition: with the current
`GALAXIES_DEFAULT` and `SIZE_CLASSES` constants, `census("POCKET")` and `census("MINOR")` both
raise (200 and 2.0e5 galaxies respectively against a declared ceiling of 1), and the code's own
comment already says this is "FOR THE OWNER, AND LEFT FOR THE OWNER" pending a charter ruling on
which constant is wrong. Not re-filed as a new finding since the module already surfaces it
honestly; see the Questions section below for a one-line flag in case it has gone stale.

## src/resonance.py

No findings. `hodge_decompose`'s Gauss-Seidel sweep, the no-evidence/non-convergence fail-closed
paths, `dominates`, and `incomparability_rate` were checked and are correct. The module's own
"NO PRODUCTION CALLER" status is the known, already-recorded condition (order f467f662be4b) and
is not re-filed.

## src/audit.py

No findings. `VALID_BANDS` was checked against `pipeline.BANDS` directly
(`["M10",...,"M0","unassayed"]`) to confirm `"unassayed"` is a legitimate ladder value and does
not spuriously fail the `band not in VALID_BANDS` check. The denominator-by-class fix, the
uncapped violation listing, and the two explicitly-labelled samples (not claiming to be
exhaustive) are all correct.

---

## Questions (owner judgment, not filed as bugs)

1. **cosmography.py POCKET/MINOR ceiling conflict** — already self-documented in the code
   (`SIZE_CLASS_MAX_GALAXIES`'s comment) as an open charter ruling: either
   `SIZE_CLASSES["POCKET"]`/`["MINOR"]` or their own "at most one galaxy" descriptions are
   wrong, since both currently compute galaxy counts that exceed their own declared ceiling and
   so `census()` refuses for both size classes today. Flagging only to confirm this is still on
   the owner's radar and hasn't silently become dead code (i.e., that something still calls
   `census("POCKET")` / `census("MINOR")` and the refusal is actually being seen, not swallowed
   somewhere upstream). Not re-filed as a work order since the code already names the decision
   it is waiting on.
