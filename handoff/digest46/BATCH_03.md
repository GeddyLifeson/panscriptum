# OWNER DECISION DIGEST — BATCH 03

21 open OWNER/SESSION orders, each re-verified against the live tree on 2026-09-07.
**6 are dead and need no ruling. 4 more are mechanical and should leave the OWNER/SESSION rung.
11 are real decisions.**

Verification was read-only. No file in `src/` was touched; `drill.py`, `mutate.py`, `allsweep.py`
and `publish.py` were not run. Live measurements used: `netstat -ano`, `nvidia-smi`,
`Get-CimInstance Win32_Process`, one 8-second GET to `/api/tags`, `state/drill_last.json`,
`data/*.json`, and a read-only open of `state/corpus.db`.

---

### f6c52ef7657f  [OWNER] [MAJOR]  — Foreign semsearch daemon exhausts the machine's ephemeral ports
STILL LIVE: **NO** — the leaker is gone and the host is clean. `Get-CimInstance Win32_Process` finds
no process whose command line contains `semsearch` anywhere on this machine; PID 25716 no longer
exists. `netstat -ano` right now: **311 TCP rows host-wide, 9 of them on 11434** — versus the 32,467
this order measured. All 9 belong to this project (pipeline.py PID 74144, verify_math.py PID 72088,
read.py PID 59704) plus `ollama.exe serve` PID 42876. `curl http://127.0.0.1:11434/api/tags` returns
**HTTP 200 in 0.005s**. And the order's own best evidence — the monotonic WinError 10055 trend — has
stopped dead: the last 10055 anywhere under `state/` is `state/pipeline.log:15701`,
`[2026-08-31 13:45:03]`. Seven days with zero occurrences. Per-day counts confirm the break:
41 / 183 / 245 / 370 / 676 / 636 / 462 across 08-23 to 08-31, then nothing.
QUESTION:   none — the person-action this order asked for has happened.
OPTIONS:    (a) close it  (b) keep it open as a watch item.
RECOMMEND:  **(a)** — close. The remedy was "a person stops PID 25716" and PID 25716 is stopped;
            an order whose whole content is a machine condition that has ended is furniture.
COST IF WRONG: if semsearch is restarted the condition returns, but it will be re-measured and
            re-filed automatically — this order's own history shows it was filed three times.
UNBLOCKS:   28f79d511879, d2583f4c8b36 (same measurement closes all three)
THEME:      foreign process

---

### 74f1bc47da2a  [SESSION] [MAJOR]  — Battery rows still redden on live network, not on this code
STILL LIVE: **yes** — all three limbs verified in the current file. `verify_math.py:7464` still runs
the live `__import__("standards").check(__import__("dashboard").state())` and asserts
`_declared_b1 - _emitted_b1 - _KNOWN_CONDITIONAL_STANDARDS_B1 == []` with the exemption set at
`:7438-7440` still holding **exactly one** name. `verify_math.py:7968` and `:7975` still call
`_STx_b3.check(_state_b3)` twice and diff the two name-sets at `:7996`, and the note at `:7993-7994`
still asserts the immunity the order says it lacks. `standards.py:1901` is still a bare
`if flow is not None:` with no `else` and no `_dropped.append` — its enclosing `except` at `:1919`
only covers the raise, so a `None` flow deletes "the local model produces tokens" silently.
`standards.py` now carries 27 `_dropped.append` sites.
QUESTION:   should a standard that could not be measured because of the machine or network ABSTAIN
            out loud, or keep reddening the battery as if this library were at fault?
OPTIONS:    (a) name the network/machine-tier drop paths and report them as an abstention banner,
            using the existing `_third_party_vm` pattern at `verify_math.py:390`; (b) close the
            `standards.py:1901` gate the way `_UNCONDITIONAL_NAMES_B3` closed its two, so an
            unrunnable probe BREACHES with an UNMEASURED reading instead of vanishing; (c) both.
RECOMMEND:  **(c)** — they fix opposite halves and neither is sufficient alone. (b) is the strictly
            better shape and the file already argues for it in its own comment at `:7887-7892`
            ("There is nothing left to drop"); (a) is what stops the residual drop paths from
            costing another 119-mutant run its gate.
COST IF WRONG: an abstention banner that is too broad turns a standard that genuinely stopped
            firing into an invisible one — the run #25 shape. Do NOT widen
            `_KNOWN_CONDITIONAL_STANDARDS_B1` by name; that is the failure this order forbids.
UNBLOCKS:   none in this batch (sibling of 23dbbcd656f3)
THEME:      live-state gates

---

