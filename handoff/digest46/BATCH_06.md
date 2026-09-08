# OWNER DECISION DIGEST — BATCH 06

20 orders. **17 still live, 3 dead.** 3 should leave the OWNER/SESSION rung entirely.
Every "STILL LIVE" verdict below was checked against the current executable line, not a comment.

---

### 895a99602bf0  [OWNER] [MAJOR]  — What stops a thirteenth probe-litter site appearing
STILL LIVE: yes — but MUCH narrower than filed. The generic ratchet the order asks for **already exists in one of the two gates**: `verify_math.py:213-263` installs a spy on `health.record` AND a second spy on `health.flush`, `:334` snapshots the ledger file, and `:10013` asserts `check("no probe anywhere in this battery writes into the live failure ledger", _escaped20z, [])` with a control row at `:10037` proving the detector still fires. `drill.py` has **no equivalent**: its only ledger net, `a_probe_leaves_the_failure_LEDGER_alone` (`drill.py:11290`), byte-diffs the ledger around **two named probes**, not the whole run. Confirmed the per-site work held: all eight drill keys sit frozen at exactly 39 in `state/failures.json` today (not growing).
QUESTION:   Should drill.py get verify_math's whole-run leak spy, or should every gate instead redirect the ledger wholesale for its entire run?
OPTIONS:    (a) Port §20z's spy+snapshot apparatus into drill.py; per-call `_deliberately_failing` scoping stays as-is.  (b) Redirect LEDGER/LEDGER_LOCK for the whole of every gate run.  (c) Maintenance run snapshots/diffs each shift and files what grew.
RECOMMEND:  (a), with (c) as the standing check — and **not (b)**. (b) means a genuine fault occurring during a 20-minute gate run is never recorded operationally, and verify_math's own §20z comment already argues the opposite doctrine ("growth here is evidence to be READ, not automatically a fault of the battery"); the apparatus that answers this order is written, tested and running in one file already, so the work is a port, not a design.
COST IF WRONG: Pick (b) and the failure ledger goes blind for the duration of every drill/verify_math run — the exact window in which the library is stressing its own guards hardest. Pick (c) alone and site fourteen accumulates for another five weeks.
UNBLOCKS:   none directly, but it retires the per-site class that produced 247b173c78ee, 31a946e96c69, 630fe4529c51, b53dd5b3f76f.
THEME:      ledger hygiene

---

### 66f96febdb3a  [OWNER] [MAJOR]  — descending_ladder has no consumers; the gap it names is open
STILL LIVE: yes — re-grepped today. Every hit outside the file itself is prose or a scan list: `anchors.py:43` still tells a reader to "Use transgression_bits()", `drill.py:81` and `liveness.py:268` name it in a list of ten modules nothing imports, `secondopinion.py:25` is a historical note, `tempus.py:46` a comment. Nothing imports it; none of the seven public functions is called. `assay.py:74-75` still scores Reach off its own hand-written sub-planetary edges. What HAS changed: `liveness.scan()`'s module limb (order 209391b4f990) now reports it, and `drill.LIVENESS_CEILING` was raised 41→52 to absorb it — so it is instrumented, just still unwired.
QUESTION:   Wire the Ladder into assay's Reach axis, delete the module, or declare it reference-only in its own docstring?
OPTIONS:    (a) Wire it — `assay._band_for(reach)` consults `rung_for_length`, and `anchors.py:43`'s pointer becomes true.  (b) Delete it and drop the docstring's claim.  (c) Keep it, retitle the docstring as a reference table, and delete the "THE FIX, IN ONE SENTENCE" paragraph that promises a fix nobody applied.
RECOMMEND:  (a). The defect the docstring names is measurable and unfixed — sub-planetary Reach is scored against a floor that does not exist — and the arithmetic was already verified correct (monotonicity, domain guards, PLANCK_ENERGY against m_P c²), so (a) is wiring, not authorship. (b) throws away correct work to make a lint row go green.
COST IF WRONG: (a) changes published Reach bands for every sub-planetary entity, so the assay corpus needs a re-derivation pass. (b)/(c) leave every sub-planetary Reach score resting on an edge table nobody has defended.
UNBLOCKS:   the `descending_ladder` row inside `liveness.scan`'s dead_module set; sibling orders 707fefc17465 (render) and the scale_theories SWEEP34_FINDING are the same shape but separate rulings.
THEME:      unwired module

