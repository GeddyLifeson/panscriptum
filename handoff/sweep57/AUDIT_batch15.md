# AUDIT — run57, batch 15

Modules read in full, top to bottom (line counts confirmed against `wc -l`):
`src/local_agent.py` (1639), `src/escalation.py` (1445), `src/generate.py` (977),
`src/policy.py` (582), `src/autostart.py` (564), `src/retry_synthesis.py` (379),
`src/suppressions.py` (353), `src/entity_match.py` (310).

AUDIT ONLY. No file was edited. `escalation.py`'s `clear()`, `escalate()`, `stop_subsystem()` and
`resume_subsystem()` were not called — reading only. `drill.py`, `verify_math.py` were not run.
No subagent was spawned. `prose_enabled`/`step4_enabled` were not touched.

Prior work checked first: `handoff/sweep56/AUDIT_batch05.md` (autostart.py, entity_match.py),
`AUDIT_batch06.md` (policy.py), `AUDIT_batch12.md` (retry_synthesis.py, suppressions.py),
`AUDIT_batch15.md` (local_agent.py, escalation.py, generate.py — same set of three this batch
still owns), plus the open queue (`workorders.open_orders()`).

---

## escalation.py

Read in full, including the three-property trace (INDEPENDENT / FAIL CLOSED / PROVEN) already
laid out by sweep56-batch15, re-verified line-by-line against the CURRENT text (unchanged
1445-line file):

- FAIL CLOSED: `_read_halt_raw()` (L603-633) returns the `_unreadable_halt()` stand-in for
  anything that isn't a parseable dict, `_read_stopped()` (L782-807) does the identical thing for
  `STOPPED.json`, and `_halt_lock()` (L389-450) is the one *documented* exception (fails OPEN by
  owner ruling 2026-09-08, on purpose, so a stuck lock file can never block a halt from landing).
- INDEPENDENT: the OWNER halt (`_raise_halt`/`_land_halt`) and the MANAGER stop
  (`stop_subsystem`/`_write_stopped`) are separately compare-and-swapped, separate files, and
  neither's CAS loop shares a code path with `clear()`/`resume_subsystem_verdict()`.
  `refuse_unit`/`refuse_source` (L1081-1119, rungs 1/2) confirmed still to have **zero callers**
  anywhere in `src/` outside `escalation.py` itself (`grep -rn "refuse_unit\|refuse_source" src/`
  hits only the pyc cache) — this is the documented, deliberate "REPORTED DEAD, NOT DELETED"
  state under owner ruling 2026-09-08 q1, not a fresh finding.
- PROVEN: `_by_a_person_at_the_cli()` (L1141-1169) still gates both `clear()` and
  `resume_subsystem_verdict()` on `sys._getframe(2)` landing in this file's own `main()`; `main()`
  (L1367-1379) calls `resume_subsystem_verdict()` directly rather than through the
  `resume_subsystem()` wrapper, exactly as the docstring requires (a call through the wrapper
  would shift the frame count and defeat the check).

**Checked against the four open mutation-testing survivor orders** (`befe73801f6f` L303,
`17242f0e3f39` L1297, `aa9522fcec35` L1324, `3c85cdc4e5ee` L1379) — all four line numbers still
land on exactly the code the order names (`if not recorded:` corroboration branch;
`_halt_file_cleared()`'s return; `_land_clear`'s except-arm `return False, "raised"`; the
`--resume` CLI dispatch). **KNOWN(befe73801f6f, 17242f0e3f39, aa9522fcec35, 3c85cdc4e5ee)** — live
mutation-testing target, not re-analysed further per the brief.

Verified the `escalate()` → `workorders.file_order()` handler map (L334) against
`workorders.LADDER = ["LOCAL","BOTS","RUN","SESSION","OWNER"]` — every value escalate() can emit
(`LOCAL, BOTS, RUN, SESSION`) is a member. No mismatch.

**Nothing new found in escalation.py.** This file is a live mutation-testing target this shift and
was audited, not touched.

---

## local_agent.py

Read in full, both halves (0-929, 930-1639). The write-gate chain — allowlist (`WRITABLE_PREFIXES`
/`WRITABLE_FILES`, fails closed), denylist (`DENYLIST`, `DENYLIST_PATHS`, `DENYLIST_PREFIXES`),
identity check (`_protected_identities`/`_identity_denied`, the hard-link closer), junction
resolution in `_safe()`, and the four `_gates()` checks (parse, pyflakes, import, whole-suite
`verify_math`) — was traced end to end through `t_propose_patch`. All eight previously-documented
bypass classes (case-fold, name-prefix, ADS, case-sensitive extension, unlisted directory,
junction, DENYLIST_PREFIXES-through-junction, hard link) have their fix present and consistent
with the comment describing it. The blast-radius cap (`_blast_ok`, `MAX_FILES_PER_RUN=8`,
`MAX_PATCHES_PER_RUN=24`) is charged only once a write is about to actually land (L1051-1060),
matching its own comment.

