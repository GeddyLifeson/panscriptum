# SWEEP31 — BATCH 14 AUDIT

Modules: `src/rigor.py` (865 lines), `src/publish.py` (560 lines), `src/rosetta.py` (416 lines),
`src/scout.py` (287 lines), `src/grounding.py` (245 lines), `src/profile.py` (201 lines),
`src/cachekey.py` (135 lines).

Total lines read: **2,709** (every line of all seven files, in full).

Repo: `C:\Users\imarl\panscriptum-library-kit`. Read-only audit; no files edited, `publish.py` not
executed. Regex/behavioral claims below marked VERIFIED were checked with `python -c` snippets
against the actual imported module (read-only, no writes) — commands are reproduced inline.

---

## BLOCKING

### B1. `publish.py` main(): the credential-scanner refusal is swallowed and the process still exits 0

**File:line:** `src/publish.py:220-237` (loop), specifically:
```python
    while True:
        try:
            n = sync_tree()
            render_page()
            write()
            print(f"synced {n} files, wrote docs/state.json  ->  {SITE}")
            if a.push:
                print("pushed" if push() else "no change to push")
        except Exception as e:
            silence.note("publish.py:main")
            print(f"publish failed: {type(e).__name__}: {str(e)[:180]}")
        if not a.loop:
            return 0
        time.sleep(a.loop * 60)
```
**Why it is wrong:** `push()` raises `RuntimeError("PUBLISH REFUSED ...")` when `scan_for_secrets`
finds a credential-shaped value staged for the public repo (`src/publish.py:150-155`, the exact
mechanism the task named). That exception is caught by the bare `except Exception` above, logged
with `silence.note` + a `print`, and then — because `a.loop` defaults to `0` — execution falls
through to `if not a.loop: return 0` **unconditionally**, regardless of whether the `try` block
raised. A single-shot `python publish.py --push` run that gets its push refused for a live
credential in the tree still exits with status 0.
**Failure scenario:** any automation, scheduled task, or supervisor script that gates on
`publish.py`'s exit code (the normal way to detect "did the halt fire") sees success and moves on.
The one step in the whole project explicitly documented as "IRREVERSIBLE and OUTWARD-FACING"
(`src/publish.py:128-134`) has its refusal reported only as ignorable stdout text.
**Severity:** blocking. **Confidence:** VERIFIED by code reading (control flow is unambiguous;
no need to execute per task instructions).

### B2. `publish.py` credential regex: Bearer tokens containing base64 `+`/`/` are never redacted or detected

