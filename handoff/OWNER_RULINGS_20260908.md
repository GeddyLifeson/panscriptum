# OWNER RULINGS — 2026-09-08
**Ruled by the owner, in session, on 2026-09-08**, through the decision dialogue published at
`https://claude.ai/code/artifact/ede39771-c1eb-45a0-b24a-4a3915683b49`. The selection is recorded
in that artifact's own store (`rulings/selection`, 22 of 22) and was read back and verified
against the recommendation set before any of it was acted on: all 22 are the recommended option,
none diverged.

These 22 rulings settle **137 work orders** that had accumulated on the OWNER and SESSION rungs.
Each order closed under them cites this file.

This file exists because of Hard Rule -1: a decision must be RELOCATED somewhere findable, never
merely remembered. A ruling whose record nobody can find has not been ratified.

**Nothing here opens `prose_enabled` or `step4_enabled`** — both remain owner-held and shut/held
as they were. No ruling weakens a guard: three options that would have (blanket ledger
suppression across the battery, fail-closed halt-write locking, and suppressing the drill halt
while `MAINTENANCE_RUN.json` is live) were deliberately not offered.

**Phase 4.3 is NOT authorised by any of this.** It needs its own ruling recorded in
`STEP4_PLAN.md` the way §7E and §7F were.

---

## The fourteen irreversible ones, named

These spend, re-mine, re-derive, change what publishes, or alter a safety's authority.

- **Wrong wikis, wrong titles, unmined entities** (10 orders) — Wire resolve_title alongside the raw name, then re-judge
- **Charter prose against the measured values on disk** (10 orders) — Whatever is published wins; correct the side nothing rests on
- **Filters that quietly remove entities from the roll** (7 orders) — Rank instead of displace; record every drop and re-ask
- **Traffic on the Fandom edge, and what gets re-mined** (5 orders) — Pace per domain, defer quarantined hosts, re-mine only anomalies
- **Live machine state inside the battery** (4 orders) — Name the class and port the whole-run ledger spy to drill
- **Whole modules built and never wired in** (7 orders) — Wire what closes a measured gap; hold the rest, marked
- **Stored files a fixed writer would now compute differently** (6 orders) — Re-derive all of it, with a snapshot and a before/after table
- **Nets that cannot fail on the guard they name** (6 orders) — Fixture-driven nets, a scratch-tree harness, no ceiling move
- **The last checks before an irreversible outward act** (6 orders) — Name the criterion, check beside the write, ratify the floor
- **Which faults sound, and on which rung** (6 orders) — Abstain where the instrument is down; raise where the fact is real
- **Who may lift a halt or a subsystem stop** (5 orders) — Compulsory attribution, a person-facing resume, one refusal type
- **Gates reading a tree under concurrent edit** (5 orders) — Re-read before halting; a foreign edit voids the run, not the park
- **Which measurement passes get commissioned now** (6 orders) — Take the cheap passes; abstain where there is no honest input
- **Evidence cut before it was stored** (4 orders) — Re-review the waiver, preserve the rest, mark the remaining cuts

---

## All twenty-two

### 1. Correct code that no caller ever reaches

**Question.** When a public symbol, constant or table in src/ has no caller, is it annotated and kept, retired, or wired?

**Why it mattered.** Sixteen orders across ten sweep batches ask this about the same shape: thirteen public functions only verify_math/drill/liveness call (assay.interval_from_hands now has 13 battery call sites, up from 8), tempus.DEGENERATE_TIME with one battery reader, assay.REFERENCE_JOULES, catalogue_web's two None constants, sweep.load, worldseed.URL_SETTABLE, scope.ceiling_for, address.build_address and sweep_plan.coverage_map. The tree already has a house answer nobody has ruled on -- the 'REPORTED DEAD, NOT DELETED' marker at feats.py:1346-1352 -- so every sweep re-finds these as open questions instead of a decision.

**RULED: (a) Mark and keep: one line each, delete nothing** — Every uncalled public symbol gets a one-line retention marker in the feats.py:1346 idiom naming the order and the date, and overwatch's _STATE_RANK keeps its refuted/stale ranks documented rather than dropped, because 6 of the 1,404 rows on disk still carry them.

*Reversible.* Settles 16 order(s):

```
1a9c237dda4d e68664e621bf de43fe54feb7 c0384991bfc5 7099a092abd3 0291835411d9
db36d589713e 665e3609bc82 d411f780d347 4e92365b54f6 c72431056a14 12c457975677
47067a8f0ad5 2b695c192470 464cc4e12fbc 40e98eed6870
```

Not taken: (b) Retire by default unless a caller lands the same shift; (c) Case by case: wire the four that hand out wrong answers

### 2. Wrong wikis, wrong titles, unmined entities

**Question.** For sources whose wiki binding or catalogued titles do not resolve, do we wire the ranked title resolver, unbind, rebind, or re-catalogue?

