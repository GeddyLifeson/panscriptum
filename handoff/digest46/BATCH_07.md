# OWNER DECISION DIGEST — BATCH 07

20 open OWNER/SESSION orders, each checked against the CURRENT executable line on 2026-09-07.
Two are dead. Five are code fixes misfiled on the decision rung. Thirteen need a ruling.

---

### f9643582fd29  [OWNER] [MAJOR] — Close the sandbox claim window or accept the race
STILL LIVE: yes — `src/mutate.py:1337-1354` is unchanged: `reap_orphans()` then
`root = tempfile.mkdtemp(prefix="panscriptum_mutate_")` then `_claim_sandbox(root)`, with the
comment still ending "Left open on purpose." `_claim_sandbox` (mutate.py:1157) cannot run earlier
because it writes INTO the directory. The drill-side containment did land (`tempfile.tempdir` is
redirected at drill.py:11966 and :12062), so only the drill is fenced off, not the window.
QUESTION:   Do we restructure `sandbox()`'s claim sequence so a zero-age reap can never take a
            sandbox that has no owner file yet, or keep it as an accepted risk now that the one
            known zero-age caller is fenced?
OPTIONS:    (a) mkdtemp under a prefix the reaper does NOT match, write the owner file, then
            rename into `panscriptum_mutate_*` — the claim exists before the name is reapable
            (b) leave the window; the drill redirect is the whole mitigation
            (c) (a) plus a guard in `reap_orphans` refusing `older_than=0` unless the temp root
            has been redirected away from the real one — belt on top of braces
RECOMMEND:  (a)+(c) — the rename is one line of reordering and removes the mechanism rather than
            the one caller that could reach it. (c) is a strengthening, not a weakening: it makes
            the aggressive parameter unreachable against a live tempdir by anything at all.
COST IF WRONG: (b) risks another ~20h pass dying at a target boundary with a third of its mandate
            unmeasured, and the evidence for next time is already degraded (see below). (a) done
            carelessly leaks unowned directories under a name nothing reaps.
UNBLOCKS:   none
THEME:      sandbox reaper
NOTE:       the order's second half — narrowing order 247b173c78ee's `_deliberately_failing`
            wrapper (drill.py:12079) so it stubs `health.record` only for the fixture
            directories and not across the reap's pass over real sandboxes — needs no ruling.
            Reroute that half to RUN/LOCAL; it is the signal you would want the next time this
            happens.

---

### 7099a092abd3  [OWNER] [MAJOR] — Thirteen public functions the battery alone calls
STILL LIVE: yes — re-ran the AST scan today over all of `src/` including `src/deprecated/`. All
thirteen still have ZERO callers outside verify_math/drill/liveness/mutate/secondopinion, and the
battery's grip has tightened, not loosened: `assay.interval_from_hands` now has 13 battery call
sites where the order measured 8.
QUESTION:   For each of the thirteen — reference apparatus kept deliberately, or a leftover to
            retire with its battery rows?
OPTIONS:    (a) keep all thirteen, add one line per function saying it is charter apparatus with
            no consumer, correct order 1a9c237dda4d's evidence
            (b) retire a named subset and delete their verify_math rows with them
            (c) rule the CLASS once ("battery-only symbols are kept and marked") and let a
            maintenance run apply the marker everywhere it applies
RECOMMEND:  (c), then (a) for these thirteen. One class ruling settles five other orders on this
            desk, and deleting charter apparatus on an audit's say-so is the failure mode
            CLAUDE.md's own preamble is about.
COST IF WRONG: keeping leftovers means the battery goes on proving properties of code that never
            runs, which is what order 06b7f22484df already cost. Retiring wrongly deletes charter
            machinery no consumer has been written for YET.
UNBLOCKS:   0291835411d9, 665e3609bc82, db36d589713e, da15f582b2ea, and the urgency half of
            38c51153243c
THEME:      dead apparatus ruling

---

