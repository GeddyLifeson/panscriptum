# Batch 11 sweep audit — run27

Modules read in full, every line, no sampling:
- src/dashboard.py — 766 lines (766/766 read)
- src/weave.py — 487 lines
- src/health.py — 403 lines
- src/cosmography.py — 282 lines
- src/grounding.py — 245 lines
- src/audit.py — 177 lines
- src/resync_roll.py — 81 lines

Total: 2,441 lines across 7 modules.

Supporting context read outside the batch (for tracing only, not audited line-by-line):
src/standards.py (job-silence + COVERAGE-freshness mechanism), src/lognames.py (LN.OWNER),
src/overnight.py (supervisor cycle cadence / coverage_snapshot), src/coverage.py (write site),
src/pipeline.py (records(), phase_weave caller of weave.py), src/tiers.py (weave.py caller),
src/read.py / src/feats.py (progress-line format strings matched against dashboard's regexes),
src/silence.py (note()/flush() cadence).

---

## EXTRA FOCUS — how dashboard.py decides a job is silent, and the movement-panel numbers

**dashboard.py itself does not decide job silence.** `jobs()` (dashboard.py:171-216) only
*displays* progress by tail-matching the most recent line in `read_auto.log` / `roll_auto.log`
against `RE_READ`/`RE_ROLL` (dashboard.py:58-67) — verified against read.py:1026-1027 and
feats.py:893-897, both still match, no regex drift. There is no staleness/timestamp check in
`jobs()` at all: a line that matched five minutes ago and a line that matched five hours ago
render identically.

The verdict shown in the Standards panel ("every running job is advancing") is computed
entirely in **standards.py** (out of this batch), which watches raw **log file byte size**
against `MAX_JOB_SILENCE_MIN` for every job named in `lognames.OWNER` (6 jobs: read, roll,
**pipeline**, recatalogue, sweep, calibrate) — not by parsing progress lines at all. This means:

1. **dashboard.py's own Jobs panel only tracks 2 of those 6 jobs** (READ and ROLL via
   `_read_row`/`_roll_row`, dashboard.py:196-216). `pipeline_auto.log`, `recatalogue.log`,
   `sweep.log`, `calibrate.log` have no row in the Jobs panel and no key in `movement()`'s
   tracked metrics (dashboard.py:325-333: `cited`, `settled`, `feats`, `entities read`,
   `chunks`, `standards met` — none of these is sourced from pipeline_auto.log). So when
   standards.py flags `pipeline_auto (20 min, 26894 bytes)` RED, the dashboard has **no
   corroborating detail to show** for that specific job — it cannot tell an operator whether
   pipeline is busy on one long unit or genuinely wedged, because it never reads that log's
   content, only ever the two reader/roll logs. **CONFIRMED, medium severity** — see finding
   D3 below.

2. **The `movement` block's two "stalled" metrics are downstream of a slow-cadence file, not a
   live signal.** `settled`/`cited`/`feats` all come from `data/COVERAGE.json`
   (dashboard.py:256-263, via `library()`→`_library()`, TTL-cached 30s). COVERAGE.json is
   rewritten once per supervisor cycle by `overnight.coverage_snapshot()` (overnight.py:459-469),
   and a cycle floors at `MIN_CYCLE_SECONDS = 300` (overnight.py:362) but runs far longer than
   that in practice — `coverage.py` itself is given up to 1800s, and the loop only sleeps when a
   cycle finishes *under* 5 minutes. A 30-31 minute movement window can easily fall entirely
   inside one supervisor cycle, in which case COVERAGE.json — and therefore `settled`/`cited`/
   `feats` — cannot have changed at all, **independent of whether the library is actually
   moving**. `standards met` (a scalar count of how many declared standards currently hold) is
   similarly quantized: many of the standards it counts are themselves derived from
   COVERAGE.json / OVERWATCH.json / GROUNDINGS.json, all written on cycle or sub-cycle cadences,
   so the count only changes at flip boundaries and can sit flat for a full cycle even while
   real work (chunks) is progressing. `chunks`, by contrast, is read **fresh on every single
   poll** straight from the tail of `read_auto.log` (dashboard.py:196-206, not TTL-cached, not
   file-cadence-bound) — which is exactly why it can show `+119` in the same 31-minute window
   that `settled`/`standards met` show `delta 0`. **This is a real, confirmed artefact of write
   cadence, not evidence the pipeline stopped.** See finding D2 below.

