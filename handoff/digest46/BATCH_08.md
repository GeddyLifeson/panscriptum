# OWNER DECISION DIGEST — BATCH 08

20 open OWNER/SESSION orders, each verified against the live tree on 2026-09-07.
16 still live, 4 dead. 3 of the live ones need no ruling and should be rerouted.

---

### 82fc93f056d4  [OWNER] [MINOR]  — read 55 wh40k axes and tag each wiki or canon

STILL LIVE: yes — `wh40k.py:220` already reads the tag off the tuple (`"[" + _provenance(v) + "] "`)
and `_provenance` at :230-238 defaults to `unattributed`, but every ROSTER axis is still a 2-tuple
(grep for a third element across the file: zero hits), so all 55 axes print `[unattributed]` today.
QUESTION:   Who spends the hour reading 55 axis sentences to mark each one quotation or paraphrase,
and is `unattributed` acceptable on the published worksheet until they do?
OPTIONS:    (a) commission the 55-axis reading pass now, mark each `wiki`/`canon`, leave the rest
unattributed  (b) ship as-is — `unattributed` is honest and blocks nothing  (c) do it opportunistically,
tagging axes only as some other pass touches them.
RECOMMEND:  (a), but scoped to one sitting — halo.py's precedent found 24 of 33 tags false, so the
prior that these are mixed is strong and the file is only 5 entities deep. The code is already
finished; this is pure reading, and it never gets cheaper than a single focused pass.
COST IF WRONG: Choosing (b) leaves a citations worksheet whose entire provenance column says
"nobody checked" — no data is corrupted, only the file's usefulness as evidence.
UNBLOCKS:   none (halo.py and zfighters.py are already done)
THEME:      provenance honesty

---

### a8464e348c5e  [OWNER] [MAJOR]  — read pass stall: both 2026-08-27 causes are gone

STILL LIVE: NO — both named causes are measurably absent. Ollama's `/api/ps` reports the resident
qwen3:8b at `context_length: 12288`, which equals `config.yaml:82 num_ctx: 12288`, so the context
mismatch that this order's remedies all addressed no longer exists; and no `semsearch.cli watch`
process is running (pid 11468 is gone; a full python/pythonw enumeration shows only `read.py --run`
and the mutation pass). All three offered remedies are done or moot.
QUESTION:   Nothing left to rule on — but the SYMPTOM outlived the diagnosis and needs re-filing.
OPTIONS:    (a) close this order and file a fresh diagnostic order for the residual stall
(b) leave it open, which asks the owner to re-decide a settled question.
RECOMMEND:  (a) — reroute to RUN/LOCAL, no ruling needed. `state/read_auto.log` at 18:21 today
still reads 0.01 chunks/s, 2,625 of 240,441 entities, ETA 17,433h, with repeated
"ollama failed after 3 tries: TimeoutError", and the GPU sits at 99% util / 8.2 of 10.2 GB. That is
a NEW cause (a saturated single-GPU shared with the running mutation pass and timing-out ollama
calls), and it deserves its own measurement rather than inheriting a refuted one.
COST IF WRONG: Leaving it open costs the owner a repeat ruling on a mismatch that no longer exists,
and hides the fact that the stall survived its own fix.
UNBLOCKS:   informs 9fb8a6b10c1f (both are about having one model on one saturated card)
THEME:      stale diagnosis

---

### b317ba3a4f36  [OWNER] [MAJOR]  — re-derive GENRES.json confidences, moving 63 published flags

STILL LIVE: yes — the code is fixed (`genre.py:135 def classify_text(text, top=None)`, `:233
total = sum(s for _, s in ranked)` over the whole field) but the stored file is untouched:
`data/GENRES.json` still reads 2112 (Rush) confidence 0.567 (the corrected value is 0.530), still
carries exactly 2 runners-up for 207 of 210 records, and still flags only 46 sources below 0.45.
QUESTION:   Do we re-run `src/genre.py --write` and let 193 published confidences drop and the
mixed-source flag count go from 46 to ~106?
OPTIONS:    (a) re-derive now  (b) leave the stored file until some consumer needs it
(c) re-derive but record a before/after table so the movement is documented rather than silent.
RECOMMEND:  (c) — zero genre labels change, so nothing downstream is re-classified; only the
honesty of the confidence number moves, and it moves the way the module's own docstring says it
should. Writing the before/after alongside it costs one file and stops a future reader reading a
0.616 in an old handoff as a contradiction.
COST IF WRONG: Choosing (b) means 63 sources that the module's own 0.45 rule calls mixed keep
presenting as confidently single-genre, and every day of prose or downstream selection built on
them inherits that.
UNBLOCKS:   none, but the same shape sits in `grounding.py` (`classify_text`, `score / total`) —
check it was fixed in the same pass before re-deriving.
THEME:      stored data vs fixed writer

