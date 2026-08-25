# Batch 12 audit — run27

Modules read in full, every line:
- src/overnight.py (766 lines)
- src/zfighters.py (485 lines)
- src/catalogue_web.py (403 lines)
- src/scout.py (287 lines)
- src/wh40k.py (238 lines)
- src/recover_folder_records.py (180 lines)
- src/module_index.py (83 lines)

Total: 2,442 lines across 7 modules.

No files were edited. Two live reproductions were run to confirm findings (`python zfighters.py`
and `python zfighters.py --full`), which is the only side effect of this audit beyond writing
this report — both are the module's own normal/documented invocation and wrote only its own
declared output file (`data/Z_FIGHTERS.json`).

---

## src/overnight.py

### 1. Line 145 — unconstrained whole-command-line substring fallback (HIGH, CONFIRMED, matches known-open)

```python
if fragment in cmd.replace("\\", "/").split("/")[-1] or fragment in cmd:
    return True
```

The first clause matches `fragment` against just the basename of the last path segment of the
command line — correct and scoped. The `or fragment in cmd` fallback matches `fragment` as an
**unconstrained substring anywhere in the full command line of any python.exe/pythonw.exe process
on the machine**, not scoped to this project's directory, argv position, or word boundary. The
module's own docstring (lines 97-100) already documents that an earlier bug in this exact area
("matched itself... any command that merely MENTIONED a stage's filename counted as that stage
running") was found and partially fixed via PID-based self-exclusion — but that fix addressed only
self-matching, not this fallback, which reopens the identical failure class against **other**
processes.

Concrete failure scenario: this machine runs many unrelated Python projects per the user's own
project index (aisling_companion, trading_bot, SAM, rent_engine, niamh, cooldown_guard,
myth-and-blood, motoko, cascade, orrery, undercentury, tcg_design, Oracle's Loom). `running()` is
called with generic basenames like `"dashboard.py"`, `"publish.py"`, `"read.py"`,
`"pipeline.py"` (STANDING, lines 372-380). If any unrelated project on this machine happens to be
running a python process whose full command line contains that substring anywhere — a log path
argument, a `--config` value, a docstring embedded in a `-c` inline script, or simply a
same-named script in a different directory — `running()` returns `True` for a job that is not
this project's job at all. Two concrete consequences:
- `run()`/`start()` (lines 167, 213) skip launching a stage that is genuinely down, logging
  `"already running, left alone"` when nothing of this kit's is actually running.
- The keeper thread (`_keep()`, lines 556-568) believes a STANDING job is up and never restarts
  it, leaving it down for the rest of the night while `foreman_report()`/`watch_report()` and the
  dashboard have no way to know the "already-running" verdict was a false positive from an
  unrelated process.

### 2. Lines 683 vs 711-712 — pipeline started as a standing background job, then separately "run" synchronously (MEDIUM, CONFIRMED structurally; causal link to the reported RED is SUSPECTED)

`pipeline` is in `STANDING` (line 379) and is fire-and-forget `start()`-ed at the top of every
cycle (line 683, return value **not captured** — unlike `roll = start(...)` two lines later, which
is captured and later `join()`-ed with a timeout). Later in the same cycle, after `read` and
`roll` finish, the code calls a **blocking** `run("pipeline", ...)` again (lines 711-712), with a
comment: *"Runs after the reader so it sees the evidence the reader just produced."*

Both calls guard on the same basename (`"pipeline.py"`) via `running()`. Because the STANDING
copy from line 683 is (by design) meant to be a long-lived, continuously-kept-alive service — the
keeper thread restarts it every 5 minutes if it's down — it will, in the overwhelming majority of
cycles, still be alive when execution reaches line 711. `run()`'s own guard
(`if running(...): return "already-running"`) then fires immediately, and the "runs after the
reader" step never actually happens as a synchronous, evidence-fresh pass; it just records
`"already-running"` and moves on. The comment at 709-710 promises a sequential per-cycle "absorb
the new feats" step that the code cannot reliably deliver once the singleton guard is doing its
job as designed elsewhere in the same file.

Whether this is a bug or deliberate (pipeline.py might loop and re-scan for new work on its own,
making the explicit `run()` call intentionally redundant/best-effort) I could not determine from
this module alone — `pipeline.py` is out of this batch. Flagging as a genuine question: if
pipeline.py does NOT loop internally, "fresh evidence after the reader" is not actually being
delivered most cycles, silently.

### 3. Extra-focus trace: how overnight relates to "job is slow rather than dead" (CONFIRMED re: overnight's own scope; SUSPECTED re: causing the reported RED)

`overnight.py` itself contains **no** stall/silence detection logic — `MAX_JOB_SILENCE_MIN` (15
min) lives in `standards.py:106`, and the kill itself (`kill_stalled_job`, wired to the standard
`"every running job is advancing"`) lives in `foreman.py:387,736`. Overnight's only two levers
touching a stalled job are: (a) the keeper thread restarting anything in STANDING that
`running()` reports down (lines 556-568), and (b) the cycle-top `start()` calls doing the same
thing inline. Neither has any concept of "slow but making progress" vs "genuinely wedged" — that
distinction lives entirely in whatever heartbeat/progress-print discipline the job itself follows
(see `catalogue_web.py`'s `_beat()` mechanism, added after run #25 for exactly this reason).

Since `pipeline` was moved into STANDING (comment at line 678-682: "THE GPU-SERIAL RULE IS
OBSOLETE"), it is now subject to the keeper's blind restart-if-down behaviour like the other four
standing services. If `foreman.kill_stalled_job` SIGTERMs `pipeline_auto` for exceeding 15
minutes of log silence while it is legitimately deep in a large batch (the exact pattern already
documented as the `catalogue_web.py`/DC-category failure mode, `catalogue_web.py:162-176`), the
keeper will restart it from scratch within 5 minutes with no memory of "this one was actually
working, just slow." Whether `pipeline.py` has its own resumable-progress/heartbeat discipline
that would make a restart cheap (as `read.py`/`feats.py --roll` are documented to have,
"work is cached, it resumes", line 197) is outside this batch — I could not confirm or refute it.
The structural exposure (STANDING membership = blind kill-then-restart, no slow-vs-dead
distinction) is confirmed from the code read here; whether it is the actual cause of the reported
`pipeline_auto (20 min, 26894 bytes)` RED is not.

### 4. Line 500 — `preflight()`'s blocking guard is a fragile double-literal-substring match (LOW, SUSPECTED/fragile-but-currently-correct)

```python
blocking = "control characters in source" in out and "FAIL  control" in out
```

Verified against `health.py:368`, `f"  FAIL  {label}"` with `label = "control characters in
source"` (`health.py:350`) — today's output line is `"  FAIL  control characters in source"`,
which satisfies both literal substrings, so the guard is **currently correct**. But this is the
single blocking condition in the entire supervisor (the docstring's "producing confident
emptiness" halt at lines 21-25) implemented as two independent hardcoded string fragments against
another module's print formatting. Any future rewording of `health.py`'s label, or a spacing
change in its `FAIL` print (`"  FAIL  {label}"` → `"  FAIL {label}"` etc.), silently disables the
halt rather than erroring — a default that fails in the dangerous direction (continues instead of
blocking) with no test coverage visible in this file to catch drift between the two modules.

---

## src/zfighters.py

### 1. Line 474 — `--full` crashes `KeyError: 'provenance'` on Son Goku (HIGH, CONFIRMED — live crash reproduced, matches known-open)

```
$ python zfighters.py --full
...
  File "...\zfighters.py", line 474, in main
    % (ax, d["score"], d["provenance"], d["cited"][:60]))
KeyError: 'provenance'
```

Root cause, traced: every `ROSTER`-derived record's `axes` dict is built at lines 417-418 as
`{"score": v[0], "cited": v[1], "provenance": v[2]}` (from the 3-tuples in `ROSTER`). But Goku's
record (line 438) is loaded verbatim from `data/REFERENCE_ASSAYS_PRESENCE.json["Son Goku"]`,
which has a **different axes shape** — verified directly:
`{"score": 3.5, "cited": "Exchanges with Jiren destabilise..."}`, no `"provenance"` key at all.
`main()`'s `--full` branch (line 473) applies the ROSTER shape's key set unconditionally to every
row in `rank`, including Goku's, and crashes on the very first axis it prints for him
(`A.WEIGHTS[0]`, `ruin`). The plain (non-`--full`) path avoids this because it never touches
`d["axes"][ax]["provenance"]`.

### 2. Lines 24-29 — headline claim is false against the module's own computed output (MEDIUM, CONFIRMED via live run, matches known-open)

The docstring states: *"ANDROID 17 ANCHORS AT M7, above Vegeta and every Earth-raised fighter
except Goku."* Live run of `compute()` + the module's own ranking (`value()`, sorted
descending) produces:

```
Vegito      𝔄 M7.63 ± 0.06
Android 17  𝔄 M7.60 ± 0.06
Gogeta      𝔄 M7.60 ± 0.06
Vegeta      𝔄 M7.53 ± 0.06
Son Goku    𝔄 M7.53 ± 0.06
```

Vegito — himself a fusion of two Earth-raised Saiyans, i.e. "Earth-raised" by any reading the
docstring intends — outranks Android 17 (7.63 vs 7.60). Gogeta ties Android 17 exactly at 7.60,
not below him. So the claim "above ... every Earth-raised fighter except Goku" is false on two
counts against the module's own arithmetic: Vegito is both Earth-raised and ranked above him, and
Gogeta is not below him at all. This is the docstring's own worked "result worth stating plainly"
— the thing the whole preamble is building to — contradicted by the code that computes it.

---

## src/catalogue_web.py

### 1. Lines 87-148 (`catalogue_composite`) — never received run #25's stall-avoidance heartbeat (MEDIUM, CONFIRMED, matches known-open)

`catalogue()` (the non-composite path) was rewritten with a `_beat()` heartbeat printed during
category discovery, ranking, and page fetching specifically because a silent multi-minute phase
on a large wiki category gets killed by `foreman.kill_stalled_job` under
`standards.MAX_JOB_SILENCE_MIN` (documented at length in the comment block, lines 162-181).
`catalogue_composite()` calls the identical slow operations —
`ws.category_members(sub, c, limit=None)` (line 100), `ws.rank_by_size(sub, titles, top=None)`
(line 105), `ws.page_texts(sub, wanted)` (line 113) — with **zero** progress callbacks anywhere
in the loop. Its only `print` (lines 128-129) fires once an entire `(sub, cats)` group is fully
done, i.e. exactly the "print nothing until a whole class is finished" behaviour the comment
block says was the original bug. A large sub-wiki category reached through a composite source
(`ws.COMPOSITE_SOURCES`) remains structurally killable by `kill_stalled_job` the same way DC was
before the fix.

### 2. Lines 199 vs 244 — stale `_short` label during the fetch-progress heartbeat (MEDIUM, CONFIRMED via static read)

```python
for canon in ws.CATEGORY_KEYWORDS:               # loop 1 (discovery)
    ...
    _short = canon.split(" (")[0][:16]            # line 199 — set per canon here
    ...
    if titles:
        planned.append((canon, cats, titles))
...
for canon, cats, titles in planned:               # loop 2 (fetch) — reuses `planned`
    ...
    texts = ws.page_texts(sub, wanted,
                          progress=lambda d, t: _beat(_short + " fetching", d, t))   # line 244
```

`_short` is a plain module-function-local variable, set inside loop 1 once per `canon` (line 199,
executed whenever `cats` is non-empty, whether or not that canon made it into `planned`). Loop 2
iterates over `planned` — a **different** set of `(canon, cats, titles)` tuples, potentially in a
different order and set — and never reassigns `_short` for its own current `canon`. Every
`" fetching"` progress line printed during loop 2 therefore carries whatever category label was
last set during loop 1's *final* iteration (the last canonical category `ws.CATEGORY_KEYWORDS`
walked that had any matching wiki categories), not the category actually being fetched at that
moment. This doesn't corrupt any written data — it only mislabels the operator-facing heartbeat
lines — but it directly undermines the observability run #25's fix exists to provide: a person
watching the log during the fetch phase sees the wrong category name for every canon except
coincidentally the last one.

### 3. Lines 95-127 (`catalogue_composite`) — dedup scoped across unrelated wikis, not per-wiki (MEDIUM, SUSPECTED / framed as a question)

`entries, seen = [], set()` (line 95) is declared **once**, outside the `for sub, cats in spec:`
loop, and the same `seen` set gates every sub-wiki in the composite spec (`key` built at line 108
from the normalized title only, with no `sub` component). If two different sub-wikis in a
composite source's spec each catalogue an entity under the same normalized name (plausible for
"invented pantheons of fiction across anime, film, television and games" per the module's own
provenance text, line 143 — deity/character names collide across franchises: "Loki",
"Ares", "Anubis"-styled original characters, etc.), only the **first** sub-wiki's version survives;
the second is silently treated as an already-seen duplicate and dropped, even though
`origin_work` (line 125) differs and the module's own docstring promises "Every entry records
which wiki it came from, so a merged source stays auditable per-item" (lines 90-91) — implying
distinct per-wiki entries are the expected shape. Under Hard Rule 0's framing ("a cap does not
fail, it returns a smaller universe wearing the same shape as the real one"), a same-named entity
from a second wiki silently vanishing looks like exactly that failure class, just triggered by a
name collision instead of a numeric limit. I could not confirm from this file alone whether
`ws.COMPOSITE_SOURCES`' actual specs are curated to avoid real collisions — flagging as a
question rather than an asserted bug.

### 4. Lines 76-84 (`save_roll`) — fixed-name temp file, no cross-process guard (LOW-MEDIUM, SUSPECTED)

`tmp = ROLL + ".tmp"` is a fixed path. Writes from this module's own thread pool are serialized
via `_wlock` (line 355, held around the `save_roll(roll)` call at line 391), so there is no
intra-process race. But `data/SWEEP_ROLL.json` is documented (line 77-79) as read by
`resync_roll.py` and written from elsewhere too; nothing in `save_roll()` guards against a second
**process** (a manual second invocation of `catalogue_web.py`, or `resync_roll.py` itself if it
also writes) using the identical `data/SWEEP_ROLL.json.tmp` path concurrently. This is the same
shape of exposure as the known WIKI_HOSTS.json race in `scout.py`, applied to `SWEEP_ROLL.json`.

### 5. Line 58 — `CATEGORY_SCAN_DEPTH` is a dead constant with a comment describing behaviour that no longer exists (LOW, CONFIRMED)

```python
# How deep to read a category before ranking. Must be well above MAX_PER_CATEGORY or ranking
# has nothing to choose from and the alphabetical bias returns.
CATEGORY_SCAN_DEPTH = None
```

Grepped the whole file: `CATEGORY_SCAN_DEPTH` appears only at its own definition (line 58) and in
this comment. It is never read anywhere in `catalogue()` or `catalogue_composite()`. The comment
describes a scan-depth-vs-ranking relationship that isn't wired to anything — harmless (the value
is `None` and unused, not a live cap), but it's a comment asserting a mechanism the code doesn't
implement.

---

## src/scout.py

### 1. Lines 200-206 — unlocked read-modify-write of shared `WIKI_HOSTS.json` (HIGH, CONFIRMED, matches known-open)

```python
hosts = json.load(open(F.HOSTS, encoding="utf-8"))
hosts[source] = "pages:" + source
_land(F.HOSTS, hosts)
```

No lock around the read-mutate-write sequence. `_land()` itself is atomic (tmp + `replace_retry`,
lines 55-65) but that only makes the *write* atomic — it does nothing about a second writer
having already read a now-stale copy of `hosts` before this one lands. This is one of the >=4
call sites project-wide noted in the task brief (others are in `hostcheck.py`, out of this
batch). Concrete scenario: `scout.py --source X` and `hostcheck.py`'s own adopt loop (or a second
`scout.py` invocation) both read `WIKI_HOSTS.json` at the same time, each adds a different
source's key in memory, and whichever writer's `replace_retry` lands second **silently discards**
the other's addition — last-write-wins on the whole file rather than a merge, so one source's
newly-discovered host mapping is lost without any error being raised anywhere.

