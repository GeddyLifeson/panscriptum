# Sweep56 batch13 — audit

Modules read in full, top to bottom: `src/assay.py` (1914 lines), `src/dashboard.py` (1248),
`src/derivation.py` (811), `src/weave.py` (698), `src/catalogue_codex.py` (511),
`src/pantheon.py` (432), `src/deprecated/catalogue_local.py` (334), `src/audit.py` (272).

General note on this batch: every one of these files (except the deprecated one) is already
extremely heavily self-audited — most historical bugs the sweep task asks me to look for
(tautological checks, fail-open paths, silent swallows, undisclosed caps) have their own long
comment blocks describing exactly when they were found and fixed, with "measured" verification
numbers. I verified a sample of these claims directly (see catalogue_codex.py and
catalogue_local.py below) rather than taking the comments on trust, per the instructions. I did
not find any evidence that a documented fix is not actually in the code.

---

## src/assay.py

**Nothing found.** This is the scoring engine the task specifically asks to look hard at (score
that cannot vary, unreachable band, silently-substituted default). I read it end to end and
checked the live behaviour of `axis_score`, `_check_scores`, `_check_weights`,
`_check_constants`, `_interval`, `assay()`, `instrument()`, `interval_from_hands()`:

- Every score input is refused (raises `AssayIntegrityError`) rather than clamped when it is off
  the 0–10 scale, on an unrecognised axis, negative-weighted, non-finite, or NaN. All three public
  entry points that take numbers from a caller (`assay`, `instrument`, `interval_from_hands`) run
  the same Layer-1 validation — confirmed by reading each call site, not just the docstrings
  claiming it.
- `_check_constants()` (import-time) cross-checks `BAND_EDGES` vs `LADDER`, `SIGMA_BY_ATTESTATION`
  monotonicity and ceiling, `ATTESTATION_FLOOR` monotonicity, `INSTRUMENT_WINDOWS` vs `LADDER`,
  `FACULTY_READS` vs `WEIGHTS`, and the `BAND_EDGES`/`NON_ENERGETIC_AXES`/`WEIGHTS` partition —
  and is actually called at the bottom of the file (line 1914), so a broken table refuses to
  import rather than silently loading. Confirmed by reading the call site, not assuming it exists.
- The M10 "top rung" branch in `axis_score` (return `9.9`/`0.0`) is reached only *after* the
  band/axis/quantity checks, per its own extensively-argued docstring — verified this ordering
  directly in the code (lines 306–351): the `band not in BAND_EDGES` and
  `axis not in BAND_EDGES[band]` checks run before the `i + 1 >= len(LADDER)` branch, so a
  misspelled axis or off-ladder band still raises even on M10.
- `calibration_report()` genuinely re-derives the charter's Kenshiro number from the live
  arithmetic (calls `assay()`) rather than asserting a stored constant, and does not mutate the
  shared `SIGMA_BY_ATTESTATION` table during its sweep (uses the per-call `sigma=` parameter).

