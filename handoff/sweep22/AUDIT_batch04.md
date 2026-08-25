# Batch 4 audit — standards.py, endpoint.py, weave_index.py, runguard.py, catalogue_models.py, repass_bands.py

Every line of every file was read top to bottom (standards.py 1260 lines, endpoint.py 370,
weave_index.py 276, runguard.py 219, catalogue_models.py 172, repass_bands.py 112). Findings
below; cross-checked against BUGS.md where relevant and against the live filesystem
(`data/records`) for one factual claim.

---

## endpoint.py — HIGH PRIORITY MODULE (per assignment)

### HIGH — `fetch_raw()` collapses every failure class into the identical "absent" signature — VERIFIED
This is the mechanism BUGS.md already names as **M16 / m93 / m94**'s shared root, confirmed here
by direct read of the code that produces it.

```python
190  def fetch_raw(host, titles, workers=2):
...
200      def one(t):
201          url = raw_url(host, t)
202          if not url:
203              return t, None
204          try:
205              body = _get(url, timeout=40)
206          except urllib.error.HTTPError as e:
...
217              if getattr(e, "code", None) in (404, 410):
218                  silence.note("endpoint.py:fetch_raw-absent")
219              else:
220                  silence.note("endpoint.py:fetch_raw-refused-%s" % getattr(e, "code", "?"))
221              return t, None
222          except Exception:
223              silence.note("endpoint.py:fetch_raw")
224              return t, None
225          if not body or body.lstrip().lower().startswith(("<!doctype", "<html")):
226              return t, None
227          return t, body
...
229      with ThreadPoolExecutor(max_workers=workers) as ex:
230          for t, body in ex.map(one, titles):
231              if body:
232                  out[t] = body
233      return out
```

Four distinct situations — (a) confirmed 404/410 absence, (b) an HTTP refusal (403/429/500...),
(c) a raised exception (timeout, connection reset, DNS failure), (d) a 200 response that turns
out to be an HTML error page rather than wikitext — all `return t, None` at lines 203, 221, 224,
226. The `silence.note()` class name at 218/220/223 is the *only* place the distinction survives,
and it goes to a diagnostic ledger, never to the return value. `fetch_raw`'s signature is
`{title: wikitext}`; a title's simple absence from that dict is the only thing any caller can see,
and it means "confirmed absent" and "the request never completed" identically.

The comment at 207-216 already states this precisely ("A REFUSAL IS NOT AN ABSENCE... a rate-limit
during a raw pass was therefore filed as permanent absence... the fix is to make the two cases
legible in the ledger") but the fix described was never carried into the return contract — only
into the silence-note class name, which no caller reads.

**Confirmed downstream, in the exact place BUGS.md's m93 already documents** (not my batch, cited
for the trace only): `hostcheck.py:134-139`

```python
if EP.detect(host)["mode"] == EP.MODE_RAW:
    got = EP.fetch_raw(host, names[:12])
    n = min(len(names), 12)
    return {"host": host, "probed": n, "hits": len(got),
            "rate": round(len(got) / n, 3), ...}
```

`hits = len(got)` treats every dropped title — network failure or genuine absence alike — as a
miss, and `rate` is a real float (never `None`), so a total network failure during a raw-mode
probe reports a real, judgeable "0% held" instead of "unmeasured." Twenty lines below, the
API-mode branch of the *same function* (`hostcheck.py:150-155`) explicitly guards against this
exact shape (`"NOT a rate of zero. A request that failed is not a wiki that holds nothing"`) —
the fix pattern already exists in the file, just not on the path `fetch_raw` feeds.

**`feats.py:437`** (`return EP.fetch_raw(host, titles)`, inside `fetch()`) and
**`hostcheck.py:246`** (`[b[:8000].lower() for b in EP.fetch_raw(...).values()]`) are the other two
live callers; both inherit the same blind spot.

**Repair shape** (not applied — report only): `one()`'s three failure branches need to return a
tri-state (e.g. `(t, body, status)` with status in `{"absent", "refused", "error"}`) instead of a
uniform `None`, and `fetch_raw`/`exists_raw`'s callers need to be updated to read it. This is
exactly the "public-signature change needing a review cycle" BUGS.md already flags for M16.

