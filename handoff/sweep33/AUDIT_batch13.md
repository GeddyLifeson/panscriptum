# Batch 13 — run33
Modules read: assay.py (868 lines), derivation.py (558 lines), custodes.py (418 lines),
escalation.py (308 lines), feats_index.py (263 lines), autostart.py (218 lines), halo.py (178 lines)

## FINDINGS

### 1. escalation.py — "cannot be cleared programmatically" is enforced by a literal-string grep, not a runtime guard  [severity: BLOCKING]
escalation.py's own module docstring (lines 31-36) and CLAUDE.md's Hard Rule -1 both assert this
as an absolute: "It cannot be cleared programmatically -- `clear()` demands a written ruling...
and `verify_math` asserts that no module in `src/` calls it." I traced the actual enforcement
(it lives in `drill.py`, not `verify_math.py` -- see finding 2) and read it directly:

```python
def _no_programmatic_clear():
    src = os.path.dirname(os.path.abspath(__file__))
    for f in sorted(os.listdir(src)):
        if not f.endswith(".py") or f in ("escalation.py", "drill.py"):
            continue
        with open(os.path.join(src, f), encoding="utf-8") as fh:
            t = fh.read()
        if "escalation.clear(" in t or "ESC.clear(" in t:
            return False
    return True
```
This is a static substring scan for exactly two spellings. It does not stop, and cannot detect,
`import escalation as X; X.clear(...)`, `from escalation import clear; clear(...)`,
`getattr(escalation, "clear")(...)`, or any dynamically-built call. Nothing in `escalation.py`
itself prevents `clear()` from being called by any module that imports it under a different name
-- the function is a normal public callable with no runtime access check. The "asymmetry" the
project treats as its central safety property (raise is easy, lift requires a person) is
therefore enforced only against two known spellings, not against the capability itself. This is
a verification finding about an existing gap, not a proposal to touch `clear()` or `escalate()`.

### 2. escalation.py:34 — docstring misattributes the no-programmatic-clear check to `verify_math`  [severity: MINOR]
> "`clear()` demands a written ruling and records who gave it, and `verify_math` asserts that no
> module in `src/` calls it."
I grepped `verify_math.py` for any check on `escalation.clear` / lifting the halt and found none
(only unrelated `dict.clear()` calls and the `assert_clear` naming-collision checks). The actual
check (`_no_programmatic_clear`, see finding 1) lives in `drill.py`. The safety property is
enforced somewhere, just not where this module's own comment says it is -- a reader who goes to
`verify_math.py` to confirm the claim will not find it there.

### 3. assay.py:496-531 — `calibration_report()` mutates the shared global `SIGMA_BY_ATTESTATION` with no lock, the exact bug class this file documents fixing elsewhere  [severity: MAJOR]
```python
saved = SIGMA_BY_ATTESTATION["Witnessed"]
try:
    s = max(AXIS_MIN + 0.5, saved - 2.0)
    while s <= min(SIGMA_MAX, saved + 2.0):
        SIGMA_BY_ATTESTATION["Witnessed"] = s
        if assay(...)["interval"] == CHARTER_KENSHIRO_INTERVAL:
            ...
        s += 0.005
finally:
    SIGMA_BY_ATTESTATION["Witnessed"] = saved
```
This sweeps ~800 iterations (0.005 step over a ~4-unit range), mutating the module-global sigma
table that every concurrent call to `assay()`/`_interval()` reads, restoring it only in
`finally`. `assay.py`'s own comment at lines 603-607 describes fixing precisely this pattern for
`WEIGHTS`: "custodes' axis-emphasis readings used to mutate the module-global WEIGHTS under a
try/finally -- correct alone, silently wrong the moment any other thread called assay() mid-
window." `calibration_report()` still does that to `SIGMA_BY_ATTESTATION`. It is called from
`dashboard.py` (`_AS.calibration_report()`, one call site, confirmed by grep -- dashboard.py is
outside this batch so I did not read it in full) and from `drill.py`'s safety-net battery. If
either runs while any other process/thread calls `assay()` concurrently (e.g. a generation job
scoring an entity via `magnitude.py` while the dashboard renders), that concurrent call will
transiently score against a wrong, sweep-in-progress Witnessed sigma -- corrupting a published
interval for the duration of an ~800-iteration loop.

