# sweep67 (run67) AUDIT batch 07

## Scope

Nine modules, every line read in sequential chunks with the Read tool. Nothing under src/, data/,
state/, output/, prompts/ or reference/ was edited. No daemon, pipeline phase, generate, publish,
mutate, verify_math or drill was run. Standalone reproductions live under %TEMP%/s67b7 and only
read the corpus (one ran `weave_index.build()` and `dashboard._watch()` read-only).

| module | lines (read) | sweep66 lines |
|---|---|---|
| standards.py | 2577 | 2487 |
| sweep_plan.py | 1150 | 1150 |
| weave_index.py | 825 | 731 |
| address_space.py | 651 | 679 |
| zfighters.py | 536 | 536 |
| catalogue_models.py | 409 | 364 |
| style_audit.py | 342 | 342 |
| repass_bands.py | 244 | 214 |
| chord_field.py | 210 | 210 |

Five of the nine changed since sweep66 (halt interlocks in weave_index/repass_bands,
staleness/escalation in weave_index, secrets merge + `enabled:false` in catalogue_models,
citation_card deletion in address_space, new job-stall witness and more in standards).

## Prior-audit cross-check (handoff/sweep66)

sweep66 batches 02/03/04/06/07/08/10/13 all reported zero findings on these modules. Status:

- b07 standards.py, "every standard could read its own input" / green-by-absence defence:
  the ~30 `_dropped` handlers still hold. My findings F1 and F2 are the two standards the
  defence does not reach (the input exists but is structurally empty), so they are not
  regressions of what b07 cleared.
- b07 open question `d03706b5eaf0` (a job that never produced a log): still stands as a
  question. Behaviour today: an unstattable log is appended to `unmeasurable` at
  standards.py:1794 BEFORE the alive test, so it turns "every running job is advancing" red
  even for a job that is not running. See Q6.
- b07 open question `d9328fe1ee38` (deliberately slow job): now answered in code
  (`output_age_min`, `job_stall_verdict`, `lognames.PRODUCT`, standards.py:461-520). Reviewed,
  correct: the second witness only narrows a positive. Closed as far as this file goes.
- b03 weave_index `_records_sig` per-file/dir fail-closed split: still correct. F5 below is the
  parse-failure twin in `load_records`, one function down, which b03 did not cover.
- b03 repass_bands write-then-gate-on-`write_record`, `touched`/`denied`: still correct, and the
  new halt interlock (`_assert_not_halted`, 48-72) is fail-closed on the import.
- b04 catalogue_models four-way outcome: still correct. New code since (secrets merge,
  `wanted()` skipping `enabled:false`) reviewed, see Cleared.
- b06 chord_field: unchanged, still clean.
- b08 sweep_plan: unchanged file, and b08 cleared freeze/CAS/shard logic. That still holds; F6
  and F7 are in the CLI dispatch and in one exception path b08 did not exercise.
  `coverage_map()` is still dead-but-marked (order d411f780d347), fine.
- b10 zfighters: unchanged, still clean (see Q5 for a content question only).
- b13 address_space: `citation_card()` deletion (order 7354d54f0e27) confirmed, no dangling
  reference in src/. style_audit unchanged; `TURN_ENDING` `\Z` anchor still correct.

## Findings

### F1 (HIGH) `every module imports` cannot fail
standards.py:1184-1189 reads `w.get("broken")`; `dashboard._watch()` (dashboard.py:347) creates
`"broken": []` and nothing in src/ ever assigns to it. The import scan lives in
`overwatch.structure()` (overwatch.py:470) under the different key `broken_modules`, and that is
not carried into `state["watch"]` either. Evidence: `dashboard._watch()` on the live tree returns
`{'open': 25, 'high': 10, ..., 'broken': 0}` and a grep for any writer of `["broken"]` over src/
(excluding drill/verify_math) finds none; no drill or battery row mentions the standard.
`0 <= MAX_BROKEN_MODULES (0)` is therefore true forever: a HIGH standard whose stated purpose is
"a module that will not import is one nobody knows is broken" is a tautology. Fix: have
`_watch()` (or standards.py) source the list from `allsweep` / OVERWATCH `broken_modules`, and
report UNMEASURED (holds False) when that source is absent.

