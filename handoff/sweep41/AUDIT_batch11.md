# Sweep 41 — Batch 11 audit

Modules read IN FULL (lines read = lines total in each file, per `wc -l`):

| module | lines |
|---|---:|
| src/overnight.py | 1556 |
| src/rigor.py | 956 |
| src/build_terminal.py | 654 |
| src/ingest_doc.py | 542 |
| src/canon_backup.py | 418 |
| src/feats_index.py | 369 |
| src/resonance.py | 298 |
| src/audit.py | 226 |
| src/lognames.py | 52 |
| **total** | **5071** |

Also read in full for cross-checking (not part of the batch, not re-reported on): `src/prose_gate.py`
(402 lines, to check overnight.py's prose gate against it) and small excerpts of `src/pipeline.py`
(`BANDS`, `records()`) to verify two candidate findings in `src/audit.py` before filing.

No file in `src/` was edited. No standing job was started, stopped or restarted. `drill.py` was not
run.

## Directed checks from the brief

- **overnight.py's prose gate vs. prose_gate.py.** `overnight._prose_enabled()` (lines 48-79) now
  delegates entirely to `prose_gate.gate_open(cfg)[0]` — it does not reimplement the check. Compared
  line-for-line against `prose_gate.gate_open()` (prose_gate.py:68-87): same strict-identity test
  (`cfg.get("prose_enabled", False) is not True`), same fail-closed-on-unreadable-config behaviour,
  same "read fresh every call" contract. **No divergence found.** This is already the fixed state the
  module's own docstring describes (the `bool()` defect and the config.yaml-clobbering trial-write
  defect are both described in the docstring as past incidents, not present behaviour) — not a new
  finding, and per the brief I did not touch it or propose opening either gate.
- **`overnight.name_rc` and rc=17.** Confirmed at overnight.py:856-857: `rc == 17` is named explicitly
  as `"rc=17 (ON PURPOSE — source changed, restarting to run the current code)"`, placed before the
  generic "UNRECOGNISED exit code" fallback and before the Windows NTSTATUS table, so it can never be
  read as a crash. Already correct; not re-filed.
- **canon_backup.py snapshot naming/overwrite.** See finding 2 below — a real, but already
  self-documented, gap. Filed as a QUESTION per the brief's instruction on deliberate design, not as a
  bug.
- **audit.py / rigor.py caps that hide evidence.** Checked every `[:N]` slice in both files (see
  "Considered and NOT filed" below for the ones that are already-declared, Hard-Rule-0-compliant
  truncations per this project's own established convention). Found one real unmarked-truncation
  instance in audit.py — finding 1 below.
- **lognames.py name mismatches.** `READ`/`ROLL`/`PIPELINE` constants cross-checked against every
  place `overnight.py` spawns those three jobs (STANDING table and the `run()`/`start()` calls in the
  main cycle): the log filename, the `lognames.OWNER` command-line fragment, and the actual argv
  overnight.py passes all agree (`read.py --run`, `feats.py --roll`, `pipeline.py --run`). No
  mismatch found in this batch's modules. (`RECATALOGUE`, `SWEEP`, `CALIBRATE` are driven by
  foreman.py/other modules outside this batch and were not re-verified end-to-end.)

## Findings filed

### 1. `d7e6e8db9f53` — src/audit.py:93,121 — unmarked truncation in BACKSCAN's own evidence strings
**LOCAL / MINOR**

`audit_invariants()` appends two diagnostic strings to its `fails` dict with a bare, unmarked
60-character slice of unbounded text:

```python
fails["synthesis: band rests on evidence that is not a scale feat"].append(
    f"{src}: {ev[:60]!r}")                                          # line 93
...
fails["entry: band rests on a note that no longer passes the gate"].append(
    f"{src}/{nm}: {sn[:60]!r}")                                     # line 121
```

