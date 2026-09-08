# OWNER DECISION DIGEST — BATCH 10

20 open OWNER/SESSION orders, each verified against the CURRENT executable line on 2026-09-07.
18 still live, 2 dead. 3 reroute to RUN/LOCAL with no ruling needed; 1 more should be deferred
onto an order it depends on. Read-only pass — nothing in `src/` was touched.

**CAVEAT ON TWO FILES.** `state/MUTATION_ACTIVE.json` shows a sandboxed pass running (pid 68112,
targets `assay.py`, `prose_gate.py`, `escalation.py`). Everything quoted below from `assay.py` and
`escalation.py` matched its order's own recorded values, so no line read here appears mutated —
but if either block reads oddly, re-check it after the pass lands.

---

### 728d9e99e9ec  [SESSION] [MAJOR] — Six unwrapped live-state calls redden §20z and cancel mutation passes
STILL LIVE: yes — all six sites are still bare at `verify_math.py:4008` (`_STx.check` in `_pool19ai`), `:4643` (`_D20.jobs()`), `:4725` (`_on21._proc_lines()`), `:5834`/`:5838`/`:5861`/`:5876`, `:7463`, `:7953`/`:7967`. The only wrapped `standards.check()` in the file is `:7976`, under `with _no_ledger_vm():` at `:7975` — its clean twin at `:7967` is bare, exactly as filed. `_THIRD_PARTY_CLASSES_VM` (`verify_math.py:384-386`) still holds exactly ONE dependency, `"cascade scratch DB"`; no live-operational-state class exists.
QUESTION:   Should these calls be covered by a NAMED third-party abstention for live operational state, or by a blanket ledger suppression, or left alone?
OPTIONS:    (a) extend `_THIRD_PARTY_CLASSES_VM` with a "live operational state" dependency naming the machine- and network-tier classes `standards.py`/`dashboard.py`/`overnight.py` can legitimately emit, and close the two mechanical sites with `_no_ledger_vm()`  (b) wrap all six in blanket `_no_ledger_vm()`  (c) leave it and keep accepting a non-deterministic baseline
RECOMMEND:  (a) — and yes, this is the highest-leverage single fix in the queue. It removes the largest source of run-to-run battery non-determinism: because `dashboard.state()` calls `standards.check()` internally at `dashboard.py:739`, `standards.check()` runs ~15x per battery run, each doing a real `getaddrinfo` (`standards.py:382`), an Ollama generate with `timeout=300` (`standards.py:184`, `:264`), and a 60s PowerShell `Get-CimInstance` spawn (`standards.py:1962`, `overnight.py:146-152`) — against 38 `silence.note("standards.py:*")` sites and 29 `silence.note("dashboard.py:*")` sites counted today, every one on a live artefact's read-failure path.
COST:       Roughly an hour to enumerate and name the classes, plus one clean battery run to confirm. It must NOT land while the current pass is running — `mutate.py` takes its baseline from the live tree.
COST IF WRONG: (b) suppresses the echo of a GENUINE library fault occurring during a live call — the exact hole §20z was built to close (doctrine at `verify_math.py:353-405`; the widened-exemption control at `:10091-10110` exists to catch precisely this). (c) keeps cancelling 20-hour passes for reasons that are not about this library's code.
UNBLOCKS:   `74f1bc47da2a` (the same call sites, other half — that order asks for the same decision and should be answered together, by the same person). By precedent it also answers `895a99602bf0`'s open question.
NO RULING NEEDED ON TWO OF THE SIX — reroute to RUN/LOCAL: `verify_math.py:4643` and `:4725` are single calls whose assertions do not touch the ledger; both take `_no_ledger_vm()` as §16's `SF.build()` calls now do. The third §20v row in that same edit — `check('the process probe returned a listing at all', bool(_probe21), True)` — DOES remove a check, so it stays the owner's call; note the precedent is already set, `verify_math.py:4728-4737` records two sibling rows removed from that section for the same reason, and `_proc_lines` returns None on a loaded machine, which is the one condition under which a 20-hour pass runs.
THEME:      battery determinism

---