---

## dashboard.py (766 lines)

### D1 — [HIGH][CONFIRMED] `_watch()` returns a "clean" verdict on read failure, identical in
shape to a genuinely empty result
`dashboard.py:284-305`. `out = {"open": 0, "high": 0, "rounds": 0, "findings": [], "broken": []}`
is set **before** the `try` that reads `data/OVERWATCH.json`. If that read/parse fails for any
reason (torn file mid-write by the sweep, permissions, etc.), the `except` only calls
`silence.note(...)` and returns — `out` is never touched again, so the function returns exactly
the same shape as "0 open findings after 0 rounds," which the front end
(`panelWatch`, line ~689-690) renders as `"0 (0 high) after 0 round(s)"`. There is no way for
the page to distinguish "the sweep found nothing" from "the dashboard could not read the
sweep's ledger." **Failure scenario:** OVERWATCH.json is mid-write (the sweep writes it) at the
moment the dashboard polls; the page shows a clean bill of health for up to 5 seconds (or
longer, since `watch()` is TTL-cached 30s at dashboard.py:280-281) while in fact the real
finding count is unknown. This is the *exact* failure class (`silent null read into a
success-shaped default`) that `movement()` a few dozen lines below was explicitly, elaborately
hardened against (dashboard.py:335-358, the "A CORRUPT HISTORY FILE MUST HEAL, NOT WEDGE"
comment) — the fix was never applied to its sibling function in the same file.

### D2 — [HIGH][CONFIRMED] `movement()`'s `stalled` flag cannot distinguish "genuinely idle" from
"underlying file hasn't been rewritten yet"
`dashboard.py:314-398`. See the EXTRA FOCUS section above for the full trace. `stalled` is
defined at line 397 as `delta == 0 and span >= 10` with no awareness of which source each
metric comes from. `cited`/`settled`/`feats` are sourced from `data/COVERAGE.json`
(written once per supervisor cycle, often >>30 min under load — confirmed via overnight.py:362,
459-469); `standards met` aggregates many cycle-cadence-bound standards. `chunks` and `entities
read` are live/near-live. **Failure scenario, matching the reported symptom exactly:** during a
single long supervisor cycle, `read_auto.log`'s tail advances continuously (chunks +119 over 31
minutes) while COVERAGE.json sits unwritten since the cycle started, so `settled` and
`standards met` report `delta: 0, stalled: true` — read by an operator as "the library stopped
working" when the correct reading is "the coverage snapshot hasn't run yet this cycle." The
`movement` panel's own selling point (dashboard.py:315-323, "A bar that has not moved looks
identical to one that just moved... This says which") is undermined for exactly the metrics
most likely to be checked during a long-running job, because it says "stalled" for a
write-cadence artefact using the same label it uses for genuine inactivity.

