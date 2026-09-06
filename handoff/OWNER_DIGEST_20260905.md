# The owner's queue, digested — 2026-09-05

**186 orders read in full: 128 on the OWNER rung, 58 on SESSION.** Nothing is sampled and nothing
is summarised away — every id appears somewhere below, and the roster at the end catches anything
not named in a group. (Three of those arrived while this was being written; the count moved under
me, which is itself worth knowing about a queue this size.)

This is not a worklist. It is a list of **decisions**, grouped by the question being asked rather
than by the file the question was found in, because most of these orders are the same handful of
questions arriving from different sweeps. Answering one question closes several orders.

Three things to know before reading:

* **69 of the 128 OWNER orders are more than a week old.** Only 1 of the 57 SESSION orders is.
  The OWNER rung is where things go to sit.
* **34 of the 128 OWNER orders carry a "restored from the 600-char cap" block** — the filing cap
  ate the *remedy*, because a work order's instruction is written at its end. Those restorations
  are honest about what was recoverable and what is simply gone. Where a remedy is lost, the
  finding is still good; it needs re-deriving, not re-finding.
* **Section 4 is the part worth your time first.** Roughly a third of this queue is not an owner
  decision at all — it is ordinary defect work that landed here because nobody wanted to decide
  it, and it can be handed straight back to a maintenance run.

---

## 1. TIME- AND MONEY-SENSITIVE — read these first

### 1.0 THE LIBRARY IS HALTED AS THIS IS WRITTEN — `a74678936964`
`state/HALT.json` carries `cleared: false`, raised **2026-09-05 22:44:18** by `drill.py`, two
minutes before this line was typed:

> DRILL_BREACH — 1 safety net did not hold: **"publish refuses to push while a mutation run is
> active"** (`drill.py:10976`)

`state/MUTATION_RUN.json` is **absent**, so no mutation run is active — which means either the net
drives a synthetic fixture and the guard genuinely failed to refuse, or the net itself is wrong.
This was raised by another agent's drill run during the current maintenance shift and may already
be in hand; it is recorded here because a halt that nobody mentions is a halt that stays up.

**Only a person may lift it.** That asymmetry is the entire subject of `c614f7c145fc` in §1.4
below, which exists because a halt was once lifted by an automated actor labelled `owner-cli`.
Nothing in this digest lifted, cleared or touched it.

### 1.1 A loaded gun on the prose gate — `342ccfafa4a4`
`config.yaml` configures `qwen3:8b`. The comment block directly above that key describes a
different model entirely (a 30B MoE at q4_K_M, 18.6GB, 22.0 tok/s) — so every VRAM, throughput
and context number a reader takes from that block is fiction. Worse, the block states a
**requirement**: the model must be the non-thinking `-instruct-2507` variant, because
`generate.py` writes `data[response]` straight to disk with no think-tag stripping. Ollama's own
`/api/tags` reports `qwen3:8b`'s capabilities as completion, tools, **thinking**.

Nothing is damaged **only** because `prose_enabled` is shut. The moment the prose gate opens on
this configuration, reasoning scratchpads land in published chapters. This is the one item in the
queue whose cost is a function of when you act relative to something else you control.

It is already costing the repair rung: the first work order routed to LOCAL this shift came back
`rc=1` after 570s with an empty patch list — a reasoning model spends its budget thinking before
it emits a tool call. Three options, none of which a run should pick: install a non-thinking
instruct variant (`pick_model.py --write` exists to choose on measurement); keep `qwen3:8b` and
**both** strip think-tags in `generate.py` **and** rewrite the comment block; or configure the
prose lane separately from the repair lane, which the config does not currently support.

### 1.2 Free cloud tiers are spent — `88982cef258d`, `2239a87c57f5`, `9fb8a6b10c1f`
`groq:qwen/qwen3.6-27b` sat at 198,972 of 200,000 tokens-per-day. Gemini 3.1 Flash-Lite, DeepSeek
V3 (SambaNova), GLM 4.7 Flash (Z.AI) and Command R+ (Cohere) all answered rate-limited in one
selftest walk. `allsweep`'s cascade verifier is red for this reason and stays red until quota
returns or buckets are added. **The remedy is money or waiting, and the standing answer to money
is no** — so the only thing owed here is that it stays recorded, which it now is. `9fb8a6b10c1f`
is the same census taken on 2026-08-25 and is superseded (see §3).

`7ebac78494e8` belongs here too and is **not** a quota condition, which is why it keeps getting
re-diagnosed: four buckets — deepinfra, huggingface, cerebras, chutes — all fail with
`curl: (6) Could not resolve host`, on four different domains, all unreachable from **the same
second**. That is one resolver fault on this machine, not four provider refusals, and the four
have been silently absent from the pool ever since. They were saved from being permanently benched
only by luck of ordering; `cascade_bridge` now refuses to classify a curl transport line as a
permanent refusal for exactly this reason. Seen 7 times. If the pool feels thinner than the roster
says, this is four buckets of the answer, and the fix is DNS, not code.

`2239a87c57f5` is the one part of this with a real decision in it: the router parses a provider's
`retry-after` (501s, 499s, 99s, 40s) and **discards it**, then dispatches to that bucket again —
3 of 6 probes went to a bucket that had just said "retry in 499s". Three rulings, all yours:
(a) leave it, the cost is one wasted call per rotation; (b) honour the parsed retry-after as a
bench duration *without* writing to the unrecognised-failure ledger, which keeps the current
rationale fully intact; (c) treat a stated per-**day** exhaustion as permanent-for-the-day,
distinct from a per-minute throttle. Note `drill.py` has a net pinning the current behaviour, so
any change moves a net deliberately.

### 1.3 Your machine, not the library's — the local rung
`f6c52ef7657f`, `28f79d511879`, `505177847f43`, `a8464e348c5e`, `4e37d5e59b09`, `d2583f4c8b36`,
`bffc372a96d2` — **seven orders, one question.**

A foreign process (`pythonw -m semsearch.cli watch`, not part of this project) has repeatedly
exhausted this host's entire ephemeral TCP port range against Ollama — measured 2026-08-31 at
31,791 of 31,867 host sockets on port 11434. `pipeline.py`'s daily WinError 10055 count went
41 → 183 → 245 → 370 → 585 over six days, monotonic. Panscriptum itself held **2** of 32,294
sockets: the library is the victim, not a contributor.

**Measured fresh, just now:** 308 host sockets total, **4** on `:11434`, and no `semsearch`
python process on the box. Overwatch.exe is not a GPU compute client either. So the emergency is
not currently live. But `f6c52ef7657f` documents this as a **cycle** — it drained to 5,468 and
climbed back to 6,903 in a day — and `28f79d511879` warns the PID moves across reboots. Not
resolved; just not firing today.

