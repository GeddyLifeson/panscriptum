# AUDIT — run56, batch 15

Modules read in full, top to bottom (all listed line counts confirmed against `wc -l`):
`src/local_agent.py` (1639), `src/escalation.py` (1445), `src/generate.py` (977),
`src/endpoint.py` (577), `src/tiers.py` (543), `src/coverage.py` (436),
`src/resync_roll.py` (332), `src/propagation.py` (254), `src/repass_bands.py` (189).

No fixes, edits or writes were made. `escalation.py`'s standing OWNER halt was not touched,
diagnosed, or cleared. `prose_enabled` / `step4_enabled` were not touched. No subagents were
spawned.

General note: every one of these nine files already carries an extensive in-source audit
trail (order hashes, run numbers, "found by sweepNN-batchNN" citations) documenting many past
fixes to exactly the failure classes this brief asks about (fail-open paths, checks that
cannot fail, undisclosed truncation, lost updates). Most candidate findings below turned out,
on reading the surrounding comment, to already be the FIXED state of a defect the file itself
describes — those are recorded as "nothing found" rather than re-reported as new.

---

## FINDING 1 — `generate.py` carries no `escalation.assert_clear()` interlock (QUESTION)

**Module:** `src/generate.py` (whole file). Verified with
`grep -n "assert_clear\|import escalation" src/generate.py` → no hits.

**What:** Of the escalation-chain-critical modules in this tree, `generate.py` is the one that
actually writes finished prose chapters to disk (`save_raw`, `compress_store.store`, the
`catalog[...]` write in `main()`). It never imports `escalation` and never calls
`assert_clear()` anywhere — not in `main()`, not in `generate_job()`. Its own module docstring
documents direct, by-hand invocation as normal usage:

```
python3 src/generate.py --manifest output/index/manifest.pilot.json
python3 src/generate.py --manifest output/index/manifest.json --limit 20
```

**This is already known and partially mitigated, not a fresh discovery** — `src/overnight.py`
documents the exact same fact in its own comments (around its per-cycle dispatch of the prose
stage):

> "`generate.py` -- the prose stage below -- has NO halt interlock anywhere in it (grep for
> escalation/assert_clear: no hits). It is the one job this cycle can start that would not
> notice the library halting under it, so it is the one job that needs this verdict."

and mitigates it at the *dispatch* site: `overnight.py` calls `_ESC.assert_clear()` once per
cycle before doing anything, then additionally gates the `start("prose", [...generate.py...])`
call on `drill_rc != 1` (the same-cycle safety-net inspection), explicitly because generate.py
itself carries no interlock of its own.

**Why it still matters / the open question:** That mitigation only covers the path where
`overnight.py` is the thing starting `generate.py`. It does not cover:
- a hand-run of `python src/generate.py --manifest ...` — generate.py's own documented usage —
  during a standing OWNER halt (such as the one currently standing on this run);
- any other future automated caller that invokes `generate.py` directly rather than through
  `overnight.py`'s cycle loop.

The only thing that would stop such a run is the separate `prose_gate` / `prose_enabled`
config flag (checked via `PG.assert_gate_open(cfg)` in `generate.py:main()`), which is a
different safety with a different, and previously-defeated, failure history in this same
codebase (`local_agent.py`'s own `DENYLIST` comment records that `overnight.py` once
reimplemented this same gate with `bool()` instead of a strict check, so
`prose_enabled: "false"` opened it). The OWNER halt and the prose gate are supposed to be
independent layers; for `generate.py` specifically, only one of them is actually wired to the
module doing the writing.

**Confidence:** QUESTION. The gap is real and verified by grep; whether the residual
hand-run/direct-invocation exposure is an accepted risk (mitigated "close enough" by the
dispatch-side check) or should be closed by adding `escalation.assert_clear()` to
`generate.py`'s own `main()` (matching the twelve other modules `local_agent.py`'s own comment
enumerates: pipeline, publish, feats, read, foreman, overnight, overwatch, allsweep, dashboard,
drill, verify_math, escalation) is a decision for the owner, not something I should silently
call a defect and fix.

---

## FINDING 2 — `repass_bands.py` and `resync_roll.py` carry no halt interlock either, and are not gated by any dispatcher (QUESTION, lower confidence)

**Module:** `src/repass_bands.py` (whole file), `src/resync_roll.py` (whole file). Verified
with the same grep — no hits for `escalation`/`assert_clear` in either file.

**What:** Both are corpus-mutating maintenance scripts:
- `repass_bands.py --apply` rewrites `data/records/*.json` corpus-wide via
  `pipeline.write_record`, demoting Magnitude bands whose evidence no longer passes the
  (corrected) gate. Its own comment at line ~87 calls this "the corpus-wide run".