---

### d2e44a766769  [OWNER] [MAJOR]  — gate restart_reader's kill on restartability, or adopt read.py

STILL LIVE: yes — `foreman.py:511-553`. `restart_reader` still matches on `lognames.OWNER[READ]`
and calls `os.kill(pid, signal.SIGTERM)` at :547 with no `_restartable()` check; the sibling
`kill_stalled_job` still carries the 2026-08-25 "NEVER KILL WHAT YOU CANNOT RESTART" gate.
QUESTION:   Should the automatic remedy for "counters are moving" be forbidden from killing the
reader, or should read.py be promoted into the keeper's STANDING set so the kill becomes cheap?
OPTIONS:    (a) gate it: refuse the kill and escalate SUPERVISOR/STALLED_UNRESTARTABLE, as
`kill_stalled_job` does  (b) put `read.py --run` into `overnight.STANDING` so the kill costs 300s
instead of up to four hours  (c) leave it — a wedged reader is worth nothing anyway.
RECOMMEND:  (b) — reading (a) turns the remedy into a permanent no-op by construction, and (c) is
the reading a measured four-hour outage already refuted. Promoting read.py makes the docstring's
own justification true instead of arguing about it, and it is the only option that leaves a working
remedy behind. Note this is a supervisor-topology change, so it is genuinely the owner's call.
COST IF WRONG: Under (b) a badly-behaved reader gets restarted every five minutes instead of once
a lap, which burns GPU on repeated startup; under (a) the counters-flat stall has no remedy at all.
UNBLOCKS:   NEXT_STEPS S2 B (named in `_restart_horizon` as holding three candidate fixes awaiting
this same ruling)
THEME:      kill/restart topology

---

### f27c121c6cb7  [OWNER] [MAJOR]  — re-catalogue stored entry types while the prose gate is shut

STILL LIVE: yes — measured on disk today: 216 records, 156 with mode='web', 272,004 entries, and
Warhammer Fantasy's Events still carry the type `Total War: Warhammer` (690 entries). Nothing has
been re-catalogued. `config.yaml:108 prose_enabled: false` still holds, so the "cheap now" argument
in the order is still true.
QUESTION:   Do we spend days of free-tier pool time re-cataloguing 156 sources to repair stored
`type` fields, do a targeted subset, or nothing?
OPTIONS:    (a) full `--recatalogue` of all 156 web sources  (b) targeted: re-catalogue only the
sources whose stored types are provably not entity kinds  (c) defer until a full re-catalogue is
running for another reason.
RECOMMEND:  (b) — my own scan today counts ~25,000 entries carrying a multi-word or colon-bearing
type, and the worst are unmistakable: `Total War: Warhammer` (690), `Pages using ISBN magic link`
(255, a wiki maintenance category stored as an entity kind). That is a small ranked list, a bounded
pool spend, and it fixes the entries that would most visibly poison a prompt.
COST IF WRONG: Choosing (c) means the repair happens after prose is running, when every wrong type
has already been carried into finished text and the fix is a re-generation rather than a re-fetch.
UNBLOCKS:   none
THEME:      stored data vs fixed writer

---

### 97cc0dc43ca7  [OWNER] [MAJOR]  — lock the halt write, and decide fail-open vs fail-closed