### D3 — [MEDIUM][CONFIRMED] `jobs()` only tracks 2 of the 6 supervised jobs; no detail available
for the job most likely to be flagged
`dashboard.py:171-216` vs `lognames.OWNER` (READ, ROLL, PIPELINE, RECATALOGUE, SWEEP,
CALIBRATE — lognames.py:29-35). `_read_row`/`_roll_row` are the only two builders called from
`jobs()`. `movement()`'s tracked `keys` dict (dashboard.py:325-333) likewise has no
pipeline/recatalogue/sweep/calibrate entry. When standards.py's file-size-based stall detector
(standards.py:872-926, out of this batch) flags e.g. `pipeline_auto (20 min, 26894 bytes)`, the
dashboard's Jobs panel and Movement panel offer zero corroborating signal for that job — no
progress numbers, no "here's what it's doing," nothing to distinguish a legitimately long single
unit of work from a genuine wedge. standards.py's own comment (standards.py:929-930) claims
parity — *"`dashboard.py` already flags this in its movement panel — if the panel says stalled
and this standard does not, the two are measuring different things and this one is wrong"* —
but `movement()` in dashboard.py has no key for `pipeline` at all, so that claimed cross-check
cannot actually happen for this job. (This comment lives in standards.py, outside my batch, but
it makes a direct, checkable claim about dashboard.py's behavior, and the claim does not hold.)

### D4 — [MEDIUM][CONFIRMED] `throughput()` leaks a sqlite3 connection every poll; also has a
read-only-looking call with a write side effect
`dashboard.py:150-168`. `c = sqlite3.connect(path)` is opened, queried, and never closed (no
`c.close()`, no context manager, no `finally`). This function runs on **every** `/api/state`
poll — the page auto-refreshes every 5 seconds (dashboard.py:712) — so a long-lived dashboard
server leaks one open sqlite3 connection handle per poll indefinitely. Separately:
`sqlite3.connect(path)` on a path that does not yet exist silently **creates** an empty database
file as a side effect — so a dashboard that is supposed to be a pure read-only instrument
(module docstring, dashboard.py:21-24: "Nothing here computes anything of its own... so the
dashboard can never disagree with the system it is reporting on") can itself create
`state/cascade_scratch.db` before cascade_bridge ever does, which is a write, not a read.

### D5 — [MEDIUM][CONFIRMED] Hard Rule 0: a rank-then-truncate cap sits two lines below its own
fixed sibling, in the same function
`dashboard.py:296` vs `dashboard.py:301`. Line 296's trailing comment documents that the
`findings` list's cap was identified and removed as a truncation ("ALL open findings — a
monitoring cap ruled a truncation, 2026-08-24"). Five lines later, in the same function
(`_watch()`), `out["swallowed"] = sorted(f.items(), key=lambda kv: -kv[1])[:6]` is an
unremediated rank-then-slice-to-6 on the swallowed-failures breakdown. Per the project's own
Hard Rule 0 text ("Ranking is still allowed... **Ranking then truncating is not**"), this is a
live violation of the identical shape as the one fixed immediately above it. Mitigating factor:
the true total is preserved separately (`out["swallowed_total"] = sum(f.values())`,
dashboard.py:302) and rendered on the page (line 697-698), so no failure count is lost from the
ledger — only the itemized top-6 breakdown shown in the table is truncated. Flagging at medium
rather than high because the underlying data (failures.json) is untouched; only the display
list is capped.

### D6 — [MEDIUM][CONFIRMED] Unlocked read-modify-write race on `state/dashboard_history.json`
across concurrent request threads
`dashboard.py:349-369`. `movement()` performs read-hist → append-row → filter → write-tmp →
`silence.replace_retry` with no lock. The server is a `socketserver.ThreadingTCPServer` with
`daemon_threads = True` (dashboard.py:743-745), i.e. concurrent requests are handled on separate
threads within the same process. Two near-simultaneous `/api/state` requests (two browser tabs,
a curl poll alongside the page, `--once` invoked against a running server) can each read the
same `hist` list, each append their own sample, and the second thread's atomic replace silently
discards the first thread's appended row — a same-process lost-update. The atomicity fix
documented at dashboard.py:335-358 (and the `silence.replace_retry` call) protects against torn
writes and corrupt files; it does not protect against this concurrent-append race, since there
is no lock around the read→append→write sequence.

### Confirmed-clean / non-findings in dashboard.py
- `RE_READ`/`RE_ROLL` still match read.py/feats.py's current print formats — no drift (checked
  directly against read.py:1026-1027, feats.py:893-897).
- `_TTL_MEMO` (dashboard.py:219-232) is touched without a lock from multiple request threads;
  under CPython's GIL a single dict assignment can't corrupt, so the only real effect is
  occasional redundant recomputation — noted, not flagged as a bug.

---

## weave.py (487 lines)

### W1 — [MEDIUM][CONFIRMED] Mechanic-filter gate silently degrades when `pipeline._STATBLOCK`
fails to import
`weave.py:176-202` (`filtered_index`). If `from pipeline import _STATBLOCK` raises for any
reason, `_STATBLOCK` is set to `None` (weave.py:187-191) and filtering proceeds with only the
`_MECHANIC` name-regex and `_RULES_VOICE` description-regex — the docstring's claim
("reuses `pipeline._STATBLOCK` on the DESCRIPTION, which is the same test the scale_note gate
already applies... One detector, two callers, and it does not need updating per supplement,"
weave.py:183-186) silently stops being true. The only trace is a `silence.note("weave.py:187")`
call, invisible on the page unless someone reads `state/failures.json` directly. Since this
filter feeds entity clustering for the whole continuity-resolution pass, a degraded filter here
means class-feature/rules-text entries ("Ability Score Improvement", "Extra Attack" — the exact
examples the docstring cites, weave.py:179-181) can leak back into the weave as pseudo-entities
without any visible signal that the second gate stopped running.

### W2 — [LOW][CONFIRMED] `pair_weights()`/`null_threshold()` (idf-weighted variants) are dead
code carrying a live "fix" comment
`weave.py:156-173`, `weave.py:249-273`. Grepped every caller in `src/`: `pipeline.py:1771`
(`phase_weave`) and `tiers.py:194,233` (`_graph`) both call only `surprisal_pair_weights` /
`null_threshold_surprisal` / the surprisal-based `name_surprisal`. `weave.py`'s own `main()`
also calls only the surprisal variants (line 436-437). Neither `pair_weights` nor
`null_threshold` has a single caller anywhere in the tree. The "NO CAP -- the idf twin of the
same truncation removed... 2026-08-25" comment at weave.py:170-171 documents a real fix, but to
a function that is not on any live path — low severity, but worth flagging because a future
reader could reasonably assume this function is exercised/audited in production because of the
comment's presence, when it is orphaned.

### W3 — [LOW][SUSPECTED] Mechanic-description scan is truncated to the first 300-400 characters
`weave.py:196-198`: `_STATBLOCK.search(desc[:400])` and `_RULES_VOICE.search(desc[:300])`. A
mechanic whose rules-voice or stat-block cues appear only after the first 300/400 characters of
its description would not be caught by this gate. This may be a deliberate signal-density /
performance tradeoff (early sentences are the ones most likely to carry the tell) rather than a
bug — flagged as a question, not a confirmed defect.

---

## health.py (403 lines)

### H1 — [HIGH][CONFIRMED] `state/failures.json` (the project's central failure ledger) has a
cross-process lost-update race; only intra-process access is locked
`health.py:61-63` (`LEDGER = collections.Counter()`, `_LOCK = threading.Lock()`),
`health.py:85-123` (`flush()`). `_LOCK` is a `threading.Lock`, which only serializes threads
*inside one process*. `flush()`'s sequence — read `prev` from `LEDGER_PATH`, merge in-memory
`LEDGER` counts, write via a `.tmp` + `silence.replace_retry` — has no cross-process
coordination at all. health.py's own comment (lines 104-109) states the file is
*"the highest-traffic shared file in the project — the dashboard polls it, standards reads it,
and EVERY process read-modify-writes it through health.flush()."* Traced the call chain:
`silence.note()` (silence.py:290-321) calls `health.record()` on every swallowed exception and
auto-flushes every `FLUSH_EVERY` (25) records and again at process exit — and `silence.note` is
called from essentially every module in `src/`, many of which (`read.py`, `feats.py`,
`pipeline.py`, `overnight.py`, `foreman.py`, etc.) run as independent subprocesses, frequently
concurrently (overnight.py spawns read/roll/pipeline as parallel workers). **Failure scenario:**
process A and process B both flush within the same window; both read `prev` at count 10 for some
failure class; A adds 3 (writes 13); B — computed from its own stale 10 baseline, not from A's
13 — adds 5 and writes 15. A's 3 counts are silently lost from the ledger forever, with no
error, no log line, nothing — the exact "quiet bug" class this file's docstring (lines 3-20)
says the whole module exists to end. The identical unlocked read-merge-write repeats for
`SAMPLES_PATH` (health.py:124-144, the evidence-sample ring), where the `except: pass` at line
143-144 additionally swallows the failure completely (justified in-line as "the evidence bag
must never break the ledger write," but it means a torn samples-write leaves no trace at all,
not even a `silence.note`).

### H2 — [MEDIUM][CONFIRMED] `check_caches()` samples only the first 200 files per host directory
`health.py:220-253`, specifically `for fp in files[:200]:` (line 241) and `n = min(len(files),
200)` (line 250). The adjacent comment (lines 234-238) explains and justifies checking file
**size** rather than **parsing** each file, but never explains or justifies checking only the
first 200 files of what can be an arbitrarily large per-host cache directory. **Failure
scenario:** a host directory has 3,000 cached files; the first 200 (by `glob.glob` order) are
all populated (host was healthy at first) but a host outage partway through the crawl left the
remaining 2,800 empty — `check_caches()` reports "ok" for that host and the real, large-scale
breakage goes completely undetected by the one preflight check whose stated job (lines 220-223)
is exactly "a cache that is systematically empty means broken, not absent." The inverse
(populated files after the empty first 200) produces a false "all sampled entries empty" alarm.
Given this project's explicit zero-cap doctrine, and that this check runs at the head of every
supervisor cycle specifically to catch broken-vs-absent, this is a real gap in the tool's own
mandate.

### H3 — [LOW][SUSPECTED] Small host directories (<25 files) are never checked for emptiness at
all
`health.py:230-233`: `if len(files) < 25: continue`. A host with a small, entirely-empty cache
(a genuine 404 signature on a low-volume source) is skipped outright rather than flagged.
Plausibly a deliberate noise-reduction floor (matching the "sampled" framing elsewhere) —
flagged as a question rather than a confirmed defect.

### H4 — [LOW][SUSPECTED] Inconsistent chars-per-token ratio between system prompt and body
`health.py:168-188` (`check_context_budget`): `sys_toks = len(R.SYSTEM) / 4` vs
`body_toks = R.CHUNK / 3.7`. The docstring cites and justifies 3.7 chars/token specifically for
"English wiki prose" (the body); the system prompt's `/4` divisor has no comment and no
citation. Could be deliberate (system prompt is not wiki prose and a generic 4-chars/token
heuristic is more appropriate there) or an unremarked inconsistency — flagged as a question.

### Confirmed-clean / non-findings in health.py
- `check_control_chars`, `check_api_paths`, `check_state` all iterate their full input sets with
  no caps.
- `reopen_stranded`'s `for k in reopen[:20]:` (line 327) is a console-print-only truncation; the
  actual state mutation (`st["done"]["entrypass"] = [k for k in done if k not in set(reopen)]`,
  line 330) uses the full, uncapped `reopen` list. Not flagged as a Hard Rule 0 violation.

---

## cosmography.py (282 lines)

No correctness bugs, swallowed failures, caps, two-writer issues, or comment/code contradictions
found. This module is pure math (no file I/O, no exception handling anywhere in the file) with
an explicit self-validation pass (`validate()`, lines 215-253) that actively refuses a
physically-impossible census rather than silently returning one — a good example of the
project's own doctrine done right, and it correctly catches the specific historical bug its own
comment describes (Type III at 0.001 producing more galactic empires than galaxies;
KARDASHEV_MIX now sums to exactly 1.0, verified by hand: 0.90000+0.08500+0.01499+0.00001=1.0).

- **Minor/informational (not a finding):** `STARS_MILKY_WAY` (line 52) is defined and commented
  but never referenced in any computation in this file — used only as explanatory context in the
  surrounding comment, not a bug.
- **Unverifiable dependency (flag as a question, not a bug):** `kardashev_to_magnitude()`
  (lines 145-166) walks `ladder` in the order returned by `assay.LADDER` (out of this batch) and
  assumes it is sorted ascending by the band's Ruin threshold — `reached = b` is overwritten on
  every band whose edge is cleared, so an out-of-order `ladder` would silently produce the wrong
  band. Not independently verifiable without reading assay.py.

---

## grounding.py (245 lines)

### G1 — [LOW][SUSPECTED] `classify_text(text, top=3)` caps `Counter.most_common()` to 3 of 5
possible grounding types
`grounding.py:112-117`, called with its default `top=3` from `classify_source` (line 162).
`GROUNDINGS` has 5 keys (ex_nihilo, emanation, eternal_cycle, demiurgic, immanent); this always
discards the bottom 2 candidates' scores before `classify_source` can see them, so the
`runners_up` diagnostic field (used by the "contested cosmogonies" report, lines 228-233) can
never show more than the 2nd- and 3rd-ranked types. The primary `"grounding"` verdict is
unaffected (it only ever reads `ranked[0]`), so real-world impact looks small, but this is a
literal, undocumented cap on a `most_common()` call in a project with an explicit zero-cap rule.
Flagged as a question given the low apparent impact, not asserted as a confirmed defect.

### Confirmed-clean / non-findings in grounding.py
- `classify_source`'s own `cap` parameter is correctly and loudly refused
  (`raise SystemExit(...)`, lines 143-147) with a docstring (lines 128-141) that documents the
  exact prior harm (Marvel: 153 of 5,012 origin entries read, score understated 33-fold) — this
  is the pattern other modules should be held to, not a finding.
- The origin-entry scan itself (lines 153-159) is uncapped, iterating every entry in the record.
- Console print truncations in `main()` (`low[:5]`, line 231) are display-only; `args.write`
  persists the full `out` dict via `silence.write_json`. Not flagged.

---

## audit.py (177 lines)

### Design note, not a finding
`audit_invariants()` (lines 37-112) is genuinely exhaustive — verified the loop has no caps over
`recs` or `rec["entries"]`. The module's SAMPLE section (`main()`, lines 151-172) is an
explicitly documented, deliberately different pass ("a seeded random draw, printed in full so a
person can read actual rows," module docstring lines 11-14) — this is a stated design choice,
not a Hard Rule 0 violation dressed up as one. The print-truncations inside the invariants
report (`for x in v[:4]:`, line 145, with an explicit "...and N more" count at line 147-148) are
display-only; the full occurrence count (`len(v)`) is always reported. Flagging none of this.

### A1 — [LOW][SUSPECTED] Missing `provisional_magnitude` key reads identically to an invalid one
`audit.py:48-53`. `band = syn.get("provisional_magnitude")` returns `None` if the key is simply
absent from a synthesis dict rather than explicitly set to `"unassayed"`. `if band not in
VALID_BANDS:` then fires `"synthesis: band not on the ladder"` with `band=None` for that source
— indistinguishable in the report from a genuinely malformed/invalid band value. Whether this is
reachable in practice depends on whether pipeline.py always writes `provisional_magnitude` (even
as `"unassayed"`) whenever it creates a `synthesis` dict — that write site is in pipeline.py,
outside this batch, so I could not confirm or rule this out directly. Flagged as a question.

---

## resync_roll.py (81 lines)

### R1 — [HIGH][CONFIRMED — KNOWN-OPEN, re-verified] "Fixed 2026-08-25" comment claims a hazard
that is only half-fixed
`resync_roll.py:65-68`. The comment reads: *"ATOMIC: this file's own docstring warned about the
roll-clobber hazard while the code went on truncate-then-filling it. Fixed 2026-08-25."* Traced
the actual code: `main()` reads `SWEEP_ROLL.json` **once** at the top (line 33-34) into `roll`,
scans every record file on disk to compute what should change (lines 38-63), and then — if
anything changed and not a dry run — writes the **entire** `roll` object back via
`silence.write_json` (line 68), which is genuinely atomic (temp file + `replace_retry`). That
closes the *torn-write* hazard (an interrupted write leaving 0 or partial bytes). It does
**not** close the hazard the module's own docstring actually describes (lines 5-11): *"every
cataloguer (catalogue_web.py, catalogue_aurora.py, catalogue_codex.py,
recover_folder_records.py) rewrites the whole roll after each source, so two of them running
concurrently will have one clobber the other's counters with a stale copy read minutes
earlier."* `resync_roll.py` has that exact same shape internally — read-once, compute, write-
whole-file-back — so if any of those four cataloguers updates `SWEEP_ROLL.json` at any point
between `resync_roll.py`'s line-34 read and its line-68 write (a window that includes a full
`os.listdir` + per-file JSON parse of every record in `data/records/`, potentially hundreds of
files), that cataloguer's update is silently discarded the moment `resync_roll.py`'s write
lands — the identical lost-update failure the docstring's own worked example describes (Aurora's
425/681-entry writes for two sources reset to 0 by a concurrent wiki-run save). The atomic write
makes the *symptom* (corruption) go away without touching the *cause* (stale-base
read-modify-write across independently-run processes), and the "Fixed" comment now reads as
though the whole hazard is closed when only half of it is. This is precisely the KNOWN-OPEN item
flagged for this batch — confirmed still true, no change needed to the finding, but noting it is
not unique to this file: the same read-whole/write-whole pattern is stated to exist in all four
cataloguer scripts too (outside this batch), so the fix here doesn't even close the loop for
`resync_roll.py`'s own runs, let alone the wider race.

