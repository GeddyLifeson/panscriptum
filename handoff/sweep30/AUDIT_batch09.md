# AUDIT — batch 09 (sweep30)

Files: `src/dashboard.py`, `src/weave.py`, `src/endpoint.py`, `src/scout.py`, `src/genre.py`,
`src/descending_ladder.py`, `src/catalog.py`. Every line read top to bottom. Read-only —
no repo file edited except this one. No secrets found in any of the seven files.

Method note: several findings below are corroborated against real production evidence in
`state/failures.json` (read-only `cat`), and several are corroborated with runnable
reproductions written to the scratch temp dir
(`C:\Users\imarl\AppData\Local\Temp\claude\...\scratchpad\repro\`), never against repo state.

---

## 1. src/dashboard.py — audited hardest, per instructions

### 1.1 HIGH — `watch()` (:299-320) and `throughput()` (:150-168) initialize their zeros
BEFORE the try, so an unreadable diagnostic renders as a confident all-clear instead of
"UNMEASURED". **REPRODUCED** (both mechanically, by inspection, and against real production
counts).

`_watch()`:
```
out = {"open": 0, "high": 0, "rounds": 0, "findings": [], "broken": []}   # :301
try:
    d = json.load(open(os.path.join(DATA, "OVERWATCH.json"), encoding="utf-8"))
    ...
except Exception:
    silence.note("dashboard.py:watch")
```
If `OVERWATCH.json` is missing/torn/locked, `out` is never touched past its initializer and
the function returns `{"open": 0, "high": 0, ...}` — indistinguishable from "every finding was
fixed or retired." The front-end (`panelWatch`, :867-876) renders this exact case as *"Nothing
open — every finding was fixed or retired when its file changed."* — the confident, wrong
sentence the task description predicted. `state/failures.json` records
`silent:dashboard.py:watch:FileNotFoundError 1` — this has already happened in production.

`throughput()` (:155): `out = {"window_min": minutes, "calls": 0, "per_hour": 0, "buckets": []}`
initialized before the sqlite3 connect/query. If `state/cascade_scratch.db` is absent, locked,
or its schema drifts, the panel renders "0 calls, 0/hour" — identical to a genuinely idle
router. `state/failures.json` records `silent:dashboard.py:throughput:OperationalError 1` —
also already observed live.

**Fix**: both should carry an explicit `"measured": False` (or `None` sentinel per field) set
only on the happy path, and the front-end panels should render "UNMEASURED" rather than a bare
zero when that flag is absent.

### 1.2 HIGH — `movement()` (:329-413): unlocked, un-PID-qualified read-modify-write on
`state/dashboard_history.json`, causing real, currently-active lost updates under concurrent
`/api/state` polling. **REPRODUCED**, both synthetically and against real production counts.

The dashboard's `Server` (:924-926) is a `socketserver.ThreadingTCPServer` — every `GET
/api/state` spawns a new thread, and the page's own JS polls every 5 seconds (:893) — so two
overlapping requests (two open tabs, or a slow request overlapping the next poll) call
`movement()` concurrently. The write path at :374-384:
```
tmp = HISTORY + ".tmp"                      # FIXED name -- no PID/thread qualifier
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(hist, f)
silence.replace_retry(tmp, HISTORY)
```
is exactly the vulnerable shape `silence.write_json`'s own docstring says was found and fixed
project-wide ("Two writers of the same path otherwise collide on the temp file itself, and the
loser can replace the winner's target with a partial file"). `dashboard.py` never adopted that
fix for its own history file — it calls `silence.replace_retry` directly instead of
`silence.write_json`, so the tmp path stays `HISTORY + ".tmp"` for every thread.

Reproduction (`repro/race_history.py`, 40 threads writing through the identical pattern to a
scratch file): **39 of 40 concurrent rows were lost**, most via `FileNotFoundError` from
`os.replace` (`WinError 2`) when one thread's `open(tmp,"w")` raced another's `os.replace`
already consuming the same tmp path. `replace_retry` only retries on `PermissionError`, not
`FileNotFoundError`, so the exception propagates out to `movement()`'s outer `except Exception:
silence.note("dashboard.py:movement"); return []` (:382-384) — the row, and the whole
movement panel for that poll, is silently dropped.

This is corroborated by real production counts in `state/failures.json`:
```
silent:dashboard.py:movement:FileNotFoundError 31    <- the live version of what was reproduced
silent:dashboard.py:movement:JSONDecodeError   82    <- historical; predates the read/write
                                                          isolation fix already visible in the
                                                          current source (:364-373) and cited in
                                                          the file's own comment at :350-363
silent:dashboard.py:movement-corrupt-reset:JSONDecodeError 7  <- current, correctly self-healing
```
The 82-count `JSONDecodeError` tag is the ledger's memory of the OLDER bug the in-file comment
narrates fixing (unified try/except for read+write); that fix is genuinely present in the
current source. The 31-count `FileNotFoundError` under the same `dashboard.py:movement` tag is
a **different, currently live** bug with the same root cause class (fixed shared tmp name), not
yet fixed.

**Fix**: use `silence.write_json(HISTORY, hist)` instead of the hand-rolled tmp+replace_retry,
exactly as `weave.py`, `genre.py`, and `endpoint.py:register()` already do elsewhere in this
batch.

### 1.3 MEDIUM — Hard Rule 0: diagnostic cap on the swallowed-failures panel, :316
```python
out["swallowed"] = sorted(f.items(), key=lambda kv: -kv[1])[:6]
```
This is exactly "ranking, then truncating" — allowed to rank, not allowed to then cut. The
adjacent `findings` list (:308-311) was explicitly de-capped on 2026-08-24 per its own comment
("ALL open findings — a monitoring cap ruled a truncation"), but the `swallowed` list a few
lines below it was not. `out["swallowed_total"]` is computed from the full dict so the total is
honest, but the itemized top-N list — the part a reader actually scans to find which tag is
spiking — silently hides everything past rank 6. Given this same file's own comment established
the precedent that a monitoring cap here counts as the Hard Rule 0 violation, this is the same
class of defect, unfixed.

**Fix**: drop `[:6]`, or if the panel genuinely needs a bounded render, do it in the front-end
JS (which is provably display-only) rather than in the JSON the API serves.

### 1.4 Clean / correctly handled
- The negative-delta "stalled" and "reset" handling in `movement()` (:396-412) is correct and
  well-reasoned (a restart-driven negative delta is explicitly labeled `reset`, not silently
  smoothed).
- `jobs()` (:171-193) fault-isolates the read/roll rows into separate try/excepts as its
  docstring claims — verified, this is not the "one handler for both" shape.
- `safety()` correctly treats a cleared halt's `code`/`what` as history (`last_cleared`) rather
  than a live field once `halted` is false (:481-494) — matches the stated design intent.
- No committed secrets in this file.

---

## 2. src/endpoint.py

### 2.1 HIGH — `_save()` (:83-94) violates the two-writer contract twice, with confirmed real
data loss. **REPRODUCED** synthetically and against real production counts.

```python
def _save():
    with _LOCK:
        if _MEM is None:
            return
        try:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            tmp = CACHE + ".tmp"                 # (a) fixed name, no PID/thread qualifier
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(_MEM, f, indent=1, sort_keys=True)
            os.replace(tmp, CACHE)                # (b) raw os.replace, NOT silence.replace_retry
        except Exception:
            silence.note("endpoint.py:save")
```
(a) `_LOCK` is a `threading.Lock` — it protects nothing across the multiple OS *processes* this
module is actually used from (parallel readers/scouts). A fixed tmp filename shared by every
process racing to persist `data/ENDPOINTS.json` reproduces the exact torn-write hazard
`silence.write_json`'s docstring documents fixing project-wide, PID/thread-qualified tmp names
included. (b) calling `os.replace()` directly instead of `silence.replace_retry()` means a
single Windows `PermissionError` (a reader holding `ENDPOINTS.json` open — which the project's
own `replace_retry` docstring says happens routinely here) drops the entire write with **zero**
retry, where every other writer in this batch that uses `replace_retry` gets 5 attempts with
backoff.

`state/failures.json` confirms this is not theoretical:
```
silent:endpoint.py:save:PermissionError 26
```
26 real, unretried cache-write losses recorded live.

The consequence compounds through `_load()` (:70-80): any read of a torn/corrupted `CACHE`
raises, is caught, and **silently resets the whole in-memory cache to `{}`** — which the next
`_save()` then persists back to disk, discarding every previously-probed host's `MODE_API` /
`MODE_RAW` / `MODE_DEAD` verdict, not just the one write that failed. One torn read erases the
accumulated probe history for however many hundred hosts had been resolved.

**Fix**: route `_save()` through `silence.write_json(CACHE, _MEM, indent=1, sort_keys=True)`,
which fixes both (a) and (b) in one change (it already PID/thread-qualifies its tmp name and
calls `replace_retry` internally).

### 2.2 HIGH — `detect()` (:126-173) swallows every exception from both probe loops
undifferentiated, matching the "~5,500 swallowed HTTPError" figure precisely.
**REPRODUCED against real production counts.**

```python
except Exception:
    silence.note("endpoint.py:detect-api")   # :152 -- any exception, any HTTP code
...
except Exception:
    silence.note("endpoint.py:detect-raw")   # :164 -- any exception, any HTTP code
```
Unlike `fetch_raw()` (see 2.3), `detect()` makes no distinction between "this host genuinely
has no API" (a 404, real information) and "this host, or the network path to it, is refusing
or rate-limiting me right now" (a 403/429/5xx, or the fandom.com-wide connection drop the
file's own comment at :117-123 describes happening "today"). Both land under the same
undifferentiated tag. Given `DEAD_TTL` (:124) only re-probes hosts already marked `MODE_DEAD`,
and marks new dead verdicts from exactly this loop, a transient block can permanently misclass
a host for up to 24h with no way to tell "genuinely absent" from "was rate-limited" from the
ledger.

`state/failures.json`:
```
silent:endpoint.py:detect-api:HTTPError        450
silent:endpoint.py:detect-raw:HTTPError        450
silent:endpoint.py:fetch_raw-absent:HTTPError 4587
```
450 + 450 + 4587 = 5,487 — matching the "~5,500" figure in the task brief almost exactly.

**Fix**: give `detect()` the same code-aware branching `fetch_raw()` already has (2.3) so
403/429/5xx land under a distinct tag from 404/410, and so a transient-refusal verdict does not
silently graduate into a 24-hour `MODE_DEAD` cache entry the way a genuine 404 should.

### 2.3 MEDIUM — `fetch_raw()` (:190-233) records the refusal/absence distinction in the
ledger but the *behavior* the original bug caused is still present: the return value for a
403/429/500 is identical (`None`) to a genuine 404, so callers (`feats.py`, `hostcheck.py`, per
the function's own comment at :213-215) still cannot act differently on a transient refusal
versus a real absence — only the aggregate failure-count ledger can now see the difference.
The docstring frames this as the fix; it is a visibility fix, not a behavior fix, and the
comment slightly overstates what changed ("Same failure family as ... a transient wearing the
face of settled fact" — the transient still wears that face to every caller of `fetch_raw`,
just not to the person later reading `failures.json`).

### 2.4 Clean
- `register()` (:356-394) is a genuinely correct fix of the "unreadable != absent" class of bug
  it describes: raises rather than silently overwriting on an unreadable `SOURCE_PAGES.json`,
  and uses `silence.write_json` for the actual write. No issues found.
- `html_text()` / `fetch_html()` — straightforward, no caps, no swallowed-without-note
  exceptions.
- No committed secrets. `_UA` (:70-71) is a descriptive User-Agent string with a contact email,
  not a credential.

---

## 3. src/scout.py

### 3.1 HIGH — `_land()` (:55-65) shares the exact fixed-tmp-name hazard as 1.2/2.1, and is
used for a genuine cross-process read-modify-write on the shared `WIKI_HOSTS.json`
(`feats.HOSTS`) at :200-204. **REPRODUCED.**

```python
def _land(path, obj, sort_keys=True):
    tmp = path + ".tmp"                        # fixed name, shared by every caller of _land()
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=sort_keys)
    silence.replace_retry(tmp, path)
