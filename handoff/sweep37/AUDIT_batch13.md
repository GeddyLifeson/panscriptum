# SWEEP 37 — BATCH 13 AUDIT

Modules read IN FULL, every line, 3,967 lines total:

| module | lines | read |
|---|---|---|
| `src/hostcheck.py` | 1,133 | full |
| `src/workorders.py` | 829 | full |
| `src/endpoint.py` | 522 | full |
| `src/ingest_doc.py` | 405 | full |
| `src/genre.py` | 337 | full |
| `src/entity_match.py` | 296 | full |
| `src/propagation.py` | 235 | full |
| `src/suppressions.py` | 210 | full |

Everything below was verified against source and, where a fault is behavioural, demonstrated
offline. No source file was edited. No real work order was resolved, deleted or hand-edited;
`workorders.py --sweep` was not run. The queue was exercised only against a **copy** of
`state/workorders.json` in a temp directory. No network calls were made. No process was started
or stopped.

---

## FINDINGS BY SEVERITY

### MAJOR

---

#### 1. `state/workorders.json` — 45 of 94 open orders are STILL truncated at exactly 600 characters. The code fix does not repair the data, and nothing will.
**Where:** `src/workorders.py` `file_order._change` (the removal is correct); the damage is in `state/workorders.json`.
**Confidence:** certain — measured directly.

The four field caps were removed from `file_order` today and the removal is genuinely complete.
I verified it by round-tripping through a copy of the queue:

```
filed. what len=3018 (sent 3018) tail='XX|REMEDY-AT-THE-END'
where len=900 (sent 900)  evidence proof len=2000 (sent 2000)  found_by len=400 (sent 400)
resolved. resolution len=2518 (sent 2518) tail='RR|WHY-IT-WAS-CLOSED'
```

**But removing the cap only stops NEW damage.** The orders filed while the cap was in force are
still on disk, still cut, and 48% of the live queue is in that state:

```
open orders: 94   of which `what` is EXACTLY 600 chars: 45
of those, refiled by a live detector (self-healing): 0
PERMANENTLY truncated (no detector will ever rewrite them): 45
```

Every one of the 45 is a hand-filed sweep or maintenance finding (`SWEEP34_FINDING`,
`SWEEP35_FINDING`, `RENDER_MODULE_IS_UNREACHABLE`, `A_HALT_WAS_LIFTED_BY_AN_AUTOMATED_ACTOR`,
…) under a code no detector owns. `file_order` refreshes an order only when its detector fires
again; none of these has a detector. They will sit cut for ever unless a run rewrites them.

The cuts are mid-word, and the remedy is what is missing:

```
SWEEP34_FINDING (src/scale_theories.py:23-27,104-148)
  ...rries c, G, hbar, nuclear_density and planck_length as MEASURED roots. So the ledger const

WINERROR_10055_NOT_A_KNOWN_LOCAL_TRANSPORT_FAULT (src/cascade_bridge.py _LOCAL_TRANSPORT)
  ...eman reported '0 of 36 buckets answer'. Blaming 36 providers for one local socket exhausti

SWEEP35_FINDING (binding_health.py:310-355)
  ...ation Wiki") correctly scores 50/MISBOUND. A host whose siteinfo sitename happens to be sh
```

**How much is recoverable.** I searched all 307 files under `handoff/` for each order's last 45
surviving characters: **28 of 45 tails are present verbatim in a handoff audit file and can be
restored. 17 are not** — they were filed directly by maintenance runs and run37 agents
(`found_by` = `maintenance-2026-08-27 direct measurement`, `run37 core-safety agent, observed
outside its orders`, …) whose text exists nowhere but the truncated order. Those 17 have lost
their remedy permanently.

The closed log carries the same residue: **532 of 1,029 closed orders hold a resolution of
exactly 400 characters.** That is a paper trail rather than a queue, so it is scope rather than
a second order — but it is the same loss.

I checked whether the 400-cap is still biting and it is not; the fix is live:

```
most recent resolution of EXACTLY 400 chars : 2026-08-28 23:11:53
most recent resolution LONGER than 400 chars: 2026-08-28 23:34:52
400-char closures AFTER the newest long one : 0
```

**Filed as `WORKORDER_CAP_RESIDUE_45_TRUNCATED_ORDERS`.**

---

