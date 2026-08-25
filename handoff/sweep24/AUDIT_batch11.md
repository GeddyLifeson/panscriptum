# AUDIT — batch 11 (sweep #24)

Files in batch: `src/dashboard.py` (731 lines), `src/zfighters.py` (486), `src/publish.py` (379),
`src/scout.py` (288), `src/hosts.py` (244), `src/audit.py` (178), `src/resonance.py` (150).

All seven files were read in full, top to bottom, via the `Read` tool (not sampled, not
grepped-and-skimmed). Cross-file verification was also done for two known suspects that require
it: `cosmology_graph.py` (to confirm the `pair_shared` cap resonance.py consumes) and `silence.py`
(to confirm what `replace_retry`/`write_json` actually do differently from the hand-rolled writes
found in this batch).

---

## SECRET SCAN (publish.py's public-repo sync) — RESULT: CLEAN, no live secrets found

Per the task brief's security focus, every path `sync_tree()` copies into the public export —
`src/`, `prompts/`, `reference/`, `registry_terminal/`, `handoff/`, plus `CLAUDE.md`, `README.md`,
`config.yaml`, `requirements.txt`, `WATCH.md`, `STATUS.md`, `HANDOFF.md`, `BUGS.md`,
`NEXT_STEPS.md`, `MAINTENANCE.md` — was grepped directly (not the export copy) for:

- The exact key-shape regexes `_scrub()` itself uses (`sk-`, `gsk_`, `AIza`, `github_pat_`,
  `ghp_`, `gho_`, `hf_`, `xai-`, `csk-`, `AKIA...`, PEM private-key headers): **zero matches.**
- Generic `(api_key|token|secret|password|bearer)\s*[:=]\s*"<12+ chars>"` patterns, with
  env-var/placeholder noise filtered out: **zero matches.**
- URLs carrying embedded `user:pass@` credentials: **zero matches.**
- Credential-shaped filenames (`*.env`, `*.pem`, `id_rsa*`, `*credential*`, `*.key`, `*secret*`)
  anywhere under the five copied directories: **none exist.**
- `config.yaml` (read in full): only a `localhost:11434` Ollama host and tuning notes — no
  provider keys.

This matches sweep22/AUDIT_batch11.md's independent prior finding of "zero matches" for the same
check. **No live secret is currently being published.** The structural gap below is about the
absence of a safety net, not a live leak.

---

## `publish.py`

Read in full (379 lines).

### 1. `_scrub()` covers only `state.json`; the bulk `sync_tree()` copy has no content scrubbing at all
**MINOR | doc/code mismatch | VERIFIED**

```python
# publish.py:31-33 (module docstring)
The snapshot is scrubbed as well. It carries bucket names, quota counts, progress numbers and
finding summaries; it carries no keys, and `_scrub` refuses anything credential-shaped even if a
future edit puts one in the state dict by accident.
```
`_scrub()` (line 151) is called from exactly one place: `snapshot()` (line 176), which builds
`docs/state.json`. `sync_tree()` (line 203) copies `src/`, `prompts/`, `reference/`,
`registry_terminal/`, `handoff/`, and `config.yaml` etc. via a plain `shutil.copy2` walk
(line 229) with **zero** content inspection — `SKIP_SUFFIX` (line 142) filters only backup file
*extensions* (`.bak`, `.tmp`, `.presilence`, ...), never file *contents*. The docstring's "it
carries no keys" reads as a claim about the whole export; it is actually a claim about one
generated JSON file inside it. Today's grep found nothing live in the bulk-copied tree (see secret
scan above), so this is a missing safety net rather than an active leak — but the tree that is
git-add -A'd and pushed publicly (line 303) includes every `.py`, `.md`, `.txt`, `.yaml`, `.html`,
`.js` file under five source directories with no equivalent of `_SECRET.sub(...)` ever run over
them. A stray API key pasted into a `handoff/*.md` note, a debug `print()` left in a `src/*.py`
during development, or a captured error string containing a bearer token in a prompt file would
all sail through untouched.

### 2. `write()` — fixed temp filename + non-retrying replace on a file two writers share
**MAJOR | two-writer contract violation / concurrency race | VERIFIED**

