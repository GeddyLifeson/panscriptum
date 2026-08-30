# SWEEP 38 — AUDIT, batch 14

Agent: `sweep38-batch14`. Run: `run38`. 8 modules, 4,468 lines, all read in full.
Reproductions were run from the agent's own scratch directory
(`.../scratchpad/sweep38/batch14/`); nothing under `src/` or `data/` was modified.

Modules: `hostcheck.py`, `workorders.py`, `catalogue_web.py`, `ledger_guard.py`,
`address.py`, `sweep.py`, `cleanup.py`, `chord_field.py`.

---

## src/workorders.py (941 lines) — read in full

### FINDING (MAJOR, RUN) — a corrupt queue file is silently rewritten as an EMPTY one

`_load()` (`:245-262`) answers a `json.JSONDecodeError` with `silence.note(...)` and `d = {}`.
`_mutate()` (`:265-311`) then applies the caller's change to that empty dict and lands it under a
CAS whose digest **matches** — `silence._digest_or_unreadable` digests bytes, and a corrupt file
reads perfectly well as bytes. So the compare-and-swap sees no change and the write succeeds.

Reproduced (scratch copy of the module with `OPEN_FILE` repointed):

```
queue on disk holds: 3 orders
after truncation, json.load raises: JSONDecodeError
file_order returned: an order
queue on disk now holds: 1 order(s): ['NEW_FINDING']
```

