# Batch 10 — run34

Modules read end to end: assay.py (991), derivation.py (558), gpu_lane.py (479), estate.py (348),
anchors.py (277), render.py (252), suppressions.py (187), scale_theories.py (148).

Everything below was executed or quoted from the live source. Where a candidate defect dissolved
on inspection it is recorded in **Dissolved** at the end rather than filed, because run33's
false-positive load was the expensive part of last shift.

---

## assay.py

### F1 — an axis score whose key is not in the weight table is silently discarded  [MAJOR]

`assay()` builds the scored set by filtering on membership of the weight table:

```python
    W = weights if weights is not None else WEIGHTS
    used = {k: v for k, v in scores.items()
            if k in W and isinstance(v, (int, float))}
```
(assay.py:725-727)

`_check_scores` runs first and passes any numeric value on the 0–10 scale, whatever its key. So a
key the table does not know — a typo, a renamed axis, a model emitting `stamina` — survives
validation and is then dropped with no trace. It appears in neither `axes_scored` nor
`axes_unscored`, does not move `axis_coverage`, and produces a decimal identical to the one you
get by omitting it. Measured live:

```
assay('M3', {'ruin':2.1,'ruinn':9.9,'stamina':8.0}, 'Witnessed', worksheet='w')
  -> 𝔄 M3.21 ± 0.22   axes_scored ['ruin']   coverage 0.15
assay('M3', {'ruin':2.1},                      'Witnessed', worksheet='w')
  -> 𝔄 M3.21 ± 0.22   axes_scored ['ruin']
identical decimal: True
```

This is not a hypothetical shape in this file. Its own ERRATUM (X.11) at assay.py:118-121 records
the same filter zeroing the three faculties library-wide: *"`FACULTY_WEIGHTS` was defined and never
read by anything, while `assay()` filtered on `k in WEIGHTS`, which excluded them outright."* The
weights were repaired; the silent-drop behaviour that hid the problem for months was not.

`magnitude.AXES = list(A.WEIGHTS)` means today's main caller cannot produce an unknown key, which
is why this has not bitten again — but that is one caller's discipline, not the instrument's.

### F2 — the NONE sentinel is tested by identity in one place and by equality in another  [MINOR, latent]

```python
        if v is NONE or v in (INAPPLICABLE, UNESTIMABLE) or v is None:
```
(assay.py:459, in `_check_scores`)

```python
    nil = [k for k in W if scores.get(k) == NONE]
```
(assay.py:736, in `assay`)

`NONE` is the string `"none"`. Of the three sentinels on line 459 it is the only one compared with
`is`; `INAPPLICABLE` and `UNESTIMABLE` on the same line use `==`. A `"none"` that is not the
interned literal — the ordinary result of `json.loads` — therefore fails the identity test, falls
through to the "not a number" branch and RAISES, so the equality test at line 736 is never reached:

```
>>> s = json.loads('{"ruin": 2.1, "reach": "none"}')
>>> s['reach'] is A.NONE, s['reach'] == A.NONE
(False, True)
>>> A.assay('M3', s, worksheet='w')
AssayIntegrityError: axis scores off the scale: reach='none' (not a number)
```

Latent today: every live caller builds its scores from the `A.NONE` literal (halo.py, magnitude.py,
anchors.py), so nothing loads the sentinel back off disk into `assay()`. But `"none"` is already
stored as an axis score on disk — `data/HERO_ASSAYS.json` holds it at
`Wally West (New Earth)/axes/sustain/score` and `Wally West (Prime Earth)/axes/sustain/score` — so
the first record-driven re-assay path will hit it. The failure is fail-closed (a refusal, not a
wrong number), which is why it is MINOR and not MAJOR.

### F3 — two of `_check_constants`' four branches cannot fail  [MINOR]

```python
    if SIGMA_UNKNOWN < max(vals):
        ...
    if max(vals) > SIGMA_MAX:
```
(assay.py:488, 493)

against

