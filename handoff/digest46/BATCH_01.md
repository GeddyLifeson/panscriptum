# OWNER DECISION DIGEST — BATCH 01

19 open OWNER/SESSION orders, each verified against the live tree on 2026-09-07.
Read-only pass: nothing in `src/` was touched, no order was closed, no gate was moved.

**6 of 19 are DEAD** — the code moved under them and they can come off the desk.
**13 are still live**, of which **5 need no ruling at all** and should drop to RUN/LOCAL.

---

### 44c420f80448  [SESSION] [MAJOR]  — Sweep batch plan reshuffles mid-run and falsifies the coverage ledger
STILL LIVE: **NO** — the remedy this order asks for is already in the tree. `src/sweep_plan.py:249` `def freeze_plan(run, n=16)` computes the plan once and lands it; `batches(n, snapshot=None)` at :112 now takes the frozen table (`"Pass the table freeze_plan() stored and the plan is reproducible"`, :128), `frozen_plan()` at :163 refuses every unreadable/malformed case rather than silently recomputing, and `check_briefs()` at :819 diffs against the frozen plan rather than a live repack. Landed as order 4d44a6363245 (closed). Frozen plans exist on disk: `state/sweep_plan/run46.json` (`frozen: True`, 16 batches, carries `src_table_digest`) and `state/sweep_plan/sweep45.json`.
QUESTION:   Nothing — but one half of the remedy was declined and the owner may want it: should `record()` refuse a `covered` list that disagrees with the frozen plan?
OPTIONS:    (a) close it as done; (b) close it and file the `record()` cross-check as a fresh RUN item; (c) leave open.
RECOMMEND:  **(b)** — the partition is frozen, which was the load-bearing fix, so the coverage ledger can no longer be falsified by drift. `record()` still writes whatever list it is handed (`src/sweep_plan.py` `record()` docstring: "IT DOES NOT RAISE, deliberately"), which is a deliberate design choice, not an oversight; make it a separate, small item rather than keeping a MAJOR open.
COST IF WRONG: Nothing breaks. Leaving it open costs the owner a re-read of 4,000 words describing a fixed bug.
UNBLOCKS:   `b86d79c574e3` (identical finding, different batch — close both on one answer)
THEME:      sweep partition stability

---

### b86d79c574e3  [OWNER] [MAJOR]  — Same batch-instability finding, filed independently by sweep39 batch 9
STILL LIVE: **NO** — same kill as above. `freeze_plan()` at `src/sweep_plan.py:249` implements this order's own stated remedy almost verbatim ("have batches() take a run id, compute the pack once, and persist it (e.g. state/SWEEP_PLAN.<run>.json)"); the file lives at `state/sweep_plan/<run>.json` per `plan_path()` at :156. `batches()`'s docstring at :117-126 now records this exact run39 measurement as the reason the `snapshot` parameter exists.
QUESTION:   Nothing to decide. The only residual is the coordination question the order raised at the end: was run39 ever re-dispatched over a frozen plan?
OPTIONS:    (a) close as superseded; (b) close, and ask a run to check `sweep_plan.missing('run39')` once for the record.
RECOMMEND:  **(b)** — one command settles the historical gap this order flagged, and the mechanism that created it cannot recur. Do not spend an owner slot on the design question; it was answered.
COST IF WRONG: None. run39 is three runs old and every run since has been dispatched from a frozen plan.
UNBLOCKS:   `44c420f80448` — one answer closes both
THEME:      sweep partition stability

---

