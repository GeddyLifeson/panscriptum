# AUDIT batch06 — run56

Modules read in full, top to bottom: `src/standards.py` (2467 lines), `src/codewatch.py` (1028),
`src/estate.py` (723), `src/policy.py` (575), `src/scope.py` (474), `src/cosmography.py` (376),
`src/physics.py` (313), `src/halo.py` (220), `src/cachekey.py` (213).

General note: all nine modules are unusually heavily self-documented, with most historical bugs
described in detail alongside their fixes. The great majority of what looks alarming on a skim
("cannot fail", "fail open", "swallowed") is a documented, deliberate design decision with a
named incident behind it. I have tried hard not to re-report those as new findings — see the
"nothing found" lines below for modules where I looked specifically for the listed defect classes
and did not find a live, unfixed instance. Findings below are only things I could not find prior
documentation excusing.

---

## DEFECT — stale line-number citation, standards.py:1473

```
1473:            # restated by hand from CHARTER_REGRESSION_MAX_AGE_H (:525) the way every other
```

`CHARTER_REGRESSION_MAX_AGE_H` is declared at **line 635** (`CHARTER_REGRESSION_MAX_AGE_H = 26`),
not line 525. The comment is making a point about not hand-restating this exact constant instead
of interpolating it — a citation that no longer points at the declaration undermines the very
point it's making (a reader who "goes and checks :525" finds unrelated code). Confidence: DEFECT
(cheaply verified with `grep -n`).

## DEFECT — stale line-number citation, policy.py:423 ("uncut at policy.py:339")

```
423:                # to this at policy.py:339. Filed at INFO ...
```
(full text: "the record loop's twin was uncut at policy.py:339")

Line 339 is currently `return 0` (the `ap.print_help()` early-exit branch). The record-loop
"uncut" fix the comment is pointing at — `unreadable.append((os.path.basename(p), "%s: %s" %
(type(e).__name__, e)))` — is now at line **363**. Confidence: DEFECT.

A second, related citation in the same block, `policy.py:497` ("the record loop's twin was
already changed to this at policy.py:~477"), is hedged with `~` and is also off — the actual
"PAD, DO NOT CUT" UNREAD-print for records is at line **528**, not ~477 (off by ~51 lines).
Because it is explicitly approximate I rate this one QUESTION rather than DEFECT, but flagging it
since it compounds the first.

## DEFECT — stale line-number citation, scope.py:383

```
383: # (magnitude.py:942), which reads SCOPE.json directly and reimplements the live-probe fallback.
```

`magnitude.host_ceiling` is defined at **magnitude.py:1721** today, not 942 — a drift of 779
lines. (magnitude.py is not in this batch, but the citation lives in scope.py and was cheap to
verify with `grep -n "def host_ceiling" src/magnitude.py`.)

## DEFECT — stale line-number citation, scope.py:466

```
466:        # ceilings. Same doctrine as catalogue_codex.py:315-331.
```

Lines 315-331 of `catalogue_codex.py` are mid-way through an unrelated duplicate-element-detection
routine (`norm()` collisions in manifest parsing), not the "verdict reaches the exit code / return
1 on a denied write" doctrine the comment is invoking. The matching pattern in that file (return 1
on a denied write, verdict reaching the process boundary) is around lines 496-507 today.

---

## DEFECT (verified, undisclosed truncation matching Hard Rule 0's shape) — policy.py:389

```
389:            evals.append(evaluate(row, COVERAGE_RULES, str(row.get("source"))[:40]))
```

This truncates a coverage row's `source` name to 40 characters with **no marker** and stores the
truncated value as the evaluation's `subject`, which is persisted verbatim into
`state/policy_report.json` via `report()`. This is a different case from the many `[:26]`/`[:34]`/
`[:38]` cuts elsewhere in this same file (lines 389 vs. 540/543), which the module's own docstring
for `_observed()` explicitly excuses as acceptable **display-only** caps "at the call sites" —
this one is not a display cap, it lands in the persisted report file, exactly the distinction
`_observed()` itself draws ("a cap is acceptable exactly where it is reversible").

