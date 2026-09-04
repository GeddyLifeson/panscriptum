# Sweep 43, Batch 14 — Audit

Files read in full: `src/hostcheck.py`, `src/escalation.py`, `src/scout.py`,
`src/manifest_builder.py`, `src/anchors.py`, `src/genre.py`, `src/style_audit.py`,
`src/descending_ladder.py`.

This is a read-only audit. No `escalation.raise_*`/`clear()` was called; no writes were made.
Everything below was checked against the source, and several candidates were traced and
discarded as either already-fixed (this codebase has an unusually deep prior-fix history in
every one of these files) or as defensible design rather than a defect.

---

## escalation.py

### [MAJOR] `clear()` writes the halt file without compare-and-swap, unlike every other writer of it
`src/escalation.py:900`

```python
landed = silence.write_json(HALT_FILE, rec, indent=1, ensure_ascii=False)
```

`_raise_halt` / `_land_halt` (lines 304-433) and `_write_stopped` (line 654) both go through
`silence.replace_if_unchanged(tmp, target, expected_digest)` — a genuine compare-and-swap — and
each carries a long comment explaining exactly why: multiple standing jobs ("the drill, the
keeper, the foreman and nine standing jobs") can all reach `escalate(OWNER, ...)` at once, and a
blind whole-file write loses whichever fault landed second. `clear()` reads the halt record via
`status()`, mutates the in-memory copy, and writes it back with `silence.write_json`, which
(confirmed by reading `silence.write_json`'s own docstring at `src/silence.py:649`) is atomic
against a torn read but has no notion of "did the file change since I read it" — exactly the
"blind to another writer's read-modify-write racing this one" primitive `scout.py:_land`'s
docstring names by name and warns against for shared, contended files.

What actually happens: if an automated process calls `escalate(OWNER, "NEW_FAULT", ...)` between
a person's `status()` read inside `clear()` and `clear()`'s write, `_raise_halt` lands its fault
as a corroborating `also` entry on the currently-standing halt (a real, landed write). `clear()`
then unconditionally overwrites the whole file with the pre-race copy plus `cleared: True` —
silently erasing that `also` entry from the halt file — and the library is reported CLEAR even
though a brand-new OWNER-level fault was raised during the clear and never made it into the
record that `assert_clear()` reads. The fault does survive in `state/escalation.log` (the
JANITOR rung, via `_append_log`, which ran inside `escalate()` before this race), so the story
is not entirely lost — but the halt file itself, which every process actually gates on via
`assert_clear()`/`status()`, would say "running" while a genuine unaddressed OWNER fault exists.

This is precisely the failure this module's own doctrine names: "a second fault while halted is
appended as corroboration rather than replacing the first — the FIRST thing that went wrong is
the one a person needs to see, and a later, louder symptom must not bury it." `clear()`'s write
can bury a fault that arrives concurrently, including one that arrived *after* the fault the
person is clearing.

Likelihood: narrow window (a `--clear` invocation racing an `escalate(OWNER, ...)` call from
another process), but the project's own operating pattern — multiple standing jobs, a keeper,
a drill, all capable of reaching `escalate(OWNER, ...)` — makes this a real rather than
theoretical race, and it is exactly the class of race every other write to this same file was
independently hardened against.

**Remedy** (RUN, not a mechanical edit): give `clear()` the same CAS treatment as `_land_halt` —
digest `HALT_FILE` before `status()`'s read, write through `silence.replace_if_unchanged`, and on
a digest mismatch re-read and retry rather than clearing on stale data (a retry here should re-run
the whole `status()`/mutate/write cycle against the fresh record, since a fault landing mid-clear
means there is now something new to report to the person clearing, not just a race to re-win).

### [MINOR] `_FIELDS[OWNER]` omits `"level_name"`, unlike every other rung
`src/escalation.py:97-104`

```python
_FIELDS = {
    JANITOR:    ("at", "level_name", "code", "what", "source", "who", "evidence", "halt_landed"),
    OPERATOR:   ("at", "level_name", "code", "what", "source", "who"),
    SUPERVISOR: ("at", "level_name", "code", "what", "source"),
    SAFETY:     ("at", "level_name", "code", "what", "source"),
    MANAGER:    ("at", "level_name", "code", "what", "source", "who"),
    OWNER:      ("at", "code", "what", "source", "evidence", "who", "halt_landed"),
}
```

Every other rung's whitelist carries `"level_name"`; OWNER's does not. Verified directly:

```
_FIELDS[OWNER]:      ('at', 'code', 'what', 'source', 'evidence', 'who', 'halt_landed')
_FIELDS[SUPERVISOR]: ('at', 'level_name', 'code', 'what', 'source')
```

This is read by `_append_log`'s per-source log write: `_append(os.path.join(SRC_LOGS,
_safe_name(src) + ".log"), brief(rec, rec.get("level", JANITOR)))`. For an OWNER-level
escalation, the per-source log entry in `state/escalations/<source>.log` therefore carries no
`level_name` field, while the identical entry for a SUPERVISOR- or SAFETY-level fault about the
same source does. The full picture survives in `state/escalation.log` (always briefed at
JANITOR, which does carry `level_name`), so this is not a fail-open finding — it is a real,
verified inconsistency in what a person reading one source's own escalation history sees for its
most serious entries. `code` alone (e.g. `HALT_NOT_RAISED`, a hand-written `--raise-halt` code)
does not reliably read as "this was OWNER" the way `level_name: "OWNER"` does for every other
rung's entries in the same file.

**Remedy** (LOCAL): add `"level_name"` to the OWNER tuple in `_FIELDS`.

### [INFO] `escalate()`'s level normalisation silently truncates a float level instead of routing it through the fail-closed path
`src/escalation.py:222-234`

```python
_bad_level = None
if isinstance(level, str):
    ...