### 40e98eed6870  [OWNER] [MINOR] — Era and condition vocabulary worldseed can never emit
STILL LIVE: yes — `worldseed.py:226` is still `"medieval": 45, "primitive": 35`, `TECH` (`worldseed.py:96-101`) still has exactly four names, `CONDITION` (`:90-94`) still three; `burgs.py:132` still keys `"primitive"`, `:126` and `:134` still key `"settled"`.
QUESTION:   Add matchers so the vocabulary becomes reachable, or delete the dead keys?
OPTIONS:    (a) add a `"primitive"` TECH row and a `"settled"` CONDITION row  (b) delete the dead keys from worldseed/burgs  (c) keep and annotate as reserved vocabulary
RECOMMEND:  (a). The evidence gathered under order `ad681057369a` and quoted in-file at `worldseed.py:213-224` shows `"primitive"` is live in three sibling modules — `genre.py:57` gives the mythology genre `tech="primitive"`, `onomast.py:348` maps it to the guttural register, `burgs.py:132` gives it a 2,500-population primate city — so worldseed's table is the one place in the tree that cannot produce the value.
COST IF WRONG: (a) re-derives `era`, `size` and every downstream burg count for whichever worlds a new matcher catches, moving published numbers. (b) makes genre's mythology prior and onomast's guttural-by-tech rule permanently unreachable.
UNBLOCKS:   `ad681057369a` — same question, evidence already gathered there.
THEME:      dead vocabulary

---

### 3eff62be6cc3  [OWNER] [MAJOR] — GROUNDINGS.json still publishes pre-fix inflated confidences
STILL LIVE: yes, but only the DATA half — the code is fixed. `grounding.py:125` is now `def classify_text(text, top=None)` and `classify_source`'s comment at `:220` records "the denominator below is the whole field and `runners_up` is the whole field minus the winner." The stored file was NOT re-derived: measured this shift, `data/GROUNDINGS.json` holds 209 rows of which 48 carry 2 runners-up and 159 carry 3, and `groundings_scored` — a key only the fixed code emits (`grounding.py:229`) — is absent from all 209.
QUESTION:   Re-run `grounding.py --write` and move published numbers, or keep the stored classifications and annotate them?
OPTIONS:    (a) re-derive and republish  (b) keep and annotate as computed under the old denominator
RECOMMEND:  (a). Four sources — Marvel, Bleach, "major fantasy pantheons", "Pantheon: Mesoamerican" — currently publish confidence >= 0.5 and are reported as settled cosmologies when the full ranking makes them contested, and `main()`'s contested line reads that exact 0.5 threshold. The file is asserting something the module itself no longer computes.
COST IF WRONG: (a) moves 14 published confidences and flips 4 verdict lines, visible to anyone tracking the site. (b) leaves `navtree.py` and `pipeline.py` reading a number the code would refuse to produce.
UNBLOCKS:   the `GENRES_JSON_HOLDS_INFLATED_CONFIDENCES` sibling this order's own evidence names — identical defect, identical decision, rule both at once.
THEME:      stale published numbers

---

### d44b106ce7e3  [SESSION] [INFO] — Three rulings owed: publish stderr, escalation 'who', assert_clear scope
STILL LIVE: yes, all three. **Q1** `publish.py:1521-1530` still notes, prints to stderr, and `return False` when `ahead is None`. **Q2** `escalation.py:103-107` — SUPERVISOR and SAFETY tuples still lack `"who"`, OPERATOR one rung lower still has it. **Q3** `escalation.py:886` still reads "EVERY entry point calls this before doing anything"; re-measured today it is **17 of 98** (was 14 of 97 — `hostcheck`, `threads` and `withdraw_chapters` have since been added, so the `withdraw_chapters` instance this order cites as the cost is already fixed).
QUESTION:   Three one-sentence rulings. Q3 is the one that matters and settles ~81 other cases.
OPTIONS:    Q1 (a) stderr is sufficient here (b) raise `PushHeld` on an unanswerable ahead-check. Q2 (a) add `"who"` to both rungs (b) say in the comment that the omission is deliberate. Q3 (a) name the criterion and correct the docstring (b) wire `assert_clear` into all 98 entry points.
RECOMMEND:  Q1 **(a)** — no commit was made this cycle so nothing new is stranded, and order `3778bc42499f` already closed the real hole by retrying stranded commits at `publish.py:1531-1540`; just say so in the comment. Q2 **(a)** — `"who"` is a decision field at every rung that can stop work, and the asymmetry has no stated reason. Q3 **(a)** — write "every entry point that WRITES outside `output/` and `state/` asks; read-only instruments do not."
COST IF WRONG: Q3 (b) would halt `zfighters.py` from printing a table, and would keep the dashboard — the one instrument built to display a halt — refusing to start under one, which is the opposite harm order `aad11acb1183` records.
UNBLOCKS:   `aad11acb1183` and the `WITHDRAW_CHAPTERS_NEVER_ASKS_IF_THE_LIBRARY_IS_HALTED` order, both settled by Q3's one sentence.
THEME:      docstring invariants

