# run39 — AUDIT, batch 13

Modules owned (obtained from `sweep_plan.batches(16)[12]['modules']`, not from a typed list) and
read IN FULL, no sampling:

    assay.py (1374 lines)          rigor.py (956)          custodes.py (683)
    estate.py (543)                address.py (419)        cosmography.py (335)
    resync_roll.py (287)           descending_ladder.py (226)

`assay.py` was read from the LIVE file only; `mutate.py` was not run and the sandbox copy was
not touched.

Every finding below was reproduced against the live source before it was written down. Where two
readings are defensible it is filed as a QUESTION at the foot, not as a finding.

---

## MAJOR

### R1 — `rigor.theorem_1_check()` reports `both_say_consistent: True` on a matrix it computed nothing from
`src/rigor.py:231-269` (`theorem_1_check`), `src/rigor.py:181-202` (`perron_weights`),
`src/rigor.py:205-229` (`logrank_weights`)

Both docstrings require a POSITIVE reciprocal matrix. Neither checks. Measured live:

    A = [[1, 3, 0], [1/3, 1, 3], [0, 1/3, 1]]
    theorem_1_check(A) -> logrank_weights [nan nan nan]
                          CR   -0.5049883082990546
                          eta   1.0
                          both_say_consistent  True

Two independent one-sided tests, each of which alone produces the wrong verdict:

* `rigor.py:266` — `bool(p["CR"] < 1e-9 and lr["curl_fraction"] < 1e-9)`. CR is built from
  `(lam - n)/(n - 1)`; for a genuine positive reciprocal matrix Saaty's theorem puts
  `lambda_max >= n`, so a NEGATIVE CR is itself the signal that the input was not one. The test
  `< 1e-9` reads that signal as *maximally consistent*. `perron_weights`' own returned field
  `"coherent": bool(cr < 0.10)` (`rigor.py:202`) is one-sided in the same way and answers True
  for the same matrix.
* `rigor.py:224` — `eta = (grad_sq / total) if total > 0 else 1.0`. With a non-positive entry,
  `np.log(A)` makes `grad_sq` and `res_sq` nan, `total > 0` is False, and the `else 1.0`
  fallback hands back "the log-flow is a pure gradient" — the strongest possible finding — for
  an arithmetic that produced nothing. That is the same conflation
  `resonance.hodge_decompose` draws a line under (an empty edge set vs. a perfectly consistent
  ladder) and that `custodes.staleness_widening`'s own docstring cites as its rule.

This is the module's headline check: §2's claim is that commensuration "is never assumed; it is
ATTEMPTED, and the attempt reports its own residual". On a bad input the attempt reports the
residual as zero. `theorem_1_check` and `consistent_matrix` have no consumer outside
`rigor.main()` today, which is why it has not surfaced.

**Remedy.** Validate at the head of `perron_weights` and `logrank_weights` — square, finite,
strictly positive, reciprocal to tolerance — and RAISE rather than return; make both consistency
tests two-sided (`abs(CR) < 1e-9`); and make the `total > 0` fallback return `eta=None` with a
stated reason ("no flow to decompose") instead of 1.0.

### S1 — `resync_roll` prints POST-fix figures under a "(pre-fix figures)" label on the branch where nothing landed
`src/resync_roll.py:130-168` (the repair loop), `src/resync_roll.py:261-272` (the denied branch)

In the non-dry path the loop mutates the in-memory rows before any write is attempted:

    resync_roll.py:133-135   if not dry:
                                 r["entry_count"] = n
    resync_roll.py:166-168   if not dry:
                                 r["status"] = want

`roll` is the list those rows belong to. When `roll.mutate` refuses (`landed` False), the closing
block recomputes from that same mutated list:

    resync_roll.py:263   have = sum(1 for r in roll if r.get("entry_count", 0) > 0)
    resync_roll.py:264   print(f"\nroll unchanged: {have}/{len(roll)} sources catalogued (pre-fix figures)" ...)