**QUESTION** (very low confidence, no evidence of a live problem): `_check_constants()` verifies
that `INSTRUMENT_WINDOWS` and `LADDER` carry the same keys, but does not verify that each
`(lo, hi)` pair is internally sane (`lo <= hi`, both within the declared 1–30 range that
`instrument()`'s docstring cites from X.6 §6 Definition 4). Every other constant table in this
file (`BAND_EDGES`, `SIGMA_BY_ATTESTATION`, `ATTESTATION_FLOOR`) gets this kind of internal
ordering check; this one table does not. Currently harmless — the live table
(`"M0": (1, 18)` … `"M5"`–`"M10": (30, 30)`) is valid, and `instrument()`'s arithmetic degrades
gracefully even if `hi == lo` (verified: `span = hi - lo = 0` collapses `value` to exactly `lo`,
no crash) — so this is not a live bug, just a possibly-incomplete invariant list. Flagging as a
question rather than a defect because I have no evidence the table has ever been wrong, and it
may be a deliberate scope decision.

---

## src/dashboard.py

**Nothing found.** Read-only instrument; every panel builder (`quotas`, `throughput`, `jobs`,
`library`, `watch`, `movement`, `metrics`, `safety`) is individually try/excepted so one bad
source cannot blank the page, and every except branch calls `silence.note(...)` with a distinct
tag (I did not find a bare `except: pass` anywhere in the file). `main()` fails closed if
`escalation` cannot be imported (`raise SystemExit`, not a swallowed `ImportError`) — confirmed
this is not the softened `except ImportError: pass` the file's own comment says it used to be.
The one cap in the file, `hist[-2000:]` in `movement()` (history buffer for the movement panel),
is a monitoring-instrument sample cap, not a corpus/entity roster, and the file has an extensive,
specific argument for why it does not affect the correctness of the 30-minute delta window it
serves (`MOVED_WINDOW_MIN = 30` is far inside both the 2000-sample and 24h bounds) — I traced
that argument against the actual code and it holds. Not treating it as a Hard-Rule-0 finding.

---

## src/derivation.py

**DEFECT (documentation only — comment contradicts the code it describes, no functional
impact).** Two docstrings/comments still describe `SCAN_MODULES` as being built from
`os.listdir(HERE)`, but the function that actually builds it, `_scan_modules()` (lines 584–593),
uses `os.walk(HERE)` recursively (with `__pycache__` pruned) — and the block comment directly
above it (lines 565–583) says this recursive walk is the *fix*: "NO LONGER FLAT (order
ca1ed2be8c51, closed 2026-09-06). `os.listdir(HERE)` read only the TOP level of `src/`... A
deprecated directory is exactly where an undeclared constant would be least looked at."

The two stale spots, neither updated when that fix landed:

- `scan_constants_with_reason`'s docstring, line 628: "`SCAN_MODULES` is built from
  `os.listdir(HERE)` over the same directory this function then reads (order ca1ed2be8c51 notes
  this listing is still flat and misses `src/deprecated/`, left open this shift — see the comment
  above `SCAN_MODULES`)".
- `main()`'s comment, lines 789–791: "`(absent)` for everything was actively wrong here:
  `SCAN_MODULES` is built from `os.listdir` of this same directory, so `\"absent\"` is a race and
  `\"will not parse\"` is the only thing a reader realistically sees."

Both assert, in the present tense, a mechanism (`os.listdir`, top-level only) that the code no
longer uses. This is exactly the "stale citation that no longer points at the cited code" shape
the sweep asks for, just for a described mechanism rather than a line number. No behavioural
consequence — `_scan_modules()` itself is correct and does walk `deprecated/` (confirmed by
reading it), so this cannot cause a real miss; a future reader trusting the docstring's account
of *how* the absent/unparseable distinction is guarded could be confused about whether the
`deprecated/` blind spot is still open (it is not).

