# sweep46 — batch 06

**Modules:** `cascade_bridge.py` (2,053) · `chain.py` (858) · `weave.py` (699) · `zfighters.py` (536) ·
`address.py` (477) · `hosts.py` (396) · `runguard.py` (303) · `scale_theories.py` (174) ·
`module_index.py` (163). **5,659 lines, all of them read**, end to end, no sampling.

Read-and-report only. No file in `src/` was modified. `drill.py`, `mutate.py`, `allsweep.py` and
`publish.py` were not run; no live crawl or fetch was made; no cloud provider was called.

---

## Filed

### 1. `bfafac3e1c5e` — LOCAL / MINOR — `pipeline.phase_weave()` does not catch the new weave exceptions

`weave.py` was changed today (order `12aca83cab86`): `components()` now refuses a threshold `<= 0`
(raises `ValueError`) and `null_threshold_surprisal()`/`null_threshold()` raise
`NullThresholdUnmeasured` instead of returning `0.0` when the permutation null cannot be measured
(empty corpus after mechanic-filtering, or non-positive `trials`). `weave.py`'s own `main()`
(`weave.py:596-613`) wraps both calls and prints a clean `REFUSED: ...` message on either exception.

`pipeline.phase_weave()` (`pipeline.py:2881-2892`) calls the identical pair —
`thr = W.null_threshold_surprisal(occ, sur, sources, trials=12)` at `:2889`, then
`groups = W.components(sources, w, thr)` at `:2892` — with no try/except around either call.
This is not a fabrication risk: `pipeline.main()`'s phase loop already wraps every phase function in
a blanket `except Exception:` that logs `PHASE CRASHED`, saves state, and returns without marking
the phase complete, so the run does fail closed and no stale/partial artifact is written. The gap is
that the anticipated, already-designed refusal message (the one `weave.py`'s CLI gives for exactly
this condition) never appears — an operator sees a generic crash trace instead of the specific
"permutation threshold could not be measured" explanation the rest of the module was built to give.

Checked every other caller of these two functions across `src/`: `tiers.chart()`/`tiers._graph()`
are the only other callers of `weave.components()`, and they always pass the fixed positive constant
`MULTIVERSE_THRESHOLD = 102.3` — never a measured threshold — so `tiers.py` never calls
`null_threshold_surprisal()` at all and is not exposed to either new exception. `drill.py`'s own net
(`weave_null_threshold_surprisal_refuses_unmeasured`, `drill.py:13148-13211`) tests the raise
directly and correctly. `phase_weave` is the one real caller left unguarded.

### 2. `10dbef1a47d2` — LOCAL / MINOR — `cascade_bridge.record_unrecognised()`'s dedup key folds the error tail

`record_unrecognised()` (`cascade_bridge.py:871-997`) keys its ledger row on
`bucket + "|" + text[:80].lower()` (`:899`), where `text` is the provider's error string already
capped to 300 characters (`:888`). Every call that hashes to the same key overwrites `r["error"]`
with the newest text (`:950`) and only bumps `count` (`:952`) — it keeps no trace of whatever
DIFFERENT text an earlier occurrence carried past the shared 80-character prefix. Two genuinely
distinct provider complaints sharing a long common preamble ("Model returned an unexpected response
format: ...", "HTTP error from provider X: ...") before diverging into the actual disposition
collapse into one row, and only the last-arrived text survives — the count still reflects both
occurrences, but a second, different, investigatable cause is silently discarded with nothing on
disk saying so.

Same shape as the bug chain.py's `harvest()` was fixed for under m37 (`sentence[:120]` deciding
which contests exist) and the same principle the file's own nearby comment states without quite
covering this case: "THE KEY FOLDS; THE TEXT DOES NOT... text is stored verbatim" addresses only the
case-folding fix, not this 80-character truncation, which is exactly as capable of silently
overwriting a distinct error as lowercasing was.