### HIGH — `detect()` conflates "confirmed absent" with "probe failed," caching the result as MODE_DEAD for 24h — VERIFIED, new (not the same locus as M16/m93/m94, same failure family, at the detection layer)

```python
143      found = {"mode": MODE_DEAD, "path": None}
144      for path in API_PATHS:
145          try:
146              body = _get(f"https://{host}{path}?action=query&format=json&meta=siteinfo")
147              d = json.loads(body)
148              if isinstance(d, dict) and ("query" in d or "batchcomplete" in d):
149                  found = {"mode": MODE_API, "path": path}
150                  break
151          except Exception:
152              silence.note("endpoint.py:detect-api")
153
154      if found["mode"] == MODE_DEAD:
155          for path in RAW_PATHS:
156              try:
157                  body = _get(f"https://{host}{path}?title=Main_Page&action=raw")
158                  if body and not body.lstrip().lower().startswith(("<!doctype", "<html")):
159                      found = {"mode": MODE_RAW, "path": path}
160                      break
161              except Exception:
162                  silence.note("endpoint.py:detect-raw")
163
164      if found["mode"] == MODE_DEAD:
165          import time as _t
166          found["at"] = _t.time()
167      with _LOCK:
168          mem[host] = found
169      _save()
170      return found
```

Both probe loops catch every exception the same way regardless of cause — a 403 (confirmed: API
closed), a 404 (confirmed: wrong path), a connection timeout, a DNS failure, and a 5xx are all
"this path didn't work, try the next one." Unlike `fetch_raw`, the `silence.note()` calls here
(`endpoint.py:detect-api`, `endpoint.py:detect-raw`) do not even carry the status code, so the
distinction is lost earlier than in the fetch_raw case. If every one of the 6 paths fails for
*any* reason during one bad network minute, `found` stays `{"mode": MODE_DEAD, ...}`, gets a
timestamp, and is cached to `data/ENDPOINTS.json` (line 58/`CACHE`) under `DEAD_TTL = 24 * 3600`
(line 124). `api_url()` (176-179) and `raw_url()` (182-187) both key off this cached mode, so
every caller of `api()`/`fetch()`/`fetch_raw()` for that host reads it as fully dead — no API,
no raw — for up to 24 hours from one bad probe window, indistinguishable in the cache from a host
that was cleanly and correctly probed and found to have neither endpoint.

The module's own comment at 117-124 shows this is a known, reasoned-about tradeoff (the 24h TTL
already replaced an earlier "no expiry ever" design after exactly this shape bit the project on
2026-08-23/24 with the entire fandom.com domain). It is not an oversight — but it is still open:
the fix reduces the blast radius from permanent to "up to a day," not to "never." A host probed
during any transient outage is unreadable through every mode for the rest of that window, and
nothing distinguishes "probed and confirmed closed" from "never successfully probed" in the cache
entry itself (`{"mode": "dead", "path": None, "at": ...}` looks the same either way). Recommend:
record which failure class produced MODE_DEAD (all-exceptions vs. all-clean-negative), and treat
an all-exceptions dead verdict as immediately re-probable rather than TTL-gated.

### MEDIUM — `register()` has no lock and no exception handling around a shared-file replace — VERIFIED, live caller confirmed

```python
356  def register(source, urls):
357      """Record where a source's material actually lives."""
358      try:
359          with open(PAGES_FILE, encoding="utf-8") as f:
360              d = json.load(f)
361      except Exception:
362          silence.note("endpoint.py:334")
363          d = {}
364      d[source] = sorted(set((d.get(source) or []) + list(urls)))
365      os.makedirs(os.path.dirname(PAGES_FILE), exist_ok=True)
366      tmp = PAGES_FILE + ".tmp"
367      with open(tmp, "w", encoding="utf-8") as f:
368          json.dump(d, f, indent=1, sort_keys=True)
369      os.replace(tmp, PAGES_FILE)
370      return d[source]
```