### dc9ffadae765  [SESSION] [MINOR]  — Work-order evidence cites line numbers nothing has ever checked
STILL LIVE: **YES** — and re-measured today, smaller but confirmed. The queue is now 297 open orders (was 458) carrying 1,231 `file.py:NNN` citations across 216 orders (was 2,898 across 393). Past-EOF citations are now **0** (was 5), so the only automated detector conceivable has nothing left to find. The wrong-line-within-the-file case is untouched and **has drifted further**: both example orders are still open, and `derivation.py` now has `SCAN_MODULES` at :575 (order cites :477, this finding measured :543) and `scan_constants` at :657 (order cites :481-500, finding measured :617). Two drifts in ten days on the same two symbols.
QUESTION:   Should the house require work orders to cite by SYMBOL rather than by line number?
OPTIONS:    (a) rule "cite by symbol" as a filing convention and let the existing citations rot; (b) also build a resolver that reads each cited line and checks the named symbol is on or near it; (c) leave as is.
RECOMMEND:  **(a) now, (b) as a RUN item** — (a) costs one sentence in the filing rule and stops the bleeding at source; it is also what `generate.py`'s own silence.note site already says. (b) is real work with no judgment in it and belongs on RUN, not here.
COST IF WRONG: Owners keep re-deriving findings from proofs that point at the wrong lines. Nothing becomes untrue; confirming it just costs a grep each time.
UNBLOCKS:   none in this batch, but the same ruling covers the source-comment citation orders filed every sweep
THEME:      citation drift

---

### fbc0930ae309  [OWNER] [MAJOR]  — Proving a behavioural drill net works currently costs a library outage
STILL LIVE: **YES** — verified. `src/drill.py:393-408` has `_SRC_OVERRIDE` / `_srcdir(src)` for SOURCE-SHAPE nets only, and it is used that way throughout (e.g. `_ast_of(os.path.join(_srcdir(src), "threads.py"))` at :10113). There is **no** helper that copies `src/` to a throwaway root, applies a caller-supplied reversal and runs ONE net there: no `copytree` of `src/` anywhere in drill.py's 13,665 lines, and the only CLI flag is `--to-halt` (:13465). The ad-hoc harness written that shift was not kept.
QUESTION:   Should behavioural nets get the same scratch-tree affordance source-shape nets already have, so proving a guard does not require halting the library?
OPTIONS:    (a) build the permanent harness in drill.py (copy src/ to a temp root, apply a reversal, run one net, report HELD/RED, never touch the live tree or HALT.json); (b) keep reverting the live tree and accepting a self-caused halt each time; (c) build it, and additionally require every new net to be exercised in the mutate.py sandbox world as well as the live one.
RECOMMEND:  **(c)** — the sharper half of this order is not the outage, it is that two of that net's three versions were wrong in opposite directions and only running it in more than one world revealed it. The dangerous failure is version 2: a net red in mutate's baseline is DISABLED as a detector for that whole run, so a misfiring net would silently switch off a 20-hour mutation pass rather than cry wolf.
COST IF WRONG: Choose (b) and every future guard costs a self-caused DRILL_BREACH — local_agent refuses to start, mutate.py refuses to run — which trains everyone to skip the proof step, which is the failure Hard Rule -1 exists to prevent.
UNBLOCKS:   `850786a2fee4` — a safe single-net runner is also what makes firing nets from a daemon thinkable
THEME:      drill net provability

---

### 3859043e365e  [OWNER] [INFO]  — Generate's output reserve does not account for a reasoning model's thinking tokens
STILL LIVE: **YES** — nothing has moved. `src/context_budget.py:97-98` still has only `DEFAULT_RESERVE_TOKENS = 1024` and `CHAPTER_RESERVE_TOKENS = 2048`; no `THINKING_RESERVE_TOKENS`, and grep for `thinking`/`reasoning` in that file returns nothing. `src/generate.py:230` still sends `"num_predict": -1` with no `think` key anywhere in the file. `config.yaml:108` still `prose_enabled: false`, so nothing is running against it.
QUESTION:   Does the output reserve need a thinking term, or should generate.py ask qwen3 not to think?
OPTIONS:    (a) measure first — one generation at the live window recording `eval_count` split between `thinking` and `response`, then decide; (b) add a `THINKING_RESERVE_TOKENS` term to the reserve; (c) send `think: false` on the /api/generate call; (d) do nothing until the prose gate opens.
RECOMMEND:  **(a)** — the order names exactly the measurement that would settle it and nobody has taken it. (b) and (c) are different decisions (one changes the refusal threshold for every job, the other changes what the model is being asked to be) and you should not pick between them on an estimate. Cheap, and it can be done with the gate closed.
COST IF WRONG: Pick (c) blind and you silently change the model's behaviour for every job. Pick (d) and the first prose run after the gate opens shows an elevated refusal rate whose cause takes a shift to find — though the two downstream guards (`prose_gate.assert_block_complete`, `_covered`) mean it fails in the safe direction.
UNBLOCKS:   none
THEME:      prose budget sizing