try:
    level = int(level)
except (TypeError, ValueError):
    _bad_level, level = repr(level), MANAGER
if not (JANITOR <= level <= OWNER):
    _bad_level, level = level, MANAGER
```

The whole point of this block, per its own comment, is that "AN UNRECOGNISABLE LEVEL LANDS AT
MANAGER, NOT OWNER" — a deliberate fail-closed-but-not-over-eager design for a bad rung name or
value. `int()` on a non-integer float does not raise — `int(2.7) == 2` (confirmed directly) — so
`escalate(2.7, ...)` silently becomes `escalate(OPERATOR, ...)` rather than being caught as an
unrecognised level and routed to MANAGER with `evidence["unrecognised_level"]` set, as every
other malformed input (bad string, `None`, out-of-range int) is. No call site in this batch
passes a float level, so this is very unlikely to be live — flagged because it is a genuine gap
in an otherwise carefully-closed contract, not because it is currently exploitable.

**Remedy** (OWNER — a judgment call on how strict the contract should be): decide whether to
reject non-integer numeric levels explicitly (`isinstance(level, float) and not level.is_integer()`)
or to leave it, since no caller currently exercises this path.

---

## hostcheck.py

Read in full, including `sweep`, `score`, `null_rate`, `probe`, `relevance`, `_bodies`,
`candidates`/`candidates_split`, `roster_audit`, `purge`, `adopt`, and every CAS-write helper
(`_land`, `_land_hosts`). This file has an unusually deep prior-fix history (documented inline
by "order" id) and I did not find a live defect in it. Two things were checked and are **not**
findings:

- `PROBE = 40` (names sampled per host for the fitness rate) and the length-3 token-shortlisting
  in `relevance()`/`roster_audit()` look at first glance like Hard Rule 0 caps, but they are
  statistical samples that feed a *rate* (with `n` always carried alongside and floored by
  `MIN_PROBE`/`ABOUT_MIN`), not truncations of an evidence listing — the module is explicit and
  consistent about this distinction elsewhere (`probe()`'s RAW-mode `"titles"` field is the
  uncapped list; only `"examples"` is a capped display slice).
- `GOOD = 0.35` (line 196) is defined but has no live caller in the scoring logic — every
  reference to it outside its own definition is inside a comment describing a bug that was
  already fixed (the raw-rate comparison it used to gate). This matches the module's own
  docstring claim ("`GOOD` is now only the figure quoted in prose here") exactly, so it is
  intentional vestigial documentation, not a contradiction.

## scout.py

Read in full, including `_mutate`'s CAS loop, `verify()`/`_names_in()`'s name-boundary matching,
`scout()`'s verify-then-register-then-adopt sequencing, and `sweep()`'s stamp-before-work /
archive-before-trim rotation. No defect found; the Hard Rule 0 history here (uncapped
verification against every catalogued name, uncapped URL proposals, archived rather than deleted
log roll-off) is consistent and the code matches every claim in its own comments.

## manifest_builder.py

Read in full. `load_record()`'s fuzzy slug-matching (exact match first, then a length-floored,
closeness-ranked prefix/containment fallback) was traced against its own stated failure history
and is internally consistent. `pack_feats()`'s flush-before-append bin-packing and oversized-
entity pagination were traced by hand against the docstring's own worked numbers and do not drop
or clip any feat. The `numbering_pool` vs `build_pool` split (spine/volume numbers computed over
the full roll before `--only`/`--pilot` narrows what gets built) was checked and `build_pool` is
always a subset of `numbering_pool`, so the `volume_code[r["name"]]` lookup in `main()` cannot
KeyError. No defect found.

## anchors.py

Read in full, including the CLAIMS table, the monotone-ladder invariant, and the
`refused`/`ungraded`/`unanchored` guard rails around it. Traced `opener_shape`-equivalent logic
is not present here, but the CLAIMS lambdas were hand-checked against each anchor's actual scores
dict (Skate Guy has exactly 11 axis keys and no `INAPPLICABLE` strike; Sword strikes exactly
`["volition"]`; Goku's `volition` is numeric; Yggdrasil's is `A.UNESTIMABLE`). All hold. No
defect found.

## genre.py

Read in full. Confirmed directly (small interpreter check) that `classify_text`'s `Counter`
accumulation inserts a key for every one of the 11 genres even when a genre's score is 0 — so
`classify_source`'s claim that its confidence denominator is "the whole field" is actually true
at runtime, not just in the docstring. `cap` is correctly refused with a loud `SystemExit` rather
than silently truncating. No defect found.

## style_audit.py

### [MINOR] `--self-test` never asserts on `turn_endings`/`turn_rate`/`em_per_entry`, despite the fixture apparently being built to exercise both
`src/style_audit.py:234-296`

The GAMMA fixture is deliberately constructed with an em-dash (`"— and it is a warning"`) and a
sentence built to trip `TURN_ENDING` (`"...to the age. And so it remains."`). `TURN_ENDING`'s own
docstring (lines 37-57) documents a serious historical bug in this exact detector: it used to
match on every paragraph break under `re.M`, inflating the measured turn-ending rate from a true
0.2% to a reported 4.3% — "over-reporting one is a fabricated pass mark", in the module's own
words. Despite that history and despite the fixture appearing purpose-built to cover it, the
`checks` list in `--self-test` (lines 279-289) asserts only on `entries`, `shapes`, and `banned`
tells — never on `a["turn_endings"]`, `a["turn_rate"]`, or `a["em_per_entry"]`. A regression in
`TURN_ENDING` (the exact class of regression this file has already shipped once) would pass
`--self-test` silently. This is the same lesson the file's own comment states about the shape
detector's self-test ("a check whose result is printed and discarded cannot fail" / "a check
that cannot fail looks exactly like a check that passed") applied to a *different* detector in
the same file that the self-test simply never reaches.

**Remedy** (LOCAL): add assertions to the `checks` list, e.g.
`("GAMMA's em-dash and turn ending are counted", a["em_per_entry"] > 0 and a["turn_endings"] == 1)`
and a negative-control assertion that the `good` fixture trips neither (`b["turn_endings"] == 0`).

## descending_ladder.py

Read in full. `rung_for_length`'s "keep overwriting while `metres <= r[3]` holds" loop was hand-
traced against several boundary values (an object exactly on a rung edge, an object between two
rungs) and correctly finds the *tightest* (smallest-length) rung whose edge is still `>=` the
input, because `DESCENDING` is strictly decreasing in length and the loop's overwrite-until-false
pattern degenerates to exactly that without needing a `break`. Every constant in the `DESCENDING`
table was checked against its own cited physical quantity (e.g. Atomic: 13.6 eV × 1.602e-19 J/eV
≈ 2.2e-18 J, matches the table; Planck: Planck mass × c² ≈ 1.956e9 J, matches `PLANCK_ENERGY`)
and all are internally consistent. No defect found; one edge case is worth noting but not filed:

- `transgression_bits(mass_kg, to_m)` returns `0.0` (via `density_at_scale`'s `None` for
  `size_m <= 0`) if ever called with `to_m <= 0` — i.e. a degenerate "shrunk to a point" input
  reads as *zero* exception cost rather than being flagged as unrepresentable or maximal. Nothing
  in this batch calls this function with such a value, and the ladder's own `FOLD_RUNG` mechanism
  is presumably how a real descent below Planck length is meant to be represented instead, so
  this reads as an untested edge of an internal helper rather than a live defect. Noted for
  whoever next touches this function's callers.

---

## Questions for the OWNER

1. **escalation.py `clear()` race (see MAJOR finding above).** The fix itself (CAS-write the
   halt file in `clear()`) is mechanical once decided, but *whether* a fault landing mid-clear
   should abort the clear outright (forcing the person to re-run `--clear` and see the new fault
   first) or should merely be preserved as an `also` entry on the now-cleared-and-reopened record
   is a design call this audit should not make silently.
2. **escalate() float-level strictness (see INFO finding above).** Is tightening this contract
   worth doing given no live caller exercises it, or is it acceptable as documented dead-path
   slack?

Everything else in this batch was traced to a specific line, evaluated against what the code
actually does at runtime (including two direct interpreter checks), and either filed above or
discarded as already-correct.
