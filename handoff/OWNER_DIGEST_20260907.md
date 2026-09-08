# OWNER DECISION DIGEST — 2026-09-07 (run #46)
All 200 open OWNER and SESSION orders, each re-read against the live tree before being put in
front of a person. Ten readers in parallel; 490,000 characters of order text.
**138 need a ruling · 37 are already dead · 25 are misfiled and need no judgment at all.**
So 62 come off the desk on one word.
Web version, with filters and check-off: the artifact published alongside this file.
Per-order detail with full reasoning: `handoff/digest46/BATCH_01.md` .. `BATCH_10.md`.

---

## The twelve to take first

### `728d9e99e9ec` — Six unwrapped live-state calls redden §20z and cancel mutation passes  [SESSION / MAJOR]
- **Question** — Should these calls be covered by a NAMED third-party abstention for live operational state, or by a blanket ledger suppression, or left alone?
- **Recommend** — (a) — and yes, this is the highest-leverage single fix in the queue. It removes the largest source of run-to-run battery non-determinism: because dashboard.state() calls standards.check() internally at dashboard.py:739, standards.check() runs ~15x per battery run, each doing a real getaddrinfo (standards.py:382), an Ollama generate with timeout=300 (standards.py:184, :264), and
- **If wrong** — (b) suppresses the echo of a GENUINE library fault occurring during a live call — the exact hole §20z was built to close (doctrine at verify_math.py:353-405; the widened-exemption control at :10091-10

### `342ccfafa4a4` — configured model is a thinking variant the config forbids  [OWNER / MAJOR]
- **Question** — Which model does the prose lane run on before the prose gate is ever opened — and is the fix a model change or a code change?
- **Recommend** — (a), with (c) as a follow-on. qwen3:8b has never been benchmarked against a real chapter job — the measured table in config.yaml:11-16 covers the 30B, gemma3:12b and qwen2.5:14b and not this model — so (b) asks you to keep an unmeasured model and write code to compensate for it. Landing the capability check *with* the ruling is the point: written before it, the check would free
- **If wrong** — (b) leaves the prose lane on a reasoning model that spends its answer budget thinking before it emits — already measured this shift as rc=1 after 570s on the repair rung — and generate.py has no outpu

### `959b98f38a63` — Fandom throttling is our own aggregate rate, not a ban  [OWNER / MAJOR]
- **Question** — What number caps the library's aggregate request rate against the fandom.com edge, and which knob sets it?
- **Recommend** — (c), then re-measure before touching (a) or (b). This corrects the order's own diagnosis. The order's two unestablished items are now measured: --workers 12 is set at src/overnight.py:1624, and the per-host rate is NOT 12x anything — feats._throttle (feats.py:122-149) takes _HOST_LOCKS[host] and enforces PAUSE = 0.34 s spacing, so one subdomain gets at most ~2.9 req/s no matter
- **If wrong** — Turn --workers down without (c) and you crawl fewer sources at the same illegal aggregate rate — the 429s continue and Hard Rule 0 pays for it in wall-clock. Do nothing and STALLED_UNRESTARTABLE keeps

### `71ae3fa7e55e` — Should a breach read mid-edit halt the library  [OWNER / MAJOR]
- **Question** — When a net breaches, may the drill read that one net a second time on a settled tree before it halts the library?
- **Recommend** — (b) — a breach that reproduces on a settled tree is strictly stronger evidence than one read, so (b) loses no true breach while removing the entire false-red class; the exact mechanism is already established practice here twice over (drill.py:13606-13620 declines to halt during a mutation run, and mutate.py re-photographs its baseline on a timer and calls a disagreement a drift
- **If wrong** — Under (a) you keep paying an investigation per false red and, on the run #45 pattern, an unnecessary halt plus a written ruling to lift it — roughly one event per shift at current agent counts. Under 

### `895a99602bf0` — What stops a thirteenth probe-litter site appearing  [OWNER / MAJOR]
- **Question** — Should drill.py get verify_math's whole-run leak spy, or should every gate instead redirect the ledger wholesale for its entire run?
- **Recommend** — (a), with (c) as the standing check — and not (b). (b) means a genuine fault occurring during a 20-minute gate run is never recorded operationally, and verify_math's own §20z comment already argues the opposite doctrine ("growth here is evidence to be READ, not automatically a fault of the battery"); the apparatus that answers this order is written, tested and running in one fi
- **If wrong** — Pick (b) and the failure ledger goes blind for the duration of every drill/verify_math run — the exact window in which the library is stressing its own guards hardest. Pick (c) alone and site fourteen

### `ef4ca9edd61f` — Re-mine 34,850 records that cannot say why they are empty  [OWNER / MAJOR]
- **Question** — Once the transport outcome is stamped on new records, what happens to the 34,850 already on disk that cannot be classified after the fact?
- **Recommend** — (c) — it buys the answer where the ratio says something is wrong and does not spend 30k+ fetches to re-confirm absences that are probably genuine. dc.fandom.com is the built-in control: same farm, same corpus size, a third the rate.
- **If wrong** — (a) leaves an eighth of the evidence corpus permanently unable to tell a throttle from an honest blank — the module's own signature failure, at rest. (b) risks the IP ban this project has already take

### `f9643582fd29` — Close the sandbox claim window or accept the race  [OWNER / MAJOR]
- **Question** — Do we restructure sandbox()'s claim sequence so a zero-age reap can never take a sandbox that has no owner file yet, or keep it as an accepted risk now that the one known zero-age caller is fenced?
- **Recommend** — (a)+(c) — the rename is one line of reordering and removes the mechanism rather than the one caller that could reach it. (c) is a strengthening, not a weakening: it makes the aggressive parameter unreachable against a live tempdir by anything at all.
- **If wrong** — (b) risks another ~20h pass dying at a target boundary with a third of its mandate unmeasured, and the evidence for next time is already degraded (see below). (a) done carelessly leaks unowned directo

### `5bbd4b3376fe` — Coverage checks string-match against un-stripped thinking text  [OWNER / MAJOR]
- **Question** — This is the SAME question as 342ccfafa4a4 — by which of three routes does the project stop think-tag text from reaching any check or any disk write?
- **Recommend** — (b), with (c) alongside since it is free and also reduces the tokens the context-budget squeeze is about. (b) is the only route that survives a model swap, and it fixes _covered, _deed_traced, think-tags-reaching-disk and the budget squeeze in one place rather than four.
- **If wrong** — patching _covered alone leaves the identical false positive in _deed_traced and in prose_gate; (a) alone re-opens the whole class the moment config.yaml:37 changes. The failure this guards is a thinki

### `4f5fa3146cc4` — foreign edit during a mutation run halts the whole library  [SESSION / MAJOR]
- **Question** — Should MUTATE_TOUCHED_LIVE_TREE keep the OWNER rung now that the sandbox rewrite makes the failure it is named after impossible by construction?
- **Recommend** — (b), with the message from (a). The finding is true and worth stopping on, but it says the *run* is unsafe, not the library — and mutate.py already treats a concurrent editor as an expected condition elsewhere (tree_is_moving() only WARNS). This does not weaken a safety: the sandbox is what prevents the original incident, and the digest keeps reporting; only the rung and the se
- **If wrong** — choose (c) and one repair agent landing one line in src/assay.py during a sixteen- hour --target all pass halts the entire library over a file the run never touched. Note the check is *also* blind to 

### `2eabb417f58f` — A drill net that cannot fail on the dedupe guard it names  [SESSION / MAJOR]
- **Question** — How much of catalogue() is worth making testable — factor the pairing out, or drive the real function against a fixture?
- **Recommend** — (b). It is the only version that actually enters the loop the net's printed name promises, so it catches the f4f3c1d15915 regression AND the TYPE_CATEGORY routing the damage report turns on (Race Troglodyte in FACTIONS vs Language Troglodyte in POWERS). (a) protects one line and leaves the rest of the loop untested — take it only if the fixture proves impractical, and rename th
- **If wrong** — (a) keeps a net whose name over-promises — the exact class CLAUDE.md calls the standing lesson, and the class this codebase has now caught twice.

### `ca0a93856e2a` — BUGS.md Open section is majority-resolved entries  [SESSION / MINOR]
- **Question** — Does the "one at a time, hand-verified" rule stand, or may a measured filter do the bulk and leave only the ambiguous ones for a person?
- **Recommend** — (b) plus (c) — and the number that decides it: of the 75 RESOLVED-labelled entries, only 3 carry a PARTIAL / STILL LIVE / NOT FIXED qualifier anywhere in their body (M79, m142/m143, m137), and M79's is the phrase "PARTIAL-MERGE" in the bug's own title, not a partial closure. All six entries the order names as must-not-move — M38, M16, M42, m105, m133, m134 — are labelled OPEN, 
- **If wrong** — If the filter is trusted and a partial closure hides in a body phrased some fourth way, a live fault gets filed as history. Cheap insurance: move in one commit so it reverts whole, and print the 72 he

### `481ef92af785` — Invented scope ceilings still clamping every published Magnitude  [OWNER / MAJOR]
- **Question** — Run the re-probe, accepting that published Magnitudes will move?
- **Recommend** — (a) — the code fix already decided the method; what is left is only consent to the numbers moving, and they should move: a source clamped at M7 on two mentions is constraining every entity under it on evidence the current parser would refuse outright. (b) is not meaningfully safer, because the pre-v2 rows carry no mention counts to filter on.
- **If wrong** — (a) changes published Magnitudes across up to 146 hosts in one pass — irreversible without a snapshot, so take one first. (c) leaves invented ceilings permanently authoritative over the library's head

---

## The remaining 126 decisions

### MAJOR (47)

- `1b7f14efce8e` [OWNER] **prime.fandom.com is bound to a source it has nothing to do with**  
  → (a) — unbind. The entry names read as a homebrew supplement, which is unlikely to have a wiki at all; searching for one is speculative work against 19 entries. Unbinding costs nothing (feats.py:1605-1607 drops entities of a hostless source 
- `2239a87c57f5` [OWNER] **Router discards the provider's own retry-after and redispatches**  
  → (b) — it keeps the order's stated rationale fully intact (a throttle is not a mystery and still must not reach the unrecognised ledger) while fixing the different question, which is routing. What tips it is the measurement: 3 of 6 probes di
- `24155b641dfa` [OWNER] **Bloons secret-scan waiver lost its scope caveat to a 300-character cap**  
  → (a) if you can state the caveat, (b) if you cannot — what is known from the surviving text is that this is mined Bloons TD 6 wiki prose about an in-game Easter egg on the map "Encrypted", not a credential, so (b) costs one re-review and no 
- `27f823fd6ed5` [OWNER] **Ledger-guard 5% loss tolerance is set by taste, not measurement**  
  → (a), and consider (b) in the same sitting — the value of the ruling is not the number, it is that a tamper-evident guard's one hand-set constant stops being the agent's taste and becomes yours. The 4.50%/5% measurement is the concrete input
- `28c1f58f5e8a` [OWNER] **Six run35 proposal files with 59 checks were never adopted**  
  → (b), but with (a) as the first move to find out what you are triaging — run the six once against the current tree and let the pass/fail split do most of the sorting. The order's own strongest evidence is that of the 67 order ids these files
- `2d6bef2aef03` [OWNER] **Star Realms is bound to a wiki that serves something else**  
  → (a) — I checked the record: data/records/star-realms.json holds 68 entries with correct names, types and descriptions ("Trade Federation", "Machine Cult", "Barter World"), so nothing needs re-fetching and nothing is lost by unbinding. Both 
- `3eff62be6cc3` [OWNER] **GROUNDINGS.json still publishes pre-fix inflated confidences**  
  → (a). Four sources — Marvel, Bleach, "major fantasy pantheons", "Pantheon: Mesoamerican" — currently publish confidence >= 0.5 and are reported as settled cosmologies when the full ranking makes them contested, and main()'s contested line re
- `3fb312a72435` [OWNER] **hosts.py fixes the single-host cap and nothing in the pipeline calls it**  
  → (a) — deletion is the option to refuse. The standing house rule is that a cap is a truncation hiding a smaller universe, and hosts.py exists precisely to remove one: its header states the fault plainly, that WIKI_HOSTS holds "194 sources, 1
- `3fb9fc6b9999` [OWNER] **ledger.py (De Pretio) has no caller in the pipeline**  
  → (b) — it is fully built, internally consistent and exercised by verify_math.py:266-284, so it costs nothing to hold; and (a) is a content decision about whether entries state prices at the Freeport, which is a charter question and yours alo
- `4398d76f822f` [SESSION] **repass_bands --apply destroys rejected scale_note text**
- `4f308dbd9d2c` [SESSION] **Switch on title resolution, or declare it off**  
  → (a) — alongside-not-instead means a wrong resolution costs an extra fetch rather than a misattribution, and the mined_under stamp is what stops the fix being cached away and not in effect. _page_exists (:925) goes with the same decision.
- `556c1b8fda9f` [SESSION] **NTFS hard links bypass the propose_patch denylist**
- `58cfc2b6dbc4` [OWNER] **Re-check the halt beside the write, not only at entry**  
  → (b) — the analogy it was modelled on has a check-to-action window of seconds over local file moves; this one is minutes to hours over rate-limited network I/O. Putting the check inside _land_hosts also covers the third writer the docstring 
- `5be28f56946c` [OWNER] **quarantine handoff brakes nothing; comment claims it does**  
  → (b), with (a) applied inside the same change and never on its own. Dropping is a smaller universe wearing the same shape as the real one, which Hard Rule 0 forbids outright; deferring costs latency and nothing else. Applying (a) alone delet
- `5c8a7bc883e7` [OWNER] **One feat-bearing entry excludes the whole rest of the cast**  
  → (b) — the 2026-08-25 ruling is written in the comment directly above this line and says lead paragraphs CAN carry a ceiling feat; on that premise, dropping 46 of 54 lead paragraphs because 8 siblings have a mined feat is the same act the ru
- `5c962f306e58` [OWNER] **The model-patch gate skips the entire VERIFY tier**  
  → (c). It answers the actual gap — a verifier's CLI/exit-code contract is what a model patch breaks, not its internal logic, which verify_math already pins separately — at a fraction of the VERIFY tier's cost, so it fits inside the foreman's 
- `5f1dc97d5216` [OWNER] **Unreadable records directory reads as a clean empty corpus**  
  → (b). The same event (a Norton lock, an offline mount, a permissions blip) is fail-closed at file granularity and fail-open at directory granularity inside one function. Unlike the per-file case, a directory failure reaches weave_index.py --
- `60dc7c624c06` [OWNER] **TIERS.json contradicts the address prose on all four tier counts**  
  → (a) — the prose was written against a chart that no longer exists (the filed measurement was "4 distinct values 2-5"; it is now {0,3,5}), so it is a stale caption, not a charter. Critically, (a) changes no published address: assign() reads 
- `642a95fe9f3c` [OWNER] **A missing tier is published as charted tier zero**  
  → (a) — the vocabulary already exists unused (UNADDRESSED at :141, and TIERS rows now carry a hyperverse_type field), and 16 rows is a small, safe change. (c) is too strong: it would pull those 16 worlds off the shelf entirely.
- `66f96febdb3a` [OWNER] **descending_ladder has no consumers; the gap it names is open**  
  → (a). The defect the docstring names is measurable and unfixed — sub-planetary Reach is scored against a floor that does not exist — and the arithmetic was already verified correct (monotonicity, domain guards, PLANCK_ENERGY against m_P c²),
- `6e6954f261e0` [OWNER] **Prose gate never checks the Instrument section exists**  
  → (a), scoped — this strengthens an owner-held safety rather than weakening one, and the docstring naming Instrument loss as a founding symptom of the incident this layer exists to stop is the strongest possible argument that its absence shou
- `707fefc17465` [OWNER] **render.py, all nine cosmology view tiers, reachable only by hand**  
  → (a) — the module's stated purpose is real and unmet: five cosmology tiers "had addresses and no way to look at them", and 60dc7c624c06 below is a question about exactly those tiers that a picture would help answer. Retiring it discards work
- `7099a092abd3` [OWNER] **Thirteen public functions the battery alone calls**  
  → (c), then (a) for these thirteen. One class ruling settles five other orders on this desk, and deleting charter apparatus on an audit's say-so is the failure mode CLAUDE.md's own preamble is about.
- `74f1bc47da2a` [SESSION] **Battery rows still redden on live network, not on this code**  
  → (c) — they fix opposite halves and neither is sufficient alone. (b) is the strictly better shape and the file already argues for it in its own comment at :7887-7892 ("There is nothing left to drop"); (a) is what stops the residual drop path
- `789f99f2a65f` [OWNER] **tiers.py prints "hyperverse DECLINED" while assigning one**  
  → (a) — the tier was re-implemented as a grounding and the prose was never updated. No data changes; data/TIERS.json already holds the four non-null values and is correct. This is a comment-contradicts-code fix, which is a stated lens of the 
- `7ad10a229440` [OWNER] **Does reprove_pool's success block restart_reader from ever running**  
  → (c), then (a). (c) is the honest reading of did and matches the precedent the .always mark was introduced for — measuring is not an alternative to repairing. (a) on top costs nothing, because restart_reader's own docstring records that rest
- `850786a2fee4` [OWNER] **No drill net fires before a model-authored patch to live source is kept**  
  → (a) now, (c) later — (b) is the one option to refuse: verify_math.py:5504 records that verify_math and drill "are not safe to run" from an agent context, and drill historically wrote trial values of prose_enabled into the live config (verif
- `8f50f37255b5` [OWNER] **_STOPNAMES deletes real named entities from the entity index**  
  → (a). The filter's own comment says the rationale is that "a collision on these is meaningless" — which is an argument about matching, not about existence, and the code applies it to existence. Hard Rule 0's shape exactly: a filter silently 
- `97cc0dc43ca7` [OWNER] **lock the halt write, and decide fail-open vs fail-closed**  
  → (a) — this is a safety path, so the failure that matters is a halt that never gets raised because a lockfile is stuck, not a duplicated one. Fail-open keeps the guard's purpose intact while closing the window; (b) would convert a rare lost 
- `9a44b1535851` [OWNER] **Recovery tool writes records outside the record writer**  
  → (b) — the dangerous half is already blocked in code (:170 re-reads the live record and skips any source already holding entries, treating unreadable as populated, and :216 gates the roll update on the write actually landing), so what remain
- `9fb8a6b10c1f` [OWNER] **cascade has no reachable model and grades broken every run**  
  → (a) first, then reconsider — it costs nothing, uses the model already resident, and turns a permanently red subsystem green or honestly amber. (b) is the wrong move today with the GPU at 99% util and the read pass already timing out on the 
- `9fcbe25a473b` [OWNER] **pantheon prints an incomplete roster but returns rc=0**  
  → (a). The file already states the principle two branches down in its own words — "a run that printed a ranking holding six of twenty-one entities is not a successful run, and rc=0 is how a scheduler records it as one" — and a ranking missing
- `a3d518d078c3` [SESSION] **Forty-four sources stranded by a done-keys gate the todo filter fixed**  
  → (c) — (a) is the durable fix and matches the ruling this same file already made at pipeline.py:1906-1924; (b) is one line and rescues the existing 44 without waiting for (a). Do NOT simply drop the done_keys test: that re-nominates every ge
- `aad11acb1183` [OWNER] **The dashboard refuses to start while a halt stands**  
  → (a) — the interlock exists so a job cannot do WORK while the library is halted; the dashboard does no work, it only reports, and reporting the halt is the whole point. The honest form is to call escalation.status() and render, not assert_cl
- `ae25c89f0179` [OWNER] **Genre-aware naming register is structurally unreachable**  
  → (a) if a per-group genre source exists, otherwise (c) — never (b). The docstring names the exact harm the blend was written to fix (Alien and Doom given the flowing elvish sound, Greek myth denied the classical one), so deleting the mechani
- `b186bc4dad8f` [OWNER] **category, topic and subroom are three axes; what about the unrestored rows**  
  → (c) — (a) and (b) differ only in when, but neither stops it happening again, and right now the only thing standing between this project and a repeat is a comment. The order says the follow-on step would have CLEARED 126,136 topics; a commen
- `b317ba3a4f36` [OWNER] **re-derive GENRES.json confidences, moving 63 published flags**  
  → (c) — zero genre labels change, so nothing downstream is re-classified; only the honesty of the confidence number moves, and it moves the way the module's own docstring says it should. Writing the before/after alongside it costs one file an
- `b813fc5a37e2` [SESSION] **Cloud routing gate ignores the pool-proof age it claims to check**  
  → (a) now, with the docstring corrected in the same edit; take (b) only on the owner's word. (a) is free and makes the decision visible, whereas (b) settles a question tuning.py explicitly declines to settle, citing m59 — even a FRESH proof o
- `bd673ceaaf31` [OWNER] **Wire Lumen's staleness and Threnody's veto, or rule them abstained**  
  → (b) for Lumen now; leave Threnody abstaining. (b) costs one line and converts a silent gap into a stated convention. Threnody has no honest input — SHARED_STAGE_GRAPH.json holds co-attestation weight, not contest flow — and a plausible-look
- `bffc372a96d2` [OWNER] **The LOCAL rung is starved by the library's own daemons**  
  → (c) for one shift, then (a). The two fixes that landed after this order was filed changed the input to the decision — the rung was being timed out at 420s against a config that serves 1800, so "the model is incapable" and "the lane is conte
- `c614f7c145fc` [OWNER] **a halt was lifted by an automated actor, not a person**  
  → (c) now, (b) only if you want the asymmetry to be real. (c) is small, closes the "reads as a person" gap permanently rather than relying on an agent's good manners, and costs a person at a terminal one extra flag. (b) is the only option tha
- `d2e44a766769` [OWNER] **gate restart_reader's kill on restartability, or adopt read.py**  
  → (b) — reading (a) turns the remedy into a permanent no-op by construction, and (c) is the reading a measured four-hour outage already refuted. Promoting read.py makes the docstring's own justification true instead of arguing about it, and i
- `d8858a26e46e` [OWNER] **A module partition does not partition meaning**  
  → (b), written into MAINTENANCE.md rather than NEXT_STEPS.md — (a) fights the line-count balancing that makes 16 batches finish together, and coupling is not always one-net-to-one-module, whereas sequencing the battery after the agents report
- `f07b7d538ed1` [OWNER] **Star Realms host misbound (truncated duplicate)**  
  → (a) — 2d6bef2aef03 carries the same evidence, is re-measured live by binding_health.identity (seen 66 times, last on 2026-09-06) and is not truncated. Two orders on one host binding is one more ruling than the fact deserves.
- `f27c121c6cb7` [OWNER] **re-catalogue stored entry types while the prose gate is shut**  
  → (b) — my own scan today counts ~25,000 entries carrying a multi-word or colon-bearing type, and the worst are unmistakable: Total War: Warhammer (690), Pages using ISBN magic link (255, a wiki maintenance category stored as an entity kind).
- `f84cb75edcfe` [OWNER] **Prime World Equipment is bound to the hydration-drink wiki**  
  → (a), then (b) if the re-mine comes back thin. Rebinding is right regardless of what follows — the current binding cites a beverage wiki as evidence for a fiction, which is strictly worse than no host at all — and the grain decision in (b) s
- `fbc0930ae309` [OWNER] **Proving a behavioural drill net works currently costs a library outage**  
  → (c) — the sharper half of this order is not the outage, it is that two of that net's three versions were wrong in opposite directions and only running it in more than one world revealed it. The dangerous failure is version 2: a net red in m

### MINOR (52)

- `01695fe3ef26` [OWNER] **Keep scale_theories' four priced codifications, or delete the module**  
  → (b) — the constants have a settled precedent working against them and the content does not. chord_field.py:35-44 and tempus.py:44-46 both deleted exactly this kind of duplicate constant, and verify_math.py:9182 now asserts tempus stays clea
- `0291835411d9` [OWNER] **tempus.DEGENERATE_TIME, and its prose duplicate**  
  → (a) — the four entries are charter cross-references, not code, and the duplication is the actual hazard here. The loop_report half is mechanical and can go to a code rung the moment you rule keep.
- `0fbaba6e1070` [OWNER] **ANEURISM IV mines to nothing and no bot can fix it**  
  → (a) — 175 hand re-catalogued names for one small source, on a wiki whose probe says even known-present titles return nothing, is not where curatorial hours buy the most. Record it so the 67th re-file does not happen.
- `13aee150e0dc` [SESSION] **A lock file moves a stale-code alarm four rungs down**  
  → (a) — the escalation fires either way, so (a) costs only louder filing during a shift, while (b) leaves any writer of that guard file — including a crashed run that left done:false with a fresh heartbeat — able to demote the alarm for free.
- `171ade4c7d27` [OWNER] **local_agent reports rc=0 and ok=true for a prose non-answer**  
  → (b). The measured case is exactly "read a truncated slice of src/policy.py, never paged, reported failure in prose", which is nameable without free-text matching; that fixes the true half of NEXT_STEPS run #42 item 3 without (c)'s loosenabl
- `18d0fedabf13` [SESSION] **pick which college and bit-value properties anchors grades**  
  → (a) + (c) + (d), and explicitly NOT (b). Checked: custodes.py:540 computes attestation_floor_share as round(1.0 - prior_share, 3), so the two are complements by construction, not computed separately — grading (b) would add a tautology, exac
- `1cdc2f8cd2f3` [OWNER] **does Hard Rule 0 reach announced console truncation**  
  → (b), and write it into CLAUDE.md so it stops being re-derived. The precedent already went that way once: order 6434c1ba7b20 uncapped catalog.py:76-78 to print every missing source, and a rule that has been applied to one console listing and
- `1eb00a84225e` [OWNER] **address_space.UNADDRESSED is a name for a decision nobody takes**  
  → (c), and this one leaves the desk today. The constant's comment — "a shelf in no hyperverse: it shares no entity with anything" — is the honest answer for precisely that case, so if the missing-tier ruling goes the way the comment assumes, 
- `1f9a54bede08` [SESSION] **mark or remove the 600/900-char cuts in both writers**  
  → (b) — evidence is the string a reader later checks a band claim against, so an unmarked cut is exactly the "a truncated X is indistinguishable from a complete one" fault this project keeps finding, and (a) risks unbounded record growth for 
- `2b695c192470` [OWNER] **sweep.load has no caller anywhere in src/**  
  → (a). verify_math.py:4807-4813 already argues the case: what §21 pins is the miss/corrupt SPLIT, and that split is the repair that took the swallowed-failure ledger from 18,418 of 21,764 entries being one expected absence back to meaning som
- `2f38b3e5258d` [OWNER] **resident() and fit_note() measure different VRAM budgets**  
  → (a) — (b) would make the residency gate flap with whatever the desktop happens to hold this minute, which is the opposite of what a standing eligibility rule wants; free_vram_gb()'s own docstring explains why the two are separate.
- `38c51153243c` [OWNER] **Is the Ruin band edge meant to be U-shaped?**  
  → (a) — a cell really is easier to disrupt than a nucleus, and an axis that says so is telling the truth about the world. Say it in the header; the unstated non-monotonicity is the actual defect.
- `3b9812ae8ab7` [OWNER] **Mach is written unit-first, so 86% is unminable**  
  → (b) — the note's own argument is weaker here and the order says why: "Mach 5" is a far less ambiguous token than "a power level of 5,000", which is exactly the ambiguity the subject- resolution worry is about. The volume is honest and small
- `3d2d9b87cc10` [OWNER] **Should FOR_OWNER.md be published, or withdrawn from the export**  
  → (b) as the code change, whichever way the owner rules on the document. The two are separable and the owner should not have to trade them: the root-file sweep closes the unreachable-withdrawal hole permanently for every future root file, and
- `3dd5b6caef38` [OWNER] **Does Hard Rule 0 reach announced console illustration lists**  
  → (c). It is (a)'s readability and (b)'s honesty in one, the idiom already exists in this tree, and the harm Hard Rule 0 actually names is a truncation that hides a smaller universe — which a printed remainder structurally cannot do. Worth st
- `40e98eed6870` [OWNER] **Era and condition vocabulary worldseed can never emit**  
  → (a). The evidence gathered under order ad681057369a and quoted in-file at worldseed.py:213-224 shows "primitive" is live in three sibling modules — genre.py:57 gives the mythology genre tech="primitive", onomast.py:348 maps it to the guttur
- `4d78c426afb3` [OWNER] **MediaWiki category floor of 40 pages is undeclared**  
  → (c), then (b) if the tail turns out to hold cast. (c) is the cheap version of the measurement the order proposes without the extra Fandom traffic — the floor is applied server-side, so the only honest alternative to measuring it is disclosi
- `4e92365b54f6` [OWNER] **build_address() is dead and returns the colliding pre-volume form**  
  → (a) — nothing calls it, and the honest address needs a per-Series volume map that address.py does not hold; (b) would either duplicate manifest_builder's map or take a new argument, which is a new function, not a repair. (c) leaves a trap: 
- `5a0c4196142f` [OWNER] **Should source-substring checks ask the parse tree instead of the text**  
  → (a) as the floor now, (b) for the ones that prove a guard is WIRED. (a) is a mechanical sweep of the remaining in _*_src sites and removes the exact hole that was measured; (b) costs real work per site and only pays where the check is the s
- `61c763a60779` [SESSION] **quarantine write verdict discarded, console asserts it anyway**  
  → (a) — this is not a lost alarm (quarantine() raises HOST_QUARANTINE_NOT_RECORDED itself), it is a stored report and a console line asserting an action that may not have happened, pointing the opposite way from the fault _report_not_released
- `665e3609bc82` [OWNER] **Four uncalled functions in feats.py**  
  → (a) — answering it on its own re-decides the same two things in a different order and leaves stale line numbers on the record.
- `68459d3e739b` [OWNER] **Franchise rank-agreement rests on a single franchise**  
  → (c), with (b) first because it costs nothing and the UNSCORED row added by the fix already gets most of the way there. The assay work in (a) is a content decision only the owner can size.
- `6c479972e838` [OWNER] **Receiver-aware dead-code detection needs the ratchet moved with it**  
  → (b) first, (a) only if (b) fails — and settle 01695fe3ef26 before either. Five of today's 45 findings are scale_theories; if that module is dealt with, liveness drops to 40 and the sharper detector has 12 points to land in. A raise that tur
- `6d594a775899` [OWNER] **Does pages_read mean fetched or read?**  
  → (a) — the field's name is a claim and it is currently false; (b) leaves the same trap armed for the next consumer. Either way coverage.py needs a REFUSED state, because "we were served a block page" is not "READ".
- `6fc71f8ab76e` [OWNER] **feat-less entries never nominated once a source has any feats**  
  → (b) — nominate both, feat-bearing blocks first. Your own 2026-08-25 ruling on the line above already settled the underlying principle in the same direction ("the tail is now REACHED rather than discarded"), and given the block above it — si
- `70f66fbd98aa` [OWNER] **runguard fails OPEN on a corrupt guard, against Hard Rule -1**  
  → (c) — and note this is the owner's call because it touches the one invariant that prevented bug m27 (two maintenance runs overlapping, one clobbering the other). (c) is the only option that keeps the guard's stated safety property (nothing 
- `729c26e0e63c` [SESSION] **declared count unpacked and never compared**  
  → (a) — a mapping declaring 350 items against a register yielding 3 currently lands silently, is stamped status='catalogued', and because work selection everywhere keys on entry_count == 0 the source is never revisited. That is the "a truncat
- `7e360eaec3a6` [OWNER] **Keep or delete chord_field's six uncalled physics functions**  
  → (a). The arithmetic was independently checked correct, and the module is now a real dependency of rigor's adjudication audit, so deleting half of it invites re-deriving the same physics later. A documented "no callers yet" comment costs one
- `82fc93f056d4` [OWNER] **read 55 wh40k axes and tag each wiki or canon**  
  → (a), but scoped to one sitting — halo.py's precedent found 24 of 33 tags false, so the prior that these are mixed is strong and the file is only 5 entities deep. The code is already finished; this is pure reading, and it never gets cheaper 
- `845dbaec182f` [OWNER] **coin_well_formed's exhausted exit returns a rejected name**  
  → (b). It keeps the module's stated position (refusing to name anything is the worse failure) while ending the thing that is actually indefensible — an exit that returns a value it has just tested and rejected, which is the shape of a check t
- `85cdecef25f8` [OWNER] **'weapon property' unmapped in the codex type taxonomy**  
  → (a). A weapon property (finesse, versatile, reach) is rules text describing what a weapon grants, not an object — the same reading that put rule, racial trait and background feature in POWERS. Ten seconds of your time; add one key.
- `88982cef258d` [OWNER] **Free cloud tiers are spent; recorded so nobody re-diagnoses it**  
  → (b) — (a) is right about the quota half and needs no further thought. The 401s are a different fault hiding inside a quota order: two buckets are absent from the binding constraint for want of a key, which costs nothing. Worth ten minutes o
- `8fb33a0204c4` [OWNER] **the printed shelfmark omits the star field entirely**  
  → (a), the docstring-plus-seed_from_card variant. The charter's own worked shelfmark at address_space.py:98 has no star either, so (a) is faithful to Part Two; and (b) re-addresses every world's map seed, which address_space.py:283-291 alread
- `9b3e59aeeb19` [SESSION] **axis_score returns one None for five different conditions**
- `a1aa2be36b7e` [SESSION] **refuse a mutation root that is the live tree**  
  → (a) — it adds a guard rather than weakening one, has no behavioural effect on any existing caller (all verified: _session passes sandbox(), both drill sites stub _run_mutation), and makes the module's stated architecture a property of the c
- `a78d5cd748b2` [OWNER] **Five dead physical constants in a module nothing reaches**  
  → (b). Deleting five dead constants from a module nothing imports buys nothing while touching a file already flagged for the larger question, and the house precedent is already settled twice over — chord_field.py:35-44 keeps only the constant
- `adaeaa7ad639` [OWNER] **Cosmography size-class multipliers contradict their own descriptions**  
  → (a). The charter's own II.N.3 exception class — "the small universes that re-run themselves", the Basement Loop and the Rot City of ANEURISM IV — describes sub-galactic pockets, which is what the prose says. Nothing in src/ moves either way
- `aecffd7eea57` [OWNER] **eberron.fandom.com is correctly bound but no catalogued title resolved**  
  → (a) — do not rule. Both options in (b) are answers to a question the data says is false, and either would do real damage: accepting "no per-entry articles" would stop mining a wiki that answers 15 of 15. Note also that the close path in wor
- `c0384991bfc5` [OWNER] **worldseed.unreachable_by_url has no callers**  
  → (c), defaulting to (a) in the meantime — the function is a real, correct statement about what the Azgaar query string cannot carry, and it sits next to a long comment about exactly that limitation, so it reads as documentation with a signat
- `c391a1f77e42` [OWNER] **Does phase 8 close when every ready source has zero entries**  
  → (a), plus a diagnostic. Reaching that branch means sources WERE ready and every one was empty, which is a genuinely different fact from "nothing was ready" (handled far above by if not ready) and is currently invisible; logging that count c
- `c8dc624e4e02` [SESSION] **unbound host and no-feats give one indistinguishable answer**  
  → (a) for the data, and reroute the code half. The pages: sentinels (5 of the 18) are correct by design and should answer "not a wiki source", not "no feats" — that distinction is what makes (a) safe to act on afterwards.
- `c9e6e50e792f` [OWNER] **assay_dof lists nine parents while its own prose says ten**  
  → (a) — (b) does not close. college_size derives the College's size FROM assay_dof, so nine levers derive a nine-member College while custodes.py seats ten, and custos_dasein at :275-279 explicitly says the structure derives "why exactly ten"
- `d411f780d347` [OWNER] **coverage_map() has no callers and the CLI bypasses it**  
  → (a) — --coverage is documented at :20 as "what the last sweep actually covered", and it currently answers from the file record()'s own docstring at :139 says "nothing draws a conclusion from". One call site changes; the function was written
- `da15f582b2ea` [OWNER] **A declared safety with no site that can raise it**  
  → (a) — Hard Rule -1's chain is the thing this project built after 145 chapters were written with nothing failing, and two of its six rungs currently have a name in a file and no expression in code. Note what (b) costs: deleting it leaves the
- `ddb5eadd8934` [SESSION] **should lifting a rung-4 stop require a person**  
  → (a) — the incident this guard exists for (catalogue_web stopped at 22:5x, restarted at 23:21) was an automated actor, which is precisely the class the current gate does not cover, and there is today no person-facing command to lift a stop a
- `de43fe54feb7` [OWNER] **scope.ceiling_for has no callers anywhere in the tree**  
  → (b) unless you take (c). (c) is the better engineering answer — host_ceiling reimplements the live-probe fallback, so there are two definitions of one rule — but it touches a live Magnitude path and is a bigger change than this order is ask
- `e296ea51a1d9` [OWNER] **the 25-file floor that hides small broken caches**  
  → (b) — it preserves whatever statistical caution the 25 encodes while removing the permanent blind spot, since a new host that 404s on everything stays under 25 files forever and is therefore invisible to this detector for exactly as long as
- `e68664e621bf` [OWNER] **URL_SETTABLE is read by nothing and has already diverged**  
  → (a). The module's whole stated discipline is that the emitted set must match the honoured set, and (a) makes that mechanical instead of aspirational for four lines of work.
- `efd2b537f26d` [OWNER] **warthunder's catalogued entry names are not article titles**  
  → (c), falling back to (a). The source name is a four-game composite ("War Thunder + World of Tanks/Warplanes/Warships (space-refit)") bound to a wiki that covers one of them, which is the likeliest reason its titles do not resolve — that is 
- `f27d210d4fea` [SESSION] **Dead alive() and _page_exists() in feats.py, filed four times over**  
  → answer 4f308dbd9d2c, and let this order follow it. Delete alive() now regardless, per its own docstring: it is an uncalled wrapper whose only remaining function is to be the wrong thing to call, which is the mistake order 64e4db060ad6 was f
- `f5503302ce44` [OWNER] **Suppression reason still truncated on disk after the code cap was removed**  
  → Answer 24155b641dfa and close this one against the same ruling. The only thing this filing adds is the sharper phrasing of why (c) is not good enough: a reviewer reading "...this only sur" cannot tell a truncation from a typo.
- `fc08e056e1ab` [OWNER] **Two disagreeing tests for "is this the entity's own page"**  
  → (a). _norm_q is a regex fold over one short string and this runs once per row, not per character — the cost argument for (b) has never been measured, and the order itself measures the affected population at ~0.2% of 282,059 rows, i.e. rough

### INFO (27)

- `12c457975677` [SESSION] **assay.REFERENCE_JOULES is a 14-entry table nothing reads**  
  → (b). The two tables do genuinely different jobs — magnitude parses units out of prose ("kiloton", "kilotons"), this one names whole feats ("hiroshima", "continent_shatter") — so merging them would put feat names into a unit parser. The real
- `14a73de63099` [SESSION] **"8 known-present titles" reads as the whole catalogue**  
  → (a) — and this is the highest-leverage item in the batch, because it is not cosmetic. What tips it: data/BINDING_HEALTH.json shows the eight titles actually tried for eberron.fandom.com were *Alchemical Savant, Arcane Firearm, Chemical Mast
- `189532cbf41a` [OWNER] **Spine-gap report shows 4 of 33 unassigned sources**  
  → (c), and (a) is the half that must not wait. Thirty-three names is nothing to print, the standing house rule is that a cap is a truncation hiding a smaller universe, and the [:4] is currently the only thing between the owner and the exact w
- `1a9c237dda4d` [OWNER] **Four public symbols in ledger.py and tempus.py with no reader anywhere**  
  → (a) — and this is the answer to a whole class, not three symbols. A one-line retention marker stops every future sweep re-finding them, which currently costs more than the finding is worth. CONDENSATES encodes the material Chord (W.7) and c
- `2e0ba4b02ec4` [OWNER] **Phantom pass builds its defined set module-wide**  
  → (b) — the file's stated policy is to err toward no false positive, and a module-wide set can only ever UNDER-report, never invent. The real reason to be slow here is named in the order: liveness's finding count is ratcheted by a drill net (
- `382d3a1c387c` [OWNER] **Rule-of-three tell is narrower than the label it ships**  
  → (a) — an unqualified three-item-list pattern fires on ordinary English constantly ("Persons, Places and Powers" is in your own charter), and this file already defends one such asymmetry at length after run33 filed it as a bug without checki
- `3859043e365e` [OWNER] **Generate's output reserve does not account for a reasoning model's thinking tokens**  
  → (a) — the order names exactly the measurement that would settle it and nobody has taken it. (b) and (c) are different decisions (one changes the refusal threshold for every job, the other changes what the model is being asked to be) and you
- `464cc4e12fbc` [OWNER] **Dead entries in overwatch's _STATE_RANK, or legacy compatibility**  
  → (b), on the measurement rather than on taste — 6 of the 1,404 rows on disk carry refuted or stale, and dropping their ranks makes _progress() score them 0 (the same as open), so a stale writer's copy could overwrite a terminal verdict. Only
- `47067a8f0ad5` [SESSION] **catalogue_web constants justified by an importer that does not exist**  
  → (b). The comment at :429 — "Was if len(titles) > MAX_PER_CATEGORY:" — carries the history of the TypeError the neutralised cap caused for every non-empty category, and the names being present is what keeps that comment legible. One correcte
- `762256b4b844` [OWNER] **Should escalate() reject a non-integral float level**  
  → (a). It is two lines inside the block whose entire stated purpose is that an unrecognisable level lands somewhere loud, and the failure it prevents is the worst-shaped one available here — a level that silently DE-escalates, so a SAFETY eve
- `79da6c08c536` [OWNER] **Rejections filed even when the host-map write was refused**  
  → (a) — cheapest thing that ends the re-filing; (b) is optional polish on a file no program reads.
- `864a626a258e` [OWNER] **CLAUDE.md's "all 57 nets" is stale by an order of magnitude**  
  → (a). It is the only wording that does not need re-editing every time an area is added, and 57 is the one claim in that paragraph a reader can check — a figure off by 8x in the safety layer's own charter is the kind of thing that stops a rea
- `91cf746c651e` [OWNER] **Does secondopinion's "escalates to JANITOR" name a call or a severity**  
  → (a) — what tips it is the paragraph the sentence lives in. secondopinion.py:62-71 is an argument about SEVERITY: the module is fail-open because "halting the park because an optional second opinion is unavailable would make a safety indisti
- `95f817b752ac` [OWNER] **Fabrication standard reports red when its reader is merely down**  
  → (b) — the tipping factor is that the sibling block's own stated reason applies *more* here, not less: this standard has no remedy at all, so its red row cannot even dispatch a cure, it can only occupy the owner's page. Reading (a)'s real fe
- `98f18453deaf` [OWNER] **Synthesis blob bypasses the origin-entry filter in grounding**  
  → (a) — a synthesis rationale is the most considered origin account in a record, and the _ORIGIN filter exists to stop *incidental entry* vocabulary outvoting the creation account ("recurring character" nearly made eternal recurrence the comm
- `9adb8291c16c` [SESSION] **suppressions.problems() re-walks the whole repo per row**
- `a34f10a87483` [OWNER] **A drill net that halts the library over the wording of a comment**  
  → (b) — this weakens nothing. The owner's no-paid-lane ruling stays pinned in code and stays checked; only the *penalty* for a wording change moves from "halt the library" to "file a finding". What tips it is this file's own standing line at 
- `b248f8f706d3` [SESSION] **Hard Rule 0 tripwire fires only after hours of network work**
- `bc4156603071` [OWNER] **Where on the attestation scale an unrecognised grade belongs**  
  → (b). Order 13a678071cbf, which introduced this constant, ruled that "the value was never the defect and must not be retuned as if it were." (a) tightens every interval_from_hands reading carrying an unrecognised grade — and through custodes
- `be9e9f089d62` [OWNER] **Shelfmark omits the star, so names can collide**  
  → (a) — Part Two's own worked Shelfmark, quoted in the file at :98, has seven tiers and no star, and the live data is clean (1,016 rows, 1,016 unique addresses, 1,016 unique shelfmarks). (b) is a re-addressing of the kind the _LEGACY_HASH_OFF
- `c72431056a14` [SESSION] **Mutation token env var documents a safety nothing implements**  
  → (a) — the mechanism is already served by mutate.active(), so wiring a reader would duplicate a working interlock, and a constant documenting a safety nothing implements is precisely the shape this module exists to find. This is a one-word a
- `cca253138a62` [SESSION] **Console tool trace cuts args and results unmarked**  
  → (a) — genuinely INFO now: the durable channels were repaired and main() prints the verdict first and unconditionally, so nothing load-bearing rides this line. It is a consistency fix inside a DENYLIST-protected file, which is the only reaso
- `cdfeccbfbab0` [OWNER] **Two of three universe size classes refuse to produce a census**  
  → (a). "A closed loop, a demiplane, one stage and no sky" cannot hold 200 galaxies in any reading, so the multiplier is the wrong half — and SIZE_CLASS_MAX_GALAXIES already encodes that judgment, it is just not the value census computes from.
- `d2da5914da94` [OWNER] **A source with no probeable categories is dropped, not marked unmeasured**  
  → (b). The same function argues four separate times in its own comments that "a source absent from COMPLETENESS.json is indistinguishable from a source with nothing missing" — and CATEGORY_PROBES missing a wiki's real category name is a live 
- `d44b106ce7e3` [SESSION] **Three rulings owed: publish stderr, escalation 'who', assert_clear scope**  
  → Q1 (a) — no commit was made this cycle so nothing new is stranded, and order 3778bc42499f already closed the real hole by retrying stranded commits at publish.py:1531-1540; just say so in the comment. Q2 (a) — "who" is a decision field at e
- `db36d589713e` [OWNER] **A constant nothing reads, deferred to you by name**  
  → (a) — it is the cheapest possible answer and it is the same answer the class ruling in 7099a092abd3 would give. The measurement is worth keeping and moving it costs a diff in two files for no gain.
- `ec05033115d6` [OWNER] **generate_job keeps calling the GPU for a chapter already doomed**  
  → (c) — not in the order, and it dissolves the trade-off. ChapterRefused's docstring insists on the FULL offender list, and every entity in a block that was never attempted is by definition missing, so the complete list can be assembled at ze

---

## Dead — confirm and they close (37)

- `0b1cda11f4a2` feats.axis_evidence is dead code duplicating the live gate
- `0c1670811107` Corroboration of a coverage-stamp fault that has since been fixed
- `18f7673b77ce` clean_ceiling's prefix match picks the shortest with no ambiguity check
- `28f79d511879` The machine has run out of TCP ports (the 40x magnitude filing)
- `2d8b96343896` is the drill:4256 citation a quotation or a pointer
- `33000660ddac` feats --roll exit code: fixed, counters now reach rc
- `372d4a8c8d46` runguard compare-and-swap check-then-act window
- `3e11c452ff67` "REFUSING TO" substring row shares a failure mode with the dead regex
- `44c420f80448` Sweep batch plan reshuffles mid-run and falsifies the coverage ledger
- `47c8def059e3` Console truncation in cosmology_graph
- `4e37d5e59b09` Local rung closed by a pinned llama-server; recorded mechanism refuted
- `4e7f1e47d0a0` Keeper restarted a job a run had stopped
- `505177847f43` Foreign process starving the free local labour rung
- `51f0be4252e6` Escalation fail-open regex matches a shape that exists in no file
- `570525d35825` MODE_HTML constant no resolver can return
- `585fcd3774b8` Bone (Jeff Smith) has no roll row; 86 entries invisible
- `692f693c3900` Duplicate of the rule-of-three scope question
- `732f68f640cf` coverage --show-best cap: disclosed and ruled on in code
- `7ebac78494e8` Four cloud buckets: the DNS diagnosis is disproven
- `8c354f6c9780` Twin watchdog failed open silently at boot
- `8d8ba5377fb6` Ceiling prompt showed 3 of 33 mined feats
- `92fd876c2f0e` Two rho-fallback checks that cannot run in normal operation
- `946153deafe9` completeness.category_size has no caller and claimed callers it did not have
- `a8464e348c5e` read pass stall: both 2026-08-27 causes are gone
- `b1f561587b19` Extra-entry penalty in the prose gate: fixed, verified twice
- `b57e23204f66` What rho() returns when the axis matrix is unreadable
- `b86d79c574e3` Same batch-instability finding, filed independently by sweep39 batch 9
- `cefcad5fc513` Step-4 enforcer assert_step4_open has no caller and is unwired
- `d2583f4c8b36` The local rung was unworkable because a game held the GPU
- `d47ea56cca29` the one unjudged assay mutant is a non-terminating loop
- `e637c67ab438` weave.null_threshold was unreported dead code
- `eb681053b234` pyflakes gate ran with no encoding contract
- `ee0e5bef7dab` Bulk-delete the leaked %TEMP% scratch directories
- `ef8940b363b3` Codex section substring fallback is not most-specific-wins
- `f2b06f8c9476` Synthesis prompt cut each entity's feats to the first three
- `f6c52ef7657f` Foreign semsearch daemon exhausts the machine's ephemeral ports
- `f90795d5c6bd` codewatch.stamp ignores its who argument

## Misfiled — confirm and they move to RUN/LOCAL (25)

- `0a9943374fe6` Publish-refusal check greps two of the most generic strings in Python
- `19791681f257` Survivor rows alias one red-gate list that is rewritten mid-run
- `19c507a16430` Unmarked store-time cuts in the records
- `1e83e387cfc1` Spawn-site anti-vacuity floor has 14 of headroom
- `2c8e55f8f3f7` An unrankable tier ranks as the lowest real tier
- `423e35500033` Empty provenance manufactures a probe out of nothing
- `541384445ec3` Grounding distribution log capped at exactly the population size
- `572918512dbc` Refusal-marker layer refuses real articles on the API transport
- `76ab006d84b8` band_for_quantity answers M0 on an axis it cannot measure
- `7716ac4884cc` Six pipeline.py line cross-references now point at the wrong lines
- `8350f7a183d1` alive_verdict answers "undetermined, because everything was fine"
- `85a6b7b9e2c8` pick_model claims MoE markers disqualify; the gate is size only
- `88a5f9192e1b` cachekey.owns ignores the host dimension
- `95f80c0ea860` tiers report denies the hyperverse it publishes on the next page
- `9e300162f4df` Composite catalogue hardcodes type "Deity" for every entry
- `b9584c782d95` feats --roll silently drops sources with no resolved host
- `c2bbe43e0f2d` A source with zero slug candidates gets a clean "no wiki" negative
- `d3acbb793ef2` Cascade pin path can dispatch a live call to the local GPU
- `dc501e776a2b` rigor certifies a nan matrix as maximally consistent
- `dc9ffadae765` Work-order evidence cites line numbers nothing has ever checked
- `e038ec1759a9` pick_model prints two different VRAM budgets in one table
- `e8466cd6ed14` chain.main() exits 0 over a CHAIN.json that was never written
- `e8622cf0d047` why=None reverts a good patch with a wrong error
- `ecc355769a41` Stored exception text cut at 120 chars, unmarked
- `fa86e8b92150` mine() drops uninteresting rejections to no counter

---

*Every order was judged on the current executable line, never on a comment: this
codebase records in comments what a line used to be, and that trap has produced false
positives for four separate readers. Orders whose reroute applies to only one half are
counted as decisions, not as reroutes.*
