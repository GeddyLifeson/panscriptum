# Audit batch 15 — wiki_source.py, local_agent.py, identity.py, worldseed.py, hosts.py, thread_integrity.py, scale_theories.py

Every line of every listed file was read (wiki_source.py 616 lines, local_agent.py 505,
identity.py 423, worldseed.py 327, hosts.py 243, thread_integrity.py 184, scale_theories.py 148).

---

## src/wiki_source.py

### FINDING 1 (VERIFIED, HIGH — HARD RULE 0 + docstring contradiction) — `wiki_source.py:352-389` `all_categories(hard_stop=6000)`

Docstring (352-362):
```python
def all_categories(subdomain, min_pages=40, hard_stop=6000):
    """[(size, name)] for every category on a wiki holding at least `min_pages` pages.
    ...
    `hard_stop` bounds the API walk, not the answer: it exists so a wiki with a hundred thousand
    year-buckets cannot spin here forever.
    """
```

Code (369-389):
```python
    out, cont = [], None
    while len(out) < hard_stop:
        p = {"action": "query", "list": "allcategories", "aclimit": 500,
             "acmin": min_pages, "acprop": "size"}
        if cont:
            p["accontinue"] = cont
        try:
            d = _api(subdomain, p)
        except Exception:
            silence.note("wiki_source.py:all_categories")
            break
        for c in d.get("query", {}).get("allcategories", []):
            name = c.get("*") or ""
            if name and not _META_CATEGORY.search(name):
                out.append((c.get("pages", 0), name))
        cont = d.get("continue", {}).get("accontinue")
        if not cont:
            break
    with _ALLCATS_LOCK:
        _ALLCATS[key] = out
    return out
```

The `while len(out) < hard_stop` condition directly gates `out`, which is exactly the list
`return out` hands back — there is no separate "walk" counter distinct from the answer. The
docstring's claim that `hard_stop` "bounds the API walk, not the answer" is false: it bounds the
answer. `list=allcategories` returns MediaWiki categories in alphabetical order by default (no
`acdir=descending` is passed), so once a wiki has more non-meta categories meeting `min_pages`
than `hard_stop`, the categories dropped are whichever sort alphabetically last — an arbitrary,
content-blind cutoff of exactly the kind Hard Rule 0 forbids. (The loop can also overshoot by up
to 499 entries per batch since the check only runs between API pages, but that doesn't change the
substance — the cap is real and it is alphabetical.)

This propagates into `discover_categories()` (392-406), which is the only caller, and from there
into `find_categories()`'s "discover" pass (428-434) that supplements the fixed `CATEGORY_PROBES`
list — so on a wiki with an unusually large category namespace, alphabetically-late categories
(the kind a "Superman"/"Wonder Woman"-adjacent late-alphabet grouping could be) can silently never
be discovered as matching a canonical bucket. This is the already-filed suspect from
`NEXT_STEPS.md` section F ("6000 is the same number that once lost Superman from the DC roster")
— independently re-verified here by tracing the loop condition and the MediaWiki API's default
sort order.

### Everything else in wiki_source.py: CLEAN

- `_get`/`_api`: real UA, shared rate limiter via `feats._throttle` plus a `MIN_GAP` floor,
  retries on 429/503/exception — no swallowed distinguishability issue (`_get` always re-raises
  after retries are exhausted; `silence.note` is a side-channel log, not a substitute return).
- `resolve_wiki` correctly prefers `data/WIKI_HOSTS.json`, isolates the file-read try/except from
  the rest of the function per its own comment (an explicit fix for a prior NameError-swallowing
  bug), and falls through to guess+verify. Fine.
- `verify_wiki_matches`'s `srlimit=8` and `find_categories`'s probe `cmlimit=3` are diagnostic
  membership checks (does this category exist / does this wiki know this subject), not roster
  truncations — they never return counted results to a caller as "the roster."
- `find_categories(limit=None, ...)`: default `None`, and its own docstring explicitly documents
  the historical Hard Rule 0 fix ("It was 6, which quietly discarded..."). Confirmed all call
  sites (`src/catalogue_web.py:160`) pass no truncating `limit`.
- `category_members(limit=None)`: paginates via `cmcontinue` until exhausted when `limit=None`;
  docstring explicitly states the Hard Rule 0 rationale. Confirmed call sites
  (`catalogue_web.py:95,168`) pass `limit=None`.
- `page_texts`/`extracts`/`page_text`: `max_chars`/`chars` bound the *prose length of one page's
  description*, not a roster of entities — and `extracts()`'s `for i in range(0, len(titles), 20)`
  processes every title, never truncates the title list itself. `page_text`'s 2026-08-23 fix
  (continue-not-return across all three section attempts) is real and matches its comment.
