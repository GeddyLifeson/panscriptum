# AUDIT batch09 — sweep run54

Auditor read every line of all eight modules in this batch:
`foreman.py` (1992), `overwatch.py` (1101), `completeness.py` (845), `custodes.py` (698),
`address.py` (539), `hosts.py` (396), `catalogue_models.py` (339), `resonance.py` (298).

General note on this batch: all eight modules are unusually heavily self-documented, with a
long visible history of prior fixes cited by order-hash and cross-checked against callers. Most
of the obvious defect shapes this project watches for (checks that cannot fail, substring
verdicts, discarded write verdicts, silent excepts, caps on rosters) have already been found and
fixed in these files, with the fix and the measurement both left in the comment. Findings below
are things I could still verify were wrong; I did not re-litigate anything already marked
fixed-and-explained unless the explanation itself didn't hold up.

---

## src/completeness.py

Read top to bottom, including every helper `audit()`/`work()` calls. Traced `wiki_host`,
`subdomain`, the `shared`/`primary` host-disambiguation block, and `land()`'s three-way verdict.
Cross-checked against `data/WIKI_HOSTS.json` and `data/COMPLETENESS.json` on disk.

### MAJOR — the "primary host" disambiguation can never name a primary for any non-fandom shared host, so every source on one is permanently excluded from coverage
**Where:** src/completeness.py:442-449 (building `primary`), src/completeness.py:651-654 (using it)
**What:** `audit()` builds a `primary` map so that when two sources point at the *same* host,
only the one host actually belongs to may claim it as a denominator:
```python
primary = {}
for src, h in todo:
    sub = subdomain(h) or ""
    key = "".join(ch for ch in str(src).lower() if ch.isalnum())
    if (key and key in sub.replace("-", "")
            and (h not in primary or len(key) > len(primary[h][1]))):
        primary[h] = (src, key)
...
elif shared[host] > 1 and (primary.get(host) or (None, None))[0] != src:
    why = ("shares " + host + " with " + str(shared[host] - 1) + " other source(s) and "
           "is not the primary; denominator belongs to "
           + str((primary.get(host) or ("nobody",))[0]))
```
`subdomain(h)` (line 61-65) returns `None` for any host that is not `*.fandom.com`, so for a
non-fandom host `sub` is always `""`. `key in "".replace("-", "")` is `key in ""`, which is
`False` for every non-empty `key` (and `key` is required to be non-empty by the `if key and ...`
guard). So **`primary[host]` is never assigned for any non-fandom host**, no matter how many or
how few sources share it.
**Why it is wrong:** 28 sources on the live roll share `en.wikipedia.org` and 4 share
`www.dandwiki.com` (verified against `data/WIKI_HOSTS.json`: `{'en.wikipedia.org': 28,
'www.dandwiki.com': 4}`). For every one of them, `shared[host] > 1` is true and
`(primary.get(host) or (None, None))[0]` is always `None`, so `!= src` is always true — every
single one of those 32 sources takes the "shares host … and is not the primary; denominator
belongs to nobody" branch and is marked `unreliable`, forever, regardless of whether the
category probes for that specific source's own Wikipedia category actually found a real,
distinguishing size. This is unlike the fandom case the comment above the loop is written about
("'Marvel' -> 'marvel'" naming its own subdomain): a general encyclopedia host has no
per-franchise subdomain to match against, so the mechanism that is supposed to pick a winner
among genuine collisions instead refuses *everyone* on any shared non-fandom host, every time,
by construction — a check that looks like a disambiguator but can only ever produce one answer.
I reproduced this directly (isolated from the network) by calling the actual `wiki_host`/
`subdomain` functions from the module against a synthetic `todo` list of two distinct sources
sharing `en.wikipedia.org` plus two sharing `marvel.fandom.com`: the fandom pair correctly picks
`Marvel` as primary; the Wikipedia pair assigns no primary to either.
This is currently masked in `data/COMPLETENESS.json` because `en.wikipedia.org` is presently
recorded as unreachable at audit time (every affected row's `unreliable` field currently reads
"host unreachable…", not "is not the primary…") — so the bug is latent rather than visibly
firing today, but it will fire on the next audit round where en.wikipedia.org answers, silently
converting real per-source Wikipedia coverage numbers into permanent "unreliable, denominator
belongs to nobody" rows for all 28 (Wikipedia) + 4 (dandwiki) sources.
**Confidence:** verified by reading the full call chain, checking `subdomain()`'s actual return
value for non-fandom hosts, counting real shared-host cardinalities in `data/WIKI_HOSTS.json`,
and reproducing the `primary`-building loop standalone against both a fandom and a non-fandom
synthetic case with the module's own functions.

### Clean otherwise
Read `_load`/`_cs_load`/`_cs_put` caching, `category_size_probe`/`category_size_probe_host`,
`host_reachable`'s three-mode (DEAD/RAW/normal) branching, `work()`'s full dispatch (sentinel
host, unreachable host, no-denominator, genuine-vs-unmeasured absence, `cov > 1.0`), and
`land()`'s three-outcome contract (`True`/`False`/`SKIPPED_ONLY`) plus its shrink-floor and
write-denial guards. All of these already carry a documented prior fix and I could not find a
new defect in any of them — verified the arithmetic and control flow match the docstrings in
each case.

