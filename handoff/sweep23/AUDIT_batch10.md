# Batch 10 audit — rigor.py, gpu_lane.py, reference.py, sevenfold.py, autostart.py, catalogue_aurora.py

Auditor: batch 10 of 16, full line-by-line read of all six files (2,254 lines total).

---

## src/rigor.py (866 lines) — CLEAN

Read in full. This is the commensuration/MDL/statistics module (AHP/Perron, HodgeRank,
Bradley-Terry with Ford's-condition refusal, MDL beta, lognormal Fermi-style uncertainty
propagation, extreme-value ceiling correction, derivation-graph resonance).

Checked specifically for:
- **Hard Rule 0**: `mathematical_resonance()` returns `load_bearing` fully sorted, never sliced
  (rigor.py:720, explicit comment: "Ranked, never truncated (Hard Rule 0)"). The only slicing
  found is `mr["load_bearing"][:6]` inside `main()`'s print block (rigor.py:858) — this is a
  console-preview slice of an already-fully-returned list, not a truncation of persisted or
  returned data. Not a violation.
- **Two-writer contract**: no file writes in this module at all.
- **Swallowed failures**: no bare `except: pass` / broad `except Exception` anywhere in the file.
- **Correctness**: `perron_weights`, `logrank_weights`, `theorem_1_check`, `_strongly_connected`
  (iterative Tarjan over the "i beat j" digraph), `bradley_terry`'s Ford's-condition refusal
  logic (raw wins used for connectivity check, prior-augmented wins used for the MAP estimate —
  correctly kept separate per its own long comment at rigor.py:426-443), `mdl_bits`,
  `_log2_choose`, `adjudication_beta`, `lognormal_product`, `prob_at_least_one`,
  `gumbel_return_level` — all traced and internally consistent with their extensive docstrings.
  No logic bug found.
- **Comment/code contradiction**: none found; this file is unusually self-auditing (its own
  docstrings narrate three prior bugs it previously had and how they were fixed — I checked the
  current code matches the "fixed" state described, e.g. `measure_bit_value` now uses
  `T.band_resolution` not `rung_description_length`, matching its own note at rigor.py:116-124).

No findings to report for this module.

---

## src/gpu_lane.py (480 lines)

### FINDING 1 — HIGH — heartbeat "liveness" cannot detect a wedged-but-alive model call — VERIFIED

This is exactly the failure mode named in the assignment's special focus. Traced the mechanism:

- A held slot/claim is only ever reclaimed by `_expired()` (gpu_lane.py:171-177), which returns
  "expired" iff the heartbeat is stale OR the holder PID is dead.
- The heartbeat is refreshed by a **separate daemon thread**, `_heartbeat()`
  (gpu_lane.py:326-360), started in `lane()` (gpu_lane.py:434-437) and run independently of
  whatever the caller's actual model call is doing inside the `yield` at gpu_lane.py:438. It
  loops `while not stop.wait(_BEAT_SECONDS): touch(...)` and is only stopped when the `lane()`
  context manager's `finally` block runs — i.e., when the wrapped call *returns or raises*.
