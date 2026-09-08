# OWNER DECISION DIGEST — BATCH 05 (20 open OWNER/SESSION orders)

Verified against the live tree 2026-09-06/07, read-only. Nothing in `src/` was edited, no gate
was run, no order was closed. Line numbers below are the CURRENT executable lines, not the ones
the orders were filed against — several have moved.

**4 come off your desk without a ruling** (3 fixed in source, 1 a duplicate).
**5 more need a re-route, not a decision.**
**11 are genuine rulings.**

---

### 4e7f1e47d0a0  [OWNER] [MAJOR]  — Keeper restarted a job a run had stopped
STILL LIVE: NO — the keeper now asks the stop ledger first. `overnight.py:1409` is
`held, why = _manager_stopped(name, args)` followed by `if held: ... continue`, and the same gate
is on both other start paths (`:611`, `:689`). The ledger behind it is real
(`escalation.py:543 STOPPED = state/STOPPED.json`, `subsystem_stopped()` at `:755` failing closed
on an unreadable file, `resume_subsystem()` demanding a ruling). Four drill nets cover it.
QUESTION:   Nothing left to rule on; the remedy the truncated order asked for was applied.
OPTIONS:    (a) close as fixed-in-source  (b) close, and file the one residual at RUN.
RECOMMEND:  (b) — one gap survives and it is not a ruling: `autostart.py watch()` restarts the
SUPERVISOR itself and never consults `subsystem_stopped` (no such call anywhere in that file), so
a MANAGER stop on `overnight.py` would still be re-asserted. That is a one-line code fix, not a
decision about the chain of command.
COST IF WRONG: Nothing — the incident class this order was filed for cannot recur through the
keeper path; only the supervisor-level path is uncovered, and it has never fired.
UNBLOCKS:   4c1eaa9df7fa (cited in the same fix)
THEME:      escalation enforcement

---

### 71ae3fa7e55e  [OWNER] [MAJOR]  — Should a breach read mid-edit halt the library
STILL LIVE: YES — `drill.py main()` at `:13605-13648` reads: if a mutation run is active it
prints and returns 1 without halting; otherwise it goes straight to
`ESC.escalate(ESC.OWNER, "DRILL_BREACH", ...)` on the FIRST read. There is no re-read, no
`quiet_seconds` consultation, no naming of an unsettled tree in the breach line.
QUESTION:   When a net breaches, may the drill read that one net a second time on a settled tree
before it halts the library?
OPTIONS:    (a) leave it — one read, halt immediately  (b) re-read ONLY the breached net(s), and
halt if the breach reproduces; if `codewatch.quiet_seconds()` is still under `STABLE_SECONDS`
(180), halt anyway but name the unsettled condition in the breach sentence  (c) suppress the halt
while `state/MAINTENANCE_RUN.json` is live.
RECOMMEND:  **(b)** — a breach that reproduces on a settled tree is strictly stronger evidence
than one read, so (b) loses no true breach while removing the entire false-red class; the exact
mechanism is already established practice here twice over (`drill.py:13606-13620` declines to
halt during a mutation run, and `mutate.py` re-photographs its baseline on a timer and calls a
disagreement a drift event). The evidence is now overwhelming rather than anecdotal: run #45 lost
a halt to it (`publish.py` mtime 51.8s AFTER the halt, `HANDOFF.md:69`) and run #46 hit three
separate false reds in one shift — `verify_math` 980/1, then 979/2, then a `SCAN_MODULES`
mismatch, tracebacks pointing at comment text, all clearing on a quiet tree, two agents hitting it
independently (`HANDOFF.md:57`, `NEXT_STEPS.md:137`).
**Reject (c) explicitly, and it is not a close call:** letting the maintenance guard switch off a
safety makes the guard a way to disarm the drill, which is the 2026-08-25 incident's shape. Signal
that describes; never decides.
COST IF WRONG: Under (a) you keep paying an investigation per false red and, on the run #45
pattern, an unnecessary halt plus a written ruling to lift it — roughly one event per shift at
current agent counts. Under (b) the theoretical cost is a genuinely intermittent breach that fails
to reproduce on the second read; a flapping net is itself a finding and would still print.
UNBLOCKS:   690db2bf4f1d (RUN — `mutate` currently infers "src/ is being edited" from the
maintenance guard's heartbeat instead of `codewatch`'s fingerprint; (b) makes the correct signal
the one both callers use), and it settles the gate half of d8858a26e46e.
THEME:      gate-vs-edit timing

