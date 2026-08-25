# Batch 11 audit — run #25

Files: `src/overnight.py`, `src/zfighters.py`, `src/publish.py`, `src/context_budget.py`,
`src/wh40k.py`, `src/recover_folder_records.py`, `src/resonance.py`. All read end to end, every
line, no sampling.

## SPECIAL ITEM 1 — SECRET SCAN OF `publish.py`'s SYNCED TREE (loud, first)

**RESULT: CLEAN. No live secret found.** This re-confirms run #24's finding — same result,
independently re-derived.

Method (VERIFIED — commands actually run, not inferred): grepped every directory `sync_tree()`
copies (`src/`, `prompts/`, `reference/`, `registry_terminal/`, `handoff/`) and every file in
`COPY_FILES` (`CLAUDE.md`, `README.md`, `config.yaml`, `requirements.txt`, `WATCH.md`,
`STATUS.md`, `HANDOFF.md`, `BUGS.md`, `NEXT_STEPS.md`, `MAINTENANCE.md`) for:
- every pattern in `publish.py`'s own `_SECRET` regex (`sk-`, `gsk_`, `AIza`, `github_pat_`,
  `ghp_`, `hf_`, `xai-`, `csk-`)
- AWS-shaped keys (`AKIA...`)
- PEM/private-key headers (`-----BEGIN ... PRIVATE KEY-----`)
- embedded URL credentials (`://user:pass@`)
- `Authorization: Bearer ...` strings
- generic `key/token/password/secret[:=]"..."` assignments
- any `.env`, `.pem`, `.key`, `*credential*`, `.p12`, `.pfx` files sitting under a synced dir

Zero hits across all patterns and all paths. Manually eyeballed every "key/token/password/
secret/auth/bearer" line in `config.yaml` too — all six hits are prose about LLM context-window
*tokens*, not credentials.