---

### b9584c782d95  [SESSION] [MAJOR] — feats --roll silently drops sources with no resolved host
STILL LIVE: yes — `feats.py:1654` is still `if not h or (only and only not in r["source"]): continue` with no counter, `:1899` still calls `resolve_hosts(recs, verify=False)`, and roll()'s printed summary still counts `refused` / `_UNCACHED` / `_STALE_GATE` / `_CAP_BOUND` / the length filter / `_RATE_LIMITED` and nothing for a hostless source.
QUESTION:   **Reroute to RUN/LOCAL — no ruling needed.**
OPTIONS:    (a) reroute as written  (b) hold on SESSION
RECOMMEND:  (a). The order supplies both remedies and says "either is enough", and both are add-a-counter-and-print in the exact shape five sibling loss categories already use in the same function. There is no reading in which printing an exclusion count is the wrong answer.
COST IF WRONG: nothing breaks either way; holding it just keeps 727 measured, silently-excluded entities off the roll's stdout for another cycle.
UNBLOCKS:   none
THEME:      silent exclusion

---

### 171ade4c7d27  [OWNER] [MINOR] — local_agent reports rc=0 and ok=true for a prose non-answer
STILL LIVE: yes, for the finding it actually carries. `local_agent.py:1180` still derives `produced_nothing` from `not attempted and answer is not None`, so a run whose answer text says the model could not do the job has `produced_nothing=False` and `:1238`'s `out = {"ok": not unreverted, ...}` leaves ok=True with rc=0 at `:1353`. The 503 backoff at `:1039-1051` is correctly untouched — this order exists to record that the proposed refuse-on-first-503 fix was measured wrong and deliberately NOT implemented.
QUESTION:   Should local_agent detect "the model reported failure in prose", and if so how narrowly?
OPTIONS:    (a) leave rc alone, document the ~6-minute-under-contention scheduling fact, treat the prose non-answer as the caller's problem  (b) add one narrow named predicate — the model returned an answer but made zero tool calls after being handed a truncated slice whose `chars_after_slice` was still non-zero — and set ok=False on it  (c) a general "did the model say it failed" text heuristic
RECOMMEND:  (b). The measured case is exactly "read a truncated slice of `src/policy.py`, never paged, reported failure in prose", which is nameable without free-text matching; that fixes the true half of NEXT_STEPS run #42 item 3 without (c)'s loosenable gate.
COST IF WRONG: (c) lets a model's phrasing decide the exit code. (a) keeps every caller here gating on an exit code that says success over a handler that could not handle. **Do NOT implement run #42 item 3 as written** — refusing on the first 503 converts a measured slow success (5m52s, two turns, rc=0) into a fast failure, precisely when the free rung is most worth having.
UNBLOCKS:   closes NEXT_STEPS run #42 item 3 as answered-and-refused.
THEME:      rung honesty

---

