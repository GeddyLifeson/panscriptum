# SWEEP 38 — AUDIT, BATCH 16

Agent: `sweep38-batch16`. Modules assigned: 8 (4,465 lines). **All eight read in full.**

Environment: `C:/Users/imarl/miniconda3/python.exe`, `PYTHONIOENCODING=utf-8`.
Reproductions run from the batch scratch directory; nothing under `src/` was edited.

---

## dashboard.py — 1,066 lines, read in full

Read whole, including the embedded `PAGE` HTML/JS. The panel builders, the TTL memo, the
movement history repair and the safety panel are all consistent with their comments, and the
three list caps this file's own comments record as ruled truncations (open findings, swallowed
failures, breached nets) are genuinely gone — `_watch()` returns every open finding and every
swallowed tag (measured live: 5 open findings, 54 swallowed tags, no slicing), and
`panelSafety` iterates `br` and `qn` in full.

Findings:

* **Per-row string caps survive inside the uncapped lists.** `_watch()` stores
  `(f.get("actual") or "")[:160]` for every open finding (line 328) and `safety()` stores
  `r.get("reason", "")[:120]` for every quarantined host (line 579-580). Both land straight in
  the rendered table with no ellipsis and no full text anywhere on the page, so a reader cannot
  tell a 160-character finding from one that was cut. Measured live: the longest `actual`
  returned is exactly 160. The two sibling *list* caps in the same function were ruled
  truncations on 2026-08-24; these per-row caps sit three lines away and were not visited.
  Filed as `DASH_ROW_TEXT_CAP`.