---

### 51f0be4252e6  [SESSION] [MAJOR]  — Escalation fail-open regex matches a shape that exists in no file
STILL LIVE: **NO** — the AST predicate this order asks for was built and landed as order 6dc4bde7fab6. `src/verify_math.py:6383-6408` defines `_interlock20p()`, an `ast.Try` walk over every `_INTERLOCKED` file; :6414 pins the guard COUNT per module (`_EXPECT20p = {"overnight.py": 2, "publish.py": 2}`) so a deleted guard is caught, not just a weakened one; :6432-6444 report three named lists (`_noguard20p`, `_openguard20p`, `_noclear20p`) as file:line, not booleans. The two-sided controls the order specified are at :6448-6470, including the negative control `check("[control] and it does not cry wolf on the real fail-closed shape", _interlock20p(_ok20p), ([1], []))`. The old regex row survives at :6340-6349 but is explicitly demoted — the note on the sibling row at :6351 now reads *"The interlock guarantee rests on the AST rows below, not here"*.
QUESTION:   None. Optionally: should the superseded regex row be deleted or left as a cheap tripwire?
OPTIONS:    (a) close as fixed; (b) close and file a tidy-up to drop the dead regex row.
RECOMMEND:  **(a)** — leave the regex. It costs nothing, its own note now tells a reader it is not load-bearing, and removing a row from a Hard Rule -1 section to save four lines is a bad trade.
COST IF WRONG: None.
UNBLOCKS:   `3e11c452ff67` — same fix killed both
THEME:      interlock guard strength

---

### 24155b641dfa  [OWNER] [MAJOR]  — Bloons secret-scan waiver lost its scope caveat to a 300-character cap
STILL LIVE: **YES** — measured on disk today. `data/SUPPRESSIONS.json` holds three rows, reason lengths 175, 137 and exactly **300**. The 300 one is `secret_scan` on `data/feats/bloons_fandom_com/Encrypted.json`, ending `"...on a full re-scan of the export SITE tree; this only sur"`. The CODE cap is gone (`src/suppressions.py:123` — "THE REASON IS STORED WHOLE (order 7a6362fa3c91). This was `str(reason).strip()[:300]`"), so the next reason written survives; this one cannot be recovered. Row metadata: `added_by: run35-L1-2026-08-26`, `expires_at: 1803357126` = **2027-02-21**, not 2026-02 as the order estimated — the waiver stands unreviewable for another five months if nothing is done.
QUESTION:   Is the Bloons secret-scan exemption still narrow enough to stand, and who restates its scope caveat?
OPTIONS:    (a) re-justify: `suppressions.add('secret_scan', 'data/feats/bloons_fandom_com/Encrypted.json', '<whole reason>')` now stores it uncapped and replaces the row by detector+path; (b) delete the row so the finding reports again and gets reviewed from scratch; (c) rewrite the reason to say explicitly that the caveat is unrecoverable, and keep the waiver.
RECOMMEND:  **(a) if you can state the caveat, (b) if you cannot** — what is known from the surviving text is that this is mined Bloons TD 6 wiki prose about an in-game Easter egg on the map "Encrypted", not a credential, so (b) costs one re-review and no risk. Do **not** let a run invent a replacement sentence: that is manufacturing the evidence a reviewer is supposed to weigh, on the file that decides what a secret scanner may wave through.
COST IF WRONG: Choose (c) and a live secret-scanner exemption on a real data file stands until 2027-02 with no reviewable scope. Choose (b) needlessly and you re-review a known-benign Easter egg once.
UNBLOCKS:   `f5503302ce44` — same row, same decision, filed twice
THEME:      suppression evidence

---