```python
SIGMA_MAX = SIGMA_BY_ATTESTATION["Disputed"]        # line 414
SIGMA_UNKNOWN = SIGMA_MAX                            # line 417
```

`vals` is exactly the five `SIGMA_BY_ATTESTATION` values, and the monotonicity check two lines
above guarantees `Disputed` is the largest of them. So both comparisons test a value against
itself. Measured: `max(vals) > SIGMA_MAX -> False`, `SIGMA_UNKNOWN < max(vals) -> False`, and no
assignment of `_RAW_SIGMA` can change that, because the ceiling is *derived from* the table it
polices.

What makes this worth filing rather than shrugging at is the docstring above it:

> Two of these are the exact failures this file has already had:
>   * monotonicity — ...
>   * the ceiling — an attestation sigma above SIGMA_MAX is silently clamped by `_interval` ...

The ceiling branch *would* have fired against the pre-2026-08-25 table, when `SIGMA_MAX` was the
literal `9.9/sqrt(12)` and raw Witnessed sat at 4.08 above it. Rebinding `SIGMA_MAX` to the widest
grade fixed the incoherence and, as a side effect, disabled the check written to catch it. The net
is now redundant, not broken — but it is presented as live protection against a recurrence it can
no longer see, and this file's own standing lesson is that those look identical.

(Contrast with the `grade_n <= 5` bounds guard at assay.py:840-845, which run33 filed as a
tautology and which was correctly left standing: that one prevents an `IndexError` on a literal
with six slots. These two prevent nothing.)

### F4 — `_rho`'s docstring names an import-time guard that does not exist  [MINOR]

```python
    was before" rather than to some third behaviour nobody has seen. It must not stay silent
    about it, and it does not: `_check_constants` refuses at import time if the matrix is absent
    when it should be present, and a drill net attacks it.
```
(assay.py:564-566)

`_check_constants` (assay.py:476-497) contains only the sigma-order and ceiling branches. It never
opens, names or reasons about `axis_correlation` or `AXIS_CORRELATION.json`. The second half of the
sentence is true — `drill.py:2384-2395` has `measures_are_not_independent`, which returns False on a
missing matrix — so the protection exists; the file simply credits it to the wrong mechanism, and
`_rho`'s own `except Exception: _RHO_CACHE[0] = {}` (assay.py:573) then discards the reason silently
on the strength of a guard that is not there.

### F5 — the off-scale-axis refusal reports at most six of the bad axes  [MINOR]

```python
            "axis scores off the scale: " + "; ".join(sorted(bad)[:6])
```
(assay.py:467)

Eleven axes can be bad at once — a pasted percentage column is precisely the case the check was
written for and precisely the case that produces more than six. The list is sorted and then
truncated, so the operator fixes the alphabetical head and re-runs into the same refusal. Hard Rule
0's shape, in an error message: the truncation does not fail, it returns a smaller universe wearing
the same shape as the real one. Precedent for filing a display truncation: order 47c8def059e3
(cosmology_graph).

---

## derivation.py

### F6 — the constant scan covers 22 of 113 modules, and the list is hand-maintained  [MAJOR]

```python
SCAN_MODULES = ["assay", "feats", "cosmography", "propagation", "descending_ladder",
                "scale_theories", "chord_field", "resonance", "tempus", "ledger", "rigor", "custodes", "weave", "onomast", "worldseed", "address_space", "genre", "profile", "tiers", "grounding", "sevenfold", "burgs"]
```
(derivation.py:476-478 — 22 names; `ls src/*.py` is 113)

The module docstring states the purpose the scan is meant to serve:

> ... and the modules' own source is scanned for module-level constants, so a reviewer can see
> exactly where numbers live and catch a new undeclared one the day it is written rather than three
> volumes later.

