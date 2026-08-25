# Batch 03 audit — foreman.py, catalogue_web.py, entity_match.py, anchors.py, catalogue_models.py, module_index.py

Every line of every file read in full (foreman.py 1264 lines, catalogue_web.py 362, entity_match.py
278, anchors.py 232, catalogue_models.py 171, module_index.py 83). This is run23; batch02's sweep22
audit already covered foreman.py/catalogue_web.py/entity_match.py/anchors.py once (plus two files not
in this batch) — this pass re-verifies those four independently and adds catalogue_models.py and
module_index.py, which were not previously assigned together with this set.

---

## foreman.py

### CONFIRMED — foreman.py:996 — non-atomic write to a LIVE `src/*.py` module during a model patch

```python
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        lines[start:end] = [new]
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        good, why = _checks_pass(module)
        if not good:
            shutil.copy2(backup, path)
```
(`attempt_patch`, lines 989–1009.) A backup is taken first (`shutil.copy2`, line 991) and restored on
any check failure or exception, which limits the blast radius — but the write to `path` itself is a
bare truncating `open(path,"w")`, not `silence.write_json`/`replace_retry`. A crash or kill between the
truncate and the `writelines()` call (or a reader importing the module mid-write, which is exactly what
`_checks_pass` does two lines later via `import <module>`) can observe a truncated/partial `.py` file.
VERIFIED — matches the already-filed finding exactly; still present, same shape, same lines.

### CONFIRMED (with detail) — restart_reader / kill_stalled_job (M15): the reader is bounced for a stall the reader did not cause

Precisely what each standard's remedy list does (`REMEDIES`, lines 733–770):

```python
    "every running job is advancing": [kill_stalled_job],
    ...
    "the library's counters are moving": [reprove_pool, restart_reader],
    ...
    "corpus read is progressing": [restart_reader],
```

`round_once`'s dispatch loop (lines 1144–1195) tries each remedy in order and `break`s the whole list
the first time one returns `did=True` (unless marked `.always`). Neither `reprove_pool` nor
`restart_reader` is marked `always`. Consequence:

- Under **"the library's counters are moving"**, `reprove_pool` runs first and returns `True` on
  *any* successful re-measurement — including `0 of N buckets answer` (`foreman.py:162`,
  `return True, f"{len(ok)} of {len(rows)} buckets answer"` — success is "the measurement ran", not
  "the pool is healthy"). So `restart_reader` under this standard fires only if `reprove_pool` itself
  raises.
- Under **"corpus read is progressing"**, `restart_reader` is the *sole* remedy — no pool-repair
  alternative in the list at all. Whatever causes the reader to look non-advancing (reader genuinely
  stuck, *or* the pool it depends on being exhausted/answering nothing), the only action taken is
  bouncing the reader process (`os.kill(pid, SIGTERM)`, lines 373–381).

`restart_reader`'s own docstring (lines 342–350) states the mismatch outright: *"the counters-flat
stall it serves is precisely the case where the reader is alive, logging failures, and doing nothing"*
— i.e. the authors know the standard this remedy answers is frequently a pool symptom, not a reader
fault, and the remedy still targets the reader with no pool check first. This is the exact mechanism
named in M15, located here (the `REMEDIES` table + `restart_reader`), not in `overnight.py`.

`kill_stalled_job` (lines 387–460) is a different, better-scoped mechanism: it reads
`standards.check(...)`'s row for `"every running job is advancing"`, regex-parses job names out of
the row's free-text `observed` field (`r"([A-Za-z0-9_]+) \(\d+ min"`, line 413), resolves each name to
its process fragment via `lognames.OWNER`, and kills only processes matching that fragment. **What
the stall test actually measures is not visible in this file** — it is computed by
`standards.check()` (not in this batch) and handed to `kill_stalled_job` as pre-formatted text;
`kill_stalled_job` trusts that text completely and has no way to tell "this job's own logic is stuck"
from "this job is idle because an upstream dependency (the pool) has nothing to give it." That
distinction, if it exists at all, would have to live in `standards.py`.

VERIFIED for everything traceable inside foreman.py (the REMEDIES table, the break-on-first-success
dispatch logic, restart_reader's unconditional kill, and restart_reader's own docstring admission).
The root-cause attribution inside `standards.check()` itself is UNVERIFIED (out of batch).