**Why it mattered.** feats.resolve_title has zero callers -- discover() still passes the raw catalogue name and the 17,148 entities the docstring is about are still mined to nothing -- while WIKI_HOSTS.json points Star Realms at a wiki serving The Brain World Wikia (66 sightings) and Prime World Equipment at the Prime Hydration energy-drink wiki. The probes that judge these bindings are themselves broken: binding_health tried eight alphabetically-first artificer features against eberron's 212-entry catalogue and eight real-world admirals against warthunder, and BINDING_HEALTH.json is 10.8 days stale, so none of these orders can close until it runs again.

**RULED: (a) Wire resolve_title alongside the raw name, then re-judge** — discover() adds the ranked resolved title beside the raw name with a mined_under stamp so a wrong resolution costs one extra fetch rather than a misattribution, binding_health reports '8 of N' and spreads its candidate pick instead of taking the alphabetical front, and only then are Star Realms and Prime World Equipment unbound and ANEURISM IV and warthunder accepted as feature-level if they still fail.

*IRREVERSIBLE.* Settles 10 order(s):

```
4f308dbd9d2c f27d210d4fea 2d6bef2aef03 f07b7d538ed1 f84cb75edcfe 1b7f14efce8e
efd2b537f26d 0fbaba6e1070 aecffd7eea57 14a73de63099
```

Not taken: (b) Fix bindings by hand and rule title resolution off; (c) Fix the probe artefact first, defer every binding call

### 3. The prose lane's model and layer four

**Question.** Which model does the prose lane run on, where are think-tags stripped, and what must layer 4 require before the gate is ever opened?

**Why it mattered.** config.yaml:37 points at qwen3:8b, a thinking variant the config's own comment forbids, and generate.py:255 string-matches its coverage checks against un-stripped output, so a model that names an entity while planning satisfies _covered and _deed_traced and collapses Hard Rule -1's three independent layers to prose_gate alone. That gate's REQUIRED_PER_ENTRY (prose_gate.py:49) still does not require an Instrument marker -- the 2026-08-25 incident's own headline symptom, 1,155 of 1,268 entries losing their Instrument block, a 91% loss -- and prose_enabled stays false under every option here.

**RULED: (a) Strip at the transport boundary and widen the gate** — generate.py strips think-tags once before any check or disk write sees the text (which survives a model swap and fixes _covered, _deed_traced, tags reaching disk and the output-reserve squeeze in one place), sends think:false alongside since it is free, requires an Instrument marker keyed off entry class so feats chapters that write none by design do not red, and renames the rule-of-three tell to the pattern it actually catches.

*Reversible.* Settles 5 order(s):

```
342ccfafa4a4 5bbd4b3376fe 3859043e365e 6e6954f261e0 382d3a1c387c
```

Not taken: (b) Change the model: pull the documented instruct variant; (c) Measure the thinking split before choosing

### 4. Charter prose against the measured values on disk

**Question.** When a charter sentence and the code's measured values contradict each other, which side gets corrected?

**Why it mattered.** address_space.py's prose claims '168 multiverses, 8 metaverses, 6 xenoverses, 1 hyperverse' while TIERS.json measures 143/6/3/6 -- all four numbers now wrong -- and the printed shelfmark drops the star field that FIELDS declares, against 1,016 published rows that are currently all distinct. On the other side cosmography's POCKET multiplier of 1e-9 makes 'a closed loop, a demiplane, one stage and no sky' hold 200 galaxies while SIZE_CLASS_MAX_GALAXIES caps it at 1.0, and assay_dof lists nine parents under prose reading 'ten survive the test' while custodes.py seats ten -- and every caller of census() passes 'STANDARD', so nothing depends on the multipliers at all.

**RULED: (a) Whatever is published wins; correct the side nothing rests on** — The three address_space prose sites read from _tier_counts() instead of hardcoded numbers and a None tier prints a marked blank rather than a charted zero (16 of 1,016 designations affected), seven-tier shelfmarks stand with both docstrings fixed and no re-addressing, the cosmography multipliers are brought under their own descriptions, applicability_mark joins assay_dof's parents so the College's ten seats stay derived, the Ruin column's U-shape is stated in the header, and ATTESTATION_FLOOR_UNRECOGNISED stays at 0.30 per the prior ruling.

*IRREVERSIBLE.* Settles 10 order(s):

```
adaeaa7ad639 cdfeccbfbab0 bc4156603071 38c51153243c c9e6e50e792f 8fb33a0204c4
be9e9f089d62 642a95fe9f3c 60dc7c624c06 1eb00a84225e
```

Not taken: (b) Charter prose is authoritative: re-cut and re-address; (c) Record every contradiction, change nothing

### 5. Filters that quietly remove entities from the roll

**Question.** When one of the library's own filters excludes an entity or source, must the exclusion be recorded and re-asked, or may it stand?

**Why it mattered.** pipeline.py:1459's `or` drops the whole rest of a cast from ceiling nomination the moment any sibling has a mined feat -- tales-from-the-yawning-portal nominates from 8 of 54 entries, kbp-unlikely-heroes from 2 of 55 -- and weave_index's _STOPNAMES removes all 34 generic names from a 266,406-key ENTITY_INDEX, so Fullmetal Alchemist's 'Father' does not exist to weave, cosmology_graph or thread_integrity. Forty-four sources including Ghost Recon (808 entries) and Overwatch sit in done_keys with no ceiling_entity and zero reachable by the rescue tool, and recover_folder_records unpacks a declared count it never compares, so a mapping declaring 350 against a register yielding 3 lands silently stamped 'catalogued'.