### F2 (MEDIUM) `phases implemented` is green by absence
standards.py:1195-1202. `ph = lib.get("phases") or []`; when `dashboard.library()` fails to
import `pipeline` it only notes `dashboard.py:library-phases` (dashboard.py:329-332) and leaves the
key out, so `missing == []`, `0 <= 0`, observed `0/0`, floor `at least 0`, MET. An import failure
of pipeline.py is exactly the fault this standard names, and it reads as the all-clear. The
sibling library standards (`coverage`, `sources`) were fixed to emit an UNMEASURED breach; this
one was missed. Fix: `if not ph:` emit holds False with an UNMEASURED reading. (Also
`p["built"]` at :1196 raises KeyError on a malformed row and takes check() down rather than
dropping one standard.)

### F3 (MEDIUM) weave_index.load_records caches and serves a partial corpus after an unreadable record
weave_index.py:350-359. A record file that fails to open/parse (Norton lock, AV, transient
PermissionError during the atomic replace on Windows) is noted and skipped with `continue`, then
`_REC_CACHE.update({"sig": sig, "out": out})` stores the short list under a VALID signature (the
stat succeeded, so `sig` is not None). Consequences: `designations()` is derived from the partial
list and cached; `build()` returns the short population with `excluded` empty; `main --write`
(and `overnight.weave_index_cycle`) then writes a short ENTITY_INDEX.json and
WEAVE_CANDIDATES.json over the complete pair, which weave.py / cosmology_graph.py /
thread_integrity.py read as the whole entity population. This is the same shape the file already
hardened at stat level (f70e87058f66, 5f1dc97d5216) and left open at parse level.
Repro (%TEMP%/s67b7/wi.py): temp records dir with 2 valid records + 1 torn one ->
`records loaded: 2 of 3 files; entries 4 excluded {}`, cache sig set to a clean `(3, mtime)`.
Fix: count skipped files, do not cache (`sig=None`) when any was skipped, print the count in
`main()`'s report, and make `--write` refuse (return 1) when the count is non-zero.
Same silent-skip shape sits in `pipeline.records()` (pipeline.py:756-767) which repass_bands
consumes (see Q7).

### F4 (MEDIUM) sweep_plan `--batches N --check-briefs FILE` silently runs the plan and exits 0
sweep_plan.py:1032 and :1090. The branches are `if a.batches: ... elif a.check_briefs: ...`, but
the option's own help (:1022-1024) and check_briefs' docstring describe it as "diff FILE against
--batches N". Passing both takes the first branch, prints the plan JSON, and returns 0 without
ever comparing. Repro: `sweep_plan.py --batches 16 --check-briefs <briefs.json containing []>`
-> rc 0 and a plan; without `--batches` the same file gives "NOT DISPATCHED AT ALL ... NOT CLEAN"
rc 1. This is a pre-dispatch gate that returns success on the documented invocation. The
`a.batches or 16` at :1092 is dead for the same reason (the branch is only reachable when
`a.batches == 0`). Fix: test `a.check_briefs` before `a.batches`, or reject the combination.

### F5 (MEDIUM) address_space.main() can overwrite the published SHELFMARKS.json with placeholder addresses
address_space.py:585-635. If TIERS.json cannot be read at that moment, `tiers = {}` (line 591),
the run prints a one-line "placeholder, not a charting" note (598-600) and then still computes
`assign_and_mark(desig, {})` for every world and lands the result over data/SHELFMARKS.json.
`fit()` maps every uncharted tier to 0 while the packed address moves. Measured against the live
data: with `{}` all 1016 of 1016 addresses differ from the published ones (and `map_seed`
changes with them); with the real tier rows all 1016 reproduce. The file's own header says the
1,016 addresses and their map seeds are the identity and re-addressing needs an owner ruling. The
import-time twin: `_tier_counts()` (:140-158) falls back to hard-coded 1/6/8/168 widths, and its
own comment says "the run's shelfmarks should be discarded rather than published", yet `main()`
does publish them (no flag records that the fallback fired). tiers.py:549 documents that
address_space holding TIERS.json open is a real denial scenario here. The module is hand-run and
also has no `_assert_not_halted` while writing data/SHELFMARKS.json (Q4). Fix: `return 1` before
the write when `tiers` is empty or the fallback fired.

