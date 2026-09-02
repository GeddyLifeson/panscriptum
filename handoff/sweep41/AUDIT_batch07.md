# Sweep 41 — Batch 07 audit

Auditor: sweep41-batch07. Scope per assignment: `src/feats.py` (1,900 lines), `src/corpus_db.py`
(795 lines), `src/threads.py` (630 lines), `src/autostart.py` (502 lines), `src/pick_model.py`
(403 lines), `src/deprecated/catalogue_local.py` (333 lines), `src/recover_folder_records.py`
(283 lines), `src/cachekey.py` (190 lines) — 5,036 lines total, all read in full, top to bottom.
Every candidate finding was checked against the actual current source (and, where relevant,
against live data files and other callers in `src/`) before filing. This is an AUDIT: no file
under `src/` was edited.

## What these files are

`feats.py` is the crawler that mines cited combat/scale evidence from wiki pages — the module
whose history (per my brief) is this project's founding-defect gallery: fetch failures reading as
honest absences, template-wrapped articles stripping to nothing, slug-guessed hosts serving the
wrong fiction. It turns out to be, by a wide margin, the most thoroughly self-audited file I read
this batch: nearly every one of the failure shapes I was told to hunt for is already fixed in
place, with a paragraph explaining the measured defect and the fix, and cross-referenced to a
work order number. `corpus_db.py` (the derived SQLite index) and `cachekey.py`/`threads.py` are
similarly dense with prior fixes. `autostart.py`, `pick_model.py`, `recover_folder_records.py`
are shorter and each carries a handful of well-documented prior repairs. `deprecated/
catalogue_local.py` is the quarantined local-model cataloguer.

## Findings filed

### 1. `b9584c782d95` — `feats-roll-silently-drops-hostless-sources` (MAJOR)

