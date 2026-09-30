# sweep68 batch16 audit (run68, 2026-09-30)

## Scope (each module read in full with the Read tool, in chunks, sequentially)

| module | lines | chunks read |
|---|---|---|
| src/read.py | 1723 | 1-450, 450-870, 868-1287, 1287-1723 |
| src/local_agent.py | 1689 | 1-420, 420-840, 840-1259, 1259-1689 |
| src/threads.py | 1074 | 1-400, 400-738, 738-1074 |
| src/secondopinion.py | 719 | 1-370, 370-719 |
| src/handbuilt.py | 550 | whole |
| src/citecheck.py | 458 | whole |
| src/profile.py | 367 | whole |
| src/resonance.py | 302 | whole |
| src/lognames.py | 74 | whole |

Total 6,956 lines. Read-only on the project. Scratch scripts are in `%TEMP%\aud68_16` (`hb1/hb2/rd1/la1/th1/th2/pf1/pf2/cc1.py`). Every reproduction patched `silence.note` and `silence.write_json` (or ran pure functions) and redirected cache paths to a temp dir. No daemon, phase, generate, publish, mutate, verify_math or drill was run, no model was called, and no subagent was spawned. Nothing under `state/`, `data/`, `src/`, `output/`, `prompts/` or `config.yaml` was written.

## Prior-audit cross-check (sweep67)

- **read.py / local_agent.py (sweep67 batch16).**
  - F6 (qcache prune keeps superseded-rule keys) is **fixed**. `read.py:1365` is now `k.endswith(_QK + _QROW_RULE)`. Measured on the live `state/read_queue_index.json`: 275,442 keys, 275,442 of them ending in the current rule. The "61 MB" in the comment at :1358 is still stale (the file is 80 MB).
  - F7 (stale line-number comments) is **fixed** for the read.py sites (now cited by symbol).
  - local_agent F2 (`offset="abc"`) is **fixed** for ValueError (:1582), but the same class survives, see F4 below.
  - local_agent F3 (`find_symbol` skips unparseable files) is **fixed** (`skipped_files`, `unique` False).
  - Open questions 1 (`fallback_model` caches the failed-probe fallback), 2 (`--loop` ignores `ok`), 7 (text-mode rewrite) and 8 (`why` cut to 200 in the returned dict): all **still stand**, unchanged.
- **threads.py (sweep67 batch04).** F9 (stale T4 text) is fixed. F8 (`annex_codes`/`law_codes` wrong shape) is fixed for the top-level and row shapes, but a wrong-shaped `declared` still raises, see F8 below. Q3 (`verify()` does not pin T2 edges to class T2 or `from`) and Q4 (LAWS.json re-parsed per magnitude entry) **still stand**.
- **handbuilt.py (sweep67 batch04).** F10 (superlatives in shipped `cited` text): the Getter Emperor line now says "Tied for", and Rune King's is a true unique maximum (checked). The Undertaker suasion line still says "THE HIGHEST-EARNED SCORE IN THIS LIBRARY" for 9.9, a tie with his own continuity 9.9. Partly stands, LOW.
- **profile.py (sweep67 batch09).** F7 (unknown genre/register answered with a plausible value) is **fixed**. `encode` notes both, and `decode` refuses (:198-200).
- **secondopinion.py (sweep67 batch12).** F9 (silence count included non-silent rows) is **fixed** (:478-479). The `text=True` encoding finding is fixed (`encoding="utf-8"` at :291/:324/:386). Q3 (only 4 sites per rule in a work order) stands as a labelled display cap ("+N more").
- **resonance.py (sweep67 batch12).** F14 (absolute tolerance) is **fixed**: `_tol = tol * max|f|` (:171). Re-checked the Gauss-Seidel sweep, the gauge fix, the non-convergence path and the no-evidence branches. Still no production caller, as the module says.
- **citecheck.py, lognames.py.** No prior findings.

## Findings

### F1. read.py:978 with :984 a malformed pool answer is cached forever and then crashes every later read of that entity (VERIFIED, MEDIUM)
`_chunk_put(host, ch, name, (got or {}).get("feats", []))` stores whatever `feats` value the model returned. The pool answer only has to pass `P._pool_answer_usable`, which checks the key `feats` is present and never its type or its items. The loop at :984 then does `for f in (got or {}).get("feats", [])` with `f.get(...)`.