```python
# publish.py:283-290
def write(state=None):
    os.makedirs(DOCS, exist_ok=True)
    data = state if state is not None else snapshot()
    tmp = STATE_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, STATE_JSON)
    return STATE_JSON
```
`push()`'s own docstring three lines below confirms the operating reality: *"Two writers publish
into this tree (the standing loop and whatever session is working)"* (line 296-298). Yet `write()`
does not call `silence.write_json` or `silence.replace_retry` anywhere in this file (confirmed:
`grep -n "silence\.\(write_json\|replace_retry\)" publish.py` returns nothing). It hand-rolls the
weaker half of that pattern: a **fixed, non-PID-qualified** tmp path (`docs/state.json.tmp`) and a
**bare `os.replace`** with no retry. `silence.write_json`'s own docstring (silence.py:262-265)
names this exact failure mode: *"Two writers of the same path otherwise collide on the temp file
itself, and the loser can replace the winner's target with a partial file."* If the standing loop
and a manually-run `publish.py --push` land in the same window, one process's `open(tmp, "w")` can
truncate the other's in-flight tmp file, and whichever calls `os.replace` second commits a
partial/torn `state.json` — with no retry if Windows denies the rename because a reader (or the
other writer) currently holds the file open, unlike `replace_retry`'s 5-attempt backoff built
specifically for that Windows behavior (silence.py:223-240).

### 3. `render_page()` — no tmp file, no atomicity at all
**MAJOR | two-writer contract violation | VERIFIED (task-flagged line)**

```python
# publish.py:261-263
os.makedirs(DOCS, exist_ok=True)
with open(PAGE, "w", encoding="utf-8") as f:
    f.write(html)
```
Worse than `write()`: this is a direct truncate-then-fill of `docs/index.html` with no temp file
whatsoever. Under the same two-concurrent-publisher scenario documented in `push()`'s docstring, a
`git add -A` (line 303) running in one process could pick up the other process's `index.html`
mid-write. Lower real-world exposure than `state.json` since the rendered page's content is
static markup that only changes when `dashboard.PAGE`'s template changes, but the same class of
bug as finding 2, on the file the audit brief specifically called out at this line.

---

## `dashboard.py`

