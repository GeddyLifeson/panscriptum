# SWEEP run54 — batch 13 audit

Batch: `src/assay.py`, `src/dashboard.py`, `src/rosetta.py`, `src/secondopinion.py`,
`src/withdraw_chapters.py`, `src/render.py`, `src/navtree.py`, `src/ledger.py`, `src/chord_field.py`

Every module below was read in full, top to bottom (not sampled), including every inline
comment documenting prior fixes. This batch turned out to be one of the most heavily
self-documented in the tree — most modules carry extensive "here is the bug this used to have
and here is the fix" commentary, and I traced each such claim against the code that follows it
to confirm the fix described is actually the fix present. Where I found the claim and the code
agree, I have not re-filed it; I only report what I could find *beyond* what the file already
documents about itself, or a documented claim I could not verify.

---

## src/navtree.py (335 lines) — read in full

### MAJOR — no escalation/halt check before writing data/NAVTREE.json
**Where:** src/navtree.py (whole file; specifically `main()`, ~line 236-331, and the write at
line 304 via `silence.write_json(OUT, ...)` where `OUT = data/NAVTREE.json`)
**What:** `navtree.py` has no `import escalation` anywhere and no call to
`escalation.assert_clear()`. `grep -n escalation src/navtree.py` returns nothing. `main()`
proceeds straight from argparse into `build()` and then, under `--write`, replaces
`data/NAVTREE.json`.
**Why it is wrong:** CLAUDE.md's Hard Rule -1 says the escalation chain "binds every actor
here — human, scheduled run, or local model" and that "every entry point calls
[`escalation.assert_clear`] before doing anything" (quoting `escalation.assert_clear`'s own
docstring, per `withdraw_chapters.py`'s comment on the identical gap it used to have). A second,
more specific criterion is stated in `dashboard.py:1179-1181` citing owner ruling
`aad11acb1183` (2026-09-08): "every entry point that WRITES outside output/ and state/ asks, and
read-only instruments do not." `navtree.py` writes `data/NAVTREE.json` — outside both `output/`
and `state/` — under `--write`, and does not ask. Per `navtree.py`'s own docstring, a stale
`NAVTREE.json` is not a cosmetic problem: "`build_terminal`, `reference` and `sweep` resolve
addresses and shelfmarks THROUGH [it]; a stale one does not fail to answer, it answers with the
previous tree." That is exactly the class of consequential write the interlock exists for.
**Confidence:** Verified directly — `grep -n escalation src/navtree.py` returns nothing, and I
read the whole file, including every function definition. Fourteen (now fifteen with
`withdraw_chapters.py`, per its own comment) production modules do call
`escalation.assert_clear()` (`grep -l assert_clear src/*.py`: allsweep, dashboard, feats,
foreman, hostcheck, ingest_doc, local_agent, overnight, overwatch, pipeline, publish, read,
threads, withdraw_chapters), so this is not a rule the codebase never applies — it is a rule
applied inconsistently. **Caveat on the "should":** the write-outside-output/state criterion I
am citing is stated in a comment inside `dashboard.py`, justifying *dashboard.py's own*
exemption from a *stronger* form of the rule (dashboard is read-only and starts anyway under a
halt). I could not confirm from this batch alone whether that criterion is enforced project-wide
by `verify_math.py` (outside this batch) or is scoped narrower than I am reading it. The
underlying fact (no escalation call in navtree.py) is certain; whether it *should* have one is
inferred from the clearest general statement of the policy I could find in-tree.

### QUESTION — same gap, same file class
**Where:** src/rosetta.py (see below) — noted here because it is the same shape.

No other findings in this file. What I checked beyond the above: `sources_under`'s
strict-descendant matching (order m11), `register_for`'s and the hyperverse-naming loop's
deterministic tie-breaks (order m41), `audit()`'s parent/child sum reconciliation and its
handling of a missing child key without crashing, and `main()`'s exit-code paths (order
3726ed72236c) — all match their documenting comments exactly as written. One thing I traced but
am not filing as a finding: `sorted(nodes, key=lambda x: (len(x.split(".")), x))` in the naming
loop sorts same-depth keys as strings, not numerically (so `"10"` sorts before `"2"`) — this
affects *which* name a given node draws from its type's pool when there is contention, but every
node still gets a unique, valid name regardless of order, so it is cosmetic rather than a
correctness defect. Noting it rather than filing it because I could not show it produces a wrong
answer, only a different (still-consistent) one.

