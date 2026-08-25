# Sweep #28 — Batch 12 audit

Modules: `src/overnight.py` (766 lines), `src/zfighters.py` (485), `src/onomast.py` (407),
`src/cosmography.py` (282), `src/grounding.py` (245), `src/recover_folder_records.py` (180),
`src/resync_roll.py` (81). Total 2,446 lines, every line read.

`NEXT_STEPS.md` §3 was read first. Relevant KNOWN items for this batch: `zfighters.py:474`
(KeyError crash) and `resync_roll.py:65-68` ("Fixed" comment hiding an open RMW window) — both
explicitly named as this batch's special focus, both re-verified live below.

---

## src/resync_roll.py — SPECIAL FOCUS

### [HIGH, KNOWN — re-verified, STILL OPEN] `resync_roll.py:33-68` — the "Fixed 2026-08-25" comment only closed the write-tearing half; the read→scan→write clobber window is fully open

```python
33  with open(ROLL, encoding="utf-8") as f:
34      roll = json.load(f)
...
39  for fn in os.listdir(RECORDS):        # 217 record files, each opened and parsed
...
65  if changed and not dry:
66      # ATOMIC: this file's own docstring warned about the roll-clobber hazard while the
67      # code went on truncate-then-filling it. Fixed 2026-08-25.
68      silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)
```

`silence.write_json` (temp-file + `replace_retry`) makes the **write itself** atomic — no reader
sees a half-written file, no crash mid-write leaves a corrupt one. That is a real fix for torn
writes, but it is not the hazard the module's own docstring describes. The docstring (lines
6-11) names the actual hazard: **two writers of the roll running concurrently, one clobbering
the other's fresher counts with a stale copy read minutes earlier** — the exact Dr. Firestorm /
Elements Beyond incident it cites.

