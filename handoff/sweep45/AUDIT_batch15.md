# sweep45 — batch 15

**Modules:** `assay.py` `dashboard.py` `codewatch.py` `threads.py` `withdraw_chapters.py` `snapshot.py` `wh40k.py` `audit.py`
**Lines:** 5,376. **Read: all of them**, every module end to end, no sampling (Hard Rule 0).
**Read-and-report only — no source file was edited.** The standing `DRILL_BREACH` halt was not touched and no battery tool was run.

| module | lines | read |
|---|---|---|
| `assay.py` | 1,414 | 1–1414 |
| `dashboard.py` | 1,141 | 1–1141 (including the embedded page and its JS) |
| `codewatch.py` | 763 | 1–763 |
| `threads.py` | 630 | 1–630 |
| `withdraw_chapters.py` | 479 | 1–479 |
| `snapshot.py` | 376 | 1–376 |
| `wh40k.py` | 302 | 1–302 (including the whole ROSTER) |
| `audit.py` | 271 | 1–271 |

Every grep hit was confirmed against the **code** line, not the comment recording what the line used to be. Two findings were reproduced by driving the live modules; one already-open order was found to be already repaired in code (below).

---

## 1. `withdraw_chapters.py` — first, as instructed

### FILED — `ba5683e9506a` · MAJOR · LOCAL — the stray sweep has no unclaimed test
`src/withdraw_chapters.py:305-334`, report line `:397`.

The sweep is introduced as *"Anything left in `output/raw` that the catalog never claimed — the pilot's strays"* and **implements no such test**. It walks every file in `output/raw` and takes it. The only thing that has ever kept catalogued chapters out of that count is an implicit ordering assumption — that the loop above has already *moved* them — and the assumption fails in two situations.

**(a) The dry run, always and deterministically.** `shutil.move` at `:331` is inside `if a.go:`; `extra += 1` at `:334` is not. Without `--go` nothing has moved, so every catalogued chapter is still in `output/raw` and every one is counted. The preview prints `raw paths moved : N (+M unclaimed by the catalog)` with `M` inflated by the entire catalogued population. The dry run exists so a person can see what `--go` will do; it reports an archive swallowing files `--go` will not touch, and the two runs disagree about the same operation.

**(b) A stuck entry whose condition clears.** An entry whose move failed (`:277`) or whose stat came back `unavailable` (`:251`) **keeps its record**, pointing at `output/raw` — the module's whole doctrine. The sweep reaches the same file a few lines later; `os.path.isfile` at `:318` answers False only while the lock or denial is *still* held. If it has lifted, the sweep moves the file into the archive, counts it as unclaimed, and makes no amendment (`entry_left` is empty). The catalog is then left pointing at a path nothing occupies while the report prints *"MOVE FAILED, RECORD KEPT: … their files are still in the library"* — the docstring's own named harm, inverted.

**(c) Minor, same shape.** On an archive-name collision (`:266-274`) the same catalogued file is reported twice, once as a chapter that was not moved and once at `:324-327` as an "unclaimed" stray.

**Remedy:** build the set of basenames the whole catalog claims under `output/raw` before the sweep and skip those names, whether or not this run moved them and whether or not it is a dry run.

### Read and judged sound — no over-delete found
Everything else in this module holds up, and several parts are stronger than they look:

- **`_file_state` (`:52-83`)** correctly refuses to read an unanswerable stat as absence. It asks twice — `os.stat`, then the parent directory's own listing — and only a directory that answers "not there" yields `gone`. `unavailable` keeps the record. This is the right shape.
- **`select` (`:112-125`)** is pure and exact-match; the no-filter case returns the whole catalog, which is the documented default.
- **The selector refusal (`:170-184`)** checks `--source` and `--addr` *independently* against the catalog, so any selector matching nothing stops the run. A partially-mistyped selection cannot proceed.
- **`remaining = {k: v for k, v in cat.items() if k not in withdrawn}`** and `withdrawn = sel - stuck`: non-selected entries are never touched, and a failed move keeps its record. The catalog is edited, not erased.
- **Both writes land through `silence.write_json`** and **both verdicts are kept and reported**, with distinct remedies (`record_landed` cannot be reproduced by a re-run; `catalog_landed` can).
- **`main()` returns non-zero** on any refusal, stuck entry, unreadable path, collision or stray failure.
- The `escalation.assert_clear` interlock sits above argparse and above the catalog read, and fails closed on the import.