Ninety-one modules are never opened, and — the part that matters — a module written tomorrow is not
scanned until somebody remembers to add its name here. The one automated instrument the library has
for finding undeclared free parameters cannot see most of the library, and reports nothing when it
misses one: `main()` prints the 22 rows under the honest header "a reviewer's map, not a verdict"
and the VERDICT line is computed from `check_graph()` alone, so a run is green either way. Every
listed module does exist (verified — no "(absent)" rows), so the omission is silent in both
directions.

Judgment call for RUN rather than a mechanical fix: globbing `src/*.py` would work, but the output
is a human-read table and 113 rows may want grouping or a floor.

---

## gpu_lane.py

No confirmed findings. The module is unusually well covered against its own history; the two shapes
worth attacking both held up (see Dissolved).

---

## estate.py

### F7 — every numeric `silence.note()` tag in the file points at the wrong line  [MINOR]

| call | tag says | actually at |
|---|---|---|
| `silence.note("estate.py:65")` | 65 | 66 |
| `silence.note("estate.py:83")` | 83 | 85 |
| `silence.note("estate.py:85")` | 85 | 88 |
| `silence.note("estate.py:87")` | 87 | 91 |
| `silence.note("estate.py:93")` | 93 | 98 |
| `silence.note("estate.py:96")` | 96 | 102 |
| `silence.note("estate.py:107")` | 107 | 114 |

Two of them are worse than merely stale: the tag `estate.py:85` now names the line holding the
`estate.py:83` call, so a reader chasing a swallow report lands on a *different* handler and reads
the wrong failure. The same file already shows the convention that does not rot —
`silence.note("estate.py:written-sources")` at line 250, and `suppressions.py:load`. Distinct from
order 918da0e4b88b, which is sweep33 batch09 (magnitude/handbuilt/tiers/scout/genre/profile/physics)
and does not cover this file.

---

## anchors.py

### F8 — the `__main__` comment states an exit status the script no longer produces  [MINOR]

```python
    # It exits 1 TODAY: measured run #26, `A Sword` (0.10) sits below `The Skate Guy` (0.22) and
    # `Goku` (5.42) below `Yggdrasil` (6.18). Whether that ordering or the scores are wrong is an
    # instrument question for the owner (NEXT_STEPS), not something this script may paper over --
    # but it must now say so out loud instead of exiting 0.
```
(anchors.py:272-275)

The owner ruling of 2026-08-25 recorded 60 lines above reordered the declared ladder to
`["A Sword", "The Skate Guy", "Goku", "Yggdrasil", "The Seat of the Creator"]` (anchors.py:242) —
i.e. to exactly the ordering this comment calls a violation. Run just now:

```
  monotone floor -> ceiling : True
     A Sword                        0.10
     The Skate Guy                  0.22
     Goku                           5.42
     Yggdrasil                      6.18
     The Seat of the Creator       10.99
EXIT=0
```

`allsweep` lists `anchors.py` under "the instrument" and judges it by exit code, so anyone reading
this comment to interpret a green sweep will conclude the sweep is lying to them. The invariant
itself is sound and the exit-code plumbing above it is correct; only the "TODAY" paragraph is stale.

---

## render.py

No confirmed findings.

---

## suppressions.py

### F9 — an unreadable SUPPRESSIONS.json reports as zero suppression problems  [MAJOR]

```python
def _load():
    try:
        ...
    except FileNotFoundError:
        return []
    except Exception:
        silence.note("suppressions.py:load")
        return []
```
(suppressions.py:45-54)

`problems()` iterates `_load()` (suppressions.py:139), so corruption collapses to an empty list and
the fault report is computed over nothing. Measured against a deliberately corrupt copy (temp file,
repo untouched):

```
_load     -> []
active    -> []
problems  -> []
suppressed('secret_scan','src/drill.py') -> None
main --check prints "0 suppression problem(s)" and returns 0
```

The module's own docstring is the standard this fails: *"an expired or dangling one is a FAULT
rather than a silent pass"*. The one fault that destroys the entire waiver record — including every
stated reason, which the header argues is the whole point of the file — is the one it cannot report.
It also takes two drill nets with it, both of which pass vacuously on an empty list:

```python
    net(a, "every suppression carries a reason and an expiry",
        lambda: all(len(r.get("reason", "")) >= 12 and r.get("expires_at")
                    for r in SUP.active()), ...)
    net(a, "no suppression is expired or dangling",
        lambda: SUP.problems() == [], ...)
```
(drill.py:840-846)

The third net, `_suppressed_still_visible`, *would* still fail (no finding would come back tagged
SUPPRESSED), so the drill does not go fully green — but the operator-facing `--check`, which is the
interface a person uses to review waivers, reports clean. The direction of the failure is safe for
the detectors (nothing is waved through when the file is unreadable) and blind for the review, which
is the half this module exists to protect.

---

## scale_theories.py

### F10 — the module is referenced by nothing; four dead functions and five unread constants  [MINOR]

`liveness.py` reports all four public functions dead:

```
   scale_theories.py:104 bulk_export_beta()
   scale_theories.py:121 growth_strike()
   scale_theories.py:134 penetration_pressure()
   scale_theories.py:145 surviving_theory()
```

and no module in `src/` imports `scale_theories` — the only mention anywhere is its own name inside
`derivation.SCAN_MODULES`. The five module-level constants

```python
C_LIGHT = 2.99792458e8
G_NEWTON = 6.67430e-11
HBAR = 1.054571817e-34
NUCLEAR_DENSITY = 2.3e17
PLANCK_LENGTH = 1.616255e-35
```
(scale_theories.py:23-27)

are read nowhere — not by the four functions, not outside the file — while `physics.py:57` owns `C`
and the derivation ledger already carries `c`, `G`, `hbar`, `nuclear_density` and `planck_length` as
MEASURED roots. So the ledger's own constant map counts "scale_theories 6 constants" without
noticing they are a fifth restatement of quantities it declares are fixed once.

One shape inside the dead code is worth recording in case the module is kept rather than removed:

```python
def surviving_theory():
    return {name: t for name, t in THEORIES.items()
            if t["falsified_by"].startswith("Nothing attested")}
```
(scale_theories.py:145-148)

The verdict "which theory survives the evidence" is selected by the literal English prefix of a
prose field. Reword T3's `falsified_by` and the function returns `{}` — no theory survives — with no
complaint anywhere.

This is an OWNER call, not a repair: `THEORIES` is authored content (four priced codifications with
their falsifiers) and deleting the module would lose it. The decision is whether to wire it into
whatever prices Transgression, or to keep the catalogue and drop the unread constants.

---

# QUESTIONS

1. **assay.py:250 / `band_for_quantity`.** For any axis with no `BAND_EDGES` entry —
   `transgression`, `volition`, `vector`, `acumen`, `discernment`, `suasion` — the loop
   `if x >= BAND_EDGES[b].get(axis, math.inf)` never fires, so the function returns `"M0"` for every
   positive quantity rather than `None`. Verified: `band_for_quantity(1e9, 'acumen') -> 'M0'`.
   `axis_score` handles the same case by returning `None`. Not filed: the function has no callers and
   is already covered by order b5e63bb91ca2 (three dead functions in assay.py). Worth knowing if the
   deletion is turned into a repair instead — `feats.py:747` names it as the intended tool.

2. **assay.py:979 / `interval_from_hands`.** `"covers_all_signatures": all(abs(v - centre) <= interval
   for v in vals)` is evaluated immediately after the loop
   `while any(abs(v - centre) > interval for v in vals): interval = round(interval + 0.01, 2)`. Same
   predicate, negated — the reported field can only ever be `True`. It is a genuine report column that
   can never be populated with the answer it exists to give. Not filed for the same reason as (1):
   the function is dead and already filed. Is the field meant to be a check, or a label?

