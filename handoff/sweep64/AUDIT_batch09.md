# sweep64 batch09 audit

Auditor for batch 9 of sweep64. Read-only throughout: nothing under `src/`, `data/`, `state/` or
`output/` was edited, created or deleted except this report and the mandated coverage call. No
drill, verify_math, generate, pipeline, publish, mutate, foreman, manifest_builder or any job was
run. No subagents were spawned.

## Scope (read in full, start to finish, via the Read tool, no grep-sampling)

- `src/foreman.py`          2279 lines
- `src/codewatch.py`        1180 lines
- `src/derivation.py`        816 lines
- `src/manifest_builder.py`  671 lines
- `src/zfighters.py`         536 lines
- `src/hosts.py`             424 lines
- `src/profile.py`           354 lines
- `src/ledger.py`            220 lines
- `src/chord_field.py`       210 lines

Total 6,690 lines, all nine read completely.

## Method

Read `CLAUDE.md` first (Hard Rule -1 escalation/halt, Hard Rule 0 no caps, fail-closed doctrine,
"a check that cannot fail looks exactly like a check that passed"). Then grepped `handoff/sweep63/`
for each of the nine module names and read every prior audit that named one before reading any
source: `AUDIT_batch09.md` (foreman, codewatch, derivation, zfighters, hosts, among others — the
closest predecessor to this exact roster), `AUDIT_batch07.md` (ledger.py, chord_field.py),
`AUDIT_batch10.md` (profile.py), and `AUDIT_batch01.md`/`AUDIT_batch06.md`/`AUDIT_batch12.md`
(manifest_builder.py). This is, again, a heavily pre-audited batch — nearly every non-obvious line
carries a comment citing the specific prior order that found and fixed the shape being looked for.
Findings already named and fixed in the code's own comments are not re-reported here.