### adaeaa7ad639  [OWNER] [MINOR] — Cosmography size-class multipliers contradict their own descriptions
STILL LIVE: yes — `cosmography.py:134-135` still `"POCKET": 1e-9` / `"MINOR": 1e-6` with the same prose, `SIZE_CLASS_MAX_GALAXIES` at `:161-163` still 1.0/1.0, and the file's own comment at `:156-160` says "FOR THE OWNER, AND LEFT FOR THE OWNER". `census('POCKET')` and `census('MINOR')` refuse today at `:295-300`.
QUESTION:   Is the prose right (the multipliers are wrong by ~6 orders of magnitude), or are the multipliers right (the prose and the ceiling are wrong)?
OPTIONS:    (a) multipliers wrong — MINOR nearer 5e-12, POCKET smaller again; prose stands  (b) descriptions wrong — raise or remove `SIZE_CLASS_MAX_GALAXIES` and rewrite the prose
RECOMMEND:  (a). The charter's own II.N.3 exception class — "the small universes that re-run themselves", the Basement Loop and the Rot City of ANEURISM IV — describes sub-galactic pockets, which is what the prose says. Nothing in `src/` moves either way: every caller of `census()` passes `'STANDARD'` (`address_space.py:397-398`, `pipeline.py:1896`, `verify_math.py:178/771/773`).
COST IF WRONG: (b) makes POCKET — "a closed loop, a demiplane, one stage and no sky" — a 200-galaxy universe holding twelve galaxy-spanning Type III civilisations. Either way the fix is one line.
UNBLOCKS:   none (parent `be783948fd66` already closed)
THEME:      charter arithmetic

---

### 4e37d5e59b09  [OWNER] [MAJOR] — Local rung closed by a pinned llama-server; recorded mechanism refuted
STILL LIVE: **NO.** The remedy was "restart the Ollama runner", and it happened. `tasklist /FI "PID eq 29452"` returns no task — the pinned `llama-server` this order names is gone; today's pair is `ollama.exe` pid 42876 and `llama-server.exe` pid 32776. `state/OLLAMA_RESTARTS.json` records `{"count": 12, "last": 1788311477}` — ~2026-09-01, four days after this order was filed. The DO-NOT half was honoured too: `config.yaml:82` still reads `num_ctx: 12288`. And order `171ade4c7d27`'s 2026-09-03 measurement put a real task through `local_agent --no-apply` successfully in 5m52s at rc=0, which retires the "rung is still closed" headline outright.
QUESTION:   None — close it.
OPTIONS:    (a) close as done  (b) keep open as a standing watch on llama-server residency
RECOMMEND:  (a) — close. Named process gone, restart on the record, `num_ctx` not lowered, rung measured working by a later order.
COST IF WRONG: none to this order. The residual operational fact — `llama-server.exe` pid 32776 currently holds an 8.2 GB working set with an effectively-infinite `keep_alive` — is a standing condition, not this finding; file a fresh watch item if it is wanted.
UNBLOCKS:   retires the mechanism claimed by `a8464e348c5e` and `505177847f43`, both of which attribute the stall to a num_ctx mismatch this order measured as false.
THEME:      dead — already fixed

---

### 5bbd4b3376fe  [OWNER] [MAJOR] — Coverage checks string-match against un-stripped thinking text
STILL LIVE: yes — `generate.py:255` is `t = text.lower()` over the whole model response, with no think-tag stripping anywhere in the module; `_deed_traced` at `:262-274` ends `return probe.lower() in text.lower()`; `_deed_shortfall` at `:285-293` runs every deed through it. `config.yaml:37` still reads `model: "qwen3:8b"`, a thinking variant.
QUESTION:   This is the SAME question as `342ccfafa4a4` — by which of three routes does the project stop think-tag text from reaching any check or any disk write?
OPTIONS:    (a) configure a non-thinking model variant  (b) strip `<think>...</think>` once at the transport boundary, before any check or write sees the text  (c) pass `think: false` on the Ollama call
RECOMMEND:  (b), with (c) alongside since it is free and also reduces the tokens the context-budget squeeze is about. (b) is the only route that survives a model swap, and it fixes `_covered`, `_deed_traced`, think-tags-reaching-disk and the budget squeeze in one place rather than four.
COST IF WRONG: patching `_covered` alone leaves the identical false positive in `_deed_traced` and in `prose_gate`; (a) alone re-opens the whole class the moment `config.yaml:37` changes. The failure this guards is a thinking model naming an entity while planning ("now for Entity X...") and never writing its Entry-Template text — `_covered` returns True, no retry fires, and `prose_gate.assert_block_complete` becomes the ONLY check left, collapsing Hard Rule -1's three independent layers to one for exactly the class Layer 3 exists to catch. Not urgent: `config.yaml:108` has `prose_enabled: false`, so nothing runs against this today. **This is a before-you-open-the-gate item.**
UNBLOCKS:   `342ccfafa4a4` and `3859043e365e` — same root cause, one ruling settles all three.
THEME:      thinking-model contamination

