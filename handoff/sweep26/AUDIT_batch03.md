# BATCH 03 audit — run26

Modules (src/, full line-by-line read): standards.py (1307), endpoint.py (370), backfill.py (276),
runguard.py (219), catalogue_aurora.py (171), lognames.py (36). Total 2,379 lines.

---

## lognames.py

### MAJOR — `OWNER["pipeline_auto.log"]` is a bare, unqualified fragment, contradicting the file's own stated rule
`src/lognames.py:32`
```python
OWNER = {
    READ:        "read.py --run",
    ROLL:        "feats.py --roll",
    PIPELINE:    "pipeline.py",
    RECATALOGUE: "catalogue_web.py --recatalogue",
    SWEEP:       "sweep.py",
    CALIBRATE:   "magnitude.py --calibrate",
}
```
The file's own docstring (lines 26-28) states the rule this dict must follow: *"The fragment is
matched against the live command line by `overnight.running()`, so it must be specific enough to
distinguish two invocations of the same script: `feats.py --roll` is the page roll, a bare
`feats.py` is something else."* Every entry except `PIPELINE` follows that rule — each carries the
argument that identifies the specific invocation. `PIPELINE` is the one exception: `pipeline.py`
is bare.

`src/pipeline.py:1830-1832` confirms `pipeline.py` has at least two other invocation shapes:
`--phase N` and `--status`. Because `overnight.running()` (`src/overnight.py:91`) matches by plain
substring against the live command line, a manually-run `python pipeline.py --status` (a read-only
diagnostic, not the supervisor-driven phase runner) would satisfy `OWNER[PIPELINE]` just as well as
the real job. The stall detector in `standards.py`'s "every running job is advancing" check
(`standards.py:900-902`, `alive = bool(_ON.running(owner))`) would then see "pipeline.py is up" and
treat `pipeline_auto.log`'s silence as the job legitimately not writing yet, or skip the stall
check entirely if the log is also held, while the actual phase runner may be dead. This is the
exact "bare fragment reads as live when it is something else" failure this file's docstring was
written specifically to name and forbid, just not applied to its own last row.

**Failure scenario:** someone runs `python pipeline.py --status` from a terminal while the real
supervisor-driven pipeline has crashed. `overnight.running("pipeline.py")` returns True (matches
the `--status` process). The stall detector believes the phase runner is alive and, if
`pipeline_auto.log` also happens to hold size (e.g. a leftover partial write), never reports the
job silent — masking a dead phase runner for as long as anyone leaves a diagnostic shell open.

---

## catalogue_aurora.py

### MINOR — `written` list is appended before the write-gate, so a denied write is reported as written
`src/catalogue_aurora.py:140-153, 161-165`
```python
written.append((r, record))
if not args.dry_run:
    import pipeline as _P
    ...
    if not _P.write_record_catalogue(
            os.path.join(RECORDS, slug(source_name) + ".json"), record):
        print(f"      -> WRITE DENIED {source_name}; roll left untouched", flush=True)
        continue
    r["entry_count"] = len(entries)
    r["status"] = "catalogued"
...
print(f"{verb} {len(written)} records from Aurora XML:\n")
for r, rec in sorted(written, key=lambda x: -len(x[1]["entries"])):
    withtext = sum(1 for e in rec["entries"] if e["description"])
    print(f"  {len(rec['entries']):5d} entries ({withtext} with description)  {r['name']}")
```
The persisted state (the roll row, the record file) is correctly left untouched on a denied write
— the gate fix from run #25 holds. But the console summary is wrong: `record` is appended to
`written` unconditionally at line 140, before the gate is even attempted. If
`write_record_catalogue` returns False, the loop prints "WRITE DENIED" and `continue`s, but the
tuple stays in `written`. The trailing summary block (`"{verb} {len(written)} records..."` and the
per-source entry-count lines) then counts and lists the denied source as if it were written,
directly contradicting the "WRITE DENIED" line printed moments earlier for the same source in the
same run. An operator reading only the final summary (the more prominent, bottom-of-output part)
would see the source credited with N entries "written" when nothing landed on disk.

### MINOR / HARD RULE 0 note — `slug()` truncates to 60 characters
`src/catalogue_aurora.py:59`
```python
def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]
```
A `[:N]` slice, flagged per the audit's blanket caps rule. This is a filesystem-safe slug/filename
length bound (record files are named `slug(source_name) + ".json"`), not a truncation of a data
set — it does not drop any entries or records. Judged legitimate, but two source names differing
only after character 60 would collide on the same record filename; worth confirming no such pair
exists in `FOLDER_SOURCE`'s values today (none currently come close).

