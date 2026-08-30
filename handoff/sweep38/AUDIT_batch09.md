# SWEEP 38 — AUDIT, BATCH 09

Agent: `sweep38-batch09`. Run `run38`. 8 modules, 4,463 lines, all read in full.

Modules: `mutate.py`, `generate.py`, `build_terminal.py`, `zfighters.py`, `prose_gate.py`,
`catalogue_codex.py`, `thread_integrity.py`, `scope.py`.

Every claim below was checked against the code as it stands today and, where cheap, reproduced
with a measurement against the live data. Three candidate findings were **dropped** after
verification and are recorded at the bottom so nobody re-derives them next run.

---

## src/mutate.py (1,448 lines) — read in full

The sandbox architecture, the reap ledger, the ownership ceiling, the differential judging and
the `not_attempted` accounting all hold up. Five findings, one of them real.

### M1 — `_session()` prints STOP and does not stop (MAJOR, RUN)
`src/mutate.py:1395-1441`. Inside the per-target loop:

* `restored_exactly == False` prints `*** THE SANDBOX FILE WAS NOT RESTORED. Later targets are
  unreliable. ***` and escalates at MANAGER — then falls through to the next iteration and runs
  those "unreliable" targets anyway, in the same sandbox, printing their survivor lists as
  findings.
* `live_file_untouched == False` prints `*** THE LIVE FILE CHANGED DURING A SANDBOXED RUN.
  STOP. ***` and escalates at OWNER — and then does the same thing.

