# PANSCRIPTUM — HANDOFF

*Hand-written. `src/pipeline.py` rewrites its own status block below the line; everything above
it is durable and should be read first.*

Last substantive update: **2026-08-23** (section 0b is the day; the 2026-08-22 sections below it stand unchanged)

---

## 0. HARD RULE — NO CAPS — NO CAPS. EVER. (owner directive, 2026-08-22)

**Every IP and every reference is MANDATORILY UNCAPPED.** No limit, no cap, no sample, no
"top N", no truncation of a roster, a page list, a chunk list, or an entry list. If a wiki
lists 40,000 characters, the library takes 40,000 characters.

This is not a preference about thoroughness. A cap on an ordered listing is not a sample, it is
a TRUNCATION, and it silently decides that everything past the cutoff does not exist:

* `roster(limit=600)` returned Dragon Ball A-through-G. **Goku fell outside the window.**
* `roster(limit=6000)` on DC returned Abin Sur, Ace, Adolf Hitler. **Superman, Wally West and
  Wonder Woman fell outside the window.**
* `cap=250` took the alphabetical head of every missing-cast repair.
* `cap_chunks=12` decided on an entity's behalf that the rest of its own pages did not count.

Every one of those looked like a completed job. That is the whole danger: a cap does not fail,
it returns a smaller universe wearing the same shape as the real one.

Ranking is still allowed and is encouraged — order by article size or evidence density so the
richest material lands first if a run is interrupted. **Ranking then truncating is not.**

If something is genuinely too slow, the answer is more workers, more providers, or more time.
It is never a smaller universe.

---

## 0b. 2026-08-23 — DOCTRINE, THE CAP PURGE, THE LOOP WAR, AND THE ASSAY GOING INDUSTRIAL

The audits carry the detail (`handoff/AUDIT_2026-08-23.md`, `handoff/AUDIT_2026-08-23_EVENING.md`
— every module read line-by-line, morning and evening). What a successor must know:

**OWNER RULINGS, ratified in FOR_OWNER.md and encoded in the code the bots execute:**
- **Magnitude = capacity to decide outcomes at scale.** Person -> who would win; equipable ->
  the delta granted to a possessor; anything else -> effect within what it can interact with.
  One quantity, three manifestations (Yggdrasil sustains / Dr. Manhattan acts / the Infinity
  Gauntlet grants), which keeps unlike things comparable. Restates Part Three's own "decide,
  not merely break". Lives in `magnitude.SYSTEM` and both `pipeline` glosses. The
  presence-attendance reading is retired to `data/REFERENCE_ASSAYS_PRESENCE.json`
  (`_superseded` note inside); the charter's published Goku/Naruto/Luffy values stand as canon.
- **Epoch-mandatory sources** (`identity.EPOCH_REQUIRED`): mtg.fandom.com (the MENDING —
  oldwalker vs neowalker are different power classes) and forgottenrealms.fandom.com (Time of
  Troubles / Spellplague / Second Sundering). An unstamped sheet for these hosts is REFUSED and
  requeued, enforced in `assay_entity` on every path including the split-retry. One entity may
  hold multiple accessions, keyed `host|name@epoch`.
- Travel is Vector, never the anchor (the Jace clause, in the prompt).

**THE CAP PURGE.** `catalogue_web.MAX_PER_SOURCE = 320` silently truncated every source's cast
— Marvel held 1,051 of 103,554 characters; Molecule Man, Mxyzptlk and the Black Winter all read
as "not in that fiction". Removed, with a guard that refuses to run if re-capped. Marvel
re-catalogued to **30,207 entries**. `completeness.py` measures every source against the wiki's
own categoryinfo (excluding rows whose denominator it cannot stand behind); the
`every source is fully catalogued` standard (floor 1.0, deliberately unsatisfiable) keeps the
catalogue dispatching itself. `wiki_source.find_categories` now DISCOVERS a wiki's real
categories from its own allcategories listing (pro wrestling's cast lived in "Male wrestlers",
13,314 pages — the fixed probe list had catalogued 158 COUNTRIES from a nationality grouping).

**THE FANDOM IP BAN.** `wiki_source.MIN_GAP=0.01` (100 req/s, benchmarked on 60-page samples)
drove the Marvel pull; fandom.com dropped this machine at the socket for hours. Rate is 0.15s
now, `feats._throttle` is the shared politeness layer, `endpoint.detect` DEAD verdicts expire
(24h — a bad hour must not brand a host permanently unreadable), and a `fandom answers this
machine` standard plus a socket gate on the catalogue remedy stop the automation dispatching
into a block. Ban shape: fandom HTTP 000 at the socket while Wikipedia answers in 0.2s.

**GITHUB WAS 122 COMMITS BEHIND, SILENTLY.** Session `GITHUB_TOKEN`/`GH_TOKEN` PATs override
the keyring gh login and 403 every push; supervisor children lacked gh-cli on PATH.
`publish.git()` sheds both. The export repo moved out of the session scratchpad to
`C:\Users\imarl\panscriptum-export` (`PANSCRIPTUM_EXPORT` set at User scope). Backup strays
(`src/*.pre*`) were being published to the public repo; SKIP_SUFFIX extended, backups now live
in `state/backups/`.

**THE LOOP WAR** (an afternoon of black windows and 3-minute respawns). Root causes, each now
guarded: `overnight.running()` and `autostart.supervisor_alive()` filtered on `python.exe`
ONLY and went blind when the stack moved to pythonw — the watchdog restarted a "dead"
supervisor every cycle; THREE watchdogs ran at once and their supervisors' foremen shot each
other's stacks (`kill_duplicate_jobs` may now never target overnight/autostart; watchdog and
supervisor both carry self-guards); a creationflags mass-patch omitted the `_NO_WIN` constant
in overnight and the NameError sat inside `silence.note` for an hour; and every
powershell/wmic/python/git child of a windowless parent ALLOCATES A CONSOLE unless
CREATE_NO_WINDOW is passed — it now is, in every module that spawns. The Startup `.vbs`
launches pythonw.

