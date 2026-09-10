# sweep run54 — batch 03 audit

Modules: `src/pipeline.py`, `src/estate.py`, `src/policy.py`, `src/scope.py`,
`src/cosmography.py`, `src/physics.py`, `src/cachekey.py`, `src/catalog.py`.

Each module was read in full, top to bottom, in the order listed (pipeline.py in five
sequential chunks owing to its length — 3,494 lines). For every module I checked: whether any
`except` swallows a failure without a trace reaching `silence.note` or `log`; whether any
band/ordering/clamp logic reads the data in the direction its comment claims; whether a
docstring's claim about behaviour (including cited orders/line numbers) still matches the code
beneath it; and whether any gate that is supposed to exclude bad input can be satisfied
vacuously. Given how heavily self-audited this codebase already is (nearly every module carries
extensive "found and fixed" commentary with order IDs), I concentrated on finding gaps the
existing commentary does not already cover, rather than re-deriving fixes already on record.

---

## src/pipeline.py

Read in full (3,494 lines, five sequential reads). This is the phase-ladder runner; most of its
history of defects is already narrated in-line with order IDs. I traced the phase-1 synthesis
evidence gate, the two record writers' merge logic, the resume/gating machinery in `main()`, and
the later phases (5–8) end to end.

### MAJOR — the evidence gate demotes the band but not the entity it was attached to, and that leaves the source permanently unreconsiderable
**Where:** src/pipeline.py:1728-1737 (the gate), :1744 (`_ceiling` extraction), :1760-1763
(the `unassayable` stamp), and the exclusion gate at :1671-1672.

**What:** In `phase_synthesis`, after a nomination call returns:

```python
b = clean_band(g.get("magnitude"))
_ev = (g.get("evidence") or "").strip()
if b != "unassayed" and not valid_scale_note(_ev):
    b = "unassayed"
...
got, band = best[1], best[2]
_ceiling = (got.get("ceiling_entity") or "").strip()
rec["synthesis"] = {"ceiling_entity": _ceiling, "provisional_magnitude": band, ...}
if not _ceiling:
    rec["synthesis"]["unassayable"] = True
    rec["synthesis"]["unassayable_cast_size"] = len(rec.get("entries") or [])
```

The gate at :1733-1734 mutates only `b` (which becomes `band`). It never touches
`got["ceiling_entity"]`. So when the model names an entity but backs it with evidence that
`valid_scale_note` rejects (a reputation word, a stat-block phrase, an act with no object — all
of which `valid_scale_note` in this same file is written to refuse), the stored record ends up
with a non-empty `ceiling_entity` next to `provisional_magnitude: "unassayed"`.

**Why it is wrong:** SYNTH_SYSTEM's own hard rule 3 (this file, ~line 1425) says the two fields
must move together: *"If no entry shows a demonstrated feat, set ceiling_entity to "" and
magnitude 'unassayed'."* The code enforces that pairing for the magnitude half only. Two
concrete consequences follow from the mismatch, both traced against the code rather than assumed:

1. `if not _ceiling:` at :1760 is the only place `unassayable`/`unassayable_cast_size` get set,
   and it never fires here because `_ceiling` is non-empty. So a source whose evidence was
   correctly rejected by the gate is *not* recorded as unassayable.
2. The `todo` filter that decides which sources phase 1 will (re-)examine reads, at :1671-1672:
   `if not (r.get("synthesis") or {}).get("ceiling_entity")`. A non-empty `ceiling_entity`
   removes the source from `todo` permanently — `_unassayable_verdict_is_stale` (the mechanism
   this same file built on 2026-09-08 specifically to let a stale unassayable verdict be
   revisited when the cast grows) never even gets consulted, because that mechanism only applies
   to sources already flagged `unassayable`, which this one is not.

   Net effect: a source can get an "unassayed" band stapled to a named entity, on a single bad
   model answer, and there is no path back — not the re-nomination path, not any other code in
   this file — to ever re-examine it. This is the same shape Hard Rule -1's preamble names
   ("a gate that looks like a gate and refuses nothing"), just on the field the gate was not
   built to protect.

   `manifest_builder.py` then hands `ceiling_entity` and `provisional_magnitude` to the prose
   stage together (confirmed by reading manifest_builder.py:283-286, :310-314, :417-420 — outside
   this batch, checked only to establish that both fields are consumed as a pair downstream), so
   the mismatched pair is exactly what a generated volume would see: a named power ceiling with
   no magnitude standing behind it.

