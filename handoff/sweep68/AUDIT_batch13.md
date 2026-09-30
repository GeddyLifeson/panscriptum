# sweep68 batch13 audit (run68)

## Scope
Every line read with the Read tool, in chunks, sequentially. Read-only; reproductions are scratch scripts under
`%TEMP%/aud68_13` (a1, b1-b6) with `health.*_PATH`, `silence.replace_retry`, `genre.HERE`, `tiers.HERE`,
`module_index.OUT` redirected to a temp dir. No project file touched, no `main()` run against the live tree.

| module | lines | notes |
|---|---|---|
| assay.py | 1956 | 3 chunks |
| health.py | 1399 | 3 chunks |
| liveness.py | 1127 | 3 chunks |
| estate.py | 723 | 2 chunks |
| tiers.py | 556 | whole |
| render.py | 441 | whole |
| genre.py | 386 | whole |
| propagation.py | 254 | whole |
| module_index.py | 192 | whole |

## Prior-audit cross-check (handoff/sweep67)
- **67/13 F2, `interval_from_hands` hang on 1e17: FIXED.** assay.py:1885-1889 jumps to the largest 0.01 step below the worst
  deviation and takes `_max_dev` when +0.01 is absorbed. Ran `{"AVAR":0,"QUILL":0,"MOTH":1e17}` -> interval 6.67e16, instant;
  `MOTH=3000` -> 2000.0, `covers_all_signatures` True.
- **67/13 F3, `axis_score(nan)` returned 10.0: FIXED.** assay.py:335 `math.isnan(x)`; `axis_score(nan,"M3","ruin")` -> None.
  (`inf` -> 10.0, arguably right.)
- **67/14 F4 stale citations in liveness.py (:7-9, :469, :778): FIXED.** No `liveness.py:NN` or "57 nets" text remains.
- **67/12 F16 stale citations / frozen count in tiers.py: PARTLY FIXED.** The frozen "13 unaddressed shelves" is gone
  (`main()` counts live) and the cliff paragraph cites by symbol. One `:143` citation remains (see F8).
- **67/12 F1 (allsweep `--help` executing `tiers.main`): FIXED in allsweep** (`check_import` now passes `--help` only to
  modules with a parser, allsweep.py:358-369). tiers.py still has no argparse, which is now harmless.
- **67/12 Q7 (no halt interlock in `tiers.main`, `genre --write`, `render.write_views`): unchanged, OWNER-routed class
  question.** Not re-filed. health.py did gain `_assert_not_halted` (1305-1329) for `--reopen --go`; still correct.
- **67/03 Q3, genre cue stems over-match (`hell`/hello, `ration`/rational): unchanged, still a question.**
- 67/03 genre `genre_field_size` rename and `genres_with_signal`: still as ruled. 67/16 Q3 (render draws one sample node per
  tier): still stands, re-measured below. No prior finding on propagation.py or module_index.py.

## Findings

### F1 (LOW) assay.py:1442 vs :1449 -- `decimal` and the printed Moth Number can disagree by 0.01
`"decimal": round(_dec, 2)` (float rounding) but `moth_number` prints `round(_dec * 100):02d` (half-even on the product).
Two published spellings of one number, rounded by two rules. Repro (b4.py, single-axis assays, score 0.00-10.00 step 0.01,
11 anchors x 3 axes = 33,033 calls): **283 cases (0.86%) disagree**, e.g. `assay("M0",{"ruin":0.25},worksheet="w")` ->
`decimal 0.03` but `"𝔄 M0.02 ± 0.22"`; `ruin=0.05` -> 0.01 vs `M0.00`; `ruin=2.15` -> 0.21 vs `M0.22`.
Scan of the seven live `*ASSAYS*.json` files: 0 of 244 rows mismatch, so latent today (multi-axis composites rarely land on a
tie). Fix: `_pct = round(round(_dec, 2) * 100)` and print that. Severity LOW (second decimal, which the module itself calls
finer than the evidence), but it is the same number stated two ways.

### F2 (MEDIUM) tiers.py:283-309, 398-405, 522 -- a parseable-but-empty GROUNDINGS.json counts as "readable" and is published
`_load_groundings()` returns `(doc, True)` for anything `json.load` accepts. The refusal in `main()` (`REFUSING TO CHART`) and
the re-check at the write both key on that flag only. Repro (b1.py, temp tree): body `{}` -> `({}, True)`; `chart()` then
returns for every shelf `hyperverse: 5, hyperverse_type: 'ungrounded'`, `groundings_readable: True`. `[]` also reads True and
then dies in `hyperverse_of` with `AttributeError` (loud, but the guard let it through). Scenario: `grounding.py:338-350`
writes whatever `out` holds with no shrink floor (it would write `{}` if its inputs were unreadable), `tiers.main` then sees
"readable", passes the containment gate, and `silence.write_json`s an all-`ungrounded` TIERS.json over a good one; the docstring
names exactly this outcome ("a guess wearing the shape of a measurement") and address_space reads TIERS.json at import.
Fix: `_load_groundings` should return ok only for a non-empty dict, and `main()` should compare the count of grounded sources
with the file it is about to replace (the `completeness.land()` SHRINK_FLOOR pattern the docstring cites).
Not reproduced against the live tree (no write attempted).

