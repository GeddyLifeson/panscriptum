# sweep66 batch10 audit (maintenance run #66, 2026-09-27)

Auditor for batch 10. Read-only throughout: nothing under `src/`, `data/`, `state/`, `output/`,
`prompts/`, `reference/` or the repo root was edited, created or deleted, except this report and
the mandated `sweep_plan.record` call. No `drill.py`, `verify_math.py`, `generate.py`, `pipeline`,
`publish`, the crawl, `overwatch`, `foreman`, `mutate` was run, and nothing that clears a halt or
touches `prose_enabled`/`step4_enabled` was called. No subagents were spawned. The only execution
was a small standalone repro of `publish._package_store_facts` against a synthetic environment
(below), which touched no file under the repo.

## Scope (every line read, start to finish, via the Read tool, no sampling)

- `src/publish.py`         2253 lines (read in 5 chunks: 1-450, 451-900, 901-1350, 1351-1800,
  1801-2253)
- `src/dashboard.py`       1249 lines (read in 3 chunks: 1-420, 420-840, 840-1249)
- `src/rosetta.py`          815 lines (read in 2 chunks: 1-410, 411-815)
- `src/runguard.py`         660 lines (read in 2 chunks: 1-340, 341-660)
- `src/zfighters.py`        536 lines (read in 2 chunks: 1-270, 270-536)
- `src/suppressions.py`     425 lines (read whole)
- `src/navtree.py`          335 lines (read whole)
- `src/audit.py`            275 lines (read whole)
- `src/compress_store.py`   149 lines (read whole)

Total 6,697 lines across nine modules, matching `wc -l`, all read in full this session.

## Prior-audit cross-check

This exact nine-module roster was NOT audited together as one batch before, but every module was
covered very recently: `handoff/sweep65/AUDIT_batch10.md` (publish.py, dashboard.py, derivation.py,
runguard.py, zfighters.py, suppressions.py, style_audit.py, cachekey.py, module_index.py --
overlaps this batch on publish/dashboard/runguard/zfighters/suppressions), `handoff/sweep65/
AUDIT_batch09.md` (rosetta.py, among others), `handoff/sweep65/AUDIT_batch13.md` (navtree.py, among
others), and `handoff/sweep65/AUDIT_batch06.md` (audit.py, compress_store.py, among others). All
four were read in full before touching source. Between them they reported exactly one VERIFIED
finding across this batch's nine files (`publish.py:_package_store_facts`, below) and zero others;
everything else was traced and cleared.

Searched `state/workorders.json` (55 open orders) for all nine module names before writing
anything. Every hit is a pre-existing, already-open item, none of it new and none of it re-filed
here:

- `publish.py` -- order re-routed RUN -> OWNER re: scratch `.py` files under `handoff/` (a
  file-housekeeping decision, not a live code defect; the code-side refusal it depends on
  (`CODE_FREE_DIRS`/`_is_agent_scratch`) is still correct, re-verified below).
