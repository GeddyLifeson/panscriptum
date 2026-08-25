# Batch 05 Audit — run32

Modules read in full, every line:

| file | lines |
|---|---|
| src/cascade_bridge.py | 1226 |
| src/gpu_lane.py | 479 |
| src/address_space.py | 346 |
| src/navtree.py | 272 |
| src/autostart.py | 218 |
| src/catalogue_models.py | 176 |
| src/compress_store.py | 65 |

---

## KNOWN LEAD 1 — cascade_bridge.py dead-provider bench: PER-PROCESS, confirmed

`cascade_bridge.py:158-160`:
```python
_DEAD = {}
_STRIKES = {}
_DEAD_LOCK = threading.Lock()
```
These are plain module-level dicts, mutated by `_bury()` (line 693), `_clear()` (line 712), and
read by `_alive()` (line 676). `_DEAD_LOCK` is a `threading.Lock()` — it serialises threads
*inside one interpreter*, nothing more. Nothing here is written to disk, to the shared SQLite
scratch DB, or to any other cross-process channel. `dead_buckets()` (line 719) reads the same
in-memory dict.

**Consequence, VERIFIED by reading the code (not benchmarked here):** every one of the ~15
standing Panscriptum processes that imports `cascade_bridge` builds its own empty `_DEAD` at
import time and has to independently accumulate strikes against `zai:free`, `cohere:free`,
`cloudflare:free`, `hyperbolic:free` before any of *its own* calls stop landing on them. A
process that starts fresh (or restarts) re-learns all four from zero. Because `FIRST_BENCH=60s`
graded up to `MAX_BENCH=900s` (15 min) per-strike, and 15 processes never see each other's
strikes, the pool-wide call rate against a dead provider does not fall the way the single-process
bench model assumes — this is the mechanism behind "~40x/hour with zero successes" the lead
describes.

**What sharing would take, concretely:** the plumbing to do this already exists in this same
file and is unused for this purpose. `SCRATCH_DB` (`state/cascade_scratch.db`, cited at line 355)
already carries a `bucket_state` table with `last_error`/`updated_at`, read cross-process by
`provider_error()` (line 474-501) via a read-only SQLite connection. `_DEAD`/`_STRIKES` do not
write there — they would need either (a) a write into that same table (adding a `benched_until`
column, one INSERT/UPDATE per `_bury`), or (b) a small shared JSON file in the style of
`UNRECOGNISED`/`POOL_PROOF.json`, written via `silence.write_json`. Neither exists today. **Not
changed — audit only, per instructions.**

Severity: **MAJOR**. Confirmed mechanism, no fix applied.

---

## KNOWN LEAD 2 — address_space.py:251-252 — CONFIRMED, contract violation

```python
def fit(v, field):
    return (0 if v is None else int(v)) % (1 << WIDTHS[field])
```
`pack()` (line 145-159) explicitly raises `ValueError` for any field value that doesn't fit its
bit width, with its own docstring stating the reason: *"Raises rather than truncating: a silently
wrapped address would name a different world, which is the one failure mode worth being loud
about."* `assign()` (line 240-261) calls `pack(fit(tiers.get("hyperverse"), "hyperverse"), ...)`
for the four charted tiers. Because `fit()` pre-wraps every value into range with `%`, `pack()`'s
raise branch can **never fire** for any value that reaches it through `assign()` — out-of-range
tier data from `TIERS.json` (stale, corrupt, or grown past the widths computed at import time in
the module-level `_TC = _tier_counts()` / `WIDTHS`) is silently remapped to a different, valid,
*wrong* hyperverse/xenoverse/metaverse/multiverse index instead of raising.

This directly defeats the stated guarantee, and it is the exact failure the file's own docstring
calls out as the one to avoid: a truncated/wrapped address "names a different world."

**Compounding staleness risk:** `WIDTHS` is computed once at import (`_TC = _tier_counts()`,
line 119), from whatever `TIERS.json` looked like at that moment. `main()` re-reads
`TIERS.json` fresh later (line 316-322) before calling `assign()`. If `TIERS.json` grows (more
hyperverses/xenoverses charted) between those two reads within a long-lived process, `fit()`'s
modulo against the now-stale, too-narrow `WIDTHS` silently wraps legitimately-new indices into
existing ones — same defect, reached by staleness rather than corruption.

Severity: **BLOCKING**. This is a silent data-corruption path in the addressing system the
charter treats as authoritative, and it is trivially reachable by a data file that simply grows.

