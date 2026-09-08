# OWNER DECISION DIGEST — BATCH 04

Twenty open OWNER/SESSION orders, each checked against the CURRENT executable line on
2026-09-07. Read-only pass: nothing in `src/` was touched, no order was closed, no gate run.

Where an order's line numbers have drifted, the current line is given. A comment describing a
fault was never accepted as evidence the fault is live.

---

### bd673ceaaf31  [OWNER] [MAJOR]  — Wire Lumen's staleness and Threnody's veto, or rule them abstained
STILL LIVE: yes — `anchors.py:190` still reads `col = CU.convene(a["anchor"], a["scores"], attestation=a["attestation"], worksheet="anchors.py")`, and `convene`'s signature (`custodes.py:421-422`) still defaults `eta`, `distance` and `years_since` to None. NARROWED since filing: the "dispersive flag with no consumer" half was fixed — `custodes.py:399` now reads the flag inside `_transit_widening` (order 90eba4982972) — and both abstentions are published on every result (`staleness_measured`, `comparability_measured`), so nothing is misreported today.
QUESTION:   Do the calibration anchors carry a stated observation vantage, and where would Threnody's contest-flow edges come from?
OPTIONS:    (a) add explicit `distance`/`years_since` to each ANCHORS entry and pass them at :190  (b) rule anchors are read AT ZERO REMOVE by definition and pass `distance=0.0` so the 0.0 is computed, not a sentinel  (c) rule both permanently abstained and close the wiring question
RECOMMEND:  (b) for Lumen now; leave Threnody abstaining. (b) costs one line and converts a silent gap into a stated convention. Threnody has no honest input — `SHARED_STAGE_GRAPH.json` holds co-attestation weight, not contest flow — and a plausible-looking `eta` would make the veto fire on the wrong evidence, which is worse than a veto that never fires.
COST IF WRONG: if anchors really are read at a remove, (b) hard-codes "perfectly current" into the instrument the whole scale is calibrated against, and every published ± inherits it.
UNBLOCKS:   supersedes the caller halves of 2af7ca515157 and f467f662be4b.
THEME:      custodes wiring

---