---

### e8466cd6ed14  [SESSION] [MAJOR] — chain.main() exits 0 over a CHAIN.json that was never written
STILL LIVE: yes, and it has grown. `chain.py:154` is still an unconditional `return out` after the denial branch at `:151-153`. `main()` now has THREE `write_result` call sites — `:809` (already `return 1`, the refusal path), `:833` and `:852` — of which `:833` and `:852` both discard the return and fall through to `return 0` while printing `-> {OUT}`. The order's cited `:715`/`:734` have drifted to `:833`/`:852`.
QUESTION:   **Reroute to RUN/LOCAL — no ruling needed.**
OPTIONS:    (a) reroute as written  (b) hold on SESSION
RECOMMEND:  (a). The order supplies the remedy, the precedent (five sibling sites closed under rulings `dc5c92aad5c1` / `3e65dbed45a6` at `onomast.py:569-573`, `reference.py:363-373`, `genre.py:327-331`, `sevenfold.py:412-415`, `wh40k.py:289-293`), and the trap. Factor `pipeline._chain_landed`'s body into `chain.py` so both callers share one implementation.
COST IF WRONG: nothing — but the order's DO-NOT is load-bearing: widening `write_result`'s signature to `(out, landed)` breaks drill.py's phase-4 net, which drives `pipeline.phase_chain` against a stand-in whose write_result is `lambda edges, res, unmatched: doc` (`chain.py:91-98`).
UNBLOCKS:   none
THEME:      write-denial blindness

---

### bc4156603071  [OWNER] [INFO] — Where on the attestation scale an unrecognised grade belongs
STILL LIVE: yes as a ruling — the fixable half already landed. `assay.py:1479-1486` now carries the corrected comment ("WHERE IT ACTUALLY SITS, corrected 2026-09-06 ... 0.30 sits between TRANSCRIBED and RECONSTRUCTED"), and `_check_constants` at `:676-682` refuses at import if the floor is at or below the best recognised grade. `ATTESTATION_FLOOR_UNRECOGNISED = 0.30` at `:1488` is untouched.
QUESTION:   Did the charter mean an unrecognised grade to sit between Reconstructed (0.40) and Disputed (0.55), or between Transcribed (0.20) and Reconstructed (0.40)?
OPTIONS:    (a) the comment recorded the intent — raise the constant to ~0.48  (b) the constant is right — 0.30 stands and the corrected comment is the final word
RECOMMEND:  (b). Order `13a678071cbf`, which introduced this constant, ruled that "the value was never the defect and must not be retuned as if it were." (a) tightens every `interval_from_hands` reading carrying an unrecognised grade — and through `custodes._ATT_BASE` every Custos' evidential part on such a reading — on the strength of a prose sentence that has since been corrected.
COST IF WRONG: (b) leaves an invented grade treated as better evidence than the charter intended. (a) moves published intervals for a comment, which is exactly what the prior ruling forbade.
UNBLOCKS:   none
THEME:      charter constants

---

### a78d5cd748b2  [OWNER] [MINOR] — Five dead physical constants in a module nothing reaches
STILL LIVE: yes — `scale_theories.py:23-27` still declares `C_LIGHT`, `G_NEWTON`, `HBAR`, `NUCLEAR_DENSITY`, `PLANCK_LENGTH`, each occurring exactly once in the tree with no importer; `descending_ladder.py:60` still carries "scale_theories.py names the same value as G_NEWTON"; `liveness.py:269` still lists scale_theories among the NEVER REACHED modules.
QUESTION:   Really only one question — is `scale_theories.py` kept at all? The five constants fall out of that answer.
OPTIONS:    (a) delete the five, following the chord_field precedent, and fix `descending_ladder.py:60`  (b) rule on the whole module, which subsumes (a)  (c) keep and annotate
RECOMMEND:  (b). Deleting five dead constants from a module nothing imports buys nothing while touching a file already flagged for the larger question, and the house precedent is already settled twice over — `chord_field.py:35-44` keeps only the constants it uses, and `verify_math.py:9182` pins that `tempus.py` no longer carries a dead `C_LIGHT`.
COST IF WRONG: (a) alone silently makes `descending_ladder.py:60`'s comment false, and that comment is part of how the duplication was meant to stay visible.
UNBLOCKS:   a keep-or-drop criterion for never-reached modules settles the `render 707fefc17465` / `scale_theories SWEEP34_FINDING` pair that both `liveness.py:269-271` and `drill.py:82-83` name.
THEME:      dead module

