# BATCH 11 AUDIT — run29

Modules: `dashboard.py`, `zfighters.py`, `catalogue_web.py`, `cosmography.py`, `wh40k.py`,
`audit.py`, `resync_roll.py`

Method note: every finding below was checked by reading, and every finding flagged
REPRODUCED was additionally driven with a real Python process using the miniconda
interpreter (`PYTHONIOENCODING=utf-8 C:/Users/imarl/miniconda3/python.exe`), either by
calling the real function with a rigged environment, or — where the real code path needs
live network/wiki access not available here (catalogue_web.py's threaded cataloguer) — by
isolating the exact write primitive from the source file and running it under real OS
thread/process concurrency to demonstrate the mechanism.

---

## dashboard.py (781 lines)

### 1. `watch()` / `_watch()` — unreadable OVERWATCH.json reports a clean sweep, not UNMEASURED
**Severity: HIGH.** **REPRODUCED.**

`src/dashboard.py:301`:
```python
out = {"open": 0, "high": 0, "rounds": 0, "findings": [], "broken": []}
try:
    d = json.load(open(os.path.join(DATA, "OVERWATCH.json"), encoding="utf-8"))
    ...
except Exception:
    silence.note("dashboard.py:watch")
```
The defaults are assigned **before** the try, exactly the anti-pattern named in the audit
brief ("defaults set before a try so a failure is indistinguishable from a real zero").
When `data/OVERWATCH.json` cannot be read (missing, mid-write, permission-denied — all
things this same project's own `silence.py` docstring says happen on Windows), `watch()`
silently returns the all-zero dict. The client JS (`panelWatch`, around
`src/dashboard.py:697`) then renders:

```
open findings: 0 (0 high) after 0 round(s)
"Nothing open — every finding was fixed or retired when its file changed."
```

That second line is not merely absent data, it is an **affirmatively false claim** — it
asserts every finding was resolved, when the true state is "the overwatch ledger could not
be read." This is precisely dashboard.py's own special charge: a standard/panel that
cannot be computed must say UNMEASURED, not vanish into looking green. `quotas()`
(`src/dashboard.py:96-135`) already does this correctly elsewhere in the same file — on
total failure it appends an explicit `{"bucket": f"quota read failed: {type(e).__name__}"}`
row rather than defaulting to a healthy-looking value. `watch()` does not follow that
pattern.

Reproduction: pointed `DATA` at an empty temp directory (no `OVERWATCH.json`,
`failures.json`, or `COVERAGE.json`) and called `dashboard.watch()` directly:
```
D.DATA = tmpdir; D.STATE = tmpdir
D.watch()  ->  {'open': 0, 'high': 0, 'rounds': 0, 'findings': [], 'broken': []}
```
Bit-for-bit identical to "the sweep ran and found nothing wrong."

**Fix direction:** move the dict literal inside the try (or after a success flag), and add
an explicit `"unreadable": True` (or similar) key on the exception path that
`panelWatch()` renders distinctly from the zero-findings case.

### 2. `throughput()` — a broken metrics DB reads as "quiet system", not "instrument broken"
**Severity: MEDIUM-HIGH.** **REPRODUCED.**

`src/dashboard.py:155`:
```python
out = {"window_min": minutes, "calls": 0, "per_hour": 0, "buckets": []}
try:
    c = sqlite3.connect(path)
    ...
except Exception:
    silence.note("dashboard.py:throughput")
return out
```
Same shape as finding 1. If `state/cascade_scratch.db` is missing, locked, or lacks the
`usage` table (which is exactly what happens on a fresh/reset state directory —
`sqlite3.connect` on a nonexistent path silently creates an empty new DB file, then the
`select ... from usage` raises `OperationalError: no such table: usage`), `throughput()`
returns the same `{"calls": 0, "per_hour": 0, "buckets": []}` a genuinely idle system would
produce. The "Provider spend" panel then shows "0 calls per hour" / "Nothing has called out
recently" — read by the owner as "nothing is happening" when the real fact is "the
throughput instrument itself is dead."

Reproduction: pointed `STATE` at an empty temp dir (no `cascade_scratch.db`) and called
`dashboard.throughput()` directly:
```
D.STATE = tmpdir
D.throughput()  ->  {'window_min': 15, 'calls': 0, 'per_hour': 0, 'buckets': []}
```

**Fix direction:** same as finding 1 — don't pre-seed the numeric defaults before the try;
carry an explicit failure flag through to the panel.

### 3. `movement()` — fixed-name temp file raced by the dashboard's own HTTP threads
**Severity: MEDIUM.** **REPRODUCED (mechanism, isolated).**

`src/dashboard.py:374-382`:
```python
tmp = HISTORY + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(hist, f)
silence.replace_retry(tmp, HISTORY)
```
This is a hand-rolled atomic write using a **fixed** temp filename — not
`silence.write_json()`, which this same project's own docstring (`src/silence.py:250-268`,
dated 2026-08-25) says is "the one correct way to write a shared file in this project"
specifically **because** the old `path + ".tmp"` idiom lets two concurrent writers of the
same file collide on the temp file itself and have "the loser... replace the winner's
target with a partial file." `movement()` is called from `state()`, which is called from
every `GET /api/state` request, and the server is a `socketserver.ThreadingTCPServer` with
`daemon_threads=True` (`src/dashboard.py:750-752`) — **a new thread per HTTP request, with
no lock around this write.** Two browser tabs open on the dashboard, or a monitoring script
polling alongside a human's browser, produce two threads racing on the identical
`state/dashboard_history.json.tmp` path.

Reproduction: extracted the exact write sequence from `movement()` (fixed tmp name, no
lock) and ran it from two real Python threads with an artificial mid-write pause to widen
the natural race window (necessary because on a small/fast history file the window is
normally sub-millisecond, not because the underlying mechanism differs):
```
A fragments: 3011   B fragments: 989   total bytes: 102890
CORRUPTION CONFIRMED: two threads writing dashboard_history.json.tmp under the same
fixed name interleave into one file.
```
The consequence in the real code is bounded but real: `movement()`'s own "must heal, not
wedge" logic (added in run #26, `src/dashboard.py:340-359`) will catch the resulting
`JSONDecodeError` on the *next* read and reset history to empty — so the failure mode is
"the Movement panel silently loses up to 24h of trend data," not a hard crash, but it is a
genuine unguarded shared-file race matching lens item 6 exactly, in the one file this batch
was asked to give special scrutiny to.

**Fix direction:** either wrap the read-modify-write in the same `threading.Lock` pattern
`catalogue_web.py`'s `_wlock` uses, or switch to `silence.write_json(HISTORY, hist)`, whose
pid+thread-tagged temp name makes the collision structurally impossible.

### 4. `movement()` — "standards met" conflates ST.check() failure with zero standards holding
**Severity: LOW.** **VERIFIED-BY-READING.**

`src/dashboard.py:347`:
```python
"standards met": sum(1 for x in (now_state.get("standards") or []) if x.get("holds")),
```
`state()` sets `s["standards"] = []` whenever `standards.check()` raises
(`src/dashboard.py:471-475`). The Standards panel itself handles this correctly client-side
(`panelStandards` shows "Standards not readable." for an empty list —
`src/dashboard.py:591-593`), so this is not a repeat of findings 1-2. But `movement()`
still computes `"standards met": 0` for that same tick and appends it to
`dashboard_history.json` as a real, comparable data point. A later `/api/state` poll, once
`standards.check()` recovers, will show a large *positive* delta for "standards met" (e.g.
+40 in N minutes) that is really "the check started working again," not "40 standards
newly started holding." A `standards.check()` outage that straddles a poll in the other
direction would equally show a large synthetic *negative* delta, which — per the movement
panel's own stated purpose of catching "every counter flat while every job is up" — is
exactly the kind of false signal this panel exists to avoid on every *other* metric (see
the "reset" handling for the `chunks` counter one function up, which this project already
fixed for exactly this class of problem in run #26).

**Fix direction:** only include `"standards met"` in the `keys` dict when
`now_state.get("standards")` is non-empty, mirroring how `library`/`readfeats`/`chunks`
already go missing from `keys` rather than reporting a fake zero when their own source is
unavailable.

No other issues found in dashboard.py. The file is otherwise unusually well hardened —
almost every panel already has a documented fix history (run #19, #26, #27, #28) for
exactly this class of bug, which is why findings 1-3 stand out as the panels that class of
fix hasn't reached yet.

---

## catalogue_web.py (403 lines)

### 1. `save_roll()` still uses the fixed-name-tmp pattern every sibling writer was just fixed off of
**Severity: HIGH.** **REPRODUCED (mechanism, isolated).**

`src/catalogue_web.py:75-84`:
```python
def save_roll(roll):
    # Atomic for the same reason the record write beside it is: SWEEP_ROLL.json is written from
    # three worker threads here and read elsewhere by `load_roll` and `resync_roll.py`, BOTH of
    # which do an unguarded `json.load`. A truncating write interrupted mid-dump therefore does
    # not degrade anything gracefully -- it kills the next run of either script outright.
    import silence as _sil
    tmp = ROLL + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(roll, f, indent=2, ensure_ascii=False)
    _sil.replace_retry(tmp, ROLL)
```
The docstring correctly identifies the hazard and even name-checks `replace_retry`, but the
temp path is still the bare fixed name `ROLL + ".tmp"` rather than
`silence.write_json()`'s pid+thread-tagged name. Compare the two OTHER cataloguers that
write this exact same file, both updated **today** (2026-08-25, per their own comments):

```
src/catalogue_aurora.py:158-159:
    # ATOMIC: four scripts write this same roll (see silence.write_json). 2026-08-25.
    silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)

src/catalogue_codex.py:209:
    silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)
```
`silence.write_json`'s own docstring (`src/silence.py:250-268`) states plainly: "Four of
those sites were writing the SAME file — `data/SWEEP_ROLL.json` — from four different
scripts... `catalogue_web.save_roll()` had the atomic version." **That claim is currently
false of the code on disk** — `catalogue_web.py`'s `save_roll()` has the `replace_retry`
half of the fix (safe against a torn/partial write reaching the final path) but not the
fixed-temp-name half (unsafe against two writers of the file colliding on the temp file
itself), which is the specific hazard `silence.write_json`'s docstring spends four
paragraphs on.

Within one run of `catalogue_web.py` itself, `save_roll()` is called under a
`threading.Lock` (`_wlock`, `src/catalogue_web.py:353-391`), so its own three worker
threads don't race each other. But `resync_roll.py`'s own docstring documents the actual,
previously-observed incident this bug class causes: *"That happened once here — the Aurora
run wrote 425 entries for Dr. Firestorm's Engineering Corps and 681 for The Elements
Beyond, then the wiki run's final save reset both to 0 while leaving the record files
untouched."* That is a `catalogue_aurora.py` process and a `catalogue_web.py` process
(**"the wiki run"** is this file) both writing `SWEEP_ROLL.json` at the same time — a
`threading.Lock` inside one process provides zero protection against a second OS process
running concurrently, which is lens item 6 by name ("threading.Lock used where processes,
not threads, contend"). `catalogue_aurora.py` has since been migrated off the vulnerable
pattern; `catalogue_web.py` — the very script the historical incident names — has not.

Reproduction: isolated `save_roll()`'s exact I/O (fixed tmp name, `open("w")`,
`os.replace` with retry) and ran it from two separate OS processes writing different
payloads to the same fixed tmp path:
```
bytes landed: 182890
entry_count=111 fragments: 3087   entry_count=222 fragments: 913
CORRUPTION CONFIRMED: both writers' bytes landed interleaved in one file because they
shared the fixed tmp name and thus the same inode.
```
This is the identical corruption shape (byte-interleaved, not merely last-writer-wins) that
a second concurrent `catalogue_web.py`/`catalogue_aurora.py`/`catalogue_codex.py` run would
produce against `data/SWEEP_ROLL.json.tmp`.

**Fix direction:** replace `save_roll()`'s body with
`silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)`, matching its two siblings
exactly — the `_wlock` around the call site can stay (it still serializes this process's
own three threads, which is harmless), but the temp-name fix needs to land in this file too.

No other issues found in catalogue_web.py. Hard Rule 0 is enforced unusually well here:
`MAX_PER_SOURCE`/`MAX_PER_CATEGORY`/`CATEGORY_SCAN_DEPTH` are all `None` with a
`SystemExit` guard (`src/catalogue_web.py:213-216`) that fires if anyone reintroduces a
numeric cap, and `rank_by_size(..., top=None)` is called with an explicit "rank, never
truncate" comment at both call sites (`src/catalogue_web.py:105, 233`). `--limit N` on the
CLI (`src/catalogue_web.py:328-329`) is an operator-controlled *how-many-sources-this-run*
batching knob, not a within-source data cap, and is out of scope for Hard Rule 0.

Minor, non-blocking observation: per-source exceptions inside the `ThreadPoolExecutor`
worker (`src/catalogue_web.py:365-367`, bare `except Exception as e:` with no
`silence.note()` call) are printed to stdout and tallied as failed, so they are not silently
swallowed for the operator running the command — but they also never reach
`state/failures.json`, so a `catalogue_web.py` run's per-source failures won't surface on
the dashboard's "swallowed failures" panel the way failures elsewhere in the project do.

---

## resync_roll.py (81 lines)

**No findings.** This module was itself the subject of a fix landed today (its own
docstring is dated against the exact incident quoted above) — `silence.write_json(ROLL,
roll, ...)` at `src/resync_roll.py:68` is correctly pid+thread-tagged, and the
per-record-file read at `src/resync_roll.py:42-47` is individually guarded so one corrupt
record file can't abort the whole resync. Status handling at line 63
(`r["status"] = "catalogued" if n else r.get("status", "catalogued")`) has a narrow
theoretical edge (a roll row missing its `status` key entirely, with a record file that has
since gone to zero entries, would get labeled `"catalogued"` by the `.get(..., "catalogued")`
default rather than something like `"empty"`) — flagged as HYPOTHESIS only; it requires a
roll row that's simultaneously missing `status` and drifted-to-zero, which the normal
cataloguer-write path shouldn't produce, and is not worth ranking as a real finding.

---

## audit.py (177 lines)

**No findings.** `audit_invariants()` runs over `PL.records()` unfiltered (verified
`pipeline.records()` glob-reads every file in `data/records/*.json` with no cap) and every
violation category accumulates its full count in `stats`/`fails`, printed in full
(`f"{len(v):,} occurrences"`). The `[:4]` slice at `src/audit.py:145` and the `--sample
14`/`10` random draws at `src/audit.py:117, 157, 170` are clearly-labeled console-preview
truncation over an already-complete, unbounded violation count and stats dict — the
INVARIANTS pass itself (the exhaustive half) never truncates. The core-invariant check
("BAND WITH NO SCALE NOTE") and the meta-language/topic/category checks are all genuine
conditionals against real gate functions in `pipeline.py`, not tautologies. Return code
(`1 if fails else 0`) is correctly wired for use as a CI/gate signal.

---

## cosmography.py (282 lines)

**No findings.** Pure-math module; ran `census()` directly and confirmed the derivation
chain and `validate()`'s physical-impossibility checks are non-tautological (they compare
independently-derived quantities like Kardashev Type III headcount against galaxy count,
not a value against itself), and confirmed `kardashev_to_magnitude()`'s bracket-scan against
`assay.BAND_EDGES`/`assay.LADDER` is correctly ordered ascending (`M0`→100 J through
`M10`→1e99 J), so the "keep updating `reached` while `annual_joules >= edge`" loop lands on
the correct (highest-satisfied) band rather than the first. `validate()` genuinely can and
does fail — the module's own comment documents a real prior catch (Type III count exceeding
galaxy count under an earlier `KARDASHEV_MIX`) — so this is not a check that cannot fail.

---

## wh40k.py (244 lines)

**No findings.** Twin of `zfighters.py` in structure; its own in-code comment
(`src/wh40k.py:230-236`) documents that the atomic-write gap `zfighters.py` had was found
and fixed in this file too as of run #27 — confirmed the code matches: `main()` ends with
`silence.write_json(OUT, out, indent=1, ensure_ascii=False)` at `src/wh40k.py:237`, not a
raw `json.dump`. Hand-authored assay content (magnitude/axis scores with cited evidence) is
subjective narrative judgment, not something this audit can validate programmatically, and
is out of scope for the correctness/caps/swallowed-failure lens.

---

## zfighters.py (486 lines)

**No blocking findings.** Output write is atomic (`silence.write_json`,
`src/zfighters.py:478`, with its own comment citing the same run-#27/"m100 tail" fix as
wh40k.py). One minor observation:

`src/zfighters.py:434-440`:
```python
try:
    p = os.path.join(HERE, "data", "REFERENCE_ASSAYS_PRESENCE.json")
    with open(p, encoding="utf-8") as f:
        out["Son Goku"] = json.load(f)["Son Goku"]
except Exception:
    silence.note("zfighters.py:goku")
```
**HYPOTHESIS, currently not manifesting** — verified `data/REFERENCE_ASSAYS_PRESENCE.json`
exists and parses with a `"Son Goku"` key today, so the roster is currently complete. But if
that file goes missing, is renamed, or the `"Son Goku"` key is ever dropped/renamed upstream
(e.g. during the presence-thesis rebuild this comment references), `main()` would silently
print and write a fifteen-fighter roster with no error surfaced beyond
`state/failures.json` — the printed ranking table and `Z_FIGHTERS.json` would both look like
a complete, successful run. Given the file this roster is explicitly built to be read
alongside (`pantheon.py`, per the write-site comment) would then also silently lose Goku
from any ranking that reads `Z_FIGHTERS.json`, this is worth a one-line hardening (e.g. print
a visible warning to stdout, not just the failures ledger, when the Goku carry-in fails) but
is not a live bug today.

---

## Coverage

`sweep_plan.record('run29', [...7 modules...], batch=11)` — see step (b) below for the
actual invocation; run separately after this report was written.
