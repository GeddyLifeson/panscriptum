# Batch 03 — run33
Modules read: standards.py (1510 lines), endpoint.py (394 lines), address.py (290 lines),
render.py (252 lines), chord_field.py (203 lines), suppressions.py (151 lines),
repass_bands.py (119 lines)

## FINDINGS

### 1. suppressions.py:94,118 — suppression path matching is case-insensitive on Windows, silently widening every suppression  [severity: MAJOR]
`suppressed()` and `problems()` both match a suppression's stored `path` glob against a
repo-relative path with `fnmatch.fnmatch()`:

```python
for r in active(detector):
    if fnmatch.fnmatch(rel, r.get("path", "")):
        return r
```

`fnmatch.fnmatch()` normalizes both operands through `os.path.normcase()` before comparing, and
on Windows `normcase` lowercases the string — so the match is case-insensitive on the platform
this project actually runs on (confirmed by direct execution: `fnmatch.fnmatch('Data/Fixtures/
Foo.py', 'data/fixtures/*.py')` returns `True`; `fnmatch.fnmatchcase` on the same inputs returns
`False`). The module's own header states the rule this breaks in capitals: "a suppression
narrows a detector for a NAMED case. It never turns a detector off. If an exception is broad
enough to hide a class of real findings, the detector is wrong." A suppression added for
`data/fixtures/*` will also silently swallow findings under `DATA/Fixtures/*` or any other
casing variant nobody named or reviewed — the exact silent widening the docstring warns against,
on the exact OS this ships on. `problems()`'s dangling-suppression glob check (line 118) has the
same defect, so a suppression could also fail to report as dangling when the on-disk casing
differs from the recorded pattern. Fix is `fnmatch.fnmatchcase()`.

