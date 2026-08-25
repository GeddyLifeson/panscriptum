# Audit batch 04 — sweep #24

Files read, in full, line by line (not sampled):

- `src/foreman.py` — 1265 lines, all read.
- `src/endpoint.py` — 371 lines, all read.
- `src/entity_match.py` — 279 lines, all read.
- `src/anchors.py` — 233 lines, all read.
- `src/recover_folder_records.py` — 173 lines, all read.
- `src/repass_bands.py` — 113 lines, all read.

Cross-references made outside the batch, for verification only (not audited for their own
defects): `src/silence.py` (`replace_retry`, `write_json`), `src/pipeline.py`
(`write_record_catalogue`, `write_record`), `src/scout.py` (`sweep`, `scout`), `src/feats.py`,
`src/hostcheck.py`, `src/completeness.py` (callers of `endpoint.*`).

---

## foreman.py

### MAJOR — `foreman.py:801-808` `_function_source()` discards class qualification, can silently patch the wrong function — VERIFIED

```python
want = symbol.split("(")[0].split(".")[-1].strip()
for node in _ast.walk(tree):
    if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and node.name == want:
        ...
        return "".join(lines[start:end]), start, end
```

`finding.get("symbol")` is explicitly expected to be dotted (`ClassName.method`, or
module-qualified) — the code itself strips to the last component with `.split(".")[-1]`. But
having stripped it, the lookup then matches on **bare name only**, walking the whole AST with
`ast.walk` (breadth-first, so top-level defs are found before class methods, and two methods of
the same name in different classes are disambiguated only by their source order) and returning
the **first** `FunctionDef`/`AsyncFunctionDef` with that name anywhere in the file. If an
overwatch finding names `ClassB.compute` and `ClassA.compute` exists earlier in the same module,
`attempt_patch()` will fetch `ClassA.compute`, hand it to the model as "the function the claim is
about," and — if the checks happen to still pass — commit a patch to a function that was never
the one reported broken, while the actually-flagged function is left untouched and the finding
gets silently retired or left open based on an unrelated function's behavior. This is the
signature failure this same function goes to great lengths to prevent elsewhere (`regex_touched`,
`lines_changed`, `_checks_pass`) but the identity of "the function under discussion" itself is
never verified.

**Scenario:** overwatch flags `foo.py: Reader.parse` as wrong. `foo.py` also has a module-level
or earlier-class `def parse(...)` used for something unrelated. The patch pipeline "fixes" the
wrong `parse`, checks pass because nothing exercised by `verify_math`/`allsweep --quick` touches
either function's real behavior, and the patch is kept — with the actually-reported defect intact
and a different function silently altered.

### MAJOR — `foreman.py:1205` `round_once()`'s `--patch` selection is a stable `[:3]` slice with no rotation — VERIFIED (Hard Rule 0 shape)

```python
for f in sorted(open_f, key=lambda x: -(x.get("severity") == "high"))[:3]:
    res = attempt_patch(f, dry=dry)
    ...
    if res.get("retire") and not dry:
        _retire(f)
```

`open_f` is rebuilt fresh from `OVERWATCH.json` every round, `sorted()` is stable, and JSON/dict
insertion order is preserved across loads — so unless the underlying JSON content itself changes,
this same top-3 (high severity first, ties in original order) is selected **every single round**.
Most `attempt_patch` failure paths (`"model unreachable"`, `"GPU busy..."`, `"patch changes N
lines"`, `"refused: the patch alters a regex literal"`, `"reverted: ..."`) do **not** set
`retire`, so a finding that keeps failing for a structural reason (e.g. `MAX_PATCH_LINES`,
persistent regex touch, a module that never imports cleanly) occupies one of the three slots
forever, and any finding ranked 4th or later by this sort — including every other high-severity
one — is never attempted at all, for as long as the foreman keeps looping. This is the exact
"cap that returns a smaller universe wearing the same shape as the real one" pattern the project's
own Hard Rule 0 names, just applied to the patch queue instead of a roster.