**RULED: (a) Rank instead of displace; record every drop and re-ask** — with_feats blocks are concatenated ahead of rest rather than replacing it, _STOPNAMES moves to the matching step so the index holds every named entity while a stopname collision stops counting as evidence, an explicit unassayable verdict is written with the cast digest it was reached against and re-admitted when the cast grows, stranded_sources selects on ceiling_entity, the missing counters land in feats_index/manifest_builder and recover_folder_records, and _queue_row routes through _norm_q so one rule has one implementation.

*IRREVERSIBLE.* Settles 7 order(s):

```
5c8a7bc883e7 6fc71f8ab76e 8f50f37255b5 c8dc624e4e02 a3d518d078c3 729c26e0e63c
fc08e056e1ab
```

Not taken: (b) Keep the filters, report them, re-ask nothing; (c) Re-admit only where the absence is provably a crawl artefact

### 6. Traffic on the Fandom edge, and what gets re-mined

**Question.** What caps the library's aggregate request rate against fandom.com, and do the 34,850 unexplainable empty records get re-mined?

**Why it mattered.** feats._throttle takes _HOST_LOCKS[host] keyed on the netloc at PAUSE=0.34s, so twelve workers across twelve fandom subdomains put roughly 35 req/s on one Fandom edge that believes it is being asked 2.9 -- and the quarantine meant to take over brakes nothing: all seven quarantined hosts have retry_after stamps expired by 1.1 to 235.8 hours. Separately 34,850 of 276,218 feat records (12.62%) carry pages_read=[] with pages_refused={} and cannot say whether they were blocked or genuinely blank, with www.dandwiki.com at 96.8% and marvel at 25.3% against dc's 8.6% on the same wiki farm.

**RULED: (a) Pace per domain, defer quarantined hosts, re-mine only anomalies** — _throttle locks on the registrable domain so every *.fandom.com subdomain shares one pacer, the fetch path consults is_quarantined and DEFERS the host to the end of the roll (never drops it, which would be a smaller universe in the same shape), pages_read is renamed to hold only gate-passing pages with pages_fetched preserving the old number and coverage gaining a REFUSED state, the 40-page MediaWiki category floor is declared and its dropped count reported, and only hosts whose empty-rate is anomalous against dc's 8.6% control are re-mined.

*IRREVERSIBLE.* Settles 5 order(s):

```
5be28f56946c 959b98f38a63 4d78c426afb3 ef4ca9edd61f 6d594a775899
```

Not taken: (b) Slow the whole crawl and re-mine all 34,850; (c) Pace correctly, stamp forward, leave the legacy records

### 7. What must pass before a model patch is kept

**Question.** What must a model-authored patch to live src/ pass before the foreman keeps it?

**Why it mattered.** foreman._checks_pass runs exactly three things -- import, verify_math, allsweep --quick -- and allsweep.py:790 and :815 skip the whole VERIFY and ESTATE tiers under --quick, so all ten verifiers including rosetta --check are skipped by the last gate in front of an autonomous model's writes; grep -c drill src/allsweep.py returns 1, and it is a mention. The denylist fencing the model off src/drill.py is also bypassable by file identity: local_agent.py:495 gates the denied-target interrogation on path divergence, and realpath() returns a hard-linked path unchanged, with no st_ino or st_dev comparison anywhere in the module.

**RULED: (a) Add a contracts pass; close the identity hole; keep drill out** — allsweep gains a --quick --contracts mode that runs each verifier's CLI for exit-code shape only so it fits inside the foreman's 20-minute round, _denied_target compares st_ino+st_dev against every denylist module and path, and the full drill stays out of _checks_pass because verify_math.py:5504 records drill as unsafe from an agent context and drill has historically written trial values of prose_enabled into the live config.

*Reversible.* Settles 3 order(s):

```
850786a2fee4 5c962f306e58 556c1b8fda9f
```

Not taken: (b) Run the full sweep on the patch lane only; (c) Close the identity hole and leave the gate as it is

### 8. Live machine state inside the battery

**Question.** Should the battery name a live-operational-state abstention class, or keep reddening on conditions that are not this library's code?

**Why it mattered.** dashboard.state() calls standards.check() internally, so standards.check() runs about 15 times per battery run, each doing a real getaddrinfo, an Ollama generate at timeout=300 and a 60-second PowerShell Get-CimInstance, against 38 silence.note('standards.py:*') sites and 29 dashboard.py sites -- while _THIRD_PARTY_CLASSES_VM holds exactly one dependency, 'cascade scratch DB'. The resulting non-determinism has cancelled three 20-hour mutation passes, and drill's only ledger net byte-diffs around two named probes where verify_math's section 20z spies on the whole run.

**RULED: (a) Name the class and port the whole-run ledger spy to drill** — Extend _THIRD_PARTY_CLASSES_VM with a named live-operational-state dependency listing the machine- and network-tier classes standards/dashboard/overnight may legitimately emit, close the two purely mechanical sites with _no_ledger_vm(), port verify_math's health.record/flush spy plus ledger snapshot into drill.py, and build suppressions.problems()'s listing once with os.walk instead of a full-repo glob per row on every drill cycle -- landing only after the running mutation pass finishes, since mutate takes its baseline from the live tree.