---

### 959b98f38a63  [OWNER] [MAJOR]  — Fandom throttling is our own aggregate rate, not a ban
STILL LIVE: yes, and **the seven-in-one claim is now FALSE**. Checked today: only **4 of the 7** named orders are still open — befb174bca20, ad80146c36dc, d7404ad383f1 (HOST_QUARANTINED, last seen 2026-09-07 00:48) and 3dc2832846bc (STALLED_UNRESTARTABLE, now seen 130 times, last 2026-09-07 18:48). d0f38ade3405, 1bf24541a18f and f3eb4708e29f have closed on their own. The BOTS rung now holds exactly 4 orders total, so this answer still clears the entire rung — just four orders, not seven.
QUESTION:   What number caps the library's aggregate request rate against the fandom.com edge, and which knob sets it?
OPTIONS:    (a) Lower `overnight.py:1624`'s `--workers 12`.  (b) Raise `feats.PAUSE` (0.34) or add a `HOST_PAUSE["fandom.com"]` entry.  (c) Make `_throttle` lock on the registrable domain rather than the netloc, so all `*.fandom.com` subdomains share one pacer.
RECOMMEND:  (c), then re-measure before touching (a) or (b). **This corrects the order's own diagnosis.** The order's two unestablished items are now measured: `--workers 12` is set at `src/overnight.py:1624`, and the per-host rate is NOT 12x anything — `feats._throttle` (`feats.py:122-149`) takes `_HOST_LOCKS[host]` and enforces `PAUSE = 0.34` s spacing, so one subdomain gets at most ~2.9 req/s no matter how many workers. But the lock is keyed on the **netloc**, and marvel/onepiece/naruto/dragonball/mtg/hokuto are six different netlocs hitting **one** Fandom edge from **one** IP — so twelve workers on twelve subdomains produce ~35 req/s to a host that thinks it is being asked 2.9. That is the over-request, and no per-host pause can see it.
COST IF WRONG: Turn `--workers` down without (c) and you crawl fewer sources at the same illegal aggregate rate — the 429s continue and Hard Rule 0 pays for it in wall-clock. Do nothing and STALLED_UNRESTARTABLE keeps refiling (130 and counting) while `HOST_QUARANTINED` has no health row to close against.
UNBLOCKS:   befb174bca20, ad80146c36dc, d7404ad383f1, 3dc2832846bc — the whole BOTS rung.
THEME:      crawl politeness

---
### SEPARATE FROM THE ABOVE — needs no ruling
`data/BINDING_HEALTH.json` was last written **2026-08-27 23:29 — 10.8 days stale** (worse than the 9.0 the order measured). Nothing schedules `binding_health.py`. Reroute to RUN: add it to the maintenance cadence. This is why the quarantine orders have no corroborating health row.

---

### 92fd876c2f0e  [SESSION] [MAJOR]  — Two rho-fallback checks that cannot run in normal operation
STILL LIVE: **NO** — the remedy the order specifies is built, in two places.
(c) is killed by `verify_math.py:8530-8554` (`_b4_axis_correlation_checks`): it sets `AC.load = lambda: None`, clears `A._RHO_CACHE[0]`, and calls `A._rho("reach","ruin")`, which reaches `assay._rho_doc`'s `if not doc:` limb at `assay.py:840` for real — setting `RHO_FALLBACK_REASON` and printing the stderr banner. Its own comment confirms the limb fires ("`axis_correlation.py:rho-no-matrix` stood at 30 in the live ledger, one a run"), and it is wrapped in `_no_ledger_vm()` for exactly that reason.
(b) is killed by `verify_math.py:7148-7159`, an **unconditional** row that forces the fallback state and asserts `"the matrix was unreadable on this run" in _fallback_stamp` — the same property the environment-conditional block at `:7014` was supposed to guard. `:7135-7146` adds the other direction ("a matrix that loads cleanly files NO fallback reason").
QUESTION:   none — nothing left to decide.
OPTIONS:    close it.
RECOMMEND:  Close. **Reroute one crumb to RUN/LOCAL — no ruling needed:** the vestigial `if _stamp.startswith("FALLBACK"):` block at `verify_math.py:7014-7017` is now dead weight duplicating `:7155`, and deleting it removes a check-that-cannot-fail from the file whose whole subject is checks that cannot fail.
COST IF WRONG: none.
UNBLOCKS:   the (b) and (c) limbs of 23dbbcd656f3.
THEME:      dead order