Per the brief's specific context, I traced whether anything retires `foreman.kill_stalled_job`'s
SUPERVISOR escalation for a stalled-but-unrestartable job once the stall ends or the named pid
dies. This required reading past this batch's own files into `escalation.py` and `workorders.py`
(read-only, for context only — not part of this batch's coverage or report roster) to establish
whether a generic retirement mechanism exists.

## Findings

### VERIFIED

**1. `src/foreman.py`, `kill_stalled_job()`, lines 800–813 — the STALLED_UNRESTARTABLE escalation
is filed once and never retired, by anything, under any condition.**

```python
    if unrestartable:
        # A stalled job nothing would restart is escalated, not silently left. SUPERVISOR rung:
        # it is one job's problem, not the library's, and it must not halt the park.
        spared = ("; SPARED (stalled but nothing restarts them, so killing costs more than the "
                  "stall): " + ", ".join(unrestartable))
        try:
            import escalation as _ESC
            _ESC.escalate(_ESC.SUPERVISOR, "STALLED_UNRESTARTABLE",
                          "stalled and deliberately NOT killed, because nothing would bring them "
                          "back promptly: " + ", ".join(unrestartable),
                          evidence={"jobs": unrestartable}, who="foreman.kill_stalled_job")
        except Exception:
            silence.note("foreman.py:kill_stalled-escalate")
```

`escalation.escalate()` (escalation.py:223 on) turns every escalation into a work order via
`WO.file_order(rec["code"], rec["what"], handler, severity, where=rec.get("source") or "", ...)`
(escalation.py:338). This call site never passes `source=`, so `where=""`, and `file_order`'s own
docstring states the order is keyed on `(code, where)` — meaning every future
`STALLED_UNRESTARTABLE` filing from any job refreshes the *same* order (`workorders.py:515–650`),
overwriting its `evidence` (the `job:pid` list) each time but only when `kill_stalled_job` finds a
non-empty `unrestartable` list on some later round.

Grepped every `resolve_code(` call site in `src/` (`drill.py:609,3178,4495`; `escalation.py:771,
1065`; `workorders.py:1293,1418,1436,1663,1715,1768`). None resolves `STALLED_UNRESTARTABLE`. The
only generic self-resolving mechanism is `workorders.sweep_detectors()`'s `_fire`/`_detector`
pattern (`workorders.py:1380–2120`), which owns a fixed, enumerated set of codes (LEDGER_STRUCTURE,
LEDGER_CHAIN, MAINTENANCE_GUARD_DISAGREES_WITH_THE_PROCESS_TABLE, LIVENESS_RATCHET,
BINDING_HEALTH_STALE, SECRET_STAGED, battery codes, STALE_CITATION, etc. — grepped explicitly,
`STALLED_UNRESTARTABLE` is not among them) — each of those detectors re-runs every sweep and closes
its own order the moment its condition clears. `STALLED_UNRESTARTABLE` is filed directly by
`foreman.py` through `escalation.escalate()`, outside that detector pattern, with no counterpart
that ever calls `resolve_code("STALLED_UNRESTARTABLE", ...)`.

**Concrete failure scenario, matching the one described in the brief:** `kill_stalled_job` finds
job X stalled and unrestartable at round N, pid 1234; it escalates SUPERVISOR/STALLED_UNRESTARTABLE
naming `"X:1234"`, filing (or refreshing) one open work order. At round N+1 the stall has ended (or
the process holding pid 1234 has since died and restarted under a new pid) — `unrestartable` comes
back empty, so the `if unrestartable:` block does not execute at all, and nothing calls
`resolve_code` for that code. The work order stays open, forever, still naming `X:1234`, and a pid
that "no longer existed a day later" is exactly what a person would find reading the open-orders
queue. Nothing in `foreman.py`, `escalation.py`, or `workorders.py` closes it — the only way it
closes is a person running `workorders.py --resolve` (or the equivalent CLI) by hand.

This is a real gap, not a design choice with a stated reason (unlike the deliberate omissions this
codebase usually documents): no comment anywhere claims the order is meant to self-clear, and none
of the `WHAT WOULD MOVE IT OUT OF HELD`-style "this is deliberate" commentary this codebase uses
elsewhere appears at this call site.

**2. `src/manifest_builder.py` — the unassigned-sources report can print a provisional spine code
that does not match the code the volume was actually built under, whenever two or more unassigned
sources share a `category`.**

`provisional_spine()` (line 254–257) is a pure function of `roll_entry["category"]` alone:

```python
def provisional_spine(roll_entry):
    """Only used with --include-unassigned. Clearly marked PROVISIONAL, never silently real."""
    cat = slugify(roll_entry.get("category", "Uncategorized"))
    return f"UNSORTED.{cat}.PROVISIONAL"
```

`main()`'s numbering pass (lines 533–546) is aware this collides and disambiguates it correctly for
the actual build: every source lands in `series_members[code]` keyed on this same base code, and
when more than one source shares a code (unavoidable whenever two unassigned sources share a
category — `provisional_spine` has no other input), `volume_code[name]` gets `f"{code}.{i}"` for
`i` in sorted order. `volume_code[r["name"]]` — the disambiguated value — is what
`build_jobs_for_source` actually receives and what the real job addresses in the manifest carry
(line 566).

But the `unassigned_sources.md` report, written a hundred lines later, does not read
`volume_code[r["name"]]`. It recomputes the bare, undisambiguated code directly:

```python
    for r in sorted(unassigned, key=lambda r: r["category"]):
        f.write(f"- **{r['name']}** ({r['category']}, {r.get('entry_count', 0)} entries)"
                + (f" -- built as `{provisional_spine(r)}`\n"          # <-- line 648
                   if args.include_unassigned else "\n"))
```

**Failure scenario:** run `manifest_builder.py --include-unassigned` when two populated,
spine-code-less sources share the same `category` (e.g. two unassigned "Video Games" entries).
Both are actually built under distinct codes (`UNSORTED.Video-Games.PROVISIONAL.1` and `.2`), but
the report lists both rows as `-- built as \`UNSORTED.Video-Games.PROVISIONAL\`` — identical
strings, with no `.1`/`.2` suffix on either, and no way for the reader to tell which report row
corresponds to which actually-generated volume. This directly contradicts the surrounding comment's
own claim (line ~611–614): "the provisional code each one received is printed too, since that is
the string that has to be replaced in the charter" — the string printed is not the string the
volume received whenever the category collision applies.

**Currently inert:** I checked the live roll (`data/SWEEP_ROLL.json` via `address.spine_code_for`)
and there are 0 populated, unassigned sources on it today (the "day the last source got a spine
code" this file's own header-selection logic already anticipates has apparently already arrived),
so no category collision exists to trigger this right now. The bug is real and traced against the
source, not reproducible against today's data — reported per the brief's instruction to verify
against source and give a concrete scenario, which I did; it would resurface the moment a source is
added to the roll with no spine code, sharing a category with another such source, and
`--include-unassigned` is used.

## QUESTIONS

None met the bar for reporting as a design/policy question distinct from the two findings above.
`prose_enabled`/`step4_enabled` were not touched or examined for opening (out of scope per the
brief) and nothing else in these nine modules presented an ambiguous design choice worth a ruling.

## Candidates traced and ruled out (not filed, not re-filed)

- `foreman.py`'s `_restartable`/`_restart_horizon` STANDING-derivation, `round_once`'s
  `always`-remedy handling, `_catalogue_batch`'s rotation, `_python_processes`'s psutil-only
  listing (no wmic anywhere live), `attempt_patch`'s patch-safety gates (`regex_touched`,
  `lines_changed`, `_contracts_pass`, `_checks_pass`'s verify_math result-line regex) — all
  re-verified against the comments describing their own prior fixes; all match, no drift found.
- `codewatch.py`'s `runs_script`/`twins`/`claim_singleton` FAIL OPEN behaviour on an unreadable
  cwd or process table — explicitly documented as intentional in three separate docstrings
  ("FAIL OPEN", "an outage that reports itself as caution is the worst shape a safety can take"),
  not a hidden defect.
- `codewatch.py`'s `CODEWATCH_NEVER_SETTLES`/`CODEWATCH_STALE_THROUGH_SHIFT`/`CODEWATCH_BUDGET`/
  `CODEWATCH_NOT_STAMPED`/`DAEMON_TWIN` escalations share the same "no `resolve_code` counterpart
  exists" property as the foreman finding above, but I did not file them as separate findings:
  the brief's specific incident and question was about `kill_stalled_job`'s
  `STALLED_UNRESTARTABLE` order by name, and these are a broader, systemic pattern (any
  `escalation.escalate()` call not routed through `workorders.sweep_detectors()`'s self-resolving
  `_fire`/`_detector` idiom has this property) that spans files well outside this batch's roster
  and is better raised once, generally, than four more times here.
- `derivation.py`'s cycle-detection early-return (order 90516d53d696) and `manifest_builder.py`'s
  `pack_feats` pagination/flush-before-exceeding arithmetic — re-verified by hand, both match
  their own comments exactly.
- `hosts.py`'s `work()` returning a 3-tuple on every path (making the `if not res: continue` guard
  in `discover()` unreachable by construction, per its own comment) and `zfighters.py`'s
  Son-Goku-fallback / `--full` worksheet wrapping — both re-verified present and correct.
- `profile.py`'s `encode()`/`decode()` round trip, including the attested-axes refusal
  (bool-excluded, range 0–4) and the per-axis feature-digit range check in `decode` — traced by
  hand, matches.
- `ledger.py`/`chord_field.py` — both self-consistent, no live callers outside `verify_math.py`'s
  battery (by ruling, `ledger.py`'s own "HELD FOR A FUTURE PHASE" doctrine, order 3fb9fc6b9999),
  no arithmetic errors found (`assay_to_standards`'s M10 top-band handling checked against the
  `hi == lo` bug class it cites and does not reproduce).

## Coverage

Recorded via `sweep_plan.record('run64', [...], batch=9)` for all nine modules listed above, each
read in full this session (none substituted or skipped).