- `rank_by_size(top=None)`: ranks, doesn't truncate by default; confirmed callers pass `top=None`
  with an explicit `# rank, never truncate` comment at both call sites.
- `clean_titles`: dedup/subpage filter, no cap.

---

## src/local_agent.py — SPECIAL FOCUS (the write gate)

### FINDING 2 (VERIFIED, HIGH — security-adjacent, path-traversal) — `local_agent.py:233-238` `_safe()` prefix-boundary bug

```python
def _safe(path):
    """A path the model may touch: inside the project, never the export copy or .git."""
    full = os.path.abspath(os.path.join(HERE, path or "."))
    if not full.startswith(HERE) or ".git" in full.split(os.sep):
        return None
    return full
```

`full.startswith(HERE)` has no path-separator boundary check. Demonstrated directly:

```
>>> HERE = os.path.abspath('C:/Users/imarl/panscriptum-library-kit')
>>> full = os.path.abspath(os.path.join(HERE, '../panscriptum-library-kit-EVIL/x.py'))
'C:\\Users\\imarl\\panscriptum-library-kit-EVIL\\x.py'
>>> full.startswith(HERE)
True
```

A `..`-relative path that resolves to a **sibling** directory whose name happens to start with
`panscriptum-library-kit` passes the guard, because the check is a raw string prefix test, not a
directory-boundary test (it should be `full == HERE or full.startswith(HERE + os.sep)`). This is
the exact question the special focus asked ("can a `..` or an absolute path escape it?") — a `..`
path can, whenever a sibling directory sharing the prefix exists. Today's disk only has
`C:\Users\imarl\panscriptum-export` alongside `panscriptum-library-kit` (checked directly — it
does not share the prefix, so it is not reachable through this specific hole today), so this is
not live-exploitable against `panscriptum-export` right now, but the guard itself is broken and
`_safe()` gates every one of the four tools (`read_file`, `list_dir`, `grep`, and — critically —
`propose_patch`'s target file resolution), so the moment any sibling directory sharing that prefix
exists, the model gains read AND WRITE access outside the project root through this function.

### FINDING 3 (VERIFIED, CRITICAL — the denylist can be bypassed on this machine's own OS) — `local_agent.py:358-372` case-sensitive denylist vs. case-insensitive filesystem

```python
def t_propose_patch(path, find, replace, why="", apply=True, log=None, **_):
    full = _safe(path)
    if not full or not os.path.isfile(full):
        return {"applied": False, "error": "no such file: " + str(path)}
    modname = os.path.basename(full)[:-3] if full.endswith(".py") else None
    ...
    rel = os.path.relpath(full, HERE).replace(os.sep, "/")
    denied = modname if modname in DENYLIST else (rel if rel in DENYLIST_PATHS else None)
```

`DENYLIST = {"foreman", "silence", "health", "allsweep", "estate", "standards", "verify_math",
"local_agent"}` (line 52) and `DENYLIST_PATHS = {"config.yaml"}` (line 59) are both plain
case-sensitive Python sets. `modname`/`rel` are derived from the literal case of the `path`
argument the model supplies — `os.path.abspath`/`os.path.join` never touch the filesystem to
normalize case. On Windows the filesystem is case-insensitive, so `os.path.isfile()` on
`src/Foreman.py` resolves to the real `src/foreman.py` and returns `True`, while `modname` comes
out as `"Foreman"`, which is **not** in the lower-case `DENYLIST`. Demonstrated directly on this
machine:

```
>>> full = 'C:\\Users\\imarl\\panscriptum-library-kit\\src\\Foreman.py'
>>> os.path.isfile(full)          # resolves via Windows case-insensitive FS
True
>>> modname = 'Foreman'
>>> modname in DENYLIST
False
```

`t_propose_patch(path="src/Foreman.py", ...)` therefore proceeds straight past the denylist to
`_gates()` and can be **applied to the real `foreman.py`** — the checking machinery's own source
— exactly the outcome the denylist comment says must never happen ("the checking machinery may
not edit itself"). The same bypass applies to every other entry (`silence.py`, `verify_math.py`,
even `local_agent.py` itself) and to `config.yaml` via `DENYLIST_PATHS`. This is the sharpest
finding in the batch and squarely on the special focus's target: an unreviewed local-model patch
can land on the gate/verifier files themselves, on the machine's own OS, with no need for any
adversarial input beyond the model spelling a path with different capitalization than usual.

### FINDING 4 (VERIFIED, HIGH — swallowed failure, contradicts the module's own promise) — `local_agent.py:384-402` auto-revert can fail and still reports `"reverted": True`

```python
    backup = original
    try:
        with open(full, "w", encoding="utf-8") as f:
            f.write(original.replace(find, replace, 1))
        fail = _gates(full, modname)
        if fail:
            with open(full, "w", encoding="utf-8") as f:
                f.write(backup)
            return {"applied": False, "reverted": True, "gate": fail}
        return {"applied": True, "why": why[:200]}
    except Exception as e:
        silence.note("local_agent.py:apply")
        try:
            with open(full, "w", encoding="utf-8") as f:
                f.write(backup)
        except Exception:
            silence.note("local_agent.py:revert")
        return {"applied": False, "reverted": True,
                "error": type(e).__name__ + ": " + str(e)[:120]}
```

Two problems, both instances of LENS #2 (a failure path returning the same shape as success):

1. In the `except` branch, the inner revert-write is wrapped in its own `try/except` that
   **swallows** any exception via `silence.note("local_agent.py:revert")` — and the function
   still unconditionally returns `"reverted": True"` immediately after, regardless of whether that
   inner write actually succeeded. If the disk write that applied the patch succeeds but the
   *revert* write then fails (locked file, permission denial, disk full — precisely the class of
   Windows file-locking hazard `silence.replace_retry`'s own docstring documents elsewhere in this
   repo), the broken/patched file is left on disk in `src/`, silently, while the caller — the
   model's own tool-result message, and any human reading `main()`'s JSON dump — is told the
   revert happened. This directly contradicts the module's docstring promise ("A backup is
   written before and restored on ANY failure, including a crash inside the checking") and the
   special focus's own question ("whether the auto-revert can fail silently") — it can, and the
   return value actively misreports it.
2. The `if fail:` branch's revert-write (391) has **no** try/except of its own; if it raises, it
   is caught by the outer `except`, which then repeats the same already-failed write and again
   reports `"reverted": True"` unconditionally on the way out.

### Denylist/gate mechanics otherwise: mostly sound, worth noting

- `_gates()` (291-355) is genuinely comprehensive and its own docstring narrates two real prior
  bugs it fixes (non-.py files skipping every gate; a non-executing pyflakes read as "clean") —
  both fixes check out against the code as written. The whole-suite `verify_math.py` gate runs
  unconditionally for every file type, matching its docstring.
- `_CHECKS`/`t_run_check`'s allowlisted argv construction (179-230) is a fixed-vector allowlist,
  not a shell string the model can inject into — sound.
- `propose_patch`'s `original.count(find) != 1` uniqueness requirement (374-377) is sound and
  matches its docstring.
- `t_grep`/`t_find_symbol`: no caps on results, walk the whole tree, matching the "never a
  truncation" framing.

---

## src/identity.py

### FINDING 5 (VERIFIED, MEDIUM — comment/docstring contradicts code) — `identity.py:180-207` `_is_continuity()`'s own worked example fails

The module docstring (57-61) and the function's own docstring (190-196) both use `(Fates)` as the
canonical example that BRANCHING is sufficient **on its own**, with only one bearer:

> "`(Fates)` has one bearer and is obviously a continuity because that bearer exists in three
> other branches. Either alone admits it."

But the code:

```python
def _is_continuity(desig, stat):
    d = (desig or "").strip()
    if not d or d.lower() in NEVER:
        return False
    if d[0].islower():
        return False
    n = stat["bearers"] if isinstance(stat, dict) else stat
    shared = stat.get("shared", 0) if isinstance(stat, dict) else 0
    if n >= MIN_BEARERS:
        return True
    return n >= 2 and shared >= max(2, 0.5 * n)
```

requires `n >= 2` as a hard prerequisite even on the branching path. `shared` can never exceed
`n` (see `mine()`'s construction at 173-176: `shared` counts a subset of the same designator's own
bearer set). For the docstring's own `(Fates)` case — one bearer (`n=1`), that bearer shared with
other designators (`shared=1`) — the function returns `False`, not `True`. Verified directly:

```
>>> identity._is_continuity('Fates', {'bearers': 1, 'shared': 1})
False
```

Branching is documented as "sufficient... alone" but the code makes population `>=2` a
co-requirement, silently misclassifying any single-bearer-but-heavily-shared designator (a young
alternate continuity with exactly one character written up so far — precisely the case `MIN_BEARERS`'s
own comment at line 96-98 says the module is trying not to lose) as a non-continuity.

### FINDING 6 (VERIFIED, MEDIUM — swallowed failure, same shape as a real "no marker" answer) — `identity.py:291-320` `epoch_of()` cannot distinguish a failed model call from an absent epoch marker

```python
def _ask(prompt, system=EPOCH_SYSTEM):
    try:
        import read as R
        R.ensure_transport(verbose=False)
        return R._ask(R.config(), system, prompt, EPOCH_SCHEMA)
    except Exception:
        silence.note("identity.py:_ask")
        return None

def _json(raw):
    if isinstance(raw, dict):
        return raw
    m = re.search("[{].*[}]", raw or "", re.S)
    if not m:
        return {}
    ...

def epoch_of(sentence):
    """The epoch a single sentence places itself in, or "" when it names none."""
    d = _json(_ask(sentence.strip()[:1200]))
    if not d.get("explicit"):
        return ""
    return str(d.get("epoch") or "").strip()[:60]
```

`_ask` returns `None` on any transport/model exception. `_json(None)` → `raw or ""` → `""` → no
regex match → `{}`. `epoch_of` then reads `d.get("explicit")` as falsy either way and returns
`""`. A genuine "this sentence names no epoch" answer and a network/model failure both surface as
the identical `""` to `epoch_of`'s caller (`chain.py:381` per the comment at 323-328) — the exact
pattern this project's own `wiki_source.py:page_text` fix (BUGS m4, cited in that file at
455-461) was written to eliminate elsewhere: "a transient hiccup wearing the face of a page with
no prose ... recorded as genuine silence and never re-asked." `identity.py` has the same shape,
unfixed, one file over.

