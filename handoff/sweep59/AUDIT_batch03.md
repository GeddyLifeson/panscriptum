# Sweep 59 -- AUDIT batch 03

Modules read in full: | module | lines | read (top to bottom? mtime) |
|---|---|---|
| src/pipeline.py | 3656 | yes, full (2026-09-14 00:09) |
| src/weave_index.py | 730 | yes, full (2026-09-14 00:21) |
| src/endpoint.py | 615 | yes, full (2026-09-13 23:24) |
| src/backfill.py | 494 | yes, full (2026-09-13 23:22) |
| src/snapshot.py | 376 | yes, full (2026-09-02 23:15) |
| src/catalogue_aurora.py | 328 | yes, full (2026-09-14 22:14) |
| src/cachekey.py | 217 | yes, full (2026-09-14 22:14) |
| src/whoruns.py | 159 | yes, full (2026-09-13 22:34) |

No new CRITICAL/MAJOR/MINOR defects found in any of the eight modules on this pass. This is an
extremely mature, heavily-audited slice of the tree (marked by dozens of order-numbered fixes each
with measured evidence); everything suspicious on first read resolved into either already-fixed
behaviour or a documented deliberate design once the surrounding docstring/comment was read, per
the brief's rule 2. All open work orders touching these eight modules were re-verified directly
against current source rather than assumed still true.

## src/pipeline.py
### New findings
None.
### Known (already open orders)
- `0aceab8473e1` SCHEMA_FIELD_UNREAD -- still accurate. `physiology` is required of the model on
  every entrypass call (`ENTRY_SYSTEM` prompt text lines 1959-1964; `ENTRY_SCHEMA` property at
  line 2055 and `required` list at line 2062) and is read from `res` NOWHERE in the result walk
  (lines 2345-2428 handle `category`, `scale_note`, `magnitude`, `topic`, `subroom`, `catalogued`
  but never `res.get("physiology")`). `MERGED_ENTRY_FIELDS` (line 841-846) still omits it.
  `grep -n physiology src/*.py` outside pipeline.py returns nothing -- no other module reads it
  either. Every entrypass call still pays tokens for a field the corpus discards.
- `55d0be76b99b` SYNTHESIS_CEILING_WITHOUT_A_BAND -- still accurate. In `phase_synthesis`
  (line 1814), `_ceiling = (got.get("ceiling_entity") or "").strip()` (line 1898) is computed
  independently of `band`, which can be forced to `"unassayed"` by the evidence check at lines
  1887-1888 (`if b != "unassayed" and not valid_scale_note(_ev): b = "unassayed"`). Nothing clears
  `_ceiling` when that happens, so `rec["synthesis"]` can still land with a real `ceiling_entity`
  and `provisional_magnitude: "unassayed"` together -- the exact state the order describes. `todo`
  at line 1825-1826 is still keyed on `ceiling_entity` alone, so such a record is never re-selected
  either. Unchanged since the order was filed; still an owner ruling, not something to fix here.
- `b186bc4dad8f` THREE_AXES_NOT_TWO_CATEGORY_TOPIC_SUBROOM -- still accurate as doctrine. Verified
  `CATEGORIES`/`TOPICS`/`SUBROOMS` (lines 131-183) and the entrypass result walk (2401-2427) keep
  the three axes independent as the order requires; no violation found, just confirming the
  standing ruling is still being followed in code.
- `ff77e242b830` item 8 (OWNER_QUESTIONS_FROM_SWEEP48_BUNDLE) -- still accurate.
  `rec["synthesis"]["unassayable_digest"]` is written at line 1917 and
  `_unassayable_verdict_is_stale` (lines 1779-1811) still reads only `unassayable_cast_size`, never
  the digest. Unwired exactly as the order states.
- `f19f4a2b00f4` ENTRYPASS_DONE_KEYS_FOR_PURGED_SOURCES -- an owner curatorial question about
  `state/PIPELINE_STATE.json`, not something this module's code can settle; `records()` (line 753)
  still only returns sources with a truthy `entries` list, consistent with the order's description.
