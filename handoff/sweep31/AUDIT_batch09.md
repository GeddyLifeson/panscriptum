# SWEEP 31 — BATCH 09 AUDIT

**Modules:** `src/dashboard.py`, `src/weave.py`, `src/endpoint.py`, `src/escalation.py`,
`src/anchors.py`, `src/liveness.py`, `src/resonance.py`

**Total lines read:** 2,712 (dashboard.py 955, weave.py 487, endpoint.py 394, escalation.py 289,
anchors.py 250, liveness.py 188, resonance.py 149) — every line of every listed module was read.

**Method:** full-file reads via `cat -n`/`Read`, cross-checked against `silence.py` (the
project's own two-writer / atomic-write / append primitives) and targeted greps across `src/`
to confirm caller graphs (`pair_weights`/`surprisal_pair_weights`, `liveness` import sites,
`SHARED_STAGE_GRAPH*` producers/consumers) before calling anything dead or mismatched.

This audit is READ-ONLY. No file outside this report was modified. `escalation.py` was audited
for correctness only; every finding below either strengthens or is neutral toward the halt — none
proposes weakening, bypassing, or auto-clearing it, and `clear()` remains callable only by a
human (confirmed: no caller of `clear()` anywhere in `src/` other than `main()`'s `--clear` CLI
branch).

---

## Severity tally

| Severity | Count |
|---|---|
| Blocking | 0 |
| Major | 6 |
| Moderate | 5 |
| Minor | 6 |
| Cosmetic | 4 |
| Informational (cross-module pointer, low confidence) | 1 |
| **Total** | **22** |

---

## dashboard.py

### 1. [MAJOR — VERIFIED] `movement()` races on `state/dashboard_history.json` with no lock — lines 364–384
```python
hist = []
if os.path.exists(HISTORY):
    try:
        with open(HISTORY, encoding="utf-8") as f:
            hist = json.load(f)
        ...
try:
    hist.append(row)
    cutoff = time.time() - 24 * 3600
    hist = [h for h in hist if h.get("at", 0) > cutoff][-2000:]
    tmp = HISTORY + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(hist, f)
    silence.replace_retry(tmp, HISTORY)
```
`Server` (line 924) is a `socketserver.ThreadingTCPServer` — every `GET /api/state` runs in its
own thread, and `state()` calls `movement(s)` unconditionally on every poll. This is a
read-modify-write on a shared file with **no lock anywhere in the module**. Two threads (e.g.
the dashboard open in two browser tabs, or an overlapping `curl`/`--once` invocation) can both
read the same `hist`, each append their own row, and each independently overwrite the file — the
later `os.replace` wins outright and the earlier thread's sample is silently dropped from
history, not merged. On top of the lost-update race, the temp file itself is a **fixed name**
(`HISTORY + ".tmp"`, no PID/thread suffix), so two concurrent writers can also collide on the
temp path itself — exactly the class of hazard `silence.write_json` (silence.py:290–327) was
built to close project-wide ("TWELVE call sites... writing shared data/ and state/ files with a
bare `open(path,'w')`+`json.dump`... reintroduced"). `movement()` doesn't call
`silence.write_json` at all; it hand-rolls the pre-fix pattern.
- **Scenario:** two `/api/state` requests land within the same poll tick; both threads read
  `hist` at length N; both append; both write; the second `os.replace` wins; the first thread's
  sample is gone from `dashboard_history.json` even though it was appended successfully in
  memory.
- **Why it matters:** this is the one panel the module's own docstring calls out as catching
  "every counter flat while every job is up" — a race that silently thins its own history
  degrades exactly the instrument meant to catch silent stalls.

### 2. [MAJOR — VERIFIED] `swallowed` failure breakdown capped at 6, one comment-block away from an explicit "no cap" ruling — line 316
```python
311:    "findings": [...]     # ALL open findings -- a monitoring cap ruled a truncation, 2026-08-24
...
316:    out["swallowed"] = sorted(f.items(), key=lambda kv: -kv[1])[:6]
```
Line 311 explicitly documents that a monitoring cap on `findings` was ruled a truncation and
removed (2026-08-24). Five lines later, `watch()`'s sibling panel (`swallowed`, the breakdown of
`state/failures.json` by failure kind) still does a literal `[:6]` — a cap wearing the exact
shape Hard Rule 0 calls out ("a cap wearing a threshold's or schedule's clothing still counts").
`swallowed_total` (the sum) is not truncated, but any failure kind beyond the top 6 by raw count
is invisible on the dashboard — including a newly-emerging failure class that hasn't yet grown
large enough to crack the top 6, which is precisely the case a monitoring panel exists to catch
early.

### 3. [MINOR — VERIFIED] stated 24h retention vs. actual ~2.7h retention — line 377
`hist = [h for h in hist if h.get("at", 0) > cutoff][-2000:]` with `cutoff = time.time() - 24 *
3600`. At the page's own 5-second poll interval (`setInterval(tick,5000)`, line 893) a full day
produces ~17,280 samples; the hard `[-2000:]` slice caps actual retention to roughly the most
recent 2.7 hours, well short of the 24h the `cutoff` variable implies. This is operational
telemetry, not corpus content, so it's a softer case than a roster truncation, but the stated and
actual retention windows disagree by almost an order of magnitude.

### 4. [COSMETIC] Observed-but-generic exception handling
`_num()` (70–75), `_tail_match()` (78–96), `quotas()`, `throughput()`, `library()`, `watch()`,
`metrics()`, `safety()` all use `except Exception: silence.note(...); return <default>`. Every
one of these calls `silence.note`, so per the project's own `silence.py` audit discipline these
are *observed*, not silent-swallow violations — listed for completeness only, no action needed.

---

## weave.py

### 5. [MODERATE — VERIFIED] a failed `pipeline` import silently halves the mechanics gate — lines 187–191
```python
try:
    from pipeline import _STATBLOCK
except Exception:
    silence.note("weave.py:187")
    _STATBLOCK = None
```
The docstring for `filtered_index()` (176–186) says the second exclusion gate "reuses
`pipeline._STATBLOCK`... One detector, two callers." But this `except Exception` catches *any*
failure importing `pipeline` — not just a missing symbol — including a transitive import error
anywhere inside that (large) module. If it fails, `_STATBLOCK is not None` is `False` for the
rest of the run, and the STATBLOCK half of the mechanics filter silently does nothing while the
`_MECHANIC` regex and `_RULES_VOICE` window continue to look like the full, documented two-gate
system. It is logged (`silence.note`), so it's not fully invisible in the ledger, but nothing in
the console report or the written `RESOLVED_ENTITIES.json` signals that the gate degraded for
that run.

### 6. [MODERATE — VERIFIED] entity/mechanic classification only inspects the first 300–400 characters of a description — lines 196–198
```python
if (_MECHANIC.match(nm)
        or (_STATBLOCK is not None and _STATBLOCK.search(desc[:400]))
        or _RULES_VOICE.search(desc[:300])):
    dropped += 1
    continue
```
This directly gates whether an entity is *included at all* in `RESOLVED_ENTITIES.json` — unlike
the console-only truncations below, this is a real corpus-membership decision made from a
truncated window. A genuine entity whose narrative description happens to contain rules-voice
phrasing within its first ~300 characters (e.g. flavor text that quotes an ability by name early)
would be wrongly classified as a mechanic and dropped; conversely genuine rules text with an
unusually long narrative preamble slips the exclusion past the window. `desc` is read once and
sliced twice with two different, un-explained cutoffs (400 vs 300).

### 7. [COSMETIC — VERIFIED] print-only truncations in `main()`'s console report
`multi[:12]` (446), `g[:4]`/`x[:26]` (447), `sorted(...)[:8]` (458), `v['attestations'][:3]`
(460), `byk.most_common(6)` (464), `names[k][:34]` (434). None of these touch the written
outputs: `CONTINUITY_GROUPS.json`, `RESOLVED_ENTITIES.json`, and `SHARED_STAGE_GRAPH_IDF.json`
all get the full, uncapped data per the explicit "NO CAP" comments at 170–172 and 217–225.
Flagged per the audit's literal instruction to report every `[:N]` pattern; no data-loss
consequence.

### 8. [MINOR — VERIFIED] `pair_weights()` / `null_threshold()` are dead code beside the live surprisal path
Grep confirms every real caller (`src/pipeline.py:1836`, `src/tiers.py:199`) uses
`surprisal_pair_weights`, not `pair_weights` (156–173, IDF-weighted). `null_threshold` (249–273,
also IDF-based) has no caller either. `main()`'s own `idf, N = idf_table(index)[1,3]` values
(line 428) are likewise computed and never used again once `sur`/`surprisal_pair_weights` take
over two lines later. Not a bug, but exactly the drift-risk `liveness.py`'s own docstring warns
about: a formula frozen beside the one that actually runs.

---

## endpoint.py

### 9. [MAJOR — VERIFIED] `_save()` writes the shared endpoint cache with a fixed-name temp file and a bare `os.replace` — lines 83–94
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
This is the two-writer-contract violation the task specifically asked to look for: `CACHE`
(`data/ENDPOINTS.json`) is a shared cache written directly, not via `silence.write_json`.
Two defects stack here:
1. **Fixed temp name.** `silence.write_json`'s own docstring (silence.py:290–309) explicitly
   describes fixing this exact class of bug project-wide ("THE TMP NAME CARRIES PID AND THREAD,
   which the older hand-rolled `path + '.tmp'` sites did not. Two writers of the same path
   otherwise collide on the temp file itself"). `_save()` still uses the pre-fix pattern.
   `register()`, 270 lines below in this SAME file, was explicitly rewritten to use
   `silence.write_json` for exactly this reason ("a shared `PAGES_FILE + '.tmp'` is the
   collision m100 retired repo-wide") — the fix landed in the file but not in `_save()`.
2. **Bare `os.replace`, not `silence.replace_retry`.** No retry on Windows `PermissionError`,
   which `silence.replace_retry`'s own docstring says is a real, measured failure for this
   project's state files ("this project's state files all have readers on their own clocks...
   One such collision took an assay worker down mid-batch (2026-08-23, WinError 5)").
- **Scenario:** the module's own docstring says this cache is written from "every process that
  probes an endpoint" (register()'s docstring, echoed by `detect()`'s own design). Two
  concurrently-running probing processes hit `_save()` near-simultaneously for different hosts;
  their temp files collide, or a same-moment Windows rename denial is only logged (not retried),
  and the process's newly-learned host mode is silently dropped — the probe has to be re-paid
  next time, against the module's own stated goal ("the probe cost is paid once per host per
  project, not per request").

### 10. [MAJOR — VERIFIED] `fetch_html()` regressed to the exact swallowed-failure shape `fetch_raw()` was rewritten to fix — lines 327–334
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
Forty lines above, `fetch_raw()`'s handler (206–224) was explicitly rewritten with a long
comment explaining why lumping every `HTTPError` together is wrong: "A REFUSAL IS NOT AN
ABSENCE... a 403, a 429 or a 500 reached the caller as the exact same answer a genuine 404
gives... 404/410 are the only statuses that actually mean 'not here'." `fetch_html()` — added
later, for the HTML-mode homebrew sources described in the file's own trailing `mode: html`
section — never got that fix: every exception, including `HTTPError` with any code, timeout, or
DNS failure, funnels into one tag (`endpoint.py:fetch_html`) and one return value (`None`),
identical to a genuinely empty page. This is the same class the task flagged endpoint.py for
(`fetch_raw-absent:HTTPError`), reintroduced in the sibling function three functions later in the
same file.

### 11. [MODERATE — VERIFIED] a short-but-real page is silently discarded as if it failed — line 334
`text if len(text) > 400 else None`. A genuinely fetched, genuinely valid homebrew stub page
whose extracted text is ≤400 characters is returned as `None` — indistinguishable from a network
failure to the caller, and not logged under any distinct tag (it doesn't go through the `except`
branch at all, so nothing records that content existed but was filtered out for length). This is
the reverse of "transport failure filed as absence": here a real result is filed as an absence.

### 12. [MODERATE — VERIFIED] `source_pages()` collapses "absent" and "unreadable" — the exact distinction `register()` was rewritten to enforce — lines 346–353
```python
def source_pages(source):
    try:
        with open(PAGES_FILE, encoding="utf-8") as f:
            return (json.load(f) or {}).get(source) or []
    except Exception:
        silence.note("endpoint.py:source_pages")
        return []
```
`register()`, immediately below (356–393), has an entire docstring devoted to this exact
distinction: "the file is ABSENT -> `{}` is the truth, and writing it is correct; the file is
UNREADABLE -> we know nothing, and the only safe act is to not write." `source_pages()` is the
read-side counterpart and makes no such distinction: `FileNotFoundError` and any other read
failure (a torn concurrent write, a lock held by another writer — both explicitly named as
observed hazards elsewhere in this project) return the identical `[]`. For an HTML-mode source
(no wiki, cited only through registered pages per this module's own design), a transient read
failure at the wrong moment makes a source with real registered pages look permanently uncitable
for that call.

---

## escalation.py
*(audited for correctness only; both findings below strengthen the audit trail, neither weakens
the halt; `clear()` remains human-only — confirmed no in-tree caller besides the CLI)*

### 13. [MAJOR — VERIFIED] `_append()` uses the exact buffered-write pattern `silence.append_line` was built to replace — lines 97–106
```python
def _append(path, rec):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True
    except Exception:
        silence.note("escalation.py:log")
        return False
```
This writes `state/escalation.log` (the janitor rung — "the lowest log always holds the whole
story") and every per-source `state/escalations/<src>.log`. `silence.py`'s own `append_line()`
(silence.py:187–220) exists specifically because this pattern corrupts under concurrent writers:
"Five live processes append to `state/model_metrics.jsonl`... using `open(path,'a')` plus
`f.write(...)`, which is a BUFFERED write: Python may split one line into several underlying
writes, and two processes interleaving mid-line produce a row that parses as neither. Measured
2026-08-24: 5 corrupt lines." `escalation.py` does not call `silence.append_line` anywhere; it
hand-rolls the vulnerable version.
- **Scenario:** two pipeline workers (this project runs multi-core by design) escalate within
  the same buffer-flush window; the interleaved write can land a line neither JSON parser reads
  as either record, silently corrupting one entry in the log whose entire purpose is being the
  complete, trustworthy record beneath every other rung.

### 14. [MAJOR — VERIFIED] `_raise_halt()` has no lock, and can lose a concurrently-detected fault instead of corroborating it — lines 154–183
`escalation.py` defines no `threading.Lock` anywhere in the file (unlike `endpoint.py`, which
guards its far-less-critical cache with `_LOCK`). `_raise_halt()`:
```python
cur = _read_halt_raw()
if isinstance(cur, dict) and not cur.get("cleared", False):
    cur.setdefault("also", []).append(brief(rec, OWNER))
    payload = cur
else:
    payload = {... "also": []}
...
tmp = HALT_FILE + ".tmp"          # fixed name, no PID/thread suffix
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=1, ensure_ascii=False)
silence.replace_retry(tmp, HALT_FILE)
```
If two processes independently reach an OWNER-level fault at close to the same moment, both can
read `cur` as absent/cleared before either has written, both build independent "first fault"
payloads, and both race on the same fixed `HALT_FILE + ".tmp"` path — whichever `os.replace`
lands last wins outright. The loser's fault is not appended to `"also"`; it is discarded, because
neither process ever saw the other's write. This doesn't defeat the halt (the library still ends
up halted; `assert_clear()` still raises on whatever payload won), but it directly contradicts
the function's own documented guarantee — "the FIRST thing that went wrong is the one a person
needs to see, and a later, louder symptom must not bury it" — because a race can bury the first
fault under whichever process happened to write second, with no record that a second one ever
happened.

### 15. [MINOR] `_append_log`'s `rec.get("level", JANITOR)` default is currently unreachable
Line 123: both callers of `_append_log` (`escalate()` at 135 and `clear()` at 247) always set
`rec["level"]` before calling it, so the `JANITOR` fallback never fires today. Harmless
defensive code; noted only for completeness.

---

## anchors.py

### 16. [MINOR — HYPOTHESIS] the invariant-check `order` list contradicts its own anchor-tier assignments — lines 92–172, 215–232
```python
order = ["The Skate Guy", "A Sword", "Yggdrasil", "Goku", "The Seat of the Creator"]
```
`Yggdrasil` is anchored `"M6"` (line 153) and `Goku` is anchored `"M5"` (line 93) in the same
file's `ANCHORS` dict, yet `order` places Yggdrasil *before* Goku in what is meant to be an
ascending floor-to-ceiling sequence. Since `M6 > M5`, a correctly-calibrated assay should score
Yggdrasil higher than Goku — which is exactly what the run-#26 measurement the file itself
reports found (`Goku 5.42` sits below `Yggdrasil 6.18`, comment at 245–248) — yet the script
treats that as an "INVARIANT VIOLATED" finding rather than the `order` list simply having Goku
and Yggdrasil transposed relative to its own M-tier assignments. The file's own trailing comment
explicitly punts this to the owner as "an instrument question... not something this script may
paper over," and the script does correctly exit 1 on it rather than hide it — so nothing is
silently lost here — but the `order` list's internal inconsistency with `ANCHORS`' own tier
assignments is worth the owner's attention specifically, separate from the deeper assay question.

---

## liveness.py

### 17. [MODERATE — VERIFIED] the DEAD-function detector cannot see self-recursive or mutually-recursive dead code — line 114, `used` built at 92–99
```python
for name, t in trees.items():
    for node in ast.walk(t):
        if isinstance(node, ast.Name):
            used.add(node.id)
        ...
if fn not in used:
    dead.append(...)
```
`used` is built by walking every module's WHOLE tree, including each function's own body. A
function that calls only itself (`def foo(): return foo()`) with no external caller anywhere in
`src/` adds its own name to `used` via that self-call, and is therefore never flagged DEAD, even
though nothing outside it ever invokes it — the same is true for two functions that call only
each other. This is a real blind spot in the one detector whose entire job is finding code that
never runs, and — unlike the TAUTOLOGY pass, whose SYNTACTIC-vs-SEMANTIC limit is explicitly
documented in the module's own docstring (lines 32–38) — this DEAD-detection gap is not
mentioned anywhere in the file's otherwise-careful self-documentation of its own limits.

### 18. [MINOR — VERIFIED] the PHANTOM detector's `defined` set is module-wide, not scope-aware — lines 131, 135–153
`defined` pools every function's local `Store`-context names, parameters, and imports from the
ENTIRE module into one flat set before checking each `if` guard against it. A name that is
genuinely undefined in the specific scope where it's used in a guard is still excused as
"defined" if it happens to be a local variable, loop variable, or parameter in a *different*
function elsewhere in the same file. This produces false negatives whenever an undefined-guard
bug happens to collide with an unrelated same-named local — a narrower instance of the same
"erring toward it is used" tradeoff the docstring explicitly accepts and names for the DEAD pass
(comment at line 91) but never discloses for PHANTOM.

### 19. [COSMETIC — VERIFIED] `dir(__builtins__)` behaves differently depending on import context — line 131
```python
defined = set(dir(__builtins__)) | set(EXEMPT)
```
Confirmed via grep that `liveness.py` is imported as a library, not only run as `__main__`:
`src/drill.py:812–813,856–857` do `import liveness; liveness.scan()`. In a non-`__main__`
module, CPython's `__builtins__` is the builtins **dict**, not the `builtins` module, so
`dir(__builtins__)` there returns dict methods (`keys`, `values`, `items`, `get`, `pop`,
`update`, `copy`, `clear`, `setdefault`, `fromkeys`), not real builtin names. The following line
(146–147, `import builtins; defined |= set(dir(builtins))`) does correctly add every real builtin
regardless of context, so no genuine builtin is ever missing from `defined` — but when `scan()`
runs via `drill.py`'s import path, those ~9 dict-method names still leak into `defined` and would
silently excuse a genuinely-undefined `if keys:` / `if get:` / `if update:` guard from PHANTOM
detection in any scanned module, purely as an accident of this quirk.

---

## resonance.py

### 20. [MINOR — VERIFIED] `hodge_decompose()` raises `ZeroDivisionError` on empty input instead of degrading gracefully — lines 62–79, contrast with line 88
```python
nodes = sorted({n for e in edges for n in e})
theta = {n: 0.0 for n in nodes}
...
for _ in range(600):
    new = {}
    for n in nodes:
        ...
    shift = sum(new.values()) / len(new)     # len(new) == 0 if `edges` is empty
```
If `edges` is `{}`, `nodes` is empty and `new` is empty every iteration; `len(new)` is 0 and the
division raises on the very first iteration. Two lines further down, the analogous division is
explicitly guarded — `eta = (grad_sq / total) if total > 0 else 1.0` (line 88) — showing the
author is aware of the zero-denominator case in this same function, just not for this earlier
division. Not confirmed from this batch whether any current caller ever passes empty edges (the
callers live outside this batch's modules), so this is a real but possibly-unreached edge case.

### 21. [COSMETIC — VERIFIED] `examples` capped at 5 in `incomparability_rate()` — lines 118–128
`if len(examples) < 5: examples.append((a, b))`. The measured quantities themselves (`total`,
`inc`, `rate`) are computed over the full `itertools.combinations` set, uncapped; only the
illustrative `examples` list returned alongside them is capped. Flagged per the audit's literal
instruction to report every `< N` pattern; functionally a labeled sample field, not a truncation
of the measured statistic.

### 22. [INFORMATIONAL — LOW CONFIDENCE, cross-module pointer] `resonance_strength()`'s default graph file may not be the corrected one — line 141
```python
path = graph_path or os.path.join(HERE, "data/SHARED_STAGE_GRAPH.json")
```
Grep confirms `data/SHARED_STAGE_GRAPH.json` (no `_IDF` suffix) is written by
`src/cosmology_graph.py` (`OUT = .../SHARED_STAGE_GRAPH.json`, not in this batch), and is
distinct from weave.py's `SHARED_STAGE_GRAPH_IDF.json`. weave.py's own docstring (lines 30–45)
describes the pre-fix `SHARED_STAGE_GRAPH` methodology — "counted shared names raw" — as
producing clearly wrong links (Greek/Roman myth fused through a Weyland-Yutani planetary
designation, two D&D books tied through stat names). This batch did not read
`cosmology_graph.py`, so it is unconfirmed whether that module has since adopted the same
IDF/surprisal correction weave.py applied. If it hasn't, `resonance_strength()` — and, per its
own docstring, everything reading resonance for "propagation delay, cosmological clustering" —
is built on the graph weave.py's own docstring calls out as flawed. Flagged as a pointer for
whichever batch covers `cosmology_graph.py` and `propagation.py`, not a confirmed defect in
`resonance.py` itself.