### F3 (LOW) genre.py:327-329, 361-381 -- `--write` publishes a smaller GENRES.json with rc 0 and no count check
`PL.records()` silently skips an unreadable record (pipeline.py:797-800, note only) and any record with empty `entries`;
`main()` classifies what came back and writes it, printing only "sources classified: N". Repro (b1.py, `records()` returning
nothing): GENRES.json becomes `{}`, "wrote ..." and rc 0. Today's shape of the same fault, measured (a1.py): 216 record files,
6 with zero entries (HAWX, Heaven's Lost Property, Lost Mines of Phandelver, major live-action Disney films, the Witch Tradition,
Twilight Imperium), 210 rows in GENRES.json; those 6 are absent rather than `unclassified`. `profile.build_all` and
`navtree` turn an absent source into `classical`/`unclassified` silently, i.e. the same answer a genuine zero-signal source
gets. Harmless for the 6 (no entries, no world), real if a corrupt record is skipped. Fix: name the roll sources not classified
and return non-zero when the set differs from the roll.

### F4 (LOW) propagation.py:105-106, 201-207 -- a misspelt shelf name is reported as "DISCONNECTED (no shared furniture at any remove)"
`shortest()` returns `(inf, [])` both for "no path" and for "name not in the graph"; `--from/--to` prints the first as a finding
about the library. The default survey path already separates them (`?? not in graph`). Repro (b1.py): `--from Marvle --to DC`
-> `Marvle -> DC: DISCONNECTED (no shared furniture at any remove)`, rc 1. Also 19 of the roll's sources are not in the graph
at all (197 nodes), so "not in graph" is a live answer, not just a typo. Fix: test `src in adj` / `dst in adj` in `main()` first
and say which name is unknown.

### F5 (LOW) estate.py:218-229 vs :86-90 -- a zero-byte `.corrupt` copy is graded a fault
The `KEPT_DAMAGED_EXT` comment says a `.corrupt` file "would be a permanently red row that no repair can ever clear ... Sized,
never opened", but the zero-bytes branch exempts only `TRANSIENT_EXT`. health.py preserves a torn `failures.json` as
`.corrupt`, and its own comment names the 0-byte case ("an interrupted flush leaves 0 bytes"). Repro (b1.py):
`inspect("failures.json.corrupt")` at 0 bytes -> `{'error': 'zero bytes'}`; a 0-byte `.applock` -> no error. None exists in the
tree today (both current `.corrupt` files are non-empty). Fix: add `KEPT_DAMAGED_EXT` to the exemption at :226.

### F6 (LOW) health.py:351, 468 -- a second torn ledger overwrites the first `.corrupt`
`silence.replace_retry(path, path + ".corrupt")` is `os.replace`, so the earlier wreck is destroyed by the next one. Repro
(b6.py, temp paths): tear 1 -> `.corrupt` holds tear 1; tear 2 -> `.corrupt` holds only tear 2, and the fresh ledger starts at
`ledger:unreadable: 1` again rather than 2. The code and comments describe the wreck as "the only copy of whatever tore it".
Fix: a unique suffix (`.corrupt.<epoch>`) or refuse when `.corrupt` already exists (estate already recognises the `.corrupt`
extension). Same for the samples file (:468).

### F7 (LOW) module_index.py:156-168 -- a denied replace leaves its temp file behind
On `replace_retry` -> False the function returns 1 without removing `tmp` (render.write_views:432-435 does remove it).
Repro (b6/b1, `replace_retry` stubbed False): rc 1, `handoff/` contains `MODULE_INDEX.md.36160.39880.tmp`. The pid+thread name is
unique per run, so each denied run adds another. Fix: `os.remove(tmp)` on the failure arm.