**File:line:** `src/publish.py:33` (the `_SECRET` alternative):
```python
r"(?i:bearer)\s+[A-Za-z0-9_\-\.=]{24,}|"
```
**Why it is wrong:** the character class omits `+` and `/`, the last two characters of the
standard base64 alphabet that real OAuth/API bearer tokens commonly use. `_SECRET_ASSIGN`
(`src/publish.py:44-45`) does not cover this either — it requires the credential-ish *name* to sit
immediately before the value via `name\s*[:=]\s*value`, and `"Authorization: Bearer <token>"` is
not that shape.
**VERIFIED:**
```
>>> P._SECRET.search('Authorization: Bearer abcdEFGH1234+/abcdEFGH1234+/==')
None
>>> P.scrub_text('Authorization: Bearer abcdEFGH1234+/abcdEFGH1234+/==')
'Authorization: Bearer abcdEFGH1234+/abcdEFGH1234+/=='   # unredacted, unchanged
```
**Failure scenario:** a live bearer token pasted into a log excerpt in `HANDOFF.md`/`BUGS.md`
(exactly the scenario Lock Three's own docstring names, `src/publish.py:138-140`) that happens to
contain `+` or `/` sails through all three locks straight to the public repo.
**Severity:** blocking (this is the exact "redaction that misses a real credential shape" the task
asked to find). **Confidence:** VERIFIED.

### B3. `publish.py` credential regex: GitHub `ghu_`/`ghr_` tokens are absent from the vendor list; bare-prose leaks pass every lock

**File:line:** `src/publish.py:17-19`, the GitHub-token alternatives:
```python
r"github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|"
r"ghs_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}|"
```
**Why it is wrong:** covers `github_pat_`, `ghp_` (classic PAT), `gho_` (OAuth), `ghs_` (server-to-
server), but omits `ghu_` (GitHub App user-to-server token) and `ghr_` (GitHub App refresh token) —
both real, current GitHub token prefixes. The module's own header comment
(`src/publish.py:10-15`) says the widening pass was meant to close exactly this class of gap.
**VERIFIED:**
```
>>> P._SECRET.search('ghu_' + 'a'*36)
None
>>> P.scrub_text('a bare github app token pasted in prose: ghu_abcdefghijklmnopqrstuvwxyz1234567890 is live')
'a bare github app token pasted in prose: ghu_abcdefghijklmnopqrstuvwxyz1234567890 is live'   # unredacted
```
When the same string appears in `name: value`/`name=value` shape (e.g. `GITHUB_TOKEN=ghu_...`),
`_SECRET_ASSIGN` does catch it — but a token quoted in free prose (a pasted API response, a log
line) is not in that shape and is invisible to both locks and to `scan_for_secrets`.
**Severity:** blocking. **Confidence:** VERIFIED.

### B4. `publish.py scan_for_secrets()`: files over 2MB are skipped entirely, exempting exactly the free-text files Lock Three exists for

**File:line:** `src/publish.py:133,151-152`:
```python
def scan_for_secrets(root, max_bytes=2_000_000):
    ...
    if os.path.getsize(p) > max_bytes:
        continue
```
**Why it is wrong:** Lock Three's own docstring (`src/publish.py:134-142`) says its job is to read
"what is about to be PUBLISHED" because a wholesale-copied file "never passes through `_scrub` at
all" — "a log excerpt pasted into HANDOFF.md, a provider error quoted in BUGS.md" is the named
threat model. `handoff/` is one of the four directories copied wholesale into the export
(`COPY_DIRS`, `src/publish.py:133`), and this very sweep's own audit reports land under
`handoff/sweep31/`. A credential pasted into any staged file larger than 2MB is silently exempted
from the only lock that inspects wholesale-copied files at all — the size cap creates a blind spot
in precisely the surface the lock was built to cover.
**Failure scenario:** a large HANDOFF/BUGS/log file (or a big multi-batch sweep report, plausibly
several MB once several agents' full audits are concatenated) that happens to carry a pasted
credential is pushed to the public repo unscanned, unredacted, with all three locks silent.
**Severity:** blocking. **Confidence:** VERIFIED by code reading (unconditional `continue`, no
fallback partial-scan of the first N bytes).

---

## MAJOR

### M1. `grounding.py`: `classify_text`'s default `top=3` truncates the ranking BEFORE the confidence denominator is summed, inflating every reported confidence and hiding runner-ups

**File:line:** `src/grounding.py:112-117` (`classify_text`), used by `src/grounding.py:162,169-170`
(`classify_source`):
```python
def classify_text(text, top=3):
    scores = collections.Counter()
    for name, spec in GROUNDINGS.items():
        for pat, wt in spec["cues"].items():
            scores[name] += wt * len(re.findall(pat, text, re.I))
    return scores.most_common(top)          # <- top 3 of up to 5 GROUNDINGS
...
    ranked = classify_text(" ".join(parts))          # top=3 default
    ...
    top, score = ranked[0]
    total = sum(s for _, s in ranked) or 1           # summed over the TRUNCATED list
    ...
    "confidence": round(score / total, 3),
    ...
    "runners_up": ranked[1:],                        # at most 2 items, of up to 4 possible
```
**Why it is wrong:** `GROUNDINGS` has 5 keys (`ex_nihilo`, `emanation`, `eternal_cycle`,
`demiurgic`, `immanent`). `classify_text(text)` is called with no `top=` argument, so it silently
drops the two lowest-scoring groundings before returning. `classify_source`'s `total` is then
computed only over the surviving 3, so `confidence = score/total` is systematically inflated
whenever a source scores non-trivially on all five (or even four) grounding types, and
`runners_up` under-reports how contested a cosmogony actually is — `main()`'s "contested
cosmogonies" list (`src/grounding.py:228-233`) filters on `confidence < 0.5`, so this bug can hide
genuinely contested sources from that report by inflating their confidence past the cutoff.
**VERIFIED** (`python -c` against a fabricated text hitting all five types):
```
top=3 (as actually called) -> [('emanation', 30), ('ex_nihilo', 12), ('eternal_cycle', 12)]
top=99 (uncapped)          -> [('emanation', 30), ('ex_nihilo', 12), ('eternal_cycle', 12), ('demiurgic', 10), ('immanent', 10)]
sum top3 = 54   sum all = 74
confidence as computed: 30/54 = 0.556   true confidence: 30/74 = 0.405
```
**Failure scenario:** any source whose origin-account text triggers cues from 4-5 grounding types
gets its `confidence` overstated by roughly 20-40% and can be silently excluded from the
"contested" report that exists specifically to flag close calls. Note the module's own §128-147
docstring block is a careful, explicit Hard-Rule-0 fix for a *different* cap (the `cap=`
parameter on `classify_source`) — this second cap, one function up the call chain, was missed by
that same pass.
**Severity:** major. **Confidence:** VERIFIED.

### M2. `publish.py write()`: STATE_JSON bypasses the project's mandated atomic-write helper, in the one module whose own docstring documents two concurrent writers and Windows lock contention

**File:line:** `src/publish.py:107-114`:
```python
def write(state=None):
    os.makedirs(DOCS, exist_ok=True)
    data = state if state is not None else snapshot()
    tmp = STATE_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, STATE_JSON)
    return STATE_JSON
```
**Why it is wrong:** the project's own contract (per this batch's brief, and `silence.py`'s
`write_json`/`replace_retry` docstrings) is that shared state files land only via
`silence.replace_retry`/`silence.write_json` — precisely because a bare `path + ".tmp"` collides
between two writers of the same path, and a bare `os.replace` raises `PermissionError` outright
when a reader holds the Windows handle open, rather than retrying. `publish.py`'s own `push()`
docstring (`src/publish.py:120-124`) states outright: "Two writers publish into this tree (the
standing loop and whatever session is working)" — and the module's top-of-file docstring
(`src/publish.py:22-24`) separately documents Norton intermittently denying writes under this
project directory. `write()` uses neither `silence.replace_retry` (retry on `PermissionError`) nor
a PID/thread-qualified temp name, despite both hazards being independently documented in this same
file.
**Failure scenario:** two publish cycles overlapping (loop + manual run, as the docstring says
happens) both write `STATE_JSON + ".tmp"`; the loser's write corrupts or is silently replaced by
the winner's, or a reader (dashboard fetch, static host) holding `state.json` open at replace time
raises an uncaught `PermissionError` — which (per B1) is then swallowed and reported as a false
success anyway.
**Severity:** major. **Confidence:** VERIFIED by code reading; cross-referenced against
`silence.replace_retry`/`write_json` docstrings in `src/silence.py:263-315`.

