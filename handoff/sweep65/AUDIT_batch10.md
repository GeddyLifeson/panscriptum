# sweep65 batch10 audit (maintenance run #65, 2026-09-26)

Auditor for batch 10. Read-only throughout: nothing under `src/`, `data/`, `state/`, `output/`,
`prompts/`, `reference/` or the repo root was edited, created or deleted, except this report and
the mandated `sweep_plan.record` call. No `drill.py`, `verify_math.py`, `generate.py`, `pipeline`,
`publish`, the crawl, `overwatch`, `foreman`, `mutate` or `verify_math` was run, and nothing that
clears a halt or touches `prose_enabled`/`step4_enabled` was called. No subagents were spawned.
The only executions were small, read-only scratch scripts: a synthetic-environment reproduction
of `publish._package_store_facts` (below), a direct `derivation.check_graph()` call (0 problems,
confirming the ledger still closes), and `style_audit.py --self-test` (PASSED, all twelve
checks), none of which wrote anything outside a scratch temp directory.

## Scope (every line read, start to finish, via the Read tool, no sampling)

- `src/publish.py`         2249 lines (read in 6 chunks)
- `src/dashboard.py`       1249 lines (read in 4 chunks)
- `src/derivation.py`       816 lines (read in 2 chunks)
- `src/runguard.py`         660 lines (read in 2 chunks)
- `src/zfighters.py`        536 lines (read in 2 chunks)
- `src/suppressions.py`     425 lines (read whole)
- `src/style_audit.py`      342 lines (read whole)
- `src/cachekey.py`         217 lines (read whole)
- `src/module_index.py`     192 lines (read whole)