- `dashboard.py`, `navtree.py`, `rosetta.py`, `zfighters.py` -- all four are named inside the same
  sweep54 "FIVE THINGS" question-list order, none of it about a code defect in this batch's files
  specifically: (1) `overnight.py`'s `drill_rc is None` gate (not in this batch), (2) `scope.py`'s
  TIERS gap (not in this batch), (3) `custodes.py` (not in this batch), (4) `genre.py`'s missing
  `_BAD_CHARS` self-check (not in this batch -- and irrelevant here since all nine of this batch's
  modules already carry that self-check, confirmed by reading each one's header), (5)
  `navtree.py`/`rosetta.py` writing outside `output/`/`state/` without `escalation.assert_clear()`
  -- already covered by the next item.
- `navtree.py`/`rosetta.py` also separately named by owner order `5bb12b398783` (sweep54) and the
  broader class question `1e6f99e54b25` (sweep58, "should manually-invoked writers of corpus/
  output data refuse under a halt"). Confirmed still true by this read: `navtree.main()`'s
  `--write` path and `rosetta.py --mine`/`--refine` still call `silence.write_json` directly with
  no halt check. This is an open OWNER ruling question, not a defect, and is not re-filed.
- `suppressions.py` -- named only as one of three call sites in an unrelated order about a
  shared `_marked`-style truncation helper being proposed for hoisting (`axis_correlation.write()`,
  `custodes._transit_widening()`, `suppressions.add()`); not about a defect in `suppressions.py`
  itself. `suppressions.py`'s own truncation helper (`_preview`) already carries a marker, unlike
  the raw form these three sites are being asked to converge on.
- `audit.py` -- matched only via a passing mention inside the `thread_integrity`/`allsweep.py`
  DANGLING-escalation ruling question (`allsweep.py:181 agrees with it -- ... the same as
  silence.py and audit.py`); not about a defect in this `audit.py`, which does not implement
  `thread_integrity` at all (that is a different module, not in this batch).
- `runguard.py`, `compress_store.py` -- no hits.

## Findings

### 1. CLOSED (not a new finding) -- `publish.py:_package_store_facts` bug from sweep65 is fixed

sweep65's batch10 audit filed a MINOR, CONFIRMED finding at `publish.py:811-848`: the function
gated on `if rel is None or not local:`, which fired the wrong branch ("path is not under AppData")
whenever `LOCALAPPDATA` was unset/empty even though the path had matched the `APPDATA` (Roaming)
root correctly.

Current source (`publish.py:825-841`) has this fixed:

```python
        local = os.environ.get("LOCALAPPDATA", "") or (
            os.path.join(os.path.dirname(os.path.abspath(roaming)), "Local") if roaming else "")
        roots = [(os.path.normcase(os.path.abspath(local)), "Local")] if local else []
        if roaming:
            roots.append((os.path.normcase(os.path.abspath(roaming)), "Roaming"))
        rel, kind = None, None
        for root, k in roots:
            if full.startswith(root + os.sep):
                rel, kind = full[len(root) + 1:], k
                break
        if rel is None:
            return "package store: path is not under AppData, so virtualisation cannot explain it"
```

`local` is now derived from Roaming's sibling when `LOCALAPPDATA` is unset, and the gate checks
only `rel is None`. The function's own docstring and a new comment at line 829 ("sweep65 batch10:
an unset LOCALAPPDATA misreported a Roaming path") record the fix and cite the finding by name.

**VERIFIED by direct execution** in a scratch script (imported `publish._package_store_facts`
directly against a synthetic `os.environ`, restored afterward; nothing under the repo was
touched):

```
Case B (LOCALAPPDATA="", APPDATA set, path under Roaming\GitHub CLI\hosts.yml):
  -> "package store: no packaged app holds a copy either; the file is genuinely missing"
Case C (LOCALAPPDATA deleted entirely, same path):
  -> same as Case B
Case A (both set, path under Local\gh-cli\bin\gh.exe):
  -> same shape ("no packaged app holds a copy either")
```

All three now reach the actual package-store search rather than short-circuiting on the wrong
"not under AppData" message (which is what sweep65 measured before the fix). The "no packaged app
holds a copy" answer for the synthetic `fakeuser` paths is expected -- this machine has no such
user -- and is not itself a finding; the point verified is which branch the function took.

No other defect found in this function or its siblings `_token_facts`/`_credential_probe`; both
are unchanged from sweep65's clean bill.

## Everything else checked and cleared (re-verified against current source, not assumed)

- **`publish.py`**: read start to finish. `export_root`/`home_export`'s throwaway-directory
  refusal; `_is_skipped`/`_is_agent_scratch`/`CODE_FREE_DIRS`/`gitignore_lines()`'s derived,
  shape-based (not enumerated) refusal of scratch code under `handoff/`; the three secret-scan
  locks (`_SECRET`, `_SECRET_ASSIGN`+`_entropy`, and `scan_for_secrets`'s streaming per-file scan
  via `_scan_units`, including the compiled-bytecode exclusion and the suppressed-not-dropped
  reporting); `_live_root_state`/`_live_file_state`'s live/gone/unavailable three-way
  classification and the matching `prune_export`/`sync_tree` withdrawal logic (COPY_DIRS roots,
  COPY_FILES, and the "roots/files nobody copies any more" sweeps); `_unpushed()`'s three-outcome
  contract; `PushHeld`'s three interlocks (ledger guard import, mutation interlock read on both
  sides of the tree copy, secret scan) all fail closed on an unimportable dependency; `push()`'s
  fetch-rebase-then-push sequence and its own confirmation re-read after a reported-successful
  push; `maintenance_shift_live`'s deliberate fail-open on an unreadable guard; `_one_shot_push_
  verdict`'s three cases (modern token match, legacy assertion, refusal); `main()`'s per-cycle halt
  re-check, `codewatch.exit_if_stale` at the loop tail, and the `break`-sets-`rc=1` exit path. All
  traced end to end against the live source; matches sweep65's detailed trace with no drift beyond
  the one fix above.
- **`dashboard.py`**: read start to finish, including the full HTML/CSS/JS page body and the HTTP
  server. `quotas()`/`throughput()`/`jobs()`/`library()`/`watch()`/`safety()`'s per-panel fault
  isolation (each wrapped so one bad log/file cannot black out `/api/state`); `movement()`'s
  corrupt-history-must-heal three-layer guard (non-list, non-dict-element, non-numeric-`at`), the
  `hist[:-1]` cold-start fix, and the reset-on-negative-delta rule; `safety()`'s absent-vs-
  unreadable distinction on the halt, drill record and escalation log; `main()`'s read-only-
  instrument exemption from the halt (renders it instead of refusing to start) with the fail-closed
  import guard kept intact. All unchanged from sweep65's clean bill.
- **`rosetta.py`**: read start to finish. `numeric_rows`'s row-vs-window split and the "first
  number after the name, never the largest" column-order rule; `ordinal_rows`'s original-text
  (never lowercased-copy) offset matching; `stand_rows`'s label-anchored parameter-block reading
  and its mean-of-parameters-present scoring; `assays_by_host`'s partition("|") fix for a bare key;
  `check()`'s per-host scoping via `by_host` and its `rho=None` unscorable-vs-disagreement
  distinction; `refine()`'s per-host Persons-only matching and the numeric-scale order-of-magnitude
  floor; `main --mine`'s `MINE_FLOOR` refusal-to-shrink guard and per-host error isolation. All
  unchanged from sweep65's clean bill.
- **`runguard.py`**: read start to finish. `read_verdict`'s three-fault classification (unparseable,
  wrong-shape, unfinished-with-no-heartbeat) and its escalate-but-still-claim fail-open policy
  under owner ruling `70f66fbd98aa`; `_land_claim`'s digest-before-read compare-and-swap, used
  identically by `claim`/`beat`/`release`; `holder_is_live`'s asymmetric pid-identity check (only
  ever proves LIVE, never DEAD); `guard_fault`'s single-shape (stale-but-alive) detector and the
  documented reason the opposite shape was removed; `claim()`'s per-claim token minting and
  digest-only storage. All unchanged from sweep65's clean bill.
- **`zfighters.py`**: read the full roster (all fifteen hand-built sheets) and confirmed every
  `axes=dict(...)` block carries a genuine `(score, evidence, provenance)` triple with no bare
  placeholder axis. `compute()`/`main()`'s Goku-sheet fallback (with the incomplete-roster marker
  correctly excluded from ranking via the `_incomplete` underscore convention), the `--full`
  worksheet wrapping (`textwrap.wrap`, no truncation, correct continuation-line alignment), and the
  gated `write_json` verdict. All unchanged from sweep65's clean bill.
- **`suppressions.py`**: read start to finish. `_load`'s wrong-shape-is-corruption handling;
  `_mutate`'s compare-and-swap with re-apply-on-lost-race; `add`/`remove`'s "REFUSED IS NOT ADDED"/
  "STILL IN FORCE" fail-closed discipline and the unbounded (never capped) stored reason; `active`/
  `suppressed`'s fail-closed-on-unreadable and deliberate `fnmatchcase`; `_repo_listing`'s
  single-walk, per-directory-relpath optimisation; `problems()`'s expired-vs-dangling distinction
  and lazy listing build. All unchanged from sweep65's clean bill.
- **`navtree.py`**: read start to finish. `build()`'s "sources first, so a branch exists even
  where nothing is catalogued yet" ordering; `sources_under()`'s `+ "."` boundary fix on both arms
  so a sibling branch sharing a numeric prefix cannot vote in the wrong node's naming ballot;
  `register_for`/the hyperverse-naming loop's deterministic `(count, name)` tie-break (m41 fix);
  `audit()`'s child-sum-vs-claimed-count check with its own fail-safe against a dangling child key;
  `main()`'s gated writes (both the audit-record write and the `--write` tree write) and the
  exit-code fix so a denied write or an unclean audit cannot report rc=0. The `data/NAVTREE.json`
  write with no `escalation.assert_clear()` call is the same pre-existing, already-open owner
  question named above, not a new finding.
- **`audit.py`**: read start to finish. `_JUNK`'s per-alternative anchoring (`\b` vs `$`) correctly
  matching its own comment's stated intent, verified against the five example titles the comment
  names; the source-population (`sources_with_synthesis`) vs. entry-population
  (`entries_catalogued`) denominator split for the rate calculation; every long field
  (`fails[k]` list, scale-note text, description text) printed whole or wrapped, never sliced.
- **`compress_store.py`**: read start to finish. `store()`'s pid/thread-qualified temp name and
  `replace_retry`-gated landing, with the temp file swept before raising on a denied replace;
  `load()`'s content-hash verification against `_address_in(path)`, correctly gated on the path
  actually looking like a 32-hex-character content address so a hand-copied file cannot be flagged
  as corrupt.

## Questions

None new. The pre-existing open OWNER questions touching this batch's files (`navtree.py`/
`rosetta.py` writing outside `output/`/`state/` without a halt check, and the sweep54
"FIVE THINGS" list's item 5 covering the same pair) are listed under "Prior-audit cross-check"
above with their order IDs rather than repeated here, per the brief's instruction not to re-file
an already-open item.

## Coverage recorded

Recording via `sweep_plan.record('run66', ['publish.py', 'dashboard.py', 'rosetta.py',
'runguard.py', 'zfighters.py', 'suppressions.py', 'navtree.py', 'audit.py', 'compress_store.py'],
batch=10)` for all nine modules listed above, each read in full this session.