*IRREVERSIBLE.* Settles 4 order(s):

```
728d9e99e9ec 74f1bc47da2a 895a99602bf0 9adb8291c16c
```

Not taken: (b) Close standards.py's silent drop path instead; (c) Leave the battery reading live state

### 9. Whole modules built and never wired in

**Question.** For a finished module that nothing imports, is it wired into a cycle, held as marked charter apparatus, or retired?

**Why it mattered.** A repo-wide grep for 'import hosts' returns zero hits while data/SOURCE_HOSTS.json holds 94 verified extra host records across 73 of 208 sources, all unread because feats.py:50 still takes one host per source from WIKI_HOSTS -- the exact single-host cap hosts.py was written to remove. descending_ladder, render.py, ledger.py, scale_theories and onomast's genre-aware register are all finished and arithmetic-checked with no importer, and 5 of liveness.scan()'s current 45 findings are scale_theories alone.

**RULED: (a) Wire what closes a measured gap; hold the rest, marked** — hosts.py goes into the mining path behind the existing fetch throttling (never ahead of it, on a domain that has IP-banned this machine once) and render.py gets a step in the publish cycle, because both close a documented gap; ledger.py, scale_theories' four priced codifications and the genre register are marked as held for a future phase with the reason on the record, scale_theories' five duplicate physical constants go on the chord_field precedent, and nothing is deleted wholesale.

*IRREVERSIBLE.* Settles 7 order(s):

```
3fb312a72435 66f96febdb3a 707fefc17465 3fb9fc6b9999 01695fe3ef26 a78d5cd748b2
ae25c89f0179
```

Not taken: (b) Wire or retire: nothing is held; (c) Hold everything, wire nothing

### 10. Stored files a fixed writer would now compute differently

**Question.** Do the stored data files get re-derived under the corrected writers, moving published numbers, or are they annotated and left?

**Why it mattered.** genre.py and grounding.py were both fixed to divide by the whole field, but GENRES.json still reads Rush 2112 at 0.567 against a corrected 0.530 and flags 46 sources as mixed where the fix flags about 106, and none of GROUNDINGS.json's 209 rows carries the groundings_scored key the fixed code emits, so four sources publish confidence at or above 0.5 as settled cosmologies the full ranking makes contested. SCOPE.json holds 155 rows of which 146 carry a ceiling with no probe_version stamp -- root.fandom.com clamped at M7 on 2 universe mentions against MIN_MENTIONS=10 -- and magnitude.host_ceiling reads them off disk as authoritative clamps on every published Magnitude.

**RULED: (a) Re-derive all of it, with a snapshot and a before/after table** — Re-run genre --write, grounding --write and scope.build() after taking a snapshot, recording the movement in a before/after table rather than letting it happen silently, take the targeted re-catalogue of the roughly 25,000 entries whose stored type is not an entity kind (Total War: Warhammer at 690, 'Pages using ISBN magic link' at 255) while the prose gate is still shut, add the regression net that stops the topic rewrite recurring, and leave recover_folder_records outside the catalogue writer with the exemption recorded in the two-writer note.

*IRREVERSIBLE.* Settles 6 order(s):

```
b317ba3a4f36 3eff62be6cc3 f27c121c6cb7 481ef92af785 b186bc4dad8f 9a44b1535851
```

Not taken: (b) Re-derive only where nothing published moves; (c) Annotate every stale file and leave the numbers

### 11. Nets that cannot fail on the guard they name

**Question.** Must a drill net drive the module it names, and how are sharper nets and detectors proven without moving the ratchet?

**Why it mattered.** drill_codex_dedupe_is_typed imports catalogue_codex only for norm, rebuilds its own pairing key and never enters catalogue()'s loop, so reverting catalogue_codex.py:272 -- the exact f4f3c1d15915 regression that dropped 88 elements across 8 sections -- leaves the net GREEN; verify_math still pins guards with bare identifiers over raw source at :6142, :9331 and :5275, each defeatable by a comment reproducing the word. Proving a behavioural net currently costs a self-caused DRILL_BREACH because nothing in drill.py's 13,665 lines copies src/ to a scratch root, and 59 authored checks in six run35 files are executed by nothing while 56 of the 67 fixes they cover have a landed fix and no guard.

**RULED: (a) Fixture-driven nets, a scratch-tree harness, no ceiling move** — Nets drive the real function against a fixture rather than a reconstruction, drill gains a permanent copy-src-to-a-temp-root harness so a guard can be proven without halting the library (and every new net is also exercised in mutate's sandbox world, since a net red at mutate's baseline is disabled as a detector for the whole run), the remaining raw-source pins are comment-stripped with AST for the two that are the sole evidence a safety is wired, and the sharper liveness detector must land inside the existing 7 points of headroom -- settle scale_theories first, which frees 5 more -- while the phantom pass stays module-wide with its conservatism documented.

*IRREVERSIBLE.* Settles 6 order(s):

