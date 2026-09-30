# Sweep 68 (run68) - AUDIT batch 04

## Scope

Read in full, sequentially, with the Read tool, in chunks; nothing skimmed. Read-only for the project: no
daemon, phase, drill, verify_math, publish, generate or mutate run was started, and no subagent was used.
Scratch scripts only under `%TEMP%\aud68_04` (they import modules with their paths redirected, or read
`data/` without writing; `rfr.py` redirects every `recover_folder_records` path into a temp tree and stubs
`roll.update_rows`).

| module | lines |
|---|---|
| src/mutate.py | 3440 |
| src/completeness.py | 959 |
| src/weave.py | 747 |
| src/withdraw_chapters.py | 614 |
| src/cleanup.py | 452 |
| src/recover_folder_records.py | 380 |
| src/ledger.py | 232 |
| src/scale_theories.py | 215 |

## Prior-audit cross-check (handoff/sweep67/AUDIT_batch*.md)

mutate.py (sweep67 batch04, F1-F6, Q1-Q2):
- F1 (void target still filed as work): FIXED. `if a.file_orders and r["survivors"] and confirm and stopped_at != i`
  (mutate.py:3373).
- F2 (case-sensitive live-tree refusal): FIXED. `_canon` = `normcase(realpath(...))` on both sides (:2303-2306).
- F3 (stale 24h/one-day docstring): FIXED. `_owner_pid` says 72 hours and about 30 hours (:1266-1273).
- F4 (`_write_rulings` fixed tmp, blind replace): FIXED. Per-pid tmp, `silence.replace_if_unchanged` CAS, and
  `_edit_rulings` re-applies on a lost race (:1098-1156).
- F5 (stale-lock clear removes a fresh lock): FIXED in the way its comment says. The record is re-read and removed
  only if still equal to the stale one (:250-271); the residual read-then-remove window is marked `ponytail:`.
- F6a/F6b (silent state copy, `live_before` outside the `try`): FIXED (`silence.note` at :1792; `live_before` read
  inside the `try` at :2371-2374).
- Q1 (`--list` refused under a halt while `--list-ruled`, `--rule-equivalent`, `--unrule` are exempt): STILL STANDS,
  unchanged (`escalation.status()` at :2971, `--list` at :2978, registry commands at :2926-2968). Carried, not re-filed.
- Q2 (`splitlines` vs `ast` line numbers, :472 and :2397): STILL STANDS as latent. Re-checked: none of
  `\x0b \x0c \x1c-\x1e \x85    ` occurs in assay.py, prose_gate.py or escalation.py, and
  `len(splitlines(keepends=True))` equals the newline count in all three.

weave.py (sweep67 batch16 F1, Q6): F1 (`filtered_index` decided on `hits[0]`) is FIXED: `_mechanic(h)` is applied per hit
and a key is dropped only when no hit survives (weave.py:288-305). Q6 (`load_index` warns on a stale ENTITY_INDEX and
`--write` still lands) STILL STANDS, unchanged (:138-146, `main` :613-698). New finding F1 below is a different fault in
the same function.

withdraw_chapters.py (sweep67 batch16, unchanged, Q5): STILL STANDS. `_manifest_merge` still replaces an unparseable
existing manifest with only this run's withdrawals (:483-489), under a digest match. Carried.

completeness.py (sweep67 batch15 F3, F9): both FIXED. `_api_error` gates both probes (:213-226, used at :199, :295), and
`land()` now refuses on an unreadable prior and notes a torn one (:812-832).

cleanup.py (sweep67 batch13): re-checked the `_NAV` measurement against the live corpus (36 hits then; 327 catalogued
names match now, mostly `List of ...`, `Season N` and `Index of ...` rows plus the `Character*` /
`Characters*` furniture named there; none is a real entity). The write gate on `write_record` is as described. The halt
interlock was not examined then and is F2 below.

recover_folder_records.py (sweep67 batch14): its `is None` vs `[]` handling, shortfall recording and CAS roll update were
"re-traced, hold". They hold for the first run; F3 below is the second run.

ledger.py, scale_theories.py (sweep67 batch06): unchanged; the ruled "retained, no production caller" markers still
sit at ledger.py:154-198 and the held-module text at scale_theories.py:21-57. `surviving_theory()`'s field switch and
raised arity check re-read and hold.