The window is precisely: `roll` is read into memory once, at line 33-34, *before* the entire
`data/records/` directory (217 files today, confirmed by listing) is opened and parsed one at a
time (lines 39-50). Only after that full scan completes does the process write back the in-memory
`roll` it read at the very start. Any other writer of `SWEEP_ROLL.json` — `catalogue_web.py`,
`catalogue_aurora.py`, `catalogue_codex.py`, `recover_folder_records.py` (all named in this
file's own docstring as concurrent writers) — that lands its own write to `ROLL` anywhere in that
window is silently discarded the moment this process reaches line 68: the write is atomic, but it
atomically writes **stale data**, which is a lost update, not a torn one.

**Concrete failure scenario:** `resync_roll.py` starts, reads `roll` at T0. At T1 (mid-scan),
`catalogue_aurora.py` finishes cataloguing a source and writes a fresh `SWEEP_ROLL.json` with
that source's real `entry_count`. At T2, `resync_roll.py` finishes its scan and writes back its
own T0-vintage `roll`, in which that source still carries whatever count it had at T0 — silently
reverting Aurora's update. This is exactly the bug the docstring's own worked example describes,
just with `resync_roll.py` itself now playing the clobbering role instead of the wiki run.

**Minimal correct fix:** don't blind-overwrite the T0 snapshot. Re-read `ROLL` immediately before
the final write and apply only the computed `(name, n)` deltas onto that fresh copy (or hold a
cross-process lock — e.g. a lockfile — across the entire read-modify-write, not just the final
`os.replace`). Re-reading right before the write does not close the race to zero, but it shrinks
the window from "the time to open and parse 217 files" to "the time to reserialize one JSON
list," which is the same mitigation pattern this project already uses in `silence.replace_retry`
for the write side.

### [MED, NEW] Same clobber shape lives in `recover_folder_records.py` too — see that section below; both are writers of the same file with the identical read-once/write-once-at-the-end structure `resync_roll.py`'s docstring exists to repair after the fact.

### [LOW, NEW, speculative] `resync_roll.py:39-50` — `by_source` dict silently overwrites on a duplicate normalized source name

```python
39  for fn in os.listdir(RECORDS):
...
50          by_source[norm(src)] = (rec, fn)
```

If two record files in `data/records/` ever declare the same `source` after `norm()`'s
alphanumeric-lowercase fold (e.g. a stale file left behind after a rename, alongside its
replacement), only the one `os.listdir()` happens to enumerate last survives in `by_source`, and
directory enumeration order is not sorted/deterministic. No duplicate exists in the tree today
(verified by direct scan of the current 217 files, 0 collisions), so this has not fired — flagging
as a latent, unexercised hazard rather than a live bug.

---

## src/zfighters.py — SPECIAL FOCUS

### [HIGH, KNOWN — reproduced live, STILL OPEN] `zfighters.py:474` — `--full` crashes `KeyError: 'provenance'` on Son Goku

```python
436  p = os.path.join(HERE, "data", "REFERENCE_ASSAYS_PRESENCE.json")
437  with open(p, encoding="utf-8") as f:
438      out["Son Goku"] = json.load(f)["Son Goku"]
...
471  for ax in A.WEIGHTS:
472      d = rec["axes"][ax]
473      print("   %-15s%5.1f  [%s] %s"
474            % (ax, d["score"], d["provenance"], d["cited"][:60]))
```

Reproduced live: `python src/zfighters.py --full` prints through Vegeta cleanly, then crashes on
the very first Son Goku axis line:

```
Traceback (most recent call last):
  File "...\zfighters.py", line 485, in <module>
    sys.exit(main())
  File "...\zfighters.py", line 474, in main
    % (ax, d["score"], d["provenance"], d["cited"][:60]))
KeyError: 'provenance'
```

Root cause confirmed at source: `data/REFERENCE_ASSAYS_PRESENCE.json`'s `Son Goku` axes are
built by a different module (the presence-thesis rebuild) and each axis dict there carries only
`{"score", "cited"}` — no `"provenance"` key, unlike every axis this file builds itself (which
always carries `score`/`cited`/`provenance`, see `compute()` line 417-418). The merged-in Goku
entry silently lacks a field the print loop assumes is universal. Because the crash happens
inside the `--full` print loop, it happens *before* the final `silence.write_json(OUT, ...)` at
line 478 — so `data/Z_FIGHTERS.json` is never corrupted by this crash, only `--full` output is
lost. **Minimal fix:** `d.get("provenance", "?")` (or backfill `provenance` onto the merged Goku
axes at merge time, e.g. `"presence-rebuild"`).

### [MED, KNOWN — reproduced live, STILL OPEN] `zfighters.py:24-29` — the docstring's headline claim is false against the module's own computed output

The docstring asserts "ANDROID 17 ANCHORS AT M7, above Vegeta and every Earth-raised fighter
except Goku." Running the module (non-`--full`, so no crash) and reading the printed ranking:

```
Vegito           𝔄 M7.63 ± 0.06   M7
Android 17       𝔄 M7.60 ± 0.06   M7
Gogeta           𝔄 M7.60 ± 0.06   M7
Vegeta           𝔄 M7.53 ± 0.06   M7
Son Goku         𝔄 M7.53 ± 0.06   M7
```

Vegito (7.63) and Gogeta (7.60, tied with 17) both outrank Android 17, and Android 17/Gogeta both
now outrank Son Goku (7.53) — directly contradicting "above ... every Earth-raised fighter except
Goku" (Goku is not above 17 here, he's below both 17 and Gogeta) as well as implying Android 17 is
second only to Goku, when three other fighters (Vegito, Gogeta tied, and effectively Vegeta tied
with Goku) sit at or above his score. This is a comment-vs-code mismatch on the module's own
central claim, matching the class of finding this run's rules flag specifically (comments that
contradict what the code, run today, actually produces).

---

## src/recover_folder_records.py

### [MED, NEW] `recover_folder_records.py:86-164` — same read-once/write-once-at-the-end roll-clobber shape as `resync_roll.py`, unfixed by the "ATOMIC" comment here either

```python
86  roll = load(ROLL)                       # read once, at the top
...
98  for name in empty:                      # loop writes N individual record files to disk
...
162 if not args.dry_run and written:
163     # ATOMIC: `resync_roll.py`'s docstring names THIS script as a roll-clobber source.
164     silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)
```

