# SWEEP 34 — BATCH 15

Modules read end to end: `src/local_agent.py` (791), `src/publish.py` (671),
`src/binding_health.py` (487), `src/address_space.py` (383), `src/entity_match.py` (296),
`src/tempus.py` (254), `src/axis_correlation.py` (211), `src/ledger.py` (136).

Every finding below was verified against the source and, where the claim is about behaviour or
about data on disk, reproduced against the live tree with the miniconda interpreter. Nothing here
is "as reported". Anything that could be deliberate design is filed as a QUESTION, not a finding.

`publish.py` was never executed in any mode. The standing `--push --loop 10` daemon was not
touched. The HALT was neither read as breakage nor altered.

Two findings already filed by other agents are excluded: `address_space.py`'s hyperverse claim
against `data/TIERS.json`, and the three permanently-unresolvable BINDING_SUSPECT hosts.

---

## 1. `src/local_agent.py`

The one lane that lets a model write into `src/`. One BLOCKING finding: the last gate in the
chain cannot fail for a whole class of regressions.

### F1 — BLOCKING. The whole-suite gate passes when verify_math reports 10, 20, 30 … FAILED

`_gates()`, line 498, the final gate every applied patch must clear:

```python
    r = subprocess.run([PY, os.path.join(HERE, "src", "verify_math.py")], ...)
    if "0 FAILED" not in (r.stdout or ""):
        return "verify_math regressed"
```

`verify_math.py:4625` prints `RESULT: {len(PASS)} passed, {len(FAIL)} FAILED`. The zero in
`"0 FAILED"` is just the last digit of M:

```
    0 -> True      1 -> False
   10 -> True      7 -> False
   20 -> True
  100 -> True
```

So a model-authored patch that breaks a round number of invariants is KEPT, and the gate reports
that it passed. `foreman._checks_pass` had this identical bug, found and fixed 2026-08-23, and its
fix comment names the consequence exactly: *"This is the gate that decides whether a model-authored
patch to live source is KEPT or REVERTED, so the false positive kept exactly the patches that broke
a round number of checks."* `foreman.py:977-990` now parses the number with a regex and also refuses
when no result line is readable. `local_agent._gates` was never given that fix.

Note the other direction is safe: a verify_math that crashes emits no `"0 FAILED"` and the gate
fails closed. Only the round-number case fails open.

This is a defect that makes the write gate EASIER to pass, so it is BLOCKING per the batch brief.

### F2 — MINOR. The blast-cap escalation is swallowed by a bare `pass`

Lines 578-584:

```python
    _ok, _why = _blast_ok(full)
    if not _ok:
        try:
            import escalation as _ESC
            _ESC.escalate(_ESC.MANAGER, "LOCAL_AGENT_BLAST_CAP", _why, who="local_agent")
        except Exception:
            pass
        return {"applied": False, "error": _why}
```

The refusal itself still happens, so this is not a gate hole. But every other escalation site in
this file records the swallow (`silence.note("local_agent.py:revert-escalate")` at line 665), and
this one does not — so a broken `escalation.py` makes the runaway signal vanish with no trace in
the failure ledger. The blast cap exists precisely because the enumerated gates will be bypassed a
sixth time; its alarm should not be the quiet one.

### F3 — MINOR. Model-controlled `**args` can kill the run with a TypeError

Lines 761-767:

```python
            if fn == "propose_patch":
                res = t_propose_patch(apply=apply, log=patches, **args)
            elif fn in impl:
                res = impl[fn](**args)
```

`args` is whatever the model emitted. A model that emits `{"apply": false, ...}` raises
`TypeError: got multiple values for keyword argument 'apply'`; one that omits a required `path`
raises `TypeError: missing 1 required positional argument`. Neither is caught — only `_chat` is
wrapped — so a malformed tool call terminates `run()` with a traceback instead of handing the model
`{"error": ...}` and letting it correct itself. Every other bad input in this file is answered with
an error dict.

### F4 — MINOR. Refused patches leave no trace in the audit trail