**THE ASSAY WENT INDUSTRIAL** (7 scored -> 210+). `magnitude.py` now has: the cascade pool
with a proof-ranked fallback (POOL_PROOF.json first — config order was a graveyard tour, ~100
failed calls per success; and the router never hands out local buckets, which had flooded one
10GB card with three competing model loads until Ollama answered everyone "maximum pending
requests exceeded"); `--batch` with `settled()` (a score, "no axis cleared its gate", or a
saturation refusal are findings; everything else requeues); the SOURCE CEILING clamp from
`data/SCOPE.json` via `host_ceiling()` (Jace one-shot at M10.77 against the charter's
published M2.88 — the clamp existed all along and only calibrate() ever passed it);
SPLIT-FIRST above `ONE_SHOT_MAX=30k` (the recall cliff: 36k chars gave 19 feats vs 41 at 10k)
with per-axis slices, an anchor call over the winning citations, `_split_gate` (verbatim
containment ONE WAY — a fabricated wrapper around a real quote fails), and a split-RETRY when
a one-shot's every citation fails verbatim (a transport's bad day is not the entity's evidence
ceiling). Every gate re-applies to the retry — epoch and clamp both; the bypass was the
evening sweep's C1. `feats.AXIS_ACT` vector vocabulary gained
planeswalk/plane shift/apparate/shunpo/flash step/blink/portal/rift — the most famous
planeswalker in fiction had VECTOR unestimable because his franchise's own verb was not in the
list. Proof of the whole chain, bots only:
**Jace M10.77 -> A M2.56 +/- 0.08 with vector scored, vs charter M2.88 +/- 0.25.**

