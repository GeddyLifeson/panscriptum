# AUDIT batch 13

Modules: src/overwatch.py, src/handbuilt.py, src/onomast.py, src/scout.py, src/genre.py,
src/coverage.py, src/repass_bands.py

Every file read in full, line by line.

---

## src/overwatch.py

### FINDING 1 — overwatch.py:326-343 — HIGH — VERIFIED
**The reconcile filter drops real findings, AND every internal exception in `structure()` is
invisible in `WATCH.md`.**

```python
326    out["reconcile"] = [r for r in A.reconcile()
327                        if r["finding"].isupper() or "no host" in r["finding"]
328                        or "never catalogued" in r["finding"]
329                        or "MORE THAN ONE" in r["finding"]]
330 except Exception as e:
331     silence.note("overwatch.py:193")
332     out["error"] = f"{type(e).__name__}: {str(e)[:90]}"
333 if not deep:
334     return out
335 try:
336     import estate as E
337     art = E.artifacts(workers=8)
338     out["corrupt_files"] = [r["path"] + " — " + r["error"] for r in art["bad"]]
339     out["files"] = art["total"]
340 except Exception as e:
341     silence.note("overwatch.py:202")
342     out["estate_error"] = f"{type(e).__name__}: {str(e)[:90]}"
343 return out
```

**Part A — the whitelist filter drops real findings.** I enumerated every `finding` string
`allsweep.reconcile()` (src/allsweep.py:152-320) actually emits via its `note()` helper, and
checked each against the filter's four conditions
(`isupper()` OR contains `"no host"` OR contains `"never catalogued"` OR contains
`"MORE THAN ONE"`):

| finding string (from allsweep.py) | kept by overwatch's filter? |
|---|---|
| `hosts for sources with no catalogue record` | **DROPPED** (no "no host" substring — it's "no catalogue") |
| `catalogued sources with no host` | kept |
| `on the roll but never catalogued` | kept |
| `source reconciliation failed` (exception path) | **DROPPED** |
| `coverage says CITED` | **DROPPED** |
| `readfeats records holding text` | **DROPPED** |
| `COVERAGE.json is stale` | **DROPPED** — a real, actionable finding (allsweep.py:203-207) |
| `coverage reconciliation failed` (exception path) | **DROPPED** |
| `cache directories no source points to` | **DROPPED** — orphan cache dirs |
| `cache reconciliation failed` (exception path) | **DROPPED** |
| `purged sources that still carry entries` (allsweep.py:236-237) | **DROPPED** — ghost entries, exactly the class the task flagged |
| `purge reconciliation failed` (exception path) | **DROPPED** |
| `phases implemented` | dropped (informational, fine) |
| `PHASES NAMED BY THE RUNNER WITH NO IMPLEMENTATION` | kept |
| `phase reconciliation failed` (exception path) | **DROPPED** |
| `ENTRIES BANDED ABOVE THEIR OWN SOURCE'S CEILING` | kept |
| `band reconciliation failed` (exception path) | **DROPPED** |
| `process check failed` (exception path) | **DROPPED** |
| `MORE THAN ONE INSTANCE RUNNING` | kept |
| `NOT RUNNING` | **DROPPED** |

So: stale coverage, orphan cache directories, and — most importantly — **ghost roster entries
(`purged sources that still carry entries`)** are silently dropped from WATCH.md by this filter.
Worse, **every one of `reconcile()`'s own six internal `except Exception` handlers** (source,
coverage, cache, purge, phase, band, process-check — allsweep.py:186-318) reports its failure via
the same `note()` mechanism as a `"... reconciliation failed"` string, and every one of those
strings is lowercase and contains none of the four whitelisted substrings — so **if any single
reconciliation section inside `allsweep.reconcile()` throws, that failure is silently discarded by
overwatch's filter before it ever reaches WATCH.md.**

**Part B — `write_report` never reads `error`/`estate_error`.** Confirmed by reading
`write_report` (overwatch.py:524-568) in full: it reads only `struct.get("broken_modules")`,
`struct.get("corrupt_files")`, `struct.get("files")`, and `struct.get("reconcile")`. It never once
reads `struct.get("error")` or `struct.get("estate_error")`. Trace the consequence: if the outer
`try` at line 318 throws (e.g. `import allsweep` fails, `A.modules()` throws, or the
`ThreadPoolExecutor.map(A.check_import, ...)` call itself raises) *before* `out["broken_modules"]`
and `out["reconcile"]` are ever assigned, then:
- `struct.get("broken_modules") or []` → `[]`
- `struct.get("reconcile") or []` → `[]`