---

### 9a44b1535851  [OWNER] [MAJOR]  — Recovery tool writes records outside the record writer
STILL LIVE: YES — `recover_folder_records.py:216` is still
`if not silence.write_json(path, record, indent=2, ensure_ascii=False):`, not
`pipeline.write_record_catalogue`. The module imports no pipeline writer.
QUESTION:   Should this tool be routed through the sanctioned record writer, given that doing so
changes its merge semantics from replace to merge?
OPTIONS:    (a) route it through `write_record_catalogue` and accept merge semantics  (b) leave it
outside the contract and record the exemption in the two-writer note where a reader will find it
(c) retire the tool if the folder-recovery path is no longer reachable.
RECOMMEND:  (b) — the dangerous half is already blocked in code (`:170` re-reads the live record
and skips any source already holding entries, treating unreadable as populated, and `:216` gates
the roll update on the write actually landing), so what remains is a contract violation with no
live symptom. Routing it to the catalogue writer would swap "replace, but refuse if anything is
there" for "merge", and merge is the wrong verb for a tool whose input is a mechanical folder
transcription rather than research.
COST IF WRONG: Under (b) `data/records` keeps two sanctioned writers on the books, so the next
sweep re-files this; under (a) a recovery pass could merge folder-mechanical rows into a
researched record instead of refusing outright.
UNBLOCKS:   none (the two-writer standing bug is broader than this order)
THEME:      record-writer contract

---

### be9e9f089d62  [OWNER] [INFO]  — Shelfmark omits the star, so names can collide
STILL LIVE: YES — `address_space.py:237` still prints seven tiers and no star, and
`seed_from_card()`'s docstring (`:272-284`) still says nothing about being star-insensitive. The
`shelfmark()` docstring was partly updated (`:229` now names "U, G, the star and P" as the four
drawn fields), so half the documentary remedy is done and the half that matters is not.
QUESTION:   Does the charter's seven-tier notation govern the printed name, or must a printed
shelfmark carry the whole address?
OPTIONS:    (a) confirm seven tiers; fix the two docstrings so nobody re-derives this a fourth
time  (b) add a star tier to the notation and re-address every row in `data/SHELFMARKS.json`.
RECOMMEND:  (a) — Part Two's own worked Shelfmark, quoted in the file at `:98`, has seven tiers
and no star, and the live data is clean (1,016 rows, 1,016 unique addresses, 1,016 unique
shelfmarks). (b) is a re-addressing of the kind the `_LEGACY_HASH_OFFSETS` floor says needs a
ruling precisely because it rewrites published names, and the collision it would prevent is
currently hypothetical.
COST IF WRONG: Under (a), two worlds around different stars in the same galaxy would share a map
seed via `seed_from_card()` while `map_seed(addr)` separates them — a silent behavioural fork
between the two seeding paths that only bites if the galaxy field ever collides.
UNBLOCKS:   789f99f2a65f is the sibling half of the same address-space question, but it is
self-answered (below) and needs no ruling.
THEME:      address notation

---

### 8c354f6c9780  [OWNER] [MINOR]  — Twin watchdog failed open silently at boot
STILL LIVE: NO — the "safe middle" the order asked for is implemented. `autostart.py:71` sets
`TWIN_TRIES = 4`, `:343` retries the process-table read that many times, and `:367` writes
`"FAILED OPEN: could not read the process table after %d tries (%s); starting a watchdog anyway
-- if one was already up, there are now two"` into `autostart.log`. The fault as filed was the
SILENCE, and the silence is gone.
QUESTION:   Nothing actionable; at most, do you want to ratify fail-open as the standing choice?
OPTIONS:    (a) close as fixed-in-source  (b) close, ratifying fail-open in one sentence.
RECOMMEND:  (a) — fail-open is already argued in place at `:193-200` (failing closed leaves the
supervisor unwatched until the next logon because nothing restarts the `.vbs`; moving the check
into the loop creates a mutual-suicide race), and four tries plus a log line is the outcome both
prior audits called the right one.
COST IF WRONG: A boot where the process table is unreadable four times running leaves two
watchdogs — logged, and recoverable by killing one.
UNBLOCKS:   none
THEME:      supervisor safety

---