- `resync_roll.py` rewrites `data/SWEEP_ROLL.json` (via `roll.mutate`), correcting
  `entry_count`/`status` drift.

Neither calls `assert_clear()`. `pipeline.write_record()` (which `repass_bands.py` calls) also
does not call it internally — `pipeline.py`'s own `assert_clear()` call lives in its `main()`,
not in `write_record()`, so importing the function does not inherit the check.

I checked whether either script is dispatched (and therefore possibly gated) by another
module. `allsweep.py` names both in its own `NEVER_RUN` set (alongside `generate` and
`pipeline`) with the comment: "Modules whose no-argument run does real, expensive or mutating
work. They are still IMPORT checked; they are simply never invoked." So `allsweep.py` never
actually runs either script's mutating path, and provides no dispatch-time gating for them
either.

**Why this is lower-confidence than Finding 1:** Unlike `generate.py`, I found no comment
anywhere in the tree acknowledging this as a known gap for these two scripts specifically.
Both read, by their own docstrings, as occasional, hand-run repair/backfill tools ("Running
this after any cataloguing session…", "Run with --apply to write" as a one-time
gate-correction pass) rather than standing/looping automated jobs — which may be exactly why
they were never brought into the `assert_clear()` convention: a person choosing to run a
repair script is arguably expected to have already checked the library's state. I cannot tell
from the source alone whether that is the actual reasoning or simply an oversight that has not
yet been hit in practice (both scripts are far less frequently invoked than `generate.py`).

**Confidence:** QUESTION.

---

## FINDING 3 — `coverage.py`: undisclosed `entries >= 40` threshold excludes small hosted sources from both ranked lists (QUESTION, minor)

**Module:** `src/coverage.py`, line 378 (`report()`):
```python
have = [r for r in rows if r["host"] and r["entries"] >= 40]
worst = sorted(have, key=lambda x: (x["coverage"], -x["entries"]))
...
best_all = sorted(have, key=lambda x: -x["coverage"])
```

**What:** Sources with a host but fewer than 40 catalogued entries never appear in either the
"WORST COVERED WITH A HOST" or "BEST COVERED" listings — not even under a disclosed cut with a
remainder count, the way `--show`/`--show-best` disclose their own caps a few lines later.
They are not double-counted anywhere else in `report()`'s output either (the headline
CITED/READ/NO PAGE/etc. totals are computed over the full `rows`, so the totals are correct;
only the two ranked per-source listings silently omit these sources). No comment anywhere near
this line explains the choice of 40 or acknowledges the exclusion.

**Why it matters:** This is the same shape Hard Rule 0 warns about — a smaller universe
(sources shown in the rankings) wearing the same shape as the real one (all sources with a
host) — though it is much milder than the truncations this file has already fixed elsewhere
in its own history (e.g. the `--show-best 0` fix, the `NOT ATTEMPTED` vs `NO PAGE`
conflation), because it is not a *count* cap, it's a *membership* filter with no visible seam.
A small hosted source that is genuinely at 0% coverage would never surface in "WORST COVERED"
at all.

**Confidence:** QUESTION — plausibly a deliberate noise-reduction choice (a single bad entry
in a 3-entry source produces a meaningless 0%/33%/66% coverage figure), but it is undocumented
and unannounced, unlike every other cut in this same function.

---

## FINDING 4 — `local_agent.py`: the halt is checked once per run, not per turn/per patch (QUESTION, low confidence)

**Module:** `src/local_agent.py`, `run()`, line 1434: `_ESC.assert_clear(who="local_agent.run")`
is called once, at the very top of `run()`, before the turn loop begins.

**What:** A single invocation can run up to `MAX_TURNS = 24` turns, and on each
`propose_patch` call that reaches `_gates()`, one of the gates is a `verify_math.py` subprocess
run with a 600s timeout — so a single run of this lane can legitimately take many minutes,
during which an OWNER halt could be raised by a completely different process (another job
detecting a library-wide invariant violation). Nothing inside the turn loop re-checks
`assert_clear()`, so such a run would keep proposing and applying patches to `src/` for the
rest of its turn budget rather than stopping when the halt lands.

**Why I am not calling this a DEFECT:** `assert_clear()`'s own docstring states the house
convention plainly: "EVERY entry point calls this before doing anything" — entry-point
granularity, not per-operation. Every other checked module in this tree (`pipeline.py`,
`overnight.py`) also checks once per invocation or once per outer loop cycle, not once per
inner action, so this matches the established pattern rather than deviating from it.

**Confidence:** QUESTION, and a weak one — flagged because `local_agent.py` is explicitly
called out (in its own comments) as "the ONLY lane in the project on which a model may WRITE
TO `src/`," which makes its window between checks the most consequential one of the twelve
gated modules, even though the pattern itself is consistent with the rest of the codebase.