Read in full (731 lines). This module computes the numbers everything else (including
`publish.py`'s snapshot) treats as ground truth, so its own swallowed-failure and staleness
behavior matters more than the other files in this batch.

### 4. `movement()` — a `standards.check()` crash renders as a real regression, not a computation failure
**MAJOR | swallowed failure fabricates a misleading signal | VERIFIED**

```python
# dashboard.py:420-425 (state())
try:
    import standards as ST
    s["standards"] = ST.check(s)
except Exception:
    silence.note("dashboard.py:standards")
    s["standards"] = []
```
```python
# dashboard.py:332 (movement(), inside `keys = {...}`)
"standards met": sum(1 for x in (now_state.get("standards") or []) if x.get("holds")),
```
If `standards.check()` raises (any bug in that module, a bad import, a malformed input file it
reads), `s["standards"]` becomes `[]` — bitwise identical to "every standard was checked and none
of them are met." `movement()` then diffs this against history: if standards were previously
holding (say 40 of them), this reading shows `"standards met": 0`, and the movement panel's
front-end renders that as `NO CHANGE`/`-40 in N min` in red (`panelMovement`, lines 520-538,
`cls=m.stalled?'down':''`). This is the mirror image of the project's usual "swallowed failure
looks like zero" bug: here a transient computation failure in an unrelated module is amplified
into what reads as an alarming real-world regression on the dashboard whose entire stated purpose
(lines 21-24) is "if a number is wrong here it is wrong there."

### 5. `throughput()` — any DB failure is indistinguishable from "no calls made"
**MINOR-MAJOR | swallowed failure | VERIFIED**

```python
# dashboard.py:150-168
def throughput(minutes=15):
    ...
    out = {"window_min": minutes, "calls": 0, "per_hour": 0, "buckets": []}
    try:
        c = sqlite3.connect(path)
        ...
    except Exception:
        silence.note("dashboard.py:throughput")
    return out
```
A locked, missing, or corrupt `state/cascade_scratch.db` returns the exact same zero-calls dict as
a genuinely quiet 15 minutes. Compare this to the sibling `quotas()` panel two functions above
(lines 143-146), which on its own `except Exception` explicitly appends a visible
`{"bucket": f"quota read failed: {type(e).__name__}", ...}` row — an intentional, working example
of *not* doing this. `throughput()` has no equivalent, so `panelSpend()`'s front end
(lines 598-607) shows the identical "Nothing has called out recently" message whether the router
truly went idle or the metrics DB is broken.

### 6. `watch()` / `library()` — no staleness signal on the files that gate the whole panel
**MINOR | check-that-cannot-fail | VERIFIED (code fact); real-world staleness UNVERIFIED**

`_watch()` (lines 284-305) reads `data/OVERWATCH.json` and `state/failures.json`; `_library()`
(lines 239-277) reads `data/WEAVE_INDEX`-derived host data via `feats.HOSTS`. Unlike the coverage
sub-panel three lines below it in the same function, which explicitly computes and surfaces
`age_h` (lines 260-263: `"age_h": round((time.time() - os.path.getmtime(...)) / 3600, 1)`), none
of `watch()`'s reads carry any age indicator. If the standing Overwatch sweep stalls or crashes
outright, `OVERWATCH.json`'s `open`/`high` finding counts freeze at whatever they last were, and
the dashboard has no way to say so — the exact "a check that cannot fail is never looked at again"
pattern the audit brief calls out, present here specifically because the file's *own* `coverage`
panel shows the fix already exists elsewhere in the same function and simply wasn't applied to
`watch()`.

### 7. `HISTORY` cap (`[-2000:]`) can silently shrink the documented 24h/30min windows under load
**MINOR | Hard Rule 0-adjacent | VERIFIED as code gap; not triggered under the single-viewer case checked**

```python
# dashboard.py:341-342 (movement())
cutoff = time.time() - 24 * 3600
hist = [h for h in hist if h.get("at", 0) > cutoff][-2000:]
```
Retention is nominally 24 hours, but is additionally hard-capped at 2000 rows regardless of how
often `state()`/`movement()` is invoked. Under the one documented consumer (the dashboard's own
5-second `setInterval` poll, one browser tab), 2000 rows ≈ 2.78 hours of headroom above the
30-minute `MOVED_WINDOW_MIN` used for stall detection (line 311), so the "stalled" check does not
currently starve. But nothing bounds how many processes call `/api/state` (or `dashboard.state()`
directly) — a second viewer, a monitoring script, or `publish.py`'s own `snapshot()` (which also
calls `D.state()`, and therefore also calls `movement()`, appending its own row every publish
cycle) all shrink the effective window further. If append frequency ever exceeds roughly one every
0.75s sustained, the 2000-row cap would push the oldest retained sample inside the 30-minute
`MOVED_WINDOW_MIN`, and `stalled` (line 362) would never fire even for a genuinely dead job,
because `older` (line 352) would never contain an entry old enough.

---

## `zfighters.py`

