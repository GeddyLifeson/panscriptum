# AUDIT — Batch 10 (run #25)

Files: `src/rigor.py`, `src/gpu_lane.py`, `src/reference.py`, `src/sevenfold.py`,
`src/autostart.py`, `src/catalogue_aurora.py`. Every line of every file read end to end (no
sampling). Two items got the deep, run-something treatment per the batch brief: `gpu_lane.py`'s
m99 mechanism and `autostart.py`'s unverified supervisor start.

---

## 1. `gpu_lane.py:326-455` — THE m99 MECHANISM, confirmed at source

**VERIFIED.**

### What the code actually does

`lane()` (`:388-455`) starts a **separate daemon thread** (`_heartbeat`, `:326-360`) the moment it
acquires a slot/foreground claim:

```python
def _heartbeat(paths, stop):
    many = paths if isinstance(paths, (list, tuple)) else (paths,)
    while not stop.wait(_BEAT_SECONDS):
        for p in many:
            _touch(p)
```

`_touch()` (`:290-310`) rewrites the lease file's `heartbeat` field to `_now()` on every tick,
unconditionally — it has **no argument, no channel, no shared variable that carries any signal
from the actual HTTP call**. It only knows two things: "this PID still owns the record" and "wall
clock has advanced." The thread that is actually blocked inside `requests.post(...)` /
`urllib.request.urlopen(...)` (in `generate.py:157`, `pipeline.py:372`, `local_agent.py:493`) is a
**different thread**, and `_heartbeat` never inspects it, polls it, or receives anything from it.
`stop` is only ever `.set()` in `lane()`'s `finally` block, i.e. after the wrapped call returns
*for any reason* (success or exception) — so the heartbeat keeps ticking for the entire wall-clock
span the call thread is parked on that blocking read, whether or not Ollama is making any real
progress.

**This is exactly what the batch brief describes**: the lease is evidence the *wrapping Python
thread has not exited*, not evidence the *model call is progressing*. `_alive()` (PID-liveness)
and `_expired()` (heartbeat age) both pass for the entire span, because both are watching the
wrong thing.

### What bounds it today, and why that bound is weaker than it looks

Every caller passes an HTTP-level `timeout` to the underlying socket call (`generate.py`: up to
1800s via `config.yaml`'s `request_timeout`; `pipeline.py:ask()`: 420s default; `local_agent.py`:
420s). In principle a truly silent, byte-for-byte-zero hang is bounded by that number. I proved
directly that this bound is **not** the backstop it appears to be — Python's / urllib3's socket
`timeout` is a **per-`recv()` inactivity timeout**, not a total-call deadline:

```
ran: scratchpad/wedge_test.py — a local HTTP server that writes ONE byte per second for
20 seconds and never completes a real response (no Content-Length, connection stays open)

result: urllib.request.urlopen(req, timeout=2) did NOT raise — it blocked the full 20s,
10x the configured timeout, because each trickled byte reset the read-timeout clock.
```

So the *actual* requirement for gpu_lane's mechanism to be safe is "Ollama (or anything between
this process and it — a proxy, a keep-alive layer) never emits so much as one byte while making
zero real progress." That is not a property gpu_lane enforces or even knows about; it is an
assumption borrowed from the transport, and the heartbeat thread compounds it by supplying an
**independent, wall-clock-only signal of health that would keep the GPU slot "occupied" for the
full span even if the transport-level timeout were somehow evaded**. Concretely: a wedged-but-
trickling Ollama request holds the slot for as long as the caller's `timeout` value allows (up to
30 minutes for prose generation) with `gpu_lane.status()` reporting a perfectly healthy, actively-
refreshed lease throughout — which is the "every health probe reads green" signature named in the
task.

### Minimal correct fix

The lease needs to carry evidence that the **call itself** is advancing, not that the wrapping
thread hasn't exited. Two changes, smallest first:

1. **Stop refreshing on a timer; refresh on bytes.** Ollama's `/api/generate` supports
   `"stream": true`, returning newline-delimited JSON chunks as generation proceeds. If every
   caller streamed and passed the *actual last-chunk-received timestamp* into `_touch()` (instead
   of `_now()` on a dumb interval), the lease would only stay fresh while tokens are actually
   arriving — a wedge with zero token output would go stale within one `_BEAT_SECONDS` window
   (~100s) rather than surviving the full request timeout. This requires exposing a shared
   "last progress" value from the calling thread to the heartbeat thread (a `threading.Event` per
   tick or a mutable timestamp cell), not just a path list.
2. **If streaming is not adopted**, at minimum give `lane()`'s heartbeat a ceiling independent of
   the caller-supplied HTTP timeout — e.g. refuse to refresh past `N` beats without an explicit
   "yes, still working" signal from the caller (a lightweight callback or counter the call site
   increments after each conceptual unit of work). Anything that keeps "the lease is fresh" and
   "the wrapping thread hasn't exited" as the *same fact* leaves this mechanism exposed to any
   transport that can be kept nominally alive without producing a real response.

The socket-timeout side is a second, independent gap worth closing regardless: an unbounded or
very generous `timeout=` on any future caller (or a proxy/AV layer, per this machine's known
Norton TLS interception — see memory) removes even the partial backstop that exists today.

---

## 2. `gpu_lane.py:66-67` — import-time crash contradicts "FAIL OPEN, ALWAYS"

**VERIFIED — reproduced.**

```python
MAX_SLOTS = max(1, int(os.environ.get("PANSCRIPTUM_GPU_SLOTS")
                       or os.environ.get("OLLAMA_NUM_PARALLEL") or "2"))
```

```
$ PANSCRIPTUM_GPU_SLOTS=abc python -c "import gpu_lane"
IMPORT RAISED: ValueError: invalid literal for int() with base 10: 'abc'
```

The module's own header (`:32-37`) states: *"FAIL OPEN, ALWAYS... every failure path here
PROCEEDS rather than blocks... a bug in it must never be able to stop the library from working."*
A malformed `PANSCRIPTUM_GPU_SLOTS` or `OLLAMA_NUM_PARALLEL` value does the opposite of proceeding
— it prevents `import gpu_lane` from completing at all, which takes down every caller
(`generate.py`, `pipeline.py`, `local_agent.py`) at import time, not just at call time. This is the
single worst failure mode available to a module whose entire design goal is "never able to stop
the library." Fix: wrap the `int(...)` in a try/except that falls back to `2` (or `MAX_SLOTS = 2`)
on any parse failure — one line, matching the file's own stated policy.

**Related, not in this batch but worth flagging by name**: `read.py:283-284` has the byte-for-byte
identical unguarded pattern (`GATE_LOCAL_N = max(1, int(os.environ.get("PANSCRIPTUM_GPU_SLOTS") or
os.environ.get("OLLAMA_NUM_PARALLEL") or "2"))`), so the same malformed env var would also crash
`read.py` at import. Confirms this is a live, reachable code path (both vars are read in at least
two modules), not a hypothetical.

---

## 3. `autostart.py:103-200` — supervisor start never re-verified

**KNOWN** (already in `NEXT_STEPS.md` §3). Confirmed at source, and I ran the concrete timing
proof the brief asked for.

`start_supervisor()` (`:103-118`) is a bare `subprocess.Popen(...)` that returns immediately —
nothing waits, nothing checks `.returncode`, nothing re-queries `supervisor_alive()`. Both call
sites treat the mere fact that `Popen()` didn't raise as success:

```python
# :194-200  (--install)
if not supervisor_alive():
    start_supervisor(a.read_hours)
    print("supervisor started")          # unconditional
    return 0

# :163-169  (watch() loop)
if not supervisor_alive():
    start_supervisor(read_hours)
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"[...] supervisor was not running; started it{chr(10)}")   # unconditional
```