---

## KNOWN LEAD 3 — navtree.py:254-257 cap — REFUTED (display-only, not a Hard-Rule-0 violation)

```python
problems = audit(data)
print(f"\nAUDIT: {len(problems)} problems")
for p in problems[:6]:
    print("   " + p)
...
if args.write and not problems:
    silence.write_json(OUT, data, ...)
```
The `[:6]` at line 256 only limits how many problem lines are echoed to the console. The write
gate at line 259 (`if args.write and not problems`) tests the **full, untruncated** `problems`
list — so a run with 7+ real problems still correctly refuses to write `NAVTREE.json`, it just
doesn't print all 7+ of them to the terminal. No roster, world list, or persisted record is
truncated: the earlier text in the same file explicitly states worlds are listed with "No cap: a
universe lists every world it holds" (line 99), and that holds — verified by reading the `build()`
loop, which appends every world in `worlds.items()` with no slicing anywhere.

Severity: **NOTE**. Confirmed safe; recommend closing this lead.

---

## KNOWN LEAD 4 — gpu_lane.py "1 of 16 permits" — deliberate design, and not actually in this file

`gpu_lane.py`'s own permit count is `MAX_SLOTS` (line 66-67):
```python
MAX_SLOTS = max(1, int(os.environ.get("PANSCRIPTUM_GPU_SLOTS")
                       or os.environ.get("OLLAMA_NUM_PARALLEL") or "2"))
```
This defaults to **2**, not 16, and is documented (lines 61-65) as deliberately tied to Ollama's
own `OLLAMA_NUM_PARALLEL` daemon setting — "one physical fact, read rather than restated." The
"1 of 16" framing in the lead belongs to a **different** gate: `read.py`'s `GATE_LOCAL_N` (=2,
same physical constant) vs `GATE_CLOUD_N` (=16) — confirmed via grep (`src/read.py:284-285`,
`src/standards.py:486,516-528`, `src/verify_math.py:2298-2358`), none of which is in this batch.
`read.py` is not one of the seven files assigned to batch 05, so I cannot audit its permit logic
directly under this task's scope — flagging this explicitly rather than guessing at a file I was
not asked to read.

Within **this** file, `gpu_lane.lane()` throttles only **local** Ollama calls: confirmed by
grep, the only importers are `generate.py` (line 156, `priority=True`), `local_agent.py` (line
586), `pipeline.py` (line 373 — wraps a direct `POST .../api/generate` to `c["ollama_host"]`,
i.e. local Ollama only), and `overnight.py` (busy-check only). `cascade_bridge.py` — the cloud
router — never imports `gpu_lane` (confirmed by grep across `src/`). So gpu_lane.py does **not**
throttle "the whole pool" (cloud+local); it throttles only the local GPU leg, which is exactly
what its own header says it's for. Whether `read.py`'s separate 2-vs-16 regime causes accidental
starvation is a question for whoever audits `read.py`, not answerable from this file alone.

