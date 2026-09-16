# sweep60 batch 08 audit

Modules read in full (6,660 lines total, per the assignment):
`src/cascade_bridge.py` (2334), `src/sweep_plan.py` (1150), `src/derivation.py` (813),
`src/runguard.py` (660), `src/catalogue_codex.py` (516), `src/hosts.py` (425),
`src/deprecated/catalogue_local.py` (334), `src/halo.py` (220), `src/repass_bands.py` (215).

All nine were read start to end, no sampling. This is a heavily self-audited part of the tree —
nearly every function carries a comment describing a bug that was already found and fixed here in
a prior sweep ("order ..." / "run #N" citations throughout). That history is real evidence the
files have been gone over hard already, and it shows: I did not find a fresh instance of the
project's signature "check that cannot fail" defect in live, reachable code in this batch.

## Findings

### 1. `derivation.py:644-652` — unguarded file read can crash the constant-scanner (MEDIUM, verified)

```python
def scan_constants_with_reason(mod):
    path = os.path.join(HERE, mod + ".py")
    if not os.path.exists(path):
        return None, "absent"
    with open(path, encoding="utf-8") as f:
        src = f.read()
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        ...
```

The `open(...).read()` call has no error handling of its own — only the subsequent `ast.parse`
is wrapped in `try/except SyntaxError`. If any `.py` file under `src/` (including
`src/deprecated/`, which this function now walks per the `SCAN_MODULES` fix at line ~596)
contains a byte sequence that is not valid UTF-8, `f.read()` raises `UnicodeDecodeError`
*before* reaching the try block, and that exception is not caught anywhere in the call chain —
`main()`'s loop (`for m in SCAN_MODULES: cs, why = scan_constants_with_reason(m)`, line 787-788)
has no try/except around the call, so it would propagate out of `main()` and crash the whole
"derivation ledger" report.

This is inconsistent with the project's own established pattern for exactly this hazard:
`sweep_plan.py`'s `modules()` (line 92) opens every `.py` file in `src/` with
`errors="replace"` specifically so an encoding problem in one file degrades gracefully rather
than aborting the whole scan. `derivation.py` does the analogous walk without that guard.

I verified this by reading the function and its only caller in this file; I did not verify that
any file in `src/` actually contains invalid UTF-8 today (my own reads of files in this batch
all succeeded as UTF-8), so this is a dormant latent bug rather than one I watched fire — the
same "verified 2026-09-07: 0 mismatches today" caveat the file's own `parse_codex()` docstring
uses for a different dormant check.

### 2. `catalogue_local.py` — confirmed, but deliberately intentional dead code (not a bug)

Lines 96-334 (`import yaml` through `main()`/`if __name__=="__main__"`) are unreachable under
every invocation path: line 91-94 is
```python
if set(sys.argv[1:]) & {"-h", "--help"}:
    print(_REFUSAL)
    raise SystemExit(0)
raise SystemExit(_REFUSAL)
```
at *module* scope (not inside `if __name__=="__main__":`), so both branches raise `SystemExit`
before any of the code below it executes, whether the module is run as a script or merely
imported. I confirmed this by reading the whole file top to bottom: `load_cfg`, `slug`, `call`,
`catalogue_source`, and `main` cannot be invoked by any caller, including one that just imports
the module for introspection.

This exactly matches the audit's "dead code / functions nothing calls" category, but the file's
own header comment (lines 43-94) explains this is deliberate: the module is kept as a record of
a past failure mode ("catalogued Bleach's Yasutora Sado as 'Chad (Seraura Urahara)'") and the
refusal is intentionally placed at module scope specifically so *importing* it is as inert as
running it. Reporting this as confirmed-but-not-a-finding per the instructions' honesty
standard — it is dead code, but it is dead on purpose and says so.

### 3. `cascade_bridge.py:1654-1671` — eight guards on an always-true condition, explicitly documented as such (LOW / informational)

