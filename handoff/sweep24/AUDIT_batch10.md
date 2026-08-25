# Audit — Batch 10 (run #24 whole-tree sweep)

Files in batch, all read completely, every line:
- `src/rigor.py` (866 lines) — full read.
- `src/gpu_lane.py` (480 lines) — full read.
- `src/reference.py` (359 lines) — full read.
- `src/sevenfold.py` (275 lines) — full read.
- `src/autostart.py` (219 lines) — full read.
- `src/catalogue_aurora.py` (163 lines) — full read.

Supporting cross-checks performed (outside batch, to verify claims made *inside* batch files
rather than to audit those files themselves): `src/tempus.py` (`band_resolution` /
`rung_description_length`, referenced by `rigor.py`), `src/silence.py` (`write_json`,
`replace_retry`, `note` — the two-writer contract machinery every batch file leans on),
`src/pipeline.py` (`write_record_catalogue`, used by `catalogue_aurora.py`), `src/worldseed.py`
(`build_all`, `_graph`-adjacent designation naming) and `src/tiers.py` (`_graph`, source naming)
to test the `sevenfold.py` silent-drop finding. Grep confirmed `data/SWEEP_ROLL.json` has at
least 8 writer call sites across the tree (`catalogue_codex.py`, `resync_roll.py`,
`catalogue_aurora.py`, `pipeline.py`, `catalogue_web.py`, `recover_folder_records.py`,
`verify_math.py`, `allsweep.py`).

---

## rigor.py — clean

Read in full, including the long module docstring's mathematical claims. Traced
`measure_bit_value` against `tempus.band_resolution`/`rung_description_length` directly: the
docstring's claim that `band_resolution` was split out specifically to avoid the M0-floor
zero-bits bug, and that `measure_bit_value` divides by 10 itself (not double-dividing), checks
out — `band_resolution` returns `log2(hi/lo)` un-divided; `measure_bit_value` does the `/10.0`.
No mismatch. **VERIFIED clean.**

Checked `perron_weights`, `logrank_weights`, `theorem_1_check`, `bradley_terry` (MM algorithm
against Hunter 2004's closed form, Ford's condition, the deviance formula's ordered-pair
iteration, the `undefeated`/`winless` check against `observed` rather than the prior-augmented
matrix), `_strongly_connected` (iterative Tarjan), `mdl_bits`, `_log2_choose`,
`adjudication_beta`, `lognormal_product`, `prob_at_least_one`, `ceiling_confidence`,
`gumbel_return_level`, `mathematical_resonance`. All matched their docstrings and standard
formulations; no off-by-one, no inverted condition, no swallowed failure found. The
`load_bearing` truncation in `main()`'s print (`mr["load_bearing"][:6]`) is display-only — the
function itself returns the full untruncated list per its own Hard-Rule-0 comment, and the
console summary slicing is the explicitly-sanctioned "sole consumer." Not a finding.

**No findings in this file.**

---

## gpu_lane.py

### 1. `gpu_lane.py:326-455` (`_heartbeat`, `lane`) — the wedge mechanism, confirmed and traced

```python
def _heartbeat(paths, stop):
    ...
    while not stop.wait(_BEAT_SECONDS):
        for p in many:
            _touch(p)
```
`_touch` is started right before `yield` inside `lane()` and stopped only in the `finally` block,
which runs only after the wrapped call (the `yield` statement) returns or raises. The heartbeat
thread's only job is "has the `with lane():` block exited yet" — it has zero visibility into
whether the underlying Ollama HTTP call is actually making progress. A synchronous request that
the daemon has accepted but never answers (socket open, no response, no client-side read
timeout actually enforced) leaves the calling thread blocked inside the `yield`, the process
alive, and the heartbeat thread — running independently in the same process — refreshing both
the slot lease and the foreground claim every `_BEAT_SECONDS` (≤300s) forever. Nothing in this
module can distinguish that from a healthy long-running generation, because nothing in this
module ever inspects the actual HTTP response stream. This confirms the suspect exactly as
described: `/api/ps`/`/api/tags` external health checks would also read green, since the daemon
process itself is fine — only a completed generation proves the call is alive.