Three filed orders gone, `file_order` reporting success. This is the exact treatment
`hostcheck._land_hosts` refuses to give WIKI_HOSTS.json ("NEVER heal this one by starting
empty"), applied to the file that holds every finding in the project. Detector-owned codes re-file
on the next sweep; **agent-filed sweep findings do not** — they are written once and are not
re-derivable. The same fail-open reaches the read path: `open_orders()`/`for_ladder()` on a corrupt
file make `main()` print *"no open work orders — the nets found nothing outstanding"*, which is
the exact sentence the module's own docstring (`:97-107`) was written against.

### FINDING (MINOR, LOCAL) — the CAS temp name carries pid + attempt, not thread

`:293` — `tmp = "%s.%d.%d.tmp" % (OPEN_FILE, os.getpid(), a)`. Two THREADS of one process both use
attempt 0 and open the same scratch file; the second truncates the first and the first's
`os.replace` can land a partial file. `escalation.escalate()` calls `file_order` (`escalation.py:234,
497`) and escalation happens inside threaded mining passes. This is the shared-scratch-file hazard
`silence.write_json` exists to make unavailable, and the shape `hostcheck._land_hosts` (pid +
`threading.get_ident()`) and `catalogue_web.save_roll` were both migrated onto. It is also the most
likely way to *produce* the corrupt file the finding above then empties.

### FINDING (MINOR, LOCAL) — the paper-trail append failure is swallowed

`resolve()` `:428-433`. The order has already been deleted from the open file by the time the
append runs; if the append raises, the only record is a `silence.note` counter, and `resolve()`
returns the record as though the closure were complete. The closure then exists nowhere. This
module's own `_detector()` comment (`:526-535`) argues at length that a `silence.note` is not a
report.

### Read and judged correct
`battery_faults` (pure, fail-closed on every "cannot tell" arm, including the ungraded-rc and
`estate_faults is None` arms); `order_id` content addressing; the uncapped `what`/`where`/
`evidence`/`resolution` fields; `_supersede_binding_suspect`; the recovery-close loops in sections
3, 3b and 6; `_fire`; the `landed`-before-`rec is None` ordering in `resolve`; the
`[f for f in filed if f]` at `:898`. The `[:70]` in `main()` is a console render at its own call
site, which is where the module says a cap belongs.

---

## src/catalogue_web.py (585 lines) — read in full

### FINDING (MAJOR, RUN) — every entry in a class is typed by the FIRST category discovered

`:410` — `"type": _singular(cats[0]) if cats else _singular(canon.split(" (")[0])`.

The discovery loop at `:342-344` accumulates titles from **all** of a canonical class's
categories into one list and keeps no title→category mapping, so the stored `type` is whichever
category `wiki_source.find_categories` happened to return first. That order is the hardcoded
`CATEGORY_PROBES` guess list followed by discovery (`wiki_source.py:456-476`) — nothing makes
`cats[0]` the primary or the largest.

Measured over the 156 `mode: "web"` records now on disk:

| canonical class | stored `type` | entries |
|---|---|---|
| Events | `Total War: Warhammer` | 690 |
| Media | `Ability` | 3,521 |
| Vessels & Things | `Character` | 1,696 |
| Places & Locations | `Character` | 620 |
| Factions & Organizations | `Character` | 699 |

Worked example, `data/records/warhammer-fantasy.json`, provenance `src/catalogue_web.py`:
entry **Lizardmen**, category `Events (major storyline events...)`, `type: "Total War: Warhammer"`
— a video game's name stored as an entity type, for 690 entries at once.

It is not a cosmetic field. `corpus_db.py:236` indexes it, and `manifest_builder.py:316` puts the
whole entry dict into the model prompt while `prompts/system_style.txt:109` instructs the model to
"pick the closest fit to the entry's type" — so a wrong type reaches finished prose.

Remedy: record the category each title came from while the discovery loop runs
(`first_cat.setdefault(title, c)`) and type each entry from its own category, falling back to the
canonical class name when a title has no recorded category.

### Read and judged correct
`MAX_PER_SOURCE`/`MAX_PER_CATEGORY`/`CATEGORY_SCAN_DEPTH` are all `None` with the `SystemExit`
guard at `:369` still live; `rank_by_size(..., top=None)` everywhere; the imported (not re-written)
`slug`/`record_path`; `_singular`; the `no_text` and `failed_cats` accounting and the provenance
sentences they add; both write gates in `_one` (`write_record_catalogue` then `save_roll`) and the
distinct message each refusal gets; the default-arg freeze on both progress lambdas.
`catalogue_composite`'s hardcoded `"Deity"`/Persons category is correct — `COMPOSITE_SOURCES`
holds exactly one source and it is the pantheons one.

---

## src/hostcheck.py (1,263 lines) — read in full

### FINDING (INFO, LOCAL) — the control sample's stride is computed on the pre-dedup list

`:560` — `foreign = sorted(set(foreign))[::max(1, len(foreign) // sample)][:sample]`. The RHS
`len(foreign)` is the list **with duplicates**; the stride is then applied to the deduplicated
list, so the control is smaller than `sample` whenever rosters share names. Measured on the live
corpus (193 sources, `exclude='2112 (Rush)'`): 561 raw names, 538 distinct, stride 14 → **39**
control names where the deduped stride gives 40. Live effect is one name today; on a corpus with
heavier name reuse it scales (a synthetic 150/63 case gives 21 names instead of 40). The function's
own comment says the control is the whole point, so the fix is worth the one character:
compute the stride from the deduplicated list.

### QUESTION (not a finding) — `HOST_UNFIT.json` is written even when the host merge was refused

`sweep()` `:808-832`. `_land_hosts(fixed, ...)` can return `(False, why)` — nothing was removed
from WIKI_HOSTS.json — and `_land(UNFIT, unfit)` on the next line writes the rejections anyway.
Two readings: (a) deliberate, the rejection is a finding and worth keeping on file whatever the
host map did; (b) a mismatch, since a source can then be listed as rejected while still carrying
the host it was rejected from. Nothing else in `src/` reads `HOST_UNFIT.json`, so the stakes are a
human reader's, not a pipeline's.

### Read and judged correct
`_land`/`_land_hosts` (CAS, per-writer temp name, unreadable-host-map refusal, contended-write
report); `probe`'s rate=None-on-error; `null_rate`'s None-not-zero and its deliberate
non-caching of failures; the full key `(host, exclude, sample, tuple(foreign))`; `score`'s
propagation of `base is None` into an UNREACHABLE verdict rather than a lift; `candidates`' split
`grounded + spec` with no slice; the lift-only first tuple slot in both `sweep(--repair)` and
`adopt`; `purge`'s gating of the cache deletion on the record write's verdict; `roster_audit`'s
`judgeable` flag, which IS consumed (`standards.py:1163`). `PROBE`, `sample=12` and the `[:3]`
token cuts are measurement parameters on a probe, not truncations of a stored or reported
universe. `GOOD` is unused by code, exactly as the module docstring `:33-38` now says.

---

## src/ledger_guard.py (475 lines) — read in full

### FINDING (MINOR, LOCAL) — the sealed snapshot uses a fixed temp name and swallows failure

`seal()` `:228-233` writes `SNAPSHOT_DIR/<name>.tmp` — one shared scratch path per ledger — and
wraps the whole write in `except Exception: pass`, with no `silence.note`. `publish.push()` is the
caller (via `assert_intact`), and this project runs a `publish.py --loop` daemon alongside manual
pushes, so two sealers meeting here is not exotic.

The comment at `:217-221` reasons that a stale or missing snapshot can only report a truncation
late, never wave one through. That is true of *stale*; it is not true of *torn*. If writer B
truncates the shared `.tmp` while writer A is between write and `os.replace`, A lands a **prefix**
of HANDOFF.md as the sealed copy — and `_one_insertion(old=prefix, new=live)` returns True for any
live file that still begins with that prefix, so `check_since_snapshot` answers "history
preserved" for exactly the truncate-then-regrow attack it was added (2026-08-27, run #36) to
catch. The guard is weakened in proportion to the tear, silently.

Remedy: a per-writer temp name (pid + `threading.get_ident()`, as `hostcheck._land_hosts` and
`silence.write_json` both do) and `silence.note("ledger_guard.py:snapshot")` instead of `pass`.
Keep the not-failing-the-seal behaviour — that part is right.

### Read and judged correct
`_one_insertion` (prefix+suffix cover, which accepts this project's newest-on-top append and still
refuses reorderings and mid-file deletions); `check_structure`'s find-order-derived section spans;
`read_chain`'s FileNotFoundError-only swallow; `verify_chain`'s `is not None` byte test;
`assert_intact`'s gate on `seal() is None`; `main()` running all three mechanisms and reporting
them separately. Ran the CLI: STRUCTURE ok, 624 chain links verify, HANDOFF.md history preserved.

Cosmetic only, not filed: `verify_chain` `:355` formats `"link %d does not follow link %d" % (i,
i - 1)`, which reads "link -1" if the first link's `prev` is ever wrong.

---

## src/sweep.py (323 lines) — read in full

### FINDING (MINOR, LOCAL) — two report tails are cut with no "+N more"

`report()` `:289` `gap.most_common(10)` and `:296` `bysrc.most_common(8)`. Measured against the
live `data/CHARACTER_SWEEP.json` (141,428 rows): BIGGEST GAPS currently holds 6 sources, so it
prints all of them — but REACHED BUT SILENT holds **168 sources and prints 8**, and the count line
above it reports characters, not sources, so 160 sources are invisible with nothing saying they
exist. That list is precisely the actionable one ("read, yet no axis found anything"). Remedy:
print all rows, or state the tail — `... and N more sources (M characters)` — in both places.
`--top` on DEEPEST EVIDENCE is an explicit "show me the best N" and is left alone.

### FINDING (INFO, LOCAL) — `rosetta_index`'s docstring is one field behind the code

`:113` says `{normalised name: (scale title, value, rank-within-scale)}`; the code stores a
4-tuple `(title, val, rank, sc["n"])` and `sweep()` `:187` reads `hit[3]` as `"of"`. The comment
directly under it (`:123-126`) depends on that fourth slot to explain the finer-scale-wins rule.

### Read and judged correct
The control-character guard; `load()`'s FileNotFoundError exemption with its argument written out;
the `cachekey.load` verified read with `on_corrupt`; `nested_run` (asked of the data, correct at
the run boundaries); the funnel/loose-population split and the crossover counts in both
directions; `main()`'s gate on `silence.write_json` and rc=1 on refusal.

---

## src/cleanup.py (272 lines) — read in full

### FINDING (MINOR, LOCAL) — a markup rule strips meaningful question marks from descriptions

`_MARKUP` entry 5, `:69` — `(re.compile(r"\s*\?\s*(?=\))"), "")`, "stray ? before a close paren".
It exists for Japanese ruby annotations (`(フランス, Furansu ? )`), but it is unconditional, so it
also fires on ordinary English parentheticals that end in a question.

Measured over all 282,822 catalogued descriptions in `data/records/`: 6,073 matches, of which
**43 are pure-ASCII** — no ruby annotation anywhere near them. Examples:

```
... LaForge and Ensign Sonya Gomez (Q Who?)          ->  (Q Who)      [a real episode title]
... an intense magnetic shock (a murder attempted?)  ->  (a murder attempted)
... (or manifestation of mental illness?)            ->  (... illness)
```

The damage has not happened yet — the 43 are still intact, so no `--apply` run has reached them —
which makes this cheap to prevent and not to repair. The module's own docstring says the
description "is the evidence every later volume quotes from". Remedy: fire the rule only when the
enclosing parenthetical contains a non-ASCII character (the case it was written for), or fold it
into the ruby pattern above it.

### Read and judged correct
The mangled-escape roster guard, including the `_SETTING_META` and `_MARKUP` entries added after
the `("_SETTING_META", None)` no-op; `_NAV`'s deliberately different `$`/`\b` halves (the note is
past tense and the sweep-33 reading of it was wrong); `clean_ceiling`'s prefix-not-substring
strategy and its "unresolved" refusal to guess; the `thin_description` first-time-only guard with
`changed = True` inside it; the gate on `PL.write_record` and the `unwritten` list, which is the
one list in the report that names its own tail. The `[:5]`/`[:6]`/`[:4]` report samples all sit
directly under a printed full count, so nothing is hidden.