---

### 68459d3e739b  [OWNER] [MINOR] — Franchise rank-agreement rests on a single franchise
STILL LIVE: yes for the coverage half; the code half is closed. `rosetta.assays_by_host` exists at `rosetta.py:399`, `check()` takes `by_host` at `:427`, and the explicit UNSCORED row prints at `:765`. The coverage is unchanged: measured this shift, `data/ASSAYS.json` still holds 507 entries of which 217 carry a decimal, and `data/ROSETTA.json` still holds exactly 8 scales — only `dragonball.fandom.com | List of Power Levels` has enough same-wiki assays (32 on that host) to score; `onepiece.fandom.com | Bounty/List` still has 96 rows behind too few host assays to reach the 4-name floor.
QUESTION:   Is it worth assaying more entities on the seven wikis that publish a native scale?
OPTIONS:    (a) target assays at the seven unscored scales — One Piece's Bounty/List at 96 rows is the cheapest, it needs 4 overlapping names  (b) accept one-franchise coverage and make the verifier say so in its own output  (c) both
RECOMMEND:  (c), with (b) first because it costs nothing and the UNSCORED row added by the fix already gets most of the way there. The assay work in (a) is a content decision only the owner can size.
COST IF WRONG: (b) alone leaves an allsweep verifier — this module's entire stated purpose — resting for good on one franchise at n=4, rho=0.6.
UNBLOCKS:   none (parent `0bba50a6d76b` already closed)
THEME:      verifier coverage

---

### ec05033115d6  [OWNER] [INFO] — generate_job keeps calling the GPU for a chapter already doomed
STILL LIVE: yes — `generate.py:439-440` still `parts.append(text.strip())` / `missing.extend(...)` inside the block loop, with `if missing: raise ChapterRefused(...)` at `:441-447` only after every block has been attempted.
QUESTION:   Break out of the block loop on the first unrecoverable `lacking`, or keep going?
OPTIONS:    (a) keep current behaviour — complete diagnostics, more GPU on doomed jobs  (b) break on first unrecoverable miss — cheaper, partial diagnostics  (c) keep going but skip the model call: derive the remaining blocks' `lacking` from the entry list without generating
RECOMMEND:  (c) — not in the order, and it dissolves the trade-off. `ChapterRefused`'s docstring insists on the FULL offender list, and every entity in a block that was never attempted is by definition missing, so the complete list can be assembled at zero GPU cost with no `call_ollama` through `gpu_lane`.
COST IF WRONG: (b) truncates the "which entries a chapter failed on" record that order `4e437987e382` was filed to protect. (a) burns several full generations per doomed chapter on the one GPU CLAUDE.md records at 99% utilisation. Nothing pays this today — `prose_enabled: false`.
UNBLOCKS:   none
THEME:      doomed-job GPU cost

---

### 12c457975677  [SESSION] [INFO] — assay.REFERENCE_JOULES is a 14-entry table nothing reads
STILL LIVE: yes — grep across `src/` returns only the definition at `assay.py:195`; the comment at `:193-194` still claims "for converting described feats into joules"; `magnitude.py:411` still carries the overlapping live unit table.
QUESTION:   Wire it into magnitude's converter, or mark it documentary and correct the comment?
OPTIONS:    (a) wire it — magnitude reads one table instead of two  (b) mark documentary, the way `assay.HANDS` is prose-in-a-dict
RECOMMEND:  (b). The two tables do genuinely different jobs — magnitude parses units out of prose ("kiloton", "kilotons"), this one names whole feats ("hiroshima", "continent_shatter") — so merging them would put feat names into a unit parser. The real defect is a comment claiming a purpose the table does not serve.
COST IF WRONG: (a) risks the unit parser matching on "supernova". Either way, **do not delete** — several band edges are calibrated against these values.
UNBLOCKS:   same underlying policy question as `47067a8f0ad5` and `1eb00a84225e` — "correct the comment vs. delete an unread name" — one rule settles all three, and (b) is that rule.
THEME:      unread constant

