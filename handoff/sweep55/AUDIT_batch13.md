# SWEEP run55 — AUDIT batch 13

Modules read, every line of each: `src/assay.py` (1,914), `src/dashboard.py` (1,248),
`src/derivation.py` (811), `src/weave.py` (698), `src/catalogue_codex.py` (511),
`src/pantheon.py` (432), `src/deprecated/catalogue_local.py` (333), `src/audit.py` (271).

Method: read top-to-bottom in contiguous windows (no grep-only skimming). Where a claim could be
settled by running something read-only, it was — `assay.calibration_report()`,
`assay.band_for_quantity`, `assay.axis_score`, a monkeypatched `assay._check_constants`,
`derivation.check_graph()`, and a probe of `assay()`'s `hand_readings=` path. Nothing under
`data/`, `state/` or any ledger was written: every function driven is pure (`assay` and
`derivation.check_graph` touch no file; `silence.note` was never reached). `data/Z_FIGHTERS.json`
and `data/SWEEP_ROLL.json` were read, never written. Nothing from `panscriptum-export` was run.

Findings are ranked but not truncated: eighteen below (4 MAJOR, 7 MINOR, 7 INFO), plus the two
questions the batch note asked for, answered at the end.

---

## src/assay.py

Read in six windows covering lines 1–1914. Hardest reading given to `_check_constants`,
`_check_scores` / `_check_weights` / `_check_readings`, `_interval`'s clamping and covariance,
`axis_score`'s five-way refusal, and `assay()`'s ceiling/floor clamp. The calibration was
re-derived live and **holds**: `calibration_report()` returns
`{'interval': 0.12, 'decimal': 0.52, 'holds': True, 'sigma': 1.7973, 'band_lo': 1.725,
'band_hi': 1.870, 'margin': 0.997}` — the charter's published Kenshiro number reproduces with
the sigma sitting essentially dead-centre of the band that produces it.

