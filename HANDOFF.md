# Handoff Log — the maintenance-pass run journal

*One dated entry per maintenance run, newest on top. This is the RUN LOG only; the project's
deep engineering history, doctrine, and architecture live in `handoff/HANDOFF.md` (decision
recorded run #1: two files, two jobs — a run journal and a reference book do not share a
writer). Bug ledger: `BUGS.md`. Priority queue for the next run: `NEXT_STEPS.md`. The working
tree is not itself a git repo — commits happen through `src/publish.py --push` into the export
repo (`PANSCRIPTUM_EXPORT`), so "commit hash" below means an export-repo hash.*

---

## 2026-08-24 12:00 (local) — Run #8 (the writer that was two and a half hours out of date, and the names that were never the same twice)

**FOR THE OWNER, AT THE TOP:**

1. **No secrets, no money movement, no data loss. The paid lane is still shut and has not
   moved:** `598 used / cap 500`, byte-identical to how runs #6 and #7 left it, and
   `paid_lane_open()` returns **False**. Three runs of a flat counter is now the evidence that
   run #6's enforcement fix holds. **M4 remains YOUR decision, not a leak.**
2. **A process from an earlier session was two hours into silently corrupting the review
   ledger, and was stopped.** Details below — it is the run's main find, and it was caught by
   listing processes rather than by any check the kit runs.
3. **The Registry Terminal's node names were random.** Not stale, not wrong — *random*, changing
   on every regeneration, because a tie-break read a hash-randomized set. Now deterministic and
   settled once. This one is worth knowing because it means **any earlier "the nav names
   changed" observation was noise, not signal.**
4. **Run #7's biggest fix is now CONFIRMED IN PRODUCTION, by the test run #7 wrote for it.**
   Run #7 could only justify its `ask_pool_first` fix by construction — the cloud pool died
   before the failure could be reproduced — so it left a falsifiable check behind. That check has
   now fired: `state/pipeline_auto.log` at **11:33:11** reads *"pool answered entrypass with an
   unusable shape; falling back to local"*. That is the predicted signature exactly. **The cloud
   really was returning valid JSON of the wrong shape, run #7's diagnosis was right, and the
   guard catches it.** Honest limit: no batch has posted a `returned N/M` line since the 11:17
   bounce, so the *consequence* (0/20 becoming non-zero) is still unmeasured — but there are also
   **zero new `returned 0/20` lines**. See NEXT_STEPS item 1 for the one command that finishes it.
5. **fandom.com is still down at the socket** — unchanged across runs #5–#8. `health --preflight`
   reports it every run. Not a code fault, and the completeness audit stays honestly UNMEASURED.
6. **This run began 2 minutes after run #7 ended** (11:26:49 → 11:28:44). The scheduler fires
   faster than a run takes. The guard was correctly closed, so this was a legitimate run, not an
   overlap — but it means the code diff since the last run was nil and the value here came from
   working the queue rather than from reading a diff.

**THE RUN'S THEME: the dangerous writer is the one that has been away.** Both headline findings
are the same shape — a process or a function acting on a picture of the world it formed a while
ago, writing the whole thing back as if nothing had happened in between.

**m40 — AN ORPHANED PROCESS WAS ONE `return` AWAY FROM WIPING THE REVIEW LEDGER.** Listing
python processes turned up PID 35016: an ad-hoc `overwatch.verify_open` one-liner launched by an
**earlier session at 09:02**, still alive at 11:28 with **2.8 seconds of CPU across 2h26m** —
that ratio means blocked on a model reply, not working. It ends in `OW.save(led)`, and
`overwatch.save()` is a **whole-file replace**. It was holding a 09:02 snapshot of a ledger that
had since reached 68 rounds and 64 findings. Measured exactly what its return would have cost:
**4 findings destroyed** (3 open — `feats.roll`, `hostcheck.add`, and, pointedly,
`cascade_bridge.ask` — plus 1 retired), **1 retirement reverted**, and the round counter
regressed. **The write would have succeeded.** Nothing in the kit would have reported it; the
findings would simply never have existed. Killed it (it did no work anything depended on) and
confirmed the ledger was untouched.

The orphan is the instance; **the missing guard is the bug.** `save()` never asked whether the
file had changed under it. Now `load()` stamps the digest it read and `save()` compares: on a
mismatch it MERGES instead of replacing — union of findings, terminal verdicts win in either
direction, `seen` keeps the later sighting, `rounds` takes the max. Merging is only sound because
nothing in the module ever deletes a finding, so **verify_math pins that premise too** — if
retirement ever becomes a removal, the suite says so before it ships. Falsified against the real
event first: the pre-fix `save` drops both interloper findings and regresses rounds 68 → 2; the
new one keeps everything and still lands its own work. §19m, 10 checks. Bounced the live loop
onto the fix; the keeper re-asserted it at 11:37.

**A note on why this class keeps recurring: every maintenance run that leaves a long foreground
call behind creates one of these.** That is a habit, not an accident, and the guard is the only
thing that makes the habit survivable.