```
fbc0930ae309 2eabb417f58f 5a0c4196142f 28c1f58f5e8a 6c479972e838 2e0ba4b02ec4
```

Not taken: (b) Authorise the ratchet raise and adopt all twelve check files; (c) Rename the nets that over-promise and stop there

### 12. The last checks before an irreversible outward act

**Question.** Which entry points must ask whether the library is halted, at what moment, and what stands between a run and the public repo?

**Why it mattered.** escalation.py:886 says 'EVERY entry point calls this before doing anything' and it is true of 17 of 98 -- the dashboard, the one instrument built to display a halt, calls assert_clear before argparse so --once cannot even parse, while hostcheck's _land_hosts does the compare-and-swap that rewrites WIKI_HOSTS.json with no halt check at all, minutes to hours after the entry-time one, on a file the project has confirmed it cannot reconstruct. On the push side MAX_LOST_FRACTION is 0.05 set by taste, and handoff/HANDOFF.md holds 733 substantive lines of which only 700 are distinct, so 33 lines -- 4.50% -- could have been deleted and measured as exactly zero loss, half a point under the only gate in front of publish.push().

**RULED: (a) Name the criterion, check beside the write, ratify the floor** — Rule that every entry point which WRITES outside output/ and state/ asks and read-only instruments do not, so the dashboard renders the halt as its headline instead of refusing to start; re-call _assert_not_halted immediately before _land_hosts' compare-and-swap; put an O_EXCL lock with staleness steal around the halt write that still raises the halt if the lock cannot be taken in budget; ratify 0.05 as your own ruling with the 4.50% measurement recorded as its input; and give sync_tree a root-file sweep so FOR_OWNER.md and every future root file can actually be withdrawn.

*IRREVERSIBLE.* Settles 6 order(s):

```
97cc0dc43ca7 58cfc2b6dbc4 aad11acb1183 d44b106ce7e3 27f823fd6ed5 3d2d9b87cc10
```

Not taken: (b) Wire assert_clear into all 98 entry points; (c) Write the criterion and the loss ruling; defer the code

### 13. Which faults sound, and on which rung

**Question.** When an instrument cannot measure, or a write is refused, does it go red, abstain, or merely print?

**Why it mattered.** standards.py's fabrication row goes HIGH into the owner's file every supervisor round when the reader has merely logged no progress line yet, and because 'sentences that survive the verbatim check' is absent from foreman.REMEDIES that red row cannot dispatch a cure -- it can only occupy the page. At the other end drill.py:6858 halts the entire library if anyone reflows one comment at cascade_bridge.py:232, pantheon prints a ranking holding six of twenty-one entities and returns rc=0, and binding_health prints 'checked and quarantined' off a counter that never captured the write's verdict.

**RULED: (a) Abstain where the instrument is down; raise where the fact is real** — Route only the not-read case to _dropped while the three genuine instrument faults stay red, move the comment-wording half of the paid-lane net from 'halt the library' to a verify_math row while the structural half stays a net and the ruling stays pinned in code, make pantheon's _incomplete count toward merge_failed so the rc and the console agree, capture the quarantine and unfit write verdicts into the stored rows, and have runguard escalate on a corrupt guard while still allowing the claim, so the authorisation stops being silent.

*IRREVERSIBLE.* Settles 6 order(s):

```
95f817b752ac a34f10a87483 9fcbe25a473b 61c763a60779 79da6c08c536 70f66fbd98aa
```

Not taken: (b) Loudest wins: everything unmeasured stays red; (c) Correct the reports without touching any exit code

### 14. The one GPU, the local rung, the keeper's remedies

**Question.** Does the repair lane get a reserved GPU slice, and may the keeper's automatic remedy kill the reader?

**Why it mattered.** The card runs at 99% utilisation with llama-server holding 8.2 of 10.2 GB, ollama serves exactly one model so cascade grades '0 usable remote bucket(s)' and broken in every sweep, and the read pass sits at 0.01 chunks/s with an ETA of 17,433 hours -- while LOCAL now holds 43 open orders on a rung that only started answering after the num_ctx and gpu_lane fixes landed. On the remedy side foreman's 'counters are moving' list always short-circuits on reprove_pool, which returns did=True and '0 of N buckets answer' alike, so restart_reader -- which kills a reader with no _restartable() check and up to a four-hour restart horizon -- has never once run.

**RULED: (a) Measure one shift; make did honest; promote read.py** — Re-point cascade's local roster at the resident qwen3:8b so a permanently red subsystem goes honest at zero cost, let reprove_pool return did=False when zero buckets answer and mark restart_reader .always, put read.py --run into overnight.STANDING so the kill costs 300s instead of four hours, add local_agent's one narrow produced-nothing predicate (an answer with zero tool calls after a truncated slice whose chars_after_slice was non-zero), derive a doomed chapter's remaining lacking list without calling the GPU at all, and re-measure LOCAL for one shift before re-rating anything.

*Reversible.* Settles 6 order(s):

```
bffc372a96d2 9fb8a6b10c1f 171ade4c7d27 ec05033115d6 7ad10a229440 d2e44a766769
```