### b57e23204f66  [OWNER] [MAJOR]  — What rho() returns when the axis matrix is unreadable
STILL LIVE: **NO** — the contradiction is gone; the docstring was rewritten to record the ruling.
`axis_correlation.py:295-326` now separates the two cases explicitly: the measured-mean promise is
scoped to "an UNMEASURED PAIR inside an otherwise-present matrix", and the missing-matrix branch is
ruled on in the file itself — *"changing the fallback VALUE would be re-opening c00cab9d0412's
ruling, not fixing a bug, so it stays as assay.py chose it."* The executable line is
`axis_correlation.py:328-330`, `if not doc: _no_matrix("rho-no-matrix"); return 0.0 if default is
None else default`. The order offered two exits — "rule that 0.0 stands and fix the docstring" or
"name a value" — and the first has been taken.
QUESTION:   none. Both halves the order named (the value, and the silence) are settled.
OPTIONS:    (a) close it.
RECOMMEND:  **(a)** — close, and note that `verify_math.py:6452` pins 0.0, so the ruling is now
            enforced rather than merely written down.
COST IF WRONG: none; if the owner still wants a non-zero fallback that is a new order against
            c00cab9d0412, not this one.
UNBLOCKS:   none
THEME:      already ruled

---

### 01695fe3ef26  [OWNER] [MINOR]  — Keep scale_theories' four priced codifications, or delete the module
STILL LIVE: **yes**, and it is now measurable. `grep -rn scale_theories src/` finds no importer —
the only five hits are comments in `descending_ladder.py:60`, `drill.py:82-83`, `liveness.py:269-271`
and `tempus.py:46`. A live `liveness.scan()` right now returns **45 findings total, 5 of them this
module**: four dead functions (`:109 bulk_export_beta`, `:126 growth_strike`,
`:139 penetration_pressure`, `:150 surviving_theory`) plus one `dead_module` row. The five constants
at `:23-27` are still read nowhere. One sub-issue IS fixed: `surviving_theory` no longer selects on
an English prose prefix (order e7dc70db782b, `:150-165`), so the "reword the sentence and no theory
survives" hazard is dead.
QUESTION:   is `THEORIES` — four priced codifications with their falsifiers — authored content worth
            keeping, or scaffolding that should go?
OPTIONS:    (a) delete the module; (b) keep `THEORIES`, drop the five unread constants, and wire
            `surviving_theory()` into whatever prices Transgression; (c) keep everything and
            suppress the liveness rows.
RECOMMEND:  **(b)** — the constants have a settled precedent working against them and the content
            does not. `chord_field.py:35-44` and `tempus.py:44-46` both deleted exactly this kind of
            duplicate constant, and `verify_math.py:9182` now asserts tempus stays clean; a fifth
            restatement of `c`, `G`, `hbar` beside `descending_ladder.py`'s live copies is the same
            defect. The four falsifiable theories are authored prose that nothing else holds.
COST IF WRONG: choosing (a) loses four authored codifications with no copy elsewhere. Choosing (c)
            keeps 5 of the project's 45 liveness findings alive permanently.
UNBLOCKS:   **6c479972e838** — deleting or wiring this module drops liveness from 45 to 40, which
            may give the receiver-aware `used` set enough room to land without moving the ratchet
            at all, dissolving that order's whole pairing constraint.
THEME:      dead module

---

### c9e6e50e792f  [OWNER] [MINOR]  — assay_dof lists nine parents while its own prose says ten
STILL LIVE: **yes**, counted directly today. `derivation.py:266-271` holds exactly nine parent names
under prose reading "ten survive the test"; `derivation.py:272-274` (`college_size`) says "one Custos
per degree of freedom", note "the count is derived, not chosen"; `custodes.py` still declares exactly
ten `dof=` labels (`:104, :114, :124, :134, :143, :165, :175, :199, :209, :223`), the unmatched one
being `applicability` at `:143`; and `applicability_mark` still sits at `derivation.py:324-326`,
outside the parents list.
QUESTION:   is applicability a tenth independent lever in the assay, or a gate that decides whether
            an axis counts at all and therefore sits outside the count?
OPTIONS:    (a) add `applicability_mark` to `assay_dof`'s parents — the count becomes ten and the
            prose is already right; (b) change "ten" to "nine" in both `assay_dof` and
            `college_size` and add a sentence on why Cassia's seat is not one of the nine levers.
RECOMMEND:  **(a)** — (b) does not close. `college_size` derives the College's size FROM `assay_dof`,
            so nine levers derive a nine-member College while `custodes.py` seats ten, and
            `custos_dasein` at `:275-279` explicitly says the structure derives "why exactly ten".
            (b) would require rewriting three ledger entries and would still leave Cassia's seat
            underived. (a) is one name and makes the graph agree with the code. `applicability_mark`
            does not depend on `assay_dof`, so this introduces no cycle — `check_graph()` will pass.