Neither `ev` (synthesis evidence text) nor `sn` (entry `scale_note`) is bounded before the slice, so
a reader of the printed report cannot tell a genuinely short note from one cut mid-sentence. This is
the exact shape `_field()` in the same file (line ~50) records having already found and fixed at two
other sites in this module ("description came out at `[:150]` and the feat at `[:110]`/`[:120]`, with
no marker of any kind") — these two slices were apparently missed by that pass. The neighbouring
slice at line 141 (`d[:40]`) is **not** a bug: `d` is already checked `< 15` chars two lines above, so
it never actually cuts anything — verified before filing and left alone.

Suggested remedy in the order: route through `_field()`'s wrap-not-slice discipline, or append an
explicit marker when the slice actually cuts something (this file already has the "and N more"
convention four lines below, for the list-level `v[:4]` cut, which is correctly declared and is
**not** part of this finding).

### 2. `61037867dc5d` — src/canon_backup.py:130-218 (`snapshot()`) — same-second stamp collision silently overwrites a prior verified snapshot
**OWNER / MINOR — filed as a QUESTION, not a bug**

`snapshot()`'s final archive name is `canon-<stamp>.zip` where `stamp = time.strftime("%Y%m%d-%H%M%S")`
— one-second resolution. Two `snapshot()` calls whose stamps collide (a hand-run
`python src/canon_backup.py --snapshot`, which bypasses the 12h age gate entirely, racing
`overnight.canon_backup_cycle()`'s own gated call) land at the identical `final` path, and
`silence.replace_retry(tmp, final)` is an ordinary overwrite — so the second process to land silently
replaces the first **verified** snapshot with no error and no log line. This is exactly the class the
sweep brief calls out ("a backup that silently overwrites a prior snapshot ... loses the thing it
exists to keep").

I filed this as a question rather than a bug because the module's own docstring (lines 208-212)
already names this precisely and calls it deliberately open: *"NOT FULLY CLOSED, and deliberately
left so: two snapshots starting in the same second share `stamp`, hence share `final` ... Closing
that means putting the pid into `stamp` itself, which changes the archive naming `prune()` and
`newest()` read, so it is a separate decision from this one."* The work order restates both readings
for the owner:

- **(A) Leave it** — the collision window is narrow, and because both racing calls verify their own
  zip against the *same* live tree moments apart, the two archives are near-certain to be
  byte-for-byte equivalent in practice, so the "loss" is of a redundant duplicate rather than of
  distinct data.
- **(B) Close it** — put pid (or pid+tid, matching the temp-file convention this same function
  already uses three lines above) into the final stamp, removing the one write in this module that is
  not held to its own "a backup that was never read is a belief, not a backup" standard.

## Considered and NOT filed

- **audit.py's `v[:4]` list truncation with "... and N more" (line 190-193).** Initially flagged as a
  candidate ("reports only the first N offenders of an invariant" — a pattern the brief explicitly
  asked me to look for), but verified against this project's own stated convention before filing:
  `prose_gate.assert_block_complete`'s docstring states outright that "Hard Rule 0 forbids
  ranking-then-truncating a list a person reads to act, and the honest 'and N more' is the remedy it
  names for a display shortening." audit.py's cut declares its own size and the remainder count with
  no marker missing, which matches that accepted pattern (also used by `rigor.mathematical_resonance`'s
  `load_bearing` display). Not filed — it is not the same defect as finding 1, which has no
  declaration at all.
- **canon_backup.py `verify()`, `prune()`, `members()`.** Re-read against the exact hazards named in
  the brief (silent overwrite, identical naming, caps hiding evidence). All three already carry
  explicit fixes with "order" citations for name-collision-adjacent and cap-adjacent defects
  (`members()` refuses on a partial canonical set rather than silently backing up a subset; `prune()`
  treats a half-removed pair as not-removed; every list in `verify()`'s output is uncapped). No new
  defect found beyond finding 2.
- **overnight.py `_manager_stopped`'s two-spellings list, `running()`/`_cmd_is_running`'s basename
  vs. `lognames.OWNER` fragment asymmetry.** Read closely because it looked at first like a name
  mismatch: the STANDING-set spawn guard in `run()`/`start()` checks `running(os.path.basename(args[0]))`
  (e.g. bare `"pipeline.py"`), which is coarser than `lognames.OWNER["pipeline_auto.log"]`
  (`"pipeline.py --run"`) used elsewhere (stall detector, foreman remedy). This is intentional, not a
  bug: the spawn guard's question is "is a copy of this *script* already running, for any reason"
  (resource-contention protection — deliberately wants to catch a hand-run `--status` or `--phase 6`
  too), while `lognames.OWNER`'s stricter fragment answers "is the process that writes *this specific
  log* alive" (used by the stall detector/foreman). Two different questions with two different,
  correctly-scoped fragments; the STANDING table's own comment (overnight.py:806-809) states this
  reasoning directly. Not filed.
- **rigor.py, resonance.py, feats_index.py, ingest_doc.py, build_terminal.py.** Read in full; no
  uncaught defects found beyond what their own docstrings already record as fixed. `resonance.py` in
  particular is explicitly dead code with zero production callers (documented at the top of the file,
  order f467f662be4b) — not re-flagged as a fresh finding since the module itself already says so
  loudly and an OPEN order already exists for wiring it into `anchors.py`.

## Findings by severity

- BLOCKING: 0
- MAJOR: 0
- MINOR: 2 (`d7e6e8db9f53`, `61037867dc5d`)
- INFO: 0

## Coverage

Recorded via `sweep_plan.record('run41', [overnight.py, rigor.py, build_terminal.py, ingest_doc.py,
canon_backup.py, feats_index.py, resonance.py, audit.py, lognames.py], batch=11)`, shard
`state/sweep_shards/run41.11.46492.json`. Note: an earlier call in this run wrote a malformed shard
(`run41.11.34276.json`) using `src/`-prefixed paths instead of the bare basenames `sweep_plan.record`'s
own docstring calls for ("`covered` is an iterable of basenames") — every other run40/run41 shard in
`state/sweep_shards/` uses bare basenames, so the prefixed one would have shown as nine extra,
never-before-seen modules in the aggregate coverage view. That shard was deleted and replaced with the
correctly-keyed one before this report was written.