STILL LIVE: yes — `escalation.py:396-421` is still the bounded CAS-plus-readback loop
(`for _attempt in range(STOP_CAS_ATTEMPTS)`), and there is no `O_CREAT|O_EXCL` anywhere in the file.
The residual measured window (1/25 trials at two writers, 7/25 at four) stands.
QUESTION:   Do we put an exclusive-create lock around the halt read-modify-write, and if the lock
cannot be taken in budget, does the halt still get raised?
OPTIONS:    (a) O_EXCL lock with staleness steal and FAIL-OPEN fallback — raise the halt anyway
(b) O_EXCL lock, fail-closed — refuse to raise if the lock is stuck  (c) leave the CAS as is and
accept losing a corroboration entry roughly 1 time in 25 under simultaneous first halts.
RECOMMEND:  (a) — this is a safety path, so the failure that matters is a halt that never gets
raised because a lockfile is stuck, not a duplicated one. Fail-open keeps the guard's purpose intact
while closing the window; (b) would convert a rare lost corroboration into a rare lost halt, which
is strictly worse.
COST IF WRONG: Under (b), one stale lockfile silently disarms the entire OWNER halt path. Under (c),
a library-wide invariant that breaks for several jobs at once can still lose one of the faults.
UNBLOCKS:   BUGS.md M38 (this is its last limb)
THEME:      halt-path concurrency

---

### 18d0fedabf13  [SESSION] [MINOR]  — pick which college and bit-value properties anchors grades

STILL LIVE: yes — `anchors.py:190` computes `col = CU.convene(...)` and `:208` computes
`bit = R.measure_bit_value(...)`, and a grep for any `col[` read in the file returns nothing; all
five CLAIMS lambdas at :336-370 still take `col` and none touch it.
QUESTION:   Which properties of the college reading is the project willing to have fail at a fixed
anchor, so they can be graded rather than printed?
OPTIONS:    (a) grade a finite non-zero interval per anchor  (b) grade prior/attestation shares
summing to 1.0  (c) grade `dispersive_without_mechanism == []`  (d) grade `measure_bit_value`
strictly increasing across `A.LADDER`.
RECOMMEND:  (a) + (c) + (d), and explicitly NOT (b). Checked: `custodes.py:540` computes
`attestation_floor_share` as `round(1.0 - prior_share, 3)`, so the two are complements by
construction, not computed separately — grading (b) would add a tautology, exactly the mistake the
order warns about with `covers_every_reading`.
COST IF WRONG: Grading nothing keeps two whole sub-instruments exercised at five calibration points
and judged by nothing; grading (b) makes the file look better tested while testing nothing.
UNBLOCKS:   none
THEME:      grading discipline

---

### a1aa2be36b7e  [SESSION] [MINOR]  — refuse a mutation root that is the live tree

STILL LIVE: yes — `mutate.py:1910-1912` still reads `own_sandbox = root is None; root = root or
sandbox(); path = os.path.join(root, "src", target)` with no comparison against `HERE`. Reroute to
RUN/LOCAL — no ruling needed.
QUESTION:   None. The remedy is one refusal at the top of `_run_mutation`, in the exact shape the
missing-baseline refusal directly above it already uses.
OPTIONS:    (a) add the assertion  (b) don't.
RECOMMEND:  (a) — it adds a guard rather than weakening one, has no behavioural effect on any
existing caller (all verified: `_session` passes `sandbox()`, both drill sites stub `_run_mutation`),
and makes the module's stated architecture a property of the code instead of the callers.
COST IF WRONG: Not adding it leaves a public entry point advertised for "a future scheduler" that
would corrupt real source for hours while three separate guards report success.
UNBLOCKS:   none
THEME:      sandbox safety

---

### 570525d35825  [OWNER] [MINOR]  — MODE_HTML constant no resolver can return

STILL LIVE: NO — resolved by documentation under order a60c150b6303. `endpoint.py:406-408` now
states plainly: "`detect()` can never return MODE_HTML, so the constant below has no reader anywhere
in the tree -- kept as the honest NAME for what the prefix selects, and documented here so it does
not read as a mode the prober forgot to emit." The misleading "So a third mode" comment the order
was filed against is gone.
QUESTION:   Nothing to decide; a third option (keep and document) was taken and the harm — a reader
misled into writing a comparison that cannot succeed — is closed.
OPTIONS:    n/a
RECOMMEND:  Close it. If a general dead-name cleanup ever runs, this joins that pass on its merits.
COST IF WRONG: none
UNBLOCKS:   none
THEME:      resolved by doc

---

### 9fb8a6b10c1f  [OWNER] [MAJOR]  — cascade has no reachable model and grades broken every run