* **A literal `\n` inside a non-raw docstring** at line 356
  (`A progress bar at 12.8%\n    looks identical ...`). Confirmed with `cat -A`: the two
  characters `\` `n` are on disk. Python's escape processing turns it into a newline so
  `__doc__` reads correctly, but the source line is 143 columns and it is a heredoc-transit
  artifact of exactly the class the file's own `_BAD_CHARS` guard exists for — that guard
  watches `\b \v \f \a` and cannot see a surviving `\n`. Filed as `DASH_DOC_ESCAPED_NL`.

* **`throughput()` calls `sqlite3.connect(path)` unguarded and never closes it** (line 175).
  `sqlite3.connect` on a missing path *creates* it: reproduced, a 0-byte
  `cascade_scratch.db` appears and the query then fails with `no such table: usage`, which is
  swallowed to `silence.note("dashboard.py:throughput")` on **every 5-second poll**. Not biting
  today (the real db is 10.3 MB), so filed INFO. `DASH_THROUGHPUT_RO`.

Examined and judged NOT defects:

* `movement()`'s ungated `silence.write_json` — the three conditions its comment gives for that
  being safe all hold today; verified `hist` is reconstructed in memory and the stall detector
  still fires against a frozen file.
* `movement()` returning `[]` on the append/serialise handler, which the page renders as the
  benign "No history yet". The `except` covers only `hist.append` and the JSON serialisation
  (`write_json` answers `False` rather than raising for a denied replace), and every value in
  `row` is an int/float/None, so I could not construct a reachable failure. Recorded here so the
  next reader does not have to re-derive it.
* The `standards.py:663` citation in `_read_row`'s comment has drifted — the live site is
  `standards.py:1116`, which now correctly reads `read.get("dropped")`. It is a past-tense
  narrative of a fixed defect, so no order.

---

## local_agent.py — 1,027 lines, read in full

The six-gate patch machinery, the six documented `_safe()` bypass repairs, the blast-radius cap
and the escalation call sites all check out, and the ordering claims in the comments match the
code. Two real defects and one stale docstring:

* **Every tool result handed back to the model is silently cut at 12,000 characters**
  (line 996, `messages.append({"role": "tool", "content": json.dumps(res)[:SLICE]})`).
  Reproduced against `src/dashboard.py`:

  ```
  slice chars              : 12000
  chars_after_slice        : 43498
  total_chars              : 55498
  json.dumps length        : 12677
  chars dropped on the way : 677
  parses as JSON           : NO -- JSONDecodeError
  'chars_after_slice' present in what the model sees : False
  'total_chars' present in what the model sees       : False
  ```

  The two fields that exist *specifically* so nothing falls off the end are the two that are
  always destroyed, for every file over 12 KB — which is most of `src/`. The module docstring's
  "sliced -- iterative reads, never a truncation" and `SLICE`'s own comment "a WINDOW, not a
  cap ... the tool says how much remains so nothing silently falls off the end" are both false
  as shipped. Filed as `LA_TOOL_RESULT_CUT`, MAJOR.

* **`main()`'s `[:8000]` print cut hides the achievement verdict and the half-written-file
  ALARM.** Reproduced on a realistic exhausted-turn-budget result (24 logged patches, each
  carrying `why`/`find`/`replace` at their 200-char store): the JSON is 19,843 characters, so
  `achievement` and `ALARM` are both invisible to the operator. On the answer-exit path
  `error` is inserted after `patches` too and is lost as well. This is the same shape the file
  already documents and fixed once for `json.dumps(res)[:110]`. Filed as `LA_MAIN_PRINT_CUT`.

* **The module docstring says the harness "hands the model four tools" and lists four**
  (lines 9-14); `TOOLS` has six — `find_symbol` and `run_check` were added later with their own
  long rationale docstrings and the header was never updated. Filed as `LA_DOC_FOUR_TOOLS`.

---

## silence.py — 643 lines, read in full

* **`main()` prints only the first twelve line numbers per file** (line 235,
  `', '.join(map(str, lines[:12]))`) with no "and N more". Measured on the live tree: 176
  silent handlers, 158 line numbers printed, **18 hidden** — `drill.py` shows 12 of 20,
  `mutate.py` 12 of 17, `sweep_plan.py` 12 of 15, `workorders.py` 12 of 14. The per-file count
  is printed, so the magnitude is honest and only the *identities* vanish, which is precisely
  the reasoning `dashboard._watch` records for retiring its own rank-6 cap. Hard Rule 0. Filed
  as `SIL_AUDIT_LINE_CAP`.

* **`--instrument` bakes a line number into every tag it writes** (line 615,
  `silence.note("{base}:{node.lineno}")`). The tree is being hand-repaired one site at a time
  because of it — `dashboard.py:num-parse` and `dashboard.py:metrics-badline` each carry a
  paragraph about the label rotting, `catalogue_aurora.py:folder-xml-unparseable` a third —
  and the generator that produces them was never changed, so the next `--instrument` run
  reintroduces the class wholesale. Filed as `SIL_INSTRUMENT_LINENO`.

* **`_ensure_import` prepends to line 1 when a module has no top-level imports.** `last` stays
  0 and `lines.insert(0, "import silence\n")` puts the statement above the module docstring,
  demoting it to a bare expression and setting `__doc__` to None — the exact failure the
  function's own docstring says it exists to avoid, and several modules here read their own
  docstring. No file in `src/` triggers it today. Filed as `SIL_ENSURE_IMPORT_NOIMP`.

Examined and judged NOT defects: `swallow.__exit__`'s and `note()`'s bare `except: pass` (both
documented as deliberately total, correctly); `_handler_is_observed`'s three repairs (the
`Raise` node walk, the `node.name` load test and the body-only dump) all verified against the
parse tree; `append_line`'s `O_APPEND` single-syscall argument; `write_json`'s `separators`
deference and `_discard_tmp` on the denied-replace branch.

---

## endpoint.py — 522 lines, read in full

* **`register()`'s temp name carries pid and attempt but not the thread id** (line 505,
  `"%s.%d.%d.tmp" % (PAGES_FILE, os.getpid(), attempt)`). Two threads of one process at the same
  attempt number write the same temp path and can land each other's partial file — the exact
  collision the function's own docstring says "m100 retired repo-wide", and the one
  `silence.write_json` uses `threading.get_ident()` for. `_save()` above is safe only because
  `_SAVE_LOCK` serialises it; `register()` has no such lock. Filed as `EP_REGISTER_TMP_THREAD`.

* **Two absence-vs-failure holes in the fetch paths.** `fetch_raw.one()` records a ledger entry
  for every HTTP status class (a repair whose comment reads "A REFUSAL IS NOT AN ABSENCE") and
  then, twelve lines later, returns `t, None` for an HTML body with no note at all (line 320) —
  so an edge serving an error page reaches the caller as "this page does not exist", which is
  the same fault one branch over. `fetch_html.one()` does the same with its `len(text) > 400`
  floor (line 424): a systematically short page is dropped with no record. Filed as
  `EP_SILENT_ABSENCE`.

* **The `if __name__ == "__main__"` guard sits at line 359, mid-file.** Everything below it —
  `MODE_HTML`, `html_text`, `fetch_html`, `source_pages`, `register`, `PAGES_FILE` — is
  undefined when the module is run as a script. Imports are unaffected (`feats.py` uses
  `EP.source_pages` and `EP.fetch_html` and they resolve fine), so this is latent, but any CLI
  flag added to `main()` that touches the html mode will `NameError`. `MODE_HTML` itself has no
  reader anywhere in the tree — verified by grep. Filed INFO as `EP_MAIN_GUARD_MIDFILE`.

Examined and judged NOT defects: `_save()`'s merge-on-`_DIRTY` compare-and-swap (correct, and
the `_SAVE_LOCK`-before-`_LOCK` ordering is honoured at both sites); the DEAD-only TTL
asymmetry; `detect()` discarding `_save()`'s verdict (documented and correct — the hosts stay
in `_DIRTY`); `register()` raising on a run of refusals.

---

## anchors.py — 407 lines, read in full

Ran it: exits 0, all seven verdicts HELD, `A Sword 0.10  The Skate Guy 0.22  Goku 5.42
Yggdrasil 6.18  The Seat of the Creator 10.99`. The CLAIMS table, the ladder-membership verdict
and the missing-anchor guards are all genuine and all can fail.

* **`vals[name] = A.LADDER.index(a["anchor"]) + (res.get("decimal") or 0.0)`** (line 245) turns
  an assay *refusal* into a ladder value at the band floor. `assay()` has two paths returning
  `{"decimal": None, "reason": ...}` (`src/assay.py:886` and `:897`); the second — "no axis
  scored from cited feats" — is reachable from this file, and the monotone check would then
  grade a number the assay declined to produce, in the file whose whole premise is that a check
  that cannot fail is worse than no check. `or 0.0` also collapses a genuine 0.0 into the same
  value. Remedy: a `verdict("every anchor produced a decimal", ...)`. Filed as
  `ANCH_DECIMAL_FAILOPEN`.

* **The message the file's own comment condemns is still printed verbatim.** The comment at
  lines 232-236 states, as the finding worth keeping, that "this file's own message ('a reading
  about the ASSAY') quietly asserted" which side was lying; line 359 still prints
  `"This is a reading about the ASSAY, not about this script."` The 2026-08-25 ruling found the
  *declared ladder* wrong at two of four steps, so the message is wrong in the direction the
  comment names. Filed as `ANCH_BLAME_MESSAGE`.

Examined and judged NOT a defect: the ceiling claim's `str(v).startswith("30")` — the
faculties render as `"30 (Grade V)"` strings, so an equality test would not work, and
`min(30, ...)` in `assay.instrument` makes a `"300"` false positive unreachable.

---

## catalogue_aurora.py — 306 lines, read in full

The uncapped `slug()`, the legacy-cap-aware `record_path()`, the description-in-the-dedup-key
repair, the gated `write_record_catalogue` call, the gated `written` roster and the gated exit
code are all correct and all match their comments.

* **`SWEEP_ROLL.json` is written atomically but with no compare-and-swap** (line 282). The
  function reads the whole roll at line 194, mutates two fields per source across ten XML folder
  parses, and lands the whole document. Grep finds **seven** writers of this same file —
  `catalogue_aurora`, `catalogue_codex`, `catalogue_web`, `recover_folder_records`,
  `resync_roll`, `roll`, plus `foreman`'s state write in the same idiom — every one of them
  `silence.write_json`. That is the m42 lost-update shape verbatim, and `endpoint.py`'s own
  docstring names it: *"ATOMIC WAS NOT ENOUGH"*. Nothing fails, nothing tears; a concurrent
  writer's row simply disappears, and since the default work selection is `entry_count == 0`, a
  disappeared row means a source is silently re-catalogued or silently never picked up. This
  file's comment at line 273 still reads "ATOMIC: four scripts write this same roll" — the
  count is now seven and atomicity was the wrong property. Filed as `ROLL_LOST_UPDATE`.

Noted, not filed: `CUSTOM` is a hardcoded absolute path into the owner's Documents tree
(line 33). It fails closed (glob returns nothing, "no elements parsed", rc=1), which is the
right direction, so it is a portability observation rather than a defect. Raised as a question
below.

---

## deprecated/catalogue_local.py — 280 lines, read in full

`src/deprecated/README.md` says "do not run" and explains why (model recall filed as research,
"Chad (Seraura Urahara)"). The quarantine is documentation only:

* the file is a live entry point — `if __name__ == "__main__": main()` with no refusal, no
  `escalation.assert_clear`, no `import silence` (so the export-copy marker and `_BAD_CHARS`
  guards every sibling carries are absent);
* `main()` returns `None`, so the process exits 0 whatever happened — including when every
  source produced nothing;
* it writes `data/records/*.json` with a bare `open(path, "w")` + `json.dump` (line 263),
  bypassing `pipeline.write_record_catalogue` entirely. That is a third writer against a
  two-writer contract, and it is the precise region `local_agent.DENYLIST_PREFIXES` lists as
  `"data/records/"  # two-writer contract: pipeline.write_record only`;
* it rewrites the whole of `SWEEP_ROLL.json` non-atomically **inside the per-source loop**
  (line 268), so an interrupt lands a truncated roll;
* `slug()` still carries the `[:60]` cap that `catalogue_aurora.slug` documents at length as
  the identity truncation that orphans records;
* `catalogue_source` records a failed Ollama call as `per_cat[key] = 0` with no
  `silence.note` — a network failure filed as "this source has nothing in this category",
  which is the founding defect of `silence.py`.

Hard Rule -1's fourth property is that a safety in a file is not a safety that is running. A
README is not an interlock. Filed as `DEPRECATED_RUNNABLE` — the ask is a hard refusal at the
top of the file, not a repair of the six defects above.

---

## physics.py — 214 lines, read in full

The cleanest module in the batch. Every guard's comment matches its code, the NaN-vs-infinity
reasoning of order 7909342fefa4 is correctly implemented for `kinetic()`'s **speed** and for
`joules_for()`'s **volume**, and the `binding_energy` / `BAND_EDGES` divergence note is
accurate.

* **The same doctrine is only half applied: infinity is refused for speed and volume and
  accepted for mass and radius.** Reproduced:

  ```
  kinetic(inf, 10)         -> inf
  kinetic(1e308, 1e5)      -> inf
  sphere_volume(inf)       -> inf
  binding_energy(inf, 1)   -> inf
  kinetic(inf, inf)        -> REFUSED (speed guard fires first)
  binding_energy(1e200, 1) -> REFUSED (OverflowError, by accident of m**2)
  ```

  `not m > 0.0` catches NaN as a side effect of its shape and lets infinity straight through —
  which is word for word the diagnosis `joules_for()`'s own comment gives for the volume case it
  fixed. A joule figure of `inf` is not a quantity wearing the shape of one; it is an
  UNESTIMABLE body reported as an enormous one, and it flows to a band edge and a shelfmark.
  Filed as `PHYS_INFINITE_MASS`.

Nothing else found.

---

## Coverage

All eight modules read in full and recorded via `sweep_plan.record('run38', ..., batch=16)`.

---

## Orders filed (17)

| code | sev | handler | module |
|---|---|---|---|
| `LA_TOOL_RESULT_CUT` | MAJOR | RUN | local_agent.py |
| `SIL_AUDIT_LINE_CAP` | MAJOR | LOCAL | silence.py |
| `ROLL_LOST_UPDATE` | MAJOR | RUN | catalogue_aurora.py (+6 siblings) |
| `PHYS_INFINITE_MASS` | MINOR | RUN | physics.py |
| `DEPRECATED_RUNNABLE` | MINOR | RUN | deprecated/catalogue_local.py |
| `EP_SILENT_ABSENCE` | MINOR | RUN | endpoint.py |
| `SIL_INSTRUMENT_LINENO` | MINOR | RUN | silence.py |
| `EP_REGISTER_TMP_THREAD` | MINOR | LOCAL | endpoint.py |
| `LA_MAIN_PRINT_CUT` | MINOR | LOCAL | local_agent.py |
| `LA_DOC_FOUR_TOOLS` | MINOR | LOCAL | local_agent.py |
| `SIL_ENSURE_IMPORT_NOIMP` | MINOR | LOCAL | silence.py |
| `ANCH_DECIMAL_FAILOPEN` | MINOR | LOCAL | anchors.py |
| `ANCH_BLAME_MESSAGE` | MINOR | LOCAL | anchors.py |
| `DASH_ROW_TEXT_CAP` | MINOR | LOCAL | dashboard.py |
| `DASH_DOC_ESCAPED_NL` | MINOR | LOCAL | dashboard.py |
| `DASH_THROUGHPUT_RO` | INFO | LOCAL | dashboard.py |
| `EP_MAIN_GUARD_MIDFILE` | INFO | LOCAL | endpoint.py |

All seventeen `file_order` calls returned an order (checked, none printed `ORDER NOT FILED`).

## Questions, not findings — OWNER

1. **`catalogue_aurora.CUSTOM` is a hardcoded absolute path** into the owner's Documents tree
   (`C:\Users\imarl\Documents\5e Character Builder\custom`, line 33). Reading 1: this is correct
   and deliberate — the Aurora library is a fact about this one machine, the module exists to
   read the owner's own files, and it fails closed (glob finds nothing, "no elements parsed",
   rc=1) rather than producing wrong data. Reading 2: it is the one thing in the module that
   makes it unrunnable anywhere else, and it means a moved or renamed Aurora folder reports as
   "no elements parsed" — same message as a genuinely empty folder. If reading 1 stands, a
   one-line "the directory itself is missing" refusal would separate the two states; if reading
   2 stands, it belongs in config.yaml. Curatorial either way, so not filed.

2. **`assay.INSTRUMENT_WINDOWS` is zero-width at 6 of 11 bands** — `anchors.py` reports this on
   every run as an explicit OWNER QUESTION and I am relaying it because it is still open and the
   run I made reproduces it: every faculty reads 30 at M5 and above, so Goku (whose own anchor
   comment says `acumen=4.0, # not a planner, and the charter should not pretend otherwise`)
   prints the same six numbers as the M10 ceiling. `anchors.py` is right that it cannot rule on
   whether this is charter X.6 §6's declared saturation or the Instrument silently ceasing to
   measure most of the library. It is stated correctly, printed on every invocation, and needs a
   ruling rather than a work order.

3. **Should `silence --instrument`'s tag rename be a single pass?** `SIL_INSTRUMENT_LINENO` asks
   for descriptive tags instead of line numbers. Any such conversion orphans the existing
   `state/failures.json` history for the renamed tags. Filed at RUN with the hazard named, but
   whether the history is worth preserving (a mapping file) or worth losing is a call for
   whoever works it.