#### 2. `hostcheck.py` — FIVE discarded write verdicts, in the module whose own `_land` docstring says the verdict is returned *because it was being discarded*.
**Where:** `src/hostcheck.py:750, 761, 871, 899, 1007`.
**Confidence:** certain — `silence.write_json` returns a bool and, by its own contract, "never raises on a denied replace".

`_land()`'s docstring (`hostcheck.py:94-97`) states: *"THE VERDICT IS NOW RETURNED, because it was
being discarded … `binding_health._land` and `suppressions._land` gate on this identical verdict
for the identical reason."* The only caller that uses a verdict is `_land_hosts`, which is a
different function. **Every actual `_land()` call ignores the boolean**, and four of the five
print a success line immediately afterwards:

| line | write | what is printed regardless |
|---|---|---|
| 750 | `_land(UNFIT, unfit)` | `-> {UNFIT}   (every rejection kept, so a gap reads as a gap)` |
| 761 | `_land(OUT, results)` | `-> {OUT}` |
| **871** | `_land(fp, r, …)` — the emptied record in `purge()` | `removed: {src} … {n} entries, {m} cache files` |
| 899 | `_land(PURGED, prev)` | `-> {PURGED}` |
| 1007 | `_land(ROSTERS, …)` | `-> {ROSTERS}` |

**Line 871 is the one that matters and it is destructive.** In `purge(dry=False)` the sequence is:
write the emptied record (verdict discarded) → then unconditionally `os.remove(fp)` every cached
page for that host (`hostcheck.py:878-885`) → then print `removed`. A denied replace on the
record — the ordinary Windows case this project documents everywhere — leaves the 262
wrong-fiction entries **in** the record while their supporting cache is **gone**, and takes the
`purged_roster` stamp with it. The docstring at 800-811 says the purge exists so "the gap it
leaves is a recorded finding rather than a silence"; on a denied write it is a silence, and the
operator is told it was removed.

Line 750 has the same inversion in miniature: the host has already been dropped from
`WIKI_HOSTS.json` by `_land_hosts` above, so a denied `UNFIT` write produces exactly the
"gap indistinguishable from a source nobody has got to yet" that the comment three lines above
says "this whole file exists to end".

**Filed as `HOSTCHECK_FIVE_DISCARDED_LAND_VERDICTS`.**

---

#### 3. `suppressions.py:98` — the waiver's REASON is stored capped at 300 characters, and one of the three suppressions on disk is sitting at exactly 300, cut mid-word.
**Where:** `src/suppressions.py:98` — `"reason": str(reason).strip()[:300]`.
**Confidence:** certain — live instance on disk.

This module's header is an argument that an inline marker is wrong precisely because *"it carries
no REASON that a reviewer can weigh"*, and `add()`'s docstring says *"A reason is REQUIRED and is
not decoration."* The stored copy is then silently truncated. This is the `workorders` shape
exactly: a stored field, no marker, no warning, and the qualifying clause of a waiver comes at
the end.

Measured on `data/SUPPRESSIONS.json`, 3 rows:

```
len=175  secret_scan  src/drill.py
len=137  secret_scan  handoff/*/AUDIT_*.md
len=300  secret_scan  data/feats/bloons_fandom_com/Encrypted.json     <-- AT THE CAP
```

The truncated one ends:

> `…Confirmed 0 blocking hits on a full re-scan of the export SITE tree; this only sur`

The sentence that was cut is the waiver's own **scope caveat** — "this only sur[faces/applies
to …]" — which is the single clause a reviewer needs in order to decide whether the exemption is
still narrow. One in three suppressions has lost it.

The display truncations at `:165` (`[:60]`) and `:205` (`[:44]`) are fine and should stay: a
display cap is reversible.

**Filed as `SUPPRESSION_REASON_STORED_CAPPED_AT_300`.**

---

#### 4. `ingest_doc.record_path()` — containment matching with no boundary and no ambiguity guard binds a new book to the wrong franchise's record.
**Where:** `src/ingest_doc.py:154-164`.
**Confidence:** high on the mechanism (demonstrated); latent today.

The fallback is `if want in base or base in want`, first match in `os.listdir` order wins, with no
separator boundary, no minimum length, and no refusal on multiple matches. `data/records/` holds
32 slugs of eight characters or fewer (`dc`, `arms`, `doom`, `halo`, `dune`, `alien`, `baki`,
`xcom`, …), and any of them is a substring of plenty of real source names. Demonstrated:

```
'Marvel vs DC'       slug='marvel-vs-dc'       -> dc.json
'DC Elseworlds'      slug='dc-elseworlds'      -> dc.json
'Alien vs Predator'  slug='alien-vs-predator'  -> alien.json
'Doom Eternal'       slug='doom-eternal'       -> doom.json
'Halo Infinite'      slug='halo-infinite'      -> halo.json
'Dune Messiah'       slug='dune-messiah'       -> dune.json
```

`mine()` uses this path to load AND to write back the record, so an owner-supplied sourcebook for
a source that does not yet have its own record file would have its entire entity extraction merged
into another franchise's record — and `main()` would stamp that record's `provenance` with the
wrong book. That is the "wrong fiction filed as research" family `hostcheck.py` exists for,
arriving through a different door.

**It is latent right now, and I checked rather than assumed:** all 193 sources on
`CHARACTER_SWEEP.json` resolve to an exact `slug + ".json"` file, so the containment branch is
never reached today. But `ingest_doc` is the *new-material* path — the one place a source
routinely arrives without a record — so the branch exists for exactly the input that triggers it.

Second, smaller defect in the same loop: `base = fn[:-5]` assumes every entry is `*.json`.
`data/records/` currently contains `getter-robo.json.precatfix`, which yields the nonsense base
`getter-robo.json.pre`. Harmless for that name, but the function can return a path to a
non-JSON file, which `mine()` then `json.load`s.

**Filed as `INGEST_RECORD_PATH_UNBOUNDED_CONTAINMENT`.**

---

### MINOR

---

#### 5. `ingest_doc.py:279` — entity descriptions are stored capped at 2,000 characters, and this corpus holds descriptions six times longer.
`"description": (e.get("description") or "").strip()[:2000]` is a stored cap on catalogue data,
unmarked. I measured the whole corpus (216 record files, 282,822 entries): no description is
currently sitting at exactly 2,000, so nothing has been cut **yet** — but the longest legitimate
description on disk is **11,634 characters** (`the-elements-beyond.json`, "Deepling"), and the
files with the most long descriptions are precisely the homebrew/sourcebook sources this module
targets (`unearthed-arcana…` 71 over 1,500 chars, `the-elements-beyond` 44,
`kibblestasty-techno-psionic-line` 29). Other writers store those in full; this one would take
the first 2,000. Hard Rule 0 with a measured margin against it.

**Filed as `INGEST_DOC_DESCRIPTION_STORED_CAP_2000`.**

---

#### 6. `workorders.py:534, 537, 678` — three detectors build a truncated `what` and pass NO uncapped `evidence`. Two of them file BLOCKING orders.
The module knows the right shape and says so twice: `PREFLIGHT_PROBLEM` (`:127-137`) and
`BATTERY_GRADED` (`:210-215`) name the count, label the sample as "first three", and carry the
complete list in `evidence`. `STRANDED_SYNTHESIS` (`:761-778`), added today, does the same and
even appends `(+N more)`. Three older detectors do neither:

| line | code | severity | truncation | evidence passed |
|---|---|---|---|---|
| 534 | `LEDGER_STRUCTURE` | **BLOCKING** | `json.dumps(bad)[:300]` | none |
| 537 | `LEDGER_CHAIN` | **BLOCKING** | `chain_problems[:3]`, count not stated | none |
| 678 | `SECRET_STAGED` | **BLOCKING** | `hits[:5]`, count not stated | none |
| 523 | `DETECTOR_FAILED` | MAJOR | `str(exc)[:160]` | none |

So a BLOCKING order can say "the ledger hash chain does not verify: A; B; C" when there are
fifty problems, with no complete copy anywhere and no "first three of N" to warn the reader.
This is the `file_order` cap that was removed today, relocated one layer up into the callers that
compose the text.

**Latent, and I checked rather than assumed:** none of these four codes is currently open (the
detectors are quiet), so no order in the live queue is damaged by this today.

**Filed as `WORKORDER_DETECTOR_WHAT_CAPPED_NO_EVIDENCE`.**

---

#### 7. `hostcheck.null_rate()` — the cache key still omits `by`, which selects the universe the control sample is drawn from.
`src/hostcheck.py:525` — `key = (host, exclude, sample)`.