This script is explicitly named, in `resync_roll.py`'s own docstring, as one of the concurrent
writers whose collision `resync_roll.py` exists to repair after the fact. It has the identical
shape: `roll` is loaded once at the very start (line 86), then the script does real disk I/O for
every recovered source (writing a fresh record file per source via `silence.write_json` inside the
loop, which for a large batch is not instantaneous), and only at the very end does it write back
the *entire* in-memory `roll` list. Exactly as with `resync_roll.py`, the comment marks the final
`os.replace` as "ATOMIC" — true of the write itself, but it does nothing to prevent this process's
stale T0 snapshot from clobbering a concurrent writer's update to some *other* row of the same
roll made anywhere during this script's run. Same root cause, same minimal fix: re-read `ROLL`
immediately before the final write and merge only this run's own deltas onto it.

### [LOW, present but self-acknowledged in-code] `recover_folder_records.py:143-160` — records are written via raw `silence.write_json` to `data/records/`, not through `pipeline.write_record_catalogue`

```python
143  path = os.path.join(RECORDS, slug(name) + ".json")
144  if not args.dry_run:
145      # ATOMIC. NOTE FOR REVIEW: the two-writer contract says a RECORD should be written
146      # through `pipeline.write_record_catalogue`, not straight to disk at all. Making the
147      # write atomic is the safe half of that repair; routing this recovery tool through
148      # the catalogue writer changes its merge semantics and is flagged in NEXT_STEPS.
...
155      if not silence.write_json(path, record, indent=2, ensure_ascii=False):
```