- If the wrapped Ollama call hangs (wedged runner, no response ever arrives, no exception ever
  raised — exactly the m40/m42/M5 scenario cited in the module's own header), the calling
  process is simply blocked in I/O wait. The heartbeat thread keeps running (Python threads are
  not blocked by another thread's I/O wait) and keeps touching the lease every `_BEAT_SECONDS`
  (~100s here, `min(900,300)/3`). The holder's PID is still alive (it's just stuck). So
  `_expired()` returns `False` forever: heartbeat never goes stale, PID never dies.
- Net effect: a wedged qwen3:8b call holds its GPU slot **indefinitely**, with no ceiling in this
  file at all — `SLOT_LEASE_SECONDS` (900s) is only consulted as (a) the deadline for a *new*
  caller trying to *acquire* a slot, and (b) the staleness threshold compared against a heartbeat
  that keeps renewing. There is no "has this call actually made progress" check, no absolute
  cap on total hold time, nothing that distinguishes "a real 20-minute prose generation" from
  "a runner that will never respond again."
- This means `gpu_lane.py`'s own arbitration reports the wedged holder as healthy for as long as
  the wedge lasts, for the identical structural reason `/api/ps`/`/api/tags` do in the wedge
  scenario described in the task: the check measures "is something responding to a shallow
  probe" (here: "is the watcher thread still looping"), not "is the underlying generation still
  progressing." With `MAX_SLOTS` typically 2, one wedged call can halve — and with `MAX_SLOTS=1`
  it would completely stop — every other Ollama caller in the library until a human notices and
  kills the process.

### FINDING 2 — MEDIUM — unguarded `int()` on an operator-supplied env var can crash the whole module at import — VERIFIED

```python
MAX_SLOTS = max(1, int(os.environ.get("PANSCRIPTUM_GPU_SLOTS")
                       or os.environ.get("OLLAMA_NUM_PARALLEL") or "2"))
```
gpu_lane.py:66-67. If `PANSCRIPTUM_GPU_SLOTS` or `OLLAMA_NUM_PARALLEL` is ever set to a
non-numeric value, `int(...)` raises `ValueError` **uncaught**, at import time, for every caller
of this module. The module's own header states as its central design promise: "A bug in it must
never be able to stop the library from working... FAIL OPEN, ALWAYS." This one line is not
inside any guard and would fail the library CLOSED (ImportError propagating to every caller)
on a misconfigured environment variable. Low likelihood of being triggered (requires an operator
typo in an env var), but it directly contradicts the file's own stated invariant, so I flag it.

### Other checks — CLEAN
`_alive()` (Windows `OpenProcess`/`GetExitCodeProcess` path, with the ESRCH-vs-Windows-errno
distinction correctly implemented per its own docstring), `_take_slot`'s `O_CREAT|O_EXCL` atomic
claim, `_touch`'s "never resurrects" guard, `_remove_retry`'s retry-on-Windows-rename-denial,
`foreground()`'s refcounted re-entrancy, and `status()` (enumerates every holder, never samples
— Hard Rule 0 compliant) were all traced and match their documentation. No two-writer-contract
violation: all shared-file writes go through `silence.replace_retry` (via `_write_claim`/
`_touch`) as required.

---

## src/reference.py (358 lines) — CLEAN

Hand-built reference Assay worksheets for Goku/Naruto/Luffy plus `shelfmark()`, `citation()`,
`card()`, and a `--compare` mode against the automated pipeline's output.

- **Two-writer contract**: `silence.write_json(OUT, out, ...)` used for the shared
  `REFERENCE_ASSAYS.json` (reference.py:333), correctly annotated "ATOMIC: standards.py and
  zfighters.py both read REFERENCE_ASSAYS.json." Compliant.
- **Swallowed failures**: `shelfmark()`'s `try/except Exception: silence.note(...)` (reference.py
  :233-242) degrades to `upper = ["?","?","?"]` on any NAVTREE lookup failure — this is the
  project's sanctioned silence-discipline pattern (logged via `silence.note`, not a bare swallow)
  and produces the charter's own explicit "?" convention for unknown rungs, so it's a designed
  fallback, not a bug.
- **Hard Rule 0**: `REFERENCE` is a fixed hand-authored dict of 3 entities, not a truncation of
  any larger real listing. No caps found.
- Minor, non-blocking robustness note (not filed as a finding, UNVERIFIED / currently untriggered):
  `shelfmark()`'s rung-index arithmetic (reference.py:243-245) assumes `tier_key` always has
  exactly 3 dot-separated parts and `lower_rungs` always has exactly 4 entries, so that
  `RUNGS[3+i]` for the lower rungs never collides with `RUNGS[i]` for the upper ones. All three
  current `REFERENCE` records satisfy this, so it does not currently misfire, but nothing enforces
  it structurally.

No findings to report for this module.

---

## src/sevenfold.py (275 lines)

### Confirming known finding — sevenfold.py:198-209 — VERIFIED

