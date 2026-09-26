# sweep64 batch16 — audit

## Scope and method

Read every line, in full, sequentially, of all nine modules in this batch:

- `src/local_agent.py`     1650 lines — read in full (2 chunks) [SAFETY-CRITICAL: write gate]
- `src/binding_health.py`  1601 lines — read in full (3 chunks) [canary / quarantine gate]
- `src/threads.py`         1022 lines — read in full (2 chunks)
- `src/address_space.py`    679 lines — read in full (2 chunks)
- `src/handbuilt.py`        519 lines — read in full (1 chunk)
- `src/render.py`           441 lines — read in full (1 chunk)
- `src/style_audit.py`      342 lines — read in full (1 chunk)
- `src/audit.py`            275 lines — read in full (1 chunk)
- `src/compress_store.py`   149 lines — read in full (1 chunk)

Total: 6,678 lines across 9 modules. Read-only. Nothing under `src/`, `data/`, `state/` or
`output/` was edited, created or deleted. No `drill.py`, `verify_math.py`, `generate.py`,
pipeline, `publish`, `mutate`, `local_agent`, or `binding_health --run` job was executed. No
subagents were spawned. `handoff/sweep63/` was consulted for the modules it also covered
(`local_agent.py`, `binding_health.py`) before concluding on them; its findings are not
re-reported here except where noted.

This is a heavily audited, mature codebase. Almost every module carries dense inline
documentation of previously found and fixed defects (tautologies, fail-open guards, caps,
discarded write verdicts, TOCTOU races, case/prefix/ADS/junction/hard-link bypasses), each cited
by order ID. Findings below are only things not already fixed and documented in the source
itself.

## Findings

### VERIFIED — `src/binding_health.py`: a fully-throttled (HTTP 429) host can be scored `healthy=False` and quarantined

