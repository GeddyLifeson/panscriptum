# The open queue at the end of run #37

Generated from `state/workorders.json` at the close of the shift. The queue itself is the authority; this is a snapshot so the next run can start from a position rather than rediscover one. Ranked by rung (cheapest handler first) and then by severity, then oldest first.

Total open: 286

### LOCAL — 22 open


**MAJOR (1)**

- `03c0fe609e89` — src/backfill.py:291-294 (main, the --audit branch) — backfill.main --audit prints `for x in rows[:26]` and then '... and N more'. That is the exact shape run #33 removed from pipeline.phase_write (refuse

**MINOR (18)**

- `596493b0b139` — b05 address_space.py:186, 216 — address_space.py:186, 216 — `citation_card()` and `seed_from_card()` are dead code
- `65e5735ba6dd` — src/pipeline.py:2214 len(named) — pipeline.py:2214 logs len(named), which now includes RETIRED records after the onomasticon was made append-only under order 9309a040f208 (closed this 
- `1ee5fa4e37f9` — src/verify_math.py:6443 — verify_math.py:6443 cites AUDIT_batch4.md by bare filename; the file actually lives at handoff/run35/AUDIT_batch4.md. Cosmetic, but it is the same cla
- `119ebee92481` — src/cascade_bridge.py _LOCAL_TRANSPORT — WinError 10055 -- 'an operation on a socket could not be performed because the system lacked sufficient buffer space' -- is not listed in _LOCAL_TRANS
- `7100890382fc` — src/ingest_doc.py mine() — mine()'s state['found'] counter is incremented in memory and persisted only through the resume-cursor write, so a denied cursor write silently detache
- `2928a0f9c314` — src/secondopinion.py module docstring (the `vulture` line) — the module docstring's vulture entry says 'Found `descending_ladder.py:129 from_m` and two others at 100% confidence'. Both halves have drifted: src/d
- `4a79b0e8a375` — src/pipeline.py:main (the `phases = [args.phase] if args.phase e — pipeline.main mishandles every out-of-range --phase value, in three different ways. (1) --phase 9: IMPLEMENTED.get(9) is None and the 'not implemented
- `37d3d588847a` — src/recover_folder_records.py:115-117 (main) — recover_folder_records.main does `mapped = source_map.get(name)` then `if not mapped: skipped_no_map.append(name)`. An empty LIST is falsy, so a sourc
- `4922a303e614` — src/ingest_doc.py main() provenance-write comment — The comment above the provenance write reads 'ADVANCE ON THE WRITE, NOT ON THE INTENT (same discipline this file argues for at 233-245 re: write_recor
- `d61b06dbe66d` — src/dashboard.py:77 — _num()'s handler calls silence.note('dashboard.py:73') from line 77 -- a line-number tag that has already drifted four lines, in the file that carries
- `6c24b2297f40` — src/retry_synthesis.py:225 — do_merge() counts records whose write_record refused, prints '<n> denied (write refused -- rerun the merge)', and then returns 0 unconditionally, so m
- `2b83e058be3f` — src/cleanup.py:195 — The thin-description branch sets e['thin_description'] = True and changed = True whether or not the flag is already there, so every subsequent --apply
- `a05eb35ebe4f` — src/verify_math.py:2426 — verify_math.py -- two module-level import aliases are rebound to a different module: _CB is cascade_bridge at :1712 and context_budget at :2426; PR is
- `af447d21d634` — src/verify_math.py:3108 — verify_math.py -- 11 of 15 mkdtemp/mktemp sites are never cleaned up (1248, 1353, 1394, 1911, 2046, 2087, 2919, 3108, 4269, 6317, 6322, 6847, 7082; on
- `a09a0e003c31` — src/verify_math.py:2349 — verify_math.py -- line-number citations have drifted, in a file whose own idiom (:3802-3804) is to cite by symbol or tag. (a) :2349 and :4407 both off
- `aaa4eb561cc0` — src/verify_math.py:4663 — verify_math.py:4662-4665 prints, every run, 'prose_gate.py:34 cites this one as 19s', and :4675-4679 says the corresponding prose_gate.py edit is stil
- `ba7b55d6465f` — src/verify_math.py:4487 — verify_math.py:4487-4490 still asserts 'every standard the checker declares actually emits a row' as a hardcoded len(...) >= 40 floor. Section 20k's o
- `49fb30ed12da` — src/compress_store.py store() denied-replace raise — store() correctly RAISES rather than reporting success when replace_retry is denied, and the message even names the leftover -- 'the temp file %s is s

**INFO (3)**

- `91bb70c85e31` — publish — publish exited to pick up changed source (src/ changed d69e633ff5648b04 -> f5adba04087caa22 and held for 615s)
- `e45618de083f` — foreman — foreman exited to pick up changed source (src/ changed da63c0b2ce88c94c -> d69e633ff5648b04 and held for 2746s)
- `ee382241ff8c` — overwatch — overwatch exited to pick up changed source (src/ changed d69e633ff5648b04 -> f5adba04087caa22 and held for 1402s)

### BOTS — 2 open


**MINOR (2)**

- `2da53c3e192f` — www.dandwiki.com — www.dandwiki.com: host unreachable: siteinfo returned nothing usable -- the API is not answering (present probe: 8 known-present title(s) all returned
- `3dc2832846bc` — - — stalled and deliberately NOT killed, because nothing would bring them back promptly: roll_auto:16752

### RUN — 192 open


**MAJOR (90)**

- `30854f11f322` — binding_health.py:310-355 — binding_health.binding_verdict (329-355) can return a false CONFIRMED at score 100 whenever the normalised sitename is a WORD-SUBSET of the normalised
- `f2271d9ee843` — src/publish.py prune_export / COPY_DIRS — prune_export only ever walks roots listed in COPY_DIRS, so REMOVING a root from that tuple leaves its entire export copy standing in the PUBLIC repo f
- `3b030216a138` — src/address.py spine_code_for() worded-containment branch — THE SAME HARD RULE 2 HAZARD AS ORDER 7f9a58566f91, ONE LEVEL UP AND STILL LIVE. That order fixed the token-overlap FALLBACK so a one-token index entry
- `8d14f0adda1b` — src/withdraw_chapters.py archive move — Two withdrawals sharing one --label archive collide: shutil.move onto an existing name in output/withdrawn_<label>/ silently OVERWRITES on Windows via
- `944274e8bfd8` — data/ENTITY_INDEX.json vs src/weave_index.py — THE CODE IS FIXED AND THE DATA IT PRODUCED IS STILL TRUNCATED. Order b974e9ed76de (closed this shift) removed weave_index's silent 400-character cap o
- `a3fd659f4ff7` — src/foreman.py reprove_pool() — foreman.reprove_pool() hand-rolls open(_pp + '.tmp', 'w') followed by replace_retry instead of routing through silence.write_json -- so it uses a FIXE
- `8f4bb64503c2` — src/drill.py:3133 — drill.py:3133 `_local_buckets_excluded_from_cloud_claims` is VACUOUS three ways. It requires only that SOME `if` in cascade_bridge.py has `<x>.bucket.
- `78f04bec15ad` — src/drill.py:2569,2813,3697,3727 — Four nets use the whole-file `_calls()` helper, which walks dead code, `orelse` and uncalled helpers (`_called_names` -> `_call_spellings(tree)` with 
- `7cc460706efe` — src/drill.py:1287,5086 — Two nets are pinned to the literal spelling of an import alias rather than to the module, so a rename of an import BREACHES the drill -- and a drill b
- `c54a22a4e6fc` — src/drill.py:1287,1301,1402 — Three local_agent nets accept a call or an assignment that the running program cannot reach. drill.py:1287 `_failed_revert_is_escalated` calls `_calls
- `18958aba2143` — src/drill.py:3091 — drill.py:3091 `_refusal_is_recorded` is two whole-file `ast.walk` searches with no branch scoping. Its `records` half is satisfied by ANY assignment w
- `9ada7602a356` — src/drill.py:1560 — drill.py:1560 'the cap resets per run, not per process' reads only `LA._BLAST['patches']`. `local_agent._BLAST` is {'files': set(), 'patches': 0} and 
- `64dfe6bec15c` — src/drill.py:3407 — drill.py:3407 reads cascade_bridge.py as TEXT and two nets test that text with `in`. 'burial is documented as permanent-codes-only' (drill.py:3409) is
- `5ed81099fc49` — src/drill.py:2764,5116 — Two nets assert 'there EXISTS a correctly-guarded site' where the property is 'EVERY site is guarded', so adding an ungated one restores the fault wit
- `e2f44baedfdc` — src/drill.py:1176 — drill.py:1176 `_halt_is_not_breakage` loops over ast.walk looking for `if idle >= IDLE_LIMIT`, runs its checks on the FIRST one it meets, and `return`
- `cf9ee9000be8` — src/drill.py:1608,4349 — drill.py:1608 `_no_programmatic_clear` ('No module in src/ CALLS the halt's release') and drill.py:4349 `_counts_decided_by_substring` ('NO gate anywh
- `5eea5c20db8a` — src/drill.py:5441 — drill.py:5441 `datasette_config_is_generated_not_copied` calls `corpus_db.datasette_metadata()` with no path, which WRITES state/datasette.json on eve
- `5c87268a388c` — src/drill.py:1986,2575,2591,2621,3407 — Five statements execute at area-function call time OUTSIDE any net() wrapper, so an exception in them is an uncaught traceback out of main()'s `for fn
- `6e1c72cddfeb` — src/resonance.py:119 — `resonance.hodge_decompose` reports eta = 0.0 -- '0% ladder-representable, 100% irreducibly chord, theorem_2_error_floor = 1.0' -- for contest flows t
- `1e86b06e7463` — src/silence.py:145 — The `"raise"` token in `silence._handlers` (src/silence.py:145) and in `silence.instrument` (src/silence.py:562) CAN NEVER MATCH A RE-RAISE. Both test
- `f194d8444d12` — src/foreman.py:924 — `foreman.restart_ollama`'s 30-minute rate limit FAILS OPEN, silently, on an unreadable stamp file. src/foreman.py:921-925 reads state/OLLAMA_RESTARTS.
- `4866dfb2d9fc` — src/pipeline.py:write_record (drift-branch field tuple) and src/ — both record writers' per-entry merge allowlist is ('category','scale_note','scale_note_rejected','magnitude','topic','catalogued') and omits 'excluded
- `99b1ae2c580c` — src/foreman.py:281 — `foreman.py` still hand-rolls SEVEN atomic writes with a FIXED `path + ".tmp"` name, in a process the code DELIBERATELY permits to run twice at once. 
- `881ff7f49438` — src/foreman.py:95 — `foreman.DENYLIST` (src/foreman.py:95) omits every module that constitutes Hard Rule -1's PROVEN property, and `_checks_pass` (src/foreman.py:1135-119
- `212e3096edfc` — src/prose_gate.py:section_shortfall (the `extra` branch) + asser — prose_gate.section_shortfall counts an INVENTED entry into `missing` but never into `required`, so assert_block_complete cannot refuse it. Each extra 
- `17e6cba194ce` — src/scout.py:_mutate — scout._mutate replaces a corrupt or wrong-shape shared JSON artifact with an almost-empty dict and reports landed=True. It takes silence.digest_of(pat
- `1ebd28c8cd85` — src/standards.py:check() -- the `ledger` block and the `unans_fi — Two standards in standards.check() report a clean ZERO off an input they could not read, because the out.append(_s(...)) sits OUTSIDE the try rather t
- `b901c088890e` — src/standards.py:check() -- the duplicate-process block (`_dup = — The 'one instance of each job' standard (HIGH, group machine) is the only outer handler in standards.check() that neither re-emits a row nor records _
- `d2085b1d8dd3` — src/escalation.py:escalate (the `level >= OWNER` arm) — escalation.escalate() throws away _raise_halt()'s return value: `if level >= OWNER: _raise_halt(rec)` then `return rec`. _raise_halt was fixed in run 
- `4b308c6b750d` — src/escalation.py:clear + escalation.py:main (--clear) — `python src/escalation.py --clear --ruling "..."` prints 'nothing was halted.' when the lift was REFUSED. escalation.clear() returns False for two ent
- `e16a93099bbe` — src/feats_index.py:host_to_sources, feats_index.py:load_index, f — feats_index swallows a failed host-map read, CACHES the emptiness, and thereby defeats the guard manifest_builder added for exactly this. host_to_sour
- `6434c1ba7b20` — src/catalog.py:64 — catalog.py's `stats` prints only the first 30 of the populated-sources-with-no-books roster (`for n in missing[:30]`), then '... and N more'. Measured
- `65ae84ee4bd7` — src/burgs.py:205 — burgs.main() accumulates per_world[w['designation']] = bs over WS.build_all(). `designation` is NOT unique: 5,940 worlds carry only 5,893 distinct des
- `47e4e1ace8f1` — src/burgs.py:207 — burgs.main() builds the FULL settlement roll for every world into memory unconditionally, before --write is consulted. Measured: burg_count summed ove
- `62f4b7caae73` — src/cascade_bridge.py:638 — _CLIENT_REJECTION = r'error code:\s*10\d\d|cloudflare|browser integrity|just a moment|attention required'. `cloudflare` is a bare alternative AND the 
- `1661efdee019` — src/cascade_bridge.py:1489 — Today's prove()/dead_forever repair is CORRECT in source -- verified offline against a synthetic proof file, 12 cases, 0 mismatches, both directions -
- `64e4db060ad6` — src/feats.py:resolve_hosts (the `if src in known: continue` guar — A FAILED host probe is cached permanently as 'this source has no wiki', and nothing ever re-probes it. `alive(h)` is `bool(api(host, {...}, retries=0)
- `75307186e12a` — src/weave_index.py:designations (the `except Exception:` arm tha — The failure path caches an EMPTY designation set against the LIVE corpus signature, so one transient read failure poisons entity identity for the rest
- `eacc5444288c` — src/feats.py:mine and src/feats.py:by_axis (both `if not (20 < l — Every text unit of 400 characters or more is discarded before the evidence gate ever sees it, with no counter anywhere and no entry in `gate_rejected`
- `8605c2ed6061` — src/resync_roll.py: the `if __name__ == '__main__': main()` line — A denied SWEEP_ROLL.json write exits 0. The write itself is correctly gated (`landed = silence.write_json(...)`) and the denial is correctly printed -
- `e959f566275d` — src/weave_index.py:build (`if not key or len(key) < 3 or key in  — Entries whose normalised key is shorter than three characters are excluded from ENTITY_INDEX.json ITSELF, not merely from cross-source candidate match
- `fc8e20f90ee9` — state/workorders.json (45 open orders); src/workorders.py file_o — The four field caps were removed from file_order today and the removal is genuinely complete -- I round-tripped a 3,018-char `what`, a 900-char `where
- `1b15acd3f7b2` — src/hostcheck.py:750,761,871,899,1007 (_land call sites) — hostcheck._land()'s own docstring (hostcheck.py:94-97) says 'THE VERDICT IS NOW RETURNED, because it was being discarded ... binding_health._land and 
- `7a6362fa3c91` — src/suppressions.py:98 — suppressions.add() stores the waiver's justification as 'reason': str(reason).strip()[:300] -- a silent, unmarked cap on STORED data, in the module wh
- `66e007cf54d5` — src/ingest_doc.py record_path() — ingest_doc.record_path()'s fallback matches a source to a record file with 'if want in base or base in want' -- bare substring containment, first matc
- `9a694b3ae227` — src/mutate.py:_mutations (the `swap` table under isinstance(node — mutate._mutations mutates only six of the ten ast.cmpop types (Lt Gt LtE GtE Eq NotEq) and only when len(node.ops) == 1, so `in`, `not in`, `is`, `is 
- `91c1a581453d` — src/mutate.py:run (base=None) -> _run_mutation (base = {} if bas — run()'s public signature defaults base=None; _run_mutation turns that into {}; the kill test is `if sig != base.get(gname)`. {}.get(name) is None and 
- `d2fb14ffa8c6` — src/mutate.py:_run_mutation (both gate loops) with _gate_result  — unusable_gates(base) refuses to mutate when a gate cannot complete on CLEAN code, and its docstring reasons carefully about TIMEOUT == TIMEOUT produci
- `90eba4982972` — src/custodes.py:convene -- `dispersive = sorted(...)` and out['d — The comment above this line claims the dispersive flag 'is now READ rather than merely declared... Deriving the list from the table means a second dis
- `a08557925d87` — src/tells.py:prompt_section (claims at tells.py docstring, style — tells.py's WHY ONE FILE section states 'the list lives here, the prompt section is GENERATED from it, and the audit imports it', style_audit.py:30 rep
- `302c7da84032` — src/overwatch.py:167 — overwatch.load() only treats an UNPARSEABLE ledger as damaged. A ledger that is valid JSON but not a ledger -- null, [], {}, or a bare string -- retur
- `c6f64c1424fa` — src/overwatch.py:559 — verify_open() writes f['last_verified'] = time.time() and increments `checked` BEFORE testing whether the model answered. _ask returns None on purpose
- `d316c46b67bd` — src/gpu_lane.py:326 — _take_slot() returns None for two different situations and lane() cannot tell them apart: 'every slot is live' (wait) and 'os.open raised, cannot arbi
- `9ef32bd37b95` — src/verify_math.py:7232 — verify_math.py:7232-7248 -- the section-tag uniqueness scan (20y) only reads '# ---- Section <tag>:' lines. 21 of the file's 62 section tags use a pri
- `b18acbb35760` — src/verify_math.py:4637 — verify_math.py:4637-4644 -- 'the live sweep proves its own completeness' asks sweep_plan.latest_run() and demands missing()==[]. latest_run() returns 
- `67c692701386` — src/verify_math.py:6166 — verify_math.py:6165-6172 -- the row enforcing order 495390283745 tests '_want_b3 in _selfsrc_b3' where _want_b3 is a plain literal that appears on its
- `6a8444cad673` — src/verify_math.py:5021 — verify_math.py:5020-5032 -- _nogate20q collects a phase's calls with ast.walk(_fn20q), which descends into nested defs, so a phase that lands artifact
- `469b4db261ef` — src/verify_math.py:2319 — verify_math.py -- seven rows assert a code string is PRESENT in a target module by searching the raw file text, and the target module carries that tok
- `66696f8ee28f` — src/magnitude.py:497 — magnitude.SYSTEM tells the model 'Cite, for each axis, the exact feat number that justifies it', while verify()'s guard 1 demands the citation MATCH a
- `41e8ffc2e490` — src/magnitude.py:1014 — Guard 5 (QUANTITY) never applies guard 3, and it OVERWRITES guard 3's refusals. quantity_scores() (magnitude.py:421) does not call subject_refusal at 
- `dd76d4a930f7` — src/magnitude.py:974 — The one-shot quality-failure retry at magnitude.py:974 (`if not sheet and any(cand.values())`) can essentially never fire, so the Jace case it was wri
- `14bd09740627` — src/allsweep.py:598 — The VERIFY tier's verdicts are computed, printed, landed in ALLSWEEP.json and graded by nothing. allsweep.main()'s `bad` sum counts only `crashed` or 
- `2a48315d26e6` — src/sevenfold.py:138 — sevenfold.seams()'s even-split fallback -- added because clustering all six cuts at one end 'produced exactly the giant component this function's own 
- `237356c82d06` — src/anchors.py:242 — anchors.run() computes an ASSAY, an INSTRUMENT reading, a COLLEGE interval and a bit-value for each of the five anchors, prints them all, and gates th
- `3778bc42499f` — src/publish.py push() — publish.push() returns False ('nothing to send') when the export branch is AHEAD of origin/main. The no-op test is `if not porcelain: return False` on
- `d2edc81326da` — src/publish.py sync_tree() COPY_FILES branch — sync_tree's COPY_FILES withdrawal deletes the export copy on the strength of ONE os.path.exists answer, and has none of prune_export's guards. (1) os.
- `dd3ff361db49` — src/binding_health.py _load / quarantined / quarantine — _load returns the same default for FileNotFoundError and for every other exception, so a torn, locked or non-UTF-8 HOST_QUARANTINE.json reads as 'no h
- `9979963c093a` — src/binding_health.py run() — run() lands an EMPTY whole-estate report when WIKI_HOSTS.json cannot be read. hosts_map = _load(WIKI_HOSTS.json, {}) -> {} -> hosts=[] -> out=[] -> me
- `a29c38c9eff3` — src/binding_health.py run() -- release(h) call sites — release()'s NOT-RELEASED verdict is thrown away at both of its call sites. release() was rewritten today so a lost compare-and-swap returns 'NOT RELEA
- `6d35eacf252d` — src/chain.py extract() / _ask() — extract() cannot tell 'the model answered with no contests' from 'no model answered'. _ask returns None when the cascade bridge AND the local model bo
- `6447bcc2f18c` — src/rosetta.py main() --mine / scales_for() — --mine writes the SAME pass output to both ROSETTA.json and ROSETTA.raw.json, so the 'raw' copy is not a backup of the previous mine but a second copy
- `22394233dbad` — src/withdraw_chapters.py main() -- the `missing` branch — An entry whose file could not be STATTED loses its catalog record. `if not src or not os.path.exists(src): missing += 1; continue` does NOT add the ad
- `0b75182d495c` — data/records/*.json done.entrypass vs the entries on disk — THE CODE IS FIXED AND THE DATA IT LOST IS STILL LOST. Order 9ef51c36acea (closed this shift) repaired pipeline.write_record's no-drift branch, which d
- `776507b529c5` — the run-36 red-check for pipeline.write_record's top-key merge — THE CHECK THAT GUARDED THE CHANGE COULD NOT SEE WHAT THE CHANGE BROKE, and that is the more important half of order 9ef51c36acea. The run-36 top-key r
- `6e0127c4f3ed` — src/local_agent.py:_safe (junction block) and _denied_region — local_agent._safe re-checks a junction-resolved path against DENYLIST_PREFIXES ONLY (via _denied_region) and never against DENYLIST_PATHS, so config.y
- `838be29f9e58` — src/codewatch.py:stale (the _PENDING comparison) and STABLE_SECO — REFINES ff3c67a67b92 rather than restating it, and the refinement changes the remedy. codewatch.stale() compares the current digest against _PENDING['
- `1f172f5acc6f` — src/drill.py:drill_codewatch.daemons_actually_check_their_own_so — codewatch's docstring and CLAUDE.md both say it gives EVERY standing daemon a fingerprint of src/. Only three modules call it. Six long-lived jobs are
- `4c1eaa9df7fa` — src/overnight.py:1021,1027,1040,1046,1053,1068,1070,1081,1103 (g — overnight.py honours a MANAGER (rung 4) subsystem stop in ONE of the ten places it launches jobs. `_manager_stopped()` (overnight.py:867) has exactly 
- `a37032c3f36a` — src/overnight.py:720-734 — overnight.coverage_snapshot() (overnight.py:720-734) runs coverage.py with subprocess.run and DISCARDS the return code, then json.loads data/COVERAGE.
- `6761a8e56280` — src/overnight.py:737-761 — overnight.preflight() (overnight.py:737-761) never inspects health.py's return code. Its except arm -- added run #19 with the explicit promise 'it no 
- `372168774ee7` — src/manifest_builder.py:460-473 (filtered at 437-441) — manifest_builder.main() builds `series_members` (line 460-465) from `build_pool`, which lines 437-441 have ALREADY narrowed by --only or --pilot. So v
- `ab820740fb85` — src/policy.py:211-218 — policy.EVIDENCE_RULES (policy.py:211-218) has ZERO consumers anywhere in src/. `grep -rn 'EVIDENCE_RULES' src/*.py` returns only its own definition; p
- `c812e8db852f` — src/read.py:1029-1030 (against src/cachekey.py docstring section — cachekey.py's module docstring section 3 ('ONE HELPER, NOT FOUR SPELLINGS ... A rule applied at some of its sites is not applied (standing lesson 14)'
- `4f02ea2d7ecd` — src/read.py:738-739 (read_entity) and src/read.py:1238 (--chunks — read_entity(cap_chunks=N) slices the density-ranked chunk list -- chunks = chunks[:cap_chunks] -- and the partial read it produces is then written to 
- `7bffb5634d7a` — src/thread_integrity.py classify() -- the `back = (b, a) in reco — classify() dedupes to one direction per unordered pair (`if (b, a) in seen or (a, b) in seen: continue`) and then asks only `back = (b, a) in recorded
- `fa2c96a63fe7` — src/compress_store.py load() — A CONTENT-ADDRESSED STORE WHOSE LOADER NEVER CHECKS THE ADDRESS. content_hash() computes sha256(text)[:32] and that hash NAMES the file, but load(path
- `d770b1896635` — src/health.py:150,210 (_flush_ledger) and src/health.py:218,264  — health._flush_ledger (src/health.py:150) and health._flush_samples (src/health.py:218) read state/failures.json, merge their snapshot into it, and wri
- `209391b4f990` — src/liveness.py:142 (_defs) and src/liveness.py:169 (scan) — liveness.scan()'s DEAD pass is per-symbol and can therefore never see (a) a whole module nothing imports, or (b) a class nothing instantiates -- and d
- `0924f1b5af2f` — src/catalogue_web.py:122 (save_roll) — catalogue_web.save_roll (src/catalogue_web.py:122) writes through a FIXED `SWEEP_ROLL.json.tmp`, shared by every process that writes the roll. It is t
- `bee9d16f4174` — src/autostart.py:236,262 (watch) — autostart.watch() (src/autostart.py:236) is a bare `while True:` at autostart.py:262 with a 180s sleep and NO codewatch staleness check -- and it is t

**MINOR (102)**

- `5d14e90b5043` — src/overnight.py:842 — overnight.py:842 run("pipeline", ...) is effectively unreachable work. pipeline is a member of STANDING (line 421), is started backgrounded at line 80
- `c421410c2194` — entity_match.py — entity_match.py:276 embed_available() has no caller anywhere in src/ -- confirmed via liveness.scan() (only hit under dead was entity_match.py:276 emb
- `ad681057369a` — src/worldseed.py size lookup — The 'primitive': 35 entry is unreachable: f['tech'] can never take that value. Confirmed, and it is a vocabulary entry that silently describes a world
- `e14c1f1c494e` — src/publish.py ensure_site vs _is_skipped — ensure_site writes '*.presilence' into the export .gitignore, while _is_skipped matches the whole '.pre*' family by shape. A hand-placed .preNNN file 
- `01a479a891a5` — src/drill.py _suppressed_still_visible — drill._suppressed_still_visible calls publish.scan_for_secrets(HERE) against the whole ~4.3 GB project tree and did not finish in four minutes when me
- `d19d705925e3` — src/binding_health.py run() merge-unreadable branch — run()'s unreadable-standing-report branch also lands nothing but still only prints and calls silence.note. It is the THIRD write-not-landed path in th
- `cdcb11e3d7fa` — src/binding_health.py run() -> canary() -> rec['present']['title — run() passes the LIST returned by known_present_titles into canary(h, title), and it is stored as rec['present']['title'] -- so a report field named '
- `18a2053bc62d` — src/binding_health.py binding_verdict() max(scored) — binding_verdict picks the best source with max(scored) over (score, name) tuples, so equal scores are broken by ALPHABETICAL source name and 'matched'
- `ded8418c75a6` — src/custodes.py convene() early return on len(readings) < 2 — convene()'s early return for fewer than two readings yields only {decimal, reason}, so it carries none of the measured-flags added this shift (stalene
- `77d59411ca75` — src/cascade_bridge.py try_disabled() — try_disabled() has the IDENTICAL isolation defect just repaired in prove() under order c810cf64d278: it flips m.enabled = True and pins the model, but
- `b44cdf75a80e` — handoff/run35/checks_L4.py address_space.py silence.note asserti — checks_L4.py asserts that address_space.py contains EXACTLY 4 silence.note tags, so any legitimate NEW note tag in that file fails the battery. It fir
- `64c8827cc72b` — src/drill.py:2591 — drill.py:2591 takes `_empty_before = set(os.listdir(SNAP.ROOT))`, runs one net(), then rmtree()s EVERY directory that appeared in the interval (drill.
- `f3536eed6ce0` — handoff/pipeline_merge_redcheck.py:ENTRIES / run_all — handoff/pipeline_merge_redcheck.py certifies the run #36 write_record top-key fix using ENTRIES = [{'name': 'Alpha'}, {'name': 'Beta'}] -- entries tha
- `c426af1de74f` — src/standards.py:check() -- the `hand-built assays match the cha — The HIGH standard 'hand-built assays match the charter' holds on an empty file. The predicate is `inside >= len(refs) if refs else True`, which parses
- `b8686a5c9772` — src/standards.py:check() -- the `if read` / `if roll` / `if cov` — Eight standards in standards.check() are emitted under a plain conditional with no _dropped record, so they can disappear from the page while 'every s
- `1def9a6ce0d5` — src/standards.py:check() -- the job-advance loop (`standards.py: — Inside standards.check()'s job-advance loop, two handlers silently remove a job from the stall watch instead of reporting it unmeasurable: `except Exc
- `dddf4d96bb3e` — src/standards.py:check() -- the `served = next(...)` line feedin — The HIGH standard 'the resident runner serves the context this project asks for' reads the served window off whichever model /api/ps happens to list F
- `e8cd908ce5e4` — src/prose_gate.py:assert_block_complete, src/scout.py:sweep, sco — Caps on fields a person reads to act, all verified in source, in the two modules of this batch that carry them. (1) prose_gate.assert_block_complete r
- `7f2cbf26a60e` — src/scout.py:_ask and scout.py:scout — scout._ask returns None for EVERY exception (`except Exception: silence.note('scout.py:_ask'); return None`), and scout() then returns {'source':..., 
- `0e8ef2e30f2b` — src/catalogue_codex.py:main and its __main__ guard — catalogue_codex.main() returns None and the module ends `if __name__ == '__main__': main()` with no sys.exit, so a DENIED SWEEP_ROLL.json write exits 
- `5da00dda2c8e` — src/catalogue_codex.py:main (the sec_by_norm fallback scan) — catalogue_codex.main() binds a roll source to a codex section by a BIDIRECTIONAL substring scan that breaks on the first hit in codex-file order: `for
- `fdebedb8d0ce` — src/cascade_bridge.py:1563 — prove()'s belt-and-braces cross-check is `if verdict == 'answers' and by and by != bucket`, where `by = str(served.get('bucket') or '')` and served['b
- `3b37494e20db` — src/build_terminal.py:471 — build_terminal.py's template carries the comment 'Every catalogue-derived string goes through this before it reaches innerHTML' (the esc() helper, BUG
- `9d24c8a5febf` — src/pantheon.py:308 — pantheon.main()'s --full view prints each axis as `d['cited'][:58]`. Measured: 54 of the 66 axis citations are cut; the longest (Vados, acumen) is 294
- `328c1dd39f3d` — src/identity.py:364 — identity.py carries two citations into chain.py by LINE NUMBER; both have drifted and one now asserts something false. (1) line 364: 'chain.py:422 is 
- `2583671339d2` — src/silence.py:404 — `silence.write_json` silently OVERRIDES a caller's request for compact output. src/silence.py:404 does `dump_kw.setdefault("indent", 1)` before the du
- `e5001f0b0153` — src/onomast.py:441 — `onomast.name_worlds` flags a world's designation `retired` while the world is STILL LIVE in `resolved` and still carries that designation. src/onomas
- `87795c671285` — src/navtree.py:67 — All three `silence.note` call sites in `navtree.py` cite a LINE NUMBER, and all three have DRIFTED off the handler they name. The house idiom everywhe
- `89fc2eaf23f1` — src/resonance.py:194 — FIVE printed lists in this batch are truncated, and four of the five say nothing about what was cut. Hard Rule 0's stated shape is 'a cap does not fai
- `9803b72711b3` — src/foreman.py:344 — THREE SHAPES VERIFIED AS PRESENT BUT NOT CURRENTLY CAUSING HARM. Filed together at MINOR so they are on the record without being reported as live faul
- `2cbb690f65a4` — src/coverage.py:71 — `coverage._so_load`'s silence exemption claims a narrower cause than the handler actually covers. src/coverage.py:71-72 is `except Exception:` with th
- `09a410dc7457` — src/feats.py:resolve_title (the api() call carrying srlimit=8) — resolve_title asks the wiki for 8 search hits and follows no continuation, so the candidate list it ranks over is truncated by us at 8. discover() was
- `abe49b3ba7b3` — src/feats.py:evidence_for (`plain = bool(host) and host.startswi — A `pages:` host with registered URLs is NOT a wiki -- reads_as_wiki says so, and page_looks_real correctly drops its wiki-markup layer for it -- but t
- `74b37b4c6c3a` — src/generate.py: the `with open(raw_path, 'w', encoding='utf-8') — The raw chapter write is a bare truncate-then-fill outside any handler, three lines above a try/except that exists for the identical failure. Its own 
- `b3c806f694d6` — src/generate.py: the six `failures[job['address']] = {...}` site — A chapter that failed once and succeeded later stays in output/index/failures.json for ever, so a dead refusal is indistinguishable from a live one. T
- `2ab24aeb63f7` — src/resync_roll.py: main()'s `if r.get('entry_count', 0) != n:`  — Two ways this script reports agreement it has not established. (1) The status repair added for the entry_count==0/status==catalogued pair sits INSIDE 
- `ad6496327a94` — src/rigor.py: the docstring citation `tempus.py:182-186` in meas — The citation names the wrong function. tempus.py:182-186 is the closing paragraph of rung_description_length's docstring ('This is not a new scale...'
- `baf4a18d1f1a` — src/ingest_doc.py mine() fresh-entry construction — mine() stores each extracted entity as 'description': (e.get('description') or '').strip()[:2000] -- a silent unmarked cap on STORED catalogue data, i
- `e6385a07a3fd` — src/workorders.py sweep_detectors: LEDGER_STRUCTURE, LEDGER_CHAI — The caps removed from file_order today survive one layer up, in the detectors that COMPOSE the `what` text. The module already knows the right shape a
- `4ff1db780b99` — src/hostcheck.py null_rate() cache key — Today's fix keyed _NULL_CACHE by (host, exclude, sample) for the right reason: those are part of the question the function answers. `by` is the same k
- `e2f0b13c766f` — src/hostcheck.py sweep() repair loop, candidate selection — sweep(--repair) selects a replacement host by RAW HIT RATE: best = (0.0, None); 'if ok and p["rate"] is not None and p["rate"] > best[0]'; early exit 
- `afd7aa05efb4` — src/ingest_doc.py main() --mine branch — main() does 'if a.mine: mine(a.source)' and then 'return 0' unconditionally, discarding mine()'s return value. mine() returns True ONLY when every chu
- `7059872ef2b7` — src/mutate.py:_mutations, the ast.BoolOp branch, `if not found_a — In the BoolOp branch each adjacent pair of values is skipped when the left operand's end_lineno differs from the right operand's lineno. The whole-lin
- `0aefdac4a26d` — src/custodes.py:_custos_reading -- ATTESTATION_QUALITY.get(attes — An attestation string outside the charter's five grades silently reads as a mid-quality grade (0.4) and a number is published; nothing in the returned
- `39f19f7e646c` — src/custodes.py:_custos_reading -- evidential_part = tilt * evid — The evidential term is a multiple of `tilt`, so a Custos whose tilt is 0.0 has no response to attestation quality no matter what evidence_sensitivity 
- `b6474eb0a258` — src/address_space.py:assign -- fit(): `% (1 << WIDTHS[field])` — pack()'s docstring promises 'Raises rather than truncating: a silently wrapped address would name a different world, which is the one failure mode wor
- `ca3452eb9d49` — src/snapshot.py:_rel and before() (src = p if os.path.isabs(p) e — _rel() is os.path.relpath(p, HERE) with no containment check, so an absolute path outside the repository yields a relative beginning '../'. before() j
- `f4193095edff` — src/snapshot.py:before -- `if not os.path.exists(src): continue` — before() refuses only when NOTHING was captured. A snapshot asked for several paths where one is a typo, a renamed directory, or a path not yet create
- `33ba82dab55c` — src/wiki_source.py:clean_titles -- `if t not in out:` against a  — clean_titles dedups with a linear membership test against the list it is building, so the cost is O(n^2). Measured on this machine: n=2,000 -> 0.032s;
- `f42c55355431` — src/sweep_plan.py:45 — modules() globs src/*.py non-recursively while its docstring says 'Every module in src/, NO exclusions, deliberately'. src/deprecated/catalogue_local.
- `6794cb447987` — src/sweep_plan.py:226 — The aggregate-write fallback in record() opens and json.dumps its temp file OUTSIDE any try (lines 226-228); only the os.replace below it was routed t
- `e8e095597f74` — src/overwatch.py:654 — write_report() lists open findings [:40] with no 'and N more' line, under a header that states the true count -- plus broken[:4] at :628 and corrupt[:
- `97373afb2d5b` — src/overwatch.py:747 — round_once() builds its module list as [m for m in A.modules() if not m.startswith('_') and m not in ('overwatch', 'allsweep')] with no comment saying
- `62286a6c018a` — src/dashboard.py:396 — movement()'s corrupt-history repair (the run #26 fix at :369-392) checks that the file parses and that it is a list, but not that its ELEMENTS are dic
- `dbc2937118da` — src/verify_math.py:5141 — verify_math.py:5140-5143 -- the positive control 'and it still SCORES a well-formed quantity (the refusals are not blanket)' reads '_ax_valid is None 
- `8389720500a9` — src/verify_math.py:4646 — verify_math.py:4646-4653 -- 'an UNMEASURED fabrication guard does not read as green' collects r['holds'] for every UNMEASURED row and requires []. An 
- `d4a18a25f780` — src/magnitude.py:1006 — The cross-axis citation check at magnitude.py:1004-1009 matches `^\s*\[(\d+)\]` against the model's citation, but only compose() labels evidence with 
- `8f14aff37392` — src/magnitude.py:965 — An anchor the model returns that is not on the ladder becomes a published 'M0' on the one-shot and local paths (magnitude.py:965, `anchor = got.get('a
- `7c9d763fa17c` — src/estate.py:252 — estate.charter()'s erratum rows report 'X is a rung with no Magnitude band' whenever the word X appears anywhere in the charter text -- `for rung in (
- `3e65dbed45a6` — src/sevenfold.py:322 — sevenfold.main() gates its write on silence.write_json's verdict and prints 'WRITE DENIED: {p} did not land; rerun to retry' -- and then returns 0. An
- `1618d9790f0d` — src/anchors.py:242 — The one invariant anchors.py grades runs over the five names hardcoded in the local `order` list, not over ANCHORS. An anchor added to ANCHORS and not
- `b1147f53971e` — src/publish.py _scrub() — _scrub walks values only -- `{k: _scrub(v) for k, v in obj.items()}` -- so a credential sitting in a dictionary KEY passes through untouched. The modu
- `3d1efe60b4cf` — src/publish.py render_page() — render_page rewrites the published page with three exact-literal .replace() calls against dashboard.PAGE and never checks that any of them fired. All 
- `df572f47255f` — src/publish.py scan_for_secrets() — Suppressed findings are reported under `rel_for_supp` (forward slashes) while real findings are reported under `rel` (os.sep), so one refusal message 
- `d56228616f9c` — src/publish.py main() sync_tree -> push ordering — The mutation interlock is asked at PUSH time, after sync_tree has already copied src/ into the export. A mutation run that begins after sync_tree star
- `6c5faf62b2c6` — src/binding_health.py run() -- doc construction — `doc = {'at':..., 'checked': len(merged), 'failed': failed, 'hosts': merged}`. On a --host/--limit pass `merged` is the whole estate while `failed` wa
- `5e2aaac58753` — src/binding_health.py run() -- the `if not title` branch — `title = known_present_titles(h, hosts_map); if not title: out.append({...'reason': 'no catalogued entry to probe with'}); continue` -- the continue j
- `29dde10c569c` — src/chain.py extract() -- local_unmatched[side[:40]] — The `unmatched` roster's identity key is `side[:40]`, a 40-character truncation of the name, and write_result PERSISTS that roster into data/CHAIN.jso
- `679368768c02` — src/chain.py adjudicate_mutuals() — The split condition is `if ea != eb`, which is TRUE when one side dates itself and the other does not (None != 'X'). The pair is then split, and `if n
- `b9c013a041db` — src/chain.py harvest() — glob.glob returns [] for a missing or unmountable directory rather than raising, so if data/feats or data/readfeats is momentarily unavailable, `live`
- `f045ffe20c52` — src/rosetta.py ordinal_rows() — ordinal_rows finds tier matches in `low = wikitext.lower()` and then slices the ORIGINAL with those offsets: `seg = wikitext[max(0, m.start() - 160):m
- `0bba50a6d76b` — src/rosetta.py check() / spearman() — check() builds `a_by = {_norm(k): v for k, v in assays.items()}` -- one GLOBAL map, no host scoping -- and then looks up every scale row in it regardl
- `13f18179d05f` — src/worldseed.py:256,264 — Both silence.note tags in this module cite LINE NUMBERS and both have drifted: silence.note('worldseed.py:248') now sits at line 256, and silence.note
- `ef19733afaa7` — src/worldseed.py build_all() — An unreadable ONOMASTICON.json gives `ono = {}` -> `reg_by_group = {}` -> `reg_by_group.get(g, 'classical')` for EVERY world -> CULTURE_SET['classical
- `8b86e70ce8b7` — src/worldseed.py main() --write — `payload = {w['designation']: {'address': address(w), **w} for w in worlds}` with `designation = f'{src}::{nm}'`. Two catalogued Places in one source 
- `1687ff8084b9` — src/withdraw_chapters.py main() -- per-entry raw/compressed loop — raw_path and compressed_path are moved independently inside one entry. If the first succeeds and the second raises, `stuck.add(_addr)` keeps the WHOLE
- `c8ac7dbab3c5` — src/withdraw_chapters.py main() -- the empty-selection refusal — A --addr that matches nothing is silently ignored whenever any OTHER selector matched. The refusal ('NAMING SOMETHING AND WITHDRAWING NOTHING IS A TYP
- `7909342fefa4` — src/physics.py kinetic() — kinetic() accepts a NaN speed and returns NaN with no exception: abs(nan) is nan, `nan >= C` is False, `nan < RELATIVISTIC_ABOVE * C` is False, so it 
- `4965e049c8fb` — src/canon_backup.py:prune — canon_backup.prune() catches OSError around os.remove, calls silence.note('canon_backup.py:prune-denied:...'), and then falls through to removed.appen
- `b6d5f70a7f19` — src/canon_backup.py:verify — canon_backup.verify() returns ok=True when no .manifest.json sits beside the snapshot. `recorded` stays {}, so `changed` is empty by construction, and
- `72bc85d74ccf` — src/derivation.py:check_graph and src/derivation.py:scan_constan — Two gaps in derivation's own checking, both in the module whose docstring says the taxonomy 'is the point' and that 'the checker below enforces it two
- `deeb24037ede` — src/local_agent.py:_gates (import gate) and src/local_agent.py:t — Three accuracy defects on the lane a model writes through. (1) _gates' IMPORT GATE CHECKS A DIFFERENT FILE for any .py outside src/: modname is os.pat
- `be783948fd66` — src/cosmography.py:kardashev_to_magnitude and src/cosmography.py — Two in cosmography. (1) kardashev_to_magnitude cannot report 'below the ladder': reached = ladder[0] before the loop and the loop only ever raises it,
- `08c1b6828384` — src/chord_field.py:G_NEWTON, HBAR; src/derivation.py LEDGER['bet — (1) chord_field.G_NEWTON and chord_field.HBAR are assigned and referenced ZERO times in the file (C_LIGHT once in recoil_momentum, K_BOLTZMANN once in
- `abd06525b40b` — state/workorders.json order f883d9bb534e; src/codewatch.py:twins — Order f883d9bb534e (MINOR, sweep34-batch03) describes codewatch.py:109 twins() doing 'me = os.getpid() if exclude_pid is None else exclude_pid', so th
- `b66a8b1acf50` — src/overnight.py:789 — overnight.safety_drill() (overnight.py:789) has exactly one breach branch, `if r.returncode == 1:`. drill.py exiting 2 (argparse), or with a Windows N
- `3fdf445e7c0d` — src/overnight.py:798-822 — overnight.write_status() (overnight.py:798-822) does open(STATUS.md, 'w') and then ~20 sequential f.write() calls -- the m6 truncate-before-serialise 
- `3cc35f54b235` — src/catalogue_aurora.py:286 (and main() 186-282) — catalogue_aurora.main() returns None and the module ends `if __name__ == '__main__': main()` with no sys.exit, so the process exits 0 in every case --
- `ac55ed089e96` — src/tuning.py:215-223 — tuning.regime() caches its verdict for RECHECK_SECONDS (180s), but tuning.profile() (tuning.py:215-223) then calls _answering_buckets() again, uncondi
- `543cec75ad02` — src/weave.py filtered_index() -- _STATBLOCK.search(desc[:400]) / — filtered_index() drops mechanics by searching only the first 300 characters of a description for rules voice (and the first 400 for a stat block). Rul
- `8c3d5e9aac87` — src/read.py queue() -- the inline os.path.join(FF.CACHE, re.sub( — queue() builds the per-entity evidence cache path by hand instead of through cachekey, which is the one helper that exists to be the single spelling o
- `25266fa8c2dc` — src/corpus_db.py rebuild() -- the `try: code = _spine_for(src) e — `code = None` is initialised, the resolver is called in a try/except that only silence.note()s, and the very next line's comment states the contract t
- `b66146e38fb5` — src/corpus_db.py -- meta.evidence_included written in rebuild(), — rebuild() writes meta.evidence_included explicitly so the caveat 'travels WITH the index, not only in the rebuild's stdout' and is available to 'any l
- `6160ef68b229` — src/corpus_db.py main() -- the row renderer's str(v)[:40] — Every printed cell is cut at 40 characters with nothing to say it was cut. Verified against the live index: 'Who Framed Roger Rabbit (incl. all conten
- `418e83501f0f` — src/ledger_guard.py main() — `python src/ledger_guard.py` calls check_all() and, on an empty result, prints 'ledgers: all intact' and returns 0. It never calls verify_chain() and 
- `6f95694b8143` — src/read.py _ask_ungated() -- the second `_FELL_BACK[0] += 1`, a — After the backoff ladder and the `if _TRANSPORT == 'cascade': return None` guard, `_FELL_BACK[0] += 1` fires unconditionally and control then falls to
- `08c1fd3932a4` — src/lognames.py OWNER: PIPELINE and SWEEP — THIS FILE'S OWN RULE IS BROKEN BY TWO OF ITS OWN SIX ENTRIES. The comment above OWNER states it plainly: a fragment 'must be specific enough to distin
- `34cf5b961af1` — the run-37 sweep dispatch (batches 08 and 15) — THE COORDINATOR'S OWN BRIEFS LOST TWO MODULES AND ONLY missing() NOTICED. sweep_plan.batches(16) put 9 modules in batch 08 and 9 in batch 15; the brie
- `a6764f7d3d3e` — src/health.py:467 (check_caches) — health.check_caches (src/health.py:467) tests cache emptiness over `files[:200]` and then reports 'all {n} sampled entries empty' with n = min(len(fil
- `8b74d2b4f569` — src/assay.py:843 and src/assay.py:877 — Two asymmetries in assay.assay(), both demonstrated. (1) src/assay.py:843 divides by `wsum` with no guard, three lines above src/assay.py:864's `denom
- `5f99aa19c059` — src/assay.py:941 (instrument) — assay._check_scores -- the module's own 'LAYER 1' -- is called from assay() only. assay.instrument() (src/assay.py:941) is a public entry that takes a
- `0a5019b2527e` — src/catalogue_web.py:351 — src/catalogue_web.py:351 derives every entry's stored `type` field with `cats[0].rstrip('s')`. str.rstrip(chars) removes a SET of characters, not a su

### SESSION — 2 open


**BLOCKING (1)**

- `70dd3d8b9d99` — - — publish refused: 2 credential-shaped value(s) staged for the PUBLIC repo. First: handoff\sweep37\file_batch14_orders.py:222 (vendor pattern)

**MINOR (1)**

- `ddb5eadd8934` — src/escalation.py:resume_subsystem (vs escalation.py:clear / _by — escalation.resume_subsystem lifts a MANAGER (rung 4) stop with nothing but a 20-character string: `if not (ruling or '').strip() or len(str(ruling).st

### OWNER — 68 open


**MAJOR (36)**

- `f84cb75edcfe` — data/WIKI_HOSTS.json: 'Prime World Equipment' — prime.fandom.com is bound to the source 'Prime World Equipment' but SERVES THE PRIME HYDRATION DRINK WIKI. Measured this shift: siteinfo on prime.fand
- `f07b7d538ed1` — data/WIKI_HOSTS.json: 'Star Realms' — starrealms.fandom.com is bound to the source 'Star Realms' but SERVES 'The Brain World Wikia' -- measured this shift, siteinfo HTTP 200, sitename 'The
- `9a44b1535851` — src/recover_folder_records.py:145-148 — recover_folder_records writes data/records/<slug>.json through silence.write_json rather than pipeline.write_record_catalogue, which is the project's 
- `60dc7c624c06` — data/TIERS.json vs src/address_space.py — address_space.py states the charting is '168 multiverses -> 8 metaverses -> 6 xenoverses -> 1 hyperverse, strictly nested, zero containment violations
- `9fb8a6b10c1f` — src/cascade_bridge.py live call — cascade_bridge has NO reachable model left, so allsweep grades it a bad subsystem every run. Measured this shift: every cloud provider in the roster r
- `66f96febdb3a` — src/descending_ladder.py:1 — descending_ladder.py has no functional consumers anywhere in src/. Excluding the file itself, grep for descending_ladder|DESCENDING|rung_for_length|sh
- `aad11acb1183` — src/dashboard.py:968 — dashboard.py:968 calls escalation.assert_clear in main(), so the ONE instrument built to display a standing halt refuses to start while a halt stands.
- `b1f561587b19` — src/prose_gate.py:249 — prose_gate.py:246-253 + 259-269 REPORT ONLY, DO NOT ACT WITHOUT THE OWNER. The 'entries the manifest never asked for' penalty never reaches the verdic
- `642a95fe9f3c` — src/address_space.py:275-276 — address_space.assign()'s fit() maps a None or missing tier to 0 with no marker, so a source the weave never charted is published at H0/X0/Mt.0 -- indi
- `789f99f2a65f` — src/tiers.py:309 — tiers.py:309 prints 'hyperverse: DECLINED for all 209 shelves' in the same main() that assigns a hyperverse index per source (chart(), 260-267), print
- `b317ba3a4f36` — data/GENRES.json — genre.py's truncated-denominator bug was FIXED in code this shift, but the stored classifications were deliberately NOT re-derived, because doing so m
- `3eff62be6cc3` — data/GROUNDINGS.json — grounding.py carries the IDENTICAL truncated-denominator defect as genre.py -- confirmed this shift: classify_text(top=3) over 5 GROUNDINGS, confidenc
- `7ebac78494e8` — machine DNS/resolver, not src/ — Four cloud buckets -- deepinfra:free, huggingface:free, cerebras:free, chutes:free -- all fail with `transport: curl: (6) Could not resolve host: <hos
- `4e7f1e47d0a0` — src/autostart.py keeper vs a MANAGER-rung stop — A MAINTENANCE RUN CANNOT DURABLY STOP A STANDING JOB, and this shift proved it on the worst possible example. At 22:5x this run stopped catalogue_web 
- `e9ff72c7eb48` — data/ASSAYS.json vs magnitude.subject_refusal — magnitude.py:335 Guard 3 -- "the entity must be the DOER" -- NEVER READ THE ENTITY. Proved by AST: verify(entity, got, ev) took the argument and refer
- `c614f7c145fc` — state/HALT.json cleared_by=owner-cli at 2026-08-26 00:55:07 — THE HALT WAS LIFTED AT 00:55 BY SOMETHING AUTOMATED, NOT BY A PERSON, AND YOU SHOULD KNOW THAT BEFORE YOU READ ANYTHING ELSE THIS RUN DID. Raised 22:1
- `1b7f14efce8e` — prime.fandom.com — prime.fandom.com is bound to 'Prime World Equipment' but SERVES 'Prime Hydration Wiki' (name agreement 50.0%). The catalogued entry names may be perfe
- `2d6bef2aef03` — starrealms.fandom.com — starrealms.fandom.com is bound to 'Star Realms' but SERVES 'The Brain World Wikia' (name agreement 36.36363636363637%). The catalogued entry names may
- `505177847f43` — localhost:11434 — THE LOCAL RUNG IS EFFECTIVELY CLOSED AND THE CAUSE IS NOT PANSCRIPTUM. Measured 2026-08-26: a non-Panscriptum process -- pythonw.exe pid 11468, comman
- `ae25c89f0179` — onomast.py:311-334,385 — onomast.register_for()'s documented genre+feature blend (FEATURE_SHIFT/GENRE_WEIGHT/FEATURE_WEIGHT, lines 278-334) is unreachable from the only produc
- `3fb312a72435` — hosts.py — src/hosts.py is a finished, working, self-consistent module (docstring: sources should be read from MORE than one host) with NO caller anywhere in the
- `3fb9fc6b9999` — ledger.py — src/ledger.py (De Pretio, the omniversal currency standard) is fully built and internally tested (verify_math.py lines 266-284 exercise to_standards, 
- `a8464e348c5e` — localhost:11434 — THE READ PASS IS RUNNING AT AN ETA OF ROUGHLY 1.7 YEARS AND THE CAUSE IS NOT IN THIS LIBRARY. Reported live 2026-08-27: read.py --run had done 1,659 o
- `4e37d5e59b09` — localhost:11434 / llama-server pid 29452 — THE LOCAL RUNG IS STILL CLOSED, BUT THE RECORDED MECHANISM IS WRONG AND A FIX BUILT ON IT WOULD HAVE COST QUALITY FOR NOTHING. Orders a8464e348c5e and
- `ff3c67a67b92` — src/codewatch.py stale() settle window vs standing daemons — M47 -- NO DAEMON PICKS UP NEW CODE FOR THE WHOLE OF A MAINTENANCE SHIFT, AND BOTH HALVES OF THAT ARE WORKING AS DESIGNED. codewatch.stale() needs the 
- `8f50f37255b5` — src/weave_index.py _STOPNAMES filter — The _STOPNAMES filter drops entries such as 'father', 'god', 'king' ENTIRELY from ENTITY_INDEX.json, not merely from cross-source candidate matching a
- `27f823fd6ed5` — src/ledger_guard.py check_since_snapshot MAX_LOST_FRACTION — The 5% loss tolerance cannot distinguish an accidental typo-fix in old ledger text from a deliberate small falsification of it. The number is explicit
- `d8858a26e46e` — run36 agent partitioning vs drill nets — RUN 36 HALTED ITS OWN LIBRARY AND THE PARTITION SCHEME IS WHY. Agent work was split BY TARGET MODULE so no two agents could edit one file -- which wor
- `481ef92af785` — data/SCOPE.json + src/scope.py build() — THE CODE WAS FIXED TODAY AND THE BAD DATA IT PRODUCED IS UNREACHABLE BY THE FIX. scope_for now returns None below the evidence floor instead of invent
- `585fcd3774b8` — data/records/bone-jeff-smith.json vs data/SWEEP_ROLL.json — data/records/bone-jeff-smith.json holds 86 catalogued entries and there is NO roll row for it under any spelling -- searching all 215 rows of SWEEP_RO
- `f6c52ef7657f` — - — A FOREIGN PROCESS CYCLICALLY EXHAUSTS THIS MACHINE'S ENTIRE EPHEMERAL PORT RANGE AGAINST OLLAMA, AND THAT -- NOT num_ctx -- IS THE MECHANISM BEHIND OR
- `707fefc17465` — src/render.py (entire module) — RE-VERIFIED THIS SHIFT AND RAISED TO OWNER, because the remedy is a curatorial call and this project forbids deletions without a review cycle. render.
- `b57e23204f66` — src/axis_correlation.py rho()/widening() no-matrix return — AN OWNER RULING IS OWED ON ONE NUMBER: what rho() should return when data/AXIS_CORRELATION.json is unreadable. The module's own docstring says 'THE DE
- `bd673ceaaf31` — src/anchors.py:190 CU.convene(...) call site — TWO CUSTODES CANNOT CONTRIBUTE WHAT THEY EXIST TO MEASURE, AND FINISHING THEM IS A CURATORIAL CALL RATHER THAN A CODE FIX. This supersedes the caller 
- `5c8a7bc883e7` — src/pipeline.py:synthesis_blocks (the `or` in the blocks express — QUESTION FOR THE OWNER, not a fix. synthesis_blocks ends with `blocks = ([with_feats chunks] or [rest chunks])`, so `rest` -- every entry with no mine
- `28c1f58f5e8a` — src/verify_math.py:7168 — verify_math.py:7164-7171 -- section 20u globs handoff/run35/checks_L*.py (6 files) and sections 20s splices checks_batch1..6. Six MORE run35 proposal 

**MINOR (32)**

- `47c8def059e3` — src/cosmology_graph.py — The console report truncates ranked lists: pair_w[:16], comps[:8], pair_shared[:4], c[:6]. Display-only -- the full data now reaches the JSON after th
- `85cdecef25f8` — src/catalogue_codex.py TYPE_CATEGORY — 'weapon property' (35 occurrences in the codex) is the third unmapped element type and still defaults to THINGS. Probably POWERS alongside 'rule'/'pro
- `6c479972e838` — src/liveness.py + drill.LIVENESS_CEILING — liveness's DEAD detection has a real false-negative surface, but the only narrowing that bites is a receiver-aware 'used' set, and that needs a matchi
- `8c354f6c9780` — src/autostart.py:121-145,157 — _twin_watchdog() returns False ('no twin, proceed') on ANY exception, and runs once before the loop. Both limbs verified. Neither obvious fix is right
- `2b695c192470` — sweep.py:68 — CROSS-MODULE (found while auditing verify_math.py). sweep.load (sweep.py:68) has no caller anywhere in src/ -- the only references are verify_math.py'
- `570525d35825` — src/endpoint.py:285-301 — endpoint.py:301 MODE_HTML is defined and referenced nowhere in the tree (grep MODE_HTML across all *.py: one hit, the definition). detect() can only e
- `d411f780d347` — src/sweep_plan.py:186 — coverage_map() has no callers anywhere in src/. grep returns one hit outside its own definition: line 209, a docstring in covered_by that merely menti
- `946153deafe9` — src/completeness.py:122-129 — completeness.py:122-129 -- category_size() has no caller anywhere in src/ (only mentions are inside category_size_probe's docstring and its silence.no
- `7e360eaec3a6` — src/chord_field.py — chord_field.py is never imported anywhere and none of its public functions has a caller. A repo-wide search for chord_field / total_beta / per_system_
- `de43fe54feb7` — src/scope.py:123 — scope.py:123 ceiling_for() has no callers anywhere in the repository -- 'grep -rn ceiling_for src/ docs/ *.md' returns only its own def line (plus pri
- `1eb00a84225e` — src/address_space.py:133 — address_space.UNADDRESSED is dead: defined at line 133 with a comment describing the honest answer for a shelf that shares no entity with anything, an
- `01695fe3ef26` — src/scale_theories.py:23-27,104-148 — scale_theories.py -- nothing in src/ imports this module; its only mention anywhere is its own name inside derivation.SCAN_MODULES. liveness reports a
- `665e3609bc82` — src/feats.py:542,550,876,1026 — Four functions in feats.py have zero callers anywhere in src/ (verified by grep: the only occurrence of each name is its own def): resolve_title() at 
- `4e92365b54f6` — src/address.py:208 — address.py:208 build_address() has zero callers in src/ (only its own __main__ demo at line 322) AND is stale: it returns f'{spine_code_for(source_nam
- `0291835411d9` — src/tempus.py:67-77 — tempus.DEGENERATE_TIME is dead: a four-entry table at line 67 naming the Basement Loop, the Rot City, the Betweens and the Pale with their charter cro
- `40e98eed6870` — src/worldseed.py:184 — Unreachable era/condition vocabulary: worldseed.to_options's size table carries 'primitive' (worldseed.py:184) and burgs.largest_city carries 'primiti
- `c0384991bfc5` — src/worldseed.py:236 — worldseed.unreachable_by_url (worldseed.py:236) has no callers anywhere in src/ -- grep matches only its own definition. Public helper, so this is a d
- `f883d9bb534e` — src/codewatch.py:109 — codewatch.py:109 twins(): the exclude_pid keyword REPLACES self-exclusion instead of adding to it -- me = os.getpid() if exclude_pid is None else excl
- `0fbaba6e1070` — aneurism.fandom.com — aneurism.fandom.com IS the wiki it is bound to -- it names itself 'ANEURISM Wiki', matching the bound source 'ANEURISM IV' -- but none of its catalogu
- `aecffd7eea57` — eberron.fandom.com — eberron.fandom.com IS the wiki it is bound to -- it names itself 'Eberron Wiki', matching the bound source 'Eberron: Rising from the Last War' -- but 
- `efd2b537f26d` — warthunder.fandom.com — warthunder.fandom.com IS the wiki it is bound to -- it names itself 'War Thunder Wiki', matching the bound source 'War Thunder + World of Tanks/Warpla
- `82fc93f056d4` — src/wh40k.py ROSTER axis citations — wh40k.py 55 axis citations now read [unattributed] because nobody has recorded whether each sentence is a verbatim wiki quotation or the assayer parap
- `5a0c4196142f` — src/verify_math.py source-substring checks — Several checks pin on a single generic identifier rather than a code-shaped fragment, e.g. '"ALL_JOBS" in _allsweep_src', which is also matched by a C
- `732f68f640cf` — src/coverage.py main() --show-best — --show-best defaults to a silent cap of 10 rows on BEST COVERED while its sibling --show (WORST COVERED) defaults to unlimited. The asymmetry is undis
- `372d4a8c8d46` — src/runguard.py replace_if_unchanged — The compare-and-swap has a narrow inherent window between the digest read and the rename. Reported as a QUESTION, not a defect: it is likely an accept
- `1cdc2f8cd2f3` — src/identity.py top[:6] / src/catalog.py missing[:30] — Both cap a CLI summary listing with an announced '+N more', never affecting the underlying data the pipeline consumes. THIS IS A QUESTION FOR THE OWNE
- `ef8940b363b3` — src/catalogue_codex.py section matching — The section-matching substring fallback keeps the same non-'most-specific-wins' shape that address.py was rewritten to fix. Zero live collisions verif
- `18f7673b77ce` — src/cleanup.py clean_ceiling — The prefix match picks the shortest candidate with no ambiguity check when two entities share a name stem. Not reproduced against live data; the missi
- `692f693c3900` — src/tells.py rule-of-three pattern — The 'rule of three' regex requires a trailing alike/all/together, so it matches far less than its name claims. Filed as a QUESTION: whether that narro
- `2f38b3e5258d` — src/pick_model.py resident() vs fit_note() — resident()'s REFUSED gate measures against TOTAL VRAM budget while fit_note() measures against FREE VRAM, so a model resident() calls usable can still
- `3dd5b6caef38` — src/estate.py charter() — charter()'s 'no charter spine code' finding caps its illustrative example list at four names (un[:4]) while the reported COUNT stays full. Filed becau
- `f2b06f8c9476` — src/pipeline.py:synthesis_prompt (the `fl[:3]` expression) — QUESTION FOR THE OWNER. synthesis_prompt builds each entity's evidence line as `' | '.join(re.sub(...)[:150] for x in fl[:3])[:420]`. `fl` is the enti
