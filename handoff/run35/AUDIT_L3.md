# run35 LOCAL batch L3 — audit

## 0a77fa43d821 — assay.py `_check_scores`, NONE sentinel checked by identity
Verified against source and by running it: `_check_scores` tested `v is NONE` for the NONE
sentinel while its two siblings (`INAPPLICABLE`, `UNESTIMABLE`) were tested by `in` (equality).
`json.loads('"none"') is A.NONE` measures `False` — a fresh string from disk is never the
interned module literal — so a `none` score read off any real record raised
`AssayIntegrityError` and reported "not a number" instead of being recognised as the sentinel it
is. FIXED: changed the identity check to an equality check, same shape as the other two
sentinels (`assay.py`, `_check_scores`). Confirmed `A.assay('M3', {'ruin':2.1,'reach':json.loads('"none"')}, worksheet='w')`
now returns a decimal instead of raising. `_check_scores` is not on the protected
signature/return-key list, and this changes neither.

## 3cf9bafb03ed — profile.py module docstring, stale "74-bit" claim
Verified: `address_space.TOTAL_BITS` computes to 89 at runtime (`address_space.py`'s own WIDTHS:
3+3+3+8+6+38+27+1), and that module's comment says explicitly the 74-bit/five-field number went
stale once already and must not again. `profile.py`'s docstring still said 74. FIXED: one-word
change, "74-bit" to "89-bit" (`profile.py:20`). No other "74" reference in the file.

## 52f1a4d278ea — anchors.py `__main__` comment, stale exit-status claim
Ran `python src/anchors.py`: `monotone floor -> ceiling : True`, exit 0, confirming the
comment's claimed "It exits 1 TODAY" is stale — the owner ruling of 2026-08-25 (recorded 30
lines above, at the `order` list) reordered the declared ladder to match the assay, and the
invariant has held since. FIXED: rewrote the comment in past tense describing what run #26
measured and why it changed, without weakening the "still exits 1 if it disagrees again"
guarantee the comment exists to state.

## 61ca2388367c — rigor.py `main()`, unconditional MDL finding
Verified: the per-row `ok = "above floor" if declared >= floor else "BELOW FLOOR"` computation
was printed inside the loop, but the summary `FINDING: every declared cost sits above its MDL
floor` printed unconditionally two lines later — the exact shape already fixed 30-odd lines
above for the faculty-weight section. FIXED: collected an `_underpriced` list during the loop and
branched the FINDING message on it, mirroring the existing `_muted` pattern. Ran `main()`
end-to-end: with today's data (all 5 declared costs above floor) the output is unchanged.

## 6d0ecf0fdc3c — profile.py ROUND TRIP check, tautological comparison
Verified: `decode()` echoes its own argument back as `d["profile"]`, so
`d["profile"] != r["profile"]` compares an object to itself — confirmed
`decode(s)["profile"] is s` is `True`. Only the `address` field was a real check; genre,
register, features, band and attested_axes were decoded and never compared to anything. FIXED:
replaced the tautology with a re-encode of everything `decode()` extracted, compared against the
original profile string — this exercises all five previously-unchecked fields, because a wrong
decode of any of them would produce a different re-encoded string. Verified with a synthetic
profile that the round trip both passes normally and would flag if the decode logic were wrong.

## 71dfbc345f2a — handbuilt.py `--full`, TypeError on string-sentinel scores
Verified by running `python src/handbuilt.py --full`: before the fix this raised
`TypeError: must be real number, not str` on Zalama's `ruin`/`continuity`/`celerity`/`vector`/
`volition`/`discernment`, all recorded as the string `"unestimable"`. FIXED: format the score as
`%5.1f` only when it is actually a number, else as a right-justified string of the same width.
Ran `--full` again end-to-end (exit 0) and confirmed the Zalama sheet renders all eleven axes,
five of them printing `unestimable` cleanly.

## 80ca00f00cbe — physics.py `--table`, help text vs. behaviour disagree
Verified: the table prints unconditionally before the `if a.table: return 0` check, so `--table`
only ever suppresses the three worked examples that print afterward — measured, `--table` output
is a strict prefix of the bare-invocation output. The help text said "print the specific
energies", describing the unconditional default rather than the flag's actual effect. FIXED:
reworded the help text to say what `--table` does (print only the table, suppress the worked
examples), rather than changing the ordering — the ordering already matches the file's evident
intent (the table is baseline context, the examples are optional extras).

