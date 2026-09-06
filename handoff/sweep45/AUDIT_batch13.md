# sweep45 — batch 13

Read-and-report only. No source file was edited. The DRILL_BREACH halt was left standing and no
battery tool (`drill.py`, `verify_math.py`, `allsweep.py`, `publish.py`, `mutate.py`) was run.

## Coverage

Every line of every assigned module was read, start to finish. No sampling.

| module | lines | read |
|---|---:|---|
| `src/read.py` | 1476 | all |
| `src/health.py` | 1065 | all |
| `src/ledger_guard.py` | 792 | all |
| `src/onomast.py` | 640 | all |
| `src/reference.py` | 485 | all |
| `src/prose_gate.py` | 402 | all |
| `src/tells.py` | 280 | all |
| `src/cosmology_graph.py` | 260 | all |
| **total** | **5,400** | **all** |

Recorded via `sweep_plan.record('sweep45', [...], batch=13)`.

Two read-only live checks were run (neither writes, neither is a battery tool):

* `python src/tells.py --check` → `IN SYNC ... (2680 chars)`, rc 0. The one-file claim is
  currently in force; `standards.py:979` is its production caller and it distinguishes
  `None` (unreadable) from `False` (drifted).
* `python src/ledger_guard.py` → all three mechanisms green, rc 0, 1,419 links verify, three
  acknowledged shrinks carried and printed (order `be33a61be79f`), `SINCE LAST SEAL` ok for both
  append-only ledgers. `main()` deliberately does not seal, so this changed no state.

## Filed this batch (worst first)

### `cdf0d2367cba` — READ_RUN_WORKER_INDEXES_A_DRIFTING_RECORD_SCHEMA (LOCAL, MINOR)

`src/read.py` `run().work()`. The aggregation block subscripts four keys of `out` directly
(`out["feats"]`, `out["fabricated_dropped"]`, `out["chunks_read"]`, `out["chunks_skipped"]`)
while the line immediately above uses `out.get("chunks_unanswered", 0)`. Those subscripts are
inside `with lock:` and **outside** the `try/except` that wraps `read_entity`, and `out` is very
often a document `read_entity` returned straight out of the cache — written by an older version
of this module and never rewritten.

**Measured on the live cache this shift: of 2,341 documents under `data/readfeats`, 28 carry no
`chunks_reused` key.** They predate that field and are served back unchanged. `chunks_reused` is
not one of the four subscripted keys, so nothing breaks today — but those 28 records are the
proof that a document outliving a schema addition is the normal state of this cache, not an edge
case. A `KeyError` there escapes `work()`, is re-raised at `list(ex.map(work, todo))`, and kills
`run()` *after* every entity in the pass has been read and paid for: the closing
`done in %.2fh …` line and the `err_note` never print, so a completed pass reports as a crash.

Latent, not live. Filed as MINOR for that reason.

### `f366f81f6ddc` — PREFLIGHT_API_PROBE_HAS_NO_RETRY_AND_NO_OUTCOME_CHANNEL (LOCAL, MINOR)

`src/health.py` `check_api_paths()` probes with `F.api(host, {...}, retries=0)` against
`feats.api`'s own default of `retries=2`, and does not pass the `outcome` dict. Two effects:

1. One dropped packet — DNS, TLS, a closed connection — makes the probe return `None`, which
   becomes a preflight problem, is stamped into `state/preflight_last.json`, and is turned into
   a filed work order by `workorders.sweep_detectors`. This machine has documented TLS
   interception that breaks HTTPS from Python intermittently, so this is a live exposure.
2. `"fandom API unreachable"` is emitted identically for a transient network fault and for the
   wrong-API-path 404 that is this check's entire stated purpose (the fault that cost 5,590
   entries). `api()` already separates those — `http-404`, `no-api`, `throttled`, `nonjson`,
   `network`, `unknown` — and its docstring says that channel exists precisely because
   collapsing them "is NOT tolerable for a liveness probe". This *is* a liveness probe and it is
   the caller that discards the distinction.