---

## Per-module "nothing found" / clean-pass notes

**`src/escalation.py`** — read in full. This is by a wide margin the most heavily
self-audited file in the batch (dozens of named "order" fixes for exactly the failure classes
this brief asks about: fail-open CAS races, `_read_stopped`'s wrong-shape-vs-unparseable
handling, the float/string/out-of-range `escalate(level=...)` coercion, the `--resume`/`clear`
person-and-ruling checks, the hard-link/identity bypass). I traced the three named properties
directly:
- **FAIL CLOSED**: `_read_halt_raw()`, `_read_stopped()`, `subsystem_stopped()` all verified to
  answer "halted"/"stopped" on any unreadable or wrong-shaped file, not just a missing one.
  `_halt_lock()` is the one deliberate, explicitly-documented exception (fails OPEN by owner
  ruling 2026-09-08, because a stuck lock file must never be able to prevent a halt from being
  raised) — this is correct as designed, not a bug.
- **INDEPENDENT**: the OWNER-halt write path (`_raise_halt`/`_land_halt`) and the MANAGER-stop
  path (`stop_subsystem`/`_write_stopped`) are compare-and-swapped against their own files
  independently of each other and of `clear()`/`resume_subsystem_verdict()`.
- **PROVEN**: `_by_a_person_at_the_cli()`'s frame-counting was traced by hand against both call
  sites (`clear()` and `resume_subsystem_verdict()`, both called directly from `main()`) and is
  internally consistent — `sys._getframe(2)` correctly lands on `main()` in both cases, and the
  docstring's warning about *not* routing through the `resume_subsystem()` one-line wrapper
  (which would shift the frame count) is honored: `main()` calls
  `resume_subsystem_verdict()` directly, never the wrapper.

I found no check-that-cannot-fail, no new fail-open path, and no stale line-number citation
inside this file (its self-citations, e.g. `binding_health.py:291,416,419`, are to other
modules outside this batch and were not re-verified against those files' current line numbers).

**`src/local_agent.py`** — read in full. The write-gate (allowlist + denylist + identity/hard-
link check + junction resolution + parse/lint/import/whole-suite gates + backup/auto-revert)
was traced end to end through `_safe()`, `_denied_target()`, `_identity_denied()`, `_gates()`
and `t_propose_patch()`. All eight previously-found bypass classes documented in this file's
own comments (case-folding, name-prefix, ADS, case-sensitive extension, unlisted directory,
junction, DENYLIST_PATHS-through-junction, hard link) were checked against the current code and
each fix is present and consistent with its comment. `run()` does call `assert_clear()` (see
Finding 4 for the one caveat). No bare `except:`/swallowed-exception-with-no-note was found.
Aside from Finding 4, nothing else found.

**`src/endpoint.py`** — read in full. The `ENDPOINTS.json`/`SOURCE_PAGES.json` compare-and-swap
merge logic (`_save()`, `register()`) was traced and is self-consistent with its own extensive
comments about the lost-update history it was fixed for. `register()`'s fail-closed behavior on
an unreadable or wrong-shaped registry (raises rather than silently overwriting) was verified
directly against the code. Nothing found.

**`src/tiers.py`** — read in full, including the two refusal gates in `main()` (unreadable
`GROUNDINGS.json` and a broken containment/nesting invariant both refuse to publish
`TIERS.json` and exit 2). Nothing found.

**`src/coverage.py`** — read in full. `state_of()`'s CITED > READ > NO PAGE > UNREACHABLE >
NOT ATTEMPTED precedence logic was traced by hand across multiple candidate paths and is
correct against its own documented ordering. `measure()`'s host-map read (4 attempts, then a
hard refusal on an empty/wrong-shape result) is fail-closed. Aside from Finding 3, nothing else
found.

**`src/resync_roll.py`** — read in full. The duplicate-source "last name alphabetically wins"
claim was traced against the actual `sorted(os.listdir(...))` + dict-overwrite logic and holds.
The compare-and-swap write through `roll.mutate` and the exit-code discipline (nonzero on a
denied write) were verified. Aside from Finding 2 (interlock), nothing found.

**`src/propagation.py`** — read in full, including the by-hand trace of `observed_mark()`'s
loop direction and its claim that the trailing `return 0` is unreachable once `lag >= 0`
(confirmed: `ascension_years(1) == 0.0`, so the last loop iteration, rung 1, always matches).
Read-only module (no writes at all), so the interlock question does not apply here. Nothing
found.

**`src/repass_bands.py`** — read in full. The write-then-gate discipline (`PL.write_record`'s
return value is checked, denials are counted and named, not merely printed) was verified.
Aside from Finding 2, nothing found.