### MINOR — `foreman.py` diagnostic `silence.note()` site strings are stale line numbers — VERIFIED

Several `silence.note()` calls carry a hardcoded `"foreman.py:<line>"` label that no longer
matches the line it sits on, e.g. `silence.note("foreman.py:497")` at actual line 661 (inside
`run_charter_regression`), `"foreman.py:824"` at actual line 1087 (`owner_queue`),
`"foreman.py:942"` at actual line 1219 (`round_once`), `"foreman.py:967"` at actual line 1252
(`main`), `"foreman.py:595"` at actual line 827 (`_literals`). These offsets are not a single
consistent shift (164, 232, 263, 277, 285 lines off respectively), so they are organic drift from
edits, not a one-time renumbering that could be mechanically corrected. This directly undermines
`triage_swallowed()`'s own stated diagnostic value ("the class names the module and the line, and
a class that is 90% of the total is a single fault wearing thousands of hats") — a maintainer
chasing the top class in `state/failures.json` by its site string is sent to the wrong function.
Not a logic bug, but it degrades the one tool built specifically to make swallowed failures
legible.

### MINOR — `foreman.py:989-991` model-patch backup filenames can collide within the same second — VERIFIED

```python
backup = os.path.join(BACKUPS, f"{module}.{int(time.time())}.py")
shutil.copy2(path, backup)
```

`round_once(patch=True)` can attempt up to three findings per round via `sorted(open_f, ...)[:3]`.
If two of those three findings target the **same module** and both are processed within the same
wall-clock second, the second `attempt_patch()` call computes the identical backup path and
`shutil.copy2` overwrites the first finding's pre-patch backup with a copy of the file *after* the
first patch already landed. Each call's own revert-on-failure still works correctly (it reads the
`backup` variable set in that call, from the state just before that call's own patch), so no
in-flight revert is broken — but the backup archive loses the true pre-first-patch snapshot,
which matters if a human later wants to audit what a specific patch actually changed.

### MINOR — `foreman.py:190-194` `scout_hostless()` calls a hard-capped, non-rotating sweep — VERIFIED (via `scout.py`)

```python
res = SC.sweep(limit=4)
```

`scout.sweep()` (`src/scout.py:237-241`) does:

```python
todo = hostless()
order = sorted(todo, key=lambda s: -len(todo[s]))
if limit:
    order = order[:limit]
```

`order` is sorted **deterministically** by page count descending, then sliced to `limit`. Since
`hostless()` returns the same set of sources until one is successfully resolved (removed by
`register()`), and the sort key does not change between rounds, the same top-4-by-page-count
sources are re-attempted by this remedy on every foreman round, and any hostless source that is
not in that top 4 is never scouted at all as long as at least four larger-page-count sources
remain unresolved. This is the same shape as `foreman.py:1205` above, one call site earlier in
the pipeline, and it is a hard rule 0-flavoured cap even though `scout.py` itself is outside this
batch. Flagging here because the cap is invoked from this batch's file at this call site.

### MINOR — `foreman.py:409-411` `kill_stalled_job()` conflates "standard not found" with "standard healthy" — VERIFIED

```python
row = next((r for r in rows if r["standard"] == "every running job is advancing"), None)
if not row or row.get("holds"):
    return True, "no job is stalled now"
```

This remedy is only invoked because the orchestrator already determined this exact standard is
breached (it is keyed in `REMEDIES` under that name and `round_once` only calls remedies for
standards present in `orders`). It then re-queries `ST.check(D.state())` from scratch. If that
fresh call ever fails to surface a row with this exact name (a rename in `standards.py`, an
exception inside `ST.check` for this one standard, timing skew between the two `state()` reads),
`row` is `None` and the function reports the identical success message as the legitimate
"currently healthy" case: `did=True, "no job is stalled now"`. A genuinely stalled job and a
standards-lookup failure are indistinguishable to the caller and to the operational log. Given
this project's stated signature failure class is exactly this kind of conflation, it is worth
recording even though the practical trigger (a standard vanishing from `ST.check()`'s output
between two calls) is narrow.

