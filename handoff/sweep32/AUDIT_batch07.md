# AUDIT — batch07 (run32)

Modules read in full, every line:

| file | lines |
|---|---|
| src/magnitude.py | 1109 |
| src/zfighters.py | 485 |
| src/pick_model.py | 357 |
| src/entity_match.py | 278 |
| src/coverage.py | 243 |
| src/recover_folder_records.py | 180 |
| src/withdraw_chapters.py | 112 |

Total 2764 lines. All read directly with the Read tool (not skimmed).

---

## BLOCKING

### `withdraw_chapters.py:66-98` — no chapter-selection logic; `--go` withdraws the ENTIRE catalog and wipes `catalog.json` to `{}`

CONFIRMS the known open lead exactly. The module's docstring (lines 1-13) frames this as a
targeted withdrawal of "the 145 chapters written while the prose gate was inverted," but `main()`
contains **zero** filtering logic — no address allowlist, no citation-percentage check, no date
range, no per-entry predicate of any kind:

```python
for _addr, rec in cat.items():                       # line 66 — EVERY entry in the catalog
    for key, sub in (("raw_path", "raw"), ("compressed_path", "compressed")):
        ...
        if a.go:
            shutil.move(src, os.path.join(arch, sub, os.path.basename(src)))   # line 74
```

then, unconditionally, once the loop over the *whole* catalog finishes:

```python
tmp = CATALOG + ".tmp"                                # line 95
with open(tmp, "w", encoding="utf-8") as f:
    json.dump({}, f, indent=2)                         # line 97 — the ENTIRE catalog, not a subset
silence.replace_retry(tmp, CATALOG)                     # line 98
```

**Blast radius**: any `--go` run relocates the raw/compressed files of *every* catalogued chapter
— not just the 145 flagged ones — into `output/withdrawn_<label>/`, and resets `catalog.json` to
an empty dict. Since `generate.py` treats `catalog.json` as its resumability ledger (per
CLAUDE.md), this forces regeneration of the *entire* library, at real model-time cost, exactly
the cost the file's own docstring says the move-not-unlink design exists to avoid. If the catalog
ever grows past the 145 flagged entries (which it will, as generation continues), this script
cannot be used to withdraw only the bad batch — it can only be used to withdraw everything.