### R2 — [MEDIUM][CONFIRMED] Unordered, unresolved normalization collisions in `by_source`
`resync_roll.py:38-50`. Record files are indexed via `for fn in os.listdir(RECORDS):` — **not**
sorted, unlike `pipeline.records()`'s `sorted(glob.glob(...))` (pipeline.py:399), which this
project treats as the deliberate norm elsewhere for determinism. Each record's `source` field is
normalized (`norm()`, lowercased/alnum-only, line 26-27) and used as a dict key:
`by_source[norm(src)] = (rec, fn)` (line 50). If two distinct record files' `source` strings
normalize to the same key (differing only in punctuation, spacing, or case — plausible in a
~215-source corpus with many similarly-titled franchise variants), the dict silently keeps only
whichever one `os.listdir` happens to enumerate last, in a platform/filesystem-dependent order
that is not guaranteed stable across runs. **Failure scenario:** roll entries for both
colliding sources then resync against the *same* single record file's entry count — one of the
two sources gets a correct fix, the other silently gets the wrong number written into its
`entry_count`/`status`, and which one "wins" can change between invocations without any file on
disk changing, purely from directory-enumeration nondeterminism.

### R3 — [MEDIUM][CONFIRMED] Status default for a resynced-to-zero source is backwards
`resync_roll.py:63`: `r["status"] = "catalogued" if n else r.get("status", "catalogued")`. When
the resynced count `n` is `0`, this evaluates to `r.get("status", "catalogued")` — i.e., if the
roll entry has no pre-existing `status` key at all, the fallback value written is
**`"catalogued"`**, even though the record file that triggered this resync was just confirmed to
hold zero entries. A default in the dangerous direction: an empty source can be marked done by a
tool whose whole purpose is correcting exactly this kind of drift. Real-world reachability is
uncertain — if every roll row is guaranteed to already carry a `status` key from whichever
cataloguer created it, this branch is a no-op in practice — but the literal fallback semantics
are backwards for the `n == 0` case and are undocumented (no comment on this line explains the
intent).

### R4 — [LOW][CONFIRMED] `--dry-run` summary line reports pre-fix numbers, not a preview
`resync_roll.py:61-77`. `r["entry_count"] = n` (line 62) is only executed `if not dry:`, so in
`--dry-run` mode `roll` is never mutated. The closing summary — `have = sum(1 for r in roll if
r.get("entry_count", 0) > 0)`, `total = sum(...)`, printed as `"roll now: X/Y sources
catalogued, Z entries"` (lines 75-77) — is computed from that same unmutated `roll`, so it
prints the *current* (pre-fix) totals under `--dry-run`, identical to what it would print if no
drift existed at all. An operator using `--dry-run` specifically to preview the post-fix roll
state gets no such preview from this line — only the per-row `changed` list (already printed
above) shows what would change.

### Confirmed-clean / non-findings in resync_roll.py
- The per-file record-load exception handling (lines 42-47) correctly uses `silence.note` and
  `continue` rather than swallowing silently or crashing the whole scan.
- `changed` is computed identically whether `dry` or not (lines 59-63), so the dry-run preview
  of *which* rows would change and by how much is accurate — only the final aggregate summary
  (R4) is not.