### 850786a2fee4  [OWNER] [MAJOR]  — No drill net fires before a model-authored patch to live source is kept
STILL LIVE: **YES** — verified line by line. `src/foreman.py:1309` `_checks_pass(module)` runs exactly three things: `import <module>` (:1315), `verify_math.py` read for a passing RESULT line (:1318-1331), and `allsweep.py --quick` gated on rc (:1332-1360). `grep -c drill src/allsweep.py` = **1** (a passing mention, not a verifier). So none of the drill battery's nets fires before a patch is kept. The DENYLIST half is confirmed closed — `src/foreman.py:120-121` now reads `{"foreman", "silence", "health", "allsweep", "estate", "standards", "verify_math", "drill", "escalation", "codewatch", "liveness", "overnight"}`.
QUESTION:   Should `_checks_pass` fire the drill before keeping a model-authored patch, given that a standing daemon running drill.py is exactly what a standing rule forbids?
OPTIONS:    (a) leave as is — the DENYLIST removal of drill/escalation/codewatch/liveness/overnight already took the sharp edge off, and foreman's docstring (:41-51) describes three checks honestly; (b) add `python src/drill.py` to `_checks_pass`; (c) add a bounded SUBSET of nets safe to run from an agent context, once the scratch-tree harness of `fbc0930ae309` exists.
RECOMMEND:  **(a) now, (c) later** — (b) is the one option to refuse: `verify_math.py:5504` records that verify_math and drill "are not safe to run" from an agent context, and drill historically wrote trial values of `prose_enabled` into the live config (`verify_math.py:4845-4847`). Having a standing daemon run the full drill on every kept patch does the forbidden thing on a loop, and it lengthens a gate whose remedy timeouts are deliberately bounded under the round interval.
COST IF WRONG: Choose (a) and a patch that weakens a comparison INSIDE a net is kept — verify_math's ~30 source-level assertions catch a deletion, not a weakening. Choose (b) and you hand a daemon the drill, which is how the gate flag gets moved by something that is not a person.
UNBLOCKS:   `fbc0930ae309` — (c) is only reachable once that harness exists; answer them together
THEME:      patch gate strength

---

### 1a9c237dda4d  [OWNER] [INFO]  — Four public symbols in ledger.py and tempus.py with no reader anywhere
STILL LIVE: **YES** — re-verified by grep across every `*.py`. `ledger.STANDARD_GLYPH` (:45), `ledger.CONDENSATES` (:71) and `tempus.concordance_now` (:128) have exactly one hit each: their own definition. `ledger.currency_status` (:87) has three: its definition plus two docstring cross-references at ledger.py:108 and :117 — mentions, not callers.
QUESTION:   Are these reference data awaiting a consumer, or leftovers?
OPTIONS:    (a) add one line to each saying "no consumer yet; retained as reference data per owner ruling <date>"; (b) delete them on tempus.py's own precedent (:43-48 removed SECONDS_PER_YEAR and C_LIGHT for exactly this reason); (c) name the intended caller for each.
RECOMMEND:  **(a)** — and this is the answer to a whole class, not three symbols. A one-line retention marker stops every future sweep re-finding them, which currently costs more than the finding is worth. `CONDENSATES` encodes the material Chord (W.7) and `currency_status` encodes a considered distinction between an unlisted and a deliberately non-convertible currency; neither should be deleted on an audit's judgment.
COST IF WRONG: Choose (b) and you delete doctrinal data an audit did not understand. Choose (a) wrongly and you keep four unused symbols — a rounding error against re-litigating them every sweep.
UNBLOCKS:   `3fb312a72435`, `946153deafe9` — all three are the same question: **what does this house do with correct code that has no caller?** One standing ruling settles all three and every future sighting.
THEME:      orphan code policy

---