```
`_land`'s own docstring says it exists to stop `WIKI_HOSTS.json` landing "empty or unparseable"
under a losing writer, and explicitly namechecks that the file "is written from here AND from
two call sites in `hostcheck.py`" — i.e., it documents the multi-writer scenario and then does
not defend against the one hazard that matters under it (the shared tmp filename). The register
path itself is a read-modify-write on the whole file:
```python
hosts = json.load(open(F.HOSTS, encoding="utf-8"))   # :202
hosts[source] = "pages:" + source                     # :203
_land(F.HOSTS, hosts)                                  # :204
```
Two concurrent callers (two `scout.py --source` invocations, or a `sweep()` run overlapping a
`hostcheck.py --adopt` run) each read a stale snapshot, mutate their own key, and the second
writer's `_land()` call silently clobbers the first's addition — a classic lost update, on top
of the tmp-file torn-write risk.

Reproduction (`repro/race_hosts.py`, 30 threads each registering a distinct source through the
identical read-modify-write + `_land` shape): **29 of 30 concurrent registrations were lost**;
the survivor was whichever writer's `os.replace` happened to land last. This is caught by the
surrounding `except Exception: silence.note("scout.py:register-host")` (:205-206) for the
register-host path specifically, so it fails silently rather than crashing — consistent with
the task's "unlocked write" description of :197-206.

**Fix**: route `_land()` through `silence.write_json` (PID/thread-qualified tmp names), and —
separately — the read-modify-write on `WIKI_HOSTS.json` needs either a real lock file or a
retry-on-conflict loop; atomic replace alone does not make a read-then-write-whole-dict
sequence safe against a concurrent writer of a *different* key.

### 3.2 MEDIUM — Hard Rule 0-flavored: `PROBE_NAMES = 25` (:78) truncates the verification
sample to the first 25 catalogued names in **stored (scrape) order, unranked**
(`sample = [n for n in names if n and len(n) > 3][:PROBE_NAMES]`, :176), and that same truncated
`sample` — not the full `names` list — is what `verify()` checks each candidate page against
(:193, `verify(u, sample)`). This is the identical shape Hard Rule 0 names as the canonical
violation ("`roster(limit=600)` returned Dragon Ball A-through-G... Goku fell outside the
window") applied to a keep/reject gate rather than a display list: a real page that covers a
different (but genuine) slice of a large source's roster than whatever the scraper happened to
store first can score below `MIN_NAME_HITS` and be rejected as "not about this material" purely
because of scrape order, not because the page is wrong. Unlike the historical caps this
project has fixed elsewhere (Marvel's 18M characters, 77s to scan), checking a page's text
against every catalogued name instead of 25 is cheap (string search, not a network call) — there
is no performance excuse here, which is exactly the condition Hard Rule 0 calls out ("If
something is genuinely too slow... never a smaller universe" — this isn't even slow).

The `sample[:18]` shown to the model in the prompt (:178) is a separate, lower-severity
instance (LLM context-budget truncation is a more defensible reason to cap than a verification
gate is).

### 3.3 LOW — `sweep()`'s run-history log, :262 (`_land(LOG, prev[-40:], sort_keys=False)`),
caps `data/SCOUT.json` to the 40 most recent sweep runs. This is arguably a legitimate rolling
retention window for a live-status artifact (same pattern as `dashboard.py`'s
`hist[...][-2000:]`), not a truncation of the current sweep's own results (every source scouted
in a given run is recorded; nothing inside one run's `results` list is capped). Flagging per
the instruction to treat any un-obviously-exempt `[:N]` as worth listing — recommend the owner
confirm this specific cap is intentional log rotation and not an unnoticed roster truncation.

### 3.4 Clean
- `verify()` (:136-171) correctly distinguishes 401/403/429 ("declines readers") from other
  HTTP codes and from network failure, and records the reason rather than collapsing all three
  to "not found" — this is the fixed version of the bug pattern found live in `endpoint.py`
  2.1/2.2.
- `_names_in()` (:117-133) correctly word-boundary-anchors and skips names under 4 characters —
  no over-match issue analogous to genre.py's found here.
- No committed secrets (`_UA`, :70-71, is the same descriptive string as endpoint.py's).

---

## 4. src/genre.py

### 4.1 HIGH — cue regexes over-match ordinary English via unanchored `\w*` after a bare
prefix. **REPRODUCED with real English sentences.**

Several cue patterns are `\b(...|token|...)\w*` where `token` is a short common English root;
the `\b` anchors only the *start*, so any ordinary word beginning with that root matches in
full:

| line | pattern (excerpt) | genre | real English matched |
|---|---|---|---|
| :104 | `\b(soldier\|war\|army\|weapon\|mission\|combat)\w*` | military_modern | "warm regards", "the wardrobe creaked", "a warden watched", "warning: high voltage", "she felt warmth" |
| :69 | `\b(demon\|hell\|undead\|necro\|plague\|curse\|dread)\w*` | grimdark | "hello there, friend", "she yelled hello" |
| :88 | `\b(cyber\|netrunner\|megacorp\|implant\|augment\|neural\|hacker\|corpo\|neon\|chrome\|black ?ice)\w*` | cyberpunk | "a corporal gave orders", "the corporate office was busy" |
| :118 | `\b(ninja\|sword saint\|clan\|honor\|spirit)\w*` | eastern | "a clandestine meeting", "Clancy walked in" |

Verified directly against Python's `re` (script output):
```
war    | 'warm regards'              -> matches=['war']
war    | 'the wardrobe creaked'      -> matches=['war']
war    | 'a warden watched'          -> matches=['war']
war    | 'warning: high voltage'     -> matches=['war']
war    | 'she felt warmth'           -> matches=['war']
hell   | 'hello there, friend'       -> matches=['hell']
hell   | 'she yelled hello'          -> matches=['hell']
corpo  | 'a corporal gave orders'    -> matches=['corpo']
corpo  | 'the corporate office was busy' -> matches=['corpo']
clan   | 'a clandestine meeting'     -> matches=['clan']
clan   | 'Clancy walked in'          -> matches=['Clan']
```
"corporal" is a real military rank — meaning ordinary military-fiction prose describing rank
structure silently feeds the *cyberpunk* score instead of (or in addition to) military_modern's
own score. "hello" is close to unavoidable in any dialogue-bearing description. This corrupts
`register` and `world priors` (the module's stated whole purpose, per its own docstring) for
any source whose catalogued descriptions contain these extremely common words, which given
prose-derived entity descriptions is most of them.

**Fix**: anchor the suffix too (`\bhell\b` rather than `\bhell\w*`, or an explicit alternation
of the actual intended forms — `hellish|hells?` etc.) for every short-root cue; keep `\w*` only
where the intent is genuinely to catch inflections of a long, distinctive stem (`xenomorph\w*`,
`grimdark\w*` are fine; `war\w*`, `hell\w*`, `corpo\w*`, `clan\w*` are not).

### 4.2 HIGH — Hard Rule 0: the confidence score is computed against a silently truncated
denominator. **REPRODUCED with realistic mixed-genre text, showing the truncation flips the
low-confidence flag.**

```python
def classify_text(text, top=3):                          # :135, default top=3
    ...
    return scores.most_common(top)                        # only the top 3 of 11 genres