---

## src/address.py (399 lines) — read in full

### FINDING (MINOR, LOCAL) — `slugify` still ends in `[:60]`

`:230` — `return "".join(...)[:60]`. This is the same cap, on the same kind of value (a stored path
component), that `catalogue_web.py:68-95` spends thirty lines describing after it orphaned
`who-framed-roger-rabbit-incl-all-content-from-its-associated.json` from its roll row.

Latent today, and verified so rather than assumed: `slugify` has exactly two call sites
(`chapter_slug`'s fallback for a label not in `CHAPTER_SLUGS`, and `manifest_builder.py:247` on
`roll_entry["category"]`), and all 17 category values on the live roll slugify to 5-29 characters.
Removing the cap changes no current output; leaving it leaves a truncating filename-maker in the
addressing module for the next longer label to find.

### Read and judged correct
`spine_code_for`'s four tiers and the three separate false-match repairs layered into them
(letter-equality first, then word-boundary containment with most-specific-wins and the
opens-or-closes rule for single-token index entries, then the token-overlap fallback with its
`overlap < 2 and target_tokens != name_tokens` guard) — each documented case re-checked against
the code; `UNASSIGNED` as the safe answer; `tier_for`/`tier_rank`/`promote` (promotion-only);
`recipe_hash` including `content_hash`; `placeholder_shelfmark`; the `str | None` annotations.

---

## src/chord_field.py (210 lines) — read in full

Read in full, nothing found. Formulas check out: `landauer_floor` = bits·k·T·ln2;
`recoil_momentum` = E/c (and the A2 prose's "1e20 J → ~3e11 kg·m/s" is right);
`critical_power_self_focus` = 3.77·λ²/(8π·n₀·n₂), the standard Kerr expression, with air defaults.
`total_beta()` = 328 over the six adjudications, matching the 64/96/8/0/128/32 that
`derivation.py:138` and `rigor.py:813` both quote. The module has no importer anywhere in `src/`,
which is a known and deliberate state — `liveness.py:208` and `drill.py:69` both name
`chord_field` in their standalone-module lists — so its callerless functions are not dead code
findings.

---

## Coverage

All 8 modules read in full and recorded to `sweep_plan` under `run38`, batch 14.
