# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #5 wrote this on 2026-08-24 ~08:55.*

**Read this first: two of the three things blocking the library are not code.** M3 (fandom
dropping connections at the socket) and M1 (dandwiki 403) are network/politeness states, and
between them they account for the page roll at 52%, reachable-wiki at 90%, and the completeness
audit having nothing to measure. No amount of fixing helps until fandom answers. Check it in one
command before you plan anything (section 1.1). If it is still down, this run's useful work is
audits and owner questions, not repairs.

## 1. Verify first

1. **Is fandom answering yet?** One probe settles it:
   `curl.exe -s -o /dev/null -w "%{http_code} %{time_total}s\n" --max-time 25 -A "Mozilla/5.0" "https://marvel.fandom.com/api.php?action=query&meta=siteinfo&format=json"`
   HTTP 000 after ~20s means still blocked; compare against `en.wikipedia.org` (0.25s when
   healthy) to tell a block from a local network fault. **If it answers**, the first real work is
   letting the completeness audit run: the foreman's `_fandom_reachable()` gate will dispatch it
   on its own, and `COMPLETENESS.json` should refill from `[]` to ~164 rows. Confirm it does —
   the whole run-#5 fix chain is only *proven* when a real measurement lands.
2. **Confirm the completeness standard reads honestly in both states.** Empty file → `UNMEASURED
   -- 0 row(s) ...`; real rows → a genuine percentage. It should never again print `0.0% (0 of
   0)`. Verified this run in the empty state only; the populated state is unverified because
   fandom is down.
3. **`publish.py` now fetch-rebases before pushing** (BUGS M2, fixed by the concurrent session
   in export `fbcbe57` while run #5 was writing its ledger). Run #5's closing push succeeded and
   left local and `origin/main` in sync. Still worth reading `state/publish.log` before assuming
   a run's commits reached GitHub — this is the first cadence with two publishers in it.
4. **[m23] job logs are still truncated on every restart.** It blocked a diagnosis again this run
   — `state/completeness.log` was 0 bytes at exactly the moment it would have explained the wipe.
   Transcribe anything you are diagnosing before the keeper bounces the job.

## 2. Human decisions needed (owner)

5. **[m24] `cascade_bridge.dead_forever`** buries buckets on `no such model` / `needs billing` /
   `bad key`, which its own docstring's "permanent codes only" rule does not cover. Inert today.
   Document those three as permanent, or drop them?
6. **[m25] `scout.sweep`'s `prev[-40:]` run history** — and the same ruling would settle **[m16]**
   (`weave.py`'s `shared_sample`) and `dashboard.py`'s `findings` cap of 12. **One decision,
   three sites: does Hard Rule 0 bind diagnostics and run logs, or only reader-facing listings?**
7. **[m12] `thread_integrity.py`'s asymmetric/dangling detection is structurally unreachable.**
   Is it meant to compare implied threads against a separately-recorded DIRECTED thread graph it
   currently is not given? Not a one-line fix either way.
8. **[m13] `phase_synthesis`'s 14-entity ceiling sample** can clamp a whole source to a lesser
   band if the true strongest entity is not sampled. Raise, re-rank, or accept.
9. **[M1] dandwiki.com** — browser-UA HTML reader vs. owner-supplied. Politeness/ToS call, open
   since run #1. `health --preflight` will keep reporting its cache all-empty until it is
   decided; that FAIL is this decision, not a fault.
10. **Permanently hostless roll entries** (Clockwork Angels, Twilight Imperium, HAWX, …) — stay
    on the roll as owner-supplied-text candidates, or come off?
11. **Paid burst lane** — 500-call cap, counter in `state/PAID_BURST.json`. Raise, keep, retire?
12. **Two spine assignments still land in UNASSIGNED** (`Sword Coast Adventurer's Guide`, `Who
    Framed Roger Rabbit (…)`) — Hard Rule 2 curatorial work, not a code fix.

## 3. Carried operational items

13. **[m1] Marvel completeness row** — cannot be re-measured until fandom answers (M3). The
    byslug-matching suspicion is still unresolved and still untestable.
14. **[m2] 6 roll sources never catalogued, 20 catalogued with no host** — overlaps item 10.
15. **Charter regression** — `data/CHARTER_REGRESSION.json` exists and its writer is now atomic.
    Confirm the `automation reproduces the charter` standard takes a real reading from it rather
    than a vacuous pass. **This is the same shape as the bug run #5 found**: a standard reading a
    file that is not there, or is empty, and reporting a number anyway. Worth an explicit check.
16. **The local model roster changed under us (owner ruling 2026-08-24: GPU-only residency).**
    Only `qwen3:8b` is installed; the 30B MoE is gone; `pick_model.py` now refuses anything that
    cannot sit entirely in VRAM. **Run #4's "30B MoE throughput" watch item is obsolete — deleted
    rather than carried.** Phases are now pool-first (`pipeline.ask_pool_first`, gated on ≥3
    proven-answering buckets), so phase-2 throughput is a *pool* question now, not a GPU one.
17. **Delegation note for the next run:** rung 2 (Ollama) was skipped this run on purpose — one
    8B model, the pipeline mid-phase-2 on it, and the foreman's own model lane reporting "GPU busy
    and no spare pool capacity" on three items. Check that state before routing work to
    `local_agent.py`; contending with the pipeline for the only model is not delegation.

## 4. Surface rotation for the next audit fan-out

Covered, do **not** re-read unless the diff touched them: the round-1 full-codebase audit and
evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces (derivation/rigor/handbuilt;
sweep/endpoint/wiki_source/coverage; build_terminal/weave/weave_index/navtree/render;
pipeline/ledger/thread_integrity); run #3's two (ingest_doc/manifest_builder/generate/address/
catalog; foreman/standards/publish/overnight/dashboard); **run #5's three** (assay/magnitude/
identity; hostcheck/scout/tuning/compress_store; read/feats/estate/worldseed/onomast).