### Everything else in identity.py: CLEAN

- `load()`/write of `data/DESIGNATORS.json` (210-223) is correctly atomic — `tmp = CACHE + ".tmp"`
  then `silence.replace_retry(tmp, CACHE)`. Two-writer contract respected.
- `mine()` (147-177) uses every title in the cache, no sampling, matching its own docstring.
- `EPOCH_REQUIRED`/`epoch_directive`/`epoch_acceptable` (391-424): consistent, no caps, no
  contradiction found.

---

## src/worldseed.py

### FINDING 7 (VERIFIED, MEDIUM-HIGH — two-writer/atomic-write contract violation) — `worldseed.py:317-322` bare `open(path,"w")`+`json.dump` on a SHARED data file

```python
    if args.write:
        path = os.path.join(HERE, "data", "WORLDSEEDS.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({w["designation"]: {"address": address(w), **w} for w in worlds},
                      f, indent=2, ensure_ascii=False)
        print(f"\nwrote {path}")
```

`data/WORLDSEEDS.json` is not a private scratch file — it is read by at least two other modules:

```
src/address_space.py:302:  with open(os.path.join(HERE, "data", "WORLDSEEDS.json"), encoding="utf-8") as f:
src/pipeline.py:1401:      seeds = json.load(open(os.path.join(HERE, "data/WORLDSEEDS.json"), ...))
```

