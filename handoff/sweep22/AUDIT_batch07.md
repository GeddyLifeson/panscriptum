# Batch 07 audit — feats.py, allsweep.py, address_space.py, tuning.py, style_audit.py, physics.py

Every line of every assigned module was read top to bottom. Findings below, grouped by severity,
each cited as `file.py:LINE` with quoted code and labeled VERIFIED/UNVERIFIED.

---

## HIGH PRIORITY TASK: M16 in feats.py — verified at source

**M16 claim: `api()` caches a network timeout as a verified "nothing here", permanently.**
**VERIFIED — and the blast radius is wider than `api()` itself.**

### The root: `api()` cannot tell its caller *why* it returned None

`feats.py:120-174`:

```python
def api(host, params, retries=2):
    """One MediaWiki API call. Returns parsed JSON, or None."""
    ...
    for attempt in range(retries + 1):
        try:
            ...
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                silence.note("feats.py:api-404")
                return None
            silence.note("feats.py:125")
            if e.code == 429:
                ...
                if attempt == retries:
                    return None
                time.sleep(min(wait, 120))
                continue
            if attempt == retries:          # 404 already returned above
                return None
            time.sleep(2 + attempt * 4)
        except Exception:
            silence.note("feats.py:139")
            if attempt == retries:
                return None
            time.sleep(2 + attempt * 4)
```

`None` is the return value for **three semantically different outcomes**: a confirmed 404, a
429 that never cleared, and *any other exception* (`socket.timeout`, `URLError`/DNS failure,
`ConnectionResetError`, etc.) that survived every retry. A caller holding `None` has no way to
tell "this wiki genuinely has nothing" from "the network dropped the request twice." That
ambiguity is exactly M16's premise, and it is real, at this exact function.

### The chain that turns one timeout into a permanent record

1. **`alive(host)`** (`feats.py:177-178`):
   ```python
   def alive(host):
       return bool(api(host, {"action": "query", "meta": "siteinfo"}, retries=0))
   ```
   Called with **`retries=0`** — a single dropped packet is enough to make `alive()` return
   `False`. There is no distinction available to the caller between "this is not a wiki" and
   "the probe glitched once."

2. **`resolve_hosts()`** (`feats.py:243-299`) uses `alive()` to test slug guesses:
   ```python
   for slug in _slugs(src):
       h = f"{slug}.fandom.com"
       if alive(h):
           known[src] = h
           break
   else:
       known[src] = None
   ```
   (`feats.py:282-288`.) If every guessed slug happens to fail `alive()` — including from a
   single transient blip per guess — `known[src] = None` is written, indistinguishable in the
   data from "verified: no wiki exists."

3. That `None` is then **permanent**, because of the very next guard in the same loop
   (`feats.py:265-266`):
   ```python
   if src in known:
       continue
   ```
   `in` tests key *presence*, not truthiness. Once `known[src]` exists — even as `None` — every
   future call to `resolve_hosts()` skips that source without ever re-attempting resolution.
   The dict is then written to `data/WIKI_HOSTS.json` via `silence.replace_retry` (correctly
   atomic — this part is fine) and loaded back on every subsequent run.

4. **`roll()`** (`feats.py:831-921`) reads that host map and, for any source whose host is
   `None`, drops it from the job list entirely (`feats.py:840-842`):
   ```python
   h = hosts.get(r["source"])
   if not h or (only and only not in r["source"]):
       continue
   ```
   So a source that got a false-negative `None` from one bad network moment during a past
   `--hosts` run is **silently excluded from every mining run forever**, with no error and no
   visible signal — the exact "verified nothing here, permanently" failure M16 describes, one
   layer up from `api()` itself.

5. The same ambiguity recurs inside a single entity's evidence pull. `discover()`
   (`feats.py:311-368`) treats an `api()` failure identically to a genuinely empty result:
   ```python
   ap = api(host, {"action": "query", "list": "allpages", ...})
   ...
   for row in (ap or {}).get("query", {}).get("allpages", []):
   ```
   `fetch()` (`feats.py:427-453`) does the same per batch — a batch whose `api()` call fails
   silently contributes **zero pages**, indistinguishable from "these titles have no
   revisions." `evidence_for()` (`feats.py:732-808`) then writes whatever came back —
   including an empty `pages_read` caused purely by transport failure — to
   `data/feats/<host>/<name>.json` **unconditionally**, and the very next call with the default
   `cache=True` (used by `roll()`) trusts that file forever (`feats.py:736-741`):
   ```python
   if cache and os.path.exists(path):
       try:
           with open(path, encoding="utf-8") as f:
               return json.load(f)
       except Exception:
           ...
   ```
   There is no field recording whether the fetch was complete, so a mid-pull timeout on an
   entity with genuinely rich source material can freeze as "zero feats" on disk permanently.

