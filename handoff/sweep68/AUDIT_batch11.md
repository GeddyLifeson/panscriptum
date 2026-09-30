# sweep68 (run68) batch 11 - audit

Every line of every module below was read with the Read tool, sequentially, in chunks. Line counts match
`wc -l`. Reproductions are in `%TEMP%/aud68_11` (`chain_repro.py`, `scout_repro.py`, `pg_repro.py`,
`pick_repro.py`, `em_repro.py`, `id_repro.py`, `j.py`); each imports the live module with `silence.note`
stubbed and every write path (`feats.HOSTS`, `SC.BLOCKED`, `identity.CACHE`/`HERE`, `pick_model.save_config`,
`endpoint.register`, `escalation.HALT_FILE`) redirected to a temp directory. No `main()` of a live tool, no
model call, nothing under `state/` or `data/` touched.

## Scope

| module | lines | notes |
|---|---:|---|
| src/overnight.py | 2165 | whole (+15 vs sweep67) |
| src/chain.py | 1310 | whole (+5) |
| src/scout.py | 878 | whole (+43 vs sweep67 b08's 835) |
| src/identity.py | 763 | whole (unchanged) |
| src/prose_gate.py | 621 | whole (+57: new marginalia section 567-621) |
| src/pick_model.py | 479 | whole (+14) |
| src/catalogue_aurora.py | 357 | whole (+29) |
| src/entity_match.py | 326 | whole (+7) |

## Prior-audit cross-check (sweep67 b05, b08, b10, b11, b15)

FIXED / CLOSED (verified in the current code):
- b11 F1 `write_status` renders a failed snapshot as zeros: fixed (`good` list, overnight.py:1490-1518).
- b11 F3 `chain.py --limit` unmarked truncation: fixed (`limit` and `rows_harvested` ride into `unanswered`, chain.py:672-676, 812-815).
- b11 F4 stale line numbers in overnight.py: fixed ("Named, not line-numbered", 1616).
- b08 F1/F2 scout 403/429 and transport-as-invented-URL: fixed (`_control_404`, `transport` flag, `reached=False` on all-transport).
- b05 F8 catalogue_aurora silent unparseable XML: fixed (`unparsed` list, printed, counted into `refused`, rc 1).
- b10 #6 `pick_model.save_config` leaked temp: fixed (removed on both failure paths).
- b10 finding 1, digit half: fixed (`similarity` digit-run gate, entity_match.py:190). The other half still stands (see N6).

STILL STANDS:
- b10 finding 1, non-trailing parenthetical half: STANDS, reproduced below as N6.
- b10 Q3 `best()` returns the alphabetically-first of equal top scores without flagging the tie: unchanged
  (`best("Zeus Prime", ["Zeus Prime", "Zeus  Prime"])` returns the double-space one, unflagged).
- b10 Q4 `weight_gb` returns 0.0 for an entry with no `size` and no parsable params and `resident()` admits it
  (`resident({"name": "mystery-model:latest"}, 9.7)` is True). Unreachable while Ollama supplies `size`.
- b11 Q1 (halt at top of lap `break`s the supervisor; idle branch waits instead): code unchanged, still a question.
- b11 Q2 (`running()` matches script basename, so a hand-run `feats.py --mine` blocks the roll): unchanged.
- b11 Q3 (prose_gate 4c searches "Not applicable"/"uninstrumented"/axis label over the whole block): unchanged (484-488).
- b11 Q4 (prose_gate body strip has no colon): STANDS and is now REPRODUCED as a false refusal, see N7.
- b15 Q5 (`identity._titles` calls `.get` on whatever `json.load` returns): unchanged, loud, not re-filed.

## Findings

### N1. MEDIUM, VERIFIED. chain.py:761-773 - a self-edge from the entity index kills the whole fit
`"if not w or not loser or w.lower() == loser.lower()"` only rejects identical strings. The next test is on
`WI.norm` keys, and `norm` drops parentheticals, titles and punctuation, so two different strings share a key,
and a partial name ("Ichigo" / "Ichigo Kurosaki") resolves to the same canonical name. `edges[(x, x)]` is then
built. Since sweep67 b05 `rigor.bradley_terry` raises `RigorIntegrityError` on any `a == b` key, so one such
edge aborts `chain.fit` (and `pipeline.phase_chain`, which calls `CH.fit(edges, prior=0.5)` at pipeline.py:2985)
with a traceback, `CHAIN.json` is not written, and the previous fit stays on disk looking current.
Scenario: the model answers `winner "Goku (Super Saiyan)", loser "Goku"` for one sentence out of ~30,000.
Reproduction (`chain_repro.py`, entity index stubbed): `edges = {('Goku','Goku'): 1, ...}` then
`fit raised: RigorIntegrityError bradley_terry: 'Goku' is contested against itself`.
Fix: skip `idx[wk] == idx[lk]` (or `wk == lk`) in `work()` and count it in `unmatched`/a `self_contest` tally.

### N2. MEDIUM, VERIFIED. scout.py:498-503 - `scout()` overwrites an existing wiki host with `pages:<source>`
`_adopt` is `hosts[source] = "pages:" + source`, unconditional. `sweep()` only reaches hostless sources, but
`main()` with `--source X` deliberately supports a source that is NOT hostless (the `names is None` branch
looks the record up itself) and calls `scout(..., register=True)`. `feats.py:534` treats a `pages:` host as
"read only SOURCE_PAGES.json", so the source's real wiki stops being read.
Scenario: `python src/scout.py --source "Some Source"` where WIKI_HOSTS.json holds `somewiki.fandom.com`; one
proposed URL verifies. Reproduction (`scout_repro.py`): before `{'Some Source': 'somewiki.fandom.com'}`, after
`{'Some Source': 'pages:Some Source'}`, `registered: True`. Same window exists in `sweep()` if
`hostcheck --adopt` lands a real host between `hostless()` and the `_mutate` (CAS protects torn writes, but
`_adopt` never looks at what it is replacing).
Fix: inside `_adopt`, refuse (return False, do not set) when `hosts.get(source)` is already non-empty and not a
`pages:` value.

### N3. MEDIUM, VERIFIED. scout.py (whole file) - a hand-run WIKI_HOSTS.json writer with no halt interlock
Hard Rule -1. `scout.py` has zero `assert_clear`/`_assert_not_halted` calls and is not on
`verify_math._INTERLOCKED` (7762-7772). Its `main()` writes WIKI_HOSTS.json (via `_mutate`), SOURCE_PAGES.json
(via `endpoint.register`), SCOUT_ATTEMPTS/BLOCKED and spends model calls. `hostcheck.py` was put on the roster on
2026-09-06 precisely because `--repair/--adopt --go` rewrite WIKI_HOSTS.json, "one of the two files not
reconstructible from anything else on disk". The roster check is one-directional (every module that calls
`assert_clear` must be on it), so a module that never calls it is invisible to the net.
Reproduction (`scout_repro.py`): `ESC.HALT_FILE` pointed at a temp file holding a live halt, `ESC.status()[0]`
True, `scout("Halted Src", ..., register=True)` returns `registered: True` and rewrites the host map.
Fix: `_assert_not_halted` on the writing path of `main()` (skip `--dry`), add to `_INTERLOCKED` and drill's
`_HALT_WRITERS`. (The foreman's `scout_hostless` path is gated by the foreman itself; this is the hand-run path.)

### N4. MEDIUM, VERIFIED. pick_model.py:390, 397-401, 466-473 - unmeasured VRAM lets `--write` install an unenforced pick
When `nvidia-smi` cannot be read, `vram_measured` is False, `resident()` is skipped, and the WARNING says "Fix
nvidia-smi and re-run before trusting this pick" - and then `--write` writes that pick into config.yaml anyway.
The doctrine is fail closed, and the owner's 2026-08-24 ruling (GPU-only) is exactly the thing not being
enforced. The scoring then favours the biggest model.
Reproduction (`pick_model.py` with `total_vram_gb` stubbed, `save_config` stubbed to capture): with a 10.74 GB
card the 30B MoE is REFUSED and `qwen3:8b` is written; with `total_vram_gb() -> None` the same two models give
`WROTE model = qwen3:30b-a3b-instruct-2507-q4_K_M`. config.yaml is re-read by nine modules, and nvidia-smi
has a 15 s timeout on a card the pipeline keeps at 99%.
Fix: refuse `--write` (exit 1, keep the printed report) when `not vram_measured`.

### N5. MEDIUM, VERIFIED. prose_gate.py:343-345, 549 - layer 4b only recognises `Axis: <digit>`; five plausible spellings of an unearned score pass
`_AXIS_RE` needs the label, optional decoration, a colon, optional decoration, then digits. Measured with
`unearned_instrument(text, set())` on an uncited Person (`pg_repro.py`): `Wisdom: 28 (..)` caught; `Wisdom: ~28`,
`Wisdom: about 28`, `Wisdom (Perception): 28`, `Wisdom - 28`, `| Wisdom | 28 |` and a full-width colon all
NOT caught. `_AXIS_LABEL` (used by 4c) has the same "label then colon" shape, so an entry carrying `Wisdom: ~28`
would also count as `scored` there. The file's own comment (333-341) records the first version losing to bold
markdown for the same reason. Scenario: model writes `Strength: ~24` under `Magnitude: unassayed` for a source
with 0% cited; the block passes 4b and is written. Not proven to occur in the wild (frequency UNVERIFIED), but the
gate is green for exactly the deviations a model makes under a template it is paraphrasing.
Fix: match the label followed by any run of non-newline non-letter characters and a digit, and add the table row
form; add the variants above to the drill fixture.

### N6. MEDIUM (latent, no production caller), VERIFIED. entity_match.py:94-108, 263 - continuity marker that is not last is fuzzy-scored; `best()` returns STRONG
Carried from sweep67 b10 finding 1 (its digit half is fixed). `qualifier_compatible` sees only a trailing
parenthetical. `best("Doctor Stephen Vincent Strange of the Sanctum Sanctorum (Ultimate) (Sorcerer)", ["... (Prime)
(Sorcerer)"])` returns `('strong', 0.9358)` and `qualifier_compatible` is True (both trailing qualifiers are
"Sorcerer"). The shorter `Wally West (New Earth) (Comics)` vs `(Prime Earth) (Comics)` still lands at `weak`
0.8333 (listed, not blocked). Nothing in production calls `best()` yet (only drill, verify_math, liveness,
sevenfold, tempus, threads mention the module), so nothing is mis-merged today.
Fix as b10 suggested: gate every parenthetical group, in order.

### N7. LOW, VERIFIED. prose_gate.py:266-268 - the body strip eats any line that STARTS with the label words, so a real Record paragraph is refused as "only 1 characters of prose"
The strip pattern `^[\s*_#>-]*(Shelfmark|Class|Magnitude|Threads).*$` has no colon, and `.*$` takes the rest of the
line, so a paragraph beginning "Classical scholarship...", "Threads of ...", "Classified as ..." or "Magnitude
of ..." is deleted whole. A Record is one long line in the template, so an entry whose only paragraph opens with
one of those words gets `only 1 characters of prose (needs 120)` and the block is refused. Reproduction
(`pg_repro.py`, three-sentence Record starting "Classical"): `(4, 5, ['entry 1: only 1 characters of prose
(needs 120)'])`. Over-refusal only (fail-closed direction), carried from b11 Q4 and now measured.
Fix: use the same `re.escape(sec)` (with its colon) that the presence test at 257 uses.

### N8. LOW, VERIFIED. prose_gate.py:583-588, 605-621 - `_EYEWITNESS` verbs are wide enough to delete ordinary reactions
New section (2026-09-29). `held`, `stood`, `lived`, `watched`, `met`, `faced` are in the verb list, and
`drop_invented_marginalia` removes the whole line with no per-note record. Measured: all five of
`AVAR: I held my breath reading this Record.`, `QUILL: I stood corrected by the second paragraph.`,
`MOTH: We watched the Record diverge from the wiki, Avar.`, `QUILL: I lived for entries like this one.`,
`AVAR: I have met stricter clerks than this Record.` are dropped. The module says a Hand "may react to the
Record"; these are reactions. Content loss, not a safety fault. Also worth confirming that `generate.py` logs
the dropped count per chapter (it captures `_inv_dropped`; I did not read generate.py).

### N9. LOW, VERIFIED. chain.py:717-756, 788-798 - model output of the wrong TYPE still ends the pass (run #60's fix covered one shape)
The comment at 732-747 says every malformation is handled by skipping. Reproduced with `extract()` and `_ask`
stubbed: `{"outcomes": null}` -> `TypeError: 'NoneType' object is not iterable`; `winner: 5` ->
`AttributeError: 'int' object has no attribute 'strip'`; a bare JSON list as the whole answer ->
`AttributeError: 'list' object has no attribute 'get'`. Each propagates out of `work()` through `ex.map` and
ends the run, CHAIN.json stays the old fit. Fix: `got if isinstance(got, dict)`, `outcomes` coerced to a list,
`str()` on winner/loser before `.strip()`.

### N10. LOW, VERIFIED. scout.py:431, 257-264 - a non-object model answer kills the sweep after the stamps are spent; a string `urls` is logged as a real negative
`urls = [... for u in ((got or {}).get("urls") or [])...]`. A list answer raises `AttributeError` (reproduced)
past every `except` in `scout()`, so `sweep()` never writes SCOUT.json/ARCHIVE and never unstamps, and the
attempt stamps written before the work stand - the failure order d57377577891's comment describes for a raising
`register`. `{"urls": "https://example.org/x"}` iterates characters, none start with "http", and the result is
`model proposed nothing`, `reached: True` (reproduced) - the source burns its rotation slot on a proposal that
existed. Fix: `isinstance(got, dict)` and `isinstance(urls, list)` checks that return `reached: False`.

### N11. LOW, VERIFIED. identity.py:373-434, 705-717 with overnight.py:580-592 - `identity.py --refresh` exits 0 when it refused or could not write, and the supervisor logs "re-mined whole"
`load(refresh=True)` returns the inventory on three paths that leave the disk copy unchanged (root absent,
"REFUSING to overwrite" an empty mine over a populated cache, and a denied `write_json`); `main()` ignores which
and returns 0 after printing a banner computed from the returned (empty) inventory. `identity_refresh_cycle`
tests only `returncode`. Reproduction (`id_repro.py`, temp tree): refusal case prints `0 hosts indexed, 0
on disk` and `main() rc = 0`, cache mtime unmoved; denied-write case `rc = 0`. The supervisor then logs
`designator inventory re-mined whole in Ns`. Self-corrects (mtime unmoved, so the next lap retries), but the
log line is false and a persistently failing refresh costs a full mine every lap (up to the 3600 s timeout).
Fix: have `load` report whether it landed and return 1 from `main` when it did not.

### N12. LOW, VERIFIED. identity.py:563-575 with chain.py:902 - a JSON-list model answer raises TypeError out of `epoch_of(strict=True)`
`_json(raw)` handles dict and str only; a list reaches `re.search(pattern, list)` and raises
`TypeError: expected string or bytes-like object, got 'list'` (reproduced with `_ask` stubbed).
`adjudicate_mutuals` catches only `ID.ProbeUnavailable`, so the whole chain pass ends.
Fix: `_json` returns `{}` for anything else (which `epoch_of` already turns into `ProbeUnavailable`).

### N13. LOW, by reading. overnight.py:2035-2042 - in-lap maintenance subprocesses do not re-ask halt or pause
The halt and the pause are asked at the top of a lap; a lap is hours (reader up to 3 h, roll join up to 4 h).
After those return, `canon_backup_cycle`, `identity_refresh_cycle` (16-minute mine, no interlock in
identity.py), `weave_index_cycle` (178 MB write; weave_index has its own gate) and `coverage_snapshot` run
without asking. `start()`/`run()` gate on manager stop and pause, but these use `subprocess.run` directly. A pause
issued mid-lap ("the owner wants the machine") is not honoured by the 16-minute identity mine. Low because the
files are derived and the top-of-lap check catches it a lap later.

### N14. LOW, by reading. identity.py:154-200 vs chain.py:401 - `identity.mine()` never reads `data/readfeats`, but `chain.harvest()` calls `identify()` on readfeats hosts
Latent. `data/readfeats` holds 99 host directories, one of which (`disney_fandom_com`) has no `data/feats`
counterpart, so `stale_hosts()` cannot see it and `_inv_counts` answers `{}` for it: every title on a
readfeats-only host reads as "no continuity", the wrong-merge direction the module exists to prevent. Current
impact is zero (that directory holds no files; `disney.py` in the scratch dir confirms 0 titles). Question or
fix: mine `readfeats` too, or include it in `stale_hosts`.

### N15. LOW, by reading. chain.py:391-395 - the `ID.load()` fallback in `harvest()` defers the failure instead of degrading
`_inv = None` after a failed load, then `ID.identify(page, host, inv=None)` calls `continuities` -> `load()`
again, which raises the same error inside the file loop with no handler. The `except` reads like graceful
degradation and is not; the pass still dies, later, at the first contest sentence. Loud, so low.

## Questions (owner's call; not filed as defects)

1. scout.py:356-357 `verify` requires `min(MIN_NAME_HITS=2, probeable)` hits, and since order e8cd908ce5e4
   `probeable` is every catalogued name (681 for The Elements Beyond). The bar stayed at 2 while the pool grew
   ~27x, so a generic D&D page has a much better chance of carrying two of 681 common-word names ("Fire",
   "Ember") than two of 25. Should the required hits scale (a fraction, or a floor on the longest names)?
   UNVERIFIED: I did not fetch a page.
2. catalogue_aurora.py:245-260 - a source with an unparseable XML file is still written and marked `catalogued`
   with a partial `entry_count`, so the default selection (`entry_count == 0`) never re-reads it once the file is
   fixed. The rc is now 1 and the refusal is named. Is "partial but marked done" wanted, or should the roll row
   stay at 0 until the XML parses?
3. chain.py:1075-1078 `_singleton_active` treats a claim whose pid is alive as held, with no process-creation
   time comparison, so a recycled pid blocks `chain.py` until that pid exits. Documented as the safe direction;
   confirming it is preferred over `runguard`'s process-signature check.
4. pick_model.py:128 `re.subn(r'^model:\s*.*$', ...)` - `\s*` can cross a newline, and a trailing comment on the
   model line is discarded. config.yaml line 37 is a plain `model: "qwen3:8b"` today, so neither bites.
5. prose_gate.py:447 `_INSTRUMENT_MARK` ends with `|▣`, so a `▣` anywhere in the block satisfies the marker. Same
   family as b11 Q3.

## Checked and found sound (so it is not re-read)

- overnight.py: `_proc_lines` three-answer contract, TTL and blind handling; `_cmd_tokens`/`_cmd_is_running`
  (`-m`/`-c` refusals, args-in-fragment test); `_in_this_tree`; `_guarded_popen` lock and banner ordering;
  `run`/`start`/`join`; `_manager_stopped` both spellings; `weave_index_decision` (None does not rebuild);
  `name_rc` signed/NTSTATUS handling; `coverage_snapshot` rc+mtime; `preflight` label-by-identity and DID NOT
  COMPLETE branch; `safety_drill` rc handling; `write_status` (good rows only, window announced); the prose gate
  `drill_rc == 0`; the idle counter, `BUSY_STATUSES`, halt-wait branch; keeper and keep-warm threads. Every report
  function's input was checked against the live file shape (FOREMAN.json rows carry `standard/remedy/result/did`;
  failures.json values are all ints), so the unguarded key reads in `foreman_report`/`ledger_report` cannot raise
  on today's data.