**m41 — THE NAV TREE'S NAMES WERE NEVER THE SAME TWICE, AND I NEARLY RECORDED THE CHURN AS A
FIX.** Chasing NEXT_STEPS item 2 (did run #7's genre regeneration reach its consumers?) I found
`data/NAVTREE.json` dated **08-21**, three days older than the regenerated `GENRES.json`, while
its downstream `output/registry_terminal.html` had been rebuilt **12 minutes earlier**. So a
reader-facing page was being rebuilt continuously from stale nav data — a tidy story, and I
regenerated the file: **168 of 734 node names changed**. I was one step from writing that up as
"the genre fix reaching production."

**Then I ran it a second time. 75 more names changed, with identical inputs.** The names were
not stale; they were nondeterministic. `PYTHONHASHSEED=0` made two separate processes agree byte
for byte, which named the cause: `register_for()` picks a node's naming register with
`max(set(regs), key=regs.count)`, and on a TIE — two registers equally common under one node, the
ordinary case on a small branch — `max` keeps whichever the **set** yielded first. String set
order is randomized per process. The register is an input to `coin_well_formed`, so a flipped tie
renames the node. `build()` picked hyperverse grounding types the same way. Both the module's own
comment ("seeded on the node's own key so the name is stable") and `coin_well_formed`'s docstring
("Deterministic: same input, same output") asserted the opposite of the behaviour — **the code
said it was deterministic and was believed.** Fixed by making the tie-break explicit
(`key=lambda r: (regs.count(r), r)`). Three processes with random seeds now agree exactly.

I **restored the 08-21 file byte-identically** the moment I learned the diff was noise, then
regenerated once on the fixed code to settle the names: **146 of 734 names changed, structure
untouched** (734 nodes, 0 added, 0 removed, not one non-name field), and a second `--write` is
now a genuine no-op. §19n, 5 checks.

**And the actual answer to item 2, which the churn was hiding:** `profile.build_all` reads
`GENRES.json` at runtime and **persists nothing**, so it has been current since the moment run #7
rewrote the file — no action needed, ever. `navtree` also reads it at runtime, but writes an
artifact that only a hand-run `--write` produces. Structurally that artifact was **already
current** (734 nodes before and after, nothing added or removed), so the genre change had no
structural consequence to deliver. Marvel's `superhero → mythology` / `compact → classical` move
is live in `GENRES.json` and reaches anything that computes from it.

**m37 — the audit subagent was right on all four counts, which is worth recording because the
standing advice says to expect otherwise.** Verified each against source before touching
anything. Confirmed repo-wide, not just `src/`: **nothing reads `data/CHAIN.json`** — the string
occurs outside documentation only at `chain.py:53` (the writer) and `chain.py:92` (its
docstring), and `pipeline.py:1255` drives the write side. So the Bradley-Terry strengths and the
Ford's-condition verdict are persisted every cycle and the cross-check the module calls its whole
purpose never runs. **Left open as a HUMAN CALL** — wiring a consumer invents a contract, and
"it obviously should do X" is not a licence. The other three were repairs and are fixed:
the **`sentence[:120]` dedup key** (Hard Rule 0 — measured **22 distinct contests** being
discarded on the live index, up from 2 on a smaller one, so the loss *grows with the corpus*),
the **bare `open(OUT,"w")`** on a published artifact, and the **discarded `replace_retry`** on
the harvest index.

**Two more discarded verdicts closed, from NEXT_STEPS items 21 and 22.** `pick_model.save_config`
claimed success two ways — it dropped `replace_retry`'s boolean AND its targeted `re.sub` could
match nothing, writing the file back byte-identical while `main()` printed "config.yaml updated"
regardless. `local_agent`'s **pyflakes gate could not fail**: it tested stdout alone, so a
pyflakes that never ran looked clean and waved a patch through one of the six gates standing
between a local model and live source. Both now report the truth.

**THE LADDER, honestly.** The repo's own bots did the generic work and I read their outputs
rather than redoing them. **Ollama is healthy** — `/api/ps` names qwen3:8b *and*
`llama-server.exe` (PID 37544) exists, so the known 503 wedge is absent; proved it with a real
generate call (HTTP 200, `OK`, 15.9s) rather than trusting `/api/tags`. **No Claude subagents
were spawned this run**: the queue had enough verified, concrete work in it that a fan-out would
have been invented work, and the rotation list is untouched and waiting for a run with a real
diff to read.

**BATTERY: `verify_math` 404 passed / 0 FAILED** (389 before this run's 15 new checks),
`allsweep` **0 subsystems in a bad state**, `health --preflight` 2 problems (M3 fandom, M1
dandwiki — both unchanged outages, not regressions), `pyflakes` clean across `src/`, and the
silence audit **13 → 12** silent handlers. That last one is not a boast: **the audit caught a
silent `except` I had just introduced in the m40 merge**, and I fixed it before shipping. The
battery is not ceremony.

**LESSONS**

- **Diff it twice.** The genre story was coherent, well-evidenced, and wrong, and the only thing
  that caught it was running the same command a second time and comparing. A single diff cannot
  tell "changed because of my fix" from "changes every time".
- **A comment asserting determinism is not evidence of determinism.** Two separate docstrings
  claimed the nav names were stable. Both were sincere and both were wrong.
- **`max(set(...))` is a bug, not a style.** Any tie-break over a set of strings is
  hash-order-dependent. Worth grepping for elsewhere; this run did not.
- **Check for orphans from previous sessions.** The kit's own health checks look at standing
  jobs; nothing looks for a two-hour-old foreground call from a dead session holding a stale
  snapshot of a shared file. Listing processes found in one command what no check would have.
- **"Only one module writes this file" does not mean one writer.** It means one *code path*, and
  a code path can be running in several processes at once.

---

## 2026-08-24 11:45 (local) — Run #7 (the fix that never reached production, and the batch that was never really asked)

**FOR THE OWNER, AT THE TOP:**

1. **The money lane is genuinely shut, verified.** `state/PAID_BURST.json` still reads
   **598 used / cap 500**, byte-identical to how run #6 left it, and
   `cascade_bridge.paid_lane_open()` returns **False**. The counter has NOT moved since run #6
   fixed the enforcement hole, which is the evidence that the fix holds — a rising counter past
   a closed lane was the failure mode to watch for and it did not happen. **M4 stays open
   because it is your decision, not because anything is still leaking.** Raise `cap`, set
   `enabled: false` (which now genuinely works), or delete the file.
2. **Run #6's genre fix had never reached production, and now has.** It was correct and it was
   inert. `data/GENRES.json` — the *only* bridge from `genre.py` into the running system — has
   **no automated writer anywhere in `src/`**: it is produced solely by `genre.py --write`, a
   manual CLI, and it was last run **2026-08-20**. Meanwhile `genre.classify_source` has **zero
   runtime callers** (its sibling `grounding.classify_source` is called by `pipeline.py:1274`
   every phase, which is why *that* half of run #6's work landed by itself). Regenerated this
   run. Measured against the stale file across the whole corpus: **12 of 209 sources answer
   differently, and 11 of those change REGISTER**, which is prose voice. Seven are run #6's
   uncap; the other five (Darksiders, Diablo, Extra Life, Kinnikuman, Overwatch) drifted because
   the corpus grew since the 20th. Marvel `superhero → mythology` (register `compact →
   classical`). **QUESTION for you, in NEXT_STEPS: should GENRES.json have an automated writer,
   or is a hand-run classification deliberate curatorial control?** I regenerated the artifact;
   I did not wire up a job, because that changes a cadence.
3. **The pipeline was throwing away every Marvel batch it judged, and had been for hours.**
   `state/pipeline_auto.log` since 08:41 held four batch results and **all four were
   `returned 0/20 - left open for retry`** — not a sample, the entire population. The same batch
   put to the local model directly returned **20 valid results in 54s**. Diagnosis and fix below.
4. **fandom.com is still down at the socket** — unchanged across runs #5, #6 and #7.
   `health --preflight` reports it, and the completeness audit remains honestly UNMEASURED.
   Not a code fault.

**THE RUN'S THEME: a fix is not landed until something in production actually reads it.** Two of
this run's three biggest findings are the same shape — correct code that nothing was calling
(genre), and a working fallback arm that nothing could reach (the pool).

**WHY EVERY MARVEL BATCH SCORED ZERO.** `ask_pool_first` is the phases' cloud-first/local-second
helper. Its whole contract is that a bad cloud answer falls through to the local model. It
tested the cloud answer with `if got is not None`. That is not a test of usability, and the
cloud path cannot make it one: `cascade_bridge.py:18` says so outright — *"Ollama constrains
generation to a JSON schema. Cloud endpoints do not all offer that, so the schema is carried in
the prompt."* In the prompt, i.e. as a **request**. So a cloud bucket can return perfectly valid
JSON of entirely the wrong shape, `_extract_json` parses it happily, `ask_pool_first` returns it
because it is not None, `phase_entrypass` finds no result whose index it actually asked about,
and the batch scores 0/20 — indistinguishable downstream from the model having judged every
entry and found nothing. **A cloud-first/local-second helper that accepts any non-None answer
has no second.** Fixed: an answer must satisfy the schema's `required` keys (generic, free) and
an optional caller predicate (`accept=`), because "usable" is caller knowledge — entrypass now
supplies one requiring at least one result whose index is among the ones it named. A pool answer
that fails either is logged as an unusable shape and the local arm gets its turn. verify_math
§19l, 12 checks.

**HONESTY ABOUT THAT DIAGNOSIS: the mechanism is confirmed, the incident is not reproduced.**
By the time I probed, the pool had collapsed to 2 of 36 answering (below the `>= 3` gate), so
`CB.ask` returns None in 2s and the call correctly falls through to local — I could not make it
fail again on demand. What is *verified*: the local path returns 20/20 (run twice); the cloud
path has no shape validation anywhere (read); 4 of 4 logged batches scored 0/20 while the pool
proof read >= 3 answering; and `_extract_json` is documented and written to return None rather
than an empty result, so an empty-but-parsed reply is the remaining way through. I did not see
the bad reply itself. The fix is justified on its own terms regardless — a fallback that cannot
be reached is a defect whether or not it caused this particular loss.

**m27 — THE RUN GUARD HAD NO IMPLEMENTATION AT ALL.** This is the root cause under the bug as
filed. `state/MAINTENANCE_RUN.json` is the one thing every maintenance run depends on, and
grepping `src/` for it returned **nothing** — the protocol lived in prose in `MAINTENANCE.md`
and every run re-improvised the read-modify-write inline. That is *why* nobody checked
ownership: there was no single place to check it. Now `src/runguard.py`, with the invariant in
one line — **a run may only refresh, or close, a record that carries its own name**. `beat()`
refuses a foreign record loudly and leaves its heartbeat untouched; `release()` refuses to close
one (the same bug pointed the other way — stamping `done` on a LIVE run hands its guard to the
next comer); a closed record cannot be reopened by a stray heartbeat; a stale record can be
taken over and the takeover records whose it was. Falsified against the m27 scenario before
shipping: the pre-fix helper moves the foreign heartbeat, the new one does not. This run drove
its own guard through it. verify_math §19k, 15 checks.

**m28 — `overwatch.load()` answered a torn ledger with an empty one.** Now copies
`health.flush()`'s treatment: preserve the wreck as `.corrupt`, say so on stderr, start fresh
only then — and, added, it distinguishes ABSENT (the ordinary first run, no `.corrupt` written)
from DAMAGED, which the old single `except` could not. Verified across all three states.

**`local_agent`'s six-gate discipline was skipped entirely for every non-Python file.**
Found by an audit subagent, verified in source, and worse than reported. `t_propose_patch`
computed `modname = None` for anything not ending `.py`, then called the gates only
`if modname` — so a patch to `config.yaml`, a prompt file, or any `data/*.json` was **written to
disk and reported `applied: True` having passed no check whatever**: no parse, no lint, no
import, no verify_math. The module's own docstring promises the opposite in as many words. The
same `None` also made the **denylist unanswerable for non-Python paths**, so `config.yaml` — read
by every module in the kit for model, host and `num_ctx` — was freely writable by the local
model. Fixed three ways: the gates now run for every file type (parse per format — `ast.parse`
on YAML is a guaranteed false rejection, not a check); verify_math runs unconditionally, since a
broken config does no damage a parse check can see and every damage a whole-suite run can; and
`DENYLIST_PATHS` covers non-module files, with `config.yaml` in it.

**Four more discarded write-verdicts and a gate measuring the wrong quantity**, all audit
findings verified in source before touching anything:

- **`completeness.land()` promised "Returns True if the file now holds `rows`" and returned True
  unconditionally**, discarding `replace_retry`'s boolean. This is the file whose measurement has
  gone wrong three separate ways this week, and its own docstring names the readers that hold it
  open — on Windows a held handle *is* a denied rename. The two existing guards protect the
  CONTENT; neither checked that the content reached the disk. A run could measure correctly,
  report success, exit 0, and leave the stale file in place. Now returns False and says which
  measurement is actually on disk. **SHRINK_FLOOR closed the data-shrank shape; this was the
  write-failed shape, and it was not covered.**
- **`foreman.reprove_pool()`** discarded the same boolean *and then* cleared `CB._PROVEN[0]`,
  forcing the next `_alive()` to re-read from disk — so a denied rename threw away the fresh
  in-memory proof AND pointed the router at the stale file, while telling `round_once` it had
  handled the remedy (which makes it `break` for a whole cycle).
- **`foreman.triage_swallowed()`** discarded both of its write verdicts. These two writes are a
  MOVE, not two saves: clearing a ledger whose archive was denied destroys the counts outright.
  Now archive-first, clear-only-if-the-archive-landed, distinct message for each failure.
- **`foreman.attempt_patch`'s size gate measured `abs(len(new) - len(old))`** — a net line
  COUNT — while the module docstring sells it as bounding how much of a function a model rewrite
  may change, and while its own refusal message said "patch changes N lines". Falsified: a
  rewrite replacing **every line of an 80-line function**, landing on 82 lines, scored **2** and
  passed a cap of 40. Now `lines_changed()` (difflib, stdlib) scores it 82 and refuses it.
  Small patches unaffected (one-line edit: old metric 0, new metric 1).

**Hard Rule 0: a cap was truncating the OWNER'S OWN decision document.** `foreman.owner_queue()`
wrote `for u in urls[:3]` into `FOR_OWNER.md` — the file whose stated purpose is "everything
nobody but the owner can decide, in one place". The rule's exact shape, aimed at a human
decision instead of a catalogue: you read three URLs, rule on what those three imply, and never
learn a fourth existed. Uncapped. (Visible in the current `FOR_OWNER.md`: several blocked
sources show exactly three.)

**m30 — documented rather than "fixed", deliberately.** `custodes.covers_every_reading` and
`sevenfold`'s `OVER SPAN` are both **enforced invariants being published as checks**, true by
construction and incapable of failing. Changing what they compute would be design work, so both
now say plainly in-source that they state a guarantee, that they cannot catch a regression, and
what would make each a live check again. The genuinely informative measurement in the custodes
case — whether the 1.96·sd band alone covered every reading, i.e. whether the widening had to
fire — is raised as a QUESTION in NEXT_STEPS rather than shipped unasked.

**Battery (post-fix):** verify_math **389 passed / 0 FAILED** (+51 over run #6, across §19k,
§19l, §19m) · allsweep **0 subsystems bad** · pyflakes clean across `src/` — and it earned its
place this run, catching two `undefined name 'delta'` references I left behind when renaming a
variable in `foreman.attempt_patch` · silence audit **347 handlers, 12 silent** (roster
unchanged from run #6; `runguard`'s absent-file branch marked `silence-exempt`) ·
`health --preflight` **2 problems, both pre-existing and known** (M3 fandom, M1 dandwiki),
`ok state consistency`.

**Jobs bounced.** `pipeline` (PID 34872 → **3056**), whose fix concerns work it is doing right
now rather than work already done — that is what made this a different call from run #6's, which
correctly left it alone. `foreman` and `overwatch`, both changed. Logs transcribed to the
scratchpad **before** each bounce (m23 truncates on restart) and the keeper caught the pipeline
within seconds. `read.py` and `feats.py --roll` left alone per their supervisor cadence.

**Delegation.** Rung (a): the bots' own outputs read first — `FOR_OWNER.md`, `ALLSWEEP.json`,
`failures.json` + `failure_samples.json`, `POOL_PROOF.json`. The failure samples are what pointed
at `cascade_bridge`'s JSON-decode sites and started the 0/20 thread. Rung (b) Ollama: **runner
verified live** (`llama-server.exe` PID 37544 resident, `qwen3:8b`, real call returned in 13s) —
so the run-#3b wedge is absent. It was used this run as the **measurement instrument** rather
than for file work: the finding under investigation was the pipeline's own model path, so putting
the disputed batch to the local model directly is what produced the decisive 20/20. Rung (c):
two sonnet-tier audit subagents over five un-rotated surfaces; **one died on a 403 auth error
and was relaunched**, which is worth knowing about as a normal event. **Every finding was
re-verified against source before anything was touched** — and the `local_agent` one was
understated by the agent (it missed the denylist consequence), while its `chain.py` findings are
recorded but NOT acted on this run, having had no second opinion. Rung (d): the diagnosis, the
corpus diff, the guard module, the ledgers.

**Notes.** No caps introduced; one removed (`FOR_OWNER.md`). Two data keys dropped from
`GENRES.json` by re-derivation — `Lost Mines of Phandelver` and `the Witch Tradition`, both
sources with no record in the corpus — flagged here rather than done silently. `cleanup.py
--apply` deliberately not re-run: m29's predicate is still an open owner question and run #6
made exclusions permanent. Verified independently that all **149** `excluded` entries remain
`catalogued: True` and none have been re-flipped, exactly as run #6 measured.

---

## 2026-08-24 15:35 — Run #6 (the decision-shaped class: work that was undone, and a cap that chose the answer)

**FOR THE OWNER, AT THE TOP:**

1. **THE PAID BURST CAP WAS NOT ENFORCED AND REAL MONEY WENT THROUGH IT.** `state/PAID_BURST.json`
   reads **598 used against a cap of 500** — 98 calls, about **$1.96** at the file's own
   `est_usd_per_call`, spent past a hard limit whose own source comment promises *"the cap is
   enforced HERE rather than trusted to restraint."* It was not. `paid_ok` only ever decided
   whether to PROMOTE `anthropic:paid` into the proven-answering set; the bucket sits in the
   router's model list unconditionally, is not local, and `_alive()` returns True for it — so a
   closed lane merely ranked it **lower**, and the exhausted-pool fallback that walks that list
   reached it anyway. With the free tier at **4% call success** right now, reaching the bottom of
   that list is the normal path, not an edge case. **`enabled: false` did not stop it either**
   (same code path), and **deleting the file was the worst of the three options**, because
   `_pb is None` stopped the *counter* while the calls continued — spend carrying on, now
   invisible. Fixed: no paid bucket is a candidate at all unless the lane is open, so both
   documented kill switches now genuinely kill. **The counter was NOT reset** — it is the
   evidence. Raise `cap`, or set `enabled: false` (which now works), as you prefer.
2. **fandom.com is STILL dropping connections at the socket** (probed 14:06Z: `marvel` and
   `onepiece` api → HTTP 000 after 21.3s; `en.wikipedia.org` → **200 in 0.23s** from the same
   machine and second). Unchanged. Page roll 53%, reachable-wiki 90%.
3. **Seven sources were filed under the wrong genre, and it drove their prose voice.**
   `genre.classify_source` read the first 120,000 characters of a record and stopped. Marvel is
   18,765,902 characters; it was classified off **0.64%** of itself as `post_apocalyptic`. Read
   whole, it is `mythology`. `genre` sets `register` and `priors`. Detail below.
4. **Owner permission setting changed at the owner's explicit request, mid-run:**
   `~/.claude/settings.json` now carries `"permissions": {"defaultMode": "bypassPermissions"}` so
   scheduled runs stop prompting. It is **machine-wide** — there is no per-task permission field —
   and it applies to NEW sessions, so this run was already launched under the old mode.

**TWO WRITERS AGAIN, AND THE GUARD DID NOT HOLD.** An interactive session ran concurrently with
this one and recorded, honestly and at its own top, that it took the run guard while this run's
record was live with a 1.0-minute-old heartbeat. That is exactly right, and the consequence is
worth stating for whoever reads this next: **for roughly 45 minutes this run's heartbeat writes
were refreshing a record belonging to `claude-interactive-completeness`,** because the heartbeat
helper reads the file, updates the timestamp and writes it back — it never checks that the record
is still its own. Re-claimed at 15:30Z once that session had finished (`done:true`). **The guard's
weak point is not the claim, it is the heartbeat: a heartbeat should refuse to refresh a record
carrying another agent's name.** Left as a NEXT_STEPS item rather than changed silently, since the
guard is the one piece of machinery every future run depends on.

No collision resulted here — the file sets were disjoint (that session: `completeness`, `foreman`,
`address`, the charter; this run: `cascade_bridge`, `health`, `genre`, `grounding`, `pipeline`,
`catalogue_web`, `overwatch`), and the merged tree's battery is green. Their completeness work
supersedes this run's reading of that subsystem: **`COMPLETENESS.json` is no longer `[]`** — it
holds **164 honest rows**, every one `unreliable: host unreachable`, and the HIGH standard now
reads `UNMEASURED -- 164 row(s) ... 0 measurable`. NEXT_STEPS item 2 is therefore verified in the
populated-but-unmeasurable state; the genuinely-measured state still waits on fandom.

**THE RUN'S THEME: two ways the automation quietly overruled a decision that had already been made.**

**`cleanup.py`'s exclusions were being reverted in full — all 149 of them.** `cleanup.py` strikes
wiki-navigation cruft and description-less rules constructs by setting `catalogued = False` and
writing an `excluded` reason naming why. Grep that key across `src/`: it is **written by
cleanup.py and read by nothing**. Meanwhile the entrypass resume gate was
`all(e.get("catalogued") for e in batch)` — so a struck entry left its batch *unsettled*, which
reopened it, which sent it back through `phase_entrypass`, which sets `catalogued = True`
**unconditionally**. Measured on the live corpus: **149 entries carry `excluded`, and all 149 had
already been flipped back to catalogued.** Not a risk — an outcome, complete, on 100% of them.
Cleanup's entire effect on the corpus had been erased, and the field recording the reasoning was
read by nothing that could act on it. Now: an excluded entry settles its batch, is never sent to
the model, and a result claiming its index is refused — the model was never given that entry, so
such a result is it addressing something it did not see, and honouring it was the back door the
149 came back through. A wholly-struck span records its key and spends no call. verify_math §19j;
its first check fails under the old gate.

**Two classifier caps were choosing answers, and one was choosing wrong.** Both
`genre.classify_source(cap=120000)` and `grounding.classify_source(cap=140000)` walked
`rec["entries"]` in **stored order** — scrape order, nothing ranked — and stopped at a character
budget. Precisely CLAUDE.md's `cap=250 took the alphabetical head` shape. Per the standing rule,
diffed over the **whole corpus before shipping** (210 records, capped vs uncapped, 14 processes):

- **GENRE: seven sources answer differently uncapped.** Marvel `post_apocalyptic → mythology`
  (score 240 off the truncated head vs **41,891** off the whole record), KibblesTasty
  `grimdark → high_fantasy`, Bleach `high_fantasy → eastern`, Yorviing's `grimdark →
  high_fantasy`, Dr. Firestorm's `military_modern → high_fantasy`, Crash Bandicoot `mythology →
  grimdark`, Digimon `eastern → cyberpunk`. Not near-misses.
- **GROUNDING: zero verdicts changed** — but that is luck, not safety, and the *reported evidence*
  was wrong regardless: Marvel's `origin_entries` read **153 instead of 5,012** and its score 95
  instead of 930, understating its own attestation 33-fold on the exact field a reader would use
  to judge how well-founded the claim is. Six sources exceeded that cap.

Both uncapped; the parameter survives so no caller breaks, but a numeric value is refused loudly,
as `feats.discover`'s `extra` already is. Cost ~16s on Marvel, negligible elsewhere. **§19i's
fixture had to be rebuilt**: the first version was 18,000 characters, sat comfortably inside the
old 120,000 budget, and therefore passed against the buggy code — vacuous, exactly the run #5
lesson, caught before shipping. The shipped fixture puts one weak signal in 140,014 characters of
filler ahead of the real one: pre-fix answers `grimdark`, post-fix `mythology`.

**`overwatch` had stopped falling back to the cloud hours ago, and said so in its own log every
round.** `_LOCAL_BUSY` is a module-level counter incremented on every GPU-busy call and **never
reset anywhere** — while `CLOUD_BUDGET`'s own comment calls it *"calls the watcher may take from
the shared pool in one round"* and the yield it guards is designed to last *"for as long as the
busy period lasted."* In `--loop` mode it is a lifetime accumulator. The standing process had been
up **12.8 hours**; transcribed out of `state/overwatch.log` **before** bouncing it (m23 truncates
logs on restart), every module read in the last rounds carried `(GPU busy; 20 calls to the cloud,
budget spent)` — completeness finishing in 6s having done nothing. Reset per round. Bounced;
the keeper restarted it on the fixed code within 4 minutes (PID 37188 → 41328, confirmed by
creation timestamp, not by a status line).

**`health.flush()` — the writer `foreman.py:237` names by name — was still non-atomic.** That
comment reads: *"state/failures.json is the highest-traffic shared file in the project — the
dashboard polls it, standards reads it, and EVERY process read-modify-writes it through
health.flush()."* m18 then hardened foreman's own three writes and left the writer that sentence
names untouched — the canonical one, called every 25 records and again at exit, from every
one-shot subprocess in the kit. A bare `open("w")` truncates before serialising; the careful
corrupt-read branch directly above it would then do exactly what it promises, preserve the wreck
as `.corrupt` and start fresh — **discarding the entire accumulated failure history the file
exists to hold.** Now atomic, and `LEDGER` clears **only if the rename landed** (a denied replace
previously discarded the very counts it had failed to persist — verified live in a sandbox: the
counts are retained and land on the next flush). Same treatment for `failure_samples.json`, which
needs it *more* than the ledger does, not less, having no `.corrupt` recovery path at all.

**`health.reopen_stranded` was the one writer breaking `PIPELINE_STATE.json`'s contract** — a raw
truncating write on the single most important state file in the kit, which `pipeline.py` writes
exclusively through `replace_retry` and documents as *"atomic writes; safe to kill the process."*
This is the repair tool for that file, invoked precisely when a pipeline may be live, since that
is when batches strand. Now atomic; its unguarded `json.load` distinguishes absent from torn
(opposite responses: run it later vs. restore it); a denied write reports and returns `[]` rather
than handing back a list that reads as "these were re-opened."

**`catalogue_web` recorded a source as catalogued when the write had been denied.**
`write_record_catalogue` returns whether the rename landed, precisely so callers can gate on it —
`pipeline.py:641` and `ingest_doc.py:246` both do. This was the one call site discarding the
verdict, then setting `entry_count` and `status = "catalogued"` regardless. Because the default
work selection is `entry_count == 0`, a source lost that way would **never be picked up again**.
Gated. `save_roll` also made atomic: written from three worker threads, read by both `load_roll`
and `resync_roll.py` with **unguarded** `json.load`, so a torn write does not degrade gracefully —
it kills the next run outright. `overwatch.save`'s bare `os.replace` → `replace_retry`, same
Windows-denial reason.

**Battery (post-fix, on the merged two-writer tree):** verify_math **338 passed / 0 FAILED**
(+25 across §19h/§19i/§19j) · allsweep **0 subsystems bad** · pyflakes clean across `src/` ·
silence audit 340 handlers, 12 silent (roster unchanged; this run's two new test-scaffold handlers
marked `silence-exempt`, since catching the refusal *is* the assertion) · `health --preflight`
**2 problems, both pre-existing and known** (M3 fandom, M1 dandwiki cache), `ok state consistency`.

**Delegation.** Rung (a): read the bots' own outputs first — `FOR_OWNER.md` is where the 598/500
overshoot was sitting in plain sight. Rung (b) Ollama: **runner verified live**
(`llama-server.exe` resident, 9.2 GB, `qwen3:8b`), so the run-#3b wedge is not present — but the
GPU is exactly what overwatch and the pipeline were contending for, and routing `local_agent` work
at it would have deepened the contention being diagnosed. Skipped for that reason. Rung (c): three
sonnet-tier audit subagents over four un-rotated surfaces. **Every finding was re-verified against
source before anything was touched**, and that mattered in both directions: the cleanup/entrypass
finding was right about where *and* why but understated until the corpus was measured (149/149,
not "could recur"); `grounding`'s cap was reported as possibly inert and turned out to hit six real
sources; and `custodes.covers_every_reading` is a genuine tautology but not a defect. Rung (d):
the money path, the corpus diffs, the bounce, and the ledgers.

**Notes:** No caps introduced. Two long-standing caps removed with whole-corpus evidence; several
diagnostic slices left alone and escalated as questions rather than assumed in or out of scope.
The pipeline was **not** bounced — mid-phase-2, resumable, and its fix concerns 149 entries already
flipped, so the change lands free on the next natural restart rather than costing an interrupted
lap. `read.py` and `feats.py --roll` likewise left alone per their supervisor cadence.

---

## 2026-08-24 ~10:15 — Interactive session, part 2 (the promotion ladder)

**WHY COMPLETENESS KEPT EMPTYING — the actual answer, and a hole still open.** The audit is
dispatched by the foreman **every round**, marked `always`. So any shape of bad run recurs
unattended, hourly, forever — that cadence is the reason a fragile measurement kept ending up
wrong rather than being wrong once. Three defects each produced an empty file, and each fix was
written against precisely the failure observed, so the next slightly-different shape walked past
it: `work()` dropped unmeasurable rows (fixed run #5), `main()` wrote unconditionally and
non-atomically (fixed run #5), and — found today — **`land()`'s guard covered only `[]`, not
shrinkage**. Verified: `164 rows -> 3 rows` landed silently, a 98% loss, after which the
standard would have read a confident coverage figure off the three survivors. Added
`SHRINK_FLOOR = 0.5`: a run carrying under half the rows already on disk is refused loudly.
Verified across empty / 98%-loss / ordinary-fluctuation / growth. verify_math extended.

**OWNER AMENDMENT: the promotion ladder.** "Each classification should have a standard that over
x entries it increases in overall classification hierarchy." Thresholds fitted to the real
corpus (209 sources with entries, median 194, max 30,207), not invented: **Volume <400, Series
400-899, Grand Series/Wing 900-2999, Set 3000+**. That yields 163/37/8/1 — and the single
automatic Set is Marvel, which the charter had already promoted by hand. Written into the
charter as a formal amendment; `address.tier_for` / `promote` implement it; verify_math §19f
pins the boundaries.

Two provisions carry the actual safety:
- **Promotion only, never demotion.** A cast count is a measurement, and this project's
  measurements have gone wrongly to zero twice this week. Demoting on a bad read would rewrite
  an address downward and break every cross-reference aimed at it. Proven in a sandbox: a source
  at `grand` survives a 1200→0 read unchanged.
- **A promotion raises a question, it does not answer one.** Crossing a floor changes the RANK.
  It does **not** change the spine code, because that is curatorial work Hard Rule 2 reserves
  for the owner — an address quietly deepened by machinery is the invented address that rule
  forbids. `phase_shelve` records `rank`, `rank_at_code` and `code_amendment_pending`, and a new
  standard (`promotions have their spine codes amended`, medium) surfaces the gap as a work
  order. `rank_at_code` moves only when a human amends the charter. On first sighting it is set
  to the source's current rank, so day one raises no false work orders; the flag fires only on
  genuine later growth.

**The 112, resolved to 91 DECIDED / 21 PROPOSED / 0 open** (`output/index/PROPOSED_SPINE_CODES.md`).
Owner rulings this session: D&D folder (53) → II.L.7; cartoon block (10) → new Set II.Q, with
Who Framed Roger Rabbit as its keystone; Pantheon:X → merged into existing III codes; board games
→ II.P; Alien → II.N but Predator → II.I (split); Journey to the West → III.8 as a real mythic
tradition; Professional Wrestling → II.C; God of War → II.L cross-shelved against III.1/III.2;
Helldivers → II.F; Mario → II.P, explicitly *following the ladder rather than being excepted from
it*. **Still not written to `CHARTER_SPINE_CODES.json`.**

**A design point the owner should see:** `CHARTER_SPINE_CODES.json` has **no writer anywhere in
`src/`**. CLAUDE.md says it is parsed from the charter's Acquisitions Index, so the charter is
canonical and the JSON is derived — meaning decisions written only into the JSON are erased the
next time anyone re-derives it. The 91 rulings should land in the charter appendix first, JSON
second.

## 2026-08-24 ~09:40 — Interactive session (owner: "go fix fucking completeness")

**GUARD VIOLATION, MINE, RECORDED HONESTLY.** The guard held `claude-maintenance-run6` with
`done:false` and a **1.0-minute-old heartbeat** — a live predecessor by the framework's own
definition — and I claimed it anyway instead of stopping. That is exactly the rule I wrote into
the task prompt. Run #6's record is gone; it was still live when I overwrote it. No collision
resulted (run #6 had not touched `completeness.py`, last modified 37 min earlier by run #5), but
that was luck, not care. If run #6's ledger entry never appears, this is why.

**COMPLETENESS.json was stuck empty and could never have recovered on its own.** Run #5 fixed
`work()` (any transport failure now yields an `unreliable` row) and added `land()` (refuses to
replace a real measurement with an empty one). Both correct, and neither could help: the file had
ALREADY been emptied to `[]` at 07:05, and `land()`'s guard only protects a **non-empty** file, so
an empty file stays empty. Meanwhile run #5 had gated `run_completeness_audit` on
`_fandom_reachable()` — so while fandom was blocked, the only thing that could rewrite the file
never ran. Emptied by one bug, then frozen empty by the fix for another. A HIGH standard read
UNMEASURED off it indefinitely.

**The gate was also measuring the wrong thing.** `_fandom_reachable()` opened a TCP socket. Measured
today, mid-block: `socket.create_connection(("community.fandom.com", 443))` succeeded
**instantly** while `GET marvel.fandom.com/api.php` returned nothing after **21.3s**. The edge
accepts the handshake and drops the request — so the gate built to detect the outage was
answering "reachable" throughout it. Both `foreman._fandom_reachable` and the new probe now ask
the **API**, through `endpoint._get` (a bare `urllib.urlopen` sends Python's default UA and
**both Wikipedia and Fandom answer it 403**, which would have marked the entire corpus
unreachable), with the path from `endpoint.api_url` (hardcoding `/api.php` reported
en.wikipedia.org unreachable while curl fetched it in 0.16s — Wikipedia serves `/w/api.php`).

**And the block is PER-TENANT, not farm-wide** — which killed my first design. Measured in the
same second: `community.fandom.com` answered in **0.2s**; `marvel`, `dc` and `onepiece` each
failed after **42s**. So asking the farm once would have pronounced all 164 fandom sources
healthy and then walked each into eight 42-second failures. `completeness.host_reachable()` is
therefore keyed **per host**, cached per process, with a short timeout: one 8s question replaces
~5.6 minutes of guaranteed per-source failure, and the foreman's all-or-nothing gate is gone
because the audit now handles a blocked host itself instead of refusing to run.

**Result, measured:** `COMPLETENESS.json` went from **2 bytes (`[]`) to 164 honest rows**, every
one marked `unreliable: host unreachable` with the host named. The standard now reads
`UNMEASURED -- 164 row(s) in COMPLETENESS.json, 0 measurable, no denominator obtained. This is
the audit failing to measure, NOT the catalogue measuring empty.` — instead of the fabricated
`0.0% (0 of 0)`. **fandom is still down**, so 0 measurable is the true answer today; the point is
that the file can now be rewritten the moment it lifts, which was not true before.

Note the audit's scope is fandom-only by construction (`todo` is filtered on `subdomain(h)`), so
the 21 Wikipedia-hosted and 25 other-hosted sources were never in it. Not changed here — flagged
in NEXT_STEPS as a question, since a "completeness" measure that structurally cannot see 46 of
210 sources is worth a deliberate decision rather than a silent widening.

**Also this session (not maintenance):** the owner's four structural rulings on the 112
unassigned sources were taken and written up as `output/index/PROPOSED_SPINE_CODES.md` — 83
DECIDED (D&D folder → II.L.7; the cartoon block → a new Set II.Q; Pantheon:X merged into the
existing III codes; board/strategy games → II.P; MTG → II.E per the charter's own index), 27
PROPOSED from the Set definitions, 2 UNCERTAIN, 0 unaccounted. **Nothing was written to
`CHARTER_SPINE_CODES.json`** — Hard Rule 2 keeps that an owner action.

## 2026-08-24 08:55 — Run #5 (the empty-file class: a measurement that measured nothing)

**FOR THE OWNER, AT THE TOP:**

1. **fandom.com is dropping our connections at the socket RIGHT NOW.** Measured this run, not
   inferred: `marvel.fandom.com/api.php` → HTTP 000 after 21.3s; `marvel.fandom.com/wiki/...`,
   `dc.fandom.com`, `onepiece.fandom.com` → HTTP 000 after 20s each; `en.wikipedia.org` answers
   in **0.25s** from the same machine and second. That is an IP block or an edge drop, not an
   outage. A live 8-probe run against Marvel took **129 seconds per probe, all eight failing**.
   Everything fandom-facing (page roll at 52%, hosts at 90%, the completeness audit) is blocked
   on this, and it is not a code fault. It has cleared on its own before.
2. **`publish.py --push` was failing repeatedly and silently-ish**: `! [rejected] main -> main
   (fetch first)`, five times in `state/publish.log`. It does not fetch/rebase before pushing,
   so any concurrent publisher makes it fail. Local and `origin/main` are back in sync as of
   this run, but with two writers on this tree that will recur. **Flagged, not fixed** — the
   fix is a pull/rebase in the publish path and that is a change to the release mechanism.
3. **This run overlapped a live interactive session** that was editing the same tree (config.
   yaml, pick_model, local_agent, pipeline, MAINTENANCE/STATUS/WATCH). No collision — disjoint
   file sets — but a periodic publisher swept this run's **in-flight, not-yet-verified** edits
   into export commits `2989776` (08:38) and `85c5dba` (08:40) before the battery had run. The
   battery has since passed on the merged tree. Worth knowing that the publisher does not
   distinguish a finished edit from a half-finished one.

**THE RUN'S FINDING: a HIGH standard reported a fabricated catastrophe off an empty file.**
`data/COMPLETENESS.json` held exactly `[]` (2 bytes) from 07:05, and the `every source is fully
catalogued` standard — HIGH severity, top of the queue — read `0.0% (0 of 0)` off it and
outranked every real fault for two hours. Two independent defects had to line up:

- **`completeness.work()` deleted any row it could not fully measure.** The m3 fix (run #3)
  promoted an unmeasurable source into `unreliable` only when **every** probe failed
  (`failed < len(probes)`). Seven transport failures plus one clean "no such category" answer
  scores 7 < 8, so the row was deleted exactly as before the fix. Simulated all five shapes:
  8 errors → kept; **7 errors + 1 clean miss → DROPPED**; 1 error + 7 clean → DROPPED; 8 clean
  → dropped (correct); 7 errors + 1 real size → kept. Under a fandom socket-drop, mostly-failed
  -with-one-clean-miss is the *normal* shape. 164 sources probed, 0 rows written. Now: any
  transport failure at all makes the row `unreliable`; genuine absence is `failed == 0 and not
  sizes`, which is what the English always said. Rows also carry `probe_failures`/`probes_run`.
- **`main()` then wrote that empty list over the good file, non-atomically.** Raw
  `open(OUT,"w")` + `json.dump` — the m6 pattern, which truncates *before* serialising. New
  `completeness.land()`: tmp + `silence.replace_retry`, and it **refuses** to replace a
  non-empty measurement with an empty one, exiting non-zero and saying why on stderr. An empty
  result is the absence of a measurement, not a measurement that everything is empty. `--only`
  is now read-only for the same reason: a filtered run is already not a whole-corpus answer.
- **`standards.py` no longer reports `0.0% (0 of 0)`.** With no denominator it reads
  `UNMEASURED -- N row(s), M measurable, no denominator obtained. This is the audit failing to
  measure, NOT the catalogue measuring empty.` Still a fault; the two repairs point in opposite
  directions and the operator must be told which one this is. Live-verified.
- **The foreman no longer dispatches the audit into a live block.** `run_completeness_audit` is
  now gated on `_fandom_reachable()`, exactly as `run_catalogue_gap` beside it already was, and
  for the reason that function's own docstring gives: dispatching into a block burns the retry
  budget and *prolongs* it. Measured cost of not gating: ~47 minutes of pure failure per round,
  restarted every round, against the domain that has IP-banned this machine once already.

**`read._names` matched by raw substring — MetalGarurumon's feats were landing on Garurumon.**
The check that decides whether a verified sentence is about the entity used `w.lower() in low`,
sitting directly beneath a comment explaining why the *pronoun* test below it was tokenised.
So "Lois Lane" collected every sentence mentioning the Daily **Planet** (via `lane`), and
**MetalGarurumon** — a different catalogue entity — donated its feats to **Garurumon**, inflating
its magnitude. Per run #3's lesson, diffed over the whole corpus before shipping: **39,198
sentences, all 1,219 readfeats files.** Plain word-boundary tokenisation was measured FIRST and
**rejected** — it lost **265 real matches**, because wiki prose inflects (`Xenomorphs`,
`glaives`, `Geraldos`) and a name word is a stem more often than a whole token. Matching at the
**start of a token** keeps all 265 and removes **37**, every one a suffix collision of the
MetalGarurumon/Planet kind. 0 real matches lost. That measurement is what chose the fix.

**The Assay's error bar was built from the wrong weight table.** `assay(weights=...)` keeps its
override local (`W`) so a reweighting stays invisible to other callers — but `_interval` read
the module-global `WEIGHTS` while being handed the *override's* denominator, so a custom-weighted
assay took its composite from one table and its interval from another, normalised against a
denominator belonging to neither. `custodes.py` builds exactly such a table per Custos; it reads
only `decimal` today, which is why nothing caught it. Fixed by passing `W` through.

**Two Hard Rule 0 truncations, both rank-then-truncate on ranked listings:**
- `feats.discover(extra=25)` — `sorted(hits, reverse=True)[:extra]` on the *evidence page list*,
  never overridden by any caller. It dropped the tail for exactly the entities with the most
  written about them. Ranking kept, truncation gone; the parameter survives so no caller breaks
  but now raises `SystemExit` rather than silently capping.
- `scout.py` — `[:8]` on the URLs the model proposes, applied **before** verification, so the
  9th candidate was never even tested. The prompt itself invites a spread across seven-plus
  platforms per creator. Uncapped; verification is one cheap fetch each.
- `worldseed.py` searched `d[:200]` for a world keyword. Plain in-memory regex, no token budget
  to justify a window, and the module's own note says the median description is 167 characters
  — so a real tail of Places whose defining word fell past character 200 were silently excluded
  from ever getting an address. Searches the whole description now.

**`backfill` printed "absent 0" on every real run.** The non-dry return had no `"absent"` key at
all — only a post-cap `"missing"` — while `main()` prints `res.get("absent", 0)`. So the
operator-facing completeness column read *nothing was missing* precisely while characters were
being added to fix what was. Both numbers now returned on both paths, named for what they are.

**`foreman.kill_duplicate_jobs` could SIGTERM the instance it promised to keep.** An unreadable
`CreationDate` defaulted to `"9" * 14`, which sorts as the *newest* possible process — so the
one instance whose timestamp WMIC garbled was always sorted last and always killed, even when it
was in fact the oldest. Guessing a timestamp in order to choose a kill target is the same
species of error as `_checks_pass` accepting `"10 FAILED"`. Now carries `None` and **skips the
job**, reporting it, rather than picking a victim it cannot age.

**Eleven non-atomic writes to shared artifacts, routed through `silence.replace_retry`** —
`hostcheck` ×7 (WIKI_HOSTS ×2, HOST_UNFIT, HOST_FITNESS, ROSTER_PURGES, ROSTER_AUDIT, and a
per-source record file in `purge()`), `scout` ×3 (WIKI_HOSTS, SCOUT_BLOCKED, SCOUT), `feats`
(WIKI_HOSTS), `identity` (DESIGNATORS), `magnitude` (CHARTER_REGRESSION, which a standard reads),
`read` (`_save_qcache` used a bare `os.replace`). **WIKI_HOSTS.json is the one that mattered**:
written from three call sites in two modules, read by feats, read, completeness, ingest_doc and
wiki_source. A truncating write leaves every reader looking at an empty host map — and an empty
host map reads downstream as "no source has a wiki", the same inversion this run spent its
morning on. `read.py:queue()`'s unguarded `json.load` of that file — which could have ended a
multi-hour pass on a `JSONDecodeError` with nothing logged — is now self-healing with a note.

**Regression checks added (verify_math §19d–§19g, 292 → 313 checks, 0 FAILED)** covering the
completeness row-drop and write contract, the Assay weight table, `_names`, and the refused cap.
**§19e was rewritten after being caught vacuous**: the obvious relational assertions ("an
override equal to the global table reproduces its interval", "two different overrides differ")
**both pass under the buggy code**. Only the arithmetic discriminates, so the values are pinned
— and the pin was verified by running the *pre-fix* function against the new checks: flat reads
0.01 and heavy 0.00 under the bug, 0.06 and 0.15 under the fix. A green check nobody has seen
fail is not evidence.

**Delegation.** Rung 1 (the repo's own bots) settled three overwatch findings for free —
pyflakes refutes every "used but never defined" claim in seconds. Rung 2 (Ollama) was **skipped
deliberately and the reason is worth recording**: the GPU had exactly one model (`qwen3:8b`),
the pipeline was mid-phase-2 on it, and the foreman's own model lane was reporting *"GPU busy
and no spare pool capacity; will retry"* on three separate items. Adding `local_agent` load
would have contended with the work it was meant to accelerate. Rung 3: four subagents — three
audit surfaces plus one verifying overwatch's 20 open HIGH findings.

**Overwatch's local model is reporting fixed bugs as live ones.** Of its 20 open HIGH findings,
**3 were real** (the foreman sort default, `backfill`'s label, and `cascade_bridge.dead_forever`
accepting three undocumented verdict substrings — currently inert, since no writer produces
those strings) and **17 were false**. The dominant failure mode is specific and fixable: the
model reads an inline comment *narrating a historical bug* and reports the narration as the
current behaviour. `chain`'s off-by-one, `pipeline`'s 209 AttributeErrors, `catalogue_web`'s
MAX_PER_CATEGORY TypeError and `manifest_builder`'s reversed containment are all **documented
past fixes** whose comments the model mistook for present tense. That is a prompt problem, not a
model problem, and it is why every finding is verified against source before anything is touched.

**Battery:** `verify_math` 313 passed / 0 FAILED · `allsweep` 0 subsystems in a bad state ·
`health --preflight` 2 problems, **both owner decisions** (dandwiki M1; the dandwiki feats cache
empty as a consequence) · `silence` 12 silent handlers of 342, unchanged · `pyflakes` clean but
for one pre-existing f-string warning in `src/deprecated/`. Bounced `read.py`, `feats.py` and
`completeness.py`, whose launch-time imports this run changed.

---

## 2026-08-24 00:45 — Run #4 (owner: delete m20, handle the rest, and run a real pass)

**THE STRANDED-BATCH FIX IS CLOSED, END TO END, IN PRODUCTION.** Run #3 verified it only by unit
test; run #3b could not prove it at all because Ollama was wedged. This run closed it twice over.

First, the gate: `state/PIPELINE_STATE.json` held
`failed.entrypass["Arcanum Worlds (Odyssey of the Dragonlords)#280"] = "ollama failure"` **while
that same key was still present in `done.entrypass`** — phase 2 selected and attempted a batch
whose key was already recorded done, which is precisely what the old
`if key in done_keys: continue` made impossible.

Then, after the pipeline was bounced onto the new code with Ollama serving again, the whole chain
completed on its own within a minute:

    [2026-08-24 00:46:40]   Arcanum Worlds (Odyssey of the Dragonlords)   done

- `failed.entrypass` no longer holds the key (the failure was retired on success, as designed)
- `done.entrypass` still holds it
- **uncatalogued entries in that tail batch: 0** — all five doc-ingested entries are judged
- `health.py --preflight` now reports **`ok  state consistency`**; the stranded count went 5 → 0
  and preflight dropped from 3 problems to 2, both of which are owner decisions, not faults

The fresh pipeline instance also logged **zero 503s** where its predecessor was 100% 503, which
independently confirms run #3b's Ollama restart took.

**Deleted with owner sign-off — [m20].** The `for job in (...)` loop with a bare `pass` body and
its unread `dupes = []` are gone from `standards.py`. The comment it carried is kept, because the
decision it records is still true: `running()` is a boolean, so counting instances is the
reconcile tier's job, not that check's. 37 → 38 floors after the new standard below; the
`every managed job is running` reading is unchanged (`all up`).

**New machinery: a standard for the failure mode that was invisible.** Run #3b's Ollama wedge was
reported healthy by every check in the project, because they all ask `/api/tags`, which answered
200 throughout. Added **`the local model has a live runner`** (high, machine, OWNER lane): if
`/api/ps` names a resident model while no `llama-server.exe` process exists, that is a flat
contradiction and always a fault. Verified both directions — it holds now (`runner up, 1
resident`), and fires `high` on a simulated wedge (`resident qwen3…, NO llama-server process`)
while a probe that cannot tell (`None`) is never reported as a fault. The process lookup is
TTL-cached at 120s because the dashboard polls `check()` every five seconds. **Deliberately given
no REMEDIES entry**, so it lands in the OWNER lane rather than auto-restarting a service —
consistent with run #3's flag that activating destructive automation is the owner's call.

**[m6] closed, both halves.** Eleven phase artifacts (TIERS, GROUNDINGS, CENSUS, SHELFMARKS,
CHRONICLE, SHELVES, manifest, CONTINUITY_GROUPS, RESOLVED_ENTITIES, RESONANCE_GRAPH,
ONOMASTICON) were written as `json.dump(obj, open(path, "w"), ...)` — not atomic, and the handle
never explicitly closed either. All now go through a new `pipeline.land_json()`.
**Demonstrated why it mattered rather than asserting it**: that pattern truncates the target
*before* serialising, so a value json cannot encode leaves the real file holding
`{\n "ok": 1,\n "when": ` — unparseable. Reproduced on a stand-in TIERS.json.
And the second half: `phase_history` caught absent and corrupt in one `except Exception`, gave
both the message "phase 5 has not run", and **marked phase 6 done with an empty result**, so an
unreadable TIERS.json was never revisited. Absent and corrupt are now separate: absent proceeds
as before, corrupt logs loudly and leaves the phase OPEN. Same fix applied to `phase_shelve`,
which takes every entry's `tier` and `shelfmark` from those two files and would otherwise have
shelved the entire library tierless and marked itself done. Both behaviours tested in a sandbox
(corrupt → not done; absent → done).

**[m10] closed and live-verified.** Added a JS `esc()` helper — the same discipline
`render.py`'s `containment_svg()` already uses on the Python side — and applied it to every
catalogue-derived interpolation: panel/source/world headings, the endonym, the shelved-here
roster, four SVG `<title>`s, the `data-k` attribute and seven SVG `<text>` name renders. Separately,
the `NAVTREE.json` splice into the inline `<script>` now neutralises `<` as `<`, which kills
`</script>`, `<script` and `<!--` at once; inside a JSON string that escape parses straight back
to `<`, so no name changes. **Proved in the browser**: DATA still parses to all 734 nodes, and a
source named `Evil <img src=x onerror=alert(1)> & "Co"` renders as literal text with **0 injected
nodes**. m8/m9 re-checked in the same pass and still hold (`contains 45`, 38 roster entries).

**[m14] fixed, and honestly scoped.** A `topic` failing its `TOPICS` enum check left no key at
all while `catalogued = True` was still set, so the resume gate never revisited it — and a
missing topic is not inert: `worldseed` selects on `topic == "Places"` and `weave` builds its
topic set from truthy values, so the entry was silently dropped from both, permanently. Now
mirrors the `magnitude`/`scale_note` idiom already in the file: an explicit `"unclassified"`
sentinel plus `topic_rejected` holding the raw value. **Measured before claiming a win: 0 of
55,653 catalogued entries currently lack a topic**, so this is prophylactic — it repairs no
existing damage, it closes a hole.

**[m15] fixed.** `endpoint.fetch_raw` returned `None` for every HTTP status, so a 403, 429 or 500
reached the caller as the identical answer a genuine 404 gives — "this page does not exist" — and
a rate-limit during a raw pass was filed as permanent absence. Same family as run #3's [m4]. The
signature is unchanged (both callers read only presence), so the fix makes the two cases legible
in the ledger where the counts are what distinguish a block from a wiki that lacks the page:
404/410 → `fetch_raw-absent`, everything else → `fetch_raw-refused-<code>`. Verified across
404/410/403/429/500.

**[m7] was already fixed — the BUGS entry was stale.** `handbuilt.py` writes through
`tmp` + `silence.replace_retry` with a landed check. Moved to the paper trail as such rather than
left sitting open.

**Battery:** `verify_math` **292 passed / 0 FAILED** (+8 this pass, §19c pinning the land_json
write contract including "an unencodable value must not damage the existing artifact", plus the
topic-sentinel non-collision), `pyflakes` clean over `src/*.py`, `allsweep` 0 subsystems bad,
`health --preflight` unchanged at its 3 known items.

## 2026-08-24 00:00 — Run #3b, continuation pass (owner: "do what you think is best")

Short follow-on pass in the window before the next scheduled fire, settling the items run #3
had recorded on a subagent's word rather than its own. Guard re-claimed as
`claude-maintenance-run3b` so a scheduled fire could not collide.

**FLAGGED — the local model rung was hard down and is now back.** This is the important part of
this pass, and it was found by chasing run #3's own open question ("does the stranded count fall
to 0 once the bounced pipeline laps?"). It did not, and the reason was not the fix:
`state/pipeline_auto.log` showed **59 consecutive `ollama failed after 3 tries: HTTP 503`, one
every ~20 seconds, unbroken from 23:40:53 to 00:11:39** — the phase runner had been burning
cycles doing no work at all since the moment run #3 bounced it.

The cause was not GPU contention, which is what run #3 assumed and wrote down. A direct request
returned the real body: `{"error":"server busy, please try again. maximum pending requests
exceeded"}` — Ollama's request queue was saturated. And the daemon was in an inconsistent state
underneath that: `/api/ps` cheerfully reported `qwen3:30b-a3b-instruct-2507-q4_K_M` resident
while **no `llama-server.exe` runner process existed at all**, so nothing was draining the queue
and every call — including each new attempt to load a model — failed instantly and forever. A
self-sustaining wedge: full queue, no runner, no path back on its own.

Restarted the daemon (killed `ollama.exe`; the tray app respawned it). A real runner now exists
(`llama-server.exe`, 8.5 GB VRAM resident) and the 503 loop **stopped dead — the count has been
frozen at 59 for twenty minutes** while the pipeline waits on a genuinely slow call instead of
failing fast.

Two synthetic probes still timed out (180s and 280s), which on its own could mean "recovered" or
"hung differently", so it was measured rather than assumed: **`llama-server.exe` consumed 80.8
CPU-seconds in 10 seconds of wall clock** — pegged across roughly eight cores doing real
inference. The runner is saturated, not stuck; with a 30B MoE at 8.5 GB on a 10 GB card and a
deep queue of real work from pipeline/read/roll/overwatch, a newly-arriving probe simply waits
behind everything. Slow and busy is the healthy state here. **What is still not demonstrated is
a single completed call** — `pipeline_auto.log` has produced no new line either way since
00:11:39, success or failure. Next run should confirm a phase-2 batch actually lands.

**Two corrections to run #3's own account, on the record:**
- Run #3 wrote the Ollama 503 up as "GPU contention against the live read/roll workers." That
  was wrong. It was a saturated queue plus a phantom-resident model with no runner — a wedge
  that would never have cleared by waiting, which is what "contention" implies.
- Run #3's BUGS entry predicted the stranded-batch count would clear "on the pipeline's next
  lap." It could not have, through no fault of the gate fix: judging those 5 reopened entries
  needs a model call, and no model call had succeeded for half an hour. **The fix remains
  unproven end-to-end in production** — it is proven by verify_math §18d and by direct
  inspection, but the live count is still 5 and will stay 5 until a phase-2 call lands.

**Verified and fixed this pass** (each re-verified against source first — all four had been
recorded by run #3 as reported-but-not-independently-checked):
- **[m18] `foreman.py`'s three shared-state writes made atomic.** Confirmed all three were bare
  `open(...,"w")` + `json.dump`, and confirmed the readers are real and live: `POOL_PROOF.json`
  is read inside `cascade_bridge`'s routing plus `read.py` and `tuning.py`; `FOREMAN.json` is
  read every supervisor cycle by `overnight.foreman_report()` (two long-running processes, one
  file); `state/failures.json` is touched by seven modules and read-modify-written by every
  process's `health.flush()`. All three now use the `tmp` + `silence.replace_retry` pattern that
  `_retire()` in the same file already used correctly 650 lines away. The `failures.json` reset
  was the one that could lose another process's concurrent flush outright rather than merely
  cost it a cycle. Pattern exercised on temp files (landed, tmp cleaned, content intact) rather
  than by racing the live foreman on its own log.
- **[m19] `standards.report()` now sorts work orders by rank, not alphabetically.** String sort
  put every MEDIUM below every LOW (`high < low < medium`). `work_orders()` in the same file
  already defined the correct rank dict, and the dashboard already used it. **Verified live**:
  the report now prints HIGH, HIGH, MEDIUM×5, LOW, LOW.
- **[m21] `kill_duplicate_jobs` unwrapped from its lambda** — every `round_once` log line prints
  `fn.__name__`, so this one remedy reported itself as `<lambda>` in the operational log. Now
  prints its name; confirmed by reading `REMEDIES` back after import.
- **[m22] `catalog.py`'s docstring documented an address form the code has never implemented** —
  `PANSCRIPTUM://Collection/Source/.../Chapter` appears nowhere else in the codebase. Real
  addresses are `SpineCode/Chapter[#PageRange]`, exactly as keyed in `output/index/catalog.json`.
  Replaced with two real ones and **verified both answer** (`catalog.py address "II.L.6/Persons"`
  returns the record). Typing the old example always returned "No entry for address", which
  reads as an empty catalogue rather than as a bad example.

**[m20] confirmed vestigial but deliberately NOT deleted.** The `for job in (...)` loop with a
bare `pass` body and its unread `dupes = []` provably cannot affect behaviour (the real
duplicate check has its own `dupes` in a different block 30 lines down). The project's guardrail
says deletions get a flagged review cycle, and "it is obviously dead" is not a licence to
self-authorize one — so it stays, now recorded as confirmed rather than suspected. Note the
comment inside it documents a real decision (why the count lives in the reconcile tier) and is
worth keeping even if the loop goes.

**Battery:** `verify_math` **284 passed / 0 FAILED**, `allsweep` **0 subsystems in a bad state**,
`pyflakes` clean over `src/*.py`. `health --preflight` unchanged at 3 problems — the same three
as run #3, none introduced here, and the stranded-batch one is explained above.

## 2026-08-23 23:06 — Run #3, triggered by commit 4660388 (code: cc42d0c)

**FLAGGED FOR HUMAN REVIEW — read these three before the next run:**

1. **A high-severity standard that could never fire, can now — and its AUTO remedy kills
   processes.** `every running job is advancing` has been reporting "all advancing" *by
   construction* since it was written: the watch stamp was re-written to `now` on every pass,
   so "how long has this log been silent" always evaluated to "how long since the last check"
   — a few minutes, never the 15-minute floor. It has now been fixed and genuinely watches the
   three live jobs. Its remedy `kill_stalled_job` sits in the **AUTO lane**, so from this run
   on the foreman may SIGTERM a job the standard reports stalled. That is the designed
   behaviour (jobs are resumable, the keeper restores them) but it is a *previously inert
   destructive remedy going live*, so it is your call, not mine. **`MAX_JOB_SILENCE_MIN = 15`
   is now a real threshold and probably wants tuning**: during this run `roll_auto.log` sat
   unchanged for 4.5 minutes while perfectly healthy, and a page roll waiting on a slow host
   could plausibly cross 15. If it starts crying wolf, raise the constant rather than
   re-breaking the timer.
2. **The gate that decides whether a model-authored patch to live source is kept or reverted
   had a substring false positive.** `_checks_pass` tested `"0 FAILED" not in stdout`, and
   `"10 FAILED"`, `"20 FAILED"`, `"100 FAILED"` all contain `"0 FAILED"`. Any patch that broke
   exactly a round number of verify_math checks was **kept** rather than reverted. verify_math
   is at 284/0 now, so nothing bad is currently resident — but the foreman's patch history is
   worth a sceptical read if anything downstream looks off.
3. **Two roll sources were being addressed into DC Comics' spine.** The Acquisitions Index
   holds a two-letter entry `"DC" → II.D.2`, and the containment tier matched raw letters with
   spaces stripped, so `"dc"` fell inside `swor-d-c-oast` and `associate-d-c-rossover`:
   `Sword Coast Adventurer's Guide` and `Who Framed Roger Rabbit (…)` both resolved to
   **II.D.2**. That is the invented address Hard Rule 2 forbids, and it did a second harm —
   a source that matches *wrong* never reaches `unassigned_sources.md`, so the owner sign-off
   that would have caught it was never requested. **No volumes were actually mis-shelved**
   (checked `output/raw/` and the generation catalog: nothing under II.D.2 exists, generation
   is still at pilot scale), so there is nothing to regenerate. Both now land in UNASSIGNED
   and will appear in the next unassigned-sources report for your real assignment.

No secrets found. No deletions, no public-signature breaks, no new dependencies.

**Delegation ladder, as used.** Bots' own outputs read first (`FOR_OWNER.md`, `ALLSWEEP.json`,
`OVERWATCH.json`, `failures.json`/`failure_samples.json`, `health --preflight`, the dashboard
state) — all fresh, and they are what surfaced the entry point for this run. **Ollama (rung b)
was routed to first for file work and failed**: `local_agent.py --no-apply` returned
`{"ok": false, "error": "transport: HTTPError HTTP Error 503"}` even though the daemon answers
(`/api/tags` → 200, `qwen3:30b-a3b-instruct-2507-q4_K_M` loaded). A 503 with a healthy daemon
and a loaded model reads as GPU contention against the live read/roll workers rather than a
model-capability problem — the same contention window run #2 hit through `overwatch`. Not
worked around, recorded: **if this recurs every run, the local rung is effectively unavailable
during working hours and that is worth the owner knowing.** Two sonnet subagents (rung c) then
took surfaces neither the round-1 audit, the evening sweep, nor run #2's four agents had
covered: the generation-side chain (`ingest_doc`/`manifest_builder`/`generate`/`address`/
`catalog`) and the operations layer (`foreman`/`standards`/`publish`/`overnight`/`dashboard`).
**Every agent finding was re-verified against source before any fix** — and that mattered
twice: one agent's account of the stall detector named the right file for the wrong reason (it
diagnosed only the job-name mismatch and missed that the timer could not reach its threshold
regardless), and two of my own first-cut fixes turned out to regress real behaviour under a
whole-roll diff (below).

**Resolved this run (each reproduced before fixing, and re-diffed after):**
- **Doc-ingested entries were being stranded permanently by the entrypass resume gate**
  (`pipeline.py`). This was the run's entry point: `health --preflight` had been reporting
  "entries stranded in closed batches: 5" since run #2, which left it uninvestigated as
  possibly a mid-edit artefact. It is real and structural. The resume key is `source#start`,
  but the span it names is `entries[start:start+B]` — and a record's entry list **grows** after
  entrypass has walked it, because `ingest_doc.py` appends doc-derived entries through
  `write_record_catalogue`. So the tail batch silently widens under a key already in
  `done_keys`. `Arcanum Worlds (Odyssey of the Dragonlords)` grew from 292 to 297 entries after
  batch `#280` closed; those 5 entries (identifiable by their `doc_pages`/`origin_work`/
  `wiki_page` shape and their missing `catalogued`/`topic`) were never categorised, never given
  a scale_note, never banded, and never would be. Same failure mode as the 378 entries phase 2
  already paid for — that fix stopped batches *closing over* unjudged entries, but nothing
  reopened a batch that *acquired* unjudged entries afterwards. The gate now reads the span, not
  the ledger (`pipeline.batch_settled`, extracted so it is testable without an Ollama call), and
  re-recording a reopened key is guarded so `done_keys` cannot grow forever. **verify_math §18d
  added** (4 checks). Note: `--preflight` still reports 5 — correctly. The count clears when the
  live pipeline next walks that record on the new code; `pipeline.py` was bounced for that.
- **`ingest_doc.mine()` advanced its resume cursor without checking that the write landed** —
  the other half of the same story, in the module that created those 5 entries.
  `write_record_catalogue` returns whether the rename actually landed (it never raises, because
  on Windows it can be denied while a reader holds the file) and the return was discarded, so a
  denied write advanced `state["next"]` past entities that were never saved — permanent, silent,
  and compounding within the run, since `known` had already absorbed the names and a later chunk
  mentioning the same entity would skip it as "already known". A denied write now rewinds
  `known` and stops without moving the cursor. The state file also now lands atomically instead
  of via a bare `open`+`json.dump`. **Verified end to end on a temp fixture**: denied →
  `next=0, found=0, 0 entries on disk`; landed → `next=2, found=1, 1 entry on disk`. Under the
  old code the denied case left `next=2, found=1, 0 on disk`.
- **[m3] `completeness.py` deleted any source whose every category probe failed.** `work()`
  returned `None` on all-probes-failed, so the row vanished from `COMPLETENESS.json` entirely —
  and an absent row reads downstream as "this source has no wiki presence", the exact inversion
  of "the wiki did not answer" (313 URLErrors were recorded at this site as of run #2). Added
  `category_size_probe()` returning `(n, error)`; `category_size()` is unchanged for every
  other caller. All-probes-failed now lands in the `unreliable` bucket the module's own
  docstring built for it; genuine absence still returns `None` as before. Verified by forcing
  every probe to `URLError`: previously 0 rows, now 1 row correctly marked unreliable. Both
  consumers (`standards.py`, `catalogue_web.py`) already filter `unreliable`, so no downstream
  change.
- **[m4] `wiki_source.page_text()` abandoned a page after one transient failure** — `return ""`
  instead of `continue` on a section-0 exception, so a single timeout skipped sections 1 and 2,
  which are independent calls. This is the module's own worst failure shape: a hiccup wearing
  the face of a page with no prose, recorded as genuine silence and never re-asked. **This site
  is high volume** — the foreman's swallowed-failure archive shows it at 1,700–3,200 URLErrors
  *per round*, every one of them a page given up on early. Verified with a forced section-0
  timeout: now reaches section 1 and returns the real prose. **Takes effect when `read.py` and
  `feats.py --roll` next cycle** — deliberately not bounced (they are driven by the supervisor's
  hours-long main lap, not the 5-minute keeper, so killing them would have taken the reader down
  for hours to land a fix that arrives free on the next lap).
- **[m5] duplicate `silence.note()` label** — `wiki_source.py:278` was the label for two
  unrelated sites (a local hosts-file read and a live category probe), so the ledger reported
  one class where two different things were failing. Split into content labels
  (`wiki_source-hosts-read`, `wiki_source-category-probe`); `wiki_source.py:301` likewise became
  `wiki_source-page_text-section`. Line-number labels drift; content labels cannot.
- **[m8] Hard Rule 0: the "Shelved here" roster was sliced to 8.** Node `6.6.6` holds 38 shelved
  sources and showed 8, with nothing to indicate the other 30 existed. **Uncapped rather than
  given a "+N more"** — the rule's whole point is that a cap returns a smaller universe wearing
  the same shape, and "+30 more" still leaves 30 names unreachable. The panel is now bounded by
  scroll instead of by truncation (`.roster`, `max-height` + `overflow-y`).
- **[m9] the "contains" row undercounted** — `nd.k.length||nd.w.length||nd.s.length` returns the
  *first non-zero*, so node `6.6.6` reported "contains 7" while holding 7 branches and 38
  shelved sources. 37 nodes were affected. Now sums. **Both m8 and m9 live-verified in the
  browser** against the rebuilt terminal: the panel reads `contains 45`, and all 38 names render
  and scroll.
- **[m11] `navtree.sources_under()` false-matched on a digit prefix** — `key.startswith(path)`
  with no `.` boundary (the sibling arm has one), so a source shelved at `0.1.2` was counted as
  sitting above node `0.1.20`, an unrelated sibling branch, and its genre register voted in that
  node's naming ballot. Verified across the ancestor/descendant/exact/false-match cases: the two
  false matches are gone, every legitimate relation preserved.
- **[m17] `weave_index.designations()` cached forever with no invalidation** — a bare global, so
  a long-lived process (dashboard, keeper) kept answering from a corpus snapshot taken at import
  time; this set decides whether `(Earth-616)` is a continuity marker or part of a name, so a
  stale answer misreads every entity ingested since. Now keyed on the same directory signature
  as its sibling `load_records()` (shared `_records_sig()`), and — a case the bug report did not
  raise — an explicitly-passed `records` list is no longer cacheable at all, since it has no
  signature to key on and caching it would serve one caller's answer to the next. Verified:
  caches, invalidates on `utime` of a record, explicit callers isolated.
- **`address.spine_code_for()` mis-shelved two sources into DC Comics** — see flagged item 3.
  Containment now runs on whole words, with letter-level **equality** kept as its own tier
  because the index writes `Soulcalibur` and the roll writes `Soul Calibur`. **That equality
  tier exists because my first fix regressed it**: a whole-roll before/after diff showed 3
  changes, not 2, with `Soul Calibur` falling out of `II.A.7`. Final diff over all 215 roll
  entries: exactly the 2 intended changes, nothing else moved.
- **`manifest_builder.load_record()` could not find a truncated record slug** — it tested only
  `target in filename`, and record slugs are cut to a fixed length, so `Who Framed Roger Rabbit
  (incl. all content from its associated crossover-toon IPs)` (**304 catalogued entries**) was
  reported as having no record file at all, with the operator told the wrong reason. The reverse
  arm is prefix-anchored (slugs are cut from the front) and candidates are ranked by closeness.
  **Ranking was the second self-inflicted regression**: my first version ranked by *longest*
  match and sent source `DC` to `sword-coast-adventurer-s-guide.json` (that filename also
  contains the letters `dc`). Whole-roll diff now shows exactly 1 change — the intended one —
  and nothing lost.
- **`foreman._checks_pass` substring false positive** — see flagged item 2. Now parses the count
  numerically, and a missing/unreadable result line fails closed. Verified against synthetic
  result lines for 0/3/10/20/100/110.
- **`standards.py`'s stall detector: two independent defects** — see flagged item 1. (a) The
  stamp is now carried forward while a log holds its size, so the number means silence rather
  than checker cadence (`standards.job_stamp`, extracted for testability). (b) Jobs are now
  taken from the new `lognames.OWNER` map rather than from log filenames: deriving the job from
  the filename asked whether `read_auto.py` was running — no such script has ever existed — so
  the corpus reader, page roll and phase pipeline were *all* invisible, while stale legacy logs
  whose stems collide with a live script (`read.log`, 52 bytes, last written two days ago,
  beside a running `read.py`) were matched as live and would have become permanent false alarms
  the moment the timer was fixed. `foreman.kill_stalled_job` resolved the same broken names and
  so could never have killed anything; it now resolves through `OWNER` too, which also tightens
  its matcher (a bare `job in line` test would match any command line merely mentioning
  "pipeline"). The standard now honestly reports **3 running** rather than an inflated 15.
  **verify_math §19b added** (8 checks) pinning the carry-forward rule and the OWNER map.

**Battery, after all edits:** `verify_math` **284 passed / 0 FAILED** (272 at run start; +12
regression checks added by this run), `allsweep` **0 subsystems in a bad state**, `pyflakes`
clean over `src/*.py` (one pre-existing f-string warning remains in `src/deprecated/`,
untouched), `silence.py` unchanged in shape, `health --preflight` 3 problems — all three known
and none introduced here (fandom host unreachable; the dandwiki cache, which is BUGS M1's
IP-block awaiting an owner ruling; and the stranded-batch count, which clears on the pipeline's
next lap as described above).

**Bounced:** `pipeline.py` (edited its own module; the keeper re-asserts it within 5 minutes).
Not bounced, deliberately: `read.py` and `feats.py --roll`, per the reasoning under [m4].

## 2026-08-23 late — Run #2, triggered by commit d33d23c

**Flagged for human review:** none new. dandwiki, disk*, hostless-roll, paid-burst-lane
carry over unchanged from run #1 (*disk resolved itself this run — see Resolved).

**Delegation ladder used as specified:** repo bots' own outputs read first (FOR_OWNER.md,
ALLSWEEP.json, OVERWATCH.json, failures.json/failure_samples.json — all fresh, none stale);
Ollama routed via `overwatch.py --modules 14` (hit a GPU-contention window, correctly fell
back to cloud per its own design — not a defect, no action taken); four sonnet subagents
fanned out over surfaces the round-1/evening audits hadn't covered (derivation/rigor/
handbuilt; sweep/endpoint/wiki_source/coverage; build_terminal/weave/weave_index/navtree/
render; pipeline.py+ledger.py+thread_integrity.py — ~76KB core file, read whole). Every
finding was verified against source (ran the actual code, not just read it) before any fix
landed — see the code comments left at each fix site explaining what was verified and how.

**Resolved this run (root causes, all independently reproduced before fixing):**
- **`cascade_bridge._bury()` raised `UnboundLocalError` on every call** — a dead `if _DEAD is
  None: _DEAD = {}` guard turned `_DEAD` local-by-assignment for the whole function scope, so
  the read one line above it threw before any provider could be benched. Both call sites sit in
  a bare `try/finally` with no `except`, so the error propagated out of the whole cascade call
  uncaught. This is the mechanism behind the exhausted/401-ing providers cycling back into
  rotation every few minutes that OPERATIONAL notes have been describing as "the meter, not the
  code" — it was partly the code. Reproduced by direct call before and after; strike-benching,
  auth-benching, `_alive`, and `_clear` all verified end-to-end post-fix.
- **Phase-1/phase-2 band gates accepted a fabricated Assay decimal** — `re.match(...)\b` is
  start-anchored only, and `\b` is satisfied by a `.`, so `"M4.31 +/- 0.30"` matched and
  `group(1)` returned a laundered `"M4"` — exactly the fabrication both call sites' own
  comments say must be refused. Replaced with `pipeline.clean_band()` (full-match, strict) at
  both acceptance sites, and a separate `pipeline.ceiling_band()` (still lenient, since the
  ceiling clamp can only ever lower a band and refusing to read a legacy dirty ceiling would
  silently drop the clamp for the oldest records). Verified against a dozen inputs including
  clean bands, decimals, prose, `None`, `M11`, and whitespace.
- **`write_record`/`write_record_catalogue` discarded `silence.replace_retry`'s return value**
  — on persistent Windows rename-denial the write silently doesn't land, but both entrypass and
  synthesis marked the unit done regardless (the `done_keys` resume gate then skips it
  forever). Both writers now return whether the rename landed (`pipeline._landed`), and both
  call sites gate `done_keys`/`failed` on that result — a denied write now stays open for the
  next run exactly like an unfinished batch already does, instead of vanishing. Verified with
  a monkeypatched `replace_retry` forced to return `False`.
- **`handbuilt.py` crashed before writing its own artifact** — `moth_number` opens with U+1D504
  (FRAKTUR CAPITAL A), and the report loop that prints it ran before the `json.dump`, so on
  this machine's cp1252 console `python src/handbuilt.py` died with `UnicodeEncodeError`
  mid-report and `data/HANDBUILT_ASSAYS.json` silently stopped regenerating (it had been stale
  since 2026-08-22 20:50). Write now happens first, console reconfigures to UTF-8 with
  `errors="replace"` after. Reproduced the original crash, then reproduced a clean run and
  confirmed the artifact's mtime moved.
- **`rigor.bradley_terry()`'s `undefeated`/`winless` always empty under regularisation** — the
  symmetric prior was folded into `W` before those two lists were computed from it, so any
  `prior > 0` gives every entrant a nonzero row and column sum by construction. Now computed
  from a pre-prior `observed` copy. Reproduced with a 4-entrant all-A-wins fixture at
  `prior=0.0` (correct) vs `prior=1.0` (was `[]`/`[]`, now correct).
- **`rigor.mathematical_resonance()`'s returned `load_bearing` field capped at 8** — Hard Rule
  0: a returned field, not a display string: `sorted(...)[:8]` silently dropped everything past
  the 8th quantity. Uncapped; console `main()` still slices for its own printout. Verified the
  full ledger returns 75 entries now, self-test still prints correctly.
- **stale `silence.note()` line label** at `derivation.py:490` (labeled `:488`) — renamed to a
  content label (`scan_constants-parse`) so it can't drift again.
- **`render.children_of()`'s child-tier gate asserted a schema instead of reading the tree** —
  `child_tier not in SF.TIERS` happens to agree with the current SEVENFOLD.json (which stops at
  `universe`) but would silently keep returning `[]` for `universe` even after galaxy
  coordinates are charted. Changed to `child_tier is None`, letting the per-entry
  `child_tier not in c` check (already present) do the honest work off the actual tree. Traced
  all 9 tiers against a real coordinate before and after — identical child counts, `render.py`
  self-test ("all 9 tiers viewable") still passes. Dropped the now-dead `sevenfold` import
  (pyflakes was clean before touching this file and stayed clean after).
- **[minor] disk pressure (BUGS M2)** — resolved itself between runs; `allsweep` now reports
  135 GB free (was ~5 GB). No action taken by this run; moved to paper trail.
- **`identity.adjudicate()` deleted** (was src/identity.py:321-367) — flagged dead in run #1's
  audit (superseded by `chain.adjudicate_mutuals()`), re-verified dead this run (fresh grep:
  no callers, `winner_epoch` never read anywhere) per the run #1 guardrail ("flagged this run,
  execute next"). `epoch_of()` above it stays — `chain.py:381` calls it directly.

**Findings surfaced but NOT changed (documented, not "fixed"):**
- `thread_integrity.py`'s `implied_threads()`/`classify()` — `pairs` is built symmetrically by
  construction, so every implied thread classifies RECIPROCAL and the ASYMMETRIC-LAWFUL/
  -SUSPECT branches (and the propagation-distance "lawful excuse" logic) are structurally
  unreachable; `DANGLING` is a documented output category that's never computed. This is a
  design-shaped question (is the module meant to compare against a directed thread graph it
  isn't given?), not a one-line fix — added to NEXT_STEPS for review.
- `completeness.py category_size()` — a source whose every category probe hits `URLError`
  returns `None` from `work()` and vanishes from `COMPLETENESS.json` entirely, rather than
  landing in the `unreliable` bucket the module's own docstring says exists for exactly this.
  313 `URLError`s recorded against this site. Added to NEXT_STEPS.
- `wiki_source.page_text()` — a transient exception fetching section 0 returns `""`
  immediately instead of trying sections 1/2, reproducing the exact "transient network hiccup
  read as genuine silence" failure shape `silence.py`'s own header essay warns about. Added to
  NEXT_STEPS.
- `wiki_source.py:278` used as the `silence.note()` label for two semantically unrelated
  failure sites (a local `WIKI_HOSTS.json` read and a live per-candidate category probe) —
  ledger key collision, not a behavior bug. Added to NEXT_STEPS.
- `pipeline.py` phase_cosmology/history/shelve/weave/write write 9 shared, cross-phase-read
  JSON files (`TIERS.json`, `GROUNDINGS.json`, `CENSUS.json`, `SHELFMARKS.json`,
  `CHRONICLE.json`, `SHELVES.json`, `manifest.json`, plus weave's four outputs) with a raw
  `open+json.dump`, not through `_landed`/`replace_retry` — inconsistent with the discipline
  just extended to `write_record`. Medium surgery (9 call sites); added to NEXT_STEPS rather
  than rushed in this run.
- `pipeline.py phase_synthesis` samples only 14 entities (by feat-count then description
  length) to nominate a source's power ceiling, which then hard-clamps every entry in that
  source — if the true ceiling entity has no mined feats, every other entry gets clamped
  against a lesser nominee. UNCERTAIN whether this is Hard-Rule-0-shaped or a design tradeoff;
  added to NEXT_STEPS as a question, not a fix.
- `pipeline.py phase_entrypass` marks `catalogued=True` unconditionally even when `topic` fails
  its enum check (no fallback, unlike `magnitude`'s explicit `unassayed`) — entry becomes
  permanently topicless via the `done_keys` resume gate. Added to NEXT_STEPS.
- `build_terminal.py` interpolates catalogue-derived text into `innerHTML` unescaped
  everywhere, and splices `NAVTREE.json` into a `<script>` block via a plain string replace
  with no `</script>`-sequence guard — `render.py`'s `containment_svg()` already does this
  correctly (`html.escape()`) elsewhere in the same codebase, so the fix pattern exists.
  Real, but a multi-site JS-generation change; added to NEXT_STEPS rather than rushed.
- `build_terminal.py`'s side-panel "Shelved here, not yet catalogued" note truncates to the
  first 8 sources with no "+N more" (Hard Rule 0, display-layer) — small, targeted fix; added
  to NEXT_STEPS.
- `build_terminal.py`'s "contains" row uses `a||b||c` instead of summing branch-children and
  directly-shelved sources — undercounts a node holding both. Added to NEXT_STEPS.
- `navtree.py sources_under()`'s `key.startswith(path)` arm has no `.`-boundary check (the
  sibling arm does), so e.g. key `"0.1.20"` can false-match path `"0.1.2"` and pollute that
  branch's naming register with an unrelated sibling's sources. Added to NEXT_STEPS.
- `weave_index.py designations()` caches forever with no invalidation, unlike its sibling
  `load_records()` which is signature-keyed — low exposure today (its one caller never varies
  the arg) but a real stale-cache pattern. Added to NEXT_STEPS.
- `weave.py`'s per-pair `shared_sample` (capped 8-then-6) is diagnostic evidence for why two
  shelves were linked, not a reader-facing catalogue listing — flagged as Hard-Rule-0-adjacent
  for an owner call rather than assumed in scope. Added to NEXT_STEPS.
- `endpoint.py fetch_raw` lumps every HTTPError (403/429/500, not just 404) into "page doesn't
  exist"; `endpoint.py register()` mutates `SOURCE_PAGES.json` without the lock `ENDPOINTS.json`
  uses in the same file. Both UNCERTAIN/low — added to NEXT_STEPS.
- `handbuilt.py`'s own artifact write was still non-atomic (raw `open+json.dump`, no
  `replace_retry`) even after the ordering fix above — no live second writer today, so lower
  priority than the ordering bug; added to NEXT_STEPS.

**Battery (post-fix):** verify_math 272/272 · allsweep 0 subsystems bad · pyflakes clean in
`src/` (one pre-existing, out-of-scope finding in `src/deprecated/`) · silence audit 331
handlers, 10 silent (unchanged roster, all previously reviewed) · health.py --preflight: 2
pre-existing/known issues (fandom transient unreachability; dandwiki empty cache, BUGS M1) plus
5 entries stranded in closed batches — new count, not investigated this run (pipeline.py was
live and being edited concurrently; flagged to NEXT_STEPS rather than chased mid-run).

**Repo health:** Ollama up (9 models), Cascade 4 usable buckets, disk 135 GB free (BUGS M2
resolved). Export git log confirms `publish.py --push`'s earlier `RuntimeError` (rejected
push, "fetch first", recorded 21:51/22:01/22:11) had already self-resolved by the time this run
checked (`main`/`origin/main` 0/0 apart) — no action needed, noting for the record since it hit
the silent-failure ledger 3x.

**Notes:** four subagents this run, all sonnet-tier, all read-only until findings came back to
this session for source-verification — matching last run's stated discipline ("agents propose,
verify before fixing"). No caps introduced anywhere; two existing caps (`weave.py` shared_sample,
`build_terminal.py`'s 8-source note) flagged rather than silently left in scope-creep territory.

---

## 2026-08-23 — Run #1, triggered by commit b16f631

**Flagged for human review:** dandwiki HTML-reader decision (BUGS M1); disk at ~5 GB free
(BUGS M2); permanently hostless roll entries; `identity.adjudicate` deletion proposed for
next run (NEXT_STEPS 6); `assay.assay()` gained an OPTIONAL `weights=` kwarg (additive,
default None, no caller broken — noting per the signature guardrail).

**Resolved this run:** the full round-1 + round-2 audit findings — see BUGS.md's paper-trail
section for root causes and commits. Headlines: the two-writer contract got its second,
direction-aware writer after `write_record` silently discarded the doc-ingest's first finds;
`silence.replace_retry` now guards every reader-raced state file; evidence caches self-heal;
custodes' shared-WEIGHTS mutation localized; the terminal's invisible `--dim` labels fixed;
`config.yaml` writes atomic; endpoint cache writes locked.

**New machinery this run:** the maintenance framework itself (`MAINTENANCE.md`, this journal,
`BUGS.md`, `NEXT_STEPS.md`, hourly scheduled task `panscriptum-maintenance`); the supervisor
keeper thread; `write_record_catalogue`; verify_math §18c (merge directions) → 272 checks;
`module_index.py` + `handoff/MODULE_INDEX.md`; `handoff/PHASE_CONTRACTS.md`; descriptive
export commit messages; `ingest_doc.py` (owner-supplied books → corpus, `doc:` host sentinel).

**Optimizations (measured):** standards.check ~146 PowerShell spawns → one 3s-TTL
enumeration, 2.3s/call; chain.harvest 900MB re-parse → incremental index, 3.1s warm;
coverage.measure full-corpus deserialize → mtime cache, 15.6s→6.9s warm; completeness
~1,300 fandom calls per foreman round → 12h disk cache; publish sync ~2GB/day of
unconditional copies → mtime short-circuit; dashboard library/watch on a 5s poll → 30s TTL;
by_axis 3× regex redundancy hoisted; chain per-sentence 54KB DESIGNATORS reload → loaded
once; zstd 19→10.

**Repo health:** verify_math 272/272 · 88/88 modules compile+import · pyflakes clean ·
allsweep 0 bad subsystems · standards ~24-25/37 met (reds: evening pool tide, deliberately
unsatisfiable floors, and items in BUGS.md) · open bugs: 2 major (both human-gated),
2 minor, 3 watching.

**Notes:** the scheduler floors recurring tasks at hourly — that IS "as often as possible"
here; the overlap guard plus the repo's continuous machinery covers the gaps. The evening
free-tier pool is the throughput ceiling tonight; the midnight window reset feeds the
deferred backlog, the charter regression, and the Dragonlords miner without supervision.