### 3fb312a72435  [OWNER] [MAJOR]  — hosts.py fixes the single-host cap and nothing in the pipeline calls it
STILL LIVE: **YES** — and the inert work is bigger than the order recorded. `grep -rn "from hosts import|import hosts"` across every `*.py` in the repo returns **zero hits**, including from hosts.py itself. `data/SOURCE_HOSTS.json` (11,583 bytes, written 2026-08-22) holds real discovered data: **73 sources carry 94 extra host records** with scores and evidence, e.g. `Bleach -> en.wikipedia.org, about=1.0 lift=-0.112, score 0.35`. `src/feats.py:50` still reads `HOSTS = data/WIKI_HOSTS.json` (208 sources, one host each). So 94 verified readable hosts across 73 of 208 sources are sitting on disk unread.
QUESTION:   Wire hosts.py into the mining path, or delete it and accept one host per source?
OPTIONS:    (a) wire it in — `feats.py` reads `hosts_for()` instead of WIKI_HOSTS directly; (b) delete hosts.py and SOURCE_HOSTS.json; (c) leave dormant with a retention marker.
RECOMMEND:  **(a)** — deletion is the option to refuse. The standing house rule is that a cap is a truncation hiding a smaller universe, and hosts.py exists precisely to remove one: its header states the fault plainly, that WIKI_HOSTS holds "194 sources, 194 strings, zero lists" and that reading one host and calling a source covered "is the same error as reading one page of an entity and calling the entity read". The work of finding those 94 hosts is already done and paid for.
COST IF WRONG: Choose (b) and you re-accept the single-host cap and throw away 94 measured hosts. Choose (a) and mining volume rises against a domain that has IP-banned this machine once already — so wire it in behind the existing fetch throttling, not ahead of it.
UNBLOCKS:   `1a9c237dda4d`, `946153deafe9` — same orphan-code question, but this one is the exception: here the orphan removes a documented cap, so the class ruling should not sweep it into "retain and mark"
THEME:      orphan code policy

---

### f5503302ce44  [OWNER] [MINOR]  — Suppression reason still truncated on disk after the code cap was removed
STILL LIVE: **YES** — same measurement as `24155b641dfa`. Three active rows at 175 / 137 / 300 characters; the 300 is the Bloons `secret_scan` waiver, still ending mid-word at `"this only sur"`. `src/suppressions.py:123` confirms the code cap is gone and the surviving comment records what it already ate.
QUESTION:   Identical to `24155b641dfa` — this order and that one are the same finding filed by two different sweeps.
OPTIONS:    Same three: (a) re-justify whole; (b) delete the row; (c) state explicitly that the caveat is unrecoverable.
RECOMMEND:  **Answer `24155b641dfa` and close this one against the same ruling.** The only thing this filing adds is the sharper phrasing of why (c) is not good enough: a reviewer reading `"...this only sur"` cannot tell a truncation from a typo.
COST IF WRONG: Nothing extra — but leaving two orders open on one row means the second gets re-triaged after the first is resolved.
UNBLOCKS:   `24155b641dfa`
THEME:      suppression evidence

---

### cefcad5fc513  [OWNER] [MINOR]  — Step-4 enforcer assert_step4_open has no caller and is unwired
STILL LIVE: **NO** — remedy (1), the part that mattered, is landed, and remedy (2)'s precondition has arrived and is satisfied by other means. The drill net exists: `src/drill.py:1311-1313`, `net(a, "assert_step4_open RAISES when closed", lambda: _refuses(lambda: PG.assert_step4_open({}), PG.ProseRefused), ...)` — so the enforcer can no longer be deleted as dead code, which is what the order asked for "NOW". The entanglement pass now HAS an entry point, `src/threads.py`, and it is gated: `threads.py:647` `ok, why = PG.step4_gate_open()`, then :652-659 `if not ok: print("REFUSING TO WRITE %s")... return 3`, with a further drill net at :10106-10121 asserting via the parse tree that `main()` consults the gate before it writes. The interlock is IN EFFECT.
QUESTION:   None to rule. Cosmetic only: should `threads.py` call the assert form instead of the predicate-plus-refuse?
OPTIONS:    (a) close as satisfied; (b) close and file a cosmetic RUN item to swap in `assert_step4_open`.
RECOMMEND:  **(a)** — `threads.py`'s current shape refuses with a three-line explanation of what `step4_enabled` asserts, which is better operator output than a raised `ProseRefused`. Swapping it would lose that. Note for the record: `config.yaml:143 step4_enabled: true`, open since 2026-08-31 by recorded owner ruling; `prose_enabled` at :108 remains `false` and is a separate flag. **Neither is touched by this recommendation.**
COST IF WRONG: None.
UNBLOCKS:   none
THEME:      step4 gate