This is exactly the failure mode the task asked to check for ("check that a throttled probe can
never be scored False"), and it is real: two of the three canary probes lack the outcome channel
that the third one (`_fetch_chars`, feeding `_probe_present`) was already fixed to use.

**The mechanism.** `feats.api()` (src/feats.py:840-962) does not raise on a 429/503. On the last
retry it calls `note_throttled(host)` and returns `None` cleanly:

```python
if e.code in (429, 503):
    ...
    if attempt == retries:
        _stamp(False, "throttled")
        return None
```

`feats.api()` explicitly documents an `outcome=` parameter for exactly this reason — "Pass a
dict and this call stamps it with {'ok': bool, 'why': str}" — so a caller can tell "throttled"
apart from "the host genuinely answered nothing." `binding_health._fetch_chars` (line 520) uses
it correctly: `got = F.fetch(host, [title], outcome=_oc)`, and its caller `_probe_present`
treats a `why == "throttled"` result as an error, not as a clean miss (lines 542-545).

`_probe_absent` (line 764) and `_probe_reachable` (line 843) do **not** thread the outcome
channel through:

```python
# _probe_absent, line 764
got = F.fetch(host, [ABSENT_PROBE])          # no outcome= passed
...
if not got:
    return True, "correctly absent -- nothing came back for a title that cannot exist"
```

```python
# _probe_reachable, line 843
d = F.api(host, {"action": "query", "meta": "siteinfo"}, retries=0)
...
if not isinstance(d, dict) or "query" not in d:
    return False, "siteinfo returned nothing usable -- the API is not answering"
```

On a 429, `F.fetch()`/`F.api()` return `{}`/`None` — not an exception — so the `except
Exception` arms in both functions (which correctly return `None`, "could not ask", and are the
arms the extensive surrounding docstrings describe as the fix for "not asked is not answered")
are never reached for real throttling. The throttled case falls straight through to the
"answered cleanly" branches: `_probe_absent` reports `ok_absent=True` ("correctly absent"), and
`_probe_reachable` (called with `retries=0`, so it gives up on the very first 429) reports
`ok_reachable=False` ("the API is not answering").

**Failure scenario.** A host in deep backoff (e.g. during a busy evening sweep, or one already
in `_throttle`'s consecutive-strike ladder) answers every request with 429:

1. `_probe_present` correctly identifies each candidate title fetch as throttled via
   `_fetch_chars`'s outcome channel, collects them as errors, and returns
   `ok_present=False, det_p="every probe failed: transport did not answer cleanly: throttled"`.
2. Because `ok_present` is falsy, `canary()` calls `_probe_reachable(host)`, which also hits the
   429 wall and returns `ok_reachable=False` (not the `None`/"unmeasured" it should).
3. `_probe_absent` also hits the 429 wall on its one fetch, gets back an empty dict, and returns
   `ok_absent=True` (not `None`/"unmeasured").
4. `verdict(False, True, False, ...)` (line 1001): since `ok_absent` is not `None`, the
   first (correct, "unmeasured") branch is skipped entirely. `ok_present and ok_absent` is
   `False`. `not ok_absent` is `False`. `ok_reachable` is `False`, not `None`, so the function
   falls through to `return False, "host unreachable: ..."`.
5. `canary()` returns `healthy=False`. `run()` (line 1350) then calls
   `quarantine(h, rec.get("reason") or "canary failed")`, holding the host for `RETRY_AFTER_S`
   (24h).

This reproduces, through a different door, precisely the "74 throttled probes came back as 0%"
/ "1,364 throttled fetches filed as honest absences" failure this whole module's docstring says
it exists to prevent — a host that is merely busy gets its coverage switched off and reported as
broken, for up to 24 hours, on the strength of nothing but rate-limiting.

**Fix shape** (not applied — read-only audit): thread `outcome=` through the `F.fetch()` call in
`_probe_absent` and the `F.api()` call in `_probe_reachable`, and treat a `why` of `"throttled"`
(or any non-clean, non-`CLEAN_NEGATIVES` reason) the same way `_probe_present` already does:
as "could not ask" (`None`), not as an answer.

### SUSPECTED — `src/local_agent.py`: `DENYLIST_PREFIXES` region check in `t_propose_patch` is not re-asked of a hard-linked path, and `_protected_identities()` deliberately excludes regions

`t_propose_patch`'s own region guard (lines 1014-1020) tests only the as-written spelling:

```python
for _pfx in DENYLIST_PREFIXES:
    if _rel_l.startswith(_pfx):
        return _settle({...})
```

This differs from the `WRITABLE_PREFIXES` allowlist check immediately above it (lines 996-1010),
which explicitly re-tests the **resolved** spelling too (`_spellings` includes
`os.path.relpath(os.path.realpath(full), ...)`), specifically because a junction can make the
written and resolved spellings disagree.

For an ordinary junction this gap is closed one layer down, in `_safe()`: when the written and
resolved project-relative paths differ, `_safe()` re-asks `_denied_target(rel_real)` (line 534),
which does include `_denied_region()` (the `DENYLIST_PREFIXES` test) — so a junction from the
writable surface into `state/`, `data/records/`, `reference/keystone_volumes/` or
`output/index/` is refused before `t_propose_patch` is even reached.

A **hard link** is different, and the module's own `_protected_identities()` docstring (lines
551-577) says so at length: a hard link has no "target" for `os.path.realpath()` to resolve, so
`rel_written == rel_real` for a hard-linked path, and `_safe()`'s junction-diversion branch never
fires. `_protected_identities()` was written precisely to close this for **named** denylist
modules and `DENYLIST_PATHS` entries (`config.yaml`) by comparing `(st_dev, st_ino)` — but its
own docstring states the identity set is built **only** from `DENYLIST` module names and
`DENYLIST_PATHS`, and explicitly **not** from `DENYLIST_PREFIXES` regions: "MODULES AND PATHS
ONLY, never the DENYLIST_PREFIXES regions, and that is a deliberate boundary rather than an
oversight... building an identity set for a region would mean an unbounded `os.walk` on the
write path."

**The gap this leaves**: if a file under the writable surface (`src/`, `prompts/`, `handoff/`)
is ever a hard link to a file inside a protected region (`state/`, `data/records/`,
`reference/keystone_volumes/`, `output/index/`), none of the three checks catch it — not
`_identity_denied` (regions excluded by design), not the written-spelling `DENYLIST_PREFIXES`
test (the hard link's own name is outside every prefix), not the junction-diversion re-ask in
`_safe()` (hard links don't produce a spelling mismatch for `realpath` to notice). `open(full,
"w")` would then rewrite the real protected-region file (e.g. a record in `data/records/`,
bypassing the two-writer contract; or a keystone volume) via a name that looks entirely ordinary
on the writable surface.

**Why this is SUSPECTED, not VERIFIED:** the model's own tool set (`read_file`, `list_dir`,
`grep`, `find_symbol`, `run_check`, `propose_patch`) cannot create a hard link — `propose_patch`
requires the target to already be a file (`os.path.isfile(full)`), so the model cannot construct
this bypass by itself in a single run. Exploiting it requires a hard link to already exist
somewhere under `src/`, `prompts/`, or `handoff/` pointing into one of the four protected
prefixes, which I did not check for on this machine (that would mean walking every file's
`st_ino` under the writable surface against every file under the protected regions — expensive,
and out of scope for a read-only pass). The developers' own comment shows they considered exactly
this shape and made a deliberate, reasoned tradeoff (cost of an unbounded walk vs. the residual
risk) rather than missing it — so this reads as a known, accepted residual gap rather than an
oversight, but it is still a real path by which a write could land in a protected region if the
precondition (a pre-existing hard link) is ever true. Worth a targeted check (`os.walk` the
writable surface, `os.stat` each file, and cross-reference `st_ino` against every file under the
four `DENYLIST_PREFIXES` regions) before treating the boundary as closed.

## Everything else read and not flagged

- **`src/local_agent.py`** (the rest of it): the write-gate machinery is exceptionally
  well-defended. I traced all eight documented bypass classes (case, name-prefix, NTFS ADS,
  case-sensitive extension, unlisted directory, junction, wrong-file import gate, hard link on
  named denylist entries) against the current source and each fix holds under the scenarios its
  own comment describes. The `_gates()` parse/lint/import/verify_math sequence, the blast-radius
  cap, the revert-on-failure path (including the failed-revert ALARM/SAFETY escalation), and the
  turn-loop's malformed-tool-call handling are all sound on inspection. No new escape path found
  beyond the SUSPECTED hard-link/region gap above.
- **`src/threads.py`**: the T1-T4 thread-derivation and its refusal paths (`ThreadRefused`,
  `AnnexJoinUnreadable`, the anti-dangling `_resolves`/`edge()` checks, `verify()`'s round-tripped
  checks) are internally consistent; every `[:n]` slice I found (`cohort_family`'s `parts[:2]`)
  is a field decomposition, not a listing truncation, matching the file's own Hard-Rule-0
  self-audit. `step4_gate_open()` / `prose_gate` / `step4_enabled` were not opened or touched, per
  the task's instruction; no question arose about that gate's design.
- **`src/address_space.py`**: pure arithmetic (bit-packing, width derivation from `TIERS.json`,
  hash-offset floors). `pack()`'s raise-not-truncate contract and `assign()`'s removal of the
  old modulo-wraparound are both correctly wired to their described call sites. No logic bugs
  found.
- **`src/handbuilt.py`**: static, hand-authored assay data plus a small renderer; the
  `score_str` sentinel-vs-number branch and the write-before-print ordering (to survive a
  non-UTF-8 console) are both correct.
- **`src/render.py`**: `children_of()`'s whole-coordinate-required guard and `containment_svg`'s
  child-count-vs-layout-divisor separation are both correct; `write_views()` uses an atomic
  temp+`replace_retry` write with a pid/thread-qualified temp name.
- **`src/style_audit.py`**: `TURN_ENDING`'s `\Z`-anchored regex and the self-test's
  positive/negative fixture pair genuinely exercise the shape-collision and turn-ending
  detectors (verified by reading the assertions against the fixtures rather than trusting the
  docstring). `_cut(len(heavy), len(heavy), ...)` always reports "all shown" for the vocabulary
  ranking, which is correct — that ranking is genuinely uncapped (`most_common()` with no
  argument, filtered only by the rate threshold), not a bug.
- **`src/audit.py`**: `_JUNK`'s per-alternative anchoring (`\b` vs `$`) matches its own comment's
  stated intent, and the denominator-per-population fix (`sources_with_synthesis` vs
  `entries_catalogued`) is applied correctly to every failure class.
- **`src/compress_store.py`**: `load()`'s content-hash verification against `_address_in(path)`
  and `store()`'s atomic temp+`replace_retry` write are both sound; the temp-cleanup-before-raise
  path correctly does not let a cleanup failure mask the original error.

## Summary

- VERIFIED: 1
- SUSPECTED: 1
- QUESTION: 0