**This does NOT close known finding C** (`publish.py`'s `sync_tree()` bulk-copies `src/`,
`prompts/`, `reference/`, `registry_terminal/`, `handoff/`, `config.yaml` with **zero content
scrubbing**, while only `state.json` goes through `_scrub()`; the module docstring's "carries no
keys" reads as if it covered the whole synced tree, and it doesn't). The tree is clean *today*;
nothing prevents a future edit from putting a credential into a synced file, since only
`state.json` is defended. `[KNOWN — item C, NEXT_STEPS §2]`.

## SPECIAL ITEM 2 — `name_rc()` VERDICT (`overnight.py:392-436`, written by run #24)

**VERDICT: CORRECT for the case it exists to name.** VERIFIED live (all three claims below
actually executed on this machine, not inferred):

1. `subprocess.Popen.terminate()`/`.kill()` on Windows call `_winapi.TerminateProcess(handle, 1)`
   — confirmed by reading the live `subprocess` source (`inspect.getsource`). Matches
   `known[1]`.
2. `os.kill(pid, signal.SIGTERM)` — the actual mechanism `foreman.py:378,449,519` uses for a
   stalled-job kill (`foreman.py` does **not** import `psutil` at all — checked, zero hits) —
   was executed against a live spawned child on this machine and produced
   `subprocess.returncode == 15`. Matches `known[15]`.
3. `TerminateProcess(handle, -1)` (via raw `ctypes`, exit code passed as `c_uint(0xFFFFFFFF)`)
   against a live spawned child produced `subprocess.returncode == 4294967295` (Python's
   `int`, unsigned, exactly as `NEXT_STEPS.md` and run #23/#24 described — **not** a native
   `-1`). Then:
   ```
   overnight.name_rc(4294967295) -> "rc=4294967295 (TerminateProcess(-1) from OUTSIDE this
   supervisor -- not a remedy (those are 15) and not a python crash (those are 1))"
   overnight.name_rc(-1)         -> the identical classification text
   ```
   confirmed by direct import and call. The unsigned-wraparound arithmetic
   (`signed = rc - (1<<32) if rc >= (1<<31) else rc`) is correct and handles both the raw
   unsigned DWORD Windows actually returns and an already-signed `-1` identically. Also spot
   checked against real NTSTATUS crash codes (`STATUS_ACCESS_VIOLATION`,
   `STATUS_CONTROL_C_EXIT`, two unnamed `0xC0000009`/`0xC00002BD` codes, and ordinary small
   codes 0/1/2/9009) — every one classified as expected, including the "UNRECOGNISED" fallback
   for codes with no entry. **No mis-naming found.**

Two minor issues found on top of the core verdict, both new:

- **`overnight.py:410` — docstring misattributes the mechanism.** `"15 psutil's kill() on
  Windows terminates with the signal number -- a foreman remedy"` — but `foreman.py` never
  imports `psutil` (verified: `grep -n "^import\|import psutil" src/foreman.py` — no hit), and
  every stalled-job kill in the tree (`foreman.py:378,449,519`) uses `os.kill(pid,
  signal.SIGTERM)`. The *number* `name_rc()` reports for `rc=15` is still correct — VERIFIED
  live that `os.kill(pid, signal.SIGTERM)` on Windows also yields `returncode == 15` — but the
  comment names the wrong API as the cause. Lens 6 (comment contradicts code). **VERIFIED.**
  Low severity: no functional impact, just a misleading trail for the next person chasing an
  `rc=15`.
- **`overnight.py:432-436` — asymmetric handling of an already-signed NTSTATUS input.** The
  `if rc >= 0xC0000000:` catch-all (line 434) that prints "unnamed Windows NTSTATUS crash code"
  tests the *original* `rc`, not `signed`. A code arriving as an unsigned DWORD (which is what
  this codebase's Windows subprocesses actually produce — verified above) is caught correctly.
  But if some future caller ever passed an already-negative NTSTATUS not in the `known` dict
  (e.g. a raw `-1073741824` that isn't one of the four listed), it falls through to the generic
  "UNRECOGNISED exit code" branch instead of the NTSTATUS branch, because a negative number is
  never `>= 0xC0000000`. Traced, not exercised against a real process (no such caller exists
  today — every `p.returncode` this file reads comes straight from `subprocess`/`Popen.wait()`,
  confirmed unsigned). **UNVERIFIED as a live bug — currently unreachable given how `rc` always
  arrives in this codebase — but the function is not symmetric on its own terms.** Low severity.

## SPECIAL ITEM 3 — reader downtime measurement (`overnight.py:372-389`, `:704-712`)

**Measured worst case: up to 6 hours**, unchanged from run #24, reconfirmed against the current
main-lap code path (line numbers shifted ~47 lines from run #24's citation because `name_rc()`
was inserted above):

- `STANDING` (`overnight.py:372-380`) — the keeper's every-5-minute re-assert roster — lists
  `dashboard`, `publish`, `foreman`, `overwatch`, `pipeline`. **`read.py` is not in it.**
- The main lap (`overnight.py:704-712`) runs, in strict sequence, inside a single-threaded
  `for cycle in range(...)` loop:
  1. `run("read", ..., timeout_h=a.read_hours)` (`:704-706`, default 3.0h) — `run()` calls
     `p.wait(timeout=...)`, which returns **as soon as the child exits**, not after the full
     timeout. So if `read.py` dies (crashes, or is externally `TerminateProcess`'d) at any point
     during its run, `run()` returns almost immediately and the loop moves on — it does **not**
     sit blocked for the remainder of the 3h budget.
  2. `join(roll, timeout_h=4)` (`:707`) — blocks up to **4 hours** waiting for the
     already-backgrounded roll job.
  3. `run("pipeline", ..., timeout_h=2)` (`:711-712`) — blocks up to **2 hours**.
  4. Only after all three return does the loop reach its top again, where `roll = start(...)`
     and then `run("read", ...)` (`:693-706`) restart the reader — and the keeper thread
     (`_keep`, `:556-569`) never touches it in between, because it isn't in `STANDING`.
- So from the instant `read.py` dies to the instant it is next started: **remaining
  `join(roll)` time (up to 4h) + `run(pipeline)` time (up to 2h) = up to 6h**, plus the
  negligible (seconds-to-low-minutes) overhead of `preflight()` and the background job starts at
  the top of the next cycle. This is the exact number `NEXT_STEPS.md §1.5` already carries
  ("measured up to ~6h (roll 4h + pipeline 2h)"). `[KNOWN — reconfirmed at source, current line
  numbers]`.

## SPECIAL ITEM 4 — `coverage_snapshot()`/`preflight()` returncode check

Confirmed at source, current lines `overnight.py:461-475` (`coverage_snapshot`) and `:478-502`
(`preflight`). Both call `subprocess.run(...)` and never inspect `r.returncode` /
the discarded `subprocess.run(...)` result in `coverage_snapshot`. `coverage_snapshot()` loads
`data/COVERAGE.json` unconditionally after the subprocess call returns — if `coverage.py`
crashed, the JSON file is simply whatever was left from the **previous successful run**, and
`coverage_snapshot()` reports it as this cycle's number with no distinguishing mark.
`preflight()` scans `r.stdout` for `"FAIL"` lines regardless of whether `health.py` actually
completed its checks or crashed after printing a partial preamble. `[KNOWN — reconfirmed at
source, current line numbers 461-475 / 478-502 vs. NEXT_STEPS' 414-455]`.

---

## Findings by file

### `src/overnight.py` (766 lines, read whole)

- **`:410` — `name_rc()` docstring misattributes SIGTERM-15 to "psutil's kill()"** when the
  actual mechanism is `os.kill(pid, signal.SIGTERM)` in `foreman.py`; no `psutil`-based kill
  exists anywhere in `src/`. Numeric classification still correct (VERIFIED, see Special Item
  2). **VERIFIED, low severity, NEW.**
- **`:434-436` — NTSTATUS catch-all is asymmetric** for an already-signed input outside the
  `known` dict; unreachable today because every real `rc` in this codebase arrives unsigned
  (VERIFIED). **UNVERIFIED as live, low severity, NEW.**
- **`:372-389` / `:704-712` — read.py downtime up to 6h.** `[KNOWN, reconfirmed]`, see Special
  Item 3.
- **`:461-502` — `coverage_snapshot()`/`preflight()` ignore subprocess `.returncode`.** `[KNOWN,
  reconfirmed]`, see Special Item 4.
- Everything else read clean: `running()`'s self-exclusion semantics, `run()`/`start()`/`join()`
  append-not-truncate logging, the `_keep` and `_keep_warm` daemon threads, `tail()`,
  `write_status()`, and `main()`'s idle-cycle halt logic all do what their (extensive) comments
  say they do. No new correctness bugs, no new swallowed-failure, no new cap.

### `src/publish.py` (379 lines, read whole)

- **Secret scan: CLEAN.** See Special Item 1. `[KNOWN result, re-verified]`.
- **`sync_tree()` zero-scrub of the synced tree vs. the docstring's "carries no keys".** `[KNOWN
  — item C]`.
- **`:261-263` (`render_page()`'s direct `open(PAGE,"w")`) and `:283-290` (`write()`'s
  `STATE_JSON + ".tmp"`, not PID-qualified, then `os.replace` with no retry)** — both are
  non-atomic / non-PID-qualified writes into a tree `push()`'s own docstring says has **two
  concurrent writers** ("the standing loop and whatever session is working"). `[KNOWN —
  "Non-atomic shared writes still open" list]`.
- `export_root()`, `_is_throwaway()`, `git()`'s credential-shedding, `push()`'s fetch-rebase-first
  logic, `main()`'s loop — all read correct and matched their extensive commentary. No new
  findings.

### `src/zfighters.py` (486 lines, read whole)

- **`:478` — `silence.write_json(OUT, out, ...)` return value ignored.** `write_json()` returns
  `False` on a persistent lock (confirmed by reading `silence.py:250-287`'s docstring and
  `replace_retry`'s 5-attempt-then-give-up contract, then **VERIFIED live**: held a lock on a
  target file and called `silence.write_json` against it — returned `False` after ~3s of
  retries, target left unchanged). `zfighters.py:main()` does not check the return; it
  unconditionally prints `"-> " + OUT` (`:480`) as though the write landed, on a file
  (`data/Z_FIGHTERS.json`) the module's own comment (`:476-477`) says `pantheon.py` reads. This
  is the exact pattern `NEXT_STEPS.md §3` already generalises ("audit every ignored `write_json`
  return in the tree") but is not one of the three examples it names — a fourth instance.
  **VERIFIED, NEW.**
- **`:434-440` — Goku silently drops from the roster on any `REFERENCE_ASSAYS_PRESENCE.json`
  load failure.** `[KNOWN]`.
- The 15 hand-built assay sheets, `compute()`, `value()`, and `main()`'s ranking/printing logic
  read correct; no arithmetic or truncation issues.

### `src/context_budget.py` (278 lines, read whole)

**CLEAN.** Re-verified the derived-budget arithmetic end to end: `content_budget_chars()`
correctly charges scaffolding at the measured prose ratio and converts the remaining token
budget back to characters at the pessimistic content ratio; `feats_block_budget()`'s
`JOB_OVERHEAD_CHARS`/`METADATA_INFLATION` corrections are applied in the right order and the
right direction (both shrink the budget, never widen it); `assert_fits()` raises rather than
clamps. No caps, no swallowed-failure-as-success, no docstring/code mismatch found. Matches
run #24's own "found CLEAN" list — independently reconfirmed this run, not merely copied.

### `src/wh40k.py` (238 lines, read whole)

- **`:230-231` — `with open(OUT, "w", ...): json.dump(out, f, ...)`** — a bare truncate-then-fill
  on `data/WH40K_ASSAYS.json`, not routed through `silence.write_json` the way `zfighters.py`'s
  equivalent write was (that file's own comment at `:476-477` cites "the m100 tail,
  2026-08-25" as the reason it *was* fixed — `wh40k.py` was not). `[KNOWN — exact line match in
  the "Non-atomic shared writes still open" list]`.
- The five hand-built Chaos God / Emperor sheets, `compute()`, and `main()`'s ranking read
  correct. No other findings.

### `src/recover_folder_records.py` (172 lines, read whole)

- **`:149-151` and `:156` — both `silence.write_json()` calls' return values are ignored,
  and on a failed record write the roll is still updated as if it landed.** Concretely: line
  149 writes the record file and, whether or not it succeeded, lines 150-151
  unconditionally set `roll_entry["entry_count"] = len(entries)` and
  `roll_entry["status"] = "catalogued"` in the in-memory roll dict; that dict is then
  persisted to `data/SWEEP_ROLL.json` at line 156 (also an unchecked `write_json` call). So a
  transient lock on one record file (a real possibility — `data/records/` is read concurrently
  by `dashboard.py`, `standards.py`, `pipeline.py`) does not just silently drop that one record;
  it leaves `SWEEP_ROLL.json` **positively asserting** a nonzero `entry_count` and
  `status:"catalogued"` for a source whose record file was never actually written — worse than
  the status quo the script exists to fix (**100 sources showing `entry_count: 0` while flagged
  `catalogued`**, per the module's own docstring), because now the roll is lying about a
  specific count instead of being honestly zero. **VERIFIED**: reproduced `write_json`'s
  false-return behavior live (see zfighters.py finding above — same contract, same module); the
  absence of any `if not silence.write_json(...):` guard in this file is directly visible in the
  source. This is a genuinely new consequence beyond the already-known
  bypass-of-`write_record_catalogue` issue (which is about *merge semantics*, not about *silent
  write failure*). **NEW, VERIFIED, and higher severity than the other findings this batch** —
  it can make `SWEEP_ROLL.json` actively wrong rather than merely stale.
- **`:143-150` — bypasses `pipeline.write_record_catalogue`'s merge**, writing straight to
  `data/records/*.json`. `[KNOWN — flagged in the module's own "NOTE FOR REVIEW" comment and in
  NEXT_STEPS §3]`.
- `slug()`, the `EXCLUDED_REGISTER_SOURCES` denylist (`"ME"`), and the `--dry-run` reporting
  logic all read correct.

### `src/resonance.py` (149 lines, read whole)

- **`:71-79` — fixed 600-iteration Gauss-Seidel with no convergence check.** `[KNOWN]`.
- **`:141,146` — `resonance_strength()` reads `data/SHARED_STAGE_GRAPH.json`** (built by
  `cosmology_graph.py`, whose `pair_shared` is capped at 8 — Hard Rule 0), consuming
  `shared_sample` as real evidence, while `weave.py` fixed this exact cap but wrote its result
  to a *different* file (`SHARED_STAGE_GRAPH_IDF.json`) this module never reads. `[KNOWN — item
  F]`.
- **NEW, low severity: `:74-76` — `if not nbrs[n]: continue` is unreachable dead code.**
  `nodes = sorted({n for e in edges for n in e})` — every node in `nodes` by construction
  appeared in at least one edge, and the very next loop (`for (a,b), f in edges.items(): nbrs[a
  ].append(...); nbrs[b].append(...)`) populates `nbrs` for exactly those same nodes. So every
  `n` in `nodes` is guaranteed to have a non-empty `nbrs[n]`. **VERIFIED**: instrumented the
  identical logic against a 3-edge test graph and confirmed `any(not nbrs[n] for n in nodes)` is
  `False`. Lens 8 (a check that cannot fail). No functional impact — the branch, if it could
  fire, would do the right thing (`new[n] = theta[n]`) — but it never will, and its presence
  currently reads as defensive coverage that does not exist.
- `dominates()`, `incomparability_rate()` (iterates ALL pairs via `itertools.combinations`, no
  cap) read correct.

---

## Modules read end to end and found CLEAN this batch

`context_budget.py` — zero findings, new or known, on this independent re-read.

(All other six files in this batch have at least one finding, new or KNOWN, listed above.)
