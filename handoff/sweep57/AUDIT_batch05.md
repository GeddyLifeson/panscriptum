# AUDIT batch05 — run57

Modules read in full, top to bottom: `src/feats.py` (2783 lines), `src/allsweep.py` (1024 lines),
`src/thread_integrity.py` (721 lines), `src/runguard.py` (567 lines, audited hard per the work
order's instruction — it grew from 383 lines at sweep56/batch09 to 567 in run #56),
`src/cleanup.py` (445 lines), `src/sweep.py` (374 lines), `src/physics.py` (312 lines),
`src/catalog.py` (167 lines).

Open queue checked first via `workorders.open_orders()` (PYTHONIOENCODING=utf-8,
`C:/Users/imarl/miniconda3/python.exe`). Four of these eight modules (`feats.py`, `allsweep.py`,
`thread_integrity.py`, `sweep.py`) were read in full by `handoff/sweep56/AUDIT_batch05.md` and are
**byte-identical or line-shifted-only** in the areas that batch flagged — every DEFECT/QUESTION it
raised in those four files was independently re-verified against the current source and is
reported below as KNOWN rather than re-derived. `runguard.py`, `cleanup.py`, `physics.py` and
`catalog.py` were not part of that prior batch's module list; `catalog.py` matches the sweep56
read exactly (167 lines, identical content, "nothing found" reconfirmed).

---

## src/runguard.py — audited hard, per the work order. Nothing found.

Read in full. `_process_signature()`, `holder_is_live()`'s new stale-but-alive arm, `guard_fault()`
and the `pid`/`pid_started` stamping in `claim()`/`beat()` were all traced by hand against the
invariants the work order named:

- **`_process_signature(pid)`** (lines 180-242): psutil path returns `(False, None)` only on a
  confirmed-absent pid, `(True, create_time_or_None)` on a confirmed-alive one, and `(None, None)`
  on any exception or on ImportError-then-ctypes-failure. The ctypes fallback (lines 220-242)
  distinguishes `ERROR_INVALID_PARAMETER` (proof of death, `(False, None)`) from every other
  `OpenProcess` failure, including access-denied on someone else's process (`(None, None)`,
  correctly refusing to guess). Verified the ctypes path never returns a `create_time`, which
  means on a machine without psutil the new stale-but-alive arm in `holder_is_live` can never
  fire — that is a documented, intentional conservative degradation (`_process_signature`'s own
  docstring: "duplicated rather than imported... an unreadable process table returns (None,
  None) and `holder_is_live` then falls back to the heartbeat alone, exactly as it behaved before
  this function existed"), not a defect.
- **`holder_is_live()`'s new arm** (lines 245-293): confirmed it is reached only after the
  existing `(now - hb) < STALE_AFTER_S` fresh-heartbeat check has already failed, and it can only
  ever turn that would-be `False` into `True` — never the reverse. It requires **positive**
  evidence (`alive` from `_process_signature` truthy, `created is not None`,
  `abs(created - started) < 1.0`) before extending liveness; any missing/unreadable component
  (absent pid, absent `pid_started`, unreadable process table, non-matching start instant) falls
  through unchanged to the pre-existing `return False`. A recycled pid is correctly rejected by
  the `abs(created - started) < 1.0` start-instant match — a reused pid will essentially never
  share the exact `create_time` recorded for the original claim, so the "wedge on a recycled pid"
  failure mode the work order asked about does not occur.