and WATCH.md prints `"modules that will not import: **0**"` with no reconcile lines at all, and no
mention anywhere that a crash occurred. Likewise if the `estate` block throws,
`struct.get("corrupt_files") or []` → `[]` and `struct.get("files", 0)` → `0`, rendering
`"files that will not parse: **0** of 0 inspected"`.

**Part C — the round's own console print has the identical blind spot.** `round_once`
(overwatch.py:597-598) prints
`f"   {len(struct.get('broken_modules') or [])} module(s) will not import, "` — same pattern,
same blind spot; a crashed structural check prints "0 module(s) will not import, 0 file(s) will
not parse" on the console too, with the `error`/`estate_error` value going nowhere but
`silence.note()`.

**Net effect, fully traced end to end:** a CRASHED structural check (import failure,
`ThreadPoolExecutor` exception, `estate.artifacts()` throwing) renders in `WATCH.md` exactly like
"0 broken, 0 corrupt, nothing to reconcile" — indistinguishable from an actually-clean sweep. This
is the file's own stated failure mode from its docstring ("an auditor that called an empty log
file corrupt" / crying wolf) inverted into its opposite and more dangerous twin: a report that
looks clean because the checker crashed, not because nothing is wrong.

### FINDING 2 — overwatch.py:552-553 — LOW — VERIFIED
`write_report`'s "What the model found" section caps the *rendered list* of open findings at 40
(`sorted(open_f, ...)[:40]`), even though the header line above it
(`f"**{len(open_f)} open** ({len(hi)} high)."`) reports the true, uncapped count. This means once
more than 40 findings are open, the header count and the number of bullets actually shown diverge
— the report says e.g. "60 open" but lists 40. The underlying ledger (`OVERWATCH.json`) is never
truncated and `--show` prints the full list, so this is a display cap on a preview, not data loss
— flagged per the audit's instruction to note every `[:N]`, and noted as a preview-only cap
rather than a Hard Rule 0 violation, but worth the owner's awareness since severity/date sort means
older lower-priority findings could silently fall off the visible page as open findings pile up.

### CLEAN
Everything else in overwatch.py: the ledger merge (`_merge_ledgers`), digest-based staleness
reconciliation (`_reconcile_with_disk`), the `_LOCAL_BUSY` reset fix, `verify_open`'s budgeted
re-triage, and the atomic `WATCH.md`/`OVERWATCH.json` writes were all read and traced — all sound,
and all match their docstrings.

---

## src/onomast.py

### FINDING 3 — onomast.py:311-356 — HIGH — VERIFIED
**`register_for()`'s genre/feature voting is dead code — confirmed.**

`register_for(group_id, genre_register=None, features=None)` (onomast.py:311-334) contains real
voting logic (lines 322-334: weight the genre register at 3, each matching feature at 2, break
ties toward the source) — but it only runs `if genre_register or features` is truthy (line 318).
I grepped the entire `src/` tree for every call to this function:

```
src\onomast.py:356:            reg = register_for(v["continuity_group"])
```

This is the **only** call site anywhere in the codebase (the `register_for` inside `navtree.py` is
a separate, locally-defined function with the same name — confirmed by reading navtree.py:157,
178, 192 — it is not this one). The sole caller, `name_worlds()` (onomast.py:337-370), calls it as
`register_for(v["continuity_group"])` — positionally only `group_id`, with `genre_register` and
`features` left at their `None` defaults. Since `resolved` entities (`v`) carry only
`canonical_name`, `key`, `continuity_group`, and `attestations` (confirmed by reading the fields
`name_worlds` actually accesses), there is no genre or feature data available to pass even if the
call site wanted to. Every call therefore takes the `if not genre_register and not features:`
branch at line 318-320 and returns the pure hash-of-`group_id` fallback — the exact behavior the
function's own docstring (lines 312-317) says "used to be the whole function" and that this
rewrite was meant to replace. The docstring is now false: the voting logic it describes as live is
unreachable.

### CLEAN otherwise
`is_carried`, the `_stream` deterministic PRNG, `well_formed`'s four phonotactic constraints,
`coin_name`, and `coin_well_formed`'s widening-fallback (the m-numbered fix noted in its own
comment, onomast.py:244-265) were all read and traced against their comments — consistent. The
`ONOMASTICON.json` write at line 399 correctly uses `silence.write_json` (atomic, shared-file
compliant).

---

## src/genre.py

### FINDING 4 — genre.py:236-237 — HIGH — VERIFIED
**Non-atomic write to a shared file — two-writer contract violation.**