---

### 0a9943374fe6  [SESSION] [MINOR]  — Publish-refusal check greps two of the most generic strings in Python
STILL LIVE: **YES** — the row is unchanged, only moved. `src/verify_math.py:6592-6595`: `check("a refused publish does not return success", "return rc" in _pub20p and "rc = 1" in _pub20p, True, ...)`. The underlying behaviour is correct and must not be "fixed" — only the check is weak, because `rc = 1` appears at three sites in publish.py so the refusal path alone could become `return 0` and the row stays green.
QUESTION:   None — this is a mechanical rewrite of one check.
OPTIONS:    n/a
RECOMMEND:  **reroute to RUN/LOCAL — no ruling needed.** Drive it instead of grepping it: call `publish.main()` with `push` stubbed to raise `RuntimeError('PUBLISH REFUSED -- probe')`, argv set so `a.loop` is unset and `a.push` is set, assert the return is non-zero, restore the stub in a `finally`. That cannot be satisfied by a string anywhere in the file. Same class the file has already re-aimed at the parse tree four times.
COST IF WRONG: If left, a regression making a refused publish return 0 goes undetected — the original bug told every caller the push succeeded while a live credential sat staged for the PUBLIC repo.
UNBLOCKS:   none
THEME:      grep-shaped checks

---

### 3e11c452ff67  [SESSION] [MAJOR]  — "REFUSING TO" substring row shares a failure mode with the dead regex
STILL LIVE: **NO** — killed by the same order 6dc4bde7fab6 that killed `51f0be4252e6`. The substring row survives at `src/verify_math.py:6350-6357` but its note now states this order's own finding as fact: *"MESSAGE QUALITY ONLY, AND IT SAYS SO NOW. This row is a whole-file substring search for two words... publish.py carries five of them... Gutting the escalation interlock in either module left this row GREEN -- measured on scratch copies, order 6dc4bde7fab6. The interlock guarantee rests on the AST rows below, not here."* The independent layer the order demanded is the AST predicate at :6383-6444, which pins guard COUNT per module and names offenders as file:line. Hard Rule -1's INDEPENDENT property is restored.
QUESTION:   None.
OPTIONS:    (a) close as fixed.
RECOMMEND:  **(a)** — and note that the fix went further than the order asked: it also caught that `overnight.py` and `publish.py` each carry TWO guards, so a `>= 1` row would have read green over deleting the startup guard in either.
COST IF WRONG: None.
UNBLOCKS:   `51f0be4252e6` — one fix, two orders
THEME:      interlock guard strength

---

### 8350f7a183d1  [SESSION] [INFO]  — alive_verdict answers "undetermined, because everything was fine"
STILL LIVE: **YES** — `src/feats.py:567` still reads `if api(host, {"action": "query", "meta": "siteinfo"}, retries=0, outcome=out):`, testing the truthiness of the parsed body rather than `out.get('ok')`. So a wiki answering 200 with a body parsing to `null`/`{}`/`[]` yields a stamped `'ok'` and a falsy return, giving `(None, 'ok')`. The three-answer contract at :550-557 and the only-404-is-settled comment at :570-572 are intact; the behaviour still fails in the safe direction.
QUESTION:   None — the guard is correct, only the reason string it reports is not.
OPTIONS:    n/a
RECOMMEND:  **reroute to RUN/LOCAL — no ruling needed.** Test `out.get('ok')` rather than the body's truthiness and branch separately on an empty parsed body, or add an explicit `'empty-body'` reason. Keep the three-answer contract exactly as it stands: only `'http-404'` may be False, everything else stays None. The value is that `resolve_hosts`'s PROBE UNDETERMINED list (`feats.py:772-786`) prints `why` for an operator to act on, and `'ok'` there is neither actionable nor true.
COST IF WRONG: An operator reading "undetermined: ok" cannot distinguish an empty-but-valid API response from a transport failure or from the pre-stamped `'unknown'` default. No cached negative, no data loss.
UNBLOCKS:   none
THEME:      operator-facing reasons