Any row repaired from 0 to a positive count is inside `have`, so the number printed is exactly
the count the roll WOULD have carried had the write landed — printed on the one branch whose
entire purpose is to say it did not. This is the reporting half of the fault order 8605c2ed6061
closed in the exit code: "the run reported that the roll now agrees with the record files when
the file on disk was unchanged".

**Remedy.** Take the `have`/`total` snapshot from `roll` immediately after `json.load`, before the
repair loop mutates it, and print that snapshot on the denied branch — or stop mutating the
snapshot at all and let `_apply` be the only writer, which is the shape order f818a77293fc
already moved this module toward.

---

## MINOR

### A1 — `assay.interval_from_hands`'s `covers_all_signatures` is a tautology
`src/assay.py:1343-1344` (the widening loop), `src/assay.py:1352` (the field)

    while any(abs(v - centre) > interval for v in vals):
        interval = round(interval + 0.01, 2)
    ...
    "covers_all_signatures": all(abs(v - centre) <= interval for v in vals),

The loop exits precisely when the field's expression is True, and the two expressions are
character-identical in the quantities they read. Measured live, including a deliberately hostile
input: `interval_from_hands({'AVAR': 0.0, 'QUILL': 30.0}, attestation='NONSENSE')` returns
`covers_all_signatures True` with `interval 15.0`.

The docstring sells this field as constraint 1 of two "hard constraints, both from the charter":
"THE INTERVAL MUST COVER EVERY SIGNED READING ... An interval that excludes a signatory's value
is not a measurement, it is a suppression." What is published is a guarantee, not a check, and
nothing at the field says so. `custodes.py:539-551` carries the identical shape and DOES say so
(m30) — so this project has already ruled on how to present it, in the other file.

**Remedy.** Say what custodes says, at the field. And add the datum that would be genuine
information: whether the quadrature interval covered every signature BEFORE the loop fired, and
how many hundredths the loop had to add — that is the "did the widening have to happen" number
custodes' m30 note raises as the missing one.

### A2 — `assay.band_for_quantity` answers "M0", confidently, for any axis it has no edges for
`src/assay.py:234-250` (definition at 234; the loop at 246-250)

    out = "M0"
    for b in LADDER:
        if x >= BAND_EDGES[b].get(axis, math.inf):
            out = b
    return out

`BAND_EDGES` carries floors for five axes (ruin, reach, celerity, sustain, continuity). The other
six Measures in `WEIGHTS` — transgression, vector, volition, acumen, discernment, suasion — have
none, so `.get(axis, math.inf)` makes every comparison false and the initialiser survives.
Measured: `band_for_quantity(1e50, "acumen")` -> `"M0"`. `x <= 0` correctly answers None; an axis
this ladder cannot measure answers with a band.

This is the same defect `cosmography.kardashev_to_magnitude` was repaired for under order
be783948fd66 — its docstring: "`reached` was initialised to `ladder[0]` and the loop below only
ever RAISES it, so a budget orders of magnitude beneath the lowest Ruin edge came back reported
as reaching M0 ... the docstring said REACHES and the code said 'at least the bottom', which are
different claims, and the wrong one is the flattering one."

**Remedy.** Return None when the axis has no floor on this ladder. The sub-floor case for a REAL
axis must keep answering "M0" — `verify_math.py:5686` pins `band_for_quantity(1.0, "ruin") == "M0"`
— so the fix is on the missing-axis case only.

### A3 — `assay.axis_score` returns None for five different conditions and names none of them
`src/assay.py:213-231`

`None` is returned for: `x is None`; `x <= 0`; `band not in BAND_EDGES`; the axis has no floor or
no ceiling; `hi <= lo`. Measured live, all None: `axis_score(1e30, "M3", "transgression")`,
`axis_score(5.0, "M3", "acumen")`, `axis_score(5.0, "MX", "ruin")`, `axis_score(None, "M3", "ruin")`.
Six of the eleven Measures are permanently in the missing-floor case. `anchors.py:37-40` says so
in prose — "The six axes with no entry in BAND_EDGES are not unscalable ... axis_score() silently
returns None for them, leaving an assessor no guidance" — and then works around it rather than
distinguishing it in code.