Filed MINOR rather than MAJOR: this is a diagnostic ledger (`POOL_UNRECOGNISED.json`), not the
primary corpus, and requires two distinct causes on one bucket sharing an 80-char prefix — plausible,
not guaranteed common.

---

## Already open — corroborated, not refiled

Every order below was checked against the CURRENT source (not assumed from its filing text) and is
still accurate. Line numbers noted where they have drifted since filing.

* **`07258ace3a09`** — `address.spine_code_for()`'s crossover/anthology exception. Re-ran all three
  of the order's own reproductions against live code: `"Alien Predator Doom Crossover"` and
  `"Doom Marines vs Aliens Anthology"` now correctly return `UNASSIGNED` (the shift-note fix has
  landed); `"Halo Fan Documentary About Nothing"` still returns `II.F.4`, exactly as the order's
  latest note says. Still open on the third case, unchanged.
* **`2c8e55f8f3f7`** — `address.tier_rank` returns 0 (same as `'volume'`) for an unrecognised tier.
  Confirmed at current `address.py:448-451`.
* **`4e92365b54f6`** — `address.build_address()` has no caller anywhere in `src/` outside its own
  `__main__` demo. Re-grepped; still true (current def at `address.py:363`).
* **`3fb312a72435`** — `hosts.py` has no caller anywhere in `src/`. Re-grepped, including the two
  false-positive hits (`chain.py:377`'s local variable `hosts.add(...)`,
  `workorders.py:1126`'s `seen_hosts.add(...)`) that make a plain grep overstate it; neither is a
  real import. Still zero real callers.
* **`372d4a8c8d46`**, **`70f66fbd98aa`** — the two `runguard.py` owner questions (the CAS's inherent
  digest/write window; `read()`/`holder_is_live()` treating absent and corrupt the same way).
  Confirmed at current lines (`read()` `:52-69`, `holder_is_live()` `:139-151`); nothing in this
  read disputes either.
* **`01695fe3ef26`**, **`a78d5cd748b2`** — `scale_theories.py` has no real importer anywhere in
  `src/` (the four files a plain grep matches — `descending_ladder.py`, `drill.py`, `liveness.py`,
  `tempus.py` — all reference it only in comments), and its five physics constants are confirmed
  still dead and still deliberately un-deleted for the reasons the order already gives (no
  canonical-constants-home precedent in this codebase; deleting five constants from a module whose
  own retention is the open question doesn't resolve anything).
* **`2239a87c57f5`**, **`9fb8a6b10c1f`**, **`d3acbb793ef2`** — the three standing `cascade_bridge.py`
  OWNER questions (transient-throttle classification not benching a bucket with a real retry-after;
  every cloud provider spent/dead on the day measured; the pin path at current `:1336-1361` still
  carries no `LOCAL_PREFIX` exclusion the non-pin claim loop has, and `try_disabled()`'s gate at
  current `:1971-1977` still admits a disabled local Ollama entry the same way). Re-verified against
  today's source; all three still stand, line numbers shifted by roughly +7 to +20 since filing
  (the file has grown from 1,270 lines, per CLAUDE.md's figure, to 2,053).
* **`af47010df391`** — the Groq size-refusal misclassified as a transient throttle
  (`_TRANSIENT_WORDS` catching "rate_limit_exceeded"/"try again" on a permanent per-request
  output-size cap). Per this batch's brief, this is the owner's design decision and was not
  re-litigated or touched; confirmed still present and unchanged at current `:549-557`.
* **`e8466cd6ed14`** — `chain.main()` reports success over a `CHAIN.json` write that may not have
  landed. `write_result()` (`chain.py:101-153`) returns `out` unconditionally even when
  `silence.write_json` is denied (`:149-152` only notes and prints to stderr — the return value is
  unaffected), and none of its three call sites (`:809`, `:833`, `:852`) check the write's own
  success before printing `"-> {OUT}"`. Confirmed unchanged; only the line numbers moved since the
  order was filed (chain.py grew from 837 to 858 lines this run — mostly comment expansion, not new
  bugs).
* **`423e35500033`** — `adjudicate_mutuals.side_epoch`'s `for row in (prov.get(e) or [{}])`
  (current `chain.py:668`). Confirmed structurally unreachable on the one path that calls it
  (`main()`'s `edges, unmatched, prov = extract(...)` immediately feeding
  `adjudicate_mutuals(edges, prov)` — every key in `edges` has at least one `prov` entry by
  construction of `extract()`'s own `local`/`prov[e].append(src)` pairing).

## Checked and judged deliberate — not filed

* **`address.py`'s `_index_name_is_placed_like_a_title`** — the `remainder` "does another catalogued
  work's name appear" check (`address.py:196-212`) uses plain substring containment (`w_other in
  remainder`), not a word-boundary test, for the "does this name a genuine crossover" question. A
  short catalogued index entry could in principle appear as a substring of an unrelated word inside
  the remainder and cause a legitimate single-franchise title to be rejected into `UNASSIGNED`
  rather than correctly matched. Not filed: the failure direction is the SAFE one Hard Rule 2 asks
  for (an over-cautious `UNASSIGNED` rather than an invented address), and the function already
  exists specifically to trade false negatives for zero false positives on this exact question.
* **`cascade_bridge.py`'s diagnostic-string truncations to 300/200/80 characters**
  (`provider_error()` `:839`, `box["error"]` at `:1544/1550/1563`, `served["error"]` `:1725`,
  `prove()`'s `reason[:300]` `:1944`) — considered against Hard Rule 0's caps concern, since these
  feed the same classifiers (`permanent_refusal`, `named_transient`, `client_rejection`) the file's
  own history shows are sensitive to exactly which words survive. Not filed as a defect: provider
  disposition markers (`HTTP 401`, `insufficient balance`, the throttle vocabulary) are measured in
  this file's own comments as arriving near the START of a provider's message, which a tail-truncate
  preserves, and 300 characters comfortably covers every quoted provider string in the file's own
  extensive commentary (the longest, Groq's OTPM refusal quoted under `af47010df391`, runs to about
  320 and is a single case already flagged under that open order for an unrelated reason). The one
  case with a real, novel, previously-unexamined failure mode from a truncated identity — the
  `record_unrecognised` KEY at `[:80]` — is filed above (`10dbef1a47d2`); the longer 200/300-char
  diagnostic-text caps are display/classification budgets, not identity truncations, and are judged
  proportionate.
* **`zfighters.py`** — nothing filed. The roster is entirely hand-authored narrative data (14
  fighters plus Son Goku carried in from `data/REFERENCE_ASSAYS_PRESENCE.json`); `main()` already
  reports an incomplete roster loudly (`:441-451`) rather than silently proceeding without Goku, the
  file write is gated on `silence.write_json`'s own verdict (`:524-529`, not assumed), and the
  `--full` worksheet print wraps rather than truncates every cited sentence (`:502-514`). No console
  cap, no fabricated score, no silent write failure.
* **`hosts.py`, `runguard.py`, `module_index.py`, `scale_theories.py`** — read end to end; no new
  finding beyond the corroborations above. All four fail closed on every I/O path checked (`_load`
  distinguishing absent from corrupt in `hosts.py`; the compare-and-swap in `runguard._land_claim`;
  `module_index.main()`'s exit code carrying both the stale-group-name and the denied-write
  verdicts; `scale_theories.surviving_theory()` raising rather than returning a plausible answer
  when the `THEORIES` table is edited into zero or two survivors).
* **`weave.py`** — beyond the `pipeline.phase_weave` gap filed above, every predicate and writer in
  the module was re-read against the current source. `components()`'s new `threshold <= 0` refusal
  and both `null_threshold*` functions' `NullThresholdUnmeasured` are each caught, by name, in
  `weave.main()` (`:596-613`); the three-file `--write` path already reports per-file DENIED writes
  rather than a single unconditional success line (`:649-693`, from the run #36 sweep). Nothing new.
