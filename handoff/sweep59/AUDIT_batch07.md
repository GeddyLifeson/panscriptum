# Sweep 59 -- AUDIT batch 07

Modules read in full:

| module | lines | read (top to bottom? mtime) |
|---|---|---|
| src/standards.py | 2477 | yes, full (2026-09-14 00:23) |
| src/overwatch.py | 1124 | yes, full (2026-09-13 23:51) |
| src/identity.py | 752 | yes, full (2026-09-08 16:30) |
| src/feats_index.py | 628 | yes, full (2026-09-14 00:24) |
| src/reference.py | 497 | yes, full (2026-09-07 23:19) |
| src/recover_folder_records.py | 380 | yes, full (2026-09-14 00:04) |
| src/profile.py | 332 | yes, full (2026-09-14 22:14) |
| src/ledger.py | 220 | yes, full (2026-09-08 16:27) |
| src/repass_bands.py | 214 | yes, full (2026-09-11 22:35) |

Order of work: pulled `state/workorders.json` first and read the full text of every order whose
`where` names a module in this batch (three: `1e6f99e54b25`, `7099a092abd3`, `d9328fe1ee38`).
All three re-verified against current source below rather than re-filed.

## General

All nine modules in this batch are heavily hardened already -- every one carries dozens of
in-file comments recording prior sweeps' fixes, with quoted before/after behaviour and order
IDs. No new DEFECT was found that survives verification against current source. Two items are
recorded as QUESTIONs and three known orders are re-verified as still accurate.

### New findings

No DEFECT filed this batch. (See QUESTIONS below for two items considered and not filed as
defects, and Known for the three pre-existing orders re-verified.)

**QUESTION -- should a never-yet-started managed job read UNMEASURABLE rather than count
against "every running job is advancing"?**
where: src/standards.py, `check()`'s job-advance block, lines 1702-1718 (mtime 00:23)
The loop iterates `LN.OWNER` (six core managed jobs: read, roll, pipeline, recatalogue, sweep,
calibrate) and does `size = os.path.getsize(path)` before ever asking whether the job's owning
process is alive. If a job's log genuinely does not exist yet (first run never happened), the
`except Exception` branch fires and the job is appended to `unmeasurable`, which makes `holds =
not stalled and not unmeasurable` false -- a MISS is reported even though nothing is wrong: the
job simply hasn't run yet. Reading 1706-1718, the "is it alive" check (`_ON.running(owner)`)
only happens *after* a successful stat, so a job that is legitimately down-and-never-run cannot
reach the `if not alive: continue` exemption that a job which HAS run once and then stopped
gets. Two readings: (a) this is a real gap -- an `alive` check should gate the stat, and only a
job that is alive yet unstatable should count as unmeasurable; (b) this is deliberate, per the
block's own comment two lines above ("a job that cannot be measured is the one most likely to be
in trouble" -- i.e. treat "never produced a log at all" as itself suspicious for one of the six
core supervisor jobs, which are expected to have run at least once in any mature installation).
Not filed as a DEFECT because I could not produce a live state where this actually fires
(all six `LN.OWNER` logs exist on a running installation), so I cannot show the concrete
wrong-result state Method step 4 requires -- flagging as a question for a ruling on intent
instead of guessing.

**QUESTION -- `profile.encode()`'s feature-index lookup has no failure path**
where: src/profile.py `encode()` line 133 (mtime 22:14)
`f = "".join(B32[[n for n, _ in tbl].index(features[axis])] for axis, tbl in AXES)` raises a
bare uncaught `ValueError` if `features[axis]` is a value that is not one of the `n`s in `tbl`
(from `worldseed.LANDFORM`/`CLIMATE`/`CONDITION`/`TECH`). Every other failure path in this same
function (band parsing, band range) is caught and degraded via `silence.note` + a safe fallback;
this one is not. Two readings: (a) real gap -- a stray feature value from a `WS.build_all()` w
dict whose `features` doesn't validate against `AXES`'s tables would crash `build_all()` for
every world after it rather than degrading one row; (b) deliberately not guarded because
`worldseed.build_all()` is the only realistic producer of `features` and it is constructed
directly from the same `AXES`/`LANDFORM`/etc. tables, making the mismatch structurally
impossible today -- an invariant violation worth crashing loudly on rather than silently
degrading. Not filed as a DEFECT: I could not find a live caller that supplies a `features` dict
from an independent source, so I have no concrete input that reaches the crash.

### Known (already open orders)

