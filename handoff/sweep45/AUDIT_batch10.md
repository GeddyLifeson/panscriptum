# sweep45 — batch 10 audit

**Modules:** `foreman.py` (1762), `rigor.py` (984), `custodes.py` (698), `endpoint.py` (563),
`canon_backup.py` (472), `grounding.py` (334), `context_budget.py` (296), `suppressions.py` (254).
**5,363 lines, all eight read end to end. No sampling, no skipped region.**

Read-and-report only. No source file was edited. No battery tool (`drill.py`, `verify_math.py`,
`allsweep.py`, `publish.py`, `mutate.py`) was run; the DRILL_BREACH halt was left standing.

---

## Filed

### `df385729e15f` — MAJOR / LOCAL — `foreman.owner_queue` reports a denied write as written
`src/foreman.py:1554-1567`, consumed at `:1673-1674`.

The owner queue is staged to a pid/thread-qualified scratch name and landed with
`if not silence.replace_retry(_tmp, FOR_OWNER): silence.note("foreman.py:for-owner-write")`,
then falls through to an unconditional `return FOR_OWNER` — the same value success returns.
`round_once` prints `f"\n{len(owner_items)} for the owner -> {p}"`, so a denied landing prints
`7 for the owner -> ...FOR_OWNER.md` over a file that still holds the previous round's queue.

Why it matters: FOR_OWNER.md is the only landing place for the OWNER lane and for the
SCOUT_BLOCKED section, and `publish.py` copies it into the export tree every ten minutes — which
is the reason this function's own comment at `:1544-1546` demanded atomicity. A denied replace on
this machine is the ordinary outcome (`silence.replace_retry`'s docstring exists for exactly the
Windows reader-holds-the-target case, and publish.py is a standing reader of this file).

Every sibling writer in the same file already refuses this shape — `reprove_pool` (`:222-224`),
`triage_swallowed` (`:354-359`), `restart_ollama` (`:1064-1067`) — and `grounding.main`
(`grounding.py:323-328`, order e7b6dcc8d630) was corrected the other way. `owner_queue` is the
one writer in `foreman.py` that still returns the cheerful sentence the file's own comment at
`:349-353` names as the defect.

Not covered by the existing pin: verify_math §19b `_for_owner_landing_b19` asserts only that the
write is staged and atomic, never that the verdict is read. Zero orders in the queue mention
`owner_queue`.

### `7368cd63bd2c` — MINOR / LOCAL — `rigor.main()`'s MDL audit hardcodes the table it audits
`src/rigor.py:867-870` vs `src/chord_field.py ADJUDICATIONS`.

The audit loop restates the charter's five declared betas as literals (8 / 32 / 64 / 96 / 128).
The live table holding those numbers is `chord_field.ADJUDICATIONS` (`beta_bits` at
chord_field.py:110, :167, :72, :91, :149, plus A4 at 0 on :128), and rigor's own comment at
`:859-866` *names* that table while explaining A4's deliberate omission. There is no
`import chord_field` in rigor.py.

Consequence: the FINDING branch at `:886-894` — installed by run #21 precisely so the verdict
could no longer be printed unconditionally — is computed over frozen literals. Floors are
4.58 / 13.58 / 16.04 / 25.04 / 34.78 against 8 / 32 / 64 / 96 / 128, all above by 1.7x-3.7x, so
`_underpriced` is empty and stays empty for any edit to chord_field.py. Lower A3's `beta_bits`
and rigor goes on printing "every declared cost sits above its MDL floor".

This is the module's own named defect shape: its docstring at `:28-40` records the identical
fault being repaired one paragraph earlier and states the rule — "name the live tables, never
copy them". Sections 1, 2 and 6 of `main()` were moved onto live tables for that reason; section
3 was not. Cross-references open order **7e360eaec3a6** (chord_field has no importer anywhere) —
this is why: its one natural consumer copies it instead.

### `8a5593b3e777` — MINOR / LOCAL — `kill_stalled_job`'s job-name key diverges from the standard's
`src/foreman.py:575,582-583` vs `src/standards.py:1511-1512`.

foreman: `owners = {fn[:-4]: frag for fn, frag in _LN.OWNER.items()}` — unconditional strip.
standards, which writes the names foreman then parses: `job = fn[:-4] if fn.endswith(".log") else fn`
— guarded. Both walk `lognames.OWNER`, the module whose header says a constant shared by writer
and reader cannot drift.