**Confidence:** Read the full `phase_synthesis` function and the `todo`/`_unassayable_verdict_is_stale`
gating around it; traced that `b`/`band` and `got["ceiling_entity"]` are independent objects with
no code path that clears the latter when the former is downgraded. Confirmed the coupling
SYNTH_SYSTEM's own prompt text demands. Confirmed the two-field consumption pattern in
manifest_builder.py by direct grep/read (not a full read of that file — it is outside this
batch).

### MINOR — `update_handoff`'s outer exception handler doesn't call `silence.note`, unlike every other handler in this file
**Where:** src/pipeline.py:2468-2469.

**What:**
```python
except Exception:
    log("  (handoff update failed: " + traceback.format_exc(limit=1).strip() + ")")
```
Every other `except Exception` block in this module (I counted ~30 of them while reading) calls
`silence.note("pipeline.py:<tag>")` in addition to whatever else it does. This one does not.

**Why it is wrong:** it is not a silent failure in the everyday sense — `log()` both prints and
appends to `state/pipeline.log`, so a human reading the log sees it. But `silence.note` is this
project's own convention for feeding a failure into whatever aggregate the sweep/health tooling
reads (the ledger `secondopinion.py`/`health.py` are built against). A failure inside
`update_handoff` — say, a corrupt `data/SWEEP_ROLL.json` or a `KeyError` from `PHASES`/`IMPLEMENTED`
disagreeing — is invisible to that aggregate while every sibling write path (`save_state`,
`write_record`, `write_record_catalogue`, `land_json`) is counted. Given how much of this file's
own history is "a fault was real but nothing counted it," this is worth closing even though the
immediate blast radius (a stale `handoff/RUN_STATUS.md`) is already logged in words.

**Confidence:** Read the function and grepped every `except` in the file (shown above) to confirm
this is the one outlier.

---

## src/estate.py

Read in full (724 lines). This module walks the whole tree and parses every file it can, plus a
charter-vs-code consistency check, a `written()`/`terminal()`/`external()` battery. I checked its
TOCTOU-style guards, the `_effective_ext` marker-peeling logic, the charter table-parsing regexes,
and the `external()` Ollama/Cascade/disk checks.