### F8 (LOW) stale citations and comments (the tree's own rule is "cite by symbol")
- assay.py:1131 `axis_correlation.py:284-292` for `load()`; `load` is at :337 (:284-292 is `_finish`'s return dict).
- assay.py:1573 `anchors.py:186` for the `instrument()` call; it is at anchors.py:231.
- assay.py:1898 `custodes.py:539-551` for the "GUARANTEE being published" text; it is at custodes.py:576.
- assay.py:226 `anchors.py:41`; the table is at :42 (historical wording, one line off).
- health.py:85 `workorders.py:81` for `SELFTEST_SUBJECT`; it is at :85. health.py:94 calls `subject=` "the half proposed to
  escalation.py:248"; escalation.py:346-347 now passes `subject=rec.get("source")`, so "proposed" is out of date.
- tiers.py:507 "`_cut` ... at :143"; it is at :144.

### F9 (LOW, latent, UNVERIFIED for timing) two hot spots that cost nothing today
- health.py:1053-1054 `check_state` calls `P.records()` once per failed-synthesis source. `records()` reads every record file
  (302 MB under data/records) before `next(...)` filters. `state.failed.synthesis` has 0 entries today, so it costs nothing; with
  K entries it reads the corpus K times at the head of every supervisor cycle. Hoist one `P.records()` above the loop.
  (Timing not measured.)
- health.py:163-172 `record()` routes a self-test key's COUNT to the rehearsal ledger but its SAMPLE ring is keyed into the same
  `_SAMPLES` and flushed to `state/failure_samples.json`. Repro (b1.py): a `__drill_rung4__` key with `sample=` lands in
  `_SAMPLES`. No caller passes a sample with a drill key today (live samples file: 257 keys, 0 drill keys), so latent.

## Questions (not asserted as defects)
1. **render.py `write_views` / `main`:** still one sample node per tier (`worlds` holds 1,569; the first world is drawn, giving
   hyperverse 7 children, xenoverse 7, metaverse 7, multiverse 1, universe 0). Also `WS.build_all(limit=1)` in `main`. Is one
   sample per tier the intended product under Hard Rule 0? (Carried from 67/16 Q3, order 5bb12b398783.)
2. **liveness.py `main()`:** the default scan and `--reachability` both `return 0` whatever they find, including "NOT MEASURED"
   and UNDECLARED unreached lines. `drill.py` ratchets the scan count (44 now, ceiling 52), but a script running
   `--reachability` cannot tell measured-clean from not-measured by rc. Deliberate?
3. **liveness.py dead_module:** scan reports 6 modules nothing names: descending_ladder, halo, module_index, pantheon,
   scale_theories, zfighters. module_index.py's header says it is run by hand. Is a hand-run tool meant to sit in
   `EXEMPT_MODULES` (empty) rather than the finding count?
4. **estate.py `terminal()`:** the husk test (`len(body) < 64`) covers `.js` only; a truncated `PANSCRIPTUM_TERMINAL.html` above
   0 bytes passes ("N page(s)"). Intended, given `artifacts()` catches zero-byte files?
5. **tiers/genre/render halt interlock:** the standing owner-routed class question (67/12 Q7). No new fact.

## Cleared (read closely, found correct)
- **assay.py:** `axis_score` order (band, axis, then x), top-rung 9.9/0.0 branch, NaN refusal; `_check_scores/_weights/_readings/
  _hand_readings` (bool, non-finite, unknown key with did-you-mean, all-zero table); `_check_constants` (monotonic sigmas,
  ceiling, BAND_EDGES symmetry and increase, ATTESTATION_FLOOR set/order, INSTRUMENT_WINDOWS/FACULTY_READS/partition);
  `_interval` (variance, covariance over every applicable pair, `max(...,0)`); `assay` wsum refusal, nil/unestimable/
  inapplicable partition, clamp at both ends; `calibration_report` sweep touches nothing shared, `holds` True; `instrument`
  sentinel handling; `interval_from_hands` widening and the recorded-before-widening fields. Import-time `_check_constants()`.
- **health.py:** `_flush_ledger`/`_flush_samples` CAS loops (digest before read, re-take after preserve, settle only on
  landing, keep counts on refusal); `flush()` re-entry guard; `_read_ledger` wrong-shape refusal; `check_caches` (uncapped,
  stat-only, exemptions fail closed, small-floor as a note); `check_api_paths` per-domain family and shelved/quarantined
  handling; `reopen_stranded` None-vs-[] contract, text-compare plus digest CAS, uncapped listing; `preflight` stamp
  verdict; `_assert_not_halted` fail-closed import; `main` exit codes.
- **liveness.py:** receiver-aware `_credit_attrs` with per-scope aliases, `scoped` MRO by name, dead class/module limbs,
  phantom `defined` set. Measured that dropping `EXEMPT_PREFIXES` adds only `pipeline.phase_history/phase_shelve`, which are
  reached by `globals()["phase_"+name]` (pipeline.py:3719), so the prefix exemption hides nothing real. `_function_line_ranges`
  qualified/ambiguous keys, `stale_declarations`, `reachability` fail-closed errors and window flags.
- **estate.py:** `inspect` stat-retry, `.jsonl` per-line parse, `_effective_ext`, root discovery, charter table parse and the
  four errata (live run: 3 rung errata + the M0-M2 row emit, 33 unassigned sources printed in full), `written`/`terminal`/
  `external` split handlers.
- **tiers.py:** CUTS raised not asserted, `_components`, `xenoverse_grounding` per-xenoverse vote with recorded dissent,
  containment scan gate, write gated, rc from the landing verdict, uncut evidence lists.
- **render.py:** `children_of` refuses partial coordinates, whole names, atomic per-file write with pid+thread temp and verdict.
- **genre.py:** full-field denominator, `cap` refused, zero-signal branch, atomic gated write. **propagation.py:** Dijkstra,
  `observed_mark` (unreachable trailing `return 0` confirmed), keep-shortest edge merge, rc verdicts. **module_index.py:**
  recursive `_modules`, stale/duplicate verdicts reach rc 1 with the page still written.

Recorded via `sweep_plan.record('run68', ['assay.py','health.py','liveness.py','estate.py','tiers.py','render.py','genre.py','propagation.py','module_index.py'], batch=13)` after this file was written.
