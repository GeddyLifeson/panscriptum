# sweep67 batch16 audit (run67, 2026-09-28)

## Scope (each module read in full, sequentially, no skimming)

| module | lines | chunks read |
|---|---|---|
| src/read.py | 1720 | 1-600, 601-1160, 1161-1720 |
| src/local_agent.py | 1677 | 1-560, 561-1130, 1131-1677 |
| src/wiki_source.py | 910 | 1-470, 471-910 |
| src/weave.py | 740 | 1-400, 401-740 |
| src/withdraw_chapters.py | 614 | 1-320, 321-614 |
| src/render.py | 441 | whole |
| src/sweep.py | 374 | whole |
| src/tempus.py | 309 | whole |

Total 6,785 lines. Read-only on the project. Scratch scripts lived under %TEMP%\s67b16. No daemon, phase, generate, publish, mutate, verify_math or drill was run, and no subagent was spawned.

Incidental write to disclose: my reproduction script (page_text with `_api` patched to raise) triggered `silence.note` and `health.flush`. That added a few `silent:wiki_source-page_text-section` counts to `state/failures.json` through the project's own atomic writer. No other file under state/, data/, src/, output/ was touched.

## Prior-audit cross-check

No sweep66 report names `read.py` or `sweep.py` as read. The `sweep.py` hits in sweep66 are all `allsweep.py`. The other six modules were covered:

- **local_agent.py** (sweep66 batch16: 0 findings).
  - The carried sweep64 SUSPECTED item, a hard link from the writable surface into a `DENYLIST_PREFIXES` region (order d2f103634cf1), is **resolved**. `t_propose_patch` now refuses `st_nlink > 1` or an un-stat-able target (local_agent.py:1037-1047), and the code cites the order. The audit trail also now records find/replace whole (:899), where it was cut to 200 characters before. The file grew 1650 to 1677 lines, consistent with those two changes. The gate trace is otherwise unchanged and still holds.
- **weave.py / tempus.py** (sweep66 batch04: 0 findings). Both still stand as cleared for the items named there. Finding F1 below is new and is not in that report.
- **wiki_source.py / withdraw_chapters.py** (sweep66 batch07: 0 findings). withdraw_chapters is unchanged. wiki_source grew 808 to 910 lines with the maintenance-box block (order cb31bf2707ad). I read that block closely: `_furniture_spans` closes by balanced tag counting and fails closed on an unclosed container, and the banner regexes only strip a leading run. No defect.
- **render.py** (sweep66 batch09: 0 findings). Unchanged at 441 lines. Order 5bb12b398783 (SWEEP54_QUESTIONS_FOR_A_RULING, OWNER) still names it and is still open. See Q3.
- The sweep66 batch02 remark that a comment at `:11415` mis-cites `withdraw_chapters.py:176`. The comment is not in my modules and I did not re-check it.

## Findings

### F1. weave.py:289-297 `filtered_index` decides on `hits[0]` alone and drops or keeps the whole key (VERIFIED, medium-low)
`filtered_index` tests only `hits[0]` (name and description) against `_MECHANIC`, `_STATBLOCK` and `_RULES_VOICE`, then keeps or drops all hits of that key. `ENTITY_INDEX` hits are ordered by source name, so the alphabetically first source decides the fate of every other source's entity of the same name.