```python
234    if args.write:
235        p = os.path.join(HERE, "data", "GENRES.json")
236        with open(p, "w", encoding="utf-8") as f:
237            json.dump(out, f, indent=2, ensure_ascii=False)
238        print(f"\nwrote {p}")
```

This is a bare `open(path, "w")` + `json.dump` — the exact truncate-then-fill pattern the project
bans for shared files. Confirmed `data/GENRES.json` is genuinely shared and read elsewhere: I
grepped and found `src/navtree.py:124` and `src/profile.py:130` both `open()`/`json.load()` this
same file directly. A reader hitting this file mid-write (while `--write` is running) sees a
truncated or unparseable JSON file and crashes or misreads. Every other write in this same file
(and every other file in this batch) that touches a shared JSON artifact correctly uses
`silence.write_json` or a tmp+`silence.replace_retry` pair — this is the one holdout. This matches
the already-filed known bug exactly.

### CLEAN otherwise
`classify_source`'s `cap` parameter handling (genre.py:143-176) is a model of the project's own
doctrine: a numeric `cap` now raises `SystemExit` with a citation of the exact prior harm (7 of
210 sources misclassified) rather than being silently applied — correctly implemented, matches
its own docstring. `classify_text`/`classify_source`'s main loop iterates `rec.get("entries", [])`
uncapped. The `low[:5]`, and the `main()`-only preview loops are console-preview caps on top of
uncapped underlying computation — compliant.

---

## src/coverage.py

### FINDING 5 — coverage.py:16-18 vs 82-115 — HIGH — VERIFIED
**Docstring promises a state the code never produces — fetch failures are silently folded into
"no article exists."**

The module's own header (lines 10-21) defines five states an entry can be in, explicitly including:

```
16    NO PAGE      the wiki has no article under this name
...
18    UNREACHABLE  a host exists but the fetch failed -- the only state that is purely a defect
```

and the header's very next paragraph (line 20) makes the promise the whole module exists to keep:
*"The distinction between READ and NO PAGE is the whole point of the file. Collapsing them is
what made every silent failure in this project look like an honest absence."*

But `UNREACHABLE` is never implemented. I grepped the whole file (and confirmed via
`grep -rn UNREACHABLE src/`) — the string appears in `coverage.py` exactly once, in this docstring.
`state_of()` (coverage.py:82-115) only ever returns `"NO HOST"`, `"NO PAGE"`, `"READ"`, or
`"CITED"` — four states, not five — and `measure()` (coverage.py:118-138) only ever counts those
same four (`c["CITED"]`, `c["READ"]`, `c["NO PAGE"]`, `c["NO HOST"]`).

Trace the read path directly (coverage.py:88-104):
```python
88    for base in (READ_CACHE, F.CACHE):
89        fp = _p(base, host, name)
90        try:
91            mt = os.path.getmtime(fp)
92        except OSError:
93            continue
...
99            try:
100               with open(fp, encoding="utf-8") as f:
101                   d = json.load(f)
102           except Exception:
103               silence.note("coverage.py:60")
104               continue
```
If the file exists (so `getmtime` succeeds, meaning a wiki page *was* fetched for this entry) but
`open`/`json.load` then fails — corrupt JSON, a permission error, or (per this batch's own
concurrency lens) a torn read racing a concurrent writer to the same `readfeats`/`feats` cache
file — the `except Exception: continue` at line 102-104 silently skips that base entirely. `best`
stays at its initial value, `("NO PAGE", 0, 0)` (line 87), and the function returns exactly what
it would return for an entry with genuinely no article. This is precisely the anti-pattern the
module's own docstring names as the reason the file exists: a fetch/read failure (which the
docstring itself classifies as "the only state that is purely a defect") is reported as an honest
absence, with no signal anywhere that it happened beyond an unread `silence.note()` call.

**Special-focus answer — what happens to COVERAGE.json's headline figures on a crash or partial
run:** `main()` (coverage.py:176-187) calls `rows = measure()`, then `report(rows, ...)`, then
`silence.write_json(OUT, rows, ...)`. If `measure()` raises anywhere in its loop (e.g.
`json.load(open(F.HOSTS, ...))` at line 119, or any per-record failure not otherwise guarded), the
exception propagates out of `main()` uncaught — the write at line 185 never executes, so
**the on-disk `COVERAGE.json` is never touched and keeps whatever the last successful run wrote.**
That part is safe: the atomic `silence.write_json` means there is no torn/partial write. But two
things follow from that safety property that are worth the owner's attention: (1) `COVERAGE.json`
carries no `generated_at`/timestamp field inside its own JSON (confirmed — `rows` is a bare list
of per-source dicts, no top-level metadata), so any reader of the file's *content* alone cannot
tell it is stale; the only staleness signal is filesystem mtime, which is exactly what
`allsweep.reconcile()`'s `"COVERAGE.json is stale"` check reads (allsweep.py:203-207) — and
Finding 1 above shows that exact finding is filtered out of `WATCH.md` by `overwatch.py`. (2) A
transient per-entry read failure during a *successful* run (the `except Exception: continue` above)
doesn't crash the run or block the write — it just quietly nudges that one entry's state from
whatever it should have been to `NO PAGE`, silently lowering that run's `coverage`/`settled`
percentages by exactly the amount the docstring says must never happen silently.