### F6 (LOW) standards.py `--json`/`--orders`/default paths run check() twice
standards.py:2552-2554 (`work_orders(state)` then `check(state)`) and :2570-2573 (`report(state)`
then `work_orders(state)`). The comments at 2547-2569 say the point of building one state was to
stop every live probe running twice and to stop the two passes disagreeing; but `check()` is
where the probes live (`Get-CimInstance` with a 60 s timeout is uncached, `_UNANS_CACHE` and the
token-flow/fandom memos are TTL only), so each still runs twice and the exit code comes from a
different pass than the table printed. Fix: `rows = check(state)` once; derive report, breaches
and rc from `rows` (`report`/`work_orders` would take rows).

### F7 (LOW) sweep_plan.unknown_claims can raise UnboundLocalError
sweep_plan.py:804. `silence` is imported function-locally (`import silence`) inside `except`
branches at :770 and :781; that makes `silence` a local for the whole function, so the bare
`silence.note(...)` at :804 raises if that name was never bound in this call, i.e. when a shard
is readable in pass 1 and unreadable in pass 2. Repro (%TEMP%/s67b7/sp.py, simulated flaky
`json.load`): `UnboundLocalError: cannot access local variable 'silence'`. It aborts the
`--missing` falsifier after "nothing missing" was printed. Fix: module-level `import silence`
(as every other module does) or import at the top of the function.