### 8d8ba5377fb6  [SESSION] [MAJOR]  — Ceiling prompt showed 3 of 33 mined feats
STILL LIVE: NO — fixed under order `0e041fe97852`. `pipeline.py synthesis_prompt` (`:1477`) no
longer slices: feats are sorted richest-first (`key=lambda s: (-len(s), s)`), carried until the
420-char budget is spent, and the line ends
`f" | [{len(flat) - len(shown)} of this entity's {len(flat)} mined feats withheld for prompt
budget, ranked richest-first]"`. The description fallback now goes through `_budgeted(...)`
(`:1464`), which appends `"[cut here; N more characters in the source]"`.
QUESTION:   None — this is Hard Rule 0 satisfied on the executable line.
OPTIONS:    (a) close as fixed-in-source.
RECOMMEND:  (a) — the fix does exactly what the order's REMEDY paragraph asked for, including the
house remainder marker.
COST IF WRONG: None. The residual "should the 420-char budget be derived from `num_ctx` rather
than declared" is a smaller, separate question the new docstring already flags as yours.
UNBLOCKS:   none
THEME:      Hard Rule 0 caps

---

### ca0a93856e2a  [SESSION] [MINOR]  — BUGS.md Open section is majority-resolved entries
STILL LIVE: YES, AND WORSE — re-measured today, whole file, nothing sampled: `## Open` now holds
**134** labelled entries over **2,183** lines of a **5,023**-line file; **75** say RESOLVED in
their own label; **59** are genuinely open. When filed on 2026-08-30 it was 108 / 56 / 52. The rot
grew by 19 entries in seven days, so the one-at-a-time policy is currently losing to accretion.
QUESTION:   Does the "one at a time, hand-verified" rule stand, or may a measured filter do the
bulk and leave only the ambiguous ones for a person?
OPTIONS:    (a) keep it strictly one-at-a-time  (b) move the entries a two-condition filter proves
unambiguous, hand-check the remainder  (c) leave it and add a standing rule that the run which
resolves an entry moves it in the same commit.
RECOMMEND:  **(b) plus (c)** — and the number that decides it: of the 75 RESOLVED-labelled
entries, only **3** carry a PARTIAL / STILL LIVE / NOT FIXED qualifier anywhere in their body
(M79, m142/m143, m137), and M79's is the phrase "PARTIAL-MERGE" in the bug's own title, not a
partial closure. **All six entries the order names as must-not-move — M38, M16, M42, m105, m133,
m134 — are labelled OPEN, not RESOLVED**, so the filter would never touch one of them. The hazard
the order was built around is measurably absent from the set the filter selects: 72 clean movers,
3 to read by hand. (c) is what stops it re-rotting; the `### Resolved this run (paper trail, run
#NN)` subsections show the habit already half-exists.
COST IF WRONG: If the filter is trusted and a partial closure hides in a body phrased some fourth
way, a live fault gets filed as history. Cheap insurance: move in one commit so it reverts whole,
and print the 72 headers for a read-through before the move.
UNBLOCKS:   none directly, but it makes the other 59 open bugs findable, which is the point.
THEME:      ledger hygiene

---

### d8858a26e46e  [OWNER] [MAJOR]  — A module partition does not partition meaning
STILL LIVE: YES — `MAINTENANCE.md:121` still describes the mechanism as
`sweep_plan.py --batches 16` partitioning modules "by line count", with no rule pairing a net with
the module it tests and no rule sequencing the battery after agents report. Worse: the procedural
remedy from run #45/#46 lives at `NEXT_STEPS.md:137`, and `MAINTENANCE.md` itself says
`NEXT_STEPS.md` is "overwritten each run" — so the lesson is recorded in the one file guaranteed
to be erased. That is this project's own "a decision recorded where nobody reads it" failure,
again.
QUESTION:   How should a run partition work so that a check and the thing it checks are one unit?
OPTIONS:    (a) put the nets about module X in the same batch as module X  (b) keep the line-count
partition and stage behaviour changes, merging them serially, with the battery run only after all
agents report  (c) do nothing structural and rely on (b)'s sequencing rule alone.
RECOMMEND:  **(b), written into `MAINTENANCE.md` rather than `NEXT_STEPS.md`** — (a) fights the
line-count balancing that makes 16 batches finish together, and coupling is not always
one-net-to-one-module, whereas sequencing the battery after the agents report costs one wait and
removes the entire class. Wherever you land, the load-bearing half of this ruling is *which file
it is written in*: a rule that lives only in the overwritten queue is not a rule.
COST IF WRONG: Under (c) you keep paying run #36's 32-minute self-inflicted halt shape — a net
asserting behaviour that a sibling agent has already correctly changed. Note this is NOT covered
by 71ae3fa7e55e's re-read: in run #36 the code was consistent and the net was stale, so a re-read
reproduces the breach.
UNBLOCKS:   none, but it is the process half of 71ae3fa7e55e — answer them together.
THEME:      run partitioning