### MAJOR — `assay()`'s `hand_readings=` has no Layer 1, and publishes `± nan`
**Where:** src/assay.py:1255 (signature), src/assay.py:1355 (pass-through), src/assay.py:1246-1249
(`_interval`'s between-hands term).
**What:** `assay()` validates its scores (`_check_scores`, :1311) and its weight table
(`_check_weights`, :1310). It does **not** validate `hand_readings`, which it forwards straight
into `_interval`, where `m = sum(hand_readings) / len(hand_readings)` and the sample-variance line
consume it unchecked. `_check_readings` (:706) exists and does exactly this job — but it is called
from one place only, `interval_from_hands` (:1795), which this same file documents at :1767-1778
as having **zero production callers**.
**Why it is wrong:** driven against the live module, on the charter's own Kenshiro worksheet:

```
assay("M3", CHARTER_KENSHIRO, attestation="Witnessed", worksheet="w",
      hand_readings=[nan, 3.5])   ->  𝔄 M3.52 ± nan   (interval: nan)
assay("M3", ..., hand_readings=[inf, 3.5])   ->  𝔄 M3.52 ± nan   (interval: nan)
assay("M3", ..., hand_readings=["seven", 3.5])
      ->  TypeError: unsupported operand type(s) for +: 'int' and 'str'   (from assay.py:1247)
```

Both outcomes are the two this file's own `_check_readings` docstring names as unacceptable, word
for word: "An interval of nan is not a plus-or-minus… it is not wide, it is absent, and it prints
as a bar", and a TypeError that "reports a LINE, not a fault". `moth_number` is built by f-string
(`f"± {interval:.2f}"`), so the nan reaches the printed Moth Number and, via the returned dict,
`data/ASSAYS.json`. The asymmetry is the finding: the guarded door is the dead one, the unguarded
door is the one every published number comes out of. That is the same argument order 5f99aa19c059
made when it added `_check_scores` to `instrument()` — "a gate on one of two doors is not a gate,
it is a preference" — left unfinished on the third operand.
**Confidence:** reproduced against the live module (output above); call sites for `hand_readings`
grepped across `src/` — today only `verify_math.py:2569/2571/8451/8456` pass it, so **no
production caller reaches this yet**. It is a Layer 1 hole, not a live wrong number.

### MAJOR — a renamed attestation grade dies with a bare `KeyError` where its sibling table raises `AssayIntegrityError`
**Where:** src/assay.py:791 (`vals = [SIGMA_BY_ATTESTATION[g] for g in order]`), against
src/assay.py:851-857 (`if set(ATTESTATION_FLOOR) != set(order): raise AssayIntegrityError(...)`).
**What:** `_check_constants` opens by indexing `SIGMA_BY_ATTESTATION` with each of the charter's
five grade names, with no prior key-set check. Two hundred lines later the *other* five-grade
table, `ATTESTATION_FLOOR`, gets an explicit `set(...) != set(order)` guard before it is indexed,
with a message explaining precisely why.
**Why it is wrong:** confirmed by monkeypatching the derived table and calling `_check_constants()`
directly — renaming `Transcribed` to `Reported` yields `KeyError: 'Transcribed'`, not
`AssayIntegrityError`. Because `_check_constants()` is called at import (:1914), the whole library
then fails to import on a `KeyError` whose message is one word, rather than on this module's own
integrity error naming which table diverged from the charter and what that does to published bars.
The import still fails closed — nothing wrong is published — so the cost is diagnosis, not a wrong
number. Note the module-level derivation partly masks this: `_ANCHOR_RAW = _RAW_SIGMA["Witnessed"]`
(:504) would `KeyError` first if *Witnessed* specifically were renamed; the other four grades fall
through to :791.
**Confidence:** reproduced (`KeyError :: 'Transcribed'`). This **confirms** the observation in the
batch note.

### MINOR — `band_for_quantity` reports "M0" for a quantity that clears no floor at all
**Where:** src/assay.py:383 (`out = "M0"`), loop at :384-386.
**What:** the function refuses an axis that is not on the energy ladder (:381, added under the
`kardashev_to_magnitude` initialiser-fault order) and then seeds `out = "M0"` and only ever raises
it. A positive quantity **below M0's own floor** matches no rung and leaves the initialiser
standing.
**Why it is wrong:** driven live — `band_for_quantity(1.0, "ruin")` returns `"M0"` while
`BAND_EDGES["M0"]["ruin"]` is `100.0`; `band_for_quantity(1e-9, "celerity")` returns `"M0"`
against a floor of `1.0`. The docstring asks "Which rung's floor does this quantity clear?" and the
answer for these inputs is *none*, reported as *the bottom rung*. It is the identical initialiser
fault the comment at :374-380 says it repaired, half-repaired: the off-ladder-axis case was closed,
the below-the-bottom-floor case was not. Compare `axis_score`, which gets this right —
`axis_score(1e-9, "M10", "ruin")` returns `0.0`, a clamped bound, not a band.
**Confidence:** driven against the live module (outputs above). Low blast radius: this function is
marked REPORTED DEAD at :353-361 with 0 production callers, retained by owner ruling.

### INFO (QUESTION) — the sigma table ranks Instrumented above Witnessed; the charter and two files in this batch rank Witnessed first
**Where:** src/assay.py:496-502 (`_RAW_SIGMA`: Instrumented 2.70 < Witnessed 4.08),
src/assay.py:790 (`order = ["Instrumented", "Witnessed", ...]`), src/assay.py:1738
(`ATTESTATION_FLOOR`: Instrumented 0.08 < Witnessed 0.10).
**What:** the code makes *Instrumented* the tightest (best) grade, with the comment "an instrument
reading beats a witness" (:497).
**Why it may be wrong:** `reference/keystone_volumes/00_MASTER_CHARTER.md:145` states the grade
ladder as "Witnessed → Instrumented → Transcribed → Reconstructed → Disputed", and
`src/deprecated/catalogue_local.py:19` — in this batch — restates it identically and reads the
arrow as descending quality ("Reconstructed… sits below Transcribed"). Every other pair in that
arrow is unambiguously descending quality, so the arrow appears to be a quality ordering with
*Witnessed* at the top, and the code inverts its first two rungs. Consequence, if the charter is
read that way: an entry attested *Instrumented* publishes a bar tighter than the charter's own best
grade allows. Nothing currently on the shelf moves — the anchor is Witnessed and Kenshiro
reproduces exactly — so this is a **question for the owner about the charter's intent**, not a fix.
Charter line 202 ("*seen* (Witnessed/Instrumented)") groups the two, which is the case for the
ordering being free.
**Confidence:** read the charter line and both code tables; verified `_ANCHOR_GRADE` is Witnessed
and that `calibration_report()` still holds, so I am confident about the facts and deliberately not
about the ruling.

### INFO — `axis_score` saturates at 9.9 while `AXIS_MAX` is 10.0
**Where:** src/assay.py:346 (`return 9.9 if x >= lo else 0.0`), src/assay.py:483 (`AXIS_MAX = 10.0`).
**What/why:** already named in the source as the known open bug M18 and explicitly ruled
out-of-scope by the comment block at :283-297, which also records that no record in
`data/ASSAYS.json` anchors at M10 so the branch has never fired. Recorded here only so the next
sweep does not re-file it; the marking was seen and no action is proposed.
**Confidence:** read the marking; confirmed `axis_score(1e-9, "M10", "ruin") == 0.0`, i.e. the
below-floor half of that rung is correct.

### Clean, and what was checked for
`_check_weights`, `_check_scores`, `_check_readings`, `_check_constants`'s BAND_EDGES /
INSTRUMENT_WINDOWS / FACULTY_READS / partition blocks, `_interval`'s covariance loop and
`max(var + cov, 0.0)` floor, `assay()`'s `wsum <= 0.0` refusal and both ends of the decimal clamp
(`>= 0.995 -> 0.99` matching `round(_dec*100)`'s own overflow point), `instrument()`'s
`max(1, min(30, ...))`, `_attestation_sigma`'s `min(SIGMA_MAX, ...)`, `interval_from_hands`'s
widening loop and its explicitly-declared-non-check `covers_all_signatures` — all read for
always-true/always-false conditions, off-by-one, and swallowed exceptions. Nothing further found.
The `or 1.0` at :1352 and the `grade_n <= 5` at :1535 are both marked kept-on-purpose with their
reasoning; seen and left.

---

## src/weave.py

Read in three windows covering lines 1–698.

### MAJOR (QUESTION, as the note asked) — `filtered_index()` fails OPEN on an import error
**Where:** src/weave.py:268-276.
**What:** `try: from pipeline import _STATBLOCK / except Exception: silence.note(...);
_STATBLOCK = None`, and the filter below (:281-286) then evaluates
`(_STATBLOCK is not None and _STATBLOCK.search(desc))` — i.e. that whole arm of the
mechanics filter is skipped for the entire run. `return out, dropped` (:287) carries no degraded
flag, so no caller can tell.

**Is fail-open right there? My reading: no — but the fix is a returned flag, not a refusal.**
The argument in both directions, since this is a ruling and not mine to make:

* *For fail-open.* The module still has two of its three gates (`_MECHANIC` on the name,
  `_RULES_VOICE` on the description), so it is not unfiltered; `silence.note` does fire, so it is
  not wholly silent; and `pipeline` failing to import would break far more than this.
* *Against.* This gate exists to stop D&D rules text becoming evidence that two universes share a
  continuity — the module docstring's own named failure ("tied two D&D supplements together
  through Dexterity and Channel Divinity"). When it is skipped, `main --write` (:640-661) lands
  `CONTINUITY_GROUPS.json`, `RESOLVED_ENTITIES.json` and `SHARED_STAGE_GRAPH_IDF.json` on disk,
  and `weave_index.py` / `resonance.py` / `cosmology_graph.py` then read those as the settled
  weave. The artefacts are indistinguishable from a fully-filtered run. Order 543cec75ad02's own
  measurement is the size marker: the *window* alone (`desc[:400]`) kept 54 entities the
  whole-description test drops, two of them inside the 2..60 band where they actively weight a
  shelf pair — dropping the pattern entirely is strictly worse than that. Hard Rule -1's FAIL
  CLOSED says "every layer answers 'I don't know' with STOP", and `generate.py`'s P8
  meta-language check was hardened to fail closed on exactly an ImportError.
* *Blast radius, measured.* Three callers: `pipeline.py:3135`, `tiers.py:245`, `weave.py:576`.
  The pipeline one cannot trip — `pipeline` is by definition already imported there. So the
  exposure is `weave.py` and `tiers.py` run as entry points, which is the `--write` path.
* *What I would propose, if asked.* Not a `raise`. Return the degradation
  (`return out, dropped, statblock_ok` or a third element) and let `main()` refuse the `--write`
  while still allowing the read-only report — that keeps the diagnostic value of a partial run and
  stops a degraded weave reaching disk. Filed as a question per the brief; **no change made**.
**Confidence:** read all three call sites and the `--write` block; did not run the module (it
writes into `data/`).

### MINOR — `hits[0]` is indexed unguarded in three places
**Where:** src/weave.py:206 (`nm = hits[0].get("name") or k`), :281-282 (`hits[0].get("name")`,
`hits[0].get("description")`).
**What:** `filtered_index` and `name_surprisal` both assume every value in `ENTITY_INDEX.json` is a
non-empty list of hit dicts.
**Why it is wrong:** an index key carrying `[]` — which `weave_index.py` is free to produce and
nothing here validates — raises `IndexError` out of `load_index()`'s caller with no
`silence.note`, killing the whole weave over one malformed key. Every other degradation in this
module is named and isolated (`index_staleness`, `NullThresholdUnmeasured`, the per-file write
verdicts), so this is the one unlabelled crash path.
**Confidence:** read only; I did not construct an index to trigger it, and the writer
(`weave_index.py`) is outside this batch so I cannot confirm whether an empty hit list is
reachable in practice. **Stated as unconfirmed-reachable.**

### INFO — `main()` unpacks `idf` and `N` and never reads them
**Where:** src/weave.py:580.
**What/why:** marked REPORTED DEAD at :577-579 with the order number (25ec11447b4c / sweep33
batch08); `pair_weights` (:222-231) and `null_threshold` (:351-380) carry the same marking.
Seen and left.

### Clean, and what was checked for
`components()`'s `threshold <= 0` refusal and the complete-linkage early exit, the
`NullThresholdUnmeasured` raise-instead-of-return-0.0 on both null functions, `main()`'s two
`return 1` refusal paths, the three-way per-file `--write` verdict with its out-of-step warning,
`resonance_graph`'s BFS/eccentricity, `resolve()`'s homonym separation. All the caps in this file
are removed and annotated with their rulings. Nothing further found.

---

## src/derivation.py

Read in three windows covering lines 1–811. `check_graph()` driven live: **0 problems, 112
quantities**.

### MAJOR — the ledger's `attestation_grades` CHARTER row cites four grade names the charter does not have
**Where:** src/derivation.py:123 —
`"attestation_grades": Q(CHARTER, "Part Seven: Transcribed / Corroborated / Attested / Sealed")`.
**What:** the row claims the charter fixes four attestation grades named *Transcribed*,
*Corroborated*, *Attested*, *Sealed*.
**Why it is wrong:** `reference/keystone_volumes/00_MASTER_CHARTER.md:145` gives
"Witnessed → Instrumented → Transcribed → Reconstructed → Disputed", restated at charter:684
("Witnessed / Instrumented / Transcribed / Reconstructed / Disputed / Redacted"), at charter:202,
and at charter:295. `src/assay.py:496-502` and `src/assay.py:1738` both implement exactly those
five. "Corroborated", "Attested" and "Sealed" appear **nowhere** in `src/*.py` — `grep -rn
"Corroborated" src/*.py` returns this line and one unrelated prose use in `pipeline.py:1226`. So
the ledger names three grades that do not exist, omits three that do, and gets the count wrong
(four against five). Three DERIVED rows stand on this citation: `hand_interval` (:175),
`assay_dof` (:289) and `applicability_mark` (:346), plus `attestation_quality` (:316-317) whose own
note says it is "from assay()'s own attestation table" — which is precisely the table this row
does not describe. Nothing arithmetic moves; what breaks is the provenance record, in the one file
whose stated premise is that "prose citation does not compose" and whose checker exists so a number
cannot have "no parentage at all". `check_graph()` cannot see it: it validates *kind*, parent
closure, acyclicity and non-empty `source` string — never whether a CHARTER citation is true.
**Confidence:** grepped the charter for all eight grade names and read the matching lines; ran
`check_graph()` to confirm the ledger is otherwise clean, so this is the one row a reader checking
citations would fail to confirm. Not verified: which *Part* of the charter the grade table sits in
— charter:145 is in the Part Three material and charter:684 in the entry-template material, so
"Part Seven" may also be wrong, but I did not trace the part headings.

### MINOR — `scan_constants_with_reason` promises a reason for every failure and handles only two
**Where:** src/derivation.py:619-647; docstring at :620 ("-> (names, None) on success, or
(None, reason) when the module could not be scanned"); unguarded read at :644-645.
**What:** the function catches `SyntaxError` (:648) and tests `os.path.exists` (:642), and reads
the file at :644-645 with no handler.
**Why it is wrong:** any other read failure — a `UnicodeDecodeError` on a module not in UTF-8, a
`PermissionError`, an `OSError` from a lock — propagates out of `main()`'s constants-map loop
(:791) and kills the run *after* the VERDICT banner logic has been passed but *before* it prints,
so the module exits on a traceback rather than on the verdict it exists to deliver. That is the
same shape order 90516d53d696 repaired one panel earlier (the cyclic-ledger walk that never
terminated, so "the one fault this module exists to name was the one it could not report").
**Confidence:** read only; I did not create a non-UTF-8 module to trigger it.

### INFO — the constants map silently omits every module with no uppercase constants
**Where:** src/derivation.py:794 (`elif cs:`).
**What/why:** `cs == []` (parsed fine, no module-level constants) prints no line at all, so a
reader of "where constants live" cannot distinguish a module with none from a module the walk
never reached. Advisory panel only, no number depends on it; the `SCAN_MODULES` walk itself was
verified correct by reading `_scan_modules` (:585-593), which does walk `deprecated/`.
**Confidence:** read; `check_graph()` and `_scan_modules` driven.

### Clean, and what was checked for
`check_graph()`'s four rules including the `kind`-validation added under order 72bc85d74ccf,
`visit()`'s cycle detection, `depth()`'s `seen` guard, `provenance()`'s dedupe, `_target_names`'
tuple/starred/list unwrapping, the `bool`-excluded literal count, and `main()`'s early `return 1`
(which is what makes the closing banner a printed constant rather than a second verdict — marked
and correct). Checked the `nine_measures` row against the charter: charter:133 and charter:147 do
say "the Nine Measures" (eight axes plus the evidence grade) with the extended set called "the
Twelve Measures", so that row is right. Nothing further found.

---

## src/dashboard.py

Read in five windows covering lines 1–1248, including the embedded page/JS.

### MINOR — `movement()` is a read-modify-write on a shared file inside a threaded server
**Where:** src/dashboard.py:433-506 (`hist = []` … `hist.append(row)` …
`silence.write_json(HISTORY, hist)`), against `Server(ThreadingTCPServer, daemon_threads=True)`
at :1155-1157 and `state()` calling `movement()` at :761.
**What:** every `/api/state` request reads `state/dashboard_history.json` whole, appends its own
sample, prunes, and writes the whole file back. The comment at :501-505 considers the threading
explicitly and addresses only the **temp-file name** collision ("two concurrent pollers on a fixed
temp name collide on the temp file itself"), which `write_json`'s PID+thread-qualified name closes.
**Why it is wrong:** the temp name is not the shared resource — `HISTORY` is. Two concurrent polls
both read N rows, both append one, both write N+1; the later rename wins and one sample is lost.
With a single browser the polls are serial, so this is quiet; with two tabs, two viewers, or a
scraper alongside the page, samples drop. The panel's whole subject is deltas against a baseline,
and `base` is picked from `prior` by age (:534-536), so lost samples silently widen `span` and can
turn a genuine reading into a "first reading"/"no change yet" row. The same "lost update on shared
state another writer also writes" shape the roll writers in this tree were migrated to
compare-and-swap for (`roll.update_rows`).
**Confidence:** read the server class, the handler, and the write site; not reproduced with
concurrent clients. Consequence is a lost *sample*, never a wrong number — I would rank it below
anything that moves a published figure.

### MINOR — `safety()`'s docstring says nothing here is computed; `assay_calibration` is computed every poll
**Where:** src/dashboard.py:625 ("Every field here is READ from a file, never computed by running
the thing it reports on") against src/dashboard.py:670
(`out["assay_calibration"] = _AS.calibration_report()`).
**What:** the docstring states a standing property and gives the reason ("a panel that ran the
drill would be a denial-of-service against its own library"); the code at :666-671 deliberately
breaks it, with its own comment saying so ("The calibration is RE-DERIVED here, not read from a
constant"). Two comments in one function assert opposite things.
**Why it matters:** `calibration_report()` sweeps 649 sigmas through full `assay()` calls —
**measured at 0.196 s** — on a 5-second poll, and `safety()` is the one panel builder not wrapped
in `_ttl` (`library()` and `watch()` both are, at :297 and :339). That is ~4% of the poll interval
per client, multiplied by clients. More importantly the standing property is what `main()`'s
read-only-instrument exemption at :1188-1209 leans on ("every field on the page is READ from a
file, which `state()`'s own docstring makes a standing property") — so a live exception in the
doctrine is load-bearing for a *halt* exemption argument. Not a wrong number; a docstring the code
no longer honours, in a place the doctrine is quoted from.
**Confidence:** both lines read; `calibration_report()` timed live (0.196 s).

### INFO — `metrics()` reports an unmeasured p50/p95 as `0`, where its two neighbours report `None`
**Where:** src/dashboard.py:616 (`round(pct(secs, 0.5) or 0, 1)`) against :617
(`ok_pct … if oks else None`, `tps … if tps else None`).
**What/why:** `pct()` returns `None` for an empty list; `or 0` turns that into `0`, and the page
renders "p50 0s / p95 0s" — instantaneous calls — for a tag whose rows carry no numeric `s`. The
two fields on the same line get this right. It is the "UNMEASURED IS NOT ZERO" rule this same file
states at :372-383 for the standards counter, unapplied one function away. A genuine `pct` of `0`
is also flattened into the same value.
**Confidence:** read; trivially derivable from `pct`'s own `if v else None`.

### INFO — `verb = "Wrote"` … the header count precedes the writes (see also catalogue_codex)
Not applicable here; noted under catalogue_codex.

### Clean, and what was checked for
Every panel builder is fault-isolated with its own `silence.note` tag, and the
absent-vs-unreadable distinction is drawn in all four places it matters (`throughput`'s
`os.path.exists`, `safety`'s drill `FileNotFoundError` vs generic handler, the escalation log's
two handlers, `quotas`' `worst = None` for a bucket with no readable window). `jobs()`'s
`lognames` import guard, `movement`'s three-layer history-corruption guard (container, element
type, and the `at` field the arithmetic actually uses), the `reset` branch for negative deltas,
`prior = hist[:-1]` so the baseline is never this poll's own row, the `--once` codewatch
exemption, and the fail-closed `escalation` import at :1173-1187 were all read for
checks-that-cannot-fail. Nothing further found. The JS was read for caps: none remain, and every
list (`findings`, `swallowed`, `breached`, `quarantined`) renders whole.

---

## src/catalogue_codex.py

Read in three windows covering lines 1–511.

### MINOR — the write header claims `Wrote N records` before any write is attempted, and is never corrected
**Where:** src/catalogue_codex.py:429-430 (`verb = "Would write" if args.dry_run else "Wrote"`;
`print(f"{verb} {len(written)} records from the codex:")`), against the per-record denial at
:437-446.
**What:** the count printed is `len(written)` — the number of records *built* — and the writes
happen inside the loop below it. A denied `write_record_catalogue` prints
`-> WRITE DENIED …` under the header and appends to `denied`, but the header's number stands.
**Why it is wrong:** a reader (or a log scrape) sees "Wrote 12 records from the codex" for a run in
which, say, 9 landed. This file is emphatic about exactly this class elsewhere — the denial path's
own comment at :442-444 says a verdict "honoured in prose and thrown away as a return code" is a
defect, and `rc` *is* correctly set at :495-503. The console line is the half that still overstates.
Cosmetic against `rc`, real against anyone reading the console (which is how this script is run).
**Confidence:** read the ordering; the loop at :431 is unambiguously after the print at :430.

### INFO — `joined` (the "with register text" count) is inferred by prefix rather than recorded
**Where:** src/catalogue_codex.py:432 —
`joined = sum(1 for e in rec["entries"] if not e["description"].startswith(e["type"]))`.
**What/why:** the fallback description is built at :366-367 as `f"{etype} from {title}. …"`, so the
test is a proxy for "did the Local Register supply text". A genuine transcribed description that
happens to open with the element's own type string (e.g. type `Class`, desc "Class features are…")
is counted as *not* joined. Diagnostic only — nothing is written or dropped from it — and the
undercount is in the conservative direction.
**Confidence:** read both sites; not measured against the live register (running this module writes
`data/records/` and `data/SWEEP_ROLL.json`, so it was not run).

### Clean, and what was checked for
All five collision classes are counted, printed uncapped, and surfaced before the write summary
(`norm_clashes`, `ambiguous`, `reg_ambiguous`, `dupe_elements`, `unmapped_types`) — I checked each
is actually populated on the path it claims and actually printed. The manifest declared-count
cross-check (:143-161) compares `int(group(2))` against `len(names)` and reports uncapped. The
element identity is the `(norm(etype), norm(name))` pair. The roll write is a compare-and-swap via
`roll.update_rows` against a freshly-read roll, not a whole-document land, and both write verdicts
reach `rc` at :495-503. `record_path()` prefers an existing 60-char legacy file before minting an
uncapped path. `slug()` is marked as having zero callers with the verification method stated.
Nothing further found.

---

## src/pantheon.py

Read in two windows covering lines 1–432.

### MINOR — `--full` reads `provenance` defensively and `axes[ax]` by the same trusted claim it just distrusted
**Where:** src/pantheon.py:381-383 (`for ax in A.WEIGHTS: d = rec["axes"][ax]` … `d.get("provenance", "?")`).
**What:** the comment at :365-372 records that the order which removed the old guard claimed every
`Z_FIGHTERS.json` entry carries score/cited/provenance on all eleven axes, that this was **false**
for Son Goku, and that the loop therefore "reads provenance defensively rather than trusting the
claim". It then indexes `rec["axes"][ax]` directly.
**Why it is wrong:** the claim that was disproved was about the *shape of the axes dicts*, and the
fix hardened the inner field while leaving the outer lookup on exactly the same trust. A merged
entry missing any of the eleven Measures raises `KeyError` out of `main()` in the view whose flag
is `--full`, after the ranking table has already printed — i.e. the run dies half-way through its
own output. The sibling `value()` at :249-251 has the same shape: `r["decimal"]` is `None` for any
band-only assay, and `A.LADDER.index(...) + None` is a `TypeError` inside `sorted()` at :333,
which would kill the ranking outright.
**Why it is only MINOR:** measured against the live `data/Z_FIGHTERS.json` — all 15 entries carry
all eleven axes and a non-null `decimal`, so neither path is reachable today.
**Confidence:** driven a read-only check over `data/Z_FIGHTERS.json` comparing each entry's axis
keys against `assay.WEIGHTS` and its `assay.decimal` (0 gaps).

### INFO — `merge_failed` covers only the `Z_FIGHTERS.json` merge; `--gods-only` makes rc a pure write verdict
**Where:** src/pantheon.py:268 (`if not a.gods_only:`), :430 (`return 0 if write_ok else 1`).
**What/why:** with `--gods-only` the merge block is skipped entirely, so `merge_failed` is empty by
construction and rc reflects only whether `PANTHEON.json` landed. That is correct behaviour for a
flag that asks for the gods alone — recorded so the next sweep does not read the empty list as a
check that cannot fail. It is not one; the list is unreachable *because the work it grades was not
requested*.
**Confidence:** read.

### Clean, and what was checked for
The `_incomplete` marker path now appends to `merge_failed` and notes to `silence` (the fix at
:290-300 that the comment says was previously print-only), the total-merge-failure path prints and
counts, the band-label table covers all eleven rungs so the `.get` fallback is a backstop rather
than a live path, the write verdict reaches both the console and rc, and every cap in the `--full`
view is removed with the citation wrapped rather than sliced. `compute()`'s `worksheet=sheet` is a
non-empty dict so `assay()`'s H5 band-only branch is correctly not taken. Nothing further found.

---

## src/audit.py

Read in one pass, lines 1–271.

### INFO — `--sample` accepts a negative value and dies inside `random.sample`
**Where:** src/audit.py:188 (`ap.add_argument("--sample", type=int, default=14)`), :247
(`rng.sample(pool, min(args.sample, len(pool)))`).
**What/why:** `--sample -1` reaches `random.sample(pool, -1)`, which raises
`ValueError: Sample larger than population or is negative` from inside the stdlib. Operator
ergonomics only; `weave.py:570-575` shows the house treatment (`ap.error` with a sentence saying
why the floor exists).
**Confidence:** read; not run (this module imports `pipeline` and reads the whole corpus, but
writes nothing — it was still not run, to keep the pass read-only end to end).

### INFO — a synthesis with no `provisional_magnitude` is reported under "band not on the ladder"
**Where:** src/audit.py:97-99.
**What/why:** the repair at :82-96 deliberately collapses "key missing" into the single row
`band not on the ladder: None`, which is one honest row instead of three false ones and is the
stated intent. Recorded only because the heading asserts a band was claimed and placed wrongly,
where the fact is that no band was claimed at all. Latent either way: measured by that comment at
0 of 210 synthesis rows.
**Confidence:** read; verified `PL.BANDS` really does contain `"unassayed"`
(`['M10'…'M0', 'unassayed']`), so `claims_a_band` at :97 is correct and an `"unassayed"` band does
**not** produce a false "not on the ladder" row — the thing I went looking for and did not find.

### Clean, and what was checked for
The `_JUNK` regex was read alternative by alternative for the prefix-vs-whole-name split described
at :32-41 — `characters?\b`, `category:`, `list of `, `index of ` are prefixes and the remaining
eleven are `$`-anchored, which matches the comment exactly. The denominator split at :223-226
(synthesis rows against `sources_with_synthesis`, entry rows against `entries_catalogued`, with
the unit printed) is correct and is the fix for a three-orders-of-magnitude understatement. Every
occurrence list prints whole. `return 1 if fails else 0` at :267 reaches the process. The
`d.strip()` printed at :180-181 rather than `d[:40]` is right for the reason stated. Nothing found.

---

## src/deprecated/catalogue_local.py

Read in one pass, lines 1–333.

**Quarantined and clean for the purposes of this sweep.** The unconditional
`raise SystemExit(_REFUSAL)` at :94 runs at module scope before any import of `yaml`, any config
read or any file touch, so both running and importing the module stop there; everything from :96
to :333 is unreachable by construction. The six defects below it —
the bare `open(path,"w")` third writer against `data/records/`'s two-writer contract (:316-317),
the non-atomic whole-roll rewrite inside the per-source loop (:321-322), `main()` returning `None`
(:262/:333), the absent `escalation.assert_clear` / `silence` / export-marker / `_BAD_CHARS`
guards, `slug()`'s `[:60]` identity truncation (:198), and `per_cat[key] = 0` recording a failed
Ollama call as "this category is empty" (:227-231) — are each named in the quarantine block at
:43-78 and **deliberately left unrepaired** so the file cannot look usable. Seen, and moving on
per the brief.

### INFO — the `--help` exemption keys on the *importing process's* argv
**Where:** src/deprecated/catalogue_local.py:91-93
(`if set(sys.argv[1:]) & {"-h", "--help"}: print(_REFUSAL); raise SystemExit(0)`).
**What/why:** the test reads `sys.argv`, not this module's own invocation, so any *other* program
whose argv happens to contain `-h` or `--help` and which imports this module exits 0 at the import,
printing the refusal text into that program's output. The block at :72-78 documents the exemption
and names `cascade_bridge`'s argv guard as the pattern being followed, so this is the known trade —
recorded only because "it exits 0" is the one outcome that reads as success. No importer of this
module exists in `src/` today (`grep` finds none; `derivation._scan_modules` and
`sweep_plan`/`drill`'s file walks read it as *source*, never import it).
**Confidence:** read; grepped `src/` for importers of `catalogue_local`.

**A second, useful datum from this file:** :18-19 independently restates the charter's attestation
ladder as "Witnessed -> Instrumented -> Transcribed -> Reconstructed -> Disputed" and reads it as
descending quality. That is the second in-repo witness (with `00_MASTER_CHARTER.md:145`) against
`assay._RAW_SIGMA`'s ordering — see the assay QUESTION above.

---

## Cross-batch limits, stated rather than guessed

* The `filtered_index` fail-open ruling depends on `pipeline.py`, `tiers.py` and `weave_index.py`,
  all outside this batch. I read their **call sites** (`pipeline.py:3135`, `tiers.py:245`) to
  bound the blast radius but did not audit those modules; the coordinator should confirm nothing
  else consumes a degraded index.
* The `weave.py:206/281` empty-`hits` finding depends on whether `weave_index.py` (outside this
  batch) can emit a key with an empty hit list. I could not settle that here.
* `derivation.py:123`'s citation was checked against `reference/keystone_volumes/00_MASTER_CHARTER.md`
  (a reference document, not a module). I did **not** trace which numbered Part the grade table sits
  in, so the "Part Seven" half of that citation is unverified in both directions.
* `assay.py`'s `hand_readings` finding was bounded by grepping `src/` for callers; `verify_math.py`
  is the only one and is outside this batch, so I did not read how it drives those cases.