### CLEAN / already-fixed, confirmed by inspection
- `clear_learned_caps`, `adopt_hosts` (substring-vs-regex fix at line 174–178), `triage_swallowed`
  (archive-then-clear ordering, both `replace_retry` return values checked, third false-success path
  fixed per its own comment), `recatalogue_models`, `refresh_coverage`, `kill_duplicate_jobs`
  (supervision-chain exclusion, unstamped-process guard), `_fandom_reachable`, `run_catalogue_gap`,
  `run_completeness_audit` (`.always = True`, correctly wired), `run_charter_regression`,
  `restart_ollama` (30-minute rate limit via atomic stamp file, checked), `_checks_pass` (reads
  `RESULT: N passed, M FAILED` via regex rather than substring — the "0 FAILED"-in-"10 FAILED" bug is
  fixed), `lines_changed` (now `difflib`-based, matches its own docstring's `> MAX_PATCH_LINES`
  claim), `regex_touched`, `_literals` (module-level `ast` import present, no more `NameError`
  swallowed by a bare `except`), `_retire`, `owner_queue` (full URL listing for `SCOUT_BLOCKED.json`,
  no `[:3]` cap — matches its own comment that a cap here would violate Hard Rule 0 for a human
  decision document), `round_once`'s per-remedy and per-round exception fencing, `main()`'s outer
  try/except around the loop. All read in full; all match their own docstrings/comments; no new
  defects found in any of them.

### Reviewed, judged non-violations (bounded action, not a truncated listing)
- `scout_hostless` (line 192): `SC.sweep(limit=4)` bounds how many hostless sources one foreman round
  processes. `scout.py` is not in this batch, so whether this genuinely starves sources beyond the
  first 4 across repeated rounds (vs. round-robining) is UNVERIFIED — worth a follow-up read of
  `scout.py`, but as written here it reads as a per-cycle throughput bound (cost control on model
  calls), not a listing of sources being silently truncated for a reader.
- `round_once` line 1205: `sorted(open_f, ...)[:3]` bounds MODEL-lane patch attempts to 3 per round.
  Findings not attempted stay `open` and are retried next round rather than being hidden — this
  throttles a repair action's blast radius per cycle (consistent with the module's own stated
  philosophy of fencing the MODEL lane hard), not a truncated report of findings.

---

## catalogue_web.py — CLEAN

Hard Rule 0 is handled deliberately and explicitly: `MAX_PER_SOURCE = None`, `MAX_PER_CATEGORY = None`,
`CATEGORY_SCAN_DEPTH = None` (lines 53–58), with a `SystemExit` trip-wire (lines 187–190) if
`MAX_PER_SOURCE` is ever set again, and every category is pulled with `limit=None`
(`ws.category_members(sub, c, limit=None)`, lines 95, 168) and ranked-never-truncated
(`ws.rank_by_size(sub, titles, top=None)`, lines 100, 175). Both `catalogue()` and
`catalogue_composite()` were checked line by line — no cap anywhere on the entries transcribed.

Concurrency: `_one()` (lines 317–353) runs the network-bound `catalogue()` call *outside* `_wlock`
(three workers via `ThreadPoolExecutor(max_workers=3)`, line 355) but does every mutation of the
shared `roll_by_name`/`roll` structures and the `save_roll(roll)` write *inside* `_wlock`
(lines 327–353) — correctly serialized, matches the file's own comment ("Record and roll writes are
serialized under a lock"). `save_roll` itself writes via `.tmp` + `_sil.replace_retry` (lines 76–79).
Record writes go through `pipeline.write_record_catalogue`, and its boolean return is checked
(line 344) before the roll is updated — a denied write correctly leaves `roll` untouched and reports
`WRITE DENIED` rather than a false "catalogued". No bare `open(path,"w")+json.dump` on any shared file
anywhere in this module.

## entity_match.py — CLEAN

Pure-function module, no file I/O of catalogue/shared state (only `embed_available()` does network
I/O, to a local Ollama endpoint, wrapped in try/except that returns a reported `available: False`
rather than raising or silently returning an empty list — satisfies rule 2, distinguishable from
"found nothing"). `candidates()`'s `limit` parameter defaults to `None` and is documented as Hard
Rule 0-compliant (lines 180–182); truncation, when a caller explicitly opts in, is flagged via a
`"truncated"` key rather than silently shrinking the result (lines 226–229, 237–239). The
`qualifier_compatible()` gate (lines 107–127) matches its own corrected docstring (normalized
comparison, not literal string equality — the stale "EXACTLY" wording was already fixed per the
in-file note at lines 28–32). No concurrency surface. Nothing to report.

## anchors.py

### CONFIRMED — anchors.py:215 — the "monotone floor → ceiling" self-check is structurally guaranteed to read `False`