Not taken: (b) Re-rate LOCAL and forbid the reader kill; (c) Reserve a foreground lane for maintenance now

### 15. Who may lift a halt or a subsystem stop

**Question.** Should lifting a halt or a rung-4 stop require something a scheduled run cannot supply?

**Why it mattered.** escalation.clear() gates on _by_a_person_at_the_cli(), which only asks whether escalation.py is __main__ and whether the caller is its own main() -- both true for a scheduled run -- and --by still defaults to owner-cli, so the 2026-09-05 lift reads as 'scheduled-maintenance-2026-09-05-daily' only because that actor volunteered; it has now happened twice, the first time with the publish daemon resuming behind it. resume_subsystem gates on a 20-character ruling alone with no person-facing --resume command in argparse at all, and escalation.Refused -- the named type for the OPERATOR and SUPERVISOR rungs -- has no raise site, no except and no importer anywhere in the tree.

**RULED: (a) Compulsory attribution, a person-facing resume, one refusal type** — clear() errors unless --by is passed explicitly rather than defaulting to something that reads as a person, main() gains a --resume for rung-4 stops with a private test-only release path so drill's three probes do not leave orphaned stops, the existing per-unit and per-source refusals route through escalation.Refused so the chain has one spelling, escalate() rejects a non-integral float into the same MANAGER-with-evidence path (honouring is_integer() so 3.0 still passes), and a stale-code alarm escalates at MANAGER unconditionally instead of letting a heartbeating guard file demote it four rungs to JANITOR.

*IRREVERSIBLE.* Settles 5 order(s):

```
c614f7c145fc ddb5eadd8934 da15f582b2ea 762256b4b844 13aee150e0dc
```

Not taken: (b) Make the asymmetry real: require an out-of-band token; (c) Keep the current gates; honesty stays voluntary

### 16. Gates reading a tree under concurrent edit

**Question.** When a gate or a mutation run reads a tree other agents are editing, what may it stop -- the run, or the whole library?

**Why it mattered.** drill main() escalates OWNER/DRILL_BREACH on the first read with no re-read and no naming of an unsettled tree: run #45 lost a halt to it (publish.py's mtime is 51.8s after the halt) and run #46 hit three separate false reds in one shift, two agents independently. mutate answers any foreign edit with escalate(OWNER, MUTATE_TOUCHED_LIVE_TREE), and a pass is running right now over assay.py, prose_gate.py and escalation.py -- the three files maintenance shifts edit most -- while sandbox() still mkdtemps into a reapable name before _claim_sandbox can write the owner file into it.

**RULED: (a) Re-read before halting; a foreign edit voids the run, not the park** — The drill re-reads only the breached net on a settled tree and halts if the breach reproduces, naming the unsettled condition in the breach sentence when codewatch.quiet_seconds() is still under 180; MUTATE_TOUCHED_LIVE_TREE drops to a run-level abort with a message that stops naming this process as the corrupter and stops claiming coverage of the corrupt-then-restore case it is blind to; sandbox() mkdtemps under a prefix the reaper does not match and renames in after claiming; _run_mutation refuses a root equal to HERE; and the battery is sequenced after all agents report, with that rule written into MAINTENANCE.md rather than the NEXT_STEPS.md that is overwritten every run.

*IRREVERSIBLE.* Settles 5 order(s):

```
71ae3fa7e55e d8858a26e46e 4f5fa3146cc4 f9643582fd29 a1aa2be36b7e
```

Not taken: (b) One read, one halt: keep the current strictness; (c) Change the process, not the gates

### 17. Answering unknown with a plausible value

**Question.** When a routine cannot measure something, may it return a plausible-looking value, or must it say unknown?

**Why it mattered.** weave_index's directory-level scandir failure falls through to the clean cacheable signature (0, 0) -- an unreadable records directory reads as an empty corpus -- while the per-file handler eight lines above fails closed on the identical event, and that path reaches weave_index --write, which would land a near-empty ENTITY_INDEX over the population weave, cosmology_graph and thread_integrity read as the whole roster. The same shape recurs: axis_score returns one None for five different conditions with six of eleven Measures permanently in the missing-floor case, coin_well_formed returns the byte-identical string it just tested and rejected, completeness drops an unprobeable source instead of marking it unmeasured, and health.py exempts every directory under 25 files so a new host that 404s on everything stays invisible for exactly as long as it stays broken.

**RULED: (a) Say unknown out loud and name every refusal** — A directory-level failure forces sig=None like the per-file guard already does, axis_score keeps None only for genuinely unscorable input while raising AssayIntegrityError for a band off the Ladder and refusing the six non-energetic axes by name from anchors.NON_ENERGETIC_AXES, coin_well_formed's last resort appends a digest of base and stamps coined_under='exhausted' so shelfmarks stay unique without stopping world naming, completeness returns _unmeasured for a source with no probeable categories, health emits a weaker small-and-empty note below 25 files, phase 8 logs the ready-but-empty count while still closing, and liveness' phantom pass stays module-wide with its conservatism written into the docstring rather than moving the ratchet.

*Reversible.* Settles 6 order(s):