---

## src/render.py (429 lines) — read in full

No new findings. This module carries the same density of prior-fix documentation as navtree.py
(orders 3270e0172391, 3b422bc17939, d1a008863b02, 48c1388144bd, c738ca184269, 707fefc17465,
ea182ee53f5f) and I traced every one of them against the current code:

- `children_of`'s "every prefix key must be present" refusal (orders 3270e0172391 /
  3b422bc17939) is implemented exactly as described — `missing = [t for t in prefix if t not in
  coord]` raises rather than silently pooling.
- The child name is returned uncut (`v[0].split("::")[0]`, order d1a008863b02) — confirmed no
  `[:24]` or similar survives.
- `containment_svg`'s child count vs. layout divisor split (order 48c1388144bd) is present:
  `_kids = len(children)` for the caption, `n = max(1, len(children))` only for the ring
  geometry.
- `write_views()` uses the atomic tmp+`replace_retry` pattern with a pid+thread-qualified temp
  name (order c738ca184269), and is wired into the publish cycle as its own function rather than
  an argparse branch (order 707fefc17465).
- `main()`'s `--probe` path correctly distinguishes "URL formatted" from "URL answered" (order
  ea182ee53f5f).

`render.py` does **not** call `escalation.assert_clear()` either, but unlike navtree.py and
rosetta.py its only write (`write_views()`) lands inside `output/views/` — which the
`dashboard.py`-stated criterion ("outside output/ and state/") would exempt. I am not filing
this one; flagging only for symmetry with the navtree.py/rosetta.py finding above, since the
same absence in this file appears to be the *correct* side of the same line.

---

## src/rosetta.py (793 lines) — read in full

### MAJOR — no escalation/halt check before writing data/ROSETTA.json (same shape as navtree.py)
**Where:** src/rosetta.py, `main()` `--mine` and `--refine` branches (~lines 595-725), which
write `data/ROSETTA.json` and `data/ROSETTA.raw.json` via `silence.write_json`.
**What/Why/Confidence:** identical shape and identical caveat to the navtree.py finding above —
no `import escalation` anywhere in the file (confirmed by grep), and the file writes to `data/`
(outside `output/` and `state/`) under both `--mine` and `--refine`, the latter explicitly
described in its own comments as "the destructive mode." Not re-stating the full argument here;
see the navtree.py entry.

No other findings. What I checked beyond the escalation question: the table-row pairing fix in
`numeric_rows` (splitting on `|-` rather than a sliding window, and taking the first number after
a link rather than the max within a row); the Windows-drive-letter/word-boundary fixes in
`_STAND`, `ORDINAL_LADDERS` and `_SCALE_TITLE` (single-letter grade matching, the `\b` on
"bount"); the Unicode-offset bug fix in `ordinal_rows` (matching on the original text, not a
lowercased copy); `assays_by_host`'s `str.partition` fix for keys with no `|`; the `kept`
counter's placement in `refine()` (order 78f2bebed995, counted only after both the 4-row floor
and the numeric-span filter, not before); and the exit-code fix in `--check` (order tied to
2026-08-26 batch 3). All match their comments. I did not attempt to verify the numeric constants
in `SCALE_QUERIES`/`ORDINAL_LADDERS` against the live wikis (would require network access this
audit did not use), so I cannot confirm or deny whether those lists are complete — only that the
parsing logic around them is internally consistent with what the comments claim was fixed.

---

## src/secondopinion.py (693 lines) — read in full

### MINOR — `_exe()` mislabels "tool ran but returned nonzero" as "no such file"
**Where:** src/secondopinion.py:125-152 (`_exe`)
**What:** `reason` is initialised to `"no such file"` and is only ever overwritten inside the
`except Exception as e:` branch. If a candidate path is found and `subprocess.run([cand,
"--version"], ...)` completes *without raising* but returns a nonzero exit code, the loop simply
falls through to the next candidate without touching `reason`. If every candidate does this,
the function returns `(None, "no such file")` even though a real binary was found and executed.
**Why it is wrong:** `file_orders()` uses the returned reason to decide the remedy message:
`"no such file"` → `"pip install"` remedy; anything else → `"investigate why the process could
not be spawned, do not reinstall"`. A tool that exists on disk but whose `--version` exits
nonzero (for whatever reason) would be told to reinstall a tool that is already installed,
exactly the wrong-remedy class the surrounding comment (order 61d2d34d580a) says this function
exists to prevent for the *other* half of this same distinction.
**Confidence:** Read the function directly; did not run it. In practice this is very unlikely to
fire — `ruff --version`, `vulture --version` and `detect-secrets --version` are not expected to
return nonzero — which is presumably why it has not been caught before. Filing at MINOR because
the code path is real and the mislabelling is total when it does fire, but the trigger condition
is narrow.

