# BATCH 14 audit — run26

Modules (2,556 lines total, read in full, no sampling):

| module | lines |
|---|---|
| assay.py | 650 |
| chain.py | 497 |
| generate.py | 422 |
| pantheon.py | 309 |
| tempus.py | 255 |
| resync_roll.py | 82 |
| cleanup.py | 209 |

---

## SPECIAL FOCUS — assay.py `axis_score()` M18, verified against current source

**Confirmed exactly as briefed.** assay.py:219-229:

```python
if x is None or x <= 0 or band not in BAND_EDGES:
    return None
i = LADDER.index(band)
if i + 1 >= len(LADDER):
    return 9.9
lo = BAND_EDGES[band].get(axis)
hi = BAND_EDGES[LADDER[i + 1]].get(axis)
```

`LADDER` (assay.py:105) has 11 rungs, M0..M10. For `band == "M10"`, `i == 10`, `i + 1 (11) >=
len(LADDER) (11)` is true, so the function returns a hardcoded `9.9` **without ever looking at
`x`**. Live-verified:

```
A.axis_score(1e30, "M10", "ruin")  -> 9.9
A.axis_score(1e33, "M10", "ruin")  -> 9.9
A.axis_score(1e36, "M10", "ruin")  -> 9.9
A.axis_score(1e40, "M10", "ruin")  -> 9.9
```

Ten orders of magnitude (1e30 through 1e40) collapse to the identical decimal. The docstring
directly above (assay.py:212-217) states the rule as `s(x) = 10 * clamp((ln x - ln x_r) / (ln
x_{r+1} - ln x_r))` — a **log-interpolation between the band's own floor and the next band's
floor** — and the M10 branch does not implement that rule; it implements a different one, silently,
with no comment explaining the departure. There is no "next band" for M10 to interpolate against,
which is a real problem (the Ladder has no M11), but the fix chosen (flat-return) throws away all
resolution above the M10 floor rather than, e.g., extending the M9->M10 band width the way
`tempus.band_resolution()` (tempus.py:182-210) explicitly does for the identical situation:

> "M10 has no band above it, so it inherits the M9->M10 width; saturation at the ceiling is a
> property of the Ladder, not a licence to invent an edge." (tempus.py:199-200)

`tempus.band_resolution()` implements exactly that fallback (`lo, hi =
BAND_EDGES[LADDER[i-1]]["ruin"], BAND_EDGES[band]["ruin"]` at tempus.py:209 when `i+1 >=
len(LADDER)`). `assay.axis_score()` has the same edge case, the correct pattern already exists
elsewhere in this same batch, and it was not applied here.

**A second, smaller inconsistency**: the flat return is `9.9`, but an *ordinary* band's own
ceiling (frac clamped to 1.0) evaluates to `round(10.0 * 1.0, 2) == 10.0`, confirmed live and by
`verify_math.py:127` (`axis_score clamps above ceiling` checks `A.axis_score(hi*100, "M3",
"ruin") == 10.0`). So an M9 entity landing exactly at the M9/M10 boundary scores `10.0`
(M9's own ceiling), while an M10 entity sitting just above its own floor scores `9.9` — a
discontinuity in the wrong direction across a band edge, with no comment addressing it either.

**Bottom-rung (M0/M1) check, per the special focus's second ask**: no equivalent silent-collapse
bug exists there. A quantity below the M0 floor clamps to `0.0` via the same generic
`max(0.0, min(1.0, frac))` that every band uses (not a special-cased early return), and this
clamp is explicitly documented and deliberate (assay.py:155-157, 214-217, citing the Kenshiro
Erratum 1 where a hand-scored Ruin of 2.1 could not be sustained below the M3 floor). The M10
top-of-ladder case is different in kind: it is undocumented, untested (see below), and
contradicts its own docstring's stated rule, where the M0 clamp is documented, tested, and
consistent with its docstring.

**verify_math.py coverage, confirmed**: `verify_math.py:122-127` is the entirety of
`axis_score`'s test coverage —

```
lo, hi = A.BAND_EDGES["M3"]["ruin"], A.BAND_EDGES["M4"]["ruin"]
x = math.sqrt(lo * hi)
check("axis_score at band geometric midpoint", A.axis_score(x, "M3", "ruin"), 5.0, ...)
check("axis_score clamps below floor", A.axis_score(lo / 100, "M3", "ruin"), 0.0, ...)
check("axis_score clamps above ceiling", A.axis_score(hi * 100, "M3", "ruin"), 10.0, ...)
```

All three checks use `"M3"`. No check anywhere in `verify_math.py` calls `axis_score` with
`band="M10"` (or any band at the top of the Ladder). The M18 bug is invisible to the project's
own regression suite exactly as briefed.

---

## MAJOR — assay.py `SIGMA_BY_ATTESTATION` rescale silently breaks the charter-reproduction claim it documents

assay.py:274-322 is a long, careful comment block arguing that the interval formula was
*derived* rather than decreed, and that solving the variance-propagation equation for the sigma
that reproduces the charter's own published Kenshiro interval (`M3.52 ± 0.12`, Witnessed
attestation, all eight physical Measures scored, three faculties absent) "gives 4.08 — on an
axis scale running 0.0 to 9.9" (assay.py:277-278). `_RAW_SIGMA["Witnessed"] = 4.08`
(assay.py:310) is that exact number.