### M3. `scout.py _land()`: shared-file temp name is not writer-qualified, reproducing the exact race `silence.write_json` was built to close

**File:line:** `src/scout.py:55-65`:
```python
def _land(path, obj, sort_keys=True):
    """Write a shared artifact whole or not at all -- tmp + `silence.replace_retry`. ..."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=sort_keys)
    silence.replace_retry(tmp, path)
```
**Why it is wrong:** `silence.write_json`'s docstring (`src/silence.py:290-309`, written the same
day as this sweep) names this exact pattern as the bug it fixed project-wide: "THE TMP NAME
CARRIES PID AND THREAD, which the older hand-rolled `path + ".tmp"` sites did not. Two writers of
the same path otherwise collide on the temp file itself, and the loser can replace the winner's
target with a partial file." `_land()` is textually that older, hand-rolled pattern — it calls
`replace_retry` (good, gets the Windows-lock retry) but never migrated to `write_json`, so it still
shares one temp filename across every concurrent writer of `LOG`
(`data/SCOUT.json`), `BLOCKED` (`data/SCOUT_BLOCKED.json`), and the host registry write at
`src/scout.py:200-204`.
**Failure scenario:** two `scout.py` invocations (e.g. a scheduled sweep and a manual
`--source X --dry` run) racing on the same `.tmp` path: writer A opens and starts dumping JSON,
writer B opens the same path (truncating A's partial content), dumps its own object; whichever
process's `replace_retry` fires first can land the OTHER writer's still-in-progress (torn) JSON
onto `path`. `rosetta.py`'s own `--mine`/`--refine` comments (`src/rosetta.py:361-366`) describe
this exact class of accident happening for real in this project on 2026-08-25 and name
`scout.py`/`grounding.py`/`coverage.py` as the three sites the sweep fixed that day — but the fix
recorded there addressed a *different* symptom (raw-mine overwritten by refine); the shared
`.tmp`-name race in `_land()` itself is still present.
**Severity:** major. **Confidence:** VERIFIED by code reading, cross-referenced against
`silence.write_json`'s docstring.

### M4. `scout.py`: `PROBE_NAMES = 25` truncates the name sample used to *verify* a candidate page, not just to prompt the model

**File:line:** `src/scout.py:78,176,193`:
```python
PROBE_NAMES = 25
...
def scout(source, names, register=True):
    sample = [n for n in names if n and len(n) > 3][:PROBE_NAMES]     # <- capped to 25
    prompt = (f"SOURCE: {source}\n"
              f"CATALOGUED UNDER IT: {', '.join(sample[:18])}\n\n"    # <- capped again to 18, for the prompt only
              ...)
    got = _ask(prompt)
    ...
    for u in urls:
        r = verify(u, sample)          # <- the 25-name cap, not the full catalogue, decides pass/fail
```
**Why it is wrong:** `verify()`'s pass/fail test (`MIN_NAME_HITS = 2` catalogued names found on the
page, `src/scout.py:169-171`) is checked against `sample` — the same 25-name-capped list used for
the LLM prompt — rather than against the source's full `names` list. The scout.py module's own
comment two lines above (`src/scout.py:181-186`) explicitly documents fixing an *unrelated*
Hard-Rule-0 cap in this same function ("Uncapped 2026-08-24 (Hard Rule 0)" — the URL-candidate
cap) without noticing this one.
**Failure scenario:** a source with hundreds of catalogued entities (typical for a large wiki) can
have a genuine, correctly-scoped index page rejected by `verify()` because none of the arbitrary
first 25 names (in whatever order `hostless()` produced them) happen to appear on that particular
page — a real hit is scored as "0 catalogued name(s) present" and thrown away, and the source stays
hostless.
**Severity:** major. **Confidence:** VERIFIED by code reading.

