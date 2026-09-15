# Sweep 59 -- AUDIT batch 08

Modules read in full:

| module | lines | read (top to bottom? mtime) |
|---|---|---|
| src/cascade_bridge.py | 2317 | yes, in 6 passes (mtime 2026-09-09 23:14) |
| src/silence.py | 1126 | yes (mtime 2026-09-14 00:02) |
| src/rosetta.py | 809 | yes (mtime 2026-09-13 22:27) |
| src/runguard.py | 660 | yes (mtime 2026-09-13 23:24) |
| src/catalogue_codex.py | 515 | yes (mtime 2026-09-14 22:14) |
| src/genre.py | 385 | yes (mtime 2026-09-14 22:14) |
| src/deprecated/catalogue_local.py | 333 | yes (mtime 2026-08-29 23:51) |
| src/tempus.py | 297 | yes (mtime 2026-09-08 16:28) |

## src/silence.py

### New findings

**DEFECT MAJOR -- `_handler_is_observed`'s "carries the exception into its own return value" test is satisfied by a trivial, discarded reference, so a genuinely silent handler can classify itself as observed**

where: src/silence.py `_handler_is_observed` (lines 169-209, the "carries the exception" test at lines 207-209, mtime 00:02)

evidence:
```
207    return bool(node.name) and any(
208        isinstance(n, ast.Name) and n.id == node.name
209        for stmt in node.body for n in ast.walk(stmt))
```
The docstring's own claim for this branch (lines 199-206) is narrower than what the code checks:
```
199    # A handler that carries the exception into its own return value is observed too.
```
but the implementation asks only "does an `ast.Name` node with this id appear anywhere in the
body", which is true for a Load that is immediately discarded, not only for a value that reaches
a `return`, a print, a log call, or `health.record`.

Reproduced directly against the live function (scratch script, not committed):
```
except Exception as e:
    x = e
    return None
```
`silence._handler_is_observed(node)` on this handler returns `True` -- classified OBSERVED --
even though nothing about the exception is ever recorded, printed, logged, or re-raised; `x` is
assigned and never read again. The canonical fault this whole module exists to catch
(`except Exception as e: return None`, cited in the comment two lines above the code) is defeated
by adding one throwaway assignment line, with no behavioural change to what the handler actually
does about the failure.

A second, even more minimal case behaves the same way:
```
except Exception as e:
    _ = e.args
    return None
```
also classifies OBSERVED.

failure: `python src/silence.py`'s SILENT count, and `--instrument`'s auto-rewrite target list,
both silently exclude any handler in the shape `except ... as e: <touch e once, discard it>
<swallow>` across the whole `src/` tree that this module audits -- exactly the shape Hard Rule -1
calls "a check that cannot fail looks exactly like a check that passed", now inside the detector
built to find that shape. This is a false negative in the SAFE-LOOKING direction (a handler reads
as observed when it is not), which is the direction this module's whole history (m27, the tautology
this exact function replaced at run #33, the word-boundary fix at a04cbfab2473) has repeatedly had
to re-close.

remedy: require that the loaded name actually reach one of the `_OBSERVED_TOKENS` calls, a
`return`/raise, or otherwise flow into an effect, rather than accepting any `ast.Name` reference
to the bound name anywhere in the body. At minimum, distinguish `Store` targets and immediately-
discarded temporaries from a value that is passed to a call or returned.

### Known (already open orders)

- 7099a092abd3 (BATTERY_IS_THE_ONLY_CALLER_OF_THIRTEEN_PUBLIC_FUNCTIONS) -- not filed against
  silence.py itself, no action needed here.

### Checked and clean

- `swallow`, `replace_if_unchanged`, `replace_retry`, `write_json`, `append_line`'s Windows
  locking and CRLF fixes, `_src_py_files`'s recursive walk, `_ensure_import`'s anchor logic, and
  the suppress-block detection (`_suppressed_names` / `_suppress_is_declared`) all read correctly
  against their own extensively-documented histories; no new defect found in any of them.