### CLEAN otherwise
`_so_load`/`_so_save`'s per-file cache is a correctness-neutral performance layer (recomputes
identically on a cache miss) written atomically via `_sil.replace_retry`. `report()`'s `[:12]`,
`show` (default 26), `[:10]` are all console-preview caps on top of an uncapped `rows` computation
and an uncapped `silence.write_json(OUT, rows, ...)` write — compliant with Hard Rule 0.

---

## src/scout.py

### FINDING 6 — scout.py:107-114, 187-189 — MEDIUM — VERIFIED
**`_ask()` swallows every exception and returns `None`, which `scout()` cannot distinguish from a
legitimate "the model knows of no URLs" answer.**

```python
107 def _ask(prompt):
108     try:
109         import read as R
110         R.ensure_transport(verbose=False)
111         return R._ask(R.config(), SYSTEM, prompt, SCHEMA)
112     except Exception:
113         silence.note("scout.py:_ask")
114         return None
```
and in `scout()`:
```python
187    urls = [u for u in ((got or {}).get("urls") or []) if str(u).startswith("http")]
188    if not urls:
189        return {"source": source, "proposed": 0, "kept": [], "note": "model proposed nothing"}
```
`_ask` catches every exception (import failure, `ensure_transport` failure, a genuine network/
transport exception before `R._ask` even runs) and returns bare `None`. `R._ask` itself
(`src/read.py:328`) can also legitimately return `None` when the whole transport ladder is
exhausted. Both paths collapse to the identical `{"proposed": 0, "kept": [], "note": "model
proposed nothing"}` result in `scout()` — a caller (`sweep()`, or a human reading `SCOUT.json`)
cannot tell "the model was asked and correctly said it doesn't know" from "the ask never actually
happened because something threw." This is exactly the swallowed-failure pattern the audit's lens
targets: a failure path returning the same value as a legitimate success/negative-result path.

### FINDING 7 — scout.py:200-206 — MEDIUM — VERIFIED
**Unguarded read-modify-write race on the shared `WIKI_HOSTS.json` file.**

```python
197    if kept and register:
198        import endpoint as EP
199        EP.register(source, kept)
200        try:
201            import feats as F
202            hosts = json.load(open(F.HOSTS, encoding="utf-8"))
203            hosts[source] = "pages:" + source
204            _land(F.HOSTS, hosts)
205        except Exception:
206            silence.note("scout.py:register-host")
```
This reads the entire `WIKI_HOSTS.json` dict, mutates one key, then writes the whole dict back.
The write itself is atomic (`_land` → tmp + `silence.replace_retry`), so there's no torn file —
but the read-modify-write as a whole is not atomic, and the file's own docstring two functions
above (scout.py:56-61) states outright that this exact file **"is written from here AND from two
call sites in `hostcheck.py`"** — i.e. the module itself documents that this is a multi-writer
file. If `scout.py` and `hostcheck.py` (or two `scout.py` runs) read the file at close to the same
moment and each add a different key, the second writer's whole-dict write silently discards the
first writer's addition (last-writer-wins on the full dict, not a per-key merge) — the same class
of hazard `overwatch.py`'s `_merge_ledgers`/`_reconcile_with_disk` was built specifically to close
for `OVERWATCH.json`. No equivalent digest-check or merge exists here for `WIKI_HOSTS.json`.

### FINDING 8 — scout.py:256-262 — LOW — VERIFIED
**A corrupt `SCOUT.json` silently discards run history instead of preserving it.**

