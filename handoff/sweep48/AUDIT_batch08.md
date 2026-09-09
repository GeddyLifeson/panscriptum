# AUDIT — batch 08, run #48

Modules assigned (read in full, successive chunks, no sampling):

| module | lines read | total lines |
|---|---|---|
| src/workorders.py | 1-2097 | 2097 |
| src/overwatch.py | 1-1051 | 1051 |
| src/onomast.py | 1-773 | 773 |
| src/weave_index.py | 1-673 | 673 |
| src/handbuilt.py | 1-516 | 516 |
| src/runguard.py | 1-382 | 382 |
| src/suppressions.py | 1-352 | 352 |
| src/tuning.py | 1-286 | 286 |

Total: 6,130 lines read, matching `wc -l` for all eight files exactly.

---

## FINDING 1 — MAJOR — src/weave_index.py:458 and :470 — a boolean term that cannot affect the `stale` verdict it appears to gate

**What is wrong.** `staleness()` computes:

```
458:    coarse_stale = (newest is not None and newest > idx_mtime) or age_hours > STALE_HOURS
...
470:            "stale": bool(coarse_stale and age_hours > STALE_HOURS),
```

Let `A = (newest is not None and newest > idx_mtime)` (a record file was touched after the index was last built) and `B = age_hours > STALE_HOURS`. Then `coarse_stale = A or B`, and the field actually returned is `coarse_stale and B = (A or B) and B`. By boolean algebra this reduces to exactly `B`, in every case — `A` cannot change the result no matter its value. I verified this with an exhaustive truth table over the four (A, B) combinations (all four checked directly with Python), and it holds in all four rows.

Concretely: if a record file was modified one minute after `ENTITY_INDEX.json` was built (`A = True`) but the index itself is only, say, 2 hours old (`B = False`, well under the 48-hour `STALE_HOURS` ceiling), the returned `"stale"` is `False` — even though `modified_since` (computed a few lines above, gated on `coarse_stale`) may report that most of the corpus's record files changed since the last build. The mtime-freshness signal that `coarse_stale` was built to carry never reaches the verdict a caller reads.

