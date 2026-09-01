# Sweep 40, batch 16 — audit

Modules read in full: `src/binding_health.py` (1218 lines), `src/local_agent.py` (1212 lines,
NOT executed per instructions), `src/catalogue_web.py` (630 lines, `--recatalogue` NOT run per
instructions), `src/weave_index.py` (516 lines), `src/anchors.py` (457 lines), `src/grounding.py`
(334 lines), `src/resync_roll.py` (287 lines), `src/descending_ladder.py` (226 lines).

All eight files are heavily self-documented with prior fixes (order IDs, "found by run #NN"
comments). Most candidate issues on first read turned out to already be the fix for an earlier
defect, correctly done. Four real findings survived verification against the source.

---

## Finding 1 — resync_roll.py: "(pre-fix figures)" is actually post-fix, unlanded figures

**File:** `src/resync_roll.py`
**Lines:** 131–135, 162–168 (the premature mutation) and 260–265 (the mislabelled print)
**Severity:** MAJOR
**Handler:** LOCAL

`main()` loads the roll once (line 56), then loops over it:

```python
131        if r.get("entry_count", 0) != n:
132            changed.append((r["name"], r.get("entry_count", 0), n, fn))
133            if not dry:
134                r["entry_count"] = n
135                repairs.setdefault(r["name"], {})["entry_count"] = n
```

and similarly for `status` at lines 166–168. This mutates the **local, in-memory** `roll` rows
directly, *unconditionally* whenever `not dry` — regardless of whether the later disk write
succeeds. The disk write itself goes through `roll.mutate()` (compare-and-swap, re-reads fresh
from disk), landing only the `repairs` dict, not this local `roll` list.

When that write is refused (`landed=False`, e.g. a Windows reader holding the file open), the
script hits:

```python
260    if not dry and not landed:
261        print(f"\nWRITE DENIED {ROLL} -- replace refused; roll is UNCHANGED on disk, "
262              f"the fixes above did not land and will retry next run")
263        have = sum(1 for r in roll if r.get("entry_count", 0) > 0)
264        print(f"\nroll unchanged: {have}/{len(roll)} sources catalogued (pre-fix figures)"
265              + caveat)
266        return 1
```

`have` is computed from `roll` — the same list that lines 133–135/166–168 already mutated to
hold the **new** (would-be) `entry_count`/`status` values. So a row whose fix did NOT land on
disk (per the "WRITE DENIED... roll is UNCHANGED on disk" message immediately above) is counted
here as if it HAD landed, and the whole line is captioned "(pre-fix figures)" — the opposite of
what it actually shows. A reader gets: "the disk is unchanged" and then a headline number that
is quietly the POST-fix count, mislabelled as the PRE-fix one.

Concretely: if source X had `entry_count: 0` on disk before this run, and this run's record scan
finds 500 entries for X, then (not dry) `r["entry_count"]` is set to 500 in the local `roll`
row immediately — before the CAS write is even attempted. If that CAS write is then denied, disk
still holds `entry_count: 0` for X, but the "pre-fix figures" line counts X as catalogued (>0)
anyway.

**Remedy:** snapshot the true pre-fix state before mutating any row (e.g.
`pre_have = sum(1 for r in roll if r.get("entry_count", 0) > 0)` right after `roll = json.load(f)`
at line 56), and use that snapshot — not the now-mutated `roll` — in the write-denied branch at
line 263. Alternatively, defer mutating `r` in place until after `_roll.mutate()` reports
`landed=True` (the `changed`/`relabelled` tuples used for the diff printout above already carry
old/new values independently of `r`, so nothing else in the function depends on the early
mutation).

---

## Finding 2 — catalogue_web.py: main() never signals failure; process always exits 0

**File:** `src/catalogue_web.py`
**Lines:** 494 (`def main():`) through 626 (end of function body, no `return`), and 630
(`if __name__ == "__main__": main()`)
**Severity:** MAJOR
**Handler:** LOCAL