This is a genuine two-writer-contract deviation (record files are supposed to land only via
`pipeline.write_record`/`write_record_catalogue`, per this run's own priority-4 lens), and the
comment says as much. However: **the comment's claim that this is "flagged in NEXT_STEPS" does
not hold today** — `NEXT_STEPS.md` §3 (read in full for this run) contains no entry for
`recover_folder_records.py`; the only trace of this exact issue is historical, in `HANDOFF.md`
(m131, which resolved the *write-denial-ignored* half of this file's problem, not the
which-writer-owns-this-file half). So the routing question this comment defers to "NEXT_STEPS"
has silently fallen off the tracked queue. Flagging as NEW on that basis — the underlying
technical deviation is long-standing and self-documented, but the tracking claim in the comment is
currently false and the item needs re-adding to the owner-ruling queue if it's still meant to be
one.

The write-denial gate itself (lines 155-157: refuse to update the roll row if the write returns
`False`) is correctly implemented and matches the fixed m131 pattern — confirmed **FIXED**, not a
finding.

---

## src/onomast.py

Read in full, 407 lines. No correctness bugs found in the name-generation logic itself
(`well_formed`, `coin_name`, `coin_well_formed`'s widening-fallback, `register_for`'s
weighted-vote tie-break) — all deterministic, all bounded, the fallback ladder documented and
functioning as described (verified by re-reading the exhaustion path at lines 260-265: 400 + 9,600
= 10,000 deterministic candidates before giving up, matching the comment). Uniqueness is enforced
via a single run-scoped `taken` set (line 350) shared across all continuities, so no output
collision is possible within one run. The shared `ONOMASTICON.json` write (line 399) correctly
uses `silence.write_json`.

### [LOW, NEW] `onomast.py:389-396` — the console summary caps to 4 endonyms and 9 example worlds each; the written data file is not affected

```python
389  for endo in sorted(by_endonym, key=lambda k: -len(by_endonym[k]))[:4]:
390      rows = by_endonym[endo]
391      print(f"\n  {endo} — {len(rows)} worlds, none of them each other:")
392      for v in rows[:9]:
```

`ONOMASTICON.json` (line 399) is written from the full, uncapped `named` dict, so no data is
lost. This is a print-only diagnostic cap on the human-readable run summary — low impact, but
per this run's lesson 16 ("a cap on a diagnostic hides the pattern, not just the rows"), an
operator glancing at the console output would never see the 5th-most-common carried name, or
worlds 10+ of any group, in a run with many worlds sharing a name.

---

## src/cosmography.py

Read in full, 282 lines. Pure derivation module (no I/O, no writes, no shared state). Checked
`kardashev_to_magnitude`'s band-selection loop (line 162-166) against `assay.LADDER`'s actual
ascending order (`M0..M10`, confirmed at `assay.py:105`) — correct, since the loop's
"keep updating `reached` while the threshold holds" logic depends on ascending iteration order,
which holds. Checked `validate()`'s four physical-ceiling guards and the `KARDASHEV_MIX` sum
check — all correct and exercised on every `census()` call (line 206), which is the intended
"refuse an impossible universe" contract described in the docstring; confirmed the constants sum
to exactly 1.0 (`0.90000 + 0.08500 + 0.01499 + 0.00001`). No caps, no swallowed exceptions, no
shared-file writes. No findings.

---

## src/grounding.py

Read in full, 245 lines.

### [LOW, NEW] `grounding.py:112-117,163` — `classify_text`'s default `top=3` caps `runners_up` to at most 2 entries even though up to 4 groundings could have a nonzero score

```python
112  def classify_text(text, top=3):
113      scores = collections.Counter()
114      for name, spec in GROUNDINGS.items():
115          for pat, wt in spec["cues"].items():
116              scores[name] += wt * len(re.findall(pat, text, re.I))
117      return scores.most_common(top)
...
162  ranked = classify_text(" ".join(parts))
...
185      "runners_up": ranked[1:],
```

`GROUNDINGS` has 5 keys (`ex_nihilo`, `emanation`, `eternal_cycle`, `demiurgic`, `immanent`); the
default `top=3` means `classify_text`'s `Counter.most_common(3)` discards the two lowest-scoring
grounding types from `ranked` before `classify_source` ever sees them, so `runners_up` (written
verbatim into `GROUNDINGS.json`, line 185/239) can show at most 2 competing accounts even when up
to 4 had a nonzero cue match. The winning `verdict` itself is unaffected (top-1 of `most_common`
is always the true maximum regardless of `top`), so this does not misclassify any source, but it
does under-report how contested a classification actually was in the on-disk record — the exact
transparency field `classify_source`'s own docstring (lines 120-141) argues for elsewhere in this
same file when explaining why `cap` on the entry list was refused entirely. Bounded impact (max 2
categories ever hidden, out of a fixed universe of 5), but the same Hard-Rule-0 reasoning this
file applies rigorously to its `cap` parameter is not applied to `top`.

### [LOW, NEW] `grounding.py:231-233` — console "contested cosmogonies" report truncates to 5 rows and each row's `runners_up` to 2

```python
231  for s, v in low[:5]:
232      ru = ", ".join(f"{g}:{n}" for g, n in v["runners_up"][:2])
```

Print-only; the full `low` list length is reported (`len(low)` on line 230) and the full `out`
dict is written uncapped to `GROUNDINGS.json` when `--write` is passed. Same low-impact shape as
the `onomast.py` finding above — flagged for completeness under lesson 16, not because data is
lost.

The `cap=None`-refusal pattern in `classify_source` (lines 120-147) was checked and is correctly
implemented and matches the fixed pattern used by `feats.discover`/`genre.classify_source` per
this file's own docstring — confirmed **not a finding**, this half is done right.

---

## src/overnight.py

Read in full, 766 lines. This module is unusually well self-documented about its own past bugs
(the `running()` self-exclusion fix, the `did[:5]` truncation removed from `foreman_report()`,
the append-not-truncate log fix, the `name_rc()` exit-code decoder, the preflight/coverage
"error-shaped-as-zero" fixes) — all of those were re-checked at source and are correctly
implemented as described. Two NEW findings, both the same shape as the `did[:5]` cap this file
already found and fixed once, elsewhere in itself:

### [MED, NEW] `overnight.py:313-335` — `watch_report()`'s open-findings list is capped to `top=6`, unlike the sibling cap this same file already removed

```python
313  def watch_report(top=6):
...
327  open_f = [v for v in (d.get("findings") or {}).values() if v.get("state") == "open"]
...
331  hi = [f for f in open_f if (f.get("severity") or "").lower() == "high"]
332  log(f"  overwatch: {len(open_f)} finding(s) open ({len(hi)} high) after "
333      f"{d.get('rounds', 0)} round(s):")
334  for f in sorted(open_f, key=lambda x: -(x.get("severity") == "high"))[:top]:
```

Compare to `foreman_report()` in the same file (lines 300-303), which explicitly documents
removing an identical `did[:5]` cap: *"the header announces a count and the list then delivered
fewer... Nothing downstream parses this, so the cap bought nothing and cost the sixth remedy its
only mention."* That exact reasoning applies unchanged here: if more than 6 findings are open (or
even more than 6 *high-severity* ones — the sort only guarantees high-severity findings sort
before others, it does not guarantee all of them fit in the first 6), `state/overnight.log` — the
file this project's own docstring says is where "somebody looks in the morning" — silently drops
the 7th-and-later high-severity finding from the one place meant to surface it without anyone
having to go open `OVERWATCH.json` by hand. `OVERWATCH.json` itself is untouched (this is a log
line only), so no data is lost, but the morning-read summary this function exists to provide is
capped exactly the way this file's own history says that pattern is a bug.

