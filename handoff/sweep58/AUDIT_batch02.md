# Sweep 58 -- AUDIT batch 02

| module | lines | read |
|---|---|---|
| src/verify_math.py | 13,110 | in full, lines 1-13110, paged in 800-line reads |

I checked the open queue first (103 orders) and pulled the full text of every verify_math order.
Scratch scripts (all read-only) are in the session scratchpad under `sweep58/`: `b02_queue.py`, `b02_orders.py`, `b02_s20q.py`, `b02_stamp.py`.
Nothing under src/, data/, state/ or prompts/ was edited, and the battery was not run.

Focus this shift:
- agent C's §20u admission (`_admit36` / `_RUN35_PINNED36`)
- §20e/§20j (`_spawn_scan20e` and its fixtures)
- the lifted canary functions
- `_no_ledger_for_vm`
- the ledger witness move
- the c8491264e6dc minors
- the coordinator's §20q and `_publish_rc20p` edits, and the checks_L4.py re-pin

---

## src/verify_math.py

### DEFECT MINOR -- §20q cannot see a dropped `land_onomasticon` verdict (coordinator change)

`land_onomasticon` returns a tuple, `(named, landed, why)`. The coordinator widened §20q's writer test to include it:

```python
def _is_writer20q(_f20q):
    return ((isinstance(_f20q, _ast20q.Name) and _f20q.id == "land_json")
            or (isinstance(_f20q, _ast20q.Attribute) and _f20q.attr == "land_onomasticon"))
...
    if (isinstance(_n20q, _ast20q.Expr) and isinstance(_n20q.value, _ast20q.Call)
            and _is_writer20q(_n20q.value.func)):
        _discarded20q.append(...)
```

The only thing the row tests is a bare expression statement. That is the right shape for `land_json`, which returns a bool. It is the wrong shape for a writer whose verdict is the middle element of an unpacked tuple.

**Failure scenario, measured** (`b02_s20q.py`, which replicates the predicates verbatim over pipeline.py):
- Delete `landed.append(onom_landed)` from `pipeline.phase_weave`.
- The phase now marks weave done even when the onomasticon compare-and-swap was refused.
- Both §20q rows stay green: `discarded` is `[]` and `used` is `12`.
- Only the bare-expression mutant (M2) is caught.

Two sibling gaps have the same cause:
- `_nogate20q` collects only `Name` calls and tests `"land_json" in _calls20q`. A phase whose only writer is `O.land_onomasticon` falls outside the "every phase that lands artifacts consults gate_done()" row.
- §20ac's handler row checks "calls no land_json" only.

Also: `_used20q >= 12` is now 11 `land_json` + 1 `land_onomasticon` = exactly 12, so the floor has zero headroom.

**Remedy.** For a tuple-returning writer, assert that the unpacked verdict name (target index 1) is read by a later `landed.append(...)` / `gate_done` in the same function. Also count `Attribute` writer calls in `_calls20q`. Add a fixture control carrying the M1 shape.

### DEFECT MINOR -- two blanket ledger wraps around live-state reads remain, and §20c's comment now contradicts §16

§20c:

```python
# ... Nothing under test is suppressed: only the echo, for
# the duration of this one call, exactly as §16's `SF.build()` calls are.
with _no_ledger_vm():
    _j20 = _D20.jobs()
```

§16's `SF.build()` calls were narrowed this shift to `_no_ledger_for_vm("silent:weave.py:index-stale")`, so "exactly as §16" is now false. §20v wraps `_on21._proc_lines()` the same blanket way.

Both are the live-state shape the owner refused. Every class they are known to note is already on `_THIRD_PARTY_CLASSES_VM[_LIVE_STATE_VM]`:
- `dashboard.py:jobs-lognames-import`, `:jobs-read`, `:jobs-roll`
- `overnight.py:proc-lines`, `:proc-lines-blind`

So the named grant fits exactly.

**Failure scenario.**
- `jobs()` -> `_read_row` -> `_tail_match` notes `silent:dashboard.py:tail-format-mismatch:read_auto.log` (dashboard.py `_tail_match`, the f-string label). That class is not on the grant.
- This happens when read.py's progress-line format drifts from `dashboard.RE_READ`, which is a repository fault.
- §20c swallows it, and the row still passes, because `jobs()` is total and the row asserts only `isinstance(_j20, list)`.

Partial mitigation: §20k's `dashboard.state()` runs under `_third_party_vm`, so the same class on the same run would redden §20z there. The §20c/§20v wraps are therefore a residual hole plus a false comment, not an unguarded class.

This was not named by 19eb3626d39c (that order named §b3 and `SF.build` only).

**Remedy.** Use `with _third_party_vm(_LIVE_STATE_VM):` at both sites, and correct the §20c sentence.

### DEFECT MINOR -- §20g says the `codewatch._stamp_poll` finding was "filed"; no codewatch order carries it

§20g's "WHAT THIS SECTION DOES NOT DO" paragraph:

```
# silence. One already has: `codewatch._stamp_poll` opens its poll stamp with "w" and
# `json.dump`s into it, and is on no list. That is a finding about codewatch.py, filed rather
# than pinned here
```

The code claim is true today: `codewatch._stamp_poll` still does `with open(..., "w") as fh: json.dump(...)`.

The "filed" claim is not. I searched every row of state/workorders.json for `_stamp_poll` (`b02_stamp.py`):
- 093a35335c68 is about pid contamination of the stamp, not its atomicity.
- c8491264e6dc (VERIFY_MATH_MINORS) is the only order that names the truncate-then-fill write.

**Failure scenario.** Once this shift resolves c8491264e6dc for its verify_math edits, the codewatch finding leaves the queue. The comment then points at a filing that does not exist.