```
5f1dc97d5216 845dbaec182f 9b3e59aeeb19 c391a1f77e42 d2da5914da94 e296ea51a1d9
```

Not taken: (b) Keep the stable answers and document why; (c) Refuse rather than answer anywhere

### 18. Ledgers and sentences the code outgrew

**Question.** May a measured bulk pass correct the project's ledgers and stale sentences, or must every entry be hand-verified one at a time?

**Why it mattered.** BUGS.md's Open section now holds 134 labelled entries over 2,183 lines of a 5,023-line file, of which 75 say RESOLVED in their own label and only 59 are genuinely open -- it was 108/56/52 seven days earlier, so the one-at-a-time policy is losing to accretion -- and of those 75 only 3 carry a PARTIAL or STILL LIVE qualifier anywhere in their body, while all six entries flagged as must-not-move are labelled OPEN and so would never be selected. Alongside it CLAUDE.md still claims the drill 'attacks all 57 nets' against 449 net( sites, tiers.py prints 'hyperverse: DECLINED for all shelves' thirty-nine lines before printing a concrete H value, and secondopinion's docstring names a JANITOR escalation it never calls.

**RULED: (a) Measured bulk move, then move-on-resolve as a standing rule** — The 72 clean movers go in one revertible commit with their headers printed for a read-through first and the 3 qualified ones read by hand, a standing rule requires the run that resolves an entry to move it in the same commit, and the stale sentences are corrected in place -- 'attacks every net' rather than a number that goes stale weekly, the tiers print and docstring rewritten so the published hyperverse is said to come from grounding, secondopinion reworded to 'a JANITOR-level matter, recorded via silence.note', the grounding docstring given its synthesis-blob exemption, and one sentence in each of resident() and fit_note() naming which VRAM budget it answers.

*Reversible.* Settles 6 order(s):

```
ca0a93856e2a 864a626a258e 91cf746c651e 98f18453deaf 789f99f2a65f 2f38b3e5258d
```

Not taken: (b) Strictly one at a time, forever; (c) Correct the sentences now, leave the ledger for a dedicated pass

### 19. Does Hard Rule 0 reach console output

**Question.** Does the no-caps rule govern console reports and illustration lists, or only rosters the pipeline consumes?

**Why it mattered.** Five sweep batches asked this independently -- identity.py:717's top[:6], estate.py:422's 'e.g.' cut at four names, handbuilt's cited[:58], repass_bands' 8/14, hosts.discover's per_source=24 -- and the precedent already went one way once, when order 6434c1ba7b20 uncapped catalog.py to print every missing source. It is not always cosmetic: estate.py's [:4] is currently the only thing between you and the 33 unassigned-source names Hard Rule 2 reserves to you alone, and output/index/unassigned_sources.md has said 'None' since 2026-08-27.

**RULED: (a) Every cut prints its remainder; nothing is silently short** — Route every console cut through the house remainder idiom (style_audit._cut) so a printed '+N more' is structural rather than remembered, print all 33 unassigned source names in full because that list is your worklist, mark local_agent's arg and result dumps, move catalogue_web's MAX_PER_SOURCE tripwire to import time with a drill net pinning it None so it fires before a single request instead of after hours of network work, and write the rule into CLAUDE.md so it stops being re-derived every sweep.

*Reversible.* Settles 5 order(s):

```
1cdc2f8cd2f3 3dd5b6caef38 189532cbf41a b248f8f706d3 cca253138a62
```

Not taken: (b) Pipeline-consumed data only; announced console cuts are legitimate; (c) No cap anywhere: print every row in full

### 20. Which measurement passes get commissioned now

**Question.** Which of the outstanding reading, tagging and wiring passes on the Assay instrument do you fund, and which abstain?

**Why it mattered.** All 55 of wh40k.py's ROSTER axes print [unattributed] because every axis is still a 2-tuple, and halo.py's precedent found 24 of 33 tags false, so the prior that these are mixed quotation and paraphrase is strong. rosetta's franchise rank-agreement verifier rests entirely on dragonball at n=4 and rho=0.6 while One Piece's 96-row Bounty/List needs only 4 overlapping same-host names; anchors passes no distance or years_since so Lumen abstains at every calibration point; and none of the five CLAIMS lambdas reads the college object it is handed.

**RULED: (a) Take the cheap passes; abstain where there is no honest input** — Commission the one-sitting 55-axis wh40k reading, add the weapon property key to POWERS beside rule and proficiency (35 occurrences, ten seconds), add the unit-first Mach alternative as a bounded test at 210 unminable against 33 minable before anyone touches power level's 11,622 mentions, pass distance=0.0 for Lumen as a stated convention while Threnody stays abstained because SHARED_STAGE_GRAPH holds co-attestation weight and not contest flow, grade the college's finite-interval, dispersive and bit-value properties but never the prior/attestation shares, which are complements by construction and would grade a tautology, and print rosetta's UNSCORED row before funding any new assays.

*IRREVERSIBLE.* Settles 6 order(s):

```
82fc93f056d4 68459d3e739b 3b9812ae8ab7 85cdecef25f8 bd673ceaaf31 18d0fedabf13
```

Not taken: (b) Instrument now, content later; (c) Fund everything, including the seven unscored scales