No other findings. What I checked beyond the above: the Windows-drive-letter regex fix in
`_vulture` (non-greedy path capture up to `:<digits>:`); the returncode-contract fixes in
`_ruff`/`_vulture`/`_detect_secrets` (0/1 for ruff, 0/1/3 for vulture, 0 for detect-secrets, each
treating other codes as "tool did not actually answer" rather than "clean"); the `NOT_FILED`
table's claim that it only contains codes `RUFF_RULES` actually selects (checked: E402, RUF100,
PLW1510, B007, RUF059, PLW0603, PLW2901, B008 — all in categories E/F/B/BLE/S110/S112/PLE/PLW/
RUF/SIM, matches); the tree-fingerprint-before/after "torn scan" gate in `report()`/`main()`
(order 25a24f24716c / dd673cc2f348); and the three-way AGREEMENT/DISAGREEMENT/UNMEASURED branch
in `report()` (order cee96f28fea4). All match their comments as written.

---

## src/withdraw_chapters.py (519 lines) — read in full

No findings. This is the module CLAUDE.md and its own docstring describe being rebuilt around
the 2026-08-25 incident, and it now has the escalation check (confirmed: `import escalation as
_ESC` and `_ESC.assert_clear(...)` sit above the argparse block, per its own comment "so there
is no path into this job that skips it"). I traced the following claims against the code and all
match:

- `select()` is pure and filters on exact `source_name`/address match, never fuzzy.
- `_file_state()`'s three-way live/gone/unavailable classification (stat, then a directory
  listing check, distinguishing `FileNotFoundError` from any other `OSError`/`ValueError`).
- `_archive_name_free()`'s same three-way logic protecting against `shutil.move`'s
  silent-overwrite-onto-a-file-path behaviour.
- The per-path (`raw_path`/`compressed_path`) vs. per-entry (`stuck`) unit distinction, and the
  `entry_left`/`amended` partial-withdrawal repair (order 1687ff8084b9).
- The stray-sweep's dry-run-vs-`--go` symmetry fix and its "claimed by catalog" vs. "unclaimed"
  distinction (order ba5683e9506a), including the three failure scenarios its comment lists (dry
  run always, a stuck entry that later clears, and an archive-name collision reported twice).
- The manifest-merge-not-replace fix for two `--go` runs sharing a `--label` (order
  959ac19ac3f7).
- The final `bad`/return-code computation, gated correctly so a dry run always returns 0 and a
  selector matching nothing raises `SystemExit` before reaching it.

I did not independently exercise the snapshot subsystem (`snapshot.before`/`snapshot.verify`) —
that module is outside this batch — so I can only confirm this file calls it and checks its
result (`if not ok: raise SNAP.SnapshotFailed(...)`), not that `snapshot.py` itself behaves as
advertised.

---

## src/dashboard.py (1249 lines) — read in full

No findings. This file has clearly been through many rounds of fixes (run #19, #26, #28, #34,
#37, and orders e7ea68901bfe, c003673cff01, 7bebaa921ef3, ffdaa9aa7288, 50c9f6130b95,
ef7a5b8b56a5, and the `aad11acb1183` ruling discussed above under navtree.py). I traced the
following against the code and all match:

- `movement()`'s history-file self-healing: a torn JSON file, a list of non-dicts, and a dict
  whose `at` field is non-numeric are all caught by one guard before the append/write, and the
  guard's failure path resets and re-writes rather than wedging (three layered fixes, orders
  62286a6c018a and c003673cff01).
- `movement()` compares each sample against `hist[:-1]` (prior samples), never against the
  just-appended current row, on cold start.
- The `reset`-on-negative-delta handling for the `chunks` counter (run #26), so a reader restart
  cannot read as forward progress.
- `_read_row`/`_roll_row`'s fault isolation (`jobs()` guards the `lognames` import itself, not
  just the two row-builders, order e7ea68901bfe).