Both remedies are additive and neither weakens the check.

### `b1623ff4a677` — LEDGER_GUARD_CLI_VERDICT_COUNTS_CHECKS_BUT_NAMES_MECHANISMS (LOCAL, MINOR)

`src/ledger_guard.py` `main()` closes with `"ledgers: %d of the three mechanisms reported a
fault"`, but `failures` increments once for `check_all()`, once for `verify_chain()`, and **once
per name in `APPEND_ONLY`** — two names since 2026-08-31 (order `42db308cc85d`). The ceiling is
therefore 4 against the literal word "three", and below the ceiling it over-states breadth:
`check_all` plus both seal checks prints "3 of the three" while the hash chain in fact verified.

This is the readout, not a gate — `assert_intact()` raises per mechanism and does not use the
counter. It matters because `main()`'s own docstring is about exactly this hazard: "three
verdicts collapsed into one sentence cannot be audited against the code."

## Corroborated — already open, not refiled

* `ef26ed6029e7` (LOCAL) — `read.py --run --limit N` slices the ranked queue with no marker.
  Confirmed still present at `run()`.
* `aefd1a2c9343` — `read.py` `category[:20]` in `queue()`'s row build. Confirmed; the value is
  in-memory only and reaches no file, which is why it is survivable.
* `d9fbd60efd0f` — `size = CLOUD_CHUNK if _CASCADE_OK else CHUNK` reads a module global that may
  still be `None` on the `--one` path. Currently harmless because `CLOUD_CHUNK == CHUNK`.
* `05294ca33e1f` — `run()`'s closing line omits `done["unanswered"]`. Confirmed.
* `fc08e056e1ab` — `read_entity` and `_queue_row` disagree about "own page" (`_norm_q` vs a
  plain `.strip().lower()`). Confirmed at both sites.
* `ae25c89f0179` / `5d8533bc1ed6` — `onomast.register_for`'s genre+feature vote is unreachable:
  the only production caller is `name_worlds` at one positional argument, so
  `FEATURE_SHIFT` / `GENRE_WEIGHT` / `FEATURE_WEIGHT` never run. Verified by a repo-wide search;
  `navtree.py:164`'s `register_for` is a different, local function. Left for OWNER as recorded.
* `845dbaec182f` — `onomast.coin_well_formed`'s exhausted path still recomputes the
  byte-identical `f"{base}|fallback"` name it already rejected. The 2026-08-25 change added an
  inspection and a stderr report around it; the redundant recomputation itself stands.
* `e296ea51a1d9` — `health.check_caches`'s `if len(files) < 25: continue`.
* `5bbbb65e7787` — the self-test ledger split. See the note below on its current state.
* `27f823fd6ed5` — `MAX_LOST_FRACTION` is a judgement, not a measurement.
* `47c8def059e3` — `cosmology_graph.main()`'s console slices. All four now carry markers in the
  code; the open order is the OWNER question of whether a console summary may cut at all.
* `6e6954f261e0`, `b1f561587b19`, `cefcad5fc513` — the three open `prose_gate` OWNER questions.
  Note `b1f561587b19`'s described defect (extra entries priced into `missing` but not into
  `required`) **is repaired in the code** — `section_shortfall` now charges
  `extra * (len(REQUIRED_PER_ENTRY) + 1)` into `required`, with the 2026-08-28 note explaining
  it. The order text describes the pre-fix state; it should be closed rather than worked.
* `382d3a1c387c` / `692f693c3900` — `tells.py`'s "rule of three" regex requires a trailing
  `alike|all|together`. Confirmed; both are already-open style questions.

## Examined and deliberately not filed

* **`prose_gate.py` — nothing proposed, nothing weakened.** The five layers are wired and
  enforced: `generate.py:414` raises through `assert_block_complete`, `:424-437` refuses on
  `unearned_instrument`, `:468` calls `assert_gate_open` before the manifest is loaded, `:530`
  gates on `floor_ok`. `gate_open` and `step4_gate_open` both re-read config fresh, both use
  strict `is not True`, both refuse an unreadable or non-mapping config. `cited_names_for` fails
  closed to `set()`, which makes every axis score unearned and refuses the block. `overnight.py`
  no longer carries its own predicate — it delegates to `prose_gate.gate_open(cfg)`.