---

### d3acbb793ef2  [OWNER] [MAJOR]  — Cascade pin path can dispatch a live call to the local GPU
STILL LIVE: **YES** — verified against current source. The non-pin claim loop at `src/cascade_bridge.py:1374` has the exclusion (`if cand.bucket.startswith(LOCAL_PREFIX): _ROUTER.release(cand); continue`) with a full paragraph at :1367-1373 explaining why locals must never be claimed ("108 calls in fifteen minutes, zero ok, and Ollama answering everyone 'maximum pending requests exceeded'"). The PIN path at :1350-1361 has **no such check** — it resolves `pin` by id, reserves it and proceeds. `try_disabled()`'s gate at :1977 is still `if not (prov.get("api_key") or prov.get("local")):`, which admits disabled LOCAL models exactly as it admits disabled cloud ones.
QUESTION:   None that requires judgment — the invariant is already stated absolutely in this file's own commentary; the pin path just doesn't honour it.
OPTIONS:    n/a
RECOMMEND:  **reroute to RUN/LOCAL — no ruling needed**, with the owner's nod on blast radius only. Mirror the `LOCAL_PREFIX` exclusion onto the pin path. Flagging honestly: this is a change to dispatch in 1,270 lines of tuned, load-bearing code where parity is the best case, so it wants a narrow diff and a proof run, not a refactor. If you would rather not touch the router at all, the equivalent one-line fix is at `try_disabled()`'s gate (:1977) — drop `prov.get("local")` — which closes the only in-tree caller that can reach the hole.
COST IF WRONG: Leave it and running `try_disabled()` pins a disabled `ollama:` model and dispatches a live call to the local GPU bucket, which this file's own commentary calls an absolute invariant never to violate. It is reachable today: the live cascade config holds six disabled `provider: 'ollama'` entries in the `coding` pool.
UNBLOCKS:   none
THEME:      local GPU dispatch

---

### e038ec1759a9  [SESSION] [INFO]  — pick_model prints two different VRAM budgets in one table
STILL LIVE: **YES** — partially addressed, contradiction intact. The gate at `src/pick_model.py:310` uses `budget = (_measured_vram or 10.0) - VRAM_RESERVE_GB` (total minus reserve); the REFUSED block at :363 now prints `_budget_note()` (:312-314), so refusals name their budget. But the scored table at :371 still annotates every ADMITTED model with `fit_note(m, vram_gb)` where `vram_gb = free_vram_gb()` (:341), and `fit_note` at :257 prints `"WILL OFFLOAD: needs ~X.XGB vs Y.YGB free"`. So a model that PASSED the residency gate is still told, in the next column, that it will offload. Neither number is labelled as measuring a different thing.
QUESTION:   None — a labelling fix, and both numbers are separately defended in their own docstrings (:176-178 total, :200-203 free).
OPTIONS:    n/a
RECOMMEND:  **reroute to RUN/LOCAL — no ruling needed.** Label them: the gate's verdict as "by class (total − reserve)" and the fit note as "right now (free)". Do not change either number; the point is that a reader is currently made to choose between two correct answers with nothing saying they answer different questions.
COST IF WRONG: An operator reads the table, sees a passing model marked WILL OFFLOAD, and either distrusts the gate or closes browsers that were never the problem.
UNBLOCKS:   none
THEME:      two budgets one table

---