`ON.running()` (used by `supervisor_alive()`) checks the live process list, not a marker file, so
an immediate re-check *would* see a fresh crash — but neither call site does a re-check at all.

**Proof that a short wait would actually catch it** (Windows, this machine):

```
p = subprocess.Popen([...python -c "raise SystemExit(1)"...])
immediately after Popen: poll() = None
after 0.5s:              poll() = None
after 1.5s:               poll() = 1        <-- crash visible
```

A crash-on-startup is detectable within ~1.5s on this machine; the current code waits 0s.

**What correct verification looks like**: after `start_supervisor()`, poll for up to a few seconds
(e.g. `for _ in range(N): if proc.poll() is not None: break; time.sleep(0.5)`), then check both
`proc.poll() is None` (didn't immediately die) and, once seen alive, `supervisor_alive()` a beat
later (confirms `overnight.py` itself, not just the interpreter, is up). On failure, read the tail
of `overnight_stderr.log` and report the real failure instead of printing/logging "started" /
"started it". The `watch()` loop's self-correction on its *next* 180s tick is real but is not the
same as verifying — for up to `CHECK_SECONDS` the log and any dashboard reading it says "started
it" about a supervisor that is actually down.

**New, smaller sub-finding in the same file — UNVERIFIED (reasoned, not reproduced):**
`_twin_watchdog()` (`:121-145`) fails open into the exact scenario its own docstring says is
catastrophic. On any error querying the process list (PowerShell unavailable, CIM timeout, etc.)
it returns `False` — "no twin detected" — via `except Exception: silence.note(...); return False`
(`:131-133`). The docstring for `watch()` (`:151-155`) recounts a real incident where three
watchdogs ran at once and "the whole arrangement respawned itself in a loop." The one guard that
exists to prevent a repeat of that incident silently disables itself under the same class of
transient failure (PowerShell/CIM trouble) that a flaky machine would plausibly produce.

---

## 4. `sevenfold.py:198-202` — silent continue drops a source's world list

**KNOWN** (already in `NEXT_STEPS.md` §3, cited at these exact lines). Confirmed at source:

```python
for src, ws in by_source.items():
    base = coords.get(src)
    if base is None:
        continue
```

If a source name from `worldseed.build_all()`'s designations doesn't match a key in `coords`
(built from `tiers._graph()` / `weave.filtered_index()`'s source set), every world under that
source silently vanishes from the shelved output with no log line. Not re-investigated further
this run beyond confirming it is still live and unchanged.

---

## 5. `catalogue_aurora.py:107-150` — unguarded read-modify-write on `SWEEP_ROLL.json`

**KNOWN** (already in `NEXT_STEPS.md` §3, cited at these exact lines as one of five writers of this
file). Confirmed at source: `roll` is read once at `:107-109`, mutated in memory across the
`FOLDER_SOURCE` loop (`r["entry_count"] = ...`, `r["status"] = ...`), and written back once at
`:150` via `silence.write_json` (correctly atomic *as a single write*, but with no lock and no
merge against a concurrent writer's changes made during this script's run). A concurrent writer
(`resync_roll.py`, `catalogue_codex.py`, or the pipeline itself) touching the same file mid-run
would have its changes clobbered by this script's stale in-memory copy. Not re-investigated
further; NEXT_STEPS already names the fix direction (lock or read-just-before-write).

---

## 6. `catalogue_aurora.py:92` — inherits catalogue_codex's THINGS-fallback miscategorization, NEW verified numbers

**VERIFIED — ran against the real Aurora XML.**

```python
"category": TYPE_CATEGORY.get(etype.lower(), THINGS),
```

`TYPE_CATEGORY`/`THINGS` are imported directly from `catalogue_codex.py` (`:35`). `NEXT_STEPS.md`
already flags `catalogue_codex.py:159` for silently miscategorizing 70 codex elements into THINGS
via this same fallback — but that finding was scoped to the codex file's own data. I ran
`parse_folder()`'s actual glob + `ET.parse()` path over all ten real `FOLDER_SOURCE` directories
under `C:\Users\imarl\Documents\5e Character Builder\custom` and diffed every real `etype` seen
against `TYPE_CATEGORY`'s keys:

```
total elements parsed: 5,861
falling back to THINGS (no TYPE_CATEGORY entry):
  'companion action'    : 36
  'weapon property'     :  7
  'race variant'        :  5
  'background variant'  :  1
  total misfiled         : 49
```

Same root cause as the KNOWN `catalogue_codex.py:159` finding, but a **new, independently-verified
manifestation**: `catalogue_aurora.py` is a second, more comprehensive data path (the docstring's
own selling point — "1,159 elements from the XML against 123 names from the codex" for just two of
the ten folders) that inherited the incomplete dict rather than getting its own or an extended one.
Fixing `TYPE_CATEGORY` at its source (`catalogue_codex.py`) would fix both call sites at once.

---

## Modules read end to end and found CLEAN this run

- **`rigor.py`** (865 lines) — pure computation, zero file I/O beyond a self-integrity check on its
  own source (`:59`, matches the project's control-character canary pattern used elsewhere) and one
  `json.load` for display in an unrelated file (none in this module). No shared state, no writes,
  no caps on returned data (the three `[:N]` slices at `:449` and `:858` are console-preview-only
  truncations of diagnostic strings; the underlying `comps`/`load_bearing` fields returned to
  callers are the full, uncapped lists). Re-confirmed clean (it was also CLEAN in run #24's list).
- **`reference.py`** — the three-entity calibration file. Single writer of `REFERENCE_ASSAYS.json`
  via `silence.write_json` (atomic, correctly commented as such). `shelfmark()`'s NAVTREE.json read
  failure path degrades honestly to `"?"` placeholders rather than fabricating a value. No caps
  (the `REFERENCE` dict's three hardcoded entities are an intentional small calibration set, not a
  sample of a larger population). No two-writer-contract violations.
- **`sevenfold.py`** — apart from the KNOWN `:198-202` finding above, clean: `--write` path uses
  `silence.write_json` atomically (commented "the m100 tail, 2026-08-25"); the display-only `[:8]`
  slices in `main()`'s "sample shelfmarks" printouts do not touch the written data, which is always
  the full `coords`/`worlds` dicts. Verified the `affinity_order()` tie-break concern I initially
  suspected (Python set iteration order / hash randomization affecting reproducibility) does **not**
  apply in practice: `tiers._graph()` and `weave.idf_table()` both hand `shelve()` a `sorted()`
  list, not a set, so the tie-break is alphabetically deterministic regardless of hash seed — ran
  the same tied-weights scenario three times in separate processes and got identical output each
  time. The `seams()` "OVER SPAN" check that can never fire (`:241-245`) is self-aware in its own
  comment about being a guaranteed-pass display, not a hidden one — not counted as a new finding.

---

## Verification log (commands run)

- `PANSCRIPTUM_GPU_SLOTS=abc python -c "import gpu_lane"` → `ValueError` at import (finding 2).
- `scratchpad/wedge_test.py` — local dribbling HTTP server vs `urllib.request.urlopen(timeout=2)` →
  20s hang against a 2s timeout, no exception (finding 1, socket-timeout-is-inactivity-not-total).
- `subprocess.Popen(...raise SystemExit(1)...)` polled at 0s/0.5s/1.5s → crash visible only after
  ~1.5s (finding 3, proves a short wait would work where zero wait does not).
- Live `parse_folder()`-equivalent run over all ten real `FOLDER_SOURCE` XML directories, diffed
  against `TYPE_CATEGORY` → 49/5,861 elements fall back to THINGS (finding 6).
- Three separate process invocations of `sevenfold.affinity_order()` under all-tied weights →
  identical output every time (ruled out a suspected reproducibility bug — not reported as a
  finding because it does not reproduce).