Today all six OWNER keys end in `.log`, so the derivations agree and the guard at `:582-583`
(`if not frag: continue`, "a job with no declared owner is not one this remedy may kill") **cannot
fire** — verified by tracing `names` back through the `([A-Za-z0-9_]+) \(\d+ min` regex to
`standards.py:1560`'s `"%s (%d min, %d bytes)"`, whose only sources are those six stems (the
unmeasurable suffix is deliberately shaped not to match). The comment therefore credits a
protection no data path exercises; the real limit on what is SIGTERMed is the loose
`frag in line and "python" in line` at `:593`.

It stops being dead the moment an OWNER entry does not end in `.log`: the two keys disagree,
`owners.get(job)` returns None, and a stalled job **with** a declared owner is dropped from
`killed`, from `unrestartable`, from the STALLED_UNRESTARTABLE escalation and from the returned
sentence. Remedy is one line (match the standard's guard) or, better, hoist the derivation into
`lognames.py` — the treatment `_standing_cmds` (`:402-415`) already got for this exact class.
The guard itself must **not** be deleted: it fails closed.

---

## Corroborated — already open, not refiled

| order | where | state |
|---|---|---|
| `d2e44a766769` | foreman.py restart_reader | still true; SIGTERMs `read.py --run` with no `_restartable` gate while the sibling refuses the same case |
| `5a269c4ad1ab` | foreman.py:686 | still true; `job in DENYLIST` is the patch denylist doing process-kill exclusion |
| `a39f5792c5f9` | foreman.py `_catalogue_batch` | still true; `len(gap)` is captured after off_roll and unnameable are popped |
| `6c3a42f8dbdd` | foreman.py:256 | still true |
| `90945e55b1c9` | foreman.py:1385 | still true |
| `d021f0c7f821` | rigor.py:577 (was :549) | still true; `if k < M else 0.0` after `_log2_choose` already returns 0.0 for `k >= n` |
| `233cc167e4c0` | rigor.py:739-740 (was :711-713) | still true |
| `dc501e776a2b` | rigor.py:266 | still true |
| `d79dd404fef2` | rigor.py:154 | still true |
| `00a85c511b53` / `d27e95a57233` | custodes.py `table_faults` | still true; `table_faults()` exists and `main()` now exits 1 on a fault, but no battery row reads it |
| `df960819fdf8` | endpoint.py:355-363 | still true; `by` is built over every row, only three modes printed |
| `570525d35825` | endpoint.py:396 | still true, but now answered in source by the comment block at `:387-394` citing a60c150b6303 |
| `323703189931` | canon_backup.py `verify()` | still true; `changed` and `added` are counted and their names discarded (`gone` alone names members) |
| `f844326cafc8` | grounding.py:308 | still true; `{s[:28]:<30}` is an unmarked cut |
| `98f18453deaf` | grounding.py:218 | still true (question, synthesis block appended) |
| `9adb8291c16c` | suppressions.py:205-206 | still true; the whole-repo `glob.glob(..., recursive=True)` is inside the per-row loop |
| `f5503302ce44` | data/SUPPRESSIONS.json | still true, **verified against the data**: the three live reasons are 175 / 137 / **300** characters and the 300 one still ends mid-word, `"...this only sur"` |

## Open orders that appear ALREADY FIXED in source (stale, not refiled)

Each checked on a **code** line, not on a comment describing a repair.

* **`7604e95da60d`** (foreman `kill_stalled_job` conflates unmeasured with passed). The order
  quotes `if not row or row.get("holds"): return True`. Source now has two separate branches at
  `:557-562`: `if row is None: return False, "...UNKNOWN; nothing killed"` and
  `if row.get("holds"): return True, "no job is stalled now"`.
* **`61037867dc5d`** (canon_backup snapshot stamp collision on `canon-<stamp>.zip`). Source at
  `:156-157` is now `stamp = stamp or "%s-%d-%d" % (time.strftime("%Y%m%d-%H%M%S"), os.getpid(),
  threading.get_ident())`. The name still sorts (fixed-width timestamp leads), so `prune()` and
  `newest()` are unaffected.
* **`980ccacdcead`** (custodes `main()` cuts `refuses` at 44 chars). Source at `:640` prints
  `c['refuses']` whole.
* **`c9146abf92df`** names `src/foreman.py:189` as a whole-document writer of
  `data/SWEEP_ROLL.json`. **`foreman.py` contains no reference to SWEEP_ROLL at all** (grep: zero
  hits). The `roll.py:127` half may still stand; the foreman half of that `where` is wrong or
  stale.

## Judged deliberate design — examined and NOT filed

* **`custodes.convene`'s `covers_every_reading`** is a tautology (`half` is defined as
  `max(1.96*sd, max|v-consensus|)` and only widened after). Explicitly declared as such at
  `:542-550` with the reason it is kept and the better check it is not. Left alone.