## Findings

### F1. MEDIUM (reproduced) - weave.py:297 the rules-voice test drops thousands of real entities from the weave index
`_mechanic()` ends `or _RULES_VOICE.search(desc))`, and since order 543cec75ad02 it scans the WHOLE description. The
pattern (weave.py:175-180) matches `you (can|may|gain|choose|learn|know|have|...)`, `when you use|cast|...` and
`as an action`, all of which are ordinary English in quoted dialogue and wiki boilerplate. Scenario: the Marvel entry
"Doctor Castillo (Earth-616)" carries the description "You know, I just never get tired of having my credentials ..."
and is dropped as a rules construct; DC "Edwin Alva (Dakotaverse)" and "Grimble (Fables)" carry the wiki stub line "You
can help out by providing additional information" and are dropped; "Black Widow Vol 7 1" and "X-Command (Earth-19647)"
(quoted speech) likewise. A dropped hit contributes nothing to `occ`, to the surprisal pair weights, to the permutation
null or to `resolve()`, so the shelf pair evidence is computed from a smaller universe wearing the same shape.

Repro (`%TEMP%\aud68_04\idx2.py`, `idx3.py`, live `data/ENTITY_INDEX.json`, 266,450 keys, 282,850 hits; `_STATBLOCK`
not applied, so the counts are a floor): 8,377 hits are dropped by `_RULES_VOICE` alone; 7,231 of them are outside any
D&D-named source. By topic (rules-voice or name-mechanic): Powers 4,109, Persons 2,422, Weapons 703, Media 358, Places
347, Events 263, Factions 193. By source: Marvel 1,992, DC 626, SpongeBob 220, Transformers 113, Legend of Zelda 83,
Halo 44, Gumball 43, Diablo 41. 583 of the dropped hits are the stub sentence "You can help out by providing". 7,482 keys
lose every hit (109 hits are the name test). `main()` prints only `(N mechanics dropped -> M)`, a key count, with no
per-source or per-topic figure, so nothing shows that Marvel lost about 2,000.
Fix: keep the voice test but require it to sit with a rules signal (a `Powers`/`Weapons` topic, or two distinct
matches, or a match outside a quoted span), and print the dropped counts per source. Or apply it to the topic
buckets that can carry rules text only.