**Remedy.** Keep None for "not scorable from this quantity", but raise `AssayIntegrityError` for a
band that is not on the Ladder (a caller error, not a reading), and refuse the six non-energetic
axes by name, quoting the real scale each one lives on — `anchors.NON_ENERGETIC_AXES` already
holds that text and is the natural place to import it from.

### R2 — `rigor.gumbel_return_level` returns a different SHAPE out of domain, and conflates three conditions
`src/rigor.py:711-713`

    if n_scored <= 0 or n_entries <= n_scored or tail_index <= 0:
        return {"correction_bits": 0.0, "corrected_bits": sample_max_bits, "tail_index": tail_index}

Measured: out-of-domain keys are `['corrected_bits', 'correction_bits', 'tail_index']`; the normal
return also carries `'basis'`. A caller reading `["basis"]` gets a KeyError only on the branch it
is least likely to have exercised. Worse, the three conditions folded together are three different
statements: "nothing has been scored" (an error), "the read is COMPLETE, n == N" (a finding, and
the good one), and "the tail index is inadmissible" (an error). All three publish a silent zero
correction, so a completed read is indistinguishable from a broken call.

**Remedy.** Return the same keys on both branches and add a `reason` naming which condition fired.

### R3 — dead ternary in `rigor.adjudication_beta`
`src/rigor.py:549` — `b_which = _log2_choose(M, k) if k < M else 0.0`

`_log2_choose` (`rigor.py:519-523`) already returns 0.0 when `k >= n`. Verified:
`_log2_choose(12, 12) == 0.0`, and `adjudication_beta(99, 1)["which_laws_bits"] == 0.0` by either
route. **Remedy.** Drop the ternary.

### R4 — `rigor.faculty_parity_weights` hardcodes the axis counts the module header forbids restating
`src/rigor.py:154` — `def faculty_parity_weights(n_physical=8, n_faculty=3)`

The module header (`rigor.py:28-36`) spends a paragraph on exactly this class, for the weights:
"DELIBERATELY NO NUMBERS ARE RESTATED HERE (order d444e7a90cff) ... name the live tables, never
copy them, so the next re-weighting cannot strand this paragraph a second time." One screen below,
the axis COUNTS the same tables imply are copied into a signature, and `rigor.main()` prints the
result immediately beneath the live `A.FACULTY_WEIGHTS` line (`rigor.py:787-789`), so the two
would silently part company the day an axis is added.

**Remedy.** Default from `len(assay.CHARTER_PHYSICAL_WEIGHTS)` and `len(assay.FACULTY_AXES)`.

### C1 — `custodes.main()` cuts every Custos's refusal mid-word, unmarked
`src/custodes.py:638` — `print(f"{n:<11}{c['dof']:<17}{c['charter']:<16}{c['refuses'][:44]}")`

Measured against the live table: 9 of the 10 entries are longer than 44 characters and are cut.
Cassia's "category error; she will strike an axis before she will score it badly" prints as
"category error; she will strike an axis befo" — the half that carries the meaning is gone. Hard
Rule 0. The same function already gets this right one screen down, at `custodes.py:658`, where the
abstention text is cut at 76 and an explicit `...` is appended.

**Remedy.** Widen the column or append the ellipsis, as that line does.

### E1 — `estate.external()` conflates three faults under one message, and stays silent on a fourth
`src/estate.py:506-513`

    try:
        import yaml
        cfg = yaml.safe_load(open(...config.yaml...))
        want = cfg.get("model")
        if want and want not in names:
            note("config.yaml NAMES A MODEL OLLAMA DOES NOT HAVE", want, bad=True)
    except Exception as e:
        note("config.yaml unreadable", str(e)[:70], bad=True)