**No other path in this file produces the same class of wedge** — `_take_slot`'s deadline loop
(`SLOT_LEASE_SECONDS`) bounds queueing for a slot, and `MAX_YIELD_SECONDS` bounds background
yielding to foreground; both of those loops run *before* the call is made and cannot wedge.
Once inside the `yield`, the heartbeat is the only thing keeping the lease alive, and it is
structurally blind to the call's real state. This is a design limitation, not a separate bug —
but it means the fix (if one is wanted) has to live where the actual model call happens (e.g. an
enforced client-side socket/read timeout in `ollama_client.py` or similar, outside this batch),
not in `gpu_lane.py` itself, since this module has no hook into the response stream.

Severity: **MAJOR**. **VERIFIED** (traced from `lane()`'s heartbeat start/stop to `_heartbeat`'s
loop body; confirms the mechanism, not the downstream root cause).

### 2. `gpu_lane.py:66-67` — unguarded `int()` on an environment variable, contradicts "fail open, always"

```python
MAX_SLOTS = max(1, int(os.environ.get("PANSCRIPTUM_GPU_SLOTS")
                       or os.environ.get("OLLAMA_NUM_PARALLEL") or "2"))
```
If `PANSCRIPTUM_GPU_SLOTS` or `OLLAMA_NUM_PARALLEL` is set to any non-numeric string (a stray
space, a comment, a copy-paste artifact — e.g. `PANSCRIPTUM_GPU_SLOTS=2 # slots`), `int(...)`
raises `ValueError` at **import time**. Since this module is imported by "every model call the
library makes" per its own header, that one bad environment variable takes down every one of the
nine standing processes' ability to import `gpu_lane` at all — the opposite of "FAIL OPEN,
ALWAYS," which is this module's own stated invariant three paragraphs above this line. Empty
string and unset are both handled fine (fall through via `or`); only a garbage non-numeric value
crashes it, but that's exactly the kind of value a human editing an env file or a
`.env`/systemd-unit typo would introduce.

Severity: **MAJOR**. **VERIFIED** (read directly; no try/except anywhere around this line).

### 3. `gpu_lane.py:219-256` (`foreground`, `_write_claim`) — latent lost-update race if ever called from two threads in one process