### 2. suppressions.py:62 — a suppression's write verdict is discarded, so `add()` can report success while nothing lands on disk  [severity: MAJOR]
```python
def _land(rows):
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    tmp = FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)
    silence.replace_retry(tmp, FILE)
```
`silence.replace_retry()` returns `True`/`False` and, by its own docstring, deliberately never
raises on persistent `PermissionError` ("persistent denial is recorded, never raised — the
caller's write lands next round"). `_land()` ignores that return value, and `add()` (line 76-77)
returns `rows[-1]` unconditionally right after calling it — so a caller that adds a suppression
under exactly the concurrent-reader condition this project has hit before (WinError 5, documented
in `silence.py`'s own docstring) gets back a row that looks committed while `SUPPRESSIONS.json`
on disk is untouched. The very next `active()`/`suppressed()` call (which always re-reads from
disk, no cache) will not see it. This is the identical shape `repass_bands.py` in this same
batch was fixed to avoid (see its "GATE ON THE WRITE" comment at line 79-87, explicitly citing a
prior incident where an unchecked write return caused a false "rewritten" report) — the fix
exists in one file in this batch and not in this one.

### 3. endpoint.py:92 — the endpoint cache is saved with a bare `os.replace()`, not the project's own retry helper, so a probed host's result can be silently lost  [severity: MAJOR]
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
`silence.replace_retry()` exists specifically because `os.replace` raises `PermissionError` on
Windows "while any reader holds the target open," and its docstring names this project's own
state files, including caches read by the dashboard, as the exact class of file that collides
this way. `endpoint.py`'s `ENDPOINTS.json` is read/written from every process that probes a host
(`detect()` is called from `feats.py`, `hostcheck.py`, `completeness.py`) and is exactly this
shape of shared cache. Here the plain `os.replace` is wrapped in a bare `except Exception` that
just logs and drops the write — so under the same contention this project has already diagnosed
and fixed via `replace_retry` elsewhere, a freshly-probed `MODE_API`/`MODE_RAW`/`MODE_DEAD`
verdict is silently lost, forcing a redundant re-probe next run (wasted network calls against a
project that already rate-limits itself carefully per host).

### 4. standards.py:1236-1250 — a wedged-queue diagnosis is reported for any failure in the token-flow probe, including ones that contradict it  [severity: MAJOR]
```python
try:
    ...
    with _ur.urlopen(req, timeout=timeout) as r:
        _raw = json.loads(r.read())
    ok = bool(_raw.get("eval_count")) or bool(_raw.get("response", "").strip())
    secs = round(time.time() - t0, 1)
except Exception as e:
    ok, secs = False, None
    silence.note("standards.py:token-flow")
    _ = e
```
and the message built from it (`work_orders`/`report` surfaces this to a human or model as a
HIGH-severity standard):
```python
("probe completed in %ss" % secs) if flow
else "daemon up, generation TIMED OUT -- queue is wedged"
```
The `except` clause is one catch-all around DNS/connect failure, `yaml.safe_load` failure on a
missing or malformed `config.yaml`, a JSON decode error on the response, an HTTP error status, and
an actual timeout — yet the reported text asserts one specific diagnosis ("daemon up... queue is
wedged") regardless of which of those actually happened. If the daemon is not listening at all
(connection refused) the message still claims "daemon up," and if `config.yaml` fails to parse
the message still tells the reader to "restart ollama.exe" for what is actually a local config
bug. Given this exact file's repeated, explicit lesson about misdiagnoses sending runs down the
wrong remedy for hours (the `model calls per hour` order text rewrite documented a few hundred
lines above this), a HIGH-severity standard asserting a specific wrong cause is the same failure
mode in a smaller box.

### 5. address.py:94-114 — `spine_code_for()`'s fallback matching resolves on first/most-generic match, not most-specific, so a short index entry can shadow a correct, more specific match present in the same index  [severity: MAJOR]
```python
w_target = _worded(source_name)
if w_target.strip():
    for name, code in codes.items():
        w_name = _worded(name)
        if w_target in w_name or w_name in w_target:
            return code                      # <- first hit wins, by dict order
...
target_tokens = _token_set(source_name)
if target_tokens:
    best, best_overlap = None, 0
    for name, code in codes.items():
        name_tokens = _token_set(name)
        ...
        coverage = overlap / min(len(target_tokens), len(name_tokens))
        if coverage >= 0.8 and overlap > best_overlap:
            best, best_overlap = code, overlap
```
The word-boundary loop returns on the *first* index entry whose whole-word form is contained in
either direction — not the longest/most specific one — and the token-overlap loop's `coverage`
is normalized by the *smaller* of the two token sets, so any short, generic single- or two-word
index entry (the index has 125 such entries, e.g. `'DC' -> II.D.2`, `'ARMS' -> II.P`, `'Alien' ->
II.N`, `'Doom' -> II.N.2`) reaches `coverage == 1.0` against **any** longer target name that
happens to contain that one word, regardless of how unrelated the rest of the name is. Verified
by direct execution against the live module and its real `data/CHARTER_SPINE_CODES.json`:
```
spine_code_for("Sword Coast Adventurer's Guide DC Edition Reprint") -> "II.D.2"   (DC Comics)
```
even though `"Sword Coast Adventurer's Guide"` is itself an index entry mapped to the *correct*
`II.L.7` — the loop reaches `'DC'` first in dict-iteration order and returns immediately, never
reaching the correct, more specific match sitting later in the very same dict. This is the same
harm class the docstring immediately above (lines 64-84) documents fixing and "verified against
all 215 roll entries before and after" — that verification covered the 215 *current* roll names
only (confirmed: running `spine_code_for` over every name in `data/SWEEP_ROLL.json` today
produces no live misroute), so the general mechanism remains open for any future or renamed
source whose title happens to contain a short index entry's word — exactly the invented-address
harm Hard Rule 2 exists to prevent, and the module's own docstring says a false hit here is worse
than a miss because it never reaches `unassigned_sources.md` for owner sign-off.

### 6. suppressions.py:130,139-146 — the `--list` CLI flag is parsed but never read  [severity: MINOR]
```python
ap.add_argument("--list", action="store_true")
ap.add_argument("--check", action="store_true", ...)
a = ap.parse_args()
if a.check:
    ...
rows = active()
...
```
`a.list` is never referenced anywhere after `parse_args()`. Omitting `--check` already prints the
active-suppressions listing unconditionally, so `--list` does nothing whether passed or not — a
flag that looks like it gates behavior but is dead.

### 7. endpoint.py:236 — `exists_raw()` has no callers anywhere in the repository  [severity: INFO]
```python
def exists_raw(host, titles, workers=2):
    """Which of these titles the host actually serves. The raw-mode answer to a titles probe."""
    return sorted(fetch_raw(host, titles, workers=workers))
```
A repo-wide grep for `exists_raw` finds only this definition. `hostcheck.py` and `feats.py` both
call `fetch_raw()` directly for the same purpose. Dead code; reporting per the brief rather than
assuming it is safe to delete.

### 8. chord_field.py — the whole module is never imported anywhere in the repository  [severity: INFO]
A repo-wide grep for `import chord_field` / `from chord_field` finds no hits outside the file
itself; `derivation.py`'s only reference is the bare string `"chord_field"` inside a list of
module names (line 477), not an actual import. So `ADJUDICATIONS`, `total_beta()`,
`per_system_beta_without_unification()`, `landauer_floor()`, `recoil_momentum()`,
`recoil_velocity()`, and `critical_power_self_focus()` are all unreachable from any running
pipeline today. Two prior sweeps (sweep31 batch15, sweep32 batch10) read this file and called it
"clean," which it is on correctness — the formulas check out (Kerr self-focusing, Landauer bound,
E=pc recoil) — but neither flagged that nothing calls it. Reporting per the brief's dead-code
category; this may well be intentional standalone reference material (the file reads as the
charter's physics adjudication made checkable, not as pipeline plumbing), which is why it is
INFO, not a defect claim.

## QUESTIONS

1. **standards.py:1203-1229** — "the local model has a live runner" standard is wrapped in
   `if resident:`, so when Ollama's `/api/ps` reports zero resident models (or fails to answer at
   all, `resident = None`), the standard is not appended to `check()`'s output at all — it simply
   does not appear on the page. This file explicitly fixed the identical failure mode twice
   elsewhere in the same function ("the library's counters are moving," line ~880-901, and "every
   running job is advancing" via `job_stamp`), both times citing "a standard that does not emit is
   worse than one that fails." Is the empty/no-answer case here deliberately excluded because a
   fully-down daemon is caught by `ollama_token_flow()`'s own probe instead, or is this an
   unfixed instance of the same lesson? Settling it needs knowing whether "zero resident models"
   is ever a normal transient state this project expects to see mid-run (between generations) or
   always means something is wrong.

2. **render.py** — `view()` / `children_of()` / `containment_svg()` have no callers anywhere else
   in the repository; the module is only reachable through its own `--write` CLI entry point. Is
   this deliberately a standalone diagnostic/generator tool (consistent with several other `src/`
   modules that are primarily invoked as scripts), or is it infrastructure written ahead of an
   integration that has not happened yet — similar to the Registry Terminal integration the
   project's own CLAUDE.md flags as "not wired up... not done for you"? If the latter, it is not
   a fault, just unfinished wiring worth tracking.

## CLEAN

- **repass_bands.py** — read in full. Correctly checks `PL.write_record()`'s return value before
  counting a source as rewritten (the fix for exactly the failure mode found live in
  `suppressions.py` above, finding 2). No mutation-through-a-disconnected-`or {}`-default bug
  despite the `syn = rec.get("synthesis") or {}` pattern (verified: the only path that would
  matter, `band` being truthy off an empty `syn`, cannot occur). No findings.
- **chord_field.py** — correct on its own terms (formulas verified); see finding 8 for the
  dead-code note, which is a reporting obligation under the brief rather than a correctness
  defect.
- **render.py** — no correctness, silent-failure, or contract-drift findings; see question 2
  above for an open integration question rather than a fault.