---

### 4d78c426afb3  [OWNER] [MINOR]  — MediaWiki category floor of 40 pages is undeclared
STILL LIVE: yes. `wiki_source.py:375` still defaults `all_categories(subdomain, min_pages=40)`, `:424` still sends `"acmin": min_pages`, `:462` still defaults `find_categories(..., min_pages=40)` — and `find_categories`' docstring at `:463` still promises "Every category on this wiki that holds subjects of the given canonical class" while documenting only the removal of `limit=6`. The floor is still unnamed in the function catalogue_web actually calls.
QUESTION:   Is a 40-page category floor a noise filter (declare it) or a silent cap on the universe (remove it)?
OPTIONS:    (a) Keep the floor, add one sentence to `find_categories`' docstring naming it.  (b) Remove the floor (`min_pages=1`) and rank instead, per Hard Rule 0.  (c) Keep 40 as the default but report the count and summed page-size of what it dropped.
RECOMMEND:  (c), then (b) if the tail turns out to hold cast. (c) is the cheap version of the measurement the order proposes without the extra Fandom traffic — the floor is applied server-side, so the only honest alternative to measuring it is disclosing it, and (c) does both over time. Note the same file already deleted `hard_stop=6000` and `limit=6` for this exact reason.
COST IF WRONG: (a) and you keep a server-side exclusion with no "and N more" anywhere in the tree — the invisible kind of cap. (b) unmeasured and you multiply category walks on the host that has already IP-blocked this machine (`wiki_source.py:155-158`).
UNBLOCKS:   none.
THEME:      undeclared cap

---

### bffc372a96d2  [OWNER] [MAJOR]  — The LOCAL rung is starved by the library's own daemons
STILL LIVE: yes, but **the (b) half is done and the numbers have moved**. `local_agent._chat` (`local_agent.py:1000-1055`) now reads `num_ctx` and `request_timeout` from config.yaml instead of the literals 8192/420, runs inside `gpu_lane.lane("local_agent")` at background priority, and retries a 503 four times before **raising** — so the "15 minutes, no output, exit 0" symptom the order was filed on is gone; the rung now reports `rc=1 transport: TimeoutError` instead of a silent success. Also re-counted: **LOCAL holds 43 open orders today, not 128** (OWNER 137, SESSION 63, RUN 50, BOTS 4).
QUESTION:   Does the maintenance shift get a reserved GPU slice, or is LOCAL formally a quiet-hours rung whose 43 orders get re-rated?
OPTIONS:    (a) Reserve a foreground `gpu_lane` claim for the maintenance shift, or a scheduled quiet window.  (b) Accept LOCAL as nights-and-weekends and re-rate the 43 open LOCAL orders to RUN/SESSION.  (c) Leave it: with the timeout and lane fixes in, measure one more shift before deciding.
RECOMMEND:  (c) for one shift, then (a). The two fixes that landed after this order was filed changed the input to the decision — the rung was being timed out at 420s against a config that serves 1800, so "the model is incapable" and "the lane is contended" were never separable. `gpu_lane` already has the foreground/background primitive (a) needs; spending a shift's measurement before re-rating 43 orders is cheaper than re-rating them twice.
COST IF WRONG: Pick (b) now and you may re-rate 43 orders off a rung that has just started working. Pick (a) blind and you give a repair lane priority over the library's own prose generation — the contention `gpu_lane`'s header exists to arbitrate.
UNBLOCKS:   9b54659bc403 ("the LOCAL rung came back empty-handed"), and the disposition of 43 LOCAL orders.
THEME:      local rung capacity

---