### QUESTION — `FOLDER_SOURCE` is a hand-maintained folder allow-list
`src/catalogue_aurora.py:41-52`
Any new homebrew folder dropped under `CUSTOM` (`C:\Users\imarl\Documents\5e Character
Builder\custom`) is silently never catalogued by this script until someone adds a row here.
`endpoint.py`'s own docstring (lines 36-38) explicitly rejects this exact pattern for host
detection — *"a list is a thing somebody has to maintain and this project has been bitten by every
list it ever wrote"* — but `catalogue_aurora.py` uses the pattern for its folder set. Not
necessarily wrong (folder-to-source-name mapping may be inherently manual, unlike endpoint
detection which is probeable), but worth confirming there is a companion check elsewhere that
flags an un-mapped folder under `custom/`, the way `MIN_HOST_COVERAGE` flags an unreached source.

---

## backfill.py

### MAJOR — `roster()`'s pagination silently truncates on API failure, indistinguishable from "no more pages"
`src/backfill.py:64-77`
```python
def members(cat, kind="page"):
    rows, cont = [], None
    while True:
        q = {"action": "query", "list": "categorymembers", "cmtitle": cat,
             "cmlimit": "500", "cmtype": kind}
        if cont:
            q["cmcontinue"] = cont
        d = F.api(host, q)
        if not d:
            return rows
        rows += [x["title"] for x in d.get("query", {}).get("categorymembers", [])]
        cont = (d.get("continue") or {}).get("cmcontinue")
        if not cont or (limit and len(rows) >= limit):
            return rows
```
`feats.api()` (`src/feats.py:120-121`) is documented to "Return parsed JSON, or None" — it returns
`None` after retries are exhausted on any HTTP error or timeout (confirmed at `feats.py:157,
162-166`). `members()` treats a `None`/falsy response identically to "pagination legitimately
ended": `if not d: return rows`. A transient network error, a 429, or a timeout mid-pagination
therefore returns whatever partial `rows` had accumulated so far, with **no error signal, no
distinction from a complete roster, and no retry**. This is the exact failure class the whole
module exists to eliminate — the module's docstring (lines 5-10) opens with cast members silently
missing from the catalogue due to a "cap [that] truncates the alphabet rather than sampling it."
Here the truncation isn't a hard-coded cap, it's an unmarked API failure landing in the same code
path as legitimate completion, producing an incomplete roster that `backfill_source()` will treat
as ground truth for "who is missing" — silently under-reporting the roster and therefore
under-adding characters, on exactly the kind of large/slow category walk (DC's 6,000+ member
category is cited in the same docstring) most likely to hit a transient failure partway through.

**Failure scenario:** `roster("dc.fandom.com")` walks `Category:Characters` across a dozen
`cmcontinue` pages; page 7 of 12 times out. `F.api` returns `None` after 2 retries. `members()`
returns the first 6 pages' worth of names as if that were the complete category. `backfill_source`
computes `missing` against this truncated `names` list — several thousand real characters are
never queued, and nothing in the run's output indicates the roster was cut short rather than
completed.