**Not yet audited line-by-line** — pick from here: `chain.py`, `cascade_bridge.py` (only partly
covered), `module_index.py`, `catalogue_web.py`, `silence.py`, `health.py`, `overwatch.py`,
`local_agent.py`, `custodes.py`, `tiers.py`, `sevenfold.py`, `grounding.py`, `address_space.py`,
`profile.py`, `burgs.py`, `tells.py`, `style_audit.py`, `audit.py`, `cleanup.py`, `backfill.py`,
`descending_ladder.py`, `cosmography.py`, `pick_model.py` **(newly rewritten — worth a look)**.

Three findings from run #5's audits were **not** actioned and are worth a second opinion before
anything is done with them: `hostcheck`'s `judgeable` flag is computed and respected by
`standards.py` but ignored by hostcheck's own two consumers (so a product-titled sourcebook gets
tagged "ROSTER FROM ANOTHER FICTION" anyway); `onomast.coin_well_formed`'s fallback skips both
its quality and uniqueness checks (needs 400 consecutive collisions to bite); `feats`'
`_unwrap_templates` miscounts brace nesting on `{{{`.

## 5. Three lessons worth keeping

- **A green check nobody has watched fail is not evidence.** Run #5's first draft of the Assay
  regression asserted two perfectly reasonable relations — and both passed against the *buggy*
  function. The check only became real when the pre-fix code was run against it and produced
  0.01/0.00 where the fix produces 0.06/0.15. Pin arithmetic, then falsify the pin.
- **Measure the alternative before shipping a matching change.** The obvious fix to
  `read._names` (word-boundary tokenisation) was the *wrong* one and would have silently dropped
  265 real matches; only a full-corpus diff surfaced that wiki prose inflects. The corpus is
  1,219 files and the diff takes seconds — there is no excuse for guessing.
- **An empty artifact is not a measurement of emptiness.** This is now the third distinct form of
  the same error (m3's dropped rows, run #5's wiped file, run #5's `0.0% (0 of 0)` standard).
  Any writer of a shared artifact should ask what an empty result means before landing it, and
  any reader should distinguish "no denominator" from "zero".
