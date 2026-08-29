# SWEEP 37 — BATCH 03 AUDIT

Modules read IN FULL (3,968 lines, every line):

| module | lines | read |
|---|---|---|
| `src/pipeline.py` | 2,440 | yes |
| `src/secondopinion.py` | 474 | yes |
| `src/backfill.py` | 329 | yes |
| `src/hosts.py` | 282 | yes |
| `src/recover_folder_records.py` | 231 | yes |
| `src/halo.py` | 212 | yes |

Nothing was run that does real work. `pipeline.py`, `backfill.py`, `hosts.py --discover` and
`recover_folder_records.py` were IMPORTED and individual functions exercised against temporary
copies only. No source file was edited.

---

## FINDINGS

### F1 — BLOCKING. `pipeline.write_record` silently discards every per-entry judgment on the no-drift path

**Where:** `src/pipeline.py`, `write_record`, the `else:` branch (the "NO DRIFT IS NOT NO CHANGE"
comment, ~line 758-767).

**What is wrong.** The drift branch copies the pipeline's per-entry judgment fields from the
in-memory record onto the disk entries before writing. The no-drift branch does not — it calls
`_merge_top_keys` (which by construction skips `entries`) and then sets `merged = disk`. So the
entries written back are the DISK entries, exactly as they were read, and every field the caller
just wrote is thrown away.

The branch is chosen by `_entry_digest`, which digests entry **names** only. `phase_entrypass`
never changes a name — it writes `category`, `scale_note`, `scale_note_rejected`, `magnitude`,
`topic`, `catalogued`. So for phase 2 the no-drift branch is the ORDINARY case, not the corner.

**Demonstrated** on a copy of a real record (`data/records/gears-of-war.json`, batch at
`start=340`, 20 genuinely unjudged entries):

```
landed: True
in-memory settled: 20 / 20
ON DISK settled after write: 0 / 20
disk entry keys: ['category','description','name','scale_note','type','wiki_page']
```

`write_record` returned **True**. `_landed` was never reached with a problem to report. The
judgment pass reported success and wrote nothing.

**Why it matters.**
* `phase_entrypass` then does `if landed and all(entry_settled(e) for e in batch)` against the
  IN-MEMORY batch, which is settled, so it appends the key to `done_keys`, increments
  `units_done`, and `update_handoff` publishes the progress to `handoff/RUN_STATUS.md`. The
  state file, the run log and the owner-facing status all record work that is not on disk.
* On the next run the batch is re-read from disk, `batch_settled` finds it unsettled and the
  batch is redone — one model call each, every pass, for ever. This is the unbounded-retry
  shape `entry_settled`'s own docstring says cost 66 batches once; it is now the default.
* **Live corroboration:** of the 4,559 keys in `state/PIPELINE_STATE.json`
  `done.entrypass`, **1,496 (33%) name a span that is NOT settled on disk** — 677 Marvel,
  195 DC, 151 all Final Fantasy, 36 Gears of War, 35 Dragon Ball Z. The grown-tail-batch case
  can only ever account for one batch per source, so it does not explain 677.

**Blast radius beyond phase 2** (all callers of `write_record`):
* `src/repass_bands.py:84` — writes `e["magnitude"]` / `e["scale_note"]` per entry. Its entire
  corrective effect is discarded, and it prints "APPLIED. N rewritten".
* `src/cleanup.py:217` — writes `catalogued`, `excluded`, `description`, `thin_description`
  per entry. See F2.
* `src/retry_synthesis.py:217` and `src/ingest_doc.py:395` write only top-level keys and are
  NOT affected (`_merge_top_keys` folds those correctly).
* `phase_synthesis` writes the top-level `synthesis` block and is NOT affected.

**Provenance of the regression.** The `else` branch used to be `merged = rec`. Run #36 changed
it to fold top-level keys onto `disk`, which fixed a real defect and introduced this one. The
comment's reasoning — *"The cast is equal by construction here, so folding onto `disk` keeps
every disk-authored key and costs nothing"* — is the error: the cast is equal by NAME, not by
CONTENT, and the entries are exactly what is being changed.

**Confidence: certain** (reproduced twice, once synthetically and once on a real record copy).

---