### 2. Lines 208-218 vs the `--dry` flag (MEDIUM, CONFIRMED)

`main()`'s `--dry` flag is documented as *"verify but do not register"* (line 269) and correctly
gates the `WIKI_HOSTS.json` write: `if kept and register:` (line 197). But the blocked-URL
bookkeeping a few lines later is **not** gated by `register` at all:

```python
blocked = [c for c in checked if c.get("code") in (401, 403, 429)]
if blocked:
    ...
    _land(BLOCKED, prev)     # writes data/SCOUT_BLOCKED.json unconditionally
```

A `--dry` run still durably mutates `data/SCOUT_BLOCKED.json` — appending to and persisting a
per-source list of blocked URLs — even though the flag's own help text promises no registration
side effect. Whether "register" was ever meant to cover the blocked-list bookkeeping is arguable,
but the code's actual behaviour doesn't match a reasonable reading of "dry run" for anyone
exercising `--dry` expecting zero on-disk mutation.

### 3. Lines 78, 176-179, 193 — `PROBE_NAMES = 25` caps the verification sample, unranked (LOW, question/SUSPECTED, not asserted as a Hard-Rule-0 violation)

```python
PROBE_NAMES = 25
...
sample = [n for n in names if n and len(n) > 3][:PROBE_NAMES]
```