Repro (`%TEMP%\s67b16\w1.py`, live `data/ENTITY_INDEX.json`, 266,437 keys, 9,755 with 2 or more hits). I applied only weave's own `_MECHANIC` and `_RULES_VOICE`, not `_STATBLOCK`, so the counts are a floor:
- 160 keys are dropped wholesale because hits[0] is rules text, although at least one other hit is not. Examples: `herooflight` (A Plethora of Paladins is rules, Legend of Zelda is not), `quickdraw` (Henry Stickmin), `reaper` (Diablo, Doom, Mass Effect kept out because Adventure Time's hit is flagged).
- 587 keys are kept although some non-first hit is rules text. That rules text then serves as continuity evidence, which is the failure the module docstring names ("Dexterity", "Channel Divinity").

Effect: the pair weights, the permutation null and `resolve()` all read a source-order-dependent index. Real cross-source sharing is lost for 160 keys and rules-text sharing is admitted for 587.

Fix: filter per hit (`hits = [h for h in hits if not bad(h)]`, drop the key only if none remain), which makes the result independent of source order.

### F2. local_agent.py:646 with :1573 `int(offset)` ValueError escapes the dispatch handler (VERIFIED, low-medium)
`run()` guards tool dispatch with `except TypeError` only (:1573), under a comment saying a malformed tool call "MUST NOT END THE RUN". `t_read_file` does `int(offset or 0)`. A model-supplied `offset="12,000"` or `"abc"` raises **ValueError**, which propagates out of `run()`.

Repro: `local_agent.t_read_file("src/read.py", offset="12,000")` raises `ValueError: invalid literal for int()`. The uncaught exception discards the transcript and `patches`. It also discards the `unreverted` alarm list, so a half-written module from an earlier failed revert in the same run would not reach the exit code.

Fix: catch `Exception` at the dispatch, returning `{"error": ...}`. Alternatively coerce `offset` inside `t_read_file` with a try.

### F3. local_agent.py:333-373 `t_find_symbol` silently skips files it cannot parse and still reports `unique: True` (VERIFIED, low)
An unparseable or unreadable `src/*.py` is skipped by `except Exception: continue`, with no note and nothing in the result. The tool exists to stop the model patching the wrong function (m38), and a uniqueness verdict computed over a subset is a plausible wrong answer.

Repro (`l1.py`, fake tree with a valid `a.py` and a syntax-broken `b.py`, both defining `foo`): the result is `count 1, unique True, warning None`. The `deprecated` skip is also unmentioned in the result.

Fix: collect `skipped_files` and add a warning and `unique: False` when any file could not be parsed.

### F4. wiki_source.py:577-593 `page_text` returns "" when all three section fetches raised (VERIFIED, low-medium)
The `continue` fix covers one failed section. If all three raise (network down, or the fandom IP ban the header comments describe), the return is `""`, indistinguishable from a page with no prose. `page_texts` then drops the title.

Repro (`l1.py`, `_api` patched to raise): `page_text` returns `''` and `page_texts` returns `{}`. `catalogue_web` counts `no_text` and documents that it "cannot tell the two apart from the outside".

Fix: raise, or return a sentinel, when every section raised and none answered. The distinction is available here and nowhere else.

### F5. sweep.py:131-133, :149-150, :162 absent input files become empty maps and a plausible all-negative sweep (VERIFIED by reading, low)
- `hosts = ... if os.path.exists(F.HOSTS) else {}`
- `rosetta_index` returns `{}` if ROSETTA.json is absent.
- `navtree_names` returns `{}, {}` if NAVTREE.json is absent.

A missing file gives every row `host None` and `shelfmark None`. That yields reachable=0, read=0 and addressed=0, which is a coherent-looking report. It is then written to CHARACTER_SWEEP.json, which the file's own comment says magnitude, standards, foreman and hostcheck read "as fact". `read.py:queue` refuses the same empty-host condition (SystemExit).

Fix: refuse or flag when HOSTS is absent or empty, and state in the report which inputs were missing.

### F6. read.py:1362 the qcache prune keeps superseded-rule entries (VERIFIED by measurement, low)
`qcache = {k: v ... if _QK in k}` keeps any key containing the separator. The comment says entries under the old path-only key "are DROPPED". Keys from before `_QROW_RULE` was appended (`path SEP name`) also contain `_QK`, so they are kept forever.

Measured on live `state/read_queue_index.json` (152 MB, not the "61 MB" the comment states): 548,734 keys, of which only 275,437 end with the current rule `norm_q-own-page-v2`. About 273,000 (50%) are pre-rule keys ending in the entity name. They can never be hit and are re-serialised whole every pass. Any future `_QROW_RULE` bump repeats this.

Fix: keep only `k.endswith(_QK + _QROW_RULE)`.

### F7. Stale line-number comments (low, cosmetic)
- read.py:64-76 says CHUNK's recall measurement is at ":88-96 below". It is at :99-107.
- read.py:584 says "CLOUD_CHUNK == CHUNK now (:94-96)". The assignment is :111.
- read.py:889 says ":88-96" for the measurement, and it is at :99-107.
- read.py:1569 and :1571 cite ":872-875" and ":530-540-area". Those passages are now near :1029-1032 and :603-612.
- sweep.py:86-89 says the live read is "`cachekey.load` at :160". `sweep()` is at :160 and the `cachekey.load` call is at :192. sweep.py:186 says `cache_path` is "below", and it is defined above at :72.

Fix: cite by symbol, as the sweep66 orders already ask elsewhere.

## Questions

1. **read.py:657-660, `fallback_model`.** After a transient `/api/tags` failure it caches `c.get("model")` (config's 18.6 GB model) for the life of the process. Under `--loop` (a standing job) every later local fallback then thrashes a 10 GB card, which is the state its own docstring says caused the 18-in-15-minutes timeouts. Deliberate memoisation, or should a failed probe not be cached?
2. **read.py:1702-1714, `--loop`.** The loop ignores `run()`'s `ok`. A pass where every entity raised loops on forever with rc never surfaced, and only the one-shot path returns 1. Intended, given the keeper?
3. **render.py `write_views` (:385-437).** It draws only `sample = next(iter(worlds.values()))`, one node per tier written to `output/views/<tier>.svg`. The tree holds 7 hyperverse, 43 xenoverse, 120 metaverse, 214 multiverse and 350 universe nodes (measured, `r1.py`). `universe.svg` is an empty ring (0 children). Is one sample node per tier the intended product under Hard Rule 0, or should it draw every node? (Related to open order 5bb12b398783.)
4. **tempus.py:107-114 with pipeline.py:3070.** `apparent_lag_years` returns the same "no shared furniture" answer for an unknown shelf name (`shortest` returns `(inf, [])`) as for a real absence. `pipeline.phase_history` uses `REGISTRY_SHELF = sorted(tiersd)[0]`, the alphabetically first source, as the reference shelf. Placeholder, or ruled?
5. **withdraw_chapters.py:483-489.** `_manifest_merge` replaces an unparseable existing manifest with only this run's withdrawals (it prints, but the corrupt file is overwritten under a digest match). Should an unparseable manifest be set aside, not replaced, given the archive is the only copy?
6. **weave.py:138-146.** `load_index` warns on a stale ENTITY_INDEX (stderr only) and `--write` then lands the derived files anyway. Currently `CONTINUITY_GROUPS.json` and `RESOLVED_ENTITIES.json` are dated Aug 22, against an index of Sep 28. The 2..60-source band that drops common names from pair weights looks deliberate. Confirm that both stay as they are.
7. **local_agent.py:1103-1131.** It rewrites files in text mode. Every `src/` file is CRLF, so this is harmless there, but an LF file under `prompts/` or `handoff/` would come back CRLF and a revert would not be byte-exact. I did not check those trees' line endings.
8. **local_agent.py:1119.** The returned `why` is still cut to 200 characters, while the audit-trail entry was made whole. It is only echoed to the model; leave it?

## Cleared (examined, no defect)

- **read.py**
  - `_names` matching, including the punctuation-gap fallback and the fold on both sides.
  - `_ask_ungated` transport ladder and counters, including the `_pool_answer_usable` shape check.
  - `_gate`/`_card_gate` re-entrancy.
  - `_local_carded` returns None if any piece fails, so an empty merge cannot be cached.
  - `_chunk_key` includes the entity.
  - `read_entity` caches only when nothing is unanswered; `cap_chunks` is inert and noted.
  - `priority()` three buckets, with none dropped.
  - `queue()` fails closed on an empty or unreadable host map.
  - `run()` exit code.
  - `_HAS_ACTION` is skip-only and its skip count is reported.
- **local_agent.py**
  - The full write gate: denylists, allowlist on both spellings, region prefixes, NTFS-stream/junction/hard-link handling, blast cap charged at landing, `_gates` parse/lint/import/verify_math regex, revert plus SAFETY escalation, halt check, `_tool_message`, `_achievement`.
- **wiki_source.py**
  - Every raising walk (`all_categories`, `category_members`, `extracts`, `rank_by_size`), and the category floor, which is ruled and reported.
  - `resolve_wiki` three-way branch.
  - Maintenance-box stripping.
- **weave.py**
  - The null-threshold refusal, `components` complete linkage and its `<= 0` refusal, `resolve`, and the write verdicts.
  - No entity name in the live index lacks an ASCII token (0 of 266,437), so surprisal cannot silently zero any of them.
- **withdraw_chapters.py**
  - `_file_state`, `_archive_name_free`, CAS `_land_merged`, per-selector refusal, half-entry amendment, and rc propagation.
- **render.py**
  - `children_of` whole-coordinate guard and the atomic writes.
- **sweep.py**
  - `nested_run` and the funnel.
- **tempus.py**
  - `rung_description_length`, `band_resolution` and `prescience_horizon_bits` (positive-lead guard). `retrocausality_beta` returns 0.0 for a non-positive span, which is the correct "no inversion" value.
  - The dead-code markers are all owner-ruled.

## Coverage

Recorded via `sweep_plan.record('run67', ['read.py', 'local_agent.py', 'wiki_source.py', 'weave.py', 'withdraw_chapters.py', 'render.py', 'sweep.py', 'tempus.py'], batch=16)` after this file was written.