* **`custodes._transit_widening`'s third `source is None` branch** (`:411-417`) is unreachable
  while Lumen carries the flag, and says so, existing so that removing the flag reads as a change
  in the college rather than as a measurement.
* **`custodes.CUSTODES` tilt 0.0 with non-zero sensitivity** — the known shape, already filed.
  Both zero-tilt entries declare 0.0 today with written reasons; `table_faults()` refuses the
  coupling and `main()` exits 1 on it.
* **`suppressions._preview`** (`:45-56`) — checked as the cited house form. `s if len(s) <= width
  else s[:width-1] + chr(8230)` is **correct**: the marker is present, the result is exactly
  `width` characters, and both call sites (`:201`, `:249`) pass positive widths. The precedent it
  is cited for holds.
* **`foreman` "unrestartable stall is reported, not killed"** and the 95 STALLED_UNRESTARTABLE
  escalations — documented intent per the brief; no destructive act is taken on that reading.
  `kill_stalled_job` refuses the kill and escalates at SUPERVISOR, which is the correct rung.
* **`foreman.kill_duplicate_jobs`'s `None` creation time** (`:688-703`) — an unreadable
  CreationDate now carries `None`, the whole job is skipped, and the skip is reported. Fails
  closed correctly.
* **`foreman.restart_ollama`'s stamp read** (`:1057-1067`) — `FileNotFoundError` proceeds,
  anything else refuses. Fails closed correctly.
* **`foreman.clear_learned_caps`** (`:175-178`) — `json_valid(learned) AND
  json_extract(learned,'$.rpm') = 1` is a genuine refusal, not a fallback. Correct.
* **`canon_backup.members(strict=True)`** — verified against the live tree: `data/records/` holds
  **216 `.json` files and zero subdirectories**, so "every `.json` directly inside it" is in fact
  the complete set. The refusal on a missing declared path is real.
* **`silence.replace_retry(...) is False`** in `canon_backup` (`:208`, `:425`) — checked
  `silence.py:656-673`; the function returns only `True` or `False`, never `None`, so `is False`
  is equivalent to `not` and is not a guard that cannot fire.
* **`context_budget`** — `assert_fits`, `system_for`, `feats_block_budget` and `ContextOverflow`
  all have real production callers (`generate.py:216,351`, `manifest_builder.py:369,373`), so
  none is a guard aimed at a dead function. An unreadable prompt file still widens the budget in
  the truncating direction, but the widening is consistent with what `generate.assert_fits`
  actually measures at send time (both read the same file), so the two layers do not disagree.
  Noted, not filed — the residual risk is a chapter generated with an empty system prompt, which
  is `generate.py`'s territory, not this batch's.
* **Bare `except Exception:` returning without recording** — none found. Every handler in all
  eight modules carries a `silence.note`, an honest failure return, or a re-raise. `rigor.py`,
  `custodes.py` and `grounding.py` contain no `except` clauses at all.

## Observation, not a finding

`data/records/` holds two non-`.json` files that `canon_backup.members()` correctly ignores:
`getter-robo.json.precatfix` (77 KB, 2026-08-22) and
`gundam-all-centuries-incl-g-gundam.json.25428.25044.tmp` (992 KB, 2026-09-04 07:04). The second
is orphaned `silence.write_json` scratch litter from a denied replace. Nothing was lost — the live
`gundam-....json` is 5.58 MB and newer (10:49) — but it is a canonical-directory scratch file that
no reaper covers, unlike `canon_backup.prune`'s `_writing-*.zip` sweep.