## 85a1d426681d — magnitude.py `--calibrate`, exit code ignores partial reproduction
Verified: `calibrate()` returns `band_hits`, an int 0-6, and `main()` did
`return 0 if calibrate() else 1` — truthy on any nonzero count, so 1-of-6 benchmarks reproducing
its band exited 0. Cross-checked against `standards.py`'s own
`charter_regression_verdict`, which requires every SCORED row `consistent` (zero `bad`) for "the
automation reproduces the charter" to hold — confirming the CLI exit code should mean full
reproduction, not any. FIXED: `return 0 if calibrate() == len(BENCHMARKS) else 1`. No other
caller of `magnitude.calibrate()` exists in `src/` (grepped) so nothing else is affected.

## b124bcb46f86 — handbuilt.py, stale "four" count in The Sentry's why_missed
Verified: `ROSTER` holds nine entries (`The Undertaker`, `The Internal Revenue Service`,
`Zalama`, `Molecule Man`, `Rune King Thor`, `The Sentry`, `The Black Winter`, `Getter Emperor`,
`Mister Mxyzptlk` — counted both by reading and `len(H.ROSTER)`), not four. FIXED: "these four"
to "these nine" in The Sentry's `why_missed` string. The SECOND half of the same order's
evidence — that the module docstring (`:9-41`) documents only two of the nine (Getter Emperor,
Mister Mxyzptlk) — is real but is not the same defect: the docstring never asserts a count, it
picks two case studies as illustrations, and the other seven each already carry an equivalent
explanatory comment directly above their `ROSTER` entry (e.g. Zalama's five-line comment at
`:162-168`), which is where the module's stated goal ("recording the defect beside the assay")
is actually satisfied. Writing full docstring sections for the remaining seven would be new
prose authorship, not a bug fix, so left as-is and reported rather than expanded.

## b5e63bb91ca2 — assay.py, "three functions are dead code" — DISPROVEN
The cited report (`handoff/sweep33/AUDIT_batch13.md`, finding 4) says
`band_for_quantity()`, `interval_from_hands()`, and `null_instrument()` are "exported but never
called anywhere in `src/`". Grepped `src/verify_math.py` directly: all three are called
extensively — `A.band_for_quantity(...)` (5 call sites), `A.interval_from_hands(...)` (4 call
sites), `A.null_instrument()` (2 call sites) — in section 34, the same 63 checks this shift's
own briefing describes adding to close the 24-corruption gap. The audit predates that addition;
it was accurate when written and is stale now. DISPROVEN as currently true: not dead code, not
touched. These three are also on this shift's explicit do-not-change-signature list, so even if
they had been dead they would not have been deleted.

## d5b264f8a196 — assay.py `_check_scores`, off-scale message truncates past 6
Verified: `"; ".join(sorted(bad)[:6])` in the off-scale branch. Reproduced with 8 simultaneously
off-scale axes — the pre-fix message named only 6, silently dropping the ANCHOR the operator most
needs to fix a pasted-percentage-column error (the exact case this check was written for, per
its own docstring). FIXED: dropped the `[:6]` slice, so every offending axis is listed, ranked
alphabetically but not truncated (Hard Rule 0). While in the same function I also found and fixed
the IDENTICAL shape one block down, in the unknown-axis branch (`sorted(unknown)[:6]`) — not
separately ordered, but the same rule, the same function, and a one-line fix; verified with 7
simultaneous unknown axes that all 7 now appear.

## c70075814337 — physics.py, `kinetic()`/`joules_for()` missing sign checks
Verified: `kinetic()` applies `abs()` to speed but not to mass, so `kinetic(-5, 10)` returned a
negative energy silently; `joules_for()` has no check on `volume_m3` at all, so
`joules_for(-10, 'rock', 'pulv')` did the same. Both neighbours in the same file
(`sphere_volume`, `binding_energy`) already refuse a non-positive input with the same worded
rationale ("a wrong number wearing the shape of a right one"). FIXED: added the same
non-positive-refuses-with-ValueError guard to both, matching the existing message style. Checked
every existing caller in `src/` (`verify_math.py`, `anchors.py`) — all pass positive
mass/volume, so no regression. Sibling order `adffa670486c` (binding_energy's mass specifically)
was not in this batch and was not touched.