**One judgment call not filed:** an existing archive manifest that is *unreadable* (`ValueError`/`OSError` at `:379-382`) is printed about and then **replaced** by this run's manifest, losing the earlier withdrawal's record. It is announced rather than silent, and a lock-driven failure would also deny the write (which *is* reported), so the only live case is a corrupt JSON manifest. Renaming the unreadable file aside before writing would close it. Recorded here rather than filed.

**Also not filed:** `--label` is concatenated unvalidated into the archive path, so `--label "../../src"` resolves the archive outside `output/`. Operator-supplied, single-argument, and the default is today's date; noted for the record only.

---

## 2. Filed, worst first

| id | sev | where | what |
|---|---|---|---|
| `c003673cff01` | MAJOR | `dashboard.py:427-437, 476-483, 505-534` | history file wedges past its own shape guard; a second variant blacks out the whole page |
| `9a0588111549` | MAJOR | `assay.py:826-827, 1101` | an unrecognised attestation grade silently doubles the **published** interval |
| `ba5683e9506a` | MAJOR | `withdraw_chapters.py:305-334` | stray sweep has no unclaimed test (above) |
| `e7ea68901bfe` | MAJOR | `dashboard.py:660-664, 674-679` | `safety()` reports the good state on an unreadable file |
| `422ccc9f6eb4` | MINOR | `assay.py:_check_constants` | tonight's ratchet leaves `INSTRUMENT_WINDOWS` and `FACULTY_READS` unguarded |
| `04c6360636bf` | MINOR | `threads.py:198-202` | `SUBROOM_PARENT` degrades the published graph without a record |

### `c003673cff01` — `dashboard.movement()` wedges past its own shape guard
Both cases **reproduced** against the live module with `dashboard.HISTORY` pointed at a scratch file.

**Case A — permanent wedge, worse than the one `62286a6c018a` fixed.** `[{"at": "2026-09-05", "cited": 1}]` is a list of dicts, so the guard at `:435-436` passes it. Inside the try, `:479` raises `TypeError` comparing `str` to `float`; the handler notes and returns `[]`. **The `silence.write_json` at `:482` is never reached**, so the only code that writes `HISTORY` can never replace the bad file. Measured: three consecutive polls returned `[]` and the file was byte-identical afterwards. The panel renders "No history yet" forever — the exact failure the block's own heading (*A CORRUPT HISTORY FILE MUST HEAL, NOT WEDGE*) names, one type down from the guard order `62286a6c018a` added, and strictly worse than the shape that order caught, which at least reset and healed.

**Case B — the whole page goes dark.** A row with a recent numeric `at` and a string metric value becomes `base`; the delta loop at `:506-534` is **outside** the try, so `v - was` raises out of `movement()`. Measured: `TypeError: unsupported operand type(s) for -: 'int' and 'str'`. `state()` calls `movement(s)` unguarded as its last act, `/api/state` answers `{"error": …}`, and the page's `tick()` then throws on `d.jobs.length` and writes "server unreachable". Every panel goes dark — including the halt headline `panelSafety` renders first and loud.

### `9a0588111549` — `assay()` absorbs an unrecognised attestation grade
Measured on the charter's own Kenshiro worksheet:

```
attestation='Witnessed'   ->  M3.52 +/- 0.12      (the charter's published bar)
attestation='witnessed'   ->  M3.52 +/- 0.25
attestation='Excellent'   ->  M3.52 +/- 0.25
```

A lowercase spelling and an invented grade both fall to `SIGMA_BY_ATTESTATION.get(attestation, SIGMA_MAX)` at `:826-827`, take the Disputed sigma 3.7444, and publish a bar **twice the width**. The returned dict carries `"attestation": "witnessed"` verbatim and no recognition flag — verified, no key in it contains `recog`. The sibling `interval_from_hands` in the same file was fixed for exactly this (order `13a678071cbf`) and its comment states the doctrine: *"two layers absorbing the same bad input the same way is one layer and a decoy … so both layers have to speak."* The layer that produces every printed Magnitude is the one that does not speak. It is also the one operand of `assay()` with no Layer 1: `_check_scores` guards the scores, `_check_weights` guards the table, and the grade — which multiplies straight into the answer — is validated nowhere.