**QUESTION (re-confirmed, sweep56-batch15 Finding 4, unchanged) — `assert_clear()` is checked
once per `run()` invocation, not per turn.** `run()` L1433-1434:
```
import escalation as _ESC
_ESC.assert_clear(who="local_agent.run")
```
is the only call in the file, before the `MAX_TURNS=24` loop begins. A run can span many
`verify_math` subprocess calls (600s timeout each) inside `_gates()`, during which an OWNER halt
raised by an unrelated process would not be noticed until the *next* invocation of `local_agent`.
Sweep56-batch15 judged this consistent with the house convention ("entry-point granularity, not
per-operation" — matches `pipeline.py`, `overnight.py`) rather than a defect, and nothing in the
code has changed since. Not re-raising as new; flagging only because this is the one lane that can
write to `src/`, so the window is the most consequential of the twelve gated modules.

**Nothing else found in local_agent.py.**

---

## generate.py

Read in full. The think-tag stripping boundary (`strip_think`), the two-call retry-then-refuse
block discipline in `generate_job()`, `ChapterRefused`'s full-offender-list carrying, the P8
meta-language gate's fail-closed `ImportError` handling, and the final-write-decides-the-exit-code
discipline in `main()` were all traced and match their own extensive in-source commentary.

**QUESTION (re-confirmed, sweep56-batch15 Finding 1, unchanged, not filed as a work order) —
`generate.py` still carries no `escalation.assert_clear()` interlock.**
`grep -n "escalation\|assert_clear" src/generate.py` → zero hits, same as when sweep56-batch15
raised this. `overnight.py` calls `assert_clear()` once per cycle before dispatching the prose
stage and additionally gates the `start("prose", …)` call on the same-cycle drill result — but
that only covers the path where `overnight.py` is the caller. A hand-run
(`python src/generate.py --manifest …`, which is `generate.py`'s own documented usage in its
module docstring) or any future direct caller reaches a model call and a disk write with no halt
check of its own. The only thing that would stop such a run under a halt is the unrelated
`prose_gate`/`prose_enabled` flag, which is a different safety with its own defeat history in this
tree (`bool()` coercion in `overnight.py`). Still a QUESTION, not a DEFECT: it may be an accepted
gap (dispatch-side mitigation judged "close enough"), and I have no new evidence either way. Not
re-analysed in depth per the brief's instruction to avoid re-deriving known work.

**Nothing else found in generate.py.**

---

## policy.py

Read in full (grew 575→582 lines since sweep56-batch06's read; the growth is in comments, no new
functions). The evaluator's own contract (checked-before-`try` `BadRule` refusal for `is_type` and
the other seven arg-taking ops, so a malformed rule table entry is refused at *load* rather than
silently misjudged) was re-verified. `evaluate()`'s vacuous-pass detector and its single documented
exemption (`absent`) are unchanged and correct.

**QUESTION (re-confirmed, sweep56-batch06, unchanged) — a malformed rule table entry can still
surface as "record unreadable" rather than as its own fault.** `evaluate()` (L196-198) calls
`check_rule()` (which raises `BadRule` for a bad rule) with no try/except of its own; `main()`'s
three sweep loops all wrap the `evaluate()` call in a broad `except Exception` that files the
result under `unreadable`/`ev_unreadable` (record-loop L352-364, coverage-loop L377-383,
evidence-loop L423-435). A `BadRule` raised by a bug in `RECORD_RULES`/`EVIDENCE_RULES`/
`COVERAGE_RULES` themselves would therefore be attributed to the *document* being corrupt, not to
the rule table — the exact confusion `check_rule`'s own comment (L161-165) says it exists to
prevent, reachable one level up from where that comment thinks it stopped it. None of the three
live tables is malformed today, so this is dormant, matching the file's own "landmine for the next
table" framing of the adjacent `TYPES`-default fix. Not a new finding — same as sweep56-batch06.