```python
worlds = {}
for src, ws in by_source.items():
    base = coords.get(src)
    if base is None:
        continue
    ...
```
Confirmed present exactly as filed. `base = coords.get(src)` silently drops **every world**
belonging to a source whose designation prefix isn't found in `coords` (the top-level
source-shelving result) — no count, no log, no diagnostic of how many worlds/sources were
skipped. Combined with the file's own Hard-Rule-0-adjacent design ethos (elsewhere in this same
file it explicitly refuses to truncate: "Ranked, never truncated"), this silent drop is the same
class of bug the project treats as a truncation: a `worlds` dict that looks complete but is
missing an unknown-and-unreported subset. Confirmed real, not refuted.

### Confirming known finding — sevenfold.py:266 — VERIFIED

```python
if args.write:
    p = os.path.join(HERE, "data", "SEVENFOLD.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"span": SPAN, "sources": coords, "worlds": worlds},
                  f, indent=2, ensure_ascii=False)
```
Confirmed: bare `open(path, "w")` + `json.dump` on `data/SEVENFOLD.json`, a shared data file per
the two-writer contract, bypassing both `silence.write_json` and `silence.replace_retry`. This is
a truncate-then-fill write with no atomicity — a reader hitting this file mid-write, or a crash
between truncation and the full dump completing, sees a corrupt/partial file. Confirmed real, not
refuted.

### Other checks — CLEAN
`affinity_order` (greedy nearest-neighbour), `seams()`/`split()` (clamps branching to ≤7 per the
declared span while never dropping a member — all members are placed, only the grouping count is
bounded, so this is not a Hard-Rule-0 violation of the kind the project bans), and the
`shelve()`-then-relabel trick in `build()` (worlds' inner 2-level shelve reuses the generic
`TIERS` labels "hyperverse"/"xenoverse" for what are conceptually "multiverse"/"universe", then
`build()` explicitly remaps them at sevenfold.py:206-208) were traced and are internally
consistent, if a little fragile to reordering the global `TIERS` tuple — not flagged as a
standalone finding since it currently works correctly. `main()`'s `sorted(coords)[:8]` /
`sorted(worlds)[:8]` (sevenfold.py:257, 261) are diagnostic "sample shelfmarks" print-only
displays, explicitly labelled as samples, and do not affect the written `SEVENFOLD.json`, which
carries every source/world with no truncation — not a Hard Rule 0 violation.

---

## src/autostart.py (218 lines)

### Confirming known finding — autostart.py:208-211 — VERIFIED, with the concrete detail

```python
try:
    import overnight as ON
    for job in ("dashboard.py", "publish.py", "foreman.py", "overwatch.py",
                "feats.py", "read.py"):
        print(f"  {job:<16}" + ("running" if ON.running(job) else "not running"))
except Exception:
    silence.note("autostart.py:status")
```
Confirmed present. Cross-checked against `gpu_lane.py`'s own header, which lists the nine
standing Panscriptum jobs by name: "read, feats --roll, pipeline, foreman, overwatch, publish,
dashboard, overnight, autostart." Excluding `overnight.py` (the supervisor, checked separately
just above via `supervisor_alive()`) and `autostart.py` (this file), the remaining seven jobs
are: read, feats, **pipeline**, foreman, overwatch, publish, dashboard. The hardcoded tuple here
lists only six — **`pipeline.py` is missing**. `--status` will never report whether the pipeline
job is running, with no indication that a job was omitted from the listing. Given this is the
watchdog's own human-facing status report, a dead `pipeline.py` is invisible to anyone running
`autostart.py --status` to check the fleet.

### FINDING — MEDIUM/UNVERIFIED — `supervisor_alive()` fails closed (assumes dead) on any error, which could start a duplicate supervisor

```python
def supervisor_alive():
    try:
        import overnight as ON
        return ON.running("overnight.py")
    except Exception:
        silence.note("autostart.py:alive")
        return False
```
autostart.py:94-100. Any exception while importing `overnight` or evaluating `ON.running(...)`
(transient import error, exception inside `overnight.running`, etc.) makes this return `False`
("not alive") even if the supervisor is, in fact, running. `watch()`'s loop
(autostart.py:163-179) treats `False` as license to call `start_supervisor()` and launch a
second `overnight.py` process. `overnight.py`/`overnight.running()` are outside this batch, so I
could not verify whether `ON.running()` itself is robust enough that this exception path is ever
actually reached in practice — flagging as UNVERIFIED, but it is a real code path that, if hit,
directly produces the "starts a second copy of a job" failure class the assignment calls HIGH
severity for this file.