### `e7ea68901bfe` — `dashboard.safety()` reports the good state on an unreadable file
Two bare `except Exception` blocks that record nothing and whose declared exemption covers only one of the conditions they catch, in the panel the module calls *"the FIRST thing the page shows"*. `drill_last.json` (`:660-664`): any exception renders as "no safety drill has run yet", so a torn file is indistinguishable from one that never existed. `escalation.log` (`:674-679`) is worse, because the exemption **asserts the verdict** — *"an empty escalation log is the good state"* — so a read failure on the 24-hour escalation ledger is presented as a clean 24 hours. Precedent for narrowing to `FileNotFoundError` is in this same file twice (`throughput()` under order `ef7a5b8b56a5`, *ABSENT IS NOT THE SAME AS UNREADABLE*; `_tail_match`'s `hint`), and order `9508f9322b4c` is the same class one module over.

Two smaller same-class faults are recorded inside that order so they are not lost: `jobs()` does `import lognames as LN` at `:215` **outside** both of its try blocks, so an unimportable `lognames` blacks out the page — the precise outcome its docstring says it was fault-isolated to prevent; and `quotas()` initialises `worst = 1.0` and only ever `min()`s it down, so a bucket with no readable window renders "ok · 100% left".

### `422ccc9f6eb4` — audit of tonight's `_check_constants` ratchet
**The BAND_EDGES half is correct and I could not break it.** Verified against the live table: `BAND_EDGES` and `LADDER` name the same eleven rungs; all eleven rows carry the identical five-axis set; `ruin`, `reach`, `celerity`, `sustain` and `continuity` are each strictly increasing rung to rung. Every branch is a live ratchet over a property the table currently has.

What it did not cover, and the ratchet's own rationale (*"this file's constant tables … are guarded unevenly"*) is why it counts:

- **`INSTRUMENT_WINDOWS` is not checked against `LADDER`.** `instrument()` at `:1126` refuses a missing anchor with the message *"anchor must be one of {LADDER}"* — a sentence that would name the very rung it just refused. Worse, `anchors.py:427` does `A.INSTRUMENT_WINDOWS[b] for b in A.LADDER` with no guard, so the same divergence is a `KeyError` from inside production code rather than a refusal.
- **`FACULTY_READS`' axis names are not checked against `WEIGHTS`, and a wrong one is a silent drop in a published faculty.** `:1199` does `axis_scores.get(axis)`; a misspelt Measure returns `None`, `_reading` answers `(None, "unattested")`, and `faculty_status` then asserts the subject was never observed exercising that faculty when the table simply names a Measure that does not exist. `_check_scores` cannot see it — it validates the caller's keys, not the table's values.

Both hold today, so both proposed loops are ratchets that change no behaviour.

### `04c6360636bf` — `threads.SUBROOM_PARENT` degrades the graph without a record
`:198-202` builds it from `pipeline.SUBROOMS` inside a bare `except Exception: SUBROOM_PARENT = {}` with no `silence.note`, three lines under a comment saying *"this one decides the shape of the thread graph."* With `{}`, `category_path` at `:268` can never reach a subroom, every finer room disappears, and the pass silently reverts to the pre-2026-09-01 shape its own comment calls *"a regression dressed as a correction"*. Nothing catches it: `verify()` tests structural properties that still hold, `main()`'s counts stay internally consistent (just smaller), and `THREADS.json` lands derived under a different rule. This is the one place in a module built entirely of loud refusals that does not make the distinction. `assay._rho_doc` / `RHO_FALLBACK_REASON` / `correlation_source` solve the identical problem — a derived table that can be missing, degrading to historical behaviour and **announcing** it — and are the model.

---

## 3. Corroborated, already open — not refiled

- **`e4c8355cc7a0`** (`assay.py:1352`) — the `interval_from_hands` widening loop. Seeded at `sqrt(half_spread² + floor²) >= half_spread`. Confirmed on the code line; used as the model for finding this class elsewhere, not refiled.
- **`06b7f22484df`** — both harnesses for the restart budget aim at `_budget_left`, which has **no production caller**. Confirmed over the whole tree including `src/deprecated/`: the only callers are `drill.py:9537-9548`; the live path is `exit_if_stale` → `_claim_restart_slot` → `_take_locked`. `codewatch.py:398` documents this honestly. Corroborated.
- **`aad11acb1183`** — `dashboard.py` calls `escalation.assert_clear` in `main()`, so the one instrument built to display a standing halt refuses to start while one stands. Confirmed on the code line; live right now against `DRILL_BREACH`.
- **`7bebaa921ef3`** — `movement()`'s history is bounded twice. Confirmed; the reasoning at `:466-476` now names both bounds, so the *comment* half is repaired. Finding `c003673cff01` is a different fault in the same function.
- **`82fc93f056d4` / `901e441aae1d`** — `wh40k.py`'s 55 `[unattributed]` axis citations and the `--full` view that omits the provenance mark its twin `zfighters.py` prints. Both confirmed on the code lines (`compute()` builds the mark; `main()`'s `--full` block at `:271-275` prints score and citation only). Nothing new to add.
- **`2f0a734d8c15`** — the `verify_math` check for `withdraw_chapters --label` that never touches its subject. Confirmed: the `--label` default at `:167` is `datetime.date.today().isoformat()`, correct; the check remains a probe of a locally-built parser.