The decision is not technical, it is permission: **what may an autonomous run do about a
non-Panscriptum process that closes the cheapest handler rung?** Today the answer is "nothing",
runs #37–#40 all correctly declined to kill it, and the consequence is the condition grew for four
shifts. The options: (a) leave the standing prohibition and accept the rung is unreliable;
(b) grant a narrow standing permission to stop one named process; (c) accept LOCAL is a
nights-and-weekends rung and **re-rate the ~128 orders addressed to it**, which is what
`bffc372a96d2` argues, because a handler that cannot handle and exits 0 is a check that cannot
fail.

### 1.4 Two governance items about who is allowed to stop things
`c614f7c145fc` — a halt raised at 22:18 by `drill.py` was **lifted at 00:55:07 by an automated
actor**, recorded as `who=owner-cli`, which is the CLI's default label and not evidence a person
ruled. On the merits the ruling was defensible and the cause genuinely repaired; on authority it
was not, and the charter's asymmetry (a run may raise a halt, only a person may lift one) is the
entire point. The mechanism cannot tell a person at a keyboard from an agent, because both use
the same command with the same default label. **Consequence:** with the halt gone the publish
daemon resumed and pushed to the public repo at 01:01 and 01:07. Nobody decided that.
**What wants a ruling:** should `clear()` require something a scheduled run cannot supply, and
should `cleared_by` record the actual caller?

`ddb5eadd8934` is the same question one rung down and it is **strictly worse**: `resume_subsystem`
lifts a MANAGER stop on nothing but a 20-character string — no person check at all — and
`drill.py` calls it programmatically at three sites today. Its own docstring claims it demands a
ruling "EXACTLY AS `clear` DOES". It does not. There is also no `--resume` in `main()`, so there
is no person-facing path. One ruling settles both: either the person check applies to both lifts
(and `drill.py` gets a private test-only path), or the programmatic resume is deliberate and the
docstring is overclaiming in capitals.

`4e7f1e47d0a0` is the incident that produced both: a MANAGER-rung stop of `catalogue_web
--recatalogue` (it was nulling synthesis blocks — 26 sources in 24 hours) lasted 25 minutes before
the keeper restarted the job. That half is fixed (durable `STOPPED.json`, fail-closed reads, the
keeper now asks). It is listed here because it is the evidence for the two above.

### 1.5 On your machine, outside the repo — `ee0e5bef7dab`
`%TEMP%` holds 490 `panscript-ledger-*` and 302 `panscript-lane-*` directories that `verify_math`
leaked before the leak was fixed. The leak **is** fixed and verified. Nothing removes the history,
and a bulk deletion in someone's `%TEMP%` is not an autonomous agent's call. It wants a person or
an explicitly scoped sweep.

---

## 2. THE DECISIONS

### 2.1 Does Hard Rule 0 reach an announced console listing? — 6 orders, one ruling
`1cdc2f8cd2f3` · `3dd5b6caef38` · `189532cbf41a` · `47c8def059e3` · `732f68f640cf` · `541384445ec3`

Every one of these is a CLI report that ranks and then cuts, with the count disclosed and usually
a `+N more` marker, never touching the data the pipeline consumes. The same question arose
independently in **eight** sweep batches. One sentence settles all of them.

- **For "it's fine":** the count is printed, `e.g.` says plainly it is a sample, and the row exists
  to keep a *number* visible rather than to hand anyone a worklist.
- **For "it's a cap":** your standing note is that a cap is a truncation hiding a smaller universe.
  `189532cbf41a` is the sharpest instance — `estate.charter()` reports "33 — e.g. " and four names,
  and the one artifact that would carry the other twenty-nine, `output/index/unassigned_sources.md`,
  currently reads "**None.**" and is stale. So today there is **no place in the tree** where the
  missing names can be read.

**Not curatorial, and I will say so plainly: the *stored* half of this question is already
settled and these are defects, not decisions.** `19c507a16430`, `ecc355769a41`, `1f9a54bede08`,
`f2b06f8c9476`, `8d8ba5377fb6`, `cca253138a62` and `14a73de63099` cut values that are **written to
disk** and read back by other code. The project has already ruled twice — the `[:300]` cap came
out of `suppressions.add()` (order `7a6362fa3c91`) and out of `binding_health.quarantine()`
(order `d6ca84486153`) — on the stated grounds that "a display cap is reversible because the
stored text is still there to widen back to; a stored cap destroys the only copy." These are the
same shape one level up. `8d8ba5377fb6` is the worst: the ceiling-nomination prompt shows the
model **3 of an average 33** mined feats, unranked and in stored order, and the resulting band
clamps every entry in the source.

`4d78c426afb3` is the same rule one level further out and genuinely needs your call, because the
cut happens **server-side**: `find_categories()` asks MediaWiki for categories with `acmin: 40`,
so every category under 40 pages is never returned and there is no local list to notice is short.
Settling it cheaply means calling `all_categories(sub, min_pages=1)` alongside `40` for a handful
of sources and counting what the floor drops — but this machine has been IP-blocked by fandom
before over exactly that kind of extra traffic, so it must be run slowly and deliberately.

### 2.1b Pick a crawl concurrency — `959b98f38a63` closes seven recurring orders
Filed today, and it is the best-value single answer in the queue: **seven recurring BOTS orders are
one condition, and the hosts are not banning us — we are out-requesting them.** Six
HOST_QUARANTINED orders (marvel.fandom.com throttled 75 times consecutively at 32× backoff, seen 43
times over 114 hours; onepiece, naruto, dragonball, mtg and hokuto each at 3 consecutive and 8×)
plus STALLED_UNRESTARTABLE (seen **95 times over 157 hours**).

Four measurements support one reading: the named "stalled" process was three hours old and burning
CPU, not wedged; the advancing standard reads green right now, so the stall is intermittent; a
single polite request to marvel returned **HTTP 200 in 0.27s** and onepiece in 0.30s, so there is
no ban and no blackhole; and the backoff is in-memory and per-process, so the 32× dies with the
roll rather than needing to be cleared. The crawl runs **twelve concurrent workers** against hosts
that answer one sequential request in under a third of a second; they return 429; the adaptive
backoff correctly ratchets; throughput collapses; the roll goes long enough between writes to trip
the advancing standard. **Every component is behaving as designed and the setting is wrong.**

The filer is careful about what was *not* established, and so am I: the probe used a different user
agent, no session and one request, so it proves the host is fast for a well-behaved caller — not
that the library is unthrottled under its own load. The 429s are almost certainly real and earned.
**Nobody has measured the per-host rate twelve workers actually produce, and nobody has found where
`--workers 12` is chosen.** Measure before picking a number; do not halve it on one probe.

Why it is yours: Hard Rule 0 forbids a smaller universe, so the answer is never to crawl *less* —
it is to crawl at a rate the host will serve, possibly for longer. That trade is an operations call.

**A second, unrelated fault found while looking, and it should not ride along on this ruling:**
`data/BINDING_HEALTH.json` was last written **nine days ago**. The binding-health probe is on no
schedule that reaches it, so the file a reader consults to ask which hosts are healthy is nine days
stale *while the throttle orders it should corroborate are refiled hourly* — which is why those six
quarantine orders have nothing to close against. That half is a scheduling defect, not a decision.