---

### 47067a8f0ad5  [SESSION] [INFO] — catalogue_web constants justified by an importer that does not exist
STILL LIVE: yes, half of it. `catalogue_web.py:55` and `:60` are both still `None` and grep across `src/` finds no importer anywhere. `CATEGORY_SCAN_DEPTH`'s comment at `:56-59` already concedes "nothing reads it"; `MAX_PER_CATEGORY`'s at `:54` still claims "kept only as a name other code may import", which is the untrue sentence left standing.
QUESTION:   Delete both, or correct `:54` to match its sibling's honesty?
OPTIONS:    (a) delete both  (b) keep both and correct `:54` to say they are retained as documentation of a removed cap, with no importer
RECOMMEND:  (b). The comment at `:429` — "Was `if len(titles) > MAX_PER_CATEGORY:`" — carries the history of the TypeError the neutralised cap caused for every non-empty category, and the names being present is what keeps that comment legible. One corrected sentence stops the next sweep re-deriving that nothing reads them.
COST IF WRONG: (a) is harmless to the code but leaves `:429` referring to a name no longer in the file. Note there is no `burgs.GENERATORS`-style rescue available here — no use exists to wire them to.
UNBLOCKS:   same policy question as `12c457975677` and `1eb00a84225e`.
THEME:      unread constant

---

### 85a6b7b9e2c8  [SESSION] [INFO] — pick_model claims MoE markers disqualify; the gate is size only
STILL LIVE: yes — `pick_model.py:82` still reads "STILL DISQUALIFYING under the residency mandate below", `:251` still repeats it, `resident()` at `:192-194` is purely `weight_gb(m) + KV_GB <= budget_gb`, and `is_moe` at `:230-231` survives only to choose the word "MoE" in fit_note's warning at `:256`.
QUESTION:   **Reroute to RUN/LOCAL — no ruling needed.**
OPTIONS:    (a) reroute with the order's own clause  (b) hold on SESSION
RECOMMEND:  (a). "No longer buys any tolerance; MoE models are refused by the size gate like everything else, and this list now only labels the warning" is true under BOTH of the readings the order lays out, so nothing is actually being decided.
COST IF WRONG: nothing. Flagged separately, not part of this ruling: on a 10 GB card an MoE model often outperforms a dense one that nominally fits, so if MoE should ever buy tolerance again, that is a NEW question and this edit does not foreclose it.
UNBLOCKS:   none
THEME:      stale claim in comment

---

### 2b695c192470  [OWNER] [MINOR] — sweep.load has no caller anywhere in src/
STILL LIVE: yes, but reduced to one clause — the docstring half is DONE. `sweep.py:87-90` now reads "The live path today is `cachekey.load` inside `sweep()`; `load` itself currently has no caller (order 2b695c192470)", and the false ":129" claim is gone from both `sweep.py` and `verify_math.py:4805-4813`. Only the curatorial call remains.
QUESTION:   Delete `sweep.load`, restore a caller, or record it as a kept public helper?
OPTIONS:    (a) keep as a kept public helper — one line saying so, then close  (b) delete it and the `verify_math` §21 section that is now its only exerciser  (c) restore a caller
RECOMMEND:  (a). `verify_math.py:4807-4813` already argues the case: what §21 pins is the miss/corrupt SPLIT, and that split is the repair that took the swallowed-failure ledger from 18,418 of 21,764 entries being one expected absence back to meaning something — the same contract the live `cachekey.load` path has to keep for the caller that exists today.
COST IF WRONG: (b) deletes the only place that contract is asserted. (c) invents a caller for a job `cachekey.load` already does.
UNBLOCKS:   none
THEME:      callerless helper

---