### F2 — MAJOR. The per-entry merge allowlist omits `excluded`, and copying `catalogued` without it re-creates the reverted-exclusion defect

**Where:** `src/pipeline.py`, `write_record` drift branch field tuple (~line 750) and
`write_record_catalogue` field tuple (~line 522). Both read:

```
("category", "scale_note", "scale_note_rejected", "magnitude", "topic", "catalogued")
```

**What is missing:** `excluded`, `topic_rejected`, `thin_description`, `description`.

**Why it matters.** `cleanup.py` strikes an entry by setting `catalogued = False` **and**
`excluded = "<reason>"`. On the drift path `write_record` copies `catalogued` and drops
`excluded`, producing an entry that is neither catalogued nor excluded — i.e. UNSETTLED — which
`phase_entrypass` then judges and sets `catalogued = True`. That is precisely the cycle
`batch_settled`'s docstring describes ("Measured 2026-08-24: 149 entries carried `excluded`, and
all 149 had already been flipped back to catalogued") and says has been closed. It has not.

`write_record_catalogue` has the same gap pointing the other way: it copies the disk's judgments
onto the fresh cast but not `excluded`, so every re-catalogue erases the exclusion reason.

**Live corroboration:** across `data/records/`, **111 entries carry `excluded`, and all 111 of
them also carry `catalogued: True`.** 111/111. `topic_rejected` — written by
`phase_entrypass` at the topic gate — appears **0 times in 282,822 entries**.

**Confidence: high** for the allowlist gap (read directly, and the 111/111 figure is measured).
The `topic_rejected: 0` figure is corroborating rather than conclusive on its own.

---

### F3 — MAJOR (OWNER question). `synthesis_blocks` never nominates a feat-less entry when any entry in the source has a mined feat

**Where:** `src/pipeline.py`, `synthesis_blocks`, the final expression:

```python
blocks = ([with_feats[i:i + 14] for i in range(0, len(with_feats), 14)]
          or [rest[i:i + 14] for i in range(0, len(rest), 14)])
```

`rest` is only reached when `with_feats` is EMPTY. One entry with a mined feat is enough to
exclude the entire rest of the cast from ceiling nomination.

**Demonstrated** against live records:

| record | entries | with mined feats | nominated |
|---|---|---|---|
| `tales-from-the-yawning-portal.json` | 54 | 8 | 8 |
| `eastern-astrology-bazi-jyotisha.json` | 55 | 4 | 4 |
| `kbp-unlikely-heroes.json` | 55 | 2 | 2 |
| `dms-guild-wayfinder-s-guide-to-eberron.json` | 53 | 0 | 53 |

**Why it matters, and why it is a QUESTION rather than a fix.** The comment block immediately
above this line records the owner's 2026-08-25 ruling that removed `rest[:14]`, and states the
premise explicitly: *"The owner ruled the second way: lead paragraphs CAN carry a ceiling
feat."* If that premise holds, then dropping 46 of 54 lead paragraphs because 8 siblings happen
to have a mined feat is the same act the ruling forbade — a ranked selection that decides, on
the entity's behalf, that everything past the cutoff does not exist — just expressed as an `or`
instead of a slice. If instead the intended rule is "a mined feat is strictly better evidence
and displaces lead paragraphs entirely", that is a defensible curatorial position but it
contradicts the ruling written directly above the code. Only the owner can say which.

The cheap alternative is `with_feats_blocks + rest_blocks` (feat-bearing first, so an
interrupted run still saw the best material), which is what the same comment prescribes for
`rest` on its own.

**Confidence: certain** on the behaviour; the ruling is the open question.

---

### F4 — MAJOR. `backfill.py --audit` truncates the thin-cast roster to 26

**Where:** `src/backfill.py`, `main`, the `--audit` branch:

```python
for x in rows[:26]:
    ...
if len(rows) > 26:
    print(f"  ... and {len(rows) - 26} more")
```

This is the exact shape run #33 removed from `pipeline.phase_write` (`refused[:5]`), and the
argument recorded there applies word for word: the count stays right the whole time, which is
what makes it comfortable, and the whole point of the line is to NAME which sources are thin.
`rows` is bounded by the roll (215), it is a diagnostic-only path, and `--all` already walks the
full list — so there is no cost to printing all of it.

**Confidence: certain** (read directly; no ambiguity).