**Nothing else found.** `check_graph()`'s `kind` validation is real (I checked the reasoning that
a typo'd `kind` used to pass silently, and the current code has an explicit `q.get("kind") not in
KINDS` branch before the other checks). The cycle-detection early return before the
deepest-chain walk (`return 1` at line 756 before the `_chains` loop) is genuinely necessary —
`depth()` does not memoise and has no cycle bound, so I agree the walk would not terminate over a
cyclic ledger; the guard is real, not decorative. The `_chains` panel and the `where constants
live` panel are both genuinely uncapped (`_chains` iterates all `len(_chains)` rows;
`SCAN_MODULES` loop has no `[:n]`).

---

## src/weave.py

**Nothing found.** All of the caps this module's own comments describe finding (the `[:400]` /
`[:300]` description windows, the `if len(shared[p]) < 8` cap, the `[:34]` name truncation, the
capped `most_common(6)`, the three-nested-truncation report line) are confirmed removed in the
live code — I checked each cited line against its comment and none of the old slice/cap
expressions remain; `filtered_index` reads the whole description, `surprisal_pair_weights`
appends to `shared[p]` with no cap, `byk.most_common()` takes no argument, and the `--write`
report loops (`for g in multi`, `for v in sorted(resolved.values()...)`, `for k, n in
byk.most_common()`) have no slicing. `NullThresholdUnmeasured` is genuinely raised (not returned
as `0.0`) when `trials <= 0` or no trial produces a weight, and `components()` genuinely refuses
`threshold <= 0` before agglomerating (both paths fail closed rather than defaulting to "merge
everything" or "cutoff of zero"). `main()` correctly returns 1 rather than swallowing either
refusal.

---

## src/catalogue_codex.py

**Nothing found; one QUESTION.** Every collision class this module tracks (section-title
`norm()` clashes, ambiguous substring section binding, ambiguous register descriptions, duplicate
`(type, name)` manifest elements, unmapped element types) is reported uncapped, verified by
reading each print loop (`for k, v in sorted(norm_clashes...)`, `for nm, cands in ambiguous`,
etc.) — none has a slice or a `[:n]`.

I additionally ran the parser (read-only; `parse_codex()` only opens and reads the codex file, it
does not write) against the live codex at
`C:\Users\imarl\Documents\5e Character Builder\custom\THE_PRIME_OMNIVERSE_CODEX.md` to check the
module's own "measured 0 mismatches" claim for the manifest count cross-check
(`parse_codex()`, line 129 comment). Confirmed: 64 sections, 4,489 manifest elements, 0 count
mismatches today — matches the comment's claim exactly.

**QUESTION** (low confidence, currently unreachable): in `main()`'s element loop, line ~313–314:

```python
key = norm(name)
...
if not key:
    continue