---

## src/hosts.py

Read in full, including `_load`'s absent-vs-corrupt distinction, `add()`'s three-valued return,
and `discover()`'s per-source candidate scoring loop (grounded/speculative split, `KEEP`
verdicts, `MIN_HITS_SECONDARY`/`MIN_ABOUT_SECONDARY` substance test) and its three distinguished
negative outcomes (`not_probed`, `probe_failed`, thin-roster). No new defect found — every
branch's counting and reporting matches its own docstring, and the counts (`withheld_total`,
`lost`, `not_probed`, `probe_failed`) are each accumulated and printed rather than dropped.

---

## src/catalogue_models.py

Read in full: `ask_provider`'s four-outcome contract (`LISTED`/`EMPTY_LIST`/`UNREACHABLE`/
`UNCONFIGURED`), the `/v1` path-doubling guard, and `sweep()`'s `live`/`stale`/`unverified`
accounting including the `LAST_WRITE_LANDED` tri-state global. Checked that `EMPTY_LIST`
providers are counted in both `live` and `verified` consistently (they are, at lines 208-209 and
274). Checked that a positive-only `axis_emphasis`-style reweight can't silently zero the
provider table the way `assay.py`'s `_check_weights` describes — not applicable here, this
module has no such interaction. No defect found.

---

## src/resonance.py

Read in full, including the module's own header which already states (as of 2026-08-28) that
`hodge_decompose` and `resonance_strength` have zero production callers and that
`incomparability_rate`/`dominates` are exercised only by `verify_math.py`. I re-confirmed this
is still true by grepping `src/` for callers of all four names — the only hits outside this file
are `verify_math.py` (for `incomparability_rate`) and this module's own `main()` demo. This is
not a new finding; it's the module's own documented and still-accurate state, and it means the
Threnody curl-veto and Lumen staleness-widening wired up in `custodes.convene()` still cannot
fire from any real call site (`anchors.py` passes neither `eta` nor `distance`/`years_since`),
exactly as `custodes.py`'s own docstring says.

### QUESTION — `prior_share` defaults to 1.0 on a zero-variance reading
**Where:** src/resonance.py is not involved here; this belongs to custodes.py below, moved up
by mistake — see custodes.py entry.

Checked `hodge_decompose`'s Gauss-Seidel convergence loop and gauge-fix arithmetic by hand
against its own docstring's STAR/BIPARTITE/PATH4 worked examples; the update rule
(`theta[n] = sum(theta[b]+f for b,f in nbrs[n]) / len(nbrs[n])`, in place per node, then
mean-centered) matches Gauss-Seidel as described and the convergence test (`max` per-node shift
against `tol`, not the mean) is the correct choice for the reason given. No defect found.

---

## src/custodes.py

Read in full: the `CUSTODES` table (all ten Daseins/tilts/emphases), `_custos_reading`'s private
per-call weight table (confirmed it does not mutate `A.WEIGHTS` globally), `staleness_widening`,
`_transit_widening`'s per-dispersive-Custos accounting, `convene()`'s attendance block and
Threnody veto, `dof_coverage()`, and `table_faults()`.

Checked specifically whether `_custos_reading`'s second call to `A.assay(...)` (under
`axis_emphasis`) could return `decimal: None` after the first call already passed the
`if base.get("decimal") is None: return None` guard — traced into `src/assay.py`'s `assay()`:
the reweighted table `w` is built over exactly the same keys as `A.WEIGHTS`
(`{k: v * emph.get(k, 1.0) for k, v in A.WEIGHTS.items()}`), so the "no axis scored" `None`
branch (`assay.py`, `if not used:`) cannot newly trigger, and since every `axis_emphasis` value
in the table is positive, `_check_weights`'s negative-weight refusal and the `wsum <= 0.0`
`AssayIntegrityError` (which would raise loudly, not return `None`) are the only other ways
`assay()` can fail — so this path is safe, not a live bug. Confirmed by reading `assay.py`'s
Layer-1 checks around the `wsum` computation.

### QUESTION — `prior_share` defaults to 1.0 when `total_var` is exactly 0
**Where:** src/custodes.py:508-509
**What:**
```python
prior_share = (prior_var / total_var) if total_var > 0 else 1.0
```
**Why it might be wrong:** if all ten Custodes' readings happen to coincide exactly (zero
dispersion in both the raw and perfect-evidence readings), this reports "100% prior divergence,
0% attestation floor" rather than "no disagreement measured, share undefined." I could not
construct a live input where `total_var` is exactly 0 given the table's distinct tilts — it
looks structurally very hard to hit with real evidence — so I am filing this as a question, not
a fix: is the `else 1.0` default intentional (treat the degenerate zero-disagreement case as
"whatever the interval is, it's all irreducible prior" for downstream printing), or should it
read as unmeasured?
**Confidence:** read the code and the surrounding docstring; did not find or construct a real
input that reaches the `else` branch, so this is a code-shape question rather than a
demonstrated live defect.