### F2. MEDIUM (verified by grep of both rosters) - cleanup.py:270 and recover_folder_records.py:94 hand-run corpus writers with no halt interlock
Neither module calls `assert_clear` or a `_assert_not_halted`, and neither is on `verify_math._INTERLOCKED`
(verify_math.py:7762-7770) or drill's `_HALT_WRITERS` (drill.py:26602-26623). `pipeline.write_record` does not consult the
halt either (no `assert_clear` between :1501 and :1700). The 2026-09-28 "fix everything" ruling (orders 1e6f99e54b25 /
21c075e5e2d6 / 3099138a82bd) and sweep67 order 6d800a399592 interlocked the class; sweep67 batch06 finding 5 named
`recover_folder_records.py` as absent and did not read it. Scenario: an OWNER halt stands; a person or wrapper runs
`python src/cleanup.py --apply`. It then rewrites data/records/*.json under the halt. Measured dry (`cl.py`, read-only,
live records): 184,565 of 282,835 catalogued descriptions would be rewritten, 327 entries struck as navigation, 26 as
empty mechanics, 87 newly marked thin. The blast radius is the whole corpus, on a path the supervisor's gates never see.
`recover_folder_records.py` (no `--dry-run`) writes new `data/records/<slug>.json` and lands roll rows the same way.
Fix: `_assert_not_halted` on the writing path only (after argparse, skipped for dry runs), as retry_synthesis.py does,
plus a row in each roster.

### F3. LOW-MEDIUM (reproduced) - recover_folder_records.py:321-323 "re-run to update the roll" is false; the second run never retries the roll
When the CAS roll write is denied the run prints "the records landed but SWEEP_ROLL.json still reads entry_count: 0 for
them -- re-run to update the roll" and returns 1. A re-run cannot do that: `roll_changes[name]` is set only on the branch that
just wrote the record (:305), and the record now exists, so `already` is true and the name goes to `skipped_populated`
(:224-226) with no roll change. Repro (`rfr.py`, temp tree, `roll.update_rows` stubbed): run 1 writes the record and the
stub reports denied (rc 1); run 2 prints "Left alone: 1 record(s) already hold entries on disk. The roll's entry_count is
what is stale", exits 0, and `update_rows` has been called once in total. The roll stays at `entry_count: 0` and the exit
code is clean, so a wrapper that reruns on rc 1 stops. Fix: in the `already` branch, when the roll row is still 0 and the
record has entries, add `roll_changes[name] = {"entry_count": n, "status": "catalogued"}`; or reword the message to say
`resync_roll.py` is the remedy.

### F4. MEDIUM (mechanism reproduced, the poisoning itself UNVERIFIED) - mutate.py:2539-2540, 2436-2438, 2497-2527 only HALT.json is scrubbed; anything else a mutant leaves in the sandbox judges every later mutant, and a baseline refresh adopts it
This is the answer to the run #68 question. `_scrub_sandbox_halt` (:1966-1989) removes `root/state/HALT.json` before each
mutant and before each refresh. The sandbox `state/` is otherwise copied once (`sandbox()`, :1779-1792) and never restored
between mutants, while the gates write to it: `escalate()` appends to `state/escalation.log` and
`state/escalations/<source>.log`, calls `health.record`, and files work orders; `stop_subsystem` writes `STOPPED.json`;
the drill net at drill.py:15255-15275 stops the synthetic `__drill_rung4__` in the REAL (here sandbox) `STOPPED.json`
and releases it in a `finally`. State a mutant leaves behind, and what carries it forward:
1. **Between the gates of one mutant.** The scrub runs once per mutant, before the write. A mutant whose `verify_math`
   run reaches `escalate(OWNER, ...)` in the sandbox and still produces the baseline signature (so it "survives" that
   gate) leaves `HALT.json`; the next gate in the same loop (`drill`, :2546) then runs halted. Per the module's own
   account of 2026-09-29, a halted sandbox turns drill and verify_math red, so `sig != base` and the mutant is scored
   KILLED by a refusal to run, not by a net. That is the false-kill direction this module exists to prevent. Scrub
   between gates, or count a gate whose output says halted as `could_not_judge`.
2. **`STOPPED.json` and `PAUSED.json`.** A mutant that breaks `resume_subsystem`/`_is_probe_release`
   (escalation.py:1072) leaves `__drill_rung4__` stopped in `sandbox/state/STOPPED.json` for every later mutant, target
   and refresh. `PAUSED.json` is copied in from the LIVE state if the owner has a pause standing when the sandbox is built,
   and is not stripped (only `HALT.json` and `MUTATION_ACTIVE.json` are, :1873-1877). I could not run drill to show a later
   verdict changing; I checked that the nets which read these files mostly redirect them to a scratch path
   (drill.py:26460, 29321, 15700), so the visible effect may be small. UNVERIFIED.
3. **The refresh adopts it.** `_refresh_baseline` (:2497-2527) takes any moved signature as the new baseline
   (`base.update(fresh)`), including green-to-red, and only journals it as drift. So the first refresh after a mutant
   dirties the sandbox (at most `--rebaseline-every`, 1800 s) turns the leftover into the reference the remaining
   mutants are judged against. That is exactly how a single halt disabled two gates for twenty hours.
4. **Junction write-through.** `prompts/`, `reference/`, `output/index`, `output/raw` and every `data/<dir>` are live
   portals (documented at :1555-1562); a mutant's gate that writes through one changes the live tree and every other
   sandbox. Known and documented, listed for completeness.
Fix for 1-3 in one place: snapshot the sandbox `state/` tree right after `sandbox()` and after the baseline, and restore
it (copy the `.json`/`.jsonl` set back, delete anything new) before each mutant and inside each refresh. It is 14 MB
against gates that take minutes, and it replaces the per-file scrub with the property the scrub was standing in for. In
addition, in `_refresh_baseline`, restore first and refuse to adopt a moved signature whose rows name the halt.

### F5. MEDIUM-LOW (reproduced) - mutate.py:831-833 the gate timeout is not a bound when the gate has a live grandchild
`_gate_result` runs `subprocess.run(cmd, capture_output=True, timeout=timeout)`. On expiry `run` kills only the direct
child and then calls `communicate()` again, which waits for the stdout/stderr pipes to close, and a grandchild inherited them.
Repro (`t2.py`): a child that spawns a grandchild sleeping 25 s and itself sleeps 60 s, `timeout=3` returned after
29.7 s. drill.py has 27 `subprocess` call sites; a mutant that makes one of those children hang (or an orphaned child
of a hung drill) makes `_gate_result` block for as long as the grandchild lives, with no timeout, and the TIMEOUT
verdict and `hang_confirms_a_kill` never happen. The pass stalls at that mutant. Any leftover grandchild also keeps reading
and writing the sandbox while the next mutant is written, which is another path into F4. Fix: `Popen` with
`CREATE_NEW_PROCESS_GROUP`/a job object, and on timeout `taskkill /T /F /PID` before `communicate()`; or redirect
output to a file instead of pipes.

### F6. LOW - withdraw_chapters.py:594 stale line citation
"`address_space.py:467-480` hits the identical condition -- a denied `silence.write_json` ... and returns 1". Those lines
are now the tail of `fit()` in `address_space.py` ("The `None` -> 0 arm is still here", :465-476), not a denied-write return. The
sentence is the justification for rc 1, so a reader who follows the citation finds nothing. Cite by symbol.

### F7. LOW (by reading) - completeness.py:812-815, 189-191 and mutate.py:2531 a wrong-shaped file quietly disarms or crashes
(a) `land()`: a prior COMPLETENESS.json that parses to `null`, `0` or any falsy value leaves `prior` falsy, so
`if prior and len(rows) < len(prior) * SHRINK_FLOOR` (:843) is skipped and the floor is not applied, with no note (the
`ValueError` arm notes; this shape does not). (b) `category_size_probe`/`_host` call `d.get(k)` and `hit.get("at")` on
whatever `state/category_sizes.json` decoded to (`_cs_load`, :107-116); a list or a string there raises `AttributeError`
outside the `try` and takes the audit down. (c) mutate.py `--rebaseline-every -1` is truthy (`a.rebaseline_every or
None`, :3193), so `time - last_base >= -1` re-photographs every gate before every mutant. All three are self-inflicted
or hand-edited inputs; none reaches a published number. Fix: `isinstance(prior, list)`; `isinstance(d, dict)`; `ap.error`
on a negative interval.

### F8. LOW - ledger.py:198-232 `assay_to_standards` accepts a `ruin_score` outside [0, 10] and extrapolates past the band
`ruin_score / 10.0` interpolates in log space between the band's floor and the next floor with no clamp. Run:
`assay_to_standards("M3", 15)` returns 1.57e28 Standards, above M4's own floor (1.05e24); `-3` returns a value below M3's
floor. The docstring says "a band of destructive capability", so a score that leaves the band prices an entity in a different
band. Held module, no production caller (ruled), so this is only for whoever wires it: raise on a score outside [0, 10].

## Questions

1. **mutate.py `--list` under a halt** (carried from sweep61/65/66/67, mutate.py:2971-2993): unchanged, counts only, still
   refused while the three registry commands are exempt.
2. **weave.py:138-146 and :613-698** (carried): `--write` lands CONTINUITY_GROUPS / RESOLVED_ENTITIES / SHARED_STAGE_GRAPH_IDF from an
   index the code itself has just called stale. The ruling asked for in sweep67 has not arrived.
3. **weave.py:225, 313 `len(srcs) > 60` / `max_sources=60`.** An entity in more than 60 sources contributes no pair evidence and
   no `shared` row. The comment calls it a common noun; it is also the only remaining band cut in the weave. Deliberate under
   Hard Rule 0 (weights, not a roster), or should the excluded keys at least be listed in the output?
4. **mutate.py:1736 vs silence.append_line.** `sandbox()` hardlinks every top-level `data/` file and argues safety from
   `silence.write_json`'s atomic replace. `silence.append_line` appends in place, and `data/SCOUT_ARCHIVE.jsonl` (written by
   `scout._land` through it, scout.py:836) is a top-level file, so an append from a sandboxed gate would land in the LIVE
   inode. No gate in drill/verify_math runs scout today (grep), so nothing fires; is the claim "every writer replaces" meant to
   cover appenders?
5. **withdraw_chapters.py:483-489** (carried Q5): an unparseable existing `catalog.withdrawn.json` is replaced, not set aside.
6. **withdraw_chapters.py:414-443.** The stray sweep reads `claimed_raw` from the catalog read at startup and then walks
   `output/raw`. A chapter `generate.py` lands in between (file written and catalog row added after the read) looks unclaimed,
   is moved to the archive, and its catalog row is kept by `_catalog_merge`. Whole-catalog `--go` only, and the tool is normally
   run with the library stood down; is that assumed, or should the sweep re-read the catalog under the same CAS?

## Cleared (read start to finish; what was checked)

- **mutate.py**: the lock (`active` fails closed on unreadable and wrong-shape records; `_lock_acquire` O_EXCL; token-checked
  `_lock_release`; `_hold_lock` re-entrancy); `_mutations` (per-node spans, `_col` byte-to-char, `_between`, `_token_pos`,
  `_fallback_next`, dedup keyed on resulting text); `_row_ids`; `_gate_result` signature/side channels; `hang_confirms_a_kill`
  (two independent pristine readings, scrub and restore before the re-run); `unusable_gates`/`red_gates`/`could_not_judge`;
  `sandbox()` build order (BUILDING_PREFIX rename, owner claim, walk of `src/` including subdirectories, target-presence
  check, `state/` recursive copy, sqlite backup of the scratch DB, HALT/lock removal); `reap_orphans`/`_remove_sandbox`
  (ownership beats age, junction unlink before rmtree, 72 h ceiling); `_run_mutation` refusals (live root, no baseline,
  ungauged gate, unusable gate), restore probe, killed + survived + indeterminate arithmetic, `live_file_untouched`;
  `file_orders`; `_session` ordering, `stopped_at` break, rc propagation, `--detach` argv rebuild. Stale-`.pyc`
  hazard (same-second, same-size mutants reuse a stale pyc; reproduced in `run2.py`) is real in principle but unreachable here:
  the import gate alone takes 4-5 s on a sandbox copy, so no two mutants are written inside one integer second.
- **completeness.py**: `subdomain`/`wiki_host` sentinel filter; `_cs_put` snapshot under lock; `_api_error` at both probes;
  `host_reachable` DEAD/RAW/API three-way; `audit()` union of hosts and records, `primary`/`shared`, every
  `_unmeasured` shape, `n is not None`, the zero-denominator and none-answered branches, `cov > 1.0`; `land()` three outcomes,
  shrink floor, `write_json` verdict. No duplicate `source` key exists across the 216 record files (checked, `dup.py`), so
  `catalogued_counts`'s last-writer-wins dict does not lose a numerator today.
- **weave.py**: `index_staleness`, `idf_table`, `name_surprisal`, `null_threshold_surprisal` (refuses zero trials and empty
  null), `components` (`<= 0` refusal, complete linkage, early exit), `resonance_graph`, `resolve` (all 282,850 hits carry `name` and
  `source`, checked), the per-hit `filtered_index`, `main`'s three-file write verdict.
- **withdraw_chapters.py**: `_file_state`, `_archive_name_free`, `_land_merged` CAS and its OSError arm, per-selector refusal,
  half-entry amendment, stray guard, exit code.
- **cleanup.py**: `_ruby_question_mark`/`_ruby_parenthetical` decline on ASCII, idempotent `?` rule, `clean_ceiling`
  (ambiguous prefix refused), thin-mark first-time-only `changed`, gated `write_record`, five uncapped rosters, rc.
- **recover_folder_records.py**: `mapped is None`, shortfall recording before the early exit, `already` fail-closed on an
  unreadable record, denied-write branch, `roll.update_rows` CAS on the first run.
- **ledger.py**: band edges are contiguous (each band's hi equals the next band's floor in Standards), M10's extrapolated ceiling,
  `cross_rate` orientation (gil to zenny 0.79), `to_standards` `None` for the non-convertible and the unlisted.
- **scale_theories.py**: exactly one `falsified: False` (T3); `bulk_export_beta` floor branch; T2's 6.3e18 J.

## Coverage recorded

`sweep_plan.record('run68', ['mutate.py', 'completeness.py', 'weave.py', 'withdraw_chapters.py', 'cleanup.py',
'recover_folder_records.py', 'ledger.py', 'scale_theories.py'], batch=4)` run from the kit directory via miniconda python
after this file was written; all eight modules were read in full first.
