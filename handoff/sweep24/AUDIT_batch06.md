# Sweep 24 — Batch 06 Audit

Files in this batch and how completely each was read:

- `src/magnitude.py` (1027 lines) — read in full, every line.
- `src/silence.py` (426 lines) — read in full, every line.
- `src/estate.py` (339 lines) — read in full, every line.
- `src/navtree.py` (273 lines) — read in full, every line.
- `src/catalogue_codex.py` (210 lines) — read in full, every line.
- `src/scope.py` (153 lines) — read in full, every line.

Also read `src/assay.py` (649 lines, full) as necessary cross-reference — it is not in this
batch, but `magnitude.py`'s worst finding physically lives inside it and cannot be characterised
without quoting it. Every claim below that touches `assay.py` is clearly marked as such.

Several claims were checked against **live data** on this machine (the owner's real
`THE_PRIME_OMNIVERSE_CODEX.md`, `data/SWEEP_ROLL.json`) rather than left as code-reading
inference, using a scratch script run through the project's own `parse_codex()` /
`norm()` functions. Those are marked VERIFIED WITH LIVE DATA below.

---

## 1. `assay.py:219-223` (root cause) / `magnitude.py:244`, `magnitude.py:706-711` (blast radius) — MAJOR — VERIFIED

`assay.axis_score()`:

```python
def axis_score(x, band, axis):
    if x is None or x <= 0 or band not in BAND_EDGES:
        return None
    i = LADDER.index(band)
    if i + 1 >= len(LADDER):
        return 9.9
    lo = BAND_EDGES[band].get(axis)
    hi = BAND_EDGES[LADDER[i + 1]].get(axis)
    ...
```

`LADDER = ["M0", ..., "M10"]` (11 rungs). For `band == "M10"`, `i = 10`, `i + 1 = 11 >= len(LADDER)`,
so the function returns the flat literal `9.9` for **any** positive `x`, without ever consulting
`BAND_EDGES["M10"]` (whose own floors are enormous, e.g. `ruin=1e99`). A quantity as small as "40
tons of TNT" (~1.67e11 J, twelve orders of magnitude below `M10`'s own floor) scores 9.9 exactly
the same as a quantity of 1e120 J.

This function is called from `magnitude.py:244` inside `quantity_scores()`:

```python
s = A.axis_score(x, anchor, axis)
```

and `quantity_scores()`'s output unconditionally overwrites the model-gated score in
`assay_entity()` at `magnitude.py:706-711`:

```python
    # 5 QUANTITY -- measured readings overwrite the model's judgement on their axis. An
    # instrument outranks an opinion, which is the ordering the Attestation ladder already
    # states (Instrumented above Transcribed).
    for ax, q in quantity_scores(ev, anchor).items():
        scores[ax] = q["score"]
        sheet[ax] = f"INSTRUMENT {q['measured']} = {q['si']:.3g} SI  <- {q['feat'][:120]}"
```