This is exactly the truncate-then-fill pattern the project's own `silence.write_json()` docstring
(src/silence.py:250-264, dated 2026-08-25) names as a repeat hazard: "A reader arriving in the gap
sees an empty or half-written file; a crash in the gap leaves it that way permanently." Contrast
with this same file's own `to_options`/`address` design discipline, and with `identity.py`'s
`load()` a few files over in this same batch, which does the tmp+`silence.replace_retry` pattern
correctly. `worldseed.py --write` should use `silence.write_json(path, ...)` instead.

### Everything else in worldseed.py: CLEAN

- `build_all(limit=None)`'s `if limit and len(out) >= limit: return out` (282-283) truncates only
  when the CLI's own `--limit` flag is explicitly passed by the operator (default `None`) — this
  reads as the same sanctioned pilot/sample pattern `manifest_builder.py --pilot 3` uses per
  CLAUDE.md, not a hidden cap on catalogued data.
- The `WORLD` regex match runs over the *whole* description (272-278), with an explicit comment
  documenting the 2026-08-24 fix for a prior 200-char-window truncation bug — matches the code.
- `features()`/`_first()`: no truncation; `_first`'s seeded-fallback (never defaulting to a fixed
  value) is exactly what its docstring claims and is a real, checked-in fix for a measured 86-87%
  default-collapse bug.
- `to_fmg_query`/`unreachable_by_url`: the URL adapter deliberately narrows to 4 of 10 parameters,
  but says so explicitly and in detail (`URL_SETTABLE`, the empirical-test comment block at
  203-219) — a documented, honest adapter limitation, not a silent cap on library data.

---

## src/hosts.py

