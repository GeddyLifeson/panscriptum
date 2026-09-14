# SWEEP 58 — BATCH 08 AUDIT

Modules read in full (line counts as read):

| module | lines |
|---|---|
| src/cascade_bridge.py | 2317 |
| src/overwatch.py | 1123 |
| src/wiki_source.py | 800 |
| src/runguard.py | 655 |
| src/backfill.py | 474 |
| src/recover_folder_records.py | 379 |
| src/citecheck.py | 349 |
| src/audit.py | 271 |
| src/compress_store.py | 149 |

Open-queue check done first via `workorders.open_orders()` (98 open orders read, first 300
chars of `what` each). Findings below are cross-referenced against that queue.

None of these nine modules are in this shift's rewrite list (drill.py, verify_math.py,
overnight.py, chain.py, foreman.py, pipeline.py, health.py, onomast.py, withdraw_chapters.py,
sweep_plan.py, canon_backup.py, codewatch.py, rosetta.py, burgs.py, tells.py, custodes.py,
publish.py, runguard.py, binding_health.py, wiki_source.py, weave.py, coverage.py,
secondopinion.py, ledger_guard.py, whoruns.py, events.py, cleanup.py, workorders.py, roll.py,
citecheck.py, catalogue_web.py, tiers.py, catalogue_models.py, feats_index.py, completeness.py,
scout.py, entity_match.py, threads.py) EXCEPT runguard.py, wiki_source.py and citecheck.py,
which is why this shift's brief singled those three out for hard scrutiny. That scrutiny is
below, along with a full read of the other six.

---

## src/runguard.py (655 lines) — the overlap guard, audited hard per the brief

**Nothing found.** This is a careful re-audit of the new per-claim-token mechanism
(`claim()`'s `token_path=`/`print_token=`, `token_matches()`'s `hmac.compare_digest`), verified
line-by-line against source and against `publish.py`'s consumer of it:

- `claim()` never writes the raw token to the guard record — only `TOKEN_DIGEST_KEY:
  _token_digest(token)` (sha256 hex) goes into `rec`. Confirmed by reading `claim()`'s full
  body (:401-496): the local `token` variable is only ever passed to `_deliver_token`, never to
  `rec`.
- `token_matches()` (:66-83) returns False for a record with no digest and for an empty token
  before ever calling `hmac.compare_digest`, so there is no way to force a match with an empty
  string.