Today's fix added `exclude` and `sample` for the right reason: they are part of the question. `by`
is the same kind of parameter and is not in the key. `exclude` says *which roster to leave out*;
`by` says *which rosters exist at all*. The two callers genuinely disagree about it —
`sweep()` passes `entities_by_source()` (read from `CHARACTER_SWEEP.json`) while `adopt()` builds
`by` from `weave_index.load_records()` — so the same host with the same `exclude` and `sample`
can have two different correct baselines, and the cache would answer the second with the first.

Contained today only because `main()` dispatches exactly one of `--adopt` / `--repair` / `--rosters`
per process, so `by` is constant per run. It is a module-level cache in an importable module with
public `score(host, names, source, by=…)`, so nothing enforces that. `by` is an unhashable dict,
which is presumably why it was left out; a digest of its keys would serve.

**Filed as `NULL_RATE_CACHE_KEY_OMITS_BY`.**

---

#### 8. `hostcheck.sweep(--repair)` picks the replacement host by RAW RATE, the measure this module says must not decide.
`src/hostcheck.py:683-697`. `best = (0.0, None)`; `if ok and p["rate"] is not None and p["rate"] > best[0]`;
early exit `if best[0] >= GOOD`; gate `best[0] > DEAD`. All raw hit rate.

`score()`'s own docstring (`:562-587`) is an argument that this reading is wrong — *"Judged
absolutely, 33% is a weak result … Both readings were made in this project and both were wrong"* —
and `adopt()` (`:1036-1057`) selects by LIFT with a comment explaining that storing the rate in
the lift slot was a bug. The two passes rank candidates by different measures.

Bounded, not fatal: candidates must first pass `verdict in ("holds","partial")`, which *is*
lift-based, so the raw-rate comparison only reorders hosts that all cleared the lift bar. But it
systematically prefers generous hosts (Wikipedia at 50% baseline over a specific wiki at 45%
held), which is the exact preference `LIFT` was introduced to remove.

**Filed as `HOSTCHECK_REPAIR_RANKS_BY_RATE_NOT_LIFT`.**

---

#### 9. `ingest_doc.main()` discards `mine()`'s completion verdict and always exits 0.
`src/ingest_doc.py:399-401` — `if a.mine: mine(a.source)` then `return 0`.

`mine()` returns `True` only when every chunk was processed, and `False` on both of its early
stops: 60 consecutive transport misses (`:260-263`) and a denied record write (`:309-314`). Both
are exactly the conditions an operator or a scheduler needs to see. A run that mined 3 of 262
chunks and stopped exits with the same success code as one that finished. This is the discarded
verdict the rest of the file argues against at length in three separate comments.

**Filed as `INGEST_MAIN_DISCARDS_MINE_VERDICT`.**

---

#### 10. `ingest_doc.py:391` — a citation by line number that has drifted.
The comment reads *"same discipline this file argues for at 233-245 re: write_record_catalogue"*.
Lines 233-245 are the chunk-accumulator tail, `record_path`, `_key` and a `print`. The
`write_record_catalogue` discussion is at 291-314. The house idiom is to cite by symbol.

**Filed as `INGEST_DOC_CITATION_BY_DRIFTED_LINE_NUMBERS`.**

---

### INFO — real, recorded, not worth an order

* **`hostcheck.null_rate:536`** — `foreign = sorted(set(foreign))[::max(1, len(foreign) // sample)][:sample]`
  computes the stride from the **pre-dedup** length while slicing the **deduped** list. Measured
  on the live corpus (193 sources): raw 561 → dedup 538 → stride 14 → **39 names instead of 40**.
  Correct in kind, negligible in size. Not filed.
* **`endpoint.py:379` `MODE_HTML`** — defined, never used anywhere in `src/`, and `detect()` has
  no branch that can return it; an HTML-only host is reported `MODE_DEAD`. The HTML machinery is
  live and correct, but it is reached through the `pages:` sentinel in `feats.py:294,1203` and
  `scout.py:245,281`, not through this constant. A mode constant the resolver cannot produce.
* **`endpoint.py:359-360`** — `if __name__ == "__main__": sys.exit(main())` sits **above** the
  definitions of `MODE_HTML`, `html_text`, `fetch_html`, `PAGES_FILE`, `source_pages` and
  `register` (363-523). Run as a program, the module never defines its second half. Harmless for
  today's `main()`, which touches none of them; a trap for the next line added to it.