### CONFIRMED (known suspect, characterised) — `foreman.py:996` writes a live `src/*.py` non-atomically — VERIFIED

```python
with open(path, encoding="utf-8") as f:
    lines = f.readlines()
lines[start:end] = [new]
with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
good, why = _checks_pass(module)
if not good:
    shutil.copy2(backup, path)
    ...
```

Confirmed as described: this is a bare truncate-then-fill on a `.py` file that is itself imported
by other running processes (every module in `src/` is importable, and several foreman remedies
and standards/dashboard processes import modules from `src/` on their own schedules). A reader
that imports `module` in the gap between the truncating `open(path, "w")` and the completed
`writelines` gets a syntactically invalid or truncated file — `SyntaxError` at best, a partially
overwritten function silently accepted at worst if the truncation happens to land after a
complete statement. Unlike `foreman.py`'s JSON writers (which at least use `.tmp` + rename, even
if not through `silence.write_json`), this write path has no `.tmp` staging at all. Backup/revert
protects against a *bad patch*, not against a *reader catching the file mid-write*.

### CONFIRMED (known suspect, characterised) — `restart_reader` / `kill_stalled_job` remedy-horizon mismatch — VERIFIED

`_restart_horizon()` (`foreman.py:306-339`) is correct as written and does exactly what its own
docstring says: it looks up whether the killed job's fragment is in `overnight.STANDING`, and
reports either "restarts within 300s" or "NOT in the keeper's STANDING set -- nothing restarts it
until the supervisor's next MAIN LAP (42-44 min typically, 4h at worst)". Both `restart_reader()`
and `kill_stalled_job()` correctly call this and report the true horizon rather than the old
blanket "supervisor restarts next cycle" claim. The remedies genuinely cannot make `read.py` or
`feats.py --roll` restart any faster than the supervisor's own MAIN LAP — they can only kill, not
relaunch — which is exactly what the module docstring says ("Which of the three candidate real
fixes to apply is the owner's ruling"). This is accurately self-documented, not a live bug beyond
what the code already discloses.

### VERIFIED, no new defect — `foreman.py:83-94` model-patch gates (`_checks_pass`, `regex_touched`, `lines_changed`)

Re-derived independently and all three now measure what their docstrings claim: `lines_changed`
sums `max(i2-i1, j2-j1)` over non-equal opcodes (a true "lines touched" count, not a net delta);
`regex_touched` compares the *sets* of metacharacter-bearing string literals before/after,
catching a changed regex even when line count is unchanged; `_checks_pass` reads
`RESULT:\s*\d+\s+passed,\s*(\d+)\s+FAILED` via regex rather than substring-matching `"0 FAILED"`.
No residual bug found in these three.

---

## endpoint.py

### CONFIRMED, extended — `endpoint.py:200-233` `fetch_raw()` collapses every failure mode to `(t, None)` — VERIFIED, with callers enumerated

```python
def one(t):
    url = raw_url(host, t)
    if not url:
        return t, None
    try:
        body = _get(url, timeout=40)
    except urllib.error.HTTPError as e:
        if getattr(e, "code", None) in (404, 410):
            silence.note("endpoint.py:fetch_raw-absent")
        else:
            silence.note("endpoint.py:fetch_raw-refused-%s" % getattr(e, "code", "?"))
        return t, None
    except Exception:
        silence.note("endpoint.py:fetch_raw")
        return t, None
    ...
```

The comment at 210-216 candidly admits the fix is only "make the two cases legible in the
ledger" — the `silence.note` site string now distinguishes absent-vs-refused for anyone reading
`state/failures.json` by class name, but **the return value to the caller is still identical**:
`fetch_raw()`'s output dict simply omits the title whether it 404'd, was refused with 403/429/500,
or the request raised (timeout, connection reset, DNS failure). `exists_raw()` inherits the same
ambiguity, since it is `sorted(fetch_raw(...))`.

**Callers, traced from this batch:**
- `src/feats.py:437` — `return EP.fetch_raw(host, titles)` inside the raw-mode branch of the
  corpus reader's own page-fetch path. A title missing from the returned dict because of a
  transient 429/500/timeout is indistinguishable, to `feats.py`, from a title that genuinely does
  not exist on that wiki — which for the actual corpus-reading job means real, recoverable
  material can be treated as "this entity is not documented here" and never retried.
- `src/hostcheck.py:135` — `got = EP.fetch_raw(host, names[:12])`, used to verify a *candidate*
  host actually serves a source's known names before adopting it. A transient failure on even a
  few of the 12 probe titles lowers the apparent match count and can cause a genuinely correct
  host to be rejected as a host-adoption candidate — directly undermining `foreman.py`'s
  `adopt_hosts()` remedy in this same batch, whose entire job is closing the "sources with a
  reachable wiki" standard.
- `src/hostcheck.py:246` — same pattern, a second verification call site.

(`feats.py` and `hostcheck.py` themselves are outside this batch and were not audited beyond this
call-site trace.)

### CONFIRMED, extended — `endpoint.py:126-173` `detect()` caches a transient failure as 24h `MODE_DEAD` — VERIFIED, with downstream impact

Every `except Exception` in the two probe loops (API_PATHS then RAW_PATHS) is silently swallowed
and treated identically to "this path does not serve MediaWiki" — a `socket.timeout`, a DNS
failure, and a genuine "no API here" response from a live, healthy host all fall through to the
same `found = {"mode": MODE_DEAD, ...}`, cached for `DEAD_TTL = 24 * 3600` seconds. Downstream:
`feats.py:345,436` and `hostcheck.py:134,245` all gate on `EP.detect(host)["mode"] == EP.MODE_RAW`
(and implicitly on not being `MODE_DEAD`), so a host that was merely slow or briefly unreachable
during the one probe window is read as fully dead by the corpus reader and the host-checker for a
full day, even though — per this module's own historical commentary about the fandom.com IP-block
incident — this exact scenario has already happened to this project once, for a different domain.

### MAJOR — `endpoint.py:83-94`, `:356-370` — bare `.tmp` + unretried `os.replace`, cross-process race — VERIFIED

`_save()`:
```python
def _save():
    with _LOCK:
        if _MEM is None:
            return
        try:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            tmp = CACHE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(_MEM, f, indent=1, sort_keys=True)
            os.replace(tmp, CACHE)
        except Exception:
            silence.note("endpoint.py:save")
```

`register()`:
```python
def register(source, urls):
    try:
        with open(PAGES_FILE, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        silence.note("endpoint.py:334")
        d = {}
    d[source] = sorted(set((d.get(source) or []) + list(urls)))
    os.makedirs(os.path.dirname(PAGES_FILE), exist_ok=True)
    tmp = PAGES_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, sort_keys=True)
    os.replace(tmp, PAGES_FILE)
    return d[source]
```

Confirmed exactly as flagged, with two additional specifics found by reading `silence.py` for
comparison:

1. **Neither uses `silence.replace_retry` or `silence.write_json`**, both of which exist in this
   same project specifically to fix this pattern. `silence.write_json`'s own docstring: "TWELVE
   call sites across ten modules were writing shared `data/` and `state/` files with a bare
   `open(path, 'w')` + `json.dump`... THE TMP NAME CARRIES PID AND THREAD... Two writers of the
   same path otherwise collide on the temp file itself, and the loser can replace the winner's
   target with a partial file." `endpoint.py`'s two writers use the exact fixed, non-unique
   `path + ".tmp"` name that `write_json` was written to stop.
2. **`_save()`'s `os.replace` has zero retries** on `PermissionError` (only wrapped in a bare
   `except Exception: silence.note(...)`, so a single Windows sharing violation discards the
   write outright) where `silence.replace_retry` would back off and retry five times. Given this
   project's own stated experience that Windows denies a rename "while any reader holds the
   target open" as a *routine* occurrence, `_save()` will lose freshly-probed `detect()` results
   more often than the project's own established remedy for exactly this situation.