### ef4ca9edd61f  [OWNER] [MAJOR] — Re-mine 34,850 records that cannot say why they are empty
STILL LIVE: yes, and I re-measured it rather than trusting the order. Full scan of all 276,218
files under `data/feats` today: **34,850 records (12.62%)** carry `pages_read=[]` AND
`pages_refused={}`. marvel.fandom.com 13,664 of 53,922 (25.3%), dc.fandom.com 4,802 of 55,565
(8.6%) — and worse tails the order did not name: www.dandwiki.com 779 of 805 (96.8%),
forgottenrealms 2,517 of 4,194 (60.0%), en.wikipedia.org 2,964 of 6,392 (46.4%). The write at
`src/feats.py:1563-1584` is still unconditional and `mined_under` still carries only
`{stripper, attribution}` — no transport outcome.
QUESTION:   Once the transport outcome is stamped on new records, what happens to the 34,850
            already on disk that cannot be classified after the fact?
OPTIONS:    (a) stamp going forward, leave the legacy records — they stay ambiguous for ever
            (b) stamp, then re-mine all 34,850 — network spend against hosts already throttling
            (c) stamp, then re-mine only the hosts whose empty-rate is anomalous against a
            comparable corpus (marvel at 25.3% vs dc at 8.6% on the same wiki farm), leaving the
            rest to age out naturally as the stamp spreads
RECOMMEND:  (c) — it buys the answer where the ratio says something is wrong and does not spend
            30k+ fetches to re-confirm absences that are probably genuine. dc.fandom.com is the
            built-in control: same farm, same corpus size, a third the rate.
COST IF WRONG: (a) leaves an eighth of the evidence corpus permanently unable to tell a throttle
            from an honest blank — the module's own signature failure, at rest. (b) risks the
            IP ban this project has already taken once.
UNBLOCKS:   partially settles the direction of 6d594a775899 (same record, same distinction)
THEME:      cache honesty

---

### 88a5f9192e1b  [SESSION] [MAJOR] — cachekey.owns ignores the host dimension
STILL LIVE: yes — `src/cachekey.py:93-101` still reads `doc.get("entity") == name` and nothing
else, and `host_dir` at :67-69 still applies the same lossy `_SANITISE`+`[:40]` that produced the
founding name bug.
QUESTION:   **Reroute to RUN/LOCAL — no ruling needed.** The only thing that made this a decision
            was the risk that adding a host check would invalidate cache records written before
            `host` was stored, forcing a mass re-mine. I measured it: of 276,218 files, exactly
            **ONE** lacks a `host` key. The remedy costs one re-mine repo-wide.
OPTIONS:    (a) hand it to a code rung as specified — `owns()` also compares `doc.get("host")`,
            `write_path()` disambiguates on a host mismatch
            (b) keep it on the owner's desk
RECOMMEND:  (a) — the measurement removes the judgment. Today's collision count is still 0 across
            141 hosts, but `doc:arcanum-worlds-odyssey-of-the-dragonlords` sits at exactly the
            40-character boundary, so the cap is live and binding.
COST IF WRONG: nothing material; the change is cheap and the failure it prevents is one entity's
            evidence silently overwriting another's with nothing raised or logged.
UNBLOCKS:   none
THEME:      cache identity

---

### 13aee150e0dc  [SESSION] [MINOR] — A lock file moves a stale-code alarm four rungs down
STILL LIVE: yes — `src/codewatch.py:675` still reads
`escalation.JANITOR if shift else "MANAGER"`, with `shift` coming from
`_maintenance_run_live()` reading `state/MAINTENANCE_RUN.json`.
QUESTION:   Should a heartbeating maintenance-run guard file be allowed to move "a daemon is
            running code nobody asked for" from MANAGER (stop the subsystem) to JANITOR (no
            authority to stop anything)?
OPTIONS:    (a) escalate at MANAGER unconditionally and carry the shift-versus-pathology
            distinction in the message and the evidence dict, which already holds
            `maintenance_run_live`
            (b) keep the split and correct `_maintenance_run_live`'s "ASKED ONLY TO DESCRIBE,
            NEVER TO DECIDE" docstring to say what it actually governs
RECOMMEND:  (a) — the escalation fires either way, so (a) costs only louder filing during a
            shift, while (b) leaves any writer of that guard file — including a crashed run that
            left `done:false` with a fresh heartbeat — able to demote the alarm for free.
COST IF WRONG: (a) produces MANAGER-rung lines through every long maintenance shift, which is
            noise on a rung that is supposed to mean something.
