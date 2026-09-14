# AUDIT — sweep run57, batch 08

Modules read in full, top to bottom, this run: `src/workorders.py` (2,162 lines), `src/liveness.py`
(1,054), `src/catalogue_web.py` (785), `src/manifest_builder.py` (670), `src/worldseed.py` (532),
`src/burgs.py` (432), `src/deprecated/catalogue_local.py` (333, guarded by its module-level
`SystemExit` -- read only, guard not touched, not run), `src/citecheck.py` (260), `src/whoruns.py`
(159).

AUDIT ONLY. Nothing under `src/`, `data/`, or `state/` was written or edited. No orders filed,
resolved or rerouted. `workorders.py --sweep`, `drill.py` and `verify_math.py` were not run. The
open queue was read once at the start (`workorders.open_orders()`) to avoid re-deriving known
findings; matches are marked KNOWN(<id>) below. `handoff/sweep56/AUDIT_batch08.md` and
`AUDIT_batch16.md` were also read for the same reason -- batch numbers are coincidentally the same
between sweep56 and sweep57 but the module lists differ (sweep56 batch08 covered `wiki_source.py`,
`address_space.py`, `canon_backup.py` etc. alongside `workorders.py`/`liveness.py`; sweep56
batch16 covered `citecheck.py`/`whoruns.py` alongside `hostcheck.py`/`binding_health.py`/etc.).

---

## workorders.py

