# Sweep 40, batch 05 — audit

Modules read in full: `src/cascade_bridge.py` (1957 lines), `src/chain.py` (740 lines),
`src/codewatch.py` (578 lines), `src/policy.py` (476 lines), `src/pick_model.py` (381 lines),
`src/style_audit.py` (308 lines), `src/tuning.py` (272 lines), `src/compress_store.py`
(149 lines), `src/lognames.py` (52 lines).

This is an exceptionally mature, heavily self-audited corner of the tree. Seven of the nine
modules (`lognames.py`, `compress_store.py`, `style_audit.py`, `pick_model.py`, `tuning.py`,
`codewatch.py`, and the large majority of `cascade_bridge.py`) show no live defects — every
cap, gate, cross-reference and discarded-verdict shape this sweep hunts for has already been
found and fixed in place, with the fix and its reasoning left in the comment, and every
`file.py:NNN`-style cross-reference checked against the cited file's actual current line
verified correct (including three references into the sibling `verify_math.py` — sections
`19ac`, `19h`, `19aa` — and one into the external `cascade/engine.py:277,343`). Two real,
verifiable defects were found, both below.

---

## FINDING 1 — three stale self-referential `chain.py:NNN` line-number claims

**File:** `src/chain.py`, lines 364, 371, 449

**Quoted:**
```python
364:        silence.note("chain.py:ask-cloud")   # was `chain.py:155`; the line is now 276
371:        silence.note("chain.py:ask-local")   # was `chain.py:161`; the line is now 283
```
```python
449:                # was `chain.py:252`; the line is now 345
450:                silence.note("chain.py:extract-bad-index")
```

**Verification:** the comments assert the *current* location of these three lines is 276, 283
and 345 respectively. The actual current lines (confirmed by `grep -n` against the live file)
are 364, 371 and 449. Line 276 is inside `harvest()`'s corpus-prune loop (`for rel in [k for k
in idx if k not in live ...`); line 283 is the `if changed:` block that lands the harvest index;
line 345 is inside `entity_index()`'s short-form collision handling. None of the three has
anything to do with `_ask`'s cloud/local fallback or `extract`'s bad-index guard.

**Why it's wrong:** this is the exact defect the file's own neighbouring comment (line 251,
`chain.py:harvest-feats-unreadable`) warns against by name — *"a tag that points at an unrelated
line is worse than an opaque one, because it sends the next reader somewhere confidently
wrong."* These three comments were evidently corrected once (from 155/161/252 to 276/283/345)
when the file was edited, but the file has grown further since and the "now" values were never
re-checked, so they have drifted stale again — the same failure mode recurring after its own
fix, in the same file, three times.

**Remedy:** either update the three comments to the real current line numbers (364, 371, 449),
or — better, and consistent with the fix already applied at line 251 for the same reason — drop
the line-number claim entirely and keep only the historical "was chain.py:NNN" note, since a
"the line is now X" claim will go stale again on the next edit above it.

**Severity:** MINOR — comment-only, no behavioural effect. `handler: LOCAL`.

---

## FINDING 2 — unreadable record files are counted for the console but never land in
`state/policy_report.json`, and never affect the exit code

**File:** `src/policy.py`, `main()`, lines 314–323 (collection) and 396–408 (persistence)

**Quoted (collection, line 314–323):**
```python
    unreadable = []
    all_records = sorted(glob.glob(os.path.join(HERE, "data", "records", "*.json")))
    records = all_records if a.limit is None else all_records[:a.limit]
    for p in records:
        try:
            with open(p, encoding="utf-8") as f:
                evals.append(evaluate(json.load(f), RECORD_RULES, os.path.basename(p)))
        except Exception as e:
            silence.note("policy.py:record-unreadable")
            unreadable.append((os.path.basename(p), "%s: %s" % (type(e).__name__, str(e)[:70])))
            continue
```

**Quoted (persistence, line 396–408 — the `scope` dict handed to `report()`):**
```python
    landed = report(evals, scope={
        "limit": a.limit, "partial": partial,
        "records_total": len(all_records), "records_evaluated": len(records),
        "coverage_total": cov_total, "coverage_evaluated": cov_read,
        "evidence_swept": not a.skip_evidence,
        "evidence_total": ev_total, "evidence_evaluated": ev_read,
        "evidence_passed": ev_passed, "evidence_unreadable": len(ev_unreadable),
        "evidence_stored": len(ev_interesting),
        "evidence_note": (...),
        "records_skipped": [os.path.basename(p) for p in all_records[a.limit:]] if partial else [],
    })
```

**Verification:** `grep -n "unreadable" src/policy.py` shows the record-loop's `unreadable`
list is referenced only at its own collection (314, 322–323) and in the final console
`print()` block (442–445: `if unreadable: print("%d record(s) COULD NOT BE READ ...")`). It is
never passed into `scope`, and no key resembling `records_unreadable` appears anywhere in the
file. Compare the evidence sweep two blocks down, which *does* carry its own unreadable count
into the persisted scope as `"evidence_unreadable": len(ev_unreadable)`. The two sweeps are
handled asymmetrically: one's unreadable count survives the run, the other's does not.

Separately, `main()`'s return code is computed from `failed` (rule failures) and `landed`
(whether the report replace landed) only:
```python
    if failed:
        return 1
    if not landed:
        return 2
    return 0