def classify_source(rec, cap=None):
    ...
    ranked = classify_text(" ".join(parts))                # :182, top defaults to 3
    ...
    total = sum(s for _, s in ranked) or 1                  # :187, sums only those 3
    ...
    "confidence": round(score / total, 3),                  # :193
```
`GENRES` has 11 entries (:50-128); `classify_text`'s default keeps only the top 3, and
`classify_source` never overrides it. `total` — the confidence denominator — is therefore the
sum of only the top 3 genres' scores, silently discarding whatever score the 4th, 5th, ... 11th
genres accumulated. This is precisely the lens's called-out case: "a cap on a DIAGNOSTIC hides
the pattern, not just the rows" — here the diagnostic *is* the confidence score, and the pattern
it hides is exactly how mixed the source's genre signal actually is.

Reproduced with a constructed passage carrying real high_fantasy, mythology, military_modern,
*and* superhero vocabulary:
```
top-3 ranked:  [('high_fantasy', 22), ('mythology', 12), ('military_modern', 11)]
all-11 ranked: [('high_fantasy', 22), ('mythology', 12), ('military_modern', 11),
                ('superhero', 10), (...rest, 0)]

confidence using top-3 denominator   (what the code computes): 0.489
confidence using full-11 denominator (the honest figure)      : 0.400
```
`main()`'s own low-confidence flag (:218) uses a `0.45` threshold — this example would be
correctly flagged "genuinely mixed" at the true 0.400 figure but is silently passed through as
confident at the code's actual 0.489. The excluded `superhero:10` evidence is real signal the
regex layer found; it is discarded from the denominator purely by rank position, not relevance.

**Fix**: `classify_text(text, top=len(GENRES))` (or `top=None`) inside `classify_source`, so
`total` sums every genre's score, not just the top 3. `runners_up` (:196, `ranked[1:]`) is fed
by the same truncated list and inherits the same defect for anything using it for display.

### 4.3 Clean
- `classify_source`'s `cap` parameter (:144, :173-177) — the previously-flagged Hard Rule 0
  truncation on the entry-scan itself — is **already fixed**: passing a non-`None` cap now
  raises `SystemExit` with an explanation rather than truncating. Confirmed by reading the
  code; this is closed, not open.
- `main()`'s write path uses `silence.write_json` (:241) with a docstring correctly describing
  why (`profile.py`'s silent-`{}`-on-failed-load fallback). No issue.
- No committed secrets.

---

## 5. src/descending_ladder.py

### 5.1 HIGH — the entire module has zero real callers anywhere in the tree. **REPRODUCED by
exhaustive grep.**

```
grep -rn "import descending_ladder\|from descending_ladder" --include="*.py" .   ->  no results
```
The only other reference to the name anywhere in `src/` is `derivation.py:476`'s
`SCAN_MODULES` list, which does **not** import the module — `derivation.scan_constants()`
(:480-493) opens `descending_ladder.py` as raw text and `ast.parse`s it purely to enumerate
UPPERCASE module-level constants for a documentation/derivation audit. None of
`rung_table()`, `rung_for_length()`, `compton_confinement_energy()`, `density_at_scale()`,
`schwarzschild_radius()`, `shrink_report()`, or `transgression_bits()` is ever invoked from any
other module, launcher, or config in the repo. (One OVERWATCH.json finding on this module,
`compton_confinement_energy`, exists and is already `state: closed` / `verdict: auto-triage
refuted` — that specific finding is not live and is unrelated to the dead-code issue.)

This means the charter-described capability the module's own docstring opens with — addressing
Ant-Man-style sub-Planet descents, and specifically the claim "the omission is silently
load-bearing" for X.2's Reach axis — remains functionally unaddressed in the running pipeline
despite a complete, well-tested-looking implementation existing on disk. `address.py` (per
CLAUDE.md's Hard Rule 4, out of this batch) still only handles the seventeen-rung Ladder; this
module was never wired to it.

### 5.2 MEDIUM — `rung_for_length()` (:85-95): the Planck rung is reachable only at bit-exact
float equality to `PLANCK_LENGTH`. **REPRODUCED numerically.**

```python
def rung_for_length(metres):
    if metres <= 0:
        return None, None
    if metres < PLANCK_LENGTH:
        return FOLD_RUNG, "Below the Fold"        # anything strictly below never reaches the loop
    best = DESCENDING[0]
    for r in DESCENDING:
        if metres <= r[3]:
            best = r
    return best[0], best[2]