### 2.2 Dead public symbols: what is the default disposition? — 28 orders, one policy
**Whole modules with no caller:** `66f96febdb3a` (descending_ladder) · `7e360eaec3a6` (chord_field)
· `01695fe3ef26` + `a78d5cd748b2` (scale_theories) · `3fb312a72435` (hosts.py) · `3fb9fc6b9999`
(ledger.py) · `707fefc17465` (render.py)

**Single symbols with no reader:** `2b695c192470` · `570525d35825` · `d411f780d347` ·
`946153deafe9` · `de43fe54feb7` · `c0384991bfc5` · `e68664e621bf` · `4e92365b54f6` ·
`0291835411d9` · `1eb00a84225e` · `db36d589713e` · `1a9c237dda4d` · `12c457975677` ·
`47067a8f0ad5` · `e637c67ab438` · `464cc4e12fbc` · `da15f582b2ea` · `c72431056a14` ·
`0b1cda11f4a2` · `665e3609bc82` · `f27d210d4fea`

The house rule — dead code is reported, never silently deleted, deletions need a review cycle — is
correct and is producing an **unbounded queue**: every sweep re-finds the same symbols, and
several orders exist only to say "this was found again". What is missing is a stated default
disposition. Something as simple as *"a symbol with no reader gets one line in the source saying
it is retained as reference data and why, or it goes; a maintenance run may write that line"*
would drain most of this section without a single deletion.

**But six of these are not dead code — they are unwired features, and the gap they were built to
close is still open.** These deserve individual answers and should be split out of the group:

| order | what was built | what is still broken |
|---|---|---|
| `4f308dbd9d2c` | `feats.resolve_title` | its own docstring: **17,148 entries mined to nothing** on catalogue-name/wiki-title mismatch. Never called once. |
| `66f96febdb3a` | descending_ladder's 15 sub-planetary rungs | Reach below 1e7 m is still scored against a floor that does not exist, off a hand-written table in `assay.py`. |
| `3fb312a72435` | `hosts.py` multi-host reading | `data/SOURCE_HOSTS.json` holds real discovered hosts (11,583 bytes) and nothing reads it; `feats.py` mines from `WIKI_HOSTS.json` only. |
| `bd673ceaaf31` | Lumen's staleness term, Threnody's curl veto | `anchors.py:190` is the only real caller of `convene()` and passes neither. Lumen contributes exactly 0.0; the veto has never fired on a real being. |
| `ae25c89f0179` | `onomast.register_for`'s genre+feature blend | the only production call site passes one positional argument, so the pure hash-of-group-id fallback fires every time — the exact defect the docstring says was already fixed. |
| `cefcad5fc513` | `prose_gate.assert_step4_open` | the enforcing half of the Step-4 interlock has zero callers. **Do not open the gate; do not delete this.** (Its "pin it with a net" half is now done — see §3.) |

`bd673ceaaf31` is the one with a real design question inside it: nobody has decided what
`distance` and `years_since` *are* for a calibration anchor, and supplying a number to make the
code path fire would invent the measurement. The cheap honest move offered is to rule that anchors
are read at zero remove **by definition** and pass `distance=0.0` explicitly, converting a silent
gap into a stated convention. Do **not** wire `resonance_strength`'s co-attestation graph into
Threnody's `eta`: it is a different quantity and a plausible-looking eta is worse than a veto that
never fires.

### 2.3 The writer is fixed. Does the stored output get recomputed? — 5 orders, one question
`b317ba3a4f36` · `3eff62be6cc3` · `e9ff72c7eb48` · `481ef92af785` · `f27c121c6cb7`

Each is the same shape: a defect was found and repaired in code, and the data the broken code
already wrote was deliberately left alone because re-deriving it **moves published numbers**.

| order | what is stored wrong | what re-deriving costs |
|---|---|---|
| `b317ba3a4f36` | `GENRES.json` — 193 of 210 confidences inflated; **63 sources cross the 0.45 mixed-source flag**, all downward (flagged count 43 → 106). Zero labels change. | one command, `src/genre.py --write`. Published confidences move. |
| `3eff62be6cc3` | `GROUNDINGS.json` — same defect; 4 sources reported as settled cosmologies are actually contested (Marvel and Bleach among them). | same shape. |
| `e9ff72c7eb48` | `ASSAYS.json` — 885 published decimals rest on evidence the *fixed* subject guard now refuses; 110 refused, 81 of 217 assays touched (12.4%). Some refusals are alias failures rather than bystander credits. | a re-assay pass; some published magnitudes move. |
| `481ef92af785` | `SCOPE.json` — ceilings invented before the fix, and `build()`'s `h not in out` skip means those rows **can never be re-probed**. `magnitude.host_ceiling()` reads them as authoritative clamps right now. | 20 hosts to re-derive (see §3 — I re-measured this). |
| `f27c121c6cb7` | 272,004 stored entry `type` values from `cats[0]` rather than the real category. 2,517 are provably wrong (690 Warhammer Events typed "Total War: Warhammer"). | `--recatalogue` is **hours per large wiki**; a full pass over 156 sources is multi-day against a spent pool. |

Two things worth saying plainly. **`481ef92af785` is not a "someday" item** — those rows are
constraining published Magnitudes today and are structurally unreachable by the fix, which makes
it different in kind from the other four. And `f27c121c6cb7` offers a targeted first move that
avoids the multi-day cost: re-catalogue only the 2,517-entry proper-noun set, which is small,
ranked and well-defined, and leave the ambiguous majority for whenever a full pass runs anyway.
Its own argument for acting now is sound: the prose gate is shut, so this is cheap to fix now and
expensive later.

### 2.4 Is the hyperverse charted or declined? — 3 orders, one fact
`60dc7c624c06` · `789f99f2a65f` · `95f80c0ea860`

`address_space.py` says the charting is "168 multiverses → 8 metaverses → 6 xenoverses → 1
hyperverse". `tiers.py` prints "hyperverse: DECLINED for all 209 shelves". `data/TIERS.json` holds
four distinct non-null hyperverse values, and 170 of 208 shelves carry a real grounding-derived
hyperverse index and type. Thirty-nine lines after printing DECLINED, the same report prints a
concrete `H` number for a sample stack.

**This one is not really a decision — `789f99f2a65f` already did the work and found the answer:
the claim is stale, not the cut.** The hyperverse was re-implemented as the grounding of a
xenoverse; the top docstring and the print were never updated, and the *link-graph* hyperverse
that was genuinely declined was removed. All three orders close on one nod, and the follow-up is
documentation plus a corrected count line. The only thing needing your voice is whether the word
"declined" should still appear anywhere in that report.