### FINDING 8 (VERIFIED, MEDIUM — atomic-write contract followed in letter but not in the project's own hardened form; concurrency-adjacent) — `hosts.py:78-91` `add()` writes `data/SOURCE_HOSTS.json` via a bare `tmp+os.replace`, not `silence.replace_retry`

```python
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

This is the temp-file-then-rename shape (better than a bare in-place `open(...,"w")`), and
`os.replace` is atomic in isolation — but it is exactly the pattern `silence.replace_retry`'s own
docstring (src/silence.py:223-229) says is insufficient on this project's Windows deployment: "on
Windows the rename is DENIED while any reader holds the target open... One such collision took an
assay worker down mid-batch (2026-08-23, WinError 5)." `add()`'s `os.replace(tmp, EXTRA)` has no
retry/backoff and no `silence.note` on failure — a `PermissionError` here propagates uncaught out
of `add()`, and from there out of `discover()`'s main-thread loop (185-186), aborting a
`--discover` run outright on a transient reader collision instead of landing next round. The tmp
filename (`EXTRA + ".tmp"`) also doesn't carry a PID/thread discriminator, which `silence.write_json`'s
docstring separately flags as a hazard when two writers race on the same temp name — `hosts.py`'s
`add()` calls are serialized within one `discover()` run (see below) but nothing prevents a second
concurrent process (e.g. a second `--discover` invocation, or any other future writer of
`SOURCE_HOSTS.json`) from colliding on `SOURCE_HOSTS.json.tmp`.

Read separately: within a single `discover()` call, all `add()` calls happen in the main thread
(the `ThreadPoolExecutor` only parallelizes the read-only `work()` probes, at line 180-189), so
this is not a live in-process race today — the exposure is to (a) an external reader of
`SOURCE_HOSTS.json` holding it open at the moment of rename (the documented WinError 5 shape) and
(b) a second concurrent writer process.

### Everything else in hosts.py: CLEAN

- `hosts_for()`/`primary_host()`/`coverage()`: no caps on the returned host lists; correctly
  layers primary + all extras.
- `discover()`'s `per_source=24` cap on **candidate host names to network-probe** (156-157) is
  explicitly scoped by its own comment to sit "AFTER the evidence" and drop only *speculative,
  invented subdomains*, never known/grounded hosts — this bounds a diagnostic probing budget, not
  a roster of real catalogued entities or sources, so it reads as compliant with Hard Rule 0's
  intent rather than a violation of it.
- `work()`'s `names = list(by.get(source) or [])[:40]` (143) samples entity names only to *score*
  whether a candidate host is worth adopting (an evidence-gathering probe, not the delivered
  roster) — flagged here for completeness per the audit's instruction to report every `[:N]`
  found, but categorized as bounding a diagnostic sample, not truncating real catalogued data.

---

## src/thread_integrity.py — CLEAN

Read in full. No correctness bugs, no swallowed-failure ambiguity beyond ordinary
`silence.note`-and-skip on unreadable record files (consistent with the rest of the project's
idiom), no bare-write hazards (this module has no file writes at all — it is read-only analysis).
`classify()`'s DANGLING/RECIPROCAL/ASYMMETRIC-LAWFUL/ASYMMETRIC-SUSPECT logic was traced against
its own docstring (the 2026-08-24 BUGS m12 correction) and the code matches the docstring's
stated behavior for both the `recorded=None` (today) and future-directed-graph cases.

The only truncations in the file are `main()`'s console report slices — `[:8]` strongest
reciprocal bonds, `[:6]` worst asymmetric-suspect pairs (174, 179) — which are display-only top-N
previews of a CLI summary printout; the underlying `detail[...]` collections used to build them
are never themselves capped, and nothing downstream consumes only the printed slice.

---

## src/scale_theories.py — CLEAN

Read in full. Pure physics/data module, no I/O, no file writes, no roster of entities to cap.
Spot-checked the arithmetic:
- `T2_MASS_SHED`'s claimed `70 kg * c^2 = 6.3e18 J ≈ 1500 megatons`: `70 * (2.99792458e8)^2 =
  6.294e18 J`; `/ 4.184e15 J/megaton ≈ 1504.6` megatons — matches "fifteen hundred megatons."
- `growth_strike()`'s `tnt_kg_equivalent = ke / 4.184e6` correctly uses J-per-kg-TNT (not
  J-per-megaton) for a per-kg conversion — consistent with its own units.
- `bulk_export_beta()`'s edge case (`resident_mass_kg <= 0 or mass_kg <= resident_mass_kg` →
  return the flat 64-bit structural cost) is consistent with the docstring's declared
  decomposition.

No findings.