`entry` is created and appended to `log` at line 617, *after* six early returns: no-such-file
(line 528), module/path denylist (554), the writable-surface allowlist (560), the protected-region
prefixes (569), the blast cap (584) and the find-count check (588). So a model that repeatedly
attempts to patch `foreman.py` produces a `patches` list that is empty. The comment at 607-616
argues at length that *"A record of intentions is not an audit trail"* — the complementary gap is
that a record of accepted intentions is not one either. The console line at 769 is the only
evidence, and it is `stdout`, not the trail the run returns.

---

## 2. `src/publish.py`

Two BLOCKING findings. This is the module whose failures are irreversible and outward-facing.

### F5 — BLOCKING. The last-moment secret scan silently skips every file over 2 MB, and four published files are over 2 MB

`scan_for_secrets`, lines 272-294:

```python
def scan_for_secrets(root, max_bytes=2_000_000):
    ...
            try:
                if os.path.getsize(p) > max_bytes:
                    continue
```

`push()` calls it with the default: `leaks = [h for h in scan_for_secrets(SITE) ...]` (line 531).

`COPY_DIRS = ("src", "prompts", "reference", "registry_terminal", "handoff")`. Measured against the
live tree, four files inside those directories exceed the cap:

```
  3,363,987   reference/keystone_volumes/LOCAL_REGISTER.json
  2,969,665   reference/keystone_volumes/LOCAL_REGISTER_CITATIONS.md
  2,684,708   registry_terminal/PANSCRIPTUM_TERMINAL.html
  2,470,102   registry_terminal/lex2.js
```

All four are copied by `sync_tree` and pushed to the PUBLIC repo, and lock three reads none of
them. The skip is total and silent: no hit, no count, no `silence.note`, nothing in the refusal
message to say that 11.5 MB of published content was not examined. The docstring says this lock
exists to *"read what is about to be PUBLISHED, not what we meant to publish"*, and for the four
largest published artifacts it reads nothing at all.

Locks one and two cannot cover the gap: `_scrub` runs on the snapshot dict, and the docstring
itself says *"a file copied wholesale (`COPY_FILES`, `COPY_DIRS`) never passes through `_scrub` at
all"*.

### F6 — BLOCKING. The mutation-lock guard is still behind `except ImportError: pass`

Lines 508-527 — the third arm the brief predicted:

```python
    try:
        import mutate as _MUT
        _busy, _rec = _MUT.active()
        if _busy:
            raise RuntimeError(
                "REFUSING TO PUSH: a mutation run is active, ...")
    except ImportError:
        pass
```

`src/mutate.py` exists today and `def active()` is at line 168, so the guard currently works. But a
deleted or renamed `mutate.py`, or one whose own imports fail, raises `ModuleNotFoundError` (an
`ImportError` subclass) and this switches the guard off with no print, no `silence.note` and no
escalation — while the comment eighteen lines above goes on describing the incident it prevents:
a push that *"landed in the middle of a mutation run and shipped a `prose_gate.py` whose
`cited_fraction()` matched every source EXCEPT the one it was asked about. To GitHub."*

The two sibling arms in this same file were both converted to fail-closed today, and each carries
the reasoning that applies verbatim here: the `ledger_guard` import at 496-504 raises
`RuntimeError("REFUSING TO PUSH…")`, and the `escalation` import at 596-607 raises
`SystemExit("REFUSING TO START…")`. This one was left behind. A push that cannot ask whether the
source tree is deliberately corrupt has no business pushing.

(Other exception types do fail closed here: a `SyntaxError` in `mutate.py`, or an `AttributeError`
from a renamed `active()`, propagates and aborts the push. Only the missing-module case is open.)

### F7 — MAJOR. `FIXTURE_MARKER` silences a whole multi-line string, which the comment says it cannot

Line 224, describing the marker:

```
# ... The marker must be on the same line, so it cannot silence a region.
```

`scrub_text`, line 256-258:

```python
def scrub_text(s):
    if FIXTURE_MARKER in s:
        return s
```

