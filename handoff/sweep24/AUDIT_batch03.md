# Audit — batch 03 (run #24 whole-tree sweep)

Files in scope, all read in full, every line:
- `src/standards.py` (1293 lines) — read in two passes (1-1002, 1003-1293), full coverage.
- `src/runguard.py` (220 lines) — read in full.
- `src/catalogue_web.py` (363 lines) — read in full.
- `src/weave_index.py` (277 lines) — read in full.
- `src/catalogue_models.py` (172 lines) — read in full.
- `src/lognames.py` (37 lines) — read in full.

Supporting reads to verify claims (not in the audited batch, consulted only to confirm/refute
a finding): `src/dashboard.py` (poll cadence, `state()`), `src/silence.py` (`write_json`,
`replace_retry`), `src/weave.py` (consumer of `weave_index`'s truncated description field),
`src/resync_roll.py` / `src/pipeline.py` (other `SWEEP_ROLL.json` writers), `src/read.py`
(readfeats cache writer/self-heal), and a live check of `data/REFERENCE_ASSAYS.json` and
`data/readfeats/**` to ground two findings in real data.

---

## 1. `standards.py:241-282`, used at `:967-983` — `fandom_ipv4_reachable()` has no TTL cache

```python
def fandom_ipv4_reachable(host=FANDOM_PROBE_HOST, timeout=8, _sk=None):
    ...
    for fam, typ, proto, _canon, sa in infos:
        s = _sk.socket(fam, typ, proto)
        try:
            s.settimeout(timeout)
            s.connect(sa)
```
called unconditionally inside `check()`:
```python
_fandom_ok, _fandom_where = fandom_ipv4_reachable()
```
**What goes wrong:** every other liveness probe in this file caches itself — `ollama_runner_up`
(`ttl=120`), `ollama_token_flow` (`ttl=300`). This one does not: `check()` calls it fresh on
every invocation. `dashboard.py:state()` calls `standards.check(state)` unconditionally on
every `do_GET` for `/api/state`, and the page's own JS does `setInterval(tick, 5000)` — confirmed
by reading `dashboard.py:670-677,691-694`. So every 5 seconds a live TCP connect (up to
`timeout=8`) is attempted against `marvel.fandom.com:443` from whatever process is currently
serving the dashboard.

**Failure scenario:** during exactly the outage this function's own docstring describes
(fandom edge unreachable from this machine), every dashboard poll blocks for up to 8 seconds
before `/api/state` can respond, which is worse than a slow report — it turns a 5-second refresh
loop into an intermittently-hung one, and it repeats the exact TCP connect this machine is
possibly IP-banned for (the comment block above `FANDOM_PROBE_HOST` cites a self-inflicted IP
block from "our own 100-req/s catalogue rate" as the cause of a prior fandom outage). A dashboard
that polls this every 5 seconds is itself a source of repeated connection attempts against a host
that may specifically be blocking this machine.

Severity: MAJOR. **VERIFIED** (code read directly; poll cadence confirmed in `dashboard.py`).
This matches the suspect flagged in the task brief.

---

## 2. `runguard.py:98-121` — `claim()` TOCTOU, no lock spans read+check+write

```python
def claim(agent, path=GUARD, note=None):
    prior = read(path)
    if holder_is_live(prior):
        ...
        return False, (...)
    now = time.time()
    rec = {"started": now, "heartbeat": now, "done": False, "agent": agent}
    ...
    if not _land(rec, path):
        return False, "could not write the guard record"
    return True, "claimed"
```
**What goes wrong:** `read()` and `_land()` are two independent filesystem operations with no
lock, mutex, or exclusive-create between them. Two processes racing `claim()` at the same moment
both call `read(path)`, both see no live predecessor, and both proceed to `_land()` — the second
writer's `os.replace` simply overwrites the first's record. Both callers get `(True, "claimed")`.

**Failure scenario:** this is exactly the m27 bug this module's docstring says it exists to fix,
reintroduced one layer up. Two maintenance-pass invocations launched within the same instant
(e.g., a scheduled task firing at the same cadence as a manually-kicked run) both pass `claim()`,
both believe they hold the guard, and both proceed to do maintenance work concurrently — the
overlap this entire file exists to prevent. The module's own docstring states the invariant as
"a run may only ever refresh, or close, a record that carries its own name" and correctly
enforces that in `beat()`/`release()` (both check `owner == agent` after a fresh `read()`), but
`claim()` itself has no equivalent protection against two initial claims interleaving.

Severity: MAJOR. **VERIFIED** (code read directly — no lock of any kind, no `O_EXCL` exclusive
create, no lockfile, in this module or imported by it). Matches the suspect flagged in the task
brief. A fix would need either a file-lock/mutex spanning `read()`+`_land()`, or an atomic
create-if-absent primitive (e.g. open with `O_CREAT|O_EXCL` on a companion lockfile) around the
claim path specifically.

---

## 3. `standards.py:656-682` — "hand-built assays match the charter" cannot detect a
   magnitude-**band** drift; it only ever checks the decimal against the charter's own band

```python
inside = 0
for v in refs.values():
    if not isinstance(v, dict):
        continue
    ch = v.get("charter") or []
    got = (v.get("reference") or {})
    if len(ch) >= 3 and got.get("magnitude"):
        band = str(ch[0])
        published, tol = float(ch[1]), float(ch[2])
        mine = float(str(band)[1:]) + float(got.get("decimal", 0))
        if abs(mine - published) <= tol:
            inside += 1
```
Confirmed against live data (`data/REFERENCE_ASSAYS.json`):
```
Goku: charter=['M7', 7.62, 0.41]   reference={magnitude:'M7', decimal:0.44}
Naruto: charter=['M4', 4.31, 0.3]  reference={magnitude:'M4', decimal:0.56}
```
**What goes wrong:** `band` — the value used to build `mine`, the "computed" figure this
standard is supposed to check against the charter's published number — is read from
`ch[0]`, i.e. from the **charter's own array**, not from `got.get("magnitude")`, i.e. the
instrument's own computed reference. `got.get("magnitude")` is only ever tested for truthiness
(`if ... and got.get("magnitude")`), never compared to `ch[0]`, and never used to build `mine`.
So the arithmetic actually performed is "does `published` ≈ `charter_band_digit` + `our_decimal`"
— which structurally cannot fail on the one thing this check exists to catch: our own instrument
computing the wrong **band** (an integer Magnitude step, e.g. M6 instead of M7). If
`REFERENCE_ASSAYS.json`'s `reference.magnitude` ever disagreed with `charter[0]` (say the
worksheet drifted to M6 while the charter still expects M7), this code would still compute
`mine = 7 + our_decimal` (from the charter's own "M7"), compare it to `published=7.62`, and can
easily still land inside `tol` — reporting the instrument's arithmetic as verified when the band
itself is wrong. This is the file's own stated failure shape ("a check that cannot fail") on the
standard the file's own comment block calls "the library's one original claim" — if this drifts,
"everything shelved under it is wrong in a way no amount of correct mining can rescue."

The docstring above this block explicitly claims the fix already made ("Recomputing from the two
numbers that actually exist means the check cannot drift from what it claims to check") — that
claim is true for one prior bug (a missing `inside_charter_interval` key) but false for band
drift, because the "two numbers" it recomputes from are `ch[0]` (charter) and `got.decimal`
(ours), not `got.magnitude` (ours) and `got.decimal` (ours).

**Concrete fix shape:** `mine` should be built from `got.get("magnitude")` (stripped of its `M`)
plus `got.get("decimal", 0)`, and/or the code should separately assert
`str(got.get("magnitude")) == band` before trusting the decimal comparison at all.

Severity: MAJOR. **VERIFIED** by direct code reading and cross-checked against the actual
contents of `data/REFERENCE_ASSAYS.json` (in current data, `reference.magnitude` happens to
equal `charter[0]` for all three references, so the bug is currently latent/non-triggering —
but nothing in the code enforces that equality, so a future worksheet drift in the band would
pass silently).

---

## 4. `standards.py:560-586` — "cached records that were fully read" silently reports a
   **partial, undercounted** scan as the true value on any exception mid-glob

```python
unans_files = 0
try:
    import glob as _g
    now_m = time.time()
    if now_m - _UNANS_CACHE["at"] < 120:
        unans_files = _UNANS_CACHE["n"]
    else:
        for fp in _g.glob(os.path.join(HERE, "data", "readfeats", "**", "*.json"), recursive=True):
            with open(fp, encoding="utf-8") as f:
                head = f.read(700)
            if '"chunks_unanswered": 0' not in head and "chunks_unanswered" in head:
                unans_files += 1
            elif "chunks_unanswered" not in head:
                unans_files += 1          # written before the guard existed
        _UNANS_CACHE.update({"at": now_m, "n": unans_files})
except Exception:
    silence.note("standards.py:unanswered-records")
out.append(_s(
    "cached records that were fully read", unans_files <= MAX_UNANSWERED_RECORDS,
    unans_files, MAX_UNANSWERED_RECORDS, ..., "high", "evidence"))
```
**What goes wrong (two related issues in one block):**

(a) **Partial-scan-as-final-value.** There is no per-file `try/except` inside the loop. If
`open(fp)` raises on *any single file* partway through the (potentially thousands-strong) glob
— e.g. `FileNotFoundError` — the whole `for` loop aborts, the exception is swallowed by the
outer `except Exception: silence.note(...)`, and `unans_files` is left holding whatever partial
count had accumulated **before** the failing file, not the complete count. That partial count
(never marked as partial) is then both **appended to `out` as the standard's real observed
value** and **written into the 2-minute cache** (`_UNANS_CACHE.update` is only reached on the
non-exception path, so on exception the *old* cache value is served for the next 2 minutes
instead — meaning a transient race can hide a real breach from the dashboard for up to 2 extra
minutes on top of the truncated scan itself).

Confirmed this is a live possibility, not hypothetical: `read.py:605-621` (`read_entity`)
actively **self-heals** by deleting a readfeats file the instant it fails to parse
(`os.remove(path)` under `read.py:corrupt-cache`), and `read.py` is one of the "always running"
supervised jobs per `lognames.OWNER`. A file present in `standards.py`'s `glob()` result at
listing time that gets deleted by `read.py`'s self-heal path before `standards.py`'s `open(fp)`
executes raises exactly `FileNotFoundError`, which is not distinguished from a real read error —
it aborts the whole scan. Since `MAX_UNANSWERED_RECORDS = 0` and severity is `high`, a scan that
happens to abort *before* reaching the one file that would have tripped the standard reports a
false ALL-CLEAR for up to 2 minutes running against a corpus of currently 1,285 files (measured
live in this audit) that is scanned start-to-finish on every non-cached call.

(b) **Fragile 700-byte head heuristic.** The presence test only reads `f.read(700)` and looks
for the literal substring `"chunks_unanswered": 0`. This currently works only because, in the
present corpus, `chunks_unanswered` always appears within the first ~370 bytes (verified live:
max observed offset across all 1,285 files is 368 bytes, in
`fireemblem_fandom_com/List_of_items_in_Fire_Emblem_Three_Houses.json`). But the field's
position in the JSON depends on the length of the preceding `"pages": [...]` array (a list of
wiki page titles per entity) — an entity attached to enough pages/aliases would push the field
past byte 700, at which point the `elif "chunks_unanswered" not in head` branch fires and
**miscounts a fully-answered record as unanswered** (a false MISS rather than a false ALL-CLEAR
this time — less dangerous per this project's own stated risk ordering, but still a
correctness bug riding on an unenforced assumption about key ordering/field position that
nothing pins in place).

Severity: MEDIUM-HIGH for (a) (false ALL-CLEAR on a HIGH severity, zero-tolerance standard,
triggerable by a documented, currently-active self-heal race), MINOR for (b) (currently
non-triggering, fragile). **VERIFIED** by code reading; the race precondition (self-healing
delete in `read.py`) is confirmed to exist, exact live-timing of a collision was not
reproduced/forced.

---

## 5. `catalogue_web.py:70-79` — `save_roll()` bypasses `silence.write_json`'s
   collision-hardened tmp-naming, keeping this call site in the multi-process
   `SWEEP_ROLL.json` hazard its own comment describes

```python
def save_roll(roll):
    # Atomic for the same reason the record write beside it is: ...
    import silence as _sil
    tmp = ROLL + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(roll, f, indent=2, ensure_ascii=False)
    _sil.replace_retry(tmp, ROLL)
```
**What goes wrong:** `silence.write_json` (added later, per its own docstring, specifically to
fix "TWELVE call sites across ten modules... writing shared `data/` and `state/` files with a
bare `open(path,'w')` + `json.dump`") tags its temp filename with PID **and** thread id
precisely because "two writers of the same path otherwise collide on the temp file itself, and
the loser can replace the winner's target with a partial file." `save_roll()` still uses the
older, non-tagged `path + ".tmp"` pattern. Within `catalogue_web.py`'s own process this is safe
(the call is made under `_wlock`, serializing the 3 worker threads — verified at
`catalogue_web.py:319-350`), but `SWEEP_ROLL.json` is written by **multiple separate scripts as
separate OS processes** — confirmed via grep: `catalogue_web.py`, `catalogue_aurora.py`,
`catalogue_codex.py`, `recover_folder_records.py`, `pipeline.py`, `resync_roll.py`,
`manifest_builder.py` all touch it. `resync_roll.py`'s own module docstring states outright:
"every cataloguer (catalogue_web.py, catalogue_aurora.py, catalogue_codex.py,
recover_folder_records.py) rewrites the whole roll after each source, so two of them running
concurrently will have one clobber the other's counters with a stale copy read minutes
[earlier]" — i.e. this is an **already-documented, already-acknowledged** hazard in the codebase
(and `resync_roll.py` exists specifically as its repair tool), not a newly-discovered one. What
this audit adds: `save_roll()`'s own fixed (non-PID-tagged) tmp filename means that if two of
those processes happen to call `save_roll()` at literally the same instant, they can collide on
the shared tmp file itself — the specific failure mode `silence.write_json` was built to close —
on top of the already-known read-modify-write lost-update race that no amount of atomic-rename
fixes, because the loss happens at the read, not the write.

Severity: MEDIUM (the read-modify-write race is pre-existing/known and has a repair tool; the
tmp-file-collision half is a real gap against the project's own newer, stricter standard for
this exact file). **VERIFIED** — `save_roll` reads exactly as quoted; `resync_roll.py`'s
docstring quoted verbatim confirms the multi-process write pattern is real and current.

---

## 6. `standards.py:588-608` — fabrication standard vanishes from the report entirely
   (not even reported as UNMEASURED) whenever its regex parse fails, unlike sibling standards

```python
fab = None
read = jobs.get("corpus read")
if read:
    det = read.get("detail") or ""
    try:
        import re as _re
        kept = int((_re.search(r"([\d,]+) feats", det).group(1)).replace(",", ""))
        m = _re.search(r"dropped\s+([\d,]+)", read.get("raw") or "")
        drop = int(m.group(1).replace(",", "")) if m else None
        if drop is not None and (kept + drop):
            fab = drop / (kept + drop)
    except Exception:
        silence.note("standards.py:fabrication")
if fab is not None:
    out.append(_s("sentences that survive the verbatim check", ...))
```
**What goes wrong:** if `_re.search(r"([\d,]+) feats", det)` fails to match (e.g. the
`jobs["corpus read"]["detail"]` string format changes, a scenario this file elsewhere treats as
a first-class risk — see the "UNMEASURED, not zero" reasoning applied to `calls that succeed`
and `every source is fully catalogued` at length), `.group(1)` raises `AttributeError`, caught by
the bare `except`, and the standard is **not appended to `out` at all** — it disappears from the
dashboard silently rather than surfacing as a breach or an explicit "UNMEASURED" row the way the
file does for the structurally identical case a few hundred lines later
(`PROVIDER_MODELS.json` staleness, `COMPLETENESS.json` no-denominator). This is an inconsistency
against the file's own stated design principle ("a standard that cannot see is not a standard
that is satisfied... UNMEASURED is reported as a breach, not a quiet hold") applied to some
parse-fragile standards but not this one. Because `work_orders()`/`report()` only ever see what
`check()` returns, a silently-dropped standard produces no visible symptom at all — it just isn't
there, which is easy to miss on a panel with ~40 rows.

Severity: MINOR (inconsistency of philosophy, not a false-positive/negative on its own — no
green is being shown, the row is simply absent). **VERIFIED** by code reading.

---

## Lower-confidence / minor notes (included for completeness, not padding the count)

- `standards.py:1197-1218` (the "every declared floor is measured" self-check) slices the
  source from the string `"def check("` to end-of-file (`body = src[src.index("def check("):]`)
  rather than isolating `check()`'s own body, so a constant referenced only in `report()`,
  `work_orders()`, or `main()` (which are defined later in the file) would still count as
  "measured" even if `check()` itself never reads it. No currently-declared `MIN_/MAX_`
  constant is actually in that situation (checked: none of `report`/`main`/`work_orders`
  reference any `MIN_`/`MAX_` constant directly), so this is currently harmless, but the
  self-check's own guarantee is narrower than its comment claims. **VERIFIED** as a scope
  looseness; **UNVERIFIED** as a live false-pass today (checked, found none).
- `weave_index.py:224` truncates each indexed entity's description to `[:400]` chars in
  `data/ENTITY_INDEX.json`/`WEAVE_CANDIDATES.json`. Traced its only consumer
  (`weave.py:filtered_index`, which re-slices to `desc[:300]`/`desc[:400]` for a regex gate) —
  the truncation does not currently feed any completeness-sensitive path, and the full text
  remains in `data/records/*.json` (the source of truth). Not flagged as a Hard-Rule-0
  violation; noted only in case a future consumer starts relying on the indexed description for
  adjudication content rather than pattern-matching.
- `catalogue_models.py:146,153` truncates the printed "current alternatives" suggestion list to
  `[:8]`/`[:10]` model IDs. This is report/console display only — the full model list is stored
  untruncated in `payload["providers"]`/`data/PROVIDER_MODELS.json`. COSMETIC, not a Hard-Rule-0
  breach.

## Clean

- `lognames.py` — read in full. Small, single-purpose constant/mapping module; the
  `OWNER` dict is consistent with every caller found (`standards.py`, `dashboard.py`, and
  `overnight.py`'s expectations per its own docstring cross-references). No findings.
- `catalogue_web.py` otherwise: Hard Rule 0 compliance verified directly — `MAX_PER_SOURCE`,
  `MAX_PER_CATEGORY`, `CATEGORY_SCAN_DEPTH` are all `None` and a `SystemExit` guard fires if
  `MAX_PER_SOURCE` is ever set non-`None` again; every `rank_by_size(..., top=None)` call is
  ranking-only, no truncation. Record writes are gated on `pipeline.write_record_catalogue`'s
  return value (verified: a denied write correctly avoids updating `entry_count`/`status`).
  No other findings beyond §5 above.
- `catalogue_models.py` otherwise: atomic write via `silence.write_json` (correct, modern
  pattern). No swallowed-failure or correctness issues found beyond the cosmetic note above.