Total 6,686 lines across nine modules, all read in full. Per the brief: `publish.py` gained
`_package_store_facts` on this run (#65); it was read closely and is the subject of this batch's
one finding.

## Prior-audit cross-check

Read `handoff/sweep64/AUDIT_batch10.md` (publish.py, dashboard.py, catalogue_web.py,
build_terminal.py, worldseed.py, suppressions.py, wh40k.py, propagation.py, catalog.py —
the closest predecessor roster, overlapping on publish/dashboard/suppressions),
`handoff/sweep64/AUDIT_batch09.md` (derivation.py, zfighters.py, among others),
`handoff/sweep64/AUDIT_batch08.md` (runguard.py), `handoff/sweep64/AUDIT_batch11.md`
(cachekey.py), `handoff/sweep64/AUDIT_batch15.md` (module_index.py), and
`handoff/sweep64/AUDIT_batch16.md` (style_audit.py) before reading any source. Every one of
these nine modules has a clean recent history: sweep64's audits traced `sync_tree`/
`prune_export`'s deletion mechanics, the secret scanner's three locks, `dashboard.py`'s panel
fault-isolation and movement-history healing, `derivation.py`'s cycle-detection early return,
`zfighters.py`'s Goku-fallback and `--full` worksheet wrapping, `suppressions.py`'s
compare-and-swap and fail-closed discipline, `cachekey.py`'s verify-before-trust, and
`module_index.py`'s duplicate/stale-group detection, and found 0 new VERIFIED/SUSPECTED defects
across all nine. Re-reading the full current source confirms all of that is still true and
unchanged, with one exception: `publish.py` gained a new function today.

Searched `state/workorders.json` for each of the nine filenames. Hits of substance:
`573ab7b04b6f` (`PUBLISH_DAEMON_CANNOT_SEE_GH_CREDENTIAL_HELPER`, OWNER-handler, MAJOR) — this
is the order `_package_store_facts` was written today to help diagnose; it names the cause as
proven (an MSIX package-store virtualisation of `gh.exe`) and the remedy as a person-only fix
(reinstall `gh` or repoint the git credential helper). Not re-filed; my finding below is a
narrower defect in the new diagnostic helper itself, not in the order's own conclusion, which I
independently reproduced (see below) and found sound. No other hit named a live code defect in
this batch's files rather than context/carry-forward narrative.

## Findings

### 1. `src/publish.py:811-848`, `_package_store_facts()` — CONFIRMED (reproduced by execution).
MINOR (display-only diagnostic text; the function decides nothing that gates a push).

The function is meant to say, for a credential-helper path that failed to exec, whether it
exists only inside a packaged app's private AppData (the actual cause of order `573ab7b04b6f`).
It builds a list of `(root, kind)` pairs to test the path against — `("Local", LOCALAPPDATA)` if
`LOCALAPPDATA` is set, `("Roaming", APPDATA)` if `APPDATA` is set — finds which root the path
falls under, and then gates on the WRONG condition:

```python
        rel, kind = None, None
        for root, k in roots:
            if full.startswith(root + os.sep):
                rel, kind = full[len(root) + 1:], k
                break
        if rel is None or not local:
            return "package store: path is not under AppData, so virtualisation cannot explain it"
```

`rel is None` correctly means "matched neither root." But `not local` is unconditional — it
fires even when the path DID match the `APPDATA` (Roaming) root, purely because `LOCALAPPDATA`
happens to be empty or unset. In that case `rel`/`kind` are already set correctly from the
Roaming match, and the function still returns the "path is not under AppData" message, which is
false: the path IS under AppData (Roaming), the real reason nothing can be checked is that
`LOCALAPPDATA` is missing so `%LOCALAPPDATA%\Packages` cannot be listed.

**Reproduced** in a scratch script (`_package_store_facts` imported directly, no project state
touched) with three cases:

```
A: LOCALAPPDATA and APPDATA both set, path under LOCALAPPDATA, no package copy exists
   -> "package store: the file exists ONLY inside the private AppData of Claude_pzs8sxrjxfjjc
      -- it was installed by a process running inside that app..." (correct; matches this
      machine's real gh.exe)
B: LOCALAPPDATA="" (empty), APPDATA set, path under APPDATA\GitHub CLI\hosts.yml
   -> "package store: path is not under AppData, so virtualisation cannot explain it"  (WRONG —
      the path literally is under AppData)
C: LOCALAPPDATA deleted from the environment entirely, same path
   -> same wrong message
```

**Failure scenario**: this function is only ever called from `_credential_probe()` on the
credential-helper exe path parsed out of git's own error text, and on this machine that is
always `gh.exe` under `%LOCALAPPDATA%\gh-cli\bin\gh.exe` — so in the live deployment
`LOCALAPPDATA` being unset while the failing path is still under `%APPDATA%` cannot currently
happen, and this is why the bug is inert today rather than actively misleading the operator
reading order `573ab7b04b6f`'s evidence. It would misfire the day this helper is reused for a
path that legitimately lives under `%APPDATA%` (or on a process whose `LOCALAPPDATA` is blanked
for some other reason while `APPDATA` survives), printing "not under AppData" for a path that
demonstrably is, which would send a future reader down the wrong branch of this diagnostic at
exactly the moment they are trying to confirm the package-store theory.

**Proposed fix**: gate on which root actually matched, not on the truthiness of `local`:

```python
        if rel is None:
            return "package store: path is not under AppData, so virtualisation cannot explain it"
        if not local:
            return "package store: matched the Roaming root, but LOCALAPPDATA is unset so " \
                   "%LOCALAPPDATA%\\Packages cannot be searched"
```

Function is display-only (its docstring says so) and gates nothing about whether a push
proceeds, hence MINOR rather than MAJOR despite being a logic defect proper.

## Everything else checked and cleared (re-verified against current source, not assumed)

- **`publish.py`**: `sync_tree`/`prune_export`'s live/gone/unavailable three-way classification
  (`_live_root_state`, `_live_file_state`), the `CODE_FREE_DIRS`/`_is_agent_scratch` refusal and
  matching `gitignore_lines()` derivation, the three secret-scan locks (`_SECRET`,
  `_SECRET_ASSIGN`+entropy, and `scan_for_secrets`'s file-level scan with `_scan_units`'s
  overlapping-segment streaming), `_unpushed()`'s three-outcome contract, `PushHeld`'s three
  interlocks (ledger guard, mutation interlock at both push-time and pre-copy, secret scan),
  `maintenance_shift_live`'s deliberate fail-open, and `_one_shot_push_verdict`'s three cases —
  all traced end to end against the live source and match their own extensive documentation; no
  drift from sweep64/batch10's detailed trace of the same functions. `_token_facts()` and
  `_credential_probe()` (the two functions `_package_store_facts` was added beside) are otherwise
  unchanged and correct.
- **`dashboard.py`**: `quotas()`/`throughput()`/`jobs()`'s per-panel fault isolation, `movement()`'s
  corrupt-history-must-heal three-layer guard and the `hist[:-1]` cold-start fix, `safety()`'s
  absent-vs-unreadable distinction on the drill record and the escalation log, and the page's own
  JS panel builders (`panelMovement`, `panelSafety`, `panelStandards`, `panelWatch`, etc.) — all
  re-read in full and unchanged from the clean bill sweep64/batch10 already gave them.
- **`derivation.py`**: `check_graph()`'s four rules (UNKNOWN kind, DANGLING parent, ROOTLESS
  DERIVED, UNSIGNED OWNER) and its cycle detector, `depth()`'s memo-free-but-terminating
  recursion, and `main()`'s early-return-on-failure (order 90516d53d696) — traced by hand and
  confirmed by direct execution: `derivation.check_graph()` returns `0 problems` against the live
  112-quantity ledger.