Severity: **NOTE** — lead is about a file outside this batch; gpu_lane.py itself is correctly
scoped to local-only arbitration and MAX_SLOTS=2 is deliberate, documented, and tested
(referenced by `verify_math.py`'s concurrency checks).

---

## Other findings, this batch

### gpu_lane.py:256, gpu_lane.py:310 — `silence.replace_retry` return value discarded — SUSPECTED, MINOR-MAJOR

```python
silence.replace_retry(tmp, path)   # _write_claim, line 256 — return value not checked
...
silence.replace_retry(tmp, path)   # _touch, line 310 — return value not checked
```
`replace_retry` returns `False` on persistent failure (after retries) without raising — the
target file is **not** updated and the temp file may be left behind. `_write_claim`'s own
in-file comment (lines 250-255) names this exact risk for a *new* foreground claim: "a dropped
first write means the claim never appears, so every background call proceeds straight through
the yield this file exists to enforce" — and then the code makes no use of the return value to
detect or react to that outcome (it doesn't retry the whole claim, verify via a follow-up read,
or escalate beyond the internal `note()` `replace_retry` already fires on its own last attempt).
This is consistent with the module's declared "fail open, always" philosophy (a missed claim
just means background work isn't held back — never a hang), so I'm not calling it a correctness
bug outright, but it is exactly the discarded-return-value shape the sweep is watching for, and
the module's own comment demonstrates the author was aware of the risk without instrumenting
against it. `_touch`'s temp file (`path + "." + pid + ".tmp"`, line 307) is also not cleaned up
if `replace_retry` fails persistently — a low-volume leak in `state/gpu_lane/` on repeated
Windows rename denials.

Severity: **MINOR** (behavior matches the module's explicit fail-open design; flagged because it
matches the exact pattern named in the audit brief and the file's own comment identifies the gap
without closing it).

### catalogue_models.py:158 — `[:10]` cap reintroduced in the console summary — CONFIRMED, MAJOR

```python
stale.append({"provider": name, "wants": a, "available_sample": list(r["models"])})  # line 151, full list, fixed per comment
...
print(f"  {name}: " + ", ".join(r["models"][:10]))   # line 158, capped again
```
The comment at lines 146-150, directly above the `stale.append` at line 151, documents that an
earlier `[:8]` cap on `available_sample` was removed as a Hard Rule 0 violation ("if the
provider's ninth model was the right substitute, nothing that consumed this record could see
it" — run #26). That fix is real: `available_sample` now holds the **full** model list, and it
is written unabridged to `data/PROVIDER_MODELS.json` via `silence.write_json` (line 162).

But eleven lines below its own fix comment, in the same function, the **console** print under
"Current alternatives, per provider:" re-caps the exact same `r["models"]` list to 10 entries.
This is the human-facing summary the docstring says exists so "a stale entry is visible... rather
than [read] as a provider that stopped working" — i.e., the same field the fix comment says a
person reads to pick a replacement model. A provider with more than 10 models whose correct
replacement is alphabetically past the 10th is invisible in the interactive summary, even though
the full list is recoverable from the JSON file on disk. Not pure display formatting in the
sense Hard Rule 0 exempts (a truncated row count or a preview index) — this is the actual
decision-support data a person reads at the terminal to choose a substitute model, capped right
next to a comment asserting that exact cap was removed.

Severity: **MAJOR**. Persisted data (`PROVIDER_MODELS.json`) is NOT capped — only the console
echo is — so no data loss to disk, but the cap reappears in the one place a human is most likely
to actually look during interactive use, undermining the stated purpose of the earlier fix.

### compress_store.py:43-44 — non-atomic write to a content-addressed shared path — SUSPECTED, MINOR

```python
with open(path, "wb") as f:
    f.write(blob)
```
No temp-file staging, no `silence.write_json`/`silence.replace_retry`. Every other shared-state
writer encountered in this batch (`gpu_lane.py`, `navtree.py`, `catalogue_models.py`,
`address_space.py`, `cascade_bridge.py`) routes writes to files other processes may read
concurrently through `silence.write_json` or `silence.replace_retry` specifically to avoid
partial-read races and Windows rename-denial. `compress_store.store()` writes directly to the
final content-addressed filename. Because the filename is a content hash, two writers racing on
the *same* hash are writing byte-identical output (deterministic compression at a fixed level),
so this cannot silently corrupt a read the way a shared JSON ledger could — but a concurrent
`load()` opening the same path mid-write from another process can still read a truncated blob and
raise a decompression error mid-run (fails loud, not silent, but avoidable).

Severity: **MINOR**. Fails loud rather than silently, but is the one writer in this batch that
doesn't follow the codebase's own established two-writer contract.

### cascade_bridge.py:1119 — `ready[:12]` in `selftest()` — NOTE, not a violation

`for lab in ready[:12]:` only limits a diagnostic console preview inside `selftest()` (manual
`python cascade_bridge.py` invocation); it does not affect `pools()`, `cloud_buckets()`,
`widen_candidates()`, or any function that decides which buckets are actually claimable — all of
those iterate `_ROUTER.models`/`_ROUTER.candidates()` in full, no slicing anywhere. Pure display
formatting; compliant with Hard Rule 0's stated exception.

### address_space.py:333 — `list(addrs.items())[:6]` in `main()` — NOTE, not a violation

Console preview of 6 example shelfmarks inside `main()`'s printed report. The actual write to
`data/SHELFMARKS.json` (lines 335-340) serializes the **full** `addrs` dict, every catalogued
world, via `silence.write_json`. Confirmed not truncated on disk.

### gpu_lane.py — re-entrant foreground-claim depth counter — NOTE, latent race, not currently triggered

`foreground()` (line 219-239) implements re-entrancy via a non-atomic read-modify-write on a
JSON file's `depth` field (`rec = _read(path); depth = rec["depth"]+1; _write_claim(...)`, and
symmetrically on exit). If two *threads within the same process* both called `gpu_lane.lane(...,
priority=True)` concurrently, this depth counter could lose an update (classic TOCTOU: both
threads read depth=0 before either writes depth=1), causing an early claim removal while one
caller still believes it holds the foreground. Checked callers: `generate.py` is the only
`priority=True` call site in the tree (confirmed by grep) and is single-threaded (no
`threading`/`ThreadPoolExecutor` usage found in `generate.py`), so this is not currently
reachable. Flagged as a latent hazard should a future caller parallelize foreground work.

### cascade_bridge.py — no other correctness bugs found

Read the rest of the file closely for the specific items the brief called out: `_extract_json`'s
brace-matching retry loop is correct (verified the nested-depth accounting and the retry-next-`{`
behavior on parse failure); `record_unrecognised`/`unrecognised_open` use `silence.write_json`
correctly (not hand-rolled tmp+replace) and the key-folding/case fix is sound; `_bury`/`_clear`/
`_alive` are internally consistent; the `ask()`/`_ask_call` split, the `pin` fast-path, the widen
fallback with locked round-robin rotation, and the auth-vs-transient-vs-unrecognised
classification cascade in the failure branch (lines 981-1096) are logically consistent with their
extensive inline documentation — no contradiction between comment and code found. `dead_forever()`
correctly keys its cache on the proof file's mtime rather than process lifetime (the fix it
documents). No swallowed exceptions found beyond the sanctioned `silence.note()` pattern.