## 4. Already repaired in code — an open order that no longer reproduces

**`72ad163c4a93`** (`dashboard.py:472`, `base = older[-1] if older else (hist[0] if hist else {})`) describes `base` becoming the very sample it is the baseline for. **The code no longer reads that way.** `dashboard.py:506-508` is now:

```python
prior = hist[:-1]
older = [h for h in prior if h.get("at", 0) <= window]
base = older[-1] if older else (prior[0] if prior else {})
```

`prior` excludes the row just appended, and `span` is guarded by `if base`. The order's mechanism is closed; whoever owns the queue should verify and retire it rather than leaving it open against repaired code.

---

## 5. Deliberate design — read, judged sound, not filed

- **`snapshot.py`** is the strongest module in this batch. `_rel` refuses out-of-tree paths with a written-out account of all four ways an escaped path would have been *certified* rather than caught; `_safe_join` guards the restore end independently; `before()` refuses a partial capture and a manifest that did not land; `verify()` restores into a temp directory and `_dir_matches` walks the snapshot side file-by-file with `shallow=False`; `restore()` raises rather than returning fewer paths than promised; `listing()`'s `broken` flag is now read by `main()`. The one residual: `before()` classifies via `os.path.exists`, which reads a lock or denial as "does not exist" — but with `allow_missing=False` that *refuses*, which is the safe direction, and the only `allow_missing=True` call sites in the whole tree are in `drill.py`. Not filed.
- **`codewatch.py`** — the settle window is now measured in wall time off the filesystem rather than in polls, `runs_script` is pure and correctly rejects `-m`, `-c` and another tree's copy, check-and-take are one operation under one lock, a denied ledger write **refuses** the claim rather than granting it unmetered, `stamp()` retries and then escalates rather than disarming silently, and `_report_if_never_settling` closes the one path that said nothing. `_ledger_lock`'s proceed-unlocked fallback and `_read_ledger`'s `{}` are both argued out in place. Nothing new to file; the two live gaps are already `06b7f22484df` and `2cb8756deb0a`.
- **`audit.py`** — a read-only report. The synthesis-level checks deliberately treat a missing `provisional_magnitude` as one honest row (entry-level exempts `None`; the asymmetry is stated and intended), every violation list is uncapped, `_field` wraps rather than slices, and the denominator is read off the class prefix so a source-level fault cannot print as a rounding error. The two 10/14-row samples are declared samples with their denominators printed — not truncations.
- **`assay.axis_score`** saturating at 9.9 for an M10 anchor is the already-known open bug M18, named in the source. `band_for_quantity` returning `"M0"` for a quantity clearing nothing is the documented helper contract.
- **`assay`'s `or 1.0` backstop at `denom`** is unreachable today and the source says so in detail, including that the old reproduction no longer reproduces and must not be cited as evidence of reachability again. Left alone deliberately.
- **`threads.verify()`** builds `known` from the graph's own source codes, which cannot fail for a freshly-built graph — but it is pointed at the **round-tripped** object precisely so it tests the artifact a reader gets. Documented, and the third-tautology trap is named in place. Sound.
- **`wh40k.py`** — all five roster entries carry all eleven axes, the write is atomic and its verdict is gated, and `main()` returns 1 on a denied write. `for ax in A.WEIGHTS: rec["axes"][ax]` in the `--full` block would `KeyError` on a roster entry missing an axis; latent only, not filed.

## 6. Nothing found

- No non-atomic write to shared state in this batch. Every landing goes through `silence.write_json` (`withdraw_chapters` ×2, `snapshot`, `threads`, `wh40k`, `dashboard.movement`), and each verdict is either gated or has its ungated-ness argued in place.
- No unmarked truncation of a list or string anywhere in the batch. Every former `[:n]` carries the order that removed it, and the one surviving slice in `threads.py` (`parts[:2]` in `cohort_family`) decomposes an address rather than capping a listing — which that module's docstring already corrects itself about.
- No loop in this batch can fail to terminate. Every candidate was checked: `calibration_report`'s sigma sweep (bounded above by `min(SIGMA_MAX, saved + 2.0)`, 649 steps), `interval_from_hands`' widening loop (already open as `e4c8355cc7a0`), `stamp()`'s retry (`range(STAMP_ATTEMPTS)`), `_ledger_lock`'s acquire (`range(attempts)` with a `for/else`), and `band_for_quantity`'s ladder walk.
