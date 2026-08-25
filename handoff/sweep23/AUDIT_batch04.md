# AUDIT — batch 04

Files: `src/standards.py`, `src/endpoint.py`, `src/weave_index.py`, `src/runguard.py`,
`src/recover_folder_records.py`, `src/resonance.py`

Every line of every file in this batch was read in full (standards.py in two passes,
1-1012 and 1013-1261).

---

## src/endpoint.py

### FINDING 1 (confirms already-filed) — `fetch_raw()` collapses absence and failure to one signal
`endpoint.py:200-233`, specifically the return sites at `:203`, `:221`, `:224`, `:226` vs the
success return at `:227`.

```python
def one(t):
    url = raw_url(host, t)
    if not url:
        return t, None                                    # :203  no usable raw URL
    try:
        body = _get(url, timeout=40)
    except urllib.error.HTTPError as e:
        if getattr(e, "code", None) in (404, 410):
            silence.note("endpoint.py:fetch_raw-absent")
        else:
            silence.note("endpoint.py:fetch_raw-refused-%s" % getattr(e, "code", "?"))
        return t, None                                     # :221  ANY http error incl. 403/429/500
    except Exception:
        silence.note("endpoint.py:fetch_raw")
        return t, None                                     # :224  timeout, DNS, connection reset...
    if not body or body.lstrip().lower().startswith(("<!doctype", "<html")):
        return t, None                                     # :226  html error page
    return t, body                                          # :227  real success
```
The `silence.note()` calls DO discriminate 404/410 ("absent") from other HTTP codes ("refused-N")
in the failure ledger, but the **return value** — the only thing any caller ever sees — is
`(t, None)` in all four failure branches. `fetch_raw` is called for real content (not just
diagnostics) from `feats.py:437` (`fetch()`'s raw-mode branch, the actual entity-text path) and
for scoring/sampling from `hostcheck.py:135` (`probe()`) and `hostcheck.py:246` (about-test). All
three callers read only the returned dict's presence/absence of a title — none can distinguish
"this wiki doesn't have this page" from "we got 403/429/500'd fetching it" or "the request timed
out". **VERIFIED** — traced every return path and all three call sites.

### FINDING 2 (confirms already-filed) — `detect()` caches a transient probe failure as permanent-for-24h
`endpoint.py:126-173`. `_get()` (`:108-114`) raises on ANY failure (timeout, DNS, connection
reset, HTTP error) via a bare `except Exception` at `:151-152` (API probe) and `:163-164` (raw
probe) — there is no branch that treats a timeout differently from a confirmed 403. If every path
in `API_PATHS` and `RAW_PATHS` fails for any reason, `found` stays `{"mode": MODE_DEAD, ...}`,
gets an `"at"` timestamp (`:167-168`), and is written into `mem[host]` under `_LOCK` and persisted
to `data/ENDPOINTS.json` (`:170-172`). `DEAD_TTL = 24 * 3600` (`:124`) means a single bad network
minute (a fandom-wide IP block, a DNS hiccup) marks the host unreadable for a full day. Callers:
`feats.py:345`, `feats.py:436`, `hostcheck.py:134`, `hostcheck.py:245` all gate on
`EP.detect(host)["mode"] == EP.MODE_RAW`; the API path is independently blocked too because
`api_url()` (`:176-179`) calls the same cached `detect()` and requires `mode == MODE_API`. So one
bad probe silently takes both reading paths offline for the host for 24h. **VERIFIED**.

### FINDING 3 (new) — `_save()` writes the shared `ENDPOINTS.json` cache with a bare, unshared temp name, not via `silence.write_json`
`endpoint.py:83-94`:
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
`silence.write_json`'s own docstring (`src/silence.py:250-269`) documents exactly this shape as a
bug class fixed project-wide on 2026-08-25: a bare `path + ".tmp"` temp name, used by two
concurrent *processes* writing the same path, lets one writer's tmp file get overwritten by the
other's before either calls `os.replace` — "the loser can replace the winner's target with a
partial file." `write_json`'s fix was to key the temp name on PID and thread id. `_save()` here
still uses the pre-fix pattern, and skips `silence.replace_retry` too, so a `PermissionError` from
a concurrent reader on Windows (the exact WinError 5 collision `replace_retry`'s docstring cites
as having taken an assay worker down) is swallowed by the bare `except Exception` with no retry —
the write is lost outright rather than landing "next round." `_LOCK` is a `threading.Lock`, so it
serializes threads inside one process but does nothing across the separate OS processes
(`feats.py`, `hostcheck.py`, `read.py --run`) that all import this module and can all call
`detect()` on a new host around the same time. **VERIFIED** — read `silence.write_json`'s and
`silence.replace_retry`'s implementations directly to confirm the contrast; the race requires two
processes probing a new host in the same window, which this pipeline's own concurrency (multiple
managed jobs, `standards.py`'s "one instance of each job" check is per-job-name, not
cross-job) makes plausible, not rare. Severity: HIGH — this is precisely the two-writer/atomic-
write contract this project stood up `silence.write_json` to close everywhere else.

