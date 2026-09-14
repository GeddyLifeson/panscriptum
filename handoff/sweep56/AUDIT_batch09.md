# AUDIT — run56, batch 09

Modules read in full, top to bottom: `src/foreman.py` (1993 lines), `src/overwatch.py` (1099
lines), `src/completeness.py` (867 lines), `src/custodes.py` (699 lines), `src/worldseed.py`
(533 lines), `src/runguard.py` (383 lines), `src/descending_ladder.py` (358 lines), `src/tells.py`
(297 lines).

Per the work order's note, `runguard.py` was read in full but not edited, and the already-known
open item (the guard records no pid; `holder_is_live` never consults the process table) is
excluded from this report — it is owned by a separate lane. Everything else found in that file
is reported below.

All findings below were verified against the current source with `sed`/`grep` at the time of
writing. Every quoted "actual" location was re-read directly.

---

## Category: stale line-number citations in comments

This turned out to be the dominant defect class in this batch. Nearly every cross-file or
self-referential `file.py:NNN` citation checked in `foreman.py`, `overwatch.py`, `completeness.py`
and `custodes.py` no longer points at the code it describes — evidence of heavy post-hoc editing
that moved code without updating the line numbers named in nearby comments. By contrast, every
citation checked in `descending_ladder.py` was still correct (see the "nothing found" note for
that file). `worldseed.py` had one stale self-citation. `runguard.py` and `tells.py` carry no
`file.py:NNN` citations at all.

### foreman.py

1. **foreman.py:113** — DEFECT
   Quote: `` # `--quick` skips only the VERIFY and ESTATE tiers (allsweep.py:702, :727) -- IMPORT and LINT``
   The cited lines (allsweep.py:702, :727) are inside `estate_faults()`'s docstring/body, unrelated
   to `--quick`. The actual `if not a.quick:` gates for the VERIFY and ESTATE tiers are at
   `allsweep.py:818` and `allsweep.py:843` respectively. The prose claim itself (IMPORT/LINT
   always run, VERIFY/ESTATE skipped under `--quick`) still checks out against `allsweep.py:741,
   818, 843` — only the line numbers are wrong.

2. **foreman.py:122** — DEFECT
   Quote: `` verify_math.py:6051 (and again at :6283) records a standing rule that verify_math.py``
   `` and drill.py "are not safe to run" concurrently from an agent context``
   Neither verify_math.py:6051 nor :6283 contains this text (6051 is mid-`_REPAIRED_20g` atomic-write
   loop; 6283 is about `name_rc` for TerminateProcess). The actual "not safe to run concurrently"
   language (order c349a51ee2c5) appears at `verify_math.py:8681-8682`, `9095`, `9949`, and `10370`.

3. **foreman.py:232 and foreman.py:1774** — DEFECT (same stale citation, two sites)
   Quote: `` write_json's temp carries pid and thread (silence.py:511)``
   Line 511 of `silence.py` is inside `append_line()`, unrelated to `write_json`'s temp naming.
   The actual pid/thread temp-name construction (`"%s.%d.%d.tmp" % (path, os.getpid(),
   _th.get_ident())`) is at `silence.py:827`.

4. **foreman.py:294** — DEFECT
   Quote: `` SAME TEST AS scout.py's OWN found COUNTER (scout.py:616)``
   Line 616 of `scout.py` is mid-comment about whole source names in a deferral list, unrelated.
   The actual `found` counter and its `registered is True` test are at `scout.py:640` and
   `scout.py:649-650`.

5. **foreman.py:389** — DEFECT
   Quote: `` health.py:198-210 records the interleaved-writer corruption of `state/failures.json` ``
   `` verbatim``
   `health.py:195-212` discusses a *different* incident (a `RuntimeError` from concurrent dict
   mutation during flush). The "interleaved-writer" `failures.json.corrupt` finding is actually
   discussed at `health.py:390-411` (comment naming the "interleaved-writer shape" and the
   102-byte/38-byte corrupt file).

6. **foreman.py:580** — DEFECT
   Quote: `` The fragment is "read.py --run", which is how overnight.py:1425 actually launches it.``
   `overnight.py:1420-1428` is inside `_write_status`'s denied-replace handling, unrelated to
   launching the reader. The actual STANDING-list entry that launches `read.py --run` is at
   `overnight.py:1049-1050`.

7. **foreman.py:638** — DEFECT
   Quote: `` SAME KEY DERIVATION AS standards.py:1511-1512, the code that writes the names this``
   `` function parses``
   `standards.py:1505-1515` is inside a throughput-history/dashboard-restart block, unrelated. The
   actual `fn[:-4] if fn.endswith(".log") else fn` key derivation is at `standards.py:1693`.

