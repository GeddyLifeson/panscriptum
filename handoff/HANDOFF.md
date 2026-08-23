# PANSCRIPTUM — HANDOFF

*Hand-written. `src/pipeline.py` rewrites its own status block below the line; everything above
it is durable and should be read first.*

Last substantive update: **2026-08-22**

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

## 8. RUNBOOK

```bash
python src/health.py --preflight        # ALWAYS first — cheap, and it has caught real faults
python src/silence.py                   # how many handlers still swallow a failure silently
python src/overnight.py                 # the supervisor: roll || read -> pipeline -> coverage
python src/coverage.py                  # the dashboard, per source, with the blocker named
python src/hostcheck.py --repair        # does each wiki hold the fiction it is assigned to
python src/hostcheck.py --rosters       # is each catalogued cast from its own source
python src/identity.py                  # the continuity inventory, mined not listed
python src/chain.py --prior 0.5         # phase 4, now continuity- and epoch-aware
python src/reference.py                 # the three hand-built calibration assays
python src/magnitude.py --calibrate     # against the charter's six published values
```

`STATUS.md` is rewritten each supervisor cycle — read that first in the morning. Then read the
`swallowed failures:` block in `state/overnight.log`; a new entry there is a bug, not data.

## 9. NEXT

1. **Let the reader finish.** ~9.7h for all 32,705 entries with pages, uncapped, at 13 workers.
   CITED should move off 9.4% substantially — this is the first pass where the model has actually
   been reading rather than the GPU trickling.
2. Re-run `hostcheck --repair` and then `--rosters --purge --go` once the roll settles, so the
   wrong-fiction rosters come out before anything is written about them.
3. Close the NO PAGE gap with `feats.resolve_title` — measured 16% recovery ≈ 2,700 entries.
4. Fit ρ from the chain, then put the compensation question to the owner with a number.
5. **Phases 5–8 (`cosmology`, `history`, `shelve`, `write`) are not implemented**; the runner
   stops cleanly at the first missing one. This is the largest single block of unbuilt work.
6. Charter errata to raise with the owner: rungs 10 (Supercluster), 11 (Filament/Void) and 16
   (Hyperverse) have **no Magnitude band**, and M0–M2 sit below rung 1.
7. Rewrite `reference.py`'s three calibration cards' AXIS notes in presence language — the anchor
   statements were converted on 2026-08-22 (`hegemonic` → `presence` throughout the assay stack),
   but the per-axis prose still reads as threat in places.
8. Fellegi–Sunter for entity resolution (currently complete-linkage; F–S gives match probabilities
   and a principled threshold instead of an inspected cutoff).

## 10. HOST CANDIDATES FOR THE "NEVER CATALOGUED" SIX (researched read-only, 2026-08-23)

`WATCH.md` round 3 (15:03 on 8/22) reported **6** sources on the roll with zero catalogue
records (`allsweep.py`'s `"on the roll but never catalogued"` check — `roll_src - set(recs)`,
distinct from the 32 "catalogued but no host" sources). Its own display line truncates the
`note()` detail string, so only 4½ names were legible in the file:

```
HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major [cut]
```

**This session cannot see `data/SWEEP_ROLL.json` or `data/weave_index` at all** — this checkout
is `publish.py`'s export copy (see `.is-export-copy`; `src/silence.py` refuses to run pipeline
code here on purpose), and it ships without `data/` entirely. So the exact 6th name, and
confirmation that this list hasn't already moved since 15:03 on 8/22, need a live run:

```bash
python src/allsweep.py --quick    # reprints the untruncated "missing" list under RECONCILE
```

What could be worked out from the roll text and web research anyway, for whoever runs the
above — `hostcheck.py --adopt` should confirm or correct these, not take them on faith:

| roll entry | likely host | notes |
|---|---|---|
| HAWX (`all Tom Clancy` line, roll §VI) | `hawx.fandom.com` | dedicated wiki, 278 pages, covers both games, the novel, and the mobile spinoff. Distinct from the other Tom Clancy sub-franchises, which have their own wikis — don't let `--adopt`'s neighbour-candidate logic point this at e.g. `rainbowsix.fandom.com`. |
| Heaven's Lost Property (roll §I) | `soranootoshimono.fandom.com` | the dedicated wiki, under the Japanese title (*Sora no Otoshimono*) — the English-title search surfaces several thinner cross-reference wikis (`versus-connections`, `animanga`, `neoencyclopedia`) first; those will score real but low `HELD`/`ABOUT` against this. |
| Lost Mines of Phandelver (roll §XV, the Folder) | `forgottenrealms.fandom.com` | **§3a of this file already solved this one on 8/22 13:40** — it's the "wrong wiki" case (`lost.fandom.com`, the TV series *Lost*), corrected to Forgotten Realms with the mined roster purged (531 entries removed between this and the Witch Tradition). Its reappearance in the 15:03 "never catalogued" list is almost certainly that purge leaving it with zero records until the next `hostcheck --repair` + re-roll against the corrected host — not a new unhosted source. Re-sweep before doing anything else with it. |
| Twilight Imperium (roll §XI) | `twilight-imperium.fandom.com` | dedicated wiki. `ti3reference.fandom.com` exists as a 3rd-edition-specific fork — worth checking which one `--adopt`'s HELD/ABOUT scoring prefers before locking it in, since the roll doesn't pin an edition. |
| "major live-action Disney films" (roll §III, one umbrella roll line, not a title) | *(needs a decision, not a host)* | if `SWEEP_ROLL.json` really carries this phrase as a single literal source name (plausible — the roll itself lists it as one bullet, unlike the Pixar films which get their own line), no single wiki is "about" it by construction — it's an editorial category spanning many separate live-action films with separate wikis (`disney.fandom.com` covers general Disney content but isn't specific to this subset). Worth flagging to the owner as a curatorial question — split into per-film sources, or accept a broad host — same shape as the Extra Life / War-Thunder-composite / Witch-Tradition cases §3a already called "genuinely without a wiki that holds them," not a discovery failure. |
| *(6th name, illegible in WATCH.md)* | unknown | `sorted()` on the roll set is plain ASCII order, so anything lowercase-initial (like `major live-action Disney films` above) sorts after every uppercase-initial roll name — the roll has several other lowercase-led entries (`the Elements Beyond`, `the Root Companions`, `the Sex Worker background`, `the Weaveshaper Ateliers`, `the Witch Tradition`, `swordmeow's Atavist`, `swecky's Nature Traditions`, `aurora_mods...`) any of which could be it. Don't guess a host for it sight unseen — rerun `allsweep.py --quick` first. |

None of this was run against live data or verified with `hostcheck.py`'s HELD/ABOUT/ROSTER
tests — treat the table above as candidates to feed `--adopt`, not as adopted hosts.

---