**Why it matters.** `escalate_if_stale()` (same file, lines 474-515) files/refreshes the RUN-rung work order `ENTITY_INDEX_NEVER_REBUILT_STALENESS_ANNOUNCED_BUT_UNACTED` **only when `st["stale"]` is true**. Because of the reduction above, that gate is really just "is the index older than 48 hours", never "has the corpus changed since the index was built". A corpus that is rewritten heavily inside the 48-hour window (which the module's own docstring says is common — `pipeline.write_record` is the sole writer and runs continuously) will not be flagged stale by this instrument even though `weave.py`, `cosmology_graph.py` and `thread_integrity.py` are all reading a demonstrably out-of-date `ENTITY_INDEX.json` against the corpus on disk. This is distinct from the already-filed order d1709d8e757d ("nothing schedules a rebuild") — that order is about there being no scheduler; this is about the staleness *detector itself* silently discarding the more sensitive of its two signals, so even a caller that does check staleness on a tight cadence would under-report it within the first 48 hours after any build.

**How I verified it.** Quoted the exact two lines above from the file as it stands, then ran the boolean identity `(A or B) and B == B` for all four truth assignments of A and B in `C:/Users/imarl/miniconda3/python.exe` — all four rows confirm `final_stale == B` regardless of `A`.

**Proposed remedy.** The `stale` field should almost certainly just be `coarse_stale` (i.e. `A or B`) — that already reads as the intended verdict ("stale if the corpus changed since the build, or if the build itself is simply old"), and the second `and B` on line 470 should be removed. Whoever added the `and age_hours > STALE_HOURS` clause after `coarse_stale` was computed should confirm whether they intended a *conjunction* of a modified-since signal with a minimum age floor (in which case `coarse_stale` itself would need to become `A and B`, not `A or B` — a materially different design), or whether this is simply a leftover guard that defeats its own sibling expression. Either way the current code does not implement any coherent policy: it implements "ignore A entirely."

---

## FINDING 2 — MAJOR — src/overwatch.py:328, :696, :904 — `_progress()`'s tie-break field compares two incommensurable timestamp formats, so a "closed" auto-triage verdict can be silently discarded in favour of a bare "retired" record with no reason

**What is wrong.**

```
324: def _progress(f):
325:     if not isinstance(f, dict):
326:         return (-1, "", 0)
327:     return (_STATE_RANK.get(str(f.get("state", "")).lower(), 0),
328:             str(f.get("retired_at") or f.get("closed_at") or ""),
329:             len(f))
```

`_STATE_RANK` (line 321) ranks `"retired"` and `"closed"` at the SAME tier, 2 (both terminal). When two ledger copies disagree about a finding's fate — one process retired it, another closed it via auto-triage — `_merge_ledgers` (line 332) picks whichever `_progress()` tuple is greater, and since the rank (first element) is tied, the decision falls to the second element: a string built from `retired_at` OR `closed_at`.

But these two fields are written in incompatible formats:
- line 904: `f["retired_at"] = led["last_run"]`, and `led["last_run"] = time.strftime("%Y-%m-%d %H:%M")` — a human date string beginning with the current year, e.g. `"2026-09-08 12:34"`.
- line 696: `f["closed_at"] = time.time()` — a raw Unix epoch float, e.g. `1757312345.678`, which `str()`-ifies to a string beginning with `"1"`.

Because Python string comparison is lexicographic and any current-era date string starts with `"2"` while any current-era epoch-float string starts with `"1"` (this holds until the epoch float crosses 2×10⁹, i.e. until the year 2033), **a "retired" record's tuple always compares greater than a "closed" record's tuple**, regardless of which event actually happened more recently. This is not a tie-break on recency; it's an accidental, permanent bias toward "retired" whenever the two terminal states collide on the same fingerprint.

**Why it matters.** The module's own docstring for `verify_open()` and the surrounding comments (e.g. the block at lines 684-691, order 92a9017a5d14) argue at length that the text explaining WHY a finding was auto-closed ("auto-triage refuted: …") must never be lost — it is treated as important enough that a prior truncation of the same field was itself logged as a defect. But `_merge_ledgers`' `merged[k] = v` (line 354) replaces the LOSING record wholesale, not just its rank field — so when "retired" beats "closed" in this comparison, the entire `closed_at` / `verdict: "auto-triage refuted: …"` record is discarded and replaced by a bare retired stub carrying no reason at all. The module's own docstring for `save()`/`_reconcile_with_disk()` states plainly that two processes hold this ledger "routinely" (the standing `--loop` job plus "any ad-hoc `verify_open` call a maintenance run leaves behind"), so the collision this exploits is not a hypothetical edge case for this file — it is the concurrency pattern the file is written to expect.

**How I verified it.** Quoted lines 324-329 (`_progress`), 696 (`closed_at` assignment, inside `verify_open`), and 904 (`retired_at` assignment, inside `round_once`'s retirement loop) directly from the file. Confirmed `_STATE_RANK` (line 321) maps both `"retired"` and `"closed"` to rank 2. The string-format mismatch and its consequence (date-string > epoch-float-string lexicographically, for any current date) follows directly from the two assignments' literal formats — `time.strftime("%Y-%m-%d %H:%M")` vs. `time.time()`.

**Proposed remedy.** Give both fields comparable epoch timestamps (e.g. change `retired_at` to `time.time()` and format the human-readable date, if wanted, into a separate field), or have `_progress()` normalise both into a single epoch value before building the tuple (e.g. try to `time.strptime` a date-shaped string, fall back to `float()` for an epoch-shaped one). Either fix restores the "further along, ties by more recent" semantic the docstring already claims to implement.

---

## FINDING 3 — MINOR — src/suppressions.py:300 — stale line-number citation

**What is wrong.** Inside `problems()`, the comment at line 300 reads:

```
300:            # `fnmatchcase` is kept exactly as it was and is argued at :152-160: a suppression
301:            # narrows a detector for a NAMED case, and a case nobody wrote down is not a named
302:            # case, so a mis-cased pattern surfaces HERE as dangling rather than quietly
303:            # covering files it was never reviewed against.
```

Lines 152-160 of the file as it stands today are inside `add()` (the reason-storage / no-truncation discussion), and have nothing to do with `fnmatchcase` or case sensitivity. The actual explanation the comment is pointing at — "CASE-SENSITIVE ON PURPOSE (`fnmatchcase`, never `fnmatch`)… a suppression narrows a detector for a NAMED case, and a case nobody wrote down is not a named case… a mis-cased pattern surfaces there as DANGLING" — is the docstring of `suppressed()`, currently at lines 221-229 (verbatim wording matches, including the "NAMED case" / "not a named case" phrasing and the "DANGLING" conclusion).

**Why it matters.** This is exactly the class of defect the sweep brief names under "stale citations": the comment was almost certainly accurate when written, and line numbers drifted as `remove()` (added under order f5503302ce44, per its own docstring) and other code were inserted above it. It is low-severity on its own — a reader chasing `:152-160` will land in the wrong function and have to search — but in a codebase this dense with cross-references, a wrong pointer erodes trust in every other citation the same way the project's own Hard Rule about `file.py:NNN` citations already warns about (order dc9ffadae765, filed).

**How I verified it.** Read lines 145-165 (confirmed no fnmatch/case-sensitivity content there) and lines 218-236 (confirmed the `suppressed()` docstring, currently at 221-229, is the passage being referenced) directly from the file as it stands.

**Proposed remedy.** Update the citation to `:221-229` (or drop the specific line range and just say "see `suppressed()`'s docstring", which does not drift).

---

## QUESTIONS (not filed as findings — flagging for a second pair of eyes)

- **onomast.py `main()`, line 732** (`src = v["attestations"][0]`): this will raise `IndexError` if any live onomasticon record has an empty `attestations` list. I could not find anywhere in `name_worlds()` that guarantees `v["attestations"]` (copied straight from `resolved[cid]["attestations"]`, line 639) is non-empty, and `RESOLVED_ENTITIES.json` is produced upstream of this module. This may simply be a documented invariant of the resolution stage that I did not have in scope to verify (batch 08 does not include the resolver), so I am not filing it as a finding — but it is worth someone with visibility into the resolver confirming that `attestations` is never empty for a carried-name record.

---

## What I read and found nothing wrong in

- **src/workorders.py** (all 2097 lines): the compare-and-swap `_mutate`/`_load` machinery, `file_order`/`resolve`/`reroute`/`resolve_code`, the self-test/selftest-log routing (`is_selftest`), `battery_faults`, `cap_boundary_scan`, `ghost_orders`, `twins`/`where_split_by_code`, the entire `sweep_detectors()` detector ladder (ledgers, liveness, binding health and its identity-verdict superseding, secrets, the battery reader, drill-close, stranded-synthesis, handoff-scratch, cap-boundary regression, ghost-order, misrouted-local), `_side_channel_text`, and `main()`'s CLI handling including the `--resolve`/`--reroute`/`--twins`/`--handler` paths. This module is extremely heavily self-documented with its own fix history; I checked several of its own claimed invariants directly against the code (e.g. the LOCAL-rung denylist check, the `_fire` polarity, the "did it land, then did it exist" ordering in `resolve()`/`main()`) and all matched what the docstrings claim. No new defect found beyond the two already-filed items named in the brief (dc9ffadae765, the symbol-convention item, d1709d8e757d).
- **src/overwatch.py**: the ledger load/save/merge machinery (aside from Finding 2), the structure/semantics split, `_ask`'s local-then-cloud-then-yield budget logic (verified the `_LOCAL_BUSY[0] > CLOUD_BUDGET` gate does what its comment claims), `review()`/`verify_open()`'s "only a complete read counts as seen/verified" fix, `rotation()`, `write_report()`'s uncapped listings, and `main()`'s plant-wide interlock and singleton guard.
- **src/onomast.py**: the `well_formed()` phonotactic constraints (re-derived each of the seven checks against the four named example names by hand and confirmed the constraint that actually rejects each, matching the docstring's own self-correction), `coin_well_formed_stamped`'s three-tier fallback and its uniqueness guarantee via `_digest_tail`, `register_for`'s weighted voting and its documented-as-unwired status, `load_onomasticon`/`name_worlds`'s append-only carry-forward and retired/standing distinction, and `main()`'s atomic write with exit-code propagation.
- **src/weave_index.py** (aside from Finding 1): `designations()`'s caching and its "do not cache a failure" fix, `_records_sig()`'s per-file vs. per-directory OSError handling and its finish-the-walk behaviour, `load_records()`'s signature-gated cache, `build()`'s uncapped index entries and counted exclusions, and `main()`'s candidate-matching filters (stopnames, short keys) and atomic paired write of `ENTITY_INDEX.json`/`WEAVE_CANDIDATES.json`.
- **src/handbuilt.py**: the roster data (spot-checked citations read as consistent prose, not independently re-verified against the source wikis — out of scope for a code sweep), `compute()`, and `main()`'s write-before-print ordering, the `score` sentinel handling for `"unestimable"` axes, and the uncapped citation wrapping.
- **src/runguard.py** (all 382 lines): `read_verdict`/`read`, `_land_claim`'s CAS-based write, `holder_is_live`, and the digest-before-read ordering in `claim()`/`beat()`/`release()` — this one is unusually tight and I found no discrepancy between its docstrings and its code.
- **src/suppressions.py** (aside from Finding 3): `_load`'s three-way (missing/wrong-shape/unreadable) distinction, `add()`/`remove()`'s fail-closed behaviour on an unreadable file and on a refused write, `active()`/`suppressed()`'s case-sensitive matching, `_repo_listing()`'s single-walk optimisation, and `problems()`'s expired/dangling detection.
- **src/tuning.py** (all 286 lines): `_ollama_host()`'s config-file-based host resolution, `_answering_buckets()`/`cloud_success_rate()`'s "no evidence is never a fault" handling, `regime()`'s cloud/local/starved decision and its cache, and `workers()`'s "zero is a request, not an absence" ceiling semantics — verified `min(0, n) == 0` directly.

No unmarked caps on stored order/identity/roster/evidence text were found beyond what the brief already lists as filed; no new `except: pass`-style silent swallows were found (grepped for the bare pattern across all eight files with zero hits, consistent with the close reading).