`foreground()`'s re-entrant refcount (`depth`) is implemented as a plain read-`json.load`,
increment, write-`replace_retry` sequence against `fg.{pid}.json`, keyed only by PID, with no
thread-local component and no lock:
```python
rec = _read(path) or {}
depth = int(rec.get("depth") or 0) + 1
_write_claim(path, depth, label)
```
If two threads inside the *same process* call `foreground()` concurrently (rather than the
nested-single-thread case the docstring describes — "a foreground call may nest inside
another"), both can read `depth=0` before either writes, and both write `depth=1`; on exit both
decrement from their own stale view, and the claim can be removed while one thread still
believes it holds it, or double-removed. This is not the scenario the module was built for
(nine *processes*, not multi-threaded foreground use within one), and I found no call site in
this batch that does this — `lane()`'s own heartbeat thread never calls `foreground()`, only
`_touch()`. Flagging as a design gap, not a confirmed live bug.

Severity: **MINOR**. **UNVERIFIED** (no confirmed multi-threaded caller found; the race window
exists in the code as written).

---

## reference.py

No correctness bugs found. `shelfmark()`'s rung-count arithmetic
(`RUNGS[3 + i]` for `lower_rungs`, assuming `upper` from `tier_key.split(".")` is always exactly
3 parts) is fragile — if a future `REFERENCE` entry's `tier_key` had 2 or 4 dotted parts instead
of 3, `lower`'s marks would either skip a `RUNGS` slot or collide with `upper`'s. All three
current entries (Goku `1.6.1`, Naruto `4.2.0`, Luffy `1.2.5`) have exactly 3 parts, so this is
currently dormant.

Severity: **MINOR** (latent fragility in a hardcoded, currently-consistent reference dataset).
**VERIFIED** as a code-level assumption; **UNVERIFIED** as a live bug (not currently triggered).

Everything else — `perron`/`logrank` cross-check via `theorem_1_check`, the `compute`/`card`/
`citation`/`_vernacular` chain, the `--compare` path, the `silence.write_json` use for
`REFERENCE_ASSAYS.json` (correctly following the two-writer contract) — checked out clean.

---

## sevenfold.py

### 1. `sevenfold.py:198-202` (`build`) — silent whole-source drop if source-name sets diverge

```python
for src, ws in by_source.items():
    base = coords.get(src)
    if base is None:
        continue
    ...
```
`by_source` is keyed by `world["designation"].split("::")[0]`, and `designation` is built in
`worldseed.py:280` as `f"{src}::{nm}"` where `src = rec["source"]` comes from
**`pipeline.records()`** (the catalogue). `coords` (and therefore the set of keys `coords.get`
can hit) comes from `srcs, w, shared = TI._graph()` in `tiers.py:193-200`, which is built from
**`weave.load_index()` / `weave.filtered_index()` / `weave.idf_table()`** — a completely
different index over a *filtered* view of the corpus (the name itself says "filtered"). These
are two independently-built lists of "source names," not a shared reference. If `weave`'s
filtered index ever excludes, renames, or fails to include a source that `pipeline.records()`
still carries (a very plausible drift — different filtering criteria, different point-in-time
snapshot, a source added to one pipeline and not yet reflected in the other's corpus-derived
weights), that source's **entire world list is silently dropped** from `worlds` — no print, no
count, no `silence.note`, nothing. `main()`'s own summary (`worlds shelved: {len(worlds):,}`)
would look like a complete, successful run while quietly shelving fewer worlds than exist. This
is precisely Hard Rule 0's signature failure shape: a truncation that "does not fail, it returns
a smaller universe wearing the same shape as the real one."

Severity: **MAJOR** (matches the project's explicitly named worst failure class). **VERIFIED**
at the code level (the silent `continue` is real, and the two source-name sets are confirmed to
come from genuinely different pipelines — `pipeline.records()` vs `weave.filtered_index()`).
**UNVERIFIED** whether the two name sets currently diverge in practice — that would require
diffing `weave`'s live index against `pipeline`'s live catalogue, which is outside this batch.

### 2. `sevenfold.py:241-245` — a check that cannot fail (self-disclosed in-code)

```python
# m30, same shape as custodes' covers_every_reading: `seams()` already clamps every child
# count to SPAN, so "OVER SPAN" cannot print for any input. This displays a GUARANTEE, not
# a discovery. Kept because it states the bound where a reader looks for it; it becomes a
# real check only if seams() ever stops clamping.
ok = "OK" if hi <= SPAN else "OVER SPAN"
```
This is exactly the "check that cannot fail" shape the sweep is hunting for — but it is already
identified, named (`m30`), and explained in the code itself as an intentional display of a
guarantee rather than a live check. No new information to surface; recorded here only because
the lens explicitly asks for it.

Severity: **COSMETIC** (self-documented, intentional). **VERIFIED**.

Everything else in this file — `affinity_order`, `seams`, `split`/`shelve`'s recursive
partitioning, the `TIERS`/`SOURCE_TIERS`/`WORLD_TIERS` relabeling trick between the two `shelve()`
calls in `build()` (looked like a bug on first read — `dict(zip(TIERS, c))` labelling a
2-element `WORLD_TIERS` coordinate with `TIERS[0:2]` = hyperverse/xenoverse — but `build()`
explicitly re-maps `inner[d]["hyperverse"]`→`multiverse` and `inner[d]["xenoverse"]`→`universe`
right after the call, so the generic relabelling is deliberate and correctly consumed) — checked
out clean.

---

## autostart.py

Directly targeting the audit brief: **what happens when a managed job fails to start, and is a
start failure distinguishable from success.**

### 1. `autostart.py:103-118`, `148-179`, `191-200` — a start failure is not distinguishable from success

```python
def start_supervisor(read_hours=10):
    ...
    return subprocess.Popen([PY, "-u", os.path.join(SRC, "overnight.py"), ...],
                             cwd=HERE, env=env, stdout=out, stderr=err, creationflags=flags)
```
`start_supervisor` returns whatever `subprocess.Popen` gives it. `Popen()` only raises if the
interpreter itself can't be launched (bad path, permissions); it does **not** verify that
`overnight.py` gets past its own imports and actually enters its supervisory loop. Both call
sites treat the mere return of `start_supervisor()` as success:

```python
# watch(), 148-179
if not supervisor_alive():
    start_supervisor(read_hours)
    with open(log, "a", ...) as f:
        f.write(f"[...] supervisor was not running; started it\n")
```
```python
# main(), --install path, 194-200
if not supervisor_alive():
    start_supervisor(a.read_hours)
    print("supervisor started")
```
Neither call site re-checks `supervisor_alive()` (or even `Popen.poll()`) after launching. If
`overnight.py` has a startup-time bug (a broken import, an exception before its own
try/except-everything loop begins, a config parse error) it can exit within milliseconds, and
the log/console message still unconditionally says "started it" / "supervisor started" — a
false positive exactly at the one place (`autostart.py`'s own header) the module identifies as
the load-bearing single point of failure ("`overnight.py`... is the single point whose own
failure is invisible by construction. It watches everything except itself."). The watchdog loop
does at least retry every `CHECK_SECONDS` (180s), so a transient failure self-heals, but a
**persistent** startup bug in `overnight.py` produces an infinite loop of confidently-logged
false "started it" messages every 3 minutes, with the process actually down the entire time.

Severity: **MAJOR** (the exact scenario the audit brief calls out — a start failure that reads
as a successful start, in the module whose entire job is not letting that happen silently).
**VERIFIED**: no post-launch liveness re-check exists anywhere in this file.

### 2. `autostart.py:207-213` — `--status`'s per-job breakdown silently disappears on import failure

```python
try:
    import overnight as ON
    for job in ("dashboard.py", "publish.py", "foreman.py", "overwatch.py",
                "feats.py", "read.py"):
        print(f"  {job:<16}" + ("running" if ON.running(job) else "not running"))
except Exception:
    silence.note("autostart.py:status")
```
`silence.note` (confirmed by reading `silence.py`) only records to the in-memory `health`
ledger, flushed to `state/failures.json` at process exit — it prints nothing to the console. So
if `overnight.py` fails to import (the same class of failure finding #1 above worries about), a
human running `python autostart.py` to check status sees the two top-line booleans
(`Startup launcher`, `supervisor`) but the entire per-job table silently vanishes with no
on-screen indication that anything went wrong — it just looks like a shorter, valid report. This
is a smaller instance of the same "swallowed failure indistinguishable from an empty/absent
result" pattern (lens #2), scoped to a diagnostic command rather than the automation path
itself.

Severity: **MINOR** (diagnostic-only, not the automation itself; `supervisor_alive()` uses the
same import defensively but correctly defaults to "not running" rather than hiding a whole
section). **VERIFIED**.

Everything else — `_vbs_body`'s `Chr(34)` quoting fix, `_twin_watchdog`'s de-duplication via
`Get-CimInstance`, `install`/`uninstall`, the `_BAD_CHARS` corruption guard — read correctly and
matches its own commentary.

---

## catalogue_aurora.py

### 1. `catalogue_aurora.py:107-150` (`main`) — unguarded read-modify-write on `data/SWEEP_ROLL.json`, confirmed as a known suspect

```python
with open(ROLL, encoding="utf-8") as f:
    roll = json.load(f)
by_name = {r["name"]: r for r in roll}
...
for folder, source_name in FOLDER_SOURCE.items():
    r = by_name.get(source_name)
    ...
    r["entry_count"] = len(entries)
    r["status"] = "catalogued"
...
if not args.dry_run and written:
    silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)
```
The final `write_json` call is itself atomic (confirmed in `silence.py`: unique
`path.pid.threadid.tmp` name, then `os.replace`), so this file cannot *corrupt*
`SWEEP_ROLL.json`. But the whole **read → mutate in memory → write** sequence at the top of
`main()` has no lock and no version/hash check against the file it started from. Grep confirms
at least 8 other call sites write the same file (`catalogue_codex.py`, `resync_roll.py`,
`pipeline.py`, `catalogue_web.py`, `recover_folder_records.py`, `verify_math.py`,
`allsweep.py`, plus `silence.py`'s own doc citing "four different scripts"). If any other writer
lands its own `write_json(ROLL, ...)` between this script's initial `json.load` and its final
`write_json`, that writer's update is **silently and completely discarded** — this script's
`roll` (loaded before the other write happened) becomes the new file contents, a clean
last-writer-wins lost update, not a crash and not a corrupted file, so nothing here would ever
surface the loss.

Severity: **MAJOR** (matches the recorded known suspect precisely; concurrency race on shared
state, lens #5). **VERIFIED** (the read-modify-write pattern and the multi-writer fan-in are
both confirmed directly in code/grep; whether a collision has actually occurred in a specific
run is not something static reading can confirm).

### 2. `catalogue_aurora.py:70-96` (`parse_folder`) — dedup key ignores content, can silently drop a genuinely distinct entry

```python
key = (etype.lower(), re.sub(r"[^a-z0-9]", "", name.lower()))
if key in seen:
    continue
seen.add(key)
entries.append({... "description": text_of(el), ...})
```
Entries are de-duplicated purely by `(type, normalized-name)`, across every XML file recursively
globbed under a folder. If two files legitimately define an element with the same type and name
but **different content** (e.g. a base file and an errata/revision file, or two supplement files
that happen to reuse a name like "Fire Bolt" or "Warlock" for unrelated homebrew content), only
the first one encountered (in `sorted(glob(...))` order) is kept; the second is dropped with
**no count printed, no warning, no log line** distinguishing "this was an exact duplicate" from
"this silently discarded different content under the same name." `main()`'s own summary prints
only `{entries} entries ({withtext} with description)` per source — a reader has no way to see
that N items were merged away, or whether any merge was lossy. This is the Hard Rule 0 failure
shape applied to homebrew content rather than a wiki roster: "a cap does not fail, it returns a
smaller universe wearing the same shape as the real one."

Severity: **MAJOR** (matches Hard Rule 0's stated failure class precisely). **VERIFIED** at the
code level (the dedup key and silent `continue` are exactly as described); **UNVERIFIED**
whether the owner's actual XML files under `C:\Users\imarl\Documents\5e Character Builder\custom`
currently contain any same-name/same-type, different-content collisions — that file content was
not inspected as part of this audit (outside the library-kit repository).

Everything else — `FOLDER_SOURCE`'s mapping, `slug()` (60-char truncation is filesystem hygiene
on a file *path*, not a content truncation of any roster — all current `FOLDER_SOURCE` values
are well under 60 chars, so this is dormant and not flagged as a Hard-Rule-0 issue), `text_of`,
the `entry_count > 0` resumability skip (an explicit, `--force`-overridable "already done" guard,
not a silent cap), and the final `record`/`written` reporting — checked out clean.

---

## Summary table

| Severity | Location | Claim | Status |
|---|---|---|---|
| MAJOR | gpu_lane.py:326-455 | Heartbeat refreshes lease on process-alive only, blind to a wedged call; only a completed generation proves liveness | VERIFIED |
| MAJOR | gpu_lane.py:66-67 | Unguarded `int(os.environ...)` crashes at import on a non-numeric env value, contradicting "fail open, always" | VERIFIED |
| MINOR | gpu_lane.py:219-256 | `foreground()`'s depth read-modify-write has no lock; a lost update is possible if ever called from two threads in one process | UNVERIFIED |
| MINOR | reference.py:229-246 | `shelfmark()` assumes `tier_key` always splits into exactly 3 parts; a 2- or 4-part key would misalign or collide `RUNGS` slots | UNVERIFIED live trigger |
| MAJOR | sevenfold.py:198-202 | `coords.get(src) is None: continue` silently drops a source's entire world list if `weave`'s filtered index and `pipeline.records()`'s source names diverge | UNVERIFIED live trigger |
| COSMETIC | sevenfold.py:241-245 | "OVER SPAN" check cannot ever print OVER SPAN, `seams()` already clamps — self-disclosed in code | VERIFIED |
| MAJOR | autostart.py:103-200 | `start_supervisor()`'s success is never re-verified; "started it"/"supervisor started" logged unconditionally even if `overnight.py` crashes on startup | VERIFIED |
| MINOR | autostart.py:207-213 | `--status`'s per-job table silently disappears (only logged to `health`, nothing printed) if `import overnight` fails | VERIFIED |
| MAJOR | catalogue_aurora.py:107-150 | Unguarded read-modify-write on `data/SWEEP_ROLL.json`, ≥8 writer call sites, lost-update race | VERIFIED (known suspect confirmed) |
| MAJOR | catalogue_aurora.py:70-96 | `parse_folder()` dedups by (type, name) only; can silently drop genuinely distinct content sharing a name | VERIFIED code pattern / UNVERIFIED live trigger |
| — | rigor.py | Full file read; math cross-checked against tempus.py; no findings | CLEAN |