Read in full (486 lines). Almost entirely hand-authored assay data (fine — not evidence-mined,
so Hard Rule 0's "don't sample the corpus" doesn't apply to the roster itself). One code path:

### 8. Goku silently drops from the ranked roster on any load failure
**MINOR | swallowed failure | VERIFIED**

```python
# zfighters.py:434-440
try:
    p = os.path.join(HERE, "data", "REFERENCE_ASSAYS_PRESENCE.json")
    with open(p, encoding="utf-8") as f:
        out["Son Goku"] = json.load(f)["Son Goku"]
except Exception:
    silence.note("zfighters.py:goku")
```
If `REFERENCE_ASSAYS_PRESENCE.json` is missing, malformed, or has dropped the `"Son Goku"` key,
this is caught and swallowed with only a `silence.note` (not printed to console). The ranked
table then prints all fifteen Z Fighters with no Goku row and no visible error — a truncated
roster that looks like a complete run. Output is written via `silence.write_json` (line 478,
correctly atomic and PID-safe — good), so the file-landing half of this is solid; the
data-completeness half is not.

---

## `scout.py`

Read in full (288 lines). Confirms all three suspects named in the audit brief.

### 9. `_ask()` — every failure mode collapses to "the model doesn't know"
**MAJOR | swallowed failure | VERIFIED**

```python
# scout.py:107-114
def _ask(prompt):
    try:
        import read as R
        R.ensure_transport(verbose=False)
        return R._ask(R.config(), SYSTEM, prompt, SCHEMA)
    except Exception:
        silence.note("scout.py:_ask")
        return None
```
`scout()` (line 180) does `got = _ask(prompt)`, then `urls = [... for u in ((got or {}).get("urls")
or [])]`. Whether the model is unreachable, Ollama is down, the JSON schema validation fails, or
the model genuinely returns `{"urls": []}` because it doesn't know — all four produce the same
`urls = []` and the same final output: `{"note": "model proposed nothing"}`. `sweep()`'s console
output (line 254) prints `none <source> <reasons>` identically for a real "nothing found" and an
infrastructure outage.

### 10. `scout()` — read-modify-write race on the shared host map
**MAJOR | concurrency / two-writer race | VERIFIED**

```python
# scout.py:200-206
if kept and register:
    import endpoint as EP
    EP.register(source, kept)
    try:
        import feats as F
        hosts = json.load(open(F.HOSTS, encoding="utf-8"))
        hosts[source] = "pages:" + source
        _land(F.HOSTS, hosts)
```
`_land()` (line 55) itself writes atomically (`tmp` + `silence.replace_retry`, correct), but the
read at line 202 and the write inside `_land` at line 204 are not a single transaction. The
module's own docstring on `_land` says `WIKI_HOSTS.json` "is written from here AND from two call
sites in `hostcheck.py`" (line 58-59) — i.e. multiple processes/call sites are expected to touch
this exact file. If `hostcheck.py` (or a second concurrent `scout.py --source` invocation) writes
`F.HOSTS` between this `json.load` and this `_land` call, that write is silently lost: this
process's in-memory `hosts` dict was built from a now-stale read, and its subsequent atomic write
overwrites the other writer's change with the stale-plus-one-key version. The write mechanism is
race-safe; the read-then-write around it is not.

### 11. `sweep()` — a corrupt `SCOUT.json` permanently discards all prior scout history
**MAJOR | swallowed failure → data loss | VERIFIED**

```python
# scout.py:256-262
try:
    prev = json.load(open(LOG, encoding="utf-8")) if os.path.exists(LOG) else []
except Exception:
    silence.note("scout.py:241")
    prev = []
prev.append({"at": time.strftime("%Y-%m-%d %H:%M"), "results": results})
_land(LOG, prev[-40:], sort_keys=False)
```
If `SCOUT.json` exists but fails to parse (truncated by a crash mid-write, corrupted by the race
in finding 10's sibling pattern, or simply hand-edited badly), `prev` resets to `[]`. The very next
line appends this run's results and lands the file — permanently replacing whatever history
existed with a single new entry. There is no "don't overwrite if the read failed" guard; a
transient read failure becomes an irreversible history loss on the next successful write. Also
note the stale `silence.note` tag at line 259: it says `"scout.py:241"`, which is not this line's
current location — the same "labels baked once by `--instrument`, never move as the file grows"
drift `dashboard.py`'s own comment (lines 386-390) describes as a project-wide hazard for
`failures.json` diagnosability. **COSMETIC** on its own, called out here because it sits right next
to a MAJOR finding it would otherwise help someone find.

### 12. `verify()` reuses the same capped 25-name sample for the model prompt AND the match test
**MINOR | precision / false-negative risk | VERIFIED code fact; false-negative rate not measured**

```python
# scout.py:176, 193
sample = [n for n in names if n and len(n) > 3][:PROBE_NAMES]   # PROBE_NAMES = 25
...
for u in urls:
    r = verify(u, sample)
```
`sample` is the first 25 (by catalog order, not random) sufficiently-long names for the source,
used both to prompt the model and to test whether a fetched page is "about" this source
(`MIN_NAME_HITS = 2` of these same 25, `_names_in`, line 117-133). A genuinely correct page that
happens not to mention any of the specific first 25 catalogued names — while mentioning dozens of
others from the source's full roster — is scored `hits=0` or `hits=1` and rejected as "a real page
about something else" (line 146-149's stated failure category), when it may in fact be exactly the
right page. This is adjacent to, but distinct from, the Hard Rule 0 URL-count cap this file
explicitly fixed elsewhere (line 181-186's "Uncapped 2026-08-24" comment) — that fix uncapped
*which URLs get verified*; this is a fixed-size, non-random *evidence sample* used for the
verification test itself, with no comment explaining why 25 (vs. all catalogued names, or a random
25) was chosen.

---

## `hosts.py`

Read in full (244 lines). Confirms the suspect named in the audit brief and finds a related
Hard Rule 0 violation the brief didn't name.

### 13. `_load()` — any read failure on either shared JSON file resets to empty
**MAJOR | swallowed failure, cascades into finding 14 | VERIFIED**

```python
# hosts.py:44-50
def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        silence.note("hosts.py:load")
        return default
```
Every caller in this file — `primary_host`, `hosts_for`, `add`, `discover`, `coverage` — routes
through this. A corrupt `WIKI_HOSTS.json` (the file the module's own docstring calls "the primary
[that] stays where every other module expects it", line 25) or `SOURCE_HOSTS.json` makes
`coverage()` report `"sources": 0` — the library reads as having zero cataloged hosts, not as
"the host file failed to load" — and feeds directly into the data-loss risk below.

### 14. `add()` — fixed temp filename, no retry, and a read-modify-write race on the shared extra-hosts file
**MAJOR | two-writer contract violation | VERIFIED (task-flagged lines)**

```python
# hosts.py:78-91
def add(source, host, evidence=None, score=None):
    """Record an additional host. Never touches WIKI_HOSTS."""
    if not host or host == primary_host(source):
        return False
    data = _load(EXTRA, {})
    rows = data.setdefault(source, [])
    if any((r.get("host") if isinstance(r, dict) else r) == host for r in rows):
        return False
    rows.append({"host": host, "evidence": evidence, "score": score})
    tmp = EXTRA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    os.replace(tmp, EXTRA)
    return True
```
Same shape as `publish.py`'s finding 2: fixed (non-PID-qualified) `EXTRA + ".tmp"`, bare
`os.replace` with no retry, and — worse than `publish.py` — a read-modify-write of the *entire*
`SOURCE_HOSTS.json` dict (`data = _load(EXTRA, {})` at line 82, mutated, written back at line 90).
Within one `discover()` run this is safe (all `add()` calls happen sequentially on the main thread
after `ThreadPoolExecutor.map` returns each `work()` result — verified at line 180-189, the workers
only compute `keep` lists, they never call `add()` themselves). The exposure is cross-process: two
`hosts.py --discover` invocations, or a `--discover` run overlapping with anything else that writes
`SOURCE_HOSTS.json`, will silently lose whichever update's read was staler — no error, no log
entry, the other writer's addition simply isn't in the file afterward.

### 15. `discover()`/`work()` — candidate hosts are ranked then truncated before verification
**MAJOR | Hard Rule 0 violation | VERIFIED**

```python
# hosts.py:152-157
# `candidates` returns grounded hosts first and speculation after. Probing every
# invented subdomain costs a network round trip each to learn it does not exist, so the
# tail is bounded -- but the bound sits AFTER the evidence, never through it, and what
# it drops is guesses rather than known hosts.
if per_source and len(cands) > per_source:
    cands = cands[:per_source]
```
`per_source` defaults to 24 (`discover(only=None, workers=6, per_source=24)`, line 119). Per the
comment's own description, `cands` arrives already **ranked** (grounded first, speculative after)
— and this line **truncates** that ranking at a fixed cutoff before a single one of the dropped
candidates is ever probed. CLAUDE.md's Hard Rule 0 is explicit that this combination is the
violation, independent of where the cut falls: *"Ranking is still allowed and is encouraged...
Ranking then truncating is not."* This is also, concretely, the exact same anti-pattern
`scout.py` names and fixes in this very batch (scout.py:181-186, *"the cap sat BEFORE
verification... Uncapped 2026-08-24 (Hard Rule 0)"*) — the sibling bug was found and removed in
one file of this project and is still live in this one. A source with more than 24 real candidate
hosts (grounded + speculative combined) never gets the 25th-and-beyond even fetched, let alone
scored.

---

## `audit.py`

Read in full (178 lines). **No MAJOR or MINOR findings.** This module is read-only (no state
writes at all, so the two-writer contract doesn't apply), has no `try/except` anywhere (a
genuine failure crashes loudly rather than being swallowed), and its one enumeration pass
(`audit_invariants`, lines 37-112) iterates every record and every entry with no cap. The only
truncation in the file (`v[:4]` at line 145, `args.sample`/`rng.sample` at lines 152-172) is
console-display sampling on top of counts (`len(v)`, `total_f`) that are always computed over the
complete set — the same "rank/sample for display, never for the underlying count" pattern the
brief's own item 3 endorses. Clean.

---

## `resonance.py`

Read in full (150 lines). Cross-checked against `cosmology_graph.py` (lines 60-90) to verify the
capped-evidence suspect named in the brief.

### 16. `resonance_strength()` re-exposes a capped sample under an unqualified name
**MINOR | naming hazard, not a corruption of the real measure | VERIFIED**

```python
# cosmology_graph.py:86-87 (build_graph)
if len(pair_shared[p]) < 8:
    pair_shared[p].append(name)
...
# cosmology_graph.py:143 (written to disk under --write)
"shared_sample": pair_shared[(a, b)]
```
```python
# resonance.py:144-147
for p in g["pairs"]:
    if {p["a"], p["b"]} == {a, b}:
        return {"weight": p["weight"], "shared": p.get("shared_sample", []),
                "in_resonance": True}
```
Confirmed: `cosmology_graph.py` honestly names the field `shared_sample` and caps it at 8 entries
per pair — the underlying `weight` (the actual relational-strength measure the module's own
docstring calls "the ontology's operational form", lines 133-139) is **not** capped; it sums
`1/log(n+1.5)` over every co-attested entity, uncapped. `resonance_strength()` reads
`shared_sample` and republishes it as `"shared"` — dropping the `_sample` qualifier that signaled
its incompleteness — with no note in the return value or docstring that this list is capped at 8
or what the true co-attestation count is. `weight` remains the honest, complete number; a future
caller who reads `len(result["shared"])` as a proxy for relational strength (a natural mistake
given the renamed, unqualified key) would get a value artificially ceilinged at 8 regardless of
how many entities two sources actually share.

### 17. `resonance_strength()` — no staleness signal on the graph it reads
**MINOR | check-that-cannot-fail | VERIFIED code fact**

```python
# resonance.py:141-149
path = graph_path or os.path.join(HERE, "data/SHARED_STAGE_GRAPH.json")
with open(path, encoding="utf-8") as f:
    g = json.load(f)
for p in g["pairs"]:
    if {p["a"], p["b"]} == {a, b}:
        return {...}
return {"weight": 0.0, "shared": [], "in_resonance": False,
        "note": "no shared furniture at this remove; relation is mediated, not direct"}
```
If `SHARED_STAGE_GRAPH.json` (built by `cosmology_graph.py --write`) hasn't been regenerated since
new source data was added, a pair that now genuinely shares entities still gets the confident,
worded "no shared furniture... relation is mediated, not direct" response — there is no way for a
caller to tell "verified absent" from "not yet reflected in a stale graph." No age check exists
(contrast with `dashboard.py`'s coverage panel, which does surface this for its own file reads).

### 18. `hodge_decompose()` — fixed iteration budget, no convergence check
**MINOR / low-confidence | VERIFIED as a code gap only**

```python
# resonance.py:71-79
for _ in range(600):
    new = {}
    for n in nodes:
        ...
    shift = sum(new.values()) / len(new)
    theta = {n: v - shift for n, v in new.items()}
```
Gauss-Seidel runs exactly 600 iterations regardless of graph size or actual convergence; there is
no residual/delta check and no fallback or warning if 600 iterations were insufficient for a given
graph shape. `eta`/`curl_fraction` are returned as if authoritative either way. Not something this
audit could confirm actually mis-converges on real data (would require running it against the
live graph), but the absence of any convergence verification is a real gap in an otherwise
carefully-reasoned module.

---

## Summary table

| # | Severity | Location | Claim | Status |
|---|----------|----------|-------|--------|
| secret scan | — | src/, prompts/, reference/, registry_terminal/, handoff/, config.yaml | No live secrets found in anything `publish.py` syncs to the public repo | VERIFIED |
| 1 | MINOR | publish.py:31-33 | Docstring "carries no keys" describes only `_scrub()`'d state.json, not the unscrubbed bulk source-tree copy | VERIFIED |
| 2 | MAJOR | publish.py:283-290 | `write()` uses a fixed tmp name + non-retrying `os.replace` on a file two writers share, bypassing `silence.write_json` | VERIFIED |
| 3 | MAJOR | publish.py:261-263 | `render_page()` writes `docs/index.html` with no tmp file/atomicity at all | VERIFIED |
| 4 | MAJOR | dashboard.py:332,420-425 | A `standards.check()` crash renders in `movement()` as a fabricated "-N" regression, not a computation failure | VERIFIED |
| 5 | MINOR-MAJOR | dashboard.py:150-168 | `throughput()` returns the same zero-calls dict for a broken DB as for genuine quiet, unlike sibling `quotas()` | VERIFIED |
| 6 | MINOR | dashboard.py:284-305 | `watch()`/`library()` hosts data carry no staleness/age signal unlike the coverage sub-panel | VERIFIED (code); real staleness UNVERIFIED |
| 7 | MINOR | dashboard.py:341-342 | `HISTORY[-2000:]` cap can shrink retention below the 30-min stall-detection window under higher poll load | VERIFIED (code gap); not triggered in the single-viewer case |
| 8 | MINOR | zfighters.py:434-440 | Goku silently drops from the ranked roster on any load failure of REFERENCE_ASSAYS_PRESENCE.json | VERIFIED |
| 9 | MAJOR | scout.py:107-114 | `_ask()` swallows every exception to `None`, identical to "model doesn't know" | VERIFIED |
| 10 | MAJOR | scout.py:200-206 | Read-modify-write race on WIKI_HOSTS.json across scout.py/hostcheck.py writers | VERIFIED |
| 11 | MAJOR | scout.py:256-262 | Corrupt SCOUT.json → `prev=[]` → permanent history loss on next write | VERIFIED |
| 12 | MINOR | scout.py:176,193 | Same capped 25-name sample used for both the model prompt and the match-verification test | VERIFIED (code); false-negative rate not measured |
| — | COSMETIC | scout.py:259 | Stale `silence.note("scout.py:241")` tag no longer matches its line | VERIFIED |
| 13 | MAJOR | hosts.py:44-50 | `_load()` resets to `{}` on any read failure, indistinguishable from empty | VERIFIED |
| 14 | MAJOR | hosts.py:78-91 | `add()` fixed tmp name + no retry + read-modify-write race on SOURCE_HOSTS.json | VERIFIED |
| 15 | MAJOR | hosts.py:152-157 | Candidate hosts ranked then truncated at `per_source=24` before verification — Hard Rule 0 violation, same anti-pattern scout.py fixed elsewhere in this project | VERIFIED |
| — | CLEAN | audit.py | Read-only, no caps, no swallowed exceptions | VERIFIED |
| 16 | MINOR | resonance.py:144-147 | `shared_sample` (capped at 8, cosmology_graph.py:86-87) re-exposed as unqualified `"shared"`; underlying `weight` is uncapped | VERIFIED |
| 17 | MINOR | resonance.py:141-149 | No staleness check on SHARED_STAGE_GRAPH.json | VERIFIED |
| 18 | MINOR | resonance.py:71-79 | Fixed 600-iteration Gauss-Seidel with no convergence check | VERIFIED (code gap only) |