STILL LIVE: yes — measured today: ollama `/api/tags` holds exactly one model (qwen3:8b), and the
most recent sweep, `state/allsweep_final_20260905.log`, still reads "cascade live call ... rc=0
(broken)" and "Cascade — 0 usable remote bucket(s)".
QUESTION:   Do we spend money on a provider, pull a local model that fits, or point the router's
local bucket at the one model that is actually resident and accept the reduced roster?
OPTIONS:    (a) re-point the cascade roster's local entries at qwen3:8b, which is pulled and serving
(b) pull one of the five 404ing local models  (c) fund one cloud provider  (d) accept it and stop
grading cascade as a subsystem.
RECOMMEND:  (a) first, then reconsider — it costs nothing, uses the model already resident, and turns
a permanently red subsystem green or honestly amber. (b) is the wrong move today with the GPU at 99%
util and the read pass already timing out on the one model it has. The roster lives in cascade's own
config.json outside this kit, which is why it is yours and not the library's.
COST IF WRONG: Choosing (d) removes a real signal; leaving it as-is trains everyone to ignore a red
row in every sweep, which is how a genuine cascade fault gets missed later.
UNBLOCKS:   context for a8464e348c5e's residual stall
THEME:      model capacity

---

### ddb5eadd8934  [SESSION] [MINOR]  — should lifting a rung-4 stop require a person

STILL LIVE: yes, but half-settled. `escalation.py:811-812` still gates on the 20-character ruling
alone; `_by_a_person_at_the_cli` is called only at :949 (inside `clear`), and argparse at :1068-1086
still offers no `--resume`. The docstring overclaim that option (b) asked for HAS already been fixed
(order 8b1b81bcfee4), so only the policy half is open.
QUESTION:   May an autonomous run lift a MANAGER-rung subsystem stop, or must a person be at the CLI?
OPTIONS:    (a) require the person check, give drill.py a private test-only release path, and add a
`--resume` to main()  (b) accept the programmatic resume as deliberate, now that the docstring is
already honest about it.
RECOMMEND:  (a) — the incident this guard exists for (catalogue_web stopped at 22:5x, restarted at
23:21) was an automated actor, which is precisely the class the current gate does not cover, and
there is today no person-facing command to lift a stop at all. Note that (b) is not a weakening so
much as an admission, but it leaves the rung-4 stop liftable by any loop with 20 characters.
COST IF WRONG: Under (a), drill's three rung-4 probes must be given a clean-up path or they will
leave orphaned stops on a live library — the order already records that happening.
UNBLOCKS:   none
THEME:      chain of command

---

### f07b7d538ed1  [OWNER] [MAJOR]  — Star Realms host misbound (truncated duplicate)

STILL LIVE: yes as a fact, NO as a separate order — `data/WIKI_HOSTS.json` still maps
'Star Realms' to 'starrealms.fandom.com'. This is the same finding as 2d6bef2aef03, filed twice;
this copy is the one the old 600-char cap truncated and whose remedy is unrecoverable.
QUESTION:   Nothing distinct. Close as a duplicate of 2d6bef2aef03 and rule once, there.
OPTIONS:    (a) merge into 2d6bef2aef03  (b) keep both open.
RECOMMEND:  (a) — 2d6bef2aef03 carries the same evidence, is re-measured live by
`binding_health.identity` (seen 66 times, last on 2026-09-06) and is not truncated. Two orders on one
host binding is one more ruling than the fact deserves.
COST IF WRONG: none beyond a duplicate on the desk
UNBLOCKS:   settled entirely by the 2d6bef2aef03 ruling
THEME:      host bindings

---

### 729c26e0e63c  [SESSION] [MINOR]  — declared count unpacked and never compared

STILL LIVE: yes — `recover_folder_records.py:140` still reads
`for register_source, _declared_count in mapped:` and the count is never compared with
`len(by_source.get(register_source, []))` two lines below. Reroute to RUN/LOCAL — no ruling needed.
QUESTION:   None. Both numbers are on adjacent lines, the remedy is fully specified, and the
reporting convention it must follow (name the sources, do not count them) is already established for
this same file by order aff81a1f1029.
OPTIONS:    (a) implement as written  (b) leave it.
RECOMMEND:  (a) — a mapping declaring 350 items against a register yielding 3 currently lands
silently, is stamped `status='catalogued'`, and because work selection everywhere keys on
`entry_count == 0` the source is never revisited. That is the "a truncated catalogue is
indistinguishable from a complete one" shape, arriving free through data already paid for.
COST IF WRONG: Leaving it means silent under-recovery that no counter anywhere will ever surface.
UNBLOCKS:   none
THEME:      silent truncation