8. **foreman.py:1426** — DEFECT
   Quote: `` THE DRILL STAYS OUT, per the same ruling. verify_math.py:5504 records the standing``
   `` rule that verify_math and drill are not safe to run from an agent context``
   `verify_math.py:5500-5508` is inside an unrelated `running(include_self=True)` test block. As
   with finding 2 above, the real text is at `verify_math.py:8681-8682` / `9095` / `9949` / `10370`.

Nothing else found in foreman.py. The module's remedy logic, DENYLIST/NEVER_DEDUPED construction,
`_checks_pass`/`_contracts_pass` gating, `attempt_patch`'s guard order, `round_once`'s
`.always`-remedy handling, and all atomic-write call sites were read closely and are internally
consistent with what their own comments claim. No bare `except: pass`, no undisclosed `[:N]`
truncation of a roster/list (every slice found is either an error-message truncation to `str(e)`
or an explicitly-disclosed console-display cap with the full data still written to disk), and no
tautological checks were found.

### overwatch.py

9. **overwatch.py:343** (self-citation) — DEFECT
   Quote: `` IT SURVIVED READING BECAUSE THE INTENT IS VISIBLE AND CORRECT. The comment at :341``
   `` says `last_run` values are "zero-padded 'YYYY-MM-DD HH:MM', so that is time order"``
   Line 341 of this same file is part of the docstring text making this very point (it is the
   sentence before, about "2026-..." vs "1788..." string comparison), not the comment being
   described. The `last_run` comment actually being referenced ("last_run max as a string; these
   are zero-padded...") is at `overwatch.py:391`, inside `_merge_ledgers`'s docstring.

10. **overwatch.py:865 and overwatch.py:1061** — DEFECT (same stale citation, two sites)
    Quote: `` the house exemption for console renderers (ingest_doc.py:363) does not reach it.``
    and `` A CONSOLE renderer, so the cut stays (house exemption, ingest_doc.py:363)``
    `ingest_doc.py:355-365` is mid-comment about chunk-splitting boundaries, unrelated. The actual
    "house exemption for console renderers" text ("Other writers store them whole; the console
    renderers truncate at their own call sites") is at `ingest_doc.py:474`.

Nothing else found in overwatch.py. The ledger merge/CAS logic (`_merge_ledgers`, `_progress`,
`_reconcile_with_disk`), the `_LOCAL_BUSY` per-round reset, the `complete`-gated `seen`/
`last_verified` stamping, and `write_report`'s uncapped findings list were all read closely and
match their documenting comments. No bare `except: pass` and no undisclosed caps found.

### completeness.py

11. **completeness.py:465-466** (self-citation) — DEFECT
    Quote: `` none of this function's four call sites -- :473, :477, :489, :560 -- ever passed``
    `` either``
    None of lines 473, 477, 489, or 560 is currently a call site of `_unmeasured()` (473 is a
    closing docstring `"""`, 477 is mid-dict-comprehension inside `_unmeasured` itself, 489 is a
    comment line, 560 is a comment line). The current call sites are at `completeness.py:495,
    499, 511, 584, 612` — five, not four (a fifth was added by a later change, order
    d2da5914da94, promoting the "genuine absence" branch — itself correctly explained a few lines
    later in the same docstring, so the substance is fine; only the old line-number list is stale).

12. **completeness.py:71** — DEFECT (two stale citations on one comment line)
    Quote: `` the project's own idiom for telling them apart is``
    `` `str(h).startswith(("pages:", "doc:"))` -- binding_health.py:1018 and health.py:486-488``
    `` both do exactly this``
    `binding_health.py:1018` is mid-comment about a `titles` field, unrelated; the actual
    `startswith(("pages:", "doc:"))` idiom in that file is at `binding_health.py:1223`.
    `health.py:486-488` is mid-comment about `_SAMPLES.clear()`, unrelated; the actual sentinel
    check in that file (`if h.startswith("pages:") or h.startswith("doc:"):`) is at
    `health.py:654-656`.

13. **completeness.py:356** — nothing found (citation checked and correct)
    Quote: `` `api_url` returns None for MODE_RAW exactly as it does for MODE_DEAD --``
    `` `endpoint.py:275-278` --``
    Verified: `endpoint.py:275-277` is exactly `def api_url(host): ... return f"..." if
    d["mode"] == MODE_API else None`, i.e. returns None for both MODE_RAW and MODE_DEAD. Off by
    at most one line and materially accurate.

Nothing else found in completeness.py. `land()`'s three-valued return, the shrink-floor guard,
the `_unmeasured` row-shape discipline, and `host_reachable`'s three-mode handling were all read
closely and match their comments. The `--top` print cap in `main()` is explicitly disclosed
("the file always holds every row") and the full row set is written to `COMPLETENESS.json`
unconditionally — not a Hard Rule 0 violation.

### custodes.py

14. **custodes.py:355-357 and :438-440** — DEFECT (stale citation *and* stale factual claim)
    Quote (355-357): `` both were then wired to a keyword argument that no production caller``
    `` supplies -- `anchors.py:190`, the single real call site, passes neither `eta` nor``
    `` `distance`/`years_since`.``
    Quote (438-440, `convene`'s docstring): `` `distance`/`years_since` are what Lumen reads, via``
    `` `propagation.observed_mark`. No caller supplies them either, so `staleness_widening```
    `` contributes exactly 0.0 to every real interval.``
    Two problems, not one:
    - The line number is wrong: the actual (and only) production call to `custodes.convene()` is
      at `anchors.py:236-237`, not `:190`.
    - The factual claim is now **out of date**, not merely mis-cited. `anchors.py:175-217`
      documents owner ruling `bd673ceaaf31` (2026-09-08): "pass distance=0.0 for Lumen as a
      stated convention while Threnody stays abstained." The call at `anchors.py:236-237` now
      reads `distance=_dist, years_since=_since` from `_anchor_vantage()`, which returns real,
      non-None values (`0.0, P.ascension_years(P.LADDER_HEIGHT)`). So Lumen's `currency`
      abstention path (`custodes.py:403-410`) is *not* taken on this call any more, and
      `staleness_widening` does *not* contribute exactly 0.0 to the anchor readings — `eta`/
      Threnody's abstention is still accurate (anchors.py never passes `eta`), but the
      distance/years_since half of the claim is stale. `anchors.py:496-501` even carries its own
      verify_math-style check confirming the fix ("Lumen measured staleness at every anchor
      rather than abstaining"). custodes.py's own docstring was not updated to reflect this.
      Confidence: DEFECT on the line number; DEFECT (not just QUESTION) on the "no caller
      supplies them" claim, since it is directly contradicted by currently-live code in the
      project's own acknowledged sole production caller.

Nothing else found in custodes.py. The degrees-of-freedom table, `_custos_reading`'s prior/
evidential split, `_transit_widening`'s dispersive-but-unmechanised bookkeeping, `convene`'s
attendance flags, and `table_faults()` were all read closely and are internally consistent
(including the explicitly self-disclosed non-check `"covers_every_reading"`, which the code's own
comment at custodes.py:542-550 already flags as "a GUARANTEE being published, not a check being
run" and "true by construction" — this is a known, documented, not a hidden, non-check).

### worldseed.py

15. **worldseed.py:367-368** (self-citation) — DEFECT
    Quote: `` What this handler actually leaves behind is `reg_by_group`, already initialised at``
    `` line 315 outside the try``
    Line 315 of this file is inside `unreachable_by_url`'s docstring, unrelated. The actual
    `reg_by_group, bad_rows = {}, 0` initialisation is at `worldseed.py:355`.

Nothing else found in worldseed.py. `to_options()`'s band-parsing (`band_provenance` tri-state),
`_first()`'s attested-vs-seeded fallback, the `limit is not None` guard fix in `build_all()`, and
the `args.write` collision-reporting/atomic-write path were all read closely and match their
comments. `TEMPLATE` and `CULTURE_SET` dict coverage of every value the `LANDFORM`/register
tables can produce was checked and is complete (no missing-key risk). The `most_common()`
call in `main()` is uncapped as its comment claims.

### descending_ladder.py — nothing found

All three citations in this file's docstring were checked and are correct:
`publish.py:1346` (`import render as R`, verified verbatim), `anchors.py:43` (the
`NON_ENERGETIC_AXES["transgression"]` entry, verified verbatim: "Use `transgression_bits()`."),
and `handoff/queue/OWNER.md:158` (the `- **where**: src/descending_ladder.py:1` line, verified
verbatim). The physics (`PLANCK_ENERGY = PLANCK_MASS * C_LIGHT ** 2`, the U-shaped binding column,
`rung_for_length`'s monotonic-length lookup and both-ends domain guard, `transgression_bits`'s
and `shrink_report`'s non-positive-input refusals) was traced by hand and is self-consistent.
This module is genuinely unwired dead code, but that is stated as a deliberate, owner-ruled hold
(order `66f96febdb3a`) rather than a hidden defect, and the docstring's account of that state is
accurate as of this reading.

### runguard.py — nothing else found

Read in full. Aside from the already-known, separately-owned issue (no pid recorded in the guard
record; `holder_is_live` at runguard.py:180-199 never consults the OS process table, only the
heartbeat timestamp), the rest of the file is internally consistent: `read_verdict`'s three-fault
taxonomy, the digest-before-read ordering in `claim`/`beat`/`release`, and the ownership checks in
`beat`/`release` (refusing to stamp a record that is not the caller's own, or one already closed)
all match their documenting comments. No stale line citations (none present). No bare
`except: pass`; the two `_ = "silence-exempt: ..."` sites are the project's established idiom for
a deliberately untracked non-event (absent-file-on-first-run, own-pid temp-file cleanup), not
silent failures.

### tells.py — nothing found

Read in full. No `file.py:NNN` citations present. The lexical/structural/discourse pattern tables,
the `_anchor()` sentence-boundary rewrite (verified against every `^\s*`-prefixed pattern in
`STRUCTURAL`/`DISCOURSE`), the control-character guard, and `prompt_in_sync()`'s drift check were
all read closely. Live-verified (read-only): running
`python -c "import sys; sys.path.insert(0,'src'); import tells; print(tells.prompt_in_sync())"`
against this repo returns `(True, "system_style.txt carries the generated block verbatim (2683
chars)")`, confirming the prompt and the checker are currently in sync, i.e. the `a08557925d87`
fix this module's docstring describes is still in effect today.

---

## Other categories checked, with no findings

- **Checks that cannot fail / tautologies / undefined-name guards**: none found beyond the
  self-disclosed `custodes.py` `"covers_every_reading"` field noted above, which the code's own
  comment already names as a non-check rather than hiding it.
- **Fail-open where the house rule is fail-closed**: none found. Every guard checked
  (`foreman.main`'s escalation-import check, `overwatch.main`'s same check, `restart_ollama`'s
  stamp-read guard, `runguard.read_verdict`'s corrupt-guard handling) either fails closed or is a
  documented, owner-ruled exception (runguard's fail-open on a corrupt guard, order 70f66fbd98aa,
  which is now escalated at SAFETY rather than silent — this is the separately-owned item, not a
  new finding).
- **Silent failure (bare `except: pass`)**: none found in any of the eight modules. Every
  `except` either calls `silence.note(...)`, returns a stated failure value, or is one of the
  project's own explicitly-commented `"silence-exempt: ..."` sites for a genuinely benign,
  first-run-shaped absence.
- **Caps / truncation / sampling on any roster or entry set**: none found. Every `[:N]` slice
  located in these eight files truncates either an error-message string for a log line, or a
  console print with an explicit "N of M, the file holds every row" disclosure and the full set
  still written to disk.
- **Lost-update / read-modify-write races on shared state files**: one soft QUESTION, not a
  DEFECT — `foreman._catalogue_batch()` (foreman.py:921-944) reads, mutates, and writes
  `state/CATALOGUE_ATTEMPTS.json` through `silence.write_json` (atomic replace) but *without* a
  compare-and-swap, unlike the CAS pattern used elsewhere in this same codebase for
  higher-stakes shared files (e.g. `runguard._land_claim`, `overwatch.save`/`_merge_ledgers`).
  Two concurrently-running foremen (explicitly permitted by this file's own design — the
  singleton claim lives inside `if a.loop:`) could race here and lose one side's timestamp
  update. The function's own comment already reasons about the *denied-write* case and
  concludes the cost is bounded ("nothing is dispatched twice ... the same batch sorts to the
  front again next round"), and that same bound applies to a lost-update race, not just a
  denied write — so this looks like a deliberate, low-stakes tradeoff rather than an oversight,
  but it is called out as a QUESTION because the reasoning for *why CAS was skipped here but used
  for OVERWATCH.json* is not spelled out anywhere.
- **A supervisor reading a deliberate rc as a crash**: not applicable to any of these eight
  modules directly; `foreman.py` and `overwatch.py` both correctly treat `codewatch.exit_if_stale`
  as an intentional restart mechanism and neither implements the interpretation of rc=17 itself
  (that lives in `overnight.name_rc`, outside this batch).
- **Dead code / unreachable branches**: `descending_ladder.py` is wholesale unwired but is
  explicitly owner-ruled "hold, marked" (see above) rather than a silent defect. `worldseed.py`'s
  unreachable `"primitive"` TECH/size key and `unreachable_by_url`/`URL_SETTABLE` are likewise
  explicitly marked and owner-ruled to stay. `completeness.py`'s `category_size()` is marked dead
  and kept per house doctrine. None of these read as *undisclosed* dead code.

---

## Coverage recorded

`sweep_plan.record('run56', ['foreman.py','overwatch.py','completeness.py','custodes.py',
'worldseed.py','runguard.py','descending_ladder.py','tells.py'], batch=9)` was run from the repo
root with `PYTHONIOENCODING=utf-8` under `C:/Users/imarl/miniconda3/python.exe` and returned
successfully (all eight modules now stamped `run56` in the coverage ledger).