`sample` — the first 25 qualifying names in whatever order `names` arrives, not ranked by any
measure — is used both to prompt the model for candidate URLs (line 178, further sliced to 18)
and, more consequentially, to **verify** every candidate URL (`verify(u, sample)`, line 193): a
page is accepted only if it contains `>= MIN_NAME_HITS` (2) of these same 25 names. For a source
with a large catalogue, a genuine index/compendium page covering a name-disjoint subset of the
same source could fail verification purely because none of its covered names happened to land in
the arbitrary first-25 sample, or conversely a page could pass on a thin coincidental overlap.
This does not truncate anything that gets *stored* (the full catalogue is untouched), so it's not
a clear Hard Rule 0 violation, but it is a `[:N]` slice feeding a pass/fail gate — flagging as a
design question rather than a confirmed bug.

---

## src/wh40k.py

### 1. Lines 230-231 — raw `open(...,'w')` + `json.dump` to shared `data/WH40K_ASSAYS.json` (HIGH, CONFIRMED, matches known-open)

```python
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
```

No `silence.write_json`/`replace_retry` anywhere in this file — `silence` is not even imported
(compare the full `import` block, lines 31-38, against `zfighters.py`'s, which imports `silence`
at line 44). This is a direct two-writer-contract violation (lens 4): `data/WH40K_ASSAYS.json` is
written truncate-first, dump-second, with no atomicity. The sibling module in this same batch,
`zfighters.py`, has the **identical** output pattern (`compute()` → rank → optional `--full` →
write) and was fixed for exactly this at `zfighters.py:478` with an explicit comment: *"ATOMIC.
`data/Z_FIGHTERS.json` is read by `pantheon.py`, so a crash mid-write corrupts a file another
module consumes. The m100 tail, 2026-08-25."* `wh40k.py` was never visited by that same fix — a
textbook case of "a fix applied to one file while the identical construction in a sibling module
was never visited." A crash or kill mid-write (e.g. hitting `overnight.py`'s `timeout_h`, or a
manual interrupt) leaves `data/WH40K_ASSAYS.json` truncated/unparseable for whatever reads it
next.