**Real-world evidence this isn't theoretical:** `data/WIKI_HOSTS.json` currently holds 203
sources, 7 of them (`JMBrew`, `Kobold Press (Midgard Heroes Handbook, Midgard Worldbook)`, `The
Amethyst / Cockroach King screenplay (Chroma Wastes)`, `aurora_mods (Way of the Inkmaster)`,
`swordmeow's Atavist`, `the Sex Worker background`, `the Weaveshaper Ateliers`) resolved to
`null`. Several of these read as genuinely homebrew/no-wiki material and may well be honest
negatives — the point isn't that these seven are proven false negatives, it's that **the code
gives no way to ever find out**, and any future case in this class becomes permanent by
construction, by design of `resolve_hosts()`'s cache-presence check.

### Which callers would have to change if `api()`'s contract distinguished failure from empty

If `api()` returned a tri-state (e.g. `(data, status)` where `status` is one of
`"ok" | "confirmed-empty" | "failed"`, or raised a dedicated `ApiUnavailable` exception on
transport failure while still returning `None`/empty JSON for a genuine 404-style miss), every
direct and indirect caller in this chain would need an update:

1. **`api()` itself** — the return contract change, obviously the root.
2. **`alive(host)`** (`feats.py:177-178`) — needs to become tri-state (definitely up /
   definitely down / unknown), and its `retries=0` call would need reconsidering — a single
   failed probe should not be treated as equivalent to a confirmed-dead host.
3. **`resolve_hosts()`** (`feats.py:243-299`, specifically the slug loop at `282-288` and the
   `if src in known: continue` gate at `265-266`) — must stop writing `known[src] = None` on an
   "unknown" result, and must not let an "unknown" cached value satisfy `if src in known`
   forever; it needs to remain eligible for retry on a later run.
4. **`discover()`** (`feats.py:311-368`) — its two `api()` calls (allpages at `348`, search at
   `358`) currently fold failure into "zero results" via `(ap or {}).get(...)`. Would need to
   return or set a discovery-incomplete flag so a partial pull isn't mistaken for a complete
   one.
5. **`fetch()`** (`feats.py:427-453`) — same pattern per batch (`d = api(...)` at `443`); a
   failed batch currently contributes nothing to `out` with no record that it failed.
6. **`evidence_for()`** (`feats.py:732-808`) — would need a new field (e.g.
   `"complete": bool`) in the cached JSON, and its cache-hit check (`736-741`) would need to
   treat a previously-incomplete pull as eligible for re-fetch rather than trusted forever.
7. **`roll()`** (`feats.py:831-921`) — `done["empty"]` (incremented at `888-889`) currently
   conflates "confirmed no pages" with "fetch incomplete due to failure," the same ambiguity the
   module's own `errored` vs `empty` split (`860-865`, `881-889`) already solved one level up
   for outright exceptions. A parallel `done["incomplete"]` counter would close the gap.
8. **`_page_exists()`** (`feats.py:376-381`) and **`resolve_title()`** (`feats.py:384-424`) —
   both call `api()` and treat a failure identically to "no such title" today. Currently dead
   code (see MEDIUM finding below), but the same fix would be needed if either is wired in.

---

## HIGH