**DEFECT, KNOWN — stale self-citation, drifted further since sweep56-batch06.** Sweep56-batch06
already flagged `policy.py:423` ("uncut at policy.py:339") and a second citation at `policy.py:497`
("policy.py:~477") as stale, both off because the file had grown. The file has grown *again*
(575→582 lines) and the same two comments — unedited — now sit at different line numbers still
citing the same stale targets:
- Current L431 (docstring inside `_sweep_one`'s except-arm): `"UNCUT (order 491269a0f908). The
  record loop's twin was uncut at policy.py:339 with the note..."` — line 339 today is
  `if not a.run:` inside `main()`'s argument handling, unrelated to any "uncut" fix.
- Current L505 (comment above the evidence `UNREAD` print): `"the record loop's twin was already
  changed to this at policy.py:~477."` — the actual record-loop `UNREAD` print is now at L536.

Both citations describe a real, correct relationship (two sibling "print the whole unreadable
name, don't cut it" fixes exist and match each other); only the line numbers are wrong, and they
will keep drifting every time an unrelated line is added above them.
**KNOWN** — this exact defect is sweep56-batch06's finding, not yet corrected, and falls under the
open general orders `89503c58409f` (LINE_CITATIONS_IN_SRC_COMMENTS_HAVE_ROTTED_AT_SCALE),
`386c0d66e31e` (STALE_LINE_CITATIONS_SWEEP54) and `d7efd67caa6f` (STALE_CITATION).

**Verified as already fixed, not re-reported** — open order `fe99e57e1993`
(UNMARKED_NAME_CUTS_SWEEP44) names `src/policy.py:323,369 str(e)[:70]` as an unmarked cut.
`grep -n "\[:70\]\|str(e)" src/policy.py` today returns **zero hits**: every exception in this
file is now rendered as `"%s: %s" % (type(e).__name__, e)` in full (L356-357, L363, L380-382,
L426-435). Policy.py's share of that combined, multi-file order appears to already be resolved in
current source; flagged here only so whoever eventually closes/narrows that order can cross this
file off. Not itself a new finding.

**Nothing else found in policy.py.**

---

## autostart.py

Read in full, unchanged since sweep56-batch05's clean read (byte-identical 564 lines — that batch
found nothing here, which is consistent with this defect being filed by a *later* sweep).

**DEFECT, KNOWN(06041602990d) — confirmed exact lines.** `watch()`'s crash-recovery branch:
```
elif not alive:                                                       # L453
    starts = [t for t in starts if now - t < START_WINDOW_SECONDS]    # L454
    if len(starts) >= MAX_STARTS_PER_HOUR:                            # L455
        if now - said_budget_at >= START_WINDOW_SECONDS:              # L456
            said_budget_at = now
            _log("supervisor is down and %d start(s) in the last hour did not fix "
                 "it; NOT starting another. This is deeper than a crash and needs "
                 "a person -- respawning past this point is the loop, not the cure."
                 % len(starts))
    else:
        start_supervisor(read_hours)                                  # L463
        starts.append(now)
```
`supervisor_alive()` (L240-268) answers only the tri-state "is `overnight.py` running", via
`overnight.running("overnight.py")`. It never consults `escalation.status()` or
`escalation.subsystem_stopped("overnight")`. `overnight.py` is one of the twelve
`assert_clear()`-gated modules per CLAUDE.md, so under a standing OWNER halt each
`start_supervisor()` call here (L271-301, a plain detached `Popen`) launches a process that raises
`SystemHalted` and exits almost immediately — `supervisor_alive()` reads that as "not running"
again on the very next 180s poll, indistinguishable from a genuine crash. The three restarts this
loop is willing to try (`MAX_STARTS_PER_HOUR=3`) burn inside minutes against a deliberate,
person-facing halt, and once the budget under `START_WINDOW_SECONDS=3600` is exhausted the
watchdog goes quiet ("NOT starting another... needs a person") for up to the remaining hour —
**including the time after an owner lifts the halt**, since nothing here re-checks
`escalation.status()` to notice the halt cleared and reset the budget early. The message printed
("this is deeper than a crash") is also actively misleading in this case: it is not deeper, it is
the chain of command working exactly as designed, misread by the one component that has no view of
it. Exact lines confirmed against current source: L453-466 (the budget/restart branch itself),
L240-268 (`supervisor_alive()`, which has no escalation awareness), L372-476 (`watch()`'s whole
loop, which never imports `escalation`). Confirmed `grep -n "escalation\|assert_clear"
src/autostart.py` → zero hits anywhere in the file.

**Nothing else found in autostart.py** beyond the above (already-filed) defect. The tri-state
`supervisor_alive()`/`ON.running()` handling elsewhere (the `--status` printer, the stale-launcher
detection in `installed_state()`, the `_twin_watchdog()` fail-open-with-retry) all match sweep56-
batch05's clean read and are unchanged.

---

## retry_synthesis.py

Read in full. `save_side()`'s read-merge-write-and-report-the-verdict discipline, `synthesise()`'s
five documented anti-drift fixes against `pipeline`'s own synthesis-phase logic (nomination
method, transport, acceptance gate, evidence validation, evidence truncation), and `do_merge()`'s
uncapped unmerged-source reporting were all traced and match their own commentary.