### [LOW, NEW] `overnight.py:338-357` — `ledger_report()`'s swallowed-failures ranking is capped to `top=8`

```python
338  def ledger_report(top=8):
...
354  rows = sorted(d.items(), key=lambda kv: -kv[1])[:top]
355  log(f"  swallowed failures: {sum(d.values()):,} recorded, top {len(rows)}:")
```

Same shape, lower severity because the function explicitly labels itself "top N" and prints the
true total (`sum(d.values())`) alongside it, and `state/failures.json` itself is untouched. Still
worth flagging alongside the `watch_report` finding above since it is the identical pattern in the
same file, one function away from the one that was already fixed.

### [LOW, NEW] `overnight.py:65-89` — `_proc_lines()`'s lazy lock initialization is not itself synchronized

```python
71  global _PROCS_LOCK
72  if _PROCS_LOCK is None:
73      import threading
74      _PROCS_LOCK = threading.Lock()
75  with _PROCS_LOCK:
```

Classic unsynchronized double-checked-locking gap: if two threads (this module runs a
`_keep()` and a `_keep_warm()` daemon thread alongside the main loop, all of which can reach this
function) call `_proc_lines()` for the very first time concurrently, both can observe
`_PROCS_LOCK is None` and each construct its own `Lock()` object, so the two calls proceed to the
"populate `_PROCS`" section without mutual exclusion for that one race window. Worst realistic
outcome under CPython's GIL is a redundant PowerShell/WMI spawn on first use, not data corruption
(`_PROCS` dict writes are individually atomic under the GIL) — flagged as a genuine but low-impact
race, not a data-loss bug.

`run()`/`start()`'s `_PROCS["at"] = 0.0` cache-invalidation writes (lines 188, 239) happen outside
`_PROCS_LOCK` entirely, from whichever thread calls `run`/`start` (main loop or the `_keep()`
daemon thread) — also unsynchronized against `_proc_lines()`'s locked section, same low-impact
class.

No two-writer-contract violations found in this file: `STATUS.md` (line 505-526) and
`state/overnight.log` (line 53-58) are each written by exactly one supervisor process (enforced
by the `running("overnight.py")` self-exclusion check at line 540), so the raw `open(p, "w")` /
`open(..., "a")` calls here are single-writer and do not carry the multi-process RMW hazard this
run's lens is primarily aimed at for `data/`-tier shared state.

---

## Summary of coverage

All 7 modules read in full, every line. `NEXT_STEPS.md` §3 checked against every finding before
filing; both explicitly-flagged special-focus items (`resync_roll.py:65-68`,
`zfighters.py:474`) were re-verified live and remain open, plus `zfighters.py:24-29`'s docstring
mismatch was independently re-confirmed against a fresh run's output. No style-only findings are
included above.
