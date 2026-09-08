# SWEEP 47 — BATCH 13 AUDIT

Scope: 9 modules, 5,715 lines. **Every line of every module was read.** No module and no line
range was skipped or sampled.

| module | lines | read |
|---|---|---|
| src/assay.py | 1621 | full |
| src/health.py | 1100 | full |
| src/completeness.py | 812 | full |
| src/secondopinion.py | 665 | full |
| src/address.py | 477 | full |
| src/prose_gate.py | 402 | full |
| src/entity_match.py | 296 | full |
| src/cachekey.py | 193 | full |
| src/compress_store.py | 149 | full |

Nothing was edited. Every finding below was reproduced against the live modules before filing,
except where it is explicitly marked as read-verified only.

---

## FILED

| id | code | handler | sev |
|---|---|---|---|
| `b0a931a92419` | HEALTH_LEDGER_WRONG_SHAPE_IS_NOT_CORRUPT_TO_ANY_READER | LOCAL | MAJOR |
| `1f0a100f754b` | ASSAY_AXIS_SCORE_TOP_RUNG_ANSWERS_9_9_BEFORE_LOOKING_THE_AXIS_UP | SESSION | MINOR |
| `dd673cc2f348` | SECONDOPINION_FILES_ORDERS_FROM_A_SCAN_IT_JUST_CALLED_NOT_A_VERDICT | LOCAL | MINOR |
| `21f729df8884` | ENTITY_MATCH_ONE_RETURN_SHAPE_FIX_LEFT_TWO_SHAPES | LOCAL | MINOR |
| `e045c3218e85` | HEALTH_API_PROBE_CALLS_ONE_ARBITRARY_HOST_THE_FAMILY | LOCAL | MINOR |
| `2ce520242de8` | PROSE_GATE_TORN_EVIDENCE_FILE_READS_AS_UNCITED_UNRECORDED | OWNER | INFO |
| `50e8d8be9a9b` | ASSAY_INTERVAL_FROM_HANDS_IS_THE_THIRD_DOOR_WITH_NO_LAYER_1 | SESSION | INFO |

### 1. health.py — a valid-JSON, WRONG-SHAPED ledger is invisible to all three readers (MAJOR)

`state/failures.json` and `state/failure_samples.json` are read in three places, and all three
treat "`json.load` did not raise" as "this is the document I expect". The `.corrupt`
preservation branches — the ones whose comments say at length that the recorder must not become
the sixteenth instance of the defect it exists to expose — are keyed on the parse RAISING, so a
file holding a JSON **list** (or a string, or a number) never reaches them.

Measured against scratch copies:

```
_flush_ledger over a ledger holding ["silent:foo","silent:bar"]
    -> AttributeError: 'list' object has no attribute 'get'
    -> no .corrupt copy made, counts left in memory
_read_ledger over the same file
    -> returns the list unchanged; main(--failures) then dies on s.items()
_flush_samples over a samples file holding [1,2,3]
    -> swallowed by the outer `except Exception: pass`; the file is left as it was,
       no .corrupt copy, nothing recorded anywhere
```

`flush()` is called from `silence.note`, whose blanket `except Exception: pass` is deliberate,
so the ledger write failure is dropped on the floor. From that moment the failure ledger stops
updating and the evidence bag goes permanently, silently empty — which is verbatim the failure
mode the comment at `_flush_samples` says was closed.

### 2. assay.py — `axis_score` on the top rung answers 9.9 before it looks the axis up (MINOR)

`axis_score` returns the literal `9.9` at `if i + 1 >= len(LADDER)`, which is reached before the
`BAND_EDGES[band].get(axis)` lookup and before the `hi <= lo` refusal. Measured live:

```
axis_score(5.0, 'M10', 'ruin')   -> 9.9
axis_score(5.0, 'M10', 'acumen') -> 9.9      # no floor for acumen on any rung
axis_score(5.0, 'M10', 'ruinn')  -> 9.9      # a misspelt Measure
axis_score(1e-9, 'M10', 'ruin')  -> 9.9
axis_score(5.0, 'M9',  'acumen') -> None     # the same axis, one rung down
axis_score(5.0, 'M3',  'acumen') -> None
```

So the function already has the right convention for an axis it cannot scale and does not reach
for it on the one rung where the answer it gives instead is the MAXIMUM. Sibling of the
already-open `76ab006d84b8` (`band_for_quantity` -> M0 on an unknown axis) and
`9b3e59aeeb19` (five conditions, one None) — cross-referenced in the order so the three are
worked together. The plain saturation half is the known M18 bug; the unknown/floorless-axis half
is not covered by either open order.

### 3. secondopinion.py — `--file-orders` files from a scan the module just declared not a verdict (MINOR)