That tests the whole string, not a line. Reproduced:

```
  multiline value, marker on line 1, "ghp_AAAA…" on line 2  ->  returned unscrubbed
  the same token on its own                                 ->  "[redacted]"
```

`scan_for_secrets` does apply the marker per line (line 306), so the comment is true of lock three
and false of locks one and two. It matters because `json.dump(..., indent=1)` escapes newlines, so
a multi-line snapshot value becomes ONE line in `docs/state.json` — a line carrying the marker,
which lock three then also skips. A value carrying both the marker and a real key therefore clears
all three locks.

### F8 — MAJOR. A held push is reported as "no change to push", and exits 0

`push()` returns bare `False` from two unrelated states:

```python
    porcelain = git("status", "--porcelain")
    if not porcelain:
        return False                      # line 550 — genuinely nothing to publish
```

```python
        print("push held: rebase onto origin/main failed (" + str(e)[:120]
              + "); retrying next loop on a fresh tree", file=sys.stderr)
        return False                      # line 585 — committed, NOT pushed
```

and `main()` line 653 cannot tell them apart:

```python
                print("pushed" if push() else "no change to push")
```

So a commit that was made and could not land prints "no change to push" on stdout, and `rc` stays
0 — a one-shot `--push` by a person exits successfully having published nothing. The stderr line is
the only truthful signal. This is the same shape as the defect `main()`'s own comment at 638-646
was written to fix (*"A REFUSED PUBLISH MUST NOT REPORT SUCCESS"*), arriving one branch over.

### F9 — MINOR. An unreadable staged file is treated as clean

`scan_for_secrets`, lines 288-295:

```python
            except OSError:
                continue
```

A file the scanner cannot open is skipped with no note and no hit. For a scanner whose whole
premise is that it reads what actually reaches the public repo, "could not read" and "read and
found nothing" must not be the same answer. Same class as F5, smaller surface.

### F10 — MINOR. `SKIP_SUFFIX` is a hand-enumerated denylist on the publish path

Line 146:

```python
SKIP_SUFFIX = (".pyc", ".presilence", ".prebandfix", ".precapfix", ".prefix", ".prepool",
               ".preprobe", ".prewiden", ".prewindow", ".bak", ".tmp", ".orig")
```

with the comment above it recording that this list already failed once: *"seven of them were
sitting in src/ and being published to the PUBLIC repo because this tuple only knew about two
suffixes."* The remedy was to enumerate seven more `.pre*` names. The eighth backup suffix anyone
writes publishes a stale copy of a live module. `local_agent.py`'s own header states the principle
this violates — *"a DENYLIST fails OPEN — anything nobody thought of is permitted"*. No `.pre*`
file exists in `src/` right now, so this is latent, which is the condition under which all five
`local_agent` bypasses were also latent.

### F11 — MAJOR. `sync_tree` never deletes, so the export is append-only

`sync_tree` (lines 358-407) copies named files forward and removes nothing. A file deleted from the
live project — including one deleted *because* of what it contained — stays in
`$USERPROFILE/panscriptum-export`, is re-staged by `git add -A` on every cycle, and keeps being
published indefinitely. The docstring says *"Refresh the export copy from the live project"*, which
is only half of what a refresh is. (Verified from the source only; the export tree was not opened.)

---

## 3. `src/binding_health.py`

### F12 — MAJOR. The absent probe PASSES on a transport failure

Lines 234-247:

```python
def _probe_absent(host, timeout=25):
    ...
    try:
        import feats as F
        got = F.fetch(host, [ABSENT_PROBE])
    except Exception:
        return True, "no answer, which is the correct answer"
```

An exception is not a negative result. A 429, a connection reset, a DNS failure or any raise inside
`feats.fetch` is reported as the host *correctly refusing* a title nobody holds — and `verdict()`
then treats `ok_absent=True` as evidence: with a passing present probe the host is declared
`healthy`, and with a failing one the module never asks whether the host answers yes to everything.