- **`guard_fault()`** (lines 296-364): confirmed it carries exactly ONE arm (`STALE BUT ALIVE`),
  and its own docstring explains, with a measured counter-example (run #56's own pid 26924,
  gone, heartbeat 0.8 minutes old, run healthy), why the "fresh heartbeat, pid gone" arm was
  written, measured against the live guard, and deliberately removed — per the work order's
  instruction, this is **not** re-reported as a missing arm. The one arm's threshold
  (`age_min >= STALE_AFTER_S/60.0`) is the exact mirror of `holder_is_live`'s
  `(now - hb) < STALE_AFTER_S`, so the two cannot disagree about what counts as stale. It is
  called from `src/workorders.py:1240-1247` (outside this batch's module list, confirmed by grep)
  and from `src/drill.py`'s net suite, so it has a live consumer.
- **`claim()`/`beat()` pid recording** (lines 367-441, 443-486): both stamp `rec["pid"]` and
  `rec["pid_started"]` via `_process_signature(os.getpid())` immediately before landing the
  record, so the field travels with whichever short-lived interpreter is actually doing the
  work at that instant, matching the docstring's account of the guard's holder being "a
  succession of short-lived interpreters," not one process.
- The digest-before-read ordering in `claim()`, `beat()` and `release()`, and the
  compare-and-swap in `_land_claim` via `silence.replace_if_unchanged`, were re-traced and are
  correct and consistent with each function's own docstring — no lost-update window found.
- No `file.py:NNN` citations exist anywhere in this file (confirmed by grep for
  `[A-Za-z_]+\.py:[0-9]+`), so the stale-citation defect class that dominates this project's other
  files does not apply here.
- The fail-open on a corrupt guard record (in `claim()`, lines 399-412) is the owner-ruled
  exception (order `70f66fbd98aa`, 2026-09-08) and is now announced via `escalation.escalate` at
  SAFETY rather than silent — confirmed present and correctly wired, not a fresh fail-open.

**Nothing found in runguard.py.**

---

## src/allsweep.py

### DEFECT — `reconcile()`'s exception messages are cut to 90 characters, undisclosed, with no
### record of the full text anywhere (new; not previously filed)

**Location:** src/allsweep.py:493, 515, 541, 558, 576, 615, 687

```
493:        note("source reconciliation failed", f"{type(e).__name__}: {str(e)[:90]}")
515:        note("coverage reconciliation failed", f"{type(e).__name__}: {str(e)[:90]}")
541:        note("cache reconciliation failed", f"{type(e).__name__}: {str(e)[:90]}")
558:        note("purge reconciliation failed", f"{type(e).__name__}: {str(e)[:90]}")
576:        note("phase reconciliation failed", f"{type(e).__name__}: {str(e)[:90]}")
615:        note("band reconciliation failed", f"{type(e).__name__}: {str(e)[:90]}")
687:        note("process check failed", f"{type(e).__name__}: {str(e)[:90]}")
```

All seven sites are inside `reconcile()`'s per-section `except Exception as e:` handlers. The
`detail` field this constructs is the *only* place the exception text is stored — it becomes the
row landed in `data/ALLSWEEP.json` under `"reconcile"` and the line printed under "RECONCILE —
where the subsystems disagree." Once the function returns, `e` is gone (the same argument this
file already makes for itself: `run_verifier`'s own `except Exception as e:` handler, lines
423-431, was deliberately changed to keep `f"{type(e).__name__}: {e}"` WHOLE, with the comment
"WHOLE. This is the only record that this verifier could not even be launched... the exception
is gone once this returns, so the cut is irreversible"). `check_import` (lines 307-358) was given
the identical treatment for the same reason under order `215f9e7b86ff` ("WHOLE, NOT CLIPPED"),
and the task brief's own note that "three error tails" were fixed in run #56 refers to exactly
these two sites plus one more inside `check_import` — all three verified correctly whole in this
read (no `[:150]`/`[:120]` slice remains at any of them).

`reconcile()`'s seven sites were not touched by that same repair and still carry the identical
shape the file elsewhere calls out as wrong: an undisclosed, irreversible truncation of the one
surviving record of a caught exception. A `str(e)` longer than 90 characters (a path-heavy
`OSError`, a `KeyError` naming a long dict key, a `json.JSONDecodeError` with a long "Expecting
value" position message) loses its tail with no ellipsis, no "+N chars," and no way to recover it
— exactly the pattern order `2da56d4307ee`/`215f9e7b86ff` exist to forbid elsewhere in this same
file.

**Why it matters:** RECONCILE is the tier this file's own docstring calls the one "no single
verifier can do," and a reconciliation failure (a corrupt `SWEEP_ROLL.json`, a `KeyError` on a
record missing `"source"`) is diagnostic information an operator needs in full to fix the
underlying data problem, not a display column with room to spare. The severity is lower than a
Hard-Rule-0 roster truncation (this cuts one error message, not a list of entities), but the
shape and the irreversibility are identical to what this same file has fixed at three other sites.

**Confidence:** DEFECT (verified against the current source; not present in
`handoff/sweep56/AUDIT_batch05.md` or in any open work order — searched the queue for `str(e)`,
`[:90]`, and `"reconciliation failed"` with no hits).

### KNOWN — stale cross-file line citations, unchanged from sweep56/AUDIT_batch05.md (line numbers
### shifted by the run #56 edit, content identical)

**Location:** src/allsweep.py:188, :267, :798 (was :789), :937-938 (was :926-927)

Re-verified against current source; all four citations are still wrong in exactly the way
`handoff/sweep56/AUDIT_batch05.md` documented (verify_math.py:6824-6825 is really :9758-9759;
rosetta.py:618-624 is really :776-782; overnight.py:1007-1015 is really :1287;
workorders.py:158/standards.py:1132 are really :253/:1536). The only change since that audit is
that all four sites moved down by ~9-11 lines because run #56 added the three "kept whole" fixes
described above earlier in the file. Not re-filed as new; see that audit for the full citations
and verified correct locations.

### Verified correct — "three error tails kept whole instead of cut at 150" (order 215f9e7b86ff)

Confirmed all three sites the task brief names are correctly implemented with no truncation
remaining: `check_import`'s `err = tail[-1] if tail else ...` (line 332), its
`"exited without a traceback, saying: " + said.splitlines()[-1]` (line 355), and
`run_verifier`'s `"tail": [f"{type(e).__name__}: {e}"]` (line 431). None of the three carries a
`[:150]`/`[:120]` slice any more. **Nothing found** at these three sites — reported as verified,
not as a defect.

### Nothing else found in allsweep.py

`Verifier`'s `__iter__`/`__len__`/`__getitem__` shim, `run_verifier`'s `rc_means` fallback chain,
`estate_faults`/`_row_is_fault`'s fail-closed default on a keyless row, the `_marked`/`_head`
console-cut helpers (both disclosed, per Hard Rule 0's "ranking is fine, truncating silently is
not"), and `main()`'s `bad` count formula were all re-traced and are internally consistent with
their own documentation. `NEVER_RUN` genuinely has no reader anywhere in `src/` (confirmed by
grep), matching its own comment. No new bare `except: pass`, no new tautological check, no new
undisclosed roster/entity-list cap found.

---

## src/thread_integrity.py

File is unchanged from the sweep56 batch05 read (721 lines, identical content in every section
checked). Two items from that audit are reconfirmed present and unfixed:

### KNOWN — stale self-citation at :592-593 (unchanged from sweep56/AUDIT_batch05.md)

```
592:    # THE FOURTH LISTING. ASYMMETRIC-LAWFUL was the one remaining class whose per-pair detail
593:    # was computed at :188 and then discarded: main() itemised its three siblings and this one
```

Still at the identical lines, still wrong (the real `ASYMMETRIC-LAWFUL` append is at
`thread_integrity.py:430-431`, inside `classify()`; line 188 today is inside
`load_thread_graph`'s target-resolution loop). Not re-filed; see the prior audit.

### KNOWN — QUESTION on `_floor_verdict`'s read-modify-write lacking a compare-and-swap (unchanged)

`_floor_verdict` (lines 209-266) still reads, compares and conditionally rewrites
`state/THREAD_INTEGRITY_FLOOR.json` via `silence.write_json` with no CAS against a concurrent
writer. Unchanged from the prior audit's QUESTION; not re-filed.

### Nothing else found

`load_thread_graph`'s fail-closed `ThreadGraphUnreadable` raising, `_charter_codes`'s
absent-vs-corrupt distinction, `classify`'s directed-graph asymmetry logic (order 7bffb5634d7a),
and `main()`'s exit-code wiring (order aa075aa80f5c) were all re-traced and match their own
documentation. Separately, `a724ec57e0d5` (`TI_DANGLING_VERDICT_STOPS_SHORT_OF_THE_LADDER`) is an
open, still-undecided OWNER-rung ruling question about whether the DANGLING verdict should also
escalate — confirmed still open and still a live design question, not a hidden defect; not
re-derived here.

---

## src/cleanup.py

### DEFECT — the file's own comment claims a Hard-Rule-0 fix that is only half made: `d[:46]`/
### `cd[:46]` are still silently truncated (unfixed remainder of KNOWN order `fe99e57e1899`... `fe99e57e1993`)

**Location:** src/cleanup.py:333 (write), :409-412 (print)

```
331:            cd = clean_description(d)
332:            if cd != d:
333:                desc_fixed.append((src, nm, d[:46], cd[:46]))
```//
```
409:    print(f"\n3. descriptions with markup stripped         : {len(desc_fixed):,}")
410:    for s, n, b, a in desc_fixed:
411:        print(f"     {str(n):<24}{b!r}")
412:        print(f"     {'':<24}-> {a!r}")
```

Open work order `fe99e57e1993` (`UNMARKED_NAME_CUTS_SWEEP44`, filed by sweep44) names, among nine
sites across seven files, `"cleanup.py:231,233,261 ce[:70], ce[:52], d[:46]/cd[:46]"` as
unmarked, undisclosed per-name/per-value truncations, explicitly "beneath a comment claiming
these per-name cuts were fixed alongside the roster caps." Checked against the current source:

- The **ceiling** truncations (old `ce[:70]`/`ce[:52]`) genuinely are fixed — `clean_ceiling`'s
  three result lists (`ceil_unres`, `ceil_ambig`, `ceil_fixed`, lines 294-306) all now carry and
  print the untruncated `ce`/`before`/`after` strings in full.
- The **description** truncation (old `d[:46]`/`cd[:46]`) is **still present**, now at line 333,
  and is still printed un-marked (no ellipsis, no "+N chars") at lines 410-412 — `b!r` and `a!r`
  are `repr()` of a 46-character slice, which prints as a complete-looking quoted string with no
  indication anything was cut.

This sits directly beneath the module's own comment (lines 374-382) asserting the opposite:
*"The per-name character cuts in the same statements go with them"* — i.e., claiming they were
removed alongside the five roster caps this same paragraph documents fixing. That claim is true
of the ceiling rows and **false** of the description rows. A description longer than 46
characters (the median description here is stated elsewhere in this codebase as ~170 characters)
prints as though it were the whole before/after text, which is exactly the "looks complete, is
not" shape Hard Rule 0 exists to name — here applied to a diagnostic listing rather than a
roster, but the same undisclosed-truncation defect the surrounding comment believes is already
gone.

**Why it matters:** the raw and cleaned descriptions are stored in full on disk in the record
itself (`e["description"] = cd` under `--apply`), so no data is lost permanently — but the
`desc_fixed` console/report listing is the one place an operator reviews *what markup got
stripped and whether the strip was correct*, and a silently truncated before/after pair can hide
a bad strip (e.g., `_ruby_question_mark` or `_ruby_parenthetical` misfiring on real English text,
exactly the failure mode this file's own docstrings for those two functions spend paragraphs
worrying about) past the 46-character mark.

**Confidence:** DEFECT. The underlying finding (unmarked `d[:46]`/`cd[:46]`) is KNOWN — it is
still open under work order `fe99e57e1993` and the "where" field still points at the old line
numbers (231/233/261, since shifted). What is newly verified here is that the fix this file's own
comment claims for it did **not** land for this half of the finding, only for the ceiling half —
worth flagging explicitly so the order is not closed as fully resolved.

### Nothing else found in cleanup.py

`_ruby_question_mark`/`_ruby_parenthetical`'s non-ASCII gating (both carefully measured and
documented against real false-positive corpora), `clean_ceiling`'s exact/head/prefix/
prefix-ambiguous strategy ladder (with the single-vs-multiple-match guessing defect from order
`ed6e66c0c12d` confirmed fixed), the mangled-escape control-character guard over `_NAV`,
`_EMPTY_MECHANIC`, `_SETTING_META` and every `_MARKUP` pattern, and the gated
`write_record`/`unwritten` reporting were all re-traced and match their own documentation. The
five main rosters (`nav`, `mech`, `ceil_fixed`/`ceil_unres`/`ceil_ambig`, `desc_fixed`, `thin`)
and `unwritten` are genuinely uncapped in the sense Hard Rule 0 asks about (no `[:N]` on the list
itself) — only the per-value `d[:46]`/`cd[:46]` slice above is a truncation.

---

## src/sweep.py

File is unchanged from the sweep56 batch05 read (374 lines, identical content).

### KNOWN — stale citation in `load()`'s docstring, unchanged from sweep56/AUDIT_batch05.md

**Location:** src/sweep.py:81-89

```
85:    # `sweep()`'s live read is
86:    # `cachekey.load` at :160. Kept because it is the one place the FileNotFoundError-is-normal
```

Re-verified: `def sweep():` really is at line 160 (correct); the `cachekey.load(...)` call
claimed to also be at `:160` is actually at line 192; the "verify_math's own probes at
3358/3368/3374" claim is likewise still wrong (per the prior audit, the real probes are at
verify_math.py:5554 and :5570). Unchanged from the prior audit; not re-filed.

### Nothing else found

`rosetta_index`'s finer-grained-scale-wins tie-break, `nested_run`'s subset-testing (not
declaring nesting), and `report()`'s funnel/loose-population split were all re-traced and match
their own documentation, including the disclosed `--top` cap on `DEEPEST EVIDENCE` (an explicit
CLI parameter, not a silent truncation) and the padded-not-cut name columns (order `4f66afc16fbd`/
`9e5c04e01d74`, confirmed no `[:N]` remains on `r['name']`/`r['source']` anywhere in `report()`).

---

## src/physics.py — nothing found

Full read. This module did not appear in the sweep56 batch05 or batch09 handoffs available to
this batch, so it is reported here in full detail as a first read.

`kinetic()`, `joules_for()`, `sphere_volume()` and `binding_energy()` each refuse non-positive,
non-finite (NaN/inf) inputs AND non-finite results, with the guard shape argued consistently
across all four (a domain error must be reported as a `ValueError` naming the offending argument,
never allowed to silently propagate as `inf`, `-0.0`, or an `OverflowError`/`ZeroDivisionError`
naming arithmetic instead of the domain problem that caused it). Every one of these guards is
independently verifiable by hand:

- `kinetic()`: mass `> 0` and finite; speed `>= 0` (NaN refused) and `< C`; the relativistic
  branch's own `gamma`/result checked for finiteness afterward. Order chain (`3598ae9a4aad`,
  `7909342fefa4`, `371088645964`) is internally consistent and each cited fix is present.