### 4. assay.py — three functions are dead code  [severity: MINOR]
`band_for_quantity()` (line 232), `interval_from_hands()` (line 819), and `null_instrument()`
(line 736) are exported but never called anywhere in `src/`. Grepped the whole tree for each
name: `band_for_quantity` appears only inside a comment in `feats.py` ("assay.band_for_quantity()
can place them on the ladder"), never an actual call; the other two have no references outside
their own definitions.

### 5. assay.py:703-714 — `instrument()`'s grade-lookup has an unreachable branch  [severity: MINOR]
```python
grade_n = max(0, LADDER.index(anchor) - 5)
grade = ["", "I", "II", "III", "IV", "V"][grade_n] if grade_n <= 5 else "V"
```
`LADDER` has 11 entries (M0..M10), so `LADDER.index(anchor)` is 0-10 and `grade_n` is clamped by
`max(0, ...)` to the range [0, 5] for every possible anchor. `grade_n <= 5` is therefore always
true and `else "V"` can never execute -- a tautological guard (category: a check that cannot
fail). Harmless as written, but it is the shape this project's own comments elsewhere warn about.

### 6. autostart.py:121-145, 157 — the duplicate-watchdog guard fails open on error, and only runs once  [severity: MAJOR]
```python
def _twin_watchdog():
    ...
    try:
        out = subprocess.run(["powershell", ...], ...).stdout
    except Exception:
        silence.note("autostart.py:131")
        return False        # <- "no twin found", proceeds
    ...
```
called as:
```python
def watch(read_hours=10):
    if _twin_watchdog():
        ...
        return
    ...
    while True:
        ...
```
The module's own docstring explains why this function exists: "Three of these once ran at once
-- the logon .vbs copy, a shell relaunch, and a PowerShell relaunch -- ... the whole arrangement
respawned itself in a loop." The guard against exactly that is a single PowerShell
`Get-CimInstance` call made ONCE, at watchdog startup, and any exception from it (a transient
PowerShell hiccup, a permissions issue, WMI being slow to answer at boot) makes the function
return `False` -- "no twin," proceed -- rather than refusing to start. Because the check runs
only before entering the `while True:` loop and never again, a single transient failure at boot
permanently disables the one guard that exists specifically because this failure mode already
happened once.

### 7. autostart.py:31 — dead module constant  [severity: MINOR]
`_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)` is computed at import time and never read.
`start_supervisor()` (line 115) and `_twin_watchdog()` (line 130) each independently recompute
the same expression instead of using it. Not a correctness bug (both call sites do apply
`CREATE_NO_WINDOW` correctly), just an unused binding.

### 8. feats_index.py — `host_to_sources()` and `load_index()` cache by function identity, ignoring their own path arguments  [severity: MINOR]
```python
def host_to_sources(path=WIKI_HOSTS):
    if _CACHE["hosts"] is not None:
        return _CACHE["hosts"]
    ...
```
and the equivalent for `load_index(root=READFEATS)`. Both accept a path/root override but cache
under a single global key that does not include it. Calling either function twice with two
different paths in the same process returns the first call's result both times. I grepped every
caller in `src/` (`manifest_builder.py`, `entity_match.py`, `verify_math.py`) and none pass a
non-default argument today, so this is latent rather than triggered -- but the signatures invite
exactly the misuse the cache would then silently get wrong.

## QUESTIONS

1. **custodes.py is not imported by the production generation pipeline.** The module's own
   docstring (lines 47-52) states, in the present tense, what it "buys": "Before this module,
   assay() computed ± from a hardcoded dict... After it, the ± is a MEASURED DISPERSION of ten
   independent readings." I grepped every `import custodes` in `src/` and found exactly two:
   `anchors.py` (a validation/demo script) and `verify_math.py` (the test suite). `magnitude.py`
   -- confirmed by its own docstring to be the real "Charter Part Three... run against mined
   source text" pipeline -- calls `A.assay()` directly and never imports `custodes`. So for any
   entity actually scored by the live pipeline, the published interval is still the hardcoded
   attestation-grade lookup the docstring says this module replaced. Is `custodes.py` mid-
   integration (wiring into `magnitude.py` still pending), or is it intentionally a separate
   audit/validation instrument that was never meant to replace the per-entry interval in
   production? I did not read `magnitude.py` in full (outside this batch) so I can't rule out a
   wiring path I didn't see.

2. **assay.py:444 -- `_check_scores()` checks `v is NONE` (identity) while `INAPPLICABLE` and
   `UNESTIMABLE` are checked with `in` (value equality).** I traced the one production call site
   that builds the NONE sentinel (`magnitude.py:348`, `scores[ax] = {"none": A.NONE, ...}`) and
   confirmed it always assigns the actual `A.NONE` object, so the identity check doesn't
   misfire today. But it's a fragile pattern: any caller that constructs the literal string
   `"none"` itself (e.g. from a JSON worksheet not routed through `magnitude.py`'s normalizer)
   would fail the identity check, fall through to the "not a number" branch, and get an
   `AssayIntegrityError` for a legitimately-marked absence. Is the identity check deliberate
   (forcing every caller to go through `assay.NONE` rather than a raw string), or an oversight
   that happened to not matter because only one caller builds this value today?

3. **escalation.py's `escalate()` has no minimum-content check on `what` (the reason), unlike
   `clear()`'s ruling (which must be a real sentence, >= 12 characters).** `"what": str(what)` at
   line ~138 accepts an empty string. Given CLAUDE.md's Hard Rule -1 states "every raise carries
   a reason" as an invariant, should `escalate()` reject an empty/whitespace `what` the way
   `clear()` rejects a short ruling -- or is this asymmetry intentional, since OPERATOR/SUPERVISOR
   -level refusals are meant to stay lightweight and unrestricted (only the OWNER-level lift is
   meant to be hard)? I am not proposing this change myself, since it would make raising a halt
   marginally harder rather than easier, per the brief's instruction not to touch that side.

## CLEAN
- **derivation.py** — read in full and additionally executed (`python src/derivation.py`): the
  112-entry ledger graph closes with no dangling parents, no rootless derivations, no cycles.
  Cross-checked every public function (`check_graph`, `depth`, `provenance`, `scan_constants`)
  against its actual callers in `rigor.py` and `verify_math.py` — all are used. Nothing found.
- **halo.py** — read in full. All three ROSTER entities carry all 11 axes consistently, `compute()`
  and `main()` have no unguarded paths that don't already exist elsewhere in this batch's
  findings, and the file is otherwise a straightforward data module. Nothing found.

---
Coverage recorded separately via `sweep_plan.record('run33', [...], batch=13)`.
