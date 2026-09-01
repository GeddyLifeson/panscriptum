# Sweep 40, batch 10 — audit

Modules read in full: `overnight.py` (1543 lines), `escalation.py` (821 lines),
`scout.py` (667 lines), `liveness.py` (554 lines), `tiers.py` (426 lines),
`cosmography.py` (335 lines), `wh40k.py` (301 lines), `physics.py` (246 lines).

Context: `state/MUTATION_ACTIVE.json` shows a live mutation run targeting
`assay.py`, `prose_gate.py` and `escalation.py` at the time of this audit.
`escalation.py` was read twice (a plain read and a second `sed` spot-check of
lines 55-80) and was consistent both times — no corruption observed, and
nothing here treats a transient mutation artefact as a finding.

This batch's modules turn out to have already been through several prior
sweep passes (workorder codes already on file include `OVERNIGHT_*`,
`SCOUT_*`, `TIERS_*`, `WH40K_*`, `PHYSICS_*`, `COSMOGRAPHY_*`, `LIVENESS_*`,
and a `sweep39-batch10` audit of this exact module set). Before filing
anything, every candidate finding below was checked against
`state/workorders.json` (453 existing orders) to avoid re-filing. Several
strong candidates turned out to be already filed — see "Checked and already
on file" below. Two genuinely new, verified findings remain.

## 1. New findings

### 1.1 `liveness.py:154` cites `escalation.py:64` for `class Refused` — now at `escalation.py:75`

`liveness.py`'s `_classdefs()` docstring (lines 150-158) uses the escalation
chain's `Refused` exception as its worked example of a class the DEAD-CLASS
pass now catches:

```
    measured over this tree, `escalation.py:64 Refused` -- "An OPERATOR- or
    SUPERVISOR-level stop: this unit or this source, not the library" -- is
    never raised, caught, imported or named anywhere in src/, ...
```

Verified against the current `escalation.py` (read in full, then
double-checked with a targeted `sed -n '55,80p'` for consistency under the
active mutation run): line 64 is

```python
HALT_REFUSAL = "THE LIBRARY IS HALTED"
```