### MAJOR — subcategory walk is skipped whenever the top-level category returns 40+ members, even if the real roster spans both
`src/backfill.py:79-94`
```python
for t in members("Category:Characters"):
    if t not in seen and not _NOT_A_CHARACTER.match(t):
        seen.add(t)
        out.append(t)
# One level down, for wikis that keep the roster in subcategories rather than the top.
if len(out) < 40:
    # Every subcategory. Twelve was a cap on an alphabetical listing, so a wiki that
    # files its roster under "Villains", "Heroes", "Kryptonians"... lost everything
    # after the twelfth letter of the alphabet.
    for sub in members("Category:Characters", "subcat"):
        for t in members(sub):
            if t not in seen and not _NOT_A_CHARACTER.match(t):
                seen.add(t)
                out.append(t)
        if limit and len(out) >= limit:
            break
```
The comment directly above this code celebrates removing a cap ("Twelve was a cap... lost
everything after the twelfth letter") but the `if len(out) < 40:` gate reintroduces the same shape
of bug one level up: it is a magic-number heuristic that decides, based only on how many
*top-level* pages were found, whether to look at subcategories *at all*. A wiki that lists, say,
45 characters directly under `Category:Characters` **and** files hundreds more under
`Category:Characters/Villains`, `/Heroes`, etc. (God of War is explicitly named in this file's own
docstring, lines 16-18, as exactly this shape — "the rest sit in subcategories") gets the
subcategory walk skipped entirely once the top-level count crosses 40, silently dropping every
character filed only in a subcategory. This is precisely the "silent, per-source completeness
failure that looks like an honest absence" class the module exists to catch — reintroduced via a
threshold instead of a slice.

**Failure scenario:** a mid-size wiki lists 50 non-character-excluded pages directly under
`Category:Characters` (mix of a few real top-level entries plus index/list pages that survive the
`_NOT_A_CHARACTER` filter) and keeps its actual 800-person roster in subcategories. `len(out)` is
50 on entry to the `if`, subcategory walk never runs, and `roster()` returns 50 names against an
800-name true roster — silently, with the same downstream effect (characters read as "not in that
fiction") the module's docstring calls out for Kratos/Arthas/Gilgamesh/Byleth.

### MAJOR — `endpoint.py`'s HTML-mode fetch swallows every failure alike, unlike the already-fixed raw-mode fetch (see endpoint.py section)
Cross-reference only — see endpoint.py `fetch_html` finding below; relevant here because
`backfill.py` itself doesn't call it, but it is the sibling of `roster()`'s failure-swallowing bug
within the same subsystem this module depends on (`F.api`, `F.fetch`).

### MINOR — swallowed per-source exception in `--all` loses all diagnostic detail
`src/backfill.py:252-258`
```python
try:
    res = backfill_source(x["source"], recs, hosts, cap=a.cap, dry=a.dry)
except Exception as e:
    print("  %3d/%d  %-46sERROR %s" % (i, len(thin), x["source"][:44],
                                       type(e).__name__), flush=True)
    continue
```
Only `type(e).__name__` is printed — no `str(e)`, no traceback, and no `silence.note()` call
either (this is a bare `except Exception` with no logging to the failures ledger at all, unlike
almost every other except-block in this batch). A `KeyError`, a `TypeError` from a malformed wiki
response, and a `URLError` all print as an undifferentiated one-word line; the source is skipped
for the run with no way to tell from the output alone what actually failed.

### MINOR — unclosed file handle
`src/backfill.py:235`
```python
hosts = json.load(open(F.HOSTS, encoding="utf-8"))
```
No context manager; the file object is never explicitly closed (relies on CPython refcounting/GC).
Inconsistent with the rest of the batch, which uses `with open(...)` throughout.

### MINOR / HARD RULE 0 note — display-only cap in `--audit`
`src/backfill.py:240`
```python
for x in rows[:26]:
```
Truncates the printed `--audit` table to the 26 worst sources; `audit()` itself computes the full
`rows` list over every source with a non-Wikipedia host, so no underlying measurement is capped —
only the console table. Flagged per the blanket-caps rule; judged a legitimate display bound, not
a data truncation, but worth a second opinion since the file elsewhere is emphatic that "a cap on
an alphabetically-ordered listing is not a sample, it is a truncation" — the same logic could be
read to argue a report should show every row too.

### QUESTION — redundant duplicate fields in return dict
`src/backfill.py:215-218`
```python
return {"source": source, "host": host, "roster": len(names),
        "already_held": len(names) - absent, "absent": absent,
        "queued": len(missing), "missing": len(missing),
        "added": added, "entries_now": len(r["entries"])}
```
`"queued"` and `"missing"` are always the same value (`len(missing)`, computed once, after the
`cap` truncation at line 166). Likely leftover from the 2026-08-24 fix mentioned in the comment
above (which added `"absent"` back in) — harmless today, but two identically-valued keys under
different names invites a future caller to read the wrong one expecting a different number (e.g.
expecting `"missing"` to mean the pre-cap count that `"absent"` actually holds).

---

## runguard.py

### MAJOR — `claim()` has no atomic test-and-set; two concurrent callers can both believe they hold the guard
`src/runguard.py:98-121`
```python
def claim(agent, path=GUARD, note=None):
    prior = read(path)
    if holder_is_live(prior):
        age = time.time() - prior.get("heartbeat", 0)
        return False, (...)
    now = time.time()
    rec = {"started": now, "heartbeat": now, "done": False, "agent": agent}
    ...
    if not _land(rec, path):
        return False, "could not write the guard record"
    return True, "claimed"
```
This is a plain read-then-write with no lock, no compare-and-swap, and no OS-level exclusive
file lock around the sequence. `claim()` reads `prior`, decides `holder_is_live(prior)` is False,
and then unconditionally writes a fresh record naming itself the holder. If two processes call
`claim()` within the same narrow window (both read the same "not live" `prior`, e.g. right after a
predecessor released or went stale), **both** will pass the liveness check and **both** will write
their own record as the new holder — each returns `(True, "claimed")` to its caller, and only
whichever `_land()` call's `os.replace` lands last actually persists. Both callers proceed to do
maintenance work believing they hold exclusive access.

This module's own docstring (lines 12-25) frames its entire reason for existing as fixing a
related but different bug (m27: a heartbeat refreshing a record that isn't its own). The fix
correctly adds an ownership check to `beat()` and `release()` (both compare `rec.get("agent") ==
agent` before acting) — but `claim()` itself, the operation that establishes ownership in the first
place, has no equivalent protection against two racing claims. The one-line invariant the
docstring states — *"A run may only ever refresh, or close, a record that carries its own name"* —
says nothing about two runs claiming the same unclaimed record simultaneously, and the code doesn't
guard against it either.

**Failure scenario:** the maintenance cadence fires two runs seconds apart (e.g. a scheduled run
and a manually-triggered one) right as a predecessor's heartbeat goes stale. Both call `claim()`,
both read the same stale/absent `prior`, both pass `holder_is_live() == False`, both write a
`"claimed"` record. Two maintenance passes now run concurrently against the same caches and
quota — the exact hazard `standards.py`'s "one instance of each job" check (`standards.py:1126`)
exists to catch for the overnight jobs, reintroduced here for the maintenance pass this module
guards, undetected by `runguard` itself.

### MINOR — `_land()`'s temp filename is not writer-tagged, unlike `silence.write_json`'s pattern
`src/runguard.py:72-80`
```python
def _land(rec, path):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2)
    except Exception:
        silence.note("runguard._land")
        return False
    return silence.replace_retry(tmp, path)
```
Uses `silence.replace_retry` correctly (this is the compliant half of the two-writer contract), but
the temp file name is the bare `path + ".tmp"`, not PID/thread-tagged the way `silence.write_json`
deliberately is (see `silence.py:250-268`, whose docstring explains this exact hazard: "Two writers
of the same path otherwise collide on the temp file itself, and the loser can replace the winner's
target with a partial file"). Given the `claim()` race above can produce two concurrent `_land()`
calls, this is not a hypothetical: two callers writing to the same `MAINTENANCE_RUN.json.tmp` path
at once can interleave, and whichever `os.replace` runs last wins regardless of which JSON write
finished cleanly.

---

## endpoint.py

### MAJOR — two shared state files are written with a raw `os.replace`, not `silence.replace_retry`, despite `silence` already being imported and used in this exact file
`src/endpoint.py:83-94` (`_save()`, writes `data/ENDPOINTS.json`):
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
`src/endpoint.py:356-369` (`register()`, writes `data/SOURCE_PAGES.json`):
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
Both are textbook instances of exactly the anti-pattern `silence.write_json`'s own docstring
(`silence.py:250-268`) says was hunted down and fixed project-wide in the 2026-08-25 comprehensive
sweep: *"TWELVE call sites across ten modules were writing shared `data/` and `state/` files with a
bare `open(path, "w")` + `json.dump`, which is not a write but a TRUNCATE-THEN-FILL... Two writers
of the same path otherwise collide on the temp file itself, and the loser can replace the winner's
target with a partial file."* `endpoint.py` was apparently not among the twelve fixed — it uses the
identical bare `path + ".tmp"` naming and a raw `os.replace` (no `PermissionError` retry loop) in
both places, even though `silence` is already imported at the top of this file and `silence.note`
is called from the very same functions. This directly violates the audit's two-writer contract
("shared state files via `silence.replace_retry` only").

`ENDPOINTS.json` in particular is not a low-traffic file: the module's own comment at line 122
notes "2,958 dead entries are on file," implying frequent, ongoing probing from many hosts across
many runs — exactly the concurrent-writer conditions the docstring above describes. `_save()`'s
in-process `_LOCK` only serializes writers *within one process*; it does nothing for two
concurrently-running probe processes (e.g. a manual `endpoint.py <hosts>` invocation running
alongside a crawl subprocess), each with its own `_MEM` snapshot loaded once at start. Two such
processes racing `_save()` can each overwrite the other's newly-detected hosts wholesale (last
writer's full in-memory snapshot wins), silently discarding whichever process's discoveries lost
the race — with no error, since `os.replace` on Windows either succeeds or the `except Exception`
just calls `silence.note` and moves on.

The comment immediately above `_save()`'s call site (line 169) already flags awareness of the
locking being fragile: *"Under the cache's own lock: the write was accidentally-safe GIL behaviour,
not design."* — i.e. the author already knows this write path is not properly synchronized, but the
fix (route through `silence.write_json`/`silence.replace_retry`) was never applied.

**Compounding failure scenario for `register()` specifically:** `register()` has no lock at all
(not even the in-process `threading.Lock` `_save()` has), and — worse — its exception handling
means a single corrupted/partially-written `SOURCE_PAGES.json` (made more likely by the exact race
above, since this file has no PID-tagged temp name either) is read as `d = {}` (line 358-363) with
only a `silence.note`, and the function then proceeds to write `d` — now containing **only the
current source's URLs** — back over the entire file, permanently erasing every other source's
previously registered pages in one call. This is not "swallowed failure reads as success"; it is a
swallowed read failure that goes on to actively destroy unrelated data.

**Failure scenario:** two parallel crawl helpers each call `register()` for a different source at
nearly the same moment. Writer A's `os.replace` completes; writer B, mid-flight, briefly leaves
`SOURCE_PAGES.json.tmp` in an inconsistent state that a third, unrelated reader (or writer B itself
on a retry) opens and fails to parse. That reader/writer falls into the `except Exception: d = {}`
branch and, believing the registry was always empty, writes back a file containing only its own
source — every other source's registered homebrew page list (the entire reason this module's
"mode: html" section exists, per its own docstring: 1,335 KibblesTasty entries "uncitable"
without it) is now gone, silently, with only a `silence.note("endpoint.py:334")` recorded.

### MAJOR — `fetch_html`'s `one()` swallows every failure identically, the same bug `fetch_raw` already fixed once in this file (BUGS m15)
`src/endpoint.py:327-334`
```python
def one(u):
    try:
        body = _get(u, timeout=45)
    except Exception:
        silence.note("endpoint.py:fetch_html")
        return u, None
    text = html_text(body)
    return u, (text if len(text) > 400 else None)
```
Compare to `fetch_raw`'s `one()` (`endpoint.py:200-227`), which was explicitly fixed for this exact
failure class — the comment there (lines 207-216) explains at length why a blanket "any exception
= absent" is wrong: *"A REFUSAL IS NOT AN ABSENCE... a 403, a 429 or a 500 reached the caller as
the exact same answer a genuine 404 gives... a transient wearing the face of settled fact"* — and
the fix splits `404/410` (genuine absence) from everything else (refusal, logged under a distinct
`silence.note` key so the ledger can tell the two apart). `fetch_html`, added later in the same
file (the `MODE_HTML` section, lines 273 onward), has a bare `except Exception` with a single
undifferentiated `silence.note` — no `urllib.error.HTTPError` handling, no status-code split. A
429 or 403 while crawling a one-author homebrew site reads identically to the page genuinely not
being there. The file's own docstring for this section (lines 275-287) is emphatic about how much
material depends on this specific mode working — *"1,335 [KibblesTasty entries]... 6,110
catalogued entries are uncitable"* without it — making this the highest-value fetch path in the
file to have this diagnostic blind spot.

### MINOR — `_load()` treats a corrupt cache identically to a missing one, silently discarding all prior probe results
`src/endpoint.py:70-80`
```python
def _load():
    global _MEM
    with _LOCK:
        if _MEM is None:
            try:
                with open(CACHE, encoding="utf-8") as f:
                    _MEM = json.load(f)
            except Exception:
                silence.note("endpoint.py:load")
                _MEM = {}
        return _MEM
```
Any read failure (corrupt JSON — plausible given the non-atomic write above — permissions, etc.)
resets the entire in-memory endpoint cache to empty. Given the DEAD-verdict asymmetry documented at
lines 117-124 (a live verdict is trusted forever, so the cache is meant to accumulate permanently),
silently starting from empty after a corruption means every previously-probed host — API, RAW, or
DEAD — gets re-probed from scratch, hitting the network for thousands of hosts with no visible
signal that this happened beyond one `silence.note` call.

---

## standards.py

Subprocess spawns re-verified: `tasklist` at line 129-131 and the PowerShell `Get-CimInstance` call
at line 1123-1127 both still carry `creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0)`. Both fixes
from the prior run hold; no other subprocess spawns exist in this file.

Two-writer contract: the one direct-write site (`state/job_progress.json`, lines 913-916) uses
`silence.replace_retry` correctly. No violation found in this file.

### MAJOR — several evidence-integrity standards read files without checking their age, unlike sibling standards in this same file that explicitly guard the identical failure mode
Contrast the following, which have no freshness gate on the file they read:
- `"rosters that name their own fiction"` reads `data/ROSTER_AUDIT.json` — `standards.py:610-632`
- `"shelfmarks are unique"` reads `data/SHELFMARKS.json` — `standards.py:634-648`
- `"hand-built assays match the charter"` reads `data/REFERENCE_ASSAYS.json` — `standards.py:658-684`
- `"every source is fully catalogued"` reads `data/COMPLETENESS.json` — `standards.py:774-813`
  (this one does carefully distinguish "0 measured" from "not measured," but never checks the
  file's own age/mtime)

against standards in the very same file that explicitly age-gate for this exact reason, each with a
detailed narrative comment about a real incident this file already caused:
- `"coverage figures are current"` — checks `cov.get("age_h")` against `MAX_COVERAGE_AGE_H`
  (`standards.py:456-461`)
- `"model IDs their providers still serve"` — explicitly refuses to report green off a
  58-hour-old snapshot (`standards.py:1160-1199`, "AGE THE EVIDENCE BEFORE BELIEVING THE
  ALL-CLEAR")
- `"the full audit is recent"` — `MAX_SWEEP_AGE_H` (`standards.py:952-957`)
- `"the automation reproduces the charter"` — 26h age gate (`standards.py:688-714`)
- `"the published panel is fresh"` — `MAX_PUBLISH_AGE_H` (`standards.py:1141-1147`)

The file's own docstring for the provider-models standard states the general lesson plainly: *"a
stale file that produces a FALSE ALL-CLEAR is never looked at again... An empty `stale` list from
three days ago is not a measurement of now — it is the absence of one."* That lesson is not applied
to `ROSTER_AUDIT.json`, `SHELFMARKS.json`, or `REFERENCE_ASSAYS.json` — each is read and trusted
regardless of how long ago it was generated. A roster audit that hasn't rerun since new sources
were catalogued would report `"rosters that name their own fiction": True` (holds) even though the
newly-catalogued sources have never been checked at all — exactly the "green reading off stale
evidence" shape the task brief calls out as a MAJOR finding pattern.

### MINOR / HARD RULE 0 note — two "worst N" display truncations in report text
`src/standards.py:587` (`worst = sorted(good, key=lambda c: c.get("coverage", 0))[:3]`, inside
`"every source is fully catalogued"`) and `src/standards.py:942`
(`_worst = sorted(_unrec, key=lambda r: -int(r.get("count", 0)))[:3]`, inside `"every pool failure
is recognised"`). Both are `[:N]` slices, flagged per the blanket-caps rule. In both cases the
`holds` boolean and the aggregate numbers (`cov`, `bool(_unrec)`) are computed from the full,
uncapped collection — only the human-readable "worst offenders" list embedded in the `order`/
`observed` text is capped to 3 examples. Judged legitimate (a report snippet, not a truncated
measurement), consistent with the same pattern already reviewed in `backfill.py:240`.

### QUESTION — `MIN_CALLS_TO_JUDGE_RATE` is a manually-kept mirror of `tuning.MIN_CALLS_TO_JUDGE`
`src/standards.py:58-60`
```python
MIN_CALLS_TO_JUDGE_RATE = 20    # below this a success PERCENTAGE is noise, not a measurement.
                                # Mirrors tuning.MIN_CALLS_TO_JUDGE (20), which already answers
                                # this exact question for regime(). See `calls that succeed`.
```
The comment states these two constants (in two different modules) are meant to answer "this exact
question" identically and gives their current values as equal (20 and 20). There is no import or
shared reference tying them together — just a comment asserting they match. If `tuning.py`'s value
is ever changed without a matching edit here (or vice versa), nothing would detect the drift; the
"every declared floor is measured" self-check (`standards.py:1210-1229`) only verifies a constant
is *used*, not that it stays consistent with constants of the same purpose declared elsewhere.
