# AUDIT — batch 06, sweep #48

Batch: 06
Modules and lines read (full, no sampling):

| module | lines read | file length |
|---|---|---|
| src/standards.py | 1-2353 | 2353 |
| src/ledger_guard.py | 1-1007 | 1007 |
| src/estate.py | 1-723 | 723 |
| src/policy.py | 1-574 | 574 |
| src/cleanup.py | 1-445 | 445 |
| src/render.py | 1-429 | 429 |
| src/catalogue_aurora.py | 1-324 | 324 |
| src/ledger.py | 1-220 | 220 |
| src/catalog.py | 1-167 | 167 |

Read-only pass throughout; nothing under `src/` was modified.

---

## Finding 1 — MAJOR — `src/standards.py:898-902` — "corpus read is progressing" is a sibling of the already-filed log-size blind spot

**What is wrong.** The standard is:

```python
prog = read.get("done", 0) / max(read.get("total", 1), 1)
out.append(_s(
    "corpus read is progressing", prog > 0, f"{prog:.1%}", "above 0",
    ...
    "high", "read"))
```

`read.get("done", 0)` is not a live measurement — it is the `chunks` figure captured off the **last matching line of `state/read_auto.log`** (`dashboard._read_row`, `src/dashboard.py:242-247`, via `_tail_match`). That count is monotonically non-decreasing for the life of one reader run: once the reader has logged a single chunk of progress, `done > 0` and stays `> 0` for as long as the log's last line is not overwritten — including if the reader has since wedged solid and stopped writing entirely. The standard tests only "has this job *ever* produced one unit of output", not "is it producing output *now*", so once satisfied it can never go red again for that run, however long the process has since gone silent.

This is exactly the shape the batch's already-filed finding (`d9328fe1ee38`, the "every running job is advancing" log-size standard) describes, one function away: an instrument that measures a proxy which can freeze high while the real work has stopped. The mitigation here is even thinner than that standard's — the log-size check at least re-measures growth every tick; this one only ever asks whether the ever-cumulative counter has cleared zero.

**How I verified it.** Read `standards.py:870-902` for the check itself; then read `src/dashboard.py:242-260` (`_read_row`) to confirm `done` is sourced from `_tail_match(..., RE_READ, ...)` against the log's tail rather than any current-tick liveness probe, and that nothing resets it except a fresh reader process starting a new log entry from small numbers.