3. **estate.py:216-219.** The charter errata are reported on word presence, not on the condition:
   `for rung in ("Supercluster", "Filament", "Hyperverse"): if rung.lower() in text.lower(): note(...)`.
   The comment says this is deliberate — *"The errata, restated every run so they cannot quietly
   become accepted"* — but it means a charter that gained the missing Magnitude bands would keep
   reporting the erratum as open for ever. Intended, or should it read the band assignment?

4. **suppressions.py:98-104, 122.** `active(detector=None)` skips the detector filter entirely
   (`if detector:`), so `suppressed(None, path)` — or `suppressed("", path)` — matches an exemption
   written for *any* detector. Both live callers (drill.py:848, publish.py:300) pass a real detector
   name, so nothing is wrong today, but the module's own rule in capitals is that a suppression
   narrows a detector for a NAMED case. Should a falsy detector be refused rather than treated as a
   wildcard?

5. **suppressions.py:57-75 / `_land`.** `add()` does read-modify-write: `_load()`, append, `_land()`
   via `silence.replace_retry`, which does not check the file was unchanged. `silence` already
   provides `replace_if_unchanged(tmp, dst, expected_digest)` and `digest_of()` for exactly this. Two
   concurrent `add()` calls lose one waiver silently, and the losing caller gets a row back that looks
   committed — the same class of lie the docstring reasons at length about for the rename verdict.
   `add()` has no callers in `src/` (operator-invoked), so this is theoretical today. Worth the
   stronger primitive on a safety file?

6. **derivation.py:534.** `for n in sorted(LEDGER, key=lambda x: -depth(x))[:6]` — a ranked list
   truncated for the console. Display only, and the same shape order 47c8def059e3 files against
   cosmology_graph. File it or leave it?

7. **render.py:237.** `print(f"\nall {len(TIER_ORDER)} tiers viewable")` is printed unconditionally.
   For the four fetched tiers "viewable" means only that a URL string was formatted — nothing checks
   the generator answers. The line cannot say otherwise while the script runs at all. Report or design?

8. **render.py:222.** `w = WS.build_all(limit=1)[0]` in `main()` — a `limit=` on a builder, used to
   get one seed for a demo row. Hard Rule 0 shape, benign purpose. Leave?

---

# DISSOLVED — checked and NOT filed

* **gpu_lane.py:62-63** — the comment says `read.py` "spelled the same number out a third time as
  `GATE_LOCAL_N`", implying a fix that links them. It is true and current:
  `read.py:289-290` reads the identical
  `PANSCRIPTUM_GPU_SLOTS` / `OLLAMA_NUM_PARALLEL` pair as `gpu_lane.py:66-67`. (My first grep was
  head-limited and missed read.py; the finding would have been wrong.)
* **gpu_lane.py:477 / `status()`** — `except Exception: pass` with no silence marker. Already carried
  by the standing silence audit (13 handlers in this file, all documented fail-open) and by orders
  e1f0e884806f / 5ff878fe008f. Not a new finding.
* **gpu_lane `_take_slot`** — the `_remove_retry` return value is discarded, but the following
  `O_CREAT|O_EXCL` open converts a failed release into `FileExistsError -> continue`, so the verdict
  is not needed. Correct as written.
* **assay `calibration_report` sweep** — the `sigma=` per-call override does what the comment claims;
  the sweep touches no shared table. Re-read after today's fix, holds.
* **assay `_interval` weights** — `W` is threaded from `assay()` and used for both the independent
  and the covariance terms, against the same `denom`. No mismatch.
* **derivation `check_graph`** — closes; DANGLING/ROOTLESS/CYCLE branches are all reachable.
* **anchors monotonicity invariant** — reachable and currently True; the exit-code plumbing at
  anchors.py:276-277 is correct. Only the comment above it is stale (F8).
* **suppressions `active()`** — a row with no `expires_at` is excluded (`(r.get("expires_at") or 0) >
  now`), i.e. fails shut. Correct.
* **estate `artifacts()`** — no sampling anywhere; the `bad` list is returned entire. Matches its
  docstring.