```python
if pinned is None:
    ...
    return None
# INVARIANT, STATED ONCE (order 8b0338b019ce): `pinned` is a non-None router Model from HERE
# to the end of this function ... Every `if pinned:` / `pinned and ...` guard below this point
# (there are eight) is therefore belt-and-braces, not a live condition; none of them can be
# False. That is deliberate, not dead code -- read them as documentation...
```
This is the textbook shape the audit brief calls out ("a guard on an always-true condition"),
and I verified by tracing control flow that the invariant claim is correct: every path that
could leave `pinned` as `None` returns immediately above this comment, so all eight later
`if pinned:` checks in `_ask_call` are indeed unconditionally true for the rest of the function.
Flagging it because it matches the pattern precisely, but this is the codebase's own doctrine
speaking, not a hidden bug — the comment is honest about what it is, and no correctness or
reporting logic depends on the guards ever evaluating False.

### 4. `catalogue_codex.py:105-116` — `slug()` is confirmed dead code, but says so itself (informational)

```python
def slug(s):
    """NOTHING IN THIS TREE CALLS THIS (order c158b93e2e07). Kept as a public helper;
    `record_path()` below is the entry point `main()` actually uses...
```
Verified: `main()` calls `record_path(r["name"], RECORDS)`, never `slug(...)`, and I found no
other caller of `slug` in this file. Same category as #2/#3 — noted because it matches the
"dead code" search, not reported as a defect, since the function's own docstring already states
the fact and the reasoning for keeping it.

### 5. `cascade_bridge.py:71-73` / `catalogue_codex.py:38-40` / `hosts.py:36-38` — self-read file handle not explicitly closed (LOW, unsure)

```python
_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")
```
This pattern (present verbatim in three of this batch's modules) opens the module's own source
file to scan for stray control characters but never closes the handle via `with` or `.close()`.
On CPython the object is closed immediately by reference-counting once the generator expression
finishes, so this is very unlikely to matter in practice on the interpreter this project uses —
flagging as "unsure" / cosmetic rather than a real resource leak, since I can't rule out a
non-CPython runtime or a future refactor that keeps a reference alive.

## Areas checked and found clean

- `cascade_bridge.py`'s classifier functions (`permanent_refusal`, `named_transient`,
  `client_rejection`, `local_transport`, `_size_refusal_permanent`, `retry_after_seconds`,
  `pool_exhausted`) — traced each regex/word-list against its stated purpose and ordering
  (`local_transport` and `client_rejection` checked before `permanent_refusal`, `_size_refusal`
  checked before the general transient-word scan). No tautologies, no fail-open gaps beyond
  the ones already documented and owner-ruled.
- `cascade_bridge.py`'s `dead_forever()` TTL/memo cache (lines 468-540) — traced the
  stamp-vs-cache logic for the None-stamp (file absent) case explicitly; it degrades correctly
  rather than caching "dead forever" past a file's disappearance.
- `sweep_plan.py`'s shard/CAS machinery (`record`, `_land_claim` analogue in `freeze_plan`,
  `covered_by`, `missing_detail`, `normalise_module`) — the completeness proof this whole file
  exists to provide traces correctly end to end; the `record()` call signature this task itself
  uses (`record(run, covered, batch=None)`) matches what's documented and callable.
- `runguard.py`'s ownership checks in `beat()`/`release()` and the digest-before-read compare-
  and-swap in `_land_claim` — both check `rec.get("agent") == agent` before mutating, and the
  CAS ordering (digest taken before read) is correct for the race it's built to close.
- `derivation.py`'s `check_graph()` cycle detector — traced the open/done state machine by hand
  for a two-node and a three-node case; a detected cycle does not get double-reported and does
  not cause the non-terminating walk the file's own history describes as m103's mirror bug
  (that bug is already fixed via the early `return 1` in `main()`).
- `catalogue_codex.py`'s collision reporting (`norm_clashes`, `ambiguous`, `reg_ambiguous`,
  `dupe_elements`, `unmapped_types`) and its roll-write gating — all traced through to their
  print statements and all are uncapped as claimed.
- `hosts.py`'s three-state `add()` return (`True`/`False`/`None`) and the CAS retry loop, and
  `discover()`'s distinguishing of "thin roster" / "probe raised" / "found and lost to a denied
  write" — all three sentinel paths are actually reachable and actually reported, not silently
  collapsed.
- `halo.py` and `repass_bands.py` are small and mostly data/reporting; no tautological checks,
  no silent truncation (both wrap-not-cut for evidence text), and the write-verdict gating in
  both (`silence.write_json` return value checked, non-zero rc on denial) is correct.

## Coverage note

`sweep_plan.record('sweep60', [...], batch=8)` was run after this report was written, recording
all nine assigned modules as covered.