COST IF WRONG: picking (b) leaves the "derived, not chosen" claim false by one seat, which is the
            claim the whole College section rests on.
UNBLOCKS:   none
THEME:      ledger arithmetic

---

### 28f79d511879  [OWNER] [MAJOR]  — The machine has run out of TCP ports (the 40x magnitude filing)
STILL LIVE: **NO** — same measurement that killed its parent. The order's headline reading was
31,867 host sockets with 31,791 on 11434 and `curl` returning HTTP 000; today it is **311 host rows,
9 on 11434, HTTP 200 in 0.005s**. No `semsearch` process exists. Every downstream symptom the order
named is also gone: `allsweep` is not grading OLLAMA UNREACHABLE, `llama-server.exe` (PID 32776) is
resident at 8,014 MB serving `-c 12288` — the configured context — and the last WinError 10055 in
any log is `[2026-08-31 13:45:03]`.
QUESTION:   none.
OPTIONS:    (a) close it as its parent's magnitude record.
RECOMMEND:  **(a)** — close. Its stated purpose was to preserve a magnitude reading separate from
            f6c52ef7657f's; that reading is preserved in the closed record.
COST IF WRONG: none.
UNBLOCKS:   settled together with f6c52ef7657f and d2583f4c8b36
THEME:      foreign process

---

### 19791681f257  [SESSION] [MAJOR]  — Survivor rows alias one red-gate list that is rewritten mid-run
STILL LIVE: **yes** — line numbers moved but the aliasing is intact. `mutate.py:1908` builds
`red_at_baseline`; `mutate.py:2044` still does the in-place `red_at_baseline[:] = [...]`;
`mutate.py:2148` (journal) and `mutate.py:2153` (`survivors.append`) both store the object itself,
not a copy; `mutate.py:2167` puts the same object in the result dict, and `file_orders` reads it at
`:2229` and `:2250` at the end of the run.
QUESTION:   **none — reroute to RUN/LOCAL, no ruling needed.**
OPTIONS:    the order names the fix, the reason it is safe, and what must NOT change: wrap the two
            row-level stores in `list(...)` and leave `:2044`'s in-place update alone.
RECOMMEND:  reroute. There is no judgment here — the JSONL journal already holds the correct
            per-survivor snapshot, so the fix has a verified oracle to be checked against.
COST IF WRONG: none from rerouting. Note for whoever takes it: a 20-hour mutation pass is running
            now and takes its baseline from the live tree, so this must land *after* it finishes.
UNBLOCKS:   none
THEME:      reroute / aliasing

---

### 95f80c0ea860  [SESSION] [MAJOR]  — tiers report denies the hyperverse it publishes on the next page
STILL LIVE: **yes** — `tiers.py:374` still prints `hyperverse: DECLINED for all {len(srcs)} shelves`
while `:315-317` fills `hyperverse` / `hyperverse_type` / `hyperverse_contested_by` from
`xenoverse_grounding()`, and `:447` still prints a concrete `H{c['hyperverse']}` in the sample-stacks
block. The stale docstring survives at `:3`, `:38` and `:66-96`.
QUESTION:   **none — reroute to RUN/LOCAL, no ruling needed.** The curatorial call the order asks for
            has already been made in the source: `tiers.py:153` states flatly *"The hyperverse
            therefore comes from grounding.py and from nowhere else."*
OPTIONS:    with that settled, the work is mechanical — replace `:374` with the real counts and
            rewrite the docstring so it says the LINK-GRAPH hyperverse is declined by cause while
            the published H comes from grounding.
RECOMMEND:  reroute. Give the handler the measured split from the order's own evidence
            (170 of 208 shelves carry a grounding-derived hyperverse, 38 carry none) and have it
            re-count from `data/TIERS.json` rather than pasting those figures.
COST IF WRONG: none from rerouting; leaving it open costs an operator who reads "DECLINED for all
            208" and then an H number thirty-nine lines later.
THEME:      reroute / stale report

---