---

### e637c67ab438  [OWNER] [MINOR]  — weave.null_threshold was unreported dead code

STILL LIVE: NO — the gap this order names has been closed. `weave.py:361-367` now carries the
annotation: "SUPERSEDED, NOT CALLED ANYWHERE -- `main()` here, `pipeline.py` and `tiers.py` all call
`null_threshold_surprisal()` instead ... Reported in sweeps 22, 25, 26, 27, 28, 30, 31, 34, 38 and
now here (order 905f13a21f0c) -- this is the annotation that was missing from the matched pair."
QUESTION:   The order asked for option (b), annotate and leave for a combined cleanup; that is what
the tree now does.
OPTIONS:    n/a for this order. A separate, larger decision remains: whether the project ever runs
that combined dead-code deletion pass.
RECOMMEND:  Close it, and if you want the deletion question asked, ask it once across all annotated
dead functions rather than one order per function — that is what nine repeat filings were really
signalling.
COST IF WRONG: none
UNBLOCKS:   c0384991bfc5 would fold into the same combined pass
THEME:      dead code doctrine

---

### 61c763a60779  [SESSION] [MINOR]  — quarantine write verdict discarded, console asserts it anyway

STILL LIVE: yes — `binding_health.py:1094` is still a bare `quarantine(h, rec.get("reason") or
"canary failed")`, while the two branches at :1099 and below capture `release()`'s verdict; and
`:1282` still prints "%d host(s) checked, %d failed and quarantined" off the `failed` counter.
Reroute to RUN/LOCAL — no ruling needed.
QUESTION:   None. The sibling three lines below already establishes the pattern and the docstring at
:243-266 is the argument for it.
OPTIONS:    (a) capture `landed` into `rec["quarantined"]` and count the summary off that  (b) leave it.
RECOMMEND:  (a) — this is not a lost alarm (`quarantine()` raises HOST_QUARANTINE_NOT_RECORDED
itself), it is a stored report and a console line asserting an action that may not have happened,
pointing the opposite way from the fault `_report_not_released` was written for.
COST IF WRONG: A reader cannot distinguish a host that was held from one whose hold was refused.
UNBLOCKS:   none
THEME:      write-verdict discipline

---

### e296ea51a1d9  [OWNER] [MINOR]  — the 25-file floor that hides small broken caches

STILL LIVE: yes — `health.py:698` still reads `if len(files) < 25: continue`, still the one numeric
threshold in that function with no comment defending it, while every sibling constant around it
carries a paragraph.
QUESTION:   Is 25 a deliberate significance floor, and if so should a directory below it be exempt
entirely or merely reported more weakly?
OPTIONS:    (a) document the number and keep the exemption  (b) keep the floor but emit a weaker
"small and entirely empty" note below it  (c) lower or remove the floor.
RECOMMEND:  (b) — it preserves whatever statistical caution the 25 encodes while removing the
permanent blind spot, since a new host that 404s on everything stays under 25 files forever and is
therefore invisible to this detector for exactly as long as it stays broken. (a) alone documents the
blind spot rather than closing it.
COST IF WRONG: (c) risks noisy findings on genuinely fresh directories, which is the failure mode
that teaches people to ignore this report.
UNBLOCKS:   none
THEME:      detector blind spot

---

### 1f9a54bede08  [SESSION] [MINOR]  — mark or remove the 600/900-char cuts in both writers