---

## MINOR

### N1. `rosetta.py`: `srlimit: "5"` caps every MediaWiki search query to its top 5 hits

**File:line:** `src/rosetta.py:194`:
```python
d = F.api(host, {"action": "query", "list": "search", "srlimit": "5", "srsearch": q})
```
**Why it matters:** `scales_for()` runs ~26 different `SCALE_QUERIES` per wiki, so total coverage
is broader than one query — but each individual query only ever considers the wiki search engine's
top 5 results by its own relevance ranking, silently discarding any genuine scale page ranked 6th
or lower for every query term that would have found it.
**Severity:** minor (mitigated by the many-query fan-out; still a literal Hard-Rule-0 cap).
**Confidence:** VERIFIED by reading; effect size not measured (would need a live wiki fetch, out
of scope for a read-only audit).

### N2. `scout.py sweep()`: scout-run log history is truncated to the last 40 entries on every write

**File:line:** `src/scout.py:262`:
```python
_land(LOG, prev[-40:], sort_keys=False)
```
**Why it matters:** every `sweep()` invocation permanently drops any log entries beyond the most
recent 40, shrinking the recorded history of scouting runs. Written via the correct atomic-write
path (see M3 for that path's own defect), but the retention policy itself is a Hard-Rule-0 cap on
stored data.
**Severity:** minor. **Confidence:** VERIFIED.

### N3. `scout.py sweep()`: a transient/corrupt read of the log file silently discards all prior history, not just the current append

**File:line:** `src/scout.py:256-262`:
```python
    try:
        prev = json.load(open(LOG, encoding="utf-8")) if os.path.exists(LOG) else []
    except Exception:
        silence.note("scout.py:241")
        prev = []
    prev.append({"at": time.strftime("%Y-%m-%d %H:%M"), "results": results})
    _land(LOG, prev[-40:], sort_keys=False)
```
**Why it is wrong:** any exception on read — a transient Windows lock/AV scan mid-read, a
half-written file left by a racing writer (see M3), a decode error — is caught by the same bare
`except Exception` that also covers "file genuinely does not exist yet," and both are treated
identically: `prev = []`. The very next line then writes `LOG` containing *only* the current run's
result, permanently overwriting whatever history existed before the transient failure. This is a
swallowed failure that is indistinguishable from "no history yet" (Lens 2) and, combined with M3's
race, means a losing writer's transient read failure can wipe the shared log outright.
**Severity:** minor-to-major (log data, not corpus data, but a genuine irreversible loss).
**Confidence:** VERIFIED by code reading.

### N4. `cachekey.py write_path()`: TOCTOU between the existence/ownership check and the caller's actual write

**File:line:** `src/cachekey.py:119-134`:
```python
def write_path(base, host, name):
    nat = natural_path(base, host, name)
    if not os.path.exists(nat):
        return nat
    try:
        with open(nat, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception:
        return nat
    if owns(doc, name):
        return nat
    return disambiguated_path(base, host, name)
```
**Why it matters:** the function only *decides* a path; it does not lock or write. Two concurrent
callers racing to write two different, colliding-by-sanitisation entity names (the exact scenario
this whole module exists to fix — `Magic 8 Ball` vs `Magic 8-Ball`, per the module's own header)
can both call `write_path()` while `nat` does not yet exist, both get told to use `nat`, and
whichever writes second overwrites the first with no ownership check ever having run against the
other's in-flight write. The module's own docstring says the write-side fix exists precisely so
"a colliding pair would [not] overwrite each other forever" — a race here reintroduces exactly
that failure mode once per collision, non-deterministically.
**Severity:** minor (requires a genuine name collision AND a concurrent write, which the module's
own measurement puts at 10 entities across the whole 96,666-entity corpus — but the fix's whole
purpose is defeated when it happens). **Confidence:** HYPOTHESIS (the actual write call sites are
outside this module and were not read as part of this batch; whether callers add their own lock is
unverified).

### N5. `cachekey.py`: `NAME_CAP = 80` / `HOST_CAP = 40` truncation is still live in the sanitiser

**File:line:** `src/cachekey.py:52-53,58,63`:
```python
HOST_CAP = 40
NAME_CAP = 80
...
return _SANITISE.sub("_", host or "")[:HOST_CAP]
...
return _SANITISE.sub("_", name or "")[:NAME_CAP]
```
**Why it matters:** a literal `[:N]` truncation, which the sweep brief asks to be reported
regardless of justification. The module's docstring extensively justifies keeping it: changing it
would rename all 86,288 existing cache files, and `load()`/`owns()` (read-time verification against
the stored, un-truncated `entity` field) is the actual fix for the ambiguity this cap causes.
Recorded here for completeness, not as a new defect — this is a documented, deliberate legacy
compromise with a working mitigation layered on top, not an oversight.
**Severity:** cosmetic/documented. **Confidence:** VERIFIED (present in code); the module's own
argument for keeping it is coherent and was not contradicted by anything found in this audit.

---

## COSMETIC

### C1. `rosetta.py --check`: dead code adds a global attribute that is never defined anywhere in the codebase

**File:line:** `src/rosetta.py:402-404`:
```python
assays = {k: v["result"]["decimal"] + P.__dict__.get("_x", 0)
          for k, v in json.load(open(path, encoding="utf-8")).items()
          if v.get("result") and v["result"].get("decimal") is not None}
```
**Why it matters:** `grep -rn "_x" src/*.py` finds zero definitions of a module-level `_x` in
`pipeline.py` or anywhere else in `src/`. `P.__dict__.get("_x", 0)` therefore always evaluates to
`0` and this term is permanently a no-op — dead code that reads as if some live adjustment is being
applied to the decimal Assay value, misleading a future reader. Harmless today; worth removing or
explaining.
**Severity:** cosmetic. **Confidence:** VERIFIED (`grep` across all of `src/` for `_x` returns no
definitions).

### C2. `publish.py push()`: two very different "nothing happened" states collapse to the same return value

**File:line:** `src/publish.py:157-160` vs `:188-195`:
```python
    porcelain = git("status", "--porcelain")
    if not porcelain:
        return False                      # genuinely nothing changed
    ...
    except RuntimeError as e:
        ...
        print("push held: rebase onto origin/main failed ...", file=sys.stderr)
        return False                      # a commit EXISTS locally but could not be synced
```
Both paths return `False`, and the caller (`src/publish.py:230-231`) prints `"pushed" if push()
else "no change to push"` — so a held commit (real, unpushed work sitting in the export repo)
prints the same "no change to push" as a genuinely clean tree, on stdout. The true reason is
separately printed to stderr in the second case, so this is a display/log-clarity issue, not a
functional bug.
**Severity:** cosmetic. **Confidence:** VERIFIED by code reading.

### C3. `publish.py`: display-only truncations of security/error reporting text

**File:line:** `src/publish.py:148,153` (escalation evidence `leaks[:20]` / refusal message
`leaks[:10]`), `src/publish.py:335` (git error message `[:220]`), `src/publish.py:551`
(`str(e)[:180]` in the main-loop failure print).
**Why it matters:** none of these affect the actual block/refuse decision (`len(leaks)` and the
`if leaks:` gate both use the untruncated list) — they only shorten what a human reads in the
escalation record and log lines. For a mass-leak event (many credential-shaped hits at once), the
owner reviewing the `SECRET_IN_EXPORT` escalation sees only the first 20 of N locations, which
understates the true scope of that specific incident even though the push itself is correctly
blocked either way.
**Severity:** cosmetic. **Confidence:** VERIFIED.

---

## Modules with no findings beyond the above

`src/rigor.py` (865 lines, fully read) is a math/reporting module. It contains extensive
self-documented history of *previously* fixed Hard-Rule-0 and correctness bugs (the faculty-weight
zero, the cumulative-vs-per-band bit value, the Bradley-Terry Ford's-condition refusal, the ranked-
never-truncated `load_bearing` field) and no bare `except` blocks at all. No new findings were
identified in this file; its one `[:6]`/`[:3]`/`[:4]` slices are all display-only truncations of a
value that is separately returned in full (e.g. `mathematical_resonance()`'s `load_bearing` is
returned untruncated; only the `main()` print statement slices it).

`src/profile.py` was read in full; its two `except Exception: silence.note(...); genres/tiers = {}`
fallbacks (`src/profile.py:128-138`) follow the project's own documented swallow-but-record
convention and were not flagged as new findings — a missing `GENRES.json`/`TIERS.json` degrades
every world to `unclassified`/`classical` rather than crashing, which is recorded via
`silence.note` per the project's stated policy, not silently absorbed.