* `_AXIS_RE` anchors on `^[\s*_#>-]*` and so would not see an axis score rendered inside a
  markdown **table** row (`| Wisdom | 28 |` has no colon at all; `| Wisdom: 28 |` opens with a
  character outside the class). The entry template in `prompts/system_style.txt` asks for
  line-oriented `Strength: 30 (Transcendent, Grade III)` and never asks for a table, so there is
  no evidence the shape occurs. Recorded here rather than filed, per the standing instruction
  that defects in this module need strong evidence. Any future change here would be a
  *widening* of what the guard catches, never a relaxation.
* **`health.py`'s new `SELFTEST_SUBJECT` / `is_selftest(key, subject=)` — audited, no defect
  found.** The `subject=` door is wired: `escalation.py:267` passes `subject=rec.get("source")`,
  which is the seventh row (`escalation:SUPERVISOR:DRILL_AREA:…`, marker in `source` only) that
  no reading of the key could catch. `record()` routes under `_LOCK`; `_flush()` carries
  `_SELFTEST` through the *same* `_flush_ledger` with the same compare-and-swap,
  preserve-the-wreck and never-settle-on-refusal rules; `main(--failures)` prints both the
  routed rows and the pre-routing rows still mixed into `failures.json`, each under its own
  heading, ranked and whole. The only routing a real fault could take into the self-test ledger
  is one whose `source` or composed key carries `__drill…__`, and `drill.py`'s genuine failures
  do not escalate under a synthetic source — only its `DRILL_AREA` rehearsal at `drill.py:2094`
  does. One stale sentence: health.py's comment says `subject=` "is the half proposed to
  `escalation.py:248`", which reads as an open proposal when it is done. Comment-only, and this
  codebase records history in comments, so it is noted rather than filed.
* `ledger_guard`'s acknowledgement window is positional (`links[i-1]`, `links[i]`), so a dropped
  chain line before the acknowledged range would shift indices and could misdirect the waiver.
  It cannot stand alone: dropping an interior line breaks the following link's `prev`, which
  `verify_chain` reports and `assert_intact` fails closed on, and a dropped *final* line shifts
  nothing. Not a fail-open.
* `check_since_snapshot` returns `True` when the snapshot is missing or empty
  (`old.strip()` falsy → "history preserved"). Deleting the snapshot does not open the gate:
  `verify_chain`'s SHRANK test reads the sealed sizes out of the chain, and `check_all`'s byte
  floor runs first in `assert_intact`. `_read_snapshot` catches only `FileNotFoundError`, so a
  permission fault propagates and stops the publish.
* `read.py` — the transport ladder, the `_card_gate` re-entrancy guard, `_chunk_key`'s
  entity-bearing key, the `if unanswered: return out` deferral, `priority()`'s three buckets
  (`woven + no_page + thin` is a complete partition of `rows`), and `queue()`'s four-attempt
  fail-closed host-map load were each checked against the failure they document. All hold.
* `health._flush_ledger`'s "unreadable **and** unpreservable" branch returns after a stderr
  message without a `silence.note`. Recording there would be futile — the note lands in the very
  in-memory ledger whose only outlet is the file that cannot be written — so this is correct as
  written.
* `cosmology_graph` — `--write` emits every pair uncapped, `pairs_filtered: False`,
  `threshold_applies_to: "clusters"`, the landed verdict gates both the message and the exit
  code, and `_cut` marks every string cut. `#components <= #edges` always, so `--show`'s shared
  `shown` cannot silently hide clusters.
* `reference.py` — `shelfmark()` notes its NAVTREE failure by content label, the RUNGS clamp
  notes its own shape refusal, and `main()`'s exit code carries both `landed` and `calibrated`.