Failure: a cloud model returns `{"feats": null}`, `{"feats": "abc"}` or `{"feats": ["a sentence"]}` (schema is a request there, not a constraint, per cascade_bridge's own docstring). The bad shape is written to `data/chunkfeats/`. `read_entity` raises, `work()` counts the entity as ERRORED. On every later pass `_chunk_get` serves the same cached shape and it raises again. The entity is never read and never cached, and no model call is ever made for that chunk again.

Repro (`rd1.py`, temp CHUNK_CACHE, `_ask` stubbed):
```
feats:null attempt 1 -> RAISED TypeError 'NoneType' object is not iterable ; model calls so far 1
feats:null attempt 2 -> RAISED TypeError ... ; model calls so far 1     (served from cache)
feats:list-of-strings attempt 1/2 -> RAISED AttributeError 'str' object has no attribute 'get'
```
Fix: validate `isinstance(feats, list)` and `all(isinstance(f, dict))` before `_chunk_put`, and have `_chunk_get` treat a malformed cached body as a miss (delete and re-ask). The error is loud (ERRORED counter, silence note), but the block is permanent and self-reinforcing.

### F2. threads.py:530-557 `survey()`/`build()` with a torn record yields a short graph that `main()` writes (VERIFIED, MEDIUM)
`survey(None)` reads `weave_index.load_records()`, which skips an unreadable record and sets `LAST_UNREADABLE`. `weave_index.main` refuses to write on a non-empty `LAST_UNREADABLE` (:788). `threads.py` never reads it (grep: the name appears nowhere in threads.py). A source whose record is momentarily unparseable is then absent from `graph["sources"]`. It is not in `unaddressed` either, so nothing names it. `verify()` passes because it only checks what is present. `step4_enabled: true` is live in config.yaml, so `main()` proceeds to `silence.write_json(OUT, graph)`.

Repro (`th1.py`, `load_records` patched to omit one source and `LAST_UNREADABLE` set): `build()` returned 209 sources of 210, the victim was neither present nor listed as unaddressed, `verify()` returned `[]`.

Consequence: a THREADS.json missing a whole source lands. `threads_for` later refuses that source ("no such source in this graph"), so downstream fails loud, but the artifact itself is short with no record of why. The only guard is the join-key strictness, which fires only if the missing source happens to be an ANNEX_JOIN key. Fix: in `main()` (or `build` when `records is None`) refuse when `weave_index.LAST_UNREADABLE` is non-empty, the way weave_index does.

### F3. handbuilt.py:173, 210, 322, 360, 391 (and the header :9-41) `why_missed` text is now false for five of nine sheets, and it ships in the data (VERIFIED, MEDIUM)
`compute()` writes `"why_the_machine_missed_it": rec["why_missed"]` into `data/HANDBUILT_ASSAYS.json`, and the report prints it as "MISSED BECAUSE". Checked against `data/records/`:
- Mister Mxyzptlk: "never catalogued (DC's roster is 377 entries)". `dc.json` now has 55,560 entries and holds `Mister Mxyzptlk (Earth-One)` as a Persons/Character entry.
- Zalama: "not catalogued". `dragon-ball-z.json` has `Zalama`, Persons/Character.
- Molecule Man: "not catalogued under either name". `marvel.json` has `Owen Reece (Earth-616)`, Persons/Character (the page the sheet itself names).
- The Black Winter: "never catalogued". `marvel.json` has `Black Winter (Sixth Cosmos) (Multiverse)`, category Powers, type Character.
- Getter Emperor: "catalogued as Media, not as a Person". It is now `Getter Emperor (Manga)` under Vessels & Things (the header says "Media"). Still not Persons, so the "invisible to every assay stage" claim needs re-checking, but the stated category is wrong.

The Undertaker claim (158 country entries in the wrestling source) still holds (checked). The module's purpose is to record why the machine could not reach an entity, so a persisted reason that the record now contradicts is the module's own defect. Second consequence, UNVERIFIED: if the machine now reaches these entities, the library may carry a machine assay and a hand-built one for the same entity with no reconciliation. Fix: re-derive each reason from the live records, or date-stamp them ("as of 2026-08-xx").

### F4. local_agent.py:1582 dispatch catches (TypeError, ValueError) only, so a non-string argument still ends `run()` and discards the patch list (VERIFIED, LOW)
`t_find_symbol(name=5)` and `t_run_check(check=5)` do `(x or "").strip()` and raise AttributeError. `t_read_file(offset=1e999)` (JSON inf) raises OverflowError. None is caught. The comment at :1565 says a malformed call "MUST NOT END THE RUN".

Repro (`la1.py`, scripted `_chat`): `run()` itself RAISED `AttributeError 'int' object has no attribute 'strip'`, so the `patches` audit trail and the `unreverted` alarm list are lost with the traceback. Reaching the worst case needs a failed revert earlier in the same run, then a numeric `name`. Fix: `except Exception` at the dispatch (still returning the `{"error": ...}` dict), as the sweep67 order intended.

### F5. read.py:361-376 with :1495 `ensure_transport` pins False for the life of a `--loop` process (VERIFIED, LOW)
`_CASCADE_OK` is decided once and cached; `run()` calls `ensure_transport()` each pass but it returns the cached value. `read.py --run --loop` is a STANDING job that can live for days, and a transient `CB.engine()` failure at the first pass (or an import error) leaves the reader on local Ollama until src/ changes and codewatch restarts it. `workers` also collapses to 2 through `if _CASCADE_OK else 2`.

Repro (`rd1.py`, stub `cascade_bridge.engine` raising, then healthy): `first probe: False`, `second probe after cascade recovers: False`. Slow, not wrong, and one printed line says so per pass. Fix: re-probe False at the top of each `--loop` pass, or on the `_gate` timer.

### F6. profile.py:113-120 `_b32` loops forever on a negative address (VERIFIED, LOW)
`while n: out.append(B32[n & 31]); n >>= 5` never reaches 0 for negative n (-1 >> 5 is -1). Repro (`pf2.py`): `_b32(-1)` was still running after 1 s, growing a list. `encode` validates `band` and `attested` (:185) but not `address`. No caller passes a negative today (`assign` returns `pack()` output), so dormant. Fix: refuse `n < 0` with a ValueError beside the `attested` refusal.

### F7. profile.py:264-271 an unreadable TIERS.json or GENRES.json gives every world a wrong-but-valid profile, noted only (VERIFIED for the address change, LOW)
`except Exception: silence.note(...); tiers = {}`, then `AS.assign(w["designation"], tiers.get(src, {}))`. `assign` turns a missing tier into 0, which is the packed-zero ambiguity `assign_and_mark`/`charted_gaps` exist for (address_space, order 642a95fe9f3c). `pf1.py`: the address for the first live designation with real tiers differs from the one with `{}`. The round trip in `main()` then passes on the wrong addresses (it re-encodes what it decoded), and `decode`'s shelfmark is printed without `uncharted`. All 30 live sources have TIERS rows today, so this needs a torn read of the file. Consumers are only `main()` and verify_math, so it reports a wrong world set rather than corrupting stored data. Fix: raise on an unreadable file (as the empty-worlds case does), or use `assign_and_mark`.

### F8. threads.py:271, 296 `annex_codes`/`law_codes` still raise AttributeError when `declared` is not an object (VERIFIED, LOW)
The sweep67 fix guards the top level and the rows, not `doc.get("declared")`. `{"canons": [...], "declared": [1]}` gives `AttributeError: 'list' object has no attribute 'get'` (`th2.py`), out of `build()`, `verify()` and `threads_for`. Docstrings promise an EMPTY set. Fail-closed in effect (nothing written), but `main()` prints a traceback instead of REFUSING. Fix: `isinstance(declared, dict)`.

### F9. citecheck.py:175 with :330 `splitlines()` numbers lines differently from every editor and from `ast` (VERIFIED mechanism, LATENT, LOW)
`splitlines()` also breaks on `\x1c-\x1e`, `\x85`, ` `, ` ` (`"a b\nc".splitlines()` is 3 lines). The citation resolver, and the `line` of a stale finding, would shift by one for every line after such a character. `cc1.py`: 0 of the `src/*.py` files differ today (`_BAD_CHARS` only bans 8, 7, 11, 12). This is the same latent class as sweep67 batch04 Q2 (mutate.py). A shifted resolver can turn a good citation into BLANK_LINE and hide a bad one. Fix: split on `re.split(r"\r\n|\r|\n", text)` and drop a trailing empty element.

### F10. secondopinion.py:554-573 the torn-tree fingerprint only sees `.py` files (by reading, LOW)
`codewatch.fingerprint(root)` hashes `.py` files only. `report(['src','prompts'])` fingerprints `prompts/` as the constant empty digest, so a `.txt` caught mid-write there is never called "torn", while detect-secrets and `scan_for_secrets` do read it. Not reproduced by running it. Default `[SRC]` is unaffected. Fix: fingerprint the tree the scanners actually read, or say so in the report.

### F11. Stale comments (cosmetic, LOW)
- read.py:1358 "one 61 MB object": measured 80 MB now.
- handbuilt.py:284 "queued ahead of nothing" and 21,614 entities: a count nobody keeps current; the header (:9-41) also states pre-catalogue facts (F3).
- lognames.py: consistent with `overnight`/`dashboard` names as far as the file itself shows. No finding.

## Questions

1. **read.py:436-441 `_gate`.** On a `tuning.regime()` exception the regime keeps its last value (initially "cloud"), so a broken `tuning` import leaves the wide 16-permit gate on for the whole run, with only a note. Deliberate?
2. **read.py:1706-1715 `--loop`.** Still ignores `run()`'s `ok` (carried).
3. **read.py:624-661 `fallback_model`.** A failed `/api/tags` probe caches the 18.6 GB configured model for the process life (carried).
4. **citecheck.py:215-223 `_self_citation_ok`** is constant False, so the `target_name == base and ...` test at :359 can never be true. Documented as "grants no exemption"; is a hook that cannot fire wanted, or should the branch go (liveness-shaped dead guard)?
5. **citecheck.py:137 QUOTED_TAG exemption.** A genuine pointer written inside matching quotes (`"see 'x.py:88'"` style) is set aside as a mention and never checked. Measured as all-mentions when written (21 of 21); the exemption still lets a rotted pointer hide if someone quotes it. Kept deliberately?
6. **local_agent.py:1110-1128 text-mode rewrite** (carried): a revert of an LF file under `prompts/` or `handoff/` would come back CRLF, not byte-exact.

## Cleared (examined, no defect)

- **read.py**: `_names` (fold, unicode split, phrase fallback with per-gap punctuation), `_ask_ungated` ladder, the `_pool_answer_usable` call and counters, `_local_carded` (None from any piece returns None, seams noted), `_chunk_key` includes the entity, `read_entity` caches only when nothing is unanswered, `cap_chunks` inert with a note, `priority()` three buckets (none dropped), `queue()` fail-closed host map and current-rule prune, `run()` exit code, `--one` prints every feat.
- **local_agent.py**: the full write gate (denylist both case-folded spellings, allowlist on both spellings, region prefixes, NTFS-stream/junction/hard-link (`st_nlink`), blast cap charged at landing, `_gates` parse/lint/import/verify_math regex, revert plus SAFETY escalation, halt check), `_tool_message` (always valid JSON), `_achievement`, `t_find_symbol` skip reporting, `t_grep` file/dir handling.
- **threads.py**: `cohort_family`, `category_path`, `build()` sibling map from `source_codes`, `edge()` refusals (T5 refused, unresolvable address refused), `counts`, `threads_for` T4 derivation and refusal, `verify()` T3 checks and the empty-Annex refusal, `recorded_pairs`, rc paths and the ratification gate.
- **secondopinion.py**: `_exe` reason split, per-tool exit-code handling (ruff 0/1, vulture 0/1/3 with nothing-parsed refusal, detect-secrets 0), `ran_clean`/`missing` (absent is not clean), `--file-orders` refused on a torn tree, disagreement branches keyed on comparison.
- **handbuilt.py**: `compute()` ran clean for all nine sheets (M and decimals plausible, Zalama interval 0.19 vs 0.15 as its comment now says), sentinel-safe `--full`, write before print, halt asked before the write.
- **citecheck.py**: `CITATION` boundaries, `_in_tree_lead`, other-tree/mention skips counted by kind, line 0 as PAST_EOF, UNRESOLVED not filed, uncapped findings.
- **profile.py**: alphabet/regex derivation, decode per-axis refusal, band clamp and the `a` (=10) digit round trip, attested refusal.
- **resonance.py**: Gauss-Seidel in place, gauge fix, largest-shift test, non-convergence returns None everywhere, no-evidence vs eta 1.0 split, self-loop and multi-component graphs, `incomparability_rate` split, uncapped `examples`.
- **lognames.py**: 6 log constants, `OWNER` fragments and `PRODUCT` witnesses consistent (every constant is keyed in both tables).

## Coverage

Recorded via `sweep_plan.record('run68', ['read.py', 'local_agent.py', 'threads.py', 'secondopinion.py', 'handbuilt.py', 'citecheck.py', 'profile.py', 'resonance.py', 'lognames.py'], batch=16)` after this file was written.
