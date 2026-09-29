# Sweep 67 (run67) - AUDIT batch 14

## Scope

Read in full, sequentially, with the Read tool (no skimming), plus CLAUDE.md first:

| module | lines |
|---|---|
| src/module_index.py | 192 |
| src/citecheck.py | 458 |
| src/cosmology_graph.py | 261 |
| src/recover_folder_records.py | 380 |
| src/axis_correlation.py | 538 |
| src/manifest_builder.py | 701 |
| src/generate.py | 1511 (3 chunks) |
| src/liveness.py | 1127 (3 chunks) |
| src/binding_health.py | 1765 (4 chunks) |

Strictly read-only against the project. Nothing under src/, data/, state/, output/, prompts/,
reference/ or the root was edited. No pipeline phase, generate.py, publish.py, mutate.py,
verify_math.py or drill.py was run. Two read-only helper runs: `citecheck.py` (reports 0 findings)
and one scratch repro under %TEMP%\b14 (monkeypatched, writes nothing). No subagents.

## Prior-audit cross-check

Grepped handoff/sweep66/AUDIT_batch*.md for every module name (batches 04, 06, 08, 10, 11, 12,
13, 14, 16 mention them). All earlier passes filed 0 findings against these modules.

- liveness.py question (sweep63-66, "DECLARED_UNREACHABLE name matching no def excuses nothing
  silently"): NO LONGER STANDS. `stale_declarations()` plus the `stale_declarations` key in
  `reachability()` now name it and `main --reachability` prints it (order 6b59a5d4302a item 5).
- binding_health.py order 30854f11f322 (containment-only CONFIRMED): remedy now in code
  (`confirmed=` pairs from HOST_RULINGS.json, `tight` ratio). Not re-derived; behaves as documented.
- axis_correlation.py sweep66 batch12 item (no floor guard on `write()`): CLOSED, `SHRINK_FLOOR`
  and `ShrinkRefused` present and traced (fail-closed on unreadable prior, bool excluded).
- generate.py `_covered("")` returning True (order 28f335ecefd3 item 2): CLOSED, now returns False.
- manifest_builder.py provisional-code report (sweep64): still correct, prints `volume_code`.
- manifest_builder.py `load_record` and `pack_feats` clearances: re-traced, still hold.
- recover_folder_records.py `mapped is None` vs `[]`, `short_sources`, CAS roll update: re-traced, hold.
- cosmology_graph.py weight formula and uncapped write: re-traced, hold.
- citecheck.py, module_index.py: no prior defect; no change found.

## Findings

### F1. `run()` files an exception on OUR side as a host fault and quarantines the host
`src/binding_health.py:1479-1483` then `:1485-1511`. Severity: MEDIUM (reproduced).

`canary()` raising (a bug, `ImportError` from `from rapidfuzz import fuzz` in `binding_verdict`,
an unguarded `EP.detect`/`EP.raw_url` in `_probe_reachable` at :916-919, a corrupt endpoint cache)
is caught and stored as `{"healthy": False, "reason": "canary raised X"}`. `healthy is False` is
exactly the value that drives `quarantine()` at :1510, which stops mining that host and raises a
SUPERVISOR escalation. This is the false-quarantine the module documents at length ("NOT ASKED IS
NOT ANSWERED", three-valued verdict, `_probe_absent`/`_probe_reachable` exception arms return
None). The catch-all is the one exit that still answers unknown with False.

Repro (`%TEMP%\b14\repro_bh.py`, patches `canary` to raise ImportError, `quarantine` to record):
```
rows: [('a.fandom.com', False, True)]
quarantine() calls: [('a.fandom.com', 'canary raised ImportError')]
```
A missing rapidfuzz would therefore quarantine every host whose titles failed to resolve
(the only ones that reach `binding_verdict`), in one sweep.
Fix: in the `except` at :1479 store `"healthy": None` with the reason (and `silence.note`), so it
is neither quarantined nor released; the row still reports the fault.

### F2. Feats jobs are built from the full record, so struck and stale entries reach prose through the Feats chapter
`src/manifest_builder.py:401` (versus the filter at :283-284). Severity: MEDIUM.

`build_jobs_for_source` filters `excluded` and `stale_since` entries out of `entries` (order
c9666b0bd8d9, "a struck entry does not reach prose"), but line 401 calls
`feats_index.feats_for_source(source_name, record, ...)` with the unfiltered `record`.
`feats_for_source` (feats_index.py:407-414) builds `entries_by_norm` from
`record["entries"]` with no `excluded`/`stale_since` test (grep of feats_index.py for
`excluded|stale_since` finds nothing). Any feat mined for an entity whose catalogue entry was
struck (the Logan Paul / Prime World Equipment case the comment names) or is a stale old-wording
row is packed into a `feats` job and written up, and it carries `r["entry"]` (the struck entry's
description and magnitude) into the block. The strike stops at the catalogue chapters and
continues through the Feats chapter.
Fix: `feats_index.feats_for_source(source_name, dict(record, entries=entries), binding=_binding)`.
(Not run: needs the feats index; this is from reading both call sites.)

### F3. `--only` with a name that matches nothing (or only some) writes a short or empty manifest, silently
`src/manifest_builder.py:511-513`, `:591-603`. Severity: LOW-MEDIUM.

`--only "One Piece,Marvle"` keeps whatever matches, drops the misspelt name without a word, and
the result is written to `paths.manifest` (the FULL manifest path; only `--pilot` diverts to
`pilot_manifest`). With no match it lands `{"jobs": []}` over the standing manifest and prints
"Wrote 0 jobs from 0 sources". `generate.py` then runs on that (a manifest with no jobs is
"0 pending", rc 0), and the previous full job list is gone until the next full build. Unmatched
names are not reported, which is this project's failure shape (a smaller universe with the same
form). Fix: after computing `wanted`, name every entry of `wanted` not found in `build_pool` and
return 1 if any (or all) are missing; consider not overwriting the full manifest path from `--only`.