`main()` has no `return` statement anywhere in its body (verified: `grep -n "return " src/
catalogue_web.py` shows no hits inside `main`'s line range). It ends after:

```python
623    with ThreadPoolExecutor(max_workers=3) as ex:
624        list(ex.map(_one, todo))
625
626    print(f"Catalogued {tally['done']}/{len(todo)} sources ({tally['failed']} skipped).")
```

and `__main__` calls it bare:

```python
629 if __name__ == "__main__":
630     main()
```

with no `sys.exit(...)`. So the process exits 0 unconditionally — even when every source in
`todo` fails (`tally['failed'] == len(todo)`, `tally['done'] == 0`), even when `--dry-run`
resolves nothing, even when `_one()` catches an exception for every source.

This is exactly the defect class this codebase has independently found and fixed in its sibling
cataloguers and reporting scripts: `resync_roll.py`'s own `__main__` comment ("THE EXIT CODE IS
THE NUMBER THE SCHEDULER ACTUALLY LOOKS AT -- generate.py, weave_index.py, sweep.py, feats.py and
handbuilt.py all say so at this same line") explicitly lists sibling modules that got this fix;
`catalogue_web.py` is not on that list and was never fixed.

It matters concretely here: `src/foreman.py`'s `run_catalogue_gap()` dispatches this exact script
in the background via `overnight.start(...)` (`foreman.py:919`, `["src/catalogue_web.py",
"--recatalogue", "--shortfall", "1", "--only", ...]`), and `overnight.join()`
(`src/overnight.py:640-652`) is the mechanism that later checks `job["proc"].returncode`: on
`rc != 0` it tails the job's log for a person to see and reports `f"rc={rc}"`; on `rc == 0` it
reports `"ok"` unconditionally. Because `catalogue_web.py` never returns nonzero, a dispatch that
failed on every one of its targeted sources (network down, every wiki unresolved, every write
denied) is reported to the operational log as `"ok"` — silently defeating the exact monitoring
this codebase built `name_rc`/`join()` to provide.

**Remedy:** have `main()` return an exit code (e.g. `return 1 if todo and tally['failed'] ==
len(todo) else 0`, or more strictly `return 1 if tally['failed'] else 0`) and wrap the
`__main__` call as `sys.exit(main())`, matching the pattern already used in `resync_roll.py`,
`weave_index.py`, `grounding.py`, `anchors.py`, and `binding_health.py` (all audited in this
same batch).

---

## Finding 3 — catalogue_web.py: stale cross-reference, all three citations wrong

**File:** `src/catalogue_web.py`
**Line:** 590 (comment spanning 588–590)
**Severity:** MINOR
**Handler:** LOCAL

```python
588            # GATE ON THE WRITE, like every other caller. write_record_catalogue returns whether
589            # the rename LANDED, and it returns it precisely so a denied write is not recorded as
590            # done (pipeline.py:381-396; pipeline.py:641 and ingest_doc.py:246 both check it).
```

Verified against current `src/pipeline.py` and `src/ingest_doc.py`:

- `pipeline.py:381-396` is inside `ask_pool_first()` (defined at pipeline.py:355), specifically
  the cloud-pool-first fallback-to-local logic — unrelated to `write_record_catalogue` or its
  return value. `write_record_catalogue` is actually defined at `pipeline.py:515`, and the
  "returns whether the rename LANDED" logic the comment describes is `_landed()` at
  `pipeline.py:609-624` ("Rename `tmp` over `path`, and SAY whether it actually happened.").
- `pipeline.py:641` is inside `mark_done()` (defined at pipeline.py:627) — the phase-completion
  marker helper, unrelated to record writes. `grep -rn "write_record_catalogue(" src/*.py`
  confirms `pipeline.py` itself never calls `write_record_catalogue` at all (only defines it), so
  no line in `pipeline.py` can be a "caller that checks it".
- `ingest_doc.py:246` is inside `mine()`'s docstring/corpus-existence check, unrelated. The actual
  call site that checks `write_record_catalogue`'s return value is `ingest_doc.py:395`
  (`if not P.write_record_catalogue(rp, rec):`), per the same grep.

All three citations point at unrelated code; a reader following any of them to verify the claim
lands in the wrong function.

**Remedy:** update the comment to cite `pipeline.py:515` (or `:609-624` for `_landed`
specifically) and `ingest_doc.py:395`, and drop the `pipeline.py:641` citation entirely (no such
caller exists) or replace it with another real caller from the grep list above (e.g.
`catalogue_aurora.py:261`, `catalogue_codex.py:329`, `backfill.py:275`, `drill.py:3510`).

---

## Finding 4 — anchors.py: stale cross-reference, both citations off by exactly 16 lines

**File:** `src/anchors.py`
**Lines:** 246–247
**Severity:** MINOR (INFO-leaning — a reader landing nearby would still find the real text a few
lines down)
**Handler:** LOCAL

```python
246    # `assay.assay` has two documented paths that return `decimal: None` with a reason -- no
       # worksheet (assay.py:886, honesty theorem H5) and "no axis scored from cited feats;
       # band-only"
247    # (assay.py:897). The first is unreachable here because every call passes
```

Verified against current `src/assay.py`:

```
900:        # H5 of X.6: no worksheet, no number. Thin attestation yields a band window.
902:                "reason": "no worksheet supplied; band-only per honesty theorem H5"}
913:                "reason": "no axis scored from cited feats; band-only"}
```

The two reasons actually live at `assay.py:902` and `assay.py:913` — both cited line numbers in
`anchors.py` are low by exactly 16 lines (consistent offset, i.e. one edit inserted 16 lines
above `assay.py:886` at some point after this comment was written, and the comment was never
updated).

**Remedy:** update the citations to `assay.py:902` and `assay.py:913`.

---

## Not findings (checked and cleared)

- `src/descending_ladder.py` — `rung_for_length`'s domain bounds, the Fold threshold, and the
  transit-energetics functions (`compton_confinement_energy`, `density_at_scale`,
  `schwarzschild_radius`, `shrink_report`, `transgression_bits`) were all checked against the
  physics they claim (Planck energy, covalent/ionisation/nuclear binding energies, proton rest
  mass) and matched. `shrink_report`'s `is_descent` flag is reported, not enforced, exactly as
  its docstring states.
- `src/grounding.py`, `src/weave_index.py` — both already carry extensive, verified Hard-Rule-0
  fixes (uncapped rankings, uncapped runners-up, gated writes with CAS where needed); no
  additional tautologies, silent caps, or discarded return values found.
- `src/binding_health.py`, `src/local_agent.py` — both extremely heavily hardened (five to six
  documented bypass-class fixes each for `local_agent.py`'s path-safety gate alone). Full read
  found no new tautological checks, fail-open paths, or discarded verdicts; every write path
  (`quarantine`, `release`, `run`'s merge) already uses digest-before-read CAS correctly.
- `src/weave_index.py`'s citation of `health.py:576-585` (in the "most cross-attested entities"
  comment) points about 13 lines above the actual ruling text (`health.py:589-599`, "it must be a
  RANKING plus a stated floor, never a prefix of a glob") — same general paragraph/function,
  materially less misleading than Findings 3/4 above, so not filed separately; noted here for the
  record.

## Coverage

`sweep_plan.record('run40', [...8 modules...], batch=16)` called; see `data/sweep_shards/`.