**AUTOMATION CLOSES ITS OWN LOOP.** 35 standards (new today: jobs must be ADVANCING, not
merely alive — log growth vs a stored snapshot; catalogue coverage vs the wikis' own counts;
sweep-freshness vs the newest record; fandom reachability). Foreman: per-remedy AND per-round
exception guards (one remedy's TimeoutExpired once ended the autonomous loop permanently),
remedy timeouts bounded under the loop interval, `always`-remedies (a measurement is not an
alternative to a repair — Marvel read 0.4% coverage for 18 hours after it was actually fixed),
kill_stalled_job / kill_duplicate_jobs, and the catalogue / sweep / completeness / adopt
dispatches all fire from work orders. Work-order lifecycle: standards orders are STATELESS
(met floor -> order gone next round), FOR_OWNER.md is regenerated whole each round, overwatch
findings keep closed history for recurrence detection — delete-on-resolve for orders,
keep-on-resolve for findings. `allsweep` gained a LINT tier (pyflakes on every module, every
run — undefined names are how two of the day's faults hid behind silence.note). `lognames.py`
is the single place job log filenames live; dashboard, standards and foreman all read it.

**PIPELINE SAFETY.** `pipeline.write_record` now MERGES when the on-disk record has drifted —
the recatalogue and the phases are two whole-file writers, and the pipeline's stale in-memory
copy would have silently reverted Marvel 30,207 -> 1,051. `chain.write_result` is the ONE
writer for CHAIN.json (two callers had two schemas). `update_handoff` derives its phase table
from IMPLEMENTED (the hand table said "to build" about built phases, published every unit) and
caches its counts (it was re-parsing ~86k entries after every completed unit).

**CURRENT STATE (2026-08-23 ~21:00).** Catalogue 85,904 entities across 210 sources (Marvel
30,207; DC re-catalogue running). ASSAYS.json: 507 records, 210 scored; multi-accession keys
live. Standards 27/35 met (reds are the evening pool tide — free-tier daily windows drained —
plus coverage pending DC and settled 47%). Overwatch open findings: 0 (all six triaged with
recorded verdicts; one was checked against the code before refuting). The swallowed ledger was
94% one probe artefact (35,806 entries from overnight.running noting its own output's
formatting rows) — cleaned; what accrues now is real pool-decline noise. Running unattended:
one watchdog -> one supervisor -> one of each job; the mandate-era 400-batch; DC recatalogue;
host adoption; Jace's two accessions plus the Infinity Gauntlet (the equipable doctrine's
first live test) queued behind the thin pool.

**BITES ADDED TODAY.** A batch in flight carries the code it launched with — bounce
read/foreman/overwatch after editing anything they import. Evening = pool tide: expect defers,
not failures; nothing false publishes and settled() requeues everything. wmic/powershell/git
spawned from pythonw flash console windows without CREATE_NO_WINDOW. Never run project
commands after cd-ing into the export copy — the `.is-export-copy` guard refuses, and it fired

**LATE EVENING (2026-08-23, after the sweep).** The engineering-rubric pass, executed:
(1) **The charter regression is a standard now** -- `magnitude.py --calibrate` runs the six
published assays through the whole live chain and persists `data/CHARTER_REGRESSION.json`;
the `automation reproduces the charter` standard (consistency = interval OVERLAP, 26h
freshness) dispatches `run_charter_regression` via the foreman, gated on >=3 answering
buckets. (2) **verify_math section 18b**: the assay's five transport paths (one-shot, junk ->
split-retry, epoch refusal, no-transport defer, split-first) proven under a fully mocked
model -- **267 checks, 0 failed**, runs with the pool down. (3) **Per-call metrics both
lanes**: `pipeline.ask` (tok/s from Ollama's eval counts) and `cascade_bridge.ask` (wall/ok)
append to `state/model_metrics.jsonl`; the dashboard grew a per-lane p50/p95 panel. (4)
**Band reconcile**: allsweep flags any entry banded above its own source's synthesis ceiling.
(5) README rewritten to the real architecture. (6) **`the library's counters are moving`
standard**: the owner caught a 36-minute output flatline (fourteen processes alive, logs
streaming timeout lines, cited/settled/feats flat) that log-growth liveness cannot see; the
dashboard's own movement history is now the measurement, remedied by reprove+restart-reader.
Cause that evening: the GPU thrashing between a benchmark's gemma load and the batch's 30B
calls under MAX_LOADED_MODELS=1, atop a 13%-ok evening pool -- never bench on a contended
card.

**TWO OWNER RULINGS, encoded in the prompt layer:** the **Scale Ladder**
(`prompts/scale_ladder.md`, digest in `system_style.txt`) -- ten rungs from Household to
Omniverse, every topic written at its own altitude, cross-reference upward instead of
re-explaining cosmology in a village, honest N/A rungs, Xeno on its own terms; and **VOLUME
DEPTH** -- every volume is a full-length book: `generate.py` now writes chapters in
WRITE_CHUNK=8-entry blocks with per-entry presence verification (one retry, then a LOUD
job failure that stays pending), `num_predict: -1` so Ollama's default output cap cannot
end a chapter mid-entry, and `prompt_version` bumped to v5 so every thin pre-ruling volume
regenerates. The model bench (gemma3:12b vs the 30B MoE for judgment phases) remains open --
run it in a quiet window, never beside the batch.
for real today, correctly.

---

## 1. WHAT THIS PROJECT IS, IN ONE PARAGRAPH

An omniverse encyclopedia assembled from ~212 fictional sources, addressed against the charter's
own spine codes, where **every claim traces to a sentence on a real source page**. The hard part
is not prose. It is that Charter Part Three's Custodial Assay demands a worksheet of cited feats
behind every Magnitude decimal, and the catalogue's own entry descriptions cannot supply one.

## 2. THE ONE DEFECT THAT GENERATED ALL THE OTHERS

Read this before debugging anything.

Eighteen separate faults were found on 2026-08-21/22. Listed as a list they look like bad luck.
Lined up by SHAPE they are one fault:

| what happened | what it looked like |
|---|---|
| Wikipedia served 404 (wrong API path) | "these 5,590 entities have no page" |
| chunks overflowed `num_ctx`, silently truncated | "the model fabricates 51% of the time" |
| `\b` arrived as a 0x08 backspace (six times) | "the gate is too strict" |
| a batch closed on write, not on result | "judged" — 378 entries stranded forever |
| failed synthesis wrote an empty block | "no ceiling exists here" — and could never retry |
| the evidence gate could only see Ruin | "no evidence on the other ten axes" |
| `strip_wikitext` ate template-wrapped articles | 3,736 entities "read as empty pages" |
| slug-guessed hosts answered, wrong fiction | 2,765 pages mined from *Descent* the board game |
| a wrong host wrote a wrong ROSTER | `Lost Mines of Phandelver` holds 262 characters from the TV series *Lost* |
| the reader crashed on its own banner (`%d` vs an uncapped `None`) | supervisor logged ten tidy `finished` lines in five minutes |
| an unsynchronised lazy transport probe raced 10 workers | Cascade resolved False, permanently, in silence |
| `claim()` ranked and reserved non-atomically | 8 workers claimed one free-tier meter; 8 calls that take 3s together took >120s |
| `claim()` called `candidates()` (0.27s) inside the flight lock | raising workers made the run SLOWER |
| the reading loop called `P.ask`, never `_ask` | the whole morning ran on one GPU while 13 cloud buckets idled |

**Every layer converted a failure into a plausible NEGATIVE RESULT.** That is the defect. The
eighteen were its output, and each cost a full investigation to tell "broken" from "genuinely
empty" — because in this library an honest absence is a real finding, so a swallowed failure
lands in exactly the shape the design trusts.

### The fix that closes the class — `src/silence.py`

```bash
python src/silence.py              # audit: how many handlers still swallow silently
python src/silence.py --instrument # insert a recorder into each one (.presilence backups)
```

It parses every `except` in `src/`, decides whether the body records, logs, re-raises, or carries
the exception into its return value, and reports the rest. On 2026-08-22 that was **67 of 80**;
59 were instrumented automatically and the remainder are either deliberate (the recorder must not
record itself) or were fixed by hand. Each instrumented handler now calls `silence.note(site)`,
which counts the failure BY CLASS into `state/failures.json` and flushes every 25 records, so a
job failing every call from its first minute stops looking like a job working slowly.

`overnight.py` prints the top swallowed failures each cycle. That report is the payoff — treat a
new entry in it as a bug, not as data.

**Three more defences, all of which must be kept:**

- **`src/health.py --preflight`** — before any long job. Context arithmetic, API path per host
  family, control characters in source, caches empty in a way that means *broken*, state
  consistency. It found the wrong-wiki bug on its first run. Keep it CHEAP: it once parsed 200
  full records per host and pushed a supervisor cycle past five minutes before any work started.
  It now judges emptiness by file size (0.8s for the whole tree).
- **A load-time guard in every regex-bearing module** that refuses to import if a control
  character is present. It has caught two more since, including one where the failure would have
  been invisible-but-total (no word boundary ⇒ `he` matches inside `the` ⇒ every sentence passes).
- **`src/hostcheck.py`** — see §3a. Existence was never the question; aboutness is.

## 2b. THE FULL AUDIT — `src/allsweep.py` and `src/estate.py`

```bash
python src/allsweep.py            # everything, ~45s across 12 workers
python src/allsweep.py --quick    # imports and reconciliation only
```

Nine verifiers existed and every one of them worked. **Nothing ran them together**, so the
project was verified the way it was debugged: whichever symptom happened to surface. Five tiers
now run at once, and the first pass found faults in every one.

**IMPORT** — `--help` against all 68 modules. That is the cheapest total exercise there is: it
runs every import, every module-level constant, every regex compile and every load-time guard,
without doing any work. Four modules could not start:

| module | error | how long |
|---|---|---|
| `verify_math` | `module 'feats' has no attribute 'kinetic'` | unknown |
| `anchors` | same | unknown |
| `ledger` | `cannot import name 'MATERIAL' from 'feats'` | unknown |
| `address_space` | `xenoverse=11 does not fit in 3 bits` | since the address grew to 8 tiers |

`verify_math` is the module whose entire job is independently verifying every number this
project computes. **It had not run in some time and nothing noticed, because nothing invoked
it** — which means every number it checks had been unverified for exactly as long.

The cause was ordinary: the physics constants lived in `feats.py` when `feats.py` was a feat
CALCULATOR, and went out with the rewrite that made it a wiki miner. They now live in
`src/physics.py`, which is their proper home — energy constants have no business in the module
that makes HTTP requests. `address_space` failed on a demo written for a five-field address and
never updated when three tiers were added; it now passes by keyword and writes
`data/SHELFMARKS.json`, 1,016 worlds, zero collisions, which nothing had been producing.

**VERIFY** — each verifier runs for real. `verify_math` now reports **237 passed, 0 failed**.

**ESTATE** — every file in the tree, opened. 45,421 of them, no sampling. This matters more here
than in most projects because of how every stage reads `data/`: open, `json.load`,
`except: continue`. A record that will not parse is skipped in silence by every consumer, so a
corrupt cache is indistinguishable from an empty one — and "empty" is a legitimate finding in
this library. Four problems found, two of them perfect: **`handoff/HANDOFF.md` contained two
0x08 control characters, in the table row describing the control-character bug.**

**CHARTER / WRITTEN / TERMINAL / EXTERNAL** — the specification against the code, the prose
against the roll, the viewer's data files, and the dependencies that live outside the tree
(Ollama, Cascade, disk).

**RECONCILE** — where the subsystems disagree, which no single verifier can see. This is the
tier that earns the file: it caught 53 catalogued sources with no host (17.5% of the library,
uncitable by construction), 17 orphan cache directories, and a runner naming phases nobody had
implemented.

### The Assay was publishing false confidence

`verify_math`'s one real failure, invisible for as long as the module would not import:

```
ruin = 0.0           coverage 0.73   interval 0.12
ruin = UNESTIMABLE   coverage 0.58   interval 0.11   <-- LESS knowledge, NARROWER bar
```

`SIGMA_UNKNOWN` is range/sqrt(12) = 2.86, the maximum-entropy dispersion for a 0–9.9 scale — the
most uncertain a single axis can honestly be. The attestation sigmas had been fitted to reproduce
the charter's published intervals back when `_interval` had ONE component, so they absorbed the
between-hand disagreement that now has a term of its own, and Witnessed came out at **4.08 —
wider than knowing nothing at all.** An axis nobody could read published more confidence than one
that was measured.

`SIGMA_MAX` is now a hard ceiling, the grades are rescaled to preserve the charter's ordering
exactly, and the between-hand term carries what the inflation was standing in for. The three
calibration assays still land 3/3 inside the charter's published intervals.

## 2c. THE STANDING SWEEP — `src/overwatch.py`

```bash
python src/overwatch.py                    # one round
python src/overwatch.py --loop 20          # what the supervisor starts
python src/overwatch.py --show             # the open findings
```

`allsweep` is a snapshot — somebody runs it, reads it, acts. Every fault in this project's
history was detectable by a measurement nobody was taking *at the time*. The supervisor now keeps
a watcher alive between cycles, and it watches two different things because they fail differently.

**Structure** — imports, file integrity, reconciliation. Objective, cannot miss a break, cannot
invent one. The deep file walk runs every 6th round; the import tier runs every round, because
that is the one that caught four dead modules.

**Semantics** — the model reads the modules. This is what structure cannot reach: `read.py`
calling `P.ask` instead of `_ask` was valid Python, correct types, no exception, and cost the
entire cloud pool for a morning. Reading the code catches it in ten seconds; no import check ever
will. It runs on the local GPU by preference — the corpus reads through Cascade now — and falls
through to the cloud when the card is busy, because a watcher that stops watching during busy
periods is the thing this file exists to prevent.

Findings pass three filters or they are discarded: the named symbol must exist in the file (a
claim about "the error handling" is unverifiable and half of them are hallucinated); each is
fingerprinted and reported once, staying open until that file changes; and the prompt asks for
exactly one class of thing — code that does something other than what it says. `WATCH.md` is the
report; `data/OVERWATCH.json` is the ledger.

### What building it found, live

```
1140/33417   9.89 chunks/s   chunks 7083/50821   (5090 fell back to the GPU)
```

**5,090 of 7,083 chunks — 71% — were declined by every transport, returned nothing, and were
counted as read.** The entities were then written to cache, which marks them done forever:
`read_entity` returns the cache on every later call and `queue` never revisits them. Not
incomplete records — *permanently* incomplete ones, indistinguishable from entities that
genuinely had fewer feats. Nothing raised, nothing logged, and the progress line said 9.8 chunks
a second.

Two fixes. An entity is cached **only when every chunk was answered**, and the pool now backs off
and retries instead of failing fast — when free tiers are saturated the honest options are "wait"
and "use the GPU", never "skip the passage". The 1,097 records written in that window were
deleted for re-reading.

## 2d. WIKIS THAT ARE NOT FANDOM — `src/endpoint.py`

Every request assumed `https://{host}/api.php`, with one bolted-on case for Wikipedia. That is
wrong three ways, and each looked like an absence:

```
rimworldwiki.com    serves /api.php but is not Fandom
many wikis          serve /w/api.php but are not Wikipedia
www.dandwiki.com    answers EVERY API call with HTTP 403 — logged-in users only
```

D&D Wiki holds the third-party and homebrew shelf, which is most of what this library had no host
for. Its API is closed and `index.php?action=raw` is wide open, returning exactly the wikitext
`prop=revisions` would have — one title per request instead of fifty. Slower, and not nothing.

`endpoint.detect()` probes each host once and caches the answer: `api` at some path, `raw`, or
`dead`. `feats.fetch` and `hostcheck.probe` both route through it. Discovery on a raw host is the
entity's own title only — there is no search to ask — which is thinner coverage honestly stated
rather than one title returned as if the wiki had been searched.

## 2e. LIFT, NOT HIT RATE — the control that replaced three hardcoded rules

A hit rate means nothing alone, because hosts differ enormously in how generous they are with
names they have no reason to hold. Measured, by probing each host with *foreign* names drawn from
other sources' rosters:

```
en.wikipedia.org              answers  50% of FOREIGN names
forgottenrealms.fandom.com    answers   8%
dc.fandom.com                 answers   5%
www.dandwiki.com              answers   0%
```

Judged absolutely, 33% is weak. Against those baselines, **33% on D&D Wiki is thirty-three points
of signal and 33% on Wikipedia is worse than chance.** Both readings were made here and both were
wrong: the homebrew shelf was rejected from the wiki that hosts it, and `Rocket League` was nearly
adopted onto Wikipedia because its entities are ordinary words with ordinary articles.

`score()` now reports **lift** — observed minus baseline — and it needs no per-host rule and no
hostname exemption, because the encyclopedia's generosity is the thing being subtracted. It is the
same move `weave.py` already makes with its permutation threshold: measure what chance produces,
then require the observation to beat it. The aboutness veto survives only on generous hosts
(baseline ≥ 25%), because where a host answers for almost nothing the hits *are* the evidence —
and demanding aboutness there rejects every sourcebook, whose title names a product and not a
world.

## 2f. ALL EIGHT PHASES ARE BUILT

`cosmology`, `history`, `shelve` and `write` existed as finished modules with no phase to
dispatch to them. Worse, `chain` was finished AND had a phase, and the runner still reported it
"not implemented yet" — because `IMPLEMENTED` was a hand-written dict of three entries that went
stale the moment anybody wrote a phase without remembering to add it. The runner stopped at phase
4 every single time, so 5 through 8 were never attempted.

`IMPLEMENTED` is now derived from `PHASES`: writing `phase_<name>` **is** registering it.

```
5 cosmology   209 sources charted, 1,016 worlds addressed, 0 collisions
6 history     209 shelves placed by ratification depth, 3 contemporaneity classes
7 shelve      55,749 entries placed with spine codes and shelfmarks
8 write       4,029 generation jobs across the 117 settled sources
```

**Phase 8 refuses to write about a source whose entries have not been read** (`WRITE_SETTLED_MIN
= 0.60`). Prose about an entity with no evidence is the one output that would undo everything
above it: same voice, same shelfmark, same confident interval, indistinguishable from the cited
kind. A library that writes about what it has not read is a generator with a card catalogue.

Two of the four crashed on first run against APIs I assumed rather than read, and phase 6's first
draft reported **"0 shelves given an ascension mark"** — a phase that ran, returned empty, and
looked like a finding rather than a wrong call. The signature defect, committed inside a phase
written to close it.

**And running them destroyed this file.** `pipeline.py` rewrote `handoff/HANDOFF.md` after every
completed unit, replacing 629 lines of hand-written reasoning with a status table. Nothing
failed, nothing warned; the loss surfaced only because a later edit could not find its own
anchor, and it was recovered from the first GitHub push. Two authors writing one file, one
silently clobbering the other. The runner now writes `handoff/RUN_STATUS.md`.

## 2g. HOMEBREW IS NOT ON A WIKI — `endpoint.MODE_HTML`

*"for a lot of the homebrew stuff you might have to do a little bit of internet scouring since
homebrew can be inconsistent with where stuff is kept."* Exactly why 6,110 entries were
uncitable. KibblesTasty — 1,335 of them — lives at `kthomebrew.com` and on GM Binder.

A third endpoint mode reads ordinary web pages: strip scripts, styles and navigation (all of
which read as sentences once the tags are gone, and none of which any entity ever did), then take
the text. There is no title lookup, so an HTML source is read from a **registered page list** —
`data/SOURCE_PAGES.json` — with the reader's own name-matching doing the attribution exactly as
it already does for shared wiki index pages. The host map carries a `pages:<source>` sentinel so
every stage asking "does this source have somewhere to read from" gets a yes.

## 2h. THE POOL PROOF — headroom is not evidence

```
36 buckets tested, 11 actually answer
```

Headroom is what a bucket says about its own meters. It is not evidence that the key works, that
the model exists, or that the provider will accept a request — and 25 of 36 reported healthy
quota while answering nothing, each burning a full deadline every time it was claimed.
`cascade_bridge.prove()` sends one three-token call to every bucket; `_alive()` then refuses
anything the proof did not confirm.

**Per-bucket pacing**, the same instrument `feats._throttle` uses on wiki hosts: a claim says
"this bucket has headroom", not "it is your turn". Nine workers across a dozen buckets still put
several requests a second into free tiers allowing ten a *minute*, and 4% of calls were
succeeding. Now 38%.

The reader's local fallback picks **the largest model that fits the card whole**. config.yaml
names an 18.6GB MoE on a 10GB 3080; it fits only by CPU offload, so every fallback blew the
180-second timeout while the card sat at 22% — not busy, thrashing.

## 3. WHERE THE EVIDENCE COMES FROM

```
feats.py    fetch source pages  ->  data/feats/          (45,346 entities, ~370M chars)
read.py     the MODEL reads them ->  data/readfeats/      (verbatim-verified feats)
chain.py    contest outcomes     ->  data/CHAIN.json      (phase 4)
rosetta.py  native power scales  ->  data/ROSETTA.json    (ground truth we did not author)
scope.py    each fiction's scale ->  data/SCOPE.json
coverage.py the dashboard        ->  data/COVERAGE.json
```

**Regex gathers and skips; the model reads.** That division was backwards for most of this
project. Measured on Goku's three pages: eleven regex axis-gates found **13 feats**; the model
reading the same text found **241 across all eleven axes**. Regex now has exactly one job —
cheaply discarding text that cannot contain a feat.

**Every guard stays.** The model's output is verified verbatim against the page it came from,
which caught a 51% fabrication rate before that was traced to context truncation (now 0–4%).
A better reader does not make the guards less necessary; it makes them the only thing between a
fluent paraphrase and a printed measurement.

## 3a. IS THE EVIDENCE EVEN FROM THE RIGHT WORLD? — `src/hostcheck.py`

A source's wiki was guessed from its title and the guess was checked for whether the host
EXISTED. Every wrong one existed:

```
Descent into Avernus       -> descent.fandom.com        the board game Descent
Odyssey of the Dragonlords -> arcanum.fandom.com        the CRPG Arcanum
Unearthed Arcana           -> unearthed.fandom.com      an Egyptology wiki
The Elements Beyond        -> elements.fandom.com       the periodic table
Lost Mines of Phandelver   -> lost.fandom.com           the television series Lost
```

Three tests now run over the whole roll, and all three are needed:

1. **HELD** — do the source's own catalogued names exist as articles there? One batched
   `action=query&titles=` call answers for forty names. A right host scores 60%+, a wrong one
   almost exactly zero, because two unrelated fictions share no proper nouns.
2. **ABOUT** — of the articles that DO exist, are they about this fiction? Rocket League scored
   72% HELD on Wikipedia purely because its entity names are ordinary words with ordinary
   articles. Tokens already spelled into the host's own domain are struck out first, or
   `lost.fandom.com` scores 100% aboutness on the word "Lost". If every distinctive token IS the
   domain (`metro.fandom.com` for Metro), the wiki is *named after* the fiction and passes.
   `prop=extracts` is a Wikipedia extension; most Fandom wikis lack it, so raw wikitext is the
   fallback. Treating its absence as "no text" once made this test silently unavailable on the
   entire Fandom half of the roll.
3. **ROSTER** (`--rosters`) — correcting a host does not correct what the wrong host already
   wrote into the CATALOGUE. Take the source's proper nouns and look for them in the pages mined
   for its own entities: "phandelver" appears zero times in 106,000 characters about a plane
   crash. Proper nouns, not longest words — ranking by length asked whether Pixar's roster
   mentions "films".

```bash
python src/hostcheck.py --repair    # measure every host, repoint or record unfit
python src/hostcheck.py --rosters   # which catalogued casts are from another fiction
python src/hostcheck.py --purge     # dry run;  --purge --go  to actually remove
```

**Candidate generation had silently died.** Fandom's `api/v1/Search/CrossWiki` now returns 404,
and `candidates()` swallowed the error on every call — 124 of them — falling through to slug
guessing while looking like it was searching. Three generators replace it, all from evidence
already on hand:

- **tokens** — each proper noun and each adjacent pair as a slug. `warthunder`, `worldoftanks`,
  `rogerrabbit` — none of which the whole-title slug ever produced.
- **neighbours** — any source whose catalogued roster overlaps this one's by a quarter is about
  the same world, so its host is a candidate. This is what found
  `Explorer's Guide to Wildemount → criticalrole.fandom.com` at 90%: Wildemount *is* Critical
  Role's setting, and no string manipulation on the title would ever have reached it.
- **Wikipedia, ranked last**, because it answers for almost anything and the aboutness test is
  what stops it winning on names alone.

Result: unassigned sources went from 33 to **3** (`Extra Life`, the War Thunder/World-of-Tanks
composite, and `the Witch Tradition` — all genuinely without a wiki that holds them).

**The tool caught itself doing the project's own defect, twice.** Both are fixed and both are the
warning for anyone extending it:

- A probe that threw an `HTTPError` returned `rate: 0.0`, indistinguishable from a wiki holding
  none of the names. Seventy-four throttled probes later, the repair pass unassigned
  `warhammer40k.fandom.com` from Warhammer 40,000. A failed request now returns `rate: None` and
  the verdict `UNREACHABLE — no judgement`, which is never eligible for repair or unassignment.
- Aboutness tokens must contain a LETTER. `Warhammer 40,000` had "warhammer" struck out as
  already-in-the-domain and was left testing articles for the string "000" — a wiki holding 95%
  of its own roster scored 0% aboutness.

### Finding a host at all — `--adopt`

`sweep()` only probes sources that ALREADY have a host, so a source with none was invisible to
it — and 53 of them were, holding 10,059 entries: **17.5% of the library, uncitable by
construction**, and nothing in the pipeline was ever going to mention it. `--adopt` closes that,
and four separate faults had to be fixed before it worked:

- **Fandom's disambiguation suffixes.** When a name is taken, a wiki takes the name plus a
  category word and the bare name goes to whoever got there first. `metro.fandom.com` is the
  **New York City Subway wiki**; the game is `metrovideogame.fandom.com`. Without trying
  `{token}videogame`, `{token}game`, `{token}series` and the rest, the search proposes the
  squatter, measures 0%, and concludes the fiction has no wiki — 303 Metro entries were
  permanently uncitable that way.
- **`exlimit` is capped at 1** unless `exintro` is set, so `prop=extracts` returned ONE extract
  for twelve titles and aboutness was a rate over a denominator of one. Polynesian myth scored
  98% held and 0% about. The whole extracts path is gone; raw wikitext works on every wiki, has
  no limit, and reads the whole article rather than its opening line.
- **The probes were not paced.** `feats._throttle` already paces per host with Wikimedia far
  slower than Fandom, and `hostcheck` was not using it. Six workers produced **1,364 swallowed
  HTTPErrors** in one pass, and an unreachable host reads as a host that holds nothing.
- **The candidate list was ranked and then truncated.** Wikipedia is deliberately added last, and
  the suffix variants pushed it to position nineteen of a list cut at eighteen. Every pantheon
  and astrology source came back "no wiki holds this fiction" while scoring `holds` on a host
  that was never probed. Speculation is now capped; evidence never is — **Hard Rule 0 in
  miniature, and I wrote the truncation myself.**

Wikipedia must clear `holds` (≥35%) rather than `partial`, because it has an article for almost
any noun: one-author homebrew scored 18–32% there and would have been pointed at entirely
unrelated pages. Remaining: **38 sources, 7,070 entries** with genuinely no wiki — nearly all
one-author homebrew, which is an honest NO HOST rather than a gap.

**`--purge` requires `--source`, and that is the most important line in this file.** The audit
asks whether the PAGES mined for a source name that source. A "no" proves the **host** was wrong.
It does **not** prove the **roster** was, and an automatic purge nearly destroyed 1,119 correct
entries on that confusion:

```
Lost Mines of Phandelver -> lost.fandom.com        roster IS the cast of the TV series
Unearthed Arcana -> unearthed.fandom.com           roster IS genuine D&D — Changeling, Shifter,
                                                   Beasthide Shifter, Eberron content.
                                                   Only the wiki was wrong.
```

Both score 0–2% identically, because an Egyptology wiki's articles never say "arcana" either. No
threshold separates them: a sourcebook's title names a **product**, not a world, so "does this
page say Unearthed Arcana" is the wrong question for it. The audit shortlists; a person reads the
roster and decides; ten seconds each. Unearthed Arcana kept its roster and got
`forgottenrealms.fandom.com`; Lost Mines and `the Witch Tradition` (which turned out to be the
cast of *W.I.T.C.H.*) lost 531 entries between them.

Every removal is stamped into the record itself (`purged_roster: {mined_from, removed}`) and into
`data/ROSTER_PURGES.json`, so the gap reads as a finding rather than as a source nobody got to.
Rejections go to `data/HOST_UNFIT.json` for the same reason.

## 3b. CONTINUITY AND EPOCH ARE PART OF IDENTITY — `src/identity.py`

Owner's ruling: *"each continuity in marvel and dc should be their own, not resolved into one,
it's timelines not retcons"*, and the same for Dragon Ball and anything else that branches. A
retcon replaces; a timeline coexists. Kal-El (New Earth) and Kal-El (Prime Earth) are two
accessions, assayed separately, never averaged — an average across continuities describes a being
no source recorded.

Continuities are RECOGNISED, never listed, by three structural tests:

- **orthography** — a continuity is a proper name; Fandom writes its own metadata lowercase, so
  `(Filmation)` separates from `(character)` on every wiki at once, forever;
- **population** — a designator worn by several distinct base names is a place characters live in
  (`G1`: 48 bearers; `Tom Keenlyside`: one, a voice actor);
- **branching** — a designator most of whose bearers also appear under another designator is a
  branch, since that is what a branch is: the same names occurring twice.

Population and branching are each sufficient, neither necessary. A short NEVER list handles
capitalised wiki furniture (`Skill`, `Multiplayer`, `Codex Entry`); every entry there was observed
as a false positive first.

**Epoch** is the fine-grained case of the same error and is resolved only where it bites.
`identity.adjudicate()` takes the chain's MUTUAL pairs — A beats B and B beats A — and dates just
those two sentences. Goku loses to Mercenary Tao; Goku beats Mercenary Tao *"after training with
Korin"*. That is not an inconsistency, it is one entity at two points in its own history, and
collapsing them manufactures a contradiction the source never contained. Where both sides date to
the SAME epoch the pair is left standing: that is a real disagreement and dissolving it with an
invented chronology would be the fabrication this library exists to refuse.

## 4. WHAT "DONE" MEANS — AND WHY IT IS NOT 100% CITED

Every entry sits in one of five states, and **keeping READ separate from NO PAGE is the whole
point**. Collapsing them is what made every silent failure look like an honest absence.

| state | meaning |
|---|---|
| CITED | carries a verbatim feat from its own source page |
| READ | pages were read and honestly held no feat — **a result, not a gap** |
| NO PAGE | no article under that name |
| NO HOST | the source has no wiki anywhere (homebrew) — permanently uncitable |
| UNREACHABLE | a host exists but the fetch failed — the only pure defect |

**CITED will never approach 100% and should not.** Of 43 entities where the regex miner found
nothing, the model also found nothing in 41. They agree on the negatives because most entries
genuinely have no feats — an item, a location, a Pokémon trainer. The achievable target is
**SETTLED** (cited + read).

## 5. CURRENT STATE (2026-08-22 13:40)

```
sources          212        entries        57,279      judged     57,095
ceilings         167/212    feats on record 12,046     chain edges     64
CITED             5,384 (9.4%)             SETTLED    59.3%

roll   (page mining)   49,800/53,971   504M chars, 38,298 pages   eta 0.2h
read   (model)         32,705 entries, 13 workers, UNCAPPED chunks
                       0.93 entities/s, 0 fallbacks to the GPU     eta 9.7h
```

The reader's rate is the number that changed today, and by roughly 20x. It was serialising every
chunk on one 10GB card because the loop called `P.ask` instead of `_ask`; it now fans out across
thirteen separately-metered cloud buckets. **CITED will move for the first time tonight** — the
9.4% figure predates the fix.

Gap to settled: ~17,000 NO PAGE (a **discovery** problem — network, cheap, parallel) and ~3,400
NO HOST (homebrew, plus whatever `hostcheck --repair` records as unfit). Neither is a GPU problem;
putting a GPU on them was spending the expensive resource on the cheap constraint.

## 6. THE MATHS, AND WHAT CHANGED

`derivation.py` still reports **VERDICT: LEDGER CLOSES**. Four changes on 2026-08-22:

1. **The interval is derived, not decreed.** Was `base + 0.5*(1-coverage)`; that 0.5 was a house
   convention. Now variance propagation, `Var = Σ wᵢ²σᵢ²`, with unscored axes carrying the
   uniform dispersion of ignorance. A missing *heavy* axis now costs more than a light one.
2. **σ calibrated against the charter's own bars.** Kenshiro's published ±0.12 implies a per-axis
   σ of **4.08 on a 0–9.9 scale** — the charter's own error bar says a Measure is known to about
   ±4 of its range. The second decimal is finer than the evidence under it, and printing
   `3.52 ± 0.12` always said so.
3. **The interval is a variance-components model.** Goku is published at ±0.41 under the SAME
   Witnessed grade that gives Kenshiro ±0.12, which no per-axis σ can produce. The charter names
   the reason in his own citation: *"readings divergent, both filed."* So
   `Var = Var(measurement) + Var(between hands)`. Kenshiro reproduces at exactly ±0.12.
4. **Weights use the geometric mean, not the eigenvector.** Crawford & Williams (1985) is the ML
   estimator under multiplicative error and cannot rank-reverse. Measured over 200 simulated
   eleven-axis matrices: identical at CR=0.011, logrank better by 3.2% at CR=0.057 and **8.9% at
   CR=0.202**. They provably coincide at n=3, which is why a small example never shows it.
   Perron keeps λ_max, from which CR is defined.

**Bradley–Terry now offers a prior.** Ford (1957) refuses on a disconnected graph, correctly and
— on unconnected fictions — totally. `prior>0` adds symmetric virtual contests, asserting nothing
about who is stronger, only that everyone is comparable. `identified` still reports what the DATA
ordered; `regularised` says an answer exists anyway. At `prior=0` it is bit-for-bit the old MLE.

### OPEN QUESTION FOR THE OWNER — the compensation parameter

The composite is a weighted **arithmetic** mean, so axes trade freely. Real consequence:

```
glass cannon        (Ruin 9.9, Continuity 0.0)   composite 1.78
unkillable/harmless (Ruin 0.5, Continuity 9.9)   composite 2.07
mediocre everywhere (everything 3.2)             composite 3.20   <- outranks both
```

Part Three says Magnitude is *"what rung this thing can meaningfully threaten"*, and threatening
requires surviving contact — which argues Continuity is a **gate**, not an addend. The general
form is CES, `(Σ wᵢsᵢ^ρ)^(1/ρ)`: ρ=1 is the current sum, ρ→0 geometric, ρ→−∞ weakest-link.

**This is now empirically decidable.** `data/CHAIN.json` holds recorded outcomes. Fit ρ by which
value best predicts who actually beat whom. Until then the charter's declared formula stands —
it is the owner's call, not a defect.

## 6b. EPOCH-AWARE CHAIN NODES — BUILT 2026-08-22

Was open; is now closed. `chain.py` keys every contest node through `identity.node(base,
continuity, epoch)`:

- **continuity** comes from the page the sentence was mined from, and both parties inherit it —
  an Earth-616 page does not narrate an Earth-1610 fight;
- **epoch** is resolved only for MUTUAL pairs, by `identity.adjudicate()`, at one model call per
  side. Eleven thousand sentences that contradict nothing gain nothing from a timestamp.

`extract()` now returns `(edges, unmatched, prov)`; `prov` carries each edge's originating
sentence, which is what makes the dating possible at all. See §3b for the reasoning.

Still open on the maths: **HodgeRank curl was an artifact.** The 0.4022 figure came from a graph
with zero directed 3-cycles — it measured sparsity, not inconsistency, and was nearly reported as
a headline. Do not quote a curl number until the graph has real cycles in it.

## 7. THINGS THAT WILL BITE YOU

1. **One runner only.** Use `src/overnight.py`; it enforces exclusion by live process check on the
   BASENAME, not a lock file and not a full-path match — a lock file survives a kill and blocks
   its stage forever, and a full-path test once let a second roll launch against a live one.
2. **A job that "finished rc=1 in 0m" is not a finished job.** The supervisor now tails a failed
   job's log and halts after three cycles in which nothing worked. It also treats
   `already-running` as HEALTH, not idleness, and waits instead of spinning.
3. **Concurrency is bounded by the number of separately-metered BUCKETS, not by cores.** Sixteen
   workers were measurably slower than eight: the extra ones queued on providers already busy or
   on the single local GPU. `read.py --workers auto` sizes itself from
   `cascade_bridge.cloud_buckets()`. Local `ollama:` buckets are excluded from Cascade claims
   entirely — reaching the GPU through the "cloud" path hides the slow path behind a fast label.
4. **The GPU is serial** and is the fallback of last resort. Anything that sends it a chunk with a
   600-second timeout will stall a worker for ten minutes; the local timeout is 180s for that
   reason, and a chunk it cannot finish is better retried through the pool next pass.
5. **Never write regexes through a shell heredoc.** Six occurrences of `\b` arriving as 0x08, and
   the heredoc also eats `
` inside string literals — several files were written with real
   newlines inside `print(f"` and had to be repaired. Use the editor.
6. **Free tiers lie, and the quiet ones cost more than the loud ones.** DeepInfra and Chutes
   return HTTP 402 and the router drops them on the spot, which is correct. The expensive case is
   a bucket that accepts the claim and never answers: `cascade_bridge` gives every call a 75s
   deadline and benches the bucket. **The bench is GRADED — 60s, doubling, capped at 15 minutes,
   and any success clears the record.** A flat ten-minute bench treated "gone" and "busy right
   now" as the same event and, fifteen minutes into a real run, benched Mistral, Gemini Flash-Lite
   and Groq simultaneously — the three carrying nearly all the traffic — taking the estimate from
   9.7 hours to 59. The progress line names benched providers; if it names your best three,
   the deadline is too tight, not the providers too weak.
7. **Continuities are timelines, not retcons** (§3b). Designators are LEARNED from the corpus,
   never hand-listed.
8. **Ranking is encouraged; truncating is forbidden** (§0). The reader ranks by own-page depth and
   interleaves one deep subject per four short ones, so a run stopped at any moment has both the
   richest material and a wide spread of settled questions. Nothing is dropped.
9. **Estimate in CHUNKS, never in entities.** Entities are wildly uneven — a Warhammer chapter
   is sixty model calls and a side character is two — and the queue is deliberately front-loaded
   with the deepest subjects. An entities-per-second rate measured over that head projected
   **121 hours** for work whose real bound was fifteen. The honest denominator is
   `sum(chars) // chunk_size`: 47,757 chunks at the GPU-safe size, 23,878 at the cloud size.
10. **Do not enlarge the chunk to save calls. It was tried and measured.** Pool models carry
    huge contexts and free tiers meter requests, not tokens, so reading a page in fewer, bigger
    pieces looks like free throughput. On one entity, both ways:

    ```
    10,000 characters   5 chunks  ->  41 feats
    36,000 characters   2 chunks  ->  19 feats
    ```

    **54% of the evidence gone for a 2.5x saving.** The model is asked to find EVERY feat in
    what it is shown and attention over a long passage thins — and a feat never returned is
    indistinguishable from a feat that was never there, which is the defect arriving by a new
    road. Recall is the entire reason the model reads instead of the regex. Throughput comes
    from more providers and more workers; `CLOUD_CHUNK = CHUNK`.
11. **`queue()` is memoised by mtime** in `state/read_queue_index.json`. It parses 497M characters
   of cached page text on a cold index (49s) and 4s warm. Deleting that file is safe but costs a
   minute at every start.

## 8. RUNBOOK (refreshed 2026-08-23)

Day-to-day, NOTHING here needs running by hand — the watchdog starts the supervisor, the
supervisor starts every job, the foreman repairs, and standards dispatch the rest. These are
the commands for looking, and for the rare deliberate act:

```bash
# LOOK (all read-only)
python src/health.py --preflight        # ALWAYS first — cheap, and it has caught real faults
python src/verify_math.py               # 267 checks incl. the mocked assay topology; no network
python src/allsweep.py                  # the full audit battery: imports, lint, reconcile, estate
python src/silence.py                   # how many handlers still swallow a failure silently
python src/dashboard.py --port 8777     # the instrument panel (usually already running)
python src/tuning.py --force            # which regime the machine is in and what follows

# ASSAY
python src/magnitude.py --calibrate     # the charter regression; persists CHARTER_REGRESSION.json
python src/magnitude.py --one <host> "<entity>"
python src/magnitude.py --batch --workers 12   # workers are a CEILING; tuning.py decides

# CORPUS
python src/completeness.py --workers 6  # sources vs the wikis' own category counts
python src/catalogue_web.py --recatalogue --shortfall 100
python src/hostcheck.py --adopt --go --workers 3
python src/ingest_doc.py --pdf <path> --source "<name>"   # owner-supplied book -> corpus
python src/ingest_doc.py --source "<name>" --mine         # its entity pass (resumable, patient)

# PROSE
python src/manifest_builder.py          # then generate.py; chapters write in verified 8-entry blocks
python src/generate.py --manifest output/index/manifest.json

# PUBLISH (the supervisor's publisher loop already does this)
PANSCRIPTUM_EXPORT="C:\Users\imarl\panscriptum-export" python src/publish.py --push
```

Morning reading order: `FOR_OWNER.md` (decisions queued for you, paid-lane spend included) ->
the dashboard's MOVEMENT panel (flat counters with running jobs is the one stall class the
logs cannot show; a standard watches it now) -> `state/failure_samples.json` beside
`state/failures.json` (each class carries its last three concrete instances). On THIS machine
always use miniconda's python directly, never `py`, and never run anything from
`panscriptum-export` — the `.is-export-copy` guard will refuse.