**QUESTION (new instance of a known class — sweep56-batch15's Finding 2, not previously checked
against this specific module) — `retry_synthesis.py` carries no `escalation.assert_clear()`
interlock either, and it is a corpus-mutating tool exactly like `repass_bands.py`/
`resync_roll.py`.** `grep -n "escalation\|assert_clear" src/retry_synthesis.py` → zero hits.
`--merge` (`do_merge()`, L250-307) writes into `data/records/*.json` through the sanctioned
`PL.write_record()` (so it respects the two-writer contract's merge-on-write discipline — this is
not the M24-shape bypass), but nothing stops it from being invoked, or from running its (separate,
GPU-calling) retry pass, while the library is under an OWNER halt or a MANAGER-level
`stop_subsystem("pipeline", ...)`. The module's own docstring already documents one such external
constraint by convention rather than by code — `do_merge()`'s own docstring: *"Run ONLY when the
pipeline is stopped"* — and the sibling comment at L276-277 notes drily that "nothing enforced it"
for the two-writer-contract bypass this file already fixed once (order relating to `write_record`
merge-on-write). The same "convention, not code" gap now applies one level up, to the chain of
command itself. Sweep56-batch15 treated the identical shape in `repass_bands.py`/`resync_roll.py`
as a QUESTION rather than a DEFECT, reasoning that an occasional hand-run repair tool may
reasonably expect its operator to have already checked the library's state; the same reasoning
applies here with the same confidence level. Flagging as the same open question, extended to a
module sweep56-batch15 did not have in scope, rather than as a new class of finding.

**Nothing else found in retry_synthesis.py.**

---

## suppressions.py

Read in full, unchanged since sweep56-batch12's read (353 lines, same as then). The
unreadable-vs-empty distinction in `_load()`, the whole-value-stored (never-truncated)
`reason` field in `add()`, `remove()`'s fail-closed refusal over an unreadable file, and the
case-sensitive `fnmatchcase` gate in `suppressed()`/`problems()` (deliberately never plain
`fnmatch`, to avoid Windows case-folding silently widening a suppression) all match their own
extensive commentary and sweep56-batch12's read.

**KNOWN(sweep56-batch12 finding #4) — the `drill.py:2515` self-citation at L247 is still stale,
still uncorrected, drift measured fresh this batch.** `suppressions.py` L245-248:
```
    IT WAS INSIDE THE LOOP. `problems()` built the listing once PER WILDCARD ROW, so the entire
    repository -- ... -- was walked again for every wildcard suppression on file, and
    `drill.py:2515` calls `problems()` every cycle as a net.
```
Verified against current `src/drill.py` (17,928 lines, grew from the 17,710 sweep56-batch12
measured): `grep -n "suppressions" src/drill.py` shows the only import at L4576 and the actual
`SUP.problems()` call inside a `net(...)` at **L4582** — a further ~2,067-line drift past the
`4582` sweep56-batch12 already found (up from that batch's citation gap of `2515`→`4582`; the
stale number `2515` itself is unchanged since it was never corrected). Same defect, same file,
still open; not re-filed as new.

**KNOWN(sweep56-batch12 Q2, unchanged) — `add(..., ttl_days=DEFAULT_TTL_DAYS)` still has no upper
bound.** `add()` (L109-154) validates only that `reason` is non-empty and ≥12 characters; nothing
bounds `ttl_days`, so a caller (or a typo — `ttl_days=18000` instead of `180`) can mint a
suppression that outlives any realistic review cycle. Same code as sweep56-batch12 found; not
re-analysed further.

**Nothing else found in suppressions.py.**

---

## entity_match.py

Read in full, unchanged since sweep56-batch05's read (310 lines, same as then; the file remains
uncalled from anywhere in `src/` — confirmed no writes, no CLI mutation path, and the module
docstring and header still say "nothing calls this module yet"). `qualifier_compatible()`'s
absolute (never-scored) gate against merging the three Wally West continuities, `similarity()`'s
documented rejection of swapping in `rapidfuzz` (measured 27% disagreement on the calibrated
thresholds), and `candidates()`'s uniform four-key return shape (including the
`order 21f729df8884` fix for the two early-exit paths) were all re-traced and match.

**QUESTION (re-confirmed, sweep56-batch05, unchanged) — the STRONG/WEAK ordering guard is a bare
`assert`.** L195: `assert 0.0 < WEAK < STRONG <= 1.0, "entity_match: STRONG/WEAK threshold "`
`"ordering is broken"`. Run under `python -O` this check is stripped entirely and silently
disappears — for a module whose whole design constraint is "a similarity score must never be
allowed to overrule a continuity marker," a stripped assert protecting the very thresholds that
decide EXACT/STRONG/WEAK labelling is a checked-in check that a common invocation flag can
silently remove. Nothing in this project runs Python with `-O` today (not found in any launcher,
`.vbs`, or subprocess call across the batches read this run and prior sweeps), so this is dormant,
matching sweep56-batch05's original framing. Not re-raised as new.

**Nothing else found in entity_match.py.**

---

## Coverage recorded

`sweep_plan.record('run57', [...8 modules...], batch=15)` — see command output below.
