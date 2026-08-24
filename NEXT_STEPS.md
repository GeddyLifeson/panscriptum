# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #1 wrote this on 2026-08-23 ~22:00.*

## 1. Carried over / verify-next-run

1. **Verify the first scheduled fire worked** (~:20 past the hour, task
   `panscriptum-maintenance`) — check `state/MAINTENANCE_RUN.json` got written and a run
   entry appended to HANDOFF.md. If the fire never landed, the app may have been closed.
2. **Charter regression result**: `data/CHARTER_REGRESSION.json` — the foreman dispatched
   the first run autonomously at 21:31 into a thin evening pool. If rows are all DEFERRED,
   the standard stays red and the foreman retries; expect a real result after the midnight
   free-tier window. Confirm the `automation reproduces the charter` standard flips.
3. **Marvel completeness row**: a fresh `completeness.py` run was launched ~21:20 (plus the
   new 12h category cache). If the row still reads ~0.4% against 30,207 entries on disk,
   suspect the source-name→record matching in `catalogued_counts()` — that becomes a real
   bug, promote to BUGS.md major.
4. **Dragonlords ingest**: patient miner (60-miss/5h) grinding 252 chunks on the corrected
   catalogue-side writer. Verify `found` in `data/docs/.../ingest_state.json` and the record
   growing past 292 once the pool window rolls.
5. **1,060 reopened Marvel entrypass batches**: confirm the pipeline is re-judging them
   (phase 2 progress in `state/pipeline_auto.log`).

## 2. Proposals (act only after a review look)

6. **Delete `identity.adjudicate()` (src/identity.py:321-367)** — dead code, superseded by
   `chain.adjudicate_mutuals()`; nothing calls it, nothing reads `winner_epoch` (round-2
   audit, verified by repo-wide grep). Guardrail: deletion flagged this run, execute next.
7. **Sweep-level by_axis result caching** — `sweep.py` re-derives `candidates()` over the
   whole 874MB corpus per pass even after the 3× hoist. Proposal: per-(host,entity) cache
   keyed on the evidence file's mtime, same pattern as `chain_harvest_idx`. Medium surgery
   on a hot artery; do it in a quiet window with before/after timings.
8. **`hostcheck._NULL_CACHE` to disk** — minor (1-2 HTTP calls per foreman round).
9. **manifest_builder/address per-entry normalize memo** — verified real but ~milliseconds;
   only worth doing if touching those files anyway.

## 3. Human decisions needed (owner)

10. **dandwiki.com (BUGS M1)**: build an HTML-path reader with a browser UA for its 4
    homebrew sources, or leave them owner-supplied? The API 403s all non-browser clients;
    scraping HTML past that is a politeness/ToS call, not a technical one.
11. **Disk (BUGS M2)**: ~5 GB free on the drive, floor is 10; the project is only ~1 GB of
    it. Clear non-project space or say where the corpus should move.
12. **Permanently hostless roll entries** (Clockwork Angels, Twilight Imperium, HAWX, …):
    rule whether they stay on the roll as owner-supplied-text candidates (ingest_doc now
    exists for exactly that) or come off.
13. **Paid burst lane**: 500-call cap stands, counter in `state/PAID_BURST.json`, spend line
    in FOR_OWNER.md. Raise, keep, or retire?