### c2bbe43e0f2d  [SESSION] [MAJOR]  — A source with zero slug candidates gets a clean "no wiki" negative
STILL LIVE: **yes**, and reproduced against live data today. `feats.py:730-733` still writes
`known[src] = None` in the `else` branch when `undetermined` is empty — which includes the case where
`_slugs(src)` returned nothing at all and the loop body never ran. `feats.py:639` still requires
`len(c) > 2`. Re-running the slug rule over all 215 sources in `data/SWEEP_ROLL.json` yields exactly
one empty-candidate source, **DC**, exactly as filed; it is still saved only by
`data/WIKI_HOSTS.json` holding `DC -> dc.fandom.com` from the netloc branch at `:692-697`.
`WIKI_HOSTS.json` currently carries 4 hard nulls (JMBrew, Kobold Press, aurora_mods, the Weaveshaper
Ateliers) — all four DO produce slug candidates, so none of them came through this path.
QUESTION:   **none — reroute to RUN/LOCAL, no ruling needed.** The order gives the primary remedy
            unambiguously and it is additive.
OPTIONS:    primary: treat "no candidate could be generated" as a third case — put it in
            `unprobed[src]`, `known.pop(src, None)`, so it prints in PROBE UNDETERMINED and is
            re-asked next run. Secondary and optional: lower the `len(c) > 2` floor.
RECOMMEND:  reroute with the primary remedy only. Lowering the floor changes probe volume for all
            215 sources to fix one; the third-case fix costs nothing and is the same shape the
            transport-failure branch already uses.
COST IF WRONG: none from rerouting. Left as is, the next short-named source with no stored
            `wiki_page` is silently dropped from the universe by `feats.py:1605-1607`.
THEME:      reroute / unprobed negative

---

### d2583f4c8b36  [OWNER] [MAJOR]  — The local rung was unworkable because a game held the GPU
STILL LIVE: **NO** — the card is free and the rung answers. `Get-Process Overwatch` returns nothing;
`nvidia-smi --query-compute-apps` lists no game among the compute clients. GPU is at
**8,407 MiB of 10,240 used with 1,647 free**, and that 8.4 GB is this project's own
`llama-server.exe` (PID 32776) holding the model resident at `-c 12288`. `/api/tags` answers HTTP 200
in 0.005s against the order's 300s and 90s no-answers. The order's own closing line said no code
change was implied and the remedy was to stop somebody's game; that has happened.
QUESTION:   the order left one forward-looking ask that is NOT a machine condition: *"nothing in the
            battery distinguishes 'the local model is unavailable' from 'the local model had nothing
            to do', and those are opposite facts about the cheapest rung."*
OPTIONS:    (a) close outright; (b) close the machine condition and refile the missing detector as a
            RUN order against `standards.py`.
RECOMMEND:  **(b)** — the outage is over, but the detector gap is real and is the same blind spot
            74f1bc47da2a is about from the other side. Refiling it costs the owner nothing and keeps
            a good idea from being closed along with a dead incident.
COST IF WRONG: choosing (a) loses the detector idea; nothing breaks.
UNBLOCKS:   settled together with f6c52ef7657f and 28f79d511879
THEME:      foreign process

---

### b186bc4dad8f  [OWNER] [MAJOR]  — category, topic and subroom are three axes; what about the unrestored rows
STILL LIVE: **yes, but narrowed to one question.** The warning half has landed in code where the next
agent will hit it: `pipeline.py:130-142` now spells out all three axes and closes with
*"Do not re-derive this: they are three axes."* `subroom` is implemented and enforced —
`pipeline.py:151` `SUBROOMS`, `:169` `subroom_ok()`, `:162` `subroom_rejected`. `threads.py:241-247`
carries the 2026-08-31 split ruling. The classifier schema at `pipeline.py:1713-1721` still requires
`category` AND `topic` separately, which is the test the order names. `category` coverage confirmed
today at **282,822 of 282,822** rows in `state/corpus.db`.
What is NOT settled: 7,909 topics were rewritten, 5,418 were still identifiable, **5,293 were
restored — so roughly 2,616 entities' topics were rewritten and never put back.**
QUESTION:   accept the ~2,616 unrestored topic rewrites as-is, or re-classify those entities?
OPTIONS:    (a) accept — they will be re-topiced on the next classifier pass over those rows anyway;
            (b) identify and force a re-classify of the affected rows now; (c) accept, and add one
            executable regression net so a future run cannot repeat the rewrite.
RECOMMEND:  **(c)** — (a) and (b) differ only in when, but neither stops it happening again, and
            right now the only thing standing between this project and a repeat is a comment. The
            order says the follow-on step would have CLEARED 126,136 topics; a comment is thin cover
            for that.
COST IF WRONG: accepting without a net means the next agent that measures the 87% overlap draws the
            same conclusion and this time may not be caught before the follow-on step.
UNBLOCKS:   none
THEME:      axis ruling

---