- `joules_for()`: material/mode membership checked before any arithmetic (raises `KeyError`
  rather than silently defaulting to rock); volume `> 0` and finite; result finiteness checked
  after the multiply (guards a `vapor`-mode overflow).
- `sphere_volume()`: radius `> 0` and finite; `OverflowError` from `r ** 3` caught and re-raised
  in the module's own domain-error voice (`from None`, correctly suppressing the arithmetic
  traceback per assay.py's own stated complaint about exceptions that "name a line, not a
  fault").
- `binding_energy()`: radius `> 0` and finite (explicitly refusing the "R=0 in the denominator"
  and "R=inf silently returns a finite-looking 0.0" cases separately, each with its own
  docstring reasoning); mass `>= 0` (zero allowed, correctly — a massless body has zero binding
  energy) and finite; `m ** 2` overflow caught and re-raised in-voice; final result finiteness
  checked.

No `file.py:NNN` citations exist in this module (confirmed by grep). No caps, no truncation, no
bare `except`, no tautological check, no dead code (the module has no unreachable functions —
`MATERIAL`, `MODES`, `kinetic`, `joules_for`, `sphere_volume`, `binding_energy` are all either
called from `main()` or documented as consumed by `verify_math`/`anchors`/`ledger`/
`address_space`, per the module's own header explaining why it exists as a standalone file).

---

## src/catalog.py — nothing found

167 lines, byte-for-byte matching the sweep56/batch05 read (also "no findings" there). Re-traced
`load_catalog`'s absent-vs-empty distinction (order `3f4d2d058fdc`), `cmd_stats`'s uncapped
`missing` roster (order `6434c1ba7b20`, Hard Rule 0), and `main()`'s exit-code propagation on a
missing address (also order `3f4d2d058fdc`, "EVERY PATH USED TO EXIT 0"). All three remain
correctly implemented; no regression, no new finding.

---

## Coverage recorded

`sweep_plan.record('run57', ['feats.py','allsweep.py','thread_integrity.py','runguard.py',
'cleanup.py','sweep.py','physics.py','catalog.py'], batch=5)` run from the repo root with
`PYTHONIOENCODING=utf-8` under `C:/Users/imarl/miniconda3/python.exe`.
