# AUDIT — run29, batch 02

Modules: `src/pipeline.py`, `src/anchors.py`, `src/coverage.py`, `src/resonance.py`
Method: full read of all four files (pipeline.py is 1,910 lines, read in two passes), plus
targeted reads of `src/silence.py`, `src/weave.py`, `src/cosmology_graph.py`, `src/feats.py` where
a claim in one of my four files depended on their behaviour. Every finding below marked
REPRODUCED was exercised with a driver script under the session scratchpad, using
`C:/Users/imarl/miniconda3/python.exe`, against the real project modules — never against a
rewritten copy. No file under `src/` was edited.

---

## src/pipeline.py

### 1. [HIGH] [REPRODUCED] Fixed-name temp files race across every atomic writer in this file —
crashes with an uncaught `FileNotFoundError`, the exact class of bug `silence.write_json` was
built today to close, and this file was never migrated to it

**Where:** `save_state` (pipeline.py:183-188), `write_record_catalogue` (pipeline.py:460-463),
`write_record` (pipeline.py:561-564), `land_json` (pipeline.py:497-500) — all four use the
identical pattern:
```python
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(obj, f, ...)
silence.replace_retry(tmp, path)
```

**What it claims / what the project already knows:** The two-writer contract this file
documents and enforces (`write_record` is the pipeline's writer, `write_record_catalogue` is the
catalogue's) explicitly exists *because* multiple separate processes write the same record
files concurrently — that is the entire reason the merge logic in both functions exists.
`update_handoff`'s own generated markdown (pipeline.py:1316-1321) even warns the owner: "Two
concurrent runners both write `PIPELINE_STATE.json` and the same record files; that happened on
2026-08-21 and the records survived by luck." This is a *known*, previously-observed hazard.

`src/silence.py`'s `write_json` (added **2026-08-25**, today) was written specifically to close
this: its docstring says outright, "THE TMP NAME CARRIES PID AND THREAD, which the older
hand-rolled `path + ".tmp"` sites did not. Two writers of the same path otherwise collide on the
temp file itself, and the loser can replace the winner's target with a partial file." `coverage.py`
was migrated to `silence.write_json` for exactly this reason **the same day** (see coverage.py:182,
"This file's own cache-save two functions above already lands atomically; the headline write did
not. 2026-08-25."). `pipeline.py` — the file that actually *implements* the two-writer contract
(`write_record` / `write_record_catalogue`) and has by far the most write call sites — was not
migrated. It still uses the fixed `path + ".tmp"` pattern `silence.write_json`'s own docstring
names as the bug.

**What actually happens (reproduced):** `silence.replace_retry` (silence.py:223-240) only catches
`PermissionError`. When two writers race on the *same* fixed tmp filename for the same destination
path, `os.replace` on Windows deletes the source as part of the rename — so if writer B's
`os.replace(tmp, path)` fires first, writer A's later `os.replace(tmp, path)` call raises
`FileNotFoundError`, which `replace_retry` does not catch. Driver script
(`scratchpad/run29b2/repro_fixed_tmp_race.py`) simulates exactly `write_record`'s (pipeline
side) and `write_record_catalogue`'s (catalogue side) write pattern in two threads racing on one
destination path:

```
Exception in thread Thread-1 (writer_A_pipeline_entrypass):
  File "...\src\silence.py", line 233, in replace_retry
    os.replace(tmp, dst)
FileNotFoundError: [WinError 2] The system cannot find the file specified:
  '...\marvel.json.tmp' -> '...\marvel.json'
writer A's replace_retry reported landed: None
writer B's replace_retry reported landed: True
FINAL file content on disk: {"writer": "B-catalogue-growth", "entries": ["30207-entry-recatalogue"]}
```

**Consequence:** the phase that hits this (any phase calling `write_record` while a concurrent
`backfill.py` / `catalogue_web.py` / `ingest_doc.py` process calls `write_record_catalogue` on the
same source — which the project's own contract says happens routinely) gets an *uncaught*
exception. `main()`'s broad `except Exception: log("PHASE CRASHED..."); save_state(st); return`
(pipeline.py:1862-1865) catches it at the top level, so the process does not hard-crash and state
is saved — but the whole phase run halts immediately and must be restarted by hand, rather than
the pipeline continuing past one bad unit the way its own header docstring
("costs at most one unit") promises. This is not a data-loss bug; it is a reliability bug that
directly reproduces the class of failure the project fixed in `silence.py` the same day and did
not carry through to its own busiest writer.

**Fix direction (for the supervisor, not applied here):** route `save_state`, `write_record`,
`write_record_catalogue`, and `land_json` through `silence.write_json` (or otherwise give the tmp
file a PID/thread-unique name before the atomic rename), the same way `coverage.py` was migrated
today.

---

### 2. [HIGH] [REPRODUCED] `phase_entrypass` binds `entries = rec["entries"]` once per source at
the top of a phase documented as "multi-day"; entries a concurrent catalogue writer appends to
that exact source while entrypass is already iterating it are silently never judged in this run

**Where:** pipeline.py:1037-1046 (`entries = rec["entries"]` bound once, `range(0, len(entries),
ENTRY_BATCH)` computed from that one binding) interacting with `write_record`'s disk-merge
(pipeline.py:518-537).

**What the code claims:** The large comment block at pipeline.py:1050-1066 ("A CLOSED BATCH IS
NOT A CLOSED SPAN") describes and claims to fix exactly this class of bug — a record's entry list
growing after entrypass has already closed a batch over it — citing a real incident (Arcanum
Worlds grew from 292 to 297 entries after batch #280 closed, 5 entries stranded). The fix
(`batch_settled` re-checking the *current* span against `done_keys`) genuinely works **across
separate process invocations**, because `records()` re-reads every file from disk fresh each time
`phase_entrypass` starts. `phase_entrypass`'s own docstring calls the phase "Multi-day; fully
resumable" (pipeline.py:1038) — describing one long-lived, continuously-running process, not one
restarted every batch.

**What actually happens (reproduced):** within *one* continuous run, `entries` is a live Python
list reference captured once per source (`entries = rec["entries"]`, pipeline.py:1046) and never
reassigned afterward. `write_record`'s drift-merge (triggered when disk has grown, e.g. because a
concurrent `ingest_doc.py` / `backfill.py` call to `write_record_catalogue` appended a new entry to
*this exact source* while entrypass is mid-way through its batches for it) builds a **new** dict
(`merged = disk`, pipeline.py:535) and writes that to the file correctly — but never touches the
caller's `rec` or `entries` object. Driver script
(`scratchpad/run29b2/repro_writerecord_stale.py`) calls the real `pipeline.write_record_catalogue`
then the real `pipeline.write_record` in the exact sequence `phase_entrypass` uses:

```
entries length bound at start of source loop: 2
disk entries after concurrent catalogue append: ['A', 'B', 'C']
write_record: testsrc.json drifted on disk (2 -> 3 entries); merged
disk entries AFTER write_record() call: ['A', 'B', 'C']
did write_record's merge correctly preserve C on disk? True

caller's in-memory `entries` list after write_record(): ['A', 'B']
caller's in-memory rec['entries'] is entries object: True
Did the caller's own `entries`/`rec` ever learn about C? False
```

**Consequence:** the file on disk is correct (no data loss at rest — `write_record`'s merge does
its job), but *this run's* `phase_entrypass` will never see, batch, or judge the appended entry
for the remainder of its process lifetime, however many days that is. It is not marked
`catalogued`, gets no `scale_note`, no `magnitude`, no `topic` — for the whole run. The very next
process restart of `phase_entrypass` picks it up correctly (because `records()` re-reads from
disk), so this is not permanent, but for a phase whose own docstring describes it as multi-day and
long-running, and whose whole `allrecs = records()` snapshot (pipeline.py:1040) is taken once at
phase start for *every* source (not just the one mid-processing), this is a real gap between what
the code's own comment claims was fixed and what it actually guarantees for the continuous-run
case the phase is designed for.

---

### 3. [LOW] [VERIFIED-BY-READING] `phase_synthesis`'s description-only ceiling-nomination
fallback truncates to 14 entries — deliberately, with cited rationale, but still a literal
Hard-Rule-0-shaped slice

**Where:** pipeline.py:693-707, specifically:
```python
chunks = [with_feats[i:i + 14] for i in range(0, len(with_feats), 14)] or [rest[:14]]
```
When a source has **zero** feat-bearing entries (`with_feats` empty), only the top 14 entries by
description length (`rest[:14]`) are ever shown to the model for the source's power-ceiling
nomination — out of what can be a roster of hundreds. Every feat-bearing entry (`with_feats`) is
correctly uncapped and chunked in full, per the comment directly above citing BUGS m13 and the
owner's "FIX IT ALL" ruling — this fallback is the one path left capped.

The comment defends this explicitly, citing measured evidence that a lead-paragraph description
essentially never demonstrates a feat (the "99.6% unassayed" finding referenced twice in this
file), so widening the sample would spend calls without changing outcomes in the observed cases.
That is a real, cited rationale — not an oversight — so I am not calling this a bug outright. But
it is still a `[:14]` slice of a real roster in a project whose Hard Rule 0 says "Ranking is still
allowed... Ranking then truncating is not," and the one scenario it forecloses (a source whose true
ceiling entity happens to be correctly identifiable from description alone, but isn't the 14
longest) cannot be checked by this code — it is asserted from a corpus-wide statistic, not
guaranteed per-source. Worth a second look from the owner given the rule it sits next to, not an
urgent fix.

---

## src/anchors.py

No correctness defects found. This file is a validation harness (five reference cases exercised
against `assay.py`/`physics.py`/`custodes.py`/`rigor.py`, none of which are in this batch), and its
own previously-documented failure mode — `run()` computing an invariant and discarding it, so
`sys.exit` always returned 0 (BUGS m26, comment at pipeline.py:236-248) — **is currently fixed and
verified working**: I ran `src/anchors.py` directly with the miniconda python; the ordering
invariant is (correctly, per the script's own honest report) currently violated on real data
(`Yggdrasil` 6.18 sits above `Goku` 5.42, out of floor-to-ceiling order), and the process **exits
1**, not 0, confirming the exit-code guard the comment describes actually works today:

```
monotone floor -> ceiling : False
   The Skate Guy                  0.22
   A Sword                        0.10
   Yggdrasil                      6.18
   Goku                           5.42
   The Seat of the Creator       10.99
ACTUAL EXIT CODE: 1
```
(My first attempt at capturing the exit code went through a `| tail` pipe and read `tail`'s exit
status, not Python's — that was my own test-harness mistake, corrected in the run above. Recording
it here so it isn't mistaken for a finding.)

The invariant violation itself (Yggdrasil outscoring Goku) is a reading about `assay.py`'s scoring,
which is out of this batch's scope, and the script already surfaces it honestly rather than hiding
it — exactly what it exists to do.

---

## src/coverage.py

No significant defects found. `measure()` iterates every entry of every record with no cap
(Hard Rule 0 compliant); `report()`'s `[:12]` / `[:show]` (default 26) / `[:10]` slices are
confirmed DISPLAY-only previews for the terminal report — the full, uncapped per-source `rows`
list is what gets written to `data/COVERAGE.json` via `silence.write_json` (coverage.py:185),
which is the file every other module (dashboard, `phase_write`'s settled-fraction gate, `allsweep`)
actually reads. The two-tier evidence cache (`state_of`, coverage.py:82-115) is mtime-keyed and
persisted; the only quirk is cosmetic: when both `READ_CACHE` and `F.CACHE` independently report
`READ` for the same entry, `best` is overwritten by whichever base is checked second rather than
keeping the larger page count — this only affects a diagnostic `n_pages` number, never the
CITED/READ/NO PAGE state itself or the coverage fraction, so I'm not escalating it.

---

## src/resonance.py

### 4. [MEDIUM] [REPRODUCED] `resonance_strength()`'s default `graph_path` reads the *old*,
raw-count graph that `weave.py`'s own docstring says produces spurious cross-franchise links — not
the IDF-corrected graph the real pipeline actually computes. The comment claiming otherwise, in a
sibling file, is false as of current code.

**Where:** resonance.py:133-149, specifically the default:
```python
path = graph_path or os.path.join(HERE, "data/SHARED_STAGE_GRAPH.json")
```

**What `weave.py` says about that exact file (weave.py:30-35):** "The existing SHARED_STAGE_GRAPH
counted shared names raw, which is why it linked Greek and Roman myth through 'Tartarus
(LV-797)' — a Weyland-Yutani planetary designation — and tied two D&D supplements together through
'Dexterity' and 'Channel Divinity'. Raw counts treat a stat name and a protagonist as equal
evidence." `weave.py` was written specifically to replace this with an IDF-weighted graph, and
writes its corrected output to a **different** filename, `data/SHARED_STAGE_GRAPH_IDF.json`
(weave.py:82), with a comment at the write site (weave.py:478) asserting "resonance.py reads it."

**What's actually on disk right now — three different files, three different sizes, none of them
kept in sync:**
```
SHARED_STAGE_GRAPH.json       250,917 bytes   2026-08-20 13:26   (raw counts; what resonance.py
                                                                    actually defaults to reading)
SHARED_STAGE_GRAPH_IDF.json    55,154 bytes   2026-08-20 15:48   (weave.py's IDF-corrected output;
                                                                    the comment's claimed target —
                                                                    resonance.py never reads this
                                                                    filename)
RESONANCE_GRAPH.json           55,102 bytes   2026-08-22 01:08   (pipeline.py's phase_weave, the
                                                                    ACTUAL pipeline-integrated
                                                                    output — also never read by
                                                                    resonance.py's default)
```

**Reproduced divergence:** loaded all three and diffed the pair sets. The old raw graph
(`SHARED_STAGE_GRAPH.json`, resonance.py's actual default) has 1,087 pairs; the real pipeline
output (`RESONANCE_GRAPH.json`) has 205; 883 pairs exist ONLY in the stale/flawed graph. Calling
the real `resonance.resonance_strength()` function on three of those 883 pairs:

```
pair: Gundam (all centuries, incl. G Gundam) / major fantasy pantheons
  DEFAULT (reads old raw SHARED_STAGE_GRAPH.json): {'weight': 1.079, 'shared': ['Mars (Martian
      society)', 'The Titans', 'Artemis (Outfit)'], 'in_resonance': True}
  against RESONANCE_GRAPH.json (what phase_weave actually produces): {'weight': 0.0, 'shared': [],
      'in_resonance': False, ...}

pair: Alien / all Modern Warfare
  DEFAULT: {'weight': 1.928, 'shared': ['Royce', 'New York City', 'Russia', 'Paris'],
      'in_resonance': True}
  against RESONANCE_GRAPH.json: {'weight': 0.0, 'shared': [], 'in_resonance': False, ...}

pair: Soul Calibur / Pantheon: Greek
  DEFAULT: {'weight': 3.025, 'shared': ['Athens', 'Elysium', 'Ares', 'Kratos', 'Hephaestus'],
      'in_resonance': True}
  against RESONANCE_GRAPH.json: {'weight': 0.0, 'shared': [], 'in_resonance': False, ...}
```

These are exactly the kind of false-positive, raw-name-sharing artifact `weave.py`'s docstring
describes the IDF correction as existing to eliminate — a modern shooter linked to Alien through
city names, a fighting game linked to Greek myth through generic character/place names Soul
Calibur happens to share with Kratos's setting.

**Current blast radius:** I grepped all of `src/` and found no call site for `resonance_strength()`
anywhere outside its own definition — it is presently unwired (consistent with several previous
sweep batches' notes on this same function). So today this is latent, not actively corrupting a
shipped output. But the comment in `weave.py` (line 478) asserting a real data dependency
("resonance.py reads it") is false against the current code, and the moment anything *does* call
`resonance_strength()` with its default argument, it will silently return confident-looking,
wrong, superseded relational data rather than an error — which is the shape of failure this
project treats as worst-case.

---

## Coverage recorded

```
cd C:/Users/imarl/panscriptum-library-kit && PYTHONIOENCODING=utf-8 C:/Users/imarl/miniconda3/python.exe -c "import sys; sys.path.insert(0,'src'); import sweep_plan; sweep_plan.record('run29', ['pipeline.py','anchors.py','coverage.py','resonance.py'], batch=2)"
```