```
A run in which every readable record passes every rule, but N record files were corrupted or
truncated and never evaluated at all, still returns 0 — "clean" — with no trace of the N
unreadable files anywhere outside that one run's stdout.

**Why it's wrong:** this module's own opening thesis (docstring, lines 9–13) is built entirely
around refusing exactly this shape: *"a rule buried in imperative code can degrade to a no-op
without anyone noticing... this project has hit that shape repeatedly."* `report()`'s own
docstring says its entire reason for existing is the word "later" — `state/policy_report.json`
is described as "the only copy that outlives" the run. A record that could not be parsed is
the single strongest evidence of corpus corruption this run can produce, and it is precisely
the case the module's docstring calls "ABSENT for its whole life" when discussing HIGH guards —
here it is the module doing that to its own finding. Anything that reads only
`state/policy_report.json` after the run (a dashboard panel, a later maintenance pass) has no
way to learn that N records were never looked at; anything that checks only `rc == 0` gets a
clean bill of health for a run that silently skipped part of the corpus.

**Remedy:** add `"records_unreadable": len(unreadable)` (and, for symmetry with the
`evidence_note` field, the filenames/reasons themselves — they are already bounded and short)
to the `scope` dict passed to `report()`, so the persisted artifact carries the same fact the
console does. Whether the return code should also change (a third distinct code, matching the
existing `1`/`2` split rationale in the file) is a judgment call for the owner given the
existing two-code scheme, but the *persisted* gap is unambiguous and should close regardless.

**Severity:** MINOR — the fact is not silently lost (it prints to stdout every run), but it does
not survive the run in the one artifact the module's own docstring says is built to outlive it.
`handler: LOCAL`.

---

## Modules with no findings

- **`lognames.py`** — the `OWNER` dict's five command-fragment claims (`read.py --run`,
  `feats.py --roll`, `pipeline.py --run`, `catalogue_web.py --recatalogue`,
  `magnitude.py --calibrate`) were checked against each target file's actual `add_argument` /
  usage and all five are real, current flags.
- **`compress_store.py`** — the `catalog.py:97` cross-reference (`load()`'s docstring, "when
  catalog.py:97 serves the chapter to a reader") was checked: line 97 is `def cmd_read(...)`,
  which does read `compressed_path` via `compress_store.load()` a few lines further down in the
  same function. Correct.
- **`style_audit.py`** — the `repass_bands.py:106-113` cross-reference for the `_cut()` "house
  line" idiom was checked: that range is the `_survivors_shown = kept_entries[:14]` /
  "showing N of M; K more not shown" block, the same idiom `_cut()` implements. Correct.
- **`pick_model.py`** — `FAMILY_TIERS` ordering (more specific family strings before their own
  prefixes, e.g. `"qwen3"` before the bare `"qwen"` catch-all) was traced by hand against the
  tier-search loop order and produces no cross-tier mis-scores for any family pair actually
  listed. `resident()`'s VRAM-budget gate (against `total - reserve`) and `fit_note()`'s display
  warning (against live free VRAM) are deliberately different measurements for different
  purposes, both explained in comments, and both correct for their stated purpose.
- **`tuning.py`** — the `verify_math S19ac` cross-reference (`workers()`'s docstring) was
  checked: `verify_math.py:2976` opens `# ---- Section 19ac: a worker request is a ceiling at
  every value, including zero`, which is exactly the property the docstring claims is pinned.
- **`codewatch.py`** — `_ledger_lock()`'s `O_CREAT|O_EXCL` mutual exclusion around
  `_take_locked()`'s read-modify-write of the restart ledger is real compare-and-swap (verified:
  the earlier unlocked check-then-take shape this replaced is described and dated in the same
  docstring, order referenced, and the current code path — `_claim_restart_slot` → one
  `with _ledger_lock(): return _take_locked(...)` call — has no gap between check and take).
  `twins()` / `claim_singleton()`'s FAIL OPEN behaviour when `psutil` is missing is explicitly
  and correctly labelled as such in both docstrings, not a mismatch against any fail-closed
  promise.
- **`cascade_bridge.py`** — read in full. The module carries an unusually large number of
  already-fixed-and-documented defects (double-checked-locking races, TOCTOU windows on the
  restart/unrecognised-failure ledgers, classifier word-boundary bugs, truthiness-vs-type bugs,
  a `--help` accidentally spending a live model call) — all with dated orders and, in several
  cases, reproduction numbers. No further live defect was found; every cap on persisted or
  printed output (`selftest()`'s provider-ready list, `main()`'s unmatched-name preview,
  `write_result()`'s `unmatched` roster) is either uncapped-and-ranked on the persisted artifact
  or explicitly labelled as a partial console preview with a total alongside it, per Hard
  Rule 0.