### 7ad10a229440  [OWNER] [MAJOR]  — Does reprove_pool's success block restart_reader from ever running
STILL LIVE: yes — `foreman.py:1157` still `"the library's counters are moving": [reprove_pool, restart_reader]`; `reprove_pool` still returns `True, f"{len(ok)} of {len(rows)} buckets answer"` at `:239` regardless of whether `ok` is empty; the break is at `:1674` (`if did and not getattr(fn, "always", False)`); and `:1054-1055` mark only `run_completeness_audit` and `refresh_coverage` as `.always`. `restart_reader` (`:511`) carries no mark.
QUESTION:   Is restart_reader deliberately throttled behind the cheap remedy, or was it missed when the `.always` marking was added?
OPTIONS:    (a) mark `restart_reader.always = True`  (b) leave it graduated — cheap remedy first, expensive restart next round  (c) make `reprove_pool`'s `did` mean "the pool problem was fixed" rather than "a measurement completed" (did=False when 0 buckets answer)
RECOMMEND:  (c), then (a). (c) is the honest reading of `did` and matches the precedent the `.always` mark was introduced for — measuring is not an alternative to repairing. (a) on top costs nothing, because `restart_reader`'s own docstring records that restarting is lossless; without it, the one stall restart_reader exists for (reader alive, logging failures, doing nothing) is precisely the stall it is guaranteed never to see.
COST IF WRONG: (a)+(c) can bounce a healthy reader on a merely-partial pool, paying a 42-44 minute (worst case 4h) restart horizon every round it fires.
UNBLOCKS:   none — d2e44a766769 covers a different gap (restart_reader's own missing `_restartable()` check) and needs its own answer.
THEME:      foreman remedy dispatch

---

### 0c1670811107  [SESSION] [MINOR]  — Corroboration of a coverage-stamp fault that has since been fixed
STILL LIVE: NO — the order's own closing condition is met. It says "Close this alongside whichever of the two is fixed"; parent 4d44a6363245 is in `state/workorders_closed.jsonl`, and its remedy landed: `sweep_plan.py:249 def freeze_plan(run, n=16)` freezes the plan once per run, `batches(n=16, snapshot=None)` at `:112` packs a passed table rather than the live tree, and the dispatch CLI wires it at `:908` — `plan_rec = freeze_plan(a.run, a.batches) if a.run else None`. The corrupted shard was already repaired by hand at filing and the aggregate re-verified.
QUESTION:   none for the owner.
OPTIONS:    close it.
RECOMMEND:  close. The one residual — `record()` refusing when handed modules the frozen plan did not name — is not implemented (`sweep_plan.py:417` validates names against `known_modules()` but never against the plan), and it belongs to still-open parent 44c420f80448, whose own remedy has also largely landed. Re-check that parent instead of answering this one.
COST IF WRONG: none; the evidence this order preserved is already folded into the corrected shard.
UNBLOCKS:   flags 44c420f80448 as probably also stale.
THEME:      sweep coverage ledger

---

### 7e360eaec3a6  [OWNER] [MINOR]  — Keep or delete chord_field's six uncalled physics functions
STILL LIVE: yes, narrowed to half. `ADJUDICATIONS` is NO LONGER dead — `rigor.py:917` does a real `import chord_field as CF` and reads `CF.ADJUDICATIONS` at `:931` and `:937` (order 7368cd63bd2c). The cited evidence is also stale: `derivation.SCAN_MODULES` is now computed by `_scan_modules()` at `derivation.py:575`, not a hand-written list at :477. But a repo-wide grep for `total_beta`, `per_system_beta_without_unification`, `landauer_floor`, `recoil_momentum`, `recoil_velocity` and `critical_power_self_focus` returns nothing outside `chord_field.py` itself: all six functions still have zero callers.
QUESTION:   Are the six physics helpers reference material the Mensura work will call, or dead weight to remove?
OPTIONS:    (a) keep and mark them explicitly uncalled, in the idiom `feats.remine` already uses  (b) delete them  (c) wire them into rigor/derivation's audit rows
RECOMMEND:  (a). The arithmetic was independently checked correct, and the module is now a real dependency of rigor's adjudication audit, so deleting half of it invites re-deriving the same physics later. A documented "no callers yet" comment costs one paragraph and stops this being re-filed a fifth time — it has already been recorded by run33 batch03 and read clean by sweep31 and sweep32.
COST IF WRONG: (a) leaves six functions nobody exercises; a wrong constant inside one would go unnoticed until something wires it.
UNBLOCKS:   none.
THEME:      dead code ruling

---

### b813fc5a37e2  [SESSION] [MAJOR]  — Cloud routing gate ignores the pool-proof age it claims to check
STILL LIVE: yes — `pipeline.py:366` still `_PHASE_POOL["n"], _ = _T._answering_buckets()`, discarding the caption; the docstring at `:354-360` still claims tuning "already compared the file's mtime"; the gate is at `:436`. `tuning.py:161-163` still returns the same `n` with only a different caption, and `tuning.py:62-66` still says a stale proof is counted at full strength and that discounting it "is not settled here".
QUESTION:   Should a stale `POOL_PROOF.json` still count at full strength toward `CLOUD_MIN_BUCKETS`?
OPTIONS:    (a) keep the count but capture and log the caption, so a cloud route taken on an eight-hour-old proof says so in `state/pipeline.log`  (b) fail closed — refuse to count a proof older than `PROOF_STALE_SECONDS`
RECOMMEND:  (a) now, with the docstring corrected in the same edit; take (b) only on the owner's word. (a) is free and makes the decision visible, whereas (b) settles a question `tuning.py` explicitly declines to settle, citing m59 — even a FRESH proof once certified 4-of-36 while live calls succeeded at 2.8%. The docstring correction is not optional either way: as written it is the exact sentence that stops the next reader checking.
COST IF WRONG: staying at (a) leaves a week-old proof routing every phase judgment cloud-first; moving to (b) strands the pipeline local-only whenever a `prove()` run is late, and the gate was measured sitting exactly on its threshold (3 vs CLOUD_MIN_BUCKETS 3).
UNBLOCKS:   none.
THEME:      staleness fail-closed

---

### 5f1dc97d5216  [OWNER] [MAJOR]  — Unreadable records directory reads as a clean empty corpus
STILL LIVE: yes — `weave_index.py:272-276` is unchanged: `except OSError:` then `_ = "silence-exempt: an unreadable records dir reads as an empty corpus, as it always did"`, falling through to `val = (files, None if unstattable else (len(files), newest))` with `files=[]` and `unstattable=0`, i.e. the clean cacheable signature `(0, 0)`. The per-file handler eight lines above (`:245-268`) still forces `sig=None` for exactly the same class of event.
QUESTION:   Should a directory-level `scandir` failure be indistinguishable from a genuinely empty records directory?
OPTIONS:    (a) leave as-is — callers depend on empty being a stable answer, and the next good scan busts the cache  (b) mirror the per-file guard: treat a top-level failure as `unstattable=1`, forcing `sig=None`
RECOMMEND:  (b). The same event (a Norton lock, an offline mount, a permissions blip) is fail-closed at file granularity and fail-open at directory granularity inside one function. Unlike the per-file case, a directory failure reaches `weave_index.py --write`, which would land near-empty `ENTITY_INDEX.json` and `WEAVE_CANDIDATES.json` over the files `weave.py`, `cosmology_graph.py` and `thread_integrity.py` read as the whole entity population — the same shape as the catalogue_web synthesis-nulling incident that reached MANAGER rung.
COST IF WRONG: (b) makes a genuinely empty records directory uncacheable, so callers re-scan; that is the 0.70 ms enumeration, not the 43 minutes the memo was written to remove. Do NOT weaken the per-file guard to match — it is the one that already works.
UNBLOCKS:   none.
THEME:      fail-closed I/O

---

### dc501e776a2b  [SESSION] [MAJOR]  — rigor certifies a nan matrix as maximally consistent
STILL LIVE: yes — reproduced verbatim on the current source today: `perron_weights [0.632, 0.298, 0.070]`, `logrank_weights [nan nan nan]`, `CR -0.5049883082990546`, `eta 1.0`, `both_say_consistent True`. `rigor.py:217` is still `"coherent": bool(cr < 0.10)`, `:239` still `eta = (grad_sq / total) if total > 0 else 1.0`, `:281` still `bool(p["CR"] < 1e-9 and lr["curl_fraction"] < 1e-9)`.
QUESTION:   **Reroute to RUN/LOCAL — no ruling needed.** The remedy is fully specified and mechanical: validate square/finite/positive/reciprocal at the head of both functions and raise in the voice `assay._check_scores` uses; make both consistency tests two-sided (`abs(...) < 1e-9`); make `coherent` `abs(cr) < 0.10`; return `eta=None` plus "no flow to decompose" instead of 1.0.
OPTIONS:    (a) do the fix as written  (b) escalate the raise-vs-refuse style choice — but the order already resolves it against an existing house precedent
RECOMMEND:  (a). No judgment is left in it, and the one thing that makes it urgent is timing: `theorem_1_check` and `consistent_matrix` have no consumer outside `rigor.main()` today, so this is free to fix now and expensive the moment anything wires them.
COST IF WRONG: none from fixing; leaving it means the strongest verdict the module can give — "a single scalar faithfully represents the relation" — is returned for an arithmetic that produced nothing.
UNBLOCKS:   none.
THEME:      check cannot fail

---

### 7716ac4884cc  [SESSION] [MINOR]  — Six pipeline.py line cross-references now point at the wrong lines
STILL LIVE: yes, and MORE stale than when filed — the file has grown since. Current state: `pipeline.py:604` still cites ":1552" for a `topic_rejected` write now at `:2076`; `:617-618` still cite ":1532"/":1573" for pops now at `:2031`/`:2072`; `:2445-2446` still cite ":1948 and :2054" for phase 6/7 rulings; `:2373` still cites `profile.py:20` for a number that no longer appears anywhere in `profile.py`.
QUESTION:   **Reroute to RUN/LOCAL — no ruling needed.** Correct six numbers, and where the cited construct is unique, cite it by NAME instead of by line.
OPTIONS:    (a) correct in place  (b) convert to name-based citations
RECOMMEND:  (b) where the construct has a unique name, (a) otherwise. The by-name preference is already this codebase's own argument (`address_space.py` reading TOTAL_BITS at import rather than transcribing it), so it is house style rather than a new decision; these have now gone stale twice and will go stale again.
COST IF WRONG: nothing breaks. The cost of leaving it is that `:604`'s citation sits in the middle of a measured claim ("appears 0 times in 282,822 entries") and points the reader at a line with nothing to do with topics.
UNBLOCKS:   none.
THEME:      stale citations

---

### c391a1f77e42  [OWNER] [MINOR]  — Does phase 8 close when every ready source has zero entries
STILL LIVE: yes — `manifest_builder.py:255` is still `if not entries: return jobs`; `phase_write` (`pipeline.py:2745`) still has `if jobs: ... elif refused:` and no `elif names:` arm; and `drill._write_phase_stays_open_when_everything_refuses` (`drill.py:4542`) still carries, at `:4582`, "... and the vacuous case is still allowed to close, or the phase never finishes." The explanatory note left for the next reader is in place, so this has not been silently re-attempted.
QUESTION:   Does "every ready source produced nothing" mean phase 8 is DONE, or that phase 8 should stay OPEN?
OPTIONS:    (a) current behaviour is right — nothing to build is not a failure to build  (b) hold the phase open, which requires editing the drill net's second half FIRST
RECOMMEND:  (a), plus a diagnostic. Reaching that branch means sources WERE ready and every one was empty, which is a genuinely different fact from "nothing was ready" (handled far above by `if not ready`) and is currently invisible; logging that count costs nothing and touches no net. Take (b) only if you want phase 8 to mean "a manifest exists", and say so explicitly, because editing a net to admit the change you are making is the move the ratchet exists to prevent.
COST IF WRONG: (a) can permanently mark phase 8 done having written no manifest, with no later run to redo it; (b) risks phase 8 never finishing on a library that has catalogued sources it has not read yet.
UNBLOCKS:   supersedes 97d5b256fbdc (already closed).
THEME:      phase gate semantics

---

### ae25c89f0179  [OWNER] [MAJOR]  — Genre-aware naming register is structurally unreachable
STILL LIVE: yes — `onomast.py:512` still `reg = register_for(v["continuity_group"])`, one positional argument; `register_for` (now at `:363`) still returns the sha256-of-group-id fallback at `:370-372` whenever both `genre_register` and `features` are None. Measured today: `RESOLVED_ENTITIES.json` records carry `['attestations','band_conflict','bands_attested','canonical_name','continuity_group','key','n_attestations','topics']` — no genre, no features. The gap is structural, not a missed keyword.
QUESTION:   Where do genre and world-features per continuity group come from, or is hash-assigned naming accepted?
OPTIONS:    (a) join through `genre.py`/`worldseed` per continuity group at the call site  (b) accept the hash fallback and delete the unreachable blend  (c) leave it in place, documented as unreachable pending the input
RECOMMEND:  (a) if a per-group genre source exists, otherwise (c) — never (b). The docstring names the exact harm the blend was written to fix (Alien and Doom given the flowing elvish sound, Greek myth denied the classical one), so deleting the mechanism re-accepts a defect the project already ruled against; leaving it documented keeps the fix available the day the input exists.
COST IF WRONG: (c) means every generated world name is a hash of a group id — a real prose-quality loss that is invisible because it always produces a plausible name.
UNBLOCKS:   none.
THEME:      unreachable feature

---

### 2eabb417f58f  [SESSION] [MAJOR]  — A drill net that cannot fail on the dedupe guard it names
STILL LIVE: yes — confirmed line by line today, and this is the highest-value item in the batch. `drill.py:11675 def drill_codex_dedupe_is_typed()` imports `catalogue_codex` only for `norm`, builds its own four-row `contents` list, folds it with its OWN reconstruction of the pairing key (`seen.add((_CC.norm(et), _CC.norm(nm)))`) and returns `len(seen) == 4`. The guard it names is `catalogue_codex.py:272 pair = (norm(etype), key)`, inside `catalogue()`'s per-section loop, which the net never enters. Reverting `:272` to `pair = key` — the exact f4f3c1d15915 regression, 88 dropped elements across 8 sections — leaves this net GREEN. `src/drill.py` is on `local_agent.DENYLIST` (`local_agent.py:64-65`), so LOCAL genuinely cannot do this; SESSION is the right rung.
QUESTION:   How much of `catalogue()` is worth making testable — factor the pairing out, or drive the real function against a fixture?
OPTIONS:    (a) factor the pairing into a named helper the net drives against a synthetic contents list  (b) drive `catalogue()` against a fixture manifest carrying the four (type, name) rows and assert four entries come back with the right categories and `dupe_elements` empty
RECOMMEND:  (b). It is the only version that actually enters the loop the net's printed name promises, so it catches the f4f3c1d15915 regression AND the `TYPE_CATEGORY` routing the damage report turns on (Race Troglodyte in FACTIONS vs Language Troglodyte in POWERS). (a) protects one line and leaves the rest of the loop untested — take it only if the fixture proves impractical, and rename the net to what it really checks if you do.
COST IF WRONG: (a) keeps a net whose name over-promises — the exact class CLAUDE.md calls the standing lesson, and the class this codebase has now caught twice.
UNBLOCKS:   a5de2dcb9447 (`feat_bearing_path_unchanged`, still open) is the same class. One ruling — "a net must drive the module it names, or be renamed to what it does test" — settles both.
THEME:      net cannot fail

---

### f84cb75edcfe  [OWNER] [MAJOR]  — Prime World Equipment is bound to the hydration-drink wiki
STILL LIVE: yes — `data/WIKI_HOSTS.json` still holds `'Prime World Equipment' -> 'prime.fandom.com'`. NOTE: this order's remedy was cut by the old 600-char cap and is unrecoverable (searched exhaustively 2026-08-29); the options below are re-derived from the `where` and the evidence, as that marker instructs.
QUESTION:   Rebind to `primeworld.fandom.com` even though it carries no articles for the item-level entries already catalogued, or handle the source differently?
OPTIONS:    (a) rebind and re-mine, accepting that the item-level entries will not resolve  (b) rebind and re-catalogue the source at a coarser grain (heroes/factions rather than 'Argentum'/'Aurum'/'Bath Potion')  (c) leave unbound and mark the source uncitable pending a real host
RECOMMEND:  (a), then (b) if the re-mine comes back thin. Rebinding is right regardless of what follows — the current binding cites a beverage wiki as evidence for a fiction, which is strictly worse than no host at all — and the grain decision in (b) should follow a live look at what `primeworld.fandom.com` actually carries, not precede it.
COST IF WRONG: (a) alone leaves BINDING_SUSPECT standing and the catalogued entries uncitable, which reads to the next run as a failed rebind rather than as a known, ruled-on gap.
UNBLOCKS:   none.
THEME:      source binding

---

### 423e35500033  [SESSION] [INFO]  — Empty provenance manufactures a probe out of nothing
STILL LIVE: yes — `chain.py:668` is still `for row in (prov.get(e) or [{}]):` with `probed = True` at `:673`. Still unreachable along `chain.main`'s path, exactly as filed: `chain.py:490-492` appends to `prov[e]` inside the same locked block that increments `edges[e]`.
QUESTION:   **Reroute the fix to RUN/LOCAL — no ruling needed.** The contract question (private to `extract`, or callable on an externally built graph) changes only the docstring: the code change — `or []` with `probed` left False — is identical and correct under both readings.
OPTIONS:    (a) make the change and document it as tidying  (b) make the change and document it as load-bearing on a public contract
RECOMMEND:  the change either way; leave the wording to whoever owns `chain.py`. An edge with no provenance is by definition unprobed, so reporting it in the NOT ADJUDICATED tally rather than as a genuine disagreement is more honest and free.
COST IF WRONG: none in the fix. The risk is documenting it private and then someone building `edges` and `prov` separately, which reinstates the fault silently — the docstring itself calls this shape "a check that cannot fail".
UNBLOCKS:   none.
THEME:      unprobed vs disagree

---

### f27d210d4fea  [SESSION] [MINOR]  — Dead alive() and _page_exists() in feats.py, filed four times over
STILL LIVE: yes as fact — `feats.py:576 def alive(host)` and `feats.py:925 def _page_exists(host, title)` both still have zero callers anywhere in the tree (only their own defs and two comments about `alive()` at `:431` and `:559`). But this is ONE question filed FOUR times: `c54bb7d84622` (LOCAL/MINOR) covers exactly these two functions, `4f308dbd9d2c` (SESSION/MAJOR) covers `resolve_title`, and `665e3609bc82` (OWNER/MINOR) covers all four at once.
QUESTION:   **Reroute the mechanical half to RUN/LOCAL and consolidate.** The only decision in this cluster is 4f308dbd9d2c's: wire `resolve_title` in, or decline it — 17,148 entries were mined to nothing by the catalogue-name/wiki-title mismatch it exists to fix, and `evidence_for` still calls `discover(host, name)` with the raw catalogue name.
OPTIONS:    (a) wire `resolve_title` (and `_page_exists` goes with it)  (b) decline it and delete all three  (c) answer only the trivial half — delete `alive()` — and leave the real question open
RECOMMEND:  answer 4f308dbd9d2c, and let this order follow it. Delete `alive()` now regardless, per its own docstring: it is an uncalled wrapper whose only remaining function is to be the wrong thing to call, which is the mistake order 64e4db060ad6 was filed about. Leave `remine()` alone — `feats.py:1573-1585` documents it as deliberately uncalled.
COST IF WRONG: (b) rules that a measured 17,148-entry loss stays unmitigated; make that ruling explicitly rather than by deletion.
UNBLOCKS:   c54bb7d84622, 665e3609bc82 and 4f308dbd9d2c — one answer settles all four.
THEME:      dead code cluster

---

### 585fcd3774b8  [OWNER] [MAJOR]  — Bone (Jeff Smith) has no roll row; 86 entries invisible
STILL LIVE: NO as an owner question — the order's own nominated tiebreaker settles it. `state/backups/SWEEP_ROLL.json.reconstructed-20260826` holds **216** rows and CONTAINS `{"name": "Bone (Jeff Smith)", "entry_count": 86, "status": "catalogued"}`; the live `data/SWEEP_ROLL.json` holds **215** and zero matches for "bone". So the row was LOST in the 2026-08-26 double destruction, not never-added. That is repair, not a curatorial call. The record is real: 86 entries, `provenance: "added from boneville.fandom.com"`, `_writer` digest `b4ce17d37f200b4f`.
QUESTION:   **Reroute to RUN/LOCAL — no ruling needed.** Restore the row.
OPTIONS:    (a) restore from the reconstruction  (b) leave it out
RECOMMEND:  (a). One caution for whoever does it, and it is the only judgment left: the backup row is THINNER than a live row — live rows carry `category`, `seq`, `mode`, `ceiling_entity`, `provisional_magnitude`. Derive those from `data/records/bone-jeff-smith.json` (which has `category: "Comics / graphic novels"`, `mode: "wiki"`, `status: "added"`) rather than inventing them, and leave any field the record cannot supply absent rather than guessed.
COST IF WRONG: leaving it out keeps 86 catalogued entries invisible to every downstream gate while the record sits on disk looking complete.
UNBLOCKS:   none — the sibling Roger Rabbit case is a slug mismatch and is a different repair.
THEME:      roll repair

---

### 762256b4b844  [OWNER] [INFO]  — Should escalate() reject a non-integral float level
STILL LIVE: yes, but still unexercised. `escalation.py:258-260` is unchanged — `try: level = int(level)` / `except (TypeError, ValueError):` — and `int(2.7)` is 2, so `escalate(2.7, ...)` silently becomes OPERATOR instead of the MANAGER-with-`unrecognised_level`-evidence routing every other malformed level gets (`:262-268`). Checked repo-wide today: no call site in `src/` passes a float literal.
QUESTION:   Tighten the contract for a path nothing currently exercises, or leave it as documented slack?
OPTIONS:    (a) reject a non-integral float into the same MANAGER-with-evidence path  (b) leave it, and document the gap where the comment block already explains the design
RECOMMEND:  (a). It is two lines inside the block whose entire stated purpose is that an unrecognisable level lands somewhere loud, and the failure it prevents is the worst-shaped one available here — a level that silently DE-escalates, so a SAFETY event filed as `3.5` would refuse one unit of work instead of failing the battery. Honour `is_integer()` so a legitimate `3.0` still passes.
COST IF WRONG: (a) adds a branch nothing runs today. That is the entire downside.
UNBLOCKS:   none.
THEME:      escalation contract

---

### 541384445ec3  [SESSION] [MINOR]  — Grounding distribution log capped at exactly the population size
STILL LIVE: yes — `pipeline.py:2427` still `kinds.most_common(6)`, and measured today `len(grounding.GROUNDINGS) == 5` plus `grounding.UNGROUNDED` gives exactly 6 possible values. Margin zero.
QUESTION:   **Reroute to RUN/LOCAL — no ruling needed.** `most_common()` with no argument. The population is bounded by doctrine, not by data, so there is no reason for a bound at all.
OPTIONS:    (a) drop the argument  (b) keep a bound and route it through the house remainder idiom (`style_audit._cut`, `style_audit.py:156-170`)
RECOMMEND:  (a). Hard Rule 0 already decides this; the line's whole job is to report the distribution, and it would truncate silently the day a sixth grounding type is added.
COST IF WRONG: nothing — the log line gets at most six entries either way.
UNBLOCKS:   shares its doctrine with 3dd5b6caef38 below, but needs no ruling of its own.
THEME:      hard rule 0 cap

---

### ee0e5bef7dab  [OWNER] [MINOR]  — Bulk-delete the leaked %TEMP% scratch directories
STILL LIVE: NO — there is nothing left to delete. Counted in `%TEMP%` today: 8 `panscript-ledger-*`, 6 `panscript-lane-*`, 22 `panscript-*` in total, and NONE older than 2026-09-03. The 490 + 302 backlog this order asks a person to rule on was cleared outside this repository some time after 2026-08-29. The leak fix itself is confirmed in place: `verify_math.py` routes its `mkdtemp` sites through `_mkdtemp_vm` (25 occurrences).
QUESTION:   none for the owner.
OPTIONS:    close it.
RECOMMEND:  close. The bulk deletion this order was filed to authorise no longer has a subject.
COST IF WRONG: none.
UNBLOCKS:   RESIDUAL WORTH ONE LINE, and it is a run's job not the owner's: the 22 remaining span 2026-09-03 to today across four prefixes (`ledger`, `lane`, `cache21`, `wr20k`), so the `atexit` rmtree is not firing for every run — expected for hard-killed or rc=17 exits, but it means the leak is slowed rather than closed. Worth a fresh measurement, not this order.
THEME:      temp hygiene

---

### 3dd5b6caef38  [OWNER] [MINOR]  — Does Hard Rule 0 reach announced console illustration lists
STILL LIVE: yes — `estate.py:422` still `f"{len(un)} — e.g. " + ", ".join(un[:4])`, with the count reported in full and the example list cut at four.
QUESTION:   Does the no-caps rule govern console illustration, or only pipeline-consumed rosters?
OPTIONS:    (a) illustration may be capped provided the count is full and the cut is named  (b) no cap anywhere — print all of them  (c) route every such cut through the house remainder idiom (`style_audit._cut`) so the remainder always prints
RECOMMEND:  (c). It is (a)'s readability and (b)'s honesty in one, the idiom already exists in this tree, and the harm Hard Rule 0 actually names is a truncation that hides a smaller universe — which a printed remainder structurally cannot do. Worth stating as doctrine rather than fixing one line, since five separate batches asked it independently.
COST IF WRONG: (b) turns a one-line status note into a wall of names on a normal run — this list is currently the ~110 unassigned sources; (a) leaves five more `[:N]` sites nobody has to justify.
UNBLOCKS:   the same question raised independently by sweep36 batches 07, 08, 10, 15 and 16 — one ruling settles all five, and it also settles the shape (though not the fix) of 541384445ec3 above.
THEME:      hard rule 0 scope

---

### 5a0c4196142f  [OWNER] [MINOR]  — Should source-substring checks ask the parse tree instead of the text
STILL LIVE: yes as a class; NO as the cited instance. The exemplar was fixed by order 469b4db261ef — `verify_math.py:3054` now strips comment tails into `_allsweep_code` and `:3056` tests `"ALL_JOBS" in _allsweep_code`, not `_allsweep_src`. But bare-identifier pins over RAW source remain, notably `:6142` `"assert_gate_open" in _gen_src`, `:9331` `"_pool_answer_usable" in _cb_src`, and `:5275` `"silence.write_json" in _atomic_src[...]` — each still defeatable by a comment reproducing the word, which is the defeat that was actually measured.
QUESTION:   Is comment-stripping enough for these checks, or should the ones guarding a safety parse?
OPTIONS:    (a) comment-strip everywhere — the `_code` idiom is already used in five places  (b) go to `ast` for pins that name a call or a binding  (c) leave, case by case
RECOMMEND:  (a) as the floor now, (b) for the ones that prove a guard is WIRED. (a) is a mechanical sweep of the remaining `in _*_src` sites and removes the exact hole that was measured; (b) costs real work per site and only pays where the check is the sole evidence a safety is in effect — `assert_gate_open` and `_pool_answer_usable` are both that, and both sit on the prose gate and the cloud path.
COST IF WRONG: (a) alone still passes on a string literal or a docstring naming the identifier — a narrower hole than the comment one, but the same shape, and this class is what CLAUDE.md's standing lesson is about.
UNBLOCKS:   none.
THEME:      net cannot fail