---

### F5 — MINOR. The red-check for the run #36 merge fix cannot see F1

**Where:** `handoff/pipeline_merge_redcheck.py`, `ENTRIES = [{"name": "Alpha"}, {"name": "Beta"}]`.

All four arms and the control use entries that carry NO per-entry judgment fields, so the
round-trip can never observe that the no-drift branch writes the disk entries back unchanged.
The proof that certified the change is structurally unable to fail in the direction the change
broke. A fifth arm — judge an entry in memory, write, assert the judgment is on disk — would
have caught F1 the day it landed.

**Confidence: certain.**

---

### F6 — MINOR. `secondopinion.py` cites a line number that has drifted, and a finding that is no longer true

**Where:** `src/secondopinion.py` module docstring, the `vulture` entry:
*"Found `descending_ladder.py:129 from_m` and two others at 100% confidence."*

`src/descending_ladder.py:129` is now `def compton_confinement_energy(...)`. `from_m` is a
parameter of `shrink_report` at line 156, and it is **read** at lines 159-163 and 185-186 —
that module's own docstring records the fix ("`from_m` was accepted and then never mentioned
again"). So both halves of the citation are stale: the line has moved, and the dead-code finding
it advertises as vulture's proof of value has since been repaired. This project's idiom is to
cite by symbol.

**Confidence: certain** (both lines read).

---

### F7 — MINOR. `pipeline.main --phase` mishandles every out-of-range value, in three different ways

**Where:** `src/pipeline.py`, `main`, `phases = [args.phase] if args.phase else ...` and the
`if fn is None:` log line.

Measured:

| invocation | result |
|---|---|
| `--phase 9` | uncaught `IndexError` on `PHASES[ph-1]` in the "not implemented yet" log line — a traceback, not the clean stop the message promises |
| `--phase 0` | `0` is falsy, so the flag is silently IGNORED and the runner does a full resume run instead |
| `--phase -1` | logs *"phase -1 (shelve) is not implemented yet"* — names the wrong phase |

Operator-facing only, but `--phase N` is the documented recovery action the
pointer-past-end-with-open-phases path tells a person to take.

**Confidence: certain** (all three reproduced by import).

---

### F8 — MINOR. `recover_folder_records` reports a mapped-but-empty source as "not in FOLDER_SOURCE_MAP"

**Where:** `src/recover_folder_records.py`, `main`: `mapped = source_map.get(name)` then
`if not mapped: skipped_no_map.append(name)`. An empty LIST is falsy, so a source that IS in the
map with an empty mapping is reported under

> `not in FOLDER_SOURCE_MAP (web-mode sources -- need real research, no local data exists)`

`skipped_no_items` ("mapped, but the register holds no items for them") exists for exactly this
case and can never fire for it.

**Live:** of the 6 sources with `entry_count == 0`, two — `Lost Mines of Phandelver` and
`the Witch Tradition` — are present in the map with `[]` and are mislabelled. The distinction
matters because the two buckets prescribe different remedies (one needs research, the other
needs the register or the mapping fixed).

**Confidence: certain** (measured against the live map and roll).

---

### F9 — MINOR (OWNER question). `synthesis_prompt` truncates each entity's mined-feat list to 3

**Where:** `src/pipeline.py`, `synthesis_prompt`:
`d = " | ".join(re.sub(r"\s+", " ", x)[:150] for x in fl[:3])[:420]`

`fl` is the entity's mined feat list — an evidence list, unranked, cut to the first three. Also
`[:150]` per feat and `[:420]` overall. This is prompt budgeting rather than a roster cap, and
the surrounding code otherwise defends Hard Rule 0 carefully, so it is put to the owner rather
than fixed.

**Measured impact is small:** in a 4,001-file sample of `data/feats/`, 170 caches hold at least
one feat and **7** hold more than three. The tail is real but thin.

**Confidence: certain** on the code; the ruling is the open question.

---

## CHECKED AND HEALTHY

Recorded so the next run knows these were genuinely read, not skipped.

**`src/pipeline.py`**
* `save_state`, `land_json`, `_landed`, `write_record`, `write_record_catalogue`,
  `update_handoff` and `halo`-style writers all gate on `silence.replace_retry` /
  `silence.write_json` and report a denial through `log` + `silence.note`. No hand-rolled
  `open(path + '.tmp')` + `os.replace` survives — `_tmp_for` carries pid AND thread at every
  site, including the `update_handoff` one gated in run #38.