### 1eb00a84225e  [OWNER] [MINOR] — address_space.UNADDRESSED is a name for a decision nobody takes
STILL LIVE: yes — now at `address_space.py:141` (drifted from `:133`), still `UNADDRESSED = None`, with no other reference in `src/`. (`threads.UNADDRESSED` at `threads.py:109` is a DIFFERENT constant whose value is `"UNASSIGNED"`; `drill.py:10086`'s `TH.UNADDRESSED` reads that one, not this.)
QUESTION:   Wire it into the missing-tier case, or delete it?
OPTIONS:    (a) wire it into the missing-tier case  (b) delete it  (c) defer — answer it as a rider on the MAJOR `address_space.py:275` missing-tier order
RECOMMEND:  (c), and this one leaves the desk today. The constant's comment — "a shelf in no hyperverse: it shares no entity with anything" — is the honest answer for precisely that case, so if the missing-tier ruling goes the way the comment assumes, this is already written; if it does not, deleting is one line. It should not consume an owner decision ahead of the order it depends on.
COST IF WRONG: none material — the only risk is spending a ruling out of order.
UNBLOCKS:   none; it is BLOCKED BY the MAJOR `address_space.py:275` order. Attach it there.
THEME:      unread constant

---

### 372d4a8c8d46  [OWNER] [MINOR] — runguard compare-and-swap check-then-act window
STILL LIVE: **NO.** Two things killed it. First, the `where` was never right — `replace_if_unchanged` lives at `silence.py:553`, not in `runguard.py` (runguard merely calls it at `:130`). Second, the ask was "either write the reasoning down or close the window", and the reasoning is now written in the function itself at `silence.py:586-590`: "A narrow window remains and always will — there is no atomic compare-and-rename on this platform — but it is now microseconds of syscall rather than seconds of backoff." The window was also narrowed under order `fede605db64f`: the loop now re-digests immediately before each `os.replace` instead of handing the rename to `replace_retry`'s 0.3/0.6/0.9/1.2s backoff, measured at 117-120 of 120 rows kept against 55-86 before.
QUESTION:   None — close it.
OPTIONS:    (a) close as done
RECOMMEND:  (a). Both halves of the ask were satisfied by a later order; the next reader no longer has to re-derive anything.
COST IF WRONG: none.
UNBLOCKS:   none
THEME:      dead — already fixed

---

## ROLL-UP

| | count | ids |
|---|---|---|
| still live | 18 | all but the two below |
| **dead — remove from the desk** | **2** | `4e37d5e59b09` (runner restarted, pid gone, rung measured working), `372d4a8c8d46` (reasoning written down at silence.py:586-590; `where` was always wrong) |
| **reroute to RUN/LOCAL — no ruling** | **3** | `b9584c782d95`, `e8466cd6ed14`, `85a6b7b9e2c8` — plus 2 of the 6 sites inside `728d9e99e9ec` |
| **defer onto another order** | **1** | `1eb00a84225e` → the MAJOR `address_space.py:275` missing-tier order |
| **one answer settles several** | | `5bbd4b3376fe` + `342ccfafa4a4` + `3859043e365e` (think-tags); `728d9e99e9ec` + `74f1bc47da2a` (ledger escapes); `12c457975677` + `47067a8f0ad5` + `1eb00a84225e` (unread names); `3eff62be6cc3` + GENRES sibling (stale confidences); `40e98eed6870` + `ad681057369a` (dead vocabulary) |

**Net: 20 orders in, 14 actually need the owner.**

### Three highest-value decisions
1. **`728d9e99e9ec`** — name a "live operational state" third-party class. Highest-leverage fix in the queue: it ends the battery non-determinism that has spoiled three mutation passes, removing ~15 real DNS + Ollama-generate + PowerShell round-trips per run against ~67 note sites that can each redden §20z for something that is not this library's fault. One decision, ~1 hour, and it also answers `74f1bc47da2a`. Must not land while pid 68112's pass is running.
2. **`5bbd4b3376fe`** — strip think-tags at the transport boundary. One ruling closes three orders and restores Hard Rule -1's three independent layers from the one they currently collapse to. Do it before `prose_enabled` is ever opened, not after.
3. **`d44b106ce7e3` Q3** — write the one sentence naming which entry points must call `assert_clear` ("every entry point that WRITES outside `output/` and `state/`; read-only instruments do not"). It corrects a docstring that is true of 17 of 98 and settles `aad11acb1183`, the withdraw_chapters order, and ~81 uninspected cases at once.