### `feats.py:824-825` — `remine()` writes the shared evidence cache with a bare `open(path, "w")`
**VERIFIED.**
```python
def remine(path):
    ...
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ev, f, indent=1, ensure_ascii=False)
    return ev
```
Every other writer of this exact cache path (`evidence_for()`, `feats.py:803-807`) uses the
tmp-file + `silence.replace_retry` pattern specifically because these files are read
concurrently (`evidence_for()`'s own cache-hit path handles a truncated file at
`feats.py:739-747`, self-healing by deleting it — an admission that partial writes happen).
`remine()` bypasses that protection with a plain truncating write. **Currently this is inert:
`remine()` has zero callers anywhere in the codebase** (grepped the full `src/` tree — not
called from `feats.py`, not imported/invoked by any other module). It is dead code today, but
its own docstring and the surrounding module docstring (`feats.py:795-799`, "makes every later
tuning pass a local re-mine over cached files") describe exactly the workflow this function
exists for — the moment it's wired into a bulk re-mine pass run alongside `roll()` or another
reader, this becomes a live truncation race.
**Suggested repair:** route through `silence.replace_retry` like `evidence_for()` does.

### `allsweep.py:433-437` — final report write bypasses `silence.replace_retry`
**VERIFIED.**
```python
tmp = OUT + ".tmp"
with open(tmp, "w", encoding="utf-8") as fh:
    json.dump({"imports": imports, "verifiers": verifiers, "reconcile": findings,
               "estate": est, "seconds": round(time.time() - t0, 1)}, fh, indent=1)
os.replace(tmp, OUT)
```
`allsweep.py` imports `silence` (line 45) and uses `silence.note()` throughout, but its own
primary output — `data/ALLSWEEP.json`, a file the module's own comment at `430-432` says is
read by "the audit" (itself, on a later pass, via the ESTATE tier's tree-wide file scan) and
presumably other tooling — is written with a bare `os.replace`, not
`silence.replace_retry`. `silence.replace_retry`'s own docstring
(`silence.py:223-229`) exists precisely because "on Windows the rename is DENIED while any
reader holds the target open" and names this project's own dashboard/standards polling loops as
real past collisions (WinError 5, 2026-08-23). A bare `os.replace` here will raise an unhandled
`PermissionError` and crash the whole sweep if a concurrent reader (another `allsweep.py`
instance scheduled by `foreman`/`overwatch`, or `dashboard.py`) has `ALLSWEEP.json` open at that
instant — the exact failure class the comment two lines above claims was already solved
("the audit duly reported its own report as corrupt" — that specific torn-read failure was
fixed by writing atomically, but the *rename itself* still has no retry).
**Suggested repair:** `silence.replace_retry(tmp, OUT)` instead of the bare `os.replace`.

**On the specific ask — "measurements taken from inside the process being measured":** no
instance of `reconcile()` computing a property of its own executing process was found; the
"what is actually running right now" check (`allsweep.py:293-318`) correctly shells out to
`Get-CimInstance` and correctly excludes `allsweep.py` itself from `overnight.ALL_JOBS`
(confirmed by reading `overnight.py:387-388` — `allsweep` is not a member), so it does not
double-count itself as a running job. The closest real instance of self-referential
measurement is adjacent rather than inside `reconcile()`: the ESTATE tier (`allsweep.py:394-409`,
which runs immediately before `reconcile()`) opens every file under the tree, which includes
`data/ALLSWEEP.json` — the previous run's own output. Combined with the bare-`os.replace` bug
above, a concurrent second instance of `allsweep.py` mid-rename can make this scan observe a
torn/absent file and misreport "corrupt" or "missing" for the tool's own prior report. Fixing
the write (above) closes this too.

### `address_space.py:335-338` — `SHELFMARKS.json` written with a bare `open(out, "w")`
**VERIFIED.**
```python
out = os.path.join(HERE, "data", "SHELFMARKS.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump({d: {"address": a, "shelfmark": shelfmark(a), "map_seed": map_seed(a)}
               for d, a in addrs.items()}, f, indent=2, ensure_ascii=False)
```
`SHELFMARKS.json` is read elsewhere in the codebase (`pipeline.py`, `standards.py` — confirmed
by grep), making it shared state under the two-writer contract, exactly the class of file the
contract requires `silence.replace_retry` for. `address_space.py` already imports `silence` and
uses `silence.note()` four times in this same file (`71`, `115`, `305`, `321`) — the convention
is known to the author of this module, just not applied to its own primary output.
**Suggested repair:** write to a `.tmp` path and call `silence.replace_retry(tmp, out)`.

---

## MEDIUM

### `feats.py:162` and `feats.py:351,361` — unguarded read-modify-write races on shared counters
**VERIFIED.**
```python
_RATE_LIMITED[host] = _RATE_LIMITED.get(host, 0) + 1        # feats.py:162, inside api()
```
```python
_CAP_BOUND["aplimit"] = _CAP_BOUND.get("aplimit", 0) + 1    # feats.py:351
_CAP_BOUND["srlimit"] = _CAP_BOUND.get("srlimit", 0) + 1    # feats.py:361
```
`roll()` runs many entities concurrently via `ThreadPoolExecutor` (`feats.py:899-903`), and
`api()`/`discover()` run inside those worker threads. `_throttle()` correctly guards
`_HOST_LAST[host]` with `_HOST_LOCKS[host]` (`feats.py:95-101`), and `roll()`'s own `done`
counters are correctly guarded with an explicit `lock` (`feats.py:867`, `879-889`) — so the
author clearly knows this pattern is needed for shared mutable state under threads. It was not
applied to `_RATE_LIMITED` or `_CAP_BOUND`: two threads hitting the same host's 429, or two
threads both discovering a `continue` token in the same run, can race between the `.get()` read
and the `[key] =` write and lose an increment. The consequence is understatement of a diagnostic
number the module's own docstring insists matters ("A measurement nobody prints is not a
measurement," `feats.py:908-909`) — the number gets printed, it just isn't reliably correct
under concurrency.
**Suggested repair:** guard both with `_HOST_LOCKS` (for `_RATE_LIMITED`, keyed by host — the
lock already exists per-host) or a dedicated `threading.Lock()`, mirroring the pattern already
used for `done`.

### `feats.py:376-424` — `_page_exists()` and `resolve_title()` are dead code
**VERIFIED** (grepped every `.py` in `src/` for `resolve_title(` and `_page_exists(` — no call
sites anywhere, including inside `feats.py` itself).
`resolve_title()` carries a substantial docstring describing a real, measured production bug —
"17,148 entries mined to nothing because the entity's catalogue name is not the wiki's page
title." The function that is documented as the fix for that problem is never invoked by
`discover()`, `evidence_for()`, or anywhere else in the pipeline. Either the 17,148-entry
title-mismatch problem the docstring describes is still live in production (because nothing
calls the fix), or the fix was superseded elsewhere and this is stale — either way it's worth
resolving rather than leaving an unused, well-documented fix sitting unreferenced.

### `feats.py:348-368` — `aplimit=500`/`srlimit=50` still truncate real content when they bind (Hard Rule 0)
**VERIFIED, judgment call flagged as requested.** This is a genuine cap on real content, not a
sample bound: when MediaWiki's response carries a `continue` token, `discover()` has been told
there are more subpages/search hits than it fetched, and it does not loop to get the rest — it
proceeds with only the first 500/50. The module's own docstring (`feats.py:75-84`) is candid
that this is a deliberate, incremental step: "Counting that is free and settles the question
with a number instead of an argument" — i.e. the fix so far is *measurement*
(`_CAP_BOUND`, printed in `roll()`'s summary at `910-915`) rather than *elimination* via a
continuation loop. Per Hard Rule 0's own text ("if something is genuinely too slow, the answer
is more workers, providers, or time — never a smaller universe"), this remains an open
violation whenever it binds; it is just no longer a *silent* one. Current measured state (from
`roll()`'s own printed summary convention) was not re-run as part of this audit — the code path
to check it is `feats.py --roll`, which performs live network mining and was out of scope for a
read-only sweep. Flagging as still-open per the module's own framing of it as unfinished.

### `address_space.py:106-116` — `_tier_counts()` degrades silently to 1-bit fields on a valid-but-empty `TIERS.json`
**VERIFIED (by code reading).**
```python
def _tier_counts():
    try:
        with open(os.path.join(HERE, "data", "TIERS.json"), encoding="utf-8") as f:
            t = json.load(f)
        out = {}
        for k in ("hyperverse", "xenoverse", "metaverse", "multiverse"):
            out[k] = max((v[k] for v in t.values() if v.get(k) is not None), default=0) + 1
        return out
    except Exception:
        silence.note("address_space.py:112")
        return dict(hyperverse=1, xenoverse=6, metaverse=8, multiverse=168)
```
The `except` branch's sane fallback (`xenoverse=6, metaverse=8, multiverse=168`, matching the
module's own documented census in the header) only fires if the file is *missing or malformed
enough to raise* — e.g. missing/unparseable JSON. If `TIERS.json` exists as valid JSON but is
`{}` (or every row lacks the relevant key), the `try` branch succeeds and silently returns
`{hyperverse:1, xenoverse:1, metaverse:1, multiverse:1}` for every field — collapsing the
address space's upper tiers to 1 bit each rather than falling back to the documented real
counts. This is an edge case (a partial/failed weave run producing an empty-but-valid file)
rather than a currently-observed failure, but there's no sanity check between "parsed
successfully" and "parsed to something structurally empty."

---

## LOW

### `feats.py:159,171,451,876` — stale `silence.note()` line-number labels
**VERIFIED.**
```
159:            silence.note("feats.py:125")
171:            silence.note("feats.py:139")
451:                silence.note("feats.py:374")
876:            silence.note("feats.py:695")
```
None of these labels match the line they're actually called from any more (drift from
refactoring after the labels were written). Purely cosmetic — it doesn't change behavior — but
it undermines the traceability the `silence` ledger exists to provide: a reader trying to locate
the failure site from the ledger's label lands on the wrong line four times in this one module.

### `feats.py:274-277` — unreachable branch in `resolve_hosts()`
**VERIFIED by control-flow trace.**
```python
ov = _override(src)                                    # line 274
if ov:
    known[src] = ov
    continue
```
This is only reached when the code has already established `ov` (computed identically at line
261 from the same `src`, a pure function) was falsy — every path that could have `ov` truthy
either updates-and-continues at `262-264` or continues via `if src in known` at `265-266` before
reaching here. Since `_override(src)` is deterministic and `src` hasn't changed,
`if ov:` at `275` can never be true. Harmless (costs one redundant regex-scan call per
resolution with no override and no corpus hit), but dead code that reads as live.

### `style_audit.py:44` — duplicate identical codepoint in a character class
**VERIFIED** (confirmed both characters are U+25C8 via direct codepoint inspection).
```python
parts = re.split(r"^[◈◈]\s*", text, flags=re.M)
```
`[◈◈]` is a character class containing the same character (U+25C8, the only entry-divider
symbol used anywhere in `prompts/` or `generate.py`, confirmed by grep) twice. Functionally a
no-op — behaves identically to `[◈]` — but reads as if a second divider variant was intended and
never added, or as a copy-paste slip. No behavioral impact found since only one divider
character exists in the actual generation format.

### `style_audit.py:42-45` — `entries()` silently returns nothing for unparseable text
**VERIFIED.**
```python
def entries(text):
    parts = re.split(r"^[◈◈]\s*", text, flags=re.M)
    return [p for p in parts[1:] if p.strip()]
```
A chapter file with zero `◈` dividers (malformed output, format drift, wrong file picked up)
silently contributes zero entries to the audit with no warning printed anywhere in `main()`
(`style_audit.py:201-206` just prints "read N files" and reports on whatever `entries()`
returned). Not a correctness bug in the arithmetic — the aggregate stats are still accurate over
what it *did* parse — but a malformed-input case is indistinguishable from "this file legitimately
had nothing," the same class of ambiguity flagged at HIGH severity for `feats.py`'s `api()`,
here at LOW severity because the consequence is a quieter style report rather than lost mining
work.

---

## CLEAN

- **`tuning.py`** — CLEAN. No writes to shared state (config/db/proof files are read-only from
  this module), no caps, no mutable-default-arg issues, no unguarded shared-state races found.
  The one historically-documented bug the module's own docstring calls out — `workers()`
  treating a requested `0` as falsy and silently substituting the full profile count
  (`tuning.py:233-240`) — was checked directly against the current code
  (`return min(requested, n) if requested is not None else n`, `tuning.py:244`) and is
  correctly fixed: `0 is not None` is `True`, so `min(0, n)` correctly returns `0`.
- **`physics.py`** — CLEAN. Pure-function module, no I/O beyond argparse printing, no shared
  state, no caps. `kinetic()`'s relativistic/Newtonian boundary and `>= C` guard were checked
  directly and are consistent with the docstring's claims.

---

## Summary counts

| module | HIGH | MEDIUM | LOW |
|---|---|---|---|
| feats.py | 2 | 3 | 2 |
| allsweep.py | 1 | 0 | 0 |
| address_space.py | 1 | 1 | 0 |
| tuning.py | 0 | 0 | 0 |
| style_audit.py | 0 | 0 | 2 |
| physics.py | 0 | 0 | 0 |