### Other checks — CLEAN
`_vbs_body()`'s `Chr(34)`-based VBScript quoting was traced term-by-term and correctly produces
`"<python>" -u "<autostart.py>" --watch` as the launched command — matches the docstring's claim
that an earlier f-string version was broken and this was the fix; current code is correct.
`_twin_watchdog()` correctly excludes its own PID and only fires on `python.exe`/`pythonw.exe`
command lines containing both `autostart.py` and `--watch`; on a PowerShell failure it fails open
(`return False`, i.e. "no twin found," so `watch()` proceeds) — consistent with the file's
fail-open philosophy, though it does mean the "ONE WATCHDOG" guarantee is only as reliable as
this one-time PowerShell probe at startup, not continuously enforced. `start_supervisor()`
correctly uses `CREATE_NO_WINDOW | DETACHED_PROCESS` (no-console-window rule honoured). No
two-writer-contract violations — no shared JSON files are written by this module at all, only
append-only text logs via plain `open(..., "a")`, which is the right primitive for a log, not a
record/state file.

---

## src/catalogue_aurora.py (162 lines)

### FINDING — MEDIUM — `data/SWEEP_ROLL.json` read-modify-write has no cross-process merge/lock, despite being a documented four-writer shared file — VERIFIED (structural), UNVERIFIED (no observed collision)

```python
with open(ROLL, encoding="utf-8") as f:
    roll = json.load(f)
...
r["entry_count"] = len(entries)
r["status"] = "catalogued"
...
# ATOMIC: four scripts write this same roll (see silence.write_json). 2026-08-25.
silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)
```
catalogue_aurora.py:107-150. `silence.write_json` (not read in this batch) makes the final
*write* atomic — a reader can never observe a half-written file — but the read-modify-write
around it is not: the whole roll is loaded into memory at the start of `main()`, mutated
in-process, and the complete (whole-file) result is written back once at the end. The comment
itself confirms this file is written by four separate scripts. If another of those four scripts
reads-and-writes the same roll while this one is running, whichever finishes last silently
overwrites the other's in-memory changes — a classic lost-update race, not prevented by
atomicity of the individual write. I did not observe an actual collision (would require tracing
the other three writers, outside this batch), so I'm labelling the mechanism VERIFIED (I read the
code and there is no lock, version check, or per-key merge) but the real-world occurrence
UNVERIFIED.

### Other checks — CLEAN
`parse_folder()`'s per-file `try/except Exception: silence.note(...); continue` around
`ET.parse` is the sanctioned pattern (a malformed homebrew XML file is skipped, logged, and does
not abort the whole source — explicitly documented at catalogue_aurora.py:76-77). No Hard Rule 0
violation: `root.iter("element")` is walked in full with no `[:N]`/`limit=`/early break, and the
`seen` dedup set only removes true (type, normalized-name) duplicates, never truncates a distinct
listing. Two-writer contract: `pipeline.write_record_catalogue(...)` is used (catalogue_aurora.py
:142-144) — the correct call for the cast-growing/cataloguing side per the contract. No swallowed
failures beyond the sanctioned `silence.note` pattern.

---

## Summary table

| File | Findings | Clean |
|---|---|---|
| rigor.py | 0 | yes |
| gpu_lane.py | 2 (1 HIGH, 1 MEDIUM) | — |
| reference.py | 0 | yes |
| sevenfold.py | 2 confirmed known findings (both VERIFIED present) | — |
| autostart.py | 1 confirmed known finding (VERIFIED, detail added) + 1 new MEDIUM/UNVERIFIED | — |
| catalogue_aurora.py | 1 MEDIUM (structural VERIFIED, occurrence UNVERIFIED) | — |