---

### 382d3a1c387c  [OWNER] [INFO]  — Rule-of-three tell is narrower than the label it ships
STILL LIVE: YES — `tells.py:97` is unchanged:
`"rule of three": r"\b\w+, \w+,? and \w+ (?:alike|all|together)\b"`, and `prompt_section` still
hands the model the bare label.
QUESTION:   Is the trailing `alike|all|together` requirement the intended scope, or should the
pattern cover plain three-item lists?
OPTIONS:    (a) deliberate — add a scope comment in the shape of the `not merely / not simply /
not just` note at `:70-79`, and rename the label to what it catches ("X, Y and Z alike")  (b)
widen the pattern, measuring the false-positive rate against the existing corpus first.
RECOMMEND:  (a) — an unqualified three-item-list pattern fires on ordinary English constantly
("Persons, Places and Powers" is in your own charter), and this file already defends one such
asymmetry at length after run33 filed it as a bug without checking what symmetry would cost. The
rename is what actually closes the drift, because `prompt_in_sync` compares text and cannot see a
label whose pattern under-covers it.
COST IF WRONG: Under (a), a corpus with heavy rule-of-three cadence audits clean while the prompt
says the cadence was banned. Not urgent either way: the prose gate is shut.
UNBLOCKS:   **692f693c3900** — same pattern, same question, strictly less detail.
THEME:      prose tell scope

---

### 6e6954f261e0  [OWNER] [MAJOR]  — Prose gate never checks the Instrument section exists
STILL LIVE: YES — `prose_gate.py:49` is still
`REQUIRED_PER_ENTRY = ("Shelfmark:", "Class:", "Magnitude:", "Threads:")`, and the only other
Instrument check, `unearned_instrument()` at `:385`, catches a fabricated score when one is
present, never a section's absence. So the 2026-08-25 incident's own headline symptom — 1,155 of
1,268 entries losing their Instrument block, a 91% loss, worse than the 71% Threads loss that IS
checked — would pass layer 4 today.
QUESTION:   Should `REQUIRED_PER_ENTRY` be widened to require an Instrument marker?
OPTIONS:    (a) widen it — require either a score line `_AXIS_RE` recognises or the template's own
"Not applicable" text  (b) leave it; treat total absence as covered by `unearned_instrument()`.
RECOMMEND:  (a), scoped — this strengthens an owner-held safety rather than weakening one, and the
docstring naming Instrument loss as a founding symptom of the incident this layer exists to stop
is the strongest possible argument that its absence should be caught. One caveat that shapes the
implementation, not the ruling: `generate.py:346-347` says a feats chapter writes no Instrument
block by design, so the requirement must key off entry class or accept the "Not applicable" text,
or feats chapters will red every run.
COST IF WRONG: Under (b), a regenerated library can reproduce the original incident exactly and
every gate reports green. Under (a) badly scoped, feats chapters fail a check they were never
meant to satisfy — visible immediately, and recoverable.
UNBLOCKS:   none
THEME:      prose gate strictness

---

### 3b9812ae8ab7  [OWNER] [MINOR]  — Mach is written unit-first, so 86% is unminable
STILL LIVE: YES — `feats.py:1200` still carries `mach` inside the alternation anchored on a
leading figure, and the unit-first note at `:1187-1199` still discusses only `power level` and
`kili`; the word "mach" appears nowhere in it.
QUESTION:   Should `_QUANTITY` gain a second, unit-first alternative for Mach?
OPTIONS:    (a) no — the existing note's argument (a quantity attributed to the wrong subject is
worse evidence than none, and this pattern has no subject resolution) applies unchanged; extend
the note to name mach  (b) yes — add a unit-first alternative for Mach only  (c) yes, and revisit
`power level` on the same basis.
RECOMMEND:  (b) — the note's own argument is weaker here and the order says why: "Mach 5" is a far
less ambiguous token than "a power level of 5,000", which is exactly the ambiguity the subject-
resolution worry is about. The volume is honest and small (210 unminable vs 33 minable, measured
across all 275,029 files, nothing sampled), so it is a cheap, bounded test of whether unit-first
mining is safe before anyone touches `power level`'s 11,622 mentions.
COST IF WRONG: A handful of Mach figures attributed to the wrong subject in ~210 sentences —
detectable, and far smaller blast radius than the same change on `power level`. Choosing (a)
costs 86% of the Mach evidence in the corpus, permanently and silently.
UNBLOCKS:   the LOCAL half (extend the `:1187-1199` note to name mach) needs no ruling and can go
either way this lands.
THEME:      assay pattern coverage