3. **`register()`'s write path has no exception handling at all** — only the read is guarded.
   Traced its one caller in this project: `src/scout.py:197-198`,
   `EP.register(source, kept)`, called with **no try/except** around it, inside `scout()`, which
   is itself called from `sweep()`'s `for src in order:` loop (`src/scout.py:244`) **also with no
   try/except**. A single `PermissionError` from `os.replace` on `SOURCE_PAGES.json` — the exact
   scenario this project's own `silence.replace_retry` docstring calls routine — propagates
   uncaught out of `register()`, out of `scout()`, and aborts the rest of `sweep()`'s loop
   entirely: if source #1 of a 4-source scout batch hits this, sources #2-4 are never attempted
   this round. The blast radius is contained one level up only because `foreman.py:190-197`
   (`scout_hostless`, this batch) wraps the whole `SC.sweep(limit=4)` call in its own
   `try/except Exception`, so the foreman loop itself survives — but the batch's remaining work
   is silently dropped for that round.
4. Multiple separate OS processes import `endpoint.py` independently
   (`feats.py`, `hostcheck.py`, `scout.py`, `completeness.py` all do `import endpoint`), each
   getting its own `_MEM`/`_LOCK` globals. `_LOCK` is a `threading.Lock`, which only serializes
   threads inside one process — it does nothing to prevent two of these processes from both
   loading `ENDPOINTS.json`, both adding a new host, and one write clobbering the other's update
   (classic read-modify-write lost update), independent of the tmp-collision issue above.