This is the module's own founding confusion, reproduced inside the probe built to catch it. The
header states it plainly: *"the host is throttling us -> every fetch returns 429, which reads as
'empty'"*, and *"74 throttled probes came back as 0% and a repair pass unbound
`warhammer40k.fandom.com` from Warhammer 40,000 on the strength of it."* The sibling probe does not
make this mistake — `_fetch_chars` catches and returns the exception as a `problem` (lines 172-176),
and `_probe_reachable` returns `False` on a raise (lines 275-277). Only `_probe_absent` fails open,
and it gives no reason for doing so.

### F13 — MINOR. The success detail is tautological

Line 220-221:

```python
            return True, "%d chars from %r (candidate %d of %d tried)" % (
                n, t, len(tried), len(tried))
```

Both operands are `len(tried)`, so the line always reads "candidate 3 of 3 tried". The docstring
says the bound *"is reported in the detail rather than left implicit ... and the reader can see how
many were asked"* — the reader can see only that the last candidate tried was the last candidate
tried. The intended second number is presumably `PRESENT_CANDIDATES` or the candidate-list length.

### F14 — MINOR. Two probes take a `timeout` they never use

`def _probe_present(host, title, timeout=25):` (line 189) and
`def _probe_absent(host, timeout=25):` (line 234). Neither passes `timeout` to anything; both
delegate to `feats.fetch`, which is never given it. A parameter that reads as a control and controls
nothing.

### F15 — MINOR. `run(limit=)` truncates a sorted host list with no truncation flag

Lines 404-410:

```python
    hosts = sorted({h for h in hosts_map.values() if ...})
    if only:
        hosts = [h for h in hosts if h in set(only)]
    if limit:
        hosts = hosts[:limit]
```

`sorted(...)[:N]`. Operator-facing (`--limit`, default `None`), so this is the mild end of the
class — but the returned records and the `BINDING_HEALTH.json` this writes carry no marker saying
the sweep was partial, and `health.py` and `dashboard.py` both read that file. `entity_match.
candidates` faces the identical decision and carries a `truncated` flag for exactly this reason.

---

## 4. `src/address_space.py`

(The hyperverse-vs-TIERS.json finding is already filed and is not repeated.)

### F16 — MAJOR. A missing tier is silently addressed as tier ZERO and printed as a charted position

`assign()`, lines 275-276:

```python
    def fit(v, field):
        return (0 if v is None else int(v)) % (1 << WIDTHS[field])
```

Measured against the live data:

```
  TIERS.json rows                                209
  rows carrying at least one None tier           109
  WORLDSEEDS.json sources                         30
  of those, sources with a None tier               8
    'Baki'   -> hyperverse None, xenoverse None, metaverse None, multiverse 37
    'Bleach' -> hyperverse 4, xenoverse 0, metaverse None, multiverse 39
    ...
```

Each becomes `Ω › H0 › X0 › Mt.0 › Mv.37 › …`, and nothing distinguishes that from a source
genuinely charted into hyperverse 0. The module is explicit that this is the one thing it must not
do — the charter is quoted twice in this file: *"hyperverse position is uncharted; the Custodes
considered guessing a form of lying"*, and `shelfmark`'s docstring insists *"Nothing here guesses
… what prints is a measurement, not a filled-in blank."*

That docstring names the compensating warning:

> If TIERS.json is ever absent, `assign()` falls back to tier zero, and the note in `main()` says
> so out loud rather than letting a zero read as a survey.

The note it means is line 365, `if not tiers:` — it fires only when the whole file is missing, never
for a per-source or per-field gap. And this is not a `main()`-only path: `pipeline.py:1645` and
`profile.py:160` both call `AS.assign(desig, tiers.get(src) or {})`, so the zero-filled shelfmarks
reach the published record with no note anywhere.

`UNADDRESSED = None` at line 133 is commented *"a shelf in no hyperverse"* — the vocabulary for the
honest answer exists and is never used (see F18).

### F17 — MINOR. Three stale `silence.note` line tags