UNBLOCKS:   none
THEME:      escalation rung

---

### 505177847f43  [OWNER] [MAJOR] — Foreign process starving the free local labour rung
STILL LIVE: **NO** — measured on this machine today. There is no `semsearch.cli watch` process:
`Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'"` returns fourteen processes, every one
of them Panscriptum or the cooldown guard, and pid 11468 does not exist. Port 11434 carries **6**
ESTABLISHED connections, not 9,599, and their owners are `ollama.exe` (42876) plus this project's
own `read.py`, `pipeline.py` and `verify_math.py`. The decision the order asked for — whether to
kill another of your applications to free the shared daemon — has expired with the process.
QUESTION:   Nothing left to decide about pid 11468. Optionally: do you want a standing rule?
OPTIONS:    (a) close it as resolved-by-disappearance
            (b) close it and record one standing line — "a non-Panscriptum holder of :11434 is
            reported, never killed" — so the next occurrence is a report and not a question
RECOMMEND:  (b) — it costs a sentence and the answer you gave last time (a person's call) becomes
            the recorded rule rather than something rediscovered.
COST IF WRONG: none. The LOCAL rung's economics still need watching, but the measured cause is
            gone and the order's evidence no longer describes this machine.
UNBLOCKS:   none
THEME:      resolved by time

---

### 38c51153243c  [OWNER] [MINOR] — Is the Ruin band edge meant to be U-shaped?
STILL LIVE: yes — `src/descending_ladder.py` DESCENDING table is unchanged (Og -5 at 1.0e5 J
dropping to Cl -6 at 1.0e-11 J, minimum at Ml -9, rising to Pk -14 at 1.956e9 J), and the header
sentence declaring binding energy the Ruin rung edge is still one line above it. Still no
functional consumer: a tree-wide grep finds `descending_ladder` only in comments (drill.py:81,
liveness.py:268, secondopinion.py:25, tempus.py:46), never an import.
QUESTION:   Is X.2's Ruin axis meant to be non-monotonic in binding energy below rung 0 —
            physically honest — or is the upper half quoting a different quantity from the lower?
OPTIONS:    (a) reading one is right: extend the header to SAY the Ruin column is U-shaped and
            why, so the next reader does not file it as a bug
            (b) reading two: the Og->Cl step and the sign of the lower half both need work
RECOMMEND:  (a) — a cell really is easier to disrupt than a nucleus, and an axis that says so is
            telling the truth about the world. Say it in the header; the unstated
            non-monotonicity is the actual defect.
COST IF WRONG: if (b) is right and you affirm (a), any future Ruin scorer reading these as band
            edges gets a two-valued mapping — 1e-11 J falls at both rung -6 and near rung -12 —
            and cannot say which rung it means.
UNBLOCKS:   none
THEME:      charter physics

---

### 4f308dbd9d2c  [SESSION] [MAJOR] — Switch on title resolution, or declare it off
STILL LIVE: yes — `grep resolve_title` over `src/` returns two lines, both inside feats.py, and
the second is the def at :933. `discover()` still does `add(name)` at :879 and
`apprefix=f"{name}/"` at :897 with the raw catalogue name; both `evidence_for` call sites still
pass it. The 17,148 entries the docstring is about are, per the call graph, still unmitigated.
QUESTION:   Do we wire the ranked title resolver into the live mining path, or rule that its
            ranking is not safe enough and say so in the docstring?
OPTIONS:    (a) resolve in `discover()` and add the resolved title ALONGSIDE the raw name, using
            it as the subpage apprefix; stamp `mined_under` with which name found the pages
            (b) resolve in `evidence_for` and pass both names down
            (c) rule it off, rewrite the docstring so it stops reading as live machinery
RECOMMEND:  (a) — alongside-not-instead means a wrong resolution costs an extra fetch rather than
            a misattribution, and the `mined_under` stamp is what stops the fix being cached
            away and not in effect. `_page_exists` (:925) goes with the same decision.
COST IF WRONG: (c) permanently accepts 17,148 entities reading as "no evidence" when they mean
            "we looked under the wrong name". (a) without the stamp re-mines nothing, because
            the cache serves the old empty records.
UNBLOCKS:   665e3609bc82 (same two functions); would partially relieve 0fbaba6e1070
THEME:      title resolution

---

### 6d594a775899  [OWNER] [MINOR] — Does pages_read mean fetched or read?
STILL LIVE: yes — `src/feats.py:1563` still writes `"pages_read": sorted(pages)` with refused
titles left in `pages`, and `src/coverage.py:177-179` still computes
`st = "CITED" if feats else ("READ" if pages else "NO PAGE")` with no fourth state. The same
verbatim copy still lands in an assay row at `src/magnitude.py:1450`.
QUESTION:   Is `pages_read` a fetch log the consumers must correct for, or a misnamed field that
            should hold only pages that passed the gate?
OPTIONS:    (a) rename: `pages_read` holds only gate-passing pages, new `pages_fetched` preserves
            the old number — a persisted schema change touching every pre-`pages_refused` reader
            (b) leave the field as a fetch log and make coverage.py and magnitude.py subtract
            `pages_refused` themselves
RECOMMEND:  (a) — the field's name is a claim and it is currently false; (b) leaves the same trap
            armed for the next consumer. Either way coverage.py needs a REFUSED state, because
            "we were served a block page" is not "READ".
COST IF WRONG: (a) mis-migrated means old records read as having fetched nothing. (b) keeps a
            wholly-blocked entity classified read-and-silent, which is the exact confusion
            `pages_refused` was added to end, restored one layer up.
UNBLOCKS:   shares a direction with ef4ca9edd61f — decide both in one sitting
THEME:      cache honesty

---

### 665e3609bc82  [OWNER] [MINOR] — Four uncalled functions in feats.py
STILL LIVE: partly, and it should be merged rather than answered. `axis_evidence` is RESOLVED:
order 73aacce08418 landed and it is now a wrapper over the single shared predicate
`_axis_independent_gates` (`src/feats.py:1327-1357`), so the two-definitions drift hazard the
order named is gone — the function is still uncalled, but it can no longer disagree with the live
gate. All four line numbers in the order are stale (now 925, 933, 1355, 1606). What remains live
is the same question 4f308dbd9d2c asks about `resolve_title`/`_page_exists`, and the same class
question 7099a092abd3 asks about everything else.
QUESTION:   Nothing separate. Merge into 4f308dbd9d2c (resolve_title, _page_exists) and the class
            ruling in 7099a092abd3 (axis_evidence, remine).
OPTIONS:    (a) close as duplicate once those two are answered
            (b) answer it separately anyway
RECOMMEND:  (a) — answering it on its own re-decides the same two things in a different order and
            leaves stale line numbers on the record.
COST IF WRONG: none; the underlying functions are covered either way.
UNBLOCKS:   none — it is itself unblocked by 4f308dbd9d2c + 7099a092abd3
THEME:      dead apparatus ruling

---

### 76ab006d84b8  [SESSION] [MINOR] — band_for_quantity answers M0 on an axis it cannot measure
STILL LIVE: yes — `src/assay.py:246-250` is unchanged, `out = "M0"` survives every comparison
when `BAND_EDGES[b].get(axis, math.inf)` never matches, and BAND_EDGES (:73-89) still carries
floors for five axes only.
QUESTION:   **Reroute to RUN/LOCAL — no ruling needed.** The house convention is already settled
            inside this same file: `axis_score` at :226-228 does `lo = BAND_EDGES[band].get(axis)`
            and returns None when there is no floor. `band_for_quantity` is the one sibling that
            does not, and the order names both the fix and the pin not to break
            (verify_math.py:5686).
OPTIONS:    (a) hand it to a code rung as specified
            (b) keep it here
RECOMMEND:  (a) — there is no judgment left; the function's own neighbour shows the answer.
COST IF WRONG: negligible, provided the sub-floor behaviour for a REAL axis is untouched.
UNBLOCKS:   none — though note this function is one of the thirteen in 7099a092abd3, so it is
            fixed on a path only the battery calls
THEME:      stored truncations / false confidence

---

### fa86e8b92150  [SESSION] [MINOR] — mine() drops uninteresting rejections to no counter
STILL LIVE: yes — `src/feats.py:1211-1213` is still `if P.valid_scale_note(s): ... elif
_QUANTITY.search(s) or re.search(...)` with no `else`, and `_UNIT_DROPS` (:297-298) still carries
only `seen/short/long`.
QUESTION:   **Reroute to RUN/LOCAL — no ruling needed.** The remedy is fully specified, the
            precedent is in the same file (order eacc5444288c's `_UNIT_DROPS`), and the order
            explicitly forbids the one expensive variant ("do NOT widen `gate_rejected`").
OPTIONS:    (a) hand it to a code rung: one counter, printed in roll()'s summary even when zero,
            plus a correction to both docstrings
            (b) keep it here
RECOMMEND:  (a) — the only content is a counter and two sentences of docstring truth-telling.
COST IF WRONG: nothing breaks; the module's docstring simply goes on promising an auditable
            rejection rate over a pre-filtered denominator.
UNBLOCKS:   none
THEME:      stored truncations

---

### ecc355769a41  [SESSION] [MINOR] — Stored exception text cut at 120 chars, unmarked
STILL LIVE: yes, with the line numbers moved: the three `"%s: %s" % (type(e).__name__,
str(e)[:120])` sites are now `src/binding_health.py:505, :711, :845` (the order says 486/692/826).
All three still flow to stored fields, and :711's reaches `data/HOST_QUARANTINE.json`'s reason.
QUESTION:   **Reroute to RUN/LOCAL — no ruling needed.** Hard Rule 0 (CLAUDE.md:138) and this
            same module's order d6ca84486153 — which already removed `str(reason)[:300]` one
            level down for being "a hard slice on a STORED field, which is Hard Rule 0's exact
            shape" — settle it. There is nothing here the owner has not already ruled.
OPTIONS:    (a) hand it to a code rung: store the text whole at all three sites
            (b) keep it here
RECOMMEND:  (a) — the identical cut on the identical path was already removed by owner-standing
            doctrine; this is the copy that survived.
COST IF WRONG: none. A quarantine reason cut mid-title with the closing parenthesis gone is the
            measured failure this already cost once.
UNBLOCKS:   19c507a16430 (same doctrine, same answer)
THEME:      stored truncations

---

### 19c507a16430  [SESSION] [INFO] — Unmarked store-time cuts in the records
STILL LIVE: yes, and there is now a SIXTH the order does not list. Current lines:
`evidence[:600]` and `rationale[:900]` at `src/pipeline.py:1600-1601`; `scale_note[:500]` and
`scale_note_rejected[:500]` at :2027 and :2029; `topic_rejected[:120]` at :2076; and
`subroom_rejected[:120]` at :2087, which is new since the order was filed.
QUESTION:   **Reroute to RUN/LOCAL — no ruling needed.** The house idiom is fixed
            (`policy._observed` appends "... (+N chars)") and Hard Rule 0 covers stored cuts.
OPTIONS:    (a) hand it to a code rung: apply the marker idiom at all six sites (not five)
            (b) drop the bounds entirely
RECOMMEND:  (a) — the marker preserves the bound and makes a short value distinguishable from a
            shortened one, which is the whole property. Tell whoever takes it about :2087.
COST IF WRONG: low. These fire only on a non-compliant model answer, which is exactly the case a
            reader most wants intact.
UNBLOCKS:   none — settled by the same answer as ecc355769a41
THEME:      stored truncations

---

### da15f582b2ea  [OWNER] [MINOR] — A declared safety with no site that can raise it
STILL LIVE: yes — `class Refused(RuntimeError)` is now at `src/escalation.py:75` (the order says
:64) and a tree-wide grep still finds no `raise Refused`, no `except Refused`, and no import of
it. Its sibling `SystemHalted` two lines below is raised and caught; `prose_gate.ProseRefused`
and `threads.ThreadRefused` are separate private types.
QUESTION:   Are the OPERATOR and SUPERVISOR rungs expressed through this type, or through the
            per-module refusal types that already exist — and if the latter, does the declared
            class stay?
OPTIONS:    (a) route the existing per-unit and per-source refusals through `escalation.Refused`
            so the chain has one spelling
            (b) delete it and accept that each subsystem declares its own refusal type
RECOMMEND:  (a) — Hard Rule -1's chain is the thing this project built after 145 chapters were
            written with nothing failing, and two of its six rungs currently have a name in a
            file and no expression in code. Note what (b) costs: deleting it leaves the middle
            two rungs with no shared exception type at all, so the next refusal invents a third
            private one and the chain drifts further apart. This is your doctrine call, not a
            maintenance edit.
COST IF WRONG: (a) is refactoring across prose_gate and threads for a property no test currently
            asserts. (b) removes a named safety — inert today, but the name is what a future
            reader would reach for.
UNBLOCKS:   none
THEME:      escalation chain

---

### 58cfc2b6dbc4  [OWNER] [MAJOR] — Re-check the halt beside the write, not only at entry
STILL LIVE: yes, and verified precisely. `_assert_not_halted` is called at
`src/hostcheck.py:865` (sweep's repair branch), :1126 (`--purge --go`) and :1461 (`adopt --go`) —
all at function entry. `_land_hosts` (:151-224) contains the compare-and-swap that actually
rewrites `WIKI_HOSTS.json` and has NO halt check anywhere in it; the repair branch reaches it at
:1017, after the whole threaded probe. `_land_hosts`'s own docstring says the window is "minutes,
often much longer".
QUESTION:   Does a halt raised while the probe is running have to stop the write, or is the
            entry-time check close enough?
OPTIONS:    (a) accept it — the withdraw_chapters analogy was judged close enough and the race
            is narrow
            (b) re-call `_assert_not_halted()` immediately before the CAS inside `_land_hosts`,
            covering all three write paths at once
RECOMMEND:  (b) — the analogy it was modelled on has a check-to-action window of seconds over
            local file moves; this one is minutes to hours over rate-limited network I/O. Putting
            the check inside `_land_hosts` also covers the third writer the docstring warns about.
COST IF WRONG: (a) means a halt raised mid-sweep does not stop the eventual write to
            `WIKI_HOSTS.json`, one of the two files this project has confirmed it cannot
            reconstruct from anything else on disk. (b) costs one extra read of the halt file per
            landing.
UNBLOCKS:   none
THEME:      halt interlock

---

### db36d589713e  [OWNER] [INFO] — A constant nothing reads, deferred to you by name
STILL LIVE: yes — `FEATS_BLOCK_CHARS = 20000` is still at `src/manifest_builder.py:168` and a
tree-wide grep still finds only that line plus two comments (context_budget.py:20,
manifest_builder.py:360). The live budget still comes from :368-369.
QUESTION:   Keep the constant as documentation of a real measurement, or move the measurement
            paragraph into context_budget.py beside the arithmetic that replaced it and delete it?
OPTIONS:    (a) keep it, add one line saying it is documentation and is read by nothing
            (b) move the paragraph to context_budget.py and delete the constant
RECOMMEND:  (a) — it is the cheapest possible answer and it is the same answer the class ruling
            in 7099a092abd3 would give. The measurement is worth keeping and moving it costs a
            diff in two files for no gain.
COST IF WRONG: none of consequence; at worst a future reader spends a minute establishing that
            the number is inert.
UNBLOCKS:   settled by the same class ruling as 7099a092abd3
THEME:      dead apparatus ruling

---

### 0291835411d9  [OWNER] [MINOR] — tempus.DEGENERATE_TIME, and its prose duplicate
STILL LIVE: yes, but its shape has changed since filing. The table is now at
`src/tempus.py:71-81` and it is no longer referenced NOWHERE — it has exactly one reader,
`src/verify_math.py:722`. That makes it a battery-only symbol, which is precisely the class
7099a092abd3 is about. `loop_report` still restates the Basement Loop and the Rot City in prose
rather than reading them from the table.
QUESTION:   Same class question: keep the table as marked charter apparatus, or retire it?
OPTIONS:    (a) keep and mark, and make `loop_report` read the table so the one fact has one copy
            (b) retire the table and its verify_math row
RECOMMEND:  (a) — the four entries are charter cross-references, not code, and the duplication is
            the actual hazard here. The `loop_report` half is mechanical and can go to a code
            rung the moment you rule keep.
COST IF WRONG: retiring loses four charter citations that no other file carries; keeping without
            de-duplicating leaves one fact with two copies that can drift.
UNBLOCKS:   settled by the same class ruling as 7099a092abd3
THEME:      dead apparatus ruling

---

### 0fbaba6e1070  [OWNER] [MINOR] — ANEURISM IV mines to nothing and no bot can fix it
STILL LIVE: yes, and confirmed against today's data. `data/WIKI_HOSTS.json:4` still binds
"ANEURISM IV" to aneurism.fandom.com; `data/BINDING_HEALTH.json` still records the binding
CONFIRMED at score 100 with `present.ok: false`. The cache tells the story: 175 entities under
`data/feats/aneurism_fandom_com`, **161 with no pages at all, 0 feats in total**. Note this order
has been re-filed 66 times — answering it stops a recurring entry on every binding_health run.
QUESTION:   Is ANEURISM IV mined at feature level with no per-entry articles, or do its 175 entry
            names get re-catalogued to the titles that wiki actually uses?
OPTIONS:    (a) accept feature-level mining, record the decision so binding_health stops re-filing
            (b) re-catalogue the 175 entries by hand against the live wiki
RECOMMEND:  (a) — 175 hand re-catalogued names for one small source, on a wiki whose probe says
            even known-present titles return nothing, is not where curatorial hours buy the most.
            Record it so the 67th re-file does not happen.
COST IF WRONG: (a) leaves one source contributing no per-entry evidence for good. (b) is real
            hours against a source that may simply not have per-entity articles.
UNBLOCKS:   none, but wiring `resolve_title` (4f308dbd9d2c) may rescue some of these names for
            free — worth deciding 4f308dbd9d2c first
THEME:      curatorial binding

---

### 47c8def059e3  [OWNER] [MINOR] — Console truncation in cosmology_graph
STILL LIVE: **NO** — the ruling has already been made in code. `src/cosmology_graph.py` now marks
every cut it makes: `_cut()` at :90-104 appends an ellipsis to string fields with a docstring
citing this family of orders; `names[:4]` at :186-187 carries "(+N more shared)"; `c[:6]` at
:198-199 carries "(+N more)"; and both ranked listings print an explicit tail —
":191-193" says "... N further pairs not printed here (of N). Screen framing, not a filter:
--show 0 prints them all, and --write emits every one", with the matching line for clusters at
:202-204. The `pair_w[:16]`/`comps[:8]` slices the order names are now `[:shown]` off an
`--show` argument that accepts 0 for all.
QUESTION:   Nothing to decide. Every cut is marked and reversible, which is the answer the order
            was asking for.
OPTIONS:    (a) close it
RECOMMEND:  (a) — close as already answered by the code.
COST IF WRONG: none.
UNBLOCKS:   none
THEME:      resolved in code

---

## Summary of this batch

**Dead (close without reading further): 2** — 505177847f43 (the foreign process is gone;
measured today), 47c8def059e3 (every console cut is now marked).

**Reroute to RUN/LOCAL, no ruling needed: 5** — 88a5f9192e1b (invalidation cost measured at 1
record), 76ab006d84b8, fa86e8b92150, ecc355769a41, 19c507a16430. Plus the second half of
f9643582fd29 (narrowing the `_deliberately_failing` suppression).

**Duplicate: 1** — 665e3609bc82 folds into 4f308dbd9d2c + 7099a092abd3.

**One class ruling settles five** — answer 7099a092abd3 ("battery-only symbols: keep and mark, or
retire") and 0291835411d9, 665e3609bc82's tail, db36d589713e and the urgency half of 38c51153243c
all fall out of it.

**Genuinely needs you: 12**, in this order of value —
1. ef4ca9edd61f — re-mine or not; 34,850 records, re-measured today
2. f9643582fd29 — the sandbox reaper's contract; the cost of getting it wrong is a 20-hour pass
3. 58cfc2b6dbc4 — halt interlock on the one file that cannot be rebuilt
4. 7099a092abd3 — the class ruling above
5. 4f308dbd9d2c — switch on title resolution or declare it off
6. 6d594a775899 — the `pages_read` schema
7. da15f582b2ea — how the OPERATOR/SUPERVISOR rungs are expressed
8. 13aee150e0dc — whether a guard file may demote an alarm
9. 38c51153243c — the Ruin column's shape
10. 0fbaba6e1070 — ANEURISM IV, curatorial
11. db36d589713e / 0291835411d9 — one line each, once the class ruling is made