### F4. Stale citations and stale comments that contradict the code
Severity: LOW (documentation only; `citecheck` cannot see these by design, since the cited lines
are non-blank, non-bracket).

- `src/liveness.py:7-9`: "profile.py's round trip -- FIXED, now at `profile.py:196-208`". Those
  lines are `decode()`'s IndexError-refusal comment; the round trip is at profile.py ~:324-331.
- `src/liveness.py:469`: "named at liveness.py:10" for `coverage._p()`; it is named at line 12
  (line 10 is the `cleanup.py` bullet).
- `src/liveness.py:778`: "`drill.py`'s 57 nets". CLAUDE.md records that this figure was removed
  from doctrine on 2026-09-08 for being a stale count that gets reasoned from (order 864a626a258e).
- `src/binding_health.py:1456`: "`is_quarantined`'s ... callers (below, at :1095 and :1100)". The
  calls are at :1512 and :1517 (:1095-1100 is inside `binding_verdict`'s comments).
- `src/binding_health.py:1490`: "the `landed` key `quarantine()` sets at :392". It is set at :493.
- `src/generate.py:1461-1463`: "can be made good by the next one five chapters later". The loop
  now lands the catalog after every chapter (:1451-1459), so there is no "five chapters later".
Fix: replace each with a symbol name (`_land_catalog`, `quarantine`, `decode`) per the tree's own
"cited by symbol, not by line" ruling.

### F5. `--host` names that are not bound hosts are dropped without a word when others match
`src/binding_health.py:1414-1415`. Severity: LOW.
`hosts = [h for h in hosts if h in set(only)]` silently discards a mistyped host as long as at
least one other `--host` matches (the all-miss case is caught by BINDING_FILTER_MATCHED_NOTHING at
:1549). The operator investigating a binding believes it was re-probed and merged. Also
`set(only)` is rebuilt per element (harmless). Fix: print/escalate `set(only) - set(hosts)`.

### F6. Crash paths in manifest_builder on roll rows with missing fields
`src/manifest_builder.py:494-495` and `:670`. Severity: LOW.
`r.get("entry_count", 0) > 0` raises TypeError if a roll row carries `entry_count: null` (other
readers in this tree, e.g. recover_folder_records.py:109, use `== 0`, which treats None
differently, so the two disagree on what an empty source is); `sorted(unassigned, key=lambda r:
r["category"])` raises KeyError where `provisional_spine` and the rest use
`.get("category", "Uncategorized")`. Loud, not silent, but it aborts the whole build after the
manifest write, so the manifest lands and the report and rc do not. Fix: `.get(..., 0) or 0` and
`.get("category", "Uncategorized")`.

## Questions (possibly deliberate)

1. generate.py `main()` returns 0 (falls off the end) when every pending job failed, e.g. Ollama
   unreachable: each job files a row in failures.json through a CAS write and the run ends
   "0 generated, N failed" with rc 0. Only a failed catalog/failures landing returns 1 (:1495-1501).
   Is rc 0 the intended reading for the keeper when the whole pass produced nothing? (An
   unreachable model could fail fast and loudly rather than file N refusals.)
2. generate.py returns 0 when the prose gate is closed (:1075-1080), while a missing manifest,
   misconfigured floor and unreadable COVERAGE.json return 1. Presumably deliberate (closed gate is
   the safe idle state); worth stating in the docstring next to the other exits.
3. axis_correlation.py `observations()`: the same entity could appear in more than one of
   `SOURCES` (e.g. a hand-built assay and its later automated `ASSAYS.json` row, or PANTHEON and
   Z_FIGHTERS). There is no dedupe by entity, so a duplicate counts twice toward n and r and toward
   the SHRINK_FLOOR base. Is disjointness of the sources guaranteed elsewhere?
4. manifest_builder.py volume numbering (`series_members`, :554-567) is drawn from populated,
   non-excluded sources. A source flipping `entry_count` 0 to >0, or being put out-of-scope, shifts
   the `.N` volume of every alphabetically later member of its Series and so their job ids,
   catalog keys and raw filenames (generate.py keys on the address). Deliberate ("deterministic by
   sorted name"), but the address is stable only as long as the roll's populated set is; is a
   stored, frozen volume number wanted?
5. binding_health.py `known_present_titles`/`known_present_title` (:1333, :1367) draw canary
   titles from every entry including struck (`excluded`) ones. A struck row that is wiki navigation
   may not resolve as a page and can sit among the eight spread candidates. Low impact (one hit ends
   the probe); flagging because it is the same blind spot as F2.
6. recover_folder_records.py :162-189 iterates the mapping's `register_source` entries as written;
   a mapping listing the same register source twice would transcribe its items twice into one
   record (duplicate entries, one provenance). No such row is claimed today; not checked against
   the live FOLDER_SOURCE_MAP.json (read-only run, data not opened).

## Cleared (read closely, found correct)

- module_index.py: recursive `_modules()` keyed like allsweep; stale and duplicate-group verdicts
  accumulate and reach rc 1 while the page is still written; tmp+`replace_retry` with verdict
  checked. Every name in GROUPS exists in src/ (checked), so no stale-name rc today. (Trivia: the
  `open(path)` in `first_line` is not closed explicitly; CPython closes it.)
- citecheck.py: the use/mention rules narrow and after-the-phrase only; `_in_tree_lead`; line 0 and
  PAST_EOF handling; unreadable is noted, not reported clean; `citations_in_text` and
  `stale_citations` share one resolver. Live run: 0 findings.
- cosmology_graph.py: formula `1/log(n+1.5)`, x0.15 above 12; whole `shared_sample` kept; every pair
  written; write verdict gated; display cuts marked.
- recover_folder_records.py: `is None` vs empty mapping; shortfall recorded before the early exit;
  `already` guard fails closed on unreadable; a denied write leaves the roll untouched; roll updated
  only through `roll.update_rows`; denied verdict reaches the exit code.
- axis_correlation.py: `_scores_of` bool exclusion in both shapes; `_pearson` MIN_N and constant
  column; `rho` fallback (ruled value, announced once); `widening` sentinel doc; shrink verdict
  (missing prior proceeds, unreadable refuses); write verdict gated.
- manifest_builder.py: `load_record` equality-first, prefix-anchored inexact arm with 12-letter
  floor; `pack_feats` flush-before-exceed pagination with every slice emitted; `chunk` ranges;
  numbering over `numbering_pool` not `build_pool`; both writes gated and folded into rc.
- generate.py: `strip_think` three shapes; `_land_catalog`/`_land_failures` CAS (digest before read,
  refuse unparseable, `own` cleared only on landing); `_covered` and `_deed_traced`; the fixed-tail
  fill leaves beings with a Magnitude band to the gate; `meta_rewrite` never deletes a sentence it
  could not clean; P8 gate fails closed on ImportError; failures popped only after the catalog row
  exists.
- liveness.py: receiver-aware DEAD pass with per-scope aliases; class and module limbs (self
  reference excluded); PHANTOM `defined` set including builtins module not `dir(__builtins__)`;
  `reachability()` subprocess isolation and error-not-empty returns; `_function_line_ranges`
  qualified keys with ambiguous alias as None.
- binding_health.py: `_read_quarantine` unreadable != empty; `quarantine`/`release` digest-before-
  read CAS and NOT RELEASED escalation; `_spread` even sampling; three-valued `verdict()` truth
  table; `_probe_absent` block-page None; `binding_verdict` containment/tight/ruling logic; the
  whole-estate empty-map refusal and the partial-pass merge under CAS; `checked`/`failed` over the
  same population.