```
  line  84:  silence.note("address_space.py:69")
  line 128:  silence.note("address_space.py:112")
  line 342:  silence.note("address_space.py:293")
```

`silence.note(site)` records the label into `health.record(f"silent:{site}", ...)` — it is the
string a diagnostician navigates by, and all three point 15 to 49 lines above the `except` that
raised. `binding_health.py` and `axis_correlation.py` use symbolic tags (`":load"`,
`":load-matrix"`); this file uses symbolic form once (`":tiers"`, line 358) and numeric form three
times.

### F18 — MINOR. `UNADDRESSED` is dead

`grep -rn "UNADDRESSED" src/ --include=*.py` returns exactly one line, its own definition at
line 133. No reader, no writer, no test.

---

## 5. `src/entity_match.py`

No confirmed findings. The two shapes this batch was hunting are both handled correctly and
explicitly here, and it is worth recording that:

- `candidates(name, pool, limit=None)` caps only on explicit request, defaults to no cap, and sets
  `"truncated": True` when it does cap (lines 234-236). The docstring names Hard Rule 0.
- `qualifier_compatible` cannot be overruled by a score, and `similarity` never sees a qualifier.
- The two early returns carry the same key set as the normal path, fixed with the reasoning stated.

Questions only, below.

---

## 6. `src/tempus.py`

### F19 — MINOR. Two unused module constants, each a fifth copy of a physical constant

```python
SECONDS_PER_YEAR = 3.15576e7      # line 43
C_LIGHT = 2.99792458e8            # line 44
```

Neither appears anywhere else in `tempus.py`, and nothing imports them from `tempus`.
`cosmography.py:42`, `chord_field.py:35`, `descending_ladder.py:44` and `scale_theories.py:23` each
declare their own copy of one or both. `ledger.py`'s header states the rule these violate: *"A
literal copied by hand here would be a second, silently-drifting source of truth for one quantity —
which is the exact failure the derivation ledger exists to catch."*

### F20 — MINOR. `DEGENERATE_TIME` is dead

Defined at line 67 with four hand-written entries and cross-references. No reference anywhere in
`src/`, including `loop_report()` twenty lines below it, which re-states the Basement Loop and the
Rot City in prose rather than reading them from the table.

### F21 — MINOR. `apparent_lag_years` returns two different dict shapes

```python
    if not path:
        return {"lag_years": None, "note": "no shared furniture; ..."}      # line 90
    return {"distance": round(d, 4), "lag_years": P.arrival_years(d), "path": path,
            "note": "A sees B as B stood this many years ago"}
```

A caller reading `r["path"]` or `r["distance"]` unconditionally gets a `KeyError` on the branch
most likely to arrive from real data. `pipeline.py:1731` calls this in a loop over sources. This is
the identical defect `entity_match.candidates` was corrected for, with the same reasoning available
verbatim: *"ONE RETURN SHAPE, ALWAYS."*

---

## 7. `src/axis_correlation.py`

Never audited before. The measured numbers hold up; the guarantees around them do not.

**The header's data claims were re-derived and are exact.** Running `measure()` against the live
tree: 45 entities, 55 measurable pairs, mean r = +0.3193, n ranging 42 to 45, `reach|ruin` = +0.8161
(n=44), `continuity|sustain` = +0.7731, `continuity|reach` = +0.7562, `reach|sustain` = +0.6942.
`data/AXIS_CORRELATION.json` on disk matches the live computation field for field. All seven
`SOURCES` files exist. Every one of the 55 possible pairs over the 11 axes is measured, so the
`mean_r` fallback in `rho()` never fires against today's axis set.

### F22 — MAJOR. `rho()` returns 0.0 when the matrix is unreadable, under a docstring saying it must not

Lines 148-165:

```python
def rho(a, b, doc=None, default=None):
    """Correlation between two axes. -> float.

    THE DEFAULT IS THE MEASURED MEAN, NOT ZERO, and that is the entire point of this function.
    An unmeasured pair is a pair we know nothing about -- and "know nothing" must not resolve to
    the single value the data has ruled out. Falling back to 0.0 would silently restore the
    independence assumption for exactly the pairs with the least evidence behind them, which is
    the failure mode this module was written to end.
    """
    doc = doc or load()
    if not doc:
        return 0.0 if default is None else default
```

The line immediately below the paragraph does the thing the paragraph forbids. `load()` (lines
138-146) returns `None` on any exception, noted only via `silence.note`, so a missing or corrupt
`data/AXIS_CORRELATION.json` restores rho = 0 for *every* pair — not the low-evidence ones, all of
them — and `widening()` then returns a factor of 1.0 with `cov = 0.0`. The library goes back to
publishing the intervals the module header calls **1.78x too narrow** on the charter's own Kenshiro
worksheet, and says nothing.

The fail-open may well be the right call (see F23 for why it is defensible), but it must be stated
where it happens instead of denied there.

### F23 — MAJOR. The import-time guard that justifies the fail-open does not exist

`assay._rho` (`src/assay.py:561-567`) is the production consumer of this matrix, and it defends its
own `return 0.0` by naming a guard:

```
    ON THE FALLBACK. If the matrix is missing entirely this returns 0.0 -- the independence
    assumption -- and that is the WRONG answer, deliberately chosen: ... It must not stay silent
    about it, and it does not: `_check_constants` refuses at import time if the matrix is absent
    when it should be present, and a drill net attacks it.
```

`_check_constants()` is `src/assay.py:473-496`. It verifies three things, all about the sigma
table: that the attestation sigmas are strictly increasing, that `SIGMA_UNKNOWN` is not below the
widest grade, and that no sigma exceeds `SIGMA_MAX`. It never opens, mentions or checks the
correlation matrix. `grep -n "AXIS_CORRELATION" src/*.py` returns three lines — two in
`axis_correlation.py` itself and one comment in `verify_math.py`. There is no import-time refusal
anywhere.

Half the claim is true: `drill.py:2384-2394` does net it —
`measures_are_not_independent()` returns `False` when `AC.load()` is falsy. So the loss is not
total; it is that the guarantee is a drill run away rather than at import, while the docstring
promises the strong form. The rho = 0 fallback is a decision resting on a safety that was never
built.

### F24 — MINOR. The header's correlation table skips two ranks inside what reads as a top five

The module header presents:

```
    reach x ruin              r = +0.816   n = 44      <- the suspected pair, confirmed
    continuity x sustain      r = +0.773   n = 42
    continuity x reach        r = +0.756   n = 44
    reach x sustain           r = +0.694   n = 43
    acumen x discernment      r = +0.653   n = 44
    ...
```

Re-derived from the live data, the true descending order is:

```
  1 reach|ruin                0.8161  n=44
  2 continuity|sustain        0.7731  n=42
  3 continuity|reach          0.7562  n=44
  4 reach|sustain             0.6942  n=43
  5 continuity|suasion        0.6887  n=44      <- omitted
  6 reach|transgression       0.6679  n=45      <- omitted
  7 acumen|discernment        0.6534  n=44      <- printed as if it were 5th
```

Every quoted value is correct; the ORDER is not, and the `...` after the fifth line asserts that the
five above it are the top five. A reader reconstructing the ranking from the header gets a different
list than `main()` prints.

### F25 — MINOR. `main()` raises when there is not enough data to measure anything

Line 202:

```python
    print("   %d pair(s) measured, mean r = %+.4f" % (doc["measured_pairs"], doc["mean_r"]))
```

`measure()` sets `"mean_r": ... if vals else None` (line 128). With fewer than `MIN_N = 4`
co-scored entities on every pair, `vals` is empty and this raises
`TypeError: unsupported format string passed to NoneType.__format__` — the report crashes in exactly
the state where a reader most needs it to say "nothing measurable yet". The two lines below it guard
correctly (`if doc["mean_r"] and ...`).

### F26 — MINOR. A missing source file is skipped silently

Lines 76-78:

```python
        p = os.path.join(HERE, rel)
        if not os.path.exists(p):
            continue
```

All seven `SOURCES` exist today. If one is renamed, the matrix silently shrinks — fewer entities,
different correlations, a different `mean_r` — and neither `measure()`'s return nor
`AXIS_CORRELATION.json` records how many of the seven were actually read. For a file the header
calls the covariance term inside *"every published interval in the library"*, the provenance of the
sample should travel with the number.

---

## 8. `src/ledger.py`

Arithmetic verified: `JOULES_PER_STANDARD` is `2.14e8` exactly, matching the header and
`physics.MATERIAL["rock"]["pulv"]`. `cross_rate(a, b) == rb/ra` is correct for the "units per
Standard" convention (1 gil = 1/120 §; `cross_rate("gil","gold pieces") = 25/120 = 0.208` gp, which
is right). `to_standards`/`from_standards` round-trip.

### F27 — MINOR. At the top band, `ruin_score` is silently ignored

`assay_to_standards`, lines 130-134:

```python
    i = LADDER.index(magnitude_band)
    lo = BAND_EDGES[magnitude_band]["ruin"]
    hi = BAND_EDGES[LADDER[min(i + 1, len(LADDER) - 1)]]["ruin"]
    joules = math.exp(math.log(lo) + (ruin_score / 10.0) * (math.log(hi) - math.log(lo)))
```

For `M10`, `min(11, 10) == 10`, so `hi is lo`, the log range is zero, and the interpolation collapses.
Reproduced:

```
  M10 ruin=0.0   -> standards 4.672897196261646e+90
  M10 ruin=5.0   -> standards 4.672897196261646e+90
  M10 ruin=10.0  -> standards 4.672897196261646e+90
  M9  ruin=0.0   -> standards 4.67289719626174e+76
  M9  ruin=10.0  -> standards 4.672897196261646e+90
```

A parameter that spans fourteen orders of magnitude at every other band is inert at the top one, and
the returned dict says nothing about it. `tempus.band_resolution` faces the same "M10 has no band
above it" problem twelve lines of docstring further down and handles it deliberately (*"M10 …
inherits the M9->M10 width; saturation at the ceiling is a property of the Ladder, not a licence to
invent an edge"*). `ledger` inherits nothing and clamps to a point.

### F28 — MINOR. An unlisted currency is indistinguishable from a deliberately non-convertible one

Lines 87-98:

```python
    rate = CURRENCIES.get(currency, (None, "unlisted"))[0]
    if rate is None:
        return None
```

Reproduced: `to_standards(100, "quatloos")` returns `None`, and so does
`to_standards(100, "poneglyph-grade favour")`. The second is a considered doctrinal statement — the
table's own entry explains *"A market cannot price what one party has criminalised knowing"* — the
first is a typo. A caller writing an Aperture Doctrine Position Paragraph cannot tell them apart,
and would print "not convertible" for a misspelling. The `"unlisted"` reason string is constructed
and then discarded by the `[0]` subscript on the same line. `entity_match.py`'s header names this
exact failure: *"a function that returns `[]` for 'failed' and `[]` for 'genuinely nothing' has
destroyed the distinction its caller needs."*

---

# QUESTIONS

Things that may be deliberate, or that I could not settle from the source. None filed as orders.

**Q1 — `publish.py`, entropy threshold.** `SECRET_ENTROPY_BITS = 4.0`, and a 16-character value with
all-distinct characters has entropy exactly `log2(16) = 4.0`. Was the boundary meant to be
inclusive at the minimum-length case, or is 4.0 chosen for longer strings and the 16-char minimum
independent?

**Q2 — `publish.py`, suppression granularity.** `suppressions.suppressed("secret_scan", rel)` is
keyed on the FILE, and a match suppresses every line in it (line 300-310). One waived line waives
the whole file thereafter. Intended, or should the suppression carry a line?