---

### 3fb9fc6b9999  [OWNER] [MAJOR]  — ledger.py (De Pretio) has no caller in the pipeline
STILL LIVE: YES — re-grepped today: the only `import ledger` in `src/` is `verify_math.py:739`.
Every other hit is `ledger_guard`, a different module. `manifest_builder.py`, `generate.py`,
`prose_gate.py` and the `catalogue_*` modules import neither.
QUESTION:   Is the omniversal currency standard scheduled work, or is it dead weight?
OPTIONS:    (a) wire it — the Position Paragraph clause it exists to serve gets currency wiring in
the generation path and prompts  (b) mark it explicitly as charter machinery held for a future
phase, so no sweep re-files it  (c) retire it to `src/deprecated/`.
RECOMMEND:  (b) — it is fully built, internally consistent and exercised by
`verify_math.py:266-284`, so it costs nothing to hold; and (a) is a content decision about whether
entries state prices at the Freeport, which is a charter question and yours alone. What is NOT
defensible is the current state, where a reader cannot tell "not yet wired" from "forgotten" —
this has been re-filed at least twice.
COST IF WRONG: Under (c) you would rebuild it if the Position Paragraph clause is ever honoured;
under (b) nothing breaks, you just carry ~1 module of unused, tested code.
UNBLOCKS:   none
THEME:      unwired subsystem

---