```
Because the guard above already diverts every `metres < PLANCK_LENGTH` to `FOLD_RUNG`, the only
way the loop's last row (`Planck`, `r[3] == PLANCK_LENGTH`) can still win the `metres <= r[3]`
comparison is `metres == PLANCK_LENGTH` exactly:
```
metres = PLANCK_LENGTH                    -> (-14, 'Planck')          # exact
metres = nextafter(PLANCK_LENGTH, +inf)   -> (-13, 'Quark-confinement')  # one ULP above
metres = nextafter(PLANCK_LENGTH, 0)      -> (-15, 'Below the Fold')     # one ULP below
```
Any real physical computation feeding this function (as `shrink_report()` does, :129-149) will
essentially never produce the literal constant to the last bit, so the "Planck" rung is a
measure-zero target in practice — every value is silently routed to its neighbor instead. Low
current severity only because of 5.1 (nothing calls this yet); the moment the module is wired
up, this activates immediately and silently.

**Fix**: change the loop condition to `<` against the *next* rung's threshold, or use `<=`
consistently with the Fold guard being `<` rather than `<=` (i.e., make the boundaries
half-open and non-overlapping by construction), or simply special-case
`metres <= PLANCK_LENGTH` alongside the Fold check.

### 5.3 LOW — `rung_for_length()` has no upper guard: for any `metres` larger than
`DESCENDING[0]`'s length (1.0e6 m, "Continental"), the loop never overwrites the `best =
DESCENDING[0]` initializer, so anything bigger than continental scale is silently classified as
"Continental" rather than signaling out-of-range / deferring to the main seventeen-rung Ladder.
Low severity given 5.1, but worth fixing in the same pass if the module is ever activated.

### 5.4 Clean
- The physics itself is sound where checked: `compton_confinement_energy` correctly implements
  `p = ħ/(2r)`, `E = p²/2m` (the OVERWATCH finding alleging otherwise was independently
  triaged and closed as a false positive, confirmed above). `schwarzschild_radius`,
  `density_at_scale`, `transgression_bits` are straightforward and internally consistent with
  their docstrings.
- No committed secrets (module is pure constants/math, no I/O at all).

---

## 6. src/weave.py

### 6.1 MEDIUM — two functions are dead code: `pair_weights()` (:156-173) and the
non-surprisal `null_threshold()` (:249-273). **REPRODUCED by exhaustive grep.**

```
grep -rn "[^_]pair_weights\(" src/*.py | grep -v surprisal_pair_weights   -> only the def line itself
grep -rn "null_threshold\("    src/*.py | grep -v null_threshold_surprisal -> only the def line itself
```
`main()` (:418-483), and the two other real callers of this module elsewhere in the tree
(`pipeline.py:1834-1836`, `tiers.py:197-199`), all call `idf_table()` +
`surprisal_pair_weights()` + `null_threshold_surprisal()` — the name-surprisal-weighted path
the module's own docstring (:124-153) explains was built specifically to fix the "Gordon"
problem (`idf`-only weighting fusing Cowboy Bebop and Thomas the Tank Engine through common
given names). The plain `idf`-weighted `pair_weights()`/`null_threshold()` pair is the exact
superseded, buggier approach the docstring warns against, left callable and importable with no
caller anywhere. Low risk of accidental use only because nothing currently imports it, but it
is exactly the kind of leftover a future edit could reach for by mistake since it sits
undecorated in the same module as the correct path.

**Fix**: delete both, or mark clearly deprecated/`_`-prefixed if kept for reference.

### 6.2 LOW — tautological guard, `name_surprisal()` :152: `if df[t] > 0`. `df` (:141-147) is
built by counting tokens from the exact same `index` this function iterates over
(`for k, hits in index.items(): nm = hits[0].get("name") or k; ... for tok in set(...): df[tok]
+= 1`), so every token in `toks` for any `nm` drawn from that same loop necessarily has
`df[tok] >= 1` already. The guard cannot fail given the function's own construction — it is not
harmful (no incorrect output results either way), but it is a check that cannot fail sitting in
a place a reader would reasonably expect it to matter.

### 6.3 Clean
- All three Hard Rule 0 caps this module's own comments describe fixing (`shared[p]` unbounded
  in `pair_weights`/`surprisal_pair_weights`, :170-172 and :217-225; the `SHARED_STAGE_GRAPH`
  write at :478 keeping the whole `shared_sample` list) are genuinely uncapped in the current
  source — verified by reading, not just trusting the comments.
- `components()`'s complete-linkage clustering (:276-325) is correctly not connected-components;
  the early-exit in `min_cross` (:299-308) is a legitimate optimization, not a correctness
  shortcut.
- Writes at :472-481 correctly use `silence.write_json`.
- No committed secrets.

---

## 7. src/catalog.py

### 7.1 Clean, no findings above LOW
- `cmd_search()` (:70-77) is correctly uncapped — full match list printed, no `[:N]`. This is a
  positive Hard Rule 0 data point in an otherwise cap-heavy batch.
- `cmd_stats()`'s `missing[:30]` (:64) is a legitimate display-only truncation: it prints an
  explicit `"... and {len(missing) - 30} more"` continuation line (:66-67), which is exactly the
  provable-display-only carve-out in the lens — not flagged.
- `load_catalog()` (:34-39) does not catch `json.JSONDecodeError` on a torn/mid-write
  `catalog.json`; a corrupt catalog crashes the CLI with a full traceback rather than a silent
  wrong answer. This is arguably correct per this project's fail-closed philosophy (loud beats
  silent), so not flagged as a defect, just noted — it is the *opposite* of a swallowed
  failure.
- LOW / unverified assumption, not independently confirmable from this batch alone:
  `cmd_stats()`'s `missing` computation (:61) compares `SWEEP_ROLL.json`'s `r["name"]` against
  `catalog.json`'s `v["source_name"]` (:50) as if the two fields are guaranteed to be identical
  strings; the writers of both fields (`manifest_builder.py`, `generate.py`) are outside this
  batch and were not audited here, so this is flagged as a HYPOTHESIS only, not tested.
- No committed secrets.

---

## Summary of severities

- HIGH: 8 (dashboard.py x2 [1.1, 1.2], endpoint.py x2 [2.1, 2.2], scout.py x1 [3.1], genre.py
  x2 [4.1, 4.2], descending_ladder.py x1 [5.1])
- MEDIUM: 5 (dashboard.py x1 [1.3], endpoint.py x1 [2.3], scout.py x1 [3.2],
  descending_ladder.py x1 [5.2], weave.py x1 [6.1])
- LOW: 4 (scout.py x1 [3.3], descending_ladder.py x1 [5.3], weave.py x1 [6.2], catalog.py x1
  [7.1 roll/catalog name-match assumption])

No committed secrets found in any of the seven files.