- The re-raise test (`ast.Raise` walked over the whole body) and the word-boundary token match
  (`_OBSERVED_RX`) are both correct as implemented.

## src/rosetta.py

### New findings

**DEFECT MAJOR -- `refine()`'s `kept + dropped` no longer reconciles with the pre-refine total when a whole scale is rejected after the per-name filter, reintroducing the exact hidden-discrepancy shape order 78f2bebed995 fixed**

where: src/rosetta.py `refine` (lines 491-545, mtime 22:27), specifically the `dropped` accounting
at line 522 versus the `continue`s at lines 523-524 and 532-533

evidence:
```
521            vals = {n: v for n, v in sc["values"].items() if _norm(n) in known}
522            dropped += len(sc["values"]) - len(vals)
523            if len(vals) < 4:                  # below four rows a scale cannot rank anything
524                continue
...
530            if sc["kind"] == "numeric":
531                lo, hi = min(vals.values()), max(vals.values())
532                if lo <= 0 or hi / lo < 100:
533                    continue
...
541            kept += len(vals)
```
`dropped` is only ever incremented by the difference the per-name (`known`) filter removes
(line 522). When a scale then fails the 4-row floor (523-524) or the numeric magnitude-span floor
(532-533), the `continue` discards the remaining `vals` rows without ever adding `len(vals)` to
`dropped`, and `kept` is never reached for that scale either (the increment at 541 sits after both
continues). Those rows vanish from both counters.

Reproduced (scratch script `test_refine.py`): a synthetic scale with 10 rows, 4 of which are in
the catalogued ("known") set but clustered within one order of magnitude (so the numeric-span
floor at line 532 rejects the whole scale after the name filter has already run):
```
before: 10
kept: 0 dropped: 6 kept+dropped: 6
```
4 of the 10 original rows are unaccounted for in either printed total.

failure: `main()`'s `--refine` branch prints `rows kept: X` and `dropped: Y` as the reconciliation
of `rows before refine: Z` (X+Y should equal Z). The comment immediately above the `kept +=`
line (534-540) explicitly frames this as the property the prior fix (order 78f2bebed995) restored
-- "kept + dropped stayed arithmetically equal to the pre-refine total either way, which is what
let the discrepancy hide behind two numbers that looked reconciled" -- but that fix corrected only
`kept`'s definition; it left `dropped` uncredited for rows a scale-level (rather than per-name)
rejection removes. The written `data/ROSETTA.json` (`out`) itself is correct -- rejected scales are
correctly absent from it -- so this is a diagnostic/reporting miscount, not data corruption, but it
is exactly the "looks reconciled and is not" shape the neighbouring comment is about, on the
module whose whole subject is measuring where the Assay's own honesty comes from.

remedy: credit the rows a scale loses to the 4-row floor or magnitude-span floor into `dropped`
too (e.g. `dropped += len(vals)` immediately before each of the two `continue`s), so `kept +
dropped == sum(len(sc["values"]) for scales in rosetta.values())` always holds.

### Known (already open orders)

- none of `state/workorders.json`'s open orders name rosetta.py.

### Checked and clean

- `numeric_rows`'s row-scoped parsing (row split on `|-`, first-number-after-name rule, the
  1000x-median outlier filter), `ordinal_rows`'s original-text offset matching, `stand_rows`'s
  nearest-preceding-link attribution and `STAND_MIN_PARAMS` floor, `assays_by_host`'s bare-key
  handling (order 52a73082c56b) and collision reporting, `check()`'s per-host scoping and
  `rho is None` sort-last handling, and `main()`'s `--mine` floor/force/atomic-write logic
  (order 6447bcc2f18c) all read correctly against their documented histories.

## src/cascade_bridge.py

### Known (already open orders): id -- still accurate?