- `safety()`'s FileNotFoundError-vs-any-other-exception split for both `drill_last.json` and
  `escalation.log`, distinguishing "never run yet" from "could not be read" in both cases.
- `main()`'s read-only-instrument exemption from the halt-refuses-to-start rule (the
  `aad11acb1183` ruling): the import-failure fail-closed guard still refuses to start outright,
  but a *raised* halt is rendered on the page rather than refusing the daemon.
- The uncut findings/quarantine/breached-nets lists (Hard Rule 0, several orders across
  2026-08-24) are genuinely uncut in the current code — no `[:N]` slicing survives on any of
  them.

One thing I checked and am **not** filing, only noting: `quotas()` wraps its entire body in one
`try`/`except Exception`, and if an exception fires partway through the `for bucket, m in
sorted(seen.items())` loop (after some buckets have already been appended to `out`), the handler
appends a `"quota read failed"` entry on top of the partial results rather than clearing them.
This produces a mixed partial-result-plus-error-marker list rather than either a clean partial
list or a clean failure, which is unusual but not obviously wrong — the page would show real
data for buckets that succeeded before the fault, plus a marker that something else failed. I
could not find a plausible input that reaches this path (the only `Exception`-raising code
inside the outer try that is not already caught by the inner `try` around `model_status` would
have to come from `router.models` iteration, `st.get(...)`, or arithmetic on `v.get("cap")`/
`v.get("left")` — all defensive already), so I'm recording it as checked-but-not-filed rather
than a finding.

---

## src/assay.py (1914 lines) — read in full

No findings. This is the single most heavily self-audited module in the batch — it documents
its own history of at least a dozen distinct fixes (the X.11 faculty-weight erratum, the M3
band-floor correction, the `axis_score` top-rung ordering fix, the halved-interval /
`_SCALE`-anchoring fix, the covariance-term addition, the `_check_scores`/`_check_weights`/
`_check_readings` three-door validation layer, the ceiling-and-floor decimal clamp, and the
`_check_constants` cross-table consistency checks) and I worked through the arithmetic of each
one rather than only reading the prose:

- **`axis_score`**: confirmed the lookup-order fix (structural errors — off-Ladder band, a
  non-energetic axis, a misspelt axis — are all raised *before* the quantity is examined, so the
  top rung's `9.9` shortcut cannot mask any of the three), and confirmed the below-floor clamp
  (`0.0 if x < lo`) still applies on the top rung.
- **`_interval`**: traced the variance-propagation formula, including the covariance term
  (`Var = Σᵢ Σⱼ wᵢwⱼ ρᵢⱼ σᵢσⱼ` with the diagonal folded into the first loop and cross-terms in
  the second), the `max(var + cov, 0.0)` floor against a hypothetically negative variance, and
  the unit conversion (`/10` before squaring, to bring the 0-9.9 axis scale into the 0-1 decimal
  scale) before combining with between-hand variance.
- **`_check_constants`**: worked through each of its assertions (attestation-sigma monotonicity
  and ceiling; `BAND_EDGES` completeness, agreement with `LADDER`, and strict-increase on every
  axis between adjacent rungs; `ATTESTATION_FLOOR`'s parallel monotonicity check;
  `INSTRUMENT_WINDOWS`/`FACULTY_READS` agreement with the Ladder and `WEIGHTS`; and the
  three-way partition of `WEIGHTS` into `BAND_EDGES` axes and `NON_ENERGETIC_AXES`, checked
  disjoint and exhaustive) and confirmed the numbers currently in the tables actually satisfy
  every one of these (e.g. `SIGMA_BY_ATTESTATION` values are strictly increasing:
  Instrumented < Witnessed < Transcribed < Reconstructed < Disputed, and `SIGMA_MAX` equals the
  Disputed value exactly, so no assertion here is close to its own boundary by accident).
- **`calibration_report()`**: re-derived the sweep bounds by hand (`SIGMA_MAX` ≈ 3.7444,
  `saved` (Witnessed) = 1.7973, sweep range 0.5 to 3.7444 in steps of 0.005 ≈ 649 iterations) and
  confirmed this matches the comment's claim of "the real figure is 649" rather than the
  superseded "~800".
- **`assay()`**'s ceiling/floor clamp (`_dec >= 0.995` / `_dec < 0.0`) is keyed on the same
  0.995 threshold the `moth_number` display's `round(_dec * 100)` would otherwise overflow at
  (order 2a0d854b0b68) — confirmed the two thresholds actually agree (0.995 rounds to 100 at two
  decimal places of `_dec*100`, matching the guard).
- **`interval_from_hands()`**'s covering-widening loop and its `covers_all_signatures` /
  `covered_before_widening` distinction (a guarantee vs. a genuine measurement) are structurally
  guaranteed to agree with the loop's own termination condition, as the comment claims.

I did not attempt to independently re-derive `_ANCHOR_SIGMA = 1.7973` from first principles
(that would require re-solving the calibration equation myself rather than checking the code's
internal consistency), so I cannot certify that constant is *itself* correct against the
charter's Kenshiro example beyond what `calibration_report()` already checks at runtime — I can
only confirm the module's own self-check (`_check_constants()`, run at import) does not fail
against the numbers currently on file, and that `calibration_report()`'s logic for verifying it
is sound.

---

## src/ledger.py (220 lines) — read in full

No findings. This module is marked **HELD, not wired** by owner ruling (Ruling 9 of 2026-09-08,
order 3fb9fc6b9999) — its own docstring explains at length why it has no caller in the
generation pipeline and why that is deliberate. Per the brief's instruction to note
owner-marked-and-kept code rather than re-file it: I saw the marking (`STANDARD_GLYPH`,
`CONDENSATES`, and `currency_status()` are each individually marked "REPORTED DEAD, NOT
DELETED" under order 1a9c237dda4d) and moved on.

I did check the live arithmetic anyway, since it is exercised by `verify_math.py` even without a
pipeline caller:
- `to_standards`/`from_standards`/`cross_rate` are consistent inverses of each other (verified
  the algebra: `cross_rate(a,b) = rate_b/rate_a` correctly answers "units of b per unit of a"
  given `CURRENCIES` stores "units of local currency per Standard").
- `assay_to_standards()`'s M10 handling — the file's own comment describes a bug where M10's
  ceiling collapsed to its own floor (`hi == lo`) and was fixed by borrowing the M9→M10 gap
  width anchored at M10's own floor. I re-derived this by hand: `hi = lo * (lo/prev)` puts
  `log(hi) - log(lo) = log(lo) - log(prev)`, i.e. exactly the M9→M10 log-width, anchored at M10's
  floor rather than shifted to M9's — matches the comment's claim.

---

## src/chord_field.py (210 lines) — read in full

No findings. Small, self-contained physics-reference module (six thought-experiment
adjudications plus four small formulas: `total_beta`, `landauer_floor`, `recoil_momentum`/
`recoil_velocity`, `critical_power_self_focus`). Checked each formula against the standard
physics it claims to implement:
- `landauer_floor`: `bits * k_B * T * ln(2)` — correct form of Landauer's principle.
- `recoil_momentum`: `E/c` — correct minimum-momentum bound for a directed energy beam.
- `critical_power_self_focus`: `3.77 * λ² / (8π·n₀·n₂)` — matches the standard Marburger
  critical-power formula for Kerr self-focusing.
- `total_beta`/`per_system_beta_without_unification` are simple sums/products over the
  `ADJUDICATIONS` table's `beta_bits` field; no off-by-one or wrong-key access found.

The module's own comment about removing unused `G_NEWTON`/`HBAR` constants (kept nowhere,
re-declared nowhere) checks out: `grep -n "G_NEWTON\|HBAR" src/chord_field.py` finds only the
comment describing their removal, not the names themselves.

---

## Summary of what I could NOT verify (flagged rather than assumed clean)

- Any external data (wiki content for `rosetta.py`, live host lists) — this audit did not run
  network calls, so parsing-logic correctness was checked against the code's own worked examples
  in comments, not against live pages.
- `snapshot.py`, `escalation.py`, `silence.py`, `codewatch.py`, `axis_correlation.py`,
  `cascade_bridge.py`, `standards.py`, `liveness.py`, `weave_index.py`, `feats.py`, `pipeline.py`
  and `verify_math.py` — all outside this batch and imported/called by these modules. Where a
  finding above depends on one of these behaving as documented (e.g. `silence.write_json`'s
  return-value contract, `escalation.assert_clear`'s actual enforcement), I have said so at the
  point it matters rather than treating it as confirmed.