**Concrete failure scenario:** `catalogue_web.py` (or another sweep) and `feats.py` run
concurrently, both probe a new host around the same moment. Both processes' `detect()` calls
independently miss each other's in-memory `_MEM`, both call `_save()`, both write to the shared
`CACHE + ".tmp"` filename; whichever `os.replace` loses the race either fails outright (discarded
silently, no retry) or — worse, if the interleaving lands mid-write — replaces `ENDPOINTS.json`
with a truncated/interleaved JSON body, which every subsequent `_load()` across the project (a
bare `json.load`, `except Exception: _MEM = {}`) will then read as "start empty," re-probing every
previously-known host from scratch and discarding accumulated adoption/dead-cache history.

Severity: MAJOR. This is the exact two-writer-contract violation the audit specification already
flagged, now traced to two additional concrete consequences (an uncaught propagating exception in
`register()`'s one real caller, and a zero-retry write in `_save()` that is strictly worse than
this project's own established fix for the identical problem).

---

## entity_match.py

No file-write, no shared state, and no correctness bug found. Read in full. Notes:

- `candidates(name, pool, limit=None)` correctly defaults `limit=None` and documents Hard Rule 0
  compliance explicitly in its own docstring ("NO CAP BY DEFAULT... every programmatic consumer
  must leave it None, and a truncated result is flagged"); the one place a cap is applied
  (`scored[:limit]`) sets a `truncated: True` flag in the return value rather than hiding the
  truncation. This is the pattern the rest of the project should be following and largely is not.
- `qualifier_compatible()` matches its docstring precisely: normalised-but-not-literal equality
  of trailing parenthetical qualifiers, absolute rather than scored, exactly as
  `verify_math §19r` is described as requiring.
- `split_qualifier()`'s anchor-at-end regex (`r"\(([^()]*)\)\s*$"`) correctly refuses to treat a
  mid-name parenthetical as a qualifier, matching the docstring's own worked example.
- No caps, no swallowed exceptions of consequence (the module does no I/O beyond an optional
  Ollama `/api/tags` probe in `embed_available()`, which correctly degrades to
  `{"available": False, ...}` on any failure rather than raising, and is explicitly unused by
  default).

Clean module. No findings.

---

## anchors.py

### CONFIRMED (known suspect) — `anchors.py:215` monotonicity check order places Yggdrasil (M6) before Goku (M5) — VERIFIED

```python
order = ["The Skate Guy", "A Sword", "Yggdrasil", "Goku", "The Seat of the Creator"]
vals = {}
for name, a, res, inst, col in rows:
    vals[name] = A.LADDER.index(a["anchor"]) + (res.get("decimal") or 0.0)
prev = None
ok = True
for n in order:
    if prev is not None and vals[n] < vals[prev]:
        ok = False
    prev = n
```

`ANCHORS["Yggdrasil"]["anchor"] = "M6"` and `ANCHORS["Goku"]["anchor"] = "M5"` (both declared
earlier in the same file, lines 92 and 152). `vals["Yggdrasil"]` is therefore always
`A.LADDER.index("M6") + decimal ≈ 6.x`, strictly greater than `vals["Goku"] ≈ 5.x`. The `order`
list walks Yggdrasil immediately before Goku, so the step `vals["Goku"] < vals["Yggdrasil"]` is
true by construction — `ok = False` fires on every single run of `anchors.py`, regardless of
whether the underlying instrument (ruin/celerity/reach/sustain/continuity chain) is actually
monotonic in the correct floor-to-ceiling order (Skate Guy → A Sword → Goku → Yggdrasil → Seat of
the Creator, which is the order the module's own header describes: "floor... standard... M6...
ceiling"). This is a check that cannot pass, the mirror image of this project's usual "check that
cannot fail" defect, but the same root cause: an assertion whose input was never actually
satisfiable, so it stops meaning anything and a real regression in the instrument would print the
identical `False` as this permanent false alarm. Severity MAJOR as an instrument-validation defect
(this script exists specifically to catch monotonicity breaks, and currently cannot).

No other defects found in `anchors.py`. The five `ANCHORS` entries, `vector_score()`, and the
per-anchor reporting loop were all read and are internally consistent with their own docstrings
(e.g. "The Seat of the Creator" correctly uses `attestation="Transcribed"` with the stated
rationale, "A Sword" correctly nils out `celerity`/`continuity`/`vector` rather than scoring an
object as if it acted).

---

## recover_folder_records.py

### MINOR (self-documented, half-fixed) — `recover_folder_records.py:143-150` writes the record file directly, bypassing `pipeline.write_record_catalogue`'s merge — VERIFIED, downgraded from the flagged severity

```python
path = os.path.join(RECORDS, slug(name) + ".json")
if not args.dry_run:
    # ATOMIC. NOTE FOR REVIEW: the two-writer contract says a RECORD should be written
    # through `pipeline.write_record_catalogue`, not straight to disk at all. Making the
    # write atomic is the safe half of that repair; routing this recovery tool through
    # the catalogue writer changes its merge semantics and is flagged in NEXT_STEPS.
    silence.write_json(path, record, indent=2, ensure_ascii=False)
    roll_entry["entry_count"] = len(entries)
    roll_entry["status"] = "catalogued"
written.append((name, len(entries), os.path.basename(path)))
```

Verified against `pipeline.write_record_catalogue` (`src/pipeline.py:411-441`): that function
exists specifically because "one merge cannot serve both writers" and merges a fresh entry list
onto whatever is already on disk (`rec`'s list wins, disk-only entries and disk per-entry
judgments are preserved) rather than truncating. `recover_folder_records.py` calls
`silence.write_json(path, record, ...)` directly — atomic (the half already fixed, confirmed: it
now uses the PID+thread-unique-tmp-name writer rather than a bare `.tmp`), but a straight
overwrite, not a merge. In practice this is low-risk for the specific 100 `entry_count: 0`
sources this script targets (77 have no file at all; 23 have an empty `entries: []` — nothing on
disk to lose in either case, by the script's own accounting), but if this script is ever re-run
after some other process has since added entries to one of those same record files (e.g. a
partial catalogue re-run that landed a handful of entries before this script runs), that work
would be silently discarded rather than merged. The code's own comment already identifies this
precisely and defers it as an owner decision, so I am recording it as confirmed-and-current but
not elevating severity beyond what the comment itself already discloses.

### COSMETIC — `recover_folder_records.py:54` comment cites a nonexistent module — VERIFIED

> "Matches ingest.py's slug()..."

There is no `src/ingest.py` in this project (checked: only `ingest_doc.py`, and that module's
`slug()` does **not** truncate to 60 characters, unlike this one). The `slug()` implementation
here (`re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]`) actually matches
`catalogue_web.py`, `catalogue_codex.py`, and `catalogue_aurora.py`'s `slug()` functions
byte-for-byte, all three of which are plausible candidates for "the cloud session's" writer. This
is purely a stale/wrong reference in a comment — the actual slug format is correct and consistent
with the three catalogue writers, and `manifest_builder.load_record()`'s prefix-matching (as
documented in that function) tolerates the 60-char truncation regardless — so there is no
functional bug, just a misleading pointer for a future reader trying to verify the claim.

No other defects found. `EXCLUDED_REGISTER_SOURCES = {"ME"}` is a documented, reasoned data-
quality exclusion (contamination removal, not a Hard-Rule-0 style truncation of a good universe),
and the roll/record write ordering (all record files written individually and atomically inside
the loop, `SWEEP_ROLL.json` written once at the end) is idempotent on re-run and does not lose
data on a mid-loop crash — it only redoes already-correct work.

---

## repass_bands.py

### MINOR — `repass_bands.py:91` hardcoded denominator `"of 211"` does not track the actual source count — VERIFIED

```python
print(f"  demoted to unassayed: {len(demoted_sources):,} of 211")
```

`211` is a literal, not derived from `PL.records()`, `len(recs)`, or any count taken in this run.
Every other piece of context in this batch and the project's own `CLAUDE.md` describes the
Acquisitions Roll as "~215 sources," and `recover_folder_records.py` in this same batch says "100
of the 215 sources." Whatever the correct historical count of source-ceiling assays actually is,
baking it in as a literal means this denominator silently goes stale the instant the roll's
composition changes (sources added, folder-mode records recovered by this batch's own
`recover_folder_records.py`, sources retired) — exactly the "measurement that ages invisibly"
shape called out in the audit brief, just applied to a report line rather than a pass/fail gate.
Low severity because it is a print-only display, not something a standard or a remedy branches
on, but it will misreport the source-level demotion rate as soon as the true source count drifts
from 211, and nothing will visibly indicate that has happened.

No other defects found. The script's `[:14]` / `[:8]` slices at lines 95 and 101 are honestly
labeled console **samples** ("SURVIVORS", "a sample of what was carrying a Magnitude") of lists
whose full lengths are separately reported and whose full contents are what actually gets written
under `--apply` — the sampling is display-only and does not touch the actual demotion logic, so
this is not a Hard Rule 0 violation. `PL.write_record` (verified by reading `pipeline.py:487ff`)
merges on entry-count drift before writing, so this script's read-then-mutate-then-write cycle is
protected against clobbering a concurrent writer in the same way `pipeline.py`'s own callers are.
The evidence-gate re-check (`PL.valid_scale_note`) is applied uniformly to both the source-level
`synthesis.provisional_magnitude` and every catalogued entry's `magnitude`, consistent with the
module's stated purpose, and the loop only rewrites files that actually changed (`if changed:`).