### 3d2d9b87cc10  [OWNER] [MINOR]  — Should FOR_OWNER.md be published, or withdrawn from the export
STILL LIVE: **yes** — verified in source. `publish.py:152-160` lists COPY_FILES and `FOR_OWNER.md` is
not among the eleven names. `publish.py:1114` is still `for f in COPY_FILES`, so the withdrawal loop
can only reach names the tuple still holds. `prune_export`'s docstring at `publish.py:911` still puts
root files out of scope: *"the root marker files are ours"*. So nothing refreshes it and nothing can
withdraw it. (The export repo itself was not inspected — this run is barred from it — so the
"tracked in the export root" half rests on the order's own `git ls-files` record.)
QUESTION:   is `FOR_OWNER.md` meant to be a public document?
OPTIONS:    (a) yes — add it to `COPY_FILES` so it is refreshed each cycle and withdrawable like
            every other ledger; (b) no — give `sync_tree` a root-file sweep mirroring
            `prune_export`'s new withdrawn-root sweep, and let it take `FOR_OWNER.md` with it.
RECOMMEND:  **(b) as the code change, whichever way the owner rules on the document.** The two are
            separable and the owner should not have to trade them: the root-file sweep closes the
            unreachable-withdrawal hole permanently for every future root file, and if the answer to
            the document question is "yes, publish it" then adding it to `COPY_FILES` on top is one
            more line. Doing only (a) fixes one file and leaves the hole.
COST IF WRONG: (a) alone publishes a refreshed owner-facing document and leaves the next withdrawn
            root file frozen in the public repo forever. (b) alone un-publishes a document the owner
            may have wanted public — recoverable in one cycle.
UNBLOCKS:   none (sibling f2271d9ee843 already closed for directories)
THEME:      export hygiene

---

### 91cf746c651e  [OWNER] [INFO]  — Does secondopinion's "escalates to JANITOR" name a call or a severity
STILL LIVE: **yes** — unchanged. `grep escalation src/secondopinion.py` still returns no import and
no call; the only hits for JANITOR are the docstring sentence at `secondopinion.py:71`. The recording
is still `silence.note` only.
QUESTION:   the order gives two readings; committing to one — **reading (a) is right, and the fix is
            to the sentence, not to the code.**
OPTIONS:    (a) reword to something like "it is a JANITOR-level matter — recorded via silence.note,
            never a halt", which says the same thing without naming a call on the chain;
            (b) add an `escalation.escalate(JANITOR, ...)` call on the missing-tool path.
RECOMMEND:  **(a)** — what tips it is the paragraph the sentence lives in. `secondopinion.py:62-71`
            is an argument about SEVERITY: the module is fail-open because "halting the park because
            an optional second opinion is unavailable would make a safety indistinguishable from a
            fault". Adding an escalate() call would import the very chain that paragraph is
            explaining why not to trigger. The absence is already loud — `run()` returns
            `NOT INSTALLED` and `report()` prints it as loudly as a failure, which is the module's
            stated design.
COST IF WRONG: if the owner picks (b), an absent second opinion becomes a chain event on every
            fresh checkout that lacks ruff or detect-secrets — noise on the rung that is supposed to
            be signal.
UNBLOCKS:   none
THEME:      doc vs behaviour

---

### 464cc4e12fbc  [OWNER] [INFO]  — Dead entries in overwatch's _STATE_RANK, or legacy compatibility
STILL LIVE: **yes, and the live ledger answers it.** `overwatch.py:303` is unchanged, and the module
still writes only three states — `:663` `f["state"] = "closed"`, `:872` `= "retired"`, `:919`
`"state": "open"`. The order named two dead entries; there are in fact **three**, because `refuted`
is only ever written to `f["verdict"]` at `:664`, never to `f["state"]`.
But `data/OVERWATCH.json` right now holds 1,404 findings with these states:
**closed 726, retired 670, refuted 5, open 2, stale 1.** So `refuted` and `stale` are live values in
the ledger this table ranks, written by something other than the current code — exactly the
"hand-edited or externally-written entry" case the order raised as the second reading.
QUESTION:   drop the unreachable ranks, or keep them for ledger entries that already carry them?
OPTIONS:    (a) drop the dead entries; (b) keep them and document that they exist for ledger rows
            this module no longer writes.
RECOMMEND:  **(b)**, on the measurement rather than on taste — 6 of the 1,404 rows on disk carry
            `refuted` or `stale`, and dropping their ranks makes `_progress()` score them 0 (the same
            as `open`), so a stale writer's copy could overwrite a terminal verdict. Only
            `confirmed` is genuinely unreachable; document all three and say which is which.
COST IF WRONG: dropping them is a silent regression in `_merge_ledgers`' "further along wins" rule
            for six existing findings — the exact failure the comment above the table warns about.
UNBLOCKS:   none
THEME:      dead guard

---

### 14a73de63099  [SESSION] [INFO]  — "8 known-present titles" reads as the whole catalogue
STILL LIVE: **yes** — `binding_health.py:974-975` still returns the moment `len(out) >= want` and
reports no total; `PRESENT_CANDIDATES` is still 8 at `:64`; the failure detail at `:610-611` still
reads `"%d known-present title(s) all returned nothing..."` with no denominator.
QUESTION:   the order gives two readings, but they do not actually conflict — **commit to the remedy
            it already names, which satisfies both at zero network cost.**
OPTIONS:    (a) have `known_present_titles` also report how many candidates were available (a cheap
            count over the same scan it already walks, no extra fetch) and have `_probe_present` and
            `--titles` say "8 of N"; (b) leave it, on Reading A.
RECOMMEND:  **(a) — and this is the highest-leverage item in the batch, because it is not cosmetic.**
            What tips it: `data/BINDING_HEALTH.json` shows the eight titles actually tried for
            eberron.fandom.com were *Alchemical Savant, Arcane Firearm, Chemical Mastery, Eldritch
            Cannon, Experimental Elixir, Explosive Cannon, Flamethrower, Force Ballista* — eight
            artificer rules features, taken alphabetically off the front of a **212-entry**
            catalogue, none of which any wiki has an article for. The same shape hit
            warthunder.fandom.com, whose eight were real-world admirals. The bound is not just
            under-reported, it is systematically sampling the wrong end of the catalogue and
            manufacturing false CONFIRMED bindings. Add the "of N" AND spread the candidate pick.
COST IF WRONG: leaving it costs one permanently open OWNER order per affected host, each of which is
            unanswerable because the evidence in it is an artefact.
UNBLOCKS:   **aecffd7eea57** directly, and very likely the warthunder and aneurism siblings outside
            this batch.
THEME:      probe bound

---

### 6c479972e838  [OWNER] [MINOR]  — Receiver-aware dead-code detection needs the ratchet moved with it
STILL LIVE: **yes, and materially easier than when filed.** `drill.py:125` has
`LIVENESS_CEILING = 52`. `state/drill_last.json`, stamped today at 2026-09-07 19:07, reads
**liveness 45, ceiling 52, 443 nets, zero breached** — so headroom is now **7**, not the 4 the order's
correction recorded and not the 0 the original text claimed. The pairing constraint itself is
unchanged: `drill.py:7466` returns `n <= LIVENESS_CEILING` over the sum of every `scan()` list, so a
sharper `used` set raises `n` and the two files must move together.
QUESTION:   authorise a paired change — a receiver-aware `used` set in `liveness.py` plus whatever
            `LIVENESS_CEILING` revision it forces — or leave the false-negative surface standing?
OPTIONS:    (a) authorise the pair, with the raise written out in `drill.py`'s own format alongside
            the two lawful raises already on record; (b) require it to land inside the existing
            7 points of headroom, with no ceiling move at all; (c) decline.
RECOMMEND:  **(b) first, (a) only if (b) fails** — and settle 01695fe3ef26 before either. Five of
            today's 45 findings are `scale_theories`; if that module is dealt with, liveness drops
            to 40 and the sharper detector has 12 points to land in. A raise that turns out to have
            been unnecessary is exactly the rubber stamp `drill.py:43-48` warns about.
COST IF WRONG: authorising a raise without first taking the free 5 makes the ratchet look
            negotiable, which is the one thing this layer exists to prevent.
UNBLOCKS:   none — but 01695fe3ef26 unblocks this
THEME:      ratchet pairing

---

### 28c1f58f5e8a  [OWNER] [MAJOR]  — Six run35 proposal files with 59 checks were never adopted
STILL LIVE: **yes**, re-counted today. `verify_math.py:9399` still globs
`handoff/run35/checks_L*.py` and `:9401` still asserts `len(_run35_files) == 6`. `handoff/run35/`
holds all twelve `checks_*` files; `checks_batch1..6` are spliced and `checks_L1..L6` are exec'd,
while `checks_F1.py` (13 `def check_`), `checks_M1.py` (6), `checks_M2.py` (16), `checks_M3.py` (9),
`checks_M4.py` (7) and `checks_SO.py` (8) — **59 functions** — are reached by nothing. The only
reference anywhere in `src/` is `drill.py:13383`, which uses `handoff/run35/checks_F1.py` as a path
string in an unrelated agent-scratch test.
QUESTION:   for each of the six files: adopt it, execute it via a widened glob, or record on the
            file why it is not wanted?
OPTIONS:    (a) widen the glob to `checks_*.py` and let all twelve run, fixing whatever goes red;
            (b) triage the six by hand, adopting some and writing a refusal note on the rest;
            (c) delete them.
RECOMMEND:  **(b), but with (a) as the first move to find out what you are triaging** — run the six
            once against the current tree and let the pass/fail split do most of the sorting. The
            order's own strongest evidence is that of the 67 order ids these files cover, 11 appear
            in `src/` and every one of those 11 is in the TARGET module, not in `verify_math.py`:
            the fixes landed and the checks that would notice a regression did not. That is 56 fixes
            with no guard, which is why this is MAJOR rather than housekeeping.
COST IF WRONG: (c) discards 59 authored checks. (a) alone risks pinning behaviour nobody re-examined
            — some of these were written against a tree that has moved.
UNBLOCKS:   none
THEME:      unadopted checks

---

### aecffd7eea57  [OWNER] [MINOR]  — eberron.fandom.com is correctly bound but no catalogued title resolved
STILL LIVE: **yes as an open order — but its premise is an artefact, and that changes the answer.**
The order asks the owner to choose between "accept this source is mined at feature level and carries
no per-entry articles" and "re-catalogue its entries". Both assume the wiki holds nothing.
It does. `data/BINDING_HEALTH.json` (the file the sweep reads, last written 2026-08-27) shows the
eight titles tried were all artificer rules features — *Alchemical Savant, Arcane Firearm, Chemical
Mastery, Eldritch Cannon, Experimental Elixir, Explosive Cannon, Flamethrower, Force Ballista* —
the alphabetical front of a **212-entry** catalogue. Meanwhile `data/HOST_FITNESS.json` records
eberron.fandom.com at **probed 15, hits 15, rate 1.0, about 1.0, verdict "holds"**, with examples
*Arawai, Aureon, Balinor, Boldrei, Dol Arrah* — Eberron deities, which the wiki plainly does have
articles for. The wiki serves this source's entries; the probe just never asked for one.
QUESTION:   given that, do you still need to rule — or does this close once the probe samples
            properly?
OPTIONS:    (a) hold it pending 14a73de63099's fix and a fresh `binding_health` run, then close it if
            the host goes healthy; (b) rule now on feature-level vs re-catalogue.
RECOMMEND:  **(a)** — do not rule. Both options in (b) are answers to a question the data says is
            false, and either would do real damage: accepting "no per-entry articles" would stop
            mining a wiki that answers 15 of 15. Note also that the close path in
            `workorders.py:1186-1191` requires `healthy is True` in `BINDING_HEALTH.json`, and that
            file is 11 days old — this order cannot close until `binding_health` runs again
            regardless of what the owner decides.
COST IF WRONG: ruling (b) "accept feature-level" removes a productive wiki from per-entry mining on
            the strength of eight badly-chosen probes.
UNBLOCKS:   none — but 14a73de63099 unblocks this
THEME:      binding artefact

---

### 1b7f14efce8e  [OWNER] [MAJOR]  — prime.fandom.com is bound to a source it has nothing to do with
STILL LIVE: **yes, and unlike its sibling above this one is real.** `data/WIKI_HOSTS.json` still maps
`Prime World Equipment -> prime.fandom.com`. `data/BINDING_HEALTH.json` records the sitename probe as
**"Prime Hydration Wiki", score 50.0, verdict MISBOUND** — an energy-drink brand wiki. The eight
catalogued titles tried were *Angler's Armour, Argentum, Aurum, Bath Potion, Bloody Marilith,
Celestial Sunrise, Chain Devil Gauntlets, Djinn and Tonic* — a 19-entry set of drink-themed fantasy
magic items (Marilith, Chain Devil and Djinn are all D&D). No sampling fix rescues this: the host is
simply the wrong wiki. `data/HOST_FITNESS.json` has no entry for this source at all.
QUESTION:   unbind the source, or find and bind the right host?
OPTIONS:    (a) unbind — remove the `prime.fandom.com` mapping, so the source is mined from its own
            catalogue and no wiki is consulted; (b) rebind to a correct host, if one exists;
            (c) leave it.
RECOMMEND:  **(a)** — unbind. The entry names read as a homebrew supplement, which is unlikely to
            have a wiki at all; searching for one is speculative work against 19 entries. Unbinding
            costs nothing (`feats.py:1605-1607` drops entities of a hostless source from the roll,
            which is the correct outcome for a source with no wiki) and removes the standing risk
            that mining attributes beverage-brand content to a fantasy source.
COST IF WRONG: (c) is the expensive option — 66 sightings so far and it will re-file every sweep.
            Leaving a MISBOUND host mapped is how the wrong fiction gets mined and attested.
UNBLOCKS:   none
THEME:      misbound host

---

### ef8940b363b3  [OWNER] [MINOR]  — Codex section substring fallback is not most-specific-wins
STILL LIVE: **NO** — replaced by something stronger than the fix the order asked for.
`catalogue_codex.py:236-241` no longer picks a winner at all: it collects every candidate
(`cands = sorted({t for k, t in sec_by_norm.items() if n in k or k in n})`), binds only when
`len(cands) == 1`, and on more than one appends to `ambiguous` — which `:339-345` prints uncapped as
AMBIGUOUS SECTION BINDING and which is *"bound to nothing on purpose"* (`:206`). The first-hit
`break` in codex-file order that this order was filed against is gone (order 5da00dda2c8e), and an
exact match short-circuits above it at `:220-221`. "Most-specific-wins" is moot because nothing wins
on a tie any more; it refuses instead.
QUESTION:   none.
OPTIONS:    (a) close it.
RECOMMEND:  **(a)** — close. The shape the order named as the finding no longer exists in the file.
COST IF WRONG: none.
UNBLOCKS:   none
THEME:      already fixed

---

### 18f7673b77ce  [OWNER] [MINOR]  — clean_ceiling's prefix match picks the shortest with no ambiguity check
STILL LIVE: **NO** — fixed, with the old behaviour written out as the thing it replaced.
`cleanup.py:255-262` now reads `if len(low_pref) == 1: return low_pref[0], "prefix"` followed by
`if low_pref: return ce, "prefix-ambiguous"`. The comment at `:238-248` names exactly the defect this
order describes — the guard was `len(low_pref) >= 1` then `min(low_pref, key=len)`, so the shortest
won on no evidence — and records it as removed under order ed6e66c0c12d. Several matches now resolve
to nothing and get their own reported reason.
QUESTION:   none.
OPTIONS:    (a) close it.
RECOMMEND:  **(a)** — close. Note for the owner: the comment at `:230-248` is a description of the
            *former* behaviour, not evidence the fault is live; the executable lines at `:255-262`
            are the current rule.
COST IF WRONG: none.
UNBLOCKS:   none
THEME:      already fixed

---

## Batch summary

| | count | ids |
|---|---|---|
| Dead — close, no ruling | **6** | f6c52ef7657f, 28f79d511879, d2583f4c8b36, b57e23204f66, ef8940b363b3, 18f7673b77ce |
| Reroute to RUN/LOCAL | **4** | 19791681f257, 95f80c0ea860, c2bbe43e0f2d, 14a73de63099 |
| Real owner decisions | **11** | 74f1bc47da2a, 01695fe3ef26, c9e6e50e792f, b186bc4dad8f, 3d2d9b87cc10, 91cf746c651e, 464cc4e12fbc, 6c479972e838, 28c1f58f5e8a, aecffd7eea57, 1b7f14efce8e |

**Themes:** foreign process (3, all dead) · already fixed (3, all dead) · reroute (4) ·
binding health (2) · ledger/graph arithmetic (2) · dead code and ratchets (2) ·
live-state gates (1) · export hygiene (1) · unadopted checks (1) · axis ruling (1) · doc vs behaviour (1)

**Three highest-value decisions**

1. **14a73de63099** — the "8 of N" fix. Cheapest item here and the only one that dissolves another
   order outright. The bound is not just under-reported; it samples the alphabetical front of the
   catalogue, which is how eberron (212 entries) came to be judged on eight artificer rules features
   and warthunder on eight real-world admirals. Fixing it plus spreading the candidate pick very
   likely closes aecffd7eea57 and its siblings without a ruling.
2. **28c1f58f5e8a** — 59 authored checks in six files that nothing executes, covering 67 order ids of
   which 56 have a landed fix and no guard. The largest silent coverage gap found in this batch.
3. **01695fe3ef26 → 6c479972e838** — settle scale_theories first. It is 5 of today's 45 liveness
   findings, and taking it may give the receiver-aware detector enough headroom to land without
   touching `LIVENESS_CEILING` at all, which turns a ratchet decision into no decision.

**Two things worth knowing regardless of any ruling**

- The 2026-08/09 Ollama outage is over. No `semsearch` process on the machine, 9 sockets on 11434,
  `/api/tags` at HTTP 200 in 5 ms, GPU free of foreign clients, and zero WinError 10055 anywhere
  under `state/` since 2026-08-31 13:45:03. Three MAJOR orders close on that one measurement.
- `data/BINDING_HEALTH.json` was last written 2026-08-27 and is the only file
  `workorders.py:1186-1191` will close a binding order from. Until `binding_health` runs again, both
  binding orders in this batch re-file every sweep no matter what the owner decides.