### FINDING 4 (new) — `register()` does an unguarded read-modify-write on shared `SOURCE_PAGES.json`, with the same unsafe temp-file pattern
`endpoint.py:356-370`:
```python
def register(source, urls):
    """Record where a source's material actually lives."""
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
No lock of any kind guards this function (not even the module's own `_LOCK`, which only covers
the `ENDPOINTS.json` cache). Two calls to `register()` for two different sources, close together,
race classically: both read the same `d`, both add their own key in memory, the second write wins
and the first caller's addition to `SOURCE_PAGES.json` is silently lost — no exception, no log
line, just a missing source-pages entry the next time anyone reads the file. The temp name is also
the bare `PAGES_FILE + ".tmp"` (same unshared-temp-file problem as Finding 3), and unlike `_save()`
this whole block is not even wrapped in a `try/except`, so a Windows `PermissionError` on
`os.replace` propagates uncaught to `register()`'s caller instead of being retried per this
project's established pattern. **VERIFIED** by reading the full function; not traced to a live
concurrent caller pair, but the read-modify-write shape is unconditionally racy by inspection.
Severity: HIGH for the silent-data-loss RMW race, independent of whether two callers currently
happen to overlap in practice.

### CLEAN
`_load()`, `api_url()`, `raw_url()`, `exists_raw()`, `main()`, `html_text()`, `fetch_html()`,
`source_pages()` — read correctly, no truncation of any host/title listing, no other swallowed-
failure ambiguity beyond Findings 1-2. `UA_OVERRIDES` and the dandwiki browser-UA handling match
their documented rationale. No `[:N]` truncates an actual roster anywhere in this file — the only
slices are on individual strings/URLs for display or protocol reasons, not on entity/title lists.

---

## src/standards.py

This file computes the numeric standards read as the maintenance protocol's opening diagnostic.
Each floor's computation was checked against its `order`/description text; findings below.

### FINDING 5 (new) — `fandom_ipv4_reachable()` is called with no cache, inside a function invoked on every 5-second dashboard poll
`standards.py:966-982` calls `fandom_ipv4_reachable()` (`:241-282`, a live TCP `connect()` to
`marvel.fandom.com:443`) directly inside `check()`, with **no TTL cache**. Contrast with every
other network/subprocess-cost check in this same file:
- `ollama_runner_up()` (`:113-137`) — explicit `ttl=120.0` cache (`_RUNNER`), justified in its own
  docstring by "this costs a process spawn."
- `ollama_token_flow()` (`:143-229`) — explicit `ttl=300.0` cache (`_TOKENFLOW`).
- the "cached records that were fully read" check (`:561-576`) — explicit 120s cache
  (`_UNANS_CACHE`), whose own comment says why: **"on a check the dashboard polls every five
  seconds, for an answer that only changes when the reader finishes an entity."**

`check()` is called directly (no wrapper) from `dashboard.state()` (`dashboard.py:416-425`), which
is itself called with no TTL from the `/api/state` HTTP handler (`dashboard.py:691-694`), which the
page's own client JS polls every 5 seconds per the comment at `dashboard.py:703` and the fetch call
at `dashboard.py:670`. So every 5 seconds a live socket connects to `marvel.fandom.com`, timeout up
to 8s, with zero caching — the exact "dashboard polls every five seconds" scenario this file's own
sibling checks were explicitly written to guard against. This module's own extensive commentary
(`:232-238`, `:244-258`) documents a *real prior incident* of this project earning an IP block from
fandom.com by its own request rate; an uncached per-poll live connect to the same domain family is
a smaller but analogous self-inflicted-load risk, and it is inconsistent with the pattern the
file otherwise follows everywhere else a network call sits inside `check()`. **VERIFIED** by
tracing `fandom_ipv4_reachable` (no cache in its body), `check()`'s call site, `dashboard.state()`,
and the `/api/state` handler. Severity: MEDIUM (traffic volume is low — one connect per 5s per open
dashboard tab/process — but the omission is a genuine inconsistency against an established,
documented pattern in the same file, and `publish.py`/`foreman.py` also call `ST.check()` on their
own independent minute-scale loops, adding further uncached hits).

### Floors checked against their `order` text — no mismatch found
Traced each of the ~40 standards' computation against what its description claims to measure:
`model calls per hour`, `buckets with headroom`, `buckets not exhausted`, `no bucket pinned at rpm
1`, `calls that succeed` (correctly reports UNMEASURED under `MIN_CALLS_TO_JUDGE_RATE` instead of a
manufactured 100%/0%), `chunks nobody answered`, `corpus read finishes inside a day`, `feats per
chunk`, `corpus read is progressing`, `page roll complete`, `coverage figures are current`,
`entries settled`, `sources with a reachable wiki`, `every module imports`, `no high-severity
findings open`, `phases implemented`, `unexpected swallowed failures` (correctly excludes the
probe classes it lists), `probe failures (reported, not judged)`, `cached records that were fully
read`, `sentences that survive the verbatim check`, `rosters that name their own fiction`,
`shelfmarks are unique`, `hand-built assays match the charter`, `the automation reproduces the
charter`, `the library's counters are moving`, `files that parse`, `verifiers all run`, `the full
audit is recent`, `every source is fully catalogued` (correctly distinguishes UNMEASURED
zero-denominator from a true 0%), `the character sweep is newer than the catalogue`, `every running
job is advancing`, `every pool failure is recognised`, `fandom answers this machine`, `disk space`,
`promotions have their spine codes amended`, `the local model has a live runner`, `the local model
produces tokens`, `every managed job is running`, `one instance of each job`, `the published panel
is fresh`, `model IDs their providers still serve`, `every declared floor is measured`. Each reads
the field its prose says it reads; none reads a stale/shared file mislabeled as a live signal
beyond what its own docstring already discloses (e.g. `CHARTER_REGRESSION.json`'s 26h freshness
floor is itself the stated check, not a hidden staleness bug).

### Diagnostic-only truncations (not Hard-Rule-0 violations) — confirmed bounded, not real-data-dropping
- `:785` `worst = sorted(good, key=...)[:3]` — feeds only the human-readable `detail` string; the
  actual `cov`/`have`/`wiki` numbers driving the `holds` verdict are summed over the full `good`
  list beforehand. Preview only.
- `:937` `_worst = sorted(_unrec, ...)[:3]` — same shape; `holds` is `not _unrec` (full list).
  Preview only.
- `:786` `str(c["source"])[:18]`, `:940` `str(r.get("error"))[:60]`, `:1006` `[:120]` on a joined
  pending-list string, `:1038` `resident[0][:28]` — all string-display truncations inside an
  already-complete listing, not roster truncation.
None of these drop an entity/source/page from anything that is measured or persisted; all bound
only what gets printed in a work-order sentence. Confirmed CLEAN against Hard Rule 0.

### `runguard`-adjacent write and self-check mechanics — CLEAN
`job_stamp()` (`:285-294`) is correct per its own regression note (stamp carried forward while size
holds). `JOB_WATCH` is written via `open(tmp,"w")` + `silence.replace_retry` (`:903-906`) — atomic,
compliant. The "every declared floor is measured" self-check (`:1159-1186`) was spot-checked by
hand against the full `MIN_/MAX_` declaration list; every declared floor is in fact referenced
inside `check()`'s body — the self-check's own claim holds.

### Minor, not separately flagged
`:903-906` (`JOB_WATCH` write) has no cross-process lock either, but writes are atomic
(`replace_retry`) so the failure mode is "last writer's stall-tracking wins," not corruption —
noted, not raised as a separate finding, since it degrades gracefully (worst case: a stall
gets under- or over-counted for one cycle, not silently permanently wrong).

---

## src/weave_index.py — CLEAN (one low-confidence note)

Read in full. `load_records()` and `designations()` both cache correctly against
`_records_sig()` (file count + max mtime), which was itself the fix for the m17 stale-cache bug
this file's own comments describe (`:96-104`, `:181-187`) — verified the fix is actually in place,
not just claimed. `norm()`/`continuity_of()` correctly preserve a declared continuity as a suffix
so two same-named entities under different Earths/timelines stay distinct (`:136-162`). The
cross-source candidate build (`main()`, `:229-272`) computes `candidates` over the FULL `index`
dict with no cap; the only slices present (`top = ...[:18]` at `:259`, `spread ... [:10]` at
`:255`, `srcs[:5]` at `:264`) are all inside the human-readable `print()` summary — the atomic
writes at `:268-270` (`silence.write_json`, correctly used) persist the complete `index` and
`candidates` with nothing sliced off. Compliant with the two-writer/atomic-write contract and with
Hard Rule 0.

One low-confidence note, **UNVERIFIED**: `build()` truncates each entry's stored `description` to
400 characters (`:224`, `(e.get("description") or "")[:400]`). This is not a roster/listing
truncation (no entity is dropped), but it does discard evidence text from what gets written to
`ENTITY_INDEX.json`/used for weave candidate review. Flagging for awareness rather than as a
confirmed Hard-Rule-0 breach, since the rule as stated targets truncation of *listings* of
entities/pages/chunks/sources, not per-field string length.

---

## src/runguard.py — mostly CLEAN, one real race

Read in full. The ownership-check design (`claim()`/`beat()`/`release()` all checking
`rec.get("agent") == agent` before acting) correctly implements the m27 fix described in its own
docstring — a run can never refresh or close a record it does not own. `_land()` writes via
`open(tmp,"w")` + `silence.replace_retry` (`:72-80`) — atomic, compliant.

### FINDING 6 (new) — `claim()` has an unguarded TOCTOU race against a concurrent `claim()`
`runguard.py:98-121`:
```python
def claim(agent, path=GUARD, note=None):
    prior = read(path)                          # :105  read
    if holder_is_live(prior):                    # :106  check
        ...
        return False, (...)
    now = time.time()
    rec = {"started": now, "heartbeat": now, "done": False, "agent": agent}
    ...
    if not _land(rec, path):                     # :119  act (write), no lock held across read+write
        return False, "could not write the guard record"
    return True, "claimed"