But `_RAW_SIGMA` is never used directly. It is immediately rescaled:

```python
_SCALE = SIGMA_MAX / max(_RAW_SIGMA.values())          # SIGMA_MAX / 8.50
SIGMA_BY_ATTESTATION = {k: round(v * _SCALE, 4) for k, v in _RAW_SIGMA.items()}
```

`SIGMA_MAX = 9.9 / sqrt(12) ≈ 2.8579`, so `_SCALE ≈ 0.3362`, and
`SIGMA_BY_ATTESTATION["Witnessed"] ≈ 1.3718` — **not** 4.08. `_interval()` (assay.py:343) reads
`SIGMA_BY_ATTESTATION`, not `_RAW_SIGMA`, so **the code never uses the sigma the adjacent comment
says was solved for.**

Live-verified reproduction of the charter's own worked example (8 physical axes scored at 5.0,
3 faculties unscored, Witnessed attestation — the exact scenario the comment describes):

```
A.assay("M3", {ruin:5.0, continuity:5.0, celerity:5.0, reach:5.0, transgression:5.0,
               sustain:5.0, vector:5.0, volition:5.0},
        attestation="Witnessed", worksheet="test")["interval"]
-> 0.06
```

Re-deriving by hand with the *raw* 4.08 in place of the rescaled 1.3718 reproduces `0.12` exactly
(var_physical=1.2385+var_faculty=0.2025 → sqrt/10, squared, sqrt → 0.120). With the rescaled
1.3718 the same calculation gives `0.0585 -> 0.06`. **The interval the code actually prints for
this exact scenario is roughly half of the charter's published `± 0.12`.**

This is a real, currently-shipping regression against the calibration the comment block claims
(and against the "CALIBRATED AGAINST THE CHARTER'S OWN PUBLISHED BARS, not chosen" banner at
assay.py:274). The rescale step (added, per its own comment at assay.py:304-307, specifically to
enforce the `SIGMA_MAX` ceiling so "the worst grade just reaches the ceiling") is a legitimate
goal on its own, but it was applied *after* the 4.08 was fitted to reproduce 0.12, and nothing
re-checked that the *rescaled* table still reproduces the charter's number. It doesn't.

This is very likely a direct contributor to the run's "the automation reproduces the charter" RED
standard described in the task brief — any reference case routed straight through
`assay.assay()`/`assay._interval()` under Witnessed attestation will publish an interval about
half the charter's own. See the "WHY 5 REFERENCES ARE UNSCORED" section below for how far this
traces within this batch's modules.

**Also note**: `verify_math.py:490-494` runs a related check but through `custodes.CU.convene()`,
not through `assay.assay()`/`assay._interval()` directly — `custodes.py` is not in this batch, so
whether `CU.convene`'s own interval path shares this bug (via `CU.ATTESTATION_QUALITY`, which
`verify_math.py:538` says is "DERIVED from assay's own table") could not be confirmed here, but
the shared derivation makes it likely.

---

## MAJOR — resync_roll.py claims a fix that does not close the race its own docstring describes

resync_roll.py's docstring (lines 3-14) names the exact hazard the script exists to repair: four
different cataloguer scripts race to rewrite the whole of `data/SWEEP_ROLL.json`, and "two of
them running concurrently will have one clobber the other's counters with a stale copy read
minutes earlier" — with a cited real incident (an Aurora run's 425/681-entry counts reset to 0 by
a concurrent wiki-cataloguer's later save).

The current write path (resync_roll.py:65-68):

```python
if changed and not dry:
    # ATOMIC: this file's own docstring warned about the roll-clobber hazard while the
    # code went on truncate-then-filling it. Fixed 2026-08-25.
    silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)
```

`silence.write_json` (added/hardened 2026-08-25 per its own docstring at silence.py:250-269) does
make the **write itself** atomic — a per-pid/thread temp file plus `os.replace`, so no reader can
ever see a torn file and no two writers' temp files collide. That is a real fix for *file
corruption*. It is not a fix for the hazard the docstring actually describes, which is **staleness**,
not corruption: resync_roll.py reads `ROLL` once at line 33-34, then does a full, unbounded
`os.listdir(RECORDS)` scan and JSON-parses every record file (line 39-50) — a window with no
upper bound on wall-clock time — and only then writes back the in-memory snapshot it read at the
start. If any of the four cataloguer scripts (or another `resync_roll.py` invocation) writes
`SWEEP_ROLL.json` at any point during that scan window, that writer's update is silently replaced
by resync_roll.py's stale snapshot the moment resync_roll.py's own atomic write lands — the exact
"Aurora's 425/681 reset to 0" scenario the docstring exists to fix, still fully reproducible.