### navtree.py, autostart.py — no correctness bugs beyond the items above

`navtree.py`'s `audit()`, `sources_under()` (m11 fix verified correct), and `register_for()`/
grounding tie-breaks (m41 fix verified deterministic) are all sound on inspection.

`autostart.py`: `start_supervisor()` (lines 103-118) opens `out`/`err` log file objects that are
handed to `Popen` as stdout/stderr but never explicitly closed by the parent afterward — a minor
file-handle leak in the long-running `watch()` loop (line 148-179) if the supervisor is
crash-looping (each restart leaks 2 handles). Severity: **MINOR**, only manifests under repeated
crash-restart cycles. `_twin_watchdog()` (line 121-145) has a narrow TOCTOU at simultaneous
process startup (no lock file, just a WMI process-list snapshot) — plausible only at
near-simultaneous boot-time launch of more than one watchdog; the file's own comment describes
this exact scenario as a past incident this function was written to prevent, and it reduces but
does not fully eliminate the race. Severity: **NOTE**.

---

## Summary table

| finding | file:line | severity | status |
|---|---|---|---|
| Dead-provider bench is per-process, not shared | cascade_bridge.py:158-160 | MAJOR | VERIFIED |
| `fit()` modulo-wraps out-of-range tiers, defeating `pack()`'s raise guarantee | address_space.py:251-252 | BLOCKING | VERIFIED |
| `[:6]` audit-problem print cap | navtree.py:256 | NOTE | REFUTED (display-only, gate uses full list) |
| "1 of 16" GPU semaphore | gpu_lane.py (whole file) | NOTE | Lead belongs to read.py, outside batch; gpu_lane's own MAX_SLOTS=2 is deliberate/local-only |
| `silence.replace_retry` return value discarded | gpu_lane.py:256, 310 | MINOR | SUSPECTED (matches fail-open design, but risk named unaddressed in own comment) |
| `[:10]` cap reintroduced in console summary next to its own fix comment | catalogue_models.py:158 | MAJOR | CONFIRMED |
| Non-atomic write to shared content-addressed path | compress_store.py:43-44 | MINOR | SUSPECTED |
| `ready[:12]` diagnostic preview | cascade_bridge.py:1119 | NOTE | Not a violation (display only) |
| `list(addrs.items())[:6]` diagnostic preview | address_space.py:333 | NOTE | Not a violation (full data written to disk) |
| Re-entrant foreground depth counter race | gpu_lane.py:219-239 | NOTE | Latent, not currently reachable (no concurrent priority=True callers found) |
| Unclosed log file handles on supervisor restart | autostart.py:111-112 | MINOR | SUSPECTED, crash-loop only |
| Twin-watchdog boot-time TOCTOU | autostart.py:121-145 | NOTE | Narrow race, already partially mitigated |