```

This silently drops a manifest element whose name normalises to an empty string (e.g. a name
made entirely of punctuation), with no counter, no print, and no roll/report entry — unlike
every other drop path in this same function (`dupe_elements`, `reg_ambiguous`, `unmapped_types`,
`ambiguous`), which are all explicitly collected and printed uncapped specifically because this
module's own doctrine is that a dropped catalogue entry must never be silent. I checked whether
this branch is live against the actual codex: it is not — 0 of 4,489 parsed manifest names
normalise to an empty string today (measured directly, see above), so this is a dormant guard in
the same spirit as several other "kept as a backstop, currently unreachable" guards this project
explicitly endorses elsewhere (e.g. `assay.py`'s `denom = ... or 1.0`). Flagging only because it
is the one drop path in this file that doesn't follow the file's own report-everything pattern,
not because I found it actually dropping anything.

---

## src/pantheon.py

**Nothing found.** `compute()` builds `worksheet=` as a per-axis citation dict rather than a
single string; I checked whether any consumer of `assay()`'s returned `worksheet` field assumes a
string and found exactly one reader in the tree (`reference.py:472`), which reads its own
separately-built `out[name]["worksheet"]` dict (a different structure built in `reference.py`
itself), not the field `pantheon.py` sends into `assay()` — so there is no cross-module type
mismatch here. `main()`'s roster merge and the `--full` view are already hardened against a
partial `Z_FIGHTERS.json` (`_incomplete` marker), a totally unreadable one (`except Exception` ->
`merge_failed`), and a per-entity missing `provenance` field (`.get("provenance", "?")`) — I
traced each of the three failure paths against the code that is supposed to handle it and all
three set `merge_failed`/print a note and are reflected in the exit code (`return 1`). The
`for ax in A.WEIGHTS: d = rec["axes"][ax]` loop in `--full` would `KeyError` if a merged roster
entry were missing an axis key entirely (not just missing `provenance`); the file's own comment
says this was checked against the live data ("all fifteen Z_FIGHTERS entries carry an assay and
all eleven axes") — I did not re-verify that measurement against `data/Z_FIGHTERS.json` since
`zfighters.py` is outside this batch's module set, so I'm not asserting it as clean, just noting
I have not disproved the comment's claim either.

---

## src/deprecated/catalogue_local.py

**Nothing found — verified by direct execution, not just by reading.** This is the module the
task specifically warns about ("a real, live entry point that can WRITE... escapes house
checks that glob `src/*.py`"). As currently written, the entire module refuses to run:

```python
if set(sys.argv[1:]) & {"-h", "--help"}:
    print(_REFUSAL)
    raise SystemExit(0)
raise SystemExit(_REFUSAL)
```

This sits at module level, before `import yaml`, before `load_cfg()`, before any of
`slug`/`call`/`catalogue_source`/`main` are defined. I ran it directly (read-only invocations
only — `--help` and `--dry-run`, neither of which reaches any file I/O) to confirm this is not
just a documentation claim:

- `python src/deprecated/catalogue_local.py --help` → prints the refusal notice, exit code 0.
- `python src/deprecated/catalogue_local.py --dry-run` → prints the refusal notice, exit code 1.

In both cases execution stops at the module-level `raise` before `def main()` is ever reached, so
`main`, `catalogue_source`, `call`, and `slug` are never bound in the module namespace on any
import path I could construct — there is no way to reach the six specific write-hazards the
file's own header documents (bare `open(path, "w")` bypassing the two-writer contract, the
`slug()` `[:60]` identity truncation, the non-atomic whole-roll rewrite inside the loop, `main()`
returning `None`/rc=0 on any outcome, the `per_cat[key] = 0` silent failure-as-empty-result) short
of an actual code edit to this file. Those six issues are real *in the dead source text* — I
confirmed each one is still literally present at the lines the header describes — but none of
them are reachable, which matches the header's own claim ("What is removed is the loaded gun...
before any config is read or any file is touched"). I am reporting this as verified-clean rather
than silently trusting the header comment, since the sweep's own house rule is not to trust a
self-report without checking it directly.

One thing worth the owner's attention even though it is not a defect in the code: `derivation.py`
(line 565–583, this same run) independently confirms that the `os.walk`-based module scanner
*does* now descend into `deprecated/` (order ca1ed2be8c51), so the specific escape hatch this
task's briefing describes ("house checks... do not descend into `deprecated/`") is at least
partly already closed for the constant-scanning check, on top of this file's own unconditional
refusal. I have not verified every other house check mentioned generically in that briefing
(`drill.py`, `sweep_plan.py`, etc. are outside this batch) actually descends into `deprecated/`
too — only that `derivation.py`'s scanner does, and that this file's own refusal makes the
question largely moot for this specific module regardless.

---

## src/audit.py

**Nothing found.** `audit_invariants()`'s synthesis-vs-entry fault classes are genuinely
independent (I checked the `claims_a_band = band in VALID_BANDS and band != "unassayed"` guard
that the file's own comment says was added to stop a missing `provisional_magnitude` from firing
three unrelated-looking fault rows at once). The denominator for each fault class's percentage is
read from the class's own population (`sources_with_synthesis` for `synthesis:`-prefixed keys,
`entries_catalogued` for everything else) rather than one shared counter — verified this against
the `if k.startswith("synthesis:")` branch, matches the comment's claim about the old
three-orders-of-magnitude-wrong rate. Every fault list is printed in full (`for x in v: print(...)`,
no `[:n]`, no "and N more"). `_field()` wraps rather than slices sample text. The
`description too short` check operates on `d.strip()` for both the length test and the printed
value (not `d` for one and `d.strip()` for the other), which the file's own comment says was the
actual bug in an earlier version (a padded-then-short string could print as blank) — confirmed
the current code uses `d.strip()` consistently in both the condition and the printed `!r`.

---

## Coverage

Recorded via `sweep_plan.record` for run56 batch 13, modules: assay.py, dashboard.py,
derivation.py, weave.py, catalogue_codex.py, pantheon.py, deprecated/catalogue_local.py, audit.py
— all eight read in full, top to bottom, in this pass.