STILL LIVE: yes — `retry_synthesis.py` still stores `ev = _ev[:600]` and the rationale at [:900],
and the surrounding comment says so directly: "That stored-length question is untouched here and
stays open." The related drift (validating the cut string) was fixed separately; the stored-length
question was not.
QUESTION:   Do the evidence and rationale fields keep their whole value, or carry an explicit
truncation marker plus original length?
OPTIONS:    (a) both writers store the whole value  (b) both writers append a marker and the
original character count  (c) leave as-is.
RECOMMEND:  (b) — evidence is the string a reader later checks a band claim against, so an
unmarked cut is exactly the "a truncated X is indistinguishable from a complete one" fault this
project keeps finding, and (a) risks unbounded record growth for no reader's benefit. Whichever is
chosen, change `pipeline.py:1151-1152` in the same commit or the documented parity breaks.
COST IF WRONG: (c) leaves a reader unable to tell a cut evidence string from a short one, in the
field the "no feat, no band" invariant is judged on.
UNBLOCKS:   none
THEME:      truncation markers

---

### 2d8b96343896  [SESSION] [INFO]  — is the drill:4256 citation a quotation or a pointer

STILL LIVE: NO, effectively — the sentence already dates itself. `mutate.py:1208-1212` sits inside
"Measured on 2026-08-27: ... and the reap ledger added this shift named the call site,
`drill.py:4256 -> M.reap_orphans()`", which reads as reading (b), a verbatim ledger row from that
date, not a current pointer. Reroute to RUN/LOCAL if anyone wants the clause made explicit.
QUESTION:   Nothing requiring the owner. If touched at all, add three words ("read, at the time,")
and stop.
OPTIONS:    (a) add the clarifying clause  (b) close as already-clear.
RECOMMEND:  (b), or (a) opportunistically — I confirmed the live call sites are now drill.py:11982
and :12079, so a reader following the number as a pointer lands nowhere, but the "Measured on
2026-08-27" that opens the sentence already tells them not to.
COST IF WRONG: negligible — one comment reads slightly ambiguously.
UNBLOCKS:   none
THEME:      citation hygiene

---

### 2d6bef2aef03  [OWNER] [MAJOR]  — Star Realms is bound to a wiki that serves something else

STILL LIVE: yes — `data/WIKI_HOSTS.json` still maps 'Star Realms' to 'starrealms.fandom.com', and
`binding_health.identity` has re-detected it 66 times, most recently 2026-09-06.
QUESTION:   Rebind, unbind, or leave a source pointed at a host that serves The Brain World Wikia?
OPTIONS:    (a) unbind — set the host to null, as four sources in this file already are
(b) rebind to a non-Fandom Star Realms source  (c) leave it and live with the daily MISBOUND alarm.
RECOMMEND:  (a) — I checked the record: `data/records/star-realms.json` holds 68 entries with
correct names, types and descriptions ("Trade Federation", "Machine Cult", "Barter World"), so
nothing needs re-fetching and nothing is lost by unbinding. Both candidate replacement hosts were
already probed and neither exists, and the roll marks the source `catalogued` with entry_count 68 so
it is never revisited anyway. Unbinding costs nothing and silences a 66-times-repeated false alarm.
COST IF WRONG: (c) keeps a recurring MAJOR in every binding run, which is how real misbindings get
skimmed past. Unbinding forecloses nothing — the host can be set again if a real wiki appears.
UNBLOCKS:   f07b7d538ed1 (same fact, close as duplicate)
THEME:      host bindings

---

### c0384991bfc5  [OWNER] [MINOR]  — worldseed.unreachable_by_url has no callers

STILL LIVE: yes — `worldseed.py:278` is still the only match for the name in src/. Its docstring
("What the profile derives that a query string cannot deliver. Named, not hidden.") explains what it
does but never says it is deliberately uncalled, which is the annotation `read.cache_path` carries.
QUESTION:   Delete a public helper with no callers, or annotate it as deliberately kept?
OPTIONS:    (a) annotate as kept-and-uncalled  (b) delete  (c) fold into a single combined
dead-code decision covering every annotated leftover in the tree.
RECOMMEND:  (c), defaulting to (a) in the meantime — the function is a real, correct statement about
what the Azgaar query string cannot carry, and it sits next to a long comment about exactly that
limitation, so it reads as documentation with a signature. One line of annotation costs nothing and
takes it off the sweeps' re-filing list.
COST IF WRONG: Deleting removes a small piece of honest documentation about the render's limits;
keeping it costs 4 lines.
UNBLOCKS:   would be settled by the same combined pass as e637c67ab438
THEME:      dead code doctrine