* `gate_done` is called by phases 3-8 and its verdict drives `main`'s `stalled` pointer; the
  pointer no longer advances past a phase that did not report completion. Verified by reading
  the loop, not by the comment.
* `_chain_landed` asks the DISK, comparing against a json round-trip of the written document —
  correct handling of the tuple/list asymmetry it documents.
* `clean_band` is a `fullmatch` (a decimal cannot be laundered into a band); `ceiling_band` is
  deliberately laxer and can only ever LOWER a band. The asymmetry is real and correct.
* `valid_scale_note` is a genuine conjunction (act ∧ object ∧ not-patient ∧ not-reputation),
  not the OR-of-three `_SCALE_EVIDENCE` shape; `_SCALE_PATTERNS` / `_SCALE_EVIDENCE` are indeed
  unreferenced elsewhere in `src/` and are labelled as the rejected approach.
* `entry_settled` / `batch_settled` are single-spelling predicates used by both the resume gate
  and the write-completion gate. Correct — the loss in F1 is upstream of them.
* `_pool_answer_usable` checks schema-`required` presence AND the caller predicate; the
  `_judged_something` accept for entrypass really can return False.
* `phases_never_closed` + the `if not phases:` branch distinguish "finished" from "pointer
  walked past open work" and exit 3 on the second. A real check that can fail.
* `IMPLEMENTED` is derived from `PHASES`, so all 8 phases dispatch; verified by import.
* `escalation` import failure raises `SystemExit` rather than passing — fail-closed, first
  statement in `main`.

**`src/secondopinion.py`**
* Every `NOT_FILED` code (`E402`, `RUF100`, `PLW1510`, `B007`, `RUF059`, `PLW0603`, `PLW2901`,
  `B008`) falls inside `RUFF_RULES = "E,F,B,BLE,S110,S112,PLE,PLW,RUF,SIM"`, so no waiver is
  unreachable — the property the comment claims. `BLE001`/`S110`/`S112`/`SIM115` are NOT waived.
* The returncode guards match the documented exit codes (ruff 0/1, vulture 0/1/3 plus the
  nonzero-but-nothing-parsed case, detect-secrets 0), and an installed-but-failing tool returns
  `TOOL ERROR`, which `missing()` treats as not-RAN. `ran_clean` requires status RAN on all
  three. `drill.py:5453` and `verify_math._b4_secondopinion_checks` both exercise this.
* The module never escalates automatically and never files orders unless `--file-orders` is
  passed; nothing in `src/` or the schedulers invokes it that way. Consistent with its stated
  fail-open, JANITOR-level posture — noted, not filed.

**`src/backfill.py`**
* `roster()` has no live cap: `backfill_source` calls `roster(host)` with `limit=None`, the
  subcategory walk is unconditional (the `< 40` gate is gone), and a transport failure raises
  `RosterIncomplete` rather than returning a short roster.
* The `sizes` sort key `(t in sizes, -sizes.get(t, 0))` does what its comment says: an
  unmeasured title sorts BEFORE measured ones. Verified by reading the key, not the prose.
* `(d or {}).get("query", {}).get("pages", [])` iterating `pages` as a list is CORRECT here —
  `feats.api` sets `formatversion: "2"` (feats.py:344), under which `query.pages` is a list of
  objects. Not a dict-iteration bug.
* `write_record_catalogue` (not `write_record`) is used and its verdict is gated; the
  write-denied return path reports `added: 0` and `entries_now` minus the un-landed appends.

**`src/hosts.py`**
* The three-state `add()` (True / False / None) edited today is correct and correctly consumed:
  `discover` does `if landed: added += 1` / `elif landed is None: lost.append(...)`, so a
  duplicate (`False`) and a denied write (`None`) are distinguished, and both being falsy keeps
  naive success counters honest. The `lost` list is printed to stderr AND `silence.note`d.