Everything else in `convene()` (the `half = max(1.96*sd, *(abs(v-consensus)...))` band-covers-
every-reading construction, the `covers_every_reading` guarantee the file itself already flags
as "not a check," the abstention bookkeeping for `staleness`/`comparability`, and
`table_faults()`'s zero-tilt/nonzero-sensitivity detector) matches its docstring and I found no
new defect.

---

## src/address.py

Read in full: `spine_code_for`'s four-stage fallback (exact code, normalized-equality, worded
containment with the opens/closes "placed-like-a-title" check, and the token-overlap fallback),
`slugify`, `chapter_label_for`/`chapter_slug`, `build_address` (already marked dead-and-stale by
its own docstring, kept per owner ruling), `placeholder_shelfmark`, `recipe_hash`, and the
promotion ladder (`tier_for`/`tier_rank`/`promote`, promotion-only-never-demotion). Traced the
`_index_name_is_placed_like_a_title` remainder logic by hand against its own worked examples
("Alien Predator Doom Crossover", "Halo Fan Documentary About Nothing"). No new defect found —
every one of the several already-documented false-positive fixes (raw-letter containment,
first-in-file-order, single-token mid-sentence matches, opening/closing without checking the
remainder) is correctly closed by the code as it stands today.

---

## src/overwatch.py

Read in full: the ledger's `_NotALedger`/damaged-vs-absent load path, `save()`'s
merge-before-write (`_reconcile_with_disk`/`_merge_ledgers`), `_progress`/`_finished_at`'s
tie-break scale fix, `structure()`'s import/reconcile/estate tiers and their `error`/
`estate_error` "unknown, not zero" reporting, `_ask`'s local-first-never-local-only budget
(`_LOCAL_BUSY`/`CLOUD_BUDGET`, reset per round in `round_once`), `review()`'s `complete` flag and
its effect on `rotation()`'s stale queue, `verify_open()`'s yielded-vs-checked accounting, and
`write_report()`'s uncapped findings list. Checked `main()`'s escalation-chain fail-closed gate
and the `codewatch.claim_singleton`/`exit_if_stale` loop-mode guarding. No new defect found;
every one of the many documented prior fixes checks out against the code as it reads today.

---

## src/foreman.py

Read in full, all ~2000 lines, including every AUTO remedy (`clear_learned_caps`,
`reprove_pool`, `adopt_hosts`, `scout_hostless`, `rerun_roll`, `triage_swallowed`,
`recatalogue_models`, `refresh_coverage`, `restart_reader`, `kill_stalled_job`,
`kill_duplicate_jobs`, `_fandom_reachable`, `_catalogue_batch`/`run_catalogue_gap`,
`run_character_sweep`, `run_completeness_audit`, `run_charter_regression`, `restart_ollama`),
the `REMEDIES` table and its `.always` handling in `round_once`, the whole MODEL-lane patch
pipeline (`_function_source`'s qualified-symbol resolution, `_literals`/`regex_touched`,
`lines_changed`, `_contracts_pass`, `_checks_pass`'s four gates, `attempt_patch`'s local-then-
cloud model call and backup/revert), `_retire`, `_pool_has_room`, `owner_queue`, `round_once`,
and `main()`'s escalation gate and loop.

Specifically traced:
- `_catalogue_batch()`'s rotation (`order` sort key, `rate` computation, `frags`/`unnameable`
  disambiguation, `seen`-stamped-before-work) end to end against its own docstring's claims
  about Hard Rule 0 and rotation fairness — matches.
- `round_once`'s `if did and not getattr(fn, "always", False): ... break` logic for the
  `[run_catalogue_gap, run_completeness_audit]` and `[reprove_pool, restart_reader]` remedy
  pairs — confirmed the `always`-marked remedy still runs even when an earlier remedy in the
  same list succeeds and would otherwise short-circuit the list via `break`.
- `attempt_patch`'s backup/verify/revert path, including the double-failure case where the
  revert copy itself fails (reports `"reverted": False` with the backup path rather than
  silently claiming success).

No new defect found. This module's own comment history already documents an unusually large
number of previously-fixed instances of exactly the fault classes this sweep looks for
(substring verdicts standing in for counts, discarded write verdicts, checks that cannot fail,
loose process-line matching), each with a measurement of the prior behaviour and a citation of
its cost; I could not find a further occurrence.

---

## Summary of findings

- **1 MAJOR**: `src/completeness.py:442-449` / `:651-654` — the primary-host disambiguation
  structurally cannot name a primary for any non-fandom shared host, so all 28
  `en.wikipedia.org`-hosted sources and all 4 `www.dandwiki.com`-hosted sources are permanently
  excluded from ever getting a real coverage measurement once those hosts are reachable again.
  Currently latent (masked by `en.wikipedia.org` reading "unreachable" in the current audit
  snapshot).
- **0 MINOR**
- **2 QUESTION** (not fixes): `src/custodes.py:508-509`'s `prior_share = 1.0` zero-variance
  default; and the already-open, module-documented fact (re-verified here) that
  `resonance.hodge_decompose`/`resonance_strength` still have no production caller.