Verified against the live corpus (`data/COVERAGE.json`, 210 rows): **14 sources exceed 40
characters**, e.g. `"War Thunder + World of Tanks/Warplanes/Warships (space-refit)"` (61 chars),
`"Who Framed Roger Rabbit (incl. all content from its associated crossover-toon IPs)"` (82 chars).
No two currently collide on their first 40 characters (`Counter` check found zero collisions
today), so this is not actively mislabeling two different sources' findings against each other
right now — but the same undisclosed-truncation shape is exactly what this project's own
`cachekey.py` (M23) and multiple `standards.py` fixes were written to eliminate elsewhere, and a
report row's `subject` silently losing its tail is the kind of thing that reads fine until two
long names first agree on their first 40 characters. Confidence: DEFECT (undisclosed truncation of
a persisted identifying field), though not currently causing an observed collision.

---

## QUESTION — standards.py:1188, a standard hard-coded to always hold

```
1188:            "probe failures (reported, not judged)", True, f"{probe:,}", "no floor",
```

`_s(name, holds, observed, floor, order, severity, group)` is called with a literal `True` for
`holds`, so this row can never appear as a work order. This is exactly the "check that cannot
fail" shape Hard Rule -1 warns about — but it is also explicitly self-labelled "(reported, not
judged)" and the surrounding comment says plainly this is deliberate: probe-class failures (host
detection, scout candidate probing) are the *method*, not damage, so this row exists purely to
surface the count without gating on it. I am not confident this is a defect since it is clearly
intentional and documented immediately above it — flagging as a QUESTION for the record because
it is the one place in `check()` where `holds` is a literal constant rather than a computed
comparison, and it is worth an explicit owner sign-off that a permanently-`True` row is fine to
leave inside the same `_s()` mechanism every other (fallible) standard uses.

## QUESTION — policy.py, a malformed rule table entry could surface as "record unreadable"

`check_rule()` raises `BadRule` for a rule with a bad `op`/`arg` (by design, so a typo in a rule
table is never silently graded as a passing or failing *document* — see the long comment at
policy.py:161-171). But `evaluate()` calls `check_rule()` with no try/except, and in `main()` the
only callers that wrap `evaluate()` in try/except (the per-record loop at line 352-364, the
evidence-sweep worker at line 413-427) catch it as a bare `except Exception`, which folds a
`BadRule` into "record unreadable" / "evidence file unreadable" for *every* document evaluated
against that table — the exact confusion (`"a malformed rule reported as a failing document ...
sends the reader to the wrong place entirely"`) the module's own docstring says `BadRule` exists
to prevent. Today none of the three live rule tables (`RECORD_RULES`, `EVIDENCE_RULES`,
`COVERAGE_RULES`) contains a malformed rule, so this is inert — the same "landmine for the next
table" the module's own comments already accept for `TYPES`'s default and `ARG_REQUIRED`. Flagging
as a QUESTION rather than a DEFECT because it may be judged an acceptable residual risk consistent
with the rest of the file's stated philosophy, but the mechanism does not fully deliver on the
promise made two paragraphs above `check_rule()`.

---

## Nothing found

- **standards.py** — read in full. This file has an enormous back-catalogue of fixed defects
  (fail-open paths turned fail-closed, vanishing standards routed through `_dropped`, tautological
  progress checks replaced with delta measurements, etc.), all of which read as already-repaired
  in the current source. I looked specifically for: guards on undefined names (none), a second
  literal duplicating `tuning.MIN_CALLS_TO_JUDGE` (removed, now derived), caps/slicing on rosters
  or name lists (all of the ones I found were historical, already fixed, e.g. `[:3]`/`[:60]`/
  `[:120]`/`[:18]`/`[:28]` are all now un-capped with the old cut described only in comments), and
  read-modify-write races on `state/job_progress.json`/`state/read_progress.json` (both go through
  `silence.write_json` and a denied write is routed to `_dropped` rather than silently accepted).
  Aside from the stale citation and the tautological-but-labelled row above, nothing new found.