### 2.5 Is the printed shelfmark the whole address? — 4 orders
`be9e9f089d62` and `8fb33a0204c4` are **the same finding filed twice** by different sweeps.
`FIELDS` declares eight address fields; `shelfmark()` prints seven and silently omits `star`,
which is 27 of the address's 88 bits — so the printed name is not injective. It matters beyond
cosmetics because `seed_from_card()` hashes the shelfmark as a world's map seed, so two worlds
around different stars would share a shelfmark *and* a terrain. **No live collision today**: all
1,016 rows in `SHELFMARKS.json` have distinct addresses, shelfmarks and seeds, because the
38-bit galaxy field is hash-drawn.

Both readings are defensible and the counter-reading is strong: the charter's own worked Shelfmark
has seven tiers and no star. If the notation governs, the work is documentary. If the address
governs, adding a star element **re-addresses every world's map seed** across 1,016 standing rows.

`642a95fe9f3c` is the sharper sibling and is the one I would answer first: a missing tier is
mapped to **0** with no marker, so a source the weave never charted publishes at H0/X0/Mt.0,
indistinguishable from one genuinely charted into hyperverse 0. 109 of 209 `TIERS.json` rows carry
at least one `None` tier; 8 of 30 `WORLDSEEDS.json` sources are among them. The module quotes the
charter twice saying this is the one thing it must not do ("the Custodes considered guessing a
form of lying"), and the compensating warning it names only fires when the whole file is missing.
`1eb00a84225e` is the vocabulary for the honest answer — `UNADDRESSED = None`, "a shelf in no
hyperverse" — sitting unused.

### 2.6 Misbound wikis and unbound sources — 9 orders, two questions
**Wrong host (rebind, or unbind):** `f84cb75edcfe` + `1b7f14efce8e` are the same finding on
`prime.fandom.com`, which is bound to "Prime World Equipment" and **serves the Prime Hydration
drink wiki**; the correct fiction is at `primeworld.fandom.com` (verified live), but its catalogued
entries are item-level and that host has no articles for them, so rebinding alone will not clear
the signal. `f07b7d538ed1` + `2d6bef2aef03` are the same finding on `starrealms.fandom.com`, which
serves "The Brain World Wikia"; the entry names are genuine Star Realms factions so the names are
right and the host is wrong, and **no replacement host exists** — Star Realms may have no fandom
wiki at all, in which case unbinding is the answer. *Confirmed still bound as of today.*

**Right host, wrong titles:** `0fbaba6e1070` (aneurism), `aecffd7eea57` (eberron), `efd2b537f26d`
(warthunder). The wiki is the right one and names itself correctly; none of the catalogued titles
resolve there. One ruling covers all three: accept that these sources are mined at feature level
and carry no per-entry articles, or re-catalogue their entries under names those wikis use.
Mining continues either way and nothing is broken.

**Not on the map at all:** `585fcd3774b8` — `data/records/bone-jeff-smith.json` holds 86
catalogued entries and there is **no roll row for it under any spelling** (all 215 rows searched).
Not a slug mismatch. Two possibilities needing different answers: it was catalogued without ever
being added to the Acquisitions Roll (Hard Rule 2 makes that yours), or its row was lost when
`SWEEP_ROLL.json` was destroyed twice on 2026-08-26 — in which case restoring it is repair, not
judgement. `state/backups/SWEEP_ROLL.json.reconstructed-20260826` settles which. Meanwhile 86
entries are invisible to downstream gating.

`c8dc624e4e02` and `b9584c782d95` are the same population from two directions: 13 (later measured
9) sources are simply not recorded in `WIKI_HOSTS.json`, four of them carrying real entries — The
Elements Beyond alone has 681, and 727 entities total are silently excluded from every `--roll`
run. Five further sources are legitimate `pages:` sentinels and correctly have no wiki host.
Binding the unrecorded ones is a data question for you; the *silence* about the exclusion is a
defect (see §4).

### 2.7 Fail open or fail closed? — 7 orders, one doctrine
`8c354f6c9780` · `70f66fbd98aa` · `5f1dc97d5216` · `79da6c08c536` · `2f8ebf12e5f2` ·
`d2da5914da94` · `95f817b752ac`

Hard Rule -1 says every layer answers "I don't know" with STOP. These seven are places that
deliberately answer it with "carry on", each with written reasoning, and none has been put to you
as a ruling. The reasoning is good in every case — that is what makes it a doctrine question
rather than a bug list. `70f66fbd98aa` is the clearest: `runguard` treats a corrupt
`MAINTENANCE_RUN.json` as "free to claim", because failing closed would wedge the pass permanently
on a file nothing repairs — and this is the file holding the one invariant that stopped two
maintenance runs from clobbering each other.

`5f1dc97d5216` is the one with teeth and I would not leave it in the group. `weave_index._records_sig`
hardened its **per-file** OSError handler to return a `None` signature so nothing caches an unclean
pass — and eight lines up, the **top-level** handler treats an unreadable `data/records` directory
as a clean, cacheable, *empty corpus*. If `weave_index.py --write` runs during a Norton lock or a
mount blip, it computes an empty index and **overwrites** `ENTITY_INDEX.json` and
`WEAVE_CANDIDATES.json` — the files three other modules read as "the whole entity population" —
with near-empty replacements, with no minimum-size or shrink check anywhere in between. That is
the same shape as the synthesis-nulling incident that reached MANAGER rung. Same function, same
failure class, opposite handling.

One ruling would settle the group: name the criterion under which a layer may fail open (something
like *"only where failing closed would wedge a pass that nothing else can repair, and only where
the fail-open is logged"*), and each of the seven then answers itself.

### 2.8 Charter and physics judgments — 5 orders
- `adaeaa7ad639` + `cdfeccbfbab0` — **the same ruling filed twice.** `SIZE_CLASSES['POCKET'] = 1e-9`
  is described as "a closed loop, a demiplane, one stage and no sky" and computes **200 galaxies**
  and twelve galaxy-spanning Type III civilisations; `MINOR` is "a single galaxy's worth, walled"
  and computes 200,000 galaxies. Exactly one of the two declarations must move. Nothing calls
  either class (every `census()` site passes `STANDARD`), so this breaks nothing today and is
  cheap to settle now.
- `38c51153243c` — the descending ladder's binding-energy column is declared the rung edge for
  Ruin and is **not monotonic**: it drops sixteen orders of magnitude from Organic to Cellular,
  then reverses and climbs thirty orders to the Planck rung. Either that is true about the world
  (a cell really is easier to disrupt than a nucleus) and the header should *say* the column is
  U-shaped, or the upper rungs quote structural disruption energy while the lower quote
  per-particle binding, and they are not the same quantity. No urgency: nothing consumes this table.
- `c9e6e50e792f` — `assay_dof`'s prose says "ten independent levers", its parents list holds
  **nine**, and `college_size` derives "one Custos per degree of freedom" from it while
  `custodes.py` seats **ten**. Matching by content leaves exactly one Custos — Cassia,
  applicability — with no ledger counterpart. Either add `applicability_mark` as the tenth parent,
  or change "ten" to "nine" in both places and say why Cassia's seat sits outside the count.
- `27f823fd6ed5` — `ledger_guard`'s 5% loss tolerance cannot tell an accidental typo-fix in old
  ledger text from a deliberate small falsification. It is explicitly a judgement by the agent who
  wrote it, and it is the one value in a tamper-evident guard set by taste. The containment maths
  around it was adversarially tested and is sound.
- `b57e23204f66` — what `axis_correlation.rho()` should return when the matrix is unreadable. The
  module header promises "the measured mean, not zero" and the code returns `0.0`, so the file
  contradicts itself. The measuring agent's judgment is recorded and is worth keeping: **neither**
  substitute nor refuse — substituting the mean is incoherent because the mean lives *inside* the
  matrix, and refusing breaks every consumer on a fresh clone. So: rule that 0.0 stands and fix
  the docstring, or name a value. The fallback is now loud, so only the number is open.

### 2.9 The prose gate's own integrity — 3 orders
`6e6954f261e0` · `b1f561587b19` · `cefcad5fc513`

All three concern the layer built after the 2026-08-25 incident. `6e6954f261e0` is a genuine
question: `REQUIRED_PER_ENTRY` checks Shelfmark/Class/Magnitude/Threads and **never checks for the
Instrument section** — the incident's own headline symptom ("only 113 of 1,268 kept an Instrument
block", a 91% loss, worse than the 71% Threads loss that *is* checked). Reproduced this shift: a
block that drops the Instrument section entirely scores 100% and passes cleanly. Either that is an
oversight, or Instrument integrity is considered covered by the fabrication check and total absence
was an accepted residual risk. The filer is careful to say this asks whether the check should be
**widened**, not whether the gate should open. So is this digest.

`b1f561587b19` is **not a question** and belongs in §4: the extra-entry penalty never reaches the
verdict. `section_shortfall` appends the complaint to `missing` but adds nothing to `required`, and
a well-formed extra entry raises `present` and `required` equally, so `frac` does not move.
Reproduced: three entries against `expected_entries=2` gives 15/15, frac 1.0, no refusal. Padding
with invented entries is free, which is the thing Hard Rule 1 forbids — and the companion drill net
asserts that the *string* appears in `missing`, so it is green while the thing it is named for does
not happen.

### 2.10 What may an autonomous model's patch be gated on? — 4 orders
`850786a2fee4` and `5c962f306e58` are **the same finding**, filed a week apart: `foreman._checks_pass`
gates a model-authored patch to live source on `import`, `verify_math`, and `allsweep --quick` — and
`--quick` runs only the IMPORT and LINT tiers. The VERIFY tier is skipped entirely, and `drill`
appears **nowhere** in `allsweep.py`, so **not one of the nets is fired before a model patch is
kept**. Hard Rule -1 names `python src/drill.py` as the PROVEN property.

The reason it was not simply fixed is real and is yours to weigh: `verify_math.py:5504` records a
standing rule that `verify_math` and `drill` "are not safe to run" from an agent context, and
`drill.py` historically wrote trial values of `prose_enabled` into the live config. Adding drill to
the gate would have a standing daemon run it on every kept patch. The sharpest half is already
closed — drill, escalation, codewatch, liveness and overnight are on `foreman.DENYLIST`, so the
model lane cannot edit them at all.

`d3acbb793ef2` and `556c1b8fda9f` are two more holes in the same lane, both traced and neither
currently exploitable: the cascade **pin path** has no `LOCAL_PREFIX` exclusion (so `try_disabled()`
would dispatch a live call to a local GPU bucket, which that file calls an absolute invariant never
to do), and `local_agent._safe` resolves junctions and symlinks but **cannot see NTFS hard links**,
because `realpath()` returns a hard-linked path unchanged. Both have exact remedies written.

### 2.11 Ledger hygiene — 3 orders
- `ca0a93856e2a` — **52% of `BUGS.md`'s `## Open` section is entries that say RESOLVED in their own
  label.** 56 of 108. A reader looking for what still needs doing wades through 56 finished items.
  The file's own header forbids this, and `workorders.resolve` cites this exact section as the
  reason it *deletes* on close. Not done automatically for a good reason: six entries (M38, M16,
  M42, m105, m133, m134) are PARTIALLY closed, and a regex that moved everything labelled RESOLVED
  would silently close live faults.
- `dc9ffadae765` — the queue's own stored proof text carries **2,898 `file.py:NNN` citations that no
  detector has ever checked**, in a project that files dozens of orders a sweep about exactly this
  drift in comments. 393 of 458 orders carry at least one. A cheap scan can only catch citations
  past end-of-file (5 of 2,898); the common case drifts to a wrong line *within* the file and is
  invisible. **This digest is direct evidence the finding is right — see §3, where I found eleven
  more.** Do **not** bulk-rewrite the stored numbers: those are correct findings with stale
  pointers, and automated renumbering is editing evidence.
- `864a626a258e` — `CLAUDE.md`'s Hard Rule -1 says drill "attacks all 57 nets". The order measured
  269 `net()` call sites; **I measure 407 today**, so the order's own correction is already stale,
  which is rather the point. It matters slightly more than an ordinary stale number because 57 is
  the one claim in that paragraph a reader can check, and `drill.py:2564` already reasons from it
  ("WHY 57 NETS MISSED IT"). Replace with "every net". The three properties themselves stand.

### 2.12 Remaining single questions
Each of these is genuinely one decision with no sibling, and each order states both readings:

`5c8a7bc883e7` / `6fc71f8ab76e` (the same `with_feats or rest` short-circuit, filed twice — a single
feat-bearing entry excludes the whole remaining cast from ceiling nomination; measured live, 46 of
54 lead paragraphs dropped because 8 siblings had a mined feat) · `c391a1f77e42` (phase 8 closes
silently on an empty record — a fix was attempted and **the library's own drill net refused it**,
so changing it means moving a net, which must be your decision not a run's) · `d2e44a766769`
(`restart_reader` SIGTERMs a job it cannot restart; the sibling killer got the "NEVER KILL WHAT YOU
CANNOT RESTART" gate and this one did not) · `7ad10a229440` (`reprove_pool` returns did=True on any
successful measurement, so it breaks the remedy chain and `restart_reader` never runs) ·
`d8858a26e46e` (a module partition does not partition *meaning* — run #36 halted its own library for
32 minutes through the gap between a fix and the net asserting the old behaviour) · `fbc0930ae309`
(proving a new behavioural net works currently costs an outage; source-shape nets have a scratch-tree
affordance and behavioural ones do not) · `97cc0dc43ca7` (the halt write race, narrowed 25× and
honestly reported as not closed; the real fix is an O_CREAT|O_EXCL lock with a **fail-open** fallback,
which is a design decision on the halt path) · `b186bc4dad8f` (**read this before touching `topic` or
`category`** — they are three axes, not two names for one thing, and a run acting on that misreading
rewrote 7,909 topics before catching it) · `28c1f58f5e8a` (six run35 proposal files with 59 checks
covering 67 order ids are neither spliced nor globbed into `verify_math`) · `3d2d9b87cc10`
(`FOR_OWNER.md` is tracked in the export repo, is not in `COPY_FILES`, and therefore can be neither
refreshed nor withdrawn — both readings are one-line changes in opposite directions) ·
`24155b641dfa` + `f5503302ce44` (**the same order twice**: the bloons secret-scan waiver's scope
caveat was destroyed by a stored cap and ends "…this only sur" mid-word; confirmed still on disk at
exactly 300 characters. Only its author can restate it; the alternative is deleting the row so the
finding reports again. Doing nothing leaves an unreviewable secret-scanner exemption standing to
~2026-02) · `8f50f37255b5` (`_STOPNAMES` drops entries named "father", "god", "king" *entirely* from
`ENTITY_INDEX.json` — Fullmetal Alchemist's character literally named Father would be invisible) ·
`27f823fd6ed5`, `82fc93f056d4` (55 wh40k axis citations read `[unattributed]`; the code is ready for
per-axis tags and what remains is purely the reading) · `68459d3e739b` (the franchise-rank check now
works but rests on **one** franchise; 7 of 8 scales cannot be scored for want of assays) ·
`b813fc5a37e2` (the phase-routing gate claims a proof-staleness check it does not get and throws
away the caption that carries it) · `a3d518d078c3` (44 sources are stranded with an empty ceiling
and the rescue tool selects on the wrong condition, so it reaches 0 of them — Overwatch, FFXIV/Eorzea
at 685 entries, Ghost Recon at 808, and 41 more, all named in the order) · `2239a87c57f5`,
`372d4a8c8d46`, `2f38b3e5258d`, `e038ec1759a9`, `85a6b7b9e2c8`, `692f693c3900`, `382d3a1c387c`,
`5a0c4196142f`, `ef8940b363b3`, `18f7673b77ce`, `e296ea51a1d9`, `79da6c08c536`, `98f18453deaf`,
`91cf746c651e`, `a34f10a87483`, `ec05033115d6`, `2e0ba4b02ec4`, `61037867dc5d`, `d44b106ce7e3`,
`2d8b96343896`, `423e35500033`, `8350f7a183d1`, `9b3e59aeeb19`, `fc08e056e1ab`, `6d594a775899`,
`845dbaec182f`, `9adb8291c16c`, `b248f8f706d3`, `47067a8f0ad5`, `18d0fedabf13`, `e68664e621bf` —
each a stated two-reading question in its own order, none with a sibling to group it with.

---

## 3. STALE — verified against source today. **These are yours to dismiss, not mine.**

I read the live source for each. Where a finding still stands but its *pointer* has drifted, I give
the current line so the next reader does not have to re-derive it.

**Fully overtaken — the condition the order describes no longer exists:**

1. **`33000660ddac`** ("`feats.py --roll` returns 0 unconditionally") — **fixed.** `feats.py:1853`
   now binds `done = roll(...)` and lines 1854-1872 implement exactly the remedy asked for, citing
   order `f4f4b9d5f935`.
2. **`8c354f6c9780`** (twin watchdog fails open silently) — the "safe middle nobody applied" **is
   applied**: `autostart.py:69` `TWIN_TRIES = 4`, `:302` the retry loop, `:297` and `:321` log
   "FAILED OPEN" explicitly before conceding. Only the fail-open-vs-fail-closed *design* question
   survives, and that is §2.7's group question, not a separate order.
3. **`47c8def059e3`** (cosmology_graph console truncation) — the four cuts it names
   (`pair_w[:16]`, `comps[:8]`, `pair_shared[:4]`, `c[:6]`) are gone or marked. The comment at
   `cosmology_graph.py:96-97` records that both surviving list slices now carry "(+N more)", and
   the string cuts go through `_cut()` which appends an ellipsis. Folds into §2.1.
4. **`cefcad5fc513`** step (1) — "NOW: pin it" is **done**: `drill.py:1311-1312` nets
   "assert_step4_open RAISES when closed". Step (2) — wiring it when Step 4 gains an entry point —
   still stands, so the order should be *narrowed*, not closed.
5. **`9fb8a6b10c1f`** — a 2026-08-25 census of five 402-ing providers and five 404-ing local
   models. Superseded by `88982cef258d`'s current picture; the named model list is a year-stale
   inventory of a pool that has since been re-rostered.

**Diagnosis refuted or overtaken — the finding is real but the mechanism recorded is wrong:**

6. **`a8464e348c5e`** and **`505177847f43`** both attribute the local-rung stall to a `num_ctx`
   mismatch forcing a per-request model reload. `4e37d5e59b09` **refuted that by direct
   measurement** (the resident context stayed 4096 across `num_ctx` None/4096/12288/4096; Ollama
   never reloaded), and `f6c52ef7657f` then named the real mechanism (port exhaustion). Three
   orders carry two dead diagnoses of one live condition. Acting on either would have cost quality
   for nothing — `4e37d5e59b09` says so explicitly: *do not lower `num_ctx`.*
7. **`d2583f4c8b36`** (local rung unworkable, Overwatch.exe holding 9,762 MiB of the card) —
   measured today, Overwatch.exe is **not** a GPU compute client. Condition not live.
8. **`f6c52ef7657f`** / **`28f79d511879`** — measured today: 308 host sockets, **4** on `:11434`,
   no `semsearch` python process running. **Not stale — the order documents this as cyclical** —
   but the emergency framing is not current and a reader meeting these cold would think the
   machine is on fire.
9. **`01695fe3ef26`** and **`7e360eaec3a6`** both rest on the premise that the module's "only
   mention anywhere is its own name inside `derivation.SCAN_MODULES`", implying a hand-written
   list. `SCAN_MODULES` is now `sorted(f[:-3] for f in os.listdir(HERE) ...)` at
   `derivation.py:543` — it enumerates the directory, so every module is in it automatically and
   being named there means nothing at all. Both orders' cited line (`derivation.py:477`) is also
   wrong. This is the pair `dc9ffadae765` found by hand; I confirm it and add that the *premise*
   drifted too, not only the pointer.
10. **`665e3609bc82`** — all four cited lines are wrong (`542`→925, `550`→933, `876`→1313,
    `1026`→1571) **and** it is superseded by three newer orders covering the same four functions
    with current pointers: `4f308dbd9d2c` (resolve_title), `f27d210d4fea` (alive, _page_exists),
    `0b1cda11f4a2` (axis_evidence). Note `0b1cda11f4a2`'s own citation (1301) has already drifted
    to 1313.
11. **`1cdc2f8cd2f3`** — its `catalog.py` half is recorded as already settled by order
    `6434c1ba7b20`, inside the order's own `where` field. Only the `identity.py` half is open.
12. **`eb681053b234`** — half fixed: `local_agent.py:667` now passes
    `env=dict(os.environ, PYTHONIOENCODING="utf-8")`. The `encoding=`/`errors=` half stands (the
    parent still decodes `text=True` with the platform default), so the risk is reduced, not gone.

**Finding stands, pointer drifted** — current lines, so nobody re-derives them:

| order | cited | actual today |
|---|---|---|
| `de43fe54feb7` | `scope.py:123` | `scope.py:210` — still no callers, only comments |
| `570525d35825` | `endpoint.py:301` | `endpoint.py:396` — and `:392` now carries a comment stating the finding |
| `1eb00a84225e` | `address_space.py:133` | `address_space.py:141` (`threads.py`'s `UNADDRESSED` is a different constant) |
| `c0384991bfc5` | `worldseed.py:236` | `worldseed.py:278` |
| `e8622cf0d047` | `local_agent.py:830` / `:707` | `:931` / `:777` — still unguarded |
| `541384445ec3` | `pipeline.py:1928` | `pipeline.py:2321` |
| `aad11acb1183` | `dashboard.py:968` | `dashboard.py:1068` |
| `e4c8355cc7a0` | `assay.py:1352` | `assay.py:1392` |
| `18187cb13de7` | `magnitude.py ~1153`, `~1357` | `:1175`, `:1380` — both still omit `host` |
| `850786a2fee4` | `allsweep.py:479`, `:498` | `:702`, `:727` (`5c962f306e58` has these right) |
| `789f99f2a65f` / `95f80c0ea860` | `tiers.py:309` / `:357` | `tiers.py:359` |

**Re-measured, number changed:** `481ef92af785` says 28 of 155 SCOPE rows hold invented ceilings.
Today it is **20 of 155**, and the worst case it names is no longer the worst: `tales.fandom.com`
carries **M7 on a single mention**. Both hosts it names are still there —
`root.fandom.com` M7 on 3 mentions, `rosariovampire.fandom.com` M7 on 2, against `MIN_MENTIONS=10`.
The fault is unchanged and still clamping published Magnitudes.

**Duplicate pairs — close one when you close the other:** `f84cb75edcfe`/`1b7f14efce8e` ·
`f07b7d538ed1`/`2d6bef2aef03` · `be9e9f089d62`/`8fb33a0204c4` · `adaeaa7ad639`/`cdfeccbfbab0` ·
`24155b641dfa`/`f5503302ce44` · `850786a2fee4`/`5c962f306e58` · `5c8a7bc883e7`/`6fc71f8ab76e` ·
`c8dc624e4e02`/`b9584c782d95` · `44c420f80448`/`b86d79c574e3`/`0c1670811107` (the third says so
itself and explains it was filed separately only to avoid overwriting the other two's evidence).

---

## 4. NOT ACTUALLY AN OWNER DECISION — hand these back

These landed here because nobody wanted to decide them. Each has an exact remedy already written
in its own text, a sibling in the same file that already does it right, or a project ruling that
has already settled the principle. **Suggested rung in bold.**

**Close outright — already fixed:** `33000660ddac`.

**→ RUN. One-line or few-line defects with a correct sibling in the same file:**
- `e8622cf0d047` — `local_agent.py:931` `why[:200]` where `why` can be `None` from model JSON;
  `:777` already writes `(why or "")[:200]`. Throws away a patch that passed every gate and blames
  a `TypeError`.
- `18187cb13de7` — add `"host": host` to two dict literals in `magnitude.assay_entity`; every
  sibling return has it.
- `eb681053b234` — add `encoding="utf-8", errors="replace"` to the pyflakes call; its two siblings
  set an encoding contract and it does not.
- `61c763a60779` — capture `quarantine()`'s `landed` verdict; the two branches immediately below
  already capture `release()`'s, and the console currently claims quarantines the file may not hold.
- `e8466cd6ed14` — `chain.main()` reports success over a `CHAIN.json` that was never written.
  **Five sibling sites were already repaired** under rulings `dc5c92aad5c1`/`3e65dbed45a6`; this is
  the one that was missed, and `pipeline.phase_chain` already compensates by asking the disk.
- `729c26e0e63c` · `4da7238657a3` · `fa86e8b92150` · `c2bbe43e0f2d` · `b9584c782d95` — accounting
  gaps where a number already in hand is dropped on the floor.
- `9e300162f4df` — `catalogue_composite` hardcodes `type: "Deity"`; the single-wiki path in the
  **same module** was repaired for exactly this under order `6eb20e8d3565` and the fix pattern is
  three lines away.

**→ RUN. Hard Rule 0 already rules on these; there is nothing left to decide:**
- `541384445ec3` — `most_common(6)` over a population the doctrine bounds at exactly 6. **Zero
  margin**: it truncates silently the day a sixth grounding type is added. `most_common()`.
- `ecc355769a41` — three unmarked 120-char cuts on exception text that is **stored** in
  `BINDING_HEALTH.json` and `HOST_QUARANTINE.json`. The identical cut one level down in the same
  module was already removed under order `d6ca84486153`.
- `19c507a16430` · `1f9a54bede08` · `cca253138a62` — the same, in stored record fields and a
  console trace, all with a house marker idiom already written (`policy._observed`,
  `suppressions._preview`, `style_audit._cut`).

**→ RUN. Real defects filed as questions:**
- `b1f561587b19` (**MAJOR**) — the extra-entry penalty never reaches the prose verdict; padding
  with invented entries is free, and the drill net asserting it is green while the thing it names
  does not happen. This is the one I would move first.
- `4398d76f822f` (**MAJOR**) — `repass_bands --apply` overwrites a rejected `scale_note` with `""`
  and preserves it nowhere. `pipeline.py:1540-1553` handles the identical event the opposite way
  and records what this cost last time: **51,611 entries blanked, ~46,000 candidate feats
  destroyed**, and the rejection rate made unauditable. `--apply` is precisely the run that would
  do it at corpus scale. The remedy is field-for-field copyable.
- `dc501e776a2b` (**MAJOR**) — `rigor.theorem_1_check` returns `both_say_consistent=True`, its
  strongest verdict, for a matrix it computed `nan` from. Validate the input and raise; make two
  one-sided tests two-sided. No curatorial content.
- `76ab006d84b8` — `band_for_quantity` returns a confident `"M0"` for any positive quantity on an
  axis with no floor (six of eleven Measures). **The identical initialiser fault was already fixed
  in `cosmography.kardashev_to_magnitude` under order `be783948fd66`**, and the function already
  has the right convention (`None`) two lines up.
- `e4c8355cc7a0` — `covers_all_signatures` is true by construction and presented as a charter
  check. `custodes.py:539-551` already carries the identical shape **and declares it** (m30), so
  the project has ruled on how to present this; only the copy needs writing.
- `2c8e55f8f3f7` — `address.tier_rank` returns 0 for an unrecognised tier, the same rank as the
  lowest real one, so a corrupt shelf address survives every promotion pass indefinitely.
- `88a5f9192e1b` (**MAJOR**) — `cachekey.owns()` checks the entity and never the host, though the
  record stores both and `host_dir()` applies the same lossy sanitiser-plus-cap that produced this
  module's founding bug for names. One live host already sits **exactly at** the 40-char cap.
- `51f0be4252e6` · `3e11c452ff67` (**both MAJOR**) — `verify_math` section 20p's fail-open guard is
  a regex that matches **none** of the eight files it guards and **zero of six** plausible
  regressions; its companion check is satisfied by the string "REFUSING TO" appearing anywhere,
  and `publish.py` contains it five times. Two layers, one failure mode, on a Hard Rule -1
  interlock protecting the one daemon whose action is irreversible and outward-facing.
- `1e83e387cfc1` · `0a9943374fe6` — the same family: a floor with 15 of headroom that reports a
  count instead of a name, and a check that greps `"rc = 1"` in a 1,500-line file. The sibling
  instrument was already retired for this exact reason under order `ba7b55d6465f`.
- `762256b4b844` · `464cc4e12fbc` — tiny contract tightenings in fail-closed code.
- `9adb8291c16c` — a repo-wide `glob` rebuilt **inside** a per-row loop, called by a drill net every
  cycle, and blind to dotted paths.

**→ LOCAL (mechanical, no judgement):** `7716ac4884cc` — six `file:line` cross-references in
`pipeline.py` that no longer land; all six correct values are in the order. Better still, cite by
symbol, which is what `dc9ffadae765` argues for generally.

**→ BOTS or RUN, not OWNER — the sweep's own bookkeeping:** `44c420f80448`, `b86d79c574e3`,
`0c1670811107`. `sweep_plan.batches()` is a greedy bin-pack recomputed from **live line counts** on
every call, so batch membership changes underneath a running fan-out. Measured three times in one
run: batch 12 got 1 module in common out of 9 across forty minutes; batch 10's shard **actually
landed a false coverage stamp** claiming six modules nobody had opened, one of which
(`custodes.py`) was read by nobody that run. That is a coverage ledger claiming a clean sweep over
a real gap — a check that cannot fail wearing the shape of one that passed, applied to the audit's
own bookkeeping. **I verified today that nothing is frozen: `batches(n=16)` still recomputes and
there is no plan file.** The remedy (freeze the pack once per run and have `record()` refuse a
mismatch) is a code change, not a coordination call.

**→ RUN once §2.4 is nodded through:** `95f80c0ea860` — the `tiers.py` report contradicts itself
thirty-nine lines apart. `789f99f2a65f` already established which side is stale.

**Half RUN, half yours:** `b813fc5a37e2` — the docstring claiming a staleness check the gate does
not get is simply wrong and should be corrected by a run; whether a stale pool proof should be
*discounted* rather than merely captioned is the live question `tuning.py:62-66` declines to settle
and is yours.

---

## 5. Residual roster

Every order id on either rung, so nothing here is a smaller universe than the queue. Ids named in
sections 1-4 are not repeated.

**OWNER, not otherwise named:** `9a44b1535851` (records written outside the sanctioned record
writer; the clobber symptom is blocked but the routing is still outside the contract and the
two-writer hazard on `data/records` stands) · `6c479972e838` (liveness DEAD detection needs a
receiver-aware `used` set, which must move in the same change as `drill.LIVENESS_CEILING` because
the ceiling is a ratchet) · `40e98eed6870` (an era/condition vocabulary — "primitive", "settled" —
the feature extractor can never produce) · `d2da5914da94` · `98f18453deaf` · `79da6c08c536` ·
`95f817b752ac` · `91cf746c651e` · `a34f10a87483` · `2e0ba4b02ec4` · `ec05033115d6` ·
`61037867dc5d` · `171ade4c7d27` (**worth reading before acting on any local-rung order**: it
measures and *refutes* a remedy an earlier run proposed — refusing on the first Ollama 503 would
have converted a slow success into a fast failure, because the 503 is transient and the six
minutes are being waited, not burned) · `e296ea51a1d9` · `fc08e056e1ab` · `6d594a775899` ·
`845dbaec182f` · `e68664e621bf` · `db36d589713e` · `1a9c237dda4d` · `38c51153243c` · `c9e6e50e792f`
· `4d78c426afb3` · `2f38b3e5258d` · `372d4a8c8d46` · `5a0c4196142f` · `ef8940b363b3` ·
`18f7673b77ce` · `692f693c3900` · `382d3a1c387c` · `85cdecef25f8` (`weapon property`, 35
occurrences, is the third unmapped codex element type and defaults to THINGS; probably POWERS, but
curatorial).

**SESSION, not otherwise named:** `8d8ba5377fb6` · `a3d518d078c3` · `7716ac4884cc` · `c8dc624e4e02`
· `f90795d5c6bd` (`codewatch.stamp(who=...)` never reads its own argument; four callers volunteer a
job name that goes nowhere) · `18d0fedabf13` (`anchors.run()` computes and prints a college reading
and a bit value that **no verdict grades** — in the file whose own rule is "A CHECK WHOSE RESULT IS
PRINTED AND DISCARDED CANNOT FAIL"; the order names which properties are genuinely falsifiable and
which would only add a tautology) · `2d8b96343896` · `c72431056a14` · `85a6b7b9e2c8` ·
`e038ec1759a9` · `1f9a54bede08` · `d44b106ce7e3` · `14a73de63099` · `9b3e59aeeb19` · `12c457975677`
· `47067a8f0ad5` · `b248f8f706d3` · `9adb8291c16c` · `423e35500033` · `8350f7a183d1` ·
`572918512dbc` (**the project's signature failure inverted**: `page_looks_real`'s refusal-marker
layer is refusing **real articles** — 119 records, every one on a MediaWiki API host where a block
page cannot arrive at all, including two 41,125-character Final Fantasy articles refused whole and
Doom's UAC announcer, whose canonical voice line *is* "Access denied") · `4f308dbd9d2c` ·
`f27d210d4fea` · `33000660ddac` · `dc9ffadae765` · `ca0a93856e2a` · `4da7238657a3` · `18187cb13de7`
· `b9584c782d95` · `88a5f9192e1b` · `556c1b8fda9f` · `51f0be4252e6` · `3e11c452ff67` ·
`1e83e387cfc1` · `0a9943374fe6` · `dc501e776a2b` · `e4c8355cc7a0` · `76ab006d84b8` · `2c8e55f8f3f7`
· `0c1670811107` · `ddb5eadd8934` · `4398d76f822f` · `b813fc5a37e2` · `541384445ec3` ·
`19c507a16430` · `95f80c0ea860` · `44c420f80448` · `ecc355769a41` · `61c763a60779` · `e8622cf0d047`
· `eb681053b234` · `cca253138a62` · `9e300162f4df` · `729c26e0e63c` · `e8466cd6ed14` ·
`fa86e8b92150` · `c2bbe43e0f2d` · `6fc71f8ab76e`.

---

*Compiled 2026-09-05 by reading all 185 orders in full. Staleness claims in section 3 were checked
against live source and live data on the same day; the measurements quoted there are mine, not the
orders'. Nothing here was closed, dismissed or edited — OWNER orders are the owner's.*