- **`d9328fe1ee38`** (STALL_STANDARD_WATCHES_THE_LOG_NOT_THE_WORK) -- **still accurate.**
  Re-read `standards.py`'s "jobs that are ADVANCING" block in full (header comment at line 1674,
  code through line 1792 in the current file -- the order's own line citation of 1595-1640 has
  drifted, which per the sweep brief §5 is already covered by the standing line-drift orders and
  is not re-filed separately). The witness is still exactly one thing: `os.path.getsize(path)`
  on the job's own log file, compared via `job_stamp()`. No second witness against the job's
  actual output tree (`data/feats` for `feats.py --roll`, etc.) has been added. The order's
  remedies (a)/(b)/(c) are all still unimplemented. Confirmed by direct read, not by trusting
  the order text.

- **`7099a092abd3`** (BATTERY_IS_THE_ONLY_CALLER_OF_THIRTEEN_PUBLIC_FUNCTIONS) -- **still
  accurate for the four `ledger.py` symbols it names.** Grepped the whole tree for
  `ledger.cross_rate`, `ledger.to_standards`, `ledger.from_standards`,
  `ledger.assay_to_standards` outside `ledger.py` itself: zero matches anywhere in `src/`.
  `ledger.py`'s own module docstring (lines 42-63) independently confirms this from the other
  side -- it says outright "it has no caller in the generation pipeline at all: the only import
  of it anywhere in the tree is that battery" and explains it is HELD by owner ruling
  (order `3fb9fc6b9999`) pending a Position Paragraph consumer, not an oversight. The two
  documents agree; nothing has changed.

- **`1e6f99e54b25`** (CORPUS_WRITERS_WITHOUT_A_HALT_INTERLOCK) -- **still accurate for
  `repass_bands.py --apply`.** Read the whole file: no `import escalation` and no call to
  `escalation.assert_clear()` anywhere in it. `--apply` still writes `data/records/*.json`
  (via `PL.write_record`) with no halt check. Confirmed by direct read.

### Checked and clean (notable things verified as correct)

- `ledger.assay_to_standards`'s M10 top-band handling (no rung above it to supply a ceiling):
  `hi = lo * (lo / prev)` correctly extends the same log-width as the M9->M10 gap, anchored at
  M10's own floor, matching the order-5082a529e937 fix described in the comment. Verified the
  arithmetic by hand: `log(hi) - log(lo) = log(lo) - log(prev)` as claimed.
- `profile.py`'s `_BAD_CHARS` self-read guard (inserted tonight, one of run #59's 24 modules) is
  placed correctly -- before `HERE`/`sys.path` setup and before any other import, using
  `os.path.abspath(__file__)` consistently, matching the pattern already used in the ~50 other
  modules that carry it (`standards.py`, `overwatch.py`, `identity.py`, `feats_index.py`,
  `reference.py` among this batch already had it from earlier sweeps). No ordering hazard found.
- `feats_index.feats_for_source`'s within-source name-collision handling ("first entry wins")
  is consistent with `feats_index.audit()`'s independent corpus-wide rescan of the same
  collision class (both keep the first-seen name and report the dropped one), and with the
  printed report line's own claim ("the first one wins").
- `overwatch._merge_ledgers` / `_progress` / `_finished_at`: re-verified the tie-break chain
  end to end. A non-dict `mine` entry always loses (`_progress` returns `(-1, 0.0, 0)`), a tie
  in progress rank correctly falls back to disk's copy (`merged` starts as `dict(df)` and is
  only overwritten on a strict `>`), and `_finished_at` now compares `retired_at`
  ("YYYY-MM-DD HH:MM[:SS]") and `closed_at` (epoch float/str) on one numeric scale rather than
  as strings, closing the "RETIRED always beats CLOSED" bug the in-file comment (order
  `72e33d06d4eb`) describes as fixed. Confirmed the fix is actually in place, not just claimed.
- `recover_folder_records.py`'s three-way bucketing (`skipped_no_map` / `skipped_no_items` /
  `short_sources`) correctly routes an empty-list mapping (`FOLDER_SOURCE_MAP.json` entry `[]`)
  through `skipped_no_items` rather than `skipped_no_map`, per the `is None` (not falsiness)
  check at the top of the loop -- matches the order-37d3d588847a fix description.
- `reference.py`'s `--compare` path keys `ASSAYS.json` rows by `(host, entity)` pulled from the
  row's own fields first, falling back to a bare key-split only when a row carries neither --
  confirmed this actually finds rows (not silently landing in the "no row" branch for every
  entity, which the in-file comment says was the prior bug).
- `identity._is_continuity`'s branching/population majority rule for `n == 2` (`shared >=
  (n // 2) + 1` = `shared >= 2`, i.e. both bearers shared) is a genuine "more than half" rule as
  the comment claims, correctly distinguished from the `n == 1` case handled separately above it.

## Coverage

`sweep_plan.record('run59', [...9 basenames...], batch=7)` -- ran successfully, output
`record() done`, no exception.

QUESTIONS: 2
record(): ok