PyYAML not installed, config.yaml absent, and config.yaml malformed all report as "config.yaml
unreadable", which sends whoever reads the estate report to open the wrong thing — the same
mis-routing the SECOND HANDLER in `charter()` (`estate.py:301-311`) was added to prevent, with
that comment saying so explicitly. And a config carrying no `model` key emits NO row at all,
because `if want and ...` (estate.py:510) is skipped: "the config names no model" is invisible and reads exactly
like "the config names a model Ollama has".

**Remedy.** Split the import from the read, and emit a row when `want` is falsy.

### D1 — `address.tier_rank` ranks an unknown tier equal to the lowest one, so `promote()` preserves corruption
`src/address.py:390-393` (`tier_rank`), `src/address.py:396-408` (`promote`)

    return order.index(tier) if tier in order else 0

Verified: `tier_rank("KINGDOM") == tier_rank("volume") == 0`; `promote("KINGDOM", 0)` returns
`"KINGDOM"` unchanged, and `promote("KINGDOM", 5000)` returns `"set"`. So a corrupt or renamed
tier on a source's row survives every routine promotion pass for as long as the source stays under
400 entries — it is never repaired and never reported. This is an addressing module and Hard Rule 2
territory: the value being preserved is part of a source's shelf address.

**Remedy.** Return None (or raise) for an unrecognised tier, and have `promote()` treat an
unrecognised `current` the way it treats None — take `earned` — so a bad value is repaired instead
of carried.

### S2 — `resync_roll`'s two repair tables cut source names at 44 with no marker
`src/resync_roll.py:217` and `src/resync_roll.py:225` (`name[:44]`), plus `str(was)[:14]` at 225

Verified against the live roll: 11 of 215 rows carry names longer than 44 characters, e.g.
`The Amethyst / Cockroach King screenplay (Ch` (56 chars),
`DMs Guild: Xanathar's Lost Notes to Everythi` (51). These two tables are what a person reads to
decide which record file to open, and the module's own comment eleven lines below insists the
unreadable/unmatched lists are "UNCAPPED, both of them, per Hard Rule 0: these are lists a person
reads in order to act ... a truncated list of them would quietly decide which sources are worth
the reader's attention". The identical argument applies to a truncated NAME.

**Remedy.** Append an ellipsis and widen, or print the full name on its own line.

### S3 — stale cross-reference: `silence.py:366-367` does not hold what `resync_roll.py:188` says it holds
`src/resync_roll.py:187-189`

    # THE VERDICT IS NOT OPTIONAL. The writer returns False rather than raising on a
    # denied replace (silence.py:366-367), and this call used to discard that return ...

`silence.py:366-367` are two comment lines inside the compare-and-swap's rationale block:

    366  # is this window running backwards.
    367  #

Verified against the current file. The behaviour cited lives at `silence.py:397-406` (the
`except PermissionError` branch returning `(False, "... nothing landed. Retry next round.")`) and
`silence.py:408-414` (the `except OSError` branch).

**Remedy.** Cite `silence.cas_replace`'s PermissionError branch by NAME rather than by line — which
is the ruling `verify_math`'s §20f block and `rigor.py:139-145` both already argue for ("a section
tag rather than a line number, because a line drifts and a tag does not").

### L2 — `descending_ladder.shrink_report` grades a bad argument as an attested black hole
`src/descending_ladder.py:156-183`