### 21. Evidence cut before it was stored

**Question.** For stored evidence a cap already ate or is about to eat, do we re-review from scratch, re-justify, or only preserve going forward?

**Why it mattered.** data/SUPPRESSIONS.json's secret_scan waiver on data/feats/bloons_fandom_com/Encrypted.json is exactly 300 characters, ending mid-word at 'this only sur' -- the code cap is gone but that reason is unrecoverable, and the row stands unreviewable until expires_at 2027-02-21. repass_bands.py:74-76 still blanks scale_note with no preservation, against pipeline.py:1547-1553 whose comment records that the first version of that line blanked 51,611 entries and destroyed about 46,000 candidate feats -- and --apply is precisely the corpus-wide run that would do it again.

**RULED: (a) Re-review the waiver, preserve the rest, mark the remaining cuts** — Delete the Bloons row so the finding reports again and is reviewed from scratch -- never let a run invent a replacement sentence on the file that decides what a secret scanner may wave through -- set scale_note_rejected before clearing and SET the rejection companion rather than leaving it absent, doing it before the next --apply, and append the house marker plus the original character count to the 600/900 cuts with pipeline.py:1151-1152 changed in the same commit.

*IRREVERSIBLE.* Settles 4 order(s):

```
24155b641dfa f5503302ce44 1f9a54bede08 4398d76f822f
```

Not taken: (b) Re-justify the waiver in place and keep it; (c) Preserve going forward only

### 22. Free cloud pool: keys, cooldowns, stale proofs

**Question.** How is the free cloud pool routed and kept honest, given that the standing answer to spending money is no?

**Why it mattered.** groq's three buckets sit at 198,192 / 199,938 / 198,540 of 200,000 TPD and cascade_bridge parses no retry_after anywhere, so 3 of 6 probes dispatched into a bucket that had just answered 'retry in 499s' and the pool reported about 50% success while other buckets were answering. Two buckets are dark on credentials rather than quota -- cloudflare:free and hyperbolic:free, both HTTP 401 since 2026-08-25 -- six more now fail at connect in 7 to 120ms, which is a local refusal matching this machine's TLS interception rather than a provider fault, and pipeline.py:366 discards the pool-proof age caption its own docstring claims to check while sitting exactly on its threshold at 3 against CLOUD_MIN_BUCKETS 3.

**RULED: (a) Honour the stated cooldown, recover the keys, log the proof age** — Parse the provider's retry-after into a bench duration without writing to the unrecognised-failure ledger (a throttle is not a mystery), re-issue the two free API keys behind the 401s and re-probe the six connect-refusing buckets, filing any residual failure against this machine's firewall/TLS layer rather than benching six providers for a local fault, and capture the pool-proof caption so a cloud route taken on an eight-hour-old proof says so in state/pipeline.log.

*Reversible.* Settles 3 order(s):

```
2239a87c57f5 88982cef258d b813fc5a37e2
```

Not taken: (b) All of that, plus fail closed on a stale proof; (c) Recover the two keys and nothing else

---

*Recorded by the maintenance run of 2026-09-08. The dialogue's own selection document is
the primary record; this file is the findable copy.*

---

## 23. In-universe reference is a SUBSTITUTION, not only a prohibition

**Ruled by the owner, in session, 2026-09-08**, in their own words:

> *"any thing that would/should/could reference out of universe stuff will instead point to
> something in universe instead"*

**What changed.** `prompts/system_style.txt` rule 4 already forbade breaking frame -- no tier of
play, no dice, no addressing a real-world player. That is the prohibition half, and it is the
easier half: it says what not to write and leaves the sentence with a hole in it. The ruling adds
the positive obligation. An out-of-universe referent is not deleted, it is REPLACED by the
in-universe thing it points at, named specifically.

The Chronicle is the model and already writes this way: a certain small blue engine is *"on loan
from a distant island"*; the shelves are *the Shinobi Countries*, *the Blind Eternities*, *Hokuto
Star* -- never the titles a cataloguer would type.

**Recorded in the style contract** with the substitution table (creator to hand, franchise to
shelf, publication date to a date in AS, edition to recension, mechanic to practice, fandom to
attesting tradition, wiki to register), because that file is the one thing controlling voice and a
ruling that lives only in a conversation has not been ratified.

**The one limit carried with it:** where no in-universe counterpart can honestly be named, the
entry says so in the Custodial register -- *"the Chronicle does not record by what hand"*, *"attested
but unplaced"* -- which is itself an in-universe sentence about the limits of the record. Hard Rule
1 is not suspended: an honest in-universe silence outranks a fabricated in-universe fact.

*Reversible (a prompt edit).* `prose_enabled` remains shut, so nothing has been generated under it.

**Consequence for Phase 4.3, noticed while applying it:** the blocked shelf mapping (order
`c39a2c0e1bef`) was filed asking for a map from the Chronicle's shelf names to *roll source names*
-- which are out-of-universe titles. Under this ruling the mapping's target should be the
**in-universe spine code**, not the source title, and the Chronicle's poetic shelf names are
revealed as correct and deliberate rather than as an obstacle. The order has been amended to say so.