Two problems, both against the module's own `_save()` a few lines above (line 83-94), which
handles the identical shape correctly:

1. **No lock.** `_load()`/`_save()` for `ENDPOINTS.json` use the module's own `_LOCK`
   (`threading.Lock`, line 66). `register()` uses none, despite doing the exact same
   read-JSON / modify-dict / write-JSON sequence on a different shared file
   (`data/SOURCE_PAGES.json`). Two concurrent calls (real: `scout.py:199` calls
   `EP.register(source, kept)` once per source, and `scout.py` is written to be run per-source
   in a loop that could plausibly be parallelised or run alongside a second invocation) can both
   read `d` before either writes, and the second write silently discards the first's addition —
   a classic lost-update race.
2. **No exception handling around the replace.** `_save()` wraps its `os.replace()` in
   `try/except Exception: silence.note(...)` (line 87-94). `register()`'s `os.replace(tmp,
   PAGES_FILE)` at line 369 is bare — a `PermissionError` from a concurrent reader (which is
   exactly the scenario `silence.replace_retry`'s own docstring says this project's state files
   routinely hit) propagates uncaught and crashes the caller (`scout.py`) mid-scout, losing
   `urls` for `source` that were already verified.

Recommend routing through `silence.replace_retry(tmp, PAGES_FILE)` (as the project's own helper
is designed for) and adding the same `_LOCK` this file already has in scope.

### LOW / judgment — `_save()` uses a bare `os.replace()` instead of `silence.replace_retry()`
`endpoint.py:92`: `os.replace(tmp, CACHE)` inside a `try/except Exception` that only notes and
drops the failure, rather than the project's dedicated `silence.replace_retry()` (which retries
across a Windows `PermissionError` from a concurrent reader before giving up). Not crash-prone
like `register()` above since it's already inside a try/except, but a `PermissionError` here
silently drops that round's probe result to the cache instead of retrying — the exact hazard
`silence.replace_retry` exists to absorb for state files. Judgment call, not a violation of the
letter of the two-writer rule (records go through the sanctioned writer; this is a *cache* file),
but inconsistent with the project's own stated discipline.

### CLEAN
- No caps/truncation on rosters, page lists, or entry lists anywhere in this file (Hard Rule 0
  compliant). `fetch_raw`/`fetch_html`/`exists_raw` all process the full `titles`/`urls`
  iterable given to them.
- `_get()`'s `urllib.request.urlopen` is used as a context manager; no socket/file-handle leaks
  found anywhere in the file.
- The `UA_OVERRIDES` / dandwiki browser-UA handling and the `html_text()` tag-stripping regexes
  were read line by line; no correctness defects found there.

---

## standards.py

### MEDIUM — self-audit note: "unexpected swallowed failures" never excludes standards.py's own exceptions — VERIFIED / judgment call
Directly responsive to the task's instruction to check whether standards.py can misreport on its
own process.

```python
536  probe = sum(v for k, v in ledger.items()
537              if any(t in k for t in ("endpoint.py:detect", "endpoint.py:fetch",
538                                      "hostcheck.py:probe", "hostcheck.py:candidates",
539                                      "hostcheck.py:relevance", "scout.py:verify")))
540  real = sum(ledger.values()) - probe
541  out.append(_s(
542      "unexpected swallowed failures", real <= MAX_SWALLOWED_NEW, f"{real:,}", ...
```

The exclusion list names only the classes where "probing IS the measurement" (endpoint/hostcheck/
scout). It does not exclude `standards.py:*` classes. standards.py itself contains roughly two
dozen `silence.note("standards.py:...")` call sites across its own try/except blocks (e.g. lines
535, 578, 599, 619, 633, 648, 683, 699, 718, 747, 775, 815, 843, 871, 893, 920, 953, 982, 992,
1018, 1049, 1068, 1096, 1127, 1142, 1157, 1186 — a non-exhaustive sample). Every one of those,
when it fires (whether from a genuinely missing optional data file like `ROSTER_AUDIT.json` on a
fresh checkout, or from an actual bug inside standards.py's own arithmetic), is counted toward
`real` and reported through the work-order text as "something upstream failing and being
tolerated" — attributing standards.py's own faults to an unnamed upstream, on the one standard
whose whole job is to name where a swallowed failure lives. This is not necessarily wrong for the
missing-optional-file cases (something upstream genuinely hasn't produced that file yet), but it
means a bug *inside standards.py itself* — the instrument meant to catch this class of thing —
would never be distinguished from "the rest of the pipeline is unwell" by this standard. Given the
project already did the harder work of carving out endpoint/hostcheck/scout as "probing is the
point," carving out (or separately reporting) `standards.py:*` would close the same gap for the
instrument itself.

### CLEAN — explicitly guarded against a related self-measurement bug
Lines 1078-1096 (`"every managed job is running"`) show the module is otherwise careful about
this exact class of error: `include_self=True` is called out by comment as load-bearing, because
without it each renderer process (`dashboard.py`, `publish.py`) would report *itself* as down —
and the comment documents that this exact failure happened on 2026-08-25 and was fixed. Worth
recording as a positive: the standards module is not naive about self-measurement in general, just
incomplete on the one class above.

### LOW / judgment — display-only truncations, not measurement truncations
`standards.py:785` (`sorted(good, key=...)[:3]`), `:937` (`sorted(_unrec, ...)[:3]`), `:786`
(`str(c["source"])[:18]`), `:940` (`str(r.get("error"))[:60]`), `:1006` (`[:120]` on a joined
pending-sources string), `:1038` (`resident[0][:28]`). All of these bound *human-readable detail
strings* attached to a work order (e.g. "worst 3 sources", "top 3 unrecognised pool failures");
the underlying measurement each standard reports on (`cov`, `len(_unrec)`, `len(_pending)`, etc.)
is computed over the full, unsliced collection in every case checked. Judgment calls, not Hard
Rule 0 violations.

### CLEAN — two-writer contract
`state/job_progress.json` (the one shared/state file this module writes) goes through
`tmp` + `silence.replace_retry(tmp, JOB_WATCH)` (lines 903-906) — the sanctioned pattern.

No other correctness defects, mutable-default-argument issues, or dead code found on a full
top-to-bottom read of this file's 1260 lines.

---

## weave_index.py

### HIGH — non-atomic bare writes to shared data files with live concurrent readers — VERIFIED
```python
266      if args.write:
267          with open(OUT_INDEX, "w", encoding="utf-8") as f:
268              json.dump({k: v for k, v in index.items()}, f, ensure_ascii=False)
269          with open(OUT_CAND, "w", encoding="utf-8") as f:
270              json.dump(candidates, f, indent=2, ensure_ascii=False)
```
`OUT_INDEX` = `data/ENTITY_INDEX.json`, `OUT_CAND` = `data/WEAVE_CANDIDATES.json` (lines 37-38).
Both are written directly with no `tmp` file and no `silence.replace_retry` — the exact pattern
the project's own two-writer contract exists to prevent, and the exact pattern this same module
avoids for the *records* it reads (`load_records()`'s docstring explains the caching discipline
around concurrent access to those files in detail). Confirmed live readers of these two files:
`cosmology_graph.py`, `thread_integrity.py`, and `weave.py` (grep-confirmed). A reader hitting
either file mid-write sees a truncated/invalid JSON document (a `json.dump` of a multi-MB dict is
not atomic at the OS level); a crash or kill mid-write leaves a permanently corrupt file with no
recovery path. Recommend routing both writes through a `tmp` + `silence.replace_retry` pair, as
every other cross-process shared file in this batch does.

### LOW / judgment — description field truncated to 400 chars inside the identity-adjudication index
```python
224  "description": (e.get("description") or "")[:400],
```
This bounds a *field* inside each index entry, not the entry list itself — `build()` (205-226)
iterates every record and every entry with no cap, and `index`/`candidates` are written whole.
Not a Hard Rule 0 violation of a roster/page/entry list. Worth a flag anyway because this exact
field is the one a human or model uses at `weave.py`'s adjudication step to decide whether two
same-named entries are the same entity or two different ones sharing a name — a distinguishing
detail (e.g. a stated continuity, world, or era) that happens to land after character 400 would
be silently unavailable to that judgment. Judgment call, not a defect.

### CLEAN
- `main()`'s printed report slices (`spread[:10]` at 255, `top = ...[:18]` at 259, `srcs[:5]` at
  264) are console-summary-only; the persisted `index`/`candidates` written to disk are the full,
  unsliced dicts built by `build()`. Hard Rule 0 compliant for the actual data product.
- `designations()`'s cache-invalidation-by-signature (`_records_sig()`) is correct and is the
  documented fix for a prior staleness bug (BUGS m17); re-verified here that the signature
  (`file count, newest mtime`) is recomputed on every call and compared before trusting the
  cache — no remaining staleness issue found.
- No mutable default arguments, no unreachable branches, no bare `except:` (all are
  `except Exception:` paired with `silence.note`, per project convention).

---

## runguard.py

### MEDIUM — `claim()` has a check-then-act race with no exclusive lock — VERIFIED (narrow window)
```python
98   def claim(agent, path=GUARD, note=None):
...
105      prior = read(path)
106      if holder_is_live(prior):
107          age = time.time() - prior.get("heartbeat", 0)
108          return False, (...)
109      now = time.time()
110      rec = {"started": now, "heartbeat": now, "done": False, "agent": agent}
...
119      if not _land(rec, path):
120          return False, "could not write the guard record"
121      return True, "claimed"
```
There is no file lock, `O_EXCL` create, or compare-and-swap between the `read(path)` at line 105
and the `_land(rec, path)` at line 119. Two `claim()` calls issued close enough together (both
observing no live predecessor) will both proceed to write; whichever's `_land()` lands second
silently overwrites the first's record, and both callers' in-process return value is
`(True, "claimed")` — so two runs can simultaneously believe they hold exclusivity, which is
exactly the failure category this module was written to close (per its own docstring, for the
*heartbeat* half of the problem — m27). The window here is small (one file read plus one atomic
replace, no network I/O in between) but real, and the module's own worked history shows this
project has been bitten by exactly this shape once already. Not flagged HIGH because the
practical trigger (two `claim()` calls within milliseconds of each other) is much narrower than
m27's actual trigger (an interactive session and a 45-minute background run overlapping).

### CLEAN — this module is otherwise a model of the two-writer contract done right
- `beat()` (124-148) and `release()` (151-172) both explicitly re-read the record and refuse to
  act unless `rec.get("agent") == agent`, which is the actual, correctly-implemented m27 fix the
  file's docstring describes.
- `_land()` (72-80) always writes through `tmp` + `silence.replace_retry`, the sanctioned pattern.
- `read()` (52-69) deliberately conflates "no file" and "unreadable file" for a stated, sound
  reason (a corrupt guard must not permanently wedge the pass) — this is documented reasoning, not
  an oversight, and I agree with the design as written.
- No Hard Rule 0 issues (no rosters/lists in this file at all), no mutable defaults, no dead code.

---

## catalogue_models.py

### HIGH — bare, non-atomic write to a shared data file that standards.py depends on — VERIFIED
```python
155  payload = {"at": time.strftime("%Y-%m-%d %H:%M"), "providers": rows, "stale": stale}
156  os.makedirs(os.path.dirname(OUT), exist_ok=True)
157  with open(OUT, "w", encoding="utf-8") as f:
158      json.dump(payload, f, indent=1, sort_keys=True)
```
`OUT` = `data/PROVIDER_MODELS.json` (line 51). No `tmp` file, no `silence.replace_retry`. This
file is read directly by `standards.py`'s `"model IDs their providers still serve"` check
(`standards.py:1146`), which the dashboard polls on a cycle per the project's own stated pattern.
A reader hitting this file mid-write during a `catalogue_models.py` sweep risks a JSON parse
failure; standards.py's own read is wrapped in `try/except Exception:
silence.note("standards.py:provider-models")` (standards.py:1156-1157), so the practical effect
is that standard silently going unmeasured for that one poll rather than crashing anything — but
that is itself the exact "measured nothing" failure mode `standards.py`'s own docstring at
1159-1164 calls out as "worse than no floor." Recommend the same `tmp` + `silence.replace_retry`
fix as the other two write sites in this batch.

### LOW — `locals().get("last", ...)` fallback pattern is fragile but not currently a live bug
```python
83   tries = []
84   for path in LIST_PATHS:
85       if base.endswith("/v1") and path.startswith("/v1"):
86           continue
87       tries.append(base + path)
88   for url in tries:
89       try:
...
103      except Exception as e:
104          silence.note("catalogue_models.py:ask_provider")
105          last = f"{type(e).__name__}: {str(e)[:70]}"
106  return {"provider": name, "error": locals().get("last", "no model list endpoint")}
```
`last` is only ever assigned inside the `except` block of the `tries` loop; the fallback string at
line 106 relies on `tries` never being empty to guarantee `last` exists whenever every attempt
fails. Given `LIST_PATHS = ("/models", "/v1/models")`, at least `/models` is always appended to
`tries` regardless of `base`'s shape, so `tries` cannot currently be empty and this is not a live
bug — flagging only because the fallback silently depends on that invariant holding, and a future
edit to `LIST_PATHS` (e.g. adding an entry that's always filtered by the `/v1` guard) would make
this default text mask a `NameError`-shaped hole instead of the intended message. Prefer
initializing `last = "no model list endpoint"` before the loop.

### CLEAN
- No caps on the provider list or the model list actually persisted: `rows` (full sweep result)
  and each provider's full `r["models"]` list are written unsliced into `payload`. The only
  `[:8]` / `[:10]` slices (lines 146, 153) feed a printed/"available_sample" preview field
  alongside the full list stored elsewhere in the same payload — judgment call, not a violation.
- Thread pool usage (`ThreadPoolExecutor(max_workers=workers)`, line 127) is a proper context
  manager; no leak.
- No mutable default arguments; no bare `except:`.

---

## repass_bands.py

### MEDIUM — hardcoded source-count denominator is already stale — VERIFIED against the live filesystem
```python
91   print(f"  demoted to unassayed: {len(demoted_sources):,} of 211")
```
`211` is a magic number for "total sources," not derived from `recs` or any data file. Checked
against the live corpus: `data/records` currently holds **217** files (`ls data/records | wc -l`
→ 217), not 211. The denominator this line prints is already wrong today, will keep drifting as
the Acquisitions Roll grows (per CLAUDE.md, ~215 and rising), and nothing regenerates it. Should
be computed from `len(recs)` (already available in scope at line 36) or an equivalent live count
rather than a literal.

### CLEAN
- Writes go through `PL.write_record(path, rec)` (line 79) — the sanctioned pipeline writer, per
  the project's two-writer contract. No bare `open(path, "w")` anywhere in this file.
- The demotion/kept/gate-recheck loop (lines 43-80) processes every record and every entry
  returned by `PL.records()` with no slicing — Hard Rule 0 compliant. The only `[:N]` slices in
  the file (`kept_entries[:14]` at 95, `demoted_entries[:8]` at 101) are confined to the console
  summary printed *after* the full unsliced pass has already run and already written every
  changed record — sample display, not truncated processing.
- `PL.valid_scale_note()` is called on the full, untruncated `sn`/`evidence` text for every actual
  gate decision (lines 50, 64, 72); the `[:70]` slices at 51/65/67/102 only truncate the copies
  kept for the print-report tuples, never the values used to decide anything.
- No mutable default arguments, no bare `except:`, no unreachable branches found.

---

## Summary table

| module | high | medium | low |
|---|---|---|---|
| endpoint.py | 2 | 1 | 1 |
| standards.py | 0 | 1 | 1 (group of 6 slices) |
| weave_index.py | 1 | 0 | 1 |
| runguard.py | 0 | 1 | 0 |
| catalogue_models.py | 1 | 0 | 1 |
| repass_bands.py | 0 | 1 | 0 |