```
There is no lock (file lock, or any other mutual-exclusion primitive) spanning the `read()` at
`:105` and the `_land()` write at `:119`. If two runs call `claim()` within the same narrow window
— both see no live predecessor, both proceed to write — the second `_land()` silently overwrites
the first's guard record. Both callers receive `(True, "claimed")` and both believe they hold the
guard, which is exactly the overlap this entire module exists to prevent (the m27 incident this
file's docstring describes was two runs overlapping, just via a different mechanism — an
improvised heartbeat helper rather than a double-claim). **VERIFIED** by inspection of the full
function; not observed to have fired in production. The window is narrow (claim is normally called
once at a run's start, not on a tight cadence like `beat()`), so this is a lower-probability race
than Findings 3/4 in `endpoint.py`, but the consequence — silently defeating the module's sole
purpose — is severe when it does land. Severity: MEDIUM (narrow window, high-consequence).

### CLEAN otherwise
`read()`, `holder_is_live()`, `beat()`, `release()`, `main()` — all read correctly, ownership
checks match their docstrings, no swallowed-failure ambiguity (each refusal path prints a specific
reason to stderr and returns `False`, never silently succeeding on a rejected write).

---

## src/recover_folder_records.py

### FINDING 7 (new) — self-documented two-writer-contract bypass, and its own justifying comment is false
`recover_folder_records.py:143-150`:
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
Two parts:
1. **The write itself is atomic** (`silence.write_json`, correctly used) — so this is not a
   truncate-then-fill bug. But it IS a confirmed bypass of the two-writer contract as this
   project's own rules define it: a record file under `data/records/` is written directly with
   `silence.write_json` instead of going through `pipeline.write_record_catalogue`, which the
   comment itself concedes. **VERIFIED** — read the function in full; there is no call to
   `pipeline.write_record_catalogue` anywhere in this file, and the write lands straight to
   `data/records/<slug>.json`.
2. **The comment's own justification is false.** It claims the bypass "is flagged in
   NEXT_STEPS" — `grep -i recover NEXT_STEPS.md` and `grep -i write_record_catalogue
   NEXT_STEPS.md` both return zero hits; `NEXT_STEPS.md` exists but never mentions this script or
   this issue by name. So the one piece of tracking this comment points to as covering the gap
   does not exist. **VERIFIED** by reading `NEXT_STEPS.md` and grepping it. This is exactly the
   class of bug the audit brief calls out under lens item 6 — a comment that misdescribes its own
   code's status, which is what stops anyone else from noticing the gap is untracked.

Severity: MEDIUM. The write is safe from corruption; the risk is purely that records recovered by
this tool skip whatever merge/dedup semantics `write_record_catalogue` provides for the
cast-growing side, and nothing outside this file's own comment currently tracks that as an open
item.

### CLEAN otherwise
`slug()`, `load()`, the `EXCLUDED_REGISTER_SOURCES` filtering, the roll-empty detection, and the
final `silence.write_json(ROLL, ...)` write (`:156`, also atomic and correctly used) are all
correct against their stated purpose. No entity/source list is capped — `empty`, `by_source`, and
`entries` are all built over the complete input with no slicing.

---

## src/resonance.py — CLEAN

Read in full. `hodge_decompose()`'s fixed-600-iteration Gauss-Seidel has no convergence check, but
that is a deliberate implementation choice (documented as "plain Gauss-Seidel... no dependencies,"
`:59-60`), not a correctness bug — the gauge-fix (mean-zero shift, `:78-79`) and the
gradient/residual split (`:81-96`) are computed correctly against the stated least-squares
objective. `incomparability_rate()` (`:109-128`) computes `total`/`inc`/`rate` over the FULL
`itertools.combinations` of all vectors — no truncation of the pair space; only the `examples` list
is capped at 5 (`:124`, display-only, matches its own field name). `dominates()` (`:101-106`) is a
correct componentwise preorder check. `resonance_strength()` (`:133-149`) is a read-only linear
scan over `g["pairs"]`, no cap, no write anywhere in this file — no two-writer contract exposure
possible.

---

## Summary of findings

| # | File:Line | Severity | Status |
|---|---|---|---|
| 1 | endpoint.py:200-233 | HIGH (confirms filed) | VERIFIED |
| 2 | endpoint.py:126-173 | HIGH (confirms filed) | VERIFIED |
| 3 | endpoint.py:83-94 | HIGH | VERIFIED |
| 4 | endpoint.py:356-370 | HIGH | VERIFIED |
| 5 | standards.py:966-982 | MEDIUM | VERIFIED |
| 6 | runguard.py:98-121 | MEDIUM | VERIFIED |
| 7 | recover_folder_records.py:143-150 | MEDIUM | VERIFIED |
| — | weave_index.py:224 description[:400] | informational | UNVERIFIED |

`resonance.py`: CLEAN, no findings.