`feats.py --roll` builds its job list with `h = hosts.get(r["source"]); if not h: continue` — any
source absent from the host map is silently excluded from the roll's "universe" of jobs. Nothing
in `roll()`'s own accounting counts this. That is a real gap against a file whose entire other
personality is measuring and printing every other way an entity can go unmined: `_RATE_LIMITED`,
`_CAP_BOUND`, `_STALE_GATE`, `_UNCACHED`, the length-filter drops, the refused-page tally — all
printed in the run summary under the file's own stated rule ("a measurement nobody prints is not
a measurement"). A source with no host is the one exclusion this meticulous accounting never
names, and it is structurally the same shape as the file's own founding defect
(`resolve_hosts`'s docstring: "roll() dropped every entity of that source from the universe").

`--roll` calls `resolve_hosts(recs, verify=False)`, and with `verify=False` any source with no
cached host, no override, and no corpus-derived host is simply left out of the returned map — no
probing, no guessing, no record of the omission. `main()`'s `--roll` branch never prints how many
records or entities that left behind, and `roll()`'s opening line prints only `len(jobs)` — the
post-exclusion count — with nothing to compare it against.

Measured against the live `data/WIKI_HOSTS.json` (207 keys) vs `data/SWEEP_ROLL.json` (215
sources): **9 sources have no entry at all** in the host map ('Curious DM Investigations (the
Sharkin)', 'Genuine Fantasy Press (Forgotten Secrets)', 'HAWX', "Heaven's Lost Property", 'Super
Energy Apocalypse 1 & 2', 'The Elements Beyond', 'Twilight Imperium', 'major live-action Disney
films', 'the Witch Tradition'). Four of those carry real catalogued entries per
`SWEEP_ROLL.json`'s `entry_count` — Curious DM 12, The Elements Beyond 681, Genuine Fantasy Press
25, Super Energy Apocalypse 9, **727 entities total** — every one of which is invisibly excluded
from `feats.py --roll` today (which per my brief is the live crawler, currently running), and an
operator watching its stdout has no way to learn that from the tool itself.

(A separate, narrower slice of this — sources holding an explicit `null` in `WIKI_HOSTS.json` —
is already re-probed automatically on the next `--hosts` run and is not part of this finding.
This finding is specifically about sources absent from the map entirely, which `verify=False`
never asks about at all, and about `roll()`'s silence on the exclusion regardless of cause.)

### 2. `88a5f9192e1b` — `cachekey-owns-ignores-host-dimension` (MAJOR)

This is the "cache key that ignores a dimension" pattern my brief named directly.
`cachekey.owns(doc, name)` — the one gate every read/write site in this module, and every one of
its callers (`feats.py`, `coverage.py`, `pipeline.py`, `read.py`, `hostcheck.py`, `sweep.py`,
`prose_gate.py`), trusts before believing a cache hit — checks `doc.get("entity") == name` and
**nothing else**. It never checks `doc.get("host")` against the `host` it was asked for, even
though the record already carries `host` (`feats.evidence_for()` stores `"host": host` alongside
`"entity": name` in every record it writes) and the entire reason this module exists (per its own
docstring, order M23) is that a lossy sanitiser plus a length cap folds two different identities
onto one file.

`host_dir(host)` applies the identical lossy transform that produced the module's founding bug
for names: `_SANITISE.sub("_", host or "")[:HOST_CAP]`, `HOST_CAP=40` — the same shape as
`name_stem`'s `[:NAME_CAP]`, `NAME_CAP=80`, which this module's own docstring says folded "Magic 8
Ball" and "Magic 8-Ball" onto one file and handed a reader the wrong entity's mined feats. If two
different host strings ever sanitise to the same `host_dir()` (a punctuation-only difference, or
agreement on the first 40 sanitised characters) and an entity of the same name exists under both
hosts, `cachekey.load()` for host A can silently return host B's cache file — `owns()` sees the
right `entity` and says yes. `write_path()` inherits the identical blind spot: it would treat host
B's write as already owning the natural path (the stored entity name matches) and hand back the
same path, so a later mining pass for host B could silently overwrite host A's evidence, with
neither side raising or logging anything.

Verified, not purely theoretical: no two hosts in the current `data/WIKI_HOSTS.json` collide on
`host_dir()` today (checked directly — 140 distinct hosts, 0 collisions) — but the 40-character
cap is already live and binding: `doc:arcanum-worlds-odyssey-of-the-dragonlords` sanitises to
**exactly 40 characters** (`doc_arcanum_worlds_odyssey_of_the_dragon`), i.e. it is already sitting
at the truncation boundary the same way the 59 `name_stem` entries at `NAME_CAP` were before the
read-time verification fix landed for names. The fix this module already applies to names
generalises directly: `owns()` should also compare `doc.get("host")`, and `write_path()`'s
disambiguation should trigger on a host mismatch the same way it already triggers on an
entity-name mismatch.

### 3. `2f8ebf12e5f2` — `autostart-status-roster-collapses-unknown-to-not-running` (INFO, QUESTION)

Filed as a question, not a confirmed defect — both readings are genuinely defensible.
`autostart.py`'s `--status` branch prints the supervisor's own liveness correctly as a tri-state
(`running` / `UNKNOWN (could not read the process table)` / `NOT running`, lines 477-480), but
three lines later the per-job roster loop over `ON.ALL_JOBS` collapses `overnight.running(job)`'s
tri-state result (True/False/None) into a plain boolean (`'running' if ON.running(job) else 'not
running'`, lines 492-495) — a job whose liveness could not be determined prints identically to one
that is confirmed down. `overnight.running()`'s own docstring explicitly blesses this for
"read-only callers that only ever ask `if running(x)`," so it may well be intentional policy.
Against that: this file's entire second half is built around "an inability to observe is not an
observation," and this specific line sits three lines under a status line for the supervisor that
*does* preserve the distinction, in the same command's output. Filed to OWNER for a ruling either
way.

## Considered and NOT filed

- **`feats-roll-rc-always-zero` (order `33000660ddac`, still open)** — the code I read (lines
  1842-1876) already implements the fix this order describes, explicitly cross-referenced to
  "order f4f4b9d5f935, run40 sweep." The order appears to be a stale duplicate left open after a
  newer order was actually acted on; not something I can close (workorders.py is not in my batch
  and I did not touch it), but flagged here rather than silently ignored.
- **`deprecated/catalogue_local.py`'s quarantine** — verified directly by running it twice
  (`--dry-run` and `--help`, both read-only, both exit before any file I/O per the guard's
  placement above every other statement in the module): `--dry-run` prints the refusal and exits
  1; `--help` prints the refusal and exits 0 (the documented `allsweep.check_import` exemption).
  Quarantine holds. Not lifted, per instructions.
- **`corpus_db.py --sql` with a bad query or a missing database** crashes with an unhandled
  `sqlite3.OperationalError` traceback rather than a clean message (verified: ran `--sql "SELECT *
  FROM nonexistent_table"` against the live index). This fails *loud*, not silent — full
  diagnostic traceback, nonzero exit — which is the direction this codebase's doctrine actually
  cares about, so I judged it too low-confidence/low-severity to be worth an order on its own and
  did not file it.
- **`pick_model.py`'s `resident()`/`fit_note()` two-VRAM-budget inconsistency** — I found this
  independently (residency gate uses TOTAL VRAM minus reserve; the per-model display note uses
  CURRENTLY FREE VRAM, so a model the summary calls "resident and usable" can print "WILL OFFLOAD"
  next to it) and it is exactly the shape of thing my brief asked me to hunt for — but it is
  already filed, in detail, as `2f38b3e5258d` (`PICK_MODEL_RESIDENT_AND_FIT_NOTE_USE_DIFFERENT_
  VRAM_BUDGETS`) plus two related duplicates (`e038ec1759a9`, `ae7b56cd43d0`). Not re-filed.
- **`corpus_db.py`, `threads.py`, `recover_folder_records.py` generally** — read in full and cross-
  checked against several specific candidate defects (`worst_cited`'s NULL-sorting on `pct`,
  `category_path`'s subroom/topic fallback ordering, `recover_folder_records`'s dry-run/write
  gating, its `EXCLUDED_REGISTER_SOURCES` handling); none held up as a genuine, unfiled defect.
  `recover_folder_records.py`'s two candidates I did independently spot — the unmarked
  `name[:48]` display truncation in its written-records report, and the unused `_declared_count`
  from `FOLDER_SOURCE_MAP.json` — are already filed as `b1612dc92424` and `729c26e0e63c`
  respectively. Its known-open `RECORDS_WRITTEN_OUTSIDE_THE_RECORD_WRITER` (`9a44b1535851`) is the
  order named in my brief and was not re-filed.

## Coverage

Recorded via `sweep_plan.record('run41', ['feats.py', 'corpus_db.py', 'threads.py',
'autostart.py', 'pick_model.py', 'deprecated/catalogue_local.py', 'recover_folder_records.py',
'cachekey.py'], batch=7)`.
