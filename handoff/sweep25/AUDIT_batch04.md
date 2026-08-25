# AUDIT batch04 — run #25

Files (every line read, no sampling):
`src/foreman.py` (1264), `src/endpoint.py` (370), `src/entity_match.py` (278),
`src/anchors.py` (232), `src/audit.py` (177), `src/ledger.py` (136). Total 2457 lines.

---

## NEW findings (this run)

### 1. `completeness.py:194-203,259,268` — `host_reachable()` reports EVERY RAW-mode host as
"unreachable" and writes `coverage: 0.0`, because it gates on `endpoint.api_url()`, which is
API-mode-only. **VERIFIED.**

This is a new, concrete consequence of the already-known m106 contract problem
(`endpoint.py:200-233` / NEXT_STEPS item D) that was not previously traced this far. It is not
duplicate ground — the prior citations (`feats.py`, `hostcheck.py`) are call sites that check
`detect()["mode"]` directly and branch correctly on `MODE_RAW`. `completeness.py` does not: it
calls `EP.api_url(host)`, which returns `None` for `MODE_RAW` exactly as it does for `MODE_DEAD`
— `api_url` only ever succeeds for `MODE_API`:

```python
# endpoint.py:176-179
def api_url(host):
    d = detect(host)
    return f"https://{host}{d['path']}" if d["mode"] == MODE_API else None
```

```python
# completeness.py:194-198
base = EP.api_url(host)
if not base:
    _REACH[host] = False
    return False
```

```python
# completeness.py:259-268
if not host_reachable(host):
    ...
    return {"source": src, "host": host, ..., "coverage": 0.0, "probe_failures": len(probes),
            "probes_run": 0,
            "unreliable": ("host unreachable: %s did not answer its API at audit time, "
                           "so no denominator could be requested. Not probed further, "
                           "deliberately -- see completeness.host_reachable." % host)}
```

I confirmed `www.dandwiki.com` — the module's own header calls this host "most of the sources
this library has no host for" (the D&D homebrew shelf) — is live in `data/ENDPOINTS.json` as
`MODE_RAW`, and reproduced the failure directly:

```
python -c "import sys;sys.path.insert(0,'src');import endpoint as EP;
print(EP.detect('www.dandwiki.com')); print(EP.api_url('www.dandwiki.com'))"
->  {'mode': 'raw', 'path': '/w/index.php'}
    None
```

So every dandwiki-hosted source (the D&D homebrew shelf, ~1,335+ entries per `endpoint.py`'s own
comment) is reported by `completeness.py` as `coverage: 0.0` / `"unreliable: host unreachable"`,
even though the host demonstrably answers (raw mode) and `feats.py` successfully reads it every
roll. The message text — "did not answer its API at audit time" — is also literally false: the
host was never even asked, because `api_url` short-circuits before any request is made for a
RAW-mode host. **The fix is one line**: `host_reachable` should accept `MODE_RAW` too (probe via
`EP.raw_url` + a single raw fetch, the same shape it already uses for the API case) rather than
asking `api_url` a question only an API-mode host can answer yes to.