`escalation.escalate` returns the record; it does not raise (its own docstring: "Raising is the
CALLER's decision for rungs 1-4… Rung 5… writes the halt file"). So at OWNER a halt is now
standing, the loop keeps mutating, and `_session` returns **0**. `main()`'s own halt check at
:1303 refuses to *start* under a halt; nothing re-checks after one is raised mid-session. This is
the "a refusal that prints but does not stop the caller" shape, in the module written to find
exactly that shape.

### M2 — drifted line citation (MINOR, LOCAL)
`src/mutate.py:864`: "the junction case at :506-511". Lines 506-511 are the `ast.Compare` branch
of `_mutations`. The junction-unlink loop the sentence is about is at :856-862, two lines above
the comment.

### M3 — `_gate_result`'s `name` parameter is never read (MINOR, LOCAL)
`src/mutate.py:595`. Every call site passes it; the body uses only `cmd`, `cwd`, `timeout`, `env`.

### M4 — module constant carries an indented comment block (MINOR, LOCAL)
`src/mutate.py:728-730`. The two comment lines above `OWNERSHIP_CEILING_SECONDS` sit at four
spaces of indent at module level. Legal (comment-only lines emit no INDENT token) but it reads as
a stray function body.

### M5 — the lock is check-then-create, and released without checking the token (MINOR, RUN)
`src/mutate.py:215-233` and `:236-246`. `_lock_acquire` calls `active()` and then opens the path
`"w"`; two processes can both see no lock and both write one, and the second silently overwrites
the first's pid/token. `_lock_release` then does a bare `os.remove(LOCK)` with no comparison
against `_HELD` — whichever session finishes first deletes the lock a still-running session
believes it is holding, and `publish.py` is unblocked mid-run. The token is written into the
record specifically so ownership can be established; nothing ever reads it back.

### Checked and clean
* `_mutations` byte-offset handling (`_col`), gap location (`_between`), token bounding
  (`_token_pos`), the per-occurrence dedup key `(lineno, new_src)`, and the `skipped` accounting.
* `muts[:limit]` is an interactive cap, reported through `result["capped"]` and printed. Correct
  under Hard Rule 0.
* `_journal`/`survivors` store `old_line.strip()[:120]`. **Latent only**: measured, the longest
  line in any of the three TARGETS is 101 chars (`assay.py`), and the house limit is 100, so the
  cut cannot fire today. Not filed.

---

## src/generate.py (716 lines) — read in full

The exit-code plumbing, the atomic `save_raw`, the failures.json pop/clear accounting, the P8
meta-language ban and the three prose-gate layers are all live and correctly wired.

### G1 — three capped lists in operator output and in stored failure records (MINOR, LOCAL)
* `:514-517` — `sorted(refused_src.items())[:20]` with "… and N more". The evidence-floor
  hold-back list is precisely what an operator reads to decide what to go and read next.
* `:410-411` — `', '.join(missing[:8])` with "(+N more)". This string is written into
  `failures.json` as the `error` field, so the record of *which entries were never written* is
  truncated on disk.
* `:405` — `"; ".join(_unearned[:5])`; the count is stated but only five of the fabricated-assay
  entities are named, again in the stored failure record.

The house standard set elsewhere this shift is stricter than "and N more": `mutate.py --list`
("no cap, no 'and N more' — because this is the listing a person reads"),
`thread_integrity.main` and `catalogue_codex`'s two collision reports all print in full.

### Checked and clean
`pending[:args.limit]` (a declared CLI flag) and the dry-run `pending[:3]` (which states
"showed 3 of N") are legitimate. The six discarded `save_json` returns inside the loop are
argued for in the docstring and the two final writes do set rc.

---

## src/build_terminal.py (607 lines) — read in full

### B1 — the write verdict never reaches the exit code, and the temp file is orphaned (MAJOR, LOCAL)
`src/build_terminal.py:595-603`. `landed = silence.replace_retry(tmp, OUT)`; on failure it prints
`WRITE DENIED` and then **`return 0`**. `sys.exit(main())` at :607 therefore reports success for a
run whose only product did not land. `catalogue_codex.py:315-331` and `generate.py:700-706` both
settle this the other way in the same tree, with the reasoning written out.

Second half: `silence.replace_retry` does **not** unlink `tmp` on failure (verified — it notes
`replace-denied`/`replace-failed` and returns False). The temp name carries pid and thread, so
every denial leaves a uniquely-named `output/registry_terminal.html.<pid>.<tid>.tmp` behind and
nothing ever collects them. `generate.py:_discard_tmp` exists for exactly this and is not used here.

### B2 — four catalogue-derived values reach innerHTML unescaped (MINOR, LOCAL)
`src/build_terminal.py:542-545`, inside `selectWorld`: `${f.landform}`, `${f.climate}`,
`${f.condition}`, `${f.tech}` are interpolated raw. `esc()`'s own definition at :84-88 states the
rule — "Every catalogue-derived string goes through this before it reaches innerHTML" — and order
`3b37494e20db` fixed the sibling sinks in `shelfmark()` and `selectWorld`'s `cat`, arguing the fix
belongs "where the value enters the string, not at the three places it leaves".

**Latent today, verified**: across the 1,569 worlds in `data/NAVTREE.json` these four fields are
closed enums — landform 6 values, climate 6, condition 3, tech 4, none containing `& < > " '`.
The exposure is the next cosmology pass that widens any of them.

### Checked and clean
The `data.replace("<", "\\u003c")` guard, the `getBBox`-measured `resetView`, the collapsed-box
guard in `pointermove`, and the display truncations (`slice(0,24)`, `slice(0,22)`,
`slice(0,17)+"…"`) — every truncated label has the full string in the sibling `<title>` tooltip,
so nothing is unreachable.

---

## src/zfighters.py (504 lines) — read in full

The fifteen hand-built sheets, the presence-thesis reasoning and the gated atomic write are
sound. The `provenance`-missing fix for the carried Goku sheet is correct: verified against
`data/REFERENCE_ASSAYS_PRESENCE.json`, that sheet carries all eleven `A.WEIGHTS` axes with
`score`+`cited` and no `provenance`, and `assay.decimal`/`magnitude` are present, so both
`--full` and `value()` are safe on it.

### Z1 — `--full` truncates the worksheet it exists to print (MINOR, LOCAL)
`src/zfighters.py:481-482`. `--full`'s help is "print every worksheet line"; the line prints
`d["cited"][:60]`, no ellipsis, no count. **Reproduced**: 100 of the 154 worksheet citations in
`ROSTER` are longer than 60 characters; the worst (Vegeta/acumen, Piccolo/transgression,
Piccolo/acumen at 157 chars) lose 97 characters each. The cited evidence *is* the worksheet.

Same line of the same defect at `:459`, `epoch[:38]` in the ranking table: 5 of the 14 epochs are
cut (Vegeta 46, Gohan 44, Chiaotzu 43, Piccolo 42, Krillin 39), and the epoch is the thing the
module's header says makes each assay a measurement of a specified subject.

### Z2 — Goku can drop out of the ranking with nothing on stdout saying so (MINOR, LOCAL)
`src/zfighters.py:435-440`. `except Exception: silence.note("zfighters.py:goku")`. The comment
above it says the sheet is carried in "so the roster ranks whole"; if the read fails the table
still prints under the banner `THE Z FIGHTERS, BY MAGNITUDE`, missing the fighter the header
paragraph spends two sentences comparing Android 17 against, and the only trace is a silence-ledger
row. `data/Z_FIGHTERS.json` is then written without him and `pantheon.py` reads that.

### Checked and clean
The `_BAD_CHARS` self-inspection guard at :46-48 (paranoia, but it does test what it claims).
The atomic write and its rc=1 on denial are correct and are the shape the other modules should copy.

---

## src/prose_gate.py (371 lines) — READ IN FULL, NOTHING FOUND

All five layers check out. Specifically verified rather than assumed:

* `_AXIS_RE` (:308-310) matches `Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma`.
  I suspected this was checking the wrong axis vocabulary — the Custodial Assay's own axes are
  ruin/continuity/celerity/… — but `prompts/system_style.txt:140-142` defines The Instrument as
  "a standard six-axis instrument — Strength, Dexterity, Constitution, Intelligence, Wisdom,
  Charisma — scored 1 to 30". The regex matches the real vocabulary, and the leading-decoration
  class `[\s*_#>-]*` covers the `**Wisdom:**` and `**Wisdom**:` forms the comment names.
* `evidence_ok`'s `0.0 < floor <= 1.0` band closes the `floor=0` hole for real.
* `section_shortfall` charges both ghosts *and* extras into `required`, so neither an omitted nor
  an invented entry can reach `frac == 1.0`.
* `assert_block_complete`'s `missing[:6]` is a display shortening that declares its own truncation
  and names where the complete list lives. That is the remedy Hard Rule 0 prescribes, argued in
  place, and is not a finding.
* `cited_names_for` fails closed to `set()`, which makes every axis score unearned and refuses the
  block — the safe direction, as documented.

---

## src/catalogue_codex.py (335 lines) — read in full

The section-title collision report, the ambiguous-binding refusal, the gated record write, the
gated roll write and the rc plumbing are all correct and are the best-argued in this batch.

### C1 — the same collision the module refuses for sections is silently resolved for descriptions (MAJOR, RUN)
`src/catalogue_codex.py:138-146`. `load_register_index` builds `{norm(name): item}` with
`if key and key not in idx` — first wins, silently, no report. Every later item with the same
normalised name is dropped, and its description is the one attached to the codex element at
:220-226 and written into the record under `"attestation": "Transcribed"`.

**Reproduced against `reference/keystone_volumes/LOCAL_REGISTER.json`**: 14,576 items, 13,602
distinct `norm()` keys, **885 colliding keys and 974 items silently dropped** — and **678 of those
collision groups carry different `desc` text**. So for 678 element names the transcribed
description written into the corpus is decided by file order in LOCAL_REGISTER.

This is the module's own stated doctrine turned on itself. Forty lines below, for codex sections,
it says: "Attesting to a transcription from the wrong section is worse than not cataloguing the
source at all, and it is the one case where guessing is worse than doing nothing." The section
path reports its collisions uncapped and refuses ambiguous bindings; the register path does the
coin flip.

### Checked and clean
`slug`/`record_path` correctly delegate to `catalogue_aurora` (one implementation, uncapped).
`joined` at :274 is a display statistic only.

---

## src/thread_integrity.py (278 lines) — read in full

The DANGLING/PARTIALLY-DANGLING split, the both-directions fix at :163, and the uncapped detail
listings are all correct and well argued.

### T1 — the uncapped lists truncate the identifiers inside them (MINOR, LOCAL)
`src/thread_integrity.py:251, 258, 264, 274`. `{a[:24]:26s}` / `{b[:24]}` and `{a[:26]:28s}` /
`{b[:26]}`, sitting directly under a sixteen-line comment arguing that these lists must not be
truncated because "main() is the ONLY reporting surface this module has… anything not printed here
is not recorded anywhere by anybody". The rows are uncapped; the source names in them are not.
**Measured**: 50 of the 215 roll sources are longer than 24 characters and 39 are longer than 26.
No two currently collide in their first 24 characters, so nothing is *ambiguous* today — but a
truncated name cannot be pasted back into `catalog.py`, `corpus_db.py` or the roll, which is what
the reader does next.

### T2 — `ASYMMETRIC-LAWFUL` detail is collected and never printed (INFO, LOCAL)
`classify()` fills `detail["ASYMMETRIC-LAWFUL"]` with the excuse string at :188; `main()` itemises
DANGLING, PARTIALLY-DANGLING, RECIPROCAL and ASYMMETRIC-SUSPECT and never that one. It is the
only remaining class whose per-pair detail exists and is discarded, which is verbatim the defect
:239-245 describes for DANGLING ("counted… and nowhere else"). The excuse is the *evidence for
waiving a hole*, so it is the one that most wants reading. Unreachable today (every caller passes
`recorded=None`), hence INFO.

### Checked and clean
`total = sum(counts.values())` cannot divide by zero (the `if counts.get(k)` guard). The
propagation-unavailable fallback prints its own notice rather than failing silently.

---

## src/scope.py (204 lines) — read in full

### S1 — the Hard Rule 0 fix in `scope_for()` is inert for 89% of the corpus and can never run (MAJOR, RUN)
`src/scope.py:132-137`. `build()` seeds `out` from the existing `SCOPE.json` and then computes
`todo = {h … if h and h not in out and not F.is_wikipedia(h)}` — **membership by key**. Every host
already in the file is skipped for ever, and `main()` offers no `--rebuild`, `--force` or
`--only` to get past it.

`scope_for()` was recently repaired for two stacked truncations: `srlimit` 3 → 500 per query, and
the `titles[:8]` before `F.fetch` removed, with the comment "two stacked truncations feeding the
term-frequency count that `ceiling_for()` turns into the Magnitude ceiling for every entity in the
source". **The file on disk was built before that fix and cannot be rebuilt by any code path here.**

Measured on the live tree:

| | |
|---|---|
| `data/SCOPE.json` mtime | 2026-08-21 15:50 (the fix is later) |
| hosts keyed in the file | 155 (146 scored, 9 null) |
| non-Wikipedia hosts on the roll | 139 |
| of those, already keyed → skipped by `todo` | **124** |
| a fresh `--build` would probe | 15 |
| scored records with exactly 8 pages, i.e. sitting on the removed cap | **80 of 146** |
| page-count histogram | `{1:4, 2:4, 3:8, 4:13, 5:12, 6:15, 7:10, 8:80}` |

Nothing exceeds 8, which is the removed cap's fingerprint on every record. `magnitude.py:67,1542`
reads this file to clamp the anchor, so 124 sources' Magnitude ceilings are still being computed
from the truncated evidence the fix was written to end. This is a cap that survived its own repair
by hiding in the cache.

Remedy: a re-probe path. Either a `--rebuild`/`--host` flag that ignores the `h not in out`
membership test, or a version/`probe_version` stamp written into each record with `todo` selecting
anything stamped older than the current `scope_for` contract — the second is better, because it
makes the next truncation fix self-healing instead of needing this audit again.

### S2 — `--probe` truncates its own answer (MINOR, LOCAL)
`src/scope.py:187`: `print(json.dumps(scope_for(a.probe, verbose=True), indent=1)[:900])`. No
ellipsis, no count. Today's stored records all fit (largest 608 chars) **only because they were
built under the 8-page cap**; a post-fix probe returns up to 4 × 500 search hits filtered by size,
so the `pages` list — the provenance of the whole verdict — will be cut mid-string, silently, in
the one command that exists to inspect a scope answer.

### S3 — the write verdict is threaded back and then dropped (MINOR, LOCAL)
`src/scope.py:191-198`. `build()` was deliberately changed to return `ok` — its own comment: "so
its one caller can tell the difference" — and `main()` prints the difference and then `return 0`
on both branches. `sys.exit(main())` is already in place at :203, so this is a one-word fix, and
`catalogue_codex.py:315-331` states the doctrine ("THE VERDICTS REACH THE EXIT CODE").

### Checked and clean
The `best`-is-highest-clearing-the-floor loop, the removal of the sub-floor `argmax` fallback, and
`build()`'s refusal to cache a probe FAILURE as a verdict (while still caching a genuine empty
answer) are all correct.

---

## CANDIDATES DROPPED AFTER VERIFICATION

Recorded so the next sweep does not re-derive them.

1. **`prose_gate._AXIS_RE` checks the wrong axis vocabulary.** It does not — `prompts/system_style.txt:140-142`
   defines The Instrument as the six D&D-shaped axes the regex matches.
2. **`mutate.py`'s `[:120]` journal truncation loses survivor diffs.** Cannot fire: the longest
   line in any of the three mutation targets is 101 characters.
3. **`zfighters.py --full` crashes on the carried Goku sheet.** Already fixed; the sheet carries
   all eleven `A.WEIGHTS` axes and the `d.get("provenance", "")` guard is correct.