- 9fb8a6b10c1f (CASCADE_BRIDGE_HAS_NO_REACHABLE_MODEL) -- still accurate. The header comment
  (lines 49-69) is explicitly dated "RE-MEASURED 2026-09-08, and unchanged since the order was
  filed"; the remedy (re-pointing `<CASCADE_HOME>/config.json`'s local roster) still lives outside
  this repository and has not been applied. No change needed to the order.

### Checked and clean (no new defect found after a full top-to-bottom read)

- The classifier vocabulary (`_DEAD_CODES`/`_DEAD_WORDS`, `_TRANSIENT_WORDS`/`_TRANSIENT_CODES`,
  `_PERMANENT_WORDS`/`_PERMANENT_CODES`, `_CLIENT_REJECTION`/`_WAF_COMPANION_WORDS`,
  `_SIZE_REFUSAL`) is checked in the order the functions apply it
  (`local_transport` -> `client_rejection` -> `permanent_refusal` -> `named_transient`), and the
  ordering matches every docstring's claim about precedence.
- `dead_forever()`'s TTL-and-mtime memo (order 90bd64fe676d), `_land_claim`-style CAS in
  `record_unrecognised` (order 853aa8990132) with its jittered 12-attempt backoff, and
  `engine()`/`thread_engine()`'s double-checked-locking publication order (order af50bab5a369)
  all read correctly.
- `_ask_call`'s invariant that `pinned` is non-None from line 1666 onward holds for every path
  that reaches it (pin resolution failure and the local-bucket refusal both `return None` before
  that point; the widen fallback and claim loop are the only ways to reach it with `pinned` set).