`report()` fingerprints the tree before and after, and on a mismatch prints *"NO NUMBER ON THIS
PAGE IS A VERDICT ... Re-run when the tree is quiet before filing anything from it."* `_torn` is
a local of `report()`; `main()` then calls `file_orders(got)` on that same `got` with no gate, so
the one code path that files work orders is the same process that just detected the tear. The
stated precondition for filing is printed as advice to a human and enforced nowhere.

`main()` also returns 0 whatever `report()` printed — three absent tools, a `TOOL ERROR`, an
`UNPARSEABLE OUTPUT` all exit 0. Verified that nothing in `src/` runs this module as a
subprocess today (drill and verify_math call the functions directly), so the exposure is to an
operator or a future verifier, not to the battery.

**On the brief's standing question — can an absent tool read as a pass here?** Inside the
module's own API, no: `run()` returns `NOT INSTALLED` / `UNASKABLE (...)` with an empty list,
`ran_clean()` requires `status == "RAN"` for every tool, `missing()` reports them, `report()`
prints `<-- NOT AN ALL-CLEAR`, `file_orders()` files a `SECONDOPINION_ABSENT_*` order, and
`drill.absent_tool_is_not_reported_as_clean` holds the invariant. The three runners also read
`returncode` and refuse to parse a placeholder. The only channel that cannot express the
three-valued answer is the process exit code.

### 4. entity_match.py — the "ONE RETURN SHAPE, ALWAYS" fix left two shapes (MINOR)

`candidates()`'s two early exits return `"blocked_by_qualifier": []` while the normal path
returns `dict(rejected)`. Measured:

```
candidates("",       [...])  -> blocked_by_qualifier=[]   (list)
candidates("x",      [])     -> blocked_by_qualifier=[]   (list)
candidates("Wally West (Prime Earth)", [...])
                             -> {'qualifier-conflict': 1} (dict)
.get(MatchReason.QUALIFIER_CONFLICT, 0) raises AttributeError on the first two
```

The comment above those exits names exactly this hazard — "a caller reading that key
unconditionally would KeyError on an empty name or an empty pool, the two inputs most likely to
arrive from real data" — and the fix supplied the key with the wrong type.

### 5. health.py — `check_api_paths` probes one arbitrary host and calls it the family (MINOR, question-worded)

`fams.setdefault("wikipedia" if "wikipedia" in h else "fandom", h)` is a two-way bucket over
`WIKI_HOSTS.json`, so the whole "fandom" verdict is whichever host the JSON happens to list
first. Measured today: 134 distinct hosts, probed = `{'wikipedia': 'en.wikipedia.org',
'fandom': 'aneurism.fandom.com'}`. Two hosts are neither — `rimworldwiki.com` and
`www.dandwiki.com` — and both sit in the "fandom" bucket; dandwiki is the RAW-mode, 403-to-
anonymous host that `check_caches` twenty lines above excuses by name precisely so it cannot sit
permanently red. Latent today (dict order puts aneurism first), and one probe per family is
adequate for the API PATH question this check was built for. The part put as a question is the
reachability half: `completeness.host_reachable`'s own comment records that the fandom block is
per-tenant and that "the farm being up says nothing about the tenant", while this check emits
`"<fam> API unreachable"` as a claim about the family.

### 6. prose_gate.py — the one `cachekey.load` call site in the tree with no `on_corrupt` (INFO)

`cited_names_for` calls `cachekey.load(base, host, n)` with no `on_corrupt`. Every other call
site passes one: `feats.py:1454`, `hostcheck.py:1374`, `pipeline.py:1399`, `read.py:804`,
`sweep.py:184`. A torn evidence file therefore reads as "this entity has no cited feats" with
nothing recorded anywhere. **The direction is fail-closed and no change to what the gate refuses
is proposed** — an entity whose evidence cannot be read should be treated as uncited. The
finding is only that the corruption is unrecorded, so an operator sees `unearned_instrument`
naming an entity whose evidence is on disk and unreadable, with no trace of which of the two it
was.

### 7. assay.py — `interval_from_hands` is the third public door with no Layer 1 (INFO)

`assay()` gained `_check_scores` + `_check_weights`, and `instrument()` gained `_check_scores`
under order 5f99aa19c059 on the stated ground that "a gate on one of two doors is not a gate, it
is a preference". `interval_from_hands` takes Hand readings straight from a caller and publishes
a `centre` and an `interval` from them, unvalidated. Measured:

```
interval_from_hands({"AVAR": nan, "QUILL": 3.0})
    -> centre nan, interval nan, spread nan, covers_all_signatures False
interval_from_hands({"AVAR": inf, "QUILL": 3.0})
    -> centre inf, interval inf, spread inf,  covers_all_signatures False
interval_from_hands({"AVAR": "seven"})  -> TypeError from inside the arithmetic
```

Latent: order `7099a092abd3` records the battery as this function's only caller. The one saving
signal is that `covers_all_signatures` comes back False, which is the only place in the returned
dict that says anything is wrong. Filed as a question because whether a Hand reading has a
declared scale is a charter matter, not a code one.

---

## LOOKED AT AND FOUND SOUND (recorded so the next sweep does not re-derive it)

* **assay.py and Hard Rule 0.** No cap, slice or `[:N]` anywhere in the published path.
  `axes_scored`, `scores`, `axes_nil`, `axes_unestimable`, `axes_unscored`, `variance_by_axis`
  and `signatures` are all whole. The only display cut in the file is
  `difflib.get_close_matches(n=1)` inside an error message that already lists every unknown key.
* **`_check_constants()` runs at import and is genuinely load-bearing** — it now guards
  `SIGMA_BY_ATTESTATION`, `BAND_EDGES` (off-ladder rungs, half-extended rungs, strict increase
  per axis), `ATTESTATION_FLOOR`, `ATTESTATION_FLOOR_UNRECOGNISED`, `INSTRUMENT_WINDOWS` and
  `FACULTY_READS`. Its last two branches have been read as dead twice; the docstring's
  reproduction (rebind `SIGMA_UNKNOWN`, rebind `SIGMA_MAX`) is correct — they watch the two
  derived constants, not the table. Do not delete them.
* **`covers_all_signatures` is honestly labelled.** It is a guarantee being published, not a
  check being run, and the dict says so with `covered_before_widening`, `widening_added` and
  `quadrature_interval` beside it. It is not a check that cannot fail in the harmful sense — it
  does go False on a NaN reading.
* **`assay()`'s `or 1.0` at `denom`** is correctly documented as a structural backstop that
  cannot currently fire. It must not be cited as reachable again; it also must not be deleted.
* **completeness.py `_unmeasured` rows carry `coverage: 0.0`.** Checked the consumers rather than
  assuming: `standards.py:1389` filters `if not c.get("unreliable")` before summing and prints
  an explicit `UNMEASURED` reading when no denominator was obtained; `foreman` and
  `catalogue_web --shortfall` skip on the same key. Not a live misreading; no order filed.
* **completeness.py display cuts are all marked** — `good[:a.top]` is printed under "rows
  printed: N of M measurable (the file holds every row)", the NOT MEASURED list is whole, and
  both name columns are sized from the data.
* **prose_gate.py layers 1–4 hold as written.** `gate_open` / `step4_gate_open` use strict
  `is not True`, read fresh, and refuse on an unreadable or non-mapping config; `floor_ok`
  refuses a floor outside (0, 1]; `cited_fraction` returns None for both "absent" and "zero
  entries" and `evidence_ok` refuses on None; `section_shortfall` charges ghosts AND extras into
  the denominator, so neither a short nor a padded block can reach 1.0; `cited_names_for` fails
  closed to an empty set. Nothing here reads as an unnecessary restriction that should be
  relaxed, and no opening of `prose_enabled` or `step4_enabled` is proposed or implied.
* **cachekey.py** `load()` verifies ownership before believing a hit and `write_path()`
  disambiguates a taken slot; `provenance_ok` keeps its third answer (None = unverifiable).
* **compress_store.py** stages into a pid+thread temp, sweeps it on a denied replace, RAISES
  rather than returning a success dict for a blob that never landed, and `load()` verifies the
  decompressed text against the content address in the filename.
* **address.py** `_load_spine_codes` fails closed (no try/except), `slugify`'s `[:60]` is gone,
  and the UNASSIGNED fallback is the safe answer.

## ALREADY OPEN — CONFIRMED STILL PRESENT, NOT RE-FILED

`0922effae314` (a partially-read correlation matrix is stamped `measured:` identically to a
complete one — this is the batch's brief item 8 and it is already filed, against
`assay._rho_source` by name), `76ab006d84b8`, `9b3e59aeeb19`, `2a0d854b0b68`, `bc4156603071`,
`d47ea56cca29`, `7099a092abd3`, `e296ea51a1d9` (the `len(files) < 25` cache floor),
`4ed4041c3b78`, `d2da5914da94`, `946153deafe9` (`category_size` still has no caller),
`fe99e57e1993`, `07258ace3a09`, `2c8e55f8f3f7`, `6e6954f261e0`, `cefcad5fc513`, `88a5f9192e1b`,
`6273d7103222`, `91cf746c651e`. None was found already fixed.