**Mitigating context, stated for fairness.** Two siblings in the same block can independently catch the same stall: "every running job is advancing" (log-size growth, itself imperfect per the sweep's own prior finding) and "corpus read finishes inside a day" (an ETA figure, whose own freshness depends on the same log tail and could similarly freeze). None of the three is a live, current-tick liveness probe of the reader; each is a different proxy with a different blind spot, which is arguably the intended defence-in-depth, but the specific standard named here contributes essentially nothing once the job has produced its first chunk.

**Proposed remedy.** Either retire this standard (its signal is fully subsumed by "every running job is advancing" once the job has started) or change its condition to something that CAN go false again after passing — e.g. compare `done` against the previous poll's `done` (the same `job_stamp`/held-size pattern the job-advance standard already implements) rather than testing only `> 0`.

---

## Finding 2 — MINOR — `src/policy.py:389` — coverage-row subject truncated to 40 characters with no marker, in the one file whose whole thesis is against exactly this

**What is wrong.** Line 389:

```python
for row in rows:
    evals.append(evaluate(row, COVERAGE_RULES, str(row.get("source"))[:40]))
```

`str(row.get("source"))[:40]` is a bare slice with no ellipsis or "+N chars" marker, and the value becomes the `subject` field of every `COVERAGE_RULES` evaluation record — persisted verbatim into `state/policy_report.json` via `report()`. It is the identifier a person or a script reads to know *which coverage row* a FAIL or a vacuous-pass line is about.

This is inconsistent with its own two siblings in the same function:
- the record loop three lines above uses `os.path.basename(p)` — full filename, no cut (`policy.py:355`);
- the evidence-sweep loop below uses `os.path.relpath(p, feats_root).replace(os.sep, "/")` — full relative path, no cut (`policy.py:414`).

It is also inconsistent with this module's own stated doctrine: `_observed()` (`policy.py:125-149`) exists specifically because a prior version of this file cut the *observed value* at 120 characters with no marker, and its docstring states the rule plainly — "a cut now declares itself and its size" — while allowing display-only caps (`r['observed'][:34]` at the print site) precisely because those are reversible and the underlying value survives elsewhere. Line 389's cut is not reversible: nothing downstream in `evals`/`state/policy_report.json` retains the untruncated source name, so a source whose name shares its first 40 characters with another (long homebrew or franchise titles are common in this corpus — see `catalogue_aurora.py`'s own docstring example, `"Who Framed Roger Rabbit (incl. all content from its associated crossover-toon IPs)"`, 85 characters) would be indistinguishable from its collision partner in the persisted report.

**How I verified it.** Read `policy.py:340-389` in full, confirmed the three subject-construction call sites (`RECORD_RULES` at 355, `EVIDENCE_RULES` at 414-417, `COVERAGE_RULES` at 389) and that only the coverage one truncates without a marker. Confirmed `evaluate()`'s `subject` parameter (policy.py:196-214) is stored unmodified into the returned dict and that `report()` (217-250) writes `evaluations` — hence this `subject` — to disk as-is.

**Proposed remedy.** Either drop the `[:40]` entirely (the record and evidence subjects carry no such cap) or route it through `_observed()`-style marking (`s if len(s) <= 40 else s[:40] + "... (+N chars)"`) so a persisted report never silently drops the tail of a source name it exists to identify.

---

## Finding 3 — INFO — stale citation cluster in `src/standards.py` (two pairs, both verified by grep cross-reference)

The file cites its own past line numbers by name in several places to point a future reader at where a similar defect was already repaired. Two such citations have drifted as the file grew around them:

**3a. `standards.py:198`** — the comment reads:

> "A [:80] cut with no marker on the one field that carries the cause is the same shape already repaired at **standards.py:604** and catalogue_models.py:130-138"

Line 604 today falls inside `provider_pool_denominator`'s docstring ("A NUMERATOR WITH NO DENOMINATOR...") — unrelated to any truncation repair. The actual "cut a field with no marker" repair the comment is pointing at is the "UNCUT (orders 5802e8899e4f, c1ab7302613e)" block at **standards.py:644-652** ("A [:40] slice cut the REASON, not the name, with no marker"), 40+ lines away from the cited line.

**3b. `standards.py:647`** (inside that same UNCUT block) — cites "the function's docstring at **:576**" for the phrase `"NOTHING IS CAPPED -- every unverified provider is named"`. That phrase is actually at **standards.py:617**, not 576.

**3c. `standards.py:1475-1476`** — the comment reads:

> "This file has already fixed the identical shape twice, at **:1671** (\"ALL OF THEM, not [:120] characters...\") and at **:1742** (\"EVERY RESIDENT NAME ... ranking is allowed here, truncating is not\")."

Line 1671 today is the opening of the unrelated "A POOL FAILURE NOBODY CAN NAME" section. The actual `[:120]`-repair comment ("ALL OF THEM, not `[:120]` characters -- that cut the joined name list mid-name") is at **standards.py:1781**, 110 lines away. Line 1742 is mid-way through the "the local model has a live runner" block, unrelated; the actual "ranking is allowed here, truncating is not" phrase is at **standards.py:1879**, 137 lines away.

**How I verified it.** For each citation, `grep -n` for the exact quoted phrase against the live file and compared the returned line number to the one named in the comment. All four are reproduced above with the exact current line numbers.

**Proposed remedy.** Update the four line-number references (198, 647, 1475, 1476) to 644 (or 649), 617, 1781 and 1879 respectively. No behavioural code is affected — this is documentation drift only, but it is the exact "stale file:line citation" class this sweep is asked to catch, and a person chasing "the same shape already repaired at standards.py:604" today lands on unrelated prose.

---

## Finding 4 — QUESTION/INFO — this batch's two named "writers of shared state" don't fit the brief as given

The sweep brief calls out `ledger.py` and `catalogue_aurora.py` as "both writers of shared state" to check for lost-update (read-modify-write-whole-document) hazards. Neither turned out to match that description on inspection:

- **`src/ledger.py`** ("DE PRETIO — the Ledger Standard") is a pure in-memory currency-conversion module (`to_standards`, `from_standards`, `cross_rate`, `work_value`, `assay_to_standards`). It performs **no file I/O of any kind** — no read, no write. Its own docstring explains why: it is deliberately HELD/unwired (owner ruling 2026-09-08, order `3fb9fc6b9999`) with zero callers in the generation pipeline. There is no shared-state writer here to audit for lost updates.
- **`src/catalogue_aurora.py`** does write shared state (`data/records/*.json` via `pipeline.write_record_catalogue`, and `data/SWEEP_ROLL.json`), but the exact defect class the brief is asking about — landing a whole document over concurrent writers — was already found and fixed in this file (order `f818a77293fc`): the roll write goes through `roll.update_rows(roll_changes, path=ROLL)`, described in the surrounding comment as a compare-and-swap that "re-reads and re-applies if the file moved under it," rather than writing the in-memory snapshot wholesale. I did not find a new instance of the whole-document-overwrite hazard in this file.

Flagging this as a question rather than asserting the brief is wrong: it is possible the "ledger.py" the general sweep instructions had in mind is a different, differently-named module elsewhere in the tree (this project has more than one `*ledger*`-named file — see `ledger_guard.py` in this same batch, which is itself a *checker* of ledger files, not a shared-state writer either, by design). Worth relaying to the coordinator so the actual shared-state-writer pair (if one exists under a different name) gets checked by whichever batch holds it.

---

## What I read and found nothing wrong in

- **`src/standards.py`** — the remaining ~2,300 lines: every `_dropped`/`silence.note` pairing in `check()` (all ~25 of them), the fandom-IPv4 probe and its per-process TTL memo, `ollama_token_flow`/`_flow_failure`'s three-valued contracts, `job_stamp`/the job-advance stall detector itself (distinct from Finding 1's standard), `charter_regression_verdict`, `provider_pool_denominator`, the self-check that greps the file for unused `MIN_`/`MAX_` constants, the aggregate "every standard could read its own input" check, and `report()`/`main()`'s exit-code handling. All internally consistent with their (extensive) documented histories; I did not find a second unfixed instance of the "measures the wrong witness" or "check that cannot fail" shapes beyond Finding 1.
- **`src/ledger_guard.py`** — all three independent mechanisms (`check_append_only`/`_one_insertion`, `check_structure`'s bug-id-in-both-sections test, and the hash chain `seal()`/`verify_chain()`/`check_since_snapshot()`/`check_since_floor()` quartet), the acknowledgement mechanism (`_load_acknowledgements`, fails closed on any malformed entry), and `main()`'s four-mechanism CLI. The floor-ratchet logic at `seal()` (lines 368-425) is sound against the compounding-loss hazard it documents fixing.
- **`src/estate.py`** — `inspect()`'s per-extension handling (including the `.jsonl` torn-line case and the stat-retry-then-classify race handling), `artifacts()`'s root discovery, `charter()`'s four behavioural (not string-presence) erratum tests, `written()` and `terminal()`'s vanishing-row-safe `note()` calls, and `external()`'s four-condition Ollama/Cascade/disk checks. No lost updates (this module only reads/audits; it writes nothing).
- **`src/cleanup.py`** — `clean_description`/`_MARKUP`'s idempotency fix and mangled-escape guard, `clean_ceiling`'s exact/head/prefix/ambiguous resolution ladder, and `main()`'s five uncapped report rosters plus the `write_record` return-value gating.
- **`src/render.py`** — `containment_svg`'s caption-vs-geometry separation, `children_of`'s partial-coordinate refusal (`missing = [...]; raise ValueError`), and `write_views`'s atomic per-file temp+fsync+`replace_retry` write path.
- **`src/catalog.py`** — small, read-only CLI; `load_catalog`'s missing-vs-empty distinction and `main()`'s exit-code discipline are both correct and consistent with their documented fixes.
- **`src/catalogue_aurora.py`** — `slug()`/`record_path()`'s legacy-cap migration handling, `parse_folder`'s duplicate-vs-distinct dedup key, and `main()`'s write-then-report gating (record write and roll write are both verdict-gated, in the correct order).
- **`src/ledger.py`** — arithmetic in `assay_to_standards`'s M10-ceiling handling (borrowed from `tempus.band_resolution`, anchored at M10's own floor) checks out against its own worked description; `currency_status`'s unlisted-vs-non-convertible distinction is correctly separate from `to_standards`/`from_standards`'s bare-`None` contract.

No `except: pass` or other bare-swallow patterns were found in any of the nine files; every exception handler I inspected pairs with a `silence.note(...)` tag or an explicit re-raise.