---

## src/recover_folder_records.py

### 1. Lines 145-148 — direct-to-disk write bypasses `pipeline.write_record_catalogue` (LOW, self-documented by the module, CONFIRMED still open)

The script's own comment explicitly flags this:

> "NOTE FOR REVIEW: the two-writer contract says a RECORD should be written through
> `pipeline.write_record_catalogue`, not straight to disk at all. Making the write atomic is the
> safe half of that repair; routing this recovery tool through the catalogue writer changes its
> merge semantics and is flagged in NEXT_STEPS."

The write itself IS atomic (`silence.write_json`, correctly gated on its return value at line
155-157, unlike an earlier version the same comment block describes as having ignored it). This
is not a new finding — the module's author already identified and partially mitigated it — but
confirming it is still true as of this read: if a source name is both mapped in
`FOLDER_SOURCE_MAP.json` (this script's domain) and independently resolvable by
`catalogue_web.py` (which writes the same `data/records/<slug>.json` path via
`pipeline.write_record_catalogue`, a different code path with different merge semantics), the two
writers have no shared merge contract between them — whichever runs second overwrites the other's
record wholesale rather than merging.

---

## src/module_index.py

### 1. Line 75 — raw `open(...,'w')` write to `handoff/MODULE_INDEX.md` (LOW, CONFIRMED)

```python
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
```

Not atomic (no tmp+replace). `MODULE_INDEX.md` is documentation, not shared pipeline JSON state,
so this is likely outside the letter of the two-writer contract (which names "shared state/JSON
files" specifically) — flagging at low severity since the practical blast radius (a truncated
onboarding doc, regenerable by rerunning the script) is small, but noting it for consistency since
the module's own docstring insists "Generated, never hand-edited" implies people trust this file
as always-valid-or-absent, which a mid-write crash would violate.

### 2. Line 2 — stale module count in the docstring (LOW, CONFIRMED, cosmetic only)

Docstring: *"the map of the 87 modules"*. Actual count of `src/*.py` files as of this read: 95
(verified via directory listing). The generated output itself is unaffected — `main()` computes
the real count dynamically (line 52-53, 77) and the hardcoded "87" is never used in logic, only
in prose — so this is a pure comment/reality drift, not a functional bug.