**Failure scenario:** any entity whose anchor resolves to `M10` — either because the model
genuinely said `M10`, or because `host_ceiling()` (magnitude.py:854-882) returned `None` (no
scope data cached and the live `SCOPE.scope_for()` call also failed/returned nothing, which is
common — the file's own docstring says 203/211 sources are `unassayed`) and so no ceiling clamp
was applied at all — and who has even one measured Ruin or Reach quantity in its mined feats
(a "40 tons" or "3,000 meters" sentence) will have that axis force-set to 9.9 by "the highest-
grade evidence the library can hold" (module's own words), *regardless of the quantity's actual
magnitude*. This is precisely the "all eleven axes scored 9.9" failure the whole file's five-guard
architecture exists to prevent (see the module docstring's own opening anecdote) — reproduced by
the guard built to be the most trustworthy of the five, because the top rung has no upper edge to
interpolate against and the code silently treats "no upper edge" as "maximum score" rather than
returning `None`/unscored. It can also corrupt `saturated()` (magnitude.py:390-393), which fires
on `>=6 axes at >=9.0`, either triggering or masking the saturation refusal based on an artifact
of this bug rather than genuine model behaviour.

**Severity: MAJOR. VERIFIED** by direct trace: `LADDER` has 11 elements, `axis_score` unconditionally
returns `9.9` whenever `band == LADDER[-1]`, and that return value is not gated by any of the five
guards described in the module docstring — Guard 5 is arithmetic and is trusted precisely *because*
it bypasses the model, but the arithmetic itself is broken for the top band.

---

## 2. `magnitude.py:911-996` (`run_batch`) — cross-process lost update AND unsafe fixed temp filename — MAJOR — VERIFIED

`run_batch()` loads `done` once per process:

```python
done = {}
if resume and os.path.exists(OUT):
    try:
        with open(OUT, encoding="utf-8") as f:
            done = json.load(f)
    except Exception:
        silence.note("magnitude.py:resume")
        done = {}
```

Every worker thread's completion (`work()`, magnitude.py:952-990) mutates this **process-local**
snapshot and rewrites the *entire* file from it on every single completion:

```python
        with lock:
            done[h + "|" + n] = r
            ...
            tmp = OUT + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(done, f, ensure_ascii=False)
            for attempt in range(5):
                try:
                    os.replace(tmp, OUT)
                    break
                except PermissionError:
                    if attempt == 4:
                        silence.note("magnitude.py:assays-replace")
                    else:
                        time.sleep(0.3 * (attempt + 1))
```

Two distinct, compounding defects, both VERIFIED by direct reading:

**(a) Cross-process lost update (matches the known suspect exactly).** `done` is read from disk
once at process start and never re-read. If a second process (e.g. a second `--batch` invocation,
or the same command run twice, or `--host X` alongside `--host Y`) is also running `run_batch`,
each process's `done` dict only ever reflects the file as it stood at that process's own start.
Every completion writes the *entire* local snapshot back, so whichever process writes last
clobbers every entry the other process wrote that isn't in its own stale snapshot. `threading.Lock`
(`lock = threading.Lock()`, line 949) is process-local and provides zero protection here — this is
exactly the "`threading.Lock` guarding something written from multiple OS processes" shape called
out in the audit brief.

**(b) The temp filename is fixed (`OUT + ".tmp"`), not PID/thread-qualified**, unlike the
`silence.write_json()` primitive that this same file already imports and uses elsewhere
(`silence.note`, `silence.replace_retry` in `calibrate()`). `silence.py`'s own docstring for
`write_json` (see finding 3 below) explicitly names this exact pattern as the fixed hazard:
"THE TMP NAME CARRIES PID AND THREAD... Two writers of the same path otherwise collide on the temp
file itself, and the loser can replace the winner's target with a partial file." `run_batch` hand-
rolls the *pre-fix* version of the primitive instead of calling it. Concretely: if two OS processes
race on `data/ASSAYS.json.tmp`, one process's `open(tmp, "w")` can truncate the other's
in-progress write, and if process A's `os.replace(tmp, OUT)` fires after process B has already
consumed and removed `tmp` via its own successful replace, `os.replace` raises
`FileNotFoundError` — which this loop does **not** catch (only `except PermissionError:`). That
exception propagates out of `work()` uncaught (the only try/except in `work()` wraps the
`assay_entity()` call, not the write block) and out through `ThreadPoolExecutor.map`, killing the
entire batch run with an unhandled exception the "written to be killed" design explicitly claims
not to have.

**Severity: MAJOR. VERIFIED.** (a) is the known suspect, confirmed by code trace. (b) is an
additional, more severe failure mode uncovered in this pass: not just silent data loss but a
plausible unhandled-exception crash path, using precisely the anti-pattern `silence.write_json`
exists to eliminate, in a file that already imports `silence`.

---

## 3. `silence.py:250-287` (`write_json`) / `silence.py:223-240` (`replace_retry`) — the primitive does not deliver what its callers assume — MAJOR — VERIFIED

`replace_retry` retries `os.replace` up to 5 times against `PermissionError` only, with total
backoff of at most ~3.0s (`0.3*(a+1)` summed over 4 sleeps), then gives up:

```python
def replace_retry(tmp, dst, attempts=5):
    for a in range(attempts):
        try:
            os.replace(tmp, dst)
            return True
        except PermissionError:
            if a == attempts - 1:
                note("replace-denied:" + os.path.basename(dst))
            else:
                _t.sleep(0.3 * (a + 1))
    return False
```

`write_json` returns whatever `replace_retry` returns:

```python
def write_json(path, obj, **dump_kw):
    ...
    return replace_retry(tmp, path)
```

The docstring says "the caller's write lands next round, which is the established behaviour
here" — true for a loop like `run_batch`'s (finding 2), but **false for every one-shot call site in
this batch**, none of which check the return value:

```
navtree.py:263:        silence.write_json(OUT, data, separators=(",", ":"), ensure_ascii=False)
catalogue_codex.py:203:        silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)
scope.py:119:    silence.write_json(OUT, out, indent=1, ensure_ascii=False)
```

**Failure scenario:** if the target file (`NAVTREE.json`, `SWEEP_ROLL.json`, `SCOPE.json`) is held
open by another reader (the dashboard, a concurrent script) for longer than ~3 seconds — which is
plausible for a dashboard that polls on its own clock, per this very module's own comments
elsewhere in the codebase about WinError 5 collisions — `replace_retry` exhausts its retries,
`note()` records the failure into the `health` ledger (silently, to disk, requiring someone to
actively read `state/failures.json`), and returns `False`. Every one of the three call sites in
this batch discards that boolean. The script then prints a success message (`navtree.py` prints
"wrote {OUT} ({size} KB)" unconditionally after the call; `scope.py`'s `build()` prints per-host
progress lines as if landed) and exits — with the on-disk file **silently unchanged** from before
the run, the caller's in-memory update discarded, and a stray, permanently orphaned
`path.PID.TID.tmp` file left on disk (nothing ever removes a tmp file after a failed
`replace_retry` — the cleanup-on-failure code in `write_json` only runs if the *dump itself*
raised, not if `replace_retry` failed after a clean dump). This is the project's signature failure
class (a real failure indistinguishable from success) living inside the very primitive built to
end that class project-wide.

**Severity: MAJOR. VERIFIED** by direct trace of the three unchecked call sites in this batch,
confirmed by `grep` (no site in this batch inspects the return value of `write_json`).

**Secondary, minor note (COSMETIC):** `write_json`'s own comment block (silence.py:262-265) cites
`silence.py:_chunk_put` and describes exactly the PID/thread-qualified-tmp fix — the very fix
`magnitude.py:run_batch` (finding 2) does not use, despite importing this module. The primitive is
correct in isolation; the fix simply is not adopted everywhere the module's own docstring implies
it should be.

---

## 4. `catalogue_codex.py:159` — ~70 codex elements silently miscategorised into THINGS — MAJOR — **VERIFIED WITH LIVE DATA**

```python
"category": TYPE_CATEGORY.get(etype.lower(), THINGS),
```

`TYPE_CATEGORY` has exact-string keys only (`"weapon"`, `"race"`, `"sub race"`, `"subrace"`,
`"background"`, `"background feature"`, etc.) with no normalisation for near-miss element-type
labels, and any lookup miss falls through to `THINGS`.

Ran the project's own `parse_codex()` against the owner's real
`C:\Users\imarl\Documents\5e Character Builder\custom\THE_PRIME_OMNIVERSE_CODEX.md` (11,813
lines) and diffed every distinct element `type` string against `TYPE_CATEGORY`'s keys:

```
total distinct etypes: 18
total elements: 4489

UNMAPPED etypes (fall through to THINGS default):
    35  'weapon property'      e.g. (Eberron: Rising from the Last War, 'Special (Double-Bladed Scimitar)')
    28  'race variant'         e.g. (Eberron: Rising from the Last War, 'Mark of Detection')
     7  'background variant'   e.g. (The Player's Handbook (Core Rules), 'Variant Criminal: Spy')
TOTAL unmapped elements -> 70
```

This is exactly the count and shape the known suspect describes. All three miss their evidently
intended category by the dict's own internal logic: `"weapon"` maps to THINGS but `"weapon
property"` (a game-mechanic trait, not a physical item) does not map at all and lands in THINGS by
accident rather than by design; `"race"`/`"sub race"`/`"subrace"` map to FACTIONS but `"race
variant"` does not and lands in THINGS instead of FACTIONS; `"background"`/`"background feature"`
map to POWERS but `"background variant"` does not and lands in THINGS instead of POWERS.

**Severity: MAJOR. VERIFIED WITH LIVE DATA** — 70 real elements from the owner's actual codex are
confirmed miscategorised by running the exact production code path.

(Checked a related risk and found it clean: the codex's "Full Contents:" line-parsing regex
`^\s{2,}(.+?)\s*\((\d+)\):\s*(.+?)$` could in principle truncate a wrapped multi-line item list
without warning — this would be a Hard-Rule-0 violation. Cross-checked all 281 "Full Contents"
lines' declared counts against parsed item counts: 0 mismatches. Not a live bug in this codex.)

---

## 5. `catalogue_codex.py:122-203` — unguarded read-modify-write on `data/SWEEP_ROLL.json` — MAJOR — VERIFIED

```python
122  with open(ROLL, encoding="utf-8") as f:
123      roll = json.load(f)
...
196          r["entry_count"] = len(rec["entries"])
197          r["status"] = "catalogued"
...
203      silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)
```

The final write (line 203) is individually atomic (via `silence.write_json`, per finding 3's
caveats). But `roll` is read into memory once at the top of `main()` and only written back after
the *entire* run — parsing all 281 "Full Contents" sections of an 11,813-line file, joining
register text, printing per-section summaries. There is no lock held across that window. This
project's own docstring for the sibling `catalogue_web.save_roll()` (quoted in the comment at line
200-202 here) already warns that an interrupted write to this exact file "kills the next run of
either script outright" — the same hazard applies to a *concurrent* writer, not just an
interrupted one: any other process that reads-modifies-writes `data/SWEEP_ROLL.json` during this
script's run (the comment itself says "Four scripts write this roll") will have its changes
silently discarded the moment this script's stale in-memory `roll` snapshot lands at line 203,
because line 203 writes the *whole* dict, not a merge.

**Severity: MAJOR. VERIFIED** — the atomic single-call primitive is used correctly, but the
read-modify-write *span* around it is unguarded, which is exactly the two-writer contract failure
this audit's lens asks about: atomicity of the write does not imply safety of the read-modify-write
cycle wrapping it.

(Checked whether this collision is presently *reachable* given real data: confirmed 0 substring-
match ambiguities between codex section titles and `SWEEP_ROLL.json` entries with the current
data, so the separate substring-matching logic at `catalogue_codex.py:132-135` is not currently
mis-routing any entry to the wrong codex section — checked and clean, not reported as a finding.)

---

## 6. `scope.py:68-81` — sample-of-8 pages, `srlimit=3`×4, sets a fiction-wide Magnitude ceiling — MAJOR — VERIFIED (known suspect, confirmed)

```python
QUERIES = ["cosmology universe world setting", "multiverse", "universe", "world"]

def scope_for(host, verbose=False):
    titles, seen = [], set()
    for q in QUERIES:
        d = F.api(host, {"action": "query", "list": "search", "srlimit": "3", "srsearch": q})
        for row in (d or {}).get("query", {}).get("search", []):
            if row["title"] not in seen and row.get("size", 0) > 1200:
                seen.add(row["title"])
                titles.append(row["title"])
    if not titles:
        return None
    pages = F.fetch(host, titles[:8])
    text = " ".join(F.strip_wikitext(v) for v in pages.values())
    counts = {lab: len(rx.findall(text)) for lab, rx, _ in _RE}
```

Four search queries, each hard-capped to the wiki API's top 3 results (`srlimit=3`, max 12 titles
before dedup/size filtering), then truncated again to the first 8 of whatever survives
(`titles[:8]`). The resulting term-frequency count over at most 8 pages becomes `ceiling_for()`'s
output, which `magnitude.py:host_ceiling()` (magnitude.py:854-882) uses to clamp **every entity in
that fiction** — quoting that function's own docstring: "Jace Beleren came back at M10.77...
Silver Surfer at M10.93... the SOURCE's own measured scope is the outside check." A ceiling
computed from 8 pages, selected 3-at-a-time from four fixed search phrases, decides the Magnitude
ceiling for an entire fiction's worth of entities — the textbook Hard Rule 0 violation: "a cap on
an ordered listing... silently decides that everything past the cutoff does not exist," here
applied to the sample that grounds a project-wide clamp rather than to a listing of entities
directly, but with the same shape and larger blast radius (one host's under-sampled ceiling
affects every entity assayed against that host).

**Severity: MAJOR. VERIFIED** by direct code reading; matches the known suspect exactly, no
additional live-data check was needed since the cap values (`srlimit=3`, `titles[:8]`) are
unconditional and always in effect.

---

## 7. `silence.py` — `swallow` context manager is documented as the pattern, adopted nowhere — MINOR — VERIFIED

`silence.py`'s own module docstring (lines 39, 78-88) presents `swallow(kind)` as one of "two
things this file does" and gives a worked usage example (`with swallow("fetch", host): ...`).
Searched every `.py` file in `src/` for an actual call site:

```
$ grep -rn "swallow(" src/*.py | grep -v "def swallow\|class swallow"
silence.py:39:    swallow(kind)    a context manager...
silence.py:81:        with swallow("fetch", host):
```

Both hits are inside `silence.py`'s own docstrings. No other module in `src/` uses `swallow` as a
context manager anywhere — the actually-adopted pattern everywhere else is calling `silence.note()`
directly from inside a bare `except` body (which is also correct and is what `magnitude.py`,
`estate.py`, `navtree.py`, `catalogue_codex.py`, `scope.py` all do). `swallow` is fully-implemented,
documented as load-bearing, and dead.

**Severity: MINOR. VERIFIED.** Not a correctness bug — the two patterns are equivalent in effect —
but the module's own docstring overstates its own adoption, which is worth flagging under the
"comments/docstrings that contradict code" lens, since a future reader would reasonably expect to
find `swallow` in use somewhere given how it's introduced.

---

## 8. `navtree.py:256` — problem list printed capped at 6, audit itself uncapped — COSMETIC — VERIFIED (not a real Hard Rule 0 violation)

```python
problems = audit(data)
print(f"\nAUDIT: {len(problems)} problems")
for p in problems[:6]:
    print("   " + p)
```

`audit()` itself (navtree.py:210-223) is not capped — every problem is found and counted, and the
gate at line 259 (`if args.write and not problems:`) checks the *full* uncapped list, so a write is
correctly refused if any problem exists anywhere, not just among the first 6 printed. Confirmed
this is display-only truncation of a diagnostic printout, not a truncation of the underlying
check or of what blocks a write.

**Severity: COSMETIC. VERIFIED** as harmless — flagged only because the audit brief asks for any
`[:N]` slice to be checked; this one does not bound a universe that should be complete, it bounds
a terminal printout of an already-complete, already-enforced list.

---

## Modules with no findings

None of the six files in this batch came back entirely clean — every file produced at least one
finding above except that `estate.py`'s own logic was read in full and found sound: it is itself
an auditor (checks every file in the tree, explicitly "No sampling anywhere," verified true by
reading `artifacts()`), its zero-byte / malformed-JSON / bad-control-character / syntax-error
checks are all correctly wired to `silence.note()` (observed, not swallowed), and no cap, limit,
or truncation was found in it.