### Checked and clean
- `_merge_state`/`_fold_state`/`save_state` three-way CAS merge of `PIPELINE_STATE.json` (lines
  320-486): scalar-wins-to-this-runner, dict-recurse, list-as-bidirectional-set-merge all verified
  against their own docstrings' claims by tracing the four base/ours/disk cases by hand.
- `write_record` / `write_record_catalogue` two-writer contract (lines 981-1502): entry pairing by
  `_entry_pair_key` triple and by name-group ordinal, `MERGED_ENTRY_FIELDS`/
  `ENTRY_REJECTION_COMPANIONS`/`CATALOGUE_CURATED_FIELDS` gating, and the "never shrink the cast"
  carry-forward arithmetic (`max(len(dgroup)-len(fgroup),0)`) all check out arithmetically and
  match their docstrings' measured claims.
- `ask_pool_first`/`_pool_answer_usable`/`ask` cloud-then-local routing, `_landed`/`gate_done`
  write-verdict gating across all eight phases, and the phase-pointer/`phases_never_closed`
  honesty check in `main()` all verified consistent with their stated contracts.
- `_BAD_CHARS` eaten-escape guard present and correctly placed (lines 94-97, before any regex use).

## src/weave_index.py
### New findings
None.
### Known (already open orders)
- `2cb442afd901` WHEN_SHOULD_A_MOVED_CORPUS_RAISE_THE_INDEX_ORDER -- still accurate. `staleness()`
  (lines 439-526) computes `behind` and `stale` as separate, correctly-independent fields exactly
  as the order describes; the fractional threshold it asks the owner to rule on is still absent by
  design ("picking one here would be decreeing a policy inside a detector").
