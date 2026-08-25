# Sweep 28 — Batch 03 audit

Modules (read every line): `src/standards.py` (1400), `src/tiers.py` (360),
`src/weave_index.py` (276), `src/autostart.py` (218), `src/catalogue_aurora.py` (171).
Total 2425 lines.

Cross-checked `NEXT_STEPS.md` §3 (and §2, which names findings from prior run's batch 03) for
already-recorded items before writing anything up as NEW.

---

## src/standards.py

### [NEW, HIGH] `sentences that survive the verbatim check` can never fire — reads a field that
does not exist anywhere in the codebase

`src/standards.py:656-676`:
```python
fab = None
read = jobs.get("corpus read")
if read:
    det = read.get("detail") or ""
    try:
        import re as _re
        kept = int((_re.search(r"([\d,]+) feats", det).group(1)).replace(",", ""))
        m = _re.search(r"dropped\s+([\d,]+)", read.get("raw") or "")
        drop = int(m.group(1).replace(",", "")) if m else None
        if drop is not None and (kept + drop):
            fab = drop / (kept + drop)
    except Exception:
        silence.note("standards.py:fabrication")
if fab is not None:
    out.append(_s(
        "sentences that survive the verbatim check", fab <= MAX_FABRICATION, ...
```
`read.get("raw")` is read from the `jobs` dict that `dashboard.state()` builds. The producer,
`dashboard.py:196-205` (`_read_row`), builds that dict as:
```python
def _read_row(out, LN):
    r = _tail_match(os.path.join(STATE, LN.READ), RE_READ)
    if r:
        out.append({
            "name": "corpus read", "unit": "chunks",
            "done": _num(r["chunks"]), "total": _num(r["budget"]),
            "detail": (f"{_num(r['done']):,}/{_num(r['total']):,} entities  ·  "
                       f"{_num(r['feats']):,} feats  ·  {r['rate']} chunks/s"),
            "warn": (f"{_num(r['unans'])} unanswered" if _num(r["unans"]) else ""),
            "eta_h": float(r["eta"])})
```
There is no `"raw"` key. Grepped the entire `src/` tree (`grep -rn '"raw"|'"'"'raw'"'"''`) — the
only other hit is `endpoint.py`'s unrelated `MODE_RAW` constant and `output/raw` path strings.
No code anywhere ever sets a `"raw"` key on a jobs-list dict. So
`read.get("raw") or ""` is unconditionally `""`, the `dropped\s+([\d,]+)` regex never matches,
`m` is always `None`, `drop` is always `None`, and `fab` is always `None` — so the
`if fab is not None:` guard never passes and this HIGH-severity standard (floor
`MAX_FABRICATION = 0.45`) is **never appended to `check()`'s output, under any real fabrication
rate**. It is not merely blind on read errors (the documented "vanish on read error" pattern) —
it is structurally incapable of ever computing, because the data it wants was never wired
through.

The double bug: `dashboard.py`'s own regex `RE_READ` (`dashboard.py:58-62`) **does** capture the
dropped count (`(?P<dropped>[\d,]+)`), and read.py's log line does emit it — but `_read_row`
throws that captured group away when building the `detail`/`warn` strings; it is never placed on
the dict at all, under `"raw"` or any other key.

**Failure scenario**: model fabrication rate spikes to 90% (chunk truncation, weak fallback
model) — the standard that exists specifically to catch this (its own `order` text: "The model is
returning text that is not in the source... check the chunk size... or a weak fallback model is
carrying the run") simply is not on the standards page, at any severity, forever. This is exactly
the class of bug this file's own docstring exists to prevent ("a number with no floor under it
cannot be wrong") — except here the floor itself is unreachable.

**Fix sketch**: either (a) have `dashboard._read_row` include the parsed `dropped` count (and
`kept`/`feats`) directly as int fields on the job dict, and have `standards.py` read those fields
instead of re-parsing a nonexistent `"raw"` string, or (b) put the raw matched log line onto the
dict under `"raw"`. Either closes it; (a) is cleaner since the numbers are already parsed once.

### [KNOWN, STILL OPEN] probe/unexpected split matches a dead substring
`standards.py:605-608` classifies swallowed failures as "probe, not judged" via
`any(t in k for t in ("endpoint.py:detect", "endpoint.py:fetch", "hostcheck.py:probe",
"hostcheck.py:candidates", "hostcheck.py:relevance", "scout.py:verify"))`. Grepped every
`silence.note(...)` call site in `src/` — `"hostcheck.py:candidates"` matches **zero** of them
(closest is the unrelated `hosts.py:candidates`, a different file). Recorded in
`NEXT_STEPS.md` §2 ("Machinery worth building") as found by a prior run's batch 03; unchanged
this run, still open. The other five substrings all do match at least one real call site
(verified against the full `silence.note` grep — `endpoint.py:detect-api`/`detect-raw`,
`endpoint.py:fetch_raw*`/`fetch_html`, `hostcheck.py:probe`, `hostcheck.py:relevance-wikitext`,
`scout.py:verify`/`verify-http`).

### [KNOWN, STILL OPEN] `every declared floor is measured` self-check scans past `check()`
`standards.py:1305-1326`, specifically line 1309: `body = src[src.index("def check("):]` has no
end bound, so it scans `work_orders()`, `_wrap()`, `report()` and `main()` too, not just the body
of `check()`. A `MIN_`/`MAX_` constant referenced only in `report()`/`main()` (never actually
used to gate a standard inside `check()`) would read as "measured". Recorded in `NEXT_STEPS.md`
§2; unchanged this run.

### [KNOWN, STILL OPEN] data-file-backed standards vanish (rather than report UNMEASURED) on a
read error
The `ALLSWEEP.json` try block, `standards.py:831-857`, wraps three standards ("files that
parse" HIGH, "verifiers all run" HIGH, "the full audit is recent" MEDIUM) in one
`try/except Exception: silence.note(...)` with nothing appended to `out` on failure — an
`ALLSWEEP.json` that fails to parse makes all three standards disappear from the page rather
than reading UNMEASURED/red. Same shape recurs at `standards.py:678-702` (ROSTER_AUDIT),
`:704-717` (SHELFMARKS), `:724-752` (REFERENCE_ASSAYS), `:907-925` (sweep freshness) — each an
independent standard that vanishes silently on any read/parse exception. `NEXT_STEPS.md` §2
already names this pattern ("Most data-file-backed standards VANISH on a read error instead of
reporting UNMEASURED... The fix pattern already exists in the same file (lines 739-750), applied
to exactly one standard" — referring to the `every source is fully catalogued` /
`the automation reproduces the charter` standards' explicit UNMEASURED branches). Unchanged this
run; still only two of the ~10 file-backed standards use the UNMEASURED pattern.

### [KNOWN, FIXED] lesson-16's 14-row pool-failure cap
`standards.py:1016-1059` ("every pool failure is recognised") now joins **every** row in
`_unrec` with its full error text and computed age (`_now - last_seen`), no `[:3]`/`[:60]`
slicing anywhere in the block. This matches the docstring's claim ("Each row is a provider
failing...") and NEXT_STEPS lesson 16's own account of the fix. Confirmed fixed, not a
regression.

### [SPECULATIVE, LOW] `f.read(700)` truncated header scan for `chunks_unanswered`
`standards.py:630-645` reads only the first 700 bytes of every `data/readfeats/**/*.json` file
and string-searches that prefix for `"chunks_unanswered": 0"` / `"chunks_unanswered"`. Ran this
against the live corpus (1322 files in `data/readfeats/`): the key's byte offset never exceeds
367 in any current record (`"pages"` list is small relative to the 700-byte window), so **today**
this does not misfire. But there is no explicit bound tying the 700-byte window to the size of
the `"pages"` array the record schema allows (`read.py:734`, `"pages": sorted(text)` — an
unbounded list of every page title an entity's chunks came from). An entity attested across many
dozens of pages could in principle push `chunks_unanswered` past byte 700, at which point the
`elif "chunks_unanswered" not in head:` branch would fire and count a genuinely fully-read record
as unanswered (a false positive on this HIGH-severity standard, not a false negative — the
project's own Hard Rule 0 concern about caps that *hide* problems does not directly apply since
this errs toward over-reporting, but it is a positional fragility with no assertion or fallback
to a full read). Flagging as speculative/low because it does not currently misfire on any real
file.

---

## src/tiers.py

### [KNOWN, FIXED] `deliberate_joins` shared-evidence cap
`tiers.py:271-287` (`deliberate_joins`) now returns the whole `shared.get((a, b), [])` list with
no `[:3]` slice — matches NEXT_STEPS' account of this being "the fourth member of the
`shared_sample` family," fixed run #27. Confirmed fixed at source.

### [NEW, LOW] `main()`'s "unaddressed" diagnostic prints only 6 of N rows
`tiers.py:308-312`:
```python
unaddressed = [s for s in srcs if s not in linked]
print(f"\nhyperverse: DECLINED for all {len(srcs)} shelves — uncharted by cause, not omission")
print(f"unaddressed (share no entity with anything at all): {len(unaddressed)}")
for s in unaddressed[:6]:
    print(f"   {s}")
```
The count (`len(unaddressed)`) is uncapped/accurate, but the actual list of which shelves are
unaddressed is capped at 6 in the printed diagnostic. The module's own docstring calls these "the
honest residue... a fragment of another hyperverse... or a self-contained fiction — nothing in
the data separates those two readings," i.e. the module considers this list worth a person's
attention, not just a count. No downstream file consumes this truncated form (nothing writes
`unaddressed` to disk), so this is a CLI-report-only instance of the "cap on a diagnostic" class
Hard Rule 0 and lesson 16 call out, not a data-loss bug. Low severity because nothing downstream
depends on it and the count itself is honest.

---

## src/weave_index.py

### [KNOWN, STILL OPEN] `description[:400]` truncation at write time
`weave_index.py:224`: `"description": (e.get("description") or "")[:400],` inside `build()`.
Confirmed present, unchanged. Matches `NEXT_STEPS.md` §3's "`weave_index.py:224` +
`weave.py:195-198` — `description[:400]` at write time blinds the mechanic-detection regex to
any tell later in the text." `OUT_INDEX`/`OUT_CAND` writes both go through `silence.write_json`
(`weave_index.py:268-270`) — correctly atomic, so the two-writer contract itself is respected;
the bug is the pre-truncation of the field's content, not the write mechanism.

### [NEW, LOW] two "top N" print caps in the CLI report (data files themselves are uncapped)
`weave_index.py:255-256` (`for n in sorted(spread, reverse=True)[:10]:`) and `:259`
(`top = sorted(candidates.items(), key=lambda kv: -len({h["source"] for h in kv[1]}))[:18]`).
Both are display-only: `OUT_INDEX` and `OUT_CAND` are written with the full, uncapped `index`/
`candidates` dicts regardless of what the console prints. Flagging because Hard Rule 0's text is
unqualified ("no cap... no 'top N'... on data, diagnostics, or output") and this is literally a
"most cross-attested... " top-N block, but severity is low since nothing on disk is affected and
the header counts (`len(candidates)`, `len(index)`) printed just above are accurate and uncapped.

### Read but no other findings
`designations()`/`continuity_of()`/`norm()` (`:96-162`) were read closely for the "stale
parenthetical cache" bug class already fixed per BUGS m17 — the fix (`_records_sig()`-keyed
cache, `weave_index.py:104-133`) is intact and correctly invalidates on any records-directory
mtime change. Noted but not filing: `continuity_of` (called once per entity name inside `norm`,
called once per entry inside `build()`) recomputes `_records_sig()` — a `glob.glob` over the full
records dir plus an `os.path.getmtime` scan of every file — on every single call, even though the
expensive `designations()` body is cache-hit. This is a performance concern (stat-ing 217+ files
per entity, not per corpus load) rather than a correctness bug; not filing as a finding since
lens item 1-6 is about correctness/safety, not raw performance, and I have no profiling evidence
it is materially slow in practice.

---

## src/autostart.py

### [KNOWN, STILL OPEN] `_twin_watchdog()` fails open
`autostart.py:121-145`. On any exception from the `Get-CimInstance` PowerShell probe (timeout,
PowerShell unavailable, etc.), `except Exception: silence.note("autostart.py:131"); return False`
— `False` means "no twin found," so `watch()` (`:148-161`) proceeds to run its own supervisor
loop rather than exiting. Confirmed unchanged from `NEXT_STEPS.md` §3: "`autostart.py:131-133` —
`_twin_watchdog()` returns False on any failure of its own detection call, defaulting to
'proceed' — re-opens the multi-watchdog respawn loop its docstring fixes." Still open — the
watchdog's whole reason for existing (per its own docstring at `:148-156`, describing three
concurrent watchdogs once respawning each other's supervisors in a loop) is undefended exactly
when the detection probe itself is unreliable, which is correlated with machine load/PowerShell
contention — i.e. more likely exactly when duplicate processes are also more likely.

### Read but no other findings
`install()`/`uninstall()`/`_vbs_body()` (`:56-91`) — single local `.vbs` file, no shared-state or
concurrency concern. `start_supervisor()` (`:103-118`) correctly sets
`CREATE_NO_WINDOW | DETACHED_PROCESS` on Windows, consistent with the project's no-console-window
rule. `main()`'s process-status branch (`:205-213`) calls `ON.running(job)` without
`include_self=True`, but none of the polled job names (`dashboard.py`, `publish.py`, `foreman.py`,
`overwatch.py`, `feats.py`, `read.py`) match `autostart.py`'s own command line, so the
`include_self` omission that bit `standards.py`'s "every managed job is running" standard (per
that file's own comment) does not apply here — not a bug.

---

## src/catalogue_aurora.py

### [NEW, MEDIUM-HIGH] "Wrote N records" summary counts denied writes as written
`catalogue_aurora.py:99-165`, specifically the ordering across lines 140 and 150-155:
```python
written.append((r, record))          # line 140 — unconditional
if not args.dry_run:
    import pipeline as _P
    # GATE ON THE WRITE. ...
    if not _P.write_record_catalogue(
            os.path.join(RECORDS, slug(source_name) + ".json"), record):
        print(f"      -> WRITE DENIED {source_name}; roll left untouched", flush=True)
        continue
    r["entry_count"] = len(entries)
    r["status"] = "catalogued"
...
verb = "Would write" if args.dry_run else "Wrote"
print(f"{verb} {len(written)} records from Aurora XML:\n")
for r, rec in sorted(written, key=lambda x: -len(x[1]["entries"])):
    withtext = sum(1 for e in rec["entries"] if e["description"])
    print(f"  {len(rec['entries']):5d} entries ({withtext} with description)  {r['name']}")
```
The comment ("GATE ON THE WRITE... `catalogue_web.py` already gates this exact call for this
exact reason; these siblings did not. Found by the run #25 sweep.") documents a real, correct
fix — but only for the `roll`-row mutation half of the bug (`r["entry_count"]`/`r["status"]` are
now correctly skipped on a denied write, and the roll JSON is not falsely marked
`catalogued`). The half the comment does not mention: `written.append((r, record))` at line 140
runs **before** the gate, unconditionally, for every source whose `parse_folder()` produced
entries — regardless of whether the subsequent `write_record_catalogue` call succeeds. So on a
denied write:
1. `"      -> WRITE DENIED {source_name}; roll left untouched"` prints (correct, honest).
2. ...but the entry is still in `written`, so the closing summary block re-prints it as though it
   succeeded: `f"  {len(rec['entries']):5d} entries ({withtext} with description)  {r['name']}"`
   under the header `"Wrote {len(written)} records from Aurora XML"` — a success-shaped line for
   a write that was just reported denied two lines above.

**Failure scenario**: `write_record_catalogue` denies a write (e.g. a concurrent writer holds the
target, or the drift-merge guard rejects it — see `pipeline.py`'s known write-gating behavior).
The operator sees `WRITE DENIED Dr. Firestorm's Engineering Corps; roll left untouched` during
the run, then at the very end sees `Wrote 7 records from Aurora XML` with `Dr. Firestorm's...`
listed among them with its full entry/description counts — the summary directly contradicts the
denial message printed moments earlier, and a operator who only reads the final table (the
normal way to check "did this run work") would believe the record landed on disk when it did
not. This is exactly lens item 2's shape: a failure correctly detected and reported inline, then
silently re-absorbed into a success-shaped aggregate one screen later.

**Fix sketch**: move `written.append((r, record))` to after the write-success gate for the
non-dry-run path (keep it unconditional only inside `if args.dry_run:`), or track denied writes
in a separate list and print them distinctly instead of folding them into `written`.

### Read but no other findings
`parse_folder()` (`:69-96`) — per-folder `seen` dedup keyed on `(type, normalized-name)` is
correctly scoped per call, no cross-folder leakage. `slug()` (`:58-59`) truncates to 60 chars;
checked all 10 `FOLDER_SOURCE` values (`:41-52`) and none are anywhere near 60 chars pre-slug, so
no live truncation-collision risk today, though the function has no collision guard if that ever
changes (not filing — no live instance, purely hypothetical). The roll write
(`catalogue_aurora.py:157-159`) correctly uses `silence.write_json` with the "ATOMIC: four
scripts write this same roll" comment, matching the two-writer contract. `text_of()` (`:62-66`)
is a simple XML itertext join, no bug found.

---

## Summary table

| Severity | Status | Location | Claim |
|---|---|---|---|
| HIGH | NEW | standards.py:656-676 (root cause dashboard.py:196-205) | fabrication-rate standard can never fire — reads nonexistent `"raw"` key |
| MEDIUM-HIGH | NEW | catalogue_aurora.py:140 vs 150-155 | denied writes counted in the "Wrote N records" success summary |
| LOW | NEW | tiers.py:308-312 | `unaddressed[:6]` caps a printed diagnostic (count itself uncapped) |
| LOW | NEW | weave_index.py:255-256,259 | two "top N" print caps (written data files uncapped) |
| LOW (speculative) | — | standards.py:630-645 | 700-byte header scan has no live misfires, no explicit bound either |
| HIGH | KNOWN, still open | standards.py:605-608 | `hostcheck.py:candidates` matches zero call sites |
| HIGH | KNOWN, still open | standards.py:1309 | self-check slice has no end bound, scans past `check()` |
| HIGH/MED | KNOWN, still open | standards.py:831-857 (+ siblings) | data-file-backed standards vanish rather than report UNMEASURED |
| — | KNOWN, fixed | standards.py:1016-1059 | lesson-16's 14-row pool cap now shows all rows + age |
| — | KNOWN, fixed | tiers.py:271-287 | `deliberate_joins` shared-evidence cap removed |
| HIGH | KNOWN, still open | weave_index.py:224 | `description[:400]` truncation at write time |
| — | KNOWN, still open | autostart.py:131-133 | `_twin_watchdog()` fails open on probe error |