```python
256    try:
257        prev = json.load(open(LOG, encoding="utf-8")) if os.path.exists(LOG) else []
258    except Exception:
259        silence.note("scout.py:241")
260        prev = []
261    prev.append({"at": time.strftime("%Y-%m-%d %H:%M"), "results": results})
262    _land(LOG, prev[-40:], sort_keys=False)
```
If `SCOUT.json` exists but fails to parse (damaged, truncated by an earlier race), `prev` silently
resets to `[]`, and the next line immediately overwrites the file (via `_land`, atomically — no
torn write, but a torn *history*) with just the current round's single entry, discarding up to 40
prior rounds' history with no trace preserved. `overwatch.py`'s own `load()` (overwatch.py:143-176)
handles the identical situation correctly elsewhere in this codebase — renaming the wreck to
`.corrupt` and saying so on stderr before starting fresh — establishing that this is a known,
already-solved pattern in this project that was not applied here. Low severity because `SCOUT.json`
is a rolling diagnostic log, not load-bearing data, but it is the same class of silent loss the
project has already paid to fix once.

### NOTE (not a bug) — scout.py:176-178 — diagnostic bound, not a Hard Rule 0 violation
`sample = [n for n in names if n and len(n) > 3][:PROBE_NAMES]` (`PROBE_NAMES = 25`) caps the
catalogued-name list used (a) in the prompt sent to the model and (b) as the probe set
`verify()` checks candidate pages against (`MIN_NAME_HITS = 2` of this 25-name sample). This does
not truncate any persisted roster or listing — `hostless()` and the caller still hold every
catalogued name for the source — but it does mean a source with more than 25 entries is
represented to the relevance-check by only its first 25 (in whatever order `names` arrives in,
not ranked). A real page about material #26-onward of a large source could plausibly score 0 hits
against this 25-name sample and be wrongly rejected as "not about this material." Flagged per the
audit's instruction to note every `[:N]`; judged a diagnostic/probe bound rather than a truncation
of reported data, since it affects only which candidate URLs get accepted, not what is
subsequently listed as the source's catalogue.

---

## src/handbuilt.py

### CLEAN
Read in full. `ROSTER` is fixed, hand-authored data (not a truncated listing of anything). The
write to `HANDBUILT_ASSAYS.json` (handbuilt.py:453-459) is correctly ordered — the atomic
tmp+`silence.replace_retry` write happens *before* any console printing, with a comment explaining
exactly why (a `UnicodeEncodeError` on `moth_number`'s Fraktur glyph used to kill the process before
the file ever landed) — read and confirmed the ordering matches the comment's claim. No caps, no
swallowed failures beyond the deliberately-documented `sys.stdout.reconfigure` exemption
(handbuilt.py:462-465), which is honestly labeled `"silence-exempt"` and genuinely harmless (stdout
still prints with replacement characters on failure).

---

## src/repass_bands.py

### FINDING 9 — repass_bands.py:91 — LOW — VERIFIED
**Hardcoded source-count in a report line, never derived from the data being processed.**

```python
90    print("\nSOURCE CEILINGS")
91    print(f"  demoted to unassayed: {len(demoted_sources):,} of 211")
```
`211` is a literal, not computed from `recs = PL.records()` or from any count of distinct sources
actually encountered in the loop above (`src = rec["source"]`, line 45) — I grepped the file and
this is the only occurrence of `211`, and nothing in the function derives it. As the library's
source roll grows (the project's own `CLAUDE.md` already puts the roll at ~215 as of this
session), this denominator silently drifts from the true source count with no mechanism to catch
it, understating or overstating the fraction of sources whose ceiling was demoted. Low severity —
cosmetic to a console report, not a data-mutation bug — but it's exactly the class of "value
hardcoded where the code around it says it should be derived" the audit's lens calls out, and a
one-line fix (`len({rec["source"] for _, rec in PL.records()})`, captured before the generator is
consumed, or a running total) would make it self-correcting.

### CLEAN otherwise
The demotion logic itself (lines 43-80) is correct and uncapped — it iterates every record and
every entry with no truncation, and correctly uses `PL.write_record(path, rec)` (the sanctioned
two-writer-contract path) for every mutated record. The `kept_entries[:14]` and
`demoted_entries[:8]` print loops (lines 95, 101) are explicitly self-labeled samples
("SURVIVORS", "a sample of what was carrying a Magnitude") over data whose true totals
(`total_banded`, `len(kept_entries)`, `len(demoted_entries)`, and the `by_band` Counter) are
computed and printed uncapped immediately above — fully Hard-Rule-0 compliant.

---

## Summary count

- HIGH: 3 (overwatch.py:326-343, onomast.py:311-356, genre.py:236-237)
- HIGH (special-focus): 1 (coverage.py:16-18/82-115)
- MEDIUM: 2 (scout.py:107-114/187-189, scout.py:200-206)
- LOW: 3 (overwatch.py:552-553, scout.py:256-262, repass_bands.py:91)
- Modules fully clean: handbuilt.py (entirely); large clean portions of every other file noted
  inline above.