* **`endpoint._save:160-162`** — on a failed `json.dump` this returns `False` leaving the partial
  `tmp` on disk. `hostcheck._land_hosts` handles the same case with `_unlink(tmp); raise`, and
  `silence.write_json` calls `_discard_tmp`. Litter only.
* **`propagation.main()` `--from/--to`** — a shelf absent from the graph and a shelf genuinely
  disconnected both print `DISCONNECTED (no shared furniture at any remove)`. The default survey
  path distinguishes them (`?? not in graph`); the targeted path does not. Two different facts,
  one sentence.
* **`propagation.load_graph()`** — no error handling; a missing or malformed
  `SHARED_STAGE_GRAPH.json` exits with a traceback, and `main()` returns no exit code at all.
* **`hostcheck.purge():861`** — `n_entries = len(...)` inside the per-record loop overwrites
  rather than accumulates. One record per source today, so it is correct today.
* **`suppressions.problems():169`** — globs the entire repo tree once per wildcard suppression.
  `suppressions.main():205` does `r.get("path")[:34]`, which raises on a row with no `path`.
  `add()` does not validate `ttl_days`, so a negative value files an already-expired suppression.
* **`entity_match.candidates()`** docstring says it "Returns a list of {name, score, reason}"; it
  returns a dict. The described list is the `matches` key.
* **`entity_match.embed_available()`** — confirmed still dead: the only two matches for the name
  in `src/` are the `def` at `:276` and the docstring mention at `:44`. Already filed as
  `c421410c2194` and awaiting an owner decision; **not re-filed**.

---

## WHAT IS HEALTHY — verified, not assumed

* **`workorders._mutate` is a correct compare-and-swap, and I proved it rather than trusting the
  docstring.** Digest taken before the read (`_load(with_digest=True)`, `:226`), per-attempt temp
  name carrying pid and attempt (`:267`), `replace_if_unchanged` (`:270`), the refusal reason
  bound and reported rather than swallowed (`:273`), temp cleaned on refusal, and on exhaustion it
  returns `(False, None)` and writes to stderr — it never reports a lost write as success. Driven
  against a copy with a writer mutating the file on every attempt: `landed=False`, value `None`.
* **All three mutators route through it:** `file_order` (`:343`), `resolve` (`:391`), and
  `resolve_code` (`:413`, via `resolve`). There is no fourth write path to `OPEN_FILE`.
* **`resolve()` tests landed-then-existed in that order** (`:391-398`), so "your close was lost"
  and "no such open order" stay distinguishable — and the paper trail is appended only after the
  deletion lands (`:399-405`).
* **The five removed caps are genuinely gone**, demonstrated by round-trip: `what` 3,018,
  `where` 900, evidence 2,000, `found_by` 400, `resolution` 2,518, all byte-exact including the
  trailing remedy.
* **`hostcheck.null_rate`'s unmeasured-control handling is correct end to end.** `probe()` returns
  `rate=None` on a failed request; `null_rate` returns `None` rather than 0.0 and **does not
  cache the failure**; `score()` propagates `None` into `lift`, suppresses the aboutness veto
  (which would raise on `None >= float`), and buckets the result as `UNREACHABLE` so `sweep()`
  retries rather than repairs. The `exclude`/`sample` cache-key fix is present at `:525`.
* **`hostcheck._land_hosts`** is a proper key-wise CAS merge with a no-op guard, a refusal to heal
  an unreadable `WIKI_HOSTS.json` by starting empty, per-attempt temp names, and both callers
  (`:749`, `:1079`) gate their success message on the verdict.
* **`hostcheck.candidates()`** truncates only the speculative list; grounded hosts (neighbours,
  Wikipedia, dandwiki) are returned whole and first. `adopt()` scans the whole list.
* **`endpoint._save` and `endpoint.register`** are both correct CAS merges; `register` raises
  rather than returning quietly on an unreadable file or on exhausted attempts, and the
  once-unreachable `return d[source]` is gone.
* **`endpoint.detect`** expires only DEAD verdicts, under a documented asymmetry, and mutates the
  cache under `_LOCK` with `_DIRTY` recording what this process actually earned.