- `d1709d8e757d` ENTITY_INDEX_NEVER_REBUILT -- still accurate. `escalate_if_stale()` (line 529)
  now files/refreshes a RUN-rung order every invocation, which is the escalation half the order's
  shift notes describe as already done; the scheduling half is still open by the module's own
  admission in its docstring ("This module cannot fix that by itself ... overnight.STANDING and
  the foreman remedies are not files this order's rung may edit"). `grep -n weave_index
  src/overnight.py src/foreman.py` returns nothing, confirming no standing job calls it.
- `21c075e5e2d6` MORE_WRITERS_WITHOUT_A_HALT_INTERLOCK_SWEEP58 -- still accurate. `main()` (line
  573) writes `ENTITY_INDEX.json`/`WEAVE_CANDIDATES.json` under `--write` with no
  `escalation.assert_clear()` call anywhere in the module.
- `fadd4338a7b0` REGEX_MODULES_WITHOUT_EATEN_ESCAPE_GUARD -- not applicable to this module; the
  order's own text excludes weave_index.py by name ("Also weave_index.py, which run #58 fixed").
  Confirmed: guard present at lines 39-41.
### Checked and clean
- `designations()`/`continuity_of()`/`norm()` caching and fallback-on-unreadable-corpus logic
  (lines 109-197): confirmed the failure path does NOT cache an empty designation set (matches the
  order 75307186e12a fix it documents).
- `_records_sig()` scandir-based signature with per-entry vs. whole-directory OSError handling
  (lines 207-315): traced both exception arms: an unstattable single file still returns the full
  readable file list with a poisoned (`None`) signature; a whole-directory `OSError` now also
  poisons the signature via `unstattable` rather than silently returning a cacheable `(0, 0)`.
- `build()`'s short-key/stopname/empty-key exclusion counters (lines 355-433) and the candidate
  report's uncapped bucket/ranked-with-floor printing (lines 622-684) all match Hard Rule 0.

## src/endpoint.py
### New findings
None.
### Known (already open orders)
None found referencing this module in `state/workorders.json` (checked by string search over the
whole file, not just the ids surfaced by grep on module basenames).
### Checked and clean
- `_save()` compare-and-swap merge of `ENDPOINTS.json` restricted to `_DIRTY` hosts only (lines
  91-190), and `register()`'s equivalent CAS merge of `SOURCE_PAGES.json` (lines 523-606): both
  re-read, re-merge and retry on a changed digest rather than overwriting.
  `source_pages()`/`register()`'s absent-vs-unreadable distinction (raises `PagesRegistryUnreadable`
  rather than returning `[]`) verified correct.
- `detect()`'s DEAD_TTL re-probe logic (lines 222-272): a live verdict never expires, a dead one
  re-probes after 24h; order matters (API tried before RAW) as documented.
- `fetch_raw()`/`fetch_html()`'s refusal-vs-absence handling (404/410 vs. other HTTP codes vs. a
  200 that is actually a block page) all correctly distinguished and separately counted via
  `silence.note`.
- `_BAD_CHARS` guard present and correctly placed (lines 55-57) despite not being one of tonight's
  24 modules -- it was evidently added in an earlier run.

## src/backfill.py
### New findings
None.
### Known (already open orders)
- `0384c99d5454` BACKFILL_ALL_EXIT_CODE_ON_SOURCE_FAILURE -- still accurate. `main()`'s `--all`
  path (lines 399-463) counts sources that raise into `errors` (line 429) but the final `return`
  (line 463) is `1 if denied else 0` -- `errors` never affects the exit code, so a run in which
  every thin source raised `RosterIncomplete` still exits 0. Confirmed this is exactly the
  asymmetry the order contrasts with the `--source` path (lines 465-490), which since sweep58-
  batch08's fix does exit 1 on `failed` (raised, refused, or write-denied).
### Checked and clean
- `roster()`'s uncapped, alphabetical-then-subcategory category walk (lines 67-126) and
  `RosterIncomplete` raised (not returned) on an unreadable page (lines 47-58, 90-97): verified the
  docstrings' claims against the actual loop logic.
- `backfill_source()`'s ranking key `(t in sizes, -sizes.get(t, 0))` (line 250): traced by hand
  that an unmeasured title sorts before (ahead of) a measured one in ascending order, matching the
  intent that a failed size-probe must not be the reason `--cap` drops a title.
- `absent` computed before capping, `queued_titles` uncapped in the dry-run/`if not missing` return
  (lines 227-280), and the `write_denied` gate before `added`/`entries_now` are reported (lines
  338-356): all correct per their own comments.
- `lead()`'s "walk forward to the first real prose block" logic and its cut-marker on a mid-word
  truncation (lines 129-169): traced the fallback path re-uses the same `t` from
  `F.strip_wikitext`, not a stale rebind.

## src/snapshot.py
### New findings
None.
### Known (already open orders)
None found referencing this module.
### Checked and clean
- `_rel()`'s cross-drive/escape-the-tree containment refusal (lines 44-84) and `_safe_join()`'s
  second, restore-side containment check (lines 267-284): both verified to actually refuse (not
  merely warn) on an out-of-tree path.
- `before()`'s nanosecond+pid snapshot id, `exist_ok=False` directory creation, and
  all-or-nothing/partial-snapshot refusal gated behind `allow_missing` (lines 87-195): traced the
  `requested`/`skipped`/`took` bookkeeping is written to the manifest even when the refusal is
  waived.
- `verify()`'s restore-into-a-tempdir-then-byte-compare, and `_dir_matches()`'s file-by-file walk
  for directory snapshots (as opposed to a bare `os.path.exists` on the directory) (lines 203-264):
  confirmed a truncated/corrupted restore inside a directory snapshot is actually caught.
- `restore()`'s missing-manifest-entry refusal (raises rather than silently returning a smaller
  count) (lines 287-326), and `main()`'s `--list` printer correctly branching on `m.get("broken")`
  (lines 356-372).

## src/catalogue_aurora.py
### New findings
None.
### Known (already open orders)
- `fadd4338a7b0` REGEX_MODULES_WITHOUT_EATEN_ESCAPE_GUARD -- now fixed for this module. It was one
  of the 23 listed modules; the guard is present and correctly placed (lines 30-32, before `HERE`/
  imports that follow, and before any regex use in the file), consistent with tonight's
  "Known concurrent activity" note that run #59 inserted it into 24 modules including this one.
  Confirmed the insertion did not break anything: `slug()`, `record_path()`, `text_of()` and
  `parse_folder()` (which all use `re` after this point) work unchanged.
### Checked and clean
- `slug()`/`record_path()`'s uncapped-identity-with-legacy-fallback scheme (lines 69-119): matches
  `cachekey.py`'s natural/disambiguated-path pattern in spirit; verified the legacy path is only
  consulted when it differs from the full path and actually exists.
- `parse_folder()`'s dedup key `(etype.lower(), normalised name, description)` (lines 129-187):
  confirmed the description rides in the key un-normalised beyond `text_of()`'s own whitespace
  collapse, so two verbatim-identical elements still collapse to one while two same-named,
  different-text elements (the run #36 fix's whole point) do not.
- `main()`'s write-verdict gating on both the per-record write (`write_record_catalogue`, lines
  257-268) and the roll compare-and-swap (`roll.update_rows`, lines 281-304), and the refusal
  roster feeding a nonzero exit code (lines 202-324): all correctly wired end to end.

## src/cachekey.py
### New findings
None.
### Known (already open orders)
- `fadd4338a7b0` REGEX_MODULES_WITHOUT_EATEN_ESCAPE_GUARD -- now fixed for this module, same as
  catalogue_aurora.py above. Guard present at lines 54-56, correctly placed before `_SANITISE` and
  every other use of `re`.
### Checked and clean
- `natural_path()`/`disambiguated_path()`/`candidate_paths()` (lines 86-99): confirmed the
  disambiguating suffix is a hash of the exact requested name, so `candidate_paths()` for entity X
  only ever needs to check X's own two slots, never a third party's.
- `owns()`'s entity-and-optional-host ownership check (lines 101-129), and `load()`'s
  miss-not-corrupt-not-hit-on-a-name-mismatch behaviour (lines 132-151): traced against the
  Magic-8-Ball collision scenario the module's header describes and confirmed a mismatched
  `entity`/`host` is correctly treated as a miss rather than a false hit.
- `write_path()`'s natural-path-unless-owned-by-another-entity fallback (lines 201-217), including
  the unreadable-existing-file case (`except Exception: return nat`) which is a deliberate
  re-earn-the-slot decision, not a swallowed error.
- `text_digest()`/`provenance_ok()`'s three-outcome (proven/changed/unverifiable) provenance check
  (lines 154-198): confirmed an empty `recorded["pages"]` correctly falls into the "unverifiable"
  branch rather than being compared against an empty `now`.

## src/whoruns.py
### New findings
None.
### Known (already open orders)
- `de265a105279` A_NEW_MODULE_REDS_A_SAFETY_ROW_UNTIL_A_WHOLE_SWEEP_RUNS -- a policy question
  about the sweep-completeness proof's handling of newly-added modules in general (already
  resolved for this specific module by run #54, which read whoruns.py in full and fixed the two
  defects it found then); the still-open half of the order is about `verify_math`/`sweep_plan`
  policy, not about whoruns.py's own code, and whoruns.py is not in my module list for this batch
  anyway beyond being the module that originally triggered the order.
- Not applicable: `fadd4338a7b0` (REGEX_MODULES_WITHOUT_EATEN_ESCAPE_GUARD) does not list
  whoruns.py, and correctly so -- the module never imports `re` at all (confirmed by reading the
  whole file), so it has no eaten-escape exposure to guard against.
### Checked and clean
- `script_of()`'s interpreter-flag-skipping scan (lines 50-75), including the two-token skip for
  `-X`/`-W`/`--check-hash-based-pycs` and the `-m`/`-c` early-return-None: traced by hand against
  the `-X utf8 script.py` example the module's own comment gives.
- `running()`'s exclude-self, tree-scoping via `overnight._in_this_tree`, and reliance on
  `overnight._proc_lines()`'s documented return shape (a raw string, not a list) (lines 78-121):
  confirmed against `overnight.py`'s actual `_proc_lines`/`_cmd_tokens`/`_in_this_tree`
  definitions, which exist and match what this module assumes of them.
- `main()`'s grep-style exit codes (0/1/2) and the tri-state UNKNOWN-vs-NONE reporting on an
  unreadable process table (lines 124-159).

## Coverage
`sweep_plan.record('run59', [...], batch=3)` -- see result below.