* The `per_source=24` cap on `HC.candidates` — the one place in this module that looks like a
  Hard Rule 0 violation — was checked empirically across the whole live roll: **0 sources have
  a grounded block exceeding 24**, and `en.wikipedia.org` (the last grounded entry) falls
  outside the cut for **0** of the 72 sources with more than 24 candidates. `candidates` returns
  `grounded + spec`, so the bound really does land in the speculative tail today. The claim is
  true as measured, but it is a property of the current roll rather than of the code — if a
  source name ever generates enough token/neighbour candidates, the cut would reach grounded
  hosts. Recorded, not filed.

**`src/recover_folder_records.py`** (edited today)
* Verified `recover_folder_records.slug is catalogue_aurora.slug` at runtime, and that the
  79-character `Who Framed Roger Rabbit (incl. ...)` name now slugs untruncated. `record_path`
  is used instead of a raw join, so a record written under the old 60-char cap is still found
  and correctly counted as populated. The change looks right.
* `FOLDER_SOURCE_MAP.json` is uniformly `[[name, count], ...]` (60 entries, every value a
  2-list), so the `for register_source, _declared_count in mapped` unpack is safe.
* The discarded `_declared_count` costs nothing today: declared vs actual register item counts
  agree for **every one of the 60 mapped sources, 0 mismatches**. Worth a cheap assertion some
  day; not filed.
* Both writes (`record`, then `ROLL`) are gated on `silence.write_json` and the roll row is only
  mutated after the record write lands. `already` treats an unreadable record as populated —
  the recoverable direction.

**`src/halo.py`**
* All three roster entities carry exactly the 11 axes in `assay.WEIGHTS` (no missing, no extra),
  so `main --full`'s `rec["axes"][ax]` cannot `KeyError`. `compute()` runs clean:
  Precursors 𝔄 M6.84 ± 0.15, Gravemind 𝔄 M6.84 ± 0.15, Ur-Didact 𝔄 M4.74 ± 0.15, each at its
  declared anchor.
* Per-axis provenance is genuinely per-axis (`wiki` vs `canon` both appear, 33 lines across
  3 entities), not the blanket `[wiki]` the docstring says it replaced.
* The write is gated: a denied `write_json` prints a loud WRITE DENIED naming the file as the
  previous run's and returns rc=1.
* `d["cited"][:54]` in the `--full` display truncates the citation without an ellipsis. Display
  only; the untruncated text is in `HALO_ASSAYS.json`. Noted, not filed.

---

## ORDERS FILED

| id | code | handler | severity | finding |
|---|---|---|---|---|
| `9ef51c36acea` | PIPELINE_WRITE_RECORD_NODRIFT_DISCARDS_JUDGMENTS | RUN | BLOCKING | F1 |
| `4866dfb2d9fc` | PIPELINE_MERGE_ALLOWLIST_OMITS_EXCLUDED | RUN | MAJOR | F2 |
| `5c8a7bc883e7` | PIPELINE_SYNTHESIS_BLOCKS_OR_EXCLUDES_FEATLESS_CAST | OWNER | MAJOR | F3 |
| `03c0fe609e89` | BACKFILL_AUDIT_TRUNCATES_ROSTER_TO_26 | LOCAL | MAJOR | F4 |
| `f3536eed6ce0` | REDCHECK_PIPELINE_MERGE_CANNOT_SEE_ENTRY_LOSS | RUN | MINOR | F5 |
| `2928a0f9c314` | SECONDOPINION_DOCSTRING_CITES_DRIFTED_LINE | LOCAL | MINOR | F6 |
| `4a79b0e8a375` | PIPELINE_PHASE_ARG_OUT_OF_RANGE | LOCAL | MINOR | F7 |
| `37d3d588847a` | RECOVER_FOLDER_EMPTY_MAPPING_MISREPORTED | LOCAL | MINOR | F8 |
| `f2b06f8c9476` | PIPELINE_SYNTHESIS_PROMPT_FEAT_LIST_CAP | OWNER | MINOR | F9 |

## COVERAGE

Recorded via `sweep_plan.record('run37', ['pipeline.py','secondopinion.py','backfill.py',
'hosts.py','recover_folder_records.py','halo.py'], batch=3)` — all six now carry `run37`.

**F1 is BLOCKING and should be worked before the next entrypass pass.** Every phase-2 model
call made while it stands is spent on a write that does not land, and the state file plus
`handoff/RUN_STATUS.md` report the work as done.
