# Sweep 41 — Batch 14 audit

Auditor: sweep41-batch14. Read in full, in order: `src/hostcheck.py` (1407 lines),
`src/escalation.py` (997 lines), `src/scout.py` (742 lines), `src/endpoint.py` (564 lines),
`src/sevenfold.py` (422 lines), `src/snapshot.py` (363 lines), `src/wh40k.py` (303 lines),
`src/propagation.py` (236 lines). 5,034 lines read (task line-count estimate was 5,026; both
figures agree to within rounding — confirmed via `wc -l`). No file in `src/` was edited; this is
audit-only, per instructions.

No `escalation.clear()` caller was added or proposed. No refusal was weakened. No change to who
may lift a halt was proposed.

## Method

Read every module end to end, cross-checked candidate findings against the current source (not
against memory of the docstrings, which in this codebase narrate *past* defects at length and
can be mistaken for present ones), then cross-checked every surviving candidate against
`state/workorders.json` before filing, to avoid re-filing what a prior sweep (chiefly run39's
batch 10, which covered these same eight files) already has open. This batch's files carry an
unusually dense prior-audit history — dozens of open orders already reference lines in exactly
these modules — so most of what a fresh read turns up is corroboration of existing open orders,
not new ground.

## escalation.py — the safety-critical read

Read line by line against the five-rung chain doctrine in CLAUDE.md. Specifically checked:

- **Enforcement wiring for MANAGER.** `escalate(MANAGER, ...)` alone records but does not stop
  anything; only `stop_subsystem()` (which calls `escalate(MANAGER, ...)` and then durably writes
  `state/STOPPED.json`) actually closes a subsystem. Grepped all of `src/` for any OTHER direct
  caller of `escalate(MANAGER, ...)` that might bypass the durable write — none exists. The
  "MANAGER stop was a note in a file nobody opened" gap this file's docstring describes as
  historical does not currently have a live analogue of that shape.
- **Fail-open surfaces.** `status()`, `_read_halt_raw()`, `_read_stopped()`,
  `subsystem_stopped()` — all fail CLOSED on an unreadable/wrong-shape file, verified by reading
  every return path, not just the happy one.
- **`_raise_halt`'s CAS race.** Confirmed this is exactly order `97cc0dc43ca7` (open, MAJOR,
  OWNER) — `replace_if_unchanged`'s digest-check-then-rename is not itself atomic, so two
  concurrent *first* halts can still both report `halt_landed: True` with only one fault in the
  file, at a measured residual rate (1/25 for two contenders, 7/25 for four, down from 25/25 and
  75/25 faults before the CAS was added). This is a genuine, still-open gap in the halt path
  exactly of the kind the mutation harness would struggle to reach (it needs a real race, not a
  single-threaded mutation). Already filed with the measurement and the proposed real fix
  (O_CREAT|O_EXCL lock with a fail-open budget) written into the order; not re-filed.
- **`class Refused` never raised anywhere in `src/`.** Confirmed by grep — matches the already-open
  `da15f582b2ea` (MINOR, OWNER) exactly, surfaced by `liveness.py`'s dead-class pass. Not re-filed.
- **`resume_subsystem`'s ruling bar (20 chars) has no `_by_a_person_at_the_cli()`-style gate**,
  unlike `clear()`. Confirmed by reading the function body — no such check exists, and
  `drill.py` calls it programmatically from three sites today. Matches open order `ddb5eadd8934`
  (MINOR, SESSION, correctly framed as a policy question rather than a bug). Not re-filed.
- **New code this shift** — `resume_subsystem_verdict()` and the fix so an unrecordable MANAGER
  stop closes its own false work order (the `_still_stopped` re-check before `resolve_code`) —
  read closely for the asymmetric-failure shape this file cares about. Both are correct: the
  re-check fails closed (an unreadable ledger leaves the order standing), and nothing here lifts
  a halt or resumes a subsystem without a write that actually landed.

No new escalation.py finding. The one MAJOR item outstanding (the halt-file race) is already
filed, already measured, and already carries the real fix as an OWNER decision — re-filing it
would not add information.

## hostcheck.py

Read in full including `purge()`, `roster_audit()`, `adopt()`, `null_rate()`, `score()`,
`candidates_split()`. The purge-shortlist `judgeable` split mentioned as fixed today was
confirmed present and correct (`actionable`/`unjudgeable` split at the `--purge` no-`--source`
path). Confirmed `roster_audit()`'s own per-source print (~line 1258) prints the source name
whole, per its own "HARD RULE 0" comment.

**Found and filed (523015e0fd21, MINOR, LOCAL):** the identical truncation `roster_audit()` was
fixed for was never carried to its two siblings in the same file. `sweep()`'s per-host report
line (hostcheck.py:775) still does `r['source'][:34]`, and `adopt()`'s per-source report lines
(hostcheck.py:1337, :1340) still do `src[:40]` — both silent, unmarked mid-name cuts on the exact
column an operator uses to tell two sources apart in the `--repair` and `--adopt` reports, which
is where a repointing or a new adoption is actually read and acted on. Verified against current
source, not memory. Not previously filed (checked `state/workorders.json` for the line numbers
and for `source'][:34]`/`src[:40]` — no match).

