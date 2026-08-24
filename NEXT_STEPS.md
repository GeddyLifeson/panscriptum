# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #3 wrote this on 2026-08-23 ~23:40.*

## 0. Verify first — things run #3 changed that need a second pair of eyes

1. **The stall detector is live for the first time.** `every running job is advancing` could
   never fire before run #3 (the watch stamp was re-written every pass, so it measured checker
   cadence, not silence). It now watches 3 real jobs. **Check `state/job_progress.json` and the
   standard's reading**: are the `at` stamps genuinely ageing on quiet logs, and has the
   standard reported any job stalled? If it fired, was the job actually wedged? Its AUTO remedy
   `kill_stalled_job` SIGTERMs the job, so a false positive costs a restart (resumable, keeper
   restores) — but a *pattern* of false positives means `MAX_JOB_SILENCE_MIN = 15` is too tight
   and should be raised. **Do not "fix" it by re-breaking the timer.**
2. **`entries stranded in closed batches` should fall from 5 to 0** once the bounced
   `pipeline.py` walks `Arcanum Worlds (Odyssey of the Dragonlords)` on the new code. If it is
   still 5 after a full lap, the reopen gate is not behaving as verify_math §18d claims —
   investigate the live path rather than re-patching the predicate.
3. **[m4] takes effect only when `read.py` and `feats.py --roll` next cycle** — run #3
   deliberately did not bounce them (they hang off the supervisor's hours-long main lap, not
   the 5-minute keeper). Confirm the fix is live by checking whether the
   `wiki_source-page_text-section` label appears in the silence ledger *without* a matching
   drop in pages recovered. The old `wiki_source.py:301` label ran 1,700–3,200 URLErrors per
   foreman round; the new label should show similar volume but no longer cost the whole page.
4. **Two spine assignments moved to UNASSIGNED** (`Sword Coast Adventurer's Guide`, `Who Framed
   Roger Rabbit (…)`). They will now appear in `output/index/unassigned_sources.md`. **These
   need the owner's real Collection/Set assignment** — Hard Rule 2 work, not a code fix.

## 1. Human decisions needed (owner)

5. **The AUTO kill remedy going live** (item 0.1) — the owner should know a previously inert
   destructive remedy now has teeth. Keep, or move `kill_stalled_job` to the OWNER lane?
6. **[m12] `thread_integrity.py`'s asymmetric/dangling detection is structurally unreachable** —
   `implied_threads()` builds its pair map symmetrically, so ASYMMETRIC-LAWFUL/-SUSPECT and
   DANGLING can never be reported. Is the module meant to compare implied threads against a
   separately-recorded DIRECTED thread graph it currently isn't given? Unchanged from run #2.
7. **[m13] `pipeline.py phase_synthesis`'s 14-entity ceiling sample** can clamp a whole source
   to a lesser band if the true strongest entity isn't sampled. Raise, re-rank, or accept.
8. **[m16] `weave.py`'s `shared_sample` (8, sliced to 6)** — diagnostic evidence, not
   reader-facing content, but Hard Rule 0's text doesn't carve out diagnostics. Rule on scope.
   **Related, same question:** `dashboard.py`'s `/api/state` caps its `findings` list to 12 —
   a returned data structure, but on a live-monitoring endpoint feeding an HTML panel. One
   ruling should settle both.
9. **dandwiki.com (BUGS M1)** — browser-UA HTML reader vs. owner-supplied. Politeness/ToS call,
   unchanged since run #1. Note `health --preflight` still reports its cache all-empty; that is
   this decision, not a new fault.
10. **Permanently hostless roll entries** (Clockwork Angels, Twilight Imperium, HAWX, …) — stay
    on the roll as owner-supplied-text candidates, or come off? Unchanged since run #1.
11. **Paid burst lane** — 500-call cap stands, counter in `state/PAID_BURST.json`. Raise, keep,
    or retire?
12. **Is the local model rung actually available?** Run #3's `local_agent.py` got HTTP 503 with
    a healthy daemon and a loaded model; run #2's `overwatch` hit the same window. If Ollama is
    reliably contended out by the read/roll workers, rung (b) of the delegation ladder is
    theoretical and the framework should say so.