Measured: `shrink_report(70.0, 1.0, 0.0)` returns

    objections               ['BLACK HOLE: target size 0.00e+00 m is inside the Schwarzschild
                              radius 1.04e-25 m for this mass']
    mass_conserved_is_lawful  False
    target_rung               None
    density_kg_m3             None
    confinement_energy_J      None

`density_at_scale` and `compton_confinement_energy` both refused the input and returned None;
`rung_for_length` correctly answered `(None, None)`. Only `to_m < r_s` at line 176 had no guard,
so the single objection raised — and the one that sets `mass_conserved_is_lawful: False`, which
the docstring says "downstream reads as a statement about the fiction" — is the wrong finding
about the wrong thing. A non-positive length is a caller error, not a suspended law, and the
docstring itself draws that exact line for `is_descent`: "an attested trajectory that goes the
other way is not a violation of physics, it is a caller asking the wrong function, and the
objections list is reserved for laws that had to be patched".

**Remedy.** Refuse `to_m <= 0` at the top, returning `mass_conserved_is_lawful: None` and a
separate `input_error` field, keeping `objections` for laws. `rung_for_length` already carries the
right convention two functions up.

---

## INFO

### A4 — `assay.REFERENCE_JOULES` is read by nothing
`src/assay.py:195-209`. A grep across every `.py` and `.md` in the tree returns only the
definition. `magnitude.py:411` carries an overlapping unit table of its own (`"kiloton": 4.184e12`),
so the quantity exists twice with only one live copy. **Remedy.** Wire it (magnitude.py's converter
is the natural consumer) or mark it documentary.

### A5 — `assay.HANDS` is read by nothing
`src/assay.py:1277-1288`. No code reads it; the section is prose that happens to be a dict.

### C2 — `custodes.table_faults()` is a declared safety with no caller but `main()`
`src/custodes.py:584-617`. Confirmed by grep across `src/`: the only occurrences are the definition
and `custodes.py:630`. Its own docstring says the deferral was deliberate and names the fix — "One
line there against this function turns the next occurrence into a red battery instead of an audit
finding three sweeps later" — so this records that the deferral is STILL open as of run39, not that
it was hidden.

### E2 — every error detail in `estate.py` is cut with no marker
`str(e)[:50]` at `estate.py:178`; `[:60]` at 182, 185, 192, 195, 198, 205, 209, 542; `[:70]` at 424, 449,
482, 513; `[:80]` at 305, 325. A `json.JSONDecodeError` carries its line and column at the END of
the message, which is the part these cuts remove. **Remedy.** Append "…" when the cut fires.

### D2 — half of `address._FILLER` is unreachable
`src/address.py:39`. `_token_set` (`address.py:46-48`) matches `[a-z0-9]+` and keeps only
`len(w) > 1`, so `"a"`, `"1"`, `"2"`, `"3"`, `"&"` and `"-"` can never be tested against the set.
Verified: the reachable subset is `{all, and, associated, incl, its, the}`. **Remedy.** Drop the six,
or drop the length filter if single-character tokens were meant to be excluded by name.

### G1 — two cosmography constants are declared and read nowhere
`src/cosmography.py:46` (`GALAXIES_CONSELICE_2016`) and `src/cosmography.py:52`
(`STARS_MILKY_WAY`). Both are deliberate — the Conselice figure is kept because "the disagreement
is real and the library's own doctrine is to file both readings rather than silently average" —
so this is recorded, not filed as breakage. It is worth a marker nonetheless: this module's own
admissibility contract is DECLARED / DERIVABLE / REVERSIBLE ("change one, re-run, and every
downstream figure moves with it"), and for these two nothing moves.

### L1 — four dead constants and one dead function in `descending_ladder.py`
`PLANCK_TIME` (`:41`), `PLANCK_MASS` (`:42`), `BOLTZMANN` (`:50`), `FOLD_GLYPH` (`:88`) each occur
exactly once in the file — their own definition — and nowhere else in `src/`. `rung_table()`
(`:92-94`) has no caller anywhere. This sits inside the standing OWNER order already filed against
the whole module ("descending_ladder.py has no functional consumers anywhere in src/",
handoff/queue/OWNER.md:158), but these five would still be dead if the module were wired tomorrow,
which is why they are listed separately.

### R5 — stale cross-reference into rigor from another batch's module
`src/verify_math.py:4076` reads "§20f  kept by §26 (rigor's prose)  -- cited by rigor.py:123 and
BUGS.md m88, m89". The §20f citation in rigor.py is at **line 143**; line 123 is
"the whole content of the coherence framework:", a prose line in `measure_bit_value`'s docstring.
`verify_math.py` belongs to another batch — filed for the record so it is not lost.

---

## QUESTIONS (two defensible readings; deliberately NOT filed as findings)

**Q1 — `assay._check_constants`'s last two branches cannot fire.** `src/assay.py:570-601` (`_check_constants`; the two branches at 594 and 599).
`SIGMA_UNKNOWN` and `SIGMA_MAX` are both bound to `SIGMA_BY_ATTESTATION["Disputed"]`, which IS
`max(vals)`, so `max(vals) > SIGMA_UNKNOWN` and `max(vals) > SIGMA_MAX` are both false by
construction. The docstring anticipates this reading exactly, names the two source edits each
branch is watching for, records that run #34 order 02277646a783 already read them as dead, and
says "Do not delete them as unreachable". Both readings are correct about different things — they
are unreachable for edits to `_RAW_SIGMA` and live for edits to the two derived constants. Raised
so the next sweep does not re-file it a third time.

**Q2 — `custodes.covers_every_reading` is the same tautology as A1.** `src/custodes.py:539-551`.
It is declared as such at the field (m30). The open question is not whether it is a tautology but
whether both files should replace it with the informative version — did the covering widening have
to fire, and by how much. custodes' own note calls that "an addition to the contract, not a
repair". A1's remedy is written to match, so the two can be closed together.

**Q3 — `descending_ladder.rung_for_length`'s `best = DESCENDING[0]` initialiser is now unreachable.**
`src/descending_ladder.py:118`. The `metres > DESCENDING[0][3]` guard two lines above guarantees
the first loop iteration assigns `best`. The docstring records that this initialiser WAS the bug
(it "used to leave `best` at its initialiser and report 'Continental' for anything larger"), so
keeping it is defensible as a structural backstop in the same voice as `assay()`'s kept `or 1.0`.
Left as a question rather than a dead-code finding.

---

## Verified NOT defects (checked and cleared, recorded so they are not re-opened)

* `custodes.py:355` cites `anchors.py:190` as "the single real call site" of `convene()` passing
  neither `eta` nor `distance`/`years_since`. Confirmed: `anchors.py:190` is the `CU.convene(...)`
  call, and a grep over `src/` finds no other production caller (the rest are `custodes.main()`
  and `verify_math`).
* `assay.py:1103` cites `anchors.py:186` for "callers hand this the whole numeric score dict".
  Confirmed: `anchors.py:186` is the `A.instrument(...)` call with the numeric-filtered dict.
* `address.py:226` cites `catalogue_web.py:68-95` as "thirty lines documenting" the `[:60]` slug
  cap. Confirmed: the HARD RULE 0 block runs 68-94 with the import at 95.
* `address.py:234` claims `slugify` has "exactly two call sites ... and manifest_builder.py:247".
  Confirmed by grep: `address.py:302` and `manifest_builder.py:247`, and line 247 is
  `cat = slugify(roll_entry.get("category", "Uncategorized"))`.
* `resync_roll`'s duplicate-source claim "winner is the last name alphabetically" is correct:
  `for fn in sorted(os.listdir(RECORDS))` with an unconditional `by_source[key] = (rec, fn)`, and
  the `dupes.setdefault(key, [by_source[key][1]]).append(fn)` chain lists every file, not just two.
* `estate`'s `bad=True` grading is genuinely consumed: `allsweep.estate_faults()`
  (`allsweep.py:560`) counts exactly those rows.
* `assay._rho_doc()` is NOT in fallback on this machine: `_rho_source()` returns
  "measured: data/AXIS_CORRELATION.json" and `RHO_FALLBACK_REASON` is None.
* `assay.PLANCK`-style constant arithmetic in `descending_ladder`: `PLANCK_ENERGY 1.956e9` checks
  out against `PLANCK_MASS * C_LIGHT**2 = 1.9561e9`.
* `cosmography.SIZE_CLASSES` POCKET/MINOR now REFUSE via `validate()`; no caller uses them
  (`census("STANDARD")` is the only invocation in `src/`), so the refusal is dormant by design and
  the owner ruling it waits on is correctly left open.