## 9. NEXT (rewritten 2026-08-23)

1. **Pool rollover (tonight):** the free tiers' daily windows reset; the mandate-era batch
   clears the deferred backlog — including the split-path heavyweights — without supervision.
2. **The dependency chain after DC's re-catalogue:** sweep rebuild -> feats roll -> read ->
   assay. The sweep-freshness standard plus foreman dispatch enforce the order now; let it run.
3. **Coverage re-measure** happens via the `always`-remedy after the shortfall list drains.
   One open oddity: Marvel shows 30,207 on disk but the completeness row still reads low —
   check the row's byslug match before trusting the next percentage.
4. **Chain of Defeats on the post-recatalogue index** — Lex Luthor, Wally West et al. become
   matchable edges; Ford's condition gets its first real shot at holding.
5. **Charter errata for the owner:** Supercluster / Filament / Hyperverse rungs have no
   Magnitude band. The anchor-vs-axes "chord view" (eleven-axis profile beside every Moth
   number) was offered and awaits a yes.
6. Phase 8 prose: WRITE_SETTLED_MIN = 0.60 gates on the settled fraction — rises as the read
   runs on the refreshed pool.
7. Terminal rebuild (`build_terminal.py`) once the catalogue settles — registry data is Aug 19.
8. Mid-run executor resize (the tuning regime is start-of-run; the adaptive gate covers
   read.py only). Fellegi-Sunter for the weave remains the principled upgrade.

---