- The digest-before-read ordering in `claim()`/`beat()`/`release()` (`expected =
  silence.digest_of(path)` taken before `read_verdict`/`read`) is correct, and I traced why: the
  actual safety property is enforced by `silence.replace_if_unchanged`'s compare-and-swap at
  write time (re-digests immediately before each `os.replace` attempt, per `silence.py:624-719`,
  read to confirm), so a competitor landing in the gap always causes the write to fail-closed
  regardless of which order the digest/read happen in for `claim()` specifically. Where the
  order genuinely matters is exactly the race `verify_math.py:11298` ("order e0c7891274ea")
  already drives as a live test (agentA claims, reads its own record and a stale digest, agentB
  claims into the gap, agentA's `_land_claim` with the stale digest is asserted to fail and
  agentB's claim to survive) — I read that test and it matches the code's own behaviour.
- One design observation, filed as a **QUESTION**, not a defect: `beat()` and `release()`
  authenticate ownership by `rec.get("agent") == agent` (a plaintext string comparison), not by
  the per-claim token. The token is deliberately scoped by `claim()`'s own docstring to the one
  caller that needs unforgeable proof of holdership (`publish.py`'s one-shot `--push` check
  against a *live* maintenance shift) — widening it to `beat()`/`release()` was explicitly
  rejected in-file as unnecessary for their existing callers (`drill.py`'s probes,
  `verify_math.py`'s self-tests all unpack the unchanged `(ok, reason)` pair). Since this is a
  single-user machine and the docstring itself frames the token as solving a different problem
  (a plaintext file readable by any local process pretending to be a named agent to a *remote*
  verifier), I could not demonstrate a concrete bad outcome from `beat()`/`release()` staying
  name-only, so this is a QUESTION for the record rather than a DEFECT.

Checked and confirmed correct: `_land_claim`'s temp-file naming (pid+thread), `holder_is_live`'s
positive-evidence-only pid/start-time arm, `guard_fault`'s report-only (never-enforce) contract,
and the CLI (`--claim` always `print_token=True`, library callers never pass it).

## src/wiki_source.py (800 lines) — `rank_by_size` audited hard per the brief

**KNOWN e7143aba1e9a — no longer accurate, both findings fixed this shift.**
`category_floor_report()` now has a caller: `catalogue_web.py:774` (`floor_rows =
ws.category_floor_report()`, printed per wiki after the catalogue pass — confirmed by reading
that call site). And `rank_by_size`'s `fetch()` now raises on transport failure instead of
returning `{}` (confirmed at :742-748: `except Exception: silence.note(...); raise`), matching
`all_categories`/`category_members`/`extracts`'s sibling raises under order de0681cb9edc — this
is exactly the brief's "fetch now raises" callout. Both of order e7143aba1e9a's findings are
resolved; it should be closed.

**DEFECT MAJOR — `rank_by_size`'s new raise is uncaught inside `catalogue_composite`'s
per-category loop, turning one category's transient network failure into loss of the whole
composite source's already-gathered entries.**
`src/catalogue_web.py:274-288`, inside `catalogue_composite()`:
```python
for c in cats:
    try:
        raw_titles = ws.category_members(sub, c, limit=None)
    except Exception:
        silence.note("catalogue_web.py:composite-category-members")
        failed_cats.append(f"{sub}:{c}")
        continue
    ...
    titles = ws.clean_titles(raw_titles)
    if len(titles) > 40:
        titles = ws.rank_by_size(sub, titles, top=None)   # rank, never truncate
    ...
```
The `try/except` at line 275 wraps only `category_members` (line 276); `rank_by_size` at line
288 sits *outside* it, at the same indentation as the `try`, not inside it. Before this shift,
`rank_by_size`'s inner `fetch()` swallowed a transport failure and returned `{}}` (the exact
mis-ranking order e7143aba1e9a's finding #2 identified and this shift correctly fixed by making
it raise). Now that it raises, a transient network failure during the ranking step of *one*
category on *one* sub-wiki of a composite source (e.g. `COMPOSITE_SOURCES["major fantasy
pantheons"]`, which spans marvel/godofwar/elderscrolls/finalfantasy/zelda/riordan/genshin-
impact/smite/warhammerfantasy/hades/shuumatsunovalkyrie/saintseiya/witcher) propagates out of
`catalogue_composite()` uncaught, discarding every entry already accumulated in `entries` from
categories/sub-wikis processed earlier in the same `spec` loop. It is caught one level up, in
`catalogue_web.py`'s `_one()` (`try: record, note = catalogue(name) except Exception: ...
record, note = None, ...`), so the process does not crash — but the *entire* composite source is
then reported "SKIPPED" and `tally['failed'] += 1`, losing all its work for this pass, where the
surrounding code's own design (the `failed_cats` list, the per-category try/except) clearly
intends a single category's failure to cost only that category. `category_members`'s failures
three lines above get exactly that graceful degradation; `rank_by_size`'s (only) do not.
Concretely: `category_members(sub, c)` succeeds, `len(titles) > 40`, `rank_by_size`'s `fetch()`
exhausts `_get`'s retries on one batch (timeout/429/503) and raises — the whole composite
source's catalogue attempt for this run is discarded, including any sub-wikis processed before
the failing one. `catalogue()`'s own single-wiki path (`catalogue_web.py:482`, also unwrapped)
is fine as-is because there "the source" genuinely is the one wiki being catalogued — but
`catalogue_composite`'s per-category contract says otherwise, and its own `rank_by_size` call
site breaks that contract.
**Remedy:** wrap the `rank_by_size` call at `catalogue_web.py:288` in the same
try/except shape as `category_members` just above it — on failure, append to `failed_cats` and
either skip this category's texts or fall back to the unranked `titles` (Hard Rule 0 forbids
truncating, not skipping ranking), consistent with the loop's existing per-category
fault-tolerance.

Everything else read clean: `_get`'s retry/backoff, `resolve_wiki`'s hosts-file-first resolution
and its non-fandom-known-host short-circuit, `verify_wiki_matches`, `all_categories`'s
uncapped/raising walk and its `(subdomain, min_pages, hard_stop)` cache key, `find_categories`'s
uncapped floor-and-probe merge, `page_text`/`page_texts`'s exhaust-all-sections-before-""
contract, `category_members`'s raise, `clean_titles`'s O(n) dedup.

## src/citecheck.py (349 lines) — `citations_in_text` audited per the brief

**Nothing found.** The new `citations_in_text(text, src_dir=None, include_unresolved=False,
skipped=None)` (:187-224) is exactly what its docstring claims: the same `CITATION` regex,
`_classify` resolver, `_PLACEHOLDERS` set and (now module-level, per order dc9ffadae819)
`_in_tree_lead` helper that `stale_citations` uses, applied to an arbitrary string instead of a
file's lines. I traced its one real caller, `workorders.py`'s `--check-citations` (:2143-2168):
it scans every open order's `what`/`where`/`evidence` text, is read-only (never imports
`resolve`/`_mutate`), and is uncapped. `drill.py:18703-18721` carries a live net asserting it
catches a synthetic `t.py:5` PAST_EOF citation and passes a clean one — read and consistent with
`_classify`'s behaviour. The one structural difference from `stale_citations` (no `citing` /
`target_name == base` self-citation check) is correct and harmless: `_self_citation_ok` always
returns False today regardless, and text passed to `citations_in_text` has no "citing file" of
its own to compare against.

## src/backfill.py (474 lines)

**KNOWN fe99e57e1993 — partially fixed; the `backfill.py` citation is resolved, the order's
other sites (catalogue_web.py, cleanup.py, weave.py, tiers.py, policy.py, completeness.py,
repass_bands.py, overnight.py) were not read this batch.** The order cites `src/backfill.py:364`
for an unmarked name cut; current line 364 is unrelated argparse setup (lines have drifted from
edits), and the actual cut it described is now fixed and documented in-file at :389-394 ("UNCUT
(Hard Rule 0, order fe99e57e1993). This was `x['source'][:52]`...").

**DEFECT MAJOR — `RosterIncomplete`'s docstring claims universal per-source containment that
the `--source` CLI path does not provide.**
`roster()`'s `RosterIncomplete` (:47-58) documents: *"The caller at the bottom of this module
already catches per source and prints the exception's class name, so raising costs one source's
pass and prints why; returning silently costs the source's missing characters, permanently."*
That is true only of the `--all` path (`main()` :421-434, `try: res = backfill_source(...) except
Exception as e: errors += 1; print(...); continue`). The other entry point, `--source name
[name ...]` (:467-469):
```python
for s in a.source:
    print(json.dumps(backfill_source(s, recs, hosts, cap=a.cap, dry=a.dry),
                     ensure_ascii=False))
return 0
```
has no try/except at all. `backfill_source`'s own header comment (order 929622118156) already
half-acknowledges this gap but only fixes the *typo'd source name* case (returns a dict instead
of raising `StopIteration`); it explicitly notes "the explicit `--source name [name ...]` CLI
path does not [wrap in try/except]" as a known, unaddressed fact. Concretely: `python
backfill.py --source Foo Bar Baz`, where `Foo`'s wiki API returns `None` mid-category-walk
(`F.api` returning `None` for a timeout, per `RosterIncomplete`'s own motivating case) — `roster()`
raises `RosterIncomplete`, it propagates out of `backfill_source("Foo", ...)` uncaught, and the
whole `main()` invocation crashes with a traceback before `Bar` or `Baz` are ever attempted, even
though nothing is wrong with either. This contradicts Hard Rule -1's "a source is its own area of
the park" containment principle that the `--all` path (and `RosterIncomplete`'s own docstring)
correctly applies, and it means a single flaky wiki silently denies every subsequent named
source in one invocation. **Remedy:** wrap the `for s in a.source:` loop's body in the same
per-source try/except shape `--all` already uses.

Everything else read clean: `roster()`'s unlimited-by-default subcategory walk and its removed
caps, `lead()`'s marked-cut fallback, `audit()`, and `backfill_source`'s cap/ranking/write-gating
logic (the `t in sizes` sort key, the `absent`-before-cap reporting, the
`not_fetched`/`dropped_as_stub`/`size_lookup_failed` accounting, the write-denial short-circuit).

## src/recover_folder_records.py (379 lines)

Nothing found. Read the whole one-shot script: the `EXCLUDED_REGISTER_SOURCES = {"ME"}` guard,
the `is None` vs falsiness distinction for `source_map.get(name)`, the shortfall accounting
(order 729c26e0e63c) recorded before the early `continue` so it can't be silently dropped, the
"roll is a snapshot, record folder is the truth" `already`-populated guard (fails safe toward
not overwriting), the atomic `silence.write_json` + gated roll `update_rows` compare-and-swap,
and the fully-named (uncapped) reporting of every bucket (`skipped_no_map`, `skipped_no_items`,
`short_sources`, `skipped_populated`). All consistent with their extensive in-file
justifications; no lost-update or silent-failure path found.

## src/overwatch.py (1123 lines)

Nothing found. Full read of the standing debug-sweep daemon: `load()`/`save()`'s
preserve-the-wreck-then-refuse-to-overwrite contract for a damaged ledger, `_merge_ledgers`'s
monotone per-key union (findings/seen/rounds/last_run), `_finished_at`'s single-epoch-scale
tie-break, `rotation()`'s changed-then-longest-unread ordering, `verify_open`'s
only-stamp-what-was-actually-checked contract, `round_once`'s per-round `_LOCAL_BUSY` reset and
`--loop`'s per-round halt re-check (`_ESC_ROUND.assert_clear`), and `write_report`'s uncapped
open-findings list and its check-that-crashed-is-not-a-check-that-passed handling of
`struct["error"]`/`struct["estate_error"]`. All matches documented fixes; no fresh defect found.
The `structure()` reconcile filter's own criteria remain an open standing QUESTION (order
5b79deaaace9, not in the current open queue as its own row, so not re-filed here) but that is
pre-existing, not new.

## src/cascade_bridge.py (2317 lines)

Nothing found beyond the already-open account/config condition. **KNOWN 9fb8a6b10c1f — still
accurate.** The module's own comment at :49-69 confirms the local Ollama roster in
`<CASCADE_HOME>/config.json` still names three unused local models (`local-qwen3-30b`,
`local-qwen3-30b-q3`, `local-gemma3-12b`) against a daemon serving only `qwen3:8b`, and states
plainly the remedy "is not applied by the maintenance run that recorded it: the file is outside
this repository." This is an account/config condition, not a code fault, and the file's own text
says it has not been fixed.

Full read of the rest of the module (the graded-not-flat bench, `dead_forever`'s proof-file
memo keyed on mtime+TTL, the classifier trio `permanent_refusal`/`named_transient`/
`client_rejection` and their word-boundary/companion-word guards, `record_unrecognised`'s
digest-before-read CAS with read-back verification, `unrecognised_open`'s read-side re-triage
and pin/attempt mismatch labelling, `_ask_call`'s reserve-before-try/release-in-finally
invariant and its widen-fallback rotation, `prove()`/`try_disabled()`'s `max_attempts=1`
isolation) found nothing new; every subtlety I probed is already the subject of an in-file
comment recording a past incident and its fix, and I could not find daylight between the
comments' claims and the code.

## src/audit.py (271 lines, "BACKSCAN")

Nothing found. Checked in particular whether `band not in VALID_BANDS` at the entry level
(:140-141) would misfire on `magnitude: "unassayed"` the way order f149e109c174 describes a
similar three-fold misfire at the synthesis level — it does not, because `"unassayed"` is itself
a member of `PL.BANDS` (`src/pipeline.py:203`), so `band in VALID_BANDS` is True for it and the
"not on the ladder" check is correctly silent; `band and band != "unassayed"` is the separate,
correct gate for "does this entry actually claim a magnitude". `_JUNK`'s per-alternative
`$`-vs-`\b` anchoring, `_field`'s wrap-never-slice sample printing, and `main()`'s
population-correct denominator (`sources_with_synthesis` vs `entries_catalogued`) all read as
documented and uncapped.

## src/compress_store.py (149 lines)

Nothing found. Small, fully read: zstd-then-gzip fallback, content-hash-keyed temp-then-
`replace_retry` landing with pid+thread in the temp name, the guarded temp-cleanup-before-raise
on a denied replace, and `load()`'s address-verification against `_address_in()` (32-hex-char
stem check) before trusting decompressed bytes. Consistent with its own extensive commentary
(m55, run #19, order bf22c557852e).

---

## Summary of findings

- **DEFECT MAJOR** — `src/catalogue_web.py:288` (`catalogue_composite`): uncaught
  `wiki_source.rank_by_size` raise (this shift's fix) discards a whole composite source's
  already-gathered entries on one category's transient network failure, inconsistent with the
  per-category fault tolerance the surrounding loop already gives `category_members`.
- **DEFECT MAJOR** — `src/backfill.py` `main()`'s `--source` path (:467-469): no per-source
  try/except, so `RosterIncomplete` (or any exception) from one named source crashes the whole
  invocation before later-named sources run, contradicting `RosterIncomplete`'s own docstring
  claim and Hard Rule -1's per-source containment.
- **KNOWN e7143aba1e9a** — stale/resolved: both `wiki_source.py` findings (category_floor_report
  wired in, rank_by_size raises) are fixed this shift.
- **KNOWN 9fb8a6b10c1f** — still accurate: cascade_bridge's local roster mismatch is an
  external-config condition, unfixed, as the file's own comment says.
- **KNOWN fe99e57e1993** — partially accurate: the `backfill.py:364` citation is fixed; the
  order's other sites were not read this batch and were not re-verified.
- **QUESTION** — `runguard.py` `beat()`/`release()` authenticate by agent-name string, not by
  the new per-claim token; scoped deliberately per the file's own docstring, no demonstrated
  consequence found.

Counts: 2 DEFECT (both MAJOR), 1 QUESTION, 3 KNOWN.