- **codewatch.py** — read in full. The restart-ledger read-modify-write goes through
  `_ledger_lock()` (an `O_CREAT|O_EXCL` mutual-exclusion file) before `_take_locked()` touches the
  document, closing the specific twin-race the module's own docstring describes (order
  b67c5d98c91f / run #36). `stale()`'s two-clock settle-window logic (`seen` vs. `quiet`) was
  worked through by hand and is self-consistent with its own docstring. `twins()`/`claim_singleton`
  are documented FAIL-OPEN by design (no psutil, or an unreadable process table, means "no twins
  found" rather than refusing to start) — an explicit, argued trade-off, not a silent one. No
  caps, no bare `except: pass`, no dead code beyond what is already self-reported (none is).
- **estate.py** — read in full. The `inspect()`/`artifacts()` no-sampling walk, the `.jsonl`
  torn-line detection, the retry-then-classify stat-failure handling, and `charter()`'s four
  behavioural (not string-presence) erratum checks were all worked through. No caps found (every
  historical `[:N]` cut this file describes is already removed from the live code — `un[:4]` in
  `charter()` is now the full uncapped list, as the comment at line 421-431 confirms and as the
  code at line 432-433 shows).
- **scope.py** — read in full, aside from the two stale citations above. `ProbeUnread` correctly
  distinguishes "not read" from "read, nothing cleared MIN_MENTIONS", `build()`'s compare-and-swap
  via `mutate()` is key-wise rather than whole-document, and the tier logic (highest tier clearing
  `MIN_MENTIONS`, never argmax) matches its own docstring's stated method. `ceiling_for()` is
  already self-flagged dead code per house doctrine (mark and keep, order de43fe54feb7) — not a
  new finding.
- **cosmography.py** — read in full. `validate()`'s Kardashev-ceiling and size-class-ceiling
  checks are both real, non-tautological comparisons against the document being judged; hand-
  checked the arithmetic for POCKET/MINOR/STANDARD against `SIZE_CLASS_MAX_GALAXIES` and both
  non-standard classes land at or under their own ceiling (MINOR computes exactly 1.0 galaxy
  against a ceiling of 1.0; POCKET computes ~1e-8). `KARDASHEV_MIX` sums to 1.0 (checked). No caps,
  no dead code, no fail-open paths (this module raises rather than silently accepting an invalid
  census).
- **physics.py** — read in full. Every public function (`kinetic`, `joules_for`, `sphere_volume`,
  `binding_energy`) has matched NaN/negative/infinite/overflow guards on every parameter and on
  its own result, each with a specific incident cited in a comment. No caps, no silent failure, no
  guard that cannot fire (each guard's docstring cites the actual input that used to slip past it).
- **halo.py** — read in full. Per-axis provenance tagging (`wiki`/`canon`) is applied consistently
  across all three roster entries and all axes; the `--full` printer wraps rather than cuts
  citation text; the write path checks `silence.write_json`'s landed/denied verdict and returns a
  non-zero exit code on denial. No caps, no fail-open, no tautologies found.
- **cachekey.py** — read in full. `owns()`'s entity+host check, `load()`'s verify-before-trust,
  and `write_path()`'s collision-avoiding suffix all match the module's own stated M23 fix. No
  caps (the `[:80]`/`[:40]`/`[:10]`/`[:16]` slices here are the *fixed-width digest/sanitiser*
  the module exists to make collision-safe via `owns()`'s verification step, not a roster/list
  truncation — this is the one file in the batch where a fixed-length slice is the correct
  behaviour, not a Hard Rule 0 violation, because every read is verified against the unsanitised
  `entity` field before being trusted).

---

## Coverage

Recorded via `sweep_plan.record('run56', [...], batch=6)` — see tool output in the session; all
nine listed modules were read in full as required.