Read all 2,162 lines: `_load`/`_mutate`'s CAS, `order_id`/`file_order`, `is_selftest`, `resolve`,
`reroute`, `resolve_code`, `twins`/`where_split_by_code`, `cap_boundary_scan`,
`_supersede_binding_suspect`, `ghost_orders`, the whole of `sweep_detectors()` (all twelve `_fire`
call sites plus the "1b" overlap-guard block added in run #56), `_side_channel_text`, and `main()`.

### CONFIRMED — KNOWN(066bfb187bd1): `file_order`'s refresh unconditionally overwrites `handler`
AND `found_by` (and `evidence`), clobbering a prior `reroute()` and its audit trail

**Where:** `src/workorders.py:530-555` (`file_order`'s `_change`) vs `src/workorders.py:748-768`
(`reroute`'s `_change`).

`reroute()` mutates the record's `handler` in place and appends a note to `found_by`:
```python
        old = rec.get("handler")
        ...
        rec["handler"] = handler
        rec["found_by"] = "%s | rerouted %s -> %s by %s: %s" % (
            rec.get("found_by") or "", old, handler, by or "?", why)
        return rec, True
```
`file_order`'s refresh, called every time the *same detector* fires again for the same
`code`/`where`, rebuilds the stored dict from scratch out of the detector's own call-site
arguments, carrying forward only `first_seen` and `seen` from the previous record:
```python
        prev = d.get(oid) or {}
        d[oid] = {"id": oid, "code": str(code), "what": str(what), "handler": handler,
                  "severity": severity, "where": str(where),
                  "evidence": evidence if isinstance(evidence, (dict, list)) else
                  (None if evidence is None else str(evidence)),
                  "found_by": str(found_by or ""),
                  "first_seen": prev.get("first_seen", now), "last_seen": now,
                  "seen": int(prev.get("seen", 0)) + 1}
```
`handler` here is the detector's hard-coded parameter at its `_fire(...)` call site (e.g.
`"SESSION"` for the 1b overlap-guard block), not `prev.get("handler")` -- so the very next sweep
after a human reroutes a detector-owned order back to whatever rung the detector originally used,
silently overwriting the reroute. `found_by` is likewise fully replaced by the fresh call's
`found_by` string rather than appended-to, so the `"| rerouted X -> Y by Z: why"` note `reroute()`
attached is deleted in the same write, and `evidence` (already named in the order's own title) is
replaced wholesale too.

**Confirmed exact code path.** The clobber happens on the NEXT `file_order(...)` call for the same
`order_id(code, where)` -- i.e. the next time `sweep_detectors()` runs and that detector is still
unhealthy. It is not conditional on anything a caller can opt out of; every detector-owned code in
`sweep_detectors()` (all twelve `_fire` sites, including the new 1b overlap guard) goes through
this same `file_order` refresh path.

**Confirmed no OTHER human-settable field escapes this.** Grepped this module for every place a
field on an *existing* order record is set: `reroute()` sets `handler` and appends to `found_by`
(both clobbered, as above); `resolve()`/`resolve_code()` **delete** the record entirely (not
applicable to a refile, since a deleted order's next `file_order` call finds `prev = {}` and is a
legitimate fresh filing, correctly distinguished from a clobber by `ghost_orders()`). No function
in this module ever sets `severity` on an existing order (`grep '\["severity"\] *='` finds only a
read at `open_orders()` line 798). So the full set of fields a human can attach to a *still-open*
order is exactly `{handler, found_by-note}`, both of which `file_order`'s refresh clobbers, plus
`evidence`, which is already named in the order's own title
(`A_DETECTOR_REFILE_WIPES_A_REROUTE_AND_ITS_EVIDENCE`). Nothing new to add to the order's remedy.

Verdict: **KNOWN(066bfb187bd1)** -- confirmed against source, no additional clobbered field found
beyond what the order's own title already names.

### Nothing found wrong in the "1b. the overlap guard" block (run #56 addition)

**Where:** `src/workorders.py:1229-1250`.

```python
    try:
        import runguard as _RG
        _gf = _RG.guard_fault()
        _fire(_gf is None, "MAINTENANCE_GUARD_DISAGREES_WITH_THE_PROCESS_TABLE",
              _gf or "", "SESSION", "MAJOR", where="state/MAINTENANCE_RUN.json",
              found_by="runguard.guard_fault")
        _detector("runguard", True)
    except Exception:
        _detector("runguard", False)
```
This follows the same shape as every other detector in `sweep_detectors()`: `_fire`'s `ok`
predicate (`_gf is None`) is TRUE exactly when `runguard.guard_fault()` reports no disagreement,
matching the polarity contract documented at the top of `_fire` (net-checked by
`drill.py`'s `SWEEP_FIRE_POLARITY`, per the docstring); the `except Exception` arm routes an
import/call failure to `_detector`, which files `DETECTOR_FAILED` with a full traceback rather
than reading a broken detector as a clean area (same pattern as every other section). Read
`runguard.guard_fault()` (src/runguard.py:296-360, not one of this batch's assigned modules, but
directly relevant to auditing this block) to check whether `None` conflates "healthy" with "could
not tell": it does, deliberately and by explicit owner-level design documented in its own
docstring -- `None` is returned both for "no discrepancy" and for every "could not compare" case
(no int pid, unreadable process table, no heartbeat), and the docstring explains at length why the
opposite arm (fresh heartbeat + dead pid) was tried, measured against a live run, and *removed*
because the guard's holder is an ephemeral process rather than one long-lived interpreter, so a
dead pid proves nothing. This is a considered, documented trade-off (silence on "cannot tell",
because a detector that fires on unknown is noise that gets switched off) rather than an
undisclosed fail-open path. **Nothing found wrong in this block.**

### Nothing else found wrong in `sweep_detectors()`, `_load`/`_mutate`'s CAS, `resolve`/`reroute`'s
"did it land, then did it exist" ordering, or the twelve `_fire` predicates' polarity (re-verified
by hand against what each one watches: `not bad`, `chain_ok`, `_gf is None`, `n <= CEILING`,
`not hits` gated on `scanned`, `f is None` in the `BATTERY_CODES` loop, `not stranded`,
`not scratch`, `not _cap["open_hits"]`, `not _ghosts`, `not _stuck`, `not _cites` -- every one
TRUE only when the watched condition is healthy).

---

## liveness.py

Read all 1,054 lines: the three mechanical passes (DEAD/DEAD_CLASS/DEAD_MODULE, TAUTOLOGY,
PHANTOM) in `scan()`, the receiver-aware attribute credit machinery (`_credit_attrs`,
`_scope_aliases`, `_self_attrs`), and the `reachability()` gate-coverage measurement plus `main()`.

**Nothing found wrong.** This module is unusually heavily self-audited already -- nearly every
paragraph documents a specific prior defect (tautological round-trips, receiver-blind attribute
credit, module-blind bare-name credit, the `os.walk` vs `os.listdir` directory-descent bug already
fixed here at `_modules()`, the always-true `if seen else set()` branch, the coverage-package
shadowing hazard in `reachability()`) and states its own remaining honest limits out loud
(PHANTOM's module-wide scoping is a declared under-report, ratcheted rather than silently
sharpened; TAUTOLOGY is declared syntactic-only and known not to catch the semantic `profile.py`
shape that motivated the module). No new dead/tautological/phantom-guard shape was found in this
file's own source, and no gap in its documented honesty was found.

---

## catalogue_web.py

Read all 785 lines: `catalogue_composite`, `catalogue`, `save_roll`'s roll-merge CAS, and `main`'s
threaded per-source loop including the write-verdict gating on both the record write
(`pipeline.write_record_catalogue`) and the roll write (`roll.update_rows`).

**Nothing found wrong.** Hard Rule 0 (`MAX_PER_SOURCE`/`MAX_PER_CATEGORY`/`CATEGORY_SCAN_DEPTH`
all `None`, with an import-time tripwire raising `SystemExit` if any is ever reintroduced),
truncation-marker discipline (`_note_bits`, the dedup/no-text provenance sentences), the
`record_path`/`slug` import from `catalogue_aurora` (avoiding a second slug implementation that
could drift, per the Roger Rabbit incident this file's own comments describe), and the write-gate
ordering (record write checked before `roll_by_name[name]` is updated, roll write checked before
counting `done`) were all read and are consistent with what the comments claim. `main()`'s exit
code correctly returns 1 on any per-source failure, not only total failure (order ea1a063d75d6).

## manifest_builder.py

Read all 670 lines: `load_record`'s fuzzy record-matching (`MIN_INEXACT_LETTERS` floor),
`pack_feats`'s pagination-not-truncation of oversized entities, `build_jobs_for_source`'s Feats
chapter (the `binding` out-channel distinguishing `unbound`/`pages`/`doc`/`bound`), and `main`'s
volume-numbering-over-`numbering_pool`-not-`build_pool` fix plus both atomic writes (manifest and
`unassigned_sources.md`).

**QUESTION -- `load_record`'s reverse fuzzy-match arm is free containment, not prefix-anchored,
despite the docstring's framing.** `src/manifest_builder.py:118`:
```python
        if norm_target in norm_fname or norm_target.startswith(norm_fname):
```
The docstring above this (lines 72-105) says "THE REVERSE ARM IS PREFIX-ANCHORED, NOT FREE
CONTAINMENT" -- but that sentence is talking specifically about the *added* `.startswith()` arm
(the fix for the Roger-Rabbit-style truncation case), not about the pre-existing `in` arm, which
*is* free containment and is retained (per the opening paragraph, "the containment runs both
ways"). For a target/filename pair both at or above `MIN_INEXACT_LETTERS` (12 normalised
characters) with no exact match, a target name that happens to appear anywhere inside an unrelated,
longer filename would still match via `norm_target in norm_fname` -- structurally the same
DC-swallows-Sword-Coast accident `address.py` was fixed for twice, which this function's own
opening paragraph cites as the reason for anchoring. The floor and the closeness-ranking
(`score = abs(len(norm_fname) - len(norm_target))`, smallest wins) mitigate this today (the
comments report 214/215 sources resolve by exact equality, and no live misfire was found by
inspection of the current `data/records/` roster) but the general vulnerability for a future
12+-character source name is not closed by this arm, only by the ranking picking a closer match
if a genuinely correct one exists on disk. Not verified as a live misfire against today's data
(that would need enumerating every records-directory filename pair, which is out of this audit's
budget) -- flagged as a QUESTION for a ruling on whether the forward `in` arm should also be
anchored (e.g. to a trailing/leading boundary) or whether the current floor is judged sufficient.

Everything else in this module: **nothing found wrong.**

## worldseed.py

Read all 532 lines: the four feature-axis regex tables and `_first`'s attested-vs-seeded
provenance tagging, `to_options`'s band parsing (the `unassayed`/`unparsed`/`out_of_range`/`ok`
`band_provenance` states), `build_all`'s ONOMASTICON/CONTINUITY_GROUPS failure reporting via
`LAST_BUILD`, and `main`'s uncapped distribution printing and gated `WORLDSEEDS.json` write.

**Nothing found wrong.** The "primitive" unreachable-tech-key marking (owner ruling 2026-09-08,
order 40e98eed6870) is present and complete in this file at lines 217-244 -- see the burgs.py
finding below for the half of that same ruling this file explicitly says is "that module's to
mark" and which has not been done.

## burgs.py

Read all 432 lines: `burg_count`/`largest_city`'s rank-size derivation, `class_histogram`'s
closed-form-plus-correction rank counting, `burgs_for`'s limit-may-only-narrow guard, and `main`'s
parameters-not-rosters accumulation (order 47e4e1ace8f1) and both write paths.

### NEW DEFECT -- burgs.py owes (and has not written) the unreachable-key marking comment
`worldseed.py` explicitly assigns it

**Where:** `src/burgs.py:126,132,134` (`largest_city`'s `base` dict and both `factor` dicts;
`burg_count`'s `factor` dict) vs `src/worldseed.py:237-244`.

`worldseed.py`'s own comment, recording owner ruling 2026-09-08 (order 40e98eed6870, "Mark and
keep: one line each, delete nothing"), says explicitly:

> "the twin unreachable keys in burgs.py (largest_city's 'primitive', and 'settled' in both
> condition tables) are the same ruling and are that module's to mark."

Checked against the live catalogue-derivation path: `worldseed.py`'s `TECH` table (lines 95-100)
has exactly four entries (spacefaring/industrial/magical/medieval) and no route to "primitive";
its `CONDITION` table (lines 90-94) has exactly three entries (ruined/wartorn/thriving) and no
route to "settled". Since `burgs.world_parameters` derives `era`/`cond` from
`features.get("tech", "medieval")` / `features.get("condition", "settled")` where `features` is
always `worldseed.features()`'s output when called from the normal `WS.build_all()` -> `burgs.py`
path, `largest_city`'s `"primitive": 2500` key (line 132) and the `"settled"` key in both
`factor` dicts (lines 126 and 134) can never be selected via that path -- exactly the "unreachable
dict entry" shape this module's whole subject (checks/values that cannot fire) exists to catch,
and exactly the ruling `worldseed.py` says is `burgs.py`'s own to record.

Grepped `src/burgs.py` for any such marker: `primitive` appears exactly once (line 132, the bare
dict literal, no comment at all); `settled` appears in the two `factor` dicts (lines 126, 134)
plus two unrelated prose uses ("medieval/settled world" at line 251, "`suppressions._preview`
settled" at line 375) -- neither a marking comment. **The ruling `worldseed.py` names as owed has
not been carried out**, more than two weeks (order-numbering distance) after the ruling that
assigned it. This is not a functional bug (the values are cosmetically present, harmlessly unused)
but it is exactly the "check that cannot fail, undisclosed" shape the sweep brief calls out, made
worse by the fact that the codebase has *already ruled* that it must be disclosed and the
disclosure was never written.

Everything else in this module: **nothing found wrong.**

## deprecated/catalogue_local.py

Read all 333 lines. Confirmed the module-level refusal is unconditional and structural: lines
91-94,
```python
if set(sys.argv[1:]) & {"-h", "--help"}:
    print(_REFUSAL)
    raise SystemExit(0)
raise SystemExit(_REFUSAL)
```
sits before any config read, any network call, or any file touch, and the only exemption
(`--help`/`-h`) touches nothing. The comment block above it (lines 43-78) enumerates six specific,
deliberately-unrepaired defects in the code below the guard (non-atomic roll rewrite inside the
per-source loop, a bare `main()` returning `None` so the process always exits 0, the `[:60]` slug
truncation, a failed Ollama call recorded as `per_cat[key] = 0` with no note, a third writer
against the `data/records/` two-writer contract, no `silence`/escalation/export-copy machinery)
and states plainly that these are kept as the historical record of a failure mode, not repaired.
Read the whole 333 lines to confirm nothing below the guard is reachable by any path this audit
could find (no other module imports anything from this file; `sys.path.insert` at line 96 runs
only after the two `raise SystemExit` calls above it, so even that has no effect on any real
invocation). **The guard was not tested by attempting to defeat it (per the sweep's rules), and
nothing found wrong** -- the six known defects below the guard are already fully disclosed in the
file's own header and are explicitly out of scope for repair by owner ruling.

## citecheck.py

Read all 260 lines: `CITATION`'s regex, `_PATH_LEAD`'s directory-prefix skip, `_classify`'s three
provable-break reasons, `_self_citation_ok` (currently a hard `False`, i.e. grants no exemption),
and `stale_citations`'s default file-listing and per-line scan.

### CONFIRMED — KNOWN(9daa719e4819): `_PATH_LEAD` skips any `src/`-prefixed citation uncounted

**Where:** `src/citecheck.py:73` (`_PATH_LEAD = ("/", "\\")`), applied at
`src/citecheck.py:189-190`:
```python
                if m.start() > 0 and raw[m.start() - 1] in _PATH_LEAD:
                    continue
```
Confirmed exactly as filed: `CITATION`'s regex (line 63) only captures the bare filename
(`[A-Za-z_][A-Za-z0-9_]*\.py`), never a leading path segment, so a citation written
`src/liveness.py:197` matches starting at `liveness.py` with a `/` immediately before the match --
indistinguishable, by this purely syntactic test, from a genuinely foreign-tree citation such as
`cascade/engine.py` or `motoko/discord_bot.py`. It is `continue`d before ever reaching `_classify`,
so it is not counted as UNRESOLVED, not counted as CLEAN, and does not appear in `stale_citations`'
output at any verbosity. Verdict: **KNOWN(9daa719e4819)**, re-confirmed against live source this
run (not merely cited from the prior sweep's finding).

### NEW DEFECT -- a second, distinct undercount: `stale_citations()`'s default file list does not
descend into `src/deprecated/`, so citations written inside it are never scanned as CITING text,
and the same non-recursive resolution means a citation naming a file that genuinely lives in
`src/deprecated/` can never resolve as CLEAN under either spelling convention

**Where:** `src/citecheck.py:175-177` (the default path listing) and `src/citecheck.py:131`
(`_classify`'s single-directory target resolution).

```python
    root = src_dir or SRC
    if paths is None:
        paths = sorted(os.path.join(root, f) for f in os.listdir(root) if f.endswith(".py"))
```
`os.listdir(root)` enumerates only the direct children of `src/` and does not recurse into
subdirectories -- `src/deprecated/` (currently holding `catalogue_local.py`, README aside) is
invisible to this listing, exactly as it was to `liveness.py`'s `_modules()` before that was fixed
(order aeeba9364147), to `sweep_plan._src_py_files` (order f42c55355431), and to
`drill._src_py_files` (order cf9ee9000be8) -- `liveness.py`'s own docstring at
`src/liveness.py:120-129` calls that combination "the third occurrence of the same defect class"
and names both prior fixes; `citecheck.py`'s unfixed `os.listdir` is a fourth, still-live instance
of the identical mechanical mistake. Concretely, this means:

  1. **As a citing source**: any `file.py:NNN`-shaped comment written inside
     `src/deprecated/catalogue_local.py` (or any future file placed under a `src/` subdirectory)
     is never scanned by `stale_citations()` at all -- it is not in `paths`, so the outer loop at
     line 179 never opens it. Checked against the live file: `catalogue_local.py` currently
     carries no such citation (`grep -n '\.py:[0-9]' src/deprecated/catalogue_local.py` -> no
     hits), so there is no live undercount from this file TODAY, but the detector's coverage is
     silently incomplete regardless of what is in that file this week, which is the same "a
     subdirectory nothing can see reads exactly like a clean one" shape `liveness.py`'s own
     comment names for the identical mistake.
  2. **As a citation TARGET**: `_classify` resolves a cited module with
     `target = os.path.join(src_dir or SRC, target_name)` (line 131) -- a single join against the
     top-level `SRC`, never searched recursively either. A citation to
     `deprecated/catalogue_local.py` is skipped uncounted via the `_PATH_LEAD` bug above (its
     `/` prefix). A citation to the SAME real, in-tree file spelled WITHOUT the directory
     (`catalogue_local.py:280`) would NOT be skipped by `_PATH_LEAD` (no leading slash), but
     `_classify` would look for it at `src/catalogue_local.py` -- which does not exist, since the
     real file is one level down -- and report it `UNRESOLVED`, even though the file is real,
     in-tree, and resolvable by `liveness.py`'s own (recursive) module lister one file over. So a
     genuinely broken citation into `src/deprecated/` (a blank line, past-EOF, or bare-bracket
     target) can be filed under NEITHER spelling: the directory-prefixed spelling is swallowed by
     `_PATH_LEAD` as "another tree", and the bare-filename spelling is reported as merely
     unresolved rather than checked, so `src/deprecated/` is a blind spot for this checker under
     both conventions.

Not a large live population today (one file, zero live citations found in it by grep), but it is
the same silent-completeness-gap shape as the `_PATH_LEAD` finding immediately above and as three
prior, now-fixed instances elsewhere in this tree, and it compounds with `_PATH_LEAD` rather than
being an alternate description of the same bug: fixing `_PATH_LEAD` alone (to stop skipping
`src/`-relative citations) would not fix this, because the file listing itself never offers
`src/deprecated/catalogue_local.py` as a citing path, and `_classify`'s target join would still
need to search more than one directory to resolve a bare-name citation into it.

Everything else in this module (the three provable-break reasons, the placeholder/self-citation
exemptions, `report`/`summary`): **nothing further found wrong.**

## whoruns.py

Read all 159 lines: `script_of`'s interpreter-flag walk (including the `-X`/`-W` value-consuming
arm and the `-m`/`-c` short-circuit), `running`'s tri-state (None = unmeasurable, distinct from an
empty list) and its `this_tree_only` sandbox-exclusion, and `main`'s grep-style exit codes.

**QUESTION -- a display-only cap with no disclosure marker, unlike the pattern this codebase
otherwise applies to display truncations.** `src/whoruns.py:154`:
```python
                print("   %-7d %s" % (pid, cmd[:150]))
```
`cmd` (the full matched process's command line) is sliced to 150 characters for the console table
with no "+N chars" or similar marker, unlike, e.g., `workorders.py`'s `_what` display line
(`src/workorders.py:2142-2145`), which cuts similarly but appends
`"... (+%d chars -- the whole finding is on order %s)"`. This is a `main()`-only CLI print (the
full, uncut `cmd` is still returned in full by `running()` for any programmatic caller), so it is
lower-stakes than a Hard-Rule-0 catalogue-data cap -- flagged as a QUESTION rather than a DEFECT,
since it is plausibly an intentional console-only convenience this codebase's own doctrine treats
as reversible ("the console renderers already truncate for display at their own call sites...
which is where a cap belongs, because it is reversible there" -- `workorders.py:544-546`) rather
than an oversight, but it is inconsistent with the marker convention several sibling call sites in
this same tree now follow.

Everything else in this module: **nothing found wrong.**
