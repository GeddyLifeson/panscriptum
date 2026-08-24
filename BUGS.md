# Bug Ledger

*Open bugs by severity (blocking > major > minor > cosmetic). Resolved bugs move to the
bottom with root cause and the export-repo commit that fixed them — a paper trail, never a
deletion. Maintained by the maintenance pass; humans welcome to add.*

## Open

### Major
- **[M4] The paid burst counter stands at 598 against a cap of 500 — HUMAN CALL on what to do
  about it.** The enforcement bug is FIXED (run #6, see paper trail): no paid bucket is a
  candidate unless the lane is open, and both documented kill switches now genuinely kill. What
  remains is the owner's decision, and the reason this is filed Major rather than closed: ~98
  calls (~$1.96 at the file's own `est_usd_per_call`) were spent past a hard cap, the counter was
  **deliberately not reset** because it is the evidence, and the lane currently reads
  `enabled: true` with `used > cap` — so it is closed by the cap, not by intent. Raise `cap`,
  set `enabled: false`, or delete the file (deletion is now safe; before the fix it was the worst
  of the three, since it silenced the counter without stopping the spend).
- **[M3] fandom.com is dropping connections at the socket** — measured 2026-08-24 08:35:
  `marvel.fandom.com` api and html, `dc.fandom.com`, `onepiece.fandom.com` all HTTP 000 after
  20–21s; `en.wikipedia.org` answers in 0.25s from the same machine. A live probe run took 129s
  per probe, all 8 failing. NOT a code fault and not auto-fixable — an IP block or edge drop
  that has cleared on its own before. Everything fandom-facing is blocked behind it: page roll
  52%, reachable-wiki 90%, the completeness audit. `run_completeness_audit` and
  `run_catalogue_gap` are both now gated on `_fandom_reachable()` so neither dispatches into it.
- **[M1] dandwiki.com is API-blocked (HTTP 403 to every non-browser client)** — 4 homebrew
  sources unhosted; HTML answers a browser UA, so a design decision is needed: build an
  HTML-path reader with a browser UA (politeness/ToS question — HUMAN CALL) or leave the four
  sources owner-supplied. Noted in `data/SCOUT_BLOCKED.json`. Not auto-fixable.
### Major
- **[m42] BOUNCING A STANDING JOB ORPHANS ITS LONG-RUNNING CHILDREN, and the orphan then writes
  shared state from a stale snapshot.** Found live in run #9. `foreman.adopt_hosts()` shells out
  via `subprocess.run(..., timeout=1800)` to `hostcheck.py --adopt --go`. `subprocess.run` does
  kill its child on timeout — but only if the PARENT is still alive to do it. Run #8 bounced the
  foreman at 11:22 to ship the m40 fix; the foreman it replaced had launched a `--adopt` child at
  11:15:25 which was left with **parent PID 35128, a process that no longer exists**. Its killer
  was dead, so its 1800-second timeout could never fire, and at 12:20 it was still alive with
  2.9s of CPU over 65 minutes (blocked on fandom sockets, which are down — M3). `adopt()` ends in
  `hosts.update(found); _land(F.HOSTS, hosts)`, a **whole-file replace of `WIKI_HOSTS.json` from
  the snapshot it read at 11:15**, and the CURRENT foreman had meanwhile launched a second,
  legitimate `--adopt` (PID 17724, parent 5420, started 12:15:27). Two processes, each holding
  its own snapshot, each ending in a whole-file write: whichever landed last would silently
  discard the other's adoptions.
  **This is m40's exact shape one run later in a different module, and it was CREATED BY the act
  of shipping m40's fix** — every keeper bounce of a job that shells out to a slow child makes one.
  Damage this time was nil (`WIKI_HOSTS.json` was untouched since 08:55, md5 `451703b8…` before
  and after) because neither had finished; the orphan was killed and the ledger verified. **The
  instance is closed. The missing guard is the open bug**, and it has two candidate fixes, which
  is why it is filed rather than patched: either `_land` gains m40's digest-compare (write only
  if the file is as it was read, else re-read and merge), or long children are made to notice
  their parent is gone. `hostcheck._land` is atomic (`tmp` + `replace_retry`) but **atomicity is
  not the property that was missing** — a stale whole-file write lands perfectly intact.
- **[m43] Nothing in the kit detects an orphaned child**, which is the reason m40 and m42 were
  both found by hand. Run #8 said as much in prose; run #9 found the second instance 65 minutes
  later, so this is now a recurring cost rather than an observation. A check is cheap and
  self-contained: any `panscriptum` python process whose ParentProcessId names a dead process is
  an orphan by construction. Candidate home is `allsweep`'s RECONCILE block or `health
  --preflight`. **Not self-authorized in run #9** because it adds a new reported subsystem and
  the two runs that hit it disagree about the right remedy (kill vs. report).

### Minor
- **[m44] `hostcheck.null_rate` computes its sampling stride from the WRONG list — currently
  inert, deliberately not fixed.** `foreign = sorted(set(foreign))[::max(1, len(foreign) //
  sample)][:sample]`: the RHS is evaluated before the assignment, so `len(foreign)` is the length
  of the list WITH duplicates while the stride is applied to the DEDUPED one. Measured on the
  live corpus: raw 618, deduped 599, so the stride is 15 where it should be 14 — and both yield
  the full 40 names, because dedup only removes 19. **Fixing it would change the control sample
  for every host and therefore host-adoption verdicts, for no gain while it returns the right
  count.** Filed so the next reader who spots it knows it was measured and left alone on purpose;
  becomes live only if the roster ever dedups heavily.
- **[m26] the completeness audit structurally cannot see 46 of 210 sources** — `audit()`'s
  `todo` is filtered on `subdomain(h)`, which only resolves fandom hosts, so the 21
  Wikipedia-hosted and 25 other-hosted sources have never been in scope. Not widened silently
  this session: a measure called "completeness" that ignores a fifth of the corpus is a naming
  and design question (should it measure them, or should it be renamed to say what it measures?)
  rather than a bug to be patched. **Owner call.**
- **[m23] `overnight.start()` TRUNCATES a job's log on every restart** (`fh = open(lf, "w")`),
  so each keeper-driven bounce destroys that job's entire history. Found the hard way in run #4:
  the 59-503 record that diagnosed the Ollama wedge existed only in `pipeline_auto.log`, and the
  keeper's restart erased it minutes after it was read — the counts survive only because they
  were transcribed into HANDOFF.md first. The keeper restarts standing jobs every five minutes
  when they are down, so this is the normal path, not an edge case: any problem that needs more
  than one restart to understand cannot be investigated. Fix is small (`"a"` plus a
  session-separator line, or rotate to `<job>.N.log`) but it changes an operational convention
  and the dashboard's `_tail_match` readers assume a single current file — **worth an owner
  glance before changing**, not a silent flip.
- **[m1] Marvel completeness row 25h stale** (0.4% vs 30,207 on disk) — re-measure was
  launched this run (`completeness.py --workers 6`); verify the row after it lands. If still
  wrong after a fresh run, the byslug matching in `completeness.py` becomes a real suspect.
- **[m2] `sources on the roll but never catalogued`: 6** (HAWX, Heaven's Lost Property, Lost
  Mines of Phandelver, Twilight Imperium, +2) and **16 catalogued sources with no host** —
  scout/adopt remedies keep retrying; some (music albums, board games) may be permanently
  hostless and deserve an owner ruling on whether they stay on the roll.
- **[m12] `thread_integrity.py`'s asymmetric-thread detection is structurally unreachable** —
  `implied_threads()` builds `pairs` symmetrically by construction, so `classify()`'s `back =
  pairs.get((b,a))` is always truthy and every implied thread reports RECIPROCAL; the
  ASYMMETRIC-LAWFUL/-SUSPECT branches (including the propagation-distance "lawful excuse"
  logic) can never fire. `DANGLING` is a documented output category that is never computed.
  This looks design-shaped rather than a one-line fix — HUMAN CALL: is the module meant to
  compare the weave's implied threads against a separately-recorded directed thread graph it
  currently isn't given? See NEXT_STEPS.
- **[m13] `pipeline.py phase_synthesis`'s 14-entity ceiling-nomination sample can silently
  clamp the whole source to a lesser band** — the sampled 14 (by feat-count then description
  length) may not include the source's true strongest entity; that entity's own later-mined M6
  feat then gets clamped down to whatever lesser ceiling was nominated. UNCERTAIN whether this
  is Hard-Rule-0-shaped; HUMAN CALL requested in NEXT_STEPS.
- **[m16] `weave.py`'s per-pair `shared_sample` field is capped (8, then re-sliced to 6)** —
  diagnostic evidence for why the weave linked two shelves, not a reader-facing catalogue
  listing, but Hard Rule 0's text says "no sample" without carving out diagnostics explicitly.
  HUMAN CALL requested in NEXT_STEPS rather than assumed out of scope.
- **[m24] `cascade_bridge.dead_forever` buries buckets for three undocumented reasons** — the
  docstring says exclusion is permanent-codes-only (401/402/404/410) and that "a timeout, a 429,
  or a silent minute excludes nothing", but the code also buries on the substrings `no such
  model`, `needs billing`, `bad key`. **Currently inert** — verified that no writer of `verdict`
  produces those strings today (`prove()` writes `answers`/`no answer`/`local`, an exception
  class name, or `provider disabled`/`no API key`). It becomes live the moment a verdict carries
  an exception *message* instead of its class name. Contract question rather than a defect:
  should those three be permanent exclusions (then document them) or not (then drop them)?
- **[m25] `scout.sweep` keeps only the last 40 run entries** (`prev[-40:]` into `SCOUT.json`).
  Judged NOT a Hard Rule 0 violation this run — a run history is not a roster, an entry list, a
  page list or a chunk list — but it is a truncation of an ordered listing and the rule's text
  does not carve out logs explicitly. **Question, not a fix.** Same family as m16's diagnostics
  ruling; one decision could settle both.
- **[m37] `data/CHAIN.json` is written every cycle and NOTHING reads it — CONFIRMED run #8,
  and now the only part of m37 still open.** Verified repo-wide, not just `src/`: the string
  `CHAIN.json` occurs in exactly two places outside documentation and this ledger — `chain.py:53`
  (`OUT`, the writer) and `chain.py:92` (its docstring). `pipeline.py:1255` imports chain and
  drives the WRITE side. No consumer exists in `src/`, in the dashboard, or in the published
  site. So `write_result` persists the edges, the Bradley-Terry strengths and the Ford's-condition
  `identified` verdict every cycle, and the cross-check the module's docstring calls its entire
  purpose ("the only one that checks the others") is never performed against the Assay.
  **HUMAN CALL — this is a design question, not a repair**: wire a consumer that actually runs
  the cross-check, or say plainly that CHAIN.json is an archival record and stop calling it a
  check. Deliberately not self-authorized in run #8: inventing a consumer invents a contract.
  *The audit agent's other three claims about this module were all verified true and are FIXED
  in run #8 — see the paper trail (`[:120]` dedup key, bare `open(OUT,"w")`, discarded
  `replace_retry`). The agent was right about WHERE and WHY on every one of the four.*
- **[m38] `foreman._function_source()` resolves a symbol by bare name with no uniqueness
  check.** `symbol.split("(")[0].split(".")[-1]` deliberately strips a class qualifier, then
  takes whichever same-named function `ast.walk` reaches first. A finding naming
  `ClassA.validate` can therefore hand `ClassB.validate`'s body to the model lane and, with
  `--patch` live, overwrite the wrong function with a fix meant for the other — syntactically
  valid, so `_checks_pass` need not catch it. Verified in source; not fixed this run because the
  right behaviour (refuse an ambiguous symbol? honour the qualifier?) is a contract choice.
- **[m39] `scout.sweep(limit=4)` can starve lower-ranked sources indefinitely.** `foreman`'s
  `scout_hostless` calls it with `limit=4`; `scout.sweep` sorts `todo` by page count and takes
  `[:limit]`. The ranking is deterministic and recomputed every round, so while the top four
  remain hostless the fifth and below are never attempted — round after round. Hard Rule 0's
  ranked-then-truncated shape, but removing the cap changes per-round load, so it is an owner
  call rather than a silent fix.
- **[m29] `cleanup.py`'s `_EMPTY_MECHANIC` predicate cannot tell a rules construct from a real
  entity whose description failed to fetch.** It strikes an entry when the description is empty
  AND the name ends in `variant|feature|trait|slot|...`. But an empty description is a signal this
  project has repeatedly shown to be unreliable (`feats._unwrap_templates` turned 190KB pages into
  30 characters and it "read as CORRECT SILENCE"), and real entities do end in those words —
  Marvel's Loki *Variants* are the obvious case. **Relevant now in a way it was not before**: run
  #6 made exclusions durable, so a wrong strike is now permanent rather than being undone by the
  next entrypass. **Owner call before `cleanup.py --apply` is run again** — and note that the 149
  entries struck earlier have all since been flipped back, so re-running is what would re-strike
  them. Deliberately not re-run this session.

*Open items are now: two operational blocks that are not code faults (M3 fandom, M1 dandwiki),
one money decision (M4), three contract questions (m24, m25, m26), the standing HUMAN CALLs
(m12, m13, m16, m29 and M1), two contract choices raised by run #7's audits (m38, m39), one
CONFIRMED design question (m37 — CHAIN.json has no reader) and two watched states (m1, m2).
Run #7 resolved m27, m28 and m30 and added m31-m36. Run #8 confirmed m37's core claim, fixed
its three sub-findings, and added m40 (stale overwatch writer) and m41 (hash-seed-dependent
nav names) to the paper trail. **Nothing on the open list is a live data-loss risk; every
remaining item is either an outage, a decision, or a watched state.***

## Watching (not bugs — expected states with a clock on them)
- **`MAX_JOB_SILENCE_MIN = 15` is a live threshold as of run #3** — the stall detector could not
  previously reach it (see the Resolved entry). During run #3 a healthy `roll_auto.log` sat
  unchanged for 4.5 minutes; a page roll waiting on a slow host could plausibly cross 15 and
  trigger the AUTO kill remedy. Watch for false alarms; raise the constant if they appear.
- **Local model throughput is the live constraint.** Not a 503 any more (that was the run-#3b
  wedge, resolved) — the runner is up and measurably pegged at ~8 cores, but a 30B MoE at 8.5 GB
  on a 10 GB card means heavy CPU offload, and a phase-2 batch can sit for a long time. Run #4
  watched `units_done` hold at 3382 across a 40s sample with the state file freshly written:
  blocked inside one call, not broken. If phase 2 makes no measurable progress over a few hours,
  the question is model choice / offload split, not correctness.
- ~~`entries stranded in closed batches`~~ **CLEARED to 0 in run #4** — moved to the paper
  trail. `health --preflight` now reads `ok  state consistency`.
- Charter regression: `data/CHARTER_REGRESSION.json` **landed** (22:24, run #3 confirmed it on
  disk). Verify the `automation reproduces the charter` standard now takes a real reading.
- Dragonlords ingest miner: patient loop (60-miss ≈ 5h), waiting out the evening pool for the
  midnight free-tier window. Cursor at chunk 1/252 after the writer fix.
- Deferred assay backlog (heavyweights, Jace accessions, Infinity Gauntlet) self-requeues
  when the pool window rolls.

## Resolved (paper trail)

*Run #9 (2026-08-24 12:30 local, export commit = run #9's `publish.py --push` sync). Full detail
in HANDOFF.md's run #9 entry:*

- **[m45] `feats_index._norm`'s docstring promised a fold it does not perform, and the module
  docstring blamed all 17 stranded records on one cause when they have two.** Both corrected in
  place; no code changed, because the code was right both times. (a) `_norm`'s docstring offered
  *"Zangetsu (Zanpakutou spirit)" vs "Zangetsu"* as a pair it folds together. It does not —
  alphanumeric-only folding yields `zangetsuzanpakutouspirit` against `zangetsu`. The STRICT
  behaviour is nonetheless correct and is now defended by three verify_math checks (§19o), because
  loosening it is the obvious fix for the stranded records and is a trap: `Wally West (New Earth)`
  and `Wally West (Prime Earth)` would both fold onto the catalogue's `Wally West (Earth-16)`,
  merging three DC continuities into one cast entry and attaching 177 deeds to the wrong one.
  Measured: 79 of 1,241 records carry a parenthetical and 76 join anyway, so strict costs almost
  nothing. (b) The module docstring, and `NEXT_STEPS` item C, said the 17 strays were all hosts
  missing from `WIKI_HOSTS`. Re-measured: **14 records / 222 feats** are missing hosts, but
  **3 records / 240 feats — 52% of the stranded evidence — sit on hosts that ARE bound**
  (`dc.fandom.com`→DC, `marvel.fandom.com`→Marvel). Binding the four missing hosts will never
  recover those; they are catalogue gaps. `audit()` and `main()` already reported the distinction
  correctly — only the prose was wrong. Root cause of both: a docstring written from the shape of
  the answer rather than from a re-measurement, in code less than an hour old.

*Run #8 (2026-08-24 12:00 local, export commit = run #8's `publish.py --push` sync). Full detail
in HANDOFF.md's run #8 entry:*

- **[m40] A STALE `overwatch.save()` writer silently erased a fresher ledger.** `save()` is a
  whole-file replace, and although this module is the ledger's only writer, it is not its only
  WRITING PROCESS: the standing `--loop` job plus any ad-hoc `verify_open` call a maintenance run
  leaves behind both hold it. Caught in the act — an orphaned diagnostic call launched **09:02**
  by an earlier session was still alive at **11:28** with 2.8 seconds of CPU across 2h26m (i.e.
  blocked on a model reply, not working), holding a 09:02 snapshot, one `return` away from
  replacing a 68-round / 64-finding ledger with it. Measured exposure: **4 findings destroyed**
  (3 open — `feats.roll`, `hostcheck.add`, `cascade_bridge.ask` — plus 1 retired), **1 retirement
  reverted**, and the round counter regressed. The write would have SUCCEEDED, which is why
  nothing would ever have reported it. Root cause: no writer checked whether the file had changed
  under it. Fixed — `load()` stamps the digest it read, `save()` compares and MERGES rather than
  replaces when they differ (union of findings, terminal verdicts win, `seen` keeps the later
  sighting, `rounds` takes the max). Merging is sound only because nothing in the module ever
  deletes a finding, and verify_math §19m now pins that premise too. Falsified against the real
  event before shipping: the pre-fix `save` drops both interloper findings and regresses rounds
  68 → 2; the new one keeps all three findings and both writers' work. §19m, 10 checks.
  The orphan was killed (it did no work anything depended on) and the live loop bounced onto
  the fix; the keeper re-asserted it at 11:37.
- **[m41] Every `navtree --write` renamed a chunk of the tree — the Registry Terminal's node
  names depended on the PROCESS HASH SEED.** `register_for()` chose a node's naming register with
  `max(set(regs), key=regs.count)`, and `build()` chose a hyperverse's grounding type the same
  way. On a TIE — two registers equally common under one node, the ordinary case on a small
  branch — `max` keeps whichever the **set** yielded first, and string set order is randomized
  per process. The register is an input to `onomast.coin_well_formed`, so a flipped tie renames
  the node. Both the module's own comment ("seeded on the node's own key so the name is stable")
  and `coin_well_formed`'s docstring ("Deterministic: same input, same output") asserted the
  opposite of the behaviour. Measured: two consecutive `--write` runs on identical inputs renamed
  **75 of 734 nodes**; with `PYTHONHASHSEED=0` two separate processes agreed byte for byte, which
  is what identified the cause. NAVTREE.json feeds `build_terminal.py`, `reference.py` and
  `sweep.py`, so these are reader-facing names. Fixed by making the tie-break explicit
  (`key=lambda r: (regs.count(r), r)`); three processes with random seeds now agree exactly.
  The artifact was regenerated once to settle the names — **146 of 734 names changed, structure
  identical (734 nodes, 0 added, 0 removed, no non-name field changed)** — and a second `--write`
  is now a no-op. verify_math §19n, 5 checks. *Found only because a routine staleness check was
  diffed twice instead of once.*
- **[m37 sub-findings, all three verified true and fixed]**
  **`chain.harvest`'s dedup key was `sentence[:120]`** — a truncation that DECIDED WHICH CONTESTS
  EXIST, since wiki prose front-loads its subject and two different sentences about one entity
  routinely share a 120-character prefix; the second was dropped as a duplicate it was not.
  Hard Rule 0. Measured on the live index: **22 distinct contests were being discarded** (12 of
  them Khan Noonien Singh sentences diverging only after char 120), up from 2 when the index was
  smaller — the loss GROWS with the corpus. Now keyed on the full sentence, which can only make
  the dedup finer, never coarser. **`chain.write_result` used a bare `open(OUT,"w")`** on a
  published phase artifact — a torn CHAIN.json after a mid-dump death is indistinguishable from
  a fit that found fewer edges; now write-then-`replace_retry` with the verdict checked.
  **The harvest index discarded `replace_retry`'s boolean** — a denied rename silently costs the
  whole incremental cache, so the next cycle re-parses ~900MB and presents as "the pipeline is
  slow"; now reported. (Same family as m33–m35.)
- **`pick_model.save_config` reported a success it had not had, two ways.** It discarded
  `replace_retry`'s boolean, and its targeted `re.sub` could match nothing — a config with no
  top-level `model:` line wrote itself back byte-identical — while `main()` printed
  "config.yaml updated" unconditionally for both. Now returns a real verdict (`re.subn`, and the
  rename checked), and `main()` exits 1 rather than claiming a model switch that never happened.
- **`local_agent`'s pyflakes gate could not fail.** It tested `r.stdout` for "undefined name"
  only, so a pyflakes that never executed produced empty stdout and was read as a clean pass —
  waving a patch through one of the six gates that stand between a local model and live source.
  The very next gate checks `returncode`, which is what makes this an oversight. Now a code
  outside pyflakes' own (0, 1), or a stderr that looks like the tool failing, is a gate failure.

*Run #7 (2026-08-24 11:45 local). Full detail in HANDOFF.md's run #7 entry:*

- **[m31] `ask_pool_first` accepted any non-None cloud answer, so a cloud-first/local-second
  helper had no second.** The cloud path cannot constrain generation to the schema — it carries
  the schema in the prompt as a REQUEST (`cascade_bridge.py:18`) — so a bucket can return valid
  JSON of the wrong shape, `_extract_json` parses it, and the helper returns it on the sole test
  `got is not None`. Downstream that is indistinguishable from the model judging every entry and
  finding nothing: **four of four logged Marvel entrypass batches read `returned 0/20`** while
  the same batch put to the local model returned 20 valid results in 54s. Now an answer must
  carry the schema's `required` keys AND satisfy an optional caller predicate (`accept=`);
  entrypass supplies one requiring at least one result whose index it actually asked about. A
  failing answer is logged as an unusable shape and the local arm runs. verify_math §19l.
  **Mechanism confirmed by source and log; the incident itself was NOT reproduced** — the pool
  had collapsed to 2 of 36 answering by the time it was probed, below the `>= 3` gate.
- **[m27] The run guard had no implementation in `src/` at all.** Filed as "the heartbeat does
  not check whose record it is refreshing"; the root cause is that the protocol lived only in
  prose in `MAINTENANCE.md`, so every run re-improvised the read-modify-write and there was no
  single place for the ownership check to live. Now `src/runguard.py`: a run may only refresh or
  close a record carrying its own name. `beat()` refuses a foreign record loudly and leaves its
  heartbeat untouched, `release()` refuses to close one, a closed record cannot be reopened by a
  stray heartbeat, and taking over a stale record records whose it was. Falsified against the
  m27 scenario (the pre-fix helper moves the foreign heartbeat; this one does not).
  verify_math §19k.
- **[m28] `overwatch.load()` turned a corrupt ledger into an empty one.** Now copies
  `health.flush()`'s treatment — preserve the wreck as `.corrupt`, say so on stderr, start fresh
  only then — and additionally distinguishes ABSENT (ordinary first run, no `.corrupt` written)
  from DAMAGED, which the single `except` could not. Verified across absent / intact / torn.
- **[m32] `local_agent`'s six-gate discipline was skipped entirely for every non-Python file.**
  `t_propose_patch` set `modname = None` for anything not `.py` and then ran the gates only
  `if modname`, so a patch to `config.yaml`, a prompt file or any `data/*.json` was written and
  reported `applied: True` having passed no parse, lint, import or verify_math check — the exact
  opposite of the module docstring's promise. The same `None` also made the **denylist
  unanswerable for non-Python paths**. Fixed: gates run for every file type with a per-format
  parse check (`ast.parse` on YAML is a false rejection, not a check), verify_math runs
  unconditionally, and `DENYLIST_PATHS` covers non-module files with `config.yaml` in it.
- **[m33] `completeness.land()` claimed a write landed without checking.** Its docstring says
  "Returns True if the file now holds `rows`"; it discarded `replace_retry`'s boolean and
  returned True unconditionally. The two existing guards protect the CONTENT (empty, and the
  SHRINK_FLOOR added the same day); neither checks that the content reached the disk, and this
  file's own docstring names the readers that hold it open — on Windows a held handle is a denied
  rename. A run could measure correctly, report success, exit 0, and leave the stale file.
  Now returns False and names which measurement is actually on disk. verify_math §19m.
- **[m34] `foreman.reprove_pool()` discarded the same boolean and then invalidated the cache
  anyway.** Clearing `CB._PROVEN[0]` forces the next `_alive()` to re-read from disk, so a denied
  rename threw away the fresh in-memory proof AND pointed the router at the stale file, while
  reporting `did=True` — which makes `round_once` `break` and skip the remedy for a full cycle.
  Now reports the failure and leaves the cached proof standing.
- **[m35] `foreman.triage_swallowed()` discarded both of its write verdicts.** Those two writes
  are a MOVE, not two saves: clearing `state/failures.json` when the archive rename was denied
  destroys the counts outright. Now archive-first, clear-only-if-the-archive-landed, with a
  distinct message per failure.
- **[m36] `foreman.attempt_patch`'s size gate measured the wrong quantity.**
  `abs(len(new) - len(old))` is a net line COUNT, while the module docstring sells the gate as
  bounding how much of a function a model rewrite may change and the refusal message said "patch
  changes N lines". Falsified: a rewrite replacing **every line of an 80-line function**, landing
  on 82, scored **2** against a cap of 40 and passed. Now `foreman.lines_changed()` (difflib,
  stdlib) scores it 82 and refuses. One-line edit: old metric 0, new metric 1. verify_math §19m.
- **[Hard Rule 0] `foreman.owner_queue()` truncated the OWNER'S decision document.**
  `for u in urls[:3]` into `FOR_OWNER.md` — the file whose purpose is "everything nobody but the
  owner can decide, in one place". The rule's exact shape aimed at a human decision rather than a
  catalogue: three URLs read, ruled on, and a fourth never known to exist. Uncapped.
- **[m30] Two checks that could not fail — documented, not changed.** `custodes.convene`'s
  `covers_every_reading` and `sevenfold`'s `OVER SPAN` are enforced invariants published as
  checks, true by construction. Changing what they compute is design work, so each now says
  in-source that it states a guarantee, cannot catch a regression, and what would make it live
  again. The informative version of the custodes one is raised as a question in NEXT_STEPS.
- **[genre reaches production] Run #6's uncap was correct and inert.** `data/GENRES.json` has no
  automated writer — only the manual `genre.py --write`, last run 2026-08-20 — and
  `genre.classify_source` has zero runtime callers, unlike `grounding.classify_source` which
  `pipeline.py:1274` calls every phase. Regenerated: **12 of 209 sources changed genre and 11
  changed register** against the stale file (seven from run #6's uncap, five from corpus growth).
  Consumers are `profile.build_all` (genre and register encoded into every world profile) and
  `navtree` (tier naming). The missing-writer question is open in NEXT_STEPS.

*Run #6 (2026-08-24 15:35). Full detail in HANDOFF.md's run #6 entry:*

- **[M4-enforcement] The paid burst cap was never enforced at SELECTION, and ~$1.96 of real money
  went past it.** `paid_ok` only decided whether to PROMOTE `anthropic:paid` into the proven-
  answering set. The bucket is in `_ROUTER.models` unconditionally, is not local, and `_alive()`
  returns True for it — so a closed lane merely ranked it lower and the exhausted-pool fallback
  reached it anyway (free tier at 4% success, so reaching the list's bottom is the normal path).
  `enabled: false` failed identically, and deleting the file was worse still: `_pb is None`
  stopped the counter while the calls continued. Now `widen_candidates()` excludes paid buckets
  unless `paid_lane_open()`, and the counter re-reads from disk under a lock and lands atomically
  (the old snapshot-increment was a lost-update race that drifted the count BELOW true spend —
  the wrong direction on a money file). verify_math §19h, falsified against the pre-fix
  expression. The remaining owner decision stays open as M4.
- **[Hard Rule 0] `genre.classify_source(cap=120000)` was choosing genres off the front of a
  record.** Stored order, not ranked. Marvel: 18,765,902 characters, 0.64% read,
  `post_apocalyptic` (score 240) where the whole record says `mythology` (41,891). Whole-corpus
  diff, 210 records: **seven sources answered differently uncapped** (Marvel, KibblesTasty,
  Bleach, Yorviing's, Dr. Firestorm's, Crash Bandicoot, Digimon). `genre` sets `register` and
  `priors`, so each was dressing its prose in a voice chosen by scrape order. Uncapped; a numeric
  cap is now refused loudly. §19i — whose fixture was rebuilt after the first version proved
  vacuous (it fitted inside the old budget and passed against the buggy code).
- **[Hard Rule 0] `grounding.classify_source(cap=140000)`** — same shape, six sources over the
  cap. No verdict changed, but Marvel reported **153 origin entries instead of 5,012** and score
  95 instead of 930, understating its own attestation 33-fold on the field a reader would use to
  judge it. Uncapped; numeric cap refused.
- **`cleanup.py`'s exclusions were reverted in full — 149 of 149.** `excluded` was written by
  cleanup and read by nothing, while `batch_settled` demanded `all(catalogued)`, so a struck entry
  unsettled its batch, reopened it, and `phase_entrypass` set `catalogued = True` unconditionally.
  Measured: every one of the 149 had already been flipped back. Now an excluded entry settles its
  batch, is never sent to the model, and a result claiming its index is refused; a wholly-struck
  span costs no call. §19j. **See m29 before re-running `cleanup.py --apply`.**
- **`overwatch`'s `_LOCAL_BUSY` was a lifetime accumulator, not a per-round budget** — never reset
  anywhere, while `CLOUD_BUDGET`'s own comment says "in one round". The standing job had been up
  12.8 hours and every module read in its last rounds logged `budget spent`, with no cloud
  fallback at all; completeness "finished" in 6s having done nothing. Reset per round, job bounced,
  keeper restart confirmed by PID and creation timestamp (37188 → 41328).
- **`health.flush()` wrote `state/failures.json` non-atomically** — the exact writer
  `foreman.py:237` names ("EVERY process read-modify-writes it through health.flush()") and the
  one m18 did not fix. A torn write would trip the careful corrupt-read branch above it, which
  preserves the wreck as `.corrupt` and starts fresh — discarding all accumulated failure history.
  Atomic now, and `LEDGER` clears only if the rename landed (a denied replace used to discard the
  counts it had just failed to persist). `failure_samples.json` likewise, which needed it more,
  having no `.corrupt` recovery path.
- **`health.reopen_stranded` broke `PIPELINE_STATE.json`'s single-writer-atomic contract** — raw
  truncating write on the kit's most important state file, from the repair tool that runs
  precisely when a pipeline is live. Atomic now; absent vs. torn distinguished on read; a denied
  write reports and returns `[]` instead of a list that reads as "these were re-opened".
- **`catalogue_web` marked a source catalogued when the record write had been DENIED** — the one
  call site discarding `write_record_catalogue`'s landed verdict. Since work selection is
  `entry_count == 0`, such a source would never be picked up again. Gated. `save_roll` made
  atomic (two unguarded `json.load` readers); `overwatch.save`'s bare `os.replace` →
  `replace_retry`.

*Interactive session 2026-08-24 ~09:40 (owner-directed). Full detail in HANDOFF.md:*

- **COMPLETENESS.json was stuck at `[]` and could not recover.** Run #5 fixed the two bugs that
  emptied it, but neither could refill it: `land()`'s guard only protects a **non-empty** file,
  and `run_completeness_audit` was gated on `_fandom_reachable()`, so while fandom was blocked
  the only thing that could rewrite the file never ran. Emptied by one bug, frozen empty by the
  fix for another. Now **164 honest rows** where there were 2 bytes, and the standard reads
  `UNMEASURED -- 164 row(s), 0 measurable...` instead of a fabricated `0.0% (0 of 0)`.
- **Reachability was measured with a TCP socket, which is not the question.** Measured mid-block:
  the socket to `community.fandom.com` opened **instantly** while `GET marvel.fandom.com/api.php`
  returned nothing after **21.3s** — so `foreman._fandom_reachable`, written to detect exactly
  that outage, answered "reachable" throughout it. Both probes now ask the **API**, via
  `endpoint._get` (a bare `urllib.urlopen` is 403'd by both Wikipedia and Fandom on User-Agent)
  and `endpoint.api_url` (hardcoding `/api.php` called en.wikipedia.org unreachable while curl
  fetched it in 0.16s).
- **The block is PER-TENANT, not farm-wide.** In the same second: `community.fandom.com` 0.2s OK;
  `marvel` / `dc` / `onepiece` each failed at 42s. So `host_reachable()` is keyed per HOST, not
  per domain — asking the farm would have pronounced all 164 sources healthy and then walked each
  into eight 42s failures. One 8s question now replaces ~5.6 min of guaranteed per-source
  failure, and the foreman's all-or-nothing gate is gone because the audit handles a blocked host
  itself. verify_math §19d extended: 4 new checks (a row is still produced, marked, and **not
  probed even once**), and the 3 pre-existing probe checks now hold the gate open so they keep
  testing what they were written for.

*Run #5 (2026-08-24 08:55, export commits `2989776` / `85c5dba` and the closing sync). Full
detail in HANDOFF.md's run #5 entry:*

- **COMPLETENESS.json was wiped to `[]` and a HIGH standard reported `0.0% (0 of 0)` off it for
  two hours.** Two defects in series. (a) `work()` deleted any row it could not fully measure:
  m3's guard required UNANIMOUS probe failure, so 7 transport errors + 1 clean "no such
  category" scored 7 < 8 and dropped the row exactly as before the fix — and under a fandom
  socket-drop that is the normal shape, so all 164 rows vanished. Now any transport failure
  marks the row `unreliable`; genuine absence is `failed == 0 and not sizes`. (b) `main()` wrote
  the empty list over the good file with a raw truncating `open("w")`. New `land()`: tmp +
  `replace_retry`, and it REFUSES to replace a non-empty measurement with an empty one. `--only`
  is now read-only. verify_math §19d pins both halves.
- **`standards.py` reported a fabricated 0% instead of "unmeasured"** — with no denominator the
  arithmetic yields a clean-looking `0.0% (0 of 0)` on a HIGH standard, outranking every real
  fault while accusing the catalogue of holding nothing. Now says `UNMEASURED` and names which
  of the two failures it is, because the repairs point in opposite directions.
- **`read._names` matched by raw substring**, so MetalGarurumon's feats landed on GARURUMON and
  every Daily *Planet* sentence on LOIS LANE (via `lane`). Fixed to start-of-token matching,
  chosen by a whole-corpus diff (39,198 sentences, 1,219 files): plain tokenisation lost 265
  real inflected matches; start-of-token lost 0 and removed 37 suffix collisions. §19f.
- **`assay._interval` read the global WEIGHTS while using the override's denominator** — a
  custom-weighted assay's error bar was normalised against a table it did not come from.
  `custodes.py` builds such a table per Custos. §19e — and §19e itself was rewritten after the
  obvious relational checks were caught passing under the buggy code.
- **[Hard Rule 0] `feats.discover`'s `extra=25`** truncated the ranked evidence-page list for
  exactly the entities with the most written about them; **`scout`'s `[:8]`** truncated proposed
  URLs *before* verification, so the 9th was never tested; **`worldseed`'s `d[:200]`** windowed a
  plain in-memory regex against a 167-character median description. All three uncapped; the
  `extra` parameter now raises rather than capping silently. §19g.
- **`backfill` printed "absent 0" on every non-dry run** — the real path returned no `absent`
  key at all, only a post-cap `missing`, while `main()` prints `res.get("absent", 0)`. The
  completeness column read "nothing missing" precisely while characters were being added.
- **`foreman.kill_duplicate_jobs` could kill the instance it promised to keep** — an unreadable
  `CreationDate` defaulted to `"9" * 14`, sorting as the newest, so a garbled-timestamp process
  was always the one SIGTERMed even when it was the oldest. Now carries `None` and skips the job
  rather than choosing a victim it cannot age.
- **Eleven non-atomic writes to shared artifacts** routed through `silence.replace_retry`:
  `hostcheck` ×7, `scout` ×3, `feats` (WIKI_HOSTS), `identity` (DESIGNATORS), `magnitude`
  (CHARTER_REGRESSION — a standard reads it), `read` (`_save_qcache`'s bare `os.replace`).
  WIKI_HOSTS.json was the one that mattered: three writers, six readers, and a truncating write
  leaves every reader seeing an empty host map, which reads downstream as "no source has a wiki".
- **`read.py:queue()`'s unguarded `json.load` of WIKI_HOSTS** could have ended a multi-hour pass
  on a JSONDecodeError with nothing logged. Self-healing with a note now.
- **NEW: `run_completeness_audit` gated on `_fandom_reachable()`**, as `run_catalogue_gap` beside
  it already was. Ungated it cost ~47 minutes of pure failure per foreman round against a domain
  that has IP-banned this machine once already.
- **[M2] `publish.py --push` failed whenever a second session published concurrently** — five
  `! [rejected] main -> main (fetch first)` failures in one morning, visible only to somebody
  reading `state/publish.log`. Raised by this run as a flagged mechanism change rather than
  edited unilaterally; **fixed by the concurrent session within the hour** (export `fbcbe57`):
  publish now fetch-rebases before pushing, and a conflicting rebase is aborted and reported
  rather than forced. Verified end-to-end — this run's own closing push succeeded and left local
  and `origin/main` in sync.

*Run #4 (2026-08-24 00:45). Full detail in HANDOFF.md's run #4 entry:*

- **The stranded-batch fix is CLOSED end-to-end in production.** Live state first showed the
  gate firing (`failed.entrypass[...#280]` present while the same key was still in
  `done.entrypass` — impossible under the old gate); then, once the pipeline ran on the new code
  with Ollama serving, `Arcanum Worlds … done` at 00:46:40, the failure retired on success,
  **0 uncatalogued entries left in the tail batch**, and `health --preflight` flipped to
  `ok  state consistency` (stranded 5 → 0, preflight 3 problems → 2).
- **[m6] eleven phase artifacts made atomic** via the new `pipeline.land_json()` — the old
  `json.dump(obj, open(path,"w"))` truncates before serialising, so an unencodable value left
  the real file unparseable (reproduced). **And the second half**: `phase_history` treated absent
  and corrupt identically, reported both as "phase 5 has not run", and marked phase 6 **done with
  an empty result** so the corruption was never revisited. Absent and corrupt are now separate,
  corrupt leaves the phase open. Same fix in `phase_shelve`, which would otherwise have shelved
  the whole library tierless and marked itself done. verify_math §19c pins the write contract.
- **[m10] build_terminal escaping** — new JS `esc()` applied to every catalogue-derived
  interpolation (headings, endonym, roster, 4 SVG titles, `data-k`, 7 SVG text renders), and the
  `NAVTREE.json` splice now neutralises `<` as `<`, killing `</script>` / `<script` / `<!--`.
  Live-verified: 734 nodes still parse, and a name carrying `<img onerror=…>` renders as literal
  text with 0 injected nodes.
- **[m14] topicless entries** — a `topic` failing its enum check left no key while
  `catalogued=True` blocked revisiting, silently dropping the entry from `worldseed` and `weave`
  forever. Now an explicit `"unclassified"` sentinel plus `topic_rejected`, matching the
  `magnitude`/`scale_note` idiom. **Prophylactic: 0 of 55,653 catalogued entries are currently
  affected.**
- **[m15] `endpoint.fetch_raw` filed refusals as absences** — 403/429/500 were indistinguishable
  from 404 to the caller. Signature unchanged; the ledger now splits `fetch_raw-absent` from
  `fetch_raw-refused-<code>`, where the counts are what tell a block from a missing page.
- **[m20] dead loop deleted** with owner sign-off. Its comment is kept — the decision it records
  (counting instances belongs to the reconcile tier) is still true.
- **[m7] was already fixed; the entry was stale.** `handbuilt.py` writes through
  `tmp` + `silence.replace_retry` with a landed check.
- **NEW: `the local model has a live runner` standard added** (high, machine, OWNER lane) —
  `/api/ps` naming a resident model with no `llama-server.exe` process is a flat contradiction
  and was the exact shape of run #3b's 31-minute invisible outage. Fires on a simulated wedge,
  silent when it cannot tell, TTL-cached at 120s. No REMEDIES entry by design: restarting a
  service is not automation this pass will switch on unasked.

*Run #3b (2026-08-24 00:00, continuation pass). Full detail in HANDOFF.md's run #3b entry:*

- **Ollama was hard down and self-sustainingly wedged** — queue saturated (`maximum pending
  requests exceeded`) while `/api/ps` reported a resident model with **no `llama-server.exe`
  runner process in existence**, so nothing drained the queue and every call, including each
  attempt to load a model, failed instantly. The phase runner logged 59 unbroken 503s in 31
  minutes doing zero work. Fixed by restarting the daemon; a real runner now holds 8.5 GB VRAM
  and the 503 loop stopped dead. **This corrects run #3's diagnosis of "GPU contention"** — a
  wedge, not contention, and it would never have cleared by waiting.
- **[m18] `foreman.py`'s three shared-state writes** (`POOL_PROOF.json`, `FOREMAN.json`,
  `failures_archive.json` + the `failures.json` reset) now use `tmp` + `silence.replace_retry`,
  the pattern `_retire()` in the same file already used. Readers confirmed live in all three
  cases; the `failures.json` reset was the one that could lose a concurrent `health.flush()`.
- **[m19] `standards.report()` sorted work orders alphabetically** (`high < low < medium`, so
  every MEDIUM printed below every LOW). Now uses the rank dict `work_orders()` already defines.
  Verified live: HIGH, HIGH, MEDIUM×5, LOW, LOW.
- **[m21] `kill_duplicate_jobs` was registered as a bare lambda**, so it logged itself as
  `<lambda>` in the operational log. Unwrapped.
- **[m22] `catalog.py`'s docstring advertised a `PANSCRIPTUM://…` address form the code has
  never implemented.** Replaced with real `SpineCode/Chapter[#PageRange]` examples, both verified
  to answer.

*Run #3 (2026-08-23 23:06, export commit `cc42d0c`). Root causes one line each — full detail in
HANDOFF.md's run #3 entry:*

- **Doc-ingested entries stranded permanently by the entrypass resume gate** — the resume key
  `source#start` names a span `entries[start:start+B]` that GROWS when `ingest_doc` appends
  through `write_record_catalogue`, so the tail batch widened under a key already in
  `done_keys` (Arcanum Worlds: 292 → 297 entries, 5 never judged). Gate now reads the span, not
  the ledger (`pipeline.batch_settled`); verify_math §18d pins it.
- **`ingest_doc.mine()` advanced its resume cursor on a denied write** — `write_record_catalogue`'s
  landed-flag was discarded, so entities never written were skipped forever and `known` had
  already absorbed their names. Denied write now rewinds `known` and stops without advancing;
  state file also made atomic.
- **[m3] `completeness.py` dropped any source whose every category probe failed** — `work()`
  returned `None`, deleting the row from `COMPLETENESS.json`, where absence reads as "no wiki
  presence". New `category_size_probe()` returns `(n, error)`; all-probes-failed lands in
  `unreliable`. `category_size()` unchanged for other callers.
- **[m4] `wiki_source.page_text()` abandoned a page after one transient failure** — `return ""`
  instead of `continue` on a section-0 exception skipped the independent sections 1 and 2. High
  volume: 1,700–3,200 URLErrors per foreman round at this site.
- **[m5] duplicate `silence.note()` label `wiki_source.py:278`** across two unrelated sites —
  split into content labels; `:301` likewise.
- **[m8] Hard Rule 0: "Shelved here" roster sliced to 8** (node 6.6.6 hid 30 of 38) — uncapped,
  bounded by scroll rather than by a "+N more" that would still leave 30 names unreachable.
- **[m9] "contains" row undercounted** — `a||b||c` returns the first non-zero, so 6.6.6 showed
  7 instead of 45; 37 nodes affected. Now sums. m8/m9 live-verified in the browser.
- **[m11] `navtree.sources_under()` false-matched on a digit prefix** — `key.startswith(path)`
  lacked the `.` boundary its sibling arm has; `0.1.2` counted as above `0.1.20`.
- **[m17] `weave_index.designations()` cached forever** — now keyed on the same directory
  signature as `load_records()` (shared `_records_sig()`); explicitly-passed record lists are
  no longer cached at all, having no signature to key on.
- **`address.spine_code_for()` shelved two sources into DC Comics** — the index's two-letter
  `"DC"` matched raw letters with spaces stripped (`swor-d-c-oast`), so `Sword Coast
  Adventurer's Guide` and `Who Framed Roger Rabbit (…)` both returned II.D.2, and matching
  *wrong* kept them out of the unassigned report that would have caught it. Containment now
  runs on whole words, with letter-equality kept as its own tier for spacing variants
  (`Soulcalibur`/`Soul Calibur`). No volumes were mis-shelved; nothing to regenerate.
- **`manifest_builder.load_record()` missed truncated record slugs** — tested only `target in
  filename`, so a 304-entry catalogued record reported as "no matching record file". Reverse
  arm is prefix-anchored, candidates ranked by closeness.
- **`foreman._checks_pass` kept patches that broke a round number of checks** — `"0 FAILED" not
  in stdout` is satisfied by `"10 FAILED"`, `"20 FAILED"`, `"100 FAILED"`. Now parses the count
  numerically and fails closed on an unreadable result line.
- **`standards.py`'s stall detector could never fire, for any job** — the watch stamp was
  re-written every pass, so "how long silent" measured checker cadence; and jobs were derived
  from log filenames (`read_auto.py` has never existed), hiding the three live jobs while
  matching stale legacy logs as alive. Stamp now carried forward (`standards.job_stamp`); jobs
  taken from the new `lognames.OWNER` map, which `foreman.kill_stalled_job` also now uses.
  verify_math §19b pins both. **Its AUTO remedy is destructive and was previously inert — see
  the flagged item at the top of HANDOFF.md run #3.**

*Run #2 (2026-08-23 late, export commit pending as of this write). Root causes one line each —
full detail in HANDOFF.md's run #2 entry:*

- **`cascade_bridge._bury()` raised `UnboundLocalError` on every call, never benching a
  provider** — a dead `if _DEAD is None: _DEAD = {}` guard made `_DEAD` local-by-assignment for
  the whole function; removed, mutate the module-level dict directly.
- **Phase-1/phase-2 band gates laundered a fabricated Assay decimal into a clean band**
  (`re.match(...)\b` matches a `.`) — replaced with `pipeline.clean_band()` (full-match) at
  acceptance, `pipeline.ceiling_band()` (still lenient) at the clamp.
- **`write_record`/`write_record_catalogue` marked a unit done even when the write was denied**
  — both now return whether the rename landed (`pipeline._landed`); both call sites gate on it.
- **`handbuilt.py` crashed on its own `moth_number`'s Fraktur A before ever writing its
  artifact** (cp1252 console) — write now happens before the report loop; console reconfigures
  to UTF-8 after.
- **`rigor.bradley_terry()`'s `undefeated`/`winless` always empty once a prior was set** — the
  symmetric prior was folded into `W` before those two lists were read from it; now computed
  from a pre-prior copy.
- **`rigor.mathematical_resonance()`'s returned `load_bearing` field capped at 8** (Hard Rule 0)
  — uncapped; console print still slices for display only.
- **`render.children_of()`'s child-tier gate asserted a schema (`SF.TIERS`) instead of reading
  the actual tree** — changed to `child_tier is None`; the existing per-entry check does the
  honest work. (No behavior change today — SEVENFOLD.json doesn't chart past `universe` yet —
  but the old form would have silently stayed empty once it does.)
- **stale `silence.note()` label** `derivation.py:490` said `:488` — renamed to a content label.
- **disk pressure (BUGS M2)** — resolved itself between runs (~5 GB -> 135 GB free); no fix
  needed, moving straight to paper trail.

*Run #1 (2026-08-23, commits fc390a9…b16f631). Root causes one line each:*

- **ingest_doc used `write_record` (disk-wins merge) and its first 14 finds were discarded** —
  wrong side of the two-writer contract; → `write_record_catalogue`, cursor reset, both merge
  directions pinned by verify_math §18c (b16f631).
- **`os.replace` PermissionError killed an assay worker mid-batch** — Windows denies rename
  while a reader holds the target; → `silence.replace_retry` shared helper on every
  reader-raced state file (fc390a9).
- **standards' floors self-check blind to a dead floor** — substring match defeated by a
  comment mention and a prefix collision (`MAX_UNANSWERED[_RECORDS]`); → word-bounded,
  comment-stripped matcher; dead floor deleted (fc390a9).
- **Catalogue tools wrote records raw** (truncating, non-atomic, racing the pipeline) — →
  routed through the new catalogue-side merge writer (fc390a9).
- **feats/read evidence caches: truncated file = permanent silent entity loss** — unguarded
  json.load of a cache killed mid-write; → atomic writes + self-healing reads (fc390a9).
- **`_WIDEN_RR` rotation cursor raced by worker threads** — re-pinned the pool to one bucket;
  → locked (fc390a9).
- **`foreman._retire` truncating write on overwatch's ledger** — → atomic (fc390a9).
- **`restart_reader` never restarted anything** (both branches returned without acting) and
  **both foreman process-killers filtered `python.exe` only** (jobs run under pythonw) — →
  reader bounce implemented; filters widened (fc390a9).
- **standings jobs stayed down for hours after a mid-cycle death** — the cycle only re-asserts
  at its top, then blocks in run/join; → keeper thread re-asserts every 5 min (d4745fa).
- **`silence.py --instrument` resurrected the 5,672-row probe-noise ledger class** — the
  rewriter can't distinguish deliberate silence; → `silence-exempt` string markers honoured by
  both audit and instrumenter (fc390a9).
- **Epoch-mandate bypass through the split retry** (morning); **split-gate accepted fabricated
  wrappers**; **entry bands could exceed their source's ceiling** (Starkiller Base M5 in M4)
  — all gated/clamped; reconcile check added (earlier commits, same day).
- **~146 PowerShell spawns per standards.check** (dashboard polls it at 5s) — one shared
  enumeration, 3s TTL, invalidated on launch; check now 2.3s (d4745fa).
- **chain.harvest re-parsed 56k files/900MB per cycle** — incremental mtime index; 3.1s warm
  (fc390a9). **weave_index.load_records re-parsed 63MB per dashboard poll** — signature cache
  (fc390a9). **13MB sweep parsed twice per batch** — once (fc390a9).