## 2. Open bugs, by severity (see BUGS.md for full detail)

Medium surgery — do in a quiet window, own pass:
13. **[m6] `pipeline.py`'s 9 remaining raw JSON writes** (cosmology/history/shelve/weave/write
    phases) — route through `pipeline._landed`, and fix `phase_history`'s `TIERS.json` read
    handler so a corrupt file isn't misdiagnosed as "phase 5 hasn't run". **Now the largest
    open item of its class**; run #3 closed the `ingest_doc` and `write_record` instances.
14. **[m10] `build_terminal.py` HTML/JS escaping** — `html.escape()` every interpolated
    catalogue string (`render.py`'s `containment_svg()` is the correct pattern in-repo), and
    guard the `<script>` splice against a literal `</script>` in `NAVTREE.json`. Note run #3
    touched this file (m8/m9) but deliberately did not widen into the escaping pass.
15. **[m18] `foreman.py`'s three non-atomic shared-state writes** — `POOL_PROOF.json`,
    `FOREMAN.json`, `failures.json`/`failures_archive.json`. Reported by run #3's ops audit but
    **not independently re-verified** — confirm each against source first.
16. **[m7] `handbuilt.py`'s artifact write** — route through `silence.replace_retry`.
17. **[m14] `phase_entrypass` can mark an entry permanently topicless** — `topic` fails its
    enum check silently with no `"unassayed"`-style fallback, yet `catalogued=True` is still
    set. **Run #3's `batch_settled` fix does NOT rescue this**: the entry carries `catalogued`,
    so the reopen gate correctly skips it. Needs its own fallback, in the same shape
    `magnitude` already has.
18. **[m15] `endpoint.py fetch_raw` treats every HTTPError as "page doesn't exist"** — 403/429/
    500 misfiled as permanent absence. Same failure family as the [m4] fix run #3 just landed,
    and a good next target for the same reason: a transient read as genuine silence.

Small / good first pass (all reported, none independently re-verified — check before fixing):
19. **[m19]** `standards.report()` sorts work orders alphabetically, not by rank.
20. **[m20]** dead `dupes` loop in `standards.py` (bare `pass`) — confirm vestigial, and note
    deletions need a flagged review cycle.
21. **[m21]** `kill_duplicate_jobs` registered as a bare lambda, so its log line loses its name.
22. **[m22]** `catalog.py`'s docstring documents a `PANSCRIPTUM://…` address form the code
    doesn't implement.

## 3. Surface rotation for the next audit fan-out

Covered so far — do **not** re-read these unless the diff touched them: the round-1
full-codebase audit and the evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces
(derivation/rigor/handbuilt; sweep/endpoint/wiki_source/coverage; build_terminal/weave/
weave_index/navtree/render; pipeline/ledger/thread_integrity); run #3's two (ingest_doc/
manifest_builder/generate/address/catalog; foreman/standards/publish/overnight/dashboard).

**Not yet audited line-by-line** — pick from here: `assay.py`, `magnitude.py`, `chain.py`,
`identity.py`, `cascade_bridge.py` (only partly covered), `compress_store.py`, `module_index.py`,
`hostcheck.py`, `scout.py`, `tuning.py`, `catalogue_web.py`, `silence.py` itself, `health.py`,
`overwatch.py`, `local_agent.py`, `read.py`, `feats.py`.

**A note on agent findings, earned twice this run:** both audits were right about *where* and
partly wrong about *why* — one named the stall detector's job-name mismatch but missed that the
timer could not reach its threshold regardless, which was the bigger half. And two of run #3's
own first-cut fixes regressed real behaviour (`Soul Calibur` fell out of II.A.7; source `DC`
was sent to the Sword Coast record) and were caught only by diffing all 215 roll entries before
and after. **Diff the whole corpus before and after any matching-logic change.** A fix that
looks right on the reported case is not verified until the cases nobody reported are checked.