Nothing new found. Checked specifically for:
- silent exception swallowing (every `except` here calls `silence.note` and sets a visible
  `note(...)`/`rec["error"]`, with the sole deliberate documented exception at
  `phase_shelve`... — no, that's pipeline.py; in estate.py the one bare `except FileNotFoundError:
  pass`-shaped absence is explicitly marked "silence-exempt" in its own comment, matching house
  convention for a legitimate first-run state);
- whether the `charter()` band/rung regexes (`band_rows`, `rung_rows`) actually gate on a
  structural check before trusting their match count (they do — `set(band_rows) != {"M%d"...}` and
  `len(rung_rows) != 17` both refuse the four errata checks rather than silently passing zero of
  them);
- whether `artifacts()`'s root-discovery walk (`os.scandir(HERE)`) still agrees with its own
  docstring's claim of "every file in the project, opened and checked" — it does, having been
  fixed from a hand-kept list to a `scandir` walk;
- the `external()` Ollama-unreachable branch: confirmed that the yaml/config/model-name checks
  nested inside the outer `try` are each independently wrapped in their own `try/except`, so an
  internal config fault is very unlikely to be mis-reported as `OLLAMA UNREACHABLE` — I could not
  construct a concrete path that leaks past those inner handlers, so I am not filing this as a
  finding (per the brief: unconfirmed speculation is not filed).

---

## src/policy.py

Read in full (575 lines). The DSL-lite rule evaluator (`OPS`, `check_rule`, `evaluate`) plus
`main()`'s record/coverage/evidence sweep. I checked every operator in `OPS` against the vacuous-
pass exemption logic in `evaluate()`, and the CLI's exit-code contract.

### MINOR — the `absent` operator doesn't check `found`, so it can pass on a field that IS present (holding an explicit `null`), contradicting the assumption the vacuous-pass exemption is built on
**Where:** src/policy.py:44 (the `absent` operator), :212 (its exemption in `evaluate`).

**What:**
```python
"absent":    lambda v, _a: v is None,
...
vacuous = [r for r in results if r["ok"] and not r["found"] and r["op"] != "absent"]
```
`resolve()` (lines 101-122) already distinguishes "the field holds `None`" from "the field does
not exist" via its `(value, found)` return — that distinction is this module's whole reason for
being, per its own header. But `OPS["absent"]` only tests `v is None`; it never consults `found`.
So a document with an explicit JSON `null` at the rule's path (`found=True`, `value=None`) makes
an `absent` rule report `ok=True` — exactly as if the field were genuinely missing.

**Why it is wrong:** the comment immediately above the exemption line claims *"`absent` IS EXEMPT,
and it is the one honest exemption... its only truthful passing case is `found=False`"* — but the
operator itself does not enforce that, so the claim is not actually guaranteed by the code sitting
right below it. A `found=True, value=None` pass for an `absent` rule is a genuine vacuous-shaped
result (the rule was supposed to assert the field is *missing*, and it is not), yet it is
unconditionally exempted from the `vacuous` list, so nothing anywhere would ever surface it. This
is the same shape of bug (a check that looks like a gate but is satisfied by an input the gate was
not built to accept) this module's own header names as the reason it records observed values at
all.

Impact today is nil — no rule table in this file (`RECORD_RULES`, `EVIDENCE_RULES`,
`COVERAGE_RULES`) uses `op: "absent"` (confirmed by reading all three tables in full), so nothing
is silently passing in production. This is a latent defect for the next table, in the same spirit
as this file's own `TYPES`/`ARG_REQUIRED` comments about "a landmine for the next table."

**Confidence:** Read `OPS`, `resolve()`, `check_rule()` and `evaluate()` in full and traced the
exact boolean path for a `found=True, value=None` document field. Confirmed by reading all three
rule tables that `absent` is currently unused, so this is reported as latent rather than active.

---

## src/scope.py

Read in full (474 lines). The per-host fiction-scope prober (search + fetch + tier-mention count)
and its `PROBE_VERSION`-gated cache. I checked the `ProbeUnread` exception discipline, the
compare-and-swap `mutate()` logic, and the `TIERS` band ladder itself.

### QUESTION — the `TIERS` ladder can only ever produce M1-M4 or M6-M8; M0, M5, M9 and M10 have no textual marker and can never be assigned
**Where:** src/scope.py:51-60 (`TIERS`).

**What:** `TIERS` maps scope language to Magnitude ceilings: nation→M1, continent→M2, planet→M3,
star system→M4, galaxy→M6, universe→M7, multiverse→M8. M0 (a village), M5 (star
clusters/associations/nebulae), M9 (metaverses/xenoverses) and M10 (everything) have no entry, so
`scope_for()` can never return them as a source's scope ceiling.

**Why it might matter:** the module header states the goal as establishing "the largest arena a
fiction's conflicts are decided in," bounding the Assay anchor to a fiction's own stated scale
across the *whole* Part Three ladder. The M4→M6 jump in particular skips a whole rung (M5,
"stellar — star clusters, associations, nebulae") that the ladder elsewhere treats as a real,
distinct band (see `pipeline.py`'s `BANDS`/`SYNTH_SYSTEM` and `assay.LADDER`, which both carry all
eleven bands). I could not find a comment in this file explaining the omission the way the module
otherwise explains every other design choice (the MIN_MENTIONS floor, the highest-not-commonest
rule, the srlimit history) — it may be a deliberate omission (no natural-language marker
reliably distinguishes "star cluster scale" prose the way "galaxy"/"universe" do, and nobody
writes fiction claiming M0/M9/M10 scope in so many words), but given how carefully every other
threshold in this file is justified, the silence on this one specific gap reads more like an
oversight than a ruling. Flagging as a question rather than a fix per the brief, since I could not
confirm which it is from the source alone.

**Confidence:** Read `TIERS`, `scope_for()`, and the module header in full; grepped this file for
any comment referencing M0, M5, M9 or M10 and found none.

Also checked and found clean: `ProbeUnread` is raised (not swallowed) for every unread-vs-empty
distinction the module cares about; `mutate()`'s compare-and-swap digest-then-read-then-write
ordering is consistent with its own docstring; `build()`'s `todo` selection correctly uses
`_stamp(...) < PROBE_VERSION` rather than bare membership.

---

## src/cosmography.py

Read in full (376 lines). The planetary-census/Kardashev-bridge module. Checked:
- `KARDASHEV_MIX` sums to 1.0 exactly (0.90000 + 0.08500 + 0.01499 + 0.00001 = 1.00000) — the
  `validate()` check at :325-326 would catch a drift here, and it currently would not fire.
- `kardashev_to_magnitude()`'s loop assigns `reached = b` for every band whose Ruin edge the
  budget clears, relying on `ladder` being ascending so the last match is the strongest; confirmed
  against `assay.LADDER = ["M0", "M1", ..., "M10"]` (src/assay.py:107) that this holds.
- `SIZE_CLASS_MAX_GALAXIES` ceilings against `SIZE_CLASSES` multipliers: POCKET computes
  `1/(GALAXIES_DEFAULT*STARS_PER_GALAXY_MEAN)` galaxies (≈5e-9, well under its ceiling of 1.0) and
  MINOR computes exactly `1.0` galaxies (not `>` its ceiling of `1.0`, so `validate()` correctly
  does not refuse it) — both consistent with the 2026-09-08 repair this file documents.

Clean. No new finding.

---

## src/physics.py

Read in full (313 lines). The real-world energy-conversion primitives (`kinetic`, `joules_for`,
`sphere_volume`, `binding_energy`). Every function already carries explicit, cross-referenced
guards for non-positive/non-finite/NaN inputs and non-finite results, each with an "order" ID and
a worked numeric example of the failure it closed. I re-derived several of the cited failure
cases by hand (e.g. that `v >= C` alone lets NaN speed fall through to the relativistic branch
where `gamma` becomes NaN, which the added `not v >= 0.0` guard at :110 now catches) and could not
find an input that still slips past the current guards.

Clean. No new finding.

---

## src/cachekey.py

Read in full (214 lines). The per-entity cache-path scheme (`natural_path`/`disambiguated_path`/
`owns`/`load`/`write_path`) built to stop the `Magic 8 Ball` vs `Magic 8-Ball` collision class.
Traced a three-way collision scenario by hand (entity A takes the natural path; a same-stem
entity B is disambiguated by `_suffix(name)` derived from B's own name; a third same-stem entity C
gets its own distinct suffix from C's name) and confirmed no two of them can be handed each
other's file, and confirmed `owns()`'s optional `host` check is only applied when the caller
supplies one, matching its documented "never a host check with nothing to compare against" rule.

Clean. No new finding.

---

## src/catalog.py

Read in full (168 lines). The read-side CLI (`stats`/`search`/`address`/`read`) over
`output/index/catalog.json`. Checked the `load_catalog()` missing-vs-empty distinction, the
`main()` exit-code plumbing (`cmd_address`/`cmd_read` return 1 on a miss, `sys.exit(main())` at
the bottom actually uses it), and the uncapped "populated sources with no books" listing.

Clean. No new finding.

---

## Summary of findings

- 1 MAJOR: `src/pipeline.py:1728-1763,1671-1672` — phase-1 evidence gate downgrades the band to
  "unassayed" without clearing `ceiling_entity`, which both violates SYNTH_SYSTEM's own stated
  rule and permanently excludes the affected source from re-nomination.
- 2 MINOR: `src/pipeline.py:2468-2469` (missing `silence.note` in `update_handoff`'s outer
  handler); `src/policy.py:44,212` (`absent` operator doesn't check `found`, currently unused).
- 1 QUESTION: `src/scope.py:51-60` (`TIERS` ladder has no marker for M0/M5/M9/M10).
- 0 INFO.
- Modules read clean with no new finding: `src/estate.py`, `src/cosmography.py`,
  `src/physics.py`, `src/cachekey.py`, `src/catalog.py`.