**Q3 — `publish.py`, path separators in hits.** Suppressed hits record `rel_for_supp` (forward
slashes, line 297); real hits record `os.path.relpath(p, root)` (backslashes on this platform,
lines 313/318). Harmless today, but they are the same field in the same list.

**Q4 — `address_space.py`, the missing `star` field.** `FIELDS` has eight entries; `shelfmark()`
prints seven — `star` (27 bits) never appears. That matches the charter's own notation
(`Ω › H? › X? › Mt › Mv › U › G › P`), so it looks deliberate. The consequence is that two worlds
differing only in `star` share a shelfmark, and `seed_from_card` keys terrain on
`name|endonym|shelfmark`. Is the star deliberately unpublished, or was the field added to the
address without being added to the notation?

**Q5 — `address_space.py`, the collision count.** `main()` prints
`collisions : {len(addrs) - len(set(addrs.values()))}` and nothing consumes it — no threshold, no
escalation, no non-zero exit. A number worth computing that nothing acts on.

**Q6 — `entity_match.py`, ties in `best()`.** `best()` returns `r["matches"][0]` when it scores
`>= STRONG`, with no signal that a second candidate tied. `local_agent.t_find_symbol` treats exactly
this ambiguity as the thing worth reporting (*"it cannot disambiguate what it was never told was
ambiguous"*). Should `best()` refuse, or flag, a tie at the top?

**Q7 — `entity_match.py`, callers.** The only importer in `src/` is `verify_math.py:2152`. The
header says so and calls it a seam held shut on purpose. Confirming that this is a deliberate
unbuilt lane rather than an abandoned one is an owner call, not a repair.

**Q8 — `binding_health.py`, quarantine on an internal exception.** `run()` lines 419-424 turn any
exception out of `canary()` into `{"healthy": False}`, which quarantines the host. A local
`TypeError` therefore stops mining a live wiki for 24 hours. Deliberate strictness, or should an
internal fault produce `None` (the "not the host's fault" verdict the three-valued canary added)?

**Q9 — `binding_health.py`, the residual `n >= 200`.** `_fetch_chars`'s docstring argues at length
that judging by length was the defect and `page_looks_real` replaced it, but `_probe_present` still
gates on `if n >= 200` (line 219). It only makes the probe stricter, so it is not a hole — is it a
deliberate belt-and-braces, or a leftover the docstring believes was removed?

**Q10 — `tempus.py`, free foresight at M0.** `rung_description_length("M0") == 0` by construction,
so `prescience_horizon_bits("M0", n)["bits_required"] == 0` for any lead time. The `ceiling_note`
reasoning supports it (there is nothing in an M0 stream to extract), and `band_resolution`'s
docstring calls the same zero *"an instrument with no resolution at its own floor"* in the
commensuration case. Which reading governs prescience?

**Q11 — `tempus.py`, three functions with no consumer.** `concordance_now` has no caller anywhere,
including `verify_math`. `contemporaneous` and `is_present_at` are exercised only by
`verify_math.py:243-245`. Doctrine formalisation whose consumer is the battery is a legitimate
shape here — flagging for the owner, not proposing deletion.

**Q12 — `axis_correlation.py`, `widening()` when cov is strongly negative.**
`total = max(indep + cov, 1e-12)` (line 181) clamps, so a sufficiently negative covariance yields a
factor far BELOW 1 — a narrower bar than independence. Every measured r is positive today so it
cannot fire, but the clamp silently converts an impossible variance into a tiny one rather than
refusing.

**Q13 — `axis_correlation.py`, `mean_r` as the unmeasured-pair default.** `mean_r` is the unweighted
mean over pairs whose n ranges 42 to 45. Fine at today's spread; worth stating whether it should be
n-weighted if the sample ever becomes uneven.

**Q14 — `ledger.py`, anchor provenance.** `CURRENCIES` rates are declared fictional per Axiom M3 and
each carries a prose anchor, but nothing records which axis or worksheet validated the anchor, so
the table cannot be re-derived the way the header says it should be (*"change an anchor and the rate
moves with it, which is what makes the table reversible rather than decreed"*). Curatorial.