This is a re-confirmation of a MEDIUM finding already raised in `handoff/sweep23/AUDIT_batch05.md`
("unguarded read-modify-write on the shared, multi-writer `data/SWEEP_ROLL.json`"). What has
changed since sweep23 is that the code now carries a comment reading "Fixed 2026-08-25" directly
over the unchanged race — raising this to MAJOR, because the comment will read as closing the
finding to any future auditor who doesn't re-derive the mechanism, and the underlying risk
(silent loss of a concurrent cataloguer's fresher counts) is unchanged. `silence.write_json` does
not re-read-and-merge, lock, or otherwise guard the read-scan-write window; nothing in this batch
does.

---

## MAJOR — chain.py's own writers were missed by the same 2026-08-25 atomic-write sweep

`silence.py`'s `write_json()` docstring (silence.py:250-269, written today) states: "Found by the
2026-08-25 comprehensive sweep: TWELVE call sites across ten modules were writing shared `data/`
and `state/` files with a bare `open(path, 'w')`... THE TMP NAME CARRIES PID AND THREAD, which the
older hand-rolled `path + '.tmp'` sites did not. Two writers of the same path otherwise collide on
the temp file itself, and the loser can replace the winner's target with a partial file."

`chain.py` has two writers that still use exactly that vulnerable, superseded pattern, not
`silence.write_json`:

- `write_result()` (chain.py:111-121), writing `data/CHAIN.json`:
  ```python
  tmp = OUT + ".tmp"
  with open(tmp, "w", encoding="utf-8") as f:
      json.dump(out, f, indent=1, ensure_ascii=False)
  if not silence.replace_retry(tmp, OUT):
  ```
- `harvest()`'s incremental cache (chain.py:190-203), writing `state/chain_harvest_idx.json`:
  ```python
  tmp = HARVEST_IDX + ".tmp"
  with open(tmp, "w", encoding="utf-8") as f:
      json.dump(idx, f, ensure_ascii=False)
  if not silence.replace_retry(tmp, HARVEST_IDX):
  ```

Both call `silence.replace_retry()` for the rename (the second half of the safe pattern) but build
the tmp file with the bare `path + ".tmp"` name (the unsafe first half) instead of
`silence.write_json`'s per-pid/thread name. `write_result()`'s own docstring (chain.py:92-98)
records that this function already has two callers — `chain.main()` and `pipeline.phase_chain` —
so two processes writing `CHAIN.json` concurrently is not a hypothetical for this file; it is the
documented shape of how the function is called. If both land in the tmp-write window at once,
one process's partially-written temp file can be renamed over the other's completed one (or the
two writes interleave into the same inode), producing a torn `CHAIN.json` or `chain_harvest_idx.json`
despite `replace_retry`'s retry loop — `replace_retry` only retries a `PermissionError` on the
rename call; it does nothing about two writers sharing one tmp filename. This is the same class of
bug the 2026-08-25 sweep says it fixed at twelve sites; chain.py's two sites were not among them.

---

## MINOR — chain.py:108 `unmatched.most_common(40)` truncates data written to disk, not just a console preview

```python
"unmatched": (unmatched.most_common(40) if hasattr(unmatched, "most_common")
              else (unmatched or [])),
```

This is inside `write_result()`, writing directly into the persisted `data/CHAIN.json` artifact —
unlike the `unmatched.most_common(8)` in `main()` (chain.py:456), which is a `print()`-only
preview. Every unmatched name past the 40th most common is silently absent from the file that
downstream readers (and any future audit of "which real entities never matched the catalogue")
would consult. Classify: this reads as a legitimate *summary* field (the full edge list and
`components` are written in full alongside it; `unmatched` is explicitly a diagnostic tally, not
the phase's actual output), but it is still a `most_common(N)` cap on a value landing in a
committed data file, which Hard Rule 0 asks to be reported regardless of how defensible the
rationale is. Recommend either writing the full `Counter` (it is small — capped by the number of
distinct unmatched name strings, already deduplicated) or renaming the field to make the
truncation self-documenting (e.g. `unmatched_top40`).

---

## MINOR (reconfirmed, unchanged since sweep23) — cleanup.py:77-80 inert `_SETTING_META` guard slot

```python
for _n, _p in (("_NAV", _NAV), ("_EMPTY_MECHANIC", _EMPTY_MECHANIC),
               ("_SETTING_META", None)):
    if _p is not None and any(ord(c) < 32 for c in _p.pattern):
```

`_SETTING_META` is not defined in `cleanup.py` — the real regex of that name lives in
`pipeline.py:954`. The tuple entry is `None` and is skipped by the `_p is not None` guard, so this
is inert rather than broken, exactly as `handoff/sweep23/AUDIT_batch05.md` already noted. Still
harmless; flagged only for completeness of this full re-read.

---

## QUESTION — is the M10 flat-`9.9` a deliberate "never-quite-full" design choice or a placeholder?

No comment in `assay.py` explains why the M10 branch returns `9.9` specifically rather than
`10.0` (the value an ordinary band reaches at its own ceiling, per `verify_math.py:127`) or why it
returns a constant at all rather than adopting the `tempus.band_resolution()` pattern of
inheriting the previous band's width. Worth asking the owner directly rather than guessing.

---

## WHY 5 REFERENCES ARE UNSCORED / DAILY RE-RUN 32H OLD

Traced as far as this batch's seven modules go, and no further — reporting plainly per the task's
own instruction rather than guessing into files outside the batch.

`pantheon.py`'s `GODS` dict (6 entities: Zeno, Vados, Whis, Beerus, Champa, Grand Minister) was
the most plausible in-batch candidate for "six published reference assays," but live-testing
`pantheon.compute(pantheon.GODS)` shows **all six** score fully (real decimals: 0.77, 0.80, 0.84,
0.75, 0.64, 0.87 — none return the `"no worksheet supplied"` / `"no axis scored"` band-only
branches of `assay.assay()`). So this batch's reference set is not the one behind the "1/1
consistent, 5 unscored" figure; that figure names a different reference registry.

What this batch *does* establish, and hands to whichever module owns that registry: any reference
case that is (a) attested "Witnessed" and (b) computed straight through `assay.assay()` /
`assay._interval()` will publish an interval roughly half of what the charter's own worked example
calibrates to (see the SIGMA rescale finding above, live-verified at 0.06 vs. the charter's 0.12).
A "does the automation's interval overlap the published interval" check would read this as
inconsistent for any Witnessed-attestation reference, which is consistent with — though not
proven to be the sole cause of — the run reading mostly RED/unscored rather than all-green. The
"32h old" freshness figure and the actual "unscored" bookkeeping (which reference cases exist,
which attestation grades they carry, and what marks one "scored" vs. "unscored" for this
standard's purposes) are not computed anywhere in `assay.py, chain.py, generate.py, pantheon.py,
tempus.py, cleanup.py, resync_roll.py`. The likely owners, based on names surfaced while tracing
this (none read in this batch): `custodes.py` (`CU.convene`, `CU.ATTESTATION_QUALITY` —
`verify_math.py:454-494` exercises exactly the Kenshiro-reproduction scenario through this path),
`reference.py`, `standards.py`, and whatever drives the daily automated run (`overnight.py`
references `verify_math` but no scheduling/cron logic was found in this batch's modules).
Recommend routing this specific question to a batch covering `custodes.py`, `reference.py`,
`standards.py`, and `overnight.py`.

---

## Clean / no findings

- `tempus.py` — read in full; no bugs found. Its `band_resolution()` M10 fallback (lines 199-210)
  is in fact the correct pattern that `assay.axis_score()` should have used (cited above).
- `generate.py` — read in full; no Hard-Rule-0 violations (`pending[:3]` dry-run preview and
  `missing[:8]` failure-message preview both report their own truncation counts explicitly and do
  not affect what gets generated or written to the catalog); atomic writes throughout via
  `silence.write_json`.
- `pantheon.py` — read in full; `compute()` scores all 11 axes for all 6 entities correctly;
  atomic write via `silence.write_json`; no caps.
- `cleanup.py` — read in full; no deletions (only `catalogued=False` + `excluded` reason, which is
  the correct soft-exclusion shape per the project's no-deletion rule); writes via
  `pipeline.write_record` per the two-writer contract; print-preview slices (`[:5]`, `[:6]`,
  `[:4]`) do not affect what `--apply` writes.

---

## Summary table

| File | Verdict |
|---|---|
| assay.py | 2 MAJOR (M18 confirmed + new: SIGMA rescale breaks charter-reproduction claim), 1 QUESTION |
| chain.py | 1 MAJOR (unsafe tmp-file writers missed by 2026-08-25 sweep), 1 MINOR (data-cap on `unmatched`) |
| generate.py | Clean |
| pantheon.py | Clean |
| tempus.py | Clean (contains the correct pattern assay.py should reuse) |
| cleanup.py | Clean; 1 MINOR reconfirmed from sweep23 (inert guard slot) |
| resync_roll.py | 1 MAJOR (misleading "Fixed" comment over an unchanged clobber race) |