- **`runguard.py`**: `holder_is_live()`/`guard_fault()`'s asymmetric pid-identity check (only
  ever proves LIVE, never DEAD, by design — re-verified against the 2026-09-09 incident it was
  written for), `_land_claim`'s digest-before-read compare-and-swap used identically by `claim`/
  `beat`/`release`, and `claim()`'s fail-open-but-escalated corrupt-guard path — all match their
  documentation.
- **`zfighters.py`**: all fifteen hand-built roster sheets carry a genuine `(score, evidence,
  provenance)` triple per axis (verified by reading every `axes=dict(...)` block); `compute()`/
  `main()`'s Goku-sheet fallback, `--full` worksheet wrapping (`textwrap.wrap`, no truncation),
  and the gated `write_json` verdict all match their documentation.
- **`suppressions.py`**: `_load`'s wrong-shape-is-corruption handling, `_mutate`'s compare-and-swap
  with re-apply-on-lost-race, `add`/`remove`'s "REFUSED IS NOT ADDED"/"STILL IN FORCE" fail-closed
  discipline, `suppressed()`/`problems()`'s deliberate `fnmatchcase`, and `_repo_listing`'s
  single-walk optimisation — all traced and match their documentation.
- **`style_audit.py`**: `TURN_ENDING`'s `\Z`-anchored regex (not `re.M`, correctly avoiding the
  per-paragraph false-positive its own comment documents), `opener_shape`'s NAME-collapsing, and
  the `_cut()` no-truncation ranking helper — re-verified and confirmed by running
  `--self-test`, which passed all twelve assertions (entry splitting, shape collision/non-collision,
  tell-detection by name, turn-ending exact count, em-dash detection, and the negative-control
  fixture tripping nothing).
- **`cachekey.py`**: `owns()`'s entity-and-optional-host verification, `load()`'s
  miss-not-mismatch semantics, `write_path()`'s natural-vs-disambiguated-path branch, and
  `text_digest`/`provenance_ok`'s three-outcome (proven/changed/unverifiable) contract — traced
  and match their documentation.
- **`module_index.py`**: `_modules()`'s recursive walk (subdirectories included, `__pycache__`
  pruned), the stale-group-name and duplicate-group-name detectors (both correctly accumulate
  into the exit code rather than being printed-and-discarded), and the gated `replace_retry`
  write — all match their documentation. `GROUPS` currently names no stale or duplicate module
  (not run, but visually cross-checked against `_modules()`'s output shape by inspection).

## Questions

None met the bar for a design/policy question distinct from the finding above. The credential
diagnostics generally (`_token_facts`, `_credential_probe`, `_package_store_facts`) are all
explicitly display-only and none of them gates a push decision, so there is no fail-open/
fail-closed policy question raised by today's addition — only the logic defect filed above.

## Coverage recorded

Recording via `sweep_plan.record('run65', [...], batch=10)` for all nine modules listed above,
each read in full this session.