### 946153deafe9  [OWNER] [MINOR]  — completeness.category_size has no caller and claimed callers it did not have
STILL LIVE: **NO** — both halves were answered by order 551256c7dc68 (closed). The false sentence is gone and replaced with its own correction at `src/completeness.py:175-181`: *"`category_size` stays as it was -- but for NO caller, which is the part this sentence used to get wrong... grepping `category_size` (excluding this name) finds only its own `def` and docstring mentions."* The retention decision is recorded at :212-215: *"NO CALLER TODAY; KEPT AS THE PLAIN-NUMBER FORM (order 551256c7dc68). Every call site moved to `category_size_probe`... the house rule is that a public function is not removed by a maintenance pass... Said in the present tense so the next sweep re-finds the fact rather than the function."* Verified: `grep -rn category_size src/` minus `category_size_probe` returns only the def and docstring mentions.
QUESTION:   None. The order asked to "delete the function and the sentence, or name the intended caller" — the sentence was corrected and the function deliberately retained with the reason on the record.
OPTIONS:    (a) close as answered.
RECOMMEND:  **(a)** — this is the model outcome for the whole orphan-code class: the fact was made honest in place and the retention was ruled, so the next sweep re-finds a documented decision rather than an open question. Use it as the template when ruling `1a9c237dda4d`.
COST IF WRONG: None.
UNBLOCKS:   `1a9c237dda4d` — this is the precedent that answers it
THEME:      orphan code policy

---

### 27f823fd6ed5  [OWNER] [MAJOR]  — Ledger-guard 5% loss tolerance is set by taste, not measurement
STILL LIVE: **YES** — `src/ledger_guard.py:191` is still `MAX_LOST_FRACTION = 0.05`, and the comment above it (:187-190) still argues the number from feel: high enough that ordinary hand-editing cannot reach it, "because this refuses a PUSH and a safety that stops the operator doing ordinary work is a safety that gets deleted." No measurement was substituted. **New evidence since filing, and it is the strongest argument for ruling now:** the loss function was changed on 2026-09-03 to count duplicate lines (`Counter - Counter`, :401-411), and the docstring at :386-392 records what the old spelling was hiding — `handoff/HANDOFF.md` holds 733 substantive lines of which only 700 are distinct, so **33 lines, 4.50% of the file, could have been deleted and measured as EXACTLY ZERO loss, against a threshold of 5%.** The margin between invisible and refused was half a percentage point on the only gate in front of `publish.push()`.
QUESTION:   What loss fraction should refuse a push, and on what basis rather than taste?
OPTIONS:    (a) ratify 0.05 as an owner ruling and record the reasoning, which makes it evidence rather than an agent's judgment; (b) set it lower (e.g. 0.02) now that duplicate lines are counted and the old blind spot is gone; (c) make it two-sided — a low auto-refuse threshold plus a band that requires an explicit acknowledgement rather than a hard stop.
RECOMMEND:  **(a), and consider (b) in the same sitting** — the value of the ruling is not the number, it is that a tamper-evident guard's one hand-set constant stops being the agent's taste and becomes yours. The 4.50%/5% measurement is the concrete input that was missing when this was filed: the threshold sat almost exactly on top of a real file's duplicate-line slack, which is uncomfortably tight for the gate in front of an irreversible outward-facing push.
COST IF WRONG: Set it too high and a run that lost its history can push. Set it too low and the guard refuses a person re-wrapping a paragraph — and, as the module's own comment warns, a safety that blocks ordinary work is a safety that gets deleted.
UNBLOCKS:   none
THEME:      tamper-evidence threshold

---

## Cross-cutting notes for the sitting

**Three orders are one question.** `1a9c237dda4d` (four unread symbols), `3fb312a72435` (hosts.py) and `946153deafe9` (category_size) all ask: what does this house do with correct code that has no caller? `946153deafe9` already shows the answer that works — make the fact honest in place, record the retention decision, and the next sweep re-finds a ruling instead of an open question. Rule the class once. **`3fb312a72435` is the exception that must not be swept in with it:** hosts.py is not a leftover, it is an unwired removal of a documented cap with 94 measured hosts already on disk.

**Two pairs are literal duplicates.** `44c420f80448`/`b86d79c574e3` (both dead) and `24155b641dfa`/`f5503302ce44` (both live, same row). Four orders, two answers.

**Four orders need no owner at all** — `0a9943374fe6`, `8350f7a183d1`, `e038ec1759a9`, `d3acbb793ef2` — plus the detector half of `dc9ffadae765`. They are mechanical work misfiled on a decision rung.

**Nothing here recommends weakening a guard.** `config.yaml:108 prose_enabled: false` and `:143 step4_enabled: true` were read, not touched, and no recommendation moves either.
