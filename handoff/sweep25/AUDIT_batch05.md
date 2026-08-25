# Sweep #25 — Batch 05 audit

Files (read every line, no sampling): `src/read.py` (1135), `src/identity.py` (423),
`src/worldseed.py` (327), `src/grounding.py` (245), `src/coverage.py` (191), `src/catalog.py` (127).
Total 2,448 lines.

Cross-referenced against `NEXT_STEPS.md` §3 (run #24 findings) before filing anything as new.

---

## PART 0 — THE `read.py` `TerminateProcess(-1)` MYSTERY (top priority)

**VERDICT: nothing in `src/` can produce this exit code. Proven by direct experiment, not
inference — the search should now move outside the repo.**

### What was searched

`grep -rn -i "TerminateProcess|taskkill|\.kill(|os\.kill|SIGTERM|SIGKILL|CREATE_NEW_PROCESS_GROUP|
JobObject|CTRL_BREAK"` across all of `src/*.py`, plus a separate grep for raw `ctypes`/`windll`
usage. Every kill-adjacent site in the tree:

| Site | Mechanism | What it actually produces |
|---|---|---|
| `overnight.py:196` `p.kill()` (on `subprocess.TimeoutExpired` in `run()`) | `Popen.kill()` | **VERIFIED: returncode 1** (see experiment below) |
| `overnight.py:259` `job["proc"].kill()` (on `TimeoutExpired` in `join()`) | `Popen.kill()` | **VERIFIED: returncode 1** |
| `foreman.py:378,449,519` `os.kill(pid, signal.SIGTERM)` | `os.kill` + SIGTERM on Windows | **VERIFIED: returncode 15** (also independently proved by the repo's own `verify_math.py:3036-3057`, re-run and confirmed) |
| (no site) `psutil.Process.kill()` | not used anywhere in `src/` (only mentioned in an `overnight.py` comment) | **VERIFIED anyway, to check the comment's own claim: returncode 15**, matching `overnight.py:410`'s documented `name_rc()` table |
| (no site) `taskkill /F` | not used anywhere in `src/` | **VERIFIED for completeness: returncode 1** |
| (no site) raw `ctypes` `TerminateProcess` | not used anywhere in `src/` — `gpu_lane.py:127-148` is the only `ctypes`/`windll` use in the tree and it only *reads* exit status via `GetExitCodeProcess`, never terminates | N/A |

### The experiments (all run against this machine's actual Python/Windows, VERIFIED)

```
Popen.kill():                    returncode 1
taskkill /F /PID <pid>:          returncode 1
psutil.Process(pid).kill():      returncode 15
raw TerminateProcess(h, 0xFFFFFFFF) via ctypes:  returncode 4294967295   <- matches the mystery exactly
```

The last experiment confirms the *mechanism* the supervisor's own comment describes
(`overnight.py:412`, "`TerminateProcess(handle, -1)` by something OUTSIDE this supervisor") is
mechanically correct and reproducible — but it requires an explicit, deliberate
`TerminateProcess(handle, 0xFFFFFFFF)` call, and **no such call exists anywhere in `src/`**. Every
kill path this codebase actually uses (`Popen.kill()`, `os.kill(pid, SIGTERM)`) lands on 1 or 15,
never -1.

### Read.py's own child-process handling

`read.py` does not spawn, manage, or kill any child process at all — no `subprocess`, no
`os.kill`, no thread/process pool teardown that touches an external PID. Its only concurrency
primitives are `threading.Lock`, `threading.BoundedSemaphore`, and `threading.local` (all
in-process). It cannot kill its own tree because it has no tree to kill. `main()` returns 0 on
every path (`--one`, `--run`, or the help text), matching the brief's premise exactly.

### Conclusion

**Proven negative.** The -1 is not `Popen.kill()`, not `os.kill(SIGTERM)`, not `psutil.kill()`,
not `taskkill /F`, not any code in `read.py` itself, and there is no raw `ctypes.TerminateProcess`
call anywhere in the tree that could emit it deliberately. The search should move to: (a) Norton
or another AV/EDR product force-terminating the process (this machine's known TLS-interception
history makes Norton a live suspect per `MEMORY.md`), (b) an external Job-Object teardown from
whatever launches `overnight.py` itself (no Job Object code exists inside this repo — `overnight.py`
and `foreman.py` never call `CreateJobObject`/`AssignProcessToJobObject`, only plain
`CREATE_NO_WINDOW`), or (c) console-control-event propagation: `overnight.py:187` and `:238` spawn
`read.py` with only `CREATE_NO_WINDOW` (no `CREATE_NEW_PROCESS_GROUP`/`DETACHED_PROCESS`), so if
the supervisor's own console/session is torn down externally, `read.py` shares that console group
and could be swept up in whatever Windows does by default on a console close — this is
**UNVERIFIED** (could not safely simulate a console-close event from this tool) but is the one
candidate consistent with "not this repo's own kill code."

---

## PART 1 — Findings

### `coverage.py:16-18` vs `:82-115` — `UNREACHABLE` promised, never implemented [KNOWN]

Docstring (lines 16-18):
```
UNREACHABLE  a host exists but the fetch failed -- the only state that is purely a defect
```
`state_of()` (lines 82-115) only ever returns `"NO HOST"` (line 85), `"CITED"`/`"READ"` (lines 107,
111-114), or the `best` default of `("NO PAGE", 0, 0)` (line 87) when nothing was found. There is
no code path that returns `"UNREACHABLE"` anywhere in the module. Worse, the `except Exception:`
at lines 102-104 (a corrupt/unreadable evidence file) does `silence.note(...); continue` — the
loop just tries the next `base` and, failing both, falls through to the `"NO PAGE"` default. A
transient read failure is therefore indistinguishable from genuine absence, exactly as the
docstring's own contrast (line 20-21) says must never happen. Matches NEXT_STEPS §3 verbatim.
**VERIFIED** (read at source, confirmed by tracing every `return` in `state_of`).

### `read.py:1097-1098` — "done" summary omits `unanswered`/chunks/`_FELL_BACK` [KNOWN]

```python
print("done in %.2fh  %d feats kept, %d fabrications dropped"
      % ((time.time() - t0) / 3600, done["feats"], done["fab"]))
```
`done["unanswered"]`, `done["chunks"]`, `done["skipped"]`, and `_FELL_BACK[0]` are all tracked
throughout `run()` (used in the per-5-entity progress line at lines ~1015-1024) but none appear in
the final banner. A run where every single chunk went unanswered (pool exhausted + GPU benched)
still prints "done in 3.10h  0 feats kept, 0 fabrications dropped" — indistinguishable from a
healthy run over a corpus that genuinely has zero feats. Matches NEXT_STEPS §3 verbatim.
**VERIFIED** (read at source; the progress-line format string two hundred lines earlier proves the
data was available and simply not carried into the closing line).

### `identity.py:180-207` — `_is_continuity()`'s own worked example can never classify [KNOWN]

The docstring's own example: `"(Revelation) shares no bearers yet and is still plainly a
continuity, so branching cannot be required — only sufficient"` (lines 194-196) describes a
designator with `shared=0` and (per "shares no bearers yet") effectively one attested bearer. But
the code (lines 205-207):
```python
if n >= MIN_BEARERS:        # MIN_BEARERS = 3
    return True
return n >= 2 and shared >= max(2, 0.5 * n)
```
requires `n >= 2` on the branching path — a single-bearer designator with `n=1` fails *both*
branches regardless of `shared`, so the exact case the docstring calls "obviously a continuity"
returns `False`. Matches NEXT_STEPS §3 verbatim. **VERIFIED** by re-deriving the truth table from
the code (n=1, shared=0 → `False` on both conditions).

### `identity.py:291-320` — `epoch_of()` returns `""` for both "no marker" and "call failed" [KNOWN]

`_ask()` (line 291-298) returns `None` on any exception (network, transport, or parse failure).
`_json(None)` (line 301-312) returns `{}`. `epoch_of()` (line 315-320) then does
`if not d.get("explicit"): return ""` — a genuinely absent epoch marker and an outright call
failure both produce the empty string, with no way for `chain.py:407`'s caller
(`ID.epoch_of(sa), ID.epoch_of(sb)`) to tell them apart. Matches NEXT_STEPS §3 verbatim.
**VERIFIED**.

### `worldseed.py:317-322` — direct `open(path,"w")`+`json.dump` on shared `WORLDSEEDS.json` [KNOWN]

```python
path = os.path.join(HERE, "data", "WORLDSEEDS.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump({w["designation"]: {"address": address(w), **w} for w in worlds},
              f, indent=2, ensure_ascii=False)
```
Bare truncate-then-fill on a shared `data/` file, no atomic rename, despite `silence` already
being imported in this exact module (used for `silence.note` at lines 250 and 258). A reader
polling this file (dashboard, catalog build) mid-write sees a truncated/empty file; a crash mid-
dump leaves it that way permanently. Matches NEXT_STEPS §3's "Non-atomic shared writes still open"
list verbatim. **VERIFIED**.

### `coverage.py:185-186` and `grounding.py:239-240` — `silence.write_json` return value ignored, success reported unconditionally [NEW, but same class as the m119/m120 lesson NEXT_STEPS explicitly generalises]

`silence.write_json()`'s own docstring (`silence.py:267-268`): *"Returns True if the file landed.
Never raises on a denied replace."* Its real contract (`silence.py:250-287`, calling
`replace_retry` at `:221-238`): on a **persistent** `PermissionError` (a reader holding the target
open through all 5 retries — the exact Windows collision this project's own comments document
repeatedly, e.g. `silence.py:222-224` citing a 2026-08-23 WinError 5 that took an assay worker
down mid-batch) it returns `False` and the write is silently dropped; the caller is expected to
retry "next round".

Both sites ignore that return and print success unconditionally:

```python
# coverage.py:185-186
silence.write_json(OUT, rows, indent=1, ensure_ascii=False)
print(f"\nper-source table -> {OUT}")
```
```python
# grounding.py:239-240
silence.write_json(p, out, indent=2, ensure_ascii=False)
print(f"\nwrote {p}")
```
`COVERAGE.json` is, per `coverage.py:182-184`'s own comment, read by the dashboard, `standards.py`,
`allsweep.py` and the published page — a silently-dropped write here means all four downstream
readers keep serving the *previous* run's headline coverage numbers while the tool that generated
them reports `per-source table -> ...` as if it succeeded. NEXT_STEPS §3 explicitly calls out this
exact pattern ("`silence.py:250-287` ... every one-shot caller in batch 06 ignores the return ...
the m119/m120 lesson generalises: audit every ignored `write_json` return in the tree") and lists
three other sites (`navtree.py`, `catalogue_codex.py`, `scope.py`) — **these two in this batch are
new instances of that same audited-for pattern, not previously named.**
**VERIFIED** by reading `silence.write_json`'s actual return contract and both call sites.

### `identity.py:219` — fixed, non-PID-qualified tmp filename on `DESIGNATORS.json` [NEW]

```python
tmp = CACHE + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(inv, f, indent=1, sort_keys=True)
silence.replace_retry(tmp, CACHE)
```
This is the exact anti-pattern `read.py`'s own `_chunk_put` was fixed for, described in that
function's docstring (`read.py:596-602`, quoted here for cross-reference): *"This was `p +
".tmp"`, derived only from the cache key, so two workers answering the same passage at once opened
and truncated ONE file... The pid and thread id make the staging file private."* `identity.py`'s
`load(refresh=...)` (lines 210-223) never received that fix — `tmp` is still a bare, unqualified
name shared by every caller. `chain.py:146` calls `ID.load()` (refresh=False by default, so this
only bites on first population before `DESIGNATORS.json` exists, or whenever `--refresh` is passed
manually) — but a first-population race between two concurrent processes that both import
`chain.py` (e.g. `pipeline.py` and a manually-run diagnostic, or two sweep batches) would hit
exactly the collision `read.py`'s own comment describes: the loser's `os.replace` (via
`replace_retry`, which *is* used correctly here) still can't protect against two writers
truncating the *same* tmp file simultaneously before either rename happens.
**UNVERIFIED** — the mechanism is proven (by `read.py`'s own documented 2026-08-2x incident on the
identical shape) and the code is confirmed to have the flaw, but no concurrent collision on this
specific file was reproduced live in this session; flagging as the same class of risk, not a
observed failure.

### `coverage.py:73` — same fixed-tmp-name pattern on `state/coverage_cache.json` [NEW]

```python
tmp = _SO_CACHE_P + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(_SO["d"], f)
_sil.replace_retry(tmp, _SO_CACHE_P)
```
Same shape as the `identity.py:219` finding above, in-scope for this batch. `coverage.py` is
routinely invoked as a standalone diagnostic (NEXT_STEPS §1 item 2's own verification commands are
exactly this pattern: run it ad hoc to check current state while the supervisor may also have a
scheduled invocation in flight). Two concurrent `python src/coverage.py` processes racing to
write `state/coverage_cache.json`'s per-file result cache collide on the shared `.tmp` staging
file before either atomic rename occurs. Lower blast radius than the other findings here — this
cache is purely a speed optimisation (`_SO_CACHE_P` docstring, lines 49-52: "measure() was
deserializing on the order of the whole 874MB corpus per run" — losing an entry just costs a
re-parse, not data loss) — but it is the identical race class the project has fixed elsewhere with
PID+thread-qualified names.
**UNVERIFIED** (mechanism proven elsewhere in this exact codebase; no live collision reproduced
here).

---

## PART 2 — Modules read end to end and found CLEAN this run

- **`catalog.py`** (127 lines, full read) — pure read-only CLI query tool over `output/index/catalog.json`
  and `data/SWEEP_ROLL.json`. No writes anywhere in the file. The one truncation
  (`missing[:30]` at `cmd_stats`, line 64) is an honest display cap that prints `"... and N more"`
  (line 66-67) rather than hiding the count — the pattern this project treats as acceptable
  ranking/display, not a Hard Rule 0 violation. Matches its CLEAN listing in NEXT_STEPS' own §3.
- **`grounding.py`** (245 lines, full read) — aside from the ignored-`write_json`-return finding
  above (a genuinely new, narrow issue), the module is otherwise sound: the `cap` parameter is
  actively *refused* with a loud `SystemExit` (lines 143-147) rather than silently truncating —
  exactly the defensive pattern Hard Rule 0 asks for, and the docstring at lines 128-141 documents
  its own prior cap bug and fix in detail, cross-checked against `genre.classify_source`'s
  sibling bug. `classify_text`/`classify_source` iterate every entry, no sampling.
- **`worldseed.py`** (327 lines, full read) — aside from the KNOWN non-atomic write at
  317-322, the rest of the module is sound: `build_all()` iterates `PL.records()` fully (no
  default cap; `--limit` is CLI-opt-in only and no caller in the tree passes one), the
  Hard-Rule-0 fix at lines 272-279 (matching against the *whole* description rather than the
  first 200 chars) is real and dated, and `_first()`'s seeded-fallback-over-defaulting design
  (lines 103-120) is a deliberate, well-reasoned anti-bias choice, not a bug.

No module in this batch was entirely clean end-to-end (`read.py`, `identity.py`, `coverage.py` all
carry at least one finding above), but all six were read in full per the brief's requirement.