- chain.py: `_RECIPE_KEY`, `_corpus_root_state`/held roots, `_land_harvest` and `refresh_continuity` CAS loops,
  dedup key (full sentence), `write_result` uncapped `most_common()`, `landed()`, `adjudicate_mutuals` branches
  (split/left standing/unprobed/half-dated/self-split), singleton claim/release, halt guard ahead of the claim.
- scout.py: `_mutate` fail-closed on damaged file, `hostless()` raising `HostsUnreadable`, `sweep()` stamp and
  `_unstamp` (`seen_ok`), log-shape checks, archive-before-trim roll-off, `verify` `needed` arithmetic,
  `_control_404`, `--limit 0`.
- identity.py: `_is_continuity` n=1/2/>=3, `mine` visited-key rule, `stale_hosts`, `load` incremental repair and
  empty-over-populated refusal, `_inv_keys`/`_inv_counts`, `epoch_of` strict/overlong.
- prose_gate.py: strict `is not True` on both gates, `floor_ok`/`evidence_ok`, `section_shortfall` ghost and extra
  charging, `assert_block_complete`, `instrument_shortfall` non-being rule, `unearned_instrument` exact-name match,
  `_HAND_LINE` against the prompt's actual `AVAR:` / `CUSTOS-PRIME AVAR:` / `**QUILL:**` shapes.
- pick_model.py: family-tier ordering, `_mib_to_gb`, `resident` vs `fit_note` budgets, `--min-quality`, both
  `save_config` failure paths.
- catalogue_aurora.py: uncapped slug with legacy `record_path`, description-in-key dedup, `write_record_catalogue`
  merge (it preserves `synthesis`, so `--force` cannot null one), roll CAS via `roll.update_rows`, rc carries every
  refusal.
- entity_match.py: threshold ratchet, empty-name/empty-pool shape, deterministic sort, digit gate.