**Remedy.** File a codewatch-scoped order for `_stamp_poll` (and the missing tree-wide scan §20g says it lacks) before closing c8491264e6dc. Alternatively, cite the new order id in the comment.

### QUESTION -- the witness-ordering row guards imports only, not every noisy statement after the witness

`_importers_after20z` flags a module-level statement after the witness rows only if it:
- is an `import`,
- calls `__import__` / `import_module` / `exec_module` / `reload` / `exec`, or
- calls a same-file function that does one of those.

A statement that calls already-imported library code through an existing alias passes. For example, `_STx.check(state)` placed after the witness returns `(2, [])`, yet it can `silence.note` into `health.LEDGER` after both witness rows were read. The atexit flush then lands it unseen.

The row's label is honest ("can import"), and house style re-imports per section, so most new sections would still be caught. Should the guarantee instead be an allowlist (only the witness's own controls and the label-dup rows may follow)?

### QUESTION -- §20u's splice proof is satisfied by a single surviving label

```python
    elif not (_their36 & _mylabels36):
        _unspliced36.append(...)
```

One label in common clears a whole batch file. A partial revert that drops all but one of checks_batchN's rows reads green. This predates this shift; I raise it because §20u changed.

Is a full-subset test wanted (`_their36 <= _mylabels36`, minus labels deliberately retired)?

---

### KNOWN 3c72359c53aa -- fixed in source, order still open

- **§20j:** the rows now drive `_spawn_scan20e` with five planted modules. The rows can fail:
  - deleting alias resolution empties slot 1;
  - ignoring `creationflags` fills slot 2;
  - matching any `.Popen` fills slot 3.
- **§20e's unfixtured fields:** `recognised` and `imports_subprocess` are still covered by the two live reconciliation rows (the silent-importer row and the regex-vs-AST row).
- **Canaries:** the three canaries now call the lifted `_ctx_literals_in19ab`, `_failopen_in20p` and `_clear_callers20t`. The live scans call the same functions (the §19ab loop, the `_failopen20p` loop, the §20t loop). Must-not fixtures are present for the first two and the attribute shape.
- **`_self_cites20ad`:** now reads `check(note=...)` constants and `line ~NNNN`.
- **Duplicate-label row:** now the last pair in the file.

### KNOWN 7d314c5e00e4 -- fixed

The §20z witness block now follows §20ae, and the ordering row plus its six-fixture control hold it there. See the QUESTION above for the residual.

### KNOWN 19eb3626d39c -- fixed at both named sites

- §16 (both `SF.build` calls) and §b3 now use `_no_ledger_for_vm`.
- `silence.note` records `health.record(f"silent:{site}", ...)`, so the exact-match class key works.
- Both named labels exist: `weave.py:index-stale`, `standards.py:catalogue-coverage`.
- The narrow wrapper's control drives drop, forward and restore.
- The spy excludes `_forward_unnamed_vm` from blame.
- Residual blanket sites are filed above as NEW.

### KNOWN 491bd68b18e9 -- fixed, pins verified

- `_admit36` hashes the bytes it executes and decides every name on disk or pinned. Unpinned, tampered and gone files are refused as FAILED rows.
- The control covers all four outcomes.
- I measured sha256 of all six `handoff/run35/checks_L*.py`, including the re-pinned `checks_L4.py` (`baf73377...0b5607`). All six match `_RUN35_PINNED36`.
- The pinned files import only modules resolved through `sys.path.insert(0, SRC)`. None imports or execs a sibling in handoff/.

### KNOWN c8491264e6dc -- mostly fixed; still accurate for two items

Fixed and verified:
- §18c now names SEVEN self-cleaning temp sites. I grepped and found exactly seven: 19ab flow root, `_scratch19ft`, 20p halt probe, batch2 `scratch_dir`, two `TemporaryDirectory`, batch6 `_tmp_guard`.
- §20g no longer claims to stop a seventeenth write.
- BUGS.md has no "Pinned by §19s" (grep verified).
- The batch1-5 headers now say "SPLICED AND LIVE".
- §19o span subscripts go through `_at_vm`.
- The backfill `sample` note and `_self_cites20ad` output are uncut.

Still accurate:
- **Hardcoded population floors remain:** `len(_tags20y) >= 55`, `_toln20z >= 60`, `_seen20zn >= 30`, `len(_seen20ae) >= 50`, `_used20q >= 12` (the last now at zero headroom).
- **The `_stamp_poll` half:** see the NEW §20g defect.

### KNOWN 1d45a56ae1d8 -- verify_math half fixed

The §19n note no longer carries `:1605`, and the §20x retag comment no longer carries "line ~2494". `_self_cites20ad` now flags both spellings, including inside notes. The mutate/read/handbuilt/drill citations are other batches'.

### Coordinator `_publish_rc20p` stub -- nothing found

Stubbing `maintenance_shift_live` to `(False, ...)` is correct. Without it, a live shift routes a one-shot `--push` through `_one_shot_push_verdict` and refuses, so the "landed" control would measure the guard.

No coverage is lost: drill.py drives `_one_shot_push_verdict` with `maintenance_shift_live` stubbed live (the net near the `PB.maintenance_shift_live` save/restore). The saved-dict restore covers the new attribute.

### Other areas read -- nothing new found

Sections 1-19ah, 20a-20p, 20r-20s, the batch1-6 splices, 20ab, 20aa, 20y, 20ad, the tol= scan, the prose-backed scan and §20ae were read for the brief's classes. Beyond the KNOWN orders above (79d51aef8b71, de265a105279, e727ab804c5b and 7099a092abd3 unchanged and still accurate), nothing was found:
- no new truncation
- no swallowed exception that becomes a result
- no unguarded spawn
- no live-state write in a probe