Everything else already open and re-verified rather than re-filed: `5e7a55b690a4` (INFO — the
`best[0] > LIFT_MIN` gate in `sweep(--repair)` is genuinely dead code, confirmed by tracing that
`ok` already implies `lift > LIFT_MIN` via `score()`'s own verdict branches — correctly filed at
INFO since the code's own comment already says as much), `79da6c08c536` (INFO/OWNER, a real
two-reading question about whether `HOST_UNFIT.json` should gate on the host-map write landing),
`c107711349f0` (INFO), `a5fd110e3910` (INFO, `null_rate`'s control has no MIN_PROBE-style floor),
`ae5276abc7f8` (INFO), `4c1f531236ad` (INFO, dead `GOOD` constant).

## scout.py

Read in full. The `registered` tri-state (`None`/`True`/`False`) mentioned as done today is
correctly threaded end to end: `sweep()`'s FOUND/UNSAVED/none branches all test `is True`/
`is False` rather than truthiness, and the `never_asked` unstamp logic correctly distinguishes
"reached is False" (transport outage, rotation slot returned) from a genuine negative result.
`verify()`'s `unverifiable` case (a source with zero probeable names >3 chars) is honestly
reported as unverifiable rather than as a false negative, and its known limitation — such a URL
can never be marked `ok` — is stated in the docstring rather than silently left as a mystery;
this is a real design limit, not a bug, since there is no way to verify a URL against zero names.
Zero open work orders currently reference this file by name (checked); nothing new found.

## endpoint.py

Read in full, including the CAS merge logic in `_save()`, `register()`'s raise-on-unreadable
contract, and the MODE_HTML guard-at-end-of-file ordering fix. `MODE_HTML` being unreferenced by
`detect()` matches the already-open `570525d35825` (MINOR, OWNER) — this is a named-but-unused
mode constant by design (selected via the `pages:` host prefix, not via `detect()`), already
correctly framed as an owner question rather than dead code. Not re-filed.

## sevenfold.py

Read in full, including the two-round balance fix (`seams()`'s window-plus-median-eligibility
construction) and its extensive measured-before/after commentary. The unmarked name truncations
in `main()`'s report (`a[:24]`, `b[:24]`, `s[:34]`, `d[:42]`) match already-open `1e9a348ea2ca`
(MINOR, LOCAL). Not re-filed. No other issue found; this module writes no shared state file
outside its own `--write` output, which is correctly gated on `write_json`'s verdict.

## snapshot.py

Read in full. The restore-returns-fewer-files-than-promised fix mentioned as done today is
present and correct: `restore()` now collects `missing` and raises `SnapshotFailed` naming every
manifest entry it could not copy back, rather than silently returning a smaller count. Also
checked the containment guards (`_rel()`, `_safe_join()`) that stop a snapshot or restore from
writing outside the repository tree or outside the restore target — both correctly refuse rather
than silently re-rooting. Zero open work orders currently reference this file; none found.

## wh40k.py

Read in full, including the ROSTER content and `compute()`'s per-axis provenance tagging. The
`unattributed` default (rather than defaulting to `wiki`) is the correct fail-closed reading:
asserting only what is on record. Confirmed all five entries carry the same 11 axes matching
`A.WEIGHTS`. Two already-open questions for OWNER (`82fc93f056d4` — the axis citations are all
unattributed pending a curatorial pass; `901e441aae1d` — `--full` is the one view that would show
a curator the gap) both re-verified as still accurate against current source. Not re-filed.

## propagation.py

Read in full, including `observed_mark()`'s two-clock model (vertical ascension independent of
lateral distance) and the `lag < 0` guard that is the sole source of an honest `[^0]`. Traced the
descending-rung loop and confirmed it is monotonically correct (returns the highest rung whose
ascension cost the lag clears). The two already-open findings — `67a45b2dcaf8` (stale-comment
risk around the "unreachable" trailing return) and `e8f59f0800fd` (mid-word truncation of shelf
names at `[:19]` in `main()`'s primary probe output) and `d773ad5756ab` (`main()` called bare, not
through `sys.exit`) — all re-verified as still accurate against current source. Not re-filed.

## Summary

| module | lines | new findings filed |
|---|---|---|
| hostcheck.py | 1407 | 1 (MINOR) |
| escalation.py | 997 | 0 |
| scout.py | 742 | 0 |
| endpoint.py | 564 | 0 |
| sevenfold.py | 422 | 0 |
| snapshot.py | 363 | 0 |
| wh40k.py | 303 | 0 |
| propagation.py | 236 | 0 |
| **total** | **5034** | **1** |

Nothing filed at MAJOR/BLOCKING; nothing safety-critical in `escalation.py` was found beyond the
already-open, already-measured, already-actioned-on-paper CAS race (`97cc0dc43ca7`). This batch's
eight files were already heavily audited by prior sweeps; this pass corroborates rather than
substantially extends the open queue.