### 79da6c08c536  [OWNER] [INFO]  — Rejections filed even when the host-map write was refused
STILL LIVE: YES structurally (`hostcheck.py:1040`, `unfit_landed = _land(UNFIT, unfit) if
n_reject else None`, ungated on `landed`) — but **reroute to LOCAL: no ruling needed.** The
code already argues reading (a) at `:1018-1035` under order `1b15acd3f7b2` ("a refused UNFIT write
left the source gone from the host map with no finding written down anywhere"), and the operator
gets both facts because `:1046` prints `"WIKI_HOSTS.json NOT updated: " + why` to stderr. The
stakes are nil, re-verified today: nothing in `src/` reads `data/HOST_UNFIT.json` — the only two
mentions in the whole tree are `hostcheck.py:73` defining the path and `:1033` in a comment.
QUESTION:   n/a — the order itself offers "a one-line comment saying so" as a complete remedy.
OPTIONS:    (a) LOCAL: one comment at `:1040` recording that the unfit write is deliberately
ungated, so the next sweep stops re-filing it  (b) LOCAL: additionally stamp each unfit row with
whether the host-map write landed.
RECOMMEND:  (a) — cheapest thing that ends the re-filing; (b) is optional polish on a file no
program reads.
COST IF WRONG: A human reading `HOST_UNFIT.json` may believe a rejection took effect when the map
write was denied — mitigated by the stderr line in the same run.
UNBLOCKS:   none
THEME:      verdict/write gating

---

### e8622cf0d047  [SESSION] [MINOR]  — `why=None` reverts a good patch with a wrong error
STILL LIVE: YES — `local_agent.py:953` is still `return _settle({"applied": True, "why":
why[:200]})`, while the guarded sibling at `:777` is `(why or "")[:200]` and the dispatch at
`:1277` is still `t_propose_patch(apply=apply, log=patches, **args)` with `args` decoded from the
model's JSON. **Reroute to RUN — no ruling needed.**
QUESTION:   n/a — this is a one-token fix with a stated remedy and a guarded sibling twelve lines
up to copy from.
OPTIONS:    (a) RUN: change `:953` to `(why or "")[:200]`.
RECOMMEND:  (a) — no judgment is involved; the correct spelling already exists in the same
function. It cannot go to LOCAL because `local_agent.py` is on `local_agent.DENYLIST`, which is
probably why it landed on SESSION and then read as an owner-rung item.
COST IF WRONG: Every patch the model writes with `"why": null` is written, gated, passed, then
thrown away and reported as `TypeError: 'NoneType' object is not subscriptable` — an argument-shape
fault wearing an apply/revert fault's message, on the one lane where a model writes to `src/`.
UNBLOCKS:   cca253138a62 travels with it (same file, same denylist constraint, one visit)
THEME:      misfiled code fix

---

### 789f99f2a65f  [OWNER] [MAJOR]  — tiers.py prints "hyperverse DECLINED" while assigning one
STILL LIVE: YES — `tiers.py:374` still prints
`"hyperverse: DECLINED for all {len(srcs)} shelves — uncharted by cause, not omission"` in the
same `main()` whose `chart()` writes `out[s]["hyperverse"]` and `["hyperverse_type"]` at
`:315-317`. **Reroute to RUN/LOCAL — no ruling needed.**
QUESTION:   n/a — the order answers itself in its own words: "THE CLAIM IS STALE, NOT THE CUT."
OPTIONS:    (a) RUN: correct the `:374` print and the top docstring (`:3`, `:38`, `:44`, `:87`) to
say the hyperverse is the xenoverse's grounding, per `:150-153` and `:315-317`.
RECOMMEND:  (a) — the tier was re-implemented as a grounding and the prose was never updated. No
data changes; `data/TIERS.json` already holds the four non-null values and is correct. This is a
comment-contradicts-code fix, which is a stated lens of the sweep, not an owner decision.
COST IF WRONG: A reader takes "DECLINED for all 209 shelves" at face value and builds on the
belief that the tier is uncharted, while `TIERS.json` says otherwise — the exact Hard Rule 4
failure `address_space.shelfmark`'s docstring already suffered for three sweeps.
UNBLOCKS:   it is the tiers.py half of be9e9f089d62's address-space question, and answering it
does not depend on that ruling.
THEME:      doc-vs-code drift

---

### 5c8a7bc883e7  [OWNER] [MAJOR]  — One feat-bearing entry excludes the whole rest of the cast
STILL LIVE: YES — `pipeline.py:1459` is still
`blocks = ([with_feats[i:i+14] ...] or [rest[i:i+14] ...])`. The `or` means `rest` is reached only
when NO entry in the source has a mined feat.
QUESTION:   Does a mined feat strictly displace lead paragraphs from ceiling nomination, or should
feat-bearing blocks simply be ranked ahead of the rest?
OPTIONS:    (a) keep the `or` — a mined feat displaces  (b) concatenate: `with_feats` blocks
FOLLOWED BY `rest` blocks — ranking kept, nothing excluded.
RECOMMEND:  **(b)** — the 2026-08-25 ruling is written in the comment directly above this line and
says lead paragraphs CAN carry a ceiling feat; on that premise, dropping 46 of 54 lead paragraphs
because 8 siblings have a mined feat is the same act the ruling forbade, expressed as an `or`
instead of a slice. The measured cases make it concrete: `tales-from-the-yawning-portal` nominates
from 8 of 54 entries, `kbp-unlikely-heroes` from 2 of 55.
COST IF WRONG: (b) costs pool spend — a source whose 8 feat-bearing entries would have been one
call becomes four or five. That is the same spend the owner already accepted when removing
`rest[:14]`, and the comment above the line states the cost case explicitly. (a) leaves ceilings
chosen from a fraction of the cast and published as though the source had been read.
UNBLOCKS:   `retry_synthesis.synthesise()` shares this function, so one answer covers both paths.
THEME:      Hard Rule 0 caps

---

### cca253138a62  [SESSION] [INFO]  — Console tool trace cuts args and results unmarked
STILL LIVE: YES — `local_agent.py:1287-1288` still prints `json.dumps(args)[:90]` and
`json.dumps(res)[:110]` with no marker. **Reroute to RUN — no ruling needed.**
QUESTION:   n/a — the remedy is stated (append an ellipsis when either dump exceeds its width),
and the file already labels its other windows honestly at `:368-371` and `:1204-1206`.
OPTIONS:    (a) RUN: mark both cuts, in the same visit as e8622cf0d047.
RECOMMEND:  (a) — genuinely INFO now: the durable channels were repaired and `main()` prints the
verdict first and unconditionally, so nothing load-bearing rides this line. It is a consistency
fix inside a `DENYLIST`-protected file, which is the only reason it cannot go to LOCAL.
COST IF WRONG: A person watching a run sees a truncated result and cannot tell it was truncated —
the condition that once hid a failed revert behind the `ALARM` key.
UNBLOCKS:   none (bundle with e8622cf0d047)
THEME:      misfiled code fix

---

### 2e0ba4b02ec4  [OWNER] [INFO]  — Phantom pass builds its `defined` set module-wide
STILL LIVE: YES — `liveness.py:499-517` walks the whole module tree `t` and adds every
`FunctionDef`, `Store` name, `arg`, import and handler name to one flat `defined` set, with no
per-function scoping. The sibling DEAD pass, by contrast, uses three scoped sets (`used`,
`used_local[name]`, `reachable`) at `:465-473`.
QUESTION:   Should the phantom detector scope `defined` per function, accepting more findings, or
stay module-wide and conservative?
OPTIONS:    (a) scope it, matching the DEAD pass  (b) leave it module-wide and write the policy
into the docstring so it stops being re-filed.
RECOMMEND:  (b) — the file's stated policy is to err toward no false positive, and a module-wide
set can only ever UNDER-report, never invent. The real reason to be slow here is named in the
order: liveness's finding count is ratcheted by a drill net (`drill.LIVENESS_CEILING`), so (a)
moves the ratchet and would need the new baseline watched before it is trusted. If you do want
(a), take it as its own piece of work with the count measured before and after, not as a tidy-up.
COST IF WRONG: Under (b), a guard naming a name defined only in a different function goes
unreported — it raises `NameError` on the branch nobody takes, which is exactly the fault class
this pass exists for. Under (a), a noisier detector that people stop reading, plus a ratchet move.
UNBLOCKS:   none
THEME:      detector scope

---

### 2f38b3e5258d  [OWNER] [MINOR]  — resident() and fit_note() measure different VRAM budgets
STILL LIVE: YES — `pick_model.py:192` `resident(model_entry, budget_gb)` is fed
`total_vram_gb()` (`:308`, and `:176-177` says it sizes "against TOTAL minus a reserve, not
against free"), while `fit_note()` at `:244-257` compares against free VRAM and prints
`"WILL OFFLOAD: needs ~XGB vs YGB free"`. Neither docstring says which question it answers.
**Reroute to LOCAL — no ruling needed.**
QUESTION:   n/a — the order itself offers "one sentence in each docstring" as a complete remedy,
and both measurements are legitimate: "does this fit the card" and "does this fit right now" are
different questions on a shared GPU.
OPTIONS:    (a) LOCAL: one sentence in each docstring naming its budget  (b) OWNER: make them
agree by gating `resident()` on free VRAM too.
RECOMMEND:  (a) — (b) would make the residency gate flap with whatever the desktop happens to hold
this minute, which is the opposite of what a standing eligibility rule wants; `free_vram_gb()`'s
own docstring explains why the two are separate.
COST IF WRONG: An operator reads "usable" and "WILL OFFLOAD" about the same model in the same
report and mistrusts the tool. Nothing downstream is decided by the disagreement.
UNBLOCKS:   none
THEME:      docstring precision

---

### 692f693c3900  [OWNER] [MINOR]  — Duplicate of the rule-of-three scope question
STILL LIVE: NO, as a separate item — this is the same finding as `382d3a1c387c` about the same
line, `tells.py:97`, filed two sweeps earlier with strictly less evidence (`evidence: {}` here,
versus the pattern, the counterexample, the precedent at `:70-79` and both readings there).
QUESTION:   Nothing distinct is being decided.
OPTIONS:    (a) close as duplicate of 382d3a1c387c.
RECOMMEND:  (a) — answer 382d3a1c387c once and this closes with it; leaving both on the rung is
the same "two entries, one fault" dilution `ca0a93856e2a` is about, in the other ledger.
COST IF WRONG: None.
UNBLOCKS:   n/a — it is the thing 382d3a1c387c unblocks.
THEME:      duplicate order

---

## Cross-cutting note

Two orders in this batch (`71ae3fa7e55e`, `d8858a26e46e`) are the two halves of one condition:
gates read a tree that distributed work has made temporarily inconsistent. The mechanical half is
"re-read the breached net before halting"; the process half is "sequence the battery after the
agents report, and write that rule somewhere that survives the run." Answering them in the same
sitting is worth more than answering either alone — and the second is currently recorded only in
`NEXT_STEPS.md`, which `MAINTENANCE.md` says is overwritten every run.