```python
    order = ["The Skate Guy", "A Sword", "Yggdrasil", "Goku", "The Seat of the Creator"]
    vals = {}
    for name, a, res, inst, col in rows:
        vals[name] = A.LADDER.index(a["anchor"]) + (res.get("decimal") or 0.0)
    prev = None
    ok = True
    for n in order:
        if prev is not None and vals[n] < vals[prev]:
            ok = False
        prev = n
```
`vals[name]` is dominated by `LADDER.index(anchor)` (the decimal remainder is < 1.0). Declared anchors:
Skate Guy `M0` (line 73), A Sword `M0` (line 131), **Yggdrasil `M6`** (line 153), **Goku `M5`**
(line 93), Seat of the Creator `M10` (line 115). `order` places Yggdrasil immediately before Goku, so
the check compares `vals["Goku"] ≈ 5.x` against `vals["Yggdrasil"] ≈ 6.x` and sets `ok = False` on
every run, regardless of what the Assay/Instrument/College formulas actually compute — a permanently-
red invariant that can never distinguish a healthy instrument from a broken one, in a module whose
own stated purpose is "to find breakage, not to display success." VERIFIED — reproduced independently
against `assay.LADDER`'s ordering and each anchor's declared band; unchanged from the prior filing.
Repair options unchanged from before: reorder `order` to ascending `LADDER.index` (…, Goku, Yggdrasil,
…), or lower Yggdrasil's declared anchor if M6 is not actually intended.

### CLEAN otherwise
`vector_score`'s clamping (lines 55–58), all five `ANCHORS` score dictionaries, and the per-anchor
print block (lines 183–210) are internally consistent and correctly wired to `assay.py` /
`custodes.py` / `rigor.py`. No caps, no swallowed exceptions, no shared-file writes in this module at
all (it only prints).

---

## catalogue_models.py — CLEAN

Asks each provider's own `/models` or `/v1/models` endpoint rather than trusting static config
(matches its docstring's stated purpose exactly). `ask_provider`'s per-URL try/except records failures
via `silence.note` and returns a structured `{"provider", "error"}` rather than a bare `None` — the
absent-vs-failed distinction rule 2 asks for is honored. The final `payload` write uses
`silence.write_json(OUT, payload, ...)` (line 157) — correct two-writer-contract usage, not a bare
`open()+json.dump`. `rows` (line 128) is built from *every* provider in the config
(`sorted(provs.items())`, no cap) via `ThreadPoolExecutor`; no read-modify-write race, since each
worker only computes its own row and the list is assembled by `ex.map` on the main thread.

Two cosmetic, non-violating truncations, both display-only with the full data preserved elsewhere in
the same payload: `"available_sample": r["models"][:8]` (line 146, a labeled *sample*, not presented
as the full list) and the printed "Current alternatives" line `", ".join(r["models"][:10])` (line 153,
console output only — `payload["providers"]` still carries every model id via `sorted(ids)` at
line 102, unsliced). Neither hides data from the JSON record; both are named as previews.

## module_index.py — CLEAN

`main()` builds the module list from *every* `src/*.py` file (`glob.glob`, line 53, no cap) and the
`GROUPS` membership only controls print ordering — anything not in a named group still appears under
"Everything else" (`rest = sorted(set(mods) - placed)`, lines 68–74), so nothing is dropped from the
generated page. `first_line()` returns distinguishable placeholders for "no docstring" vs. a parse
failure (`"(no docstring)"` vs. `"(unparseable)"`, lines 44–48), satisfying rule 2.

The final write, `open(OUT, "w", encoding="utf-8")` at line 75, is a bare non-atomic write with no
`silence.write_json`/`replace_retry`. Checked whether this is a two-writer-contract violation: grepped
all of `src/*.py` for both `MODULE_INDEX` and `module_index` — the only hits are inside
`module_index.py` itself. Nothing else reads or writes `handoff/MODULE_INDEX.md`, and nothing schedules
this script automatically (its own docstring gives the invocation as a manual, standalone command,
`python src/module_index.py`, run by a person regenerating documentation). With no concurrent reader
and no second writer, this is a real non-atomic write but not the shared-file hazard rule 4 targets —
noted for completeness, not filed as a finding of consequence.

---

## Summary table

| file | high | medium | low/notes |
|---|---|---|---|
| foreman.py | 1 confirmed (996, non-atomic live-src write) + 1 confirmed w/ detail (M15 mechanism) | 0 | scout_hostless limit=4 and round_once [:3] patch cap reviewed, judged non-violations |
| catalogue_web.py | 0 | 0 | CLEAN |
| entity_match.py | 0 | 0 | CLEAN |
| anchors.py | 1 confirmed (215, dead invariant) | 0 | otherwise CLEAN |
| catalogue_models.py | 0 | 0 | CLEAN (two labeled display-only slices) |
| module_index.py | 0 | 0 | CLEAN (one non-atomic write to an unshared, unread-elsewhere doc file, noted not filed) |