* **`endpoint.fetch_raw`** distinguishes 404/410 from a refusal in the ledger rather than
  reporting both as absence.
* **`ingest_doc`'s three writes are gated and the directions are right:** `pages.json` raises into
  a `main()` handler that stops the sequence (`:119-124`, `:356-365`); `register()` returns `None`
  on a denied host write and `main()` reports it and exits 1; `write_record_catalogue` denial
  rewinds `known` and stops **without** advancing the cursor; the cursor denial is reported but
  does not stop, which is the correct asymmetry (the cursor may lag, never lead).
* **`ingest_doc.mine`'s oversize-page re-split** (`:219-235`) is correct and the resume-cursor
  monotonicity claim holds: splitting only adds boundaries, so chunk *k* can only start earlier.
* **`genre.py` is clean on Hard Rule 0 in both directions.** `classify_text(top=None)` returns all
  eleven genres (the `Counter` is seeded for every genre, so `most_common(None)` cannot omit a
  zero-scorer), `classify_source` refuses a numeric `cap` loudly, the confidence denominator is
  the full field, `runners_up` is the full field minus the winner, and `main()`'s low-confidence
  listing prints every flagged source. The `--write` verdict is gated and returns 1 on denial.
* **`entity_match`** has no cap by default, flags `truncated` when a caller passes `limit`, and the
  qualifier gate is genuinely absolute — a conflict short-circuits before any score is computed,
  so no similarity value can overrule a continuity marker. Both early returns carry the full
  return shape including `blocked_by_qualifier`. Sorting is deterministic (score desc, name asc).
* **`propagation.observed_mark`** — the trailing `return 0` is genuinely unreachable
  (`ascension_years(1) == 1.0**1.35 - 1.0 == 0.0`, so the loop's last iteration always matches),
  and the docstring says so explicitly and explains that the honest `[^0]` comes only from the
  `lag < 0` guard. Dead line, correctly annotated as such.
* **`suppressions`** — `_load` distinguishes absent from unreadable; `add()` refuses to write on
  top of an unreadable file and raises rather than returning a row that was not committed;
  `active()` fails closed; `suppressed()` uses `fnmatchcase` so a mis-cased pattern fails shut and
  surfaces as DANGLING; `problems()` reports unreadability as a fault rather than as zero
  problems; `main()` refuses `--check --list` together. The only defect is the stored `[:300]`.

---

## COVERAGE

Recorded by this batch:

```
python -c "import sys;sys.path.insert(0,'src');import sweep_plan;print(sweep_plan.record('run37',[...],batch=13))"
```

Recorded via `sweep_plan.record('run37', [...], batch=13)` — all eight modules now stamped
`{'run': 'run37'}`.

## ORDERS FILED

| id | severity | code |
|---|---|---|
| `fc8e20f90ee9` | MAJOR | `WORKORDER_CAP_RESIDUE_45_TRUNCATED_ORDERS` |
| `1b15acd3f7b2` | MAJOR | `HOSTCHECK_FIVE_DISCARDED_LAND_VERDICTS` |
| `7a6362fa3c91` | MAJOR | `SUPPRESSION_REASON_STORED_CAPPED_AT_300` |
| `66e007cf54d5` | MAJOR | `INGEST_RECORD_PATH_UNBOUNDED_CONTAINMENT` |
| `baf4a18d1f1a` | MINOR | `INGEST_DOC_DESCRIPTION_STORED_CAP_2000` |
| `e6385a07a3fd` | MINOR | `WORKORDER_DETECTOR_WHAT_CAPPED_NO_EVIDENCE` |
| `4ff1db780b99` | MINOR | `NULL_RATE_CACHE_KEY_OMITS_BY` |
| `e2f0b13c766f` | MINOR | `HOSTCHECK_REPAIR_RANKS_BY_RATE_NOT_LIFT` |
| `afd7aa05efb4` | MINOR | `INGEST_MAIN_DISCARDS_MINE_VERDICT` |
| `4922a303e614` | MINOR | `INGEST_DOC_CITATION_BY_DRIFTED_LINE_NUMBERS` |

All ten landed with `what` between 859 and 2,549 characters — every one past the old 600-char
cap, which is incidentally a tenth proof that the `file_order` fix is live.

Not re-filed: `entity_match.embed_available()` is still dead, already filed as `c421410c2194`,
awaiting an owner decision.