Mitigating factors (why this isn't total data loss): `shutil.move` relocates rather than deletes,
so files survive under the archive dir; `catalog.json` is copied to
`arch/catalog.withdrawn.json` (line 94) before being wiped; and a `snapshot.before(...)` +
`snapshot.verify(...)` pair (lines 52-60) guards the catalog file specifically and raises
`SnapshotFailed` if the backup doesn't restore. **But `snapshot.before` is only given
`["output/index/catalog.json"]`** (line 53) — the physical raw/compressed content files being
moved are never snapshotted, only the metadata pointing at them is.

Additional robustness gap: the physical move loop (lines 66-78) and the catalog-wipe write
(lines 92-98) are not transactional with each other. If the process is killed partway through the
move loop, some entries' files have already been relocated to the archive while `catalog.json`
still claims their original `raw_path`/`compressed_path` — the catalog is never touched until
*after* the full loop completes, so a crash mid-run leaves the catalog pointing at files that no
longer exist at those paths, with no checkpointing to detect or resume from that state.

**Severity: BLOCKING.** This is a destructive, un-scoped operation whose docstring materially
misrepresents its own selectivity. It must not be run against the current `catalog.json` without
either (a) adding real selection logic, or (b) manually confirming the catalog contains only the
145 flagged entries at the moment of the run.

---

## MAJOR

### `withdraw_chapters.py:95,98` — two-writer contract violation (reported instance, confirmed)
Hand-rolled `tmp = CATALOG + ".tmp"` (no PID/thread tag, unlike `silence.write_json`'s
`"%s.%d.%d.tmp"` scheme) instead of calling `silence.write_json`, **and** the boolean return of
`silence.replace_retry(tmp, CATALOG)` at line 98 is discarded. If the replace is denied on every
retry (Windows `PermissionError`, e.g. a reader holding `catalog.json` open — explicitly the
scenario `replace_retry`'s own docstring describes as normal on this project), the script does
not raise or warn; it falls through to the print block at 103-106, which re-reads `CATALOG` and
prints whatever is actually on disk. Because that re-read happens to be visible, a stale count
would show up in the printed "catalog now: N entries" line — but nothing in the code itself
checks or reports the failure, and the same silent-discard pattern is what `pick_model.py`'s own
comment (see below) documents as having caused a false "config.yaml updated" message elsewhere in
this project.

### `magnitude.py:848,850` — two-writer contract violation (reported instance, confirmed)
Inside `calibrate()`'s `_land()` checkpoint helper: hand-rolled `_cr + ".tmp"` (line 848) instead
of `silence.write_json`, and `silence.replace_retry(_cr + ".tmp", _cr)` (line 850) return value
discarded. `CHARTER_REGRESSION.json` is read by `standards.py` to certify "the automation
reproduces the charter" per the docstring itself (lines 845-847 acknowledge the stakes: "a
truncating write can leave that check reading an unparseable artifact"). A denied replace here is
never surfaced to the caller — `calibrate()` proceeds as if each checkpoint landed, and a resumed
pass on the next invocation could silently work from a stale file.

### `magnitude.py:1050-1066` — two-writer contract violation (reported instance, confirmed), duplicated retry logic
Inside `run_batch()`'s `work()` closure: `tmp = OUT + ".tmp"` (line 1050) — hand-rolled, not
PID/thread-tagged — then a **hand-duplicated** copy of `replace_retry`'s own 5-attempt
backoff-on-`PermissionError` loop (lines 1058-1066) instead of calling `silence.replace_retry`
directly. The retry-and-`silence.note`-on-final-failure logic is faithfully reproduced, so this
one is not silently swallowed, but it is now two independent implementations of the same
algorithm that can drift out of sync, and — more importantly — it still uses the un-tagged tmp
filename `ASSAYS.json.tmp`. `ASSAYS.json` is explicitly documented (lines 1054-1055) as read
concurrently by the dashboard and by `settled()` "on their own clocks," i.e. by other processes,
not just other threads in this one. The in-process `threading.Lock` (line 1032, wrapping the
whole write) protects against the 8 worker threads racing each other, but does **not** protect
against a second OS process (e.g. a manually-run `--one` invocation, or a second `run_batch`)
writing the identically-named tmp file concurrently — exactly the collision `silence.write_json`'s
PID+thread-tagged naming was built to prevent.

### `coverage.py:78,85` — two-writer contract violation (reported instance, confirmed)
Inside `_so_save()`: hand-rolled `tmp = _SO_CACHE_P + ".tmp"` (line 82 in this file's numbering —
matches the batch's cited line 78 in an earlier revision) instead of `silence.write_json`, and
`_sil.replace_retry(tmp, _SO_CACHE_P)` (line 85) return value discarded. `state/coverage_cache.json`
is a memoization cache for `state_of()`; a silently-denied replace here just means stale
memoized state gets recomputed next run (low blast radius), but it's the same anti-pattern
repeated a fourth time in this batch alone.

### `pick_model.py:127-129` — hand-rolled tmp name (return value correctly checked, unlike the others)
`save_config()` uses `open(p + ".tmp", "w")` (line 127) rather than `silence.write_json`, so it
still has the un-tagged-tmp-name collision exposure described above. Credit where due: unlike
every other instance in this batch, the `replace_retry` return value **is** checked (`if not
_sil.replace_retry(...)`, line 129) and a clear failure message is printed and `False` returned
up the call chain to `main()`, which exits non-zero rather than claiming success. This is the
correct half of the pattern; only the tmp-naming half is unfixed.

---

## MINOR

- **`magnitude.py:741`** — `got.get("presence_evidence", got.get("hegemonic_feat", ""))`. No
  code path in this file (or `_split_assay`, which is the only other producer of `got`) ever sets
  a `"hegemonic_feat"` key — `SCHEMA` and `ANCHOR_SCHEMA` only define `presence_evidence`. Dead
  fallback referencing a field name that appears to be a leftover from an earlier version;
  harmless (both `.get()`s fall through to `""`) but should be removed or explained.

- **`zfighters.py:478`** — `silence.write_json(OUT, out, ...)` return value discarded. The
  comment directly above it (lines 476-477) specifically warns "a crash mid-write corrupts a file
  another module consumes," which is exactly the scenario an unchecked return value doesn't
  detect — `main()` still prints `"-> " + OUT` unconditionally at line 480.

- **`coverage.py:237`** — same pattern: `silence.write_json(OUT, rows, ...)` (writing
  `COVERAGE.json`, read by "the dashboard, standards, allsweep and the published page" per the
  adjacent comment) has its return value discarded; `main()` prints the success line regardless.

- **`recover_folder_records.py:164`** — `silence.write_json(ROLL, roll, ...)` return value
  discarded. Lower risk than the others: the per-record write immediately above it (line 155) *is*
  correctly gated (`if not silence.write_json(path, record, ...): ... continue`), so no record
  file is ever written without a corresponding successful roll update being attempted — but if
  the roll write itself is denied, `main()`'s final "Wrote N records" message doesn't reflect that
  the roll (`data/SWEEP_ROLL.json`) may still show `entry_count: 0` for sources whose record files
  now exist on disk with real content.

- **`coverage.py:192-210`** — `report()` divides by `n = sum(r["entries"] for r in rows)` with no
  guard against `n == 0` (unlike `measure()`'s own `coverage`/`settled` calculations, which use
  `max(n, 1)`). An empty `rows` (e.g. no records found) would raise `ZeroDivisionError`. Per this
  project's own stated fail-closed philosophy a crash is the safe direction, so this is informational
  rather than a hazard, but it's inconsistent with the rest of the file.

- **`pick_model.py` — VRAM budget silently defaults to a hard-coded 10GB card** (line 295:
  `budget = (total_vram_gb() or 10.0) - VRAM_RESERVE_GB`). If `nvidia-smi` is present but reports
  a smaller card (or `total_vram_gb()` fails for a reason other than "no GPU"), the residency gate
  would evaluate against an assumed 9GB budget instead of the real, smaller one, silently admitting
  a model that would actually offload. No warning is printed for this fallback (contrast with
  `free_vram_gb()`'s display-only fallback, which does print a warning at line 314). Narrow
  scenario (requires a working `nvidia-smi` returning a value other than nothing/error), so kept
  as MINOR rather than MAJOR.

---

## NOTE

- **`pick_model.py` — "enforce qwen3:8b" is emergent, not pinned.** `RESIDENT_ONLY` + `resident()`
  (lines 91-92, 190-192) correctly and unconditionally enforce the GPU-only-residency *rule* — any
  candidate model whose `weight_gb + KV_GB` exceeds the VRAM budget is refused and listed under
  "REFUSED under the GPU-only residency ruling" (never silently hidden, per the comment at
  lines 88-90). Confirmed: nothing pulls a model automatically (`print_pull_suggestions()` only
  prints `ollama pull` text, never executes it), and nothing switches `config.yaml`'s model
  without the explicit `--write` flag typed by the operator. So the two specific behaviors the
  task asked to verify — "cannot silently pull" and "cannot silently switch models" — both hold.
  However, the module does **not** pin specifically to `qwen3:8b` by name; it picks whatever
  scores highest among models that fit the VRAM budget (`FAMILY_TIERS` + size heuristic). On this
  machine's current install and 10GB-card numbers that happens to resolve to `qwen3:8b`
  (`llama3.1:8b` is the only other model both tier-5-adjacent... actually tier 3... and
  small enough to fit), but a newly-pulled model that both scores higher under `FAMILY_TIERS` and
  still fits the residency budget would be auto-selected on the next `--write` run with no
  explicit check against the owner's specific "qwen3:8b, and stick to it" ruling — only the
  general residency property is enforced, not the specific model identity. Not a bug in the code
  as written (the design intent per `CLAUDE.md`/the module's own docstring is "pick the best
  installed model," not "always use qwen3:8b"), but worth flagging as a gap between the owner's
  stated ruling and what the tool actually pins.

- **`pick_model.py:239`** — `weight_gb()`'s fallback heuristic `parse_param_size(model_entry) *
  0.6` (labeled "~Q4 bytes per param") is only used when Ollama's API omits the `size` field
  entirely (line 236-238 prefer real on-disk `size` first). If an F16/BF16 model were installed
  and `size` were ever missing, this would underestimate its VRAM footprint by roughly 3x,
  letting an oversized model pass the residency gate. Believed low-likelihood in practice since
  Ollama's `/api/tags` reliably reports `size`; recorded as SUSPECTED, not verified against a live
  Ollama instance.

- **`entity_match.py`** — read in full; no defects found. The qualifier gate (`qualifier_compatible`,
  lines 107-127), the "one return shape always" contract fix documented in its own comment
  (lines 190-200), and `candidates()`'s uncapped-by-default `limit=None` (Hard Rule 0 compliant,
  with `truncated` flagged explicitly when a caller does pass one) are all correct as written.

- **`recover_folder_records.py`** — read in full; no other defects found beyond the MINOR note
  above. The `EXCLUDED_REGISTER_SOURCES = {"ME"}` filter and its justifying comment (lines 62-71)
  check out against the stated problem (garbage-bucket cross-contamination).

- All `[:N]` slices found elsewhere in this batch (`magnitude.py:387,393,730,878,882,1042,1099`;
  `zfighters.py:459,474`; `coverage.py:213,220,223,225`; `recover_folder_records.py:59,169`) are
  display/print-width or log-message truncations, not truncations of a roster/page/chunk/entry
  list being persisted or acted on — compliant with Hard Rule 0's display-formatting exception.
  `magnitude.py`'s `candidates()` (line 415) and `queue()` (line 904) both default their `cap`/
  `limit` params to `None` (full, uncapped list) and only truncate on an explicit caller-supplied
  value — the same opt-in pattern the charter's `--pilot N` uses elsewhere in this project.

- No bare `except:` found in any of the seven modules. Every `except Exception:` seen was paired
  with a `silence.note(...)` call recording the failure by class, consistent with the project's
  `silence.py` discipline.

---

## Summary counts
- BLOCKING: 1
- MAJOR: 4
- MINOR: 6
- NOTE: 5