- Confirmed `_extract_json`'s `raw_decode`-based fallback (order 5e5d86e36687), the `isinstance
  dict` guards on `got` in both `ask()`'s metric row and `selftest()` (the two sites the file's own
  comments say were fixed together), and `_size_refusal_permanent`'s arithmetic-over-wording
  requirement (order af47010df391).

### QUESTION -- a `named_transient` failure with no provider-stated retry-after now benches nothing

`elif pinned and (exhausted or named_transient(err)): _wait = None if exhausted else
retry_after_seconds(err); if _wait: _bury(pinned.bucket, _wait)` (lines 1870-1895). Since order
2239a87c57f5 made the bench timed-and-provider-stated, an ordinary transient refusal that names no
parseable retry-after (`retry_after_seconds` returns `None` for a bare "Rate limit exceeded" with
no number in it) is not benched at all -- not even the old flat `FIRST_BENCH`/exponential-strike
bench `_bury(bucket)` (no `seconds`) still used for the deadline and unparseable-reply paths.
Reading A: this is intentional and sufficient, because `_pace()` already throttles re-entry to the
bucket's own declared rpm, so no additional bench is needed for an un-stated throttle. Reading B:
this is a gap the order's remedy did not cover -- a bucket that fails with generic throttle wording
and no number is now claimable again on the very next round with no cooldown of any kind, which is
close to the original problem the pacing mechanism (and `_bury`'s graded-not-flat redesign) was
built to prevent. This needs an owner ruling on whether a default short bench should still apply
when `named_transient(err)` is true but `retry_after_seconds(err)` is `None`.

## src/genre.py

### Known (already open orders): id -- still accurate?

- f646c1c5f1d0 (GENRE_DEAD_DISJUNCTS_AFTER_UNCAPPING) -- still accurate as recorded. The mechanical
  half (no `not ranked` disjunct at line 227-233, no `or 1` at line 240-243, `genres_with_signal`
  added beside `genres_scored` at lines 237-238 and 264-267) is confirmed present in the current
  file exactly as the order's own re-route note describes. The owner question (whether the
  invariant `genres_scored` field should be dropped, renamed, or kept as a tripwire) is still open
  and this run does not rule on it, per the order's own instruction not to re-file it.

### Checked and clean

- `classify_text`'s uncapped `most_common(None)` and `classify_source`'s refusal of a numeric
  `cap` (both order bc0b85ea353b) are present and correct; `main()`'s low-confidence list and
  `_cut()` display truncation (order 3363994a27b1, display-only, `GENRES.json` unaffected) are
  correct; `main()`'s atomic, gated `write_json` call (verdict checked, rc set on denial) is
  correct.

## src/catalogue_codex.py

### Checked and clean

- `parse_codex()`'s manifest-count cross-check (order f1d5165b188b), the (type, name) pair keying
  that replaced name-only `seen` (order f4f3c1d15915), `load_register_index()`'s multi-item index
  and the disagreement-vs-agreement description handling (order 096f6efc33d2), the exact-match-
  before-substring section binding with ambiguous-match refusal (order 5da00dda2c8e), the
  compare-and-swap roll update (order f818a77293fc) and the write-verdict-reaches-exit-code fix
  (order 0e8ef2e30f2b) are all present and correct against the live file. No new defect found.

### Known (already open orders)

- none of `state/workorders.json`'s open orders name catalogue_codex.py.

## src/runguard.py

### Checked and clean

- The digest-before-read ordering in `claim()`/`beat()`/`release()`, the compare-and-swap in
  `_land_claim` (order fede605db64f's sibling fix, via `silence.replace_if_unchanged`), the
  ownership checks in `beat()`/`release()` (the m27 fix this whole module exists for), the
  `holder_is_live`/`guard_fault` PID-and-start-time corroboration (order 99d752c5632f) and the
  announced (not silent) fail-open on a corrupt guard in `claim()` (order 70f66fbd98aa) all read
  correctly against their documented histories. No new defect found.

### Known (already open orders)

- none of `state/workorders.json`'s open orders name runguard.py.

## src/deprecated/catalogue_local.py

### Checked and clean

- The module-level refusal (`raise SystemExit(_REFUSAL)` at line 94, with the `-h`/`--help`
  exemption at lines 91-93) genuinely precedes every other statement in the file, so `main()`,
  `catalogue_source()`, `call()` and the bare `open(..., "w")` writes the file's own header
  describes as deliberately unrepaired are unreachable under any invocation, including on import
  by another module. No new defect found; the file behaves exactly as its own extensive header
  describes.

### Known (already open orders)

- none of `state/workorders.json`'s open orders name catalogue_local.py.

## src/tempus.py

### Known (already open orders): id -- still accurate?

- 7099a092abd3 (BATTERY_IS_THE_ONLY_CALLER_OF_THIRTEEN_PUBLIC_FUNCTIONS) -- still accurate for the
  four tempus.py symbols it names (`retrocausality_beta`, `contemporaneous`, `is_present_at`,
  `prescience_horizon_bits`): the module's own comment at lines 138-145 independently confirms
  these are read only by the battery/pipeline test harnesses, consistent with the order's
  "0 production" finding. No action taken, per the order's own note that this needs an owner
  ruling rather than a mechanical fix.

### Checked and clean

- `apparent_lag_years`'s single return shape (order e3a52d3f20b5), `DEGENERATE_TIME`'s retained-
  as-reference-data status (order 1a9c237dda4d) and the still-real "loop_report duplicates the
  table in prose" drift it names (correctly left unrepaired, a wiring decision not a marker),
  `rung_description_length`/`band_resolution`'s BAND_EDGES-derived math, and
  `prescience_horizon_bits`/`retrocausality_beta`'s positive-lead-time guard all check out
  arithmetically. No new defect found.

## Summary

- 2 new DEFECTs (both MAJOR): silence.py `_handler_is_observed` evasion; rosetta.py `refine()`
  kept/dropped reconciliation loss.
- 1 new QUESTION: cascade_bridge.py's un-benched generic transient failure.
- 3 "Known" order confirmations (7099a092abd3 x2 modules, 9fb8a6b10c1f, f646c1c5f1d0), all still
  accurate, none re-filed.