### F8 (LOW) standards `shelfmarks are unique` counts addresses, not printed shelfmarks
standards.py:1470-1480. It counts `v["address"]`. The name, the order text ("every citation to
either is ambiguous") and the citation are about the PRINTED `shelfmark`, which
address_space.shelfmark() documents (order be9e9f089d62) as NOT injective: the star field is not
printed, so two addresses can share a name. Today 1016 / 1016 printed shelfmarks are distinct
(checked), so nothing is wrong yet; the standard just cannot see the failure class the
docstring names. Also an empty SHELFMARKS.json reads as MET (0 collisions, 0 rows) and two rows
missing `address` count as a collision. Fix: also count `len(set(v["shelfmark"]))`, and emit
UNMEASURED on an empty file.

## Questions

Q1. standards.py:2019-2020 `except FileNotFoundError` on SHELF_RANKS.json is a
`silence-exempt` pass with no `_dropped` entry ("phase 7 has not run yet"). Is deleting that
file meant to remove `promotions have their spine codes amended` from the count?

Q2. style_audit.py:178-196 still windows OPENING SHAPES and EXACT OPENERS at `top=8` (with a
"N more not shown" remainder). Order 1cb7bd3ad0ce kept ranking and disclosed the remainder; Hard
Rule 0 wording forbids ranking-then-truncating. Same for weave_index.py:750 `TOP_N = 18` (with
the full set in WEAVE_CANDIDATES.json). Accepted display windows, or uncap? (`_cut(len(heavy),
len(heavy), ...)` at style_audit.py:233 is a tautology, always "all shown"; harmless.)

Q3. weave_index.py:170-174 / :195: a learned continuity designation with a non-ASCII head folds
to "" in `continuity_of` and is silently not a designation; names that are wholly non-Latin fold
to an empty key. Live count of the latter is 3 ("???" entries in one source), printed in the
report, so it is disclosed. Intended?

Q4. address_space.py (writes data/SHELFMARKS.json), zfighters.py (data/Z_FIGHTERS.json, read by
pantheon.py) and catalogue_models.py (data/PROVIDER_MODELS.json) are hand-run writers not on
verify_math `_INTERLOCKED`. Does the 2026-09-28 "every hand-run tool that writes the corpus or
the library's output refuses under a halt" ruling reach derived data/ files, or only records
and output/?

Q5. zfighters.py: (a) Tien's `continuity` axis (line 324-325) quotes "Killed along with Tien
when Kid Buu blows up the Earth ..." as [wiki] evidence for Tien, but that sentence is Chiaotzu's
own wiki line (Chiaotzu's presence text, 385-386, uses it correctly), so it is another
character's article cited under Tien. (b) Header says "these fifteen" and line 476 says "the
fourteen"; the roster has 14 hand sheets plus Goku loaded from file. Wording only. I did not
check the [canon] claims against the source works.

Q6. standards.py:1791-1803: a log that cannot be statted makes the standard red whether or not
its owner is running (order d03706b5eaf0 territory). Intended for jobs that legitimately have no
log yet?

Q7. repass_bands.py:83 uses `pipeline.records()`, which skips unreadable record files with a
note and no count, so `--apply` can end "APPLIED. N record files rewritten." rc 0 having never
seen a torn record. Should the tool print how many record files it could not read?
Similarly catalogue_models.sweep() reads raw `~/cascade/config.json`, not `cascade.config.load()`,
so providers/models that exist only in Cascade's DEFAULT_CONFIG merge are invisible to it.

Q8. standards.py:1149-1150 tests `cov.get("age_h", 99)` but prints `cov.get("age_h", 0)`: a
coverage block with no `age_h` shows a red row reading "0.0h". Cosmetic, worth aligning.

## Cleared (examined closely, found correct)

- chord_field.py: all six adjudications' arithmetic helpers (`landauer_floor`, `recoil_momentum`,
  `recoil_velocity`, `critical_power_self_focus`), `total_beta()` sum (64+96+8+0+128+32=328),
  constants used and none dead.
- repass_bands.py: gate-on-write pattern, `scale_note_rejected` companion set before clearing the
  note (matches `ENTITY_REJECTION_COMPANIONS` reasoning), all roster prints uncapped, `denied`
  list and rc 1, halt interlock fail-closed and only on the `--apply` path.
- style_audit.py: `TURN_ENDING` anchor, `entries()`/`record_of()` splitting, self-test negative
  control, the banned/vocab lists uncapped.
- zfighters.py: ran `compute()` and `value()` from a temp script: 14 sheets all carry exactly the
  eleven `A.WEIGHTS` axes, magnitudes M7/M4/M3/M2 match the stated anchors, Goku's sheet loads
  and `value()` works on it; `--full` handles a missing `provenance`; write is gated.
- catalogue_models.py: `m.get("id") or m.get("name") if isinstance(...) else str(m)` parses as
  intended; EMPTY_LIST vs malformed vs unreachable arms; `_merge_keys` precedence produces the
  same effective winner as cascade/config.py `load()` (a legacy config.json key overrides
  secrets.json there too; only the docstring wording differs); write verdict gated and carried
  into the rc.
- weave_index.py: `_records_sig` per-file and directory-level fail-closed handling, memo window,
  `stale_verdict` arithmetic and STALE_FRACTION table, `staleness()` reason branches,
  `escalate_if_stale` identity held constant, `--write` pair-landing SPLIT warning, stopname/short
  key rules at the matching step only, `norm()` on the live corpus (3 empty keys of 282,853).
- address_space.py: `_bits`, `pack`/`unpack` round trip, `_hash_offsets` floor reproducing
  8/48/78, `HASH_BYTES` guard, `fit()` no-modulo raising via `pack`, write gated.
- sweep_plan.py: `freeze_plan` CAS against absence, refusal on non-"absent" reasons,
  `normalise_module` exact rules, shard per-pid naming, `record()` never raising, `missing_detail`
  roster split, `check_briefs` frozen-plan comparison (excluding F4).
- standards.py: `job_stamp`, `job_stall_verdict`, `read_progress_verdict` tri-state,
  `charter_regression_verdict`, `context_verdict`/`resident_context`, `provider_pool_denominator`,
  the model-metrics `tps` proof of flow (cloud rows carry character counts, not `tps`), the
  self-check regex, and the `_dropped` aggregate.

Recorded via `sweep_plan.record('run67', [...nine basenames...], batch=7)`.