### fc08e056e1ab  [OWNER] [MINOR]  — Two disagreeing tests for "is this the entity's own page"
STILL LIVE: yes, verified today at the current line numbers (the order's 791/1144 have drifted). `read.py:841` reads `own = _norm_q(title).lower() == _norm_q(name).lower()`; `read.py:1194` still reads `if t.strip().lower() == name.strip().lower():` with no normalisation. The two tests still disagree for exactly the curly-punctuation class `_norm_q` exists to fold.
QUESTION:   Should `_queue_row` route through `_norm_q`, or is the raw comparison a deliberate, accepted cost at 282k rows a pass?
OPTIONS:    (a) Route `_queue_row` through `_norm_q` — one signal, one answer.  (b) Keep the raw compare and write the accepted gap into `_queue_row`'s docstring.
RECOMMEND:  (a). `_norm_q` is a regex fold over one short string and this runs once per row, not per character — the cost argument for (b) has never been measured, and the order itself measures the affected population at ~0.2% of 282,059 rows, i.e. roughly 560 entities systematically read late. Two implementations of one rule is the fault this project keeps paying for.
COST IF WRONG: (a) adds a normalisation call to a 282k-row pass. (b) leaves a deep entity's evidence read later than it should be, permanently, in the file whose stated design intent is "entities that already show evidence, deepest first".
UNBLOCKS:   none.
THEME:      normalisation mismatch

---

### 9fcbe25a473b  [OWNER] [MAJOR]  — pantheon prints an incomplete roster but returns rc=0
STILL LIVE: yes, verified line-by-line. `pantheon.py:279-283` still only `print()`s the `_incomplete` note and `continue`s — no `merge_failed.append`, no `silence.note`. The sibling `except Exception` at `:286-309` does all three, and the rc gate at `:397-401` (`if merge_failed: ... return 1`) is still blind to `_incomplete`.
QUESTION:   Is one already-diagnosed missing entity categorically less severe than losing the whole roster?
OPTIONS:    (a) Make `_incomplete` count toward `merge_failed` — same rc, same ledger trace, both shapes carry the same way out.  (b) Keep the asymmetry and write the reason into a comment beside the branch.
RECOMMEND:  (a). The file already states the principle two branches down in its own words — "a run that printed a ranking holding six of twenty-one entities is not a successful run, and rc=0 is how a scheduler records it as one" — and a ranking missing Son Goku is a smaller universe in the same shape as the real one either way. Nothing in the file defends the distinction, which reads as an unfinished repair, not a decision.
COST IF WRONG: (a) turns a scheduled pantheon run red whenever zfighters drops one entity, which is noisier. (b) leaves a provably incomplete published ranking reporting success to every scheduler, with the only trace on a console nobody reads.
UNBLOCKS:   completes order a8eb06d38216.
THEME:      rc honesty

---

### cdfeccbfbab0  [OWNER] [INFO]  — Two of three universe size classes refuse to produce a census
STILL LIVE: yes. `cosmography.py:134-135` still declares `POCKET: 1e-9` / `MINOR: 1e-6` while `SIZE_CLASS_MAX_GALAXIES` at `:161-163` caps both at 1.0, and the refusal is raised at `:295-300`. Re-grepped the call sites: `address_space.py:432,433`, `pipeline.py:2440`, `verify_math.py:634,1263,1265` — **every one passes the literal "STANDARD"**, so nothing breaks today. The comment at `:151-157` still says the ruling is deliberately not made here.
QUESTION:   Is a POCKET universe 1e-9 of an observable universe (200 galaxies), or at most one galaxy as its own description says?
OPTIONS:    (a) Set `SIZE_CLASSES["POCKET"]` and `["MINOR"]` to multipliers yielding <= 1 galaxy, matching the descriptions.  (b) Rewrite the descriptions to admit 200 / 200,000 galaxies.  (c) Leave both refusing and record the pending ruling in the charter.
RECOMMEND:  (a). "A closed loop, a demiplane, one stage and no sky" cannot hold 200 galaxies in any reading, so the multiplier is the wrong half — and `SIZE_CLASS_MAX_GALAXIES` already encodes that judgment, it is just not the value `census` computes from. (a) makes both classes usable without touching `validate()`.
COST IF WRONG: Effectively nil today — nothing calls them. The cost of leaving it is that `SIZE_CLASSES` advertises three classes and delivers one, and the first caller to reach for POCKET gets an exception instead of a documented refusal.
UNBLOCKS:   none.
THEME:      charter ruling

---

### 9e300162f4df  [SESSION] [MINOR]  — Composite catalogue hardcodes type "Deity" for every entry
STILL LIVE: yes. `catalogue_web.py:275` still writes `"type": "Deity"` and `:277` still writes the literal `"category": "Persons (named individual characters, real or fictional)"`, while the real category `c` is in scope at `:248` and simply not carried. The single-wiki path's fix (order 6eb20e8d3565) is present and works — but only there.
QUESTION:   none of substance — **reroute to RUN/LOCAL, no ruling needed.**
OPTIONS:    apply the remedy the order already specifies: build the same `first_cat` map on the raw title as titles arrive, and store `"type": _singular(first_cat.get(title) or "Deity")`, keeping the literal as the dropped-provenance fallback exactly as `catalogue()` does.
RECOMMEND:  Reroute. There is no judgment left in it — the sibling path is the worked precedent, the fallback shape is named, and the file already records what the same defect cost when measured (3,521 Media entries typed "Ability", 1,696 Vessels typed "Character").
COST IF WRONG: Nothing is wrong today because the only composite source is deity-shaped; the next non-pantheon COMPOSITE_SOURCES entry inherits a silent mislabel that `corpus_db` indexes and `manifest_builder` feeds to the prose model.
UNBLOCKS:   none.
THEME:      misfiled code fix

---

### d2da5914da94  [OWNER] [INFO]  — A source with no probeable categories is dropped, not marked unmeasured
STILL LIVE: yes. `completeness.py:583-584` still reads `if not sizes and failed == 0: return None`, one line below the `no_denominator` branch at `:581-582` that returns `_unmeasured(...)` for the structurally identical RAW-mode case.
QUESTION:   Does the HIGH standard "every source is fully catalogued" exclude an unprobeable source from its denominator, or name it as unmeasured?
OPTIONS:    (a) Keep returning None — genuine absence has no cast to measure.  (b) Return `_unmeasured(src, host, "every probe answered and none of the eight CATEGORY_PROBES categories exists on this wiki; its cast size is unknown, not zero")`.
RECOMMEND:  (b). The same function argues four separate times in its own comments that "a source absent from COMPLETENESS.json is indistinguishable from a source with nothing missing" — and CATEGORY_PROBES missing a wiki's real category name is a live failure mode this file already has a branch for (the `cov > 1.0` limb exists because The Division catalogued 448 against a probed 314). "Unknown" and "zero" are different answers and only one of them is honest here.
COST IF WRONG: (b) adds rows to COMPLETENESS.json — but every consumer (`foreman._catalogue_batch`, `catalogue_web --shortfall`) already skips on `c.get("unreliable")`, so dispatch does not change. (a) keeps a class of source invisible in the file built to make invisibility impossible.
UNBLOCKS:   none.
THEME:      absent vs unknown

---

### 70f66fbd98aa  [OWNER] [MINOR]  — runguard fails OPEN on a corrupt guard, against Hard Rule -1
STILL LIVE: yes. `runguard.py:60-69` still returns None on any exception (with `silence.note("runguard.read")` — so there IS a ledger trace, which the order does not credit), and `holder_is_live` at `:145-151` still returns False for a record whose `heartbeat` is missing or non-numeric. Both are the documented fail-open the order objects to.
QUESTION:   Should a corrupt MAINTENANCE_RUN.json stay "free to claim", or escalate so a person clears it?
OPTIONS:    (a) Keep fail-open, and record the exception as a ruled Hard Rule -1 exception in CLAUDE.md so the next auditor finds a decision rather than a departure.  (b) Fail closed and refuse to claim.  (c) Keep fail-open but raise an escalation rung on the corrupt-guard path, so the claim proceeds AND a person is told.
RECOMMEND:  (c) — and note this is the owner's call because **it touches the one invariant that prevented bug m27** (two maintenance runs overlapping, one clobbering the other). (c) is the only option that keeps the guard's stated safety property (nothing else repairs a corrupt MAINTENANCE_RUN.json, so failing closed wedges the pass permanently) while ending the silence Hard Rule -1 actually forbids — the rule's words are "Silence must never authorise anything," and today the authorisation is silent even though the note is filed.
COST IF WRONG: (b) wedges every maintenance pass on a file nothing repairs — a permanent red, which this project's own preflight doctrine names as how a check stops being read. (a) leaves the departure standing, correctly documented.
UNBLOCKS:   none.
THEME:      fail-open exception

---

### 189532cbf41a  [OWNER] [INFO]  — Spine-gap report shows 4 of 33 unassigned sources
STILL LIVE: yes. `estate.py:422` still reads `f"{len(un)} — e.g. " + ", ".join(un[:4])`, graded `bad=False` at `:416-420`. And the artifact meant to carry the full list is **worse than stale**: `output/index/unassigned_sources.md` was last written **2026-08-27** and still says "**None.** Every populated source on the Acquisitions Roll resolves to a real spine code" — flatly contradicting the 33 this function measures. There is still nowhere in the tree a person can read the other 29 names.
QUESTION:   Print all 33 names, or keep the four-name sample?
OPTIONS:    (a) Join all of `un` (already sorted) and keep the row `bad=False`.  (b) Keep `[:4]` and fix `unassigned_sources.md` to carry the full list.  (c) Both.
RECOMMEND:  (c), and (a) is the half that must not wait. Thirty-three names is nothing to print, the standing house rule is that a cap is a truncation hiding a smaller universe, and the `[:4]` is currently the only thing between the owner and the exact worklist Hard Rule 2 reserves to them. The stale artifact is a separate RUN fix and should not gate the one-token change.
COST IF WRONG: Keeping `[:4]` costs nothing operationally and hides 29 names the owner is the only person allowed to act on.
UNBLOCKS:   none — but file the stale `unassigned_sources.md` separately to RUN.
THEME:      cap on a worklist

---

### eb681053b234  [SESSION] [INFO]  — pyflakes gate ran with no encoding contract
STILL LIVE: **NO.** Fixed at `local_agent.py:665-667`: the call now reads `subprocess.run([PY, "-m", "pyflakes", full], capture_output=True, text=True, timeout=120, creationflags=_NO_WIN, env=dict(os.environ, PYTHONIOENCODING="utf-8"))`, and the comment at `:658-664` records the repair (sweep42-batch16) in the order's own terms. It now matches its two siblings at `:734-737` (import gate) and `:744-747` (verify_math gate), which is the bar the order set.
QUESTION:   none.
OPTIONS:    close it.
RECOMMEND:  Close. **Reroute one crumb to RUN/LOCAL — no ruling needed:** the pyflakes call still lacks `cwd=HERE` (both siblings have it) and all three gates still lack `encoding="utf-8", errors="replace"`, which `t_run_check` at `:389-391` does set. One line, three call sites, no judgment.
COST IF WRONG: none.
UNBLOCKS:   none.
THEME:      dead order

---

### 2c8e55f8f3f7  [SESSION] [MINOR]  — An unrankable tier ranks as the lowest real tier
STILL LIVE: yes. `address.py:451` still reads `return order.index(tier) if tier in order else 0`, so `tier_rank("KINGDOM") == tier_rank("volume") == 0`, and `promote()` at `:465-468` returns `current` unchanged whenever `tier_rank(earned) <= tier_rank(current)` — preserving a corrupt shelf address indefinitely.
QUESTION:   none of substance — **reroute to RUN/LOCAL, no ruling needed.**
OPTIONS:    apply the order's own remedy: `tier_rank` returns None for an unrecognised tier, `promote()` treats an unrecognised `current` exactly as it treats None (take `earned`), and logs the unrecognised value.
RECOMMEND:  Reroute. Nothing here needs a judgment — the promotion-only asymmetry the file defends at `:457-462` is untouched by the fix (an unrankable value is not a rank, so repairing it upward is not a demotion), and no reading defends silently carrying an address nobody can read.
COST IF WRONG: A corrupt or renamed tier value on a source's row survives every promotion pass for as long as the source stays under 400 entries, indistinguishable in output from a legitimate "volume".
UNBLOCKS:   none.
THEME:      misfiled code fix

---

### 5c962f306e58  [OWNER] [MAJOR]  — The model-patch gate skips the entire VERIFY tier
STILL LIVE: yes, exactly as filed. `foreman.py:1332` still runs `_run([os.path.join(SRC, "allsweep.py"), "--quick"], timeout=900)`, and `allsweep.py:790` and `:815` still read `if not a.quick:` around the VERIFY tier and the ESTATE tier respectively — so all ten verifiers, `rosetta.py --check` included, are skipped by the last gate standing in front of an autonomous model's writes.
QUESTION:   Does the model-patch lane's gate need to run the VERIFY tier, given the foreman's 20-minute loop?
OPTIONS:    (a) Keep `--quick` — the trade that lets the lane exist.  (b) Run the full sweep on the patch lane only (not on every foreman round).  (c) Add a `--quick --contracts` mode that runs each verifier's CLI for exit-code shape only, without its internal battery.
RECOMMEND:  (c). It answers the actual gap — a verifier's **CLI/exit-code contract** is what a model patch breaks, not its internal logic, which `verify_math` already pins separately — at a fraction of the VERIFY tier's cost, so it fits inside the foreman's round. (b) is correct and unaffordable; (a) leaves one layer and a decoy where Hard Rule -1 requires layers that fail differently. Note that `_checks_pass` is already deliberately strict (no pre-patch baseline, `:1355-1359`) — this adds coverage, it does not loosen anything.
COST IF WRONG: Pick (a) and the rosetta-class regression that ran for eleven runs can recur, accepted by a gate that says "verified". Pick (b) and the patch lane cannot finish inside the foreman's 20-minute round, which its own comment says is by construction.
UNBLOCKS:   none.
THEME:      gate coverage

---

### 864a626a258e  [OWNER] [INFO]  — CLAUDE.md's "all 57 nets" is stale by an order of magnitude
STILL LIVE: yes. `CLAUDE.md:105` still reads "**PROVEN** — `python src/drill.py` attacks all 57 nets and reports HELD or BREACHED for each." The static count of `net(` call sites in `src/drill.py` is now **449** (the order measured 269; it has grown 67% since), and the runtime count is higher because two sites sit inside `for` loops. `drill.py:3672` still reasons from the stale figure — "WHY 57 NETS MISSED IT".
QUESTION:   What should the sentence say instead — and it stays OWNER only because CLAUDE.md is the owner's document.
OPTIONS:    (a) "attacks every net".  (b) "attacks all ~449 nets".  (c) Leave it and add a note that the number is illustrative.
RECOMMEND:  (a). It is the only wording that does not need re-editing every time an area is added, and 57 is the one claim in that paragraph a reader can check — a figure off by 8x in the safety layer's own charter is the kind of thing that stops a reader checking the other two properties. INDEPENDENT / FAIL CLOSED / PROVEN are unaffected and should stand exactly as written.
COST IF WRONG: (b) is accurate today and stale next week. Doing nothing leaves a falsifiable claim in the document every other rule cites.
UNBLOCKS:   none — but `drill.py:3672`'s "WHY 57 NETS MISSED IT" should be reworded in the same pass (RUN).
THEME:      stale doctrine

---

### efd2b537f26d  [OWNER] [MINOR]  — warthunder's catalogued entry names are not article titles
STILL LIVE: yes, and it is refiling — `seen: 66`, last seen 2026-09-07. `binding_health.identity` confirms the binding is CORRECT (sitename "War Thunder Wiki" matches the bound source at score 100.0); the fault is that none of the catalogued titles resolve there, so the entry names are not that wiki's article titles.
QUESTION:   Is this source mined at feature level with no per-entry articles, or should its entries be re-catalogued under the names that wiki actually uses?
OPTIONS:    (a) Declare it feature-level and suppress the recurring order.  (b) Re-catalogue its entries against the wiki's real titles.  (c) Split the source — "War Thunder" binds to this wiki, the World of Tanks/Warplanes/Warships half binds elsewhere.
RECOMMEND:  (c), falling back to (a). The source name is a four-game composite ("War Thunder + World of Tanks/Warplanes/Warships (space-refit)") bound to a wiki that covers one of them, which is the likeliest reason its titles do not resolve — that is a curatorial split, not a mining failure. If the owner does not want to split, (a) at least stops a resolved condition refiling hourly.
COST IF WRONG: Nothing breaks — mining continues either way, which is why this has sat at MINOR for 66 sightings. The cost of leaving it is one permanently-red row that trains a reader to skim the binding-health output.
UNBLOCKS:   none.
THEME:      curatorial

---

### f2b06f8c9476  [OWNER] [MINOR]  — Synthesis prompt cut each entity's feats to the first three
STILL LIVE: **NO.** Order 0e041fe97852 replaced it. `pipeline.py:1496-1512` no longer contains `fl[:3]` anywhere: the feats are now sorted richest-first by flattened length, carried until the 420-char budget is spent, and the line ends with an explicit `[N of this entity's M mined feats withheld for prompt budget, ranked richest-first]`. The docstring at `:1479-1494` names this order's exact objection and states the resolution — "What was wrong was that the bound was neither RANKED nor DISCLOSED."
QUESTION:   none. The Hard Rule 0 objection is answered; a ranked, disclosed prompt budget is not a cap.
OPTIONS:    close it.
RECOMMEND:  Close. If the owner wants to revisit whether 420 chars is the right budget, that is a fresh question with the numbers now visible in the prompt itself — which is what the code's own docstring says it deliberately left open.
COST IF WRONG: none.
UNBLOCKS:   none.
THEME:      dead order

---

### 8f50f37255b5  [OWNER] [MAJOR]  — _STOPNAMES deletes real named entities from the entity index
STILL LIVE: yes, and now measurable. `weave_index.py:368-370` still reads `if key in _STOPNAMES: excluded[...] += 1; continue` — a full drop from `ENTITY_INDEX.json`, not merely from cross-source matching. Confirmed against the live artifact: **zero** of the 34 stopnames appear as keys in the 266,406-key `data/ENTITY_INDEX.json`, so Fullmetal Alchemist's "Father", Rush's "Oracle", and every entity literally named King/Queen/Dragon/Narrator is invisible to the index. What HAS changed since filing: the casualties are now counted and printed (`:340`, `:369`, `:438-441`), and the code at `:361-364` explicitly parks the ruling with this order id — "so the ruling can be made against a number." Run `python src/weave_index.py` to see that number before ruling.
QUESTION:   Should a generic-sounding name exclude an entity from the index entirely, or only from cross-source candidate matching?
OPTIONS:    (a) Move the filter to the MATCHING step — index everything, refuse to treat a stopname collision as evidence.  (b) Keep the drop and rename the filter so the docstring stops implying it is a matching-only concern.  (c) Keep the drop but emit the excluded names to a sidecar file so nothing is unrecoverable.
RECOMMEND:  (a). The filter's own comment says the rationale is that "a collision on these is meaningless" — which is an argument about matching, not about existence, and the code applies it to existence. Hard Rule 0's shape exactly: a filter silently deciding certain named entities do not exist, in the artifact `weave`, `cosmology_graph` and `thread_integrity` all read as the roster.
COST IF WRONG: (a) grows ENTITY_INDEX.json (already 177 MB) and puts 34 high-collision keys back into the matcher's path, so the matching-side refusal must land in the same change or cross-source matching gets noisier. (b)/(c) leave the library unable to name a character called Father.
UNBLOCKS:   none.
THEME:      silent exclusion

---

## ROLL-UP

| | count |
|---|---|
| Still live | 17 |
| Dead — close without reading | 3 (92fd876c2f0e, eb681053b234, f2b06f8c9476) |
| Reroute off OWNER/SESSION — no ruling needed | 3 (9e300162f4df, 2c8e55f8f3f7, + 864a626a258e's drill.py half) |
| Residual RUN crumbs from dead orders | 2 (verify_math.py:7014 vestigial block; local_agent pyflakes `cwd=HERE`) |
| Separate RUN items surfaced | 2 (BINDING_HEALTH.json 10.8d stale; unassigned_sources.md stale since 2026-08-27) |

**Themes:** ledger hygiene · crawl politeness · gate coverage · caps and disclosure · fail-open exceptions · unwired modules · misfiled code fixes · charter rulings · curatorial

**Three highest-value decisions, in order:**
1. **959b98f38a63** — clears the entire BOTS rung (4 orders, one of them refiled 130 times), and the diagnosis now has the measurement it was missing: the throttle is keyed per-netloc while Fandom rate-limits per-IP across all subdomains.
2. **5c962f306e58** — this is the last gate in front of an autonomous model's writes to live source, and it currently skips all ten verifiers.
3. **895a99602bf0** — the apparatus the owner is being asked to authorise is already written and running in verify_math; the decision is whether to port it to drill or to redirect the ledger wholesale, and only one of those keeps a genuine mid-gate fault recordable.