### 2. `foreman.py:801-808` — `_function_source()` bare-name match confirmed by direct
reproduction. **VERIFIED** (previously UNVERIFIED/inferred in run #24 — now proven).

```python
def _function_source(path, symbol):
    ...
    want = symbol.split("(")[0].split(".")[-1].strip()
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and node.name == want:
            ...
            return "".join(lines[start:end]), start, end
```

Reproduced against a two-class file where both `A` and `B` define `compute`:

```
FM._function_source(path, "B.compute")
-> returns A.compute's body (the first match `ast.walk` encounters), not B.compute's.
```

Given a finding whose `symbol` is `"B.compute"`, `attempt_patch()` sends `A.compute`'s source to
the model, applies the model's rewritten `A.compute` in place of whatever `[start:end]` spanned
(which is `A.compute`'s own span, since `_function_source` returns that span) — so in this
specific reproduction the patch actually lands back on `A.compute`, silently leaving `B.compute`
(the function the finding was actually about) untouched and unreported as unfixed. Worse case:
two methods of the *same* name in classes at different points in the file where the AST walk
order doesn't match the intended target at all — the returned `(start, end)` span is always the
first same-named `def` in the file, full stop, regardless of which class the finding names.

### 3. `foreman.py:990-997` — the model-patch write to live `src/*.py` is provably non-atomic,
and a concurrent importer can observe syntactically-broken source mid-write. **VERIFIED by
reproduction.**

```python
os.makedirs(BACKUPS, exist_ok=True)
backup = os.path.join(BACKUPS, f"{module}.{int(time.time())}.py")
shutil.copy2(path, backup)
try:
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    lines[start:end] = [new]
    with open(path, "w", encoding="utf-8") as f:      # <-- truncate-then-fill, no tmp+replace
        f.writelines(lines)
    good, why = _checks_pass(module)
    ...
```

This is a bare `open(path, "w")` + `writelines` on a file that lives in `src/`, importable by
every other job in the supervisor's tree (`read.py`, `feats.py`, `hostcheck.py`, `dashboard.py`,
etc. all run as separate OS processes and `import` shared `src/*.py` modules at arbitrary times).
Simulated the race directly: a background reader polling a file with `open()+compile()` while a
writer truncates and re-fills it in chunks hit `SyntaxError` on **129 of ~300** poll attempts —
i.e. the truncate-then-fill window is wide enough, in practice, for a concurrent reader to see a
half-written file. Applied to this code path: any process that does a fresh `import <module>`
(cold import, or a subprocess like `_checks_pass`'s own `import {module}` check invoked from a
*second, unrelated* foreman round, or literally any of the always-running supervisor jobs
importing the module for the first time in their process) during the ~milliseconds this write
takes can raise `SyntaxError`/`ImportError` and crash that job. The `_checks_pass` import
verification that follows is a same-process, post-write check — it does not protect any other
process racing the write. The fix is the same one already used everywhere else in this file
(`silence.replace_retry` / tmp+`os.replace`), just not applied to the one write that touches
live, multiply-imported source.

### 4. `foreman.py:990` — backup filename granularity confirmed. **UNVERIFIED** (logical, not
reproduced under real contention — matches NEXT_STEPS' existing citation).

`f"{module}.{int(time.time())}.py"` is 1-second-granular; `shutil.copy2` silently overwrites an
existing destination. Two `attempt_patch` calls against the *same module* within the same wall
second (only reachable if two foreman processes overlap, since a single round's `_checks_pass`
takes well over a second per patch) would make the second backup clobber the first, so a
mid-second failure's revert target is gone. Given `round_once`'s own duplicate-supervisor
handling elsewhere in this same file treats "two of my own processes running at once" as a real,
previously-observed failure mode, this is not a hypothetical scenario for this codebase
specifically — but I did not reproduce a live two-process race, so UNVERIFIED.

---

## KNOWN findings (re-verified, kept brief per instructions)

- **`foreman.py:1205`** — `sorted(open_f, key=lambda x: -(x.get("severity")=="high"))[:3]`, no
  rotation; findings ranked 4th+ within a severity tier never get a patch attempt. [KNOWN]
- **`foreman.py:192`** (`scout_hostless`) — `SC.sweep(limit=4)` re-attempts the same top-4
  hostless sources every round. [KNOWN]
- **`endpoint.py:200-233`** (`fetch_raw`) — identical `(t, None)` return for a confirmed
  404/410, an HTTP refusal, an exception, and an HTML error body. Re-confirmed misled callers by
  grepping the whole tree: `feats.py:135,345,436,437,779,781`, `hostcheck.py:95,133,134,135,
  244,245,246`, `completeness.py:194-195` (chain traced further this run, see NEW finding #1
  above — the concrete downstream damage from this call site wasn't previously documented).
  `scout.py` imports `endpoint` (`:153,198`) but does not call `fetch_raw`/`detect` — its own
  `verify()` uses raw `urllib` directly, so it is not misled by this specific contract; not
  adding it to the misled-caller list. [KNOWN, extended]
- **`endpoint.py:83-94` / `:356-370`** — `_save()`/`register()`: unguarded read-modify-write on
  shared `ENDPOINTS.json`/`SOURCE_PAGES.json`, bare `.tmp` name, unretried `os.replace()` (no
  `silence.replace_retry`). `register()`'s write is fully unguarded by any lock at all (unlike
  `_save()`, which at least takes `_LOCK` — a `threading.Lock`, cross-process-useless anyway).
  An uncaught exception in `register()` would propagate out of `scout.py`'s sweep loop. [KNOWN]
- **`anchors.py:215`** — `order = ["The Skate Guy", "A Sword", "Yggdrasil", "Goku", "The Seat of
  the Creator"]` places Yggdrasil (anchor `"M6"`) before Goku (anchor `"M5"`), so the
  monotone-floor-to-ceiling invariant check fires false every run regardless of instrument
  health. Confirmed by reading `ANCHORS["Yggdrasil"]["anchor"] == "M6"` and
  `ANCHORS["Goku"]["anchor"] == "M5"` directly. [KNOWN]
- **`ledger.py:127-133`** (`assay_to_standards`) — at the last band on the ladder,
  `i = LADDER.index(magnitude_band)`, `hi = BAND_EDGES[LADDER[min(i+1, len(LADDER)-1)]]["ruin"]`
  clamps to the same band as `lo`, so `hi == lo` and `joules = exp(log(lo) + ratio*0) = lo`
  regardless of `ruin_score`. This is the owner-ruling item already logged in NEXT_STEPS §2A
  ("`ledger.py:127-133` answers the same question incompatibly [as `assay.py`'s M10 flat-9.9]
  ... `joules` collapses to the floor regardless of `ruin_score`"). Re-confirmed by reading, not
  re-executed (owner ruling, not a repair). [KNOWN]
- **Stale `silence.note()` line tags across `foreman.py`** — several tags no longer match their
  containing line (e.g. `"foreman.py:824"` inside `owner_queue`, whose body is nowhere near line
  824 currently; `"foreman.py:495"`, `"foreman.py:595"`, `"foreman.py:942"`, `"foreman.py:967"`
  are all similarly stale relative to current line numbers). Cosmetic — they still uniquely name
  the call site by string, so failure-ledger triage is not actually broken, just the human
  cross-reference is wrong. [KNOWN, generic mention in NEXT_STEPS §3 confirmed still true]

---

## Things checked and found NOT to be bugs (worth recording so the next run doesn't re-check)

- `foreman.py` MODEL-lane gate order and the six gates named in the module docstring: symbol
  resolution → size cap (400 lines) → model call (local-first, pool fallback) → verdict check →
  shape check (`starts with def`) → `lines_changed` cap (`> MAX_PATCH_LINES`, matches the
  docstring's corrected wording exactly) → no-op check → `regex_touched` refusal → backup →
  write → `_checks_pass` (import, `verify_math` exact-number-read via regex not substring,
  `allsweep --quick` string check) → revert-on-any-failure including on exception. All six gates
  described in the docstring are genuinely present and fire in the order claimed, **except** for
  the "it parses" gate, whose docstring already self-corrects ("The standalone parse gate this
  line promises does not exist; an unparseable patch is caught by the import check below, after
  being written and then reverted") — i.e. the docstring is honest about its own inaccuracy, not
  a new contradiction.
- `restart_ollama()`'s 30-minute rate-limit guard, and its claim about how long the daemon takes
  to come back (up to ~42s: 12s kill-settle + up to 6×5s poll) — both checked against the code
  and both true as stated.
- `_restart_horizon()` / the M15 remedy-honesty requirement — this module already implements
  exactly what the task asked to check for: every kill remedy (`restart_reader`,
  `kill_stalled_job`) reports a per-job, STANDING-vs-not-STANDING-accurate recovery time rather
  than a blanket "restarts next cycle" claim. This is the run-#24 fix for M15, still correct.
- `round_once()`'s `if did and not getattr(fn, "always", False): break` plus the explicit
  `always`-marked remedies (`run_completeness_audit`, `refresh_coverage`) — the docstring-vs-code
  mismatch this shape used to have (a repair succeeding and starving its own re-measurement) is
  already fixed and matches its own extensive inline comment.
- `entity_match.py` — read end to end. `candidates()`/`best()`/`qualifier_compatible()` all
  match their docstrings exactly; `limit=None` by default (Hard Rule 0 compliant, the module's
  own header explains why); reason codes are never silently dropped; deterministic sort order
  (`score desc, name asc`, never hash order). **CLEAN.**
- `audit.py` — read end to end. `audit_invariants()` runs over the full, uncapped record set;
  the `[:4]` and `rng.sample(...)` truncations in `main()` are terminal-display sampling only
  (explicitly documented as a "SAMPLE" pass, seeded, separate from the exhaustive "INVARIANTS"
  pass which is what actually decides pass/fail) — not a Hard Rule 0 violation. **CLEAN.**
- `ledger.py` — read end to end apart from the already-known `assay_to_standards` band-edge
  issue above. `to_standards`/`from_standards`/`cross_rate`/`work_value` all correctly return
  `None` for the non-convertible `"poneglyph-grade favour"` currency and for unlisted currencies;
  `JOULES_PER_STANDARD` is genuinely imported from `physics.MATERIAL`, not hand-copied (the
  module's own header explicitly calls out avoiding that failure class). **CLEAN apart from the
  known item.**

## Modules read end to end and found fully CLEAN this run

`entity_match.py`, `audit.py`

(`ledger.py` and `anchors.py` are clean apart from the one already-known, owner-ruling-pending
item each; `endpoint.py` and `foreman.py` carry the findings above.)