`class Refused(RuntimeError):` is at **line 75**, eleven lines below the cited
number. The drift is explainable and not mysterious — the eight-line
`HALT_REFUSAL` provenance comment (lines 56-63, "THE SENTENCE A HALT REFUSES
WITH...") was evidently added above the class block after this citation was
written, pushing everything below it down. The underlying claim (`Refused`
has no raiser anywhere in `src/`) is still true — confirmed independently
with `grep -rn "Refused" src/` — and is separately tracked by open order
`ESCALATION_REFUSED_IS_DECLARED_WITH_NO_RAISER`. What is new here is narrower
and mechanical: the **line number** in `liveness.py`'s own citation has
rotted, in the module whose entire subject is catching exactly this class of
decay elsewhere in the tree.

**Remedy:** repoint the citation to `escalation.py:75`, or better, cite it
structurally (`class Refused`, no line number) the way `dashboard.py:77-80`'s
own rule already argues for — "a baked-in line number rots the moment
anything above it moves."

**Filed:** `LIVENESS_STALE_XREF_ESCALATION_REFUSED_LINE`, MINOR, handler LOCAL.

### 1.2 `overnight.py` cites two `health.py` line numbers that have both drifted

Two separate citations inside `overnight.py`'s `preflight()`, both pointing
at `health.py`, both now wrong:

**(a) `overnight.py:967`** (inside the `blocking` label-pinning comment):

```
    # -- the label is `health.CHECKS[0][0]` and the two-space "  FAIL  {label}" is health.py's
    # print format (health.py:840), and NOTHING pinned either. ...
```

Current `health.py:840` is inside the middle of the `preflight()` docstring
("reported only to a terminal: ..."), not a print statement. The actual FAIL
print format is at **`health.py:864`**:

```python
                print(f"  FAIL  {label}")
```

**(b) `overnight.py:1009`** (inside the "a preflight that died mid-run" comment):

```
    # a clean run. health.py's contract is `return 1 if n else 0` (health.py:780), so a
```

Current `health.py:780` is a line inside an unrelated repair-tool comment
block (`missing = sum(1 for e in E[start:start + B] if not P.entry_settled(e))`
context). The actual contract line is at **`health.py:926`**:

```python
    return 1 if n else 0
```

Both citations are off by a similar mechanism to 1.1 — `health.py` grew
between when these comments were written and now (the preflight docstring
alone gained the paragraph now sitting at line 840). Checked against
`state/workorders.json`: an existing order (`STALE_XREF_ALLSWEEP_OVERNIGHT`)
covers a *different* stale citation — `allsweep.py:674` pointing at
`overnight.py:961` — and does not touch either of these two `overnight.py →
health.py` citations, so this is not a duplicate.

**Remedy:** repoint to `health.py:864` and `health.py:926` respectively, or
cite by content (`health.CHECKS`'s print line; `health.preflight`'s return
line) rather than by number.

**Filed:** `OVERNIGHT_STALE_XREF_HEALTH_LINES`, MINOR, handler LOCAL.

## 2. Checked and already on file (not re-filed)

For completeness, and so the next batch doesn't re-discover these: every one
of the following was independently found while reading this batch's modules,
verified against source, and then found already tracked in
`state/workorders.json` under an open order with no duplicate filed:

- `liveness.py:187` cites `entity_match.py:88 Resolver.rebuild()` as a worked
  example of a dotted-path report line. No `Resolver` class or `rebuild`
  method exists anywhere in `entity_match.py` (its only class is
  `MatchReason`, a bare constant namespace at line 75). Already filed as
  `LIVENESS_PHANTOM_ENTITY_MATCH_CITATION`.
- `tiers.py:310-312` cites `weave.py:478`, `pipeline.py:1795` and
  `cosmology_graph.py:86` for the "WHOLE list, Hard Rule 0" ruling on the
  `shared_sample` key. All three have drifted (real locations: `weave.py:519`,
  `pipeline.py:2375`, `cosmology_graph.py:~116/209`). Already filed as
  `STALE_XREF_SHARED_SAMPLE` (which explicitly names `tiers.py:309-313` as
  one of the citing sites), and again independently as `STALE_LINE_CITATION`
  and `COSMOLOGY_GRAPH_FOUR_STALE_CROSS_REFERENCES`.
- `escalation.py:64` as a citation target is also referenced (accurately, at
  time of filing) inside `ESCALATION_REFUSED_IS_DECLARED_WITH_NO_RAISER`'s
  own evidence and `Q_BATCH10_THREE_RULINGS_OWED`'s Q2/Q3; neither of those
  is a duplicate of finding 1.1 above, which is specifically about
  `liveness.py`'s own citation having rotted.
- `wh40k.py:276` cites `zfighters.py:478` for "the same reason and by the
  same hand" as its own atomic/gated write. Already filed as
  `STALE_XREF_WH40K_ZFIGHTERS_LINE`.
- `wh40k.py --full` never prints the per-axis provenance tag
  (`d["axes"][ax]["provenance"]`) it computes in `compute()`. Already filed
  as `WH40K_FULL_OMITS_THE_PROVENANCE_IT_COMPUTES`.
- `cosmography.py`'s `SIZE_CLASS_MAX_GALAXIES` ceilings make POCKET and MINOR
  refuse unconditionally (2.0e2 and 2.0e5 galaxies against ceilings of 1.0),
  which the module's own comment flags as a charter ruling left deliberately
  for the owner. Already filed as
  `COSMOGRAPHY_SIZE_CLASS_MULTIPLIERS_CONTRADICT_THEIR_DESCRIPTIONS` and
  `Q_COSMOGRAPHY_POCKET_MINOR_ALWAYS_REFUSE`.

## 3. Read in full, nothing new found

- **`physics.py`** — every guard (`kinetic`, `joules_for`, `sphere_volume`,
  `binding_energy`) correctly rejects non-positive, non-finite, and NaN
  inputs, each with a docstring explaining exactly which sibling defect it
  mirrors. `main()`'s `write` path isn't present (it only prints); no
  gate/cap/discarded-verdict issues found. Only pre-existing dead-code note
  (`PHYSICS_HERE_AND_SYSPATH_DEAD`) is already filed.
- **`escalation.py`** — matches every promise in `CLAUDE.md`'s Hard Rule -1
  section: `clear()` is CLI-and-`main()`-gated via `_by_a_person_at_the_cli`,
  every shared-state read-modify-write (`_write_stopped`,
  `stop_subsystem`/`resume_subsystem`) is compare-and-swap with a
  before-the-read digest and a bounded retry count, `_read_halt_raw` and
  `_read_stopped` both fail closed on unreadable/wrong-shape files, and every
  write verdict (`_raise_halt`, `clear`, `_write_stopped`) is checked and
  reported rather than discarded. No new defects found.
- **`scout.py`** — `_mutate`'s CAS, `verify()`'s adaptive `needed` floor,
  `sweep()`'s rotation-not-cap ordering, and the archive-before-trim roll-off
  are all internally consistent with their own docstrings. No new defects
  found.
- **`cosmography.py`** — `kardashev_to_magnitude`'s `reached = None` fix and
  `validate()`'s ratio-vs-absolute distinction both check out against the
  code as written. No new defects found beyond the already-filed owner
  question in section 2.
- **`overnight.py`** — read start to finish including `main()`'s cycle loop,
  the keeper thread, `_guarded_popen`'s lock-serialised check-then-spawn, and
  `name_rc`'s exit-code table. One near-miss investigated and dismissed as
  not a real defect: `start()` returns `None` for three different reasons
  (manager-stopped, blind process-table probe, already-running), and `join()`
  maps any `None` job to the single string `"already-running"` — but every
  caller only ever buckets that string together with `"manager-stopped"` and
  `"probe-blind"` in the `busy` idle-detection check (`overnight.py:1492-1493`),
  and `start()` itself already logs the *real* reason at the point of the
  call, so the mislabelling has no behavioural or diagnostic consequence.
  Not filed.
- **`tiers.py`** — `chart()`'s fail-open-with-a-flag / fail-closed-at-the-writer
  split, `_load_groundings`'s three-state read, and `main()`'s
  write-then-check-the-verdict gate are all consistent with their own
  documentation. No new defects beyond the already-filed stale citations in
  section 2.
- **`wh40k.py`** — `_provenance()`'s default-to-`unattributed` (not `wiki`)
  and `main()`'s gated, atomic `write_json` call check out. No new defects
  beyond section 2.
- **`liveness.py`** — the detector's own three-tier usage model (`used`,
  `used_local`, `scoped` self/cls attributes) and the module/class/function
  DEAD passes all read correctly against the AST-walking code. No new
  defects beyond the two filed above (1.1) and already-filed (2).

## 4. Work orders filed this batch

| code | severity | handler | where |
|---|---|---|---|
| `LIVENESS_STALE_XREF_ESCALATION_REFUSED_LINE` | MINOR | LOCAL | `src/liveness.py:154` |
| `OVERNIGHT_STALE_XREF_HEALTH_LINES` | MINOR | LOCAL | `src/overnight.py:967,1009` |
